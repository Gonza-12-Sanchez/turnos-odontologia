"""Tablas de seña MP, pagos, auditoría e idempotencia (C-09).

Aditivo: crea tablas nuevas y agrega unicidad de referencia_mp en cobro.
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers
revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "intento_sena",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("paciente_id", UUID, sa.ForeignKey("paciente.id"), nullable=False),
        sa.Column("sillon_id", UUID, sa.ForeignKey("sillon.id"), nullable=False),
        sa.Column("tratamiento_id", UUID, sa.ForeignKey("tratamiento.id"), nullable=False),
        sa.Column("inicio", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fin", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duracion_min", sa.Integer(), nullable=False),
        sa.Column("monto_centavos", sa.Integer(), nullable=False),
        sa.Column("moneda", sa.String(3), nullable=False, server_default="ARS"),
        sa.Column(
            "sena_politica", sa.String(20), nullable=False, server_default="deshabilitada"
        ),
        sa.Column(
            "estado",
            sa.String(20),
            nullable=False,
            server_default="creando_checkout",
        ),
        sa.Column("preference_id", sa.String(120), nullable=True, unique=True),
        sa.Column("checkout_url", sa.String(500), nullable=True),
        sa.Column("turno_id", UUID, sa.ForeignKey("turno.id"), nullable=True, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("modo", sa.String(20), nullable=False, server_default="mock"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "estado IN ('creando_checkout','pendiente','aprobado','rechazado','expirado','requiere_revision')",
            name="ck_intento_sena_estado",
        ),
        sa.CheckConstraint(
            "modo IN ('mock','sandbox','production')", name="ck_intento_sena_modo"
        ),
        sa.CheckConstraint("fin > inicio", name="ck_intento_sena_fin_gt_inicio"),
        sa.CheckConstraint("monto_centavos > 0", name="ck_intento_sena_monto_pos"),
    )
    op.create_index("ix_intento_sena_paciente", "intento_sena", ["paciente_id"])
    op.create_index("ix_intento_sena_estado", "intento_sena", ["estado"])
    op.create_index("ix_intento_sena_preference", "intento_sena", ["preference_id"])
    op.create_index("ix_intento_sena_turno", "intento_sena", ["turno_id"])

    op.create_table(
        "pago_mp",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("intento_id", UUID, sa.ForeignKey("intento_sena.id"), nullable=False),
        sa.Column("payment_id", sa.String(120), nullable=False, unique=True),
        sa.Column("estado_proveedor", sa.String(20), nullable=False),
        sa.Column("monto_centavos", sa.Integer(), nullable=False),
        sa.Column("moneda", sa.String(3), nullable=False, server_default="ARS"),
        sa.Column("receptor_id", sa.String(120), nullable=False),
        sa.Column("modo", sa.String(20), nullable=False, server_default="mock"),
        sa.Column(
            "resultado",
            sa.String(20),
            nullable=False,
            server_default="pendiente",
        ),
        sa.Column("fecha_aprobacion_proveedor", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "estado_proveedor IN ('approved','rejected','in_process','pending','cancelled','refunded','charged_back')",
            name="ck_pago_mp_estado_proveedor",
        ),
        sa.CheckConstraint(
            "resultado IN ('aplicado','incidencia','pendiente')", name="ck_pago_mp_resultado"
        ),
        sa.CheckConstraint("modo IN ('mock','sandbox','production')", name="ck_pago_mp_modo"),
        sa.CheckConstraint("monto_centavos > 0", name="ck_pago_mp_monto_pos"),
    )
    op.create_index("ix_pago_mp_intento", "pago_mp", ["intento_id"])
    op.create_index("ix_pago_mp_payment", "pago_mp", ["payment_id"])
    op.create_index("ix_pago_mp_resultado", "pago_mp", ["resultado"])

    op.create_table(
        "auditoria_cobro",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("actor_id", UUID, sa.ForeignKey("usuario.id"), nullable=True),
        sa.Column("accion", sa.String(40), nullable=False),
        sa.Column("cobro_id", UUID, sa.ForeignKey("cobro.id"), nullable=True),
        sa.Column("intento_id", UUID, sa.ForeignKey("intento_sena.id"), nullable=True),
        sa.Column("centavos", sa.Integer(), nullable=False),
        sa.Column("motivo", sa.String(300), nullable=True),
        sa.Column(
            "fecha", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("centavos >= 0", name="ck_auditoria_cobro_centavos"),
    )
    op.create_index("ix_auditoria_cobro_cobro", "auditoria_cobro", ["cobro_id"])
    op.create_index("ix_auditoria_cobro_intento", "auditoria_cobro", ["intento_id"])
    op.create_index("ix_auditoria_cobro_fecha", "auditoria_cobro", ["fecha"])

    op.create_table(
        "idempotencia_solicitud",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("usuario_id", UUID, sa.ForeignKey("usuario.id"), nullable=True),
        sa.Column("operacion", sa.String(40), nullable=False),
        sa.Column("clave", sa.String(120), nullable=False),
        sa.Column("huella", sa.String(64), nullable=True),
        sa.Column("resultado", postgresql.JSONB(none_as_null=True), nullable=True),
        sa.Column(
            "fecha", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_idempotencia_usuario_operacion_clave",
        "idempotencia_solicitud",
        ["usuario_id", "operacion", "clave"],
        unique=True,
    )
    op.create_index("ix_idempotencia_fecha", "idempotencia_solicitud", ["fecha"])

    # Unicidad de referencia_mp en cobro (varios NULL permitidos, un solo valor no nulo)
    op.create_unique_constraint("uq_cobro_referencia_mp", "cobro", ["referencia_mp"])


def downgrade() -> None:
    op.drop_constraint("uq_cobro_referencia_mp", "cobro", type_="unique")
    op.drop_index("ix_idempotencia_fecha", table_name="idempotencia_solicitud")
    op.drop_index("ix_idempotencia_usuario_operacion_clave", table_name="idempotencia_solicitud")
    op.drop_table("idempotencia_solicitud")
    op.drop_index("ix_auditoria_cobro_fecha", table_name="auditoria_cobro")
    op.drop_index("ix_auditoria_cobro_intento", table_name="auditoria_cobro")
    op.drop_index("ix_auditoria_cobro_cobro", table_name="auditoria_cobro")
    op.drop_table("auditoria_cobro")
    op.drop_index("ix_pago_mp_resultado", table_name="pago_mp")
    op.drop_index("ix_pago_mp_payment", table_name="pago_mp")
    op.drop_index("ix_pago_mp_intento", table_name="pago_mp")
    op.drop_table("pago_mp")
    op.drop_index("ix_intento_sena_turno", table_name="intento_sena")
    op.drop_index("ix_intento_sena_preference", table_name="intento_sena")
    op.drop_index("ix_intento_sena_estado", table_name="intento_sena")
    op.drop_index("ix_intento_sena_paciente", table_name="intento_sena")
    op.drop_table("intento_sena")
