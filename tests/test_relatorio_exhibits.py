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
    assert exhibits.TIPOS_CARTESIANOS == {"linha", "barras", "area", "empilhado", "dispersao"}
    assert exhibits.TIPOS_PROPRIOS == {"waterfall", "matriz"}
    assert exhibits.TIPOS == exhibits.TIPOS_CARTESIANOS | exhibits.TIPOS_PROPRIOS | {"tabela"}
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
        "series": [{"derivacao": "derivada", "formula": "ebitda / receita", "formula_nota": "margem EBITDA"}],
    }
    entrega_dict = apoio.montar_entrega(FIXTURE, dados=dados, exhibits=[exhibit])

    resolvidos, log = exhibits.resolver(entrega_dict)

    margem_esperada = [20.0 / 100.0, 22.0 / 110.0, 30.0 / 120.0]
    assert resolvidos[0]["series"][0]["valores"] == pytest.approx(margem_esperada)
    assert log == [{"exhibit": "fin", "serie": 0, "origem": "derivada", "detalhe": "ebitda / receita"}]


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
        "series": [{"derivacao": "derivada", "formula": "__import__('os').system('echo oi')",
                    "formula_nota": "hostil"}],
    }
    entrega_dict = apoio.montar_entrega(FIXTURE, dados=dados, exhibits=[exhibit])

    achados = qc.avaliar(entrega_dict, CATALOGO, html=None)

    achado = next(a for a in achados if a.codigo == "formula_invalida")
    assert achado.nivel == "HARD_FAIL"
    assert achado.params["exhibit"] == "fin"


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
        "nota_janela": "só os últimos 3 anos têm dado comparável",
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
