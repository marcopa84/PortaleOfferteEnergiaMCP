"""Stima del costo annuo della parte "vendita" di un'offerta.

Non e la spesa annua stimata del Portale Offerte: si calcolano solo le voci che cambiano
da un'offerta all'altra (componenti del venditore, indice di prezzo per le variabili,
sconti non condizionati, componenti regolate scelte dal venditore). Rete, oneri generali
di sistema, imposte, IVA e dispacciamento regolato sono esclusi, perche a parita di
cliente sono uguali per tutte le offerte.

Approssimazioni rispetto alle "Regole per il calcolo della spesa annua stimata" del SII:
- per le offerte variabili si usa il valore storico dell'indice (ultimo mese o media
  12 mesi) e non le quotazioni forward dei 4 trimestri successivi, che non sono open data;
- il TTF non e tra i prezzi storici pubblicati, quindi le offerte indicizzate al TTF
  restano senza quota indice;
- Peak/OffPeak sono approssimati con F1 e F2+F3.
"""

from __future__ import annotations

from . import codici as C

PROFILO_DOMESTICO = {"F1": 0.33, "F2": 0.31, "F3": 0.36}
PROFILO_ALTRI_USI = {"F1": 0.44, "F2": 0.24, "F3": 0.32}



def esclusi(commodity: str) -> str:
    """Cosa non e compreso nella stima, per commodity."""
    regolate = (
        "trasporto e gestione del contatore, oneri generali di sistema, dispacciamento regolato, accise e IVA"
        if commodity == "luce"
        else "trasporto e gestione del contatore, oneri generali di sistema, accise, addizionale regionale e IVA"
    )
    return (
        f"Esclusi {regolate}: a parita di cliente sono uguali per tutte le offerte, quindi il confronto "
        "resta valido ma il totale non e la bolletta. Non sono conteggiati nemmeno gli sconti condizionati "
        "(es. fattura elettronica o domiciliazione), che dipendono da cosa sceglie il cliente."
    )


class Calcolo:
    """Raccoglie le voci di costo e le note di un singolo calcolo."""

    def __init__(self, offerta: dict, consumo: float, potenza_kw: float, ripartizione: dict | None):
        self.offerta = offerta
        self.luce = offerta["commodity"] == "luce"
        self.consumo = consumo
        self.potenza = potenza_kw
        profilo = ripartizione or (PROFILO_DOMESTICO if offerta["tipo_cliente"] == "domestico" else PROFILO_ALTRI_USI)
        totale_profilo = sum(profilo.values())
        self.fasce = {f: consumo * profilo.get(f, 0) / totale_profilo for f in ("F1", "F2", "F3")}
        self.voci: dict[str, float] = {}
        # Importi su cui si calcolano gli sconti percentuali: componenti energia (macroarea 04)
        # piu indice per lo sconto vendita, prezzo di tutela (PE/CMEM) per lo sconto su tutela.
        self.base_sconto_vendita = 0.0
        self.importo_tutela = 0.0
        self.dettagli: dict[str, list[str]] = {}
        self.note: list[str] = []
        self.completa = True

    def aggiungi(self, voce: str, importo: float, dettaglio: str) -> None:
        self.voci[voce] = self.voci.get(voce, 0.0) + importo
        self.dettagli.setdefault(voce, []).append(f"{dettaglio}: {importo:.2f} €")

    def nota(self, testo: str) -> None:
        if testo not in self.note:
            self.note.append(testo)

    def consumo_fascia(self, fascia: str | None) -> float:
        """Consumo annuo a cui si applica un prezzo indicato per una fascia."""
        if not self.luce or fascia is None:
            return self.consumo
        f1, f2, f3 = self.fasce["F1"], self.fasce["F2"], self.fasce["F3"]
        monoraria = self.offerta.get("tipologia_fasce") in (None, "01")
        if fascia == "01":
            return self.consumo if monoraria else f1
        valori = {"02": f2, "03": f3, "91": f2 + f3, "92": f1 + f3, "93": f1 + f2}
        if fascia in valori:
            return valori[fascia]
        if fascia in ("07", "08"):
            self.nota("Le fasce Peak/OffPeak sono approssimate con F1 e F2+F3.")
            return f1 if fascia == "07" else f2 + f3
        self.nota(f"Fascia {C.decodifica(C.FASCIA, fascia)} non stimabile: il consumo e ripartito solo su F1, F2, F3.")
        self.completa = False
        return 0.0

    def risultato(self) -> dict:
        totale = sum(self.voci.values())
        unita = "kWh" if self.luce else "Smc"
        return {
            "codice": self.offerta["codice"],
            "nome": self.offerta["nome"],
            "venditore": self.offerta.get("venditore"),
            "piva": self.offerta["piva"],
            "fonte": self.offerta["fonte"],
            "tipo_prezzo": self.offerta["tipo_prezzo"],
            "consumo_annuo": f"{self.consumo:g} {unita}",
            "costo_vendita_anno": round(totale, 2),
            "prezzo_medio": f"{totale / self.consumo:.4f} €/{unita}" if self.consumo else None,
            "voci": {voce: round(importo, 2) for voce, importo in self.voci.items()},
            "dettaglio": self.dettagli,
            "stima_completa": self.completa,
            "note": self.note,
            "esclusi": esclusi(self.offerta["commodity"]),
        }


