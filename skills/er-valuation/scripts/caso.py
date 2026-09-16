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

import difflib
import json
import math
from pathlib import Path
from typing import Any, Callable

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
#
# Fora deste vocabulário, por decisão: `ev`/`pe` também aceitam uma família de
# inputs OPCIONAIS do gate de coerência do vetor — `--rir-observado`,
# `--ebitda-ic` e, desde v9.31, `--cash-yield` — que só confrontam/divergem um
# resultado já calculado, nunca mudam o valuation em si. Nenhum dos três entra
# em PREMISSAS_FIRM/PREMISSAS_EQUITY nem vira flag por `motor.py`. `--cash-
# yield` recebe o MESMO tratamento dos dois irmãos mais antigos: decisão de
# não expor, não omissão.
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

# Rota rampa (Fatia C, Task 1): composição bifásica do motor congelado
# (subcomando `rampa`) para capacidade PRÉ-CONSTRUÍDA — fase 1 é rampa de
# utilização (crescimento consome só giro; D&A do parque fixa em moeda),
# fase 2 é expansão de capacidade nova (bloco padrão). Vocabulário PRÓPRIO,
# não uma variação de PREMISSAS_FIRM: a rota não usa o triângulo
# g = RiR x retorno (g2 é premissa direta do vetor; RiR2/ROIC2 saem do
# motor como RESULTADO, nunca como escolha de input) — por isso 'rampa'
# não entra em `_TRIANGULO_POR_ROTA` mais abaixo, e `_validar_cenario` só
# valida triângulo para rotas presentes naquele dict. `util` e `g1` são
# alternativas — nunca as duas juntas, nunca nenhuma das duas — ver
# `_validar_util_xor_g1`.
PREMISSAS_RAMPA: frozenset = frozenset({
    "receita0", "ebitda0", "da_parque", "wk", "kappa", "g2", "wacc", "tax",
    "t_rampa", "n", "util", "g1", "tv", "roic_tv", "gp", "roic_book",
})

PREMISSAS_OBRIGATORIAS_RAMPA: frozenset = frozenset({
    "receita0", "ebitda0", "da_parque", "wk", "kappa", "g2", "wacc", "tax",
    "t_rampa", "tv",
})

_PREMISSAS_POR_ROTA: dict[str, frozenset] = {
    "firm": PREMISSAS_FIRM,
    "equity": PREMISSAS_EQUITY,
    "rampa": PREMISSAS_RAMPA,
}

