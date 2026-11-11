from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.registry import get_executor, get_registry
from app.registry.executor import validate_arguments
from app.registry.types import ToolKind


REQUIRED_WEB = {
    "search_past_inquiries",
    "search_knowledge_base",
    "get_reply_template",
    "get_inquiry_history",
}
REQUIRED_PS = {
    "lookup_ldap_user",
    "lookup_gac_user",
    "lookup_ldap_company",
    "lookup_gac_company_users",
}


def _run(coro):
    return asyncio.run(coro)


def test_registry_contains_initial_tools():
    reg = get_registry()
    names = {t.name for t in reg.list()}
    assert REQUIRED_WEB <= names
    assert REQUIRED_PS <= names


def test_web_tools_have_approved_mock_endpoints():
    for name in REQUIRED_WEB:
        tool = get_registry().require(name)
        assert tool.kind == ToolKind.WEB_API
        assert tool.execution_policy.approved_endpoint
        assert tool.execution_policy.approved_endpoint.startswith("mock://")


def test_powershell_tools_have_approved_script_ids():
    for name in REQUIRED_PS:
        tool = get_registry().require(name)
        assert tool.kind == ToolKind.POWERSHELL
        assert tool.execution_policy.approved_script_id.startswith("ps/")


def test_mock_web_api_search_past_inquiries():
    result = _run(get_executor().execute("search_past_inquiries", {"query": "password"}))
    assert result.ok
    assert result.provider == "mock_web_api"
    assert result.result["status"] == "FOUND"
    assert result.result["items"]


def test_mock_powershell_ldap_user_dual_path():
    result = _run(get_executor().execute("lookup_ldap_user", {"email": "Alice@Acme.COM"}))
    assert result.ok
    assert result.provider == "mock_powershell"
    assert result.result["status"] == "FOUND"
    assert result.result["user"]["user_id"] == "U1001"


def test_mock_powershell_gac_company_users():
    result = _run(
        get_executor().execute("lookup_gac_company_users", {"domain": "acme.com"})
    )
    assert result.ok
    assert result.result["status"] == "FOUND"
    assert len(result.result["users"]) >= 2


def test_rejects_missing_required_args():
    result = _run(get_executor().execute("lookup_ldap_user", {}))
    assert not result.ok
    assert "required" in (result.error or "").lower() or "Missing" in (result.error or "")


def test_rejects_unknown_tool():
    result = _run(
        get_executor().execute("run_arbitrary_shell", {"cmd": "rm -rf /"})
    )
    assert not result.ok


def test_validate_rejects_extra_args():
    schema = {
        "type": "object",
        "properties": {"email": {"type": "string"}},
        "required": ["email"],
        "additionalProperties": False,
    }
    with pytest.raises(ValueError, match="Unexpected"):
        validate_arguments(schema, {"email": "a@b.com", "cmd": "evil"})


def test_tools_api_list_and_execute():
    client = TestClient(create_app())
    listed = client.get("/api/v1/tools")
    assert listed.status_code == 200
    names = {t["name"] for t in listed.json()}
    assert "lookup_ldap_user" in names
    assert "search_knowledge_base" in names

    resp = client.post(
        "/api/v1/tools/lookup_ldap_user/execute",
        json={"arguments": {"email": "alice@acme.com"}},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["result"]["status"] == "FOUND"
