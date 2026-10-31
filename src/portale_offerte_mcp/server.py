"""Server MCP per gli open data del Portale Offerte luce e gas (ARERA / Acquirente Unico)."""

from __future__ import annotations

from typing import Annotated, Literal

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import Field

from . import __version__, aggiornamenti, costi, sorgenti
from . import codici as C
from .archivio import Archivio, ErroreRicerca, compatta, normalizza

ISTRUZIONI = """\
Dati delle offerte di luce e gas per il mercato italiano, dagli open data del Portale Offerte
(www.ilportaleofferte.it, gestito da Acquirente Unico per ARERA), aggiornati ogni giorno.
Comprende le offerte del mercato libero e le offerte PLACET, per clienti domestici, altri usi
e condomini (gas).

Come usarlo:
- cerca_offerte trova le offerte per tipo, zona, venditore, prezzo fisso o variabile; se si
  indica il consumo annuo le ordina per costo stimato.
- dettaglio_offerta mostra prezzi, sconti, condizioni e zone di un'offerta.
- stima_costo confronta il costo annuo della parte vendita di una o piu offerte.
- indici_prezzi e parametri_regolati danno PUN, PSV e i corrispettivi regolati.

Avvertenze da riportare all'utente:
- Le stime riguardano solo la parte vendita (quanto cambia tra un'offerta e l'altra): non
  includono rete, oneri di sistema, imposte e IVA, quindi non sono la bolletta e non coincidono
  con la "spesa annua stimata" del Portale.
- Per le offerte variabili si usa il valore storico dell'indice, non le quotazioni forward.
- Prima di sottoscrivere, rimandare sempre alla pagina dell'offerta del venditore e al Portale:
  i dati sono forniti dai venditori e possono essere incompleti o non aggiornati.
- Non e una consulenza: presentare i risultati come informazioni da verificare, non come
  raccomandazione a scegliere un'offerta.
- Questo strumento non e affiliato ad ARERA, Acquirente Unico o al Portale Offerte.
- Citare la fonte come "Portale Offerte" (open data ARERA / Acquirente Unico).
- Una volta per conversazione, al primo uso di questi strumenti, chiamare anche
  controlla_aggiornamenti. Se aggiornamento_disponibile e true, dire all'utente in una frase che
  esiste una nuova versione e che si installa chiudendo e riaprendo l'app. Non richiamarlo dopo.
"""

mcp = MCPServer("portale-offerte", instructions=ISTRUZIONI, version=__version__)
# Tutti i tool leggono soltanto dati pubblici: nessun effetto collaterale.
SOLA_LETTURA = ToolAnnotations(readOnlyHint=True, openWorldHint=True)
archivio = Archivio()

Commodity = Literal["luce", "gas", "dual"]
TipoCliente = Literal["domestico", "altri usi", "condominio uso domestico"]
TipoPrezzo = Literal["fisso", "variabile", "flat", "mista"]
Fonte = Literal["mercato libero", "PLACET"]
RiferimentoIndici = Literal["ultimo_mese", "media_12_mesi"]


AVVERTENZA = (
    "Informazioni dagli open data del Portale Offerte, non una consulenza: prima di sottoscrivere "
    "verificare l'offerta sul Portale Offerte e sul sito del venditore."
)
ALTRO_RIFERIMENTO = {"ultimo_mese": "media_12_mesi", "media_12_mesi": "ultimo_mese"}


def _carica() -> None:
    try:
        archivio.assicura()
    except sorgenti.ErroreDati as errore:
        raise ToolError(str(errore)) from errore


def _fonte_dati() -> dict:
    giornata = archivio.giornata
    return {
        "fonte": "Portale Offerte - open data (ARERA / Acquirente Unico)",
        "data_pubblicazione": giornata.data.isoformat() if giornata else None,
    }


