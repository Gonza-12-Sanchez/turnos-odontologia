"""Auditoría transaccional de configuración (C-04)."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "config_audit",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "actor_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("usuario.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("recurso", sa.String(20), nullable=False),
        sa.Column("recurso_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("accion", sa.String(20), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("antes", postgresql.JSONB(none_as_null=True), nullable=True),
        sa.Column("despues", postgresql.JSONB(none_as_null=True), nullable=True),
        sa.CheckConstraint(
            "recurso IN ('sillon','tratamiento','bloqueo')", name="ck_config_audit_recurso"
        ),
        sa.CheckConstraint(
            "accion IN ('crear','actualizar','desactivar','reactivar')",
            name="ck_config_audit_accion",
        ),
    )
    op.create_index(
        "ix_config_audit_recurso_fecha", "config_audit", ["recurso", "recurso_id", "created_at"]
    )
    op.create_index("ix_config_audit_actor_fecha", "config_audit", ["actor_id", "created_at"])


def downgrade() -> None:
    op.drop_table("config_audit")
