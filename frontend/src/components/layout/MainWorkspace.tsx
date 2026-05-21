import { AgentPanel } from '../chat/AgentPanel'
import { PromptBar } from '../input/PromptBar'
import { useSessionStore } from '../../stores/sessionStore'

export function MainWorkspace() {
  const session = useSessionStore((s) => s.sessions.find((x) => x.id === s.activeSessionId))
  const winner = session?.winner
  const executionResult = session?.executionResult
  const unloadStatus = useSessionStore((s) => s.unloadStatus)
  const isGenerating = useSessionStore((s) => s.isGenerating)
  const executeWinner = useSessionStore((s) => s.executeWinner)

  return (
    <main className="flex-1 flex flex-col overflow-hidden">
      {/* Winner banner */}
      {winner && (
        <div className="px-3 py-2 bg-green-900/80 border-b border-green-700 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-green-300 text-sm font-medium">⭐ Winner: Agent-{winner}</span>
            <button
              onClick={executeWinner}
              disabled={isGenerating}
              className="px-3 py-1 bg-green-600 hover:bg-green-500 disabled:bg-gray-600 text-white text-xs rounded font-medium transition-colors"
            >
              {isGenerating ? 'Executing...' : '▶ Execute Winner Plan'}
            </button>
          </div>
          {unloadStatus && (
            <span className="text-green-400 text-xs">{unloadStatus}</span>
          )}
        </div>
      )}

      {/* Unload status (when no winner yet) */}
      {!winner && unloadStatus && (
        <div className="px-3 py-1.5 bg-gray-800 border-b border-gray-700 text-gray-400 text-xs flex items-center justify-between">
          <span>{unloadStatus}</span>
          {isGenerating && <span className="animate-pulse">⏳ Working...</span>}
        </div>
      )}

      {/* Execution result */}
      {executionResult && (
        <div className="px-3 py-2 bg-blue-900/30 border-b border-blue-800 max-h-40 overflow-auto">
          <div className="text-blue-300 text-xs font-medium mb-1">Execution Result:</div>
          <pre className="text-blue-200 text-xs whitespace-pre-wrap">{executionResult}</pre>
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
