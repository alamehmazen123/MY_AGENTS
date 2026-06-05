import { create } from 'zustand'
import { useSettingsStore, pickModel } from './settingsStore'

export interface AgentMessage {
  id: string
  role: 'user' | 'agent' | 'system' | 'context'
  text: string
  timestamp: number
  streaming?: boolean
  traceId?: string
}

export interface AgentState {
  messages: AgentMessage[]
  status: 'idle' | 'online' | 'working' | 'waiting' | 'paused' | 'disabled'
  model: string
  // When model is 🪄 Auto, the concrete model the router picked for the last turn.
  resolvedModel?: string
}

export interface AttachedFile {
  name: string
  content: string
}

export interface ExecutionStep {
  tool: string
  args: any
  result: any
  ok: boolean
  preview: string
}

export interface ExecutionResult {
  agent: 'A' | 'B'
  steps: ExecutionStep[]
  summary: string
}

export interface Session {
  id: string
  name: string
  createdAt: number
  pinned?: boolean
  agentA: AgentState
  agentB: AgentState
  attachedFiles: AttachedFile[]
  workspaceFolder: string
  winner: 'A' | 'B' | null
  executionResult: ExecutionResult | null
}

export interface SessionState {
  sessions: Session[]
  activeSessionId: string
  isGenerating: boolean
  unloadStatus: string
  sendPrompt: (text: string, opts?: { files?: AttachedFile[]; folder?: string }) => void
  abortGeneration: () => void
  selectWinner: (agent: 'A' | 'B') => void
  executeAgent: (agent: 'A' | 'B') => Promise<void>
  reviseAgain: () => Promise<void>
  executeWinner: () => Promise<void>
  createSession: () => void
  switchSession: (id: string) => void
  deleteSession: (id: string) => void
  renameSession: (id: string, name: string) => void
  togglePin: (id: string) => void
  clear: () => void
  updateSessionModels: () => void
}

let msgId = 0
function makeId() {
  return `msg-${++msgId}-${Date.now()}`
}

let currentAbortController: AbortController | null = null

async function callOllama(
  prompt: string,
  model: string,
  system?: string,
  opts?: {
    workspaceFolder?: string
    attachedFiles?: AttachedFile[]
    enableTools?: boolean
    temperature?: number
    contextLength?: number
    signal?: AbortSignal
    agent?: 'A' | 'B'
    onToken?: (delta: string) => void
  }
): Promise<{ text: string; toolContext: string; toolResults: any[]; traceId?: string }> {
  const controller = new AbortController()
  const timeoutMs = 900_000 // 15m: match backend Ollama request timeout for long model generations
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs)

  if (opts?.signal) {
    const onAbort = () => {
      clearTimeout(timeoutId)
      controller.abort()
    }
    opts.signal.addEventListener('abort', onAbort, { once: true })
  }

  try {
    const body: any = { prompt, model, system }
    if (opts?.workspaceFolder) body.workspace_folder = opts.workspaceFolder
    if (opts?.attachedFiles) body.attached_files = opts.attachedFiles.map((f) => f.name)
    if (opts?.enableTools === false) body.no_tools = true
    if (opts?.temperature !== undefined) body.temperature = opts.temperature
    if (opts?.contextLength) body.context_length = opts.contextLength

    const settings = useSettingsStore.getState()
    body.preset = settings.preset
    body.permission_mode = settings.permissionMode

    // Force structured markdown output for every preset EXCEPT plain CHAT — so
    // answers come back as bullet points, headings, and fenced code blocks
    // (which the UI then renders as a real Python/code box with a copy button).
    if (settings.preset !== 'CHAT' && body.system) {
      body.system =
        body.system +
        '\n\nFORMATTING: Respond in markdown. Use short bullet points for any list. ' +
        'Use ## headings for distinct sections when useful. Put ALL code inside fenced ' +
        'code blocks with a language tag (e.g. ```python ... ```) — never paste raw code ' +
        'into prose. Be structured; do not write a wall of plain text.'
    }

    // Pass session/agent context so the backend persists the run correctly.
    body.session_id = useSessionStore.getState().activeSessionId
    body.agent = opts?.agent || 'A'

    console.log(
      '[SESSION_STORE_TRACE] starting run',
      JSON.stringify({ preset: body.preset, model: body.model, agent: body.agent, prompt_preview: body.prompt?.slice(0, 80) })
    )

    // ── Async Run + SSE (Phase A/B/C) ──
    // The backend enqueues the turn and returns a run_id INSTANTLY, so the HTTP
    // request can never time out. We then stream the run's events over SSE; the
    // work is persisted server-side and survives reload/restart. EventSource
    // auto-reconnects with Last-Event-ID, giving free resume.
    const startRes = await fetch('/api/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal: controller.signal,
    })
    clearTimeout(timeoutId)
    if (!startRes.ok) throw new Error((await startRes.text()) || `HTTP ${startRes.status}`)
    const { run_id } = await startRes.json()
    if (!run_id) throw new Error('no run_id returned')

    return await new Promise((resolve) => {
      const es = new EventSource(`/api/run/${run_id}/stream`)
      let settled = false
      const finish = (val: any) => {
        if (settled) return
        settled = true
        es.close()
        resolve(val)
      }

      const onAbort = () => finish({ text: '[Stopped by user]', toolContext: '', toolResults: [] })
      opts?.signal?.addEventListener('abort', onAbort, { once: true })

      es.addEventListener('token', (e: any) => {
        try {
          const d = JSON.parse(e.data)
          if (d.t && opts?.onToken) opts.onToken(d.t)
        } catch { /* ignore */ }
      })
      es.addEventListener('tool_started', (e: any) => {
        try {
          const d = JSON.parse(e.data)
          useSessionStore.setState({ unloadStatus: `🔧 ${d.tool}…` })
        } catch { /* ignore */ }
      })
      es.addEventListener('done', (e: any) => {
        try {
          const d = JSON.parse(e.data)
          if (d.error) {
            finish({ text: `[Error: ${d.error}] ${d.output || ''}`, toolContext: '', toolResults: [] })
          } else {
            finish({
              text: d.output || '[No response from model]',
              toolContext: d.tool_context || '',
              toolResults: d.tool_results || [],
            })
          }
        } catch {
          finish({ text: '[Error: malformed run result]', toolContext: '', toolResults: [] })
        }
      })
      es.addEventListener('error', (e: any) => {
        // A typed `error` event carries data; a transport error does not (EventSource
        // will auto-reconnect with Last-Event-ID, so don't kill the stream for those).
        if (e?.data) {
          try { finish({ text: `[Error: ${JSON.parse(e.data).error}]`, toolContext: '', toolResults: [] }) }
          catch { finish({ text: '[Error during run]', toolContext: '', toolResults: [] }) }
        }
      })
      es.addEventListener('close', () => {
        // Terminal status with no done payload (rare) — fall back to the run record.
        if (!settled) {
          fetch(`/api/run/${run_id}`).then((r) => r.json()).then((run) => {
            finish({ text: run?.partial_output || '[Run ended]', toolContext: '', toolResults: [] })
          }).catch(() => finish({ text: '[Run ended]', toolContext: '', toolResults: [] }))
        }
      })
    })
  } catch (e: any) {
    clearTimeout(timeoutId)
    if (e.name === 'AbortError' && opts?.signal?.aborted) {
      return { text: '[Stopped by user]', toolContext: '', toolResults: [] }
    }
    return { text: `[Error: ${e.message}]`, toolContext: '', toolResults: [] }
  }
}

