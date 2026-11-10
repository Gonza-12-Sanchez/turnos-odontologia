import { BrowserRouter, Link, Navigate, Route, Routes, useLocation } from 'react-router-dom'
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
  const [recovery, setRecovery] = useState<UnverifiedBooking | null>(null)
  return <>
    <a className="skip-link" href="#contenido">Saltar al contenido</a>
    <header className="site-header"><Link className="brand" to="/">Turnos odontologia</Link><nav aria-label="Principal">
      <Link to="/horarios">Horarios</Link><Link to="/mis-reservas">Mis reservas</Link>
      {user ? <button className="secondary" onClick={() => void session.logout()}>Cerrar sesion</button> : <Link to="/login">Ingresar</Link>}
    </nav></header>
    <main id="contenido">
      {!online ? <Notice>Sin conexion. No hay disponibilidad actual ni acciones habilitadas. No se enviaran reservas al reconectar.</Notice> : null}
      {message ? <Notice>{message}</Notice> : null}
      <Routes>
        <Route path="/" element={<section className="welcome"><h1>Tu proximo turno, a tu ritmo.</h1><p>Consulta los horarios del consultorio. Elegi tratamiento y fecha, y luego ingresa para reservar.</p><Link className="button" to="/horarios">Ver horarios</Link><p className="muted">Consultar horarios no requiere una cuenta.</p></section>} />
        <Route path="/login" element={<AuthPage key="login" />} />
        <Route path="/registro" element={<AuthPage key="registro" register />} />
        <Route path="/horarios" element={<Schedule recovery={recovery} onRecoveryChange={setRecovery} />} />
        <Route path="/mis-reservas" element={<PatientOnly><MyReservations key={user?.id} /></PatientOnly>} />
        <Route path="/pagos/retorno" element={<PatientOnly><PaymentReturn key={user?.id} /></PatientOnly>} />
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
