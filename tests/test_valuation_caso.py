import json
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures"
import sys
sys.path.insert(0, str(RAIZ / "skills" / "er-valuation" / "scripts"))
from caso import (  # noqa: E402
    CasoInvalido,
    PREMISSAS_OBRIGATORIAS_EQUITY,
    PREMISSAS_OBRIGATORIAS_FIRM,
    carregar,
    validar,
)


def _firm() -> dict:
    return json.loads((FIXTURES / "caso_minimo_firm.json").read_text(encoding="utf-8"))


def _equity() -> dict:
    return json.loads((FIXTURES / "caso_minimo_equity.json").read_text(encoding="utf-8"))


def test_fixture_firm_e_valida():
    assert carregar(FIXTURES / "caso_minimo_firm.json")["rota"] == "firm"


def test_fixture_equity_e_valida():
    assert carregar(FIXTURES / "caso_minimo_equity.json")["rota"] == "equity"


@pytest.mark.parametrize("campo", ["companhia", "moeda", "data_analise", "rota",
                                   "acoes_diluidas", "cenarios"])
def test_campo_obrigatorio_ausente_recusa(campo):
    c = _firm()
    del c[campo]
    with pytest.raises(CasoInvalido, match=campo):
        validar(c)


def test_tv_ausente_recusa_por_ser_escolha_sem_default():
    c = _firm()
    del c["cenarios"]["base"]["premissas"]["tv"]
    with pytest.raises(CasoInvalido, match="convenção terminal"):
        validar(c)


def test_ancora_ausente_recusa():
    """A metodologia exige âncora observável por cenário — cenário sem âncora e inventado."""
    c = _firm()
    del c["cenarios"]["base"]["ancora"]
    with pytest.raises(CasoInvalido, match="âncora"):
        validar(c)


def test_triangulo_ausente_recusa():
    """Cenario com RiR silencioso e cenario opaco: a configuracao tem de ser declarada."""
    c = _firm()
    del c["cenarios"]["base"]["triangulo"]
    with pytest.raises(CasoInvalido, match="triângulo"):
        validar(c)


def test_triangulo_com_output_entre_os_inputs_recusa():
    c = _firm()
    c["cenarios"]["base"]["triangulo"] = {"inputs": ["g", "roic"], "output": "g"}
    with pytest.raises(CasoInvalido, match="triângulo"):
        validar(c)


def test_rota_desconhecida_recusa():
    c = _firm()
    c["rota"] = "hibrida"
    with pytest.raises(CasoInvalido, match="rota"):
        validar(c)


def test_metrica_incompativel_com_a_rota_recusa():
    c = _firm()
    c["metrica_base"]["tipo"] = "LL"
    with pytest.raises(CasoInvalido, match="métrica"):
        validar(c)


def test_metrica_fora_da_fatia_recusa_com_mensagem_clara():
    c = _firm()
    c["metrica_base"]["tipo"] = "EBIT"
    with pytest.raises(CasoInvalido, match="EBIT"):
        validar(c)


def test_ponte_na_rota_equity_recusa():
    """Financeira nao tem ponte de divida — aceitar e ignorar seria silenciar."""
    c = _equity()
    c["ponte"] = {"divida_bruta": 10.0, "caixa_e_equivalentes": 0.0,
                  "outros_ativos": 0.0, "outros_passivos": 0.0, "minoritarios": 0.0}
    with pytest.raises(CasoInvalido, match="ponte"):
        validar(c)


def test_ponte_ausente_na_rota_firm_recusa():
    c = _firm()
    del c["ponte"]
    with pytest.raises(CasoInvalido, match="ponte"):
        validar(c)


def test_premissa_desconhecida_recusa():
    """Chave que o motor nao conhece e erro de digitacao, nao extensao silenciosa."""
    c = _firm()
    c["cenarios"]["base"]["premissas"]["roe"] = 20.0
    with pytest.raises(CasoInvalido, match="roe"):
        validar(c)


def test_cenarios_vazio_recusa():
    c = _firm()
    c["cenarios"] = {}
    with pytest.raises(CasoInvalido, match="cenário"):
        validar(c)


def test_acoes_diluidas_nao_positiva_recusa():
    c = _firm()
    c["acoes_diluidas"] = 0
    with pytest.raises(CasoInvalido, match="ações"):
        validar(c)


