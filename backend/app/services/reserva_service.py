"""Reserva de turnos con invariantes de motor (C-05)."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from fastapi import HTTPException, status
from redis.exceptions import RedisError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db import redis as redis_client
from app.models import (
    IdempotenciaSolicitud,
    IntentoSena,
    Paciente,
    Sillon,
    Tratamiento,
    Turno,
    TurnoEvento,
)
from app.schemas.turnos import HorarioLibreOut, TurnoCreate
from app.services.disponibilidad_service import DisponibilidadService
from app.services.mp_adapter import MPAdapter, MPAdapterError
from app.shared.agenda_time import fecha_argentina


class DepositoRequerido(Exception):
    def __init__(self, checkout: dict | None = None) -> None:
        self.checkout = checkout or {"provider": "mercadopago", "status": "pendiente"}


class ReservaConflicto(Exception):
    def __init__(self, alternativas: list[HorarioLibreOut]) -> None:
        self.alternativas = alternativas


class ReservaService:
    def __init__(self, session: AsyncSession, mp_adapter: MPAdapter | None = None) -> None:
        self.session = session
        self.disp = DisponibilidadService(session)
        self._mp_adapter = mp_adapter

    @property
    def mp_adapter(self) -> MPAdapter:
        if self._mp_adapter is None:
            self._mp_adapter = MPAdapter()
        return self._mp_adapter

    async def _crear_checkout_seña(
        self,
        paciente_id: Any,
        sillon_id: Any,
        tratamiento: Tratamiento,
        inicio: Any,
    ) -> dict[str, Any]:
        from datetime import UTC, datetime, timedelta

        fin = inicio + timedelta(minutes=tratamiento.duracion_min)
        expires_at = datetime.now(UTC) + timedelta(minutes=15)

        intento = IntentoSena(
            paciente_id=paciente_id,
            sillon_id=sillon_id,
            tratamiento_id=tratamiento.id,
            inicio=inicio,
            fin=fin,
            duracion_min=tratamiento.duracion_min,
            monto_centavos=tratamiento.sena_centavos,
            moneda="ARS",
            sena_politica=tratamiento.sena_politica,
            estado="creando_checkout",
            expires_at=expires_at,
            modo=settings.mp_mode,
        )
        self.session.add(intento)
        await self.session.flush()
        await self.session.refresh(intento)

        try:
            pref = await self.mp_adapter.crear_preferencia(
                access_token=settings.mp_access_token,
                external_reference=str(intento.id),
                monto_centavos=tratamiento.sena_centavos,
                notification_url=settings.mp_notification_url
                or "https://turnos.local/webhooks/mercadopago",
                back_urls={
                    "success": f"{settings.frontend_url}/pagos/retorno",
                    "failure": f"{settings.frontend_url}/pagos/retorno",
                    "pending": f"{settings.frontend_url}/pagos/retorno",
                },
            )
        except MPAdapterError as exc:
            await self.session.rollback()
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"code": "CHECKOUT_NO_VERIFICADO", "intento_id": str(intento.id)},
            ) from exc

        intento.preference_id = pref.get("id")
        intento.checkout_url = pref.get("init_point") or pref.get("sandbox_init_point")
        intento.estado = "pendiente"
        await self.session.flush()
        await self.session.refresh(intento)
        # El intento se persiste aunque la reserva no se cree (402 no crea turno).
        await self.session.commit()

        return {
            "provider": "mercadopago",
            "status": "pendiente",
            "intento_id": str(intento.id),
            "checkout_url": intento.checkout_url,
            "expires_at": intento.expires_at.isoformat(),
            "monto_centavos": intento.monto_centavos,
            "moneda": "ARS",
            "modo": settings.mp_mode,
        }

    async def reservar(
        self,
        payload: TurnoCreate,
        paciente: Paciente,
        uow,
        idempotency_key: str | None = None,
    ) -> Turno:
        # Registra la clave de idempotencia de la solicitud (si se provee)
        # para que el endpoint no procese dos veces la misma operación del usuario.
        if idempotency_key:
            self.session.add(
                IdempotenciaSolicitud(
                    usuario_id=paciente.usuario_id,
                    operacion="reservar_turno",
                    clave=idempotency_key,
                )
            )
        sillon = await self.session.get(Sillon, payload.sillon_id)
        if sillon is None:
            raise HTTPException(status_code=404, detail="Sillón inexistente")
        if not sillon.is_active:
            raise HTTPException(status_code=422, detail="Sillón inactivo")

        tratamiento = await self.session.get(Tratamiento, payload.tratamiento_id)
        if tratamiento is None:
            raise HTTPException(status_code=404, detail="Tratamiento inexistente")
        if not tratamiento.is_active:
            raise HTTPException(status_code=422, detail="Tratamiento inactivo")

        requiere_sena = bool(payload.sena or payload.requiere_sena or payload.deposit)

        # Politica de servidor: decide si se exige seña independientemente de flags cliente.
        if tratamiento.sena_politica == "obligatoria":
            checkout = await self._crear_checkout_seña(
                paciente.id, sillon.id, tratamiento, payload.inicio
            )
            raise DepositoRequerido(checkout)
        if tratamiento.sena_politica == "deshabilitada" and requiere_sena:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "SENA_DESHABILITADA",
                    "detail": "La seña no está habilitada para este tratamiento",
                },
            )
        if tratamiento.sena_politica == "opcional" and requiere_sena:
            checkout = await self._crear_checkout_seña(
                paciente.id, sillon.id, tratamiento, payload.inicio
            )
            raise DepositoRequerido(checkout)

        inicio = payload.inicio
        fin = inicio + timedelta(minutes=tratamiento.duracion_min)
        tratamiento_id = tratamiento.id

        libres = await self.disp.libres(
            fecha_argentina(inicio), tratamiento_id, sillon.id, use_cache=False
        )
        if not any(slot.inicio == inicio and slot.sillon_id == sillon.id for slot in libres):
            alts = (
                await self.disp.libres(fecha_argentina(inicio), tratamiento_id, use_cache=False)
            )[:3]
            raise ReservaConflicto(alts)

        turno = Turno(
            paciente_id=paciente.id,
            sillon_id=sillon.id,
            tratamiento_id=tratamiento_id,
            inicio=inicio,
            fin=fin,
            estado="reservado",
            origen="online",
            es_sobreturno=False,
        )
        self.session.add(turno)
        try:
            await self.session.flush()
            await self.session.refresh(turno)
            self.session.add(
                TurnoEvento(
                    turno_id=turno.id,
                    actor_id=paciente.usuario_id,
                    accion="reservar",
                    origen="online",
                )
            )
            await uow.commit()
        except IntegrityError:
            await uow.rollback()
            alts = (
                await self.disp.libres(fecha_argentina(inicio), tratamiento_id, use_cache=False)
            )[:3]
            raise ReservaConflicto(alts)
        except Exception as exc:  # noqa: BLE001
            await uow.rollback()
            import logging

            logging.getLogger(__name__).warning("Error inesperado al reservar: %s", exc)
            alts = (
                await self.disp.libres(fecha_argentina(inicio), tratamiento_id, use_cache=False)
            )[:3]
            raise ReservaConflicto(alts)

        await self.disp.invalidar(fecha_argentina(inicio))

        try:
            redis = redis_client.get_redis()
            await redis.lpush("wa:reminders", str(turno.id))
        except (RedisError, OSError):
            pass

        return turno

    async def alternativas(self, fecha, tratamiento_id) -> list[HorarioLibreOut]:
        libres = await self.disp.libres(fecha, tratamiento_id, use_cache=False)
        return libres[:3]
