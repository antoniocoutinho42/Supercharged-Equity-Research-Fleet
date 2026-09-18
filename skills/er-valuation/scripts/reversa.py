"""Reversa por eixo: o menu de reconciliação — "o que está no preço".

Este módulo NÃO faz conta de valuation além das duas que a metodologia
autoriza nesta fatia: (i) o alvo de múltiplo de mercado (`alvo_de_mercado`),
que é a definição de múltiplo aplicada a dados já declarados no caso (preço,
ações, métrica-base e, na rota firm, a ponte via `nd_efetivo`); (ii) o beta
implícito (`_beta_implicito`), que é a inversão declarada do CAPM sobre a
raiz que o motor devolveu para o eixo de custo de capital. Toda outra conta
— cada raiz, cada faixa de busca, cada diagnóstico, cada aviso, cada
sugestão — vem do motor congelado (subcomando `rev`), repassada íntegra.

A metodologia trata a reversa como MENU, não como um eixo só: um preço
admite mais de uma explicação univariada (o custo de capital implícito, o
crescimento implícito, a rentabilidade implícita, o CAP implícito), e
entregar um eixo só seria escolher a conclusão em vez de expor o menu. O
custo de capital implícito (`custo_capital`) é, dos quatro, o único eixo com
um observável direto de mercado para confrontar — o beta implícito contra a
banda de beta observado — e por isso `caso.py` já o torna obrigatório em
toda rodada de reversa (`EIXO_OBRIGATORIO`).

`reverter` roda um subprocesso do motor por eixo declarado em
`caso["reversa"]["eixos"]` — nunca resume os eixos, nunca uniformiza o shape
entre eles. O eixo `cap` tem um shape PRÓPRIO (`CAP_implicito_anos`, float
quando alcançável e string quando não, sem `raizes_*`, sem
`identificacao_por_raiz`, sem `sem_solucao`/`sugestao`) que os outros três
eixos não têm; este módulo repassa cada eixo exatamente como o motor
devolveu, sem normalizar para um formato comum.

Endurecimento (task 3B, RISCO 1+3): cada eixo ganha, além disso, a chave
`resolucao` (`_resolucao`) — `{"resolveu": bool, "motivo": str}` — um
marcador DESTE wrapper que anda AO LADO do payload do motor, nunca no
lugar dele. Não é uniformização do shape (o parágrafo acima continua
valendo — `cap` continua sem `raizes_*`, o eixo `%` sem raiz continua sem
`CAP_implicito_anos`): é só um ponto único onde o consumidor seguinte (o
relatório) pergunta "este eixo resolveu?" sem ter que aprender os quatro
shapes para responder essa pergunta sozinho. Nenhuma chave do motor é
removida, renomeada ou reformatada por causa dela.

Quando `rentabilidade` ou `crescimento` (os dois eixos PRIMÁRIOS da
metodologia) voltam sem raiz, `reverter` roda automaticamente um segundo
tipo de chamada ao motor — não mais `rev` (busca de raiz), mas o subcomando
de avaliação direta (`ev`/`pe`, o mesmo que a fatia A usa) sobre o vetor do
cenário com três premissas sobrepostas: `tv="gordon"`, `roic_tv`/`roe_tv`
levado a uma constante declarada (`RENTABILIDADE_TERMINAL_INFINITA`) e `gp`
igualado ao `g` do cenário — o caso-limite RiR_TV → 0, forma fechada do
teto do crescimento gratuito (`teto_do_crescimento_gratuito`; chave
`teto_do_crescimento_gratuito` no resultado de `reverter`, presente só
quando o gatilho dispara).

Fatia 5F, Task 1 (D2/D3 do plano `docs/superpowers/plans/2026-09-15-v4-item5f-
valuation.md`): cada eixo ganha também a chave `leitura` (`leitura_do_eixo`), AO
LADO do payload do motor e de `resolucao`, com a mesma disciplina — nenhuma chave do
motor é removida, renomeada ou reformatada. É a forma normalizada que o relatório lê
para mostrar "o que está no preço" sem aprender as quatro saídas do `rev`: códigos
(`MOTIVOS_DA_LEITURA`, `IDENTIFICACOES`, `POSICOES_NA_BANDA`) que o catálogo rotula,
números com a unidade declarada (uma chave de `catalogo.unidades`) e raiz e
identificação pareadas pela ordem em que o motor as devolve. O teto ganha `chave` (o
múltiplo que publica), e o gatilho dele é também o da limitação `iso_nao_calculada`
(`LIMITACOES_DA_LEITURA`): a curva iso-valor, que o motor manda rodar junto do teto,
não é calculada pelo Fleet — e isso sai publicado em `resultados.limitacoes`, nunca
omitido.

Fatia 5H, Task 1 (D2 do plano `docs/superpowers/plans/2026-09-15-v4-item5h-leitura-de-
preco.md`): ao lado do menu de eixos — que lê o preço em TAXA —, `reverter` publica
também `nivel_implicito`, que o lê em NÍVEL: que métrica-base o preço embute, dadas as
taxas do cenário, e como esse nível se confronta com o consenso de t+1/t+2 que o caso
declara (`reversa.consenso`, o confronto temporal do vendor, `references/aplicacao.md`
§4). A conta é do motor (subcomando `nivel`); este módulo monta a chamada com números
que já existem e classifica o prefixo da prosa em `leitura_chave`
(`LEITURAS_DO_NIVEL`), o mesmo padrão do degrau: chave classificada na integração,
prosa do motor nunca exibida.

Migração v10.1, Task 2 (Q2 do grill de 17/09): na rota firm com métrica EBITDA, o
`nivel` recebe também o vetor do cenário e a D&A em moeda, e publica a leitura
RECALCULADA (`nivel_implicito.recalculado`), a central da escada — ver `nivel_implicito`.
"""

from typing import Any, Callable

import diagnosticos
from caso import EIXOS_DE_REVERSA
from motor import MotorFalhou, _campo_do_multiplo, _exigir_valor, rodar

Caso = dict[str, Any]

# Eixo declarado no caso -> variável passada a `--resolver`, por rota. As
# chaves têm de ser exatamente `caso.EIXOS_DE_REVERSA` — a guarda de
# consistência logo abaixo (mesmo padrão de `ponte.py` contra
# `caso.CAMPOS_DA_PONTE`: um dict de tradução e um vocabulário de validação
# descrevendo o mesmo conjunto, checados juntos no import) trava isso na
# hora de importar, não só documenta a intenção.
RESOLVER_POR_EIXO: dict[str, dict[str, str]] = {
    "custo_capital": {"firm": "wacc", "equity": "ke"},
    "rentabilidade": {"firm": "roic", "equity": "roe"},
    "crescimento": {"firm": "g", "equity": "g"},
    "cap": {"firm": "cap", "equity": "cap"},
}

if set(RESOLVER_POR_EIXO) != EIXOS_DE_REVERSA:
    raise ImportError(
        "RESOLVER_POR_EIXO (reversa.py) e EIXOS_DE_REVERSA (caso.py) "
        "divergiram — o vocabulário de eixos validado na entrada e o "
        "vocabulário traduzido para --resolver tem de ser o mesmo"
    )

