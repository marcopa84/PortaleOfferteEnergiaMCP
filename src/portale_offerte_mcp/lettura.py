"""Lettura dei file open data nel modello comune di offerta (dizionari serializzabili in JSON).

Nel modello i campi descrittivi sono gia decodificati in testo, mentre i campi che servono
per i calcoli (fasce, macroaree, unita di misura, indici) mantengono il codice originale.
"""

from __future__ import annotations

import csv
import datetime as dt
import io
import xml.etree.ElementTree as ET
from typing import IO

from . import codici as C

NS = "{http://www.acquirenteunico.it/schemas/SII_AU/OffertaRetail/01}"


def _testo(elemento: ET.Element | None, percorso: str) -> str | None:
    if elemento is None:
        return None
    trovato = elemento.find(NS + percorso.replace("/", "/" + NS))
    if trovato is None or trovato.text is None:
        return None
    return trovato.text.strip()


def _tutti(elemento: ET.Element, percorso: str) -> list[ET.Element]:
    return elemento.findall(NS + percorso.replace("/", "/" + NS))


def _testi(elemento: ET.Element, percorso: str) -> list[str]:
    return [e.text.strip() for e in _tutti(elemento, percorso) if e.text and e.text.strip()]


def _numero(valore: str | None) -> float | None:
    if valore is None or valore == "":
        return None
    return float(valore.replace(",", "."))


def _intero(valore: str | None) -> int | None:
    numero = _numero(valore)
    return None if numero is None else int(numero)


def _data_ml(valore: str | None) -> str | None:
    """'13/10/2026_17:27:02' -> '2026-10-13T17:27:02'."""
    if not valore:
        return None
    return dt.datetime.strptime(valore, "%d/%m/%Y_%H:%M:%S").isoformat()


def _data_placet(valore: str | None, fine: bool) -> str | None:
    if not valore:
        return None
    giorno = dt.datetime.strptime(valore, "%d/%m/%Y")
    if fine:
        giorno = giorno.replace(hour=23, minute=59, second=59)
    return giorno.isoformat()


def _periodo(elemento: ET.Element | None) -> dict | None:
    if elemento is None:
        return None
    periodo = {
        "durata_mesi": _intero(_testo(elemento, "DURATA")),
        "valido_fino": _testo(elemento, "VALIDO_FINO"),
        "mesi": [C.decodifica(C.MESI, m) for m in _testi(elemento, "MESE_VALIDITA")],
    }
    return {k: v for k, v in periodo.items() if v}


def leggi_offerte_mercato_libero(sorgente: IO[bytes]) -> list[dict]:
    radice = ET.parse(sorgente).getroot()
    return [_offerta_ml(o) for o in radice.iter(NS + "offerta")]


