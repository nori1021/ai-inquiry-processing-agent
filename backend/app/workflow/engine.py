from __future__ import annotations

import time
from typing import Any

from sqlalchemy.orm import Session

from app.agents.inquiry_agent import analyze_and_investigate
from app.config import get_settings
from app.models.audit import utcnow
from app.models.workflow import WorkflowInstance
from app.providers.approval import MockApprovalProvider
from app.providers.audit import record_audit
from app.registry import get_executor
from app.schemas.inquiry import InquiryAnalyzeRequest
from app.schemas.workflow import (
    ApprovalDecideRequest,
    ApprovalView,
    ReadonlyInvestigateRequest,
    TransitionView,
    WorkflowCreateRequest,
    WorkflowView,
)
from app.workflow.repository import (
    create_approval,
    get_context,
    load_workflow,
    pending_approval,
    set_context,
    transition,
)
from app.workflow.states import (
    READ_ONLY_TOOLS,
    TERMINAL_STATES,
    ApprovalStatus,
    ApprovalType,
    WorkflowState,
)

_approval_provider = MockApprovalProvider()


def _settings_limits() -> tuple[int, int, float]:
    s = get_settings()
    return (
        int(s.workflow_max_tool_calls),
        int(s.workflow_max_retries),
        float(s.workflow_step_timeout_seconds),
    )


def to_view(wf: WorkflowInstance) -> WorkflowView:
    return WorkflowView(
        id=wf.id,
        state=WorkflowState(wf.state),
        subject=wf.subject,
        body=wf.body,
        from_email=wf.from_email,
        context=get_context(wf),
        error_message=wf.error_message,
        retry_count=wf.retry_count,
        tool_call_count=wf.tool_call_count,
        approvals=[
            ApprovalView(
                id=a.id,
                approval_type=ApprovalType(a.approval_type),
                status=ApprovalStatus(a.status),
                summary=a.summary,
                decision_note=a.decision_note,
                external_ref=a.external_ref,
                replan_requested=bool(a.replan_requested),
                created_at=a.created_at,
                decided_at=a.decided_at,
            )
            for a in sorted(wf.approvals, key=lambda x: x.id)
        ],
        transitions=[
            TransitionView(
                from_state=WorkflowState(t.from_state),
                to_state=WorkflowState(t.to_state),
                reason=t.reason,
                created_at=t.created_at,
            )
            for t in sorted(wf.transitions, key=lambda x: x.id)
        ],
        created_at=wf.created_at,
        updated_at=wf.updated_at,
        email_requires_approval=True,
    )


