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
import math
from pathlib import Path
from typing import Any

Caso = dict[str, Any]


class CasoInvalido(Exception):
    """Levantada quando um `caso.json` está incompleto ou inconsistente.

    Nunca levantada via `assert`, e nunca seguida de `sys.exit` dentro deste
    módulo — quem decide o exit code do processo é o CLI de `avaliar.py`,
    não a camada de validação.
    """


def _finito(valor: Any) -> bool:
    """True a menos que `valor` seja um número não-finito (NaN ou ±Infinity).

    `json.loads` aceita os literais não-padrão `NaN`, `Infinity` e
    `-Infinity`; um deles em qualquer campo numérico envenena a conta a
    jusante em silêncio — e o serializador do motor transforma float
    não-finito em `null` mais adiante, longe desta causa. Valores que não
    são número (`str`, `bool`, `None`, `dict`, `list`) não são
    responsabilidade desta função — passam livres; a validade deles é
    checada por quem chama.
    """
    if isinstance(valor, bool):
        return True
    if isinstance(valor, (int, float)):
        return math.isfinite(valor)
    return True


def _numero_valido(valor: Any) -> bool:
    """True se `valor` tem o tipo certo para ser número.

    Recusa exatamente o que `_finito` deixa passar sem checar tipo: `None`
    (ausente), `bool` (subclasse de `int` em Python, mas não é número para
    fins desta validação) e qualquer outro tipo que não seja `int`/`float`.
    Não checa finitude — isso é papel de `_finito`. Quem chama aplica as
    duas em sequência: primeiro `_numero_valido` (é candidato a número?),
    depois `_finito` (é finito?).
    """
    return (
        valor is not None
        and not isinstance(valor, bool)
        and isinstance(valor, (int, float))
    )


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

# Premissas cujo valor não é numérico — não passam pela guarda de tipo
# `_numero_valido`/`_finito`. 'tv' (convenção terminal) e 'politica_tv'
# (política associada) são string ("gordon", "book", "convergencia",
# "encerra"); só a presença de 'tv' importa nesta fatia, e isso já é
# checado em `_validar_cenario` antes deste ponto. 'mid_year' é a flag
# booleana de convenção de meio de ano — bool é exatamente o tipo certo
# para ela, ao contrário de toda outra premissa, onde bool é recusado.
_PREMISSAS_NAO_NUMERICAS: frozenset = frozenset({"tv", "politica_tv", "mid_year"})

# --------------------------------------------------------------------------
# Vocabulário do triângulo g = RiR x retorno, por rota.
#
# A identidade tem 3 variáveis nomeadas: a taxa de crescimento (g), o
# retorno (roic na rota firm, roe na rota equity) e a taxa de reinvestimento
# (rir). O caso declara exatamente duas como input e a terceira como
# output — inputs e output juntos têm de ser uma permutação exata deste
# conjunto de 3, nunca um subconjunto (menos de 3 nomes distintos), nunca
# um superconjunto (nome de fora da identidade, mesmo que seja premissa
# válida da rota, como 'wacc').
# --------------------------------------------------------------------------

TRIANGULO_FIRM: frozenset = frozenset({"g", "roic", "rir"})
TRIANGULO_EQUITY: frozenset = frozenset({"g", "roe", "rir"})

