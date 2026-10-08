# CHANGES — Secuencia de Implementación

> Índice canónico de todos los changes del proyecto **turnos-odontologia** (gestión de turnos para consultorios odontológicos chicos, 1 sede, 1–3 sillones).
> Cada change es atómico: un agente puede implementarlo en una sesión (~4-6 horas).
> **Leer este archivo antes de ejecutar cualquier `/opsx:propose`.**

> Alcance MVP v1: reserva online 24/7, agenda multi-sillón con anti-solapamiento, confirmación WhatsApp, cobro simple (+ seña MP opcional). ARCA = fase 2, OOSS/HCE = fase 3+ (fuera de este roadmap, modelo ya preparado para extender).

---

## Cómo usar este documento

1. Identificar el change a implementar (verificar que sus dependencias están en `openspec/changes/archive/`).
2. Leer los docs de la knowledge-base indicados en "Leer antes".
3. Ejecutar `/opsx:propose <nombre-del-change>`.
4. Al terminar el change, archivarlo con `/opsx:archive <nombre-del-change>`.
5. Marcar el checkbox `[x]` en este archivo.

---

## Árbol de dependencias

```
C-01 foundation-setup
  └── C-02 core-models
        └── C-03 auth-jwt-rbac                 ← desbloquea TODO lo demás
              └── C-04 catalogo-config
                    └── C-05 disponibilidad-reserva     ← corazón de agenda (RN-TU-01)
                          │
                          ├── C-06 gestion-turnos
                          │     └── C-08 whatsapp-notificaciones
                          │
                          ├── C-07 agenda-mis-reservas-api   ← paralelo con C-06
                          │
                          └── C-09 cobros-sena-mp            ← paralelo con C-06/C-07
                                │
                                ├── C-10 pwa-reserva-publica   ← + C-07
                                │
                                └── C-11 pwa-agenda-gestion    ← + C-04 + C-06 + C-07 + C-09
                                      │
                                      └── C-12 hardening-e2e   ← + C-08 + C-10 + C-11
```

### Paralelismo por fase

> Cada "gate" es un punto de sincronización. Los changes dentro de un grupo pueden ejecutarse en paralelo.

```
GATE 0: ninguna
  → C-01 foundation-setup (solo)

GATE 1: C-01 ✓
  → C-02 core-models (solo)

GATE 2: C-02 ✓
  → C-03 auth-jwt-rbac (solo)

GATE 3: C-03 ✓
  → C-04 catalogo-config (solo)

GATE 4: C-04 ✓
  → C-05 disponibilidad-reserva (solo)

GATE 5: C-05 ✓                     ← PRIMER FORK (3 paralelos, backend)
  → C-06 gestion-turnos            [Agente A]
  → C-07 agenda-mis-reservas-api   [Agente C]
  → C-09 cobros-sena-mp            [Agente B]

GATE 6: C-06 ✓
  → C-08 whatsapp-notificaciones   [Agente A — si C-06 ✓]

GATE 7: backend listo              ← SEGUNDO FORK (2 frontends en paralelo)
  → C-10 pwa-reserva-publica       [Agente C — si C-05 + C-07 ✓]
  → C-11 pwa-agenda-gestion        [Agente B — si C-04 + C-06 + C-07 + C-09 ✓]

GATE 8: C-08 + C-10 + C-11 ✓
  → C-12 hardening-e2e (solo, cierra MVP)
```

### Camino crítico (8 changes — mínimo irreducible)

```
C-01 → C-02 → C-03 → C-04 → C-05 → C-06 → C-11 → C-12
```

(La rama WhatsApp C-08 y el frontend público C-10 corren en paralelo al camino crítico; el MVP no se declara listo sin C-08, pero no bloquean C-11.)

### Plan óptimo con 3 agentes

