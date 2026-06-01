import { useSessionStore } from '../../stores/sessionStore'
import { useSettingsStore } from '../../stores/settingsStore'
import { MessageBubble } from './MessageBubble'

export function AgentPanel({ agent, label, role }: { agent: 'A' | 'B'; label: string; role: string }) {
  const activeId = useSessionStore((s) => s.activeSessionId)
  const session = useSessionStore((s) => s.sessions.find((x) => x.id === activeId))
  const settingsModel = useSettingsStore((s) => (agent === 'A' ? s.agentAModel : s.agentBModel))
  const executeAgent = useSessionStore((s) => s.executeAgent)
  const isGenerating = useSessionStore((s) => s.isGenerating)

  const agentState = agent === 'A' ? session?.agentA : session?.agentB
  const messages = agentState?.messages ?? []
  const status = agentState?.status ?? 'online'
  const model = agentState?.model || settingsModel
  const hasAgentResponse = messages.some((m) => m.role === 'agent')

  const bgColor = agent === 'A' ? 'bg-purple-50' : 'bg-orange-50'
  const textColor = agent === 'A' ? 'text-purple-900' : 'text-orange-900'
  const headerBg = agent === 'A' ? 'bg-purple-100' : 'bg-orange-100'

  const statusDot = status === 'working' ? 'animate-pulse' : ''
  const statusColor =
    status === 'working'
      ? 'bg-blue-500'
      : status === 'waiting'
        ? 'bg-yellow-500'
        : status === 'online'
          ? 'bg-green-500'
          : status === 'disabled'
            ? 'bg-gray-600'
            : 'bg-gray-400'

  const statusLabel =
    status === 'online'
      ? 'Online'
      : status === 'waiting'
        ? 'Waiting'
        : status === 'working'
          ? 'Working'
          : status === 'disabled'
            ? 'Disabled'
            : status

  return (
    <div className={`flex-1 flex flex-col rounded-lg border overflow-hidden ${bgColor} ${textColor} border-gray-200`}>
      <div className={`px-3 py-2 border-b border-gray-200 flex items-center justify-between ${headerBg}`}>
        <div>
          <div className="font-bold text-sm">{label}</div>
          <div className="text-xs opacity-75">{role}</div>
        </div>
        <div className="text-right text-xs space-y-0.5">
          <div className="flex items-center gap-1 justify-end">
            <span className={`w-2 h-2 rounded-full ${statusColor} ${statusDot}`} />
            {statusLabel}
          </div>
          <div className="opacity-75">{model || '—'}</div>
        </div>
      </div>
      <div className="flex-1 overflow-auto p-3 space-y-2">
        {messages.length === 0 && (
          <div className="text-center text-sm opacity-50 mt-8">
            {status === 'disabled'
              ? 'Disabled in current preset'
              : agent === 'A'
                ? 'Waiting for input...'
                : 'Waiting for Agent-A...'}
          </div>
        )}
        {messages.map((msg) => (
          <MessageBubble key={msg.id} role={msg.role} text={msg.text} streaming={msg.streaming} traceId={msg.traceId} />
        ))}
        {hasAgentResponse && !isGenerating && (
          <div className="flex justify-center pt-2">
            <button
              onClick={() => executeAgent(agent)}
              className="px-3 py-1.5 rounded text-xs font-medium bg-blue-600 text-white hover:bg-blue-500 transition-colors"
              title="Generate executable tool calls and run them to fulfil the original request"
            >
              ▶ Execute Plan
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
