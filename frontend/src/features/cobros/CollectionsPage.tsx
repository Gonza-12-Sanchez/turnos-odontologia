import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { useSession } from '../auth/context'
import { ars } from '../reserva/payments'
import { ApiError } from '../../shared/api/client'
import { isAwareDate, isRecord } from '../../shared/api/contracts'
import { useOnline } from '../../shared/network'
import { dateTime } from '../../shared/time'
import { Notice } from '../../shared/ui'

export interface CollectionSelection { id: string; treatment: string }
export interface PendingCollection { key: string; turno: string; amount: number }

interface Summary {
  precio_referencia_centavos: number | null
  sena_acumulada_centavos: number
  total_cobrado_centavos: number
  saldo_referencia_centavos: number | null
  cerrado: boolean
}

function cents(value: unknown): value is number {
  return typeof value === 'number' && Number.isSafeInteger(value) && value >= 0
}

function isSummary(value: unknown): value is Summary {
  return isRecord(value) && typeof value.cerrado === 'boolean'
    && cents(value.sena_acumulada_centavos) && cents(value.total_cobrado_centavos)
    && (value.precio_referencia_centavos === null || cents(value.precio_referencia_centavos))
    && (value.saldo_referencia_centavos === null || cents(value.saldo_referencia_centavos))
}

interface Movement {
  id: string
  turno_id: string
  monto_centavos: number
  medio: 'efectivo' | 'transferencia' | 'mercadopago'
  tipo: 'sena' | 'total'
  estado_mp: string | null
  created_at: string
}

const media = { efectivo: 'Efectivo', transferencia: 'Transferencia', mercadopago: 'Mercado Pago' }

function isMovement(value: unknown): value is Movement {
  return isRecord(value) && typeof value.id === 'string' && typeof value.turno_id === 'string'
    && cents(value.monto_centavos) && isAwareDate(value.created_at)
    && (value.medio === 'efectivo' || value.medio === 'transferencia' || value.medio === 'mercadopago')
    && (value.tipo === 'sena' || value.tipo === 'total')
    && (value.estado_mp === null || typeof value.estado_mp === 'string')
}

function amountInCents(input: string) {
  const value = input.trim()
  if (!/^\d{1,8}(?:[,.]\d{1,2})?$/.test(value)) return null
  const [whole, fraction = ''] = value.split(/[,.]/)
  const amount = BigInt(whole) * 100n + BigInt(fraction.padEnd(2, '0'))
  return amount > 0 && amount <= 2147483647n ? Number(amount) : null
}

function matchesReceipt(value: unknown, operation: PendingCollection) {
  return isRecord(value) && isRecord(value.cobro) && typeof value.cobro.id === 'string'
    && value.cobro.turno_id === operation.turno && value.cobro.monto_centavos === operation.amount
}

