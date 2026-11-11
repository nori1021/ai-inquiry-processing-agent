from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import create_app
from app.providers.factory import get_ai_provider


@pytest.fixture(autouse=True)
def _mock_ai(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "mock")
    get_settings.cache_clear()
    get_ai_provider.cache_clear()
    yield
    get_settings.cache_clear()
    get_ai_provider.cache_clear()


def test_synthetic_evaluation_runner():
    client = TestClient(create_app())
    resp = client.post("/api/v1/evaluations/run")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] >= 3
    assert "tool_selection_hit_rate" in body["metrics"]
    assert "not a claimed production accuracy" in body["note"].lower() or "synthetic" in body["note"].lower()
    latest = client.get("/api/v1/evaluations/latest")
    assert latest.status_code == 200
    assert latest.json()["run_id"] == body["run_id"]
