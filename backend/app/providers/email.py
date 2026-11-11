from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class SendResult:
    ok: bool
    message_id: str | None = None
    error: str | None = None
    provider: str = "mock"


class EmailProvider(Protocol):
    name: str

    def send_approved_email(
        self,
        *,
        to: str,
        subject: str,
        body: str,
        content_hash: str,
        approved_hash: str,
    ) -> SendResult: ...


@dataclass
class MockEmailProvider:
    """Default email provider — no network. Enforces hash match + duplicate guard via caller."""

    name: str = "mock"
    sent_hashes: set[str] = field(default_factory=set)
    outbox: list[dict] = field(default_factory=list)

    def send_approved_email(
        self,
        *,
        to: str,
        subject: str,
        body: str,
        content_hash: str,
        approved_hash: str,
    ) -> SendResult:
        if not approved_hash or content_hash != approved_hash:
            return SendResult(
                ok=False,
                error="content_hash does not match approved_hash; approval invalidated",
                provider=self.name,
            )
        if content_hash in self.sent_hashes:
            return SendResult(
                ok=False,
                error="duplicate_send_prevented",
                provider=self.name,
            )
        message_id = f"mock-msg-{uuid.uuid4().hex[:12]}"
        self.sent_hashes.add(content_hash)
        self.outbox.append(
            {
                "message_id": message_id,
                "to": to,
                "subject": subject,
                "body": body,
                "content_hash": content_hash,
            }
        )
        return SendResult(ok=True, message_id=message_id, provider=self.name)


class GraphEmailProvider:
    """Microsoft Graph stub — disabled by default; never used unless explicitly enabled."""

    name = "graph"

    def __init__(self, *, enabled: bool = False) -> None:
        self.enabled = enabled

    def send_approved_email(
        self,
        *,
        to: str,
        subject: str,
        body: str,
        content_hash: str,
        approved_hash: str,
    ) -> SendResult:
        if not self.enabled:
            return SendResult(
                ok=False,
                error="GraphEmailProvider disabled (EMAIL_PROVIDER!=graph or GRAPH_ENABLED=false)",
                provider=self.name,
            )
        return SendResult(
            ok=False,
            error="Graph send not implemented in demo; use mock provider",
            provider=self.name,
        )


_mock_singleton = MockEmailProvider()


def get_email_provider() -> EmailProvider:
    from app.config import get_settings

    settings = get_settings()
    provider = (settings.email_provider or "mock").lower().strip()
    if provider == "graph" and getattr(settings, "graph_enabled", False):
        return GraphEmailProvider(enabled=True)
    return _mock_singleton
