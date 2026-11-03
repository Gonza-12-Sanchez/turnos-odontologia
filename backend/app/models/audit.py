"""AuditMixin compartido (soft delete + timestamps) para todas las entidades core."""

from __future__ import annotations

import sqlalchemy as sa
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column

from app.db.types import TZTimestamp


class AuditMixin:
    is_active: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, default=True, server_default=sa.text("true")
    )
    created_at: Mapped[datetime] = mapped_column(
        TZTimestamp(), nullable=False, server_default=sa.func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TZTimestamp(),
        nullable=False,
        server_default=sa.func.now(),
        onupdate=sa.func.now(),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(TZTimestamp(), nullable=True)
