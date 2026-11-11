"""Dynamic tool selection — registered tools only."""

from __future__ import annotations

import re
from typing import Any

from app.registry import get_registry
from app.schemas.inquiry import (
    InquiryAnalysis,
    InvestigationNeed,
    InvestigationPlanItem,
    PlannedToolCall,
)
from app.services.normalization import email_domain, normalize_email

_PASSWORD_OR_ACCESS = re.compile(
    r"password_reset|password_reset_failed|access_request|access_issue",
    re.IGNORECASE,
)
_DIR_REASON = re.compile(
    r"ldap|gac|registration|directory|identity\s*verif",
    re.IGNORECASE,
)


def directory_lookup_warranted(analysis: InquiryAnalysis) -> bool:
    """
    Password/access issues must not auto-run LDAP/GAC unless there is a valid reason
    (explicit registration/directory/identity need in intent/notes/summary/reasons).
    """
    intent = (analysis.intent or "").lower()
    blob = " ".join(
        [
            intent,
            analysis.summary or "",
            " ".join(analysis.notes or []),
            " ".join(u.reason or "" for u in analysis.users),
        ]
    )
    if _PASSWORD_OR_ACCESS.search(intent) or "password" in intent:
        return bool(_DIR_REASON.search(blob))
    if intent in ("gac_registration",) or "gac" in intent or "ldap" in intent:
        return True
    # Default: allow directory checks for other IT intents
    return True


def list_selectable_tools() -> list[dict[str, Any]]:
    tools = get_registry().list(enabled_only=True)
    return [
        {
            "name": t.name,
            "kind": t.kind.value,
            "description": t.description,
            "input_schema": t.input_schema,
            "allow_ai_selection": t.permissions.allow_ai_selection,
        }
        for t in tools
        if t.permissions.allow_ai_selection
    ]


def select_tools_for_investigation(
    analysis: InquiryAnalysis,
    plan: list[InvestigationPlanItem],
) -> list[PlannedToolCall]:
    """
    Merge AI planned tools with Python plan requirements.
    Only registered + AI-selectable tools are kept. Unknown names dropped.
    """
    registry = get_registry()
    allowed = {
        t.name
        for t in registry.list(enabled_only=True)
        if t.permissions.allow_ai_selection
    }

    selected: list[PlannedToolCall] = []
    seen: set[tuple[str, str]] = set()

    def _add(call: PlannedToolCall) -> None:
        if call.tool not in allowed:
            return
        # Only execute REQUIRED (and UNCERTAIN as soft — still selected for review path)
        if call.need == InvestigationNeed.NOT_REQUIRED:
            return
        key = (call.tool, str(sorted(call.arguments.items())))
        if key in seen:
            return
        seen.add(key)
        selected.append(call)

    allow_directory = directory_lookup_warranted(analysis)
    directory_tools = {
        "check_ldap_registration",
        "check_gac_registration",
        "check_ldap_gac_registration",
        "lookup_ldap_user",
        "lookup_gac_user",
        "get_ldap_user",
        "get_gac_user",
        "lookup_ldap_company",
        "lookup_gac_company_users",
    }

    for call in analysis.planned_tools:
        if call.tool not in allowed:
            continue
        if not allow_directory and call.tool in directory_tools:
            continue
        _add(call)

    # Ensure REQUIRED users/companies get core lookups even if AI omitted them
    for item in plan:
        if item.need != InvestigationNeed.REQUIRED:
            continue
        if (
            allow_directory
            and item.target_type == "user"
            and "@" in item.target
        ):
            email = normalize_email(item.target)
            _add(
                PlannedToolCall(
                    tool="check_ldap_registration",
                    arguments={"email": email},
                    reason="plan REQUIRED user → LDAP registration check",
                    need=InvestigationNeed.REQUIRED,
                )
            )
            _add(
                PlannedToolCall(
                    tool="check_gac_registration",
                    arguments={"email": email},
                    reason="plan REQUIRED user → GAC registration check",
                    need=InvestigationNeed.REQUIRED,
                )
            )
            domain = email_domain(email)
            if domain:
                _add(
                    PlannedToolCall(
                        tool="lookup_ldap_company",
                        arguments={"domain": domain},
                        reason="plan REQUIRED user domain → company",
                        need=InvestigationNeed.REQUIRED,
                    )
                )
        if allow_directory and item.target_type == "company":
            target = item.target
            if "." in target and "@" not in target:
                _add(
                    PlannedToolCall(
                        tool="lookup_ldap_company",
                        arguments={"domain": target},
                        reason="plan REQUIRED company domain",
                        need=InvestigationNeed.REQUIRED,
                    )
                )
                _add(
                    PlannedToolCall(
                        tool="lookup_gac_company_users",
                        arguments={"domain": target},
                        reason="plan REQUIRED company GAC users",
                        need=InvestigationNeed.REQUIRED,
                    )
                )
            else:
                _add(
                    PlannedToolCall(
                        tool="lookup_ldap_company",
                        arguments={"company_id": target},
                        reason="plan REQUIRED company id",
                        need=InvestigationNeed.REQUIRED,
                    )
                )
        if item.target_type == "knowledge":
            query = item.target.replace("_", " ")
            _add(
                PlannedToolCall(
                    tool="search_past_inquiries",
                    arguments={"query": query, "limit": 5},
                    reason="plan REQUIRED knowledge → past inquiries",
                    need=InvestigationNeed.REQUIRED,
                )
            )
            _add(
                PlannedToolCall(
                    tool="search_knowledge_base",
                    arguments={"query": query, "limit": 5},
                    reason="plan REQUIRED knowledge → KB",
                    need=InvestigationNeed.REQUIRED,
                )
            )

    return selected


def domains_for_similarity_check(analysis: InquiryAnalysis) -> list[str]:
    if not directory_lookup_warranted(analysis):
        return []
    domains: list[str] = []
    seen: set[str] = set()
    for company in analysis.companies:
        if company.domain and company.domain not in seen:
            if company.investigate == InvestigationNeed.NOT_REQUIRED:
                continue
            seen.add(company.domain)
            domains.append(company.domain)
    for user in analysis.users:
        if user.email:
            d = email_domain(user.email)
            if d and d not in seen:
                seen.add(d)
                domains.append(d)
    return domains