# Único eixo em que o beta implícito é calculado: é o único cuja variável
# resolvida é um custo de capital (wacc no lado firm, ke no lado equity) —
# a perna que o CAPM inverte. Os outros três eixos resolvem crescimento,
# rentabilidade ou anos; nenhum dos três tem beta.
EIXO_DO_CUSTO_DE_CAPITAL = "custo_capital"

# 'corrente' sempre explícito, nunca implícito: a métrica-base do caso é o
# múltiplo CORRENTE (TTM). Se a tela do analista estivesse em NTM/forward
# sem ninguém declarar isso, o motor confrontaria um alvo NTM contra a base
# corrente e devolveria o vetor implícito deslocado em (1+g) — um erro que
# volta disfarçado de premissa de mercado. Ver docstring do módulo e o
# plano (`docs/superpowers/plans/2026-08-21-v4-item3b-reversa-sensibilidades.md`,
# decisão D2).
_ALVO_BASE = "corrente"

# "Rentabilidade terminal muito alta" não é um infinito matemático — é a
# aproximação numérica do limite RiR_TV = gp/RONIC → 0 (decisão D4 do plano
# `docs/superpowers/plans/2026-08-21-v4-item3b-reversa-sensibilidades.md`):
# rentabilidade terminal alta o bastante faz o reinvestimento perpétuo
# tender a zero sem resolver o limite em forma fechada. O valor é arbitrário
# por natureza — qualquer número "grande o bastante" serve — e é exatamente
# por isso que `test_teto_e_insensivel_a_escolha_do_infinito` existe: trava
# que o `multiplo` devolvido não muda entre 1e5, 1e6 e 1e7. Uma constante
# mágica sem esse teste de estabilidade seria número inventado, não
# aproximação.
RENTABILIDADE_TERMINAL_INFINITA: float = 1e6

# Os dois eixos PRIMÁRIOS da metodologia (decisão D4): os únicos cujo
# `raizes_*` vazio aciona o teto do crescimento gratuito. `custo_capital`
# tem observável de mercado direto (o beta implícito) e não depende do teto
# para ser interpretado; `cap` tem shape próprio (`CAP_implicito_anos`, sem
# `raizes_*` nem `sugestao`) e não entra nesta checagem — consultá-lo aqui
# seria olhar uma chave que ele nunca tem.
EIXOS_PRIMARIOS: frozenset = frozenset({"rentabilidade", "crescimento"})

# --------------------------------------------------------------------------
# Fatia 5F, Task 1 (D2): os vocabulários da `leitura` de cada eixo. Tuplas DESTE
# módulo, rotuladas pelo catálogo (`motivos_da_leitura`, `identificacoes`,
# `posicoes_na_banda`) e travadas contra ele por igualdade de conjunto em
# tests/test_catalogo_apresentacao.py — o relatório rotula o código e nunca lê a
# prosa do motor nem as palavras de `beta_implicito`.
# --------------------------------------------------------------------------

# As saídas do `rev` que `_motivo_do_eixo` distingue: raiz ou não nos três eixos
# percentuais, e as quatro do eixo 'cap'.
MOTIVOS_DA_LEITURA: tuple[str, ...] = (
    "raiz_na_faixa", "sem_raiz_na_faixa",
    "cap_na_faixa", "cap_na_faixa_decrescente", "cap_fora_da_faixa", "cap_indefinido",
)

# As classes de `identificacao()` do motor: a largura relativa do intervalo
# compatível com o alvo ± a tolerância abaixo de 5%, abaixo de 20%, ou acima.
IDENTIFICACOES: tuple[str, ...] = ("forte", "moderada", "fraca")

# Código da posição do beta implícito contra a banda -> as palavras que
# `beta_implicito.posicao_na_banda` publica desde a fatia B (os testes da 3B as
# leem, e elas ficam como estão). Uma tabela só, lida nos dois sentidos.
_POSICAO_EM_PALAVRAS: dict[str, str] = {
    "abaixo": "abaixo",
    "acima": "acima",
    "dentro": "dentro",
    "sem_banda": "banda não declarada",
    "sem_raiz": "sem raiz",
}
POSICOES_NA_BANDA: tuple[str, ...] = tuple(_POSICAO_EM_PALAVRAS)
_POSICAO_POR_PALAVRAS: dict[str, str] = {palavras: codigo for codigo, palavras in _POSICAO_EM_PALAVRAS.items()}

# O eixo 'cap' numérico: a `direcao` que o motor escreve decide se o número mede
# vantagem competitiva (o valor cresce com n) ou os anos de destruição de valor
# que o preço tolera (o valor decresce com n). Os dois literais do ramo `cap` do
# `rev`, verbatim — conferidos contra o motor em tests/test_valuation_reversa.py.
_MOTIVO_DO_CAP_POR_DIRECAO: dict[str, str] = {
    "valor cresce com n (spread positivo)": "cap_na_faixa",
    "valor DECRESCE com n — interpretação invertida: n maior destrói valor": "cap_na_faixa_decrescente",
}

# As unidades da leitura, chaves de `catalogo.unidades`: a raiz, o intervalo e o
# toque tangencial em pontos percentuais (`raizes_*_%`, a unidade das premissas
# que eles resolvem); o CAP em anos interpolados; a curvatura e o beta, números.
_UNIDADE_DA_RAIZ = "pp"
_UNIDADE_DO_CAP = "anos_fracionarios"
_UNIDADE_DA_CURVATURA = "curvatura"
_UNIDADE_DO_BETA = "beta"

# `identificacao()` chaveia o intervalo pela tolerância (`intervalo_para_alvo_±1%`).
_PREFIXO_DO_INTERVALO = "intervalo_para_alvo_±"

# --------------------------------------------------------------------------
# Fatia 5H, Task 1 (D2): o nível implícito e o confronto temporal. Tupla DESTE
# módulo, rotulada pelo catálogo (`leituras_do_nivel`) e travada contra ele por
# igualdade de conjunto em tests/test_catalogo_apresentacao.py.
# --------------------------------------------------------------------------

# As duas leituras do confronto temporal (vendor `references/aplicacao.md` §4, calibrado
# em J8): a métrica implícita até 125% do maior consenso declarado é ANTECIPAÇÃO
# TEMPORAL — o mercado desconta uma base futura, e a reversa correta passa a ser sobre o
# vetor consenso; acima disso, a hipótese terminal está no preço. Os códigos são o
# PREFIXO da prosa que o motor escreve em `leitura` (`"<codigo>: <texto>"`): a chave sai
# classificada aqui, e a prosa do motor nunca chega à tela. Mesma disciplina de
# `MOTIVOS_DA_LEITURA`.
LEITURAS_DO_NIVEL: tuple[str, ...] = ("antecipacao_temporal", "acima_do_consenso")

