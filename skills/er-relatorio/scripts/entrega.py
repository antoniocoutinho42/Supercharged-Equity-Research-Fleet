"""Contrato de `entrega.json` (fatia 5A, item 5, Task 3, decisão A1;
estendido na fatia 5B, item 5, Task 1, G1/G3: `dados` no topo, `exhibits`
em `analise`; e na fatia 5D, item 5, Task 2, D1/D5: a Tese do analista em
`analise`).

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

A Tese (5D, D1/D5) também é vocabulário PRÓPRIO deste contrato. A FORMA de
cada nível — chave desconhecida, tipo, campo obrigatório ausente, vocabulário
fechado de `tema`/`vetor`/`incorporacao`, exhibit citado que existe,
`exhibits` XOR `sem_exhibit` — é recusada aqui, código 1, com sugestão por
`difflib`. O que depende do catálogo ou dos números de `resultados` (o
vocabulário de vínculo, D2; a ordem da faixa; a cobertura das perguntas, §7;
preço-alvo sob fronteira de escopo; a reversa) é achado de QC (`qc.py`, D6),
código 2. A única leitura de `resultados` que a forma exige é
`resultados.fronteira_de_escopo`: fora da fronteira, `analise.faixa` é
obrigatória; sob ela, declarar a faixa não é recusa de forma — é o HARD FAIL
`fronteira_com_preco_alvo`.

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
# tipo confirmado nesta fatia (a 5E detalha o conteúdo dos dois).
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

# --------------------------------------------------------------------------
# Fatia 5D, item 5, Task 2 (D1/D5): a Tese do analista em `analise`, com
# vocabulário fechado em todo nível. `?` no plano vira, aqui, "fora de
# CHAVES_..._OBRIGATORIAS".
# --------------------------------------------------------------------------

# §7 do desenho: as três alavancas do múltiplo justo são cobertura obrigatória;
# `especifica` é a pergunta adicional, quando um fator realmente domina a tese.
# Quantas perguntas e quantas de cada tema é conteúdo (QC, D6), não forma.
TEMAS_OBRIGATORIOS: frozenset = frozenset({"moat", "crescimento", "rentabilidade_do_crescimento"})
TEMA_ESPECIFICO: str = "especifica"
TEMAS_DE_PERGUNTA: frozenset = TEMAS_OBRIGATORIOS | {TEMA_ESPECIFICO}

# §9: o vetor que um Positive/Negative atinge, e se ele está refletido no
# valuation ou declarado como não incorporado — este, sempre com a razão.
VETORES: frozenset = frozenset({"crescimento", "moat", "rentabilidade", "risco", "earning_power", "valuation"})
INCORPORACAO_NAO_INCORPORADA: str = "nao_incorporado"
INCORPORACOES: frozenset = frozenset({"refletido", INCORPORACAO_NAO_INCORPORADA})

# Cada papel da faixa nomeia um cenário de `resultados.cenarios` (declarado,
# nunca inferido); os números são os que a integração publicou.
PAPEIS_DA_FAIXA: tuple = ("piso", "base", "teto")

# §9: "o que mudou desde a análise fornecida" cabe em três linhas.
MAXIMO_DE_LINHAS_DO_QUE_MUDOU: int = 3

CHAVES_DE_ANALISE: frozenset = frozenset({
    "conclusao", "exhibits", "faixa", "veredicto", "premissas_decisivas", "positives", "negatives",
    "perguntas", "riscos", "visao_nao_consensual", "mudou_desde_analise_fornecida",
})
# `faixa` é exigida só fora da fronteira de escopo (`_validar_analise`); as duas
# últimas são opcionais.
CHAVES_DE_ANALISE_OBRIGATORIAS: frozenset = CHAVES_DE_ANALISE - {
    "faixa", "visao_nao_consensual", "mudou_desde_analise_fornecida",
}
CHAVES_DE_CONCLUSAO: frozenset = frozenset({"texto"})
CHAVES_DE_FAIXA: frozenset = frozenset(PAPEIS_DA_FAIXA)
CHAVES_DE_VEREDICTO: frozenset = frozenset({"texto"})
CHAVES_DE_PREMISSA_DECISIVA: frozenset = frozenset({"chave", "derivacao"})
CHAVES_DE_POSITIVE_OU_NEGATIVE: frozenset = frozenset({
    "afirmacao", "vetor", "mecanismo", "observavel", "incorporacao", "razao",
})
CHAVES_DE_POSITIVE_OU_NEGATIVE_OBRIGATORIAS: frozenset = CHAVES_DE_POSITIVE_OU_NEGATIVE - {"razao"}
CHAVES_DE_PERGUNTA: frozenset = frozenset({
    "id", "tema", "pergunta", "evidencia", "observavel", "vinculo", "exhibits", "sem_exhibit",
})
# D5: `exhibits` XOR `sem_exhibit` — exatamente um dos dois, conferido à parte.
CHAVES_DE_PERGUNTA_OBRIGATORIAS: frozenset = CHAVES_DE_PERGUNTA - {"exhibits", "sem_exhibit"}
CHAVES_DE_SEM_EXHIBIT: frozenset = frozenset({"razao"})
CHAVES_DE_RISCO: frozenset = frozenset({"risco", "observavel"})
CHAVES_DE_VISAO_NAO_CONSENSUAL: frozenset = frozenset({"texto"})
CHAVES_DO_QUE_MUDOU: frozenset = frozenset({"linhas"})

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


def _exigir_lista(valor: Any, campo: str) -> list:
    if not isinstance(valor, list):
        raise EntregaInvalida(f"'{campo}' não é uma lista: {valor!r}.")
    return valor


def _exigir_lista_de_textos(valor: Any, campo: str) -> list:
    """Lista NÃO VAZIA de textos não vazios — `vinculo`, `mecanismo`,
    `exhibits` de uma pergunta e as linhas do que mudou."""
    if not isinstance(valor, list) or not valor or not all(isinstance(v, str) and v.strip() for v in valor):
        raise EntregaInvalida(f"'{campo}' tem de ser uma lista não vazia de textos não vazios: {valor!r}.")
    return valor


def _exigir_do_vocabulario(valor: Any, vocabulario: frozenset, campo: str) -> str:
    if isinstance(valor, str) and valor in vocabulario:
        return valor
    sugestao = difflib.get_close_matches(str(valor), sorted(vocabulario), n=1)
    dica = f" Você quis dizer '{sugestao[0]}'? " if sugestao else " "
    raise EntregaInvalida(
        f"'{campo}' fora do vocabulário fechado: {valor!r}.{dica}"
        f"Valores aceitos: {', '.join(sorted(vocabulario))}."
    )


def _objeto_fechado(valor: Any, permitidas: frozenset, obrigatorias: frozenset, onde: str) -> dict:
    """Objeto, sem chave fora de `permitidas`, com toda chave de
    `obrigatorias` — a forma de todo nível da Tese."""
    objeto = _exigir_objeto(valor, onde)
    _recusar_chave_desconhecida(objeto, permitidas, onde)
    for campo in sorted(obrigatorias):
        if campo not in objeto:
            raise EntregaInvalida(f"campo obrigatório ausente em '{onde}': '{campo}'.")
    return objeto


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


def _validar_positive_ou_negative(valor: Any, onde: str) -> None:
    item = _objeto_fechado(valor, CHAVES_DE_POSITIVE_OU_NEGATIVE, CHAVES_DE_POSITIVE_OU_NEGATIVE_OBRIGATORIAS, onde)
    _exigir_texto_nao_vazio(item["afirmacao"], f"{onde}.afirmacao")
    _exigir_do_vocabulario(item["vetor"], VETORES, f"{onde}.vetor")
    _exigir_lista_de_textos(item["mecanismo"], f"{onde}.mecanismo")
    _exigir_texto_nao_vazio(item["observavel"], f"{onde}.observavel")
    incorporacao = _exigir_do_vocabulario(item["incorporacao"], INCORPORACOES, f"{onde}.incorporacao")
    if incorporacao == INCORPORACAO_NAO_INCORPORADA and "razao" not in item:
        raise EntregaInvalida(
            f"campo obrigatório ausente em '{onde}': 'razao' — um item "
            f"'{INCORPORACAO_NAO_INCORPORADA}' declara por que não está no valuation (§9)."
        )
    if "razao" in item:
        _exigir_texto_nao_vazio(item["razao"], f"{onde}.razao")


def _validar_pergunta(valor: Any, onde: str, ids_de_exhibit: list[str]) -> None:
    pergunta = _objeto_fechado(valor, CHAVES_DE_PERGUNTA, CHAVES_DE_PERGUNTA_OBRIGATORIAS, onde)
    _exigir_texto_nao_vazio(pergunta["id"], f"{onde}.id")
    _exigir_do_vocabulario(pergunta["tema"], TEMAS_DE_PERGUNTA, f"{onde}.tema")
    for campo in ("pergunta", "evidencia", "observavel"):
        _exigir_texto_nao_vazio(pergunta[campo], f"{onde}.{campo}")
    _exigir_lista_de_textos(pergunta["vinculo"], f"{onde}.vinculo")

    # D5 (§10: "pelo menos um exhibit útil ou uma decisão explícita de que
    # visualização não acrescenta"): exatamente um dos dois.
    tem_exhibits = "exhibits" in pergunta
    if tem_exhibits and "sem_exhibit" in pergunta:
        raise EntregaInvalida(
            f"'{onde}' declara 'exhibits' e 'sem_exhibit' ao mesmo tempo: cada pergunta cita os "
            "exhibits que a respondem OU declara a razão de nenhum acrescentar — nunca os dois."
        )
    if not tem_exhibits and "sem_exhibit" not in pergunta:
        raise EntregaInvalida(
            f"'{onde}' não declara 'exhibits' nem 'sem_exhibit': cada pergunta cita os exhibits "
            "que a respondem ou declara a razão de nenhum acrescentar."
        )
    if tem_exhibits:
        declarados = sorted(set(ids_de_exhibit))
        for indice, exhibit_id in enumerate(_exigir_lista_de_textos(pergunta["exhibits"], f"{onde}.exhibits")):
            if exhibit_id in declarados:
                continue
            sugestao = difflib.get_close_matches(exhibit_id, declarados, n=1)
            dica = f" Você quis dizer '{sugestao[0]}'? " if sugestao else " "
            raise EntregaInvalida(
                f"'{onde}.exhibits.{indice}' cita um exhibit que não existe em 'analise.exhibits': "
                f"'{exhibit_id}'.{dica}Exhibits declarados: {', '.join(declarados) or '(nenhum)'}."
            )
    else:
        sem_exhibit = _objeto_fechado(pergunta["sem_exhibit"], CHAVES_DE_SEM_EXHIBIT,
                                      CHAVES_DE_SEM_EXHIBIT, f"{onde}.sem_exhibit")
        _exigir_texto_nao_vazio(sem_exhibit["razao"], f"{onde}.sem_exhibit.razao")


def _validar_analise(analise: Any, resultados: dict) -> None:
    """`analise` (A1 + 5B/G1 + 5D/D1-D5): vocabulário fechado em todo nível.
    `resultados` só é lido para a condicional da faixa (D1/D3)."""
    analise = _objeto_fechado(analise, CHAVES_DE_ANALISE, CHAVES_DE_ANALISE_OBRIGATORIAS, "analise")

    # D1/D3: uma faixa de preços é preço-alvo. Fora da fronteira de escopo ela é
    # exigida; sob ela, declará-la é o HARD FAIL `fronteira_com_preco_alvo` — a
    # forma continua validada, e o QC nomeia o problema.
    if resultados["fronteira_de_escopo"] is None and "faixa" not in analise:
        raise EntregaInvalida(
            "campo obrigatório ausente em 'analise': 'faixa' — fora da fronteira de escopo, a Tese "
            "declara a faixa piso–base–teto pelos nomes dos cenários de 'resultados.cenarios'."
        )

    conclusao = _objeto_fechado(analise["conclusao"], CHAVES_DE_CONCLUSAO, CHAVES_DE_CONCLUSAO, "analise.conclusao")
    _exigir_texto_nao_vazio(conclusao["texto"], "analise.conclusao.texto")

    if "faixa" in analise:
        faixa = _objeto_fechado(analise["faixa"], CHAVES_DE_FAIXA, CHAVES_DE_FAIXA, "analise.faixa")
        for papel in PAPEIS_DA_FAIXA:
            _exigir_texto_nao_vazio(faixa[papel], f"analise.faixa.{papel}")

    veredicto = _objeto_fechado(analise["veredicto"], CHAVES_DE_VEREDICTO, CHAVES_DE_VEREDICTO, "analise.veredicto")
    _exigir_texto_nao_vazio(veredicto["texto"], "analise.veredicto.texto")

    # 5B/G1: vocabulário fechado por exhibit/série/overlay/dataset é
    # responsabilidade de `exhibits.py` (ver o docstring do módulo, e o de
    # `exhibits.py`, para o porquê da relançada em vez de duplicação ou
    # import circular). Antes das perguntas: são os ids que elas citam.
    try:
        exhibits.validar_exhibits(analise["exhibits"])
    except exhibits.ContratoDeExhibitInvalido as erro:
        raise EntregaInvalida(str(erro)) from erro
    ids_de_exhibit = [exhibit["id"] for exhibit in analise["exhibits"]]

    for indice, premissa in enumerate(_exigir_lista(analise["premissas_decisivas"], "analise.premissas_decisivas")):
        onde = f"analise.premissas_decisivas.{indice}"
        premissa = _objeto_fechado(premissa, CHAVES_DE_PREMISSA_DECISIVA, CHAVES_DE_PREMISSA_DECISIVA, onde)
        _exigir_texto_nao_vazio(premissa["chave"], f"{onde}.chave")
        _exigir_texto_nao_vazio(premissa["derivacao"], f"{onde}.derivacao")

    for lado in ("positives", "negatives"):
        for indice, item in enumerate(_exigir_lista(analise[lado], f"analise.{lado}")):
            _validar_positive_ou_negative(item, f"analise.{lado}.{indice}")

    perguntas = _exigir_lista(analise["perguntas"], "analise.perguntas")
    for indice, pergunta in enumerate(perguntas):
        _validar_pergunta(pergunta, f"analise.perguntas.{indice}", ids_de_exhibit)
    ids = [pergunta["id"] for pergunta in perguntas]
    repetidos = sorted({ident for ident in ids if ids.count(ident) > 1})
    if repetidos:
        raise EntregaInvalida(
            f"'analise.perguntas' repete o id '{repetidos[0]}': cada pergunta tem um id próprio."
        )

    for indice, risco in enumerate(_exigir_lista(analise["riscos"], "analise.riscos")):
        onde = f"analise.riscos.{indice}"
        risco = _objeto_fechado(risco, CHAVES_DE_RISCO, CHAVES_DE_RISCO, onde)
        _exigir_texto_nao_vazio(risco["risco"], f"{onde}.risco")
        _exigir_texto_nao_vazio(risco["observavel"], f"{onde}.observavel")

    if "visao_nao_consensual" in analise:
        visao = _objeto_fechado(analise["visao_nao_consensual"], CHAVES_DE_VISAO_NAO_CONSENSUAL,
                                CHAVES_DE_VISAO_NAO_CONSENSUAL, "analise.visao_nao_consensual")
        _exigir_texto_nao_vazio(visao["texto"], "analise.visao_nao_consensual.texto")

    if "mudou_desde_analise_fornecida" in analise:
        onde = "analise.mudou_desde_analise_fornecida"
        mudou = _objeto_fechado(analise["mudou_desde_analise_fornecida"], CHAVES_DO_QUE_MUDOU, CHAVES_DO_QUE_MUDOU, onde)
        linhas = _exigir_lista_de_textos(mudou["linhas"], f"{onde}.linhas")
        if len(linhas) > MAXIMO_DE_LINHAS_DO_QUE_MUDOU:
            raise EntregaInvalida(
                f"'{onde}.linhas' tem {len(linhas)} linhas: no máximo {MAXIMO_DE_LINHAS_DO_QUE_MUDOU} "
                "(§9 do desenho — só o que é material)."
            )


def _validar(entrega: Any) -> None:
    """Valida o dict já carregado de `entrega.json`; levanta `EntregaInvalida`
    na primeira violação. Ordem: raiz é objeto -> chaves de topo desconhecidas
    -> campos de topo obrigatórios -> versão da entrega -> `execucao`
    (vocabulário, campos, dicionário do idioma) -> `caso` (só tipo) ->
    identidade de ticker entre `caso`/`execucao` (B7, quando `caso` declara
    um) -> `resultados` (tipo + versão do sub-contrato + presença de
    `fronteira_de_escopo`, 5D) -> `dados` (5B/G3, só quando presente -- é o
    único campo de topo opcional) -> `analise` (vocabulário completo, incluindo
    `exhibits`, 5B/G1, e a Tese, 5D/D1-D5) -> `ledger`/`ficha_tecnica` (só tipo).
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

    # 5D, Task 2 (D1/D3): a presença exigida de `analise.faixa` depende deste
    # campo, que a integração publica sempre (`null` sem fronteira). Ausente, o
    # contrato não diz se a faixa é exigida ou proibida — recusa nomeada, nunca
    # "ausente = sem fronteira" em silêncio.
    if "fronteira_de_escopo" not in resultados:
        raise EntregaInvalida(
            "'resultados.fronteira_de_escopo' ausente: o contrato 'resultados/1' o publica "
            "sempre (null quando o caso não declara fronteira), e é ele que decide se "
            "'analise.faixa' é exigida."
        )

    # 5B/G3: `dados` é o único campo de topo OPCIONAL (comentário de
    # `CHAVES_DE_TOPO_OBRIGATORIAS` acima) -- só validado quando presente.
    if "dados" in entrega:
        try:
            exhibits.validar_dados(entrega["dados"])
        except exhibits.ContratoDeExhibitInvalido as erro:
            raise EntregaInvalida(str(erro)) from erro

    _validar_analise(entrega["analise"], resultados)

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
