import { create } from 'zustand'

export interface ObservabilityMetrics {
  active_requests: number
  avg_latency_ms: number
  total_tool_calls: number
  failed_requests: number
  running_cells: Record<string, string>
  request_count: number
}

export interface ObservabilityTrace {
  tool: string
  args: any
  duration_ms: number
  status: string
  timestamp: number
}

export interface ObservabilityFailure {
  trace_id: string | null
  category: string
  context: any
  timestamp: number
  exception_type?: string
  exception_msg?: string
}

export interface LogFile {
  name: string
  filename: string
  size_bytes: number
}

interface ObservabilityState {
  metrics: ObservabilityMetrics
  traces: ObservabilityTrace[]
  failures: ObservabilityFailure[]
  logs: LogFile[]
  logContents: Record<string, string[]>
  lastUpdated: number
  fetchMetrics: () => Promise<void>
  fetchTraces: (n?: number) => Promise<void>
  fetchFailures: (n?: number) => Promise<void>
  fetchLogs: () => Promise<void>
  fetchLogContents: (name: string, lines?: number) => Promise<void>
  clearLogContents: (name: string) => Promise<void>
  clearTraces: () => Promise<void>
  clearFailures: () => Promise<void>
  pollAll: () => Promise<void>
}

const DEFAULT_METRICS: ObservabilityMetrics = {
  active_requests: 0,
  avg_latency_ms: 0,
  total_tool_calls: 0,
  failed_requests: 0,
  running_cells: {},
  request_count: 0,
}

export const useObservabilityStore = create<ObservabilityState>((set, get) => ({
  metrics: DEFAULT_METRICS,
  traces: [],
  failures: [],
  logs: [],
  logContents: {},
  lastUpdated: 0,

  fetchMetrics: async () => {
    try {
      const res = await fetch('/api/observability/metrics')
      if (res.ok) {
        const data = await res.json()
        set({ metrics: data, lastUpdated: Date.now() })
      }
    } catch {
      // silent fail — dashboard is best-effort
    }
  },

  fetchTraces: async (n = 50) => {
    try {
      const res = await fetch(`/api/observability/traces?n=${n}`)
      if (res.ok) {
        const data = await res.json()
        set({ traces: data.traces || [], lastUpdated: Date.now() })
      }
    } catch {
      // silent fail
    }
  },

  fetchFailures: async (n = 50) => {
    try {
      const res = await fetch(`/api/observability/failures?n=${n}`)
      if (res.ok) {
        const data = await res.json()
        set({ failures: data.failures || [], lastUpdated: Date.now() })
      }
    } catch {
      // silent fail
    }
  },

  fetchLogs: async () => {
    try {
      const res = await fetch('/api/observability/logs')
      if (res.ok) {
        const data = await res.json()
        set({ logs: data.logs || [], lastUpdated: Date.now() })
      }
    } catch {
      // silent fail
    }
  },

  fetchLogContents: async (name: string, lines = 100) => {
    try {
      const res = await fetch(`/api/observability/logs/${name}?lines=${lines}`)
      if (res.ok) {
        const data = await res.json()
        set((s) => ({
          logContents: { ...s.logContents, [name]: data.lines || [] },
          lastUpdated: Date.now(),
        }))
      }
    } catch {
      // silent fail
    }
  },

  clearLogContents: async (name: string) => {
    set((s) => ({
      logContents: { ...s.logContents, [name]: [] },
      lastUpdated: Date.now(),
    }))
    try {
      await fetch(`/api/observability/logs/${name}/clear`, { method: 'POST' })
      await get().fetchLogs()
      await get().fetchLogContents(name)
    } catch {
      // best-effort
    }
  },

  clearTraces: async () => {
    set({ traces: [], lastUpdated: Date.now() })
    try {
      await fetch('/api/observability/clear/traces', { method: 'POST' })
    } catch {
      // best-effort
    }
  },

  clearFailures: async () => {
    set({ failures: [], lastUpdated: Date.now() })
    try {
      await fetch('/api/observability/clear/failures', { method: 'POST' })
    } catch {
      // best-effort
    }
  },

  pollAll: async () => {
    const state = useObservabilityStore.getState()
    await Promise.all([
      state.fetchMetrics(),
      state.fetchTraces(20),
      state.fetchFailures(20),
      state.fetchLogs(),
    ])
  },
}))
