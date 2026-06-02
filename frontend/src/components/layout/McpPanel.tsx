import { useState } from 'react'
import { useSettingsStore } from '../../stores/settingsStore'

const MCP_PRESETS = [
  { id: 'file_explorer', name: 'File Explorer', desc: 'Browse workspace files' },
  { id: 'code_analyzer', name: 'Code Analyzer', desc: 'Static analysis & linting' },
  { id: 'git_mcp', name: 'Git MCP', desc: 'Git operations & history' },
  { id: 'search_ripgrep', name: 'Search (ripgrep)', desc: 'Fast text search' },
  { id: 'python_exec', name: 'Python Exec', desc: 'Sandboxed Python execution' },
  { id: 'terminal_whitelist', name: 'Terminal', desc: 'Whitelisted shell commands' },
  { id: 'diff_engine', name: 'Diff Engine', desc: 'Compare & patch files' },
  { id: 'refactor_safe', name: 'Refactor Safe', desc: 'Safe code refactoring' },
  { id: 'doc_generator', name: 'Doc Generator', desc: 'Auto-generate documentation' },
  { id: 'dependency_inspector', name: 'Dependency Inspector', desc: 'Analyze dependencies' },
  { id: 'workspace_indexer', name: 'Workspace Indexer', desc: 'Index project symbols' },
  { id: 'health_monitor', name: 'Health Monitor', desc: 'System health checks' },
  { id: 'project_scaffold', name: 'Project Scaffold', desc: 'Generate project templates' },
  { id: 'rollback_manager', name: 'Rollback Manager', desc: 'Undo changes safely' },
  { id: 'web_fetch', name: 'Web Fetch', desc: 'Fetch a URL (news, docs, pages)' },
  { id: 'network_info', name: 'Network Info', desc: 'Local & public IP address' },
  { id: 'clock', name: 'Clock', desc: 'Date/time & timezones' },
  { id: 'calculator', name: 'Calculator', desc: 'Safe math evaluation' },
  { id: 'text_stats', name: 'Text Stats', desc: 'Word/line/char counts' },
  { id: 'memory', name: 'Memory', desc: 'Persistent key-value recall' },
  { id: 'sequential_thinking', name: 'Sequential Thinking', desc: 'Step-by-step reasoning log' },
  { id: 'sqlite_query', name: 'SQLite Query', desc: 'Read-only SQL on .db files' },
  { id: 'csv_json', name: 'CSV/JSON Reader', desc: 'Preview CSV & JSON files' },
  { id: 'http_request', name: 'HTTP Request', desc: 'Call any REST API' },
  { id: 'wikipedia', name: 'Wikipedia', desc: 'Search & summarize papers' },
  { id: 'weather', name: 'Weather', desc: 'Forecast by city (no key)' },
  { id: 'arxiv', name: 'arXiv', desc: 'Search research papers' },
  { id: 'ip_geolocation', name: 'IP Geolocation', desc: 'Locate an IP / your own' },
  { id: 'dns_lookup', name: 'DNS Lookup', desc: 'Resolve hostnames to IPs' },
  { id: 'html_to_markdown', name: 'HTML to Text', desc: 'Clean text from web/HTML' },
  { id: 'clipboard', name: 'Clipboard', desc: 'Read/write the clipboard' },
  { id: 'convert_units', name: 'Unit/Currency Convert', desc: 'Length, mass, temp, currency' },
  { id: 'pdf_extract', name: 'PDF Extract', desc: 'Extract text from PDFs' },
  { id: 'office_reader', name: 'Office Reader', desc: 'Read Word & Excel files' },
  { id: 'screenshot', name: 'Screenshot', desc: 'Capture the screen to PNG' },
  { id: 'process_monitor', name: 'Process Monitor', desc: 'CPU/RAM/disk & processes' },
  { id: 'qr_code', name: 'QR Code', desc: 'Generate QR (ASCII)' },
  { id: 'sympy_math', name: 'Symbolic Math', desc: 'Solve/simplify/calculus' },
].sort((a, b) => a.name.localeCompare(b.name))

export function McpPanel() {
  const mcpEnabled = useSettingsStore((s) => s.mcpEnabled)
  const setMcpEnabled = useSettingsStore((s) => s.setMcpEnabled)
  const [showGenerateMcp, setShowGenerateMcp] = useState(false)
  const [mcpDescription, setMcpDescription] = useState('')

  const enabledCount = MCP_PRESETS.filter((t) => mcpEnabled[t.id] !== false).length

  return (
    <div className="flex-1 overflow-auto p-2">
      <div className="flex items-center justify-between mb-3">
        <div>
          <h2 className="text-sm font-bold text-white">🛠 MCP</h2>
          <p className="text-xs text-gray-400">Browse and configure available MCP tools.</p>
        </div>
        <div className="text-xs text-gray-400">
          {enabledCount}/{MCP_PRESETS.length} active
        </div>
      </div>

      <button
        onClick={() => setShowGenerateMcp((v) => !v)}
        className="w-full px-3 py-2 rounded-md bg-purple-600 hover:bg-purple-500 text-white text-xs font-medium transition-colors mb-3"
      >
        ✨ Generate with AI
      </button>

      {showGenerateMcp && (
        <div className="space-y-1 p-2 bg-gray-800 rounded border border-gray-700 mb-4">
          <textarea
            className="w-full bg-gray-900 rounded px-2 py-1 text-xs text-gray-100 border border-gray-700 resize-none"
            rows={2}
            placeholder="Describe what this MCP should do..."
            value={mcpDescription}
            onChange={(e) => setMcpDescription(e.target.value)}
          />
          <div className="flex gap-1">
            <button
              onClick={() => {
                setMcpDescription('')
                setShowGenerateMcp(false)
              }}
              className="flex-1 px-2 py-1 bg-gray-700 hover:bg-gray-600 rounded text-xs text-gray-300"
            >
              Cancel
            </button>
            <button
              onClick={() => {
                alert(`Generate MCP: ${mcpDescription}`)
                setMcpDescription('')
                setShowGenerateMcp(false)
              }}
              className="flex-1 px-2 py-1 bg-green-600 hover:bg-green-500 rounded text-xs text-white"
            >
              Generate
            </button>
          </div>
        </div>
      )}

      <div className="border-t border-gray-800 pt-2 space-y-1">
        {MCP_PRESETS.map((tool) => (
          <div
            key={tool.id}
            className="group flex items-center justify-between px-2 py-1.5 rounded hover:bg-gray-800 transition-colors"
          >
            <div className="flex-1 min-w-0">
              <div className="text-sm text-gray-300 truncate">{tool.name}</div>
              <div className="text-[10px] text-gray-500 truncate">{tool.desc}</div>
            </div>
            <button
              onClick={() => setMcpEnabled(tool.id, mcpEnabled[tool.id] === false)}
              className={`ml-2 px-2 py-0.5 rounded text-[10px] font-medium transition-colors ${
                mcpEnabled[tool.id] !== false
                  ? 'bg-green-700 text-green-100 hover:bg-green-600'
                  : 'bg-gray-700 text-gray-400 hover:bg-gray-600'
              }`}
            >
              {mcpEnabled[tool.id] !== false ? 'ON' : 'OFF'}
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}
