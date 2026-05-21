"""
Forensic diagnostic script — tests every layer of the system.
Run with: python debug_trace.py
"""
import sys
import json
import asyncio
import traceback
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent))

LOG_LINES = []

def log(stage: str, status: str, detail: str = ""):
    line = f"[{datetime.utcnow().isoformat()}] [{stage}] {status}" + (f" | {detail}" if detail else "")
    print(line)
    LOG_LINES.append(line)

async def phase_3_ollama_connectivity():
    log("PHASE 3", "START", "Ollama Connectivity")
    import httpx
    from kernel.config import settings

    # 3a: GET /api/tags
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            res = await client.get(f"{settings.ollama_host}/api/tags")
            log("PHASE 3a", "PASS" if res.status_code == 200 else "FAIL", f"status={res.status_code} body={res.text[:500]}")
    except Exception as e:
        log("PHASE 3a", "FAIL", f"exception={type(e).__name__}: {e}")

    # 3b: GET /api/ps
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            res = await client.get(f"{settings.ollama_host}/api/ps")
            log("PHASE 3b", "PASS" if res.status_code == 200 else "FAIL", f"status={res.status_code} body={res.text[:500]}")
    except Exception as e:
        log("PHASE 3b", "FAIL", f"exception={type(e).__name__}: {e}")

    # 3c: Direct generation with Agent-A model (deepseek-coder:1.3b)
    model_a = "deepseek-coder:1.3b"
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            payload = {
                "model": model_a,
                "prompt": "What is 2+2? Answer with one word.",
                "stream": False,
                "system": "You are a helpful assistant. Be concise.",
                "keep_alive": 0,
            }
            res = await client.post(f"{settings.ollama_host}/api/generate", json=payload, timeout=60)
            if res.status_code == 200:
                data = res.json()
                response = data.get("response", "").strip()
                log("PHASE 3c", "PASS", f"model={model_a} response='{response[:200]}' done={data.get('done')}")
            else:
                log("PHASE 3c", "FAIL", f"model={model_a} status={res.status_code} body={res.text[:500]}")
    except Exception as e:
        log("PHASE 3c", "FAIL", f"model={model_a} exception={type(e).__name__}: {e}")

    # 3d: Direct generation with Agent-B model (qwen2.5-coder:7b)
    model_b = "qwen2.5-coder:7b"
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            payload = {
                "model": model_b,
                "prompt": "What is 2+2? Answer with one word.",
                "stream": False,
                "system": "You are a helpful assistant. Be concise.",
                "keep_alive": 0,
            }
            res = await client.post(f"{settings.ollama_host}/api/generate", json=payload, timeout=60)
            if res.status_code == 200:
                data = res.json()
                response = data.get("response", "").strip()
                log("PHASE 3d", "PASS", f"model={model_b} response='{response[:200]}' done={data.get('done')}")
            else:
                log("PHASE 3d", "FAIL", f"model={model_b} status={res.status_code} body={res.text[:500]}")
    except Exception as e:
        log("PHASE 3d", "FAIL", f"model={model_b} exception={type(e).__name__}: {e}")

async def phase_4_model_lifecycle():
    log("PHASE 4", "START", "Model Lifecycle")
    from cells.runtime.model_manager import ModelManager
    mm = ModelManager()

    # Before Agent-A
    verify_before = await mm.verify_zero_loaded()
    log("PHASE 4-before-A", "PASS" if verify_before["zero_loaded"] else "FAIL", f"running={verify_before['running_models']}")

    # Load Agent-A
    ok = await mm.load("deepseek-coder:1.3b")
    verify_loaded_a = await mm.verify_zero_loaded()
    log("PHASE 4-load-A", "PASS" if ok else "FAIL", f"loaded={ok} running={verify_loaded_a['running_models']}")

    # Unload Agent-A
    ok_unload = await mm.unload("deepseek-coder:1.3b")
    verify_after_a = await mm.verify_zero_loaded()
    log("PHASE 4-after-A", "PASS" if verify_after_a["zero_loaded"] else "FAIL", f"unloaded={ok_unload} running={verify_after_a['running_models']}")

    # Load Agent-B
    ok_b = await mm.load("qwen2.5-coder:7b")
    verify_loaded_b = await mm.verify_zero_loaded()
    log("PHASE 4-load-B", "PASS" if ok_b else "FAIL", f"loaded={ok_b} running={verify_loaded_b['running_models']}")

    # Unload Agent-B
    ok_unload_b = await mm.unload("qwen2.5-coder:7b")
    verify_after_b = await mm.verify_zero_loaded()
    log("PHASE 4-after-B", "PASS" if verify_after_b["zero_loaded"] else "FAIL", f"unloaded={ok_unload_b} running={verify_after_b['running_models']}")

