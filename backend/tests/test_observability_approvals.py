from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.agents.tool_selection import (
    directory_lookup_warranted,
    select_tools_for_investigation,
)
from app.agents.planner import build_investigation_plan
from app.config import get_settings
from app.main import create_app
from app.providers.factory import get_ai_provider
from app.schemas.inquiry import (
    ExtractedUser,
    InquiryAnalysis,
    InvestigationNeed,
    PlannedToolCall,
    UserRole,
)
from app.workflow.states import WorkflowState


@pytest.fixture(autouse=True)
def _use_mock_ai(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "mock")
    monkeypatch.setenv("OLLAMA_ALLOW_MOCK_FALLBACK", "false")
    get_settings.cache_clear()
    get_ai_provider.cache_clear()
    yield
    get_settings.cache_clear()
    get_ai_provider.cache_clear()


@pytest.fixture()
def client():
    return TestClient(create_app())


def test_password_reset_does_not_auto_ldap_gac():
    analysis = InquiryAnalysis(
        summary="Password reset request",
        intent="password_reset",
        users=[
            ExtractedUser(
                email="alice@acme.com",
                role=UserRole.AFFECTED_USER,
                investigate=InvestigationNeed.REQUIRED,
                reason="needs password help",
            )
        ],
        planned_tools=[
            PlannedToolCall(
                tool="check_ldap_registration",
                arguments={"email": "alice@acme.com"},
                need=InvestigationNeed.REQUIRED,
            )
        ],
    )
    assert directory_lookup_warranted(analysis) is False
    plan = build_investigation_plan(analysis)
    selected = select_tools_for_investigation(analysis, plan)
    names = {t.tool for t in selected}
    assert "check_ldap_registration" not in names
    assert "check_gac_registration" not in names
    assert "search_past_inquiries" in names or "search_knowledge_base" in names


def test_provider_status_endpoint(client):
    resp = client.get("/api/v1/provider")
    assert resp.status_code == 200
    body = resp.json()
    assert body["configured_provider"] == "mock"
    assert body["runtime_provider"] == "mock"
    assert body["ollama_allow_mock_fallback"] is False


def test_email_approval_blocked_while_decision_pending(client):
    created = client.post(
        "/api/v1/workflows",
        json={
            "subject": "Password reset",
            "body": "Please reset password for alice@acme.com",
            "auto_advance": True,
        },
    ).json()
    assert created["state"] == WorkflowState.AWAITING_DECISION_APPROVAL.value
    decision = next(
        a for a in created["approvals"] if a["approval_type"] == "decision"
    )

    # Forge an email approval row via drafting would require decision first.
    # Instead: approve decision, then ensure email path requires its own approval.
    mid = client.post(
        f"/api/v1/workflows/{created['id']}/approvals/{decision['id']}/decide",
        json={"decision": "approved", "note": "ok"},
    ).json()
    assert mid["state"] == WorkflowState.AWAITING_EMAIL_APPROVAL.value
    email = next(
        a
        for a in mid["approvals"]
        if a["approval_type"] == "email" and a["status"] == "pending"
    )
    # Decision is resolved; email still mandatory
    done = client.post(
        f"/api/v1/workflows/{created['id']}/approvals/{email['id']}/decide",
        json={"decision": "approved", "note": "send"},
    )
    assert done.status_code == 200
    assert done.json()["state"] == WorkflowState.COMPLETED.value


def test_analyze_surfaces_provider_fields_on_mock(client):
    resp = client.post(
        "/api/v1/inquiry/analyze",
        json={
            "subject": "Password reset",
            "body": "Please reset password for alice@acme.com",
            "execute_tools": True,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["ai_mode"] == "mock_heuristic"
    assert body["provider_status"] == "mock"
    assert body["provider_error"] is None
    tool_names = {t["tool"] for t in body["selected_tools"]}
    assert "check_ldap_registration" not in tool_names
