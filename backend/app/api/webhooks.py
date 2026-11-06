"""Webhook WhatsApp (C-08)."""

from __future__ import annotations

import hashlib
import hmac
import json

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.config import settings
from app.db import redis as redis_client
from app.services.gestion_turnos_service import GestionTurnosService
from app.services.recordatorio_wa_service import RecordatorioWAService

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