def _nome_venditore(offerta: dict) -> str:
    """Il nome viene dalle offerte PLACET: per chi non ne ha si mostra il sito del venditore."""
    if offerta["venditore"]:
        return offerta["venditore"]
    sito = offerta["contatti"].get("sito")
    return f"nome non disponibile (sito {sito})" if sito else "nome non disponibile"


def _sintesi(offerta: dict) -> dict:
    indici = [C.decodifica(C.INDICI, i["codice"]) for i in offerta.get("indici", [])]
    sintesi = {
        "codice": offerta["codice"],
        "nome": offerta["nome"],
        "venditore": _nome_venditore(offerta),
        "piva": offerta["piva"],
        "fonte": offerta["fonte"],
        "commodity": offerta["commodity"],
        "tipo_cliente": offerta["tipo_cliente"],
        "tipo_prezzo": offerta["tipo_prezzo"],
        "indice": ", ".join(dict.fromkeys(indici)) or None,
        "durata_mesi": "indeterminata" if offerta.get("durata_mesi") == -1 else offerta.get("durata_mesi"),
        "valida_fino_al": (offerta.get("data_fine") or "")[:10] or None,
        "zone": archivio.descrivi_zone(offerta),
        "pagina_offerta": offerta["contatti"].get("pagina_offerta") or offerta["contatti"].get("sito"),
    }
    if offerta["commodity"] == "dual":
        collegate = {k: v for k, v in (offerta.get("offerte_congiunte") or {}).items() if v}
        sintesi["offerte_collegate"] = collegate or None
    return {k: v for k, v in sintesi.items() if v is not None}


def _scaglione(da, a) -> str | None:
    if da is None and a is None:
        return None
    return f"da {da or 0} a {a if a is not None else 'oltre'}"


