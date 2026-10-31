"""Scaricamento e cache locale degli open data del Portale Offerte.

I file vengono pubblicati ogni giorno nella pagina Open Data. Ogni giornata viene salvata
compressa in una cartella AAAAMMGG, cosi la cache accumula anche lo storico, che sul
portale resta disponibile solo per pochi giorni.
"""

from __future__ import annotations

import datetime as dt
import gzip
import os
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path

import httpx

from . import __version__

BASE = "https://www.ilportaleofferte.it"
PAGINA_OPEN_DATA = f"{BASE}/portaleOfferte/it/open-data.page"
URL_COMUNI_ISTAT = "https://www.istat.it/storage/codici-unita-amministrative/Elenco-comuni-italiani.csv"
# Identifica il client verso il portale, con un riferimento al progetto.
USER_AGENT = f"portale-offerte-mcp/{__version__} (+https://github.com/marcopa84/PortaleOfferteEnergiaMCP)"

# Nome logico -> espressione regolare sul nome del file pubblicato.
FILE_GIORNALIERI = {
    "offerte_luce_placet": r"PO_Offerte_E_PLACET_(\d{8})\.csv",
    "offerte_gas_placet": r"PO_Offerte_G_PLACET_(\d{8})\.csv",
    "parametri_luce": r"PO_Parametri_E_(\d{8})\.csv",
    "parametri_gas": r"PO_Parametri_G_(\d{8})\.csv",
    "offerte_luce_ml": r"PO_Offerte_E_MLIBERO_(\d{8})\.xml",
    "offerte_gas_ml": r"PO_Offerte_G_MLIBERO_(\d{8})\.xml",
    "offerte_dual_ml": r"PO_Offerte_D_MLIBERO_(\d{8})\.xml",
}


def cartella_cache() -> Path:
    percorso = os.environ.get("PORTALE_OFFERTE_CACHE")
    if percorso:
        return Path(percorso).expanduser()
    return Path.home() / ".cache" / "portale-offerte-mcp"


def giorni_storico() -> int:
    """Giorni di storico da conservare (0 = senza limite)."""
    return int(os.environ.get("PORTALE_OFFERTE_GIORNI_STORICO", "365"))


@dataclass
class Giornata:
    """I file di una giornata di pubblicazione presenti in cache."""

    data: dt.date
    cartella: Path
    file: dict[str, Path] = field(default_factory=dict)

    def apri(self, nome: str):
        """Apre un file della giornata in modalita binaria (decomprimendolo)."""
        return gzip.open(self.file[nome], "rb")


class ErroreDati(RuntimeError):
    pass


def _client() -> httpx.Client:
    return httpx.Client(
        headers={"User-Agent": USER_AGENT},
        timeout=httpx.Timeout(30, read=180),
        follow_redirects=True,
    )


def _scarica_compresso(client: httpx.Client, url: str, destinazione: Path) -> None:
    temporaneo = destinazione.with_suffix(destinazione.suffix + ".part")
    with client.stream("GET", url) as risposta:
        risposta.raise_for_status()
        with gzip.open(temporaneo, "wb") as uscita:
            for blocco in risposta.iter_bytes():
                uscita.write(blocco)
    temporaneo.replace(destinazione)


def link_open_data(html: str) -> tuple[dict[str, tuple[str, str]], str | None]:
    """Estrae dalla pagina Open Data i link dei file giornalieri e del CSV dei prezzi storici.

    Restituisce ({nome logico: (url, AAAAMMGG)}, url prezzi storici).
    """
    giornalieri: dict[str, tuple[str, str]] = {}
    prezzi_storici = None
    for href in re.findall(r'href="([^"]+)"', html):
        url = href if href.startswith("http") else BASE + href
        nome_file = href.rsplit("/", 1)[-1]
        for nome, schema in FILE_GIORNALIERI.items():
            corrispondenza = re.fullmatch(schema, nome_file)
            if corrispondenza:
                giornalieri[nome] = (url, corrispondenza.group(1))
        if prezzi_storici is None and "/cms/documents/" in href and href.endswith(".csv"):
            prezzi_storici = url
    return giornalieri, prezzi_storici


