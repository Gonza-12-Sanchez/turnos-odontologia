// @vitest-environment jsdom
import { afterEach, expect, it, vi } from 'vitest'
import { act, cleanup, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from './App'

const requests: { path: string; url: string; init: RequestInit }[] = []
interface StaffUser { id: string; rol: string }
function backend(user: StaffUser | null = null, handler?: (path: string, init: RequestInit) => Response | undefined | Promise<Response | undefined>) {
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
    requests.push({ path, url: input, init })
    const response = await handler?.(path, init)
    if (response) return response
    if (path === '/auth/refresh') return user ? Response.json({ access_token: 'ficticio-memoria' }) : Response.json({}, { status: 401 })
    if (path === '/auth/me' && user) return Response.json(user)
    if (path === '/agenda') return Response.json([])
    if (path === '/catalogo-publico') return Response.json({ sillones: [], tratamientos: [] })
    if (path.startsWith('/api/config/') && init.method === 'GET') return Response.json({ items: [], total: 0, page: 1, page_size: 20 })
    throw new Error(`HTTP no previsto ${path}`)
  }))
}
function open(path: string) {
  window.history.replaceState(null, '', path)
  render(<App />)
}
afterEach(() => {
  cleanup()
  Reflect.deleteProperty(navigator, 'locks')
  requests.length = 0
  vi.unstubAllGlobals()
  Object.defineProperty(navigator, 'onLine', { configurable: true, value: true })
})

it.each(['/agenda', '/config', '/cobros'])('pide login antes de consultar %s sin sesión', async path => {
  backend()
  open(path)
  expect(await screen.findByRole('heading', { name: 'Ingresar' })).toBeTruthy()
  expect(new URLSearchParams(window.location.search).get('returnTo')).toBe(path)
  expect(requests.every(request => request.path.startsWith('/auth/'))).toBe(true)
})

it.each([
  ['secretaria', '/agenda', 'Agenda del día', 'Agenda'],
  ['secretaria', '/config', 'Configuración', 'Configuración'],
  ['odontologo', '/agenda', 'Agenda del día', 'Agenda'],
])('ofrece navegación permitida a %s en %s', async (rol, path, heading, nav) => {
  backend({ id: 'personal-ficticio', rol })
  open(path)
  expect(await screen.findByRole('heading', { name: heading })).toBeTruthy()
  const navigation = within(screen.getByRole('navigation', { name: 'Principal' }))
  expect(navigation.getByRole('link', { name: nav })).toBeTruthy()
  expect(navigation.queryByRole('link', { name: 'Mis reservas' })).toBeNull()
  if (rol === 'odontologo') expect(navigation.queryByRole('link', { name: 'Configuración' })).toBeNull()
})

it.each([
  ['paciente', '/agenda'], ['paciente', '/config'], ['paciente', '/cobros'],
  ['odontologo', '/config'], ['odontologo', '/cobros'], ['desconocido', '/config'],
])('deniega %s en %s sin consultas administrativas', async (rol, path) => {
  backend({ id: 'cuenta-ficticia', rol })
  open(path)
  expect((await screen.findByRole('alert')).textContent).toMatch(/no tiene acceso/i)
  expect(requests.every(request => request.path.startsWith('/auth/'))).toBe(true)
})

it('consulta la agenda y muestra los turnos en horario argentino', async () => {
  backend({ id: 's1', rol: 'secretaria' }, path => path === '/agenda' ? Response.json([{
    sillon_id: 'sillon1', sillon_nombre: 'Sillón uno', turnos: [{
      id: 'turno1', inicio: '2026-12-02T01:00:00Z', fin: '2026-12-02T01:30:00Z',
      estado: 'reservado', paciente_nombre: 'Paciente ficticio', tratamiento_nombre: 'Control',
      tolerancia_min: 5, es_sobreturno: true, motivo_sobreturno: 'Motivo ficticio',
    }],
  }]) : undefined)
  open('/agenda')
  expect(await screen.findByRole('heading', { name: 'Paciente ficticio' })).toBeTruthy()
  expect(screen.getByText('22:00')).toBeTruthy()
  expect(screen.getByText('Sobreturno')).toBeTruthy()
  const user = userEvent.setup()
  await user.selectOptions(screen.getByLabelText('Estado'), 'reservado')
  await user.click(screen.getByRole('button', { name: 'Consultar agenda' }))
  expect(new URL(requests.filter(request => request.path === '/agenda').at(-1)!.url).searchParams.get('estado')).toBe('reservado')
})

it('permite asistencia según la proyección del servidor y envía motivo', async () => {
  const turnId = '55555555-5555-4555-8555-555555555555'
  let status = 'confirmado'
  backend({ id: 'o1', rol: 'odontologo' }, (path, init) => {
    if (path === '/agenda') return Response.json([{
      sillon_id: 'sillon1', sillon_nombre: 'Sillón uno', turnos: [{
        id: turnId, inicio: '2026-12-02T01:00:00Z', fin: '2026-12-02T01:30:00Z',
        estado: status, paciente_nombre: 'Paciente ficticio', tratamiento_nombre: 'Control',
        tratamiento_id: turnId, tolerancia_min: 5, es_sobreturno: false, motivo_sobreturno: null,
        acciones: { confirmar: false, cancelar: false, reprogramar: false, asistencia: status === 'confirmado', sobreturno: false },
      }],
    }])
    if (path === '/turnos/' + turnId + '/marcar-asistencia' && init.method === 'PATCH') {
      status = 'asistido'
      return Response.json({ id: turnId, estado: status })
    }
  })
  open('/agenda')
  const user = userEvent.setup()
  await user.click(await screen.findByRole('button', { name: /^Ver turno/ }))
  await user.click(await screen.findByRole('button', { name: 'Marcar asistido' }))
  expect(screen.queryByRole('button', { name: 'Cancelar turno' })).toBeNull()
  await user.type(screen.getByLabelText('Motivo'), 'Atención realizada')
  await user.click(screen.getByRole('button', { name: 'Aplicar cambio' }))
  expect(await within(screen.getByRole('list')).findByText('asistido')).toBeTruthy()
  const request = requests.find(row => row.init.method === 'PATCH')
  expect(request?.init.body).toBe(JSON.stringify({ estado: 'asistido', motivo: 'Atención realizada', origen: 'mostrador' }))
})

it('recupera un cobro incierto sin reenviar la escritura', async () => {
  const turnId = '55555555-5555-4555-8555-555555555555'
  const result = { cobro: { id: 'cobro-ficticio', turno_id: turnId, monto_centavos: 7000 } }
  let attempted = false
  backend({ id: 's1', rol: 'secretaria' }, (path, init) => {
    if (path === '/agenda') return Response.json([{
      sillon_id: 'sillon1', sillon_nombre: 'Sillón uno', turnos: [{
        id: turnId, inicio: '2026-12-02T01:00:00Z', fin: '2026-12-02T01:30:00Z',
        estado: 'confirmado', paciente_nombre: 'Paciente ficticio', tratamiento_nombre: 'Control',
        tolerancia_min: 5, es_sobreturno: false, motivo_sobreturno: null,
      }],
    }])
    if (path === '/cobros/resumen/' + turnId) return Response.json({
      precio_referencia_centavos: 10000, sena_acumulada_centavos: 3000,
      total_cobrado_centavos: attempted ? 10000 : 3000,
      saldo_referencia_centavos: attempted ? 0 : 7000, cerrado: attempted,
    })
    if (path === '/cobros' && init.method === 'POST') {
      attempted = true
      throw new TypeError('Fallo de transporte')
    }
    if (path === '/cobros/operacion') return Response.json(result)
  })
  open('/agenda')
  const user = userEvent.setup()
  await user.click(await screen.findByRole('button', { name: /^Ver turno/ }))
  await user.click(await screen.findByRole('button', { name: 'Ver cobros del turno' }))
  expect(window.location.pathname).toBe('/cobros')
  expect(window.location.search).toBe('')
  await user.type(await screen.findByLabelText('Importe en ARS'), '70,00')
  await user.click(screen.getByRole('button', { name: 'Registrar cobro' }))
  expect(await screen.findByText(/resultado quedó sin verificar/)).toBeTruthy()
  await user.click(screen.getByRole('button', { name: 'Consultar resultado del cobro' }))
  expect(await screen.findByText('Cobro cerrado.')).toBeTruthy()
  const writes = requests.filter(request => request.path === '/cobros' && request.init.method === 'POST')
  expect(writes).toHaveLength(1)
  const read = requests.find(request => request.path === '/cobros/operacion')
  expect(new Headers(read?.init.headers).get('Idempotency-Key'))
    .toBe(new Headers(writes[0].init.headers).get('Idempotency-Key'))
})

