from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.registry import get_executor, get_registry
from app.registry.types import ToolDefinition, ToolExecuteRequest, ToolExecuteResult

router = APIRouter()


@router.get("", response_model=list[ToolDefinition])
def list_tools(enabled_only: bool = False) -> list[ToolDefinition]:
    return get_registry().list(enabled_only=enabled_only)


@router.get("/{name}", response_model=ToolDefinition)
def get_tool(name: str) -> ToolDefinition:
    tool = get_registry().get(name)
    if tool is None:
        raise HTTPException(status_code=404, detail=f"Unknown tool: {name}")
    return tool


@router.post("/{name}/execute", response_model=ToolExecuteResult)
async def execute_tool(name: str, body: ToolExecuteRequest) -> ToolExecuteResult:
    result = await get_executor().execute(name, body.arguments)
    if not result.ok and result.error and result.error.startswith("Unknown tool"):
        raise HTTPException(status_code=404, detail=result.error)
    return result
