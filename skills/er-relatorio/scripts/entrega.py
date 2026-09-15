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
código 2. A forma lê duas coisas de `resultados`. A primeira é
`resultados.fronteira_de_escopo`: fora da fronteira, `analise.faixa` é
obrigatória; sob ela, declarar a faixa não é recusa de forma — é o HARD FAIL
`fronteira_com_preco_alvo`. A segunda, desde a 5F (D12), é a presença de
`resultados.reversa`: o julgamento do que está no preço
(`analise.o_que_esta_no_preco`) é opcional, e declará-lo sem a reversa que ele
lê é recusa de forma. Da premissa decisiva de uma parte de SOTP
(`premissas_decisivas[].parte`, D13) a forma confere só o texto; se a parte
existe e declara a premissa é QC.

O ledger (5E, D1) tem a forma do contrato `ledger/1` do `er-evidencia`, que
`builder.py` lê e entrega a `carregar`: as chaves de cada nível e os
vocabulários fechados vêm do contrato lido, nunca de uma cópia aqui — e "exige
fórmula" é a flag do estatuto, nunca o nome dele. O consenso (D4) e o confronto
(D5) são vocabulário deste contrato; `ficha_tecnica` saiu dele (D6). O que
depende dos números do caso ou do catálogo — proveniência, reconciliação,
conflito, contraprova — é achado de QC, código 2.

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
import math
import re
from datetime import date
from pathlib import Path
from typing import Any, NamedTuple, NoReturn

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
# `resultados`, a versão do sub-contrato. O `ledger` tem a forma do contrato
# `ledger/1` do `er-evidencia` (5E, D1), lido e nunca copiado — ver o bloco da
# 5E abaixo; `ficha_tecnica` saiu do contrato (5E, D6).
#
# `dados` (5B, G3) é NOVO e OPCIONAL na raiz — por isso fica de fora de
# `CHAVES_DE_TOPO_OBRIGATORIAS` (uma entrega cujos exhibits são só `engine`
# não precisa de `dados` nenhum: `engine` lê `resultados` direto, nunca um
# dataset local). `exhibits` (5B, G1) é NOVO em `analise`, mas OBRIGATÓRIO
# lá (mesma disciplina do `ledger`: sempre presente, vazio quando não há o
# que declarar -- G10 do desenho, "não há gráfico obrigatório"). `confronto`
# (5E, D5) é o outro campo de topo opcional: só existe quando uma análise
# anterior foi fornecida.
# --------------------------------------------------------------------------

VERSAO_CONTRATO: str = "entrega/1"
VERSAO_CONTRATO_RESULTADOS: str = "resultados/1"

CHAVES_DE_TOPO: frozenset = frozenset({
    "versao_contrato", "execucao", "caso", "resultados", "analise", "ledger", "dados", "confronto",
})
CHAVES_DE_TOPO_OBRIGATORIAS: frozenset = CHAVES_DE_TOPO - {"dados", "confronto"}

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
    "conclusao", "exhibits", "faixa", "veredicto", "consenso", "premissas_decisivas", "positives",
    "negatives", "perguntas", "riscos", "visao_nao_consensual", "mudou_desde_analise_fornecida",
    "o_que_esta_no_preco",
})
# `faixa` é exigida só fora da fronteira de escopo (`_validar_analise`); as outras
# três são opcionais — `o_que_esta_no_preco` (5F, D12) só cabe com a reversa.
CHAVES_DE_ANALISE_OBRIGATORIAS: frozenset = CHAVES_DE_ANALISE - {
    "faixa", "visao_nao_consensual", "mudou_desde_analise_fornecida", "o_que_esta_no_preco",
}
CHAVES_DE_CONCLUSAO: frozenset = frozenset({"texto"})
CHAVES_DE_FAIXA: frozenset = frozenset(PAPEIS_DA_FAIXA)
CHAVES_DE_VEREDICTO: frozenset = frozenset({"texto"})
# 5F, D13: `parte`, opcional, endereça a premissa decisiva a uma parte de SOTP pelo
# nome que `resultados.sotp.partes[*].nome` publica.
CHAVES_DE_PREMISSA_DECISIVA: frozenset = frozenset({"chave", "derivacao", "parte"})
CHAVES_DE_PREMISSA_DECISIVA_OBRIGATORIAS: frozenset = CHAVES_DE_PREMISSA_DECISIVA - {"parte"}
# 5F, D12 (§9; vendor §5b, item 5): o julgamento comparativo do analista — qual
# reconciliação exige a menor violência às âncoras observáveis — e o observável que
# o testaria.
CHAVES_DO_QUE_ESTA_NO_PRECO: frozenset = frozenset({"julgamento", "observavel"})
# O bloco de `resultados` que esse julgamento lê: nome do contrato `resultados/1`, o
# mesmo que o QC confere em `analise_sem_reversa` (`qc.BLOCO_DA_REVERSA`).
BLOCO_DA_REVERSA: str = "reversa"
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

