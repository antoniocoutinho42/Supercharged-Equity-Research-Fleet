"""Contrato do caso de valuation: carrega, valida, recusa.

Este módulo NÃO calcula nada e NÃO chama o motor congelado. A única
responsabilidade dele é ler um `caso.json`, verificar que ele declara tudo
que a metodologia exige antes de qualquer conta rodar, e recusar — nomeando
o campo e a razão — o que estiver incompleto.

Em particular, ele recusa qualquer escolha que a metodologia declara sem
default. O exemplo central é a convenção terminal (`tv`): a hipótese sobre
como o spread de retorno morre é uma decisão declarada pelo analista, não
uma convenção de fábrica que este módulo possa inventar — o próprio motor
congelado recusa rodar sem `--tv`, e este módulo recusa antes, nomeando o
motivo. O mesmo vale para a âncora observável de cada cenário (um cenário
sem âncora é um cenário inventado) e para a configuração do triângulo
g = RiR x retorno (um cenário sem essa configuração declarada esconde a taxa
de reinvestimento que ele implica).

`motor.py`, `ponte.py` e `avaliar.py` consomem os dicionários e constantes
definidos aqui; nenhum deles reabre esta validação.
"""

import json
from pathlib import Path
from typing import Any

Caso = dict[str, Any]


class CasoInvalido(Exception):
    """Levantada quando um `caso.json` está incompleto ou inconsistente.

    Nunca levantada via `assert`, e nunca seguida de `sys.exit` dentro deste
    módulo — quem decide o exit code do processo é o CLI de `avaliar.py`,
    não a camada de validação.
    """


# --------------------------------------------------------------------------
# Vocabulário de premissas por rota.
#
# PREMISSAS_* é o vocabulário COMPLETO que o motor aceita para a rota (o que
# `motor.py` pode traduzir em flag). PREMISSAS_OBRIGATORIAS_* é o
# subconjunto que TEM de estar presente em todo cenário daquela rota — o
# resto é opcional (por exemplo `gp`, que só importa quando a convenção
# terminal é `gordon`).
# --------------------------------------------------------------------------

PREMISSAS_FIRM: frozenset = frozenset({
    "g", "roic", "wacc", "n", "da", "tax", "tv",
    "roic_tv", "gp", "roic_book", "mid_year",
})

PREMISSAS_EQUITY: frozenset = frozenset({
    "g", "roe", "ke", "n", "gde", "nde", "tv",
    "roe_tv", "gp", "roe_book", "politica_tv", "mid_year",
})

PREMISSAS_OBRIGATORIAS_FIRM: frozenset = frozenset({
    "g", "roic", "wacc", "n", "da", "tax", "tv",
})

PREMISSAS_OBRIGATORIAS_EQUITY: frozenset = frozenset({
    "g", "roe", "ke", "n", "tv",
})

_PREMISSAS_POR_ROTA: dict[str, frozenset] = {
    "firm": PREMISSAS_FIRM,
    "equity": PREMISSAS_EQUITY,
}

_PREMISSAS_OBRIGATORIAS_POR_ROTA: dict[str, frozenset] = {
    "firm": PREMISSAS_OBRIGATORIAS_FIRM,
    "equity": PREMISSAS_OBRIGATORIAS_EQUITY,
}

# --------------------------------------------------------------------------
# Métrica-base por rota.
# --------------------------------------------------------------------------

# O que o motor emite diretamente nesta fatia — não é transformação nenhuma,
# é a métrica que o próprio subcomando (`ev` ou `pe`) recebe como escala.
METRICAS_POR_ROTA: dict[str, frozenset] = {
    "firm": frozenset({"EBITDA", "NOPAT"}),
    "equity": frozenset({"LL"}),
}

# Métricas que existem na metodologia mas são transformação de apresentação
# sobre a métrica-base (divisão por ações, álgebra entre múltiplos). Fora
# desta fatia: entram numa fatia posterior, com a álgebra exibida — nunca
# viram default nem cálculo silencioso aqui.
METRICAS_FORA_DA_FATIA: frozenset = frozenset({
    "EBIT", "EPS", "EBITDA/acao", "NOPAT/acao",
})

