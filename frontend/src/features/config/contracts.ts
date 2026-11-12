import { isAwareDate, isRecord } from '../../shared/api/contracts'

export interface Treatment {
  id: string
  nombre: string
  activo: boolean
  duracion_min: number
  precio_referencia_centavos: number | null
  sena_politica: 'deshabilitada' | 'opcional' | 'obligatoria'
  sena_centavos: number | null
}
export interface Page<T> { items: T[]; total: number; page: number; page_size: number }
export type Resource = 'tratamientos' | 'sillones' | 'bloqueos'
export interface Clinic { id: string; nombre: string }
export function readClinicContext(value: unknown): Clinic | null {
  if (!isRecord(value)) throw new Error("Contexto de consultorio inválido")
  const clinic = value.consultorio
  if (clinic === null) return null
  if (!isRecord(clinic) || !uuid(clinic.id) || typeof clinic.nombre !== "string" || !clinic.nombre.trim()) {
    throw new Error("Contexto de consultorio inválido")
  }
  return { id: clinic.id, nombre: clinic.nombre }
}
export interface Chair { id: string; nombre: string; activo: boolean; consultorio_id: string }
export interface Block { id: string; motivo: string; activo: boolean; sillon_id: string | null; desde: string; hasta: string }
export type Entry = { resource: 'tratamientos'; item: Treatment } | { resource: 'sillones'; item: Chair } | { resource: 'bloqueos'; item: Block }
const uuid = (value: unknown): value is string => typeof value === 'string' && /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value)
const integer = (value: unknown, min: number, max = 2147483647): value is number => typeof value === 'number' && Number.isInteger(value) && value >= min && value <= max
export function isTreatment(value: unknown): value is Treatment {
  if (!isRecord(value) || !uuid(value.id) || typeof value.nombre !== 'string' || !value.nombre.trim() || value.nombre.length > 120 || typeof value.activo !== 'boolean' || !integer(value.duracion_min, 1)) return false
  if (value.precio_referencia_centavos !== null && !integer(value.precio_referencia_centavos, 0)) return false
  if (value.sena_politica === 'deshabilitada') return value.sena_centavos === null
  return (value.sena_politica === 'opcional' || value.sena_politica === 'obligatoria') && integer(value.sena_centavos, 1)
}
export function isChair(value: unknown): value is Chair {
  return isRecord(value) && uuid(value.id) && uuid(value.consultorio_id) && typeof value.activo === 'boolean' && typeof value.nombre === 'string' && !!value.nombre.trim() && value.nombre.length <= 80
}
export function isBlock(value: unknown): value is Block {
  return isRecord(value) && uuid(value.id) && typeof value.activo === 'boolean' && (value.sillon_id === null || uuid(value.sillon_id)) && typeof value.motivo === 'string' && !!value.motivo.trim() && value.motivo.length <= 120 && isAwareDate(value.desde) && isAwareDate(value.hasta) && Date.parse(value.hasta) > Date.parse(value.desde)
}
export function readPage(value: unknown, resource: Resource, page: number, active: boolean): Page<Entry> {
  if (!isRecord(value) || !Array.isArray(value.items) || !integer(value.total, 0) || value.page !== page || !integer(value.page_size, 1, 100) || value.items.length > value.page_size || value.total < value.items.length) throw new Error('Respuesta de configuración inválida')
  let items: Entry[]
  if (resource === 'tratamientos' && value.items.every(isTreatment)) items = value.items.map(item => ({ resource, item }))
  else if (resource === 'sillones' && value.items.every(isChair)) items = value.items.map(item => ({ resource, item }))
  else if (resource === 'bloqueos' && value.items.every(isBlock)) items = value.items.map(item => ({ resource, item }))
  else throw new Error('Recurso de configuración inválido')
  if (items.some(entry => entry.item.activo !== active)) throw new Error('Filtro de actividad no respetado')
  return { items, total: value.total, page, page_size: value.page_size }
}
