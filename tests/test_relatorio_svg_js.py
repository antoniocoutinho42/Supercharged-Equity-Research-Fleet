"""Módulo SVG: waterfall da ponte e matriz de sensibilidade (fatia 5B, item
5, Task 3).

Ver docs/superpowers/plans/2026-09-11-v4-item5b-graficos.md, seção "Task 3",
e `.superpowers/sdd/task-5b3-brief.md` (decisões S1–S6) para a lista de
cenários. Dois lados:

- `skills/er-relatorio/assets/svg.js` roda de VERDADE em `node`
  (`vm.createContext`/`vm.runInContext`, script sem `module`/`require`/
  `process`) -- mesmo padrão de `tests/test_relatorio_graficos.py` e
  `tests/test_espelho_js.py`. Como as duas funções são puras (string entra,
  string sai, nenhum DOM), aqui o módulo é exercido INTEIRO, não só a parte
  sem DOM: o SVG devolvido é reparseado com `ElementTree` -- o que também
  prova, de graça, que a string é XML bem formado e que todo texto saiu
  escapado.
- O lado Python é o HTML que `render.compor` produz: os hosts vazios dos
  painéis na aba Valuation e o payload `paineis_valuation` no MESMO
  `<script type="application/json">` dos exhibits.

Raízes/entregas vêm de `tests/relatorio_apoio.py` (`montar_entrega`, que
roda `avaliar()` de verdade sobre uma fixture de caso) -- nenhum
`resultados.json` é forjado à mão neste arquivo.
"""

import html
import json
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
SCRIPTS = RAIZ / "skills" / "er-relatorio" / "scripts"
ASSETS = RAIZ / "skills" / "er-relatorio" / "assets"
SVG_JS = ASSETS / "svg.js"

sys.path.insert(0, str(SCRIPTS))
import exhibits as exhibits_mod  # noqa: E402
import placeholders  # noqa: E402
import qc  # noqa: E402
import render  # noqa: E402

sys.path.insert(0, str(RAIZ / "tests"))
import relatorio_apoio as apoio  # noqa: E402

CATALOGO = json.loads(
    (RAIZ / "skills" / "er-valuation" / "assets" / "catalogo_apresentacao.json").read_text(encoding="utf-8"))
DICIONARIO = placeholders.carregar_dicionario("pt-BR")

# Ponte + uma grade 2D (roic x g), a única fixture com os dois painéis.
FIXTURE = "caso_reversa_firm.json"
# Ponte, nenhuma grade 2D -- discrimina "desenha o que existe" de "desenha
# sempre os dois".
FIXTURE_SO_PONTE = "caso_minimo_firm.json"
# Rota equity: sem ponte e sem grade 2D -- nenhum painel (S6).
FIXTURE_SEM_PAINEL = "caso_minimo_equity.json"

SEM_NODE = shutil.which("node") is None
RAZAO_SEM_NODE = "node ausente do PATH -- a suite de svg.js roda sempre no CI (setup-node)"

NS_SVG = "{http://www.w3.org/2000/svg}"

# A convenção econômica da ponte, restabelecida AQUI de forma INDEPENDENTE
# (dívida líquida = dívida bruta − caixa − outros ativos + outros passivos +
# minoritários). É o oráculo da prova de falseabilidade desta task: como
# `ponte.compor` deriva `nd_efetivo` E as parcelas da MESMA tabela `SINAIS`,
# inverter um sinal lá muda os dois juntos, e um teste que só comparasse o
# fechamento desenhado contra `resultados.ponte.nd_efetivo` continuaria
# verde. A expectativa independente é o que faz a mutação ficar vermelha.
SINAIS_ESPERADOS_DA_PONTE = {
    "divida_bruta": 1,
    "caixa_e_equivalentes": -1,
    "outros_ativos": -1,
    "outros_passivos": 1,
    "minoritarios": 1,
}


# --------------------------------------------------------------------------
# Harness de node -- carrega o FONTE de `svg.js` num contexto vazio (sem
# `document`, sem `module`, sem `require`) e devolve o que a expressão
# avaliar, serializado em JSON.
# --------------------------------------------------------------------------

def _chamar_node(expressao_js: str, **variaveis):
    declaracoes = "".join(
        "const %s = %s;" % (nome, json.dumps(valor, allow_nan=False))
        for nome, valor in sorted(variaveis.items())
    )
    script = (
        "const fs = require('fs');"
        "const vm = require('vm');"
        "const src = fs.readFileSync(%s, 'utf8');"
        "const ctx = vm.createContext({});"
        "vm.runInContext(src, ctx);"
        "const FleetSVG = ctx.FleetSVG;"
        "%s"
        "console.log(JSON.stringify(%s));"
    ) % (json.dumps(str(SVG_JS)), declaracoes, expressao_js)
    r = subprocess.run(["node", "-e", script], capture_output=True, text=True, encoding="utf-8", timeout=60)
    assert r.returncode == 0, r.stdout + r.stderr
    return json.loads(r.stdout)


def _retangulos(svg_texto: str) -> list:
    """Todo `<rect>` do SVG, já reparseado -- `fromstring` estoura se a
    string não for XML bem formado, então este helper é, de quebra, a
    checagem de boa formação."""
    return list(ET.fromstring(svg_texto).iter(NS_SVG + "rect"))


