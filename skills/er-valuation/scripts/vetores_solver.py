"""Gerador determinístico dos problemas de solver e de wrapper Python <-> JS
(item 4, fatia B, tasks 2 e 3).

Mesmo contrato de forma que `vetores_paridade.py` (fatia A), aplicado a uma
natureza de risco diferente: lá o espelho é forma fechada (uma diferença de
1e-15 permanece 1e-15); o solver aqui é ITERATIVO e AMPLIFICA. Este módulo
faz duas coisas e nenhuma outra: `gerar()` produz a lista de problemas (por
tipo — ver abaixo), e `avaliar_python()` despacha cada problema, por
`problema["tipo"]`, para o lado Python correspondente. NÃO compara nada
contra um espelho — a comparação é dos harnesses
(`tests/test_paridade_solver_js.py`, `tests/test_paridade_wrapper_js.py`) —
e NÃO conhece JavaScript: este arquivo nunca importa nem invoca `node`.

Dois `tipo`s, duas fontes de verdade Python — a razão de existirem dois
harnesses de teste separados para uma fixture só:

- `tipo: "solver"` (task 2): roda `solve`/`solve_full`/`identificacao` do
  motor CONGELADO (`vendor/multiplos-justos/scripts/justos.py`, linhas
  272-347) diretamente — a mesma função interna, em fração, sem passar pela
  CLI.
- `tipo: "alvo"|"grade1d"|"grade2d"` (task 3): roda `reversa.alvo_de_mercado`
  e `sensibilidades.grade_1d`/`grade_2d` — o WRAPPER, não o motor. Estas três
  funções chamam o motor por SUBPROCESSO (`motor.rodar`), que atravessa a CLI
  dele — e a CLI converte premissa de ponto percentual (`g: 5.0` = 5%,
  convenção de `caso.json`) para fração antes de chamar `ev_nopat`/`pe`
  (`pc = lambda x: x/100.0`, justos.py) e arredonda cada múltiplo/preço antes
  de devolver o JSON (`round(mn,4)`, `round(preco_acao,2)`, mesmo arquivo). Um
  espelho fiel ao motor mas cego a essas duas conversões da CLI produziria
  números errados por ~100x (unidade) ou por ULPs de rounding no lugar errado
  — exatamente o "número certo no lugar errado" que o docstring de
  `tests/test_paridade_wrapper_js.py` descreve.

A fixture emitida por `escrever()` é commitada em
`tests/fixtures/vetores_solver.json`; os dois harnesses regeneram e comparam
byte a byte, mesma disciplina da 4A. Os problemas de wrapper são acrescentados
DEPOIS dos 41 de solver (nunca intercalados) — `avaliar_python`, chamado sem
filtro pelo harness de solver (que não conhece `tipo` além de "solver"),
devolve um resultado por item também para os tipos de wrapper, cada um com os
três campos do shape do solver (`raizes`, `tangenciais`, `identificacao`)
preenchidos vazios/`None` — nunca ausentes — para que aquele harness, que lê
a fixture inteira sem filtrar por tipo, continue funcionando sem edição (ver
`_CAMPOS_SOLVER_VAZIOS` abaixo e o relatório da task 3).

Formato de um problema de solver (contrato do brief task-4b-2, seção
"Interfaces"):
    {"id": int, "tipo": "solver", "resolver": "<nome da premissa>",
     "fn": "ev_nopat"|"ev_ebitda"|"pe", "args": {...}, "alvo": float,
     "lo": float, "hi": float, "steps": 800, "completo": bool}
`args` traz o vetor SEM a premissa que está sendo resolvida — o solver a
injeta sob a chave `resolver` (`fn(**{**args, resolver: x})`), o mesmo jeito
que o subcomando `rev` do vendor monta `f` (justos.py, bloco do cmd 'rev':
`def f(x): ... return base_f(gg, rr, kk, a.n, kk2) - M`).

Formato de um problema de wrapper (contrato do brief task-4b-3, seção
"Interfaces"; `args` em snake_case — é JSON compartilhado com o Python, a
convenção camelCase fica só dentro do espelho JS):
    {"id": int, "tipo": "alvo",
     "args": {"rota": "firm"|"equity", "preco": float, "acoes": float,
              "nd_efetivo": float, "metrica": {"tipo": str, "valor": float}}}
    {"id": int, "tipo": "grade1d",
     "args": {"rota": ..., "premissas": {...}, "metrica": {...},
              "nd_efetivo": float, "acoes": float, "premissa": str,
              "pontos": [float, ...], "moeda": str}}
    {"id": int, "tipo": "grade2d",
     "args": {"rota": ..., "premissas": {...}, "metrica": {...},
              "nd_efetivo": float, "acoes": float,
              "premissa_x": str, "pontos_x": [float, ...],
              "premissa_y": str, "pontos_y": [float, ...], "moeda": str}}
`premissas` (grade1d/grade2d) está em PONTOS PERCENTUAIS — a mesma convenção
de `caso.json` (ver `tests/fixtures/caso_reversa_firm.json`: `g: 5.0` = 5%) —
não em fração: é o vetor central do cenário, tal como `sensibilidades.py` o
recebe de `caso["cenarios"][nome]["premissas"]`.
"""
import argparse
import json
import random
import sys
from pathlib import Path

# Mesma contagem de parents que vetores_paridade.py: este arquivo mora na
# mesma profundidade (.../skills/er-valuation/scripts/vetores_solver.py).
_VENDOR_SCRIPTS = Path(__file__).resolve().parents[3] / "vendor" / "multiplos-justos" / "scripts"

# `sys.dont_write_bytecode = True` ANTES do import: um .pyc dentro da árvore
# congelada do vendor sombreia o .py no import seguinte e derruba
# `test_vendor_sem_bytecode_compilado`/`test_rodar_nao_suja_o_vendor_com_bytecode`
# na primeira vez que qualquer teste importar este módulo antes deles (ver o
# comentário mais longo em vetores_paridade.py, que explica por que a
# variável de ambiente PYTHONDONTWRITEBYTECODE não ajuda aqui — importamos
# DENTRO do processo, não por subprocesso).
_bytecode_original = sys.dont_write_bytecode
sys.dont_write_bytecode = True
try:
    sys.path.insert(0, str(_VENDOR_SCRIPTS))
    from justos import ev_ebitda, ev_nopat, identificacao, pe, solve, solve_full  # noqa: E402
finally:
    sys.dont_write_bytecode = _bytecode_original

# Task 3: `reversa.py`/`sensibilidades.py` são módulos IRMÃOS deste arquivo
# (mesma pasta, `skills/er-valuation/scripts/`) — já alcançáveis pelo
# `sys.path.insert` que os dois harnesses de teste fazem antes de importar
# `vetores_solver` (ver `tests/test_paridade_wrapper_js.py`). Nenhuma dança de
# bytecode aqui: os dois só chamam o motor por SUBPROCESSO (`motor.rodar`),
# nunca por import — `motor.executar` já protege `vendor/` com
# `PYTHONDONTWRITEBYTECODE=1` no ambiente do subprocesso.
from reversa import alvo_de_mercado  # noqa: E402
from sensibilidades import grade_1d, grade_2d  # noqa: E402

# [item 4, fatia C, task 1] `avaliar.precificar_rampa` e `motor.MotorFalhou` — mesma razao de
# reversa/sensibilidades acima: modulos IRMAOS (skills/er-valuation/scripts/), ja alcancaveis pelo
# mesmo sys.path.insert que os dois harnesses de teste fazem, e que so chamam o motor congelado por
# SUBPROCESSO (avaliar.precificar_rampa -> motor.rodar -> subprocess), nunca por import — nenhuma
# dança de bytecode aqui tambem.
from avaliar import precificar_rampa  # noqa: E402
from motor import MotorFalhou, rodar  # noqa: E402

# [item 4, fatia C, task 2] `rodar` (motor.py) e' o MESMO import que precificar_firm/
# precificar_equity usam por baixo dos panos (avaliar.py: `from motor import ... rodar`) — os
# problemas "diag" chamam `rodar` DIRETO (sem escala, so' para ler `diagnosticos`) porque nao ha'
# ponte de preco para testar aqui, so' a lista de mensagens que o motor devolve; e' AINDA o
# caminho do wrapper (mesmo argv_para, mesmo subprocesso, mesmo colapso null->ausencia), nunca
# diag_firm/diag_eq importados direto — ver `_avaliar_diag` abaixo.

# [Fatia D, Task 2] `avaliar` (a FUNCAO de topo, apelidada `avaliar_caso` para nao colidir com o
# NOME deste modulo — `avaliar.py`, ja importado acima por simbolo) — os problemas "degrau" montam
# um `caso` MINIMO (uma rota equity, um cenario, um bloco `degrau`) e chamam `avaliar_caso` de
# verdade, o MESMO ponto de entrada que `tests/test_valuation_degrau.py` (Task 1) usa para o seu
# proprio teste-ancora — nao uma chamada as pecas internas (`precificar_degrau`,
# `_aplicar_degrau_ao_cenario`) isolada: e' o jeito mais fiel de obter, num so' lugar, as DUAS
# pernas que o wrapper roda por cenario (a rota P/L — `sem_degrau` — e o handler `degrau`) sem
# reimplementar a composicao que `avaliar()` ja faz. Ver `_avaliar_degrau` abaixo.
from avaliar import avaliar as avaliar_caso  # noqa: E402

# [5F, Task 3] `precificar_firm` com as flags da conservação de capital e o bloco que `avaliar()` publica
# (`_conservacao_publicada`) — o WRAPPER, pela mesma razão dos imports acima. Ver `_avaliar_conservacao`.
from avaliar import _conservacao_publicada, precificar_firm  # noqa: E402

SEMENTE_SOLVER = 20260826

_DESPACHO = {"ev_nopat": ev_nopat, "ev_ebitda": ev_ebitda, "pe": pe}

# tol=0.01 é o default do vendor (`identificacao(mult_fn, x, M, tol=0.01)`) e
# também o que o subcomando `rev` da CLI usa sempre que `--tol` não é
# declarado (`tol = (a.tol or 1.0) / 100.0`, justos.py). Este módulo não
# expõe `tol` como campo do problema — nenhum consumidor desta fixture
# precisa de outro valor, e inventar o campo só para nunca variá-lo seria
# complexidade sem uso (calibragem do brief).
_TOL_IDENTIFICACAO = 0.01

# [item 4, fatia C, task 1] Mesma lista/ordem de `CAMPOS_RAMPA`/`AVISOS_RAMPA` em
# motor_espelho.js e em tests/test_paridade_wrapper_js.py — os tres lados tem de concordar,
# porque os harnesses comparam os dois primeiros contra o terceiro (ver o comentario junto de
# `CAMPOS_RAMPA` em motor_espelho.js). `rir_fase1_%` sai SEM a chave 'nota' (texto estatico) —
# ver `_avaliar_rampa` abaixo.
CAMPOS_RAMPA: tuple = ("g1_%", "d_trajetoria_fase1_%", "d2_fase2_%", "rir_fase1_%", "alfa", "beta",
                       "rir2_%", "roic2_%", "vp_fase1", "valor_fase2_no_ano_T", "capacidade_receita")
# [item 4, fatia C, task 2] 'aviso_gp' acrescentado ao final — decidido no HANDLER `rampa`
# (justos.py ~1954), nao em rampa_bifasica; ver o comentario em motor_espelho.js junto do mesmo
# array para a razao e para o achado sobre o alias 'spread' (discrepancia do plano, reportada na
# task).
AVISOS_RAMPA: tuple = ("aviso_colheita", "aviso_delator", "aviso_gp")


def _problema(resolver: str, fn: str, args: dict, alvo: float, lo: float, hi: float,
              steps: int = 800, completo: bool = False) -> dict:
    """Um problema no formato do contrato. `id` nasce placeholder (renumerado
    no fim de `gerar()`) mas fica como PRIMEIRA chave — mesma disciplina de
    `_vetor()` em vetores_paridade.py, para que a ordem de inserção do Python
    (que `json.dumps` respeita) case com a ordem documentada no brief."""
    return {"id": 0, "tipo": "solver", "resolver": resolver, "fn": fn, "args": args,
            "alvo": alvo, "lo": lo, "hi": hi, "steps": steps, "completo": completo}


