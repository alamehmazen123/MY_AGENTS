import { useState, useEffect } from 'react'
import { useObservabilityStore } from '../../stores/observabilityStore'

const LOG_NAMES = [
  { key: 'execution_timeline', label: 'Execution Timeline' },
  { key: 'mcp_trace', label: 'MCP Trace' },
  { key: 'agent_reasoning', label: 'Agent Reasoning' },
  { key: 'performance', label: 'Performance' },
  { key: 'failure', label: 'Failures' },
]

function formatBytes(b: number): string {
  if (b < 1024) return `${b} B`
  if (b < 1024 * 1024) return `${(b / 1024).toFixed(1)} KB`
  return `${(b / (1024 * 1024)).toFixed(1)} MB`
}

export function LogViewer() {
  const logs = useObservabilityStore((s) => s.logs)
  const logContents = useObservabilityStore((s) => s.logContents)
  const fetchLogs = useObservabilityStore((s) => s.fetchLogs)
  const fetchLogContents = useObservabilityStore((s) => s.fetchLogContents)
  const clearLogContents = useObservabilityStore((s) => s.clearLogContents)
  const [activeLog, setActiveLog] = useState<string>('execution_timeline')
  const [lineCount, setLineCount] = useState<number>(50)
  const [copiedLine, setCopiedLine] = useState<number | null>(null)

  useEffect(() => {
    fetchLogs()
  }, [fetchLogs])

  useEffect(() => {
    if (activeLog) {
      fetchLogContents(activeLog, lineCount)
    }
  }, [activeLog, lineCount, fetchLogContents])

  const handleCopyLine = async (text: string, index: number) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopiedLine(index)
      setTimeout(() => setCopiedLine(null), 1500)
    } catch {
      /* ignore */
    }
  }

  const handleCopyAll = async () => {
    const lines = logContents[activeLog] || []
    try {
      await navigator.clipboard.writeText(lines.join('\n'))
    } catch {
      /* ignore */
    }
  }

  const currentLines = logContents[activeLog] || []

  const clearCurrentLog = () => {
    clearLogContents(activeLog)
  }

  return (
    <div className="bg-gray-800 rounded border border-gray-700 p-3 space-y-2">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-bold text-gray-300">📄 Log Files</h3>
        <div className="flex items-center gap-2">
          <select
            aria-label="Lines to load"
            value={lineCount}
            onChange={(e) => setLineCount(Number(e.target.value))}
            className="bg-gray-900 text-gray-300 text-[10px] rounded border border-gray-700 px-1.5 py-0.5"
          >
            {[25, 50, 100, 250, 500].map((n) => (
              <option key={n} value={n}>
                Last {n} lines
              </option>
            ))}
          </select>
          <button
            onClick={handleCopyAll}
            className="px-2 py-0.5 rounded text-[10px] bg-gray-700 text-gray-300 hover:bg-gray-600 transition-colors"
          >
            📋 Copy All
          </button>
          <button
            onClick={clearCurrentLog}
            className="px-2 py-0.5 rounded text-[10px] bg-red-700 text-white hover:bg-red-600 transition-colors"
          >
            ✕ Clear
          </button>
        </div>
      </div>

      {/* Log selector tabs */}
      <div className="flex flex-wrap gap-1">
        {LOG_NAMES.map((log) => {
          const meta = logs.find((l) => l.name === log.key)
          const isActive = activeLog === log.key
          return (
            <button
              key={log.key}
              onClick={() => setActiveLog(log.key)}
              className={`px-2 py-1 rounded text-[10px] font-medium transition-colors ${
                isActive
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-900 text-gray-400 hover:bg-gray-700 hover:text-gray-200'
              }`}
              title={meta ? `${formatBytes(meta.size_bytes)}` : 'unknown size'}
            >
              {log.label}
              {meta && meta.size_bytes > 0 && (
                <span className="ml-1 opacity-60">{formatBytes(meta.size_bytes)}</span>
              )}
            </button>
          )
        })}
      </div>

      {/* Log content */}
      <div className="bg-gray-950 rounded border border-gray-800 max-h-80 overflow-auto">
        {currentLines.length === 0 ? (
          <div className="p-3 text-gray-600 text-[10px]">No log entries yet</div>
        ) : (
          <div className="divide-y divide-gray-800/50">
            {currentLines.map((line, i) => (
              <div
                key={i}
                className="group flex items-start gap-1 px-2 py-0.5 hover:bg-gray-900 transition-colors"
              >
                <span className="text-gray-600 text-[9px] font-mono w-6 text-right flex-shrink-0 select-none">
                  {i + 1}
                </span>
                <pre className="flex-1 text-[10px] text-gray-300 font-mono whitespace-pre-wrap break-all">
                  {line}
                </pre>
                <button
                  onClick={() => handleCopyLine(line, i)}
                  className="opacity-0 group-hover:opacity-100 px-1 py-0.5 rounded text-[9px] bg-gray-800 text-gray-400 hover:bg-gray-700 hover:text-white transition-all flex-shrink-0"
                  title="Copy line"
                >
                  {copiedLine === i ? '✓' : '📋'}
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
