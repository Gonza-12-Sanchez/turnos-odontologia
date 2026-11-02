# Design — C-02 core-models

## Context

C-01 dejó el scaffolding ejecutable (FastAPI async, SQLAlchemy `Base`, engine async, Alembic env async, settings) pero cero entidades. Este change crea el modelo de datos núcleo, el constraint de exclusión a nivel de motor (RN-TU-01) y el seed ficticio (RN-GL-02). Ver `proposal.md` — Why/What; las reglas de negocio viven en `knowledge-base/05_reglas_de_negocio.md` y el ERD en `knowledge-base/04_modelo_de_datos.md`.

Restricciones que moldean el diseño:
- Async puro (SQLAlchemy 2.x async + asyncpg); nada sync en el event loop.
- `TIMESTAMPTZ` siempre; montos en centavos `INTEGER`; nunca `Float`/`money`.
- Anti-solapamiento garantizado por el motor (RN-GL-01), no por UI.
- Datos de seed 100% ficticios (RN-GL-02).
- Enums almacenados como `VARCHAR + CHECK` (decisión D-04) para migraciones baratas.

## Goals / Non-Goals

**Goals:**
- Definir las 9 entidades del núcleo con campos, tipos, FKs, checks e índices.
- `AuditMixin` reutilizable en todas las entidades.
- Constraint `EXCLUDE USING GIST` parcial en `turno` + `btree_gist` + `CHECK(fin > inicio)` + índices.
- `BaseRepository[T]` genérico + `UnitOfWork` mínimos, listos para C-03/C-05.
- Migración Alembic `001` con tablas, extensión, índices y seed ficticio.
- `RecordatorioWA` y `Cobro` modelados ahora; su comportamiento llega en C-08/C-09.

**Non-Goals:**
- Lógica de disponibilidad/reserva, cancelación 2 h, sobreturnos (C-05/C-06).
- Auth/JWT/RBAC real y esquema password vs OTP (C-03) — solo columna `password_hash` placeholder.
- Envío WhatsApp y Mercado Pago (C-08/C-09) — solo persistencia.
- Endpoints de negocio y frontend (C-10/C-11).
- Helpers ricos de repositorio (paginación avanzada, filtros) — diferidos.

## Decisions

### D-01 — Tablas en singular, snake_case, español de dominio

`consultorio`, `sillon`, `tratamiento`, `usuario`, `paciente`, `turno`, `bloqueo`, `recordatorio_wa`, `cobro`. Consistente con el DDL canónico del guardian (`turno`) y con los nombres de la KB. Índices con prefijo `ix_<tabla>_<cols>` y constraints `ck_`/`fk_`/`ex_`.

Alternativa: tablas en plural. Se descarta: el DDL de referencia del guardian usa singular y los tests del motor referencian `turno`.

### D-02 — UUID como PK en todas las entidades

`id UUID PRIMARY KEY DEFAULT gen_random_uuid()`. Evita secuencias y facilita seeds/merges. Alternativa: `BIGSERIAL`. Se descarta por acoplamiento a DB y peor portabilidad de fixtures.

### D-03 — `AuditMixin` compartido (soft delete + timestamps)

```python
class AuditMixin:
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=sa.text("true"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now())
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

Todas las entidades heredan `Base, AuditMixin`. Soft delete = `is_active=False` + `deleted_at=now()`; nunca `DELETE` físico en flujos normales (preserva historial y FKs). `updated_at` con `onupdate` cubre RN-GL-03 (cuándo).

### D-04 — Enums como `VARCHAR + CHECK` (no PG ENUM nativo)

Columnas categóricas (`rol`, `estado`, `origen`, `tipo`, `medio`, `estado_mp`, `respuesta`, `tipo` de recordatorio) se almacenan como `VARCHAR(n)` con `CHECK (... IN (...))`.

Rationale: agregar/renombrar valores no requiere `ALTER TYPE ... ADD VALUE` ni migraciones delicadas; SQLAlchemy mapea a `str` sin tipos custom; los checks siguen garantizando dominio a nivel motor.

Alternativa: `ENUM` nativo de Postgres. Se descarta por costo de migración y rigidez en C-04/C-06 donde los estados pueden crecer.

### D-05 — `fin` calculado, nunca del cliente (RN-TU-03)

`Turno.fin` se calcula en backend/servicio como `inicio + tratamiento.duracion_min` antes del insert. La migración solo garantiza `CHECK (fin > inicio)`; la regla de cálculo se enforce en la capa de servicio (C-05) y se testea. `fin` es columna persistida (no computed) para indexar y consultar rangos eficientemente.

### D-06 — Anti-solapamiento con `EXCLUDE USING GIST` parcial (RN-TU-01)

```sql
CREATE EXTENSION IF NOT EXISTS btree_gist;