def _dettaglio(offerta: dict) -> dict:
    def unita(codice: str) -> str | None:
        return C.decodifica(C.UNITA_MISURA, codice)

    dettaglio = {
        **_sintesi(offerta),
        "descrizione": offerta.get("descrizione"),
        "residenza": offerta.get("residenza"),
        "onnicomprensiva": offerta.get("onnicomprensiva"),
        "consumo_canone": offerta.get("consumo_canone"),
        "sottoscrivibile_singolarmente": offerta.get("sottoscrivibile_singolarmente"),
        "valida_per": offerta.get("valida_per"),
        "valida_dal": (offerta.get("data_inizio") or "")[:10] or None,
        "garanzie": offerta.get("garanzie"),
        "attivazione": offerta.get("attivazione"),
        "attivazione_note": offerta.get("attivazione_note"),
        "pagamenti": offerta.get("pagamenti"),
        "contatti": offerta["contatti"],
        "limiti": {
            k: offerta.get(k)
            for k in ("consumo_min", "consumo_max", "potenza_min", "potenza_max")
            if offerta.get(k) is not None
        } or None,
        "fasce": C.decodifica(C.TIPOLOGIA_FASCE, offerta.get("tipologia_fasce")),
        "indici": [
            {
                "indice": C.decodifica(C.INDICI, i["codice"]),
                "coefficiente": i.get("coefficiente"),
                "fascia": C.decodifica(C.FASCIA, i.get("fascia")),
                "descrizione": i.get("altro"),
            }
            for i in offerta.get("indici", [])
        ] or None,
        "componenti": [
            {
                "nome": comp["nome"],
                "descrizione": comp["descrizione"],
                "voce": C.decodifica(C.MACROAREA, comp["macroarea"]),
                "tipologia": C.decodifica(C.TIPOLOGIA_COMPONENTE, comp["tipologia"]),
                "prezzi": [
                    {
                        k: v
                        for k, v in {
                            "fascia": C.decodifica(C.FASCIA, p.get("fascia")),
                            "prezzo": f"{p['prezzo']:g} {unita(p['unita'])}",
                            "scaglione_consumo": _scaglione(p.get("consumo_da"), p.get("consumo_a")),
                            "tipo_prezzo": p.get("tipo_prezzo"),
                            "periodo": p.get("periodo"),
                        }.items()
                        if v
                    }
                    for p in comp["prezzi"]
                ],
            }
            for comp in offerta.get("componenti", [])
        ] or None,
        "componenti_regolate": [C.decodifica(C.COMPONENTI_REGOLATE, c) for c in offerta.get("componenti_regolate", [])] or None,
        "dispacciamento": [
            {
                k: v
                for k, v in {
                    "voce": C.decodifica(C.TIPO_DISPACCIAMENTO, d["tipo"]),
                    "nome": d["nome"],
                    "valore": f"{d['valore']:g} €/kWh" if d.get("valore") is not None else None,
                    "descrizione": d.get("descrizione"),
                }.items()
                if v
            }
            for d in offerta.get("dispacciamento", [])
        ] or None,
        "sconti": [
            {
                "nome": s["nome"],
                "descrizione": s["descrizione"],
                "applicato_a": [C.decodifica(C.COMPONENTE_FASCIA_SCONTO, a) for a in s["applicato_a"]] or None,
                "quando": C.decodifica(C.VALIDITA_SCONTO, s.get("validita")),
                "soggetto_iva": s.get("iva"),
                "periodo": s.get("periodo"),
                "condizioni": [
                    c["descrizione"] or C.decodifica(C.CONDIZIONE_SCONTO, c["codice"]) for c in s["condizioni"]
                ],
                "valori": [
                    {
                        k: v
                        for k, v in {
                            "tipo": C.decodifica(C.TIPOLOGIA_SCONTO, p["tipologia"]),
                            "valore": f"{p['prezzo']:g} {unita(p['unita'])}",
                            "scaglione_consumo": _scaglione(p.get("valido_da"), p.get("valido_fino")),
                        }.items()
                        if v
                    }
                    for p in s["prezzi"]
                ],
            }
            for s in offerta.get("sconti", [])
        ] or None,
        "condizioni_contrattuali": [
            {
                "tipo": c["altro"] or c["tipologia"],
                "descrizione": c["descrizione"],
                "limitante": c["limitante"],
            }
            for c in offerta.get("condizioni", [])
        ] or None,
        "servizi_aggiuntivi": offerta.get("servizi_aggiuntivi") or None,
        "offerte_congiunte": {k: v for k, v in (offerta.get("offerte_congiunte") or {}).items() if v} or None,
    }
    if offerta["fonte"] == "PLACET":
        placet = offerta["placet"]
        misura = "€/kWh" if offerta["commodity"] == "luce" else "€/Smc"
        dettaglio["prezzi_placet"] = {
            "quota_fissa": f"{placet['quota_fissa_anno']:g} €/anno" if placet.get("quota_fissa_anno") is not None else None,
            "prezzi_energia": {k: f"{v:g} {misura}" for k, v in placet["prezzi_energia"].items()} or None,
            "spread_alpha": f"{placet['spread_alpha']:g} {misura}" if placet.get("spread_alpha") is not None else None,
        }
    zone = offerta.get("zone") or {}
    if zone.get("comuni"):
        nomi = [archivio._comuni_per_codice.get(c, {}).get("nome", c) for c in zone["comuni"][:30]]
        dettaglio["comuni_esempio"] = nomi
    return {k: v for k, v in dettaglio.items() if v not in (None, "", [])}


def _offerte(codice: str, piva: str | None = None) -> list[dict]:
    """Offerte con un codice: di solito una, ma il portale contiene codici usati da piu venditori."""
    offerte = archivio.per_codice.get(codice.strip().upper(), [])
    if piva:
        offerte = [o for o in offerte if o["piva"] == piva.strip()]
    if not offerte:
        filtro = f" per la P.IVA {piva}" if piva else ""
        raise ToolError(f"Offerta {codice}{filtro} non trovata nei dati del {archivio.giornata.data.isoformat()}.")
    return offerte


def _ripartizione(f1, f2, f3) -> dict | None:
    if f1 is None and f2 is None and f3 is None:
        return None
    if None in (f1, f2, f3):
        raise ToolError("La ripartizione per fasce richiede tutti e tre i valori F1, F2, F3.")
    return {"F1": f1, "F2": f2, "F3": f3}


