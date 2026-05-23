import { create } from 'zustand'

export type Theme = 'system' | 'dark' | 'light'
export type PresetName = 'CHAT' | 'REVIEWING' | 'CODING' | 'SUPER_CODING' | 'EXECUTION' | 'CUSTOM'

export interface PresetConfig {
  name: string
  description: string
  agentA: {
    name: string
    contextLength: number
    temperature: number
    systemPrompt: string
  }
  agentB: {
    name: string
    contextLength: number
    temperature: number
    systemPrompt: string
  } | null
  mcpToolsEnabled: boolean
}

export const PRESETS: Record<PresetName, PresetConfig> = {
  CHAT: {
    name: 'CHAT',
    description: 'General conversation, no code execution. ~2.5 GB RAM, 10-18 tok/s.',
    agentA: {
      name: 'qwen3:4b',
      contextLength: 4096,
      temperature: 0.7,
      systemPrompt: 'You are a helpful assistant. Respond clearly and concisely to user questions.',
    },
    agentB: null,
    mcpToolsEnabled: false,
  },
  REVIEWING: {
    name: 'REVIEWING',
    description: 'Fast response + deep quality review. ~6.0 GB RAM.',
    agentA: {
      name: 'qwen3:1.7b',
      contextLength: 4096,
      temperature: 0.7,
      systemPrompt: 'You are a content creator. Write a draft response to the user request.',
    },
    agentB: {
      name: 'qwen3:8b',
      contextLength: 4096,
      temperature: 0.3,
      systemPrompt: 'You are a senior editor. Review the draft and provide specific improvements. Focus on clarity, accuracy, and completeness. Output the improved version only.',
    },
    mcpToolsEnabled: false,
  },
  CODING: {
    name: 'CODING',
    description: 'Fast code generation + quality review. ~5.5 GB RAM.',
    agentA: {
      name: 'deepseek-coder:1.3b',
      contextLength: 8192,
      temperature: 0.2,
      systemPrompt: 'You are an expert programmer. Write clean, efficient, well-commented code. Include error handling. Use the best practices for the requested language.',
    },
    agentB: {
      name: 'qwen2.5-coder:3b',
      contextLength: 8192,
      temperature: 0.3,
      systemPrompt: 'You are a code reviewer. Review the code for bugs, security issues, and optimization opportunities. Provide the corrected/improved version with explanations.',
    },
    mcpToolsEnabled: true,
  },
  SUPER_CODING: {
    name: 'SUPER_CODING',
    description: 'Quality generation + ultimate review. ~5.7 GB RAM.',
    agentA: {
      name: 'qwen2.5-coder:3b',
      contextLength: 8192,
      temperature: 0.2,
      systemPrompt: 'You are a senior software architect. Design and implement robust, scalable solutions. Consider edge cases, error handling, and maintainability.',
    },
    agentB: {
      name: 'deepseek-coder:6.7b',
      contextLength: 8192,
      temperature: 0.3,
      systemPrompt: 'You are a principal engineer. Critically review the architecture and implementation. Check for design patterns, security vulnerabilities, performance bottlenecks, and code smells. Provide refactored version with detailed feedback.',
    },
    mcpToolsEnabled: true,
  },
  EXECUTION: {
    name: 'EXECUTION',
    description: 'Automated code execution and verification. ~3.3 GB RAM.',
    agentA: {
      name: 'deepseek-coder:1.3b',
      contextLength: 16384,
      temperature: 0.1,
      systemPrompt: 'You are a code execution agent. Your job is to: 1. Analyze the user request 2. Write the EXACT code needed 3. Execute via MCP tools 4. Report results (success/failure, output, errors). Always verify file paths and handle errors gracefully.',
    },
    agentB: {
      name: 'qwen3:4b',
      contextLength: 16384,
      temperature: 0.2,
      systemPrompt: 'You are a verification agent. Check the execution results from Agent-A. If errors exist, diagnose the root cause and suggest fixes. If successful, verify the output meets the original requirements.',
    },
    mcpToolsEnabled: true,
  },
  CUSTOM: {
    name: 'CUSTOM',
    description: 'User-defined configuration.',
    agentA: {
      name: 'deepseek-coder:latest',
      contextLength: 8192,
      temperature: 0.7,
      systemPrompt: 'You are a helpful AI coding assistant. Answer precisely and accurately.',
    },
    agentB: {
      name: 'qwen2.5-coder:14b',
      contextLength: 8192,
      temperature: 0.3,
      systemPrompt: 'You are a senior code reviewer. Review the other agent response carefully.',
    },
    mcpToolsEnabled: true,
  },
}

export const HIGH_RISK_MODELS = ['deepseek-r1:8b', 'qwen2.5-coder:14b', 'gpt-oss:20b']

