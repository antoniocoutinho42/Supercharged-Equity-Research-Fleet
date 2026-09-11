"""Composição do HTML das três abas (fatia 5A, item 5, Task 4): Tese,
Valuation (cabeçalho estático — o laboratório interativo é a 5C) e
Evidência.

Este módulo NÃO importa nada de `er-valuation` nem do vendor (E3,
`docs/desenho-arquitetura-v4.md` §15): `compor` recebe `entrega` e
`catalogo` já carregados/validados por `builder.py` — dados, nunca código
nem metodologia. Nenhuma aritmética de valuation acontece aqui: todo número
exibido já vem pronto de `resultados`/`caso`, só formatado por
`placeholders.formatar` (mesma disciplina de `qc.py`/`builder.py`).

Duas regras cobrem TUDO que este módulo escreve:
- Todo texto DINÂMICO (vindo de `entrega`/`catalogo` — nomes, números já
  formatados, mensagens de QC) passa por `html.escape` antes de entrar no
  HTML. Nunca confie que uma prosa de analista ou um nome de cenário seja
  seguro por si só.
- Toda string de INTERFACE (rótulo de aba, título de seção, cabeçalho de
  coluna) vem de `assets/i18n/<idioma>.json` via `t()`, nunca hardcoded no
  código (§16.1) — uma chave ausente levanta `ChaveDeInterfaceAusente`,
  nomeando o caminho completo, nunca um texto substituto silencioso. Rótulo
  de rota/opção de premissa/múltiplo vem do catálogo de apresentação (A6)
  via `_rotulo_rota`/`_rotulo_opcao_premissa`/`_rotulo_multiplo`, mesma
  disciplina (`RotuloDoCatalogoAusente` nomeado).

`assets/template.html` é a casca estática (CSS e JS inline, sem nenhum
`src`/`href`/`url(` — a regra `relatorio_nao_autocontido` de `qc.py`
mecaniza isso). A composição usa `string.Template` (marcadores `$nome`),
não `str.format`: o CSS embutido usa `{ }` extensivamente, e `.format`
colidiria com toda regra de estilo. `string.Template.substitute` ignora
`{ }` por completo e nunca re-escaneia o valor já substituído em busca de
mais `$nome` — seguro mesmo quando um valor formatado contém `$` de verdade
(o símbolo "R$", por exemplo).
"""

import html
import json
import string
from pathlib import Path

import placeholders

_DIR_ASSETS: Path = Path(__file__).resolve().parent.parent / "assets"


class ChaveDeInterfaceAusente(Exception):
    """`assets/i18n/<idioma>.json` não tem a chave de interface pedida
    (§16.1: nenhuma string de interface hardcoded) — nunca um texto
    substituto silencioso."""


class RotuloDoCatalogoAusente(Exception):
    """O catálogo de apresentação (A6) não tem rótulo para a rota, opção de
    premissa ou múltiplo que esta entrega de fato usa — nunca um código cru
    ('firm', 'gordon') aparece no relatório em lugar do rótulo."""


def t(dicionario: dict, chave: str, **valores) -> str:
    """Busca `chave` (pontuada, ex. 'valuation.rota_titulo') em
    `dicionario["interface"]`; formata com `.format(**valores)` quando
    houver algum. Chave ausente ou não-texto -> `ChaveDeInterfaceAusente`,
    nomeando o caminho completo."""
    atual = dicionario.get("interface")
    percorrido: list[str] = []
    for parte in chave.split("."):
        percorrido.append(parte)
        if not isinstance(atual, dict) or parte not in atual:
            raise ChaveDeInterfaceAusente(
                f"chave de interface ausente: 'interface.{'.'.join(percorrido)}' "
                "não existe em assets/i18n/<idioma>.json."
            )
        atual = atual[parte]
    if not isinstance(atual, str):
        raise ChaveDeInterfaceAusente(f"chave de interface 'interface.{chave}' não é texto: {atual!r}.")
    return atual.format(**valores) if valores else atual


