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
"""

from typing import Any

from caso import EIXOS_DE_REVERSA
from motor import _campo_do_multiplo, _exigir_valor, rodar

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


def alvo_de_mercado(caso: Caso, nome_cenario: str, nd_efetivo: float) -> dict:
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
    """
    rota = caso["rota"]
    preco = caso["preco"]["valor"]
    acoes = caso["acoes_diluidas"]
    metrica = caso["metrica_base"]
    metrica_valor = metrica["valor"]
    market_cap = preco * acoes

    if rota == "firm":
        ev_mercado = market_cap + nd_efetivo
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
        valor = ev_mercado / metrica_valor
        base = "ebitda0"
        algebra = (
            f"market_cap = preco {preco} x acoes {acoes} = {market_cap}; "
            f"EV_mercado = market_cap {market_cap} + nd_efetivo {nd_efetivo} "
            f"= {ev_mercado}; alvo = EV_mercado {ev_mercado} / "
            f"{metrica['tipo']} {metrica_valor} = {valor}"
        )
    elif rota == "equity":
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

    return {"valor": valor, "algebra": algebra, "base": base}


def _posicao_e_distancia(beta: float, banda: list | None) -> tuple[str, float | None]:
    """Posição do beta implícito contra a banda de beta observado — sem
    adjetivo, só posição e distância (plano, decisão D3). `banda`, quando
    presente, já chega validada por `caso.py` como `[mínimo, máximo]` com
    mínimo < máximo; `None` quando o caso não declarou `beta_observado`.
    """
    if banda is None:
        return "banda não declarada", None
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
            "posicao_na_banda": "sem raiz",
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
        "posicao_na_banda": posicao,
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
    if nome_eixo == "cap":
        if "erro" in saida:
            return {
                "resolveu": False,
                "motivo": "CAP implícito indefinido: spread do eixo não é positivo.",
            }
        if isinstance(saida.get("CAP_implicito_anos"), str):
            return {
                "resolveu": False,
                "motivo": "CAP implícito fora da faixa de anos (1-60).",
            }
        return {
            "resolveu": True,
            "motivo": "CAP implícito dentro da faixa de anos (1-60).",
        }

    raizes = saida.get(f"raizes_{variavel}_%")
    if raizes:
        return {
            "resolveu": True,
            "motivo": f"raiz encontrada na faixa de busca de '{variavel}'.",
        }
    return {
        "resolveu": False,
        "motivo": f"sem raiz na faixa de busca de '{variavel}'.",
    }


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

    return {
        "multiplo": _exigir_valor(saida, campo_multiplo),
        "premissas_alteradas": premissas_alteradas,
        "leitura": leitura,
        "diagnosticos": saida.get("diagnosticos") or [],
    }


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

        eixos[nome_eixo] = saida

    resultado: dict = {"alvo": alvo, "eixos": eixos}

    algum_primario_sem_raiz = any(
        "sugestao" in eixos[nome_eixo]
        for nome_eixo in EIXOS_PRIMARIOS
        if nome_eixo in eixos
    )
    if algum_primario_sem_raiz:
        resultado["teto_do_crescimento_gratuito"] = teto_do_crescimento_gratuito(
            caso, nome_cenario, nd_efetivo
        )

    return resultado
