"""Gerador determinístico dos vetores de paridade Python <-> JS (item 4, fatia A).

Este módulo faz duas coisas e nenhuma outra: `gerar()` produz a lista completa
de vetores (bloco patológico escrito à mão + bloco aleatório semeado), e
`avaliar_python()` roda cada vetor no motor congelado (`vendor/multiplos-justos`)
e devolve o valor correspondente. NÃO compara nada contra um espelho — a
comparação é do harness, `tests/test_paridade_js.py` (Task 3 desta fatia) — e
NÃO conhece JavaScript: este arquivo nunca importa nem invoca `node`.

A fixture emitida por `escrever()` é commitada em
`tests/fixtures/vetores_paridade.json`; `test_fixture_commitada_reproduz_o_gerador`
(em `tests/test_vetores_paridade.py`) regenera e compara byte a byte — a
semente cumpre reprodutibilidade sem que ninguém precise confiar nela por fé.
"""
import argparse
import json
import math
import random
import sys
from pathlib import Path

# Path(__file__) é .../skills/er-valuation/scripts/vetores_paridade.py.
# .resolve() torna absoluto; a partir daí, cada índice de .parents sobe um
# nível de diretório: parents[0] = .../skills/er-valuation/scripts (pasta
# deste arquivo), parents[1] = .../skills/er-valuation, parents[2] =
# .../skills, parents[3] = raiz do repo. Mesma contagem de `motor.py`
# (`RAIZ_VENDOR = Path(__file__).resolve().parents[3] / ...`), porque este
# arquivo mora na mesma profundidade. Se ele for movido para outra
# profundidade, o índice tem de mudar junto; o sintoma de esquecer é o
# import de `justos` abaixo falhar alto, na importação deste módulo, em vez
# de intoxicar silenciosamente uma avaliação mais adiante.
_VENDOR_SCRIPTS = Path(__file__).resolve().parents[3] / "vendor" / "multiplos-justos" / "scripts"

# `motor.py` chama o vendor por SUBPROCESSO com PYTHONDONTWRITEBYTECODE=1 no
# ambiente (ver `motor.executar`) exatamente para não sujar a árvore
# congelada com `__pycache__/*.pyc` — um .pyc sombreia o .py no import, e o
# sha256 fixado em `tests/test_vendor_multiplos_justos.py` verifica o
# arquivo-fonte, não o bytecode que o interpretador pode passar a usar. Este
# módulo importa `justos` DENTRO do processo (não por subprocesso, porque
# `avaliar_python` roda centenas de vetores e um subprocesso por vetor seria
# tanto lento quanto o caminho errado para esta task), então a variável de
# ambiente não ajuda aqui — ela só é lida na largada do interpretador, e
# este processo já está de pé. `sys.dont_write_bytecode` é o equivalente em
# runtime: desliga a escrita de .pyc para todo import feito depois desta
# linha, no processo corrente. Sem isto, `test_vendor_sem_bytecode_compilado`
# (`tests/test_vendor_multiplos_justos.py`) e
# `test_rodar_nao_suja_o_vendor_com_bytecode` (`tests/test_valuation_motor.py`)
# reprovam na primeira vez que QUALQUER teste importar este módulo antes deles.
_bytecode_original = sys.dont_write_bytecode
sys.dont_write_bytecode = True
try:
    sys.path.insert(0, str(_VENDOR_SCRIPTS))
    from justos import ev_ebitda, ev_nopat, pe, tv_canon  # noqa: E402
finally:
    sys.dont_write_bytecode = _bytecode_original

SEMENTE = 20260825

_DESPACHO = {"ev_nopat": ev_nopat, "ev_ebitda": ev_ebitda, "pe": pe}


def _vetor(fn: str, **args) -> dict:
    """Um vetor no formato do contrato: `id` nasce placeholder (renumerado no
    fim de `gerar()`, mas fica como a PRIMEIRA chave do dict — a ordem de
    inserção do Python é o que `json.dumps` respeita — para casar com o
    formato documentado `{"id", "fn", "args"}`)."""
    return {"id": 0, "fn": fn, "args": args}


