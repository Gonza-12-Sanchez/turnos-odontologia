"""Webhooks WhatsApp (C-08) y Mercado Pago (C-09)."""

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_role
from app.core.config import settings
from app.db import redis as redis_client
from app.models import IntentoSena, PagoMP, Usuario
from app.schemas.sena import (
    IncidenciaListOut,
    IncidenciaOut,
    ResolucionIncidenciaIn,
)
from app.services.gestion_turnos_service import GestionTurnosService
from app.services.recordatorio_wa_service import RecordatorioWAService
from app.services.sena_service import SenaService

router = APIRouter(tags=["webhooks"])


def _verify_signature(raw_body: bytes, signature: str | None) -> None:
    secret = settings.whatsapp_webhook_secret or settings.whatsapp_api_key
    if not secret:
        if (settings.whatsapp_provider or "").lower() in ("", "mock"):
            return
        raise HTTPException(status_code=503, detail="Webhook secret no configurado")
    if not signature:
        raise HTTPException(status_code=401, detail="Firma ausente")
    expected = "sha256=" + hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(status_code=401, detail="Firma inválida")


async def _idempotent(message_id: str) -> bool:
    try:
        redis = redis_client.get_redis()
        key = f"wa:webhook:msg:{message_id}"
        was_set = await redis.set(key, "1", nx=True, ex=86400)
        if not was_set:
            return True
    except Exception:  # noqa: BLE001, S110
        pass
    return False


@router.post("/whatsapp")
async def whatsapp_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_hub_signature_256: str | None = Header(default=None, alias="X-Hub-Signature-256"),
):
    raw = await request.body()
    _verify_signature(raw, x_hub_signature_256)

    try:
        data = json.loads(raw.decode("utf-8")) if raw else {}
    except json.JSONDecodeError:
        raise HTTPException(status_code=422, detail="JSON inválido")

    message_id = data.get("message_id")
    respuesta = data.get("respuesta")
    if not message_id or respuesta not in ("confirmo", "cancelo"):
        raise HTTPException(status_code=422, detail="Payload inválido")

    if await _idempotent(message_id):
        return {"status": "duplicate"}

    svc_rec = RecordatorioWAService(db)
    rec = await svc_rec.get_by_message_id(message_id)

    if rec is not None and rec.respuesta is not None:
        return {"status": "duplicate"}

    turno_id = rec.turno_id if rec is not None else data.get("turno_id")
    if turno_id is None:
        raise HTTPException(status_code=404, detail="Turno no encontrado")

    gsvc = GestionTurnosService(db)
    rejected = False
    try:
        if respuesta == "confirmo":
            await gsvc.confirmar(turno_id, actor=None, origin="whatsapp")
        else:
            await gsvc.cancelar(turno_id, actor=None, origin="whatsapp")
    except HTTPException as exc:
        if respuesta == "cancelo" and exc.status_code == 422:
            rejected = True
        else:
            raise

    # register response
    if rec is None:
        await svc_rec.registrar_respuesta(message_id, respuesta, turno_id=turno_id)
    else:
        rec.respuesta = respuesta
        rec.estado = "respondido"
        await db.flush()

    await db.commit()

    if rejected:
        raise HTTPException(status_code=422, detail="Llamar al consultorio para cancelar")

    return {"status": "ok"}


# --- Webhook Mercado Pago (C-09) ---

