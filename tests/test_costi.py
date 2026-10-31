import pytest

from portale_offerte_mcp import costi

PARAMETRI = {"lambda": {"valore": 0.10}, "pcv_c": {"valore": 41.18}}
INDICI = {"PUN": 0.20, "PSV": 0.80, "PE": 0.15}


def offerta(commodity="luce", tipo_prezzo="fisso", fasce="01", componenti=(), indici=(), sconti=(), **altro):
    return {
        "codice": "PROVA",
        "fonte": "mercato libero",
        "piva": "0123",
        "venditore": "Prova",
        "contatti": {},
        "commodity": commodity,
        "nome": "Prova",
        "tipo_cliente": "domestico",
        "tipo_prezzo": tipo_prezzo,
        "tipologia_fasce": fasce if commodity == "luce" else None,
        "componenti": list(componenti),
        "indici": list(indici),
        "sconti": list(sconti),
        "dispacciamento": [],
        "componenti_regolate": [],
        **altro,
    }


def componente(macroarea, *prezzi, tipologia="01", nome="comp"):
    return {"nome": nome, "descrizione": None, "tipologia": tipologia, "macroarea": macroarea, "prezzi": list(prezzi)}


def prezzo(valore, unita="03", fascia=None, **altro):
    p = {"prezzo": valore, "unita": unita, **altro}
    if fascia:
        p["fascia"] = fascia
    return p


def sconto(*prezzi, condizione="00", validita="01", **altro):
    return {
        "nome": "sconto",
        "descrizione": None,
        "applicato_a": [],
        "validita": validita,
        "iva": "si",
        "periodo": None,
        "condizioni": [{"codice": condizione, "descrizione": None}],
        "prezzi": list(prezzi),
        **altro,
    }


def stima(o, consumo, **kwargs):
    return costi.stima(o, consumo, PARAMETRI, INDICI, "mese di prova", **kwargs)


def test_fisso_monorario():
    o = offerta(componenti=[componente("01", prezzo(96, "01")), componente("04", prezzo(0.12, fascia="01"))])
    r = stima(o, 2700)
    assert r["costo_vendita_anno"] == pytest.approx(96 + 0.12 * 2700)
    assert r["stima_completa"]


def test_trioraria_con_profilo_standard_e_personalizzato():
    o = offerta(fasce="03", componenti=[componente(
        "04", prezzo(0.15, fascia="01"), prezzo(0.12, fascia="02"), prezzo(0.10, fascia="03"),
    )])
    assert stima(o, 1000)["costo_vendita_anno"] == pytest.approx(0.15 * 330 + 0.12 * 310 + 0.10 * 360)
    personalizzata = stima(o, 1000, ripartizione={"F1": 50, "F2": 25, "F3": 25})
    assert personalizzata["costo_vendita_anno"] == pytest.approx(0.15 * 500 + 0.12 * 250 + 0.10 * 250)


def test_variabile_pun_con_perdite_e_spread():
    o = offerta(tipo_prezzo="variabile", indici=[{"codice": "12"}], componenti=[componente("04", prezzo(0.02, fascia="01"))])
    r = stima(o, 1000)
    assert r["voci"]["indice di prezzo"] == pytest.approx(0.20 * 1.1 * 1000)
    assert r["costo_vendita_anno"] == pytest.approx(220 + 20)


def test_gas_variabile_senza_perdite():
    o = offerta(commodity="gas", tipo_prezzo="variabile", indici=[{"codice": "14"}])
    assert stima(o, 1000)["costo_vendita_anno"] == pytest.approx(800)


def test_indice_ttf_non_disponibile_rende_la_stima_incompleta():
    o = offerta(commodity="gas", tipo_prezzo="variabile", indici=[{"codice": "13"}])
    r = stima(o, 1000)
    assert not r["stima_completa"]
    assert any("TTF" in n for n in r["note"])


def test_scaglioni_di_consumo():
    o = offerta(commodity="gas", componenti=[componente(
        "04", prezzo(1.0, "04", consumo_da=0, consumo_a=100), prezzo(0.5, "04", consumo_da=101),
    )])
    assert stima(o, 150)["costo_vendita_anno"] == pytest.approx(100 * 1.0 + 50 * 0.5)