CREATE TABLE turno (
  id UUID PRIMARY KEY,
  paciente_id UUID NOT NULL REFERENCES paciente(id),
  sillon_id UUID NOT NULL REFERENCES sillon(id),
  tratamiento_id UUID NOT NULL REFERENCES tratamiento(id),
  odontologo_id UUID REFERENCES usuario(id),
  inicio TIMESTAMPTZ NOT NULL,
  fin TIMESTAMPTZ NOT NULL,
  estado VARCHAR(20) NOT NULL DEFAULT 'reservado',
  origen VARCHAR(20) NOT NULL DEFAULT 'online',
  es_sobreturno BOOLEAN NOT NULL DEFAULT FALSE,
  motivo_sobreturno TEXT,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at TIMESTAMPTZ,
  CHECK (fin > inicio),
  CHECK (estado IN ('reservado','confirmado','asistido','cancelado','ausente')),
  CHECK (origen IN ('online','mostrador','whatsapp')),
  EXCLUDE USING GIST (
    sillon_id WITH =,
    tstzrange(inicio, fin) WITH &&
  ) WHERE (is_active AND estado NOT IN ('cancelado','ausente'))
);
```

Claves (ver guardian `postgres-exclude.md`):
- `btree_gist` obligatoria (escalar `=` + rango `&&`).
- `tstzrange(inicio, fin)` es `[)` por defecto → turnos pegados (10:00–10:30 y 10:30–11:00) NO solapan.
- `WHERE` parcial: cancelados/ausentes e inactivos (soft delete) no bloquean; sin `WHERE`, el historial bloquea la agenda futura.
- `CHECK(fin > inicio)` evita rangos vacíos/degenerados.

SQLAlchemy:

```python
__table_args__ = (
    CheckConstraint("fin > inicio", name="ck_turno_fin_gt_inicio"),
    CheckConstraint("estado IN (...)", name="ck_turno_estado"),
    CheckConstraint("origen IN (...)", name="ck_turno_origen"),
    ExcludeConstraint(
        ("sillon_id", "="),
        ("tstzrange(inicio, fin)", "&&"),
        where="is_active AND estado NOT IN ('cancelado','ausente')",
        name="ex_turno_no_solape",
        using="gist",
    ),
    Index("ix_turno_sillon_inicio", "sillon_id", "inicio"),
    Index("ix_turno_paciente_inicio", "paciente_id", "inicio"),
    Index("ix_turno_estado_inicio", "estado", "inicio"),
)
```

### D-07 — `BaseRepository[T]` + `UnitOfWork` mínimos

```python
class BaseRepository(Generic[T]):
    def __init__(self, session: AsyncSession, model: type[T]) -> None: ...
    async def get(self, entity_id: UUID) -> T | None: ...
    async def add(self, entity: T) -> T: ...            # session.add + flush
    async def soft_delete(self, entity: T) -> None: ... # is_active=False, deleted_at=now()
```

Helpers ricos (listados paginados, filtros, upserts) se difieren a C-05/C-06 para no sobrediseñar. `get`/`add`/`soft_delete` cubren el 80% de los changes.

```python
class UnitOfWork:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None: ...
    async def __aenter__(self) -> "UnitOfWork": ...   # abre session
    async def __aexit__(self, exc_type, exc, tb) -> None: ...  # commit si no exc, rollback si exc, close
    async def commit(self) -> None: ...
    async def rollback(self) -> None: ...
    @property
    def session(self) -> AsyncSession: ...
