"""Contrato de `entrega.json` (fatia 5A, item 5, Task 3, decisão A1;
estendido na fatia 5B, item 5, Task 1, G1/G3: `dados` no topo, `exhibits`
em `analise`).

Este módulo NÃO importa nada de `er-valuation` nem do vendor (E3,
`docs/desenho-arquitetura-v4.md` §15) — `caso` e `resultados` chegam aqui
como dicts OPACOS. `carregar` confirma que os dois são objetos e que
`resultados.versao_contrato` é o esperado, mas NUNCA revalida o conteúdo
deles: isso é responsabilidade de `caso.py`/`avaliar.py`, na camada de
integração, que este módulo nunca importa — reimplementar aquela validação
aqui seria exatamente a duplicação que a emenda proíbe. `sha256_canonico`
é a única exceção deliberada: duplica, em três linhas, a MESMA receita de
canonicalização que `avaliar.py` já usa (A2) — o preço de o relatório
provar correspondência com `resultados.origem.caso_sha256` sem nunca
importar o módulo que o calculou primeiro.

`dados`/`exhibits`, ao contrário de `caso`/`resultados`, são vocabulário
PRÓPRIO deste contrato (G1/G3 do plano da 5B) — o conteúdo profundo deles é
validado por `exhibits.py` (`validar_dados`/`validar_exhibits`), nunca
duplicado aqui; este módulo só chama e relança `exhibits.
ContratoDeExhibitInvalido` como `EntregaInvalida`, para que a recusa
continue tendo a mesma forma (código 1) que todo o resto do contrato. Ver
o docstring de `exhibits.py` para o porquê de a dependência ir só nesta
direção (`entrega.py` -> `exhibits.py`, nunca de volta).

`carregar` é o único ponto de entrada deste módulo: lê `<raiz>/entrega.json`,
confirma que o arquivo resolve DENTRO da raiz de execução (regra
inviolável 6), valida o contrato (vocabulário fechado em todo nível que
este contrato define, versão da entrega, versão do sub-contrato de
`resultados`, idioma com dicionário publicado) e devolve o dict. Nunca
escreve nada — quem escreve é `builder.py`.
"""

import difflib
import hashlib
import json
from pathlib import Path
from typing import Any

import exhibits

Entrega = dict[str, Any]


class EntregaInvalida(Exception):
    """Levantada quando `entrega.json` está ausente, malformado, fora da
    raiz de execução, ou fora do vocabulário/versão do contrato `entrega/1`.

    Nunca levantada via `assert`, e nunca seguida de `sys.exit` dentro deste
    módulo — quem decide o exit code do processo é o CLI de `builder.py`,
    mesma disciplina de `caso.CasoInvalido` em `er-valuation`.
    """


# --------------------------------------------------------------------------
# Vocabulário fechado do contrato `entrega/1` — todo nível que ESTE
# contrato define (A1). `caso` e `resultados` não ganham vocabulário aqui:
# o conteúdo deles pertence ao contrato de `caso.json`/`resultados.json`
# publicado por `er-valuation` (E3) — este módulo só confirma tipo e, para
# `resultados`, a versão do sub-contrato. `ledger`/`ficha_tecnica` só têm o
# tipo confirmado nesta fatia (a 5D detalha o conteúdo dos dois).
#
# `dados` (5B, G3) é NOVO e OPCIONAL na raiz — por isso fica de fora de
# `CHAVES_DE_TOPO_OBRIGATORIAS` (uma entrega cujos exhibits são só `engine`
# não precisa de `dados` nenhum: `engine` lê `resultados` direto, nunca um
# dataset local). `exhibits` (5B, G1) é NOVO em `analise`, mas OBRIGATÓRIO
# lá (mesma disciplina de `ledger`/`ficha_tecnica`: sempre presente, lista
# vazia quando a análise não tem exhibit nenhum -- G10 do desenho, "não há
# gráfico obrigatório").
# --------------------------------------------------------------------------

