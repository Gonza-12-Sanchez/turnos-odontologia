# Spec Delta — core/models

## Purpose

Persistencia e invariantes del modelo de datos núcleo del sistema de turnos odontológicos: nueve entidades de dominio, AuditMixin compartido, constraint de exclusión a nivel de motor contra doble reserva (RN-TU-01), reglas de almacenamiento TIMESTAMPTZ y centavos INTEGER, migración Alembic 001 con btree_gist e índices, y seed ficticio (RN-GL-02).

## ADDED Requirements

### Requirement: Turno anti-overlap enforced at the database engine

The system SHALL reject any insert or update that creates two active, non-cancelled and non-absent Turnos overlapping in the same Sillon, via a partial `EXCLUDE USING GIST (sillon_id WITH =, tstzrange(inicio, fin) WITH &&) WHERE (is_active AND estado NOT IN ('cancelado','ausente'))` constraint, independent of application-level validation (RN-TU-01, RN-GL-01).

#### Scenario: Turno válido en sillón libre se persiste (feliz)

- **GIVEN** un sillón activo sin turnos en el rango solicitado y un tratamiento con duración conocida
- **WHEN** se inserta un Turno con inicio T y fin = T + duración del tratamiento
- **THEN** el motor persiste el Turno y `fin` queda igual a `inicio + duración` del tratamiento

#### Scenario: Turno solapado en mismo sillón es rechazado por el motor (error de negocio)

- **GIVEN** ya existe un Turno activo en el sillón S en el rango [T, T+30min)
- **WHEN** se intenta insertar otro Turno activo en el mismo sillón S con rango que se solapa
- **THEN** el motor rechaza la operación con `exclusion_violation` (IntegrityError), sin depender de validación de aplicación

#### Scenario: Cancelado/soft-deleted no bloquea; sillones distintos y turnos pegados no solapan (borde)

- **GIVEN** existe un Turno en el sillón S en [T, T+30min) con estado='cancelado' o is_active=false, o un Turno en otro sillón, o un Turno cuyo fin coincide exactamente con el inicio del nuevo
- **WHEN** se inserta un nuevo Turno en el sillón S en el rango adyacente o equivalente
- **THEN** el motor acepta el insert (cancelados e inactivos no bloquean, distintos sillones no se bloquean, rangos [) adyacentes no solapan)

### Requirement: Turno fin is computed from treatment duration

The system SHALL persist `Turno.fin` as a stored TIMESTAMPTZ column computed by the backend as `inicio + tratamiento.duracion_min`; the client SHALL NOT supply `fin`, and the database SHALL enforce `fin > inicio` via CHECK (RN-TU-03).

#### Scenario: fin calculado a partir de la duración del tratamiento

- **GIVEN** un tratamiento con duración D minutos
- **WHEN** se crea un Turno con inicio I para ese tratamiento
- **THEN** `fin = I + D minutos` y se cumple `fin > inicio`

### Requirement: All temporal columns use TIMESTAMPTZ

The system SHALL store every date/time column (`Turno.inicio`, `Turno.fin`, `Bloqueo.desde`, `Bloqueo.hasta`, `AuditMixin.created_at`, `updated_at`, `deleted_at`) as TIMESTAMPTZ (timezone-aware); naive timestamps SHALL be rejected.

#### Scenario: Timestamps con zona horaria persistidos correctamente

- **GIVEN** un valor temporal con zona horaria
- **WHEN** se persiste en cualquier columna temporal del modelo core
- **THEN** se almacena como TIMESTAMPTZ y la lectura devuelve un datetime timezone-aware

#### Scenario: Timestamp naive es rechazado (borde)

- **GIVEN** un datetime sin tzinfo
- **WHEN** se intenta persistirlo en una columna temporal core
- **THEN** el sistema rechaza la operación (no se acepta naive)

### Requirement: Monetary amounts stored as INTEGER centavos

The system SHALL store every monetary amount (`Cobro.monto_centavos`, `Tratamiento.precio_referencia_centavos`) as INTEGER centavos ARS with CHECK >= 0; floating-point or money types SHALL NOT be used (RN-CO-03).

