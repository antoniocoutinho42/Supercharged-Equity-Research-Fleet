"""Grades de sensibilidade: 1D e 2D, célula a célula no motor congelado.

Este módulo NÃO faz conta de valuation. Cada célula é uma chamada de
`avaliar.precificar_firm`/`precificar_equity` — a mesma função que
`avaliar()` já usa para ir de um vetor de premissas a preço por ação, com a
mesma escolha de escala (EBITDA direto do motor vs. álgebra do ramo NOPAT)
e a mesma recusa de `null` via `avaliar._exigir_valor`. Nenhum número desta
grade é interpolado, extrapolado ou calculado fora do motor — a metodologia
é literal aqui: a grade é construída chamando o motor célula a célula,
nenhum número fora do motor.

Cada grade declara a configuração do triângulo g = RiR x retorno que ela
assume (`triangulo`, `{"inputs": [...], "output": ...}` — já validada por
`caso.py`, aqui só ecoada) e a métrica de referência sobre a qual o preço
por ação foi construído (`metrica_de_referencia`, `{"tipo", "valor"}` —
espelho de `caso["metrica_base"]`). Sem as duas, a grade não é
reproduzível nem inequívoca: a mesma análise circula legitimamente com
mais de uma métrica-base (EBITDA, NOPAT, LL), e uma tabela de preço sem a
métrica em que foi construída é ambígua por construção.

Decisão D5 do plano (`docs/superpowers/plans/2026-08-21-v4-item3b-reversa-
sensibilidades.md`): o caso declara os PONTOS de cada eixo explicitamente
— `caso.py` já recusa uma grade sem pontos declarados. Este módulo nunca
inventa uma faixa automática.

Decisão D6: diagnóstico por célula sem duplicar prosa. Cada grade carrega
`diagnosticos_unicos` — as strings distintas que o motor emitiu em
QUALQUER célula da grade, na ordem de primeira aparição — e cada célula
carrega `diag`, a lista de índices dela nessa lista. Uma grade 7x7 não
repete a mesma frase do motor 49 vezes; ela aponta para ela. A variável
implícita do triângulo (a que sobra depois dos dois inputs declarados) e
qualquer outra leitura do motor sobre a célula — reinvestimento acima de
100%, spread negativo, crescimento acima da âncora macro — chega junto
nesses diagnósticos: comentada, nunca silenciada.

Sobre `--moeda`: `precificar_firm`/`precificar_equity` aceitam `moeda`
como parâmetro opcional (default `None`, o mesmo de `motor.rodar`); este
módulo passa `caso["moeda"]` em toda célula, de toda grade — mesma
disciplina de `avaliar()` (ver docstring de `avaliar.py`). A omissão era
uma regressão: sem `--moeda`, cada célula carregava o aviso genérico do
motor "MOEDA/REGIME NÃO DECLARADOS" nos diagnósticos — uma grade 7x7
acumulava 49 alarmes falsos, um por célula, num produto cujo objetivo é a
trilha auditável. Passar moeda não muda nenhum número: troca só o aviso
por uma confirmação de âncora macro — a mesma troca que, para o cenário
principal, `test_valuation_avaliar.py` prova em
`test_moeda_do_caso_e_repassada_ao_motor_sem_mudar_numeros`. A mesma
garantia, agora sobre a grade, é o teste de regressão deste módulo:
`test_regressao_sem_alarme_falso_de_moeda_nas_celulas`.

Isso também corrige o contrato do teste
`test_diagnosticos_deduplicados_reconstroem_a_execucao_direta`: ele
reconstrói os diagnósticos de uma célula pelos índices e compara, com
igualdade exata de lista, contra uma chamada direta de `motor.rodar` — a
comparação só bate se essa chamada direta passar a mesma `moeda` que a
célula usa.

Assume, em toda função deste módulo, que `caso` já passou por
`caso.validar` — mesma disciplina de `reversa.py`: a presença e a forma de
`caso["sensibilidades"]` (e de cada `spec` de grade) já foram confirmadas
por `caso.py`; nenhuma função aqui reabre essa checagem.
"""

from typing import Any

from avaliar import precificar_equity, precificar_firm

Caso = dict[str, Any]

