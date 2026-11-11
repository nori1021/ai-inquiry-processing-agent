from __future__ import annotations

import time
from functools import lru_cache
from typing import Any, Optional

from app.providers.audit import record_tool_audit
from app.providers.powershell import MockPowerShellProvider
from app.providers.web_api import MockWebAPIProvider
from app.registry.registry import ToolRegistry, get_registry
from app.registry.types import ToolDefinition, ToolExecuteResult, ToolKind
from app.tools.company_lookup import find_similar_domains
from app.tools.gac_lookup import get_gac_user
from app.tools.ldap_lookup import get_ldap_user
from app.tools.registration_check import (
    check_gac_registration,
    check_ldap_gac_registration,
    check_ldap_registration,
)


def validate_arguments(schema: dict[str, Any], arguments: dict[str, Any]) -> None:
    """Lightweight JSON-schema subset validation (required + additionalProperties + types)."""
    if not isinstance(arguments, dict):
        raise ValueError("arguments must be an object")

    required = schema.get("required") or []
    for key in required:
        if key not in arguments or arguments[key] in (None, ""):
            raise ValueError(f"Missing required argument: {key}")

    if schema.get("additionalProperties") is False:
        allowed = set((schema.get("properties") or {}).keys())
        unknown = set(arguments.keys()) - allowed
        if unknown:
            raise ValueError(f"Unexpected arguments: {sorted(unknown)}")

    properties = schema.get("properties") or {}
    for key, value in arguments.items():
        prop = properties.get(key)
        if not prop:
            continue
        expected = prop.get("type")
        if expected == "string" and not isinstance(value, str):
            raise ValueError(f"Argument {key} must be a string")
        if expected == "integer" and not isinstance(value, int):
            raise ValueError(f"Argument {key} must be an integer")
        if expected == "number" and not isinstance(value, (int, float)):
            raise ValueError(f"Argument {key} must be a number")
        if "minimum" in prop and isinstance(value, (int, float)) and value < prop["minimum"]:
            raise ValueError(f"Argument {key} below minimum")
        if "maximum" in prop and isinstance(value, (int, float)) and value > prop["maximum"]:
            raise ValueError(f"Argument {key} above maximum")
        if (
            expected == "string"
            and "minLength" in prop
            and isinstance(value, str)
            and len(value) < prop["minLength"]
        ):
            raise ValueError(f"Argument {key} shorter than minLength")


class ToolExecutor:
    def __init__(
        self,
        registry: Optional[ToolRegistry] = None,
        *,
        web_api: Optional[MockWebAPIProvider] = None,
        powershell: Optional[MockPowerShellProvider] = None,
    ) -> None:
        self.registry = registry or get_registry()
        self.web_api = web_api or MockWebAPIProvider()
        self.powershell = powershell or MockPowerShellProvider()

    async def execute(self, name: str, arguments: dict[str, Any]) -> ToolExecuteResult:
        started = time.perf_counter()
        provider_name = "unknown"
        try:
            tool = self.registry.require(name)
            validate_arguments(tool.input_schema, arguments)
            provider_name, result = await self._dispatch(tool, arguments)
            duration_ms = (time.perf_counter() - started) * 1000
            if tool.execution_policy.audit:
                record_tool_audit(
                    tool_name=name,
                    provider=provider_name,
                    ok=True,
                    arguments=arguments,
                    duration_ms=duration_ms,
                )
            return ToolExecuteResult(
                tool=name,
                ok=True,
                result=result,
                provider=provider_name,
                duration_ms=duration_ms,
            )
        except Exception as exc:  # noqa: BLE001 — map to structured error result
            duration_ms = (time.perf_counter() - started) * 1000
            record_tool_audit(
                tool_name=name,
                provider=provider_name,
                ok=False,
                arguments=arguments,
                error=str(exc),
                duration_ms=duration_ms,
            )
            return ToolExecuteResult(
                tool=name,
                ok=False,
                error=str(exc),
                provider=provider_name,
                duration_ms=duration_ms,
            )

    async def _dispatch(
        self, tool: ToolDefinition, arguments: dict[str, Any]
    ) -> tuple[str, Any]:
        if tool.kind == ToolKind.WEB_API:
            return self.web_api.name, await self.web_api.execute(tool, arguments)
        if tool.kind == ToolKind.POWERSHELL:
            return self.powershell.name, await self.powershell.execute(tool, arguments)
        if tool.kind == ToolKind.PYTHON_LOCAL:
            return "python_local", self._python_local(tool, arguments)
        raise ValueError(f"Unsupported tool kind: {tool.kind}")

    def _python_local(self, tool: ToolDefinition, arguments: dict[str, Any]) -> Any:
        if tool.name == "get_ldap_user":
            return get_ldap_user(str(arguments["email"])).model_dump(mode="json")
        if tool.name == "get_gac_user":
            return get_gac_user(str(arguments["email"])).model_dump(mode="json")
        if tool.name == "find_similar_domains":
            threshold = arguments.get("threshold")
            return find_similar_domains(
                str(arguments["domain"]),
                threshold=float(threshold) if threshold is not None else None,
            ).model_dump(mode="json")
        if tool.name == "check_ldap_registration":
            return check_ldap_registration(
                email=arguments.get("email"),
                user_id=arguments.get("user_id"),
            ).model_dump(mode="json")
        if tool.name == "check_gac_registration":
            return check_gac_registration(
                email=arguments.get("email"),
                user_id=arguments.get("user_id"),
            ).model_dump(mode="json")
        if tool.name == "check_ldap_gac_registration":
            return check_ldap_gac_registration(
                email=arguments.get("email"),
                user_id=arguments.get("user_id"),
            ).model_dump(mode="json")
        raise ValueError(f"No python_local handler for {tool.name}")


@lru_cache
def get_executor() -> ToolExecutor:
    return ToolExecutor()
