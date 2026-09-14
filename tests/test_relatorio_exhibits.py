"""Contrato dos exhibits e rastreabilidade -- sem render (fatia 5B, item 5,
Task 1).

Ver docs/superpowers/plans/2026-09-11-v4-item5b-graficos.md, seção "Task
1", para a lista de cenários. A decisão que esta fatia acrescenta sobre a
§10 do desenho: uma spec de exhibit NUNCA declara número nenhum -- série
`direta` aponta para um campo de `entrega.dados`, `derivada` traz uma
fórmula sobre campos do MESMO dataset, `engine` aponta para um caminho de
`resultados`; o builder lê os valores. `exhibits.resolver`/`qc.avaliar`
são exercidos diretamente (funções puras) -- Task 1 não liga isto a
`builder.py`/`render.py` (Task 2/3 fazem isso), então não há CLI para
testar aqui além do contrato (código 1), que passa por `entrega.carregar`.

Raízes/entregas vêm de `tests/relatorio_apoio.py` (`montar_entrega`, que
roda `avaliar()` de verdade sobre uma fixture de caso e agora aceita
`dados=`/`exhibits=` opcionais) -- nenhum `resultados.json` é forjado à
mão neste arquivo.
"""

import json
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
SCRIPTS = RAIZ / "skills" / "er-relatorio" / "scripts"

sys.path.insert(0, str(SCRIPTS))
import entrega  # noqa: E402
import exhibits  # noqa: E402
import qc  # noqa: E402

sys.path.insert(0, str(RAIZ / "tests"))
import relatorio_apoio as apoio  # noqa: E402

CATALOGO = json.loads(
    (RAIZ / "skills" / "er-valuation" / "assets" / "catalogo_apresentacao.json").read_text(encoding="utf-8"))

FIXTURE = "caso_reversa_firm.json"


def _dataset(x, campos):
    return {"ledger": [], "x": x, "campos": campos}


# --------------------------------------------------------------------------
# G2 -- enum fechado de `tipo` (interface produzida por esta fatia).
# --------------------------------------------------------------------------

def test_enum_de_tipos_fechado():
    """B7 (onda de correção da revisão final, achado F11): `waterfall`/
    `matriz` SAEM do enum aceito. Os dois existem como PAINÉIS da aba
    Valuation (alimentados por `resultados` direto), nunca como exhibit
    declarado: a spec resolvida de um exhibit é `eixoX + séries de números`,
    que não expressa `{rotulo, valor, sinal}` nem uma grade 2D. Até esta
    correção, `tipo: "waterfall"` saía com rc 0 e caía no fallback textual no
    browser. `TIPOS_PROPRIOS` continua declarado como vocabulário
    RESERVADO."""
    assert exhibits.TIPOS_CARTESIANOS == {"linha", "barras", "area", "empilhado", "dispersao"}
    assert exhibits.TIPOS_PROPRIOS == {"waterfall", "matriz"}
    assert exhibits.TIPOS == exhibits.TIPOS_CARTESIANOS | {"tabela"}
    assert not (exhibits.TIPOS & exhibits.TIPOS_PROPRIOS)
    assert "decomposicao" not in exhibits.TIPOS  # G2: fora desta fatia, de propósito


# --------------------------------------------------------------------------
# avaliar_formula -- avaliador fechado (`ast.parse` + caminhada explícita,
# nunca `eval`/`exec`). "fórmula com __import__ ou nome estranho" cobre as
# duas causas de `FormulaInvalida`.
# --------------------------------------------------------------------------

def test_avaliar_formula_aceita_aritmetica_fechada():
    campos = {"ebitda": [20.0, 24.0, 30.0], "receita": [100.0, 120.0, 120.0]}
    assert exhibits.avaliar_formula("ebitda / receita", campos) == pytest.approx([0.2, 0.2, 0.25])
    assert exhibits.avaliar_formula("(receita - ebitda) / receita", campos) == pytest.approx([0.8, 0.8, 0.75])


def test_avaliar_formula_recusa_chamada_hostil():
    with pytest.raises(exhibits.FormulaInvalida):
        exhibits.avaliar_formula("__import__('os').system('echo oi')", {"x": [1.0]})


