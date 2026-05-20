import { useState } from 'react'
import { MessageBubble } from './MessageBubble'
import { PromptBar } from '../input/PromptBar'

export function AgentPanel({ label }: { label: string }) {
  const [messages, setMessages] = useState<any[]>([])

  const send = (text: string) => {
    setMessages((m) => [...m, { role: 'user', text }])
    setTimeout(() => {
      setMessages((m) => [...m, { role: 'agent', text: `Response from ${label}` }])
    }, 200)
  }

  return (
    <div className="flex-1 flex flex-col bg-gray-800 rounded border border-gray-700">
      <div className="px-3 py-2 border-b border-gray-700 font-semibold text-sm">{label}</div>
      <div className="flex-1 overflow-auto p-3 space-y-2">
        {messages.map((msg, i) => (
          <MessageBubble key={i} role={msg.role} text={msg.text} />
        ))}
      </div>
      <PromptBar onSend={send} />
    </div>
  )
}
