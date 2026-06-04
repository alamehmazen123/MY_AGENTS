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

// Sentinel: when an agent's model is AUTO_MODEL, pickModel() chooses the best
// installed model per prompt (intent-aware, native-tools-aware, family-decorrelated).
export const AUTO_MODEL = '🪄 Auto'

// Baseline list; the live set is merged from /api/models at runtime (fetchModels).
export const ALL_MODELS = [
  AUTO_MODEL,
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
  // Native function/tool-calling support via Ollama /api/chat:
  //  'native' = returns structured tool_calls (verified); best for tool tasks.
  //  'text'   = ignores the tools param, emits calls as text (works via our
  //             regex fallback, but slower & less reliable).
  //  'unknown'= not verified on this machine.
  tools: 'native' | 'text' | 'unknown'
  // Rough speed on a CPU-only box.
  speed: 'fast' | 'medium' | 'slow' | 'very slow'
}

// Explicit notes for known local models. `tools` reflects a real probe of
// Ollama /api/chat on this machine (see PLAN.md). Anything not listed falls
// back to a size-based heuristic in modelMeta() below.
const MODEL_NOTES: Record<string, ModelMeta> = {
  'tinyllama': { tier: 'Weak', tools: 'unknown', speed: 'fast',
    note: '1.1B. Toy/testing model — very simple chat only; unreliable for real tasks.' },
  'qwen3:1.7b': { tier: 'Weak', tools: 'unknown', speed: 'fast',
    note: '1.7B. Quick simple Q&A. Too small for multi-step or tool work.' },
  'deepseek-coder:1.3b': { tier: 'Weak', tools: 'text', speed: 'fast',
    note: '1.3B coder. Fast for short snippets. No native tool-calling — weak on agent/file tasks.' },
  'deepseek-coder:latest': { tier: 'Weak', tools: 'text', speed: 'fast',
    note: '1.3B coder. Fast for short snippets. No native tool-calling — weak on agent/file tasks.' },
  'qwen2.5-coder:3b': { tier: 'Moderate', tools: 'text', speed: 'fast',
    note: '3B coder. Fast, decent everyday code. ⚠️ No native tool-calling — slower & less reliable on file/tool tasks.' },
  'qwen3:4b': { tier: 'Moderate', tools: 'native', speed: 'medium',
    note: '4B. ✅ Native tool-calling. Good balanced Agent-A for tool tasks; can be chatty.' },
  'qwen3:8b': { tier: 'Strong', tools: 'native', speed: 'medium',
    note: '8B. ✅ Native tool-calling. Best all-round Agent-A / reviewer; solid reasoning.' },
  'cogito:8b': { tier: 'Strong', tools: 'native', speed: 'medium',
    note: '8B hybrid reasoner. ✅ Native tool-calling. Strong for tool-driven agent work.' },
  'deepseek-r1:8b': { tier: 'Strong', tools: 'unknown', speed: 'slow',
    note: '8B reasoning. Capable but slow (heavy chain-of-thought). Better for analysis than live tool loops.' },
  'qwen2.5-coder:7b': { tier: 'Strong', tools: 'text', speed: 'medium',
    note: '7B coder. Strong code gen & review. No native tool-calling — relies on text fallback for tools.' },
  'deepseek-coder:6.7b': { tier: 'Strong', tools: 'unknown', speed: 'medium',
    note: '6.7B coder. Good code review. Heavier to cold-load; verify tool use before relying on it.' },
  'llama3:8b': { tier: 'Strong', tools: 'unknown', speed: 'medium',
    note: '8B. Strong general chat & writing. Tool-calling not verified here.' },
  'llama3:latest': { tier: 'Strong', tools: 'unknown', speed: 'medium',
    note: '8B. Strong general chat & writing. Tool-calling not verified here.' },
  'qwen2.5-coder:14b': { tier: 'Very Strong', tools: 'text', speed: 'slow',
    note: '14B coder. Best code quality. ⚠️ No native tool-calling AND slow on CPU — great reviewer, poor live-tool agent.' },
  'phi4:14b': { tier: 'Very Strong', tools: 'unknown', speed: 'slow',
    note: '14B. Strong reasoning, slow on CPU. Best as a deep reviewer, not a fast doer.' },
  'gpt-oss:20b': { tier: 'Very Strong', tools: 'unknown', speed: 'very slow',
    note: '20B. Most capable but very slow on CPU — expect long waits per turn.' },
}

export function modelMeta(name: string): ModelMeta {
  if (MODEL_NOTES[name]) return MODEL_NOTES[name]
  // Heuristic for models not in the table: size from the tag (e.g. ":7b").
  const m = name.match(/(\d+(?:\.\d+)?)\s*b\b/i)
  const size = m ? parseFloat(m[1]) : 0
  const coder = /coder|code/i.test(name)
  const c = coder ? ' coder' : ''
  if (size === 0) return { tier: 'Moderate', tools: 'unknown', speed: 'medium', note: 'Unknown size — test tool use & speed before relying on it.' }
  if (size < 2) return { tier: 'Weak', tools: 'unknown', speed: 'fast', note: `${size}B${c}. Simple tasks only; too small for tool/agent work.` }
  if (size < 5) return { tier: 'Moderate', tools: 'unknown', speed: 'fast', note: `${size}B${c}. Everyday tasks, fast. Verify tool-calling support.` }
  if (size < 10) return { tier: 'Strong', tools: 'unknown', speed: 'medium', note: `${size}B${c}. Capable all-rounder. Verify tool-calling support.` }
  return { tier: 'Very Strong', tools: 'unknown', speed: 'slow', note: `${size}B${c}. High quality but slow on CPU.` }
}

