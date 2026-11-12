import { expect, test } from '@playwright/test'

const turnId = '55555555-5555-4555-8555-555555555555'
const chairId = '44444444-4444-4444-8444-444444444444'

for (const width of [360, 1440]) {
  test(`agenda multisillón, privacidad y roles a ${width}px`, async ({ page, context }) => {
    await page.setViewportSize({ width, height: 900 })
    let role = 'secretaria'
    let restored = true
    await context.route('http://localhost:8000/**', async route => {
      const path = new URL(route.request().url()).pathname
      if (path === '/auth/logout') {
        restored = false
        await route.fulfill({ status: 204 })
        return
      }
      if (path === '/auth/refresh') {
        await route.fulfill({ status: restored ? 200 : 401, json: { access_token: 'ficticio' } })
        return
      }
      if (path === '/auth/login') {
        restored = true
        await route.fulfill({ json: { access_token: 'ficticio-odontologo' } })
        return
      }
      const json = path === '/auth/me' ? { id: role, rol: role }
        : path === '/agenda' ? [turnId, chairId].map((id, index) => ({
          sillon_id: id,
          sillon_nombre: `Sillón ${index + 1}`,
          turnos: [{
            id, tratamiento_id: id, paciente_nombre: `Paciente ficticio ${index + 1}`,
            tratamiento_nombre: 'Control', estado: 'reservado',
            inicio: '2026-12-02T01:00:00Z', fin: '2026-12-02T01:30:00Z',
            tolerancia_min: 5, es_sobreturno: false, motivo_sobreturno: null,
            acciones: { confirmar: role === 'secretaria', cancelar: false, reprogramar: false, asistencia: true, sobreturno: false },
          }],
        }))
          : path === '/catalogo-publico' ? { sillones: [], tratamientos: [] }
            : path.startsWith('/cobros/resumen/') ? {
              precio_referencia_centavos: 10000, sena_acumulada_centavos: 3000,
              total_cobrado_centavos: 3000, saldo_referencia_centavos: 7000, cerrado: false,
            } : {}
      await route.fulfill({ json })
    })

    await page.goto('/agenda')
    await expect(page.getByRole('heading', { name: 'Sillón 1' })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Sillón 2' })).toBeVisible()
    await expect(page.getByText('22:00')).toHaveCount(2)
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)

    await page.getByRole('button', { name: 'Ver cobros del turno' }).first().focus()
    await page.keyboard.press('Enter')
    await expect(page.getByText('Saldo de referencia')).toBeVisible()
    expect(new URL(page.url()).search).toBe('')
    await page.getByRole('link', { name: 'Agenda' }).click()
    await expect(page.getByRole('heading', { name: 'Sillón 1' })).toBeVisible()

    await context.setOffline(true)
    await expect(page.getByText('La agenda no se guarda', { exact: false })).toBeVisible()
    await expect(page.getByText('Paciente ficticio 1')).toHaveCount(0)
    await context.setOffline(false)
    await expect(page.getByText('Paciente ficticio 1')).toBeVisible()
    expect(await page.evaluate(() => [localStorage.length, sessionStorage.length])).toEqual([0, 0])

    const logout = page.waitForResponse(response => new URL(response.url()).pathname === '/auth/logout')
    await page.getByRole('button', { name: 'Cerrar sesion' }).click()
    await logout
    await expect(page.getByRole('heading', { name: 'Ingresar' })).toBeVisible()
    role = 'odontologo'
    await page.getByLabel('Email').fill('odontologo@example.test')
    await page.getByLabel('Contrasena').fill('Ficticia123')
    await page.getByRole('button', { name: 'Ingresar' }).click()
    await expect(page.getByText('Paciente ficticio 1')).toBeVisible()
    await expect(page.getByRole('button', { name: 'Ver cobros del turno' })).toHaveCount(0)
    await expect(page.getByRole('button', { name: 'Confirmar turno' })).toHaveCount(0)
    await page.goto('/cobros')
    await expect(page.getByRole('alert')).toContainText('no tiene acceso')
  })
}
