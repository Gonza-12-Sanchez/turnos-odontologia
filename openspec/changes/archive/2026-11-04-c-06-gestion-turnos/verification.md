# C-06 — Verificación de gestión de turnos

## Estado
Archivado 2026-11-04 (10/10 tasks, suite backend 233 tests, Guardian OK).

## Evidencia
- `PATCH /turnos/{id}/confirmar`, `/cancelar`, `/reprogramar`, `/marcar-asistencia`: transiciones `reservado → confirmado → asistido | cancelado | ausente`.
- Ventana RN-TU-02 a nivel motor: cancelar/reprogramar con `< 2 h` → `422` para paciente y secretaria.
- Reprogramar revalida disponibilidad + anti-solapamiento (reutiliza servicio C-05).
- Sobreturno: solo secretaria, flag explícito + motivo, marcado visual en respuestas.
- Tolerancia 5 min informativa en payload (`LATE_TOLERANCE_MINUTES`).
- Auditoría RN-GL-03: cada cambio guarda quién/cuándo/origen (online|mostrador|whatsapp).

## Tests
- Cancelar a 1h → 422.
- Secretaria tampoco puede < 2 h.
- Reprogramar a hueco ocupado → 409.
- Sobreturno sin rol secretaria → 403.
- Auditoría registra origen.

## Guardian
turnos-core-guardian: OK (EXCLUDE, invariantes, seeds).