# Unidade do campo "valor" de toda célula, 1D e 2D — preço por ação é o que
# `precificar_firm`/`precificar_equity` devolvem em `valor["preco_acao"]`
# nas duas rotas (firm e equity), então a grade nunca varia essa unidade.
_UNIDADE = "preço por ação"


def _precificar_celula(caso: Caso, nd_efetivo: float, premissas: dict) -> tuple[dict, float, float]:
    """Roda uma célula da grade; devolve (saída do motor, preço por ação,
    múltiplo de referência).

    Delega inteiramente a `avaliar.precificar_firm`/`precificar_equity` —
    ver o docstring do módulo para o porquê. Não devolve `EV`/`Equity`/
    `algebra`: a grade não precisa e não expõe esses campos, só o preço
    por ação e o múltiplo de referência da métrica-base.

    Passa `caso["moeda"]` às duas funções de `avaliar.py` — mesma
    disciplina de `avaliar()` (ver docstring do módulo): sem isso, toda
    célula carregaria o alarme falso "MOEDA/REGIME NÃO DECLARADOS".

    Correção do item 3: mesma disciplina para `caso["mercado"]["rf"]`,
    quando o bloco existe — sem ele, toda célula de toda grade carregava
    "PREMISSA NÃO ANCORADA" em vez da âncora macro do gp (Damodaran), num
    cenário `gordon` com `gp > 0`. `mercado` é bloco opcional (`caso.py`),
    diferente de `moeda`; leitura condicional, mesma de `avaliar.avaliar()`.
    """
    rota = caso["rota"]
    acoes = caso["acoes_diluidas"]
    metrica = caso["metrica_base"]
    moeda = caso["moeda"]
    mercado = caso.get("mercado")
    rf = mercado.get("rf") if mercado else None

    if rota == "firm":
        saida, valor, _algebra, multiplo = precificar_firm(
            premissas, metrica["tipo"], metrica["valor"], nd_efetivo, acoes, moeda, rf=rf)
    else:  # equity
        saida, valor, _algebra, multiplo = precificar_equity(
            premissas, metrica["valor"], acoes, moeda, rf=rf)

    return saida, valor["preco_acao"], multiplo


def _indices_diagnosticos(diagnosticos_unicos: list[str], diagnosticos: list[str]) -> list[int]:
    """Devolve o índice, em `diagnosticos_unicos`, de cada string de
    `diagnosticos` — acrescentando a `diagnosticos_unicos`, em lugar e na
    ordem de primeira aparição, qualquer string ainda não vista.

    `diagnosticos_unicos` é o acumulador de UMA grade inteira —
    compartilhado por toda célula de `grade_1d`, ou toda célula de
    `grade_2d` (linha a linha, sem reiniciar entre linhas) — nunca por
    célula isolada. É o que evita repetir a mesma frase do motor dezenas
    de vezes num grid 7x7 (decisão D6 do plano da fatia B).
    """
    indices = []
    for diagnostico in diagnosticos:
        if diagnostico not in diagnosticos_unicos:
            diagnosticos_unicos.append(diagnostico)
        indices.append(diagnosticos_unicos.index(diagnostico))
    return indices


def grade_1d(caso: Caso, nome_cenario: str, spec: dict, nd_efetivo: float) -> dict:
    """Varia uma premissa ao longo dos pontos declarados, célula a célula.

    Cada ponto substitui só a premissa do eixo (`spec["premissa"]`) no
    vetor central de premissas do cenário `nome_cenario` — todo o resto do
    vetor fica exatamente como o caso declarou. Quando `spec["pontos"]`
    inclui o valor que o cenário-base já usa para essa premissa, aquela
    célula reproduz o caso-base por construção: mesmo vetor de premissas,
    mesma chamada ao motor — nunca uma coincidência numérica.

    `spec` é uma entrada de `caso["sensibilidades"]["grades_1d"]` —
    `{"premissa": str, "pontos": [float, ...], "triangulo": {"inputs":
    [...], "output": ...}}` — assumida já validada por `caso.py` (ver
    docstring do módulo).
    """
    metrica = caso["metrica_base"]
    premissas_centrais = caso["cenarios"][nome_cenario]["premissas"]
    premissa = spec["premissa"]

    diagnosticos_unicos: list[str] = []
    pontos = []
    for x in spec["pontos"]:
        premissas = {**premissas_centrais, premissa: x}
        saida, preco_acao, multiplo = _precificar_celula(caso, nd_efetivo, premissas)
        diag = _indices_diagnosticos(diagnosticos_unicos, saida["diagnosticos"])
        pontos.append({"x": x, "valor": preco_acao, "multiplo": multiplo, "diag": diag})

    return {
        "premissa": premissa,
        "triangulo": spec["triangulo"],
        "metrica_de_referencia": {"tipo": metrica["tipo"], "valor": metrica["valor"]},
        "unidade": _UNIDADE,
        "diagnosticos_unicos": diagnosticos_unicos,
        "pontos": pontos,
    }


