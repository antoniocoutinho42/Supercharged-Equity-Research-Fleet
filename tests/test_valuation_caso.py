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


@pytest.mark.parametrize("renomear,chave", [
    pytest.param(lambda c: c["cenarios"].__setitem__("base.2026", c["cenarios"].pop("base")), "base.2026",
                 id="cenario-com-ponto"),
    pytest.param(lambda c: c["ponte"].__setitem__("linha.extra", 1.0), "linha.extra", id="chave-extra-da-ponte"),
    pytest.param(lambda c: c["cenarios"].__setitem__("*", c["cenarios"].pop("base")), "*", id="curinga"),
])
def test_chave_com_ponto_ou_curinga_recusa(renomear, chave):
    """Revisão da 5E (F1): o caminho pontuado de um número do caso não endereça essa chave, e os
    números sob ela sairiam do mapa de insumos em silêncio."""
    c = _firm()
    renomear(c)
    with pytest.raises(CasoInvalido) as erro:
        validar(c)
    assert f"chave '{chave}'" in str(erro.value)


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


# --------------------------------------------------------------------------
# F1 (revisão final, fatia 4C): 'moeda' vazia ou de tipo errado passava por
# `_validar_campos_de_topo` (só presença/não-nulo, nunca tipo nem conteúdo)
# sem nunca ser examinada — quinta aparição, neste módulo, da mesma classe
# de defeito que `_exigir_texto` existe para fechar estruturalmente.
# `moeda: ""` sobrevivia e era descartada por truthiness em
# `motor.py:argv_para` (`if moeda:`), fazendo o motor emitir a Guarda 2 de
# Damodaran ("MOEDA/REGIME NÃO DECLARADOS") sem chave equivalente no
# espelho; `moeda: 123` sobrevivia e estourava `TypeError` no espelho
# (`moeda.toLowerCase is not a function`) em toda chamada de diagnóstico.
# Ver `caso._validar_moeda`.
# --------------------------------------------------------------------------

@pytest.mark.parametrize("valor", ["", "   ", 123, []])
def test_moeda_de_tipo_ou_valor_invalido_recusa_nomeando_moeda(valor):
    c = _firm()
    c["moeda"] = valor
    with pytest.raises(CasoInvalido, match="moeda"):
        validar(c)


# --------------------------------------------------------------------------
# F6 (revisão final, fatia 4C, achado do controlador): chave de topo
# desconhecida era ignorada em silêncio — `_validar_campos_de_topo` só EXIGE
# as seis obrigatórias, e cada bloco opcional só é examinado quando presente
# pelo NOME EXATO. Um bloco com o nome errado passava por `validar()`
# inteiro sem nunca ser examinado: o valuation saía sem um item material que
# o analista declarou. Ver `caso._validar_sem_chaves_de_topo_desconhecidas`
# e os testes com 'stop'/'sensibilidade' mais abaixo (perto de `_sotp`/
# `_reversa`) para a prova com os dois nomes que a revisão citou.
# --------------------------------------------------------------------------

def test_chave_de_topo_desconhecida_recusa_nomeando_a_chave():
    c = _firm()
    c["xyz_nao_existe"] = True
    with pytest.raises(CasoInvalido, match="xyz_nao_existe"):
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


# --------------------------------------------------------------------------
# Fatia C, Task 4: concern da revisão da Task 3 -- "rota equity do caso +
# sotp.materialidade viraria MotorFalhou em vez de recusa nomeada". SOTP
# soma EV (D3); a rota equity não produz EV e já proíbe 'ponte' (teste
# acima) -- sem esta recusa nomeada no gate, a combinação alcançava
# sotp.compor_partes e quebrava fundo, em KeyError sobre caso["ponte"], não
# numa mensagem para o analista.
# --------------------------------------------------------------------------

def test_sotp_na_rota_equity_recusa():
    """Braço financeiro (holdco pura, banco, seguradora) numa SOTP é
    limitação declarada desta fatia, não erro do usuário -- mas a
    combinação em si é recusada, nomeando a razão."""
    c = _equity()
    c["sotp"] = {
        "tipo": "segmento",
        "cenario": "base",
        "partes": [
            {
                "nome": "A", "rota": "firm",
                "metrica_base": {"tipo": "EBITDA", "valor": 100.0, "fonte": "x"},
                "ancora": "x",
                "triangulo": {"inputs": ["g", "roic"], "output": "rir"},
                "premissas": {"g": 5.0, "roic": 12.0, "wacc": 10.0, "n": 10,
                              "da": 10.0, "tax": 25.0, "tv": "convergencia"},
            },
            {
                "nome": "B", "rota": "firm",
                "metrica_base": {"tipo": "EBITDA", "valor": 50.0, "fonte": "x"},
                "ancora": "x",
                "triangulo": {"inputs": ["g", "roic"], "output": "rir"},
                "premissas": {"g": 5.0, "roic": 12.0, "wacc": 10.0, "n": 10,
                              "da": 10.0, "tax": 25.0, "tv": "convergencia"},
            },
        ],
        "topo": {"custos_corporativos_vp": 0.0, "participacoes_nao_consolidadas": 0.0,
                 "desconto_de_holding_pct": None, "razao_do_desconto": None},
    }
    with pytest.raises(CasoInvalido, match="equity"):
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


def test_bloco_sensibilidades_com_nome_errado_recusa_em_vez_de_ignorar():
    """F6: 'sensibilidade' (sem o 's' final) não bate no nome exato que
    `validar()` examina — antes desta correção, o bloco inteiro (cenário,
    grades_1d, grades_2d) era aceito e IGNORADO em silêncio."""
    c = _reversa()
    c["sensibilidade"] = c.pop("sensibilidades")
    with pytest.raises(CasoInvalido, match="sensibilidade"):
        validar(c)


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


# --------------------------------------------------------------------------
# Endurecimento (task 3B), RISCO 2: teto de células declaradas em
# 'sensibilidades' — grades_1d + grades_2d somadas, cada grade 2D contando
# len(pontos_x) x len(pontos_y). Recusa no GATE (dentro de validar(), que
# roda inteiro em carregar() antes de avaliar() chamar o motor para
# qualquer coisa — cenário, eixo de reversa ou célula de grade) — uma
# grade 20x20 são 400 chamadas de subprocesso sem aviso nenhum antes desta
# fatia. 'limite_de_celulas' é o campo opcional pelo qual o analista
# levanta (ou reduz) o teto padrão deliberadamente.
# --------------------------------------------------------------------------

def test_grade_dentro_do_teto_padrao_passa():
    c = _reversa()
    # fixture tem 5 (1D) + 4x3 (2D) = 17 células -- bem abaixo do teto padrão
    validar(c)  # nao levanta


def test_soma_acima_do_teto_padrao_recusa_nomeando_a_contagem():
    c = _reversa()
    c["sensibilidades"]["grades_1d"][0]["pontos"] = [float(i) for i in range(2001)]
    c["sensibilidades"]["grades_2d"] = []
    with pytest.raises(CasoInvalido, match="2001") as excinfo:
        validar(c)
    assert "tempo estimado" in str(excinfo.value)


