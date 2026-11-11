from __future__ import annotations

from app.registry.registry import ToolRegistry
from app.registry.types import ExecutionPolicy, ToolDefinition, ToolKind, ToolPermission

EMAIL_INPUT = {
    "type": "object",
    "properties": {"email": {"type": "string", "minLength": 1}},
    "required": ["email"],
    "additionalProperties": False,
}

DOMAIN_OR_ID_INPUT = {
    "type": "object",
    "properties": {
        "company_id": {"type": "string"},
        "domain": {"type": "string"},
    },
    "additionalProperties": False,
}

DOMAIN_INPUT = {
    "type": "object",
    "properties": {"domain": {"type": "string", "minLength": 1}},
    "required": ["domain"],
    "additionalProperties": False,
}

REGISTRATION_CHECK_INPUT = {
    "type": "object",
    "properties": {
        "email": {"type": "string", "minLength": 1},
        "user_id": {"type": "string", "minLength": 1},
    },
    "additionalProperties": False,
}


def build_default_registry() -> ToolRegistry:
    registry = ToolRegistry()

    # --- Web API tools (mock endpoints only) ---
    registry.register(
        ToolDefinition(
            name="search_past_inquiries",
            kind=ToolKind.WEB_API,
            description="Search past helpdesk inquiries by keyword.",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "minLength": 1},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 10},
                },
                "required": ["query"],
                "additionalProperties": False,
            },
            execution_policy=ExecutionPolicy(
                approved_endpoint="mock://webapi/past-inquiries/search",
                auth_profile="mock",
                timeout_seconds=5.0,
            ),
        )
    )
    registry.register(
        ToolDefinition(
            name="search_knowledge_base",
            kind=ToolKind.WEB_API,
            description="Search the knowledge base for relevant articles.",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "minLength": 1},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 10},
                },
                "required": ["query"],
                "additionalProperties": False,
            },
            execution_policy=ExecutionPolicy(
                approved_endpoint="mock://webapi/kb/search",
                auth_profile="mock",
                timeout_seconds=5.0,
            ),
        )
    )
    registry.register(
        ToolDefinition(
            name="get_reply_template",
            kind=ToolKind.WEB_API,
            description="Fetch a reply email template by template id.",
            input_schema={
                "type": "object",
                "properties": {"template_id": {"type": "string", "minLength": 1}},
                "required": ["template_id"],
                "additionalProperties": False,
            },
            execution_policy=ExecutionPolicy(
                approved_endpoint="mock://webapi/templates/{template_id}",
                auth_profile="mock",
                timeout_seconds=5.0,
            ),
        )
    )
    registry.register(
        ToolDefinition(
            name="get_inquiry_history",
            kind=ToolKind.WEB_API,
            description="Get inquiry history for an email address or inquiry id.",
            input_schema={
                "type": "object",
                "properties": {
                    "email": {"type": "string"},
                    "inquiry_id": {"type": "string"},
                },
                "additionalProperties": False,
            },
            execution_policy=ExecutionPolicy(
                approved_endpoint="mock://webapi/inquiries/history",
                auth_profile="mock",
                timeout_seconds=5.0,
            ),
        )
    )

    # --- PowerShell tools (Phase 1 mock → Excel Python tools) ---
    registry.register(
        ToolDefinition(
            name="lookup_ldap_user",
            kind=ToolKind.POWERSHELL,
            description="Lookup a user in LDAP by exact email (case-insensitive).",
            input_schema=EMAIL_INPUT,
            execution_policy=ExecutionPolicy(
                approved_script_id="ps/lookup_ldap_user",
                auth_profile="mock",
                timeout_seconds=10.0,
            ),
        )
    )
    registry.register(
        ToolDefinition(
            name="lookup_gac_user",
            kind=ToolKind.POWERSHELL,
            description="Lookup a user in GAC by exact email (case-insensitive).",
            input_schema=EMAIL_INPUT,
            execution_policy=ExecutionPolicy(
                approved_script_id="ps/lookup_gac_user",
                auth_profile="mock",
                timeout_seconds=10.0,
            ),
        )
    )
    registry.register(
        ToolDefinition(
            name="lookup_ldap_company",
            kind=ToolKind.POWERSHELL,
            description="Lookup an LDAP company by company_id and/or email domain.",
            input_schema=DOMAIN_OR_ID_INPUT,
            execution_policy=ExecutionPolicy(
                approved_script_id="ps/lookup_ldap_company",
                auth_profile="mock",
                timeout_seconds=10.0,
            ),
        )
    )
    registry.register(
        ToolDefinition(
            name="lookup_gac_company_users",
            kind=ToolKind.POWERSHELL,
            description="List GAC users belonging to an email domain.",
            input_schema=DOMAIN_INPUT,
            execution_policy=ExecutionPolicy(
                approved_script_id="ps/lookup_gac_company_users",
                auth_profile="mock",
                timeout_seconds=10.0,
            ),
        )
    )

    # --- Demo/test registration checks (AI-selectable, Excel dual-path) ---
    registry.register(
        ToolDefinition(
            name="check_ldap_registration",
            kind=ToolKind.PYTHON_LOCAL,
            description=(
                "Confirm whether a user is registered in LDAP (synthetic Excel). "
                "Exact email/UserID match only; returns yes/no/unknown."
            ),
            input_schema=REGISTRATION_CHECK_INPUT,
            permissions=ToolPermission(allow_ai_selection=True),
            execution_policy=ExecutionPolicy(
                approved_script_id="python/check_ldap_registration",
                auth_profile="none",
                timeout_seconds=10.0,
            ),
        )
    )
    registry.register(
        ToolDefinition(
            name="check_gac_registration",
            kind=ToolKind.PYTHON_LOCAL,
            description=(
                "Confirm whether a user is registered in GAC (synthetic Excel). "
                "Exact email/UserID match only; returns yes/no/unknown."
            ),
            input_schema=REGISTRATION_CHECK_INPUT,
            permissions=ToolPermission(allow_ai_selection=True),
            execution_policy=ExecutionPolicy(
                approved_script_id="python/check_gac_registration",
                auth_profile="none",
                timeout_seconds=10.0,
            ),
        )
    )
    registry.register(
        ToolDefinition(
            name="check_ldap_gac_registration",
            kind=ToolKind.PYTHON_LOCAL,
            description=(
                "Combined LDAP+GAC registration check for demo/tests. "
                "Returns LDAP_AND_GAC / LDAP_ONLY / GAC_ONLY / NEITHER / UNKNOWN."
            ),
            input_schema=REGISTRATION_CHECK_INPUT,
            permissions=ToolPermission(allow_ai_selection=True),
            execution_policy=ExecutionPolicy(
                approved_script_id="python/check_ldap_gac_registration",
                auth_profile="none",
                timeout_seconds=10.0,
            ),
        )
    )

    # --- python_local mirrors for direct deterministic use ---
    for name, desc, schema, _ in [
        (
            "get_ldap_user",
            "Python-local LDAP user lookup (Excel).",
            EMAIL_INPUT,
            None,
        ),
        (
            "get_gac_user",
            "Python-local GAC user lookup (Excel).",
            EMAIL_INPUT,
            None,
        ),
        (
            "find_similar_domains",
            "Find similar company email domains (candidates only).",
            {
                "type": "object",
                "properties": {
                    "domain": {"type": "string", "minLength": 1},
                    "threshold": {"type": "number", "minimum": 0, "maximum": 100},
                },
                "required": ["domain"],
                "additionalProperties": False,
            },
            None,
        ),
    ]:
        registry.register(
            ToolDefinition(
                name=name,
                kind=ToolKind.PYTHON_LOCAL,
                description=desc,
                input_schema=schema,
                permissions=ToolPermission(allow_ai_selection=False),
                execution_policy=ExecutionPolicy(
                    approved_script_id=f"python/{name}",
                    auth_profile="none",
                    timeout_seconds=10.0,
                ),
            )
        )

    return registry
