# Entrega C09 / C10

Fecha de corte: 2026-11-10. Entrega parcial para continuar en otra maquina.
No es una declaracion de MVP terminado, integracion aprobada ni produccion lista.

## 1. Estado Real

| Change | Estado confirmado previamente por CLI | Que existe | Que NO esta terminado |
| --- | --- | --- | --- |
| C09 `c-09-cobros-sena-mp` | En progreso, 2/26 tareas | Diseno y seams aprobados para modo prueba | No hay codigo productivo, tests nuevos ni migraciones de cobros C09; faltan 24 tareas |
| C10 `c-10-pwa-reserva-publica` | En progreso, 16/25 tareas | Frontend publico/paciente, pruebas HTTP/DOM y Chromium | Catalogo backend, fechas, baseline backend e integracion real, cookies/proxy y pagos |
| C11 / C12 | Fuera de esta entrega | No se avanzo en estos changes | No comenzar por implicacion de este documento |

Evidencia historica de la redaccion inicial; la verificacion frontend nueva de preparacion de staging se registra mas abajo:

- C10: 118/118 tests en 5 archivos, 13/13 Chromium, lint y typecheck/build correctos. HTTP interceptado con datos ficticios: no acredita cookies reales ni backend integrado.
- C10: auditoria final historica con 8 hallazgos moderados y 2 bajos, cero altos/criticos. No es auditoria limpia ni aprobacion de release.
- Backend: Ruff correcto, 263 tests recolectados y 29 casos existentes sin servicios aprobados. No sumar ejecuciones repetidas ni atribuir esos casos a C09.
- Baseline backend completo bloqueado en setup por timeout de Redis; no hay suite completa verde ni RED/GREEN C09. El fallo auth historico mencionado en C08 no fue reproducido ni descartado.
- OpenSpec con artifacts `done`, estado `ready` o validacion estricta correcta solo acredita planning/documentacion, no implementacion funcional.

Estado Git actualizado al preparar la entrega: se recupero la metadata desde `https://github.com/Gonza-12-Sanchez/turnos-odontologia.git`, conservando el historial original de `origin/main` y los archivos locales, sin checkout ni sobrescritura del contenido de trabajo. La rama local es `handoff/c09-c10-partial`. El commit de este avance sigue pendiente al momento de esta actualizacion; no se hizo push ni PR y no se afirma que la entrega este publicada.

La redaccion inicial fue solo documental: no levanto servicios ni ejecuto builds/tests/migraciones o instalaciones. La preparacion posterior de staging recupera metadata Git, sanitiza documentacion y verifica exclusivamente el frontend existente; sus resultados se registran por separado, sin atribuirlos al backend ni a la redaccion inicial. Prohibicion absoluta: no reiniciar ni programar reinicios, cerrar sesion, cerrar aplicaciones o detener servicios ajenos. Si Docker requiere habilitar sistema o reiniciar, detenerse, no intentar resolverlo automaticamente.

### Verificacion Frontend Para Staging

2026-11-10, 00:30-00:34 -03:00, desde `frontend/`, Node 24.19.0 y npm 11.17.0 existentes. No se instalaron dependencias ni navegadores, no se modificaron fuentes/tests/config/lockfile, y no se ejecutaron backend, servicios de infraestructura ni migraciones. El puerto 4173 no tenia listener detectado antes de Playwright; el runner gestiono su propio preview de prueba.

| Comando ejecutado | Exit | Resultado nuevo |
| --- | --- | --- |
| `npm.cmd test -- --reporter=dot` | 0 | 118/118 tests en 5 archivos |
| `npm.cmd run lint` | 0 | 0 warnings y 0 errores, 31 archivos |
| `npx.cmd --no-install tsc -b` | 0 | Typecheck correcto; no existe script `typecheck` |
| `npm.cmd run build` | 0 | Vite 6.4.6, 48 modulos, 12 entradas publicas de precache |
| `npm.cmd run test:e2e` | 0 | 13/13 pruebas Chromium |