def _textos(svg_texto: str, classe: str) -> list:
    """O TEXTO que o analista de fato lê, por classe, em ordem de documento.

    A1 (onda de correção da revisão final, achado F1): até esta onda, todos
    os 27 testes deste arquivo liam ATRIBUTO (`data-valor`, `data-base`,
    `data-linha`) e contavam `<rect>` -- nenhum lia o `<text>`. Quatro
    mutações que trocam o número na tela (sinal fixo em 1, tudo x100, matriz
    transposta, total recalculado) sobreviviam à superfície inteira do
    relatório. Todo teste desta seção compara o `<text>` contra um oráculo
    montado do `caso`/da `grade`, nunca contra o próprio desenho."""
    return [e.text for e in ET.fromstring(svg_texto).iter(NS_SVG + "text")
            if e.get("class") == classe]


def _ponte_da_fixture(nome_fixture: str = FIXTURE) -> tuple[dict, dict]:
    entrega_dict = apoio.montar_entrega(nome_fixture)
    return entrega_dict["caso"], entrega_dict["resultados"]["ponte"]


def _waterfall_da_ponte(ponte: dict) -> str:
    """Chama `FleetSVG.waterfall` com a ponte REAL de `resultados` -- os
    rótulos crus, porque este módulo recebe o rótulo pronto de quem chama e
    não olha para ele (S3)."""
    return _chamar_node(
        "FleetSVG.waterfall(parcelas, opcoes)",
        parcelas=ponte["parcelas"],
        opcoes={"total": {"rotulo": "total", "valor": ponte["nd_efetivo"]}},
    )


def _grade_2d_da_fixture() -> tuple[dict, dict]:
    """A grade 2D real da fixture e o par (x, y) do cenário QUE ELA
    PERTURBOU (S4) -- `caso["sensibilidades"]["cenario"]`, nunca outro."""
    entrega_dict = apoio.montar_entrega(FIXTURE)
    caso = entrega_dict["caso"]
    grade = entrega_dict["resultados"]["sensibilidades"]["grades_2d"][0]
    premissas = caso["cenarios"][caso["sensibilidades"]["cenario"]]["premissas"]
    base = {"x": premissas[grade["premissa_x"]], "y": premissas[grade["premissa_y"]]}
    return grade, base


# --------------------------------------------------------------------------
# O módulo carrega sozinho -- sem DOM, sem uPlot, sem `FleetGraficos` (S5).
# --------------------------------------------------------------------------

@pytest.mark.skipif(SEM_NODE, reason=RAZAO_SEM_NODE)
def test_svg_js_carrega_em_vm_sem_dom_module_require():
    assert _chamar_node(
        "!!(FleetSVG && typeof FleetSVG.waterfall === 'function' "
        "&& typeof FleetSVG.matriz === 'function')"
    ) is True


@pytest.mark.skipif(SEM_NODE, reason=RAZAO_SEM_NODE)
@pytest.mark.parametrize("valor", [6690.59, -1234.5, 0.0, 1234567.891, 5.0])
def test_formatar_do_svg_bate_com_placeholders_formatar_pt_br(valor):
    """A tabela de separadores pt-BR de `svg.js` é uma DUPLICAÇÃO deliberada
    de `placeholders._SEPARADORES` (ver o cabeçalho do módulo). Duplicação
    deliberada só é honesta quando mecanizada: este teste amarra as duas à
    mesma fonte de verdade, do mesmo jeito que
    `test_relatorio_graficos.py::test_formatar_js_bate_com_placeholders_formatar_pt_br`
    já amarra a de `graficos.js`."""
    assert _chamar_node(f"FleetSVG.formatar({valor!r})") == placeholders.formatar(valor, "num2", "pt-BR")


@pytest.mark.skipif(SEM_NODE, reason=RAZAO_SEM_NODE)
@pytest.mark.parametrize("formato", ["num0", "num2", "num4", "pct1", "pp0", "pp2", "x2", "moeda"])
@pytest.mark.parametrize("valor", [61.906, -1234.56, 0.164, 0.0])
def test_receita_de_formato_aplicada_no_js_bate_com_placeholders_formatar(formato, valor):
    """A4 (achado F7): a UNIDADE vira uma receita de formatação
    (`placeholders.especificacao_de_formato`) que viaja no payload, e o
    `svg.js` a aplica. Duplicação só é honesta quando mecanizada: aplicar a
    receita em JS tem de produzir, caractere a caractere, o que
    `placeholders.formatar` produz em Python -- inclusive a escala de 'pct'
    (fração x 100), o sufixo '%'/'x' e o símbolo da moeda.

    Nenhum valor aqui cai EXATAMENTE no meio da casa arredondada: Python
    (`format`, meio-para-o-par: '-1234.5' -> '-1234') e JS (`toFixed`,
    meio-para-cima: '-1235') divergem nesse ponto único. É uma divergência
    ANTERIOR a esta onda, comum aos dois módulos JS (`graficos.js` tem a
    mesma tabela), registrada e deliberadamente não tocada aqui -- a onda é
    de cobertura, e mudar o arredondamento mudaria número desenhado."""
    espec = placeholders.especificacao_de_formato(formato, "pt-BR", "BRL-nominal")
    assert _chamar_node("FleetSVG.formatar(valor, espec, 'pt-BR')", valor=valor, espec=espec) == \
        placeholders.formatar(valor, formato, "pt-BR", "BRL-nominal")