def _stima(offerta: dict, consumo: float, potenza: float, ripartizione, riferimento: str) -> dict:
    valori, descrizione = archivio.valori_indici(riferimento)
    parametri = archivio.parametri["luce" if offerta["commodity"] == "luce" else "gas"]
    stima = costi.stima(offerta, consumo, parametri, valori, descrizione, potenza, ripartizione)
    stima["venditore"] = _nome_venditore(offerta)
    return stima


def _indicizzata(offerta: dict) -> bool:
    return bool(offerta.get("indici"))


def _avviso_indici(commodity: str) -> str | None:
    """Avvisa quando l'ultimo mese dell'indice e lontano dalla media: le variabili cambiano molto di costo."""
    indice = "PUN" if commodity == "luce" else "PSV"
    ultimo, mese = archivio.valori_indici("ultimo_mese")
    media, _ = archivio.valori_indici("media_12_mesi")
    if indice not in ultimo or indice not in media or not media[indice]:
        return None
    scarto = ultimo[indice] / media[indice] - 1
    if abs(scarto) < 0.2:
        return None
    verso = "sopra" if scarto > 0 else "sotto"
    return (
        f"Il {indice} dell'ultimo mese ({ultimo[indice]:.4f}, {mese}) e il {abs(scarto):.0%} {verso} la media "
        f"degli ultimi 12 mesi ({media[indice]:.4f}): il costo stimato delle offerte variabili dipende molto "
        "dal riferimento scelto. Confrontare anche con riferimento_indici='media_12_mesi' (o 'ultimo_mese')."
    )