def test_limite_de_celulas_maior_permite_acima_do_teto_padrao():
    c = _reversa()
    c["sensibilidades"]["grades_1d"][0]["pontos"] = [float(i) for i in range(2001)]
    c["sensibilidades"]["grades_2d"] = []
    c["sensibilidades"]["limite_de_celulas"] = 3000
    validar(c)  # nao levanta -- teto levantado deliberadamente


def test_limite_de_celulas_menor_recusa_antes_do_teto_padrao():
    """Um limite declarado ABAIXO do padrao tambem vale -- o analista pode
    querer ser mais restritivo do que o teto de fabrica."""
    c = _reversa()
    # fixture tem 17 celulas -- bem abaixo do teto padrao (2000), mas acima
    # de um limite mais restritivo declarado deliberadamente
    c["sensibilidades"]["limite_de_celulas"] = 10
    with pytest.raises(CasoInvalido, match="17"):
        validar(c)


def test_contagem_soma_grades_1d_e_2d_juntas():
    """Uma grade 2D conta len(pontos_x) x len(pontos_y), nao len(x) + len(y)."""
    c = _reversa()
    c["sensibilidades"]["grades_1d"][0]["pontos"] = [1.0, 2.0, 3.0]  # 3
    c["sensibilidades"]["grades_2d"][0]["pontos_x"] = [1.0, 2.0, 3.0, 4.0]  # 4
    c["sensibilidades"]["grades_2d"][0]["pontos_y"] = [1.0, 2.0]  # 2 -> 4x2=8
    # total = 3 + 8 = 11: exatamente no teto declarado passa...
    c["sensibilidades"]["limite_de_celulas"] = 11
    validar(c)  # nao levanta -- "passa do teto" e estritamente ACIMA
    # ...um a menos que o total ja recusa.
    c["sensibilidades"]["limite_de_celulas"] = 10
    with pytest.raises(CasoInvalido, match="11"):
        validar(c)


def test_limite_de_celulas_nao_numerico_recusa():
    c = _reversa()
    c["sensibilidades"]["limite_de_celulas"] = "muitas"
    with pytest.raises(CasoInvalido, match="limite_de_celulas"):
        validar(c)


def test_sensibilidades_chave_desconhecida_recusa_em_vez_de_ignorar():
    """F3 (onda de correção da revisão final, item 2): 'limite_de_celulas'
    (o parâmetro NUMÉRICO de grade citado no brief da fatia D) era opcional
    com default silencioso — um nome digitado errado (aqui, sem o 'de')
    nunca era lido por `sensibilidades.get("limite_de_celulas")`, e o teto
    que o analista quis declarar (mais apertado que o padrão, como no teste
    acima) desaparecia sem aviso: o gate aplicava o padrão (2000) em vez do
    que o caso de fato escreveu."""
    c = _reversa()
    c["sensibilidades"]["limite_celulas"] = 10  # falta o 'de'
    with pytest.raises(CasoInvalido, match="limite_celulas"):
        validar(c)


@pytest.mark.parametrize("valor", [0, -5])
def test_limite_de_celulas_nao_positivo_recusa(valor):
    c = _reversa()
    c["sensibilidades"]["limite_de_celulas"] = valor
    with pytest.raises(CasoInvalido, match="limite_de_celulas"):
        validar(c)


# --------------------------------------------------------------------------
# Fatia C, Task 1: rota rampa — vocabulário próprio, delimitador obrigatório
# (fronteira de fase observável) e a regra util XOR g1.
# --------------------------------------------------------------------------

def _rampa() -> dict:
    return json.loads((FIXTURES / "caso_rampa.json").read_text(encoding="utf-8"))


def test_fixture_rampa_e_valida():
    assert carregar(FIXTURES / "caso_rampa.json")["rota"] == "rampa"


def test_rampa_sem_delimitador_recusa():
    """Fase sem delimitador observavel e grau de liberdade disfarcado de analise."""
    c = _rampa()
    del c["delimitador"]
    with pytest.raises(CasoInvalido, match="delimitador"):
        validar(c)


def test_rampa_com_delimitador_vazio_recusa():
    c = _rampa()
    c["delimitador"] = "   "
    with pytest.raises(CasoInvalido, match="delimitador"):
        validar(c)


def test_delimitador_em_outra_rota_recusa():
    """So a rota rampa tem fronteira de fase para delimitar."""
    c = _firm()
    c["delimitador"] = "qualquer coisa"
    with pytest.raises(CasoInvalido, match="delimitador"):
        validar(c)


@pytest.mark.parametrize("campo", ["receita0", "ebitda0", "da_parque", "wk",
                                   "kappa", "g2", "wacc", "tax", "t_rampa", "tv"])
def test_rampa_sem_premissa_obrigatoria_recusa(campo):
    c = _rampa()
    del c["cenarios"]["base"]["premissas"][campo]
    with pytest.raises(CasoInvalido, match=campo):
        validar(c)


def test_rampa_sem_util_nem_g1_recusa():
    """util deriva g1; sem um dos dois a rampa nao tem crescimento de fase 1."""
    c = _rampa()
    del c["cenarios"]["base"]["premissas"]["util"]
    with pytest.raises(CasoInvalido, match="util"):
        validar(c)


def test_rampa_com_util_e_g1_juntos_recusa():
    c = _rampa()
    c["cenarios"]["base"]["premissas"]["g1"] = 9.0
    with pytest.raises(CasoInvalido, match="util"):
        validar(c)


def test_rampa_com_metrica_errada_recusa():
    c = _rampa()
    c["metrica_base"]["tipo"] = "EBITDA"
    with pytest.raises(CasoInvalido, match="EBITDA0"):
        validar(c)


# --------------------------------------------------------------------------
# Revisão final (task 3c): review final da fatia C.
#
# FIX 1 (Crítico): rota rampa x blocos 'reversa'/'sensibilidades' (Fatia B)
# — nenhuma das duas combinações tem metodologia definida nesta fatia (a
# rampa não usa o triângulo g = RiR x retorno, e RESOLVER_POR_EIXO só
# conhece 'firm'/'equity') e as duas escapavam como KeyError cru: 'rampa'.
# 'rampa'+sensibilidades batia a guarda ANTES de qualquer chamada ao motor
# (a primeira grade dispara `_validar_triangulo`, que indexa
# `_TRIANGULO_POR_ROTA['rampa']` — chave ausente); 'rampa'+reversa passava
# o portão inteiro (nenhuma checagem de caso.py toca um dict indexado por
# rota) e só quebrava DEPOIS, dentro de `reversa.reverter`, já com os
# cenários principais do caso rodados no motor. Decisão tomada, não
# reaberta aqui: recusar as duas, pelo nome, como limitação declarada desta
# fatia — mesmo padrão de equity+sotp (`test_sotp_na_rota_equity_recusa`,
# acima).
# --------------------------------------------------------------------------

