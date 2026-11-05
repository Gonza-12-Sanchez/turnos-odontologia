# Design — C-06 Gestión de turnos

## Context

Ver `proposal.md`. Los turnos se crean en C-05 con estado `reservado`. Falta ciclo de vida y gestión. Se reutiliza `DisponibilidadService` para reprogramación y `settings.appointment_cancel_minutes`/`late_tolerance_minutes`.

## Goals / Non-Goals

**Goals:** endpoints de confirmar/cancelar/reprogramar/marcar-asistencia/sobreturno/patch, ventana de 2 h, revalidación de disponibilidad, tolerancia informativa, permisos por rol y ownership.

**Non-Goals:** lectura de agenda (C-07), notificaciones (C-08), cobros (C-09), UI (C-10/C-11), tabla de auditoría dedicada (se usa AuditMixin + origen en Turno).

## Decisions

### D-01 — Rutas y permisos
Endpoints `PATCH /turnos/{id}/...` sin prefijo adicional. Permisos: confirmar/cancelar/reprogramar para secretaria y paciente (dueño); marcar-asistencia para secretaria/odontólogo; sobreturno y patch para secretaria.

### D-02 — Ventana de 2 h
Comparar `turno.inicio - now(UTC)` contra `APPOINTMENT_CANCEL_MINUTES`. Si es menor, 422. Aplica a cancelar y reprogramar.

### D-03 — Reprogramación
Validar sillon activo, calcular `fin = inicio + duración`, verificar solapes excluyendo el turno actual y bloqueos. Si hay conflicto, 409 con alternativas (reutiliza `DisponibilidadService`).

### D-04 — Sobreturno
Endpoint dedicado y patch genérico para `es_sobreturno` + `motivo_sobreturno`, solo secretaria, motivo no vacío.

### D-05 — Tolerancia
`tolerancia_min` en `TurnoOut` con default `LATE_TOLERANCE_MINUTES` (5). Informativa, no bloquea.

### D-06 — Auditoría
Se actualiza `origen` y `updated_at` (AuditMixin) en cada cambio. No se crea tabla nueva (fuera de alcance MVP).

## Risks / Trade-offs

- [Ownership por paciente] → se resuelve `Paciente` desde el token; si no existe, 403.
- [Reprogramar al mismo hueco] → se permite si no hay otros conflictos; el turno actual se excluye del chequeo.
- [Zona horaria] → `inicio` debe ser AwareDatetime; naive → 422.

## Migration Plan

1. No requiere migración nueva.
2. Registrar endpoints (ya en `api/turnos.py`).
3. Ejecutar suite y ruff.