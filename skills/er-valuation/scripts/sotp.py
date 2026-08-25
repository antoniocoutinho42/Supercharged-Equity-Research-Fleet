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
`sensibilidades.calcular(caso, nome_cenario, nd_efetivo)` — cada parte de
SOTP declara um único vetor de premissas próprio (`ancora`/`triangulo`/
`premissas` direto na parte, não aninhado sob um nome de cenário como
`caso["cenarios"]`), então não há nada cenário-dependente do CASO para esta
composição consultar, e a conta em si não varia com `nome_cenario` — isso
continua verdade depois da Fatia C, Task 3. O que a Task 3 mudou (revisão
da Task 2, achado (d)): `compor_partes` agora RECUSA um `nome_cenario` que
não existe em `caso["cenarios"]`, em vez de aceitar qualquer string.  Sem
essa guarda, `compor_partes(caso, "bear")` e `compor_partes(caso, "bull")`
devolviam, em silêncio, exatamente os mesmos números — nenhum dos dois
nomes influencia coisa nenhuma aqui — uma armadilha para quem vier a
acoplar isto em `avaliar()` (Fatia C, Task 4) e esperar, por engano, um
resultado cenário-dependente de um nome que nem existe no caso. A guarda
existe só para que um nome inexistente falhe alto — nunca para fazer a
conta variar por cenário; ela continua igualmente flat depois da guarda,
para qualquer nome que exista.

