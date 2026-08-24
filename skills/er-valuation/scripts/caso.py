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
# Guarda estrutural de tipo em fronteira de pertencimento/iteração.
#
# Terceira vez que a mesma classe de defeito aparece neste módulo: um valor
# de tipo errado alcançando um `x not in <frozenset>`/`x not in <dict>`
# (não-hasheável: lista, dict) ou um `for item in valor` (não-lista: número,
# bool, e até `x or []` deixando passar um valor truthy não-lista) escapava
# como TypeError/AttributeError cru, não CasoInvalido — porque cada call
# site tinha de LEMBRAR de checar tipo antes, e nem todos lembravam. As duas
# funções abaixo fecham essa fronteira uma vez só, de forma estrutural: todo
# `in`/`not in` contra um vocabulário de nomes passa por `_exigir_texto`
# antes, e todo `for` sobre uma lista declarada pelo caso passa por
# `_exigir_lista` antes — inclusive nos pontos que já tinham guarda
# equivalente escrita à mão, para que exista uma única forma de fazer isso
# no arquivo inteiro, não duas.
# --------------------------------------------------------------------------

def _exigir_texto(valor: Any, campo: str) -> None:
    """Garante que `valor` é `str` antes de uma checagem de pertencimento a
    vocabulário (`x not in <frozenset>` ou `x not in <dict>` de nomes).

    Um valor não-hasheável (lista, dict) alcançando essa checagem levanta
    `TypeError` cru, antes de qualquer chance de nomear o campo; um valor
    hasheável mas do tipo errado (número, bool, `None`) produzia só uma
    recusa genérica de "fora do vocabulário", perdendo o motivo real (tipo
    errado, não nome desconhecido). Levanta `CasoInvalido` nomeando `campo`
    quando `valor` não é `str`. Não confere se o texto pertence ao
    vocabulário — isso continua responsabilidade de quem chama, depois
    desta guarda.
    """
    if not isinstance(valor, str):
        raise CasoInvalido(
            f"'{campo}' não é texto: {valor!r}. Precisa ser um nome "
            "(string) para ser confrontado com o vocabulário aceito."
        )


def _exigir_lista(valor: Any, campo: str) -> list:
    """Garante que `valor` é `list` antes de um `for item in valor`.

    Um valor não-lista chegando a esse `for` ou explode em `TypeError` cru
    (número, bool) ou, pior, itera em silêncio sobre algo que não é a
    coleção pretendida (string vira sequência de caracteres, dict vira
    sequência de chaves) — nenhuma das duas é a lista de itens que o
    restante do código presume, e a segunda nem levanta erro nenhum na
    hora, só produz um resultado sem sentido mais adiante. Levanta
    `CasoInvalido` nomeando `campo` quando `valor` não é `list`; devolve
    `valor` (já confirmado `list`) quando é, para uso direto no `for` de
    quem chama.
    """
    if not isinstance(valor, list):
        raise CasoInvalido(f"'{campo}' não é uma lista: {valor!r}.")
    return valor


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
# Reversa: eixos aceitos e o que a metodologia torna obrigatório.
#
# EIXO_OBRIGATORIO ('custo_capital') não é um default que este módulo
# preenche — é uma exigência da própria metodologia: o custo de capital
# implícito é um dos dois únicos eixos com observável direto de mercado
# para confrontar (o beta implícito, via CAPM invertido), o outro sendo o
# próprio alvo de múltiplo. Um caso que declare 'reversa' sem esse eixo é
# recusado, nunca completado em silêncio — mesma disciplina já aplicada à
# convenção terminal ('tv').
# --------------------------------------------------------------------------

EIXOS_DE_REVERSA: frozenset = frozenset({
    "custo_capital", "crescimento", "rentabilidade", "cap",
})

EIXO_OBRIGATORIO: str = "custo_capital"

