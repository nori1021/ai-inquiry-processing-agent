from fastapi import APIRouter

from app.config import get_settings
from app.providers.factory import get_ai_provider

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/api/v1/provider")
async def provider_status() -> dict:
    """Observability: configured AI provider + live Ollama reachability (no silent mock)."""
    settings = get_settings()
    provider = get_ai_provider()
    name = getattr(provider, "name", type(provider).__name__)
    payload: dict = {
        "configured_provider": settings.ai_provider,
        "runtime_provider": name,
        "ollama_allow_mock_fallback": bool(settings.ollama_allow_mock_fallback),
    }
    if hasattr(provider, "status"):
        payload["ollama"] = await provider.status()
    elif name == "mock":
        payload["ollama"] = {
            "reachable": None,
            "note": "AI_PROVIDER=mock — Ollama not used",
        }
    payload["last_metrics"] = getattr(provider, "last_metrics", {}) or {}
    payload["last_error"] = getattr(provider, "last_error", None)
    return payload
