import { ApiError, UnauthorizedError } from '../../shared/api/client'
import type { ApiClient, ApiRequestOptions } from '../../shared/api/client'

export interface User { id: string; rol: string; nombre?: string | null }
export interface SessionState {
  status: 'loading' | 'anonymous' | 'authenticated' | 'unavailable'
  user: User | null
  message?: string
}
let cookieQueue: Promise<void> = Promise.resolve()
async function withCookieLock(operation: () => Promise<void>) {
  if (typeof navigator !== 'undefined' && navigator.locks) {
    await navigator.locks.request('turnos-auth-cookie', operation)
  } else {
    if (typeof window !== 'undefined') throw new ApiError(503, 'Este navegador no permite coordinar sesiones entre pestanas. Usa un navegador actualizado con Web Locks en HTTPS o localhost.')
    const queued = cookieQueue.then(operation, operation)
    cookieQueue = queued.catch(() => {})
    await queued
  }
}
export class Session {
  private state: SessionState = { status: 'loading', user: null }
  private token: string | undefined
  private flight: { epoch: number; promise: Promise<void> } | undefined
  private logoutFlight: Promise<void> | undefined
  private epoch = 0
  private closing = false
  private listeners = new Set<() => void>()
  readonly api: ApiClient
  constructor(api: ApiClient) { this.api = api }
  snapshot = () => this.state
  subscribe = (listener: () => void) => {
    this.listeners.add(listener)
    return () => { this.listeners.delete(listener) }
  }
  private publish(state: SessionState) {
    this.state = state
    this.listeners.forEach(listener => listener())
  }
  clear(message?: string) {
    this.epoch++
    this.token = undefined
    this.publish({ status: 'anonymous', user: null, message })
  }
  private async identify(token: string, epoch: number) {
    const user = await this.api.get<User>('/auth/me', { token })
    if (epoch !== this.epoch) return
    this.token = token
    this.publish({ status: 'authenticated', user })
  }
  restore = (): Promise<void> => {
    if (this.closing) return Promise.resolve()
    const epoch = this.epoch
    if (this.flight?.epoch === epoch) return this.flight.promise
    const run = async () => {
      if (epoch !== this.epoch || this.closing) return
      const result = await this.api.post<{ access_token: string }>('/auth/refresh', undefined, { credentials: 'include' })
      await this.identify(result.access_token, epoch)
    }
    // Cookie-mutating requests share one lock. identify uses raw API GET, never recursive recovery.
    const promise = withCookieLock(run).catch(error => {
      if (epoch !== this.epoch) return
      this.epoch++
      this.token = undefined
      this.publish({ status: error instanceof UnauthorizedError ? 'anonymous' : 'unavailable', user: null, message: error instanceof ApiError && error.status === 503 ? error.message : undefined })
    }).finally(() => { if (this.flight?.promise === promise) this.flight = undefined })
    this.flight = { epoch, promise }
    return promise
  }
  async login(email: string, password: string) {
    if (this.logoutFlight) await this.logoutFlight
    this.clear()
    const epoch = this.epoch
    await withCookieLock(async () => {
      if (epoch !== this.epoch || this.closing) return
      const result = await this.api.post<{ access_token: string }>('/auth/login', { email, password }, { credentials: 'include' })
      await this.identify(result.access_token, epoch)
    })
  }
  logout = (): Promise<void> => {
    if (this.logoutFlight) return this.logoutFlight
    const token = this.token
    this.closing = true
    this.clear()
    let message: string | undefined
    this.logoutFlight = withCookieLock(async () => {
      await this.api.post('/auth/logout', undefined, { token, credentials: 'include' })
    }).catch(() => { message = 'No se verifico el cierre en el servidor. Cierra las otras pestanas e intenta ingresar nuevamente.' })
      .finally(() => { this.clear(message); this.closing = false; this.logoutFlight = undefined })
    return this.logoutFlight
  }
  async get<T>(path: string, options: ApiRequestOptions = {}): Promise<T> {
    const epoch = this.epoch
    try {
      const result = await this.api.get<T>(path, { ...options, token: this.token })
      if (epoch !== this.epoch || this.closing) throw new UnauthorizedError()
      return result
    }
    catch (error) {
      if (!(error instanceof UnauthorizedError) || epoch !== this.epoch || this.closing) throw error
      await this.restore()
      if (!this.token || epoch !== this.epoch || this.closing) throw error
      try {
        const result = await this.api.get<T>(path, { ...options, token: this.token })
        if (epoch !== this.epoch || this.closing) throw new UnauthorizedError()
        return result
      }
      catch (retryError) { if (retryError instanceof UnauthorizedError && epoch === this.epoch) this.clear(); throw retryError }
    }
  }
  async post<T>(path: string, body: unknown, options: ApiRequestOptions = {}): Promise<T> {
    const epoch = this.epoch
    try {
      const result = await this.api.post<T>(path, body, { ...options, token: this.token })
      if (epoch !== this.epoch || this.closing) throw new UnauthorizedError()
      return result
    }
    catch (error) { if (error instanceof UnauthorizedError && epoch === this.epoch) this.clear('Ingresa nuevamente para continuar.'); throw error }
  }
  async patch<T>(path: string, body: unknown, options: ApiRequestOptions = {}): Promise<T> {
    const epoch = this.epoch
    try {
      const result = await this.api.patch<T>(path, body, { ...options, token: this.token })
      if (epoch !== this.epoch || this.closing) throw new UnauthorizedError()
      return result
    }
    catch (error) { if (error instanceof UnauthorizedError && epoch === this.epoch) this.clear('Ingresa nuevamente para continuar.'); throw error }
  }
}