def _rotulo_rota(catalogo: dict, rota: str, idioma: str) -> str:
    info = catalogo.get("rotas", {}).get(rota)
    if info is None:
        raise RotuloDoCatalogoAusente(f"catálogo de apresentação sem a rota '{rota}' em 'rotas'.")
    rotulo = info.get("rotulo", {}).get(idioma)
    if not rotulo:
        raise RotuloDoCatalogoAusente(f"catálogo de apresentação sem rótulo em '{idioma}' para a rota '{rota}'.")
    return rotulo


def _rotulo_opcao_premissa(catalogo: dict, rota: str, premissa: str, opcao: str, idioma: str) -> str:
    info = catalogo.get("premissas", {}).get(rota, {}).get(premissa)
    if info is None:
        raise RotuloDoCatalogoAusente(
            f"catálogo de apresentação sem a premissa '{premissa}' na rota '{rota}'."
        )
    rotulo = info.get("rotulos_opcoes", {}).get(opcao, {}).get(idioma)
    if not rotulo:
        raise RotuloDoCatalogoAusente(
            f"catálogo de apresentação sem rótulo em '{idioma}' para a opção '{opcao}' "
            f"da premissa '{premissa}' (rota '{rota}')."
        )
    return rotulo


def _rotulo_multiplo(catalogo: dict, chave_multiplo: str, idioma: str) -> str:
    info = catalogo.get("multiplos", {}).get(chave_multiplo)
    if info is None:
        raise RotuloDoCatalogoAusente(f"catálogo de apresentação sem o múltiplo '{chave_multiplo}' em 'multiplos'.")
    rotulo = info.get("rotulo", {}).get(idioma)
    if not rotulo:
        raise RotuloDoCatalogoAusente(
            f"catálogo de apresentação sem rótulo em '{idioma}' para o múltiplo '{chave_multiplo}'."
        )
    return rotulo


def _mensagem_qc(achado, dicionario: dict) -> str:
    """Resolve `qc.<codigo>` do dicionário com `achado.params` — mesma
    receita de `builder._montar_qc_json` (módulo irmão, mesmo dicionário),
    duplicada aqui de propósito para `render.py` não precisar importar
    `builder.py`. Chave ausente -> erro nomeado, nunca mensagem inventada.
    """
    modelo = dicionario.get("qc", {}).get(achado.codigo)
    if modelo is None:
        raise ChaveDeInterfaceAusente(
            f"dicionário sem mensagem para 'qc.{achado.codigo}' (assets/i18n/) — "
            "achado não pode ser exibido no relatório."
        )
    return modelo.format(onde=achado.onde, **achado.params)


def _texto_valor(valor) -> str:
    """Texto de exibição de um valor de dado OPACO (entrada de `log` ou de
    `ficha_tecnica`) — nunca interpretado, só tornado legível. `None` vira
    texto vazio; escalar vira `str()`; dict/list vira JSON compacto
    determinístico (chaves ordenadas), para caber numa célula de tabela."""
    if valor is None:
        return ""
    if isinstance(valor, bool):
        return "true" if valor else "false"
    if isinstance(valor, (dict, list)):
        return json.dumps(valor, sort_keys=True, ensure_ascii=False, separators=(",", ": "))
    return str(valor)


# --------------------------------------------------------------------------
# Aba Tese: título (já resolvido por `compor`), conclusão resolvida, e todo
# achado REQUIRED_DISCLOSURE visível. HARD_FAIL nunca chega aqui (regra
# inviolável 2 barra antes); QUALITY_WARNING nunca é exibido (só `qc.json`).
# --------------------------------------------------------------------------

