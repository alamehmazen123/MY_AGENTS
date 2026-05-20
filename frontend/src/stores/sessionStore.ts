import { create } from 'zustand'

interface Message {
  role: string
  text: string
}

interface SessionState {
  messages: Message[]
  addMessage: (m: Message) => void
  clear: () => void
}

export const useSessionStore = create<SessionState>((set) => ({
  messages: [],
  addMessage: (m) => set((s) => ({ messages: [...s.messages, m] })),
  clear: () => set({ messages: [] }),
}))