def _offerta_ml(o: ET.Element) -> dict:
    dettaglio = o.find(NS + "DettaglioOfferta")
    tipo_offerta = _testo(dettaglio, "TIPO_OFFERTA")

    componenti = []
    for comp in _tutti(o, "ComponenteImpresa"):
        prezzi = []
        for intervallo in _tutti(comp, "IntervalloPrezzi"):
            prezzo = {
                "fascia": _testo(intervallo, "FASCIA_COMPONENTE"),
                "prezzo": _numero(_testo(intervallo, "PREZZO")),
                "unita": _testo(intervallo, "UNITA_MISURA"),
                "consumo_da": _intero(_testo(intervallo, "CONSUMO_DA")),
                "consumo_a": _intero(_testo(intervallo, "CONSUMO_A")),
                "tipo_prezzo": C.decodifica(C.TIPO_PREZZO, _testo(intervallo, "TIPO_PREZZO")),
                "periodo": _periodo(intervallo.find(NS + "PeriodoValidita")),
            }
            prezzi.append({k: v for k, v in prezzo.items() if v is not None})
        componenti.append({
            "nome": _testo(comp, "NOME"),
            "descrizione": _testo(comp, "DESCRIZIONE"),
            "tipologia": _testo(comp, "TIPOLOGIA"),
            "macroarea": _testo(comp, "MACROAREA"),
            "prezzi": prezzi,
        })

    sconti = []
    for sconto in _tutti(o, "Sconto"):
        sconti.append({
            "nome": _testo(sconto, "NOME"),
            "descrizione": _testo(sconto, "DESCRIZIONE"),
            "applicato_a": _testi(sconto, "CODICE_COMPONENTE_FASCIA"),
            "validita": _testo(sconto, "VALIDITA"),
            "iva": C.decodifica(C.IVA_SCONTO, _testo(sconto, "IVA_SCONTO")),
            "periodo": _periodo(sconto.find(NS + "PeriodoValidita")),
            "condizioni": [
                {
                    "codice": _testo(c, "CONDIZIONE_APPLICAZIONE"),
                    "descrizione": _testo(c, "DESCRIZIONE_CONDIZIONE"),
                }
                for c in _tutti(sconto, "Condizione")
            ],
            "prezzi": [
                {
                    "tipologia": _testo(p, "TIPOLOGIA"),
                    "valido_da": _intero(_testo(p, "VALIDO_DA")),
                    "valido_fino": _intero(_testo(p, "VALIDO_FINO")),
                    "unita": _testo(p, "UNITA_MISURA"),
                    "prezzo": _numero(_testo(p, "PREZZO")),
                }
                for p in _tutti(sconto, "PrezziSconto")
            ],
        })

    return {
        "codice": _testo(o, "IdentificativiOfferta/COD_OFFERTA"),
        "fonte": "mercato libero",
        "piva": _testo(o, "IdentificativiOfferta/PIVA_UTENTE"),
        "venditore": None,
        "commodity": C.decodifica(C.TIPO_MERCATO, _testo(dettaglio, "TIPO_MERCATO")),
        "nome": _testo(dettaglio, "NOME_OFFERTA"),
        "descrizione": _testo(dettaglio, "DESCRIZIONE"),
        "tipo_cliente": C.decodifica(C.TIPO_CLIENTE, _testo(dettaglio, "TIPO_CLIENTE")),
        "residenza": C.decodifica(C.DOMESTICO_RESIDENTE, _testo(dettaglio, "DOMESTICO_RESIDENTE")),
        "tipo_prezzo": C.decodifica(C.TIPO_OFFERTA, tipo_offerta),
        "onnicomprensiva": C.decodifica(C.OFFERTA_ONNICOMPRENSIVA, _testo(dettaglio, "OFFERTA_ONNICOMPRENSIVA")),
        "consumo_canone": _intero(_testo(dettaglio, "CONSUMO_CANONE")),
        "sottoscrivibile_singolarmente": _testo(dettaglio, "OFFERTA_SINGOLA") != "NO",
        "valida_per": [C.decodifica(C.TIPOLOGIA_ATT_CONTR, c) for c in _testi(dettaglio, "TIPOLOGIA_ATT_CONTR")],
        "durata_mesi": _intero(_testo(dettaglio, "DURATA")),
        "garanzie": _testo(dettaglio, "GARANZIE"),
        "attivazione": [C.decodifica(C.MODALITA_ATTIVAZIONE, c) for c in _testi(dettaglio, "ModalitaAttivazione/MODALITA")],
        "attivazione_note": _testo(dettaglio, "ModalitaAttivazione/DESCRIZIONE"),
        "contatti": {
            "telefono": _testo(dettaglio, "Contatti/TELEFONO"),
            "sito": _testo(dettaglio, "Contatti/URL_SITO_VENDITORE"),
            "pagina_offerta": _testo(dettaglio, "Contatti/URL_OFFERTA"),
        },
        "indici": [
            {
                "codice": _testo(r, "IDX_PREZZO_ENERGIA"),
                "coefficiente": _numero(_testo(r, "COEFFICIENTE")),
                "fascia": _testo(r, "FASCIA_PREZZO"),
                "altro": _testo(r, "ALTRO"),
            }
            for r in _tutti(o, "RiferimentiPrezzoEnergia")
        ],
        "data_inizio": _data_ml(_testo(o, "ValiditaOfferta/DATA_INIZIO")),
        "data_fine": _data_ml(_testo(o, "ValiditaOfferta/DATA_FINE")),
        "consumo_min": _intero(_testo(o, "CaratteristicheOfferta/CONSUMO_MIN")),
        "consumo_max": _intero(_testo(o, "CaratteristicheOfferta/CONSUMO_MAX")),
        "potenza_min": _numero(_testo(o, "CaratteristicheOfferta/POTENZA_MIN")),
        "potenza_max": _numero(_testo(o, "CaratteristicheOfferta/POTENZA_MAX")),
        "offerte_congiunte": {
            "luce": _testi(o, "OffertaDual/OFFERTE_CONGIUNTE_EE"),
            "gas": _testi(o, "OffertaDual/OFFERTE_CONGIUNTE_GAS"),
        },
        "pagamenti": [
            C.decodifica(C.MODALITA_PAGAMENTO, _testo(m, "MODALITA_PAGAMENTO"))
            if _testo(m, "MODALITA_PAGAMENTO") != "99" or not _testo(m, "DESCRIZIONE")
            else f"altro: {_testo(m, 'DESCRIZIONE')}"
            for m in _tutti(o, "MetodoPagamento")
        ],
        "componenti_regolate": _testi(o, "ComponentiRegolate/CODICE"),
        "tipologia_fasce": _testo(o, "TipoPrezzo/TIPOLOGIA_FASCE"),
        "dispacciamento": [
            {
                "tipo": _testo(d, "TIPO_DISPACCIAMENTO"),
                "valore": _numero(_testo(d, "VALORE_DISP")),
                "nome": _testo(d, "NOME"),
                "descrizione": _testo(d, "DESCRIZIONE"),
            }
            for d in _tutti(o, "Dispacciamento")
        ],
        "componenti": componenti,
        "condizioni": [
            {
                "tipologia": C.decodifica(C.TIPOLOGIA_CONDIZIONE, _testo(c, "TIPOLOGIA_CONDIZIONE")),
                "altro": _testo(c, "ALTRO"),
                "descrizione": _testo(c, "DESCRIZIONE"),
                "limitante": _testo(c, "LIMITANTE") == "01",
            }
            for c in _tutti(o, "CondizioniContrattuali")
        ],
        "zone": {
            "regioni": _testi(o, "ZoneOfferta/REGIONE"),
            "province": _testi(o, "ZoneOfferta/PROVINCIA"),
            "comuni": _testi(o, "ZoneOfferta/COMUNE"),
        },
        "sconti": sconti,
        "servizi_aggiuntivi": [
            {
                "nome": _testo(s, "NOME"),
                "dettaglio": _testo(s, "DETTAGLIO"),
                "categoria": C.decodifica(C.MACROAREA_SERVIZI, _testo(s, "MACROAREA")),
                "categoria_note": _testo(s, "DETTAGLI_MACROAREA"),
            }
            for s in _tutti(o, "ProdottiServiziAggiuntivi")
        ],
    }


