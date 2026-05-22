"""Minimal server launcher for debugging — no browser, no frontend dev server."""
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from kernel.config import settings
from kernel.universe import universe
from kernel.events import bus
from kernel.lattice_verifier import verifier
from kernel.resolution_table import table

CELL_REGISTRY = {}

async def main():
    print("[test] Starting minimal server...")
    assert verifier.verify(), "Lattice verification failed"
    print("[test] Lattice OK")

    from cells.reflex.cell import ReflexCell
    from cells.runtime.cell import RuntimeCell
    from cells.deliberation.cell import DeliberationCell
    from cells.workspace.cell import WorkspaceCell
    from cells.mcp.cell import MCPCell
    from cells.evolution.cell import EvolutionCell
    from cells.gateway.cell import GatewayCell

    cells = [
        ReflexCell(), RuntimeCell(), DeliberationCell(),
        WorkspaceCell(), MCPCell(), EvolutionCell(), GatewayCell(),
    ]
    for cell in cells:
        await cell.init()
        CELL_REGISTRY[cell.name] = cell
        print(f"[test] Cell ready: {cell.name}")

    gateway = CELL_REGISTRY.get("gateway")
    if gateway:
        gateway._runtime = CELL_REGISTRY.get("runtime")
        gateway._deliberation = CELL_REGISTRY.get("deliberation")
        gateway._mcp = CELL_REGISTRY.get("mcp")
        await gateway.start_servers()
        print(f"[test] Gateway on port {settings.api_port}")

    mcp = CELL_REGISTRY.get("mcp")
    if mcp and mcp._registry:
        print(f"[test] MCP tools: {[t['name'] for t in mcp.list_tools()]}")

    print("[test] Server READY")
    # Keep alive
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
