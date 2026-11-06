"""Abstracción de proveedor WhatsApp (C-08)."""

from __future__ import annotations

import hashlib
import uuid
from typing import Protocol

import httpx

from app.core.config import settings
from app.models import Turno


class WhatsAppProvider(Protocol):
    async def send_template(self, turno: Turno, plantilla: str) -> str:
        """Envía la plantilla y devuelve message_id."""
        ...


class MockProvider:
    """Proveedor mock para tests y etapa 6 (sin costo)."""

    async def send_template(self, turno: Turno, plantilla: str) -> str:
        # message_id determinista basado en turno + plantilla
        seed = f"{turno.id}:{plantilla}"
        return "mock-" + hashlib.sha256(seed.encode()).hexdigest()[:16]


class MetaCloudProvider:
    """Proveedor real contra Meta Cloud API (httpx async)."""

    def __init__(self, api_key: str, phone_number_id: str = "") -> None:
        self.api_key = api_key
        self.phone_number_id = phone_number_id
        self.base_url = "https://graph.facebook.com/v18.0"

    async def send_template(self, turno: Turno, plantilla: str) -> str:
        if not self.api_key:
            raise RuntimeError("WHATSAPP_API_KEY no configurada")
        # Payload mínimo; el número del paciente se asume disponible en turno.paciente.telefono
        payload = {
            "messaging_product": "whatsapp",
            "to": getattr(getattr(turno, "paciente", None), "telefono", ""),
            "type": "template",
            "template": {"name": plantilla, "language": {"code": "es_AR"}},
        }
        url = f"{self.base_url}/{self.phone_number_id}/messages"
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                url,
                json=payload,
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("messages", [{}])[0].get("id", str(uuid.uuid4()))


def get_whatsapp_provider() -> WhatsAppProvider:
    provider = (settings.whatsapp_provider or "").lower().strip()
    if provider in ("", "mock"):
        return MockProvider()
    if provider == "meta":
        return MetaCloudProvider(
            api_key=settings.whatsapp_api_key,
            phone_number_id=getattr(settings, "whatsapp_phone_number_id", ""),
        )
    # fallback mock para valores desconocidos
    return MockProvider()
