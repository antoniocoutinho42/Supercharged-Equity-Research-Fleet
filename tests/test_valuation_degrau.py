"""Fatia D, Task 1: `degrau` (Gate 3 — capacidade ociosa de balanço) no
wrapper. Seis testes que discriminam a matemática e o contrato — ver
docs/superpowers/plans/2026-09-10-v4-fatia-degrau.md, seção "Task 1".

Metodologia (não repetida aqui): `vendor/multiplos-justos/references/
aplicacao.md` §8. Implementação de referência: `elif a.cmd == 'degrau'` em
`vendor/multiplos-justos/scripts/justos.py`.
"""

import copy
import json
import re
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures"
sys.path.insert(0, str(RAIZ / "skills" / "er-valuation" / "scripts"))

from avaliar import avaliar, precificar_degrau  # noqa: E402
from caso import CasoInvalido, validar  # noqa: E402
from motor import executar as _motor_executar  # noqa: E402


def _carregado(nome: str) -> dict:
    return json.loads((FIXTURES / nome).read_text(encoding="utf-8"))


# --------------------------------------------------------------------------
# Caso âncora: o exemplo do SKILL.md do vendor (`vendor/multiplos-justos/
# SKILL.md:265`) — `--indice-atual 19.3 --indice-alvo 16,14,13,11 --m 100
# --anos 4 --perfil-transicao rampa --roe 20 --ke 20 --g 12 --n 10 --tv
# gordon --roe-tv 20 --gp 6.5 [--vpa 29.11 --fx 5.115]` — com um único
# índice-alvo (14, o terceiro da lista; D3: um preço por cenário, nunca um
# terceiro preço concorrente) e `--vpa` acrescentado (mandatório no bloco
# do wrapper, opcional na CLI crua); `--fx` fica em 1.0 (dentro do
# colchete opcional do exemplo), não no 5.115 da CLI.
# --------------------------------------------------------------------------

def _caso_ancora() -> dict:
    return {
        "companhia": "Financeira Sintética Degrau S.A.",
        "ticker": "FSDG4",
        "moeda": "BRL-nominal",
        "data_analise": "2026-09-11",
        "preco": {"valor": 40.0, "fonte": "fixture do teste", "data": "2026-09-11"},
        "rota": "equity",
        "metrica_base": {"tipo": "LL", "valor": 500.0, "fonte": "fixture do teste"},
        "acoes_diluidas": 100.0,
        "cenarios": {
            "base": {
                "ancora": "consenso t+1, 9 analistas",
                "triangulo": {"inputs": ["g", "roe"], "output": "rir"},
                "premissas": {"g": 12.0, "roe": 20.0, "ke": 20.0, "n": 10,
                              "tv": "gordon", "roe_tv": 20.0, "gp": 6.5},
            },
        },
        "degrau": {
            "indice_atual": {"valor": 19.3, "fonte": "fixture do teste", "data": "2026-06-30"},
            "piso_teorico": 11.0,
            "indice_alvo": {"valor": 14.0,
                             "razao": "piso administrável: mínimo regulatório + buffer"},
            "anos": 4,
            "perfil_transicao": "rampa",
            "razao_transicao": "deployment gradual em tranches anuais",
            "vpa": {"valor": 29.11, "fonte": "fixture do teste", "data": "2026-06-30"},
            "fx": 1.0,
            "m": {"base": {"valor": 100.0, "razao": "eficiência marginal plena"}},
        },
    }


# argv literal do SKILL.md do vendor, digitado à mão (não reconstruído a
# partir do código do wrapper — é isso que faz deste teste uma âncora de
# verdade, não uma tautologia).
_ARGV_ANCORA_SKILL_MD = [
    "degrau",
    "--indice-atual", "19.3", "--indice-alvo", "14",
    "--m", "100", "--anos", "4", "--perfil-transicao", "rampa",
    "--roe", "20", "--ke", "20", "--g", "12", "--n", "10",
    "--tv", "gordon", "--roe-tv", "20", "--gp", "6.5",
    "--vpa", "29.11",
]


