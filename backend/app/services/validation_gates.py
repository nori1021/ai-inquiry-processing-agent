from __future__ import annotations

from typing import Any, Optional

from app.config import get_settings
from app.schemas.inquiry import InquiryAnalysis, ReviewFlag, ToolCallOutcome
from app.services.password_reset_signals import (
    INTENT_PASSWORD_RESET_FAILED,
    detect_prior_password_reset_failed,
    prior_password_reset_failed_flag,
)


def evaluate_inquiry_text_gates(
    *,
    subject: str = "",
    body: str = "",
    analysis: InquiryAnalysis | None = None,
) -> list[ReviewFlag]:
    """Deterministic text gates — independent of LLM/mock heuristics."""
    flags: list[ReviewFlag] = []
    prior_failed = detect_prior_password_reset_failed(subject, body)
    if analysis is not None and (
        analysis.intent or ""
    ).lower() == INTENT_PASSWORD_RESET_FAILED:
        prior_failed = True
    if prior_failed:
        flags.append(prior_password_reset_failed_flag())
    return flags


def evaluate_confidence_gate(
    analysis: InquiryAnalysis,
    *,
    threshold: Optional[float] = None,
) -> list[ReviewFlag]:
    """Python-owned confidence gate. Do not trust uncalibrated LLM confidence alone."""
    settings = get_settings()
    limit = (
        float(threshold)
        if threshold is not None
        else float(settings.confidence_review_threshold)
    )
    flags: list[ReviewFlag] = []
    conf = analysis.confidence
    if conf is None:
        flags.append(
            ReviewFlag(
                code="confidence_missing",
                message="AI confidence missing; human review required",
            )
        )
        return flags
    try:
        value = float(conf)
    except (TypeError, ValueError):
        flags.append(
            ReviewFlag(
                code="confidence_invalid",
                message="AI confidence invalid; human review required",
            )
        )
        return flags
    if value < 0 or value > 1:
        flags.append(
            ReviewFlag(
                code="confidence_invalid",
                message="AI confidence out of range; human review required",
            )
        )
        return flags
    if value <= limit:
        flags.append(
            ReviewFlag(
                code="confidence_below_threshold",
                message=(
                    f"AI confidence {value} <= {limit}; "
                    "human review required (uncalibrated LLM score)"
                ),
            )
        )
    return flags


def evaluate_tool_result_gates(
    tool_results: list[ToolCallOutcome],
) -> list[ReviewFlag]:
    """Force review on conflicts, ambiguity, and similar-domain candidates."""
    flags: list[ReviewFlag] = []

    ldap_by_email: dict[str, dict[str, Any]] = {}
    gac_by_email: dict[str, dict[str, Any]] = {}

    for outcome in tool_results:
        if not outcome.ok or not isinstance(outcome.result, dict):
            if not outcome.ok:
                flags.append(
                    ReviewFlag(
                        code="tool_execution_failed",
                        message=f"Tool {outcome.tool} failed: {outcome.error}",
                    )
                )
            continue

        result = outcome.result
        status = result.get("status")

        if outcome.tool in (
            "lookup_ldap_user",
            "get_ldap_user",
            "check_ldap_registration",
        ):
            email = (
                outcome.arguments.get("email")
                or result.get("query")
                or result.get("query_email")
                or ""
            ).lower()
            # Normalize registration-check shape into lookup-like status for gates
            if outcome.tool == "check_ldap_registration":
                registered = result.get("registered")
                status = (
                    "UNKNOWN"
                    if registered == "unknown"
                    else "FOUND"
                    if registered == "yes"
                    else "NOT_REGISTERED"
                )
                result = {
                    **result,
                    "status": status,
                    "user": result.get("user"),
                    "query": email,
                }
            if email:
                ldap_by_email[email] = result
            if result.get("status") == "UNKNOWN":
                flags.append(
                    ReviewFlag(
                        code="ldap_source_unknown",
                        message=f"LDAP source UNKNOWN for {email}",
                    )
                )

        if outcome.tool in (
            "lookup_gac_user",
            "get_gac_user",
            "check_gac_registration",
        ):
            email = (
                outcome.arguments.get("email")
                or result.get("query")
                or result.get("query_email")
                or ""
            ).lower()
            if outcome.tool == "check_gac_registration":
                registered = result.get("registered")
                status = (
                    "UNKNOWN"
                    if registered == "unknown"
                    else "FOUND"
                    if registered == "yes"
                    else "NOT_REGISTERED"
                )
                result = {
                    **result,
                    "status": status,
                    "user": result.get("user"),
                    "query": email,
                }
            if email:
                gac_by_email[email] = result
            if result.get("status") == "UNKNOWN":
                flags.append(
                    ReviewFlag(
                        code="gac_source_unknown",
                        message=f"GAC source UNKNOWN for {email}",
                    )
                )

        if outcome.tool == "find_similar_domains":
            candidates = result.get("candidates") or []
            if candidates:
                flags.append(
                    ReviewFlag(
                        code="similar_domains_present",
                        message=(
                            "Similar domain candidates found; "
                            "never auto-accept as same company — human review required"
                        ),
                    )
                )

        if outcome.tool == "lookup_ldap_company" and status == "NOT_REGISTERED":
            # Company not found may be OK, but pair with similar-domain check elsewhere
            pass

    for email, ldap in ldap_by_email.items():
        gac = gac_by_email.get(email)
        if not gac:
            continue
        ldap_user = ldap.get("user") or {}
        gac_user = gac.get("user") or {}
        ldap_co = ldap_user.get("company_id")
        gac_co = gac_user.get("company_id")
        if (
            ldap.get("status") == "FOUND"
            and gac.get("status") == "FOUND"
            and ldap_co
            and gac_co
            and ldap_co != gac_co
        ):
            flags.append(
                ReviewFlag(
                    code="ldap_gac_company_conflict",
                    message=(
                        f"Conflicting company IDs for {email}: "
                        f"LDAP={ldap_co} GAC={gac_co}"
                    ),
                )
            )
        if ldap.get("status") == "FOUND" and gac.get("status") == "NOT_REGISTERED":
            flags.append(
                ReviewFlag(
                    code="gac_missing_while_ldap_found",
                    message=f"LDAP found but GAC not registered for {email}",
                )
            )
        if ldap.get("status") == "NOT_REGISTERED" and gac.get("status") == "FOUND":
            flags.append(
                ReviewFlag(
                    code="ldap_missing_while_gac_found",
                    message=f"GAC found but LDAP not registered for {email}",
                )
            )

    return flags


def merge_review_decision(flags: list[ReviewFlag]) -> bool:
    return len(flags) > 0
