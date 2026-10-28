# Proposal — C-02 core-models

## Why

C-01 dejó el scaffolding ejecutable pero cero entidades de dominio: sin modelos ni migraciones, ningún change posterior (C-03 auth, C-04 config, C-05 disponibilidad) puede persistir datos ni verificar la invariante central del producto — la prohibición de doble reserva (RN-TU-01). C-02 crea el modelo de datos núcleo, el constraint de exclusión a nivel de motor y el seed ficticio que desbloquean el resto del camino crítico.

## What Changes

- Modelos SQLAlchemy 2.x async: `Consultorio`, `Sillon`, `Tratamiento`, `Usuario` (rol paciente|odontologo|secretaria), `Paciente` (1↔1 con Usuario rol paciente), `Turno` (inicio/fin TIMESTAMPTZ, fin calculado), `Bloqueo`, `RecordatorioWA`, `Cobro` (monto en centavos INTEGER).
- `AuditMixin`: `is_active`, `created_at`, `updated_at`, `deleted_at`; campo `origen` en `Turno` (online|mostrador|whatsapp) para RN-GL-03.
- Constraint de exclusión Postgres por rango en `Turno`: `EXCLUDE USING GIST (sillon_id WITH =, tstzrange(inicio, fin) WITH &&) WHERE (is_active AND estado NOT IN ('cancelado','ausente'))`, con `CHECK (fin > inicio)`, extensión `btree_gist` e índices GIST/B-tree (RN-TU-01, RN-GL-01).
- `BaseRepository[T]` genérico + `UnitOfWork`; teléfono AR validado a nivel app.
- Migración Alembic 001: tablas core + índices `(sillon_id, inicio)`, `(paciente_id, inicio)`, `(estado, inicio)`, `(email)`, `(rol, activo)`.
- Seed ficticio (RN-GL-02): 1 consultorio demo, 2 sillones activos, 3 tratamientos (Limpieza 30 min, Control 15 min, Conducto 60 min), 3 usuarios (secretaria, odontólogo, paciente de prueba). Nunca datos reales.
- Tests: turno solapado falla a nivel motor; `fin = inicio + duración` del tratamiento.
- El spec `core/models` definirá ≥3 escenarios verificables (feliz, error de negocio, borde) siguiendo el estándar del proyecto.

## Capabilities

### New Capabilities

- `core/models`: persistencia e invariantes del modelo de datos núcleo (entidades, AuditMixin, anti-solapamiento a nivel motor, migración 001, seeds ficticios, BaseRepository/UnitOfWork).

### Modified Capabilities

Ninguna (inventario `openspec list --specs` solo contiene `platform/health`; no cambia su contrato).

## Impact

- Código nuevo: `backend/app/models/*.py`, repositorio genérico + `UnitOfWork`, `backend/alembic/versions/001_*.py`, seed ficticio.
- Nueva spec: `openspec/specs/core/models/spec.md` (al archivar).
- Dependencias: requiere C-01 (archivado). Desbloquea C-03 (`auth-jwt-rbac`) y en cadena C-04…C-12.
- Sin breaking changes (no hay código de negocio previo; C-01 solo dejó scaffolding).
- Riesgo principal: constraint mal definido (sin `WHERE` o extensión faltante) invalidaría RN-TU-01; se revisa con la skill `turnos-core-guardian` y el script de invariantes.

## Governance Level

CRITICO (GATE 2 — revisión solo). Cambio fundacional del modelo de datos y de la invariante anti-solapamiento; cualquier error se propaga a todos los changes posteriores.

## Open Questions

Ninguna que bloquee C-02. Los puntos abiertos IN-10-03 (password vs OTP paciente) e IN-10-04 (proveedor WhatsApp / quién paga) pertenecen a C-03 y C-08 respectivamente y solo dejan placeholders de env en este change.