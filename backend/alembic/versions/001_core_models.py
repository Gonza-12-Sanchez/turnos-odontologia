"""Migración 001: modelos core + EXCLUDE anti-solapamiento (C-02)."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "001"
down_revision = None
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")

    op.create_table(
        "consultorio",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("nombre", sa.String(120), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "sillon",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("consultorio_id", UUID, sa.ForeignKey("consultorio.id"), nullable=False),
        sa.Column("nombre", sa.String(80), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_sillon_consultorio", "sillon", ["consultorio_id"])

    op.create_table(
        "tratamiento",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("nombre", sa.String(120), nullable=False),
        sa.Column("duracion_min", sa.Integer(), nullable=False),
        sa.Column("precio_referencia_centavos", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("duracion_min > 0", name="ck_tratamiento_duracion_min"),
        sa.CheckConstraint("precio_referencia_centavos >= 0", name="ck_tratamiento_precio_centavos"),
    )

    op.create_table(
        "usuario",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("telefono", sa.String(32), nullable=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("rol", sa.String(20), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("rol IN ('paciente','odontologo','secretaria')", name="ck_usuario_rol"),
        sa.CheckConstraint("email IS NOT NULL OR telefono IS NOT NULL", name="ck_usuario_contacto"),
    )
    op.create_index("uq_usuario_email", "usuario", ["email"], unique=True)
    op.create_index("ix_usuario_rol_activo", "usuario", ["rol", "is_active"])

    op.create_table(
        "paciente",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("usuario_id", UUID, sa.ForeignKey("usuario.id"), nullable=False, unique=True),
        sa.Column("nombre", sa.String(120), nullable=False),
        sa.Column("telefono", sa.String(32), nullable=False),
        sa.Column("obra_social", sa.String(120), nullable=True),
        sa.Column("notas", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "turno",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("paciente_id", UUID, sa.ForeignKey("paciente.id"), nullable=False),
        sa.Column("sillon_id", UUID, sa.ForeignKey("sillon.id"), nullable=False),
        sa.Column("tratamiento_id", UUID, sa.ForeignKey("tratamiento.id"), nullable=False),
        sa.Column("odontologo_id", UUID, sa.ForeignKey("usuario.id"), nullable=True),
        sa.Column("inicio", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fin", sa.DateTime(timezone=True), nullable=False),
        sa.Column("estado", sa.String(20), nullable=False, server_default="reservado"),
        sa.Column("origen", sa.String(20), nullable=False, server_default="online"),
        sa.Column("es_sobreturno", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("motivo_sobreturno", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("fin > inicio", name="ck_turno_fin_gt_inicio"),
        sa.CheckConstraint("estado IN ('reservado','confirmado','asistido','cancelado','ausente')", name="ck_turno_estado"),
        sa.CheckConstraint("origen IN ('online','mostrador','whatsapp')", name="ck_turno_origen"),
        postgresql.ExcludeConstraint(
            ("sillon_id", "="),
            (sa.text("tstzrange(inicio, fin)"), "&&"),
            where="is_active AND estado NOT IN ('cancelado','ausente')",
            name="ex_turno_no_solape",
            using="gist",
        ),
    )
    op.create_index("ix_turno_sillon_inicio", "turno", ["sillon_id", "inicio"])
    op.create_index("ix_turno_paciente_inicio", "turno", ["paciente_id", "inicio"])
    op.create_index("ix_turno_estado_inicio", "turno", ["estado", "inicio"])

    op.create_table(
        "bloqueo",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("sillon_id", UUID, sa.ForeignKey("sillon.id"), nullable=True),
        sa.Column("desde", sa.DateTime(timezone=True), nullable=False),
        sa.Column("hasta", sa.DateTime(timezone=True), nullable=False),
        sa.Column("motivo", sa.String(120), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("hasta > desde", name="ck_bloqueo_hasta_gt_desde"),
    )
    op.create_index("ix_bloqueo_sillon_desde", "bloqueo", ["sillon_id", "desde"])

    op.create_table(
        "recordatorio_wa",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("turno_id", UUID, sa.ForeignKey("turno.id"), nullable=False),
        sa.Column("tipo", sa.String(20), nullable=False),
        sa.Column("plantilla", sa.String(120), nullable=False),
        sa.Column("message_id", sa.String(120), nullable=True),
        sa.Column("estado", sa.String(20), nullable=False, server_default="enviado"),
        sa.Column("respuesta", sa.String(20), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("tipo IN ('recordatorio','confirmacion')", name="ck_recordatorio_tipo"),
        sa.CheckConstraint("estado IN ('enviado','entregado','leido','respondido','fallido')", name="ck_recordatorio_estado"),
        sa.CheckConstraint("respuesta IS NULL OR respuesta IN ('confirmo','cancelo')", name="ck_recordatorio_respuesta"),
    )
    op.create_index("ix_recordatorio_turno", "recordatorio_wa", ["turno_id"])

    op.create_table(
        "cobro",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("turno_id", UUID, sa.ForeignKey("turno.id"), nullable=False),
        sa.Column("monto_centavos", sa.Integer(), nullable=False),
        sa.Column("medio", sa.String(20), nullable=False),
        sa.Column("tipo", sa.String(20), nullable=False),
        sa.Column("estado_mp", sa.String(20), nullable=True),
        sa.Column("referencia_mp", sa.String(120), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("monto_centavos >= 0", name="ck_cobro_monto_centavos"),
        sa.CheckConstraint("medio IN ('efectivo','transferencia','mercadopago')", name="ck_cobro_medio"),
        sa.CheckConstraint("tipo IN ('sena','total')", name="ck_cobro_tipo"),
        sa.CheckConstraint("estado_mp IS NULL OR estado_mp IN ('pendiente','aprobado')", name="ck_cobro_estado_mp"),
    )
    op.create_index("ix_cobro_turno", "cobro", ["turno_id"])


def downgrade() -> None:
    op.drop_table("cobro")
    op.drop_table("recordatorio_wa")
    op.drop_table("bloqueo")
    op.drop_table("turno")
    op.drop_table("paciente")
    op.drop_table("usuario")
    op.drop_table("tratamiento")
    op.drop_table("sillon")
    op.drop_table("consultorio")
    # extensión btree_gist se deja (puede estar en uso)