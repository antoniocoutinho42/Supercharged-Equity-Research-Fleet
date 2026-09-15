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


def _rotulo_do_vinculo(catalogo: dict, rota: str, item: str, idioma: str) -> str:
    """Rótulo de um item de vínculo ou de mecanismo da Tese (D2): premissa da rota
    (`_rotulo_premissa`) ou bloco econômico (`_rotulo_bloco`). O QC já recusa item
    fora dos dois antes de renderizar (`vinculo_fora_do_vocabulario`, HARD FAIL);
    aqui, defesa em profundidade, nomeada."""
    if item in ((catalogo.get("premissas") or {}).get(rota) or {}):
        return _rotulo_premissa(catalogo, rota, item, idioma)
    if item in (catalogo.get("blocos") or {}):
        return _rotulo_bloco(catalogo, item, idioma)
    raise RotuloDoCatalogoAusente(
        f"catálogo de apresentação sem '{item}' entre as premissas da rota '{rota}' e os "
        "blocos econômicos — um vínculo nunca aparece pela chave crua."
    )


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
    partes = [f'<{tag_titulo}>{html.escape(_prosa(prosa, onde + ".pergunta"))}</{tag_titulo}>']
    if exhibit.get("nota_janela"):
        partes.append(f'<p class="exhibit-nota-janela">{html.escape(_prosa(prosa, onde + ".nota_janela"))}</p>')
    partes.append(f'<div class="exhibit-grafico" data-exhibit-indice="{indice}"></div>')
    if exhibit.get("caption"):
        partes.append(f'<p class="exhibit-caption">{html.escape(_prosa(prosa, onde + ".caption"))}</p>')
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
    return f'<span class="{classe}">{html.escape(texto)}</span>'


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


def _rotulos_do_valuation_html(itens: list, catalogo: dict, rota: str, idioma: str) -> str:
    """O vínculo de uma pergunta, ou o mecanismo de um Positive/Negative (D2):
    cada item pelo rótulo do catálogo."""
    return " ".join(_valor_html("tese-rotulo", _rotulo_do_vinculo(catalogo, rota, item, idioma))
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
    return (f'<div class="tese-faixa"><p class="tese-faixa-rotulo">{html.escape(rotulo)}</p>'
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
        f'<p class="tese-veredicto-texto">{html.escape(_prosa(prosa, "analise.veredicto.texto"))}</p>'
        f'<p class="tese-preco-de-tela">{html.escape(tela)}</p>'
        '</div>'
    )


def _conclusao_html(entrega: dict, catalogo: dict, idioma: str, dicionario: dict, prosa: dict) -> str:
    """A Conclusão (D7). Sob fronteira de escopo (D3) o título é o condicional,
    sem preço-alvo, com a classe, a arquitetura dominante e a razão — e a faixa
    não é desenhada: o contrato já a proíbe, e este módulo não a desenharia nem
    se ela chegasse."""
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
        f'<p class="conclusao-texto">{html.escape(_prosa(prosa, "analise.conclusao.texto"))}</p>'
        f'{bloco_faixa}'
        f'{_veredicto_html(caso, idioma, moeda, dicionario, prosa)}'
        f'<div class="tese-multiplos">'
        f'{_multiplos_html(resultados, catalogo, idioma, dicionario, omitir_conclusao_de_valor=True)}</div>'
        '</section>'
    )