_TRIANGULO_POR_ROTA: dict[str, frozenset] = {
    "firm": TRIANGULO_FIRM,
    "equity": TRIANGULO_EQUITY,
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

# Destes seis campos de topo, só estes três não têm validador dedicado a
# jusante que já rejeitaria `None` por conta própria: 'rota' cai em
# `_validar_rota` (rejeita `None` como rota desconhecida), 'acoes_diluidas'
# cai em `_validar_acoes_diluidas` (rejeita `None` por não ser número), e
# 'cenarios' cai no `if not cenarios` de `validar` (rejeita `None` por ser
# falsy). Sem esta checagem aqui, um `null` explícito nestes três passava
# a checagem de presença (`campo in caso` é verdadeiro) e nunca mais era
# examinado — `null` é uma saída bem plausível de um template ou de um
# agente upstream, não uma allowance deliberada para estes campos.
_CAMPOS_DE_TOPO_ONDE_NULO_E_AUSENTE: frozenset = frozenset({
    "companhia", "moeda", "data_analise",
})


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
        ausente = campo not in caso
        nulo = (
            not ausente
            and campo in _CAMPOS_DE_TOPO_ONDE_NULO_E_AUSENTE
            and caso[campo] is None
        )
        if ausente or nulo:
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
        valor = metrica_base.get("valor")
        if not _numero_valido(valor):
            raise CasoInvalido(
                f"'metrica_base.valor' ausente ou não numérico: {valor!r}. "
                "O motor recebe essa métrica direto, sem conversão, como "
                "a escala de todo o valuation — sem um número de verdade "
                "aqui não há nada para o motor rodar."
            )
        if not _finito(valor):
            raise CasoInvalido(
                f"'metrica_base.valor' não é um número finito: {valor!r}. "
                "NaN e Infinity não são escala válida — o motor recebe "
                "essa métrica direto, sem conversão, e o serializador do "
                "motor transforma float não-finito em `null` mais adiante, "
                "longe desta causa."
            )
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

    if rota == "firm":
        # Presença do bloco já está confirmada acima; falta confirmar que
        # está COMPLETO. Somar (ordem e sinal do waterfall) é
        # responsabilidade de `ponte.py` — aqui só se valida presença e
        # tipo de cada linha, para que o `KeyError` de uma linha faltando
        # vire backstop defensivo em `ponte.py`, nunca o erro que o
        # usuário vê primeiro.
        ponte = caso["ponte"] or {}
        for linha in CAMPOS_DA_PONTE:
            valor = ponte.get(linha)
            if not _numero_valido(valor):
                raise CasoInvalido(
                    f"campo 'ponte.{linha}' ausente ou não numérico na "
                    f"rota firm: {valor!r}. A ponte tem de declarar todas "
                    f"as linhas ({', '.join(CAMPOS_DA_PONTE)}) antes de "
                    "somar."
                )
            if not _finito(valor):
                raise CasoInvalido(
                    f"campo 'ponte.{linha}' não é um número finito: "
                    f"{valor!r}. NaN e Infinity não são valor válido de "
                    "linha da ponte — envenenam a soma em silêncio."
                )


def _validar_acoes_diluidas(caso: Caso) -> None:
    acoes = caso["acoes_diluidas"]
    if not _numero_valido(acoes) or not math.isfinite(acoes) or acoes <= 0:
        raise CasoInvalido(
            f"'acoes_diluidas' inválido: {acoes!r}. O número de ações "
            "diluídas precisa ser um número finito e positivo — é o "
            "denominador de Equity por ação em toda rota."
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
    vocabulario = _TRIANGULO_POR_ROTA[rota]
    if (
        len(inputs) != 2
        # 'output in inputs' seria redundante aqui: com len(inputs) == 2
        # garantido acima, se output duplica um input, a união abaixo tem
        # no máximo 2 elementos — nunca fecha com um vocabulário de 3
        # nomes, então a cláusula de igualdade de conjuntos já cobre esse
        # caso sozinha.
        or set(inputs) | {output} != vocabulario
    ):
        raise CasoInvalido(
            f"{prefixo}: triângulo inconsistente — inputs {inputs!r} e "
            f"output {output!r} têm de formar uma permutação exata de "
            f"{sorted(vocabulario)}: exatamente dois inputs distintos, um "
            "output que não repete nenhum dos inputs, e as três variáveis "
            f"dentro do vocabulário do triângulo da rota '{rota}'. O "
            "output tem de ser a variável que sobra, não uma das duas "
            "declaradas como input, nem uma variável de fora da "
            "identidade g = RiR x retorno."
        )

    premissas = cenario.get("premissas") or {}

    obrigatorias = _PREMISSAS_OBRIGATORIAS_POR_ROTA[rota]
    for campo in sorted(obrigatorias):
        if campo in premissas and premissas[campo] is not None:
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
        valor = premissas[campo]
        if campo in _PREMISSAS_NAO_NUMERICAS or valor is None:
            # 'tv'/'politica_tv' são string e 'mid_year' é bool — nenhuma
            # das três passa pela guarda numérica. Um `None` sobrevivente
            # até aqui só pode pertencer a uma premissa OPCIONAL: toda
            # premissa obrigatória com valor `None` já foi recusada acima,
            # no loop de `obrigatorias` — então `None` aqui é ausência
            # legítima (roic_tv, gp etc. só importam sob certas
            # convenções), não buraco de validação.
            continue
        if not _numero_valido(valor):
            raise CasoInvalido(
                f"{prefixo}: premissa '{campo}' ausente ou não numérica: "
                f"{valor!r}. Toda premissa numérica tem de ser int ou "
                "float — texto, bool ou outro tipo aqui envenena a conta "
                "a jusante em silêncio, porque o motor recebe esse valor "
                "direto, sem conversão."
            )
        if not _finito(valor):
            raise CasoInvalido(
                f"{prefixo}: premissa '{campo}' não é um número finito: "
                f"{valor!r}. NaN e Infinity não são valor válido de "
                "premissa — envenenam toda conta a jusante em silêncio."
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