def _tese_html(entrega: dict, achados: list, idioma: str, dicionario: dict, titulo: str) -> str:
    caso = entrega["caso"]
    resultados = entrega["resultados"]
    fontes = {"resultados": resultados, "caso": caso}
    conclusao_resolvida, _log, _erros = placeholders.resolver(
        entrega["analise"]["conclusao"]["texto"], fontes, idioma, "analise.conclusao.texto")

    disclosures = [a for a in achados if a.nivel == "REQUIRED_DISCLOSURE"]
    titulo_disclosures = html.escape(t(dicionario, "tese.disclosures_titulo"))
    if disclosures:
        itens = "".join(f"<li>{html.escape(_mensagem_qc(a, dicionario))}</li>" for a in disclosures)
        bloco_disclosures = (
            f'<section class="disclosures">'
            f'<h2>{titulo_disclosures}</h2>'
            f'<ul>{itens}</ul>'
            f'</section>'
        )
    else:
        vazio = html.escape(t(dicionario, "tese.disclosures_vazio"))
        bloco_disclosures = (
            f'<section class="disclosures disclosures-vazio">'
            f'<h2>{titulo_disclosures}</h2>'
            f'<p>{vazio}</p>'
            f'</section>'
        )

    return (
        f'<h1>{titulo}</h1>'
        f'<section class="conclusao">'
        f'<h2>{html.escape(t(dicionario, "tese.conclusao_titulo"))}</h2>'
        f'<p>{html.escape(conclusao_resolvida)}</p>'
        f'</section>'
        f'{bloco_disclosures}'
    )


# --------------------------------------------------------------------------
# Aba Valuation (cabeçalho estático — o laboratório é a 5C): preço e upside
# da manchete; múltiplo justo ao lado do de tela (pareados por base — regra
# 4 do contrato `resultados/1` já garante que as bases coincidem, exceto no
# degrau, onde ambas são 'pvp'); rota e convenção terminal do cenário da
# manchete; preço por cenário quando houver mais de um. SOTP (sem
# `manchete.multiplo`): só preço e upside — nenhuma rota/convenção terminal
# única representaria fielmente partes que podem usar convenções distintas.
# --------------------------------------------------------------------------

