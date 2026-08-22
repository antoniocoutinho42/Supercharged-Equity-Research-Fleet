import json
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures"
sys.path.insert(0, str(RAIZ / "skills" / "er-valuation" / "scripts"))
from caso import carregar  # noqa: E402
from reversa import alvo_de_mercado, reverter  # noqa: E402


def _caso() -> dict:
    return carregar(FIXTURES / "caso_reversa_firm.json")


def test_alvo_e_o_multiplo_de_mercado_com_algebra_declarada():
    # preco 55 x 100 acoes = 5500 de market cap; + nd 500 = EV 6000; / EBITDA 1000 = 6,0x
    alvo = alvo_de_mercado(_caso(), "base", 500.0)
    assert alvo["valor"] == pytest.approx(6.0)
    assert "6000" in alvo["algebra"] or "6.000" in alvo["algebra"]
    assert alvo["base"] == "ebitda"


def test_custo_de_capital_implicito_tem_raiz_e_identificacao():
    r = reverter(_caso(), "base", 500.0)
    eixo = r["eixos"]["custo_capital"]
    raizes = eixo["raizes_wacc_%"]
    assert raizes and all(isinstance(x, float) for x in raizes)
    assert eixo["identificacao_por_raiz"]


def test_beta_implicito_sai_do_capm_com_algebra():
    r = reverter(_caso(), "base", 500.0)
    b = r["eixos"]["custo_capital"]["beta_implicito"]
    wacc = r["eixos"]["custo_capital"]["raizes_wacc_%"][0]
    assert b["valor"] == pytest.approx((wacc - 12.0) / 5.5, abs=1e-6)
    assert "12" in b["algebra"] and "5,5" in b["algebra"].replace(".", ",")


def test_beta_implicito_diz_a_posicao_contra_a_banda():
    r = reverter(_caso(), "base", 500.0)
    b = r["eixos"]["custo_capital"]["beta_implicito"]
    assert b["posicao_na_banda"] in ("dentro", "abaixo", "acima")
    assert "distancia" in b


def test_beta_implicito_so_existe_no_eixo_de_custo_de_capital():
    r = reverter(_caso(), "base", 500.0)
    for nome, eixo in r["eixos"].items():
        if nome != "custo_capital":
            assert "beta_implicito" not in eixo


def test_diagnosticos_do_motor_chegam_integros():
    r = reverter(_caso(), "base", 500.0)
    eixo = r["eixos"]["custo_capital"]
    assert eixo["premissas_fixadas"]["nota"]
    assert isinstance(eixo["guardas_v9_4"], list)
    assert eixo["faixa_de_busca"]["variavel"] == "wacc"


def test_alvo_base_corrente_e_declarado_explicitamente():
    """Tela NTM contra base corrente injeta erro de (1+g); a base vai declarada."""
    r = reverter(_caso(), "base", 500.0)
    assert "corrente" in r["eixos"]["custo_capital"]["base_do_alvo"]


def test_eixo_sem_raiz_preserva_sem_solucao_e_sugestao():
    c = _caso()
    c["preco"]["valor"] = 900.0  # alvo absurdo: nenhum eixo primario fecha
    r = reverter(c, "base", 500.0)
    rent = r["eixos"]["rentabilidade"]
    assert rent["raizes_roic_%"] == []
    assert "sem_solucao" in rent and "máximo atingível" in rent["sem_solucao"]
    assert "sugestao" in rent and "TETO DO CRESCIMENTO GRATUITO" in rent["sugestao"]


def test_todos_os_eixos_declarados_sao_rodados():
    r = reverter(_caso(), "base", 500.0)
    assert set(r["eixos"]) == {"custo_capital", "crescimento", "rentabilidade", "cap"}


def test_eixo_cap_passa_com_shape_proprio():
    """O motor devolve CAP_implicito_anos, nao raizes_* — repassar, nao uniformizar."""
    cap = reverter(_caso(), "base", 500.0)["eixos"]["cap"]
    assert "CAP_implicito_anos" in cap
    assert not any(k.startswith("raizes") for k in cap)
    assert cap["faixa_de_busca"]["variavel"] == "cap(n)"


def test_cap_inalcancavel_chega_como_string_sem_quebrar():
    """CAP_implicito_anos vira STRING quando o alvo esta fora de 1-60 anos."""
    c = _caso()
    c["preco"]["valor"] = 70.0
    cap = reverter(c, "base", 500.0)["eixos"]["cap"]
    assert isinstance(cap["CAP_implicito_anos"], (float, int, str))


def test_teto_roda_quando_eixo_primario_nao_fecha():
    c = _caso()
    c["preco"]["valor"] = 900.0
    r = reverter(c, "base", 500.0)
    teto = r["teto_do_crescimento_gratuito"]
    assert teto["multiplo"] > 0
    assert "RiR" in teto["leitura"] or "reinvestimento" in teto["leitura"]


def test_teto_nao_roda_quando_todos_os_eixos_fecham():
    r = reverter(_caso(), "base", 500.0)
    assert "teto_do_crescimento_gratuito" not in r


def test_teto_e_insensivel_a_escolha_do_infinito():
    """A constante e uma aproximacao numerica; se o resultado depender dela, e invencao."""
    import reversa as mod
    c = _caso()
    c["preco"]["valor"] = 900.0
    valores = []
    original = mod.RENTABILIDADE_TERMINAL_INFINITA
    try:
        for grande in (1e5, 1e6, 1e7):
            mod.RENTABILIDADE_TERMINAL_INFINITA = grande
            valores.append(mod.teto_do_crescimento_gratuito(c, "base", 500.0)["multiplo"])
    finally:
        mod.RENTABILIDADE_TERMINAL_INFINITA = original
    # medido contra o vendor: 1e5 -> 10.6467, 1e6 -> 10.647, 1e7 -> 10.647
    assert max(valores) - min(valores) < 0.01, valores


def test_teto_declara_as_premissas_que_alterou():
    c = _caso()
    c["preco"]["valor"] = 900.0
    teto = reverter(c, "base", 500.0)["teto_do_crescimento_gratuito"]
    assert teto["premissas_alteradas"]["tv"] == "gordon"
    assert teto["premissas_alteradas"]["gp"] == c["cenarios"]["base"]["premissas"]["g"]


def test_teto_e_maior_que_o_multiplo_do_caso_base():
    """Nenhuma historia de crescimento PAGO chega ao teto do crescimento gratuito."""
    c = _caso()
    c["preco"]["valor"] = 900.0
    r = reverter(c, "base", 500.0)
    from motor import rodar
    base = rodar("firm", c["cenarios"]["base"]["premissas"], None)
    assert r["teto_do_crescimento_gratuito"]["multiplo"] > base["EV/EBITDA_curr"]
