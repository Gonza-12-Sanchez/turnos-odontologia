import { useEffect, useRef, useState } from 'react'
import { useSession } from '../auth/context'
import { ApiError } from '../../shared/api/client'
import { isAwareDate, isRecord, isSlot } from '../../shared/api/contracts'
import type { Slot } from '../../shared/api/contracts'
import { argentinaDate, dateTime, hour } from '../../shared/time'
import { Notice } from '../../shared/ui'

export interface StaffActions {
  confirmar: boolean
  cancelar: boolean
  reprogramar: boolean
  asistencia: boolean
  sobreturno: boolean
}
export interface ExpectedTurn {
  estado?: string
  slot?: Slot
  motivo?: string
}
interface HistoryEntry {
  id: string
  actor_id: string | null
  accion: string
  origen: string
  motivo: string | null
  fecha: string
}
type Action = 'confirmar' | 'cancelar' | 'reprogramar' | 'asistido' | 'ausente' | 'sobreturno'

function matchesTurn(value: unknown, id: string, expected: ExpectedTurn) {
  return isRecord(value) && value.id === id
    && (!expected.estado || value.estado === expected.estado)
    && (!expected.motivo || (value.es_sobreturno === true && value.motivo_sobreturno === expected.motivo))
    && (!expected.slot || (value.sillon_id === expected.slot.sillon_id && isAwareDate(value.inicio)
      && Date.parse(value.inicio) === Date.parse(expected.slot.inicio)))
}

function isHistory(value: unknown): value is HistoryEntry {
  return isRecord(value) && typeof value.id === 'string' && typeof value.accion === 'string'
    && typeof value.origen === 'string' && isAwareDate(value.fecha)
    && (value.motivo === null || typeof value.motivo === 'string')
    && (value.actor_id === null || typeof value.actor_id === 'string')
}

const labels: Record<Action, string> = {
  confirmar: 'Confirmar turno', cancelar: 'Cancelar turno', reprogramar: 'Reprogramar turno',
  asistido: 'Marcar asistido', ausente: 'Marcar ausente', sobreturno: 'Marcar sobreturno',
}

