export function PauseOverlay({ onResume, onStop }: any) {
  return (
    <div className="absolute inset-0 bg-black/60 flex items-center justify-center gap-4 z-10">
      <button onClick={onResume} className="px-4 py-2 bg-blue-600 rounded">Resume</button>
      <button onClick={onStop} className="px-4 py-2 bg-red-600 rounded">Stop</button>
    </div>
  )
}
