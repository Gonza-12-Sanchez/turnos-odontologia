# Tasks — C-02 core-models

## 1. Fundamentos compartidos

- [ ] 1.1 Crear `backend/app/models/audit.py` con `AuditMixin` (is_active default true, created_at, updated_at con onupdate, deleted_at nullable) y verificar import sin errores (`python -c "from app.models.audit import AuditMixin"`).
- [ ] 1.2 Crear `backend/app/repositories/base_repository.py` con `BaseRepository[T]` genérico (`get`, `add`, `soft_delete`) operando sobre `AsyncSession` y verificar import + instanciación genérica.
- [ ] 1.3 Crear `backend/app/repositories/unit_of_work.py` con `UnitOfWork` (async context manager, `commit`/`rollback`, propiedad `session`) y verificar import.
- [ ] 1.4 Crear validador de teléfono AR en capa app (Pydantic) con regex `^\+54\s?9?\s?\d{2,4}[\s-]?\d{6,8}$` y verificar tests de aceptación/rechazo (5.9).
- [ ] 1.5 Verificar que importar `app.models` popula `Base.metadata` con las 9 tablas core (verificación final tras 2.x).

## 2. Modelos SQLAlchemy 2.x async (9 entidades)

- [ ] 2.1 Crear `backend/app/models/consultorio.py` (`Consultorio`) y `backend/app/models/sillon.py` (`Sillon`, FK consultorio, índice `ix_sillon_consultorio`) heredando `Base, AuditMixin`; verificar metadata.
- [ ] 2.2 Crear `backend/app/models/tratamiento.py` (`Tratamiento`, `duracion_min` CHECK > 0, `precio_referencia_centavos` INTEGER nullable CHECK >= 0) y verificar tipos.
- [ ] 2.3 Crear `backend/app/models/usuario.py` (`Usuario`: email/telefono unique nullable, password_hash not null, rol CHECK in (paciente,odontologo,secretaria), CHECK email IS NOT NULL OR telefono IS NOT NULL) + índices `uq_usuario_email`, `ix_usuario_rol_activo`; verificar.
- [ ] 2.4 Crear `backend/app/models/paciente.py` (`Paciente`: usuario_id unique FK not null, nombre, telefono not null, obra_social, notas) y verificar.
- [ ] 2.5 Crear `backend/app/models/turno.py` (`Turno`: FKs paciente/sillon/tratamiento/odontologo, inicio/fin TIMESTAMPTZ, estado/origen CHECK, es_sobreturno, motivo_sobreturno, `CHECK(fin > inicio)`, `ExcludeConstraint` parcial `ex_turno_no_solape`, índices `ix_turno_sillon_inicio`, `ix_turno_paciente_inicio`, `ix_turno_estado_inicio`) y verificar import.
- [ ] 2.6 Crear `backend/app/models/bloqueo.py` (`Bloqueo`: sillon_id nullable FK, desde/hasta TIMESTAMPTZ, motivo, CHECK hasta > desde, índice `ix_bloqueo_sillon_desde`) y verificar.
- [ ] 2.7 Crear `backend/app/models/recordatorio_wa.py` (`RecordatorioWA`: turno_id FK, tipo CHECK, plantilla, message_id, estado CHECK, respuesta CHECK nullable) + índice `ix_recordatorio_turno`; verificar.
- [ ] 2.8 Crear `backend/app/models/cobro.py` (`Cobro`: turno_id FK, monto_centavos INTEGER CHECK >= 0, medio CHECK, tipo CHECK, estado_mp CHECK nullable, referencia_mp) + índice `ix_cobro_turno`; verificar.
- [ ] 2.9 Actualizar `backend/app/models/__init__.py` exportando las 9 entidades + `AuditMixin` y verificar `len(Base.metadata.tables) == 9`.

## 3. Migración Alembic 001

