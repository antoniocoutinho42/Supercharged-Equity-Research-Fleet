"""`render.compor` — as três abas (fatia 5A, item 5, Task 4).

Ver docs/superpowers/plans/2026-09-11-v4-item5a-contratos-builder.md, seção
"Task 4", para a lista de cenários. Raízes/entregas vêm de
`tests/relatorio_apoio.py` (roda `avaliar()` de verdade sobre uma fixture
de caso — nenhum `resultados.json` é forjado à mão aqui, exceto o achado
sintético do teste de QUALITY_WARNING, que o próprio plano autoriza
('pode ser testado passando um Achado sintético direto em render.compor').
"""

import copy
import json
import re
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
SCRIPTS = RAIZ / "skills" / "er-relatorio" / "scripts"

sys.path.insert(0, str(SCRIPTS))
import placeholders  # noqa: E402
import qc  # noqa: E402
import render  # noqa: E402

sys.path.insert(0, str(RAIZ / "tests"))
import relatorio_apoio as apoio  # noqa: E402
# Fatia 5E, Task 3: texto de dado sai pelo helper que tira da página a assinatura de uma referência, e o
# HTML cru deixa de ser o texto que o analista lê — as asserções sobre texto de dado leem a mesma árvore
# da aba Tese.
from test_relatorio_tese import _aba, _secao, _todos, _um, _visivel  # noqa: E402

CATALOGO = json.loads(
    (RAIZ / "skills" / "er-valuation" / "assets" / "catalogo_apresentacao.json").read_text(encoding="utf-8"))
DICIONARIO = placeholders.carregar_dicionario("pt-BR")


def _preparar(nome_fixture: str, **kwargs):
    """Monta uma entrega válida e devolve `(entrega, achados_fase1, log)` —
    os três argumentos que `builder.py` de fato passa para `render.compor`
    depois de uma primeira passada de QC limpa (html=None)."""
    entrega_dict = apoio.montar_entrega(nome_fixture, **kwargs)
    _prosa, log = placeholders.resolver_prosa(entrega_dict, "pt-BR")
    achados = qc.avaliar(entrega_dict, CATALOGO, apoio.CONTRATO_LEDGER, html=None)
    assert not any(a.nivel == "HARD_FAIL" for a in achados), achados
    return entrega_dict, achados, log


# --------------------------------------------------------------------------
# As três abas, com conteúdo real (preço formatado e múltiplo de tela).
# --------------------------------------------------------------------------

def test_html_contem_as_tres_abas_preco_e_multiplo_de_tela():
    entrega_dict, achados, log = _preparar("caso_reversa_firm.json")

    pagina = render.compor(entrega_dict, CATALOGO, achados, log, "pt-BR")

    for nome_aba in ("tese", "valuation", "evidencia"):
        assert f'data-aba-painel="{nome_aba}"' in pagina, nome_aba
        assert f'data-aba="{nome_aba}"' in pagina, nome_aba
    assert "R$ 61,91" in pagina  # manchete.preco_acao formatado
    assert "6,00x" in pagina  # mercado_tela.valor (6.0), formatado x2
    assert "6,69x" in pagina  # manchete.multiplo.valor (6.6906), formatado x2


def test_multiplo_justo_e_de_tela_pareados_por_base_com_rotulo_do_catalogo():
    """Cada lado do par usa o RÓTULO DA PRÓPRIA chave — o wrapper já garante
    que as duas bases coincidem (regra 4 do contrato `resultados/1`); o
    relatório só precisa ler cada rótulo, nunca decidir o pareamento."""
    entrega_dict, achados, log = _preparar("caso_reversa_firm.json")
    pagina = render.compor(entrega_dict, CATALOGO, achados, log, "pt-BR")

    assert CATALOGO["multiplos"]["EV/EBITDA_curr"]["rotulo"]["pt-BR"] in pagina
    assert CATALOGO["rotas"]["firm"]["rotulo"]["pt-BR"] in pagina
    tv = entrega_dict["caso"]["cenarios"]["base"]["premissas"]["tv"]
    assert CATALOGO["premissas"]["firm"]["tv"]["rotulos_opcoes"][tv]["pt-BR"] in pagina


