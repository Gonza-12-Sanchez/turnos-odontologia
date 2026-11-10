export interface Slot { sillon_id: string; inicio: string; fin: string }
export interface Treatment {
  id: string; nombre: string; duracion_min: number
  sena_politica: 'deshabilitada' | 'opcional' | 'obligatoria'
  sena_centavos: number | null
}
export interface Catalog { sillones: { id: string; nombre: string }[]; tratamientos: Treatment[] }
export interface Booking extends Slot {
  id: string; tratamiento_id: string; estado: string; tolerancia_min: number
}
export interface Reservation extends Booking {
  sillon_nombre: string; tratamiento_nombre: string
  acciones: { confirmar: boolean; cancelar: boolean; reprogramar: boolean }
}
export function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}
export function isAwareDate(value: unknown): value is string {
  return typeof value === 'string' && /T.*(?:Z|[+-]\d{2}:\d{2})$/i.test(value) && Number.isFinite(Date.parse(value))
}
export function isSlot(value: unknown): value is Slot {
  return isRecord(value) && typeof value.sillon_id === 'string' && isAwareDate(value.inicio) && isAwareDate(value.fin) && Date.parse(value.fin) > Date.parse(value.inicio)
}
export function isCatalog(value: unknown): value is Catalog {
  if (!isRecord(value) || !Array.isArray(value.sillones) || !Array.isArray(value.tratamientos)) return false
  const named = (item: unknown): item is Record<string, unknown> => isRecord(item) && typeof item.id === 'string' && typeof item.nombre === 'string'
  return value.sillones.every(named) && value.tratamientos.every((item: unknown) => {
    if (!named(item) || typeof item.duracion_min !== 'number' || !Number.isInteger(item.duracion_min) || item.duracion_min <= 0) return false
    return item.sena_politica === 'deshabilitada' ? item.sena_centavos === null
      : (item.sena_politica === 'opcional' || item.sena_politica === 'obligatoria') && typeof item.sena_centavos === 'number' && Number.isSafeInteger(item.sena_centavos) && item.sena_centavos > 0
  })
}