```
Paso │ Agente A (Backend Core)      │ Agente B (Backend Aux)       │ Agente C (Frontend)
─────┼──────────────────────────────┼──────────────────────────────┼─────────────────────────
  1  │ C-01 foundation-setup        │              —               │            —
  2  │ C-02 core-models             │              —               │            —
  3  │ C-03 auth-jwt-rbac           │              —               │            —
  4  │ C-04 catalogo-config         │              —               │            —
  5  │ C-05 disponibilidad-reserva  │              —               │            —
  6  │ C-06 gestion-turnos          │ C-09 cobros-sena-mp          │ C-07 agenda-mis-reservas-api
  7  │ C-08 whatsapp-notificaciones │ C-11 pwa-agenda-gestion*     │ C-10 pwa-reserva-publica
  8  │ C-12 hardening-e2e           │              —               │            —
```

`*` C-11 arranca en paso 7 cuando C-06 + C-07 + C-09 están archivados; si C-07 se demora, B ayuda en C-07 antes de C-11.

---

## FASE 0 — Cimientos

### [C-01] `foundation-setup`
- **Estado**: `[x]` verificado 2026-10-06 (compose up + happy/degraded en vivo + upgrade head exit 0)
- **Scope**: Scaffolding completo del monorepo + infraestructura base
  - Estructura de directorios según `08`: `backend/app/{api,services,workers,cobros,db}`, `backend/tests`, `frontend/src/{features,shared,pages}`, `docker-compose.yml`
  - `backend/`: Python 3.12+, FastAPI 0.115+ app mínima con `GET /api/health`, SQLAlchemy 2.x async configurado, Alembic inicializado, `shared/` con settings (Pydantic), logger, excepciones de negocio
  - `frontend/`: Vite 6 + React 18 + TypeScript 5 scaffolding PWA mobile-first, api client JWT base, Tailwind
  - `docker-compose.yml`: servicios `api + db (postgres:16) + redis:7 + frontend`, `.env.example` por sub-proyecto (`DATABASE_URL`, `REDIS_URL`, `JWT_SECRET_KEY`, `JWT_EXPIRE_MINUTES`, `WHATSAPP_PROVIDER`, `WHATSAPP_API_KEY`, `MP_ACCESS_TOKEN`, `FRONTEND_URL`, `APPOINTMENT_CANCEL_MINUTES=120`, `LATE_TOLERANCE_MINUTES=5`)
  - GitHub Actions CI: jobs paralelos backend (ruff + pytest smoke) y frontend (tsc + build); secrets solo por `${VAR}`, nada hardcodeado
  - Tests: health check + conexión DB/Redis en Compose
- **Dependencias**: ninguna
- **Governance**: BAJO
- **Leer antes**:
  - `knowledge-base/01_vision_y_objetivos.md` §Alcance v1
  - `knowledge-base/02_descripcion_general.md` §Stack tecnológico
  - `knowledge-base/08_arquitectura_propuesta.md` §Estructura de directorios
  - `knowledge-base/08_arquitectura_propuesta.md` §Variables de entorno

---

### [C-02] `core-models`
- **Estado**: `[ ]` pendiente
- **Scope**: Modelos base + constraint anti-solapamiento + migraciones iniciales + seed ficticio
  - Modelos SQLAlchemy 2.x async: `Consultorio`, `Sillon`, `Tratamiento`, `Usuario` (rol paciente|odontologo|secretaria), `Paciente` (1↔1 con Usuario rol paciente), `Turno` (inicio timestamptz + fin calculado), `Bloqueo`, `RecordatorioWA`, `Cobro` (monto en centavos ARS)
  - `AuditMixin`: `is_active`, `created_at`, `updated_at`, `deleted_at`; `origen` en Turno (online|mostrador|whatsapp) para RN-GL-03
  - Constraint de exclusión Postgres por rango en `Turno` por `(sillon_id, tstzrange(inicio, fin))` solo turnos activos (RN-TU-01, RN-GL-01); CHECK `fin > inicio`; índice GIST necesario
  - `BaseRepository[T]` genérico + `UnitOfWork`; teléfono AR validado a nivel app (no CHECK críptico)
  - Migración 001: tablas core + índices `(sillon_id, inicio)`, `(paciente_id, inicio)`, `(estado, inicio)`, `(email)`, `(rol, activo)`
  - Seed ficticio (RN-GL-02, nunca datos reales): 1 consultorio demo, 2 sillones activos, 3 tratamientos (Limpieza 30 min, Control 15 min, Conducto 60 min), 3 usuarios (secretaria, odontólogo, paciente de prueba)
  - Tests: crear turno solapado falla a nivel motor; fin = inicio + duración tratamiento