def test_avaliar_formula_recusa_nome_fora_dos_campos():
    with pytest.raises(exhibits.FormulaInvalida, match="foo_estranho"):
        exhibits.avaliar_formula("foo_estranho + 1", {"receita": [1.0, 2.0]})


# --------------------------------------------------------------------------
# `exhibits.resolver` -- caminho feliz das três proveniências (G3). Nenhum
# número declarado na spec: o builder lê os valores de `dados`/`resultados`.
# --------------------------------------------------------------------------

def test_serie_direta_resolve_numeros_do_dataset():
    dados = {"fin": _dataset(["2023", "2024", "2025"], {"receita": [100.0, 110.0, 120.0]})}
    exhibit = {
        "id": "fin", "pergunta": "Como a receita evoluiu no período?", "tipo": "linha",
        "series": [{"derivacao": "direta", "fonte": "fin.receita"}],
    }
    entrega_dict = apoio.montar_entrega(FIXTURE, dados=dados, exhibits=[exhibit])

    resolvidos, log = exhibits.resolver(entrega_dict)

    assert resolvidos[0]["series"][0]["valores"] == [100.0, 110.0, 120.0]
    assert log == [{"exhibit": "fin", "serie": 0, "origem": "direta", "detalhe": "fin.receita"}]


def test_serie_derivada_reproduz_a_margem_esperada():
    dados = {"fin": _dataset(["2023", "2024", "2025"],
                              {"receita": [100.0, 110.0, 120.0], "ebitda": [20.0, 22.0, 30.0]})}
    exhibit = {
        "id": "fin", "pergunta": "Como a margem EBITDA evoluiu?", "tipo": "linha",
        "series": [{"derivacao": "derivada", "fonte": "fin", "formula": "ebitda / receita",
                    "formula_nota": "margem EBITDA"}],
    }
    entrega_dict = apoio.montar_entrega(FIXTURE, dados=dados, exhibits=[exhibit])

    resolvidos, log = exhibits.resolver(entrega_dict)

    margem_esperada = [20.0 / 100.0, 22.0 / 110.0, 30.0 / 120.0]
    assert resolvidos[0]["series"][0]["valores"] == pytest.approx(margem_esperada)
    assert log == [{"exhibit": "fin", "serie": 0, "origem": "derivada", "detalhe": "fin: ebitda / receita"}]


def test_duas_series_derivadas_podem_ler_o_mesmo_dataset():
    """G3 corrigido (11/09/2026): a série `derivada` DECLARA `fonte` -- o
    acoplamento antigo (dataset inferido pelo `id` do exhibit) impedia dois
    exhibits de compartilharem um dataset, já que cada um buscaria
    `dados[<seu próprio id>]`. Aqui, dois exhibits com ids DIFERENTES
    ('margem' e 'participacao_de_custos') leem o MESMO dataset ('fin') --
    só passa com `fonte` declarada explicitamente; a inferência antiga
    buscaria `dados['margem']`/`dados['participacao_de_custos']`, nenhum
    dos dois existente, e teria recusado com `serie_nao_rastreavel`."""
    dados = {"fin": _dataset(["2023", "2024", "2025"],
                              {"receita": [100.0, 110.0, 120.0], "ebitda": [20.0, 22.0, 30.0]})}
    exhibit_margem = {
        "id": "margem", "pergunta": "Como a margem EBITDA evoluiu?", "tipo": "linha",
        "series": [{"derivacao": "derivada", "fonte": "fin", "formula": "ebitda / receita",
                    "formula_nota": "margem EBITDA"}],
    }
    exhibit_custos = {
        "id": "participacao_de_custos", "pergunta": "Qual a participação dos custos na receita?",
        "tipo": "linha",
        "series": [{"derivacao": "derivada", "fonte": "fin", "formula": "(receita - ebitda) / receita",
                    "formula_nota": "participação de custos na receita"}],
    }
    entrega_dict = apoio.montar_entrega(FIXTURE, dados=dados, exhibits=[exhibit_margem, exhibit_custos])

    resolvidos, log = exhibits.resolver(entrega_dict)

    margem_esperada = [20.0 / 100.0, 22.0 / 110.0, 30.0 / 120.0]
    custos_esperado = [0.8, 0.8, 0.75]
    assert resolvidos[0]["series"][0]["valores"] == pytest.approx(margem_esperada)
    assert resolvidos[1]["series"][0]["valores"] == pytest.approx(custos_esperado)
    assert log == [
        {"exhibit": "margem", "serie": 0, "origem": "derivada", "detalhe": "fin: ebitda / receita"},
        {"exhibit": "participacao_de_custos", "serie": 0, "origem": "derivada",
         "detalhe": "fin: (receita - ebitda) / receita"},
    ]


