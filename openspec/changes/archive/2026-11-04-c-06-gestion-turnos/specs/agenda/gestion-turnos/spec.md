# Spec Delta — agenda/gestion-turnos

## Purpose

Manage the lifecycle of a turno: confirm, cancel, reschedule and mark attendance, enforcing the 2-hour window and anti-overlap at the engine, supporting sobreturnos by secretaria and full audit trail.

## ADDED Requirements

### Requirement: Turno state transitions via dedicated endpoints

The system SHALL expose `PATCH /turnos/{id}/confirmar`, `/cancelar`, `/reprogramar` and `/marcar-asistencia` and apply the transitions `reservado → confirmado → asistido | cancelado | ausente`. Invalid transitions SHALL be rejected with 422.

#### Scenario: Confirmar turno reservado (feliz)

- **GIVEN** a turno in state `reservado`
- **WHEN** an authorized user calls `PATCH /turnos/{id}/confirmar`
- **THEN** the turno moves to `confirmado` and responds 200 with the updated turno

#### Scenario: Transición inválida es rechazada (borde)

- **GIVEN** a turno already `asistido`
- **WHEN** a user calls `PATCH /turnos/{id}/confirmar`
- **THEN** the system responds 422 and the state is unchanged

### Requirement: Cancellation respects the 2-hour window for all roles

The system SHALL reject cancellation when the turno starts in less than `APPOINTMENT_CANCEL_MINUTES` (default 120) minutes, for both paciente and secretaria, responding 422. Otherwise it SHALL set state to `cancelado` and soft-delete is not applied (turno remains for history).

#### Scenario: Cancelar con más de 2 h (feliz)

- **GIVEN** a turno starting in more than 2 hours
- **WHEN** an authorized user cancels it
- **THEN** the turno becomes `cancelado` and responds 200

#### Scenario: Cancelar con menos de 2 h es rechazado (error de negocio)

- **GIVEN** a turno starting in less than 2 hours
- **WHEN** a paciente or secretaria cancels it
- **THEN** the system responds 422 and the state remains unchanged

### Requirement: Rescheduling revalidates availability and anti-overlap

The system SHALL, on `/reprogramar`, validate the new slot against active sillones/turnos/bloqueos and the EXCLUDE constraint; an occupied or blocked slot SHALL respond 409 with alternatives. The 2-hour window applies to the original turno.

#### Scenario: Reprogramar a hueco libre (feliz)

- **GIVEN** a turno and a free new slot
- **WHEN** an authorized user reschedules it
- **THEN** inicio/fin are updated, state becomes `reservado` or `confirmado` accordingly and responds 200

#### Scenario: Reprogramar a hueco ocupado (error de negocio)

- **GIVEN** the new slot overlaps an active turno or bloqueo
- **WHEN** reschedule is requested
- **THEN** the system responds 409 with alternatives and the original turno is unchanged

### Requirement: Sobreturno only by secretaria with explicit flag and reason

The system SHALL allow creating/flagging a sobreturno only when the actor is secretaria, with `es_sobreturno=true` and a non-empty `motivo_sobreturno`. Non-secretaria actors SHALL receive 403.

#### Scenario: Secretaria crea sobreturno (feliz)

- **GIVEN** an authenticated secretaria
- **WHEN** she marks a turno as sobreturno with a reason
- **THEN** `es_sobreturno=true` and `motivo_sobreturno` is persisted

#### Scenario: Paciente no puede crear sobreturno (borde)

- **GIVEN** an authenticated paciente
- **WHEN** he attempts to mark a sobreturno
- **THEN** the system responds 403

### Requirement: Late tolerance is informative in responses

The system SHALL include a `tolerancia_min` (5 by default, from `LATE_TOLERANCE_MINUTES`) in agenda/turno responses. It SHALL NOT block attendance marking.

#### Scenario: Tolerancia visible (feliz)

- **GIVEN** a turno response
- **WHEN** it is returned by the API
- **THEN** it includes `tolerancia_min` equal to the configured value

### Requirement: Attendance marking

The system SHALL allow secretaria/odontólogo to mark a turno as `asistido` or `ausente` via `/marcar-asistencia` with a payload `{estado: asistido|ausente}`. Paciente SHALL receive 403.

#### Scenario: Marcar asistencia (feliz)

- **GIVEN** a turno `confirmado`
- **WHEN** secretaria calls `/marcar-asistencia` with `asistido`
- **THEN** the turno becomes `asistido` and responds 200

### Requirement: Audit trail for every state change

Every state change SHALL persist an audit record with actor, timestamp (TIMESTAMPTZ) and origin (`online|mostrador|whatsapp`). The client SHALL NOT set actor or timestamp.

#### Scenario: Cambio auditado (feliz)

- **GIVEN** a state change performed by an authenticated user
- **WHEN** it completes
- **THEN** an audit record exists with actor_id, created_at tz-aware and origen

### Requirement: Origin tracking

The system SHALL store `origen` on the turno (`online|mostrador|whatsapp`) and on audit records. For management actions the default origin SHALL be `mostrador` unless specified.

#### Scenario: Origen por defecto mostrador (borde)

- **GIVEN** a management action without explicit origin
- **WHEN** it is persisted
- **THEN** `origen` is `mostrador`