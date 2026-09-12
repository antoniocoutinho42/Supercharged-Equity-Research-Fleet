"""Cartesianos: uPlot vendorizado e adaptador (fatia 5B, item 5, Task 2).

Ver docs/superpowers/plans/2026-09-11-v4-item5b-graficos.md, seção "Task 2",
para a lista de cenários. `graficos.js` é a única coisa nova que roda no
browser -- suas partes DOM-dependentes (`renderizar` de fato desenhando um
`<canvas>`) não são exercidas aqui (exigiriam um DOM, que nem os harnesses
de paridade já existentes usam); o que É pura função (`FleetGraficos.
formatar`, `FleetGraficos.TIPOS_CARTESIANOS`) roda de verdade em `node`,
mesmo padrão de `tests/test_espelho_js.py`
(`vm.createContext`/`vm.runInContext`, script sem `module`/`require`/
`process`). O resto é Python puro: o HTML que `render.compor` produz.

Raízes/entregas vêm de `tests/relatorio_apoio.py` (`montar_entrega`, que
roda `avaliar()` de verdade sobre uma fixture de caso) -- nenhum
`resultados.json` é forjado à mão neste arquivo.
"""

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
SCRIPTS = RAIZ / "skills" / "er-relatorio" / "scripts"
ASSETS = RAIZ / "skills" / "er-relatorio" / "assets"
ASSETS_LEGADO = RAIZ / "skills" / "er-relatorio-html" / "assets"
GRAFICOS_JS = ASSETS / "graficos.js"

sys.path.insert(0, str(SCRIPTS))
import exhibits  # noqa: E402
import placeholders  # noqa: E402
import qc  # noqa: E402
import render  # noqa: E402

sys.path.insert(0, str(RAIZ / "tests"))
import relatorio_apoio as apoio  # noqa: E402

CATALOGO = json.loads(
    (RAIZ / "skills" / "er-valuation" / "assets" / "catalogo_apresentacao.json").read_text(encoding="utf-8"))
DICIONARIO = placeholders.carregar_dicionario("pt-BR")

FIXTURE = "caso_reversa_firm.json"

SEM_NODE = shutil.which("node") is None
RAZAO_SEM_NODE = "node ausente do PATH -- a suite de graficos.js roda sempre no CI (setup-node)"


def _dataset(x, campos):
    return {"ledger": [], "x": x, "campos": campos}


def _preparar_com_exhibits(exhibits_decl, dados=None, texto_conclusao=None):
    """Monta uma entrega válida com `exhibits_decl`, confirma zero HARD FAIL
    (fase 1 do QC) e resolve os exhibits UMA vez -- os mesmos cinco valores
    que `builder.py` de fato passa para `render.compor` depois dessa
    passada (ver o docstring de `compor`)."""
    kwargs = {"exhibits": exhibits_decl}
    if dados is not None:
        kwargs["dados"] = dados
    if texto_conclusao is not None:
        kwargs["texto_conclusao"] = texto_conclusao
    entrega_dict = apoio.montar_entrega(FIXTURE, **kwargs)

    fontes = {"resultados": entrega_dict["resultados"], "caso": entrega_dict["caso"]}
    _resolvido, log, _erros = placeholders.resolver(
        entrega_dict["analise"]["conclusao"]["texto"], fontes, "pt-BR", "analise.conclusao.texto")

    achados = qc.avaliar(entrega_dict, CATALOGO, html=None)
    assert not any(a.nivel == "HARD_FAIL" for a in achados), achados

    exhibits_resolvidos, log_exhibits = exhibits.resolver(entrega_dict)
    return entrega_dict, achados, log, exhibits_resolvidos, log_exhibits


DADOS_RECEITA = {"fin": _dataset(["2023", "2024", "2025"], {"receita": [111.25, 222.5, 333.75]})}
EXHIBIT_LINHA = {
    "id": "receita", "pergunta": "Como a receita evoluiu no período?", "tipo": "linha",
    "nota_janela": "janela curta de teste -- só 3 pontos",
    "series": [{"derivacao": "direta", "fonte": "fin.receita"}],
}
EXHIBIT_TABELA = {
    "id": "preco_base", "pergunta": "Qual o preço justo no cenário base?", "tipo": "tabela",
    "series": [{"derivacao": "engine", "chave": "resultados:manchete.preco_acao"}],
}