# ---------------------------------------------------------------------------
# Bloco 1: patológico, escrito à mão. Cada caso foi conferido por chamada
# direta ao vendor antes de entrar aqui (mesma disciplina de
# vetores_paridade.py) — os comentários documentam o que foi medido, não uma
# expectativa não verificada. Ver task-4b-2-report.md para o roteiro de
# exploração completo.
# ---------------------------------------------------------------------------
def _bloco_patologico() -> list[dict]:
    v = []

    # --- 1. alvo ABAIXO do mínimo atingível -> sem raiz. `ev_nopat(roic=x,
    # g=0.05, w=0.09, n=10, tv='book')` (roic_book ausente, roic_book segue o
    # marginal) é MONOTÔNICA DECRESCENTE em roic no domínio (0.005, 1.50] —
    # verificado por varredura direta: máximo ~14.44 em roic~0.05, mínimo
    # 8.397 em roic=1.50. alvo=5.0 fica abaixo do mínimo do domínio inteiro,
    # então nenhuma mudança de sinal é possível.
    v.append(_problema("roic", "ev_nopat", dict(g=0.05, w=0.09, n=10, tv="book"),
                        alvo=5.0, lo=0.005, hi=1.50))

    # --- 2. mesma função, alvo no INTERIOR do range (entre 8.397 e 14.44) ->
    # raiz única (a função é monotônica, então UMA mudança de sinal).
    v.append(_problema("roic", "ev_nopat", dict(g=0.05, w=0.09, n=10, tv="book"),
                        alvo=10.0, lo=0.005, hi=1.50))

    # --- 3/4/6. MULTI-RAIZ: sob 'book' com roic_book MUITO ACIMA do marginal
    # (conflação invertida), ev_nopat(g=x, ...) tem um MÁXIMO INTERIOR em
    # g≈0.08701 (valor≈8.0562) — verificado por busca ternária direta contra
    # o vendor. Com alvo=8.0 (abaixo do pico, acima dos dois extremos do
    # range: y(0.0)≈? < 8.0 e y(0.30)=5.761 < 8.0), a função cruza 8.0 DUAS
    # VEZES: subindo (raiz≈0.041050) e descendo (raiz≈0.128587). Esta é a
    # única fonte de multi-raiz encontrada nesta exploração: resolver 'roic'
    # sozinho (bloco 1) e resolver 'g'/'roic' sob 'gordon' (bloco 8) saem
    # monotônicos no range plausível — só a INTERAÇÃO entre o termo
    # explícito (hump em g, por construção: (1-g/roic)*(1+g)^t) e o termo
    # IC_n com book "invertido" (rb >> roic marginal) produz o máximo
    # interior. #3 roda pela varredura pura (`completo=False`); #4 roda o
    # MESMO problema por `solve_full` (`completo=True`) — as raízes devem
    # bater EXATAMENTE entre #3 e #4 (mesma varredura, só ganha a busca de
    # tangenciais, que aqui deve devolver vazio: são cruzamentos de sinal
    # genuínos, não toques).
    _args_hump = dict(roic=0.08, w=0.09, n=12, tv="book", roic_book=0.50)
    v.append(_problema("g", "ev_nopat", _args_hump, alvo=8.0, lo=0.0, hi=0.30, completo=False))
    v.append(_problema("g", "ev_nopat", _args_hump, alvo=8.0, lo=0.0, hi=0.30, completo=True))

    # --- 5. TANGENCIAL: mesmo hump, alvo LOGO ACIMA do pico
    # (8.05617032431971 * (1+1e-5) = 8.056250886022955) — a função NUNCA
    # alcança o alvo (0 raízes), mas o mínimo de |f| no pico fica bem dentro
    # da tolerância de aceitação (tang_rel=1e-4 relativo ao alvo): residuo
    # medido ≈ -8.056e-5, ~10x dentro do limiar de 8.056e-4. Margem
    # deliberadamente folgada (não right-at-the-edge) para que o
    # aceita/rejeita binário do candidato tangencial não vire uma segunda
    # fonte de divergência de CONTAGEM por causa de ULPs entre os dois lados
    # — exatamente o risco que este brief pede para tratar com rigor.
    v.append(_problema("g", "ev_nopat", _args_hump, alvo=8.056250886022955,
                        lo=0.0, hi=0.30, completo=True))

    # --- 6. lo/hi ESTREITO: mesmo hump, janela [0.02, 0.15] -- cerca de 5x
    # mais estreita que o [0.0, 0.30] dos casos acima -- ainda embrulhando as
    # duas raízes de alvo=8.0 (0.041050 e 0.128587) com folga de só ~0.02 de
    # cada lado. `curvatura_d2M_dx2` medida nas duas raízes (-42.9 e -78.4,
    # via `identificacao`) é grande o bastante para que 800 passos nesta
    # janela estreita sejam a varredura mais "grossa relativamente à
    # curvatura" que esta exploração conseguiu produzir sem inventar uma
    # função sintética alheia ao motor (ver task-4b-2-report.md: tentativas
    # de afiar ainda mais o pico via n maior empurraram o pico PARA a
    # fronteira NaN em vez de afiá-lo no interior).
    v.append(_problema("g", "ev_nopat", _args_hump, alvo=8.0, lo=0.02, hi=0.15, completo=True))

    # --- 7/8/9. resolver 'w' nas três convenções terminais (firm).
    v.append(_problema("w", "ev_nopat", dict(g=0.04, roic=0.15, n=10, tv="book", roic_book=0.12),
                        alvo=10.0, lo=0.02, hi=0.35))
    v.append(_problema("w", "ev_nopat", dict(g=0.04, roic=0.15, n=10, tv="convergencia"),
                        alvo=10.0, lo=0.02, hi=0.35))
    v.append(_problema("w", "ev_nopat", dict(g=0.04, roic=0.15, n=10, tv="gordon", roic_tv=0.10, gp=0.02),
                        alvo=10.0, lo=0.03, hi=0.35))

    # --- 10/11/12. resolver 'roic' nas três convenções terminais (firm).
    v.append(_problema("roic", "ev_nopat", dict(g=0.04, w=0.09, n=10, tv="book", roic_book=0.12),
                        alvo=10.0, lo=0.02, hi=0.60))
    v.append(_problema("roic", "ev_nopat", dict(g=0.04, w=0.09, n=10, tv="convergencia"),
                        alvo=10.0, lo=0.02, hi=0.60))
    v.append(_problema("roic", "ev_nopat", dict(g=0.04, w=0.09, n=10, tv="gordon", roic_tv=0.10, gp=0.02),
                        alvo=10.0, lo=0.02, hi=0.60))

    # --- 13/14/15. resolver 'ke' nas três convenções terminais (equity).
    v.append(_problema("ke", "pe", dict(g=0.04, roe=0.16, n=10, gde=0.25, nde=0.10, tv="book", roe_book=0.13),
                        alvo=8.0, lo=0.02, hi=0.35))
    v.append(_problema("ke", "pe", dict(g=0.04, roe=0.16, n=10, gde=0.25, nde=0.10, tv="convergencia"),
                        alvo=8.0, lo=0.02, hi=0.35))
    v.append(_problema("ke", "pe", dict(g=0.04, roe=0.16, n=10, gde=0.25, nde=0.10, tv="gordon",
                                        roe_tv=0.09, gp=0.025),
                        alvo=8.0, lo=0.03, hi=0.35))

    # --- 16/17/18. resolver 'roe' nas três convenções terminais (equity).
    v.append(_problema("roe", "pe", dict(g=0.04, ke=0.10, n=10, gde=0.25, nde=0.10, tv="book", roe_book=0.13),
                        alvo=8.0, lo=0.02, hi=0.60))
    v.append(_problema("roe", "pe", dict(g=0.04, ke=0.10, n=10, gde=0.25, nde=0.10, tv="convergencia"),
                        alvo=8.0, lo=0.02, hi=0.60))
    v.append(_problema("roe", "pe", dict(g=0.04, ke=0.10, n=10, gde=0.25, nde=0.10, tv="gordon",
                                         roe_tv=0.09, gp=0.025),
                        alvo=8.0, lo=0.02, hi=0.60))

    # --- 19/20. NEUTRALIDADE (rentabilidade ≈ custo): alvo fixado no valor
    # EXATO da função em roic=w (resp. roe=ke), então a raiz encontrada cai
    # em cima do próprio custo de capital — a região que `diag_firm`/`diag_eq`
    # chamam de identidade de neutralidade. Verificado: identificação sai
    # 'moderada' nos dois (não 'fraca' como o título do brief sugere em
    # prosa, mas o MESMO fenômeno qualitativo — largura relativa de ~14% do
    # alvo ±1%, bem mais larga que os casos 'forte' de ~5% dos blocos
    # 7-18). alvo=11.444444444444445 = ev_nopat(roic=w=0.09, g=0.03, w=0.09,
    # n=10, tv='book', roic_book=0.09) = pe(roe=ke=0.09, mesmos g/n, tv book,
    # caixa 0.20-0.10=0.10) -- coincide numericamente entre as duas por
    # construção deliberada (mesmos g/n/custo/tv/book, e a convenção book é
    # invariante a caixa).
    v.append(_problema("roic", "ev_nopat", dict(g=0.03, w=0.09, n=10, tv="book", roic_book=0.09),
                        alvo=11.444444444444445, lo=0.03, hi=0.30))
    v.append(_problema("roe", "pe", dict(g=0.03, ke=0.09, n=10, gde=0.20, nde=0.10, tv="book", roe_book=0.09),
                        alvo=11.444444444444445, lo=0.03, hi=0.30))

    # --- 21. ev_ebitda: smoke de despacho (a função é ev_nopat*(1-d)*(1-t),
    # não introduz nenhuma dinâmica de raiz nova — o ponto aqui é só provar
    # que `fn: "ev_ebitda"` despacha certo dos dois lados). Reusa os mesmos
    # g/w/n/tv/roic_book do bloco 10 (resolver_roic_book) com alvo escalado
    # por (1-d)*(1-t)=0.6 (10.0*0.6=6.0): a raiz tem de bater a mesma
    # localização (~0.0693).
    v.append(_problema("roic", "ev_ebitda",
                        dict(g=0.04, w=0.09, n=10, tv="book", roic_book=0.12, d=0.20, t=0.25),
                        alvo=6.0, lo=0.02, hi=0.60))

    # --- 22. DEDUPE (revisão final 4B, achado F5): raiz EXATAMENTE sobre um ponto da
    # varredura. `_dedupe_roots`/`dedupeRaizes` está correto por leitura mas nunca disparava
    # nesta fixture — 36 raízes entravam, 36 saíam (review-4b-final.md) — porque nenhum caso
    # tinha uma raiz colidindo com um ponto da grade. `g=0` é deliberado, não decoração: com
    # g=0, `ret=1-g/roic=1` e `(1+g)**t=1` em toda parte, então ev_nopat(roic=x, g=0, w, n,
    # tv='book') colapsa para uma CONSTANTE (a soma explícita, que não depende de roic) mais
    # `1/(roic*(1+w)**n)` — monotônica em roic por construção, SEM nenhum `roic**t`/`(1+g)**t`
    # no caminho, e com (1+w)**n o ÚNICO `**` que sobra (base/expoente "limpos": w=0.25, n
    # inteiro). Isso importa porque `**`/pow() NÃO é bit-a-bit garantido entre V8 e CPython
    # (achado tangencial já registrado no ledger desta task, ver _LO_HI_POR_RESOLVER acima) —
    # a primeira tentativa desta construção (g=0.05, w=0.09) tinha exatamente essa divergência
    # de 1 ULP entre os dois lados, o que fazia SÓ UM dos dois brackets adjacentes enxergar
    # troca de sinal (o outro via os dois extremos com o MESMO sinal) e o dedupe nunca chegava
    # a ver 2 raízes cruas do lado JS — verificado por chamada direta antes de descartar.
    # Com g=0 os dois lados batem BIT A BIT: alvo = ev_nopat(roic=0.30, ...) calculado no
    # próprio ponto x_5 da varredura (lo=0.05, hi=0.55, steps=10) faz f(x_5) = 0.0 EXATO nos
    # dois lados. Verificado por chamada direta ao vendor: a varredura BRUTA (sem dedupe) acha
    # 2 raízes — 0.2999999999999997 (bracket [x_4,x_5], que nunca atualiza `fa` porque ela
    # começa positiva e só o lado direito zera) e 0.30000000000000004 (bracket [x_5,x_6], que
    # ATUALIZA fa=0 no primeiro passo e nunca sai de 0) — e `_dedupe_roots` colapsa as duas em
    # [0.2999999999999997]. Espelho JS conferido pelo MESMO caminho (evNopat/dedupeRaizes
    # exportados): raízes cruas idênticas, dedupe idêntico, `resolverProblema` devolve
    # 0.2999999999999997 — bit a bit igual ao Python. Sem este caso, remover qualquer um dos
    # dois dedupes do espelho (ou trocar `y0*y1<=0` por `<0`, que é exatamente o que faz as
    # duas raízes desta construção desaparecerem: produto = 0 deixa de satisfazer `<0`) não
    # derrubava teste nenhum.
    v.append(_problema("roic", "ev_nopat", dict(g=0.0, w=0.25, n=10, tv="book"),
                        alvo=3.9284172117333336, lo=0.05, hi=0.55, steps=10, completo=False))

    return v


# ---------------------------------------------------------------------------
# Bloco 2: aleatório, semeado — lastro, não o discriminador principal (esse
# é o bloco patológico acima). Faixas simples e "normais" (sem a mistura
# normal/extrema de vetores_paridade.py): o objetivo aqui não é forçar
# guardas do motor, é variar fn x resolver x tv com parâmetros plausíveis
# para complementar o bloco patológico com volume pequeno.
# ---------------------------------------------------------------------------
_TAMANHO_BLOCO_ALEATORIO = 20

_FAIXA_G = (-0.05, 0.35)
_FAIXA_RETORNO = (0.03, 0.35)     # roic/roe quando NÃO é a variável resolvida
_FAIXA_CUSTO = (0.03, 0.25)       # w/ke quando NÃO é a variável resolvida
_FAIXA_CAIXA = (0.0, 0.60)        # gde/nde (pe)
_FAIXA_GP = (-0.01, 0.06)
_FAIXA_TV_MARGINAL = (0.03, 0.30)  # roic_tv/roe_tv sob 'gordon'
_FAIXA_BOOK = (0.02, 0.40)         # roic_book/roe_book sob 'book'
_N_MIN, _N_MAX = 3, 30

_LO_HI_POR_RESOLVER = {
    # roic/roe: lo NAO fica perto de zero — perto do polo 1/roic (que existe
    # em toda convencao, via `ret = 1-g/roic` e/ou `ic_n`), a segunda
    # diferenca finita de `identificacao` (d2, dividida por h^2) amplifica
    # ruido de ponto flutuante o bastante para que Python e JS, mesmo
    # avaliando a MESMA formula na MESMA ordem, discordem no digito
    # arredondado — nao por um bug de espelho, mas porque `pow()`/`**` de
    # cada lado pode divergir por poucos ULPs perto de um polo, e o /h^2 da
    # segunda diferenca amplifica ULPs em ordens de grandeza (achado
    # registrado no relatorio desta task; a fixture evita a regiao em vez de
    # afrouxar a igualdade EXATA que o contrato de `identificacao` pede).
    "roic": (0.03, 0.80), "roe": (0.03, 0.80),
    "w": (0.02, 0.40), "ke": (0.02, 0.40),
    "g": (-0.30, 0.45),
}


