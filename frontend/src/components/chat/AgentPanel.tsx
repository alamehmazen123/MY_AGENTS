import { useSessionStore } from '../../stores/sessionStore'
import { useSettingsStore } from '../../stores/settingsStore'
import { MessageBubble } from './MessageBubble'

export function AgentPanel({ agent, label, role }: { agent: 'A' | 'B'; label: string; role: string }) {
  const activeId = useSessionStore((s) => s.activeSessionId)
  const session = useSessionStore((s) => s.sessions.find((x) => x.id === activeId))
  const settingsModel = useSettingsStore((s) => (agent === 'A' ? s.agentAModel : s.agentBModel))

  const agentState = agent === 'A' ? session?.agentA : session?.agentB
  const messages = agentState?.messages ?? []
  const status = agentState?.status ?? 'online'
  const model = agentState?.model || settingsModel

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
          : 'bg-gray-400'

  return (
    <div className={`flex-1 flex flex-col rounded-lg border border-gray-200 overflow-hidden ${bgColor} ${textColor}`}>
      <div className={`px-3 py-2 border-b border-gray-200 flex items-center justify-between ${headerBg}`}>
        <div>
          <div className="font-bold text-sm">{label}</div>
          <div className="text-xs opacity-75">{role}</div>
        </div>
        <div className="text-right text-xs space-y-0.5">
          <div className="flex items-center gap-1 justify-end">
            <span className={`w-2 h-2 rounded-full ${statusColor} ${statusDot}`} />
            {status === 'online' ? 'Online' : status === 'waiting' ? 'Waiting' : status === 'working' ? 'Working' : status}
          </div>
          <div className="opacity-75">{model}</div>
        </div>
      </div>
      <div className="flex-1 overflow-auto p-3 space-y-2">
        {messages.length === 0 && (
          <div className="text-center text-sm opacity-50 mt-8">
            {agent === 'A' ? 'Waiting for input...' : 'Waiting for Agent-A...'}
          </div>
        )}
        {messages.map((msg) => (
          <MessageBubble key={msg.id} role={msg.role} text={msg.text} streaming={msg.streaming} />
        ))}
      </div>
    </div>
  )
}
