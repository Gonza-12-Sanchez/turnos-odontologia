import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError, UnauthorizedError, createApiClient } from './client.ts'

const BASE_URL = 'https://api.test'

function jsonResponse(payload: unknown, status = 200): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

function stubFetch(handler: () => Promise<Response>): ReturnType<typeof vi.fn> {
  const fetchMock = vi.fn(handler)
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

function lastInit(fetchMock: ReturnType<typeof vi.fn>): RequestInit {
  const call = fetchMock.mock.calls[0]
  if (!call) throw new Error('fetch no fue llamado')
  return (call[1] ?? {}) as RequestInit
}

afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

describe('createApiClient', () => {
  it.each(['GET', 'PATCH'])('abort %s cancela solicitud sin reenvio', async (method) => {
    const controller = new AbortController()
    const mock = vi.fn((_url: string, init: RequestInit) => new Promise<Response>((_resolve, reject) => {
      init.signal?.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')))
    }))
    vi.stubGlobal('fetch', mock)
    const client = createApiClient(BASE_URL)
    const result = method === 'GET' ? client.get('/horarios-libres', { signal: controller.signal }) : client.patch('/turnos/t1/cancelar', undefined, { signal: controller.signal })
    controller.abort()
    await expect(result).rejects.toMatchObject({ name: 'AbortError' })
    expect(mock).toHaveBeenCalledTimes(1)
  })
  it.each([
    [409, { detail: 'Ocupado', alternativas: [{ sillon_id: 's1', inicio: '2026-11-10T12:00:00Z', fin: '2026-11-10T12:30:00Z' }] }],
    [402, { detail: 'Se requiere sena', checkout: { intento_id: 'i1' } }],
    [422, { detail: 'Ventana minima 2 h' }],
    [422, { detail: [{ loc: ['body', 'inicio'], msg: 'Fecha invalida' }] }],
  ])('preserva body unknown para error %s sin perder contrato', async (status, body) => {
    stubFetch(async () => jsonResponse(body, status))
    await expect(createApiClient(BASE_URL).get('/turnos')).rejects.toMatchObject({ status, body })
  })

  it.each(['<html>secret stack</html>', 'upstream password=secret'])('no muestra respuesta interna no JSON', async (body) => {
    stubFetch(async () => new Response(body, { status: 503 }))
    await expect(createApiClient(BASE_URL).get('/turnos')).rejects.toMatchObject({
      status: 503, message: 'Servicio no disponible. Intenta nuevamente.', body: undefined,
    })
  })

  it.each(['confirmar', 'cancelar'])('PATCH %s lleva Bearer sin cache ni retry', async (action) => {
    const mock = stubFetch(async () => jsonResponse({ estado: action }))
    await createApiClient(BASE_URL).patch(`/turnos/t1/${action}`, undefined, { token: 'memory' })
    expect(lastInit(mock)).toMatchObject({ method: 'PATCH', cache: 'no-store', credentials: 'omit', headers: { Authorization: 'Bearer memory' } })
    expect(mock).toHaveBeenCalledTimes(1)
  })

  it.each(['/auth/login', '/auth/refresh'])('auth cookies son explicitas en %s', async (path) => {
    const mock = stubFetch(async () => jsonResponse({ access_token: 'memory' }))
    await createApiClient(BASE_URL).post(path, {}, { credentials: 'include' })
    expect(lastInit(mock).credentials).toBe('include')
  })
  it('inyecta el header Authorization Bearer con el token pasado por parámetro', async () => {
    const fetchMock = stubFetch(async () => jsonResponse({ ok: true }))
    const client = createApiClient(BASE_URL)

    await client.get<{ ok: boolean }>('/ping', { token: 'abc123' })

    const init = lastInit(fetchMock)
    const headers = init.headers as Record<string, string>
    expect(headers.Authorization).toBe('Bearer abc123')
  })

  it('no envía Authorization cuando no se pasa token', async () => {
    const fetchMock = stubFetch(async () => jsonResponse({ ok: true }))
    const client = createApiClient(BASE_URL)

    await client.get<{ ok: boolean }>('/ping')

    const init = lastInit(fetchMock)
    const headers = init.headers as Record<string, string>
    expect(headers.Authorization).toBeUndefined()
  })

  it('propaga un 401 como UnauthorizedError tipado (con status 401)', async () => {
    stubFetch(async () => new Response('Unauthorized', { status: 401 }))
    const client = createApiClient(BASE_URL)

    try {
      await client.post('/turnos', { fecha: '2026-10-07' }, { token: 'expirado' })
      expect.unreachable('debió lanzar UnauthorizedError')
    } catch (error) {
      expect(error).toBeInstanceOf(UnauthorizedError)
      expect(error).toBeInstanceOf(ApiError)
      expect((error as UnauthorizedError).status).toBe(401)
    }
  })
})