def test_rampa_com_reversa_recusa_no_gate():
    c = _rampa()
    c["mercado"] = {"rf": 12.0, "erp": 5.5, "fonte": "x", "data": "2026-08-24"}
    c["reversa"] = {"cenario": "base", "eixos": ["custo_capital"]}
    with pytest.raises(CasoInvalido, match="rampa"):
        validar(c)


def test_rampa_com_sensibilidades_recusa_no_gate():
    c = _rampa()
    c["sensibilidades"] = {
        "cenario": "base",
        "grades_1d": [{"premissa": "g2", "pontos": [7.0],
                        "triangulo": {"inputs": ["g", "roic"], "output": "rir"}}],
        "grades_2d": [],
    }
    with pytest.raises(CasoInvalido, match="rampa"):
        validar(c)


def test_rampa_sem_mercado_nem_reversa_continua_valida():
    """A recusa e da COMBINACAO, nao da rota isolada -- rampa sem os blocos
    novos continua exatamente tao valida quanto antes desta revisao."""
    assert carregar(FIXTURES / "caso_rampa.json")["rota"] == "rampa"


def test_grade_1d_e_2d_nao_quebram_com_keyerror_para_rota_sem_triangulo():
    """FIX 1: defesa em profundidade nos dois call sites de
    `_validar_triangulo` que faltavam a guarda de membership que o próprio
    módulo, nos outros três call sites (cenário, parte de SOTP, blended de
    materialidade), chama obrigatória. Inalcançável pela API pública depois
    da recusa no gate acima (rampa nunca chega a uma grade) -- mas uma
    rota futura sem triângulo, ou uma chamada direta como esta, não pode
    quebrar com KeyError cru."""
    from caso import _PREMISSAS_NAO_NUMERICAS, _PREMISSAS_POR_ROTA, _validar_grade_1d, _validar_grade_2d
    permitidas = _PREMISSAS_POR_ROTA["rampa"] - _PREMISSAS_NAO_NUMERICAS
    _validar_grade_1d({"premissa": "g2", "pontos": [7.0]}, "rampa", permitidas)
    _validar_grade_2d(
        {"premissa_x": "g2", "premissa_y": "wacc", "pontos_x": [7.0], "pontos_y": [10.0]},
        "rampa", permitidas)


# --------------------------------------------------------------------------
# FIX 2 (Importante): 'sotp.tipo' pulava `_exigir_texto` -- quarta
# instância da mesma classe de defeito neste módulo, no próprio módulo que
# construiu `_exigir_texto` para fechá-la estruturalmente. `tipo` era
# testado direto contra `_TIPOS_DE_SOTP` (um frozenset) sem passar pela
# guarda antes -- um valor não-hasheável (lista, dict) levantava TypeError
# cru em vez de CasoInvalido nomeando o campo.
# --------------------------------------------------------------------------

def _sotp() -> dict:
    return json.loads((FIXTURES / "caso_sotp_segmento.json").read_text(encoding="utf-8"))


def test_bloco_sotp_com_nome_errado_recusa_em_vez_de_ignorar():
    """F6 (achado do controlador, revisão final): 'stop' (typo de 'sotp')
    não bate no nome exato que `validar()` examina — antes desta correção, o
    caso inteiro validava normalmente com o bloco 'stop' aceito e IGNORADO
    em silêncio: o valuation saía sem a composição SOTP que o analista
    declarou, e a manchete (preço por ação) mudava."""
    c = _sotp()
    c["stop"] = c.pop("sotp")
    with pytest.raises(CasoInvalido, match="stop"):
        validar(c)


def test_sotp_tipo_lista_recusa():
    c = _sotp()
    c["sotp"]["tipo"] = ["safra"]
    with pytest.raises(CasoInvalido, match="tipo"):
        validar(c)


def test_sotp_tipo_dict_recusa():
    c = _sotp()
    c["sotp"]["tipo"] = {"valor": "safra"}
    with pytest.raises(CasoInvalido, match="tipo"):
        validar(c)


# --------------------------------------------------------------------------
# FIX 3 (Importante): 'sotp.topo.desconto_de_holding_pct' não tinha checagem
# de domínio -- o portão exigia a razão (não-vazia) mas aceitava qualquer
# número finito. Um valor negativo é um PRÊMIO disfarçado: a fórmula
# `equity * (1 - desconto/100)` inverte de sinal e AUMENTA o equity quando
# o desconto é negativo (confirmado: -25.0 leva equity de 6378.83 para
# 7973.54) -- uma operação fora da lista autorizada. Um valor >= 100 anula
# (100) ou inverte (>100) o equity.
# --------------------------------------------------------------------------

def test_desconto_de_holding_negativo_recusa():
    c = _sotp()
    c["sotp"]["topo"]["desconto_de_holding_pct"] = -25.0
    c["sotp"]["topo"]["razao_do_desconto"] = "x"
    with pytest.raises(CasoInvalido, match="domínio"):
        validar(c)


@pytest.mark.parametrize("valor", [0.0, 100.0, 140.0])
def test_desconto_de_holding_fora_do_dominio_aberto_recusa(valor):
    c = _sotp()
    c["sotp"]["topo"]["desconto_de_holding_pct"] = valor
    c["sotp"]["topo"]["razao_do_desconto"] = "x"
    with pytest.raises(CasoInvalido, match="domínio"):
        validar(c)


def test_desconto_de_holding_dentro_do_dominio_e_aceito():
    c = _sotp()
    c["sotp"]["topo"]["desconto_de_holding_pct"] = 15.0
    c["sotp"]["topo"]["razao_do_desconto"] = "controlador com histórico de não distribuir"
    validar(c)


def test_sotp_topo_chave_desconhecida_recusa_em_vez_de_ignorar():
    """F3 (onda de correção da revisão final, item 2): 'sotp.topo' não tinha
    vocabulário fechado — 'desconto_de_holding_pct'/'razao_do_desconto' são
    um PAR OPCIONAL com default silencioso (ausente, nenhum desconto de
    holding é aplicado). Um nome digitado errado (aqui, sem o 'de') nunca é
    lido por `topo.get("desconto_de_holding_pct")`: o desconto que o
    analista declarou desaparece da soma do topo em silêncio, mudando o
    equity do SOTP — mesma classe de 'degrau.perfil_transicao'/'degrau.fx'."""
    c = _sotp()
    c["sotp"]["topo"]["desconto_holding_pct"] = 15.0  # falta o 'de'
    c["sotp"]["topo"]["razao_do_desconto"] = "controlador com histórico de não distribuir"
    with pytest.raises(CasoInvalido, match="desconto_holding_pct"):
        validar(c)


