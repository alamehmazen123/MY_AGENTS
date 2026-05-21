"""cells/mcp/registry.py — Schema-aware, policy-driven MCP registry."""
from __future__ import annotations
from kernel.mcp.protocol.tool_registry import ToolRegistry
from kernel.mcp.protocol.adapter import InternalToolAdapter
from kernel.mcp.protocol.tool_definition import ToolCapability
from kernel.security.execution_policy import ExecutionPolicy
from kernel.security.resource_limits import ResourceLimits
from kernel.config import settings


class MCPRegistry(ToolRegistry):
    """
    Extended registry that registers all 14 presets with proper
    capabilities, policies, and resource limits.
    """

    def __init__(self):
        super().__init__()
        self._workspace_root = settings.workspace_root

    def register_preset(self, name: str, description: str = "", handler=None,
                        capabilities: set[str] = None, limits: ResourceLimits = None,
                        timeout: float = 60.0):
        if capabilities is None:
            capabilities = set()
        policy = ExecutionPolicy(
            allow_filesystem=ToolCapability.FILESYSTEM in capabilities,
            allow_network=ToolCapability.NETWORK in capabilities,
            allow_subprocess=ToolCapability.SUBPROCESS in capabilities,
            allow_shell=ToolCapability.SHELL in capabilities,
            allow_git=ToolCapability.GIT in capabilities,
            limits=limits or ResourceLimits(),
        )
        tool = InternalToolAdapter.adapt(
            name=name,
            description=description,
            handler=handler,
            capabilities=capabilities,
            policy=policy,
            timeout=timeout,
        )
        self.register(tool)

    def load(self, name: str):
        """Backwards-compat: return handler from ToolDefinition."""
        tool = self.get(name)
        if tool is None:
            return None
        return tool.handler
