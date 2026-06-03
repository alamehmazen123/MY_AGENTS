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

## Golden rules
1. **Always free ports before starting a backend for a test.** A stale instance on
   8000/8001 makes `kernel/main.py` and the e2e test fail. Stop with:
   `Stop-Process -Id (Get-NetTCPConnection -LocalPort 8000 -State Listen).OwningProcess -Force`
2. **Rebuild `frontend/dist` after frontend changes**, or the user sees the old UI.
3. **Run `pytest` after backend/preset changes.** Keep it green (currently ~45 tests).
4. **One model at a time.** During the tool loop `keep_alive="5m"` keeps the model
   resident; a single unload (`keep_alive=0`) runs once in the `finally` block so the
   next agent starts with zero models loaded. Don't break this.
5. **Clean up temp files** (scratch scripts, `backend_test.log`) when done.

## Architecture map (where things live)
- `kernel/main.py` — lifespan, port pre-check, starts gateway + frontend.
- `kernel/config.py` — pydantic settings (ports, ollama host, workspace root).
- `cells/gateway/rest.py` — **the heart**: `/api/prompt` (the A/B tool loop),
  `/api/execute-plan`, `/api/mcp/*`, `/api/pick-folder`, `/api/upload-paste`,
  `/api/core-instructions`. Tool-call parsing, workspace-context injection,
  forced-tool detection, synthesis-mode summary all live here.
- `cells/mcp/cell.py` — registers all MCP presets; per-call workspace jail.
- `cells/mcp/presets/*.py` — one tool each; export `SCHEMA` + `handle(args) -> dict`.
- `kernel/mcp/runtime/worker_process.py` — runs each preset in a spawned process,
  jailed to the selected workspace via `MY_AGENTS_WORKSPACE_ROOT`.
- `frontend/src/stores/sessionStore.ts` — dual-agent orchestration, persistence,
  revise loop, execute, paste-attach.
- `frontend/src/stores/settingsStore.ts` — models, presets, tiers, MCP toggles.
- `core_instructions.md` — Karpathy behavioral guidelines, **prepended to every
  agent generation** (all presets) by `_load_core_instructions()`.

## Hard-won gotchas (do NOT regress these)
- **Tool-call JSON is often invalid.** Models emit `"""triple-quoted"""` content
  and single quotes. `_extract_tool_calls` must parse with `json.loads` first,
  then fall back to `ast.literal_eval`. Never tighten this back to JSON-only.
- **`keep_alive` during the tool loop must be `"5m"`, not `0`.** Unloading every
  iteration reloads the model from disk (36–77s each) and blew the timeout. The
  single unload happens once in the `finally` block.
- **Cap output with `num_predict` (default 1024, override via `max_tokens`)** or
  small models ramble until they fill the context window and time out.
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

## Dual-agent behavior contract
- **Agent-A** is the doer: tools ON for every preset except CHAT. It must
  investigate attached folders/files instead of asking for clarification.
- **Agent-B** is an INDEPENDENT reviewer: it has tools too, verifies A's claims
  (e.g. confirm a file was really written) before repeating them, detects and
  fixes A's mistakes, and never fabricates data.
- **Revise Again** runs another A→B round seeded with the latest response.
- **Execute Plan** (per panel) runs any `[[MCP:...]]` calls in the text; if none,
  it actively asks that agent to emit tool calls to fulfil the ORIGINAL request.

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