- **Dependencias**: C-01
- **Governance**: CRITICO
- **Leer antes**:
  - `knowledge-base/04_modelo_de_datos.md` §Entidades
  - `knowledge-base/04_modelo_de_datos.md` §ERD
  - `knowledge-base/05_reglas_de_negocio.md` §Dominio: Turnos (RN-TU)
  - `knowledge-base/09_decisiones_y_supuestos.md` §DD-02 y §DD-05
  - `knowledge-base/08_arquitectura_propuesta.md` §Patrones aplicados

---

## FASE 1 — Identidad y acceso

### [C-03] `auth-jwt-rbac`
- **Estado**: `[ ]` pendiente
- **Scope**: Autenticación JWT + RBAC por matriz 03 (US-002 exige login para reservar)
  - `POST /auth/registro` — alta paciente (crea Usuario + Paciente, hash bcrypt/argon2, validación teléfono AR); `POST /auth/login` — JWT access + refresh; `POST /auth/refresh` — rotación con blacklist del anterior en Redis; `POST /auth/logout` — blacklist access; `GET /auth/me`
  - Claims JWT: `sub`, `roles`, `email`, `jti`, `type`, `iat`, `exp`; refresh en cookie HttpOnly (secure, samesite=lax); expiración por `JWT_EXPIRE_MINUTES`
  - Dependencias FastAPI `require_role()`, `require_admin()` según matriz RBAC (03): anónimo R libres; paciente CRUD propio; odontólogo R agenda; secretaria CRUD todo + config; RN-TU-02 bloquea a todos por igual
  - Rate limiting 5/60s por IP+email en login/registro (Redis); decisión credential documentada: password simple v1 (IN-10-03, OTP queda como mejora, no bloquea)
  - Tests: registro + login feliz, token expirado 401, refresh rotation invalida anterior, rate limit 429, paciente no accede a `/agenda` (403), anónimo no puede `POST /turnos` (401)
- **Dependencias**: C-02
- **Governance**: CRITICO
- **Leer antes**:
  - `knowledge-base/03_actores_y_roles.md` §RBAC — Matriz de permisos
  - `knowledge-base/03_actores_y_roles.md` §Rutas públicas
  - `knowledge-base/05_reglas_de_negocio.md` §Dominio: Autenticación (RN-AU)
  - `knowledge-base/07_flujos_principales.md` §Flujo 1: Reserva online del paciente (paso login)
  - `knowledge-base/10_preguntas_abiertas.md` §IN-10-03

---

## FASE 2 — Agenda núcleo (backend)

> C-04 debe archivarse antes de C-05 (los endpoints de disponibilidad referencian sillones/tratamientos/bloqueos).

### [C-04] `catalogo-config`
- **Estado**: `[ ]` pendiente
- **Scope**: CRUD de catálogo y configuración del consultorio (solo secretaria)
  - Modelos ya creados en C-02; aquí los endpoints: `CRUD /api/config/sillones`, `CRUD /api/config/tratamientos` (nombre, `duracion_min > 0`, `precio_referencia` nullable, `activo`), `CRUD /api/config/bloqueos` (`sillon_id` nullable = todos, `desde/hasta`, motivo)
  - Reglas: desactivar sillón no borra turnos históricos (soft delete `is_active=false`); bloqueo quita disponibilidad (RN-TU-06); sobreturno NO se crea aquí (lo crea secretaria en C-06, marcado explícito)
  - Paginación estándar, validación Pydantic, auditoría de cambios de config (quién/cuándo)
  - Tests: CRUD por rol (secretaria 200, odontólogo 403, anónimo 401); tratamiento con duración 0 → 422; bloqueo solapado con turno existente → advertencia + permite (el bloqueo manda en disponibilidad futura)
