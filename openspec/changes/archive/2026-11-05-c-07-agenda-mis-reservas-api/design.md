# Design — C-07 Agenda y Mis reservas (lectura)

## Context

Ver `proposal.md`. Los turnos se crean y gestionan en C-05/C-06. Falta lectura para la PWA: agenda del día por sillón y reservas propias del paciente. Se reutiliza el modelo `Turno` con sus índices `(sillon_id, inicio)`, `(paciente_id, inicio)`, `(estado, inicio)` y la infraestructura async (UnitOfWork, repositorios, deps RBAC).

## Goals / Non-Goals

**Goals:** endpoints `GET /agenda` y `GET /mis-reservas`, filtros por fecha/sillón/estado, eager load sin N+1, payloads compactos, RBAC por rol, acciones permitidas según RN-TU-02, tolerancia visible, aviso de sobreturnos.

**Non-Goals:** UI (C-10/C-11), notificaciones (C-08), cobros (C-09), cambios de estado (C-06), migraciones nuevas, tabla de auditoría dedicada.

## Decisions

### D-01 — Rutas y permisos
`GET /agenda` en `api/turnos.py` con `require_role("odontologo", "secretaria")`; `GET /mis-reservas` con `require_role("paciente")`. `fecha` obligatoria en agenda (422 si falta).

### D-02 — Servicio y repositorio de lectura
Nuevo `AgendaLecturaService` en `backend/app/services/agenda_lectura_service.py` que recibe `AsyncSession` y concentra las consultas. Un método `agenda(fecha, sillon_id=None, estado=None)` y `mis_reservas(paciente, desde=None, hasta=None, estado=None)`. La agrupación por sillón se hace en el servicio (dict por sillón) para mantener la consulta única.

### D-03 — Sin N+1
Usar `selectinload`/`joinedload` de SQLAlchemy para `paciente`, `tratamiento` y `sillon` en una sola consulta por request. El repositorio expone `list_for_agenda(...)` y `list_for_paciente(...)`.

### D-04 — Schemas compactos
Nuevos schemas en `schemas/turnos.py`: `AgendaTurnoOut` (id, sillon_id, sillon_nombre, paciente_id, paciente_nombre, tratamiento_id, tratamiento_nombre, duracion_min, inicio, fin, estado, origen, es_sobreturno, motivo_sobreturno, tolerancia_min) y `MisReservaOut` (id, sillon_id, sillon_nombre, tratamiento_id, tratamiento_nombre, inicio, fin, estado, origen, es_sobreturno, tolerancia_min, acciones). `AgendaOut` agrupa por sillón: `{sillon, turnos}`. `acciones` incluye `cancelar`, `confirmar`, `reprogramar` booleans calculados en el servicio con `settings.appointment_cancel_minutes`.

### D-05 — Acciones permitidas (RN-TU-02)
Calcular en el servicio: `cancelar = estado in {reservado, confirmado} and (inicio - now(UTC)) >= appointment_cancel_minutes`. `confirmar = estado == reservado`. `reprogramar = cancelar` (misma ventana). Se expone solo lo permitido; el cliente no decide.

### D-06 — Filtros y paginación por fecha
Agenda: `fecha` obligatoria (date), `sillon` y `estado` opcionales. Mis reservas: `desde`/`hasta` opcionales (date), `estado` opcional; por defecto todos los turnos del paciente. Orden por `inicio ASC`.

### D-07 — Mobile-friendly
Payloads con nombres cortos ya existentes; sin relaciones anidadas completas (solo id+nombre). `tolerancia_min` informativo.

### D-08 — UI Mockups
No aplica UI. `Decision: no (no UI)`.

## Risks / Trade-offs

- [Performance con día completo multi-sillón] → un solo query con selectinload + índices existentes; smoke test mide tiempo.
- [Zona horaria] → `fecha` se interpreta en UTC para el rango del día; documentado.
- [Acciones calculadas en backend] → evita reglas en cliente; consistente con RN-GL-01.

## Migration Plan

1. No requiere migración nueva (índices ya existen).
2. Agregar schemas, servicio, repositorio y endpoints.
3. Ejecutar suite y ruff.

## UI Mockups

- Design system revision: n/a (backend only)
- Decision: no (no UI)
- Mockups: n/a
- Approval: n/a
- Preview: n/a
- Visual verify: n/a