def leggi_offerte_placet(sorgente: IO[bytes], commodity: str) -> list[dict]:
    """Legge il CSV delle offerte PLACET ('luce' o 'gas')."""
    righe = csv.DictReader(io.TextIOWrapper(sorgente, encoding="utf-8-sig"))
    return [_offerta_placet(r, commodity) for r in righe]


def _lista(valore: str | None) -> list[str]:
    return [v.strip() for v in (valore or "").split(";") if v.strip()]


def _offerta_placet(r: dict, commodity: str) -> dict:
    fisso = r["tipo_offerta"] == "prezzo fisso"
    if commodity == "luce":
        prezzi_energia = {
            "F1": _numero(r.get("p_vol_f1")),
            "F2": _numero(r.get("p_vol_f2")),
            "F3": _numero(r.get("p_vol_f3")),
            "F1_biorario": _numero(r.get("p_vol_bf1")),
            "F23": _numero(r.get("p_vol_bf23")),
            "monorario": _numero(r.get("p_vol_mono")),
        }
    else:
        prezzi_energia = {"gas": _numero(r.get("p_vol"))}
    return {
        "codice": r["cod_offerta"],
        "fonte": "PLACET",
        "piva": r["p_iva"],
        "venditore": r["denominazione"],
        "commodity": commodity,
        "nome": r["nome_offerta"],
        "descrizione": None,
        "tipo_cliente": "domestico" if r["tipo_cliente"] == "domestico" else "altri usi",
        "residenza": None,
        "tipo_prezzo": "fisso" if fisso else "variabile",
        "durata_mesi": 12,
        "attivazione": _lista(r["modalita_attivazione"]),
        "contatti": {
            "telefono": r["telefono"] or None,
            "sito": r["url_sito_venditore"] or None,
            "pagina_offerta": r["url_offerta"] or None,
        },
        "indici": [] if fisso else [{"codice": "01" if commodity == "luce" else "03", "coefficiente": None, "fascia": None, "altro": None}],
        "data_inizio": _data_placet(r["data_inizio"], fine=False),
        "data_fine": _data_placet(r["data_fine"], fine=True),
        "pagamenti": _lista(r["modalita_pagamento"]),
        "zone": {
            "regioni": _lista(r.get("regione")),
            "province": _lista(r.get("provincia")),
            "comuni": _lista(r.get("comune")),
        },
        "placet": {
            "quota_fissa_anno": _numero(r["p_fix_f"] if fisso else r["p_fix_v"]),
            "prezzi_energia": {k: v for k, v in prezzi_energia.items() if v is not None},
            "spread_alpha": _numero(r.get("alpha")),
        },
    }


