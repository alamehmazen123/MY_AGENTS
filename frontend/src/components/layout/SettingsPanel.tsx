import { useEffect, useState } from 'react'
import { useSettingsStore, PRESETS, HIGH_RISK_MODELS, modelLabel, modelMeta } from '../../stores/settingsStore'
import type { PresetName } from '../../stores/settingsStore'

const PRESET_NAMES: PresetName[] = ['CHAT', 'REVIEWING', 'CODING', 'SUPER_CODING', 'EXECUTION', 'CUSTOM']

export function SettingsPanel() {
  const theme = useSettingsStore((s) => s.theme)
  const preset = useSettingsStore((s) => s.preset)
  const agentAModel = useSettingsStore((s) => s.agentAModel)
  const agentBModel = useSettingsStore((s) => s.agentBModel)
  const availableModels = useSettingsStore((s) => s.availableModels)
  const setTheme = useSettingsStore((s) => s.setTheme)
  const setPreset = useSettingsStore((s) => s.setPreset)
  const setAgentAModel = useSettingsStore((s) => s.setAgentAModel)
  const setAgentBModel = useSettingsStore((s) => s.setAgentBModel)
  const fetchModels = useSettingsStore((s) => s.fetchModels)
  const applyTheme = useSettingsStore((s) => s.applyTheme)

  const [coreInstructions, setCoreInstructions] = useState('')
  const [showCore, setShowCore] = useState(false)
  const [refreshing, setRefreshing] = useState(false)

  useEffect(() => {
    fetchModels()
    applyTheme()
    fetch('/api/core-instructions')
      .then((r) => r.json())
      .then((d) => setCoreInstructions(d.instructions || ''))
      .catch(() => {})
  }, [fetchModels, applyTheme])

  const handleModelAChange = (model: string) => {
    setAgentAModel(model)
  }

  const handleModelBChange = (model: string) => {
    setAgentBModel(model)
  }

  const handlePresetChange = (p: PresetName) => {
    setPreset(p)
  }

  const handleThemeChange = (t: 'system' | 'dark' | 'light') => {
    setTheme(t)
  }

  const handleRefresh = async () => {
    setRefreshing(true)
    await fetchModels()
    setTimeout(() => setRefreshing(false), 600)
  }

  const currentPresetInfo = PRESETS[preset]

  return (
    <div className="flex-1 overflow-auto p-2">
      <div className="mb-3">
        <h2 className="text-sm font-bold text-white">⚙️ Settings</h2>
        <p className="text-xs text-gray-400">Configure agents, presets, and UI behavior.</p>
      </div>

      <div className="space-y-4 p-2 bg-gray-800 rounded border border-gray-700">
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

        <div>
          <label className="text-xs text-gray-400 block mb-1">Preset Mode</label>
          <select
            aria-label="Preset mode"
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

        <div>
          <label className="text-xs text-gray-400 block mb-1">Agent-A Model (Reasoner)</label>
          <select
            aria-label="Agent-A model"
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

        <div>
          <label className="text-xs text-gray-400 block mb-1">Agent-B Model (Reviewer)</label>
          <select
            aria-label="Agent-B model"
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
    </div>
  )
}