- **Dependencias**: C-03
- **Governance**: MEDIO
- **Leer antes**:
  - `knowledge-base/04_modelo_de_datos.md` §Sillon, §Tratamiento, §Bloqueo
  - `knowledge-base/03_actores_y_roles.md` §RBAC — Matriz de permisos (columna Config)
  - `knowledge-base/05_reglas_de_negocio.md` §RN-TU-04 y §RN-TU-06
  - `knowledge-base/06_funcionalidades.md` §Épica 2 (contexto de agenda)

---

### [C-05] `disponibilidad-reserva`
- **Estado**: `[ ]` pendiente
- **Scope**: Disponibilidad pública + reserva con invariantes de motor (US-001, US-002 backend)
  - `GET /horarios-libres?sillon=&tratamiento=&fecha=` — público (sin login): calcula franjas reales = sillones activos − turnos activos − bloqueos, expandiendo por `duracion_min` del tratamiento (RN-TU-03/04/06); no expone datos de pacientes; cache Redis TTL corto con invalidación al crear turno
  - `POST /turnos` — requiere login paciente (RN-AU-01): valida hueco, calcula `fin = inicio + duracion`, verificación anti-solapamiento a nivel motor antes de confirmar (RN-TU-01, RN-GL-01); carrera por el mismo hueco → `409 + oferta de alternativas` (Flujo 1 caso de error)
  - Si el tratamiento exige seña: responde `402 + checkout MP` y NO crea el turno hasta webhook aprobado (RN-CO-01, implementado en C-09; aquí el contrato)
  - Agenda el recordatorio WhatsApp al reservar (evento/cola Redis, RN-NT-01; el worker se implementa en C-08, aquí solo el enqueue)
  - Tests: libres excluyen ocupados y bloqueados; reserva sin login 401; doble reserva concurrente → una 201 + otra 409; duración variable (15 vs 60 min) genera fin correcto; tratamiento con seña sin pago → turno no creado
- **Dependencias**: C-04
- **Governance**: CRITICO
- **Leer antes**:
  - `knowledge-base/05_reglas_de_negocio.md` §Dominio: Turnos (RN-TU-01 a RN-TU-06)
  - `knowledge-base/07_flujos_principales.md` §Flujo 1: Reserva online del paciente
  - `knowledge-base/06_funcionalidades.md` §Épica 1: Reserva online (US-001, US-002)
  - `knowledge-base/04_modelo_de_datos.md` §Turno
  - `knowledge-base/08_arquitectura_propuesta.md` §Patrones aplicados (exclusión en rango, capas)

---

## FASE 3 — Gestión, lectura y notificaciones (backend)

> C-06, C-07 y C-09 pueden proponerse en paralelo tras C-05. C-06 debe archivarse antes de C-08.

### [C-06] `gestion-turnos`
- **Estado**: `[ ]` pendiente
- **Scope**: Máquina de estados del turno + gestión secretaria/paciente (US-005 backend)
  - `PATCH /turnos/{id}/confirmar`, `/cancelar`, `/reprogramar`, `/marcar-asistencia` (asistido|ausente): transiciones `reservado → confirmado → asistido | cancelado | ausente`
  - Ventana RN-TU-02 a nivel motor: cancelar/reprogramar con `< 2 h` (por `APPOINTMENT_CANCEL_MINUTES`) → `422` para paciente Y secretaria; reprogramar revalida disponibilidad + anti-solapamiento (reutiliza servicio C-05)
  - Sobreturno: solo secretaria, flag explícito + motivo, marcado visual en respuestas (RN-TU-06); tolerancia 5 min informativa en payload (`LATE_TOLERANCE_MINUTES`, RN-TU-05, no bloquea)
  - Auditoría RN-GL-03: cada cambio guarda quién/cuándo/origen (online|mostrador|whatsapp)
  - Tests: cancelar a 1h → 422; secretaria tampoco puede < 2 h; reprogramar a hueco ocupado → 409; sobreturno sin rol secretaria → 403; auditoría registra origen
