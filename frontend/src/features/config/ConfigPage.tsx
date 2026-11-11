import { useEffect, useState } from 'react'
import { useSession } from '../auth/context'
import { ars } from '../reserva/payments'
import { Notice } from '../../shared/ui'
import { useOnline } from '../../shared/network'
import { dateTime } from '../../shared/time'
import { readPage } from './contracts'
import type { Entry, Page, Resource } from './contracts'
import type { Chair, Treatment } from './contracts'
import TreatmentEditor from './TreatmentEditor'
import ChairEditor from './ChairEditor'
import type { ConfigWriteGuard } from './writeGuard'

const labels: Record<Resource, string> = { tratamientos: 'Tratamientos', sillones: 'Sillones', bloqueos: 'Bloqueos' }
function ConfigList({ resource, page, active, onPage, retry, writes }: { resource: Resource; page: number; active: boolean; onPage: (page: number) => void; retry: () => void; writes: ConfigWriteGuard }) {
  const { session } = useSession()
  const [result, setResult] = useState<Page<Entry> | null>(null)
  const [error, setError] = useState(false)
  const [editing, setEditing] = useState<Treatment | 'new' | null>(null)
  const [editingChair, setEditingChair] = useState<Chair | null>(null)
  const [saved, setSaved] = useState('')
  const [readRevision, setReadRevision] = useState(0)
  useEffect(() => {
    const controller = new AbortController()
    let current = true
    void session.get<unknown>(`/api/config/${resource}`, { query: { page: String(page), page_size: '20', activo: String(active) }, signal: controller.signal })
      .then(value => readPage(value, resource, page, active))
      .then(data => { if (current) setResult(data) })
      .catch(() => { if (current) setError(true) })
    return () => { current = false; controller.abort() }
  }, [session, resource, page, active, readRevision])
  if (error) return <><Notice>No se pudo consultar la configuración. No se puede afirmar que esté vacía.</Notice><button className="secondary" onClick={retry}>Reintentar consulta</button></>
  if (!result) return <p role="status">Consultando recursos…</p>
  const editor = editing ? <TreatmentEditor key={editing === 'new' ? 'new' : editing.id} item={editing === 'new' ? null : editing} writes={writes} onCancel={() => setEditing(null)} onSaved={item => {
    if (editing === 'new') {
      setEditing(null); setSaved('Tratamiento creado.'); setResult(null); setReadRevision(value => value + 1); return
    }
    setResult({ ...result, items: result.items.map(entry => entry.resource === 'tratamientos' && entry.item.id === item.id ? { resource: 'tratamientos', item } : entry) })
    setEditing(null); setSaved('Tratamiento actualizado.')
  }} /> : editingChair ? <ChairEditor key={editingChair.id} item={editingChair} writes={writes} onCancel={() => setEditingChair(null)} onSaved={item => {
    if (item.activo !== editingChair.activo) {
      setEditingChair(null); setSaved(`Sillón ${item.activo ? 'reactivado' : 'desactivado'}. Los históricos se conservan.`); setResult(null); setReadRevision(value => value + 1); return
    }
    setResult({ ...result, items: result.items.map(entry => entry.resource === 'sillones' && entry.item.id === item.id ? { resource: 'sillones', item } : entry) })
    setEditingChair(null); setSaved('Sillón actualizado.')
  }} /> : null
  return <>
    {saved ? <p role="status">{saved}</p> : null}
    {resource === 'tratamientos' ? <button disabled={writes.state !== 'idle'} onClick={() => { setSaved(''); setEditing('new') }}>Agregar tratamiento</button> : null}
    <div className={editor ? 'staff-config-split' : undefined}><div>
    <ul className="staff-catalog-list">{result.items.map(entry => <li key={entry.item.id}>
      <div className="staff-catalog-details">
      <h2>{entry.resource === 'bloqueos' ? entry.item.motivo : entry.item.nombre}</h2>
      {entry.resource === 'tratamientos' ? <p>{entry.item.duracion_min} min · {entry.item.precio_referencia_centavos === null ? 'Precio sin referencia' : ars(entry.item.precio_referencia_centavos)}</p> : entry.resource === 'bloqueos' ? <p>{entry.item.sillon_id === null ? 'Todos los sillones' : 'Sillón específico'} · {dateTime(entry.item.desde)} – {dateTime(entry.item.hasta)} · horario Argentina</p> : null}
      <span className="state">{entry.item.activo ? 'Activo' : 'Inactivo'}</span>
      </div>
      {entry.resource === 'tratamientos' ? <button className="secondary" disabled={writes.state !== 'idle'} aria-label={`Editar ${entry.item.nombre}`} onClick={() => { setSaved(''); setEditing(entry.item) }}>Editar</button> : null}
      {entry.resource === 'sillones' ? <button className="secondary" disabled={writes.state !== 'idle'} aria-label={`Editar ${entry.item.nombre}`} onClick={() => { setSaved(''); setEditingChair(entry.item) }}>Editar</button> : null}
    </li>)}</ul>
    {!result.items.length ? <p>No hay {resource} {active ? 'activos' : 'inactivos'} para esta consulta.</p> : null}
    <div className="staff-pagination"><small>Página {page} · {result.total} registros</small><div className="actions"><button className="secondary" disabled={page <= 1} onClick={() => onPage(page - 1)}>Anterior</button><button className="secondary" disabled={page * result.page_size >= result.total} onClick={() => onPage(page + 1)}>Siguiente</button></div></div>
    </div>{editor}</div>
  </>
}
export default function ConfigPage({ writes }: { writes: ConfigWriteGuard }) {
  const online = useOnline()
  const [resource, setResource] = useState<Resource>('tratamientos')
  const [active, setActive] = useState(true)
  const [draftActive, setDraftActive] = useState('true')
  const [page, setPage] = useState(1)
  const [revision, setRevision] = useState(0)
  return <section><h1>Configuración</h1><p>Administración del consultorio · solo secretaria</p>
    {writes.state !== 'idle' ? <Notice>{writes.state === 'pending' ? 'Hay una escritura de configuración pendiente. No se permiten más cambios mientras se verifica.' : 'Cambios de configuración bloqueados: resultado no verificado. Consulta el recurso y solicita conciliación; una lectura no prueba que la escritura no se aplicó.'}</Notice> : null}
    <div className="staff-resource-tabs" role="group" aria-label="Recursos">{(Object.keys(labels) as Resource[]).map(key => <button className="secondary" key={key} aria-pressed={resource === key} onClick={() => { setResource(key); setPage(1) }}>{labels[key]}</button>)}</div><form className="staff-filters" onSubmit={event => { event.preventDefault(); setActive(draftActive === 'true'); setPage(1); setRevision(value => value + 1) }}><label>Mostrar<select value={draftActive} onChange={event => setDraftActive(event.target.value)}><option value="true">Activos</option><option value="false">Inactivos</option></select></label><button className="secondary" disabled={!online}>Consultar</button></form>{online ? <ConfigList key={`${resource}:${active}:${page}:${revision}`} resource={resource} active={active} page={page} onPage={setPage} retry={() => setRevision(value => value + 1)} writes={writes} /> : <Notice>Sin conexión. No hay configuración privada guardada en este dispositivo.</Notice>}</section>
}
