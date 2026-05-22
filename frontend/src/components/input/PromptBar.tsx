import { useRef, useState } from 'react'
import { useSessionStore } from '../../stores/sessionStore'
import type { AttachedFile } from '../../stores/sessionStore'

function readFileContent(file: File): Promise<string> {
  return new Promise((resolve) => {
    const binaryExts = ['.xlsx', '.xls', '.pdf', '.zip', '.tar', '.gz', '.rar', '.7z', '.exe', '.dll', '.so', '.dylib', '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.ico', '.mp3', '.mp4', '.avi', '.mov', '.wasm']
    const ext = file.name.slice(file.name.lastIndexOf('.')).toLowerCase()
    if (binaryExts.includes(ext)) {
      resolve(`[Binary file: ${file.name} — content not readable by text model]`)
      return
    }
    const reader = new FileReader()
    reader.onload = (e) => resolve(String(e.target?.result || ''))
    reader.onerror = () => resolve(`[Error: could not read ${file.name}]`)
    reader.readAsText(file)
  })
}

export function PromptBar() {
  const [text, setText] = useState('')
  const [attachedFiles, setAttachedFiles] = useState<AttachedFile[]>([])
  const [workspaceFolder, setWorkspaceFolder] = useState('')
  const [showFolderInput, setShowFolderInput] = useState(false)
  const [folderPath, setFolderPath] = useState('')
  const [pickingFolder, setPickingFolder] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const sendPrompt = useSessionStore((s) => s.sendPrompt)
  const abortGeneration = useSessionStore((s) => s.abortGeneration)
  const isGenerating = useSessionStore((s) => s.isGenerating)

  const handleSend = () => {
    if (!text.trim() && attachedFiles.length === 0) return
    sendPrompt(text, { files: attachedFiles, folder: workspaceFolder })
    setText('')
    setAttachedFiles([])
  }

  const handleStop = () => {
    abortGeneration()
  }

  const handleFiles = async (files: FileList | null) => {
    if (!files) return
    const newFiles: AttachedFile[] = []
    for (const file of Array.from(files)) {
      const content = await readFileContent(file)
      newFiles.push({ name: file.name, content })
    }
    setAttachedFiles((prev) => [...prev, ...newFiles])
  }

  const applyFolder = () => {
    if (folderPath.trim()) {
      setWorkspaceFolder(folderPath.trim())
    }
    setShowFolderInput(false)
    setFolderPath('')
  }

  const pickFolder = async () => {
    setPickingFolder(true)
    try {
      const res = await fetch('/api/pick-folder', { method: 'POST' })
      const data = await res.json()
      if (data.path) {
        setWorkspaceFolder(data.path)
        setShowFolderInput(false)
      } else if (data.error) {
        // Native dialog unavailable — fall back to manual entry.
        setShowFolderInput(true)
      }
    } catch {
      setShowFolderInput(true)
    } finally {
      setPickingFolder(false)
    }
  }

  return (
    <div className="p-3 border-t border-gray-700 bg-gray-800">
      {/* Attached file tags */}
      {attachedFiles.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-2">
          {attachedFiles.map((file, i) => (
            <span
              key={i}
              className="px-2 py-0.5 bg-blue-900/50 text-blue-300 text-xs rounded border border-blue-800 flex items-center gap-1"
            >
              📎 {file.name}
              <button
                onClick={() => setAttachedFiles((p) => p.filter((_, idx) => idx !== i))}
                className="text-blue-400 hover:text-white"
                title="Remove file"
              >
                ✕
              </button>
            </span>
          ))}
        </div>
      )}

      {/* Folder path input */}
      {showFolderInput && (
        <div className="flex items-center gap-2 mb-2">
          <input
            type="text"
            value={folderPath}
            onChange={(e) => setFolderPath(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') applyFolder() }}
            placeholder="C:\Users\... or /home/..."
            className="flex-1 bg-gray-900 rounded px-3 py-1.5 text-xs text-gray-100 border border-gray-700 focus:border-blue-500 focus:outline-none"
            autoFocus
          />
          <button
            onClick={applyFolder}
            className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 rounded text-xs text-white"
          >
            Set
          </button>
          <button
            onClick={() => { setShowFolderInput(false); setFolderPath('') }}
            className="px-3 py-1.5 bg-gray-700 hover:bg-gray-600 rounded text-xs text-gray-300"
          >
            Cancel
          </button>
        </div>
      )}

      <div className="flex items-center gap-2 mb-2">
        <button
          type="button"
          onClick={pickFolder}
          disabled={pickingFolder}
          className="px-3 py-1 text-xs bg-gray-700 rounded hover:bg-gray-600 flex items-center gap-1 transition-colors disabled:opacity-60"
          title="Choose a workspace folder"
        >
          📁 {pickingFolder ? 'Opening…' : 'Folder'}
        </button>
        {workspaceFolder && (
          <span className="flex items-center gap-1 text-xs font-medium text-red-500 truncate max-w-[60%]" title={workspaceFolder}>
            <span className="truncate">{workspaceFolder}</span>
            <button
              onClick={() => setWorkspaceFolder('')}
              className="text-red-400 hover:text-red-300 flex-shrink-0"
              title="Remove workspace"
            >
              ✕
            </button>
          </span>
        )}
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          className="px-3 py-1 text-xs bg-gray-700 rounded hover:bg-gray-600 flex items-center gap-1 transition-colors"
        >
          📎 Attach
        </button>
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
              if (!isGenerating) handleSend()
            }
          }}
          placeholder={isGenerating ? 'Generating...' : 'Type your prompt...'}
        />
        <button
          type="button"
          onClick={isGenerating ? handleStop : handleSend}
          disabled={!isGenerating && !text.trim() && attachedFiles.length === 0}
          className={`px-5 rounded-lg text-sm font-medium transition-colors ${
            isGenerating
              ? 'bg-red-600 hover:bg-red-500 text-white'
              : 'bg-blue-600 hover:bg-blue-500 text-white disabled:bg-gray-700 disabled:text-gray-500'
          }`}
          title={isGenerating ? 'Stop generation' : 'Send prompt'}
        >
          {isGenerating ? '⏹' : '→'}
        </button>
      </div>
    </div>
  )
}