- **Dependencias**: C-05
- **Governance**: ALTO
- **Leer antes**:
  - `knowledge-base/06_funcionalidades.md` §Épica 2 (US-005)
  - `knowledge-base/05_reglas_de_negocio.md` §RN-TU-02, §RN-TU-05, §RN-TU-06 y §RN-GL-03
  - `knowledge-base/07_flujos_principales.md` §Flujo 3: Agenda del día
  - `knowledge-base/03_actores_y_roles.md` §RBAC — Matriz de permisos

---

### [C-07] `agenda-mis-reservas-api`
- **Estado**: `[ ]` pendiente
- **Scope**: Endpoints de lectura para odontólogo y paciente (US-003, US-004 backend)
  - `GET /agenda?fecha=&sillon=` (odontólogo/secretaria): turnos del día agrupados por sillón con paciente, tratamiento, estado, tolerancia visible, aviso de sobreturnos; `GET /mis-reservas` (paciente): solo turnos propios ordenados por fecha con estado + acciones permitidas según RN-TU-02
  - Paginación por fecha, filtros por estado/sillón; sin N+1 (eager load paciente+tratamiento+sillón); respuestas mobile-friendly (payload chico para PWA)
  - Tests: paciente solo ve lo propio (aislamiento); odontólogo ve agenda del día; turno cancelado < 2 h no ofrece acción cancelar; performance smoke con día completo multi-sillón
- **Dependencias**: C-05
- **Governance**: MEDIO
- **Leer antes**:
  - `knowledge-base/06_funcionalidades.md` §US-003 y §US-004
  - `knowledge-base/07_flujos_principales.md` §Flujo 3: Agenda del día
  - `knowledge-base/03_actores_y_roles.md` §RBAC — Matriz de permisos
  - `knowledge-base/04_modelo_de_datos.md` §Turno (índices)

---

### [C-08] `whatsapp-notificaciones`
- **Estado**: `[ ]` pendiente
- **Scope**: Recordatorio + confirmación WhatsApp automáticos con botón (US-006, única integración obligatoria v1)
  - Worker Redis (`backend/app/workers/`): al reservar (evento C-05) agenda recordatorio por plantilla Meta; reintentos con backoff; si falla el proveedor, el turno existe igual + reintento encolado (RN-NT-03, Flujo 1 caso de error)
  - `POST /webhooks/whatsapp`: recibe `confirmo|cancelo` + `message_id`; idempotencia por `message_id` (duplicados no duplican efectos); matchea turno, valida ventana 2 h si es cancelación (RN-TU-02 → rechazo con mensaje "llamar al consultorio"), actualiza estado + registra respuesta en `RecordatorioWA` (RN-NT-02/03)
  - Modelo `RecordatorioWA`: tipo, plantilla, `message_id`, estado (enviado|entregado|leido|respondido|fallido), respuesta; firma del webhook verificada; credenciales solo por env (`WHATSAPP_PROVIDER`, `WHATSAPP_API_KEY`)
  - Proveedor a elegir o mock para Etapa 6 (IN-10-02); costo/mensaje registrado en docs del change
  - Tests: reserva genera job WA; webhook `confirmo` confirma turno; `cancelo` < 2 h → rechazado; `message_id` duplicado → idempotente; proveedor caído → turno creado + reintento pendiente
- **Dependencias**: C-06
- **Governance**: ALTO
- **Leer antes**:
  - `knowledge-base/06_funcionalidades.md` §Épica 3 (US-006)
  - `knowledge-base/05_reglas_de_negocio.md` §Dominio: Notificaciones (RN-NT)
  - `knowledge-base/07_flujos_principales.md` §Flujo 2: Confirmación / cancelación por WhatsApp
  - `knowledge-base/04_modelo_de_datos.md` §RecordatorioWA
  - `knowledge-base/10_preguntas_abiertas.md` §IN-10-02 e §IN-10-04

---