Es regresion del frontend existente, no RED/GREEN nuevo, baseline backend ni aceptacion integrada. HTTP interceptado y datos ficticios no acreditan cookies reales, PostgreSQL/Redis ni MP. `dist`, caches, reportes y capturas generados quedan fuera del staging. No se reejecutaron auditoria npm ni validaciones OpenSpec en esta pasada; sus resultados anteriores conservan caracter historico. C09 sigue 2/26 y C10 16/25, sin cierre ni aprobacion de produccion.

## 2. Diseno Aprobado

Aprobacion humana registrada el 2026-11-09 en C09/C10: implementar en MODO PRUEBA, sin pagos reales.

- Politica de sena fija por tratamiento: deshabilitada/opcional/obligatoria; centavos ARS enteros, sin float. Default deshabilitada; no inventar precios comerciales.
- No se retiene horario durante checkout. TTL de intento propuesto/aprobado: 15 minutos, no es una reserva de cupo.
- Pago aprobado sin cupo: incidencia durable `requiere_revision`, sin turno superpuesto y con devolucion MANUAL a cargo del consultorio. No reembolso automatico ni nuevo cobro como recuperacion.
- `aprobado` publico requiere turno y cobro persistidos. Un retorno del navegador con query `approved` no prueba pago.
- C09 posee politica, persistencia, cobros, checkout/webhook, reconciliacion e incidencias. C10 posee catalogo publico y UI; coordinar la proyeccion despues de los campos C09.
- Autorizacion de prueba no habilita sandbox externo sin sus permisos/credenciales, ni piloto/produccion. Responsable nominal de devoluciones y retencion legal de evidencia monetaria siguen como gates.

No sustituir PostgreSQL por SQLite ni Redis por un emulador para acreditar concurrencia/invariantes. Mantener EXCLUDE del motor, TIMESTAMPTZ, RBAC, firma y controles JWT; no desactivarlos para lograr una demo.

## 3. Que Compartir

Entregar codigo fuente, tests/fixtures ficticios, assets publicos, documentacion, manifiestos y lockfiles revisados. Incluir `AGENTS.md`, `CHANGES.md`, `knowledge-base/`, `openspec/`, Dockerfiles/Compose, `backend/pyproject.toml`, `frontend/package.json`, `frontend/package-lock.json`, `.npmrc` y ejemplos de entorno sin secretos. Revisar tambien configuraciones y archivos ocultos intencionales.

NO empaquetar la carpeta entera como si fuera segura. Excluir `.env` y variantes locales con secretos, credenciales/certificados, dumps/volumenes, `.engram` o exportaciones de memoria, configuracion personal de agentes, `node_modules`, venvs, caches, `*.egg-info`, `dist`, reportes, capturas y artefactos generados no revisados. Las rutas personales historicas de la evidencia C09 se sustituyeron por placeholders al preparar staging; mantener esa sanitizacion antes de compartir nuevas evidencias. Un `.gitignore` o `.dockerignore` no sustituye una revision de secretos/PII.

No compartir el venv temporal de la maquina original. Recrearlo desde el manifiesto. Backend no tiene requirements.txt/lock alternativo encontrado; sus rangos pueden resolver versiones distintas. Registrar versiones del nuevo entorno, no prometer reproduccion bit a bit.

## 4. Preparacion Segura

Runbook para el companero, NO ejecutado aqui. Usar una maquina con Docker Engine/Compose operativo (contenedores Linux); para Docker Desktop prever al menos 8 GB RAM y los requisitos vigentes de su sistema. Python 3.12+ para tests backend en host; Node 22+ recomendado y npm 11.17.0 para frontend. No instalar globalmente herramientas o habilitar WSL/virtualizacion por cuenta propia.

Desde la raiz, comprobaciones de solo lectura:

```sh
docker version
docker compose version
docker ps -a
docker volume ls
docker compose ls
```

