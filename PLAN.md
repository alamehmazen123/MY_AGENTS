# PLAN.md — Professionalization roadmap (approved)

Goal: make the dual agents behave like Claude Code — native tools, a real
agentic loop, streaming, verification, and permission gating — while keeping the
local/Ollama, one-model-at-a-time constraints.

Approved scope: **P1, P4, P2, P3, P5**.

## Status
- **P1 Native tool calling** — ✅ DONE (`/api/chat` + tools, hybrid with regex fallback).
- **P2 Bounded agentic loop** — ✅ DONE (reason→tool→observe, model decides done,
  native tools + curated schemas, cap 3 iters).
- **P3 Streaming** — ✅ DONE, and extended to **true token-by-token** streaming
  (Ollama `stream:true` → SSE `token` events → live panels). See `PLAN_PERSISTENCE.md`
  for the full Run/streaming/resume/recovery architecture (Phases A–E, all done).
- **Curated tool schemas + run queue (Phase E)** — ✅ DONE.
- **Planning Mode** (grounded code map + comprehensive + executable plan) — ✅ DONE.
- **P4 Plan + verify** — ⏳ pending (auto-run `python_exec` after a `.py` write).
- **P5 Permission gating (Ask/Auto)** — ⏳ pending.

## Tool-calling support probe (Ollama 0.24.0, this machine)
Tested `/api/chat` with a `tools` param:
- `cogito:8b` ✅ native `tool_calls`
- `qwen3:8b` ✅ native `tool_calls`
- `qwen3:4b` ✅ native `tool_calls` (also emits chatter)
- `qwen2.5-coder:14b` ❌ returns the call as TEXT (no native support)
- `qwen2.5-coder:3b` ❌ returns the call as TEXT

→ **A hybrid is mandatory**: use native `tool_calls` when present, fall back to
the existing `[[MCP:...]]` regex parser when the model returns text.

## Phase 1 — Native tool calling (`/api/chat` + `tools`)
- Convert each preset `SCHEMA` into an OpenAI-style function spec.
- Send `messages` + `tools` to `/api/chat`; execute `message.tool_calls`,
  append `role:"tool"` results, loop.
- Fallback: if no native calls, run `_extract_tool_calls` on `message.content`.
- Keep: workspace-context injection, jail, single unload, think=false, num_predict.
- Removes reliance on forced keyword detection (becomes a last-resort fallback).

## Phase 4 — Plan + verify
- Coding tasks: A emits a short TODO plan, executes, then auto-runs `python_exec`
  to syntax-check/run the written file and reports PASS/FAIL with the output.

## Phase 2 — Bounded agentic loop
- Replace fixed iterations + fast-path with reason→tool→observe until the model
  stops calling tools or hits a turn/token budget (configurable, CPU-safe).

## Phase 3 — Streaming (SSE)
- Stream tokens + tool events to both panels; live "tool fired" indicators.

## Phase 5 — Permission gating (Ask/Auto)
- Per-session mode. In "Ask", delete/overwrite/shell pause for a confirm before
  the worker runs them. "Auto" keeps today's behavior.

## Housekeeping (do alongside)
- Fix stale CLAUDE.md lines: `keep_alive=0`→`"5m"` during loop; `num_predict`
  default is `1024` not 2048.
- Per-model capability cache (native-tools yes/no) to skip the probe each call.
