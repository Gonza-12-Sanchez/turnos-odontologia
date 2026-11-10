"""Contratos de catálogo público (C-10): lectura anónima sin PII ni precio de referencia."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SillonPublicoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    nombre: str


class TratamientoPublicoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    nombre: str
    duracion_min: int
    sena_politica: str = "deshabilitada"
    sena_centavos: int | None = None


class CatalogoPublicoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    sillones: list[SillonPublicoOut] = []
    tratamientos: list[TratamientoPublicoOut] = []