it('pide una nueva confirmación y clave al registrar un importe diferente', async () => {
  const turnId = '55555555-5555-4555-8555-555555555555'
  let written = false
  backend({ id: 's1', rol: 'secretaria' }, (path, init) => {
    if (path === '/agenda') return Response.json([{
      sillon_id: 'sillon1', sillon_nombre: 'Sillón uno', turnos: [{
        id: turnId, inicio: '2026-12-02T01:00:00Z', fin: '2026-12-02T01:30:00Z',
        estado: 'confirmado', paciente_nombre: 'Paciente ficticio', tratamiento_nombre: 'Control',
        tolerancia_min: 5, es_sobreturno: false, motivo_sobreturno: null,
      }],
    }])
    if (path === '/cobros/resumen/' + turnId) return Response.json({
      precio_referencia_centavos: 10000, sena_acumulada_centavos: 0,
      total_cobrado_centavos: written ? 7000 : 0,
      saldo_referencia_centavos: written ? 3000 : 10000, cerrado: written,
    })
    if (path === '/cobros' && init.method === 'POST') {
      const payload = JSON.parse(String(init.body))
      if (!payload.override_motivo) return Response.json({ detail: { code: 'MONTO_DIFIERE', esperado_centavos: 10000 } }, { status: 409 })
      written = true
      return Response.json({ cobro: { id: 'cobro-ficticio', turno_id: turnId, monto_centavos: 7000 } }, { status: 201 })
    }
    if (path === '/cobros') return Response.json([])
  })
  open('/agenda')
  const user = userEvent.setup()
  await user.click(await screen.findByRole('button', { name: /^Ver turno/ }))
  await user.click(await screen.findByRole('button', { name: 'Ver cobros del turno' }))
  await user.type(await screen.findByLabelText('Importe en ARS'), '70,00')
  await user.click(screen.getByRole('button', { name: 'Registrar cobro' }))
  await user.type(await screen.findByLabelText('Motivo de la diferencia'), 'Descuento acordado')
  expect(requests.filter(request => request.init.method === 'POST' && request.path === '/cobros')).toHaveLength(1)
  await user.click(screen.getByRole('button', { name: 'Confirmar cobro con diferencia' }))
  expect(await screen.findByText('Cobro registrado.')).toBeTruthy()
  const writes = requests.filter(request => request.init.method === 'POST' && request.path === '/cobros')
  expect(writes).toHaveLength(2)
  expect(new Headers(writes[1].init.headers).get('Idempotency-Key'))
    .not.toBe(new Headers(writes[0].init.headers).get('Idempotency-Key'))
  expect(JSON.parse(String(writes[1].init.body))).toMatchObject({
    monto_centavos: 7000, override_motivo: 'Descuento acordado',
  })
})

it('muestra la causa del 422, recarga el turno y avisa si el historial no está disponible', async () => {
  const id = '55555555-5555-4555-8555-555555555555'
  let rejected = false
  backend({ id: 's1', rol: 'secretaria' }, (path, init) => {
    if (path === '/agenda') return Response.json([{
      sillon_id: id, sillon_nombre: 'Sillón ficticio', turnos: [{
        id, tratamiento_id: id, inicio: '2026-12-02T01:00:00Z', fin: '2026-12-02T01:30:00Z',
        estado: 'reservado', paciente_nombre: 'Paciente ficticio', tratamiento_nombre: 'Control',
        tolerancia_min: 5, es_sobreturno: false, motivo_sobreturno: null,
        acciones: { confirmar: true, cancelar: !rejected, reprogramar: false, asistencia: false, sobreturno: false },
      }],
    }])
    if (path === '/turnos/' + id + '/cancelar' && init.method === 'PATCH') {
      rejected = true
      return Response.json({ detail: 'Fuera de la ventana de cancelación' }, { status: 422 })
    }
    if (path === '/turnos/' + id + '/historial') return Response.json({}, { status: 503 })
  })
  open('/agenda')
  const user = userEvent.setup()
  await user.click(await screen.findByRole('button', { name: /^Ver turno/ }))
  await user.click(screen.getByRole('button', { name: 'Cancelar turno' }))
  await user.click(screen.getByRole('button', { name: 'Aplicar cambio' }))
  expect(await screen.findByText('Fuera de la ventana de cancelación')).toBeTruthy()
  expect(screen.queryByText('Turno actualizado.')).toBeNull()
  expect(screen.queryByRole('button', { name: 'Cancelar turno' })).toBeNull()
  expect(requests.filter(request => request.path === '/agenda')).toHaveLength(2)
  await user.click(screen.getByRole('button', { name: 'Ver historial' }))
  expect(await screen.findByText('No se pudo consultar el historial del turno.')).toBeTruthy()
  expect(screen.queryByRole('region', { name: 'Historial del turno' })).toBeNull()
})

it.each([true, false])('valida el resumen de cobros con precio nulo o respuesta inválida (%s)', async valid => {
  const id = '55555555-5555-4555-8555-555555555555'
  backend({ id: 's1', rol: 'secretaria' }, path => {
    if (path === '/agenda') return Response.json([{
      sillon_id: id, sillon_nombre: 'Sillón ficticio', turnos: [{
        id, inicio: '2026-12-02T01:00:00Z', fin: '2026-12-02T01:30:00Z',
        estado: 'reservado', paciente_nombre: 'Paciente ficticio', tratamiento_nombre: 'Control',
        tolerancia_min: 5, es_sobreturno: false, motivo_sobreturno: null,
      }],
    }])
    if (path === '/cobros/resumen/' + id) return Response.json({
      precio_referencia_centavos: null, saldo_referencia_centavos: null,
      sena_acumulada_centavos: 0, total_cobrado_centavos: valid ? 0 : '0', cerrado: false,
    })
    if (path === '/cobros') return Response.json([])
  })
  open('/agenda')
  const user = userEvent.setup()
  await user.click(await screen.findByRole('button', { name: /^Ver turno/ }))
  await user.click(screen.getByRole('button', { name: 'Ver cobros del turno' }))
  expect(window.location.search).toBe('')
  if (valid) {
    expect(await screen.findAllByText('Sin referencia')).toHaveLength(2)
  } else {
    expect(await screen.findByText('No se pudo consultar el resumen de cobros.')).toBeTruthy()
    expect(screen.queryByRole('button', { name: 'Registrar cobro' })).toBeNull()
  }
})

