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


class JsonNaoSerializavel(Exception):
    """O payload que iria para dentro do `<script type="application/json">`
    tem um valor que não vira JSON válido para o browser (`NaN`/`Infinity`
    num dataset, por exemplo) — recusa NOMEADA, nunca a `ValueError` crua do
    `json.encoder` com traceback (B3, achado F6)."""


class CampoDeContratoAusente(Exception):
    """Um campo que os painéis da Valuation LEEM do contrato já validado
    (`caso`/`resultados`) não está lá — recusa NOMEADA, com o caminho
    completo, nunca um `KeyError` cru com traceback (o docstring de
    `builder.py` promete, para o código 1, que "a razão sai em stderr,
    nomeando o campo/chave"). `caso`/`resultados` são opacos para este
    módulo (E3): ele não os revalida, só nomeia o que faltou quando de fato
    precisou ler."""


class RotuloDoCatalogoAusente(Exception):
    """O catálogo de apresentação (A6) não tem o que esta entrega de fato
    usa — rótulo de rota, de opção de premissa, de múltiplo, de linha da
    ponte, ou (A4/achado F7) o formato de uma `unidade` declarada pelo
    contrato. Nunca um código cru ('firm', 'gordon') aparece no relatório em
    lugar do rótulo, e nunca um número é formatado por convenção decorada
    quando o catálogo não diz qual é a unidade."""


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


def _rotulo_linha_da_ponte(catalogo: dict, linha: str, idioma: str) -> str:
    """Rótulo de uma linha de balanço da ponte (`catalogo.ponte.<linha>`,
    fatia 5B/Task 3, S2) — mesma disciplina de `_rotulo_rota`/`_rotulo_
    multiplo`: quem nomeia é o catálogo de apresentação (A6), nunca o código
    cru ('divida_bruta') e nunca uma tabela no JS. `tests/test_catalogo_
    apresentacao.py` trava as chaves contra as linhas que o gate valida."""
    info = catalogo.get("ponte", {}).get(linha)
    if info is None:
        raise RotuloDoCatalogoAusente(f"catálogo de apresentação sem a linha de ponte '{linha}' em 'ponte'.")
    rotulo = info.get("rotulo", {}).get(idioma)
    if not rotulo:
        raise RotuloDoCatalogoAusente(
            f"catálogo de apresentação sem rótulo em '{idioma}' para a linha de ponte '{linha}'."
        )
    return rotulo


def _espec_de_formato_da_unidade(catalogo: dict, unidade: Any, idioma: str, moeda: str | None) -> dict:
    """A4 (onda de correção da revisão final, achado F7): como formatar um
    número cuja UNIDADE o contrato declara -- `catalogo.unidades.<unidade>.
    formato` traduz a unidade (vocabulário da integração: o motor publica
    `unidade` em cada grade; o catálogo publica `unidade` em cada premissa)
    no código de formato que `placeholders` já conhece, e a receita
    (`especificacao_de_formato`) viaja no payload para o `svg.js` aplicar.

    Antes desta correção o relatório DESCARTAVA `unidade` e o `svg.js`
    imprimia tudo com 2 casas e nenhum sufixo: a mesma página escrevia a
    manchete como "R$ 61,91" e a célula que vale esse mesmo número como
    "61,91", e um v10 que trocasse a métrica da grade (células viram
    múltiplo) desenhava 6,69 no lugar de 61,91 sem nenhum aviso. Uma unidade
    que o catálogo não conhece é recusa NOMEADA -- em produção pelo QC
    (`unidade_desconhecida`, HARD FAIL, antes de renderizar), e aqui como
    defesa em profundidade, nunca um número formatado ao acaso."""
    info = (catalogo.get("unidades") or {}).get(unidade)
    formato = info.get("formato") if isinstance(info, dict) else None
    if not formato:
        raise RotuloDoCatalogoAusente(
            f"catálogo de apresentação sem a unidade '{unidade}' em 'unidades' — "
            "o relatório não formata um número cuja unidade o contrato não declara."
        )
    try:
        return placeholders.especificacao_de_formato(formato, idioma, moeda)
    except placeholders.FormatoInvalido as erro:
        raise RotuloDoCatalogoAusente(
            f"catálogo de apresentação declara para a unidade '{unidade}' um formato "
            f"que este relatório não conhece: {erro}"
        ) from erro