def test_sotp_sem_multiplo_mostra_so_preco():
    """A5/Task4: manchete sem 'multiplo' (SOTP) -> nenhum código de múltiplo
    cru aparece, e a nota de SOTP (dicionário) aparece no lugar."""
    entrega_dict, achados, log = _preparar("caso_sotp_segmento.json")
    pagina = render.compor(entrega_dict, CATALOGO, achados, log, "pt-BR")

    assert "R$ 63,79" in pagina
    assert render.t(DICIONARIO, "valuation.sotp_sem_multiplo") in pagina
    for chave_multiplo in CATALOGO["multiplos"]:
        assert f">{chave_multiplo}<" not in pagina


def test_degrau_com_disclosure_visivel_na_tese():
    """B8/B13 (achados F7/S5): o número vem de `placeholders.formatar(...,
    'pp1', idioma)` -- vírgula decimal ('16,4%'), nunca ponto ('16.4%',
    o bug de antes desta correção: `round()` cru interpolado por
    `str.format`). O texto metodológico (`{texto}`) vem do catálogo
    (`catalogo.disclosures.divergencia_de_base_degrau.texto`, A4), não mais
    hardcoded no dicionário do relatório."""
    entrega_dict, achados, log = _preparar("caso_degrau.json")
    assert any(a.codigo == "divergencia_de_base_degrau" for a in achados)

    pagina = render.compor(entrega_dict, CATALOGO, achados, log, "pt-BR")

    assert "16,4%" in pagina
    assert "16.4%" not in pagina
    avisos = _visivel(_secao(_aba(pagina, "tese"), render.t(DICIONARIO, "tese.disclosures_titulo")))
    assert CATALOGO["disclosures"]["divergencia_de_base_degrau"]["texto"]["pt-BR"] in avisos


# --------------------------------------------------------------------------
# Determinismo e autocontenção.
# --------------------------------------------------------------------------

def test_saida_e_byte_identica_em_duas_composicoes():
    entrega_dict, achados, log = _preparar("caso_reversa_firm.json")

    pagina1 = render.compor(entrega_dict, CATALOGO, achados, log, "pt-BR")
    pagina2 = render.compor(entrega_dict, CATALOGO, achados, log, "pt-BR")

    assert pagina1.encode("utf-8") == pagina2.encode("utf-8")


# --------------------------------------------------------------------------
# B6 (achado F5, onda de correção da revisão final): "autocontido" é
# invariante por whitelist (`#fragmento`/URI `data:`), não lista negra de
# esquema -- cada uma destas formas passava direto (rc 0) com a lista negra
# antiga (só `http(s)://`/`//` em `src=`/`href=`/`url(`, e só com aspas).
# --------------------------------------------------------------------------

@pytest.mark.parametrize("html_texto", [
    '<link rel="stylesheet" href="https://cdn.example.com/x.css">',
    '<script src="uplot.iife.min.js"></script>',      # caminho relativo -- a fuga provada pela revisão
    '<script src=uplot.iife.min.js></script>',         # o mesmo, sem aspas
    '<img srcset="foo.png 1x, bar.png 2x">',
    '<object data="ficha.pdf"></object>',
    '<style>@import "tema.css";</style>',
    '<style>body { background: url(fundo.png); }</style>',
    '<a href="file:///C:/segredo.txt">x</a>',
    '<link href="//cdn.example.com/x.css">',
])
def test_referencia_nao_autocontida_e_hard_fail_em_qualquer_forma(html_texto):
    entrega_dict, _achados, _log = _preparar("caso_reversa_firm.json")
    achados_com_html = qc.avaliar(entrega_dict, CATALOGO, apoio.CONTRATO_LEDGER, html=html_texto)
    assert any(a.codigo == "relatorio_nao_autocontido" for a in achados_com_html), html_texto


