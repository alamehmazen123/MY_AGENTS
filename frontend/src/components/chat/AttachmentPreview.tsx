export function AttachmentPreview({ name }: { name: string }) {
  return (
    <div className="inline-flex items-center gap-1 px-2 py-1 bg-gray-800 rounded border border-gray-700 text-xs">
      <span>📎</span>
      <span className="truncate max-w-[120px]">{name}</span>
    </div>
  )
}
