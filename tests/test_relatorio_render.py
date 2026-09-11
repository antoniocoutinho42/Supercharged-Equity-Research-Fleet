"""`render.compor` — as três abas (fatia 5A, item 5, Task 4).

Ver docs/superpowers/plans/2026-09-11-v4-item5a-contratos-builder.md, seção
"Task 4", para a lista de cenários. Raízes/entregas vêm de
`tests/relatorio_apoio.py` (roda `avaliar()` de verdade sobre uma fixture
de caso — nenhum `resultados.json` é forjado à mão aqui, exceto o achado
sintético do teste de QUALITY_WARNING, que o próprio plano autoriza
('pode ser testado passando um Achado sintético direto em render.compor').
"""

import html
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

CATALOGO = json.loads(
    (RAIZ / "skills" / "er-valuation" / "assets" / "catalogo_apresentacao.json").read_text(encoding="utf-8"))
DICIONARIO = placeholders.carregar_dicionario("pt-BR")


def _preparar(nome_fixture: str, **kwargs):
    """Monta uma entrega válida e devolve `(entrega, achados_fase1, log)` —
    os três argumentos que `builder.py` de fato passa para `render.compor`
    depois de uma primeira passada de QC limpa (html=None)."""
    entrega_dict = apoio.montar_entrega(nome_fixture, **kwargs)
    fontes = {"resultados": entrega_dict["resultados"], "caso": entrega_dict["caso"]}
    _resolvido, log, _erros = placeholders.resolver(
        entrega_dict["analise"]["conclusao"]["texto"], fontes, "pt-BR", "analise.conclusao.texto")
    achados = qc.avaliar(entrega_dict, CATALOGO, html=None)
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
    entrega_dict, achados, log = _preparar("caso_degrau.json")
    assert any(a.codigo == "divergencia_de_base_degrau" for a in achados)

    pagina = render.compor(entrega_dict, CATALOGO, achados, log, "pt-BR")

    assert "16.4%" in pagina  # {valor} do achado, format() puro (não é placeholders.formatar)
    assert render.t(DICIONARIO, "tese.disclosures_titulo") in pagina


# --------------------------------------------------------------------------
# Determinismo e autocontenção.
# --------------------------------------------------------------------------

def test_saida_e_byte_identica_em_duas_composicoes():
    entrega_dict, achados, log = _preparar("caso_reversa_firm.json")

    pagina1 = render.compor(entrega_dict, CATALOGO, achados, log, "pt-BR")
    pagina2 = render.compor(entrega_dict, CATALOGO, achados, log, "pt-BR")

    assert pagina1.encode("utf-8") == pagina2.encode("utf-8")


def test_nenhum_recurso_externo():
    """A mesma regra que `qc.py` mecaniza (`relatorio_nao_autocontido`) —
    aqui exercida contra o HTML de verdade, não um HTML forjado."""
    entrega_dict, achados, log = _preparar("caso_reversa_firm.json")
    pagina = render.compor(entrega_dict, CATALOGO, achados, log, "pt-BR")

    achados_com_html = qc.avaliar(entrega_dict, CATALOGO, html=pagina)
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
    assert "&lt;script&gt;alert(&#x27;oi&#x27;)&lt;/script&gt;" in pagina


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
    assert html.escape(mensagem_disclosure) in pagina
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