def _quantita_scaglione(quantita: float, da: int | None, a: int | None) -> float:
    """Quota di consumo che cade nello scaglione [da, a] (prezzi applicati a scaglioni)."""
    if da is None and a is None:
        return quantita
    inferiore = max((da or 0) - 1, 0)
    superiore = quantita if a is None else min(quantita, a)
    return max(0.0, superiore - inferiore)


def _nello_scaglione(consumo: float, da: int | None, a: int | None) -> bool:
    """Per i prezzi fissi a scaglioni: vale quello il cui intervallo contiene il consumo annuo."""
    return (da is None or consumo >= da) and (a is None or consumo <= a)


def _pesi_periodo(prezzi: list[dict]) -> list[float]:
    """Frazione del primo anno coperta da ciascun prezzo di uno stesso gruppo.

    I prezzi con durata (mesi dall'attivazione) coprono i mesi in ordine crescente di durata,
    quelli senza durata coprono i mesi restanti del primo anno.
    """
    pesi = [0.0] * len(prezzi)
    mesi_coperti = 0
    con_durata = sorted(
        (i for i, p in enumerate(prezzi) if p.get("periodo", {}).get("durata_mesi")),
        key=lambda i: prezzi[i]["periodo"]["durata_mesi"],
    )
    for i in con_durata:
        fine = min(prezzi[i]["periodo"]["durata_mesi"], 12)
        pesi[i] = max(fine - mesi_coperti, 0) / 12
        mesi_coperti = max(mesi_coperti, fine)
    for i, p in enumerate(prezzi):
        mesi = p.get("periodo", {}).get("mesi")
        if mesi:
            pesi[i] = len(mesi) / 12
            mesi_coperti += len(mesi)
    resto = max(12 - mesi_coperti, 0) / 12
    for i, p in enumerate(prezzi):
        if not p.get("periodo", {}).get("durata_mesi") and not p.get("periodo", {}).get("mesi"):
            pesi[i] = resto
    return pesi