// Baseline list; the live set is merged from /api/models at runtime (fetchModels).
export const ALL_MODELS = [
  'tinyllama',
  'qwen3:1.7b',
  'qwen3:4b',
  'qwen3:8b',
  'cogito:8b',
  'qwen2.5-coder:3b',
  'qwen2.5-coder:14b',
  'deepseek-coder:1.3b',
  'deepseek-coder:6.7b',
  'deepseek-coder:latest',
]

export type ModelTier = 'Weak' | 'Moderate' | 'Strong' | 'Very Strong'

export interface ModelMeta {
  tier: ModelTier
  note: string
}

// Explicit notes for known local models. Anything not listed falls back to a
// size-based heuristic in modelMeta() below.
const MODEL_NOTES: Record<string, ModelMeta> = {
  'tinyllama': { tier: 'Weak', note: 'tiny 1.1B — testing / very simple chat only' },
  'qwen3:1.7b': { tier: 'Weak', note: '1.7B — quick, simple Q&A' },
  'deepseek-coder:1.3b': { tier: 'Weak', note: '1.3B coder — short snippets, fast' },
  'deepseek-coder:latest': { tier: 'Weak', note: '1.3B coder — short snippets, fast' },
  'qwen2.5-coder:3b': { tier: 'Moderate', note: '3B coder — everyday code, fast' },
  'qwen3:4b': { tier: 'Moderate', note: '4B — balanced general tasks' },
  'qwen3:8b': { tier: 'Strong', note: '8B — solid reasoning & review' },
  'cogito:8b': { tier: 'Strong', note: '8B Cogito v1 — hybrid reasoning, instruction-tuned' },
  'deepseek-r1:8b': { tier: 'Strong', note: '8B reasoning — capable but slower' },
  'qwen2.5-coder:7b': { tier: 'Strong', note: '7B coder — strong code gen & review' },
  'deepseek-coder:6.7b': { tier: 'Strong', note: '6.7B coder — good code review' },
  'llama3:8b': { tier: 'Strong', note: '8B — strong general chat' },
  'llama3:latest': { tier: 'Strong', note: '8B — strong general chat' },
  'qwen2.5-coder:14b': { tier: 'Very Strong', note: '14B coder — best code, slow on CPU' },
  'phi4:14b': { tier: 'Very Strong', note: '14B — strong reasoning, slow on CPU' },
  'gpt-oss:20b': { tier: 'Very Strong', note: '20B — most capable, very slow on CPU' },
}

export function modelMeta(name: string): ModelMeta {
  if (MODEL_NOTES[name]) return MODEL_NOTES[name]
  // Heuristic: parse the parameter size from the tag (e.g. ":7b", "-1.3b").
  const m = name.match(/(\d+(?:\.\d+)?)\s*b\b/i)
  const size = m ? parseFloat(m[1]) : 0
  const coder = /coder|code/i.test(name)
  if (size === 0) return { tier: 'Moderate', note: 'unknown size — test before relying on it' }
  if (size < 2) return { tier: 'Weak', note: `${size}B — simple tasks only` }
  if (size < 5) return { tier: 'Moderate', note: `${size}B${coder ? ' coder' : ''} — everyday tasks` }
  if (size < 10) return { tier: 'Strong', note: `${size}B${coder ? ' coder' : ''} — capable` }
  return { tier: 'Very Strong', note: `${size}B${coder ? ' coder' : ''} — heavy, slow on CPU` }
}

export function modelLabel(name: string): string {
  const meta = modelMeta(name)
  return `${name}  ·  ${meta.tier} — ${meta.note}`
}

const MCP_PRESETS = [
  'file_explorer', 'code_analyzer', 'git_mcp', 'search_ripgrep',
  'python_exec', 'terminal_whitelist', 'diff_engine', 'refactor_safe',
  'doc_generator', 'dependency_inspector', 'workspace_indexer',
  'health_monitor', 'project_scaffold', 'rollback_manager',
  'web_fetch', 'network_info', 'clock', 'calculator', 'text_stats',
  'memory', 'sequential_thinking', 'sqlite_query', 'csv_json', 'http_request',
  'wikipedia', 'weather', 'arxiv', 'ip_geolocation', 'dns_lookup',
  'html_to_markdown', 'clipboard', 'convert_units', 'pdf_extract',
  'office_reader', 'screenshot', 'process_monitor', 'qr_code', 'sympy_math',
]

const defaultMcpEnabled: Record<string, boolean> = {}
MCP_PRESETS.forEach((name) => { defaultMcpEnabled[name] = true })

const STORAGE_KEY = 'my_agents_settings_v2'

function loadPersisted(): Partial<SettingsState> | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) return JSON.parse(raw)
  } catch {}
  return null
}

function getSystemTheme(): 'dark' | 'light' {
  if (typeof window !== 'undefined') {
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
  }
  return 'dark'
}

