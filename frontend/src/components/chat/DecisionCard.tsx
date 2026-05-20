export function DecisionCard({ onAccept, onRepeat, onDiscard }: any) {
  return (
    <div className="flex gap-2 my-2">
      <button onClick={onAccept} className="px-3 py-1 bg-green-700 rounded text-xs hover:bg-green-600">Accept</button>
      <button onClick={onRepeat} className="px-3 py-1 bg-yellow-700 rounded text-xs hover:bg-yellow-600">Repeat</button>
      <button onClick={onDiscard} className="px-3 py-1 bg-red-700 rounded text-xs hover:bg-red-600">Discard</button>
    </div>
  )
}
