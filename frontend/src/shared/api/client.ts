/**
 * Cliente HTTP mínimo para la API del backend.
 *
 * El token JWT se recibe siempre por parámetro en cada llamada
 * (`options.token`); nunca se hardcodea ni se lee de un global acá.
 */

export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

export class UnauthorizedError extends ApiError {
  constructor(message = 'No autorizado') {
    super(401, message)
    this.name = 'UnauthorizedError'
  }
}

export interface ApiRequestOptions {
  /** JWT Bearer; se inyecta como `Authorization: Bearer <token>`. */
  token?: string
  headers?: Record<string, string>
  query?: Record<string, string>
  signal?: AbortSignal
}

export interface ApiClient {
  get<T>(path: string, options?: ApiRequestOptions): Promise<T>
  post<T>(path: string, body: unknown, options?: ApiRequestOptions): Promise<T>
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
  method: 'GET' | 'POST',
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
  })

  if (response.status === 401) {
    throw new UnauthorizedError()
  }
  if (!response.ok) {
    throw new ApiError(response.status, `Request failed with status ${response.status}`)
  }
  if (response.status === 204) {
    return undefined as T
  }
  const text = await response.text()
  if (!text) {
    return undefined as T
  }
  const data: unknown = JSON.parse(text)
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
  }
}