def _componenti(calcolo: Calcolo) -> None:
    opzionali = []
    for comp in calcolo.offerta.get("componenti", []):
        nome = comp["nome"] or "componente"
        # La tipologia standard/opzionale ha senso solo per l'energia verde: diversi venditori
        # marcano "opzionale" anche il prezzo dell'energia, che va invece sempre conteggiato.
        if comp["macroarea"] == "06" and comp["tipologia"] == "02":
            opzionali.append(nome)
            continue
        gruppi: dict[str | None, list[dict]] = {}
        for prezzo in comp["prezzi"]:
            gruppi.setdefault(prezzo.get("fascia"), []).append(prezzo)
        for fascia, prezzi in gruppi.items():
            etichetta = nome if fascia is None else f"{nome} {C.decodifica(C.FASCIA, fascia)}"
            for prezzo, peso in zip(prezzi, _pesi_periodo(prezzi)):
                valore, unita = prezzo["prezzo"], prezzo["unita"]
                if peso == 0 and unita != "05":
                    # Prezzo che si applica solo dopo il primo anno: non entra nella stima annua.
                    calcolo.nota(f"'{etichetta}': il prezzo di {valore:g} {C.decodifica(C.UNITA_MISURA, unita)} vale dopo il primo anno e non e incluso.")
                    continue
                da, a = prezzo.get("consumo_da"), prezzo.get("consumo_a")
                if prezzo.get("periodo", {}).get("valido_fino"):
                    calcolo.nota(f"'{nome}': prezzo valido fino al {prezzo['periodo']['valido_fino']}, considerato per tutto l'anno.")
                if unita in ("03", "04"):
                    quantita = _quantita_scaglione(calcolo.consumo_fascia(fascia), da, a)
                    importo = valore * quantita * peso
                    calcolo.aggiungi("quota energia", importo, etichetta)
                    if comp["macroarea"] == "04":
                        calcolo.base_sconto_vendita += importo
                elif unita == "01":
                    if _nello_scaglione(calcolo.consumo, da, a):
                        calcolo.aggiungi("quota fissa", valore * peso, etichetta)
                elif unita == "02":
                    calcolo.aggiungi("quota potenza", valore * calcolo.potenza * peso, etichetta)
                elif unita == "05":
                    calcolo.aggiungi("una tantum", valore, etichetta)
                else:
                    calcolo.nota(f"'{nome}': unita di misura {C.decodifica(C.UNITA_MISURA, unita)} non gestita.")
                    calcolo.completa = False
    if opzionali:
        calcolo.nota("Componenti opzionali non incluse: " + ", ".join(opzionali) + ".")


def _indici(calcolo: Calcolo, valori: dict[str, float], riferimento: str, lambda_perdite: float) -> None:
    for indice in calcolo.offerta.get("indici", []):
        nome = C.INDICI.get(indice["codice"], ("altro", None))[0]
        if nome == "altro":
            calcolo.nota(f"Indice non standard ({indice.get('altro') or 'non specificato'}): quota indice non stimata.")
            calcolo.completa = False
            continue
        valore = valori.get(nome)
        if valore is None:
            calcolo.nota(f"Valore storico dell'indice {nome} non disponibile negli open data: quota indice non stimata.")
            calcolo.completa = False
            continue
        coefficiente = indice.get("coefficiente") or 1.0
        quantita = calcolo.consumo_fascia(indice.get("fascia"))
        perdite = (1 + lambda_perdite) if calcolo.luce else 1.0
        importo = valore * coefficiente * quantita * perdite
        dettaglio = f"{nome} {valore:.5f} ({riferimento})"
        if coefficiente != 1.0:
            dettaglio += f" x coefficiente {coefficiente:g}"
        if calcolo.luce:
            dettaglio += f" x perdite di rete (1+{lambda_perdite:g})"
        if nome in ("PE", "CMEM"):
            # Offerte "sconto sul servizio di tutela": prezzo di riferimento meno lo sconto su tutela.
            calcolo.aggiungi("prezzo di tutela", importo, dettaglio)
            calcolo.importo_tutela += importo
        else:
            calcolo.aggiungi("indice di prezzo", importo, dettaglio)
            calcolo.base_sconto_vendita += importo
    if calcolo.offerta.get("indici"):
        calcolo.nota(
            "Per l'indice si usa il valore storico pubblicato, non le quotazioni forward usate dal Portale: "
            "la stima delle offerte variabili segue l'andamento recente del mercato."
        )


def _dispacciamento(calcolo: Calcolo) -> None:
    for disp in calcolo.offerta.get("dispacciamento", []):
        if disp["tipo"] == "99" and disp.get("valore") is not None:
            calcolo.aggiungi("dispacciamento del venditore", disp["valore"] * calcolo.consumo, disp["nome"] or "dispacciamento")


