"""100-run MCP stress test for file_explorer, workspace_indexer, search_ripgrep."""
import sys
import asyncio
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cells.mcp.cell import MCPCell

RUNS = 100
PRESETS = ["file_explorer", "workspace_indexer", "search_ripgrep"]

ARGS_MAP = {
    "file_explorer": {"action": "list", "path": "."},
    "workspace_indexer": {"action": "index", "path": "."},
    "search_ripgrep": {"query": "def main", "path": "."},
}

async def main():
    mcp = MCPCell()
    await mcp.init()

    metrics = {}
    for preset in PRESETS:
        args = ARGS_MAP[preset]
        passes = 0
        fails = 0
        errors = []
        latencies = []
        start_total = time.time()
        for i in range(RUNS):
            t0 = time.time()
            try:
                result = await mcp.invoke(preset, args)
                latency = time.time() - t0
                latencies.append(latency)
                status = result.get("status", "error")
                if status == "ok":
                    passes += 1
                else:
                    fails += 1
                    errors.append(f"run {i}: status={status} msg={result.get('error_message','')[:200]}")
            except Exception as e:
                fails += 1
                latency = time.time() - t0
                latencies.append(latency)
                errors.append(f"run {i}: exception={type(e).__name__}: {e}")
        total = time.time() - start_total
        metrics[preset] = {
            "runs": RUNS,
            "passes": passes,
            "fails": fails,
            "total_time_sec": round(total, 2),
            "avg_latency_ms": round((sum(latencies)/len(latencies))*1000, 2) if latencies else None,
            "min_latency_ms": round(min(latencies)*1000, 2) if latencies else None,
            "max_latency_ms": round(max(latencies)*1000, 2) if latencies else None,
            "errors": errors[:5],
        }

    await mcp.shutdown()

    print("\n=== MCP STRESS TEST RESULTS ===")
    all_pass = True
    for preset, m in metrics.items():
        status = "PASS" if m["fails"] == 0 else "FAIL"
        if m["fails"] > 0:
            all_pass = False
        print(f"{preset}: {status} | runs={m['runs']} pass={m['passes']} fail={m['fails']} "
              f"total={m['total_time_sec']}s avg={m['avg_latency_ms']}ms "
              f"min={m['min_latency_ms']}ms max={m['max_latency_ms']}ms")
        for err in m["errors"]:
            print(f"  ERR: {err}")
    print(f"OVERALL: {'PASS' if all_pass else 'FAIL'}")

    # Write raw metrics file
    import json
    Path("audit_mcp_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print("Raw metrics saved to audit_mcp_metrics.json")

if __name__ == "__main__":
    asyncio.run(main())
