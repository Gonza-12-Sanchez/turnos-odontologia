# C-05 — Verificación de disponibilidad y reserva

## Estado
Archivado 2026-11-04 (10/10 tasks, suite backend 223 tests, Guardian OK).

## Evidencia
- `GET /horarios-libres` público: calcula franjas reales excluyendo turnos activos y bloqueos, expande por `duracion_min` del tratamiento, no expone datos de pacientes, cache Redis con TTL corto e invalidación al crear turno.
- `POST /turnos`: requiere login paciente, valida hueco, calcula `fin = inicio + duracion`, verificación anti-solapamiento a nivel motor (EXCLUDE en Postgres), carrera por mismo hueco → `409 + alternativas`.
- Tratamiento con seña: responde `402 + checkout MP` sin crear turno hasta webhook aprobado (contrato C-09).
- Enqueue de recordatorio WhatsApp al reservar (cola Redis, worker en C-08).

## Tests
- Libres excluyen ocupados y bloqueados.
- Reserva sin login → 401.
- Doble reserva concurrente → una 201 + otra 409.
- Duración variable (15 vs 60 min) genera `fin` correcto.
- Tratamiento con seña sin pago → turno no creado.

## Guardian
turnos-core-guardian: OK (EXCLUDE, invariantes, TIMESTAMPTZ, centavos).