Revisar puertos ocupados y recursos existentes ANTES del arranque. Si hay conflicto, elegir un entorno/puerto nuevo con configuracion revisada; no cerrar la aplicacion que usa el puerto. No usar prune, borrado de bases/volumenes, downgrade de limpieza ni `down -v`. No ejecutar el paso destructivo de limpieza de la skill project-test-runner ni la limpieza sugerida por el README raiz.

Crear entorno solo si el destino no existe; nunca sobreescribir uno ajeno:

```sh
# Linux/macOS, desde raiz: comprobar primero que no existan los destinos.
test ! -e backend/.env && cp backend/.env.example backend/.env
test ! -e frontend/.env && cp frontend/.env.example frontend/.env
```

```powershell
# Windows PowerShell, desde raiz.
if (-not (Test-Path -LiteralPath 'backend/.env')) { Copy-Item -LiteralPath 'backend/.env.example' -Destination 'backend/.env' }
if (-not (Test-Path -LiteralPath 'frontend/.env')) { Copy-Item -LiteralPath 'frontend/.env.example' -Destination 'frontend/.env' }
```

Configurar localmente, sin imprimir valores sensibles ni subir esos archivos:

- `JWT_SECRET_KEY`: secreto de desarrollo propio y robusto (>=32 caracteres), no el placeholder.
- `FRONTEND_URL`: origen exacto de la UI que se usara; Compose publica `http://localhost:4173`, pero el ejemplo backend trae `http://localhost:5173` para dev. CORS permite un origen configurado con credentials.
- `VITE_API_URL=http://localhost:8000`, sin `/api` global; `VITE_ENABLE_TEST_PAYMENTS=false`. Todo `VITE_*` es publico, nunca poner secretos alli.
- Mantener `MP_ACCESS_TOKEN` y credenciales WA vacios mientras no haya prueba autorizada. Las variables nuevas `MP_MODE`, webhook, collector y notification URL del diseno C09 aun NO estan implementadas; no creer que agregarlas activa pagos seguros.
- La cookie refresh tiene HttpOnly, Path=/auth, SameSite y Secure configurables. El ejemplo usa `COOKIE_SECURE=true`: verificar HTTPS/localhost y comportamiento real del navegador, no asumir que funciona ni bajar seguridad automaticamente. No usar `localhost` para UI y `127.0.0.1` para API indistintamente.

## 5. Docker De Aplicacion

### Limites Del Setup Actual

`docker-compose.yml` define `db` PostgreSQL 16, `redis` 7, `api` y `frontend`; volumenes nombrados `pgdata` y `redisdata`. Publica 5432, 6379, 8000 y 4173 sin limitar a loopback: no exponerlo a redes no confiables; requiere revisar aislamiento antes de usarlo.

Compose crea SOLO la base `turnos`, no `turnos_test`. Ademas fuerza `DATABASE_URL` hacia `db:5432/turnos` y `REDIS_URL` hacia `redis:6379/0`, por encima de `backend/.env`. No cambiar solo ese .env esperando redirigir los contenedores a la base de tests.

No hay bind mounts del codigo ni migracion automatica. Las imagenes existentes pueden ser viejas; `up` no demuestra que incorporen los ultimos cambios. Verificar imagen/fecha del build y contenido. El README registra historicamente PostgreSQL 17.10, mientras Compose pide 16: NO conectar una imagen de otra version mayor a un volumen existente. Esta entrega no inspecciono contenedores actuales ni afirma que haya alguno corriendo.

Se leyeron Dockerfiles y dockerignore linea por linea, con estas reservas antes de autorizar builds:

- API copia app y Alembic, instala dependencias runtime y corre sin root; NO copia tests ni instala `.[dev]`. No indicar `docker compose exec api pytest` como comando disponible.
- Frontend es build estatico mas `vite preview`, no un servidor de produccion. Su primer `npm ci` ocurre ANTES de copiar `.npmrc`, asi que no hereda de ese archivo la politica `ignore-scripts=true`. Revisar/resolver expresamente ese desvio antes de construir; no autorizar scripts de dependencias de forma implicita.
- Los dockerignore excluyen `.env` literal, no todas sus variantes. Revisar contexto de build limpio y secretos antes de `COPY .`. No incluir `.env.local`/`.env.production` sensibles ni caches/reportes.
- Vite incorpora variables al construir; Compose no pasa configuracion frontend ni build args. Un cambio de variables despues del build no reconfigura `dist`.

