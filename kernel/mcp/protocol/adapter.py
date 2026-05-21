"""kernel/mcp/protocol/adapter.py — Bridge internal tools to MCP protocol."""
from __future__ import annotations
from typing import Any
from .tool_definition import ToolDefinition


class InternalToolAdapter:
    """Wraps a legacy handle(args) function into a ToolDefinition."""

    @staticmethod
    def adapt(name: str, description: str, handler, capabilities: set[str], policy, timeout: float = 60.0) -> ToolDefinition:
        from .tool_definition import ToolSchema
        return ToolDefinition(
            name=name,
            description=description,
            schema=ToolSchema(name=name, description=description),
            capabilities=capabilities,
            policy=policy,
            timeout=timeout,
            handler=handler,
        )
