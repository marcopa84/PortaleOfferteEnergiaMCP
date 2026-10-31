import pytest
from mcp.server.mcpserver.exceptions import ToolError

from portale_offerte_mcp import server


def offerta(codice, commodity, nome="Offerta", piva="0123", **altro):
    return {
        "codice": codice, "fonte": "mercato libero", "piva": piva, "venditore": "Prova", "commodity": commodity,
        "nome": nome, "tipo_cliente": "domestico", "tipo_prezzo": "fisso", "contatti": {}, "indici": [],
        "componenti": [], "sconti": [], "dispacciamento": [], "componenti_regolate": [], "zone": {"regioni": [], "province": [], "comuni": []},
        "data_inizio": "2026-01-01T00:00:00", "data_fine": "2026-12-31T23:59:59", "tipologia_fasce": "01",
        **altro,
    }


@pytest.fixture
def archivio(monkeypatch):
    a = server.archivio
    monkeypatch.setattr(a, "assicura", lambda forza=False: None)
    offerte = [
        offerta("LUCE1", "luce"),
        offerta("GAS1", "gas"),
        offerta("DUAL1", "dual", offerte_congiunte={"luce": ["LUCE1"], "gas": ["GAS1"]}),
    ]
    monkeypatch.setattr(a, "offerte", offerte)
    monkeypatch.setattr(a, "per_codice", {o["codice"]: [o] for o in offerte})
    monkeypatch.setattr(a, "parametri", {"luce": {}, "gas": {}})
    monkeypatch.setattr(a, "prezzi_storici", [{"mese": "2026-09", "PUN": 0.2, "PSV": 0.8}])
    monkeypatch.setattr(a, "giornata", type("G", (), {"data": __import__("datetime").date(2026, 10, 31)})())
    return a


def test_stima_rifiuta_luce_e_gas_insieme(archivio):
    with pytest.raises(ToolError, match="Luce: LUCE1. Gas: GAS1"):
        server.stima_costo(codici=["LUCE1", "GAS1"], consumo_annuo=2700)


def test_stima_rifiuta_le_dual_indicando_le_collegate(archivio):
    with pytest.raises(ToolError, match="DUAL1: luce LUCE1, gas GAS1"):
        server.stima_costo(codici=["DUAL1"], consumo_annuo=2700)


def test_raggruppa_versioni_della_stessa_offerta():
    righe = [
        {"codice": "A", "piva": "1", "nome": "Casa Gas", "commodity": "gas", "tipo_cliente": "domestico", "fonte": "mercato libero", "tipo_prezzo": "variabile", "costo_vendita_anno": 10},
        {"codice": "B", "piva": "1", "nome": "CASA GAS", "commodity": "gas", "tipo_cliente": "domestico", "fonte": "mercato libero", "tipo_prezzo": "variabile", "costo_vendita_anno": 11},
        {"codice": "C", "piva": "2", "nome": "Casa Gas", "commodity": "gas", "tipo_cliente": "domestico", "fonte": "mercato libero", "tipo_prezzo": "variabile", "costo_vendita_anno": 12},
    ]
    gruppi = server._raggruppa(righe)
    assert [r["codice"] for r in gruppi] == ["A", "C"]
    assert gruppi[0]["altre_versioni"] == [{"codice": "B", "valida_fino_al": None, "costo_vendita_anno": 11}]


def test_avviso_quando_indice_recente_lontano_dalla_media(archivio, monkeypatch):
    mesi = [{"mese": f"2026-{m:02d}", "PUN": 0.1, "PSV": 0.5} for m in range(1, 9)] + [{"mese": "2026-09", "PUN": 0.1, "PSV": 0.9}]
    monkeypatch.setattr(archivio, "prezzi_storici", mesi)
    assert "PSV" in server._avviso_indici("gas")
    assert server._avviso_indici("luce") is None


def test_tra_versioni_di_pari_costo_resta_in_evidenza_quella_valida_piu_a_lungo(archivio, monkeypatch):
    versioni = [
        offerta("OTTOBRE", "gas", nome="Casa Gas", data_fine="2026-12-01T23:59:59"),
        offerta("NOVEMBRE", "gas", nome="Casa Gas", data_fine="2027-01-31T23:59:59"),
    ]
    monkeypatch.setattr(archivio, "offerte", versioni)
    risposta = server.cerca_offerte(commodity="gas", consumo_annuo=1000)
    [riga] = risposta["risultati"]
    assert riga["codice"] == "NOVEMBRE"
    assert [v["codice"] for v in riga["altre_versioni"]] == ["OTTOBRE"]
