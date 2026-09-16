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

Fatia 5D, Task 3: a aba Tese é a decisão de investimento da §9 do desenho, na
ordem de D7 (ver a seção "Aba Tese" abaixo). Todo texto de `analise` que ela
exibe sai de `placeholders.resolver_prosa` — a mesma lista de prosa que o QC
varre e que o log da Evidência registra —, e todo vocabulário sai rotulado:
premissa, bloco e classe de fronteira pelo catálogo; tema, vetor, incorporação e
papel da faixa pelo dicionário.

Fatia 5D, onda de correção da revisão final (F1): sob fronteira de escopo, todo
número que a integração declara conclusão de valor (`catalogo.conclusoes_de_valor`)
é leitura condicional — fora da Conclusão da Tese, que fica só com o múltiplo de
tela, e com o rótulo condicional do dicionário na Valuation. Uma decisão só, em
`_leitura_condicional` (ver a seção "Leitura condicional").

Fatia 5F, Task 5 (D15): a aba Valuation na ordem da §9 — cabeçalho (com a faixa
piso–teto e o par de múltiplos forward), como o valor é formado, cenários,
laboratório, ponte, sensibilidades (tabelas 1D e matrizes 2D) e o que está no
preço, lido pela `leitura` que a integração publica. A escala dos montantes entra
só onde a unidade do catálogo a declara; a premissa decisiva de uma parte de SOTP
e o vínculo multi-rota saem rotulados na Tese; e o bootstrap pareia cada matriz ao
seu host pelo índice (ver "Aba Valuation na ordem da §9").
"""

import html
import json
import string
from pathlib import Path
from typing import Any

import entrega as contrato_entrega
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


class ProsaNaoAuditada(Exception):
    """O relatório tentou exibir um texto de `analise` que não está na lista de
    prosa auditada (`placeholders.campos_de_prosa`) — fatia 5D, Task 3, achado 3.
    Um texto fora dela sairia na tela sem o QC de placeholder e sem linha no log
    da Evidência; a recusa é nomeada, nunca um texto exibido às cegas."""


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


def _formato_da_unidade(catalogo: dict, unidade: Any) -> str:
    """O CÓDIGO de formato (`moeda`, `pp2`, `num0`...) que o catálogo declara
    para a `unidade` que o contrato usa — a tradução do vocabulário da
    integração para o de `placeholders`. Unidade que o catálogo não conhece é
    recusa NOMEADA: o relatório não formata ao acaso um número cuja unidade
    ninguém declarou (achado F7/A4)."""
    info = (catalogo.get("unidades") or {}).get(unidade)
    formato = info.get("formato") if isinstance(info, dict) else None
    if not formato:
        raise RotuloDoCatalogoAusente(
            f"catálogo de apresentação sem a unidade '{unidade}' em 'unidades' — "
            "o relatório não formata um número cuja unidade o contrato não declara."
        )
    return formato


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
    formato = _formato_da_unidade(catalogo, unidade)
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


def _rotulo_bloco(catalogo: dict, bloco: str, idioma: str) -> str:
    """Rótulo de um bloco econômico (`catalogo.blocos.<bloco>`) — os grupos do
    laboratório (5C) e os itens de vínculo e mecanismo da Tese (5D, D2). Mesma
    disciplina de `_rotulo_premissa`: a ausência é erro de catálogo, nomeado, e
    as duas leituras passam por aqui, para que o mesmo rótulo nunca seja lido de
    dois jeitos."""
    info = (catalogo.get("blocos") or {}).get(bloco)
    if info is None:
        raise RotuloDoCatalogoAusente(f"catálogo de apresentação sem o bloco '{bloco}' em 'blocos'.")
    rotulo = (info.get("rotulo") or {}).get(idioma)
    if not rotulo:
        raise RotuloDoCatalogoAusente(
            f"catálogo de apresentação sem rótulo em '{idioma}' para o bloco '{bloco}'.")
    return rotulo


def _rotulo_fronteira(catalogo: dict, classe: str, idioma: str) -> str:
    """Rótulo de uma classe de fronteira de escopo (`catalogo.fronteiras_de_
    escopo.<classe>`, 5D, D3). O gate valida a classe e `tests/test_catalogo_
    apresentacao.py` trava o catálogo contra esse vocabulário; a ausência aqui é
    recusa nomeada, nunca a chave crua na Conclusão."""
    info = (catalogo.get("fronteiras_de_escopo") or {}).get(classe)
    if info is None:
        raise RotuloDoCatalogoAusente(
            f"catálogo de apresentação sem a classe de fronteira de escopo '{classe}' em "
            "'fronteiras_de_escopo'.")
    rotulo = (info.get("rotulo") or {}).get(idioma)
    if not rotulo:
        raise RotuloDoCatalogoAusente(
            f"catálogo de apresentação sem rótulo em '{idioma}' para a classe de fronteira de "
            f"escopo '{classe}'.")
    return rotulo


def _rotulo_do_vinculo(catalogo: dict, rotas: list, item: str, idioma: str) -> str:
    """Rótulo de um item de vínculo ou de mecanismo da Tese (D2): premissa de uma das
    `rotas` (`_rotulo_premissa`, pela primeira rota que a contém) ou bloco econômico
    (`_rotulo_bloco`). `rotas` é a do caso e, num SOTP, a de cada parte (fatia 5F, Task
    5, D13: o vínculo rotulado pela rota que o contém). O QC já recusa item fora delas e
    dos blocos antes de renderizar (`vinculo_fora_do_vocabulario`, HARD FAIL); aqui,
    defesa em profundidade, nomeada."""
    for rota in rotas:
        if item in ((catalogo.get("premissas") or {}).get(rota) or {}):
            return _rotulo_premissa(catalogo, rota, item, idioma)
    if item in (catalogo.get("blocos") or {}):
        return _rotulo_bloco(catalogo, item, idioma)
    raise RotuloDoCatalogoAusente(
        f"catálogo de apresentação sem '{item}' entre as premissas das rotas {', '.join(rotas)} e os "
        "blocos econômicos — um vínculo nunca aparece pela chave crua."
    )


def _rotas_do_valuation(resultados: dict) -> list:
    """A rota do caso e, num SOTP, a de cada parte de `resultados.sotp.partes` — sem
    repetição, na ordem publicada (fatia 5F, Task 5, D13). Leitura de contrato."""
    sotp = resultados.get("sotp")
    partes = sotp.get("partes") if isinstance(sotp, dict) else None
    candidatas = [resultados.get("rota")] + [parte.get("rota") for parte in (partes or []) if isinstance(parte, dict)]
    rotas: list = []
    for rota in candidatas:
        if isinstance(rota, str) and rota not in rotas:
            rotas.append(rota)
    return rotas


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
    """Texto de exibição de um valor de dado OPACO (entrada de `log`) —
    nunca interpretado, só tornado legível. `None` vira
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
# O texto de dado na página (fatia 5E, Task 3). Todo texto que a página escreve a
# partir de dado — a prosa resolvida da Tese, os avisos, os textos e rótulos de
# exhibit, o log de placeholders e a rastreabilidade, o ledger, o consenso, o
# confronto, a ficha técnica, os nomes de cenário, os números formatados e o título
# — passa por `_texto_de_dado_html`. Além do escape de HTML, ele troca `=`, `(` e `@`
# pela entidade: no HTML cru, um texto de dado nunca forma a assinatura de uma
# referência que a regra de autocontenção (`relatorio_nao_autocontido`) lê fora dos
# `<script>` — `data=`, `href=`, `src=`, `srcset=`, `url(` e `@import`. Medido na
# Task 3: um localizador com `?data=` na query, escrito numa célula da Evidência, era
# lido como o atributo `data=`, e a entrega saía recusada (código 2); a prosa da Tese
# tinha o mesmo falso positivo desde a 5A. O leitor vê o mesmo caractere. A regra do
# QC não muda e continua inteira para a marcação: as tags e os valores de atributo,
# que só este módulo e o template escrevem, nunca passam por aqui; os rótulos de
# interface (dicionário e catálogo), quando saem sozinhos, seguem por `html.escape`.
# --------------------------------------------------------------------------

_ENTIDADES_DO_TEXTO_DE_DADO: dict = {ord("="): "&#61;", ord("("): "&#40;", ord("@"): "&#64;"}


def _texto_de_dado_html(texto: str) -> str:
    """`texto` escapado para o HTML e sem a assinatura de uma referência externa (ver acima)."""
    return html.escape(texto).translate(_ENTIDADES_DO_TEXTO_DE_DADO)


# --------------------------------------------------------------------------
# Exhibits (fatia 5B, item 5, Task 2; reposicionados na 5D, Task 3, D5): os
# gráficos/tabelas da Tese — sob as perguntas que os citam, e os que nenhuma
# pergunta cita numa seção final (G7) — e a rastreabilidade correspondente na
# Evidência (G8). Consomem
# `exhibits_resolvidos`/`log_exhibits` que `builder.py` já produziu chamando
# `exhibits.resolver(entrega)` UMA vez (ver o docstring de `compor` abaixo) —
# este módulo nunca chama `exhibits.resolver` de novo, e nunca importa
# `exhibits.py`: só lê as chaves que a série/overlay JÁ RESOLVIDA carrega
# (`derivacao`, `fonte`/`formula_nota`/`chave`, `valores`/`valor`), o mesmo
# jeito que `render.py` já trata `caso`/`resultados` como dado opaco (E3).
#
# O adaptador do browser (`graficos.js`) não lê nada disso: recebe só
# números e rótulos já prontos (`_exhibit_para_json`) — nunca uma `fonte` ou
# uma `formula` crua. Rótulo de série/overlay é o que a série declara: o nome
# do campo para `direta` (identificador de `dados`), a `formula_nota` para
# `derivada` e o `rotulo` para `engine` — os dois últimos, prosa da lista
# auditável, resolvida (onda de correção da revisão final da 5D, F3 e N12: a
# série `engine` saía com a própria `chave` no cabeçalho da tabela); overlay usa
# o `rotulo` declarado, também da lista de prosa, senão a própria `chave`. Isso
# é rotulagem de apresentação, nunca conta de valuation (E3).
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


def _rotulo_serie(serie: dict, onde: str, prosa: dict, varios_datasets: bool = False) -> str:
    """B1 (achado F3, segunda metade): quando o exhibit toca MAIS DE UM
    dataset, o rótulo de uma série `direta` é a `fonte` INTEIRA
    ('fin.margem'/'peers.margem'), não só o nome do campo -- dois datasets
    com um campo de mesmo nome davam duas séries com o MESMO rótulo de
    legenda, e o leitor não conseguia nem distinguir qual era qual. Com um
    dataset só (o caso normal), o nome do campo continua bastando e o
    rótulo fica curto. Isto é rotulagem de apresentação, dentro do E3.

    Onda de correção da revisão final da 5D (F3 e N12): o rótulo de uma série
    `derivada` (a `formula_nota`) e o de uma série `engine` (o `rotulo` que ela
    declara) são prosa da Tese — o gráfico os escreve sob a pergunta — e saem da
    lista de prosa, resolvidos (`onde` é o caminho da série). A série `engine`
    saía com a própria `chave`, crua, no cabeçalho da tabela. O nome de campo de
    uma série `direta` é identificador de `dados` (contrato da 5E)."""
    derivacao = serie["derivacao"]
    if derivacao == "direta":
        return serie["fonte"] if varios_datasets else serie["fonte"].partition(".")[2]
    if derivacao == "derivada":
        return _prosa(prosa, f"{onde}.formula_nota")
    return _prosa(prosa, f"{onde}.rotulo")  # engine


def _rotulo_overlay(overlay: dict, onde: str, prosa: dict) -> str:
    """O `rotulo` declarado, resolvido pela lista de prosa (F3) — ou, sem ele, a
    `chave` do overlay, que o contrato da 5B mantém opcional."""
    if overlay.get("rotulo"):
        return _prosa(prosa, f"{onde}.rotulo")
    return overlay["chave"]


def _valores_lista(valores: Any) -> list:
    """Normaliza um valor já resolvido para lista -- uma série `engine`
    pode resolver um ÚNICO número (ex.: o preço de um cenário, ver
    `test_serie_engine_le_caminho_real_de_resultados`); o adaptador do
    browser nunca precisa distinguir escalar de lista de um elemento."""
    return valores if isinstance(valores, list) else [valores]