def _valuation_html(caso: dict, resultados: dict, catalogo: dict, idioma: str, dicionario: dict) -> str:
    moeda = caso.get("moeda")
    manchete = resultados["manchete"]

    preco_fmt = html.escape(placeholders.formatar(manchete["preco_acao"], "moeda", idioma, moeda))
    upside_fmt = html.escape(placeholders.formatar(manchete["upside"], "pct1", idioma))
    cabecalho = (
        f'<div class="metrica">'
        f'<span class="metrica-rotulo">{html.escape(t(dicionario, "valuation.preco_justo_titulo"))}</span>'
        f'<span class="metrica-valor">{preco_fmt}</span>'
        f'</div>'
        f'<div class="metrica">'
        f'<span class="metrica-rotulo">{html.escape(t(dicionario, "valuation.upside_titulo"))}</span>'
        f'<span class="metrica-valor">{upside_fmt}</span>'
        f'</div>'
    )

    if "multiplo" in manchete:
        mj, mt = manchete["multiplo"], resultados["mercado_tela"]
        mj_fmt = html.escape(placeholders.formatar(mj["valor"], "x2", idioma))
        mt_fmt = html.escape(placeholders.formatar(mt["valor"], "x2", idioma))
        mj_rotulo = html.escape(_rotulo_multiplo(catalogo, mj["chave"], idioma))
        mt_rotulo = html.escape(_rotulo_multiplo(catalogo, mt["chave"], idioma))
        bloco_multiplos = (
            f'<div class="metrica">'
            f'<span class="metrica-rotulo">{html.escape(t(dicionario, "valuation.multiplo_justo_titulo"))}</span>'
            f'<span class="metrica-valor">{mj_fmt}</span>'
            f'<span class="metrica-nota">{mj_rotulo}</span>'
            f'</div>'
            f'<div class="metrica">'
            f'<span class="metrica-rotulo">{html.escape(t(dicionario, "valuation.multiplo_tela_titulo"))}</span>'
            f'<span class="metrica-valor">{mt_fmt}</span>'
            f'<span class="metrica-nota">{mt_rotulo}</span>'
            f'</div>'
        )

        rota = caso["rota"]
        tv = caso["cenarios"][manchete["cenario"]]["premissas"]["tv"]
        rota_rotulo = html.escape(_rotulo_rota(catalogo, rota, idioma))
        tv_rotulo = html.escape(_rotulo_opcao_premissa(catalogo, rota, "tv", tv, idioma))
        bloco_rota = (
            f'<div class="metrica">'
            f'<span class="metrica-rotulo">{html.escape(t(dicionario, "valuation.rota_titulo"))}</span>'
            f'<span class="metrica-valor">{rota_rotulo}</span>'
            f'</div>'
            f'<div class="metrica">'
            f'<span class="metrica-rotulo">{html.escape(t(dicionario, "valuation.convencao_terminal_titulo"))}</span>'
            f'<span class="metrica-valor">{tv_rotulo}</span>'
            f'</div>'
        )
    else:
        nota_sotp = html.escape(t(dicionario, "valuation.sotp_sem_multiplo"))
        bloco_multiplos = f'<p class="sotp-nota">{nota_sotp}</p>'
        bloco_rota = ""

    cenarios = resultados.get("cenarios") or {}
    if len(cenarios) > 1:
        linhas = "".join(
            f'<li><strong>{html.escape(str(nome))}</strong>: '
            f'{html.escape(placeholders.formatar(dados["valor"]["preco_acao"], "moeda", idioma, moeda))}</li>'
            for nome, dados in cenarios.items()
        )
        bloco_cenarios = (
            f'<section class="cenarios">'
            f'<h2>{html.escape(t(dicionario, "valuation.cenarios_titulo"))}</h2>'
            f'<ul>{linhas}</ul>'
            f'</section>'
        )
    else:
        bloco_cenarios = ""

    return (
        f'<section class="valuation-cabecalho">{cabecalho}</section>'
        f'<section class="valuation-multiplos">{bloco_multiplos}</section>'
        f'<section class="valuation-rota">{bloco_rota}</section>'
        f'{bloco_cenarios}'
    )


# --------------------------------------------------------------------------
# Aba Evidência: metodologia (`resultados.origem.metodologia`),
# `ficha_tecnica` (conteúdo opaco nesta fatia — só o tipo é contrato; a 5D
# detalha) e o log de resolução de placeholders da conclusão, em tabela.
# --------------------------------------------------------------------------

