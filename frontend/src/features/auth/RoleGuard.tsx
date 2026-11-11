import { Navigate, useLocation } from 'react-router-dom'
import { useSession } from './context'
import { Notice } from '../../shared/ui'

export default function RoleGuard({ roles, children }: { roles: readonly string[]; children: React.ReactNode }) {
  const { status, user, session } = useSession()
  const location = useLocation()
  if (status === 'loading') return <p role="status">Restaurando sesion...</p>
  if (status === 'unavailable') return <section><Notice>No se pudo verificar la sesion.</Notice><button onClick={() => void session.restore()}>Reintentar sesion</button></section>
  if (!user) return <Navigate to={`/login?returnTo=${encodeURIComponent(location.pathname + location.search)}`} replace />
  if (!roles.includes(user.rol)) return <Notice>Tu cuenta no tiene acceso a esta sección del consultorio.</Notice>
  return children
}
