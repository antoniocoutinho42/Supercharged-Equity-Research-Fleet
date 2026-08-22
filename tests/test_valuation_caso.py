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


# --------------------------------------------------------------------------
# FIX 5: 'metrica_base.valor' e o loop de premissas de `_validar_cenario`
# chamavam `_finito` sem checar o tipo antes — e o próprio contrato de
# `_finito` é explícito: valor não-numérico (None, str, bool, list, dict)
# "passa livre; a validade dele é checada por quem chama". Os outros dois
# pontos que chamam `_finito` (a ponte e `acoes_diluidas`) já checavam tipo
# antes de chamar; estes dois não checavam — um `metrica_base.valor`
# ausente ou uma premissa (wacc, g, roic...) de tipo errado chegava direto
# ao motor sem recusa nomeada.
# --------------------------------------------------------------------------

def test_metrica_base_valor_none_recusa():
    c = _firm()
    c["metrica_base"]["valor"] = None
    with pytest.raises(CasoInvalido, match="metrica_base"):
        validar(c)


def test_metrica_base_valor_nao_numerico_recusa():
    c = _firm()
    c["metrica_base"]["valor"] = "quinhentos"
    with pytest.raises(CasoInvalido, match="metrica_base"):
        validar(c)


def test_metrica_base_valor_ausente_recusa():
    c = _firm()
    del c["metrica_base"]["valor"]
    with pytest.raises(CasoInvalido, match="metrica_base"):
        validar(c)


@pytest.mark.parametrize("campo,valor_invalido", [("wacc", "dez"), ("g", [1, 2, 3])])
def test_premissa_numerica_com_tipo_errado_recusa(campo, valor_invalido):
    c = _firm()
    c["cenarios"]["base"]["premissas"][campo] = valor_invalido
    with pytest.raises(CasoInvalido, match=f"'{campo}'"):
        validar(c)


def test_premissa_bool_recusa_como_nao_numerica():
    """bool é subclasse de int em Python, mas não é número válido de premissa."""
    c = _firm()
    c["cenarios"]["base"]["premissas"]["wacc"] = True
    with pytest.raises(CasoInvalido, match="'wacc'"):
        validar(c)


@pytest.mark.parametrize("rota,campo,valor_legitimo", [
    ("firm", "gp", 0.0),
    ("equity", "nde", -15.0),
    ("firm", "n", 7),
])
def test_premissa_com_valor_numerico_legitimo_e_aceita(rota, campo, valor_legitimo):
    """Zero, negativo e int são números válidos — a guarda de tipo não pode confundi-los com ausência."""
    c = _firm() if rota == "firm" else _equity()
    c["cenarios"]["base"]["premissas"][campo] = valor_legitimo
    validar(c)


# --------------------------------------------------------------------------
# Simetria de cobertura: equivalente de `test_premissa_opcional_firm_nula_e_permitida`
# para a rota equity. roe_tv, roe_book e politica_tv só importam sob certas
# convenções — None é legítimo para os três, tal como para os opcionais já
# cobertos do lado firm.
# --------------------------------------------------------------------------

@pytest.mark.parametrize("campo", ["roe_tv", "roe_book", "politica_tv"])
def test_premissa_opcional_equity_nula_e_permitida(campo):
    c = _equity()
    c["cenarios"]["base"]["premissas"][campo] = None
    validar(c)


# --------------------------------------------------------------------------
# preco: bloco obrigatório, com valor positivo e fonte/data auditáveis.
# avaliar() lê caso["preco"]["valor"] para calcular o upside — sem esta
# validação aqui, um caso sem 'preco' (ou com 'preco.valor' ausente/inválido)
# passava pelo portão e só quebrava depois, com KeyError cru, longe desta
# causa. Ambas as fixtures já carregam um bloco 'preco' completo, então
# continuam válidas sem alteração.
# --------------------------------------------------------------------------

def test_preco_ausente_recusa():
    c = _firm()
    del c["preco"]
    with pytest.raises(CasoInvalido, match="preco"):
        validar(c)


def test_preco_nulo_recusa():
    c = _firm()
    c["preco"] = None
    with pytest.raises(CasoInvalido, match="preco"):
        validar(c)


def test_preco_nao_e_objeto_recusa():
    c = _firm()
    c["preco"] = 55.0
    with pytest.raises(CasoInvalido, match="preco"):
        validar(c)