# --------------------------------------------------------------------------
# uPlot vendorizado -- byte a byte contra a cópia legada (Global Constraints
# da 5B; a cópia legada só sai no item 10).
# --------------------------------------------------------------------------

@pytest.mark.parametrize("nome", ["uPlot.iife.min.js", "uPlot.min.css", "uPlot.LICENSE"])
def test_uplot_vendorizado_e_byte_identico_ao_legado(nome):
    legado = hashlib.sha256((ASSETS_LEGADO / nome).read_bytes()).hexdigest()
    novo = hashlib.sha256((ASSETS / nome).read_bytes()).hexdigest()
    assert novo == legado, f"{nome} diverge da cópia legada"


# --------------------------------------------------------------------------
# HTML com exhibits: dois hosts, JSON com os números resolvidos, rótulos
# derivados do que a série já declara (nunca um campo novo).
# --------------------------------------------------------------------------

def test_html_com_dois_exhibits_contem_os_dois_hosts_e_o_json_resolvido():
    entrega_dict, achados, log, exhibits_resolvidos, log_exhibits = _preparar_com_exhibits(
        [EXHIBIT_LINHA, EXHIBIT_TABELA], dados=DADOS_RECEITA)

    pagina = render.compor(entrega_dict, CATALOGO, achados, log, "pt-BR", exhibits_resolvidos, log_exhibits)

    assert pagina.count('class="exhibit-grafico"') == 2
    assert 'data-exhibit-indice="0"' in pagina
    assert 'data-exhibit-indice="1"' in pagina
    assert 'id="fleet-dados-exhibits"' in pagina

    # números resolvidos do dataset 'fin' (série 'direta') crus no JSON:
    assert "111.25" in pagina
    assert "222.5" in pagina
    assert "333.75" in pagina
    # rótulo da série derivado do NOME DO CAMPO (fonte 'fin.receita' -> 'receita'):
    assert '"rotulo": "receita"' in pagina or '"rotulo":"receita"' in pagina

    # número resolvido da série 'engine' (escalar, tabela) cru no JSON:
    preco_base = entrega_dict["resultados"]["manchete"]["preco_acao"]
    assert json.dumps(preco_base) in pagina


def test_serie_direta_de_dois_datasets_leva_a_fonte_inteira_no_rotulo():
    """B1 (achado F3, segunda metade): dois datasets com um campo de MESMO
    NOME davam duas séries com o MESMO rótulo de legenda ('margem'), e o
    leitor não conseguia distinguir qual era qual. Quando o exhibit toca
    mais de um dataset, o rótulo é a `fonte` inteira."""
    dados = {
        "fin": _dataset(["2021", "2022", "2023", "2024"], {"margem": [0.20, 0.21, 0.22, 0.23]}),
        "setor": _dataset(["2021", "2022", "2023", "2024"], {"margem": [0.31, 0.32, 0.33, 0.34]}),
    }
    exhibit = {
        "id": "mix", "pergunta": "A margem acompanha o setor?", "tipo": "linha",
        "nota_janela": "janela curta de teste -- só 4 pontos",
        "series": [{"derivacao": "direta", "fonte": "fin.margem"},
                   {"derivacao": "direta", "fonte": "setor.margem"}],
    }
    entrega_dict, achados, log, resolvidos, log_exhibits = _preparar_com_exhibits(
        [exhibit], dados=dados)

    spec = render._exhibit_para_json(resolvidos[0], entrega_dict["dados"])

    assert [s["rotulo"] for s in spec["series"]] == ["fin.margem", "setor.margem"]

    # Com UM dataset só, o rótulo curto (nome do campo) continua valendo.
    _e, _a, _l, resolvidos_um, _le = _preparar_com_exhibits([EXHIBIT_LINHA], dados=DADOS_RECEITA)
    spec_um = render._exhibit_para_json(resolvidos_um[0], DADOS_RECEITA)
    assert [s["rotulo"] for s in spec_um["series"]] == ["receita"]