# --------------------------------------------------------------------------
# Fatia 5E, item 5, Task 2 (D1, D4, D5): o ledger, o consenso e o confronto.
#
# A FORMA do ledger é do `er-evidencia` (§3.2 do desenho: "dona do schema do
# ledger"), publicada como dado em `contrato_ledger.json`. `builder.py` a lê
# pela constante dos assets externos e a entrega a `carregar`. Nenhuma chave de
# nível e nenhum vocabulário daquele contrato é copiado para cá: as chaves
# aceitas e obrigatórias de cada nível, as classes de fonte, os tipos de
# localizador, os estatutos, as materialidades e as âncoras do consenso vêm do
# contrato lido, e "exige fórmula" é a flag `exige_formula` do estatuto, nunca
# o nome dele. Daqui é só o TIPO de cada campo, que o contrato não declara.
#
# O consenso (D4) é bloco da Tese: cita os registros que o sustentam ou declara
# a âncora substituta, do vocabulário do contrato do ledger. O confronto (D5) é
# processo do Fleet (§12, a quarentena), com a classificação fechada aqui, como
# o vocabulário da Tese.
# --------------------------------------------------------------------------

VERSAO_CONTRATO_LEDGER: str = "ledger/1"

# Os NOMES das seções pelas quais este relatório lê o contrato do ledger — a
# forma do contrato, nunca o conteúdo dele.
NIVEIS_DO_LEDGER: tuple = ("ledger", "registro", "fonte", "localizador", "reconciliacao", "conflito", "lacuna")
VOCABULARIOS_EM_LISTA_DO_LEDGER: tuple = ("classes_de_fonte", "tipos_de_localizador", "ancoras_do_consenso")
FLAGS_DE_ESTATUTO: tuple = ("exige_formula", "e_estimativa")
FLAGS_DE_MATERIALIDADE: tuple = ("exige_disclosure",)

CHAVES_DE_CONSENSO: frozenset = frozenset({"registros", "ausente"})
CHAVES_DE_CONSENSO_AUSENTE: frozenset = frozenset({"ancora", "razao"})

# §12: "o confronto resultante classifica cada divergência em: dado novo · premissa
# revista · erro anterior · pergunta anterior resolvida pelo observável".
CLASSIFICACOES_DE_DIVERGENCIA: frozenset = frozenset({
    "dado_novo", "premissa_revista", "erro_anterior", "pergunta_resolvida",
})
CHAVES_DE_CONFRONTO: frozenset = frozenset({"analise_fornecida", "divergencias"})
CHAVES_DA_ANALISE_FORNECIDA: frozenset = frozenset({"identificacao", "data"})
CHAVES_DE_DIVERGENCIA: frozenset = frozenset({"item", "classificacao", "anterior", "atual", "explicacao"})

_PADRAO_DATA = re.compile(r"\d{4}-\d{2}-\d{2}")

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