# --------------------------------------------------------------------------
# Waterfall da ponte REAL da fixture.
# --------------------------------------------------------------------------

@pytest.mark.skipif(SEM_NODE, reason=RAZAO_SEM_NODE)
def test_waterfall_tem_uma_barra_por_parcela_mais_a_de_fechamento():
    _caso, ponte = _ponte_da_fixture()
    barras = [r for r in _retangulos(_waterfall_da_ponte(ponte)) if r.get("data-indice") is not None]

    assert len(barras) == len(ponte["parcelas"]) + 1
    assert [b.get("data-fechamento") for b in barras] == [None] * len(ponte["parcelas"]) + ["1"]


@pytest.mark.skipif(SEM_NODE, reason=RAZAO_SEM_NODE)
def test_waterfall_fecha_na_divida_liquida_das_linhas_declaradas():
    """O teste do FECHAMENTO (alvo da prova de falseabilidade desta task).

    Três afirmações encadeadas: a barra de fechamento desenha o total que o
    wrapper já somou (o SVG nunca recalcula, regra inviolável 1); o
    empilhamento geométrico das parcelas desenhadas chega nesse mesmo ponto;
    e esse ponto é a dívida líquida que as linhas de balanço DECLARADAS no
    caso implicam pela convenção econômica (`SINAIS_ESPERADOS_DA_PONTE`).
    Inverter um sinal em `ponte.SINAIS` deixa as duas primeiras verdes e a
    terceira vermelha."""
    caso, ponte = _ponte_da_fixture()
    barras = [r for r in _retangulos(_waterfall_da_ponte(ponte)) if r.get("data-indice") is not None]
    fechamento = [b for b in barras if b.get("data-fechamento") == "1"]

    assert len(fechamento) == 1
    desenhado = float(fechamento[0].get("data-valor"))

    assert desenhado == pytest.approx(ponte["nd_efetivo"])
    empilhado = sum(float(b.get("data-valor")) for b in barras if b.get("data-fechamento") != "1")
    assert empilhado == pytest.approx(desenhado)

    esperado = sum(caso["ponte"][linha] * sinal for linha, sinal in SINAIS_ESPERADOS_DA_PONTE.items())
    assert desenhado == pytest.approx(esperado)


@pytest.mark.skipif(SEM_NODE, reason=RAZAO_SEM_NODE)
def test_textos_das_barras_do_waterfall_sao_o_valor_com_o_sinal_de_cada_linha():
    """A1 (achado F1): o NÚMERO IMPRESSO em cada barra, comparado contra o
    oráculo independente (`caso["ponte"]` x `SINAIS_ESPERADOS_DA_PONTE`) e
    formatado por `placeholders.formatar` -- não contra `data-valor`, que é o
    mesmo número por outro caminho.

    Discrimina duas mutações que sobreviviam à suíte inteira: `_ponte_para_
    json` publicando `sinal: 1` sempre (o caixa sobe +300 em vez de descer
    -300: uma ponte que visivelmente não fecha, emitida com rc 0) e `svg.js`
    imprimindo tudo x100."""
    caso, ponte = _ponte_da_fixture()
    svg = _waterfall_da_ponte(ponte)

    esperado = [
        placeholders.formatar(caso["ponte"][linha] * sinal, "num2", "pt-BR")
        for linha, sinal in ((p["rotulo"], SINAIS_ESPERADOS_DA_PONTE[p["rotulo"]])
                             for p in ponte["parcelas"])
    ]
    esperado.append(placeholders.formatar(
        sum(caso["ponte"][linha] * sinal for linha, sinal in SINAIS_ESPERADOS_DA_PONTE.items()),
        "num2", "pt-BR"))

    assert _textos(svg, "fleet-svg-valor") == esperado


@pytest.mark.skipif(SEM_NODE, reason=RAZAO_SEM_NODE)
def test_barra_de_fechamento_desenha_o_total_do_motor_nunca_a_soma_das_parcelas():
    """Regra inviolável 1: o total é o `nd_efetivo` que o wrapper somou; o
    relatório não conserta número do motor. Um total DIVERGENTE das parcelas
    (perturbado aqui de propósito) tem de aparecer divergente na figura --
    é justamente o que a mutação "relatório recalcula o total" apagava, e
    nenhuma asserção pegava, porque no caminho feliz os dois coincidem."""
    _caso, ponte = _ponte_da_fixture()
    divergente = ponte["nd_efetivo"] + 111.0

    svg = _chamar_node(
        "FleetSVG.waterfall(parcelas, opcoes)",
        parcelas=ponte["parcelas"],
        opcoes={"total": {"rotulo": "total", "valor": divergente}},
    )

    assert _textos(svg, "fleet-svg-valor")[-1] == placeholders.formatar(divergente, "num2", "pt-BR")
    fechamento = [r for r in _retangulos(svg) if r.get("data-fechamento") == "1"]
    assert float(fechamento[0].get("data-valor")) == pytest.approx(divergente)