VERSAO_CONTRATO: str = "entrega/1"
VERSAO_CONTRATO_RESULTADOS: str = "resultados/1"

CHAVES_DE_TOPO: frozenset = frozenset({
    "versao_contrato", "execucao", "caso", "resultados", "analise", "ledger", "ficha_tecnica", "dados",
})
CHAVES_DE_TOPO_OBRIGATORIAS: frozenset = CHAVES_DE_TOPO - {"dados"}

CHAVES_DE_EXECUCAO: frozenset = frozenset({"id", "ticker", "idioma"})
CHAVES_DE_ANALISE: frozenset = frozenset({"conclusao", "exhibits"})
CHAVES_DE_CONCLUSAO: frozenset = frozenset({"texto"})

# Dicionários de interface/QC deste skill: asset PRÓPRIO do er-relatorio,
# não da integração — E3 só proíbe importar código/dado de er-valuation ou
# do vendor; o dicionário do próprio relatório mora aqui e é lido direto.
_DIR_I18N: Path = Path(__file__).resolve().parent.parent / "assets" / "i18n"


def sha256_canonico(obj: Any) -> str:
    """SHA-256 do JSON canônico de `obj` (A2): `sort_keys=True`,
    `separators=(",", ":")`, `ensure_ascii=False`, utf-8.

    Mesma receita, byte a byte, de `avaliar._sha256_canonico` em
    `er-valuation` — duplicada de propósito (E3): reordenar chaves ou mudar
    espaçamento do `caso.json` de origem não muda o hash em nenhum dos dois
    lados, e o relatório prova correspondência com
    `resultados.origem.caso_sha256` sem nunca importar o módulo que o
    calculou primeiro.
    """
    canonico = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonico.encode("utf-8")).hexdigest()


def _recusar_chave_desconhecida(objeto: dict, permitidas: frozenset, onde: str) -> None:
    """Recusa qualquer chave de `objeto` fora de `permitidas`, nomeando-a —
    mesma disciplina de `caso._validar_sem_chaves_de_topo_desconhecidas`:
    chave fora do vocabulário é quase sempre nome digitado errado, nunca
    extensão silenciosa do contrato.
    """
    desconhecidas = sorted(set(objeto) - permitidas)
    if not desconhecidas:
        return
    chave = desconhecidas[0]
    sugestao = difflib.get_close_matches(chave, sorted(permitidas), n=1)
    dica = f" Você quis dizer '{sugestao[0]}'? " if sugestao else " "
    raise EntregaInvalida(
        f"chave desconhecida em '{onde}': '{chave}'.{dica}"
        f"Chaves aceitas: {', '.join(sorted(permitidas))}."
    )


def _exigir_objeto(valor: Any, campo: str) -> dict:
    if not isinstance(valor, dict):
        raise EntregaInvalida(f"'{campo}' não é um objeto: {valor!r}.")
    return valor


def _exigir_texto_nao_vazio(valor: Any, campo: str) -> str:
    if not isinstance(valor, str) or not valor.strip():
        raise EntregaInvalida(f"'{campo}' ausente ou vazio: {valor!r}.")
    return valor


def _validar_execucao(execucao: Any) -> None:
    execucao = _exigir_objeto(execucao, "execucao")
    _recusar_chave_desconhecida(execucao, CHAVES_DE_EXECUCAO, "execucao")
    for campo in sorted(CHAVES_DE_EXECUCAO):
        if campo not in execucao:
            raise EntregaInvalida(f"campo obrigatório ausente em 'execucao': '{campo}'.")

    _exigir_texto_nao_vazio(execucao["id"], "execucao.id")
    _exigir_texto_nao_vazio(execucao["ticker"], "execucao.ticker")
    idioma = _exigir_texto_nao_vazio(execucao["idioma"], "execucao.idioma")

    if not (_DIR_I18N / f"{idioma}.json").exists():
        disponiveis = sorted(p.stem for p in _DIR_I18N.glob("*.json"))
        raise EntregaInvalida(
            f"'execucao.idioma' sem dicionário: '{idioma}'. Dicionários "
            f"disponíveis em assets/i18n/: {', '.join(disponiveis) or '(nenhum)'}."
        )


