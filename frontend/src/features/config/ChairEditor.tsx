import { useEffect, useRef, useState } from 'react'
import { useSession } from '../auth/context'
import { Notice } from '../../shared/ui'
import { isChair } from './contracts'
import type { Chair } from './contracts'
import type { ConfigWriteGuard } from './writeGuard'
import { ApiError } from '../../shared/api/client'
import { isRecord } from '../../shared/api/contracts'

export default function ChairEditor({ item, writes, onSaved, onCancel }: { item: Chair; writes: ConfigWriteGuard; onSaved: (item: Chair) => void; onCancel: () => void }) {
  const { session } = useSession()
  const [name, setName] = useState(item.nombre)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [confirmActivity, setConfirmActivity] = useState(false)
  const [nameInvalid, setNameInvalid] = useState(false)
  const [unavailable, setUnavailable] = useState(false)
  const mounted = useRef(true)
  useEffect(() => { mounted.current = true; return () => { mounted.current = false } }, [])
  const locked = writes.state !== 'idle' || unavailable
  async function save(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (busy || locked) return
    const value = name.trim()
    if (!value || value.length > 80) { setError('El nombre debe tener entre 1 y 80 caracteres.'); return }
    if (value === item.nombre) { setError('No hay cambios para guardar.'); return }
    await update({ nombre: value })
  }
  async function update(patch: { nombre?: string; activo?: boolean }) {
    if (busy || locked || !writes.begin()) return
    setBusy(true); setError(''); setNameInvalid(false)
    try {
      const result = await session.patch<unknown>(`/api/config/sillones/${item.id}`, patch, { expectedStatus: 200, signal: AbortSignal.timeout(15000) })
      if (!isChair(result) || result.id !== item.id || result.consultorio_id !== item.consultorio_id || result.nombre !== (patch.nombre ?? item.nombre) || result.activo !== (patch.activo ?? item.activo)) throw new Error('Respuesta no verificada')
      writes.finish(!mounted.current)
      if (mounted.current) onSaved(result)
    } catch (cause) {
      if (cause instanceof ApiError && [403, 404, 422].includes(cause.status)) {
        writes.finish(!mounted.current)
        if (!mounted.current) return
        if (cause.status === 422) {
          const detail = isRecord(cause.body) ? cause.body.detail : undefined
          setNameInvalid(Array.isArray(detail) && detail.some(entry => isRecord(entry) && Array.isArray(entry.loc) && entry.loc[0] === 'body' && entry.loc[1] === 'nombre'))
          setError('Revisa los datos. El servidor rechazó los cambios del sillón.')
        } else {
          setUnavailable(true)
          setError(cause.status === 404 ? 'El sillón ya no está disponible para tu cuenta. Reconsulta la lista antes de modificarlo.' : 'Tu cuenta no tiene permiso para modificar este sillón. Reconsulta la lista.')
        }
        return
      }
      writes.finish(true)
      if (mounted.current) setError('Resultado no verificado. No repitas la escritura; consulta el recurso y solicita conciliación.')
    } finally { if (mounted.current) setBusy(false) }
  }
  if (confirmActivity) return <form noValidate aria-label={`${item.activo ? 'Desactivar' : 'Reactivar'} ${item.nombre}`} onSubmit={event => { event.preventDefault(); void update({ activo: !item.activo }) }}>
    <h2>{item.activo ? 'Desactivar sillón' : 'Reactivar sillón'}</h2><p>{item.nombre}</p>
    {item.activo ? <Notice>Los históricos se conservan. Se dejará de ofrecer disponibilidad para este sillón. Los turnos existentes no se borran ni se cancelan automáticamente.</Notice> : <p>Volverá a estar activo y podrá participar en las consultas de disponibilidad. Se conservan sus turnos históricos.</p>}
    {error ? <Notice>{error}</Notice> : null}
    <div className="actions"><button className={item.activo ? 'danger' : undefined} disabled={busy || locked}>{busy ? 'Guardando…' : item.activo ? 'Desactivar sillón' : 'Reactivar sillón'}</button><button type="button" className="secondary" autoFocus disabled={busy} onClick={() => { setConfirmActivity(false); setError('') }}>{item.activo ? 'Conservar activo' : 'Volver'}</button></div>
  </form>
  return <form noValidate aria-label={`Editar ${item.nombre}`} onSubmit={event => void save(event)}>
    <h2>Editar sillón</h2>
    <label>Nombre<input value={name} onChange={event => setName(event.target.value)} maxLength={80} disabled={busy || locked} aria-invalid={nameInvalid || undefined} aria-describedby={nameInvalid ? 'chair-name-error' : undefined} /></label>
    {nameInvalid ? <small id="chair-name-error">Revisa el nombre indicado.</small> : null}
    <p>La sede no se cambia desde este formulario. Los turnos históricos se conservan.</p>
    {error ? <Notice>{error}</Notice> : null}
    <div className="actions"><button disabled={busy || locked}>{busy ? 'Guardando…' : 'Guardar cambios'}</button><button type="button" className="secondary" disabled={busy} onClick={onCancel}>Volver a la lista</button></div>
    <button type="button" className={item.activo ? 'danger' : 'secondary'} disabled={busy || locked} onClick={() => { setError(''); setConfirmActivity(true) }}>{item.activo ? 'Desactivar sillón' : 'Reactivar sillón'}</button>
  </form>
}
