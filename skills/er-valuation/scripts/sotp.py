"""SOTP: soma de partes, ponte única no topo.

Este módulo NÃO faz conta de valuation nova. Cada parte é precificada pela
mesma rota (`precificar_firm`/`precificar_rampa`, de `avaliar.py`) que o
caso inteiro já usaria — só que sem cruzar a ponte: uma parte de SOTP
declara EV, nunca Equity nem preço por ação (D3 do plano da fatia C: "ponte
por parte é o erro que a trava existe para impedir"). A única aritmética
nova autorizada nesta fatia é a soma dos EVs das partes, os dois ajustes de
topo com sinal fixo (D4b) e a ponte do CASO, cruzada uma única vez, no
topo — nunca por parte.

`caso.py` já validou o bloco `sotp` inteiro (tipo, cada parte — rota,
métrica, âncora, triângulo, premissas — e o topo) antes deste módulo rodar;
`compor_partes` confia no dict que recebe, a mesma disciplina que
`avaliar()` já documenta para o caso inteiro ("avaliar não chama
caso.validar de novo... avaliar confia no dict que recebe").

Sinais do topo (D4b, decisão já tomada — não reaberta aqui):

    ev_total = ev_das_partes − custos_corporativos_vp + participacoes_nao_consolidadas

Custo corporativo não alocado é despesa capitalizada: subtrai. Participação
não consolidada é ativo: soma. Só DEPOIS disso a ponte do caso cruza
(`ev_total − nd_efetivo = equity`), e só depois da ponte — nunca antes —
o desconto de holding declarado (D4) incide, sobre o equity:

    equity_pos_ponte = ev_total − nd_efetivo
    equity_final = equity_pos_ponte × (1 − desconto_de_holding_pct / 100)  (quando declarado)

`sotp.topo.desconto_de_holding_pct` só existe validado com
`razao_do_desconto` não vazia (`caso._validar_topo_sotp`) — a metodologia é
explícita: nunca aplicado por hábito. A saída carrega o equity ANTES e
DEPOIS do desconto (nunca só o líquido), dentro de `topo`.

`nome_cenario`: aceito para a mesma forma de chamada de
`reversa.reverter(caso, nome_cenario, nd_efetivo)`/
`sensibilidades.calcular(caso, nome_cenario, nd_efetivo)`, mas não usado
nesta função — cada parte de SOTP declara um único vetor de premissas
próprio (`ancora`/`triangulo`/`premissas` direto na parte, não aninhado sob
um nome de cenário como `caso["cenarios"]`), então não há nada
cenário-dependente do CASO para esta composição consultar. Mantido no
contrato para que quem vier a acoplar isto em `avaliar()` (Fatia C, Task 4)
tenha a mesma forma de chamada dos outros dois compositores por cenário.
"""

from typing import Any

from avaliar import precificar_firm, precificar_rampa
from ponte import compor

Caso = dict[str, Any]

# `avaliar.py` faz `from ponte import compor` e importa `reversa.reverter`
# no topo do arquivo — mas NÃO importa `sensibilidades.calcular` no topo,
# por causa de um ciclo (avaliar -> sensibilidades -> avaliar); o import de
# `calcular` é feito dentro de `avaliar()`, na hora de usar (ver o
# comentário lá). Quando a Fatia C, Task 4 acoplar `compor_partes` dentro
# de `avaliar()`, `from sotp import compor_partes` no TOPO de `avaliar.py`
# fecharia o mesmo tipo de ciclo (sotp.py já importa `avaliar.py` aqui em
# cima) — a Task 4 vai precisar do mesmo import local, dentro de
# `avaliar()`, não no topo do arquivo.

# Chave que `_compor_parte` já promoveu para campo próprio da parte — a
# única que o repasse íntegro do payload do motor (abaixo) precisa pular,
# para não duplicar o mesmo número sob dois nomes. Como uma parte de SOTP
# nunca cruza ponte (ver módulo), o motor nunca emite 'Equity'/'Preco_acao'
# para ela — não há mais nada para filtrar aqui.
_CHAVES_PROMOVIDAS_PARTE: frozenset = frozenset({"EV"})


