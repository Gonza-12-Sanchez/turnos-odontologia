import { useSyncExternalStore } from 'react'
import { ApiError } from './api/client'
import { isRecord } from './api/contracts'

export function errorMessage(error: unknown): string {
  if (!(error instanceof ApiError)) return 'Resultado no verificado. Consulta Mis reservas antes de intentar nuevamente.'
  if (error.status === 401) return 'Ingresa nuevamente para continuar.'
  if (error.status === 403) return 'Tu cuenta no tiene permiso para esta accion.'
  if (error.status === 404) return 'No se encontro el recurso solicitado para tu cuenta.'
  if (error.status === 429) return 'Demasiados intentos. Espera un minuto antes de volver a ingresar.'
  if (error.status === 422) {
    const detail = isRecord(error.body) ? error.body.detail : undefined
    if (typeof detail === 'string') return detail
    return 'Revisa los datos ingresados. La solicitud no cumple las validaciones del servidor.'
  }
  return 'Servicio no disponible. Intenta nuevamente.'
}
function subscribeOnline(listener: () => void) {
  window.addEventListener('online', listener); window.addEventListener('offline', listener)
  return () => { window.removeEventListener('online', listener); window.removeEventListener('offline', listener) }
}
export function useOnline() {
  return useSyncExternalStore(subscribeOnline, () => navigator.onLine)
}