def _problema_aleatorio(rng: random.Random) -> dict:
    fn = rng.choice(("ev_nopat", "pe"))
    tv = rng.choice(("book", "convergencia", "gordon"))
    resolver = rng.choice(("w", "roic", "g")) if fn == "ev_nopat" else rng.choice(("ke", "roe", "g"))

    n = rng.randint(_N_MIN, _N_MAX)
    args: dict = {"n": n, "tv": tv}
    if resolver != "g":
        args["g"] = round(rng.uniform(*_FAIXA_G), 6)

    if fn == "ev_nopat":
        if resolver != "roic":
            args["roic"] = round(rng.uniform(*_FAIXA_RETORNO), 6)
        if resolver != "w":
            args["w"] = round(rng.uniform(*_FAIXA_CUSTO), 6)
        if tv == "gordon":
            args["roic_tv"] = round(rng.uniform(*_FAIXA_TV_MARGINAL), 6)
            args["gp"] = round(rng.uniform(*_FAIXA_GP), 6)
        elif tv == "book":
            args["roic_book"] = round(rng.uniform(*_FAIXA_BOOK), 6)
    else:
        if resolver != "roe":
            args["roe"] = round(rng.uniform(*_FAIXA_RETORNO), 6)
        if resolver != "ke":
            args["ke"] = round(rng.uniform(*_FAIXA_CUSTO), 6)
        args["gde"] = round(rng.uniform(*_FAIXA_CAIXA), 6)
        args["nde"] = round(rng.uniform(*_FAIXA_CAIXA), 6)
        if tv == "gordon":
            args["roe_tv"] = round(rng.uniform(*_FAIXA_TV_MARGINAL), 6)
            args["gp"] = round(rng.uniform(*_FAIXA_GP), 6)
        elif tv == "book":
            args["roe_book"] = round(rng.uniform(*_FAIXA_BOOK), 6)

    lo, hi = _LO_HI_POR_RESOLVER[resolver]
    alvo = round(rng.uniform(2.0, 20.0), 6)
    completo = rng.random() < 0.3
    return _problema(resolver, fn, args, alvo=alvo, lo=lo, hi=hi, completo=completo)


def _bloco_aleatorio(rng: random.Random) -> list[dict]:
    return [_problema_aleatorio(rng) for _ in range(_TAMANHO_BLOCO_ALEATORIO)]


# ---------------------------------------------------------------------------
# Bloco 3 (task 3): problemas de WRAPPER — alvo de mercado, grade 1D, grade
# 2D. Pequeno de propósito (calibragem do brief task-4b-3: ~8-12 problemas no
# total bastam; o que discrimina é a ORIENTAÇÃO da grade e a aritmética da
# célula, não o tamanho — cada célula custa uma chamada de SUBPROCESSO ao
# motor congelado, `sensibilidades._precificar_celula`). Nenhum caso aqui
# cruza fronteira de domínio (NaN) de propósito — testar a recusa do motor
# através de uma grade quebraria a própria geração desta fixture
# (`grade_1d`/`grade_2d` não capturam `MotorFalhou`; ver task-4b-3-report.md).
_NOME_CENARIO = "cenario"


def _problema_alvo(rota: str, preco: float, acoes: float, nd_efetivo: float, metrica: dict) -> dict:
    return {"id": 0, "tipo": "alvo",
            "args": {"rota": rota, "preco": preco, "acoes": acoes,
                     "nd_efetivo": nd_efetivo, "metrica": metrica}}


def _problema_grade1d(rota: str, premissas: dict, metrica: dict, nd_efetivo: float,
                      acoes: float, premissa: str, pontos: list[float], moeda: str) -> dict:
    return {"id": 0, "tipo": "grade1d",
            "args": {"rota": rota, "premissas": premissas, "metrica": metrica,
                     "nd_efetivo": nd_efetivo, "acoes": acoes,
                     "premissa": premissa, "pontos": pontos, "moeda": moeda}}


def _problema_grade2d(rota: str, premissas: dict, metrica: dict, nd_efetivo: float, acoes: float,
                      premissa_x: str, pontos_x: list[float],
                      premissa_y: str, pontos_y: list[float], moeda: str) -> dict:
    return {"id": 0, "tipo": "grade2d",
            "args": {"rota": rota, "premissas": premissas, "metrica": metrica,
                     "nd_efetivo": nd_efetivo, "acoes": acoes,
                     "premissa_x": premissa_x, "pontos_x": pontos_x,
                     "premissa_y": premissa_y, "pontos_y": pontos_y, "moeda": moeda}}


def _bloco_wrapper() -> list[dict]:
    v: list[dict] = []

    # --- alvo (4): as duas rotas, incluindo um caso de caixa líquido
    # (nd_efetivo < 0) — a rota firm soma nd_efetivo ao market cap para
    # chegar em EV_mercado, então um caso sem caixa líquido nunca exercitaria
    # o sinal de subtração que essa soma vira quando nd_efetivo é negativo.
    v.append(_problema_alvo("firm", preco=42.50, acoes=120.0, nd_efetivo=350.0,
                            metrica={"tipo": "EBITDA", "valor": 900.0}))
    v.append(_problema_alvo("firm", preco=18.75, acoes=80.0, nd_efetivo=-200.0,
                            metrica={"tipo": "NOPAT", "valor": 300.0}))
    v.append(_problema_alvo("equity", preco=55.0, acoes=100.0, nd_efetivo=0.0,
                            metrica={"tipo": "LL", "valor": 250.0}))
    v.append(_problema_alvo("equity", preco=9.30, acoes=500.0, nd_efetivo=0.0,
                            metrica={"tipo": "LL", "valor": 700.0}))

    # Vetores centrais reutilizados pelas grades abaixo — mesma convenção de
    # PONTOS PERCENTUAIS de caso.json (ver tests/fixtures/caso_reversa_firm.json).
    premissas_firm_ebitda = dict(g=5.0, roic=12.0, wacc=10.0, n=10, da=20.0, tax=25.0,
                                 tv="gordon", roic_tv=10.0, gp=3.0)
    premissas_firm_nopat = dict(g=4.0, roic=15.0, wacc=9.0, n=10, da=0.0, tax=0.0,
                                tv="book", roic_book=12.0)
    premissas_equity = dict(g=4.0, roe=16.0, ke=10.0, n=10, gde=25.0, nde=10.0,
                            tv="convergencia")

    # --- grade1d (3): uma por combinação rota x métrica já usada em `alvo`
    # acima; cada uma inclui o PONTO CENTRAL (o valor que a própria premissa
    # central já usa) — regra da metodologia exercitada por
    # `test_celula_central_reproduz_o_caso_base`.
    v.append(_problema_grade1d("firm", premissas_firm_ebitda, {"tipo": "EBITDA", "valor": 900.0},
                               nd_efetivo=350.0, acoes=120.0, premissa="wacc",
                               pontos=[8.0, 9.0, 10.0, 11.0, 12.0], moeda="BRL-nominal"))
    v.append(_problema_grade1d("firm", premissas_firm_nopat, {"tipo": "NOPAT", "valor": 300.0},
                               nd_efetivo=-200.0, acoes=80.0, premissa="roic",
                               pontos=[11.0, 13.0, 15.0, 17.0, 19.0], moeda="BRL-nominal"))
    v.append(_problema_grade1d("equity", premissas_equity, {"tipo": "LL", "valor": 250.0},
                               nd_efetivo=0.0, acoes=100.0, premissa="ke",
                               pontos=[8.0, 9.0, 10.0, 11.0, 12.0], moeda="BRL-nominal"))

    # --- grade2d (2): NÃO quadradas de propósito — a fatia 3C descobriu que
    # uma grade quadrada esconde uma transposição de eixos (o teste passava
    # com os eixos trocados). 4x3 e 3x5, nunca NxN.
    v.append(_problema_grade2d("firm", premissas_firm_ebitda, {"tipo": "EBITDA", "valor": 900.0},
                               nd_efetivo=350.0, acoes=120.0,
                               premissa_x="roic", pontos_x=[10.0, 12.0, 14.0, 16.0],
                               premissa_y="g", pontos_y=[3.0, 5.0, 7.0], moeda="BRL-nominal"))
    v.append(_problema_grade2d("equity", premissas_equity, {"tipo": "LL", "valor": 250.0},
                               nd_efetivo=0.0, acoes=100.0,
                               premissa_x="ke", pontos_x=[8.0, 9.0, 10.0],
                               premissa_y="roe", pontos_y=[12.0, 14.0, 16.0, 18.0, 20.0],
                               moeda="BRL-nominal"))

    # --- grade1d (2), revisão final 4B — F4: os dois problemas equity de grade acima
    # (premissas_equity) sempre declaram gde/nde e nunca usam politica_tv, então o harness era
    # cego a F1 e F2 (review-4b-final.md). Os dois casos abaixo isolam cada achado, um por vez,
    # reusando o vetor que o revisor mediu diretamente contra o vendor
    # ({g:4, roe:18, ke:11, n:10, tv:'gordon', roe_tv:12, gp:3}).
    #
    # F1 — gde/nde AUSENTES (não `null`: são opcionais e o caso simplesmente não as declara,
    # `caso.py:161`). `premissasParaNucleo` pré-correção não repunha o default 0.0 do argparse
    # depois do colapso, então `pe()` lia `args.gde`/`args.nde` undefined e `caixa` virava NaN —
    # a grade INTEIRA saía `null` enquanto o Python (motor com o default de verdade) devolvia
    # preço. Varre "g" (não gde/nde: sweeping a própria premissa ausente reintroduziria a chave
    # e mascararia o achado).
    premissas_equity_sem_caixa = dict(g=4.0, roe=18.0, ke=11.0, n=10,
                                      tv="gordon", roe_tv=12.0, gp=3.0)
    v.append(_problema_grade1d("equity", premissas_equity_sem_caixa, {"tipo": "LL", "valor": 1000.0},
                               nd_efetivo=0.0, acoes=100.0, premissa="g",
                               pontos=[2.0, 3.0, 4.0, 5.0, 6.0], moeda="BRL-nominal"))

    # F2 — `politica_tv: null` (explícito e legal, `caso.py:797`; o wrapper Python preserva e o
    # argparse do motor aplica o default 'continua'). `premissasParaNucleo` pré-correção só
    # colapsava `null` para 'gp' — 'politica_tv' está em CHAVES_NAO_PERCENTUAIS, então o `null`
    # sobrevivia até `pe()`, que lia `'politica_tv' in args === true` e tomava o ramo
    # 'encerra' (deixa o termo de caixa do terminal DE FORA) onde o motor de verdade, nunca
    # tendo visto a flag, aplica 'continua' (ENTRA o termo de caixa) — número plausível e
    # ERRADO, não célula vazia. gde/nde declarados aqui de propósito, para isolar só F2 (sem
    # interação com F1 nesta mesma célula).
    premissas_equity_politica_null = dict(g=4.0, roe=18.0, ke=11.0, n=10, gde=25.0, nde=10.0,
                                          tv="gordon", roe_tv=12.0, gp=3.0, politica_tv=None)
    v.append(_problema_grade1d("equity", premissas_equity_politica_null, {"tipo": "LL", "valor": 1000.0},
                               nd_efetivo=0.0, acoes=100.0, premissa="roe",
                               pontos=[16.0, 17.0, 18.0, 19.0, 20.0], moeda="BRL-nominal"))

    return v


# ---------------------------------------------------------------------------
# Bloco 4 (item 4, fatia C, task 1): problemas de RAMPA — composição bifásica
# (`avaliar.precificar_rampa`, que por sua vez roda o subcomando `rampa` do motor congelado via
# subprocesso). Hand-escrito, mesma disciplina de `_bloco_patologico`/`_bloco_wrapper`: cada caso
# foi desenhado para exercitar UMA propriedade nomeada do plano da fatia e conferido por chamada
# direta a `precificar_rampa` antes de entrar aqui (ver task-4c-1-report.md). `premissas` está em
# PONTOS PERCENTUAIS (convenção de caso.json) — EXCETO receita0/ebitda0/da_parque/t_rampa/n/tv
# (CHAVES_NAO_PERCENTUAIS, motor_espelho.js): monetário/contagem/ano/enum, não taxa.
# ---------------------------------------------------------------------------


def _problema_rampa(premissas: dict, nd_efetivo: float | None, acoes: float | None,
                    moeda: str = "BRL-nominal", rf: float | None = None) -> dict:
    """`rf` (item 4, fatia C, task 2): optional, default `None` — mesmo comportamento de todo
    problema anterior a esta task (que nunca declarava a chave). Em PONTOS PERCENTUAIS, como
    `mercado.rf` — `_avaliar_rampa` repassa direto a `precificar_rampa(..., rf=...)`, e
    `resolverRampa` (motor_espelho.js) le a MESMA chave (`a.rf ?? null`)."""
    return {"id": 0, "tipo": "rampa",
            "args": {"premissas": premissas, "nd_efetivo": nd_efetivo, "acoes": acoes,
                     "moeda": moeda, "rf": rf}}


