import { create } from 'zustand'

interface RuntimeState {
  status: string
  model: string
  queueDepth: number
  setStatus: (s: string) => void
}

export const useRuntimeStore = create<RuntimeState>((set) => ({
  status: 'online',
  model: '',
  queueDepth: 0,
  setStatus: (status) => set({ status }),
}))
