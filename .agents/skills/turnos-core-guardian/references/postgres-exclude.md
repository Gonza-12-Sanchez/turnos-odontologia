# EXCLUDE anti-solapamiento (RN-TU-01) — Postgres 16

Patrón canónico para C-02. Fuente: https://www.postgresql.org/docs/16/rangetypes.html y https://www.postgresql.org/docs/16/sql-createtable.html

## Por qué EXCLUDE y no UNIQUE ni solo app

- `UNIQUE` solo evita igualdad escalar, no solapamiento de rangos.
- Validar solo en Python/ UI deja race conditions: dos `POST /turnos` concurrentes al mismo hueco crean doble reserva. El motor debe rechazar una con `409`.
- Regla dura: NUNCA doble reserva solo a nivel UI → constraint `EXCLUDE` a nivel motor.

## DDL de referencia

```sql
CREATE EXTENSION IF NOT EXISTS btree_gist;

CREATE TABLE turno (
  id UUID PRIMARY KEY,
  sillon_id UUID NOT NULL REFERENCES sillon(id),
  inicio TIMESTAMPTZ NOT NULL,
  fin TIMESTAMPTZ NOT NULL,
  estado TEXT NOT NULL,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  CHECK (fin > inicio),
  EXCLUDE USING GIST (
    sillon_id WITH =,
    tstzrange(inicio, fin) WITH &&
  ) WHERE (is_active AND estado NOT IN ('cancelado', 'ausente'))
);

CREATE INDEX ix_turno_sillon_inicio ON turno (sillon_id, inicio);
```

Claves:
- `btree_gist` es obligatoria porque `sillon_id WITH =` es escalar + rango con `&&`. Sin ella, Postgres falla.
- `tstzrange(inicio, fin)` exige `TIMESTAMPTZ`. Con `timestamp` naive se pierde zona horaria de agenda.
- `WHERE (...)` parcial: cancelados/ausentes e inactivos (soft delete) no bloquean. Sin WHERE, el historial bloquea la agenda futura.
- Intervalo `[inicio, fin)`: turnos pegados (10:00–10:30 y 10:30–11:00) NO solapan. `&&` lo respeta.

## SQLAlchemy 2.x async

```python
from sqlalchemy import CheckConstraint, Index
from sqlalchemy.dialects.postgresql import ExcludeConstraint, TSTZRANGE
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import DateTime

class Turno(Base):
    __tablename__ = "turno"
    inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fin: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    __table_args__ = (
        CheckConstraint("fin > inicio", name="ck_turno_fin_gt_inicio"),
        ExcludeConstraint(
            ("sillon_id", "="),
            ("tstzrange(inicio, fin)", "&&"),
            where="is_active AND estado NOT IN ('cancelado','ausente')",
            name="ex_turno_no_solape",
            using="gist",
        ),
        Index("ix_turno_sillon_inicio", "sillon_id", "inicio"),
    )
```

## Alembic

```python
def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
    op.create_table(...)  # con ExcludeConstraint
```

## Test motor (obligatorio C-02)

1. Crear turno 10:00–10:30 sillón 1 → 201.
2. Intentar 10:15–10:45 mismo sillón → debe fallar a nivel motor (`IntegrityError` / exclusion_violation).
3. Mismo horario en sillón 2 → OK.
4. Cancelar el primero y reintentar el hueco → OK (gracias al WHERE parcial).
5. Concurrencia: dos inserts simultáneos al mismo hueco → uno OK + otro 409 con oferta de alternativas.

## Errores típicos

| Síntoma | Causa | Fix |
|---|---|---|
| `operator class not found` | falta `btree_gist` | `CREATE EXTENSION btree_gist` |
| turnos pegados rechazan | rango `[a,b]` cerrado | usar `tstzrange` (`[)` por defecto) |
| cancelados bloquean | EXCLUDE sin WHERE | agregar `WHERE (is_active ...)` |
| hora corrida 3 h | `timestamp` naive | `TIMESTAMPTZ` en DDL y modelo |
