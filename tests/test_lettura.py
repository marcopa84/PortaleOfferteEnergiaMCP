import io

from portale_offerte_mcp import lettura, sorgenti

XML_OFFERTA = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<ListaOfferteMercatoLibero xmlns="http://www.acquirenteunico.it/schemas/SII_AU/OffertaRetail/01">
    <offerta>
        <IdentificativiOfferta>
            <PIVA_UTENTE>01234567890</PIVA_UTENTE>
            <COD_OFFERTA>000001ESVML01XXPROVA000000000000</COD_OFFERTA>
        </IdentificativiOfferta>
        <DettaglioOfferta>
            <TIPO_MERCATO>01</TIPO_MERCATO>
            <OFFERTA_SINGOLA>SI</OFFERTA_SINGOLA>
            <TIPO_CLIENTE>01</TIPO_CLIENTE>
            <DOMESTICO_RESIDENTE>03</DOMESTICO_RESIDENTE>
            <TIPO_OFFERTA>02</TIPO_OFFERTA>
            <TIPOLOGIA_ATT_CONTR>01</TIPOLOGIA_ATT_CONTR>
            <TIPOLOGIA_ATT_CONTR>04</TIPOLOGIA_ATT_CONTR>
            <NOME_OFFERTA>Prova Variabile</NOME_OFFERTA>
            <DESCRIZIONE>Offerta di prova</DESCRIZIONE>
            <DURATA>-1</DURATA>
            <GARANZIE>NO</GARANZIE>
            <ModalitaAttivazione><MODALITA>01</MODALITA></ModalitaAttivazione>
            <Contatti>
                <TELEFONO>0123456</TELEFONO>
                <URL_SITO_VENDITORE>www.prova.it</URL_SITO_VENDITORE>
                <URL_OFFERTA>https://www.prova.it/offerta</URL_OFFERTA>
            </Contatti>
        </DettaglioOfferta>
        <RiferimentiPrezzoEnergia><IDX_PREZZO_ENERGIA>12</IDX_PREZZO_ENERGIA></RiferimentiPrezzoEnergia>
        <ValiditaOfferta>
            <DATA_INIZIO>13/10/2026_17:27:02</DATA_INIZIO>
            <DATA_FINE>10/01/2027_23:59:59</DATA_FINE>
        </ValiditaOfferta>
        <CaratteristicheOfferta><POTENZA_MAX>6.0</POTENZA_MAX></CaratteristicheOfferta>
        <MetodoPagamento><MODALITA_PAGAMENTO>01</MODALITA_PAGAMENTO></MetodoPagamento>
        <MetodoPagamento><MODALITA_PAGAMENTO>99</MODALITA_PAGAMENTO><DESCRIZIONE>PayPal</DESCRIZIONE></MetodoPagamento>
        <TipoPrezzo><TIPOLOGIA_FASCE>01</TIPOLOGIA_FASCE></TipoPrezzo>
        <ComponenteImpresa>
            <NOME>SPREAD</NOME>
            <DESCRIZIONE>Spread</DESCRIZIONE>
            <TIPOLOGIA>01</TIPOLOGIA>
            <MACROAREA>04</MACROAREA>
            <IntervalloPrezzi>
                <FASCIA_COMPONENTE>01</FASCIA_COMPONENTE>
                <PREZZO>0.0200</PREZZO>
                <UNITA_MISURA>03</UNITA_MISURA>
                <PeriodoValidita><DURATA>12</DURATA></PeriodoValidita>
            </IntervalloPrezzi>
        </ComponenteImpresa>
        <ZoneOfferta>
            <REGIONE>03</REGIONE>
            <PROVINCIA>015</PROVINCIA>
        </ZoneOfferta>
        <Sconto>
            <NOME>Benvenuto</NOME>
            <DESCRIZIONE>Sconto di benvenuto</DESCRIZIONE>
            <VALIDITA>01</VALIDITA>
            <IVA_SCONTO>01</IVA_SCONTO>
            <Condizione><CONDIZIONE_APPLICAZIONE>00</CONDIZIONE_APPLICAZIONE></Condizione>
            <PrezziSconto><TIPOLOGIA>01</TIPOLOGIA><UNITA_MISURA>05</UNITA_MISURA><PREZZO>30</PREZZO></PrezziSconto>
        </Sconto>
    </offerta>