def _bloco_rampa() -> list[dict]:
    v: list[dict] = []

    # Vetor central reaproveitado por quase todo problema abaixo — cada caso sobrescreve só a(s)
    # chave(s) que a propriedade dele exige (`{**_base, "chave": valor}`), mesma convenção de
    # `_bloco_wrapper` acima (premissas_firm_ebitda etc.).
    base = dict(receita0=1000.0, ebitda0=300.0, da_parque=60.0, wk=15.0, kappa=20.0,
                g2=4.0, wacc=10.0, tax=25.0, t_rampa=3)

    # --- A. g1 DIRETO, tv='book' (sem --roic-book: o TV usa o marginal como se fosse médio — a
    # "conflação" que diag_firm comenta, fora do escopo desta task). 'n' AUSENTE da premissa —
    # PREMISSAS_OBRIGATORIAS_RAMPA (caso.py) não inclui 'n' (detalhe 2 do brief: "n não é
    # obrigatório no caso"), então este é o caso que exercita o default 10 do argparse do
    # subparser 'rampa' (justos.py:1749) — nenhum outro problema abaixo omite 'n'. Com ponte.
    v.append(_problema_rampa({**base, "g1": 6.0, "tv": "book"}, nd_efetivo=400.0, acoes=120.0))

    # --- B. g1 DERIVADO de util (g1 ausente) -> capacidade_receita sai na saída (detalhe 3 do
    # brief: "com g1 ausente, util deriva g1 e capacidade_receita sai"); tv='convergencia'. Com
    # ponte.
    v.append(_problema_rampa({**base, "util": 55.0, "tv": "convergencia", "n": 10},
                             nd_efetivo=400.0, acoes=120.0))

    # --- C. tv='gordon', roic_tv/gp válidos (roic_tv > 0, gp < wacc — nenhum dos dois viola o
    # domínio de ev_nopat na fase 2). Com ponte.
    v.append(_problema_rampa(
        {**base, "g1": 6.0, "tv": "gordon", "roic_tv": 12.0, "gp": 2.0, "n": 10},
        nd_efetivo=400.0, acoes=120.0))

    # --- D. g1 < 0 (colheita) -> aviso_colheita; SEM ponte (nd_efetivo/acoes nulos -> valor só
    # tem "EV") — combina os dois itens do brief num problema só, de propósito.
    v.append(_problema_rampa({**base, "g1": -5.0, "tv": "book", "n": 10},
                             nd_efetivo=None, acoes=None))

    # --- E. rir2 >= 100% (delator) -> aviso_delator: kappa dominante (capex fixo de expansão
    # bem acima do giro) + g2 alto empurram a taxa de reinvestimento da fase 2 acima do
    # autofinanciável — medido por chamada direta antes de fixar os números (rir2 ≈ 106,8%).
    v.append(_problema_rampa(
        {**base, "g1": 6.0, "tv": "book", "wk": 10.0, "kappa": 90.0, "g2": 25.0, "n": 10},
        nd_efetivo=400.0, acoes=120.0))

    # --- F. wk = kappa = 0 -> den_cap <= 1e-15 -> roic2_% vira a STRING do motor, não um número
    # (detalhe 5 do brief).
    v.append(_problema_rampa(
        {**base, "g1": 6.0, "tv": "book", "wk": 0.0, "kappa": 0.0, "n": 10},
        nd_efetivo=400.0, acoes=120.0))

    # --- G. g1 = wacc (mesmo ponto percentual) -> r1 = (1+g1)/(1+w) = 1 EXATO -> soma_r1 usa o
    # ramo fechado T em vez de r1*(1-r1**T)/(1-r1) (detalhe 5 do brief).
    v.append(_problema_rampa({**base, "g1": 7.0, "wacc": 7.0, "tv": "convergencia", "n": 10},
                             nd_efetivo=400.0, acoes=120.0))

    # --- H. wacc = 0 -> ann_beta usa o ramo fechado T em vez de (1-(1+w)**-T)/w (detalhe 5 do
    # brief); tv='book' — 'convergencia' exige w > 0 em ev_nopat e refutaria este caso por
    # engano, mascarando o que ele testa.
    v.append(_problema_rampa({**base, "g1": 5.0, "wacc": 0.0, "tv": "book", "n": 10},
                             nd_efetivo=400.0, acoes=120.0))

    # --- I..M: uma recusa de CADA família do item 6 do brief (5 problemas) — os outros parâmetros
    # ficam no domínio válido em cada um, para que a recusa seja atribuível à família testada, não
    # a uma interação acidental com outra guarda.

    # I. "t_rampa < 1 ou n <= t_rampa" — aqui n <= t_rampa (t_rampa=5, n=5).
    v.append(_problema_rampa({**base, "g1": 6.0, "tv": "book", "t_rampa": 5, "n": 5},
                             nd_efetivo=400.0, acoes=120.0))

    # J. "w <= -1 ou g2 <= -1" — aqui w <= -1 (wacc=-150.0%, fração -1.5).
    v.append(_problema_rampa({**base, "g1": 6.0, "tv": "book", "wacc": -150.0, "n": 10},
                             nd_efetivo=400.0, acoes=120.0))

    # K. "wk < 0 ou kappa < 0" — aqui wk < 0.
    v.append(_problema_rampa({**base, "g1": 6.0, "tv": "book", "wk": -5.0, "n": 10},
                             nd_efetivo=400.0, acoes=120.0))

    # L. "util fora de (0,1) sem g1" — g1 ausente, util=150.0% (fração 1.5, fora do domínio).
    v.append(_problema_rampa({**base, "util": 150.0, "tv": "book", "n": 10},
                             nd_efetivo=400.0, acoes=120.0))

    # M. "margem NOPAT da fase 2 <= 0" — da_parque bem acima do EBITDA do ano T (d2 >= 1, medido
    # por chamada direta: d2 ≈ 115,2% com este vetor).
    v.append(_problema_rampa({**base, "g1": 5.0, "tv": "book", "da_parque": 400.0, "n": 10},
                             nd_efetivo=400.0, acoes=120.0))

    # --- N/O/P (item 4, fatia C, task 2): aviso_gp — condição do handler `rampa`
    # (`getattr(a,'rf',None) is not None and a.tv == 'gordon' and pc(a.gp) and pc(a.gp) >
    # pc(a.rf)`), verificada por chamada direta ao motor congelado (não pela leitura isolada do
    # handler — ver task-4c-2-report.md para os dois comandos que produziram a evidência).
    #
    # N. tv='gordon', gp (8%) > rf (5%) -> aviso_gp DISPARA. roic_tv=20% fica bem acima de wacc
    # (10%) e de gp para não confundir esta propriedade com ROIC_TV < WACC (REGIME DECLARADO,
    # não testado por esta fatia na rota rampa).
    v.append(_problema_rampa(
        {**base, "g1": 6.0, "tv": "gordon", "roic_tv": 20.0, "gp": 8.0, "n": 10},
        nd_efetivo=400.0, acoes=120.0, rf=5.0))

    # O. tv='ic' (alias legado de 'book', NÃO da família gordon) com o MESMO gp (8%) > rf (5%) que
    # N -> aviso_gp NÃO dispara: o próprio _guardas_damodaran só considera a âncora quando
    # tv_canon(tv) == 'gordon', e 'ic' canonicaliza para 'book'. Fronteira genuína do domínio
    # gordon — não confundir com a peculiaridade de P abaixo.
    v.append(_problema_rampa(
        {**base, "g1": 6.0, "tv": "ic", "n": 10, "gp": 8.0},
        nd_efetivo=400.0, acoes=120.0, rf=5.0))

    # P. tv='spread' (alias legado de 'gordon'), MESMOS roic_tv/gp/rf de N.
    #
    # ACHADO (não suposição do plano — verificado empiricamente, duas vezes, contra o motor
    # congelado de verdade): a versão anterior deste item dizia que a comparação do handler
    # (`a.tv == 'gordon'`) é feita SEM tv_canon, e que por isso o alias 'spread' NÃO dispararia
    # aviso_gp. Isso não é o que o motor faz. A substituição de alias
    # (`a.tv = tv_canon(a.tv)`, justos.py ~1888-1894) roda ANTES de QUALQUER `if a.cmd == ...`,
    # para TODO subcomando — quando o handler `rampa` lê `a.tv`, 'spread' JÁ virou 'gordon'.
    # `--tv spread --gp 8 --rf 5` no motor real dispara aviso_gp byte a byte IGUAL a `--tv gordon`
    # com os mesmos números; só `--tv ic` (problema O acima, que canonicaliza para 'book') não
    # dispara. Comandos que provam isso (rodados direto, sem avaliar.py no meio):
    #   python vendor/multiplos-justos/scripts/justos.py rampa ... --tv spread --gp 8 --rf 5 ...
    #   python vendor/multiplos-justos/scripts/justos.py rampa ... --tv gordon --gp 8 --rf 5 ...
    # — os dois devolvem o MESMO 'aviso_gp'. Por isso este problema espera DISPARAR (paridade é
    # contra o COMPORTAMENTO do motor, não contra uma leitura textual isolada do handler) — o
    # oposto do que o plano original previa. Discrepância registrada no relatório desta task.
    v.append(_problema_rampa(
        {**base, "g1": 6.0, "tv": "spread", "roic_tv": 20.0, "gp": 8.0, "n": 10},
        nd_efetivo=400.0, acoes=120.0, rf=5.0))

    # --- Q/R (F2, revisão final): recusa de domínio pré-handler (`avaliar_dominios_cli`,
    # justos.py:1608-1630) que NENHUM guarda interno de `rampa_bifasica`/`rampaBifasica` cobre por
    # acidente — ao contrário de J (wacc=-150%, que a checagem `w <= -1` da própria função também
    # capturaria) e de I/K/L/M (que violam OUTRA fronteira interna sempre presente), estes dois
    # provam a lacuna de verdade: sem o guarda novo, o espelho computava um número, não recusava.

    # Q. g1 = -150% (<= -100%): rampa_bifasica/rampaBifasica NÃO tem guarda de domínio nenhuma
    # sobre g1 — vira receita negativa e um EV finito (mas sem sentido), em vez de recusa. O motor
    # de verdade recusa no Gate de domínio, antes de sequer montar `rev`. Verificado por execução
    # (fixes-4c-report.md): pré-correção, o espelho devolvia EV -359,30 aqui.
    v.append(_problema_rampa(
        {**base, "g1": -150.0, "tv": "convergencia", "n": 10}, nd_efetivo=400.0, acoes=120.0))

    # R. gp = -150% (<= -100%) sob tv='book': gp é INERTE sob 'book' (nenhuma fórmula do núcleo o
    # lê nessa convenção) — sem o guarda novo, o espelho ignorava o valor fora do domínio e
    # devolvia o MESMO preço do caso válido, porque nunca chega a ler `gp`. O motor de verdade
    # recusa mesmo assim: o Gate de domínio roda sobre o valor BRUTO da CLI, incondicional à
    # convenção terminal declarada.
    v.append(_problema_rampa(
        {**base, "g1": 6.0, "tv": "book", "gp": -150.0, "n": 10},
        nd_efetivo=400.0, acoes=120.0))

    # --- S/T (F4, revisão final): fixture mínima que fecha duas das cinco fronteiras sem pino que
    # a revisão provou (M2/M3) — cada uma, uma mutação plausível que a suíte não pegava.

    # S. (M2) gordon, gp EXATAMENTE = rf (5% = 5%) -> SEM aviso_gp: gp não EXCEDE rf, só o alcança.
    # A mutação `gpNucleo > rfFracao` -> `gpNucleo >= rfFracao` dispararia o aviso aqui, onde o
    # motor de verdade não dispara.
    v.append(_problema_rampa(
        {**base, "g1": 6.0, "tv": "gordon", "roic_tv": 20.0, "gp": 5.0, "n": 10},
        nd_efetivo=400.0, acoes=120.0, rf=5.0))

    # T. (M3) gordon, gp (10%) = wacc (10%, o default de `base`): a fase 2 chama ev_nopat com
    # `w - gp` no denominador do termo terminal -> zero -> EV/EBITDA0 não-finito -> o motor de
    # verdade recusa (`_exigir_valor` sobre um `null` que o serializador produziu a partir de NaN).
    # A mutação que remove a checagem `!Number.isFinite(saidaMotor['EV/EBITDA0'])` devolveria
    # `recusado: false` com multiplo/valor/saida nulos em vez de recusar.
    v.append(_problema_rampa(
        {**base, "g1": 6.0, "tv": "gordon", "roic_tv": 20.0, "gp": 10.0, "n": 10},
        nd_efetivo=400.0, acoes=120.0))

    return v


# ---------------------------------------------------------------------------
# Bloco 5 (item 4, fatia C, task 2): problemas de DIAGNOSTICO — predicados de diag_firm/diag_eq/
# _guardas_damodaran/coerencia_vetor, alcançados pelo mesmo caminho do wrapper que os blocos 3/4
# (`motor.rodar` direto, sem escala — só a lista `diagnosticos` importa aqui, não preço nem
# múltiplo). Hand-escrito, mesma disciplina de `_bloco_wrapper`/`_bloco_rampa`: cada caso foi
# desenhado para exercitar UMA chave NOVA de `diagnosticos_chaves.json` e conferido por chamada
# direta a `motor.rodar` antes de entrar aqui (ver task-4c-2-report.md). `premissas` está em
# PONTOS PERCENTUAIS (convenção de caso.json), como os outros blocos de wrapper.
#
# Reachability (achado da task, não suposição): `coerencia_vetor` só contribui UMA chave —
# `coerencia_eco_intensidade_capital` (identidade 4, "d×intensidade de capital") — e SÓ na rota
# firm. As outras três identidades (1: ROE×ROIC×alavancagem — a fonte de "CAIXA REMUNERADO
# [vetor]"; 2: WACC×Ke×Kd×alavancagem; 3: RiR observado×g/ROIC) exigem, juntas, {roe, gde, nde,
# kd} na rota firm ou {roic, wacc, kd, tax} na rota equity — nenhum desses nomes está em
# PREMISSAS_FIRM/PREMISSAS_EQUITY (caso.py), então nenhuma delas jamais executa pelo caminho do
# wrapper, nas duas rotas. Confirmado rodando `motor.rodar` com um varredura de ~1300 vetores
# firm/equity (nenhuma mensagem "[vetor]" fora da identidade 4 apareceu nenhuma vez) — por isso
# `diagnosticos_chaves.json` não tem entrada "INCOERÊNCIA"/"CAIXA REMUNERADO"/"DIVERGÊNCIA
# DECLARADA [vetor]" nenhuma: são inalcançáveis, "não espelhe" (detalhe 2 do plano).
_BASE_DIAG_FIRM: dict = dict(g=5.0, roic=15.0, wacc=9.0, n=10, da=20.0, tax=25.0, tv="book")
_BASE_DIAG_EQ: dict = dict(g=4.0, roe=16.0, ke=10.0, n=10, gde=25.0, nde=10.0, tv="book")


def _problema_diag(rota: str, premissas: dict, moeda: str = "BRL-nominal",
                   rf: float | None = None) -> dict:
    return {"id": 0, "tipo": "diag",
            "args": {"rota": rota, "premissas": premissas, "moeda": moeda, "rf": rf}}


