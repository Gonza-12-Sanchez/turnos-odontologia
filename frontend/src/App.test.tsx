// @vitest-environment jsdom
import { afterEach, expect, it, vi } from 'vitest'
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from './App'

const patient = { id: 'p1', rol: 'paciente', nombre: 'Paciente ficticio' }
const catalog = { sillones: [{ id: 's1', nombre: 'Sillon Norte' }, { id: 's2', nombre: 'Sillon Sur' }], tratamientos: [
  { id: 't1', nombre: 'Control', duracion_min: 15, sena_politica: 'deshabilitada', sena_centavos: null },
  { id: 't2', nombre: 'Limpieza', duracion_min: 30, sena_politica: 'deshabilitada', sena_centavos: null },
] }
const slot = { sillon_id: 's1', inicio: '2026-11-10T12:00:00Z', fin: '2026-11-10T12:15:00Z' }
const calls: { path: string; url: string; init: RequestInit }[] = []
function backend(handler?: (path: string, init: RequestInit) => Response | undefined | Promise<Response | undefined>) {
  // jsdom has no Web Locks. Model the browser primitive; browser tests use native locks.
  let queue = Promise.resolve()
  Object.defineProperty(navigator, 'locks', { configurable: true, value: {
    request: (_name: string, operation: () => Promise<void>) => {
      const pending = queue.then(operation)
      queue = pending.catch(() => {})
      return pending
    },
  } })
  vi.stubGlobal('fetch', vi.fn(async (input: string, init: RequestInit) => {
    const path = new URL(input, 'http://localhost').pathname
    calls.push({ path, url: input, init })
    const response = await handler?.(path, init)
    if (response) return response
    if (path === '/auth/refresh') return Response.json({}, { status: 401 })
    if (path === '/auth/login') return Response.json({ access_token: 'memory-only' })
    if (path === '/auth/me') return Response.json(patient)
    if (path === '/mis-reservas') return Response.json([])
    if (path === '/catalogo-publico') return Response.json(catalog)
    if (path === '/horarios-libres') return Response.json([slot])
    throw new Error(`Unexpected HTTP ${path}`)
  }))
}
function open(path: string) { window.history.replaceState(null, '', path); render(<App />) }
afterEach(() => { cleanup(); Reflect.deleteProperty(navigator, 'locks'); calls.length = 0; vi.unstubAllGlobals(); vi.unstubAllEnvs(); vi.useRealTimers() })

