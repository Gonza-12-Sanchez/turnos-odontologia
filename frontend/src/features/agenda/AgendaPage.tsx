import { useEffect, useState } from 'react'
import { useSession } from '../auth/context'
import { isAwareDate, isRecord } from '../../shared/api/contracts'
import { useOnline } from '../../shared/network'
import { argentinaDate, hour } from '../../shared/time'
import { Notice } from '../../shared/ui'
import type { CollectionSelection } from '../cobros/CollectionsPage'
import { isUuid } from '../reserva/payments'
import TurnActions from './TurnActions'
import type { ExpectedTurn, StaffActions } from './TurnActions'

interface Appointment {
  id: string
  inicio: string
  fin: string
  estado: string
  paciente_nombre: string
  tratamiento_nombre: string
  tolerancia_min: number
  es_sobreturno: boolean
  motivo_sobreturno: string | null
  tratamiento_id?: string
  acciones?: StaffActions
}

interface ChairAgenda {
  sillon_id: string
  sillon_nombre: string
  turnos: Appointment[]
}

function isStaffActions(value: unknown): value is StaffActions {
  return isRecord(value) && typeof value.confirmar === 'boolean' && typeof value.cancelar === 'boolean'
    && typeof value.reprogramar === 'boolean' && typeof value.asistencia === 'boolean' && typeof value.sobreturno === 'boolean'
}

function isAppointment(value: unknown): value is Appointment {
  return isRecord(value) && typeof value.id === 'string'
    && isAwareDate(value.inicio) && isAwareDate(value.fin)
    && Date.parse(value.inicio) < Date.parse(value.fin)
    && typeof value.estado === 'string' && typeof value.paciente_nombre === 'string'
    && typeof value.tratamiento_nombre === 'string' && typeof value.tolerancia_min === 'number'
    && Number.isInteger(value.tolerancia_min) && value.tolerancia_min >= 0
    && typeof value.es_sobreturno === 'boolean'
    && (value.tratamiento_id === undefined || isUuid(value.tratamiento_id))
    && (value.acciones === undefined || isStaffActions(value.acciones))
    && (value.motivo_sobreturno === null || typeof value.motivo_sobreturno === 'string')
}

function isChairAgenda(value: unknown): value is ChairAgenda {
  return isRecord(value) && typeof value.sillon_id === 'string'
    && typeof value.sillon_nombre === 'string'
    && Array.isArray(value.turnos) && value.turnos.every(isAppointment)
}

const statuses = ['reservado', 'confirmado', 'asistido', 'cancelado', 'ausente']

interface AgendaActions {
  onCollect?: (selection: CollectionSelection) => void
  uncertain: Record<string, ExpectedTurn>
  onUncertain: (id: string, expected?: ExpectedTurn) => void
}

function DailyAgenda({ day, status, chair, onCollect, uncertain, onUncertain }: AgendaActions & { day: string; status: string; chair: string }) {
  const { session } = useSession()
  const [result, setResult] = useState<ChairAgenda[] | null>(null)
  const [error, setError] = useState(false)
  const [revision, setRevision] = useState(0)
  function refresh() {
    setError(false)
    setResult(null)
    setRevision(value => value + 1)
  }

  useEffect(() => {
    const controller = new AbortController()
    const query = { fecha: day, ...(status ? { estado: status } : {}), ...(chair ? { sillon: chair } : {}) }
    void session.get<unknown>('/agenda', { query, signal: controller.signal })
      .then(value => {
        if (!Array.isArray(value) || !value.every(isChairAgenda)) throw new Error('Agenda inválida')
        if (!controller.signal.aborted) setResult(value)
      })
      .catch(() => { if (!controller.signal.aborted) setError(true) })
    return () => controller.abort()
  }, [session, day, status, chair, revision])

  if (error) return <Notice>No se pudo consultar la agenda. Volvé a pulsar Consultar agenda para reintentar.</Notice>
  if (!result) return <p role="status">Consultando turnos…</p>
  if (!result.some(group => group.turnos.length)) return <p>No hay turnos para los filtros elegidos.</p>

  return <>{result.filter(group => group.turnos.length > 0).map(group => <section key={group.sillon_id}>
    <h2>{group.sillon_nombre}</h2>
    <ol className="reservations">{group.turnos.toSorted((a, b) => Date.parse(a.inicio) - Date.parse(b.inicio)).map(turno => <li key={turno.id}>
      <div className="reservation-heading"><h3>{turno.paciente_nombre}</h3><span className="state">{turno.estado}</span></div>
      <p><time dateTime={turno.inicio}>{hour(turno.inicio)}</time>–<time dateTime={turno.fin}>{hour(turno.fin)}</time> · {turno.tratamiento_nombre}</p>
      <p className="muted">Tolerancia de llegada: {turno.tolerancia_min} min.</p>
      {turno.es_sobreturno ? <p><strong>Sobreturno</strong>{turno.motivo_sobreturno ? `: ${turno.motivo_sobreturno}` : null}</p> : null}
      {onCollect && isUuid(turno.id) ? <button className="secondary" onClick={() => onCollect({ id: turno.id, treatment: turno.tratamiento_nombre })}>Ver cobros del turno</button> : null}
      {isUuid(turno.id) && turno.tratamiento_id && turno.acciones ? <TurnActions id={turno.id} treatmentId={turno.tratamiento_id} actions={turno.acciones} uncertain={uncertain[turno.id]} onUncertain={onUncertain} onChanged={refresh} /> : null}
    </li>)}</ol>
  </section>)}</>
}

export default function AgendaPage(actions: AgendaActions) {
  const online = useOnline()
  const [day, setDay] = useState(argentinaDate)
  const [status, setStatus] = useState('')
  const [chair, setChair] = useState('')
  const [query, setQuery] = useState({ day, status, chair, revision: 0 })
  const [chairs, setChairs] = useState<{ id: string; nombre: string }[]>([])
  const { session } = useSession()

  useEffect(() => {
    if (!online) return
    const controller = new AbortController()
    void session.get<unknown>('/catalogo-publico', { signal: controller.signal }).then(value => {
      if (!isRecord(value) || !Array.isArray(value.sillones)) return
      const valid = value.sillones.filter((entry): entry is { id: string; nombre: string } =>
        isRecord(entry) && typeof entry.id === 'string' && typeof entry.nombre === 'string')
      if (!controller.signal.aborted) setChairs(valid)
    }).catch(() => {})
    return () => controller.abort()
  }, [online, session])

  return <section>
    <h1>Agenda del día</h1>
    <form className="staff-filters" onSubmit={event => {
      event.preventDefault()
      if (day && online) setQuery(previous => ({ day, status, chair, revision: previous.revision + 1 }))
    }}>
      <label>Fecha<input type="date" value={day} onChange={event => setDay(event.target.value)} required /></label>
      <label>Estado<select value={status} onChange={event => setStatus(event.target.value)}>
        <option value="">Todos</option>{statuses.map(value => <option key={value}>{value}</option>)}
      </select></label>
      {chairs.length > 0 ? <label>Sillón<select value={chair} onChange={event => setChair(event.target.value)}>
        <option value="">Todos</option>{chairs.map(value => <option key={value.id} value={value.id}>{value.nombre}</option>)}
      </select></label> : null}
      <button className="secondary" disabled={!online}>Consultar agenda</button>
    </form>
    {online ? <DailyAgenda key={query.revision} day={query.day} status={query.status} chair={query.chair} {...actions} />
      : <Notice>Sin conexión. La agenda no se guarda en este dispositivo.</Notice>}
  </section>
}
