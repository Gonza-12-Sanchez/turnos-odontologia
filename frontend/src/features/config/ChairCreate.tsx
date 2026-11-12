import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { useSession } from '../auth/context'
import { ApiError } from '../../shared/api/client'
import { Notice } from '../../shared/ui'
import { isChair, readClinicContext } from './contracts'
import type { Clinic } from './contracts'
import type { ConfigWriteGuard } from './writeGuard'

export default function ChairCreate({ writes, onSaved, onCancel }: {
  writes: ConfigWriteGuard
  onSaved: () => void
  onCancel: () => void
}) {
  const { session } = useSession()
  const [clinic, setClinic] = useState<Clinic | null | undefined>(undefined)
  const [name, setName] = useState('')
  const [error, setError] = useState('')
  const [revision, setRevision] = useState(0)
  const mounted = useRef(false)
  useEffect(() => {
    mounted.current = true
    return () => { mounted.current = false }
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    void session.get<unknown>('/api/config/contexto-consultorio', { signal: controller.signal })
      .then(readClinicContext)
      .then(value => { if (!controller.signal.aborted) setClinic(value) })
      .catch(() => {
        if (!controller.signal.aborted) {
          setClinic(null)
          setError('No se pudo consultar el consultorio.')
        }
      })
    return () => controller.abort()
  }, [session, revision])

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const nombre = name.trim()
    if (!clinic || !nombre || nombre.length > 80 || !writes.begin()) return
    setError('')
    try {
      const result = await session.post<unknown>('/api/config/sillones', {
        consultorio_id: clinic.id, nombre, activo: true,
      }, { expectedStatus: 201, signal: AbortSignal.timeout(15000) })
      if (!isChair(result) || result.consultorio_id !== clinic.id || result.nombre !== nombre || !result.activo) {
        throw new Error('Respuesta no verificada')
      }
      writes.finish(!mounted.current)
      if (mounted.current) onSaved()
    } catch (cause) {
      if (cause instanceof ApiError && [401, 403, 404, 422].includes(cause.status)) {
        writes.finish(!mounted.current)
        if (!mounted.current) return
        setClinic(null)
        setError('El servidor rechazó el alta. Volvé a consultar el consultorio.')
      } else {
        writes.finish(true)
        if (mounted.current) setError('No se pudo verificar el alta. Consultá la lista antes de repetirla.')
      }
    }
  }

  return <form noValidate aria-label="Agregar sillón" onSubmit={event => void save(event)}>
    <h2>Agregar sillón</h2>
    {error ? <Notice>{error}</Notice> : null}
    {clinic === undefined ? <p role="status">Consultando el consultorio…</p> : null}
    {clinic === null && !error ? <Notice>Para dar de alta un sillón debe haber un único consultorio activo.</Notice> : null}
    {clinic === null ? <button type="button" className="secondary" onClick={() => {
      setError('')
      setClinic(undefined)
      setRevision(value => value + 1)
    }}>Reconsultar consultorio</button> : null}
    {clinic ? <>
      <p>Consultorio: {clinic.nombre}</p>
      <label>Nombre<input value={name} onChange={event => setName(event.target.value)} maxLength={80} required disabled={writes.state !== 'idle'} /></label>
      <button disabled={writes.state !== 'idle' || !name.trim()}>Crear sillón</button>
    </> : null}
    <button type="button" className="secondary" disabled={writes.state === 'pending'} onClick={onCancel}>Volver a la lista</button>
  </form>
}