def test_preco_valor_ausente_recusa():
    c = _firm()
    del c["preco"]["valor"]
    with pytest.raises(CasoInvalido, match="preco"):
        validar(c)


def test_preco_valor_nulo_recusa():
    c = _firm()
    c["preco"]["valor"] = None
    with pytest.raises(CasoInvalido, match="preco"):
        validar(c)


def test_preco_valor_nao_numerico_recusa():
    c = _firm()
    c["preco"]["valor"] = "cinquenta e cinco"
    with pytest.raises(CasoInvalido, match="preco"):
        validar(c)


@pytest.mark.parametrize("valor", [float("nan"), float("inf"), float("-inf")])
def test_preco_valor_nao_finito_recusa(valor):
    c = _firm()
    c["preco"]["valor"] = valor
    with pytest.raises(CasoInvalido, match="preco"):
        validar(c)


@pytest.mark.parametrize("valor", [0, 0.0, -10.0])
def test_preco_valor_nao_positivo_recusa(valor):
    c = _firm()
    c["preco"]["valor"] = valor
    with pytest.raises(CasoInvalido, match="preco"):
        validar(c)


def test_preco_fonte_ausente_recusa():
    c = _firm()
    del c["preco"]["fonte"]
    with pytest.raises(CasoInvalido, match="fonte"):
        validar(c)


def test_preco_fonte_vazia_recusa():
    c = _firm()
    c["preco"]["fonte"] = ""
    with pytest.raises(CasoInvalido, match="fonte"):
        validar(c)


def test_preco_fonte_nao_e_string_recusa():
    c = _firm()
    c["preco"]["fonte"] = 123
    with pytest.raises(CasoInvalido, match="fonte"):
        validar(c)


def test_preco_data_ausente_recusa():
    c = _firm()
    del c["preco"]["data"]
    # FIX 9 (revisão final): match="data" também bate em mensagens de
    # 'data_analise' — regex apertada para só poder casar com 'preco.data'.
    with pytest.raises(CasoInvalido, match=r"preco\.data"):
        validar(c)


def test_preco_data_vazia_recusa():
    c = _firm()
    c["preco"]["data"] = ""
    with pytest.raises(CasoInvalido, match=r"preco\.data"):
        validar(c)


# --------------------------------------------------------------------------
# Revisão final, FIX 5: 'metrica_base.fonte' é documentado no SKILL.md como
# obrigatório (tipo, valor, fonte), mas nunca era validado — a métrica-base é
# a escala do valuation inteiro, e era o único número do caso sem
# proveniência auditável, enquanto 'preco.fonte' já era exigido. Mesma
# disciplina de _validar_preco: presente, string, não-vazia.
# --------------------------------------------------------------------------

def test_metrica_base_fonte_ausente_recusa():
    c = _firm()
    del c["metrica_base"]["fonte"]
    with pytest.raises(CasoInvalido, match="fonte"):
        validar(c)


def test_metrica_base_fonte_vazia_recusa():
    c = _firm()
    c["metrica_base"]["fonte"] = ""
    with pytest.raises(CasoInvalido, match="fonte"):
        validar(c)


def test_metrica_base_fonte_nao_e_string_recusa():
    c = _firm()
    c["metrica_base"]["fonte"] = 123
    with pytest.raises(CasoInvalido, match="fonte"):
        validar(c)


# --------------------------------------------------------------------------
# Revisão final, FIX 3: doze formatos malformados escapavam da validação como
# AttributeError/TypeError cru em vez de CasoInvalido — o portão recusava
# ANTES de qualquer chamada ao motor, mas sem motivo nomeado. Cada teste
# abaixo reproduz um formato achado por sondagem manual na revisão: o caso
# raiz não sendo objeto, um bloco-container (metrica_base/ponte/cenarios/
# cenário individual/triângulo) vindo com o tipo errado, ou uma chave de
# premissa não-textual — todos tinham de virar CasoInvalido, nomeando o
# campo, nunca uma exceção Python interna vazando para quem chama.
# --------------------------------------------------------------------------

def test_caso_raiz_none_recusa():
    with pytest.raises(CasoInvalido):
        validar(None)


def test_caso_raiz_numero_recusa():
    with pytest.raises(CasoInvalido):
        validar(42)


def test_metrica_base_string_recusa():
    c = _firm()
    c["metrica_base"] = "EBITDA"
    with pytest.raises(CasoInvalido, match="metrica_base"):
        validar(c)


