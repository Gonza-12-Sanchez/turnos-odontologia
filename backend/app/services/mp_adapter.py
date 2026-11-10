"""Adaptador HTTP asincronico a Mercado Pago Checkout Pro (C-09).

Host fijo, timeouts acotados, nunca float para montos. El cliente HTTP se puede
inyectar para tests con transporte mock (sin llamadas de pago reales).
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import httpx

MP_HOST = "https://api.mercadopago.com"


class MPAdapterError(Exception):
    def __init__(self, status_code: int, detail: Any, code: str | None = None):
        super().__init__(str(detail))
        self.status_code = status_code
        self.detail = detail
        self.code = code


class MPAdapter:
    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        if client is None:
            client = httpx.AsyncClient(
                base_url=MP_HOST,
                timeout=httpx.Timeout(connect=2.0, read=5.0, write=5.0, pool=5.0),
            )
        self._client = client
        self._owns_client = client is None

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def crear_preferencia(
        self,
        access_token: str,
        external_reference: str,
        monto_centavos: int,
        notification_url: str,
        back_urls: dict[str, str],
    ) -> dict[str, Any]:
        """Crea una preferencia de checkout. Nunca usa float para el monto."""
        unit_price = Decimal(monto_centavos) / Decimal(100)
        payload: dict[str, Any] = {
            "external_reference": external_reference,
            "items": [
                {
                    "title": "Sena de reserva",
                    "quantity": 1,
                    "currency_id": "ARS",
                    # Serializacion decimal exacta: se envia como string para
                    # evitar float; MP acepta numerico o string segun documentacion.
                    "unit_price": str(unit_price),
                }
            ],
            "notification_url": notification_url,
            "back_urls": back_urls,
            "auto_return": "approved",
        }
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "X-Idempotency-Key": external_reference,
        }
        try:
            resp = await self._client.post("/checkout/preferences", json=payload, headers=headers)
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            raise MPAdapterError(
                503,
                {"code": "CHECKOUT_NO_VERIFICADO", "detail": str(exc)},
                code="CHECKOUT_NO_VERIFICADO",
            ) from exc

        if resp.status_code >= 400:
            raise MPAdapterError(
                resp.status_code,
                {"code": "MP_ERROR", "detail": resp.text[:200]},
                code="MP_ERROR",
            )
        return resp.json()

    async def obtener_pago(self, access_token: str, payment_id: str) -> dict[str, Any]:
        """Consulta el estado de un pago en MP (verificacion propia del servidor)."""
        try:
            resp = await self._client.get(
                f"/v1/payments/{payment_id}",
                headers={"Authorization": f"Bearer {access_token}"},
            )
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            raise MPAdapterError(
                503, {"code": "MP_ERROR", "detail": str(exc)}, code="MP_ERROR"
            ) from exc

        if resp.status_code >= 400:
            raise MPAdapterError(
                resp.status_code,
                {"code": "MP_ERROR", "detail": resp.text[:200]},
                code="MP_ERROR",
            )
        return resp.json()
