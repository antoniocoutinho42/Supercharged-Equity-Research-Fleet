"""Gerador determinístico dos problemas de solver Python <-> JS (item 4, fatia B, task 2).

Mesmo contrato de forma que `vetores_paridade.py` (fatia A), aplicado a uma
natureza de risco diferente: lá o espelho é forma fechada (uma diferença de
1e-15 permanece 1e-15); aqui o espelho é o SOLVER do motor congelado —
iterativo, e que AMPLIFICA. Este módulo faz duas coisas e nenhuma outra:
`gerar()` produz a lista de problemas (bloco patológico escrito à mão + bloco
aleatório semeado), e `avaliar_python()` roda cada problema contra
`solve`/`solve_full`/`identificacao` do motor congelado
(`vendor/multiplos-justos/scripts/justos.py`, linhas 272-347) e devolve o
resultado correspondente. NÃO compara nada contra um espelho — a comparação é
do harness, `tests/test_paridade_solver_js.py` — e NÃO conhece JavaScript:
este arquivo nunca importa nem invoca `node`.

A fixture emitida por `escrever()` é commitada em
`tests/fixtures/vetores_solver.json`; o harness regenera e compara byte a
byte, mesma disciplina da 4A.

Formato de um problema (contrato do brief task-4b-2, seção "Interfaces"):
    {"id": int, "tipo": "solver", "resolver": "<nome da premissa>",
     "fn": "ev_nopat"|"ev_ebitda"|"pe", "args": {...}, "alvo": float,
     "lo": float, "hi": float, "steps": 800, "completo": bool}
`args` traz o vetor SEM a premissa que está sendo resolvida — o solver a
injeta sob a chave `resolver` (`fn(**{**args, resolver: x})`), o mesmo jeito
que o subcomando `rev` do vendor monta `f` (justos.py, bloco do cmd 'rev':
`def f(x): ... return base_f(gg, rr, kk, a.n, kk2) - M`).
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

SEMENTE_SOLVER = 20260826

_DESPACHO = {"ev_nopat": ev_nopat, "ev_ebitda": ev_ebitda, "pe": pe}

# tol=0.01 é o default do vendor (`identificacao(mult_fn, x, M, tol=0.01)`) e
# também o que o subcomando `rev` da CLI usa sempre que `--tol` não é
# declarado (`tol = (a.tol or 1.0) / 100.0`, justos.py). Este módulo não
# expõe `tol` como campo do problema — nenhum consumidor desta fixture
# precisa de outro valor, e inventar o campo só para nunca variá-lo seria
# complexidade sem uso (calibragem do brief).
_TOL_IDENTIFICACAO = 0.01


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


def gerar() -> list[dict]:
    """A lista completa de problemas, determinística — mesma disciplina de
    `vetores_paridade.gerar()`: `random.Random(SEMENTE_SOLVER)` nasce AQUI
    DENTRO, nunca uma instância de módulo reaproveitada, para que
    `gerar() == gerar()` valha trivialmente e o CLI (processo novo)
    reproduza a fixture commitada byte a byte."""
    rng = random.Random(SEMENTE_SOLVER)
    problemas = _bloco_patologico() + _bloco_aleatorio(rng)
    for i, problema in enumerate(problemas):
        problema["id"] = i
    return problemas


def avaliar_python(problemas: list[dict]) -> list[dict]:
    """Avalia cada problema no motor Python congelado, montando `f` do mesmo
    jeito que o subcomando `rev` do vendor (justos.py, bloco do cmd 'rev'):
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

    Não compara nada contra JS — isso é do harness
    (`tests/test_paridade_solver_js.py`). Não sabe que JS existe.
    """
    resultados = []
    for problema in problemas:
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

        resultados.append({
            "id": problema["id"],
            "raizes": raizes,
            "tangenciais": [{"x": t["x"], "residuo": t["residuo"]} for t in tangenciais],
            "identificacao": ident,
        })
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