def test_metrica_base_lista_recusa():
    c = _firm()
    c["metrica_base"] = ["EBITDA", 1000.0]
    with pytest.raises(CasoInvalido, match="metrica_base"):
        validar(c)


def test_ponte_lista_recusa():
    c = _firm()
    c["ponte"] = [800.0, 300.0, 0.0, 0.0, 0.0]
    with pytest.raises(CasoInvalido, match="ponte"):
        validar(c)


def test_ponte_string_recusa():
    c = _firm()
    c["ponte"] = "sem ponte"
    with pytest.raises(CasoInvalido, match="ponte"):
        validar(c)


def test_cenarios_lista_recusa():
    """Formato bem plausível de erro manual ou de agente upstream."""
    c = _firm()
    c["cenarios"] = ["base", "bull"]
    with pytest.raises(CasoInvalido, match="cenarios"):
        validar(c)


def test_cenario_individual_string_recusa():
    c = _firm()
    c["cenarios"]["base"] = "cenario base"
    with pytest.raises(CasoInvalido, match="cenário"):
        validar(c)


def test_cenario_individual_lista_recusa():
    c = _firm()
    c["cenarios"]["base"] = ["g", "roic"]
    with pytest.raises(CasoInvalido, match="cenário"):
        validar(c)


def test_triangulo_inputs_inteiro_recusa():
    c = _firm()
    c["cenarios"]["base"]["triangulo"] = {"inputs": 2, "output": "rir"}
    with pytest.raises(CasoInvalido, match="triângulo"):
        validar(c)


def test_triangulo_inputs_lista_de_listas_recusa():
    c = _firm()
    c["cenarios"]["base"]["triangulo"] = {"inputs": [["g"], ["roic"]], "output": "rir"}
    with pytest.raises(CasoInvalido, match="triângulo"):
        validar(c)


def test_triangulo_output_lista_recusa():
    c = _firm()
    c["cenarios"]["base"]["triangulo"] = {"inputs": ["g", "roic"], "output": ["rir"]}
    with pytest.raises(CasoInvalido, match="triângulo"):
        validar(c)


def test_premissa_com_chave_nao_textual_recusa():
    """JSON de verdade nunca produz chave não-string, mas caso.py aceita
    qualquer dict Python — inclusive um montado por outro código, não lido
    de arquivo. Sem a guarda, sorted(premissas) quebra com TypeError assim
    que mistura chave string e não-string (comparação entre tipos)."""
    c = _firm()
    c["cenarios"]["base"]["premissas"][5] = 10.0
    with pytest.raises(CasoInvalido, match="premiss"):
        validar(c)


# --------------------------------------------------------------------------
# Fatia B, Task 1: contrato dos blocos opcionais 'mercado', 'reversa' e
# 'sensibilidades'. Os três são opcionais — as fixtures e testes da fatia A
# continuam válidos sem eles. Mas 'reversa' presente exige 'mercado' (rf,
# erp) e o eixo 'custo_capital', porque sem eles não há beta implícito — o
# confronto que a reversa existe para produzir.
# --------------------------------------------------------------------------

def _reversa() -> dict:
    return json.loads((FIXTURES / "caso_reversa_firm.json").read_text(encoding="utf-8"))


def test_fixture_de_reversa_e_valida():
    assert carregar(FIXTURES / "caso_reversa_firm.json")["reversa"]["eixos"]


def test_caso_sem_blocos_novos_continua_valido():
    """A fatia A nao pode ser quebrada: mercado/reversa/sensibilidades sao opcionais."""
    assert carregar(FIXTURES / "caso_minimo_firm.json")["rota"] == "firm"


def test_reversa_sem_custo_de_capital_recusa():
    """Eixo obrigatorio da metodologia em toda rodada — omitir nao e escolha."""
    c = _reversa()
    c["reversa"]["eixos"] = ["crescimento", "rentabilidade"]
    with pytest.raises(CasoInvalido, match="custo de capital"):
        validar(c)


def test_reversa_com_eixo_desconhecido_recusa():
    c = _reversa()
    c["reversa"]["eixos"] = ["custo_capital", "volatilidade"]
    with pytest.raises(CasoInvalido, match="volatilidade"):
        validar(c)


