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

function fileToBase64(file: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => {
      const result = String(reader.result || '')
      // Strip the "data:<mime>;base64," prefix the FileReader adds.
      const idx = result.indexOf(',')
      resolve(idx >= 0 ? result.slice(idx + 1) : result)
    }
    reader.onerror = () => reject(new Error('read_failed'))
    reader.readAsDataURL(file)
  })
}

// Upload a pasted blob to the backend; returns the absolute saved path so
// the agent can reference the file via file_explorer / pdf_extract / etc.
async function uploadPaste(blob: Blob, name: string): Promise<{ path: string; name: string; size: number } | null> {
  try {
    const data_base64 = await fileToBase64(blob)
    const res = await fetch('/api/upload-paste', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, mime: blob.type, data_base64 }),
    })
    const json = await res.json()
    if (json.error || !json.path) return null
    return { path: json.path, name: json.name, size: json.size }
  } catch {
    return null
  }
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

  // Capture clipboard pastes: screenshots, images, files. Plain text falls
  // through to the textarea's default paste behaviour.
  const handlePaste = async (e: React.ClipboardEvent<HTMLTextAreaElement>) => {
    const cd = e.clipboardData
    if (!cd) return

    // Collect everything pasteable: files first, then inline items.
    const blobs: { blob: Blob; name: string }[] = []
    for (const f of Array.from(cd.files || [])) {
      blobs.push({ blob: f, name: f.name || `paste_${Date.now()}` })
    }
    for (const item of Array.from(cd.items || [])) {
      if (item.kind === 'file') {
        const f = item.getAsFile()
        if (f && !blobs.some((b) => b.blob === f)) {
          const ext = (f.type.split('/')[1] || 'bin').split('+')[0]
          const fallback = `screenshot_${Date.now()}.${ext}`
          blobs.push({ blob: f, name: f.name || fallback })
        }
      }
    }
    if (blobs.length === 0) return  // nothing pasteable → let text paste happen
    e.preventDefault()

    const additions: AttachedFile[] = []
    for (const { blob, name } of blobs) {
      const isImage = blob.type.startsWith('image/')
      const saved = await uploadPaste(blob, name)
      if (saved) {
        const label = isImage
          ? `[Pasted image saved to ${saved.path} (${saved.size} bytes, ${blob.type}). ` +
            `Use file_explorer or other tools to reference it. ` +
            `Text-only models can't "see" image pixels; use a vision model for visual Q&A.]`
          : `[Pasted file saved to ${saved.path} (${saved.size} bytes, ${blob.type || 'unknown'})]`
        additions.push({ name: saved.name, content: label })
      } else if (!isImage) {
        // Fall back to reading the text directly for non-image pastes.
        try {
          const text = await blob.text()
          additions.push({ name, content: text })
        } catch {
          additions.push({ name, content: `[Could not read pasted ${name}]` })
        }
      } else {
        additions.push({ name, content: `[Failed to save pasted image ${name}]` })
      }
    }
    if (additions.length > 0) setAttachedFiles((prev) => [...prev, ...additions])
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
          onPaste={handlePaste}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              if (!isGenerating) handleSend()
            }
          }}
          placeholder={isGenerating ? 'Generating...' : 'Type your prompt — paste images/files with Ctrl+V or right-click → Paste'}
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
