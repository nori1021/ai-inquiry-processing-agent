from __future__ import annotations

from app.schemas.inquiry import (
    InquiryAnalysis,
    InvestigationNeed,
    InvestigationPlanItem,
    UserRole,
)


def build_investigation_plan(analysis: InquiryAnalysis) -> list[InvestigationPlanItem]:
    """Deterministic plan derived from structured AI analysis."""
    items: list[InvestigationPlanItem] = []

    for user in analysis.users:
        target = user.email or user.display_name or "unknown_user"
        need = user.investigate
        if need == InvestigationNeed.UNCERTAIN and user.role == UserRole.UNKNOWN:
            need = InvestigationNeed.UNCERTAIN
        items.append(
            InvestigationPlanItem(
                target_type="user",
                target=target,
                need=need,
                role=user.role,
                reason=user.reason or f"role={user.role.value}",
            )
        )

    for company in analysis.companies:
        target = company.domain or company.company_id or company.name or "unknown_company"
        items.append(
            InvestigationPlanItem(
                target_type="company",
                target=target,
                need=company.investigate,
                reason=company.source,
            )
        )

    # Knowledge / past inquiries when intent is actionable
    if analysis.intent:
        items.append(
            InvestigationPlanItem(
                target_type="knowledge",
                target=analysis.intent,
                need=InvestigationNeed.REQUIRED,
                reason="intent-linked knowledge search",
            )
        )

    return items