it('espera la restauración sin mostrar contenido privado', async () => {
  let release!: (response: Response) => void
  backend({ id: 's1', rol: 'secretaria' }, path => path === '/auth/refresh' ? new Promise<Response>(resolve => { release = resolve }) : undefined)
  open('/config')
  expect(screen.getByRole('status').textContent).toMatch(/Restaurando/)
  expect(screen.queryByRole('heading', { name: 'Configuración' })).toBeNull()
  await waitFor(() => expect(requests.some(request => request.path === '/auth/refresh')).toBe(true))
  await act(async () => { release(Response.json({ access_token: 'ficticio' })) })
  expect(await screen.findByRole('heading', { name: 'Configuración' })).toBeTruthy()
})

it('no convierte indisponibilidad de sesión en acceso privado', async () => {
  backend(null, path => path === '/auth/refresh' ? Response.json({}, { status: 503 }) : undefined)
  open('/agenda')
  expect(await screen.findByText('No se pudo verificar la sesion.')).toBeTruthy()
  expect(screen.getByRole('button', { name: 'Reintentar sesion' })).toBeTruthy()
  expect(requests.every(request => request.path.startsWith('/auth/'))).toBe(true)
})

it.each([
  ['secretaria', '/config', 'Configuración'],
  ['secretaria', '/cobros', 'Cobros'],
  ['odontologo', '/agenda', 'Agenda del día'],
])('login %s conserva retorno autorizado %s sin enviar escrituras', async (rol, destination, heading) => {
  backend(null, path => path === '/auth/login' ? Response.json({ access_token: 'login-ficticio' })
    : path === '/auth/me' ? Response.json({ id: 'personal-ficticio', rol })
      : path === '/mis-reservas' ? Response.json([]) : undefined)
  open(`/login?returnTo=${encodeURIComponent(destination)}`)
  const user = userEvent.setup()
  await user.type(await screen.findByLabelText('Email'), 'personal@example.test')
  await user.type(screen.getByLabelText('Contrasena'), 'Ficticia123')
  await user.click(screen.getByRole('button', { name: 'Ingresar' }))
  expect(await screen.findByRole('heading', { name: heading })).toBeTruthy()
  expect(window.location.pathname).toBe(destination)
  expect(requests.filter(request => request.init.method !== 'GET').every(request => request.path.startsWith('/auth/'))).toBe(true)
})

const treatmentId = '11111111-1111-4111-8111-111111111111'
const chairId = '22222222-2222-4222-8222-222222222222'
const officeId = '33333333-3333-4333-8333-333333333333'
const treatment = { id: treatmentId, nombre: 'Control de ejemplo', activo: true, duracion_min: 15, precio_referencia_centavos: 12345, sena_politica: 'deshabilitada', sena_centavos: null }
const pageOf = (items: unknown[], page = 1, total = items.length) => ({ items, page, total, page_size: 20 })
const chair = { id: chairId, nombre: 'Sillón de ejemplo', consultorio_id: officeId, activo: true }
const block = { id: '44444444-4444-4444-8444-444444444444', motivo: 'Mantenimiento de ejemplo', sillon_id: null, desde: '2026-11-12T16:00:00Z', hasta: '2026-11-12T17:00:00Z', activo: true, warnings: [] }

it('muestra el intervalo del bloqueo en hora argentina y no solo su alcance', async () => {
  backend({ id: 's1', rol: 'secretaria' }, path => path === '/api/config/bloqueos' ? Response.json(pageOf([block])) : undefined)
  open('/config')
  await userEvent.setup().click(await screen.findByRole('button', { name: 'Bloqueos' }))
  const row = (await screen.findByRole('heading', { name: block.motivo })).closest('li')!
  expect(within(row).getByText(/13:00/)).toBeTruthy()
  expect(within(row).getByText(/14:00/)).toBeTruthy()
  expect(within(row).getByText(/Argentina/)).toBeTruthy()
})

it('muestra ambas fechas argentinas de un bloqueo que cruza medianoche', async () => {
  const overnight = { ...block, desde: '2026-11-13T02:30:00Z', hasta: '2026-11-13T03:30:00Z' }
  backend({ id: 's1', rol: 'secretaria' }, path => path === '/api/config/bloqueos' ? Response.json(pageOf([overnight])) : undefined)
  open('/config')
  await userEvent.setup().click(await screen.findByRole('button', { name: 'Bloqueos' }))
  const row = (await screen.findByRole('heading', { name: block.motivo })).closest('li')!
  const interval = within(row).getByText(/23:30/).textContent!
  expect(interval).toMatch(/12 de nov de 2026/)
  expect(interval).toMatch(/13 de nov de 2026/)
  expect(interval).toMatch(/00:30/)
})

it('edita el nombre de un sillón sin enviar sede ni alterar turnos', async () => {
  backend({ id: 's1', rol: 'secretaria' }, (path, init) => {
    if (path === '/api/config/sillones') return Response.json(pageOf([chair]))
    if (path === `/api/config/sillones/${chairId}` && init.method === 'PATCH') return Response.json({ ...chair, nombre: 'Sillón Norte' })
  })
  open('/config')
  const user = userEvent.setup()
  await user.click(await screen.findByRole('button', { name: 'Sillones' }))
  await user.click(await screen.findByRole('button', { name: `Editar ${chair.nombre}` }))
  await user.clear(screen.getByLabelText('Nombre'))
  await user.type(screen.getByLabelText('Nombre'), '  Sillón Norte  ')
  await user.click(screen.getByRole('button', { name: 'Guardar cambios' }))
  expect(await screen.findByText('Sillón actualizado.')).toBeTruthy()
  expect(screen.getByRole('heading', { name: 'Sillón Norte' })).toBeTruthy()
  expect(JSON.parse(String(requests.find(request => request.init.method === 'PATCH')?.init.body))).toEqual({ nombre: 'Sillón Norte' })
  expect(requests.filter(request => !request.path.startsWith('/auth/') && request.init.method !== 'GET').map(request => request.path)).toEqual([`/api/config/sillones/${chairId}`])
})

it.each([false, true])('baja lógica de sillón exige confirmación y conserva históricos (confirmar=%s)', async confirm => {
  let current = { ...chair }
  backend({ id: 's1', rol: 'secretaria' }, (path, init) => {
    if (path === '/api/config/sillones') {
      const active = new URL(requests.at(-1)!.url).searchParams.get('activo') === 'true'
      return Response.json(pageOf(current.activo === active ? [current] : []))
    }
    if (path === `/api/config/sillones/${chairId}` && init.method === 'PATCH') { current = { ...current, activo: false }; return Response.json(current) }
  })
  open('/config')
  const user = userEvent.setup()
  await user.click(await screen.findByRole('button', { name: 'Sillones' }))
  await user.click(await screen.findByRole('button', { name: `Editar ${chair.nombre}` }))
  await user.clear(screen.getByLabelText('Nombre'))
  await user.type(screen.getByLabelText('Nombre'), 'Cambio todavía no guardado')
  await user.click(screen.getByRole('button', { name: 'Desactivar sillón' }))
  expect(await screen.findByRole('heading', { name: 'Desactivar sillón' })).toBeTruthy()
  expect(screen.getByText(/Los turnos existentes no se borran ni se cancelan automáticamente/)).toBeTruthy()
  expect(requests.filter(request => request.init.method === 'PATCH')).toHaveLength(0)
  if (!confirm) {
    await user.click(screen.getByRole('button', { name: 'Conservar activo' }))
    expect(screen.getByRole('heading', { name: 'Editar sillón' })).toBeTruthy()
    expect(requests.filter(request => request.init.method === 'PATCH')).toHaveLength(0)
  } else {
    await user.click(screen.getByRole('button', { name: 'Desactivar sillón' }))
    expect(await screen.findByText('Sillón desactivado. Los históricos se conservan.')).toBeTruthy()
    expect(await screen.findByText(/No hay sillones activos/)).toBeTruthy()
    expect(JSON.parse(String(requests.find(request => request.init.method === 'PATCH')?.init.body))).toEqual({ activo: false })
    expect(requests.filter(request => !request.path.startsWith('/auth/') && request.init.method !== 'GET').map(request => request.path)).toEqual([`/api/config/sillones/${chairId}`])
    await user.selectOptions(screen.getByLabelText('Mostrar'), 'false')
    await user.click(screen.getByRole('button', { name: 'Consultar' }))
    expect(await screen.findByRole('heading', { name: chair.nombre })).toBeTruthy()
    expect(screen.getByText('Inactivo')).toBeTruthy()
  }
})