def test_serie_engine_le_caminho_real_de_resultados():
    """G3: série `engine` não usa `entrega.dados` nenhum -- lê
    `resultados` direto (aqui, o preço por ação da manchete)."""
    exhibit = {
        "id": "preco_base", "pergunta": "Qual o preço justo no cenário base?", "tipo": "tabela",
        "series": [{"derivacao": "engine", "chave": "resultados:manchete.preco_acao"}],
    }
    entrega_dict = apoio.montar_entrega(FIXTURE, exhibits=[exhibit])

    resolvidos, log = exhibits.resolver(entrega_dict)

    assert resolvidos[0]["series"][0]["valores"] == entrega_dict["resultados"]["manchete"]["preco_acao"]
    assert log == [{"exhibit": "preco_base", "serie": 0, "origem": "engine",
                    "detalhe": "resultados:manchete.preco_acao"}]


# --------------------------------------------------------------------------
# QC -- HARD FAIL de rastreabilidade (G1-G4). Cada teste constrói UMA
# entrega com UM problema e chama `qc.avaliar` direto (mesmo padrão de
# `tests/test_relatorio_render.py::_preparar`) -- Task 1 não liga isto a
# `builder.py`, então não há CLI/subprocess para exercer aqui.
# --------------------------------------------------------------------------

def test_fonte_para_campo_inexistente_e_hard_fail_nomeando_exhibit_e_serie():
    dados = {"fin": _dataset(list(range(12)), {"receita": [float(i) for i in range(12)]})}
    exhibit = {
        "id": "fin", "pergunta": "pergunta válida", "tipo": "linha",
        "series": [{"derivacao": "direta", "fonte": "fin.campo_que_nao_existe"}],
    }
    entrega_dict = apoio.montar_entrega(FIXTURE, dados=dados, exhibits=[exhibit])

    achados = qc.avaliar(entrega_dict, CATALOGO, html=None)

    achado = next(a for a in achados if a.codigo == "serie_nao_rastreavel")
    assert achado.nivel == "HARD_FAIL"
    assert achado.params["exhibit"] == "fin"
    assert achado.params["serie"] == 0
    assert achado.onde == "analise.exhibits.fin.series.0"


def test_formula_hostil_e_hard_fail():
    dados = {"fin": _dataset(list(range(12)), {"receita": [float(i) for i in range(12)]})}
    exhibit = {
        "id": "fin", "pergunta": "pergunta válida", "tipo": "linha",
        "series": [{"derivacao": "derivada", "fonte": "fin",
                    "formula": "__import__('os').system('echo oi')", "formula_nota": "hostil"}],
    }
    entrega_dict = apoio.montar_entrega(FIXTURE, dados=dados, exhibits=[exhibit])

    achados = qc.avaliar(entrega_dict, CATALOGO, html=None)

    achado = next(a for a in achados if a.codigo == "formula_invalida")
    assert achado.nivel == "HARD_FAIL"
    assert achado.params["exhibit"] == "fin"


