"""Contratos de disponibilidad y reserva (C-05)."""

from __future__ import annotations

from typing import Literal
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
    es_sobreturno: bool = False
    motivo_sobreturno: str | None = None
    tolerancia_min: int = 5


class ReprogramarIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    inicio: AwareDatetime
    sillon_id: UUID | None = None


class MarcarAsistenciaIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    estado: Literal["asistido", "ausente"]


class SobreturnoIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    motivo: str = Field(min_length=1, max_length=200)


class GestionTurnoPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    es_sobreturno: bool | None = None
    motivo_sobreturno: str | None = None
    origen: str | None = None


class AccionesOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    cancelar: bool = False
    confirmar: bool = False
    reprogramar: bool = False


class AgendaTurnoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    sillon_id: UUID
    sillon_nombre: str
    paciente_id: UUID
    paciente_nombre: str
    tratamiento_id: UUID
    tratamiento_nombre: str
    duracion_min: int
    inicio: AwareDatetime
    fin: AwareDatetime
    estado: str
    origen: str
    es_sobreturno: bool = False
    motivo_sobreturno: str | None = None
    tolerancia_min: int = 5


class AgendaSillonOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sillon_id: UUID
    sillon_nombre: str
    sillon: dict | None = None
    turnos: list[AgendaTurnoOut] = Field(default_factory=list)


class MisReservaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    sillon_id: UUID
    sillon_nombre: str
    tratamiento_id: UUID
    tratamiento_nombre: str
    inicio: AwareDatetime
    fin: AwareDatetime
    estado: str
    origen: str
    es_sobreturno: bool = False
    tolerancia_min: int = 5
    acciones: AccionesOut
    acciones_permitidas: AccionesOut | None = None


class ConflictoOut(BaseModel):
    detail: str
    alternativas: list[HorarioLibreOut] = Field(default_factory=list)