# ---------------------------------------------------------------------------
# Bloco 1: patológico, escrito à mão. Cada seção nomeia o caso da Seção 13 do
# desenho que ela cobre. Toda combinação abaixo foi conferida por chamada
# direta ao vendor antes de entrar aqui (ver task-4a-1-report.md); os
# comentários "NaN"/"finito" documentam o que o motor efetivamente devolve
# HOJE — se um deles virar falso, o vendor mudou e o achado pertence ao
# relatório desta task, não a um ajuste silencioso aqui.
# ---------------------------------------------------------------------------
def _bloco_patologico() -> list[dict]:
    v = []

    # --- 1. custo colado no crescimento (w ~= g / ke ~= g): finito, mas a
    # razão (1+g)/(1+custo) fica perto de 1 em toda parcela — sensível à
    # ORDEM da soma, o tipo de caso que separa um espelho fiel de um que só
    # acerta por acidente nos casos folgados.
    v.append(_vetor("ev_nopat", g=0.06, roic=0.15, w=0.061, n=10, tv="book", roic_book=0.15))
    v.append(_vetor("ev_nopat", g=0.07, roic=0.18, w=0.0705, n=15, tv="convergencia"))
    v.append(_vetor("ev_nopat", g=0.05, roic=0.12, w=0.0505, n=10, tv="gordon", roic_tv=0.08, gp=0.02))
    v.append(_vetor("pe", g=0.06, roe=0.15, ke=0.061, n=10, gde=0.20, nde=0.10, tv="book", roe_book=0.15))
    v.append(_vetor("pe", g=0.05, roe=0.12, ke=0.0505, n=10, gde=0.30, nde=0.10, tv="gordon", roe_tv=0.08, gp=0.02))

    # --- 2. roic <= 0 / roe <= 0 -> NaN (guarda de topo, antes de qualquer
    # ramo de tv).
    v.append(_vetor("ev_nopat", g=0.03, roic=0.0, w=0.09, n=10, tv="book", roic_book=0.10))
    v.append(_vetor("ev_nopat", g=0.02, roic=-0.05, w=0.08, n=8, tv="convergencia"))
    v.append(_vetor("ev_ebitda", g=0.02, roic=-0.02, w=0.08, n=8, d=0.20, t=0.25, tv="gordon", roic_tv=0.10, gp=0.02))
    v.append(_vetor("pe", g=0.03, roe=0.0, ke=0.10, n=10, gde=0.20, nde=0.10, tv="book", roe_book=0.10))
    v.append(_vetor("pe", g=0.02, roe=-0.08, ke=0.09, n=8, gde=0.10, nde=0.05, tv="convergencia"))

    # --- 3. g/roic > 1 (RiR acima de 100%): finito, mas o termo explícito
    # "ret" fica negativo — reinvestimento não autofinanciável.
    v.append(_vetor("ev_nopat", g=0.18, roic=0.10, w=0.09, n=10, tv="book", roic_book=0.10))
    v.append(_vetor("ev_nopat", g=0.25, roic=0.08, w=0.10, n=10, tv="convergencia"))
    v.append(_vetor("pe", g=0.18, roe=0.10, ke=0.11, n=10, gde=0.20, nde=0.10, tv="book", roe_book=0.10))
    v.append(_vetor("pe", g=0.20, roe=0.09, ke=0.10, n=10, gde=0.30, nde=0.10, tv="gordon", roe_tv=0.07, gp=0.02))

    # --- 4. gp >= w / gp >= ke -> NaN, no ramo gordon (igualdade e estrita).
    v.append(_vetor("ev_nopat", g=0.05, roic=0.15, w=0.09, n=10, tv="gordon", roic_tv=0.10, gp=0.09))
    v.append(_vetor("ev_nopat", g=0.05, roic=0.15, w=0.08, n=10, tv="gordon", roic_tv=0.10, gp=0.12))
    v.append(_vetor("pe", g=0.05, roe=0.15, ke=0.11, n=10, gde=0.20, nde=0.10, tv="gordon", roe_tv=0.10, gp=0.11))
    v.append(_vetor("pe", g=0.05, roe=0.15, ke=0.10, n=10, gde=0.30, nde=0.10, tv="gordon", roe_tv=0.09, gp=0.15))

    # --- 5. gp <= -1 -> NaN, no ramo gordon (igualdade e estrita).
    v.append(_vetor("ev_nopat", g=0.05, roic=0.15, w=0.09, n=10, tv="gordon", roic_tv=0.10, gp=-1.2))
    v.append(_vetor("ev_nopat", g=0.05, roic=0.15, w=0.09, n=10, tv="gordon", roic_tv=0.10, gp=-1.0))
    v.append(_vetor("pe", g=0.05, roe=0.15, ke=0.11, n=10, gde=0.20, nde=0.10, tv="gordon", roe_tv=0.10, gp=-1.5))

    # --- 6. horizonte mínimo (n=1, aceito) e abaixo do mínimo (n=0 e
    # negativo, recusados).
    v.append(_vetor("ev_nopat", g=0.05, roic=0.15, w=0.09, n=1, tv="book", roic_book=0.10))
    v.append(_vetor("ev_nopat", g=0.05, roic=0.15, w=0.09, n=0, tv="book", roic_book=0.10))
    v.append(_vetor("ev_nopat", g=0.05, roic=0.15, w=0.09, n=-5, tv="book", roic_book=0.10))
    v.append(_vetor("pe", g=0.05, roe=0.15, ke=0.09, n=1, gde=0.20, nde=0.10, tv="convergencia"))
    v.append(_vetor("pe", g=0.05, roe=0.15, ke=0.09, n=0, gde=0.20, nde=0.10, tv="convergencia"))

    # --- 7. g <= -1 -> NaN (guarda de topo, igualdade e estrita).
    v.append(_vetor("ev_nopat", g=-1.2, roic=0.15, w=0.09, n=10, tv="book", roic_book=0.10))
    v.append(_vetor("ev_nopat", g=-1.0, roic=0.15, w=0.09, n=10, tv="convergencia"))
    v.append(_vetor("pe", g=-1.5, roe=0.15, ke=0.11, n=10, gde=0.20, nde=0.10, tv="book", roe_book=0.10))
    v.append(_vetor("pe", g=-1.0, roe=0.15, ke=0.11, n=10, gde=0.20, nde=0.10, tv="gordon", roe_tv=0.10, gp=0.02))

    # --- 8a. roic_book/roe_book MUITO ABAIXO do marginal: finito, exercita o
    # ramo diferenciado da v9.26/v9.30 (médio != marginal), mas por si só
    # NÃO derruba IC_n/E_n (ver 8b).
    v.append(_vetor("ev_nopat", g=0.05, roic=0.20, w=0.09, n=10, tv="book", roic_book=0.02))
    v.append(_vetor("ev_nopat", g=0.04, roic=0.25, w=0.10, n=15, tv="book", roic_book=0.05))
    v.append(_vetor("pe", g=0.05, roe=0.20, ke=0.11, n=10, gde=0.20, nde=0.10, tv="book", roe_book=0.02))
    v.append(_vetor("pe", g=0.04, roe=0.22, ke=0.10, n=12, gde=0.30, nde=0.10, tv="book", roe_book=0.03))

    # --- 8b. IC_n <= 0 / E_n <= 0 -> NaN, genuinamente. IC_n = (1+g)*(1/rb -
    # 1/marginal) + (1+g)^(n+1)/marginal fatora em (1+g)/rb + (1+g)*[(1+g)^n
    # - 1]/marginal; para g >= 0 o segundo termo nunca é negativo, então o
    # guarda só é alcançável com g NEGATIVO — e precisa de rb ACIMA do
    # marginal (não abaixo) para que o termo negativo domine. Confirmado por
    # chamada direta ao vendor (ver task-4a-1-report.md); contrasta de
    # propósito com o 8a, que sorteia rb abaixo e fica finito.
    v.append(_vetor("ev_nopat", g=-0.60, roic=0.20, w=0.09, n=10, tv="book", roic_book=0.40))
    v.append(_vetor("ev_nopat", g=-0.85, roic=0.10, w=0.08, n=20, tv="book", roic_book=0.30))
    v.append(_vetor("pe", g=-0.60, roe=0.20, ke=0.11, n=10, gde=0.20, nde=0.10, tv="book", roe_book=0.40))
    v.append(_vetor("pe", g=-0.80, roe=0.08, ke=0.09, n=25, gde=0.10, nde=0.05, tv="book", roe_book=0.25))

    # --- 9. roe = ke com caixa/E em 0, 0.20 e 0.50 — sob 'gordon' e
    # 'convergencia' o caixa MOVE o valor (ret ganha +caixa*g/roe no
    # explícito, e o TV do gordon ganha o termo de política); sob 'book' não
    # move nada (ver test_caixa_nao_move_o_book_equity_mas_move_o_gordon).
    v.append(_vetor("pe", g=0.05, roe=0.10, ke=0.10, n=10, gde=0.0, nde=0.0, tv="gordon", roe_tv=0.10, gp=0.03))
    v.append(_vetor("pe", g=0.05, roe=0.10, ke=0.10, n=10, gde=0.30, nde=0.10, tv="gordon", roe_tv=0.10, gp=0.03))
    v.append(_vetor("pe", g=0.05, roe=0.10, ke=0.10, n=10, gde=0.60, nde=0.10, tv="gordon", roe_tv=0.10, gp=0.03))
    v.append(_vetor("pe", g=0.05, roe=0.10, ke=0.10, n=10, gde=0.0, nde=0.0, tv="convergencia"))
    v.append(_vetor("pe", g=0.05, roe=0.10, ke=0.10, n=10, gde=0.30, nde=0.10, tv="convergencia"))
    v.append(_vetor("pe", g=0.05, roe=0.10, ke=0.10, n=10, gde=0.60, nde=0.10, tv="convergencia"))
    v.append(_vetor("pe", g=0.05, roe=0.10, ke=0.10, n=10, gde=0.0, nde=0.0, tv="book", roe_book=0.10))
    v.append(_vetor("pe", g=0.05, roe=0.10, ke=0.10, n=10, gde=0.30, nde=0.10, tv="book", roe_book=0.10))
    v.append(_vetor("pe", g=0.05, roe=0.10, ke=0.10, n=10, gde=0.60, nde=0.10, tv="book", roe_book=0.10))

    # --- 10. roic = w (spread zero, fronteira de neutralidade).
    v.append(_vetor("ev_nopat", g=0.05, roic=0.09, w=0.09, n=10, tv="book", roic_book=0.09))
    v.append(_vetor("ev_nopat", g=0.05, roic=0.09, w=0.09, n=10, tv="convergencia"))
    v.append(_vetor("ev_nopat", g=0.05, roic=0.09, w=0.09, n=10, tv="gordon", roic_tv=0.09, gp=0.02))
    v.append(_vetor("ev_nopat", g=0.0, roic=0.09, w=0.09, n=10, tv="book", roic_book=0.09))

    # --- 11. politica_tv nas duas opções ('continua' é o default C1;
    # 'encerra' é o comportamento pré-correção) — só diverge com caixa != 0
    # e gp != 0 sob 'gordon'.
    v.append(_vetor("pe", g=0.05, roe=0.15, ke=0.11, n=10, gde=0.30, nde=0.10, tv="gordon",
                     roe_tv=0.10, gp=0.03, politica_tv="continua"))
    v.append(_vetor("pe", g=0.05, roe=0.15, ke=0.11, n=10, gde=0.30, nde=0.10, tv="gordon",
                     roe_tv=0.10, gp=0.03, politica_tv="encerra"))
    v.append(_vetor("pe", g=0.05, roe=0.15, ke=0.11, n=10, gde=0.60, nde=0.10, tv="gordon",
                     roe_tv=0.10, gp=0.03, politica_tv="continua"))
    v.append(_vetor("pe", g=0.05, roe=0.15, ke=0.11, n=10, gde=0.60, nde=0.10, tv="gordon",
                     roe_tv=0.10, gp=0.03, politica_tv="encerra"))

    # --- 12. mid_year nos dois lados (multiplica por (1+custo)^0.5 no fim).
    v.append(_vetor("ev_nopat", g=0.05, roic=0.15, w=0.09, n=10, tv="book", roic_book=0.10, mid_year=True))
    v.append(_vetor("ev_nopat", g=0.06, roic=0.11, w=0.10, n=12, tv="gordon", roic_tv=0.09, gp=0.02, mid_year=True))
    v.append(_vetor("ev_ebitda", g=0.05, roic=0.15, w=0.09, n=10, d=0.20, t=0.25, tv="book",
                     roic_book=0.10, mid_year=True))
    v.append(_vetor("pe", g=0.05, roe=0.15, ke=0.11, n=10, gde=0.30, nde=0.10, tv="book",
                     roe_book=0.10, mid_year=True))
    v.append(_vetor("pe", g=0.06, roe=0.14, ke=0.10, n=10, gde=0.20, nde=0.10, tv="convergencia", mid_year=True))
    v.append(_vetor("pe", g=0.05, roe=0.13, ke=0.10, n=10, gde=0.30, nde=0.10, tv="gordon",
                     roe_tv=0.08, gp=0.02, mid_year=True))

    # --- extra: outros guardas do motor, além dos pedidos explicitamente —
    # a fixture desta task não exige cada um por nome, mas o harness de
    # paridade (Task 3) só vale a pena se exercitar todos os guardas, não só
    # os listados na Seção 13.
    v.append(_vetor("ev_nopat", g=0.05, roic=0.15, w=-1.2, n=10, tv="book", roic_book=0.10))  # w <= -1
    v.append(_vetor("ev_nopat", g=0.05, roic=0.15, w=-1.0, n=10, tv="convergencia"))  # w <= -1, igualdade
    v.append(_vetor("pe", g=0.05, roe=0.15, ke=-1.3, n=10, gde=0.20, nde=0.10, tv="book", roe_book=0.10))  # ke<=-1
    v.append(_vetor("pe", g=0.05, roe=0.15, ke=-1.0, n=10, gde=0.20, nde=0.10, tv="gordon",
                     roe_tv=0.10, gp=0.02))  # ke <= -1, igualdade
    v.append(_vetor("ev_nopat", g=0.03, roic=0.12, w=-0.05, n=10, tv="convergencia"))  # guarda w<=0 da convergencia
    v.append(_vetor("ev_nopat", g=0.03, roic=0.12, w=0.0, n=10, tv="convergencia"))  # idem, igualdade
    v.append(_vetor("pe", g=0.03, roe=0.12, ke=-0.03, n=10, gde=0.20, nde=0.10, tv="convergencia"))  # guarda ke<=0
    v.append(_vetor("pe", g=0.03, roe=0.12, ke=0.0, n=10, gde=0.20, nde=0.10, tv="convergencia"))  # idem, igualdade
    v.append(_vetor("ev_nopat", g=0.05, roic=0.15, w=0.09, n=10, tv="gordon", gp=0.03))  # roic_tv ausente
    v.append(_vetor("pe", g=0.05, roe=0.15, ke=0.11, n=10, gde=0.20, nde=0.10, tv="gordon", gp=0.03))  # roe_tv ausente
    v.append(_vetor("ev_nopat", g=0.05, roic=0.15, w=0.09, n=10, tv="book", roic_book=0.0))  # rb <= 0 explícito
    v.append(_vetor("pe", g=0.05, roe=0.15, ke=0.09, n=10, gde=0.20, nde=0.10, tv="book", roe_book=-0.02))  # rb<=0

    # --- casos saudáveis de contraste: nenhuma fixture só de patologia prova
    # que o espelho acerta o caso comum.
    v.append(_vetor("ev_nopat", g=0.04, roic=0.15, w=0.09, n=10, tv="book", roic_book=0.12))
    v.append(_vetor("ev_nopat", g=0.04, roic=0.15, w=0.09, n=10, tv="convergencia"))
    v.append(_vetor("ev_nopat", g=0.04, roic=0.15, w=0.09, n=10, tv="gordon", roic_tv=0.10, gp=0.025))
    v.append(_vetor("ev_ebitda", g=0.04, roic=0.15, w=0.09, n=10, d=0.20, t=0.25, tv="book", roic_book=0.12))
    v.append(_vetor("pe", g=0.04, roe=0.16, ke=0.10, n=10, gde=0.25, nde=0.10, tv="book", roe_book=0.13))
    v.append(_vetor("pe", g=0.04, roe=0.16, ke=0.10, n=10, gde=0.25, nde=0.10, tv="convergencia"))
    v.append(_vetor("pe", g=0.04, roe=0.16, ke=0.10, n=10, gde=0.25, nde=0.10, tv="gordon", roe_tv=0.09, gp=0.025))

    # --- 13. resíduo da 4A — aliases legados de tv_canon ('ic'->'book',
    # 'spread'->'gordon') e tv AUSENTE (cai no default 'book' do motor).
    # Nenhum vetor da fixture batia estes três caminhos antes desta seção.
    # Os aliases fecham uma lacuna real: um alias transposto no espelho
    # ('ic'->'gordon', por exemplo) diverge nestes vetores — provado por
    # mutação (task-4b-1-review.md, item 1: mutante M1 pega, 2 divergências
    # de finitude + 2 numéricas).
    #
    # tv AUSENTE fecha uma lacuna DIFERENTE e mais estreita do que o
    # comentário original desta seção afirmava (retificado pela revisão de
    # 4B.1 — task-4b-1-review.md, achado F1). O que estes dois vetores
    # travam é o VALOR do default do ramo 'else' do motor ('book', não outra
    # coisa — provado por mutação M2, que troca esse default por 'gordon' e
    # o pega). Eles NÃO travam a distinção entre resolver o default por
    # PRESENÇA de chave e resolver por '??' (`args.tv ?? 'book'`): para uma
    # chave AUSENTE as duas resoluções são IDÊNTICAS por construção — só um
    # `tv: null` EXPLÍCITO as separa, e nenhum vetor desta seção usa null
    # (mutante M3, que reintroduz o bug do '??' desta classe no espelho,
    # roda LIMPO sobre a fixture inteira — 0 divergências em 448 vetores,
    # reconfirmado após a Seção 14 abaixo).
    # Essa distinção presença×'??' para `tv` é travada FORA da fixture, por
    # test_paridade_js.py::test_tv_e_politica_tv_null_aliases_e_tv_ausente_fora_da_fixture.
    # A Seção 14 abaixo fecha o mesmo tipo de lacuna DENTRO da fixture, mas
    # para `politica_tv`, não para `tv` (achado F2 da mesma revisão).
    #
    # Reusa DE PROPÓSITO os mesmos parâmetros dos casos saudáveis logo acima
    # (mesmo g/roic-roe/w-ke/n, e mesmo roic_book/roe_book=0.12/0.13 nos
    # dois 'ic') para que o resultado seja comparável por inspeção: 'ic' com
    # roic_book=0.12 tem de bater exatamente o 'book' de mesmo roic_book,
    # dois blocos acima — só o nome da convenção muda. tv ausente reusa
    # g/roic-roe/w-ke/n sem roic_book/roe_book (cai no ramo médio=marginal
    # do 'book', igual a um 'book' explícito sem book informado).
    v.append(_vetor("ev_nopat", g=0.04, roic=0.15, w=0.09, n=10, tv="ic", roic_book=0.12))
    v.append(_vetor("pe", g=0.04, roe=0.16, ke=0.10, n=10, gde=0.25, nde=0.10, tv="ic", roe_book=0.13))
    v.append(_vetor("ev_nopat", g=0.04, roic=0.15, w=0.09, n=10, tv="spread", roic_tv=0.10, gp=0.025))
    v.append(_vetor("pe", g=0.04, roe=0.16, ke=0.10, n=10, gde=0.25, nde=0.10, tv="spread", roe_tv=0.09, gp=0.025))
    v.append(_vetor("ev_nopat", g=0.04, roic=0.15, w=0.09, n=10))  # tv ausente -> default 'book'
    v.append(_vetor("pe", g=0.04, roe=0.16, ke=0.10, n=10, gde=0.25, nde=0.10))  # tv ausente -> default 'book'

    # --- 14. presença×'??' para `politica_tv` — achado F2 da revisão de
    # 4B.1 (task-4b-1-review.md). A fixture não tinha vetor NENHUM cobrindo
    # o defaulting por PRESENÇA de `politica_tv`: só um teste in-memory fora
    # da fixture (test_paridade_js.py::
    # test_tv_e_politica_tv_null_aliases_e_tv_ausente_fora_da_fixture)
    # travava a regressão CRITICAL que a revisão final da 4A corrigiu (um
    # espelho que resolvesse `args.politica_tv ?? 'continua'` trata ausência
    # e null presente do mesmo jeito; o Python só aplica 'continua' na
    # AUSÊNCIA da chave — assinatura de pe() no vendor). `politica_tv` só
    # entra no ramo 'gordon' de pe() (justos.py:246): `ret_tv = (1 -
    # gp/roe_tv) + (caixa*(gp/roe_tv) if politica_tv == 'continua' else
    # 0.0)`, com caixa = gde - nde (justos.py:236). Um `politica_tv=None`
    # explícito não bate a string 'continua' e cai no mesmo ramo que
    # 'encerra' (o termo de caixa SAI); ausente cai no default Python
    # 'continua' (o termo ENTRA). Reusa DE PROPÓSITO os mesmos parâmetros do
    # par 'continua'/'encerra' saudável da Seção 11 (mesmo g/roe/ke/n/gde/
    # nde/roe_tv/gp; caixa=0.20, gp=0.03, caixa*(gp/roe_tv)=0.06 ≠ 0) para
    # que o resultado seja comparável por inspeção: o vetor com
    # `politica_tv` AUSENTE tem que bater EXATAMENTE o 'continua' daquele
    # par, e o vetor com `politica_tv=None` tem que bater EXATAMENTE o
    # 'encerra' daquele par — só o mecanismo de resolução muda, não o ramo
    # final.
    v.append(_vetor("pe", g=0.05, roe=0.15, ke=0.11, n=10, gde=0.30, nde=0.10, tv="gordon",
                     roe_tv=0.10, gp=0.03, politica_tv=None))  # null explícito -> ramo 'else' (== 'encerra')
    v.append(_vetor("pe", g=0.05, roe=0.15, ke=0.11, n=10, gde=0.30, nde=0.10, tv="gordon",
                     roe_tv=0.10, gp=0.03))  # politica_tv ausente -> default Python 'continua'

    return v


