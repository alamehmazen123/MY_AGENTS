export function ReasoningPhases({ phases }: { phases: string[] }) {
  return (
    <div className="flex gap-1 text-[10px] text-gray-400 my-1">
      {phases.map((p, i) => (
        <span key={i} className="px-1.5 py-0.5 bg-gray-800 rounded border border-gray-700">
          {p}
        </span>
      ))}
    </div>
  )
}