def _bloco_diag() -> list[dict]:
    v: list[dict] = []
    bf, be = _BASE_DIAG_FIRM, _BASE_DIAG_EQ

    # ===== rota firm (diag_firm + guardas de Damodaran + coerência identidade 4) =====

    # 1. book, SEM --roic-book -> convenção 'book' + conflação (chaves novas: firm_convencao_book,
    # firm_conflacao_sem_roic_book, firm_rir, coerencia_eco_intensidade_capital).
    v.append(_problema_diag("firm", {**bf}))

    # 2. RiR > 100% (g=20% >> roic=15%) -> firm_alerta_rir_excede_100.
    v.append(_problema_diag("firm", {**bf, "g": 20.0, "roic": 15.0}))

    # 3. roic < wacc, g > 0, book SEM roic_book -> firm_alerta_roic_abaixo_wacc,
    # firm_alerta_conflacao_b01.
    v.append(_problema_diag("firm", {**bf, "roic": 6.0, "wacc": 9.0, "g": 3.0}))

    # 4. roic < wacc, book COM roic_book >= wacc (sem sub-alerta) -> firm_convencao_condicionada_b01,
    # firm_eco_deriva_medio.
    v.append(_problema_diag(
        "firm", {**bf, "roic": 6.0, "wacc": 9.0, "g": 3.0, "roic_book": 10.0}))

    # 5. roic < wacc, book COM roic_book < wacc (com sub-alerta) -> firm_sub_alerta_b01_medio.
    v.append(_problema_diag(
        "firm", {**bf, "roic": 6.0, "wacc": 9.0, "g": 3.0, "roic_book": 5.0}))

    # 6. roic ≈ wacc (9% = 9%) mas roic_book diverge (15%) -> firm_atencao_roic_wacc_book_diverge.
    v.append(_problema_diag(
        "firm", {**bf, "roic": 9.0, "wacc": 9.0, "roic_book": 15.0}))

    # 7. roic = wacc, tv='convergencia' (sem book) -> firm_neutralidade_identidade.
    v.append(_problema_diag(
        "firm", {**bf, "roic": 9.0, "wacc": 9.0, "tv": "convergencia"}))

    # 7b. QUASE-empate: roic (9,20%) − wacc (9,00%) = 0,20 p.p. = 2e-3 — ACIMA do limiar real de
    # neutralidade (5e-4 = 0,05 p.p.), então NENHUMA chave de neutralidade dispara aqui (só
    # firm_rir + coerencia_eco). Este problema é o alvo da prova de falseabilidade desta task: um
    # limiar mutado para 5e-3 (0,5 p.p.) tornaria 0,20 p.p. "neutro" e faria
    # firm_neutralidade_identidade disparar só no espelho — RED nomeando este id. Verificado por
    # chamada direta ao motor antes de fixar os números (só RiR + ECO aparecem).
    v.append(_problema_diag(
        "firm", {**bf, "roic": 9.20, "wacc": 9.00, "tv": "convergencia"}))

    # 8. g ≈ 0, tv='gordon' (roic_tv/gp válidos, sem --rf) -> firm_neutralidade_g0_gordon,
    # damodaran_premissa_nao_ancorada.
    v.append(_problema_diag(
        "firm", {**bf, "g": 0.0, "tv": "gordon", "roic_tv": 10.0, "gp": 2.0}))

    # 9. g ≈ 0, tv='convergencia' -> firm_neutralidade_g0_convergencia.
    v.append(_problema_diag("firm", {**bf, "g": 0.0, "tv": "convergencia"}))

    # 10. g ≈ 0, tv='book' -> firm_atencao_g0_book.
    v.append(_problema_diag("firm", {**bf, "g": 0.0, "tv": "book"}))

    # 11. tv='gordon', ROIC_TV (5%) < WACC (9%), sem --rf -> firm_regime_declarado_roic_tv.
    v.append(_problema_diag(
        "firm", {**bf, "tv": "gordon", "roic_tv": 5.0, "gp": 2.0, "wacc": 9.0}))

    # 12. tv='gordon', ROIC_TV ≈ WACC (9% = 9%), sem --rf -> firm_nota_colapso_gordon.
    v.append(_problema_diag(
        "firm", {**bf, "tv": "gordon", "roic_tv": 9.0, "gp": 2.0, "wacc": 9.0}))

    # 13. Damodaran ALERTA: gp (8%) > teto (rf=5%) -> damodaran_alerta_ancora_macro.
    v.append(_problema_diag(
        "firm", {**bf, "tv": "gordon", "roic_tv": 20.0, "gp": 8.0, "wacc": 9.0}, rf=5.0))

    # 14. Damodaran ÂNCORA OK: gp (3%) <= teto (rf=5%) -> damodaran_ancora_ok.
    v.append(_problema_diag(
        "firm", {**bf, "tv": "gordon", "roic_tv": 20.0, "gp": 3.0, "wacc": 9.0}, rf=5.0))

    # 15. Damodaran regime real, SEM --rf (moeda 'BRL-real' -> teto = PIB real 3%) — mesma chave
    # de 13 (damodaran_alerta_ancora_macro), mas exercita o ramo `elif regime_real:` de
    # _guardasDamodaranChaves que nenhum outro problema toca (13/14 sempre declaram rf).
    v.append(_problema_diag(
        "firm", {**bf, "tv": "gordon", "roic_tv": 20.0, "gp": 4.0, "wacc": 9.0},
        moeda="BRL-real", rf=None))

    # ===== rota equity (diag_eq + guardas de Damodaran; coerência NUNCA contribui aqui) =====

    # 16. book, SEM --roe-book -> eq_convencao_book, eq_conflacao_sem_roe_book, eq_retencao,
    # eq_limitacao_c2_ke_fixo (gde=25% != nde=10% na base -> caixa != 0).
    v.append(_problema_diag("equity", {**be}))

    # 17. book, COM roe_book (13%) que diverge do roe marginal (16%) -> eq_eco_deriva_medio.
    v.append(_problema_diag("equity", {**be, "roe_book": 13.0}))

    # 18. payout ≈ 0 (g=15,5% quase = roe=16%) -> eq_payout_zero_nao_informativo.
    v.append(_problema_diag("equity", {**be, "g": 15.5, "roe": 16.0}))

    # 19. tv='gordon', roe_tv (12%) válido, gp (9%) > 0, caixa != 0, política default 'continua',
    # Ke(10%)-gp(9%)=1 p.p. dentro de (0, 2 p.p.) -> eq_politica_caixa_continua,
    # eq_alerta_sensibilidade_ke_gp. Sem --rf -> também exercita damodaran_premissa_nao_ancorada
    # (já coberta pela rota firm, mas nesta rota confirma que o MESMO guarda compartilhado roda
    # igual dos dois lados).
    v.append(_problema_diag(
        "equity", {**be, "tv": "gordon", "roe_tv": 12.0, "gp": 9.0, "ke": 10.0}))

    # 20. ND/E (20%) > GD/E (5%) -> caixa negativo -> eq_dominio_nde_maior_gde.
    v.append(_problema_diag("equity", {**be, "gde": 5.0, "nde": 20.0}))

    # 21. g/ROE > 100% (g=20% > roe=16%) -> eq_alerta_groe_excede_100.
    v.append(_problema_diag("equity", {**be, "g": 20.0, "roe": 16.0}))

    # 22. roe < ke, g > 0, book SEM roe_book -> eq_alerta_roe_abaixo_ke, eq_alerta_conflacao_b01.
    v.append(_problema_diag("equity", {**be, "roe": 6.0, "ke": 10.0, "g": 3.0}))

    # 23. roe < ke, book COM roe_book >= ke (sem sub-alerta) -> eq_convencao_condicionada_b01.
    v.append(_problema_diag(
        "equity", {**be, "roe": 6.0, "ke": 10.0, "g": 3.0, "roe_book": 11.0}))

    # 24. roe < ke, book COM roe_book < ke (com sub-alerta) -> eq_sub_alerta_b01_medio.
    v.append(_problema_diag(
        "equity", {**be, "roe": 6.0, "ke": 10.0, "g": 3.0, "roe_book": 5.0}))

    # 25. roe ≈ ke (10% = 10%) mas roe_book diverge (15%) -> eq_atencao_roe_ke_book_diverge.
    v.append(_problema_diag("equity", {**be, "roe": 10.0, "ke": 10.0, "roe_book": 15.0}))

    # 26. roe ≈ ke, tv='book', SEM roe_book -> eq_neutralidade_book_clean_surplus.
    v.append(_problema_diag("equity", {**be, "roe": 10.0, "ke": 10.0}))

    # 27. roe ≈ ke, tv='convergencia', caixa = 0 (gde=nde=10%) -> eq_neutralidade_identidade_caixa0.
    v.append(_problema_diag(
        "equity", {**be, "roe": 10.0, "ke": 10.0, "tv": "convergencia", "gde": 10.0, "nde": 10.0}))

    # 28. roe ≈ ke, tv='convergencia', caixa != 0 -> eq_atencao_fcfe_nao_book.
    v.append(_problema_diag(
        "equity", {**be, "roe": 10.0, "ke": 10.0, "tv": "convergencia"}))

    # 29. g ≈ 0, tv='gordon' -> eq_neutralidade_g0_gordon (+ eq_politica_caixa_continua, sem --rf).
    v.append(_problema_diag(
        "equity", {**be, "g": 0.0, "tv": "gordon", "roe_tv": 12.0, "gp": 2.0}))

    # 30. g ≈ 0, tv='convergencia' -> eq_neutralidade_g0_convergencia.
    v.append(_problema_diag("equity", {**be, "g": 0.0, "tv": "convergencia"}))

    # 31. g ≈ 0, tv='book' -> eq_atencao_g0_book.
    v.append(_problema_diag("equity", {**be, "g": 0.0, "tv": "book"}))

    # 32. tv='gordon', ROE_TV (5%) < Ke (10%), política 'encerra' explícita, sem --rf ->
    # eq_politica_caixa_encerra, eq_regime_declarado_roe_tv.
    v.append(_problema_diag(
        "equity", {**be, "tv": "gordon", "roe_tv": 5.0, "gp": 3.0, "ke": 10.0,
                  "politica_tv": "encerra"}))

    # 33. tv='gordon', ROE_TV ≈ Ke (10% = 10%), sem --rf -> eq_nota_colapso_gordon.
    v.append(_problema_diag(
        "equity", {**be, "tv": "gordon", "roe_tv": 10.0, "gp": 3.0, "ke": 10.0}))

    # 34. Damodaran ALERTA visto pela rota equity (gp=8% > rf=5%) — mesma chave de 13, mas
    # confirma que o guarda compartilhado dispara igual quando chamado por diag_eq.
    v.append(_problema_diag(
        "equity", {**be, "tv": "gordon", "roe_tv": 20.0, "gp": 8.0, "ke": 9.0}, rf=5.0))

    # ===== F2 (revisão final, fatia 4C): recusa de domínio pré-handler nos DIAGNÓSTICOS =====
    # `diag_firm`/`diag_eq` nunca chegam a rodar quando `avaliar_dominios_cli` já recusou — o
    # motor sai no Gate de domínio, ANTES de calcular `diagnosticos`. Nenhuma das duas funções do
    # espelho (`diagnosticosFirm`/`diagnosticosEquity`) tinha guarda nenhuma sobre isso: um wacc/
    # ke/n fora do domínio produzia uma lista CHEIA de chaves — o diagnóstico não se movia com o
    # número (o número já tinha sido recusado por `precificarCelula`/`precificarRampa`, mas o
    # diagnóstico, chamado à parte no laboratório, não sabia disso).

    # 35. wacc = -150% (<= -100%), rota firm -> o motor recusa no Gate de domínio; NENHUMA chave
    # sai (`mensagens: []` — ver `_avaliar_diag`, que agora captura `MotorFalhou`).
    v.append(_problema_diag("firm", {**bf, "wacc": -150.0}))

    # 36. n = 0 (< 1), rota equity -> mesma recusa de domínio, família diferente (n, não uma taxa).
    v.append(_problema_diag("equity", {**be, "n": 0}))

    # ===== F4 (revisão final, fatia 4C): fixture mínima que fecha três das cinco fronteiras sem
    # pino que a revisão provou (M1/M4/M5) — cada uma, uma mutação plausível que a suíte não
    # pegava (ver `_bloco_rampa`, problemas S/T, para as outras duas, M2/M3). =====

    # 37. (M1) Damodaran, gp EXATAMENTE no teto (gp = rf = 5%) -> "ÂNCORA MACRO OK": gp não EXCEDE
    # o teto, só o alcança. A mutação `gp > teto + TOL_EPS` -> `gp >= teto` dispararia "ALERTA"
    # aqui, onde o motor de verdade não dispara.
    v.append(_problema_diag(
        "firm", {**bf, "tv": "gordon", "roic_tv": 20.0, "gp": 5.0, "wacc": 9.0}, rf=5.0))

    # 38. (M5) Damodaran, regime real com rf (6%) ACIMA do teto de 3%: o teto tem de ser
    # min(rf, 3%) = 3%, e gp (4%) excede esse teto -> "ALERTA". A mutação que troca
    # `Math.min(rfFracao, 0.03)` por `rfFracao` puro usaria 6% como teto e diria "ÂNCORA MACRO OK"
    # (gp 4% < rf 6%) — errado; o teto em regime real nunca é o rf nominal cru.
    v.append(_problema_diag(
        "firm", {**bf, "tv": "gordon", "roic_tv": 20.0, "gp": 4.0, "wacc": 9.0},
        moeda="BRL-real", rf=6.0))

    # 39. (M4) equity SEM gde/nde (chaves ausentes do vetor — o argparse do motor aplica o default
    # 0.0/0.0), roe = ke (10% = 10%), tv='convergencia' -> caixa = 0-0 = 0 ->
    # "NEUTRALIDADE [identidade, caixa/E=0]". A mutação que lê `nucleo.gde`/`nucleo.nde` crus (sem
    # o `'gde' in nucleo ? ... : 0` de presença) faria caixa = NaN — e `Math.abs(NaN) < TOL_EPS` é
    # sempre falso — caindo no ramo "ATENÇÃO [FCFE não-book]" em vez da neutralidade.
    v.append(_problema_diag(
        "equity", {"g": 4.0, "roe": 10.0, "ke": 10.0, "n": 10, "tv": "convergencia"}))

    return v