# O subcomando do motor que faz a conta (justos.py, `nivel_implicito`; desde a v10.1 também
# `nivel_recalculado`) e os dois pontos do consenso que ele aceita, na ordem em que o caso os
# declara.
_SUBCOMANDO_DO_NIVEL = "nivel"
_PONTOS_DO_CONSENSO: tuple[str, ...] = ("t1", "t2")
_SEPARADOR_DA_LEITURA = ":"

# v10.1: premissas do cenário que o `nivel` do motor usa na leitura RECALCULADA (vetor travado).
# `da` NÃO entra: `nivel` não tem `--da`, e o argparse aceitaria `--da` como abreviação de
# `--da-absoluta` em silêncio — o encargo de reposição entra em moeda, por `--da-absoluta`.
_PREMISSAS_DA_LEITURA_RECALCULADA: tuple[str, ...] = (
    "tax", "g", "roic", "wacc", "n", "tv", "roic_tv", "gp", "roic_book", "mid_year")


def alvo_de_mercado(caso: Caso, nome_cenario: str, nd_efetivo: float,
                    valor_da_metrica: float | None = None) -> dict:
    """Calcula o alvo de múltiplo de mercado: a definição de múltiplo
    aplicada aos dados já declarados no caso (preço, ações, métrica-base e,
    na rota firm, a ponte via `nd_efetivo`) — não é reinterpretação nem
    ajuste, é a mesma conta de escala que a fatia A já faz em `avaliar.py`
    para o ramo NOPAT, aplicada aqui ao preço observado em vez do valor que
    o motor devolve.

    Rota firm: `market_cap = preço × ações`, `EV_mercado = market_cap +
    nd_efetivo`, `valor = EV_mercado ÷ métrica-base`; `base` é `"ebitda"`
    ou `"nopat"` conforme o tipo declarado em `metrica_base`.

    Rota rampa (fatia 5A, item 5, Task 1): MESMO lado EV do firm —
    `EV_mercado = market_cap + nd_efetivo`, `valor = EV_mercado ÷
    métrica-base`; `base` é sempre `"ebitda0"` (a única métrica que a rota
    aceita — `caso.METRICAS_POR_ROTA["rampa"] == {"EBITDA0"}`, nunca uma
    escolha a fazer aqui). Corrige um bug latente: até esta fatia, a rota
    rampa caía no `else` (equity) abaixo — `valor = market_cap ÷ ebitda0`,
    sem somar `nd_efetivo`, um número plausível mas ERRADO (P/L sobre
    EBITDA0 em vez de EV/EBITDA0). Nunca foi alcançado por um caso real
    porque `caso._validar_reversa` recusa 'reversa' na rota 'rampa' no
    gate — mas a fatia 5A passa a publicar este múltiplo SEMPRE, como
    `mercado_tela` em `resultados.json` (não mais só dentro do bloco
    `reversa`), e publicar sempre transformaria esse bug em número errado
    na tela do analista.

    Rota equity: `valor = market_cap ÷ lucro` (a própria métrica-base, que
    `caso.py` só aceita como `"LL"` nesta rota — não há ponte de dívida do
    lado equity); `base` é `"pl"`.

    Rota desconhecida levanta `ValueError` — nunca alcançável por um caso
    que passou por `caso.validar` (só firm/equity/rampa existem no
    vocabulário de rota), mas esta função não presume isso: recusar por
    nome, mesmo aqui, é mais seguro que deixar uma quarta rota cair no
    ramo errado em silêncio, exatamente o defeito que esta mesma correção
    fecha para a rampa.

    `algebra` é uma frase com os números da conta, para auditoria — não um
    resumo, os valores literais que entraram e saíram.

    `nome_cenario` não entra nesta conta: o alvo deriva só de campos de
    topo do caso (preço, ações, métrica-base), nunca do vetor de premissas
    de um cenário específico. O parâmetro existe para que a chamada tenha
    a mesma forma de `reverter(caso, nome_cenario, nd_efetivo)`, que usa o
    nome para buscar o cenário-alvo e o vetor central de premissas dele.

    `valor_da_metrica` (fatia 5F, Task 2, D5): quando dado, substitui o valor da
    métrica-base no denominador — a mesma conta com a métrica forward que o caso
    declara (`metrica_forward.valor`, do mesmo tipo da métrica-base), para o
    múltiplo de tela forward. Sem ele, a conta de sempre.
    """
    rota = caso["rota"]
    preco = caso["preco"]["valor"]
    acoes = caso["acoes_diluidas"]
    metrica = caso["metrica_base"]
    metrica_valor = metrica["valor"] if valor_da_metrica is None else valor_da_metrica
    market_cap = preco * acoes

    if rota == "firm":
        ev_mercado = market_cap + nd_efetivo
        valor_de_mercado = ev_mercado
        valor = ev_mercado / metrica_valor
        base = "ebitda" if metrica["tipo"] == "EBITDA" else "nopat"
        algebra = (
            f"market_cap = preco {preco} x acoes {acoes} = {market_cap}; "
            f"EV_mercado = market_cap {market_cap} + nd_efetivo {nd_efetivo} "
            f"= {ev_mercado}; alvo = EV_mercado {ev_mercado} / "
            f"{metrica['tipo']} {metrica_valor} = {valor}"
        )
    elif rota == "rampa":
        ev_mercado = market_cap + nd_efetivo
        valor_de_mercado = ev_mercado
        valor = ev_mercado / metrica_valor
        base = "ebitda0"
        algebra = (
            f"market_cap = preco {preco} x acoes {acoes} = {market_cap}; "
            f"EV_mercado = market_cap {market_cap} + nd_efetivo {nd_efetivo} "
            f"= {ev_mercado}; alvo = EV_mercado {ev_mercado} / "
            f"{metrica['tipo']} {metrica_valor} = {valor}"
        )
    elif rota == "equity":
        valor_de_mercado = market_cap
        valor = market_cap / metrica_valor
        base = "pl"
        algebra = (
            f"market_cap = preco {preco} x acoes {acoes} = {market_cap}; "
            f"alvo = market_cap {market_cap} / {metrica['tipo']} "
            f"{metrica_valor} = {valor}"
        )
    else:
        raise ValueError(
            f"alvo_de_mercado: rota desconhecida {rota!r} — só 'firm', "
            "'rampa' e 'equity' têm alvo de múltiplo de mercado definido "
            "nesta fatia."
        )

    # `valor_de_mercado` (fatia 5H, Task 1, D2): o NUMERADOR desta mesma conta — o EV
    # de mercado nas rotas que atravessam a ponte, o market cap na equity —, publicado
    # ao lado do múltiplo em vez de ficar só dentro da `algebra`. É o que o subcomando
    # `nivel` do motor recebe em `--alvo-valor`; sem ele, `nivel_implicito` teria de
    # refazer a mesma soma numa segunda cópia da conta (a lição do FIX 2 da revisão
    # final), ou reconstruí-la multiplicando o múltiplo pela métrica-base de volta.
    return {"valor": valor, "valor_de_mercado": valor_de_mercado,
            "algebra": algebra, "base": base}