# --------------------------------------------------------------------------
# FIX 5 (Importante): 'ponte' e 'acoes_diluidas' declarados DENTRO de uma
# parte de SOTP eram aceitos pelo portão e silenciosamente IGNORADOS por
# `sotp._compor_parte` (que chama `precificar_firm`/`precificar_rampa` sem
# nd_efetivo/acoes, de propósito -- "ponte por parte é o erro que a trava
# existe para impedir"). O analista que declara isso acredita que a ponte
# foi cruzada ali e recebe um número plausível, mas errado.
# --------------------------------------------------------------------------

def test_parte_com_ponte_recusa():
    c = _sotp()
    c["sotp"]["partes"][0]["ponte"] = {
        "divida_bruta": 0.0, "caixa_e_equivalentes": 0.0,
        "outros_ativos": 0.0, "outros_passivos": 0.0, "minoritarios": 0.0,
    }
    with pytest.raises(CasoInvalido, match="ponte"):
        validar(c)


def test_parte_com_acoes_diluidas_recusa():
    c = _sotp()
    c["sotp"]["partes"][0]["acoes_diluidas"] = 10.0
    with pytest.raises(CasoInvalido, match="acoes_diluidas"):
        validar(c)


# --------------------------------------------------------------------------
# Correção do rf no wrapper (f2844f3): 'mercado.rf' agora chega ao motor
# mesmo SEM 'reversa' — alimenta a âncora macro do gp (Damodaran). Antes
# daquela correção o rf sem reversa era inerte, e o gate só o validava com
# 'reversa' presente. Agora um rf inválido vira alerta falso em silêncio:
# 0.12 digitado como fração entraria no motor como 0,12% e a guarda
# acusaria todo gp acima disso. Mesma régua do FIX 4 sempre que 'rf' for
# declarado; 'erp' continua exigido só com reversa (sem ela não tem uso).
# --------------------------------------------------------------------------

@pytest.mark.parametrize("rf", [0.12, "12%", float("nan"), float("inf")])
def test_mercado_rf_sem_reversa_e_validado_porque_agora_chega_ao_motor(rf):
    c = _firm()
    c["mercado"] = {"rf": rf}
    with pytest.raises(CasoInvalido, match=r"mercado\.rf"):
        validar(c)


@pytest.mark.parametrize("rf", [12.0, 1.0, 0, -0.5, None])
def test_mercado_rf_valido_ou_ausente_sem_reversa_passa(rf):
    """Guarda contra recusar demais: pontos percentuais, 0, 1, rf negativo
    (existe em moedas com juro nominal abaixo de zero) e rf nulo — que o
    wrapper trata como ausente — continuam aceitos."""
    c = _firm()
    c["mercado"] = {"rf": rf}
    validar(c)  # nao levanta


# --------------------------------------------------------------------------
# Fatia 5D, Task 1 (D3 do plano docs/superpowers/plans/2026-09-14-v4-item5d-
# tese.md): bloco opcional 'fronteira_de_escopo' (§14 do desenho). A fronteira
# é metodologia, então é declaração do CASO — validada aqui, publicada pela
# integração (`resultados.fronteira_de_escopo`, tests/test_valuation_contrato.py)
# e rotulada pelo catálogo. Vocabulário fechado em todo nível: a classe e as
# chaves do bloco; nulo é ausência, como nos demais blocos opcionais.
# --------------------------------------------------------------------------

_FRONTEIRA_VALIDA = {
    "classe": "vida_economica_finita",
    "arquitetura_dominante": "fluxo de caixa até a exaustão da reserva provada",
    "razao": "mina única, com vida útil declarada no relatório de reservas",
}


def _firm_com_fronteira(fronteira) -> dict:
    c = _firm()
    c["fronteira_de_escopo"] = fronteira
    return c


@pytest.mark.parametrize("classe", ["vida_economica_finita", "reit_imobiliaria", "pre_lucro"])
def test_fronteira_de_escopo_com_cada_classe_do_desenho_e_aceita(classe):
    validar(_firm_com_fronteira({**_FRONTEIRA_VALIDA, "classe": classe}))  # nao levanta


def test_fronteira_de_escopo_nula_e_ausencia():
    validar(_firm_com_fronteira(None))  # nao levanta


def test_fronteira_com_classe_fora_do_vocabulario_recusa_nomeando_e_sugerindo():
    with pytest.raises(CasoInvalido) as erro:
        validar(_firm_com_fronteira({**_FRONTEIRA_VALIDA, "classe": "pre-lucro"}))
    mensagem = str(erro.value)
    assert "'pre-lucro'" in mensagem
    assert "Você quis dizer 'pre_lucro'?" in mensagem


@pytest.mark.parametrize("fronteira,nomeado", [
    pytest.param(["pre_lucro"], "'fronteira_de_escopo' não é um objeto", id="nao_e_objeto"),
    pytest.param({**_FRONTEIRA_VALIDA, "razão": "acento no nome da chave"}, "Você quis dizer 'razao'?",
                 id="chave_desconhecida_com_sugestao"),
    pytest.param({k: v for k, v in _FRONTEIRA_VALIDA.items() if k != "classe"},
                 "'fronteira_de_escopo.classe'", id="classe_ausente"),
    pytest.param({**_FRONTEIRA_VALIDA, "arquitetura_dominante": "   "},
                 "'fronteira_de_escopo.arquitetura_dominante'", id="arquitetura_em_branco"),
    pytest.param({k: v for k, v in _FRONTEIRA_VALIDA.items() if k != "razao"},
                 "'fronteira_de_escopo.razao'", id="razao_ausente"),
])
def test_fronteira_de_escopo_malformada_recusa_nomeando_o_campo(fronteira, nomeado):
    with pytest.raises(CasoInvalido) as erro:
        validar(_firm_com_fronteira(fronteira))
    assert nomeado in str(erro.value)



# --------------------------------------------------------------------------
# Fatia 5F, Task 2 (D5/D7 do plano docs/superpowers/plans/2026-09-15-v4-item5f-
# valuation.md): 'metrica_forward' e 'escala_monetaria', opcionais de topo com
# vocabulário fechado.
# --------------------------------------------------------------------------

_METRICA_FORWARD = {"tipo": "EBITDA", "valor": 1100.0, "periodo": "2026E", "fonte": "consenso sintético"}


def _com(base: dict, **campos) -> dict:
    return {**base, **campos}


def _fixture(nome: str) -> dict:
    return json.loads((FIXTURES / nome).read_text(encoding="utf-8"))


def test_metrica_forward_e_escala_monetaria_declaradas_sao_aceitas_e_nulas_sao_ausencia():
    validar(_com(_firm(), metrica_forward=dict(_METRICA_FORWARD), escala_monetaria="milhoes"))
    validar(_com(_equity(), metrica_forward={**_METRICA_FORWARD, "tipo": "LL"}, escala_monetaria="bilhoes"))
    validar(_com(_firm(), metrica_forward=None, escala_monetaria=None))