def test_1_ancora_bate_com_a_cli_do_motor_para_os_mesmos_argumentos():
    """O que `avaliar()` grava em `cenarios.base.{valor.preco_acao, degrau}`
    e em `resultado.degrau.travas_obrigatorias` bate, campo a campo, com a
    saída de rodar a CLI do motor congelado com os MESMOS argumentos do
    exemplo do SKILL.md — inclusive `divergencia_de_base_%` (D8), montada
    aqui a partir de DUAS chamadas de referência independentes (o nível
    h=1 do degrau e a rota `pe`), nunca de uma multiplicação própria deste
    teste."""
    referencia = _motor_executar(_ARGV_ANCORA_SKILL_MD)
    nivel_ref = referencia["niveis"][0]

    resultado = avaliar(_caso_ancora())
    cenario = resultado["cenarios"]["base"]
    degrau = cenario["degrau"]

    assert cenario["valor"]["preco_acao"] == pytest.approx(nivel_ref["preco_acao"])
    assert degrau["h"] == pytest.approx(nivel_ref["h"])
    assert degrau["rentabilidade_pos_%"] == pytest.approx(nivel_ref["rentabilidade_pos_%"])
    assert degrau["multiplo"] == pytest.approx(nivel_ref["multiplo"])
    assert degrau["multiplo_x_rentab"] == pytest.approx(nivel_ref["multiplo_x_rentab"])
    assert degrau["com_transicao"] == pytest.approx(nivel_ref["com_transicao"])
    assert degrau["fator_transicao"] == pytest.approx(nivel_ref["fator_transicao"])
    assert degrau["perfil_transicao"] == nivel_ref["perfil_transicao"]
    assert degrau["m"] == pytest.approx(100.0)
    assert "ALERTA" not in degrau and "ALERTA_RiR" not in degrau
    assert resultado["degrau"]["travas_obrigatorias"] == referencia["travas_obrigatorias"]

    ref_h1 = _motor_executar([
        "degrau", "--indice-atual", "19.3", "--indice-alvo", "19.3",
        "--m", "100", "--anos", "4", "--perfil-transicao", "rampa",
        "--roe", "20", "--ke", "20", "--g", "12", "--n", "10",
        "--tv", "gordon", "--roe-tv", "20", "--gp", "6.5", "--vpa", "29.11",
    ])
    ref_sem_degrau = _motor_executar([
        "pe", "--g", "12", "--roe", "20", "--ke", "20", "--n", "10",
        "--tv", "gordon", "--roe-tv", "20", "--gp", "6.5",
        "--ni", "500", "--acoes", "100",
    ])
    divergencia_ref = (ref_h1["niveis"][0]["preco_acao"] / ref_sem_degrau["Preco_acao"] - 1) * 100

    assert degrau["divergencia_de_base_%"] == pytest.approx(divergencia_ref)
    assert cenario["sem_degrau"]["valor"]["preco_acao"] == pytest.approx(ref_sem_degrau["Preco_acao"])
    assert cenario["sem_degrau"]["multiplos"]["PL_curr"] == pytest.approx(ref_sem_degrau["PL_curr"])


def test_2_h_igual_a_1_nao_inventa_valor_sem_capacidade_ociosa():
    """`indice_alvo == indice_atual` -> h=1 -> o P/VP com transição é igual
    ao P/VP base (`multiplo_x_rentab`), qualquer que seja o fator de
    transição — o degrau não inventa valor sem capacidade ociosa de
    verdade. Também bate com o múltiplo P/L "sem degrau" (mesma
    rentabilidade, mesmas premissas)."""
    caso = _caso_ancora()
    caso["degrau"]["indice_alvo"]["valor"] = caso["degrau"]["indice_atual"]["valor"]

    resultado = avaliar(caso)
    cenario = resultado["cenarios"]["base"]
    degrau = cenario["degrau"]

    assert degrau["h"] == pytest.approx(1.0)
    assert degrau["com_transicao"] == pytest.approx(degrau["multiplo_x_rentab"])
    assert degrau["multiplo"] == pytest.approx(cenario["sem_degrau"]["multiplos"]["PL_curr"])


def test_3_m_zero_mantem_rentabilidade_pos_igual_a_base():
    """m=0 (eficiência marginal nula do capital liberado) -> rentabilidade
    pós-degrau = rentabilidade base — o capital liberado não rende nada
    extra —, mesmo com h != 1 (capacidade ociosa real, só não aproveitada)."""
    caso = _caso_ancora()
    caso["degrau"]["m"]["base"]["valor"] = 0.0

    resultado = avaliar(caso)
    degrau = resultado["cenarios"]["base"]["degrau"]

    assert degrau["h"] != pytest.approx(1.0)
    assert degrau["rentabilidade_pos_%"] == pytest.approx(
        caso["cenarios"]["base"]["premissas"]["roe"])


