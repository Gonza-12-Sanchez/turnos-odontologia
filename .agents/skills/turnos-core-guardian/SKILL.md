---
name: turnos-core-guardian
description: Guardián de invariantes núcleo de turnos-odontologia para C-02/C-04/C-05/C-06. Usar siempre que se creen o revisen modelos SQLAlchemy, migraciones Alembic, constraints EXCLUDE anti-solapamiento, cálculos fin=inicio+duración, montos en centavos o seeds. Garantiza RN-TU-01/03/04/06 y RN-GL-01/02/03, TIMESTAMPTZ y btree_gist.
---

# Turnos Core Guardian

Guardián del corazón de agenda. Evita que la doble reserva, fechas naive o dinero en float lleguen a `main`.
Aplica a `backend/app/models/`, `backend/alembic/`, seeds y servicios de disponibilidad/reserva.

## Cuándo usar

Usa esta skill cuando:
- crees o modifiques `Turno`, `Sillon`, `Tratamiento`, `Bloqueo`, `Paciente`, `Cobro`;
- escribas una migración Alembic que toque agenda;
- revises un `/opsx:propose` o PR de C-02, C-04, C-05 o C-06;
- dudes si un `CHECK`, índice o `EXCLUDE` cumple RN-TU-01.

No la uses para WhatsApp (C-08), Mercado Pago (C-09) ni UI PWA (C-10/C-11).

## Workflow en 4 pasos

### 1. Localizar el cambio
Identifica archivos tocados: `backend/app/models/*.py`, `backend/alembic/versions/*.py`, `backend/app/services/disponibilidad*`, seeds.

### 2. Verificar EXCLUDE motor (RN-TU-01, RN-GL-01)
Lee `references/postgres-exclude.md` y exige:
1. `CREATE EXTENSION IF NOT EXISTS btree_gist;` antes del constraint.
2. Columna `inicio TIMESTAMPTZ NOT NULL`, `fin TIMESTAMPTZ NOT NULL`, `CHECK (fin > inicio)`.
3. Constraint parcial solo turnos activos:
   `EXCLUDE USING GIST (sillon_id WITH =, tstzrange(inicio, fin) WITH &&) WHERE (is_active AND estado NOT IN ('cancelado','ausente'))`.
   Sin `WHERE`, los turnos cancelados bloquearían huecos para siempre.
4. Índices GIST + B-tree `(sillon_id, inicio)`, `(paciente_id, inicio)`, `(estado, inicio)`.
5. Doble verificación en servicio Python antes del `commit` (mensaje 409 amable), pero el motor decide.

### 3. Verificar invariantes (RN-TU-03/04/06, RN-CO-03, RN-GL-02/03)
Lee `references/invariantes.md` y exige:
- `fin = inicio + duracion_min` del tratamiento, nunca input del cliente.
- `duracion_min > 0`, `monto` en centavos `INTEGER`, jamás `Float` ni `money`.
- `origen IN (online, mostrador, whatsapp)`, `AuditMixin` con `is_active/created_at/updated_at/deleted_at`.
- Teléfono AR validado en app, no con CHECK críptico.
- Seeds 100 % ficticios (Consultorio demo, 2 sillones, Limpieza 30 / Control 15 / Conducto 60).

Ejecuta el script determinista:
```bash
python .agents/skills/turnos-core-guardian/scripts/check_turnos_invariants.py backend/app/models backend/alembic/versions
```
Debe salir `OK` antes de proponer el change. Si falla, corrige y repite.

### 4. Reportar
Usa siempre este formato:
```markdown
## Veredicto Guardian: OK / BLOQUEADO
- EXCLUDE: [OK / falta btree_gist / falta WHERE / tipo naive]
- Invariantes: [OK / lista de violaciones con archivo:línea]
- Seeds: [ficticios OK / contiene dato real]
- Siguiente paso: [qué corregir o "listo para /opsx:propose C-02"]
```

## Ejemplos

**Ejemplo 1 — modelo correcto:**
Input: `Turno.inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True))` + `__table_args__` con `ExcludeConstraint`.
Output: Veredicto OK, cita archivo:línea del EXCLUDE.

**Ejemplo 2 — modelo con fecha naive:**
Input: `inicio = Column(DateTime)` sin timezone.
Output: BLOQUEADO — "NUNCA fechas naive → usa TIMESTAMPTZ (`DateTime(timezone=True)`)", referencia a regla dura AGENTS.md.

**Ejemplo 3 — migración sin btree_gist:**
Input: Alembic con `sa.ExcludeConstraint` pero sin `op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")`.
Output: BLOQUEADO — Postgres 16 exige la extensión para `(sillon_id WITH =)`, ver references/postgres-exclude.md.

## Límites
- No genera datos reales de pacientes; si un seed/test los contiene, bloquéalo (RN-GL-02).
- No aprueba sobreturnos implícitos: solo secretaria, flag explícito + motivo (RN-TU-06).
- Si el pedido contradice AGENTS.md (Reglas Duras), las reglas duras prevalecen.
