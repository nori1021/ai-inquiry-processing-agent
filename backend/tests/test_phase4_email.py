from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import create_app
from app.providers.email import MockEmailProvider, get_email_provider
from app.providers.factory import get_ai_provider
from app.services.email_drafts import content_hash
from app.workflow.states import WorkflowState


@pytest.fixture(autouse=True)
def _use_mock_ai(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "mock")
    get_settings.cache_clear()
    get_ai_provider.cache_clear()
    # reset mock outbox between tests
    provider = get_email_provider()
    if isinstance(provider, MockEmailProvider):
        provider.sent_hashes.clear()
        provider.outbox.clear()
    yield
    get_settings.cache_clear()
    get_ai_provider.cache_clear()


@pytest.fixture()
def client():
    return TestClient(create_app())


def _to_email_approval(client: TestClient) -> dict:
    created = client.post(
        "/api/v1/workflows",
        json={
            "subject": "Password reset",
            "body": "Please reset password for alice@acme.com",
            "auto_advance": True,
        },
    ).json()
    decision = next(a for a in created["approvals"] if a["approval_type"] == "decision")
    mid = client.post(
        f"/api/v1/workflows/{created['id']}/approvals/{decision['id']}/decide",
        json={"decision": "approved", "note": "ok"},
    ).json()
    assert mid["state"] == WorkflowState.AWAITING_EMAIL_APPROVAL.value
    return mid


def test_A_templates_listed(client):
    resp = client.get("/api/v1/emails/templates")
    assert resp.status_code == 200
    ids = {t["template_id"] for t in resp.json()}
    assert "password_reset" in ids
    assert "password_reset_escalation" in ids
    assert "general" in ids


def test_B_draft_generated_with_hash(client):
    mid = _to_email_approval(client)
    draft = client.get(f"/api/v1/emails/workflows/{mid['id']}/draft")
    assert draft.status_code == 200
    body = draft.json()
    assert body["version"] == 1
    assert body["content_hash"] == content_hash(
        body["to_email"], body["subject"], body["body"]
    )
    assert body["sent"] is False


def test_C_D_email_approval_required_then_send(client):
    mid = _to_email_approval(client)
    email = next(
        a
        for a in mid["approvals"]
        if a["approval_type"] == "email" and a["status"] == "pending"
    )
    done = client.post(
        f"/api/v1/workflows/{mid['id']}/approvals/{email['id']}/decide",
        json={"decision": "approved", "note": "send"},
    )
    assert done.status_code == 200, done.text
    assert done.json()["state"] == WorkflowState.COMPLETED.value
    assert done.json()["context"]["email_send_status"] == "sent"
    draft = client.get(f"/api/v1/emails/workflows/{mid['id']}/draft").json()
    assert draft["sent"] is True
    assert draft["provider_message_id"]


def test_E_F_draft_edit_invalidates_approval(client):
    mid = _to_email_approval(client)
    wf_id = mid["id"]
    updated = client.put(
        f"/api/v1/emails/workflows/{wf_id}/draft",
        json={"body": "Updated helpdesk reply body with enough characters."},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["version"] == 2
    # pending email approval should be invalidated
    wf = client.get(f"/api/v1/workflows/{wf_id}").json()
    assert wf["state"] == WorkflowState.DRAFTING.value
    pending_email = [
        a
        for a in wf["approvals"]
        if a["approval_type"] == "email" and a["status"] == "pending"
    ]
    assert pending_email == []

    # resubmit for approval
    advanced = client.post(f"/api/v1/emails/workflows/{wf_id}/draft/submit-for-approval")
    assert advanced.status_code == 200
    assert advanced.json()["state"] == WorkflowState.AWAITING_EMAIL_APPROVAL.value


def test_G_H_duplicate_send_prevented(client):
    mid = _to_email_approval(client)
    email = next(
        a
        for a in mid["approvals"]
        if a["approval_type"] == "email" and a["status"] == "pending"
    )
    first = client.post(
        f"/api/v1/workflows/{mid['id']}/approvals/{email['id']}/decide",
        json={"decision": "approved"},
    )
    assert first.status_code == 200
    draft = client.get(f"/api/v1/emails/workflows/{mid['id']}/draft").json()
    provider = get_email_provider()
    assert isinstance(provider, MockEmailProvider)
    second = provider.send_approved_email(
        to=draft["to_email"],
        subject=draft["subject"],
        body=draft["body"],
        content_hash=draft["content_hash"],
        approved_hash=draft["content_hash"],
    )
    assert second.ok is False
    assert second.error == "duplicate_send_prevented"


def test_I_hash_mismatch_blocks_send():
    provider = MockEmailProvider()
    result = provider.send_approved_email(
        to="a@b.com",
        subject="s",
        body="body long enough for validation purposes",
        content_hash="abc",
        approved_hash="xyz",
    )
    assert result.ok is False
    assert "approved_hash" in (result.error or "")


def test_J_graph_disabled_by_default(monkeypatch):
    monkeypatch.setenv("EMAIL_PROVIDER", "graph")
    monkeypatch.setenv("GRAPH_ENABLED", "false")
    get_settings.cache_clear()
    from app.providers.email import GraphEmailProvider, get_email_provider

    # factory falls back to mock unless graph_enabled
    provider = get_email_provider()
    assert provider.name == "mock"
    stub = GraphEmailProvider(enabled=False)
    res = stub.send_approved_email(
        to="a@b.com",
        subject="s",
        body="body",
        content_hash="a",
        approved_hash="a",
    )
    assert res.ok is False
    get_settings.cache_clear()
