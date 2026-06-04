# my_agents — Local AI Cognitive Workspace

A self-hosted, 100% local dual-agent AI workspace on top of **Ollama**. Agent-A
reasons and uses tools; Agent-B independently reviews and improves. Runs in your
browser with a ChatGPT-grade UX — token streaming, persisted resumable runs, and
a 39-tool MCP ecosystem.

Stack: **FastAPI + React/Vite + SQLite + Ollama**. Windows-first.

## Key features
- 🔒 **100% local** — no cloud, no API keys, nothing leaves your machine.
- 🧠 **Dual-agent loop** — Agent-A (doer) → Agent-B (independent reviewer) → revise/execute.
- ⚡ **Single-runtime safe** — only one model loaded at a time (server-side run queue).
- 🛠️ **39 MCP tools** — files, search, python, git, web fetch, wikipedia, weather,
  arxiv, sqlite, pdf/office readers, calculator, sympy, screenshot, and more.
- 🔧 **Native tool calling** — capable models (qwen3, cogito) emit structured tool
  calls; others fall back to a tolerant text parser.
- 💬 **True token streaming** — watch the agents type, with live "🔧 tool fired" events.
- 💾 **Persisted, resumable runs** — every turn is a background job saved to SQLite;
  it survives page reload, network blips, and backend restarts (SSE resume by seq).
- 📁 **Workspace-aware** — pick a folder (native picker) and agents read/write inside it.
- 🗺️ **Planning Mode** — "make a plan for this project" returns a *grounded*
  comprehensive plan + an **executable** plan you run with one click on the folder.
- 📎 **Paste anything** — Ctrl+V / right-click images, screenshots, and files into the bar.
- 🧭 **Model capability cards** — tier, native-tool support, and speed for each model.
- 🎨 Markdown rendering with per-code-block copy buttons; pin/rename/sort sessions.

## Run it
```powershell
pip install -r requirements.txt        # backend deps
cd frontend; npm install; npm run build  # build the UI (served from frontend/dist)
```
Then, in separate terminals:
```powershell
ollama serve
python kernel/main.py                   # opens the UI at http://localhost:8000 in Edge
```
Backend only (no Edge popup): `python start_backend.py`

## Tests
```powershell
python -m pytest tests/ -q              # ~78 tests
```

## Notes
- After any `frontend/src` change, rebuild (`npm run build`) and hard-refresh (Ctrl+Shift+R) —
  the backend serves `frontend/dist`, not live source.
- For tool/agent tasks pick a **Strong** model (qwen3:8b / cogito:8b); small models
  are fast but weaker at multi-step tool use (see the capability cards in Settings).
- See `CLAUDE.md` for architecture and contributor rules; `PLAN*.md` for the roadmap.