### Arranque Condicionado

Usar un proyecto NUEVO para no tocar volumenes de otro entorno. Nombre de ejemplo: `turnos-entrega-c09c10`. Si ya existe, elegir otro y reemplazarlo consistentemente en todos los comandos. Verificar que sus volumenes no existan y los puertos requeridos esten libres:

```sh
docker compose -p turnos-entrega-c09c10 ps -a
docker volume inspect turnos-entrega-c09c10_pgdata turnos-entrega-c09c10_redisdata
docker compose -p turnos-entrega-c09c10 config --quiet
```

La inspeccion de volumenes debe indicar ausencia para este recorrido NUEVO. Si existen, no eliminarlos ni asumir que son descartables. `config --quiet` valida sintaxis, no disponibilidad, seguridad ni funcionalidad; evitar publicar `config` expandido con secretos.

Si faltan imagenes actualizadas, hay un gate previo: revision de las reservas anteriores y autorizacion explicita para construccion LOCAL de desarrollo. Solo entonces, en la maquina del companero:

```sh
docker compose -p turnos-entrega-c09c10 build api frontend
```

No se construyeron imagenes aqui. No autoriza imagenes finales, push ni despliegue. Sin ese gate o sin imagenes verificadas, detenerse; el siguiente `--no-build` no las fabrica.

Con imagenes verificadas y proyecto/volumenes nuevos:

```sh
docker compose -p turnos-entrega-c09c10 up -d --no-build db redis
docker compose -p turnos-entrega-c09c10 ps
docker compose -p turnos-entrega-c09c10 run --rm --no-deps api python -m alembic upgrade head
docker compose -p turnos-entrega-c09c10 up -d --no-build api frontend
docker compose -p turnos-entrega-c09c10 ps
docker compose -p turnos-entrega-c09c10 logs --tail 100 api frontend
```

Esperar health de db/redis antes de migrar y detenerse ante error. `upgrade head` aplica el schema existente sobre la base NUEVA de aplicacion, no implementa C09. Revisar/sanitizar logs antes de compartir.

Verificar `http://localhost:8000/api/health` (p.ej. `curl -f` en Linux o `curl.exe -f` en Windows): buscar DB/Redis `up`, no solo HTTP 200; el health puede responder 200 degradado. UI: `http://localhost:4173`; Swagger: `http://localhost:8000/docs`. Rutas auth/turnos/pagos no llevan `/api` global; configuracion administrativa si usa `/api/config`.

Es esperable que Horarios falle al cargar catalogo mientras no exista `GET /catalogo-publico`. No inventar fixtures runtime ni abrir endpoints administrativos para ocultarlo. Arrancar contenedores NO implementa C09 ni hace pasar tests.

El comando documentado en la skill `python -m app.db.seed` NO es un cargador funcional actual: `backend/app/db/seed.py` solo define `seed_demo(session)`, sin entrypoint, y usa un hash placeholder que no habilita login. No prometer usuarios demo utilizables. Preparar datos ficticios con un procedimiento revisado/autorizado; no cargar seed en datos existentes ni usarlo como sustituto de fixtures TDD.

## 6. Baseline Backend Aislado

NO ejecutar tests contra el Compose anterior ni sobre una base existente aunque se llame `turnos_test`. `backend/tests/conftest.py` y `tests/test_auth.py` ejecutan `TRUNCATE TABLE ... CASCADE`. El chequeo del nombre de base no protege sus datos. Tests solo en una instancia NUEVA, aislada, expresamente descartable y con datos ficticios; tampoco compartir Redis con uso real.

