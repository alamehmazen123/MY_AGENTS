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
  agentA: AgentState
  agentB: AgentState
  attachedFiles: AttachedFile[]
  workspaceFolder: string
}

export interface SessionState {
  sessions: Session[]
  activeSessionId: string
  isGenerating: boolean
  sendPrompt: (text: string, opts?: { files?: AttachedFile[]; folder?: string }) => void
  abortGeneration: () => void
  createSession: () => void
  switchSession: (id: string) => void
  deleteSession: (id: string) => void
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
): Promise<string> {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), 185_000)

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
      return `[Error: ${data.error}] ${data.output || ''}`
    }
    return data.output || '[No response from model]'
  } catch (e: any) {
    clearTimeout(timeoutId)
    if (e.name === 'AbortError') {
      if (opts?.signal?.aborted) {
        return '[Stopped by user]'
      }
      return '[Error: Request timed out after 185s. The model may be overloaded or Ollama is not responding.]'
    }
    return `[Error: ${e.message}]`
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
  }
}

export const useSessionStore = create<SessionState>((set, get) => {
  const initial = makeSession('sess-1', 'Session 1')
  return {
    sessions: [initial],
    activeSessionId: initial.id,
    isGenerating: false,

    createSession: () => {
      const id = `sess-${Date.now()}`
      const name = `Session ${get().sessions.length + 1}`
      const session = makeSession(id, name)
      set((s) => ({ sessions: [...s.sessions, session], activeSessionId: id }))
    },

    switchSession: (id: string) => {
      set({ activeSessionId: id })
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
      set({ isGenerating: true })

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
            ? { ...sess, agentA: updatedA, agentB: updatedB, attachedFiles: files, workspaceFolder: folder }
            : sess
        ),
      }))

      const isAborted = () => abortCtrl.signal.aborted

      try {
        // ── Phase 1: Agent-A reasons ──
        const responseA = await callOllama(fullPrompt, settings.agentAModel, settings.systemPromptA, {
          workspaceFolder: folder,
          attachedFiles: files,
          enableTools: settings.mcpToolsEnabled,
          temperature: settings.temperatureA,
          contextLength: settings.contextLength,
          signal: abortCtrl.signal,
        })

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
        const reviewPrompt = `You are a senior code reviewer. The user asked:

"""${text}"""

Another agent responded with:

"""${truncatedA}"""

Your task: Review the response above. Identify any bugs, errors, hallucinations, or incorrect assumptions. Then provide YOUR OWN corrected and improved answer. Be concise but thorough. Do NOT repeat raw JSON or error messages verbatim.`

        const responseB = await callOllama(reviewPrompt, settings.agentBModel, settings.systemPromptB, {
          enableTools: false,
          temperature: settings.temperatureB,
          contextLength: settings.contextLength,
          signal: abortCtrl.signal,
        })

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
