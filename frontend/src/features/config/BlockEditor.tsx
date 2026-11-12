import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { useSession } from '../auth/context'
import { ApiError } from '../../shared/api/client'
import { isRecord } from '../../shared/api/contracts'
import { argentinaDate, hour } from '../../shared/time'
import { Notice } from '../../shared/ui'
import { isBlock } from './contracts'
import type { Block } from './contracts'
import type { ConfigWriteGuard } from './writeGuard'

function localInput(instant: string) {
  return argentinaDate(new Date(instant)) + 'T' + hour(instant)
}

function awareTime(value: string) {
  const instant = new Date(value + ':00-03:00')
  if (!Number.isFinite(instant.getTime())) return null
  return localInput(instant.toISOString()) === value ? instant.toISOString() : null
}

export default function BlockEditor({ item, writes, onSaved, onCancel }: {
  item: Block | null
  writes: ConfigWriteGuard
  onSaved: (warning: string) => void
  onCancel: () => void
}) {
  const { session } = useSession()
  const [start, setStart] = useState(item ? localInput(item.desde) : '')
  const [end, setEnd] = useState(item ? localInput(item.hasta) : '')
  const [reason, setReason] = useState(item?.motivo ?? '')
  const [chair, setChair] = useState(item?.sillon_id ?? '')
  const [chairs, setChairs] = useState<{ id: string; nombre: string }[]>([])
  const [chairError, setChairError] = useState(false)
  const [error, setError] = useState('')
  const mounted = useRef(false)
  useEffect(() => {
    mounted.current = true
    const controller = new AbortController()
    void session.get<unknown>('/catalogo-publico', { signal: controller.signal }).then(value => {
      if (!isRecord(value) || !Array.isArray(value.sillones)) throw new Error('Catálogo inválido')
      const rows = value.sillones.filter((row): row is { id: string; nombre: string } =>
        isRecord(row) && typeof row.id === 'string' && typeof row.nombre === 'string')
      if (!controller.signal.aborted) setChairs(rows)
    }).catch(() => { if (!controller.signal.aborted) setChairError(true) })
    return () => { mounted.current = false; controller.abort() }
  }, [session])

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const desde = awareTime(start)
    const hasta = awareTime(end)
    const motivo = reason.trim()
    if (!desde || !hasta || Date.parse(hasta) <= Date.parse(desde) || !motivo) {
      setError('Ingresá un motivo y un rango válido en horario argentino.')
      return
    }
    const patch: { desde?: string; hasta?: string; motivo?: string; sillon_id?: string | null } = {}
    if (!item || start !== localInput(item.desde)) patch.desde = desde
    if (!item || end !== localInput(item.hasta)) patch.hasta = hasta
    if (motivo !== item?.motivo) patch.motivo = motivo
    if (!item || chair !== (item.sillon_id ?? '')) patch.sillon_id = chair || null
    if (!Object.keys(patch).length) { setError('No hay cambios para guardar.'); return }
    if (!writes.begin()) return
    setError('')
    try {
      const signal = AbortSignal.timeout(15000)
      const value = item
        ? await session.patch<unknown>('/api/config/bloqueos/' + item.id, patch, { expectedStatus: 200, signal })
        : await session.post<unknown>('/api/config/bloqueos', patch, { expectedStatus: 201, signal })
      if (!isBlock(value) || (item && value.id !== item.id) || value.motivo !== motivo
        || value.sillon_id !== (chair || null)
        || localInput(value.desde) !== start || localInput(value.hasta) !== end
        || !isRecord(value) || !Array.isArray(value.warnings)) throw new Error('Respuesta no verificada')
      const overlap = value.warnings.find(row => isRecord(row) && row.code === 'TURNOS_SOLAPADOS'
        && typeof row.cantidad === 'number' && Number.isSafeInteger(row.cantidad) && row.cantidad > 0)
      writes.finish(!mounted.current)
      if (mounted.current) onSaved(overlap ? 'El bloqueo se guardó. Hay turnos solapados y se conservaron.' : '')
    } catch (cause) {
      const rejected = cause instanceof ApiError && [400, 401, 403, 404, 409, 422].includes(cause.status)
      writes.finish(!rejected || !mounted.current)
      if (mounted.current) setError(rejected ? 'El servidor rechazó el bloqueo. Revisá el rango y el sillón.' : 'El resultado quedó sin verificar. Consultá la lista antes de volver a guardar.')
    }
  }

  return <form noValidate aria-label={item ? 'Editar bloqueo' : 'Agregar bloqueo'} onSubmit={event => void save(event)}>
    <h2>{item ? 'Editar bloqueo' : 'Agregar bloqueo'}</h2>
    <fieldset disabled={writes.state !== 'idle'}>
      <legend>Horario argentino</legend>
      <label>Desde<input type="datetime-local" value={start} onChange={event => setStart(event.target.value)} required /></label>
      <label>Hasta<input type="datetime-local" value={end} onChange={event => setEnd(event.target.value)} required /></label>
      <label>Motivo<input value={reason} onChange={event => setReason(event.target.value)} maxLength={120} required /></label>
      <label>Alcance<select value={chair} onChange={event => setChair(event.target.value)}>
        <option value="">Todos los sillones</option>
        {item?.sillon_id && !chairs.some(row => row.id === item.sillon_id) ? <option value={item.sillon_id}>Sillón actual</option> : null}
        {chairs.map(row => <option key={row.id} value={row.id}>{row.nombre}</option>)}
      </select></label>
      {chairError ? <Notice>No se pudo cargar la lista de sillones.</Notice> : null}
      <button>Guardar bloqueo</button>
    </fieldset>
    {error ? <Notice>{error}</Notice> : null}
    <button type="button" className="secondary" disabled={writes.state === 'pending'} onClick={onCancel}>Volver a la lista</button>
  </form>
}
