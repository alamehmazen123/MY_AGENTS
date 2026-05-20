import { useState } from 'react'

export function MessageBubble({ role, text, streaming }: { role: string; text: string; streaming?: boolean }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch {
      // ignore
    }
  }

  if (role === 'context') {
    return (
      <div className="flex justify-start">
        <div className="max-w-[90%] px-3 py-2 rounded-lg text-xs bg-gray-100 text-gray-600 border border-gray-200 italic">
          {text}
        </div>
      </div>
    )
  }

  const isUser = role === 'user'
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} group`}>
      <div
        className={`relative max-w-[80%] px-3 py-2 rounded-lg text-sm shadow-sm ${
          isUser
            ? 'bg-blue-600 text-white'
            : 'bg-white/90 text-gray-900 border border-gray-200'
        }`}
      >
        <button
          onClick={handleCopy}
          className={`absolute -top-2 ${isUser ? '-left-7' : '-right-7'} opacity-0 group-hover:opacity-100 transition-opacity p-1 rounded bg-gray-700 text-gray-300 hover:text-white text-xs`}
          title="Copy"
        >
          {copied ? '✓' : '📋'}
        </button>
        {text}
        {streaming && (
          <span className="inline-block w-1.5 h-3.5 ml-1 bg-current animate-pulse align-middle" />
        )}
      </div>
    </div>
  )
}
