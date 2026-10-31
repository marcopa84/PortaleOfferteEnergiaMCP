import pytest

from portale_offerte_mcp.archivio import Archivio, ErroreRicerca, compatta


@pytest.fixture
def archivio():
    a = Archivio()
    a.comuni = [
        {"codice": "015146", "nome": "Milano", "provincia": "015", "sigla": "MI", "regione": "03", "nome_regione": "Lombardia"},
        {"codice": "016091", "nome": "Castro", "provincia": "016", "sigla": "BG", "regione": "03", "nome_regione": "Lombardia"},
        {"codice": "075096", "nome": "Castro", "provincia": "075", "sigla": "LE", "regione": "16", "nome_regione": "Puglia"},
        {"codice": "001272", "nome": "Torino", "provincia": "001", "sigla": "TO", "regione": "01", "nome_regione": "Piemonte"},
        {"codice": "080063", "nome": "Reggio di Calabria", "provincia": "080", "sigla": "RC", "regione": "18", "nome_regione": "Calabria"},
        {"codice": "035033", "nome": "Reggio nell'Emilia", "provincia": "035", "sigla": "RE", "regione": "08", "nome_regione": "Emilia-Romagna"},
        {"codice": "037006", "nome": "Bologna", "provincia": "037", "sigla": "BO", "regione": "08", "nome_regione": "Emilia-Romagna"},
        {"codice": "002066", "nome": "Greggio", "provincia": "002", "sigla": "VC", "regione": "01", "nome_regione": "Piemonte"},
    ]
    a._comuni_per_codice = {c["codice"]: c for c in a.comuni}
    a._province_regione = {c["provincia"]: c["regione"] for c in a.comuni}
    return a


def zone(regioni=(), province=(), comuni=()):
    return {"zone": {"regioni": list(regioni), "province": list(province), "comuni": list(comuni)}}


def test_risolvi_comune(archivio):
    assert archivio.risolvi_comune("milano")["codice"] == "015146"
    assert archivio.risolvi_comune("15146")["nome"] == "Milano"
    assert archivio.risolvi_comune("Castro (LE)")["codice"] == "075096"
    with pytest.raises(ErroreRicerca, match="Castro \\(BG\\), Castro \\(LE\\)"):
        archivio.risolvi_comune("Castro")
    with pytest.raises(ErroreRicerca, match="Milano"):
        archivio.risolvi_comune("Milan")


def test_disponibilita_per_comune(archivio):
    milano = archivio.risolvi_comune("Milano")
    assert archivio.disponibile_nel_comune(zone(), milano)
    assert archivio.disponibile_nel_comune(zone(regioni=["03"]), milano)
    assert archivio.disponibile_nel_comune(zone(province=["015"]), milano)
    assert archivio.disponibile_nel_comune(zone(comuni=["015146"]), milano)
    assert not archivio.disponibile_nel_comune(zone(regioni=["01"], comuni=["001272"]), milano)


def test_disponibilita_per_regione(archivio):
    assert archivio.disponibile_in_regione(zone(comuni=["075096"]), "16")
    assert archivio.disponibile_in_regione(zone(province=["016"]), "03")
    assert not archivio.disponibile_in_regione(zone(province=["016"]), "16")


def test_indici_non_piu_pubblicati_esclusi(archivio):
    archivio.prezzi_storici = [
        {"mese": "2022-09", "PUN": 0.30, "Pfor": 1.0},
        {"mese": "2026-08", "PUN": 0.18, "Pfor": None},
        {"mese": "2026-09", "PUN": 0.20, "Pfor": None},
    ]
    valori, descrizione = archivio.valori_indici()
    assert valori == {"PUN": 0.20}
    assert "2026-09" in descrizione
    media, _ = archivio.valori_indici("media_12_mesi")
    assert media["PUN"] == pytest.approx((0.30 + 0.18 + 0.20) / 3)
    assert "Pfor" not in media


def test_comuni_in_forma_d_uso_e_con_errori_di_battitura(archivio):
    assert archivio.risolvi_comune("Reggio Calabria")["codice"] == "080063"
    assert archivio.risolvi_comune("Reggio Emilia")["codice"] == "035033"
    with pytest.raises(ErroreRicerca) as errore:
        archivio.risolvi_comune("Reggio")
    assert "Reggio di Calabria (RC)" in str(errore.value)
    assert "Reggio nell'Emilia (RE)" in str(errore.value)
    assert "Greggio" not in str(errore.value)
    with pytest.raises(ErroreRicerca, match="Bologna \\(BO\\)"):
        archivio.risolvi_comune("Bolgna")


def offerta_venditore(nome, sito, piva="0123"):
    return {"venditore": nome, "piva": piva, "contatti": {"sito": sito}}


def test_venditore_cercato_senza_spazi_ne_punteggiatura(archivio):
    assert compatta("Dolomiti Energia") in compatta("www.dolomitienergia.it")
    archivio.offerte = [offerta_venditore(None, "www.dolomitienergia.it"), offerta_venditore("ACEA ENERGIA SPA", "www.acea.it", "999")]
    assert archivio.suggerisci_venditori("Dolomiti Enegia") == ["www.dolomitienergia.it"]