def _posicao_e_distancia(beta: float, banda: list | None) -> tuple[str, float | None]:
    """Posição do beta implícito contra a banda de beta observado — sem
    adjetivo, só posição e distância (plano, decisão D3). `banda`, quando
    presente, já chega validada por `caso.py` como `[mínimo, máximo]` com
    mínimo < máximo; `None` quando o caso não declarou `beta_observado`.
    """
    if banda is None:
        return "sem_banda", None
    minimo, maximo = banda
    if beta < minimo:
        return "abaixo", minimo - beta
    if beta > maximo:
        return "acima", beta - maximo
    return "dentro", 0.0


def _beta_implicito(saida_eixo: dict, variavel: str, mercado: dict) -> dict:
    """Inversão declarada do CAPM sobre a raiz do eixo de custo de capital:
    `beta_implicito = (custo_implícito − rf) ÷ erp`. É a única conta de
    valuation, além do alvo de mercado, que este módulo faz — a álgebra vai
    registrada com os números, não só o resultado.

    Calculado sobre a PRIMEIRA raiz que o motor devolveu para `variavel`
    (`raiz_usada` diz qual, em pontos percentuais); quando há mais de uma
    raiz, `nota_multiplas_raizes` deixa explícito que o beta corresponde só
    àquela primeira, nunca ao conjunto — múltiplas raízes não viram média
    nem escolha silenciosa.

    Sem raiz nenhuma (eixo de custo de capital que também não fechou), não
    há custo implícito para inverter: devolve `valor=None` com a álgebra
    explicando o motivo, em vez de levantar exceção ou inventar um número —
    a mesma leitura do eixo (`sem_solucao`/`sugestao`) já está em
    `saida_eixo`, íntegra.
    """
    rf = mercado["rf"]
    erp = mercado["erp"]
    raizes = saida_eixo.get(f"raizes_{variavel}_%") or []

    if not raizes:
        return {
            "valor": None,
            "algebra": (
                f"sem raiz para {variavel} — beta implícito não calculável "
                "(ver 'sem_solucao'/'sugestao' neste mesmo eixo)"
            ),
            "posicao_na_banda": _POSICAO_EM_PALAVRAS["sem_raiz"],
            "distancia": None,
        }

    raiz_usada = raizes[0]
    beta = (raiz_usada - rf) / erp
    algebra = (
        f"beta_implicito = (custo_implicito - rf) / erp = "
        f"({raiz_usada} - {rf}) / {erp} = {beta}"
    )
    posicao, distancia = _posicao_e_distancia(beta, mercado.get("beta_observado"))

    resultado = {
        "valor": beta,
        "algebra": algebra,
        "posicao_na_banda": _POSICAO_EM_PALAVRAS[posicao],
        "distancia": distancia,
        "raiz_usada": raiz_usada,
    }
    if len(raizes) > 1:
        resultado["nota_multiplas_raizes"] = (
            f"{len(raizes)} raízes para {variavel} — o beta implícito "
            f"corresponde só à primeira ({raiz_usada}%), não ao conjunto."
        )
    return resultado


def _resolucao(nome_eixo: str, variavel: str, saida: dict) -> dict:
    """Marcador do WRAPPER — `{"resolveu": bool, "motivo": str}` —, sempre
    acrescentado AO LADO do que o motor devolveu para o eixo, nunca no
    lugar de nenhuma chave dele (endurecimento, task 3B, RISCO 1+3).

    O motor devolve legitimamente quatro shapes diferentes para um eixo de
    reversa (ver docstring do módulo): raiz não vazia (resolvido), raiz
    vazia (não resolvido), `CAP_implicito_anos` alcançável — float — ou
    fora da faixa 1-60 — string — (resolvido / não resolvido) e `cap` com
    spread não positivo — nem raiz nem `CAP_implicito_anos`, só `erro` e
    `alvo_normalizado` (não resolvido). Uniformizar ESSES quatro shapes
    destruiria a honestidade do motor; este marcador não uniformiza nada
    — só resume, num ponto só, a pergunta "este eixo produziu valor
    utilizável?", para que o consumidor seguinte (o relatório) não precise
    conhecer os quatro shapes para responder essa pergunta.

    `motivo` é frase curta DESTE wrapper, nunca cópia do texto do motor —
    o texto do motor (`sem_solucao`, `erro`) já está ao lado, íntegro;
    repeti-lo aqui seria a mesma informação duas vezes, uma delas fora do
    controle do motor.

    Eixo 'cap' tem shape próprio (sem `raizes_*`): resolve via
    `CAP_implicito_anos` — presente e não-string quando alcançável, string
    quando fora da faixa de anos — ou fica indefinido quando o motor
    devolve `erro` no lugar dos dois (spread <= 0). Os outros três eixos
    resolvem via `raizes_<variavel>_%`: a checagem é de LISTA VAZIA/NÃO
    VAZIA, nunca do valor da raiz — uma raiz em 0.0 é `[0.0]`, lista
    não-vazia, portanto resolvida (mesma checagem `not raizes` que
    `_beta_implicito` já usa, para a mesma lista).
    """
    # Fatia 5F, Task 1: a decisão é a de `_motivo_do_eixo`, o classificador único que
    # a `leitura` também lê; as frases e o `resolveu` de cada saída não mudam.
    motivo = _motivo_do_eixo(nome_eixo, variavel, saida)
    if motivo == "cap_indefinido":
        return {
            "resolveu": False,
            "motivo": "CAP implícito indefinido: spread do eixo não é positivo.",
        }
    if motivo == "cap_fora_da_faixa":
        return {
            "resolveu": False,
            "motivo": "CAP implícito fora da faixa de anos (1-60).",
        }
    if motivo in ("cap_na_faixa", "cap_na_faixa_decrescente"):
        return {
            "resolveu": True,
            "motivo": "CAP implícito dentro da faixa de anos (1-60).",
        }
    if motivo == "raiz_na_faixa":
        return {
            "resolveu": True,
            "motivo": f"raiz encontrada na faixa de busca de '{variavel}'.",
        }
    return {
        "resolveu": False,
        "motivo": f"sem raiz na faixa de busca de '{variavel}'.",
    }