El siguiente recorrido adapta el runbook ya registrado en C09: contenedores NUEVOS con tmpfs, sin volumenes existentes, puertos alternativos loopback. Requiere Docker Linux operativo, puertos 55432/56379 libres y permiso de provisionamiento en la maquina del companero. tmpfs consume memoria y pierde datos al detenerse: no usar para persistencia de aplicacion ni evidencia monetaria.

Primero verificar que ambos nombres esten ausentes; si existen, elegir otros sin borrarlos. Las credenciales `turnos` de estos ejemplos son ficticias, exclusivas de la instancia descartable, no secretos recuperados de un entorno real.

```sh
docker container inspect turnos-c09-pg-entrega turnos-c09-redis-entrega
```

SOLO tras verificar ausencia y puertos libres, aprovisionar:

```sh
docker run -d --name turnos-c09-pg-entrega -p 127.0.0.1:55432:5432 --tmpfs /var/lib/postgresql/data -e POSTGRES_USER=turnos -e POSTGRES_PASSWORD=turnos -e POSTGRES_DB=turnos_test postgres:16-alpine
docker run -d --name turnos-c09-redis-entrega -p 127.0.0.1:56379:6379 --tmpfs /data redis:7-alpine
docker exec turnos-c09-pg-entrega pg_isready -U turnos -d turnos_test
docker exec turnos-c09-redis-entrega redis-cli ping
docker exec turnos-c09-pg-entrega psql -U turnos -d turnos_test -c "SELECT current_database(), current_user, version();"
docker exec turnos-c09-pg-entrega psql -U turnos -d turnos_test -c "SELECT tablename FROM pg_tables WHERE schemaname='public' LIMIT 20;"
```

Esperar readiness; antes de migrar corroborar identidad, instancia recien creada y ausencia de tablas de usuario. Ante ambiguedad, STOP. Preferir Docker >=28: versiones anteriores tienen advertencia de aislamiento de puertos loopback. Estos comandos no incluyen DROP, TRUNCATE manual ni limpieza de volumenes.

Preparar un venv NUEVO en `backend/` solo si `.venv` no existe; si existe, verificarlo o elegir otro nombre, no sobreescribirlo. Usar consola dedicada para no heredar variables de otros entornos. No imprimir secretos ni instalar globalmente.

Windows PowerShell, desde `backend/`, cada paso solo si el anterior termino correctamente:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pip check
$env:DATABASE_URL = 'postgresql+asyncpg://turnos:turnos@127.0.0.1:55432/turnos_test'
$env:TEST_DATABASE_URL = $env:DATABASE_URL
$env:REDIS_URL = 'redis://127.0.0.1:56379/15'
$env:TEST_REDIS_URL = $env:REDIS_URL
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m alembic current
.\.venv\Scripts\python.exe -m pytest -q -x --tb=short
.\.venv\Scripts\python.exe -m ruff check .
```

Linux/macOS, desde `backend/`, mismas precondiciones:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m pip check
export DATABASE_URL='postgresql+asyncpg://turnos:turnos@127.0.0.1:55432/turnos_test'
export TEST_DATABASE_URL="$DATABASE_URL"
export REDIS_URL='redis://127.0.0.1:56379/15'
export TEST_REDIS_URL="$REDIS_URL"
.venv/bin/python -m alembic upgrade head
.venv/bin/python -m alembic current
.venv/bin/python -m pytest -q -x --tb=short
.venv/bin/python -m ruff check .
```

Alembic lee `DATABASE_URL`, no `TEST_DATABASE_URL`: fijar AMBAS como se muestra antes de importar app o migrar. Redis idem. No dejar procesos de aplicacion usando esta base durante tests. El backend se prueba desde fuente en host porque la imagen API no trae tests/dev; Docker suministra PostgreSQL/Redis REALES.

Si no puede crearse esta instancia nueva o falta capacidad, verificar/provisionar otra NUEVA autorizada y conservar el nombre `turnos_test`; no apuntar a una base conocida para ahorrar el paso. No ejecutar fixtures hasta confirmar aislamiento. No hay limpieza automatica al terminar.