# ---------------------------------------------------------------------------
# Bloco 2: aleatório, semeado. As três funções x as três convenções
# terminais, com faixas largas o bastante para produzir tanto casos
# saudáveis quanto degenerados (guardas do motor). `roic_book`/`roe_book`
# nascem de um sorteio INDEPENDENTE do marginal — nunca "marginal + delta" —
# para que médio != marginal apareça com frequência sem viés de construção.
# ---------------------------------------------------------------------------
_POR_COMBINACAO = 40  # 3 funções x 3 convenções x 40 = 360 vetores aleatórios

# Faixas em FRAÇÃO (0.05 = 5%), como as funções internas do motor.
#
# Cada parâmetro sensível a guarda usa um sorteio MISTO: a maior parte dos
# sorteios ("normal") cai numa faixa plausível de negócio de verdade, e uma
# MINORIA declarada ("extrema") cai deliberadamente do lado que aciona
# guarda. A alternativa óbvia — uma única faixa larga cobrindo as duas
# regiões — foi tentada primeiro e falhou: com w sorteado uniformemente em
# (-1.05, 0.30), por exemplo, 78% dos sorteios caíam em w <= 0, e a
# convenção 'convergencia' (que exige w > 0) virava quase só NaN, matando a
# contagem de finitos. Ver task-4a-1-report.md pela primeira medição.
_P_EXTREMA = 0.15  # fração dos sorteios que vai deliberadamente para a cauda degenerada