def _disclosures_html(achados: list, dicionario: dict) -> str:
    """Todo achado REQUIRED_DISCLOSURE, visível, com a mensagem do dicionário — a
    de uma limitação da reversa carrega o rótulo do catálogo que o QC pôs nos
    params."""
    disclosures = [a for a in achados if a.nivel == "REQUIRED_DISCLOSURE"]
    titulo = html.escape(t(dicionario, "tese.disclosures_titulo"))
    if disclosures:
        itens = "".join(f"<li>{html.escape(_mensagem_qc(a, dicionario))}</li>" for a in disclosures)
        return f'<section class="disclosures"><h2>{titulo}</h2><ul>{itens}</ul></section>'
    vazio = html.escape(t(dicionario, "tese.disclosures_vazio"))
    return f'<section class="disclosures disclosures-vazio"><h2>{titulo}</h2><p>{vazio}</p></section>'


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
    Premissa endereçável por parte é da 5F."""
    rota = _campo_de_contrato(resultados, "rota", "resultados")
    nome = _campo_de_contrato(_campo_de_contrato(resultados, "manchete", "resultados"),
                              "cenario", "resultados.manchete")
    cenario = _campo_de_contrato(_campo_de_contrato(resultados, "cenarios", "resultados"),
                                 nome, "resultados.cenarios")
    premissas = _campo_de_contrato(cenario, "premissas", f"resultados.cenarios.{nome}")
    itens = []
    for indice, declarada in enumerate(analise["premissas_decisivas"]):
        chave = declarada["chave"]
        rotulo = _rotulo_premissa(catalogo, rota, chave, idioma)
        valor = _valor_exibido_da_premissa(
            catalogo["premissas"][rota][chave],
            _campo_de_contrato(premissas, chave, f"resultados.cenarios.{nome}.premissas"),
            catalogo, idioma, moeda, dicionario)
        derivacao = _prosa(prosa, f"analise.premissas_decisivas.{indice}.derivacao")
        itens.append(
            '<li class="tese-premissa"><div class="metrica">'
            + _valor_html("metrica-rotulo", rotulo)
            + _valor_html("metrica-valor", valor)
            + f'</div><p class="tese-derivacao">{html.escape(derivacao)}</p></li>'
        )
    rotulo_do_consolidado = ""
    if _manchete_vem_do_sotp(resultados):
        rotulo_do_consolidado = (
            '<p class="tese-premissas-rotulo">'
            f'{html.escape(t(dicionario, "tese.premissas_decisivas_rotulo_consolidado", cenario=nome))}</p>')
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
        linhas.append(f"<li>{html.escape(linha)}</li>")
    return _secao_html("tese-o-que-mudou", t(dicionario, "tese.o_que_mudou_titulo"), f'<ul>{"".join(linhas)}</ul>')


def _item_do_valuation_html(lado: str, indice: int, item: dict, catalogo: dict, rota: str, idioma: str,
                             dicionario: dict, prosa: dict) -> str:
    """Um Positive ou Negative (§9): a afirmação, o vetor que atinge, o mecanismo
    do valuation que move, o observável que o confirma ou o mata, e se ele está
    refletido no valuation ou declarado como não incorporado — com a razão."""
    onde = f"analise.{lado}.{indice}"
    linhas = [
        f'<p class="tese-afirmacao">{html.escape(_prosa(prosa, onde + ".afirmacao"))}</p>',
        _atributo_html(t(dicionario, "tese.vetor"),
                       _valor_html("tese-vetor", _rotulo_de_vocabulario(dicionario, "tese.vetores", item["vetor"]))),
        _atributo_html(t(dicionario, "tese.mecanismo"),
                       _rotulos_do_valuation_html(item["mecanismo"], catalogo, rota, idioma)),
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


def _positives_negatives_html(analise: dict, catalogo: dict, rota: str, idioma: str, dicionario: dict,
                               prosa: dict) -> str:
    lados = []
    for lado, titulo in (("positives", t(dicionario, "tese.positives_titulo")),
                         ("negatives", t(dicionario, "tese.negatives_titulo"))):
        itens = [_item_do_valuation_html(lado, indice, item, catalogo, rota, idioma, dicionario, prosa)
                 for indice, item in enumerate(analise[lado])]
        lados.append(f'<div class="tese-lado"><h3>{html.escape(titulo)}</h3>{_lista_html(itens, dicionario)}</div>')
    return _secao_html("tese-positives-negatives", t(dicionario, "tese.positives_negatives_titulo"),
                       f'<div class="tese-lados">{"".join(lados)}</div>')


def _pergunta_html(indice: int, pergunta: dict, catalogo: dict, rota: str, idioma: str, dicionario: dict,
                    prosa: dict, exhibits_resolvidos: list, indice_por_id: dict) -> str:
    """Uma pergunta da tese (§7, §10): o tema, a pergunta, a evidência, o
    observável que a falsificaria, o vínculo com o valuation e — D5 — os exhibits
    que ela cita, na ordem em que os cita, ou a razão de nenhum acrescentar."""
    onde = f"analise.perguntas.{indice}"
    tema = _rotulo_de_vocabulario(dicionario, "tese.temas", pergunta["tema"])
    linhas = [
        f'<p class="tese-tema">{html.escape(tema)}</p>',
        f'<h3>{html.escape(_prosa(prosa, onde + ".pergunta"))}</h3>',
        _atributo_html(t(dicionario, "tese.evidencia"),
                       _valor_html("tese-evidencia", _prosa(prosa, onde + ".evidencia"))),
        _atributo_html(t(dicionario, "tese.observavel_pergunta"),
                       _valor_html("tese-observavel", _prosa(prosa, onde + ".observavel"))),
        _atributo_html(t(dicionario, "tese.vinculo"),
                       _rotulos_do_valuation_html(pergunta["vinculo"], catalogo, rota, idioma)),
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
            f'<li class="tese-item"><p class="tese-risco">{html.escape(_prosa(prosa, onde + ".risco"))}</p>'
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
                       f"<p>{html.escape(texto)}</p>")


def _tese_html(entrega: dict, catalogo: dict, achados: list, idioma: str, dicionario: dict, titulo: str,
               prosa: dict, exhibits_resolvidos: list) -> str:
    """A aba inteira, na ordem de D7. `exhibits_resolvidos` é a lista que o
    builder resolveu uma vez: cada exhibit é desenhado sob as perguntas que o
    citam, pelo índice do seu id nessa lista — o mesmo índice da sua spec no
    payload —, e o que nenhuma pergunta cita vai para a seção final."""
    analise, resultados = entrega["analise"], entrega["resultados"]
    rota = _campo_de_contrato(resultados, "rota", "resultados")
    moeda = entrega["caso"].get("moeda")
    indice_por_id = {exhibit["id"]: indice for indice, exhibit in enumerate(exhibits_resolvidos)}
    citados = {indice_por_id[exhibit_id] for pergunta in analise["perguntas"]
               for exhibit_id in pergunta.get("exhibits", []) if exhibit_id in indice_por_id}
    perguntas = "".join(
        _pergunta_html(indice, pergunta, catalogo, rota, idioma, dicionario, prosa, exhibits_resolvidos,
                       indice_por_id)
        for indice, pergunta in enumerate(analise["perguntas"]))
    return (
        f'<h1>{titulo}</h1>'
        + _conclusao_html(entrega, catalogo, idioma, dicionario, prosa)
        + _disclosures_html(achados, dicionario)
        + _premissas_decisivas_html(analise, resultados, catalogo, idioma, moeda, dicionario, prosa)
        + _o_que_mudou_html(analise, dicionario, prosa)
        + _positives_negatives_html(analise, catalogo, rota, idioma, dicionario, prosa)
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
        titulo = html.escape(_rotulo_do_numero(
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


def _valor_exibido_da_premissa(info: dict, valor: Any, catalogo: dict, idioma: str,
                                moeda: str | None, dicionario: dict) -> str:
    """O valor ORIGINAL, legível, que fica ao lado do campo editável (L6).
    Número passa pela unidade que o catálogo declara (a mesma disciplina de
    `_espec_de_formato_da_unidade`/A4 — nunca "2 casas e nada mais"); opção de
    escolha vira o rótulo da opção; booleano vira sim/não do dicionário."""
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
    return placeholders.formatar(
        valor, _formato_da_unidade(catalogo, info.get("unidade")), idioma, moeda)


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
            f'{html.escape((rotulos.get(opcao) or {}).get(idioma) or str(opcao))}</option>'
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
                           moeda: str | None, dicionario: dict) -> tuple[str, str | None]:
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
        rotulo = html.escape(
            ((info.get("rotulo") or {}).get(idioma) or chave) if info else chave)
        return (
            f'<div class="lab-campo lab-campo-travado" data-laboratorio-premissa="{html.escape(chave)}">'
            f'<label for="{identificador}">{rotulo}</label>'
            f'<input id="{identificador}" type="text" value="{bruto}" disabled>'
            f'<span class="lab-nota">{nota}</span>'
            f'</div>'
        ), None
    rotulo = html.escape(_rotulo_premissa(catalogo, rota, chave, idioma))
    original = html.escape(t(
        dicionario, "valuation.laboratorio_original",
        valor=_valor_exibido_da_premissa(info, valor, catalogo, idioma, moeda, dicionario)))
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
                                  moeda: str | None, dicionario: dict, rotulos_das_saidas: dict) -> str:
    campos_por_bloco: dict[str, list] = {}
    travados: list[str] = []
    for posicao, (chave, valor) in enumerate(premissas.items()):
        campo, bloco = _campo_do_laboratorio(
            rota, chave, valor, premissas_catalogo.get(chave), f"lab-{indice}-{posicao}",
            catalogo, idioma, moeda, dicionario)
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

    titulo = html.escape(t(dicionario, "valuation.laboratorio_cenario_titulo", cenario=nome))
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
            catalogo, idioma, moeda, dicionario, rotulos_das_saidas)
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
    em outra unidade, e a Tese fica só com a leitura de mercado que a §14 mantém."""
    manchete = resultados["manchete"]
    if "multiplo" not in manchete:
        return f'<p class="sotp-nota">{html.escape(t(dicionario, "valuation.sotp_sem_multiplo"))}</p>'
    lados = (
        ("multiplo_justo_titulo", CAMINHO_DO_MULTIPLO_DA_MANCHETE, manchete["multiplo"]),
        ("multiplo_tela_titulo", CAMINHO_DO_MULTIPLO_DE_TELA, resultados["mercado_tela"]),
    )
    blocos = []
    for chave_do_rotulo, caminho, multiplo in lados:
        if omitir_conclusao_de_valor and _leitura_condicional(resultados, catalogo, caminho):
            continue
        rotulo = _rotulo_do_numero(resultados, catalogo, dicionario, chave_do_rotulo, caminho)
        valor_fmt = placeholders.formatar(multiplo["valor"], "x2", idioma)
        blocos.append(
            f'<div class="metrica">'
            f'<span class="metrica-rotulo">{html.escape(rotulo)}</span>'
            f'<span class="metrica-valor">{html.escape(valor_fmt)}</span>'
            f'<span class="metrica-nota">{html.escape(_rotulo_multiplo(catalogo, multiplo["chave"], idioma))}</span>'
            f'</div>'
        )
    return "".join(blocos)