class ContratoDoLedgerInvalido(Exception):
    """O contrato do ledger lido não tem a forma pela qual este relatório o lê — a versão, os
    níveis com as listas `obrigatorias`/`opcionais`, os vocabulários e as flags de estatuto e de
    materialidade. Não é defeito da entrega: `builder.py` o reporta como código 1, e o QC falha
    fechado com ele — nunca lê um contrato pela metade."""


class ContratoDoLedger(NamedTuple):
    """O contrato `ledger/1` como o relatório o lê (`ler_contrato_do_ledger`)."""
    versao: str
    niveis: dict  # nível -> (chaves aceitas, chaves obrigatórias)
    classes_de_fonte: frozenset
    tipos_de_localizador: frozenset
    ancoras_do_consenso: frozenset
    estatutos: dict  # estatuto -> {flag: bool}
    materialidades: dict  # materialidade -> {flag: bool}


def _recusar_contrato_do_ledger(motivo: str) -> NoReturn:
    raise ContratoDoLedgerInvalido(f"contrato do ledger fora da forma que o relatório lê: {motivo}.")


def _lista_de_textos_do_contrato(valor: Any) -> bool:
    return isinstance(valor, list) and all(isinstance(item, str) and item for item in valor)


def _vocabulario_com_flags(vocabularios: dict, nome: str, flags: tuple) -> dict:
    vocabulario = vocabularios.get(nome)
    if not isinstance(vocabulario, dict) or not vocabulario:
        _recusar_contrato_do_ledger(f"o vocabulário '{nome}' não é um objeto não vazio")
    for entrada, declaradas in vocabulario.items():
        if not isinstance(declaradas, dict) or not all(isinstance(declaradas.get(flag), bool) for flag in flags):
            _recusar_contrato_do_ledger(f"'{nome}.{entrada}' não declara as flags {', '.join(flags)} como booleanas")
    return {entrada: {flag: declaradas[flag] for flag in flags} for entrada, declaradas in vocabulario.items()}


def ler_contrato_do_ledger(contrato: Any) -> ContratoDoLedger:
    """Lê o contrato `ledger/1` (o dict de `contrato_ledger.json`) e devolve o que o relatório usa
    dele; levanta `ContratoDoLedgerInvalido` nomeando a primeira parte fora da forma. É a única
    leitura do contrato neste pacote: `carregar` a usa para a forma da entrega, e o QC para as
    flags."""
    if not isinstance(contrato, dict):
        _recusar_contrato_do_ledger(f"o documento não é um objeto ({type(contrato).__name__})")
    versao = contrato.get("versao_contrato")
    if versao != VERSAO_CONTRATO_LEDGER:
        _recusar_contrato_do_ledger(f"'versao_contrato' é {versao!r}, e este builder só lê '{VERSAO_CONTRATO_LEDGER}'")
    niveis_declarados, vocabularios = contrato.get("niveis"), contrato.get("vocabularios")
    if not isinstance(niveis_declarados, dict) or not isinstance(vocabularios, dict):
        _recusar_contrato_do_ledger("'niveis' e 'vocabularios' têm de ser objetos")

    niveis = {}
    for nome in NIVEIS_DO_LEDGER:
        nivel = niveis_declarados.get(nome)
        if not (isinstance(nivel, dict) and _lista_de_textos_do_contrato(nivel.get("obrigatorias"))
                and _lista_de_textos_do_contrato(nivel.get("opcionais"))):
            _recusar_contrato_do_ledger(f"o nível '{nome}' não declara as listas de textos 'obrigatorias' e 'opcionais'")
        obrigatorias = frozenset(nivel["obrigatorias"])
        niveis[nome] = (obrigatorias | frozenset(nivel["opcionais"]), obrigatorias)

    listas = {}
    for nome in VOCABULARIOS_EM_LISTA_DO_LEDGER:
        vocabulario = vocabularios.get(nome)
        if not (_lista_de_textos_do_contrato(vocabulario) and vocabulario):
            _recusar_contrato_do_ledger(f"o vocabulário '{nome}' não é uma lista não vazia de textos")
        listas[nome] = frozenset(vocabulario)

    return ContratoDoLedger(
        versao=versao, niveis=niveis, classes_de_fonte=listas["classes_de_fonte"],
        tipos_de_localizador=listas["tipos_de_localizador"], ancoras_do_consenso=listas["ancoras_do_consenso"],
        estatutos=_vocabulario_com_flags(vocabularios, "estatutos", FLAGS_DE_ESTATUTO),
        materialidades=_vocabulario_com_flags(vocabularios, "materialidades", FLAGS_DE_MATERIALIDADE))


