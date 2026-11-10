"""Contratos de seña MP (C-09)."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

ModoMP = Literal["mock", "sandbox", "production"]


class IntentoSenaCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sillon_id: UUID
    tratamiento_id: UUID
    inicio: AwareDatetime


class CheckoutOut(BaseModel):
    provider: str = "mercadopago"
    status: str = "pendiente"
    intento_id: UUID
    checkout_url: str | None = None
    expires_at: AwareDatetime
    monto_centavos: int = Field(gt=0)
    moneda: str = "ARS"
    modo: ModoMP


class IntentoSenaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    estado: str
    monto_centavos: int
    moneda: str
    expires_at: AwareDatetime
    turno_id: UUID | None = None
    requiere_contacto: bool = False


# --- Incidencias (C-09, tarea 6.3) ---

ResolucionIncidencia = Literal["reembolsado", "resuelto_en_consultorio"]


class IncidenciaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    intento_id: UUID
    estado: str
    monto_centavos: int
    moneda: str
    expires_at: AwareDatetime | None = None
    turno_id: UUID | None = None
    payment_id: str | None = None
    resultado: str | None = None


class IncidenciaListOut(BaseModel):
    items: list[IncidenciaOut]
    total: int
    page: int
    page_size: int


class ResolucionIncidenciaIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resolucion: ResolucionIncidencia
    motivo: str = Field(min_length=1, max_length=300)
    referencia_operacion: str | None = Field(default=None, max_length=120)