_FAIXA_G_NORMAL = (-0.05, 0.45)     # crescimento plausível (inclui alto o bastante p/ RiR>100%)
_FAIXA_G_EXTREMA = (-1.30, -0.05)   # cauda negativa: inclui g <= -1 (guarda de topo) e o
                                     # intervalo (-1, -0.05] que alimenta IC_n<=0/E_n<=0 quando
                                     # combinado com roic_book/roe_book ACIMA do marginal

_FAIXA_RETORNO_NORMAL = (0.02, 0.45)   # roic/roe plausível
_FAIXA_RETORNO_EXTREMA = (-0.08, 0.02)  # inclui <= 0 (guarda de topo)

_FAIXA_CUSTO_NORMAL = (0.02, 0.35)     # WACC/Ke plausível
_FAIXA_CUSTO_EXTREMA = (-1.20, 0.02)   # inclui w/ke <= -1 (guarda de topo) E o intervalo
                                        # (-1, 0] que só a 'convergencia' recusa por conta própria

_FAIXA_GP_NORMAL = (-0.02, 0.30)    # gp perpétuo plausível (abaixo do custo típico)
_FAIXA_GP_EXTREMA = (-1.30, -0.02)  # inclui gp <= -1 (guarda do ramo gordon)

_FAIXA_TV_MARGINAL = (-0.05, 0.35)  # roic_tv/roe_tv: inclui <= 0 sem precisar de mistura
                                     # (a fração já é pequena o bastante: 0.05/0.40 = 12.5%)
