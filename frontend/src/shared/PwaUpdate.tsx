import { useEffect, useRef, useState } from 'react'

export default function PwaUpdate() {
  const [waiting, setWaiting] = useState(false)
  const [deferred, setDeferred] = useState(false)
  const update = useRef<((reload?: boolean) => Promise<void>) | null>(null)
  useEffect(() => {
    if (!import.meta.env.PROD) return
    let alive = true
    void import('virtual:pwa-register').then(({ registerSW }) => {
      if (!alive) return
      update.current = registerSW({ onNeedRefresh() { if (alive) setWaiting(true) } })
    })
    return () => { alive = false }
  }, [])
  return waiting ? <aside className="pwa-update" aria-label="Actualizacion disponible"><h2>{deferred ? 'Actualizacion pospuesta' : 'Hay una nueva version'}</h2>{!deferred ? <p>Actualizar recarga la pagina. Termina tu reserva antes de continuar.</p> : null}<div className="actions"><button onClick={() => void update.current?.(true)}>Actualizar ahora</button>{!deferred ? <button className="secondary" onClick={() => setDeferred(true)}>Mas tarde</button> : null}</div></aside> : null
}
