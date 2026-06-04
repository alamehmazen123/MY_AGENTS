# CLAUDE.md — Working rules for this project (my_agents PRIS v12)

Read this before responding to any prompt about this codebase. It captures the
architecture, conventions, and the hard-won gotchas so changes stay correct.

## What this project is
A 100% local, dual-agent AI workspace on top of **Ollama**. Two agents run **one
at a time** (never both loaded — VRAM safety): **Agent-A** (Reasoner/doer) plans
and uses tools; **Agent-B** (independent Reviewer) verifies and improves. A
React/Vite SPA is served by a FastAPI backend at `http://localhost:8000`.

Stack: FastAPI + React/Vite + SQLite + Ollama. Windows-first (PowerShell, Edge).

## How to run / verify
- Backend only (no browser/Edge popup): `python start_backend.py`
- Full system (opens Edge): `python kernel/main.py`
- Tests: `python -m pytest tests/ -q` (use the venv python: `.venv/Scripts/python.exe`)
- Frontend build (required after any `frontend/src` change — the backend serves
  `frontend/dist`, NOT live source): `cd frontend && npm run build`
- After editing the UI: rebuild dist, then hard-refresh Edge (Ctrl+Shift+R).
- To test the backend without touching a user's running instance on :8000, start a
  second one on another port: `MY_AGENTS_API_PORT=8010 MY_AGENTS_WS_PORT=8011 python start_backend.py`.

## Golden rules
1. **Always free ports before starting a backend for a test.** A stale instance on
   8000/8001 makes `kernel/main.py` and the e2e test fail. Stop with:
   `Stop-Process -Id (Get-NetTCPConnection -LocalPort 8000 -State Listen).OwningProcess -Force`
2. **Rebuild `frontend/dist` after frontend changes**, or the user sees the old UI.
3. **Run `pytest` after backend/preset changes.** Keep it green (currently ~78 tests).
   The e2e `test_system_lifecycle` fails if anything already holds :8000 — deselect it
   or free the port; that failure is environmental, not a code bug.
4. **One model at a time.** During the tool loop `keep_alive="5m"` keeps the model
   resident; a single unload (`keep_alive=0`) runs once in the `finally` block. A
   server-side `_gen_lock` also serializes runs so no two models ever generate at once.
5. **Clean up temp files** (scratch scripts, `*_test.log`, `pm_*.txt`) when done.

## Architecture map (where things live)
- `kernel/main.py` — lifespan, port pre-check, starts gateway + frontend.
- `kernel/config.py` — pydantic settings (ports, ollama host, workspace root).
- `cells/gateway/rest.py` — **the heart** (~1.7k lines). Endpoints:
  - `/api/run` (POST) → creates a persisted Run, spawns a background worker,
    returns `run_id` INSTANTLY (this is what kills timeouts). `_run_worker` →
    `_run_turn` under the `_gen_lock`.
  - `/api/run/{id}/stream` (SSE) → streams `token`/`tool_started`/`tool_result`/
    `status`/`heartbeat`/`done` events; resumes from `Last-Event-ID` (seq replay).
  - `/api/run/{id}` (GET) → poll the run record.
  - `/api/prompt` → legacy synchronous path; just `await self._run_turn(body)`.
  - `/api/execute-plan`, `/api/mcp/*`, `/api/pick-folder`, `/api/upload-paste`,
    `/api/core-instructions`.
  - `_run_turn` holds: workspace-context injection, **Planning Mode** (`_is_plan_request`
    + `_build_code_map` + `PLANNING_SYSTEM_PROMPT`), native tool calling via Ollama
    `/api/chat` (`_native_tool_calls`) with regex fallback (`_extract_tool_calls`/
    `_parse_args_block`), curated tool schemas (`_curate_tools`), the fast-path
    summary, synthesis mode, and per-token streaming.
- `plasma/run_store.py` — SQLite `runs` + `run_events` (monotonic per-run `seq`);
  powers SSE streaming, resume, and crash recovery (`recover_interrupted()` on startup).
- `cells/mcp/cell.py` — registers all 39 presets; per-call workspace jail;
  `ollama_tools(names=...)` builds function specs from each preset `SCHEMA`.
- `cells/mcp/presets/*.py` — one tool each; export `SCHEMA` + `handle(args) -> dict`.
- `kernel/mcp/runtime/worker_process.py` — runs each preset in a spawned process,
  jailed to the selected workspace via `MY_AGENTS_WORKSPACE_ROOT`.
- `frontend/src/stores/sessionStore.ts` — dual-agent orchestration; `callOllama`
  POSTs `/api/run` and consumes SSE (live tokens via `onToken`); revise loop; execute
  (prefers the `## Executable Plan` section); paste-attach; session persistence.
- `frontend/src/stores/settingsStore.ts` — models, presets, capability tiers
  (`MODEL_NOTES`: tier + native-tools + speed), MCP toggles.
- `core_instructions.md` — SHORT runtime agent rules (be direct, don't ask when
  context is attached, never fabricate, markdown out), **prepended to every agent
  generation** by `_load_core_instructions()`. NOT dev/coding guidance — that's here.

## Hard-won gotchas (do NOT regress these)
- **Tool-call JSON is often invalid.** Models emit `"""triple-quoted"""` content
  and single quotes. `_extract_tool_calls` must parse with `json.loads` first,
  then fall back to `ast.literal_eval`. Never tighten this back to JSON-only.
- **`keep_alive` during the tool loop must be `"5m"`, not `0`.** Unloading every
  iteration reloads the model from disk (36–77s each) and blew the timeout. The
  single unload happens once in the `finally` block.