it.each(['/mis-reservas', '/pagos/retorno?intento_id=ficticio'])('protege %s sin cargar datos privados', async (path) => {
  backend()
  open(path)
  expect(await screen.findByRole('heading', { name: 'Ingresar' })).toBeTruthy()
  expect(calls.some(c => c.path === '/mis-reservas' || c.path.startsWith('/pagos/sena'))).toBe(false)
})
it.each(['https://evil.test', '//evil.test', '/agenda', '/horarios\\evil.test', '/horarios?next=\\evil.test'])('rechaza returnTo %s tras login explicito', async (returnTo) => {
  backend()
  open(`/login?returnTo=${encodeURIComponent(returnTo)}`)
  await screen.findByRole('heading', { name: 'Ingresar' })
  const user = userEvent.setup()
  await user.type(screen.getByLabelText('Email'), 'paciente@example.test')
  await user.type(screen.getByLabelText('Contrasena'), 'Ficticia123')
  await user.click(screen.getByRole('button', { name: 'Ingresar' }))
  expect(await screen.findByRole('heading', { name: 'Mis reservas' })).toBeTruthy()
  expect(calls.some(c => c.path === '/turnos')).toBe(false)
  expect(localStorage.length).toBe(0)
  expect(sessionStorage.length).toBe(0)
})
it.each([401, 429])('login %s informa sin crear sesion', async (status) => {
  backend(path => path === '/auth/login' ? Response.json({}, { status }) : undefined)
  open('/login')
  const user = userEvent.setup()
  await user.type(await screen.findByLabelText('Email'), 'paciente@example.test')
  await user.type(screen.getByLabelText('Contrasena'), 'Incorrecta123')
  await user.click(screen.getByRole('button', { name: 'Ingresar' }))
  expect((await screen.findByRole('alert')).textContent).toMatch(status === 401 ? /email o contrasena/i : /demasiados intentos/i)
  expect(calls.some(c => c.path === '/auth/me')).toBe(false)
})
it('registro crea cuenta pero requiere login y descarta password', async () => {
  backend(path => path === '/auth/registro' ? Response.json(patient, { status: 201 }) : undefined)
  open('/registro')
  const user = userEvent.setup()
  await user.type(await screen.findByLabelText('Nombre'), 'Paciente ficticio')
  await user.type(screen.getByLabelText('Email'), 'paciente@example.test')
  await user.type(screen.getByLabelText('Telefono argentino'), '+5491100000000')
  await user.type(screen.getByLabelText('Contrasena'), 'Ficticia123')
  await user.click(screen.getByRole('button', { name: 'Crear cuenta' }))
  expect(await screen.findByText(/Cuenta creada/)).toBeTruthy()
  expect(calls.some(c => c.path === '/auth/login')).toBe(false)
  expect((screen.getByLabelText('Contrasena') as HTMLInputElement).value).toBe('')
})
it.each(['/desconocido', '/agenda'])('404 navegable %s no crea area administrativa', async (path) => {
  backend(); open(path)
  expect(await screen.findByRole('heading', { name: 'Pagina no encontrada' })).toBeTruthy()
  expect(screen.getByRole('link', { name: 'Volver al inicio' })).toBeTruthy()
})
it('otro rol no consulta reservas propias de paciente', async () => {
  backend(path => path === '/auth/refresh' ? Response.json({ access_token: 'staff' }) : path === '/auth/me' ? Response.json({ id: 's1', rol: 'secretaria' }) : undefined)
  open('/mis-reservas')
  await waitFor(() => expect(screen.getByText(/area es solo para pacientes/i)).toBeTruthy())
  expect(calls.some(c => c.path === '/mis-reservas')).toBe(false)
})

it.each(['t1', 't2'])('horarios publicos usan catalogo real para tratamiento %s', async (id) => {
  backend(); open('/horarios?fecha=2026-11-10')
  const user = userEvent.setup()
  await user.selectOptions(await screen.findByLabelText('Tratamiento'), id)
  expect(await screen.findByRole('button', { name: /09:00.*Sillon Norte/ })).toBeTruthy()
  expect(screen.getByText(/America\/Argentina\/Buenos_Aires/)).toBeTruthy()
  expect(calls.find(c => c.path === '/horarios-libres')?.init.headers).not.toHaveProperty('Authorization')
})
it.each([true, false])('distingue catalogo vacio de fallo sin inventar filtros %s', async (empty) => {
  backend(path => path === '/catalogo-publico' ? Response.json(empty ? { sillones: [], tratamientos: [] } : {}, { status: empty ? 200 : 503 }) : undefined)
  open('/horarios')
  expect(await screen.findByText(empty ? /No hay tratamientos disponibles/ : /No se pudo cargar el catalogo/)).toBeTruthy()
  expect(screen.queryByRole('option', { name: /Control/ })).toBeNull()
})
it('anonimo conserva seleccion al ingresar y no envia reserva solo por login', async () => {
  backend(); open('/horarios?fecha=2026-11-10&tratamiento=t1')
  const user = userEvent.setup()
  await user.click(await screen.findByRole('button', { name: /09:00.*Sillon Norte/ }))
  await user.click(screen.getByRole('button', { name: 'Ingresar para reservar' }))
  await user.type(await screen.findByLabelText('Email'), 'paciente@example.test')
  await user.type(screen.getByLabelText('Contrasena'), 'Ficticia123')
  await user.click(screen.getByRole('button', { name: 'Ingresar' }))
  expect(await screen.findByRole('button', { name: 'Reservar turno' })).toBeTruthy()
  expect(calls.filter(c => c.path === '/horarios-libres').length).toBeGreaterThanOrEqual(2)
  expect(calls.some(c => c.path === '/turnos')).toBe(false)
})
it.each([{ alternativas: [] }, { alternativas: [{ ...slot, inicio: '2026-11-10T13:00:00Z', fin: '2026-11-10T13:15:00Z' }] }])('409 ofrece nueva eleccion sin reserva automatica %j', async ({ alternativas }) => {
  backend(path => path === '/auth/refresh' ? Response.json({ access_token: 't' }) : path === '/turnos' ? Response.json({ detail: 'Ocupado', alternativas }, { status: 409 }) : undefined)
  open('/horarios?fecha=2026-11-10&tratamiento=t1')
  const user = userEvent.setup()
  await user.click(await screen.findByRole('button', { name: /09:00.*Sillon Norte/ }))
  await user.click(screen.getByRole('button', { name: 'Reservar turno' }))
  expect(await screen.findByText(/El horario se ocupo/)).toBeTruthy()
  if (alternativas.length) await user.click(screen.getByRole('button', { name: /10:00.*Sillon Norte/ }))
  else expect(screen.getByText(/Cambia la fecha o los filtros/)).toBeTruthy()
  expect(calls.filter(c => c.path === '/turnos')).toHaveLength(1)
})
it('201 muestra datos servidor y red perdida no reenvia POST', async () => {
  let fail = false
  backend(path => {
    if (path === '/auth/refresh') return Response.json({ access_token: 't' })
    if (path === '/turnos') {
      if (fail) throw new TypeError('network lost')
      return Response.json({ ...slot, id: 'r1', estado: 'reservado', tolerancia_min: 5 }, { status: 201 })
    }
  })
  open('/horarios?fecha=2026-11-10&tratamiento=t1')
  const user = userEvent.setup()
  await user.click(await screen.findByRole('button', { name: /09:00.*Sillon Norte/ }))
  await user.click(screen.getByRole('button', { name: 'Reservar turno' }))
  expect(await screen.findByText(/Reserva registrada/)).toBeTruthy()
  fail = true
  await user.click(screen.getByRole('button', { name: /09:00.*Sillon Norte/ }))
  await user.click(screen.getByRole('button', { name: 'Reservar turno' }))
  expect(await screen.findByText(/Resultado no verificado/)).toBeTruthy()
  expect(calls.filter(c => c.path === '/turnos')).toHaveLength(2)
  expect((screen.getByRole('button', { name: 'Reservar turno' }) as HTMLButtonElement).disabled).toBe(true)
})