# ---------------------------------------------------------------------------
# Bloco 6 (Fatia D, Task 2): problemas de DEGRAU (Gate 3 — capacidade ociosa de balanço) —
# `avaliar_caso` (avaliar.avaliar) de verdade sobre um caso MÍNIMO (uma rota equity, um cenário
# "c", um bloco `degrau`), alcançado pelo MESMO caminho do wrapper que os blocos 3/4/5 (motor
# congelado via subprocesso, nunca reimplementação). Hand-escrito, mesma disciplina de
# `_bloco_wrapper`/`_bloco_rampa`/`_bloco_diag`: cada caso foi desenhado para exercitar UMA
# propriedade nomeada do plano da fatia e conferido por chamada direta ao motor
# (`justos.py degrau`) antes de entrar aqui (ver task-d2-report.md). `premissas` está em PONTOS
# PERCENTUAIS (convenção de caso.json, como os outros blocos); `bloco_degrau` está em valores
# CRUS (indice_atual/indice_alvo/anos/vpa/fx são razão/ano/moeda, nunca taxa — não passam por
# pc()); `m_valor` está em %, como o resto de caso.json.
#
# O vetor-base B ({g:10,roe:18,ke:14,tv:gordon,roe_tv:15,gp:5}) declara `roe_tv` DIFERENTE de
# `roe` de propósito: a âncora do SKILL.md (roe=roe_tv=20%) não discrimina um mirror que ignore
# `roe_tv` declarado e sempre substitua pela rentabilidade base — com roe_tv=15% ≠ roe=18%, um
# espelho que cometesse esse erro leria roe_tv errado em toda variação abaixo (h=1, m∈{0,70,130},
# anos fracionário, ALERTA, ALERTA_RiR). O fallback `pc(roe_tv) or rent` (detalhe 2 do brief, só
# dispara quando roe_tv está AUSENTE ou é literalmente 0) não tem caso próprio aqui: qualquer
# vetor que o exercitasse sob `tv=gordon` também derrubaria a perna sem-degrau (que usa roe_tv TAL
# COMO declarado, sem o `or`) — as duas pernas refusariam juntas, e o problema cairia no mesmo
# balde do problema 11 (recusa de domínio) sem discriminar nada de novo; verificado por conferência
# direta antes de descartar a ideia (ver task-d2-report.md).
_BASE_DEGRAU_B: dict = dict(g=10.0, roe=18.0, ke=14.0, n=10, tv="gordon", roe_tv=15.0, gp=5.0)


def _problema_degrau(premissas: dict, bloco_degrau: dict, m_valor: float,
                     metrica_valor: float = 500.0, acoes: float = 100.0,
                     preco_valor: float = 40.0) -> dict:
    return {"id": 0, "tipo": "degrau",
            "args": {"premissas": premissas, "metrica_valor": metrica_valor, "acoes": acoes,
                     "preco_valor": preco_valor, "bloco_degrau": bloco_degrau, "m_valor": m_valor}}


def _bloco_degrau() -> list[dict]:
    v: list[dict] = []
    b = _BASE_DEGRAU_B

    # 1. Âncora do SKILL.md do vendor (vendor/multiplos-justos/SKILL.md:265) — os MESMOS
    # argumentos que tests/test_valuation_degrau.py:_ARGV_ANCORA_SKILL_MD usa como referência, com
    # um único índice-alvo (14, D3: um preço por cenário). Cross-valida os dois lados desta fatia
    # contra o MESMO exemplo documentado.
    v.append(_problema_degrau(
        {"g": 12.0, "roe": 20.0, "ke": 20.0, "n": 10, "tv": "gordon", "roe_tv": 20.0, "gp": 6.5},
        {"indice_atual": 19.3, "indice_alvo": 14.0, "anos": 4, "perfil_transicao": "rampa",
         "vpa": 29.11, "fx": 1.0},
        m_valor=100.0))

    # 2. h = 1 (indice_alvo == indice_atual) — o degrau não inventa valor sem capacidade ociosa
    # real (test_2 da Task 1, mesma propriedade, agora discriminada na paridade JS: com_transicao
    # == multiplo_x_rentab, e o multiplo bate com PL_curr de sem_degrau).
    v.append(_problema_degrau(
        b, {"indice_atual": 15.0, "indice_alvo": 15.0, "anos": 4, "perfil_transicao": "rampa",
            "vpa": 25.0, "fx": 1.0}, m_valor=100.0))

    # 3-5. m ∈ {0, 70, 130} — mesma capacidade ociosa (h=1.5), eficiência marginal variando; m=0
    # mantém a rentabilidade pós = base (test_3 da Task 1), apesar de h != 1.
    for m in (0.0, 70.0, 130.0):
        v.append(_problema_degrau(
            b, {"indice_atual": 15.0, "indice_alvo": 10.0, "anos": 4, "perfil_transicao": "rampa",
                "vpa": 25.0, "fx": 1.0}, m_valor=m))

    # 6. anos fracionário (3.5) — desconto_transicao recebe uma tranche PROPORCIONAL no último
    # período (detalhe 1 do brief), não uma soma inteira a mais nem uma tranche cheia.
    v.append(_problema_degrau(
        b, {"indice_atual": 15.0, "indice_alvo": 10.0, "anos": 3.5, "perfil_transicao": "rampa",
            "vpa": 25.0, "fx": 1.0}, m_valor=100.0))

    # 7. perfil_transicao = pontual — mesmos índices/anos/m do problema 3-5 (m=100): só o perfil
    # muda, e fator_transicao tem de divergir do rampa equivalente (problema 3-5, m=100).
    v.append(_problema_degrau(
        b, {"indice_atual": 15.0, "indice_alvo": 10.0, "anos": 4, "perfil_transicao": "pontual",
            "vpa": 25.0, "fx": 1.0}, m_valor=100.0))

    # 8. tv=book COM roe_book declarado (D6 — Task 1 recusaria sem ele) — vetor próprio, book não
    # usa roe_tv/gp.
    v.append(_problema_degrau(
        {"g": 8.0, "roe": 18.0, "ke": 14.0, "n": 10, "tv": "book", "roe_book": 16.0},
        {"indice_atual": 15.0, "indice_alvo": 10.0, "anos": 4, "perfil_transicao": "rampa",
         "vpa": 25.0, "fx": 1.0}, m_valor=100.0))

    # 9. ALERTA — h=3 (indice_atual=30, indice_alvo=10) empurra a rentabilidade pós (54%) acima de
    # max(2×ke, 30%) = 30% — "rentabilidade pós-degrau implausível como estado estacionário".
    v.append(_problema_degrau(
        b, {"indice_atual": 30.0, "indice_alvo": 10.0, "anos": 4, "perfil_transicao": "rampa",
            "vpa": 25.0, "fx": 1.0}, m_valor=100.0))

    # 10. ALERTA_RiR — F1 (onda de correção da revisão final) substituiu o vetor original deste
    # problema: h=0.4 (indice_atual=8 < indice_alvo=20 — degrau NEGATIVO) disparava o mesmo alerta,
    # mas o gate agora recusa `indice_atual < indice_alvo` (falta de capital, não capacidade
    # ociosa — ver `_validar_degrau`, caso.py) — o vetor antigo virou ILEGAL pelo gate. A fixture
    # tem de conter só problemas gate-legais (mesmo esta rota bypassando `validar()` via
    # `avaliar_caso` direto — ver `_avaliar_degrau`, abaixo — um vetor que o gate recusaria é
    # higiene ruim: alguém que copiasse este problema para um caso.json de verdade seria recusado).
    # Substituto achado pelo revisor da fatia D: roe=10% < g=12% (retenção > 100%, payout negativo
    # já na base — diagnóstico à parte, não recusa), indice_atual=15/indice_alvo=14 (h=1,0714,
    # LEGAL: atual > alvo) -> rentabilidade pós = 10% x 1,0714 = 10,71% ainda abaixo de g=12% ->
    # RiR = g/rentab = 112% > 100% -> MESMO alerta que o vetor antigo disparava. VERIFICADO por
    # execução direta da CLI do motor (justos.py degrau) antes de entrar aqui.
    v.append(_problema_degrau(
        {"g": 12.0, "roe": 10.0, "ke": 14.0, "n": 10, "tv": "gordon", "roe_tv": 15.0, "gp": 5.0},
        {"indice_atual": 15.0, "indice_alvo": 14.0, "anos": 4, "perfil_transicao": "rampa",
         "vpa": 25.0, "fx": 1.0}, m_valor=100.0))

    # 11. Recusa de domínio — ke = -150% (<= -100%): avaliar_dominios_cli recusa ANTES de
    # qualquer handler (mesma família de recusa que _bloco_diag já exercita para firm/equity sem
    # degrau); aqui cobre as DUAS pernas do degrau ao mesmo tempo (a perna P/L e o handler degrau
    # leem o MESMO 'ke' de premissas).
    v.append(_problema_degrau(
        {"g": 10.0, "roe": 18.0, "ke": -150.0, "n": 10, "tv": "gordon", "roe_tv": 15.0, "gp": 5.0},
        {"indice_atual": 15.0, "indice_alvo": 10.0, "anos": 4, "perfil_transicao": "rampa",
         "vpa": 25.0, "fx": 1.0}, m_valor=100.0))

    # ---- F4 (onda de correção da revisão final): pinos das 11 mutações sobreviventes ----
    # Nenhuma delas precisou mudar avaliar.py/motor_espelho.js — o código de produção já estava
    # certo (a revisão MUTOU o código, testou, restaurou); faltava só o vetor que discrimina.

    # 12. MW1/MJ1 (fx omitido) — TODA fixture/teste de degrau até aqui usa fx=1.0, onde omitir o fx
    # na chamada (avaliar.py:391) ou aplicar o fx no espelho (motor_espelho.js:1523) é invariante
    # (divide por 1.0 de qualquer jeito). Vetor com fx != 1 discrimina: o exemplo LITERAL do
    # SKILL.md do vendor (`vendor/multiplos-justos/SKILL.md:265`), com `--fx 5.115` do colchete
    # opcional que test_valuation_degrau.py (Task 1) deixou de fora de propósito — aqui entra.
    v.append(_problema_degrau(
        {"g": 12.0, "roe": 20.0, "ke": 20.0, "n": 10, "tv": "gordon", "roe_tv": 20.0, "gp": 6.5},
        {"indice_atual": 19.3, "indice_alvo": 14.0, "anos": 4, "perfil_transicao": "rampa",
         "vpa": 29.11, "fx": 5.115}, m_valor=100.0))

    # 13. MW2/MJ2 (default do perfil de transição -> 'pontual') — TODA fixture até aqui declara
    # 'perfil_transicao' explicitamente, e o próprio harness (`_avaliar_degrau`, abaixo) reinjetava
    # '.get("perfil_transicao", "rampa")" ao montar o caso mínimo, mascarando a omissão: mesmo um
    # problema sem a chave chegava em `precificar_degrau`/`precificarDegrau` com a chave JÁ presente
    # (= 'rampa'), nunca exercitando o DEFAULT de verdade daquelas duas funções
    # (`avaliar.py:389`/`motor_espelho.js:1605`). Corrigido: `_avaliar_degrau` agora só inclui
    # 'perfil_transicao' no caso quando o problema declara — este vetor, de propósito, não declara.
    v.append(_problema_degrau(
        b, {"indice_atual": 15.0, "indice_alvo": 10.0, "anos": 4,
            "vpa": 25.0, "fx": 1.0}, m_valor=100.0))

    # 14. MJ11 (sem `dominioCliRecusa` na porta nova do espelho, `precificarDegrau`,
    # motor_espelho.js:1544) — o problema 11/123 (ke=-150%) já recusa mesmo SEM aquela guarda,
    # porque `pe()`/`ev_nopat()` (o NÚCLEO) já devolvem NaN para ke <= -100% independentemente —
    # não discrimina a ausência da guarda. `gp` é INERTE sob tv='convergencia' (nenhuma fórmula do
    # núcleo o lê — ver justos.py:248-251) — sem a guarda explícita (que espelha
    # `avaliar_dominios_cli`, justos.py, rodando ANTES de qualquer handler), um gp=-150% (<=-100%)
    # sob convergencia NÃO produziria NaN nenhum no espelho, e o "laboratório" mostraria um preço
    # onde o motor de verdade recusa (rc=2, "--gp deve ser > -100%") — VERIFICADO por execução
    # direta da CLI. Mesma classe do F2 da 4C.
    v.append(_problema_degrau(
        {"g": 10.0, "roe": 18.0, "ke": 14.0, "n": 10, "tv": "convergencia", "gp": -150.0},
        {"indice_atual": 15.0, "indice_alvo": 10.0, "anos": 4, "perfil_transicao": "rampa",
         "vpa": 25.0, "fx": 1.0}, m_valor=100.0))

    # 15. MJ4 (fronteira do ALERTA com `>=` em vez de `>`, motor_espelho.js:1525) — o motor compara
    # `r2 > max(2*custo, 0.30)`. Vetor desenhado para bater EXATO na igualdade usando só frações
    # binárias exatas (roe=25%=0.25, ke=25%=0.25, h=2.0 -> r2=0.5=2*0.25=max(...)), sem ruído de
    # arredondamento de ponto flutuante — VERIFICADO por execução direta (r2 == thresh bit a bit,
    # niveis[0] sem 'ALERTA'). g=10% fica bem abaixo de r2=50% para não also disparar ALERTA_RiR
    # (isolando a fronteira que este problema testa).
    v.append(_problema_degrau(
        {"g": 10.0, "roe": 25.0, "ke": 25.0, "n": 10, "tv": "gordon", "roe_tv": 20.0, "gp": 5.0},
        {"indice_atual": 20.0, "indice_alvo": 10.0, "anos": 4, "perfil_transicao": "rampa",
         "vpa": 25.0, "fx": 1.0}, m_valor=100.0))

    # 16. MJ5 (fronteira do ALERTA_RiR com `>=` em vez de `>`, motor_espelho.js:1528) — o motor
    # compara `g / r2 > 1`. Vetor com roe=8%, h=1.5 (indice_atual=15/indice_alvo=10) -> r2=12%
    # EXATO igual a g=12% (VERIFICADO: g/r2 == 1.0 bit a bit) — niveis[0] sem 'ALERTA_RiR'. ke=14%
    # mantém max(2*ke,0.30)=0.30 bem acima de r2=12%, isolando a fronteira (sem também disparar
    # ALERTA).
    v.append(_problema_degrau(
        {"g": 12.0, "roe": 8.0, "ke": 14.0, "n": 10, "tv": "gordon", "roe_tv": 15.0, "gp": 5.0},
        {"indice_atual": 15.0, "indice_alvo": 10.0, "anos": 4, "perfil_transicao": "rampa",
         "vpa": 25.0, "fx": 1.0}, m_valor=100.0))

    # 17. Onda de correção da revisão final da 5C (F1): divergência de base DENTRO do limiar da
    # integração (`avaliar._LIMIAR_DIVERGENCIA_DE_BASE_PCT`). Todo problema precificado acima tem
    # |divergencia_de_base_%| acima dele (16,4; 25,0; -10,0; -50,0; -60,0; -77,3) — sem este, a
    # chave `degrau_divergencia_de_base` acenderia em todos, e nem a paridade nem a cobertura
    # discriminariam o limiar (um espelho que a acendesse SEMPRE passaria). Mesmo vetor e mesmos
    # índices dos problemas 3-5 (h=1,5, m=100), com vpa=28,9: ROE·VPA = 18% × 28,9 = 5,202 contra
    # LPA = 500/100 = 5 — divergência ≈ +4,03%, logo abaixo do limiar. VERIFICADO rodando o
    # wrapper (`avaliar_python`) antes de entrar aqui.
    v.append(_problema_degrau(
        b, {"indice_atual": 15.0, "indice_alvo": 10.0, "anos": 4, "perfil_transicao": "rampa",
            "vpa": 28.9, "fx": 1.0}, m_valor=100.0))

    return v


