import { useEffect } from 'react'
import { Sidebar } from './components/layout/Sidebar'
import { MainWorkspace } from './components/layout/MainWorkspace'
import { StatusBar } from './components/layout/StatusBar'
import { useSettingsStore } from './stores/settingsStore'

function App() {
  const applyTheme = useSettingsStore((s) => s.applyTheme)

  useEffect(() => {
    applyTheme()
    // Re-apply when system preference changes
    const mq = window.matchMedia('(prefers-color-scheme: dark)')
    const handler = () => applyTheme()
    mq.addEventListener('change', handler)
    return () => mq.removeEventListener('change', handler)
  }, [applyTheme])

  return (
    <div className="h-screen w-screen flex flex-col overflow-hidden bg-gray-900 text-gray-100">
      <div className="flex flex-1 overflow-hidden">
        <Sidebar />
        <MainWorkspace />
      </div>
      <StatusBar />
    </div>
  )
}

export default App