const attemptId = '11111111-1111-4111-8111-111111111111'
it.each(['opcional', 'obligatoria'])('sena %s obtiene 402 con consentimiento, monto servidor e idempotencia', async (policy) => {
  vi.stubEnv('VITE_ENABLE_TEST_PAYMENTS', 'true')
  backend(path => {
    if (path === '/auth/refresh') return Response.json({ access_token: 't' })
    if (path === '/catalogo-publico') return Response.json({ ...catalog, tratamientos: [{ ...catalog.tratamientos[0], sena_politica: policy, sena_centavos: 123456 }] })
    if (path === '/turnos') return Response.json({ checkout: { provider: 'mercadopago', status: 'pendiente', intento_id: attemptId, checkout_url: `https://sandbox.mercadopago.com.ar/checkout/v1/redirect?pref_id=test`, expires_at: '2099-11-10T12:00:00Z', monto_centavos: 123456, moneda: 'ARS', modo: 'sandbox' } }, { status: 402 })
  })
  open('/horarios?fecha=2026-11-10&tratamiento=t1')
  const user = userEvent.setup()
  await user.click(await screen.findByRole('button', { name: /09:00.*Sillon Norte/ }))
  const consent = screen.getByRole('checkbox', { name: /Acepto la sena/ })
  if (policy === 'obligatoria') expect((screen.getByRole('button', { name: 'Reservar turno' }) as HTMLButtonElement).disabled).toBe(true)
  await user.click(consent)
  await user.click(screen.getByRole('button', { name: 'Reservar turno' }))
  const link = await screen.findByRole('link', { name: 'Continuar al checkout de prueba' })
  expect(link.getAttribute('href')).toContain('https://sandbox.mercadopago.com.ar/')
  expect(screen.getByText(/El horario se verifica al aprobar el pago/)).toBeTruthy()
  expect(screen.getByText(/1.234,56/)).toBeTruthy()
  const request = calls.find(c => c.path === '/turnos')
  expect(request?.init.headers).toHaveProperty('Idempotency-Key')
  expect(JSON.parse(String(request?.init.body))).toMatchObject({ sena: true })
})
it.each(['pendiente', 'requiere_revision', 'rechazado', 'expirado', 'aprobado'])('retorno ignora approved en URL y muestra estado servidor %s', async (estado) => {
  backend(path => path === '/auth/refresh' ? Response.json({ access_token: 't' }) : path === `/pagos/sena/${attemptId}` ? Response.json({ id: attemptId, estado, turno_id: estado === 'aprobado' ? 'r1' : null, monto_centavos: 123456, moneda: 'ARS', expires_at: '2099-11-10T12:00:00Z', requiere_contacto: estado === 'requiere_revision' }) : undefined)
  open(`/pagos/retorno?intento_id=${attemptId}&status=approved&payment_id=FAKE`)
  const expected = { pendiente: /Pago pendiente/, requiere_revision: /reserva no confirmada.*contacta/i, rechazado: /Pago rechazado/, expirado: /Pago expirado/, aprobado: /Reserva registrada/ }[estado]
  expect(await screen.findByText(expected!)).toBeTruthy()
  if (estado !== 'aprobado') expect(screen.queryByText(/Reserva registrada/)).toBeNull()
  expect(calls.some(c => c.init.method === 'POST' && c.path !== '/auth/refresh')).toBe(false)
})