it.each([false, true])('reactiva sillón inactivo solo con confirmación (confirmar=%s)', async confirm => {
  let current = { ...chair, activo: false }
  backend({ id: 's1', rol: 'secretaria' }, (path, init) => {
    if (path === '/api/config/sillones') {
      const active = new URL(requests.at(-1)!.url).searchParams.get('activo') === 'true'
      return Response.json(pageOf(current.activo === active ? [current] : []))
    }
    if (path === `/api/config/sillones/${chairId}` && init.method === 'PATCH') { current = { ...current, activo: true }; return Response.json(current) }
  })
  open('/config')
  const user = userEvent.setup()
  await user.click(await screen.findByRole('button', { name: 'Sillones' }))
  await user.selectOptions(screen.getByLabelText('Mostrar'), 'false')
  await user.click(screen.getByRole('button', { name: 'Consultar' }))
  await user.click(await screen.findByRole('button', { name: `Editar ${chair.nombre}` }))
  await user.click(screen.getByRole('button', { name: 'Reactivar sillón' }))
  expect(await screen.findByRole('heading', { name: 'Reactivar sillón' })).toBeTruthy()
  expect(requests.filter(request => request.init.method === 'PATCH')).toHaveLength(0)
  await user.click(screen.getByRole('button', { name: confirm ? 'Reactivar sillón' : 'Volver' }))
  if (!confirm) expect(screen.getByRole('heading', { name: 'Editar sillón' })).toBeTruthy()
  else {
    expect(await screen.findByText('Sillón reactivado. Los históricos se conservan.')).toBeTruthy()
    expect(await screen.findByText(/No hay sillones inactivos/)).toBeTruthy()
    expect(JSON.parse(String(requests.find(request => request.init.method === 'PATCH')?.init.body))).toEqual({ activo: true })
  }
  expect(requests.filter(request => request.init.method === 'PATCH')).toHaveLength(confirm ? 1 : 0)
})

it.each([404, 422])('sillón rechazado con %s no muestra éxito y conserva el formulario', async status => {
  backend({ id: 's1', rol: 'secretaria' }, (path, init) => {
    if (path === '/api/config/sillones') return Response.json(pageOf([chair]))
    if (path === `/api/config/sillones/${chairId}` && init.method === 'PATCH') return Response.json({ detail: [{ loc: ['body', 'nombre'], msg: 'detalle interno ficticio' }] }, { status })
  })
  open('/config')
  const user = userEvent.setup()
  await user.click(await screen.findByRole('button', { name: 'Sillones' }))
  await user.click(await screen.findByRole('button', { name: `Editar ${chair.nombre}` }))
  await user.clear(screen.getByLabelText('Nombre'))
  await user.type(screen.getByLabelText('Nombre'), 'Nombre rechazado')
  await user.click(screen.getByRole('button', { name: 'Guardar cambios' }))
  if (status === 422) {
    await waitFor(() => expect(screen.getByLabelText('Nombre').getAttribute('aria-invalid')).toBe('true'))
    expect(document.getElementById(screen.getByLabelText('Nombre').getAttribute('aria-describedby')!)?.textContent).toMatch(/Revisa/)
    expect((screen.getByRole('button', { name: 'Guardar cambios' }) as HTMLButtonElement).disabled).toBe(false)
  } else {
    expect(await screen.findByText(/El sillón ya no está disponible para tu cuenta/)).toBeTruthy()
    expect((screen.getByRole('button', { name: 'Guardar cambios' }) as HTMLButtonElement).disabled).toBe(true)
  }
  expect((screen.getByLabelText('Nombre') as HTMLInputElement).value).toBe('Nombre rechazado')
  expect(screen.queryByText('Sillón actualizado.')).toBeNull()
  expect(screen.queryByText(/detalle interno ficticio/)).toBeNull()
  expect(screen.queryByText(/Cambios de configuración bloqueados/)).toBeNull()
  expect(requests.filter(request => request.init.method === 'PATCH')).toHaveLength(1)
})

it.each(['sin cambios', 'blanco'])('sillón con nombre %s no genera PATCH', async mode => {
  backend({ id: 's1', rol: 'secretaria' }, path => path === '/api/config/sillones' ? Response.json(pageOf([chair])) : undefined)
  open('/config')
  const user = userEvent.setup()
  await user.click(await screen.findByRole('button', { name: 'Sillones' }))
  await user.click(await screen.findByRole('button', { name: `Editar ${chair.nombre}` }))
  if (mode === 'blanco') { await user.clear(screen.getByLabelText('Nombre')); await user.type(screen.getByLabelText('Nombre'), '   ') }
  await user.click(screen.getByRole('button', { name: 'Guardar cambios' }))
  expect(await screen.findByText(mode === 'blanco' ? 'El nombre debe tener entre 1 y 80 caracteres.' : 'No hay cambios para guardar.')).toBeTruthy()
  expect(requests.filter(request => request.init.method === 'PATCH')).toHaveLength(0)
  expect(screen.queryByLabelText('Consultorio')).toBeNull()
})

it.each([403, 404, 422])('rechazo %s de baja de sillón no borra ni confirma éxito', async status => {
  backend({ id: 's1', rol: 'secretaria' }, (path, init) => {
    if (path === '/api/config/sillones') return Response.json(pageOf([chair]))
    if (path === `/api/config/sillones/${chairId}` && init.method === 'PATCH') return Response.json({ detail: [{ loc: ['body', 'activo'], msg: 'restricción interna ficticia' }] }, { status })
  })
  open('/config')
  const user = userEvent.setup()
  await user.click(await screen.findByRole('button', { name: 'Sillones' }))
  await user.click(await screen.findByRole('button', { name: `Editar ${chair.nombre}` }))
  await user.click(screen.getByRole('button', { name: 'Desactivar sillón' }))
  await user.click(screen.getByRole('button', { name: 'Desactivar sillón' }))
  expect(await screen.findByText(status === 403 ? /Tu cuenta no tiene permiso para modificar este sillón/ : status === 404 ? /El sillón ya no está disponible para tu cuenta/ : /El servidor rechazó los cambios del sillón/)).toBeTruthy()
  expect(screen.getByText('Activo')).toBeTruthy()
  expect(screen.queryByText('Sillón desactivado. Los históricos se conservan.')).toBeNull()
  expect(requests.filter(request => request.init.method === 'DELETE')).toHaveLength(0)
  expect(requests.filter(request => request.init.method === 'PATCH')).toHaveLength(1)
  expect(requests.filter(request => request.path === '/auth/refresh')).toHaveLength(1)
})