def _valuation_html(caso: dict, resultados: dict, catalogo: dict, idioma: str, dicionario: dict,
                     com_laboratorio: bool = False) -> str:
    moeda = caso.get("moeda")
    manchete = resultados["manchete"]

    preco_fmt = html.escape(placeholders.formatar(manchete["preco_acao"], "moeda", idioma, moeda))
    upside_fmt = html.escape(placeholders.formatar(manchete["upside"], "pct1", idioma))
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

    cenarios = resultados.get("cenarios") or {}
    if len(cenarios) > 1:
        linhas = "".join(
            f'<li><strong>{html.escape(str(nome))}</strong>: '
            f'{html.escape(placeholders.formatar(dados["valor"]["preco_acao"], "moeda", idioma, moeda))}</li>'
            for nome, dados in cenarios.items()
        )
        titulo_dos_cenarios = _rotulo_do_numero(resultados, catalogo, dicionario, "cenarios_titulo",
                                                CAMINHO_DOS_PRECOS_POR_CENARIO)
        bloco_cenarios = (
            f'<section class="cenarios">'
            f'<h2>{html.escape(titulo_dos_cenarios)}</h2>'
            f'<ul>{linhas}</ul>'
            f'</section>'
        )
    else:
        bloco_cenarios = ""

    laboratorio = (_laboratorio_html(caso, resultados, catalogo, idioma, dicionario)
                   if com_laboratorio else "")
    return (
        f'<section class="valuation-cabecalho">{cabecalho}</section>'
        f'{nota_manchete}'
        f'<section class="valuation-multiplos">{bloco_multiplos}</section>'
        f'<section class="valuation-rota">{bloco_rota}</section>'
        f'{bloco_cenarios}'
        f'{_paineis_valuation_html(caso, resultados, catalogo, idioma, dicionario)}'
        f'{laboratorio}'
    )


