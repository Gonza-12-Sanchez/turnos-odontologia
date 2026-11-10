import { useEffect, useState } from 'react'
import { createApiClient } from '../../shared/api/client'
import { Session } from './session'
import { isRecord } from '../../shared/api/contracts'
import { SessionContext } from './context'

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [session] = useState(() => new Session(createApiClient(import.meta.env.VITE_API_URL ?? 'http://localhost:8000')))
  useEffect(() => { void session.restore() }, [session])
  useEffect(() => {
    if (typeof BroadcastChannel === 'undefined') return
    const channel = new BroadcastChannel('turnos-session')
    let previous = session.snapshot().user?.id
    let remote = false
    const unsubscribe = session.subscribe(() => {
      const next = session.snapshot().user?.id
      if (next !== previous && !remote) channel.postMessage({ type: 'identity', subject: next ?? null })
      previous = next
    })
    channel.onmessage = event => {
      if (!isRecord(event.data) || event.data.type !== 'identity' || event.data.subject === session.snapshot().user?.id) return
      remote = true
      session.clear('La sesion cambio en otra pestana. Ingresa nuevamente.')
      remote = false
    }
    return () => { unsubscribe(); channel.close() }
  }, [session])
  return <SessionContext.Provider value={session}>{children}</SessionContext.Provider>
}