@mcp.tool(annotations=SOLA_LETTURA)
def cerca_offerte(
    commodity: Annotated[Commodity, Field(description="luce, gas o dual (luce+gas)")],
    tipo_cliente: Annotated[TipoCliente, Field(description="Tipo di cliente")] = "domestico",
    comune: Annotated[str | None, Field(description="Comune di fornitura: nome, 'Nome (SIGLA)' o codice ISTAT a 6 cifre")] = None,
    regione: Annotated[str | None, Field(description="Regione (nome), in alternativa al comune")] = None,
    tipo_prezzo: Annotated[TipoPrezzo | None, Field(description="Prezzo fisso, variabile (indicizzato), flat o misto")] = None,
    fonte: Annotated[Fonte | None, Field(description="Solo mercato libero o solo offerte PLACET")] = None,
    venditore: Annotated[str | None, Field(description="Parte del nome del venditore o partita IVA")] = None,
    testo: Annotated[str | None, Field(description="Testo da cercare nel nome o nella descrizione dell'offerta")] = None,
    residente: Annotated[bool | None, Field(description="Solo per domestici: cliente residente o no")] = None,
    consumo_annuo: Annotated[float | None, Field(description="Consumo annuo (kWh per la luce, Smc per il gas). Se indicato, esclude le offerte fuori dai limiti di consumo e ordina per costo stimato")] = None,
    potenza_kw: Annotated[float | None, Field(description="Potenza impegnata in kW (luce)")] = None,
    ordina_per: Annotated[Literal["costo_stimato", "nome", "venditore"] | None, Field(description="Ordinamento; predefinito costo_stimato se c'e il consumo, altrimenti venditore")] = None,
    riferimento_indici: Annotated[RiferimentoIndici, Field(description="Valore degli indici per le stime delle offerte variabili")] = "ultimo_mese",
    includi_non_ancora_valide: Annotated[bool, Field(description="Includere anche offerte con validita futura o scaduta")] = False,
    raggruppa_versioni: Annotated[bool, Field(description="Mostra una sola riga per le versioni della stessa offerta (stesso venditore e nome, es. edizioni mensili); le altre sono in altre_versioni")] = True,
    limite: Annotated[int, Field(ge=1, le=100)] = 20,
    salta: Annotated[int, Field(ge=0, description="Risultati da saltare (paginazione)")] = 0,
) -> dict:
    """Cerca offerte luce e gas del Portale Offerte filtrando per tipo, zona, venditore e prezzo.

    Con consumo_annuo le offerte sono ordinate per costo annuo stimato della sola parte vendita
    (esclusi rete, oneri, imposte): utile per confrontare, non e la bolletta.
    """
    _carica()
    try:
        offerte, comune_info = archivio.cerca(
            commodity=commodity,
            tipo_cliente=tipo_cliente,
            tipo_prezzo=tipo_prezzo,
            fonte=fonte,
            comune=comune,
            regione=regione,
            venditore=venditore,
            testo=testo,
            residente=residente,
            consumo_annuo=consumo_annuo,
            potenza_kw=potenza_kw,
            solo_valide_oggi=not includi_non_ancora_valide,
        )
    except ErroreRicerca as errore:
        raise ToolError(str(errore)) from errore

    ordinamento = ordina_per or ("costo_stimato" if consumo_annuo else "venditore")
    if ordinamento == "costo_stimato" and not consumo_annuo:
        raise ToolError("Per ordinare per costo stimato indicare consumo_annuo.")

    righe = []
    if consumo_annuo and commodity != "dual":
        for offerta in offerte:
            stima = _stima(offerta, consumo_annuo, potenza_kw or 3.0, None, riferimento_indici)
            riga = _sintesi(offerta)
            riga["costo_vendita_anno"] = stima["costo_vendita_anno"]
            riga["prezzo_medio"] = stima["prezzo_medio"]
            if not stima["stima_completa"]:
                riga["stima_incompleta"] = True
            righe.append(riga)
    else:
        righe = [_sintesi(o) for o in offerte]

    # A parita di ordinamento viene prima l'offerta valida piu a lungo: e quella che resta
    # in evidenza quando si raggruppano le versioni (gli ordinamenti successivi sono stabili).
    righe.sort(key=lambda r: r.get("valida_fino_al") or "", reverse=True)
    if ordinamento == "costo_stimato" and commodity != "dual":
        # Le stime incomplete vanno in fondo: il loro costo e sottostimato.
        righe.sort(key=lambda r: (r.get("stima_incompleta", False), r.get("costo_vendita_anno", 0)))
    elif ordinamento == "nome":
        righe.sort(key=lambda r: r["nome"].lower())
    else:
        righe.sort(key=lambda r: (r["venditore"].lower(), r["nome"].lower()))

    totale = len(righe)
    if raggruppa_versioni:
        righe = _raggruppa(righe)

    risposta = {
        **_fonte_dati(),
        "trovate": len(righe),
        "mostrate": f"{salta + 1}-{min(salta + limite, len(righe))}" if righe else "0",
        "risultati": righe[salta : salta + limite],
    }
    if len(righe) != totale:
        risposta["offerte_prima_del_raggruppamento"] = totale
    if comune_info:
        risposta["comune"] = f"{comune_info['nome']} ({comune_info.get('sigla', '')}) ISTAT {comune_info['codice']}"
    if consumo_annuo and commodity == "dual":
        risposta["nota_costi"] = (
            "Le offerte dual non hanno prezzi propri: il consumo e stato usato solo per escludere le offerte "
            "fuori dai limiti. Per il costo stimare con stima_costo le offerte luce e gas in offerte_collegate, "
            "separatamente (kWh per la luce, Smc per il gas)."
        )
    elif consumo_annuo:
        risposta["nota_costi"] = costi.esclusi(commodity)
        risposta["valori_indici"] = archivio.valori_indici(riferimento_indici)[1]
        if tipo_prezzo != "fisso" and (avviso := _avviso_indici(commodity)):
            risposta["avviso_indici"] = avviso
    if residente is not None:
        risposta["nota_residenza"] = (
            "Poche offerte indicano se sono riservate a residenti o non residenti: il filtro esclude solo "
            "quelle riservate esplicitamente all'altro caso."
        )
    if not righe and venditore:
        simili = archivio.suggerisci_venditori(venditore)
        risposta["suggerimento"] = (
            f"Nessuna offerta per il venditore '{venditore}'. "
            + (f"Venditori con nome o sito simile: {', '.join(simili)}. " if simili else "")
            + "Per l'elenco completo usare elenco_venditori."
        )
    risposta["avvertenza"] = AVVERTENZA
    return risposta


