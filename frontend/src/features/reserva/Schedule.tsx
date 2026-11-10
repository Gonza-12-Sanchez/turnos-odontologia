import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useSession } from '../auth/context'
import { ApiError } from '../../shared/api/client'
import type { Booking, Catalog, Slot } from '../../shared/api/contracts'
import { isCatalog, isRecord, isSlot } from '../../shared/api/contracts'
import { Notice } from '../../shared/ui'
import { errorMessage, useOnline } from '../../shared/network'
import { argentinaDate, dateTime, hour, timeZone } from '../../shared/time'
import { ars, isUuid, safeCheckout } from './payments'
import type { Checkout } from './payments'

export interface UnverifiedBooking { sillon_id: string; tratamiento_id: string; inicio: string; intento_id?: string }
export default function Schedule({ recovery, onRecoveryChange }: {
  recovery: UnverifiedBooking | null
  onRecoveryChange: (value: UnverifiedBooking | null) => void
}) {
  const { session, user, status } = useSession()
  const [params, setParams] = useSearchParams()
  const navigate = useNavigate()
  const online = useOnline()
  const [catalog, setCatalog] = useState<Catalog | null>(null)
  const [catalogError, setCatalogError] = useState(false)
  const [slotResult, setSlotResult] = useState<{ key: string; slots: Slot[]; error?: string } | null>(null)
  const [error, setError] = useState('')
  const [info, setInfo] = useState('')
  const [selection, setSelection] = useState<{ key: string; slot: Slot | null } | null>(null)
  const [conflict, setConflict] = useState<{ key: string; slots: Slot[] } | null>(null)
  const [busy, setBusy] = useState(false)
  const ambiguous = Boolean(recovery)
  const [reload, setReload] = useState(0)
  const writing = useRef(false)
  const paymentKey = useRef<{ payload: string; key: string } | null>(null)
  const [consent, setConsent] = useState(false)
  const [checkout, setCheckout] = useState<Checkout | null>(null)
  const attempt = recovery?.intento_id
  const testPayments = import.meta.env.VITE_ENABLE_TEST_PAYMENTS === 'true'
  const fecha = params.get('fecha') || argentinaDate()
  const tratamiento = params.get('tratamiento') || ''
  const sillon = params.get('sillon') || ''
  const inicio = params.get('inicio') || ''
  const treatment = catalog?.tratamientos.find(t => t.id === tratamiento)
  const queryKey = `${fecha}:${tratamiento}:${sillon}:${reload}:${online}`
  const slots = slotResult?.key === queryKey ? slotResult.slots : []
  const alternatives = conflict?.key === queryKey ? conflict.slots : null
  const selected = selection?.key === queryKey ? selection.slot : slots.find(s => s.inicio === inicio && (!sillon || s.sillon_id === sillon)) ?? null
  const outsideDay = selected ? argentinaDate(new Date(selected.inicio)) !== fecha : false
  const hasOutsideSlots = (alternatives ?? slots).some(slot => argentinaDate(new Date(slot.inicio)) !== fecha)
  const loading = Boolean(online && treatment && slotResult?.key !== queryKey)
  const loadError = slotResult?.key === queryKey ? slotResult.error : undefined
  const setSelected = (slot: Slot | null) => setSelection({ key: queryKey, slot })
  useEffect(() => {
    const invalidate = () => { setSlotResult(null); setSelection(null); setConflict(null); setConsent(false) }
    window.addEventListener('online', invalidate)
    return () => window.removeEventListener('online', invalidate)
  }, [])
  useEffect(() => {
    if (!online) return
    const controller = new AbortController()
    session.api.get<Catalog>('/catalogo-publico', { signal: controller.signal }).then(result => {
      if (!isCatalog(result)) throw new Error('Invalid catalog contract')
      if (!controller.signal.aborted) { setCatalog(result); setCatalogError(false) }
    }).catch(() => { if (!controller.signal.aborted) setCatalogError(true) })
    return () => controller.abort()
  }, [session, online, reload])
  useEffect(() => {
    if (!treatment || !online || !/^\d{4}-\d{2}-\d{2}$/.test(fecha)) return
    const controller = new AbortController()
    session.api.get<Slot[]>('/horarios-libres', { query: { fecha, tratamiento, ...(sillon ? { sillon } : {}) }, signal: controller.signal }).then(result => {
      if (!Array.isArray(result) || !result.every(isSlot)) throw new Error('Invalid slots contract')
      if (controller.signal.aborted) return
      setSlotResult({ key: queryKey, slots: result })
    }).catch(() => { if (!controller.signal.aborted) setSlotResult({ key: queryKey, slots: [], error: 'No se pudieron consultar horarios. Intenta nuevamente.' }) })
    return () => controller.abort()
  }, [session, treatment, fecha, tratamiento, sillon, online, queryKey])
  function filter(name: string, value: string) {
    if (ambiguous || writing.current) return
    const next = new URLSearchParams(params)
    next.set(name, value); next.delete('inicio')
    setParams(next); setSelected(null); setInfo(''); setError(''); setConsent(false); setCheckout(null)
  }
  function choose(slot: Slot) { if (ambiguous || writing.current) return; setSelected(slot); setInfo(''); setError(''); setConsent(false); setCheckout(null) }
  async function reserve() {
    if (!selected || outsideDay || !online || writing.current || ambiguous) return
    if (!user) {
      const next = new URLSearchParams({ fecha, tratamiento, sillon: selected.sillon_id, inicio: selected.inicio })
      navigate(`/login?returnTo=${encodeURIComponent('/horarios?' + next.toString())}`)
      return
    }
    if (user.rol !== 'paciente') { setError('Esta area es solo para pacientes.'); return }
    const sena = treatment?.sena_politica === 'obligatoria' || consent
    if (sena && (!testPayments || !consent)) return
    writing.current = true; setBusy(true); setError(''); setInfo('')
    const payload = { sillon_id: selected.sillon_id, tratamiento_id: tratamiento, inicio: selected.inicio, ...(sena ? { sena: true } : {}) }
    try {
      const fingerprint = JSON.stringify(payload)
      if (paymentKey.current?.payload !== fingerprint) paymentKey.current = { payload: fingerprint, key: crypto.randomUUID() }
      const result = await session.post<Booking>('/turnos', payload, { headers: { 'Idempotency-Key': paymentKey.current.key }, expectedStatus: 201 })
      if (!isSlot(result) || !isRecord(result) || typeof result.id !== 'string' || typeof result.estado !== 'string') throw new ApiError(502, 'Resultado no verificado.')
      setInfo(`Reserva registrada: ${dateTime(result.inicio)}. Estado: ${result.estado}.`)
      setSelected(null)
    } catch (e) {
      if (e instanceof ApiError && e.status === 402) {
        const value = safeCheckout(isRecord(e.body) ? e.body.checkout : undefined, testPayments, import.meta.env.DEV)
        if (value) { setCheckout(value); setSelected(null) }
        else { onRecoveryChange(payload); setError('Resultado no verificado. Checkout no habilitado o no valido. Consulta al consultorio antes de volver a pagar.') }
      } else if (e instanceof ApiError && e.status === 503 && isRecord(e.body) && e.body.code === 'CHECKOUT_NO_VERIFICADO' && isUuid(e.body.intento_id)) {
        onRecoveryChange({ ...payload, intento_id: e.body.intento_id })
        setError('Checkout no verificado. Consulta el estado de este intento; no vuelvas a pagar.')
      } else if (e instanceof ApiError && e.status === 409) {
        setError('El horario se ocupo. Elegi una alternativa y confirma nuevamente.')
        setConflict({ key: queryKey, slots: isRecord(e.body) && Array.isArray(e.body.alternativas) ? e.body.alternativas.filter(isSlot) : [] })
        setSelected(null)
      } else {
        const uncertain = !(e instanceof ApiError) || ![401, 403, 422].includes(e.status)
        setError(uncertain ? 'Resultado no verificado. Consulta Mis reservas antes de intentar nuevamente.' : errorMessage(e))
        if (uncertain) onRecoveryChange(payload)
      }
    } finally { writing.current = false; setBusy(false) }
  }
  async function reconcile() {
    if (!recovery || !online || writing.current) return
    if (recovery.intento_id) { navigate(`/pagos/retorno?intento_id=${recovery.intento_id}`); return }
    writing.current = true; setBusy(true)
    try {
      const rows = await session.get<unknown>('/mis-reservas')
      if (!Array.isArray(rows)) throw new Error('Invalid reservations contract')
      const found: unknown = rows.find((row: unknown) => isRecord(row) && isSlot(row) && typeof row.id === 'string' && typeof row.estado === 'string' && row.sillon_id === recovery.sillon_id && row.tratamiento_id === recovery.tratamiento_id && Date.parse(row.inicio) === Date.parse(recovery.inicio))
      if (isRecord(found) && isSlot(found)) {
        onRecoveryChange(null); setSelected(null); setError('')
        setInfo(`Reserva encontrada en el servidor: ${dateTime(found.inicio)}. Estado: ${found.estado}.`)
      } else {
        setInfo('No se encontro la reserva. Esto no prueba que no exista o no se este procesando. Contacta al consultorio antes de volver a reservar o pagar.')
      }
    } catch { setInfo('No se pudo reconciliar la solicitud. El bloqueo continua. Consulta al consultorio.') }
    finally { writing.current = false; setBusy(false) }
  }
  const name = (id: string) => catalog?.sillones.find(s => s.id === id)?.nombre ?? 'Sillon'
  return <section>
    <h1>Horarios disponibles</h1><p className="muted">Hora del consultorio: {timeZone} (UTC-3).</p>
    {recovery ? <section aria-label="Reserva por reconciliar"><Notice>Resultado no verificado. No vuelvas a reservar o pagar hasta reconciliar la solicitud anterior. El header de idempotencia no garantiza que el backend evite duplicados.</Notice><button disabled={busy || !online} onClick={() => void reconcile()}>Reconciliar reserva</button></section> : null}
    {catalogError ? <><Notice>No se pudo cargar el catalogo. No se muestran datos de prueba.</Notice><button onClick={() => setReload(n => n + 1)}>Reintentar consulta</button></> : !catalog ? <p role="status">Cargando catalogo...</p> : !catalog.tratamientos.length || !catalog.sillones.length ? <p role="status">No hay tratamientos disponibles. Consulta al consultorio.</p> : <div className="booking-layout">
      <div className="filters"><h2>Elegi tu visita</h2>
        <label>Tratamiento<select disabled={busy || ambiguous} value={tratamiento} onChange={e => filter('tratamiento', e.target.value)}><option value="">Elegi un tratamiento</option>{catalog.tratamientos.map(t => <option key={t.id} value={t.id}>{t.nombre} ({t.duracion_min} min)</option>)}</select></label>
        <label>Fecha<input disabled={busy || ambiguous} type="date" value={fecha} onChange={e => filter('fecha', e.target.value)} /></label>
        <label>Sillon<select disabled={busy || ambiguous} value={sillon} onChange={e => filter('sillon', e.target.value)}><option value="">Todos los sillones</option>{catalog.sillones.map(s => <option key={s.id} value={s.id}>{s.nombre}</option>)}</select></label>
        <p className="muted">Los horarios se vuelven a verificar al reservar.</p>
      </div>
      <div className="availability" aria-busy={loading}>
        <h2>Elegi un horario</h2>
        {!treatment ? <p>Selecciona un tratamiento para consultar.</p> : loading ? <p role="status">Consultando horarios...</p> : !online ? <p>Reconecta para consultar horarios actuales.</p> : <>
          {error && !recovery ? <Notice>{error}</Notice> : null}
          {loadError ? <Notice>{loadError}</Notice> : null}
          {hasOutsideSlots ? <Notice>El servidor devolvio horarios fuera de la fecha elegida en Argentina. Esas franjas no se pueden reservar aqui; el contrato del dia UTC/local sigue pendiente de acuerdo con backend. No se ocultaron horarios.</Notice> : null}
          <div className="slots">{(alternatives ?? slots).map(s => <button className="slot" key={s.sillon_id + s.inicio} disabled={busy || ambiguous || argentinaDate(new Date(s.inicio)) !== fecha} aria-pressed={selected?.inicio === s.inicio && selected?.sillon_id === s.sillon_id} onClick={() => choose(s)}><strong>{hour(s.inicio)}</strong><time dateTime={s.inicio}>{dateTime(s.inicio)}</time><span>{name(s.sillon_id)}</span></button>)}</div>
          {!(alternatives ?? slots).length && !error && !loadError ? <p role="status">No hay horarios disponibles.</p> : null}
          {alternatives?.length === 0 ? <p>Cambia la fecha o los filtros para buscar otro horario.</p> : null}
          {selected ? <section className="summary" aria-label="Resumen de reserva"><h2>Tu seleccion</h2><p>{treatment.nombre}, {dateTime(selected.inicio)}</p><p>{name(selected.sillon_id)}. Finaliza a las {hour(selected.fin)}.</p>
            {treatment.sena_politica !== 'deshabilitada' && treatment.sena_centavos !== null ? <><p>Sena {treatment.sena_politica}: {ars(treatment.sena_centavos)}</p><p>El horario se verifica al aprobar el pago. No se retiene cupo durante el checkout. Si se paga sin cupo, la devolucion es manual a cargo del consultorio.</p>
              {testPayments ? <label className="checkbox"><input type="checkbox" disabled={busy || ambiguous} checked={consent} onChange={e => setConsent(e.target.checked)} />Acepto la sena y las condiciones de cupo (modo prueba)</label> : <p>Pagos de prueba no habilitados. Consulta al consultorio.</p>}</> : null}
            <button disabled={busy || ambiguous || outsideDay || !online || status === 'loading' || (Boolean(user) && treatment.sena_politica === 'obligatoria' && (!consent || !testPayments))} onClick={() => void reserve()}>{busy ? 'Enviando...' : user ? 'Reservar turno' : 'Ingresar para reservar'}</button></section> : null}
        </>}
        {info ? <p className="success" role="status">{info}</p> : null}
        {checkout && online ? <section className="summary" aria-label="Checkout de prueba"><h2>Checkout de prueba ({checkout.modo})</h2><p>{ars(checkout.monto_centavos)}</p><p>El horario se verifica al aprobar el pago. No se retiene cupo; si no hay cupo, contacta al consultorio para una devolucion manual.</p><a className="button" href={checkout.checkout_url} rel="noreferrer">Continuar al checkout de prueba</a><Link to={`/pagos/retorno?intento_id=${checkout.intento_id}`}>Consultar estado del intento</Link></section> : null}
        {attempt ? <Link to={`/pagos/retorno?intento_id=${attempt}`}>Consultar estado del intento</Link> : null}
        <Link to="/mis-reservas">Consultar Mis reservas</Link>
        <button className="secondary" disabled={busy || ambiguous || !online} onClick={() => setReload(n => n + 1)}>Actualizar horarios</button>
      </div>
    </div>}
  </section>
}