def _exigir_data(valor: Any, campo: str) -> str:
    """`AAAA-MM-DD`, e uma data que o calendário tem (`2026-02-30` é recusa)."""
    if isinstance(valor, str) and _PADRAO_DATA.fullmatch(valor):
        try:
            date.fromisoformat(valor)
            return valor
        except ValueError:
            pass
    raise EntregaInvalida(f"'{campo}' fora do formato AAAA-MM-DD, ou não é uma data do calendário: {valor!r}.")


def _numero(valor: Any) -> bool:
    """Número finito de JSON — booleano não é número."""
    return isinstance(valor, (int, float)) and not isinstance(valor, bool) and math.isfinite(valor)


def _nivel_do_ledger(valor: Any, contrato: ContratoDoLedger, nivel: str, onde: str) -> dict:
    """Objeto fechado pelas chaves que o contrato do ledger declara para `nivel`."""
    aceitas, obrigatorias = contrato.niveis[nivel]
    return _objeto_fechado(valor, aceitas, obrigatorias, onde)


def _exigir_ids_unicos(itens: list, onde: str, razao: str) -> None:
    ids = [item["id"] for item in itens]
    repetidos = sorted({ident for ident in ids if ids.count(ident) > 1})
    if repetidos:
        raise EntregaInvalida(f"'{onde}' repete o id '{repetidos[0]}': {razao}")


def _validar_registro(valor: Any, onde: str, contrato: ContratoDoLedger) -> None:
    """Um registro do ledger (D1). As chaves são as do contrato; os tipos, e as condicionais
    que o contrato declara por flag, conferidos aqui."""
    registro = _nivel_do_ledger(valor, contrato, "registro", onde)
    for campo in ("id", "claim", "periodo", "unidade", "justificativa_da_fonte"):
        _exigir_texto_nao_vazio(registro.get(campo), f"{onde}.{campo}")

    fonte = _nivel_do_ledger(registro.get("fonte"), contrato, "fonte", f"{onde}.fonte")
    _exigir_texto_nao_vazio(fonte.get("identidade"), f"{onde}.fonte.identidade")
    _exigir_do_vocabulario(fonte.get("classe"), contrato.classes_de_fonte, f"{onde}.fonte.classe")

    localizador = _nivel_do_ledger(registro.get("localizador"), contrato, "localizador", f"{onde}.localizador")
    _exigir_do_vocabulario(localizador.get("tipo"), contrato.tipos_de_localizador, f"{onde}.localizador.tipo")
    _exigir_texto_nao_vazio(localizador.get("valor"), f"{onde}.localizador.valor")
    if "parametros" in localizador:
        _exigir_objeto(localizador["parametros"], f"{onde}.localizador.parametros")

    _exigir_data(registro.get("data_acesso"), f"{onde}.data_acesso")

    moeda = registro.get("moeda")
    if moeda is not None and not (isinstance(moeda, str) and moeda.strip()):
        raise EntregaInvalida(f"'{onde}.moeda' tem de ser um texto não vazio ou null: {moeda!r}.")

    valor_do_registro = registro.get("valor")
    if valor_do_registro is not None and not _numero(valor_do_registro):
        raise EntregaInvalida(
            f"'{onde}.valor' tem de ser um número ou null — booleano não é número: {valor_do_registro!r}.")

    estatuto = _exigir_do_vocabulario(registro.get("estatuto"), frozenset(contrato.estatutos), f"{onde}.estatuto")
    if contrato.estatutos[estatuto]["exige_formula"]:
        if "formula" not in registro:
            raise EntregaInvalida(
                f"campo obrigatório ausente em '{onde}': 'formula' — o estatuto '{estatuto}' exige a fórmula do cálculo.")
    else:
        for campo in ("formula", "insumos"):
            if campo in registro:
                raise EntregaInvalida(
                    f"'{onde}.{campo}' só cabe num registro cujo estatuto exige fórmula, e o estatuto "
                    f"'{estatuto}' não exige.")
    if "formula" in registro:
        _exigir_texto_nao_vazio(registro["formula"], f"{onde}.formula")
    if "insumos" in registro:
        _exigir_lista_de_textos(registro["insumos"], f"{onde}.insumos")

    if "usado_em" in registro:
        _exigir_lista_de_textos(registro["usado_em"], f"{onde}.usado_em")
        if not _numero(valor_do_registro):
            raise EntregaInvalida(
                f"'{onde}.usado_em' exige 'valor' numérico: um registro que sustenta um número do caso declara "
                f"esse número, e aqui 'valor' é {valor_do_registro!r}.")

    if "reconciliacao" in registro:
        reconciliacao = _nivel_do_ledger(registro["reconciliacao"], contrato, "reconciliacao", f"{onde}.reconciliacao")
        _exigir_texto_nao_vazio(reconciliacao.get("texto"), f"{onde}.reconciliacao.texto")
    if "conflito" in registro:
        conflito = _nivel_do_ledger(registro["conflito"], contrato, "conflito", f"{onde}.conflito")
        _exigir_texto_nao_vazio(conflito.get("vencedor"), f"{onde}.conflito.vencedor")
        _exigir_texto_nao_vazio(conflito.get("razao"), f"{onde}.conflito.razao")
    if "contraprova_de" in registro:
        _exigir_texto_nao_vazio(registro["contraprova_de"], f"{onde}.contraprova_de")