## 7. Frontend Y Navegador

Desde `frontend/`, scripts REALES de `package.json`, sin inventar `test:unit` o `typecheck`:

```powershell
npm.cmd ci --ignore-scripts
npm.cmd test -- --reporter=dot
npm.cmd run lint
npx.cmd --no-install tsc -b
npm.cmd run build
```

`test` ya es `vitest run`; no activar UI/API de Vitest. Para desarrollo: `npm.cmd run dev -- --host localhost`. En Linux/macOS usar `npm`/`npx` sin `.cmd` para esos comandos. Mantener lockfile y `.npmrc`, no usar `audit fix --force` ni migraciones mayores improvisadas.

E2E actual en Windows, solo con instalacion de navegador autorizada y puerto 4173 LIBRE:

```powershell
npx.cmd --no-install playwright install chromium
npm.cmd run test:e2e
```

Primero construir con `npm.cmd run build`. Playwright levanta su preview con `reuseExistingServer:false`: NO correrlo contra el frontend Compose que ya ocupa 4173 ni cerrar ese servicio para liberar el puerto sin permiso. Usar un entorno/ventana de pruebas separado acordado. La instalacion de Chromium es separada de `npm ci`, no autoriza cambios de sistema ni reinicios.

LIMITACION Linux: `frontend/playwright.config.ts` fija `webServer.command` a `npm.cmd run preview ...`. Cambiar el comando exterior a `npm run test:e2e` NO corrige esto. Antes de correr E2E en Linux, adaptar/revisar ese comando a `npm run preview ...` en una tarea autorizada, o ejecutar el runner actual en Windows. Este documento no cambia la configuracion ni asegura portabilidad ya probada.

Las 13 pruebas Chromium existentes interceptan HTTP; son evidencia frontend/PWA, NO tests E2E integrados con PostgreSQL/auth/MP. Para el catalogo real no hay fallback a mocks en runtime. Web Locks y contexto seguro HTTPS/localhost son requisitos de sesion; browser sin soporte falla cerrado.

## 8. Orden Para Retomar

1. Revisar staging y completar el commit local de entrega pendiente, sin push ni publicacion implicitos; mantener C11/C12 fuera de alcance. Confirmar ownership de backend C09, catalogo backend C10 y frontend para no pisar trabajo concurrente.
2. Preparar infraestructura NUEVA y ejecutar baseline completo existente backend/frontend. Registrar versiones, comando, fecha, salida sanitizada y exit code (PowerShell: `$LASTEXITCODE` inmediatamente; shell POSIX: `$?`). Un error de entorno no es RED. Ante defecto preexistente real, STOP/reportar sin parchearlo fuera de alcance.
3. Completar C09 1.4: revalidar documentacion oficial Checkout Pro ARGENTINA, firma/redelivery, consulta payment y recuperacion por referencia. Fuentes BR/otros productos del planning no certifican AR. Cambios materiales de contrato/diseno requieren nueva revision humana.
4. Implementar C09 por slices verticales TDD: politica/persistencia; cobros locales; checkout/402/consulta; webhook atomico; cupo perdido; reconciliacion/incidencias/privacidad. Test nuevo -> RED por causa esperada -> minimo GREEN -> >=2 casos independientes por comportamiento -> review/refactor y regresion. Registrar evidencia por slice, no escribir toda la implementacion antes de probar.
5. Verificar migraciones y carreras contra PostgreSQL real/Redis real: unicidad, EXCLUDE, atomicidad Turno+Cobro+auditoria, duplicados/fuera de orden, firma/importes/moneda/receptor, Redis caido. Upgrade/downgrade solo en base NUEVA descartable; no usar downgrade como limpieza de una base de aplicacion.
6. Completar catalogo backend C10 (`GET /catalogo-publico`): activos/orden/allowlist sin PII y campos de politica reales C09; preservar RBAC de `/api/config`. Coordinar sin agregar migraciones monetarias paralelas desde C10.
7. Resolver contrato `fecha`: UI selecciona dia Argentina, backend usa limites UTC. UI muestra fecha AR completa y deshabilita franjas fuera de dia, pero NO cubre correctamente todo el dia AR. Acordar semantica y probar bordes de medianoche; no ocultar el problema filtrando datos silenciosamente. Tarea C10 4.2 sigue abierta.
8. Probar integracion real auth/cookies/refresh/login/logout, 201/409/422, reserva incierta y reconciliacion durable. Idempotency-Key del frontend no garantiza idempotencia del backend para reserva directa. No usar recarga/reintento ciego para resolver un resultado ambiguo.
9. Verificar SW/proxy/origenes: API nunca cacheada ni cola POST/PATCH; distinguir navegacion SPA HTML de fetch JSON en rutas homonimas como `/mis-reservas`. Probar offline/reconexion, privacidad entre cuentas y movil/desktop con API real, sin desactivar CORS/cookies.
10. Solo despues del gate C09, ejecutar contrato checkout/retorno/estado integrado y sandbox autorizado con datos/dinero ficticios, incluyendo rechazo, duplicados y pago sin cupo. Mantener `VITE_ENABLE_TEST_PAYMENTS=false` hasta ese gate; produccion sigue rechazada por frontend. Sin sandbox disponible, dejar constancia NO PROBADO, no reemplazarlo por mocks para aceptar.
11. Actualizar `verification.md` y tareas con evidencia real, revisar con humano y validar artifacts; no archivar ni marcar C09/C10 completos con pendientes. Validacion documental desde raiz: `openspec.cmd validate c-09-cobros-sena-mp --strict` y equivalente C10; Linux usa `openspec`. No instalar CLI global por implicacion de estos comandos.