def _validar_analise(analise: Any) -> None:
    analise = _exigir_objeto(analise, "analise")
    _recusar_chave_desconhecida(analise, CHAVES_DE_ANALISE, "analise")
    if "conclusao" not in analise:
        raise EntregaInvalida("campo obrigatório ausente em 'analise': 'conclusao'.")
    if "exhibits" not in analise:
        raise EntregaInvalida("campo obrigatório ausente em 'analise': 'exhibits'.")

    conclusao = _exigir_objeto(analise["conclusao"], "analise.conclusao")
    _recusar_chave_desconhecida(conclusao, CHAVES_DE_CONCLUSAO, "analise.conclusao")
    if "texto" not in conclusao:
        raise EntregaInvalida("campo obrigatório ausente em 'analise.conclusao': 'texto'.")
    _exigir_texto_nao_vazio(conclusao["texto"], "analise.conclusao.texto")

    # 5B/G1: vocabulário fechado por exhibit/série/overlay/dataset é
    # responsabilidade de `exhibits.py` (ver o docstring do módulo, e o de
    # `exhibits.py`, para o porquê da relançada em vez de duplicação ou
    # import circular).
    try:
        exhibits.validar_exhibits(analise["exhibits"])
    except exhibits.ContratoDeExhibitInvalido as erro:
        raise EntregaInvalida(str(erro)) from erro


