from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import create_app
from app.providers.factory import get_ai_provider


@pytest.fixture(autouse=True)
def _mock_ai(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "mock")
    monkeypatch.setenv("TEAMS_CALLBACK_SECRET", "dev-teams-callback-secret")
    get_settings.cache_clear()
    get_ai_provider.cache_clear()
    yield
    get_settings.cache_clear()
    get_ai_provider.cache_clear()


@pytest.fixture()
def client():
    return TestClient(create_app())


def test_teams_callback_auth_and_decision_sync(client):
    created = client.post(
        "/api/v1/workflows",
        json={
            "subject": "Teams demo",
            "body": "Help alice@acme.com",
            "auto_advance": True,
        },
    ).json()
    decision = next(a for a in created["approvals"] if a["status"] == "pending")

    unauthorized = client.post(
        "/api/v1/teams/callbacks/approval",
        json={
            "workflow_id": created["id"],
            "approval_id": decision["id"],
            "decision": "approved",
        },
    )
    assert unauthorized.status_code == 401

    ok = client.post(
        "/api/v1/teams/callbacks/approval",
        headers={"X-Teams-Secret": "dev-teams-callback-secret"},
        json={
            "workflow_id": created["id"],
            "approval_id": decision["id"],
            "decision": "approved",
            "note": "from mock teams",
            "external_ref": decision.get("external_ref"),
        },
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["workflow"]["state"] in {
        "AWAITING_EMAIL_APPROVAL",
        "DRAFTING",
    }

    notify = client.post(
        "/api/v1/teams/mock/notify",
        headers={"X-Teams-Secret": "dev-teams-callback-secret"},
        json={
            "workflow_id": created["id"],
            "approval_id": decision["id"],
            "summary": "notify",
        },
    )
    assert notify.status_code == 200
    assert notify.json()["mode"] == "mock"
