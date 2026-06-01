import { create } from 'zustand'
import { useSettingsStore } from './settingsStore'

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
  }
): Promise<{ text: string; toolContext: string; toolResults: any[]; traceId?: string }> {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), 340_000)

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

    console.log(
      '[SESSION_STORE_TRACE] sending /api/prompt body=',
      JSON.stringify({ preset: body.preset, model: body.model, no_tools: body.no_tools, enableTools: opts?.enableTools, system_len: body.system?.length, prompt_preview: body.prompt?.slice(0, 80) })
    )

    const res = await fetch('/api/prompt', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal: controller.signal,
    })
    clearTimeout(timeoutId)
    if (!res.ok) {
      const err = await res.text()
      throw new Error(err || `HTTP ${res.status}`)
    }
    const data = await res.json()
    if (data.error) {
      return { text: `[Error: ${data.error}] ${data.output || ''}`, toolContext: '', toolResults: [] }
    }
    return {
      text: data.output || '[No response from model]',
      toolContext: data.tool_context || '',
      toolResults: data.tool_results || [],
      traceId: data.trace_id,
    }
  } catch (e: any) {
    clearTimeout(timeoutId)
    if (e.name === 'AbortError') {
      if (opts?.signal?.aborted) {
        return { text: '[Stopped by user]', toolContext: '', toolResults: [] }
      }
      return { text: '[Error: Request timed out. The model may be overloaded or Ollama is not responding.]', toolContext: '', toolResults: [] }
    }
    return { text: `[Error: ${e.message}]`, toolContext: '', toolResults: [] }
  }
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

      try {
        // ── PASS 1: passive extraction from the existing texts. ──
        const plan = [targetMsg?.text, otherMsg?.text].filter(Boolean).join('\n\n')
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
          const model = agent === 'A' ? settings.agentAModel : settings.agentBModel
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
      const isBEnabled = !!settings.agentBModel && settings.preset !== 'CHAT'

      // Use the most recent agent response as the seed for the revision. If
      // Agent-B has spoken, use B; otherwise the most recent A message.
      const lastB = session.agentB.messages.filter((m) => m.role === 'agent').pop()
      const lastA = session.agentA.messages.filter((m) => m.role === 'agent').pop()
      const seed = (lastB?.text || lastA?.text || '').trim()
      if (!seed) return

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
        const aResult = await callOllama(revisePromptA, settings.agentAModel, settings.systemPromptA, {
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

        // ── Phase 2: Agent-B reviews A's NEW answer ──
        const groundTruth = toolCtxA
          ? `\nACTUAL TOOL RESULTS (ground truth):\n${truncate(toolCtxA, 3000)}\n`
          : ''
        const reviewPromptB =
          `Agent-A produced this revised answer:\n"""${truncate(newA, 4000)}"""\n${groundTruth}\n` +
          `Produce an even better final answer. Correct any mistakes using the actual tool results ` +
          `above. CRITICAL: never invent data (file names, headlines, IPs, numbers). Do NOT write ` +
          `code or describe steps; the tools already ran. Be concise.`
        const reviewSystem =
          'You are a fact-checking reviewer. You verify and improve an answer using the real ' +
          'tool results provided. You never fabricate data and never write code.'
        const bResult = await callOllama(reviewPromptB, settings.agentBModel, reviewSystem, {
          enableTools: false,
          temperature: settings.temperatureB,
          contextLength: settings.contextLength,
          signal: abortCtrl.signal,
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
      const isBEnabled = !!settings.agentBModel && settings.preset !== 'CHAT'

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
        model: settings.agentAModel,
      }
      const updatedB: AgentState = {
        ...session.agentB,
        status: isBEnabled ? 'waiting' : 'disabled',
        model: isBEnabled ? settings.agentBModel : '',
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
        const aResult = await callOllama(fullPrompt, settings.agentAModel, settings.systemPromptA, {
          workspaceFolder: folder,
          attachedFiles: files,
          enableTools: settings.preset !== 'CHAT',
          temperature: settings.temperatureA,
          contextLength: settings.contextLength,
          signal: abortCtrl.signal,
        })
        const responseA = aResult.text
        const toolContextA = aResult.toolContext

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

        const aDone: AgentState = {
          ...updatedA,
          messages: [
            ...updatedA.messages,
            { id: makeId(), role: 'agent', text: responseA, timestamp: Date.now(), traceId: aResult.traceId },
          ],
          status: 'online',
        }

        // Verify Agent-A unloaded
        const verifyA = await verifyZeroModels()
        set({ unloadStatus: `Agent-A done → ${verifyA.status}` })

        if (!isBEnabled) {
          set((s) => ({
            sessions: s.sessions.map((sess) =>
              sess.id === s.activeSessionId ? { ...sess, agentA: aDone } : sess
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
            sess.id === s.activeSessionId ? { ...sess, agentA: aDone, agentB: bReady } : sess
          ),
        }))

        // ── Phase 2: Agent-B reviews ──
        const truncatedA = truncate(responseA, 4000)
        const groundTruth = toolContextA
          ? `\nACTUAL TOOL RESULTS (ground truth — the real data from the user's machine):\n${truncate(toolContextA, 3000)}\n`
          : ''
        const reviewPrompt = `The user asked:

"""${text}"""

Agent-A answered:

"""${truncatedA}"""
${groundTruth}
Your task: produce the BEST final answer to the user's request.
- Correct any mistakes in Agent-A's answer using the ACTUAL TOOL RESULTS above as the source of truth.
- CRITICAL: never invent or guess data. Do NOT make up file names, news headlines, IP addresses, or numbers. If the tool results don't contain something (e.g. no headline was returned), say it is unavailable — do NOT fabricate a plausible value.
- Do NOT write code or describe steps; the tools already ran. Just give the direct, corrected answer.
- Be concise. Do not repeat raw JSON.`

        const reviewSystem =
          'You are a fact-checking assistant. You verify and correct an answer using the real tool results provided. ' +
          'You never fabricate data and never write code — you report the actual results.'

        const bResult = await callOllama(reviewPrompt, settings.agentBModel, reviewSystem, {
          enableTools: false,
          temperature: settings.temperatureB,
          contextLength: settings.contextLength,
          signal: abortCtrl.signal,
        })
        const responseB = bResult.text

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

        const bDone: AgentState = {
          ...bReady,
          messages: [
            ...bReady.messages,
            { id: makeId(), role: 'context', text: `Agent-A said:\n${truncate(responseA, 800)}`, timestamp: Date.now() },
            { id: makeId(), role: 'agent', text: responseB, timestamp: Date.now(), traceId: bResult.traceId },
          ],
          status: 'online',
        }

        // Verify Agent-B unloaded
        const verifyB = await verifyZeroModels()
        set({ unloadStatus: `Agent-B done → ${verifyB.status}` })

        set((s) => ({
          sessions: s.sessions.map((sess) =>
            sess.id === s.activeSessionId ? { ...sess, agentB: bDone } : sess
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
