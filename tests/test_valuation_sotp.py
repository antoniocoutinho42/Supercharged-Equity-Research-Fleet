import json
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures"
sys.path.insert(0, str(RAIZ / "skills" / "er-valuation" / "scripts"))
from caso import CasoInvalido, carregar, validar  # noqa: E402
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
    """Debt (a) da revisão da Task 2: o teste original só checava que o
    desconto é DECLARADO na saída, nunca que é de fato APLICADO — um bug
    que multiplicasse pelo fator errado (ou não multiplicasse nada) teria
    passado pelo teste antigo sem ser pego. Números conferidos manualmente
    na fixture do segmento: equity antes ~6378.83 -> x0.85 -> ~5422.0055
    -> /100 ações -> ~54.220055."""
    c = _sotp()
    c["sotp"]["topo"]["desconto_de_holding_pct"] = 15.0
    c["sotp"]["topo"]["razao_do_desconto"] = "controlador com histórico de não distribuir"
    r = compor_partes(c, "base")
    assert r["topo"]["desconto_de_holding_pct"] == 15.0
    assert r["topo"]["razao_do_desconto"]
    equity_antes = r["topo"]["equity_antes_do_desconto_de_holding"]
    equity_depois = r["topo"]["equity_depois_do_desconto_de_holding"]
    assert equity_depois == pytest.approx(equity_antes * 0.85)
    assert r["equity"] == pytest.approx(equity_depois)
    assert r["preco_acao"] == pytest.approx(equity_depois / c["acoes_diluidas"])


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


# --------------------------------------------------------------------------
# Debt (b) da revisão da Task 2: o sinal '+' de participacoes_nao_consolidadas
# nunca era exercitado -- a fixture do segmento declara 0.0, então um sinal
# trocado (subtrair em vez de somar) seria invisível a qualquer teste
# existente antes desta task.
# --------------------------------------------------------------------------

def test_participacoes_nao_consolidadas_soma_com_sinal_positivo():
    c = _sotp()
    c["sotp"]["topo"]["participacoes_nao_consolidadas"] = 120.0
    r = compor_partes(c, "base")
    soma = sum(p["EV"] for p in r["partes"])
    custos = c["sotp"]["topo"]["custos_corporativos_vp"]
    assert r["ev_total"] == pytest.approx(soma - custos + 120.0)


# --------------------------------------------------------------------------
# Debt (d) da revisão da Task 2: compor_partes aceitava qualquer
# nome_cenario e o ignorava -- compor_partes(caso, "bear") e
# compor_partes(caso, "bull") devolviam, em silêncio, os mesmos números.
# --------------------------------------------------------------------------

def test_compor_partes_recusa_nome_de_cenario_inexistente():
    """Partes de SOTP carregam um vetor de premissas fixo, nunca por
    cenário -- a guarda existe só para que um nome inexistente falhe alto,
    em vez de devolver os mesmos números de qualquer outro nome."""
    c = _sotp()
    with pytest.raises(CasoInvalido, match="cenário"):
        compor_partes(c, "nao_existe")


# --------------------------------------------------------------------------
# Fatia C, Task 4: 'sotp.cenario' -- campo novo do contrato, mesma
# semântica e mesma função de validação (_validar_cenario_alvo) que
# 'reversa.cenario'/'sensibilidades.cenario' já usam. avaliar() passa este
# nome para compor_partes, que já recusava (desde a Task 2/3, teste acima)
# um nome inexistente -- mas antes desta task não havia como declará-lo no
# caso; a fixture do segmento (e as da safra/homogêneo) ganharam o campo
# junto com esta task.
# --------------------------------------------------------------------------

def test_sotp_sem_cenario_recusa():
    c = _sotp()
    del c["sotp"]["cenario"]
    with pytest.raises(CasoInvalido, match="cenario"):
        validar(c)


def test_sotp_com_cenario_inexistente_recusa_no_gate():
    """Mesma guarda de compor_partes (teste acima), agora também no
    portão de caso.validar -- um caso.json malformado assim nunca chega a
    avaliar()/compor_partes."""
    c = _sotp()
    c["sotp"]["cenario"] = "nao_existe"
    with pytest.raises(CasoInvalido, match="inexistente"):
        validar(c)


# --------------------------------------------------------------------------
# Fatia C, Task 3: materialidade -- quando o caso declara
# sotp.materialidade.blended, o vetor consolidado roda pela mesma rota do
# caso e a saída reporta EV_segmentado - EV_blended, com sinal. A direção
# do viés se calcula (o múltiplo não é linear), não se deduz.
# --------------------------------------------------------------------------

