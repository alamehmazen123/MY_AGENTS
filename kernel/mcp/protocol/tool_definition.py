"""kernel/mcp/protocol/tool_definition.py — Schema-based tool contracts."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Type
from kernel.security.execution_policy import ExecutionPolicy
from kernel.security.resource_limits import ResourceLimits


class ToolCapability:
    FILESYSTEM = "filesystem"
    NETWORK = "network"
    SUBPROCESS = "subprocess"
    SHELL = "shell"
    GIT = "git"
    PYTHON_EXEC = "python_exec"


@dataclass(frozen=True)
class ToolSchema:
    """JSON-Schema-like description for tool arguments."""
    name: str
    description: str
    parameters: dict[str, Any] = field(default_factory=dict)
    required: list[str] = field(default_factory=list)


@dataclass
class ToolDefinition:
    """Complete description of an MCP tool."""
    name: str
    description: str
    schema: ToolSchema
    capabilities: set[str] = field(default_factory=set)
    policy: ExecutionPolicy = field(default_factory=ExecutionPolicy)
    timeout: float = 60.0
    handler: Callable | None = None

    def validate_args(self, args: dict) -> dict:
        """Basic schema validation — ensures required keys present."""
        missing = [k for k in self.schema.required if k not in args]
        if missing:
            raise ValueError(f"missing_required_args: {missing}")
        return args

    def invoke(self, args: dict) -> dict:
        if self.handler is None:
            return {"error": "handler_not_set", "preset": self.name}
        validated = self.validate_args(args)
        return self.handler(validated)
