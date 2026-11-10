"""Registro y conciliación de cobros locales (C-09)."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AuditoriaCobro,
    Cobro,
    IdempotenciaSolicitud,
    Tratamiento,
    Turno,
)


class CobroError(HTTPException):
    def __init__(self, status_code: int, detail: Any, code: str | None = None):
        super().__init__(status_code=status_code, detail=detail)
        self.code = code


class CobroService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _turno_tratamiento(self, turno_id: UUID) -> tuple[Turno, Tratamiento | None]:
        turno = await self.session.get(Turno, turno_id)
        if turno is None or not turno.is_active:
            raise CobroError(status.HTTP_404_NOT_FOUND, "Turno inexistente o inactivo")
        tratamiento = await self.session.get(Tratamiento, turno.tratamiento_id)
        return turno, tratamiento

    async def _sena_acumulada(self, turno_id: UUID) -> int:
        result = await self.session.scalars(
            select(Cobro.monto_centavos).where(
                Cobro.turno_id == turno_id,
                Cobro.tipo == "sena",
                Cobro.is_active.is_(True),
                (Cobro.estado_mp.in_(["aprobado"]) | Cobro.estado_mp.is_(None)),
            )
        )
        return sum(result.all())

    async def _total_cobrado(self, turno_id: UUID) -> int:
        result = await self.session.scalars(
            select(Cobro.monto_centavos).where(
                Cobro.turno_id == turno_id, Cobro.is_active.is_(True)
            )
        )
        return sum(result.all())

    def _huella(
        self,
        turno_id: UUID,
        monto_centavos: int,
        medio: str,
        tipo: str,
        override_motivo: str | None,
    ) -> str:
        payload = {
            "turno_id": str(turno_id),
            "monto_centavos": monto_centavos,
            "medio": medio,
            "tipo": tipo,
            "override_motivo": override_motivo,
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()

    def _resultado_cobro(self, cobro: Cobro) -> dict[str, Any]:
        return {
            "id": str(cobro.id),
            "turno_id": str(cobro.turno_id),
            "monto_centavos": cobro.monto_centavos,
            "medio": cobro.medio,
            "tipo": cobro.tipo,
            "estado_mp": cobro.estado_mp,
            "referencia_mp": cobro.referencia_mp,
        }

    async def registrar(
        self,
        turno_id: UUID,
        monto_centavos: int,
        medio: str,
        tipo: str,
        actor_id: UUID,
        idempotency_key: str | None,
        override_motivo: str | None,
    ) -> tuple[dict[str, Any], bool]:
        # Idempotencia: misma clave + mismo payload devuelve resultado cacheado.
        huella = self._huella(turno_id, monto_centavos, medio, tipo, override_motivo)
        if idempotency_key:
            existente = (
                await self.session.scalars(
                    select(IdempotenciaSolicitud).where(
                        IdempotenciaSolicitud.usuario_id == actor_id,
                        IdempotenciaSolicitud.operacion == "cobros:registro",
                        IdempotenciaSolicitud.clave == idempotency_key,
                    )
                )
            ).first()
            if existente is not None:
                if existente.huella != huella:
                    raise CobroError(
                        status.HTTP_409_CONFLICT,
                        {"code": "IDEMPOTENCIA_CLAVE_DIFERENTE", "clave": idempotency_key},
                        code="IDEMPOTENCIA_CLAVE_DIFERENTE",
                    )
                if existente.resultado:
                    return {
                        "cobro": existente.resultado,
                        "sena_acumulada_centavos": 0,
                        "total_cobrado_centavos": 0,
                        "saldo_referencia_centavos": None,
                        "warnings": [{"code": "IDEMPOTENCIA_REPLAY"}],
                        "facturacion_electronica": False,
                    }, True

        # Bloqueo de turno para serializar conciliación.
        _turno, tratamiento = await self._turno_tratamiento(turno_id)
        await self.session.execute(select(Turno).where(Turno.id == turno_id).with_for_update())

        sena_acumulada = await self._sena_acumulada(turno_id)
        precio = tratamiento.precio_referencia_centavos if tratamiento else None

        # Validación de duplicación de sena por turno.
        if tipo == "sena" and sena_acumulada > 0:
            raise CobroError(
                status.HTTP_409_CONFLICT,
                {"code": "SENA_DUPLICADA", "turno_id": str(turno_id)},
                code="SENA_DUPLICADA",
            )

        # Cierre por cero no crea movimiento.
        if monto_centavos <= 0:
            raise CobroError(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                {"code": "MONTO_CERO", "detail": "El monto debe ser positivo"},
                code="MONTO_CERO",
            )

        # Conciliación: solo el cierre (tipo=total) compara contra precio de referencia.
        warnings: list[dict] = []
        saldo_referencia: int | None = None
        if precio is None:
            warnings.append({"code": "PRECIO_SIN_REFERENCIA"})
        elif tipo == "total":
            esperado = precio - sena_acumulada
            esperado = max(esperado, 0)
            if monto_centavos != esperado:
                if not override_motivo:
                    raise CobroError(
                        status.HTTP_409_CONFLICT,
                        {
                            "code": "MONTO_DIFIERE",
                            "esperado_centavos": esperado,
                            "recibido_centavos": monto_centavos,
                            "turno_id": str(turno_id),
                        },
                        code="MONTO_DIFIERE",
                    )
                warnings.append(
                    {
                        "code": "MONTO_DIFIERE_OVERRIDE",
                        "esperado_centavos": esperado,
                        "recibido_centavos": monto_centavos,
                        "motivo": override_motivo,
                    }
                )
            saldo_referencia = precio - (sena_acumulada + monto_centavos)
            saldo_referencia = max(saldo_referencia, 0)

        cobro = Cobro(
            turno_id=turno_id,
            monto_centavos=monto_centavos,
            medio=medio,
            tipo=tipo,
            estado_mp=None,
            referencia_mp=None,
        )
        self.session.add(cobro)
        await self.session.flush()
        await self.session.refresh(cobro)

        total_cobrado = sena_acumulada + monto_centavos

        # Auditoria del cobro.
        self.session.add(
            AuditoriaCobro(
                actor_id=actor_id,
                accion="registrar_cobro",
                cobro_id=cobro.id,
                centavos=monto_centavos,
                motivo=override_motivo,
                fecha=datetime.now(UTC),
            )
        )

        # Persistir registro de idempotencia con el resultado del cobro.
        if idempotency_key:
            resultado_cobro = self._resultado_cobro(cobro)
            self.session.add(
                IdempotenciaSolicitud(
                    usuario_id=actor_id,
                    operacion="cobros:registro",
                    clave=idempotency_key,
                    huella=huella,
                    resultado=resultado_cobro,
                )
            )

        return {
            "cobro": self._resultado_cobro(cobro),
            "sena_acumulada_centavos": sena_acumulada,
            "total_cobrado_centavos": total_cobrado,
            "saldo_referencia_centavos": saldo_referencia,
            "warnings": warnings,
            "facturacion_electronica": False,
        }, False
