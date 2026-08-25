# Solver de reversa e sensibilidades no espelho — Plano de Implementação (item 4, fatia B)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Levar ao espelho JS o que falta para o laboratório do item 5 recalcular ao vivo: o solver de reversa do motor congelado (varredura, bissecção, raízes tangenciais, métricas de identificação), o alvo de mercado e o eixo de reversa, e as grades de sensibilidade 1D e 2D — cada peça provada contra o lado Python que ela espelha.

**Architecture:** Duas naturezas diferentes de espelho, e o plano as trata diferente. O **solver é código do motor congelado** (`justos.py` 272–347) e sua paridade é contra o motor. O **alvo, o eixo e as grades são código do wrapper** (`reversa.py`, `sensibilidades.py`) e a paridade é contra o wrapper. Confundir as duas produziria um espelho fiel a nada. Uma segunda fixture, de problemas de solver e de grade, estende o protocolo da 4A sem tocar na primeira.

**Tech Stack:** Python 3.12+ (stdlib pura), Node.js (v24 local, v22 no CI), pytest.

## Global Constraints

- **Fonte de verdade:** `docs/desenho-arquitetura-v4.md`, Seções 8.4, 13 e 18.
- **Regra inviolável 1:** a matemática de valuation vem do motor congelado; o único JS de valuation admitido é o espelho verificado por paridade. Esta fatia amplia esse espelho — e amplia junto a prova.
- **Falha fechada.** Divergência reprova. Sem node, os testes PULAM com razão explícita nomeando o CI.
- **Tolerância medida, nunca escolhida.** Como na 4A: o teste mede, imprime e guarda a folga. `FOLGA_MINIMA = 100` é o piso já estabelecido, com a medição da 4A (2.073e-15, folga 482×) registrada ao lado.
- **Não tocar no vendor.** `vendor/multiplos-justos/**` é read-only, verificado por sha256.
- Determinismo: as fixtures são reproduzíveis byte a byte a partir dos geradores.
- stdlib pura no Python; **zero dependências npm** no JS.
- **`PYTHONUTF8=1`** em tudo que imprime saída do motor; **`sys.dont_write_bytecode = True` antes de qualquer import em processo do motor** — um `.pyc` na árvore congelada quebra dois testes de integridade.
- Commits: conventional commits em PT-BR, trailer `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`.
- Não tocar em `skills/er-motor-k3/`, `skills/er-dados-openbb/`, `skills/er-relatorio-html/`.

## Fora do escopo desta fatia

`degrau`, `rampa` e os predicados numéricos de diagnóstico (fatia 4C). O relatório, o banner e a UI (item 5). Grades sobre a rota `rampa` — a rota só entra no espelho na 4C, então uma grade sobre ela não tem como existir aqui. Não antecipe nada.

## O risco desta fatia é diferente do da 4A — e foi medido

Na 4A o espelho era forma fechada: uma diferença de 1e-15 permanecia 1e-15. **O solver é iterativo, e amplifica.** Uma diferença minúscula em `f` pode inverter a comparação de sinal `y0 * y1 <= 0` num ponto da varredura e produzir **uma raiz a mais ou a menos** — divergência discreta, não numérica, que uma comparação de valores não pega.

Medido pelo controlador antes deste plano, perturbando `f` em 1e-15 relativo e re-resolvendo:

| caso | raízes | deslocamento relativo | identificação |
|---|---|---|---|
| `gordon`, resolver `w`, alvos 8.0 a 13.3 | contagem **estável** em todos | 0 a 1.5e-15 | forte |
| `book`, resolver `roic` perto da neutralidade | contagem **estável** em todos | 2.7e-15 a 5.1e-15 | forte (largura 2.6–4.4%) |
| `gordon` perto do teto, raízes tangenciais | contagem estável (1/1 raízes, 0/0 tangenciais) | — | — |

Conclusão que o plano adota: o solver é **bem condicionado** nas regiões amostradas, o deslocamento da raiz é da ordem do erro do núcleo amplificado ~2 a 3×, e τ estrito serve. Mas a contagem de raízes é comparada **primeiro e exatamente**, porque é ali que a fragilidade moraria se existisse.

**Se alguma vez a contagem divergir, isso é um ACHADO** — o solver é instável naquele ponto e a metodologia quer saber. Reporte com o problema completo; não afrouxe nada.

## Contrato — o que espelhar e de onde

