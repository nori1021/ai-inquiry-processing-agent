from __future__ import annotations

import re
from typing import Any, Optional

from app.schemas.inquiry import (
    ExtractedCompany,
    ExtractedUser,
    InquiryAnalysis,
    InvestigationNeed,
    PlannedToolCall,
    UserRole,
)
from app.services.normalization import email_domain, normalize_email
from app.services.password_reset_signals import (
    INTENT_PASSWORD_RESET_FAILED,
    detect_prior_password_reset_failed,
)

EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")


class MockAIProvider:
    """
    Offline heuristic analyzer for local/dev/tests.
    Does not call external APIs. Produces Pydantic-valid structured analysis.
    """

    name = "mock"

    async def analyze_inquiry(
        self,
        *,
        subject: str,
        body: str,
        from_email: Optional[str],
        selectable_tools: list[dict[str, Any]],
        rag_snippets: Optional[list[dict[str, Any]]] = None,
    ) -> InquiryAnalysis:
        text = f"{subject}\n{body}"
        emails = [normalize_email(m) for m in EMAIL_RE.findall(text)]
        if from_email:
            emails.insert(0, normalize_email(from_email))
        # preserve order, unique
        seen: set[str] = set()
        unique_emails: list[str] = []
        for e in emails:
            if e and e not in seen:
                seen.add(e)
                unique_emails.append(e)

        lower = text.lower()
        users: list[ExtractedUser] = []
        for idx, email in enumerate(unique_emails):
            role = UserRole.REQUESTER if idx == 0 else UserRole.AFFECTED_USER
            if "manager" in lower and idx == len(unique_emails) - 1 and idx > 0:
                role = UserRole.MANAGER
            # Incidental CC / FYI mentions are extracted but not investigated
            email_pos = lower.find(email)
            window = lower[max(0, email_pos - 24) : email_pos + len(email) + 8]
            incidental = any(tag in window for tag in ("cc:", "cc ", "fyi", "fy i"))
            if incidental and idx > 0:
                role = UserRole.OTHER
            need = (
                InvestigationNeed.REQUIRED
                if role
                in (
                    UserRole.REQUESTER,
                    UserRole.AFFECTED_USER,
                    UserRole.TECHNICAL_CONTACT,
                )
                else InvestigationNeed.UNCERTAIN
            )
            if role == UserRole.OTHER:
                need = InvestigationNeed.NOT_REQUIRED
            users.append(
                ExtractedUser(
                    email=email,
                    role=role,
                    reason=(
                        "incidental mention — not investigated"
                        if need == InvestigationNeed.NOT_REQUIRED
                        else "extracted from inquiry text (mock heuristic)"
                    ),
                    investigate=need,
                )
            )

        domains = sorted({email_domain(e) for e in unique_emails if email_domain(e)})
        companies = [
            ExtractedCompany(
                domain=d,
                source="user_email_domain",
                investigate=InvestigationNeed.REQUIRED,
            )
            for d in domains
        ]

        intent = "access_request"
        lower = text.lower()
        if detect_prior_password_reset_failed(subject, body):
            intent = INTENT_PASSWORD_RESET_FAILED
        elif "password" in lower:
            intent = "password_reset"
        elif "gac" in lower:
            intent = "gac_registration"
        elif "vpn" in lower:
            intent = "vpn_access"

        # Password/access: do not auto-plan LDAP/GAC unless text asks for registration/dir
        wants_directory = bool(
            re.search(
                r"\b(ldap|gac|registration|directory|identity)\b",
                lower,
            )
        )
        passwordish = intent in (
            "password_reset",
            INTENT_PASSWORD_RESET_FAILED,
            "access_request",
        )
        if passwordish and not wants_directory:
            for c in companies:
                c.investigate = InvestigationNeed.NOT_REQUIRED

        allowed = {t["name"] for t in selectable_tools}
        planned: list[PlannedToolCall] = []
        if not passwordish or wants_directory:
            for user in users:
                if user.investigate != InvestigationNeed.REQUIRED or not user.email:
                    continue
                for tool_name in (
                    "check_ldap_registration",
                    "check_gac_registration",
                ):
                    if tool_name in allowed:
                        planned.append(
                            PlannedToolCall(
                                tool=tool_name,
                                arguments={"email": user.email},
                                reason=f"{user.role.value} requires registration check",
                                need=InvestigationNeed.REQUIRED,
                            )
                        )
            for company in companies:
                if not company.domain:
                    continue
                if company.investigate == InvestigationNeed.NOT_REQUIRED:
                    continue
                if "lookup_ldap_company" in allowed:
                    planned.append(
                        PlannedToolCall(
                            tool="lookup_ldap_company",
                            arguments={"domain": company.domain},
                            reason="verify company by domain from user email",
                            need=InvestigationNeed.REQUIRED,
                        )
                    )
                if "lookup_gac_company_users" in allowed:
                    planned.append(
                        PlannedToolCall(
                            tool="lookup_gac_company_users",
                            arguments={"domain": company.domain},
                            reason="list GAC users for company domain",
                            need=InvestigationNeed.REQUIRED,
                        )
                    )

        if "search_past_inquiries" in allowed:
            planned.append(
                PlannedToolCall(
                    tool="search_past_inquiries",
                    arguments={"query": intent.replace("_", " "), "limit": 5},
                    reason="check related past tickets",
                    need=InvestigationNeed.REQUIRED,
                )
            )
        if "search_knowledge_base" in allowed:
            planned.append(
                PlannedToolCall(
                    tool="search_knowledge_base",
                    arguments={"query": intent.replace("_", " "), "limit": 5},
                    reason="gather KB guidance",
                    need=InvestigationNeed.REQUIRED,
                )
            )

        # Mock confidence intentionally below auto-pass threshold unless forced high for tests
        confidence = 0.82 if users else 0.4

        notes = ["generated by MockAIProvider heuristic"]
        if rag_snippets:
            notes.append(f"rag_snippets_received={len(rag_snippets)}")
        if intent == INTENT_PASSWORD_RESET_FAILED:
            notes.append(
                "User reports prior reset failed; do not re-send standard reset steps."
            )

        return InquiryAnalysis(
            summary=(
                "Prior password reset reported as failed; escalate instead of "
                "standard reset guidance"
                if intent == INTENT_PASSWORD_RESET_FAILED
                else f"Mock analysis of inquiry about {intent}"
            ),
            intent=intent,
            category="it_helpdesk",
            users=users,
            companies=companies,
            planned_tools=planned,
            confidence=confidence,
            notes=notes,
            raw_provider=self.name,
        )
