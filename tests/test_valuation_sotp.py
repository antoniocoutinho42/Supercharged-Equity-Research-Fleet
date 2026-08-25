import json
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures"
sys.path.insert(0, str(RAIZ / "skills" / "er-valuation" / "scripts"))
from caso import CasoInvalido, validar  # noqa: E402
from sotp import compor_partes  # noqa: E402


def _sotp() -> dict:
    return json.loads((FIXTURES / "caso_sotp_segmento.json").read_text(encoding="utf-8"))


def _safra() -> dict:
    return json.loads((FIXTURES / "caso_sotp_safra.json").read_text(encoding="utf-8"))


def test_cada_parte_e_avaliada_com_a_propria_convencao():
    r = compor_partes(_sotp(), "base")
    convs = {p["nome"]: p["premissas"]["tv"] for p in r["partes"]}
    assert convs == {"Industrial": "convergencia", "Serviços": "gordon"}


def test_ev_total_e_a_soma_das_partes_menos_o_topo():
    r = compor_partes(_sotp(), "base")
    soma = sum(p["EV"] for p in r["partes"])
    assert r["ev_das_partes"] == pytest.approx(soma)
    assert r["ev_total"] == pytest.approx(soma - 400.0)


def test_a_ponte_atravessa_uma_vez_so():
    """Ponte por parte e o erro que a trava existe para impedir."""
    r = compor_partes(_sotp(), "base")
    for p in r["partes"]:
        assert "Equity" not in p and "preco_acao" not in p
    assert r["ponte_unica"]["nd_efetivo"] == pytest.approx(500.0)
    assert r["equity"] == pytest.approx(r["ev_total"] - 500.0)
    assert r["preco_acao"] == pytest.approx(r["equity"] / 100.0)


def test_desconto_de_holding_sem_razao_recusa():
    c = _sotp()
    c["sotp"]["topo"]["desconto_de_holding_pct"] = 15.0
    with pytest.raises(CasoInvalido, match="razão"):
        validar(c)


def test_desconto_de_holding_com_razao_e_aplicado_e_declarado():
    c = _sotp()
    c["sotp"]["topo"]["desconto_de_holding_pct"] = 15.0
    c["sotp"]["topo"]["razao_do_desconto"] = "controlador com histórico de não distribuir"
    r = compor_partes(c, "base")
    assert r["topo"]["desconto_de_holding_pct"] == 15.0
    assert r["topo"]["razao_do_desconto"]


def test_parte_sem_ancora_ou_triangulo_recusa():
    for campo in ("ancora", "triangulo"):
        c = _sotp()
        del c["sotp"]["partes"][0][campo]
        with pytest.raises(CasoInvalido, match=campo.replace("ancora", "âncora")):
            validar(c)


def test_sotp_com_uma_parte_so_recusa():
    """Soma de uma parte e o consolidado com passos a mais."""
    c = _sotp()
    c["sotp"]["partes"] = c["sotp"]["partes"][:1]
    with pytest.raises(CasoInvalido, match="partes"):
        validar(c)


def test_nomes_de_parte_repetidos_recusam():
    c = _sotp()
    c["sotp"]["partes"][1]["nome"] = c["sotp"]["partes"][0]["nome"]
    with pytest.raises(CasoInvalido, match="nome"):
        validar(c)


def test_diagnosticos_de_cada_parte_chegam():
    r = compor_partes(_sotp(), "base")
    assert all(p["diagnosticos"] for p in r["partes"])