@pytest.mark.parametrize("html_texto", [
    '<a href="#secao-2">pular</a>',
    '<img src="data:image/png;base64,aGVsbG8=">',
    '<style>@import url(data:text/css;base64,Zm9v);</style>',
    '<style>body { background: url(#gradiente-svg); }</style>',
])
def test_referencia_autocontida_nao_dispara(html_texto):
    entrega_dict, _achados, _log = _preparar("caso_reversa_firm.json")
    achados_com_html = qc.avaliar(entrega_dict, CATALOGO, apoio.CONTRATO_LEDGER, html=html_texto)
    assert not any(a.codigo == "relatorio_nao_autocontido" for a in achados_com_html), html_texto


def test_atribuicao_data_dentro_de_script_nao_dispara_falso_positivo():
    """Fatia 5B, item 5, Task 2: o uPlot vendorizado (minificado) contém a
    sintaxe de código legítima 'data=g.slice()' -- sem esta checagem,
    `_PADRAO_ATRIBUTO_REF` (desenhado para atributo HTML) casa a mesma
    forma dentro do CORPO de um <script>, e um relatório com uPlot embutido
    nunca conseguiria emitir. `src=`/`href=` como identificador de
    variável (não atributo) dentro do script também não pode disparar."""
    entrega_dict, _achados, _log = _preparar("caso_reversa_firm.json")
    html_com_script = (
        "<script>var data=1,src=2,href=3;function f(){data=src+href;}</script>"
    )
    achados_com_html = qc.avaliar(entrega_dict, CATALOGO, apoio.CONTRATO_LEDGER, html=html_com_script)
    assert not any(a.codigo == "relatorio_nao_autocontido" for a in achados_com_html), achados_com_html


# --------------------------------------------------------------------------
# A2 (achado F2): as oito sondas da revisão, agora como teste. Com a
# neutralização do miolo do <script> (e nada no lugar dela), TODAS as seis
# primeiras passavam com rc 0 -- uma referência VIVA num relatório que o
# analista reenvia por e-mail é vazamento de dado.
# --------------------------------------------------------------------------

@pytest.mark.parametrize("html_texto", [
    '<script>var b = new Image(); b.src = "https://cdn.exemplo.com/logo.png";</script>',
    '<script>fetch("https://telemetria.exemplo.com/ping");</script>',
    '<script>var r = new XMLHttpRequest(); r.open("GET", "https://x.exemplo.com");</script>',
    '<script>var s = new WebSocket("wss://x.exemplo.com");</script>',
    '<script>var w = new Worker("worker.js");</script>',
    '<script>importScripts("https://x.exemplo.com/w.js");</script>',
    '<script>var e = new EventSource("https://x.exemplo.com/stream");</script>',
    '<script>navigator.sendBeacon("https://x.exemplo.com/b", "d");</script>',
    '<script>var l = document.createElement("link"); l.href = "https://cdn.exemplo.com/x.css";</script>',
    '<script>img.srcset = "https://cdn.exemplo.com/x.png 2x";</script>',
])
def test_busca_de_recurso_no_miolo_de_script_e_hard_fail(html_texto):
    entrega_dict, _achados, _log = _preparar("caso_reversa_firm.json")
    achados_com_html = qc.avaliar(entrega_dict, CATALOGO, apoio.CONTRATO_LEDGER, html=html_texto)
    assert any(a.codigo == "relatorio_nao_autocontido" for a in achados_com_html), html_texto


@pytest.mark.parametrize("html_texto", [
    # Whitelist idêntica à da varredura de atributo: fragmento e URI data:.
    '<script>ancora.href = "#secao-2";</script>',
    '<script>img.src = "data:image/png;base64,aGVsbG8=";</script>',
    # Comparação não é atribuição; nome de variável não é chamada de rede.
    '<script>if (el.src === "x") { var fetchado = 1; }</script>',
    # O namespace XML que o próprio `svg.js` escreve em toda tag <svg>.
    '<script>var s = \'<svg xmlns="http://www.w3.org/2000/svg">\';</script>',
])
def test_miolo_de_script_sem_busca_de_recurso_nao_dispara(html_texto):
    entrega_dict, _achados, _log = _preparar("caso_reversa_firm.json")
    achados_com_html = qc.avaliar(entrega_dict, CATALOGO, apoio.CONTRATO_LEDGER, html=html_texto)
    assert not any(a.codigo == "relatorio_nao_autocontido" for a in achados_com_html), html_texto