def _motivo_do_eixo(nome_eixo: str, variavel: str, saida: dict) -> str:
    """O código de `MOTIVOS_DA_LEITURA` para a saída do motor num eixo — o
    classificador ÚNICO das saídas do `rev` (fatia 5F, Task 1): `_resolucao` e
    `leitura_do_eixo` leem a mesma decisão, nunca duas cópias dela.

    Eixo 'cap' (ramo `cap` do `rev`): `erro` (spread não positivo sob book) ->
    `cap_indefinido`; `CAP_implicito_anos` texto (fora de 1-60, nas duas direções
    da série) -> `cap_fora_da_faixa`; número -> `cap_na_faixa`, ou
    `cap_na_faixa_decrescente` quando o motor declara que o valor decresce com n.
    Uma `direcao` fora das duas que o motor escreve é `MotorFalhou` nomeado: a
    leitura não chuta o que o número mede. Os três eixos percentuais:
    `raizes_<variavel>_%` não vazia -> `raiz_na_faixa`; vazia ->
    `sem_raiz_na_faixa` (lista vazia ou não, nunca o valor: `[0.0]` resolve). Um
    eixo só com toque tangencial continua sem raiz; o toque sai em
    `leitura.tangenciais`.
    """
    if nome_eixo == "cap":
        if "erro" in saida:
            return "cap_indefinido"
        if isinstance(saida.get("CAP_implicito_anos"), str):
            return "cap_fora_da_faixa"
        direcao = saida.get("direcao")
        if direcao not in _MOTIVO_DO_CAP_POR_DIRECAO:
            raise MotorFalhou(
                f"eixo 'cap' da reversa com 'direcao' fora das duas que o motor escreve: {direcao!r}. "
                "Sem ela a leitura não sabe se o CAP implícito mede vantagem competitiva ou os anos de "
                "destruição de valor que o preço tolera."
            )
        return _MOTIVO_DO_CAP_POR_DIRECAO[direcao]
    return "raiz_na_faixa" if saida.get(f"raizes_{variavel}_%") else "sem_raiz_na_faixa"


def _identificacao_da_raiz(identificacao: dict) -> dict:
    """`identificacao`, `intervalo` e `curvatura` de uma raiz, lidos do dict que
    `identificacao()` do motor devolveu para ela. Sem derivadas na vizinhança o
    motor devolve só `{nota}`: os três saem `null`, nunca inventados. Uma classe
    fora de `IDENTIFICACOES` é `MotorFalhou` nomeado — o catálogo não a rotula."""
    if "identificacao" not in identificacao:
        return {"identificacao": None, "intervalo": None, "curvatura": None}
    classe = identificacao["identificacao"]
    if classe not in IDENTIFICACOES:
        raise MotorFalhou(
            f"identificação de raiz fora do vocabulário da leitura da reversa: {classe!r}. "
            f"Classes conhecidas: {', '.join(IDENTIFICACOES)}."
        )
    intervalo = next((valor for chave, valor in identificacao.items()
                      if chave.startswith(_PREFIXO_DO_INTERVALO)), None)
    return {
        "identificacao": classe,
        "intervalo": list(intervalo) if intervalo is not None else None,
        "curvatura": identificacao.get("curvatura_d2M_dx2"),
    }


def leitura_do_eixo(nome_eixo: str, rota: str, saida: dict, banda: list | None = None) -> dict:
    """A leitura normalizada de um eixo (fatia 5F, Task 1, D2), montada sobre o que
    o motor devolveu para ele — mais `beta_implicito`, no eixo de custo de capital —
    e publicada AO LADO desse payload, nunca no lugar dele.

    Todo eixo: `{"premissa", "unidade", "unidade_da_curvatura", "motivo", "raizes",
    "tangenciais", "cap_anos"}`. `unidade` vale para `raizes[].valor`,
    `raizes[].intervalo`, `tangenciais` e `cap_anos`; `unidade_da_curvatura`, para
    `raizes[].curvatura`. As duas são chaves de `catalogo.unidades`: o relatório
    formata pela unidade declarada, nunca pelo nome do campo.

    Eixos percentuais: `premissa` é a variável resolvida (`RESOLVER_POR_EIXO`); cada
    raiz de `raizes_<variavel>_%` pareia com a identificação de mesma POSIÇÃO em
    `identificacao_por_raiz` — os dois nascem da mesma lista de raízes, na mesma
    ordem, e a chave do segundo é o número formatado, nunca reformatado aqui para
    achar o par; comprimentos diferentes são `MotorFalhou`. `tangenciais` são os
    `x_%` dos toques sem cruzamento. Eixo 'cap': `premissa` nula, `raizes` e
    `tangenciais` vazias, `cap_anos` número só quando o CAP fecha na faixa. Eixo de
    custo de capital: também `beta` — `{valor, posicao, distancia, banda, unidade}`,
    lido de `beta_implicito` (a posição pelo código de `POSICOES_NA_BANDA`) e da
    banda declarada em `mercado.beta_observado`, que o chamador passa em `banda`.
    """
    variavel = RESOLVER_POR_EIXO[nome_eixo][rota]
    motivo = _motivo_do_eixo(nome_eixo, variavel, saida)
    if nome_eixo == "cap":
        return {
            "premissa": None,
            "unidade": _UNIDADE_DO_CAP,
            "unidade_da_curvatura": _UNIDADE_DA_CURVATURA,
            "motivo": motivo,
            "raizes": [],
            "tangenciais": [],
            "cap_anos": (saida["CAP_implicito_anos"]
                         if motivo in ("cap_na_faixa", "cap_na_faixa_decrescente") else None),
        }

    valores = saida.get(f"raizes_{variavel}_%") or []
    identificacoes = list((saida.get("identificacao_por_raiz") or {}).values())
    if len(identificacoes) != len(valores):
        raise MotorFalhou(
            f"eixo '{nome_eixo}' da reversa com {len(valores)} raiz(es) em 'raizes_{variavel}_%' e "
            f"{len(identificacoes)} em 'identificacao_por_raiz': a leitura pareia raiz e identificação "
            "pela posição, e sem o mesmo comprimento o par seria inventado."
        )
    leitura = {
        "premissa": variavel,
        "unidade": _UNIDADE_DA_RAIZ,
        "unidade_da_curvatura": _UNIDADE_DA_CURVATURA,
        "motivo": motivo,
        "raizes": [{"valor": valor, **_identificacao_da_raiz(identificacao)}
                   for valor, identificacao in zip(valores, identificacoes)],
        "tangenciais": [toque["x_%"] for toque in saida.get(f"raizes_tangenciais_{variavel}_%") or []],
        "cap_anos": None,
    }
    if nome_eixo == EIXO_DO_CUSTO_DE_CAPITAL:
        beta = saida["beta_implicito"]
        leitura["beta"] = {
            "valor": beta["valor"],
            "posicao": _POSICAO_POR_PALAVRAS[beta["posicao_na_banda"]],
            "distancia": beta["distancia"],
            "banda": list(banda) if banda is not None else None,
            "unidade": _UNIDADE_DO_BETA,
        }
    return leitura


def _algum_eixo_primario_sem_raiz(resultado_da_reversa: dict) -> bool:
    """O gatilho do teto do crescimento gratuito — e da curva iso-valor, que o motor
    manda rodar junto dele na `sugestao` de um eixo primário sem raiz: algum eixo de
    `EIXOS_PRIMARIOS` declarado voltou com `sugestao`. Uma função só, lida por
    `reverter` (o teto) e por `LIMITACOES_DA_LEITURA` (a iso) — uma segunda cópia da
    condição poderia divergir (a lição do FIX 2 da 3B)."""
    eixos = resultado_da_reversa["eixos"]
    return any("sugestao" in eixos[nome_eixo] for nome_eixo in EIXOS_PRIMARIOS if nome_eixo in eixos)