def _componenti_regolate(calcolo: Calcolo, parametri: dict) -> None:
    domestico = calcolo.offerta["tipo_cliente"] != "altri usi"

    def parametro(nome: str) -> float | None:
        voce = parametri.get(nome)
        return voce["valore"] if voce else None

    for codice in calcolo.offerta.get("componenti_regolate", []):
        nome = C.decodifica(C.COMPONENTI_REGOLATE, codice)
        if calcolo.luce and codice == "01":
            valore = parametro("pcv_c" if domestico else "pcv_a")
            if valore is not None:
                calcolo.aggiungi("componenti regolate", valore, f"{nome} {valore:g} €/anno")
                continue
        elif not calcolo.luce and codice == "09":
            valore = parametro("qvd_f_d" if domestico else "qvd_f_nd")
            if valore is not None:
                calcolo.aggiungi("componenti regolate", valore, f"{nome} {valore:g} €/anno")
                continue
        elif not calcolo.luce and codice in ("04", "05", "06", "07", "10"):
            chiave = {"04": "cpr", "05": "grad", "06": "qt", "07": "qt", "10": "qvd_v_d" if domestico else "qvd_v_nd"}[codice]
            valore = parametro(chiave)
            if valore is not None:
                calcolo.aggiungi("componenti regolate", valore * calcolo.consumo, f"{nome} {valore:g} €/Smc")
                continue
        calcolo.nota(f"Componente regolata {nome} non stimata (valore non presente nei parametri pubblicati).")
        calcolo.completa = False


def _sconti(calcolo: Calcolo) -> None:
    for sconto in calcolo.offerta.get("sconti", []):
        nome = sconto["nome"] or "sconto"
        condizioni = [c["codice"] for c in sconto.get("condizioni", [])]
        if any(c != "00" for c in condizioni):
            descrizioni = ", ".join(C.decodifica(C.CONDIZIONE_SCONTO, c) for c in condizioni if c != "00")
            calcolo.nota(f"Sconto '{nome}' non conteggiato perche condizionato ({descrizioni}).")
            continue
        if sconto.get("validita") == "03":
            calcolo.nota(f"Sconto '{nome}' non conteggiato: si applica dopo i primi 12 mesi.")
            continue
        durata = (sconto.get("periodo") or {}).get("durata_mesi")
        peso = min(durata, 12) / 12 if durata else 1.0
        bersagli = sconto.get("applicato_a") or []
        fascia_sconto = {"11": "01", "12": "02", "13": "03", "91": "91", "92": "92", "93": "93"}
        for prezzo in sconto.get("prezzi", []):
            valore, unita = prezzo["prezzo"], prezzo["unita"]
            if prezzo["tipologia"] == "04":
                if unita == "06":
                    calcolo.aggiungi("sconti", -calcolo.importo_tutela * valore / 100, f"{nome} ({valore:g}% sul prezzo di tutela)")
                elif unita in ("03", "04"):
                    calcolo.aggiungi("sconti", -valore * calcolo.consumo, f"{nome} (sul prezzo di tutela)")
                else:
                    calcolo.nota(f"Sconto '{nome}' sul servizio di tutela non stimato.")
                    calcolo.completa = False
                continue
            da, a = prezzo.get("valido_da"), prezzo.get("valido_fino")
            if unita in ("03", "04"):
                fasce = [fascia_sconto[b] for b in bersagli if b in fascia_sconto]
                quantita = sum(calcolo.consumo_fascia(f) for f in fasce) if fasce else calcolo.consumo
                importo = valore * _quantita_scaglione(quantita, da, a) * peso
            elif unita == "01":
                importo = valore * peso if _nello_scaglione(calcolo.consumo, da, a) else 0.0
            elif unita == "02":
                importo = valore * calcolo.potenza * peso
            elif unita == "05":
                importo = valore
            elif unita == "06":
                importo = calcolo.base_sconto_vendita * valore / 100 * peso
            else:
                calcolo.nota(f"Sconto '{nome}': unita di misura {C.decodifica(C.UNITA_MISURA, unita)} non gestita.")
                continue
            calcolo.aggiungi("sconti", -abs(importo), nome)