// Append an empty streaming agent message to a panel and return its id, so
// tokens can be rendered live as they arrive over SSE.
function pushStreamingMessage(agent: 'A' | 'B'): string {
  const id = makeId()
  const key = agent === 'A' ? 'agentA' : 'agentB'
  useSessionStore.setState((s) => ({
    sessions: s.sessions.map((sess) =>
      sess.id === s.activeSessionId
        ? { ...sess, [key]: { ...sess[key], messages: [...sess[key].messages, { id, role: 'agent', text: '', streaming: true, timestamp: Date.now() }] } }
        : sess
    ),
  }))
  return id
}

function updateStreamingMessage(agent: 'A' | 'B', id: string, text: string, streaming: boolean) {
  const key = agent === 'A' ? 'agentA' : 'agentB'
  useSessionStore.setState((s) => ({
    sessions: s.sessions.map((sess) =>
      sess.id === s.activeSessionId
        ? { ...sess, [key]: { ...sess[key], messages: sess[key].messages.map((m) => (m.id === id ? { ...m, text, streaming } : m)) } }
        : sess
    ),
  }))
}

async function verifyZeroModels(): Promise<{ ok: boolean; status: string }> {
  try {
    const res = await fetch('/api/ollama-ps', { method: 'GET' })
    if (!res.ok) return { ok: false, status: 'check_failed' }
    const data = await res.json()
    if (data.zero_loaded) {
      return { ok: true, status: '✅ Zero models loaded' }
    }
    return { ok: false, status: `⚠️ ${data.models.length} model(s) still loaded: ${data.models.join(', ')}` }
  } catch {
    return { ok: false, status: '⚠️ Could not verify unload' }
  }
}

function truncate(str: string, maxLen: number): string {
  if (str.length <= maxLen) return str
  return str.slice(0, maxLen) + '\n\n[...truncated]'
}

