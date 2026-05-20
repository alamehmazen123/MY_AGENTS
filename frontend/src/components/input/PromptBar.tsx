import { useRef, useState } from 'react'
import { useSessionStore } from '../../stores/sessionStore'

export function PromptBar() {
  const [text, setText] = useState('')
  const [attachedFiles, setAttachedFiles] = useState<string[]>([])
  const fileInputRef = useRef<HTMLInputElement>(null)
  const folderInputRef = useRef<HTMLInputElement>(null)
  const sendPrompt = useSessionStore((s) => s.sendPrompt)

  const handleSend = () => {
    if (!text.trim() && attachedFiles.length === 0) return
    const fullPrompt = attachedFiles.length > 0
      ? `[Attached: ${attachedFiles.join(', ')}]\n${text}`
      : text
    sendPrompt(fullPrompt)
    setText('')
    setAttachedFiles([])
  }

  const handleFiles = (files: FileList | null) => {
    if (!files) return
    const names = Array.from(files).map((f) => f.name)
    setAttachedFiles((prev) => [...prev, ...names])
  }

  return (
    <div className="p-3 border-t border-gray-700 bg-gray-800">
      {attachedFiles.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-2">
          {attachedFiles.map((name, i) => (
            <span
              key={i}
              className="px-2 py-0.5 bg-blue-900/50 text-blue-300 text-xs rounded border border-blue-800 flex items-center gap-1"
            >
              📎 {name}
              <button
                onClick={() => setAttachedFiles((p) => p.filter((_, idx) => idx !== i))}
                className="text-blue-400 hover:text-white"
              >
                ✕
              </button>
            </span>
          ))}
        </div>
      )}

      <div className="flex items-center gap-2 mb-2">
        <button
          type="button"
          onClick={() => folderInputRef.current?.click()}
          className="px-3 py-1 text-xs bg-gray-700 rounded hover:bg-gray-600 flex items-center gap-1 transition-colors"
        >
          📁 Folder
        </button>
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          className="px-3 py-1 text-xs bg-gray-700 rounded hover:bg-gray-600 flex items-center gap-1 transition-colors"
        >
          📎 Attach
        </button>
        <input
          ref={folderInputRef}
          type="file"
          {...{ webkitdirectory: '', directory: '' } as any}
          multiple
          className="hidden"
          onChange={(e) => handleFiles(e.target.files)}
        />
        <input
          ref={fileInputRef}
          type="file"
          multiple
          className="hidden"
          onChange={(e) => handleFiles(e.target.files)}
        />
      </div>

      <div className="flex gap-2">
        <textarea
          className="flex-1 bg-gray-900 rounded-lg px-4 py-3 text-sm resize-none border border-gray-700 focus:border-blue-500 focus:outline-none transition-colors text-gray-100"
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
          disabled={!text.trim() && attachedFiles.length === 0}
          className="px-5 bg-blue-600 rounded-lg text-sm hover:bg-blue-500 disabled:bg-gray-700 disabled:text-gray-500 font-medium transition-colors"
        >
          →
        </button>
      </div>
    </div>
  )
}