it.each(['sede', 'activo', 'red'])('sillón con respuesta incierta %s sigue bloqueado al navegar', async mode => {
  backend({ id: 's1', rol: 'secretaria' }, (path, init) => {
    if (path === '/api/config/sillones') return Response.json(pageOf([chair]))
    if (path === `/api/config/sillones/${chairId}` && init.method === 'PATCH') {
      if (mode === 'red') throw new TypeError('transporte ficticio')
      return Response.json({ ...chair, consultorio_id: mode === 'sede' ? treatmentId : officeId, activo: mode === 'activo', nombre: chair.nombre })
    }
  })
  open('/config')
  const user = userEvent.setup()
  await user.click(await screen.findByRole('button', { name: 'Sillones' }))
  await user.click(await screen.findByRole('button', { name: `Editar ${chair.nombre}` }))
  await user.click(screen.getByRole('button', { name: 'Desactivar sillón' }))
  await user.click(screen.getByRole('button', { name: 'Desactivar sillón' }))
  expect(await screen.findByText(/Cambios de configuración bloqueados/)).toBeTruthy()
  await user.click(screen.getByRole('link', { name: 'Agenda' }))
  await user.click(screen.getByRole('link', { name: 'Configuración' }))
  await user.click(await screen.findByRole('button', { name: 'Sillones' }))
  expect((await screen.findByRole('button', { name: `Editar ${chair.nombre}` }) as HTMLButtonElement).disabled).toBe(true)
  expect(requests.filter(request => request.init.method === 'PATCH')).toHaveLength(1)
  expect(screen.queryByText('Sillón desactivado. Los históricos se conservan.')).toBeNull()
})

it('secretaria consulta tratamientos reales paginados con Bearer', async () => {
  backend({ id: 'secretaria-ficticia', rol: 'secretaria' }, path => path === '/api/config/tratamientos' ? Response.json(pageOf([treatment])) : undefined)
  open('/config')
  expect(await screen.findByRole('heading', { name: 'Control de ejemplo' })).toBeTruthy()
  expect(screen.getByText(/123,45/)).toBeTruthy()
  const call = requests.find(request => request.path === '/api/config/tratamientos')
  expect(new URL(call!.url).searchParams.get('page')).toBe('1')
  expect(new URL(call!.url).searchParams.get('activo')).toBe('true')
  expect(call?.init.headers).toHaveProperty('Authorization', 'Bearer ficticio-memoria')
})

it.each([
  ['Sillones', 'sillones', chair, 'Sillón de ejemplo'],
  ['Bloqueos', 'bloqueos', block, 'Mantenimiento de ejemplo'],
])('lista %s sin usar el catálogo público ni mezclar recursos', async (tab, resource, entry, name) => {
  backend({ id: 's1', rol: 'secretaria' }, path => path === `/api/config/${resource}` ? Response.json(pageOf([entry])) : undefined)
  open('/config')
  const user = userEvent.setup()
  await user.click(await screen.findByRole('button', { name: String(tab) }))
  expect(await screen.findByRole('heading', { name: String(name) })).toBeTruthy()
  expect(requests.some(request => request.path === '/catalogo-publico')).toBe(false)
})

it('filtra inactivos y cambia página conservando el filtro autorizado', async () => {
  backend({ id: 's1', rol: 'secretaria' }, path => {
    if (path !== '/api/config/tratamientos') return undefined
    const query = new URL(requests.at(-1)!.url).searchParams
    const page = Number(query.get('page'))
    const active = query.get('activo') === 'true'
    return Response.json(pageOf([{ ...treatment, activo: active, nombre: `${active ? 'Activo' : 'Inactivo'} página ${page}` }], page, 21))
  })
  open('/config')
  expect(await screen.findByRole('heading', { name: 'Activo página 1' })).toBeTruthy()
  const user = userEvent.setup()
  await user.selectOptions(screen.getByLabelText('Mostrar'), 'false')
  await user.click(screen.getByRole('button', { name: 'Consultar' }))
  expect(await screen.findByRole('heading', { name: 'Inactivo página 1' })).toBeTruthy()
  await user.click(screen.getByRole('button', { name: 'Siguiente' }))
  expect(await screen.findByRole('heading', { name: 'Inactivo página 2' })).toBeTruthy()
  expect(new URL(requests.at(-1)!.url).searchParams.get('activo')).toBe('false')
})

it.each([
  pageOf([{ ...treatment, duracion_min: 0 }]),
  pageOf([{ ...treatment, precio_referencia_centavos: 1.5 }]),
  { ...pageOf([]), page_size: 101 },
  pageOf([{ ...treatment, activo: false }]),
])('rechaza DTO o filtro incoherente sin renderizar recursos %j', async payload => {
  backend({ id: 's1', rol: 'secretaria' }, path => path === '/api/config/tratamientos' ? Response.json(payload) : undefined)
  open('/config')
  expect(await screen.findByText(/No se pudo consultar la configuración/)).toBeTruthy()
  expect(screen.queryByRole('heading', { name: treatment.nombre })).toBeNull()
})

it.each([true, false])('distingue vacío de fallo y permite reconsulta segura %s', async empty => {
  let fail = !empty
  backend({ id: 's1', rol: 'secretaria' }, path => path === '/api/config/tratamientos' ? Response.json(fail ? {} : pageOf([]), { status: fail ? 503 : 200 }) : undefined)
  open('/config')
  if (empty) expect(await screen.findByText(/No hay tratamientos activos/)).toBeTruthy()
  else {
    expect(await screen.findByText(/No se pudo consultar la configuración/)).toBeTruthy()
    expect(screen.queryByText(/No hay tratamientos activos/)).toBeNull()
    fail = false
    await userEvent.setup().click(screen.getByRole('button', { name: 'Reintentar consulta' }))
    expect(await screen.findByText(/No hay tratamientos activos/)).toBeTruthy()
  }
})

it('ignora una respuesta tardía al cambiar de recurso aunque el transporte ignore abort', async () => {
  let release!: (response: Response) => void
  backend({ id: 's1', rol: 'secretaria' }, path => path === '/api/config/tratamientos'
    ? new Promise<Response>(resolve => { release = resolve })
    : path === '/api/config/sillones' ? Response.json(pageOf([chair])) : undefined)
  open('/config')
  await waitFor(() => expect(requests.some(request => request.path === '/api/config/tratamientos')).toBe(true))
  await userEvent.setup().click(screen.getByRole('button', { name: 'Sillones' }))
  expect(await screen.findByRole('heading', { name: chair.nombre })).toBeTruthy()
  await act(async () => { release(Response.json(pageOf([treatment]))) })
  expect(screen.queryByRole('heading', { name: treatment.nombre })).toBeNull()
  expect(screen.getByRole('heading', { name: chair.nombre })).toBeTruthy()
  expect(requests.find(request => request.path === '/api/config/tratamientos')?.init.signal?.aborted).toBe(true)
})

it.each(['paciente', 'secretaria'])('logout y nueva cuenta %s descartan datos de la secretaria anterior', async rol => {
  let current = { id: 's1', rol: 'secretaria' }
  let release!: (response: Response) => void
  let read = 0
  backend(current, (path, init) => {
    if (path === '/auth/me') return Response.json(current)
    if (path === '/auth/logout') return new Response(null, { status: 204 })
    if (path === '/auth/login') { current = { id: 'cuenta-nueva', rol }; return Response.json({ access_token: 'token-nuevo-ficticio' }) }
    if (path === '/mis-reservas') return Response.json([])
    if (path === '/api/config/tratamientos' && init.method === 'GET') {
      read++
      return read === 1 ? new Promise<Response>(resolve => { release = resolve }) : Response.json(pageOf([{ ...treatment, nombre: 'Datos de la cuenta nueva' }]))
    }
  })
  open('/config')
  await waitFor(() => expect(read).toBe(1))
  const user = userEvent.setup()
  await user.click(screen.getByRole('button', { name: 'Cerrar sesion' }))
  expect(await screen.findByRole('heading', { name: 'Ingresar' })).toBeTruthy()
  expect(screen.queryByRole('link', { name: 'Configuración' })).toBeNull()
  await user.type(screen.getByLabelText('Email'), 'cuenta-nueva@example.test')
  await user.type(screen.getByLabelText('Contrasena'), 'Ficticia123')
  await user.click(screen.getByRole('button', { name: 'Ingresar' }))
  expect(await screen.findByRole('heading', { name: rol === 'paciente' ? 'Mis reservas' : 'Datos de la cuenta nueva' })).toBeTruthy()
  await act(async () => { release(Response.json(pageOf([treatment]))) })
  expect(screen.queryByRole('heading', { name: treatment.nombre })).toBeNull()
  expect(read).toBe(rol === 'paciente' ? 1 : 2)
  expect(localStorage.length).toBe(0)
  expect(sessionStorage.length).toBe(0)
})

