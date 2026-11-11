"""Deterministic signals: user already tried password reset and it failed."""

from __future__ import annotations

import re

from app.schemas.inquiry import ReviewFlag

PRIOR_RESET_FAILED_CODE = "prior_password_reset_failed"
PRIOR_RESET_FAILED_WHY = (
    "User reports prior reset failed; do not re-send standard reset steps."
)

# Intent used by mock/LLM when prior reset already failed
INTENT_PASSWORD_RESET_FAILED = "password_reset_failed"
TEMPLATE_ESCALATION = "password_reset_escalation"

_PASSWORDISH = re.compile(
    r"\b(password|passwd|pwd|pass\s*word|credentials?)\b",
    re.IGNORECASE,
)
_RESETISH = re.compile(
    r"\b(reset|resets|resetting|self[- ]?service|forgot)\b",
    re.IGNORECASE,
)
_FAILEDISH = re.compile(
    r"\b("
    r"already\s+tried|already\s+attempted|tried\s+already|"
    r"does\s+not\s+work|doesn't\s+work|dont\s+work|do\s+not\s+work|"
    r"did\s+not\s+work|didn't\s+work|"
    r"still\s+(can'?t|cannot|not)|"
    r"failed|failing|failure|"
    r"not\s+working|no\s+longer\s+works|"
    r"same\s+error|keeps\s+failing|"
    r"unable\s+to\s+(reset|login|log\s*in|sign\s*in)|"
    r"cannot\s+reset|can'?t\s+reset"
    r")\b",
    re.IGNORECASE,
)


def detect_prior_password_reset_failed(subject: str = "", body: str = "") -> bool:
    """
    True when the inquiry indicates a password/credential reset was already
    attempted and did not succeed. Deterministic — used by mock AI and gates.
    """
    text = f"{subject}\n{body}".strip()
    if not text:
        return False
    if not _PASSWORDISH.search(text):
        return False
    # Prefer explicit reset context; allow "password ... failed" without "reset"
    has_reset = bool(_RESETISH.search(text))
    has_fail = bool(_FAILEDISH.search(text))
    if has_reset and has_fail:
        return True
    # "password reset already tried" style without separate fail verb
    if re.search(
        r"\b(password|passwd).{0,40}\b(already\s+tried|tried\s+already|already\s+reset)\b",
        text,
        re.IGNORECASE | re.DOTALL,
    ):
        return True
    if re.search(
        r"\b(already\s+tried|tried\s+already).{0,40}\b(password|passwd).{0,20}\breset\b",
        text,
        re.IGNORECASE | re.DOTALL,
    ):
        return True
    return False


def prior_password_reset_failed_flag() -> ReviewFlag:
    return ReviewFlag(
        code=PRIOR_RESET_FAILED_CODE,
        message=PRIOR_RESET_FAILED_WHY,
        severity="review",
    )