#### Scenario: Monto en centavos persistido como entero

- **GIVEN** un cobro de 500000 centavos
- **WHEN** se persiste en `Cobro.monto_centavos`
- **THEN** se almacena como INTEGER y la lectura devuelve el mismo entero

### Requirement: AuditMixin provides soft-delete and audit timestamps

The system SHALL include in every core entity an AuditMixin with `is_active` (default true), `created_at`, `updated_at` (auto-updated on change) and `deleted_at` (nullable); normal flows SHALL soft-delete (`is_active=false` + `deleted_at=now()`) and never physically DELETE (RN-GL-03).

#### Scenario: Soft delete marca is_active=false y deleted_at

- **GIVEN** una entidad core existente
- **WHEN** se ejecuta soft_delete
- **THEN** `is_active` pasa a false, `deleted_at` se setea con timestamp actual y el registro permanece en la tabla

### Requirement: Migration 001 creates core schema with btree_gist and indexes

The system SHALL provide Alembic migration `001` that creates the `btree_gist` extension and all nine core tables in dependency order, with FKs, CHECK constraints, the partial EXCLUDE constraint on `turno`, and the specified indexes (`sillon_id, inicio`, `paciente_id, inicio`, `estado, inicio`, `email`, `rol, is_active`, plus per-entity indexes).

#### Scenario: Migración 001 upgrade crea el esquema completo

- **GIVEN** una base de datos vacía
- **WHEN** se ejecuta `alembic upgrade head` (revisión 001)
- **THEN** existen las 9 tablas, la extensión btree_gist, los índices y el constraint `ex_turno_no_solape`

#### Scenario: Migración 001 downgrade revierte el esquema (borde)

- **GIVEN** el esquema creado por 001
- **WHEN** se ejecuta `alembic downgrade base`
- **THEN** las tablas core se eliminan en orden inverso (la extensión puede permanecer)

### Requirement: Fictitious seed data (RN-GL-02)

The system SHALL provide an idempotent seed script that inserts only fictitious data: 1 demo consultorio, 2 active sillones, 3 treatments (Limpieza 30 min, Control 15 min, Conducto 60 min), 3 users (secretaria, odontólogo, paciente de prueba) and 1 paciente linked to the patient user; no real patient data, emails `@example.com`, placeholder phone numbers.

#### Scenario: Seed idempotente inserta datos ficticios

- **GIVEN** una base con el esquema 001 aplicado y sin datos demo
- **WHEN** se ejecuta `seed_demo`
- **THEN** se crean el consultorio, 2 sillones, 3 tratamientos, 3 usuarios y 1 paciente, todos con datos ficticios

#### Scenario: Re-ejecutar seed no duplica (borde)

- **GIVEN** el seed ya fue ejecutado
- **WHEN** se ejecuta `seed_demo` nuevamente
- **THEN** no se insertan duplicados (idempotente por email/nombre)

### Requirement: BaseRepository and UnitOfWork for core persistence

The system SHALL provide a generic `BaseRepository[T]` (`get`, `add`, `soft_delete`) and a `UnitOfWork` (async context manager with `commit`/`rollback`) operating over `AsyncSession`, enabling transactional persistence of core entities.

#### Scenario: UoW commit persiste, rollback descarta

- **GIVEN** un UnitOfWork abierto
- **WHEN** se agrega una entidad y se hace commit (o se lanza excepción)
- **THEN** con commit la entidad queda persistida; con excepción se hace rollback y no queda persistida

### Requirement: Patient phone validated at application layer

The system SHALL validate patient phone numbers against the Argentine format regex at the application layer (Pydantic/service), not via SQL CHECK (D-08).

#### Scenario: Teléfono AR válido aceptado

- **GIVEN** un teléfono con formato AR válido
- **WHEN** se valida
- **THEN** es aceptado

#### Scenario: Teléfono inválido rechazado (borde)

- **GIVEN** un teléfono con formato no AR
- **WHEN** se valida
- **THEN** se rechaza con error de validación