def test_src_externo_na_propria_tag_script_ainda_dispara_mesmo_com_data_no_corpo():
    """Controle do teste acima: neutralizar o MIOLO do <script> não pode
    esconder um `src` de verdade na TAG -- só o conteúdo entre as tags é
    neutralizado, nunca a tag em si."""
    entrega_dict, _achados, _log = _preparar("caso_reversa_firm.json")
    html_com_script = '<script src="https://evil.example.com/x.js">var data=1;</script>'
    achados_com_html = qc.avaliar(entrega_dict, CATALOGO, apoio.CONTRATO_LEDGER, html=html_com_script)
    assert any(a.codigo == "relatorio_nao_autocontido" for a in achados_com_html), achados_com_html


def test_nenhum_recurso_externo():
    """A mesma regra que `qc.py` mecaniza (`relatorio_nao_autocontido`) —
    aqui exercida contra o HTML de verdade, não um HTML forjado."""
    entrega_dict, achados, log = _preparar("caso_reversa_firm.json")
    pagina = render.compor(entrega_dict, CATALOGO, achados, log, "pt-BR")

    achados_com_html = qc.avaliar(entrega_dict, CATALOGO, apoio.CONTRATO_LEDGER, html=pagina)
    assert not any(a.codigo == "relatorio_nao_autocontido" for a in achados_com_html), achados_com_html


# --------------------------------------------------------------------------
# Toda prosa é escapada — inclusive quando parece HTML.
# --------------------------------------------------------------------------

def test_prosa_com_tag_html_sai_escapada():
    texto = ("A companhia também aparece como <script>alert('oi')</script> em "
             "fóruns, mas o valor justo segue {{resultados:manchete.preco_acao|moeda}} por ação.")
    entrega_dict, achados, log = _preparar("caso_reversa_firm.json", texto_conclusao=texto)

    pagina = render.compor(entrega_dict, CATALOGO, achados, log, "pt-BR")

    assert "<script>alert('oi')</script>" not in pagina
    assert _visivel(_um(_aba(pagina, "tese"), classe="conclusao-texto")) == texto.replace(
        "{{resultados:manchete.preco_acao|moeda}}", "R$ 61,91")


# --------------------------------------------------------------------------
# REQUIRED_DISCLOSURE aparece; QUALITY_WARNING nunca (síntese direta em
# render.compor, como a calibragem do plano autoriza).
# --------------------------------------------------------------------------

def test_disclosure_aparece_e_quality_warning_nao():
    entrega_dict, achados, log = _preparar("caso_degrau.json")
    disclosure_real = next(a for a in achados if a.nivel == "REQUIRED_DISCLOSURE")
    aviso_sintetico = qc.Achado("QUALITY_WARNING", "codigo_inventado_sem_dicionario",
                                 "resultados.teste", {})

    pagina = render.compor(entrega_dict, CATALOGO, achados + [aviso_sintetico], log, "pt-BR")

    mensagem_disclosure = DICIONARIO["qc"][disclosure_real.codigo].format(
        onde=disclosure_real.onde, **disclosure_real.params)
    avisos = _todos(_secao(_aba(pagina, "tese"), render.t(DICIONARIO, "tese.disclosures_titulo")), tag="li")
    assert mensagem_disclosure in [_visivel(item) for item in avisos]
    assert "codigo_inventado_sem_dicionario" not in pagina


# --------------------------------------------------------------------------
# Nenhuma string de interface hardcoded (§16.1): toda chamada `t(dicionario,
# "...")` usa uma chave que existe em pt-BR.json; todo código de QC
# construído em qc.py tem mensagem em pt-BR.json.
# --------------------------------------------------------------------------

