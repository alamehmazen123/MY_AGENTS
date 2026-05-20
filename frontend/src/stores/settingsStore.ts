import { create } from 'zustand'

export type Theme = 'system' | 'dark' | 'light'

interface SettingsState {
  theme: Theme
  agentAModel: string
  agentBModel: string
  availableModels: string[]
  mcpEnabled: Record<string, boolean>
  setTheme: (t: Theme) => void
  setAgentAModel: (m: string) => void
  setAgentBModel: (m: string) => void
  setAvailableModels: (models: string[]) => void
  setMcpEnabled: (name: string, enabled: boolean) => void
  fetchModels: () => Promise<void>
  applyTheme: () => void
}

const MCP_PRESETS = [
  'file_explorer', 'code_analyzer', 'git_mcp', 'search_ripgrep',
  'python_exec', 'terminal_whitelist', 'diff_engine', 'refactor_safe',
  'doc_generator', 'dependency_inspector', 'workspace_indexer',
  'health_monitor', 'project_scaffold', 'rollback_manager',
]

const defaultMcpEnabled: Record<string, boolean> = {}
MCP_PRESETS.forEach((name) => { defaultMcpEnabled[name] = true })

function getSystemTheme(): 'dark' | 'light' {
  if (typeof window !== 'undefined') {
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
  }
  return 'dark'
}

export const useSettingsStore = create<SettingsState>((set, get) => ({
  theme: 'dark',
  agentAModel: 'deepseek-coder:latest',
  agentBModel: 'qwen2.5-coder:14b',
  availableModels: [
    'deepseek-coder:latest',
    'qwen2.5-coder:14b',
    'llama3:8b',
    'phi4:14b',
  ],
  mcpEnabled: { ...defaultMcpEnabled },

  setTheme: (theme) => {
    set({ theme })
    // Defer DOM update to next tick so React doesn't complain during render
    setTimeout(() => get().applyTheme(), 0)
  },
  setAgentAModel: (agentAModel) => set({ agentAModel }),
  setAgentBModel: (agentBModel) => set({ agentBModel }),
  setAvailableModels: (availableModels) => set({ availableModels }),
  setMcpEnabled: (name, enabled) =>
    set((s) => ({ mcpEnabled: { ...s.mcpEnabled, [name]: enabled } })),

  fetchModels: async () => {
    try {
      const res = await fetch('/api/models')
      if (res.ok) {
        const data = await res.json()
        if (data.models && data.models.length > 0) {
          set({ availableModels: data.models })
        }
      }
    } catch {
      // fallback to defaults
    }
  },

  applyTheme: () => {
    const t = get().theme
    const effective = t === 'system' ? getSystemTheme() : t
    const root = document.documentElement
    if (effective === 'dark') {
      root.classList.add('dark')
      root.classList.remove('light')
    } else {
      root.classList.remove('dark')
      root.classList.add('light')
    }
  },
}))