def test_serie_derivada_sem_fonte_e_hard_fail():
    """G3 corrigido: sem fallback para o `id` do exhibit -- uma `derivada`
    sem `fonte` é 'não rastreável', o mesmo código de uma `direta` cuja
    fonte não resolve (`serie_nao_rastreavel`). Constrói a entrega direto
    (sem passar por `entrega.carregar`, mesmo padrão dos testes de QC
    acima) -- uma entrega assim nunca chegaria a este ponto pelo caminho
    real (o contrato já recusaria a chave 'fonte' ausente, código 1), mas
    `resolver_serie` precisa recusar por conta própria mesmo assim, porque
    também é chamado por `qc.avaliar` sobre entregas que não passaram por
    validação de contrato nenhuma."""
    dados = {"fin": _dataset(list(range(12)), {"receita": [float(i) for i in range(12)]})}
    exhibit = {
        "id": "fin", "pergunta": "pergunta válida", "tipo": "linha",
        "series": [{"derivacao": "derivada", "formula": "receita * 2", "formula_nota": "dobro"}],
    }
    entrega_dict = apoio.montar_entrega(FIXTURE, dados=dados, exhibits=[exhibit])

    achados = qc.avaliar(entrega_dict, CATALOGO, html=None)

    achado = next(a for a in achados if a.codigo == "serie_nao_rastreavel")
    assert achado.nivel == "HARD_FAIL"
    assert achado.params["exhibit"] == "fin"
    assert achado.params["serie"] == 0
    assert achado.onde == "analise.exhibits.fin.series.0"


def test_overlay_com_chave_inexistente_e_hard_fail():
    dados = {"fin": _dataset(list(range(12)), {"receita": [float(i) for i in range(12)]})}
    exhibit = {
        "id": "fin", "pergunta": "pergunta válida", "tipo": "linha",
        "series": [{"derivacao": "direta", "fonte": "fin.receita"}],
        "overlays": [{"chave": "resultados:caminho.que.nao.existe"}],
    }
    entrega_dict = apoio.montar_entrega(FIXTURE, dados=dados, exhibits=[exhibit])

    achados = qc.avaliar(entrega_dict, CATALOGO, html=None)

    achado = next(a for a in achados if a.codigo == "overlay_nao_resolvido")
    assert achado.nivel == "HARD_FAIL"
    assert achado.params["exhibit"] == "fin"
    assert achado.params["overlay"] == 0


def test_serie_curta_sem_nota_janela_e_quality_warning_que_nao_impede_emitir():
    dados = {"fin": _dataset([1, 2, 3], {"receita": [1.0, 2.0, 3.0]})}
    exhibit = {
        "id": "fin", "pergunta": "pergunta válida", "tipo": "linha",
        "series": [{"derivacao": "direta", "fonte": "fin.receita"}],
    }
    entrega_dict = apoio.montar_entrega(FIXTURE, dados=dados, exhibits=[exhibit])

    achados = qc.avaliar(entrega_dict, CATALOGO, html=None)

    achado = next(a for a in achados if a.codigo == "serie_curta_sem_nota_janela")
    assert achado.nivel == "QUALITY_WARNING"
    assert not any(a.nivel == "HARD_FAIL" for a in achados), "warning não pode impedir emitir"


def test_serie_com_nota_janela_nao_dispara_warning():
    """Controle: a mesma série curta, com `nota_janela` explicando o
    recorte, não dispara o warning -- a regra não é falso positivo quando o
    analista já declarou a limitação."""
    dados = {"fin": _dataset([1, 2, 3], {"receita": [1.0, 2.0, 3.0]})}
    exhibit = {
        "id": "fin", "pergunta": "pergunta válida", "tipo": "linha",
        "nota_janela": "só os últimos {{livre:3}} anos têm dado comparável",
        "series": [{"derivacao": "direta", "fonte": "fin.receita"}],
    }
    entrega_dict = apoio.montar_entrega(FIXTURE, dados=dados, exhibits=[exhibit])

    achados = qc.avaliar(entrega_dict, CATALOGO, html=None)

    assert not any(a.codigo == "serie_curta_sem_nota_janela" for a in achados)


# --------------------------------------------------------------------------
# Contrato (código 1) -- `tipo` fora do enum fechado (G2). Vai por
# `entrega.carregar`, a mesma função que `builder.py` chama para decidir a
# recusa de contrato.
# --------------------------------------------------------------------------

def test_tipo_inventado_recusa_contrato(tmp_path):
    exhibit = {
        "id": "fin", "pergunta": "pergunta válida", "tipo": "pizza",
        "series": [{"derivacao": "direta", "fonte": "fin.receita"}],
    }
    entrega_dict = apoio.montar_entrega(FIXTURE, exhibits=[exhibit])
    raiz = tmp_path / "tipo_invalido"
    apoio.escrever_raiz(raiz, entrega_dict)

    with pytest.raises(entrega.EntregaInvalida, match="pizza"):
        entrega.carregar(raiz)