@pytest.mark.parametrize("caso,nomeado", [
    pytest.param(lambda: _com(_fixture("caso_rampa.json"), metrica_forward={**_METRICA_FORWARD, "tipo": "EBITDA0"}),
                 "'metrica_forward' presente na rota 'rampa'", id="na_rota_rampa"),
    pytest.param(lambda: _com(_fixture("caso_degrau.json"), metrica_forward={**_METRICA_FORWARD, "tipo": "LL"}),
                 "'metrica_forward' presente junto de 'degrau'", id="junto_de_degrau"),
    pytest.param(lambda: _com(_firm(), metrica_forward={**_METRICA_FORWARD, "tipo": "NOPAT"}),
                 "'metrica_forward.tipo' diferente de 'metrica_base.tipo'", id="tipo_diferente_do_da_base"),
    pytest.param(lambda: _com(_firm(), metrica_forward={**_METRICA_FORWARD, "valor": 0.0}),
                 "'metrica_forward.valor' inválido", id="valor_zero"),
    pytest.param(lambda: _com(_firm(), metrica_forward={**_METRICA_FORWARD, "valor": float("inf")}),
                 "'metrica_forward.valor' inválido", id="valor_nao_finito"),
    pytest.param(lambda: _com(_firm(), metrica_forward={**_METRICA_FORWARD, "periodos": "2026E"}),
                 "Você quis dizer 'periodo'?", id="chave_desconhecida_com_sugestao"),
    pytest.param(lambda: _com(_firm(), metrica_forward={k: v for k, v in _METRICA_FORWARD.items() if k != "fonte"}),
                 "'metrica_forward.fonte'", id="fonte_ausente"),
    pytest.param(lambda: _com(_firm(), escala_monetaria="milhões"),
                 "Você quis dizer 'milhoes'?", id="escala_fora_do_vocabulario"),
])
def test_recusas_da_metrica_forward_e_da_escala_monetaria_nomeiam_a_regra(caso, nomeado):
    with pytest.raises(CasoInvalido) as erro:
        validar(caso())
    assert nomeado in str(erro.value)


# --------------------------------------------------------------------------
# Fatia 5F, Task 3 (D6 do plano docs/superpowers/plans/2026-09-15-v4-item5f-
# valuation.md): 'conservacao_de_capital', só na rota firm com EBITDA, com
# vocabulário fechado em todo nível.
# --------------------------------------------------------------------------

def _conservacao_valida() -> dict:
    return {"capex_total": {"valor": 430.0, "fonte": "demonstração sintética", "ano_base": "corrente"},
            "dwc": {"valor": 20.0, "fonte": "demonstração sintética"}}


def _conservacao_com(grupo, campo: str, valor) -> dict:
    bloco = _conservacao_valida()
    (bloco if grupo is None else bloco[grupo])[campo] = valor
    return bloco


def _firm_nopat() -> dict:
    return _com(_firm(), metrica_base={"tipo": "NOPAT", "valor": 600.0, "fonte": "fixture sintética"})


def test_conservacao_de_capital_na_rota_firm_com_ebitda_e_aceita_e_nula_e_ausencia():
    validar(_com(_firm(), conservacao_de_capital=_conservacao_valida()))
    guidance = _conservacao_com("capex_total", "ano_base", "guidance_longo_prazo")
    guidance["dwc"]["valor"] = -35.0  # giro que libera caixa: ΔWC negativo é válido
    validar(_com(_firm(), conservacao_de_capital=guidance))
    validar(_com(_firm(), conservacao_de_capital=None))


@pytest.mark.parametrize("caso,nomeado", [
    pytest.param(lambda: _com(_equity(), conservacao_de_capital=_conservacao_valida()),
                 "bloco 'conservacao_de_capital' na rota 'equity'", id="rota_equity"),
    pytest.param(lambda: _com(_fixture("caso_rampa.json"), conservacao_de_capital=_conservacao_valida()),
                 "bloco 'conservacao_de_capital' na rota 'rampa'", id="rota_rampa"),
    pytest.param(lambda: _com(_firm_nopat(), conservacao_de_capital=_conservacao_valida()),
                 "com métrica 'NOPAT'", id="firm_com_nopat"),
    pytest.param(lambda: _com(_firm(), conservacao_de_capital=_conservacao_com("capex_total", "valor", 0.0)),
                 "'conservacao_de_capital.capex_total.valor' inválido", id="capex_zero"),
    pytest.param(lambda: _com(_firm(), conservacao_de_capital=_conservacao_com("capex_total", "valor", float("inf"))),
                 "'conservacao_de_capital.capex_total.valor' inválido", id="capex_nao_finito"),
    pytest.param(lambda: _com(_firm(), conservacao_de_capital=_conservacao_com("dwc", "valor", float("nan"))),
                 "'conservacao_de_capital.dwc.valor' inválido", id="dwc_nao_finito"),
    pytest.param(lambda: _com(_firm(), conservacao_de_capital=_conservacao_com("capex_total", "ano_base", "guidance")),
                 "'conservacao_de_capital.capex_total.ano_base' fora do vocabulário", id="ano_base_fora_do_vocabulario"),
    pytest.param(lambda: _com(_firm(), conservacao_de_capital=_conservacao_com(None, "capex", 1.0)),
                 "Você quis dizer 'capex_total'?", id="chave_desconhecida_no_bloco"),
    pytest.param(lambda: _com(_firm(), conservacao_de_capital=_conservacao_com("capex_total", "anobase", "corrente")),
                 "Você quis dizer 'ano_base'?", id="chave_desconhecida_no_capex"),
    pytest.param(lambda: _com(_firm(), conservacao_de_capital=_conservacao_com("dwc", "fontes", "balanço")),
                 "Você quis dizer 'fonte'?", id="chave_desconhecida_no_dwc"),
])
def test_recusas_da_conservacao_de_capital_nomeiam_a_regra(caso, nomeado):
    with pytest.raises(CasoInvalido) as erro:
        validar(caso())
    assert nomeado in str(erro.value)


# --------------------------------------------------------------------------
# Fatia 5G, Task 1 (D1 do plano docs/superpowers/plans/2026-09-15-v4-item5g-
# alternativas.md): 'escolhas_metodologicas', lista de escolhas declaradas com
# vocabulário fechado na chave, na posição do caso-base e nas sobreposições.
# --------------------------------------------------------------------------

def _escolha(**campos) -> dict:
    return {"chave": "rentabilidade", "no_caso_base": "central",
            "sobreposicoes": {"roic": 20.0}, **campos}


def test_escolhas_metodologicas_declaradas_sao_aceitas_e_nulas_sao_ausencia():
    validar(_com(_firm(), escolhas_metodologicas=[_escolha()]))
    validar(_com(_firm(), escolhas_metodologicas=[
        _escolha(no_caso_base="alternativa", sobreposicoes={"g": 8.0, "roic": 14.0}),
        _escolha(chave="crescimento", gatilho_disparou={"observavel": "Guidance acima do reinvestimento."}),
    ]))
    validar(_com(_equity(), escolhas_metodologicas=[_escolha(sobreposicoes={"roe": 20.0})]))
    validar(_com(_firm(), escolhas_metodologicas=None))