_PADRAO_CHAMADA_T = re.compile(r't\(\s*dicionario\s*,\s*["\']([\w.]+)["\']')
_PADRAO_ACHADO_QC = re.compile(r'Achado\(\s*"[A-Z_]+"\s*,\s*"([a-z_]+)"')


def _chave_existe(caminho: str) -> bool:
    atual = DICIONARIO.get("interface")
    for parte in caminho.split("."):
        if not isinstance(atual, dict) or parte not in atual:
            return False
        atual = atual[parte]
    return isinstance(atual, str)


def test_toda_chave_de_interface_usada_no_codigo_existe_no_dicionario():
    chaves_usadas: set[str] = set()
    for arquivo in SCRIPTS.glob("*.py"):
        chaves_usadas.update(_PADRAO_CHAMADA_T.findall(arquivo.read_text(encoding="utf-8")))

    assert chaves_usadas, "nenhuma chamada a t(dicionario, ...) encontrada — varredura vazia?"
    faltando = {chave for chave in chaves_usadas if not _chave_existe(chave)}
    assert not faltando, faltando


def test_todo_codigo_de_qc_construido_tem_mensagem_no_dicionario():
    codigos_usados: set[str] = set()
    for arquivo in SCRIPTS.glob("*.py"):
        codigos_usados.update(_PADRAO_ACHADO_QC.findall(arquivo.read_text(encoding="utf-8")))

    assert codigos_usados, "nenhum Achado(...) encontrado — varredura vazia?"
    faltando = codigos_usados - set(DICIONARIO.get("qc", {}))
    assert not faltando, faltando


def test_chave_de_interface_ausente_levanta_erro_nomeado():
    with pytest.raises(render.ChaveDeInterfaceAusente, match="interface.nao_existe"):
        render.t(DICIONARIO, "nao_existe")


def test_rotulo_do_catalogo_ausente_levanta_erro_nomeado():
    with pytest.raises(render.RotuloDoCatalogoAusente, match="rota_que_nao_existe"):
        render._rotulo_rota(CATALOGO, "rota_que_nao_existe", "pt-BR")


@pytest.mark.parametrize("remover", ["bloco", "rotulo_no_idioma"])
def test_rotulo_de_bloco_ausente_levanta_erro_nomeado(remover):
    """Fatia 5D, Task 3: o bloco econômico (vínculo e mecanismo da Tese, e os grupos do
    laboratório) é rotulado pelo catálogo com a mesma disciplina de rota e premissa — a
    ausência é recusa nomeada, nunca a chave crua na tela."""
    assert render._rotulo_bloco(CATALOGO, "custo_capital", "pt-BR") == (
        CATALOGO["blocos"]["custo_capital"]["rotulo"]["pt-BR"])
    catalogo = copy.deepcopy(CATALOGO)
    if remover == "bloco":
        del catalogo["blocos"]["custo_capital"]
    else:
        del catalogo["blocos"]["custo_capital"]["rotulo"]["pt-BR"]
    with pytest.raises(render.RotuloDoCatalogoAusente, match="custo_capital"):
        render._rotulo_bloco(catalogo, "custo_capital", "pt-BR")


def test_os_grupos_do_laboratorio_leem_o_rotulo_de_bloco_pelo_mesmo_auxiliar_da_tese(monkeypatch):
    """O painel da 5C lia o rótulo de bloco inline; passa a ler por `_rotulo_bloco`, o
    mesmo auxiliar do vínculo da Tese — duas leituras do mesmo rótulo divergiriam."""
    lidos = []
    original = render._rotulo_bloco

    def _registrar(catalogo, bloco, idioma):
        lidos.append(bloco)
        return original(catalogo, bloco, idioma)

    monkeypatch.setattr(render, "_rotulo_bloco", _registrar)
    blocos = render._blocos_do_catalogo(CATALOGO, "pt-BR")
    assert lidos and [chave for chave, _rotulo in blocos] == lidos


