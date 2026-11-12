"""Historial persistido de la gestión de turnos."""

import sqlalchemy as sa

from alembic import op

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "turno_evento",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("turno_id", sa.Uuid(), sa.ForeignKey("turno.id"), nullable=False),
        sa.Column("actor_id", sa.Uuid(), sa.ForeignKey("usuario.id")),
        sa.Column("accion", sa.String(40), nullable=False),
        sa.Column("origen", sa.String(20), nullable=False),
        sa.Column("motivo", sa.String(200)),
        sa.Column(
            "fecha", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_turno_evento_turno_fecha", "turno_evento", ["turno_id", "fecha"])


def downgrade() -> None:
    op.drop_table("turno_evento")
