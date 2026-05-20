export function MessageBubble({ role, text, streaming }: { role: string; text: string; streaming?: boolean }) {
  const isUser = role === 'user'
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[80%] px-3 py-2 rounded-lg text-sm shadow-sm ${
          isUser
            ? 'bg-blue-600 text-white'
            : 'bg-white/90 text-gray-900 border border-gray-200'
        }`}
      >
        {text}
        {streaming && (
          <span className="inline-block w-1.5 h-3.5 ml-1 bg-current animate-pulse align-middle" />
        )}
      </div>
    </div>
  )
}
