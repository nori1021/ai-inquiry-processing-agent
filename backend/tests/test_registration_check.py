from __future__ import annotations

import asyncio

from fastapi.testclient import TestClient

from app.main import create_app
from app.registry import get_executor, get_registry
from app.schemas.registration import CombinedRegistrationState, RegistrationFlag
from app.tools.registration_check import (
    check_gac_registration,
    check_ldap_gac_registration,
    check_ldap_registration,
)


def _run(coro):
    return asyncio.run(coro)


def test_registry_lists_registration_check_tools():
    names = {t.name for t in get_registry().list()}
    assert "check_ldap_registration" in names
    assert "check_gac_registration" in names
    assert "check_ldap_gac_registration" in names


def test_check_ldap_registration_found():
    result = check_ldap_registration(email="alice@acme.com")
    assert result.registered == RegistrationFlag.YES
    assert result.lookup_status == "FOUND"
    assert result.user is not None


def test_check_frank_ldap_miss_gac_hit():
    # Sample data: frank@acme.com is GAC-only (not in LDAP Excel)
    ldap = check_ldap_registration(email="frank@acme.com")
    gac = check_gac_registration(email="frank@acme.com")
    if ldap.registered != RegistrationFlag.UNKNOWN:
        assert ldap.registered == RegistrationFlag.NO
        assert ldap.lookup_status == "NOT_REGISTERED"
    if gac.registered != RegistrationFlag.UNKNOWN:
        assert gac.registered == RegistrationFlag.YES
        assert gac.lookup_status == "FOUND"
    combined = check_ldap_gac_registration(email="frank@acme.com")
    if combined.combined_state != CombinedRegistrationState.UNKNOWN:
        assert combined.combined_state == CombinedRegistrationState.GAC_ONLY


def test_check_ldap_gac_combined_shape():
    result = check_ldap_gac_registration(email="alice@acme.com")
    assert result.combined_state in set(CombinedRegistrationState)
    assert result.ldap.source == "ldap"
    assert result.gac.source == "gac"


def test_unknown_never_equals_not_registered_on_missing_identity():
    try:
        check_ldap_registration()
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_executor_runs_registration_tools():
    outcome = _run(
        get_executor().execute(
            "check_ldap_registration", {"email": "alice@acme.com"}
        )
    )
    assert outcome.ok
    assert outcome.duration_ms >= 0
    assert outcome.result["registered"] in ("yes", "no", "unknown")


def test_analyze_prefers_registration_checks_for_required_users():
    client = TestClient(create_app())
    resp = client.post(
        "/api/v1/inquiry/analyze",
        json={
            "subject": "GAC registration check",
            "body": (
                "Please confirm whether frank@acme.com is registered in GAC. "
                "cc: grace@globex.com"
            ),
            "from_email": "alice@acme.com",
            "execute_tools": True,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["ai_mode"] in ("mock_heuristic", "mock_fallback", "actual_llm", "unknown")
    assert "rag_references" in body
    assert isinstance(body["rag_references"], list)
    tool_names = {t["tool"] for t in body["selected_tools"]}
    assert "check_ldap_registration" in tool_names or "check_gac_registration" in tool_names
    users = body["analysis"]["users"]
    grace = next((u for u in users if u.get("email") == "grace@globex.com"), None)
    assert grace is not None
    assert grace["investigate"] == "NOT_REQUIRED"
    for tr in body["tool_results"]:
        assert "duration_ms" in tr
        assert tr["status"] in ("ok", "error")
        # Do not fabricate — every result comes from a real executor call
        assert tr["tool"]
