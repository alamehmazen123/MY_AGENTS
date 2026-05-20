import { create } from 'zustand'

export interface AgentMessage {
  id: string
  role: 'user' | 'agent' | 'system'
  text: string
  timestamp: number
  streaming?: boolean
}

export interface AgentState {
  messages: AgentMessage[]
  status: 'idle' | 'online' | 'working' | 'paused'
  model: string
}

export interface SessionState {
  agentA: AgentState
  agentB: AgentState
  sendPrompt: (text: string) => void
  appendToAgent: (agent: 'A' | 'B', text: string) => void
  setAgentStreaming: (agent: 'A' | 'B', streaming: boolean) => void
  setAgentStatus: (agent: 'A' | 'B', status: AgentState['status']) => void
  clear: () => void
}

let msgId = 0

export const useSessionStore = create<SessionState>((set) => ({
  agentA: {
    messages: [],
    status: 'online',
    model: 'deepseek-coder:latest',
  },
  agentB: {
    messages: [],
    status: 'online',
    model: 'qwen2.5-coder:14b',
  },

  sendPrompt: (text: string) => {
    const id = `msg-${++msgId}`
    const userMsg: AgentMessage = { id, role: 'user', text, timestamp: Date.now() }

    set((s) => ({
      agentA: { ...s.agentA, messages: [...s.agentA.messages, userMsg], status: 'working' },
      agentB: { ...s.agentB, messages: [...s.agentB.messages, userMsg], status: 'working' },
    }))

    // Simulate Agent-A response
    setTimeout(() => {
      set((s) => ({
        agentA: {
          ...s.agentA,
          messages: [
            ...s.agentA.messages,
            {
              id: `msg-${++msgId}`,
              role: 'agent',
              text: `Agent-A is analyzing: "${text}"`,
              timestamp: Date.now(),
            },
          ],
          status: 'online',
        },
      }))
    }, 1000)

    // Simulate Agent-B response
    setTimeout(() => {
      set((s) => ({
        agentB: {
          ...s.agentB,
          messages: [
            ...s.agentB.messages,
            {
              id: `msg-${++msgId}`,
              role: 'agent',
              text: `Agent-B review: Looks good.`,
              timestamp: Date.now(),
            },
          ],
          status: 'online',
        },
      }))
    }, 1800)
  },

  appendToAgent: (agent, text) => {
    set((s) => {
      if (agent === 'A') {
        return {
          agentA: {
            ...s.agentA,
            messages: [
              ...s.agentA.messages,
              { id: `msg-${++msgId}`, role: 'agent', text, timestamp: Date.now() },
            ],
          },
        }
      }
      return {
        agentB: {
          ...s.agentB,
          messages: [
            ...s.agentB.messages,
            { id: `msg-${++msgId}`, role: 'agent', text, timestamp: Date.now() },
          ],
        },
      }
    })
  },

  setAgentStreaming: (agent, streaming) => {
    set((s) => {
      if (agent === 'A') {
        return { agentA: { ...s.agentA, streaming } }
      }
      return { agentB: { ...s.agentB, streaming } }
    })
  },

  setAgentStatus: (agent, status) => {
    set((s) => {
      if (agent === 'A') {
        return { agentA: { ...s.agentA, status } }
      }
      return { agentB: { ...s.agentB, status } }
    })
  },

  clear: () =>
    set({
      agentA: { messages: [], status: 'online', model: 'deepseek-coder:latest' },
      agentB: { messages: [], status: 'online', model: 'qwen2.5-coder:14b' },
    }),
}))
