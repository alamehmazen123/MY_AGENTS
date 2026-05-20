import { Sidebar } from './components/layout/Sidebar'
import { MainWorkspace } from './components/layout/MainWorkspace'
import { StatusBar } from './components/layout/StatusBar'

function App() {
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