def _raggruppa(righe: list[dict]) -> list[dict]:
    """Una riga per offerta: le versioni con stesso venditore, nome e tipo finiscono in altre_versioni.

    Le righe sono gia ordinate, quindi resta la versione migliore secondo l'ordinamento scelto.
    """
    gruppi: dict[tuple, dict] = {}
    risultato = []
    for riga in righe:
        chiave = (riga["piva"], normalizza(riga["nome"]), riga["commodity"], riga["tipo_cliente"], riga["fonte"], riga["tipo_prezzo"])
        principale = gruppi.get(chiave)
        if principale is None:
            gruppi[chiave] = riga
            risultato.append(riga)
            continue
        versione = {"codice": riga["codice"], "valida_fino_al": riga.get("valida_fino_al")}
        if "costo_vendita_anno" in riga:
            versione["costo_vendita_anno"] = riga["costo_vendita_anno"]
        principale.setdefault("altre_versioni", []).append(versione)
    return risultato


@mcp.tool(annotations=SOLA_LETTURA)
def dettaglio_offerta(
    codice: Annotated[str, Field(description="Codice offerta restituito da cerca_offerte")],
    piva: Annotated[str | None, Field(description="Partita IVA del venditore, se lo stesso codice e usato da piu venditori")] = None,
) -> dict:
    """Mostra tutti i dettagli di un'offerta: prezzi per fascia, sconti, condizioni contrattuali, zone e contatti."""
    _carica()
    offerte = _offerte(codice, piva)
    if len(offerte) == 1:
        return {**_fonte_dati(), "offerta": _dettaglio(offerte[0]), "avvertenza": AVVERTENZA}
    return {
        **_fonte_dati(),
        "nota": "Nei dati del portale questo codice e usato da piu venditori: sono riportate tutte le offerte.",
        "offerte": [_dettaglio(o) for o in offerte],
        "avvertenza": AVVERTENZA,
    }