def _exhibit_para_json(exhibit_resolvido: dict, indice: int, dados: dict, prosa: dict) -> dict:
    """Spec resolvida que `graficos.js` de fato recebe (contrato descrito no
    cabeçalho de `graficos.js`) -- só números e rótulos, nenhuma fonte nem
    fórmula crua. Os rótulos de série derivada, de série engine e de overlay saem
    resolvidos da lista de prosa (`indice` é a posição do exhibit, a mesma do seu
    caminho na lista); só um overlay sem `rotulo` mostra a própria `chave`."""
    varios_datasets = len(_datasets_do_exhibit(exhibit_resolvido, dados)) > 1
    onde = f"analise.exhibits.{indice}"
    return {
        "id": exhibit_resolvido["id"],
        "tipo": exhibit_resolvido["tipo"],
        "eixoX": _eixo_x_do_exhibit(exhibit_resolvido, dados),
        "series": [
            {"rotulo": _rotulo_serie(serie, f"{onde}.series.{posicao}", prosa, varios_datasets),
             "valores": _valores_lista(serie["valores"])}
            for posicao, serie in enumerate(exhibit_resolvido["series"])
        ],
        "overlays": [
            {"rotulo": _rotulo_overlay(overlay, f"{onde}.overlays.{posicao}", prosa), "valor": overlay["valor"]}
            for posicao, overlay in enumerate(exhibit_resolvido.get("overlays", []))
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


def _exhibit_html(exhibit: dict, indice: int, prosa: dict, tag_titulo: str) -> str:
    """Um exhibit como o leitor o encontra: a pergunta dele como título, a nota
    de janela, o host VAZIO que só `graficos.js` preenche (bootstrap estático em
    `template.html`) e o caption. Os três textos saem da lista de prosa auditada
    (5D, Task 3, achado 4): dentro da aba Tese, um caption é prosa da tese.

    `indice` é a posição do exhibit em `exhibits_resolvidos` — a mesma da sua
    spec no payload (`_exhibit_para_json`, montado na mesma ordem). O host o
    carrega em `data-exhibit-indice`, e é por ESTE atributo que o bootstrap
    pareia host e spec (achado 1): sob as perguntas, a ordem do DOM é a das
    perguntas, e o mesmo exhibit pode aparecer em duas delas. Nenhum outro
    elemento da página carrega o atributo. `tag_titulo` é o nível do título:
    `h4` sob uma pergunta, `h3` na seção final."""
    onde = f"analise.exhibits.{indice}"
    partes = [f'<{tag_titulo}>{_texto_de_dado_html(_prosa(prosa, onde + ".pergunta"))}</{tag_titulo}>']
    if exhibit.get("nota_janela"):
        partes.append(f'<p class="exhibit-nota-janela">{_texto_de_dado_html(_prosa(prosa, onde + ".nota_janela"))}</p>')
    partes.append(f'<div class="exhibit-grafico" data-exhibit-indice="{indice}"></div>')
    if exhibit.get("caption"):
        partes.append(f'<p class="exhibit-caption">{_texto_de_dado_html(_prosa(prosa, onde + ".caption"))}</p>')
    return f'<article class="exhibit">{"".join(partes)}</article>'


def _exhibits_nao_citados_html(exhibits_resolvidos: list, citados: set, prosa: dict,
                                dicionario: dict) -> str:
    """D7: a última seção da aba, com os exhibits que nenhuma pergunta cita, na
    ordem declarada — ou nada, quando toda pergunta cita os seus: nenhuma seção
    vazia."""
    artigos = [_exhibit_html(exhibit, indice, prosa, "h3")
               for indice, exhibit in enumerate(exhibits_resolvidos) if indice not in citados]
    if not artigos:
        return ""
    return _secao_html("exhibits exhibits-nao-citados", t(dicionario, "tese.exhibits_nao_citados_titulo"),
                       "".join(artigos))


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
        f'<td>{_texto_de_dado_html(_texto_valor(entrada.get("exhibit")))}</td>'
        f'<td>{_texto_de_dado_html(_texto_valor(entrada.get("serie")))}</td>'
        f'<td>{_texto_de_dado_html(_texto_valor(entrada.get("origem")))}</td>'
        f'<td>{_texto_de_dado_html(_texto_valor(entrada.get("detalhe")))}</td>'
        "</tr>"
        for entrada in log_exhibits
    )
    tabela = f'<table class="log-exhibits"><thead><tr>{cabecalho}</tr></thead><tbody>{linhas}</tbody></table>'
    return f'<section class="rastreabilidade-exhibits"><h2>{titulo}</h2>{tabela}</section>'


# --------------------------------------------------------------------------
# Aba Tese (fatia 5D, item 5, Task 3; §9 do desenho; D3, D5 e D7 do plano): a
# decisão de investimento, na ordem de D7 — Conclusão (faixa, veredicto com o
# preço de tela, múltiplo justo × de tela corrente) → avisos obrigatórios →
# premissas decisivas → o que mudou (se declarado) → Positives/Negatives →
# perguntas, cada uma com os exhibits que cita ou a razão de não ter → riscos →
# visão não-consensual (se declarada) → exhibits que nenhuma pergunta cita.
#
# Três disciplinas, as mesmas do resto deste módulo:
# - todo TEXTO de `analise` sai de `prosa` (`_prosa`), o dicionário que
#   `placeholders.resolver_prosa` monta sobre a lista que o QC varre e que o log
#   da Evidência registra: o render não resolve texto nenhum por conta própria,
#   e o que não está na lista não chega à tela;
# - todo VOCABULÁRIO sai rotulado: premissa, bloco e classe de fronteira pelo
#   catálogo (E3); tema, vetor, incorporação e papel da faixa pelo dicionário
#   (vocabulário do Fleet, §7 e §9). Nunca a chave crua (a lição do B2);
# - todo NÚMERO já vem pronto de `resultados`/`caso` e só é formatado: o preço
#   de cada ponta da faixa, o preço de tela, o valor da premissa decisiva.
#   Nenhuma conta de valuation.
#
# HARD_FAIL nunca chega aqui (a regra inviolável 2 barra antes); QUALITY_WARNING
# nunca é exibido (só `qc.json`).
# --------------------------------------------------------------------------

# O vocabulário de `resultados.manchete.fonte` (contrato `resultados/1`,
# publicado por `avaliar._montar_manchete`): de onde vem o preço da manchete. A
# faixa sempre lê `resultados.cenarios`; quando a manchete vem do SOTP, a base
# da faixa é o cenário consolidado, e não a resposta (achado 5).
FONTE_DA_MANCHETE_CENARIOS: str = "cenarios"
FONTE_DA_MANCHETE_SOTP: str = "sotp"


def _prosa(prosa: dict, onde: str) -> str:
    """O texto resolvido de `onde`. Só existe o que `placeholders.campos_de_prosa`
    lista: um campo exibido fora dela sairia sem o QC de placeholder e sem linha
    no log da Evidência (achado 3) — recusa nomeada, nunca um texto às cegas."""
    if onde not in prosa:
        raise ProsaNaoAuditada(
            f"o relatório tentou exibir '{onde}', que não está na lista de prosa auditada "
            "(placeholders.campos_de_prosa): esse texto sairia sem o QC de placeholder e sem "
            "linha no log da Evidência."
        )
    return prosa[onde]


def _rotulo_de_vocabulario(dicionario: dict, grupo: str, codigo: str) -> str:
    """O rótulo, no dicionário, de um código de vocabulário do contrato
    `entrega/1` — tema, vetor, incorporação, papel da faixa (§7, §9).
    `tests/test_relatorio_tese.py` trava cada grupo por igualdade de conjunto
    contra as constantes de `entrega.py`; ausente, `ChaveDeInterfaceAusente`
    nomeada, nunca o código cru."""
    return t(dicionario, f"{grupo}.{codigo}")


def _valor_html(classe: str, texto: str) -> str:
    return f'<span class="{classe}">{_texto_de_dado_html(texto)}</span>'


def _atributo_html(rotulo: str, valor_html: str) -> str:
    """Uma linha "rótulo e valor" de um bloco da Tese; `valor_html` já vem
    escapado."""
    return (f'<p class="tese-atributo"><span class="tese-atributo-rotulo">{html.escape(rotulo)}</span> '
            f'{valor_html}</p>')


def _secao_html(classe: str, titulo: str, corpo: str) -> str:
    return f'<section class="{classe}"><h2>{html.escape(titulo)}</h2>{corpo}</section>'


def _lista_html(itens: list, dicionario: dict) -> str:
    """Os itens de um bloco da Tese — ou, sem nenhum, a frase do dicionário: a §9
    não fixa quantidade, e uma lista vazia também é declaração do analista."""
    if not itens:
        return f'<p class="tese-nenhum">{html.escape(t(dicionario, "tese.nenhum_item"))}</p>'
    return f'<ul class="tese-lista">{"".join(itens)}</ul>'


def _rotulos_do_valuation_html(itens: list, catalogo: dict, rotas: list, idioma: str) -> str:
    """O vínculo de uma pergunta, ou o mecanismo de um Positive/Negative (D2):
    cada item pelo rótulo do catálogo, da rota que o contém (5F, D13)."""
    return " ".join(_valor_html("tese-rotulo", _rotulo_do_vinculo(catalogo, rotas, item, idioma))
                    for item in itens)


def _fronteira_html(fronteira: dict, catalogo: dict, idioma: str, dicionario: dict, prosa: dict) -> str:
    """D3 (§14): sob fronteira de escopo a Conclusão é condicional e sem
    preço-alvo — a classe rotulada pelo catálogo, a arquitetura dominante e a
    razão, como a integração as publicou em `resultados.fronteira_de_escopo`
    (nunca lidas do `caso` cru, a lição do B2).

    Onda de correção da revisão final (F3): a arquitetura e a razão saem da lista
    de prosa (`_prosa`), resolvidas, com o QC de placeholder e a linha no log da
    Evidência. Saíam por `_campo_de_contrato`, e "a concessão vence em 2031"
    chegava à Conclusão sem proveniência."""
    onde = "resultados.fronteira_de_escopo"
    classe = _rotulo_fronteira(catalogo, _campo_de_contrato(fronteira, "classe", onde), idioma)
    arquitetura = _prosa(prosa, f"{onde}.arquitetura_dominante")
    razao = _prosa(prosa, f"{onde}.razao")
    return (
        '<div class="tese-fronteira">'
        + _atributo_html(t(dicionario, "tese.fronteira_classe"), _valor_html("tese-fronteira-classe", classe))
        + _atributo_html(t(dicionario, "tese.fronteira_arquitetura"),
                         _valor_html("tese-fronteira-arquitetura", arquitetura))
        + _atributo_html(t(dicionario, "tese.fronteira_razao"), _valor_html("tese-fronteira-razao", razao))
        + '</div>'
    )


def _manchete_vem_do_sotp(resultados: dict) -> bool:
    """`resultados.manchete.fonte` (contrato `resultados/1`): `True` quando a manchete
    é o preço da soma das partes, `False` quando é o de um cenário. Uma leitura só para
    as duas seções da Tese que mostram o cenário consolidado e precisam dizê-lo num caso
    SOTP — a faixa (achado 5 da Task 3) e as premissas decisivas (F4 da revisão final).
    Fonte fora do vocabulário é recusa nomeada: o relatório não rotula ao acaso um
    cenário cuja relação com a manchete ele não conhece."""
    fonte = _campo_de_contrato(_campo_de_contrato(resultados, "manchete", "resultados"),
                               "fonte", "resultados.manchete")
    if fonte == FONTE_DA_MANCHETE_CENARIOS:
        return False
    if fonte == FONTE_DA_MANCHETE_SOTP:
        return True
    raise CampoDeContratoAusente(
        f"'resultados.manchete.fonte' fora do vocabulário que a Tese sabe rotular: {fonte!r} "
        f"(conhecidos: '{FONTE_DA_MANCHETE_CENARIOS}', '{FONTE_DA_MANCHETE_SOTP}') — o relatório "
        "não rotula ao acaso um cenário cuja relação com a manchete ele não conhece."
    )


def _faixa_html(faixa: dict, resultados: dict, idioma: str, moeda: str | None, dicionario: dict) -> str:
    """D1/D7: as três pontas da faixa, cada uma com o preço que
    `resultados.cenarios.<nome>.valor.preco_acao` publica para o cenário que o
    analista nomeou — o QC já conferiu a ordem (`faixa_fora_de_ordem`).

    Achado 5: num caso SOTP a manchete é o preço da soma das partes, e a base da
    faixa é o cenário consolidado — dois preços "base" na mesma página. A faixa
    sai rotulada como a do consolidado, nomeando o preço da manchete. Se o SOTP
    deveria ter faixa própria é pergunta de metodologia, não deste módulo."""
    manchete = _campo_de_contrato(resultados, "manchete", "resultados")
    if _manchete_vem_do_sotp(resultados):
        preco_da_manchete = _campo_de_contrato(manchete, "preco_acao", "resultados.manchete")
        rotulo = t(dicionario, "tese.faixa_rotulo_consolidado",
                   preco=placeholders.formatar(preco_da_manchete, "moeda", idioma, moeda))
    else:
        rotulo = t(dicionario, "tese.faixa_rotulo")

    cenarios = _campo_de_contrato(resultados, "cenarios", "resultados")
    metricas = []
    for papel in contrato_entrega.PAPEIS_DA_FAIXA:
        nome = faixa[papel]
        valor = _campo_de_contrato(_campo_de_contrato(cenarios, nome, "resultados.cenarios"),
                                   "valor", f"resultados.cenarios.{nome}")
        preco = _campo_de_contrato(valor, "preco_acao", f"resultados.cenarios.{nome}.valor")
        metricas.append(
            '<div class="metrica">'
            + _valor_html("metrica-rotulo", _rotulo_de_vocabulario(dicionario, "tese.papeis_da_faixa", papel))
            + _valor_html("metrica-valor", placeholders.formatar(preco, "moeda", idioma, moeda))
            + _valor_html("metrica-nota", t(dicionario, "tese.faixa_cenario", cenario=nome))
            + '</div>'
        )
    return (f'<div class="tese-faixa"><p class="tese-faixa-rotulo">{_texto_de_dado_html(rotulo)}</p>'
            f'{"".join(metricas)}</div>')


def _veredicto_html(caso: dict, idioma: str, moeda: str | None, dicionario: dict, prosa: dict) -> str:
    """D1: o veredicto do analista, resolvido, com o preço de tela ao lado — o
    valor, a data e a fonte de `caso.preco`, que o gate exige e o analista nunca
    reescreve."""
    preco = _campo_de_contrato(caso, "preco", "caso")
    tela = t(dicionario, "tese.preco_de_tela",
             preco=placeholders.formatar(_campo_de_contrato(preco, "valor", "caso.preco"), "moeda", idioma, moeda),
             data=str(_campo_de_contrato(preco, "data", "caso.preco")),
             fonte=str(_campo_de_contrato(preco, "fonte", "caso.preco")))
    return (
        '<div class="tese-veredicto">'
        f'<h3>{html.escape(t(dicionario, "tese.veredicto_titulo"))}</h3>'
        f'<p class="tese-veredicto-texto">{_texto_de_dado_html(_prosa(prosa, "analise.veredicto.texto"))}</p>'
        f'<p class="tese-preco-de-tela">{_texto_de_dado_html(tela)}</p>'
        '</div>'
    )


def _conclusao_html(entrega: dict, catalogo: dict, idioma: str, dicionario: dict, prosa: dict) -> str:
    """A Conclusão (D7). Sob fronteira de escopo (D3) o título é o condicional,
    sem preço-alvo, com a classe, a arquitetura dominante e a razão — e a faixa
    não é desenhada: o contrato já a proíbe, e este módulo não a desenharia nem
    se ela chegasse.

    Fatia 5E, Task 3 (D4): depois do veredicto e dos múltiplos — a ordem da §9 —,
    o consenso como referência externa (`_consenso_html`), também sob fronteira."""
    caso, resultados, analise = entrega["caso"], entrega["resultados"], entrega["analise"]
    moeda = caso.get("moeda")
    fronteira = _campo_de_contrato(resultados, "fronteira_de_escopo", "resultados")
    if fronteira is None:
        titulo = t(dicionario, "tese.conclusao_titulo")
        bloco_fronteira = ""
        faixa = analise.get("faixa")
        bloco_faixa = _faixa_html(faixa, resultados, idioma, moeda, dicionario) if isinstance(faixa, dict) else ""
    else:
        titulo = t(dicionario, "tese.conclusao_condicional_titulo")
        bloco_fronteira = _fronteira_html(fronteira, catalogo, idioma, dicionario, prosa)
        bloco_faixa = ""
    return (
        '<section class="conclusao">'
        f'<h2>{html.escape(titulo)}</h2>'
        f'{bloco_fronteira}'
        f'<p class="conclusao-texto">{_texto_de_dado_html(_prosa(prosa, "analise.conclusao.texto"))}</p>'
        f'{bloco_faixa}'
        f'{_veredicto_html(caso, idioma, moeda, dicionario, prosa)}'
        f'<div class="tese-multiplos">'
        f'{_multiplos_html(resultados, catalogo, idioma, dicionario, omitir_conclusao_de_valor=True)}</div>'
        f'{_consenso_html(entrega, idioma, dicionario)}'
        '</section>'
    )


def _consenso_html(entrega: dict, idioma: str, dicionario: dict) -> str:
    """D4 (§9: "consenso como referência externa"; §6.3): sob o título do dicionário, uma
    linha por registro que `analise.consenso.registros` cita, na ordem citada — claim e
    período, valor e unidade, fonte e data de acesso. São campos estruturados do registro,
    nunca prosa, e o valor sai só localizado (`FORMATO_DO_VALOR_DO_LEDGER`). Com `ausente`,
    nada: o aviso `consenso_indisponivel` já está entre os avisos obrigatórios. Sob fronteira
    de escopo, igual — é leitura de mercado, como o múltiplo de tela (§14)."""
    citados = (entrega["analise"].get("consenso") or {}).get("registros")
    if not citados:
        return ""
    por_id = {registro["id"]: registro for registro in entrega["ledger"]["registros"]}
    linhas = []
    for posicao, ident in enumerate(citados):
        registro = por_id.get(ident)
        if registro is None:
            raise CampoDeContratoAusente(
                f"'analise.consenso.registros.{posicao}' cita '{ident}', que não é registro do ledger — o QC o "
                "recusa antes (referencia_fora_do_ledger), e a Conclusão nunca mostra um consenso sem a fonte.")
        linha = t(dicionario, "tese.consenso_linha", claim=registro["claim"], periodo=registro["periodo"],
                  valor=_valor_do_registro(registro, idioma, dicionario), unidade=registro["unidade"],
                  fonte=registro["fonte"]["identidade"], data=registro["data_acesso"])
        linhas.append(f"<li>{_texto_de_dado_html(linha)}</li>")
    return (f'<div class="tese-consenso"><h3>{html.escape(t(dicionario, "tese.consenso_titulo"))}</h3>'
            f'<ul>{"".join(linhas)}</ul></div>')


# Fatia 5E, Task 3: os parâmetros de um aviso da Tese que são código de um vocabulário do
# contrato do ledger, com o vocabulário que os rotula. Na Tese sai o rótulo do dicionário; no
# `qc.json`, o artefato interno, a chave. Hoje só a âncora do consenso indisponível, que a
# mensagem imprimia crua (a lição do B2).
VOCABULARIO_DOS_PARAMETROS_DOS_AVISOS: dict = {"consenso_indisponivel": {"ancora": "ancoras_do_consenso"}}


def _mensagem_do_aviso(achado, dicionario: dict, prosa: dict) -> str:
    """A mensagem de um aviso como a Tese a exibe (fatia 5E, Task 3), sobre os `params` do
    achado:
    - cada parâmetro que `params.campos_de_prosa` nomeia vira o texto que a lista de prosa
      resolveu (`_prosa`) — o placeholder resolvido, nunca o texto cru. Um `onde` fora da
      lista é `ProsaNaoAuditada`;
    - cada parâmetro de vocabulário (`VOCABULARIO_DOS_PARAMETROS_DOS_AVISOS`) vira o rótulo.

    O `qc.json` continua com o texto cru e a chave: `builder._montar_qc_json` formata os
    `params` como o QC os publicou."""
    params = dict(achado.params)
    for parametro, onde in (params.pop("campos_de_prosa", None) or {}).items():
        params[parametro] = _prosa(prosa, onde)
    for parametro, vocabulario in VOCABULARIO_DOS_PARAMETROS_DOS_AVISOS.get(achado.codigo, {}).items():
        params[parametro] = _rotulo_da_evidencia(dicionario, vocabulario, params[parametro])
    return _mensagem_qc(achado._replace(params=params), dicionario)


def _disclosures_html(achados: list, dicionario: dict, prosa: dict) -> str:
    """Todo achado REQUIRED_DISCLOSURE, visível, com a mensagem do dicionário — a
    de uma limitação da reversa carrega o rótulo do catálogo que o QC pôs nos
    params. Fatia 5E, Task 3: a mensagem sai por `_mensagem_do_aviso`, com a prosa
    que o aviso cita resolvida e o vocabulário do ledger rotulado."""
    disclosures = [a for a in achados if a.nivel == "REQUIRED_DISCLOSURE"]
    titulo = html.escape(t(dicionario, "tese.disclosures_titulo"))
    if disclosures:
        itens = "".join(f"<li>{_texto_de_dado_html(_mensagem_do_aviso(a, dicionario, prosa))}</li>" for a in disclosures)
        return f'<section class="disclosures"><h2>{titulo}</h2><ul>{itens}</ul></section>'
    vazio = html.escape(t(dicionario, "tese.disclosures_vazio"))
    return f'<section class="disclosures disclosures-vazio"><h2>{titulo}</h2><p>{vazio}</p></section>'


def _parte_do_sotp(resultados: dict, nome: str) -> tuple[int, dict]:
    """O índice e a parte de `resultados.sotp.partes` cujo `nome` é `nome` (fatia 5F,
    Task 5, D13). O QC já recusa a parte que não existe (`premissa_decisiva_fora_do_
    cenario`, HARD FAIL); aqui, recusa nomeada — nunca uma premissa mostrada com o
    número de outro lugar."""
    sotp = resultados.get("sotp")
    partes = sotp.get("partes") if isinstance(sotp, dict) else None
    for indice, parte in enumerate(partes or []):
        if isinstance(parte, dict) and parte.get("nome") == nome:
            return indice, parte
    raise CampoDeContratoAusente(
        f"'resultados.sotp.partes' não tem a parte '{nome}' que uma premissa decisiva nomeia — o QC a "
        "recusa antes (premissa_decisiva_fora_do_cenario), e a Tese nunca mostra o número de outro lugar.")


def _premissas_decisivas_html(analise: dict, resultados: dict, catalogo: dict, idioma: str,
                               moeda: str | None, dicionario: dict, prosa: dict) -> str:
    """D1: cada premissa decisiva com o rótulo do catálogo, o número do cenário da
    manchete (`resultados.manchete.cenario`, presente também sob fronteira e num
    caso SOTP) formatado pela unidade do catálogo — pela mesma leitura do valor
    original do laboratório, `_valor_exibido_da_premissa` — e a derivação.

    Onda de correção da revisão final (F4): num caso SOTP o cenário da manchete é
    o consolidado, e a manchete é o preço das partes — que usam premissas
    próprias. A seção sai com o rótulo do consolidado, do dicionário, nomeando o
    cenário e sem número nenhum (ela aparece também sob fronteira de escopo).

    Fatia 5F, Task 5 (D13): uma premissa com `parte` é a daquela parte de SOTP — o
    rótulo da rota dela, o número que a parte publica em `resultados.sotp.partes` e,
    sob ele, a parte pelo número e pelo nome. O montante sai com a escala declarada
    quando a unidade a declara (D7)."""
    rota = _campo_de_contrato(resultados, "rota", "resultados")
    nome = _campo_de_contrato(_campo_de_contrato(resultados, "manchete", "resultados"),
                              "cenario", "resultados.manchete")
    cenario = _campo_de_contrato(_campo_de_contrato(resultados, "cenarios", "resultados"),
                                 nome, "resultados.cenarios")
    premissas = _campo_de_contrato(cenario, "premissas", f"resultados.cenarios.{nome}")
    escala = resultados.get("escala_monetaria")
    itens = []
    for indice, declarada in enumerate(analise["premissas_decisivas"]):
        chave = declarada["chave"]
        rota_da_premissa, premissas_da_premissa = rota, premissas
        onde, nota_da_parte = f"resultados.cenarios.{nome}.premissas", ""
        if "parte" in declarada:
            indice_da_parte, parte = _parte_do_sotp(resultados, declarada["parte"])
            onde_da_parte = f"resultados.sotp.partes.{indice_da_parte}"
            rota_da_premissa = _campo_de_contrato(parte, "rota", onde_da_parte)
            premissas_da_premissa = _campo_de_contrato(parte, "premissas", onde_da_parte)
            onde = f"{onde_da_parte}.premissas"
            nota_da_parte = '<p class="tese-premissa-parte">' + _texto_de_dado_html(t(
                dicionario, "tese.premissa_da_parte", nome=declarada["parte"],
                numero=placeholders.formatar(indice_da_parte + 1, "num0", idioma))) + '</p>'
        rotulo = _rotulo_premissa(catalogo, rota_da_premissa, chave, idioma)
        valor = _valor_exibido_da_premissa(
            catalogo["premissas"][rota_da_premissa][chave],
            _campo_de_contrato(premissas_da_premissa, chave, onde),
            catalogo, idioma, moeda, dicionario, escala)
        derivacao = _prosa(prosa, f"analise.premissas_decisivas.{indice}.derivacao")
        itens.append(
            '<li class="tese-premissa"><div class="metrica">'
            + _valor_html("metrica-rotulo", rotulo)
            + _valor_html("metrica-valor", valor)
            + f'</div>{nota_da_parte}<p class="tese-derivacao">{_texto_de_dado_html(derivacao)}</p></li>'
        )
    rotulo_do_consolidado = ""
    if _manchete_vem_do_sotp(resultados):
        rotulo_do_consolidado = (
            '<p class="tese-premissas-rotulo">'
            f'{_texto_de_dado_html(t(dicionario, "tese.premissas_decisivas_rotulo_consolidado", cenario=nome))}</p>')
    return _secao_html("tese-premissas-decisivas", t(dicionario, "tese.premissas_decisivas_titulo"),
                       rotulo_do_consolidado + _lista_html(itens, dicionario))


def _o_que_mudou_html(analise: dict, dicionario: dict, prosa: dict) -> str:
    """§9: o que mudou desde a análise fornecida — só quando declarado."""
    mudou = analise.get("mudou_desde_analise_fornecida")
    if not isinstance(mudou, dict):
        return ""
    linhas = []
    for indice in range(len(mudou["linhas"])):
        linha = _prosa(prosa, f"analise.mudou_desde_analise_fornecida.linhas.{indice}")
        linhas.append(f"<li>{_texto_de_dado_html(linha)}</li>")
    return _secao_html("tese-o-que-mudou", t(dicionario, "tese.o_que_mudou_titulo"), f'<ul>{"".join(linhas)}</ul>')


def _item_do_valuation_html(lado: str, indice: int, item: dict, catalogo: dict, rotas: list, idioma: str,
                             dicionario: dict, prosa: dict) -> str:
    """Um Positive ou Negative (§9): a afirmação, o vetor que atinge, o mecanismo
    do valuation que move, o observável que o confirma ou o mata, e se ele está
    refletido no valuation ou declarado como não incorporado — com a razão."""
    onde = f"analise.{lado}.{indice}"
    linhas = [
        f'<p class="tese-afirmacao">{_texto_de_dado_html(_prosa(prosa, onde + ".afirmacao"))}</p>',
        _atributo_html(t(dicionario, "tese.vetor"),
                       _valor_html("tese-vetor", _rotulo_de_vocabulario(dicionario, "tese.vetores", item["vetor"]))),
        _atributo_html(t(dicionario, "tese.mecanismo"),
                       _rotulos_do_valuation_html(item["mecanismo"], catalogo, rotas, idioma)),
        _atributo_html(t(dicionario, "tese.observavel_item"),
                       _valor_html("tese-observavel", _prosa(prosa, onde + ".observavel"))),
        _atributo_html(t(dicionario, "tese.incorporacao"),
                       _valor_html("tese-incorporacao",
                                   _rotulo_de_vocabulario(dicionario, "tese.incorporacoes", item["incorporacao"]))),
    ]
    if "razao" in item:
        linhas.append(_atributo_html(t(dicionario, "tese.razao"),
                                     _valor_html("tese-razao", _prosa(prosa, onde + ".razao"))))
    return f'<li class="tese-item">{"".join(linhas)}</li>'


def _positives_negatives_html(analise: dict, catalogo: dict, rotas: list, idioma: str, dicionario: dict,
                               prosa: dict) -> str:
    lados = []
    for lado, titulo in (("positives", t(dicionario, "tese.positives_titulo")),
                         ("negatives", t(dicionario, "tese.negatives_titulo"))):
        itens = [_item_do_valuation_html(lado, indice, item, catalogo, rotas, idioma, dicionario, prosa)
                 for indice, item in enumerate(analise[lado])]
        lados.append(f'<div class="tese-lado"><h3>{html.escape(titulo)}</h3>{_lista_html(itens, dicionario)}</div>')
    return _secao_html("tese-positives-negatives", t(dicionario, "tese.positives_negatives_titulo"),
                       f'<div class="tese-lados">{"".join(lados)}</div>')


def _pergunta_html(indice: int, pergunta: dict, catalogo: dict, rotas: list, idioma: str, dicionario: dict,
                    prosa: dict, exhibits_resolvidos: list, indice_por_id: dict) -> str:
    """Uma pergunta da tese (§7, §10): o tema, a pergunta, a evidência, o
    observável que a falsificaria, o vínculo com o valuation e — D5 — os exhibits
    que ela cita, na ordem em que os cita, ou a razão de nenhum acrescentar."""
    onde = f"analise.perguntas.{indice}"
    tema = _rotulo_de_vocabulario(dicionario, "tese.temas", pergunta["tema"])
    linhas = [
        f'<p class="tese-tema">{html.escape(tema)}</p>',
        f'<h3>{_texto_de_dado_html(_prosa(prosa, onde + ".pergunta"))}</h3>',
        _atributo_html(t(dicionario, "tese.evidencia"),
                       _valor_html("tese-evidencia", _prosa(prosa, onde + ".evidencia"))),
        _atributo_html(t(dicionario, "tese.observavel_pergunta"),
                       _valor_html("tese-observavel", _prosa(prosa, onde + ".observavel"))),
        _atributo_html(t(dicionario, "tese.vinculo"),
                       _rotulos_do_valuation_html(pergunta["vinculo"], catalogo, rotas, idioma)),
    ]
    if "exhibits" in pergunta:
        artigos = []
        for posicao, exhibit_id in enumerate(pergunta["exhibits"]):
            if exhibit_id not in indice_por_id:
                raise CampoDeContratoAusente(
                    f"'{onde}.exhibits.{posicao}' cita o exhibit '{exhibit_id}', que não está entre os "
                    "exhibits resolvidos que o builder passou ao relatório — nenhum gráfico sai sem a sua spec."
                )
            indice_do_exhibit = indice_por_id[exhibit_id]
            artigos.append(_exhibit_html(exhibits_resolvidos[indice_do_exhibit], indice_do_exhibit, prosa, "h4"))
        linhas.append(f'<div class="tese-pergunta-exhibits">{"".join(artigos)}</div>')
    else:
        linhas.append(_atributo_html(t(dicionario, "tese.sem_exhibit"),
                                     _valor_html("tese-sem-exhibit", _prosa(prosa, onde + ".sem_exhibit.razao"))))
    return f'<article class="tese-pergunta">{"".join(linhas)}</article>'


def _riscos_html(analise: dict, dicionario: dict, prosa: dict) -> str:
    """§9: cada risco com o observável que o monitoraria."""
    itens = []
    for indice in range(len(analise["riscos"])):
        onde = f"analise.riscos.{indice}"
        itens.append(
            f'<li class="tese-item"><p class="tese-risco">{_texto_de_dado_html(_prosa(prosa, onde + ".risco"))}</p>'
            + _atributo_html(t(dicionario, "tese.observavel_risco"),
                             _valor_html("tese-observavel", _prosa(prosa, onde + ".observavel")))
            + '</li>'
        )
    return _secao_html("tese-riscos", t(dicionario, "tese.riscos_titulo"), _lista_html(itens, dicionario))


def _visao_nao_consensual_html(analise: dict, dicionario: dict, prosa: dict) -> str:
    """§9: a visão não-consensual — só quando declarada."""
    if not isinstance(analise.get("visao_nao_consensual"), dict):
        return ""
    texto = _prosa(prosa, "analise.visao_nao_consensual.texto")
    return _secao_html("tese-visao-nao-consensual", t(dicionario, "tese.visao_nao_consensual_titulo"),
                       f"<p>{_texto_de_dado_html(texto)}</p>")


def _tese_html(entrega: dict, catalogo: dict, achados: list, idioma: str, dicionario: dict, titulo: str,
               prosa: dict, exhibits_resolvidos: list) -> str:
    """A aba inteira, na ordem de D7. `exhibits_resolvidos` é a lista que o
    builder resolveu uma vez: cada exhibit é desenhado sob as perguntas que o
    citam, pelo índice do seu id nessa lista — o mesmo índice da sua spec no
    payload —, e o que nenhuma pergunta cita vai para a seção final."""
    analise, resultados = entrega["analise"], entrega["resultados"]
    # A rota do caso é contrato (ausente, recusa nomeada); o vínculo lê também as rotas das partes (5F, D13).
    _campo_de_contrato(resultados, "rota", "resultados")
    rotas = _rotas_do_valuation(resultados)
    moeda = entrega["caso"].get("moeda")
    indice_por_id = {exhibit["id"]: indice for indice, exhibit in enumerate(exhibits_resolvidos)}
    citados = {indice_por_id[exhibit_id] for pergunta in analise["perguntas"]
               for exhibit_id in pergunta.get("exhibits", []) if exhibit_id in indice_por_id}
    perguntas = "".join(
        _pergunta_html(indice, pergunta, catalogo, rotas, idioma, dicionario, prosa, exhibits_resolvidos,
                       indice_por_id)
        for indice, pergunta in enumerate(analise["perguntas"]))
    return (
        f'<h1>{titulo}</h1>'
        + _conclusao_html(entrega, catalogo, idioma, dicionario, prosa)
        + _disclosures_html(achados, dicionario, prosa)
        + _premissas_decisivas_html(analise, resultados, catalogo, idioma, moeda, dicionario, prosa)
        + _o_que_mudou_html(analise, dicionario, prosa)
        + _positives_negatives_html(analise, catalogo, rotas, idioma, dicionario, prosa)
        + _secao_html("tese-perguntas", t(dicionario, "tese.perguntas_titulo"), perguntas)
        + _riscos_html(analise, dicionario, prosa)
        + _visao_nao_consensual_html(analise, dicionario, prosa)
        + _exhibits_nao_citados_html(exhibits_resolvidos, citados, prosa, dicionario)
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
        # Fatia 5F, Task 5 (D7): a receita da unidade dos montantes da ponte, com o sufixo da escala
        # quando o caso a declara e o catálogo marca a unidade.
        "formato": _espec_de_formato_com_escala(catalogo, UNIDADE_DOS_MONTANTES_DA_PONTE, idioma, moeda,
                                                resultados.get("escala_monetaria")),
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


# Fatia 5F, Task 5 (D7): as linhas da ponte são o balanço na moeda do caso — montantes, a unidade
# `moeda` do catálogo (`resultados.ponte` não declara unidade própria; é a que a 5B já aplicava pelo
# formato). A escala entra pelo sufixo da receita que o `svg.js` recebe, só quando o catálogo marca
# essa unidade com `escala_monetaria`.
UNIDADE_DOS_MONTANTES_DA_PONTE: str = "moeda"


def _espec_de_formato_com_escala(catalogo: dict, unidade: Any, idioma: str, moeda: str | None,
                                 escala: Any) -> dict:
    """A receita de `_espec_de_formato_da_unidade` com o sufixo da escala dos montantes
    (`_sufixo_da_escala`) — vazio quando o caso não a declara ou a unidade não a marca."""
    espec = dict(_espec_de_formato_da_unidade(catalogo, unidade, idioma, moeda))
    espec["sufixo"] = espec["sufixo"] + _sufixo_da_escala(catalogo, unidade, escala, idioma)
    return espec


def _ponte_html(resultados: dict, catalogo: dict, idioma: str, dicionario: dict, moeda: str | None) -> str:
    """O host VAZIO do waterfall — só o `svg.js` o preenche (bootstrap estático em
    `template.html`) —, ou nada quando não há ponte (S6)."""
    if _ponte_para_json(resultados, catalogo, idioma, dicionario, moeda) is None:
        return ""
    titulo = html.escape(t(dicionario, "valuation.ponte_titulo"))
    return (f'<section class="painel-svg"><h2>{titulo}</h2>'
            f'<div class="painel-grafico" data-painel="ponte"></div></section>')


def _grades_1d(resultados: dict) -> list:
    sensibilidades = resultados.get("sensibilidades")
    if not isinstance(sensibilidades, dict):
        return []
    grades = sensibilidades.get("grades_1d")
    return grades if isinstance(grades, list) else []


def _numero_exibivel(valor: Any) -> bool:
    return isinstance(valor, (int, float)) and not isinstance(valor, bool)


def _unidade_publicada(catalogo: dict, caminho: str) -> str:
    """A unidade que a integração declara para o número que a página exibe em `caminho`: a família
    do mapa `catalogo.conclusoes_de_valor` que o cobre (fatia 5F, Task 5) — a mesma declaração que
    decide a leitura condicional. Um número de valor fora do mapa é recusa nomeada: o relatório não
    formata ao acaso um número cuja unidade ninguém declarou."""
    mapa = placeholders.conclusoes_de_valor(catalogo)
    familia = placeholders.conclusao_de_valor(caminho, mapa) if mapa is not None else None
    if familia is None:
        raise RotuloDoCatalogoAusente(
            f"catálogo de apresentação sem a unidade de '{caminho}' no mapa 'conclusoes_de_valor' — o "
            "relatório não formata um número de valor cuja unidade a integração não declara.")
    return familia[0]


def _grade_1d_html(caso: dict, resultados: dict, grade: dict, catalogo: dict, idioma: str, dicionario: dict,
                   moeda: str | None) -> str:
    """D10: uma grade 1D como tabela estática, sem JS (§10: "cinco números numa tabela podem
    comunicar melhor que um gráfico") — o ponto pela unidade da premissa, o preço pela unidade que a
    grade publica e o múltiplo pela do mapa —, com o ponto do cenário que a grade perturbou marcado
    por igualdade exata, a regra da matriz (`_base_da_grade`). Sob fronteira de escopo, o título e as
    colunas dos números de valor saem com o rótulo condicional."""
    rota = _campo_de_contrato(resultados, "rota", "resultados")
    onde = "resultados.sensibilidades.grades_1d[*]"
    premissa = _campo_de_contrato(grade, "premissa", onde)
    cenario = _cenario_da_grade(caso)
    central = (((caso.get("cenarios") or {}).get(cenario) or {}).get("premissas") or {}).get(premissa)
    escala = resultados.get("escala_monetaria")
    unidade_do_ponto = _unidade_da_premissa(catalogo, rota, premissa)
    unidade_do_multiplo = _unidade_publicada(catalogo, CAMINHO_DOS_MULTIPLOS_DA_GRADE_1D)
    rotulo = _rotulo_premissa(catalogo, rota, premissa, idioma)
    colunas = [
        rotulo,
        _rotulo_do_numero(resultados, catalogo, dicionario, "grade_1d_coluna_preco", CAMINHO_DOS_PRECOS_DA_GRADE_1D),
        _rotulo_do_numero(resultados, catalogo, dicionario, "grade_1d_coluna_multiplo",
                          CAMINHO_DOS_MULTIPLOS_DA_GRADE_1D),
    ]
    linhas = []
    for ponto in _campo_de_contrato(grade, "pontos", onde):
        x = _campo_de_contrato(ponto, "x", f"{onde}.pontos[*]")
        texto_do_ponto = _formatar_na_unidade(x, catalogo, unidade_do_ponto, idioma, moeda, escala)
        if _numero_exibivel(central) and _numero_exibivel(x) and x == central:
            texto_do_ponto = t(dicionario, "valuation.grade_1d_ponto_do_cenario", valor=texto_do_ponto,
                               cenario=cenario)
        celulas = [
            texto_do_ponto,
            _formatar_na_unidade(_campo_de_contrato(ponto, "valor", f"{onde}.pontos[*]"), catalogo,
                                 grade.get("unidade"), idioma, moeda, escala),
            _formatar_na_unidade(_campo_de_contrato(ponto, "multiplo", f"{onde}.pontos[*]"), catalogo,
                                 unidade_do_multiplo, idioma, moeda, escala),
        ]
        linhas.append("<tr>" + "".join(f"<td>{_texto_de_dado_html(celula)}</td>" for celula in celulas) + "</tr>")
    titulo = _rotulo_do_numero(resultados, catalogo, dicionario, "grade_1d_titulo", CAMINHO_DOS_PRECOS_DA_GRADE_1D,
                               cenario=cenario, premissa=rotulo)
    cabecalho = "".join(f'<th class="grade-rotulo">{_texto_de_dado_html(coluna)}</th>' for coluna in colunas)
    return (f'<section class="sensibilidade-1d"><h2>{_texto_de_dado_html(titulo)}</h2>'
            f'<table class="grade-1d"><thead><tr>{cabecalho}</tr></thead>'
            f'<tbody>{"".join(linhas)}</tbody></table></section>')


def _sensibilidades_html(caso: dict, resultados: dict, catalogo: dict, idioma: str, dicionario: dict) -> str:
    """As sensibilidades, na ordem publicada: uma tabela por grade 1D (D10, `_grade_1d_html`) e,
    depois, o host VAZIO de cada matriz 2D, com o `data-painel-indice` pelo qual o bootstrap a pareia
    à sua spec (achado 14) — só o `svg.js` o preenche. Nenhuma seção sem grade (S6)."""
    rota = _campo_de_contrato(resultados, "rota", "resultados")
    moeda = caso.get("moeda")
    blocos = [_grade_1d_html(caso, resultados, grade, catalogo, idioma, dicionario, moeda)
              for grade in _grades_1d(resultados)]
    for indice, grade in enumerate(_grades_2d(resultados)):
        titulo = _texto_de_dado_html(_rotulo_do_numero(
            resultados, catalogo, dicionario, "matriz_titulo", CAMINHO_DAS_CELULAS_DA_GRADE_2D,
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


# --------------------------------------------------------------------------
# Laboratório da aba Valuation (fatia 5C, item 5, Task 2).
#
# O painel é INTERFACE sobre dados já embutidos: um campo por premissa do
# cenário, agrupado pelos quatro blocos econômicos do catálogo (L5), com o
# valor original ao lado do editado (L6), e três saídas por cenário — mais a
# lista de diagnósticos (Task 3) — que o `laboratorio.js` preenche chamando a
# FACHADA (`FachadaEspelho.avaliarCaso`).
# Nenhuma conta de valuation acontece aqui nem lá — toda a metodologia que o
# laboratório executa vive na camada de integração (E3/emenda do desenho §15),
# e é por isso que o espelho e a fachada entram na página por LEITURA de
# `builder.ASSETS_DA_INTEGRACAO`, nunca por cópia.
#
# Três decisões que este módulo materializa:
# - O painel é HTML ESTÁTICO. `laboratorio.js` não constrói campo nenhum: lê
#   `[data-laboratorio-entrada]`, chama a fachada e escreve as saídas. Quem
#   sabe que premissa vai em que bloco, com que rótulo, unidade e widget, é o
#   catálogo — lido aqui, no build.
# - Premissa que o catálogo não conheça (ou cujo valor não caiba no tipo de
#   entrada declarado) é EXIBIDA, DESABILITADA e rotulada como tal (L5): o
#   laboratório nunca inventa unidade nem widget. Ela continua valendo no
#   cálculo, porque o `caso` embutido é a base de toda simulação e só os
#   campos editáveis o sobrescrevem.
# - O que não é vivo nesta fatia (SOTP, reversa, sensibilidades) ganha o
#   rótulo "congelado nas premissas originais" (L3) — e, num caso com SOTP, o
#   rótulo cobre também o PREÇO DA MANCHETE, que é o do SOTP e não o do
#   cenário que o laboratório recalcula.
# --------------------------------------------------------------------------

def _blocos_do_catalogo(catalogo: dict, idioma: str) -> list:
    """Os blocos econômicos na ORDEM que o catálogo declara (`blocos.<chave>.
    ordem`) — nunca a ordem de iteração do dict, que é dado de arquivo, e
    nunca uma ordem decorada aqui. Desempate pela chave, para que dois blocos
    com a mesma `ordem` ainda produzam um HTML determinístico."""
    blocos = catalogo.get("blocos") or {}
    ordenados = sorted(blocos.items(), key=lambda par: (par[1].get("ordem", 0), par[0]))
    # Fatia 5D, Task 3: o rótulo sai de `_rotulo_bloco`, o mesmo auxiliar do
    # vínculo da Tese — duas leituras do mesmo rótulo divergiriam.
    return [(chave, _rotulo_bloco(catalogo, chave, idioma)) for chave, _info in ordenados]


def _premissas_da_rota(catalogo: dict, rota: str) -> dict | None:
    """`catalogo.premissas.<rota>` — o vocabulário editável daquela rota, ou
    `None` quando o catálogo não conhece a rota. Nesse caso não há
    laboratório nenhum (e nenhum campo inventado): a página segue sem o
    painel, com o cabeçalho estático que a 5A já publica."""
    premissas = (catalogo.get("premissas") or {}).get(rota)
    return premissas if isinstance(premissas, dict) else None


def _sufixo_da_escala(catalogo: dict, unidade: Any, escala: Any, idioma: str) -> str:
    """O sufixo da escala dos montantes (fatia 5F, Task 5, D7): `" <rótulo>"` quando o caso
    declara a escala (`resultados.escala_monetaria`) e o catálogo marca a unidade com
    `escala_monetaria` — hoje só `moeda`, nunca preço por ação —; senão, vazio. Decide a
    flag da unidade, nunca o nome dela; o rótulo é do catálogo (`escalas_monetarias`)."""
    info = (catalogo.get("unidades") or {}).get(unidade)
    if escala is None or not (isinstance(info, dict) and info.get("escala_monetaria") is True):
        return ""
    rotulo = (((catalogo.get("escalas_monetarias") or {}).get(escala) or {}).get("rotulo") or {}).get(idioma)
    if not rotulo:
        raise RotuloDoCatalogoAusente(
            f"catálogo de apresentação sem rótulo em '{idioma}' para a escala monetária '{escala}' em "
            "'escalas_monetarias'.")
    return f" {rotulo}"


def _formatar_na_unidade(valor: Any, catalogo: dict, unidade: Any, idioma: str, moeda: str | None,
                         escala: Any = None) -> str:
    """Um número pela unidade que o contrato declara (`_formato_da_unidade`), com o sufixo da
    escala quando a unidade a declara (`_sufixo_da_escala`)."""
    return (placeholders.formatar(valor, _formato_da_unidade(catalogo, unidade), idioma, moeda)
            + _sufixo_da_escala(catalogo, unidade, escala, idioma))


def _valor_exibido_da_premissa(info: dict, valor: Any, catalogo: dict, idioma: str,
                                moeda: str | None, dicionario: dict, escala: Any = None) -> str:
    """O valor ORIGINAL, legível, que fica ao lado do campo editável (L6).
    Número passa pela unidade que o catálogo declara (a mesma disciplina de
    `_espec_de_formato_da_unidade`/A4 — nunca "2 casas e nada mais"), com a escala dos
    montantes quando a unidade a declara (5F, D7); opção de escolha vira o rótulo da
    opção; booleano vira sim/não do dicionário."""
    entrada = info.get("entrada")
    if entrada == "escolha":
        # Fatia 5D, Task 3: a premissa decisiva da Tese também passa por aqui, e
        # `resultados.cenarios.<nome>.premissas` repete o valor como o caso o
        # declarou — um alias legado ('spread') não tem rótulo no catálogo. A
        # frase do dicionário diz isso; o código cru nunca chega à tela.
        rotulo = ((info.get("rotulos_opcoes") or {}).get(valor) or {}).get(idioma)
        return rotulo if rotulo else t(dicionario, "valuation.laboratorio_valor_nao_rotulavel")
    if entrada == "booleano":
        return t(dicionario, "valuation.laboratorio_sim" if valor else "valuation.laboratorio_nao")
    return _formatar_na_unidade(valor, catalogo, info.get("unidade"), idioma, moeda, escala)


def _widget_editavel(info: dict, valor: Any, identificador: str, idioma: str) -> str | None:
    """O campo de entrada de uma premissa CATALOGADA, ou `None` quando o valor
    declarado não cabe no tipo de entrada que o catálogo anuncia — caso em que
    o chamador cai no campo desabilitado, em vez de desenhar um widget que
    mentiria sobre o dado (um `<input type=number>` com texto dentro, por
    exemplo).

    `type="number"` guarda o valor em notação com PONTO decimal
    independentemente do idioma da página (é a regra do próprio HTML para o
    `.value` desse tipo) — então o JSON do caso vai para o atributo como
    está, e volta do campo do mesmo jeito, sem nenhuma conversão de locale no
    caminho."""
    entrada = info.get("entrada")
    atributos = f'id="{identificador}" data-laboratorio-entrada="{entrada}"'
    if entrada == "numero":
        if isinstance(valor, bool) or not isinstance(valor, (int, float)):
            return None
        literal = html.escape(json.dumps(valor))
        return (f'<input {atributos} type="number" step="any" value="{literal}" '
                f'data-laboratorio-original="{literal}">')
    if entrada == "escolha":
        opcoes = info.get("opcoes") or []
        if valor not in opcoes:
            return None
        rotulos = info.get("rotulos_opcoes") or {}
        itens = "".join(
            f'<option value="{html.escape(str(opcao))}"'
            f'{" selected" if opcao == valor else ""}>'
            f'{_texto_de_dado_html((rotulos.get(opcao) or {}).get(idioma) or str(opcao))}</option>'
            for opcao in opcoes
        )
        return (f'<select {atributos} data-laboratorio-original="{html.escape(str(valor))}">'
                f'{itens}</select>')
    if entrada == "booleano":
        if not isinstance(valor, bool):
            return None
        return (f'<input {atributos} type="checkbox"{" checked" if valor else ""} '
                f'data-laboratorio-original="{"true" if valor else "false"}">')
    return None


def _campo_do_laboratorio(rota: str, chave: str, valor: Any, info: dict | None,
                           identificador: str, catalogo: dict, idioma: str,
                           moeda: str | None, dicionario: dict, escala: Any = None) -> tuple[str, str | None]:
    """Um campo do painel, e o BLOCO econômico em que ele entra (`None` quando
    não é editável). Sem entrada no catálogo — ou com valor fora do tipo de
    entrada declarado — o campo é mostrado como o caso o declara,
    DESABILITADO e rotulado; `None` no bloco é o que manda o chamador
    agrupá-lo à parte, sem que ninguém precise reler o HTML já montado para
    descobrir o que ele virou."""
    widget = _widget_editavel(info, valor, identificador, idioma) if info else None
    if widget is None:
        # B2 (achado F2 da revisão final da 5A) estendido a este painel: um
        # valor de TEXTO é um código de vocabulário controlado, e o catálogo é
        # quem o nomeia. Quando ele não sabe nomear aquele código, o campo diz
        # isso — nunca imprime o código cru. É o caso de um alias legado
        # ('spread' por 'gordon'): o gate o aceita e canonicaliza, o cabeçalho
        # já mostra "Gordon — ...", e mostrar "spread" aqui embaixo faria a
        # mesma página dizer duas coisas diferentes sobre o mesmo input.
        # Número e booleano NÃO são código: valem como o caso os declara.
        bruto = html.escape(
            t(dicionario, "valuation.laboratorio_valor_nao_rotulavel")
            if isinstance(valor, str) else _texto_valor(valor))
        nota = html.escape(t(dicionario, "valuation.laboratorio_nao_editavel_nota"))
        rotulo = _texto_de_dado_html(
            ((info.get("rotulo") or {}).get(idioma) or chave) if info else chave)
        return (
            f'<div class="lab-campo lab-campo-travado" data-laboratorio-premissa="{html.escape(chave)}">'
            f'<label for="{identificador}">{rotulo}</label>'
            f'<input id="{identificador}" type="text" value="{bruto}" disabled>'
            f'<span class="lab-nota">{nota}</span>'
            f'</div>'
        ), None
    rotulo = html.escape(_rotulo_premissa(catalogo, rota, chave, idioma))
    original = _texto_de_dado_html(t(
        dicionario, "valuation.laboratorio_original",
        valor=_valor_exibido_da_premissa(info, valor, catalogo, idioma, moeda, dicionario, escala)))
    return (
        f'<div class="lab-campo" data-laboratorio-premissa="{html.escape(chave)}">'
        f'<label for="{identificador}">{rotulo}</label>'
        f'{widget}'
        f'<span class="lab-original">{original}</span>'
        f'</div>'
    ), info.get("bloco")


def _saidas_do_cenario_html(dicionario: dict, rotulos_das_saidas: dict) -> str:
    """As três saídas que `laboratorio.js` reescreve a cada edição: preço,
    múltiplo e upside. Nascem com o texto de "sem valor" — o JS as preenche na
    carga (reproduzindo, aí, exatamente o que o relatório publicou, que é o
    que o badge acabou de provar) e a cada mudança. Se o badge reprovar, elas
    FICAM assim: um número recalculado por um motor que discorda do relatório
    é justamente o que L4 proíbe mostrar.

    `rotulos_das_saidas` (`preco`, `multiplo`, `upside`) sai de `_laboratorio_html`
    pela mesma decisão do cabeçalho da aba (`_rotulo_do_numero`): sob fronteira de
    escopo, cada saída que o mapa da integração declara conclusão de valor é
    leitura condicional. A Task 3 trocava só o rótulo do preço, e o múltiplo justo
    e o upside continuavam com os de sempre (F1 da revisão final)."""
    vazio = html.escape(t(dicionario, "valuation.laboratorio_sem_valor"))
    campos = [("preco", True), ("multiplo", False), ("upside", True)]
    blocos = []
    for chave, sem_nota in campos:
        rotulo = rotulos_das_saidas[chave]
        nota = "" if sem_nota else f'<span class="metrica-nota" data-laboratorio-saida="{chave}-rotulo"></span>'
        blocos.append(
            f'<div class="metrica">'
            f'<span class="metrica-rotulo">{html.escape(rotulo)}</span>'
            f'<span class="metrica-valor" data-laboratorio-saida="{chave}">{vazio}</span>'
            f'{nota}'
            f'</div>'
        )
    return f'<div class="lab-saidas">{"".join(blocos)}</div>'


def _diagnosticos_do_cenario_html(dicionario: dict) -> str:
    """O lugar em que `laboratorio.js` pinta os diagnósticos do cenário (fatia
    5C, Task 3; §8.4 do desenho: o diagnóstico se move junto com o número).
    Nasce com o texto de "sem valor", pela mesma razão das três saídas: o JS o
    preenche na carga, com as chaves que a fachada recalculou (e que o badge
    acabou de provar iguais às publicadas), e a cada mudança; se o badge
    reprovar, ele FICA assim. Este módulo não escolhe diagnóstico nenhum — nem
    os da carga: quem decide que chave acende é a integração."""
    vazio = html.escape(t(dicionario, "valuation.laboratorio_sem_valor"))
    titulo = html.escape(t(dicionario, "valuation.laboratorio_diagnosticos_titulo"))
    return (
        f'<div class="lab-diagnosticos">'
        f'<h4>{titulo}</h4>'
        f'<ul data-laboratorio-diagnosticos aria-live="polite">'
        f'<li class="lab-diagnostico lab-diagnostico-vazio">{vazio}</li>'
        f'</ul>'
        f'</div>'
    )


def _cenario_do_laboratorio_html(rota: str, nome: str, premissas: dict, indice: int,
                                  premissas_catalogo: dict, catalogo: dict, idioma: str,
                                  moeda: str | None, dicionario: dict, rotulos_das_saidas: dict,
                                  escala: Any = None) -> str:
    campos_por_bloco: dict[str, list] = {}
    travados: list[str] = []
    for posicao, (chave, valor) in enumerate(premissas.items()):
        campo, bloco = _campo_do_laboratorio(
            rota, chave, valor, premissas_catalogo.get(chave), f"lab-{indice}-{posicao}",
            catalogo, idioma, moeda, dicionario, escala)
        if bloco is None:
            travados.append(campo)
        else:
            campos_por_bloco.setdefault(bloco, []).append(campo)

    grupos = []
    for chave_bloco, rotulo_bloco in _blocos_do_catalogo(catalogo, idioma):
        campos = campos_por_bloco.get(chave_bloco)
        if not campos:
            continue
        grupos.append(
            f'<div class="lab-bloco" data-laboratorio-bloco="{html.escape(chave_bloco)}">'
            f'<h4>{html.escape(rotulo_bloco)}</h4>{"".join(campos)}</div>'
        )
    if travados:
        grupos.append(
            f'<div class="lab-bloco lab-bloco-travado" data-laboratorio-bloco="">'
            f'<h4>{html.escape(t(dicionario, "valuation.laboratorio_nao_editavel_titulo"))}</h4>'
            f'{"".join(travados)}</div>'
        )

    titulo = _texto_de_dado_html(t(dicionario, "valuation.laboratorio_cenario_titulo", cenario=nome))
    restaurar = html.escape(t(dicionario, "valuation.laboratorio_restaurar"))
    return (
        f'<section class="lab-cenario" data-laboratorio-cenario="{html.escape(nome)}">'
        f'<h3>{titulo}</h3>'
        f'{_saidas_do_cenario_html(dicionario, rotulos_das_saidas)}'
        f'{_diagnosticos_do_cenario_html(dicionario)}'
        f'<div class="lab-blocos">{"".join(grupos)}</div>'
        f'<p class="lab-acoes"><button type="button" data-laboratorio-restaurar>{restaurar}</button></p>'
        f'</section>'
    )


def _congelados_html(resultados: dict, dicionario: dict) -> str:
    """L3/§8.4: o que NÃO é vivo nesta fatia aparece rotulado, nunca omitido —
    o analista tem de saber que aqueles números não acompanham a edição."""
    itens = [
        ("sotp", "valuation.laboratorio_congelado_sotp"),
        ("reversa", "valuation.laboratorio_congelado_reversa"),
        ("sensibilidades", "valuation.laboratorio_congelado_sensibilidades"),
    ]
    linhas = "".join(
        f'<li>{html.escape(t(dicionario, chave_texto))}</li>'
        for campo, chave_texto in itens if resultados.get(campo)
    )
    if not linhas:
        return ""
    titulo = html.escape(t(dicionario, "valuation.laboratorio_congelado_titulo"))
    return f'<section class="lab-congelado"><h4>{titulo}</h4><ul>{linhas}</ul></section>'


def _laboratorio_html(caso: dict, resultados: dict, catalogo: dict, idioma: str,
                       dicionario: dict) -> str:
    """O painel inteiro, ou `""` quando não há laboratório possível (rota que
    o catálogo não conhece, ou caso sem cenário)."""
    rota = _campo_de_contrato(resultados, "rota", "resultados")
    premissas_catalogo = _premissas_da_rota(catalogo, rota)
    cenarios = caso.get("cenarios") or {}
    if premissas_catalogo is None or not cenarios:
        return ""
    moeda = caso.get("moeda")
    rotulos_das_saidas = {
        "preco": _rotulo_do_numero(resultados, catalogo, dicionario, "preco_justo_titulo",
                                   CAMINHO_DOS_PRECOS_POR_CENARIO),
        "multiplo": _rotulo_do_numero(resultados, catalogo, dicionario, "multiplo_justo_titulo",
                                      CAMINHO_DOS_MULTIPLOS_POR_CENARIO),
        "upside": _rotulo_do_numero(resultados, catalogo, dicionario, "upside_titulo",
                                    CAMINHO_DOS_UPSIDES_POR_CENARIO),
    }

    paineis = "".join(
        _cenario_do_laboratorio_html(
            rota, nome, (bloco or {}).get("premissas") or {}, indice, premissas_catalogo,
            catalogo, idioma, moeda, dicionario, rotulos_das_saidas, resultados.get("escala_monetaria"))
        for indice, (nome, bloco) in enumerate(cenarios.items())
    )
    return (
        f'<section class="laboratorio" data-laboratorio>'
        f'<h2>{html.escape(t(dicionario, "valuation.laboratorio_titulo"))}</h2>'
        f'<p class="lab-nota">{html.escape(t(dicionario, "valuation.laboratorio_nota"))}</p>'
        f'<div class="lab-badge" data-laboratorio-badge role="status" aria-live="polite"></div>'
        f'{paineis}'
        f'{_congelados_html(resultados, dicionario)}'
        f'</section>'
    )


def _diagnosticos_do_catalogo(catalogo: dict, idioma: str) -> dict:
    """`{chave: {rotulo, severidade}}` de TODO diagnóstico do catálogo, no
    idioma (fatia 5C, Task 3, T5) — o dicionário com que `laboratorio.js`
    pinta as chaves que a fachada devolve. Todos, não só os que o `resultados`
    publicou: qualquer edição pode acender qualquer um. Rótulo ausente no
    idioma é recusa nomeada, a mesma de blocos e múltiplos — o painel nunca
    cai no código cru por falta de rótulo."""
    saida = {}
    diagnosticos = catalogo.get("diagnosticos") or {}
    for chave in sorted(diagnosticos):
        info = diagnosticos[chave] or {}
        rotulo = (info.get("rotulo") or {}).get(idioma)
        if not rotulo:
            raise RotuloDoCatalogoAusente(
                f"catálogo de apresentação sem rótulo em '{idioma}' para o diagnóstico '{chave}'.")
        saida[chave] = {"rotulo": rotulo, "severidade": info.get("severidade")}
    return saida


def _recusas_do_catalogo(catalogo: dict, idioma: str) -> dict:
    """`{codigo: rotulo}` de todo motivo de recusa do catálogo, no idioma (onda
    de correção da revisão final da 5C, F2) — com que `laboratorio.js` diz POR
    QUE a fachada recusou um cenário. O código chega da fachada; este módulo
    não interpreta nenhum. Mesma disciplina de `_diagnosticos_do_catalogo`:
    rótulo ausente no idioma é recusa nomeada, e o painel nunca cai no código
    cru por falta de rótulo."""
    saida = {}
    recusas = catalogo.get("recusas") or {}
    for codigo in sorted(recusas):
        rotulo = ((recusas[codigo] or {}).get("rotulo") or {}).get(idioma)
        if not rotulo:
            raise RotuloDoCatalogoAusente(
                f"catálogo de apresentação sem rótulo em '{idioma}' para o motivo de recusa '{codigo}'.")
        saida[codigo] = rotulo
    return saida


def _laboratorio_para_json(caso: dict, resultados: dict, catalogo: dict, idioma: str,
                            dicionario: dict) -> dict | None:
    """O payload do laboratório: o `caso` e o `resultados` INTEIROS (opacos —
    este módulo não os interpreta; quem os lê é a fachada, do lado da
    integração), as três receitas de formatação das saídas, os rótulos dos
    múltiplos, o rótulo e a severidade de cada diagnóstico (Task 3), o rótulo
    de cada motivo de recusa (onda de correção da revisão final, F2) e a prosa
    de interface que o JS escreve.

    O `resultados` viaja junto porque o badge de paridade (L4) é um FATO
    medido na máquina de quem abriu o arquivo: a fachada recomputa cada
    cenário a partir do `caso` e compara com o que o Python publicou. Sem os
    dois lados na página não há o que comparar.

    Os textos com `{marcador}` vão como MODELO (`t()` sem valores não
    formata): quem substitui é o JS, com o cenário/chave/números da
    divergência que a fachada nomeou."""
    rota = _campo_de_contrato(resultados, "rota", "resultados")
    if _premissas_da_rota(catalogo, rota) is None or not (caso.get("cenarios") or {}):
        return None
    moeda = caso.get("moeda")
    rotulos_multiplos = {
        chave: _rotulo_multiplo(catalogo, chave, idioma)
        for chave in sorted((catalogo.get("multiplos") or {}))
    }
    return {
        "idioma": idioma,
        "caso": caso,
        "resultados": resultados,
        "formatos": {
            "preco": placeholders.especificacao_de_formato("moeda", idioma, moeda),
            "multiplo": placeholders.especificacao_de_formato("x2", idioma, moeda),
            "upside": placeholders.especificacao_de_formato("pct1", idioma, moeda),
        },
        "rotulosMultiplos": rotulos_multiplos,
        "diagnosticos": _diagnosticos_do_catalogo(catalogo, idioma),
        "recusas": _recusas_do_catalogo(catalogo, idioma),
        "textos": {
            "semValor": t(dicionario, "valuation.laboratorio_sem_valor"),
            "paridadeOk": t(dicionario, "valuation.laboratorio_paridade_ok"),
            "paridadeDivergente": t(dicionario, "valuation.laboratorio_paridade_divergente"),
            "paridadeItem": t(dicionario, "valuation.laboratorio_paridade_item"),
            "paridadeIndisponivel": t(dicionario, "valuation.laboratorio_paridade_indisponivel"),
            "diagnosticosNenhum": t(dicionario, "valuation.laboratorio_diagnosticos_nenhum"),
            "diagnosticoDesconhecido": t(dicionario, "valuation.laboratorio_diagnostico_desconhecido"),
            "diagnosticosRecusado": t(dicionario, "valuation.laboratorio_diagnosticos_recusado"),
            "recusaDesconhecida": t(dicionario, "valuation.laboratorio_recusa_desconhecida"),
        },
    }


# --------------------------------------------------------------------------
# Leitura condicional (fatia 5D, onda de correção da revisão final, F1). Sob
# fronteira de escopo, todo número que a integração declara conclusão de valor
# (`catalogo.conclusoes_de_valor`) é leitura condicional: na Conclusão da Tese
# ele não sai, e na Valuation sai com o rótulo condicional do dicionário
# (`valuation.condicional.<chave>`). A decisão é uma só, em `_leitura_condicional`:
# quem exibe um número diz QUAL número exibe — o caminho que lê em `resultados`,
# abaixo — e o mapa da integração responde se ele é conclusão de valor. Nenhum
# nome de campo decide nada neste módulo. A D3 tratava só o preço por ação, e o
# upside, o múltiplo justo, a lista por cenário, as saídas do laboratório e a
# matriz saíam com os rótulos de sempre ao lado de "(sem preço-alvo)".
# --------------------------------------------------------------------------

# O caminho, em `resultados`, de cada número de valuation que esta página exibe;
# `*` num segmento vale por todos os números exibidos ali.
CAMINHO_DO_PRECO_DA_MANCHETE: str = "manchete.preco_acao"
CAMINHO_DO_UPSIDE_DA_MANCHETE: str = "manchete.upside"
CAMINHO_DO_MULTIPLO_DA_MANCHETE: str = "manchete.multiplo.valor"
CAMINHO_DO_MULTIPLO_DE_TELA: str = "mercado_tela.valor"
CAMINHO_DOS_PRECOS_POR_CENARIO: str = "cenarios.*.valor.preco_acao"
CAMINHO_DOS_MULTIPLOS_POR_CENARIO: str = "cenarios.*.multiplos.*"
CAMINHO_DOS_UPSIDES_POR_CENARIO: str = "cenarios.*.vs_preco.upside"
CAMINHO_DAS_CELULAS_DA_GRADE_2D: str = "sensibilidades.grades_2d.*.celulas.*.*.valor"
# Fatia 5F, Task 5: os números novos da aba Valuation — o par forward, as tabelas 1D, os
# múltiplos e os montantes da formação do valor.
CAMINHO_DO_MULTIPLO_FORWARD_DA_MANCHETE: str = "manchete.multiplo_forward.valor"
CAMINHO_DO_MULTIPLO_DE_TELA_FORWARD: str = "mercado_tela_forward.valor"
CAMINHO_DOS_PRECOS_DA_GRADE_1D: str = "sensibilidades.grades_1d.*.pontos.*.valor"
CAMINHO_DOS_MULTIPLOS_DA_GRADE_1D: str = "sensibilidades.grades_1d.*.pontos.*.multiplo"
CAMINHO_DO_VALOR_DA_FASE_1: str = "cenarios.*.vp_fase1"
CAMINHO_DO_VALOR_DA_FASE_2: str = "cenarios.*.valor_fase2_no_ano_T"
# Fatia 5G, Task 4: as quatro conclusões de valor das alternativas — o preço do ramo
# alternativo de cada escolha metodológica, o do retorno exigido, o valor ponderado por
# probabilidade e o do cross-check pela rota oposta.
CAMINHO_DO_PRECO_DA_ALTERNATIVA: str = "escolhas_metodologicas.*.preco_alternativa"
CAMINHO_DO_PRECO_DO_RETORNO_EXIGIDO: str = "retorno_exigido.preco_acao"
CAMINHO_DO_VALOR_PONDERADO: str = "valor_ponderado.valor"
CAMINHO_DO_PRECO_DO_CROSS_CHECK: str = "cross_check.preco_acao"

# O `impacto` de uma escolha e a `diferenca_vs_manchete` do cross-check são FRAÇÕES DE
# COMPARAÇÃO, não conclusão de valor (5G, D1/D4): ficam fora do mapa da integração — e
# por isso fora de `_unidade_publicada` —, e saem no formato do upside do cabeçalho.
FORMATO_DA_FRACAO_DE_COMPARACAO: str = "pct1"
# O peso de um cenário é JULGAMENTO declarado (D3, §8.2: "fora da fórmula"), não insumo
# nem conclusão: nem o mapa das conclusões de valor nem o dos insumos do caso o cobrem, e
# nenhuma unidade do catálogo lhe pertence. Sai em pontos percentuais inteiros, que é como
# o caso o declara e como a integração o exige (somando 100).
FORMATO_DO_PESO: str = "pp0"


def _leitura_condicional(resultados: dict, catalogo: dict, caminho: str) -> bool:
    """`True` quando o número que a página exibe em `caminho` é, sob fronteira de
    escopo, conclusão de valor pelo mapa da integração (`placeholders.conclusao_de_
    valor`). Fora da fronteira, sempre `False` — e o mapa nem é lido. Sob ela, um
    catálogo sem o mapa é recusa nomeada: o QC já o reprovou (`fronteira_de_escopo_
    desconhecida`), e este módulo nunca decide ao acaso o que é preço-alvo."""
    if _campo_de_contrato(resultados, "fronteira_de_escopo", "resultados") is None:
        return False
    mapa = placeholders.conclusoes_de_valor(catalogo)
    if mapa is None:
        raise RotuloDoCatalogoAusente(
            "catálogo de apresentação sem o mapa das conclusões de valor ('conclusoes_de_valor'): sob "
            "fronteira de escopo, o relatório não sabe quais números exibir como leitura condicional."
        )
    return placeholders.conclusao_de_valor(caminho, mapa) is not None


def _rotulo_do_numero(resultados: dict, catalogo: dict, dicionario: dict, chave: str, caminho: str,
                      **valores) -> str:
    """O rótulo do número exibido em `caminho`: `valuation.<chave>`, ou — quando ele é
    leitura condicional (`_leitura_condicional`) — `valuation.condicional.<chave>`. Um
    número que o mapa passe a cobrir sem forma condicional no dicionário é
    `ChaveDeInterfaceAusente`, nomeada: nunca uma conclusão de valor com o rótulo de
    sempre sob fronteira."""
    if _leitura_condicional(resultados, catalogo, caminho):
        return t(dicionario, f"valuation.condicional.{chave}", **valores)
    return t(dicionario, f"valuation.{chave}", **valores)


def _multiplos_html(resultados: dict, catalogo: dict, idioma: str, dicionario: dict,
                    omitir_conclusao_de_valor: bool = False) -> str:
    """O múltiplo justo da manchete ao lado do múltiplo de tela, cada lado com o
    rótulo da própria chave (a regra 4 de `resultados/1` garante a mesma base) —
    ou, num caso SOTP (sem `manchete.multiplo`), a nota de que o preço
    consolidado não tem múltiplo único. Uma leitura só, para o cabeçalho da
    Valuation e a Conclusão da Tese (5D, Task 3): duas leituras do mesmo par
    divergiriam.

    Onda de correção da revisão final (F1): sob fronteira de escopo, o lado que o
    mapa da integração declara conclusão de valor — hoje, o múltiplo justo — sai
    com o rótulo condicional na Valuation e NÃO sai quando `omitir_conclusao_de_
    valor` (a Conclusão da Tese): múltiplo justo contra o de tela é o upside dito
    em outra unidade, e a Tese fica só com a leitura de mercado que a §14 mantém.

    Fatia 5F, Task 5 (D5): depois do par corrente, o par forward — o múltiplo justo
    forward (`manchete.multiplo_forward`, que só existe fora do degrau e da rampa) ao
    lado do de tela forward (`mercado_tela_forward`), cuja nota leva o período e a fonte
    da métrica forward como dado; sem métrica declarada, a tela forward diz isso, sem
    número. Sem `manchete.multiplo_forward`, não há par forward."""
    manchete = resultados["manchete"]
    if "multiplo" not in manchete:
        return f'<p class="sotp-nota">{html.escape(t(dicionario, "valuation.sotp_sem_multiplo"))}</p>'
    lados = [
        ("multiplo_justo_titulo", CAMINHO_DO_MULTIPLO_DA_MANCHETE, manchete["multiplo"]),
        ("multiplo_tela_titulo", CAMINHO_DO_MULTIPLO_DE_TELA, resultados["mercado_tela"]),
    ]
    if isinstance(manchete.get("multiplo_forward"), dict):
        lados += [
            ("multiplo_justo_forward_titulo", CAMINHO_DO_MULTIPLO_FORWARD_DA_MANCHETE, manchete["multiplo_forward"]),
            ("multiplo_tela_forward_titulo", CAMINHO_DO_MULTIPLO_DE_TELA_FORWARD,
             _campo_de_contrato(resultados, "mercado_tela_forward", "resultados")),
        ]
    blocos = []
    for chave_do_rotulo, caminho, multiplo in lados:
        if omitir_conclusao_de_valor and _leitura_condicional(resultados, catalogo, caminho):
            continue
        rotulo = _rotulo_do_numero(resultados, catalogo, dicionario, chave_do_rotulo, caminho)
        if multiplo is None:
            valor_fmt = t(dicionario, "valuation.sem_valor")
            nota_html = html.escape(t(dicionario, "valuation.metrica_forward_nao_declarada"))
        else:
            valor_fmt = placeholders.formatar(multiplo["valor"], "x2", idioma)
            nota_html = html.escape(_rotulo_multiplo(catalogo, multiplo["chave"], idioma))
            metrica = multiplo.get("metrica")
            if isinstance(metrica, dict):
                nota_html = _texto_de_dado_html(t(
                    dicionario, "valuation.multiplo_tela_forward_nota",
                    multiplo=_rotulo_multiplo(catalogo, multiplo["chave"], idioma),
                    periodo=str(metrica.get("periodo")), fonte=str(metrica.get("fonte"))))
        blocos.append(
            f'<div class="metrica">'
            f'<span class="metrica-rotulo">{html.escape(rotulo)}</span>'
            f'<span class="metrica-valor">{_texto_de_dado_html(valor_fmt)}</span>'
            f'<span class="metrica-nota">{nota_html}</span>'
            f'</div>'
        )
    return "".join(blocos)


# --------------------------------------------------------------------------
# Aba Valuation na ordem da §9 (fatia 5F, Task 5, D15): cabeçalho — preço e upside, a faixa
# piso–teto, os múltiplos corrente e forward, a rota e a convenção — → como o valor é formado →
# cenários → laboratório → ponte → sensibilidades → o que está no preço. Todo número sai de
# `resultados` formatado pela unidade que o contrato declara; todo texto de metodologia sai do
# catálogo; toda conclusão de valor nova sai por `_rotulo_do_numero`; nenhum código cru e nenhuma
# prosa do motor chega à aba.
# --------------------------------------------------------------------------

# Os blocos que uma limitação publicada declara suprimir (`catalogo.limitacoes.<chave>.afeta`) e que
# a seção "o que está no preço" mostra: a reversa ausente e a curva iso-valor não calculada (5F, D3).
# Nomes que a declaração da integração usa, nunca o nome da limitação.
AFETAS_DO_QUE_ESTA_NO_PRECO: tuple = (contrato_entrega.BLOCO_DA_REVERSA, "iso")


def _rotulo_de_secao_do_catalogo(catalogo: dict, secao: str, codigo: Any, idioma: str) -> str:
    """O rótulo de um código que o catálogo declara numa seção `{código: {rotulo: {idioma: ...}}}` —
    os eixos, os motivos, as identificações e as posições da leitura da reversa (5F, D2). Ausente,
    recusa nomeada: a aba nunca mostra o código cru."""
    info = (catalogo.get(secao) or {}).get(codigo) if isinstance(codigo, str) else None
    rotulo = ((info or {}).get("rotulo") or {}).get(idioma)
    if not rotulo:
        raise RotuloDoCatalogoAusente(
            f"catálogo de apresentação sem rótulo em '{idioma}' para '{codigo}' em '{secao}' — a aba "
            "Valuation nunca mostra o código cru.")
    return rotulo


def _rotulo_do_triangulo(catalogo: dict, rota: str, variavel: Any, idioma: str) -> str:
    """Uma variável do triângulo: premissa da rota (`_rotulo_premissa`) ou variável que não é premissa
    (`catalogo.variaveis_do_triangulo`, hoje `rir`) — D9."""
    if isinstance(variavel, str) and variavel in ((catalogo.get("premissas") or {}).get(rota) or {}):
        return _rotulo_premissa(catalogo, rota, variavel, idioma)
    return _rotulo_de_secao_do_catalogo(catalogo, "variaveis_do_triangulo", variavel, idioma)


def _faixa_da_valuation_html(analise: dict, resultados: dict, idioma: str, moeda: str | None,
                             dicionario: dict) -> str:
    """D15, 1: a faixa piso–teto de `analise.faixa`, quando declarada — os preços que
    `resultados.cenarios.<nome>.valor.preco_acao` publica para as duas pontas, com o nome do cenário.
    O QC já conferiu a ordem (`faixa_fora_de_ordem`); sob fronteira de escopo a faixa é HARD FAIL."""
    faixa = analise.get("faixa")
    if not isinstance(faixa, dict):
        return ""
    cenarios = _campo_de_contrato(resultados, "cenarios", "resultados")
    metricas = []
    for papel in (contrato_entrega.PAPEIS_DA_FAIXA[0], contrato_entrega.PAPEIS_DA_FAIXA[-1]):
        nome = faixa[papel]
        valor = _campo_de_contrato(_campo_de_contrato(cenarios, nome, "resultados.cenarios"),
                                   "valor", f"resultados.cenarios.{nome}")
        preco = _campo_de_contrato(valor, "preco_acao", f"resultados.cenarios.{nome}.valor")
        metricas.append(
            '<div class="metrica">'
            + _valor_html("metrica-rotulo", _rotulo_de_vocabulario(dicionario, "tese.papeis_da_faixa", papel))
            + _valor_html("metrica-valor", placeholders.formatar(preco, "moeda", idioma, moeda))
            + _valor_html("metrica-nota", t(dicionario, "tese.faixa_cenario", cenario=nome))
            + '</div>'
        )
    return f'<section class="valuation-faixa">{"".join(metricas)}</section>'


def _formacao_do_valor_html(resultados: dict, catalogo: dict, idioma: str, moeda: str | None,
                            dicionario: dict) -> str:
    """D15, 2 (D8): o quadro "como o valor é formado", colapsável — o texto de metodologia do
    catálogo (`formacao_do_valor.<rota>`) com os números do cenário da manchete: cada passo cuja
    premissa o cenário declara (na rampa, `util` e `g1` são alternativas, e só a declarada
    aparece), pelo rótulo, pela unidade do catálogo e pela função; os múltiplos que o cenário
    publica; na rampa, os montantes das duas fases; e a síntese. A taxa de reinvestimento aparece
    pela função, nunca como número (D8). Num SOTP, com o rótulo do cenário consolidado; num cenário
    com degrau, com o de antes do degrau — os múltiplos do cenário são os sem degrau."""
    rota = _campo_de_contrato(resultados, "rota", "resultados")
    formacao = (catalogo.get("formacao_do_valor") or {}).get(rota)
    sintese = ((formacao or {}).get("sintese") or {}).get(idioma) if isinstance(formacao, dict) else None
    if not sintese:
        raise RotuloDoCatalogoAusente(
            f"catálogo de apresentação sem 'formacao_do_valor.{rota}' com a síntese em '{idioma}' — o quadro "
            "de como o valor é formado é texto da metodologia, e o relatório não o escreve.")
    nome = _campo_de_contrato(_campo_de_contrato(resultados, "manchete", "resultados"),
                              "cenario", "resultados.manchete")
    cenario = _campo_de_contrato(_campo_de_contrato(resultados, "cenarios", "resultados"),
                                 nome, "resultados.cenarios")
    onde = f"resultados.cenarios.{nome}"
    premissas = _campo_de_contrato(cenario, "premissas", onde)
    escala = resultados.get("escala_monetaria")

    partes = []
    if _manchete_vem_do_sotp(resultados):
        partes.append('<p class="formacao-rotulo">'
                      f'{_texto_de_dado_html(t(dicionario, "valuation.formacao_rotulo_consolidado", cenario=nome))}</p>')
    elif "degrau" in cenario:
        partes.append('<p class="formacao-rotulo">'
                      f'{_texto_de_dado_html(t(dicionario, "valuation.formacao_rotulo_degrau", cenario=nome))}</p>')

    passos = []
    for passo in formacao.get("passos") or []:
        chave = passo.get("premissa")
        if chave not in premissas:
            continue
        rotulo = _rotulo_premissa(catalogo, rota, chave, idioma)
        funcao = ((passo.get("funcao") or {}).get(idioma))
        if not funcao:
            raise RotuloDoCatalogoAusente(
                f"catálogo de apresentação sem a função em '{idioma}' do passo '{chave}' de 'formacao_do_valor.{rota}'.")
        valor = _valor_exibido_da_premissa(catalogo["premissas"][rota][chave], premissas[chave], catalogo, idioma,
                                           moeda, dicionario, escala)
        passos.append('<li class="formacao-passo">'
                      f'{_valor_html("formacao-premissa", rotulo)} {_valor_html("formacao-valor", valor)}'
                      f'<p class="formacao-funcao">{html.escape(funcao)}</p></li>')
    partes.append(f'<ol class="formacao-passos">{"".join(passos)}</ol>')

    unidade_dos_multiplos = _unidade_publicada(catalogo, CAMINHO_DOS_MULTIPLOS_POR_CENARIO)
    itens = [
        '<li class="formacao-multiplo">'
        f'{_valor_html("formacao-multiplo-rotulo", _rotulo_multiplo(catalogo, chave, idioma))} '
        f'{_valor_html("formacao-multiplo-valor", _formatar_na_unidade(valor, catalogo, unidade_dos_multiplos, idioma, moeda))}'
        '</li>'
        for chave, valor in _campo_de_contrato(cenario, "multiplos", onde).items()
    ]
    titulo_dos_multiplos = _rotulo_do_numero(resultados, catalogo, dicionario, "formacao_multiplos_titulo",
                                             CAMINHO_DOS_MULTIPLOS_POR_CENARIO)
    partes.append(f'<div class="formacao-multiplos"><h3>{html.escape(titulo_dos_multiplos)}</h3>'
                  f'<ul>{"".join(itens)}</ul></div>')

    montantes = []
    for chave_do_rotulo, caminho in (("formacao_vp_fase1_titulo", CAMINHO_DO_VALOR_DA_FASE_1),
                                     ("formacao_valor_fase2_titulo", CAMINHO_DO_VALOR_DA_FASE_2)):
        campo = caminho.rsplit(".", 1)[-1]
        if campo not in cenario:
            continue
        rotulo = _rotulo_do_numero(resultados, catalogo, dicionario, chave_do_rotulo, caminho)
        valor = _formatar_na_unidade(cenario[campo], catalogo, _unidade_publicada(catalogo, caminho), idioma, moeda,
                                     escala)
        montantes.append('<div class="metrica">' + _valor_html("metrica-rotulo", rotulo)
                         + _valor_html("metrica-valor", valor) + '</div>')
    if montantes:
        partes.append(f'<div class="formacao-montantes">{"".join(montantes)}</div>')

    partes.append(f'<p class="formacao-sintese">{html.escape(sintese)}</p>')
    return (f'<section class="valuation-formacao"><h2>{html.escape(t(dicionario, "valuation.formacao_titulo"))}</h2>'
            f'<details><summary>{html.escape(t(dicionario, "valuation.formacao_resumo"))}</summary>'
            f'{"".join(partes)}</details></section>')


def _cenarios_da_valuation_html(resultados: dict, catalogo: dict, idioma: str, moeda: str | None,
                                dicionario: dict) -> str:
    """D15, 3 (D9): cada cenário publicado — o nome; a âncora, texto do caso que a integração publica
    em `resultados.cenarios.<nome>.ancora`, como dado (ajuste de D9 no regime de 15/09); o triângulo,
    entradas e saída pelos rótulos do catálogo, ou — sem `triangulo` publicado, a rota rampa — a frase
    de que não se aplica; e o preço e o upside, pela unidade que o mapa da integração declara e com o
    rótulo condicional sob fronteira de escopo."""
    rota = _campo_de_contrato(resultados, "rota", "resultados")
    escala = resultados.get("escala_monetaria")
    rotulo_do_preco = _rotulo_do_numero(resultados, catalogo, dicionario, "preco_justo_titulo",
                                        CAMINHO_DOS_PRECOS_POR_CENARIO)
    rotulo_do_upside = _rotulo_do_numero(resultados, catalogo, dicionario, "upside_titulo",
                                         CAMINHO_DOS_UPSIDES_POR_CENARIO)
    unidade_do_preco = _unidade_publicada(catalogo, CAMINHO_DOS_PRECOS_POR_CENARIO)
    unidade_do_upside = _unidade_publicada(catalogo, CAMINHO_DOS_UPSIDES_POR_CENARIO)
    artigos = []
    for nome, cenario in _campo_de_contrato(resultados, "cenarios", "resultados").items():
        onde = f"resultados.cenarios.{nome}"
        triangulo = cenario.get("triangulo")
        if isinstance(triangulo, dict):
            texto_do_triangulo = t(
                dicionario, "valuation.cenario_triangulo_valor",
                entradas=", ".join(_rotulo_do_triangulo(catalogo, rota, entrada, idioma)
                                   for entrada in triangulo.get("inputs") or []),
                saida=_rotulo_do_triangulo(catalogo, rota, triangulo.get("output"), idioma))
        else:
            texto_do_triangulo = t(dicionario, "valuation.cenario_triangulo_nao_se_aplica")
        preco = _campo_de_contrato(_campo_de_contrato(cenario, "valor", onde), "preco_acao", f"{onde}.valor")
        upside = _campo_de_contrato(_campo_de_contrato(cenario, "vs_preco", onde), "upside", f"{onde}.vs_preco")
        artigos.append(
            '<article class="valuation-cenario">'
            f'<h3>{_texto_de_dado_html(str(nome))}</h3>'
            + _atributo_html(t(dicionario, "valuation.cenario_ancora"),
                             _valor_html("cenario-ancora", str(_campo_de_contrato(cenario, "ancora", onde))))
            + _atributo_html(t(dicionario, "valuation.cenario_triangulo"),
                             _valor_html("cenario-triangulo", texto_do_triangulo))
            + '<div class="valuation-cenario-numeros">'
            + '<div class="metrica">' + _valor_html("metrica-rotulo", rotulo_do_preco)
            + _valor_html("metrica-valor", _formatar_na_unidade(preco, catalogo, unidade_do_preco, idioma, moeda, escala))
            + '</div><div class="metrica">' + _valor_html("metrica-rotulo", rotulo_do_upside)
            + _valor_html("metrica-valor",
                          _formatar_na_unidade(upside, catalogo, unidade_do_upside, idioma, moeda, escala))
            + '</div></div></article>'
        )
    titulo = _rotulo_do_numero(resultados, catalogo, dicionario, "cenarios_titulo", CAMINHO_DOS_PRECOS_POR_CENARIO)
    return f'<section class="valuation-cenarios"><h2>{html.escape(titulo)}</h2>{"".join(artigos)}</section>'


def _eixo_da_reversa_html(nome: str, eixo: dict, catalogo: dict, idioma: str, moeda: str | None,
                          dicionario: dict) -> str:
    """Um eixo do que está no preço, pela leitura normalizada que a integração publica ao lado do
    payload do motor (`leitura`, D2): o rótulo do eixo e o do motivo; cada raiz pela `unidade` da
    leitura, com a identificação rotulada, o intervalo e a curvatura (pela `unidade_da_curvatura`); os
    toques tangenciais; o CAP; e, no eixo de custo de capital, o beta implícito com a posição, a banda
    e a distância. A prosa do motor (`sem_solucao`, `sugestao`) e a álgebra nunca chegam aqui."""
    onde = f"resultados.reversa.eixos.{nome}"
    leitura = _campo_de_contrato(eixo, "leitura", onde)
    unidade = _campo_de_contrato(leitura, "unidade", f"{onde}.leitura")
    linhas = ['<p class="reversa-motivo">'
              f'{html.escape(_rotulo_de_secao_do_catalogo(catalogo, "motivos_da_leitura", leitura.get("motivo"), idioma))}</p>']

    raizes = []
    for raiz in leitura.get("raizes") or []:
        identificacao = raiz.get("identificacao")
        rotulo_da_identificacao = (
            _rotulo_de_secao_do_catalogo(catalogo, "identificacoes", identificacao, idioma) if identificacao is not None
            else t(dicionario, "valuation.reversa_identificacao_indisponivel"))
        pedacos = [_valor_html("reversa-raiz-valor", t(
            dicionario, "valuation.reversa_raiz", identificacao=rotulo_da_identificacao,
            valor=_formatar_na_unidade(raiz.get("valor"), catalogo, unidade, idioma, moeda)))]
        intervalo = raiz.get("intervalo")
        if isinstance(intervalo, list) and len(intervalo) == 2:
            pedacos.append(_valor_html("reversa-intervalo", t(
                dicionario, "valuation.reversa_intervalo",
                de=_formatar_na_unidade(intervalo[0], catalogo, unidade, idioma, moeda),
                ate=_formatar_na_unidade(intervalo[1], catalogo, unidade, idioma, moeda))))
        if raiz.get("curvatura") is not None:
            pedacos.append(_valor_html("reversa-curvatura", t(
                dicionario, "valuation.reversa_curvatura",
                valor=_formatar_na_unidade(raiz["curvatura"], catalogo, leitura.get("unidade_da_curvatura"), idioma,
                                           moeda))))
        raizes.append(f'<li class="reversa-raiz">{" ".join(pedacos)}</li>')
    if raizes:
        linhas.append(f'<ul class="reversa-raizes">{"".join(raizes)}</ul>')

    tangenciais = leitura.get("tangenciais") or []
    if tangenciais:
        linhas.append('<p class="reversa-tangenciais">' + _texto_de_dado_html(t(
            dicionario, "valuation.reversa_tangenciais",
            valores=", ".join(_formatar_na_unidade(valor, catalogo, unidade, idioma, moeda) for valor in tangenciais)))
            + '</p>')
    if leitura.get("cap_anos") is not None:
        linhas.append('<p class="reversa-cap">' + _texto_de_dado_html(t(
            dicionario, "valuation.reversa_cap",
            valor=_formatar_na_unidade(leitura["cap_anos"], catalogo, unidade, idioma, moeda))) + '</p>')

    beta = leitura.get("beta")
    if isinstance(beta, dict):
        unidade_do_beta = beta.get("unidade")
        if beta.get("valor") is not None:
            linhas.append('<p class="reversa-beta">' + _texto_de_dado_html(t(
                dicionario, "valuation.reversa_beta",
                valor=_formatar_na_unidade(beta["valor"], catalogo, unidade_do_beta, idioma, moeda))) + '</p>')
        linhas.append('<p class="reversa-beta-posicao">'
                      f'{html.escape(_rotulo_de_secao_do_catalogo(catalogo, "posicoes_na_banda", beta.get("posicao"), idioma))}</p>')
        banda = beta.get("banda")
        if isinstance(banda, list) and len(banda) == 2 and beta.get("distancia") is not None:
            linhas.append('<p class="reversa-banda">' + _texto_de_dado_html(t(
                dicionario, "valuation.reversa_beta_banda",
                minimo=_formatar_na_unidade(banda[0], catalogo, unidade_do_beta, idioma, moeda),
                maximo=_formatar_na_unidade(banda[1], catalogo, unidade_do_beta, idioma, moeda),
                distancia=_formatar_na_unidade(beta["distancia"], catalogo, unidade_do_beta, idioma, moeda))) + '</p>')

    titulo = _rotulo_de_secao_do_catalogo(catalogo, "eixos_de_reversa", nome, idioma)
    return f'<article class="reversa-eixo"><h3>{html.escape(titulo)}</h3>{"".join(linhas)}</article>'


def _teto_do_crescimento_gratuito_html(teto: dict, catalogo: dict, idioma: str, dicionario: dict) -> str:
    """O teto do crescimento gratuito (5F, D2): o rótulo e o texto do catálogo, e o múltiplo que a
    integração publica com o rótulo da chave dele — nunca a `leitura`, prosa do wrapper."""
    declaracao = catalogo.get("teto_do_crescimento_gratuito") or {}
    rotulo, texto = ((declaracao.get("rotulo") or {}).get(idioma), (declaracao.get("texto") or {}).get(idioma))
    if not rotulo or not texto:
        raise RotuloDoCatalogoAusente(
            f"catálogo de apresentação sem o rótulo e o texto em '{idioma}' de 'teto_do_crescimento_gratuito'.")
    onde = "resultados.reversa.teto_do_crescimento_gratuito"
    multiplo = t(dicionario, "valuation.reversa_teto_multiplo",
                 valor=placeholders.formatar(_campo_de_contrato(teto, "multiplo", onde), "x2", idioma),
                 multiplo=_rotulo_multiplo(catalogo, _campo_de_contrato(teto, "chave", onde), idioma))
    return (f'<div class="reversa-teto"><h3>{html.escape(rotulo)}</h3>'
            f'<p class="reversa-teto-multiplo">{_texto_de_dado_html(multiplo)}</p>'
            f'<p class="reversa-teto-texto">{html.escape(texto)}</p></div>')


def _o_que_esta_no_preco_html(entrega: dict, catalogo: dict, idioma: str, dicionario: dict, prosa: dict) -> str:
    """D15, 7: o que está no preço, congelado nas premissas originais (§8.4) — cada eixo da reversa
    (`_eixo_da_reversa_html`), o teto do crescimento gratuito quando publicado, as limitações publicadas
    que declaram suprimir a reversa ou a curva iso-valor, e o julgamento do analista com o observável,
    quando declarados (D12), pela lista de prosa. Sem reversa, só a limitação que a suprime. Sob
    fronteira de escopo a leitura do preço continua (§14): nada aqui é conclusão de valor."""
    caso, resultados, analise = entrega["caso"], entrega["resultados"], entrega["analise"]
    moeda = caso.get("moeda")
    partes = [f'<p class="reversa-congelado-nota">{html.escape(t(dicionario, "valuation.o_que_esta_no_preco_congelado"))}</p>']
    reversa = resultados.get(contrato_entrega.BLOCO_DA_REVERSA)
    if isinstance(reversa, dict):
        for nome, eixo in _campo_de_contrato(reversa, "eixos", "resultados.reversa").items():
            partes.append(_eixo_da_reversa_html(nome, eixo, catalogo, idioma, moeda, dicionario))
        teto = reversa.get("teto_do_crescimento_gratuito")
        if isinstance(teto, dict):
            partes.append(_teto_do_crescimento_gratuito_html(teto, catalogo, idioma, dicionario))
    declaradas = catalogo.get("limitacoes") or {}
    limitacoes = [_rotulo_limitacao(catalogo, chave, idioma) for chave in resultados.get("limitacoes") or []
                  if isinstance(chave, str) and (declaradas.get(chave) or {}).get("afeta") in AFETAS_DO_QUE_ESTA_NO_PRECO]
    if limitacoes:
        partes.append('<ul class="reversa-limitacoes">'
                      + "".join(f"<li>{html.escape(rotulo)}</li>" for rotulo in limitacoes) + '</ul>')
    if isinstance(analise.get("o_que_esta_no_preco"), dict):
        partes.append(
            '<div class="reversa-julgamento">'
            f'<h3>{html.escape(t(dicionario, "valuation.o_que_esta_no_preco_julgamento_titulo"))}</h3>'
            '<p class="reversa-julgamento-texto">'
            f'{_texto_de_dado_html(_prosa(prosa, "analise.o_que_esta_no_preco.julgamento"))}</p>'
            + _atributo_html(t(dicionario, "valuation.o_que_esta_no_preco_observavel"),
                             _valor_html("reversa-observavel", _prosa(prosa, "analise.o_que_esta_no_preco.observavel")))
            + '</div>'
        )
    return (f'<section class="valuation-o-que-esta-no-preco">'
            f'<h2>{html.escape(t(dicionario, "valuation.o_que_esta_no_preco_titulo"))}</h2>{"".join(partes)}</section>')


# --------------------------------------------------------------------------
# As alternativas que o wrapper roda (fatia 5G, Task 4): o painel de escolhas
# metodológicas, entre a ponte e as sensibilidades (§8.2), e — depois do que está no
# preço — o retorno exigido, o valor ponderado, o cross-check pela rota oposta e o
# re-teste da hipótese terminal (§9).
#
# E3 na tela: todo número sai de `resultados` já calculado, e nenhuma decisão de
# metodologia mora aqui. QUAL escolha vai ao nível principal é `gatilho_disparou` (o
# caso declara) ou `material` (a integração decide, pelo limiar dela); o rótulo e o
# gatilho de cada escolha e a direção do empilhamento vêm do catálogo e do dicionário,
# nunca como código cru; e o preço alternativo, o do retorno exigido, o valor ponderado
# e o do cross-check passam por `_rotulo_do_numero` — sob fronteira de escopo, os quatro
# são leitura condicional.
# --------------------------------------------------------------------------

def _secao_colapsada_html(classe: str, titulo: str, resumo: str, corpo: str) -> str:
    """Uma seção que abre fechada, no molde da formação do valor: o título fora do
    `<details>`, para a aba continuar legível de relance."""
    return (f'<section class="{classe}"><h2>{html.escape(titulo)}</h2>'
            f'<details><summary>{html.escape(resumo)}</summary>{corpo}</details></section>')


def _metrica_html(rotulo: str, valor: str) -> str:
    return '<div class="metrica">' + _valor_html("metrica-rotulo", rotulo) + _valor_html("metrica-valor", valor) + '</div>'


def _rotulo_e_gatilho_da_escolha(catalogo: dict, chave: Any, idioma: str) -> tuple[str, str]:
    """O rótulo e o gatilho de uma escolha metodológica, do catálogo (`escolhas_
    metodologicas`) — as duas coisas que a §8.2 pede na tela e que o relatório nunca
    escreve. Ausentes, `RotuloDoCatalogoAusente`: o QC já reprovou a entrega
    (`escolhas_desconhecidas`), e a chave crua nunca chega ao painel."""
    info = (catalogo.get("escolhas_metodologicas") or {}).get(chave) or {}
    rotulo = (info.get("rotulo") or {}).get(idioma)
    gatilho = (info.get("gatilho") or {}).get(idioma)
    if not rotulo or not gatilho:
        raise RotuloDoCatalogoAusente(
            f"catálogo de apresentação sem o rótulo e o gatilho em '{idioma}' da escolha metodológica "
            f"'{chave}' em 'escolhas_metodologicas'.")
    return rotulo, gatilho


def _escolha_html(indice: int, escolha: dict, resultados: dict, catalogo: dict, idioma: str,
                  moeda: str | None, dicionario: dict, prosa: dict, razoes: dict) -> str:
    """Uma escolha do painel (§8.2: escolha central | alternativa | impacto | razão
    econômica): o rótulo e o gatilho do catálogo, a posição do caso-base pelo rótulo do
    dicionário, o preço do ramo alternativo e o impacto sobre a manchete, a razão do
    analista (prosa auditada) e o observável que disparou o gatilho, quando declarado."""
    onde = f"resultados.escolhas_metodologicas.{indice}"
    chave = _campo_de_contrato(escolha, "chave", onde)
    rotulo, gatilho = _rotulo_e_gatilho_da_escolha(catalogo, chave, idioma)
    escala = resultados.get("escala_monetaria")
    partes = [
        f'<p class="escolha-gatilho">{html.escape(gatilho)}</p>',
        _atributo_html(t(dicionario, "valuation.escolha_posicao"),
                       _valor_html("escolha-posicao", _rotulo_de_vocabulario(
                           dicionario, "valuation.posicoes_da_escolha",
                           _campo_de_contrato(escolha, "no_caso_base", onde)))),
        '<div class="valuation-escolha-numeros">'
        + _metrica_html(_rotulo_do_numero(resultados, catalogo, dicionario, "escolha_preco_titulo",
                                          CAMINHO_DO_PRECO_DA_ALTERNATIVA),
                        _formatar_na_unidade(_campo_de_contrato(escolha, "preco_alternativa", onde), catalogo,
                                             _unidade_publicada(catalogo, CAMINHO_DO_PRECO_DA_ALTERNATIVA),
                                             idioma, moeda, escala))
        + _metrica_html(t(dicionario, "valuation.escolha_impacto_titulo"),
                        placeholders.formatar(_campo_de_contrato(escolha, "impacto", onde),
                                              FORMATO_DA_FRACAO_DE_COMPARACAO, idioma))
        + '</div>',
    ]
    if chave in razoes:
        partes.append(f'<p class="escolha-razao">{_texto_de_dado_html(_prosa(prosa, razoes[chave]))}</p>')
    disparou = escolha.get("gatilho_disparou")
    if isinstance(disparou, dict):
        partes.append(_atributo_html(
            t(dicionario, "valuation.escolha_gatilho_disparou"),
            _valor_html("escolha-observavel",
                        str(_campo_de_contrato(disparou, "observavel", f"{onde}.gatilho_disparou")))))
    return f'<article class="valuation-escolha"><h3>{html.escape(rotulo)}</h3>{"".join(partes)}</article>'


def _painel_de_escolhas_html(entrega: dict, catalogo: dict, idioma: str, dicionario: dict, prosa: dict) -> str:
    """D1 (§8.2): o painel de escolhas metodológicas, entre a ponte e as sensibilidades.

    O alerta de empilhamento sai acima, com a direção pelo rótulo do dicionário e as
    escolhas pelos rótulos do catálogo. O painel é DINÂMICO: a escolha cujo gatilho
    disparou, ou que a integração marcou `material`, fica no nível principal; as demais
    ficam num `<details>` fechado. Nenhuma escolha publicada, nenhuma seção."""
    resultados, analise = entrega["resultados"], entrega["analise"]
    escolhas = resultados.get("escolhas_metodologicas") or []
    if not escolhas:
        return ""
    moeda = (entrega.get("caso") or {}).get("moeda")
    razoes = {escolha["chave"]: f"analise.escolhas.{indice}.razao"
              for indice, escolha in enumerate(analise.get("escolhas") or [])
              if isinstance(escolha, dict) and "chave" in escolha}

    principais, avancadas = [], []
    for indice, escolha in enumerate(escolhas):
        bloco = _escolha_html(indice, escolha, resultados, catalogo, idioma, moeda, dicionario, prosa, razoes)
        no_principal = escolha.get("gatilho_disparou") is not None or escolha.get("material") is True
        (principais if no_principal else avancadas).append(bloco)

    partes = []
    empilhamento = resultados.get("empilhamento")
    if isinstance(empilhamento, dict):
        partes.append('<p class="escolhas-empilhamento">' + _texto_de_dado_html(t(
            dicionario, "valuation.escolhas_empilhamento",
            direcao=_rotulo_de_vocabulario(dicionario, "valuation.direcoes_do_empilhamento",
                                           empilhamento.get("direcao")),
            escolhas=", ".join(_rotulo_e_gatilho_da_escolha(catalogo, chave, idioma)[0]
                               for chave in empilhamento.get("chaves") or []))) + '</p>')
    partes.extend(principais)
    if avancadas:
        partes.append(f'<details><summary>{html.escape(t(dicionario, "valuation.escolhas_avancadas_resumo"))}'
                      f'</summary>{"".join(avancadas)}</details>')
    return _secao_html("valuation-escolhas", t(dicionario, "valuation.escolhas_titulo"), "".join(partes))


def _retorno_exigido_html(resultados: dict, catalogo: dict, idioma: str, moeda: str | None,
                          dicionario: dict) -> str:
    """D2 (§8.2: "que valor resulta se eu exigir retorno de X%?"): a taxa pela unidade da
    premissa que ela substituiu, a premissa pelo rótulo do catálogo e o preço que resulta —
    colapsado, e com a nota de que é leitura, jamais fair value. Sem o bloco, nada."""
    retorno = resultados.get("retorno_exigido")
    if not isinstance(retorno, dict):
        return ""
    onde = "resultados.retorno_exigido"
    rota = _campo_de_contrato(resultados, "rota", "resultados")
    premissa = _campo_de_contrato(retorno, "premissa_substituida", onde)
    corpo = (
        _atributo_html(t(dicionario, "valuation.retorno_exigido_taxa"),
                       _valor_html("retorno-exigido-taxa",
                                   _formatar_na_unidade(_campo_de_contrato(retorno, "taxa", onde), catalogo,
                                                        _unidade_da_premissa(catalogo, rota, premissa),
                                                        idioma, moeda)))
        + _atributo_html(t(dicionario, "valuation.retorno_exigido_premissa"),
                         _valor_html("retorno-exigido-premissa",
                                     _rotulo_premissa(catalogo, rota, premissa, idioma)))
        + _metrica_html(_rotulo_do_numero(resultados, catalogo, dicionario, "retorno_exigido_preco_titulo",
                                          CAMINHO_DO_PRECO_DO_RETORNO_EXIGIDO),
                        _formatar_na_unidade(_campo_de_contrato(retorno, "preco_acao", onde), catalogo,
                                             _unidade_publicada(catalogo, CAMINHO_DO_PRECO_DO_RETORNO_EXIGIDO),
                                             idioma, moeda, resultados.get("escala_monetaria")))
        + f'<p class="retorno-exigido-nota">{html.escape(t(dicionario, "valuation.retorno_exigido_nota"))}</p>'
    )
    return _secao_colapsada_html("valuation-retorno-exigido", t(dicionario, "valuation.retorno_exigido_titulo"),
                                 t(dicionario, "valuation.retorno_exigido_resumo"), corpo)


def _valor_ponderado_html(resultados: dict, catalogo: dict, idioma: str, moeda: str | None,
                          dicionario: dict) -> str:
    """D3 (§8.2: pesos "fora da fórmula"): a soma de peso × preço que a integração compôs,
    com cada peso ao lado do seu cenário — colapsado, e com a nota de que o número nunca
    substitui bear, base e bull. Sem o bloco, nada."""
    ponderado = resultados.get("valor_ponderado")
    if not isinstance(ponderado, dict):
        return ""
    onde = "resultados.valor_ponderado"
    pesos = "".join(
        f'<li class="valor-ponderado-peso">'
        f'{_texto_de_dado_html(t(dicionario, "valuation.valor_ponderado_peso", cenario=str(nome), peso=placeholders.formatar(peso, FORMATO_DO_PESO, idioma)))}'
        f'</li>'
        for nome, peso in _campo_de_contrato(ponderado, "pesos", onde).items())
    corpo = (
        _metrica_html(_rotulo_do_numero(resultados, catalogo, dicionario, "valor_ponderado_valor_titulo",
                                        CAMINHO_DO_VALOR_PONDERADO),
                      _formatar_na_unidade(_campo_de_contrato(ponderado, "valor", onde), catalogo,
                                           _unidade_publicada(catalogo, CAMINHO_DO_VALOR_PONDERADO),
                                           idioma, moeda, resultados.get("escala_monetaria")))
        + f'<ul class="valor-ponderado-pesos">{pesos}</ul>'
        + f'<p class="valor-ponderado-nota">{html.escape(t(dicionario, "valuation.valor_ponderado_nota"))}</p>'
    )
    return _secao_colapsada_html("valuation-valor-ponderado", t(dicionario, "valuation.valor_ponderado_titulo"),
                                 t(dicionario, "valuation.valor_ponderado_resumo"), corpo)


def _cross_check_html(entrega: dict, catalogo: dict, idioma: str, moeda: str | None, dicionario: dict,
                      prosa: dict) -> str:
    """D4 (§8.1): o segundo método. Com o cross-check publicado, a rota oposta pelo rótulo
    do catálogo, o preço dela e a diferença contra a manchete; sem ele, a razão da ausência
    que o analista declarou; sem os dois, a frase de que não foi declarado — a seção sai
    sempre, porque um cross-check que ninguém declarou é informação, não silêncio."""
    resultados, analise = entrega["resultados"], entrega["analise"]
    cross_check = resultados.get(contrato_entrega.BLOCO_DO_CROSS_CHECK)
    ausente = analise.get("cross_check")
    if isinstance(cross_check, dict):
        onde = "resultados.cross_check"
        corpo = (
            _atributo_html(t(dicionario, "valuation.cross_check_rota"),
                           _valor_html("cross-check-rota",
                                       _rotulo_rota(catalogo, _campo_de_contrato(cross_check, "rota", onde), idioma)))
            + '<div class="valuation-cross-check-numeros">'
            + _metrica_html(_rotulo_do_numero(resultados, catalogo, dicionario, "cross_check_preco_titulo",
                                              CAMINHO_DO_PRECO_DO_CROSS_CHECK),
                            _formatar_na_unidade(_campo_de_contrato(cross_check, "preco_acao", onde), catalogo,
                                                 _unidade_publicada(catalogo, CAMINHO_DO_PRECO_DO_CROSS_CHECK),
                                                 idioma, moeda, resultados.get("escala_monetaria")))
            + _metrica_html(t(dicionario, "valuation.cross_check_diferenca_titulo"),
                            placeholders.formatar(_campo_de_contrato(cross_check, "diferenca_vs_manchete", onde),
                                                  FORMATO_DA_FRACAO_DE_COMPARACAO, idioma))
            + '</div>'
        )
    elif isinstance(ausente, dict):
        corpo = ('<p class="cross-check-ausente">'
                 f'{_texto_de_dado_html(_prosa(prosa, "analise.cross_check.ausente.razao"))}</p>')
    else:
        corpo = ('<p class="cross-check-nao-declarado">'
                 f'{html.escape(t(dicionario, "valuation.cross_check_nao_declarado"))}</p>')
    return _secao_html("valuation-cross-check", t(dicionario, "valuation.cross_check_titulo"), corpo)


def _reteste_terminal_html(analise: dict, dicionario: dict, prosa: dict) -> str:
    """D5: o re-teste da hipótese terminal — o resultado pelo rótulo do dicionário
    (vocabulário de processo, nunca o código cru) e o texto do analista. Sem o bloco, nada."""
    bloco = analise.get("reteste_terminal")
    if not isinstance(bloco, dict):
        return ""
    corpo = (
        _atributo_html(t(dicionario, "valuation.reteste_terminal_resultado"),
                       _valor_html("reteste-terminal-resultado",
                                   _rotulo_de_vocabulario(dicionario, "valuation.resultados_do_reteste_terminal",
                                                          bloco.get("resultado"))))
        + '<p class="reteste-terminal-texto">'
        f'{_texto_de_dado_html(_prosa(prosa, "analise.reteste_terminal.texto"))}</p>'
    )
    return _secao_html("valuation-reteste-terminal", t(dicionario, "valuation.reteste_terminal_titulo"), corpo)


def _valuation_html(entrega: dict, catalogo: dict, idioma: str, dicionario: dict, prosa: dict,
                     com_laboratorio: bool = False) -> str:
    """A aba inteira, na ordem de D15, com as quatro seções que a 5G acrescenta (ver as
    duas seções acima)."""
    caso, resultados, analise = entrega["caso"], entrega["resultados"], entrega["analise"]
    moeda = caso.get("moeda")
    manchete = resultados["manchete"]

    preco_fmt = _texto_de_dado_html(placeholders.formatar(manchete["preco_acao"], "moeda", idioma, moeda))
    upside_fmt = _texto_de_dado_html(placeholders.formatar(manchete["upside"], "pct1", idioma))
    rotulo_do_preco = _rotulo_do_numero(resultados, catalogo, dicionario, "preco_justo_titulo",
                                        CAMINHO_DO_PRECO_DA_MANCHETE)
    rotulo_do_upside = _rotulo_do_numero(resultados, catalogo, dicionario, "upside_titulo",
                                         CAMINHO_DO_UPSIDE_DA_MANCHETE)
    cabecalho = (
        f'<div class="metrica">'
        f'<span class="metrica-rotulo">{html.escape(rotulo_do_preco)}</span>'
        f'<span class="metrica-valor">{preco_fmt}</span>'
        f'</div>'
        f'<div class="metrica">'
        f'<span class="metrica-rotulo">{html.escape(rotulo_do_upside)}</span>'
        f'<span class="metrica-valor">{upside_fmt}</span>'
        f'</div>'
    )

    bloco_multiplos = _multiplos_html(resultados, catalogo, idioma, dicionario)
    if "multiplo" in manchete:
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
        bloco_rota = ""

    # L3, e o achado 3 da Task 1: num caso com SOTP, `manchete.preco_acao` é o
    # preço da SOMA DAS PARTES -- que esta fatia deixou congelado --, e não o
    # preço do cenário que o laboratório recalcula. Sem este rótulo, o
    # analista veria o preço do cenário se mover logo abaixo de uma manchete
    # que não se move e concluiria que um dos dois está errado.
    nota_manchete = ""
    if com_laboratorio and resultados.get("sotp"):
        nota_manchete = (
            f'<p class="lab-congelado-nota">'
            f'{html.escape(t(dicionario, "valuation.laboratorio_manchete_congelada"))}</p>'
        )

    laboratorio = (_laboratorio_html(caso, resultados, catalogo, idioma, dicionario)
                   if com_laboratorio else "")
    return (
        f'<section class="valuation-cabecalho">{cabecalho}</section>'
        f'{nota_manchete}'
        f'{_faixa_da_valuation_html(analise, resultados, idioma, moeda, dicionario)}'
        f'<section class="valuation-multiplos">{bloco_multiplos}</section>'
        f'<section class="valuation-rota">{bloco_rota}</section>'
        f'{_formacao_do_valor_html(resultados, catalogo, idioma, moeda, dicionario)}'
        f'{_cenarios_da_valuation_html(resultados, catalogo, idioma, moeda, dicionario)}'
        f'{laboratorio}'
        f'{_ponte_html(resultados, catalogo, idioma, dicionario, moeda)}'
        f'{_painel_de_escolhas_html(entrega, catalogo, idioma, dicionario, prosa)}'
        f'{_sensibilidades_html(caso, resultados, catalogo, idioma, dicionario)}'
        f'{_o_que_esta_no_preco_html(entrega, catalogo, idioma, dicionario, prosa)}'
        f'{_retorno_exigido_html(resultados, catalogo, idioma, moeda, dicionario)}'
        f'{_valor_ponderado_html(resultados, catalogo, idioma, moeda, dicionario)}'
        f'{_cross_check_html(entrega, catalogo, idioma, moeda, dicionario, prosa)}'
        f'{_reteste_terminal_html(analise, dicionario, prosa)}'
    )


# --------------------------------------------------------------------------
# Aba Evidência (§9; fatia 5E, Task 3, D7): a camada de auditabilidade, nesta
# ordem — fontes, ledger, lacunas e limitações declaradas, confronto (se houver),
# ficha técnica e, por fim, a metodologia, o log de resolução dos placeholders de
# toda a prosa e a rastreabilidade dos exhibits.
#
# O ledger tem a forma do contrato `ledger/1` do `er-evidencia`, que
# `entrega.carregar` já conferiu: este módulo só o LÊ. Todo vocabulário dele —
# classe de fonte, tipo de localizador, estatuto, materialidade, âncora do
# consenso — sai pelo rótulo do dicionário, no grupo com o nome do vocabulário no
# contrato (`interface.evidencia.<vocabulário>`), e a classificação de uma
# divergência do confronto, no grupo com o nome da constante do `entrega.py`.
# Rótulo ausente é `ChaveDeInterfaceAusente`, nomeada, nunca a chave crua (a lição
# do B2); `tests/test_relatorio_evidencia.py` trava cada grupo, por igualdade de
# conjunto, contra o contrato e o `entrega.py`. Os textos do ledger e do confronto
# são dado da Evidência (§9: linguagem interna permitida) e saem como a entrega os
# declara; a descrição e o tratamento de uma lacuna são prosa da Tese e saem da
# lista de prosa, resolvidos.
# --------------------------------------------------------------------------

# O valor de um registro é o número que a fonte declara, na unidade que ela declara
# — texto livre, que o relatório não sabe ler. Sai só localizado, pelo formato que o
# QC já usa para os números do ledger (`insumo_nao_reconciliado`): sem escala, sem
# prefixo e sem sufixo — nenhuma conta.
FORMATO_DO_VALOR_DO_LEDGER: str = "num4"

# O nível que a §11 declara interno: o QUALITY WARNING sai no `qc.json` e na ficha
# técnica em arquivo, nunca na página (A8) — nem na ficha que a Evidência mostra.
NIVEL_INTERNO_DO_QC: str = "QUALITY_WARNING"

# Da ficha técnica que `builder.compor_ficha_tecnica` compõe: o bloco dos achados, e
# os blocos que contam registros por um vocabulário do ledger, com o vocabulário que
# rotula cada linha.
BLOCO_DOS_ACHADOS_DA_FICHA: str = "achados"
VOCABULARIO_DOS_BLOCOS_DE_CONTAGEM: dict = {
    "registros_por_estatuto": "estatutos",
    "registros_por_classe_de_fonte": "classes_de_fonte",
}


def _rotulo_da_evidencia(dicionario: dict, vocabulario: str, codigo: Any) -> str:
    """O rótulo de um código de vocabulário do ledger ou do confronto, pelo dicionário."""
    return _rotulo_de_vocabulario(dicionario, f"evidencia.{vocabulario}", str(codigo))


def _valor_do_registro(registro: dict, idioma: str, dicionario: dict) -> str:
    valor = registro["valor"]
    if valor is None:
        return t(dicionario, "evidencia.sem_valor")
    return placeholders.formatar(valor, FORMATO_DO_VALOR_DO_LEDGER, idioma)


def _contagem(quantidade: int, idioma: str) -> str:
    return placeholders.formatar(quantidade, "num0", idioma)


def _tabela_html(classe: str, colunas: list, linhas: list) -> str:
    """Uma tabela com cabeçalho; as colunas e as células são textos, escapados aqui."""
    cabecalho = "".join(f"<th>{_texto_de_dado_html(coluna)}</th>" for coluna in colunas)
    corpo = "".join("<tr>" + "".join(f"<td>{_texto_de_dado_html(celula)}</td>" for celula in linha) + "</tr>"
                    for linha in linhas)
    return f'<table class="{classe}"><thead><tr>{cabecalho}</tr></thead><tbody>{corpo}</tbody></table>'


def _tabela_de_pares_html(classe: str, pares: list) -> str:
    """Uma tabela de rótulo e valor, uma linha por par; os textos são escapados aqui."""
    corpo = "".join(f"<tr><th>{_texto_de_dado_html(rotulo)}</th><td>{_texto_de_dado_html(valor)}</td></tr>"
                    for rotulo, valor in pares)
    return f'<table class="{classe}"><tbody>{corpo}</tbody></table>'


def _frase_html(dicionario: dict, chave: str) -> str:
    return f'<p>{html.escape(t(dicionario, chave))}</p>'


def _fontes_html(entrega: dict, idioma: str, dicionario: dict) -> str:
    """D7, 1: as identidades distintas, na ordem em que o ledger as cita pela primeira vez,
    com o rótulo de cada classe com que aparecem e o número de registros de cada uma."""
    fontes: dict = {}
    for registro in entrega["ledger"]["registros"]:
        fonte = fontes.setdefault(registro["fonte"]["identidade"], {"classes": [], "registros": 0})
        if registro["fonte"]["classe"] not in fonte["classes"]:
            fonte["classes"].append(registro["fonte"]["classe"])
        fonte["registros"] += 1
    titulo = t(dicionario, "evidencia.fontes_titulo")
    if not fontes:
        return _secao_html("evidencia-fontes", titulo, _frase_html(dicionario, "evidencia.fontes_vazio"))
    colunas = [t(dicionario, f"evidencia.fontes_colunas.{coluna}") for coluna in ("identidade", "classe", "registros")]
    linhas = [[identidade,
               ", ".join(_rotulo_da_evidencia(dicionario, "classes_de_fonte", classe) for classe in fonte["classes"]),
               _contagem(fonte["registros"], idioma)]
              for identidade, fonte in fontes.items()]
    return _secao_html("evidencia-fontes", titulo, _tabela_html("fontes", colunas, linhas))


def _registro_html(registro: dict, idioma: str, dicionario: dict) -> str:
    """D7, 2: um registro, campo a campo, sob o rótulo do dicionário — o vocabulário pelo
    rótulo, o valor só localizado e os textos como a entrega os declara. Campo opcional
    ausente não ganha linha. Os parâmetros do localizador saem como `chave: valor`: com `=`,
    a página escreveria texto que a regra de autocontenção lê como atributo (`data=`)."""
    def _campo(nome: str) -> str:
        return t(dicionario, f"evidencia.registro_campos.{nome}")

    fonte, localizador = registro["fonte"], registro["localizador"]
    moeda = registro["moeda"] if registro["moeda"] is not None else t(dicionario, "evidencia.sem_valor")
    pares = [
        (_campo("id"), registro["id"]),
        (_campo("fonte"), fonte["identidade"]),
        (_campo("classe"), _rotulo_da_evidencia(dicionario, "classes_de_fonte", fonte["classe"])),
        (_campo("estatuto"), _rotulo_da_evidencia(dicionario, "estatutos", registro["estatuto"])),
        (_campo("periodo"), registro["periodo"]),
        (_campo("valor"), _valor_do_registro(registro, idioma, dicionario)),
        (_campo("unidade"), registro["unidade"]),
        (_campo("moeda"), moeda),
        (_campo("data_acesso"), registro["data_acesso"]),
        (_campo("localizador_tipo"), _rotulo_da_evidencia(dicionario, "tipos_de_localizador", localizador["tipo"])),
        (_campo("localizador_valor"), localizador["valor"]),
    ]
    if "parametros" in localizador:
        pares.append((_campo("localizador_parametros"), "; ".join(
            f"{chave}: {_texto_valor(valor)}" for chave, valor in localizador["parametros"].items())))
    pares.append((_campo("justificativa_da_fonte"), registro["justificativa_da_fonte"]))
    if "formula" in registro:
        pares.append((_campo("formula"), registro["formula"]))
    if "insumos" in registro:
        pares.append((_campo("insumos"), ", ".join(registro["insumos"])))
    if "usado_em" in registro:
        pares.append((_campo("usado_em"), ", ".join(registro["usado_em"])))
    if "reconciliacao" in registro:
        pares.append((_campo("reconciliacao"), registro["reconciliacao"]["texto"]))
    if "conflito" in registro:
        pares += [(_campo("conflito_vencedor"), registro["conflito"]["vencedor"]),
                  (_campo("conflito_razao"), registro["conflito"]["razao"])]
    if "contraprova_de" in registro:
        pares.append((_campo("contraprova_de"), registro["contraprova_de"]))
    return _tabela_de_pares_html("registro-do-ledger", pares)


def _ledger_html(entrega: dict, idioma: str, dicionario: dict) -> str:
    """D7, 2: os registros agrupados por `claim`, na ordem em que cada claim aparece pela
    primeira vez — um registro concorrente fica sob o claim que disputa, ao lado do vencedor."""
    grupos: dict = {}
    for registro in entrega["ledger"]["registros"]:
        grupos.setdefault(registro["claim"], []).append(registro)
    titulo = t(dicionario, "evidencia.ledger_titulo")
    if not grupos:
        return _secao_html("evidencia-ledger", titulo, _frase_html(dicionario, "evidencia.ledger_vazio"))
    corpo = "".join(
        f'<div class="ledger-claim"><h3>{_texto_de_dado_html(claim)}</h3>'
        f'{"".join(_registro_html(registro, idioma, dicionario) for registro in registros)}</div>'
        for claim, registros in grupos.items())
    return _secao_html("evidencia-ledger", titulo, corpo)


def _rotulo_limitacao(catalogo: dict, limitacao: Any, idioma: str) -> str:
    """Rótulo de uma limitação publicada (`catalogo.limitacoes.<chave>.rotulo`). O QC já recusa
    a limitação que o catálogo não rotula (`limitacao_desconhecida`, HARD FAIL); aqui, defesa em
    profundidade, nomeada — nunca a chave crua."""
    declaracao = (catalogo.get("limitacoes") or {}).get(limitacao) if isinstance(limitacao, str) else None
    rotulo = ((declaracao or {}).get("rotulo") or {}).get(idioma)
    if not rotulo:
        raise RotuloDoCatalogoAusente(
            f"catálogo de apresentação sem rótulo em '{idioma}' para a limitação '{limitacao}' em 'limitacoes'.")
    return rotulo


def _lacunas_e_limitacoes_html(entrega: dict, catalogo: dict, idioma: str, dicionario: dict, prosa: dict) -> str:
    """D7, 3: as lacunas do ledger — a materialidade rotulada, e a descrição e o tratamento
    resolvidos pela lista de prosa, os mesmos textos que o aviso da Tese exibe —, cada limitação
    de `resultados.limitacoes` com o rótulo do catálogo e a fronteira de escopo com o rótulo da
    classe. Sem nenhuma das três, a frase do dicionário."""
    resultados = entrega["resultados"]
    partes = []
    lacunas = entrega["ledger"]["lacunas"]
    if lacunas:
        colunas = [t(dicionario, f"evidencia.lacunas_colunas.{coluna}")
                   for coluna in ("id", "materialidade", "descricao", "tratamento")]
        linhas = [[lacuna["id"], _rotulo_da_evidencia(dicionario, "materialidades", lacuna["materialidade"]),
                   _prosa(prosa, f"ledger.lacunas.{indice}.descricao"),
                   _prosa(prosa, f"ledger.lacunas.{indice}.tratamento")]
                  for indice, lacuna in enumerate(lacunas)]
        partes.append(f'<h3>{html.escape(t(dicionario, "evidencia.lacunas_do_ledger_titulo"))}</h3>'
                      + _tabela_html("lacunas", colunas, linhas))
    limitacoes = resultados.get("limitacoes") or []
    if limitacoes:
        itens = "".join(f"<li>{html.escape(_rotulo_limitacao(catalogo, limitacao, idioma))}</li>"
                        for limitacao in limitacoes)
        partes.append(f'<h3>{html.escape(t(dicionario, "evidencia.limitacoes_titulo"))}</h3>'
                      f'<ul class="limitacoes">{itens}</ul>')
    fronteira = _campo_de_contrato(resultados, "fronteira_de_escopo", "resultados")
    if fronteira is not None:
        classe = _rotulo_fronteira(
            catalogo, _campo_de_contrato(fronteira, "classe", "resultados.fronteira_de_escopo"), idioma)
        partes.append(f'<h3>{html.escape(t(dicionario, "evidencia.fronteira_titulo"))}</h3>'
                      f'<p class="fronteira-de-escopo">{html.escape(classe)}</p>')
    corpo = "".join(partes) or _frase_html(dicionario, "evidencia.lacunas_vazio")
    return _secao_html("evidencia-lacunas", t(dicionario, "evidencia.lacunas_titulo"), corpo)


def _confronto_html(entrega: dict, dicionario: dict) -> str:
    """D7, 4 (§12, decisão 20): a análise fornecida — identificação e data — e cada divergência
    com o item, a classificação rotulada, o anterior, o atual e a explicação. Só quando a
    entrega traz o confronto: nenhuma seção vazia."""
    confronto = entrega.get("confronto")
    if not isinstance(confronto, dict):
        return ""
    fornecida = confronto["analise_fornecida"]
    cabecalho = t(dicionario, "evidencia.confronto_analise_fornecida",
                  identificacao=fornecida["identificacao"], data=fornecida["data"])
    partes = [f'<p class="confronto-analise-fornecida">{_texto_de_dado_html(cabecalho)}</p>']
    if confronto["divergencias"]:
        colunas = [t(dicionario, f"evidencia.confronto_colunas.{coluna}")
                   for coluna in ("item", "classificacao", "anterior", "atual", "explicacao")]
        linhas = [[divergencia["item"],
                   _rotulo_da_evidencia(dicionario, "classificacoes_de_divergencia", divergencia["classificacao"]),
                   divergencia["anterior"], divergencia["atual"], divergencia["explicacao"]]
                  for divergencia in confronto["divergencias"]]
        partes.append(_tabela_html("confronto-divergencias", colunas, linhas))
    else:
        partes.append(_frase_html(dicionario, "evidencia.confronto_sem_divergencias"))
    return _secao_html("evidencia-confronto", t(dicionario, "evidencia.confronto_titulo"), "".join(partes))


def _ficha_tecnica_html(ficha: dict | None, idioma: str, dicionario: dict) -> str:
    """D7, 5 (D6): a ficha técnica que o builder compôs (`builder.compor_ficha_tecnica`), bloco a
    bloco, sob os rótulos do dicionário — os campos da execução, da metodologia e dos contratos;
    as contagens de registros, pelo rótulo do vocabulário; os achados por nível, com o código e a
    quantidade, sem o nível interno (`NIVEL_INTERNO_DO_QC`). Sem ficha — um chamador direto deste
    módulo, que não passou pelo builder —, a frase do dicionário."""
    titulo = t(dicionario, "evidencia.ficha_tecnica_titulo")
    if ficha is None:
        return _secao_html("ficha-tecnica-bloco", titulo, _frase_html(dicionario, "evidencia.ficha_tecnica_vazia"))
    grupos = []
    for bloco, conteudo in ficha.items():
        if bloco == BLOCO_DOS_ACHADOS_DA_FICHA:
            nenhum = t(dicionario, "evidencia.ficha_tecnica_nenhum_achado")
            pares = [(t(dicionario, f"evidencia.ficha_tecnica_niveis.{nivel}"),
                      "; ".join(t(dicionario, "evidencia.ficha_tecnica_contagem", codigo=codigo,
                                  quantidade=_contagem(quantidade, idioma))
                                for codigo, quantidade in codigos.items()) or nenhum)
                     for nivel, codigos in conteudo.items() if nivel != NIVEL_INTERNO_DO_QC]
        elif bloco in VOCABULARIO_DOS_BLOCOS_DE_CONTAGEM:
            pares = [(_rotulo_da_evidencia(dicionario, VOCABULARIO_DOS_BLOCOS_DE_CONTAGEM[bloco], codigo),
                      _contagem(quantidade, idioma))
                     for codigo, quantidade in conteudo.items()]
        else:
            pares = [(t(dicionario, f"evidencia.ficha_tecnica_campos.{bloco}.{campo}"), _texto_valor(valor))
                     for campo, valor in conteudo.items()]
        titulo_do_bloco = t(dicionario, f"evidencia.ficha_tecnica_blocos.{bloco}")
        grupos.append(f'<div class="ficha-tecnica-grupo"><h3>{html.escape(titulo_do_bloco)}</h3>'
                      f'{_tabela_de_pares_html("ficha-tecnica", pares)}</div>')
    return _secao_html("ficha-tecnica-bloco", titulo, "".join(grupos))


def _metodologia_html(resultados: dict, dicionario: dict) -> str:
    metodologia = resultados["origem"]["metodologia"]
    nome = _texto_de_dado_html(str(metodologia.get("nome", "")))
    versao = _texto_de_dado_html(str(metodologia.get("versao", "")))
    return (
        f'<section class="metodologia">'
        f'<h2>{html.escape(t(dicionario, "evidencia.metodologia_titulo"))}</h2>'
        f'<p>{t(dicionario, "evidencia.metodologia_valor", nome=nome, versao=versao)}</p>'
        f'</section>'
    )


def _evidencia_html(entrega: dict, catalogo: dict, log: list, log_exhibits: list, idioma: str,
                    dicionario: dict, prosa: dict, ficha_tecnica: dict | None) -> str:
    """A aba inteira, na ordem de D7."""
    return (_fontes_html(entrega, idioma, dicionario)
            + _ledger_html(entrega, idioma, dicionario)
            + _lacunas_e_limitacoes_html(entrega, catalogo, idioma, dicionario, prosa)
            + _confronto_html(entrega, dicionario)
            + _ficha_tecnica_html(ficha_tecnica, idioma, dicionario)
            + _metodologia_html(entrega["resultados"], dicionario)
            + _log_html(log, dicionario)
            + _rastreabilidade_exhibits_html(log_exhibits, dicionario))


def _log_html(log: list, dicionario: dict) -> str:
    """O log de resolução dos placeholders de toda a prosa (a conclusão até a 5D, Task 3; desde
    então, também os textos da Tese, do consenso ausente, das lacunas e dos exhibits), em tabela."""
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
            f'<td>{_texto_de_dado_html(_texto_valor(entrada.get("onde")))}</td>'
            f'<td>{_texto_de_dado_html(_texto_valor(entrada.get("tipo")))}</td>'
            f'<td>{_texto_de_dado_html(_texto_valor(entrada.get("caminho")))}</td>'
            f'<td>{_texto_de_dado_html(_texto_valor(entrada.get("formato")))}</td>'
            f'<td>{_texto_de_dado_html(_texto_valor(entrada.get("bruto")))}</td>'
            f'<td>{_texto_de_dado_html(_texto_valor(entrada.get("resolvido")))}</td>'
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

    return bloco_log


def _ler_asset(nome: str) -> str:
    """Lê um asset PRÓPRIO do skill (`assets/<nome>`) como texto -- usado só
    para os vendorizados/adaptador do uPlot (Task 2). Nunca a integração
    (E3): estes arquivos vivem em `skills/er-relatorio/assets/`, o mesmo
    diretório de `template.html`/`i18n/`."""
    return (_DIR_ASSETS / nome).read_text(encoding="utf-8")


def compor(entrega: dict, catalogo: dict, achados: list, log: list, idioma: str,
           exhibits_resolvidos: list | None = None, log_exhibits: list | None = None,
           js_da_integracao: dict | None = None, ficha_tecnica: dict | None = None) -> str:
    """Compõe o HTML autocontido das três abas a partir só dos contratos já
    carregados/validados por quem chama (`builder.py`).

    `achados`: a lista de `qc.Achado` que `qc.avaliar` já produziu — a Tese
    mostra só os de nível REQUIRED_DISCLOSURE (HARD_FAIL nunca chega aqui,
    regra inviolável 2; QUALITY_WARNING nunca aparece no HTML). `log`: o
    log de resolução dos placeholders de TODA a prosa, como
    `placeholders.resolver_prosa` o devolve (até a 5D, Task 3, só o da
    conclusão), exibido em tabela na Evidência — o texto que a Tese exibe sai
    da mesma lista.

    `exhibits_resolvidos`/`log_exhibits` (fatia 5B, item 5, Task 2): o que
    `exhibits.resolver(entrega)` devolve -- `builder.py` chama isso UMA
    única vez (depois que a primeira passada do QC já confirmou zero HARD
    FAIL) e passa o resultado para cá; este módulo NUNCA chama `exhibits.
    resolver` de novo (nem importa `exhibits.py` -- só lê as chaves que a
    série/overlay já resolvida carrega). Omissos (`None`, o padrão):
    equivalem a uma entrega sem exhibit nenhum (`[]`/`[]`) -- preserva todo
    chamador existente (`tests/test_relatorio_render.py`, anterior a esta
    fatia) sem precisar tocar nele.

    `js_da_integracao` (fatia 5C, item 5, Task 2): `{"espelho": <texto>,
    "fachada": <texto>}`, LIDOS por `builder.py` de `ASSETS_DA_INTEGRACAO` --
    o único caminho deste pacote para dentro da integração (E3). Omisso
    (`None`, o padrão): a página sai SEM laboratório, exatamente como antes
    desta fatia -- um painel editável sem o motor que o alimenta seria
    interface morta, então o painel e os dois `<script>` entram ou não
    entram juntos.

    Determinístico por construção: mesma entrada, mesmos bytes — nenhuma
    ordem de `set` não determinística, nenhum relógio, nenhum caminho
    absoluto no HTML emitido, nenhuma id gerada em tempo de execução.

    `ficha_tecnica` (fatia 5E, Task 3, D6): a ficha da execução que
    `builder.compor_ficha_tecnica` compôs — a mesma que o builder grava em
    `ficha-tecnica.json` —, exibida na Evidência. Omissa (`None`, o padrão),
    a seção diz que não há dado técnico: é o caso de um chamador direto deste
    módulo, que não passou pelo builder.
    """
    exhibits_resolvidos = exhibits_resolvidos if exhibits_resolvidos is not None else []
    log_exhibits = log_exhibits if log_exhibits is not None else []

    dicionario = placeholders.carregar_dicionario(idioma)

    execucao = entrega["execucao"]
    caso = entrega["caso"]
    resultados = entrega["resultados"]
    dados = entrega.get("dados") or {}

    empresa = _texto_de_dado_html(str(caso.get("companhia", "")))
    ticker = _texto_de_dado_html(str(execucao.get("ticker", "")))
    titulo = t(dicionario, "titulo_pagina", empresa=empresa, ticker=ticker)

    laboratorio = (_laboratorio_para_json(caso, resultados, catalogo, idioma, dicionario)
                   if js_da_integracao else None)

    # Fatia 5D, Task 3: todo texto de `analise` que a Tese exibe sai daqui — a
    # mesma lista de prosa que o QC varreu e que o `log` da Evidência registra.
    prosa, _log_da_prosa = placeholders.resolver_prosa(entrega, idioma)
    corpo_tese = _tese_html(entrega, catalogo, achados, idioma, dicionario, titulo, prosa, exhibits_resolvidos)
    corpo_valuation = _valuation_html(entrega, catalogo, idioma, dicionario, prosa,
                                       com_laboratorio=laboratorio is not None)
    corpo_evidencia = _evidencia_html(entrega, catalogo, log, log_exhibits, idioma, dicionario, prosa,
                                      ficha_tecnica)

    # Os painéis SVG da Valuation entram no MESMO `<script type="application/
    # json">` dos exhibits (uma chave a mais, `paineis_valuation`) — nunca um
    # segundo bloco e nunca um segundo caminho de escape: `_json_embutido` é
    # a única porta de saída de JSON deste módulo.
    paineis_valuation = _paineis_valuation_para_json(caso, resultados, catalogo, idioma, dicionario)
    dados_exhibits = _json_embutido({
        "formatacao": _formatacao_grafico(dicionario),
        "exhibits": [_exhibit_para_json(exhibit, indice, dados, prosa)
                     for indice, exhibit in enumerate(exhibits_resolvidos)],
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

    # O laboratório (Task 2) paga ~110 KB de espelho + fachada; como o uPlot e
    # o `svg.js`, só entra na página quando há painel para alimentar. Os dois
    # módulos da integração chegam como TEXTO, lidos por `builder.py` de
    # `ASSETS_DA_INTEGRACAO` -- este módulo nunca os localiza no disco, nunca
    # os copia para `assets/` e nunca os interpreta. `laboratorio.js` é asset
    # PRÓPRIO do relatório (só interface) e entra pelo mesmo `_ler_asset` do
    # `svg.js`. Tudo isso entra como VALOR de `string.Template.substitute`,
    # nunca colado no template: os três arquivos têm `$` no corpo, e um
    # `$nome` colado no modelo seria lido como marcador.
    if laboratorio is not None:
        js_espelho = js_da_integracao["espelho"]
        js_fachada = js_da_integracao["fachada"]
        js_laboratorio = _ler_asset("laboratorio.js")
        dados_laboratorio = _json_embutido(laboratorio)
    else:
        js_espelho = js_fachada = js_laboratorio = ""
        dados_laboratorio = _json_embutido(None)

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
        js_espelho=js_espelho,
        js_fachada=js_fachada,
        js_laboratorio=js_laboratorio,
        dados_laboratorio=dados_laboratorio,
    )