def grade_2d(caso: Caso, nome_cenario: str, spec: dict, nd_efetivo: float) -> dict:
    """Varia duas premissas num plano (linhas x colunas), célula a célula.

    `celulas[i][j]` corresponde a `(pontos_y[i], pontos_x[j])`: uma linha
    por valor de `pontos_y`, uma coluna por valor de `pontos_x`. Os dois
    eixos substituem premissas DIFERENTES do vetor central (`caso.py` já
    recusa `premissa_x == premissa_y`); todo o resto do vetor fica como o
    caso declarou — mesma disciplina de `grade_1d`.

    `diagnosticos_unicos` é um único acumulador para a grade inteira: as
    linhas não reiniciam a lista entre si, do contrário a mesma frase do
    motor picotaria em índices diferentes conforme a linha.

    `spec` é uma entrada de `caso["sensibilidades"]["grades_2d"]` —
    `{"premissa_x": str, "pontos_x": [float, ...], "premissa_y": str,
    "pontos_y": [float, ...], "triangulo": {...}}` — assumida já validada
    por `caso.py`.
    """
    metrica = caso["metrica_base"]
    premissas_centrais = caso["cenarios"][nome_cenario]["premissas"]
    premissa_x = spec["premissa_x"]
    premissa_y = spec["premissa_y"]

    diagnosticos_unicos: list[str] = []
    celulas = []
    for y in spec["pontos_y"]:
        linha = []
        for x in spec["pontos_x"]:
            premissas = {**premissas_centrais, premissa_x: x, premissa_y: y}
            saida, preco_acao, multiplo = _precificar_celula(caso, nd_efetivo, premissas)
            diag = _indices_diagnosticos(diagnosticos_unicos, saida["diagnosticos"])
            linha.append({"x": x, "y": y, "valor": preco_acao, "multiplo": multiplo, "diag": diag})
        celulas.append(linha)

    return {
        "premissa_x": premissa_x,
        "premissa_y": premissa_y,
        "triangulo": spec["triangulo"],
        "metrica_de_referencia": {"tipo": metrica["tipo"], "valor": metrica["valor"]},
        "unidade": _UNIDADE,
        "diagnosticos_unicos": diagnosticos_unicos,
        "pontos_x": spec["pontos_x"],
        "pontos_y": spec["pontos_y"],
        "celulas": celulas,
    }


def calcular(caso: Caso, nome_cenario: str, nd_efetivo: float) -> dict:
    """Roda toda grade declarada em `caso["sensibilidades"]`, 1D e 2D.

    `nome_cenario` chega como parâmetro explícito — mesmo padrão de
    `reversa.reverter` — em vez de ser lido de
    `caso["sensibilidades"]["cenario"]` aqui dentro; é `avaliar.py` (Task
    5) quem faz essa leitura e repassa.

    `grades_1d`/`grades_2d`, quando ausentes de `caso["sensibilidades"]`,
    viram lista vazia — a metodologia não exige as duas formas na mesma
    rodada, e a ausência de uma não é erro.
    """
    sensibilidades = caso["sensibilidades"]
    grades_1d = [grade_1d(caso, nome_cenario, spec, nd_efetivo)
                 for spec in sensibilidades.get("grades_1d") or []]
    grades_2d = [grade_2d(caso, nome_cenario, spec, nd_efetivo)
                 for spec in sensibilidades.get("grades_2d") or []]
    return {"grades_1d": grades_1d, "grades_2d": grades_2d}
