from __future__ import annotations

from functools import lru_cache
from typing import Optional

from app.registry.types import ToolDefinition


class ToolRegistry:
    """Centralized registry of approved tools only."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool already registered: {tool.name}")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[ToolDefinition]:
        return self._tools.get(name)

    def list(self, *, enabled_only: bool = False) -> list[ToolDefinition]:
        tools = list(self._tools.values())
        if enabled_only:
            tools = [t for t in tools if t.enabled]
        return sorted(tools, key=lambda t: t.name)

    def require(self, name: str) -> ToolDefinition:
        tool = self.get(name)
        if tool is None:
            raise KeyError(f"Unknown tool: {name}")
        if not tool.enabled:
            raise PermissionError(f"Tool disabled: {name}")
        return tool


@lru_cache
def get_registry() -> ToolRegistry:
    from app.registry.catalog import build_default_registry

    return build_default_registry()
