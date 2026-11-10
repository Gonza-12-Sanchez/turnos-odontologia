import { isRecord } from '../../shared/api/contracts'

export const isUuid = (value: unknown): value is string => typeof value === 'string' && /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value)
export interface Checkout {
  provider: 'mercadopago'; status: 'pendiente'; intento_id: string; checkout_url: string
  expires_at: string; monto_centavos: number; moneda: 'ARS'; modo: 'mock' | 'sandbox'
}
export function safeCheckout(value: unknown, enabled: boolean, dev: boolean): Checkout | null {
  if (!enabled || !isRecord(value) || value.provider !== 'mercadopago' || value.status !== 'pendiente' || !isUuid(value.intento_id) || value.moneda !== 'ARS' || typeof value.monto_centavos !== 'number' || !Number.isSafeInteger(value.monto_centavos) || value.monto_centavos <= 0 || typeof value.expires_at !== 'string' || Date.parse(value.expires_at) <= Date.now() || !Number.isFinite(Date.parse(value.expires_at)) || typeof value.checkout_url !== 'string') return null
  const origin = typeof location !== 'undefined' ? location.origin : 'http://localhost'
  try {
    const url = new URL(value.checkout_url, origin)
    if (url.username || url.password || url.hash) return null
    if (value.modo === 'mock') {
      if (!dev || url.origin !== origin || url.pathname !== '/pagos/retorno' || url.searchParams.get('intento_id') !== value.intento_id) return null
    } else if (value.modo === 'sandbox') {
      if (url.protocol !== 'https:' || url.port || !['sandbox.mercadopago.com.ar', 'www.mercadopago.com.ar'].includes(url.hostname) || url.pathname !== '/checkout/v1/redirect') return null
    } else return null
    return { provider: 'mercadopago', status: 'pendiente', intento_id: value.intento_id, checkout_url: value.checkout_url, expires_at: value.expires_at, monto_centavos: value.monto_centavos, moneda: 'ARS', modo: value.modo }
  } catch { return null }
}
export function ars(centavos: number) {
  const value = BigInt(centavos)
  return `ARS $ ${(value / 100n).toLocaleString('es-AR')},${String(value % 100n).padStart(2, '0')}`
}
export interface PaymentState {
  id: string; estado: 'creando_checkout' | 'pendiente' | 'aprobado' | 'rechazado' | 'expirado' | 'requiere_revision'
  monto_centavos: number; moneda: 'ARS'; expires_at: string; turno_id: string | null; requiere_contacto: boolean
}
