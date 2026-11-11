from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app


def test_health_and_ldap_lookup_endpoint():
    client = TestClient(create_app())
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    resp = client.get("/api/v1/lookup/ldap/users", params={"email": "alice@acme.com"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "FOUND"
    assert body["user"]["user_id"] == "U1001"


def test_similar_domains_endpoint():
    client = TestClient(create_app())
    resp = client.get(
        "/api/v1/lookup/domains/similar",
        params={"domain": "acme.com", "threshold": 70},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "FOUND"
    assert body["candidates"]
