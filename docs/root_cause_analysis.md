# Root Cause Analysis — my_agents PRIS v12.0

**Date:** 2026-05-21  
**Investigator:** Forensic diagnostic session  
**Scope:** Full pipeline from user prompt to agent output, including MCP tool execution.

---

## 1. Symptom

User prompt: *"I have a problem with the full system... it is making trades, but not closing any. There is a CLOSING_AGENT that should generate stop signals... Go through the folder, identify the issue, and make a fix plan."*

**Actual result observed by user:**
- Agent-A: `[Error:]`
- Agent-B: `Agent-A said: [Error:]` + `[Error:]`

This indicates the system fails **before** meaningful reasoning or folder analysis can occur.

---

## 2. Pipeline Trace (Phase 2)

| Stage | Status | Evidence |
|-------|--------|----------|
| User Prompt → Frontend submit handler | **PASS** | Puppeteer click on "→" successfully dispatches `sendPrompt` |
| Frontend `sessionStore.ts` `sendPrompt` | **PASS** | Network request emitted to `/api/prompt` |
| REST API request `/api/prompt` | **PASS** | Backend returns HTTP 200 with valid JSON |
| REST endpoint `_handle_prompt` | **PASS** | Reaches Ollama and receives response |
| Agent-A invocation (model load) | **PASS** | `deepseek-coder:1.3b` loads and generates tokens |
| ModelManager / Ollama request | **PASS** | Direct generation test returns response in ~3s |
| Ollama response | **PASS** | Single valid JSON object (`stream: false`) |
| Agent-A output | **PASS** | Non-empty text returned to frontend |
| Unload logic (`keep_alive=0`) | **PASS** | `/api/ps` confirms zero loaded models after generation |
| Agent-B invocation | **PASS** | `qwen2.5-coder:7b` loads, reviews, and unloads |
| Agent-B prompt construction | **PASS** | Truncated Agent-A output injected into review prompt |
| Agent-B output | **PASS** | Non-empty review text returned |
| Frontend rendering | **PASS** | MessageBubble displays both outputs correctly |
| **MCP tool execution** | **FAIL** | See root causes below |
| **Winner execution** | **FAIL** | `file_explorer` error propagates into plan results |

**Conclusion:** The core request/response pipeline (Phases 5–7) is **functional**. The failure occurs specifically when the agents attempt to use **MCP tools** to explore files (Phase 8).

---

## 3. Phase 8 — MCP Execution Evidence

Tested via REST `/api/mcp/invoke` and direct `MCPCell.invoke()`:

| Tool | Status | Exact Error |
|------|--------|-------------|
| `file_explorer` | **FAIL** | `TypeError: cannot unpack non-iterable WindowsPath object` |
| `workspace_indexer` | **FAIL** | `killed` — `execution_timeout` after 60s |
| `search_ripgrep` | **PASS** | Returns matches successfully |

**file_explorer root cause:**
- File: `cells/mcp/presets/file_explorer.py`
- Function: `_resolve(path_str)`
- Line 33: `p, err = _resolve(path_str)`
- **Bug:** On success, `_resolve` returns a single `Path` object (not a tuple). On error, it returns a tuple `(None, dict)`. The unpack syntax `p, err = ...` expects a tuple in both branches. When the path is valid, Python raises `TypeError: cannot unpack non-iterable WindowsPath object`.
- **Impact:** Every `file_explorer` operation (`read`, `list`, `stat`, `write`, etc.) crashes the worker process. The agent **cannot read any file**.

**workspace_indexer root cause:**
- File: `kernel/mcp/runtime/worker_process.py`
- Function: `run_in_worker()` / `_worker_main()`
- **Bug:** On Windows, `multiprocessing.get_context("spawn")` + `Queue.put(large_dict)` causes a **pipe-buffer deadlock**. The child process puts a large result (~180KB for 3656 files) into the queue. The queue's feeder thread blocks writing to the 64KB Windows pipe buffer. The parent process is blocked in `proc.join()` and has not yet called `queue.get()`. The child process never exits; `proc.join(timeout=60)` expires; the parent kills the worker.
- **Impact:** Any preset returning >64KB of data (workspace indexer, large file reads, extensive search results) will **time out** on Windows.

---

## 4. Why Previous Implementation Failed

1. **`file_explorer` regression:** A previous refactoring introduced `_resolve()` as a helper but only returned a tuple in the error branches. The success branch returned a bare `Path`. This was never caught because:
   - No unit test covers the success path of `file_explorer` through the worker process.
   - Previous tests used inline execution (non-worker) where the bug would not surface in the same way, or tested only error paths (workspace violations).