it('dos lecturas vencidas del catálogo comparten un refresh sin recuperar filtros viejos', async () => {
  const releases: ((response: Response) => void)[] = []
  let reads = 0
  backend({ id: 's1', rol: 'secretaria' }, path => {
    if (path !== '/api/config/tratamientos') return undefined
    reads++
    return reads <= 2 ? new Promise<Response>(resolve => { releases.push(resolve) }) : Response.json(pageOf([treatment]))
  })
  open('/config')
  await waitFor(() => expect(releases).toHaveLength(1))
  await userEvent.setup().click(screen.getByRole('button', { name: 'Consultar' }))
  await waitFor(() => expect(releases).toHaveLength(2))
  await act(async () => { releases.forEach(release => release(Response.json({}, { status: 401 }))) })
  expect(await screen.findByRole('heading', { name: treatment.nombre })).toBeTruthy()
  expect(requests.filter(request => request.path === '/auth/refresh')).toHaveLength(2)
  expect(requests.filter(request => request.path === '/auth/login')).toHaveLength(0)
  expect(localStorage.length).toBe(0)
})

it.each([['123,46', 12346], ['0,29', 29], ['21474836,47', 2147483647]])('edita precio %s como centavos exactos sin enviar otros campos', async (price, cents) => {
  let saved = false
  backend({ id: 's1', rol: 'secretaria' }, (path, init) => {
    if (path === '/api/config/tratamientos') return Response.json(pageOf([{ ...treatment, precio_referencia_centavos: saved ? Number(cents) : 12345 }]))
    if (path === `/api/config/tratamientos/${treatmentId}` && init.method === 'PATCH') {
      saved = true
      return Response.json({ ...treatment, precio_referencia_centavos: cents })
    }
  })
  open('/config')
  const user = userEvent.setup()
  await user.click(await screen.findByRole('button', { name: `Editar ${treatment.nombre}` }))
  const input = screen.getByLabelText('Precio de referencia en ARS')
  await user.clear(input)
  await user.type(input, String(price))
  await user.click(screen.getByRole('button', { name: 'Guardar cambios' }))
  expect(await screen.findByText('Tratamiento actualizado.')).toBeTruthy()
  const call = requests.find(request => request.init.method === 'PATCH')
  expect(JSON.parse(String(call?.init.body))).toEqual({ precio_referencia_centavos: cents })
})

it.each([1, 2147483647])('edita duración %s sin sobrescribir precio ni política', async duration => {
  backend({ id: 's1', rol: 'secretaria' }, (path, init) => {
    if (path === '/api/config/tratamientos') return Response.json(pageOf([treatment]))
    if (path === `/api/config/tratamientos/${treatmentId}` && init.method === 'PATCH') return Response.json({ ...treatment, duracion_min: duration })
  })
  open('/config')
  const user = userEvent.setup()
  await user.click(await screen.findByRole('button', { name: `Editar ${treatment.nombre}` }))
  await user.clear(screen.getByLabelText('Duración en minutos'))
  await user.type(screen.getByLabelText('Duración en minutos'), String(duration))
  await user.click(screen.getByRole('button', { name: 'Guardar cambios' }))
  expect(await screen.findByText('Tratamiento actualizado.')).toBeTruthy()
  expect(JSON.parse(String(requests.find(request => request.init.method === 'PATCH')?.init.body))).toEqual({ duracion_min: duration })
})

it('edita nombre y conserva valores no modificados del tratamiento', async () => {
  backend({ id: 's1', rol: 'secretaria' }, (path, init) => {
    if (path === '/api/config/tratamientos') return Response.json(pageOf([treatment]))
    if (path === `/api/config/tratamientos/${treatmentId}` && init.method === 'PATCH') return Response.json({ ...treatment, nombre: 'Control actualizado' })
  })
  open('/config')
  const user = userEvent.setup()
  await user.click(await screen.findByRole('button', { name: `Editar ${treatment.nombre}` }))
  await user.clear(screen.getByLabelText('Nombre'))
  await user.type(screen.getByLabelText('Nombre'), '  Control actualizado  ')
  await user.click(screen.getByRole('button', { name: 'Guardar cambios' }))
  expect(await screen.findByRole('heading', { name: 'Control actualizado' })).toBeTruthy()
  expect(JSON.parse(String(requests.find(request => request.init.method === 'PATCH')?.init.body))).toEqual({ nombre: 'Control actualizado' })
})

it.each([['', null], ['123,46', 12346]])('crea tratamiento con precio %s sin configurar señas ni inventar un identificador', async (price, cents) => {
  let created = false
  backend({ id: 's1', rol: 'secretaria' }, (path, init) => {
    if (path === '/api/config/tratamientos' && init.method === 'POST') {
      created = true
      return Response.json({ ...treatment, nombre: 'Nuevo tratamiento', duracion_min: 30, precio_referencia_centavos: cents }, { status: 201 })
    }
    if (path === '/api/config/tratamientos') return Response.json(pageOf(created ? [{ ...treatment, nombre: 'Nuevo tratamiento', duracion_min: 30, precio_referencia_centavos: cents }] : []))
  })
  open('/config')
  const user = userEvent.setup()
  await user.click(await screen.findByRole('button', { name: 'Agregar tratamiento' }))
  await user.type(screen.getByLabelText('Nombre'), 'Nuevo tratamiento')
  await user.type(screen.getByLabelText('Duración en minutos'), '30')
  if (price) await user.type(screen.getByLabelText('Precio de referencia en ARS'), price)
  await user.click(screen.getByRole('button', { name: 'Crear tratamiento' }))
  expect(await screen.findByText('Tratamiento creado.')).toBeTruthy()
  expect(await screen.findByRole('heading', { name: 'Nuevo tratamiento' })).toBeTruthy()
  const call = requests.find(request => request.path === '/api/config/tratamientos' && request.init.method === 'POST')
  expect(JSON.parse(String(call?.init.body))).toEqual({ nombre: 'Nuevo tratamiento', duracion_min: 30, precio_referencia_centavos: cents })
})

it.each([
  ['precio_referencia_centavos', 'Precio de referencia en ARS', '0,29'],
  ['duracion_min', 'Duración en minutos', '30'],
])('asocia 422 a %s y permite corregir sin reenviar automáticamente', async (field, label, value) => {
  backend({ id: 's1', rol: 'secretaria' }, (path, init) => {
    if (path === '/api/config/tratamientos') return Response.json(pageOf([treatment]))
    if (path === `/api/config/tratamientos/${treatmentId}` && init.method === 'PATCH') return Response.json({ detail: [{ loc: ['body', field], msg: 'detalle interno no mostrar', type: 'value_error' }] }, { status: 422 })
  })
  open('/config')
  const user = userEvent.setup()
  await user.click(await screen.findByRole('button', { name: `Editar ${treatment.nombre}` }))
  await user.clear(screen.getByLabelText(label))
  await user.type(screen.getByLabelText(label), value)
  await user.click(screen.getByRole('button', { name: 'Guardar cambios' }))
  await waitFor(() => expect(screen.getByLabelText(label).getAttribute('aria-invalid')).toBe('true'))
  const description = screen.getByLabelText(label).getAttribute('aria-describedby')
  expect(document.getElementById(description!)?.textContent).toMatch(/Revisa/)
  expect(screen.queryByText(/detalle interno/)).toBeNull()
  expect((screen.getByRole('button', { name: 'Guardar cambios' }) as HTMLButtonElement).disabled).toBe(false)
  expect(requests.filter(request => request.init.method === 'PATCH')).toHaveLength(1)
})