def test_payload_da_ponte_repassa_o_total_do_motor_sem_recalcular():
    """O mesmo invariante do lado Python: `_ponte_para_json` LÊ
    `resultados.ponte.nd_efetivo` -- nunca soma as parcelas. Com um
    `nd_efetivo` perturbado (as parcelas intactas), o payload tem de
    carregar o valor perturbado."""
    entrega_dict = apoio.montar_entrega(FIXTURE)
    resultados = json.loads(json.dumps(entrega_dict["resultados"]))
    resultados["ponte"]["nd_efetivo"] = resultados["ponte"]["nd_efetivo"] + 111.0

    payload = render._paineis_valuation_para_json(
        entrega_dict["caso"], resultados, CATALOGO, "pt-BR", DICIONARIO)

    assert payload["ponte"]["total"]["valor"] == pytest.approx(
        entrega_dict["resultados"]["ponte"]["nd_efetivo"] + 111.0)


@pytest.mark.skipif(SEM_NODE, reason=RAZAO_SEM_NODE)
def test_cada_barra_carrega_a_contribuicao_com_o_sinal_da_linha():
    caso, ponte = _ponte_da_fixture()
    barras = [r for r in _retangulos(_waterfall_da_ponte(ponte)) if r.get("data-fechamento") is None]

    for barra, parcela in zip(barras, ponte["parcelas"]):
        esperado = caso["ponte"][parcela["rotulo"]] * SINAIS_ESPERADOS_DA_PONTE[parcela["rotulo"]]
        assert float(barra.get("data-valor")) == pytest.approx(esperado), parcela["rotulo"]


# --------------------------------------------------------------------------
# Matriz da grade 2D REAL da fixture.
# --------------------------------------------------------------------------

@pytest.mark.skipif(SEM_NODE, reason=RAZAO_SEM_NODE)
def test_matriz_tem_uma_celula_por_par_de_pontos():
    grade, base = _grade_2d_da_fixture()
    svg = _chamar_node("FleetSVG.matriz(grade, opcoes)", grade=grade,
                       opcoes={"base": base, "rotuloX": "x", "rotuloY": "y"})
    celulas = [r for r in _retangulos(svg) if r.get("data-linha") is not None]

    assert len(celulas) == len(grade["pontos_x"]) * len(grade["pontos_y"])
    assert {(c.get("data-linha"), c.get("data-coluna")) for c in celulas} == {
        (str(i), str(j)) for i in range(len(grade["pontos_y"])) for j in range(len(grade["pontos_x"]))
    }


@pytest.mark.skipif(SEM_NODE, reason=RAZAO_SEM_NODE)
def test_matriz_marca_a_celula_do_cenario_que_a_grade_perturbou():
    """S4: a célula-base é `celulas[1][1]` -- roic 12 (pontos_x[1]) e g 5
    (pontos_y[1]), as premissas centrais do cenário 'base' da fixture, que é
    o cenário que `caso["sensibilidades"]["cenario"]` nomeia."""
    grade, base = _grade_2d_da_fixture()
    svg = _chamar_node("FleetSVG.matriz(grade, opcoes)", grade=grade,
                       opcoes={"base": base, "rotuloX": "x", "rotuloY": "y"})
    marcadas = [r for r in _retangulos(svg) if r.get("data-base") == "1"]

    assert len(marcadas) == 1
    assert (marcadas[0].get("data-linha"), marcadas[0].get("data-coluna")) == ("1", "1")
    assert grade["celulas"][1][1]["x"] == base["x"]
    assert grade["celulas"][1][1]["y"] == base["y"]


@pytest.mark.skipif(SEM_NODE, reason=RAZAO_SEM_NODE)
def test_textos_das_celulas_da_matriz_sao_os_valores_da_grade_na_posicao_certa():
    """A1 (achado F1): o número IMPRESSO na célula-base e o da célula de
    CANTO (última linha, última coluna), contra `grade["celulas"][i][j]
    ["valor"]`. A base sozinha não bastaria: transpor a grade deixa
    `celulas[1][1]` no lugar (é a diagonal) e move todo o resto -- a célula
    de canto é o que discrimina transposição. E qualquer escala errada
    (x100) reprova nas duas."""
    grade, base = _grade_2d_da_fixture()
    svg = _chamar_node("FleetSVG.matriz(grade, opcoes)", grade=grade,
                       opcoes={"base": base, "rotuloX": "x", "rotuloY": "y"})
    textos = _textos(svg, "fleet-svg-celula-valor")

    linhas, colunas = len(grade["pontos_y"]), len(grade["pontos_x"])
    assert len(textos) == linhas * colunas
    for i, j in ((1, 1), (linhas - 1, colunas - 1), (0, colunas - 1)):
        esperado = placeholders.formatar(grade["celulas"][i][j]["valor"], "num2", "pt-BR")
        assert textos[i * colunas + j] == esperado, (i, j)


