export function AttachmentButton({ onAttach }: { onAttach: (f: File) => void }) {
  return (
    <label className="cursor-pointer px-2 py-1 bg-gray-800 rounded border border-gray-700 text-xs hover:bg-gray-700">
      + Attach
      <input
        type="file"
        className="hidden"
        onChange={(e) => e.target.files?.[0] && onAttach(e.target.files[0])}
      />
    </label>
  )
}
