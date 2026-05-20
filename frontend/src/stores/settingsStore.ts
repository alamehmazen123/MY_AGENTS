import { create } from 'zustand'

interface SettingsState {
  theme: 'dark' | 'light'
  models: string[]
  setTheme: (t: 'dark' | 'light') => void
}

export const useSettingsStore = create<SettingsState>((set) => ({
  theme: 'dark',
  models: ['qwen2.5-coder:14b', 'llama3:8b', 'phi4:14b'],
  setTheme: (theme) => set({ theme }),
}))