@pytest.mark.parametrize("tipo", sorted(exhibits.TIPOS_PROPRIOS))
def test_tipo_de_painel_proprio_recusa_contrato(tipo, tmp_path):
    """B7 (achado F11): `waterfall`/`matriz` não têm renderizador de exhibit
    -- e agora são recusados PELO CONTRATO (código 1, nomeando o tipo), em
    vez de sair com rc 0 e cair no fallback textual no browser."""
    exhibit = {
        "id": "w", "pergunta": "pergunta válida", "tipo": tipo,
        "series": [{"derivacao": "engine", "chave": "resultados:ponte.nd_efetivo"}],
    }
    entrega_dict = apoio.montar_entrega(FIXTURE, exhibits=[exhibit])
    raiz = tmp_path / f"tipo_proprio_{tipo}"
    apoio.escrever_raiz(raiz, entrega_dict)

    with pytest.raises(entrega.EntregaInvalida, match=tipo):
        entrega.carregar(raiz)


# --------------------------------------------------------------------------
# B1 (achado F3): séries de datasets com eixos x diferentes no MESMO
# exhibit. `serie_de_tamanho_incompativel` compara cada série com o `x` do
# SEU dataset, nunca as séries entre si -- dois datasets de mesmo
# comprimento e conteúdo diferente passavam com `achados: []`.
# --------------------------------------------------------------------------

def _dois_datasets_com_x_diferente():
    return {
        "fin": _dataset(["2021", "2022", "2023", "2024"], {"margem": [0.20, 0.21, 0.22, 0.23]}),
        "peers": _dataset(["ALFA", "BETA", "GAMA", "DELTA"], {"margem": [0.31, 0.32, 0.33, 0.34]}),
    }


def test_series_de_datasets_com_eixos_diferentes_e_hard_fail():
    exhibit = {
        "id": "mix", "pergunta": "pergunta válida", "tipo": "linha",
        "series": [{"derivacao": "direta", "fonte": "fin.margem"},
                   {"derivacao": "direta", "fonte": "peers.margem"}],
    }
    entrega_dict = apoio.montar_entrega(
        FIXTURE, dados=_dois_datasets_com_x_diferente(), exhibits=[exhibit])

    achados = qc.avaliar(entrega_dict, CATALOGO, html=None)

    achado = next(a for a in achados if a.codigo == "series_de_datasets_incompativeis")
    assert achado.nivel == "HARD_FAIL"
    assert achado.onde == "analise.exhibits.mix"
    assert {achado.params["dataset_a"], achado.params["dataset_b"]} == {"fin", "peers"}


def test_series_de_datasets_com_o_mesmo_eixo_nao_disparam():
    """Controle: dois datasets DIFERENTES com o MESMO `x` continuam válidos
    no mesmo exhibit (é o caso legítimo de comparar duas fontes ano a ano)."""
    dados = {
        "fin": _dataset(["2021", "2022", "2023", "2024"], {"margem": [0.20, 0.21, 0.22, 0.23]}),
        "setor": _dataset(["2021", "2022", "2023", "2024"], {"margem": [0.31, 0.32, 0.33, 0.34]}),
    }
    exhibit = {
        "id": "mix", "pergunta": "pergunta válida", "tipo": "linha",
        "series": [{"derivacao": "direta", "fonte": "fin.margem"},
                   {"derivacao": "direta", "fonte": "setor.margem"}],
    }
    entrega_dict = apoio.montar_entrega(FIXTURE, dados=dados, exhibits=[exhibit])

    achados = qc.avaliar(entrega_dict, CATALOGO, html=None)

    assert not any(a.codigo == "series_de_datasets_incompativeis" for a in achados)


# --------------------------------------------------------------------------
# B2 (achado F5): uma série `engine` é NÚMERO -- a mesma checagem que
# `resolver_overlay` já fazia. Um dict do motor inteiro ou um texto entravam
# no payload como série, com rc 0 e QC limpo.
# --------------------------------------------------------------------------