def leggi_parametri(sorgente: IO[bytes]) -> dict[str, dict]:
    righe = csv.DictReader(io.TextIOWrapper(sorgente, encoding="utf-8-sig"))
    return {
        r["nome_parametro"]: {"valore": _numero(r["valore"]), "descrizione": (r["descrizione"] or "").strip()}
        for r in righe
    }


def leggi_prezzi_storici(sorgente: IO[bytes]) -> tuple[list[dict], dict[str, str]]:
    """Legge il CSV dei prezzi storici degli indici (cp1252, ';', virgola decimale).

    Restituisce (righe mensili, {indice: unita di misura}).
    """
    righe = csv.reader(io.TextIOWrapper(sorgente, encoding="cp1252"), delimiter=";")
    intestazione = next(righe)
    indici, unita = [], {}
    for colonna in intestazione[1:]:
        nome, _, resto = colonna.partition(" (")
        indici.append(nome.strip())
        unita[nome.strip()] = resto.rstrip(")").strip()
    mesi = []
    for riga in righe:
        if not riga or not riga[0].strip():
            continue
        mese = riga[0].strip()
        voce = {"mese": f"{mese[:4]}-{mese[4:6]}"}
        for nome, valore in zip(indici, riga[1:]):
            voce[nome] = _numero(valore.strip())
        mesi.append(voce)
    return mesi, unita


def leggi_comuni(sorgente: IO[bytes]) -> list[dict]:
    """Legge l'elenco ISTAT dei comuni (latin-1, ';')."""
    righe = csv.reader(io.TextIOWrapper(sorgente, encoding="latin-1"), delimiter=";")
    intestazione = [" ".join(c.split()) for c in next(righe)]

    def colonna(prefisso: str) -> int:
        return next(i for i, nome in enumerate(intestazione) if nome.startswith(prefisso))

    i_codice = colonna("Codice Comune formato alfanumerico")
    i_nome = colonna("Denominazione in italiano")
    i_regione = colonna("Codice Regione")
    i_nome_regione = colonna("Denominazione Regione")
    i_sigla = colonna("Sigla automobilistica")
    comuni = []
    for riga in righe:
        if len(riga) <= max(i_codice, i_nome, i_regione, i_sigla):
            continue
        codice = riga[i_codice].strip()
        comuni.append({
            "codice": codice,
            "nome": riga[i_nome].strip(),
            "provincia": codice[:3],
            "sigla": riga[i_sigla].strip(),
            "regione": riga[i_regione].strip().zfill(2),
            "nome_regione": riga[i_nome_regione].strip(),
        })
    return comuni
