import { useState, useEffect } from 'react'

export function useHydration(key: string) {
  const [data, setData] = useState(null)
  useEffect(() => {
    fetch(`/api/hydrate?key=${key}`).then(r => r.json()).then(d => setData(d)).catch(() => {})
  }, [key])
  return data
}