export default function TurnActions({ id, treatmentId, chairs, actions, uncertain, onUncertain, onChanged }: {
  id: string
  treatmentId: string
  chairs: { id: string; nombre: string }[]
  actions: StaffActions
  uncertain?: ExpectedTurn
  onUncertain: (id: string, expected?: ExpectedTurn) => void
  onChanged: (message?: string) => void
}) {
  const { session } = useSession()
  const [action, setAction] = useState<Action | null>(null)
  const [message, setMessage] = useState('')
  const [reason, setReason] = useState('')
  const [day, setDay] = useState(argentinaDate)
  const [chair, setChair] = useState('')
  const chairName = (id: string) => chairs.find(row => row.id === id)?.nombre ?? 'Sillón ' + id.slice(0, 8)
  const [slots, setSlots] = useState<Slot[]>([])
  const [chosen, setChosen] = useState<Slot | null>(null)
  const [history, setHistory] = useState<HistoryEntry[] | null>(null)
  const [busy, setBusy] = useState(false)
  const pending = useRef(false)
  const reader = useRef<AbortController | null>(null)
  useEffect(() => () => reader.current?.abort(), [])

  async function read(path: string, onRead: (value: unknown) => void, query?: Record<string, string>) {
    reader.current?.abort()
    const controller = new AbortController()
    reader.current = controller
    setMessage('')
    try {
      const value = await session.get<unknown>(path, { query, signal: controller.signal })
      if (!controller.signal.aborted) onRead(value)
    } catch {
      if (!controller.signal.aborted) {
        setMessage(path.endsWith('/historial') ? 'No se pudo consultar el historial del turno.' : 'No se pudo completar la consulta.')
      }
    }
  }

  function choose(next: Action) {
    reader.current?.abort()
    setAction(next)
    setReason('')
    setMessage('')
    setSlots([])
    setChair('')
    setChosen(null)
  }

  async function write() {
    if (!action || uncertain || pending.current) return
    const motivo = reason.trim()
    const attendance = action === 'asistido' || action === 'ausente'
    if ((attendance || action === 'sobreturno') && !motivo) { setMessage('Ingresá el motivo antes de aplicar el cambio.'); return }
    if (action === 'reprogramar' && !chosen) return
    const expected: ExpectedTurn = {}
    const endpoint = attendance ? 'marcar-asistencia' : action
    let body: unknown
    if (attendance) {
      expected.estado = action
      body = { estado: action, motivo, origen: 'mostrador' }
    } else if (action === 'sobreturno') {
      expected.motivo = motivo
      body = { motivo }
    } else if (action === 'reprogramar' && chosen) {
      expected.slot = chosen
      body = { inicio: chosen.inicio, sillon_id: chosen.sillon_id }
    } else {
      expected.estado = action === 'confirmar' ? 'confirmado' : 'cancelado'
    }

    pending.current = true
    onUncertain(id, expected)
    setBusy(true)
    setMessage('')
    try {
      const value = await session.patch<unknown>('/turnos/' + id + '/' + endpoint, body, { signal: AbortSignal.timeout(15000) })
      if (!matchesTurn(value, id, expected)) throw new Error('Resultado no verificado')
      onUncertain(id)
      setAction(null)
      setHistory(null)
      onChanged('Turno actualizado.')
    } catch (cause) {
      if (cause instanceof ApiError && [400, 401, 403, 404, 409, 422].includes(cause.status)) {
        onUncertain(id)
        if (cause.status === 409 && isRecord(cause.body) && Array.isArray(cause.body.alternativas)) {
          setSlots(cause.body.alternativas.filter(isSlot))
          setChosen(null)
          setChair('')
          setMessage('El horario ya no está disponible. Elegí otro horario.')
        } else if (cause.status === 422) {
          const detail = isRecord(cause.body) ? cause.body.detail : null
          onChanged(typeof detail === 'string' ? detail : 'El turno cambió o la acción ya no está permitida.')
        } else {
          setMessage('El servidor rechazó el cambio. Volvé a consultar el turno.')
        }
      } else {
        setMessage('El resultado quedó sin verificar. Consultá el estado actual antes de volver a actuar.')
      }
    } finally {
      pending.current = false
      setBusy(false)
    }
  }

  return <>
    {!actions.cancelar && !actions.reprogramar ? <p>Cancelar y reprogramar no están habilitados por el servidor para este turno y tu cuenta.</p> : null}
    <div className="actions">
      {actions.confirmar ? <button disabled={busy || !!uncertain} onClick={() => choose('confirmar')}>{labels.confirmar}</button> : null}
      {actions.cancelar ? <button disabled={busy || !!uncertain} onClick={() => choose('cancelar')}>{labels.cancelar}</button> : null}
      {actions.reprogramar ? <button disabled={busy || !!uncertain} onClick={() => choose('reprogramar')}>{labels.reprogramar}</button> : null}
      {actions.asistencia ? <>
        <button disabled={busy || !!uncertain} onClick={() => choose('asistido')}>{labels.asistido}</button>
        <button disabled={busy || !!uncertain} onClick={() => choose('ausente')}>{labels.ausente}</button>
      </> : null}
      {actions.sobreturno ? <button disabled={busy || !!uncertain} onClick={() => choose('sobreturno')}>{labels.sobreturno}</button> : null}
      <button className="secondary" onClick={() => {
        setHistory(null)
        void read('/turnos/' + id + '/historial', value => {
          if (!Array.isArray(value) || !value.every(isHistory)) throw new Error('Historial inválido')
          setHistory(value)
        })
      }}>Ver historial</button>
    </div>
    {message ? <Notice>{message}</Notice> : null}
    {uncertain && !busy ? <button className="secondary" onClick={() => void read('/turnos/' + id + '/gestion', value => {
      if (matchesTurn(value, id, uncertain)) {
        onUncertain(id)
        setAction(null)
        setMessage('El servidor muestra el estado solicitado.')
        onChanged()
      } else setMessage('El estado consultado no confirma la operación. El turno sigue bloqueado para cambios.')
    })}>Consultar estado del turno</button> : null}
    {action ? <form noValidate aria-label={labels[action]} onSubmit={event => { event.preventDefault(); void write() }}>
      <fieldset disabled={busy || !!uncertain}>
        <legend>{labels[action]}</legend>
        {action === 'confirmar' ? <p>El turno quedará confirmado. La confirmación no registra un cobro.</p> : null}
        {action === 'cancelar' ? <p className="staff-cancel-warning">Cancelar libera el horario. El servidor comprueba que el turno siga dentro de la ventana permitida.</p> : null}
        {action === 'asistido' || action === 'ausente' || action === 'sobreturno'
          ? <label>Motivo<input value={reason} onChange={event => setReason(event.target.value)} maxLength={200} required /></label> : null}
        {action === 'reprogramar' ? <>
          <label>Nueva fecha<input type="date" value={day} onChange={event => { reader.current?.abort(); setDay(event.target.value); setSlots([]); setChair(''); setChosen(null) }} required /></label>
          <button type="button" className="secondary" disabled={!day} onClick={() => void read('/horarios-libres', value => {
            if (!Array.isArray(value) || !value.every(isSlot)) throw new Error('Horarios inválidos')
            setSlots(value)
            setChair('')
            setChosen(null)
            if (!value.length) setMessage('No hay horarios disponibles para la fecha.')
          }, { fecha: day, tratamiento: treatmentId })}>Buscar horarios</button>
          <label>Nuevo sillón<select value={chair} onChange={event => { setChair(event.target.value); setChosen(null) }}>
            <option value="">Todos los sillones</option>
            {[...new Set(slots.map(slot => slot.sillon_id))].map(id => <option key={id} value={id}>{chairName(id)}</option>)}
          </select></label>
          <p>El turno original se conserva hasta que el servidor confirme el cambio.</p>
          <ul>{slots.filter(slot => !chair || slot.sillon_id === chair).map(slot => <li key={slot.sillon_id + slot.inicio}>
            <button type="button" className="secondary" aria-pressed={chosen === slot} onClick={() => setChosen(slot)}>{dateTime(slot.inicio)} · {chairName(slot.sillon_id)}</button>
          </li>)}</ul>
          {chosen ? <section aria-label="Nuevo horario seleccionado"><h4>Confirmar nuevo horario</h4><p>{dateTime(chosen.inicio)}–{hour(chosen.fin)} · {chairName(chosen.sillon_id)}</p></section> : null}
        </> : null}
        <button className={action === 'cancelar' ? 'staff-cancel-button' : undefined} disabled={action === 'reprogramar' && !chosen}>Aplicar cambio</button>
        <button type="button" className="secondary" onClick={() => setAction(null)}>Volver</button>
      </fieldset>
    </form> : null}
    {history ? <section aria-label="Historial del turno">
      <h4>Historial del turno</h4>
      {!history.length ? <p>No hay acciones registradas para este turno.</p> : <ol>{history.map(entry => <li key={entry.id}>
        <time dateTime={entry.fecha}>{dateTime(entry.fecha)}</time> · {entry.accion} · {entry.origen}
        {entry.actor_id ? ' · Actor ' + entry.actor_id : ' · Sistema'}{entry.motivo ? ' · ' + entry.motivo : ''}
      </li>)}</ol>}
      <button className="secondary" onClick={() => setHistory(null)}>Ocultar historial</button>
    </section> : null}
  </>
}
