import { AgentPanel } from '../chat/AgentPanel'
import { PromptBar } from '../input/PromptBar'

export function MainWorkspace() {
  return (
    <main className="flex-1 flex flex-col overflow-hidden">
      <div className="flex-1 flex gap-2 p-2 overflow-hidden">
        <AgentPanel agent="A" label="Agent-A" role="Reasoner" />
        <AgentPanel agent="B" label="Agent-B" role="Reviewer" />
      </div>
      <PromptBar />
    </main>
  )
}
