import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { ApiError } from '../../shared/api/client'
import { Notice } from '../../shared/ui'
import { errorMessage, useOnline } from '../../shared/network'
import { useSession } from './context'

function safeReturn(value: string | null, rol?: string) {
  const staff = rol === 'secretaria' || rol === 'odontologo'
  const fallback = staff ? '/agenda' : '/mis-reservas'
  if (!value || !/^\/(horarios|mis-reservas|pagos\/retorno|agenda|config|cobros)(\?|$)/.test(value) || value.includes('\\') || [...value].some(char => char.charCodeAt(0) < 32 || char.charCodeAt(0) === 127)) return fallback
  const url = new URL(value, window.location.origin)
  const permitted = rol === undefined
    ? ['/horarios', '/mis-reservas', '/pagos/retorno', '/agenda', '/config', '/cobros']
    : rol === 'secretaria' ? ['/horarios', '/agenda', '/config', '/cobros']
      : rol === 'odontologo' ? ['/horarios', '/agenda'] : ['/horarios', '/mis-reservas', '/pagos/retorno']
  return url.origin === window.location.origin && permitted.includes(url.pathname) ? url.pathname + url.search : fallback
}
export default function AuthPage({ register = false }: { register?: boolean }) {
  const { session } = useSession()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [created, setCreated] = useState(false)
  const [email, setEmail] = useState('')
  const online = useOnline()
  const destination = safeReturn(params.get('returnTo'))
  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (busy || !online) return
    const form = event.currentTarget
    const data = new FormData(form)
    setBusy(true); setError('')
    try {
      const password = String(data.get('password'))
      if (register && !created) {
        await session.api.post('/auth/registro', { email, password, nombre: data.get('nombre'), telefono: data.get('telefono') })
        form.reset(); setCreated(true)
      } else {
        await session.login(email, password)
        const currentUser = session.snapshot().user
        if (!currentUser) return
        form.reset(); navigate(safeReturn(params.get('returnTo'), currentUser.rol), { replace: true })
      }
    } catch (e) {
      setError(e instanceof ApiError && e.status === 401 ? 'Email o contrasena incorrectos.' : e instanceof ApiError && e.status === 409 ? 'No se pudo crear la cuenta. Intenta ingresar o usa otro email.' : errorMessage(e))
    } finally { setBusy(false) }
  }
  const registration = register && !created
  return <section className="auth-page">
    <h1>{registration ? 'Crear cuenta' : 'Ingresar'}</h1>
    {created ? <p role="status">Cuenta creada. Ingresa con tu email y contrasena.</p> : <p>Tu cuenta te permite reservar y consultar tus turnos.</p>}
    <form onSubmit={submit} aria-busy={busy}>
      {registration ? <label>Nombre<input name="nombre" autoComplete="name" required maxLength={120} /></label> : null}
      <label>Email<input name="email" type="email" autoComplete="username" value={email} onChange={e => setEmail(e.target.value)} required maxLength={254} /></label>
      {registration ? <><label>Telefono argentino<input name="telefono" type="tel" autoComplete="tel" required aria-describedby="phone-help" /></label><small id="phone-help">Inclui codigo de pais +54 y codigo de area.</small></> : null}
      <label>Contrasena<input name="password" type="password" autoComplete={registration ? 'new-password' : 'current-password'} required minLength={registration ? 8 : undefined} aria-describedby={registration ? 'password-help' : undefined} /></label>
      {registration ? <small id="password-help">Minimo 8 caracteres, una letra y un numero. Maximo 72 bytes UTF-8.</small> : null}
      {error ? <Notice>{error}</Notice> : null}
      <button disabled={busy || !online}>{busy ? 'Enviando...' : registration ? 'Crear cuenta' : 'Ingresar'}</button>
    </form>
    <Link to={`${registration ? '/login' : '/registro'}?returnTo=${encodeURIComponent(destination)}`}>{registration ? 'Ya tengo cuenta' : 'Crear una cuenta'}</Link>
  </section>
}
