import { expect, test } from '@playwright/test'
import { readFile, writeFile } from 'node:fs/promises'

test('manifest instala iconos PNG 192/512 y proposito maskable', async ({ page }) => {
  await page.goto('/')
  const href = await page.locator('link[rel="manifest"]').getAttribute('href')
  const response = await page.request.get(href!)
  const manifest = await response.json()
  expect(manifest.icons).toEqual(expect.arrayContaining([
    expect.objectContaining({ sizes: '192x192', type: 'image/png' }),
    expect.objectContaining({ sizes: '512x512', purpose: 'maskable', type: 'image/png' }),
  ]))
  for (const icon of manifest.icons) {
    const image = await page.request.get(icon.src)
    expect(image.headers()['content-type']).toContain('image/png')
    expect((await image.body()).readUInt32BE(16)).toBe(Number(icon.sizes.split('x')[0]))
  }
})
for (const width of [360, 1280]) {
  test(`publico accesible a ${width}px con teclado y tactil`, async ({ page }) => {
    await page.setViewportSize({ width, height: 850 })
    await page.route('http://localhost:8000/**', route => {
      const path = new URL(route.request().url()).pathname
      return route.fulfill({ status: path === '/auth/refresh' ? 401 : 200, json: path === '/catalogo-publico' ? { sillones: [{ id: 's1', nombre: 'Sillon de prueba' }], tratamientos: [{ id: 't1', nombre: 'Control ficticio', duracion_min: 15, sena_politica: 'deshabilitada', sena_centavos: null }] } : [{ sillon_id: 's1', inicio: '2026-11-10T12:00:00Z', fin: '2026-11-10T12:15:00Z' }] })
    })
    await page.goto('/horarios?fecha=2026-11-10&tratamiento=t1')
    await page.waitForLoadState('networkidle')
    const slot = page.getByRole('button', { name: /09:00.*Sillon de prueba/ })
    await expect(slot).toBeVisible()
    await slot.focus()
    await page.keyboard.press('Enter')
    await expect(page.getByRole('region', { name: 'Resumen de reserva' })).toBeVisible()
    expect(await slot.evaluate(el => el.getBoundingClientRect().height)).toBeGreaterThanOrEqual(44)
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
    await page.screenshot({ path: `test-results/horarios-${width}.png`, fullPage: true })
    await page.getByRole('button', { name: 'Ingresar para reservar' }).click()
    await expect(page.getByLabel('Email')).toBeVisible()
    await page.getByLabel('Email').focus(); await page.keyboard.type('ficticio@example.test')
    await page.keyboard.press('Tab'); await expect(page.getByLabel('Contrasena')).toBeFocused()
  })
}

for (const path of ['/mis-reservas', '/pagos/retorno']) test(`shell offline ${path}, navegacion privada y JSON homonimo nunca se cachean`, async ({ page, context }) => {
  await page.goto('/')
  await page.evaluate(async () => { await navigator.serviceWorker.ready })
  await page.reload()
  await page.waitForFunction(() => navigator.serviceWorker.controller !== null)
  await context.setOffline(true)
  await page.goto(path)
  await expect(page.getByText(/Sin conexion/)).toBeVisible()
  const response = await page.evaluate(async () => {
    try { const response = await fetch('/mis-reservas', { headers: { Accept: 'application/json' } }); return response.headers.get('content-type') }
    catch { return 'network-failed' }
  })
  expect(response).toBe('network-failed')
  const urls = await page.evaluate(async () => {
    const entries = await Promise.all((await caches.keys()).map(async key => (await (await caches.open(key)).keys()).map(request => request.url)))
    return entries.flat()
  })
  expect(urls.some(url => /\/(auth|mis-reservas|pagos|turnos|horarios-libres|catalogo-publico)(\?|$|\/)/.test(new URL(url).pathname))).toBe(false)
  expect(await page.evaluate(() => [localStorage.length, sessionStorage.length])).toEqual([0, 0])
  await context.setOffline(false)
  await page.goto('/login'); await expect(page.getByLabel('Email')).toBeVisible()
})

