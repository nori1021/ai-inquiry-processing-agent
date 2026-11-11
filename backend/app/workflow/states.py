from __future__ import annotations

from enum import Enum


class WorkflowState(str, Enum):
    RECEIVED = "RECEIVED"
    ANALYZING = "ANALYZING"
    INVESTIGATING = "INVESTIGATING"
    AWAITING_DECISION_APPROVAL = "AWAITING_DECISION_APPROVAL"
    REPLANNING = "REPLANNING"
    DRAFTING = "DRAFTING"
    AWAITING_EMAIL_APPROVAL = "AWAITING_EMAIL_APPROVAL"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


TERMINAL_STATES = frozenset(
    {
        WorkflowState.COMPLETED,
        WorkflowState.FAILED,
        WorkflowState.CANCELLED,
    }
)

# Explicit allowlist of server-side transitions
ALLOWED_TRANSITIONS: dict[WorkflowState, frozenset[WorkflowState]] = {
    WorkflowState.RECEIVED: frozenset({WorkflowState.ANALYZING, WorkflowState.CANCELLED, WorkflowState.FAILED}),
    WorkflowState.ANALYZING: frozenset(
        {WorkflowState.INVESTIGATING, WorkflowState.FAILED, WorkflowState.CANCELLED}
    ),
    WorkflowState.INVESTIGATING: frozenset(
        {
            WorkflowState.AWAITING_DECISION_APPROVAL,
            WorkflowState.DRAFTING,
            WorkflowState.FAILED,
            WorkflowState.CANCELLED,
        }
    ),
    WorkflowState.AWAITING_DECISION_APPROVAL: frozenset(
        {
            WorkflowState.REPLANNING,
            WorkflowState.INVESTIGATING,
            WorkflowState.DRAFTING,
            WorkflowState.CANCELLED,
            WorkflowState.FAILED,
        }
    ),
    WorkflowState.REPLANNING: frozenset(
        {WorkflowState.INVESTIGATING, WorkflowState.FAILED, WorkflowState.CANCELLED}
    ),
    WorkflowState.DRAFTING: frozenset(
        {
            WorkflowState.AWAITING_EMAIL_APPROVAL,
            WorkflowState.FAILED,
            WorkflowState.CANCELLED,
        }
    ),
    WorkflowState.AWAITING_EMAIL_APPROVAL: frozenset(
        {
            WorkflowState.COMPLETED,
            WorkflowState.CANCELLED,
            WorkflowState.FAILED,
            WorkflowState.DRAFTING,  # draft edit invalidates approval
        }
    ),
    WorkflowState.COMPLETED: frozenset(),
    WorkflowState.FAILED: frozenset(),
    WorkflowState.CANCELLED: frozenset(),
}


class ApprovalType(str, Enum):
    DECISION = "decision"
    EMAIL = "email"


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


# Tools allowed as independent read-only while an unrelated approval is pending
READ_ONLY_TOOLS = frozenset(
    {
        "lookup_ldap_user",
        "lookup_gac_user",
        "lookup_ldap_company",
        "lookup_gac_company_users",
        "get_ldap_user",
        "get_gac_user",
        "check_ldap_registration",
        "check_gac_registration",
        "check_ldap_gac_registration",
        "find_similar_domains",
        "search_past_inquiries",
        "search_knowledge_base",
        "get_reply_template",
        "get_inquiry_history",
    }
)


def assert_transition(current: WorkflowState, new: WorkflowState) -> None:
    allowed = ALLOWED_TRANSITIONS.get(current, frozenset())
    if new not in allowed:
        raise ValueError(f"Illegal transition: {current.value} → {new.value}")
