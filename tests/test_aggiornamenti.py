import httpx
import pytest

from portale_offerte_mcp import aggiornamenti


@pytest.fixture(autouse=True)
def senza_cache(monkeypatch):
    monkeypatch.setattr(aggiornamenti, "_cache", None)


def client_github(sha: str) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(lambda richiesta: httpx.Response(200, text=sha)))


async def test_aggiornamento_disponibile(monkeypatch):
    monkeypatch.setattr(aggiornamenti, "commit_installato", lambda: "a" * 40)
    async with client_github("b" * 40) as client:
        info = await aggiornamenti.controlla(client)
    assert info.aggiornamento_disponibile is True
    assert info.ultimo_commit == "bbbbbbb"


async def test_gia_aggiornato(monkeypatch):
    monkeypatch.setattr(aggiornamenti, "commit_installato", lambda: "a" * 40)
    async with client_github("a" * 40) as client:
        info = await aggiornamenti.controlla(client)
    assert info.aggiornamento_disponibile is False


async def test_installazione_locale(monkeypatch):
    monkeypatch.setattr(aggiornamenti, "commit_installato", lambda: None)
    info = await aggiornamenti.controlla()
    assert info.aggiornamento_disponibile is None


async def test_controllo_disattivato(monkeypatch):
    monkeypatch.setenv("PORTALE_OFFERTE_UPDATE_CHECK", "0")
    info = await aggiornamenti.controlla()
    assert "disattivato" in info.messaggio