# Fatia 5F, Task 1 (D3): chave pública de cada limitação da LEITURA da reversa -> o
# gatilho dela sobre o que `reverter` devolveu. As chaves são vocabulário de
# `resultados.limitacoes`, rotuladas pelo catálogo com `afeta: "iso"` (igualdade de
# conjunto travada em tests/test_catalogo_apresentacao.py). Ligar o `iso` do motor
# pede decisões próprias (faixa de g, número de pontos, transição) e um painel novo;
# até lá, a curva que falta sai declarada.
LIMITACOES_DA_LEITURA: dict[str, Callable[[dict], bool]] = {
    "iso_nao_calculada": _algum_eixo_primario_sem_raiz,
}


def limitacoes_da_leitura(resultado_da_reversa: dict) -> list[str]:
    """As chaves de `LIMITACOES_DA_LEITURA` cujo gatilho vale para
    `resultado_da_reversa` (o que `reverter` devolveu), na ordem do registro —
    `avaliar.py` as publica em `resultados.limitacoes`, depois da limitação que
    suprime a reversa."""
    return [chave for chave, gatilho in LIMITACOES_DA_LEITURA.items() if gatilho(resultado_da_reversa)]


def teto_do_crescimento_gratuito(caso: Caso, nome_cenario: str, nd_efetivo: float) -> dict:
    """Caso-limite RiR_TV → 0: com reinvestimento zero, o FCFF/FCFE vira o
    NOPAT/lucro inteiro e o valor colapsa num Gordon puro — o TETO do que
    qualquer história de crescimento pode valer, porque nenhuma hipótese de
    crescimento PAGO chega lá (pagar reinvestimento só subtrai fluxo de
    caixa). Decisão D4 do plano; é a mesma leitura que o motor já cita no
    campo `sugestao` de um eixo primário sem raiz — esta função executa a
    sugestão, não inventa a ideia.

    `reverter` chama esta função automaticamente quando `rentabilidade` ou
    `crescimento` (`EIXOS_PRIMARIOS`) volta sem raiz, mas ela também é
    chamável direto — por isso tem a mesma assinatura de `reverter`
    (`caso, nome_cenario, nd_efetivo`). `nd_efetivo` não entra em conta
    aqui: o teto é um MÚLTIPLO (`EV/EBITDA_curr`/`EV/NOPAT_curr`/`PL_curr`),
    não um preço, e não há ponte de dívida nesta saída — o parâmetro só
    mantém a chamada simétrica à de `alvo_de_mercado` e `reverter`.

    Copia o vetor central de premissas do cenário-alvo e sobrepõe só três
    valores — nunca inventa as outras: `tv` forçado para `"gordon"` (a
    única convenção terminal com forma fechada para RiR_TV → 0);
    `roic_tv`/`roe_tv` (conforme a rota) igualado a
    `RENTABILIDADE_TERMINAL_INFINITA`; `gp` igualado ao `g` do cenário — sem
    essa igualdade o teto teria uma taxa terminal desconectada do `g` que a
    reversa está tentando explicar. As três sobreposições voltam em
    `premissas_alteradas`; o resto do vetor já está visível em
    `caso["cenarios"][nome_cenario]["premissas"]` — reexibi-lo aqui seria
    duplicar, não auditar.

    Roda o motor no subcomando de avaliação direta (`ev`/`pe`, via
    `subcomando=None` em `rodar` — NUNCA `rev`: aqui não há alvo nem
    variável a resolver, é a avaliação do caso-limite em si). `multiplo` é
    o múltiplo "corrente" que o motor devolve para essas premissas —
    campo resolvido por `_campo_do_multiplo` (FIX 2, revisão final:
    `EV/EBITDA_curr`/`EV/NOPAT_curr` na rota firm, conforme
    `metrica_base.tipo`, ou `PL_curr` na rota equity — a mesma tradução que
    `avaliar.precificar_firm`/`precificar_equity` usam, lida de `motor.py`
    em vez de reescrita aqui) — comparável direto ao que a mesma chamada
    devolveria para o vetor do caso-base sem as três sobreposições.
    `diagnosticos` é o que o motor emitiu para esta mesma chamada, íntegro
    — mesma disciplina de `reverter`, nada filtrado.

    FIX 1 (Crítico, revisão final): `multiplo` passa por `_exigir_valor` —
    antes lia `saida[campo_multiplo]` raw, a única leitura do módulo que
    não recusava um `null`. `tv="gordon"` com `gp=g` (a sobreposição logo
    acima) zera o denominador de Gordon exatamente quando `g == wacc`; o
    motor serializa o múltiplo resultante como `null` e sai com código 0
    mesmo assim — e o teto só roda automaticamente quando um eixo primário
    já falhou em fechar (`reverter`), o que torna `g >= wacc` um cenário
    plausível, não exótico. `diagnosticos` ganha a mesma guarda de chave
    ausente que `_exigir_valor` usa ao montar a própria mensagem de erro
    (`.get(...) or []`), em vez do índice raw `saida["diagnosticos"]`.

    Correção do item 3: `rf` (`caso["mercado"]["rf"]`, quando o bloco
    existe) também é repassado a `rodar` — este vetor força `tv="gordon"`
    com `gp=g`, exatamente a combinação que `_guardas_damodaran` audita;
    sem `rf` aqui, o teto saía "PREMISSA NÃO ANCORADA" mesmo quando
    `reverter` já corrigia os quatro eixos, porque este é um SEGUNDO call
    site de `rodar`, independente do de `reverter`.
    """
    rota = caso["rota"]
    moeda = caso["moeda"]
    # Correção do item 3: mesma leitura condicional que avaliar.avaliar()
    # faz — 'mercado' é bloco opcional (`caso.py`, `_validar_mercado`), e
    # esta função é chamável direto, sem garantia de que 'reversa' (que
    # torna 'mercado' obrigatório) esteja presente no caso recebido.
    mercado = caso.get("mercado")
    rf = mercado.get("rf") if mercado else None
    cenario = caso["cenarios"][nome_cenario]
    g = cenario["premissas"]["g"]

    variavel_tv = RESOLVER_POR_EIXO["rentabilidade"][rota] + "_tv"
    premissas_alteradas = {
        "tv": "gordon",
        variavel_tv: RENTABILIDADE_TERMINAL_INFINITA,
        "gp": g,
    }
    vetor = {**cenario["premissas"], **premissas_alteradas}

    saida = rodar(rota, vetor, None, moeda, rf=rf)
    campo_multiplo = _campo_do_multiplo(rota, caso["metrica_base"]["tipo"])

    leitura = (
        "Teto do crescimento gratuito: caso-limite RiR_TV -> 0 (rentabilidade "
        "terminal levada a um número muito grande, gp = g do cenário) — com "
        "reinvestimento zero, todo o lucro operacional vira caixa livre e o "
        "valor colapsa num Gordon puro. Nenhuma hipótese de crescimento PAGO "
        "chega aqui, porque pagar reinvestimento só subtrai fluxo de caixa — "
        "é o teto do que qualquer história de crescimento pode valer. A "
        "distância entre este múltiplo e o múltiplo do caso-base é o preço "
        "que o mercado está pagando pela hipótese de que o crescimento não "
        "consome capital."
    )

    diagnosticos_lista = saida.get("diagnosticos") or []

    return {
        "multiplo": _exigir_valor(saida, campo_multiplo),
        # Fatia 5F, Task 1 (D2): a chave do múltiplo, para o relatório rotulá-lo pelo
        # catálogo sem aprender a tradução rota/métrica -> campo.
        "chave": campo_multiplo,
        "premissas_alteradas": premissas_alteradas,
        "leitura": leitura,
        "diagnosticos": diagnosticos_lista,
        # A3 (onda de correção da revisão final, achado S1 generalizado —
        # "todo `diagnosticos` do resultados.json, onde quer que apareça,
        # ganha o paralelo"): este é o segundo lugar fora de
        # `avaliar._monta_cenario` onde uma lista `diagnosticos` do motor
        # chega a `resultados.json` (o primeiro é `sotp.partes[*]`, ver
        # `sotp._compor_parte`) — `reverter()` embute este dict sob
        # `resultado["reversa"]["teto_do_crescimento_gratuito"]` quando o
        # gatilho dispara (ver docstring do módulo). Mesma classificação por
        # prefixo, mesmo comprimento e ordem, `None` não filtrado.
        "diagnosticos_chaves": [diagnosticos.classificar(m) for m in diagnosticos_lista],
    }