def test_materialidade_reporta_a_diferenca_com_sinal():
    """A direcao do vies se calcula, nao se deduz.

    FIX 4 (revisão final): sem pinar `ev_segmentado`/`ev_blended` contra um
    número calculado por fora, um mutante que devolvesse `ev_das_partes *
    1.05` no lugar do EV real do vetor blended sobrevivia a suíte inteira —
    o assert de `diferenca` é uma tautologia sobre o PRÓPRIO dict que
    `materialidade()` devolve (ela sempre bate consigo mesma, mutante ou
    não). `ev_segmentado` é a SOMA das partes (D3) — pinado igual a
    `ev_das_partes`, NUNCA `ev_total` (a docstring de `materialidade` é
    explícita: os ajustes de topo são ponte-adjacentes, fora da pergunta
    "segmentar muda o preço?"). Os dois números vêm de rodar o motor de
    verdade sobre a fixture do segmento (conferido por fora deste teste).
    """
    r = compor_partes(_sotp(), "base")
    m = r["materialidade"]
    assert m["diferenca"] == pytest.approx(m["ev_segmentado"] - m["ev_blended"])
    assert m["sinal"] in ("+", "-", "0")
    assert m["ev_segmentado"] == pytest.approx(7278.83, abs=0.01)
    assert m["ev_segmentado"] == pytest.approx(r["ev_das_partes"], abs=0.01)
    assert m["ev_blended"] == pytest.approx(6973.93, abs=0.01)


def test_materialidade_sinal_positivo_e_leitura_da_fixture_padrao():
    """O teste acima só checa o enum genérico -- este pina o sinal
    concreto que a fixture do segmento produz: segmentado acima do
    blended, o consolidado SUBESTIMA."""
    r = compor_partes(_sotp(), "base")
    m = r["materialidade"]
    assert m["sinal"] == "+"
    assert "subestima" in m["leitura"]


def test_materialidade_sinal_negativo_quando_blended_excede_segmentado():
    """Pina o outro lado do sinal: um blended com retorno muito acima de
    qualquer parte segmentada vale mais que a soma das partes -- sinal
    '-', o consolidado SUPERESTIMA."""
    c = _sotp()
    c["sotp"]["materialidade"]["blended"]["premissas"]["roic"] = 30.0
    r = compor_partes(c, "base")
    m = r["materialidade"]
    assert m["sinal"] == "-"
    assert "superestima" in m["leitura"]


def test_materialidade_ausente_quando_o_caso_nao_declara_blended():
    c = _sotp()
    del c["sotp"]["materialidade"]
    assert compor_partes(c, "base").get("materialidade") is None


def test_materialidade_sem_blended_recusa():
    c = _sotp()
    del c["sotp"]["materialidade"]["blended"]
    with pytest.raises(CasoInvalido, match="materialidade"):
        validar(c)


def test_materialidade_blended_sem_ancora_recusa():
    c = _sotp()
    del c["sotp"]["materialidade"]["blended"]["ancora"]
    with pytest.raises(CasoInvalido, match="âncora"):
        validar(c)


def test_fixture_sotp_segmento_e_valida():
    """Confirma que a fixture do segmento -- que já carrega um bloco
    materialidade.blended válido -- passa pelo portão completo, não só
    pelo caminho feliz de compor_partes (que não revalida)."""
    assert carregar(FIXTURES / "caso_sotp_segmento.json")["sotp"]["tipo"] == "segmento"


# --------------------------------------------------------------------------
# Fatia C, Task 3: a parede da safra -- tipo "safra" exige exatamente uma
# parte na rota rampa (a base instalada); toda outra parte é capital novo,
# pelo fluxo padrão. Zero ou duas rampas recusam, com o motivo nomeado.
# --------------------------------------------------------------------------

def test_safra_exige_exatamente_uma_parte_em_rampa():
    """Parede: a instalada e SO rampa, a expansao e SO capital novo."""
    c = _sotp()
    c["sotp"]["tipo"] = "safra"
    with pytest.raises(CasoInvalido, match="rampa"):
        validar(c)


def test_safra_com_duas_rampas_recusa():
    c = _safra()
    c["sotp"]["partes"][1]["rota"] = "rampa"
    c["sotp"]["partes"][1]["premissas"] = dict(c["sotp"]["partes"][0]["premissas"])
    c["sotp"]["partes"][1]["metrica_base"] = {"tipo": "EBITDA0", "valor": 10.0, "fonte": "x"}
    with pytest.raises(CasoInvalido, match="rampa"):
        validar(c)


def test_fixture_safra_e_valida():
    assert carregar(FIXTURES / "caso_sotp_safra.json")["sotp"]["tipo"] == "safra"


# --------------------------------------------------------------------------
# Consequência de contrato (ver módulo/brief): na rota rampa do CASO
# inteiro, 'delimitador' é campo de topo; quando a rampa é uma PARTE de
# SOTP, o delimitador é campo DELA -- mesma regra, mesma mensagem.
# --------------------------------------------------------------------------

