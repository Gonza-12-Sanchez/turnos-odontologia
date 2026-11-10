"""Política de seña y columnas de cobro (C-09).

Aditivo: no modifica tablas existentes salvo agregar columnas y restricciones.
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers
revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tratamiento",
        sa.Column(
            "sena_politica",
            sa.String(20),
            nullable=False,
            server_default="deshabilitada",
        ),
    )
    op.add_column(
        "tratamiento",
        sa.Column("sena_centavos", sa.Integer(), nullable=True),
    )
    op.create_check_constraint(
        "ck_tratamiento_sena_politica",
        "tratamiento",
        "sena_politica IN ('deshabilitada','opcional','obligatoria')",
    )
    op.create_check_constraint(
        "ck_tratamiento_sena_centavos_pos",
        "tratamiento",
        "sena_centavos IS NULL OR sena_centavos > 0",
    )


def downgrade() -> None:
    op.drop_constraint("ck_tratamiento_sena_centavos_pos", "tratamiento", type_="check")
    op.drop_constraint("ck_tratamiento_sena_politica", "tratamiento", type_="check")
    op.drop_column("tratamiento", "sena_centavos")
    op.drop_column("tratamiento", "sena_politica")
