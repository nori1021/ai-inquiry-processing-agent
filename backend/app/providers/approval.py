from __future__ import annotations

import uuid
from typing import Protocol


class ApprovalProvider(Protocol):
    name: str

    def request_approval(self, *, summary: str, approval_type: str) -> str:
        """Return an external reference id for the pending approval."""
        ...


class MockApprovalProvider:
    """Local mock Teams/approval provider — no external network."""

    name = "mock_teams"

    def __init__(self) -> None:
        self.requests: list[dict[str, str]] = []

    def request_approval(self, *, summary: str, approval_type: str) -> str:
        ref = f"mock-teams-{approval_type}-{uuid.uuid4().hex[:12]}"
        self.requests.append(
            {"external_ref": ref, "summary": summary, "approval_type": approval_type}
        )
        return ref