@pytest.mark.parametrize("chave", ["resultados:origem.metodologia", "resultados:rota"])
def test_serie_engine_nao_numerica_e_hard_fail(chave):
    exhibit = {
        "id": "e", "pergunta": "pergunta válida", "tipo": "linha",
        "series": [{"derivacao": "engine", "chave": chave}],
    }
    entrega_dict = apoio.montar_entrega(FIXTURE, exhibits=[exhibit])

    achados = qc.avaliar(entrega_dict, CATALOGO, html=None)

    achado = next(a for a in achados if a.codigo == "serie_nao_rastreavel")
    assert achado.nivel == "HARD_FAIL"
    assert achado.params["referencia"] == chave


def test_serie_engine_com_lista_de_numeros_continua_valida():
    """Controle: número escalar e LISTA de números finitos continuam
    aceitos -- a checagem nova não estreita o que já era rastreável."""
    exhibit = {
        "id": "e", "pergunta": "pergunta válida", "tipo": "linha",
        "series": [{"derivacao": "engine", "chave": "resultados:manchete.preco_acao"},
                   {"derivacao": "engine",
                    "chave": "resultados:sensibilidades.grades_2d.0.pontos_x"}],
    }
    entrega_dict = apoio.montar_entrega(FIXTURE, exhibits=[exhibit])

    achados = qc.avaliar(entrega_dict, CATALOGO, html=None)
    resolvidos, _log = exhibits.resolver(entrega_dict)

    assert not any(a.codigo == "serie_nao_rastreavel" for a in achados)
    assert resolvidos[0]["series"][1]["valores"] == \
        entrega_dict["resultados"]["sensibilidades"]["grades_2d"][0]["pontos_x"]


# --------------------------------------------------------------------------
# B3 (achado F6), casos a e b: a fórmula exige campos paralelos e numéricos.
# Os dois derrubavam o builder com traceback cru (IndexError/TypeError), rc 1
# e nenhum `qc.json` -- a partir de entrada que o contrato ACEITA.
# --------------------------------------------------------------------------

def test_formula_sobre_campos_de_comprimentos_diferentes_e_formula_invalida():
    with pytest.raises(exhibits.FormulaInvalida, match="comprimentos diferentes"):
        exhibits.avaliar_formula("a + b", {"a": [1.0, 2.0, 3.0], "b": [1.0]})


def test_formula_sobre_campo_com_null_e_formula_invalida():
    with pytest.raises(exhibits.FormulaInvalida, match="não numérico"):
        exhibits.avaliar_formula("ebitda / receita",
                                 {"ebitda": [20.0, None, 30.0], "receita": [100.0, 110.0, 120.0]})


def test_null_em_campo_que_a_formula_nao_le_nao_atrapalha():
    """A checagem é sobre os campos que a fórmula REFERENCIA -- um `null`
    noutro campo do mesmo dataset não é assunto dela."""
    campos = {"ebitda": [20.0, 22.0], "receita": [100.0, 110.0], "outro": [None, None]}
    assert exhibits.avaliar_formula("ebitda / receita", campos) == pytest.approx([0.2, 0.2])


def test_serie_direta_com_null_continua_emitindo():
    """A assimetria documentada: `null` é "o jeito natural de um dataset
    marcar ponto ausente" numa série `direta` (vira travessão no gráfico) --
    só a `derivada` recusa, porque uma fórmula sobre ausência não tem
    resultado defensável. O que mudou é a FORMA da recusa, não esta
    tolerância."""
    dados = {"fin": _dataset([1, 2, 3], {"receita": [1.0, None, 3.0]})}
    exhibit = {
        "id": "fin", "pergunta": "pergunta válida", "tipo": "linha",
        "nota_janela": "janela curta de propósito",
        "series": [{"derivacao": "direta", "fonte": "fin.receita"}],
    }
    entrega_dict = apoio.montar_entrega(FIXTURE, dados=dados, exhibits=[exhibit])

    achados = qc.avaliar(entrega_dict, CATALOGO, html=None)

    assert not any(a.nivel == "HARD_FAIL" for a in achados), achados
