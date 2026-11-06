# Proposal — C-07 Agenda y Mis reservas (lectura)

## Why

C-05 y C-06 permiten reservar y gestionar turnos, pero no existe ningún endpoint de lectura para la agenda del día del odontólogo/secretaria ni para que el paciente consulte sus propias reservas. La PWA mobile-first necesita payloads compactos y aislamiento por actor (RN-AU-01, RBAC).

## What Changes

- Agregar `GET /agenda?fecha=&sillon=&estado=` (odontólogo/secretaria): turnos del día agrupados por sillón con paciente, tratamiento, estado, tolerancia visible y aviso de sobreturnos.
- Agregar `GET /mis-reservas` (paciente): solo turnos propios ordenados por fecha con estado + acciones permitidas según RN-TU-02 (cancelar solo si faltan ≥ 2 h).
- Paginación por fecha, filtros por estado/sillón; eager load de paciente+tratamiento+sillón (sin N+1); respuestas mobile-friendly.
- Tests: aislamiento de paciente, agenda del día para odontólogo, acción cancelar oculta si < 2 h, performance smoke multi-sillón.

## Capabilities

### New Capabilities

- `agenda/agenda-mis-reservas`: endpoints de lectura de agenda del día (por sillón) y de reservas propias del paciente, con filtros, paginación y RBAC.

### Modified Capabilities

Ninguna: reutiliza invariantes vigentes de `core/models`, `identity/auth`, `agenda/disponibilidad-reserva` y `agenda/gestion-turnos`.

## Impact

Nuevos schemas de lectura, servicio de consulta y endpoints `GET` en `backend/app/`; reutiliza `Turno`, `Paciente`, `Sillon`, `Tratamiento` y `UnitOfWork`; pruebas de API y performance smoke. Sin cambios de UI (C-10/C-11) ni migraciones.