# Tasks — C-05 Disponibilidad y reserva

## 1. Schemas y validación

- [x] 1.1 Crear `backend/app/schemas/turnos.py` con `HorarioLibreOut` (sillon_id, inicio, fin AwareDatetime) y `TurnoCreate` (sillon_id UUID, tratamiento_id UUID, inicio AwareDatetime, campos opcionales `sena`/`requiere_sena`/`deposit` bool) y `TurnoOut` (id, paciente_id, sillon_id, tratamiento_id, inicio, fin, estado, origen) y `ConflictoOut` (detail, alternativas: list[HorarioLibreOut]); verificar import y validación con pytest.
- [x] 1.2 Agregar validación de `inicio` timezone-aware y rechazo de `fin` del cliente en `TurnoCreate` (extra forbid) y verificar con test unitario.

## 2. Servicio de disponibilidad

- [x] 2.1 Implementar `DisponibilidadService` en `backend/app/services/disponibilidad_service.py` con método `libres(fecha, tratamiento_id, sillon_id=None)` que consulta sillones/tratamientos/bloqueos/turnos activos y genera candidatos cada `duracion_min` entre 00:00 y 24:00 UTC, excluyendo solapes; verificar con test directo.
- [x] 2.2 Implementar cache Redis en `libres` (clave `avail:{fecha}:{tratamiento}:{sillon or all}`, TTL 60 s) y método `invalidar(fecha)`; verificar hit/miss en test con redis real.

## 3. Servicio de reserva

- [x] 3.1 Implementar `ReservaService.reservar(payload, paciente, uow)` que valida entidades activas, calcula `fin`, verifica disponibilidad, maneja seña (402), crea Turno, captura IntegrityError → 409 con alternativas, invalida cache y encola job `wa:reminders`; verificar con tests de éxito y conflicto.
- [x] 3.2 Implementar `alternativas(fecha, tratamiento_id)` reutilizando `libres` y devolviendo hasta 3 franjas; verificar en test de conflicto.

## 4. API y registro

- [x] 4.1 Crear `backend/app/api/turnos.py` con `GET /horarios-libres` público y `POST /turnos` con `require_role("paciente")`, mapeando servicios y UoW; verificar OpenAPI y códigos de respuesta.
- [x] 4.2 Registrar el router en `backend/app/main.py` sin prefijo y verificar que `/horarios-libres` y `/turnos` aparecen en `app.openapi()`.

## 5. Tests de integración

- [x] 5.1 Agregar `backend/tests/test_disponibilidad.py` cubriendo: libres excluyen ocupados/bloqueados, filtro por sillón, reserva feliz calcula fin, reserva sin login 401, rol no paciente 403, slot ocupado 409 con alternativas, naive 422, concurrencia (una 201 + otra 409); verificar con `pytest`.
- [x] 5.2 Agregar tests de cache (hit/invalidación) y enqueue de recordatorio (`wa:reminders` contiene el turno) usando redis real; verificar con `pytest`.

## Workflow follow-up

- Sincronizar spec `agenda/disponibilidad-reserva`, archivar C-05 y marcar completo en CHANGES.md tras revisión y verificación.
- Ejecutar suite completa backend y ruff.