2. **Windows multiprocessing blind spot:** The worker process architecture was designed with Linux/macOS assumptions:
   - `multiprocessing.Queue` is safe for large objects on Unix (fork) but not on Windows (spawn + pipe buffer limits).
   - No test runs the full worker isolation on Windows with large payloads.
   - The `debug_trace.py` script from the previous session also missed this because it timed out and reported `status=killed` without diagnosing the deadlock mechanism.

3. **debug_trace.py false negatives:** The diagnostic script called Ollama directly without `"stream": false`, causing `JSONDecodeError` on NDJSON responses. This created false failures in Phases 5 and 9 that masked the real MCP issues.

---

## 5. Minimal Required Fix

### Fix A: `file_explorer` tuple unpack
**File:** `cells/mcp/presets/file_explorer.py`  
**Change:** Make `_resolve()` always return a tuple `(path, error)`.
```python
def _resolve(path_str: str):
    try:
        return _guard.validate(path_str), None
    except WorkspaceViolation as e:
        return None, {"error": "workspace_violation", "message": str(e)}
    except Exception as e:
        return None, {"error": str(e)}
```

### Fix B: Windows worker deadlock
**File:** `kernel/mcp/runtime/worker_process.py`  
**Change:** Replace `Queue` with a temporary file for result passing. The child writes JSON to a temp file; the parent reads the file after `join()`. This avoids the 64KB Windows pipe buffer limit entirely.

### Fix C: Diagnostic script accuracy
**File:** `debug_trace.py`  
**Change:** Add `"stream": false` to direct Ollama calls so Phases 5 and 9 report real system health, not test-script artifacts.

---

## 6. Side Effects

- **Fix A** is zero-risk: only corrects an obvious type mismatch.
- **Fix B** changes worker IPC from `Queue` to temp file. Risk is low because:
  - The worker is already sandboxed and short-lived.
  - Temp files are cleaned up immediately after reading.
  - No other component depends on `Queue` semantics.
- **Fix C** is test-only; no production impact.

---

## 7. Verified Components That Do NOT Need Changes

| Component | Status | Reason |
|-----------|--------|--------|
| `cells/gateway/rest.py` | OK | `_handle_prompt` correctly sets `stream: false` and handles tool loops. |
| `cells/runtime/model_manager.py` | OK | Load/unload/verify cycle works; `keep_alive=0` unloads correctly. |
| `frontend/src/stores/sessionStore.ts` | OK | Sequential A→B flow, abort handling, and winner execution are correct. |
| `kernel/config.py` | OK | Settings resolve correctly. |
| Ollama connectivity | OK | `/api/tags` and `/api/generate` respond correctly. |

---

## 8. Resolution (Completed)

**Date:** 2026-05-21  
**Status:** All fixes applied and verified.

### Verification Results

| Fix | Location | Verification Method | Result |
|-----|----------|---------------------|--------|
| A — `file_explorer` tuple unpack | `cells/mcp/presets/file_explorer.py` | `debug_trace.py` Phase 8 + `test_phases.py` Phase 8 | ✅ PASS |
| B — Windows worker deadlock | `kernel/mcp/runtime/worker_process.py` | `test_worker.py` + `test_phases.py` Phase 8/10 | ✅ PASS |
| C — Diagnostic script accuracy | `debug_trace.py` | `debug_trace.py` Phases 5 & 9 | ✅ PASS |
| Unit test hygiene | `tests/unit/test_runtime_unit.py` | `pytest tests/` | ✅ 29 passed, 1 skipped |
| Integration test suite | `test_phases.py` | `python test_phases.py` | ✅ Phases 5–10 all PASS |
| Full forensic diagnostic | `debug_trace.py` | `python debug_trace.py` | ✅ Phases 3–9 all PASS |

### Fixes Confirmed in Code

- **`file_explorer.py`** (`_resolve`): Returns `(_guard.validate(path_str), None)` on success.
- **`worker_process.py`**: Uses `tempfile.mkstemp(suffix=".json")` for IPC; child writes JSON, parent reads after `join()`.
- **`debug_trace.py`**: All direct Ollama calls include `"stream": False`.
- **`test_runtime_unit.py`**: Mocked `httpx.AsyncClient` to eliminate hard dependency on real Ollama models during unit tests.

**System is fully operational.**
