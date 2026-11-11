from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.email import EmailDraftUpdateRequest, EmailDraftView, EmailTemplateView
from app.services.email_drafts import (
    create_draft_version,
    current_draft,
    list_templates,
)
from app.models.audit import utcnow
from app.providers.audit import record_audit
from app.workflow.engine import WorkflowEngine
from app.workflow.repository import load_workflow, transition
from app.workflow.states import ApprovalStatus, ApprovalType, WorkflowState

router = APIRouter()


def _to_view(draft) -> EmailDraftView:
    return EmailDraftView(
        id=draft.id,
        workflow_id=draft.workflow_id,
        version=draft.version,
        template_id=draft.template_id,
        to_email=draft.to_email,
        subject=draft.subject,
        body=draft.body,
        content_hash=draft.content_hash,
        approved_hash=draft.approved_hash,
        is_current=draft.is_current,
        sent=draft.sent,
        sent_at=draft.sent_at,
        provider_message_id=draft.provider_message_id,
    )


@router.get("/templates", response_model=list[EmailTemplateView])
def get_templates() -> list[EmailTemplateView]:
    return [EmailTemplateView(template_id=t) for t in list_templates()]


@router.get("/workflows/{workflow_id}/draft", response_model=EmailDraftView)
def get_draft(workflow_id: int, db: Session = Depends(get_db)) -> EmailDraftView:
    draft = current_draft(db, workflow_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="No current draft")
    return _to_view(draft)


@router.put("/workflows/{workflow_id}/draft", response_model=EmailDraftView)
def update_draft(
    workflow_id: int,
    body: EmailDraftUpdateRequest,
    db: Session = Depends(get_db),
) -> EmailDraftView:
    """Edit draft: invalidate email approval, bump version, stay/return to DRAFTING."""
    try:
        wf = load_workflow(db, workflow_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    state = WorkflowState(wf.state)
    if state not in (
        WorkflowState.AWAITING_EMAIL_APPROVAL,
        WorkflowState.DRAFTING,
    ):
        raise HTTPException(
            status_code=400, detail=f"Cannot edit draft in state {state.value}"
        )

    prev = current_draft(db, workflow_id)
    if prev and prev.sent:
        raise HTTPException(status_code=400, detail="Cannot edit a sent draft")

    # Invalidate pending email approvals
    for a in wf.approvals:
        if (
            a.approval_type == ApprovalType.EMAIL.value
            and a.status == ApprovalStatus.PENDING.value
        ):
            a.status = ApprovalStatus.REJECTED.value
            a.decision_note = "invalidated_by_draft_edit"
            a.decided_at = utcnow()

    if state == WorkflowState.AWAITING_EMAIL_APPROVAL:
        transition(
            db,
            wf,
            WorkflowState.DRAFTING,
            reason="draft edited; email approval invalidated",
        )

    try:
        draft = create_draft_version(
            db,
            wf,
            template_id=body.template_id or (prev.template_id if prev else None),
            to_email=body.to_email or (prev.to_email if prev else None),
            subject=body.subject if body.subject is not None else (prev.subject if prev else None),
            body=body.body if body.body is not None else (prev.body if prev else None),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    record_audit(
        event_type="email.draft_updated",
        payload={"draft_id": draft.id, "version": draft.version},
        workflow_id=workflow_id,
        db=db,
    )
    db.commit()
    return _to_view(draft)


@router.post("/workflows/{workflow_id}/draft/submit-for-approval")
async def submit_draft_for_approval(
    workflow_id: int, db: Session = Depends(get_db)
):
    """After edit, advance DRAFTING → AWAITING_EMAIL_APPROVAL with new approval."""
    try:
        return await WorkflowEngine(db).advance(workflow_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
