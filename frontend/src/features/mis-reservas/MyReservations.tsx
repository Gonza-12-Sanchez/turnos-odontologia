import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { useSession } from '../auth/context'
import type { Reservation } from '../../shared/api/contracts'
import { ApiError } from '../../shared/api/client'
import { Notice } from '../../shared/ui'
import { errorMessage, useOnline } from '../../shared/network'
import { dateTime } from '../../shared/time'

export default function MyReservations() {
  const { session, user } = useSession()
  const online = useOnline()
  const [result, setResult] = useState<{ key: string; rows: Reservation[] } | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [cancel, setCancel] = useState<string | null>(null)
  const [reload, setReload] = useState(0)
  const writing = useRef(false)
  const loadKey = `${user?.id}:${reload}`
  const rows = result?.key === loadKey ? result.rows : null
  useEffect(() => {
    if (!online) return
    const controller = new AbortController()
    session.get<Reservation[]>('/mis-reservas', { signal: controller.signal }).then(result => {
      if (!controller.signal.aborted) setResult({ key: loadKey, rows: result.toSorted((a, b) => Date.parse(a.inicio) - Date.parse(b.inicio)) })
    }).catch(e => { if (!controller.signal.aborted) setError(errorMessage(e)) })
    return () => controller.abort()
  }, [session, online, loadKey])
  async function action(id: string, name: 'confirmar' | 'cancelar') {
    if (!online || writing.current) return
    writing.current = true; setBusy(true); setError(''); setCancel(null)
    try {
      await session.patch(`/turnos/${id}/${name}`, undefined)
      setReload(n => n + 1)
    } catch (e) {
      setError(e instanceof ApiError && e.status === 422 ? 'El servidor rechazo la accion. Para cancelar se exige un minimo de 2 horas antes del turno. Contacta al consultorio.' : errorMessage(e))
      if (e instanceof ApiError) setReload(n => n + 1)
    } finally { writing.current = false; setBusy(false) }
  }
  return <section><h1>Mis reservas</h1><p>Los permisos se verifican nuevamente al confirmar o cancelar.</p>
    {error ? <Notice>{error}</Notice> : null}
    {online && rows === null && !error ? <p role="status">Cargando reservas...</p> : null}
    {online && rows?.length === 0 ? <p>Todavia no tenes reservas. <Link to="/horarios">Buscar un horario</Link></p> : null}
    {online && rows ? <ol className="reservations">{rows.map(row => <li key={row.id}>
      <div className="reservation-heading"><h2>{row.tratamiento_nombre}</h2><span className="state">{row.estado}</span></div>
      <p><time dateTime={row.inicio}>{dateTime(row.inicio)}</time>. {row.sillon_nombre}</p><p className="muted">Tolerancia de llegada: {row.tolerancia_min} min.</p>
      <div className="actions">
        {row.acciones.confirmar ? <button disabled={busy} onClick={() => void action(row.id, 'confirmar')}>Confirmar turno</button> : null}
        {row.acciones.cancelar ? <button className="secondary" disabled={busy} onClick={() => setCancel(row.id)}>Cancelar turno</button> : <p>Cancelacion no disponible. Se exige un minimo de 2 horas y un estado que permita cancelar.</p>}
      </div>
      {cancel === row.id ? <section className="cancel-confirm" aria-label="Confirmar cancelacion"><p>Vas a liberar este horario. Queres cancelar el turno?</p><div className="actions"><button disabled={busy} onClick={() => void action(row.id, 'cancelar')}>Si, cancelar turno</button><button className="secondary" onClick={() => setCancel(null)}>Conservar turno</button></div></section> : null}
    </li>)}</ol> : null}
    <button className="secondary" disabled={!online || busy} onClick={() => { setError(''); setReload(n => n + 1) }}>Actualizar reservas</button>
  </section>
}
