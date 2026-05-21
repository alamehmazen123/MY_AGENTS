"""kernel/mcp/protocol/tool_registry.py — Schema-aware tool registry."""
from __future__ import annotations
from typing import Dict, Any
from .tool_definition import ToolDefinition


class ToolRegistry:
    """Registry for schema-based MCP tools."""

    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition):
        self._tools[tool.name] = tool

    def has(self, name: str) -> bool:
        return name in self._tools

    def get(self, name: str) -> ToolDefinition | None:
        return self._tools.get(name)

    def list_tools(self) -> list[dict]:
        return [
            {
                "name": t.name,
                "description": t.schema.description,
                "capabilities": sorted(t.capabilities),
                "timeout": t.timeout,
            }
            for t in self._tools.values()
        ]

    def summary(self) -> dict[str, Any]:
        return {
            "count": len(self._tools),
            "tools": {name: t.schema.description for name, t in self._tools.items()},
        }