### [C-09] `cobros-sena-mp`
- **Estado**: `[ ]` pendiente
- **Scope**: Cobro simple en local + seña Mercado Pago opcional (US-007 backend)
  - `POST /cobros` (secretaria): registra contra el turno `{monto centavos ARS, medio efectivo|transferencia|mercadopago, tipo seña|total}`; concilia seña previa si existía (RN-CO-02); monto inconsistente con `precio_referencia` → advertencia + permite override auditado (Flujo 4 caso de error); UI debe mostrar "sin factura electrónica en v1" (RN-CO-03)
  - Seña MP: `POST /pagos/sena` crea preferencia/intent; `POST /webhooks/mercadopago` aprueba → crea el turno pendiente (contrato C-05, RN-CO-01); pago rechazado → turno no creado + mensaje claro; idempotencia por `referencia_mp`; `estado_mp` (pendiente|aprobado)
  - Sin ARCA en v1 (fase 2, modelo listo para extender — DD-01); montos siempre en centavos ARS
  - Tests: cobro local feliz + conciliación de seña; override de monto queda auditado; webhook MP duplicado → idempotente; pago rechazado → sin turno
- **Dependencias**: C-05
- **Governance**: CRITICO
- **Leer antes**:
  - `knowledge-base/06_funcionalidades.md` §Épica 4 (US-007)
  - `knowledge-base/05_reglas_de_negocio.md` §Dominio: Cobros (RN-CO)
  - `knowledge-base/07_flujos_principales.md` §Flujo 4: Cobro y asignación en local
  - `knowledge-base/04_modelo_de_datos.md` §Cobro
  - `knowledge-base/09_decisiones_y_supuestos.md` §DD-01

---

## FASE 4 — Frontend PWA

> C-10 y C-11 pueden proponerse en paralelo cuando sus dependencias backend están archivadas. Backend antes que frontend acoplado.

### [C-10] `pwa-reserva-publica`
- **Estado**: `[ ]` pendiente
- **Scope**: PWA pública + paciente: ver libres, reservar, mis reservas (US-001/002/003 UI)
  - Pages: `/` landing, `/horarios` (ver libres sin login, filtros fecha/sillón/tratamiento, mobile-first), `/login`, `/registro`, `/mis-reservas` (lista propia + confirmar/cancelar respetando 2 h, tolerancia visible)
  - `features/reserva` + `features/mis-reservas`: api client JWT, manejo de `409 + alternativas`, `402 → checkout MP`, `422 ventana 2 h` con mensajes claros; PWA instalable, funciona bien en celular (restricción Discovery)
  - Estados de turno trazables en UI (reservado → confirmado → asistido/cancelado); sin factura electrónica: no mostrar UI de facturación
  - Tests: flujo anónimo ve libres; reservar exige login; 409 muestra alternativas; cancelar < 2 h muestra explicación
- **Dependencias**: C-05, C-07
- **Governance**: MEDIO
- **Leer antes**:
  - `knowledge-base/06_funcionalidades.md` §Épica 1 (US-001, US-002, US-003)
  - `knowledge-base/07_flujos_principales.md` §Flujo 1: Reserva online del paciente
  - `knowledge-base/08_arquitectura_propuesta.md` §Patrones aplicados (PWA mobile-first)
  - `knowledge-base/03_actores_y_roles.md` §Rutas públicas

---

### [C-11] `pwa-agenda-gestion`
- **Estado**: `[ ]` pendiente
- **Scope**: PWA consultorio: agenda del día, gestión de turnos, cobros, config (US-004/005/007 UI)
  - Pages: `/agenda` (vista día por sillón con paciente/tratamiento/estado/tolerancia, aviso de sobreturnos y solapamientos intentados), `/cobros` (registrar cobro + conciliar seña, override auditado, aviso "sin factura electrónica en v1"), `/config` (sillones, tratamientos, bloqueos — solo secretaria)
  - `features/agenda` + `features/cobros`: acciones confirmar/cancelar/reprogramar/marcar asistencia con bloqueo < 2 h también para secretaria; reprogramar revalida disponibilidad
  - RBAC en UI (oculta lo no permitido) SIN sustituir al backend (RN-GL-01); audit trail visible (quién/cuándo/origen)
  - Tests: odontólogo ve agenda; secretaria gestiona; paciente no accede a `/agenda` ni `/cobros`; sobreturno se ve marcado
