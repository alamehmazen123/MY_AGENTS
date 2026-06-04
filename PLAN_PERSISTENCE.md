# PLAN — Institutional-grade persistence & streaming (approved: Full A–E, SSE)

> STATUS: **A–E all implemented & verified.** Plus true token-by-token streaming
> (Ollama `stream:true` → SSE `token` events). See `plasma/run_store.py`,
> `cells/gateway/rest.py` (`_create_run`/`_run_worker`/`_stream_run`/`_run_turn`),
> and `frontend/src/stores/sessionStore.ts` (`callOllama` via `/api/run` + EventSource).

Goal: stop agents from "cutting off" (timeouts) and never lose in-progress work.
Turn every agent turn into a **persisted, streaming, resumable Run**.

> Note: ChatGPT's and Discord's source code are proprietary and were NOT read.
> This design is grounded in their **public** protocol/API documentation, cited below.

## Why it times out today (root cause)
Each agent turn is ONE synchronous HTTP request that blocks until the model
finishes. A local 8B on CPU takes 5–12 min; the frontend (340s) and httpx (600s)
timers fire first → "cut off". The work lives only in that request, so a reload,
network blip, or backend restart loses everything. Confirmed trigger last session:
all 39 tool schemas + a 6k-char system prompt made cogito:8b exceed the timeout.

## Reference mechanisms (public docs)

### 1. OpenAI Assistants — async **Run** lifecycle
Source: https://developers.openai.com/api/docs/assistants/deep-dive
- Runs execute **asynchronously**; you monitor via **polling OR streaming**.
- Statuses: `queued → in_progress → (requires_action) → completed | failed |
  expired | cancelled | incomplete`.
- **"While a Run is in_progress the Thread is locked"** — new runs can't start.
  → maps exactly onto our *one-model-at-a-time* rule.
- Run **steps** record `message_creation` and `tool_calls`.

### 2. Discord Gateway — heartbeat + **resume by sequence**
Source: https://docs.discord.com/developers/topics/gateway
- **Heartbeat**: client sends `{op:1, d:<last seq>}`; server ACKs (`op:11`).
  No ACK ⇒ connection is "zombied" ⇒ reconnect.
- **Resume**: client caches `session_id` + `s` (sequence). On reconnect it sends
  Resume(`op:6`, seq); the server **replays missed events in order from that seq**,
  then sends `Resumed`. Sessions survive a few minutes after a non-clean close.
- Lesson: every event carries a monotonic **seq**; resume = replay-from-seq.

### 3. SSE — native resumable streaming (the transport we'll use)
Source: https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events
- Server sends `text/event-stream`; each event may set `id:`, `event:`, `data:`,
  `retry:`.
- **`id:`** is remembered by the browser and re-sent as the **`Last-Event-ID`**
  header on auto-reconnect → server resumes from there. This is SSE's built-in
  equivalent of Discord's seq-resume — we get it almost for free.
- ⚠️ Without HTTP/2, browsers allow only **6 concurrent SSE connections/domain**
  (fine here: ≤2 panels). Close streams when a run reaches a terminal state.

## The design (A–E)

### A. Run persistence (SQLite) — *from OpenAI Runs*
- `runs(run_id, session_id, agent, model, status, prompt, partial_output, error,
  created_at, updated_at)`; status ∈ queued/running/requires_action/completed/
  failed/cancelled/interrupted.
- `run_events(run_id, seq, type, data, ts)` — monotonic `seq` per run; `type` ∈
  token / tool_started / tool_result / status / heartbeat / done / error.
  This single log powers BOTH streaming and resume.
- `POST /api/prompt` → insert run (queued) → spawn background worker →
  **return `{run_id}` immediately** (no blocking ⇒ no timeout). Enforce one
  active run at a time (Thread-lock rule).
- Worker = the existing A/B agent loop, but it **persists** each token/tool event
  and updates `runs.status` as it goes.

### B. Streaming (SSE) — *from MDN*
- `GET /api/runs/{run_id}/stream` returns `text/event-stream`, emitting each
  `run_event` as `id: <seq>\nevent: <type>\ndata: <json>\n\n`.
- Use Ollama `stream:true` so tokens flow as generated.
- Frontend `EventSource` appends tokens to the live agent bubble; shows
  "🔧 tool fired" on tool events.

### C. Resume by seq — *Discord replay + SSE Last-Event-ID*
- On (re)connect the browser sends `Last-Event-ID`; the endpoint replays
  `run_events` with `seq > last_id` from SQLite, then continues live.
- Emit an `event: heartbeat` every ~15s (keep-alive + zombie detection).

### D. Crash recovery — *Runs terminal-state discipline*
- On startup, any run still `running` → mark `interrupted` (partial_output is
  already saved). UI shows it with a Resume/Retry action.

### E. Stability (removes the timeout trigger)
- **Curated tool schemas**: send a relevant subset, not all 39 → the fix for the
  cogito slowdown.
- Bounded agent loop (turn + token budget). Run **queue** (one model at a time).
- Structured, idempotent tool errors; heartbeats so "slow" never reads as "dead".

## Build order
A (schema + enqueue + worker) → B (SSE + Ollama token stream) → C (resume +
heartbeat) → D (startup recovery) → E (curated schemas + budgets). Each phase is
shippable and independently tested. Keeps P1 (native tools, done) and is
compatible with P2/P4/P5.

## Tests to add
- Run created/queued/transitions; events persisted with increasing seq.
- SSE replay from a given Last-Event-ID returns only newer events.
- Startup marks orphaned `running` runs as `interrupted`.
- Curated-schema selection returns a bounded set.
