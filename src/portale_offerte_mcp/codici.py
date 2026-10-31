"""Tabelle di decodifica dei codici usati negli open data del Portale Offerte.

Fonte: SII - "Trasmissione Offerte Mercato Retail", sezione 7.1 "Formato Offerta"
(tracciato in vigore dal 01/04/2026). I codici non presenti nella specifica vengono
restituiti come "codice XX" invece di essere scartati.
"""

TIPO_MERCATO = {"01": "luce", "02": "gas", "03": "dual"}

TIPO_CLIENTE = {"01": "domestico", "02": "altri usi", "03": "condominio uso domestico"}

DOMESTICO_RESIDENTE = {"01": "residente", "02": "non residente", "03": "tutti"}

TIPO_OFFERTA = {"01": "fisso", "02": "variabile", "03": "flat", "04": "mista"}

OFFERTA_ONNICOMPRENSIVA = {"01": "onnicomprensiva", "02": "onnicomprensiva a canone"}

TIPOLOGIA_ATT_CONTR = {
    "01": "cambio fornitore",
    "02": "prima attivazione",
    "03": "riattivazione",
    "04": "voltura",
    "99": "sempre",
}

MODALITA_ATTIVAZIONE = {
    "01": "solo web",
    "02": "qualsiasi canale",
    "03": "punto vendita",
    "04": "teleselling",
    "05": "agenzia",
    "99": "altro",
}

MODALITA_PAGAMENTO = {
    "01": "domiciliazione bancaria",
    "02": "domiciliazione postale",
    "03": "domiciliazione su carta di credito",
    "04": "bollettino precompilato",
    "99": "altro",
}

# Indice di riferimento delle offerte variabili: (nome indice, periodicita di aggiornamento).
# La periodicita riguarda solo la fatturazione: per la stima il Portale usa sempre i forward trimestrali.
INDICI = {
    "01": ("PUN", "trimestrale"),
    "02": ("TTF", "trimestrale"),
    "03": ("PSV", "trimestrale"),
    "04": ("Psbil", "trimestrale"),
    "05": ("PE", None),
    "06": ("CMEM", None),
    "07": ("Pfor", None),
    "08": ("PUN", "bimestrale"),
    "09": ("TTF", "bimestrale"),
    "10": ("PSV", "bimestrale"),
    "11": ("Psbil", "bimestrale"),
    "12": ("PUN", "mensile"),
    "13": ("TTF", "mensile"),
    "14": ("PSV", "mensile"),
    "15": ("Psbil", "mensile"),
    "99": ("altro", None),
}

TIPOLOGIA_FASCE = {
    "01": "monorario",
    "02": "F1, F2",
    "03": "F1, F2, F3",
    "04": "F1, F2, F3, F4",
    "05": "F1, F2, F3, F4, F5",
    "06": "F1, F2, F3, F4, F5, F6",
    "07": "Peak/OffPeak",
    "91": "biorario F1 / F2+F3",
    "92": "biorario F2 / F1+F3",
    "93": "biorario F3 / F1+F2",
}

FASCIA = {
    "01": "F1 (o monorario)",
    "02": "F2",
    "03": "F3",
    "04": "F4",
    "05": "F5",
    "06": "F6",
    "07": "Peak",
    "08": "OffPeak",
    "91": "F2+F3",
    "92": "F1+F3",
    "93": "F1+F2",
}

COMPONENTI_REGOLATE = {
    "01": "PCV",
    "02": "PPE",
    "03": "CCR",
    "04": "CPR",
    "05": "GRAD",
    "06": "QTint",
    "07": "QTpsv",
    "09": "QVD fissa",
    "10": "QVD variabile",
}

TIPO_DISPACCIAMENTO = {
    "01": "corrispettivo dispacciamento",
    "02": "PD",
    "09": "capacita di mercato STG",
    "10": "capacita di mercato MT",
    "11": "reintegrazione oneri salvaguardia",
    "12": "reintegrazione oneri tutele graduali",
    "13": "DispBT",
    "14": "CdispD",
    "99": "altro (definito dal venditore)",
}

TIPOLOGIA_COMPONENTE = {"01": "standard (inclusa nel prezzo)", "02": "opzionale"}

MACROAREA = {
    "01": "commercializzazione quota fissa",
    "02": "commercializzazione quota energia",
    "04": "prezzo quota energia",
    "05": "una tantum",
    "06": "energia verde (FER)",
}

UNITA_MISURA = {
    "01": "€/anno",
    "02": "€/kW",
    "03": "€/kWh",
    "04": "€/Smc",
    "05": "€",
    "06": "%",
}

TIPO_PREZZO = {"01": "fisso", "02": "variabile"}

MESI = {
    "01": "gennaio", "02": "febbraio", "03": "marzo", "04": "aprile",
    "05": "maggio", "06": "giugno", "07": "luglio", "08": "agosto",
    "09": "settembre", "10": "ottobre", "11": "novembre", "12": "dicembre",
}

TIPOLOGIA_CONDIZIONE = {
    "01": "attivazione",
    "02": "disattivazione",
    "03": "recesso",
    "04": "offerta pluriennale",
    "05": "oneri di recesso anticipato",
    "99": "altro",
}

LIMITANTE = {"01": "si", "02": "no"}

COMPONENTE_FASCIA_SCONTO = {
    **COMPONENTI_REGOLATE,
    "11": "F1", "12": "F2", "13": "F3", "14": "F4", "15": "F5", "16": "F6",
    "17": "Peak", "18": "OffPeak", "91": "F2+F3", "92": "F1+F3", "93": "F1+F2",
}

VALIDITA_SCONTO = {"01": "all'ingresso", "02": "entro 12 mesi", "03": "oltre 12 mesi"}

IVA_SCONTO = {"01": "si", "02": "no"}

CONDIZIONE_SCONTO = {
    "00": "non condizionato",
    "01": "fatturazione elettronica",
    "02": "gestione online",
    "03": "fatturazione elettronica + domiciliazione bancaria",
    "99": "altro",
}

TIPOLOGIA_SCONTO = {
    "01": "sconto fisso",
    "02": "sconto potenza",
    "03": "sconto vendita",
    "04": "sconto su tutela",
}

MACROAREA_SERVIZI = {
    "01": "caldaia",
    "02": "mobility",
    "03": "solare termico",
    "04": "fotovoltaico",
    "05": "climatizzazione",
    "06": "polizza assicurativa",
    "99": "altro",
}

REGIONI = {
    "01": "Piemonte", "02": "Valle d'Aosta", "03": "Lombardia", "04": "Trentino-Alto Adige",
    "05": "Veneto", "06": "Friuli-Venezia Giulia", "07": "Liguria", "08": "Emilia-Romagna",
    "09": "Toscana", "10": "Umbria", "11": "Marche", "12": "Lazio", "13": "Abruzzo",
    "14": "Molise", "15": "Campania", "16": "Puglia", "17": "Basilicata", "18": "Calabria",
    "19": "Sicilia", "20": "Sardegna",
}


def decodifica(tabella: dict, codice: str | None) -> str | None:
    """Restituisce la descrizione di un codice, o "codice XX" se non e nella tabella."""
    if codice is None or codice == "":
        return None
    valore = tabella.get(codice)
    if valore is None:
        return f"codice {codice}"
    if isinstance(valore, tuple):
        nome, periodicita = valore
        return f"{nome} ({periodicita})" if periodicita else nome
    return valore