**Do motor congelado** (`vendor/multiplos-justos/scripts/justos.py`), leia e espelhe de lá:

- `_dedupe_roots` — linhas 272–279 · `solve` — 281–297 · `solve_full` — 298–322 · `identificacao` — 323–347.

Como na 4A, este plano **não transcreve as fórmulas**: uma transcrição seria uma terceira cópia capaz de divergir em silêncio. A fonte é o vendor.

**Do wrapper**, leia e espelhe de lá:

- `skills/er-valuation/scripts/reversa.py` — `alvo_de_mercado` e a montagem do argv por eixo (`RESOLVER_POR_EIXO`).
- `skills/er-valuation/scripts/sensibilidades.py` — a construção de célula das grades 1D e 2D.

**Detalhes do solver que um espelho apressado erra:**

1. `solve` avalia `f(lo)` **antes** do laço e reaproveita `y0` entre iterações — não é `f(x0)` recalculado. Reavaliar dá o mesmo número mas dobra o custo e, pior, muda a ordem das chamadas se `f` tiver efeito colateral (não tem, mas a fidelidade é de forma, não só de resultado).
2. A bissecção roda **90 iterações fixas**, sem critério de parada por tolerância. Copie o número.
3. `solve_full` procura tangenciais por **busca ternária de 80 iterações** sobre `|f|`, e só aceita o candidato se `|f(x)| <= tang_rel * max(|ref|, 1e-12)`, com dedupe contra as raízes já achadas **e** contra as tangenciais já aceitas, em ambos os casos com tolerância relativa `1e-3`.
4. `identificacao` usa passo `h = max(|x|, 1e-4) * 1e-4`, diferenças centrais, e **arredonda** os campos de saída (`round(d1, 4)`, `round(d2, 2)`, `round(elast, 3)`, os extremos do intervalo `round(·*100, 3)`, a largura `round(·*100, 1)`). O arredondamento é parte do contrato: compare os campos arredondados, não os brutos. A chave do intervalo é montada com `f'{tol:.0%}'` — com `tol=0.01` sai `intervalo_para_alvo_±1%`.
5. As classes de identificação cortam em `rel < 0.05` (forte) e `rel < 0.20` (moderada). Os textos de nota são parte da saída.

## Decisões de projeto já tomadas — não reabra, implemente

**D1 — Segunda fixture, não extensão da primeira.** Problemas de solver e de grade têm shape próprio (`{id, tipo, ...}`) e vivem em `tests/fixtures/vetores_solver.json`, com gerador próprio. A fixture de valor da 4A e seus testes ficam intactos — exceto pela correção do resíduo (D4).

**D2 — Duas paridades, dois arquivos de teste.** `tests/test_paridade_solver_js.py` compara contra o **motor**; `tests/test_paridade_wrapper_js.py` compara contra o **wrapper**. Um arquivo só esconderia que são garantias de naturezas diferentes.

**D3 — Contagem antes de valor, sempre.** Para raízes: as listas têm de ter o mesmo comprimento **antes** de qualquer comparação numérica; depois, raiz a raiz na ordem (ambos os lados devolvem ordenado). Para tangenciais, idem. Para `identificacao`: a classe (`forte`/`moderada`/`fraca`) tem de bater **exatamente** — ela é uma decisão, não um número, e um espelho que classifique diferente está dizendo outra coisa ao analista mesmo com a raiz certa.

**D4 — Fecha o resíduo da 4A aqui.** A fixture de valor não cobre os aliases `'ic'`/`'spread'` de `tv_canon` nem `tv` ausente, porque `tests/test_vetores_paridade.py` afirma igualdade **estrita** do conjunto de `tv`. Relaxe essa asserção para "contém as três convenções canônicas" e acrescente os vetores. Sem isso um alias transposto no espelho embarca em silêncio.

**D5 — Grades espelham o wrapper, e só as rotas já espelhadas.** `firm` (EBITDA e NOPAT) e `equity`. A dedup de diagnóstico (`diagnosticos_unicos` + índices) é preocupação do artefato estático em Python e **não** vai para o JS — o laboratório mostra valores, não reconstrói o arquivo. Diga isso no comentário da função para que ninguém "complete" depois.

## File Structure

