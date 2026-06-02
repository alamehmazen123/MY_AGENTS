import { useState } from 'react'
import { useSessionStore } from '../../stores/sessionStore'

export function Sidebar() {
  const sessions = useSessionStore((s) => s.sessions)
  const activeId = useSessionStore((s) => s.activeSessionId)
  const createSession = useSessionStore((s) => s.createSession)
  const switchSession = useSessionStore((s) => s.switchSession)
  const deleteSession = useSessionStore((s) => s.deleteSession)
  const renameSession = useSessionStore((s) => s.renameSession)
  const togglePin = useSessionStore((s) => s.togglePin)

  const [editingId, setEditingId] = useState<string | null>(null)
  const [editName, setEditName] = useState('')

  return (
    <aside className="w-64 bg-[#202123] border-r border-gray-800 flex flex-col">
      <div className="p-3 border-b border-gray-800">
        <h1 className="text-lg font-bold text-white">my_agents PRIS</h1>
        <div className="text-xs text-gray-500 mt-1">v12.0</div>
      </div>

      <div className="flex-1 overflow-auto p-2">
        <div className="space-y-1">
          <button
            onClick={createSession}
            className="w-full px-3 py-2 rounded-md bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium transition-colors mb-2"
          >
            + New Session
          </button>

          {(() => {
            const lastActivity = (sess: typeof sessions[number]) => {
              let mx = sess.createdAt
              for (const m of sess.agentA.messages) if (m.timestamp > mx) mx = m.timestamp
              for (const m of sess.agentB.messages) if (m.timestamp > mx) mx = m.timestamp
              return mx
            }

            const sortByRecent = (a: typeof sessions[number], b: typeof sessions[number]) =>
              lastActivity(b) - lastActivity(a)

            const pinned = sessions.filter((s) => s.pinned).sort(sortByRecent)
            const recent = sessions.filter((s) => !s.pinned).sort(sortByRecent)

            const renderRow = (sess: typeof sessions[number]) => (
              <div
                key={sess.id}
                onClick={() => switchSession(sess.id)}
                className={`group flex items-center justify-between px-2 py-2 rounded-md cursor-pointer text-sm transition-colors ${
                  sess.id === activeId
                    ? 'bg-gray-700 text-white'
                    : 'text-gray-300 hover:bg-gray-800 hover:text-white'
                }`}
              >
                {editingId === sess.id ? (
                  <input
                    aria-label="Edit session name"
                    autoFocus
                    value={editName}
                    onClick={(e) => e.stopPropagation()}
                    onChange={(e) => setEditName(e.target.value)}
                    onBlur={() => { renameSession(sess.id, editName); setEditingId(null) }}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') { renameSession(sess.id, editName); setEditingId(null) }
                      if (e.key === 'Escape') setEditingId(null)
                    }}
                    className="flex-1 min-w-0 bg-gray-900 text-white text-sm rounded px-1.5 py-0.5 border border-blue-500 focus:outline-none"
                  />
                ) : (
                  <span
                    className="truncate flex-1 flex items-center gap-1"
                    onDoubleClick={(e) => { e.stopPropagation(); setEditingId(sess.id); setEditName(sess.name) }}
                    title="Double-click to rename"
                  >
                    {sess.pinned && <span className="text-yellow-400 flex-shrink-0">📌</span>}
                    <span className="truncate">{sess.name}</span>
                  </span>
                )}
                <div className="flex items-center gap-0.5 flex-shrink-0 ml-1">
                  <button
                    onClick={(e) => { e.stopPropagation(); togglePin(sess.id) }}
                    className={`text-xs px-1 transition-opacity ${sess.pinned ? 'text-yellow-400' : 'opacity-0 group-hover:opacity-100 text-gray-500 hover:text-yellow-400'}`}
                    title={sess.pinned ? 'Unpin' : 'Pin'}
                  >
                    {sess.pinned ? '★' : '☆'}
                  </button>
                  <button
                    onClick={(e) => { e.stopPropagation(); setEditingId(sess.id); setEditName(sess.name) }}
                    className="opacity-0 group-hover:opacity-100 text-gray-500 hover:text-blue-400 text-xs px-1 transition-opacity"
                    title="Rename session"
                  >
                    ✎
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      if (sessions.length > 1) deleteSession(sess.id)
                    }}
                    className="opacity-0 group-hover:opacity-100 text-gray-500 hover:text-red-400 text-xs px-1 transition-opacity"
                    title="Delete session"
                  >
                    ✕
                  </button>
                </div>
              </div>
            )

            return (
              <>
                {pinned.length > 0 && (
                  <>
                    <div className="text-[10px] uppercase tracking-wider text-yellow-500/80 px-2 pt-1 pb-0.5">
                      📌 Pinned
                    </div>
                    {pinned.map(renderRow)}
                    {recent.length > 0 && <div className="border-t border-gray-800 my-2" />}
                  </>
                )}
                {recent.length > 0 && (
                  <>
                    <div className="text-[10px] uppercase tracking-wider text-gray-500 px-2 pt-1 pb-0.5">
                      Recent
                    </div>
                    {recent.map(renderRow)}
                  </>
                )}
              </>
            )
          })()}
        </div>
      </div>

      <div className="p-3 border-t border-gray-800">
        <div className="text-xs text-gray-500">
          <div className="flex items-center gap-2 mb-1">
            <span className="w-2 h-2 rounded-full bg-green-500" />
            System Online
          </div>
          <div className="text-gray-600">{sessions.length} session(s)</div>
        </div>
      </div>
    </aside>
  )
}
