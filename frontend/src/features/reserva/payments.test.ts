import { expect, it } from 'vitest'
import { safeCheckout } from './payments'

const value = { provider: 'mercadopago', status: 'pendiente', intento_id: '11111111-1111-4111-8111-111111111111', checkout_url: 'https://sandbox.mercadopago.com.ar/checkout/v1/redirect?pref_id=test', expires_at: '2099-01-01T00:00:00Z', monto_centavos: 123456, moneda: 'ARS', modo: 'sandbox' }
it.each(['https://sandbox.mercadopago.com.ar/checkout/v1/redirect?pref_id=test', 'https://www.mercadopago.com.ar/checkout/v1/redirect?pref_id=test'])('acepta destino MP HTTPS exacto %s en modo prueba', url => {
  expect(safeCheckout({ ...value, checkout_url: url }, true, true)?.checkout_url).toBe(url)
})
it.each(['https://sandbox.mercadopago.com.ar.evil.test/pay', 'javascript:alert(1)', 'http://sandbox.mercadopago.com.ar/pay', 'https://evil.test', 'https://user:pass@sandbox.mercadopago.com.ar/pay'])('rechaza destino malicioso %s', url => {
  expect(safeCheckout({ ...value, checkout_url: url }, true, true)).toBeNull()
})
it.each([false, true])('nunca activa produccion y mock no sale de desarrollo %s', dev => {
  expect(safeCheckout({ ...value, modo: 'production' }, true, dev)).toBeNull()
  expect(safeCheckout(value, false, dev)).toBeNull()
  const mock = { ...value, modo: 'mock', checkout_url: `/pagos/retorno?intento_id=${value.intento_id}` }
  expect(Boolean(safeCheckout(mock, true, dev))).toBe(dev)
})
