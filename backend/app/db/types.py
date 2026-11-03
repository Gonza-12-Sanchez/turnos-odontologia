"""Tipos SQLAlchemy con validación de zona horaria (TZDateTime)."""

from __future__ import annotations

from sqlalchemy import DateTime
from sqlalchemy.types import TypeDecorator


class TZTimestamp(TypeDecorator):
    """DateTime(timezone=True) que rechaza valores naive al bindear."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None and getattr(value, "tzinfo", None) is None:
            raise ValueError("datetime naive no permitido: se requiere tzinfo")
        return value

    def process_result_value(self, value, dialect):
        return value