def _validar(entrega: Any) -> None:
    """Valida o dict já carregado de `entrega.json`; levanta `EntregaInvalida`
    na primeira violação. Ordem: raiz é objeto -> chaves de topo desconhecidas
    -> campos de topo obrigatórios -> versão da entrega -> `execucao`
    (vocabulário, campos, dicionário do idioma) -> `caso` (só tipo) ->
    identidade de ticker entre `caso`/`execucao` (B7, quando `caso` declara
    um) -> `resultados` (tipo + versão do sub-contrato) -> `dados` (5B/G3,
    só quando presente -- é o único campo de topo opcional) -> `analise`
    (vocabulário completo desta fatia, incluindo `exhibits`, 5B/G1) ->
    `ledger`/`ficha_tecnica` (só tipo).
    """
    if not isinstance(entrega, dict):
        raise EntregaInvalida(
            "entrega.json inválido: o documento raiz tem de ser um objeto "
            "(com as chaves versao_contrato, execucao, caso, resultados, "
            f"analise, ledger, ficha_tecnica), não {type(entrega).__name__}: "
            f"{entrega!r}."
        )

    _recusar_chave_desconhecida(entrega, CHAVES_DE_TOPO, "entrega")
    for campo in sorted(CHAVES_DE_TOPO_OBRIGATORIAS):
        if campo not in entrega:
            raise EntregaInvalida(f"campo obrigatório ausente na entrega: '{campo}'.")

    versao = entrega["versao_contrato"]
    if versao != VERSAO_CONTRATO:
        raise EntregaInvalida(
            f"'versao_contrato' incompatível: {versao!r}. Este builder só "
            f"lê '{VERSAO_CONTRATO}'."
        )

    _validar_execucao(entrega["execucao"])
    caso = _exigir_objeto(entrega["caso"], "caso")

    # B7 (onda de correção da revisão final, achado F6): identidade do
    # ticker. `execucao.ticker` é o que o relatório de fato exibe
    # (`render.compor` ecoa `execucao["ticker"]` no título da página);
    # `caso.ticker`, quando o caso o declara, é o que a integração já
    # amarrou ao hash (`resultados.origem.caso_sha256` cobre o caso
    # inteiro, ticker incluso). Sem esta checagem, nada impedia uma
    # `execucao.ticker` divergente do `caso.ticker` real -- o título da
    # página nomeava uma empresa diferente da que o valuation avaliou,
    # código 0, sem aviso nenhum (VERIFICADO na revisão: caso/resultados de
    # 'SINT3', execucao.ticker='PETR4' -> título "Sintética S.A. (PETR4)").
    # `caso` é opaco para este módulo (E3) -- só lê a chave 'ticker' quando
    # ela é de fato uma string não vazia; um caso que não a declara (ou a
    # declara de outro tipo) não aciona esta checagem.
    caso_ticker = caso.get("ticker") if isinstance(caso, dict) else None
    if isinstance(caso_ticker, str) and caso_ticker.strip():
        execucao_ticker = entrega["execucao"]["ticker"]
        if caso_ticker != execucao_ticker:
            raise EntregaInvalida(
                f"'execucao.ticker' ({execucao_ticker!r}) diverge de 'caso.ticker' "
                f"({caso_ticker!r}) -- os dois têm de nomear a mesma empresa."
            )

    resultados = _exigir_objeto(entrega["resultados"], "resultados")
    versao_resultados = resultados.get("versao_contrato")
    if versao_resultados != VERSAO_CONTRATO_RESULTADOS:
        raise EntregaInvalida(
            f"'resultados.versao_contrato' incompatível: {versao_resultados!r}. "
            f"Este builder só lê '{VERSAO_CONTRATO_RESULTADOS}'."
        )

    # 5B/G3: `dados` é o único campo de topo OPCIONAL (comentário de
    # `CHAVES_DE_TOPO_OBRIGATORIAS` acima) -- só validado quando presente.
    if "dados" in entrega:
        try:
            exhibits.validar_dados(entrega["dados"])
        except exhibits.ContratoDeExhibitInvalido as erro:
            raise EntregaInvalida(str(erro)) from erro

    _validar_analise(entrega["analise"])

    if not isinstance(entrega["ledger"], list):
        raise EntregaInvalida(f"'ledger' não é uma lista: {entrega['ledger']!r}.")
    _exigir_objeto(entrega["ficha_tecnica"], "ficha_tecnica")


def carregar(raiz: Path) -> Entrega:
    """Lê e valida `<raiz>/entrega.json`; devolve o dict. Nunca escreve nada.

    Regra inviolável 6: `raiz` é a ÚNICA raiz de execução aceita. Um
    `entrega.json` cujo caminho resolvido (`Path.resolve()`, que segue
    symlink) sai de dentro de `raiz` é recusado — nunca lido através do
    link. Criar o symlink que exercita este caminho pode exigir privilégio
    elevado no Windows; o teste que cobre isso pula, declarando a razão
    (o CI, em Ubuntu, roda sempre).
    """
    raiz = Path(raiz)
    if not raiz.is_dir():
        raise EntregaInvalida(f"raiz de execução não é um diretório: '{raiz}'.")
    raiz_resolvida = raiz.resolve()

    caminho = raiz / "entrega.json"
    if not caminho.exists():
        raise EntregaInvalida(f"'entrega.json' ausente em '{raiz_resolvida}'.")

    resolvido = caminho.resolve()
    if resolvido.parent != raiz_resolvida:
        raise EntregaInvalida(
            f"'entrega.json' resolve fora da raiz de execução: '{resolvido}' "
            f"não está em '{raiz_resolvida}'. O builder aceita uma única "
            "raiz de execução (regra inviolável 6) — um link apontando para "
            "fora não é seguido."
        )

    texto = caminho.read_text(encoding="utf-8")
    try:
        entrega = json.loads(texto)
    except json.JSONDecodeError as erro:
        raise EntregaInvalida(f"'entrega.json' não é um JSON válido: {erro}.") from erro

    _validar(entrega)
    return entrega
