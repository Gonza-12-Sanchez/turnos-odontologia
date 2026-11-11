import { useRef, useState } from 'react'

type WriteState = 'idle' | 'pending' | 'uncertain'
export interface ConfigWriteGuard {
  state: WriteState
  begin: () => boolean
  finish: (uncertain: boolean) => void
}
// Owned by the account Layout, not a page: route changes must not unlock writes.
export function useConfigWriteGuard(): ConfigWriteGuard {
  const current = useRef<WriteState>('idle')
  const [state, setState] = useState<WriteState>('idle')
  return {
    state,
    begin() {
      if (current.current !== 'idle') return false
      current.current = 'pending'; setState('pending'); return true
    },
    finish(uncertain) {
      current.current = uncertain ? 'uncertain' : 'idle'
      setState(current.current)
    },
  }
}