| Arquivo | Responsabilidade |
|---|---|
| `skills/er-valuation/scripts/vetores_solver.py` | Gerar a fixture de problemas de solver e de grade; avaliar o lado Python de cada um |
| `tests/fixtures/vetores_solver.json` | A fixture gerada e commitada |
| `skills/er-valuation/assets/motor_espelho.js` | Ganha o solver espelhado e as funções de reversa/grade (modificado) |
| `tests/test_paridade_solver_js.py` | Paridade do solver contra o motor |
| `tests/test_paridade_wrapper_js.py` | Paridade de alvo, eixo e grades contra o wrapper |
| `skills/er-valuation/scripts/vetores_paridade.py` · `tests/fixtures/vetores_paridade.json` · `tests/test_vetores_paridade.py` | Resíduo da 4A: aliases e `tv` ausente (modificados) |

---

### Task 1: Resíduo da 4A — aliases de convenção e `tv` ausente

Tarefa curta e independente, feita primeiro para que o espelho já esteja coberto nesse flanco antes de crescer.

**Files:**
- Modify: `skills/er-valuation/scripts/vetores_paridade.py`, `tests/fixtures/vetores_paridade.json`, `tests/test_vetores_paridade.py`

- [ ] **Step 1: Afrouxar a asserção estrita e acrescentar as novas**

Em `tests/test_vetores_paridade.py`, troque a igualdade estrita do conjunto de `tv` por conter as três canônicas, e acrescente:

```python
def test_fixture_cobre_os_aliases_legados_de_convencao():
    """tv_canon mapeia 'ic'->'book' e 'spread'->'gordon'. Um alias transposto no
    espelho embarcaria em silencio sem estes vetores."""
    vetores = json.loads(FIXTURE.read_text(encoding="utf-8"))
    tvs = {v["args"].get("tv") for v in vetores}
    assert {"ic", "spread"} <= tvs


def test_fixture_cobre_tv_ausente():
    """Ausente cai no default 'book' do motor — caminho distinto de tv='book'
    explicito no espelho, que resolve o default por presenca da chave."""
    vetores = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert any("tv" not in v["args"] for v in vetores)
```

- [ ] **Step 2: Rodar para ver falhar** — `PYTHONUTF8=1 python -m pytest tests/test_vetores_paridade.py -q`.

- [ ] **Step 3: Acrescentar os vetores ao bloco patológico do gerador**

No mínimo: um `ev_nopat` e um `pe` com `tv: "ic"`; um de cada com `tv: "spread"` (com o `roic_tv`/`roe_tv` e `gp` que o gordon exige); e um de cada **sem a chave `tv`**. Regenere a fixture.

- [ ] **Step 4: Ver passar** · **Step 5: Suíte inteira** · **Step 6: Confirmar que a fixture regenera byte a byte** · **Step 7: Commit** (mensagem sua; o assunto diz que o resíduo da 4A fecha).

---

### Task 2: Solver do motor no espelho

**Files:**
- Create: `skills/er-valuation/scripts/vetores_solver.py`, `tests/fixtures/vetores_solver.json`, `tests/test_paridade_solver_js.py`
- Modify: `skills/er-valuation/assets/motor_espelho.js`

**Interfaces:**
- Produces, no Python: `SEMENTE_SOLVER: int = 20260826`; `gerar() -> list[dict]`; `avaliar_python(problemas) -> list[dict]`; `escrever(problemas, destino)`; CLI `--out`.
- Formato de um problema: `{"id": int, "tipo": "solver", "resolver": "<nome da premissa>", "fn": "ev_nopat"|"ev_ebitda"|"pe", "args": {...}, "alvo": float, "lo": float, "hi": float, "steps": 800, "completo": bool}`. `args` traz o vetor **sem** a premissa que está sendo resolvida; o solver a injeta.
- Resultado de um problema: `{"id": int, "raizes": [float], "tangenciais": [{"x": float, "residuo": float}], "identificacao": {...} | null}` — `identificacao` sobre a primeira raiz quando houver, `null` quando não houver raiz.
- Produces, no JS: `dedupeRaizes(raizes)`, `resolver(f, lo, hi, steps)`, `resolverCompleto(f, lo, hi, steps, ref, tangRel)`, `identificacao(multFn, x, M, tol)`, e `resolverProblema(problema)` que monta `f` a partir de `fn`/`args`/`resolver`/`alvo` e devolve o mesmo shape do Python. `avaliarProblemas(problemas)` para o lote e o CLI.

- [ ] **Step 1: Escrever os testes de paridade (vão falhar)**

`tests/test_paridade_solver_js.py`:

```python
"""Paridade do SOLVER: espelho JS contra o motor congelado.

Naturezas diferentes de risco: o nucleo de valor da 4A e forma fechada e uma
diferenca de 1e-15 permanece 1e-15; o solver e ITERATIVO e amplifica — uma
diferenca minuscula em f pode inverter a comparacao de sinal da varredura e
produzir uma raiz A MAIS OU A MENOS. Por isso a CONTAGEM e comparada primeiro
e exatamente, e so depois os valores.

Medido pelo controlador antes desta fatia, perturbando f em 1e-15 relativo:
contagem estavel em todos os casos amostrados, deslocamento da raiz entre 0 e
5.1e-15 (o erro do nucleo amplificado ~2-3x). Se a contagem divergir alguma
vez, isso e um ACHADO sobre a estabilidade do solver naquele ponto — reporte
o problema completo, nao afrouxe nada.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
ESPELHO = RAIZ / "skills" / "er-valuation" / "assets" / "motor_espelho.js"
FIXTURE = RAIZ / "tests" / "fixtures" / "vetores_solver.json"
sys.path.insert(0, str(RAIZ / "skills" / "er-valuation" / "scripts"))
from vetores_solver import avaliar_python  # noqa: E402

TAU = 1e-12
FOLGA_MINIMA = 100
SEM_NODE = shutil.which("node") is None
RAZAO = "node ausente do PATH — a paridade roda sempre no CI (setup-node)"


def _problemas():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _lado_js():
    r = subprocess.run(["node", str(ESPELHO), str(FIXTURE)],
                       capture_output=True, text=True, encoding="utf-8", timeout=300)
    assert r.returncode == 0, r.stdout + r.stderr
    return {x["id"]: x for x in json.loads(r.stdout)}


def _rel(a, b):
    return abs(a - b) / max(abs(a), 1.0)


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_contagem_de_raizes_bate_exatamente():
    """Divergencia discreta: uma raiz a mais ou a menos nao e erro numerico."""
    probs, js = _problemas(), _lado_js()
    py = avaliar_python(probs)
    fora = [(p["id"], p["resolver"], p["args"], len(a["raizes"]), len(js[p["id"]]["raizes"]))
            for p, a in zip(probs, py) if len(a["raizes"]) != len(js[p["id"]]["raizes"])]
    assert not fora, f"{len(fora)} problemas com contagem divergente; primeiros 3: {fora[:3]}"


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_contagem_de_tangenciais_bate_exatamente():
    probs, js = _problemas(), _lado_js()
    py = avaliar_python(probs)
    fora = [(p["id"], len(a["tangenciais"]), len(js[p["id"]]["tangenciais"]))
            for p, a in zip(probs, py) if len(a["tangenciais"]) != len(js[p["id"]]["tangenciais"])]
    assert not fora, f"{len(fora)} problemas com tangenciais divergentes; primeiros 3: {fora[:3]}"


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_valor_das_raizes_dentro_de_tau():
    probs, js = _problemas(), _lado_js()
    py = avaliar_python(probs)
    piores = []
    for p, a in zip(probs, py):
        b = js[p["id"]]
        if len(a["raizes"]) != len(b["raizes"]):
            continue  # coberto pelo teste de contagem
        for r_py, r_js in zip(a["raizes"], b["raizes"]):
            piores.append((_rel(r_py, r_js), p["id"], p["resolver"], r_py, r_js))
    piores.sort(reverse=True)
    fora = [x for x in piores if x[0] > TAU]
    assert not fora, f"{len(fora)} raizes fora de TAU={TAU}; piores 3: {fora[:3]}"


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_classe_de_identificacao_bate_exatamente():
    """A classe e uma DECISAO, nao um numero: um espelho que classifique
    diferente diz outra coisa ao analista mesmo com a raiz certa."""
    probs, js = _problemas(), _lado_js()
    py = avaliar_python(probs)
    fora = []
    for p, a in zip(probs, py):
        i_py, i_js = a["identificacao"], js[p["id"]]["identificacao"]
        if (i_py is None) != (i_js is None):
            fora.append((p["id"], "presenca", i_py, i_js)); continue
        if i_py is None:
            continue
        if i_py.get("identificacao") != i_js.get("identificacao"):
            fora.append((p["id"], "classe", i_py.get("identificacao"), i_js.get("identificacao")))
    assert not fora, f"{len(fora)} divergencias de identificacao; primeiras 3: {fora[:3]}"


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_campos_arredondados_da_identificacao_batem():
    """O arredondamento faz parte do contrato do motor — compare o arredondado."""
    probs, js = _problemas(), _lado_js()
    py = avaliar_python(probs)
    fora = []
    for p, a in zip(probs, py):
        i_py, i_js = a["identificacao"], js[p["id"]]["identificacao"]
        if not i_py or not i_js or "slope_dM_dx" not in i_py:
            continue
        for campo in ("slope_dM_dx", "curvatura_d2M_dx2", "elasticidade", "largura_relativa_%"):
            if i_py.get(campo) != i_js.get(campo):
                fora.append((p["id"], campo, i_py.get(campo), i_js.get(campo)))
    assert not fora, f"{len(fora)} campos arredondados divergentes; primeiros 3: {fora[:3]}"


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_folga_de_tau_medida_no_solver():
    """A amplificacao do solver e MEDIDA, nao presumida."""
    probs, js = _problemas(), _lado_js()
    py = avaliar_python(probs)
    erros = [_rel(a, b) for p, r in zip(probs, py)
             for a, b in zip(r["raizes"], js[p["id"]]["raizes"])
             if len(r["raizes"]) == len(js[p["id"]]["raizes"])]
    maximo = max(erros, default=0.0)
    if maximo:
        print(f"\nsolver — erro relativo maximo nas raizes: {maximo:.3e} "
              f"(TAU={TAU:.0e}, folga {TAU / maximo:.0f}x)")
    else:
        print("\nsolver — todas as raizes exatas")
    assert maximo < TAU / FOLGA_MINIMA, (
        f"folga encolheu: {maximo:.3e} contra TAU {TAU:.0e}. O solver amplifica o erro "
        "do nucleo; investigue a causa antes de mexer em TAU.")


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_fixture_de_solver_cobre_o_que_promete():
    probs = _problemas()
    py = avaliar_python(probs)
    assert len(probs) >= 80
    assert sum(1 for r in py if len(r["raizes"]) == 0) >= 5, "nenhum caso sem raiz"
    assert sum(1 for r in py if len(r["raizes"]) >= 2) >= 3, "nenhum caso multi-raiz"
    assert sum(1 for r in py if r["tangenciais"]) >= 1, "nenhuma tangencial"
    assert any(p.get("completo") for p in probs), "solve_full nunca exercitado"
    classes = {r["identificacao"]["identificacao"] for r in py
               if r["identificacao"] and "identificacao" in r["identificacao"]}
    assert "forte" in classes
```