</ListaOfferteMercatoLibero>
"""


def test_offerta_mercato_libero():
    [o] = lettura.leggi_offerte_mercato_libero(io.BytesIO(XML_OFFERTA.encode()))
    assert o["codice"] == "000001ESVML01XXPROVA000000000000"
    assert o["commodity"] == "luce"
    assert o["tipo_cliente"] == "domestico"
    assert o["residenza"] == "tutti"
    assert o["tipo_prezzo"] == "variabile"
    assert o["valida_per"] == ["cambio fornitore", "voltura"]
    assert o["data_inizio"] == "2026-10-13T17:27:02"
    assert o["potenza_max"] == 6.0
    assert o["pagamenti"] == ["domiciliazione bancaria", "altro: PayPal"]
    assert o["indici"][0]["codice"] == "12"
    assert o["zone"] == {"regioni": ["03"], "province": ["015"], "comuni": []}
    [comp] = o["componenti"]
    assert comp["macroarea"] == "04"
    assert comp["prezzi"] == [{"fascia": "01", "prezzo": 0.02, "unita": "03", "periodo": {"durata_mesi": 12}}]
    [sconto] = o["sconti"]
    assert sconto["condizioni"] == [{"codice": "00", "descrizione": None}]
    assert sconto["prezzi"][0]["prezzo"] == 30.0


CSV_PLACET = (
    "denominazione,codice_fiscale,p_iva,url_sito_venditore,telefono,nome_offerta,cod_offerta,url_offerta,"
    "modalita_attivazione,modalita_pagamento,data_inizio,data_fine,tipo_cliente,tipo_offerta,p_fix_f,p_fix_v,"
    "p_vol_f1,p_vol_f2,p_vol_f3,p_vol_bf1,p_vol_bf23,p_vol_mono,alpha,regione,provincia,comune\n"
    "PROVA SRL,0123,0123,https://prova.it,,PLACET Fissa,COD1,https://prova.it/placet,"
    "Offerta attivabile da qualsiasi canale,Domiciliazione bancaria;Bollettino precompilato,"
    "05/09/2026,31/12/2026,domestico,prezzo fisso,85.000000,0.000000,0.000000,0.000000,0.000000,"
    "0.130000,0.120000,0.125000,0.000000,,,001055;001057\n"
)


def test_offerta_placet():
    [o] = lettura.leggi_offerte_placet(io.BytesIO(CSV_PLACET.encode()), "luce")
    assert o["fonte"] == "PLACET"
    assert o["venditore"] == "PROVA SRL"
    assert o["tipo_prezzo"] == "fisso"
    assert o["pagamenti"] == ["Domiciliazione bancaria", "Bollettino precompilato"]
    assert o["data_fine"] == "2026-12-31T23:59:59"
    assert o["placet"]["quota_fissa_anno"] == 85.0
    assert o["placet"]["prezzi_energia"]["F1_biorario"] == 0.13
    assert o["zone"]["comuni"] == ["001055", "001057"]


def test_prezzi_storici_cp1252():
    contenuto = "AnnoMese;PUN (€/kWh);PSV (€/Smc);Pfor (€/Smc)\r\n202608;0,18;0,69;\r\n202609;0,207542;0,844939;\r\n"
    mesi, unita = lettura.leggi_prezzi_storici(io.BytesIO(contenuto.encode("cp1252")))
    assert unita == {"PUN": "€/kWh", "PSV": "€/Smc", "Pfor": "€/Smc"}
    assert mesi[-1] == {"mese": "2026-09", "PUN": 0.207542, "PSV": 0.844939, "Pfor": None}


def test_link_open_data():
    html = """
    <a href="/portaleOfferte/resources/cms/documents/abc123.csv">Prezzi storici (csv)</a>
    <a href="/portaleOfferte/resources/opendata/csv/offerte/2026_10/PO_Offerte_E_PLACET_20261031.csv">x</a>
    <a href="/portaleOfferte/resources/opendata/csv/offerteML/2026_10/PO_Offerte_D_MLIBERO_20261031.xml">x</a>
    <a href="/portaleOfferte/resources/opendata/csv/parametri/2026_10/PO_Parametri_G_20261031.csv">x</a>
    """
    giornalieri, prezzi = sorgenti.link_open_data(html)
    assert prezzi == "https://www.ilportaleofferte.it/portaleOfferte/resources/cms/documents/abc123.csv"
    assert giornalieri["offerte_luce_placet"][1] == "20261031"
    assert giornalieri["offerte_dual_ml"][0].endswith("PO_Offerte_D_MLIBERO_20261031.xml")
    assert "parametri_gas" in giornalieri
