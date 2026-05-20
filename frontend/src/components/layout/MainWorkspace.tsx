import { AgentPanel } from '../chat/AgentPanel'

export function MainWorkspace() {
  return (
    <main className="flex-1 flex gap-2 p-2 overflow-hidden">
      <AgentPanel label="Agent-A" />
      <AgentPanel label="Agent-B" />
    </main>
  )
}
