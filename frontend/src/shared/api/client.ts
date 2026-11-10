/**
 * Cliente HTTP mínimo para la API del backend.
 *
 * El token JWT se recibe siempre por parámetro en cada llamada
 * (`options.token`); nunca se hardcodea ni se lee de un global acá.
 */

export class ApiError extends Error {
  readonly status: number
  readonly body: unknown

  constructor(status: number, message: string, body?: unknown) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.body = body
  }
}

export class UnauthorizedError extends ApiError {
  constructor(message = 'No autorizado', body?: unknown) {
    super(401, message, body)
    this.name = 'UnauthorizedError'
  }
}

export interface ApiRequestOptions {
  /** JWT Bearer; se inyecta como `Authorization: Bearer <token>`. */
  token?: string
  headers?: Record<string, string>
  query?: Record<string, string>
  signal?: AbortSignal
  credentials?: RequestCredentials
  expectedStatus?: number
}

export interface ApiClient {
  get<T>(path: string, options?: ApiRequestOptions): Promise<T>
  post<T>(path: string, body: unknown, options?: ApiRequestOptions): Promise<T>
  patch<T>(path: string, body: unknown, options?: ApiRequestOptions): Promise<T>
}

function joinUrl(baseUrl: string, path: string): string {
  const base = baseUrl.replace(/\/+$/, '')
  const clean = path.replace(/^\/+/, '')
  return `${base}/${clean}`
}

function withQuery(url: string, query?: Record<string, string>): string {
  if (!query || Object.keys(query).length === 0) return url
  const params = new URLSearchParams(query)
  return `${url}?${params.toString()}`
}

async function request<T>(
  baseUrl: string,
  path: string,
  method: 'GET' | 'POST' | 'PATCH',
  body: unknown,
  options: ApiRequestOptions = {},
): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers ?? {}),
  }
  if (options.token) {
    headers.Authorization = `Bearer ${options.token}`
  }

  const response = await fetch(withQuery(joinUrl(baseUrl, path), options.query), {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
    signal: options.signal,
    credentials: options.credentials ?? 'omit',
    cache: 'no-store',
  })

  const text = await response.text()
  let data: unknown
  if (response.headers.get('content-type')?.includes('application/json') && text) {
    try { data = JSON.parse(text) } catch { /* Invalid JSON is never displayed. */ }
  }
  if (response.status === 401) {
    throw new UnauthorizedError('No autorizado', data)
  }
  if (!response.ok) {
    throw new ApiError(response.status, 'Servicio no disponible. Intenta nuevamente.', data)
  }
  if (options.expectedStatus !== undefined && response.status !== options.expectedStatus) {
    throw new ApiError(502, 'Resultado no verificado.')
  }
  if (response.status === 204) {
    return undefined as T
  }
  if (!text) {
    return undefined as T
  }
  if (data === undefined) throw new ApiError(502, 'Respuesta no valida del servicio.')
  return data as T
}

export function createApiClient(baseUrl: string): ApiClient {
  return {
    get<T>(path: string, options?: ApiRequestOptions): Promise<T> {
      return request<T>(baseUrl, path, 'GET', undefined, options)
    },
    post<T>(path: string, body: unknown, options?: ApiRequestOptions): Promise<T> {
      return request<T>(baseUrl, path, 'POST', body, options)
    },
    patch<T>(path: string, body: unknown, options?: ApiRequestOptions): Promise<T> {
      return request<T>(baseUrl, path, 'PATCH', body, options)
    },
  }
}