@pytest.mark.skipif(SEM_NODE, reason=RAZAO_SEM_NODE)
@pytest.mark.parametrize("base", [None, {"x": 11.0, "y": 5.0}, {"x": 12.0, "y": 4.0}])
def test_matriz_sem_par_casando_nao_marca_nenhuma_celula(base):
    """"Nunca aproxima, nunca marca a do meio" (S4): base ausente, ou um dos
    dois eixos fora dos pontos da grade, marca ZERO células."""
    grade, _base_real = _grade_2d_da_fixture()
    svg = _chamar_node("FleetSVG.matriz(grade, opcoes)", grade=grade,
                       opcoes={"base": base, "rotuloX": "x", "rotuloY": "y"})

    assert [r for r in _retangulos(svg) if r.get("data-base") == "1"] == []


# --------------------------------------------------------------------------
# Escape e determinismo (S5).
# --------------------------------------------------------------------------

@pytest.mark.skipif(SEM_NODE, reason=RAZAO_SEM_NODE)
def test_rotulo_com_marcacao_sai_escapado():
    svg = _chamar_node(
        "FleetSVG.waterfall(parcelas, opcoes)",
        parcelas=[{"rotulo": '<script>alert("x")</script> & cia', "valor": 10.0, "sinal": 1}],
        opcoes={"total": {"rotulo": "<b>total</b>", "valor": 10.0}},
    )

    assert "<script>" not in svg
    assert "<b>" not in svg
    assert "&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt; &amp; cia" in svg
    textos = [e.text for e in ET.fromstring(svg).iter(NS_SVG + "text")]
    assert '<script>alert("x")</script> & cia' in textos


@pytest.mark.skipif(SEM_NODE, reason=RAZAO_SEM_NODE)
def test_mesma_entrada_devolve_a_mesma_string():
    _caso, ponte = _ponte_da_fixture()
    grade, base = _grade_2d_da_fixture()
    duas_vezes = _chamar_node(
        "[FleetSVG.waterfall(parcelas, op1), FleetSVG.waterfall(parcelas, op1), "
        "FleetSVG.matriz(grade, op2), FleetSVG.matriz(grade, op2)]",
        parcelas=ponte["parcelas"], grade=grade,
        op1={"total": {"rotulo": "total", "valor": ponte["nd_efetivo"]}},
        op2={"base": base, "rotuloX": "x", "rotuloY": "y"},
    )

    assert duas_vezes[0] == duas_vezes[1]
    assert duas_vezes[2] == duas_vezes[3]


# --------------------------------------------------------------------------
# Lado Python: os hosts dos painéis na aba Valuation e o payload embutido.
# --------------------------------------------------------------------------

def _preparar(nome_fixture: str):
    return _preparar_mutado(nome_fixture, None)


def _preparar_mutado(nome_fixture: str, mutar_caso):
    entrega_dict = apoio.montar_entrega(nome_fixture, mutar_caso=mutar_caso)
    fontes = {"resultados": entrega_dict["resultados"], "caso": entrega_dict["caso"]}
    _resolvido, log, _erros = placeholders.resolver(
        entrega_dict["analise"]["conclusao"]["texto"], fontes, "pt-BR", "analise.conclusao.texto")
    achados = qc.avaliar(entrega_dict, CATALOGO, html=None)
    assert not any(a.nivel == "HARD_FAIL" for a in achados), achados
    return entrega_dict, achados, log


def _compor(nome_fixture: str) -> str:
    entrega_dict, achados, log = _preparar(nome_fixture)
    return render.compor(entrega_dict, CATALOGO, achados, log, "pt-BR")


# Os hosts, pela marcação EXATA que `render._paineis_valuation_html` emite --
# não por `data-painel=` solto: o bootstrap estático de `template.html` cita
# esses mesmos seletores no código, e uma checagem por substring solta ficaria
# verde mesmo sem nenhum host de verdade na aba.
HOST_PONTE = '<div class="painel-grafico" data-painel="ponte"></div>'
HOST_MATRIZ = '<div class="painel-grafico" data-painel="matriz" data-painel-indice="0"></div>'


def test_aba_valuation_traz_os_dois_paineis_e_embute_o_svg_js():
    pagina = _compor(FIXTURE)

    assert HOST_PONTE in pagina
    assert HOST_MATRIZ in pagina
    assert render.t(DICIONARIO, "valuation.ponte_titulo") in pagina
    assert SVG_JS.read_text(encoding="utf-8") in pagina


def test_rotulos_das_parcelas_vem_do_catalogo_nunca_do_codigo_da_ponte():
    """S2/E3: o payload embutido carrega o rótulo TRADUZIDO de cada linha da
    ponte (catálogo de apresentação), nunca o código cru ('divida_bruta')."""
    pagina = _compor(FIXTURE)

    for linha, info in CATALOGO["ponte"].items():
        assert info["rotulo"]["pt-BR"] in pagina, linha
        assert f'"rotulo": "{linha}"' not in pagina, linha


