from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.audit import AuditEvent
from app.models.workflow import WorkflowInstance
from app.schemas.workflow import (
    ApprovalDecideRequest,
    ReadonlyInvestigateRequest,
    WorkflowCreateRequest,
    WorkflowView,
)
from app.workflow.engine import WorkflowEngine
from app.workflow.states import ApprovalStatus

router = APIRouter()


@router.post("", response_model=WorkflowView)
async def create_workflow(
    body: WorkflowCreateRequest, db: Session = Depends(get_db)
) -> WorkflowView:
    engine = WorkflowEngine(db)
    return await engine.create(body)


@router.get("", response_model=list[WorkflowView])
def list_workflows(db: Session = Depends(get_db), limit: int = 50) -> list[WorkflowView]:
    rows = (
        db.query(WorkflowInstance)
        .order_by(WorkflowInstance.id.desc())
        .limit(min(limit, 200))
        .all()
    )
    engine = WorkflowEngine(db)
    return [engine.get(r.id) for r in rows]


@router.get("/{workflow_id}", response_model=WorkflowView)
def get_workflow(workflow_id: int, db: Session = Depends(get_db)) -> WorkflowView:
    try:
        return WorkflowEngine(db).get(workflow_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{workflow_id}/advance", response_model=WorkflowView)
async def advance_workflow(
    workflow_id: int, db: Session = Depends(get_db)
) -> WorkflowView:
    try:
        return await WorkflowEngine(db).advance(workflow_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{workflow_id}/approvals/{approval_id}/decide", response_model=WorkflowView)
async def decide_approval(
    workflow_id: int,
    approval_id: int,
    body: ApprovalDecideRequest,
    db: Session = Depends(get_db),
) -> WorkflowView:
    if body.decision not in (ApprovalStatus.APPROVED, ApprovalStatus.REJECTED):
        raise HTTPException(status_code=400, detail="decision must be approved or rejected")
    try:
        return await WorkflowEngine(db).decide_approval(workflow_id, approval_id, body)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{workflow_id}/investigate-readonly")
async def readonly_investigate(
    workflow_id: int,
    body: ReadonlyInvestigateRequest,
    db: Session = Depends(get_db),
):
    try:
        return await WorkflowEngine(db).readonly_investigate(workflow_id, body)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (ValueError, PermissionError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{workflow_id}/audit")
def workflow_audit(workflow_id: int, db: Session = Depends(get_db)):
    rows = (
        db.query(AuditEvent)
        .filter(AuditEvent.workflow_id == workflow_id)
        .order_by(AuditEvent.id.asc())
        .all()
    )
    return [
        {
            "id": r.id,
            "event_type": r.event_type,
            "payload_json": r.payload_json,
            "created_at": r.created_at,
        }
        for r in rows
    ]
