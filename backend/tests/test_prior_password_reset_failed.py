from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import create_app
from app.providers.factory import get_ai_provider
from app.providers.mock_ai import MockAIProvider
from app.services.email_drafts import select_template_id
from app.services.password_reset_signals import (
    INTENT_PASSWORD_RESET_FAILED,
    TEMPLATE_ESCALATION,
    detect_prior_password_reset_failed,
)
from app.workflow.states import WorkflowState


FAILED_BODY = (
    "I already tried a password reset for alice@acme.com and it does not work. "
    "Please help — do not just send the same reset steps."
)


@pytest.fixture(autouse=True)
def _use_mock_ai(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "mock")
    get_settings.cache_clear()
    get_ai_provider.cache_clear()
    yield
    get_settings.cache_clear()
    get_ai_provider.cache_clear()


def test_detector_positive_and_negative():
    assert detect_prior_password_reset_failed(
        "Password help", FAILED_BODY
    )
    assert detect_prior_password_reset_failed(
        "", "Password reset failed for bob@acme.com"
    )
    assert not detect_prior_password_reset_failed(
        "Password reset", "Please reset password for alice@acme.com"
    )


def test_mock_provider_sets_failed_intent():
    provider = MockAIProvider()
    analysis = asyncio.run(
        provider.analyze_inquiry(
            subject="Password reset still failing",
            body=FAILED_BODY,
            from_email="alice@acme.com",
            selectable_tools=[],
        )
    )
    assert analysis.intent == INTENT_PASSWORD_RESET_FAILED
    assert any("prior reset failed" in n.lower() for n in analysis.notes)


def test_analyze_api_flags_and_blocks_standard_template():
    client = TestClient(create_app())
    resp = client.post(
        "/api/v1/inquiry/analyze",
        json={
            "subject": "Password reset still failing",
            "body": FAILED_BODY,
            "from_email": "manager@acme.com",
            "execute_tools": True,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["analysis"]["intent"] == INTENT_PASSWORD_RESET_FAILED
    codes = {f["code"] for f in body["review_flags"]}
    assert "prior_password_reset_failed" in codes
    assert body["needs_human_review"] is True

    # Template selection must escalate, never password_reset
    tid = select_template_id(
        {
            "last_analysis": body,
            "subject": "Password reset still failing",
            "body": FAILED_BODY,
        }
    )
    assert tid == TEMPLATE_ESCALATION
    assert tid != "password_reset"


def test_workflow_draft_uses_escalation_template():
    client = TestClient(create_app())
    created = client.post(
        "/api/v1/workflows",
        json={
            "subject": "Password reset still failing",
            "body": FAILED_BODY,
            "from_email": "alice@acme.com",
            "auto_advance": True,
        },
    )
    assert created.status_code == 200, created.text
    wf = created.json()
    assert wf["state"] == WorkflowState.AWAITING_DECISION_APPROVAL.value
    flags = (wf["context"].get("last_analysis") or {}).get("review_flags") or []
    assert any(f.get("code") == "prior_password_reset_failed" for f in flags)

    decision = next(a for a in wf["approvals"] if a["approval_type"] == "decision")
    mid = client.post(
        f"/api/v1/workflows/{wf['id']}/approvals/{decision['id']}/decide",
        json={"decision": "approved", "note": "escalate"},
    ).json()
    assert mid["state"] == WorkflowState.AWAITING_EMAIL_APPROVAL.value

    draft = client.get(f"/api/v1/emails/workflows/{wf['id']}/draft").json()
    assert draft["template_id"] == TEMPLATE_ESCALATION
    assert "Password reset guidance" not in draft["subject"]
    assert "will not resend the standard self-service reset steps" in draft[
        "body"
    ].lower()