def _validar_lacuna(valor: Any, onde: str, contrato: ContratoDoLedger) -> None:
    lacuna = _nivel_do_ledger(valor, contrato, "lacuna", onde)
    for campo in ("id", "descricao", "tratamento"):
        _exigir_texto_nao_vazio(lacuna.get(campo), f"{onde}.{campo}")
    _exigir_do_vocabulario(lacuna.get("materialidade"), frozenset(contrato.materialidades), f"{onde}.materialidade")


def _validar_ledger(valor: Any, contrato: ContratoDoLedger) -> None:
    """D1: o ledger na forma do contrato lido. Se um id citado existe, se um número do caso tem
    proveniência e se o registro reconcilia com ele é QC (`qc.py`), código 2."""
    ledger = _nivel_do_ledger(valor, contrato, "ledger", "ledger")
    if ledger.get("versao_contrato") != contrato.versao:
        raise EntregaInvalida(
            f"'ledger.versao_contrato' incompatível: {ledger.get('versao_contrato')!r}. Este builder só lê "
            f"'{contrato.versao}'.")
    registros = _exigir_lista(ledger.get("registros"), "ledger.registros")
    for indice, registro in enumerate(registros):
        _validar_registro(registro, f"ledger.registros.{indice}", contrato)
    _exigir_ids_unicos(registros, "ledger.registros",
                       "cada registro tem um id próprio — é por ele que os insumos de um cálculo, o vencedor de "
                       "um conflito, a contraprova, o consenso e os datasets o citam.")
    lacunas = _exigir_lista(ledger.get("lacunas"), "ledger.lacunas")
    for indice, lacuna in enumerate(lacunas):
        _validar_lacuna(lacuna, f"ledger.lacunas.{indice}", contrato)
    _exigir_ids_unicos(lacunas, "ledger.lacunas", "cada lacuna tem um id próprio.")