def gerar() -> list[dict]:
    """A lista completa de problemas, determinística — mesma disciplina de
    `vetores_paridade.gerar()`: `random.Random(SEMENTE_SOLVER)` nasce AQUI
    DENTRO, nunca uma instância de módulo reaproveitada, para que
    `gerar() == gerar()` valha trivialmente e o CLI (processo novo)
    reproduza a fixture commitada byte a byte.

    Os problemas de wrapper (`_bloco_wrapper`, task 3), de rampa (`_bloco_rampa`, fatia C task 1),
    de diagnóstico (`_bloco_diag`, fatia C task 2), de degrau (`_bloco_degrau`, fatia D task 2) e
    de conservação de capital (`_bloco_conservacao`, fatia 5F task 3) vêm SEMPRE por último, nessa ordem, depois dos 41 de solver — nunca intercalados. Isso não é
    regra da metodologia, é o que mantém `tests/test_paridade_solver_js.py` (task 2, imutável por
    regra da fatia B) alinhado por posição com os IDs que ele já conhece; a fixture inteira
    permanece uma lista única, um gerador único, como o brief da task 3 pediu e esta task
    preserva."""
    rng = random.Random(SEMENTE_SOLVER)
    problemas = (_bloco_patologico() + _bloco_aleatorio(rng) + _bloco_wrapper() + _bloco_rampa()
                + _bloco_diag() + _bloco_degrau() + _bloco_conservacao())
    for i, problema in enumerate(problemas):
        problema["id"] = i
    return problemas


# Todo resultado de tipo "alvo"/"grade1d"/"grade2d" carrega estes três campos
# do shape do SOLVER, vazios — não é o shape natural desses três tipos (que
# só têm "alvo" ou "celulas"), é compatibilidade retroativa deliberada:
# `tests/test_paridade_solver_js.py` (task 2, imutável por regra desta task)
# lê a fixture INTEIRA sem filtrar por `tipo` e indexa `a["raizes"]`/
# `a["tangenciais"]`/`a["identificacao"]` direto (sem `.get`) em todo item —
# sem estes três campos aqui, aquele harness levantaria `KeyError` assim que
# alcançasse um item de wrapper misturado na mesma fixture. `zip`/`any` até
# tolerariam alguns desses acessos por short-circuit ou por parada antecipada
# do iterador mais curto, mas o comprehension de conjunto de
# `test_fixture_cobre_o_que_discrimina` (identificacao) percorre a lista
# INTEIRA sem short-circuit — por isso o preenchimento é incondicional, não
# uma otimização best-effort. O espelho JS carrega o mesmo preenchimento, com
# o mesmo comentário (`CAMPOS_SOLVER_VAZIOS`, motor_espelho.js) — os dois
# lados precisam concordar, porque aquele harness compara os dois.
_CAMPOS_SOLVER_VAZIOS = {"raizes": [], "tangenciais": [], "identificacao": None}


def _avaliar_solver(problema: dict) -> dict:
    """Um problema `tipo: "solver"` — corpo original de `avaliar_python`
    (task 2), extraído sem mudança de comportamento para virar um dos ramos
    de despacho por `tipo` (task 3). Monta `f` do mesmo jeito que o
    subcomando `rev` do vendor (justos.py, bloco do cmd 'rev'):
    `f(x) = fn(**{**args, resolver: x}) - alvo`, `mult(x) = f(x) + alvo`
    (NÃO uma chamada fresca a `fn` — `mult = lambda x: f(x) + M` no vendor é
    literal, e (fn(x)-alvo)+alvo não é sempre bit-a-bit igual a fn(x); a
    tarefa exige paridade em TAU=1e-12 e este é exatamente o tipo de desvio
    de ponto flutuante que uma "simplificação" equivalente introduziria em
    silêncio).

    `completo=True` roda `solve_full` (raízes + tangenciais, `ref=alvo`,
    `tang_rel` no default do vendor, 1e-4); `completo=False` roda `solve`
    (só raízes) e devolve `tangenciais: []`. `identificacao` roda sobre a
    PRIMEIRA raiz (a lista já vem ordenada de `_dedupe_roots`) com
    `tol=0.01`; `None` quando não há raiz — o mesmo shape que
    `motor_espelho.js` promete devolver.
    """
    fn = _DESPACHO[problema["fn"]]
    resolver = problema["resolver"]
    alvo = problema["alvo"]

    def f(x, fn=fn, resolver=resolver, args=problema["args"], alvo=alvo):
        return fn(**{**args, resolver: x}) - alvo

    def mult(x, f=f, alvo=alvo):
        return f(x) + alvo

    if problema.get("completo"):
        raizes, tangenciais = solve_full(f, problema["lo"], problema["hi"], problema["steps"], ref=alvo)
    else:
        raizes, tangenciais = solve(f, problema["lo"], problema["hi"], problema["steps"]), []

    ident = identificacao(mult, raizes[0], alvo, _TOL_IDENTIFICACAO) if raizes else None

    return {
        "id": problema["id"],
        "raizes": raizes,
        "tangenciais": [{"x": t["x"], "residuo": t["residuo"]} for t in tangenciais],
        "identificacao": ident,
    }


def _caso_minimo_grade(args: dict) -> dict:
    """Caso MÍNIMO para chamar `grade_1d`/`grade_2d` direto — só os campos
    que essas duas funções de fato leem (ver docstrings delas em
    `sensibilidades.py`): rota, ações diluídas, métrica-base, moeda e o vetor
    central de premissas do cenário-alvo. NÃO passa por `caso.validar()` —
    `grade_1d`/`grade_2d` documentam que assumem essa validação já feita por
    quem carregou o caso, e não a repetem; um `caso.json` de verdade exigiria
    âncora/triângulo por cenário, teto de células etc., nenhum dos quais
    `grade_1d`/`grade_2d` de fato leem (só ECOAM `spec["triangulo"]` de volta
    na saída — daí o `triangulo` de preenchimento abaixo, em
    `_spec_triangulo`, nunca lido por conta nenhuma)."""
    return {
        "rota": args["rota"],
        "acoes_diluidas": args["acoes"],
        "metrica_base": args["metrica"],
        "moeda": args.get("moeda"),
        "cenarios": {_NOME_CENARIO: {"premissas": args["premissas"]}},
    }


def _spec_triangulo(rota: str) -> dict:
    """Triângulo g = RiR x retorno de PREENCHIMENTO — `grade_1d`/`grade_2d`
    só ECOAM `spec["triangulo"]` na saída (ver `_caso_minimo_grade`), nunca
    leem por dentro; não precisa ser uma permutação válida em torno das
    premissas variadas por ESTA grade especificamente, só existir."""
    retorno = "roic" if rota == "firm" else "roe"
    return {"inputs": ["g", retorno], "output": "rir"}


def _avaliar_alvo(problema: dict) -> dict:
    """Um problema `tipo: "alvo"` — chama `reversa.alvo_de_mercado` de
    verdade (não reimplementa a conta); devolve só `["valor"]` (o número),
    não `["algebra"]`/`["base"]` (prosa de auditoria, fora do que a
    calibragem desta task pede para testar — ver task-4b-3-brief.md)."""
    args = problema["args"]
    caso = {
        "rota": args["rota"],
        "preco": {"valor": args["preco"]},
        "acoes_diluidas": args["acoes"],
        "metrica_base": args["metrica"],
    }
    resultado = alvo_de_mercado(caso, _NOME_CENARIO, args["nd_efetivo"])
    return {"id": problema["id"], "alvo": resultado["valor"], **_CAMPOS_SOLVER_VAZIOS}


def _avaliar_grade1d(problema: dict) -> dict:
    """Um problema `tipo: "grade1d"` — chama `sensibilidades.grade_1d` de
    verdade. `celulas` reduz cada ponto de `resultado["pontos"]` a
    `{x, valor, multiplo}` — sem `diag` (dedup de diagnóstico, D5 do plano:
    não vai para o espelho nem para este harness)."""
    args = problema["args"]
    caso = _caso_minimo_grade(args)
    spec = {"premissa": args["premissa"], "pontos": args["pontos"],
            "triangulo": _spec_triangulo(args["rota"])}
    resultado = grade_1d(caso, _NOME_CENARIO, spec, args["nd_efetivo"])
    celulas = [{"x": p["x"], "valor": p["valor"], "multiplo": p["multiplo"]}
               for p in resultado["pontos"]]
    return {"id": problema["id"], "celulas": celulas, **_CAMPOS_SOLVER_VAZIOS}


def _avaliar_grade2d(problema: dict) -> dict:
    """Um problema `tipo: "grade2d"` — chama `sensibilidades.grade_2d` de
    verdade. `celulas` preserva a forma linha x coluna de
    `resultado["celulas"]` (`celulas[i][j]` = `pontos_y[i]` x `pontos_x[j]`,
    a MESMA orientação que `sensibilidades.grade_2d` documenta), reduzindo
    cada célula a `{x, y, valor, multiplo}` — sem `diag`, mesma razão de
    `_avaliar_grade1d`."""
    args = problema["args"]
    caso = _caso_minimo_grade(args)
    spec = {"premissa_x": args["premissa_x"], "pontos_x": args["pontos_x"],
            "premissa_y": args["premissa_y"], "pontos_y": args["pontos_y"],
            "triangulo": _spec_triangulo(args["rota"])}
    resultado = grade_2d(caso, _NOME_CENARIO, spec, args["nd_efetivo"])
    celulas = [[{"x": c["x"], "y": c["y"], "valor": c["valor"], "multiplo": c["multiplo"]}
                for c in linha]
               for linha in resultado["celulas"]]
    return {"id": problema["id"], "celulas": celulas, **_CAMPOS_SOLVER_VAZIOS}


def _avaliar_rampa(problema: dict) -> dict:
    """Um problema `tipo: "rampa"` (item 4, fatia C, task 1) — chama
    `avaliar.precificar_rampa` de verdade (o lado Python da paridade é o WRAPPER, não o motor
    direto — mesma razão de `_avaliar_alvo`/`_avaliar_grade1d`/`_avaliar_grade2d`, e mesma razão
    pela qual esta fatia não reaproveita `rampa_bifasica`/`justos.py` diretamente).

    `MotorFalhou` — subprocesso do motor saindo com código != 0 (inclui um `ValueError` cru
    dentro de `rampa_bifasica`, sem captura nenhuma no `main()` do motor) OU um campo não-finito
    virando `null` no JSON e recusado por `_exigir_valor` (ex.: `EV/EBITDA0` quando a fase 2, sob
    'gordon', devolve NaN) — vira `{"recusado": True}`, SEM `multiplo`/`valor`/`saida`/`avisos`: o
    mesmo shape que `motor_espelho.js:precificarRampa` promete devolver.

    `saida` filtra a saída CRUA do motor (primeiro retorno de `precificar_rampa`) para só os
    campos de `CAMPOS_RAMPA` presentes, com `rir_fase1_%` sem a chave 'nota' (texto estático, fora
    do escopo desta fatia — ver Fora do escopo do plano). `avisos` é a lista, EM ORDEM, dos nomes
    de `AVISOS_RAMPA` presentes na saída crua — não a prosa (mesma fora-do-escopo).

    `rf` (item 4, fatia C, task 2): `args.get("rf")` — `None` para todo problema anterior a esta
    task (que nunca declarava a chave) e para os que declaram `"rf": None` explícito; um valor
    ativa `aviso_gp` dentro de `precificar_rampa` -> `motor.rodar` -> handler `rampa` do motor
    congelado, na MESMA condição que `motor_espelho.js:precificarRampa` espelha (ver o comentário
    lá para o achado sobre o alias 'spread')."""
    args = problema["args"]
    try:
        saida_motor, valor, _algebra, multiplo = precificar_rampa(
            args["premissas"], args["nd_efetivo"], args["acoes"], args["moeda"],
            rf=args.get("rf"))
    except MotorFalhou:
        return {"id": problema["id"], "recusado": True, **_CAMPOS_SOLVER_VAZIOS}

    saida = {}
    for campo in CAMPOS_RAMPA:
        if campo not in saida_motor:
            continue
        if campo == "rir_fase1_%":
            saida[campo] = {k: v for k, v in saida_motor[campo].items() if k != "nota"}
        else:
            saida[campo] = saida_motor[campo]
    avisos = [a for a in AVISOS_RAMPA if a in saida_motor]

    return {"id": problema["id"], "recusado": False, "multiplo": multiplo, "valor": valor,
            "saida": saida, "avisos": avisos, **_CAMPOS_SOLVER_VAZIOS}


