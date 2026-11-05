# Proposal — C-06 Gestión de turnos

## Why

C-05 permite reservar turnos, pero no existe máquina de estados ni gestión posterior: confirmar, cancelar, reprogramar, marcar asistencia o registrar sobreturnos. C-06 completa el ciclo de vida del turno y aplica la ventana de 2 h y la auditoría a nivel motor.

## What Changes

- Agregar `PATCH /turnos/{id}/confirmar`, `/cancelar`, `/reprogramar` y `/marcar-asistencia` con transiciones `reservado → confirmado → asistido | cancelado | ausente`.
- Aplicar la ventana RN-TU-02 a nivel motor: cancelar/reprogramar con menos de 2 h → `422` para paciente y secretaria.
- Reprogramar revalida disponibilidad y anti-solapamiento reutilizando el servicio C-05.
- Sobreturno solo para secretaria, con flag explícito y motivo; tolerancia de 5 min informativa en el payload (RN-TU-05).
- Auditoría RN-GL-03: cada cambio guarda quién/cuándo/origen (`online|mostrador|whatsapp`).
- Tests de transiciones, ventana, reprogramación, sobreturno y auditoría.

## Capabilities

### New Capabilities

- `agenda/gestion-turnos`: máquina de estados del turno, gestión por secretaria/paciente, ventana de 2 h, sobreturnos y auditoría de cambios.

### Modified Capabilities

Ninguna: reutiliza los invariantes vigentes de `core/models` y las capacidades de `identity/auth` y `agenda/disponibilidad-reserva`.

## Impact

Nuevos schemas, servicio de gestión y endpoints `PATCH` en `backend/app/`; reutiliza `DisponibilidadService` y `ReservaService`; pruebas de API y concurrencia. No implementa lectura de agenda (C-07), notificaciones (C-08), cobros (C-09) ni UI (C-10/C-11).