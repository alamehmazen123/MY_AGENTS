import { useState } from 'react'

export function useCell(name: string) {
  const [status, setStatus] = useState('idle')
  return { name, status, setStatus }
}