## 9. Fuentes De Verdad

- `AGENTS.md`: reglas duras, skills, privacidad e invariantes.
- `CHANGES.md`: dependencias y alcance; C01-C08 figuran archivados, C09-C12 no cerrados. README raiz tiene conteos/estado historicos y un ejemplo de limpieza destructiva que NO debe copiarse.
- `openspec/changes/c-09-cobros-sena-mp/{proposal,design,tasks,verification}.md` y sus delta specs: diseno aprobado, 2/26, contrato OBJETIVO y gates, no API implementada.
- `openspec/changes/c-10-pwa-reserva-publica/{proposal,design,tasks,verification}.md` y sus delta specs: 16/25 conservador. Leer la seccion final de correcciones/evidencia; conteos anteriores 17/25 o 90/116 tests son historicos.
- `frontend/README.md`, `.env.example`, `package.json`, `package-lock.json`, `.npmrc`, `playwright.config.ts`, `vite.config.ts`: contratos consumidos, comandos y limites reales.
- `docker-compose.yml`, ambos Dockerfiles/dockerignore y `backend/.env.example`: infraestructura actual, distinta de un setup final C12.
- `backend/pyproject.toml`, `alembic/env.py`, `alembic/versions/001_core_models.py`, `002_config_audit.py`, `tests/conftest.py`, `tests/test_auth.py`, `app/core/config.py`, `app/main.py`: dependencias, migraciones, riesgo TRUNCATE, configuracion y rutas.
- `docs/auth.md` y KB `03_actores_y_roles.md`, `04_modelo_de_datos.md`, `05_reglas_de_negocio.md`, `07_flujos_principales.md`, `08_arquitectura_propuesta.md`, `09_decisiones_y_supuestos.md`, `10_preguntas_abiertas.md`: leer antes de implementar.

El runbook de infraestructura se contrasto estaticamente con estas fuentes y la documentacion oficial Docker sobre proyecto `-p`, tmpfs y publicacion de puertos; no se ejecuto. La verificacion frontend posterior se registra por separado y no acredita ese runbook ni integracion real. Cualquier aprobacion de cierre debe apoyarse en resultados NUEVOS y sanitizados del entorno del companero.
