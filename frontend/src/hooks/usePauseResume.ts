import { useState } from 'react'

export function usePauseResume() {
  const [paused, setPaused] = useState(false)
  return {
    paused,
    pause: () => setPaused(true),
    resume: () => setPaused(false),
    stop: () => setPaused(false),
  }
}