_FAIXA_BOOK = (-0.05, 0.60)         # roic_book/roe_book, sorteado INDEPENDENTE do marginal
_FAIXA_CAIXA = (0.0, 0.90)          # gde/nde, sorteados independentes entre si
_FAIXA_DT = (-0.10, 0.60)           # d/t do ev_ebitda — sem guarda própria
_N_MIN, _N_MAX = -3, 45             # inclui n < 1 (guarda de topo) numa minoria dos sorteios


def _misto(rng: random.Random, normal: tuple[float, float], extrema: tuple[float, float]) -> float:
    """Sorteio misto: a maioria cai em `normal`, `_P_EXTREMA` cai em `extrema`."""
    faixa = extrema if rng.random() < _P_EXTREMA else normal
    return round(rng.uniform(*faixa), 6)


def _vetor_aleatorio(rng: random.Random, fn: str, tv: str) -> dict:
    g = _misto(rng, _FAIXA_G_NORMAL, _FAIXA_G_EXTREMA)
    n = rng.randint(_N_MIN, _N_MAX)
    mid_year = rng.random() < 0.35

    if fn == "pe":
        roe = _misto(rng, _FAIXA_RETORNO_NORMAL, _FAIXA_RETORNO_EXTREMA)
        ke = _misto(rng, _FAIXA_CUSTO_NORMAL, _FAIXA_CUSTO_EXTREMA)
        gde = round(rng.uniform(*_FAIXA_CAIXA), 6)
        nde = round(rng.uniform(*_FAIXA_CAIXA), 6)
        args = {"g": g, "roe": roe, "ke": ke, "n": n, "gde": gde, "nde": nde, "tv": tv}
        if tv == "gordon":
            args["gp"] = _misto(rng, _FAIXA_GP_NORMAL, _FAIXA_GP_EXTREMA)
            args["roe_tv"] = None if rng.random() < 0.08 else round(rng.uniform(*_FAIXA_TV_MARGINAL), 6)
            args["politica_tv"] = rng.choice(("continua", "encerra"))
        elif tv == "book" and rng.random() >= 0.10:
            # sorteio INDEPENDENTE do marginal (roe) -- nao "roe + delta" --
            # e' isso que faz medio != marginal aparecer sem vies.
            args["roe_book"] = round(rng.uniform(*_FAIXA_BOOK), 6)
        if mid_year:
            args["mid_year"] = True
        return _vetor(fn, **args)

    # lado firm: ev_nopat / ev_ebitda compartilham o mesmo sorteio de base.
    roic = _misto(rng, _FAIXA_RETORNO_NORMAL, _FAIXA_RETORNO_EXTREMA)
    w = _misto(rng, _FAIXA_CUSTO_NORMAL, _FAIXA_CUSTO_EXTREMA)
    args = {"g": g, "roic": roic, "w": w, "n": n, "tv": tv}
    if tv == "gordon":
        args["gp"] = _misto(rng, _FAIXA_GP_NORMAL, _FAIXA_GP_EXTREMA)
        args["roic_tv"] = None if rng.random() < 0.08 else round(rng.uniform(*_FAIXA_TV_MARGINAL), 6)
    elif tv == "book" and rng.random() >= 0.10:
        args["roic_book"] = round(rng.uniform(*_FAIXA_BOOK), 6)
    if mid_year:
        args["mid_year"] = True
    if fn == "ev_ebitda":
        args["d"] = round(rng.uniform(*_FAIXA_DT), 6)
        args["t"] = round(rng.uniform(*_FAIXA_DT), 6)
    return _vetor(fn, **args)