interface SettingsState {
  theme: Theme
  preset: PresetName
  agentAModel: string
  agentBModel: string
  temperatureA: number
  temperatureB: number
  systemPromptA: string
  systemPromptB: string
  contextLength: number
  mcpToolsEnabled: boolean
  availableModels: string[]
  mcpEnabled: Record<string, boolean>
  setTheme: (t: Theme) => void
  setPreset: (p: PresetName) => void
  setAgentAModel: (m: string) => void
  setAgentBModel: (m: string) => void
  setTemperatureA: (v: number) => void
  setTemperatureB: (v: number) => void
  setSystemPromptA: (v: string) => void
  setSystemPromptB: (v: string) => void
  setContextLength: (v: number) => void
  setMcpToolsEnabled: (v: boolean) => void
  setMcpEnabled: (name: string, enabled: boolean) => void
  fetchModels: () => Promise<void>
  applyTheme: () => void
}

const persisted = loadPersisted()

export const useSettingsStore = create<SettingsState>((set, get) => {
  const defaults = PRESETS.CODING
  const initial: SettingsState = {
    theme: 'dark',
    preset: 'CODING',
    agentAModel: defaults.agentA.name,
    agentBModel: defaults.agentB?.name || '',
    temperatureA: defaults.agentA.temperature,
    temperatureB: defaults.agentB?.temperature ?? 0.3,
    systemPromptA: defaults.agentA.systemPrompt,
    systemPromptB: defaults.agentB?.systemPrompt ?? '',
    contextLength: defaults.agentA.contextLength,
    mcpToolsEnabled: defaults.mcpToolsEnabled,
    availableModels: ALL_MODELS,
    mcpEnabled: { ...defaultMcpEnabled },
    ...persisted,

    setTheme: (theme) => {
      set({ theme })
      setTimeout(() => get().applyTheme(), 0)
    },

    setPreset: (presetName) => {
      if (presetName === 'CUSTOM') {
        set({ preset: presetName })
        return
      }
      const p = PRESETS[presetName]
      set({
        preset: presetName,
        agentAModel: p.agentA.name,
        agentBModel: p.agentB?.name || '',
        temperatureA: p.agentA.temperature,
        temperatureB: p.agentB?.temperature ?? 0.3,
        systemPromptA: p.agentA.systemPrompt,
        systemPromptB: p.agentB?.systemPrompt ?? '',
        contextLength: p.agentA.contextLength,
        mcpToolsEnabled: p.mcpToolsEnabled,
      })
    },

    setAgentAModel: (agentAModel) => set({ agentAModel, preset: 'CUSTOM' }),
    setAgentBModel: (agentBModel) => set({ agentBModel, preset: 'CUSTOM' }),
    setTemperatureA: (temperatureA) => set({ temperatureA, preset: 'CUSTOM' }),
    setTemperatureB: (temperatureB) => set({ temperatureB, preset: 'CUSTOM' }),
    setSystemPromptA: (systemPromptA) => set({ systemPromptA, preset: 'CUSTOM' }),
    setSystemPromptB: (systemPromptB) => set({ systemPromptB, preset: 'CUSTOM' }),
    setContextLength: (contextLength) => set({ contextLength, preset: 'CUSTOM' }),
    setMcpToolsEnabled: (mcpToolsEnabled) => set({ mcpToolsEnabled, preset: 'CUSTOM' }),

    setMcpEnabled: (name, enabled) =>
      set((s) => {
        const next = { ...s.mcpEnabled, [name]: enabled }
        return { mcpEnabled: next, preset: 'CUSTOM' as PresetName }
      }),

    fetchModels: async () => {
      try {
        const res = await fetch('/api/models')
        if (res.ok) {
          const data = await res.json()
          if (data.models && data.models.length > 0) {
            const merged = Array.from(new Set([...get().availableModels, ...data.models]))
            set({ availableModels: merged })
          }
        }
      } catch {
        // fallback
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
  }

  return initial
})

// Persist to localStorage on every change (debounced)
if (typeof window !== 'undefined') {
  let timeout: ReturnType<typeof setTimeout>
  useSettingsStore.subscribe((state) => {
    clearTimeout(timeout)
    timeout = setTimeout(() => {
      const snapshot = {
        theme: state.theme,
        preset: state.preset,
        agentAModel: state.agentAModel,
        agentBModel: state.agentBModel,
        temperatureA: state.temperatureA,
        temperatureB: state.temperatureB,
        systemPromptA: state.systemPromptA,
        systemPromptB: state.systemPromptB,
        contextLength: state.contextLength,
        mcpToolsEnabled: state.mcpToolsEnabled,
        mcpEnabled: state.mcpEnabled,
      }
      localStorage.setItem(STORAGE_KEY, JSON.stringify(snapshot))
    }, 100)
  })
}
