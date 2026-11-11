from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.providers.audit import record_audit
from app.schemas.workflow import ApprovalDecideRequest
from app.workflow.engine import WorkflowEngine
from app.workflow.repository import load_workflow
from app.workflow.states import ApprovalStatus

router = APIRouter()


class TeamsCallbackPayload(BaseModel):
    workflow_id: int
    approval_id: int
    decision: ApprovalStatus
    note: str = ""
    request_replan: bool = False
    external_ref: str | None = None


class TeamsOutboundRequest(BaseModel):
    workflow_id: int
    approval_id: int
    summary: str = Field(default="")


def _check_secret(x_teams_secret: str | None) -> None:
    settings = get_settings()
    expected = settings.teams_callback_secret or "dev-teams-callback-secret"
    if not x_teams_secret or x_teams_secret != expected:
        raise HTTPException(status_code=401, detail="Invalid Teams callback secret")


@router.post("/callbacks/approval")
async def teams_approval_callback(
    body: TeamsCallbackPayload,
    db: Session = Depends(get_db),
    x_teams_secret: str | None = Header(default=None),
):
    """
    Power Automate / Teams webhook callback hook.
    Auth via X-Teams-Secret header. Works fully with mock provider locally.
    """
    _check_secret(x_teams_secret)
    try:
        wf = load_workflow(db, body.workflow_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if body.external_ref:
        match = next(
            (a for a in wf.approvals if a.id == body.approval_id),
            None,
        )
        if match and match.external_ref and match.external_ref != body.external_ref:
            raise HTTPException(status_code=400, detail="external_ref mismatch")

    record_audit(
        event_type="teams.callback_received",
        payload=body.model_dump(mode="json"),
        workflow_id=body.workflow_id,
        db=db,
    )
    db.commit()

    try:
        view = await WorkflowEngine(db).decide_approval(
            body.workflow_id,
            body.approval_id,
            ApprovalDecideRequest(
                decision=body.decision,
                note=body.note or "via teams callback",
                request_replan=body.request_replan,
            ),
        )
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"ok": True, "workflow": view}


@router.post("/mock/notify")
def teams_mock_notify(
    body: TeamsOutboundRequest,
    db: Session = Depends(get_db),
    x_teams_secret: str | None = Header(default=None),
):
    """Simulate sending an Adaptive Card / Power Automate notification (local mock)."""
    _check_secret(x_teams_secret)
    settings = get_settings()
    record_audit(
        event_type="teams.mock_notify",
        payload={
            "workflow_id": body.workflow_id,
            "approval_id": body.approval_id,
            "summary": body.summary,
            "webhook_configured": bool(settings.teams_webhook_url),
            "mode": "mock",
        },
        workflow_id=body.workflow_id,
        db=db,
    )
    db.commit()
    return {
        "ok": True,
        "mode": "mock",
        "message": "Notification recorded locally; real M365 webhook optional",
        "callback_path": "/api/v1/teams/callbacks/approval",
    }
