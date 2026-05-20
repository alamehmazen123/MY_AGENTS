import { useRuntimeStore } from '../../stores/runtimeStore'

export function StatusBar() {
  const status = useRuntimeStore((s) => s.status)
  return (
    <footer className="h-8 bg-gray-950 border-t border-gray-700 flex items-center px-4 text-xs justify-between">
      <span>System: {status}</span>
      <span>PRIS v12.0</span>
    </footer>
  )
}