def test_reversa_sem_bloco_mercado_recusa():
    """Sem rf e erp nao ha beta implicito, e o beta implicito e o confronto."""
    c = _reversa()
    del c["mercado"]
    with pytest.raises(CasoInvalido, match="mercado"):
        validar(c)


@pytest.mark.parametrize("campo", ["rf", "erp"])
def test_reversa_sem_campo_de_mercado_recusa(campo):
    c = _reversa()
    del c["mercado"][campo]
    with pytest.raises(CasoInvalido, match=campo):
        validar(c)


def test_reversa_aponta_cenario_inexistente_recusa():
    c = _reversa()
    c["reversa"]["cenario"] = "otimista"
    with pytest.raises(CasoInvalido, match="otimista"):
        validar(c)


def test_beta_observado_invalido_recusa():
    c = _reversa()
    c["mercado"]["beta_observado"] = [1.4, 0.8]
    with pytest.raises(CasoInvalido, match="beta"):
        validar(c)


def test_grade_1d_sem_pontos_recusa():
    c = _reversa()
    c["sensibilidades"]["grades_1d"][0]["pontos"] = []
    with pytest.raises(CasoInvalido, match="pontos"):
        validar(c)


def test_grade_1d_com_premissa_fora_da_rota_recusa():
    c = _reversa()
    c["sensibilidades"]["grades_1d"][0]["premissa"] = "roe"
    with pytest.raises(CasoInvalido, match="roe"):
        validar(c)


def test_grade_sem_triangulo_declarado_recusa():
    """Grade sem configuracao do triangulo nao e reproduzivel."""
    c = _reversa()
    del c["sensibilidades"]["grades_1d"][0]["triangulo"]
    with pytest.raises(CasoInvalido, match="triângulo"):
        validar(c)


def test_grade_2d_com_eixos_iguais_recusa():
    c = _reversa()
    c["sensibilidades"]["grades_2d"][0]["premissa_y"] = "roic"
    with pytest.raises(CasoInvalido, match="mesma premissa"):
        validar(c)


def test_sensibilidades_sem_reversa_e_permitido():
    """Os dois blocos sao independentes."""
    c = _reversa()
    del c["reversa"]
    del c["mercado"]
    validar(c)


# --------------------------------------------------------------------------
# Revisão final #3 (terceira vez que a mesma classe de defeito aparece):
# valor de tipo errado alcançando um `x not in <frozenset/dict>`
# (não-hasheável: lista, dict) ou um `for ... in ...` (não-lista —
# `grades_1d`/`grades_2d` truthy mas não-lista, porque `x or []` só
# substitui valor falsy) escapava como TypeError/AttributeError cru, não
# CasoInvalido. As sete formas abaixo foram achadas por sondagem manual
# (quatro pelo controlador, três pelo revisor) e cobrem as duas
# causas-raiz de uma vez: `_exigir_texto`/`_exigir_lista`, chamadas em
# toda fronteira de pertencimento/iteração do módulo — não só nestes sete
# pontos.
# --------------------------------------------------------------------------

def test_reversa_eixos_com_lista_dentro_recusa():
    c = _reversa()
    c["reversa"]["eixos"] = ["custo_capital", ["x"]]
    with pytest.raises(CasoInvalido):
        validar(c)


def test_sensibilidades_grades_1d_nao_lista_recusa():
    c = _reversa()
    c["sensibilidades"]["grades_1d"] = 5
    with pytest.raises(CasoInvalido):
        validar(c)


def test_grade_2d_premissa_x_dict_recusa():
    c = _reversa()
    c["sensibilidades"]["grades_2d"][0]["premissa_x"] = {"a": 1}
    with pytest.raises(CasoInvalido):
        validar(c)


def test_reversa_cenario_lista_recusa():
    c = _reversa()
    c["reversa"]["cenario"] = ["base"]
    with pytest.raises(CasoInvalido):
        validar(c)


def test_grade_1d_premissa_lista_recusa():
    c = _reversa()
    c["sensibilidades"]["grades_1d"][0]["premissa"] = ["wacc"]
    with pytest.raises(CasoInvalido):
        validar(c)


def test_sensibilidades_cenario_lista_recusa():
    c = _reversa()
    c["sensibilidades"]["cenario"] = ["base"]
    with pytest.raises(CasoInvalido):
        validar(c)