it.each(['fallo', 'pendiente'])('navegar no libera una escritura %s del catálogo', async mode => {
  let release!: (response: Response) => void
  backend({ id: 's1', rol: 'secretaria' }, (path, init) => {
    if (path === '/api/config/tratamientos') return Response.json(pageOf([treatment]))
    if (path === `/api/config/tratamientos/${treatmentId}` && init.method === 'PATCH') return mode === 'fallo' ? Response.json({}, { status: 503 }) : new Promise<Response>(resolve => { release = resolve })
  })
  open('/config')
  const user = userEvent.setup()
  await user.click(await screen.findByRole('button', { name: `Editar ${treatment.nombre}` }))
  await user.clear(screen.getByLabelText('Precio de referencia en ARS'))
  await user.type(screen.getByLabelText('Precio de referencia en ARS'), '0,29')
  await user.click(screen.getByRole('button', { name: 'Guardar cambios' }))
  await waitFor(() => expect(requests.filter(request => request.init.method === 'PATCH')).toHaveLength(1))
  await user.click(screen.getByRole('link', { name: 'Agenda' }))
  await user.click(screen.getByRole('link', { name: 'Configuración' }))
  const edit = await screen.findByRole('button', { name: `Editar ${treatment.nombre}` })
  expect((edit as HTMLButtonElement).disabled).toBe(true)
  if (mode === 'pendiente') await act(async () => { release(Response.json({}, { status: 503 })) })
  expect(await screen.findByText(/Cambios de configuración bloqueados/)).toBeTruthy()
  await user.click(screen.getByRole('button', { name: 'Consultar' }))
  expect((await screen.findByRole('button', { name: `Editar ${treatment.nombre}` }) as HTMLButtonElement).disabled).toBe(true)
  expect(requests.filter(request => request.init.method === 'PATCH')).toHaveLength(1)
})

it.each([['', null], ['0', 0]])('precio textual %s distingue null de cero', async (price, cents) => {
  backend({ id: 's1', rol: 'secretaria' }, (path, init) => {
    if (path === '/api/config/tratamientos') return Response.json(pageOf([treatment]))
    if (path === `/api/config/tratamientos/${treatmentId}` && init.method === 'PATCH') return Response.json({ ...treatment, precio_referencia_centavos: cents })
  })
  open('/config')
  const user = userEvent.setup()
  await user.click(await screen.findByRole('button', { name: `Editar ${treatment.nombre}` }))
  await user.clear(screen.getByLabelText('Precio de referencia en ARS'))
  if (price) await user.type(screen.getByLabelText('Precio de referencia en ARS'), price)
  await user.click(screen.getByRole('button', { name: 'Guardar cambios' }))
  expect(await screen.findByText('Tratamiento actualizado.')).toBeTruthy()
  expect(JSON.parse(String(requests.find(request => request.init.method === 'PATCH')?.init.body))).toEqual({ precio_referencia_centavos: cents })
})

it.each([
  ['Precio de referencia en ARS', '21474836,48', /precio máximo/],
  ['Precio de referencia en ARS', '0,291', /dos decimales/],
  ['Precio de referencia en ARS', '1.234,56', /dos decimales/],
  ['Precio de referencia en ARS', '-1', /dos decimales/],
  ['Duración en minutos', '0', /duración debe ser/],
  ['Duración en minutos', '2147483648', /duración debe ser/],
  ['Duración en minutos', '1.5', /duración debe ser/],
])('rechaza %s=%s antes del PATCH', async (label, value, message) => {
  backend({ id: 's1', rol: 'secretaria' }, path => path === '/api/config/tratamientos' ? Response.json(pageOf([treatment])) : undefined)
  open('/config')
  const user = userEvent.setup()
  await user.click(await screen.findByRole('button', { name: `Editar ${treatment.nombre}` }))
  await user.clear(screen.getByLabelText(label))
  await user.type(screen.getByLabelText(label), value)
  await user.click(screen.getByRole('button', { name: 'Guardar cambios' }))
  expect(await screen.findByText(message)).toBeTruthy()
  expect(requests.filter(request => request.init.method === 'PATCH')).toHaveLength(0)
})

it('no escribe sin cambios en el tratamiento', async () => {
  backend({ id: 's1', rol: 'secretaria' }, path => path === '/api/config/tratamientos' ? Response.json(pageOf([treatment])) : undefined)
  open('/config')
  const user = userEvent.setup()
  await user.click(await screen.findByRole('button', { name: `Editar ${treatment.nombre}` }))
  await user.click(screen.getByRole('button', { name: 'Guardar cambios' }))
  expect(await screen.findByText('No hay cambios para guardar.')).toBeTruthy()
  expect(requests.filter(request => request.init.method === 'PATCH')).toHaveLength(0)
})

it('guarda política y seña en centavos en el mismo PATCH', async () => {
  backend({ id: 's1', rol: 'secretaria' }, (path, init) => {
    if (path === '/api/config/tratamientos') return Response.json(pageOf([treatment]))
    if (path === `/api/config/tratamientos/${treatmentId}` && init.method === 'PATCH') {
      return Response.json({ ...treatment, sena_politica: 'obligatoria', sena_centavos: 3005 })
    }
  })
  open('/config')
  const user = userEvent.setup()
  await user.click(await screen.findByRole('button', { name: `Editar ${treatment.nombre}` }))
  await user.selectOptions(screen.getByLabelText('Política de seña'), 'obligatoria')
  await user.type(screen.getByLabelText('Seña en ARS'), '30,05')
  await user.click(screen.getByRole('button', { name: 'Guardar cambios' }))
  expect(await screen.findByText('Tratamiento actualizado.')).toBeTruthy()
  expect(requests.find(request => request.init.method === 'PATCH')?.init.body)
    .toBe(JSON.stringify({ sena_politica: 'obligatoria', sena_centavos: 3005 }))
})

it.each([true, false])('solo permite alta de sillón con sede autorizada (%s)', async available => {
  let created = false
  backend({ id: 's1', rol: 'secretaria' }, (path, init) => {
    if (path === '/api/config/contexto-consultorio') {
      return Response.json({ consultorio: available ? { id: officeId, nombre: 'Sede ficticia' } : null })
    }
    if (path === '/api/config/sillones' && init.method === 'POST') {
      created = true
      return Response.json(chair, { status: 201 })
    }
    if (path === '/api/config/sillones') return Response.json(pageOf(created ? [chair] : []))
  })
  open('/config')
  const user = userEvent.setup()
  await user.click(await screen.findByRole('button', { name: 'Sillones' }))
  await user.click(await screen.findByRole('button', { name: 'Agregar sillón' }))
  if (available) {
    await user.type(await screen.findByLabelText('Nombre'), chair.nombre)
    await user.click(screen.getByRole('button', { name: 'Crear sillón' }))
    expect(await screen.findByText('Sillón creado.')).toBeTruthy()
    const post = requests.find(request => request.path === '/api/config/sillones' && request.init.method === 'POST')
    expect(post?.init.body).toBe(JSON.stringify({ consultorio_id: officeId, nombre: chair.nombre, activo: true }))
  } else {
    expect(await screen.findByText(/único consultorio activo/)).toBeTruthy()
    expect(screen.queryByRole('button', { name: 'Crear sillón' })).toBeNull()
    expect(requests.some(request => request.path === '/api/config/sillones' && request.init.method === 'POST')).toBe(false)
  }
})

