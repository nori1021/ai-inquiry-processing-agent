from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


class UserRole(str, Enum):
    REQUESTER = "requester"
    AFFECTED_USER = "affected_user"
    MANAGER = "manager"
    TECHNICAL_CONTACT = "technical_contact"
    OTHER = "other"
    UNKNOWN = "unknown"


class InvestigationNeed(str, Enum):
    REQUIRED = "REQUIRED"
    NOT_REQUIRED = "NOT_REQUIRED"
    UNCERTAIN = "UNCERTAIN"


class InquiryAnalyzeRequest(BaseModel):
    subject: str = ""
    body: str = Field(..., min_length=1)
    from_email: Optional[str] = None
    execute_tools: bool = True


class ExtractedUser(BaseModel):
    email: Optional[str] = None
    display_name: Optional[str] = None
    role: UserRole = UserRole.UNKNOWN
    reason: str = ""
    investigate: InvestigationNeed = InvestigationNeed.UNCERTAIN


class ExtractedCompany(BaseModel):
    name: Optional[str] = None
    domain: Optional[str] = None
    company_id: Optional[str] = None
    source: str = "inquiry_text"
    investigate: InvestigationNeed = InvestigationNeed.UNCERTAIN


class PlannedToolCall(BaseModel):
    tool: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    reason: str = ""
    need: InvestigationNeed = InvestigationNeed.REQUIRED


class InquiryAnalysis(BaseModel):
    """Structured AI output — validated by Pydantic before any tool execution."""

    summary: str = ""
    intent: str = ""
    category: str = "general"
    users: list[ExtractedUser] = Field(default_factory=list)
    companies: list[ExtractedCompany] = Field(default_factory=list)
    planned_tools: list[PlannedToolCall] = Field(default_factory=list)
    confidence: Optional[float] = None
    notes: list[str] = Field(default_factory=list)
    raw_provider: str = "unknown"

    @field_validator("confidence")
    @classmethod
    def confidence_range(cls, value: Optional[float]) -> Optional[float]:
        if value is None:
            return None
        if not isinstance(value, (int, float)):
            raise ValueError("confidence must be numeric")
        if value < 0 or value > 1:
            raise ValueError("confidence must be between 0 and 1")
        return float(value)


class ReviewFlag(BaseModel):
    code: str
    message: str
    severity: str = "review"  # review | block


class InvestigationPlanItem(BaseModel):
    target_type: str  # user | company | domain | knowledge
    target: str
    need: InvestigationNeed
    role: Optional[UserRole] = None
    reason: str = ""


class ToolCallOutcome(BaseModel):
    tool: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    ok: bool
    result: Any = None
    error: Optional[str] = None
    provider: str = ""
    duration_ms: float = 0.0
    status: str = "ok"  # ok | error


class RagReference(BaseModel):
    source: str
    id: Optional[str] = None
    text: str = ""


class InquiryAnalyzeResponse(BaseModel):
    analysis: InquiryAnalysis
    investigation_plan: list[InvestigationPlanItem]
    selected_tools: list[PlannedToolCall]
    tool_results: list[ToolCallOutcome] = Field(default_factory=list)
    rag_references: list[RagReference] = Field(default_factory=list)
    needs_human_review: bool
    review_flags: list[ReviewFlag] = Field(default_factory=list)
    email_requires_approval: bool = True
    provider: str
    ai_mode: str = "unknown"
    # actual_llm | mock_heuristic | mock_fallback | ollama_unavailable | ollama_error
    provider_status: str = "ok"  # ok | unavailable | error | mock
    provider_error: Optional[str] = None
    inference_metrics: dict[str, Any] = Field(default_factory=dict)
