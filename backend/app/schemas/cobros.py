"""Contratos de cobros (C-09). Montos siempre en centavos ARS."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictInt

Medio = Literal["efectivo", "transferencia", "mercadopago"]
Tipo = Literal["sena", "total"]


class CobroCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    turno_id: UUID
    monto_centavos: StrictInt = Field(gt=0, le=2147483647)
    medio: Medio
    tipo: Tipo
    override_motivo: str | None = Field(default=None, min_length=1, max_length=300)


class CobroOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    turno_id: UUID
    monto_centavos: int
    medio: Medio
    tipo: Tipo
    estado_mp: str | None = None
    referencia_mp: str | None = None


class CobroConciliacionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    cobro: CobroOut
    sena_acumulada_centavos: int
    total_cobrado_centavos: int
    saldo_referencia_centavos: int | None = None
    warnings: list[dict] = Field(default_factory=list)
    facturacion_electronica: bool = False


class CobroResumenOut(BaseModel):
    precio_referencia_centavos: int | None
    sena_acumulada_centavos: int
    total_cobrado_centavos: int
    saldo_referencia_centavos: int | None
    cerrado: bool


class CobroListOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    turno_id: UUID
    monto_centavos: int
    medio: Medio
    tipo: Tipo
    estado_mp: str | None = None
    referencia_mp: str | None = None
    created_at: str
