from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.database.session import SessionLocal
from app.main import create_app
from app.providers.factory import get_ai_provider
from app.workflow.states import (
    ALLOWED_TRANSITIONS,
    WorkflowState,
    assert_transition,
)


@pytest.fixture(autouse=True)
def _use_mock_ai(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "mock")
    get_settings.cache_clear()
    get_ai_provider.cache_clear()
    yield
    get_settings.cache_clear()
    get_ai_provider.cache_clear()


@pytest.fixture()
def client():
    return TestClient(create_app())


def test_illegal_transition_rejected():
    with pytest.raises(ValueError, match="Illegal transition"):
        assert_transition(WorkflowState.RECEIVED, WorkflowState.COMPLETED)
    assert WorkflowState.ANALYZING in ALLOWED_TRANSITIONS[WorkflowState.RECEIVED]


def test_workflow_reaches_decision_approval(client):
    resp = client.post(
        "/api/v1/workflows",
        json={
            "subject": "Password reset",
            "body": "Please help alice@acme.com with password reset.",
            "from_email": "manager@acme.com",
            "auto_advance": True,
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["state"] == WorkflowState.AWAITING_DECISION_APPROVAL.value
    assert body["email_requires_approval"] is True
    assert body["approvals"]
    assert any(a["approval_type"] == "decision" and a["status"] == "pending" for a in body["approvals"])
    assert len(body["transitions"]) >= 2


def test_approval_then_email_then_complete(client):
    created = client.post(
        "/api/v1/workflows",
        json={
            "subject": "GAC issue",
            "body": "User alice@acme.com missing from GAC.",
            "auto_advance": True,
        },
    ).json()
    wf_id = created["id"]
    decision = next(a for a in created["approvals"] if a["approval_type"] == "decision")

    decided = client.post(
        f"/api/v1/workflows/{wf_id}/approvals/{decision['id']}/decide",
        json={"decision": "approved", "note": "looks ok", "request_replan": False},
    )
    assert decided.status_code == 200, decided.text
    mid = decided.json()
    assert mid["state"] == WorkflowState.AWAITING_EMAIL_APPROVAL.value
    email = next(
        a
        for a in mid["approvals"]
        if a["approval_type"] == "email" and a["status"] == "pending"
    )

    final = client.post(
        f"/api/v1/workflows/{wf_id}/approvals/{email['id']}/decide",
        json={"decision": "approved", "note": "send ok"},
    )
    assert final.status_code == 200, final.text
    done = final.json()
    assert done["state"] == WorkflowState.COMPLETED.value
    assert done["context"].get("email_send_status") == "sent"


def test_reject_cancels_workflow(client):
    created = client.post(
        "/api/v1/workflows",
        json={
            "subject": "VPN",
            "body": "bob.smith@globex.com needs VPN",
            "auto_advance": True,
        },
    ).json()
    decision = next(a for a in created["approvals"] if a["status"] == "pending")
    resp = client.post(
        f"/api/v1/workflows/{created['id']}/approvals/{decision['id']}/decide",
        json={"decision": "rejected", "note": "not enough info"},
    )
    assert resp.status_code == 200
    assert resp.json()["state"] == WorkflowState.CANCELLED.value


def test_replan_path_does_not_skip_email_approval(client):
    created = client.post(
        "/api/v1/workflows",
        json={
            "subject": "Replan case",
            "body": "Investigate alice@acme.com registration",
            "auto_advance": True,
        },
    ).json()
    decision = next(a for a in created["approvals"] if a["approval_type"] == "decision")
    resp = client.post(
        f"/api/v1/workflows/{created['id']}/approvals/{decision['id']}/decide",
        json={"decision": "approved", "request_replan": True, "note": "recheck"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    # After replan + investigate, mock confidence still forces decision or email gate
    assert body["state"] in {
        WorkflowState.AWAITING_DECISION_APPROVAL.value,
        WorkflowState.AWAITING_EMAIL_APPROVAL.value,
        WorkflowState.DRAFTING.value,
    }
    assert body["email_requires_approval"] is True
    assert body["context"].get("replan_count", 0) >= 1


def test_readonly_investigate_while_approval_pending(client):
    created = client.post(
        "/api/v1/workflows",
        json={
            "subject": "Readonly",
            "body": "Check alice@acme.com while waiting",
            "auto_advance": True,
        },
    ).json()
    assert created["state"] == WorkflowState.AWAITING_DECISION_APPROVAL.value

    ok = client.post(
        f"/api/v1/workflows/{created['id']}/investigate-readonly",
        json={"tool": "lookup_ldap_user", "arguments": {"email": "alice@acme.com"}},
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["ok"] is True
    assert ok.json()["note"] == "read_only_independent_investigation"

    blocked = client.post(
        f"/api/v1/workflows/{created['id']}/investigate-readonly",
        json={"tool": "run_arbitrary_shell", "arguments": {"cmd": "whoami"}},
    )
    assert blocked.status_code == 400


def test_restart_recovery_preserves_state_and_allows_continue(client):
    created = client.post(
        "/api/v1/workflows",
        json={
            "subject": "Persist",
            "body": "alice@acme.com needs help",
            "auto_advance": True,
        },
    ).json()
    wf_id = created["id"]
    assert created["state"] == WorkflowState.AWAITING_DECISION_APPROVAL.value

    # Simulate process restart: new DB session + engine reload
    db = SessionLocal()
    try:
        from app.workflow.engine import WorkflowEngine

        view = WorkflowEngine(db).get(wf_id)
        assert view.state == WorkflowState.AWAITING_DECISION_APPROVAL
        assert view.id == wf_id
        decision = next(a for a in view.approvals if a.status.value == "pending")
    finally:
        db.close()

    # Continue after "restart" via API
    decided = client.post(
        f"/api/v1/workflows/{wf_id}/approvals/{decision.id}/decide",
        json={"decision": "approved", "note": "after restart"},
    )
    assert decided.status_code == 200
    assert decided.json()["state"] in {
        WorkflowState.AWAITING_EMAIL_APPROVAL.value,
        WorkflowState.DRAFTING.value,
    }

    # Audit trail persisted
    audit = client.get(f"/api/v1/workflows/{wf_id}/audit")
    assert audit.status_code == 200
    types = {e["event_type"] for e in audit.json()}
    assert "workflow.created" in types
    assert "workflow.transition" in types
    assert "workflow.approval_decided" in types