def _validar_consenso(valor: Any, contrato: ContratoDoLedger) -> None:
    """D4 (§9: "consenso como referência externa"; §6.3): o consenso cita os registros do ledger
    que o sustentam OU declara a âncora observável que entra no lugar dele, com a razão —
    exatamente um dos dois. Se os ids citados existem é QC (`referencia_fora_do_ledger`)."""
    onde = "analise.consenso"
    consenso = _objeto_fechado(valor, CHAVES_DE_CONSENSO, frozenset(), onde)
    tem_registros, tem_ausente = "registros" in consenso, "ausente" in consenso
    if tem_registros and tem_ausente:
        raise EntregaInvalida(
            f"'{onde}' declara 'registros' e 'ausente' ao mesmo tempo: o consenso cita os registros do ledger "
            "que o sustentam OU declara a âncora que entra no lugar dele — nunca os dois.")
    if not tem_registros and not tem_ausente:
        raise EntregaInvalida(
            f"'{onde}' não declara 'registros' nem 'ausente': o consenso cita os registros do ledger que o "
            "sustentam ou declara a âncora observável que entra no lugar dele (§6.3).")
    if tem_registros:
        _exigir_lista_de_textos(consenso["registros"], f"{onde}.registros")
        return
    ausente = _objeto_fechado(consenso["ausente"], CHAVES_DE_CONSENSO_AUSENTE, CHAVES_DE_CONSENSO_AUSENTE,
                              f"{onde}.ausente")
    _exigir_do_vocabulario(ausente["ancora"], contrato.ancoras_do_consenso, f"{onde}.ausente.ancora")
    _exigir_texto_nao_vazio(ausente["razao"], f"{onde}.ausente.razao")


def _validar_confronto(valor: Any) -> None:
    """D5 (§12, decisão 20): a análise fornecida e cada divergência com a classificação fechada."""
    confronto = _objeto_fechado(valor, CHAVES_DE_CONFRONTO, CHAVES_DE_CONFRONTO, "confronto")
    fornecida = _objeto_fechado(confronto["analise_fornecida"], CHAVES_DA_ANALISE_FORNECIDA,
                                CHAVES_DA_ANALISE_FORNECIDA, "confronto.analise_fornecida")
    _exigir_texto_nao_vazio(fornecida["identificacao"], "confronto.analise_fornecida.identificacao")
    _exigir_data(fornecida["data"], "confronto.analise_fornecida.data")
    for indice, divergencia in enumerate(_exigir_lista(confronto["divergencias"], "confronto.divergencias")):
        onde = f"confronto.divergencias.{indice}"
        divergencia = _objeto_fechado(divergencia, CHAVES_DE_DIVERGENCIA, CHAVES_DE_DIVERGENCIA, onde)
        _exigir_do_vocabulario(divergencia["classificacao"], CLASSIFICACOES_DE_DIVERGENCIA, f"{onde}.classificacao")
        for campo in ("item", "anterior", "atual", "explicacao"):
            _exigir_texto_nao_vazio(divergencia[campo], f"{onde}.{campo}")


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


def _validar_analise(analise: Any, resultados: dict, contrato: ContratoDoLedger) -> None:
    """`analise` (A1 + 5B/G1 + 5D/D1-D5 + 5E/D4 + 5F/D12-D13): vocabulário fechado em todo
    nível. `resultados` só é lido para a condicional da faixa (D1/D3) e para a presença da
    reversa que o julgamento do que está no preço lê (D12); o contrato do ledger, para a
    âncora do consenso ausente."""
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

    _validar_consenso(analise["consenso"], contrato)

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
        premissa = _objeto_fechado(premissa, CHAVES_DE_PREMISSA_DECISIVA, CHAVES_DE_PREMISSA_DECISIVA_OBRIGATORIAS, onde)
        _exigir_texto_nao_vazio(premissa["chave"], f"{onde}.chave")
        _exigir_texto_nao_vazio(premissa["derivacao"], f"{onde}.derivacao")
        if "parte" in premissa:
            _exigir_texto_nao_vazio(premissa["parte"], f"{onde}.parte")

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

    # 5F, D12: opcional; declarado, lê a reversa — sem ela o julgamento não tem o que ler.
    if "o_que_esta_no_preco" in analise:
        onde = "analise.o_que_esta_no_preco"
        if resultados.get(BLOCO_DA_REVERSA) is None:
            raise EntregaInvalida(
                f"'{onde}' declarado sem 'resultados.{BLOCO_DA_REVERSA}': o julgamento do que está no preço "
                "lê a reversa, e esta entrega não a publica — retire o bloco, ou rode o valuation com a "
                "reversa no caso."
            )
        bloco = _objeto_fechado(analise["o_que_esta_no_preco"], CHAVES_DO_QUE_ESTA_NO_PRECO,
                                CHAVES_DO_QUE_ESTA_NO_PRECO, onde)
        for campo in sorted(CHAVES_DO_QUE_ESTA_NO_PRECO):
            _exigir_texto_nao_vazio(bloco[campo], f"{onde}.{campo}")


