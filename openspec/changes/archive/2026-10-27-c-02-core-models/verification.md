# Verificación — C-02 core-models (evidencia retroactiva)

> **Aviso de reconstrucción.** Este documento se escribió el **2026-11-04** para dejar en el archivo la evidencia de verificación que faltaba; el cierre original del change fue el **2026-10-27**. Se distingue lo **re-verificado en esta sesión** de lo que consta en el **registro original** y no se repitió.

## 1. Registro original del cierre (2026-10-27)

Según `CHANGES.md` §C-02:

- 35/35 tareas, veredicto Guardian **OK**, 17/17 tests.
- Spec sincronizada en `openspec/specs/core/models/spec.md`.
- Migración `001` con upgrade/downgrade verificados contra base de test; seed ficticio idempotente.

Los 17 tests del cierre son consistentes con la suite vigente en ese momento: 13 de `core/models` (que siguen siendo 13) + 4 de `platform/health` (C-01).

## 2. Re-verificado en esta sesión (2026-11-04)

### 2.1 Suite de invariantes

`pytest tests/test_core_models.py` → **13/13**. Suite backend completa → **213 passed** (`turnos_test` en PostgreSQL + Redis).

| Escenario del spec | Test |
|---|---|
| Turno válido, `fin = inicio + duración` | `test_turno_valido_persiste` |
| Solapamiento mismo sillón → rechazo del motor | `test_turno_solapado_rechazado` |
| Turno cancelado no bloquea | `test_cancelado_no_bloquea` |
| Turno con soft delete no bloquea | `test_softdeleted_no_bloquea` |
| Sillones distintos no se bloquean | `test_sillones_distintos_no_bloquean` |
| Turnos adyacentes (`fin == inicio`) no solapan | `test_turnos_adyacentes_no_solapan` |
| Columnas temporales persisten con zona | `test_timestamps_tz` |
| Datetime naive rechazado | `test_naive_rechazado` |
| Montos y precios en centavos (INTEGER) | `test_centavos` |
| `soft_delete` conserva la fila y marca `deleted_at` | `test_soft_delete` |
| `UnitOfWork`: commit persiste, excepción rollback | `test_uow_commit_rollback` |
| Teléfono AR válido/inválido | `test_phone_ar` |
| Seed ficticio idempotente | `test_seed_idempotente` |

### 2.2 Catálogo real de PostgreSQL (`turnos_test`, PostgreSQL 17)

Consultado en vivo, no solo en el código:

| Invariante | Comprobación |
|---|---|
| 9 tablas core | `consultorio`, `sillon`, `tratamiento`, `usuario`, `paciente`, `turno`, `bloqueo`, `recordatorio_wa`, `cobro` (+ `config_audit` de C-04 y `alembic_version`) = 11 tablas en `public` |
| Extensión `btree_gist` | presente (`pg_extension`) |
| Anti-solapamiento RN-TU-01 | `ex_turno_no_solape`: `EXCLUDE USING gist (sillon_id WITH =, tstzrange(inicio, fin) WITH &&) WHERE (is_active AND estado NOT IN ('cancelado','ausente'))` |
| Duración positiva | `ck_turno_fin_gt_inicio`: `CHECK (fin > inicio)` |
| Estados y origen | `ck_turno_estado` (reservado, confirmado, asistido, cancelado, ausente) y `ck_turno_origen` (online, mostrador, whatsapp) |
| Fechas con zona (RN-GL) | `turno.inicio/fin`, `bloqueo.desde/hasta` = `timestamp with time zone` |
| Dinero exacto (RN-CO-03) | `cobro.monto_centavos` y `tratamiento.precio_referencia_centavos` = `integer`; sin `float` ni `money` |
| Migración aplicada | `alembic current` → `002 (head)` (implica `001` aplicada) |

### 2.3 Guardian determinista

`python .agents/skills/turnos-core-guardian/scripts/check_turnos_invariants.py backend/app/models backend/alembic/versions` → `OK ... sin fechas naive, sin float/money, EXCLUDE con btree_gist, seeds OK` (exit 0).

### 2.4 Seeds ficticios (RN-GL-02)

`app/db/seed.py` crea: 1 consultorio demo, 2 sillones activos, 3 tratamientos (Limpieza 30 min, Control 15 min, Conducto 60 min) con precios ficticios en centavos, 3 usuarios con emails `@example.com` y 1 paciente vinculado. Sin datos reales; `test_seed_idempotente` confirma que re-ejecutar no duplica.

## 3. No re-ejecutado en esta sesión

- `alembic downgrade base` / `upgrade head` completos (tareas 3.4 y 3.5): se evitó alterar la base de trabajo; consta como verificado en el cierre original.
- El número exacto 17/17 del cierre no se reprodujo como corte aislado, porque la suite creció a 213 tests con C-03 y C-04.

## 4. Estado de tareas

`tasks.md`: **35/35** tareas marcadas, sin pendientes.

## 5. Veredicto

**C-02 verificado.** Los modelos, la migración `001` y el seed siguen cumpliendo los invariantes duros del proyecto (EXCLUDE parcial por `is_active` y estado, `fin > inicio`, `TIMESTAMPTZ`, centavos en `INTEGER`, `btree_gist`), confirmados en el catálogo real de PostgreSQL además de en los tests. La spec `core/models` (9 requerimientos, 15 escenarios) valida en estricto y está sincronizada con lo archivado.

**Nota de consistencia:** al archivo de C-02 le faltaba también `.openspec.yaml`; se agregó el 2026-11-04 con `created: 2026-10-27` para igualar el formato de C-01, C-03 y C-04.
