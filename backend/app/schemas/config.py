"""Contratos de catálogo: PATCH distingue omitidos de null explícito."""

from typing import Annotated, ClassVar
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StrictBool, model_validator

SillonName = Annotated[str, Field(min_length=1, max_length=80)]
CatalogName = Annotated[str, Field(min_length=1, max_length=120)]
Duration = Annotated[int, Field(strict=True, gt=0, le=2147483647)]
Centavos = Annotated[int, Field(strict=True, ge=0, le=2147483647)]


class ConfigInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    nullable_fields: ClassVar[frozenset[str]] = frozenset()

    @model_validator(mode="before")
    @classmethod
    def reject_explicit_null(cls, data):
        if isinstance(data, dict):
            for key, value in data.items():
                if value is None and key not in cls.nullable_fields:
                    raise ValueError(f"{key} no admite null")
        return data


class ActivityPatch(ConfigInput):
    activo: StrictBool | None = None


class SillonCreate(ConfigInput):
    consultorio_id: UUID
    nombre: SillonName
    activo: StrictBool = True


class SillonPatch(ConfigInput):
    consultorio_id: UUID | None = None
    nombre: SillonName | None = None
    activo: StrictBool | None = None


class TratamientoCreate(ConfigInput):
    nullable_fields = frozenset({"precio_referencia_centavos"})
    nombre: CatalogName
    duracion_min: Duration
    precio_referencia_centavos: Centavos | None = None
    activo: StrictBool = True


class TratamientoPatch(ConfigInput):
    nullable_fields = frozenset({"precio_referencia_centavos"})
    nombre: CatalogName | None = None
    duracion_min: Duration | None = None
    precio_referencia_centavos: Centavos | None = None
    activo: StrictBool | None = None


class BloqueoCreate(ConfigInput):
    nullable_fields = frozenset({"sillon_id"})
    sillon_id: UUID | None = None
    desde: AwareDatetime
    hasta: AwareDatetime
    motivo: CatalogName
    activo: StrictBool = True

    @model_validator(mode="after")
    def valid_range(self):
        if self.hasta <= self.desde:
            raise ValueError("hasta debe ser posterior a desde")
        return self


class BloqueoPatch(ConfigInput):
    nullable_fields = frozenset({"sillon_id"})
    sillon_id: UUID | None = None
    desde: AwareDatetime | None = None
    hasta: AwareDatetime | None = None
    motivo: CatalogName | None = None
    activo: StrictBool | None = None


class ConfigWarning(BaseModel):
    code: str = "TURNOS_SOLAPADOS"
    cantidad: int


class CatalogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
    id: UUID
    activo: bool = Field(validation_alias="is_active")
    created_at: AwareDatetime
    updated_at: AwareDatetime
    deleted_at: AwareDatetime | None


class SillonOut(CatalogOut):
    consultorio_id: UUID
    nombre: str


class TratamientoOut(CatalogOut):
    nombre: str
    duracion_min: int
    precio_referencia_centavos: int | None


class BloqueoOut(CatalogOut):
    sillon_id: UUID | None
    desde: AwareDatetime
    hasta: AwareDatetime
    motivo: str
    warnings: list[ConfigWarning] = Field(default_factory=list)


class Page[T](BaseModel):
    items: list[T]
    total: int
    page: int
    page_size: int
