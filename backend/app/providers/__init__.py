"""Swappable external providers. Prefer importing submodules directly to avoid cycles."""

from app.providers.approval import MockApprovalProvider
from app.providers.email import GraphEmailProvider, MockEmailProvider, get_email_provider
from app.providers.factory import get_ai_provider
from app.providers.mock_ai import MockAIProvider
from app.providers.ollama_provider import OllamaProvider

__all__ = [
    "GraphEmailProvider",
    "MockAIProvider",
    "MockApprovalProvider",
    "MockEmailProvider",
    "OllamaProvider",
    "get_ai_provider",
    "get_email_provider",
]
