"""Contrato `resultados/1` (fatia 5A, item 5, Task 1).

Ver docs/superpowers/plans/2026-09-11-v4-item5a-contratos-builder.md, seção
"Task 1", para as seis regras do contrato. Os testes abaixo discriminam a
matemática (hash canônico, múltiplo de tela por rota) e o contrato (versão,
origem, manchete, diagnósticos classificados, cenário-base) — não repetem
metodologia, que já é coberta por `tests/test_valuation_*.py`.
"""

import hashlib
import json
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
FIXTURES = RAIZ / "tests" / "fixtures"
sys.path.insert(0, str(RAIZ / "skills" / "er-valuation" / "scripts"))
from avaliar import avaliar  # noqa: E402
from caso import CasoInvalido, carregar, validar  # noqa: E402
import diagnosticos  # noqa: E402

CASOS = sorted(p.name for p in FIXTURES.glob("caso_*.json"))
MANIFEST = json.loads((RAIZ / "skills" / "er-multiplos-justos" / "manifest_vendor.json").read_text(encoding="utf-8"))


def _sha(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False).encode("utf-8")).hexdigest()


@pytest.fixture(scope="module")
def resultados():
    return {nome: (carregar(FIXTURES / nome), avaliar(carregar(FIXTURES / nome))) for nome in CASOS}


def test_versao_e_origem_em_todo_resultado(resultados):
    for nome, (caso, r) in resultados.items():
        assert r["versao_contrato"] == "resultados/1", nome
        assert r["origem"]["caso_sha256"] == _sha(caso), nome
        assert r["origem"]["metodologia"] == {"nome": "multiplos-justos", "versao": MANIFEST["versao"]}, nome


def test_hash_ignora_ordem_de_chaves_do_arquivo(tmp_path):
    caso = json.loads((FIXTURES / "caso_minimo_firm.json").read_text(encoding="utf-8"))
    invertido = tmp_path / "caso.json"
    invertido.write_text(json.dumps(dict(reversed(list(caso.items()))), indent=4), encoding="utf-8")
    assert avaliar(carregar(invertido))["origem"]["caso_sha256"] == _sha(caso)


def test_diagnosticos_chaves_paralelas_e_classificadas(resultados):
    for nome, (_caso, r) in resultados.items():
        for cen, reg in r["cenarios"].items():
            if "diagnosticos" in reg:
                assert len(reg["diagnosticos_chaves"]) == len(reg["diagnosticos"]), (nome, cen)
                assert reg["diagnosticos_chaves"] == [diagnosticos.classificar(m) for m in reg["diagnosticos"]]
            assert None not in reg["diagnosticos_chaves"], (nome, cen)


def test_manchete_aponta_um_preco_que_existe(resultados):
    for nome, (caso, r) in resultados.items():
        m = r["manchete"]
        if "sotp" in caso:
            assert m["fonte"] == "sotp" and m["preco_acao"] == r["sotp"]["preco_acao"] and "multiplo" not in m
        else:
            assert m["fonte"] == "cenarios"
            assert m["preco_acao"] == r["cenarios"][m["cenario"]]["valor"]["preco_acao"]
        assert m["upside"] == m["preco_acao"] / caso["preco"]["valor"] - 1, nome


def test_mercado_tela_da_rampa_e_do_lado_do_ev():
    caso = carregar(FIXTURES / "caso_rampa.json")
    tela = avaliar(caso)["mercado_tela"]
    assert tela["base"] == "ebitda0"
    ev_mercado = caso["preco"]["valor"] * caso["acoes_diluidas"] + avaliar(caso)["ponte"]["nd_efetivo"]
    assert tela["valor"] == ev_mercado / caso["metrica_base"]["valor"]


def test_cenario_base_obrigatorio_com_mais_de_um_cenario():
    caso = json.loads((FIXTURES / "caso_minimo_firm.json").read_text(encoding="utf-8"))
    caso["cenarios"]["bull"] = caso["cenarios"]["base"]
    with pytest.raises(CasoInvalido, match="cenario_base"):
        validar(caso)
    caso["cenario_base"] = "inexistente"
    with pytest.raises(CasoInvalido, match="cenario_base"):
        validar(caso)
    caso["cenario_base"] = "base"
    validar(caso)


# --------------------------------------------------------------------------
# Casos extras listados pelo plano: mercado_tela para firm, equity e degrau;
# recusa de cenario_base de tipo errado.
# --------------------------------------------------------------------------

def test_mercado_tela_do_firm_bate_no_caso_reversa_firm():
    """O mesmo 6.0 que `alvo_de_mercado`/`reversa.reverter` já produzem para
    esta fixture (`tests/test_valuation_reversa.py`) — `mercado_tela` publica
    o MESMO número, agora sempre, fora do bloco `reversa`."""
    caso = carregar(FIXTURES / "caso_reversa_firm.json")
    tela = avaliar(caso)["mercado_tela"]
    assert tela["base"] == "ebitda"
    assert tela["chave"] == "EV/EBITDA_curr"
    assert tela["valor"] == pytest.approx(6.0)


def test_mercado_tela_do_equity_e_market_cap_sobre_ll():
    caso = carregar(FIXTURES / "caso_minimo_equity.json")
    tela = avaliar(caso)["mercado_tela"]
    assert tela["base"] == "pl"
    assert tela["chave"] == "PL_curr"
    market_cap = caso["preco"]["valor"] * caso["acoes_diluidas"]
    assert tela["valor"] == pytest.approx(market_cap / caso["metrica_base"]["valor"])


def test_mercado_tela_do_degrau_e_pvp_observado_contra_pvp_com_degrau():
    """A tela usa o P/VP OBSERVADO (preco/vpa, sem passar pelo motor); a
    manchete usa o P/VP JUSTO (PVP_com_degrau). As duas bases são 'pvp' — é
    assim que o relatório pareia os dois — mas as chaves são deliberadamente
    diferentes."""
    caso = carregar(FIXTURES / "caso_degrau.json")
    r = avaliar(caso)
    tela = r["mercado_tela"]
    assert tela["chave"] == "PVP"
    assert tela["base"] == "pvp"
    assert tela["valor"] == pytest.approx(caso["preco"]["valor"] / caso["degrau"]["vpa"]["valor"])

    manchete = r["manchete"]
    assert manchete["multiplo"]["chave"] == "PVP_com_degrau"
    assert manchete["multiplo"]["base"] == "pvp"
    assert manchete["multiplo"]["valor"] == pytest.approx(
        r["cenarios"]["base"]["degrau"]["com_transicao"])


def test_cenario_base_de_tipo_errado_e_recusado():
    caso = json.loads((FIXTURES / "caso_minimo_firm.json").read_text(encoding="utf-8"))
    caso["cenario_base"] = 123
    with pytest.raises(CasoInvalido, match="cenario_base"):
        validar(caso)