def _bloco_aleatorio(rng: random.Random) -> list[dict]:
    vetores = []
    for fn in ("ev_nopat", "ev_ebitda", "pe"):
        for tv in ("book", "convergencia", "gordon"):
            for _ in range(_POR_COMBINACAO):
                vetores.append(_vetor_aleatorio(rng, fn, tv))
    return vetores


def gerar() -> list[dict]:
    """A lista completa de vetores, determinística.

    `random.Random(SEMENTE)` nasce AQUI DENTRO — uma instância nova a cada
    chamada, nunca uma instância de módulo reaproveitada entre chamadas — o
    que faz `gerar() == gerar()` valer trivialmente e é o que garante que o
    CLI (processo novo) reproduza byte a byte a fixture commitada. Usar o
    `random` global em vez de uma instância própria destruiria isso: o
    global é estado compartilhado do processo, e qualquer outro teste que o
    tocasse (mesmo `random.seed()` de outro módulo, rodando antes deste no
    mesmo processo pytest) mudaria a sequência sorteada aqui.

    Ordem: bloco patológico primeiro (fixo, legível), bloco aleatório depois
    — assim a fixture commitada tem um prefixo estável e revisável por
    inspeção, e o diff de uma mudança no bloco aleatório fica isolado no
    sufixo. `id` sequencial só é atribuído no final, sobre a lista já
    concatenada.
    """
    rng = random.Random(SEMENTE)
    vetores = _bloco_patologico() + _bloco_aleatorio(rng)
    for i, vetor in enumerate(vetores):
        vetor["id"] = i
    return vetores


