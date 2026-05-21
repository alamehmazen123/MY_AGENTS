"""kernel/mcp/protocol — MCP abstraction layer for internal and external tools."""
from .tool_definition import ToolDefinition, ToolSchema, ToolCapability
from .tool_registry import ToolRegistry
from .adapter import InternalToolAdapter

__all__ = ["ToolDefinition", "ToolSchema", "ToolCapability", "ToolRegistry", "InternalToolAdapter"]