def _compor_parte(parte: dict, moeda: str | None) -> dict:
    """Avalia uma parte de SOTP com a rota, métrica, âncora, triângulo e
    premissas dela — nunca cruza a ponte.

    Reusa `precificar_firm`/`precificar_rampa` de `avaliar.py` na forma
    sem ponte (`nd_efetivo`/`acoes` omitidos — Fatia C, Task 2): a mesma
    função que compõe o cenário do caso inteiro, só sem escala de
    dívida/ações. Nenhuma quarta cópia da lógica de precificação.

    Repasse íntegro do payload do motor para dentro da parte — mesma
    disciplina de `avaliar._monta_cenario_rampa` ("diagnósticos são o
    produto"): toda chave que o motor devolveu sobrevive verbatim na
    parte, salvo 'EV' (já promovida a campo próprio, ver
    `_CHAVES_PROMOVIDAS_PARTE`). Como a parte nunca cruza ponte, o motor
    nunca emite 'Equity'/'Preco_acao' para ela nesta chamada — confirmado
    por sondagem direta do motor (ver docstrings de `precificar_firm`/
    `precificar_rampa`) — por isso a parte resultante nunca carrega essas
    duas chaves, sem precisar filtrá-las à mão.
    """
    rota = parte["rota"]
    metrica = parte["metrica_base"]
    premissas = parte["premissas"]

    if rota == "firm":
        saida, valor, algebra, _multiplo = precificar_firm(
            premissas, metrica["tipo"], metrica["valor"], moeda=moeda)
    else:  # rampa — a única outra rota que `caso._validar_parte` aceita
        # para parte de SOTP (equity nunca emite 'EV', ver docstring do
        # módulo); `compor_partes` confia nisso, não revalida.
        saida, valor, algebra, _multiplo = precificar_rampa(premissas, moeda=moeda)

    resultado: dict = {
        "nome": parte["nome"],
        "rota": rota,
        "metrica_base": metrica,
        "ancora": parte["ancora"],
        "premissas": premissas,
        "EV": valor["EV"],
        "algebra_da_escala": algebra,
    }
    if "triangulo" in parte:
        resultado["triangulo"] = parte["triangulo"]

    for chave, valor_do_motor in saida.items():
        if chave in _CHAVES_PROMOVIDAS_PARTE:
            continue
        resultado[chave] = valor_do_motor

    return resultado


def compor_partes(caso: Caso, nome_cenario: str) -> dict:
    """Compõe as partes de `caso["sotp"]`, soma os EVs, aplica os ajustes
    de topo (D4b), cruza a ponte do caso uma única vez (D3) e — quando
    declarado — aplica o desconto de holding sobre o equity pós-ponte (D4).

    Devolve
    `{"partes": [...], "ev_das_partes": float, "topo": {...},
      "ev_total": float, "equity": float, "preco_acao": float,
      "ponte_unica": {...}}`.

    Não valida `caso` de novo — `caso.validar()` é responsabilidade
    exclusiva de quem carrega o caso, a mesma disciplina que `avaliar()`
    já documenta. `caso["sotp"]` chega com `tipo`, `partes` (>= 2, nomes
    distintos, cada uma com rota/métrica/âncora/triângulo/premissas
    válidos para a rota dela) e `topo` (os quatro campos, desconto
    exigindo razão) já confirmados.
    """
    sotp = caso["sotp"]
    moeda = caso["moeda"]
    topo_declarado = sotp["topo"]

    partes = [_compor_parte(parte, moeda) for parte in sotp["partes"]]

    ev_das_partes = sum(p["EV"] for p in partes)

    custos_corporativos_vp = topo_declarado["custos_corporativos_vp"]
    participacoes_nao_consolidadas = topo_declarado["participacoes_nao_consolidadas"]
    # D4b: custo corporativo não alocado é despesa capitalizada — subtrai;
    # participação não consolidada é ativo — soma. Única soma de EVs desta
    # fatia, mais os dois ajustes de topo com sinal fixo.
    ev_total = ev_das_partes - custos_corporativos_vp + participacoes_nao_consolidadas

    # D3: a ponte cruza UMA vez, aqui — nunca dentro de `_compor_parte`.
    ponte_unica = compor(caso["ponte"])
    nd_efetivo = ponte_unica["nd_efetivo"]
    equity_antes_do_desconto = ev_total - nd_efetivo

    desconto_pct = topo_declarado.get("desconto_de_holding_pct")
    razao_do_desconto = topo_declarado.get("razao_do_desconto")
    if desconto_pct is not None:
        # D4: incide DEPOIS da ponte, sobre o equity — nunca sobre o EV, e
        # nunca antes da ponte cruzar.
        equity_depois_do_desconto = equity_antes_do_desconto * (1 - desconto_pct / 100.0)
    else:
        equity_depois_do_desconto = equity_antes_do_desconto

    acoes = caso["acoes_diluidas"]
    equity_final = equity_depois_do_desconto
    preco_acao = equity_final / acoes

    topo_resultado = {
        "custos_corporativos_vp": custos_corporativos_vp,
        "participacoes_nao_consolidadas": participacoes_nao_consolidadas,
        "desconto_de_holding_pct": desconto_pct,
        "razao_do_desconto": razao_do_desconto,
        # D4: "a saída traz o valor antes e depois, nunca só o líquido".
        "equity_antes_do_desconto_de_holding": equity_antes_do_desconto,
        "equity_depois_do_desconto_de_holding": equity_depois_do_desconto,
    }

    return {
        "partes": partes,
        "ev_das_partes": ev_das_partes,
        "topo": topo_resultado,
        "ev_total": ev_total,
        "equity": equity_final,
        "preco_acao": preco_acao,
        "ponte_unica": ponte_unica,
    }
