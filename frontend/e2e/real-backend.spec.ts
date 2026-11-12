import { expect, test, type APIRequestContext } from '@playwright/test';

/**
 * E2E contra el backend REAL en http://localhost:8000 (Docker).
 * Sin interception HTTP (sin page.route): cada llamada llega al contenedor API.
 *
 * Alcance alcanzable con la DB de desarrollo actual (sin siembra de datos):
 *   - GET /catalogo-publico: publico, anonimo, 200 (listas vacias si no hay recursos).
 *   - Auth: registro 201, login 200 + access_token, /auth/me protegido 401 sin sesion.
 *   - GET /mis-reservas: protegido, 401 sin sesion; 200 lista vacia con sesion de paciente.
 *
 * No alcanzables (bloqueados por entorno, no por codigo):
 *   - reserva sin sena: POST /turnos necesita un tratamiento activo y sillón activo;
 *     la DB de desarrollo no tiene recursos siembrados (catalogo vacio).
 *   - conflicto 409: requiere una reserva previa existente.
 *   - cancelar 422: requiere una reserva dentro de la ventana de 2 h.
 */

const API = 'http://localhost:8000';

function pacienteEmail() {
  return `paciente.e2e.${Date.now()}@turnosdemo.com.ar`;
}

function pacienteTelefono() {
  // Telefono AR valido (+54 9 <area> <linea>) unico por registro para evitar
  // el unicidad de telefono en el backend.
  return `+54911${String(Date.now() % 100000000).padStart(8, '0')}`;
}

async function registrarPaciente(request: APIRequestContext, email: string) {
  return request.post(`${API}/auth/registro`, {
    data: {
      email,
      password: 'Ficticia123',
      nombre: 'Paciente E2E',
      telefono: pacienteTelefono(),
    },
  });
}

test('anonimo lee catalogo publico sin autenticacion (backend real)', async ({ request }) => {
  const res = await request.get(`${API}/catalogo-publico`);
  expect(res.status()).toBe(200);
  const body = await res.json();
  expect(body).toHaveProperty('sillones');
  expect(body).toHaveProperty('tratamientos');
  expect(Array.isArray(body.sillones)).toBe(true);
  expect(Array.isArray(body.tratamientos)).toBe(true);
  // Lectura publica: no se envio cabecera de autorizacion.
});

test('registro de paciente contra backend real', async ({ request }) => {
  const email = pacienteEmail();
  const res = await registrarPaciente(request, email);
  expect(res.status()).toBe(201);
  const body = await res.json();
  expect(body.rol).toBe('paciente');
  expect(body.email).toBe(email);
  expect(typeof body.id).toBe('string');
});

test('login obligatorio: endpoints protegidos devuelven 401 sin sesion', async ({ request }) => {
  const me = await request.get(`${API}/auth/me`);
  expect(me.status()).toBe(401);
  const reservas = await request.get(`${API}/mis-reservas`);
  expect(reservas.status()).toBe(401);
});

test('login y acceso autenticado a Mis reservas (backend real)', async ({ request }) => {
  const email = pacienteEmail();
  await registrarPaciente(request, email);

  const login = await request.post(`${API}/auth/login`, {
    data: { email, password: 'Ficticia123' },
  });
  expect(login.status()).toBe(200);
  const { access_token } = (await login.json()) as { access_token: string };
  expect(typeof access_token).toBe('string');

  const me = await request.get(`${API}/auth/me`, {
    headers: { Authorization: `Bearer ${access_token}` },
  });
  expect(me.status()).toBe(200);
  const meBody = await me.json();
  expect(meBody.rol).toBe('paciente');

  const reservas = await request.get(`${API}/mis-reservas`, {
    headers: { Authorization: `Bearer ${access_token}` },
  });
  expect(reservas.status()).toBe(200);
  expect(Array.isArray(await reservas.json())).toBe(true);
});

test.skip('reserva sin sena contra backend real', async () => {
  // BLOQUEADO POR ENTORNO: la DB de desarrollo no tiene tratamientos ni sillones
  // siembrados (GET /catalogo-publico devuelve listas vacias). POST /turnos requiere
  // un tratamiento valido, un sillón y un paciente autenticado; sin datos de siembra
  // no se puede disparar una reserva. No es una regresion de codigo.
  expect(true).toBe(true);
});

test.skip('conflicto 409 y cancelar 422 contra backend real', async () => {
  // BLOQUEADO POR ENTORNO: no existen reservas previas en la DB de desarrollo, por lo
  // que no se puede provocar un conflicto 409 ni una cancelacion fuera de ventana 422.
  // Requieren siembra de datos o un entorno con turnos existentes.
  expect(true).toBe(true);
});


test('paciente inicia sesión, recarga y cierra sesión en la PWA real', async ({ page, request }) => {
  const email = pacienteEmail();
  expect((await registrarPaciente(request, email)).status()).toBe(201);

  await page.goto('/mis-reservas');
  await expect(page.getByRole('heading', { name: 'Ingresar' })).toBeVisible();
  await page.getByLabel('Email').fill(email);
  await page.getByLabel('Contrasena').fill('Ficticia123');
  await page.getByRole('button', { name: 'Ingresar' }).click();
  await expect(page.getByRole('heading', { name: 'Mis reservas' })).toBeVisible();

  await page.reload();
  await expect(page.getByRole('heading', { name: 'Mis reservas' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Cerrar sesion' })).toBeVisible();
  await page.getByRole('button', { name: 'Cerrar sesion' }).click();
  await expect(page.getByRole('heading', { name: 'Ingresar' })).toBeVisible();
  await page.reload();
  await expect(page.getByRole('heading', { name: 'Ingresar' })).toBeVisible();
});
