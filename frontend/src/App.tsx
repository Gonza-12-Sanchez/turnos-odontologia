import { BrowserRouter, Link, NavLink, Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { useState } from 'react'
import { useSession } from './features/auth/context'
import { SessionProvider } from './features/auth/SessionProvider'
import AuthPage from './features/auth/AuthPage'
import Schedule from './features/reserva/Schedule'
import type { UnverifiedBooking } from './features/reserva/Schedule'
import PaymentReturn from './features/reserva/PaymentReturn'
import MyReservations from './features/mis-reservas/MyReservations'
import PwaUpdate from './shared/PwaUpdate'
import { Notice } from './shared/ui'
import { useOnline } from './shared/network'
import RoleGuard from './features/auth/RoleGuard'
import ConfigPage from './features/config/ConfigPage'
import AgendaPage from './features/agenda/AgendaPage'
import type { ExpectedTurn } from './features/agenda/TurnActions'
import CollectionsPage from './features/cobros/CollectionsPage'
import type { CollectionSelection, PendingCollection } from './features/cobros/CollectionsPage'
import { useConfigWriteGuard } from './features/config/writeGuard'

function PatientOnly({ children }: { children: React.ReactNode }) {
  const { status, user, session } = useSession()
  const location = useLocation()
  if (status === 'loading') return <p role="status">Restaurando sesion...</p>
  if (status === 'unavailable') return <section><Notice>No se pudo verificar la sesion.</Notice><button onClick={() => void session.restore()}>Reintentar sesion</button></section>
  if (!user) return <Navigate to={`/login?returnTo=${encodeURIComponent(location.pathname + location.search)}`} replace />
  if (user.rol !== 'paciente') return <Notice>Esta area es solo para pacientes. No modifica los permisos de tu cuenta.</Notice>
  return children
}
function Layout() {
  const { session, user, message } = useSession()
  const online = useOnline()
  const isStaff = user?.rol === 'secretaria' || user?.rol === 'odontologo'
  const [recovery, setRecovery] = useState<UnverifiedBooking | null>(null)
  const configWrites = useConfigWriteGuard()
  const navigate = useNavigate()
  const [uncertainTurns, setUncertainTurns] = useState<Record<string, ExpectedTurn>>({})
  function setUncertainTurn(id: string, expected?: ExpectedTurn) {
    setUncertainTurns(current => {
      const next = { ...current }
      if (expected) next[id] = expected
      else delete next[id]
      return next
    })
  }
  const [collection, setCollection] = useState<CollectionSelection | null>(null)
  const [pendingCollection, setPendingCollection] = useState<PendingCollection | null>(null)
  function selectCollection(selection: CollectionSelection) {
    if (!pendingCollection) setCollection(selection)
    navigate('/cobros')
  }
  return <>
    <a className="skip-link" href="#contenido">Saltar al contenido</a>
    <header className={`site-header${isStaff ? ' staff-header' : ''}`}><Link className="brand" to="/">Turnos odontologia{isStaff ? <small className="staff-brand-note">Identidad comercial provisional (TBD)</small> : null}</Link><nav aria-label="Principal">
      {isStaff ? <><NavLink to="/agenda">Agenda</NavLink>{user.rol === 'secretaria' ? <><NavLink to="/cobros">Cobros</NavLink><NavLink to="/config">Configuración</NavLink></> : null}</> : <><Link to="/horarios">Horarios</Link><Link to="/mis-reservas">Mis reservas</Link></>}
      {user ? <button className="secondary" onClick={() => void session.logout()}>Cerrar sesion</button> : <Link to="/login">Ingresar</Link>}
    </nav>{isStaff ? <span className="staff-role">{user.rol === 'secretaria' ? 'Secretaria' : 'Odontólogo'}</span> : null}</header>
    <main id="contenido" className={isStaff ? 'staff-main' : undefined}>
      {!online ? <Notice>Sin conexion. No hay disponibilidad actual ni acciones habilitadas. No se enviaran reservas al reconectar.</Notice> : null}
      {message ? <Notice>{message}</Notice> : null}
      <Routes>
        <Route path="/" element={<section className="welcome"><h1>Tu proximo turno, a tu ritmo.</h1><p>Consulta los horarios del consultorio. Elegi tratamiento y fecha, y luego ingresa para reservar.</p><Link className="button" to="/horarios">Ver horarios</Link><p className="muted">Consultar horarios no requiere una cuenta.</p></section>} />
        <Route path="/login" element={<AuthPage key="login" />} />
        <Route path="/registro" element={<AuthPage key="registro" register />} />
        <Route path="/horarios" element={<Schedule recovery={recovery} onRecoveryChange={setRecovery} />} />
        <Route path="/mis-reservas" element={<PatientOnly><MyReservations key={user?.id} /></PatientOnly>} />
        <Route path="/pagos/retorno" element={<PatientOnly><PaymentReturn key={user?.id} /></PatientOnly>} />
        <Route path="/agenda" element={<RoleGuard roles={['secretaria', 'odontologo']}><AgendaPage onCollect={user?.rol === 'secretaria' ? selectCollection : undefined} uncertain={uncertainTurns} onUncertain={setUncertainTurn} /></RoleGuard>} />
        <Route path="/config" element={<RoleGuard roles={['secretaria']}><ConfigPage writes={configWrites} /></RoleGuard>} />
        <Route path="/cobros" element={<RoleGuard roles={['secretaria']}><CollectionsPage key={collection?.id} selection={collection} pending={pendingCollection} onPending={setPendingCollection} /></RoleGuard>} />
        <Route path="*" element={<section><h1>Pagina no encontrada</h1><Link to="/">Volver al inicio</Link></section>} />
      </Routes>
    </main><footer>Horarios en Argentina. Las reservas y sus cambios se verifican en el servidor.</footer><PwaUpdate />
  </>
}
function AccountLayout() {
  const { user } = useSession()
  return <Layout key={user?.id ?? 'public'} />
}
export default function App() {
  return <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}><SessionProvider><AccountLayout /></SessionProvider></BrowserRouter>
}
