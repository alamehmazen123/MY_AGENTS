import { useUniverse } from '../../hooks/useUniverse'

export function Observatory() {
  const state = useUniverse()
  return (
    <aside className="w-56 bg-gray-800 border-l border-gray-700 p-4 text-xs overflow-auto">
      <h2 className="font-bold mb-2">Observatory</h2>
      <pre className="text-green-400">{JSON.stringify(state, null, 2)}</pre>
    </aside>
  )
}
