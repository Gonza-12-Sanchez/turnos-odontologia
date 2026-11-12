"""Gestion de intentos de seña MP y checkout (C-09)."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import (
    AuditoriaCobro,
    Cobro,
    IdempotenciaSolicitud,
    IntentoSena,
    Paciente,
    PagoMP,
    Tratamiento,
    Turno,
)
from app.services.disponibilidad_service import DisponibilidadService
from app.services.mp_adapter import MPAdapter, MPAdapterError
from app.shared.agenda_time import fecha_argentina


class SenaError(HTTPException):
    def __init__(self, status_code: int, detail: Any, code: str | None = None):
        super().__init__(status_code=status_code, detail=detail)
        self.code = code


class SenaService:
    def __init__(self, session: AsyncSession, mp_adapter: MPAdapter | None = None) -> None:
        self.session = session
        self._mp_adapter: MPAdapter | None = mp_adapter

    @property
    def mp_adapter(self) -> MPAdapter:
        if self._mp_adapter is None:
            self._mp_adapter = MPAdapter()
        return self._mp_adapter

    async def _tratamiento_y_politica(self, tratamiento_id: UUID) -> Tratamiento:
        tratamiento = await self.session.get(Tratamiento, tratamiento_id)
        if tratamiento is None or not tratamiento.is_active:
            raise SenaError(status.HTTP_404_NOT_FOUND, "Tratamiento inexistente o inactivo")
        if tratamiento.sena_politica == "deshabilitada":
            raise SenaError(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                {"code": "SENA_DESHABILITADA", "tratamiento_id": str(tratamiento_id)},
                code="SENA_DESHABILITADA",
            )
        if tratamiento.sena_centavos is None or tratamiento.sena_centavos <= 0:
            raise SenaError(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                {"code": "SENA_SIN_MONTO", "tratamiento_id": str(tratamiento_id)},
                code="SENA_SIN_MONTO",
            )
        return tratamiento

    async def _hueco_disponible(
        self, sillon_id: UUID, tratamiento_id: UUID, inicio: datetime
    ) -> None:
        disp = DisponibilidadService(self.session)
        await self.session.get(Tratamiento, tratamiento_id)
        libres = await disp.libres(
            fecha_argentina(inicio), tratamiento_id, sillon_id, use_cache=False
        )
        if not any(slot.inicio == inicio and slot.sillon_id == sillon_id for slot in libres):
            alts = (await disp.libres(fecha_argentina(inicio), tratamiento_id, use_cache=False))[:3]
            raise SenaError(
                status.HTTP_409_CONFLICT,
                {
                    "code": "HUECO_NO_DISPONIBLE",
                    "alternativas": [a.model_dump(mode="json") for a in alts],
                },
                code="HUECO_NO_DISPONIBLE",
            )

    async def _idempotencia_existe(
        self, paciente_id: UUID, clave: str
    ) -> IdempotenciaSolicitud | None:
        result = await self.session.scalars(
            select(IdempotenciaSolicitud).where(
                IdempotenciaSolicitud.usuario_id == paciente_id,
                IdempotenciaSolicitud.operacion == "pagos:sena",
                IdempotenciaSolicitud.clave == clave,
            )
        )
        return result.first()

    def _checkout_dict(self, intento: IntentoSena) -> dict[str, Any]:
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

    def _huella(self, sillon_id: UUID, tratamiento_id: UUID, inicio: datetime) -> str:
        payload = {
            "sillon_id": str(sillon_id),
            "tratamiento_id": str(tratamiento_id),
            "inicio": inicio.isoformat(),
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()

    async def crear_intento(
        self,
        paciente_id: UUID,
        sillon_id: UUID,
        tratamiento_id: UUID,
        inicio: datetime,
        idempotency_key: str | None,
    ) -> tuple[dict[str, Any], bool]:
        if settings.mp_mode == "disabled":
            raise SenaError(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                {"code": "MP_DESHABILITADO", "detail": "Integracion de pago no disponible"},
                code="MP_DESHABILITADO",
            )

        paciente = await self.session.get(Paciente, paciente_id)
        if paciente is None:
            raise SenaError(status.HTTP_404_NOT_FOUND, "Paciente inexistente")

        # Idempotencia: misma clave + mismo payload devuelve checkout cacheado.
        huella = self._huella(sillon_id, tratamiento_id, inicio)
        if idempotency_key:
            existente = await self._idempotencia_existe(paciente.usuario_id, idempotency_key)
            if existente is not None:
                if existente.huella is not None and existente.huella != huella:
                    raise SenaError(
                        status.HTTP_409_CONFLICT,
                        {"code": "IDEMPOTENCIA_CLAVE_DIFERENTE", "clave": idempotency_key},
                        code="IDEMPOTENCIA_CLAVE_DIFERENTE",
                    )
                if existente.resultado:
                    return existente.resultado, True

        tratamiento = await self._tratamiento_y_politica(tratamiento_id)
        await self._hueco_disponible(sillon_id, tratamiento_id, inicio)

        fin = inicio + timedelta(minutes=tratamiento.duracion_min)
        expires_at = datetime.now(UTC) + timedelta(minutes=15)

        intento = IntentoSena(
            paciente_id=paciente_id,
            sillon_id=sillon_id,
            tratamiento_id=tratamiento_id,
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
            raise SenaError(
                exc.status_code,
                exc.detail,
                code=exc.code or "CHECKOUT_NO_VERIFICADO",
            )

        intento.preference_id = pref.get("id")
        intento.checkout_url = pref.get("init_point") or pref.get("sandbox_init_point")
        intento.estado = "pendiente"
        await self.session.flush()
        await self.session.refresh(intento)

        checkout = self._checkout_dict(intento)

        if idempotency_key:
            self.session.add(
                IdempotenciaSolicitud(
                    usuario_id=paciente.usuario_id,
                    operacion="pagos:sena",
                    clave=idempotency_key,
                    huella=huella,
                    resultado=checkout,
                )
            )

        return checkout, False

    # ------------------------------------------------------------------
    # Webhook MP: aplicacion atomica e idempotente (tareas 5.1, 5.2, 5.3)
    # ------------------------------------------------------------------

    async def _pago_mp_por_payment_id(self, payment_id: str) -> PagoMP | None:
        result = await self.session.scalars(select(PagoMP).where(PagoMP.payment_id == payment_id))
        return result.first()

    async def _verificar_pago_mp(self, pago_mp: dict, intento_id: str) -> tuple[bool, str | None]:
        """Verifica campos financieros del pago MP contra el intento.
        Returns (valido, motivo_rechazo)."""
        # collector_id esperado
        if settings.mp_collector_id and pago_mp.get("collector_id") != settings.mp_collector_id:
            return False, "collector_id_no_coincide"
        # moneda ARS
        if pago_mp.get("currency_id") != "ARS":
            return False, "moneda_no_es_ARS"
        # monto exacto contra snapshot del intento
        intento = await self.session.get(IntentoSena, UUID(intento_id))
        if intento is None:
            return False, "intento_inexistente"
        monto_proveedor = pago_mp.get("transaction_amount")
        if monto_proveedor is not None:
            try:
                monto_centavos_proveedor = int(Decimal(str(monto_proveedor)) * 100)
            except (ValueError, TypeError):
                return False, "monto_proveedor_invalido"
            if monto_centavos_proveedor != intento.monto_centavos:
                return False, "monto_no_coincide"
        return True, None

    async def _registrar_pago_mp(
        self, intento: IntentoSena, pago_mp: dict, resultado: str = "pendiente"
    ) -> PagoMP:
        pago = PagoMP(
            intento_id=intento.id,
            payment_id=str(pago_mp.get("id")),
            estado_proveedor=str(pago_mp.get("status", "pending")),
            monto_centavos=intento.monto_centavos,
            moneda=str(pago_mp.get("currency_id", "ARS")),
            receptor_id=str(pago_mp.get("collector_id", "")),
            modo=intento.modo,
            resultado=resultado,
            fecha_aprobacion_proveedor=(
                datetime.fromisoformat(pago_mp["date_approved"])
                if pago_mp.get("date_approved")
                else None
            ),
        )
        self.session.add(pago)
        await self.session.flush()
        await self.session.refresh(pago)
        return pago

    async def _aplicar_aprobado_atomico(
        self, intento: IntentoSena, pago_mp: dict
    ) -> dict[str, Any]:
        """Crea Turno + Cobro + Auditoria + PagoMP en una transacción corta.
        Devuelve aplicado=False si no hay cupo (sin lanzar IntegrityError)."""
        payment_id_str = str(pago_mp.get("id"))

        # Idempotencia: ya aprobado con turno -> registrar pago extra sin duplicar turno
        if intento.estado == "aprobado" and intento.turno_id is not None:
            await self._registrar_pago_mp(intento, pago_mp, resultado="aplicado")
            return {"aplicado": True, "duplicado": True, "payment_id": payment_id_str}

        # Bloquear intento para evitar carreras entre webhooks concurrentes
        await self.session.execute(
            select(IntentoSena).where(IntentoSena.id == intento.id).with_for_update()
        )

        # Revalidar disponibilidad sin cache antes de crear turno
        disp = DisponibilidadService(self.session)
        libres = await disp.libres(
            fecha_argentina(intento.inicio),
            intento.tratamiento_id,
            intento.sillon_id,
            use_cache=False,
        )
        if not any(
            slot.inicio == intento.inicio and slot.sillon_id == intento.sillon_id for slot in libres
        ):
            # Sin cupo: registrar incidencia, sin turno ni cobro
            await self._registrar_pago_mp(intento, pago_mp, resultado="incidencia")
            intento.estado = "requiere_revision"
            await self.session.flush()
            return {
                "aplicado": False,
                "motivo": "sin_cupo_disponible",
                "incidencia": True,
                "payment_id": payment_id_str,
            }

        fin = intento.inicio + timedelta(minutes=intento.duracion_min)
        turno = Turno(
            paciente_id=intento.paciente_id,
            sillon_id=intento.sillon_id,
            tratamiento_id=intento.tratamiento_id,
            inicio=intento.inicio,
            fin=fin,
            estado="reservado",
            origen="online",
            es_sobreturno=False,
        )
        self.session.add(turno)
        await self.session.flush()
        await self.session.refresh(turno)

        # Cobro sena aprobado (referencia_mp = payment_id)
        cobro = Cobro(
            turno_id=turno.id,
            monto_centavos=intento.monto_centavos,
            medio="mercadopago",
            tipo="sena",
            estado_mp="aprobado",
            referencia_mp=payment_id_str,
        )
        self.session.add(cobro)
        await self.session.flush()
        await self.session.refresh(cobro)

        # Auditoria del cobro
        self.session.add(
            AuditoriaCobro(
                actor_id=None,
                accion="aplicar_pago_mp",
                cobro_id=cobro.id,
                intento_id=intento.id,
                centavos=intento.monto_centavos,
                motivo="Pago MP aprobado via webhook",
                fecha=datetime.now(UTC),
            )
        )

        # PagoMP aplicado
        await self._registrar_pago_mp(intento, pago_mp, resultado="aplicado")

        # Marcar intento aprobado
        intento.estado = "aprobado"
        intento.turno_id = turno.id
        await self.session.flush()

        return {"aplicado": True, "duplicado": False, "payment_id": payment_id_str}

    async def _registrar_incidencia_sin_cupo(
        self, intento: IntentoSena, pago_mp: dict
    ) -> dict[str, Any]:
        """Pago aprobado pero sin cupo: incidencia durable, sin turno ni cobro."""
        payment_id_str = str(pago_mp.get("id"))
        # Re-fetch intento por si el objeto esta expirado tras rollback previo
        intento_fresh = await self.session.get(IntentoSena, intento.id)
        if intento_fresh is None:
            intento_fresh = intento
        if intento_fresh.estado == "aprobado" and intento_fresh.turno_id is not None:
            await self._registrar_pago_mp(intento_fresh, pago_mp, resultado="aplicado")
            return {"aplicado": True, "duplicado": True, "payment_id": payment_id_str}
        await self._registrar_pago_mp(intento_fresh, pago_mp, resultado="incidencia")
        intento_fresh.estado = "requiere_revision"
        await self.session.flush()
        return {
            "aplicado": False,
            "motivo": "sin_cupo_disponible",
            "incidencia": True,
            "payment_id": payment_id_str,
        }

    async def _rechazar_intento(self, intento: IntentoSena, pago_mp: dict) -> dict[str, Any]:
        await self.session.execute(
            select(IntentoSena).where(IntentoSena.id == intento.id).with_for_update()
        )
        if intento.estado == "aprobado":
            return {"aplicado": True, "duplicado": True, "payment_id": str(pago_mp.get("id"))}
        await self._registrar_pago_mp(intento, pago_mp, resultado="pendiente")
        intento.estado = "rechazado"
        await self.session.flush()
        return {"aplicado": False, "motivo": "pago_rechazado", "payment_id": str(pago_mp.get("id"))}

    async def aplicar_pago_webhook(self, payment_id: str, evento: dict) -> dict[str, Any]:
        """Procesa un webhook de Mercado Pago: valida, consulta y aplica o registra incidencia."""
        # Idempotencia: payment_id ya procesado
        existente = await self._pago_mp_por_payment_id(payment_id)
        if existente is not None:
            return {
                "aplicado": existente.resultado == "aplicado",
                "duplicado": True,
                "payment_id": payment_id,
            }

        # Consultar el pago en MP (verificacion propia del servidor)
        try:
            pago_mp = await self.mp_adapter.obtener_pago(settings.mp_access_token, payment_id)
        except MPAdapterError as exc:
            if exc.status_code >= 500:
                raise HTTPException(
                    status_code=503,
                    detail={"code": "MP_ERROR_TRANSIENT", "detail": str(exc.detail)},
                )
            raise HTTPException(
                status_code=422,
                detail={"code": "MP_ERROR", "detail": str(exc.detail)},
            )

        external_reference = pago_mp.get("external_reference")
        if not external_reference:
            raise ValueError("external_reference ausente en el pago de MP")

        # Verificar campos financieros
        valido, motivo = await self._verificar_pago_mp(pago_mp, external_reference)
        if not valido:
            # Discrepancia financiera: registrar incidencia sin crear turno
            try:
                intento = await self.session.get(IntentoSena, UUID(external_reference))
            except (ValueError, TypeError):
                raise ValueError("external_reference invalido")
            if intento is None:
                raise ValueError("intento no encontrado para el pago")
            await self._registrar_pago_mp(intento, pago_mp, resultado="incidencia")
            intento.estado = "requiere_revision"
            await self.session.flush()
            return {
                "aplicado": False,
                "motivo": motivo or "discrepancia_financiera",
                "incidencia": True,
                "payment_id": payment_id,
            }

        # Buscar intento
        try:
            intento = await self.session.get(IntentoSena, UUID(external_reference))
        except (ValueError, TypeError):
            raise ValueError("external_reference invalido")
        if intento is None:
            raise ValueError("intento no encontrado para el pago")

        estado_proveedor = str(pago_mp.get("status", "pending"))

        if estado_proveedor == "approved":
            try:
                return await self._aplicar_aprobado_atomico(intento, pago_mp)
            except IntegrityError:
                # Carrera real: otro webhook ya reservó el hueco. Registrar incidencia.
                await self.session.rollback()
                try:
                    intento_fresh = await self.session.get(IntentoSena, intento.id)
                except (ValueError, TypeError):  # nosec B101 - solo control de flujo tras rollback
                    intento_fresh = None
                if intento_fresh is not None:
                    return await self._registrar_incidencia_sin_cupo(intento_fresh, pago_mp)
                return {
                    "aplicado": False,
                    "motivo": "conflicto_concurrente",
                    "payment_id": payment_id,
                }
        elif estado_proveedor == "rejected":
            return await self._rechazar_intento(intento, pago_mp)
        else:
            # pending / in_process / cancelled / etc. -> no aplicar todavía
            await self._registrar_pago_mp(intento, pago_mp, resultado="pendiente")
            await self.session.flush()
            return {
                "aplicado": False,
                "motivo": f"pago_{estado_proveedor}_en_proveedor",
                "payment_id": payment_id,
            }

    # ------------------------------------------------------------------
    # Reconciliador de webhooks perdidos (C-09, tarea 6.1)
    # ------------------------------------------------------------------

    async def reconciliar_intento_pendiente(self, intento_id: UUID) -> dict[str, Any]:
        """Reconcila un intento pendiente consultando MP y aplicando si corresponde.
        Mismo camino idempotente que el webhook, sin generar segundo checkout."""
        intento = await self.session.get(IntentoSena, intento_id)
        if intento is None:
            raise ValueError("Intento inexistente")
        if intento.estado not in ("pendiente", "creando_checkout"):
            return {
                "aplicado": False,
                "motivo": f"intento_estado_{intento.estado}",
                "payment_id": None,
            }

        # Buscar PagoMP existente para este intento
        pago_stmt = select(PagoMP).where(PagoMP.intento_id == intento.id)
        pago_existente = (await self.session.scalars(pago_stmt)).first()

        if pago_existente is not None:
            # Ya hay un pago registrado; consultar MP para confirmar estado
            try:
                await self.mp_adapter.obtener_pago(
                    settings.mp_access_token, pago_existente.payment_id
                )
            except MPAdapterError:
                return {
                    "aplicado": False,
                    "motivo": "mp_no_disponible",
                    "payment_id": pago_existente.payment_id,
                }
            # Re-aplicar usando la logica del webhook (idempotente)
            return await self.aplicar_pago_webhook(
                pago_existente.payment_id,
                {
                    "type": "payment",
                    "data": {"id": pago_existente.payment_id},
                },
            )

        # No hay pago registrado: intentar descubrir payment_id via MP?
        # Sin external_reference valida no podemos consultar MP; dejar pendiente.
        return {
            "aplicado": False,
            "motivo": "sin_pago_registrado",
            "payment_id": None,
        }