def test_base_embutida_e_a_premissa_central_do_cenario_da_grade():
    entrega_dict, achados, log = _preparar(FIXTURE)
    pagina = render.compor(entrega_dict, CATALOGO, achados, log, "pt-BR")
    caso = entrega_dict["caso"]
    premissas = caso["cenarios"][caso["sensibilidades"]["cenario"]]["premissas"]
    grade = entrega_dict["resultados"]["sensibilidades"]["grades_2d"][0]

    payload = json.loads(
        pagina.split('id="fleet-dados-exhibits">')[1].split("</script>")[0].replace("<\\/", "</"))
    matriz = payload["paineis_valuation"]["matrizes"][0]

    assert matriz["base"] == {"x": premissas[grade["premissa_x"]], "y": premissas[grade["premissa_y"]]}
    assert matriz["rotuloX"] == CATALOGO["premissas"][caso["rota"]][grade["premissa_x"]]["rotulo"]["pt-BR"]
    assert matriz["rotuloY"] == CATALOGO["premissas"][caso["rota"]][grade["premissa_y"]]["rotulo"]["pt-BR"]
    assert payload["paineis_valuation"]["ponte"]["total"]["valor"] == pytest.approx(
        entrega_dict["resultados"]["ponte"]["nd_efetivo"])


def _com_cenario_da_grade_divergente(caso: dict) -> None:
    """Um caso LEGÍTIMO pelo gate em que a grade perturba um cenário que
    NÃO é o da manchete: dois cenários, `cenario_base = "base"` e
    `sensibilidades.cenario = "bull"`. É a configuração do achado F4."""
    bull = json.loads(json.dumps(caso["cenarios"]["base"]))
    bull["premissas"]["g"] = 7.0
    caso["cenarios"]["bull"] = bull
    caso["cenario_base"] = "base"
    caso["sensibilidades"]["cenario"] = "bull"


def test_titulo_da_matriz_nomeia_o_cenario_que_a_grade_perturbou():
    """A3 (achado F4): a aba mostrava "R$ 61,91" (a manchete, do
    `cenario_base`) no topo e, abaixo, uma matriz cuja célula contornada em
    vermelho lia 69,54 -- sem nomear cenário nenhum. A marcação estava
    certa (S4: a grade perturbou 'bull'); faltava a página dizer isso.
    O título passa a nomear o cenário DA GRADE, nunca o da manchete."""
    entrega_dict, achados, log = _preparar_mutado(FIXTURE, _com_cenario_da_grade_divergente)
    caso = entrega_dict["caso"]
    grade = entrega_dict["resultados"]["sensibilidades"]["grades_2d"][0]
    rota = entrega_dict["resultados"]["rota"]

    pagina = render.compor(entrega_dict, CATALOGO, achados, log, "pt-BR")

    esperado = render.t(
        DICIONARIO, "valuation.matriz_titulo",
        cenario=caso["sensibilidades"]["cenario"],
        x=CATALOGO["premissas"][rota][grade["premissa_x"]]["rotulo"]["pt-BR"],
        y=CATALOGO["premissas"][rota][grade["premissa_y"]]["rotulo"]["pt-BR"],
    )
    titulo = next(t for t in re.findall(r"<h2>([^<]*)</h2>", pagina) if "Sensibilidade" in t)
    assert titulo == html.escape(esperado)
    assert html.escape(caso["sensibilidades"]["cenario"]) in titulo
    assert caso["cenario_base"] not in titulo


def test_grade_2d_sem_cenario_declarado_e_recusa_nomeada():
    """A3, o outro lado: um `caso` com grade 2D sempre declara o cenário que
    ela perturba (o gate exige). Se não declarar, o painel recusa PELO NOME
    -- nunca um título sem cenário, nunca um `KeyError` cru."""
    entrega_dict = apoio.montar_entrega(FIXTURE)
    del entrega_dict["caso"]["sensibilidades"]["cenario"]

    with pytest.raises(render.CampoDeContratoAusente, match="caso.sensibilidades.cenario"):
        render.compor(entrega_dict, CATALOGO, [], [], "pt-BR")


def test_fixture_com_ponte_e_sem_grade_traz_so_o_painel_da_ponte():
    pagina = _compor(FIXTURE_SO_PONTE)

    assert HOST_PONTE in pagina
    assert HOST_MATRIZ not in pagina
    assert render.t(DICIONARIO, "valuation.ponte_titulo") in pagina


def test_fixture_sem_ponte_nem_grade_nao_traz_painel_nem_embute_o_svg_js():
    """S6: sem ponte (rota equity) e sem grade 2D o painel simplesmente não
    aparece -- nada de seção vazia com texto de erro -- e o módulo nem entra
    na página (mesma economia de bytes do uPlot na Task 2)."""
    pagina = _compor(FIXTURE_SEM_PAINEL)

    assert HOST_PONTE not in pagina
    assert HOST_MATRIZ not in pagina
    assert 'class="painel-grafico"' not in pagina
    assert render.t(DICIONARIO, "valuation.ponte_titulo") not in pagina
    assert SVG_JS.read_text(encoding="utf-8") not in pagina


def test_nenhum_recurso_externo_com_os_paineis_e_o_svg_embutido():
    entrega_dict, achados, log = _preparar(FIXTURE)
    pagina = render.compor(entrega_dict, CATALOGO, achados, log, "pt-BR")

    achados_com_html = qc.avaliar(entrega_dict, CATALOGO, html=pagina)
    assert not any(a.codigo == "relatorio_nao_autocontido" for a in achados_com_html), achados_com_html


