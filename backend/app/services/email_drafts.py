from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.config.settings import PROJECT_ROOT
from app.models.audit import utcnow
from app.models.email_draft import EmailDraft
from app.models.workflow import WorkflowInstance
from app.providers.audit import record_audit
from app.workflow.repository import get_context

TEMPLATE_DIR = PROJECT_ROOT / "templates" / "replies"

INTENT_TO_TEMPLATE = {
    "password_reset": "password_reset",
    "password_reset_failed": "password_reset_escalation",
    "gac_registration": "gac_missing",
    "vpn_access": "vpn_access",
}


def content_hash(to_email: str, subject: str, body: str) -> str:
    payload = f"{to_email.strip().lower()}\n{subject.strip()}\n{body.strip()}".encode(
        "utf-8"
    )
    return hashlib.sha256(payload).hexdigest()


def list_templates() -> list[str]:
    if not TEMPLATE_DIR.is_dir():
        return []
    return sorted(p.stem for p in TEMPLATE_DIR.glob("*.txt"))


def load_template(template_id: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9_\-]", "", template_id)
    path = TEMPLATE_DIR / f"{safe}.txt"
    if not path.is_file():
        raise FileNotFoundError(f"Template not found: {template_id}")
    return path.read_text(encoding="utf-8")


def select_template_id(context: dict[str, Any]) -> str:
    from app.services.password_reset_signals import (
        INTENT_PASSWORD_RESET_FAILED,
        TEMPLATE_ESCALATION,
        detect_prior_password_reset_failed,
    )

    analysis = context.get("last_analysis") or {}
    analysis_inner = analysis.get("analysis") or analysis
    intent = (analysis_inner.get("intent") or "").lower()
    flags = analysis.get("review_flags") or []
    flag_codes = {str(f.get("code") or "") for f in flags if isinstance(f, dict)}

    # Never send standard password_reset steps when prior reset failed
    subject = str(context.get("subject") or "")
    body = str(context.get("body") or "")
    # Workflow context may store original inquiry on the instance; prefer flags/intent
    if (
        intent == INTENT_PASSWORD_RESET_FAILED
        or "prior_password_reset_failed" in flag_codes
        or detect_prior_password_reset_failed(subject, body)
    ):
        return TEMPLATE_ESCALATION

    chosen = INTENT_TO_TEMPLATE.get(intent, "general")
    if chosen == "password_reset" and "prior_password_reset_failed" in flag_codes:
        return TEMPLATE_ESCALATION
    return chosen


def _render(template: str, variables: dict[str, str]) -> tuple[str, str]:
    text = template
    for key, value in variables.items():
        text = text.replace("{{" + key + "}}", value)
    # drop unresolved simple placeholders
    text = re.sub(r"\{\{[a-zA-Z0-9_]+\}\}", "", text)
    lines = text.splitlines()
    subject = "IT Helpdesk reply"
    body_lines = lines
    if lines and lines[0].lower().startswith("subject:"):
        subject = lines[0].split(":", 1)[1].strip()
        body_lines = lines[1:]
        if body_lines and body_lines[0].strip() == "":
            body_lines = body_lines[1:]
    return subject, "\n".join(body_lines).strip() + "\n"


