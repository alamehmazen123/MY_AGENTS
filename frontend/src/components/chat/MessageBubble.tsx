import { useState } from 'react'
import { MarkdownView } from './MarkdownView'

export function MessageBubble({
  role,
  text,
  streaming,
  traceId,
}: {
  role: string
  text: string
  streaming?: boolean
  traceId?: string
}) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch {
      /* ignore */
    }
  }

  // System notices (stop/error banners) — compact gray pill.
  if (role === 'system') {
    return (
      <div className="flex justify-center group">
        <div className="relative max-w-[90%] px-3 py-1 pr-16 rounded-full text-[10px] bg-gray-200 text-gray-600 border border-gray-300">
          {text}
          <button
            onClick={handleCopy}
            className="absolute top-0.5 right-1 px-1.5 py-0.5 rounded text-[10px] bg-gray-300/80 text-gray-600 hover:bg-gray-700 hover:text-white transition-all"
            title="Copy"
          >
            {copied ? '✓' : '📋'}
          </button>
        </div>
      </div>
    )
  }

  // "Context" rows (e.g. Agent-A said:) — italic gray.
  if (role === 'context') {
    return (
      <div className="flex justify-start group">
        <div className="relative max-w-[90%] px-3 py-2 pr-8 rounded-lg text-xs bg-gray-100 text-gray-600 border border-gray-200 italic">
          {text}
          <button
            onClick={handleCopy}
            className="absolute top-1 right-1 px-1.5 py-0.5 rounded text-[10px] bg-gray-200/80 text-gray-600 hover:bg-gray-700 hover:text-white transition-all"
            title="Copy"
          >
            {copied ? '✓' : '📋'}
          </button>
        </div>
      </div>
    )
  }

  const isUser = role === 'user'

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} group`}>
      <div
        className={`relative max-w-[85%] px-3 py-2 pr-8 rounded-lg text-sm shadow-sm ${
          isUser
            ? 'bg-blue-600 text-white'
            : 'bg-white/95 text-gray-900 border border-gray-200'
        }`}
      >
        {/* Trace ID chip for agent messages */}
        {traceId && !isUser && (
          <div className="absolute top-1 left-1 px-1.5 py-0.5 rounded text-[9px] bg-purple-100 text-purple-700 border border-purple-200 font-mono" title="Request trace ID">
            {traceId}
          </div>
        )}

        {/* Always-visible copy button anchored inside the top-right corner so
            it can't be clipped and the user doesn't have to hover to find it. */}
        <button
          onClick={handleCopy}
          className={`absolute top-1 right-1 px-1.5 py-0.5 rounded text-[11px] leading-none transition-all ${
            isUser
              ? 'bg-blue-500/60 text-blue-50 hover:bg-blue-400 hover:text-white'
              : 'bg-gray-200/80 text-gray-600 hover:bg-gray-700 hover:text-white'
          }`}
          title={isUser ? 'Copy prompt' : 'Copy whole response'}
        >
          {copied ? '✓ Copied' : '📋 Copy'}
        </button>

        {/* User messages stay plain text (preserves their literal wording).
            Agent messages render as markdown so headings, bullets, and code
            blocks display properly — and each code block has its own copy. */}
        {isUser ? (
          <span className="whitespace-pre-wrap">{text}</span>
        ) : (
          <div className="leading-snug">
            <MarkdownView text={text} />
          </div>
        )}

        {streaming && (
          <span className="inline-block w-1.5 h-3.5 ml-1 bg-current animate-pulse align-middle" />
        )}
      </div>
    </div>
  )
}
