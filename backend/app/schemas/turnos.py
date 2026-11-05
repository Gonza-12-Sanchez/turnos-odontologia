"""Contratos de disponibilidad y reserva (C-05)."""

from __future__ import annotations

from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class HorarioLibreOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sillon_id: UUID
    inicio: AwareDatetime
    fin: AwareDatetime


class TurnoCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sillon_id: UUID
    tratamiento_id: UUID
    inicio: AwareDatetime
    sena: bool = False
    requiere_sena: bool = False
    deposit: bool = False


class TurnoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    paciente_id: UUID
    sillon_id: UUID
    tratamiento_id: UUID
    inicio: AwareDatetime
    fin: AwareDatetime
    estado: str
    origen: str


class ConflictoOut(BaseModel):
    detail: str
    alternativas: list[HorarioLibreOut] = Field(default_factory=list)