def build_variables(wf: WorkflowInstance, context: dict[str, Any]) -> dict[str, str]:
    analysis = context.get("last_analysis") or {}
    inner = analysis.get("analysis") or {}
    users = inner.get("users") or []
    primary = users[0] if users else {}
    email = primary.get("email") or wf.from_email or "user@example.com"
    name = primary.get("display_name") or (email.split("@")[0] if email else "User")
    domain = email.split("@")[-1] if "@" in email else ""
    tool_results = analysis.get("tool_results") or []
    ldap_status = "UNKNOWN"
    gac_status = "UNKNOWN"
    company_name = domain or "N/A"
    for tr in tool_results:
        tool = tr.get("tool")
        result = tr.get("result") or {}
        if tool in ("lookup_ldap_user", "get_ldap_user") and tr.get("ok"):
            ldap_status = result.get("status") or ldap_status
            user = result.get("user") or {}
            company_name = user.get("company_name") or company_name
        if tool in ("lookup_gac_user", "get_gac_user") and tr.get("ok"):
            gac_status = result.get("status") or gac_status
        if tool == "check_ldap_registration" and tr.get("ok"):
            registered = result.get("registered")
            ldap_status = (
                "UNKNOWN"
                if registered == "unknown"
                else "FOUND"
                if registered == "yes"
                else "NOT_REGISTERED"
            )
            user = result.get("user") or {}
            company_name = (
                result.get("company_name")
                or user.get("company_name")
                or company_name
            )
        if tool == "check_gac_registration" and tr.get("ok"):
            registered = result.get("registered")
            gac_status = (
                "UNKNOWN"
                if registered == "unknown"
                else "FOUND"
                if registered == "yes"
                else "NOT_REGISTERED"
            )
    flags = analysis.get("review_flags") or []
    notes = "; ".join(f.get("code", "") for f in flags) or "No additional review flags."
    return {
        "subject": wf.subject or "Inquiry",
        "name": name,
        "email": email,
        "domain": domain,
        "company_name": company_name,
        "ldap_status": str(ldap_status),
        "gac_status": str(gac_status),
        "extra_notes": notes,
    }


def validate_draft(to_email: str, subject: str, body: str) -> list[str]:
    errors: list[str] = []
    if not to_email or "@" not in to_email:
        errors.append("to_email invalid")
    if not subject.strip():
        errors.append("subject required")
    if len(body.strip()) < 20:
        errors.append("body too short")
    if "{{" in body or "{{" in subject:
        errors.append("unresolved template placeholders")
    return errors


def current_draft(db: Session, workflow_id: int) -> EmailDraft | None:
    return (
        db.query(EmailDraft)
        .filter(EmailDraft.workflow_id == workflow_id, EmailDraft.is_current.is_(True))
        .order_by(EmailDraft.version.desc())
        .first()
    )


def create_draft_version(
    db: Session,
    wf: WorkflowInstance,
    *,
    template_id: str | None = None,
    to_email: str | None = None,
    subject: str | None = None,
    body: str | None = None,
) -> EmailDraft:
    context = get_context(wf)
    # Include inquiry text so deterministic prior-reset detection can run at draft time
    draft_context = {
        **context,
        "subject": wf.subject or "",
        "body": wf.body or "",
    }
    tid = template_id or select_template_id(draft_context)
    variables = build_variables(wf, context)
    if subject is None or body is None:
        rendered_subject, rendered_body = _render(load_template(tid), variables)
        subject = subject if subject is not None else rendered_subject
        body = body if body is not None else rendered_body
    to_addr = to_email or variables["email"]
    errors = validate_draft(to_addr, subject, body)
    if errors:
        raise ValueError("Draft validation failed: " + ", ".join(errors))

    # supersede previous current
    prev = current_draft(db, wf.id)
    version = 1
    if prev:
        version = prev.version + 1
        prev.is_current = False

    digest = content_hash(to_addr, subject, body)
    draft = EmailDraft(
        workflow_id=wf.id,
        version=version,
        template_id=tid,
        to_email=to_addr,
        subject=subject,
        body=body,
        content_hash=digest,
        approved_hash=None,
        is_current=True,
        sent=False,
    )
    db.add(draft)
    db.flush()
    record_audit(
        event_type="email.draft_created",
        payload={
            "draft_id": draft.id,
            "version": version,
            "template_id": tid,
            "content_hash": digest,
        },
        workflow_id=wf.id,
        db=db,
    )
    return draft


def mark_draft_approved(db: Session, draft: EmailDraft) -> None:
    draft.approved_hash = draft.content_hash
    draft.updated_at = utcnow()


def mark_draft_sent(db: Session, draft: EmailDraft, message_id: str) -> None:
    draft.sent = True
    draft.sent_at = utcnow()
    draft.provider_message_id = message_id