def _multiplo_justo_corrente(caso: Caso, nome_cenario: str) -> float:
    """O múltiplo justo CORRENTE do cenário-alvo da reversa, pelo motor: a avaliação
    direta (`ev`/`pe`) do vetor central do cenário, lida no campo que
    `_campo_do_multiplo` resolve para a rota e a métrica-base. É o mesmo número que
    `avaliar._monta_cenario` publica em `cenarios.<cenário>.multiplos.<chave>` — o
    múltiplo não depende da escala (só das taxas), e um teste prende a igualdade.

    Roda o motor de novo em vez de receber o número já publicado: `reverter` é chamável
    com `(caso, nome_cenario, nd_efetivo)` desde a fatia B, e um quarto parâmetro
    obrigatório mudaria a assinatura em todo call site só para repassar um número que o
    motor devolve de graça. Mesma forma de chamada de `teto_do_crescimento_gratuito`,
    que também avalia um vetor do cenário por conta própria."""
    rota = caso["rota"]
    mercado = caso.get("mercado")
    saida = rodar(rota, caso["cenarios"][nome_cenario]["premissas"], None, caso["moeda"],
                  rf=mercado.get("rf") if mercado else None)
    return _exigir_valor(saida, _campo_do_multiplo(rota, caso["metrica_base"]["tipo"]))


def _leitura_chave_do_nivel(saida: dict) -> str | None:
    """A chave da leitura do confronto temporal, extraída do PREFIXO da prosa que o
    motor escreve em `leitura` (`"antecipacao_temporal: ..."`). `None` quando o caso não
    declara consenso — sem consenso o motor não emite `leitura` nenhuma, e inventar uma
    classificação aqui seria o wrapper decidindo o que o motor não decidiu.

    Um prefixo fora de `LEITURAS_DO_NIVEL` é `MotorFalhou` nomeado, pela mesma razão de
    `_identificacao_da_raiz`: o catálogo não o rotula, e o relatório mostraria código
    cru — ou, pior, a prosa do motor."""
    prosa = saida.get("leitura")
    if prosa is None:
        return None
    chave = str(prosa).split(_SEPARADOR_DA_LEITURA, 1)[0].strip()
    if chave not in LEITURAS_DO_NIVEL:
        raise MotorFalhou(
            f"leitura do nível implícito fora do vocabulário do confronto temporal: {chave!r}. "
            f"Leituras conhecidas: {', '.join(LEITURAS_DO_NIVEL)}."
        )
    return chave


def nivel_implicito(caso: Caso, alvo: dict, multiplo_justo: float, premissas: dict | None = None) -> dict:
    """Reversa em degrau (fatia 5H, Task 1, D2): que NÍVEL da métrica-base o preço
    embute, dadas as taxas do cenário — `métrica_implícita = valor de mercado ÷ múltiplo
    justo` —, confrontado com o consenso de t+1/t+2 que o caso declara.

    A conta é do motor (`justos.nivel_implicito`, subcomando `nivel`): este wrapper só
    monta a chamada com números que já existem — o valor de mercado de
    `alvo_de_mercado` (`--alvo-valor`), o múltiplo justo corrente do cenário
    (`--multiplo`), a métrica-base do caso (`--metrica-base`) e cada ponto de
    `reversa.consenso` (`--consenso-t1`/`--consenso-t2`) — e publica a saída ÍNTEGRA
    mais `leitura_chave`, a classificação do prefixo da prosa. Mesma disciplina de
    `leitura_do_eixo`: nada do motor é removido, renomeado ou reformatado, e o relatório
    lê a chave, nunca o texto.

    Migração v10.1 (Task 2): com `premissas` — o vetor do cenário, que `reverter` só passa
    na rota firm com métrica EBITDA —, a chamada leva também o segundo bloco de flags do
    `nivel` (a D&A absoluta em `--da-absoluta` e `_PREMISSAS_DA_LEITURA_RECALCULADA`), e o
    motor devolve, ao lado da leitura de múltiplo fixo, a RECALCULADA (`recalculado`, ou
    `recalculado.sem_solucao`): o múltiplo refeito a cada nível, com a D&A fixa em moeda e o
    resto do vetor travado. A recalculada é a leitura CENTRAL — e, por identidade, o
    ponto de equilíbrio da base de lucro contra o preço. A congelada é o extremo da escada:
    o limite superior quando o nível implícito sobe acima da métrica declarada (a D&A pesa
    menos, o múltiplo justo sobe e o nível exigido é menor) e, quando ele desce, o extremo
    inferior — a central fica sempre entre a métrica declarada e a congelada. As razões
    contra o consenso e a leitura classificada continuam calculadas pelo motor sobre a
    congelada.

    Sem consenso declarado, o motor não emite `razao_vs_consenso_*` nem `leitura`, e
    `leitura_chave` sai `None` — o nível implícito continua publicado, porque o degrau
    que o preço embute não depende de haver consenso contra o que confrontá-lo.

    `--vol`/`--preco-base` (o `preco_driver_implicito` do motor) ficam de fora: nenhum
    caso declara volume, e sem ele o motor não roda esse ramo.
    """
    consenso = caso["reversa"].get("consenso") or {}
    argumentos: dict = {
        "alvo-valor": alvo["valor_de_mercado"],
        "multiplo": multiplo_justo,
        "metrica-base": caso["metrica_base"]["valor"],
    }
    for nome in _PONTOS_DO_CONSENSO:
        ponto = consenso.get(nome)
        if ponto is not None:
            argumentos[f"consenso-{nome}"] = ponto["valor"]
    if premissas is not None:
        # D&A absoluta = encargo de reposição do cenário × métrica-base: álgebra de escala sobre
        # dois números declarados (a mesma natureza de `alvo_de_mercado`), para o motor
        # recalcular o múltiplo a cada nível com a D&A fixa em moeda.
        argumentos["da-absoluta"] = premissas["da"] / 100.0 * caso["metrica_base"]["valor"]
        for chave in _PREMISSAS_DA_LEITURA_RECALCULADA:
            if premissas.get(chave) is not None:
                argumentos[chave] = premissas[chave]

    saida = rodar(caso["rota"], argumentos, None, None, subcomando=_SUBCOMANDO_DO_NIVEL)
    if "erro" in saida:
        raise MotorFalhou(
            f"motor recusou o nível implícito: {saida['erro']!r} (múltiplo justo "
            f"{multiplo_justo!r}, valor de mercado {alvo['valor_de_mercado']!r})."
        )
    return {**saida, "leitura_chave": _leitura_chave_do_nivel(saida)}


