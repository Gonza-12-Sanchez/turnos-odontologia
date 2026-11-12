"""Contratos de catálogo: PATCH distingue omitidos de null explícito."""

from typing import Annotated, ClassVar
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StrictBool, model_validator

SillonName = Annotated[str, Field(min_length=1, max_length=80)]
CatalogName = Annotated[str, Field(min_length=1, max_length=120)]
Duration = Annotated[int, Field(strict=True, gt=0, le=2147483647)]
Centavos = Annotated[int, Field(strict=True, ge=0, le=2147483647)]
SenaPolitica = Annotated[str, Field(strict=True, pattern="^(deshabilitada|opcional|obligatoria)$")]


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
    nullable_fields = frozenset({"precio_referencia_centavos", "sena_centavos"})
    nombre: CatalogName
    duracion_min: Duration
    precio_referencia_centavos: Centavos | None = None
    sena_politica: SenaPolitica = "deshabilitada"
    sena_centavos: Centavos | None = None
    activo: StrictBool = True

    @model_validator(mode="after")
    def validar_sena(self):
        if self.sena_politica == "deshabilitada":
            if self.sena_centavos is not None:
                raise ValueError(
                    "sena_centavos debe ser null cuando sena_politica es deshabilitada"
                )
        else:
            if self.sena_centavos is None or self.sena_centavos <= 0:
                raise ValueError(
                    "sena_centavos requiere entero positivo cuando la sena está habilitada"
                )
        return self


class TratamientoPatch(ConfigInput):
    nullable_fields = frozenset({"precio_referencia_centavos", "sena_centavos"})
    nombre: CatalogName | None = None
    duracion_min: Duration | None = None
    precio_referencia_centavos: Centavos | None = None
    sena_politica: SenaPolitica | None = None
    sena_centavos: Centavos | None = None
    activo: StrictBool | None = None

    @model_validator(mode="after")
    def validar_sena(self):
        politica = self.sena_politica
        centavos = self.sena_centavos
        if politica is not None:
            if politica == "deshabilitada":
                if centavos is not None:
                    raise ValueError(
                        "sena_centavos debe ser null cuando sena_politica es deshabilitada"
                    )
            else:
                if centavos is None or centavos <= 0:
                    raise ValueError(
                        "sena_centavos requiere entero positivo cuando la sena está habilitada"
                    )
        elif centavos is not None:
            raise ValueError("sena_centavos no se puede establecer sin definir sena_politica")
        return self


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


class ConsultorioResumen(BaseModel):
    id: UUID
    nombre: str


class ContextoConsultorioOut(BaseModel):
    consultorio: ConsultorioResumen | None


class SillonOut(CatalogOut):
    consultorio_id: UUID
    nombre: str


class TratamientoOut(CatalogOut):
    nombre: str
    duracion_min: int
    precio_referencia_centavos: int | None
    sena_politica: str = "deshabilitada"
    sena_centavos: int | None = None


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