export default function CollectionsPage({ selection, pending, onPending }: {
  selection: CollectionSelection | null
  pending: PendingCollection | null
  onPending: (value: PendingCollection | null) => void
}) {
  const { session } = useSession()
  const online = useOnline()
  const [summary, setSummary] = useState<Summary | null>(null)
  const [movements, setMovements] = useState<Movement[] | null>(null)
  const [movementError, setMovementError] = useState(false)
  const [amount, setAmount] = useState('')
  const [type, setType] = useState<'sena' | 'total'>('total')
  const [medium, setMedium] = useState('efectivo')
  const [override, setOverride] = useState<number | null>(null)
  const [reason, setReason] = useState('')
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const [readError, setReadError] = useState(false)
  const [revision, setRevision] = useState(0)
  const locked = useRef(false)
  const id = selection?.id

  useEffect(() => {
    if (!online || !id) return
    const controller = new AbortController()
    void session.get<unknown>(`/cobros/resumen/${id}`, { signal: controller.signal }).then(value => {
      if (!isSummary(value)) throw new Error('Resumen inválido')
      if (!controller.signal.aborted) setSummary(value)
    }).catch(() => { if (!controller.signal.aborted) setReadError(true) })
    void session.get<unknown>('/cobros', { query: { turno_id: id }, signal: controller.signal }).then(value => {
      if (!Array.isArray(value) || !value.every(item => isMovement(item) && item.turno_id === id)) throw new Error('Movimientos inválidos')
      if (!controller.signal.aborted) setMovements(value)
    }).catch(() => { if (!controller.signal.aborted) setMovementError(true) })
    return () => controller.abort()
  }, [id, online, revision, session])

  function reload() {
    setReadError(false)
    setSummary(null)
    setMovementError(false)
    setMovements(null)
    setRevision(value => value + 1)
  }

  async function register() {
    const parsed = amountInCents(amount)
    if (!id || !online || !summary || summary.cerrado || pending || locked.current) return
    if (parsed === null) { setMessage('Ingresá un importe positivo con hasta dos decimales.'); return }
    if (override !== null && !reason.trim()) { setMessage('Ingresá el motivo para autorizar la diferencia.'); return }

    const operation = { key: crypto.randomUUID(), turno: id, amount: parsed }
    locked.current = true
    onPending(operation)
    setBusy(true)
    setMessage('')
    try {
      const result = await session.post<unknown>('/cobros', {
        turno_id: id, monto_centavos: parsed, medio: medium, tipo: type,
        ...(override === null ? {} : { override_motivo: reason.trim() }),
      }, { headers: { 'Idempotency-Key': operation.key }, signal: AbortSignal.timeout(15000) })
      if (!matchesReceipt(result, operation)) throw new Error('Resultado no verificado')
      onPending(null)
      setOverride(null)
      setReason('')
      setAmount('')
      setMessage('Cobro registrado.')
      reload()
    } catch (cause) {
      const detail = cause instanceof ApiError && isRecord(cause.body) ? cause.body.detail : null
      if (cause instanceof ApiError && [400, 401, 403, 404, 409, 422].includes(cause.status)) {
        onPending(null)
        if (isRecord(detail) && detail.code === 'MONTO_DIFIERE' && cents(detail.esperado_centavos)) {
          setOverride(detail.esperado_centavos)
          setMessage('Confirmá la diferencia e indicá el motivo antes de guardar.')
        } else {
          setMessage('El servidor rechazó el cobro. Revisá el resumen actualizado.')
          reload()
        }
      } else {
        setMessage('El resultado quedó sin verificar. Consultá la operación antes de registrar otro cobro.')
      }
    } finally {
      locked.current = false
      setBusy(false)
    }
  }

  async function reconcile() {
    if (!online || !pending || locked.current) return
    locked.current = true
    setBusy(true)
    try {
      const result = await session.get<unknown>('/cobros/operacion', {
        headers: { 'Idempotency-Key': pending.key }, signal: AbortSignal.timeout(15000),
      })
      if (!matchesReceipt(result, pending)) {
        setMessage('Todavía no se pudo confirmar el resultado. El registro sigue bloqueado.')
        return
      }
      onPending(null)
      setAmount('')
      setOverride(null)
      setReason('')
      setMessage('El servidor confirmó que el cobro se registró.')
      reload()
    } catch {
      setMessage('No se pudo consultar el resultado. El registro sigue bloqueado.')
    } finally {
      locked.current = false
      setBusy(false)
    }
  }

  const closure = movements?.find(movement => movement.tipo === 'total')

  return <section>
    <h1>Cobros</h1>
    <p>Sin factura electrónica en v1. Mercado Pago manual registra dinero recibido en mostrador, no verifica un pago online.</p>
    {selection ? <Link to="/agenda">Volver a la agenda</Link> : null}
    {!online ? <Notice>Sin conexión. Los cobros no se guardan en este dispositivo.</Notice> : null}
    {!selection ? <p>Elegí un turno desde la <Link to="/agenda">agenda</Link> para ver su saldo.</p> : null}
    {message ? <Notice>{message}</Notice> : null}
    {pending ? <button type="button" className="secondary" disabled={busy || !online} onClick={() => void reconcile()}>Consultar resultado del cobro</button> : null}
    {online && selection ? <>
      <h2>{selection.treatment}</h2>
      {readError ? <><Notice>No se pudo consultar el resumen de cobros.</Notice><button onClick={reload}>Reintentar consulta</button></> : null}
      {!summary && !readError ? <p role="status">Consultando saldo…</p> : null}
      {summary ? <div className="staff-detail-layout">
        <section aria-label="Resumen y movimientos">
        <dl className="staff-summary">
          <dt>Precio de referencia</dt><dd>{summary.precio_referencia_centavos === null ? 'Sin referencia' : ars(summary.precio_referencia_centavos)}</dd>
          <dt>Seña registrada</dt><dd>{ars(summary.sena_acumulada_centavos)}</dd>
          <dt>Total cobrado</dt><dd>{ars(summary.total_cobrado_centavos)}</dd>
          <dt>Saldo de referencia</dt><dd>{summary.saldo_referencia_centavos === null ? 'Sin referencia' : ars(summary.saldo_referencia_centavos)}</dd>
        </dl>
        <h3>Movimientos</h3>
        {movementError ? <p>No se pudieron consultar los movimientos. <button type="button" className="secondary" onClick={reload}>Reintentar movimientos</button></p>
          : movements === null ? <p role="status">Consultando movimientos…</p>
          : movements.length === 0 ? <p>Todavía no hay movimientos.</p>
          : <ul className="staff-movements">{movements.map(movement => <li key={movement.id}>
            <strong>{movement.tipo === 'sena' ? 'Seña' : 'Cierre'} · {ars(movement.monto_centavos)}</strong>
            <span>{dateTime(movement.created_at)} · {media[movement.medio]}{movement.estado_mp ? ` · ${movement.estado_mp}` : null}</span>
          </li>)}</ul>}
        </section>
        {summary.cerrado ? <section className="staff-detail-panel" aria-label="Cierre registrado">
          <h3>Cierre registrado</h3><p>Cobro cerrado.</p>
          {closure ? <dl className="staff-summary">
            <dt>Operación</dt><dd>{closure.id}</dd>
            <dt>Dinero nuevo recibido</dt><dd>{ars(closure.monto_centavos)}</dd>
            <dt>Medio</dt><dd>{media[closure.medio]}</dd>
            <dt>Fecha</dt><dd>{dateTime(closure.created_at)}</dd>
          </dl> : <p>El cierre está confirmado. Sus detalles dependen de la consulta de movimientos.</p>}
          {summary.saldo_referencia_centavos !== null && summary.saldo_referencia_centavos > 0 ? <Notice>El cierre tiene una diferencia respecto del precio de referencia de {ars(summary.saldo_referencia_centavos)}.</Notice> : null}
          <p>La seña previa ya está incluida en el total cobrado. No se registra otra vez.</p>
          <Link to="/agenda">Volver a agenda</Link>
        </section> : <form noValidate className="staff-detail-panel" onSubmit={event => { event.preventDefault(); void register() }}>
          <fieldset disabled={busy || pending !== null}>
            <legend>Registrar cobro</legend>
            <label>Tipo<select value={type} onChange={event => { setType(event.target.value === 'sena' ? 'sena' : 'total'); setOverride(null); setReason('') }}>
              <option value="total">Cierre</option><option value="sena">Seña</option>
            </select></label>
            <label>Medio<select value={medium} onChange={event => { setMedium(event.target.value); setOverride(null); setReason('') }}>
              <option value="efectivo">Efectivo</option><option value="transferencia">Transferencia</option><option value="mercadopago">Mercado Pago manual</option>
            </select></label>
            <p>Ingresá solo el dinero recibido ahora, sin volver a sumar la seña.</p>
            <label>Importe en ARS<input value={amount} inputMode="decimal" onChange={event => { setAmount(event.target.value); setOverride(null); setReason('') }} required /></label>
            {override !== null ? <>
              <p>Importe esperado: {ars(override)}</p>
              <label>Motivo de la diferencia<input value={reason} onChange={event => setReason(event.target.value)} maxLength={300} required /></label>
            </> : null}
            <button>{override === null ? 'Registrar cobro' : 'Confirmar cobro con diferencia'}</button>
          </fieldset>
        </form>}
      </div> : null}
    </> : null}
  </section>
}