def giornate_in_cache() -> list[Giornata]:
    """Giornate complete presenti in cache, dalla piu recente."""
    radice = cartella_cache() / "giornaliero"
    giornate = []
    if radice.is_dir():
        for cartella in radice.iterdir():
            if not re.fullmatch(r"\d{8}", cartella.name):
                continue
            file = {n: cartella / f"{n}.gz" for n in FILE_GIORNALIERI if (cartella / f"{n}.gz").exists()}
            if len(file) == len(FILE_GIORNALIERI):
                data = dt.datetime.strptime(cartella.name, "%Y%m%d").date()
                giornate.append(Giornata(data, cartella, file))
    return sorted(giornate, key=lambda g: g.data, reverse=True)


def _pulisci_storico() -> None:
    limite = giorni_storico()
    if limite <= 0:
        return
    soglia = dt.date.today() - dt.timedelta(days=limite)
    for giornata in giornate_in_cache():
        if giornata.data < soglia:
            shutil.rmtree(giornata.cartella, ignore_errors=True)


def aggiorna(forza: bool = False) -> Giornata:
    """Garantisce in cache i dati piu recenti e restituisce la giornata da usare.

    Se la cache contiene gia i dati di oggi non scarica nulla (salvo forza=True).
    Se il portale non e raggiungibile usa l'ultima giornata in cache.
    """
    giornate = giornate_in_cache()
    if giornate and giornate[0].data >= dt.date.today() and not forza:
        return giornate[0]

    try:
        with _client() as client:
            pagina = client.get(PAGINA_OPEN_DATA)
            pagina.raise_for_status()
            giornalieri, url_prezzi = link_open_data(pagina.text)
            mancanti = set(FILE_GIORNALIERI) - set(giornalieri)
            if mancanti:
                raise ErroreDati(f"La pagina Open Data non contiene i file: {', '.join(sorted(mancanti))}")

            data_pubblicazione = max(data for _, data in giornalieri.values())
            cartella = cartella_cache() / "giornaliero" / data_pubblicazione
            cartella.mkdir(parents=True, exist_ok=True)
            for nome, (url, _) in giornalieri.items():
                destinazione = cartella / f"{nome}.gz"
                if forza or not destinazione.exists():
                    _scarica_compresso(client, url, destinazione)

            if url_prezzi:
                _scarica_compresso(client, url_prezzi, cartella_cache() / "prezzi_storici.csv.gz")
            _aggiorna_comuni(client)
    except (httpx.HTTPError, ErroreDati) as errore:
        if giornate:
            return giornate[0]
        raise ErroreDati(f"Impossibile scaricare gli open data e nessun dato in cache: {errore}") from errore

    _pulisci_storico()
    giornate = giornate_in_cache()
    if not giornate:
        raise ErroreDati("Scaricamento completato ma la giornata in cache e incompleta")
    return giornate[0]


def _aggiorna_comuni(client: httpx.Client) -> None:
    """Scarica l'elenco ISTAT dei comuni se manca o ha piu di 30 giorni."""
    destinazione = cartella_cache() / "comuni_istat.csv.gz"
    if destinazione.exists():
        eta = dt.datetime.now().timestamp() - destinazione.stat().st_mtime
        if eta < 30 * 86400:
            return
    try:
        _scarica_compresso(client, URL_COMUNI_ISTAT, destinazione)
    except httpx.HTTPError:
        # L'elenco serve solo per cercare i comuni per nome: se manca si usano i codici ISTAT.
        pass


def file_prezzi_storici() -> Path | None:
    percorso = cartella_cache() / "prezzi_storici.csv.gz"
    return percorso if percorso.exists() else None


def file_comuni() -> Path | None:
    percorso = cartella_cache() / "comuni_istat.csv.gz"
    return percorso if percorso.exists() else None
