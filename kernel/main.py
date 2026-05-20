"""
kernel/main.py — Entry Point, Lifespan Manager
Only `python main.py` starts the system.
"""
from __future__ import annotations
import asyncio
import signal
import socket
import subprocess
import sys
import time
import webbrowser
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
        self._frontend_proc = None
        self._frontend_log = None
    
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
        
        # 4b. Start gateway servers
        gateway = CELL_REGISTRY.get("gateway")
        if gateway:
            await gateway.start_servers()
            print(f"[main] Gateway listening on API:{settings.api_port} WS:{settings.ws_port}")
        
        # 4c. Start frontend dev server
        frontend_ok = await self._start_frontend()
        
        # 5. Start snapshot loop
        self._tasks.append(asyncio.create_task(self._snapshot_loop()))
        
        # 6. Start self-test loop
        self._tasks.append(asyncio.create_task(self._self_test_loop()))
        
        self.running = True
        print("[main] System ONLINE")
        await bus.emit("system.online", {"version": "12.0", "spec": "PRIS"})
        
        # 7. Open browser
        if frontend_ok:
            self._open_edge("http://localhost:5173")
        else:
            print("[main] WARNING: Frontend not available — open http://localhost:5173 manually once fixed")
    
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
        if self._frontend_proc:
            self._frontend_proc.terminate()
            try:
                self._frontend_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._frontend_proc.kill()
        if self._frontend_log:
            self._frontend_log.close()
        await bus.emit("system.offline", {"reason": "shutdown"})
        print("[main] System OFFLINE")
    
    async def _start_frontend(self) -> bool:
        frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
        if not (frontend_dir / "package.json").exists():
            print("[main] Frontend not found, skipping")
            return False

        # Auto-install dependencies if missing
        if not (frontend_dir / "node_modules").exists():
            print("[main] node_modules missing — running npm install...")
            try:
                result = subprocess.run(
                    ["npm", "install"],
                    cwd=str(frontend_dir),
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                if result.returncode != 0:
                    print(f"[main] npm install failed:\n{result.stderr}")
                    return False
                print("[main] npm install completed")
            except FileNotFoundError:
                print("[main] npm not found. Install Node.js or run 'cd frontend && npm install' manually.")
                return False
            except subprocess.TimeoutExpired:
                print("[main] npm install timed out (>120s)")
                return False

        log_path = frontend_dir / "dev-server.log"
        self._frontend_log = open(log_path, "w", encoding="utf-8")
        try:
            if sys.platform == "win32":
                self._frontend_proc = subprocess.Popen(
                    "npm run dev",
                    cwd=str(frontend_dir),
                    stdout=self._frontend_log,
                    stderr=subprocess.STDOUT,
                    shell=True,
                )
            else:
                self._frontend_proc = subprocess.Popen(
                    ["npm", "run", "dev"],
                    cwd=str(frontend_dir),
                    stdout=self._frontend_log,
                    stderr=subprocess.STDOUT,
                )
            print("[main] Frontend dev server starting (log: frontend/dev-server.log)...")
        except FileNotFoundError:
            print("[main] npm not found, frontend will not start")
            self._frontend_log.close()
            return False

        # Wait for Vite to bind
        for _ in range(20):
            await asyncio.sleep(0.5)
            if self._port_open("localhost", 5173):
                print("[main] Frontend ready on http://localhost:5173")
                return True

        print("[main] Frontend dev server did not start on port 5173 — check frontend/dev-server.log")
        return False

    def _port_open(self, host: str, port: int) -> bool:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return True
        except OSError:
            return False

    def _open_edge(self, url: str):
        print(f"[main] Opening {url} in Microsoft Edge...")
        if sys.platform == "win32":
            subprocess.Popen(["cmd", "/c", "start", "msedge", url])
        elif sys.platform == "darwin":
            subprocess.Popen(["open", "-a", "Microsoft Edge", url])
        else:
            try:
                subprocess.Popen(["microsoft-edge", url])
            except FileNotFoundError:
                webbrowser.open(url)

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