_PREMISSAS_OBRIGATORIAS_POR_ROTA: dict[str, frozenset] = {
    "firm": PREMISSAS_OBRIGATORIAS_FIRM,
    "equity": PREMISSAS_OBRIGATORIAS_EQUITY,
    "rampa": PREMISSAS_OBRIGATORIAS_RAMPA,
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
    "rampa": frozenset({"EBITDA0"}),
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

# --------------------------------------------------------------------------
# F6 (revisão final, fatia 4C, achado do controlador): vocabulário COMPLETO de
# chaves de topo que este módulo (`validar`) ou `avaliar.py` de fato consomem.
# `_validar_campos_de_topo` só EXIGE as seis obrigatórias; cada bloco opcional
# abaixo só é examinado quando presente pelo NOME EXATO ('metrica_base',
# 'ponte', 'delimitador', 'preco', 'mercado', 'reversa', 'sensibilidades',
# 'sotp' — cada um com validador dedicado). Sem uma lista FECHADA, uma chave
# de topo com o nome errado ('stop' em vez de 'sotp', 'sensibilidade' em vez
# de 'sensibilidades') não batia em NENHUM desses nomes exatos e passava por
# `validar()` inteiro sem nunca ser examinada — o bloco pretendido era
# IGNORADO em silêncio, e o valuation saía sem um item material que o
# analista declarou (com 'sotp', a manchete muda).
#
# 'ticker' e 'data_base' são as duas únicas chaves SEM validador dedicado que
# mesmo assim pertencem ao vocabulário: 'ticker' é lido por `avaliar.py`
# (`caso.get("ticker")`) e ecoado em `resultados.json`; 'data_base' não é lido
# em lugar nenhum do wrapper — é anotação do analista (a data-base dos dados,
# distinta de 'data_analise') que este módulo já documenta como opcional de
# verdade (`test_data_base_nula_e_permitida`, tests/test_valuation_caso.py)
# sem nunca a consumir. As duas foram confirmadas rodando TODA fixture de
# `tests/fixtures/` por este gate — nenhuma outra chave legítima apareceu.
#
# Fatia D, Task 1: 'degrau' entrou no vocabulário — bloco opcional, validado
# por `_validar_degrau` (mais abaixo), mesma disciplina de 'reversa'/
# 'sensibilidades'/'sotp': sem o nome aqui, o gate recusaria o bloco como
# chave de topo desconhecida antes de examinar o conteúdo dele.
#
# Fatia 5D, Task 1: 'fronteira_de_escopo' entrou pela mesma razão — bloco
# opcional validado por `_validar_fronteira_de_escopo` (mais abaixo).
CHAVES_DE_TOPO_PERMITIDAS: frozenset = frozenset({
    # Obrigatórias — `_RAZOES_CAMPOS_DE_TOPO`, checadas por presença/não-nulo
    # em `_validar_campos_de_topo`.
    "companhia", "moeda", "data_analise", "rota", "acoes_diluidas", "cenarios",
    # Opcionais, cada uma com validador dedicado, condicional ou não à rota.
    "metrica_base", "ponte", "delimitador", "preco", "mercado", "reversa",
    "sensibilidades", "sotp", "degrau", "cenario_base", "fronteira_de_escopo",
    # Fatia 5F, Tasks 2 e 3: validadas por `_validar_metrica_forward`,
    # `_validar_escala_monetaria` e `_validar_conservacao_de_capital` (mais abaixo).
    "metrica_forward", "escala_monetaria", "conservacao_de_capital",
    # Fatia 5G, Task 1: validado por `_validar_escolhas_metodologicas` (mais abaixo).
    "escolhas_metodologicas",
    # Fatia 5G, Task 2: validados por `_validar_retorno_exigido`,
    # `_validar_pesos_de_probabilidade` e `_validar_cross_check` (mais abaixo).
    "retorno_exigido", "pesos_de_probabilidade", "cross_check",
    # Informativas: sem validador dedicado, consumidas (ticker) ou só
    # repassadas (data_base) legitimamente.
    "ticker", "data_base",
})


def _validar_sem_chaves_de_topo_desconhecidas(caso: Caso) -> None:
    """Recusa qualquer chave de topo fora de `CHAVES_DE_TOPO_PERMITIDAS`, nomeando-a.

    Mesma disciplina que `_validar_premissas` já aplica a uma premissa de
    cenário desconhecida (chave fora do vocabulário -> recusa nomeada, nunca
    ignorada em silêncio) — agora no nível de topo do caso. Roda cedo, logo
    depois de `_validar_campos_de_topo`: uma chave de topo desconhecida é
    quase sempre a causa de um bloco "ausente" mais adiante (o analista
    escreveu o bloco, só que com o nome errado) — nomear a chave errada aqui
    é mais direto do que deixar o caso seguir e recusar por outro motivo bem
    mais adiante, ou pior, validar normalmente com o bloco pretendido
    silenciosamente fora do valuation.

    `sorted(set(caso) - CHAVES_DE_TOPO_PERMITIDAS)` e o primeiro elemento
    (não todas de uma vez): mesma disciplina de "recusa na primeira
    violação" que `validar()` já documenta — múltiplas chaves desconhecidas
    seriam múltiplos erros de digitação independentes, e o analista corrige
    um de cada vez, como já faz para qualquer outra recusa deste módulo.
    """
    desconhecidas = sorted(set(caso) - CHAVES_DE_TOPO_PERMITIDAS)
    if not desconhecidas:
        return
    chave = desconhecidas[0]
    sugestao = difflib.get_close_matches(chave, CHAVES_DE_TOPO_PERMITIDAS, n=1)
    dica = f" Você quis dizer '{sugestao[0]}'? " if sugestao else " "
    raise CasoInvalido(
        f"chave de topo desconhecida no caso: '{chave}'.{dica}"
        "Uma chave fora do vocabulário aceito é quase sempre um nome de "
        "bloco digitado errado ('stop' em vez de 'sotp', 'sensibilidade' em "
        "vez de 'sensibilidades') — sem esta recusa, o bloco pretendido "
        "seria aceito com o nome errado e IGNORADO em silêncio, e o "
        "valuation sairia sem um item material que o analista declarou. "
        f"Chaves aceitas: {', '.join(sorted(CHAVES_DE_TOPO_PERMITIDAS))}."
    )


def _validar_moeda(caso: Caso) -> None:
    """Valida que 'moeda' é texto não vazio (F1, revisão final, fatia 4C).

    Quinta aparição, neste módulo, da mesma classe de defeito que
    `_exigir_texto` existe para fechar estruturalmente: um valor de tipo
    errado alcançando uma fronteira que presume tipo. `_validar_campos_de_topo`
    só confirma presença e não-nulo — nunca o TIPO nem o CONTEÚDO — então
    `moeda: ""` e `moeda: 123` passavam por ela normalmente. Os dois têm
    consequência real, não só teórica:

    - `moeda: ""` sobrevive à checagem de presença mas é FALSY — `motor.py:
      argv_para` só emite `--moeda` `if moeda:` (a mesma armadilha de
      truthiness que a correção do rf, nesta mesma fatia, evitou de propósito
      usando `is not None`), então o motor nunca recebe a flag e devolve a
      Guarda 2 de Damodaran ("MOEDA/REGIME NÃO DECLARADOS") dentro de
      `diagnosticos` — um alerta que `motor_espelho.js` declarava
      inalcançável (a premissa era "moeda é campo obrigatório", mas
      obrigatório aqui só quer dizer presente e não-nulo, nunca não-vazio) e
      para o qual não existe chave em `diagnosticos_chaves.json`.
    - `moeda: 123` sobrevive à mesma checagem e é TRUTHY — o motor recebe
      `--moeda 123` e roda normalmente (o CLI trata moeda como texto livre,
      não validado), mas `motor_espelho.js` chama `moeda.toLowerCase()` em
      toda chamada de diagnóstico (firm e equity) e estoura `TypeError: moeda.
      toLowerCase is not a function` — o laboratório quebra, não apenas
      diverge.

    Fechando aqui, no gate, `_exigir_texto` mais a checagem de branco (mesma
    disciplina de 'preco.fonte'/'metrica_base.fonte'/'delimitador') tornam
    verdadeira a premissa que o espelho já assumia — o espelho não muda, só o
    comentário dele passa a nomear a razão certa (o gate agora garante o que
    antes só parecia garantir).
    """
    moeda = caso["moeda"]
    _exigir_texto(moeda, "moeda")
    if not moeda.strip():
        raise CasoInvalido(
            f"'moeda' vazia ou em branco: {moeda!r}. Toda taxa do caso (g, "
            "gp, custo de capital) tem de estar travada na mesma unidade "
            "monetária — declarada em branco, o wrapper descarta o campo "
            "por truthiness (`if moeda:` em motor.py:argv_para) e o motor "
            "nunca recebe `--moeda`, emitindo a Guarda 2 de Damodaran "
            "('MOEDA/REGIME NÃO DECLARADOS') sem chave equivalente no "
            "espelho do relatório."
        )


def validar(caso: Caso) -> None:
    """Valida um caso já carregado; levanta `CasoInvalido` na primeira violação.

    Ordem de verificação: o caso em si -> campos de topo -> chaves de topo
    desconhecidas -> rota -> moeda -> métrica x rota -> ponte x rota ->
    delimitador x rota -> ações diluídas -> preço -> cada cenário (âncora,
    triângulo quando a rota tiver um, premissas obrigatórias, premissas
    desconhecidas) -> cenario_base (A3, obrigatório com mais de um cenário)
    -> degrau -> blocos opcionais 'mercado', 'reversa', 'sensibilidades',
    'sotp', 'fronteira_de_escopo', 'metrica_forward', 'escala_monetaria',
    'conservacao_de_capital', 'escolhas_metodologicas', 'retorno_exigido',
    'pesos_de_probabilidade' e 'cross_check', só quando
    presentes. As duas recusas de
    'reversa' por limitação (junto de 'degrau', na rota 'rampa') saem do
    registro `LIMITACOES_DE_REVERSA`, nos mesmos pontos de sempre. Não
    modifica `caso`; não preenche nada — só confirma ou recusa.

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

    _validar_chaves_enderecaveis(caso)
    _validar_campos_de_topo(caso)
    _validar_sem_chaves_de_topo_desconhecidas(caso)

    rota = caso["rota"]
    _validar_rota(rota)
    _validar_moeda(caso)
    _validar_metrica(caso, rota)
    _validar_ponte(caso, rota)
    _validar_delimitador(caso, rota)
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

    _validar_cenario_base(caso, cenarios)

    _validar_degrau(caso, cenarios, rota)

    reversa_presente = caso.get("reversa") is not None
    _validar_mercado(caso, reversa_presente)
    _validar_reversa(caso, cenarios)
    _validar_sensibilidades(caso, cenarios, rota)
    _validar_sotp(caso, cenarios)
    _validar_fronteira_de_escopo(caso)
    _validar_metrica_forward(caso, rota)
    _validar_escala_monetaria(caso)
    _validar_conservacao_de_capital(caso, rota)
    _validar_escolhas_metodologicas(caso, rota)
    _validar_retorno_exigido(caso, rota)
    _validar_pesos_de_probabilidade(caso, cenarios)
    _validar_cross_check(caso, rota)


def _validar_chaves_enderecaveis(no: object, caminho: str = "caso") -> None:
    """Revisão da 5E (F1): nenhuma chave do caso contém '.' nem é '*'. O caminho de um número do
    caso — em `catalogo.insumos_do_caso`, no `usado_em` do ledger e nos placeholders
    `{{caso:...}}` — separa segmentos por '.' e usa '*' como curinga; um cenário chamado
    'base.2026' tirava as premissas dele do mapa de insumos, e elas moviam o preço sem
    proveniência."""
    if isinstance(no, dict):
        for chave, valor in no.items():
            if isinstance(chave, str) and ("." in chave or chave == "*"):
                raise CasoInvalido(
                    f"chave '{chave}' em '{caminho}': nenhuma chave do caso pode conter '.' nem ser '*' — o "
                    "caminho de um número do caso separa segmentos por '.' e usa '*' como curinga, e um número "
                    "sob essa chave não seria endereçável pelo mapa de insumos, pelo ledger nem pelos "
                    "placeholders. Renomeie a chave (por exemplo, 'base_2026' em vez de 'base.2026')."
                )
            _validar_chaves_enderecaveis(valor, f"{caminho}.{chave}")
    elif isinstance(no, list):
        for indice, valor in enumerate(no):
            _validar_chaves_enderecaveis(valor, f"{caminho}.{indice}")


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
    # A rota rampa atravessa a MESMA ponte da rota firm — "a ponte para
    # preço é a mesma das outras rotas firm: o nd_efetivo de ponte.py vai
    # em --nd" (plano da Fatia C). Por isso as duas rotas compartilham a
    # exigência de presença e a validação de completude abaixo; só
    # 'equity' chega em Equity direto e não tem ponte de dívida nenhuma.
    rotas_com_ponte = ("firm", "rampa")

    if rota in rotas_com_ponte and not tem_ponte:
        raise CasoInvalido(
            f"campo 'ponte' ausente na rota {rota}: a rota {rota} chega em "
            "EV e precisa da ponte (dívida, caixa, outros ativos/passivos, "
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

    if rota in rotas_com_ponte:
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


def _validar_delimitador(alvo: dict, rota: str) -> None:
    """Valida o campo condicional-à-rota 'delimitador' em `alvo`.

    `alvo` é o CASO inteiro quando a rota rampa é a rota do caso (topo) —
    a chamada original, de dentro de `validar` — OU uma PARTE de SOTP
    quando a rampa é uma parte, não a rota do caso inteiro (Fatia C, Task
    3, chamada de dentro de `_validar_parte`). Generalizada de `caso: Caso`
    para `alvo: dict` para servir às duas chamadas com a MESMA regra e a
    MESMA mensagem — nenhuma das duas frases abaixo nomeia "caso" nem
    "parte", só a rota, então o texto continua correto nos dois lugares
    sem precisar de um parâmetro de prefixo.

    Só a rota 'rampa' tem fronteira de fase para delimitar: a composição
    bifásica do motor soma fase 1 (rampa de utilização) com fase 2
    (expansão), costuradas no ano T (`--t-rampa`) — e o próprio motor
    declara esse T "delimitador OBSERVAVEL obrigatorio" no help do CLI, mas
    não pode checar que o analista de fato ancorou o número num evento real
    (comissionamento datado, plena capacidade, termo de contrato, marco de
    guidance). Uma fase sem esse delimitador é um grau de liberdade
    disfarçado de análise — um modelo multifásico sem essa trava
    racionaliza qualquer preço. Por isso a rota 'rampa' EXIGE 'delimitador'
    como string não-vazia (não só presente — em branco não conta, é a
    mesma disciplina de 'preco.fonte'/'metrica_base.fonte').

    Fora da rota 'rampa' não existe fronteira de fase nenhuma para
    delimitar — 'firm' e 'equity' rodam um único regime, do início ao fim.
    Um 'delimitador' declarado ali seria um dado sem função nenhuma no
    motor; a mera PRESENÇA do campo (não só um valor ruim) já é recusada,
    para não silenciar um dado que não se aplica — mesma disciplina de
    'ponte' presente na rota equity.
    """
    tem_delimitador = "delimitador" in alvo

    if rota == "rampa":
        valor = alvo.get("delimitador")
        if not tem_delimitador or not isinstance(valor, str) or not valor.strip():
            raise CasoInvalido(
                f"campo 'delimitador' ausente ou vazio na rota rampa: "
                f"{valor!r}. A rota exige um evento OBSERVÁVEL que baliza "
                "o fim da fase 1 (comissionamento datado, plena "
                "capacidade, termo de contrato, marco de guidance) — uma "
                "fase sem esse delimitador é um grau de liberdade "
                "disfarçado de análise, não uma fronteira real."
            )
    elif tem_delimitador:
        raise CasoInvalido(
            f"campo 'delimitador' presente na rota '{rota}': só a rota "
            "rampa tem fronteira de fase para delimitar — não há fase 1 "
            f"nem fase 2 para balizar em '{rota}'. Remova o campo."
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


def _validar_premissas(prefixo: str, premissas_bruto: Any, rota: str) -> None:
    """Valida o vetor 'premissas' de um cenário OU de uma parte de SOTP:
    tipo do container, chaves textuais, premissas obrigatórias presentes,
    premissas desconhecidas recusadas, tipo numérico e finitude de cada
    uma, e a regra 'util' XOR 'g1' na rota rampa.

    Extraída de `_validar_cenario` (Fatia C, Task 2) para ser
    compartilhada com `_validar_parte`: uma parte de SOTP exige o MESMO
    vocabulário de premissas, por rota, que um cenário do caso inteiro —
    "cada parte tem rota, métrica, convenção... próprios" (D3 do plano da
    fatia C) é a mesma regra, só que aplicada a um objeto menor (parte, não
    caso inteiro). Duplicar este bloco de ~50 linhas numa segunda função
    seria exatamente a variante que a metodologia deste módulo proíbe —
    `prefixo` (`"cenário 'nome'"` ou `"parte 'nome'"`) é o único ponto que
    varia entre as duas chamadas.
    """
    premissas = premissas_bruto
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

    if rota == "rampa":
        _validar_util_xor_g1(prefixo, premissas)


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

    # O triângulo g = RiR x retorno só existe para rotas presentes em
    # `_TRIANGULO_POR_ROTA` (firm, equity). A rota rampa não usa esse
    # mecanismo: g2 é premissa direta do vetor, e RiR2/ROIC2 saem do motor
    # como resultado — nunca como escolha de input a validar aqui. Chamar
    # `_validar_triangulo` incondicionalmente levantaria `KeyError` cru em
    # `_TRIANGULO_POR_ROTA[rota]` para 'rampa' (e para qualquer rota futura
    # sem triângulo) — a guarda de membership evita isso.
    if rota in _TRIANGULO_POR_ROTA:
        _validar_triangulo(prefixo, cenario.get("triangulo"), rota)

    _validar_premissas(prefixo, cenario.get("premissas"), rota)


def _validar_util_xor_g1(prefixo: str, premissas: dict) -> None:
    """Valida que a rota rampa declara exatamente uma entre 'util' e 'g1'.

    As duas são alternativas, nunca as duas juntas: 'util' (utilização
    atual do parque, em 0-100%) deriva 'g1' internamente
    (g1 = (1/util)^(1/T) - 1) e força Receita_T = capacidade por
    construção; 'g1' declarado direto é a mesma taxa sem essa derivação —
    negativo roda o bloco de colheita (liberação de giro, FCFF > NOPAT).
    Sem nenhuma das duas a fase 1 não tem crescimento de volume nenhum;
    com as duas, qual delas o motor deveria obedecer fica ambíguo — o
    motor congelado só aceita uma (`--util` OU `--g1`).

    Chamada só para `rota == "rampa"`, depois que o loop de premissas
    permitidas/numéricas já confirmou que 'util' e 'g1', quando presentes,
    têm tipo numérico válido — esta função só decide QUANTAS das duas
    foram declaradas, não revalida tipo.
    """
    tem_util = premissas.get("util") is not None
    tem_g1 = premissas.get("g1") is not None
    if tem_util == tem_g1:
        if tem_util:
            raise CasoInvalido(
                f"{prefixo}: premissas 'util' e 'g1' declaradas juntas — "
                "são alternativas, nunca as duas: 'util' deriva 'g1' "
                "internamente e força Receita_T = capacidade por "
                "construção. Declare apenas uma das duas."
            )
        raise CasoInvalido(
            f"{prefixo}: nem 'util' nem 'g1' declarados — a fase 1 da "
            "rampa precisa de um crescimento de volume, derivado da "
            "utilização do parque ('util', em 0-100%) ou declarado direto "
            "('g1'; negativo é o bloco de colheita). Declare exatamente "
            "uma das duas."
        )


# --------------------------------------------------------------------------
# Fatia D, Task 1: bloco opcional 'degrau' (Gate 3 — capacidade ociosa de
# balanço / re-precificação). Mesmo padrão de 'reversa'/'sotp': bloco de
# caso, não rota nova (D1) — muda a rentabilidade de cada cenário, nunca o
# vocabulário da rota. Ver docs/superpowers/plans/2026-09-10-v4-fatia-degrau.md
# (D1-D9) e vendor/multiplos-justos/references/aplicacao.md §8.
# --------------------------------------------------------------------------

# F2 (onda de correção da revisão final): mesmos aliases legados que o motor
# canoniza ANTES de qualquer handler (`a.tv = tv_canon(a.tv)`, justos.py:26-27
# e ~1888-1894 — roda no topo de `main()`, antes de despachar para 'pe'/'ev'/
# 'degrau'). D6 (abaixo) comparava o literal "book": `tv: "ic"` — o alias
# legado — escapava da recusa, precificava com a rentabilidade PÓS-degrau no
# papel de MÉDIO do estoque (a conflação que D6 existe para impedir), e o
# `ALERTA_CONVENCAO_BOOK` que o motor emite nesse caso é descartado pelo
# wrapper (`avaliar.py` nunca lê essa chave da saída crua) — tornando falsa a
# alegação de que esse alerta é "inalcançável". Duplicado aqui (em vez de
# importado do motor congelado) porque este módulo, de propósito, não
# depende do motor — é o gate que roda ANTES de qualquer chamada a ele; mesma
# disciplina de `TV_CANON`/`tvCanon` em `motor_espelho.js:89-98`, que espelha
# o mesmo dict pela mesma razão (processo JS separado, sem import Python).
TV_CANON: dict = {
    "ic": "book", "spread": "gordon", "book": "book",
    "gordon": "gordon", "convergencia": "convergencia",
}


def _tv_canon(tv: Any) -> Any:
    """Espelha `justos.py:tv_canon` — 'ic'->'book', 'spread'->'gordon',
    identidade para as demais convenções e para qualquer valor fora do
    dict (inclusive tipo não-string: `.get(tv, tv)` devolve `tv` intacto,
    nunca levanta)."""
    return TV_CANON.get(tv, tv)


# A2 (onda de correção da revisão final): vocabulário que o gate reconhece
# para a premissa de escolha 'politica_tv' — sem aliases legados (ao
# contrário de 'tv', não há um segundo nome histórico para "contínua" nem
# para "encerra"), por isso um frozenset simples, não um dict de
# canonicalização. Existe para o catálogo de apresentação amarrar
# `premissas.equity.politica_tv.opcoes` contra ALGO fora do próprio
# catálogo — mesma disciplina de `TV_CANON` acima: sem esta fonte no gate,
# uma opção nova em `politica_tv.opcoes` (ou uma removida) só seria notada
# quando o relatório (fatia 5B) tentasse rotulá-la, nunca aqui na
# integração. Não é usado para VALIDAR o valor de `politica_tv` no gate —
# `_PREMISSAS_NAO_NUMERICAS` já trata 'politica_tv' como string opaca (ver
# comentário acima) e o motor aceita qualquer string, tratando tudo que não
# é 'continua' como 'encerra' (ternário em justos.py); fechar essa validação
# no gate seria mudança de comportamento fora do escopo desta onda (A2 pede
# só a trava do catálogo contra o vocabulário, não uma recusa nova).
POLITICA_TV_OPCOES: frozenset = frozenset({"continua", "encerra"})


# F3 (onda de correção da revisão final): mesma classe do F6 da fatia 4C
# (chave desconhecida ignorada em silêncio) — mas ali fechou só o nível de
# TOPO do caso (`CHAVES_DE_TOPO_PERMITIDAS`/`_validar_sem_chaves_de_topo_
# desconhecidas`, acima). O bloco 'degrau' não tinha vocabulário fechado
# nenhum: duas chaves opcionais com default silencioso mudavam a manchete
# quando o nome saía errado — "perfil-transicao" (a grafia da flag da CLI do
# vendor; o SKILL.md do Fleet nunca lista os nomes das chaves deste bloco,
# só o plano e o código, o que torna a grafia da CLI o erro natural) caía no
# default 'rampa' (46,56 em vez dos 43,01 declarados); "cambio" em vez de
# "fx" caía no default 1.0 (46,56 em vez de 9,10). Generalizado aqui num
# helper único, reusado pelo bloco 'degrau' inteiro, por 'indice_atual'/
# 'indice_alvo'/'vpa' (que já tinham checagem de TIPO via
# `_valor_numerico_degrau`, mas não de VOCABULÁRIO) e por cada entrada de
# 'degrau.m' — não uma cópia do helper de topo (mensagem e vocabulário
# diferentes por definição; ver o comentário de
# `_validar_sem_chaves_de_topo_desconhecidas` sobre por que aquele fica como
# está).
def _recusar_chave_desconhecida(dados: dict, permitidas: frozenset, rotulo: str) -> None:
    """Recusa a primeira chave de `dados` fora de `permitidas`, nomeando-a
    com sugestão por `difflib.get_close_matches` — mesma disciplina de
    `_validar_sem_chaves_de_topo_desconhecidas` (primeira violação, nunca
    todas de uma vez: cada chave desconhecida é um erro de digitação
    independente, corrigido um de cada vez), generalizada para qualquer
    bloco/objeto do caso com vocabulário fechado. `rotulo` entra na
    mensagem para localizar ONDE a chave apareceu (ex.: "'degrau'",
    "'degrau.indice_atual'", "'degrau.m.base'")."""
    desconhecidas = sorted(set(dados) - permitidas)
    if not desconhecidas:
        return
    chave = desconhecidas[0]
    sugestao = difflib.get_close_matches(chave, permitidas, n=1)
    dica = f" Você quis dizer '{sugestao[0]}'? " if sugestao else " "
    raise CasoInvalido(
        f"chave desconhecida em {rotulo}: '{chave}'.{dica}"
        "Uma chave fora do vocabulário aceito é quase sempre um nome "
        "digitado errado — sem esta recusa, o campo pretendido seria "
        "aceito com o nome errado e IGNORADO em silêncio (o default do "
        "campo correto se aplica sem aviso, podendo mudar o valuation). "
        f"Chaves aceitas em {rotulo}: {', '.join(sorted(permitidas))}."
    )


# As 9 chaves do bloco 'degrau' (D1-D9) e o vocabulário de cada objeto
# aninhado — ver `_caso_ancora()` em tests/test_valuation_degrau.py para o
# exemplo canônico com todas as 9 declaradas. 'indice_atual.fonte'/'.data' e
# 'indice_alvo.razao' são declaração pura (§11.4 pede "fonte, data" e "por
# que o administrável é esse") — nunca lidos por nenhuma conta, mas
# legítimos: ficam no vocabulário para não recusar o que o analista tem de
# poder declarar, mesmo sem consumidor.
_CHAVES_DEGRAU_PERMITIDAS: frozenset = frozenset({
    "indice_atual", "piso_teorico", "indice_alvo", "anos", "perfil_transicao",
    "razao_transicao", "vpa", "fx", "m",
})
_CHAVES_DEGRAU_INDICE_ATUAL_PERMITIDAS: frozenset = frozenset({"valor", "fonte", "data"})
_CHAVES_DEGRAU_INDICE_ALVO_PERMITIDAS: frozenset = frozenset({"valor", "razao"})
_CHAVES_DEGRAU_VPA_PERMITIDAS: frozenset = frozenset({"valor", "fonte", "data"})
_CHAVES_DEGRAU_M_ENTRADA_PERMITIDAS: frozenset = frozenset({"valor", "razao"})


def _valor_numerico_degrau(degrau: dict, campo: str, permitidas: frozenset) -> float:
    """Lê `degrau[campo]["valor"]` como número finito, recusando (nomeando
    'degrau.{campo}') quando o subcampo não é objeto, tem chave fora de
    `permitidas` (F3) ou o valor não é número finito. Não checa sinal nem
    outra restrição — isso é responsabilidade de quem chama, com a
    mensagem tailorizada por campo ('indice_atual'/'indice_alvo'/'vpa' têm
    razões de recusa diferentes para um valor não positivo)."""
    sub = degrau.get(campo)
    if not isinstance(sub, dict):
        raise CasoInvalido(
            f"'degrau.{campo}' não é um objeto: {sub!r}. Declare ao menos "
            "'valor'."
        )
    _recusar_chave_desconhecida(sub, permitidas, f"'degrau.{campo}'")
    valor = sub.get("valor")
    if not _numero_valido(valor) or not _finito(valor):
        raise CasoInvalido(
            f"'degrau.{campo}.valor' ausente, não numérico ou não finito: "
            f"{valor!r}."
        )
    return valor


def _validar_degrau(caso: Caso, cenarios: dict, rota: str) -> None:
    """Valida o bloco opcional 'degrau' (Gate 3 — capacidade ociosa de balanço).

    `caso.get("degrau")` ausente ou `None` é um caso perfeitamente válido
    sem degrau nenhum — exatamente tão válido quanto antes desta fatia
    existir. Presente, o bloco muda a rentabilidade de CADA cenário do
    caso (rentabilidade x h, g inalterado, rentabilidade terminal parada)
    — nunca abre um cenário próprio (D1).

    Ordem das checagens, cada uma nomeando o motivo: rota (D2) -> conflito
    com 'reversa'/'sensibilidades'/'sotp' (D7 — checado ANTES do conteúdo
    do bloco, para que a mensagem nomeie 'degrau', em vez de cair na
    recusa genérica de 'sotp'/'reversa' que já existe por outro motivo)
    -> tipo do bloco -> índices e piso -> transição (anos, perfil, razão)
    -> ponte de preço (vpa, fx) -> 'm' por cenário -> por cenário, tv=book
    sem roe_book (D6) e mid_year (o subparser `degrau` não aceita
    `--mid-year`).

    `cenarios` já chegou validado por `_validar_cenario` (ancora,
    triângulo, premissas) antes desta função rodar dentro de `validar` —
    cada `cenario["premissas"]` já é um dict de tipo conhecido; esta
    função lê direto, sem revalidar tipo.
    """
    degrau = caso.get("degrau")
    if degrau is None:
        return

    if rota != "equity":
        raise CasoInvalido(
            f"bloco 'degrau' presente na rota '{rota}': o degrau (D2) só é "
            "suportado na rota equity, a única em que o motor fecha o "
            "preço sozinho (--vpa/--fx). Na rota firm, transformar "
            "EV/Capital em EV exigiria aritmética de valuation no "
            "wrapper; a rota rampa é o domínio da capacidade "
            "PRÉ-CONSTRUÍDA, que a metodologia proíbe tratar como degrau x "
            "h (ignoraria o giro). Remova o bloco 'degrau', ou troque a "
            "rota do caso."
        )

    # Fatia 5D, Task 1 (D4): a recusa de 'reversa' junto de 'degrau' é uma
    # LIMITAÇÃO publicada (`resultados.limitacoes`) — aplicada pelo registro
    # `LIMITACOES_DE_REVERSA` (logo abaixo desta função), no mesmo ponto, na
    # mesma ordem (antes de 'sensibilidades' e 'sotp') e com a mesma mensagem
    # de sempre (`_mensagem_degrau_junto_de`, que as três recusas D7 dividem).
    _recusar_reversa_por_limitacao(caso, "reversa_com_degrau")
    for outro in ("sensibilidades", "sotp"):
        if caso.get(outro) is not None:
            raise CasoInvalido(_mensagem_degrau_junto_de(outro))

    if not isinstance(degrau, dict):
        raise CasoInvalido(
            f"campo 'degrau' não é um objeto: {degrau!r}. Declare "
            "'indice_atual', 'piso_teorico', 'indice_alvo', 'anos', "
            "'razao_transicao', 'vpa' e 'm' (um valor por cenário)."
        )
    _recusar_chave_desconhecida(degrau, _CHAVES_DEGRAU_PERMITIDAS, "'degrau'")

    indice_atual = _valor_numerico_degrau(
        degrau, "indice_atual", _CHAVES_DEGRAU_INDICE_ATUAL_PERMITIDAS)
    if indice_atual <= 0:
        raise CasoInvalido(
            f"'degrau.indice_atual.valor' não é positivo: {indice_atual!r}. "
            "É o índice OBSERVADO hoje (ex.: índice de Basileia, caixa "
            "excedente em % do mínimo) — não numérico positivo não é um "
            "índice válido."
        )

    piso_teorico = degrau.get("piso_teorico")
    if not _numero_valido(piso_teorico) or not _finito(piso_teorico) or piso_teorico <= 0:
        raise CasoInvalido(
            f"'degrau.piso_teorico' ausente, não numérico ou não positivo: "
            f"{piso_teorico!r}. É o limite matemático (mínimo regulatório, "
            "sem buffer) — declarado ao lado do piso administrável para "
            "que os dois nunca se confundam ('Piso teórico ≠ piso "
            "administrável', aplicacao.md §8)."
        )

    indice_alvo = _valor_numerico_degrau(
        degrau, "indice_alvo", _CHAVES_DEGRAU_INDICE_ALVO_PERMITIDAS)
    if indice_alvo <= 0:
        raise CasoInvalido(
            f"'degrau.indice_alvo.valor' não é positivo: {indice_alvo!r}. "
            "É o piso ADMINISTRÁVEL (mínimo regulatório + buffer) usado "
            "como cenário — não numérico positivo não é um índice válido."
        )
    if indice_alvo < piso_teorico:
        raise CasoInvalido(
            f"'degrau.indice_alvo.valor' ({indice_alvo!r}) menor que "
            f"'degrau.piso_teorico' ({piso_teorico!r}): o alvo é o piso "
            "ADMINISTRÁVEL, que nunca fica abaixo do piso teórico (o "
            "limite matemático, sem buffer) — 'Piso teórico ≠ piso "
            "administrável', aplicacao.md §8."
        )

    # F1 (onda de correção da revisão final): índice ATUAL abaixo do ALVO
    # administrável não é capacidade ociosa — é falta de capital, e a
    # metodologia não admite h < 1 aqui. §8 generaliza o §7 para eventos que
    # "elevam o lucro sem consumir capital novo" (aplicacao.md:883) e define
    # h como "expansão máxima da base geradora" (:934); derivacao.md:255
    # enuncia o degrau para um evento que eleve o lucro "por um fator h > 1".
    # Abaixo do administrável os buffers já estão violados — regime de
    # restrição a distribuição (aplicacao.md:964-966) —, e o vendor SKILL.md
    # classifica isso como evento de CAPITAL, "não é taxa nem degrau de
    # rentabilidade" (:219-221). Sem esta recusa, o índice 12 contra alvo 14
    # precificava 27,34 e o índice 10 (abaixo do próprio piso TEÓRICO)
    # precificava 22,07 — os dois em silêncio, sem alerta, e a rampa ainda
    # SUAVIZAVA a deficiência (o fator de captura amacia um incremento
    # negativo em vez de descontá-lo). O caso `indice_atual < piso_teorico`
    # já fica coberto por construção (alvo >= piso, checado acima). h = 1
    # (índice atual igual ao alvo) continua aceito — é a identidade
    # degenerada que o teste 2 da Task 1 usa; ali a manchete só se move
    # pela divergência de base (D8), nunca por um degrau inventado.
    if indice_atual < indice_alvo:
        raise CasoInvalido(
            f"'degrau.indice_atual.valor' ({indice_atual!r}) menor que "
            f"'degrau.indice_alvo.valor' ({indice_alvo!r}): índice atual "
            "abaixo do alvo administrável não é capacidade ociosa — é "
            "falta de capital (h < 1 não é degenerado, é erro de "
            "classificação). A metodologia só admite o degrau para um "
            "evento que eleve o lucro 'sem consumir capital novo' "
            "(aplicacao.md §8, linha 883), com h definido como a 'expansão "
            "máxima da base geradora' (linha 934) — sempre h >= 1 "
            "(derivacao.md:255, a proposição do degrau é para h > 1). Um "
            "índice atual abaixo do alvo é um evento de CAPITAL — o vendor "
            "SKILL.md classifica isso como 'não é taxa nem degrau de "
            "rentabilidade' (linhas 219-221). Modele-o como evento de "
            "capital (ponte: evento de caixa único) ou re-base do índice "
            "atual, nunca como degrau. Se 'degrau.indice_atual.valor' e "
            "'degrau.indice_alvo.valor' são de fato iguais, declare-os "
            "iguais (h = 1 é aceito — é a identidade degenerada)."
        )

    anos = degrau.get("anos")
    if "anos" not in degrau or not _numero_valido(anos) or not _finito(anos) or anos < 0:
        raise CasoInvalido(
            f"'degrau.anos' ausente, não numérico ou negativo: {anos!r}. "
            "Não tem default (D5): o motor defaulta '--anos 0' (degrau "
            "instantâneo), exatamente o que a trava 2 da metodologia "
            "proíbe presumir — o analista declara os anos até completar o "
            "deployment, mesmo quando a resposta é '0' explícito."
        )

    perfil_transicao = degrau.get("perfil_transicao", "rampa")
    if "perfil_transicao" in degrau:
        _exigir_texto(perfil_transicao, "degrau.perfil_transicao")
    if perfil_transicao not in ("rampa", "pontual"):
        raise CasoInvalido(
            f"'degrau.perfil_transicao' inválido: {perfil_transicao!r}. "
            "Tem de ser 'rampa' (deployment gradual, o default da própria "
            "metodologia) ou 'pontual' (degrau datado num ano só, apenas "
            "com evento datado declarado — licença, decisão regulatória, "
            "fechamento de aquisição)."
        )

    razao_transicao = degrau.get("razao_transicao")
    if not isinstance(razao_transicao, str) or not razao_transicao.strip():
        raise CasoInvalido(
            f"'degrau.razao_transicao' ausente ou vazia: "
            f"{razao_transicao!r}. É onde o analista declara o evento por "
            "trás do perfil de transição — com 'pontual', é ali que o "
            "evento DATADO é declarado (D5); sem essa declaração, a "
            "escolha de perfil é arbitrária."
        )

    vpa = _valor_numerico_degrau(degrau, "vpa", _CHAVES_DEGRAU_VPA_PERMITIDAS)
    if vpa <= 0:
        raise CasoInvalido(
            f"'degrau.vpa.valor' não é positivo: {vpa!r}. É o valor "
            "patrimonial por ação que faz a ponte de preço do degrau "
            "(preco_acao = P/VP x vpa / fx) — sem um número positivo aqui "
            "não há como o motor fechar o preço do cenário."
        )
    fonte_vpa = degrau["vpa"].get("fonte")
    if not isinstance(fonte_vpa, str) or not fonte_vpa.strip():
        raise CasoInvalido(
            f"'degrau.vpa.fonte' ausente ou vazia: {fonte_vpa!r}. Um valor "
            "patrimonial por ação sem fonte não é auditável — a "
            "metodologia exige rastrear de onde veio a ponte de preço do "
            "degrau, do mesmo jeito que já exige para 'preco'."
        )

    if "fx" in degrau:
        fx = degrau.get("fx")
        if not _numero_valido(fx) or not _finito(fx) or fx <= 0:
            raise CasoInvalido(
                f"'degrau.fx' presente mas não é positivo: {fx!r}. Quando "
                "declarado, é o câmbio que divide a ponte de preço "
                "(preco_acao = P/VP x vpa / fx) — ausente, o motor "
                "defaulta para 1.0."
            )

    m = degrau.get("m")
    if not isinstance(m, dict):
        raise CasoInvalido(
            f"'degrau.m' não é um objeto: {m!r}. Declare exatamente uma "
            "entrada por cenário do caso, cada uma com 'valor' (a "
            "eficiência marginal, em %) e 'razao'."
        )
    nomes_cenarios = set(cenarios)
    nomes_m = set(m)
    if nomes_m != nomes_cenarios:
        faltando = sorted(nomes_cenarios - nomes_m)
        sobrando = sorted(nomes_m - nomes_cenarios)
        detalhe = []
        if faltando:
            detalhe.append(f"faltando: {faltando}")
        if sobrando:
            detalhe.append(f"sobrando (não são cenário do caso): {sobrando}")
        raise CasoInvalido(
            "'degrau.m' não declara exatamente uma entrada por cenário do "
            f"caso ({'; '.join(detalhe)}). Cenários do caso: "
            f"{sorted(nomes_cenarios)!r}; cenários em 'degrau.m': "
            f"{sorted(nomes_m)!r}."
        )
    for nome_cenario, entrada in m.items():
        if not isinstance(entrada, dict):
            raise CasoInvalido(
                f"'degrau.m.{nome_cenario}' não é um objeto: {entrada!r}. "
                "Declare 'valor' (a eficiência marginal do capital "
                "liberado, em %) e 'razao'."
            )
        _recusar_chave_desconhecida(
            entrada, _CHAVES_DEGRAU_M_ENTRADA_PERMITIDAS, f"'degrau.m.{nome_cenario}'")
        valor_m = entrada.get("valor")
        if not _numero_valido(valor_m) or not _finito(valor_m) or valor_m < 0:
            raise CasoInvalido(
                f"'degrau.m.{nome_cenario}.valor' ausente, não numérico ou "
                f"negativo: {valor_m!r}. É a eficiência marginal do "
                "capital liberado (retorno marginal / retorno médio), em "
                "pontos percentuais — não tem default (D4): declare o "
                "valor e a razão por cenário (ex.: banda bear/base/bull "
                "70/100/130)."
            )
        razao_m = entrada.get("razao")
        if not isinstance(razao_m, str) or not razao_m.strip():
            raise CasoInvalido(
                f"'degrau.m.{nome_cenario}.razao' ausente ou vazia: "
                f"{razao_m!r}. 'm' não tem default (D4) — declare por que "
                "esse cenário usa essa eficiência marginal."
            )

    for nome_cenario, cenario in cenarios.items():
        premissas = cenario["premissas"]
        # F2: compara a convenção CANÔNICA (`_tv_canon`), não o literal —
        # 'tv: "ic"' é o mesmo 'book' aos olhos do motor (ver o comentário
        # de TV_CANON acima).
        if _tv_canon(premissas.get("tv")) == "book" and premissas.get("roe_book") is None:
            raise CasoInvalido(
                f"cenário '{nome_cenario}': 'tv' = 'book' (ou o alias "
                f"legado 'ic', que o motor canoniza para 'book' antes de "
                "qualquer handler) com 'degrau' presente e sem 'roe_book' "
                "declarado (D6, SKILL.md do vendor: \"obrigatório de "
                "fato\" com --tv book). Sem ele, o TV usaria a "
                "rentabilidade PÓS-degrau (marginal x h) no papel de "
                "MÉDIO do estoque — conflação marginal x médio AGRAVADA "
                "pelo degrau. Declare 'roe_book' nesse cenário, ou use "
                "tv='gordon'/'convergencia' (ou seus aliases)."
            )
        if "mid_year" in premissas:
            raise CasoInvalido(
                f"cenário '{nome_cenario}': premissa 'mid_year' presente "
                "com 'degrau' no caso — o subparser `degrau` do motor "
                "congelado não aceita '--mid-year'; passar essa premissa "
                "para a chamada do degrau quebraria o motor com um argv "
                "que o argparse recusa. Remova 'mid_year' do cenário, ou "
                "remova 'degrau' do caso."
            )


# --------------------------------------------------------------------------
# Fatia 5D, Task 1 (D4 do plano docs/superpowers/plans/2026-09-14-v4-item5d-
# tese.md): as limitações que tornam a reversa inadmissível no caso.
#
# A Análise exige reversa — o desenho fixa a saída do M4 como "valuation +
# reversa + sensibilidades" (§5), e o vendor torna o custo de capital
# implícito obrigatório nela —, mas este gate recusa o bloco 'reversa' em
# combinações que o Fleet ainda não implementa: junto de 'degrau' (D7 da
# fatia D, em `_validar_degrau`) e na rota 'rampa' (FIX 1 da revisão final da
# fatia C, em `_validar_reversa`). Nenhum bloco 'reversa', por mais bem
# formado, passa por essas recusas: são LIMITAÇÕES do caso, não erros de
# forma — e só a integração sabe delas. O relatório lê a chave publicada em
# `resultados.limitacoes` e o rótulo que o catálogo dá a ela (E3), nunca a
# regra.
#
# Por isso cada uma dessas recusas mora num registro, sob a chave pública que
# a nomeia. `LIMITACOES_DE_REVERSA` mapeia a chave para a função que devolve a
# mensagem de recusa quando a limitação vale para o caso (ou `None`, quando
# não vale). O gate recusa PELO registro, nos pontos e na ordem de sempre
# (`_recusar_reversa_por_limitacao`), e `reversa_indisponivel` consulta o
# MESMO registro — não existe uma segunda lista de condições para divergir da
# primeira. A trava de `tests/test_valuation_contrato.py` confere, fixture a
# fixture, que a chave sai publicada se e só se o gate recusa um bloco
# 'reversa' válido, e que a recusa é a da limitação publicada. Ela acompanha o
# gate NAS CONDIÇÕES QUE AS FIXTURES EXERCITAM: uma recusa de reversa nova
# escrita por fora deste registro reprova ali quando alguma fixture exercita a
# condição dela. Fora dessas condições a falha é fechada, nunca calada — o gate
# recusa a reversa, `limitacoes` sai vazia e a Análise não emite (HARD FAIL
# `analise_sem_reversa` no relatório). Por isso toda limitação nova entra com
# uma fixture que a exercite; a trava já o exige das registradas (toda
# limitação do registro aparece em alguma fixture). Revisão final da 5D, F5.
# --------------------------------------------------------------------------


def _mensagem_degrau_junto_de(outro: str) -> str:
    """Mensagem da recusa D7: bloco 'degrau' junto de `outro` ('reversa',
    'sensibilidades' ou 'sotp'). Uma só redação para as três — as de
    'sensibilidades' e 'sotp' saem direto de `_validar_degrau`; a de
    'reversa', do registro de limitações."""
    return (
        f"bloco 'degrau' presente junto de '{outro}': esta "
        "combinação não está implementada nesta fatia (D7) — as "
        "grades de sensibilidade, a reversa e o SOTP hoje "
        "precificam sem degrau, e misturar quebraria a regra da "
        "célula central (a célula na premissa do caso-base bate "
        "com a manchete). Limitação declarada, a reabrir quando "
        f"um caso pedir. Remova o bloco '{outro}', ou remova "
        "'degrau'."
    )


def _reversa_barrada_pelo_degrau(caso: Caso) -> str | None:
    """Limitação `reversa_com_degrau`: a mensagem da recusa D7 quando o caso
    declara 'degrau', ou `None`. Olha só o caso sem a reversa — a presença
    do bloco 'reversa' é checada por quem recusa
    (`_recusar_reversa_por_limitacao`), não aqui."""
    if caso.get("degrau") is None:
        return None
    return _mensagem_degrau_junto_de("reversa")


def _reversa_barrada_pela_rota_rampa(caso: Caso) -> str | None:
    """Limitação `reversa_na_rota_rampa`: a mensagem da recusa quando a rota
    do caso é 'rampa', ou `None`.

    FIX 1 (Crítico, revisão final da fatia C): a rota 'rampa' não tem
    vocabulário de reversa — `RESOLVER_POR_EIXO` (reversa.py) só mapeia
    'firm'/'equity' para a variável que cada eixo resolve (wacc/ke,
    roic/roe, g/g, cap/cap). Sem esta recusa, um caso rampa+reversa passava
    pelo gate inteiro e só quebrava DEPOIS, dentro de `reversa.reverter`
    (`RESOLVER_POR_EIXO[eixo]['rampa']`, KeyError cru), já com os cenários
    principais do caso rodados no motor. Decisão tomada, não reaberta aqui:
    recusar pelo NOME, como limitação declarada — mesmo padrão de
    equity+sotp (`_validar_sotp`). Acoplar reversa à composição bifásica da
    rampa exige decidir quais eixos essa composição de duas fases admite
    reverter, decisão de metodologia que o Fleet ainda não tomou.
    """
    if caso.get("rota") != "rampa":
        return None
    return (
        "bloco 'reversa' presente na rota 'rampa': esta combinação não "
        "está implementada nesta fatia. As premissas da rota rampa "
        "(receita0, ebitda0, da_parque, wk, kappa, g2, t_rampa...) não "
        "são o vocabulário que a máquina de reversa resolve contra — "
        "'RESOLVER_POR_EIXO' só conhece a tradução de eixo para "
        "variável (wacc/roic/g...) das rotas 'firm' e 'equity'. "
        "Acoplar reversa a uma composição bifásica exige decidir quais "
        "eixos essa composição admite reverter, uma decisão de "
        "metodologia que esta fatia não toma. O bloco 'reversa' pode "
        "ser usado com as rotas 'firm' e 'equity'. Remova o bloco, ou "
        "troque a rota do caso."
    )


# Chave pública da limitação -> função que devolve a mensagem de recusa (ou
# `None`). Na ordem em que `validar` aplica as recusas (`_validar_degrau` roda
# antes de `_validar_reversa`), que é também a ordem em que
# `reversa_indisponivel` as consulta. As chaves são o vocabulário de
# `resultados.limitacoes`, rotulado por `catalogo.limitacoes` (igualdade de
# conjunto travada em tests/test_catalogo_apresentacao.py).
LIMITACOES_DE_REVERSA: dict[str, Callable[[Caso], str | None]] = {
    "reversa_com_degrau": _reversa_barrada_pelo_degrau,
    "reversa_na_rota_rampa": _reversa_barrada_pela_rota_rampa,
}


def _recusar_reversa_por_limitacao(caso: Caso, chave: str) -> None:
    """Recusa o bloco 'reversa' do caso quando a limitação `chave` vale.

    O ponto único por onde o gate aplica uma recusa de reversa por
    limitação — chamado de `_validar_degrau` e de `_validar_reversa`, cada
    um nomeando a chave que aplica. Sem 'reversa' no caso, nada a recusar: a
    limitação continua valendo (e sai publicada via `reversa_indisponivel`),
    só não há bloco para barrar. Uma `chave` fora do registro levanta
    `KeyError` — erro de programação deste módulo, nunca de um caso."""
    if caso.get("reversa") is None:
        return
    recusa = LIMITACOES_DE_REVERSA[chave](caso)
    if recusa is not None:
        raise CasoInvalido(recusa)


def reversa_indisponivel(caso: Caso) -> str | None:
    """A chave da limitação que torna a reversa inadmissível no caso, ou `None`.

    Consulta o registro que o próprio gate aplica (`LIMITACOES_DE_REVERSA`),
    na ordem dele, e devolve a chave da primeira limitação que vale. Não
    depende de o caso declarar 'reversa': num caso validado, uma limitação
    que vale implica que o caso não declara reversa — o gate a teria
    recusado. Recebe um caso já validado (`validar`) e não revalida nada;
    `avaliar.py` publica o que ela devolve em `resultados.limitacoes`.
    """
    for chave, barreira in LIMITACOES_DE_REVERSA.items():
        if barreira(caso) is not None:
            return chave
    return None


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

    # Correção do rf no wrapper (f2844f3): 'mercado.rf' passou a chegar ao
    # motor mesmo sem 'reversa' — é o que alimenta a âncora macro do gp
    # (Damodaran). Antes daquela correção o rf sem reversa era inerte e podia
    # passar sem validação; agora um rf inválido vira alerta falso em
    # silêncio (0.12 digitado como fração entraria como 0,12%). Mesma régua
    # do ramo com reversa, aplicada sempre que 'rf' é declarado. 'erp' fica
    # como está: sem reversa ele não tem consumidor. 'rf' nulo é ausência —
    # o wrapper não o repassa (motor.argv_para pula None).
    rf = mercado.get("rf")
    if not reversa_presente and rf is not None:
        if not _numero_valido(rf) or not _finito(rf):
            raise CasoInvalido(
                f"'mercado.rf' inválido: {rf!r}. Declarado, ele vai ao motor "
                "e ancora o gp perpétuo (Damodaran) — precisa ser um número "
                "finito, em pontos percentuais (12.0 significa 12%)."
            )
        if 0 < rf < 1:
            raise CasoInvalido(
                f"'mercado.rf' parece fração, não ponto percentual: {rf!r}. "
                "Taxas de mercado neste caso são declaradas em pontos "
                "percentuais (12.0 significa 12%) — 0.12 entraria no motor "
                "como 0,12% e a âncora macro acusaria qualquer gp acima "
                "disso, sem aviso nenhum."
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


def _validar_cenario_base(caso: Caso, cenarios: dict) -> None:
    """Valida o campo opcional-condicional 'cenario_base' (A3, fatia 5A item 5).

    Nenhum cenário é "o base" por convenção implícita — o wrapper (e, a
    jusante, o relatório) precisa de UM cenário declarado como resposta
    para montar a manchete e o múltiplo de tela quando o caso tem mais de
    um cenário. Com um único cenário, a declaração é dispensável — aquele
    cenário só pode ser o base, e exigir o campo seria burocracia sem
    escolha real por trás —, mas se declarado mesmo assim, tem de apontar
    para um cenário que de fato existe, com a mesma disciplina de
    'reversa.cenario'/'sensibilidades.cenario'/'sotp.cenario'
    (`_validar_cenario_alvo`, reaproveitada aqui sem variante).

    Com mais de um cenário, 'cenario_base' é OBRIGATÓRIO: um caso
    multi-cenário sem essa declaração não tem como o wrapper escolher qual
    preço é "a resposta" sem inventar uma convenção — mesma disciplina de
    'tv' (convenção terminal) e da âncora por cenário: decisão do
    analista, nunca default de fábrica.
    """
    declarado = "cenario_base" in caso
    if len(cenarios) > 1 and not declarado:
        raise CasoInvalido(
            "campo 'cenario_base' ausente com mais de um cenário declarado "
            f"({sorted(cenarios)!r}): sem essa declaração não há como saber "
            "qual cenário é 'a resposta' para a manchete e o múltiplo de "
            "tela — decisão do analista, nunca convenção implícita ('base' "
            "por hábito, por exemplo)."
        )
    if not declarado:
        return
    _validar_cenario_alvo("cenario_base", caso.get("cenario_base"), cenarios)


def _validar_reversa(caso: Caso, cenarios: dict) -> None:
    """Valida o bloco opcional 'reversa': limitação da rota, eixos, eixo
    obrigatório e cenário-alvo.

    A exigência de 'mercado' (rf, erp) quando 'reversa' está presente já foi
    confirmada por `_validar_mercado` antes desta função rodar — não é
    responsabilidade dela.

    FIX 1 (Crítico, revisão final): a rota 'rampa' não tem vocabulário de
    reversa. A recusa pelo nome é a limitação `reversa_na_rota_rampa`,
    aplicada aqui pelo registro `LIMITACOES_DE_REVERSA` (fatia 5D, Task 1; a
    razão completa está em `_reversa_barrada_pela_rota_rampa`). Continua a
    primeira checagem desta função, antes do formato do bloco — nenhum
    bloco, por mais bem formado, passa por ela. O bloco 'reversa' continua
    disponível nas rotas 'firm' e 'equity'.
    """
    reversa = caso.get("reversa")
    if reversa is None:
        return

    _recusar_reversa_por_limitacao(caso, "reversa_na_rota_rampa")

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
    # FIX 1 (revisão final): guarda de membership uniforme com os outros
    # três call sites de `_validar_triangulo` (cenário, parte de SOTP,
    # blended de materialidade) — `_TRIANGULO_POR_ROTA` não tem chave para
    # 'rampa'. Inalcançável para 'rampa' pela API pública, depois da
    # recusa de rampa+sensibilidades em `_validar_sensibilidades` — mas o
    # comentário deste módulo, nos outros três sites, chama esta guarda
    # OBRIGATÓRIA; ausente destes dois, uma rota futura sem triângulo
    # quebraria aqui com KeyError cru.
    if rota in _TRIANGULO_POR_ROTA:
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
    # FIX 1 (revisão final): mesma guarda de membership de `_validar_grade_1d`
    # — ver o comentário lá.
    if rota in _TRIANGULO_POR_ROTA:
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

# F3 (onda de correção da revisão final, item 2): 'sensibilidades' silenciava
# chave desconhecida — em particular 'limite_de_celulas' (o parâmetro
# NUMÉRICO de grade citado no brief) é opcional com default silencioso
# (ausente, vale `TETO_PADRAO_DE_CELULAS`): um nome digitado errado faz o
# teto que o analista quis declarar (mais apertado OU mais largo que o
# padrão) desaparecer sem aviso — `sensibilidades.get("limite_de_celulas")`
# devolve `None` e o teto aplicado silenciosamente vira o padrão, não o que
# foi escrito no caso. Mesma classe de 'degrau.perfil_transicao'/'degrau.fx'.
_CHAVES_SENSIBILIDADES_PERMITIDAS: frozenset = frozenset({
    "cenario", "grades_1d", "grades_2d", "limite_de_celulas",
})


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

    FIX 1 (Crítico, revisão final): mesma decisão e mesmo motivo da recusa
    de reversa+rampa em `_validar_reversa` (ver aquele docstring) — mas
    aqui o sintoma pré-fix era mais cedo e mais cru. Toda grade (1D ou 2D)
    chama `_validar_triangulo`, que indexa `_TRIANGULO_POR_ROTA[rota]` — e
    'rampa' não é chave desse dict (a rota não usa o triângulo
    g = RiR x retorno: g2 é premissa direta do vetor). Um caso
    rampa+sensibilidades batia em `KeyError: 'rampa'` NO PORTÃO, na
    primeira grade declarada, antes de qualquer chamada ao motor — mas
    ainda cru, sem nomear o motivo real (a combinação não é suportada,
    não que o formato da grade esteja errado).
    """
    sensibilidades = caso.get("sensibilidades")
    if sensibilidades is None:
        return

    if rota == "rampa":
        raise CasoInvalido(
            "bloco 'sensibilidades' presente na rota 'rampa': esta "
            "combinação não está implementada nesta fatia. A rota rampa "
            "não usa o triângulo g = RiR x retorno (g2 é premissa direta "
            "do vetor; RiR2/ROIC2 saem do motor como resultado, nunca "
            "como escolha de input) — as premissas da rota rampa não são "
            "o vocabulário que uma grade de sensibilidade varia hoje, e "
            "decidir o que uma grade significa numa composição bifásica é "
            "decisão de metodologia que esta fatia não toma. O bloco "
            "'sensibilidades' pode ser usado com as rotas 'firm' e "
            "'equity'. Remova o bloco, ou troque a rota do caso."
        )

    if not isinstance(sensibilidades, dict):
        raise CasoInvalido(
            f"campo 'sensibilidades' não é um objeto: {sensibilidades!r}. "
            "Declare 'cenario', 'grades_1d' e 'grades_2d'."
        )
    _recusar_chave_desconhecida(
        sensibilidades, _CHAVES_SENSIBILIDADES_PERMITIDAS, "'sensibilidades'")

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


# --------------------------------------------------------------------------
# Fatia C, Task 2: bloco opcional 'sotp' — soma de partes, ponte única no
# topo.
#
# 'sotp' é independente da rota do caso: o caso continua precisando de tudo
# que 'firm'/'equity'/'rampa' já exigem (validado ANTES desta função rodar,
# dentro de `validar`) — 'sotp', quando presente, é uma composição
# ADICIONAL, nunca uma substituição da validação de topo.
#
# Cada parte é validada com o MESMO vocabulário por rota que um cenário usa
# (`_validar_metrica`, `_validar_triangulo`, `_validar_premissas`) — "uma
# parte em gordon e outra em book é normal, não inconsistência" (D3 do plano
# da fatia C). A rota da parte, porém, é restrita a quem de fato produz EV:
# `_ROTAS_DE_PARTE_SOTP` exclui 'equity', mesmo essa rota sendo válida em
# qualquer outro lugar do caso — ver o motivo no docstring de
# `_validar_parte`.
#
# Fatia C, Task 3 acrescenta três checagens a este bloco, todas opcionais
# ou condicionais (nenhuma muda o que já validava antes):
#   - a parede da safra (`tipo == "safra"` exige exatamente uma parte na
#     rota rampa — ver o bloco dentro de `_validar_sotp`);
#   - o delimitador de uma parte em rampa é campo DELA, não do caso, mas a
#     MESMA regra e a MESMA mensagem de `_validar_delimitador` (agora
#     generalizada para aceitar caso OU parte) — chamada de dentro de
#     `_validar_parte`;
#   - o bloco opcional 'sotp.materialidade.blended' (`_validar_materialidade`,
#     abaixo de `_validar_sotp`), com o mesmo vocabulário de um cenário,
#     na rota do CASO inteiro.
#
# Fatia C, Task 4 acrescenta duas checagens mais, fechando dois achados da
# revisão da Task 3 — as duas ANTES de `tipo`/`partes`/`topo`, porque são
# propriedades da COMBINAÇÃO caso+sotp, não do que `sotp` declara por
# dentro:
#   - a rota do caso não pode ser 'equity' quando `sotp` está presente —
#     SOTP soma EV (D3), e a rota equity não produz EV nem admite `ponte`
#     (`_validar_ponte` já proíbe o bloco nessa rota). Sem esta recusa
#     nomeada, a combinação alcançava `sotp.compor_partes` e quebrava
#     fundo, em `KeyError` sobre `caso["ponte"]` — um erro de
#     implementação, nunca uma mensagem para o analista. O braço
#     financeiro (holdco pura, banco, seguradora) numa SOTP é limitação
#     DECLARADA desta fatia — não veste a roupa de bug nem a de erro do
#     usuário.
#   - `sotp.cenario`, campo novo do contrato: mesma semântica e mesma
#     função de validação (`_validar_cenario_alvo`) que `reversa.cenario`/
#     `sensibilidades.cenario` já usam — aponta um cenário declarado em
#     `caso["cenarios"]`. `compor_partes` já recusava (desde a Task 2/3)
#     um `nome_cenario` inexistente passado por quem chama, mas até esta
#     task não havia como declará-lo no próprio `caso.json`; a conta de
#     `compor_partes` não muda com o nome (cada parte de SOTP carrega um
#     vetor de premissas fixo, não por cenário) — a exigência existe só
#     para que um nome ausente ou inexistente falhe alto no gate, antes de
#     `avaliar()` chamar o motor para qualquer coisa.
# --------------------------------------------------------------------------

_TIPOS_DE_SOTP: frozenset = frozenset({"segmento", "safra"})

# SOTP soma EV de partes (D3) — só rotas que o motor congelado de fato
# emite 'EV' para podem ser parte. Confirmado por sondagem direta do motor
# (2026-08-25): o subcomando 'pe' (rota equity) nunca emite 'EV' no JSON —
# chega em Equity direto (P/L x LL) — e não tem ponte de dívida nenhuma
# para desfazer. Somar a saída de uma parte 'equity' como se fosse EV
# misturaria escala de firm (EV) com escala de equity (Equity por ação já
# líquida de tudo), o exato erro de dupla-contagem que a trava do topo
# único (D3) existe para impedir. 'firm' e 'rampa' são as duas rotas que
# emitem 'EV' — as únicas aceitas aqui.
_ROTAS_DE_PARTE_SOTP: frozenset = frozenset({"firm", "rampa"})

# As duas linhas do topo que SEMPRE entram na soma (D4b), com sinal fixo —
# diferente de 'desconto_de_holding_pct'/'razao_do_desconto', que são
# opcionais e só existem juntas (D4).
_CAMPOS_NUMERICOS_DO_TOPO: tuple = (
    "custos_corporativos_vp", "participacoes_nao_consolidadas",
)

# F3 (onda de correção da revisão final, item 2): 'sotp.topo' silenciava uma
# chave desconhecida — em particular, 'desconto_de_holding_pct'/
# 'razao_do_desconto' são um PAR OPCIONAL com default silencioso (ausente,
# nenhum desconto de holding é aplicado): um nome digitado errado (ex.:
# 'desconto_holding_pct', sem o 'de') cai fora de `_CAMPOS_NUMERICOS_DO_TOPO`
# e nunca é lido por `topo.get("desconto_de_holding_pct")` — o desconto que o
# analista declarou desaparece da soma do topo em silêncio, mudando o equity
# do SOTP. Mesma classe do 'perfil_transicao'/'fx' do bloco 'degrau' —
# fechado com o mesmo helper.
_CHAVES_TOPO_SOTP_PERMITIDAS: frozenset = frozenset(
    _CAMPOS_NUMERICOS_DO_TOPO + ("desconto_de_holding_pct", "razao_do_desconto"))


def _validar_parte(prefixo: str, parte: dict) -> None:
    """Valida uma parte de SOTP: rota (restrita a quem produz EV), métrica,
    âncora, triângulo (quando a rota da parte tiver um) e premissas — o
    MESMO vocabulário que `_validar_cenario` exige para a rota dela.

    Chamada só depois que quem chama já confirmou `parte` como `dict` e
    `parte["nome"]` como string não vazia (`_validar_sotp`, abaixo) — esta
    função não repete essas duas checagens.
    """
    rota = parte.get("rota")
    _validar_rota(rota)
    if rota not in _ROTAS_DE_PARTE_SOTP:
        raise CasoInvalido(
            f"{prefixo}: rota '{rota}' não produz EV — SOTP soma o EV de "
            "cada parte (D3 do plano da fatia C), e a rota 'equity' chega "
            "em Equity direto (P/L x LL), sem EV e sem ponte de dívida "
            "nenhuma para desfazer; somar essa saída como EV misturaria "
            "escalas incompatíveis — o mesmo erro de dupla-contagem que a "
            f"trava do topo único existe para impedir. Rotas aceitas para "
            f"parte de SOTP: {', '.join(sorted(_ROTAS_DE_PARTE_SOTP))}."
        )

    # FIX 5 (Importante, revisão final): 'ponte' e 'acoes_diluidas' são
    # campos do CASO inteiro — a ponte cruza uma única vez, no topo do
    # SOTP (D3: "ponte por parte é o erro que a trava existe para
    # impedir", ver docstring de `sotp.py`). Sem esta guarda, uma parte que
    # declarasse um destes dois campos era aceita pelo portão e a
    # declaração era silenciosamente IGNORADA por `sotp._compor_parte`
    # (que chama `precificar_firm`/`precificar_rampa` sem nd_efetivo/
    # acoes, de propósito, exatamente para nunca cruzar ponte por parte) —
    # a falha exata que a parede de cruzamento único existe para impedir:
    # o analista que declara uma ponte (ou uma contagem de ações) por
    # parte acredita que ela foi usada ali e recebe um número plausível,
    # mas errado, porque o campo nunca chega a `_compor_parte`. Mesma
    # disciplina de `_validar_ponte` (recusa 'ponte' na rota equity) e
    # `_validar_delimitador` (recusa 'delimitador' fora da rota rampa):
    # presença do campo já é recusada, nomeando o motivo, nunca só um
    # valor ruim dentro dele.
    for campo_do_caso in ("ponte", "acoes_diluidas"):
        if campo_do_caso in parte:
            raise CasoInvalido(
                f"{prefixo}: campo '{campo_do_caso}' presente numa parte "
                "de SOTP: a ponte cruza uma única vez, no topo do SOTP, "
                "nunca por parte — uma parte declara EV, nunca Equity nem "
                "preço por ação. Este campo aqui é aceito e IGNORADO em "
                "silêncio por `compor_partes` (que precifica cada parte "
                "sem escala de dívida/ações, de propósito): o analista que "
                "declara isto acredita que a ponte foi cruzada nesta "
                f"parte e recebe um número plausível, mas errado. Remova "
                f"'{campo_do_caso}' da parte."
            )

    # `_validar_metrica` foi escrita para receber o CASO inteiro, mas só lê
    # `caso.get("metrica_base")` — uma parte tem a mesma chave, com o mesmo
    # shape (tipo, valor, fonte). Reaproveitada tal como está, sem variante.
    _validar_metrica(parte, rota)

    # Consequência de contrato (Fatia C, Task 3): na rota rampa do CASO
    # inteiro, 'delimitador' é campo de topo (`_validar_delimitador(caso,
    # rota)`, chamada de dentro de `validar`). Quando a rampa é uma PARTE
    # de SOTP em vez da rota do caso, o delimitador é campo DELA — mesma
    # regra, mesma mensagem, só o dict que muda (`_validar_delimitador` já
    # foi generalizada para aceitar qualquer um dos dois). Sem esta
    # chamada, uma parte em rampa sem delimitador validava normalmente — a
    # fronteira de fase da parte ficava tão silenciosa quanto a do caso
    # inteiro ficaria sem a checagem original.
    _validar_delimitador(parte, rota)

    if not parte.get("ancora"):
        raise CasoInvalido(
            f"{prefixo} sem âncora: cada parte de SOTP exige o mesmo "
            "observável concreto que a metodologia exige de um cenário — "
            "parte sem âncora é parte inventada."
        )

    if rota in _TRIANGULO_POR_ROTA:
        if "triangulo" not in parte:
            raise CasoInvalido(
                f"{prefixo} sem 'triangulo' declarado: cada parte de SOTP "
                "exige a mesma configuração g = RiR x retorno que a "
                "metodologia exige de um cenário — sem isso a taxa de "
                "reinvestimento da parte fica silenciosa."
            )
        _validar_triangulo(prefixo, parte.get("triangulo"), rota)

    _validar_premissas(prefixo, parte.get("premissas"), rota)


def _validar_topo_sotp(topo: Any) -> None:
    """Valida 'sotp.topo': os dois campos numéricos obrigatórios (D4b) e o
    par opcional desconto/razão (D4).

    'custos_corporativos_vp' e 'participacoes_nao_consolidadas' entram na
    soma do topo sempre, com sinal fixo — custo corporativo não alocado é
    despesa capitalizada, subtrai; participação não consolidada é ativo,
    soma (D4b). Por isso os dois são obrigatórios e numéricos, mesmo
    quando o valor é 0.0 — 0.0 é uma DECLARAÇÃO (não há custo corporativo
    não alocado), `null`/ausente é um BURACO na soma.

    'desconto_de_holding_pct' é opcional; quando declarado (não-nulo),
    'razao_do_desconto' TEM de ser string não vazia — D4: "desconto de
    holding só existe declarado com razão", a metodologia é explícita
    sobre nunca aplicar por hábito.
    """
    if not isinstance(topo, dict):
        raise CasoInvalido(
            f"'sotp.topo' ausente ou não é um objeto: {topo!r}. Declare "
            "'custos_corporativos_vp', 'participacoes_nao_consolidadas', "
            "'desconto_de_holding_pct' e 'razao_do_desconto' — é onde a "
            "ponte única do SOTP cruza, e só ali (D3)."
        )
    _recusar_chave_desconhecida(topo, _CHAVES_TOPO_SOTP_PERMITIDAS, "'sotp.topo'")

    for campo in _CAMPOS_NUMERICOS_DO_TOPO:
        valor = topo.get(campo)
        if not _numero_valido(valor):
            raise CasoInvalido(
                f"'sotp.topo.{campo}' ausente ou não numérico: {valor!r}. "
                "O topo soma as partes com os ajustes de topo (D4b) — sem "
                "um número de verdade aqui não há soma para fazer, mesmo "
                "quando o valor declarado é 0.0."
            )
        if not _finito(valor):
            raise CasoInvalido(
                f"'sotp.topo.{campo}' não é um número finito: {valor!r}. "
                "NaN e Infinity envenenam a soma do topo em silêncio."
            )

    desconto = topo.get("desconto_de_holding_pct")
    if desconto is not None:
        if not _numero_valido(desconto) or not _finito(desconto):
            raise CasoInvalido(
                "'sotp.topo.desconto_de_holding_pct' não é um número "
                f"finito: {desconto!r}."
            )
        # FIX 3 (Importante, revisão final): o portão exigia a razão
        # (não-vazia) mas não checava o DOMÍNIO do próprio número — só a
        # razão de existir. `equity_depois = equity_antes * (1 - desconto /
        # 100)` é a única fórmula que este campo aciona (sotp.py); um
        # `desconto` <= 0 inverte o sinal do fator e vira um PRÊMIO
        # disfarçado — confirmado: -25.0 leva o equity da fixture do
        # segmento de 6378.83 para 7973.54 (aumenta, não reduz) — uma
        # operação que não está na lista autorizada deste wrapper. Um
        # `desconto` >= 100 anula (100: fator 0) ou inverte (>100: fator
        # negativo) o equity. O intervalo ABERTO 0 < x < 100 é o domínio
        # inteiro em que a fórmula faz o que o nome do campo promete.
        if not (0 < desconto < 100):
            raise CasoInvalido(
                "'sotp.topo.desconto_de_holding_pct' fora do domínio: "
                f"{desconto!r}. Tem de estar estritamente entre 0 e 100. "
                "Um valor <= 0 é um PRÊMIO disfarçado de desconto — a "
                "fórmula `equity * (1 - desconto/100)` inverte de sinal e "
                "AUMENTA o equity quando o desconto é negativo, uma "
                "operação que não está na lista autorizada deste wrapper. "
                "Um valor >= 100 anula (100: fator zero) ou inverte "
                "(acima de 100: fator negativo) o equity. Se um prêmio de "
                "holding for algum dia uma necessidade metodológica real, "
                "ele entra pelo nome, através da metodologia — nunca por "
                "um truque de sinal neste campo."
            )
        razao = topo.get("razao_do_desconto")
        if not isinstance(razao, str) or not razao.strip():
            raise CasoInvalido(
                "'sotp.topo.desconto_de_holding_pct' declarado sem "
                "'razao_do_desconto' não vazia: a metodologia é explícita "
                "— desconto de holding só existe declarado com razão, "
                "nunca aplicado por hábito (D4). Declare a razão do "
                "desconto, ou remova o desconto."
            )


def _validar_sotp(caso: Caso, cenarios: dict) -> None:
    """Valida o bloco opcional 'sotp': rota do caso, cenário-alvo, tipo,
    partes (>= 2, nomes distintos, cada uma válida para a rota dela) e topo.

    `caso.get("sotp")` ausente ou `None` é um caso perfeitamente válido sem
    SOTP nenhum — exatamente tão válido quanto antes desta fatia existir.

    Fatia C, Task 4 acrescenta as duas primeiras checagens abaixo (rota e
    cenário), as duas antes de examinar o que `sotp` declara por dentro —
    ver o comentário acima de `_TIPOS_DE_SOTP` para a razão de cada uma.
    """
    sotp = caso.get("sotp")
    if sotp is None:
        return

    rota_do_caso = caso["rota"]
    if rota_do_caso == "equity":
        raise CasoInvalido(
            "bloco 'sotp' presente na rota equity: SOTP soma o EV de cada "
            "parte (D3), e a rota equity não tem leitura de EV — chega em "
            "Equity direto (P/L x LL), sem ponte de dívida para cruzar uma "
            "única vez no topo (a própria rota equity já proíbe declarar "
            "'ponte'). O braço financeiro (holdco pura, banco, seguradora) "
            "numa composição SOTP é limitação declarada desta fatia, não "
            "um erro do usuário: hoje não há EV para somar dele. Remova o "
            "bloco 'sotp', ou avalie o braço financeiro por fora desta "
            "composição."
        )

    if not isinstance(sotp, dict):
        raise CasoInvalido(
            f"campo 'sotp' não é um objeto: {sotp!r}. Declare 'tipo', "
            "'cenario', 'partes' e 'topo'."
        )

    cenario_nome = sotp.get("cenario")
    _validar_cenario_alvo("sotp.cenario", cenario_nome, cenarios)

    tipo = sotp.get("tipo")
    # FIX 2 (Importante, revisão final): quarta instância da mesma classe de
    # defeito neste módulo — um valor não-hasheável (lista, dict) alcançando
    # `x not in <frozenset>` levanta TypeError cru, no próprio módulo que
    # construiu `_exigir_texto` para fechar essa fronteira estruturalmente.
    # `sotp.tipo` tinha ficado de fora.
    _exigir_texto(tipo, "sotp.tipo")
    if tipo not in _TIPOS_DE_SOTP:
        raise CasoInvalido(
            f"'sotp.tipo' inválido: {tipo!r}. Tem de ser um de "
            f"{', '.join(sorted(_TIPOS_DE_SOTP))} — 'segmento' (partes "
            "economicamente distintas) ou 'safra' (base instalada x "
            "capital novo)."
        )

    partes = _exigir_lista(sotp.get("partes"), "sotp.partes")
    if len(partes) < 2:
        raise CasoInvalido(
            f"'sotp.partes' com {len(partes)} parte(s): SOTP soma ao "
            "menos duas partes — soma de uma parte só é o consolidado com "
            "passos a mais, não SOTP nenhum."
        )

    nomes: list = []
    for indice, parte in enumerate(partes):
        if not isinstance(parte, dict):
            raise CasoInvalido(
                f"'sotp.partes[{indice}]' não é um objeto: {parte!r}. "
                "Cada parte declara 'nome', 'rota', 'metrica_base', "
                "'ancora', 'triangulo' e 'premissas'."
            )
        nome = parte.get("nome")
        if not isinstance(nome, str) or not nome.strip():
            raise CasoInvalido(
                f"'sotp.partes[{indice}]' sem 'nome' válido: {nome!r}. "
                "Cada parte precisa de um nome não vazio — é a chave que "
                "identifica a parte no resultado."
            )
        nomes.append(nome)

    repetidos = sorted({nome for nome in nomes if nomes.count(nome) > 1})
    if repetidos:
        raise CasoInvalido(
            f"'sotp.partes' com nome repetido: {repetidos!r}. Cada parte "
            "precisa de um nome distinto — é a chave que identifica a "
            "parte no resultado."
        )

    # Parede da safra (Fatia C, Task 3): tradução mecânica de "o
    # crescimento da parte instalada é SÓ rampa; o da expansão é SÓ
    # capital novo — a mesma receita nunca aparece nas duas". Checada AQUI
    # — antes da validação profunda de cada parte, logo abaixo — para que
    # a violação da parede seja sempre o motivo nomeado na recusa, nunca
    # mascarada por um efeito colateral de outra parte malformada (por
    # exemplo, uma segunda parte em rampa que também não declarou
    # 'delimitador' — sem essa ordem, seria essa a mensagem que o
    # analista veria, não a parede). `parte.get("rota")` é seguro mesmo
    # antes de `_validar_rota` rodar: comparação de igualdade contra a
    # string 'rampa' nunca levanta, seja qual for o tipo do valor.
    if tipo == "safra":
        partes_em_rampa = [p for p in partes if p.get("rota") == "rampa"]
        if len(partes_em_rampa) != 1:
            raise CasoInvalido(
                f"'sotp.tipo' safra com {len(partes_em_rampa)} parte(s) "
                "na rota 'rampa': a parede da safra exige exatamente uma "
                "parte na rota rampa — a base instalada. O crescimento da "
                "parte instalada é SÓ rampa; o crescimento da expansão é "
                "SÓ capital novo, pelo fluxo padrão (rota firm) — a "
                "mesma receita nunca pode aparecer nas duas. Zero partes "
                "em rampa apaga a base instalada da composição; duas ou "
                "mais partes em rampa deixa ambíguo qual delas é a base "
                "instalada de verdade."
            )

    for parte in partes:
        _validar_parte(f"parte '{parte['nome']}'", parte)

    _validar_topo_sotp(sotp.get("topo"))
    _validar_materialidade(sotp, caso["rota"])


def _validar_materialidade(sotp: dict, rota: str) -> None:
    """Valida o bloco opcional 'sotp.materialidade': quando presente,
    'blended' é um vetor de premissas completo — o MESMO vocabulário que
    um cenário ou uma parte exigem (ancora, triângulo quando a rota tiver
    um, metrica_base, premissas) — reaproveitando `_validar_metrica`,
    `_validar_triangulo` e `_validar_premissas`, sem variante nova.

    `rota` aqui é a rota do CASO inteiro (`caso["rota"]`), não a de uma
    parte: o vetor blended é a versão consolidada do caso inteiro — "as
    premissas consolidadas" — então roda pela mesma rota que o resto do
    caso já usa. É por isso que 'blended' não declara 'rota' própria (ao
    contrário de uma parte de SOTP): não há uma rota "da materialidade",
    só a rota do caso, aplicada a um vetor de premissas alternativo.

    Ausente ou `None`: SOTP sem 'materialidade' é tão válido quanto SOTP
    com ela — comparar segmentado x blended é OPCIONAL, o analista decide
    se declara o vetor consolidado.
    """
    materialidade = sotp.get("materialidade")
    if materialidade is None:
        return

    if not isinstance(materialidade, dict) or not isinstance(materialidade.get("blended"), dict):
        raise CasoInvalido(
            f"'sotp.materialidade' inválido: {materialidade!r}. Quando "
            "declarado, tem de ser um objeto com 'blended' (ancora, "
            "triângulo quando a rota do caso tiver um, metrica_base, "
            "premissas) — o vetor de premissas consolidado, na mesma "
            "rota do caso inteiro."
        )

    blended = materialidade["blended"]
    prefixo = "sotp.materialidade.blended"

    # Mesmo vocabulário de metrica_base que o caso inteiro e cada parte já
    # exigem — `_validar_metrica` só lê `alvo.get("metrica_base")`, não
    # importa se `alvo` é o caso, uma parte ou (agora) o vetor blended.
    _validar_metrica(blended, rota)

    if not blended.get("ancora"):
        raise CasoInvalido(
            f"{prefixo} sem âncora: o vetor blended exige o mesmo "
            "observável concreto que a metodologia exige de um cenário "
            "ou de uma parte — vetor sem âncora é vetor inventado."
        )

    if rota in _TRIANGULO_POR_ROTA:
        if "triangulo" not in blended:
            raise CasoInvalido(
                f"{prefixo} sem 'triangulo' declarado: o vetor blended "
                "exige a mesma configuração g = RiR x retorno que a "
                "metodologia exige de um cenário — sem isso a taxa de "
                "reinvestimento do blended fica silenciosa."
            )
        _validar_triangulo(prefixo, blended.get("triangulo"), rota)

    _validar_premissas(prefixo, blended.get("premissas"), rota)


# --------------------------------------------------------------------------
# Fatia 5D, Task 1 (D3 do plano docs/superpowers/plans/2026-09-14-v4-item5d-
# tese.md): bloco opcional 'fronteira_de_escopo' (§14 do desenho).
#
# A metodologia declara três classes de companhia fora do seu escopo como
# métrica-manchete: vida econômica finita (mineração, óleo e gás, concessão
# com termo), REITs e imobiliárias, e pré-lucro ou introdução. Sob fronteira
# declarada a entrega continua — a arquitetura dominante e por quê, as
# perguntas da tese, a leitura do que o preço embute, uma conclusão
# qualitativa e condicional —, mas sem preço-alvo de manchete, que o
# relatório reprova (fatia 5D, Task 2). A fronteira é metodologia, então é
# declaração do CASO: validada aqui, publicada pela integração
# (`resultados.fronteira_de_escopo`) e rotulada pelo catálogo
# (`fronteiras_de_escopo`, igualdade de conjunto com
# `CLASSES_DE_FRONTEIRA_DE_ESCOPO` travada em
# tests/test_catalogo_apresentacao.py). Vocabulário fechado em todo nível,
# mesma disciplina do bloco 'degrau'.
# --------------------------------------------------------------------------

CLASSES_DE_FRONTEIRA_DE_ESCOPO: frozenset = frozenset({
    "vida_economica_finita", "reit_imobiliaria", "pre_lucro",
})

_CHAVES_FRONTEIRA_DE_ESCOPO_PERMITIDAS: frozenset = frozenset({
    "classe", "arquitetura_dominante", "razao",
})

# O que cada texto obrigatório do bloco declara — entra na mensagem de recusa.
_RAZOES_TEXTOS_DA_FRONTEIRA: dict[str, str] = {
    "arquitetura_dominante": (
        "é a arquitetura de valuation que a companhia exige no lugar da "
        "métrica-manchete — o primeiro entregável sob fronteira (§14)."
    ),
    "razao": (
        "é por que a companhia está fora do escopo — sem ela, a fronteira "
        "vira uma saída cômoda para não emitir preço, não uma declaração "
        "auditável."
    ),
}


def _validar_fronteira_de_escopo(caso: Caso) -> None:
    """Valida o bloco opcional 'fronteira_de_escopo': tipo, chaves, classe e textos.

    Ausente ou `None` é um caso sem fronteira nenhuma — exatamente tão válido
    quanto antes desta fatia. Presente, tem de ser um objeto só com
    'classe', 'arquitetura_dominante' e 'razao' (chave fora disso recusada
    com sugestão, `_recusar_chave_desconhecida`); 'classe' é texto dentro de
    `CLASSES_DE_FRONTEIRA_DE_ESCOPO`, recusada pelo nome com sugestão por
    `difflib` quando fora dele; os dois textos são não vazios. Independente
    da rota e dos demais blocos: a fronteira não muda conta nenhuma — muda o
    que a entrega pode concluir.
    """
    fronteira = caso.get("fronteira_de_escopo")
    if fronteira is None:
        return

    if not isinstance(fronteira, dict):
        raise CasoInvalido(
            f"campo 'fronteira_de_escopo' não é um objeto: {fronteira!r}. "
            "Declare 'classe', 'arquitetura_dominante' e 'razao'."
        )
    _recusar_chave_desconhecida(
        fronteira, _CHAVES_FRONTEIRA_DE_ESCOPO_PERMITIDAS, "'fronteira_de_escopo'")

    classe = fronteira.get("classe")
    _exigir_texto(classe, "fronteira_de_escopo.classe")
    if classe not in CLASSES_DE_FRONTEIRA_DE_ESCOPO:
        sugestao = difflib.get_close_matches(classe, CLASSES_DE_FRONTEIRA_DE_ESCOPO, n=1)
        dica = f" Você quis dizer '{sugestao[0]}'? " if sugestao else " "
        raise CasoInvalido(
            f"'fronteira_de_escopo.classe' fora do vocabulário: '{classe}'.{dica}"
            "A fronteira nomeia uma das classes que a metodologia declara "
            "fora do seu escopo como métrica-manchete (§14 do desenho) — uma "
            "classe desconhecida seria uma fronteira que nem o catálogo nem "
            "o relatório sabem nomear. Classes aceitas: "
            f"{', '.join(sorted(CLASSES_DE_FRONTEIRA_DE_ESCOPO))}."
        )

    for campo, razao in _RAZOES_TEXTOS_DA_FRONTEIRA.items():
        valor = fronteira.get(campo)
        if not isinstance(valor, str) or not valor.strip():
            raise CasoInvalido(
                f"'fronteira_de_escopo.{campo}' ausente ou vazio: {valor!r}. "
                f"Tem de ser texto não vazio: {razao}"
            )


# --------------------------------------------------------------------------
# Fatia 5F, Task 2 (D5/D7 do plano docs/superpowers/plans/2026-09-15-v4-item5f-
# valuation.md): dois campos opcionais de topo que o relatório exibe e que nenhuma
# conta do motor consome.
#
# 'metrica_forward' é a métrica forward (consenso, guidance) com proveniência,
# denominador do múltiplo de tela forward: fato de mercado declarado, nunca uma
# escolha do wrapper. Mesmo `tipo` da métrica-base — o múltiplo justo forward que o
# motor já publica é o da mesma métrica —, valor finito e positivo, período e fonte.
# Recusada na rota rampa e junto de degrau: EV/EBITDA do ano 0 e P/VP com degrau não
# têm forward para parear com a tela.
#
# 'escala_monetaria' é a escala dos montantes do caso, convenção do caso como a moeda
# (§16.2 do desenho): o relatório a aplica às unidades que o catálogo marca. Opcional:
# sem ela, nada muda.
# --------------------------------------------------------------------------

ESCALAS_MONETARIAS: frozenset = frozenset({"milhares", "milhoes", "bilhoes"})

_CHAVES_METRICA_FORWARD_PERMITIDAS: frozenset = frozenset({"tipo", "valor", "periodo", "fonte"})


def _validar_metrica_forward(caso: Caso, rota: str) -> None:
    """Valida o bloco opcional 'metrica_forward': rota, degrau, chaves, tipo, valor,
    período e fonte. Ausente ou `None` é um caso sem tela forward. A presença é
    recusada antes da forma na rota rampa e junto de 'degrau': nenhum bloco, por mais
    bem formado, tem par justo forward ali."""
    metrica_forward = caso.get("metrica_forward")
    if metrica_forward is None:
        return

    if not isinstance(metrica_forward, dict):
        raise CasoInvalido(
            f"campo 'metrica_forward' não é um objeto: {metrica_forward!r}. Declare 'tipo', "
            "'valor', 'periodo' e 'fonte'."
        )
    if rota == "rampa":
        raise CasoInvalido(
            "campo 'metrica_forward' presente na rota 'rampa': o múltiplo da rota é EV/EBITDA do "
            "ano 0, que não tem forward — não existe múltiplo justo forward para parear com a tela. "
            "Remova o campo."
        )
    if caso.get("degrau") is not None:
        raise CasoInvalido(
            "campo 'metrica_forward' presente junto de 'degrau': o múltiplo da manchete é o P/VP "
            "justo com degrau, que não tem forward — não existe múltiplo justo forward para parear "
            "com a tela. Remova 'metrica_forward', ou remova 'degrau'."
        )
    _recusar_chave_desconhecida(metrica_forward, _CHAVES_METRICA_FORWARD_PERMITIDAS, "'metrica_forward'")

    tipo = metrica_forward.get("tipo")
    tipo_da_base = caso["metrica_base"]["tipo"]
    if tipo != tipo_da_base:
        raise CasoInvalido(
            f"'metrica_forward.tipo' diferente de 'metrica_base.tipo': {tipo!r} contra "
            f"{tipo_da_base!r}. O múltiplo de tela forward pareia com o múltiplo justo forward da "
            "mesma métrica — em outra, os dois múltiplos comparariam bases diferentes."
        )

    valor = metrica_forward.get("valor")
    if not _numero_valido(valor) or not _finito(valor) or valor <= 0:
        raise CasoInvalido(
            f"'metrica_forward.valor' inválido: {valor!r}. A métrica forward é o denominador do "
            "múltiplo de tela forward — precisa ser um número finito e positivo."
        )

    for campo in ("periodo", "fonte"):
        item = metrica_forward.get(campo)
        if not isinstance(item, str) or not item.strip():
            raise CasoInvalido(
                f"campo 'metrica_forward.{campo}' ausente ou vazio: {item!r}. A métrica forward é "
                "fato de mercado (consenso, guidance): sem período e fonte, o múltiplo de tela "
                "forward não é auditável."
            )


def _validar_escala_monetaria(caso: Caso) -> None:
    """Valida o campo opcional 'escala_monetaria': ausente ou `None` é um caso sem
    escala declarada; presente, um código de `ESCALAS_MONETARIAS`, recusado pelo nome
    com sugestão quando fora dele."""
    escala = caso.get("escala_monetaria")
    if escala is None:
        return
    _exigir_texto(escala, "escala_monetaria")
    if escala not in ESCALAS_MONETARIAS:
        sugestao = difflib.get_close_matches(escala, ESCALAS_MONETARIAS, n=1)
        dica = f" Você quis dizer '{sugestao[0]}'? " if sugestao else " "
        raise CasoInvalido(
            f"'escala_monetaria' fora do vocabulário: '{escala}'.{dica}"
            "É a escala em que os montantes do caso estão declarados — uma escala desconhecida "
            "sairia na tela sem rótulo. Escalas aceitas: "
            f"{', '.join(sorted(ESCALAS_MONETARIAS))}."
        )


# --------------------------------------------------------------------------
# Fatia 5F, Task 3 (D6 do plano docs/superpowers/plans/2026-09-15-v4-item5f-
# valuation.md): bloco opcional 'conservacao_de_capital', a verificação da §11.1b
# da metodologia — o capital que a companhia consome (capex total mais ΔWC) contra
# os encargos de reposição e de crescimento do vetor. O motor só a confronta no
# subcomando `ev`, sobre o EBITDA declarado: fora da rota firm com métrica EBITDA o
# bloco é recusado — a rampa garante a identidade por construção (reinvestimento
# por componente) e o degrau só existe na rota equity. O limiar (10%) é do motor;
# este módulo só valida a forma.
# --------------------------------------------------------------------------

ANOS_BASE_DO_CAPEX: frozenset = frozenset({"corrente", "guidance_longo_prazo"})

_CHAVES_CONSERVACAO_PERMITIDAS: frozenset = frozenset({"capex_total", "dwc"})
_CHAVES_CAPEX_TOTAL_PERMITIDAS: frozenset = frozenset({"valor", "fonte", "ano_base"})
_CHAVES_DWC_PERMITIDAS: frozenset = frozenset({"valor", "fonte"})


def _validar_conservacao_de_capital(caso: Caso, rota: str) -> None:
    """Valida o bloco opcional 'conservacao_de_capital': rota e métrica, chaves em
    todo nível, fontes, valores e o ano-base do capex. Ausente ou `None` é um caso
    sem a verificação."""
    conservacao = caso.get("conservacao_de_capital")
    if conservacao is None:
        return

    if not isinstance(conservacao, dict):
        raise CasoInvalido(
            f"campo 'conservacao_de_capital' não é um objeto: {conservacao!r}. Declare 'capex_total' "
            "({valor, fonte, ano_base}) e 'dwc' ({valor, fonte})."
        )
    tipo_da_metrica = caso["metrica_base"]["tipo"]
    if rota != "firm" or tipo_da_metrica != "EBITDA":
        raise CasoInvalido(
            f"bloco 'conservacao_de_capital' na rota '{rota}' com métrica '{tipo_da_metrica}': a "
            "conservação de capital só é confrontada na rota firm com métrica EBITDA — o motor a "
            "executa sobre o EBITDA declarado, e na rota rampa a identidade vale por construção "
            "(reinvestimento por componente). Remova o bloco, ou avalie pela rota firm com EBITDA."
        )
    _recusar_chave_desconhecida(conservacao, _CHAVES_CONSERVACAO_PERMITIDAS, "'conservacao_de_capital'")

    for grupo, permitidas in (("capex_total", _CHAVES_CAPEX_TOTAL_PERMITIDAS),
                              ("dwc", _CHAVES_DWC_PERMITIDAS)):
        item = conservacao.get(grupo)
        if not isinstance(item, dict):
            raise CasoInvalido(
                f"'conservacao_de_capital.{grupo}' ausente ou não é um objeto: {item!r}. Declare "
                f"{', '.join(sorted(permitidas))}."
            )
        _recusar_chave_desconhecida(item, permitidas, f"'conservacao_de_capital.{grupo}'")
        fonte = item.get("fonte")
        if not isinstance(fonte, str) or not fonte.strip():
            raise CasoInvalido(
                f"campo 'conservacao_de_capital.{grupo}.fonte' ausente ou vazio: {fonte!r}. Um número "
                "que confronta o vetor sem fonte não é auditável."
            )

    capex = conservacao["capex_total"].get("valor")
    if not _numero_valido(capex) or not _finito(capex) or capex <= 0:
        raise CasoInvalido(
            f"'conservacao_de_capital.capex_total.valor' inválido: {capex!r}. O capex total do "
            "ano-base precisa ser um número finito e positivo — é o capital que a operação consome."
        )
    dwc = conservacao["dwc"].get("valor")
    if not _numero_valido(dwc) or not _finito(dwc):
        raise CasoInvalido(
            f"'conservacao_de_capital.dwc.valor' inválido: {dwc!r}. A variação do capital de giro "
            "precisa ser um número finito (negativa quando o giro libera caixa)."
        )

    ano_base = conservacao["capex_total"].get("ano_base")
    _exigir_texto(ano_base, "conservacao_de_capital.capex_total.ano_base")
    if ano_base not in ANOS_BASE_DO_CAPEX:
        sugestao = difflib.get_close_matches(ano_base, ANOS_BASE_DO_CAPEX, n=1)
        dica = f" Você quis dizer '{sugestao[0]}'? " if sugestao else " "
        raise CasoInvalido(
            f"'conservacao_de_capital.capex_total.ano_base' fora do vocabulário: '{ano_base}'.{dica}"
            "O capex do ano-base é o corrente ou o do guidance de longo prazo — declare qual. "
            f"Anos-base aceitos: {', '.join(sorted(ANOS_BASE_DO_CAPEX))}."
        )


# --------------------------------------------------------------------------
# Fatia 5G, Task 1 (D1 do plano docs/superpowers/plans/2026-09-15-v4-item5g-
# alternativas.md): bloco opcional 'escolhas_metodologicas' — a sensibilidade às
# escolhas metodológicas da §5b do vendor, item 4.
#
# As escolhas são DECLARADAS pelo analista; o wrapper só precifica. O caso diz, de
# cada escolha, a chave (o vocabulário abaixo, as dez do vendor), a posição que o
# caso-base ocupa nela, as sobreposições que levam o cenário da manchete ao outro
# ramo e, quando existir, o observável que disparou o gatilho da escolha. Nenhum
# gatilho é AVALIADO aqui: reconhecer que os minoritários passaram de ~20% do PL, ou
# que o capex corrente diverge do de estado estacionário, é trabalho do analista —
# o gate só confere que o que foi declarado é declarável.
#
# Duas escolhas do vocabulário não são precificáveis nesta fatia, e a recusa é
# nomeada em vez de silenciosa:
#   - 'leitura_de_capacidade' trocaria a ROTA inteira (o ramo capacidade usa RiR por
#     componente e as fases da capacidade pré-construída, não uma sobreposição sobre
#     o vetor) — fica fora da v4, como dívida do plano;
#   - 'alavanca_de_lucro' só existe com degrau: sem o degrau declarado no caso, não
#     há alavanca a modelar nem a excluir, e a escolha seria uma declaração vazia.
# --------------------------------------------------------------------------

# As DEZ do vendor (`vendor/multiplos-justos/references/aplicacao.md` §5b, item 4).
# A base monetária NÃO entra: é invariante de coerência reportado à parte, nunca uma
# décima primeira escolha econômica. O catálogo de apresentação rotula exatamente
# estas dez e descreve o gatilho de cada uma (trava em
# tests/test_catalogo_apresentacao.py) — o relatório nunca aprende o vocabulário.
ESCOLHAS_METODOLOGICAS: frozenset = frozenset({
    "base_do_lucro",
    "alavanca_de_lucro",
    "rentabilidade",
    "crescimento",
    "hipotese_terminal",
    "regime_do_driver_no_terminal",
    "caixa_excedente_em_hibrida_financeira",
    "ano_de_capex_no_par_d_rir",
    "fronteira_de_consolidacao",
    "leitura_de_capacidade",
})

# Onde o CASO-BASE está em cada escolha: no ramo central da metodologia, ou no
# alternativo. É a declaração que a coerência interna dos cenários confronta — o
# caso-base fora da central em várias escolhas, todas na mesma direção, não é
# prudência, é cenário incoerente (o alerta sai em `avaliar`, nunca aqui).
POSICOES_DA_ESCOLHA: frozenset = frozenset({"central", "alternativa"})

# A escolha que trocaria a rota inteira, fora da v4; e a que só existe com degrau.
ESCOLHA_FORA_DA_V4: str = "leitura_de_capacidade"
ESCOLHA_QUE_EXIGE_DEGRAU: str = "alavanca_de_lucro"

_CHAVES_DA_ESCOLHA_PERMITIDAS: frozenset = frozenset({
    "chave", "no_caso_base", "sobreposicoes", "gatilho_disparou",
})
_CHAVES_DO_GATILHO_PERMITIDAS: frozenset = frozenset({"observavel"})

# Fatia 5G, Task 1b: os alvos que uma sobreposição alcança, além da premissa numérica
# da rota. As dez escolhas não movem só premissa — a base do lucro move a MÉTRICA, o
# caixa em híbrida financeira e a fronteira de consolidação movem LINHAS DA PONTE, e a
# hipótese terminal troca a CONVENÇÃO. A sobreposição é uma sobreposição parcial do
# próprio caso, e por isso usa a estrutura dele: os dois alvos fora do vetor de
# premissas entram como objetos, com os mesmos nomes que o caso lhes dá.
#
# Por que não um caminho textual ('metrica_base.valor', 'ponte.divida_bruta'), que
# seria a forma óbvia: `_validar_chaves_enderecaveis` (revisão da 5E, F1) recusa
# QUALQUER chave do caso que contenha '.', porque o caminho de um número do caso
# separa segmentos por '.' no mapa de insumos, no `usado_em` do ledger e nos
# placeholders. Uma chave com ponto tornaria o número sob ela inendereçável — e as
# sobreposições são folhas do caso como qualquer outra.
ALVOS_NAO_PREMISSA_DA_SOBREPOSICAO: frozenset = frozenset({"metrica_base", "ponte"})

# A única premissa NÃO numérica que uma sobreposição alcança: a convenção terminal, a
# única cujo vocabulário este gate de fato conhece (`TV_CANON`). 'politica_tv' e
# 'mid_year' ficam de fora — o gate as trata como string opaca e bool (ver
# `_PREMISSAS_NAO_NUMERICAS` e o comentário de `POLITICA_TV_OPCOES`), e uma
# sobreposição sobre elas passaria sem nenhuma checagem de valor.
PREMISSAS_NAO_NUMERICAS_DA_SOBREPOSICAO: frozenset = frozenset({"tv"})

_CHAVES_DA_METRICA_NA_SOBREPOSICAO: frozenset = frozenset({"valor"})


def _valor_numerico_da_sobreposicao(prefixo: str, alvo: str, valor: Any) -> None:
    """Todo alvo numérico de uma sobreposição — premissa, métrica-base ou linha da
    ponte — é número finito. O motor (ou a ponte) recebe o valor direto, sem
    conversão: texto, bool, NaN ou Infinity envenenam o preço da alternativa em
    silêncio."""
    if not _numero_valido(valor) or not _finito(valor):
        raise CasoInvalido(
            f"'{prefixo}.sobreposicoes.{alvo}' não é um número finito: {valor!r}. O motor "
            "recebe esse valor direto, sem conversão — texto, bool, NaN ou Infinity envenenam "
            "o preço da alternativa em silêncio."
        )


def _validar_sobreposicoes(prefixo: str, sobreposicoes: Any, rota: str) -> None:
    """Valida o mapa de sobreposições de UMA escolha: forma, alvos e valores.

    Os alvos são os que as dez escolhas de fato movem, e nada além deles: cada
    premissa da rota (numérica, ou a convenção terminal, em
    `PREMISSAS_NAO_NUMERICAS_DA_SOBREPOSICAO`), `metrica_base` (só `valor`) e `ponte`
    (as linhas de `CAMPOS_DA_PONTE`, e só nas rotas que declaram o bloco). É uma
    sobreposição PARCIAL do caso, com a estrutura do caso — ver o comentário de
    `ALVOS_NAO_PREMISSA_DA_SOBREPOSICAO` sobre por que não é um caminho textual.
    """
    if not isinstance(sobreposicoes, dict):
        raise CasoInvalido(
            f"'{prefixo}.sobreposicoes' não é um objeto: {sobreposicoes!r}. É o mapa de alvos "
            "do caso -> valor que leva o cenário da manchete ao outro ramo da escolha."
        )
    if not sobreposicoes:
        raise CasoInvalido(
            f"'{prefixo}.sobreposicoes' vazia: a alternativa sairia idêntica ao cenário da "
            "manchete, com impacto zero. Uma escolha sem nada que a mova não é uma escolha "
            "— declare o alvo que muda de ramo, ou remova a entrada."
        )

    premissas_da_rota = _PREMISSAS_POR_ROTA[rota]
    aceitos = set(premissas_da_rota) | ALVOS_NAO_PREMISSA_DA_SOBREPOSICAO
    for alvo in sorted(sobreposicoes):
        _exigir_texto(alvo, f"{prefixo}.sobreposicoes")
        valor = sobreposicoes[alvo]

        if alvo not in aceitos:
            sugestao = difflib.get_close_matches(alvo, aceitos, n=1)
            dica = f" Você quis dizer '{sugestao[0]}'? " if sugestao else " "
            raise CasoInvalido(
                f"'{prefixo}.sobreposicoes' cita '{alvo}', que não é alvo da rota "
                f"'{rota}'.{dica}A alternativa é precificada pelo mesmo motor, sobre uma cópia "
                "do caso com as sobreposições aplicadas: um alvo que o caso não tem seria "
                f"ignorado em silêncio. Alvos aceitos: {', '.join(sorted(aceitos))}."
            )

        if alvo == "metrica_base":
            if not isinstance(valor, dict):
                raise CasoInvalido(
                    f"'{prefixo}.sobreposicoes.metrica_base' não é um objeto: {valor!r}. "
                    "Declare 'valor' — a base do lucro sobre a qual a alternativa é construída."
                )
            _recusar_chave_desconhecida(
                valor, _CHAVES_DA_METRICA_NA_SOBREPOSICAO, f"'{prefixo}.sobreposicoes.metrica_base'")
            if "valor" not in valor:
                raise CasoInvalido(
                    f"'{prefixo}.sobreposicoes.metrica_base' sem 'valor': o tipo da métrica é a "
                    "rota do caso e não muda por escolha metodológica — o que muda de ramo é a "
                    "base, o número."
                )
            _valor_numerico_da_sobreposicao(prefixo, "metrica_base.valor", valor["valor"])
            continue

        if alvo == "ponte":
            if rota not in _ROTAS_COM_PONTE:
                raise CasoInvalido(
                    f"'{prefixo}.sobreposicoes' cita 'ponte' na rota '{rota}', que não declara "
                    "ponte de dívida: a rota chega em Equity direto, e não há linha de balanço "
                    "a sobrepor."
                )
            if not isinstance(valor, dict) or not valor:
                raise CasoInvalido(
                    f"'{prefixo}.sobreposicoes.ponte' não é um objeto com ao menos uma linha: "
                    f"{valor!r}. Declare a linha de balanço que muda de ramo "
                    f"({', '.join(CAMPOS_DA_PONTE)})."
                )
            _recusar_chave_desconhecida(
                valor, frozenset(CAMPOS_DA_PONTE), f"'{prefixo}.sobreposicoes.ponte'")
            for linha in sorted(valor):
                _valor_numerico_da_sobreposicao(prefixo, f"ponte.{linha}", valor[linha])
            continue

        if alvo in PREMISSAS_NAO_NUMERICAS_DA_SOBREPOSICAO:
            _exigir_texto(valor, f"{prefixo}.sobreposicoes.{alvo}")
            if valor not in TV_CANON:
                sugestao = difflib.get_close_matches(valor, TV_CANON, n=1)
                dica = f" Você quis dizer '{sugestao[0]}'? " if sugestao else " "
                raise CasoInvalido(
                    f"'{prefixo}.sobreposicoes.{alvo}' fora do vocabulário: '{valor}'.{dica}"
                    "A hipótese terminal alternativa é uma convenção que o motor reconhece — "
                    f"uma fora do vocabulário seria repassada crua e recusada lá. Convenções "
                    f"aceitas: {', '.join(sorted(TV_CANON))}."
                )
            continue

        if alvo in _PREMISSAS_NAO_NUMERICAS:
            raise CasoInvalido(
                f"'{prefixo}.sobreposicoes' cita '{alvo}', premissa não numérica que a "
                "sobreposição não alcança: o gate a trata como valor opaco, e uma sobreposição "
                "sobre ela passaria sem checagem nenhuma. A única convenção que uma escolha "
                f"troca é {', '.join(sorted(PREMISSAS_NAO_NUMERICAS_DA_SOBREPOSICAO))}."
            )
        _valor_numerico_da_sobreposicao(prefixo, alvo, valor)


def _validar_escolha(prefixo: str, escolha: Any, rota: str, vistas: set) -> None:
    """Valida UMA entrada de 'escolhas_metodologicas': forma, chave, posição,
    sobreposições e gatilho. `vistas` acumula as chaves já declaradas, para a recusa
    de chave repetida."""
    if not isinstance(escolha, dict):
        raise CasoInvalido(
            f"{prefixo} não é um objeto: {escolha!r}. Cada escolha declara 'chave', "
            "'no_caso_base' e 'sobreposicoes' (e 'gatilho_disparou', quando o gatilho "
            "da escolha disparou)."
        )
    _recusar_chave_desconhecida(escolha, _CHAVES_DA_ESCOLHA_PERMITIDAS, f"'{prefixo}'")

    chave = escolha.get("chave")
    _exigir_texto(chave, f"{prefixo}.chave")
    if chave not in ESCOLHAS_METODOLOGICAS:
        sugestao = difflib.get_close_matches(chave, ESCOLHAS_METODOLOGICAS, n=1)
        dica = f" Você quis dizer '{sugestao[0]}'? " if sugestao else " "
        raise CasoInvalido(
            f"'{prefixo}.chave' fora do vocabulário: '{chave}'.{dica}"
            "A sensibilidade às escolhas metodológicas cobre um conjunto fechado, que o "
            "catálogo rotula e cujo gatilho ele descreve — uma chave desconhecida sairia "
            "no painel sem rótulo e sem gatilho. Escolhas aceitas: "
            f"{', '.join(sorted(ESCOLHAS_METODOLOGICAS))}."
        )
    if chave in vistas:
        raise CasoInvalido(
            f"'{prefixo}.chave' repetida: '{chave}'. Cada escolha aparece uma vez — duas "
            "entradas da mesma escolha publicariam dois preços alternativos para o mesmo "
            "ramo, e o alerta de coerência interna dos cenários a contaria duas vezes."
        )
    vistas.add(chave)

    if chave == ESCOLHA_FORA_DA_V4:
        raise CasoInvalido(
            f"'{prefixo}.chave' é '{chave}', que esta versão não precifica: o ramo de "
            "capacidade troca a arquitetura inteira do vetor (reinvestimento por "
            "componente, fases da capacidade pré-construída, depreciação do estado "
            "estacionário), não uma sobreposição sobre o cenário da manchete. Declare-a "
            "em prosa na análise, fora do painel."
        )
    no_caso_base = escolha.get("no_caso_base")
    _exigir_texto(no_caso_base, f"{prefixo}.no_caso_base")
    if no_caso_base not in POSICOES_DA_ESCOLHA:
        sugestao = difflib.get_close_matches(no_caso_base, POSICOES_DA_ESCOLHA, n=1)
        dica = f" Você quis dizer '{sugestao[0]}'? " if sugestao else " "
        raise CasoInvalido(
            f"'{prefixo}.no_caso_base' fora do vocabulário: '{no_caso_base}'.{dica}"
            "O caso-base ocupa o ramo central da escolha ou o alternativo — sem essa "
            "declaração não há como saber de que lado o caso-base está, e o alerta de "
            f"coerência interna dos cenários fica cego. Posições aceitas: "
            f"{', '.join(sorted(POSICOES_DA_ESCOLHA))}."
        )

    _validar_sobreposicoes(prefixo, escolha.get("sobreposicoes"), rota)

    gatilho = escolha.get("gatilho_disparou")
    if gatilho is None:
        return
    if not isinstance(gatilho, dict):
        raise CasoInvalido(
            f"'{prefixo}.gatilho_disparou' não é um objeto: {gatilho!r}. Declare "
            "'observavel' — o que, no caso, fez o gatilho da escolha disparar."
        )
    _recusar_chave_desconhecida(
        gatilho, _CHAVES_DO_GATILHO_PERMITIDAS, f"'{prefixo}.gatilho_disparou'")
    observavel = gatilho.get("observavel")
    if not isinstance(observavel, str) or not observavel.strip():
        raise CasoInvalido(
            f"'{prefixo}.gatilho_disparou.observavel' ausente ou vazio: {observavel!r}. Um "
            "gatilho declarado como disparado sem o observável que o disparou é afirmação "
            "que ninguém pode conferir — a escolha sobe ao nível principal do painel por "
            "causa dele."
        )


def _validar_escolhas_metodologicas(caso: Caso, rota: str) -> None:
    """Valida o bloco opcional 'escolhas_metodologicas'. Ausente ou `None` é um caso
    sem painel de escolhas.

    Recusado inteiro junto de 'sotp': com soma de partes, a manchete é a composição
    das partes, cada uma com vetor próprio — reprecificar o vetor do cenário da
    manchete produziria um preço que não é o da manchete, e o impacto compararia
    bases que não se correspondem. Mesma disciplina das demais leituras desta fatia.
    """
    escolhas = caso.get("escolhas_metodologicas")
    if escolhas is None:
        return

    if caso.get("sotp") is not None:
        raise CasoInvalido(
            "bloco 'escolhas_metodologicas' presente junto de 'sotp': com soma de partes o "
            "preço da manchete vem da composição das partes, cada uma com o próprio vetor — "
            "a alternativa, precificada sobre o vetor de um cenário, não produziria o preço "
            "da manchete, e o impacto compararia bases diferentes. Remova um dos dois."
        )
    _exigir_lista(escolhas, "escolhas_metodologicas")
    if not escolhas:
        raise CasoInvalido(
            "bloco 'escolhas_metodologicas' vazio: declare ao menos uma escolha, ou remova o "
            "bloco — uma lista vazia e a ausência do bloco dizem a mesma coisa por dois "
            "caminhos."
        )

    vistas: set = set()
    for indice, escolha in enumerate(escolhas):
        _validar_escolha(f"escolhas_metodologicas.{indice}", escolha, rota, vistas)

    if ESCOLHA_QUE_EXIGE_DEGRAU in vistas and caso.get("degrau") is None:
        raise CasoInvalido(
            f"escolha '{ESCOLHA_QUE_EXIGE_DEGRAU}' declarada num caso sem 'degrau': a "
            "alavanca de lucro é a escolha entre modelar o degrau de nível com "
            "probabilidade e tratá-lo como opcionalidade fora do preço — sem o degrau "
            "declarado no caso não há alavanca nenhuma a modelar. Declare 'degrau', ou "
            "remova a escolha."
        )


# --------------------------------------------------------------------------
# Fatia 5G, Task 2 (D2/D3/D4 do plano docs/superpowers/plans/2026-09-15-v4-item5g-
# alternativas.md): três leituras opcionais que a §9 pede depois das sensibilidades.
#
# 'retorno_exigido' (D2) é a pergunta "que valor resulta ao exigir retorno de X%":
# a taxa substitui o custo de capital do cenário da manchete, uma rota por vez.
# Recusada com 'sotp' (a manchete vem da composição das partes, cada uma com o
# próprio custo de capital) e com 'degrau' (o preço da manchete é o do P/VP com
# degrau, e a substituição atravessaria duas composições ao mesmo tempo).
#
# 'pesos_de_probabilidade' (D3) são julgamento do analista, FORA da fórmula: o
# wrapper compõe a soma de peso x preço, e a entrega diz que o número nunca
# substitui bear, base e bull. Exigem dois cenários ou mais e soma exata de 100;
# recusados com 'sotp', que tem um preço só.
#
# 'cross_check' (D4) é o segundo método declarado: o vetor coerente da ROTA OPOSTA,
# precificado pelo mesmo motor. A rota do caso é recusada (não seria segundo
# método); uma rota que atravessa a ponte da dívida exige que o caso declare
# 'ponte', senão não há inputs coerentes para chegar a preço por ação — e a
# metodologia manda declarar a ausência, nunca calcular em silêncio.
# --------------------------------------------------------------------------

# Qual premissa o retorno exigido substitui em cada rota. As rotas firm e rampa
# descontam ao WACC; a equity, ao Ke — a mesma dicotomia que `reversa.py` já aplica
# ao eixo de custo de capital.
PREMISSA_DE_CUSTO_DE_CAPITAL_POR_ROTA: dict[str, str] = {
    "firm": "wacc", "equity": "ke", "rampa": "wacc",
}

# Soma exata dos pesos, em pontos percentuais. Não é tolerância de arredondamento:
# um conjunto de pesos que não fecha em 100 não é uma distribuição.
SOMA_DOS_PESOS: float = 100.0

_CHAVES_RETORNO_EXIGIDO_PERMITIDAS: frozenset = frozenset({"taxa"})
_CHAVES_CROSS_CHECK_PERMITIDAS: frozenset = frozenset({"rota", "metrica_base", "ancora", "premissas"})
_CHAVES_METRICA_DO_CROSS_CHECK_PERMITIDAS: frozenset = frozenset({"tipo", "valor"})

# As rotas que atravessam a ponte da dívida para chegar a preço por ação — as mesmas
# que `_validar_ponte` exige que declarem o bloco.
_ROTAS_COM_PONTE: tuple = ("firm", "rampa")


def _recusar_junto_de(caso: Caso, bloco: str, outro: str, razao: str) -> None:
    """Recusa `bloco` quando o caso declara `outro`, nomeando a razão econômica."""
    if caso.get(outro) is not None:
        raise CasoInvalido(
            f"bloco '{bloco}' presente junto de '{outro}': {razao} Remova um dos dois."
        )


def _validar_retorno_exigido(caso: Caso, rota: str) -> None:
    """Valida o bloco opcional 'retorno_exigido': combinações, chaves e a taxa.
    Ausente ou `None` é um caso sem a leitura."""
    retorno = caso.get("retorno_exigido")
    if retorno is None:
        return

    if not isinstance(retorno, dict):
        raise CasoInvalido(
            f"campo 'retorno_exigido' não é um objeto: {retorno!r}. Declare 'taxa', o retorno "
            "exigido em pontos percentuais."
        )
    _recusar_junto_de(
        caso, "retorno_exigido", "sotp",
        "com soma de partes o preço da manchete vem da composição das partes, cada uma com o "
        "próprio custo de capital — substituir um custo só não produziria o preço da manchete "
        "sob o retorno exigido.")
    _recusar_junto_de(
        caso, "retorno_exigido", "degrau",
        "o preço da manchete é o do P/VP justo com degrau, composto pelo motor a partir da "
        "transição — substituir o custo de capital atravessaria as duas composições ao mesmo "
        "tempo, e o preço resultante não seria comparável ao da manchete.")
    _recusar_chave_desconhecida(retorno, _CHAVES_RETORNO_EXIGIDO_PERMITIDAS, "'retorno_exigido'")

    taxa = retorno.get("taxa")
    if not _numero_valido(taxa) or not _finito(taxa) or not 0 < taxa <= 100:
        raise CasoInvalido(
            f"'retorno_exigido.taxa' inválida: {taxa!r}. É o retorno exigido em PONTOS "
            f"PERCENTUAIS (12.0 significa 12%, nunca 0.12), a mesma convenção de "
            f"'{PREMISSA_DE_CUSTO_DE_CAPITAL_POR_ROTA[rota]}' — precisa ser um número finito "
            "acima de zero e até 100: retorno exigido nulo ou negativo não desconta nada."
        )


def _validar_pesos_de_probabilidade(caso: Caso, cenarios: dict) -> None:
    """Valida o campo opcional 'pesos_de_probabilidade': combinação, nomes de cenário,
    quantidade e soma. Ausente ou `None` é um caso sem valor ponderado."""
    pesos = caso.get("pesos_de_probabilidade")
    if pesos is None:
        return

    if not isinstance(pesos, dict):
        raise CasoInvalido(
            f"campo 'pesos_de_probabilidade' não é um objeto: {pesos!r}. Mapeia o nome de cada "
            "cenário ao peso dele, em pontos percentuais."
        )
    _recusar_junto_de(
        caso, "pesos_de_probabilidade", "sotp",
        "com soma de partes existe um preço só, o da composição — não há cenários a ponderar.")

    if len(pesos) < 2:
        raise CasoInvalido(
            f"'pesos_de_probabilidade' com menos de dois cenários: {sorted(pesos)!r}. Ponderar "
            "um cenário só devolve o preço dele com outro nome — o valor ponderado existe para "
            "dizer o que a distribuição de cenários implica, e uma distribuição precisa de dois "
            "pontos ou mais."
        )
    for nome in sorted(pesos):
        _validar_cenario_alvo(f"pesos_de_probabilidade.{nome}", nome, cenarios)
        peso = pesos[nome]
        if not _numero_valido(peso) or not _finito(peso) or peso < 0:
            raise CasoInvalido(
                f"'pesos_de_probabilidade.{nome}' inválido: {peso!r}. Cada peso é um número "
                "finito e não negativo, em pontos percentuais."
            )
    soma = sum(pesos.values())
    if soma != SOMA_DOS_PESOS:
        raise CasoInvalido(
            f"'pesos_de_probabilidade' soma {soma!r}, não {SOMA_DOS_PESOS}: os pesos são uma "
            "distribuição sobre os cenários declarados, em pontos percentuais. Uma soma "
            "diferente de 100 publicaria um valor ponderado que não é média de nada — o "
            "wrapper não normaliza em silêncio."
        )


def _validar_cross_check(caso: Caso, rota: str) -> None:
    """Valida o bloco opcional 'cross_check': rota oposta, ponte, chaves, métrica,
    âncora e o vetor completo da rota declarada. Ausente ou `None` é um caso sem
    cross-check calculado — a ausência é declarada em prosa, na Análise."""
    cross_check = caso.get("cross_check")
    if cross_check is None:
        return

    if not isinstance(cross_check, dict):
        raise CasoInvalido(
            f"campo 'cross_check' não é um objeto: {cross_check!r}. Declare 'rota', "
            "'metrica_base' ({tipo, valor}), 'ancora' e 'premissas' da rota oposta."
        )
    _recusar_chave_desconhecida(cross_check, _CHAVES_CROSS_CHECK_PERMITIDAS, "'cross_check'")

    rota_oposta = cross_check.get("rota")
    _exigir_texto(rota_oposta, "cross_check.rota")
    if rota_oposta not in _PREMISSAS_POR_ROTA:
        sugestao = difflib.get_close_matches(rota_oposta, _PREMISSAS_POR_ROTA, n=1)
        dica = f" Você quis dizer '{sugestao[0]}'? " if sugestao else " "
        raise CasoInvalido(
            f"'cross_check.rota' desconhecida: '{rota_oposta}'.{dica}Rotas aceitas: "
            f"{', '.join(sorted(_PREMISSAS_POR_ROTA))}."
        )
    if rota_oposta == rota:
        raise CasoInvalido(
            f"'cross_check.rota' é a rota do próprio caso ('{rota}'): o cross-check é o SEGUNDO "
            "método — a rota oposta, com o vetor coerente dela. Repetir a rota do caso não "
            "confronta nada; seria o mesmo caminho com outro vetor."
        )
    if rota_oposta in _ROTAS_COM_PONTE and "ponte" not in caso:
        raise CasoInvalido(
            f"'cross_check.rota' é '{rota_oposta}', que chega em EV e atravessa a ponte da "
            "dívida até preço por ação, mas o caso não declara 'ponte' (a rota "
            f"'{rota}' não a admite). Sem dívida líquida e linhas de balanço não existem "
            "inputs coerentes para o segundo método: declare a ausência do cross-check na "
            "Análise, em vez de calcular um preço que nenhum balanço sustenta."
        )

    metrica = cross_check.get("metrica_base")
    if not isinstance(metrica, dict):
        raise CasoInvalido(
            f"'cross_check.metrica_base' ausente ou não é um objeto: {metrica!r}. Declare "
            "'tipo' e 'valor' — a escala do segundo método é a da rota dele, não a do caso."
        )
    _recusar_chave_desconhecida(
        metrica, _CHAVES_METRICA_DO_CROSS_CHECK_PERMITIDAS, "'cross_check.metrica_base'")
    tipo = metrica.get("tipo")
    aceitas = METRICAS_POR_ROTA[rota_oposta]
    _exigir_texto(tipo, "cross_check.metrica_base.tipo")
    if tipo not in aceitas:
        raise CasoInvalido(
            f"'cross_check.metrica_base.tipo' incompatível com a rota '{rota_oposta}': "
            f"'{tipo}'. Rota '{rota_oposta}' aceita apenas {', '.join(sorted(aceitas))}."
        )
    valor = metrica.get("valor")
    if not _numero_valido(valor) or not _finito(valor):
        raise CasoInvalido(
            f"'cross_check.metrica_base.valor' ausente ou não é um número finito: {valor!r}. "
            "É a escala sobre a qual o segundo método chega a preço."
        )

    ancora = cross_check.get("ancora")
    if not isinstance(ancora, str) or not ancora.strip():
        raise CasoInvalido(
            f"'cross_check.ancora' ausente ou vazia: {ancora!r}. O vetor do segundo método tem "
            "de vir de um observável concreto, como todo cenário do caso — vetor sem âncora é "
            "vetor inventado, e um cross-check inventado confirma o que quiser."
        )

    _validar_premissas("cross_check", cross_check.get("premissas"), rota_oposta)


def carregar(caminho: Path) -> Caso:
    """Lê `caminho` como JSON utf-8, valida e devolve o dict validado.

    Não faz cache, não modifica o conteúdo, não preenche nada: devolve
    exatamente o que veio do arquivo, depois de confirmar que passa em
    `validar`.
    """
    caso = json.loads(Path(caminho).read_text(encoding="utf-8"))
    validar(caso)
    return caso