def test_alavanca_de_lucro_e_aceita_com_degrau_declarado():
    """D1: a alavanca de lucro é a escolha entre modelar o degrau com probabilidade e
    tratá-lo como opcionalidade — com o degrau declarado, ela é declarável."""
    caso = _fixture("caso_degrau.json")
    caso["escolhas_metodologicas"] = [
        {"chave": "alavanca_de_lucro", "no_caso_base": "central", "sobreposicoes": {"roe": 20.0}}]
    validar(caso)


@pytest.mark.parametrize("caso,nomeado", [
    pytest.param(lambda: _com(_firm(), escolhas_metodologicas=[_escolha(chave="rentabilidad")]),
                 "Você quis dizer 'rentabilidade'?", id="chave_fora_do_vocabulario_com_sugestao"),
    pytest.param(lambda: _com(_firm(), escolhas_metodologicas=[_escolha(), _escolha(sobreposicoes={"g": 8.0})]),
                 "'escolhas_metodologicas.1.chave' repetida", id="chave_repetida"),
    pytest.param(lambda: _com(_firm(), escolhas_metodologicas=[_escolha(sobreposicoes={})]),
                 "'escolhas_metodologicas.0.sobreposicoes' vazia", id="sobreposicoes_vazia"),
    pytest.param(lambda: _com(_firm(), escolhas_metodologicas=[_escolha(sobreposicoes={"roe": 20.0})]),
                 "não é alvo da rota 'firm'", id="sobreposicao_fora_da_rota"),
    pytest.param(lambda: _com(_firm(), escolhas_metodologicas=[_escolha(sobreposicoes={"roic": "20"})]),
                 "não é um número finito", id="sobreposicao_textual"),
    pytest.param(lambda: _com(_firm(), escolhas_metodologicas=[_escolha(no_caso_base="centra")]),
                 "Você quis dizer 'central'?", id="posicao_fora_do_vocabulario"),
    pytest.param(lambda: _com(_firm(), escolhas_metodologicas=[_escolha(chave="leitura_de_capacidade")]),
                 "que esta versão não precifica", id="leitura_de_capacidade_fora_da_v4"),
    pytest.param(lambda: _com(_firm(), escolhas_metodologicas=[_escolha(chave="alavanca_de_lucro")]),
                 "declarada num caso sem 'degrau'", id="alavanca_de_lucro_sem_degrau"),
    pytest.param(lambda: _com(_fixture("caso_sotp_segmento.json"), escolhas_metodologicas=[_escolha()]),
                 "presente junto de 'sotp'", id="junto_de_sotp"),
    pytest.param(lambda: _com(_firm(), escolhas_metodologicas=[_escolha(gatilho_disparou={"observaveis": "x"})]),
                 "Você quis dizer 'observavel'?", id="chave_desconhecida_no_gatilho"),
    pytest.param(lambda: _com(_firm(), escolhas_metodologicas=[_escolha(gatilho_disparou={"observavel": "  "})]),
                 "'escolhas_metodologicas.0.gatilho_disparou.observavel' ausente ou vazio", id="gatilho_sem_observavel"),
    pytest.param(lambda: _com(_firm(), escolhas_metodologicas=[_escolha(posicao="central")]),
                 "chave desconhecida em 'escolhas_metodologicas.0'", id="chave_desconhecida_na_escolha"),
    pytest.param(lambda: _com(_firm(), escolhas_metodologicas=[]),
                 "bloco 'escolhas_metodologicas' vazio", id="lista_vazia"),
    pytest.param(lambda: _com(_firm(), escolhas_metodologicas={"chave": "rentabilidade"}),
                 "'escolhas_metodologicas' não é uma lista", id="nao_e_lista"),
    pytest.param(lambda: _com(_firm(), escolhas_metodologicas=["rentabilidade"]),
                 "escolhas_metodologicas.0 não é um objeto", id="entrada_nao_e_objeto"),
])
def test_recusas_das_escolhas_metodologicas_nomeiam_a_regra(caso, nomeado):
    with pytest.raises(CasoInvalido) as erro:
        validar(caso())
    assert nomeado in str(erro.value)


# --------------------------------------------------------------------------
# Fatia 5G, Task 2 (D2/D3/D4 do plano docs/superpowers/plans/2026-09-15-v4-item5g-
# alternativas.md): 'retorno_exigido', 'pesos_de_probabilidade' e 'cross_check'.
# --------------------------------------------------------------------------

_CROSS_CHECK_EQUITY = {
    "rota": "equity",
    "metrica_base": {"tipo": "LL", "valor": 450.0},
    "ancora": "lucro líquido normalizado 2023-2025",
    "premissas": {"g": 5.0, "roe": 15.0, "ke": 12.0, "n": 10, "tv": "convergencia"},
}


def _firm_com_dois_cenarios() -> dict:
    c = _firm()
    c["cenarios"]["bull"] = json.loads(json.dumps(c["cenarios"]["base"]))
    c["cenario_base"] = "base"
    return c


def _cross_check_com(**campos) -> dict:
    return {**json.loads(json.dumps(_CROSS_CHECK_EQUITY)), **campos}


def test_as_tres_leituras_declaradas_sao_aceitas_e_nulas_sao_ausencia():
    caso = _firm_com_dois_cenarios()
    caso["retorno_exigido"] = {"taxa": 14.0}
    caso["pesos_de_probabilidade"] = {"base": 70.0, "bull": 30.0}
    caso["cross_check"] = _cross_check_com()
    validar(caso)
    validar(_com(_firm(), retorno_exigido=None, pesos_de_probabilidade=None, cross_check=None))


def test_cross_check_pela_rota_firm_exige_a_ponte_que_so_as_rotas_com_ponte_declaram():
    """A rota equity não admite 'ponte', então dela não sai cross-check firm; de um caso
    firm sai cross-check rampa, porque a ponte do caso é a mesma."""
    rampa = {"receita0": 1000.0, "ebitda0": 300.0, "da_parque": 80.0, "wk": 10.0,
             "kappa": 1.2, "g2": 3.0, "wacc": 10.0, "tax": 25.0, "t_rampa": 4,
             "n": 10, "util": 70.0, "tv": "convergencia"}
    validar(_com(_firm(), cross_check={"rota": "rampa", "metrica_base": {"tipo": "EBITDA0", "valor": 300.0},
                                       "ancora": "capacidade instalada do parque", "premissas": rampa}))


