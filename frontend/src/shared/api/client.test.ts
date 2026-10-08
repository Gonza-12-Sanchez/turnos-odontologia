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
