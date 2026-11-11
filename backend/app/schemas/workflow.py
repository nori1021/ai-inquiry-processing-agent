from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.workflow.states import ApprovalStatus, ApprovalType, WorkflowState


class WorkflowCreateRequest(BaseModel):
    subject: str = ""
    body: str = Field(..., min_length=1)
    from_email: Optional[str] = None
    auto_advance: bool = True


class ApprovalDecideRequest(BaseModel):
    decision: ApprovalStatus  # approved | rejected
    note: str = ""
    request_replan: bool = False


class ReadonlyInvestigateRequest(BaseModel):
    tool: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class ApprovalView(BaseModel):
    id: int
    approval_type: ApprovalType
    status: ApprovalStatus
    summary: str
    decision_note: Optional[str] = None
    external_ref: Optional[str] = None
    replan_requested: bool = False
    created_at: Optional[datetime] = None
    decided_at: Optional[datetime] = None


class TransitionView(BaseModel):
    from_state: WorkflowState
    to_state: WorkflowState
    reason: str
    created_at: Optional[datetime] = None


class WorkflowView(BaseModel):
    id: int
    state: WorkflowState
    subject: str
    body: str
    from_email: Optional[str] = None
    context: dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None
    retry_count: int = 0
    tool_call_count: int = 0
    approvals: list[ApprovalView] = Field(default_factory=list)
    transitions: list[TransitionView] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    email_requires_approval: bool = True
