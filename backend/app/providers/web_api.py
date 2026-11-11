from __future__ import annotations

from typing import Any, Protocol

from app.registry.types import ToolDefinition


class WebAPIProvider(Protocol):
    name: str

    async def execute(
        self,
        tool: ToolDefinition,
        arguments: dict[str, Any],
    ) -> Any: ...


class MockWebAPIProvider:
    """In-process synthetic responses for approved mock:// endpoints only."""

    name = "mock_web_api"

    # Tiny synthetic corpora for local dev
    _PAST = [
        {
            "id": "INQ-100",
            "subject": "Cannot reset password",
            "email": "alice@acme.com",
            "tags": ["password", "ldap"],
        },
        {
            "id": "INQ-101",
            "subject": "VPN access for new hire",
            "email": "frank@acme.com",
            "tags": ["vpn", "access"],
        },
        {
            "id": "INQ-102",
            "subject": "GAC registration missing",
            "email": "grace@globex.com",
            "tags": ["gac", "registration"],
        },
    ]
    _KB = [
        {
            "id": "KB-1",
            "title": "Password reset procedure",
            "body": "Use the self-service portal...",
            "tags": ["password"],
        },
        {
            "id": "KB-2",
            "title": "VPN onboarding checklist",
            "body": "Confirm LDAP Active then provision VPN...",
            "tags": ["vpn"],
        },
        {
            "id": "KB-3",
            "title": "GAC registration FAQ",
            "body": "GAC must match company domain...",
            "tags": ["gac"],
        },
    ]
    _TEMPLATES = {
        "password_reset": {
            "template_id": "password_reset",
            "subject": "Re: Password reset",
            "body": "Hello {{name}}, please use the self-service portal to reset your password.",
        },
        "gac_missing": {
            "template_id": "gac_missing",
            "subject": "Re: GAC registration",
            "body": "Hello {{name}}, we could not find your GAC registration for {{domain}}.",
        },
    }

    def _assert_approved(self, tool: ToolDefinition) -> None:
        endpoint = tool.execution_policy.approved_endpoint
        if not endpoint or not endpoint.startswith("mock://"):
            raise PermissionError(
                f"Endpoint not approved for mock Web API: {endpoint!r}"
            )

    async def execute(self, tool: ToolDefinition, arguments: dict[str, Any]) -> Any:
        self._assert_approved(tool)
        name = tool.name
        if name == "search_past_inquiries":
            return self._search_past(arguments)
        if name == "search_knowledge_base":
            return self._search_kb(arguments)
        if name == "get_reply_template":
            return self._get_template(arguments)
        if name == "get_inquiry_history":
            return self._history(arguments)
        raise ValueError(f"No mock Web API handler for tool: {name}")

    def _search_past(self, arguments: dict[str, Any]) -> dict[str, Any]:
        query = str(arguments.get("query", "")).lower()
        limit = int(arguments.get("limit") or 10)
        hits = [
            item
            for item in self._PAST
            if query in item["subject"].lower()
            or query in " ".join(item["tags"])
            or query in item["email"].lower()
        ][:limit]
        return {"status": "FOUND" if hits else "NOT_REGISTERED", "items": hits}

    def _search_kb(self, arguments: dict[str, Any]) -> dict[str, Any]:
        query = str(arguments.get("query", "")).lower()
        limit = int(arguments.get("limit") or 10)
        hits = [
            item
            for item in self._KB
            if query in item["title"].lower()
            or query in item["body"].lower()
            or query in " ".join(item["tags"])
        ][:limit]
        return {"status": "FOUND" if hits else "NOT_REGISTERED", "items": hits}

    def _get_template(self, arguments: dict[str, Any]) -> dict[str, Any]:
        tid = str(arguments.get("template_id", ""))
        template = self._TEMPLATES.get(tid)
        if not template:
            return {"status": "NOT_REGISTERED", "template": None}
        return {"status": "FOUND", "template": template}

    def _history(self, arguments: dict[str, Any]) -> dict[str, Any]:
        email = (arguments.get("email") or "").lower()
        inquiry_id = arguments.get("inquiry_id")
        items = self._PAST
        if email:
            items = [i for i in items if i["email"].lower() == email]
        if inquiry_id:
            items = [i for i in items if i["id"] == inquiry_id]
        return {"status": "FOUND" if items else "NOT_REGISTERED", "items": items}


class HttpxWebAPIProvider:
    """
    Real async httpx path for later phases.
    Phase 1: refuses to run unless explicitly enabled; still only approved endpoints.
    """

    name = "httpx_web_api"

    def __init__(self, *, enabled: bool = False) -> None:
        self.enabled = enabled

    async def execute(self, tool: ToolDefinition, arguments: dict[str, Any]) -> Any:
        if not self.enabled:
            raise RuntimeError(
                "HttpxWebAPIProvider disabled in Phase 1; use MockWebAPIProvider"
            )
        endpoint = tool.execution_policy.approved_endpoint
        if not endpoint or endpoint.startswith("mock://"):
            raise PermissionError("Refusing non-HTTP or mock endpoint on httpx provider")
        # Intentionally not implementing live calls in Phase 1.
        raise NotImplementedError("Real httpx execution lands in a later phase")
