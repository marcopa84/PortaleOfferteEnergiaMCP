"""Avvisa il modello (e l'utente) quando su GitHub c'e una versione piu recente.

Le installazioni con uvx da git rileggono il repository a ogni avvio del server, quindi per
aggiornare basta riavviare completamente il client MCP. Qui si confronta il commit in uso
con l'ultimo pubblicato.
"""

from __future__ import annotations

import json
import os
import time
from importlib import metadata

import httpx
from pydantic import BaseModel

from . import __version__

REPO = os.environ.get("PORTALE_OFFERTE_REPO", "marcopa84/PortaleOfferteEnergiaMCP")
CACHE_SECONDI = 3600

COME_AGGIORNARE = (
    "Chiudere completamente il client MCP e riaprirlo (Claude Desktop: ⌘Q su macOS o icona nell'area di "
    "notifica → Esci su Windows; chiudere la finestra non basta). uvx scarica l'ultima versione all'avvio."
)


class InfoAggiornamento(BaseModel):
    versione_installata: str
    commit_installato: str | None
    ultimo_commit: str | None
    aggiornamento_disponibile: bool | None
    messaggio: str


_cache: tuple[float, InfoAggiornamento] | None = None


def commit_installato() -> str | None:
    """Commit registrato da pip/uv nelle installazioni da git (None per installazioni locali)."""
    try:
        grezzo = metadata.distribution("portale-offerte-mcp").read_text("direct_url.json")
    except metadata.PackageNotFoundError:
        return None
    if not grezzo:
        return None
    return (json.loads(grezzo).get("vcs_info") or {}).get("commit_id")


async def ultimo_commit(client: httpx.AsyncClient | None = None) -> str:
    url = f"https://api.github.com/repos/{REPO}/commits/HEAD"
    intestazioni = {"Accept": "application/vnd.github.sha", "User-Agent": "portale-offerte-mcp"}
    if client:
        risposta = await client.get(url, headers=intestazioni)
    else:
        async with httpx.AsyncClient(timeout=5) as c:
            risposta = await c.get(url, headers=intestazioni)
    risposta.raise_for_status()
    return risposta.text.strip()


async def controlla(client: httpx.AsyncClient | None = None, forza: bool = False) -> InfoAggiornamento:
    global _cache
    if _cache and not forza and _cache[0] > time.monotonic():
        return _cache[1]

    mio = commit_installato()
    if os.environ.get("PORTALE_OFFERTE_UPDATE_CHECK", "1") == "0":
        info = InfoAggiornamento(
            versione_installata=__version__, commit_installato=mio, ultimo_commit=None,
            aggiornamento_disponibile=None, messaggio="Controllo disattivato (PORTALE_OFFERTE_UPDATE_CHECK=0).",
        )
    elif not mio:
        info = InfoAggiornamento(
            versione_installata=__version__, commit_installato=None, ultimo_commit=None,
            aggiornamento_disponibile=None,
            messaggio="Non installato da git (installazione locale o di sviluppo): nulla da confrontare.",
        )
    else:
        try:
            ultimo = await ultimo_commit(client)
        except httpx.HTTPError as errore:
            info = InfoAggiornamento(
                versione_installata=__version__, commit_installato=mio, ultimo_commit=None,
                aggiornamento_disponibile=None, messaggio=f"Impossibile controllare GitHub: {errore}",
            )
        else:
            nuovo = ultimo != mio
            info = InfoAggiornamento(
                versione_installata=__version__,
                commit_installato=mio[:7],
                ultimo_commit=ultimo[:7],
                aggiornamento_disponibile=nuovo,
                messaggio=("E disponibile una versione piu recente. " + COME_AGGIORNARE) if nuovo else "Aggiornato.",
            )
    _cache = (time.monotonic() + CACHE_SECONDI, info)
    return info