- [ ] **Step 2: Rodar para ver falhar** — `ModuleNotFoundError: No module named 'vetores_solver'`.

- [ ] **Step 3: Implementar `vetores_solver.py`**

Bloco patológico à mão + bloco aleatório semeado, mesma disciplina da 4A (instância `random.Random`, nunca o global). O bloco patológico tem de conter, no mínimo: alvo abaixo do mínimo atingível (sem raiz); alvo no interior (raiz única); alvo perto do teto (candidato a tangencial, com `completo: true`); resolver `w`/`ke` e resolver `roic`/`roe` nas três convenções; um caso perto da neutralidade (rentabilidade ≈ custo); e um `hi`/`lo` estreito o bastante para a varredura de 800 passos ser grossa em relação à curvatura.

`avaliar_python` importa `solve`, `solve_full` e `identificacao` do vendor (com `sys.dont_write_bytecode = True` antes do import), monta `f` injetando a premissa resolvida em `args`, e devolve o shape declarado nas Interfaces. Use `solve_full` quando `completo` for verdadeiro e `solve` quando não — devolvendo `tangenciais: []` no segundo caso.

- [ ] **Step 4: Espelhar o solver no JS**

Abra o vendor nas linhas 272–347 e espelhe. Atenção aos cinco detalhes da seção "Contrato": `f(lo)` fora do laço, 90 iterações fixas na bissecção, 80 na ternária, o critério de aceitação da tangencial com os dois dedupes, e os arredondamentos de `identificacao`.

**`round` do Python e `Math.round` do JS não são a mesma função.** Python usa arredondamento bancário (metade para o par) e o JS arredonda metade para cima — e para negativos o JS arredonda para `+∞`. Escreva um helper que reproduza o comportamento do Python e use-o em todos os campos arredondados; o teste `test_campos_arredondados_da_identificacao_batem` compara igualdade exata e vai cobrar isso.