@mcp.tool(annotations=SOLA_LETTURA)
def stima_costo(
    codici: Annotated[list[str], Field(min_length=1, max_length=20, description="Uno o piu codici offerta luce, oppure uno o piu codici offerta gas (non insieme: i consumi hanno unita diverse). Le dual vanno stimate tramite le loro offerte luce e gas collegate. Un codice usato da piu venditori viene stimato per ciascuno")],
    consumo_annuo: Annotated[float, Field(gt=0, description="Consumo annuo: kWh per la luce, Smc per il gas")],
    potenza_kw: Annotated[float, Field(gt=0, description="Potenza impegnata in kW (luce)")] = 3.0,
    consumo_f1: Annotated[float | None, Field(ge=0, description="Quota o kWh in fascia F1 (con F2 e F3 sostituisce il profilo standard)")] = None,
    consumo_f2: Annotated[float | None, Field(ge=0)] = None,
    consumo_f3: Annotated[float | None, Field(ge=0)] = None,
    riferimento_indici: Annotated[RiferimentoIndici, Field(description="Valore degli indici per le offerte variabili")] = "ultimo_mese",
) -> dict:
    """Stima e confronta il costo annuo della parte vendita di una o piu offerte, con il dettaglio delle voci.

    Esclude rete, oneri di sistema, imposte e IVA (uguali per tutte le offerte a parita di cliente).
    Profilo standard per fasce: domestico F1 33%, F2 31%, F3 36%; altri usi 44%, 24%, 32%.
    """
    _carica()
    ripartizione = _ripartizione(consumo_f1, consumo_f2, consumo_f3)
    offerte = [offerta for codice in codici for offerta in _offerte(codice)]

    dual = [o for o in offerte if o["commodity"] == "dual"]
    if dual:
        dettagli = "; ".join(
            f"{o['codice']}: luce {', '.join(o['offerte_congiunte']['luce']) or 'non indicata'}, "
            f"gas {', '.join(o['offerte_congiunte']['gas']) or 'non indicata'}"
            for o in dual
        )
        raise ToolError(
            "Le offerte dual non hanno prezzi propri. Stimare separatamente le offerte collegate, "
            f"la luce con il consumo in kWh e il gas con il consumo in Smc. Offerte collegate: {dettagli}."
        )
    commodity = {o["commodity"] for o in offerte}
    if len(commodity) > 1:
        luce = [o["codice"] for o in offerte if o["commodity"] == "luce"]
        gas = [o["codice"] for o in offerte if o["commodity"] == "gas"]
        raise ToolError(
            "Non si possono stimare insieme offerte luce e gas: il consumo e in kWh per la luce e in Smc per il gas. "
            f"Fare due chiamate separate. Luce: {', '.join(luce)}. Gas: {', '.join(gas)}."
        )

    altro = ALTRO_RIFERIMENTO[riferimento_indici]
    stime = []
    for offerta in offerte:
        stima = _stima(offerta, consumo_annuo, potenza_kw, ripartizione, riferimento_indici)
        stima.pop("esclusi")
        if _indicizzata(offerta) or offerta.get("tipo_prezzo") == "variabile":
            alternativa = _stima(offerta, consumo_annuo, potenza_kw, ripartizione, altro)
            stima["con_altro_riferimento_indici"] = {
                "riferimento": archivio.valori_indici(altro)[1],
                "costo_vendita_anno": alternativa["costo_vendita_anno"],
            }
        stime.append(stima)
    stime.sort(key=lambda s: (not s["stima_completa"], s["costo_vendita_anno"]))
    risposta = {**_fonte_dati(), "esclusi": costi.esclusi(commodity.pop()), "stime": stime}
    if any(_indicizzata(o) for o in offerte) and (avviso := _avviso_indici(offerte[0]["commodity"])):
        risposta["avviso_indici"] = avviso
    risposta["avvertenza"] = AVVERTENZA
    return risposta


@mcp.tool(annotations=SOLA_LETTURA)
def elenco_venditori(
    commodity: Annotated[Commodity | None, Field(description="Solo venditori con offerte di questa commodity")] = None,
    testo: Annotated[str | None, Field(description="Parte del nome o partita IVA")] = None,
) -> dict:
    """Elenca i venditori presenti nel Portale Offerte con il numero di offerte attive per commodity."""
    _carica()
    venditori: dict[str, dict] = {}
    for offerta in archivio.offerte:
        voce = venditori.setdefault(offerta["piva"], {
            "piva": offerta["piva"],
            "nome": offerta["venditore"],
            "sito": offerta["contatti"].get("sito"),
            "offerte": {},
        })
        voce["offerte"][offerta["commodity"]] = voce["offerte"].get(offerta["commodity"], 0) + 1
    elenco = list(venditori.values())
    if commodity:
        elenco = [v for v in elenco if commodity in v["offerte"]]
    if testo:
        cercato = compatta(testo)
        elenco = [
            v for v in elenco
            if cercato == v["piva"] or cercato in compatta(v["nome"] or "") or cercato in compatta(v["sito"] or "")
        ]
    elenco.sort(key=lambda v: (v["nome"] or "~").lower())
    risposta = {
        **_fonte_dati(),
        "venditori": len(elenco),
        "nota": "Il nome e ricavato dalle offerte PLACET: per i venditori che non ne hanno restano partita IVA e sito.",
        "elenco": elenco,
    }
    if testo and not elenco:
        simili = archivio.suggerisci_venditori(testo)
        if simili:
            risposta["suggerimento"] = f"Nessun venditore trovato. Nomi o siti simili: {', '.join(simili)}."
    return risposta