function buildPrompt(text: string, files: AttachedFile[], folder: string): string {
  const parts: string[] = []

  if (folder) {
    parts.push(`Workspace: ${folder}\n`)
  }

  if (files.length > 0) {
    parts.push('--- Attached Files ---')
    for (const f of files) {
      parts.push(`\n[File: ${f.name}]`)
      if (f.content.startsWith('[Error:') || f.content.startsWith('[Binary')) {
        parts.push(f.content)
      } else {
        parts.push('```')
        parts.push(truncate(f.content, 8000))
        parts.push('```')
      }
    }
    parts.push('--- End Files ---\n')
  }

  parts.push(text)
  return parts.join('\n')
}

function makeSession(id: string, name: string): Session {
  const settings = useSettingsStore.getState()
  return {
    id,
    name,
    createdAt: Date.now(),
    agentA: {
      messages: [],
      status: 'online',
      model: settings.agentAModel,
    },
    agentB: {
      messages: [],
      status: settings.agentBModel ? 'waiting' : 'disabled',
      model: settings.agentBModel || '',
    },
    attachedFiles: [],
    workspaceFolder: '',
    winner: null,
    executionResult: null,
  }
}

const SESSIONS_KEY = 'my_agents_sessions_v1'

function persistSessions(sessions: Session[], activeSessionId: string) {
  try {
    localStorage.setItem(SESSIONS_KEY, JSON.stringify({ sessions, activeSessionId }))
  } catch {
    // Storage full or unavailable — non-fatal.
  }
}

function loadSessions(): { sessions: Session[]; activeSessionId: string } | null {
  try {
    const raw = localStorage.getItem(SESSIONS_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw)
    if (!parsed?.sessions?.length) return null
    // Restore sessions but reset any transient "in-flight" runtime state.
    const sessions: Session[] = parsed.sessions.map((s: any) => ({
      ...s,
      executionResult: null,  // transient; format may have changed
      agentA: {
        ...s.agentA,
        status: 'online',
        messages: (s.agentA?.messages || []).map((m: any) => ({ ...m, streaming: false })),
      },
      agentB: {
        ...s.agentB,
        status: s.agentB?.model ? 'waiting' : 'disabled',
        messages: (s.agentB?.messages || []).map((m: any) => ({ ...m, streaming: false })),
      },
    }))
    const activeSessionId =
      parsed.activeSessionId && sessions.some((x) => x.id === parsed.activeSessionId)
        ? parsed.activeSessionId
        : sessions[0].id
    return { sessions, activeSessionId }
  } catch {
    return null
  }
}