def _placet(calcolo: Calcolo, valori: dict[str, float], riferimento: str, lambda_perdite: float) -> None:
    dati = calcolo.offerta["placet"]
    if dati.get("quota_fissa_anno") is not None:
        calcolo.aggiungi("quota fissa", dati["quota_fissa_anno"], "quota fissa PLACET")
    # Nel CSV PLACET le strutture di prezzo non usate sono valorizzate a 0 invece che vuote.
    prezzi = {k: v for k, v in dati["prezzi_energia"].items() if v}
    alpha = dati.get("spread_alpha")

    if calcolo.offerta["tipo_prezzo"] == "fisso":
        if not calcolo.luce:
            calcolo.aggiungi("quota energia", prezzi.get("gas", 0) * calcolo.consumo, "prezzo gas PLACET")
        elif {"F1", "F2", "F3"} <= prezzi.keys():
            for fascia in ("F1", "F2", "F3"):
                calcolo.aggiungi("quota energia", prezzi[fascia] * calcolo.fasce[fascia], f"prezzo {fascia}")
        elif {"F1_biorario", "F23"} <= prezzi.keys():
            calcolo.aggiungi("quota energia", prezzi["F1_biorario"] * calcolo.fasce["F1"], "prezzo F1")
            calcolo.aggiungi("quota energia", prezzi["F23"] * (calcolo.fasce["F2"] + calcolo.fasce["F3"]), "prezzo F2+F3")
        elif "monorario" in prezzi:
            calcolo.aggiungi("quota energia", prezzi["monorario"] * calcolo.consumo, "prezzo monorario")
        return

    nome = "PUN" if calcolo.luce else "PSV"
    valore = valori.get(nome)
    if valore is None:
        calcolo.nota(f"Valore storico dell'indice {nome} non disponibile: quota indice non stimata.")
        calcolo.completa = False
    else:
        perdite = (1 + lambda_perdite) if calcolo.luce else 1.0
        dettaglio = f"{nome} {valore:.5f} ({riferimento})" + (f" x perdite di rete (1+{lambda_perdite:g})" if calcolo.luce else "")
        calcolo.aggiungi("indice di prezzo", valore * perdite * calcolo.consumo, dettaglio)
        calcolo.nota("Per l'indice si usa il valore storico pubblicato, non le quotazioni forward usate dal Portale.")
    if alpha is not None:
        calcolo.aggiungi("quota energia", alpha * calcolo.consumo, f"spread alpha {alpha:g}")


def stima(
    offerta: dict,
    consumo_annuo: float,
    parametri: dict,
    valori_indici: dict[str, float],
    riferimento_indici: str,
    potenza_kw: float = 3.0,
    ripartizione: dict | None = None,
) -> dict:
    """Stima il costo annuo della parte vendita di un'offerta luce o gas.

    consumo_annuo e in kWh per la luce e in Smc per il gas; ripartizione e un dizionario
    {"F1": x, "F2": y, "F3": z} (percentuali o frazioni) che sostituisce il profilo standard.
    """
    calcolo = Calcolo(offerta, consumo_annuo, potenza_kw, ripartizione)
    if offerta["commodity"] == "dual":
        calcolo.nota("Le offerte dual vanno stimate sulle singole offerte luce e gas collegate (vedi offerte_congiunte).")
        calcolo.completa = False
        return calcolo.risultato()

    lambda_perdite = (parametri.get("lambda") or {}).get("valore") or 0.10
    if offerta["fonte"] == "PLACET":
        _placet(calcolo, valori_indici, riferimento_indici, lambda_perdite)
    else:
        _componenti(calcolo)
        _indici(calcolo, valori_indici, riferimento_indici, lambda_perdite)
        if calcolo.luce:
            _dispacciamento(calcolo)
        _componenti_regolate(calcolo, parametri)
        _sconti(calcolo)
        if offerta["tipo_prezzo"] == "flat":
            calcolo.nota("Offerta flat: il prezzo vale solo entro i consumi minimo e massimo indicati.")
    return calcolo.risultato()
