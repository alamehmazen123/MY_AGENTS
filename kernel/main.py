"""
kernel/main.py — Entry Point, Lifespan Manager
Only `python main.py` starts the system.
"""
from __future__ import annotations
import asyncio
import signal
import sys
from contextlib import asynccontextmanager
from pathlib import Path

# Ensure project root on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kernel.config import settings
from kernel.universe import universe
from kernel.events import bus, Event
from kernel.resolution_table import table
from kernel.lattice_verifier import verifier
from kernel.recovery_invariant import make_recovery_engine, RECOVERY_SPEC

# Cell imports (will be populated as cells register)
CELL_REGISTRY: dict = {}


class LifespanManager:
    """Orchestrates startup ordering, cell lifecycle, shutdown coordination."""
    
    def __init__(self):
        self.running = False
        self._shutdown_event = asyncio.Event()
        self._tasks: list[asyncio.Task] = []
        self._recovery = make_recovery_engine(universe, bus)
    
    async def start(self):
        print(f"[main] Starting my_agents PRIS v12.0")
        print(f"[main] Environment: {settings.env}")
        print(f"[main] Data dir: {settings.data_dir}")
        
        # 1. Verify lattice integrity
        assert verifier.verify(), "Lattice verification failed — system cannot start"
        print("[main] Lattice integrity: VERIFIED")
        
        # 2. Load resolution table
        print(f"[main] Resolution table loaded: {table.size} scenarios")
        
        # 3. Verify event chain
        if not bus.verify_chain():
            print("[main] WARNING: Event chain integrity failed — attempting recovery")
            await self._recovery.execute()
        else:
            print("[main] Event chain integrity: VERIFIED")
        
        # 4. Initialize cells in dependency order
        await self._init_cells()
        
        # 5. Start snapshot loop
        self._tasks.append(asyncio.create_task(self._snapshot_loop()))
        
        # 6. Start self-test loop
        self._tasks.append(asyncio.create_task(self._self_test_loop()))
        
        self.running = True
        print("[main] System ONLINE")
        await bus.emit("system.online", {"version": "12.0", "spec": "PRIS"})
    
    async def _init_cells(self):
        # Import and initialize cells in order: reflex -> runtime -> deliberation -> workspace -> mcp -> evolution -> gateway
        from cells.reflex.cell import ReflexCell
        from cells.runtime.cell import RuntimeCell
        from cells.deliberation.cell import DeliberationCell
        from cells.workspace.cell import WorkspaceCell
        from cells.mcp.cell import MCPCell
        from cells.evolution.cell import EvolutionCell
        from cells.gateway.cell import GatewayCell
        
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
            CELL_REGISTRY[cell.name] = cell
            print(f"[main] Cell initialized: {cell.name}")
    
    async def _snapshot_loop(self):
        while not self._shutdown_event.is_set():
            try:
                await asyncio.wait_for(self._shutdown_event.wait(), timeout=settings.snapshot_interval_seconds)
            except asyncio.TimeoutError:
                await self._recovery.take_snapshot()
    
    async def _self_test_loop(self):
        while not self._shutdown_event.is_set():
            try:
                await asyncio.wait_for(self._shutdown_event.wait(), timeout=RECOVERY_SPEC["self_test_interval_seconds"])
            except asyncio.TimeoutError:
                ok = await self._recovery.self_test()
                if not ok:
                    print("[main] WARNING: Self-test failed")
    
    async def shutdown(self):
        print("[main] Shutdown initiated...")
        self.running = False
        self._shutdown_event.set()
        for t in self._tasks:
            t.cancel()
            try:
                await t
            except asyncio.CancelledError:
                pass
        for cell in CELL_REGISTRY.values():
            await cell.shutdown()
        await bus.emit("system.offline", {"reason": "shutdown"})
        print("[main] System OFFLINE")
    
    def signal_handler(self, sig):
        print(f"[main] Received signal {sig}")
        asyncio.create_task(self.shutdown())


# Global lifespan
lifespan = LifespanManager()


def main():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def _run():
        # Register Unix signal handlers once loop is running
        try:
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(sig, lambda s=sig: lifespan.signal_handler(s))
        except NotImplementedError:
            pass  # Windows ProactorEventLoop — rely on KeyboardInterrupt
        await lifespan.start()
        await lifespan._shutdown_event.wait()

    try:
        loop.run_until_complete(_run())
    except KeyboardInterrupt:
        print("[main] KeyboardInterrupt received")
    finally:
        if lifespan.running:
            loop.run_until_complete(lifespan.shutdown())
        loop.close()
        print("[main] Exited cleanly")


if __name__ == "__main__":
    main()