```

Repositorios concretos por entidad se crean en los changes que los necesiten (C-03 auth, C-05 agenda) instanciando `BaseRepository(session, Model)`. UoW no expone repos por defecto (YAGNI); los servicios los construyen con `uow.session`.

### D-08 — Teléfono AR validado en app, no en SQL

Regex `^\+54\s?9?\s?\d{2,4}[\s-]?\d{6,8}$` en Pydantic/servicio (guardian `invariantes.md`). Sin `CHECK` críptico en la migración.

### D-09 — Seed como script idempotente separado de la migración

`backend/app/db/seed.py` con `async def seed_demo(session)` que inserta solo si no existe (por email/nombre). Se invoca manualmente o por entrypoint de Docker; la migración `001` solo crea schema. Mantiene la migración reversible y evita que `downgrade` borre datos de negocio.

Alternativa: seed dentro de la migración con `op.bulk_insert`. Se descarta: mezcla schema y datos, y el downgrade borraría turnos reales si se corre en un entorno con datos.

## Entity Definitions

Todos los campos de auditoría vienen de `AuditMixin` (`is_active`, `created_at`, `updated_at`, `deleted_at`) y no se repiten por entidad.

### `consultorio`
| Campo | Tipo | Constraints |
|---|---|---|
| id | UUID | PK |
| nombre | VARCHAR(120) | NOT NULL |
| + AuditMixin | | |

### `sillon`
| Campo | Tipo | Constraints |
|---|---|---|
| id | UUID | PK |
| consultorio_id | UUID | FK consultorio(id) NOT NULL |
| nombre | VARCHAR(80) | NOT NULL |
| + AuditMixin | | |

Índice: `ix_sillon_consultorio (consultorio_id)`.

### `tratamiento`
| Campo | Tipo | Constraints |
|---|---|---|
| id | UUID | PK |
| nombre | VARCHAR(120) | NOT NULL |
| duracion_min | INTEGER | NOT NULL, CHECK > 0 |
| precio_referencia_centavos | INTEGER | NULLABLE, CHECK >= 0 |
| + AuditMixin | | |

### `usuario`
| Campo | Tipo | Constraints |
|---|---|---|
| id | UUID | PK |
| email | VARCHAR(255) | UNIQUE, NULLABLE |
| telefono | VARCHAR(32) | UNIQUE, NULLABLE |
| password_hash | VARCHAR(255) | NOT NULL (placeholder hasta C-03) |
| rol | VARCHAR(20) | NOT NULL, CHECK IN ('paciente','odontologo','secretaria') |
| CHECK | | email IS NOT NULL OR telefono IS NOT NULL |
| + AuditMixin | | |

Índices: `uq_usuario_email (email)`, `ix_usuario_rol_activo (rol, is_active)`.

### `paciente`
| Campo | Tipo | Constraints |
|---|---|---|
| id | UUID | PK |
| usuario_id | UUID | FK usuario(id) UNIQUE NOT NULL |
| nombre | VARCHAR(120) | NOT NULL |
| telefono | VARCHAR(32) | NOT NULL |
| obra_social | VARCHAR(120) | NULLABLE |
| notas | TEXT | NULLABLE |
| + AuditMixin | | |

### `turno`
Ver D-06. Campos adicionales:
| Campo | Tipo | Constraints |
|---|---|---|
| id | UUID | PK |
| paciente_id | UUID | FK paciente(id) NOT NULL |
| sillon_id | UUID | FK sillon(id) NOT NULL |
| tratamiento_id | UUID | FK tratamiento(id) NOT NULL |
| odontologo_id | UUID | FK usuario(id) NULLABLE |
| inicio | TIMESTAMPTZ | NOT NULL |
| fin | TIMESTAMPTZ | NOT NULL |
| estado | VARCHAR(20) | NOT NULL DEFAULT 'reservado' |
| origen | VARCHAR(20) | NOT NULL DEFAULT 'online' |
| es_sobreturno | BOOLEAN | NOT NULL DEFAULT FALSE |
| motivo_sobreturno | TEXT | NULLABLE |
| + AuditMixin | | |

Índices: `ix_turno_sillon_inicio (sillon_id, inicio)`, `ix_turno_paciente_inicio (paciente_id, inicio)`, `ix_turno_estado_inicio (estado, inicio)`.

### `bloqueo`
| Campo | Tipo | Constraints |
|---|---|---|
| id | UUID | PK |
| sillon_id | UUID | FK sillon(id) NULLABLE (NULL = todos los sillones) |
| desde | TIMESTAMPTZ | NOT NULL |
| hasta | TIMESTAMPTZ | NOT NULL |
| motivo | VARCHAR(120) | NOT NULL |
| + AuditMixin | | |
| CHECK | | hasta > desde |

Índice: `ix_bloqueo_sillon_desde (sillon_id, desde)`.

### `recordatorio_wa`
| Campo | Tipo | Constraints |
|---|---|---|
| id | UUID | PK |
| turno_id | UUID | FK turno(id) NOT NULL |
| tipo | VARCHAR(20) | NOT NULL, CHECK IN ('recordatorio','confirmacion') |
| plantilla | VARCHAR(120) | NOT NULL |
| message_id | VARCHAR(120) | NULLABLE (id proveedor) |
| estado | VARCHAR(20) | NOT NULL DEFAULT 'enviado', CHECK IN ('enviado','entregado','leido','respondido','fallido') |
| respuesta | VARCHAR(20) | NULLABLE, CHECK IN ('confirmo','cancelo') |
| + AuditMixin | | |

Índice: `ix_recordatorio_turno (turno_id)`.

### `cobro`
| Campo | Tipo | Constraints |
|---|---|---|
| id | UUID | PK |
| turno_id | UUID | FK turno(id) NOT NULL |
| monto_centavos | INTEGER | NOT NULL, CHECK >= 0 |
| medio | VARCHAR(20) | NOT NULL, CHECK IN ('efectivo','transferencia','mercadopago') |
| tipo | VARCHAR(20) | NOT NULL, CHECK IN ('sena','total') |
| estado_mp | VARCHAR(20) | NULLABLE, CHECK IN ('pendiente','aprobado') |
| referencia_mp | VARCHAR(120) | NULLABLE |
| + AuditMixin | | |

Índice: `ix_cobro_turno (turno_id)`.

## Migration Plan (001)

Archivo: `backend/alembic/versions/001_core_models.py` (revision `001`, down_revision `None`/base).

Orden de `upgrade()`:
1. `op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")`.
2. Crear tablas en orden de dependencias: `consultorio` → `sillon`, `tratamiento`, `usuario` → `paciente` → `turno` → `bloqueo`, `recordatorio_wa`, `cobro`.
3. FKs, CHECKs y `EXCLUDE` en `turno` (D-06).
4. Índices listados por entidad.
5. (Opcional) `op.execute` para seed mínimo solo si `ENV=dev` — **descartado**; seed va por `app/db/seed.py` (D-09).