test('logout invalida otras pestanas sin compartir tokens ni reservas', async ({ page, context }) => {
  let active = true
  await context.route('http://localhost:8000/**', route => {
    const path = new URL(route.request().url()).pathname
    if (path === '/auth/logout') { active = false; return route.fulfill({ status: 204 }) }
    return route.fulfill({ status: path === '/auth/refresh' && !active ? 401 : 200, json: path === '/auth/me' ? { id: 'p1', rol: 'paciente' } : path === '/mis-reservas' ? [{ id: 'r1', inicio: '2026-11-10T12:00:00Z', fin: '2026-11-10T12:15:00Z', sillon_id: 's1', sillon_nombre: 'Sillon ficticio', tratamiento_nombre: 'Reserva privada ficticia', tolerancia_min: 5, estado: 'reservado', acciones: { confirmar: true, cancelar: true } }] : { access_token: 'memory-only' } })
  })
  await page.goto('/mis-reservas'); await expect(page.getByText('Reserva privada ficticia')).toBeVisible()
  const other = await context.newPage()
  await other.goto('/mis-reservas'); await expect(other.getByText('Reserva privada ficticia')).toBeVisible()
  await page.getByRole('button', { name: 'Cerrar sesion' }).click()
  await expect(other.getByRole('heading', { name: 'Ingresar' })).toBeVisible()
  await expect(other.getByText('Reserva privada ficticia')).toHaveCount(0)
  expect(await other.evaluate(() => [localStorage.length, sessionStorage.length])).toEqual([0, 0])
})

for (const path of ['/login', '/registro']) test(`actualizacion diferida ${path} conserva formulario y se puede aplicar despues`, async ({ page }) => {
  await page.goto(path)
  await page.evaluate(async () => { await navigator.serviceWorker.ready })
  await page.reload(); await page.waitForFunction(() => !!navigator.serviceWorker.controller)
  await page.getByLabel('Email').fill('ficticio@example.test')
  const original = await readFile('dist/sw.js', 'utf8')
  try {
    await writeFile('dist/sw.js', original + '\n// browser update test\n')
    await page.evaluate(async () => { const registration = await navigator.serviceWorker.ready; await registration.update() })
    await expect(page.getByRole('complementary', { name: 'Actualizacion disponible' })).toBeVisible({ timeout: 15000 })
    await page.getByRole('button', { name: 'Mas tarde' }).click()
    await expect(page.getByLabel('Email')).toHaveValue('ficticio@example.test')
    await expect(page.getByRole('button', { name: 'Actualizar ahora' })).toBeVisible()
    await page.getByRole('button', { name: 'Actualizar ahora' }).click()
    await expect(page.getByLabel('Email')).toHaveValue('')
  } finally { await writeFile('dist/sw.js', original) }
})

test('dos pacientes ficticios no comparten la vista ni almacenamiento persistente', async ({ page }) => {
  let account = 'A'
  await page.route('http://localhost:8000/**', route => {
    const path = new URL(route.request().url()).pathname
    if (path === '/auth/logout') return route.fulfill({ status: 204 })
    if (path === '/auth/login') account = 'B'
    return route.fulfill({ status: 200, json: path === '/auth/me' ? { id: `paciente-${account}`, rol: 'paciente' } : path === '/mis-reservas' ? [{ id: `r-${account}`, inicio: '2026-11-10T12:00:00Z', fin: '2026-11-10T12:15:00Z', sillon_nombre: 'Sillon ficticio', tratamiento_nombre: `Turno privado ${account}`, tolerancia_min: 5, estado: 'reservado', acciones: { confirmar: true, cancelar: true } }] : { access_token: 'memory-only' } })
  })
  await page.goto('/mis-reservas'); await expect(page.getByText('Turno privado A')).toBeVisible()
  await page.getByRole('button', { name: 'Cerrar sesion' }).click()
  await page.getByLabel('Email').fill('ficticio-b@example.test')
  await page.getByLabel('Contrasena').fill('Ficticia123')
  await page.getByRole('button', { name: 'Ingresar' }).click()
  await expect(page.getByText('Turno privado B')).toBeVisible()
  await expect(page.getByText('Turno privado A')).toHaveCount(0)
  expect(await page.evaluate(() => [localStorage.length, sessionStorage.length])).toEqual([0, 0])
  const persisted = await page.evaluate(async () => {
    const result = []
    for (const name of await caches.keys()) for (const req of await (await caches.open(name)).keys()) result.push(req.url)
    return result
  })
  expect(persisted.some(url => url.includes('/mis-reservas') || url.includes('/auth/'))).toBe(false)
})

