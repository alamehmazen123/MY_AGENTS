import { useState } from 'react'

export function useAttachment() {
  const [files, setFiles] = useState<File[]>([])
  return {
    files,
    add: (f: File) => setFiles((prev) => [...prev, f]),
    clear: () => setFiles([]),
  }
}
