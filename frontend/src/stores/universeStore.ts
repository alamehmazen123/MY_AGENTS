import { create } from 'zustand'

interface UniverseState {
  state: Record<string, any>
  set: (patch: Record<string, any>) => void
}

export const useUniverseStore = create<UniverseState>((set) => ({
  state: {},
  set: (patch) => set((s) => ({ state: { ...s.state, ...patch } })),
}))