# --------------------------------------------------------------------------
# FIX 1: 'null' não pode contar como suprido — nem em campo de topo, nem em
# premissa obrigatória. A checagem de presença por 'in' sozinha deixava
# passar um campo presente com valor None; None é uma saída bem plausível
# de um template ou de um agente upstream, não uma escolha deliberada.
# --------------------------------------------------------------------------

@pytest.mark.parametrize("campo", ["companhia", "moeda", "data_analise"])
def test_campo_de_topo_nulo_recusa_como_ausente(campo):
    c = _firm()
    c[campo] = None
    with pytest.raises(CasoInvalido, match=campo):
        validar(c)


def test_tv_nulo_recusa_com_a_mesma_mensagem_de_tv_ausente():
    c = _firm()
    c["cenarios"]["base"]["premissas"]["tv"] = None
    with pytest.raises(CasoInvalido, match="convenção terminal"):
        validar(c)


def test_tv_nulo_na_rota_equity_tambem_recusa():
    c = _equity()
    c["cenarios"]["base"]["premissas"]["tv"] = None
    with pytest.raises(CasoInvalido, match="convenção terminal"):
        validar(c)


@pytest.mark.parametrize("campo", sorted(PREMISSAS_OBRIGATORIAS_FIRM - {"tv"}))
def test_premissa_obrigatoria_firm_nula_recusa_como_ausente(campo):
    c = _firm()
    c["cenarios"]["base"]["premissas"][campo] = None
    with pytest.raises(CasoInvalido, match=f"'{campo}' ausente"):
        validar(c)


@pytest.mark.parametrize("campo", sorted(PREMISSAS_OBRIGATORIAS_EQUITY - {"tv"}))
def test_premissa_obrigatoria_equity_nula_recusa_como_ausente(campo):
    c = _equity()
    c["cenarios"]["base"]["premissas"][campo] = None
    with pytest.raises(CasoInvalido, match=f"'{campo}' ausente"):
        validar(c)


def test_data_base_nula_e_permitida():
    """`data_base` e opcional de verdade — None nao pode virar recusa."""
    c = _firm()
    c["data_base"] = None
    validar(c)


@pytest.mark.parametrize("campo", ["roic_tv", "gp", "roic_book", "mid_year"])
def test_premissa_opcional_firm_nula_e_permitida(campo):
    """gp, roic_book etc. só importam sob certas convenções — None é legítimo."""
    c = _firm()
    c["cenarios"]["base"]["premissas"][campo] = None
    validar(c)


# --------------------------------------------------------------------------
# FIX 2: números não finitos (NaN, Infinity, -Infinity) são recusados.
# json.loads aceita esses literais não-padrão; um deles em qualquer campo
# numérico envenena a conta a jusante em silêncio — e o serializador do
# motor transforma float não-finito em `null` mais adiante, longe da causa.
# --------------------------------------------------------------------------

@pytest.mark.parametrize("valor", [float("nan"), float("inf"), float("-inf")])
def test_acoes_diluidas_nao_finita_recusa(valor):
    c = _firm()
    c["acoes_diluidas"] = valor
    with pytest.raises(CasoInvalido, match="ações"):
        validar(c)


def test_metrica_base_valor_nao_finito_recusa():
    c = _firm()
    c["metrica_base"]["valor"] = float("nan")
    with pytest.raises(CasoInvalido, match="metrica_base"):
        validar(c)


def test_ponte_linha_nao_finita_recusa():
    c = _firm()
    c["ponte"]["divida_bruta"] = float("nan")
    with pytest.raises(CasoInvalido, match="divida_bruta"):
        validar(c)


def test_premissa_nao_finita_recusa():
    c = _firm()
    c["cenarios"]["base"]["premissas"]["wacc"] = float("nan")
    with pytest.raises(CasoInvalido, match="wacc"):
        validar(c)


def test_json_com_nan_literal_e_recusado_end_to_end(tmp_path):
    """json.loads aceita o literal não-padrão NaN; carregar() tem de recusar
    antes que o valor envenene qualquer conta a jusante."""
    bruto = (FIXTURES / "caso_minimo_firm.json").read_text(encoding="utf-8")
    bruto_com_nan = bruto.replace('"acoes_diluidas": 100.0', '"acoes_diluidas": NaN')
    assert bruto_com_nan != bruto  # a substituição realmente aconteceu
    arquivo = tmp_path / "caso_com_nan.json"
    arquivo.write_text(bruto_com_nan, encoding="utf-8")
    with pytest.raises(CasoInvalido, match="ações"):
        carregar(arquivo)


