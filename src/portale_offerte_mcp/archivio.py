"""Archivio in memoria delle offerte di una giornata, con ricerca e risoluzione dei comuni."""

from __future__ import annotations

import datetime as dt
import gzip
import time
import unicodedata

from . import codici as C
from . import lettura, sorgenti

# Ogni quanto ricontrollare se sul portale ci sono dati nuovi.
INTERVALLO_CONTROLLO = 30 * 60


def normalizza(testo: str) -> str:
    """Minuscolo, senza accenti e spazi doppi, per confronti tolleranti."""
    senza_accenti = unicodedata.normalize("NFKD", testo).encode("ascii", "ignore").decode()
    return " ".join(senza_accenti.lower().replace("'", " ").replace("-", " ").split())


class ErroreRicerca(ValueError):
    pass


class Archivio:
    def __init__(self) -> None:
        self.giornata: sorgenti.Giornata | None = None
        self._ultimo_controllo = 0.0
        self.offerte: list[dict] = []
        # Lo stesso codice offerta puo essere usato da venditori diversi.
        self.per_codice: dict[str, list[dict]] = {}
        self.venditori: dict[str, str] = {}
        self.parametri: dict[str, dict] = {}
        self.prezzi_storici: list[dict] = []
        self.unita_indici: dict[str, str] = {}
        self.comuni: list[dict] = []
        self._comuni_per_codice: dict[str, dict] = {}
        self._province_regione: dict[str, str] = {}

    # ---------------------------------------------------------------- caricamento

    def assicura(self, forza: bool = False) -> None:
        """Carica i dati se mancano e, al massimo ogni 30 minuti, controlla se ce ne sono di nuovi."""
        adesso = time.monotonic()
        if not forza and self.giornata and adesso - self._ultimo_controllo < INTERVALLO_CONTROLLO:
            return
        giornata = sorgenti.aggiorna(forza=forza)
        self._ultimo_controllo = adesso
        if forza or self.giornata is None or giornata.data != self.giornata.data:
            self._carica(giornata)

    def _carica(self, giornata: sorgenti.Giornata) -> None:
        offerte: list[dict] = []
        for nome in ("offerte_luce_ml", "offerte_gas_ml", "offerte_dual_ml"):
            with giornata.apri(nome) as file:
                offerte.extend(lettura.leggi_offerte_mercato_libero(file))
        for nome, commodity in (("offerte_luce_placet", "luce"), ("offerte_gas_placet", "gas")):
            with giornata.apri(nome) as file:
                offerte.extend(lettura.leggi_offerte_placet(file, commodity))

        # Il portale pubblica a volte righe identiche: si tiene una sola copia.
        uniche: dict[str, dict] = {}
        for offerta in offerte:
            uniche.setdefault(repr(offerta), offerta)
        offerte = list(uniche.values())

        venditori = {o["piva"]: o["venditore"] for o in offerte if o["venditore"]}
        for offerta in offerte:
            if not offerta["venditore"]:
                offerta["venditore"] = venditori.get(offerta["piva"])

        parametri: dict[str, dict] = {}
        for nome in ("parametri_luce", "parametri_gas"):
            with giornata.apri(nome) as file:
                parametri[nome.removeprefix("parametri_")] = lettura.leggi_parametri(file)

        prezzi, unita = [], {}
        percorso_prezzi = sorgenti.file_prezzi_storici()
        if percorso_prezzi:
            with gzip.open(percorso_prezzi, "rb") as file:
                prezzi, unita = lettura.leggi_prezzi_storici(file)

        comuni = []
        percorso_comuni = sorgenti.file_comuni()
        if percorso_comuni:
            with gzip.open(percorso_comuni, "rb") as file:
                comuni = lettura.leggi_comuni(file)

        self.giornata = giornata
        self.offerte = offerte
        self.per_codice = {}
        for offerta in offerte:
            self.per_codice.setdefault(offerta["codice"].upper(), []).append(offerta)
        self.venditori = venditori
        self.parametri = parametri
        self.prezzi_storici, self.unita_indici = prezzi, unita
        self.comuni = comuni
        self._comuni_per_codice = {c["codice"]: c for c in comuni}
        self._province_regione = {c["provincia"]: c["regione"] for c in comuni}

    # ---------------------------------------------------------------- territorio

    def risolvi_comune(self, comune: str) -> dict:
        """Trova un comune per codice ISTAT, nome o "Nome (SIGLA)"."""
        valore = comune.strip()
        if valore.isdigit():
            codice = valore.zfill(6)
            if codice in self._comuni_per_codice:
                return self._comuni_per_codice[codice]
            if not self.comuni:
                # Senza elenco ISTAT si usa il codice cosi com'e.
                return {"codice": codice, "nome": codice, "provincia": codice[:3], "regione": None, "sigla": ""}
            raise ErroreRicerca(f"Codice ISTAT {valore} non trovato.")
        if not self.comuni:
            raise ErroreRicerca("Elenco ISTAT dei comuni non disponibile: indicare il codice ISTAT a 6 cifre.")

        sigla = None
        if valore.endswith(")") and "(" in valore:
            valore, _, sigla = valore[:-1].rpartition("(")
            sigla = sigla.strip().upper()
        cercato = normalizza(valore)
        trovati = [c for c in self.comuni if normalizza(c["nome"]) == cercato]
        if sigla:
            trovati = [c for c in trovati if c["sigla"] == sigla]
        if len(trovati) == 1:
            return trovati[0]
        if len(trovati) > 1:
            opzioni = ", ".join(f"{c['nome']} ({c['sigla']})" for c in trovati)
            raise ErroreRicerca(f"Piu comuni con questo nome: {opzioni}. Specificare la sigla della provincia.")
        simili = [c for c in self.comuni if cercato in normalizza(c["nome"])][:8]
        suggerimento = f" Forse: {', '.join(c['nome'] + ' (' + c['sigla'] + ')' for c in simili)}." if simili else ""
        raise ErroreRicerca(f"Comune '{comune}' non trovato.{suggerimento}")

    def risolvi_regione(self, regione: str) -> str:
        valore = regione.strip()
        if valore.isdigit() and valore.zfill(2) in C.REGIONI:
            return valore.zfill(2)
        cercato = normalizza(valore)
        for codice, nome in C.REGIONI.items():
            if normalizza(nome) == cercato or normalizza(nome).startswith(cercato):
                return codice
        raise ErroreRicerca(f"Regione '{regione}' non riconosciuta. Valori ammessi: {', '.join(C.REGIONI.values())}.")

    def regione_di_provincia(self, provincia: str) -> str | None:
        return self._province_regione.get(provincia.zfill(3))

    @staticmethod
    def nazionale(offerta: dict) -> bool:
        zone = offerta.get("zone") or {}
        return not (zone.get("regioni") or zone.get("province") or zone.get("comuni"))

    def disponibile_nel_comune(self, offerta: dict, comune: dict) -> bool:
        if self.nazionale(offerta):
            return True
        zone = offerta["zone"]
        return (
            comune["codice"] in zone["comuni"]
            or comune["provincia"] in (p.zfill(3) for p in zone["province"])
            or (comune.get("regione") is not None and comune["regione"] in (r.zfill(2) for r in zone["regioni"]))
        )

    def disponibile_in_regione(self, offerta: dict, regione: str) -> bool:
        """Vero se l'offerta e disponibile almeno in parte della regione."""
        if self.nazionale(offerta):
            return True
        zone = offerta["zone"]
        if regione in (r.zfill(2) for r in zone["regioni"]):
            return True
        if any(self.regione_di_provincia(p) == regione for p in zone["province"]):
            return True
        return any(self.regione_di_provincia(c[:3]) == regione for c in zone["comuni"])

    def descrivi_zone(self, offerta: dict) -> str:
        if self.nazionale(offerta):
            return "tutta Italia"
        zone = offerta["zone"]
        parti = []
        if zone["regioni"]:
            parti.append("regioni: " + ", ".join(C.REGIONI.get(r.zfill(2), r) for r in zone["regioni"]))
        if zone["province"]:
            parti.append(f"{len(zone['province'])} province")
        if zone["comuni"]:
            parti.append(f"{len(zone['comuni'])} comuni")
        return "; ".join(parti)

    # ---------------------------------------------------------------- indici

    def valori_indici(self, riferimento: str = "ultimo_mese") -> tuple[dict[str, float], str]:
        """Valori degli indici da usare nelle stime e descrizione del periodo usato."""
        if not self.prezzi_storici:
            return {}, "prezzi storici non disponibili"
        indici = [k for k in self.prezzi_storici[0] if k != "mese"]
        # Un indice che non viene piu pubblicato (es. Pfor fermo al 2022) non va usato come valore attuale.
        ultimo = self.prezzi_storici[-1]["mese"]
        anno, mese = int(ultimo[:4]), int(ultimo[5:])
        soglia = f"{anno - (mese <= 3)}-{(mese - 4) % 12 + 1:02d}"

        def recenti(indice: str) -> list[dict]:
            righe = [r for r in self.prezzi_storici if r.get(indice) is not None]
            return righe if righe and righe[-1]["mese"] >= soglia else []

        if riferimento == "media_12_mesi":
            valori, periodi = {}, set()
            for indice in indici:
                ultimi = recenti(indice)[-12:]
                if ultimi:
                    valori[indice] = sum(r[indice] for r in ultimi) / len(ultimi)
                    periodi.add(f"{ultimi[0]['mese']}..{ultimi[-1]['mese']}")
            return valori, "media 12 mesi " + ", ".join(sorted(periodi))
        valori, mesi = {}, set()
        for indice in indici:
            ultimi = recenti(indice)
            if ultimi:
                valori[indice] = ultimi[-1][indice]
                mesi.add(ultimi[-1]["mese"])
        return valori, "mese " + ", ".join(sorted(mesi))

    # ---------------------------------------------------------------- ricerca

    def cerca(
        self,
        commodity: str | None = None,
        tipo_cliente: str | None = None,
        tipo_prezzo: str | None = None,
        fonte: str | None = None,
        comune: str | None = None,
        regione: str | None = None,
        venditore: str | None = None,
        testo: str | None = None,
        residente: bool | None = None,
        consumo_annuo: float | None = None,
        potenza_kw: float | None = None,
        solo_valide_oggi: bool = True,
    ) -> tuple[list[dict], dict | None]:
        """Filtra le offerte. Restituisce (offerte, comune risolto o None)."""
        comune_info = self.risolvi_comune(comune) if comune else None
        codice_regione = self.risolvi_regione(regione) if regione else None
        cerca_venditore = normalizza(venditore) if venditore else None
        cerca_testo = normalizza(testo) if testo else None
        adesso = dt.datetime.now().isoformat()

        risultati = []
        for o in self.offerte:
            if commodity and o["commodity"] != commodity:
                continue
            if tipo_cliente and o["tipo_cliente"] != tipo_cliente:
                continue
            if tipo_prezzo and o["tipo_prezzo"] != tipo_prezzo:
                continue
            if fonte and o["fonte"] != fonte:
                continue
            if solo_valide_oggi and not ((o["data_inizio"] or "") <= adesso <= (o["data_fine"] or "9999")):
                continue
            if (
                residente is not None
                and o.get("residenza") not in (None, "tutti")
                and o["residenza"] != ("residente" if residente else "non residente")
            ):
                continue
            if consumo_annuo is not None:
                if o.get("consumo_min") is not None and consumo_annuo < o["consumo_min"]:
                    continue
                if o.get("consumo_max") is not None and consumo_annuo > o["consumo_max"]:
                    continue
            if potenza_kw is not None:
                if o.get("potenza_min") is not None and potenza_kw < o["potenza_min"]:
                    continue
                if o.get("potenza_max") is not None and potenza_kw > o["potenza_max"]:
                    continue
            if cerca_venditore and not (
                cerca_venditore == o["piva"]
                or cerca_venditore in normalizza(o["venditore"] or "")
                or cerca_venditore in normalizza(o["contatti"].get("sito") or "")
            ):
                continue
            if cerca_testo and cerca_testo not in normalizza(f"{o['nome']} {o.get('descrizione') or ''}"):
                continue
            if comune_info and not self.disponibile_nel_comune(o, comune_info):
                continue
            if codice_regione and not self.disponibile_in_regione(o, codice_regione):
                continue
            risultati.append(o)
        return risultati, comune_info
