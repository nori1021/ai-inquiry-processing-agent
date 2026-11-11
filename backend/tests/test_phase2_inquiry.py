from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.providers.factory import get_ai_provider
from app.providers.mock_ai import MockAIProvider
from app.providers.ollama_provider import OllamaProvider
from app.schemas.inquiry import (
    InquiryAnalysis,
    InquiryAnalyzeRequest,
    InvestigationNeed,
)
from app.services.local_rag import retrieve_limited_snippets
from app.services.validation_gates import evaluate_confidence_gate, merge_review_decision


@pytest.fixture(autouse=True)
def _use_mock_ai(monkeypatch):
    """CI/offline: force mock AI so tests never require Ollama or paid APIs."""
    monkeypatch.setenv("AI_PROVIDER", "mock")
    get_settings.cache_clear()
    get_ai_provider.cache_clear()
    yield
    get_settings.cache_clear()
    get_ai_provider.cache_clear()


def test_factory_defaults_to_ollama_when_configured(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "ollama")
    monkeypatch.delenv("OLLAMA_NUM_CTX", raising=False)
    monkeypatch.delenv("OLLAMA_TIMEOUT_SECONDS", raising=False)
    monkeypatch.setenv("OLLAMA_ALLOW_MOCK_FALLBACK", "false")
    get_settings.cache_clear()
    get_ai_provider.cache_clear()
    provider = get_ai_provider()
    assert isinstance(provider, OllamaProvider)
    assert provider.model == "qwen3:4b"
    assert provider.fallback_model == "qwen3:1.7b"
    assert provider.temperature == 0.1
    assert provider.num_ctx == 4096
    assert provider.allow_mock_fallback is False
    get_settings.cache_clear()
    get_ai_provider.cache_clear()


def test_factory_mock_for_ci(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "mock")
    get_settings.cache_clear()
    get_ai_provider.cache_clear()
    assert isinstance(get_ai_provider(), MockAIProvider)


def test_confidence_gate_forces_review_at_or_below_0_99():
    analysis = InquiryAnalysis(summary="x", confidence=0.99)
    flags = evaluate_confidence_gate(analysis, threshold=0.99)
    assert merge_review_decision(flags)
    assert any(f.code == "confidence_below_threshold" for f in flags)

    missing = InquiryAnalysis(summary="x", confidence=None)
    assert merge_review_decision(evaluate_confidence_gate(missing))


def test_confidence_gate_passes_only_above_threshold():
    analysis = InquiryAnalysis(summary="x", confidence=0.991)
    flags = evaluate_confidence_gate(analysis, threshold=0.99)
    assert flags == []


def test_mock_analysis_extracts_multi_user_and_plans_required():
    provider = MockAIProvider()
    analysis = asyncio.run(
        provider.analyze_inquiry(
            subject="Password reset",
            body=(
                "Please reset password for alice@acme.com. "
                "Also help bob.smith@globex.com with VPN."
            ),
            from_email="carol@initech.co.jp",
            selectable_tools=[
                {"name": "lookup_ldap_user", "description": "", "input_schema": {}},
                {"name": "lookup_gac_user", "description": "", "input_schema": {}},
                {"name": "lookup_ldap_company", "description": "", "input_schema": {}},
                {
                    "name": "search_past_inquiries",
                    "description": "",
                    "input_schema": {},
                },
                {
                    "name": "search_knowledge_base",
                    "description": "",
                    "input_schema": {},
                },
            ],
        )
    )
    assert len(analysis.users) >= 2
    assert any(u.investigate == InvestigationNeed.REQUIRED for u in analysis.users)
    assert analysis.planned_tools
    assert all(
        t.tool
        in {
            "lookup_ldap_user",
            "lookup_gac_user",
            "lookup_ldap_company",
            "search_past_inquiries",
            "search_knowledge_base",
            "lookup_gac_company_users",
            "check_ldap_registration",
            "check_gac_registration",
            "check_ldap_gac_registration",
        }
        for t in analysis.planned_tools
    )


def test_local_rag_is_limited():
    snippets = retrieve_limited_snippets("password", top_k=3)
    assert len(snippets) <= 3


def test_analyze_api_wires_registry_and_review_flags():
    from app.main import create_app

    client = TestClient(create_app())
    resp = client.post(
        "/api/v1/inquiry/analyze",
        json={
            "subject": "GAC registration",
            "body": "User alice@acme.com is missing from GAC. Please investigate.",
            "from_email": "manager@acme.com",
            "execute_tools": True,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["email_requires_approval"] is True
    assert body["needs_human_review"] is True  # mock confidence 0.82 <= 0.99
    assert body["analysis"]["users"]
    assert body["investigation_plan"]
    assert body["selected_tools"]
    assert body["tool_results"]
    tool_names = {t["tool"] for t in body["selected_tools"]}
    assert (
        "lookup_ldap_user" in tool_names
        or "lookup_gac_user" in tool_names
        or "check_ldap_registration" in tool_names
        or "check_gac_registration" in tool_names
    )
    assert body["ai_mode"] in (
        "mock_heuristic",
        "mock_fallback",
        "actual_llm",
        "unknown",
    )
    assert isinstance(body["rag_references"], list)
    for tr in body["tool_results"]:
        assert "duration_ms" in tr
        assert tr["status"] in ("ok", "error")
    # similar domains validation path may add review flags
    assert isinstance(body["review_flags"], list)


def test_rejects_unregistered_tool_suggestions_from_analysis():
    from app.agents.tool_selection import select_tools_for_investigation
    from app.agents.planner import build_investigation_plan
    from app.schemas.inquiry import PlannedToolCall

    analysis = InquiryAnalysis(
        summary="x",
        confidence=0.5,
        planned_tools=[
            PlannedToolCall(
                tool="run_arbitrary_shell",
                arguments={"cmd": "whoami"},
                need=InvestigationNeed.REQUIRED,
            ),
            PlannedToolCall(
                tool="lookup_ldap_user",
                arguments={"email": "alice@acme.com"},
                need=InvestigationNeed.REQUIRED,
            ),
        ],
    )
    plan = build_investigation_plan(analysis)
    selected = select_tools_for_investigation(analysis, plan)
    assert all(t.tool != "run_arbitrary_shell" for t in selected)
    assert any(t.tool == "lookup_ldap_user" for t in selected)


def test_ollama_unavailable_does_not_silently_mock():
    from app.providers.ollama_errors import OllamaProviderError

    provider = OllamaProvider(base_url="http://127.0.0.1:9")  # nothing listening
    try:
        asyncio.run(
            provider.analyze_inquiry(
                subject="Test",
                body="Please help alice@acme.com",
                from_email=None,
                selectable_tools=[
                    {
                        "name": "lookup_ldap_user",
                        "description": "",
                        "input_schema": {},
                    },
                ],
            )
        )
        assert False, "expected OllamaProviderError"
    except OllamaProviderError as exc:
        assert exc.code == "ollama_unavailable"


def test_ollama_explicit_mock_fallback_escape_hatch():
    provider = OllamaProvider(
        base_url="http://127.0.0.1:9",
        allow_mock_fallback=True,
    )
    analysis = asyncio.run(
        provider.analyze_inquiry(
            subject="Test",
            body="Please help alice@acme.com",
            from_email=None,
            selectable_tools=[
                {"name": "lookup_ldap_user", "description": "", "input_schema": {}},
            ],
        )
    )
    assert "mock_fallback" in analysis.raw_provider
