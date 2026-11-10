"""C-09: adaptador MP (tarea 4.1). Transporte mock, sin llamadas de pago reales."""

import json

import httpx
import pytest

from app.services.mp_adapter import MPAdapter, MPAdapterError


def _capture_transport():
    capturas = {}

    def handler(request: httpx.Request) -> httpx.Response:
        capturas["url"] = str(request.url)
        capturas["method"] = request.method
        capturas["headers"] = dict(request.headers)
        capturas["body"] = json.loads(request.content) if request.content else None
        return httpx.Response(200, json={"id": "pref_capturada", "status": "pending"})

    return httpx.MockTransport(handler), capturas


@pytest.mark.asyncio
async def test_mp_crear_preferencia_centavos_exactos():
    transport, capturas = _capture_transport()
    client = httpx.AsyncClient(transport=transport, base_url="https://api.mercadopago.com")
    adapter = MPAdapter(client=client)
    try:
        resultado = await adapter.crear_preferencia(
            access_token="tok_123",
            external_reference="intento_abc",
            monto_centavos=15000,
            notification_url="https://example.com/webhooks/mercadopago",
            back_urls={"success": "s", "failure": "f", "pending": "p"},
        )
        assert resultado["id"] == "pref_capturada"
        body = capturas["body"]
        assert body["external_reference"] == "intento_abc"
        assert body["items"][0]["title"] == "Sena de reserva"
        assert body["items"][0]["quantity"] == 1
        assert body["items"][0]["currency_id"] == "ARS"
        # 15000 centavos -> "150" como string decimal exacto, nunca float
        assert body["items"][0]["unit_price"] == "150"
        assert isinstance(body["items"][0]["unit_price"], str)
        assert capturas["headers"]["authorization"] == "Bearer tok_123"
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_mp_crear_preferencia_monto_no_redondo():
    transport, capturas = _capture_transport()
    client = httpx.AsyncClient(transport=transport, base_url="https://api.mercadopago.com")
    adapter = MPAdapter(client=client)
    try:
        await adapter.crear_preferencia(
            access_token="tok_123",
            external_reference="intento_xyz",
            monto_centavos=12345,
            notification_url="https://example.com/webhooks/mercadopago",
            back_urls={},
        )
        body = capturas["body"]
        # 12345 centavos -> "123.45" exacto, sin float
        assert body["items"][0]["unit_price"] == "123.45"
        assert isinstance(body["items"][0]["unit_price"], str)
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_mp_error_400_lanza_excepcion():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"message": "invalido", "cause": ["campo"]})

    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport, base_url="https://api.mercadopago.com")
    adapter = MPAdapter(client=client)
    try:
        with pytest.raises(MPAdapterError) as exc:
            await adapter.crear_preferencia(
                access_token="tok",
                external_reference="ref",
                monto_centavos=1000,
                notification_url="https://example.com/hook",
                back_urls={},
            )
        assert exc.value.status_code == 400
        assert exc.value.code == "MP_ERROR"
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_mp_timeout_lanza_503():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("timeout de conexion")

    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport, base_url="https://api.mercadopago.com")
    adapter = MPAdapter(client=client)
    try:
        with pytest.raises(MPAdapterError) as exc:
            await adapter.crear_preferencia(
                access_token="tok",
                external_reference="ref",
                monto_centavos=1000,
                notification_url="https://example.com/hook",
                back_urls={},
            )
        assert exc.value.status_code == 503
        assert exc.value.code == "CHECKOUT_NO_VERIFICADO"
    finally:
        await client.aclose()