for (const patient of [false, true]) test(`offline no encola escrituras ${patient ? 'paciente' : 'anonimo'} y reconexion reconsulta`, async ({ page, context }) => {
  let writes = 0
  let reads = 0
  await page.route('http://localhost:8000/**', route => {
    const path = new URL(route.request().url()).pathname
    if (path === '/turnos') writes++
    if (path === '/horarios-libres') reads++
    return route.fulfill({ status: path === '/auth/refresh' && !patient ? 401 : 200, json: path === '/auth/me' ? { id: 'p1', rol: 'paciente' } : path === '/auth/refresh' ? { access_token: 'memory-only' } : path === '/catalogo-publico' ? { sillones: [{ id: 's1', nombre: 'Sillon ficticio' }], tratamientos: [{ id: 't1', nombre: 'Control ficticio', duracion_min: 15, sena_politica: 'deshabilitada', sena_centavos: null }] } : [{ sillon_id: 's1', inicio: '2026-11-10T12:00:00Z', fin: '2026-11-10T12:15:00Z' }] })
  })
  await page.goto('/horarios?fecha=2026-11-10&tratamiento=t1')
  await page.getByRole('button', { name: /09:00/ }).click()
  await context.setOffline(true)
  await expect(page.getByText(/Sin conexion/)).toBeVisible()
  await expect(page.getByRole('button', { name: patient ? 'Reservar turno' : 'Ingresar para reservar' })).toHaveCount(0)
  const oldReads = reads
  await context.setOffline(false)
  await expect(page.getByRole('button', { name: /09:00/ })).toBeVisible()
  expect(reads).toBeGreaterThan(oldReads)
  expect(writes).toBe(0)
})

for (const action of ['login', 'logout']) test(`${action} respeta Web Lock de cookie tomado en otra pestana`, async ({ page, context }) => {
  let mutations = 0
  await context.route('http://localhost:8000/**', route => {
    const path = new URL(route.request().url()).pathname
    if (path === `/auth/${action}`) mutations++
    if (path === '/auth/logout') return route.fulfill({ status: 204 })
    return route.fulfill({ status: path === '/auth/refresh' && action === 'login' ? 401 : 200, json: path === '/auth/me' ? { id: 'p1', rol: 'paciente' } : path === '/mis-reservas' ? [] : { access_token: 'memory-only' } })
  })
  await page.goto(action === 'login' ? '/login' : '/mis-reservas')
  await page.waitForLoadState('networkidle')
  const locker = await context.newPage()
  await locker.goto('/'); await locker.waitForLoadState('networkidle')
  await locker.evaluate(() => {
    void navigator.locks.request('turnos-auth-cookie', () => new Promise<void>(resolve => {
      window.addEventListener('release-auth-lock', () => resolve(), { once: true })
    }))
  })
  await expect.poll(() => locker.evaluate(async () => (await navigator.locks.query()).held?.some(lock => lock.name === 'turnos-auth-cookie'))).toBe(true)
  if (action === 'login') {
    await page.getByLabel('Email').fill('ficticio@example.test')
    await page.getByLabel('Contrasena').fill('Ficticia123')
    await page.getByRole('button', { name: 'Ingresar' }).click()
  } else await page.getByRole('button', { name: 'Cerrar sesion' }).click()
  await expect.poll(() => page.evaluate(async () => (await navigator.locks.query()).pending?.some(lock => lock.name === 'turnos-auth-cookie'))).toBe(true)
  expect(mutations).toBe(0)
  await locker.evaluate(() => window.dispatchEvent(new Event('release-auth-lock')))
  await expect.poll(() => mutations).toBe(1)
  await expect(page.getByRole('heading', { name: action === 'login' ? 'Mis reservas' : 'Ingresar' })).toBeVisible()
})