@pytest.mark.parametrize("caso,nomeado", [
    pytest.param(lambda: _com(_fixture("caso_sotp_segmento.json"), retorno_exigido={"taxa": 14.0}),
                 "'retorno_exigido' presente junto de 'sotp'", id="retorno_com_sotp"),
    pytest.param(lambda: _com(_fixture("caso_degrau.json"), retorno_exigido={"taxa": 14.0}),
                 "'retorno_exigido' presente junto de 'degrau'", id="retorno_com_degrau"),
    pytest.param(lambda: _com(_firm(), retorno_exigido={"taxa": 0.0}),
                 "'retorno_exigido.taxa' inválida", id="retorno_com_taxa_zero"),
    pytest.param(lambda: _com(_firm(), retorno_exigido={"taxa": 120.0}),
                 "'retorno_exigido.taxa' inválida", id="retorno_com_taxa_acima_de_100"),
    pytest.param(lambda: _com(_firm(), retorno_exigido={"taxa": float("nan")}),
                 "'retorno_exigido.taxa' inválida", id="retorno_com_taxa_nao_finita"),
    pytest.param(lambda: _com(_firm(), retorno_exigido={"taxas": 14.0}),
                 "Você quis dizer 'taxa'?", id="retorno_com_chave_desconhecida"),
    pytest.param(lambda: _com(_fixture("caso_sotp_segmento.json"),
                              pesos_de_probabilidade={"base": 70.0, "bull": 30.0}),
                 "'pesos_de_probabilidade' presente junto de 'sotp'", id="pesos_com_sotp"),
    pytest.param(lambda: _com(_firm(), pesos_de_probabilidade={"base": 100.0}),
                 "com menos de dois cenários", id="pesos_com_um_cenario_so"),
    pytest.param(lambda: _com(_firm_com_dois_cenarios(), pesos_de_probabilidade={"base": 70.0, "bull": 20.0}),
                 "soma 90.0, não 100.0", id="pesos_que_nao_somam_100"),
    pytest.param(lambda: _com(_firm_com_dois_cenarios(), pesos_de_probabilidade={"base": 70.0, "bea": 30.0}),
                 "'pesos_de_probabilidade.bea' aponta para cenário inexistente", id="peso_de_cenario_inexistente"),
    pytest.param(lambda: _com(_firm_com_dois_cenarios(), pesos_de_probabilidade={"base": 130.0, "bull": -30.0}),
                 "'pesos_de_probabilidade.bull' inválido", id="peso_negativo"),
    pytest.param(lambda: _com(_firm(), cross_check=_cross_check_com(rota="firm")),
                 "'cross_check.rota' é a rota do próprio caso", id="cross_check_na_rota_do_caso"),
    pytest.param(lambda: _com(_equity(), cross_check=_cross_check_com(
        rota="firm", metrica_base={"tipo": "EBITDA", "valor": 1000.0},
        premissas={"g": 5.0, "roic": 12.0, "wacc": 10.0, "n": 10, "da": 20.0, "tax": 25.0, "tv": "gordon"})),
        "mas o caso não declara 'ponte'", id="cross_check_firm_sem_ponte"),
    pytest.param(lambda: _com(_firm(), cross_check=_cross_check_com(rota="equty")),
                 "Você quis dizer 'equity'?", id="cross_check_com_rota_desconhecida"),
    pytest.param(lambda: _com(_firm(), cross_check=_cross_check_com(
        premissas={"g": 5.0, "roe": 15.0, "n": 10, "tv": "convergencia"})),
        "cross_check: premissa obrigatória 'ke' ausente", id="cross_check_com_vetor_incompleto"),
    pytest.param(lambda: _com(_firm(), cross_check=_cross_check_com(
        premissas={"g": 5.0, "roe": 15.0, "ke": 12.0, "n": 10, "tv": "convergencia", "roic": 12.0})),
        "cross_check: premissa 'roic' desconhecida", id="cross_check_com_premissa_de_outra_rota"),
    pytest.param(lambda: _com(_firm(), cross_check=_cross_check_com(metrica_base={"tipo": "EBITDA", "valor": 1.0})),
                 "'cross_check.metrica_base.tipo' incompatível com a rota 'equity'", id="cross_check_com_metrica_da_outra_rota"),
    pytest.param(lambda: _com(_firm(), cross_check=_cross_check_com(ancora="  ")),
                 "'cross_check.ancora' ausente ou vazia", id="cross_check_sem_ancora"),
    pytest.param(lambda: _com(_firm(), cross_check=_cross_check_com(rotas="equity")),
                 "chave desconhecida em 'cross_check'", id="cross_check_com_chave_desconhecida"),
])
def test_recusas_das_tres_leituras_nomeiam_a_regra(caso, nomeado):
    with pytest.raises(CasoInvalido) as erro:
        validar(caso())
    assert nomeado in str(erro.value)


# --------------------------------------------------------------------------
# Fatia 5G, Task 1b: os alvos que uma sobreposição alcança além da premissa numérica —
# a convenção terminal, `metrica_base.valor` e as linhas da ponte. Todo alvo fora desse
# conjunto continua recusado, com a mesma mensagem nomeada.
# --------------------------------------------------------------------------

@pytest.mark.parametrize("sobreposicoes", [
    pytest.param({"metrica_base": {"valor": 1100.0}}, id="metrica_base_valor"),
    pytest.param({"ponte": {"caixa_e_equivalentes": 0.0}}, id="uma_linha_da_ponte"),
    pytest.param({"ponte": {"divida_bruta": 900.0, "minoritarios": 50.0}}, id="duas_linhas_da_ponte"),
    pytest.param({"tv": "book"}, id="convencao_terminal"),
    pytest.param({"tv": "convergencia", "roic": 14.0, "metrica_base": {"valor": 900.0},
                  "ponte": {"outros_passivos": 10.0}}, id="alvos_misturados"),
])
def test_sobreposicoes_alcancam_os_alvos_declarados_do_caso(sobreposicoes):
    validar(_com(_firm(), escolhas_metodologicas=[_escolha(sobreposicoes=sobreposicoes)]))