def test_rotulo_de_fronteira_de_escopo_ausente_levanta_erro_nomeado():
    """A classe de fronteira de escopo é rotulada pelo catálogo (D3), nunca pela chave."""
    assert render._rotulo_fronteira(CATALOGO, "pre_lucro", "pt-BR") == (
        CATALOGO["fronteiras_de_escopo"]["pre_lucro"]["rotulo"]["pt-BR"])
    with pytest.raises(render.RotuloDoCatalogoAusente, match="classe_que_nao_existe"):
        render._rotulo_fronteira(CATALOGO, "classe_que_nao_existe", "pt-BR")


# --------------------------------------------------------------------------
# Fatia 5E, Task 3: os avisos da Tese com a prosa resolvida, o rótulo do vocabulário do
# ledger e o valor de um registro formatado sem conta.
# --------------------------------------------------------------------------

ANCORA = apoio.CONTRATO_LEDGER["vocabularios"]["ancoras_do_consenso"][0]


def test_um_aviso_que_cita_um_campo_fora_da_lista_de_prosa_e_prosa_nao_auditada():
    """A Tese troca cada parâmetro de `campos_de_prosa` pelo texto que a lista de prosa resolveu.
    Um `onde` fora da lista é recusa nomeada — no builder, código 1 —, nunca o texto cru."""
    entrega_dict = apoio.montar_entrega("caso_minimo_firm.json", consenso={
        "ausente": {"ancora": ANCORA, "razao": "Nenhum provedor cobre a companhia."}})
    _prosa, log = placeholders.resolver_prosa(entrega_dict, "pt-BR")
    achados = qc.avaliar(entrega_dict, CATALOGO, apoio.CONTRATO_LEDGER, html=None)
    (aviso,) = [a for a in achados if a.codigo == "consenso_indisponivel"]
    render.compor(entrega_dict, CATALOGO, achados, log, "pt-BR")

    fora_da_lista = aviso._replace(params={
        **aviso.params, "campos_de_prosa": {"razao": "analise.consenso.ausente.razao_fora_da_lista"}})
    with pytest.raises(render.ProsaNaoAuditada, match="razao_fora_da_lista"):
        render.compor(entrega_dict, CATALOGO, [fora_da_lista if a is aviso else a for a in achados], log, "pt-BR")


def test_um_rotulo_de_vocabulario_do_ledger_ausente_do_dicionario_e_erro_nomeado(monkeypatch):
    """A classe de fonte, como todo vocabulário do contrato do ledger, sai pelo rótulo do
    dicionário. Sem o rótulo, a recusa nomeia a chave — nunca a classe crua na Evidência."""
    entrega_dict, achados, log = _preparar("caso_minimo_firm.json")
    classe = entrega_dict["ledger"]["registros"][0]["fonte"]["classe"]
    render.compor(entrega_dict, CATALOGO, achados, log, "pt-BR")

    sem_o_rotulo = copy.deepcopy(DICIONARIO)
    del sem_o_rotulo["interface"]["evidencia"]["classes_de_fonte"][classe]
    monkeypatch.setattr(placeholders, "carregar_dicionario", lambda _idioma: copy.deepcopy(sem_o_rotulo))
    with pytest.raises(render.ChaveDeInterfaceAusente,
                       match=re.escape(f"interface.evidencia.classes_de_fonte.{classe}")):
        render.compor(entrega_dict, CATALOGO, achados, log, "pt-BR")


def test_o_valor_de_um_registro_do_ledger_sai_formatado_pelo_idioma_e_sem_conta():
    """O valor de um registro — a linha do consenso na Tese, o ledger na Evidência — é o número
    que a fonte declara, só localizado: a receita do formato não escala, não prefixa e não
    sufixa. A unidade do registro é texto livre da fonte, e o relatório não a interpreta."""
    receita = placeholders.especificacao_de_formato(render.FORMATO_DO_VALOR_DO_LEDGER, "pt-BR")
    assert (receita["escala"], receita["prefixo"], receita["sufixo"]) == (1, "", "")