# --------------------------------------------------------------------------
# Aba Evidência: metodologia (`resultados.origem.metodologia`), a ficha
# técnica e o log de resolução dos placeholders de toda a prosa (a conclusão
# até a 5D, Task 3; desde então, também os textos da Tese e dos exhibits), em
# tabela. Fatia 5E, Task 2 (D6): `ficha_tecnica` saiu do contrato `entrega/1`
# — a ficha é da execução, e quem a compõe é o builder (Task 3) —, e até lá a
# seção sai vazia, sem ler nada da entrega.
# --------------------------------------------------------------------------

def _evidencia_html(resultados: dict, log: list, log_exhibits: list, idioma: str, dicionario: dict) -> str:
    metodologia = resultados["origem"]["metodologia"]
    nome = html.escape(str(metodologia.get("nome", "")))
    versao = html.escape(str(metodologia.get("versao", "")))
    bloco_metodologia = (
        f'<section class="metodologia">'
        f'<h2>{html.escape(t(dicionario, "evidencia.metodologia_titulo"))}</h2>'
        f'<p>{t(dicionario, "evidencia.metodologia_valor", nome=nome, versao=versao)}</p>'
        f'</section>'
    )

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
           exhibits_resolvidos: list | None = None, log_exhibits: list | None = None,
           js_da_integracao: dict | None = None) -> str:
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

    laboratorio = (_laboratorio_para_json(caso, resultados, catalogo, idioma, dicionario)
                   if js_da_integracao else None)

    # Fatia 5D, Task 3: todo texto de `analise` que a Tese exibe sai daqui — a
    # mesma lista de prosa que o QC varreu e que o `log` da Evidência registra.
    prosa, _log_da_prosa = placeholders.resolver_prosa(entrega, idioma)
    corpo_tese = _tese_html(entrega, catalogo, achados, idioma, dicionario, titulo, prosa, exhibits_resolvidos)
    corpo_valuation = _valuation_html(caso, resultados, catalogo, idioma, dicionario,
                                       com_laboratorio=laboratorio is not None)
    corpo_evidencia = _evidencia_html(resultados, log, log_exhibits, idioma, dicionario)

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