@mcp.tool(annotations=SOLA_LETTURA)
def indici_prezzi(
    ultimi_mesi: Annotated[int, Field(ge=1, le=120)] = 12,
) -> dict:
    """Valori mensili storici degli indici all'ingrosso: PUN (luce), PSV, PE, CMEM, Pfor, Psbil (gas)."""
    _carica()
    return {
        **_fonte_dati(),
        "unita": archivio.unita_indici,
        "mesi": archivio.prezzi_storici[-ultimi_mesi:],
    }


@mcp.tool(annotations=SOLA_LETTURA)
def parametri_regolati(
    commodity: Annotated[Literal["luce", "gas"], Field(description="luce o gas")],
    cerca: Annotated[str | None, Field(description="Testo da cercare nel nome o nella descrizione del parametro")] = None,
) -> dict:
    """Corrispettivi regolati pubblicati con le offerte: oneri, trasporto, PCV, QVD, IVA, perdite di rete, accise luce."""
    _carica()
    parametri = archivio.parametri[commodity]
    if cerca:
        cercato = normalizza(cerca)
        parametri = {
            k: v for k, v in parametri.items() if cercato in normalizza(k) or cercato in normalizza(v["descrizione"])
        }
    risposta = {
        **_fonte_dati(),
        "parametri": parametri,
        "nota_unita": (
            "Il file ufficiale non riporta le unita di misura. In genere le quote energia sono in "
            + ("€/kWh" if commodity == "luce" else "€/Smc")
            + ", le quote fisse in €/anno, le quote potenza in €/kW/anno, IVA e perdite come frazioni (0.10 = 10%). "
            "Alcuni valori fanno eccezione (es. accise a importo fisso mensile): verificare sulle delibere ARERA."
        ),
    }
    if cerca and not parametri:
        risposta["nota"] = (
            f"Nessun parametro {commodity} corrisponde a '{cerca}'."
            + (" Le accise del gas non sono tra i parametri pubblicati negli open data." if commodity == "gas" and "accis" in normalizza(cerca) else "")
            + f" Parametri disponibili: {', '.join(sorted(archivio.parametri[commodity]))}."
        )
    return risposta


@mcp.tool(annotations=SOLA_LETTURA)
def stato_dati(
    aggiorna: Annotated[bool, Field(description="Forza un nuovo scaricamento dal portale")] = False,
) -> dict:
    """Data dei dati in uso, numero di offerte, cartella della cache e condizioni d'uso degli open data."""
    try:
        archivio.assicura(forza=aggiorna)
    except sorgenti.ErroreDati as errore:
        raise ToolError(str(errore)) from errore
    conteggi: dict[str, int] = {}
    for offerta in archivio.offerte:
        chiave = f"{offerta['commodity']} - {offerta['fonte']}"
        conteggi[chiave] = conteggi.get(chiave, 0) + 1
    return {
        **_fonte_dati(),
        "offerte": dict(sorted(conteggi.items())),
        "giornate_in_cache": [g.data.isoformat() for g in sorgenti.giornate_in_cache()],
        "cartella_cache": str(sorgenti.cartella_cache()),
        "prezzi_storici_fino_a": archivio.prezzi_storici[-1]["mese"] if archivio.prezzi_storici else None,
        "elenco_comuni_istat": bool(archivio.comuni),
        "condizioni_uso": (
            "Gli open data del Portale Offerte sono a uso libero citando la fonte 'Portale Offerte'. "
            "I marchi Portale Offerte, AU e ARERA non possono essere usati senza consenso."
        ),
    }


@mcp.tool(annotations=SOLA_LETTURA)
async def controlla_aggiornamenti() -> aggiornamenti.InfoAggiornamento:
    """Controlla se su GitHub c'e una versione piu recente di questo server (una volta per conversazione)."""
    return await aggiornamenti.controlla()
