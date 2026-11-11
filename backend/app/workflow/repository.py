from __future__ import annotations

import json
from typing import Any, Optional

from sqlalchemy.orm import Session, joinedload

from app.models.audit import utcnow
from app.models.workflow import ApprovalRequest, WorkflowInstance, WorkflowTransition
from app.providers.audit import record_audit
from app.workflow.states import (
    ApprovalStatus,
    ApprovalType,
    WorkflowState,
    assert_transition,
)


def load_workflow(db: Session, workflow_id: int) -> WorkflowInstance:
    wf = (
        db.query(WorkflowInstance)
        .options(
            joinedload(WorkflowInstance.approvals),
            joinedload(WorkflowInstance.transitions),
        )
        .filter(WorkflowInstance.id == workflow_id)
        .one_or_none()
    )
    if wf is None:
        raise KeyError(f"Workflow not found: {workflow_id}")
    return wf


def get_context(wf: WorkflowInstance) -> dict[str, Any]:
    try:
        return json.loads(wf.context_json or "{}")
    except json.JSONDecodeError:
        return {}


def set_context(wf: WorkflowInstance, context: dict[str, Any]) -> None:
    wf.context_json = json.dumps(context, default=str)


def transition(
    db: Session,
    wf: WorkflowInstance,
    new_state: WorkflowState,
    *,
    reason: str,
) -> None:
    current = WorkflowState(wf.state)
    assert_transition(current, new_state)
    db.add(
        WorkflowTransition(
            workflow_id=wf.id,
            from_state=current.value,
            to_state=new_state.value,
            reason=reason,
        )
    )
    wf.state = new_state.value
    wf.updated_at = utcnow()
    record_audit(
        event_type="workflow.transition",
        payload={
            "from": current.value,
            "to": new_state.value,
            "reason": reason,
        },
        workflow_id=wf.id,
        db=db,
    )


def create_approval(
    db: Session,
    wf: WorkflowInstance,
    *,
    approval_type: ApprovalType,
    summary: str,
    external_ref: str,
) -> ApprovalRequest:
    row = ApprovalRequest(
        workflow_id=wf.id,
        approval_type=approval_type.value,
        status=ApprovalStatus.PENDING.value,
        summary=summary,
        external_ref=external_ref,
        replan_requested=False,
    )
    db.add(row)
    db.flush()
    record_audit(
        event_type="workflow.approval_requested",
        payload={
            "approval_id": row.id,
            "approval_type": approval_type.value,
            "external_ref": external_ref,
            "summary": summary,
        },
        workflow_id=wf.id,
        db=db,
    )
    return row


def pending_approval(
    wf: WorkflowInstance, approval_type: Optional[ApprovalType] = None
) -> Optional[ApprovalRequest]:
    for a in wf.approvals:
        if a.status != ApprovalStatus.PENDING.value:
            continue
        if approval_type and a.approval_type != approval_type.value:
            continue
        return a
    return None
