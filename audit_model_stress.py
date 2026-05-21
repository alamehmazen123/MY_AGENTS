"""50-cycle model load/unload stress test with zero-loaded verification."""
import sys
import asyncio
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cells.runtime.model_manager import ModelManager

CYCLES = 50
MODEL = "deepseek-coder:1.3b"  # small, fast

async def main():
    mm = ModelManager()
    passes = 0
    fails = 0
    errors = []
    latencies = []

    print(f"Starting {CYCLES} load/unload cycles for {MODEL}")

    for i in range(CYCLES):
        t0 = time.time()
        cycle_ok = True
        try:
            ok_load = await mm.load(MODEL)
            if not ok_load:
                cycle_ok = False
                errors.append(f"cycle {i}: load failed")

            ok_unload = await mm.unload(MODEL)
            if not ok_unload:
                cycle_ok = False
                errors.append(f"cycle {i}: unload failed")

            verify = await mm.verify_zero_loaded()
            if not verify["zero_loaded"]:
                cycle_ok = False
                errors.append(f"cycle {i}: zero_loaded FALSE running={verify['running_models']}")
        except Exception as e:
            cycle_ok = False
            errors.append(f"cycle {i}: exception={type(e).__name__}: {e}")

        latency = time.time() - t0
        latencies.append(latency)
        if cycle_ok:
            passes += 1
        else:
            fails += 1

        if (i + 1) % 10 == 0:
            print(f"  Progress: {i+1}/{CYCLES} done, fails={fails}")

    total = sum(latencies)
    print("\n=== MODEL LOAD/UNLOAD STRESS TEST RESULTS ===")
    print(f"cycles={CYCLES} pass={passes} fail={fails} total_time={round(total,2)}s "
          f"avg={round((total/CYCLES)*1000,2)}ms min={round(min(latencies)*1000,2)}ms max={round(max(latencies)*1000,2)}ms")
    for err in errors[:10]:
        print(f"  ERR: {err}")
    status = "PASS" if fails == 0 else "FAIL"
    print(f"OVERALL: {status}")

    import json
    metrics = {
        "cycles": CYCLES,
        "passes": passes,
        "fails": fails,
        "total_time_sec": round(total, 2),
        "avg_latency_ms": round((total/CYCLES)*1000, 2),
        "min_latency_ms": round(min(latencies)*1000, 2),
        "max_latency_ms": round(max(latencies)*1000, 2),
        "errors": errors,
    }
    Path("audit_model_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print("Raw metrics saved to audit_model_metrics.json")

if __name__ == "__main__":
    asyncio.run(main())