it.each(['json', 'identidad', 'importe', 'red'])('respuesta %s no acreditada nunca muestra éxito ni habilita replay', async mode => {
  backend({ id: 's1', rol: 'secretaria' }, (path, init) => {
    if (path === '/api/config/tratamientos') return Response.json(pageOf([treatment]))
    if (path === `/api/config/tratamientos/${treatmentId}` && init.method === 'PATCH') {
      if (mode === 'red') throw new TypeError('fallo de transporte')
      if (mode === 'json') return Response.json({})
      return Response.json({ ...treatment, id: mode === 'identidad' ? chairId : treatmentId, precio_referencia_centavos: mode === 'importe' ? 30 : 29 })
    }
  })
  open('/config')
  const user = userEvent.setup()
  await user.click(await screen.findByRole('button', { name: `Editar ${treatment.nombre}` }))
  await user.clear(screen.getByLabelText('Precio de referencia en ARS'))
  await user.type(screen.getByLabelText('Precio de referencia en ARS'), '0,29')
  await user.click(screen.getByRole('button', { name: 'Guardar cambios' }))
  expect(await screen.findByText(/Cambios de configuración bloqueados/)).toBeTruthy()
  expect(screen.queryByText('Tratamiento actualizado.')).toBeNull()
  expect((screen.getByRole('button', { name: 'Guardar cambios' }) as HTMLButtonElement).disabled).toBe(true)
  expect(requests.filter(request => request.init.method === 'PATCH')).toHaveLength(1)
})

it.each([
  ['secretaria', 'https://evil.test', '/agenda', 'Agenda del día'],
  ['secretaria', '//evil.test', '/agenda', 'Agenda del día'],
  ['secretaria', '/agenda\\evil.test', '/agenda', 'Agenda del día'],
  ['secretaria', '/agenda\n', '/agenda', 'Agenda del día'],
  ['odontologo', '/config', '/agenda', 'Agenda del día'],
  ['secretaria', '/mis-reservas', '/agenda', 'Agenda del día'],
  ['paciente', '/agenda', '/mis-reservas', 'Mis reservas'],
])('login %s rechaza retorno incompatible %s', async (rol, destination, expected, heading) => {
  backend(null, path => path === '/auth/login' ? Response.json({ access_token: 'login-ficticio' })
    : path === '/auth/me' ? Response.json({ id: 'cuenta-ficticia', rol })
      : path === '/mis-reservas' ? Response.json([]) : undefined)
  open(`/login?returnTo=${encodeURIComponent(destination)}`)
  const user = userEvent.setup()
  await user.type(await screen.findByLabelText('Email'), 'cuenta@example.test')
  await user.type(screen.getByLabelText('Contrasena'), 'Ficticia123')
  await user.click(screen.getByRole('button', { name: 'Ingresar' }))
  expect(await screen.findByRole('heading', { name: heading })).toBeTruthy()
  expect(window.location.pathname).toBe(expected)
  expect(requests.filter(request => request.init.method !== 'GET').every(request => request.path.startsWith('/auth/'))).toBe(true)
})


it('filtra alternativas por sillón y exige volver a elegir después de cambiarlo', async () => {
  const id = '55555555-5555-4555-8555-555555555555'
  backend({ id: 's1', rol: 'secretaria' }, path => {
    if (path === '/agenda') return Response.json([{ sillon_id: chairId, sillon_nombre: 'Sillón Norte', turnos: [{
      id, tratamiento_id: treatmentId, inicio: '2026-12-02T12:00:00Z', fin: '2026-12-02T12:30:00Z',
      estado: 'reservado', paciente_nombre: 'Paciente ficticio', tratamiento_nombre: 'Control',
      tolerancia_min: 5, es_sobreturno: false, motivo_sobreturno: null,
      acciones: { confirmar: true, cancelar: true, reprogramar: true, asistencia: false, sobreturno: false },
    }] }])
    if (path === '/catalogo-publico') return Response.json({ sillones: [{ id: chairId, nombre: 'Sillón Norte' }, { id: officeId, nombre: 'Sillón Sur' }], tratamientos: [] })
    if (path === '/horarios-libres') return Response.json([chairId, officeId].map((sillon_id, index) => ({ sillon_id, inicio: '2026-12-03T1' + (index + 2) + ':00:00Z', fin: '2026-12-03T1' + (index + 2) + ':30:00Z' })))
  })
  open('/agenda')
  const user = userEvent.setup()
  await user.click(await screen.findByRole('button', { name: /^Ver turno/ }))
  await user.click(screen.getByRole('button', { name: 'Reprogramar turno' }))
  await user.click(screen.getByRole('button', { name: 'Buscar horarios' }))
  await user.selectOptions(await screen.findByLabelText('Nuevo sillón'), chairId)
  await user.click(screen.getByRole('button', { name: /09:00.*Sillón Norte/ }))
  expect(screen.getByRole('region', { name: 'Nuevo horario seleccionado' })).toBeTruthy()
  expect((screen.getByRole('button', { name: 'Aplicar cambio' }) as HTMLButtonElement).disabled).toBe(false)
  await user.selectOptions(screen.getByLabelText('Nuevo sillón'), officeId)
  expect(screen.queryByRole('region', { name: 'Nuevo horario seleccionado' })).toBeNull()
  expect((screen.getByRole('button', { name: 'Aplicar cambio' }) as HTMLButtonElement).disabled).toBe(true)
  expect(screen.queryByRole('button', { name: /09:00.*Sillón Norte/ })).toBeNull()
  expect(screen.getByRole('button', { name: /10:00.*Sillón Sur/ })).toBeTruthy()
  expect(requests.filter(row => row.init.method === 'PATCH')).toHaveLength(0)
})

it.each([0, 1000])('muestra cierre autoritativo con saldo %s sin habilitar otro cobro', async balance => {
  const id = '55555555-5555-4555-8555-555555555555'
  backend({ id: 's1', rol: 'secretaria' }, path => {
    if (path === '/agenda') return Response.json([{ sillon_id: chairId, sillon_nombre: 'Sillón Norte', turnos: [{
      id, inicio: '2026-12-02T12:00:00Z', fin: '2026-12-02T12:30:00Z', estado: 'asistido',
      paciente_nombre: 'Paciente ficticio', tratamiento_nombre: 'Control', tolerancia_min: 5, es_sobreturno: false, motivo_sobreturno: null,
    }] }])
    if (path === '/cobros/resumen/' + id) return Response.json({ precio_referencia_centavos: 10000, sena_acumulada_centavos: 3000, total_cobrado_centavos: 10000 - balance, saldo_referencia_centavos: balance, cerrado: true })
    if (path === '/cobros') return Response.json([{ id: 'cierre-ficticio', turno_id: id, monto_centavos: 7000 - balance, tipo: 'total', medio: 'transferencia', estado_mp: null, created_at: '2026-12-02T12:00:00Z' }])
  })
  open('/agenda')
  const user = userEvent.setup()
  await user.click(await screen.findByRole('button', { name: /^Ver turno/ }))
  await user.click(screen.getByRole('button', { name: 'Ver cobros del turno' }))
  const receipt = await screen.findByRole('region', { name: 'Cierre registrado' })
  expect(await within(receipt).findByText('cierre-ficticio')).toBeTruthy()
  expect(within(receipt).getByText('Transferencia')).toBeTruthy()
  expect(within(receipt).getByText('Dinero nuevo recibido')).toBeTruthy()
  expect(screen.queryByRole('button', { name: 'Registrar cobro' })).toBeNull()
  if (balance) expect(within(receipt).getByText(/diferencia respecto/)).toBeTruthy()
})
