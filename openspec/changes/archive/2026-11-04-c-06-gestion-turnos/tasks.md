# Tasks — C-06 Gestión de turnos

## 1. Schemas

- [x] 1.1 Agregar a `backend/app/schemas/turnos.py` los schemas `ReprogramarIn`, `MarcarAsistenciaIn`, `SobreturnoIn`, `GestionTurnoPatch` y ampliar `TurnoOut` con `es_sobreturno`, `motivo_sobreturno`, `tolerancia_min`; verificar import.

## 2. Servicio de gestión

- [x] 2.1 Implementar `GestionTurnosService` en `backend/app/services/gestion_turnos_service.py` con `confirmar`, `cancelar`, `reprogramar`, `marcar_asistencia`, `sobreturno`, `patch`; verificar con tests directos.

## 3. API

- [x] 3.1 Agregar endpoints `PATCH /turnos/{id}/confirmar`, `/cancelar`, `/reprogramar`, `/marcar-asistencia`, `/sobreturno`, `/` en `backend/app/api/turnos.py`; verificar OpenAPI.

## 4. Tests

- [x] 4.1 Agregar tests en `backend/tests/test_gestion_turnos.py` cubriendo: confirmar, cancelar ventana, reprogramar feliz/conflicto, sobreturno por rol, marcar asistencia, patch, tolerancia; verificar con pytest.

## Workflow follow-up

- Sincronizar spec, archivar C-06 y marcar completo en CHANGES.md tras revisión.