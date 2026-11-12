"""Calendario operativo del consultorio, con límites comparables en UTC."""

from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

ARGENTINA = ZoneInfo("America/Argentina/Buenos_Aires")


def fecha_argentina(instant: datetime) -> date:
    return instant.astimezone(ARGENTINA).date()


def limites_dia_argentino(fecha: date) -> tuple[datetime, datetime]:
    inicio = datetime.combine(fecha, time.min, tzinfo=ARGENTINA)
    fin = datetime.combine(fecha + timedelta(days=1), time.min, tzinfo=ARGENTINA)
    return inicio.astimezone(UTC), fin.astimezone(UTC)