def reverter(caso: Caso, nome_cenario: str, nd_efetivo: float) -> dict:
    """Roda a reversa em todo eixo declarado em `caso["reversa"]["eixos"]`.

    Para cada eixo: monta o vetor central de premissas do cenário-alvo
    MENOS a variável que aquele eixo resolve (a variável que o motor está
    solucionando não pode chegar fixada, senão não há o que resolver), roda
    `rev` no motor congelado com o alvo de mercado, `--resolver`, `--base` e
    `--alvo-base corrente` explícitos, e guarda a saída do motor ÍNTEGRA —
    `sem_solucao`, `sugestao`, `identificacao_por_raiz`, `guardas_v9_4`, a
    conflação marginal×médio sob `book` em `premissas_fixadas`, tudo chega
    exatamente como o motor devolveu, sem filtrar nem reformatar nada. O
    shape de cada eixo NÃO é uniformizado entre si: `cap` devolve
    `CAP_implicito_anos` (float ou string), nunca `raizes_*` — este módulo
    não força um formato comum entre eixos.

    Em TODO eixo, acrescenta a chave `resolucao` —
    `{"resolveu": bool, "motivo": str}` (endurecimento, task 3B, RISCO
    1+3) — ao lado do que o motor devolveu, nunca no lugar de nada: o
    ponto uniforme onde perguntar "este eixo produziu valor utilizável?"
    sem ter que conhecer os quatro shapes possíveis (ver `_resolucao`).
    Desde a 5F, também `leitura` (`leitura_do_eixo`), a forma normalizada da
    mesma saída, que o relatório lê para mostrar o que está no preço.
    No eixo de custo de capital, acrescenta também `beta_implicito` — as
    duas são passthrough puro do motor mais essas adições nomeadas, nunca
    uma reformatação do que o motor pôs. A terceira adição é de topo, não
    por eixo: quando `rentabilidade` ou `crescimento` volta sem raiz
    (`EIXOS_PRIMARIOS`), o resultado ganha a chave
    `teto_do_crescimento_gratuito` — o caso-limite RiR_TV → 0 que o
    próprio motor já sugere rodar no campo `sugestao` daquele eixo (ver
    `teto_do_crescimento_gratuito`). Fechando todos os eixos primários com
    raiz, a chave nem aparece.

    Assume que `caso` já passou por `caso.validar` (responsabilidade de
    quem carregou o caso — `caso.carregar` —, nunca repetida aqui):
    `caso["reversa"]` e `caso["mercado"]` presentes, com o vocabulário de
    eixos e os campos obrigatórios (`rf`, `erp`) já confirmados.

    Correção do item 3: `mercado["rf"]` também é repassado a `rodar` em
    toda chamada por eixo, ao lado de `moeda` — sem ele, `_guardas_
    damodaran` nunca via `rf` e um cenário `gordon` com `gp > 0` saía
    "PREMISSA NÃO ANCORADA" em todo eixo, mesmo com `rf` declarado no
    caso (o mesmo `mercado["rf"]` que `_beta_implicito`, logo abaixo, já
    lia — só nunca alcançava o motor).
    """
    rota = caso["rota"]
    moeda = caso["moeda"]
    mercado = caso["mercado"]
    # Correção do item 3: 'reversa' presente garante 'mercado' com 'rf'
    # confirmado (docstring acima, mesma garantia que `_beta_implicito` já
    # assume ao indexar `mercado["rf"]` direto, abaixo) — indexação direta,
    # sem `.get`.
    rf = mercado["rf"]
    cenario = caso["cenarios"][nome_cenario]
    eixos_declarados = caso["reversa"]["eixos"]

    alvo = alvo_de_mercado(caso, nome_cenario, nd_efetivo)

    eixos: dict[str, dict] = {}
    for nome_eixo in eixos_declarados:
        variavel = RESOLVER_POR_EIXO[nome_eixo][rota]

        vetor = {k: v for k, v in cenario["premissas"].items() if k != variavel}
        vetor["alvo"] = alvo["valor"]
        vetor["resolver"] = variavel
        vetor["base"] = alvo["base"]
        vetor["alvo-base"] = _ALVO_BASE

        saida = rodar(rota, vetor, None, moeda, subcomando="rev", rf=rf)

        if nome_eixo == EIXO_DO_CUSTO_DE_CAPITAL:
            saida["beta_implicito"] = _beta_implicito(saida, variavel, mercado)

        saida["resolucao"] = _resolucao(nome_eixo, variavel, saida)
        # Fatia 5F, Task 1 (D2): a leitura normalizada, também ao lado.
        saida["leitura"] = leitura_do_eixo(nome_eixo, rota, saida, mercado.get("beta_observado"))

        eixos[nome_eixo] = saida

    # Fatia 5H, Task 1 (D2): o nível implícito da métrica-base e o confronto temporal,
    # SEMPRE publicados ao lado do menu de eixos — o que o preço embute em NÍVEL, contra
    # o que ele embute em TAXA. Sem consenso declarado no caso, o bloco sai sem razões e
    # com `leitura_chave` nula (ver `nivel_implicito`).
    # Migração v10.1 (Task 2): a leitura recalculada só existe na rota firm com métrica
    # EBITDA — em ×NOPAT a D&A não entra no múltiplo, e em P/L ela não existe.
    premissas_da_leitura_recalculada = (
        cenario["premissas"] if rota == "firm" and caso["metrica_base"]["tipo"] == "EBITDA" else None)
    resultado: dict = {
        "alvo": alvo,
        "eixos": eixos,
        "nivel_implicito": nivel_implicito(caso, alvo, _multiplo_justo_corrente(caso, nome_cenario),
                                           premissas_da_leitura_recalculada),
    }

    if _algum_eixo_primario_sem_raiz(resultado):
        resultado["teto_do_crescimento_gratuito"] = teto_do_crescimento_gratuito(
            caso, nome_cenario, nd_efetivo
        )

    return resultado