export function modelLabel(name: string): string {
  if (name === AUTO_MODEL) return `${AUTO_MODEL}  ·  picks the best installed model per prompt`
  const meta = modelMeta(name)
  return `${name}  ·  ${meta.tier} — ${meta.note}`
}

// ── 🪄 Auto model router ───────────────────────────────────────────────────
// Classify the prompt and pick the best-suited INSTALLED model. Fixes the #1
// recurring failure: the wrong model for the task (timeouts / hallucination).
type Intent = 'plan' | 'tool' | 'chat'

function classifyIntent(prompt: string, hasFolder: boolean): Intent {
  const low = (prompt || '').toLowerCase()
  if (/(make a plan|improvement (list|plan)|how to improve|improve (this|the|my)|refactor plan|review (the|this) project|plan to improve|audit the project|analyze the project|make it (more professional|better))/.test(low)) {
    return 'plan'
  }
  if (hasFolder ||
      /\b(file|files|folder|directory|read|write|list|search|grep|code|coding|script|\.py|\.ts|\.tsx|\.js|\.md|\.json|\.csv|\.pdf|git|run |execute|debug|refactor|create (a|the)|build|fix|weather|wikipedia|ip address|calculate|compute|fetch|download|screenshot|sql|database)\b/.test(low)) {
    return 'tool'
  }
  return 'chat'
}

const familyOf = (m: string) => (m || '').split(':')[0]

// Preference orders (best first) per use-case; filtered by what's installed.
const PREF_TOOL = ['qwen3:8b', 'cogito:8b', 'qwen3:4b', 'qwen2.5-coder:7b', 'qwen2.5-coder:14b', 'llama3:8b', 'qwen2.5-coder:3b']
const PREF_CHAT = ['qwen3:1.7b', 'qwen2.5-coder:3b', 'qwen3:4b', 'llama3:8b', 'qwen3:8b']
const PREF_REVIEWER = ['cogito:8b', 'qwen3:8b', 'deepseek-coder:6.7b', 'qwen2.5-coder:7b', 'llama3:8b', 'qwen2.5-coder:14b', 'qwen3:4b']

function firstInstalled(pref: string[], installed: string[], avoidFamily?: string): string | undefined {
  // First pass: honor avoidFamily (decorrelate reviewer from doer).
  if (avoidFamily) {
    const diff = pref.find((m) => installed.includes(m) && familyOf(m) !== avoidFamily)
    if (diff) return diff
  }
  return pref.find((m) => installed.includes(m))
}

// Resolve a model that may be AUTO_MODEL into a concrete installed model.
export function pickModel(
  raw: string,
  prompt: string,
  role: 'A' | 'B',
  available: string[],
  hasFolder: boolean,
  peerModel?: string,
): string {
  if (raw !== AUTO_MODEL) return raw
  const installed = available.filter((m) => m !== AUTO_MODEL)
  if (installed.length === 0) return 'qwen3:4b' // sane fallback
  const intent = classifyIntent(prompt, hasFolder)
  if (role === 'B') {
    // Reviewer: strong model, ideally a DIFFERENT family than Agent-A.
    return firstInstalled(PREF_REVIEWER, installed, peerModel ? familyOf(peerModel) : undefined)
      || installed[0]
  }
  // Agent-A (doer)
  const pref = intent === 'chat' ? PREF_CHAT : PREF_TOOL
  return firstInstalled(pref, installed) || installed[0]
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
  permissionMode: 'auto' | 'ask'
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
  setPermissionMode: (m: 'auto' | 'ask') => void
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
    preset: 'CUSTOM',
    // Default to 🪄 Auto for both agents — the router picks the best installed
    // model per prompt (and a different-family reviewer). Removes the #1 user error.
    agentAModel: AUTO_MODEL,
    agentBModel: AUTO_MODEL,
    temperatureA: defaults.agentA.temperature,
    temperatureB: defaults.agentB?.temperature ?? 0.3,
    systemPromptA: defaults.agentA.systemPrompt,
    systemPromptB: defaults.agentB?.systemPrompt ?? '',
    contextLength: defaults.agentA.contextLength,
    permissionMode: 'auto',
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
    setPermissionMode: (permissionMode) => set({ permissionMode }),
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
        permissionMode: state.permissionMode,
        mcpToolsEnabled: state.mcpToolsEnabled,
        mcpEnabled: state.mcpEnabled,
      }
      localStorage.setItem(STORAGE_KEY, JSON.stringify(snapshot))
    }, 100)
  })
}