- **Cap output with `num_predict` (default 1024, override via `max_tokens`)** or
  small models ramble until they fill the context window and time out.
- **Frontend `/api/prompt` abort timeout is aligned to 900s** and the backend
  Ollama request timeout is also 900s to support slow qwen2.5-coder/CPU generations.
- **Disable thinking for reasoning models** (`payload["think"] = False` for
  qwen3 / deepseek-r1 / gpt-oss) — their hidden CoT caused timeouts.
- **Fast-path summary after a successful tool** — don't run another (slow) model
  round to "summarize"; build a deterministic `**Done.** - Wrote ...` summary.
  Big models (14B/8B) take >5 min to summarize on CPU and time out.
- **Workspace jail runs twice** (cell + inside the worker process). The worker
  overwrites `settings.workspace_root` BEFORE importing the preset, because spawn
  re-imports `kernel.config`. Both must point at the user's folder.
- **Bare folder names** ("Desktop") resolve via `_resolve_workspace` (home dir),
  and `_infer_workspace_from_prompt` reads "my desktop"/"downloads" from text.
- **Model source of truth = the session** (`session.agentX.model`), shown in the
  panel header. `switchSession` syncs the Settings dropdowns to it. Do NOT send
  `settings.agentXModel` if it can diverge from the panel — that caused a
  "selected qwen2.5-coder but qwen3:4b was sent" bug.
- **Wikipedia 403s `httpx`** (Cloudflare fingerprint); use stdlib `urllib` there.
- **CNN headlines** come from `lite.cnn.com` (static); the JS homepage has none.
- **Currency** uses `frankfurter.dev` (keyless); exchangerate.host now needs a key.
- **Local text models can't see image pixels.** Pasted images are saved to
  `data/pasted/` and the path is attached; true vision needs a `llava`-class model.
- **Native tool calling is hybrid.** `/api/chat` is sent the tool schemas; qwen3*/
  cogito return structured `tool_calls`, but qwen2.5-coder returns them as TEXT.
  Always keep the regex fallback. Probe results live in `PLAN.md`.
- **Send curated tool schemas, not all 39.** `_curate_tools(prompt)` returns a 7-tool
  core + keyword-triggered extras (cap 16). Sending all 39 schemas was the main
  slowdown that timed out 8B models on CPU. Don't revert to sending everything.
- **Streaming = Ollama `stream:true` → NDJSON.** Each chunk's `message.content`
  delta is emitted as a `token` event; native `tool_calls` arrive in the final chunk.
  Test fakes must provide `client.stream(...)` (an async ctx mgr with `aiter_lines`).
- **Runs are the real flow now.** The frontend uses `/api/run` + SSE, not `/api/prompt`.
  `_run_turn` is shared by both; pass an `emit` callback to stream/persist events.
- **Planning Mode injects a CODE MAP, not a file list, and turns tools OFF** for the
  generation (the executable `[[MCP:...]]` block is emitted as TEXT and run later by
  "Execute Plan"). Format adherence is model-dependent — use a Strong model.

## Dual-agent behavior contract
- **Agent-A** is the doer: tools ON for every preset except CHAT. It must
  investigate attached folders/files instead of asking for clarification.
- **Agent-B** is an INDEPENDENT reviewer: it has tools too, verifies A's claims
  (e.g. confirm a file was really written) before repeating them, detects and
  fixes A's mistakes, and never fabricates data.
- **Revise Again** runs another A→B round seeded with the latest response.
- **Execute Plan** (per panel) prefers the `## Executable Plan` section, runs its
  `[[MCP:...]]` calls; if none, it actively asks that agent to emit tool calls to
  fulfil the ORIGINAL request.

## Planning Mode (grounded, executable plans)
When a folder is attached AND the prompt is a plan/improve/review request
(`_is_plan_request`), `_run_turn` injects a grounded **code map** (`_build_code_map`:
project profile + top real source files + symbols, scratch excluded) and the
`PLANNING_SYSTEM_PROMPT`, which forces two sections: `## Comprehensive Plan` (prose,
grounded) and `## Executable Plan` (a fenced block of `[[MCP:...]]` calls). Tools are
OFF so the plan isn't auto-run; the user clicks Execute Plan to run the executable
section on the folder. Planning gets a larger `num_predict` (2560).

## Output formatting
- Non-CHAT presets get a markdown formatting directive (bullets, `##` headings,
  fenced ```python``` code). The UI renders markdown with per-code-block copy
  buttons. CHAT stays plain conversational text.

## Models & tiers
Tiers live in `settingsStore.ts` `MODEL_NOTES` (Weak / Moderate / Strong / Very
Strong). When the user installs a new Ollama model, add it to `ALL_MODELS` and
`MODEL_NOTES` with the right tier. All 39 MCP tools are available to every model.

## When adding an MCP preset
1. Create `cells/mcp/presets/<name>.py` with `SCHEMA` + `handle(args) -> dict`;
   catch exceptions and return `{"error": ...}` (never raise).
2. Register it in `cells/mcp/cell.py` `_load_presets` with capabilities + limits.
3. Add it to the frontend MCP widget list (`Sidebar.tsx`, sorted by name) and to
   `MCP_PRESETS` in `settingsStore.ts`.
4. Add a case to `tests/mcp/test_all_presets.py` and the registration set.
5. Lazy-import heavy libs inside `handle`. Add new deps to `requirements.txt`.

## Style
Follow `core_instructions.md` (Karpathy): state assumptions, simplest change that
works, surgical edits, verify with tests. Match existing patterns in the file
you're editing.