- **Dependencias**: C-04, C-06, C-07, C-09
- **Governance**: MEDIO
- **Leer antes**:
  - `knowledge-base/06_funcionalidades.md` §Épica 2 (US-004, US-005) y §Épica 4 (US-007)
  - `knowledge-base/07_flujos_principales.md` §Flujo 3 y §Flujo 4
  - `knowledge-base/03_actores_y_roles.md` §RBAC — Matriz de permisos
  - `knowledge-base/05_reglas_de_negocio.md` §RN-TU-05, §RN-TU-06 y §RN-GL-01

---

## FASE 5 — Cierre MVP

### [C-12] `hardening-e2e`
- **Estado**: `[ ]` pendiente
- **Scope**: Endurecimiento y cierre del MVP v1 (listo para piloto con 1 consultorio)
  - Tests E2E felices + errores de negocio + borde (Etapa 6): doble reserva concurrente, ventana 2 h, webhook duplicado, pago rechazado, proveedor WA caído, día completo multi-sillón
  - `docker-compose.yml` final (api + db + redis + frontend) con un solo comando de levante; CI verde; variables sensibles auditadas (ninguna en repo); seeds ficticios verificados (RN-GL-02)
  - Observabilidad mínima: logs estructurados, health checks, reporte de higiene de agenda (alerta turnos sin confirmar — valida SU-02); métricas de éxito medibles (cero dobles reservas, % confirmados, tiempo secretaria)
  - Docs piloto: quién paga WhatsApp (IN-10-04), proveedor elegido (IN-10-02), seña obligatoria u opcional por tratamiento; checklist "fuera de alcance" explícito (ARCA fase 2, OOSS/HCE fase 3+)
  - Tests: suite completa verde en Compose limpio; audit trail completo por turno (RN-GL-03)
- **Dependencias**: C-08, C-10, C-11
- **Governance**: ALTO
- **Leer antes**:
  - `knowledge-base/01_vision_y_objetivos.md` §Métricas de éxito y §Fuera de alcance
  - `knowledge-base/09_decisiones_y_supuestos.md` (todas las DD + SU para validar)
  - `knowledge-base/10_preguntas_abiertas.md` (cerrar IN-10-02/04 y seña por tratamiento)
  - `knowledge-base/05_reglas_de_negocio.md` §Dominio: Excepciones globales

---

## Resumen

| Change | Nombre | Fase | Governance |
|---|---|---|---|
| C-01 | foundation-setup | 0 — Cimientos | BAJO |
| C-02 | core-models | 0 — Cimientos | CRITICO |
| C-03 | auth-jwt-rbac | 1 — Identidad y acceso | CRITICO |
| C-04 | catalogo-config | 2 — Agenda núcleo | MEDIO |
| C-05 | disponibilidad-reserva | 2 — Agenda núcleo | CRITICO |
| C-06 | gestion-turnos | 3 — Gestión/notificaciones | ALTO |
| C-07 | agenda-mis-reservas-api | 3 — Gestión/notificaciones | MEDIO |
| C-08 | whatsapp-notificaciones | 3 — Gestión/notificaciones | ALTO |
| C-09 | cobros-sena-mp | 3 — Gestión/notificaciones | CRITICO |
| C-10 | pwa-reserva-publica | 4 — Frontend PWA | MEDIO |
| C-11 | pwa-agenda-gestion | 4 — Frontend PWA | MEDIO |
| C-12 | hardening-e2e | 5 — Cierre MVP | ALTO |

Total: **12 changes** en **6 fases**. Camino crítico: **8 changes**. Gates de paralelismo: **9 (GATE 0–8)**.

Para arrancar: `/opsx:propose C-01-foundation-setup`
