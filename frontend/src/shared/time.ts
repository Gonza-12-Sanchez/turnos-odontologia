export const timeZone = 'America/Argentina/Buenos_Aires'
export function argentinaDate(date = new Date()) {
  const parts = new Intl.DateTimeFormat('en-CA', { timeZone, year: 'numeric', month: '2-digit', day: '2-digit' }).formatToParts(date)
  return `${parts.find(p => p.type === 'year')?.value}-${parts.find(p => p.type === 'month')?.value}-${parts.find(p => p.type === 'day')?.value}`
}
export function hour(value: string) {
  return new Intl.DateTimeFormat('es-AR', { timeZone, hour: '2-digit', minute: '2-digit', hourCycle: 'h23' }).format(new Date(value))
}
export function dateTime(value: string) {
  return new Intl.DateTimeFormat('es-AR', { timeZone, dateStyle: 'medium', timeStyle: 'short', hourCycle: 'h23' }).format(new Date(value))
}