export const useSessionStore = create<SessionState>((set, get) => {
  const restored = typeof window !== 'undefined' ? loadSessions() : null
  const initialSessions = restored ? restored.sessions : [makeSession('sess-1', 'Session 1')]
  const initialActive = restored ? restored.activeSessionId : initialSessions[0].id
  return {
    sessions: initialSessions,
    activeSessionId: initialActive,
    isGenerating: false,
    unloadStatus: '',

    createSession: () => {
      const id = `sess-${Date.now()}`
      const name = `Session ${get().sessions.length + 1}`
      const session = makeSession(id, name)
      set((s) => ({ sessions: [...s.sessions, session], activeSessionId: id }))
    },

    switchSession: (id: string) => {
      set({ activeSessionId: id })
      // Sync the Settings model dropdowns to this session so what the panel
      // shows == what the dropdown shows == what actually gets sent. Without
      // this, the global settings model can diverge from the session's model
      // (the panel header), causing the backend to receive a different model
      // than the user believes they selected.
      const sess = get().sessions.find((s) => s.id === id)
      if (sess) {
        const patch: any = {}
        if (sess.agentA.model) patch.agentAModel = sess.agentA.model
        patch.agentBModel = sess.agentB.model || ''
        useSettingsStore.setState(patch)
      }
    },

    renameSession: (id: string, name: string) => {
      const trimmed = name.trim()
      if (!trimmed) return
      set((s) => ({
        sessions: s.sessions.map((x) => (x.id === id ? { ...x, name: trimmed } : x)),
      }))
    },

    togglePin: (id: string) => {
      set((s) => ({
        sessions: s.sessions.map((x) => (x.id === id ? { ...x, pinned: !x.pinned } : x)),
      }))
    },

    deleteSession: (id: string) => {
      set((s) => {
        const filtered = s.sessions.filter((x) => x.id !== id)
        if (filtered.length === 0) {
          const fresh = makeSession('sess-fresh', 'Session 1')
          return { sessions: [fresh], activeSessionId: fresh.id }
        }
        const newActive = filtered[0].id
        return { sessions: filtered, activeSessionId: newActive }
      })
    },

    updateSessionModels: () => {
      const settings = useSettingsStore.getState()
      set((s) => ({
        sessions: s.sessions.map((sess) =>
          sess.id === s.activeSessionId
            ? {
                ...sess,
                agentA: { ...sess.agentA, model: settings.agentAModel },
                agentB: {
                  ...sess.agentB,
                  model: settings.agentBModel || '',
                  status: settings.agentBModel ? sess.agentB.status : 'disabled',
                },
              }
            : sess
        ),
      }))
    },

    selectWinner: (agent: 'A' | 'B') => {
      set((s) => ({
        sessions: s.sessions.map((sess) =>
          sess.id === s.activeSessionId ? { ...sess, winner: agent, executionResult: null } : sess
        ),
      }))
    },

    executeAgent: async (agent: 'A' | 'B') => {
      const state = get()
      const session = state.sessions.find((s) => s.id === state.activeSessionId)
      if (!session) return
      const settings = useSettingsStore.getState()

      const target = agent === 'A' ? session.agentA : session.agentB
      const other = agent === 'A' ? session.agentB : session.agentA
      const targetMsg = target.messages.filter((m) => m.role === 'agent').pop()
      const otherMsg = other.messages.filter((m) => m.role === 'agent').pop()
      const userMsg = session.agentA.messages.filter((m) => m.role === 'user').pop()
      const originalRequest = userMsg?.text || ''
      if (!targetMsg && !otherMsg) return

      const toSteps = (raw: any[]): ExecutionStep[] =>
        (raw || []).map((r: any) => {
          const res = r.result ?? r
          const err = res?.error || res?.status === 'error'
          return {
            tool: r.tool,
            args: r.args,
            result: res,
            ok: !err,
            preview: typeof res === 'string' ? res.slice(0, 300) : JSON.stringify(res).slice(0, 300),
          }
        })
      const buildSummary = (steps: ExecutionStep[], status: string, errMsg?: string): string => {
        const okCount = steps.filter((s) => s.ok).length
        const failed = steps.length - okCount
        if (steps.length > 0) {
          return `✅ ${okCount} tool call${okCount === 1 ? '' : 's'} executed successfully${failed ? `, ${failed} failed` : ''}.`
        }
        return status === 'no_tools_found'
          ? `⚠️ No executable tool calls found — nothing to run.`
          : `⚠️ ${status}${errMsg ? ': ' + errMsg : ''}`
      }

      const setResult = (result: ExecutionResult) =>
        set((s) => ({
          isGenerating: false,
          unloadStatus: '',
          sessions: s.sessions.map((sess) =>
            sess.id === s.activeSessionId ? { ...sess, executionResult: result } : sess
          ),
        }))

      set({ isGenerating: true, unloadStatus: `Executing Agent-${agent} plan...` })

      // In Planning Mode the agent emits an "## Executable Plan" section holding
      // the tool calls — prefer that so we run exactly those (not example calls
      // that may appear in the prose), still scoped to the attached folder.
      const executableSection = (t?: string) => {
        if (!t) return undefined
        const i = t.search(/##\s*Executable Plan/i)
        return i >= 0 ? t.slice(i) : undefined
      }

      try {
        // ── PASS 1: passive extraction from the existing texts. ──
        const plan =
          [executableSection(targetMsg?.text), executableSection(otherMsg?.text)].filter(Boolean).join('\n\n') ||
          [targetMsg?.text, otherMsg?.text].filter(Boolean).join('\n\n')
        const res = await fetch('/api/execute-plan', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ plan, workspace_folder: session.workspaceFolder }),
        })
        const data = await res.json()
        let steps = toSteps(data.results || [])

        // ── PASS 2: if nothing to run, ASK the agent to actually do the work. ──
        if (steps.length === 0) {
          set({ unloadStatus: `Asking Agent-${agent} to generate an executable plan...` })
          const rawExec = agent === 'A'
            ? session.agentA.model || settings.agentAModel
            : session.agentB.model || settings.agentBModel
          // Execution is always a tool task → resolve Auto with hasFolder=true.
          const model = pickModel(rawExec, originalRequest || 'run tools', agent, settings.availableModels, true)
          const seedAnswer = targetMsg?.text || otherMsg?.text || ''
          const execPrompt =
            `ORIGINAL USER REQUEST:\n"""${originalRequest}"""\n\n` +
            `LATEST AGENT ANSWER (for context):\n"""${truncate(seedAnswer, 2000)}"""\n\n` +
            `Now ACTUALLY perform the user's request using MCP tools. Emit one or more ` +
            `\`[[MCP:tool:{json}]]\` calls so the work really happens (e.g. file_explorer ` +
            `write to create a file at the requested path; use absolute paths). ` +
            `Workspace folder: ${session.workspaceFolder || '(project root)'}. ` +
            `Do NOT just narrate — the tool calls will be executed.`
          const execSystem =
            'You are an execution agent. Carry out the user task by emitting [[MCP:...]] ' +
            'tool calls that actually run. Output ONLY tool calls and minimal narration.'
          const r = await callOllama(execPrompt, model, execSystem, {
            workspaceFolder: session.workspaceFolder,
            enableTools: true,
            temperature: 0.1,
            contextLength: settings.contextLength,
          })
          // Backend already executed any tool calls during this /api/prompt round.
          steps = toSteps(
            r.toolResults.map((tr: any) => ({ tool: tr.tool, args: tr.args, result: tr.result }))
          )
          // Append the agent's response to its panel so the user sees what it did.
          set((s) => ({
            sessions: s.sessions.map((sess) =>
              sess.id === s.activeSessionId
                ? {
                    ...sess,
                    [agent === 'A' ? 'agentA' : 'agentB']: {
                      ...(agent === 'A' ? sess.agentA : sess.agentB),
                      messages: [
                        ...(agent === 'A' ? sess.agentA : sess.agentB).messages,
                        { id: makeId(), role: 'agent', text: r.text, timestamp: Date.now(), traceId: r.traceId },
                      ],
                    },
                  }
                : sess
            ),
          }))
        }

        // ── PASS 3 (gather → implement) ──
        // If PASS 1 only READ files (a plan's gather phase), feed the real file
        // contents back and ask the agent to produce + APPLY the edits. Safety is
        // enforced by the backend: Ask mode blocks writes; syntactically-broken or
        // truncated Python is refused pre-write; every .py is compile-checked (P4).
        const isGather = steps.length > 0 && steps.every((s) =>
          s.tool === 'search_ripgrep' ||
          (s.tool === 'file_explorer' && ['read', 'list', 'stat'].includes(s.args?.action))
        )
        const gathered = steps
          .filter((s) => s.tool === 'file_explorer' && s.args?.action === 'read' && s.result?.content)
          .map((s) => `=== ${s.args.path} ===\n${String(s.result.content).slice(0, 4000)}`)
          .join('\n\n')

        if (isGather && gathered) {
          set({ unloadStatus: 'Implementing plan — generating & applying edits…' })
          const rawExec = agent === 'A' ? session.agentA.model || settings.agentAModel : session.agentB.model || settings.agentBModel
          const model = pickModel(rawExec, originalRequest || 'implement plan', agent, settings.availableModels, true)
          const implPrompt =
            `ORIGINAL REQUEST:\n"""${originalRequest}"""\n\n` +
            `You already READ these files:\n${truncate(gathered, 9000)}\n\n` +
            `Now IMPLEMENT the improvements. For EACH file you change, emit a tool call with the FULL corrected file content:\n` +
            `[[MCP:file_explorer:{"action":"write","path":"<relative path>","content":"<complete new file content>"}]]\n` +
            `RULES: change only what the plan requires; reproduce each file COMPLETELY (no truncation, no "...rest unchanged" placeholders); ` +
            `if you cannot safely reproduce a whole large file, make a small targeted change or skip it. Paths are relative to the workspace.`
          const implSystem =
            'You are an execution agent applying concrete code edits via [[MCP:file_explorer:write]] calls with COMPLETE file content. ' +
            'Never truncate a file or use placeholders. Broken or truncated Python will be refused by the system.'
          const r = await callOllama(implPrompt, model, implSystem, {
            workspaceFolder: session.workspaceFolder,
            enableTools: true,
            temperature: 0.1,
            contextLength: settings.contextLength,
            agent,
          })
          const implSteps = toSteps((r.toolResults || []).map((tr: any) => ({ tool: tr.tool, args: tr.args, result: tr.result })))
          steps = steps.concat(implSteps)
          set((s) => ({
            sessions: s.sessions.map((sess) =>
              sess.id === s.activeSessionId
                ? { ...sess, [agent === 'A' ? 'agentA' : 'agentB']: { ...(agent === 'A' ? sess.agentA : sess.agentB), messages: [...(agent === 'A' ? sess.agentA : sess.agentB).messages, { id: makeId(), role: 'agent', text: '**Implementing plan**\n\n' + r.text, timestamp: Date.now() }] } }
                : sess
            ),
          }))
        }

        setResult({ agent, steps, summary: buildSummary(steps, data.status, data.error) })
      } catch (e: any) {
        setResult({ agent, steps: [], summary: `⚠️ Execution failed: ${e.message}` })
      }
    },

    executeWinner: async () => {
      const session = get().sessions.find((s) => s.id === get().activeSessionId)
      if (!session || !session.winner) return
      await get().executeAgent(session.winner)
    },

    reviseAgain: async () => {
      const state = get()
      const session = state.sessions.find((s) => s.id === state.activeSessionId)
      if (!session) return
      const settings = useSettingsStore.getState()
      const rawA = session.agentA.model || settings.agentAModel
      const rawB = session.agentB.model || settings.agentBModel
      const isBEnabled = !!rawB && settings.preset !== 'CHAT'

      // Use the most recent agent response as the seed for the revision. If
      // Agent-B has spoken, use B; otherwise the most recent A message.
      const lastB = session.agentB.messages.filter((m) => m.role === 'agent').pop()
      const lastA = session.agentA.messages.filter((m) => m.role === 'agent').pop()
      const seed = (lastB?.text || lastA?.text || '').trim()
      if (!seed) return

      // Resolve 🪄 Auto. Revision is a reasoning/tool task → hasFolder true.
      const lastUser = session.agentA.messages.filter((m) => m.role === 'user').pop()?.text || seed
      const agentAModel = pickModel(rawA, lastUser, 'A', settings.availableModels, true)
      const agentBModel = pickModel(rawB, lastUser, 'B', settings.availableModels, true, agentAModel)

      const abortCtrl = new AbortController()
      currentAbortController = abortCtrl
      const isAborted = () => abortCtrl.signal.aborted

      set((s) => ({
        isGenerating: true,
        unloadStatus: 'Revising — Agent-A...',
        sessions: s.sessions.map((sess) =>
          sess.id === s.activeSessionId
            ? {
                ...sess,
                winner: null,
                executionResult: null,
                agentA: { ...sess.agentA, status: 'working' },
                agentB: { ...sess.agentB, status: isBEnabled ? 'waiting' : sess.agentB.status },
              }
            : sess
        ),
      }))

      try {
        // ── Phase 1: Agent-A revises whatever came last ──
        const revisePromptA =
          `A previous answer is shown below. Build a BETTER answer/plan by improving on it.\n` +
          `If the request needs tools, emit [[MCP:tool:{json}]] calls. Never invent data.\n\n` +
          `=== PREVIOUS ANSWER ===\n${truncate(seed, 4000)}\n=== END ===\n\n` +
          `Now produce your improved version.`
        const aResult = await callOllama(revisePromptA, agentAModel, settings.systemPromptA, {
          workspaceFolder: session.workspaceFolder,
          enableTools: settings.preset !== 'CHAT',
          temperature: settings.temperatureA,
          contextLength: settings.contextLength,
          signal: abortCtrl.signal,
        })
        if (isAborted() || aResult.text === '[Stopped by user]') {
          set({ isGenerating: false, unloadStatus: '' })
          return
        }
        const newA = aResult.text
        const toolCtxA = aResult.toolContext

        set((s) => ({
          sessions: s.sessions.map((sess) =>
            sess.id === s.activeSessionId
              ? {
                  ...sess,
                  agentA: {
                    ...sess.agentA,
                    status: 'online',
                    messages: [
                      ...sess.agentA.messages,
                      { id: makeId(), role: 'agent', text: newA, timestamp: Date.now(), traceId: aResult.traceId },
                    ],
                  },
                  agentB: { ...sess.agentB, status: isBEnabled ? 'working' : sess.agentB.status },
                }
              : sess
          ),
          unloadStatus: 'Revising — Agent-B...',
        }))

        if (!isBEnabled) {
          set({ isGenerating: false, unloadStatus: '' })
          return
        }

        // ── Phase 2: Agent-B reviews A's NEW answer INDEPENDENTLY ──
        const groundTruth = toolCtxA
          ? `\nAgent-A's tool results (real data):\n${truncate(toolCtxA, 3000)}\n`
          : ''
        const reviewPromptB =
          `Agent-A produced this revised answer:\n"""${truncate(newA, 4000)}"""\n${groundTruth}\n` +
          `As an INDEPENDENT reviewer, produce an even better final answer. Verify Agent-A's claims ` +
          `with tools before repeating them (e.g. confirm a file was really written). If Agent-A asked ` +
          `for clarification while a folder/files are available, investigate yourself instead. Detect ` +
          `and fix mistakes. NEVER invent data. Be concise and structured.`
        const reviewSystem =
          'You are an independent senior reviewer. You verify claims with tools, fix mistakes, and ' +
          'investigate the workspace yourself rather than asking for clarification. You never fabricate data.'
        const bResult = await callOllama(reviewPromptB, agentBModel, reviewSystem, {
          workspaceFolder: session.workspaceFolder,
          enableTools: settings.preset !== 'CHAT',
          temperature: settings.temperatureB,
          contextLength: settings.contextLength,
          signal: abortCtrl.signal,
          agent: 'B',
        })

        if (isAborted() || bResult.text === '[Stopped by user]') {
          set({ isGenerating: false, unloadStatus: '' })
          return
        }

        set((s) => ({
          isGenerating: false,
          unloadStatus: '',
          sessions: s.sessions.map((sess) =>
            sess.id === s.activeSessionId
              ? {
                  ...sess,
                  agentB: {
                    ...sess.agentB,
                    status: 'online',
                    messages: [
                      ...sess.agentB.messages,
                      { id: makeId(), role: 'agent', text: bResult.text, timestamp: Date.now(), traceId: bResult.traceId },
                    ],
                  },
                }
              : sess
          ),
        }))
      } finally {
        currentAbortController = null
        set({ isGenerating: false })
      }
    },

    abortGeneration: () => {
      if (currentAbortController) {
        currentAbortController.abort()
        currentAbortController = null
      }
      set((s) => {
        const session = s.sessions.find((x) => x.id === s.activeSessionId)
        if (!session) return { isGenerating: false }
        return {
          isGenerating: false,
          sessions: s.sessions.map((sess) =>
            sess.id === s.activeSessionId
              ? {
                  ...sess,
                  agentA: { ...sess.agentA, status: 'online' },
                  agentB: {
                    ...sess.agentB,
                    status: sess.agentB.status === 'working' ? 'waiting' : sess.agentB.status,
                  },
                }
              : sess
          ),
        }
      })
    },

    sendPrompt: async (text: string, opts = {}) => {
      const state = get()
      const session = state.sessions.find((s) => s.id === state.activeSessionId)
      if (!session) return

      const settings = useSettingsStore.getState()
      const files = opts.files ?? session.attachedFiles
      const folder = opts.folder ?? session.workspaceFolder
      // Session is the source of truth (settings is the fallback for a new session).
      const rawA = session.agentA.model || settings.agentAModel
      const rawB = session.agentB.model || settings.agentBModel
      const isBEnabled = !!rawB && settings.preset !== 'CHAT'
      // 🪄 Auto: resolve to the best installed model for THIS prompt (and a
      // different-family reviewer). Non-Auto models pass through unchanged.
      const avail = settings.availableModels
      const agentAModel = pickModel(rawA, text, 'A', avail, !!folder)
      const agentBModel = pickModel(rawB, text, 'B', avail, !!folder, agentAModel)

      const fullPrompt = buildPrompt(text, files, folder)

      const userMsg: AgentMessage = {
        id: makeId(),
        role: 'user',
        text,
        timestamp: Date.now(),
      }

      const abortCtrl = new AbortController()
      currentAbortController = abortCtrl
      set({ isGenerating: true, unloadStatus: '' })

      const updatedA: AgentState = {
        ...session.agentA,
        messages: [...session.agentA.messages, userMsg],
        status: 'working',
        model: rawA,                 // keep 🪄 Auto sticky
        resolvedModel: agentAModel,  // the concrete model the router chose
      }
      const updatedB: AgentState = {
        ...session.agentB,
        status: isBEnabled ? 'waiting' : 'disabled',
        model: isBEnabled ? rawB : '',
        resolvedModel: isBEnabled ? agentBModel : undefined,
      }
      set((s) => ({
        sessions: s.sessions.map((sess) =>
          sess.id === s.activeSessionId
            ? { ...sess, agentA: updatedA, agentB: updatedB, attachedFiles: files, workspaceFolder: folder, winner: null, executionResult: null }
            : sess
        ),
      }))

      const isAborted = () => abortCtrl.signal.aborted

      try {
        // ── Phase 1: Agent-A reasons ──
        // Agent-A is the "doer" — it always has tool access (the whole point of a
        // Claude-Code-style agent). The MCP toggle only affects whether the user
        // can turn this off explicitly; by default A can read/write the workspace.
        const streamIdA = pushStreamingMessage('A')
        let accA = ''
        const aResult = await callOllama(fullPrompt, agentAModel, settings.systemPromptA, {
          workspaceFolder: folder,
          attachedFiles: files,
          enableTools: settings.preset !== 'CHAT',
          temperature: settings.temperatureA,
          contextLength: settings.contextLength,
          signal: abortCtrl.signal,
          onToken: (d) => { accA += d; updateStreamingMessage('A', streamIdA, accA, true) },
        })
        const responseA = aResult.text
        const toolContextA = aResult.toolContext
        // Finalize the live message with the clean final output (which may differ
        // from the raw streamed tokens, e.g. after a fast-path/synthesis summary).
        updateStreamingMessage('A', streamIdA, responseA, false)

        if (isAborted() || responseA === '[Stopped by user]') {
          set((s) => {
            const sess = s.sessions.find((x) => x.id === s.activeSessionId)
            if (!sess) return s
            const stoppedMsg: AgentMessage = {
              id: makeId(),
              role: 'system',
              text: '⏹ Generation stopped by user.',
              timestamp: Date.now(),
            }
            return {
              sessions: s.sessions.map((sess) =>
                sess.id === s.activeSessionId
                  ? {
                      ...sess,
                      agentA: {
                        ...sess.agentA,
                        status: 'online',
                        messages: [...sess.agentA.messages, stoppedMsg],
                      },
                      agentB: {
                        ...sess.agentB,
                        status: sess.agentB.status === 'working' ? 'waiting' : sess.agentB.status,
                      },
                    }
                  : sess
              ),
            }
          })
          return
        }

        // The streaming placeholder already holds the final responseA — just
        // flip status to online (no duplicate message).
        // Verify Agent-A unloaded
        const verifyA = await verifyZeroModels()
        set({ unloadStatus: `Agent-A done → ${verifyA.status}` })

        if (!isBEnabled) {
          set((s) => ({
            sessions: s.sessions.map((sess) =>
              sess.id === s.activeSessionId ? { ...sess, agentA: { ...sess.agentA, status: 'online' } } : sess
            ),
          }))
          return
        }

        const bReady: AgentState = {
          ...updatedB,
          status: 'working',
        }
        set((s) => ({
          sessions: s.sessions.map((sess) =>
            sess.id === s.activeSessionId ? { ...sess, agentA: { ...sess.agentA, status: 'online' }, agentB: bReady } : sess
          ),
        }))

        // ── Phase 2: Agent-B reviews INDEPENDENTLY ──
        const truncatedA = truncate(responseA, 4000)
        const groundTruth = toolContextA
          ? `\nAgent-A's tool results (real data from the machine):\n${truncate(toolContextA, 3000)}\n`
          : ''
        const reviewPrompt = `The user asked:

"""${text}"""

Agent-A answered:

"""${truncatedA}"""
${groundTruth}
You are an INDEPENDENT senior reviewer. Do NOT simply agree with or repeat Agent-A.
- First decide if Agent-A actually answered the request. If Agent-A asked for clarification or said the request was unclear, but a workspace folder or attached files ARE available, that is a MISTAKE — investigate it YOURSELF: use the tools (file_explorer to list/read files, search_ripgrep, etc.) to inspect the folder/files and produce a real answer.
- Independently verify Agent-A's claims. If Agent-A claims an action succeeded (e.g. "file created"), confirm it with a tool before repeating the claim. Never restate an unverified claim.
- Detect and fix bugs, wrong assumptions, and hallucinations. Explain what was wrong, then give the corrected, better answer/plan.
- NEVER invent data (file names, numbers, headlines, IPs). If something is genuinely unavailable, say so.
- Be concise and structured. Do not repeat raw JSON.`

        const reviewSystem =
          'You are an independent senior reviewer and problem-solver. You verify claims with tools, ' +
          'find and correct mistakes, and proactively investigate the workspace/attachments instead of ' +
          'asking the user for clarification. You never fabricate data.'

        const streamIdB = pushStreamingMessage('B')
        let accB = ''
        const bResult = await callOllama(reviewPrompt, agentBModel, reviewSystem, {
          workspaceFolder: folder,
          attachedFiles: files,
          enableTools: settings.preset !== 'CHAT',
          temperature: settings.temperatureB,
          contextLength: settings.contextLength,
          signal: abortCtrl.signal,
          agent: 'B',
          onToken: (d) => { accB += d; updateStreamingMessage('B', streamIdB, accB, true) },
        })
        const responseB = bResult.text
        updateStreamingMessage('B', streamIdB, responseB, false)

        if (isAborted() || responseB === '[Stopped by user]') {
          set((s) => {
            const sess = s.sessions.find((x) => x.id === s.activeSessionId)
            if (!sess) return s
            const stoppedMsg: AgentMessage = {
              id: makeId(),
              role: 'system',
              text: '⏹ Generation stopped by user during review.',
              timestamp: Date.now(),
            }
            return {
              sessions: s.sessions.map((sess) =>
                sess.id === s.activeSessionId
                  ? {
                      ...sess,
                      agentA: { ...sess.agentA, status: 'online' },
                      agentB: {
                        ...sess.agentB,
                        status: 'waiting',
                        messages: [...sess.agentB.messages, stoppedMsg],
                      },
                    }
                  : sess
              ),
            }
          })
          return
        }

        // The streaming placeholder already holds the final responseB.
        // Verify Agent-B unloaded
        const verifyB = await verifyZeroModels()
        set({ unloadStatus: `Agent-B done → ${verifyB.status}` })

        set((s) => ({
          sessions: s.sessions.map((sess) =>
            sess.id === s.activeSessionId ? { ...sess, agentB: { ...sess.agentB, status: 'online' } } : sess
          ),
        }))
      } finally {
        currentAbortController = null
        set({ isGenerating: false })
      }
    },

    clear: () =>
      set((s) => {
        const fresh = makeSession(s.activeSessionId, 'New Session')
        return {
          sessions: s.sessions.map((sess) =>
            sess.id === s.activeSessionId ? fresh : sess
          ),
        }
      }),
  }
})

// Persist sessions to localStorage on every change (debounced) so they survive
// page reloads and backend restarts. Only the user deletes/renames/pins them.
if (typeof window !== 'undefined') {
  let timeout: ReturnType<typeof setTimeout>
  useSessionStore.subscribe((state) => {
    clearTimeout(timeout)
    timeout = setTimeout(() => persistSessions(state.sessions, state.activeSessionId), 250)
  })
}
