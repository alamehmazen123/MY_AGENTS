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
  status: 'idle' | 'online' | 'working' | 'waiting' | 'paused'
  model: string
}

export interface Session {
  id: string
  name: string
  createdAt: number
  agentA: AgentState
  agentB: AgentState
}

export interface SessionState {
  sessions: Session[]
  activeSessionId: string
  sendPrompt: (text: string) => void
  createSession: () => void
  switchSession: (id: string) => void
  deleteSession: (id: string) => void
  clear: () => void
}

let msgId = 0
function makeId() {
  return `msg-${++msgId}-${Date.now()}`
}

async function callOllama(
  prompt: string,
  model: string,
  system?: string
): Promise<string> {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), 185_000) // 185s client timeout
  try {
    const res = await fetch('/api/prompt', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt, model, system }),
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
      return '[Error: Request timed out after 185s. The model may be overloaded or Ollama is not responding.]'
    }
    return `[Error: ${e.message}]`
  }
}

function truncate(str: string, maxLen: number): string {
  if (str.length <= maxLen) return str
  return str.slice(0, maxLen) + '\n\n[...truncated]'
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
      status: 'waiting',
      model: settings.agentBModel,
    },
  }
}

export const useSessionStore = create<SessionState>((set, get) => {
  const initial = makeSession('sess-1', 'Session 1')
  return {
    sessions: [initial],
    activeSessionId: initial.id,

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

    sendPrompt: async (text: string) => {
      const state = get()
      const session = state.sessions.find((s) => s.id === state.activeSessionId)
      if (!session) return

      const settings = useSettingsStore.getState()
      const userMsg: AgentMessage = {
        id: makeId(),
        role: 'user',
        text,
        timestamp: Date.now(),
      }

      // Update session: Agent-A gets user prompt and goes Working, Agent-B goes Waiting
      const updatedA: AgentState = {
        ...session.agentA,
        messages: [...session.agentA.messages, userMsg],
        status: 'working',
        model: settings.agentAModel,
      }
      const updatedB: AgentState = {
        ...session.agentB,
        status: 'waiting',
        model: settings.agentBModel,
      }
      set((s) => ({
        sessions: s.sessions.map((sess) =>
          sess.id === s.activeSessionId ? { ...sess, agentA: updatedA, agentB: updatedB } : sess
        ),
      }))

      // ── Phase 1: Agent-A reasons ──
      const systemA =
        'You are an expert coding assistant. Answer the user precisely. Only provide factual, accurate information. If unsure, say so.'
      const responseA = await callOllama(text, settings.agentAModel, systemA)

      const aDone: AgentState = {
        ...updatedA,
        messages: [
          ...updatedA.messages,
          { id: makeId(), role: 'agent', text: responseA, timestamp: Date.now() },
        ],
        status: 'online',
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

      // ── Phase 2: Agent-B reviews Agent-A's output ──
      const truncatedA = truncate(responseA, 4000)
      const reviewPrompt = `You are a senior code reviewer. The user asked:

"""${text}"""

Another agent responded with:

"""${truncatedA}"""

Your task: Review the response above. Identify any bugs, errors, hallucinations, or incorrect assumptions. Then provide YOUR OWN corrected and improved answer. Be concise but thorough. Do NOT repeat raw JSON or error messages verbatim.`

      const systemB =
        'You are a senior code reviewer. Be critical and thorough. Point out mistakes and provide corrected answers. Never repeat raw JSON dumps.'
      const responseB = await callOllama(reviewPrompt, settings.agentBModel, systemB)

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