def test_saida_e_byte_identica_em_duas_composicoes_com_paineis():
    entrega_dict, achados, log = _preparar(FIXTURE)

    pagina1 = render.compor(entrega_dict, CATALOGO, achados, log, "pt-BR")
    pagina2 = render.compor(entrega_dict, CATALOGO, achados, log, "pt-BR")

    assert pagina1.encode("utf-8") == pagina2.encode("utf-8")


# --------------------------------------------------------------------------
# O caminho INTEIRO Python -> JS (A1, terceira asserção do achado F1): o
# payload é composto por `render._paineis_valuation_para_json` -- o mesmo
# objeto que o browser recebe -- e o SVG é desenhado A PARTIR DELE, com as
# mesmas opções que o bootstrap de `template.html` monta. Os testes acima
# alimentam o `svg.js` direto do `resultados`, então nada verificava o que
# `render.py` de fato publica.
# --------------------------------------------------------------------------

def _payload_dos_paineis(nome_fixture: str = FIXTURE) -> tuple[dict, dict]:
    entrega_dict = apoio.montar_entrega(nome_fixture)
    payload = render._paineis_valuation_para_json(
        entrega_dict["caso"], entrega_dict["resultados"], CATALOGO, "pt-BR", DICIONARIO)
    return entrega_dict, payload


@pytest.mark.skipif(SEM_NODE, reason=RAZAO_SEM_NODE)
def test_waterfall_desenhado_a_partir_do_payload_de_render_imprime_a_ponte_em_moeda():
    """A1 + A4: o waterfall que o browser recebe, do payload real. Os textos
    são a ponte do caso (oráculo independente, com os sinais da convenção
    econômica) formatada na MOEDA do caso -- a mesma que a manchete usa
    logo acima na página. Antes da A4 o payload descartava a unidade e a
    figura imprimia "800,00" ao lado de uma manchete "R$ 61,91"."""
    entrega_dict, payload = _payload_dos_paineis()
    caso = entrega_dict["caso"]

    svg = _chamar_node(
        "FleetSVG.waterfall(ponte.parcelas, {total: ponte.total, formato: ponte.formato})",
        ponte=payload["ponte"])

    esperado = [
        placeholders.formatar(caso["ponte"][p["rotulo"]] * SINAIS_ESPERADOS_DA_PONTE[p["rotulo"]],
                              "moeda", "pt-BR", caso["moeda"])
        for p in entrega_dict["resultados"]["ponte"]["parcelas"]
    ]
    esperado.append(placeholders.formatar(
        sum(caso["ponte"][linha] * sinal for linha, sinal in SINAIS_ESPERADOS_DA_PONTE.items()),
        "moeda", "pt-BR", caso["moeda"]))

    assert _textos(svg, "fleet-svg-valor") == esperado
    assert _textos(svg, "fleet-svg-rotulo") == [
        CATALOGO["ponte"][p["rotulo"]]["rotulo"]["pt-BR"]
        for p in entrega_dict["resultados"]["ponte"]["parcelas"]
    ] + [render.t(DICIONARIO, "valuation.ponte_total")]


@pytest.mark.skipif(SEM_NODE, reason=RAZAO_SEM_NODE)
def test_matriz_desenhada_a_partir_do_payload_de_render_usa_a_unidade_de_cada_eixo():
    """A1 + A4: a matriz que o browser recebe, do payload real.

    Célula: `grade.unidade` é "preço por ação" e o catálogo mapeia essa
    unidade para o formato de moeda -- a célula-base tem de ler exatamente o
    que a manchete lê ("R$ 61,91"), não "61,91". Eixos: a `unidade` da
    premissa no catálogo é 'pp', então um ROIC de 12 p.p. sai "12,00%", não
    "12,00". Este é o teste que amarra UNIDADE CONHECIDA -> FORMATO
    APLICADO (achado F7)."""
    entrega_dict, payload = _payload_dos_paineis()
    grade = entrega_dict["resultados"]["sensibilidades"]["grades_2d"][0]
    matriz = payload["matrizes"][0]
    moeda = entrega_dict["caso"]["moeda"]

    svg = _chamar_node(
        "FleetSVG.matriz(m.grade, {base: m.base, rotuloX: m.rotuloX, rotuloY: m.rotuloY, "
        "formato: m.formato, formatoX: m.formatoX, formatoY: m.formatoY})",
        m=matriz)

    colunas = len(grade["pontos_x"])
    celulas = _textos(svg, "fleet-svg-celula-valor")
    for i, j in ((1, 1), (len(grade["pontos_y"]) - 1, colunas - 1)):
        assert celulas[i * colunas + j] == placeholders.formatar(
            grade["celulas"][i][j]["valor"], "moeda", "pt-BR", moeda), (i, j)

    assert celulas[1 * colunas + 1] == placeholders.formatar(
        entrega_dict["resultados"]["manchete"]["preco_acao"], "moeda", "pt-BR", moeda)
    assert _textos(svg, "fleet-svg-eixo-x") == [
        placeholders.formatar(x, "pp2", "pt-BR") for x in grade["pontos_x"]]
    assert _textos(svg, "fleet-svg-eixo-y") == [
        placeholders.formatar(y, "pp2", "pt-BR") for y in grade["pontos_y"]]


