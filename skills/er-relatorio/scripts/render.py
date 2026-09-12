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
  de rota/convenção terminal/múltiplo vem do catálogo de apresentação (A6)
  via `_rotulo_rota`/`_rotulo_convencao_terminal`/`_rotulo_multiplo`, mesma
  disciplina (`RotuloDoCatalogoAusente` nomeado). B2 (onda de correção da
  revisão final, achado F2): a convenção terminal é lida do CÓDIGO CANÔNICO
  que a integração já publica (`resultados.manchete.convencao_terminal`),
  nunca de `caso[...]["premissas"]["tv"]` cru.

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
from typing import Any

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


def _rotulo_convencao_terminal(catalogo: dict, codigo: str, idioma: str) -> str:
    """B2 (achado F2): rótulo da convenção terminal CANÔNICA da manchete
    (`resultados.manchete.convencao_terminal`, publicada pela integração --
    A1/`avaliar._montar_manchete`), lido de `catalogo.convencoes_terminais`
    -- a fonte única (Task 2/A1). Antes desta correção o relatório lia
    `caso[...]["premissas"]["tv"]` CRU e rotulava pelo LITERAL declarado no
    caso: um alias legado ('spread', 'ic') passava pelo gate e pelo wrapper
    (que só exige a presença de 'tv', nunca um valor específico) e só
    quebrava aqui, tarde demais (`RotuloDoCatalogoAusente`, sem rótulo para
    'spread'/'ic'). Agora o relatório nunca lê nada de `caso` para montar
    este rótulo -- só o código já canônico que a integração publicou."""
    rotulo = catalogo.get("convencoes_terminais", {}).get(codigo, {}).get(idioma)
    if not rotulo:
        raise RotuloDoCatalogoAusente(
            f"catálogo de apresentação sem rótulo em '{idioma}' para a convenção "
            f"terminal '{codigo}' em 'convencoes_terminais'."
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


def _json_embutido(dados: Any) -> str:
    """JSON para dentro de `<script type="application/json">` (fatia 5B,
    item 5, Task 2 -- primeira vez que este relatório embute JSON; a regra
    ficou registrada, sem implementação, na revisão da 5A): `</` escapado
    como `<\\/` -- sem isto, um valor de texto que contivesse `</script>`
    fecharia a tag prematuramente, corrompendo o HTML em volta. `allow_nan
    =False` (defesa em profundidade): nada no contrato de `dados`/`resultados`
    impede um `NaN`/`Infinity` cru de chegar a uma série `direta` (só o
    RESULTADO de uma fórmula `derivada` é garantido finito, por
    `exhibits.avaliar_formula`) -- um `NaN` doria virar o token `NaN` (JSON
    do Python aceita; `JSON.parse` do browser não) e quebraria o `JSON.parse`
    do bootstrap silenciosamente tarde demais. Recusar aqui, com uma
    exceção nomeada, é preferível a servir um JSON que o browser não
    consegue parsear."""
    bruto = json.dumps(dados, ensure_ascii=False, allow_nan=False)
    return bruto.replace("</", "<\\/")


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
# Exhibits (fatia 5B, item 5, Task 2): a seção de gráficos/tabelas da Tese
# (G7) e a rastreabilidade correspondente na Evidência (G8). Consomem
# `exhibits_resolvidos`/`log_exhibits` que `builder.py` já produziu chamando
# `exhibits.resolver(entrega)` UMA vez (ver o docstring de `compor` abaixo) —
# este módulo nunca chama `exhibits.resolver` de novo, e nunca importa
# `exhibits.py`: só lê as chaves que a série/overlay JÁ RESOLVIDA carrega
# (`derivacao`, `fonte`/`formula_nota`/`chave`, `valores`/`valor`), o mesmo
# jeito que `render.py` já trata `caso`/`resultados` como dado opaco (E3).
#
# O adaptador do browser (`graficos.js`) não lê nada disso: recebe só
# números e rótulos já prontos (`_exhibit_para_json`) — nunca uma `fonte`,
# `formula` ou `chave` crua. Rótulo de série/overlay é derivado do que a
# própria série JÁ DECLARA (G3 não tem campo 'rótulo' de série): o nome do
# campo para `direta`, a `formula_nota` para `derivada` (é exatamente o
# propósito desse campo), a `chave` para `engine`; overlay usa `rotulo`
# quando o analista declarou, senão a própria `chave`. Isso é rotulagem de
# apresentação, nunca conta de valuation (E3).
# --------------------------------------------------------------------------

def _dataset_da_serie(serie: dict, dados: dict) -> dict | None:
    """Dataset (`entrega.dados.<id>`) que a série referencia, quando ela é
    `direta`/`derivada` (`fonte` aponta pra lá — `<dataset>.<campo>` ou só
    `<dataset>`, ver `exhibits.py`); `None` para `engine` (não usa dataset).
    Nunca falha: a série já passou pelo QC (regra inviolável 2) antes de
    `compor` ser chamado, então a referência sempre resolve de verdade."""
    derivacao = serie.get("derivacao")
    if derivacao == "direta":
        dataset_id = serie["fonte"].partition(".")[0]
    elif derivacao == "derivada":
        dataset_id = serie["fonte"]
    else:
        return None
    return dados.get(dataset_id)


def _eixo_x_do_exhibit(exhibit_resolvido: dict, dados: dict) -> list | None:
    """Eixo x comum do exhibit: o `x` do PRIMEIRO dataset que alguma série
    `direta`/`derivada` referencia (todas as séries de um mesmo exhibit
    normalmente compartilham um dataset — G3/G3-corrigido existem
    exatamente para permitir isso). Um exhibit só com séries `engine` (que
    não têm dataset) devolve `None` — `graficos.js` cai para índice
    posicional nesse caso (ver o cabeçalho de `graficos.js`)."""
    for serie in exhibit_resolvido["series"]:
        dataset = _dataset_da_serie(serie, dados)
        if isinstance(dataset, dict) and isinstance(dataset.get("x"), list):
            return dataset["x"]
    return None


def _rotulo_serie(serie: dict) -> str:
    derivacao = serie["derivacao"]
    if derivacao == "direta":
        return serie["fonte"].partition(".")[2]
    if derivacao == "derivada":
        return serie["formula_nota"]
    return serie["chave"]  # engine


def _rotulo_overlay(overlay: dict) -> str:
    rotulo = overlay.get("rotulo")
    return rotulo if rotulo else overlay["chave"]


def _valores_lista(valores: Any) -> list:
    """Normaliza um valor já resolvido para lista -- uma série `engine`
    pode resolver um ÚNICO número (ex.: o preço de um cenário, ver
    `test_serie_engine_le_caminho_real_de_resultados`); o adaptador do
    browser nunca precisa distinguir escalar de lista de um elemento."""
    return valores if isinstance(valores, list) else [valores]


def _exhibit_para_json(exhibit_resolvido: dict, dados: dict) -> dict:
    """Spec resolvida que `graficos.js` de fato recebe (contrato descrito no
    cabeçalho de `graficos.js`) -- só números e rótulos, nenhuma fonte/
    fórmula/chave crua."""
    return {
        "id": exhibit_resolvido["id"],
        "tipo": exhibit_resolvido["tipo"],
        "eixoX": _eixo_x_do_exhibit(exhibit_resolvido, dados),
        "series": [
            {"rotulo": _rotulo_serie(serie), "valores": _valores_lista(serie["valores"])}
            for serie in exhibit_resolvido["series"]
        ],
        "overlays": [
            {"rotulo": _rotulo_overlay(overlay), "valor": overlay["valor"]}
            for overlay in exhibit_resolvido.get("overlays", [])
        ],
    }


def _formatacao_grafico(dicionario: dict) -> dict:
    """Único pedaço de PROSA traduzida que `graficos.js` recebe (o texto de
    fallback quando um exhibit não pôde ser desenhado) -- nunca separador
    numérico: o adaptador tem sua PRÓPRIA tabela pt-BR (`SEPARADORES_POR_
    IDIOMA`, duplicada de propósito de `placeholders._SEPARADORES`, ver o
    cabeçalho de `graficos.js`), porque só prosa de interface precisa vir
    do dicionário (§16.1) -- separador de milhar/decimal é convenção de
    formatação, não texto de interface traduzível."""
    return {"graficoIndisponivel": t(dicionario, "graficos.indisponivel")}


def _exhibits_html(exhibits_resolvidos: list, dicionario: dict) -> str:
    """Seção de exhibits na Tese (G7): um `<article>` por exhibit, na ordem
    declarada, com a pergunta como título (prosa do analista, escapada — a
    mesma disciplina do resto deste módulo) e um host VAZIO que só
    `graficos.js` preenche (bootstrap estático em `template.html`). G5: a
    5D reposiciona isto sob as perguntas da tese; nesta fatia, seção
    própria."""
    titulo = html.escape(t(dicionario, "tese.exhibits_titulo"))
    if not exhibits_resolvidos:
        vazio = html.escape(t(dicionario, "tese.exhibits_vazio"))
        return f'<section class="exhibits exhibits-vazio"><h2>{titulo}</h2><p>{vazio}</p></section>'

    blocos = []
    for indice, exhibit in enumerate(exhibits_resolvidos):
        pergunta = html.escape(exhibit["pergunta"])
        bloco_nota = ""
        if exhibit.get("nota_janela"):
            bloco_nota = f'<p class="exhibit-nota-janela">{html.escape(exhibit["nota_janela"])}</p>'
        bloco_caption = ""
        if exhibit.get("caption"):
            bloco_caption = f'<p class="exhibit-caption">{html.escape(exhibit["caption"])}</p>'
        blocos.append(
            f'<article class="exhibit" data-exhibit-indice="{indice}">'
            f'<h3>{pergunta}</h3>'
            f'{bloco_nota}'
            f'<div class="exhibit-grafico" data-exhibit-indice="{indice}"></div>'
            f'{bloco_caption}'
            f'</article>'
        )
    return f'<section class="exhibits"><h2>{titulo}</h2>{"".join(blocos)}</section>'


def _rastreabilidade_exhibits_html(log_exhibits: list, dicionario: dict) -> str:
    """Rastreabilidade dos exhibits na Evidência (G8): uma linha por série/
    overlay resolvida, dizendo de onde veio -- mesmo espírito do log de
    resolução de placeholders logo abaixo, com o SEU PRÓPRIO formato
    (`{exhibit, serie, origem, detalhe}`, o que `exhibits.resolver`
    devolve; note que uma entrada de OVERLAY também usa a chave 'serie'
    para o índice posicional -- assim `exhibits.resolver_overlay` já
    produz, ver `exhibits.py`)."""
    titulo = html.escape(t(dicionario, "evidencia.exhibits_titulo"))
    if not log_exhibits:
        vazio = html.escape(t(dicionario, "evidencia.exhibits_vazio"))
        return f'<section class="rastreabilidade-exhibits"><h2>{titulo}</h2><p>{vazio}</p></section>'

    cabecalho = (
        f'<th>{html.escape(t(dicionario, "evidencia.exhibits_colunas.exhibit"))}</th>'
        f'<th>{html.escape(t(dicionario, "evidencia.exhibits_colunas.indice"))}</th>'
        f'<th>{html.escape(t(dicionario, "evidencia.exhibits_colunas.origem"))}</th>'
        f'<th>{html.escape(t(dicionario, "evidencia.exhibits_colunas.detalhe"))}</th>'
    )
    linhas = "".join(
        "<tr>"
        f'<td>{html.escape(_texto_valor(entrada.get("exhibit")))}</td>'
        f'<td>{html.escape(_texto_valor(entrada.get("serie")))}</td>'
        f'<td>{html.escape(_texto_valor(entrada.get("origem")))}</td>'
        f'<td>{html.escape(_texto_valor(entrada.get("detalhe")))}</td>'
        "</tr>"
        for entrada in log_exhibits
    )
    tabela = f'<table class="log-exhibits"><thead><tr>{cabecalho}</tr></thead><tbody>{linhas}</tbody></table>'
    return f'<section class="rastreabilidade-exhibits"><h2>{titulo}</h2>{tabela}</section>'


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

        # B2 (achado F2): rota e convenção terminal vêm de `resultados`
        # (dados já canonicalizados pela integração), nunca de `caso` --
        # `resultados.rota` e `manchete.convencao_terminal` (A1; sempre
        # presente aqui, porque este ramo só executa quando
        # "multiplo" in manchete, e `_montar_manchete` só publica
        # 'multiplo' junto com 'convencao_terminal', nunca no ramo SOTP).
        rota = resultados["rota"]
        convencao = manchete["convencao_terminal"]
        rota_rotulo = html.escape(_rotulo_rota(catalogo, rota, idioma))
        tv_rotulo = html.escape(_rotulo_convencao_terminal(catalogo, convencao, idioma))
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

def _evidencia_html(resultados: dict, ficha_tecnica: dict, log: list, log_exhibits: list,
                     idioma: str, dicionario: dict) -> str:
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

    bloco_rastreabilidade_exhibits = _rastreabilidade_exhibits_html(log_exhibits, dicionario)
    return bloco_metodologia + bloco_ficha + bloco_log + bloco_rastreabilidade_exhibits


def _ler_asset(nome: str) -> str:
    """Lê um asset PRÓPRIO do skill (`assets/<nome>`) como texto -- usado só
    para os vendorizados/adaptador do uPlot (Task 2). Nunca a integração
    (E3): estes arquivos vivem em `skills/er-relatorio/assets/`, o mesmo
    diretório de `template.html`/`i18n/`."""
    return (_DIR_ASSETS / nome).read_text(encoding="utf-8")


def compor(entrega: dict, catalogo: dict, achados: list, log: list, idioma: str,
           exhibits_resolvidos: list | None = None, log_exhibits: list | None = None) -> str:
    """Compõe o HTML autocontido das três abas a partir só dos contratos já
    carregados/validados por quem chama (`builder.py`).

    `achados`: a lista de `qc.Achado` que `qc.avaliar` já produziu — a Tese
    mostra só os de nível REQUIRED_DISCLOSURE (HARD_FAIL nunca chega aqui,
    regra inviolável 2; QUALITY_WARNING nunca aparece no HTML). `log`: o
    log de resolução de placeholders da conclusão (mesmo formato que
    `placeholders.resolver` devolve), exibido em tabela na Evidência.

    `exhibits_resolvidos`/`log_exhibits` (fatia 5B, item 5, Task 2): o que
    `exhibits.resolver(entrega)` devolve -- `builder.py` chama isso UMA
    única vez (depois que a primeira passada do QC já confirmou zero HARD
    FAIL) e passa o resultado para cá; este módulo NUNCA chama `exhibits.
    resolver` de novo (nem importa `exhibits.py` -- só lê as chaves que a
    série/overlay já resolvida carrega). Omissos (`None`, o padrão):
    equivalem a uma entrega sem exhibit nenhum (`[]`/`[]`) -- preserva todo
    chamador existente (`tests/test_relatorio_render.py`, anterior a esta
    fatia) sem precisar tocar nele.

    Determinístico por construção: mesma entrada, mesmos bytes — nenhuma
    ordem de `set` não determinística, nenhum relógio, nenhum caminho
    absoluto no HTML emitido, nenhuma id gerada em tempo de execução.
    """
    exhibits_resolvidos = exhibits_resolvidos if exhibits_resolvidos is not None else []
    log_exhibits = log_exhibits if log_exhibits is not None else []

    dicionario = placeholders.carregar_dicionario(idioma)

    execucao = entrega["execucao"]
    caso = entrega["caso"]
    resultados = entrega["resultados"]
    dados = entrega.get("dados") or {}

    empresa = html.escape(str(caso.get("companhia", "")))
    ticker = html.escape(str(execucao.get("ticker", "")))
    titulo = t(dicionario, "titulo_pagina", empresa=empresa, ticker=ticker)

    corpo_tese = _tese_html(entrega, achados, idioma, dicionario, titulo) + _exhibits_html(
        exhibits_resolvidos, dicionario)
    corpo_valuation = _valuation_html(caso, resultados, catalogo, idioma, dicionario)
    corpo_evidencia = _evidencia_html(
        resultados, entrega["ficha_tecnica"], log, log_exhibits, idioma, dicionario)

    dados_exhibits = _json_embutido({
        "formatacao": _formatacao_grafico(dicionario),
        "exhibits": [_exhibit_para_json(exhibit, dados) for exhibit in exhibits_resolvidos],
    })

    # O uPlot vendorizado (~50 KB minificado) e o adaptador só entram na
    # página quando a entrega de fato declara exhibit -- uma entrega sem
    # gráfico nenhum (G10 do desenho: "não há gráfico obrigatório") não
    # paga o custo de bytes de uma biblioteca que nunca seria usada.
    # Substitutos vazios são HTML válido (`<style></style>`/`<script>
    # </script>`) -- o bootstrap estático de `template.html` já checa
    # `typeof FleetGraficos === "undefined"` antes de usá-lo.
    if exhibits_resolvidos:
        css_uplot = _ler_asset("uPlot.min.css")
        js_uplot = _ler_asset("uPlot.iife.min.js")
        js_graficos = _ler_asset("graficos.js")
    else:
        css_uplot = js_uplot = js_graficos = ""

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
        css_uplot=css_uplot,
        js_uplot=js_uplot,
        js_graficos=js_graficos,
        dados_exhibits=dados_exhibits,
    )