@pytest.mark.parametrize("caso,nomeado", [
    pytest.param(lambda: _com(_firm(), escolhas_metodologicas=[
        _escolha(sobreposicoes={"acoes_diluidas": 120.0})]),
        "que não é alvo da rota 'firm'", id="alvo_fora_do_conjunto"),
    pytest.param(lambda: _com(_firm(), escolhas_metodologicas=[
        _escolha(sobreposicoes={"preco": {"valor": 60.0}})]),
        "que não é alvo da rota 'firm'", id="preco_nao_e_alvo"),
    pytest.param(lambda: _com(_equity(), escolhas_metodologicas=[
        _escolha(sobreposicoes={"ponte": {"divida_bruta": 900.0}})]),
        "cita 'ponte' na rota 'equity'", id="ponte_na_rota_sem_ponte"),
    pytest.param(lambda: _com(_firm(), escolhas_metodologicas=[
        _escolha(sobreposicoes={"ponte": {"caixa_e_equivalente": 0.0}})]),
        "Você quis dizer 'caixa_e_equivalentes'?", id="linha_de_ponte_desconhecida"),
    pytest.param(lambda: _com(_firm(), escolhas_metodologicas=[
        _escolha(sobreposicoes={"ponte": {}})]),
        "'escolhas_metodologicas.0.sobreposicoes.ponte' não é um objeto com ao menos uma linha",
        id="ponte_sem_linha"),
    pytest.param(lambda: _com(_firm(), escolhas_metodologicas=[
        _escolha(sobreposicoes={"ponte": {"divida_bruta": "900"}})]),
        "'escolhas_metodologicas.0.sobreposicoes.ponte.divida_bruta' não é um número finito",
        id="linha_de_ponte_textual"),
    pytest.param(lambda: _com(_firm(), escolhas_metodologicas=[
        _escolha(sobreposicoes={"metrica_base": {"tipo": "NOPAT"}})]),
        "chave desconhecida em 'escolhas_metodologicas.0.sobreposicoes.metrica_base'",
        id="metrica_base_com_tipo"),
    pytest.param(lambda: _com(_firm(), escolhas_metodologicas=[
        _escolha(sobreposicoes={"metrica_base": 1100.0})]),
        "'escolhas_metodologicas.0.sobreposicoes.metrica_base' não é um objeto",
        id="metrica_base_escalar"),
    pytest.param(lambda: _com(_firm(), escolhas_metodologicas=[
        _escolha(sobreposicoes={"metrica_base": {"valor": float("inf")}})]),
        "'escolhas_metodologicas.0.sobreposicoes.metrica_base.valor' não é um número finito",
        id="metrica_base_nao_finita"),
    pytest.param(lambda: _com(_firm(), escolhas_metodologicas=[
        _escolha(sobreposicoes={"tv": "perpetuidade"})]),
        "'escolhas_metodologicas.0.sobreposicoes.tv' fora do vocabulário", id="tv_fora_do_vocabulario"),
    pytest.param(lambda: _com(_firm(), escolhas_metodologicas=[
        _escolha(sobreposicoes={"tv": 3.0})]),
        "'escolhas_metodologicas.0.sobreposicoes.tv' não é texto", id="tv_numerica"),
    pytest.param(lambda: _com(_firm(), escolhas_metodologicas=[
        _escolha(sobreposicoes={"mid_year": True})]),
        "premissa não numérica que a sobreposição não alcança", id="mid_year_nao_e_alcancado"),
    pytest.param(lambda: _com(_equity(), escolhas_metodologicas=[
        _escolha(sobreposicoes={"politica_tv": "encerra"})]),
        "premissa não numérica que a sobreposição não alcança", id="politica_tv_nao_e_alcancada"),
])
def test_recusas_dos_alvos_de_sobreposicao_nomeiam_a_regra(caso, nomeado):
    with pytest.raises(CasoInvalido) as erro:
        validar(caso())
    assert nomeado in str(erro.value)


# --------------------------------------------------------------------------
# Fatia 5H, Task 1 (D1): o consenso declarado da reversa — o confronto temporal da §4
# da aplicação. Uma recusa por regra, cada uma nomeando o campo.
# --------------------------------------------------------------------------

_CONSENSO_VALIDO = {"t1": {"valor": 1040.0, "periodo": "2026E"},
                    "t2": {"valor": 1100.0, "periodo": "2027E"}}


def _com_consenso(consenso) -> dict:
    c = _reversa()
    c["reversa"]["consenso"] = consenso
    return c


def test_consenso_valido_com_os_dois_pontos_passa():
    validar(_com_consenso(json.loads(json.dumps(_CONSENSO_VALIDO))))
    validar(_com_consenso({"t1": {"valor": 1040.0, "periodo": "2026E"}}))


@pytest.mark.parametrize("consenso,trechos", [
    ([{"valor": 1040.0}], ["'reversa.consenso' não é um objeto"]),
    ({}, ["'reversa.consenso' sem 't1'"]),
    ({"t2": {"valor": 1100.0, "periodo": "2027E"}}, ["'reversa.consenso' sem 't1'"]),
    ({"t1": {"valor": 1040.0, "periodo": "2026E"}, "t3": {"valor": 1.0, "periodo": "2028E"}},
     ["chave desconhecida em 'reversa.consenso'", "'t3'"]),
    ({"t1": {"valor": 1040.0, "periodo": "2026E", "fonte": "x"}},
     ["chave desconhecida em 'reversa.consenso.t1'", "'fonte'"]),
    ({"t1": {"valor": 0.0, "periodo": "2026E"}}, ["'reversa.consenso.t1.valor' inválido"]),
    ({"t1": {"valor": -10.0, "periodo": "2026E"}}, ["'reversa.consenso.t1.valor' inválido"]),
    ({"t1": {"valor": float("inf"), "periodo": "2026E"}}, ["'reversa.consenso.t1.valor' inválido"]),
    ({"t1": {"valor": "1040", "periodo": "2026E"}}, ["'reversa.consenso.t1.valor' inválido"]),
    ({"t1": {"valor": 1040.0, "periodo": "   "}}, ["'reversa.consenso.t1.periodo' ausente ou vazio"]),
    ({"t1": {"valor": 1040.0}}, ["'reversa.consenso.t1.periodo' ausente ou vazio"]),
    ({"t1": {"valor": 1040.0, "periodo": "2026E"}, "t2": 1100.0},
     ["'reversa.consenso.t2' não é um objeto"]),
], ids=["nao-objeto", "vazio", "so-t2", "ponto-desconhecido", "chave-do-ponto-desconhecida",
        "valor-zero", "valor-negativo", "valor-nao-finito", "valor-texto", "periodo-vazio",
        "periodo-ausente", "ponto-nao-objeto"])
def test_consenso_malformado_recusa_nomeando(consenso, trechos):
    with pytest.raises(CasoInvalido) as erro:
        validar(_com_consenso(consenso))
    for trecho in trechos:
        assert trecho in str(erro.value), str(erro.value)


def test_chave_desconhecida_na_reversa_recusa_com_sugestao():
    """O bloco 'reversa' passou a ter vocabulário fechado: sem isso, um 'consensos'
    digitado errado sairia ignorado — o caso declararia o confronto temporal e o motor
    rodaria sem ele."""
    c = _reversa()
    c["reversa"]["consensos"] = json.loads(json.dumps(_CONSENSO_VALIDO))
    with pytest.raises(CasoInvalido) as erro:
        validar(c)
    assert "chave desconhecida em 'reversa'" in str(erro.value)
    assert "Você quis dizer 'consenso'?" in str(erro.value)


def test_consenso_fora_da_reversa_e_chave_de_topo_desconhecida():
    """O consenso só existe DENTRO da reversa (D1): declarado no topo do caso, é a
    recusa de chave de topo desconhecida, nomeando-o — nunca um bloco aceito e ignorado."""
    c = _firm()
    c["consenso"] = json.loads(json.dumps(_CONSENSO_VALIDO))
    with pytest.raises(CasoInvalido) as erro:
        validar(c)
    assert "chave de topo desconhecida" in str(erro.value).lower()
    assert "consenso" in str(erro.value)
