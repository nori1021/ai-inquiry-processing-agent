from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class ToolKind(str, Enum):
    WEB_API = "web_api"
    POWERSHELL = "powershell"
    PYTHON_LOCAL = "python_local"


class ToolPermission(BaseModel):
    roles: list[str] = Field(default_factory=lambda: ["internal"])
    allow_ai_selection: bool = True
    requires_human_approval: bool = False


class ExecutionPolicy(BaseModel):
    """Restricts execution to approved endpoints/scripts only."""

    approved_endpoint: Optional[str] = None  # for web_api — static allowlist entry
    approved_script_id: Optional[str] = None  # for powershell — never raw commands
    auth_profile: str = "none"
    timeout_seconds: float = 10.0
    max_retries: int = 0
    validate_response: bool = True
    audit: bool = True


class ToolDefinition(BaseModel):
    name: str
    kind: ToolKind
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any] = Field(default_factory=dict)
    permissions: ToolPermission = Field(default_factory=ToolPermission)
    execution_policy: ExecutionPolicy = Field(default_factory=ExecutionPolicy)
    enabled: bool = True


class ToolExecuteRequest(BaseModel):
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolExecuteResult(BaseModel):
    tool: str
    ok: bool
    result: Any = None
    error: Optional[str] = None
    provider: str
    duration_ms: float = 0.0
