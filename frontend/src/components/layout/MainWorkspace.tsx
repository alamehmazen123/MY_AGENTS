import { AgentPanel } from '../chat/AgentPanel'
import { PromptBar } from '../input/PromptBar'
import { useSessionStore } from '../../stores/sessionStore'

function shortArgs(args: any): string {
  if (!args || typeof args !== 'object') return ''
  // Compact preview of the most useful arg fields without flooding the row.
  const out: string[] = []
  for (const k of ['action', 'path', 'url', 'query', 'host', 'expression', 'value', 'from', 'to', 'command', 'city', 'timezone']) {
    if (args[k] !== undefined && args[k] !== null && args[k] !== '') {
      const v = typeof args[k] === 'string' ? args[k] : JSON.stringify(args[k])
      out.push(`${k}=${v.length > 60 ? v.slice(0, 60) + '…' : v}`)
    }
  }
  return out.join(' · ')
}

export function MainWorkspace() {
  const session = useSessionStore((s) => s.sessions.find((x) => x.id === s.activeSessionId))
  const winner = session?.winner
  const executionResult = session?.executionResult
  const unloadStatus = useSessionStore((s) => s.unloadStatus)
  const isGenerating = useSessionStore((s) => s.isGenerating)
  const reviseAgain = useSessionStore((s) => s.reviseAgain)

  const aHasResp = !!session?.agentA.messages.some((m) => m.role === 'agent')
  const bHasResp = !!session?.agentB.messages.some((m) => m.role === 'agent')
  const canRevise = (aHasResp || bHasResp) && !isGenerating

  return (
    <main className="flex-1 flex flex-col overflow-hidden">
      {/* Top action bar */}
      {(winner || canRevise || unloadStatus) && (
        <div className="px-3 py-2 bg-gray-800/80 border-b border-gray-700 flex items-center justify-between gap-3 flex-wrap">
          <div className="flex items-center gap-2 flex-wrap">
            {winner && (
              <span className="text-green-300 text-sm font-medium">⭐ Winner: Agent-{winner}</span>
            )}
            {canRevise && (
              <button
                onClick={reviseAgain}
                disabled={isGenerating}
                className="px-3 py-1 bg-indigo-600 hover:bg-indigo-500 disabled:bg-gray-600 text-white text-xs rounded font-medium transition-colors"
                title="Run another A→B round using the latest response as input"
              >
                🔄 Revise Again
              </button>
            )}
          </div>
          {unloadStatus && (
            <span className="text-gray-400 text-xs">
              {unloadStatus} {isGenerating && <span className="animate-pulse">⏳</span>}
            </span>
          )}
        </div>
      )}

      {/* Execution result — Claude-Code-style step list + summary */}
      {executionResult && (
        <div className="px-3 py-2 bg-blue-900/30 border-b border-blue-800 max-h-56 overflow-auto">
          <div className="text-blue-300 text-xs font-medium mb-1">
            ▶ Execution from Agent-{executionResult.agent} ({executionResult.steps.length} step{executionResult.steps.length === 1 ? '' : 's'})
          </div>
          {executionResult.steps.length > 0 && (
            <ol className="space-y-1 mb-2">
              {executionResult.steps.map((step, i) => (
                <li key={i} className="text-xs">
                  <div className={step.ok ? 'text-green-300' : 'text-red-300'}>
                    {step.ok ? '✅' : '❌'} <span className="font-mono">{step.tool}</span>
                    <span className="text-blue-300 ml-1">{shortArgs(step.args)}</span>
                  </div>
                  <div className="text-blue-200/80 font-mono text-[10px] pl-5 truncate" title={step.preview}>
                    → {step.preview}
                  </div>
                </li>
              ))}
            </ol>
          )}
          <div className="text-blue-100 text-xs font-medium border-t border-blue-800/60 pt-1">
            {executionResult.summary}
          </div>
        </div>
      )}

      <div className="flex-1 flex gap-2 p-2 overflow-hidden">
        <AgentPanel agent="A" label="Agent-A" role="Reasoner" />
        <AgentPanel agent="B" label="Agent-B" role="Reviewer" />
      </div>
      <PromptBar />
    </main>
  )
}