def _evidencia_html(resultados: dict, ficha_tecnica: dict, log: list, idioma: str, dicionario: dict) -> str:
    metodologia = resultados["origem"]["metodologia"]
    nome = html.escape(str(metodologia.get("nome", "")))
    versao = html.escape(str(metodologia.get("versao", "")))
    bloco_metodologia = (
        f'<section class="metodologia">'
        f'<h2>{html.escape(t(dicionario, "evidencia.metodologia_titulo"))}</h2>'
        f'<p>{t(dicionario, "evidencia.metodologia_valor", nome=nome, versao=versao)}</p>'
        f'</section>'
    )

    if ficha_tecnica:
        linhas_ficha = "".join(
            f'<tr><th>{html.escape(str(chave))}</th><td>{html.escape(_texto_valor(valor))}</td></tr>'
            for chave, valor in ficha_tecnica.items()
        )
        corpo_ficha = f'<table class="ficha-tecnica"><tbody>{linhas_ficha}</tbody></table>'
    else:
        corpo_ficha = f'<p>{html.escape(t(dicionario, "evidencia.ficha_tecnica_vazia"))}</p>'
    bloco_ficha = (
        f'<section class="ficha-tecnica-bloco">'
        f'<h2>{html.escape(t(dicionario, "evidencia.ficha_tecnica_titulo"))}</h2>'
        f'{corpo_ficha}'
        f'</section>'
    )

    if log:
        cabecalho_colunas = (
            f'<th>{html.escape(t(dicionario, "evidencia.log_colunas.onde"))}</th>'
            f'<th>{html.escape(t(dicionario, "evidencia.log_colunas.tipo"))}</th>'
            f'<th>{html.escape(t(dicionario, "evidencia.log_colunas.caminho"))}</th>'
            f'<th>{html.escape(t(dicionario, "evidencia.log_colunas.formato"))}</th>'
            f'<th>{html.escape(t(dicionario, "evidencia.log_colunas.bruto"))}</th>'
            f'<th>{html.escape(t(dicionario, "evidencia.log_colunas.resolvido"))}</th>'
        )
        linhas_log = "".join(
            "<tr>"
            f'<td>{html.escape(_texto_valor(entrada.get("onde")))}</td>'
            f'<td>{html.escape(_texto_valor(entrada.get("tipo")))}</td>'
            f'<td>{html.escape(_texto_valor(entrada.get("caminho")))}</td>'
            f'<td>{html.escape(_texto_valor(entrada.get("formato")))}</td>'
            f'<td>{html.escape(_texto_valor(entrada.get("bruto")))}</td>'
            f'<td>{html.escape(_texto_valor(entrada.get("resolvido")))}</td>'
            "</tr>"
            for entrada in log
        )
        corpo_log = (
            f'<table class="log-placeholders"><thead><tr>{cabecalho_colunas}</tr></thead>'
            f'<tbody>{linhas_log}</tbody></table>'
        )
    else:
        corpo_log = f'<p>{html.escape(t(dicionario, "evidencia.log_vazio"))}</p>'
    bloco_log = (
        f'<section class="log-bloco">'
        f'<h2>{html.escape(t(dicionario, "evidencia.log_titulo"))}</h2>'
        f'{corpo_log}'
        f'</section>'
    )

    return bloco_metodologia + bloco_ficha + bloco_log


def compor(entrega: dict, catalogo: dict, achados: list, log: list, idioma: str) -> str:
    """Compõe o HTML autocontido das três abas a partir só dos contratos já
    carregados/validados por quem chama (`builder.py`).

    `achados`: a lista de `qc.Achado` que `qc.avaliar` já produziu — a Tese
    mostra só os de nível REQUIRED_DISCLOSURE (HARD_FAIL nunca chega aqui,
    regra inviolável 2; QUALITY_WARNING nunca aparece no HTML). `log`: o
    log de resolução de placeholders da conclusão (mesmo formato que
    `placeholders.resolver` devolve), exibido em tabela na Evidência.

    Determinístico por construção: mesma entrada, mesmos bytes — nenhuma
    ordem de `set` não determinística, nenhum relógio, nenhum caminho
    absoluto no HTML emitido.
    """
    dicionario = placeholders.carregar_dicionario(idioma)

    execucao = entrega["execucao"]
    caso = entrega["caso"]
    resultados = entrega["resultados"]

    empresa = html.escape(str(caso.get("companhia", "")))
    ticker = html.escape(str(execucao.get("ticker", "")))
    titulo = t(dicionario, "titulo_pagina", empresa=empresa, ticker=ticker)

    corpo_tese = _tese_html(entrega, achados, idioma, dicionario, titulo)
    corpo_valuation = _valuation_html(caso, resultados, catalogo, idioma, dicionario)
    corpo_evidencia = _evidencia_html(resultados, entrega["ficha_tecnica"], log, idioma, dicionario)

    modelo = (_DIR_ASSETS / "template.html").read_text(encoding="utf-8")
    return string.Template(modelo).substitute(
        idioma=html.escape(str(idioma)),
        titulo=titulo,
        rotulo_aba_tese=html.escape(t(dicionario, "abas.tese")),
        rotulo_aba_valuation=html.escape(t(dicionario, "abas.valuation")),
        rotulo_aba_evidencia=html.escape(t(dicionario, "abas.evidencia")),
        corpo_tese=corpo_tese,
        corpo_valuation=corpo_valuation,
        corpo_evidencia=corpo_evidencia,
    )