def test_pergunta_e_nota_de_janela_aparecem_na_secao_de_exhibits_da_tese():
    entrega_dict, achados, log, exhibits_resolvidos, log_exhibits = _preparar_com_exhibits(
        [EXHIBIT_LINHA], dados=DADOS_RECEITA)
    pagina = render.compor(entrega_dict, CATALOGO, achados, log, "pt-BR", exhibits_resolvidos, log_exhibits)

    assert render.t(DICIONARIO, "tese.exhibits_titulo") in pagina
    assert "Como a receita evoluiu no período?" in pagina
    assert "janela curta de teste" in pagina


def test_secao_de_exhibits_mostra_mensagem_vazia_sem_exhibit_declarado():
    entrega_dict, achados, log, exhibits_resolvidos, log_exhibits = _preparar_com_exhibits([])
    pagina = render.compor(entrega_dict, CATALOGO, achados, log, "pt-BR", exhibits_resolvidos, log_exhibits)

    assert render.t(DICIONARIO, "tese.exhibits_vazio") in pagina
    assert render.t(DICIONARIO, "evidencia.exhibits_vazio") in pagina
    assert 'class="exhibit-grafico"' not in pagina


# --------------------------------------------------------------------------
# G8 -- rastreabilidade dos exhibits na Evidência.
# --------------------------------------------------------------------------

def test_evidencia_mostra_rastreabilidade_dos_exhibits():
    entrega_dict, achados, log, exhibits_resolvidos, log_exhibits = _preparar_com_exhibits(
        [EXHIBIT_LINHA, EXHIBIT_TABELA], dados=DADOS_RECEITA)
    pagina = render.compor(entrega_dict, CATALOGO, achados, log, "pt-BR", exhibits_resolvidos, log_exhibits)

    assert render.t(DICIONARIO, "evidencia.exhibits_titulo") in pagina
    assert ">receita<" in pagina        # id do exhibit da série direta
    assert ">fin.receita<" in pagina    # detalhe: fonte exata
    assert ">preco_base<" in pagina     # id do exhibit da série engine
    assert ">resultados:manchete.preco_acao<" in pagina


# --------------------------------------------------------------------------
# Autocontenção -- com o uPlot de verdade embutido (não um HTML forjado).
# Também prova, indiretamente, que a correção de qc.py (falso positivo de
# 'data=' dentro do CORPO de um <script>, achado ao vendorizar o uPlot de
# verdade) está no lugar.
# --------------------------------------------------------------------------

def test_nenhum_recurso_externo_com_exhibits_e_uplot_embutido():
    entrega_dict, achados, log, exhibits_resolvidos, log_exhibits = _preparar_com_exhibits(
        [EXHIBIT_LINHA, EXHIBIT_TABELA], dados=DADOS_RECEITA)
    pagina = render.compor(entrega_dict, CATALOGO, achados, log, "pt-BR", exhibits_resolvidos, log_exhibits)

    achados_com_html = qc.avaliar(entrega_dict, CATALOGO, html=pagina)
    assert not any(a.codigo == "relatorio_nao_autocontido" for a in achados_com_html), achados_com_html


# --------------------------------------------------------------------------
# Determinismo.
# --------------------------------------------------------------------------

def test_saida_e_byte_identica_em_duas_composicoes_com_exhibits():
    entrega_dict, achados, log, exhibits_resolvidos, log_exhibits = _preparar_com_exhibits(
        [EXHIBIT_LINHA, EXHIBIT_TABELA], dados=DADOS_RECEITA)

    pagina1 = render.compor(entrega_dict, CATALOGO, achados, log, "pt-BR", exhibits_resolvidos, log_exhibits)
    pagina2 = render.compor(entrega_dict, CATALOGO, achados, log, "pt-BR", exhibits_resolvidos, log_exhibits)

    assert pagina1.encode("utf-8") == pagina2.encode("utf-8")


