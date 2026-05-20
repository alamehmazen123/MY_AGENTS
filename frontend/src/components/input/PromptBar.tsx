import { useState } from 'react'
import { useSessionStore } from '../../stores/sessionStore'

export function PromptBar() {
  const [text, setText] = useState('')
  const sendPrompt = useSessionStore((s) => s.sendPrompt)

  const handleSend = () => {
    if (!text.trim()) return
    sendPrompt(text)
    setText('')
  }

  return (
    <div className="p-3 border-t border-gray-700 bg-gray-800">
      <div className="flex items-center gap-2 mb-2">
        <button
          type="button"
          className="px-3 py-1 text-xs bg-gray-700 rounded hover:bg-gray-600 flex items-center gap-1 transition-colors"
        >
          📎 Attach
        </button>
        <button
          type="button"
          className="px-3 py-1 text-xs bg-gray-700 rounded hover:bg-gray-600 flex items-center gap-1 transition-colors"
        >
          📁 Folder
        </button>
      </div>
      <div className="flex gap-2">
        <textarea
          className="flex-1 bg-gray-900 rounded-lg px-4 py-3 text-sm resize-none border border-gray-700 focus:border-blue-500 focus:outline-none transition-colors"
          rows={2}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              handleSend()
            }
          }}
          placeholder="Type your prompt..."
        />
        <button
          type="button"
          onClick={handleSend}
          className="px-5 bg-blue-600 rounded-lg text-sm hover:bg-blue-500 font-medium transition-colors"
        >
          →
        </button>
      </div>
    </div>
  )
}