# --------------------------------------------------------------------------
# Ponte para preço.
#
# A ORDEM e o SINAL de cada linha (o waterfall) vivem em `ponte.py`; aqui só
# se valida a PRESENÇA do bloco, condicionada à rota. `ponte.py` importa esta
# tupla para garantir, no import, que as duas listas descrevem o mesmo
# conjunto de linhas.
# --------------------------------------------------------------------------

CAMPOS_DA_PONTE: tuple = (
    "divida_bruta", "caixa_e_equivalentes", "outros_ativos",
    "outros_passivos", "minoritarios",
)

# --------------------------------------------------------------------------
# Campos de topo obrigatórios e a razão de cada um.
# --------------------------------------------------------------------------

_RAZOES_CAMPOS_DE_TOPO: dict[str, str] = {
    "companhia": "identifica a companhia avaliada.",
    "moeda": (
        "toda taxa do caso (g, gp, custo de capital) tem de estar travada "
        "na mesma unidade monetária."
    ),
    "data_analise": (
        "ancora a análise no tempo; é a data que trava o spot dos drivers "
        "e aparece na saída."
    ),
    "rota": (
        "escolhe o subcomando do motor (firm ou equity) e o vocabulário de "
        "premissas que vale para o caso inteiro."
    ),
    "acoes_diluidas": "é o denominador de Equity por ação em toda rota.",
    "cenarios": "sem ao menos um cenário não há nada para o motor rodar.",
}


def validar(caso: Caso) -> None:
    """Valida um caso já carregado; levanta `CasoInvalido` na primeira violação.

    Ordem de verificação: campos de topo -> rota -> métrica x rota ->
    ponte x rota -> ações diluídas -> cada cenário (âncora, triângulo,
    premissas obrigatórias, premissas desconhecidas). Não modifica `caso`;
    não preenche nada — só confirma ou recusa.
    """
    _validar_campos_de_topo(caso)

    rota = caso["rota"]
    _validar_rota(rota)
    _validar_metrica(caso, rota)
    _validar_ponte(caso, rota)
    _validar_acoes_diluidas(caso)

    cenarios = caso["cenarios"]
    if not cenarios:
        raise CasoInvalido(
            "nenhum cenário declarado em 'cenarios': a metodologia exige "
            "ao menos um cenário (bear, base ou bull), cada um com âncora "
            "e triângulo próprios — um caso sem cenário não avalia nada."
        )
    for nome, cenario in cenarios.items():
        _validar_cenario(nome, cenario, rota)


def _validar_campos_de_topo(caso: Caso) -> None:
    for campo, razao in _RAZOES_CAMPOS_DE_TOPO.items():
        if campo not in caso:
            raise CasoInvalido(
                f"campo obrigatório ausente no caso: '{campo}'. {razao}"
            )


def _validar_rota(rota: Any) -> None:
    if rota not in METRICAS_POR_ROTA:
        raise CasoInvalido(
            f"rota desconhecida: '{rota}'. Rotas suportadas nesta fatia: "
            f"{', '.join(sorted(METRICAS_POR_ROTA))}."
        )


def _validar_metrica(caso: Caso, rota: str) -> None:
    metrica_base = caso.get("metrica_base") or {}
    tipo = metrica_base.get("tipo")
    aceitas = METRICAS_POR_ROTA[rota]

    if tipo in aceitas:
        return

    if tipo in METRICAS_FORA_DA_FATIA:
        raise CasoInvalido(
            f"métrica '{tipo}' fora desta fatia: '{tipo}' é transformação "
            "de apresentação sobre a métrica-base e entra numa fatia "
            "posterior, com a álgebra exibida. Rota "
            f"'{rota}' aceita apenas o que o motor emite direto: "
            f"{', '.join(sorted(aceitas))}."
        )

    raise CasoInvalido(
        f"métrica '{tipo}' incompatível com a rota '{rota}': rota '{rota}' "
        f"aceita apenas {', '.join(sorted(aceitas))}."
    )