Fatia C, Task 3 também acrescenta `materialidade()`: quando o caso declara
`sotp.materialidade.blended` (o vetor de premissas consolidado — "as
premissas do blend"), `compor_partes` roda esse vetor pela mesma rota do
caso e devolve `EV_segmentado − EV_blended`, com sinal, sob a chave
`"materialidade"` do resultado (`None` quando o caso não declara
`blended` — o bloco é opcional). Ver o docstring de `materialidade`,
abaixo, para a leitura do sinal.
"""

from typing import Any

from avaliar import precificar_firm, precificar_rampa
from caso import CasoInvalido
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

    # FIX 6e (revisão final): além da chave já PROMOVIDA acima ('EV'), o
    # loop também pula qualquer chave que já exista em `resultado` — nome,
    # rota, metrica_base, ancora, premissas, algebra_da_escala, e
    # triangulo quando presente. Nenhuma colisão existe hoje (o motor não
    # emite nenhum desses nomes), mas sem esta guarda uma chave nova do
    # motor que algum dia colidisse com um campo autorado sobrescreveria
    # esse campo em silêncio — `chave in resultado` fecha essa fronteira
    # de forma estrutural, sem precisar enumerar cada campo autorado à
    # mão numa segunda lista que poderia esquecer alguma.
    for chave, valor_do_motor in saida.items():
        if chave in resultado or chave in _CHAVES_PROMOVIDAS_PARTE:
            continue
        resultado[chave] = valor_do_motor

    return resultado


def materialidade(caso: Caso, nome_cenario: str, ev_segmentado: float) -> dict | None:
    """Compara `ev_segmentado` (a soma das partes, D3 — sem os ajustes de
    topo, D4b: eles são ponte-adjacentes, não parte da pergunta "segmentar
    muda o preço?") contra o EV do vetor BLENDED que o caso declara em
    `sotp.materialidade.blended` — as premissas consolidadas, "o que o
    caso valeria se fosse precificado como um bloco só, com um múltiplo
    só". Devolve `None` quando o caso não declara esse bloco:
    `materialidade` é OPCIONAL, nem todo SOTP precisa dela.

    A DIREÇÃO do viés se CALCULA, não se deduz: o múltiplo que o motor
    devolve não é linear nas premissas, crescimento e rentabilidade de
    partes heterogêneas não são ponderados pela mesma métrica ao somar, e
    o Hessiano da função de precificação é indefinido na região relevante
    — não há intuição confiável sobre se blendar SUPERESTIMA ou SUBESTIMA
    o valor segmentado; só rodar os dois vetores e subtrair responde.
    `diferenca = ev_segmentado - ev_blended`, com sinal: `"+"` quando o
    segmentado excede o blended (o consolidado SUBESTIMA o valor implícito
    pela soma das partes); `"-"` no sentido oposto (o consolidado
    SUPERESTIMA); `"0"` quando os dois coincidem. `leitura` é a mesma
    frase, em português, sem adjetivo de magnitude — "quanto" o viés é não
    é uma pergunta que este wrapper responde, só "para que lado".

    O vetor blended roda pela MESMA rota do caso inteiro (`caso["rota"]`),
    SEM ponte (mesmo modo EV-only que cada parte de SOTP já usa —
    `nd_efetivo`/`acoes` omitidos de `precificar_firm`/`precificar_rampa`)
    — mesmo caminho de precificação e mesma recusa de `null` do motor que
    qualquer outro vetor de premissas deste módulo, herdada de dentro
    dessas duas funções (`caso.py` já validou `blended` com o mesmo
    vocabulário de um cenário, na mesma rota — `_validar_materialidade`).
    `blended` não declara 'rota' própria: é a versão consolidada do CASO
    inteiro, não uma parte nova, então usa a rota que o caso já usa para
    tudo mais — as duas únicas rotas que produzem EV para uma parte de
    SOTP também são as únicas para as quais isto foi pensado (D3: a rota
    equity nunca emite EV — ver `_ROTAS_DE_PARTE_SOTP` em `caso.py`).

    `nome_cenario` não entra em nenhuma conta aqui — o vetor blended, como
    o de cada parte de SOTP, é um vetor de premissas FLAT, declarado uma
    vez só (não aninhado por nome de cenário); aceito só pela mesma forma
    de chamada que `compor_partes` (que já valida `nome_cenario` antes de
    chegar aqui) mantém com o resto do módulo.
    """
    sotp = caso["sotp"]
    bloco = sotp.get("materialidade")
    if bloco is None:
        return None

    blended = bloco["blended"]
    moeda = caso["moeda"]
    rota = caso["rota"]
    metrica = blended["metrica_base"]
    premissas = blended["premissas"]

    if rota == "firm":
        _saida, valor, _algebra, _multiplo = precificar_firm(
            premissas, metrica["tipo"], metrica["valor"], moeda=moeda)
    else:  # rampa — a outra rota que produz EV (D3, ver `caso.py`)
        _saida, valor, _algebra, _multiplo = precificar_rampa(premissas, moeda=moeda)

    ev_blended = valor["EV"]
    diferenca = ev_segmentado - ev_blended

    if diferenca > 0:
        sinal = "+"
        leitura = (
            "EV segmentado acima do EV blended: o consolidado subestima "
            "o valor implícito pela soma das partes."
        )
    elif diferenca < 0:
        sinal = "-"
        leitura = (
            "EV segmentado abaixo do EV blended: o consolidado "
            "superestima o valor implícito pela soma das partes."
        )
    else:
        sinal = "0"
        leitura = (
            "EV segmentado igual ao EV blended: nenhum viés de "
            "consolidação neste vetor de premissas."
        )

    return {
        "ev_blended": ev_blended,
        "ev_segmentado": ev_segmentado,
        "diferenca": diferenca,
        "sinal": sinal,
        "leitura": leitura,
    }


def compor_partes(caso: Caso, nome_cenario: str) -> dict:
    """Compõe as partes de `caso["sotp"]`, soma os EVs, aplica os ajustes
    de topo (D4b), cruza a ponte do caso uma única vez (D3), aplica —
    quando declarado — o desconto de holding sobre o equity pós-ponte (D4)
    e compara — quando o caso declara `sotp.materialidade.blended` — o EV
    segmentado contra o EV do vetor blended (Fatia C, Task 3).

    Devolve
    `{"cenario": str, "partes": [...], "ev_das_partes": float,
      "materialidade": dict | None, "topo": {...}, "ev_total": float,
      "equity": float, "preco_acao": float, "ponte_unica": {...}}`.
    `cenario` (FIX 6c, revisão final) ecoa `nome_cenario` — sem essa chave,
    um leitor de `resultados.json` que só olhasse o bloco `sotp` não tinha
    como saber qual cenário foi nomeado; a chave só existia no INPUT
    (`caso["sotp"]["cenario"]`), nunca no output.

    Não valida `caso` de novo — `caso.validar()` é responsabilidade
    exclusiva de quem carrega o caso, a mesma disciplina que `avaliar()`
    já documenta. `caso["sotp"]` chega com `tipo`, `partes` (>= 2, nomes
    distintos, cada uma com rota/métrica/âncora/triângulo/premissas
    válidos para a rota dela), `topo` (os quatro campos, desconto exigindo
    razão) e, quando presente, `materialidade.blended` (mesmo vocabulário
    de um cenário) já confirmados.

    Levanta `CasoInvalido` quando `nome_cenario` não existe em
    `caso["cenarios"]` — ver o docstring do módulo (achado (d) da revisão
    da Task 2): partes de SOTP carregam um vetor de premissas FLAT (não
    por cenário), então nada aqui muda com `nome_cenario` — a guarda
    existe só para que um nome inexistente falhe alto, em vez de devolver,
    em silêncio, os mesmos números que qualquer outro nome produziria.
    """
    if nome_cenario not in caso["cenarios"]:
        raise CasoInvalido(
            f"cenário '{nome_cenario}' inexistente em 'cenarios': "
            "compor_partes recebe nome_cenario pela mesma forma de "
            "chamada de reversa.reverter/sensibilidades.calcular, mas "
            "cada parte de SOTP carrega um vetor de premissas fixo (não "
            "por cenário) — a checagem existe só para que um nome "
            "inexistente falhe alto, em vez de devolver, em silêncio, os "
            "mesmos números que qualquer outro nome produziria."
        )

    sotp = caso["sotp"]
    moeda = caso["moeda"]
    topo_declarado = sotp["topo"]

    partes = [_compor_parte(parte, moeda) for parte in sotp["partes"]]

    ev_das_partes = sum(p["EV"] for p in partes)

    materialidade_resultado = materialidade(caso, nome_cenario, ev_das_partes)

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
        "cenario": nome_cenario,
        "partes": partes,
        "ev_das_partes": ev_das_partes,
        "materialidade": materialidade_resultado,
        "topo": topo_resultado,
        "ev_total": ev_total,
        "equity": equity_final,
        "preco_acao": preco_acao,
        "ponte_unica": ponte_unica,
    }