@pytest.mark.parametrize("valor", [5, True])
def test_sensibilidades_grades_2d_nao_lista_recusa(valor):
    """`x or []` só substitui valor falsy — 5 e True são truthy e
    não-lista, e caíam direto no `for`, sem guarda."""
    c = _reversa()
    c["sensibilidades"]["grades_2d"] = valor
    with pytest.raises(CasoInvalido):
        validar(c)


def test_sensibilidades_aponta_cenario_inexistente_recusa():
    """FIX 3: mesma checagem de existência de 'reversa.cenario', extraída
    para um helper compartilhado — cobertura simétrica do segundo
    chamador, que não tinha teste dedicado antes desta revisão."""
    c = _reversa()
    c["sensibilidades"]["cenario"] = "otimista"
    with pytest.raises(CasoInvalido, match="otimista"):
        validar(c)


# --------------------------------------------------------------------------
# FIX 2 (revisão final #3): grade de sensibilidade varia só premissa
# numérica. 'tv'/'politica_tv'/'mid_year' são premissa válida do CENÁRIO,
# mas sem sentido como eixo de grade — variar 'pontos' numéricos sobre uma
# convenção terminal textual não descreve nada. Sem esta recusa, o caso
# passava no portão e só quebrava depois, num subprocesso do motor.
# --------------------------------------------------------------------------

def test_grade_1d_com_premissa_nao_numerica_recusa():
    c = _reversa()
    c["sensibilidades"]["grades_1d"][0]["premissa"] = "tv"
    with pytest.raises(CasoInvalido, match="numérica"):
        validar(c)


def test_grade_2d_com_premissa_x_nao_numerica_recusa():
    c = _reversa()
    c["sensibilidades"]["grades_2d"][0]["premissa_x"] = "tv"
    with pytest.raises(CasoInvalido, match="numérica"):
        validar(c)


# --------------------------------------------------------------------------
# Revisão final, FIX 3 (Importante): `erp` é o denominador da inversão do
# CAPM em beta implícito (`beta = (custo_implícito - rf) / erp`, em
# `reversa._beta_implicito`) — `erp: 0` passava por `validar` sem recusa
# (só `_numero_valido`/`_finito` eram checados) e só quebrava depois, num
# `ZeroDivisionError` cru dentro de `reverter`, sem passar pelo CLI. O
# módulo já recusa `acoes_diluidas <= 0` pela mesma razão (denominador) —
# `erp` merece a mesma disciplina.
# --------------------------------------------------------------------------

def test_erp_zero_recusa_antes_de_dividir():
    c = _reversa()
    c["mercado"]["erp"] = 0.0
    with pytest.raises(CasoInvalido, match="erp"):
        validar(c)


def test_erp_negativo_recusa():
    c = _reversa()
    c["mercado"]["erp"] = -5.5
    with pytest.raises(CasoInvalido, match="erp"):
        validar(c)


# --------------------------------------------------------------------------
# Revisão final, FIX 4 (Importante): `rf` e `erp` são declarados em PONTOS
# PERCENTUAIS (12.0 = 12%) — a mesma convenção de `raizes_*_%` que o motor
# devolve. Essa convenção só vivia num docstring; um caso declarando
# `rf: 0.12` (fração, não ponto percentual) validava normalmente e
# produzia um beta implícito errado por ~100x, sem aviso nenhum de
# ninguém. Nenhuma taxa livre de risco nem prêmio de risco de mercado
# abaixo de um ponto percentual ocorre na prática — o intervalo aberto
# 0 < x < 1 é seguro para recusar sem estreitar o que é um valor
# legítimo.
# --------------------------------------------------------------------------

@pytest.mark.parametrize("campo", ["rf", "erp"])
def test_rf_ou_erp_como_fracao_recusa(campo):
    c = _reversa()
    c["mercado"][campo] = 0.12
    with pytest.raises(CasoInvalido, match=campo):
        validar(c)


def test_rf_igual_a_um_ponto_percentual_e_aceito():
    """A faixa recusada e o intervalo ABERTO (0, 1); 1.0 nao e fracao
    obviamente digitada e continua sendo um valor legitimo."""
    c = _reversa()
    c["mercado"]["rf"] = 1.0
    validar(c)  # nao levanta


def test_rf_negativo_nao_e_tratado_como_fracao():
    """So o intervalo (0, 1) e recusado; taxa livre de risco negativa (em
    pontos percentuais) nao e o defeito que o FIX 4 mira."""
    c = _reversa()
    c["mercado"]["rf"] = -0.5
    validar(c)  # nao levanta