def test_parte_rampa_sem_delimitador_recusa():
    c = _safra()
    del c["sotp"]["partes"][0]["delimitador"]
    with pytest.raises(CasoInvalido, match="delimitador"):
        validar(c)


def test_parte_firm_com_delimitador_recusa():
    c = _safra()
    c["sotp"]["partes"][1]["delimitador"] = "não deveria estar aqui"
    with pytest.raises(CasoInvalido, match="delimitador"):
        validar(c)


# --------------------------------------------------------------------------
# Debt (c) da revisão da Task 2: nenhum teste comprometido exercitava uma
# parte de SOTP na rota rampa -- a fixture da safra fecha isso por
# construção. EV da parte em rampa confrontado contra a mesma âncora do
# vendor que test_rodar_rampa_reproduz_a_ancora_do_motor já trava
# (170.9304), porque a parte usa as mesmas premissas de caso_rampa.json.
# --------------------------------------------------------------------------

def test_safra_parte_em_rampa_bate_a_ancora_do_vendor():
    r = compor_partes(_safra(), "base")
    partes_por_rota = {p["rota"]: p for p in r["partes"]}
    assert set(partes_por_rota) == {"rampa", "firm"}
    assert partes_por_rota["rampa"]["EV"] == pytest.approx(170.9304, abs=1e-2)
    assert r["ev_das_partes"] == pytest.approx(
        partes_por_rota["rampa"]["EV"] + partes_por_rota["firm"]["EV"])


# --------------------------------------------------------------------------
# Fatia C, Task 3: a identidade dos claims homogêneos -- para um vetor de
# premissas o múltiplo não depende da escala, então duas partes com
# premissas idênticas e métricas m1, m2 somam exatamente o consolidado em
# m1+m2. É identidade, não aproximação: uma falha aqui é erro de
# composição, nunca motivo para afrouxar a tolerância.
# --------------------------------------------------------------------------

def test_fixture_homogeneo_e_valida():
    assert carregar(FIXTURES / "caso_sotp_homogeneo.json")["sotp"]["tipo"] == "segmento"


def test_claims_homogeneos_somam_exatamente_o_consolidado():
    """Identidade, nao aproximacao: para um vetor de premissas o multiplo nao
    depende da escala, entao mult*m1 + mult*m2 = mult*(m1+m2)."""
    r = compor_partes(carregar(FIXTURES / "caso_sotp_homogeneo.json"), "base")
    from motor import rodar
    partes = carregar(FIXTURES / "caso_sotp_homogeneo.json")["sotp"]["partes"]
    soma_metrica = sum(p["metrica_base"]["valor"] for p in partes)
    consolidado = rodar("firm", partes[0]["premissas"],
                        {"ebitda": soma_metrica, "nd": 0.0, "acoes": 1.0})
    assert r["ev_das_partes"] == pytest.approx(consolidado["EV"], abs=0.01)


# --------------------------------------------------------------------------
# Revisão final (task 3c), FIX 6c: `compor_partes` ecoa `cenario` no bloco
# devolvido -- antes, um leitor de resultados.json via sotp não tinha como
# saber, olhando só o bloco 'sotp', qual cenário foi nomeado (a chave só
# existia no INPUT, `caso["sotp"]["cenario"]`, nunca no output).
# --------------------------------------------------------------------------

def test_compor_partes_ecoa_o_nome_do_cenario():
    r = compor_partes(_sotp(), "base")
    assert r["cenario"] == "base"


# --------------------------------------------------------------------------
# Revisão final (task 3c), FIX 6e: colisão de ordenação no loop de repasse
# íntegro de `_compor_parte` -- uma chave nova do motor que algum dia
# colidisse com um campo AUTORADO da parte (nome, rota, metrica_base,
# ancora, premissas, algebra_da_escala, triangulo) sobrescreveria esse
# campo em silêncio; hoje nenhuma colisão existe (o motor não emite
# nenhum desses nomes) -- este teste MANUFATURA uma via monkeypatch para
# provar que a guarda (`chave in resultado`) segura, não apenas documenta
# a intenção.
# --------------------------------------------------------------------------

def test_parte_com_chave_do_motor_colidindo_com_campo_autorado_nao_sobrescreve(monkeypatch):
    def _rodar_fake(rota, premissas, escala, moeda=None, subcomando=None, rf=None):
        return {
            "EV": 999.0, "EV/EBITDA_curr": 6.0, "diagnosticos": [],
            "nome": "CLOBBERED-PELO-MOTOR",  # colisão manufaturada
        }

    monkeypatch.setattr("avaliar.rodar", _rodar_fake)
    r = compor_partes(_sotp(), "base")
    nomes = {p["nome"] for p in r["partes"]}
    assert nomes == {"Industrial", "Serviços"}
    assert "CLOBBERED-PELO-MOTOR" not in nomes
