# Tasks — C-07 Agenda y Mis reservas (lectura)

## 1. Schemas de lectura

- [x] 1.1 Agregar `AccionesOut`, `AgendaTurnoOut`, `AgendaSillonOut`, `MisReservaOut` a `backend/app/schemas/turnos.py` con campos compactos y `ConfigDict(from_attributes=True)`; verificar import con `python -c "import app.schemas.turnos"`.
- [x] 1.2 Validar serialización de un turno fixture a `AgendaTurnoOut`/`MisReservaOut` en test unitario; verificar con pytest.

## 2. Repositorio de lectura

- [x] 2.1 Crear `backend/app/repositories/agenda_lectura_repository.py` con `list_for_agenda(fecha, sillon_id=None, estado=None)` y `list_for_paciente(paciente_id, desde=None, hasta=None, estado=None)` usando `selectinload` de paciente/tratamiento/sillón; verificar import.
- [x] 2.2 Agregar test de repositorio que confirme eager load sin N+1 y filtros aplicados; verificar con pytest.

## 3. Servicio de lectura

- [x] 3.1 Implementar `AgendaLecturaService` en `backend/app/services/agenda_lectura_service.py` con `agenda(...)` (agrupación por sillón) y `mis_reservas(...)` (orden por inicio, acciones según RN-TU-02); verificar con tests directos.
- [x] 3.2 Agregar test unitario de acciones: turno >2h ofrece cancelar; turno <2h no; verificar con pytest.

## 4. Endpoints GET

- [x] 4.1 Agregar `GET /agenda` y `GET /mis-reservas` en `backend/app/api/turnos.py` con RBAC y query params; verificar OpenAPI (`/docs`) y ruff.
- [x] 4.2 Agregar tests de integración: paciente solo ve lo propio (aislamiento), odontólogo ve agenda del día, fecha obligatoria → 422; verificar con pytest.

## 5. Performance smoke

- [x] 5.1 Agregar test smoke con día completo multi-sillón (2 sillones × 16 turnos) midiendo tiempo < 1s; verificar con pytest.

## Workflow follow-up

- Archivar el change tras revisión y marcar completo en CHANGES.md.
- Verificar el resultado archivado.