def _verificar_firma_mp(raw_body: bytes, x_signature: str | None) -> None:
    """Valida firma HMAC-SHA256 de Mercado Pago en tiempo constante."""
    if not settings.mp_webhook_secret:
        raise HTTPException(status_code=503, detail="Webhook secret de MP no configurado")
    if not x_signature:
        raise HTTPException(status_code=401, detail="Firma de MP ausente")
    try:
        partes: dict[str, str] = {}
        for parte in x_signature.split(";"):
            k, _, v = parte.partition("=")
            partes[k.strip()] = v.strip()
        timestamp_str = partes["ts"]
        _ = partes["v1"]  # v1 es la firma; se valida abajo con compare_digest
        timestamp = int(timestamp_str)
    except (KeyError, ValueError, AttributeError):
        raise HTTPException(status_code=401, detail="Formato de firma de MP invalido")
    ahora = int(datetime.now(UTC).timestamp())
    if abs(ahora - timestamp) > 300:
        raise HTTPException(status_code=401, detail="Firma de MP expirada")
    mensaje = f"ts={timestamp}.".encode() + raw_body
    esperado = "ts=" + timestamp_str + ";v1=" + hmac.new(
        settings.mp_webhook_secret.encode("utf-8"), mensaje, hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(esperado, x_signature):
        raise HTTPException(status_code=401, detail="Firma de MP invalida")


@router.post("/mercadopago")
async def mercadopago_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_signature: str | None = Header(default=None, alias="x-signature"),
    x_request_id: str | None = Header(default=None, alias="x-request-id"),
):
    """Webhook de Mercado Pago: valida firma, consulta el pago y lo aplica atomicamente."""
    raw = await request.body()
    _verificar_firma_mp(raw, x_signature)

    try:
        data = json.loads(raw.decode("utf-8")) if raw else {}
    except json.JSONDecodeError:
        raise HTTPException(status_code=422, detail="JSON invalido")

    if data.get("type") != "payment":
        raise HTTPException(status_code=422, detail="Tipo de evento no soportado")

    payment_id = str(data.get("data", {}).get("id") or "")
    if not payment_id:
        raise HTTPException(status_code=422, detail="payment_id ausente")

    service = SenaService(db)
    try:
        resultado = await service.aplicar_pago_webhook(payment_id, data)
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=422, detail=str(exc))
    except HTTPException:
        await db.rollback()
        raise
    await db.commit()
    return resultado


# --- Incidencias de seña MP (C-09, tarea 6.3) ---

@router.get("/pagos/incidencias", response_model=IncidenciaListOut)
async def listar_incidencias(
    page: int = 1,
    page_size: int = 20,
    user: Annotated[Usuario, Depends(require_role("secretaria"))] = None,
    db: AsyncSession = Depends(get_db),
):
    """Lista paginada de incidencias requiere_revision (solo secretaria)."""
    page = max(page, 1)
    if page_size < 1 or page_size > 100:
        page_size = 20
    offset = (page - 1) * page_size

    stmt = (
        select(IntentoSena)
        .where(IntentoSena.estado == "requiere_revision")
        .order_by(IntentoSena.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    rows = (await db.scalars(stmt)).all()

    # Contar total
    count_stmt = select(IntentoSena).where(IntentoSena.estado == "requiere_revision")
    total = len((await db.scalars(count_stmt)).all())

    # Enriquecer con datos de PagoMP
    items: list[IncidenciaOut] = []
    for intento in rows:
        pago = None
        if intento.turno_id is None:
            pago_stmt = select(PagoMP).where(PagoMP.intento_id == intento.id)
            pago = (await db.scalars(pago_stmt)).first()
        items.append(
            IncidenciaOut(
                intento_id=intento.id,
                estado=intento.estado,
                monto_centavos=intento.monto_centavos,
                moneda=intento.moneda,
                expires_at=intento.expires_at,
                turno_id=intento.turno_id,
                payment_id=pago.payment_id if pago else None,
                resultado=pago.resultado if pago else None,
            )
        )

    return IncidenciaListOut(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.patch("/pagos/sena/{intento_id}/resolucion")
async def resolver_incidencia(
    intento_id: UUID,
    payload: ResolucionIncidenciaIn,
    user: Annotated[Usuario, Depends(require_role("secretaria"))] = None,
    db: AsyncSession = Depends(get_db),
):
    """Registra resolucion operacional de una incidencia (solo secretaria).
    No ejecuta reembolso automático ni crea turno."""
    intento = await db.get(IntentoSena, intento_id)
    if intento is None:
        raise HTTPException(status_code=404, detail="Intento inexistente")
    if intento.estado != "requiere_revision":
        raise HTTPException(
            status_code=422,
            detail={"code": "INTENTO_NO_REQUIERE_REVISION", "estado": intento.estado},
        )

    # Auditoria de la resolucion operacional
    from app.models import AuditoriaCobro

    db.add(
        AuditoriaCobro(
            actor_id=user.id,
            accion="resolver_incidencia",
            intento_id=intento.id,
            centavos=intento.monto_centavos,
            motivo=f"Resolucion: {payload.resolucion}. {payload.motivo}",
            fecha=datetime.now(UTC),
        )
    )
    # Mantener estado requiere_revision para trazabilidad; la resolucion es operacional externa
    await db.commit()
    return {
        "intento_id": str(intento_id),
        "resolucion": payload.resolucion,
        "motivo": payload.motivo,
        "referencia_operacion": payload.referencia_operacion,
        "estado": intento.estado,
    }