const reservation = { ...slot, id: 'r1', tratamiento_id: 't1', tratamiento_nombre: 'Control ficticio', sillon_nombre: 'Sillon Norte', estado: 'reservado', tolerancia_min: 5, acciones: { confirmar: true, cancelar: true, reprogramar: true } }
it('Mis reservas vacio orienta a buscar horarios', async () => {
  backend(path => path === '/auth/refresh' ? Response.json({ access_token: 't' }) : undefined)
  open('/mis-reservas')
  expect(await screen.findByText(/Todavia no tenes reservas/)).toBeTruthy()
})
it.each(['confirmar', 'cancelar'])('Mis reservas %s actualiza desde servidor y cancelar exige consentimiento', async (action) => {
  let state = reservation.estado
  backend(path => {
    if (path === '/auth/refresh') return Response.json({ access_token: 't' })
    if (path === '/mis-reservas') return Response.json([{ ...reservation, estado: state, acciones: { ...reservation.acciones, confirmar: state === 'reservado', cancelar: state === 'reservado' } }])
    if (path === `/turnos/r1/${action}`) { state = action === 'confirmar' ? 'confirmado' : 'cancelado'; return Response.json({ ...reservation, estado: state }) }
  })
  open('/mis-reservas')
  const user = userEvent.setup()
  expect(await screen.findByText('Control ficticio')).toBeTruthy()
  expect(screen.getByText(/Tolerancia de llegada: 5 min/)).toBeTruthy()
  await user.click(screen.getByRole('button', { name: action === 'confirmar' ? 'Confirmar turno' : 'Cancelar turno' }))
  if (action === 'cancelar') {
    expect(calls.some(c => c.init.method === 'PATCH')).toBe(false)
    await user.click(screen.getByRole('button', { name: 'Si, cancelar turno' }))
  }
  expect(await screen.findByText(state)).toBeTruthy()
  expect(calls.find(c => c.path === `/turnos/r1/${action}`)?.init.method).toBe('PATCH')
  expect(screen.queryByRole('button', { name: /Reprogramar/ })).toBeNull()
})
it.each([false, true])('cancelacion denegada por acciones o 422 tardio %s explica ventana y no anuncia exito', async (late) => {
  backend(path => path === '/auth/refresh' ? Response.json({ access_token: 't' }) : path === '/mis-reservas' ? Response.json([{ ...reservation, acciones: { ...reservation.acciones, cancelar: late } }]) : path === '/turnos/r1/cancelar' ? Response.json({ detail: 'Ventana vencida' }, { status: 422 }) : undefined)
  open('/mis-reservas')
  await screen.findByText('Control ficticio')
  if (late) {
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: 'Cancelar turno' }))
    await user.click(screen.getByRole('button', { name: 'Si, cancelar turno' }))
  }
  expect(await screen.findByText(/minimo de 2 horas/)).toBeTruthy()
  expect(screen.queryByText('cancelado')).toBeNull()
})

