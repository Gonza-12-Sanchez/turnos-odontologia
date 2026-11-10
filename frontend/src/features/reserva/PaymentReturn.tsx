import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useSession } from '../auth/context'
import { Notice } from '../../shared/ui'
import { errorMessage, useOnline } from '../../shared/network'
import { ars, isUuid } from './payments'
import type { PaymentState } from './payments'

export default function PaymentReturn() {
  const { session, user } = useSession()
  const [params] = useSearchParams()
  const id = params.get('intento_id')
  const online = useOnline()
  const [result, setResult] = useState<PaymentState | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [query, setQuery] = useState(0)
  const payment = result?.id === id ? result : null
  useEffect(() => {
    if (!isUuid(id) || !online) return
    const controller = new AbortController()
    let timer: ReturnType<typeof setTimeout> | undefined
    const deadline = Date.now() + 60_000
    async function poll() {
      setBusy(true)
      try {
        const result = await session.get<PaymentState>(`/pagos/sena/${id}`, { signal: controller.signal })
        if (controller.signal.aborted) return
        setResult(result)
        if (['pendiente', 'creando_checkout'].includes(result.estado) && Date.now() + 3000 < deadline) timer = setTimeout(() => void poll(), 3000)
      } catch (e) { if (!controller.signal.aborted) setError(errorMessage(e)) }
      finally { if (!controller.signal.aborted) setBusy(false) }
    }
    void poll()
    return () => { controller.abort(); clearTimeout(timer) }
  }, [id, online, session, query, user?.id])
  return <section className="payment-page"><h1>Estado de la sena</h1>
    <p>El regreso del checkout no confirma un pago ni una reserva.</p>
    {!isUuid(id) ? <Notice>Falta un identificador de intento valido.</Notice> : null}
    {busy ? <p role="status">Consultando estado...</p> : null}
    {error ? <Notice>{error}</Notice> : null}
    {payment && online ? <div aria-live="polite">
      <p>{ars(payment.monto_centavos)}</p>
      {payment.estado === 'aprobado' && payment.turno_id ? <p className="success">Reserva registrada. Consulta los datos en Mis reservas.</p>
        : payment.estado === 'requiere_revision' ? <Notice>Pago a revisar, reserva no confirmada: contacta al consultorio para la devolucion manual o resolucion. No vuelvas a pagar.</Notice>
        : payment.estado === 'rechazado' || payment.estado === 'expirado' ? <p>Pago {payment.estado}. No hay reserva registrada para este intento.</p>
        : <p>Pago pendiente de verificacion. No hay reserva confirmada todavia.</p>}
    </div> : null}
    <div className="actions"><button disabled={!online || busy || !isUuid(id)} onClick={() => { setError(''); setQuery(n => n + 1) }}>Consultar estado</button><Link to="/mis-reservas">Ver Mis reservas</Link>
      {payment && ['rechazado', 'expirado'].includes(payment.estado) ? <Link to="/horarios">Volver a horarios</Link> : null}</div>
  </section>
}