# --------------------------------------------------------------------------
# Detalhe 1 ("que um implementer apressado erra"): '$' do uPlot minificado
# entra como VALOR (`$js_uplot`), nunca colado no arquivo do template --
# provado aqui verificando que o JS/CSS aparecem VERBATIM (byte a byte) no
# HTML final, não uma versão corrompida pela substituição.
# --------------------------------------------------------------------------

def test_js_e_css_do_uplot_aparecem_verbatim_no_html():
    entrega_dict, achados, log, exhibits_resolvidos, log_exhibits = _preparar_com_exhibits(
        [EXHIBIT_LINHA], dados=DADOS_RECEITA)
    pagina = render.compor(entrega_dict, CATALOGO, achados, log, "pt-BR", exhibits_resolvidos, log_exhibits)

    assert (ASSETS / "uPlot.iife.min.js").read_text(encoding="utf-8") in pagina
    assert (ASSETS / "uPlot.min.css").read_text(encoding="utf-8") in pagina
    assert (ASSETS / "graficos.js").read_text(encoding="utf-8") in pagina


def test_uplot_nao_e_embutido_quando_a_entrega_nao_tem_exhibit():
    """G10 do desenho ('não há gráfico obrigatório'): uma entrega sem
    exhibit não paga o custo de ~50 KB de uma biblioteca que nunca seria
    usada -- e não arrisca um `{{`/`}}` incidental do código minificado
    colidir com uma checagem de placeholder cru (ver
    `tests/test_relatorio_contrato.py::test_placeholder_quebrado_por_quebra_de_linha_agora_resolve`,
    que varre a página inteira por `{{`/`}}` sobrando)."""
    entrega_dict, achados, log, exhibits_resolvidos, log_exhibits = _preparar_com_exhibits([])
    pagina = render.compor(entrega_dict, CATALOGO, achados, log, "pt-BR", exhibits_resolvidos, log_exhibits)

    assert (ASSETS / "uPlot.iife.min.js").read_text(encoding="utf-8") not in pagina
    assert (ASSETS / "graficos.js").read_text(encoding="utf-8") not in pagina
    assert "leeoniya/uPlot" not in pagina  # comentário de cabeçalho do uPlot minificado


# --------------------------------------------------------------------------
# Detalhe 2: JSON embutido em <script type="application/json"> escapa '</'
# como '<\/' -- senão um rótulo de série contendo '</script>' fecharia a
# tag prematuramente.
# --------------------------------------------------------------------------

def test_json_embutido_escapa_fechamento_de_script():
    dados = {"fin": _dataset(["2023", "2024"], {"receita": [1.0, 2.0], "ebitda": [0.5, 1.0]})}
    exhibit = {
        "id": "margem", "pergunta": "pergunta válida", "tipo": "linha",
        "nota_janela": "janela curta de teste",
        "series": [{"derivacao": "derivada", "fonte": "fin", "formula": "ebitda / receita",
                    "formula_nota": "nota</script><script>alert(1)</script>"}],
    }
    entrega_dict, achados, log, exhibits_resolvidos, log_exhibits = _preparar_com_exhibits([exhibit], dados=dados)
    pagina = render.compor(entrega_dict, CATALOGO, achados, log, "pt-BR", exhibits_resolvidos, log_exhibits)

    assert "nota</script><script>alert(1)</script>" not in pagina
    assert "nota<\\/script><script>alert(1)<\\/script>" in pagina


# --------------------------------------------------------------------------
# O dicionário tem toda chave nova (checagem direta; a varredura genérica
# de tests/test_relatorio_render.py já cobre isto via `t(dicionario, ...)`
# em render.py -- esta é só documentação executável do que a fatia acrescenta).
# --------------------------------------------------------------------------

