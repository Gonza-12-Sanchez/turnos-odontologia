# C-07 — Verificación de agenda y mis reservas

## Estado
Archivado 2026-11-05 (17/17 tests C-07, suite backend 249 passed).

## Evidencia
- `GET /agenda?fecha=&sillon=` (odontólogo/secretaria): turnos del día agrupados por sillón con paciente, tratamiento, estado, tolerancia visible, aviso de sobreturnos.
- `GET /mis-reservas` (paciente): solo turnos propios ordenados por fecha con estado + acciones permitidas según RN-TU-02.
- Paginación por fecha, filtros por estado/sillón, sin N+1 (eager load paciente+tratamiento+sillón).
- Respuestas mobile-friendly (payload chico para PWA).

## Tests
- Paciente solo ve lo propio (aislamiento).
- Odontólogo ve agenda del día.
- Turno cancelado < 2 h no ofrece acción cancelar.
- Performance smoke con día completo multi-sillón.

## Guardian
N/A (change de lectura, sin modelos críticos de motor).
