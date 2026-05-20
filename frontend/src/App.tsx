import { Sidebar } from './components/layout/Sidebar'
import { MainWorkspace } from './components/layout/MainWorkspace'
import { StatusBar } from './components/layout/StatusBar'
import { Observatory } from './components/layout/Observatory'

function App() {
  return (
    <div className="h-screen w-screen flex flex-col overflow-hidden">
      <div className="flex flex-1 overflow-hidden">
        <Sidebar />
        <MainWorkspace />
        <Observatory />
      </div>
      <StatusBar />
    </div>
  )
}

export default App
