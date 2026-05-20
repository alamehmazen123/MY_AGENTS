import { useState } from 'react'

export function PromptBar({ onSend }: { onSend: (text: string) => void }) {
  const [text, setText] = useState('')
  return (
    <div className="p-2 border-t border-gray-700 flex gap-2">
      <textarea
        className="flex-1 bg-gray-900 rounded px-3 py-2 text-sm resize-none"
        rows={2}
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault()
            onSend(text)
            setText('')
          }
        }}
        placeholder="Type prompt..."
      />
      <button
        onClick={() => { onSend(text); setText('') }}
        className="px-4 bg-blue-600 rounded text-sm hover:bg-blue-500"
      >
        Send
      </button>
    </div>
  )
}
