import { create } from 'zustand'
import { useSettingsStore } from './settingsStore'

export interface AgentMessage {
  id: string
  role: 'user' | 'agent' | 'system' | 'context'
  text: string
  timestamp: number
  streaming?: boolean
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
  executionResult: string | null
}

export interface SessionState {
  sessions: Session[]
  activeSessionId: string
  isGenerating: boolean
  unloadStatus: string
  sendPrompt: (text: string, opts?: { files?: AttachedFile[]; folder?: string }) => void
  abortGeneration: () => void
  selectWinner: (agent: 'A' | 'B') => void
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
): Promise<{ text: string; toolContext: string }> {
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
      return { text: `[Error: ${data.error}] ${data.output || ''}`, toolContext: '' }
    }
    return { text: data.output || '[No response from model]', toolContext: data.tool_context || '' }
  } catch (e: any) {
    clearTimeout(timeoutId)
    if (e.name === 'AbortError') {
      if (opts?.signal?.aborted) {
        return { text: '[Stopped by user]', toolContext: '' }
      }
      return { text: '[Error: Request timed out. The model may be overloaded or Ollama is not responding.]', toolContext: '' }
    }
    return { text: `[Error: ${e.message}]`, toolContext: '' }
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

    executeWinner: async () => {
      const state = get()
      const session = state.sessions.find((s) => s.id === state.activeSessionId)
      if (!session || !session.winner) return

      const winnerAgent = session.winner === 'A' ? session.agentA : session.agentB
      const winnerMsg = winnerAgent.messages
        .filter((m) => m.role === 'agent')
        .pop()

      if (!winnerMsg) return

      set({ isGenerating: true, unloadStatus: 'Executing winner plan...' })

      try {
        const res = await fetch('/api/execute-plan', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            plan: winnerMsg.text,
            workspace_folder: session.workspaceFolder,
          }),
        })
        const data = await res.json()
        const resultText = data.status === 'executed'
          ? `✅ Executed ${data.results?.length || 0} tool(s)\n` + data.results.map((r: any) => `${r.tool}: ${JSON.stringify(r.result).slice(0, 200)}`).join('\n')
          : `⚠️ ${data.status}\n${data.plan || data.error || ''}`

        set((s) => ({
          isGenerating: false,
          unloadStatus: '',
          sessions: s.sessions.map((sess) =>
            sess.id === s.activeSessionId
              ? {
                  ...sess,
                  executionResult: resultText,
                  agentA: { ...sess.agentA, status: 'online' },
                  agentB: { ...sess.agentB, status: sess.agentB.status === 'working' ? 'waiting' : sess.agentB.status },
                }
              : sess
          ),
        }))
      } catch (e: any) {
        set({ isGenerating: false, unloadStatus: `[Error: ${e.message}]` })
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
            { id: makeId(), role: 'agent', text: responseA, timestamp: Date.now() },
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
            { id: makeId(), role: 'agent', text: responseB, timestamp: Date.now() },
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
