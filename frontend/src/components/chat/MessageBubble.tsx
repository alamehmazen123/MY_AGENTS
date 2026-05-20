export function MessageBubble({ role, text }: { role: string; text: string }) {
  const isUser = role === 'user'
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[80%] px-3 py-2 rounded-lg text-sm ${
          isUser ? 'bg-blue-600 text-white' : 'bg-gray-700 text-gray-100'
        }`}
      >
        {text}
      </div>
    </div>
  )
}
