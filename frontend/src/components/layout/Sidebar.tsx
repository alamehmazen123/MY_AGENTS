import { useState, useEffect } from 'react'
import { useSessionStore } from '../../stores/sessionStore'
import { useSettingsStore, PRESETS, HIGH_RISK_MODELS, modelLabel, modelMeta } from '../../stores/settingsStore'
import type { PresetName } from '../../stores/settingsStore'

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
  { id: 'wikipedia', name: 'Wikipedia', desc: 'Search & summarize articles' },
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

const PRESET_NAMES: PresetName[] = ['CHAT', 'REVIEWING', 'CODING', 'SUPER_CODING', 'EXECUTION', 'CUSTOM']

export function Sidebar() {
  const sessions = useSessionStore((s) => s.sessions)
  const activeId = useSessionStore((s) => s.activeSessionId)
  const createSession = useSessionStore((s) => s.createSession)
  const switchSession = useSessionStore((s) => s.switchSession)
  const deleteSession = useSessionStore((s) => s.deleteSession)
  const renameSession = useSessionStore((s) => s.renameSession)
  const togglePin = useSessionStore((s) => s.togglePin)
  const updateSessionModels = useSessionStore((s) => s.updateSessionModels)

  const theme = useSettingsStore((s) => s.theme)
  const preset = useSettingsStore((s) => s.preset)
  const agentAModel = useSettingsStore((s) => s.agentAModel)
  const agentBModel = useSettingsStore((s) => s.agentBModel)
  const availableModels = useSettingsStore((s) => s.availableModels)
  const mcpEnabled = useSettingsStore((s) => s.mcpEnabled)
  const setTheme = useSettingsStore((s) => s.setTheme)
  const setPreset = useSettingsStore((s) => s.setPreset)
  const setAgentAModel = useSettingsStore((s) => s.setAgentAModel)
  const setAgentBModel = useSettingsStore((s) => s.setAgentBModel)
  const setMcpEnabled = useSettingsStore((s) => s.setMcpEnabled)
  const fetchModels = useSettingsStore((s) => s.fetchModels)
  const applyTheme = useSettingsStore((s) => s.applyTheme)

  const [activeTab, setActiveTab] = useState<'sessions' | 'mcp' | 'settings'>('sessions')
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editName, setEditName] = useState('')
  const [coreInstructions, setCoreInstructions] = useState('')
  const [showCore, setShowCore] = useState(false)
  const [showGenerateMcp, setShowGenerateMcp] = useState(false)
  const [mcpDescription, setMcpDescription] = useState('')
  const [refreshing, setRefreshing] = useState(false)

  useEffect(() => {
    fetchModels()
    applyTheme()
    fetch('/api/core-instructions')
      .then((r) => r.json())
      .then((d) => setCoreInstructions(d.instructions || ''))
      .catch(() => {})
  }, [fetchModels, applyTheme])

  // Tools default to ON unless explicitly disabled (undefined => active).
  const enabledCount = MCP_PRESETS.filter((t) => mcpEnabled[t.id] !== false).length

  const handleModelAChange = (model: string) => {
    setAgentAModel(model)
    updateSessionModels()
  }

  const handleModelBChange = (model: string) => {
    setAgentBModel(model)
    updateSessionModels()
  }

  const handleThemeChange = (t: 'system' | 'dark' | 'light') => {
    setTheme(t)
  }

  const handlePresetChange = (p: PresetName) => {
    setPreset(p)
    updateSessionModels()
  }

  const handleRefresh = async () => {
    setRefreshing(true)
    await fetchModels()
    setTimeout(() => setRefreshing(false), 600)
  }

  const currentPresetInfo = PRESETS[preset]

  return (
    <aside className="w-64 bg-[#202123] border-r border-gray-800 flex flex-col">
      <div className="p-3 border-b border-gray-800">
        <h1 className="text-lg font-bold text-white">my_agents PRIS</h1>
        <div className="text-xs text-gray-500 mt-1">v12.0</div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-gray-800">
        {(['sessions', 'mcp', 'settings'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`flex-1 py-2 text-xs font-medium capitalize transition-colors ${
              activeTab === tab
                ? 'text-white border-b-2 border-blue-500 bg-gray-800'
                : 'text-gray-500 hover:text-gray-300'
            }`}
          >
            {tab === 'sessions' ? '💬 Sessions' : tab === 'mcp' ? '🛠 MCP' : '⚙️ Settings'}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="flex-1 overflow-auto p-2">
        {/* ── SESSIONS TAB ── */}
        {activeTab === 'sessions' && (
          <div className="space-y-1">
            <button
              onClick={createSession}
              className="w-full px-3 py-2 rounded-md bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium transition-colors mb-2"
            >
              + New Session
            </button>
            {[...sessions]
              .sort((a, b) => Number(!!b.pinned) - Number(!!a.pinned) || a.createdAt - b.createdAt)
              .map((sess) => (
              <div
                key={sess.id}
                onClick={() => switchSession(sess.id)}
                className={`group flex items-center justify-between px-2 py-2 rounded-md cursor-pointer text-sm transition-colors ${
                  sess.id === activeId
                    ? 'bg-gray-700 text-white'
                    : 'text-gray-300 hover:bg-gray-800 hover:text-white'
                }`}
              >
                {editingId === sess.id ? (
                  <input
                    autoFocus
                    value={editName}
                    onClick={(e) => e.stopPropagation()}
                    onChange={(e) => setEditName(e.target.value)}
                    onBlur={() => { renameSession(sess.id, editName); setEditingId(null) }}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') { renameSession(sess.id, editName); setEditingId(null) }
                      if (e.key === 'Escape') setEditingId(null)
                    }}
                    className="flex-1 min-w-0 bg-gray-900 text-white text-sm rounded px-1.5 py-0.5 border border-blue-500 focus:outline-none"
                  />
                ) : (
                  <span
                    className="truncate flex-1 flex items-center gap-1"
                    onDoubleClick={(e) => { e.stopPropagation(); setEditingId(sess.id); setEditName(sess.name) }}
                    title="Double-click to rename"
                  >
                    {sess.pinned && <span className="text-yellow-400 flex-shrink-0">📌</span>}
                    <span className="truncate">{sess.name}</span>
                  </span>
                )}
                <div className="flex items-center gap-0.5 flex-shrink-0 ml-1">
                  <button
                    onClick={(e) => { e.stopPropagation(); togglePin(sess.id) }}
                    className={`text-xs px-1 transition-opacity ${sess.pinned ? 'text-yellow-400' : 'opacity-0 group-hover:opacity-100 text-gray-500 hover:text-yellow-400'}`}
                    title={sess.pinned ? 'Unpin' : 'Pin'}
                  >
                    {sess.pinned ? '★' : '☆'}
                  </button>
                  <button
                    onClick={(e) => { e.stopPropagation(); setEditingId(sess.id); setEditName(sess.name) }}
                    className="opacity-0 group-hover:opacity-100 text-gray-500 hover:text-blue-400 text-xs px-1 transition-opacity"
                    title="Rename session"
                  >
                    ✎
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      if (sessions.length > 1) deleteSession(sess.id)
                    }}
                    className="opacity-0 group-hover:opacity-100 text-gray-500 hover:text-red-400 text-xs px-1 transition-opacity"
                    title="Delete session"
                  >
                    ✕
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* ── MCP TAB ── */}
        {activeTab === 'mcp' && (
          <div className="space-y-2">
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs text-gray-500">{enabledCount}/{MCP_PRESETS.length} active</span>
            </div>

            <button
              onClick={() => setShowGenerateMcp(!showGenerateMcp)}
              className="w-full px-3 py-2 rounded-md bg-purple-600 hover:bg-purple-500 text-white text-xs font-medium transition-colors"
            >
              ✨ Generate with AI
            </button>

            {showGenerateMcp && (
              <div className="space-y-1 p-2 bg-gray-800 rounded border border-gray-700">
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
        )}

        {/* ── SETTINGS TAB ── */}
        {activeTab === 'settings' && (
          <div className="space-y-4 p-2">
            {/* Core Instructions — applied to every agent & preset */}
            {coreInstructions && (
              <div className="rounded border border-purple-800 bg-purple-900/20">
                <button
                  onClick={() => setShowCore((v) => !v)}
                  className="w-full flex items-center justify-between px-2 py-1.5 text-left"
                  title="These instructions are prepended to every agent on every prompt"
                >
                  <span className="text-xs font-medium text-purple-300">
                    📜 Core Instructions <span className="text-green-400">• always active</span>
                  </span>
                  <span className="text-purple-400 text-xs">{showCore ? '▲' : '▼'}</span>
                </button>
                {showCore && (
                  <pre className="max-h-60 overflow-auto px-2 pb-2 text-[10px] leading-snug text-gray-300 whitespace-pre-wrap">
                    {coreInstructions}
                  </pre>
                )}
              </div>
            )}

            {/* Preset */}
            <div>
              <label className="text-xs text-gray-400 block mb-1">Preset Mode</label>
              <select
                value={preset}
                onChange={(e) => handlePresetChange(e.target.value as PresetName)}
                className="w-full bg-gray-800 text-gray-100 text-sm rounded border border-gray-700 px-2 py-1.5 focus:border-blue-500 focus:outline-none"
              >
                {PRESET_NAMES.map((p) => (
                  <option key={p} value={p}>
                    {p === 'SUPER_CODING' ? 'SUPER-CODING' : p}
                  </option>
                ))}
              </select>
              <p className="text-[10px] text-gray-500 mt-1 leading-tight">
                {currentPresetInfo.description}
              </p>
              {preset !== 'CUSTOM' && (
                <div className="mt-1 text-[10px] text-gray-600">
                  A: {currentPresetInfo.agentA.name} (temp {currentPresetInfo.agentA.temperature})<br />
                  B: {currentPresetInfo.agentB?.name || 'DISABLED'}
                  {currentPresetInfo.mcpToolsEnabled && (
                    <span className="text-green-600 ml-1">• MCP ON</span>
                  )}
                </div>
              )}
            </div>

            {/* Agent-A Model */}
            <div>
              <label className="text-xs text-gray-400 block mb-1">Agent-A Model (Reasoner)</label>
              <select
                value={agentAModel}
                onChange={(e) => handleModelAChange(e.target.value)}
                className="w-full bg-gray-800 text-gray-100 text-sm rounded border border-gray-700 px-2 py-1.5 focus:border-blue-500 focus:outline-none"
              >
                {availableModels.map((m) => (
                  <option key={m} value={m}>{modelLabel(m)}</option>
                ))}
              </select>
              <span className="text-[10px] text-gray-500 mt-0.5 block">
                {modelMeta(agentAModel).tier} — {modelMeta(agentAModel).note}
              </span>
              {HIGH_RISK_MODELS.includes(agentAModel) && (
                <span className="text-[10px] text-red-400 mt-0.5 block font-medium">⚠️ HIGH RISK — slow on CPU</span>
              )}
            </div>

            {/* Agent-B Model */}
            <div>
              <label className="text-xs text-gray-400 block mb-1">Agent-B Model (Reviewer)</label>
              <select
                value={agentBModel}
                onChange={(e) => handleModelBChange(e.target.value)}
                className="w-full bg-gray-800 text-gray-100 text-sm rounded border border-gray-700 px-2 py-1.5 focus:border-blue-500 focus:outline-none"
              >
                <option value="">DISABLED</option>
                {availableModels.map((m) => (
                  <option key={m} value={m}>{modelLabel(m)}</option>
                ))}
              </select>
              {agentBModel && (
                <span className="text-[10px] text-gray-500 mt-0.5 block">
                  {modelMeta(agentBModel).tier} — {modelMeta(agentBModel).note}
                </span>
              )}
              {agentBModel && HIGH_RISK_MODELS.includes(agentBModel) && (
                <span className="text-[10px] text-red-400 mt-0.5 block font-medium">⚠️ HIGH RISK — slow on CPU</span>
              )}
            </div>

            {/* Theme */}
            <div>
              <label className="text-xs text-gray-400 block mb-1">Theme</label>
              <div className="flex gap-1">
                {(['system', 'dark', 'light'] as const).map((t) => (
                  <button
                    key={t}
                    onClick={() => handleThemeChange(t)}
                    className={`flex-1 px-2 py-1 rounded text-xs capitalize transition-colors ${
                      theme === t
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
                    }`}
                  >
                    {t}
                  </button>
                ))}
              </div>
            </div>

            <div className="border-t border-gray-800 pt-2">
              <button
                onClick={handleRefresh}
                disabled={refreshing}
                className="w-full px-3 py-1.5 rounded bg-gray-800 hover:bg-gray-700 text-gray-400 text-xs transition-colors disabled:opacity-50"
              >
                {refreshing ? '🔄 Refreshing...' : '🔄 Refresh Model List'}
              </button>
            </div>
          </div>
        )}
      </div>

      <div className="p-3 border-t border-gray-800">
        <div className="text-xs text-gray-500">
          <div className="flex items-center gap-2 mb-1">
            <span className="w-2 h-2 rounded-full bg-green-500" />
            System Online
          </div>
          <div className="text-gray-600">{sessions.length} session(s)</div>
        </div>
      </div>
    </aside>
  )
}
