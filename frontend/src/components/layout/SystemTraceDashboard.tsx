import { useEffect, useState } from 'react'
import { useObservabilityStore } from '../../stores/observabilityStore'
import { LogViewer } from './LogViewer'

function formatDuration(ms: number): string {
  if (ms < 1) return `${(ms * 1000).toFixed(0)}μs`
  if (ms < 1000) return `${ms.toFixed(1)}ms`
  return `${(ms / 1000).toFixed(2)}s`
}

function formatTime(ts: number): string {
  const d = new Date(ts * 1000)
  return d.toLocaleTimeString()
}

function CopyButton({ text, size = 'xs' }: { text: string; size?: 'xs' | 'sm' }) {
  const [copied, setCopied] = useState(false)
  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch {
      /* ignore */
    }
  }
  return (
    <button
      onClick={handleCopy}
      className={`px-1.5 py-0.5 rounded text-${size === 'xs' ? '[9px]' : '[10px]'} bg-gray-800 text-gray-400 hover:bg-gray-700 hover:text-white transition-all flex-shrink-0`}
      title="Copy"
    >
      {copied ? '✓' : '📋'}
    </button>
  )
}

export function SystemTraceDashboard() {
  const metrics = useObservabilityStore((s) => s.metrics)
  const traces = useObservabilityStore((s) => s.traces)
  const failures = useObservabilityStore((s) => s.failures)
  const clearTraces = useObservabilityStore((s) => s.clearTraces)
  const clearFailures = useObservabilityStore((s) => s.clearFailures)
  const pollAll = useObservabilityStore((s) => s.pollAll)
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [confirmMessage, setConfirmMessage] = useState<string | null>(null)

  useEffect(() => {
    pollAll()
    if (!autoRefresh) return
    const id = setInterval(pollAll, 2000)
    return () => clearInterval(id)
  }, [autoRefresh, pollAll])

  const cellEntries = Object.entries(metrics.running_cells)

  return (
    <div className="flex-1 overflow-auto p-4 space-y-4 text-xs">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-bold text-white">🔍 System Trace</h2>
        <label className="flex items-center gap-2 text-gray-400 cursor-pointer">
          <input
            type="checkbox"
            checked={autoRefresh}
            onChange={(e) => setAutoRefresh(e.target.checked)}
            className="rounded border-gray-600"
          />
          Auto-refresh (2s)
        </label>
      </div>
      {confirmMessage && (
        <div className="rounded border border-green-500/30 bg-green-500/10 px-3 py-2 text-[11px] text-green-200">
          {confirmMessage}
        </div>
      )}

      {/* Metrics cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
        <MetricCard label="Active Requests" value={metrics.active_requests} color="blue" />
        <MetricCard label="Avg Latency" value={formatDuration(metrics.avg_latency_ms)} color="purple" />
        <MetricCard label="Tool Calls" value={metrics.total_tool_calls} color="green" />
        <MetricCard label="Failures" value={metrics.failed_requests} color="red" />
        <MetricCard label="Total Requests" value={metrics.request_count} color="gray" />
      </div>

      {/* Running cells */}
      <div className="bg-gray-800 rounded border border-gray-700 p-3">
        <h3 className="text-xs font-bold text-gray-300 mb-2">Running Cells</h3>
        {cellEntries.length === 0 ? (
          <div className="text-gray-500">No cells registered</div>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            {cellEntries.map(([name, state]) => (
              <div key={name} className="flex items-center gap-2 bg-gray-900 rounded px-2 py-1">
                <span className={`w-2 h-2 rounded-full ${state === 'ACTIVE' ? 'bg-green-500' : state === 'DEGRADED' ? 'bg-yellow-500' : 'bg-gray-500'}`} />
                <span className="text-gray-300">{name}</span>
                <span className="text-gray-500 ml-auto">{state}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Log Viewer */}
      <LogViewer />

      {/* Recent traces */}
      <div className="bg-gray-800 rounded border border-gray-700 p-3">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-xs font-bold text-gray-300">Recent MCP Traces</h3>
          <button
            onClick={async () => {
              await clearTraces()
              setConfirmMessage('All traces cleared')
              setTimeout(() => setConfirmMessage(null), 2500)
            }}
            className="px-2 py-0.5 rounded text-[10px] bg-red-700 text-white hover:bg-red-600 transition-colors"
          >
            ✕ Clear
          </button>
        </div>
        {traces.length === 0 ? (
          <div className="text-gray-500">No traces yet</div>
        ) : (
          <div className="space-y-1 max-h-64 overflow-auto">
            {traces.map((t, i) => (
              <div key={i} className="group flex items-center gap-2 bg-gray-900 rounded px-2 py-1">
                <span className={t.status === 'SUCCESS' || t.status === 'ok' ? 'text-green-400' : 'text-red-400'}>
                  {t.status === 'SUCCESS' || t.status === 'ok' ? '✅' : '❌'}
                </span>
                <span className="font-mono text-gray-300">{t.tool}</span>
                <span className="text-gray-500">{formatDuration(t.duration_ms)}</span>
                <span className="text-gray-600 ml-auto">{formatTime(t.timestamp)}</span>
                <CopyButton text={`${t.tool} | ${JSON.stringify(t.args)} | ${t.duration_ms}ms | ${t.status}`} />
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Recent failures */}
      <div className="bg-gray-800 rounded border border-gray-700 p-3">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-xs font-bold text-gray-300">Recent Failures</h3>
          <button
            onClick={async () => {
              await clearFailures()
              setConfirmMessage('All failures cleared')
              setTimeout(() => setConfirmMessage(null), 2500)
            }}
            className="px-2 py-0.5 rounded text-[10px] bg-red-700 text-white hover:bg-red-600 transition-colors"
          >
            ✕ Clear
          </button>
        </div>
        {failures.length === 0 ? (
          <div className="text-gray-500">No failures — system healthy</div>
        ) : (
          <div className="space-y-1 max-h-64 overflow-auto">
            {failures.map((f, i) => (
              <div key={i} className="bg-gray-900 rounded px-2 py-1">
                <div className="flex items-center gap-2">
                  <span className="text-red-400">❌</span>
                  <span className="font-mono text-red-300">{f.category}</span>
                  <span className="text-gray-500 ml-auto">{formatTime(f.timestamp)}</span>
                  <CopyButton text={`[${f.category}] trace=${f.trace_id || 'NO_TRACE'} | ${JSON.stringify(f.context)}`} />
                </div>
                {f.exception_type && (
                  <div className="text-red-400 text-[10px] pl-5">
                    {f.exception_type}: {f.exception_msg}
                  </div>
                )}
                {f.trace_id && (
                  <div className="text-gray-600 text-[10px] pl-5">trace: {f.trace_id}</div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function MetricCard({ label, value, color }: { label: string; value: string | number; color: string }) {
  const colorMap: Record<string, string> = {
    blue: 'border-blue-500/30 text-blue-300',
    purple: 'border-purple-500/30 text-purple-300',
    green: 'border-green-500/30 text-green-300',
    red: 'border-red-500/30 text-red-300',
    gray: 'border-gray-500/30 text-gray-300',
  }
  return (
    <div className={`bg-gray-800 rounded border p-3 ${colorMap[color] || colorMap.gray}`}>
      <div className="text-[10px] uppercase tracking-wider opacity-70">{label}</div>
      <div className="text-lg font-bold mt-1">{value}</div>
    </div>
  )
}