def test_prezzo_per_i_primi_mesi():
    o = offerta(componenti=[componente(
        "04", prezzo(0.05, fascia="01", periodo={"durata_mesi": 3}), prezzo(0.10, fascia="01"),
    )])
    assert stima(o, 1000)["costo_vendita_anno"] == pytest.approx(0.05 * 1000 * 3 / 12 + 0.10 * 1000 * 9 / 12)


def test_sconto_percentuale_solo_su_quota_energia():
    o = offerta(
        componenti=[componente("01", prezzo(100, "01")), componente("04", prezzo(0.10, fascia="01"))],
        sconti=[sconto({"tipologia": "03", "unita": "06", "prezzo": 10})],
    )
    assert stima(o, 1000)["costo_vendita_anno"] == pytest.approx(100 + 100 - 10)


def test_sconti_condizionati_o_tardivi_esclusi():
    o = offerta(
        componenti=[componente("01", prezzo(100, "01"))],
        sconti=[
            sconto({"tipologia": "01", "unita": "01", "prezzo": 20}, condizione="01"),
            sconto({"tipologia": "01", "unita": "01", "prezzo": 20}, validita="03"),
        ],
    )
    r = stima(o, 1000)
    assert r["costo_vendita_anno"] == pytest.approx(100)
    assert len(r["note"]) == 2


def test_sconto_su_tutela():
    o = offerta(
        tipo_prezzo="variabile",
        indici=[{"codice": "05"}],
        sconti=[sconto({"tipologia": "04", "unita": "06", "prezzo": 5})],
    )
    tutela = 0.15 * 1.1 * 1000
    assert stima(o, 1000)["costo_vendita_anno"] == pytest.approx(tutela * 0.95)


def test_energia_verde_opzionale_esclusa_ma_non_le_altre_componenti():
    o = offerta(componenti=[
        componente("04", prezzo(0.10, fascia="01"), tipologia="02"),
        componente("06", prezzo(0.01, fascia="01"), tipologia="02", nome="Verde"),
    ])
    r = stima(o, 1000)
    assert r["costo_vendita_anno"] == pytest.approx(100)
    assert any("Verde" in n for n in r["note"])


def test_pcv_regolata():
    o = offerta(componenti_regolate=["01"])
    assert stima(o, 1000)["voci"]["componenti regolate"] == pytest.approx(41.18)


def placet(tipo_prezzo, prezzi_energia, quota_fissa, alpha=None):
    o = offerta(tipo_prezzo=tipo_prezzo)
    o["fonte"] = "PLACET"
    o["placet"] = {"quota_fissa_anno": quota_fissa, "prezzi_energia": prezzi_energia, "spread_alpha": alpha}
    return o


def test_placet_fisso_ignora_le_fasce_a_zero():
    prezzi = {"F1": 0.0, "F2": 0.0, "F3": 0.0, "F1_biorario": 0.13, "F23": 0.12, "monorario": 0.125}
    r = stima(placet("fisso", prezzi, 85), 1000)
    assert r["costo_vendita_anno"] == pytest.approx(85 + 0.13 * 330 + 0.12 * 670)


def test_placet_variabile():
    r = stima(placet("variabile", {}, 100, alpha=0.01), 1000)
    assert r["costo_vendita_anno"] == pytest.approx(100 + 0.20 * 1.1 * 1000 + 0.01 * 1000)


def test_prezzo_dopo_il_primo_anno_non_crea_righe_a_zero():
    o = offerta(componenti=[componente(
        "04", prezzo(0.10, fascia="01", periodo={"durata_mesi": 12}), prezzo(0.20, fascia="01"), nome="Prezzo",
    )])
    r = stima(o, 1000)
    assert r["costo_vendita_anno"] == pytest.approx(100)
    assert r["dettaglio"]["quota energia"] == ["Prezzo F1 (o monorario): 100.00 €"]
    assert any("dopo il primo anno" in n for n in r["note"])


def test_nota_esclusi_diversa_per_luce_e_gas():
    assert "dispacciamento" in costi.esclusi("luce")
    assert "dispacciamento" not in costi.esclusi("gas")
    assert "sconti condizionati" in costi.esclusi("gas")