def _avaliar_diag(problema: dict) -> dict:
    """Um problema `tipo: "diag"` (item 4, fatia C, task 2) — chama `motor.rodar` de verdade,
    SEM escala (só a lista `diagnosticos` importa; não há preço nem múltiplo para ler aqui). É
    AINDA o caminho do wrapper — mesmo `argv_para`, mesmo subprocesso do motor congelado, mesmo
    colapso null->ausência — nunca `diag_firm`/`diag_eq` importados direto: é o vocabulário de
    premissas do CASO (`PREMISSAS_FIRM`/`PREMISSAS_EQUITY`, `caso.py`) que decide quais entradas
    de `coerencia_vetor` são alcançáveis, não a assinatura mais ampla de `diag_firm`/`diag_eq`
    (que aceita `--roe`/`--kd`/etc. na CLI, fora do vetor que o wrapper jamais declara — ver
    `flags_coerencia`, justos.py:1710-1728, e o comentário de `_bloco_diag` acima).

    `mensagens` é a lista CRUA que o motor devolve em `saida["diagnosticos"]` — a comparação por
    prefixo (`_classificar`, tests/test_paridade_wrapper_js.py) é dos harnesses, não deste
    módulo, que não sabe que `diagnosticos_chaves.json` existe (mesma disciplina de
    `avaliar_python` como um todo: não compara nada contra JS).

    F2 (revisão final, fatia 4C): `motor.rodar` levanta `MotorFalhou` quando o motor recusa por
    domínio (`avaliar_dominios_cli`, ANTES de qualquer handler — g/g1/g2/gp/gtv <= -100%, wacc/ke/
    ku/kd <= -100%, n < 1) — um motor que recusa não chega a computar `diagnosticos` nenhum.
    Captura aqui, devolvendo `mensagens: []`, é o mesmo vocabulário de recusa que `_avaliar_rampa`
    já usa (ver acima) e o que `motor_espelho.js:diagnosticosFirm/diagnosticosEquity` agora também
    devolvem (lista vazia) para o mesmo domínio — sem este catch, uma fixture com um valor de
    diagnóstico fora do domínio derrubaria `avaliar_python` inteiro (exceção não capturada), não
    só o item que a exercita."""
    args = problema["args"]
    try:
        saida = rodar(args["rota"], args["premissas"], None, args["moeda"], rf=args.get("rf"))
    except MotorFalhou:
        return {"id": problema["id"], "mensagens": [], **_CAMPOS_SOLVER_VAZIOS}
    return {"id": problema["id"], "mensagens": saida.get("diagnosticos", []),
            **_CAMPOS_SOLVER_VAZIOS}


# Nome do único cenário do caso mínimo que `_avaliar_degrau` monta — irrelevante para o shape
# comparado (nunca sai em `valor`/`sem_degrau`/`vs_preco`/`degrau`), só precisa bater entre a
# chave de `caso["cenarios"]` e a de `caso["degrau"]["m"]` dentro da MESMA chamada.
_NOME_CENARIO_DEGRAU = "c"


def _avaliar_degrau(problema: dict) -> dict:
    """Um problema `tipo: "degrau"` (Fatia D, Task 2) — chama `avaliar_caso` (avaliar.avaliar) de
    verdade sobre um caso MÍNIMO (rota equity, um cenário só, bloco `degrau` declarado) — o MESMO
    ponto de entrada que `tests/test_valuation_degrau.py` (Task 1) usa para o seu próprio
    teste-âncora, não uma chamada isolada às peças internas (`precificar_degrau`,
    `_aplicar_degrau_ao_cenario`): é o jeito mais fiel de obter, num só lugar, as DUAS pernas que
    o wrapper roda por cenário (a rota P/L — `sem_degrau` — e o handler `degrau`) sem reimplementar
    a composição que `avaliar()` já faz.

    `MotorFalhou` (domínio inválido — `avaliar_dominios_cli`, a mesma família de recusa de
    `_avaliar_rampa`/`_avaliar_diag` acima — ou qualquer campo do motor voltando `null`) vira
    `{"recusado": True}`, sem os outros campos: mesmo shape que
    `motor_espelho.js:precificarDegrau` promete devolver. Como a perna P/L (`precificar_equity`)
    roda ANTES da perna degrau dentro de `avaliar()`, um domínio inválido em `g`/`ke`/`gp`/`n`
    (compartilhados pelas duas pernas) já recusa ali, antes do handler `degrau` sequer rodar.

    ALERTA/ALERTA_RiR: o wrapper real (`_aplicar_degrau_ao_cenario`) copia a PROSA do motor
    verbatim para `resultados.json` — convertida aqui para `True`/ausência (mesma convenção de
    `avisos`/`AVISOS_RAMPA` em `_avaliar_rampa`, acima: só a PRESENÇA importa para o laboratório,
    a prosa é do vendor e fica fora do escopo desta fatia — ver o comentário na seção DEGRAU de
    `motor_espelho.js`).

    F4 (onda de correção da revisão final): `perfil_transicao` só entra no `caso["degrau"]` montado
    abaixo quando o PRÓPRIO problema o declara em `bloco_degrau_args` — antes, `.get(
    "perfil_transicao", "rampa")` reinjetava 'rampa' aqui sempre que a chave estava ausente,
    mascarando a omissão: mesmo um problema sem 'perfil_transicao' chegava em
    `avaliar.precificar_degrau`/`motor_espelho.js:precificarDegrau` com a chave JÁ presente,
    nunca exercitando o DEFAULT de verdade daquelas duas funções (é o mesmo default, 'rampa' —
    mas aplicado por ESTE harness, não pelo wrapper/espelho que a fixture existe para testar).
    Ausente aqui, a chave também fica ausente em `caso["degrau"]`, e o default de
    `precificar_degrau`/`precificarDegrau` roda de verdade — mesma disciplina de 'fx' (linha
    abaixo), que já era omitido corretamente quando ausente do problema."""
    args = problema["args"]
    nome = _NOME_CENARIO_DEGRAU
    bloco_degrau_args = args["bloco_degrau"]
    caso = {
        "companhia": "fixture degrau", "ticker": None, "moeda": "BRL-nominal",
        "data_analise": "2026-01-01",
        "preco": {"valor": args["preco_valor"]},
        "rota": "equity",
        "metrica_base": {"tipo": "LL", "valor": args["metrica_valor"], "fonte": "fixture"},
        "acoes_diluidas": args["acoes"],
        "cenarios": {nome: {"ancora": "fixture", "triangulo": {}, "premissas": args["premissas"]}},
        "degrau": {
            "indice_atual": {"valor": bloco_degrau_args["indice_atual"]},
            "indice_alvo": {"valor": bloco_degrau_args["indice_alvo"]},
            "anos": bloco_degrau_args["anos"],
            **({"perfil_transicao": bloco_degrau_args["perfil_transicao"]}
               if "perfil_transicao" in bloco_degrau_args else {}),
            "vpa": {"valor": bloco_degrau_args["vpa"]},
            "fx": bloco_degrau_args.get("fx"),
            "m": {nome: {"valor": args["m_valor"]}},
        },
    }
    try:
        resultado = avaliar_caso(caso)
    except MotorFalhou:
        return {"id": problema["id"], "recusado": True, **_CAMPOS_SOLVER_VAZIOS}

    cenario = resultado["cenarios"][nome]
    degrau_bruto = cenario["degrau"]
    degrau_saida = {
        "h": degrau_bruto["h"],
        "rentabilidade_pos_%": degrau_bruto["rentabilidade_pos_%"],
        "multiplo": degrau_bruto["multiplo"],
        "multiplo_x_rentab": degrau_bruto["multiplo_x_rentab"],
        "com_transicao": degrau_bruto["com_transicao"],
        "fator_transicao": degrau_bruto["fator_transicao"],
        "perfil_transicao": degrau_bruto["perfil_transicao"],
        "m": degrau_bruto["m"],
        "divergencia_de_base_%": degrau_bruto["divergencia_de_base_%"],
    }
    for chave in ("ALERTA", "ALERTA_RiR"):
        if chave in degrau_bruto:
            degrau_saida[chave] = True
    # Fatia 5C, Task 3 (T1/T3): as CHAVES que o wrapper passou a publicar para os dois alertas, na
    # ordem dele — comparadas por igualdade exata com `precificarDegrau`. `.get`, e nao indexacao:
    # um wrapper que deixasse de publicar a lista aparece no harness como divergencia NOMEADA do
    # campo (None contra a lista do espelho), nunca como um KeyError que derrubaria a paridade do
    # degrau inteira sem dizer qual campo sumiu.
    degrau_saida["diagnosticos_chaves"] = degrau_bruto.get("diagnosticos_chaves")

    return {
        "id": problema["id"], "recusado": False,
        "valor": cenario["valor"], "sem_degrau": cenario["sem_degrau"],
        "vs_preco": {"upside": cenario["vs_preco"]["upside"]},
        "degrau": degrau_saida,
        **_CAMPOS_SOLVER_VAZIOS,
    }


# [5F, Task 3] Conservação de capital (§11.1b). O vetor de `caso_minimo_firm` (EBITDA 1.000, d 20%,
# t 25%, g 5%, ROIC 12% — encargos de 450) contra capitais consumidos dos dois lados do limiar do motor
# (10%): fecha em zero; −2,27% com ΔWC negativo; +9,09% logo abaixo; −11,11% e +13,46% logo acima — um
# limiar de 20% no espelho, ou um sem o módulo, reprova nesses —; −50% bem acima. E um vetor com d, g
# e ROIC diferentes (+9,47%), para o gap não depender só do capex.
_PREMISSAS_CONSERVACAO: dict = dict(g=5.0, roic=12.0, wacc=10.0, n=10, da=20.0, tax=25.0, tv="gordon",
                                    roic_tv=10.0, gp=3.0)

# Os cinco números do bloco que o motor arredonda — comparados por igualdade exata no harness.
CAMPOS_CONSERVACAO: tuple = ("capital_consumido", "encargo_reposicao_d_x_EBITDA",
                             "encargo_crescimento_RiR_x_NOPAT", "gap", "gap_%")


def _problema_conservacao(premissas: dict, ebitda: float, capex_total: float, dwc: float) -> dict:
    return {"id": 0, "tipo": "conservacao",
            "args": {"premissas": premissas, "ebitda": ebitda, "capex_total": capex_total, "dwc": dwc}}


def _bloco_conservacao() -> list[dict]:
    v = [_problema_conservacao(dict(_PREMISSAS_CONSERVACAO), 1000.0, capex, dwc)
         for capex, dwc in ((430.0, 20.0), (500.0, -60.0), (495.0, 0.0), (405.0, 0.0), (520.0, 0.0),
                            (300.0, 0.0))]
    v.append(_problema_conservacao({**_PREMISSAS_CONSERVACAO, "da": 35.0, "g": 7.0, "roic": 18.0},
                                   2500.0, 1400.0, 90.0))
    return v


def _avaliar_conservacao(problema: dict) -> dict:
    """Um problema `tipo: "conservacao"` (fatia 5F, Task 3) — roda o WRAPPER de verdade:
    `avaliar.precificar_firm` com as flags da conservação de capital (a CLI converte d, t, g e ROIC de
    ponto percentual para fração, e o handler `ev` chama `conservacao_capital`) e
    `avaliar._conservacao_publicada`, o mesmo bloco que `avaliar()` publica. ALERTA vira
    `True`/ausência, a convenção de `_avaliar_degrau`: só a presença importa."""
    args = problema["args"]
    conservacao = {"capex_total": {"valor": args["capex_total"], "fonte": "fixture", "ano_base": "corrente"},
                   "dwc": {"valor": args["dwc"], "fonte": "fixture"}}
    saida, _valor, _algebra, _multiplo = precificar_firm(
        args["premissas"], "EBITDA", args["ebitda"], moeda="BRL-nominal", conservacao=conservacao)
    bloco = _conservacao_publicada(saida, conservacao)
    publicado = {campo: bloco[campo] for campo in CAMPOS_CONSERVACAO}
    if "ALERTA" in bloco:
        publicado["ALERTA"] = True
    publicado["diagnosticos_chaves"] = bloco["diagnosticos_chaves"]
    return {"id": problema["id"], "conservacao": publicado, **_CAMPOS_SOLVER_VAZIOS}


_DESPACHO_POR_TIPO = {
    "solver": _avaliar_solver,
    "alvo": _avaliar_alvo,
    "grade1d": _avaliar_grade1d,
    "grade2d": _avaliar_grade2d,
    "rampa": _avaliar_rampa,
    "diag": _avaliar_diag,
    "degrau": _avaliar_degrau,
    "conservacao": _avaliar_conservacao,
}


def avaliar_python(problemas: list[dict]) -> list[dict]:
    """Avalia cada problema, despachando por `problema["tipo"]` — sete
    ramos, cinco lados Python DIFERENTES: `"solver"` roda o motor CONGELADO
    direto (`_avaliar_solver`, task 2); `"alvo"`/`"grade1d"`/`"grade2d"`
    rodam o WRAPPER de verdade — `reversa.alvo_de_mercado`/
    `sensibilidades.grade_1d`/`grade_2d` (task 3); `"rampa"` (fatia C, task 1)
    roda `avaliar.precificar_rampa`, TAMBÉM o WRAPPER; `"diag"` (fatia C,
    task 2) roda `motor.rodar` direto, ainda o WRAPPER (mesma CLI/subprocesso
    que `precificar_firm`/`precificar_equity` usam por baixo); `"degrau"`
    (fatia D, task 2) roda `avaliar_caso` (avaliar.avaliar) de verdade sobre
    um caso mínimo, TAMBÉM o WRAPPER — nunca uma reimplementação da conta.
    `tipo` desconhecido levanta `KeyError` nomeando o tipo — falha fechada,
    mesma disciplina do despacho por `tipo` do espelho JS.

    Não compara nada contra JS — isso é dos harnesses
    (`tests/test_paridade_solver_js.py`, `tests/test_paridade_wrapper_js.py`).
    Não sabe que JS existe.
    """
    resultados = []
    for problema in problemas:
        tipo = problema["tipo"]
        if tipo not in _DESPACHO_POR_TIPO:
            raise KeyError(f"tipo de problema desconhecido: {tipo!r}")
        resultados.append(_DESPACHO_POR_TIPO[tipo](problema))
    return resultados


def escrever(problemas: list[dict], destino: Path) -> None:
    """Grava `problemas` como JSON determinístico em `destino` — mesma
    receita de `vetores_paridade.escrever` (`indent=2`, `ensure_ascii=False`,
    `\\n` final, `newline="\\n"` para não deixar o Windows traduzir EOL)."""
    texto = json.dumps(problemas, indent=2, ensure_ascii=False) + "\n"
    Path(destino).write_text(texto, encoding="utf-8", newline="\n")


def main(argv: list[str] | None = None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(
        description="Gera a fixture determinística de problemas de solver Python <-> JS.")
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