# --------------------------------------------------------------------------
# FIX 3: a ponte tem de estar COMPLETA, não apenas presente. Somar é
# responsabilidade de ponte.py; presença de cada linha é responsabilidade
# deste módulo — sem isso, {} passava e o KeyError só aparecia lá na frente.
# --------------------------------------------------------------------------

def test_ponte_vazia_na_rota_firm_recusa():
    c = _firm()
    c["ponte"] = {}
    with pytest.raises(CasoInvalido, match="ponte"):
        validar(c)


def test_ponte_com_uma_linha_faltando_recusa_nomeando_a_linha():
    c = _firm()
    del c["ponte"]["minoritarios"]
    with pytest.raises(CasoInvalido, match="minoritarios"):
        validar(c)


def test_ponte_com_linha_nula_recusa_nomeando_a_linha():
    c = _firm()
    c["ponte"]["caixa_e_equivalentes"] = None
    with pytest.raises(CasoInvalido, match="caixa_e_equivalentes"):
        validar(c)


def test_ponte_com_linha_nao_numerica_recusa_nomeando_a_linha():
    c = _firm()
    c["ponte"]["outros_ativos"] = "muita"
    with pytest.raises(CasoInvalido, match="outros_ativos"):
        validar(c)


def test_ponte_com_todas_as_linhas_zero_e_valida():
    """0.0 é um valor legítimo de linha da ponte — não pode ser lido como ausente."""
    c = _firm()
    c["ponte"] = {campo: 0.0 for campo in c["ponte"]}
    validar(c)


# --------------------------------------------------------------------------
# FIX 4: o triângulo tem de ser um triângulo — permutação exata de um
# conjunto de 3 nomes por rota, não qualquer coisa com uma chave "inputs"
# e uma chave "output". crescimento = taxa de reinvestimento x retorno.
# --------------------------------------------------------------------------

def test_triangulo_com_tres_inputs_recusa():
    c = _firm()
    c["cenarios"]["base"]["triangulo"] = {"inputs": ["a", "b", "c"], "output": "d"}
    with pytest.raises(CasoInvalido, match="triângulo"):
        validar(c)


def test_triangulo_com_um_input_so_recusa():
    c = _firm()
    c["cenarios"]["base"]["triangulo"] = {"inputs": ["g"], "output": "roic"}
    with pytest.raises(CasoInvalido, match="triângulo"):
        validar(c)


def test_triangulo_com_nome_fora_do_vocabulario_da_rota_recusa():
    """'wacc' é premissa válida da rota firm, mas não é variável do triângulo."""
    c = _firm()
    c["cenarios"]["base"]["triangulo"] = {"inputs": ["g", "wacc"], "output": "roic"}
    with pytest.raises(CasoInvalido, match="triângulo"):
        validar(c)


def test_triangulo_com_vocabulario_da_rota_errada_recusa():
    """'roe' é do triângulo equity, não do triângulo firm."""
    c = _firm()
    c["cenarios"]["base"]["triangulo"] = {"inputs": ["g", "roe"], "output": "rir"}
    with pytest.raises(CasoInvalido, match="triângulo"):
        validar(c)


def test_triangulo_com_input_duplicado_recusa():
    c = _firm()
    c["cenarios"]["base"]["triangulo"] = {"inputs": ["g", "g"], "output": "roic"}
    with pytest.raises(CasoInvalido, match="triângulo"):
        validar(c)


@pytest.mark.parametrize("inputs,output", [
    (["g", "roic"], "rir"),
    (["roic", "rir"], "g"),
    (["rir", "g"], "roic"),
])
def test_triangulo_firm_aceita_qualquer_permutacao_valida(inputs, output):
    c = _firm()
    c["cenarios"]["base"]["triangulo"] = {"inputs": inputs, "output": output}
    validar(c)


@pytest.mark.parametrize("inputs,output", [
    (["g", "roe"], "rir"),
    (["roe", "rir"], "g"),
    (["rir", "g"], "roe"),
])
def test_triangulo_equity_aceita_qualquer_permutacao_valida(inputs, output):
    c = _equity()
    c["cenarios"]["base"]["triangulo"] = {"inputs": inputs, "output": output}
    validar(c)
