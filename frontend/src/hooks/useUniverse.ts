import { useEffect, useState } from 'react'

export function useUniverse() {
  const [state, setState] = useState({})
  useEffect(() => {
    const id = setInterval(() => {
      fetch('/api/health').then(r => r.json()).then(d => setState(d)).catch(() => {})
    }, 2000)
    return () => clearInterval(id)
  }, [])
  return state
}