async def phase_5_agent_a_isolation():
    log("PHASE 5", "START", "Agent-A in isolation")
    from cells.gateway.rest import RESTServer
    server = RESTServer(gateway=None)
    # Simulate a prompt request
    import httpx
    from kernel.config import settings

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            payload = {
                "model": "deepseek-coder:1.3b",
                "prompt": "What is 2+2? Answer with one word.",
                "system": "You are a helpful assistant. Be concise.",
                "stream": False,
                "no_tools": True,
                "keep_alive": 0,
            }
            res = await client.post(f"{settings.ollama_host}/api/generate", json=payload, timeout=60)
            if res.status_code == 200:
                data = res.json()
                response = data.get("response", "").strip()
                log("PHASE 5", "PASS", f"response='{response[:200]}'")
            else:
                log("PHASE 5", "FAIL", f"status={res.status_code} body={res.text[:500]}")
    except Exception as e:
        log("PHASE 5", "FAIL", f"exception={type(e).__name__}: {e}")

async def phase_8_mcp_execution():
    log("PHASE 8", "START", "MCP Execution")
    from cells.mcp.cell import MCPCell
    mcp = MCPCell()
    await mcp.init()

    # Test file_explorer
    try:
        result = await mcp.invoke("file_explorer", {"action": "list", "path": "."})
        status = result.get("status", "error")
        log("PHASE 8-file_explorer", "PASS" if status == "ok" else "FAIL", f"status={status} keys={list(result.keys())}")
    except Exception as e:
        log("PHASE 8-file_explorer", "FAIL", f"exception={type(e).__name__}: {e}")

    # Test workspace_indexer
    try:
        result = await mcp.invoke("workspace_indexer", {"action": "index", "path": "."})
        status = result.get("status", "error")
        log("PHASE 8-workspace_indexer", "PASS" if status == "ok" else "FAIL", f"status={status} keys={list(result.keys())}")
    except Exception as e:
        log("PHASE 8-workspace_indexer", "FAIL", f"exception={type(e).__name__}: {e}")

    # Test search_ripgrep
    try:
        result = await mcp.invoke("search_ripgrep", {"query": "def main", "path": "."})
        status = result.get("status", "error")
        log("PHASE 8-search_ripgrep", "PASS" if status == "ok" else "FAIL", f"status={status} keys={list(result.keys())}")
    except Exception as e:
        log("PHASE 8-search_ripgrep", "FAIL", f"exception={type(e).__name__}: {e}")

    await mcp.shutdown()

async def phase_9_folder_analysis():
    log("PHASE 9", "START", "Folder Analysis Workflow")
    from cells.gateway.rest import RESTServer
    server = RESTServer(gateway=None)
    import httpx
    from kernel.config import settings

    prompt = "List all Python files in workspace."
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            payload = {
                "model": "deepseek-coder:1.3b",
                "prompt": prompt,
                "system": "You are a helpful assistant.",
                "stream": False,
                "no_tools": True,
                "keep_alive": 0,
            }
            res = await client.post(f"{settings.ollama_host}/api/generate", json=payload, timeout=60)
            if res.status_code == 200:
                data = res.json()
                response = data.get("response", "").strip()
                log("PHASE 9", "PASS", f"response='{response[:300]}'")
            else:
                log("PHASE 9", "FAIL", f"status={res.status_code} body={res.text[:500]}")
    except Exception as e:
        log("PHASE 9", "FAIL", f"exception={type(e).__name__}: {e}")

async def main():
    log("SYSTEM", "INFO", f"Python {sys.version}")
    log("SYSTEM", "INFO", f"CWD {Path.cwd()}")

    await phase_3_ollama_connectivity()
    await phase_4_model_lifecycle()
    await phase_5_agent_a_isolation()
    await phase_8_mcp_execution()
    await phase_9_folder_analysis()

    # Write report
    report_path = Path("docs/debug_failure_trace.md")
    report_path.write_text("\n".join(LOG_LINES), encoding="utf-8")
    log("SYSTEM", "INFO", f"Report written to {report_path}")

if __name__ == "__main__":
    asyncio.run(main())