@pytest.mark.parametrize("chave", [
    "tese.exhibits_titulo", "tese.exhibits_vazio",
    "evidencia.exhibits_titulo", "evidencia.exhibits_vazio",
    "evidencia.exhibits_colunas.exhibit", "evidencia.exhibits_colunas.indice",
    "evidencia.exhibits_colunas.origem", "evidencia.exhibits_colunas.detalhe",
    "graficos.indisponivel",
])
def test_dicionario_tem_as_novas_chaves_de_exhibits(chave):
    assert render.t(DICIONARIO, chave)


# --------------------------------------------------------------------------
# `graficos.js` em node (mesmo padrão de `tests/test_espelho_js.py`): só as
# funções PURAS (sem DOM) são exercidas aqui -- `FleetGraficos.formatar` e
# `FleetGraficos.TIPOS_CARTESIANOS`. `renderizar` desenha um `<canvas>` de
# verdade (uPlot) e não roda sem DOM; a prova de que o HTML/JSON que ele
# CONSOME está correto é feita pelos testes Python acima.
# --------------------------------------------------------------------------

def _chamar_node(expressao_js: str):
    script = (
        "const fs = require('fs');"
        "const vm = require('vm');"
        "const src = fs.readFileSync(%s, 'utf8');"
        "const ctx = vm.createContext({});"
        "vm.runInContext(src, ctx);"
        "const FleetGraficos = ctx.FleetGraficos;"
        "console.log(JSON.stringify(%s));"
    ) % (json.dumps(str(GRAFICOS_JS)), expressao_js)
    r = subprocess.run(["node", "-e", script], capture_output=True, text=True, encoding="utf-8", timeout=60)
    assert r.returncode == 0, r.stdout + r.stderr
    return json.loads(r.stdout)


@pytest.mark.skipif(SEM_NODE, reason=RAZAO_SEM_NODE)
def test_graficos_js_carrega_em_vm_sem_dom_module_require():
    """Mesmo espírito de
    `test_espelho_js.py::test_espelho_carrega_em_contexto_vm_sem_module_require_process`:
    o arquivo tem de AVALIAR sem estourar (`FleetGraficos` alcançável) num
    contexto vazio -- sem `document`, sem `module`, sem `require`."""
    resultado = _chamar_node(
        "!!(FleetGraficos && typeof FleetGraficos.renderizar === 'function' "
        "&& typeof FleetGraficos.formatar === 'function' "
        "&& Array.isArray(FleetGraficos.TIPOS_CARTESIANOS))"
    )
    assert resultado is True


@pytest.mark.skipif(SEM_NODE, reason=RAZAO_SEM_NODE)
def test_tipos_cartesianos_do_js_espelha_o_enum_do_python():
    tipos_js = _chamar_node("FleetGraficos.TIPOS_CARTESIANOS")
    assert set(tipos_js) == exhibits.TIPOS_CARTESIANOS


@pytest.mark.skipif(SEM_NODE, reason=RAZAO_SEM_NODE)
@pytest.mark.parametrize("valor", [6690.59, -1234.5, 0.0, 1234567.891, 5.0])
def test_formatar_js_bate_com_placeholders_formatar_pt_br(valor):
    """Prova de falseabilidade da Task 2 (plano): trocar a formatação de
    `graficos.js` para `en-US` (ou inverter os separadores) faz ESTE teste
    ficar vermelho -- `esperado` (Python, `placeholders.formatar`, a fonte
    de verdade pt-BR do relatório) deixaria de bater com `obtido` (node,
    `FleetGraficos.formatar`)."""
    esperado = placeholders.formatar(valor, "num2", "pt-BR")
    obtido = _chamar_node(f"FleetGraficos.formatar({valor!r}, 'numero', 'pt-BR')")
    assert obtido == esperado


@pytest.mark.skipif(SEM_NODE, reason=RAZAO_SEM_NODE)
def test_formatar_js_devolve_travessao_para_nao_finito():
    assert _chamar_node("FleetGraficos.formatar(null, 'numero', 'pt-BR')") == "—"
    assert _chamar_node("FleetGraficos.formatar(NaN, 'numero', 'pt-BR')") == "—"
    assert _chamar_node("FleetGraficos.formatar('texto', 'numero', 'pt-BR')") == "—"
