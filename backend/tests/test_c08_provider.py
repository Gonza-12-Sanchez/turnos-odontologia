import pytest

from app.core.config import settings
from app.services.whatsapp_provider import MockProvider, get_whatsapp_provider


@pytest.mark.asyncio
async def test_mock_provider_returns_deterministic_message_id():
    # build a minimal turno-like object
    class T:
        id = "11111111-2222-3333-4444-555555555555"
        paciente = None

    p = MockProvider()
    mid1 = await p.send_template(T(), "recordatorio_turno")
    mid2 = await p.send_template(T(), "recordatorio_turno")
    assert mid1 == mid2
    assert mid1.startswith("mock-")


def test_selector_respects_env(monkeypatch):
    monkeypatch.setattr(settings, "whatsapp_provider", "")
    assert isinstance(get_whatsapp_provider(), MockProvider)
    monkeypatch.setattr(settings, "whatsapp_provider", "mock")
    assert isinstance(get_whatsapp_provider(), MockProvider)