`downgrade()`: drop tablas en orden inverso; no se elimina la extensión (puede estar en uso por otra tabla; dejarla es seguro).

Rollback operativo: `alembic downgrade -1` (o `-base`). En producción con datos, coordinar con backup; este change aún no tiene despliegue previo.

## Seed Ficticio (RN-GL-02)

`backend/app/db/seed.py` idempotente (`seed_demo(session)`):
- 1 consultorio: "Consultorio demo".
- 2 sillones: "Sillón 1", "Sillón 2" (activos).
- 3 tratamientos: "Limpieza" 30 min, "Control" 15 min, "Conducto" 60 min; precios referencia ficticios en centavos (500000, 250000, 1200000).
- 3 usuarios (password hash placeholder compartido, rol respectivo):
  - `secretaria.demo@example.com` (secretaria)
  - `odontologo.demo@example.com` (odontologo)
  - `paciente.demo@example.com` (paciente)
- 1 paciente vinculado al usuario paciente: nombre "Paciente Demo", teléfono "+54 9 11 0000-0000", obra_social "Obra social demo", notas "Paciente de prueba (ficticio)".

Todos los emails `@example.com`; ningún DNI ni teléfono real. El script guardian (`check_turnos_invariants.py`) debe pasar con `OK`.

## Risks / Trade-offs

- [EXCLUDE mal definido (sin `WHERE` o sin `btree_gist`)] → invalida RN-TU-01. Mitigación: DDL canónico del guardian + test motor (turno solapado falla, cancelado no bloquea, sillón distinto OK) + revisión del script.
- [Fechas naive por error] → pérdida de zona horaria. Mitigación: `DateTime(timezone=True)` en modelos y `sa.DateTime(timezone=True)` en migración; script bloquea `DateTime()`.
- [Dinero en float/money] → errores de redondeo. Mitigación: `INTEGER` centavos + CHECK >= 0; script bloquea `Float`/`MONEY`.
- [Seed con datos reales] → violación RN-GL-02/privacidad. Mitigación: `@example.com`, teléfonos 0000, script heurístico; revisión manual.
- [Soft delete + EXCLUDE] → un turno soft-deleted no debe bloquear. Mitigación: `WHERE (is_active AND ...)` incluye `is_active`.
- [Concurrencia de inserts] → race condition solo si falta el constraint. Mitigación: el constraint a nivel motor rechaza con `exclusion_violation`; la capa de servicio (C-05) mapea a 409 con alternativas.
- [Migración no reversible con datos] → downgrade puede fallar si hay FKs. Mitigación: downgrade en orden inverso; en dev se recrea la DB.

## Open Questions

Ninguna que cambie el enfoque de C-02. Puntos diferidos a changes posteriores (placeholders/env, no bloquean):
- Esquema de credencial paciente (password vs OTP-WhatsApp) → C-03 (IN-10-03). `password_hash` queda NOT NULL con placeholder.
- Proveedor WhatsApp y quién paga → C-08 (IN-10-02/04). `RecordatorioWA` modelado, sin envío.
- Mercado Pago y seña obligatoria → C-09. `Cobro` modelado, sin integración.
- Asignación de odontólogo al turno y agenda por sillón → C-05/C-06 (`odontologo_id` nullable).
- Zona horaria del consultorio (columna vs default app) → se resuelve en C-04 si hace falta; default `America/Argentina/Buenos_Aires`.