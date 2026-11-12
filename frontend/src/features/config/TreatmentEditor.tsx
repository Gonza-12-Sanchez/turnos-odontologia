import { useEffect, useRef, useState } from 'react'
import { useSession } from '../auth/context'
import { Notice } from '../../shared/ui'
import { isTreatment } from './contracts'
import type { Treatment } from './contracts'
import { ApiError } from '../../shared/api/client'
import { isRecord } from '../../shared/api/contracts'
import type { ConfigWriteGuard } from './writeGuard'

function priceText(cents: number | null) {
  if (cents === null) return ''
  const value = BigInt(cents)
  return `${value / 100n},${String(value % 100n).padStart(2, '0')}`
}
function parsePrice(text: string): number | null {
  const value = text.trim()
  if (!value) return null
  if (!/^\d{1,8}(?:[,.]\d{1,2})?$/.test(value)) throw new Error('Ingresa un precio en ARS con hasta dos decimales, sin separador de miles.')
  const [whole, fraction = ''] = value.split(/[,.]/)
  const cents = BigInt(whole) * 100n + BigInt(fraction.padEnd(2, '0'))
  if (cents > 2147483647n) throw new Error('El precio máximo es 21474836,47 ARS.')
  return Number(cents)
}
export default function TreatmentEditor({ item, onSaved, onCancel, writes }: { item: Treatment | null; onSaved: (item: Treatment) => void; onCancel: () => void; writes: ConfigWriteGuard }) {
  const { session } = useSession()
  const [name, setName] = useState(item?.nombre ?? '')
  const [price, setPrice] = useState(() => priceText(item?.precio_referencia_centavos ?? null))
  const [policy, setPolicy] = useState<Treatment['sena_politica']>(item?.sena_politica ?? 'deshabilitada')
  const [deposit, setDeposit] = useState(() => priceText(item?.sena_centavos ?? null))
  const [duration, setDuration] = useState(item ? String(item.duracion_min) : '')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const mounted = useRef(true)
  useEffect(() => { mounted.current = true; return () => { mounted.current = false } }, [])
  const locked = writes.state !== 'idle'
  const [fields, setFields] = useState<{ nombre?: boolean; duracion_min?: boolean; precio_referencia_centavos?: boolean }>({})
  async function save(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (busy || locked) return
    const trimmedName = name.trim()
    if (!trimmedName || trimmedName.length > 120) { setError('El nombre debe tener entre 1 y 120 caracteres.'); return }
    let cents: number | null
    try { cents = parsePrice(price) } catch (cause) { setError(cause instanceof Error ? cause.message : 'Revisa el precio.'); return }
    if (!/^\d{1,10}$/.test(duration) || BigInt(duration) < 1n || BigInt(duration) > 2147483647n) { setError('La duración debe ser un entero entre 1 y 2147483647 minutos.'); return }
    let depositCents: number | null = null
    if (policy !== 'deshabilitada') {
      try { depositCents = parsePrice(deposit) } catch { setError('Ingresa una seña válida en ARS, con hasta dos decimales.'); return }
      if (depositCents === null || depositCents <= 0) { setError('La seña habilitada requiere un importe positivo.'); return }
    }
    const patch: Partial<Pick<Treatment, 'nombre' | 'duracion_min' | 'precio_referencia_centavos' | 'sena_politica' | 'sena_centavos'>> = {}
    if (policy !== (item?.sena_politica ?? 'deshabilitada') || depositCents !== (item?.sena_centavos ?? null)) {
      patch.sena_politica = policy
      patch.sena_centavos = depositCents
    }
    if (trimmedName !== item?.nombre) patch.nombre = trimmedName
    if (!item || cents !== item.precio_referencia_centavos) patch.precio_referencia_centavos = cents
    if (Number(duration) !== item?.duracion_min) patch.duracion_min = Number(duration)
    if (!Object.keys(patch).length) { setError('No hay cambios para guardar.'); return }
    if (!writes.begin()) return
    setBusy(true); setError(''); setFields({})
    try {
      const signal = AbortSignal.timeout(15000)
      const value = item
        ? await session.patch<unknown>(`/api/config/tratamientos/${item.id}`, patch, { expectedStatus: 200, signal })
        : await session.post<unknown>('/api/config/tratamientos', patch, { expectedStatus: 201, signal })
      if (!isTreatment(value) || (item && value.id !== item.id) || (!item && !value.activo) || value.sena_politica !== policy || value.sena_centavos !== depositCents || (patch.nombre !== undefined && value.nombre !== patch.nombre) || (patch.precio_referencia_centavos !== undefined && value.precio_referencia_centavos !== cents) || (patch.duracion_min !== undefined && value.duracion_min !== patch.duracion_min)) throw new Error('Respuesta no verificada')
      // If the form disappeared, retain the lock: its new reader may be stale.
      writes.finish(!mounted.current)
      if (!mounted.current) return
      onSaved(value)
    } catch (cause) {
      if (cause instanceof ApiError && cause.status === 422) {
        writes.finish(!mounted.current)
        if (!mounted.current) return
        const detail = isRecord(cause.body) ? cause.body.detail : undefined
        const invalid: typeof fields = {}
        if (Array.isArray(detail)) for (const entry of detail) {
          if (!isRecord(entry) || !Array.isArray(entry.loc) || entry.loc[0] !== 'body') continue
          const field: unknown = entry.loc[1]
          if (field === 'nombre' || field === 'duracion_min' || field === 'precio_referencia_centavos') invalid[field] = true
        }
        setFields(invalid); setError('Revisa los datos. El servidor rechazó los cambios.'); return
      }
      writes.finish(true)
      if (!mounted.current) return
      setError('Resultado no verificado. No repitas la escritura; consulta el recurso y solicita conciliación antes de volver a modificarlo.')
    } finally { if (mounted.current) setBusy(false) }
  }
  return <form noValidate onSubmit={event => void save(event)} aria-label={item ? `Editar ${item.nombre}` : 'Agregar tratamiento'}>
    <h2>{item ? 'Editar tratamiento' : 'Agregar tratamiento'}</h2>
    <label>Nombre<input value={name} onChange={event => setName(event.target.value)} disabled={busy || locked} maxLength={120} aria-invalid={fields.nombre || undefined} aria-describedby={fields.nombre ? 'name-error' : undefined} /></label>
    {fields.nombre ? <small id="name-error">Revisa el nombre indicado.</small> : null}
    <label>Duración en minutos<input inputMode="numeric" value={duration} onChange={event => setDuration(event.target.value)} disabled={busy || locked} maxLength={10} aria-invalid={fields.duracion_min || undefined} aria-describedby={fields.duracion_min ? 'duration-error' : undefined} /></label>
    {fields.duracion_min ? <small id="duration-error">Revisa la duración indicada.</small> : null}
    <label>Precio de referencia en ARS<input inputMode="decimal" value={price} onChange={event => setPrice(event.target.value)} disabled={busy || locked} maxLength={11} aria-invalid={fields.precio_referencia_centavos || undefined} aria-describedby={fields.precio_referencia_centavos ? 'price-error' : undefined} /></label>
    {fields.precio_referencia_centavos ? <small id="price-error">Revisa el precio indicado.</small> : null}
    <p>Vacío significa sin precio de referencia.</p>
    <label>Política de seña<select value={policy} disabled={busy || locked} onChange={event => {
      const value = event.target.value
      if (value === 'deshabilitada' || value === 'opcional' || value === 'obligatoria') setPolicy(value)
    }}>
      <option value="deshabilitada">Deshabilitada</option><option value="opcional">Opcional</option><option value="obligatoria">Obligatoria</option>
    </select></label>
    {policy !== 'deshabilitada' ? <label>Seña en ARS<input inputMode="decimal" value={deposit} onChange={event => setDeposit(event.target.value)} maxLength={11} disabled={busy || locked} required /></label> : null}
    {error ? <Notice>{error}</Notice> : null}
    <div className="actions"><button disabled={busy || locked}>{busy ? 'Guardando…' : item ? 'Guardar cambios' : 'Crear tratamiento'}</button><button type="button" className="secondary" disabled={busy} onClick={onCancel}>Volver a la lista</button></div>
  </form>
}