class WorkflowEngine:
    """Persistent Python state machine — not LangGraph."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.max_tools, self.max_retries, self.step_timeout = _settings_limits()

    async def create(self, request: WorkflowCreateRequest) -> WorkflowView:
        wf = WorkflowInstance(
            state=WorkflowState.RECEIVED.value,
            subject=request.subject or "",
            body=request.body,
            from_email=request.from_email,
            context_json="{}",
            retry_count=0,
            tool_call_count=0,
        )
        self.db.add(wf)
        self.db.flush()
        record_audit(
            event_type="workflow.created",
            payload={"subject": wf.subject, "from_email": wf.from_email},
            workflow_id=wf.id,
            db=self.db,
        )
        self.db.commit()
        if request.auto_advance:
            return await self.advance(wf.id)
        return to_view(load_workflow(self.db, wf.id))

    def get(self, workflow_id: int) -> WorkflowView:
        return to_view(load_workflow(self.db, workflow_id))

    async def advance(self, workflow_id: int) -> WorkflowView:
        """Run automatic steps until blocked on approval or terminal."""
        wf = load_workflow(self.db, workflow_id)
        guard = 0
        while WorkflowState(wf.state) not in TERMINAL_STATES and guard < 12:
            guard += 1
            state = WorkflowState(wf.state)
            if state == WorkflowState.RECEIVED:
                self._step_start_analyzing(wf)
            elif state == WorkflowState.ANALYZING:
                await self._step_analyze(wf)
            elif state == WorkflowState.INVESTIGATING:
                self._step_after_investigate(wf)
            elif state == WorkflowState.REPLANNING:
                await self._step_replan(wf)
            elif state == WorkflowState.DRAFTING:
                self._step_draft(wf)
            elif state in (
                WorkflowState.AWAITING_DECISION_APPROVAL,
                WorkflowState.AWAITING_EMAIL_APPROVAL,
            ):
                break
            else:
                break
            self.db.commit()
            wf = load_workflow(self.db, workflow_id)
        return to_view(wf)

    async def decide_approval(
        self, workflow_id: int, approval_id: int, body: ApprovalDecideRequest
    ) -> WorkflowView:
        wf = load_workflow(self.db, workflow_id)
        approval = next((a for a in wf.approvals if a.id == approval_id), None)
        if approval is None:
            raise KeyError(f"Approval not found: {approval_id}")
        if approval.status != ApprovalStatus.PENDING.value:
            raise ValueError("Approval already decided")
        if body.decision not in (ApprovalStatus.APPROVED, ApprovalStatus.REJECTED):
            raise ValueError("decision must be approved or rejected")

        approval.status = body.decision.value
        approval.decision_note = body.note
        approval.replan_requested = bool(body.request_replan)
        approval.decided_at = utcnow()
        record_audit(
            event_type="workflow.approval_decided",
            payload={
                "approval_id": approval.id,
                "approval_type": approval.approval_type,
                "decision": body.decision.value,
                "request_replan": body.request_replan,
                "note": body.note,
            },
            workflow_id=wf.id,
            db=self.db,
        )

        state = WorkflowState(wf.state)
        if body.decision == ApprovalStatus.REJECTED:
            transition(self.db, wf, WorkflowState.CANCELLED, reason="approval rejected")
            self.db.commit()
            return to_view(load_workflow(self.db, workflow_id))

        if approval.approval_type == ApprovalType.DECISION.value:
            if state != WorkflowState.AWAITING_DECISION_APPROVAL:
                raise ValueError("Decision approval not expected in current state")
            if body.request_replan:
                transition(
                    self.db, wf, WorkflowState.REPLANNING, reason="approved with replan"
                )
            else:
                transition(
                    self.db,
                    wf,
                    WorkflowState.DRAFTING,
                    reason="decision approved; generate email draft",
                )
        elif approval.approval_type == ApprovalType.EMAIL.value:
            # Hard separation: never approve/send email while a decision is unresolved
            if pending_approval(wf, ApprovalType.DECISION) is not None:
                raise ValueError(
                    "Cannot approve email while a decision approval is still pending"
                )
            if state != WorkflowState.AWAITING_EMAIL_APPROVAL:
                raise ValueError("Email approval not expected in current state")
            self._send_approved_email(wf, approval_id=approval.id)
        else:
            raise ValueError(f"Unknown approval type: {approval.approval_type}")

        self.db.commit()
        return await self.advance(workflow_id)

    async def readonly_investigate(
        self, workflow_id: int, body: ReadonlyInvestigateRequest
    ) -> dict[str, Any]:
        """Independent read-only investigation while approval is pending."""
        wf = load_workflow(self.db, workflow_id)
        state = WorkflowState(wf.state)
        if state not in (
            WorkflowState.AWAITING_DECISION_APPROVAL,
            WorkflowState.AWAITING_EMAIL_APPROVAL,
        ):
            raise ValueError(
                f"Read-only investigate not allowed in state {state.value}"
            )

        if body.tool not in READ_ONLY_TOOLS:
            raise PermissionError(
                f"Tool {body.tool} is not read-only; blocked while approval pending"
            )

        if wf.tool_call_count >= self.max_tools:
            raise RuntimeError("Tool execution limit reached for this workflow")

        outcome = await get_executor().execute(body.tool, body.arguments)
        wf.tool_call_count += 1
        record_audit(
            event_type="workflow.readonly_investigate",
            payload={
                "tool": body.tool,
                "arguments": body.arguments,
                "ok": outcome.ok,
                "error": outcome.error,
            },
            workflow_id=wf.id,
            db=self.db,
        )
        self.db.commit()
        return {
            "workflow_id": wf.id,
            "state": wf.state,
            "tool": body.tool,
            "ok": outcome.ok,
            "result": outcome.result,
            "error": outcome.error,
            "note": "read_only_independent_investigation",
        }

    def _fail(self, wf: WorkflowInstance, message: str) -> None:
        wf.error_message = message
        try:
            transition(self.db, wf, WorkflowState.FAILED, reason=message)
        except ValueError:
            wf.state = WorkflowState.FAILED.value
        record_audit(
            event_type="workflow.failed",
            payload={"error": message},
            workflow_id=wf.id,
            db=self.db,
        )

    def _step_start_analyzing(self, wf: WorkflowInstance) -> None:
        transition(self.db, wf, WorkflowState.ANALYZING, reason="start analysis")

    async def _step_analyze(self, wf: WorkflowInstance) -> None:
        started = time.perf_counter()
        try:
            result = await analyze_and_investigate(
                InquiryAnalyzeRequest(
                    subject=wf.subject,
                    body=wf.body,
                    from_email=wf.from_email,
                    execute_tools=True,
                )
            )
            elapsed = time.perf_counter() - started
            if elapsed > self.step_timeout:
                record_audit(
                    event_type="workflow.step_timeout",
                    payload={"step": "analyze", "elapsed": elapsed},
                    workflow_id=wf.id,
                    db=self.db,
                )

            ctx = get_context(wf)
            payload = result.model_dump(mode="json")
            tool_results = payload.get("tool_results") or []
            if len(tool_results) > self.max_tools:
                tool_results = tool_results[: self.max_tools]
                payload["tool_results"] = tool_results
                payload.setdefault("review_flags", []).append(
                    {
                        "code": "tool_limit_truncated",
                        "message": f"Truncated to {self.max_tools} tool results",
                        "severity": "review",
                    }
                )
                payload["needs_human_review"] = True

            wf.tool_call_count += len(tool_results)
            ctx["last_analysis"] = payload
            set_context(wf, ctx)
            transition(
                self.db, wf, WorkflowState.INVESTIGATING, reason="analysis complete"
            )
        except Exception as exc:  # noqa: BLE001
            if wf.retry_count < self.max_retries:
                wf.retry_count += 1
                record_audit(
                    event_type="workflow.retry",
                    payload={
                        "step": "analyze",
                        "attempt": wf.retry_count,
                        "error": str(exc),
                    },
                    workflow_id=wf.id,
                    db=self.db,
                )
                return
            self._fail(wf, f"analyze failed: {exc}")

    def _step_after_investigate(self, wf: WorkflowInstance) -> None:
        ctx = get_context(wf)
        analysis = ctx.get("last_analysis") or {}
        needs_review = bool(analysis.get("needs_human_review"))
        if needs_review:
            if pending_approval(wf, ApprovalType.DECISION) is None:
                flags = analysis.get("review_flags") or []
                summary = "Decision approval required: " + ", ".join(
                    f.get("code", "review") for f in flags
                )
                ref = _approval_provider.request_approval(
                    summary=summary, approval_type=ApprovalType.DECISION.value
                )
                create_approval(
                    self.db,
                    wf,
                    approval_type=ApprovalType.DECISION,
                    summary=summary,
                    external_ref=ref,
                )
            transition(
                self.db,
                wf,
                WorkflowState.AWAITING_DECISION_APPROVAL,
                reason="human review required by validation gates",
            )
            return

        transition(
            self.db,
            wf,
            WorkflowState.DRAFTING,
            reason="draft email before mandatory email approval",
        )

    def _request_email_approval(self, wf: WorkflowInstance) -> None:
        if pending_approval(wf, ApprovalType.EMAIL) is not None:
            return
        from app.services.email_drafts import current_draft

        draft = current_draft(self.db, wf.id)
        hash_note = f" hash={draft.content_hash[:12]}" if draft else ""
        summary = (
            f"Approve outbound email for workflow {wf.id}: {wf.subject}{hash_note}"
        )
        ref = _approval_provider.request_approval(
            summary=summary, approval_type=ApprovalType.EMAIL.value
        )
        create_approval(
            self.db,
            wf,
            approval_type=ApprovalType.EMAIL,
            summary=summary,
            external_ref=ref,
        )

    def _step_draft(self, wf: WorkflowInstance) -> None:
        from app.services.email_drafts import create_draft_version, current_draft

        try:
            if current_draft(self.db, wf.id) is None:
                create_draft_version(self.db, wf)
            transition(
                self.db,
                wf,
                WorkflowState.AWAITING_EMAIL_APPROVAL,
                reason="draft ready; email approval required",
            )
            self._request_email_approval(wf)
        except Exception as exc:  # noqa: BLE001
            self._fail(wf, f"draft failed: {exc}")

    def _send_approved_email(self, wf: WorkflowInstance, *, approval_id: int) -> None:
        from app.providers.email import get_email_provider
        from app.services.email_drafts import (
            current_draft,
            mark_draft_approved,
            mark_draft_sent,
        )

        draft = current_draft(self.db, wf.id)
        if draft is None:
            raise ValueError("No current email draft to send")
        if draft.sent:
            raise ValueError("duplicate_send_prevented: draft already sent")

        mark_draft_approved(self.db, draft)
        provider = get_email_provider()
        result = provider.send_approved_email(
            to=draft.to_email,
            subject=draft.subject,
            body=draft.body,
            content_hash=draft.content_hash,
            approved_hash=draft.approved_hash or "",
        )
        ctx = get_context(wf)
        if not result.ok:
            record_audit(
                event_type="email.send_failed",
                payload={"error": result.error, "approval_id": approval_id},
                workflow_id=wf.id,
                db=self.db,
            )
            raise ValueError(result.error or "email send failed")

        mark_draft_sent(self.db, draft, result.message_id or "")
        ctx["email_approved"] = True
        ctx["email_send_status"] = "sent"
        ctx["email_message_id"] = result.message_id
        ctx["email_provider"] = result.provider
        set_context(wf, ctx)
        record_audit(
            event_type="email.sent",
            payload={
                "message_id": result.message_id,
                "content_hash": draft.content_hash,
                "provider": result.provider,
            },
            workflow_id=wf.id,
            db=self.db,
        )
        transition(
            self.db,
            wf,
            WorkflowState.COMPLETED,
            reason="email approved and sent via provider",
        )

    def invalidate_email_approval_for_edit(self, workflow_id: int) -> WorkflowView:
        """Draft edit invalidates pending/approved email approval and returns to DRAFTING."""
        from app.services.email_drafts import create_draft_version, current_draft
        from app.workflow.states import ApprovalStatus as AS

        wf = load_workflow(self.db, workflow_id)
        state = WorkflowState(wf.state)
        if state not in (
            WorkflowState.AWAITING_EMAIL_APPROVAL,
            WorkflowState.DRAFTING,
        ):
            raise ValueError(f"Cannot edit draft in state {state.value}")

        for a in wf.approvals:
            if (
                a.approval_type == ApprovalType.EMAIL.value
                and a.status == AS.PENDING.value
            ):
                a.status = AS.REJECTED.value
                a.decision_note = "invalidated_by_draft_edit"
                a.decided_at = utcnow()

        if state == WorkflowState.AWAITING_EMAIL_APPROVAL:
            transition(
                self.db,
                wf,
                WorkflowState.DRAFTING,
                reason="draft edited; email approval invalidated",
            )

        prev = current_draft(self.db, wf.id)
        create_draft_version(
            self.db,
            wf,
            template_id=prev.template_id if prev else None,
            to_email=prev.to_email if prev else None,
            subject=prev.subject if prev else None,
            body=(prev.body + "\n") if prev else None,
        )
        record_audit(
            event_type="email.draft_edit_invalidated_approval",
            payload={"workflow_id": wf.id},
            workflow_id=wf.id,
            db=self.db,
        )
        self.db.commit()
        return to_view(load_workflow(self.db, workflow_id))

    async def _step_replan(self, wf: WorkflowInstance) -> None:
        """Replan must re-run gates; cannot bypass approvals or auto-send email."""
        try:
            result = await analyze_and_investigate(
                InquiryAnalyzeRequest(
                    subject=wf.subject,
                    body=wf.body + "\n\n[replan requested after human approval]",
                    from_email=wf.from_email,
                    execute_tools=True,
                )
            )
            ctx = get_context(wf)
            payload = result.model_dump(mode="json")
            payload["email_requires_approval"] = True
            added = len(payload.get("tool_results") or [])
            wf.tool_call_count += added
            if wf.tool_call_count > self.max_tools:
                payload["needs_human_review"] = True
                payload.setdefault("review_flags", []).append(
                    {
                        "code": "tool_limit_exceeded",
                        "message": "Tool execution limit exceeded during replan",
                        "severity": "review",
                    }
                )
            ctx["last_analysis"] = payload
            ctx["replan_count"] = int(ctx.get("replan_count") or 0) + 1
            set_context(wf, ctx)
            record_audit(
                event_type="workflow.replan",
                payload={"replan_count": ctx["replan_count"]},
                workflow_id=wf.id,
                db=self.db,
            )
            transition(
                self.db, wf, WorkflowState.INVESTIGATING, reason="replan analysis done"
            )
        except Exception as exc:  # noqa: BLE001
            if wf.retry_count < self.max_retries:
                wf.retry_count += 1
                return
            self._fail(wf, f"replan failed: {exc}")
