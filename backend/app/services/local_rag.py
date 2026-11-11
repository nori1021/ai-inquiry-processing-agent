from __future__ import annotations

from typing import Any

from app.config import get_settings
from app.providers.web_api import MockWebAPIProvider
from app.services.email_drafts import INTENT_TO_TEMPLATE, list_templates, load_template


def _match_reply_template(query: str) -> dict[str, Any] | None:
    """Real on-disk template retrieval keyed by intent keywords — never fabricated."""
    from app.services.password_reset_signals import (
        INTENT_PASSWORD_RESET_FAILED,
        detect_prior_password_reset_failed,
    )

    lower = query.lower()
    intent = "general"
    if detect_prior_password_reset_failed("", query):
        intent = INTENT_PASSWORD_RESET_FAILED
    elif "password" in lower:
        intent = "password_reset"
    elif "gac" in lower or "registration" in lower:
        intent = "gac_registration"
    elif "vpn" in lower:
        intent = "vpn_access"
    template_id = INTENT_TO_TEMPLATE.get(intent, "general")
    available = set(list_templates())
    if template_id not in available:
        return None
    try:
        text = load_template(template_id)
    except FileNotFoundError:
        return None
    return {
        "source": "reply_template",
        "id": template_id,
        "text": text[:500],
    }


def retrieve_limited_snippets(query: str, *, top_k: int | None = None) -> list[dict[str, Any]]:
    """
    Local RAG with hard top-k limit.
    Never returns the full historical corpus — only a small slice for LLM context.
    Phase 2 uses the mock Web API corpora as the local knowledge source.
    """
    settings = get_settings()
    limit = top_k if top_k is not None else int(settings.rag_top_k)
    limit = max(0, min(limit, 5))  # hard ceiling for low-memory Windows
    if limit == 0 or not query.strip():
        return []

    mock = MockWebAPIProvider()
    past = mock._search_past({"query": query, "limit": limit})
    kb = mock._search_kb({"query": query, "limit": limit})

    snippets: list[dict[str, Any]] = []
    for item in past.get("items") or []:
        snippets.append(
            {
                "source": "past_inquiry",
                "id": item.get("id"),
                "text": f"{item.get('subject')} ({item.get('email')})",
            }
        )
    for item in kb.get("items") or []:
        snippets.append(
            {
                "source": "knowledge_base",
                "id": item.get("id"),
                "text": f"{item.get('title')}: {item.get('body')}",
            }
        )
    template = _match_reply_template(query)
    if template:
        snippets.append(template)
    return snippets[:limit]