O CLI do espelho passa a despachar por `tipo`: **sem `tipo`** (a fixture de valor da 4A, cujos itens têm `fn` e nada mais) segue o caminho da 4A; `tipo: "solver"` vai para `resolverProblema`; e na Task 3 entram `"alvo"`, `"grade1d"` e `"grade2d"`. Um `tipo` desconhecido **lança** — a mesma disciplina de falha fechada do resto do arquivo, e o CLI já converte exceção em código de saída não-zero. Mantenha o caminho da 4A intacto: a fixture de valor continua passando pelo mesmo binário, e o harness da 4A continua verde sem alteração.

- [ ] **Step 5: Ver passar** · **Step 6: Suíte inteira** · **Step 7: Provar que o harness do solver fica vermelho** — troque as 90 iterações da bissecção por 5, confirme que a paridade reprova nomeando problemas, reverta e confirme verde. Registre as duas saídas. · **Step 8: `git status --short vendor` vazio** · **Step 9: Commit**

---

### Task 3: Alvo, eixo e grades — paridade contra o wrapper

**Files:**
- Modify: `skills/er-valuation/assets/motor_espelho.js`, `skills/er-valuation/scripts/vetores_solver.py`, `tests/fixtures/vetores_solver.json`
- Create: `tests/test_paridade_wrapper_js.py`
- Modify: `.github/workflows/ci.yml`, `skills/er-valuation/SKILL.md`

**Interfaces:**
- Produces, no JS: `alvoDeMercado({rota, preco, acoes, ndEfetivo, metrica})`, `grade1D({rota, premissas, metrica, ndEfetivo, acoes, premissa, pontos, moeda})` e `grade2D({..., premissaX, pontosX, premissaY, pontosY})`. As grades devolvem células com `valor` (preço por ação) e `multiplo`, na mesma orientação do wrapper: `celulas[i][j]` com `i` percorrendo `pontosY` e `j` percorrendo `pontosX`.
- O gerador ganha problemas `tipo: "grade1d"` e `tipo: "grade2d"`, avaliados no lado Python **chamando `sensibilidades.py`**, não reimplementando a grade.

- [ ] **Step 1: Escrever os testes (vão falhar)**

`tests/test_paridade_wrapper_js.py`:

```python
"""Paridade do WRAPPER: alvo de mercado, eixo de reversa e grades.

Natureza diferente da paridade do solver: aqui o lado Python NAO e o motor
congelado, e sim `reversa.py`/`sensibilidades.py`. Um espelho fiel ao motor e
infiel ao wrapper produziria numeros certos no lugar errado — por isso os dois
harnesses sao arquivos separados.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
ESPELHO = RAIZ / "skills" / "er-valuation" / "assets" / "motor_espelho.js"
FIXTURE = RAIZ / "tests" / "fixtures" / "vetores_solver.json"
sys.path.insert(0, str(RAIZ / "skills" / "er-valuation" / "scripts"))
from vetores_solver import avaliar_python  # noqa: E402

TAU = 1e-12
SEM_NODE = shutil.which("node") is None
RAZAO = "node ausente do PATH — a paridade roda sempre no CI (setup-node)"


def _problemas(tipos):
    todos = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return [p for p in todos if p.get("tipo") in tipos]


def _lado_js():
    r = subprocess.run(["node", str(ESPELHO), str(FIXTURE)],
                       capture_output=True, text=True, encoding="utf-8", timeout=300)
    assert r.returncode == 0, r.stdout + r.stderr
    return {x["id"]: x for x in json.loads(r.stdout)}


def _rel(a, b):
    return abs(a - b) / max(abs(a), 1.0)


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_alvo_de_mercado_bate_nas_duas_rotas():
    probs = _problemas({"alvo"})
    assert probs, "fixture sem problemas de alvo"
    py, js = avaliar_python(probs), _lado_js()
    fora = [(p["id"], p["args"]["rota"], a["alvo"], js[p["id"]]["alvo"])
            for p, a in zip(probs, py) if _rel(a["alvo"], js[p["id"]]["alvo"]) > TAU]
    assert not fora, f"alvo divergente: {fora[:3]}"
    assert {p["args"]["rota"] for p in probs} >= {"firm", "equity"}
    assert any(p["args"].get("nd_efetivo", 0) < 0 for p in probs), "nenhum caso com caixa liquido"


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_grades_tem_a_orientacao_do_wrapper():
    """Grade NAO quadrada de proposito: a fatia 3C descobriu que uma 3x3
    esconde uma transposicao de eixos — o teste passava com os eixos trocados."""
    probs = _problemas({"grade2d"})
    assert probs, "fixture sem grades 2D"
    js = _lado_js()
    nao_quadradas = [p for p in probs
                     if len(p["args"]["pontos_x"]) != len(p["args"]["pontos_y"])]
    assert nao_quadradas, "toda grade 2D e quadrada — transposicao ficaria invisivel"
    for p in nao_quadradas:
        g = js[p["id"]]
        px, py_ = p["args"]["pontos_x"], p["args"]["pontos_y"]
        assert len(g["celulas"]) == len(py_)
        assert all(len(linha) == len(px) for linha in g["celulas"])
        for i, linha in enumerate(g["celulas"]):
            for j, cel in enumerate(linha):
                assert cel["x"] == px[j] and cel["y"] == py_[i]


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_valor_e_multiplo_de_cada_celula_dentro_de_tau():
    probs = _problemas({"grade1d", "grade2d"})
    assert probs, "fixture sem grades"
    py, js = avaliar_python(probs), _lado_js()
    piores = []
    for p, a in zip(probs, py):
        b = js[p["id"]]
        cel_py = a["celulas"] if p["tipo"] == "grade1d" else [c for lin in a["celulas"] for c in lin]
        cel_js = b["celulas"] if p["tipo"] == "grade1d" else [c for lin in b["celulas"] for c in lin]
        assert len(cel_py) == len(cel_js), f"contagem de celulas difere no problema {p['id']}"
        for cp, cj in zip(cel_py, cel_js):
            for campo in ("valor", "multiplo"):
                if cp[campo] is None or cj[campo] is None:
                    assert (cp[campo] is None) == (cj[campo] is None), (p["id"], campo)
                    continue
                piores.append((_rel(cp[campo], cj[campo]), p["id"], campo, cp[campo], cj[campo]))
    piores.sort(reverse=True)
    fora = [x for x in piores if x[0] > TAU]
    assert not fora, f"{len(fora)} celulas fora de TAU; piores 3: {fora[:3]}"


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_celula_central_reproduz_o_caso_base():
    """Regra da metodologia: a celula na premissa do caso-base bate com a manchete."""
    probs = _problemas({"grade1d"})
    py, js = avaliar_python(probs), _lado_js()
    checados = 0
    for p, a in zip(probs, py):
        central = p["args"]["premissas"].get(p["args"]["premissa"])
        if central is None or central not in p["args"]["pontos"]:
            continue
        k = p["args"]["pontos"].index(central)
        assert _rel(a["celulas"][k]["valor"], js[p["id"]]["celulas"][k]["valor"]) <= TAU
        checados += 1
    assert checados >= 1, "nenhuma grade inclui o ponto central — a regra nao foi exercitada"
```

- [ ] **Step 2: Rodar para ver falhar** · **Step 3: Implementar** · **Step 4: Ver passar**

Ao implementar as grades no JS, lembre de D5: a dedup de diagnóstico **não** vai para o espelho. Deixe isso escrito no comentário da função.

- [ ] **Step 5: CI** — acrescente as duas fixtures novas ao passo de paridade que já existe (ele roda antes do `pytest`, como tripwire).

- [ ] **Step 6: `SKILL.md`** — uma frase dizendo que o espelho agora cobre solver e grades além do núcleo, e que a paridade tem dois arquivos porque são garantias contra fontes diferentes (motor × wrapper). Não reproduza metodologia.

- [ ] **Step 7: Suíte inteira** · **Step 8: Commit**

---

## Verificação final da fatia 4B

- [ ] `PYTHONUTF8=1 python -m pytest tests/ -q` — verde
- [ ] Os quatro harnesses imprimem seus máximos medidos (`-s`), e as folgas ficam registradas
- [ ] Contagem de raízes e de tangenciais bate em 100% dos problemas
- [ ] Falsificabilidade provada no solver (bissecção truncada) e nas grades (eixos transpostos), com reversão byte a byte
- [ ] As duas fixtures regeneram byte a byte
- [ ] `git status --short vendor` vazio; nenhum `.pyc` sob `vendor/`
- [ ] O espelho continua carregando num contexto bare (sem `module`/`require`/`process`) com a superfície pública completa — a garantia da 4A não pode ter sido perdida ao crescer