def _validar(entrega: Any, contrato: ContratoDoLedger) -> None:
    """Valida o dict já carregado de `entrega.json`; levanta `EntregaInvalida`
    na primeira violação. Ordem: raiz é objeto -> chaves de topo desconhecidas
    -> campos de topo obrigatórios -> versão da entrega -> `execucao`
    (vocabulário, campos, dicionário do idioma) -> `caso` (só tipo) ->
    identidade de ticker entre `caso`/`execucao` (B7, quando `caso` declara
    um) -> `resultados` (tipo + versão do sub-contrato + presença de
    `fronteira_de_escopo`, 5D) -> `dados` (5B/G3, só quando presente) ->
    `analise` (vocabulário completo, incluindo `exhibits`, 5B/G1, a Tese,
    5D/D1-D5, e o consenso, 5E/D4) -> `ledger` (o contrato `ledger/1`, 5E/D1)
    -> `confronto` (5E/D5, só quando presente — e exigido pelo que mudou).
    """
    if not isinstance(entrega, dict):
        raise EntregaInvalida(
            "entrega.json inválido: o documento raiz tem de ser um objeto "
            "(com as chaves versao_contrato, execucao, caso, resultados, "
            f"analise, ledger), não {type(entrega).__name__}: "
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

    _validar_analise(entrega["analise"], resultados, contrato)
    _validar_ledger(entrega["ledger"], contrato)

    # D5: o que mudou desde a análise fornecida, sem o confronto que classifica
    # cada divergência, é afirmação solta.
    if "confronto" in entrega:
        _validar_confronto(entrega["confronto"])
    elif "mudou_desde_analise_fornecida" in entrega["analise"]:
        raise EntregaInvalida(
            "'analise.mudou_desde_analise_fornecida' exige 'confronto' na raiz da entrega: o que mudou desde a "
            "análise fornecida sai do confronto que classifica cada divergência (§12) — sem ele, é afirmação solta."
        )


def carregar(raiz: Path, contrato_ledger: Any) -> Entrega:
    """Lê e valida `<raiz>/entrega.json`; devolve o dict. Nunca escreve nada.

    `contrato_ledger` (5E, D1): o dict do contrato `ledger/1` do `er-evidencia`, que
    `builder.py` lê pela constante dos assets externos — a forma do ledger é validada
    contra ele, nunca contra uma cópia deste pacote. Fora da forma que o relatório lê,
    `ContratoDoLedgerInvalido`, antes de olhar a raiz.

    Regra inviolável 6: `raiz` é a ÚNICA raiz de execução aceita. Um
    `entrega.json` cujo caminho resolvido (`Path.resolve()`, que segue
    symlink) sai de dentro de `raiz` é recusado — nunca lido através do
    link. Criar o symlink que exercita este caminho pode exigir privilégio
    elevado no Windows; o teste que cobre isso pula, declarando a razão
    (o CI, em Ubuntu, roda sempre).
    """
    contrato = ler_contrato_do_ledger(contrato_ledger)
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

    _validar(entrega, contrato)
    return entrega