def test_4_rentabilidade_terminal_nao_acompanha_o_degrau_sem_roe_tv_declarado():
    """Sem `roe_tv` declarado, o TV usa a rentabilidade BASE (rent), não a
    pós-degrau — é o `pc(roe_tv) or rent` do handler (justos.py). Testado
    direto em `precificar_degrau` (não via `avaliar()`): a perna
    "sem_degrau" roda a MESMA `tv=gordon`, que — ao contrário do degrau —
    não tem esse fallback (`pe()` devolve NaN sob gordon sem `roe_tv`);
    remover `roe_tv` do cenário inteiro quebraria essa perna antes de
    alcançar o que este teste mede. `precificar_degrau` é a função do
    wrapper desta task — testá-la direto continua sendo "o wrapper", não o
    motor cru."""
    bloco = {
        "indice_atual": {"valor": 19.3}, "indice_alvo": {"valor": 14.0},
        "anos": 4, "perfil_transicao": "rampa",
        "vpa": {"valor": 29.11}, "fx": 1.0,
    }
    base = {"g": 12.0, "roe": 20.0, "ke": 20.0, "n": 10, "tv": "gordon", "gp": 6.5}

    sem_roe_tv = precificar_degrau(dict(base), bloco, 100.0, moeda="BRL-nominal")
    com_roe_tv_da_base = precificar_degrau(
        {**base, "roe_tv": base["roe"]}, bloco, 100.0, moeda="BRL-nominal")
    com_roe_tv_pos_degrau = precificar_degrau(
        {**base, "roe_tv": sem_roe_tv["niveis"][0]["rentabilidade_pos_%"]},
        bloco, 100.0, moeda="BRL-nominal")

    multiplo_sem = sem_roe_tv["niveis"][0]["multiplo"]
    assert multiplo_sem == pytest.approx(com_roe_tv_da_base["niveis"][0]["multiplo"])
    assert multiplo_sem != pytest.approx(com_roe_tv_pos_degrau["niveis"][0]["multiplo"])


# --------------------------------------------------------------------------
# Teste 5: recusas nomeadas. Cada `constroi` devolve um caso deliberadamente
# inválido por UM motivo só; `regex` é o texto que a recusa tem de nomear.
# --------------------------------------------------------------------------

def _rota_firm_com_degrau() -> dict:
    caso = _carregado("caso_minimo_firm.json")
    caso["degrau"] = {}
    return caso


def _rota_rampa_com_degrau() -> dict:
    caso = _carregado("caso_rampa.json")
    caso["degrau"] = {}
    return caso


def _anos_ausente() -> dict:
    caso = _caso_ancora()
    del caso["degrau"]["anos"]
    return caso


def _pontual_sem_razao() -> dict:
    caso = _caso_ancora()
    caso["degrau"]["perfil_transicao"] = "pontual"
    caso["degrau"]["razao_transicao"] = ""
    return caso


def _tv_book_sem_roe_book() -> dict:
    caso = _caso_ancora()
    caso["cenarios"]["base"]["premissas"]["tv"] = "book"
    return caso


def _com_mid_year() -> dict:
    caso = _caso_ancora()
    caso["cenarios"]["base"]["premissas"]["mid_year"] = True
    return caso


def _m_faltando_para_um_cenario() -> dict:
    caso = _caso_ancora()
    caso["cenarios"]["bull"] = copy.deepcopy(caso["cenarios"]["base"])
    return caso  # 'degrau.m' só tem 'base' -- 'bull' fica sem entrada


def _degrau_mais(bloco_conflitante: str):
    def _constroi() -> dict:
        caso = _caso_ancora()
        caso[bloco_conflitante] = {}
        return caso
    return _constroi


# --------------------------------------------------------------------------
# F1 (onda de correção da revisão final): índice atual abaixo do alvo
# administrável não é capacidade ociosa — é falta de capital (h < 1). Ver
# `_validar_degrau` (caso.py) para a metodologia citada na mensagem.
# --------------------------------------------------------------------------

def _indice_atual_abaixo_do_indice_alvo() -> dict:
    caso = _caso_ancora()
    caso["degrau"]["indice_atual"]["valor"] = 12.0  # alvo (declarado) = 14.0
    return caso


# --------------------------------------------------------------------------
# F2 (onda de correção da revisão final): D6 agora compara a convenção
# CANÔNICA — o alias legado 'ic' (que o motor mapeia para 'book' antes de
# qualquer handler, justos.py:26-27/1888-1894) tem de disparar a MESMA
# recusa que 'book' literal já dispara.
# --------------------------------------------------------------------------

def _tv_ic_sem_roe_book() -> dict:
    caso = _caso_ancora()
    caso["cenarios"]["base"]["premissas"]["tv"] = "ic"
    return caso


# --------------------------------------------------------------------------
# F3 (onda de correção da revisão final): vocabulário fechado do bloco
# 'degrau' e de cada objeto aninhado — os dois typos que a revisão
# verificou por execução (46,56 em vez de 43,01 / 9,10), mais dois
# representantes da generalização estrutural (um objeto aninhado que
# reusa `_valor_numerico_degrau`, e uma entrada de 'degrau.m', que tem seu
# próprio laço).
# --------------------------------------------------------------------------

def _degrau_perfil_transicao_grafia_da_cli() -> dict:
    caso = _caso_ancora()
    caso["degrau"]["perfil-transicao"] = "pontual"  # grafia da flag da CLI do vendor
    return caso


