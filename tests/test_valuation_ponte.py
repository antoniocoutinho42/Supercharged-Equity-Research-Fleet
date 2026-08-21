import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "skills" / "er-valuation" / "scripts"))
from ponte import compor  # noqa: E402

PONTE = {"divida_bruta": 800.0, "caixa_e_equivalentes": 300.0,
         "outros_ativos": 50.0, "outros_passivos": 20.0, "minoritarios": 100.0}


def test_nd_efetivo_e_a_soma_com_sinal():
    # 800 - 300 + 100 + 20 - 50 = 570
    assert compor(PONTE)["nd_efetivo"] == pytest.approx(570.0)


def test_caixa_liquido_produz_nd_negativo():
    p = dict(PONTE, divida_bruta=0.0, caixa_e_equivalentes=500.0,
             outros_ativos=0.0, outros_passivos=0.0, minoritarios=0.0)
    assert compor(p)["nd_efetivo"] == pytest.approx(-500.0)


def test_parcelas_cobrem_todas_as_linhas_com_sinal():
    parcelas = compor(PONTE)["parcelas"]
    assert [p["rotulo"] for p in parcelas] == [
        "divida_bruta", "caixa_e_equivalentes", "outros_ativos",
        "outros_passivos", "minoritarios"]
    sinais = {p["rotulo"]: p["sinal"] for p in parcelas}
    assert sinais["divida_bruta"] == 1 and sinais["minoritarios"] == 1
    assert sinais["caixa_e_equivalentes"] == -1 and sinais["outros_ativos"] == -1


def test_soma_das_parcelas_reconstroi_o_nd_efetivo():
    """A parcela exibida no waterfall e a MESMA que entra na conta."""
    r = compor(PONTE)
    assert sum(p["valor"] * p["sinal"] for p in r["parcelas"]) == pytest.approx(r["nd_efetivo"])


def test_ponte_zerada_produz_nd_zero():
    assert compor({k: 0.0 for k in PONTE})["nd_efetivo"] == pytest.approx(0.0)


def test_linha_ausente_e_erro_nao_zero_implicito():
    p = dict(PONTE)
    del p["minoritarios"]
    with pytest.raises(KeyError):
        compor(p)
