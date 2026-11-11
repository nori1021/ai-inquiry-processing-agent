from __future__ import annotations

from functools import lru_cache
from typing import Any

from app.config import get_settings
from app.providers.mock_ai import MockAIProvider
from app.providers.ollama_provider import OllamaProvider
from app.providers.openai_provider import OpenAIProvider


@lru_cache
def get_ai_provider() -> Any:
    """
    Default: Ollama local LLM.
    CI/offline: AI_PROVIDER=mock.
    OpenAI is optional and not part of the MVP default path.
    """
    settings = get_settings()
    provider = (settings.ai_provider or "ollama").lower().strip()

    if provider == "mock":
        return MockAIProvider()

    if provider == "openai":
        return OpenAIProvider(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
            base_url=settings.openai_base_url,
            timeout_seconds=settings.openai_timeout_seconds,
        )

    # Default and "ollama" — no silent mock unless OLLAMA_ALLOW_MOCK_FALLBACK=true
    return OllamaProvider(
        base_url=settings.ollama_base_url,
        model=settings.ollama_model,
        fallback_model=settings.ollama_fallback_model,
        temperature=settings.ollama_temperature,
        num_ctx=settings.ollama_num_ctx,
        timeout_seconds=settings.ollama_timeout_seconds,
        allow_mock_fallback=bool(settings.ollama_allow_mock_fallback),
    )