- [ ] 3.1 Crear `backend/alembic/versions/001_core_models.py` (revision `001`, down_revision `None`) con `op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")` y esqueleto; verificar `alembic heads`.
- [ ] 3.2 Implementar `upgrade()`: tablas en orden de dependencias (consultorio → sillon, tratamiento, usuario → paciente → turno → bloqueo, recordatorio_wa, cobro), FKs, CHECKs, EXCLUDE parcial, índices listados; verificar sintaxis (`python -m py_compile`).
- [ ] 3.3 Implementar `downgrade()`: drop tablas en orden inverso, sin eliminar extensión; verificar sintaxis.
- [ ] 3.4 Ejecutar `alembic upgrade head` contra DB de test y verificar existencia de 9 tablas, extensión `btree_gist`, constraint `ex_turno_no_solape` y los índices requeridos (consulta catálogo / `\d`).
- [ ] 3.5 Ejecutar `alembic downgrade base` y verificar que las tablas core se eliminan (extensión puede permanecer).

## 4. Seed ficticio (RN-GL-02)

- [ ] 4.1 Crear `backend/app/db/seed.py` con `async def seed_demo(session)` idempotente (por email/nombre) y verificar import.
- [ ] 4.2 Insertar datos ficticios: 1 consultorio "Consultorio demo", 2 sillones activos, 3 tratamientos (Limpieza 30 min, Control 15 min, Conducto 60 min) con precios ficticios en centavos, 3 usuarios (secretaria/odontologo/paciente) con emails `@example.com`, 1 paciente vinculado al usuario paciente con teléfono "+54 9 11 0000-0000"; verificar ejecución sin error.
- [ ] 4.3 Re-ejecutar `seed_demo` y verificar que no se duplican registros (conteos idénticos).
- [ ] 4.4 Verificar que el seed no contiene emails `@gmail.com`/`@hotmail.com` ni DNI real (guardian heurística) — cubierto en 6.1.

## 5. Tests de invariantes y escenarios (spec core/models)

- [ ] 5.1 Configurar fixtures de test en `backend/tests/conftest.py` (engine async + session sobre DB de test `turnos_test`, rollback por test) y verificar conexión.
- [ ] 5.2 **Escenario feliz**: test inserta Turno válido en sillón libre con fin = inicio + duración del tratamiento y verifica persistencia y `fin == inicio + duración` (minutos).
- [ ] 5.3 **Escenario error de negocio**: test inserta Turno solapado en mismo sillón y espera `IntegrityError` / `exclusion_violation` del motor.
- [ ] 5.4 **Escenario borde**: tests verifican que Turno con estado='cancelado' o is_active=false no bloquea, sillones distintos no se bloquean, y turnos adyacentes (fin == inicio nuevo) no solapan.
- [ ] 5.5 Test TIMESTAMPTZ: columnas temporales persisten datetime timezone-aware; datetime naive es rechazado.
- [ ] 5.6 Test centavos: `Cobro.monto_centavos` y `Tratamiento.precio_referencia_centavos` persisten como INTEGER y se leen iguales.
- [ ] 5.7 Test AuditMixin: `soft_delete` marca `is_active=false`, setea `deleted_at` y el registro permanece en tabla.
- [ ] 5.8 Test UoW: commit persiste la entidad; excepción hace rollback y no persiste.
- [ ] 5.9 Test teléfono AR: válido aceptado, inválido rechazado con error de validación.

## 6. Verificación final

- [ ] 6.1 Ejecutar `python .agents/skills/turnos-core-guardian/scripts/check_turnos_invariants.py backend/app/models backend/alembic/versions` y verificar salida `OK` (exit 0).
- [ ] 6.2 Ejecutar `pytest` y verificar que todos los tests pasan.
- [ ] 6.3 Revisar `git status`/`git diff` asegurando solo archivos intencionales y sin secretos.

## Workflow follow-up

- Archivar el change tras satisfacer GATE 2 (revisión): `/opsx:archive 2026-10-27-c-02-core-models`.
- Marcar `[x]` C-02 en `CHANGES.md` al archivar.
- Verificar resultado archivado (spec en `openspec/specs/core/models/spec.md`).
path: C:\Users\GonziChan\Desktop\FACULTAD\Metodologia I\SDD + ACTIVE STACK\Trabajo Integrador\turnos-odontologia\openspec\changes\2026-10-27-c-02-core-models\tasks.md