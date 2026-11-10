import { afterEach, expect, it, vi } from 'vitest'
import { createApiClient, UnauthorizedError } from '../../shared/api/client'
import { Session } from './session'

const user = { id: 'p1', rol: 'paciente', nombre: 'Paciente ficticio' }
afterEach(() => vi.unstubAllGlobals())
function server(handler?: (path: string, init: RequestInit) => Response | Promise<Response>) {
  const calls: { path: string; init: RequestInit }[] = []
  vi.stubGlobal('fetch', vi.fn(async (input: string, init: RequestInit) => {
    const path = new URL(input).pathname
    calls.push({ path, init })
    if (handler) return handler(path, init)
    return Response.json(path === '/auth/me' ? user : { access_token: 'memory-only' })
  }))
  return calls
}
function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>(done => { resolve = done })
  return { promise, resolve }
}
it.each(['antes', 'despues'])('GET 401 anterior al logout no restaura cuando responde %s del cierre', async order => {
  const read = deferred<Response>()
  const close = deferred<Response>()
  let reads = 0
  const calls = server(path => {
    if (path === '/mis-reservas') return reads++ === 0 ? read.promise : Response.json([])
    if (path === '/auth/logout') return close.promise
    return Response.json(path === '/auth/me' ? user : { access_token: 'memory' })
  })
  const session = new Session(createApiClient('https://api.test'))
  await session.login('ficticio@example.test', 'Ficticia123')
  const result = session.get('/mis-reservas').catch(error => error)
  const logout = session.logout()
  if (order === 'despues') { close.resolve(new Response(null, { status: 204 })); await logout }
  read.resolve(Response.json({}, { status: 401 }))
  const outcome = await result
  if (order === 'antes') { close.resolve(new Response(null, { status: 204 })); await logout }
  expect(outcome).toBeInstanceOf(UnauthorizedError)
  expect(calls.filter(c => c.path === '/auth/refresh')).toHaveLength(0)
  expect(session.snapshot()).toMatchObject({ status: 'anonymous', user: null })
})
it('restore explicito durante cierre no muta cookie y cierre termina anonimo', async () => {
  const close = deferred<Response>()
  const calls = server(path => path === '/auth/logout' ? close.promise : Response.json(path === '/auth/me' ? user : { access_token: 'memory' }))
  const session = new Session(createApiClient('https://api.test'))
  await session.login('ficticio@example.test', 'Ficticia123')
  const logout = session.logout()
  await session.restore()
  close.resolve(new Response(null, { status: 204 })); await logout
  expect(calls.filter(c => c.path === '/auth/refresh')).toHaveLength(0)
  expect(session.snapshot()).toMatchObject({ status: 'anonymous', user: null })
})
it('GET exitoso de cuenta anterior tampoco entrega sus datos tras logout', async () => {
  const read = deferred<Response>()
  server(path => path === '/mis-reservas' ? read.promise : path === '/auth/logout' ? new Response(null, { status: 204 }) : Response.json(path === '/auth/me' ? user : { access_token: 'memory' }))
  const session = new Session(createApiClient('https://api.test'))
  await session.login('ficticio@example.test', 'Ficticia123')
  const result = session.get('/mis-reservas').catch(error => error)
  await session.logout()
  read.resolve(Response.json([{ id: 'reserva-de-cuenta-anterior' }]))
  expect(await result).toBeInstanceOf(UnauthorizedError)
})
it.each(['misma instancia', 'otra instancia'])('login B espera refresh A tardio: %s', async instance => {
  const refresh = deferred<Response>()
  let cookie = 'A'
  const events: string[] = []
  server(async (path, init) => {
    if (path === '/auth/refresh') {
      events.push('refresh-start')
      await refresh.promise
      cookie = 'A'; events.push('refresh-response')
      return Response.json({ access_token: 'A' })
    }
    if (path === '/auth/login') { cookie = 'B'; events.push('login-B'); return Response.json({ access_token: 'B' }) }
    const token = new Headers(init.headers).get('Authorization')?.replace('Bearer ', '')
    return Response.json({ ...user, id: token })
  })
  const first = new Session(createApiClient('https://api.test'))
  const second = instance === 'misma instancia' ? first : new Session(createApiClient('https://api.test'))
  const restoring = first.restore()
  await vi.waitFor(() => expect(events).toContain('refresh-start'))
  const login = second.login('cuenta-b@example.test', 'Ficticia123')
  // A browser processes Set-Cookie at this HTTP boundary, not in identify().
  refresh.resolve(Response.json({ access_token: 'A' }))
  await Promise.all([restoring, login])
  expect(events).toEqual(['refresh-start', 'refresh-response', 'login-B'])
  expect(cookie).toBe('B')
  expect(second.snapshot().user?.id).toBe('B')
})
it.each(['misma instancia', 'otra instancia'])('logout espera refresh A antes de borrar cookie: %s', async instance => {
  const refresh = deferred<Response>()
  const events: string[] = []
  server(async path => {
    if (path === '/auth/refresh') { events.push('refresh-start'); await refresh.promise; events.push('refresh-response'); return Response.json({ access_token: 'A' }) }
    if (path === '/auth/logout') { events.push('logout'); return new Response(null, { status: 204 }) }
    return Response.json(user)
  })
  const first = new Session(createApiClient('https://api.test'))
  const second = instance === 'misma instancia' ? first : new Session(createApiClient('https://api.test'))
  const restoring = first.restore()
  await vi.waitFor(() => expect(events).toContain('refresh-start'))
  const logout = second.logout()
  refresh.resolve(Response.json({ access_token: 'A' }))
  await Promise.all([restoring, logout])
  expect(events).toEqual(['refresh-start', 'refresh-response', 'logout'])
  expect(second.snapshot().user).toBeNull()
})
it.each(['post', 'patch'] as const)('%s 401 de cuenta anterior no cierra cuenta nueva', async method => {
  const write = deferred<Response>()
  let account = 'A'
  server((path, init) => {
    if (path === '/turnos') return write.promise
    if (path === '/auth/login') { account = String(JSON.parse(String(init.body)).email); return Response.json({ access_token: account }) }
    return Response.json({ ...user, id: account })
  })
  const session = new Session(createApiClient('https://api.test'))
  await session.login('cuenta-a@example.test', 'Ficticia123')
  const pending = session[method]('/turnos', {}).catch(error => error)
  await session.login('cuenta-b@example.test', 'Ficticia123')
  write.resolve(Response.json({}, { status: 401 }))
  expect(await pending).toBeInstanceOf(UnauthorizedError)
  expect(session.snapshot().user?.id).toBe('cuenta-b@example.test')
})
it.each(['restore', 'login'] as const)('navegador sin Web Locks falla cerrado antes de %s y no muta cookie', async operation => {
  vi.stubGlobal('window', {})
  vi.stubGlobal('navigator', {})
  const calls = server()
  const session = new Session(createApiClient('https://api.test'))
  if (operation === 'restore') await session.restore()
  else await session.login('ficticio@example.test', 'Ficticia123').catch(() => {})
  expect(calls).toHaveLength(0)
  expect(session.snapshot().user).toBeNull()
})
it.each([401, 503])('restore %s invalida tambien GET exitoso pendiente de esa generacion', async status => {
  const read = deferred<Response>()
  server(path => path === '/auth/refresh' ? Response.json({}, { status }) : path === '/mis-reservas' ? read.promise : Response.json(path === '/auth/me' ? user : { access_token: 'A' }))
  const session = new Session(createApiClient('https://api.test'))
  await session.login('ficticio@example.test', 'Ficticia123')
  const pending = session.get('/mis-reservas').catch(error => error)
  await session.restore()
  read.resolve(Response.json([{ id: 'reserva-anterior' }]))
  expect(await pending).toBeInstanceOf(UnauthorizedError)
})
it('logout sin coordinacion disponible limpia memoria e informa cierre no verificado', async () => {
  const calls = server()
  const session = new Session(createApiClient('https://api.test'))
  await session.login('ficticio@example.test', 'Ficticia123')
  vi.stubGlobal('window', {}); vi.stubGlobal('navigator', {})
  await session.logout().catch(() => {})
  expect(session.snapshot().user).toBeNull()
  expect(session.snapshot().message).toMatch(/No se verifico el cierre/)
  expect(calls.some(c => c.path === '/auth/logout')).toBe(false)
})
it('restaura una sola vez en paralelo y usa cookie solo para auth', async () => {
  const calls = server()
  const session = new Session(createApiClient('https://api.test'))
  await Promise.all([session.restore(), session.restore()])
  expect(session.snapshot()).toMatchObject({ status: 'authenticated', user })
  expect(calls.filter(c => c.path === '/auth/refresh')).toHaveLength(1)
  expect(calls[0].init.credentials).toBe('include')
  expect(calls[1].init.headers).toMatchObject({ Authorization: 'Bearer memory-only' })
})
it.each([401, 503])('restauracion %s distingue anonimo de servicio caido', async (status) => {
  server(() => Response.json({ detail: 'No disponible' }, { status }))
  const session = new Session(createApiClient('https://api.test'))
  await session.restore()
  expect(session.snapshot().status).toBe(status === 401 ? 'anonymous' : 'unavailable')
})
it('login usa /me y logout fallido borra identidad pero informa cierre no verificado', async () => {
  server(path => path === '/auth/logout' ? Response.json({}, { status: 503 }) : Response.json(path === '/auth/me' ? user : { access_token: 'memory-only' }))
  const session = new Session(createApiClient('https://api.test'))
  await session.login('ficticio@example.test', 'Ficticia123')
  expect(session.snapshot().user?.id).toBe('p1')
  await session.logout()
  expect(session.snapshot()).toMatchObject({ status: 'anonymous', user: null })
  expect(session.snapshot().message).toMatch(/no se verifico/i)
})
it('no reintenta escrituras 401 ni mantiene la cuenta anterior', async () => {
  const calls = server(path => Response.json(path === '/turnos' ? {} : path === '/auth/me' ? user : { access_token: 't' }, { status: path === '/turnos' ? 401 : 200 }))
  const session = new Session(createApiClient('https://api.test'))
  await session.login('ficticio@example.test', 'Ficticia123')
  await expect(session.post('/turnos', {})).rejects.toBeInstanceOf(UnauthorizedError)
  expect(calls.filter(c => c.path === '/turnos')).toHaveLength(1)
  expect(session.snapshot().user).toBeNull()
})
it('GET expirados coordinan refresh y reintentan una sola vez cada uno', async () => {
  let expired = true
  const calls = server(path => {
    if (path === '/auth/refresh') { expired = false; return Response.json({ access_token: 'fresh' }) }
    if (path === '/auth/me') return Response.json(user)
    if (path === '/mis-reservas') return Response.json([], { status: expired ? 401 : 200 })
    return Response.json({ access_token: 'old' })
  })
  const session = new Session(createApiClient('https://api.test'))
  await session.login('ficticio@example.test', 'Ficticia123')
  const result = await Promise.all([session.get('/mis-reservas'), session.get('/mis-reservas')])
  expect(result).toEqual([[], []])
  expect(calls.filter(c => c.path === '/auth/refresh')).toHaveLength(1)
  expect(calls.filter(c => c.path === '/mis-reservas')).toHaveLength(4)
})
it('logout exitoso borra cuenta e ignora restauracion tardia', async () => {
  let resolve: (r: Response) => void = () => {}
  const calls = server(path => path === '/auth/refresh' ? new Promise<Response>(done => { resolve = done }) : path === '/auth/logout' ? new Response(null, { status: 204 }) : Response.json(user))
  const session = new Session(createApiClient('https://api.test'))
  const restoring = session.restore()
  await vi.waitFor(() => expect(calls.some(c => c.path === '/auth/refresh')).toBe(true))
  const closing = session.logout()
  resolve(Response.json({ access_token: 'late' }))
  await Promise.all([restoring, closing])
  expect(session.snapshot()).toMatchObject({ status: 'anonymous', user: null })
})
