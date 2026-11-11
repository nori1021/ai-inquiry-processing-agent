from __future__ import annotations

from typing import Any, Protocol

from app.registry.types import ToolDefinition
from app.tools.company_lookup import get_company_by_domain, get_ldap_company
from app.tools.gac_lookup import get_gac_user, get_gac_users_by_domain
from app.tools.ldap_lookup import get_ldap_user


class PowerShellProvider(Protocol):
    name: str

    async def execute(
        self,
        tool: ToolDefinition,
        arguments: dict[str, Any],
    ) -> Any: ...


APPROVED_SCRIPTS = {
    "ps/lookup_ldap_user",
    "ps/lookup_gac_user",
    "ps/lookup_ldap_company",
    "ps/lookup_gac_company_users",
}


class MockPowerShellProvider:
    """
    Phase 1 dual-path: PowerShell tool names execute via Python Excel backends.
    Never runs arbitrary shell commands or AI-generated scripts.
    """

    name = "mock_powershell"

    def _assert_approved(self, tool: ToolDefinition) -> None:
        script_id = tool.execution_policy.approved_script_id
        if not script_id or script_id not in APPROVED_SCRIPTS:
            raise PermissionError(f"Script id not approved: {script_id!r}")

    async def execute(self, tool: ToolDefinition, arguments: dict[str, Any]) -> Any:
        self._assert_approved(tool)
        script_id = tool.execution_policy.approved_script_id
        assert script_id is not None

        if script_id == "ps/lookup_ldap_user":
            return get_ldap_user(str(arguments["email"])).model_dump(mode="json")
        if script_id == "ps/lookup_gac_user":
            return get_gac_user(str(arguments["email"])).model_dump(mode="json")
        if script_id == "ps/lookup_ldap_company":
            company_id = arguments.get("company_id")
            domain = arguments.get("domain")
            if company_id:
                return get_ldap_company(str(company_id)).model_dump(mode="json")
            if domain:
                return get_company_by_domain(str(domain)).model_dump(mode="json")
            raise ValueError("lookup_ldap_company requires company_id or domain")
        if script_id == "ps/lookup_gac_company_users":
            return get_gac_users_by_domain(str(arguments["domain"])).model_dump(
                mode="json"
            )
        raise PermissionError(f"No mock handler for script: {script_id}")