def _validar_ponte(caso: Caso, rota: str) -> None:
    tem_ponte = "ponte" in caso

    if rota == "firm" and not tem_ponte:
        raise CasoInvalido(
            "campo 'ponte' ausente na rota firm: a rota firm chega em EV e "
            "precisa da ponte (dívida, caixa, outros ativos/passivos, "
            "minoritários) para chegar em Equity por ação. Declare 'ponte' "
            f"com {', '.join(CAMPOS_DA_PONTE)}."
        )

    if rota == "equity" and tem_ponte:
        raise CasoInvalido(
            "campo 'ponte' presente na rota equity: a rota equity já "
            "entrega Equity direto (P/L x LL) — não existe ponte de "
            "dívida para uma companhia avaliada pelo lado do acionista "
            "(financeira, por exemplo). Aceitar e ignorar 'ponte' aqui "
            "seria silenciar um dado que não se aplica; remova o campo."
        )


def _validar_acoes_diluidas(caso: Caso) -> None:
    acoes = caso["acoes_diluidas"]
    if (
        isinstance(acoes, bool)
        or not isinstance(acoes, (int, float))
        or acoes <= 0
    ):
        raise CasoInvalido(
            f"'acoes_diluidas' inválido: {acoes!r}. O número de ações "
            "diluídas precisa ser positivo — é o denominador de Equity "
            "por ação em toda rota."
        )


def _validar_cenario(nome: str, cenario: dict, rota: str) -> None:
    prefixo = f"cenário '{nome}'"

    if not cenario.get("ancora"):
        raise CasoInvalido(
            f"{prefixo} sem âncora: a metodologia exige um observável "
            "concreto por cenário (consenso, guidance vigente, histórico "
            "normalizado, run-rate, pares diretos) — cenário sem âncora é "
            "cenário inventado."
        )

    triangulo = cenario.get("triangulo")
    if not triangulo or "inputs" not in triangulo or "output" not in triangulo:
        raise CasoInvalido(
            f"{prefixo} sem triângulo declarado: a identidade "
            "g = RiR x retorno tem dois graus de liberdade — o caso "
            "precisa registrar quais duas variáveis são input e qual saiu "
            "como output. Sem isso o cenário fica com a taxa de "
            "reinvestimento (RiR) silenciosa."
        )

    inputs = triangulo["inputs"]
    output = triangulo["output"]
    if output in inputs:
        raise CasoInvalido(
            f"{prefixo}: triângulo inconsistente — o output '{output}' "
            f"está repetido entre os inputs {inputs}. O output tem de ser "
            "a variável que sobra, não uma das duas declaradas como input."
        )

    premissas = cenario.get("premissas") or {}

    obrigatorias = _PREMISSAS_OBRIGATORIAS_POR_ROTA[rota]
    for campo in sorted(obrigatorias):
        if campo in premissas:
            continue
        if campo == "tv":
            raise CasoInvalido(
                f"{prefixo}: premissa 'tv' (convenção terminal) ausente. "
                "Não tem default: a hipótese sobre como o spread de "
                "retorno morre (book, convergência ou gordon) é decisão "
                "declarada do analista, não convenção de fábrica — o "
                "próprio motor recusa rodar sem '--tv', e este wrapper "
                "recusa antes, nomeando o motivo."
            )
        raise CasoInvalido(
            f"{prefixo}: premissa obrigatória '{campo}' ausente para a "
            f"rota '{rota}'."
        )

    permitidas = _PREMISSAS_POR_ROTA[rota]
    for campo in sorted(premissas):
        if campo not in permitidas:
            raise CasoInvalido(
                f"{prefixo}: premissa '{campo}' desconhecida para a rota "
                f"'{rota}'. Chave que o motor não conhece é erro de "
                "digitação, não extensão silenciosa do vocabulário — "
                f"premissas aceitas: {', '.join(sorted(permitidas))}."
            )


def carregar(caminho: Path) -> Caso:
    """Lê `caminho` como JSON utf-8, valida e devolve o dict validado.

    Não faz cache, não modifica o conteúdo, não preenche nada: devolve
    exatamente o que veio do arquivo, depois de confirmar que passa em
    `validar`.
    """
    caso = json.loads(Path(caminho).read_text(encoding="utf-8"))
    validar(caso)
    return caso
