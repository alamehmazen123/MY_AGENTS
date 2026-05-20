import { useSessionStore } from '../../stores/sessionStore'
import { useRuntimeStore } from '../../stores/runtimeStore'

export function StatusBar() {
  const status = useRuntimeStore((s) => s.status)
  const agentAStatus = useSessionStore((s) => s.agentA.status)
  const agentBStatus = useSessionStore((s) => s.agentB.status)

  const dotClass = (s: string, color: string) => {
    if (s === 'working') return `w-1.5 h-1.5 rounded-full ${color} animate-pulse`
    if (s === 'online') return `w-1.5 h-1.5 rounded-full bg-green-500`
    return `w-1.5 h-1.5 rounded-full bg-gray-500`
  }

  return (
    <footer className="h-8 bg-gray-950 border-t border-gray-800 flex items-center px-4 text-xs justify-between text-gray-400">
      <div className="flex items-center gap-4">
        <span className="flex items-center gap-1">
          <span className={status === 'online' ? 'w-1.5 h-1.5 rounded-full bg-green-500' : 'w-1.5 h-1.5 rounded-full bg-yellow-500'} />
          System: {status}
        </span>
        <span className="flex items-center gap-1">
          <span className={dotClass(agentAStatus, 'bg-purple-500')} />
          Agent-A: {agentAStatus}
        </span>
        <span className="flex items-center gap-1">
          <span className={dotClass(agentBStatus, 'bg-orange-500')} />
          Agent-B: {agentBStatus}
        </span>
      </div>
      <span>PRIS v12.0</span>
    </footer>
  )
}
