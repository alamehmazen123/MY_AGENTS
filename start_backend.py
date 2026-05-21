import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from cells.gateway.cell import GatewayCell
from cells.mcp.cell import MCPCell
from cells.runtime.cell import RuntimeCell
from cells.deliberation.cell import DeliberationCell
from cells.workspace.cell import WorkspaceCell
from cells.reflex.cell import ReflexCell
from cells.evolution.cell import EvolutionCell

async def main():
    # Initialize cells in dependency order
    cells = [
        ReflexCell(),
        RuntimeCell(),
        DeliberationCell(),
        WorkspaceCell(),
        MCPCell(),
        EvolutionCell(),
        GatewayCell(),
    ]
    for cell in cells:
        await cell.init()
        print(f"[backend] Cell initialized: {cell.name}")

    # Wire cross-cell references
    gateway = cells[-1]
    gateway._runtime = cells[1]
    gateway._deliberation = cells[2]
    gateway._mcp = cells[4]
    print("[backend] Cross-cell references wired")

    await gateway.start_servers()
    print("[backend] Gateway listening on API:8000 WS:8001")
    print("[backend] Press Ctrl+C to stop")

    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        print("[backend] Stopping...")
        for cell in reversed(cells):
            await cell.shutdown()
        print("[backend] Stopped")

if __name__ == "__main__":
    asyncio.run(main())