def _degrau_cambio_em_vez_de_fx() -> dict:
    caso = _caso_ancora()
    caso["degrau"]["cambio"] = 5.115
    return caso


def _degrau_indice_atual_chave_desconhecida() -> dict:
    caso = _caso_ancora()
    caso["degrau"]["indice_atual"]["fontee"] = "typo de 'fonte'"
    return caso


def _degrau_m_entrada_chave_desconhecida() -> dict:
    caso = _caso_ancora()
    caso["degrau"]["m"]["base"]["pesoo"] = 1.0  # typo — não é vocabulário nenhum
    return caso


# --------------------------------------------------------------------------
# F4 (onda de correção da revisão final): as três checagens do gate que já
# existiam mas nunca tinham teste de recusa — MG1/MG2/MG3 da revisão.
# --------------------------------------------------------------------------

def _indice_alvo_abaixo_do_piso_teorico() -> dict:
    caso = _caso_ancora()
    caso["degrau"]["piso_teorico"] = 100.0  # > indice_alvo.valor (14.0)
    return caso


def _m_negativo() -> dict:
    caso = _caso_ancora()
    caso["degrau"]["m"]["base"]["valor"] = -1.0
    return caso


def _fx_nao_positivo() -> dict:
    caso = _caso_ancora()
    caso["degrau"]["fx"] = 0.0
    return caso


_CASOS_RECUSADOS = [
    pytest.param(_rota_firm_com_degrau, r"rota 'firm'", id="rota_firm"),
    pytest.param(_rota_rampa_com_degrau, r"rota 'rampa'", id="rota_rampa"),
    pytest.param(_anos_ausente, re.escape("degrau.anos"), id="anos_ausente"),
    pytest.param(_pontual_sem_razao, "razao_transicao", id="pontual_sem_razao"),
    pytest.param(_tv_book_sem_roe_book, "roe_book", id="tv_book_sem_roe_book"),
    pytest.param(_com_mid_year, "mid_year", id="mid_year_proibido_com_degrau"),
    pytest.param(_m_faltando_para_um_cenario, re.escape("degrau.m"), id="m_faltando_para_um_cenario"),
    pytest.param(_degrau_mais("reversa"), "'reversa'", id="degrau_mais_reversa_D7"),
    pytest.param(_degrau_mais("sensibilidades"), "'sensibilidades'", id="degrau_mais_sensibilidades_D7"),
    pytest.param(_degrau_mais("sotp"), "'sotp'", id="degrau_mais_sotp_D7"),
    pytest.param(_indice_atual_abaixo_do_indice_alvo, re.escape("degrau.indice_atual.valor"),
                 id="F1_indice_atual_abaixo_do_alvo"),
    pytest.param(_tv_ic_sem_roe_book, "roe_book", id="F2_tv_ic_sem_roe_book"),
    pytest.param(_degrau_perfil_transicao_grafia_da_cli, re.escape("'perfil-transicao'"),
                 id="F3_perfil_transicao_grafia_da_cli"),
    pytest.param(_degrau_cambio_em_vez_de_fx, re.escape("'cambio'"), id="F3_cambio_em_vez_de_fx"),
    pytest.param(_degrau_indice_atual_chave_desconhecida, re.escape("'fontee'"),
                 id="F3_indice_atual_chave_desconhecida"),
    pytest.param(_degrau_m_entrada_chave_desconhecida, re.escape("'pesoo'"),
                 id="F3_m_entrada_chave_desconhecida"),
    pytest.param(_indice_alvo_abaixo_do_piso_teorico, re.escape("degrau.indice_alvo.valor"),
                 id="F4_MG1_alvo_abaixo_do_piso"),
    pytest.param(_m_negativo, re.escape("degrau.m.base.valor"), id="F4_MG2_m_negativo"),
    pytest.param(_fx_nao_positivo, re.escape("degrau.fx"), id="F4_MG3_fx_nao_positivo"),
]


@pytest.mark.parametrize("constroi,regex", _CASOS_RECUSADOS)
def test_5_recusas_nomeadas(constroi, regex):
    with pytest.raises(CasoInvalido, match=regex):
        validar(constroi())


def test_6_validar_aceita_um_caso_de_degrau_legal_de_ponta_a_ponta():
    """F4 (onda de correção da revisão final): a revisão notou que nenhum
    teste chama `validar()` (o GATE) sobre um caso de degrau LEGAL — os
    testes 1-4 chamam `avaliar()`/`precificar_degrau` direto, e os únicos
    casos que passam por `validar()` na Task 1 são as três células da
    matriz (D7), todas RECUSAS. `_caso_ancora()` é o mesmo exemplo do
    SKILL.md do vendor que o teste 1 usa como referência — `validar()` não
    pode levantar nada para ele."""
    validar(_caso_ancora())  # não levanta — é a asserção inteira
