export function Sidebar() {
  return (
    <aside className="w-64 bg-gray-800 border-r border-gray-700 flex flex-col p-4">
      <h1 className="text-lg font-bold mb-4">my_agents PRIS</h1>
      <nav className="space-y-2">
        <div className="px-2 py-1 rounded hover:bg-gray-700 cursor-pointer">Sessions</div>
        <div className="px-2 py-1 rounded hover:bg-gray-700 cursor-pointer">MCP Tools</div>
        <div className="px-2 py-1 rounded hover:bg-gray-700 cursor-pointer">Settings</div>
      </nav>
    </aside>
  )
}