# Sem 'rf' e 'erp' não há como inverter o CAPM em beta implícito
# (beta = (custo_implícito − rf) ÷ erp). Os dois só passam a ser exigidos
# quando o caso declara 'reversa' — fora disso, 'mercado' é só um bloco
# opcional.
#
# Unidade (FIX 4, revisão final): 'rf' e 'erp' são declarados em PONTOS
# PERCENTUAIS — 12.0 significa 12%, nunca 0.12 — a mesma convenção de
# 'raizes_*_%' que o motor devolve. Essa convenção só vivia num docstring;
# um caso declarando 'rf: 0.12' (fração, não ponto percentual) validava
# normalmente e produzia um beta implícito errado por ~100x, sem aviso
# nenhum. Nenhuma taxa livre de risco nem prêmio de risco de mercado abaixo
# de um ponto percentual ocorre na prática, então o intervalo ABERTO
# 0 < x < 1 é reconhecido como fração digitada por engano — recusado por
# `_validar_mercado`, sem alargar a faixa além disso.
CAMPOS_DE_MERCADO_OBRIGATORIOS: tuple = ("rf", "erp")

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

    Ordem de verificação: o caso em si -> campos de topo -> rota -> métrica x
    rota -> ponte x rota -> ações diluídas -> preço -> cada cenário (âncora,
    triângulo, premissas obrigatórias, premissas desconhecidas) -> blocos
    opcionais 'mercado', 'reversa' e 'sensibilidades', só quando presentes.
    Não modifica `caso`; não preenche nada — só confirma ou recusa.

    Revisão final (FIX 3): doze formatos malformados achados por sondagem
    manual escapavam desta função como AttributeError/TypeError cru — o
    portão recusava ANTES de qualquer chamada ao motor, mas sem motivo
    nomeado, porque o corpo desta função e das que ela chama presume tipo
    (dict, list, str) em cada boundary sem checar. A guarda abaixo cobre o
    caso raiz não sendo objeto (`None`, número, lista); as demais guardas de
    container (metrica_base, ponte, cada cenário, triângulo) vivem nas
    funções correspondentes, mais perto de onde o tipo importa.

    Revisão final #3: terceira vez que a mesma classe de defeito aparece —
    sete formas novas (eixos com lista dentro, grades_1d/grades_2d
    não-lista, premissa/premissa_x/premissa_y/cenario com tipo errado)
    ainda escapavam como TypeError cru, porque as guardas de tipo do FIX
    anterior cobriam containers (dict/list em si) mas não os valores
    ESCALARES testados em `x not in <vocabulário>` nem os `for` sobre
    `grades_1d`/`grades_2d`. Em vez de outra rodada de patches pontuais,
    `_exigir_texto` e `_exigir_lista` (acima) fecham essas duas fronteiras
    de forma estrutural, aplicadas em TODO ponto do módulo que faz esse
    tipo de checagem — inclusive nos que já funcionavam por guarda
    equivalente escrita à mão.
    """
    if not isinstance(caso, dict):
        raise CasoInvalido(
            f"caso.json inválido: o documento raiz tem de ser um objeto "
            "(com as chaves companhia, moeda, data_analise, rota, "
            f"metrica_base, acoes_diluidas, preco, cenarios), não "
            f"{type(caso).__name__}: {caso!r}."
        )

    _validar_campos_de_topo(caso)

    rota = caso["rota"]
    _validar_rota(rota)
    _validar_metrica(caso, rota)
    _validar_ponte(caso, rota)
    _validar_acoes_diluidas(caso)
    _validar_preco(caso)

    cenarios = caso["cenarios"]
    if not cenarios:
        raise CasoInvalido(
            "nenhum cenário declarado em 'cenarios': a metodologia exige "
            "ao menos um cenário (bear, base ou bull), cada um com âncora "
            "e triângulo próprios — um caso sem cenário não avalia nada."
        )
    if not isinstance(cenarios, dict):
        # Formato bem plausível de erro manual ou de agente upstream: uma
        # lista de nomes ou de objetos de cenário, em vez do dict nome ->
        # cenário que o resto desta função presume. `cenarios.items()` logo
        # abaixo levantaria AttributeError cru sem esta guarda.
        raise CasoInvalido(
            f"campo 'cenarios' não é um objeto: {cenarios!r}. Tem de mapear "
            "o nome de cada cenário (bear, base, bull) ao objeto do "
            "cenário (âncora, triângulo, premissas) — não uma lista."
        )
    for nome, cenario in cenarios.items():
        _validar_cenario(nome, cenario, rota)

    reversa_presente = caso.get("reversa") is not None
    _validar_mercado(caso, reversa_presente)
    _validar_reversa(caso, cenarios, rota)
    _validar_sensibilidades(caso, cenarios, rota)


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
    _exigir_texto(rota, "rota")
    if rota not in METRICAS_POR_ROTA:
        raise CasoInvalido(
            f"rota desconhecida: '{rota}'. Rotas suportadas nesta fatia: "
            f"{', '.join(sorted(METRICAS_POR_ROTA))}."
        )


def _validar_metrica(caso: Caso, rota: str) -> None:
    metrica_base = caso.get("metrica_base")
    if metrica_base is None:
        metrica_base = {}
    elif not isinstance(metrica_base, dict):
        raise CasoInvalido(
            f"'metrica_base' não é um objeto: {metrica_base!r}. Tem de "
            "declarar tipo, valor, periodo e fonte — é a escala de todo "
            "o valuation."
        )
    tipo = metrica_base.get("tipo")
    aceitas = METRICAS_POR_ROTA[rota]

    _exigir_texto(tipo, "metrica_base.tipo")
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
        # Revisão final (FIX 5): SKILL.md documenta metrica_base como
        # (tipo, valor, fonte) — mas 'fonte' nunca era validada aqui, embora
        # 'preco.fonte' já fosse (ver `_validar_preco`). A métrica-base é a
        # escala de todo o valuation; deixá-la como o único número do caso
        # sem proveniência auditável, enquanto o preço mantém a dele, é
        # inverter a prioridade — mesma disciplina, mesma mensagem.
        fonte = metrica_base.get("fonte")
        if not isinstance(fonte, str) or not fonte.strip():
            raise CasoInvalido(
                f"campo 'metrica_base.fonte' ausente ou vazio: {fonte!r}. "
                "Uma métrica-base sem fonte não é auditável — a "
                "metodologia exige rastrear de onde veio a escala de todo "
                "o valuation, do mesmo jeito que já exige para 'preco'."
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
        ponte = caso["ponte"]
        if ponte is None:
            ponte = {}
        elif not isinstance(ponte, dict):
            # Revisão final (FIX 3): ponte como lista ou string levantava
            # AttributeError cru no primeiro `.get()` da linha, abaixo.
            raise CasoInvalido(
                f"'ponte' não é um objeto: {ponte!r}. Declare cada linha "
                f"({', '.join(CAMPOS_DA_PONTE)}) como campo do objeto."
            )
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


def _validar_preco(caso: Caso) -> None:
    """Valida o bloco 'preco': presença, tipo, valor positivo, fonte e data.

    `avaliar()` lê `caso["preco"]["valor"]` para calcular o upside de cada
    cenário contra o valor que o motor devolve — sem esta validação aqui, um
    caso sem 'preco' (ou com 'preco.valor' ausente ou inválido) passava pelo
    portão e só quebrava depois, com `KeyError` cru, longe desta causa.
    'fonte' e 'data' não entram em conta nenhuma, mas um preço sem origem e
    sem data não é auditável.
    """
    preco = caso.get("preco")
    if not isinstance(preco, dict):
        raise CasoInvalido(
            f"campo 'preco' ausente ou não é um objeto: {preco!r}. O caso "
            "precisa declarar o preço observado (valor, fonte, data) — é "
            "contra ele que o upside de cada cenário é calculado."
        )

    valor = preco.get("valor")
    if not _numero_valido(valor) or not math.isfinite(valor) or valor <= 0:
        raise CasoInvalido(
            f"'preco.valor' inválido: {valor!r}. O preço observado precisa "
            "ser um número finito e positivo — é o denominador do upside "
            "calculado contra o valor que o motor devolve."
        )

    for campo in ("fonte", "data"):
        item = preco.get(campo)
        if not isinstance(item, str) or not item.strip():
            raise CasoInvalido(
                f"campo 'preco.{campo}' ausente ou vazio: {item!r}. Um "
                f"preço sem {campo} não é auditável — a metodologia exige "
                "rastrear de onde veio e quando foi observado cada preço "
                "usado no caso."
            )


def _validar_triangulo(prefixo: str, triangulo: Any, rota: str) -> None:
    """Valida a configuração do triângulo g = RiR x retorno.

    Extraída de `_validar_cenario` (Fatia B, Task 1) para ser compartilhada
    com as grades de sensibilidade, que declaram a mesma configuração por
    grade — mesma identidade, mesmo vocabulário por rota, mesma exigência
    de permutação exata. `prefixo` identifica quem está sendo validado
    (um cenário ou uma grade) nas mensagens de recusa.
    """
    if triangulo is not None and not isinstance(triangulo, dict):
        # Revisão final (FIX 3): triangulo como algo que não é `None` nem
        # objeto (ex.: int) levantaria TypeError cru em "inputs" not in
        # triangulo, logo abaixo — "in" exige um container.
        raise CasoInvalido(
            f"{prefixo}: 'triangulo' não é um objeto: {triangulo!r}. A "
            "identidade g = RiR x retorno exige um objeto com 'inputs' "
            "(lista de duas variáveis) e 'output' (a terceira)."
        )
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
    if (
        not isinstance(inputs, list)
        or not all(isinstance(item, str) for item in inputs)
        or not isinstance(output, str)
    ):
        # Revisão final (FIX 3): 'inputs' como int quebrava em len() logo
        # abaixo (TypeError); 'inputs' como lista de listas, ou 'output'
        # como lista, quebrava em set(inputs)/{output} (TypeError:
        # unhashable type) — as três formas malformadas achadas na
        # sondagem viram uma única recusa nomeada aqui, checando o tipo
        # certo (lista de nomes-texto; nome-texto) antes de qualquer
        # operação que presuma esse tipo.
        raise CasoInvalido(
            f"{prefixo}: triângulo com formato inválido — 'inputs' tem de "
            "ser uma lista de nomes (texto) e 'output' tem de ser um nome "
            f"(texto): inputs={inputs!r}, output={output!r}."
        )
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


def _validar_cenario(nome: str, cenario: dict, rota: str) -> None:
    prefixo = f"cenário '{nome}'"

    if not isinstance(cenario, dict):
        # Revisão final (FIX 3): um cenário individual como string ou lista
        # (em vez do objeto ancora/triangulo/premissas) levantava
        # AttributeError cru no `.get("ancora")` logo abaixo.
        raise CasoInvalido(
            f"{prefixo} não é um objeto: {cenario!r}. Cada cenário declara "
            "'ancora', 'triangulo' e 'premissas'."
        )

    if not cenario.get("ancora"):
        raise CasoInvalido(
            f"{prefixo} sem âncora: a metodologia exige um observável "
            "concreto por cenário (consenso, guidance vigente, histórico "
            "normalizado, run-rate, pares diretos) — cenário sem âncora é "
            "cenário inventado."
        )

    _validar_triangulo(prefixo, cenario.get("triangulo"), rota)

    premissas = cenario.get("premissas")
    if premissas is None:
        premissas = {}
    elif not isinstance(premissas, dict):
        # Revisão final #3: 'premissas' truthy mas não-dict (int, bool,
        # string não vazia) sobrevivia ao antigo `... or {}` — falsy só
        # cobre None/0/""/[]/{}, não 5 nem True — e o `for chave in
        # premissas` logo abaixo levantava TypeError cru (número, bool) ou
        # iterava caractere a caractere em silêncio (string). Mesmo padrão
        # já usado para metrica_base/ponte/mercado/reversa/sensibilidades/
        # cenário individual: presença de tipo, não valor por default.
        raise CasoInvalido(
            f"{prefixo}: 'premissas' não é um objeto: {premissas!r}. "
            "Declare cada premissa (g, roic, wacc, tv...) como campo do "
            "objeto."
        )

    chaves_nao_textuais = [chave for chave in premissas if not isinstance(chave, str)]
    if chaves_nao_textuais:
        # Revisão final (FIX 3): JSON de verdade nunca produz chave
        # não-string, mas caso.py aceita qualquer dict Python, inclusive um
        # montado por outro código, não lido de arquivo. Sem esta guarda,
        # `sorted(premissas)` mais abaixo levanta TypeError cru assim que
        # mistura uma chave string com uma não-string (comparação entre
        # tipos não é suportada em Python 3).
        raise CasoInvalido(
            f"{prefixo}: premissas com chave não textual: "
            f"{chaves_nao_textuais!r}. Toda chave de premissa tem de ser "
            "um nome (texto) — o motor traduz cada uma numa flag de linha "
            "de comando."
        )

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
        _exigir_texto(campo, f"{prefixo}: premissas")
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


# --------------------------------------------------------------------------
# Fatia B, Task 1: blocos opcionais 'mercado', 'reversa' e 'sensibilidades'.
#
# Os três são opcionais — um caso sem eles é exatamente tão válido quanto
# antes desta fatia. Mas 'reversa' presente muda o que 'mercado' exige
# (rf, erp deixam de ser opcionais) e o que 'reversa.eixos' precisa conter
# (custo_capital deixa de ser um eixo entre outros). Nenhuma das três
# funções abaixo calcula nada — só confirma presença, tipo e consistência,
# a mesma disciplina do resto do módulo.
# --------------------------------------------------------------------------

def _validar_mercado(caso: Caso, reversa_presente: bool) -> None:
    """Valida o bloco opcional 'mercado'.

    Sem 'reversa', 'mercado' é só um objeto opcional: só precisa ser um
    dict quando presente, e 'beta_observado' (se presente) precisa ser uma
    banda válida. Com 'reversa' presente, 'rf' e 'erp' passam a ser
    obrigatórios — sem eles não há como inverter o CAPM em beta implícito.

    'rf' e 'erp' são declarados em pontos percentuais (12.0 = 12%): um
    valor no intervalo aberto (0, 1) é recusado por ser quase certamente
    uma fração digitada por engano (FIX 4, revisão final). 'erp' também é
    recusado quando <= 0 (FIX 3): é o denominador da inversão do CAPM em
    beta implícito (beta = (custo_implícito − rf) / erp) — a mesma razão
    pela qual `_validar_acoes_diluidas` já recusa um denominador <= 0.
    """
    mercado = caso.get("mercado")

    if mercado is None:
        if reversa_presente:
            raise CasoInvalido(
                "bloco 'reversa' presente sem bloco 'mercado': sem 'rf' e "
                "'erp' não há beta implícito, e o beta implícito é o "
                "confronto que a reversa existe para produzir. Declare "
                "'mercado' com 'rf' e 'erp'."
            )
        return

    if not isinstance(mercado, dict):
        raise CasoInvalido(
            f"campo 'mercado' não é um objeto: {mercado!r}. Declare 'rf', "
            "'erp' e, opcionalmente, 'beta_observado', 'fonte' e 'data'."
        )

    if reversa_presente:
        for campo in CAMPOS_DE_MERCADO_OBRIGATORIOS:
            valor = mercado.get(campo)
            if not _numero_valido(valor):
                raise CasoInvalido(
                    f"campo 'mercado.{campo}' ausente ou não numérico: "
                    f"{valor!r}. Bloco 'reversa' presente exige 'rf' e "
                    "'erp' — sem eles não há como calcular o beta "
                    "implícito."
                )
            if not _finito(valor):
                raise CasoInvalido(
                    f"campo 'mercado.{campo}' não é um número finito: "
                    f"{valor!r}. NaN e Infinity não são valor válido de "
                    "mercado — envenenam o beta implícito em silêncio."
                )
            # FIX 4 (revisão final): 'rf' e 'erp' são pontos percentuais
            # (12.0 = 12%) — um valor no intervalo ABERTO (0, 1) é quase
            # certamente uma fração digitada por engano (0.12 em vez de
            # 12.0). Nenhuma taxa livre de risco nem prêmio de risco de
            # mercado abaixo de um ponto percentual ocorre na prática, então
            # a faixa é segura para recusar sem estreitar valor legítimo
            # algum (0 e 1 continuam aceitos; só o intervalo aberto recusa).
            if 0 < valor < 1:
                raise CasoInvalido(
                    f"'mercado.{campo}' parece fração, não ponto "
                    f"percentual: {valor!r}. Taxas de mercado neste caso "
                    "são declaradas em pontos percentuais (12.0 significa "
                    "12%) — um valor entre 0 e 1 é quase certamente uma "
                    "fração (por exemplo 0.12 em vez de 12.0) e produziria "
                    "um beta implícito errado por ~100x sem nenhum aviso. "
                    "Uma taxa livre de risco ou prêmio de risco de mercado "
                    "abaixo de um ponto percentual não ocorre na prática."
                )
            # FIX 3 (revisão final): 'erp' é o denominador da inversão do
            # CAPM em beta implícito (beta = (custo_implícito - rf) / erp,
            # em reversa._beta_implicito) — <= 0 faz essa conta explodir em
            # ZeroDivisionError (erp == 0) ou inverter o sinal do beta
            # (erp < 0) sem aviso nenhum. Mesma disciplina de
            # `_validar_acoes_diluidas`, que já recusa outro denominador
            # (acoes_diluidas) pela mesma razão.
            if campo == "erp" and valor <= 0:
                raise CasoInvalido(
                    f"'mercado.erp' inválido: {valor!r}. O prêmio de risco "
                    "de mercado é o denominador da inversão do CAPM em "
                    "beta implícito (beta = (custo_implícito - rf) / erp) "
                    "— precisa ser estritamente positivo, ou a conta "
                    "explode em ZeroDivisionError (erp == 0) ou inverte o "
                    "sinal do beta em silêncio (erp < 0)."
                )

    beta_observado = mercado.get("beta_observado")
    if beta_observado is not None:
        invalido = (
            not isinstance(beta_observado, list)
            or len(beta_observado) != 2
            or not all(_numero_valido(v) and _finito(v) for v in beta_observado)
            or not beta_observado[0] < beta_observado[1]
        )
        if invalido:
            raise CasoInvalido(
                f"'mercado.beta_observado' inválido: {beta_observado!r}. "
                "Tem de ser uma lista [mínimo, máximo] com dois números "
                "finitos e mínimo < máximo — é a banda de beta observado "
                "contra a qual o beta implícito é confrontado."
            )


def _validar_cenario_alvo(prefixo: str, cenario_nome: Any, cenarios: dict) -> None:
    """Valida que `cenario_nome` aponta para um cenário já declarado.

    FIX 3: compartilhada por `_validar_reversa` (`reversa.cenario`) e
    `_validar_sensibilidades` (`sensibilidades.cenario`) — os dois blocos
    checam a mesma coisa (o cenário-alvo tem de estar em `cenarios`),
    diferindo só no prefixo da mensagem. `cenarios` já chega validado como
    `dict` por `validar` antes de qualquer um dos dois chamar esta função.
    """
    _exigir_texto(cenario_nome, prefixo)
    if cenario_nome not in cenarios:
        raise CasoInvalido(
            f"'{prefixo}' aponta para cenário inexistente: "
            f"{cenario_nome!r}. Tem de ser um dos cenários declarados em "
            "'cenarios'."
        )


def _validar_reversa(caso: Caso, cenarios: dict, rota: str) -> None:
    """Valida o bloco opcional 'reversa': eixos, eixo obrigatório e cenário-alvo.

    A exigência de 'mercado' (rf, erp) quando 'reversa' está presente já foi
    confirmada por `_validar_mercado` antes desta função rodar — não é
    responsabilidade dela.
    """
    reversa = caso.get("reversa")
    if reversa is None:
        return

    if not isinstance(reversa, dict):
        raise CasoInvalido(
            f"campo 'reversa' não é um objeto: {reversa!r}. Declare "
            "'cenario' e 'eixos'."
        )

    eixos = reversa.get("eixos")
    if not isinstance(eixos, list) or not eixos:
        raise CasoInvalido(
            f"'reversa.eixos' ausente ou vazio: {eixos!r}. Declare ao "
            f"menos um eixo dentre {', '.join(sorted(EIXOS_DE_REVERSA))}, "
            "incluindo obrigatoriamente 'custo_capital' (custo de capital "
            "implícito)."
        )

    desconhecidos = []
    for eixo in eixos:
        _exigir_texto(eixo, "reversa.eixos")
        if eixo not in EIXOS_DE_REVERSA:
            desconhecidos.append(eixo)
    if desconhecidos:
        raise CasoInvalido(
            f"'reversa.eixos' contém eixo desconhecido: {desconhecidos!r}. "
            f"Eixos aceitos: {', '.join(sorted(EIXOS_DE_REVERSA))}."
        )

    if EIXO_OBRIGATORIO not in eixos:
        raise CasoInvalido(
            f"'reversa.eixos' sem 'custo_capital' (custo de capital "
            f"implícito): {eixos!r}. O custo de capital implícito é eixo "
            "obrigatório da metodologia em toda rodada de reversa — sem "
            "ele não há beta implícito, o único confronto direto contra "
            "um observável de mercado além do próprio alvo de múltiplo. "
            "Omitir não é escolha do analista."
        )

    cenario_nome = reversa.get("cenario")
    _validar_cenario_alvo("reversa.cenario", cenario_nome, cenarios)


def _validar_pontos(prefixo: str, pontos: Any) -> None:
    """Valida 'pontos' de uma grade: lista não vazia de números finitos.

    D5 do plano da fatia B: o caso declara os pontos explicitamente — nada
    de faixa automática. Uma grade sem pontos não é reproduzível.
    """
    if (
        not isinstance(pontos, list)
        or not pontos
        or not all(_numero_valido(v) and _finito(v) for v in pontos)
    ):
        raise CasoInvalido(
            f"{prefixo}: 'pontos' ausente, vazio ou com valor não "
            f"numérico: {pontos!r}. Cada grade declara os pontos do eixo "
            "explicitamente — sem faixa automática, a grade não é "
            "reproduzível."
        )


def _validar_grade_1d(grade: Any, rota: str, permitidas: frozenset) -> None:
    """Valida uma grade 1D: tipo do container, premissa e o resto.

    FIX 2: `permitidas` já chega SEM as premissas não-numéricas (ver
    `_validar_sensibilidades`) — uma grade varia PONTOS NUMÉRICOS ao longo
    de um eixo, e 'tv'/'politica_tv'/'mid_year' não são número. Por isso a
    rejeição abaixo distingue dois casos: premissa reconhecida pela rota
    mas não-numérica (mensagem dedicada, nomeando a premissa) de premissa
    realmente fora do vocabulário da rota (mensagem genérica, como antes).
    """
    if not isinstance(grade, dict):
        raise CasoInvalido(
            f"grade 1D de sensibilidade não é um objeto: {grade!r}. Cada "
            "grade declara 'premissa', 'pontos' e 'triangulo'."
        )

    premissa = grade.get("premissa")
    _exigir_texto(premissa, "grade 1D: premissa")
    if premissa not in permitidas:
        if premissa in _PREMISSAS_NAO_NUMERICAS:
            raise CasoInvalido(
                f"grade 1D com premissa '{premissa}': grade de "
                "sensibilidade varia apenas premissa numérica ao longo de "
                f"pontos — '{premissa}' não é numérica."
            )
        raise CasoInvalido(
            f"grade 1D com premissa '{premissa}' fora do vocabulário da "
            f"rota '{rota}': premissas aceitas: "
            f"{', '.join(sorted(permitidas))}."
        )

    prefixo = f"grade 1D '{premissa}'"
    _validar_pontos(prefixo, grade.get("pontos"))
    _validar_triangulo(prefixo, grade.get("triangulo"), rota)


def _validar_grade_2d(grade: Any, rota: str, permitidas: frozenset) -> None:
    """Valida uma grade 2D: tipo do container, as duas premissas e o resto.

    Mesma disciplina de `_validar_grade_1d` (FIX 2): `permitidas` já chega
    sem as premissas não-numéricas, e a rejeição distingue premissa
    não-numérica de premissa fora do vocabulário da rota.
    """
    if not isinstance(grade, dict):
        raise CasoInvalido(
            f"grade 2D de sensibilidade não é um objeto: {grade!r}. Cada "
            "grade declara 'premissa_x', 'premissa_y', 'pontos_x', "
            "'pontos_y' e 'triangulo'."
        )

    premissa_x = grade.get("premissa_x")
    premissa_y = grade.get("premissa_y")
    for eixo, premissa in (("x", premissa_x), ("y", premissa_y)):
        _exigir_texto(premissa, f"grade 2D: premissa_{eixo}")
        if premissa not in permitidas:
            if premissa in _PREMISSAS_NAO_NUMERICAS:
                raise CasoInvalido(
                    f"grade 2D com premissa_{eixo} '{premissa}': grade de "
                    "sensibilidade varia apenas premissa numérica ao "
                    f"longo de pontos — '{premissa}' não é numérica."
                )
            raise CasoInvalido(
                f"grade 2D com premissa_{eixo} '{premissa}' fora do "
                f"vocabulário da rota '{rota}': premissas aceitas: "
                f"{', '.join(sorted(permitidas))}."
            )

    if premissa_x == premissa_y:
        raise CasoInvalido(
            f"grade 2D com premissa_x e premissa_y na mesma premissa "
            f"'{premissa_x}': os dois eixos da grade têm de variar "
            "premissas diferentes — do contrário a grade colapsa numa "
            "diagonal, não num plano."
        )

    prefixo = f"grade 2D '{premissa_x}' x '{premissa_y}'"
    _validar_pontos(f"{prefixo} (eixo x)", grade.get("pontos_x"))
    _validar_pontos(f"{prefixo} (eixo y)", grade.get("pontos_y"))
    _validar_triangulo(prefixo, grade.get("triangulo"), rota)


# --------------------------------------------------------------------------
# Endurecimento (task 3B), RISCO 2: teto de células declaradas em
# 'sensibilidades'.
#
# Cada célula de grade é uma chamada de SUBPROCESSO ao motor congelado
# (sensibilidades.py, `_precificar_celula`) — não uma conta em memória.
# Uma grade declarada 20x20 são 400 dessas chamadas, e antes desta fatia
# nada avisava o analista disso até a rodada já estar em andamento.
#
# CUSTO_POR_CELULA_SEGUNDOS: medido nesta máquina, contra o vendor
# congelado, em 2026-08-24, sobre a fixture
# tests/fixtures/caso_reversa_firm.json (17 células: grades_1d com 5
# pontos + grades_2d 4x3). Duas medições independentes discordaram: uma
# deu 0,091–0,109 s/célula (mediana 0,093 em 5 rodadas seguidas, máquina
# ociosa) e outra 0,127–0,168 s/célula (4 rodadas, sob carga). O motor
# abre um subprocesso Python por célula, então o custo real depende da
# carga do sistema no momento — não existe "o" número.
#
# Adotamos 0,15, o extremo CONSERVADOR da faixa observada, por uma razão
# assimétrica: esta constante só alimenta a estimativa de tempo na
# mensagem de recusa, e uma estimativa que SUBESTIMA a espera é pior que
# uma que a superestima — o analista que ouve "3 minutos" e espera 6
# perde a confiança na mensagem. O número que aparece é sempre
# "estimado", nunca prometido; a contagem de células, que é o que de
# fato decide a recusa, é exata e não depende disto.
#
# TETO_PADRAO_DE_CELULAS: 2.000 células somadas (grades_1d + grades_2d,
# cada grade 2D contando len(pontos_x) x len(pontos_y)) ⟹ 2.000 x 0,15s
# ~ 300s (~5 min) ao custo adotado acima. É um número ESCOLHIDO, não
# medido: grande o bastante para cobrir uma sensibilidade generosa (por
# exemplo duas grades 2D de 30x30 = 1.800 células) sem exigir nada extra
# do analista no caso comum, pequeno o bastante para que uma declaração
# desproporcional (por exemplo 400x400 = 160.000 células, horas de
# subprocessos) seja recusada no gate — antes de qualquer chamada ao
# motor — em vez de descoberta no meio de uma rodada já paga. Por isso
# 'sensibilidades.limite_de_celulas' (ver `_validar_teto_de_celulas`)
# existe: o analista que precisa de mais (ou quer um teto mais apertado
# que o padrão) declara o número explicitamente, e a decisão fica
# registrada no caso — não escondida numa constante que ele nunca vê.
CUSTO_POR_CELULA_SEGUNDOS: float = 0.15  # extremo conservador da faixa medida, ver acima

TETO_PADRAO_DE_CELULAS: int = 2000


def _validar_teto_de_celulas(sensibilidades: dict, total_celulas: int) -> None:
    """Recusa quando `total_celulas` (grades_1d + grades_2d já somadas,
    cada grade 2D contando `len(pontos_x) x len(pontos_y)`) passa do teto
    — o padrão (`TETO_PADRAO_DE_CELULAS`) ou o que
    `sensibilidades.limite_de_celulas` declarar.

    Chamada de dentro de `_validar_sensibilidades`, portanto dentro de
    `validar` — que roda inteiro em `carregar`, ANTES de `avaliar` chamar
    o motor para qualquer coisa (cenário, eixo de reversa ou célula de
    grade). É este o "gate" da task 3B: uma declaração acima do teto é
    recusada aqui, nunca descoberta célula a célula no meio de uma rodada
    de subprocessos já em andamento.

    `limite_de_celulas` é opcional; ausente, o teto é o padrão. Quando
    presente, TEM de ser um número finito e positivo — não precisa ser
    maior que o padrão: um limite mais restritivo também é uma decisão
    legítima do analista (quer gastar menos tempo que o padrão permitiria).
    """
    limite = sensibilidades.get("limite_de_celulas")
    if limite is None:
        teto = TETO_PADRAO_DE_CELULAS
    else:
        if not _numero_valido(limite) or not _finito(limite) or limite <= 0:
            raise CasoInvalido(
                f"'sensibilidades.limite_de_celulas' inválido: {limite!r}. "
                "Quando declarado, tem de ser um número finito e positivo "
                "— é o teto de células (grades_1d + grades_2d somadas, "
                "cada grade 2D contando len(pontos_x) x len(pontos_y)) que "
                "o analista está levantando (ou reduzindo) deliberadamente "
                f"em relação ao padrão ({TETO_PADRAO_DE_CELULAS})."
            )
        teto = limite

    if total_celulas > teto:
        tempo_estimado_s = total_celulas * CUSTO_POR_CELULA_SEGUNDOS
        raise CasoInvalido(
            f"'sensibilidades': {total_celulas} células declaradas (soma "
            "de grades_1d + grades_2d, cada grade 2D contando "
            f"len(pontos_x) x len(pontos_y)) excede o teto de {teto} — "
            f"tempo estimado ao custo medido "
            f"({CUSTO_POR_CELULA_SEGUNDOS}s/célula, 2026-08-24): "
            f"~{tempo_estimado_s:.0f}s (~{tempo_estimado_s / 60:.1f} min). "
            "Cada célula é uma chamada de subprocesso ao motor congelado "
            "— uma grade grande não é uma conta mais lenta, é centenas ou "
            "milhares de processos. Declare "
            "'sensibilidades.limite_de_celulas' para levantar o teto "
            "deliberadamente, ou reduza os pontos declarados."
        )


def _validar_sensibilidades(caso: Caso, cenarios: dict, rota: str) -> None:
    """Valida o bloco opcional 'sensibilidades': cenário-alvo, cada grade e
    o teto de células somadas (RISCO 2 do endurecimento, task 3B).

    Independente de 'mercado'/'reversa' — os blocos não se exigem entre si.
    FIX 2: `permitidas` aqui já exclui as premissas não-numéricas — uma
    grade varia pontos numéricos ao longo de um eixo, e 'tv'/'politica_tv'/
    'mid_year' não são número; deixar passar produzia caso.json válido
    para uma grade que o motor não sabe rodar, e a recusa só aparecia
    depois, num subprocesso do motor.
    """
    sensibilidades = caso.get("sensibilidades")
    if sensibilidades is None:
        return

    if not isinstance(sensibilidades, dict):
        raise CasoInvalido(
            f"campo 'sensibilidades' não é um objeto: {sensibilidades!r}. "
            "Declare 'cenario', 'grades_1d' e 'grades_2d'."
        )

    cenario_nome = sensibilidades.get("cenario")
    _validar_cenario_alvo("sensibilidades.cenario", cenario_nome, cenarios)

    permitidas = _PREMISSAS_POR_ROTA[rota] - _PREMISSAS_NAO_NUMERICAS

    total_celulas = 0

    grades_1d = sensibilidades.get("grades_1d")
    if grades_1d is not None:
        # FIX 1: `... or []` só substitui valor FALSY — um `grades_1d`
        # truthy mas não-lista (número, bool) sobrevivia ao `or` e caía
        # direto no `for`, cru. `_exigir_lista` fecha isso nomeando o
        # campo antes de qualquer iteração.
        for grade in _exigir_lista(grades_1d, "sensibilidades.grades_1d"):
            _validar_grade_1d(grade, rota, permitidas)
            # `_validar_grade_1d` já confirmou `grade["pontos"]` como lista
            # de números finitos (via `_validar_pontos`) — `len()` aqui é
            # seguro, nunca alcançado por um formato malformado.
            total_celulas += len(grade["pontos"])

    grades_2d = sensibilidades.get("grades_2d")
    if grades_2d is not None:
        for grade in _exigir_lista(grades_2d, "sensibilidades.grades_2d"):
            _validar_grade_2d(grade, rota, permitidas)
            # Mesma disciplina: `_validar_grade_2d` já confirmou os dois
            # eixos de pontos. Uma grade 2D conta o PRODUTO das duas
            # dimensões — é essa a contagem de células que o motor de
            # fato roda (`sensibilidades.grade_2d`: uma chamada por
            # combinação de x e y), não a soma delas.
            total_celulas += len(grade["pontos_x"]) * len(grade["pontos_y"])

    _validar_teto_de_celulas(sensibilidades, total_celulas)


def carregar(caminho: Path) -> Caso:
    """Lê `caminho` como JSON utf-8, valida e devolve o dict validado.

    Não faz cache, não modifica o conteúdo, não preenche nada: devolve
    exatamente o que veio do arquivo, depois de confirmar que passa em
    `validar`.
    """
    caso = json.loads(Path(caminho).read_text(encoding="utf-8"))
    validar(caso)
    return caso
