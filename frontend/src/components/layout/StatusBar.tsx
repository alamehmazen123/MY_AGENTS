import { useSessionStore } from '../../stores/sessionStore'

export function StatusBar() {
  const activeId = useSessionStore((s) => s.activeSessionId)
  const session = useSessionStore((s) => s.sessions.find((x) => x.id === activeId))

  const agentAStatus = session?.agentA.status ?? 'online'
  const agentBStatus = session?.agentB.status ?? 'waiting'

  const dotClass = (s: string, color: string) => {
    if (s === 'working') return `w-1.5 h-1.5 rounded-full ${color} animate-pulse`
    if (s === 'waiting') return `w-1.5 h-1.5 rounded-full bg-yellow-500`
    if (s === 'online') return `w-1.5 h-1.5 rounded-full bg-green-500`
    return `w-1.5 h-1.5 rounded-full bg-gray-500`
  }

  const label = (s: string) => {
    if (s === 'working') return 'Working'
    if (s === 'waiting') return 'Waiting'
    if (s === 'online') return 'Online'
    return s
  }

  return (
    <footer className="h-8 bg-gray-950 border-t border-gray-800 flex items-center px-4 text-xs justify-between text-gray-400">
      <div className="flex items-center gap-4">
        <span className="flex items-center gap-1">
          <span className="w-1.5 h-1.5 rounded-full bg-green-500" />
          System: Online
        </span>
        <span className="flex items-center gap-1">
          <span className={dotClass(agentAStatus, 'bg-purple-500')} />
          Agent-A: {label(agentAStatus)}
        </span>
        <span className="flex items-center gap-1">
          <span className={dotClass(agentBStatus, 'bg-orange-500')} />
          Agent-B: {label(agentBStatus)}
        </span>
      </div>
      <span>PRIS v12.0</span>
    </footer>
  )
}