it('logout desde checkout limpia el intento privado de la vista publica', async () => {
  vi.stubEnv('VITE_ENABLE_TEST_PAYMENTS', 'true')
  backend(path => path === '/auth/refresh' ? Response.json({ access_token: 't' }) : path === '/auth/logout' ? new Response(null, { status: 204 }) : path === '/turnos' ? Response.json({ checkout: { provider: 'mercadopago', status: 'pendiente', intento_id: attemptId, checkout_url: 'https://sandbox.mercadopago.com.ar/checkout/v1/redirect?pref_id=test', expires_at: '2099-11-10T12:00:00Z', monto_centavos: 123456, moneda: 'ARS', modo: 'sandbox' } }, { status: 402 }) : undefined)
  open('/horarios?fecha=2026-11-10&tratamiento=t1')
  const user = userEvent.setup()
  await user.click(await screen.findByRole('button', { name: /09:00.*Sillon Norte/ }))
  await user.click(screen.getByRole('button', { name: 'Reservar turno' }))
  expect(await screen.findByRole('region', { name: 'Checkout de prueba' })).toBeTruthy()
  await user.click(screen.getByRole('button', { name: 'Cerrar sesion' }))
  await waitFor(() => expect(screen.queryByRole('region', { name: 'Checkout de prueba' })).toBeNull())
})
it.each(['2026-11-11', '2026-11-12'])('filtro fecha %s y sillon no envia selecciones viejas', async (fecha) => {
  backend(); open('/horarios?fecha=2026-11-10&tratamiento=t1')
  await screen.findByRole('button', { name: /09:00/ })
  fireEvent.change(screen.getByLabelText('Fecha'), { target: { value: fecha } })
  await userEvent.setup().selectOptions(screen.getByLabelText('Sillon'), 's2')
  await waitFor(() => {
    const last = calls.filter(c => c.path === '/horarios-libres').at(-1)
    expect(new URL(last!.url, 'http://localhost').searchParams.get('fecha')).toBe(fecha)
    expect(new URL(last!.url, 'http://localhost').searchParams.get('sillon')).toBe('s2')
  })
})
it('respuesta vieja ignorada incluso si transporte no respeta abort', async () => {
  let resolve: (response: Response) => void = () => {}
  let query = 0
  backend(path => path === '/horarios-libres' && query++ === 0 ? new Promise<Response>(done => { resolve = done }) : path === '/horarios-libres' ? Response.json([{ ...slot, inicio: '2026-11-10T14:00:00Z', fin: '2026-11-10T14:15:00Z' }]) : undefined)
  open('/horarios?fecha=2026-11-10&tratamiento=t1')
  await waitFor(() => expect(query).toBe(1))
  await userEvent.setup().selectOptions(screen.getByLabelText('Tratamiento'), 't2')
  await screen.findByRole('button', { name: /11:00/ })
  await act(async () => { resolve(Response.json([slot])) })
  expect(screen.queryByRole('button', { name: /09:00/ })).toBeNull()
})
it.each([401, 403, 422, 503])('reserva %s no reintenta automaticamente ni afirma exito', async (status) => {
  backend(path => path === '/auth/refresh' ? Response.json({ access_token: 't' }) : path === '/turnos' ? Response.json({ detail: status === 422 ? [{ loc: ['body', 'inicio'], msg: 'Invalido' }] : 'Error' }, { status }) : undefined)
  open('/horarios?fecha=2026-11-10&tratamiento=t1')
  const user = userEvent.setup()
  await user.click(await screen.findByRole('button', { name: /09:00/ }))
  await user.click(screen.getByRole('button', { name: 'Reservar turno' }))
  expect(await screen.findByRole('alert')).toBeTruthy()
  expect(screen.queryByText(/Reserva registrada/)).toBeNull()
  expect(calls.filter(c => c.path === '/turnos')).toHaveLength(1)
})
it.each([
  ['2026-11-10T01:59:00Z', '2026-11-09'],
  ['2026-11-10T03:01:00Z', '2026-11-10'],
])('fecha inicial AR cerca de medianoche UTC %s es %s', async (utc, expected) => {
  vi.useFakeTimers({ toFake: ['Date'] }); vi.setSystemTime(new Date(utc))
  backend(); open('/horarios')
  expect((await screen.findByLabelText('Fecha') as HTMLInputElement).value).toBe(expected)
})
it.each([404, 503])('retorno %s informa sin crear un segundo intento', async status => {
  backend(path => path === '/auth/refresh' ? Response.json({ access_token: 't' }) : path === `/pagos/sena/${attemptId}` ? Response.json({}, { status }) : undefined)
  open(`/pagos/retorno?intento_id=${attemptId}&status=approved`)
  expect(await screen.findByRole('alert')).toBeTruthy()
  expect(screen.queryByText(/Reserva registrada/)).toBeNull()
  expect(calls.some(c => c.path === '/turnos' || c.path === '/pagos/sena')).toBe(false)
})
it.each([200, 204])('reserva exige 201 no muestra exito para respuesta %s', async status => {
  backend(path => path === '/auth/refresh' ? Response.json({ access_token: 't' }) : path === '/turnos' ? status === 204 ? new Response(null, { status }) : Response.json({ ...slot, id: 'r1', estado: 'reservado' }, { status }) : undefined)
  open('/horarios?fecha=2026-11-10&tratamiento=t1')
  const user = userEvent.setup()
  await user.click(await screen.findByRole('button', { name: /09:00/ }))
  await user.click(screen.getByRole('button', { name: 'Reservar turno' }))
  expect(await screen.findByText(/Resultado no verificado/)).toBeTruthy()
  expect(screen.queryByText(/Reserva registrada/)).toBeNull()
})
it('polling pendiente se acota a 60s y consulta manual no vuelve a cobrar', async () => {
  vi.useFakeTimers()
  backend(path => path === '/auth/refresh' ? Response.json({ access_token: 't' }) : path === `/pagos/sena/${attemptId}` ? Response.json({ id: attemptId, estado: 'pendiente', turno_id: null, monto_centavos: 100, moneda: 'ARS' }) : undefined)
  await act(async () => open(`/pagos/retorno?intento_id=${attemptId}`))
  expect(screen.getByText(/Pago pendiente/)).toBeTruthy()
  await act(async () => { await vi.advanceTimersByTimeAsync(61_000) })
  expect(calls.filter(c => c.path === `/pagos/sena/${attemptId}`)).toHaveLength(20)
  await act(async () => { await vi.advanceTimersByTimeAsync(61_000) })
  expect(calls.filter(c => c.path === `/pagos/sena/${attemptId}`)).toHaveLength(20)
  await act(async () => fireEvent.click(screen.getByRole('button', { name: 'Consultar estado' })))
  expect(calls.filter(c => c.path === `/pagos/sena/${attemptId}`)).toHaveLength(21)
  expect(calls.some(c => c.path === '/pagos/sena' || c.path === '/turnos')).toBe(false)
})
it.each(['aprobado', 'requiere_revision'])('polling se detiene ante terminal %s', async estado => {
  vi.useFakeTimers()
  backend(path => path === '/auth/refresh' ? Response.json({ access_token: 't' }) : path === `/pagos/sena/${attemptId}` ? Response.json({ id: attemptId, estado, turno_id: estado === 'aprobado' ? 'r1' : null, monto_centavos: 100, moneda: 'ARS' }) : undefined)
  await act(async () => open(`/pagos/retorno?intento_id=${attemptId}`))
  await act(async () => { await vi.advanceTimersByTimeAsync(61_000) })
  expect(calls.filter(c => c.path === `/pagos/sena/${attemptId}`)).toHaveLength(1)
})
it('checkout no verificado ofrece consulta de intento sin generar nueva preferencia', async () => {
  backend(path => path === '/auth/refresh' ? Response.json({ access_token: 't' }) : path === '/turnos' ? Response.json({ code: 'CHECKOUT_NO_VERIFICADO', intento_id: attemptId }, { status: 503 }) : undefined)
  open('/horarios?fecha=2026-11-10&tratamiento=t1')
  const user = userEvent.setup()
  await user.click(await screen.findByRole('button', { name: /09:00/ }))
  await user.click(screen.getByRole('button', { name: 'Reservar turno' }))
  expect(await screen.findByRole('link', { name: 'Consultar estado del intento' })).toBeTruthy()
  expect((screen.getByRole('button', { name: 'Reservar turno' }) as HTMLButtonElement).disabled).toBe(true)
  expect(calls.filter(c => c.path === '/turnos')).toHaveLength(1)
})
it.each([500, 503])('resultado %s ambiguo bloquea retry y cambios incluso tras navegar', async status => {
  backend(path => path === '/auth/refresh' ? Response.json({ access_token: 't' }) : path === '/turnos' ? Response.json({}, { status }) : undefined)
  open('/horarios?fecha=2026-11-10&tratamiento=t1')
  const user = userEvent.setup()
  await user.click(await screen.findByRole('button', { name: /09:00/ }))
  await user.click(screen.getByRole('button', { name: 'Reservar turno' }))
  expect(await screen.findByText(/Resultado no verificado/)).toBeTruthy()
  expect((screen.getByLabelText('Tratamiento') as HTMLSelectElement).disabled).toBe(true)
  expect((screen.getByLabelText('Fecha') as HTMLInputElement).disabled).toBe(true)
  expect((screen.getByLabelText('Sillon') as HTMLSelectElement).disabled).toBe(true)
  await user.click(screen.getByRole('button', { name: 'Reservar turno' }))
  expect(calls.filter(c => c.path === '/turnos')).toHaveLength(1)
  await user.click(screen.getByRole('link', { name: 'Consultar Mis reservas' }))
  await screen.findByText(/Todavia no tenes reservas/)
  await user.click(screen.getByRole('link', { name: 'Horarios' }))
  expect(await screen.findByRole('button', { name: 'Reconciliar reserva' })).toBeTruthy()
  expect((screen.getByLabelText('Tratamiento') as HTMLSelectElement).disabled).toBe(true)
  expect(calls.filter(c => c.path === '/turnos')).toHaveLength(1)
})
it.each([true, false])('reconciliacion explicita consulta servidor y solo libera si encuentra reserva %s', async found => {
  backend(path => path === '/auth/refresh' ? Response.json({ access_token: 't' }) : path === '/turnos' ? Response.json({}, { status: 500 }) : path === '/mis-reservas' ? Response.json(found ? [reservation] : []) : undefined)
  open('/horarios?fecha=2026-11-10&tratamiento=t1')
  const user = userEvent.setup()
  await user.click(await screen.findByRole('button', { name: /09:00/ }))
  await user.click(screen.getByRole('button', { name: 'Reservar turno' }))
  await user.click(await screen.findByRole('button', { name: 'Reconciliar reserva' }))
  expect(await screen.findByText(found ? /Reserva encontrada en el servidor/ : /No se encontro la reserva.*Contacta al consultorio/)).toBeTruthy()
  expect((screen.getByLabelText('Tratamiento') as HTMLSelectElement).disabled).toBe(!found)
  expect(calls.filter(c => c.path === '/turnos')).toHaveLength(1)
})
it.each([{ inicio: slot.inicio, estado: 'reservado' }, { ...slot, id: 'r1' }])('201 malformado no afirma reserva y conserva bloqueo %j', async body => {
  backend(path => path === '/auth/refresh' ? Response.json({ access_token: 't' }) : path === '/turnos' ? Response.json(body, { status: 201 }) : undefined)
  open('/horarios?fecha=2026-11-10&tratamiento=t1')
  const user = userEvent.setup()
  await user.click(await screen.findByRole('button', { name: /09:00/ }))
  await user.click(screen.getByRole('button', { name: 'Reservar turno' }))
  expect(await screen.findByRole('button', { name: 'Reconciliar reserva' })).toBeTruthy()
  expect(screen.queryByText(/Reserva registrada/)).toBeNull()
})
it.each([409, 422])('registro %s no inicia sesion ni conserva password fuera del formulario', async status => {
  backend(path => path === '/auth/registro' ? Response.json({ detail: 'Datos no validos' }, { status }) : undefined)
  open('/registro')
  const user = userEvent.setup()
  await user.type(screen.getByLabelText('Nombre'), 'Paciente ficticio')
  await user.type(screen.getByLabelText('Email'), 'paciente@example.test')
  await user.type(screen.getByLabelText('Telefono argentino'), '+5491100000000')
  await user.type(screen.getByLabelText('Contrasena'), 'Ficticia123')
  await user.click(screen.getByRole('button', { name: 'Crear cuenta' }))
  await screen.findByRole('alert')
  expect(calls.some(c => c.path === '/auth/login')).toBe(false)
  expect([localStorage.length, sessionStorage.length]).toEqual([0, 0])
})
it.each([
  { ...catalog, tratamientos: [{ ...catalog.tratamientos[0], sena_politica: 'obligatoria', sena_centavos: null }] },
  { ...catalog, tratamientos: [{ ...catalog.tratamientos[0], sena_centavos: 1.5 }] },
])('catalogo invalido falla cerrado sin inventar politica de sena %j', async invalid => {
  backend(path => path === '/catalogo-publico' ? Response.json(invalid) : undefined)
  open('/horarios?tratamiento=t1&fecha=2026-11-10')
  expect(await screen.findByText(/No se pudo cargar el catalogo/)).toBeTruthy()
  expect(screen.queryByRole('button', { name: /09:00/ })).toBeNull()
})
it.each(['sin fecha aware', '2026-11-10T09:00:00'])('horario invalido %s no habilita reserva', async inicio => {
  backend(path => path === '/horarios-libres' ? Response.json([{ ...slot, inicio }]) : undefined)
  open('/horarios?tratamiento=t1&fecha=2026-11-10')
  expect(await screen.findByText(/No se pudieron consultar horarios/)).toBeTruthy()
  expect(screen.queryByRole('button', { name: /Ingresar para reservar/ })).toBeNull()
})
it.each([120, 119])('ventana %s min respeta acciones servidor sin bloquear confirmar por reloj cliente', async minutes => {
  vi.useFakeTimers({ toFake: ['Date'] }); vi.setSystemTime(new Date('2026-11-10T10:00:00Z'))
  backend(path => path === '/auth/refresh' ? Response.json({ access_token: 't' }) : path === '/mis-reservas' ? Response.json([{ ...reservation, inicio: minutes === 120 ? '2026-11-10T12:00:00Z' : '2026-11-10T11:59:00Z', acciones: { confirmar: true, cancelar: minutes === 120, reprogramar: false } }]) : undefined)
  open('/mis-reservas')
  expect(await screen.findByRole('button', { name: 'Confirmar turno' })).toBeTruthy()
  expect(Boolean(screen.queryByRole('button', { name: 'Cancelar turno' }))).toBe(minutes === 120)
})
it('Mis reservas ordena por instante y muestra estados del servidor', async () => {
  backend(path => path === '/auth/refresh' ? Response.json({ access_token: 't' }) : path === '/mis-reservas' ? Response.json([{ ...reservation, id: 'r2', inicio: '2026-11-12T12:00:00Z', tratamiento_nombre: 'Ultima ficticia', estado: 'asistido' }, { ...reservation, tratamiento_nombre: 'Primera ficticia', estado: 'confirmado' }]) : undefined)
  open('/mis-reservas')
  await screen.findByText('Primera ficticia')
  expect(screen.getAllByRole('listitem').map(row => row.textContent)).toEqual([expect.stringContaining('Primera ficticia'), expect.stringContaining('Ultima ficticia')])
  expect(screen.getByText('asistido')).toBeTruthy()
  expect(screen.getByText('confirmado')).toBeTruthy()
})
it.each([
  { inicio: '2026-11-10T00:00:00Z', fin: '2026-11-10T00:15:00Z', label: /9 de nov de 2026, 21:00/, outside: true },
  { inicio: '2026-11-10T03:00:00Z', fin: '2026-11-10T03:15:00Z', label: /10 de nov de 2026, 00:00/, outside: false },
])('franja UTC $inicio muestra fecha AR completa y bloquea si fuera del dia', async item => {
  backend(path => path === '/horarios-libres' ? Response.json([{ ...slot, inicio: item.inicio, fin: item.fin }]) : undefined)
  open(`/horarios?fecha=2026-11-10&tratamiento=t1&sillon=s1&inicio=${encodeURIComponent(item.inicio)}`)
  const button = await screen.findByRole('button', { name: item.label })
  expect((button as HTMLButtonElement).disabled).toBe(item.outside)
  if (item.outside) {
    expect(await screen.findByText(/fuera de la fecha elegida.*contrato.*pendiente/i)).toBeTruthy()
    expect((screen.getByRole('button', { name: 'Ingresar para reservar' }) as HTMLButtonElement).disabled).toBe(true)
  }
  expect(calls.some(c => c.path === '/turnos')).toBe(false)
})
