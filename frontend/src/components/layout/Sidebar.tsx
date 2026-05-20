export function Sidebar() {
  return (
    <aside className="w-64 bg-[#202123] border-r border-gray-800 flex flex-col">
      <div className="p-3 border-b border-gray-800">
        <h1 className="text-lg font-bold text-white">my_agents PRIS</h1>
        <div className="text-xs text-gray-500 mt-1">v12.0</div>
      </div>
      <nav className="flex-1 p-2 space-y-1 overflow-auto">
        <div className="px-3 py-2 rounded-md hover:bg-gray-800 cursor-pointer text-sm text-gray-300 transition-colors">
          💬 Sessions
        </div>
        <div className="px-3 py-2 rounded-md hover:bg-gray-800 cursor-pointer text-sm text-gray-300 transition-colors">
          🛠 MCP Tools
        </div>
        <div className="px-3 py-2 rounded-md hover:bg-gray-800 cursor-pointer text-sm text-gray-300 transition-colors">
          ⚙️ Settings
        </div>
      </nav>
      <div className="p-3 border-t border-gray-800">
        <div className="text-xs text-gray-500">
          <div className="flex items-center gap-2 mb-1">
            <span className="w-2 h-2 rounded-full bg-green-500" />
            System Online
          </div>
        </div>
      </div>
    </aside>
  )
}