def test_bootstrap_do_template_consome_toda_chave_do_payload_dos_paineis():
    """Anti-deriva de F7 na direção oposta: `render.py` publicar um campo
    novo que o bootstrap ignora é exatamente como a `unidade` do motor ficou
    sem consumidor. Toda chave que o payload dos painéis carrega tem de
    aparecer no bootstrap de `template.html`."""
    _entrega, payload = _payload_dos_paineis()
    bootstrap = (ASSETS / "template.html").read_text(encoding="utf-8")

    chaves = set(payload["ponte"]) | set(payload["matrizes"][0])
    faltando = {chave for chave in chaves if chave not in bootstrap}
    assert not faltando, faltando


def test_unidade_de_grade_fora_do_catalogo_e_hard_fail_nomeado():
    """A4/F7, o outro lado do tripwire: um v10 que troque a métrica da grade
    (células viram múltiplo, `unidade` passa a outra coisa) reprova PELO
    NOME, antes de renderizar -- em vez de desenhar 6,69 onde desenhava
    61,91 com rc 0 e QC limpo."""
    entrega_dict = apoio.montar_entrega(FIXTURE)
    entrega_dict["resultados"]["sensibilidades"]["grades_2d"][0]["unidade"] = "múltiplo EV/EBITDA"

    achados = qc.avaliar(entrega_dict, CATALOGO, html=None)

    achado = next(a for a in achados if a.codigo == "unidade_desconhecida")
    assert achado.nivel == "HARD_FAIL"
    assert achado.onde == "resultados.sensibilidades.grades_2d.0.unidade"
    assert achado.params["unidade"] == "múltiplo EV/EBITDA"


def test_toda_unidade_do_catalogo_tem_formato_que_o_relatorio_conhece():
    """O vocabulário de `catalogo.unidades` é da integração; os códigos de
    formato são do relatório. Uma unidade nova apontando para um formato que
    `placeholders` não conhece reprova aqui, não na tela."""
    unidades = CATALOGO["unidades"]
    assert unidades, "catálogo sem 'unidades' — vocabulário vazio?"
    for unidade, info in unidades.items():
        assert placeholders.especificacao_de_formato(info["formato"], "pt-BR", "BRL"), unidade


def test_prosa_da_pagina_com_paineis_nao_tem_placeholder_cru():
    """B6 (achado F10): a Task 3 duplicou a armadilha -- este teste varria a
    PÁGINA INTEIRA atrás de `{{`/`}}`, e uma página com exhibit tem 50 `}}`
    vindos do uPlot minificado. O invariante é sobre a prosa que o relatório
    escreveu; o escopo certo é a página com `<script>`/`<style>`
    neutralizados (`apoio.prosa_da_pagina`), não uma lista de exclusão por
    arquivo que envelhece a cada asset novo.

    O `indent=2` de `render._json_embutido` continua valendo por outro
    motivo (JSON legível e determinístico dentro da página), mas nenhuma
    asserção depende mais dele para não tropeçar no bundle."""
    prosa = apoio.prosa_da_pagina(_compor(FIXTURE))

    assert "{{" not in prosa
    assert "}}" not in prosa


def test_varredura_de_prosa_ignora_o_bundle_mas_pega_o_corpo():
    """Controle da correção acima, nos dois sentidos: a página COM exhibit
    (uPlot embutido, dezenas de `}}` no bundle) passa; um placeholder cru na
    PROSA continua sendo visto."""
    dados = {"fin": {"ledger": [], "x": [1, 2, 3], "campos": {"receita": [1.0, 2.0, 3.0]}}}
    exhibit = {"id": "fin", "pergunta": "pergunta válida", "tipo": "linha",
               "nota_janela": "janela curta de propósito",
               "series": [{"derivacao": "direta", "fonte": "fin.receita"}]}
    entrega_dict = apoio.montar_entrega(FIXTURE, dados=dados, exhibits=[exhibit])
    resolvidos, log_exhibits = exhibits_mod.resolver(entrega_dict)
    achados = qc.avaliar(entrega_dict, CATALOGO, html=None)
    assert not any(a.nivel == "HARD_FAIL" for a in achados), achados

    pagina = render.compor(entrega_dict, CATALOGO, achados, [], "pt-BR", resolvidos, log_exhibits)

    assert pagina.count("}}") > 10, "fixture sem bundle embutido — controle vacuamente verde?"
    assert "}}" not in apoio.prosa_da_pagina(pagina)

    with_cru = apoio.prosa_da_pagina(pagina.replace("<h1>", "<h1>{{resultados:x|num2}} "))
    assert "{{" in with_cru and "}}" in with_cru


@pytest.mark.parametrize("chave", [
    "valuation.ponte_titulo", "valuation.ponte_total", "valuation.matriz_titulo",
])
def test_dicionario_tem_as_novas_chaves_dos_paineis(chave):
    assert render.t(DICIONARIO, chave)