def avaliar_python(vetores: list[dict]) -> list[float | None]:
    """Avalia cada vetor no motor Python congelado.

    Devolve uma lista paralela de `float | None` — `None` para todo
    resultado não-finito (NaN ou +-inf), o mesmo que o serializador do
    próprio motor faz em `_json_sane` (`vendor/multiplos-justos/scripts/justos.py`).
    JSON não tem NaN; `None` é o que os dois lados (este módulo e, na Task 2,
    `motor_espelho.js`) usam para dizer "o motor recusou este vetor" sem
    inventar um número.

    Não compara nada contra JS — isso é do harness (Task 3). Não sabe que JS
    existe.
    """
    resultados: list[float | None] = []
    for vetor in vetores:
        fn = _DESPACHO[vetor["fn"]]
        valor = fn(**vetor["args"])
        if isinstance(valor, (int, float)) and math.isfinite(valor):
            resultados.append(float(valor))
        else:
            resultados.append(None)
    return resultados


def escrever(vetores: list[dict], destino: Path) -> None:
    """Grava `vetores` como JSON determinístico em `destino`.

    `indent=2` e `ensure_ascii=False` (a fixture fica legível, nenhuma
    sequência `\\uXXXX`); `\n` final e `newline="\n"` desligam a tradução de
    fim de linha do Windows — a mesma lista sempre grava os mesmos bytes,
    seja qual for a plataforma que rodou o gerador. Mesma receita de
    `avaliar.escrever` (`skills/er-valuation/scripts/avaliar.py`).
    """
    texto = json.dumps(vetores, indent=2, ensure_ascii=False) + "\n"
    Path(destino).write_text(texto, encoding="utf-8", newline="\n")


def main(argv: list[str] | None = None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(
        description="Gera a fixture determinística de vetores de paridade Python <-> JS.")
    parser.add_argument("--out", type=Path, required=True, help="caminho do JSON de saída")
    args = parser.parse_args(argv)

    try:
        escrever(gerar(), args.out)
    except OSError as erro:
        print(f"não foi possível gravar '{args.out}': {erro}.", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
