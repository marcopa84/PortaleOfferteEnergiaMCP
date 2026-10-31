"""Verifica sugli open data reali: segnala in fretta se il Portale Offerte cambia formato o indirizzi."""

import pytest

from portale_offerte_mcp import sorgenti
from portale_offerte_mcp.archivio import Archivio
from portale_offerte_mcp.costi import stima

pytestmark = pytest.mark.live


@pytest.fixture(scope="module")
def archivio(tmp_path_factory):
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("PORTALE_OFFERTE_CACHE", str(tmp_path_factory.mktemp("cache")))
        a = Archivio()
        a.assicura()
        yield a


def test_tutti_i_file_scaricati(archivio):
    assert set(archivio.giornata.file) == set(sorgenti.FILE_GIORNALIERI)
    assert archivio.prezzi_storici, "CSV dei prezzi storici non trovato nella pagina Open Data"
    assert archivio.comuni, "elenco ISTAT dei comuni non scaricato"


def test_offerte_lette(archivio):
    per_tipo = {(o["commodity"], o["fonte"]) for o in archivio.offerte}
    assert {("luce", "mercato libero"), ("gas", "mercato libero"), ("luce", "PLACET"), ("gas", "PLACET")} <= per_tipo
    assert len(archivio.offerte) > 1000
    assert all(o["codice"] and o["piva"] for o in archivio.offerte)


def test_ricerca_e_stima(archivio):
    offerte, comune = archivio.cerca(commodity="luce", tipo_cliente="domestico", comune="Milano", consumo_annuo=2700)
    assert comune["codice"] == "015146"
    assert offerte
    valori, riferimento = archivio.valori_indici()
    assert "PUN" in valori and "PSV" in valori
    costi = [stima(o, 2700, archivio.parametri["luce"], valori, riferimento)["costo_vendita_anno"] for o in offerte]
    assert sum(c > 0 for c in costi) > len(costi) * 0.9