def _rotulo_premissa(catalogo: dict, rota: str, premissa: str, idioma: str) -> str:
    """Rótulo de uma premissa (`catalogo.premissas.<rota>.<premissa>`) — os
    eixos da matriz de sensibilidade. O gate já recusa uma grade que varie
    premissa fora do vocabulário da rota, e `tests/test_catalogo_
    apresentacao.py::test_premissas_do_catalogo_sao_exatamente_as_do_gate`
    já garante que o catálogo cobre esse vocabulário — então a ausência aqui
    é erro de catálogo, nomeado, nunca um código cru na tela."""
    info = catalogo.get("premissas", {}).get(rota, {}).get(premissa)
    if info is None:
        raise RotuloDoCatalogoAusente(
            f"catálogo de apresentação sem a premissa '{premissa}' da rota '{rota}' em 'premissas'."
        )
    rotulo = info.get("rotulo", {}).get(idioma)
    if not rotulo:
        raise RotuloDoCatalogoAusente(
            f"catálogo de apresentação sem rótulo em '{idioma}' para a premissa "
            f"'{premissa}' da rota '{rota}'."
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
    consegue parsear.

    `indent=2` (fatia 5B, Task 3) não é cosmético: no formato compacto, dois
    objetos que fecham juntos imprimem '}}' — e '{{'/'}}' na página é
    exatamente o token que `tests/test_relatorio_contrato.py::test_
    placeholder_quebrado_por_quebra_de_linha_agora_resolve` varre para provar
    que nenhum placeholder cru sobrou (a mesma razão pela qual o uPlot
    minificado só é embutido quando há exhibit). O payload dos painéis da
    Valuation aninha objetos (`paineis_valuation.ponte.total`), então o
    formato compacto passaria a produzir esse par. Indentar separa todo
    fechamento por uma quebra de linha, sem mudar o JSON que o browser lê.

    B3 (achado F6, caso c): a defesa em profundidade acima estava certa, mas
    a exceção NÃO ERA NOMEADA -- era a do `json.encoder`, que ninguém
    capturava: um `NaN` num campo de dataset (o literal que `json.loads`
    aceita) derrubava o builder com traceback cru, rc 1 e nenhum `qc.json`.
    Agora vira `JsonNaoSerializavel`, que `builder.py` captura junto das
    outras recusas nomeadas."""
    try:
        bruto = json.dumps(dados, ensure_ascii=False, allow_nan=False, indent=2)
    except ValueError as erro:
        raise JsonNaoSerializavel(
            f"o payload embutido tem um valor que não vira JSON válido: {erro}. "
            "Um dataset com NaN/Infinity quebraria o JSON.parse do browser."
        ) from erro
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


def _datasets_do_exhibit(exhibit_resolvido: dict, dados: dict) -> list:
    """Ids dos datasets que as séries `direta`/`derivada` deste exhibit
    referenciam, sem repetição. Só para decidir o rótulo (B1b); este módulo
    não importa `exhibits.py` (ver o cabeçalho desta seção) e lê apenas as
    chaves que a série já resolvida carrega."""
    ids = []
    for serie in exhibit_resolvido["series"]:
        derivacao = serie.get("derivacao")
        fonte = serie.get("fonte")
        if not isinstance(fonte, str):
            continue
        dataset_id = fonte.partition(".")[0] if derivacao == "direta" else fonte
        if derivacao in ("direta", "derivada") and dataset_id in dados and dataset_id not in ids:
            ids.append(dataset_id)
    return ids


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


def _rotulo_serie(serie: dict, varios_datasets: bool = False) -> str:
    """B1 (achado F3, segunda metade): quando o exhibit toca MAIS DE UM
    dataset, o rótulo de uma série `direta` é a `fonte` INTEIRA
    ('fin.margem'/'peers.margem'), não só o nome do campo -- dois datasets
    com um campo de mesmo nome davam duas séries com o MESMO rótulo de
    legenda, e o leitor não conseguia nem distinguir qual era qual. Com um
    dataset só (o caso normal), o nome do campo continua bastando e o
    rótulo fica curto. Isto é rotulagem de apresentação, dentro do E3."""
    derivacao = serie["derivacao"]
    if derivacao == "direta":
        return serie["fonte"] if varios_datasets else serie["fonte"].partition(".")[2]
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
    varios_datasets = len(_datasets_do_exhibit(exhibit_resolvido, dados)) > 1
    return {
        "id": exhibit_resolvido["id"],
        "tipo": exhibit_resolvido["tipo"],
        "eixoX": _eixo_x_do_exhibit(exhibit_resolvido, dados),
        "series": [
            {"rotulo": _rotulo_serie(serie, varios_datasets),
             "valores": _valores_lista(serie["valores"])}
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

# --------------------------------------------------------------------------
# Painéis SVG da Valuation (fatia 5B, item 5, Task 3, S1): o waterfall da
# ponte e uma matriz por grade 2D de sensibilidade. NÃO são exhibits
# declarados — a spec resolvida de um exhibit é `eixoX + séries de números`
# (`_exhibit_para_json`), que não expressa nem `{rotulo, valor, sinal}` nem
# uma grade com dois eixos de premissa. São painéis alimentados direto por
# `resultados.ponte`/`resultados.sensibilidades.grades_2d`.
#
# Este módulo só COLHE e ROTULA: nenhuma conta acontece aqui (E3). O total do
# waterfall é o `nd_efetivo` que o wrapper já somou; os números das células
# são os que o motor já rodou. Rótulo de linha da ponte e de premissa vêm do
# catálogo (A6/S2); título e rótulo do total, do dicionário (§16.1) — o
# `svg.js` não conhece prosa nenhuma (S3).
# --------------------------------------------------------------------------

def _campo_de_contrato(objeto: dict, campo: str, onde: str) -> Any:
    """Lê `campo` de um bloco de `resultados` que os painéis DESENHAM,
    nomeando a ausência — B3 (achado F6, caso d): um v10 que renomeie
    `resultados.ponte.nd_efetivo` (ou `celulas`, ou `pontos_x`) derrubava o
    builder com `KeyError: 'nd_efetivo'`, rc 1 e nenhum `qc.json`, em vez da
    recusa nomeada que o docstring de `builder.py` promete para o código 1.
    `caso`/`resultados` continuam opacos (E3): este módulo não os revalida,
    só nomeia o que faltou no ponto exato em que precisou ler."""
    if not isinstance(objeto, dict) or campo not in objeto:
        raise CampoDeContratoAusente(
            f"campo ausente em '{onde}': '{campo}' — o painel da Valuation o desenha, "
            "e o relatório nunca inventa nem omite em silêncio um número do motor."
        )
    return objeto[campo]


def _grades_2d(resultados: dict) -> list:
    sensibilidades = resultados.get("sensibilidades")
    if not isinstance(sensibilidades, dict):
        return []
    grades = sensibilidades.get("grades_2d")
    return grades if isinstance(grades, list) else []


def _ponte_para_json(resultados: dict, catalogo: dict, idioma: str, dicionario: dict,
                      moeda: str | None) -> dict | None:
    """Payload do waterfall, ou `None` quando a entrega não tem ponte (rota
    equity) — S6: o painel simplesmente não aparece, nada de seção vazia com
    texto de erro.

    A4 (achado F7): `formato` viaja junto. As linhas da ponte são valores de
    balanço na moeda do caso — a MESMA moeda que o cabeçalho da Valuation já
    formata logo acima (`_valuation_html`), pelo mesmo `placeholders`. Sem
    isto o waterfall imprimia "800,00" onde a manchete imprime "R$ 61,91"."""
    ponte = resultados.get("ponte")
    if not isinstance(ponte, dict) or not ponte.get("parcelas"):
        return None
    onde_parcela = "resultados.ponte.parcelas[*]"
    return {
        "parcelas": [
            {
                "rotulo": _rotulo_linha_da_ponte(
                    catalogo, _campo_de_contrato(parcela, "rotulo", onde_parcela), idioma),
                "valor": _campo_de_contrato(parcela, "valor", onde_parcela),
                "sinal": _campo_de_contrato(parcela, "sinal", onde_parcela),
            }
            for parcela in ponte["parcelas"]
        ],
        "total": {
            "rotulo": t(dicionario, "valuation.ponte_total"),
            "valor": _campo_de_contrato(ponte, "nd_efetivo", "resultados.ponte"),
        },
        "formato": placeholders.especificacao_de_formato("moeda", idioma, moeda),
    }


def _base_da_grade(caso: dict, grade: dict) -> dict | None:
    """O par (x, y) da célula-base de uma grade 2D — S4: as premissas
    centrais do cenário QUE A GRADE PERTURBOU (`caso.sensibilidades.cenario`),
    nunca outro cenário. As células são substituições naquele vetor central;
    comparar contra outro marcaria uma célula que não é a central. A
    comparação em si (igualdade exata) é do `svg.js`; aqui só se colhe o par.
    Premissa do eixo ausente do cenário, ou não numérica, devolve `None` —
    e aí nenhuma célula é marcada, nunca uma aproximação."""
    sensibilidades = caso.get("sensibilidades")
    if not isinstance(sensibilidades, dict):
        return None
    cenario = (caso.get("cenarios") or {}).get(sensibilidades.get("cenario"))
    premissas = (cenario or {}).get("premissas") or {}
    par = {}
    for eixo, chave in (("x", grade.get("premissa_x")), ("y", grade.get("premissa_y"))):
        valor = premissas.get(chave)
        if isinstance(valor, bool) or not isinstance(valor, (int, float)):
            return None
        par[eixo] = valor
    return par


def _unidade_da_premissa(catalogo: dict, rota: str, premissa: str) -> Any:
    info = (catalogo.get("premissas") or {}).get(rota, {}).get(premissa)
    if not isinstance(info, dict) or "unidade" not in info:
        raise RotuloDoCatalogoAusente(
            f"catálogo de apresentação sem a unidade da premissa '{premissa}' "
            f"da rota '{rota}' em 'premissas'."
        )
    return info["unidade"]


def _matrizes_para_json(caso: dict, resultados: dict, catalogo: dict, idioma: str,
                         moeda: str | None) -> list:
    """Uma entrada por grade 2D, na ordem declarada (S6). `grade` carrega só
    o que o `svg.js` desenha; as células vão como estão em `resultados` —
    números prontos, nunca recalculados.

    A4 (achado F7): três receitas de formato viajam junto, cada uma da
    unidade que o contrato DECLARA para aquele número — `formato` das
    células (`grade.unidade`, publicada pelo motor: "preço por ação" hoje) e
    `formatoX`/`formatoY` dos pontos de cada eixo (a `unidade` da premissa
    no catálogo: 'pp' para roic/g, 'anos' para n...). Antes desta correção
    `unidade` era descartada aqui e o ROIC de 12 p.p. saía "12,00" ao lado
    de uma célula em reais impressa do mesmo jeito."""
    rota = _campo_de_contrato(resultados, "rota", "resultados")
    onde = "resultados.sensibilidades.grades_2d[*]"
    return [
        {
            "grade": {
                "pontos_x": _campo_de_contrato(grade, "pontos_x", onde),
                "pontos_y": _campo_de_contrato(grade, "pontos_y", onde),
                "celulas": _campo_de_contrato(grade, "celulas", onde),
            },
            "base": _base_da_grade(caso, grade),
            "rotuloX": _rotulo_premissa(
                catalogo, rota, _campo_de_contrato(grade, "premissa_x", onde), idioma),
            "rotuloY": _rotulo_premissa(
                catalogo, rota, _campo_de_contrato(grade, "premissa_y", onde), idioma),
            "formato": _espec_de_formato_da_unidade(catalogo, grade.get("unidade"), idioma, moeda),
            "formatoX": _espec_de_formato_da_unidade(
                catalogo, _unidade_da_premissa(catalogo, rota, grade["premissa_x"]), idioma, moeda),
            "formatoY": _espec_de_formato_da_unidade(
                catalogo, _unidade_da_premissa(catalogo, rota, grade["premissa_y"]), idioma, moeda),
        }
        for grade in _grades_2d(resultados)
    ]


def _paineis_valuation_para_json(caso: dict, resultados: dict, catalogo: dict,
                                  idioma: str, dicionario: dict) -> dict:
    moeda = caso.get("moeda")
    return {
        "ponte": _ponte_para_json(resultados, catalogo, idioma, dicionario, moeda),
        "matrizes": _matrizes_para_json(caso, resultados, catalogo, idioma, moeda),
    }


def _cenario_da_grade(caso: dict) -> str:
    """A3 (achado F4): o nome do cenário QUE AS GRADES PERTURBARAM
    (`caso.sensibilidades.cenario`, o mesmo que `_base_da_grade` usa para
    marcar a célula-base, S4) — dado do caso, nunca prosa do relatório.

    Existe porque a página mostrava "R$ 61,91" (a manchete, do
    `cenario_base`) no topo e, logo abaixo, uma matriz cuja célula
    contornada em vermelho lia 69,54, sem nomear cenário nenhum: a marcação
    estava certa e o leitor não tinha como saber de que cenário ela era.
    Um `caso` com grade 2D sempre declara esse nome (o gate exige 'cenario'
    junto de 'grades_2d'); a ausência aqui é contrato quebrado, recusa
    nomeada, nunca um título sem cenário."""
    sensibilidades = caso.get("sensibilidades")
    nome = sensibilidades.get("cenario") if isinstance(sensibilidades, dict) else None
    if not isinstance(nome, str) or not nome.strip():
        raise CampoDeContratoAusente(
            "'caso.sensibilidades.cenario' ausente ou não é texto, mas a entrega "
            "traz grade 2D: o painel da matriz não pode nomear o cenário que a grade perturbou."
        )
    return nome


def _paineis_valuation_html(caso: dict, resultados: dict, catalogo: dict,
                             idioma: str, dicionario: dict) -> str:
    """Hosts VAZIOS na aba Valuation, na mesma ordem do payload — só o
    `svg.js` os preenche (bootstrap estático em `template.html`). Nenhum host
    quando não há o que desenhar (S6)."""
    rota = _campo_de_contrato(resultados, "rota", "resultados")
    moeda = caso.get("moeda")
    blocos = []
    if _ponte_para_json(resultados, catalogo, idioma, dicionario, moeda) is not None:
        titulo = html.escape(t(dicionario, "valuation.ponte_titulo"))
        blocos.append(
            f'<section class="painel-svg">'
            f'<h2>{titulo}</h2>'
            f'<div class="painel-grafico" data-painel="ponte"></div>'
            f'</section>'
        )
    for indice, grade in enumerate(_grades_2d(resultados)):
        titulo = html.escape(t(
            dicionario, "valuation.matriz_titulo",
            cenario=_cenario_da_grade(caso),
            x=_rotulo_premissa(catalogo, rota, grade["premissa_x"], idioma),
            y=_rotulo_premissa(catalogo, rota, grade["premissa_y"], idioma),
        ))
        blocos.append(
            f'<section class="painel-svg">'
            f'<h2>{titulo}</h2>'
            f'<div class="painel-grafico" data-painel="matriz" data-painel-indice="{indice}"></div>'
            f'</section>'
        )
    return "".join(blocos)


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
        f'{_paineis_valuation_html(caso, resultados, catalogo, idioma, dicionario)}'
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

    # Os painéis SVG da Valuation entram no MESMO `<script type="application/
    # json">` dos exhibits (uma chave a mais, `paineis_valuation`) — nunca um
    # segundo bloco e nunca um segundo caminho de escape: `_json_embutido` é
    # a única porta de saída de JSON deste módulo.
    paineis_valuation = _paineis_valuation_para_json(caso, resultados, catalogo, idioma, dicionario)
    dados_exhibits = _json_embutido({
        "formatacao": _formatacao_grafico(dicionario),
        "exhibits": [_exhibit_para_json(exhibit, dados) for exhibit in exhibits_resolvidos],
        "paineis_valuation": paineis_valuation,
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

    # Mesma economia para o módulo SVG (Task 3): ele só entra quando há
    # painel para desenhar. Os dois módulos são embutidos de forma
    # INDEPENDENTE — uma entrega pode ter painel sem exhibit, ou o contrário
    # —, e é por isso que `svg.js` não pode depender de `FleetGraficos`
    # existir na página (ver o cabeçalho de `svg.js`).
    tem_painel = paineis_valuation["ponte"] is not None or bool(paineis_valuation["matrizes"])
    js_svg = _ler_asset("svg.js") if tem_painel else ""

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
        js_svg=js_svg,
        dados_exhibits=dados_exhibits,
    )
