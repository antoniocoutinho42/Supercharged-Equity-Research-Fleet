# Espelho JS do núcleo e harness de paridade — Plano de Implementação (item 4, fatia A)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Um espelho JS do núcleo de valor da metodologia congelada — `ev_nopat`, `ev_ebitda`, `pe` e a ponte para preço — provado idêntico ao motor Python por um harness de paridade com fixture de semente fixa, casos patológicos deliberados, tolerância medida e não escolhida, e falha fechada.

**Architecture:** Três peças com uma responsabilidade cada: um gerador Python determinístico que emite o arquivo de vetores; o espelho `motor_espelho.js`, que exporta as funções puras e um ponto de entrada em lote usado tanto pelo node (CI) quanto pelo browser (banner de paridade do item 5); e o harness pytest que roda os dois lados sobre os MESMOS vetores e compara. O espelho vive sob `er-valuation`, não sob o relatório: é matemática de valuation sob a disciplina do wrapper, e o relatório apenas o embute depois.

**Tech Stack:** Python 3.12+ (stdlib pura), Node.js (v24 local, v22 no CI), pytest.

## Global Constraints

- **Fonte de verdade:** `docs/desenho-arquitetura-v4.md`, Seções 8.4, 13 e 18.
- **Regra inviolável 1 do desenho:** a matemática de valuation vem do motor congelado; **o único JS de valuation permitido é o espelho verificado por paridade**. Este item é essa exceção controlada — e é controlada exatamente pelo harness.
- **Falha fechada.** Divergência reprova. Sem node, o teste PULA com mensagem explícita (o CI tem node e sempre roda); um pulo silencioso é defeito.
- **A tolerância é medida, não escolhida.** O teste mede o erro máximo observado sobre a fixture, compara contra τ, e ALERTA se o observado chegar perto de τ. Constante mágica sem propriedade medida é número inventado.
- **Não tocar no vendor.** `vendor/multiplos-justos/**` é read-only e verificado por sha256.
- Determinismo: a fixture é reproduzível byte a byte a partir do gerador.
- stdlib pura no Python; **zero dependências npm** no JS (o espelho será embutido num HTML autocontido, sem rede).
- **`PYTHONUTF8=1` em tudo que imprime saída do motor** — o console desta máquina não codifica alguns caracteres e o `UnicodeEncodeError` parece falha de teste sem ser.
- Commits: conventional commits em PT-BR, trailer `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`.
- Não tocar em `skills/er-motor-k3/`, `skills/er-dados-openbb/`, `skills/er-relatorio-html/` (legado do v3, sai no item 10).

## Fora do escopo desta fatia

Solver de reversa e sensibilidades ao vivo (fatia 4B). `degrau`, `rampa` e os predicados numéricos de diagnóstico (fatia 4C). O relatório e o banner de paridade renderizado (item 5) — esta fatia entrega a função que o banner vai chamar, não o banner. Não antecipe nada.

## Contrato do espelho — e por que o plano NÃO transcreve as fórmulas

O espelho tem de reproduzir exatamente `vendor/multiplos-justos/scripts/justos.py`:

- **`ev_nopat`** — linhas 32–70 · **`ev_ebitda`** — linhas 71–72 · **`pe`** — linhas 214–271.

**Leia essas linhas no vendor e espelhe de lá.** Este plano deliberadamente **não** reproduz as fórmulas: uma transcrição minha seria uma terceira cópia, capaz de divergir do motor sem que nada acusasse, e o implementador estaria espelhando o plano em vez do motor. A fonte é o vendor; o que prova que você acertou é o harness da Task 3, mais as âncoras abaixo para conferir a si mesmo enquanto trabalha.

**Três armadilhas específicas da v9.31, todas verificadas contra o vendor:**

1. **O ramo `book` do firm usa IC ACUMULADO** (mudou na v9.26; é o único bug matemático daquele ciclo). `IC_n = (1+g)·(1/médio − 1/marginal) + (1+g)^{n+1}/marginal`, e `IC_n ≤ 0 ⟹ NaN`. Um espelho que use a fórmula antiga (`NOPAT_{n+1}/médio`) passa despercebido quando médio = marginal e erra ~12% quando não. Âncora: `ev_nopat(g=0.05, roic=0.20, w=0.08, n=10, tv='book', roic_book=0.10)` = **12.837404750556278** (é o caso da auditoria registrado no changelog). Colapso obrigatório: com `roic_book=0.20` (médio = marginal) e sem `roic_book` os dois dão **10.405638938111686**.
2. **No ramo `book` do equity, caixa/E NÃO altera o valor** (v9.30: `Div = LL − ΔE` já contém o caixa retido dentro de `E_n`; somar Δcaixa duplicaria). O termo `caixa·(g/roe)` entra em `gordon`/`convergencia` e **não** em `book`. Verificado: `pe(g=0.05, roe=0.20, ke=0.12, n=10, tv='book', roe_book=0.10)` dá **9.79359664180879** com caixa/E = 0.00, 0.20 e 0.50 — idêntico. Por contraste, no `gordon` o caixa move: `pe(g=0.08, roe=0.18, ke=0.14, n=10, tv='gordon', roe_tv=0.12, gp=0.03)` dá **8.464696096030156** sem caixa e **9.418809626084222** com `gde=0.30, nde=0.10`.
3. **`mid_year`** multiplica por `(1+custo)^0.5` no fim. Âncora: `ev_nopat(g=0.05, roic=0.12, w=0.10, n=10, tv='gordon', roic_tv=0.10, gp=0.03, mid_year=True)` = **11.69525022672858**.

**Âncoras adicionais** (as mesmas que o wrapper já usa): `ev_nopat(0.05, 0.12, 0.10, 10, tv='gordon', roic_tv=0.10, gp=0.03)` = **11.151…**, e a sua `ev_ebitda` com `d=0.20, t=0.25` = **6.6906…**; `pe(0.08, 0.18, 0.14, 10, 0.30, 0.20, tv='convergencia')` = **9.003…**.

**Caminhos NaN verificados:** `gp >= w` sob `gordon` ⟹ NaN; `roic <= 0` ⟹ NaN. Outros guardas existem no código — espelhe todos, não só estes.

**Um caso patológico da Seção 13 que NÃO pertence a esta fatia:** `ROE2 = 0` é parâmetro da composição bifásica (`_pe2_book`), que entra na 4C junto com `rampa`. Não é lacuna desta fixture; é escopo da fatia seguinte.

## Decisões de projeto já tomadas — não reabra, implemente

**D1 — O espelho vive em `skills/er-valuation/assets/motor_espelho.js`.** É matemática de valuation, e a disciplina que a governa é a do wrapper. O relatório (item 5) apenas o embute. Assim o item 4 não depende de o `er-relatorio` existir.

**D2 — Um só ponto de entrada em lote, dois chamadores.** O espelho exporta as funções puras **e** `avaliarVetores(vetores)`, que recebe a lista de vetores e devolve a lista de resultados. Sob node, `node motor_espelho.js <arquivo.json>` lê a fixture e imprime o JSON dos resultados em stdout. No browser (item 5), o banner de paridade chama `avaliarVetores` com os vetores embutidos no build. **Um caminho de código, dois chamadores** — um espelho que se auto-testa por um caminho e serve o produto por outro não prova nada sobre o produto.

**D3 — Os vetores nascem no Python, e a fixture é commitada.** O gerador tem semente fixa; a fixture gerada entra no repositório para ser revisável, e um teste regenera e compara **byte a byte**. Assim a semente cumpre o papel de reprodutibilidade sem que ninguém precise confiar nela.

**D4 — Não-finito atravessa como `null`, e a finitude é comparada ANTES do valor.** JSON não tem NaN. O Python emite `null` para todo resultado não-finito (é o que o próprio motor faz em `_json_sane`), e o JS idem. A comparação confere **primeiro** se os dois lados concordam sobre ser finito ou não; discordância aí é falha dura com o vetor impresso. Um espelho que devolve número onde o motor devolve NaN é defeito grave — e é exatamente o tipo que uma comparação numérica ingênua esconderia (`abs(nan - 5)` não é uma comparação útil).

**D5 — τ como erro relativo com piso absoluto:** `|py − js| ≤ max(τ·|py|, τ)`. Grandezas vão de múltiplos (~10) a valores de equity (~10⁹); um número fixo de casas decimais seria frouxo num extremo e impossível no outro. Valor inicial de τ: **1e-12**. A Task 3 **mede** o erro máximo real e o registra; se o medido não ficar pelo menos três ordens de grandeza abaixo de τ, isso é um achado a reportar, não a acomodar.

**D6 — A fixture tem de conter resultados não-finitos.** O gerador varre o espaço e a fixture guarda o que ele achou; um teste exige que existam **ao menos 20 vetores com resultado não-finito** e **ao menos 200 finitos**. Fixture só com casos bem-comportados não testa os guardas, que são metade do valor do espelho.

## File Structure

| Arquivo | Responsabilidade |
|---|---|
| `skills/er-valuation/scripts/vetores_paridade.py` | Gerar a fixture de vetores determinística; avaliar o lado Python. Nada mais |
| `tests/fixtures/vetores_paridade.json` | A fixture gerada e commitada |
| `skills/er-valuation/assets/motor_espelho.js` | O espelho: funções puras + `avaliarVetores` + CLI node. Zero dependência |
| `tests/test_paridade_js.py` | O harness: roda os dois lados, compara finitude e valor, mede τ |
| `.github/workflows/ci.yml` | Passo de paridade |
| `skills/er-valuation/SKILL.md` | O espelho e sua disciplina no escopo da skill |

---

### Task 1: Gerador de vetores e fixture

**Files:**
- Create: `skills/er-valuation/scripts/vetores_paridade.py`
- Create: `tests/fixtures/vetores_paridade.json`
- Create: `tests/test_vetores_paridade.py`

**Interfaces:**
- Produces: `SEMENTE: int = 20260825`; `gerar() -> list[dict]` (a lista completa de vetores, determinística); `avaliar_python(vetores: list[dict]) -> list[float | None]`; `escrever(vetores, destino: Path) -> None`; CLI `python skills/er-valuation/scripts/vetores_paridade.py --out <arquivo>`.
- Formato de um vetor: `{"id": int, "fn": "ev_nopat"|"ev_ebitda"|"pe", "args": {...}}`, onde `args` usa **os nomes de parâmetro do motor** (`g`, `roic`, `w`, `n`, `tv`, `roic_tv`, `gp`, `roic_book`, `mid_year` para o lado firm; `g`, `roe`, `ke`, `n`, `gde`, `nde`, `tv`, `roe_tv`, `gp`, `roe_book`, `politica_tv`, `mid_year` para `pe`; `ev_ebitda` acrescenta `d` e `t`). Taxas em **fração** (0.05 = 5%), como as funções internas do motor — não em porcento como o CLI.
- Consumed by: `motor_espelho.js` (lê o arquivo), `tests/test_paridade_js.py`.

- [ ] **Step 1: Escrever os testes (vão falhar)**

`tests/test_vetores_paridade.py`:

```python
import json
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
FIXTURE = RAIZ / "tests" / "fixtures" / "vetores_paridade.json"
SCRIPTS = RAIZ / "skills" / "er-valuation" / "scripts"
sys.path.insert(0, str(SCRIPTS))
from vetores_paridade import avaliar_python, gerar  # noqa: E402


def test_gerador_e_deterministico():
    assert gerar() == gerar()


def test_fixture_commitada_reproduz_o_gerador(tmp_path):
    """A semente cumpre reprodutibilidade; a fixture commitada e revisavel."""
    destino = tmp_path / "regerado.json"
    r = subprocess.run(
        [sys.executable, str(SCRIPTS / "vetores_paridade.py"), "--out", str(destino)],
        capture_output=True, text=True, encoding="utf-8", timeout=120)
    assert r.returncode == 0, r.stdout + r.stderr
    assert destino.read_bytes() == FIXTURE.read_bytes()


def test_fixture_cobre_as_tres_funcoes():
    vetores = json.loads(FIXTURE.read_text(encoding="utf-8"))
    fns = {v["fn"] for v in vetores}
    assert fns == {"ev_nopat", "ev_ebitda", "pe"}


def test_fixture_cobre_as_tres_convencoes_terminais():
    vetores = json.loads(FIXTURE.read_text(encoding="utf-8"))
    tvs = {v["args"]["tv"] for v in vetores}
    assert tvs == {"book", "convergencia", "gordon"}


def test_fixture_exercita_book_com_medio_diferente_do_marginal():
    """O ramo que mudou na v9.26 — um espelho com a formula antiga so erra aqui."""
    vetores = json.loads(FIXTURE.read_text(encoding="utf-8"))
    def separado(v):
        a = v["args"]
        if a["tv"] != "book":
            return False
        med = a.get("roic_book") if v["fn"] != "pe" else a.get("roe_book")
        marg = a.get("roic") if v["fn"] != "pe" else a.get("roe")
        return med is not None and abs(med - marg) > 1e-9
    assert sum(1 for v in vetores if separado(v)) >= 30


def test_fixture_exercita_mid_year_nos_dois_lados():
    vetores = json.loads(FIXTURE.read_text(encoding="utf-8"))
    com_mid = [v for v in vetores if v["args"].get("mid_year")]
    assert {v["fn"] for v in com_mid} >= {"ev_nopat", "pe"}


def test_fixture_tem_finitos_e_nao_finitos_em_quantidade():
    """Fixture so com casos bem-comportados nao testa os guardas."""
    vetores = json.loads(FIXTURE.read_text(encoding="utf-8"))
    r = avaliar_python(vetores)
    assert sum(1 for x in r if x is None) >= 20, "poucos nao-finitos"
    assert sum(1 for x in r if x is not None) >= 200, "poucos finitos"


def test_avaliacao_python_reproduz_as_ancoras_do_motor():
    """Ancoras conferidas contra o vendor; se mudarem, o vendor mudou."""
    casos = [
        ({"fn": "ev_nopat", "args": {"g": 0.05, "roic": 0.20, "w": 0.08, "n": 10,
                                     "tv": "book", "roic_book": 0.10}}, 12.837404750556278),
        ({"fn": "ev_nopat", "args": {"g": 0.05, "roic": 0.20, "w": 0.08, "n": 10,
                                     "tv": "book", "roic_book": 0.20}}, 10.405638938111686),
        ({"fn": "pe", "args": {"g": 0.05, "roe": 0.20, "ke": 0.12, "n": 10,
                               "gde": 0.30, "nde": 0.10, "tv": "book",
                               "roe_book": 0.10}}, 9.79359664180879),
        ({"fn": "ev_nopat", "args": {"g": 0.05, "roic": 0.12, "w": 0.10, "n": 10,
                                     "tv": "gordon", "roic_tv": 0.10, "gp": 0.03,
                                     "mid_year": True}}, 11.69525022672858),
    ]
    obtido = avaliar_python([dict(c[0], id=i) for i, c in enumerate(casos)])
    for (_, esperado), got in zip(casos, obtido):
        assert got == esperado


def test_caixa_nao_move_o_book_equity_mas_move_o_gordon():
    """Invariancia da v9.30, checada no lado Python antes de exigi-la do espelho."""
    def um(args):
        return avaliar_python([{"id": 0, "fn": "pe", "args": args}])[0]
    base = {"g": 0.05, "roe": 0.20, "ke": 0.12, "n": 10, "tv": "book", "roe_book": 0.10}
    sem = um(dict(base, gde=0.0, nde=0.0))
    com = um(dict(base, gde=0.60, nde=0.10))
    assert sem == com
    g_base = {"g": 0.08, "roe": 0.18, "ke": 0.14, "n": 10, "tv": "gordon",
              "roe_tv": 0.12, "gp": 0.03}
    assert um(dict(g_base, gde=0.0, nde=0.0)) != um(dict(g_base, gde=0.30, nde=0.10))
```

- [ ] **Step 2: Rodar para ver falhar**

Run: `PYTHONUTF8=1 python -m pytest tests/test_vetores_paridade.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'vetores_paridade'`.

- [ ] **Step 3: Implementar `vetores_paridade.py`**

Estrutura obrigatória:

- Docstring de módulo dizendo o que o arquivo faz e o que **não** faz: gera vetores e avalia o lado Python; não compara nada (isso é do harness) e não conhece JS.
- `SEMENTE = 20260825` e `random.Random(SEMENTE)` — instância própria, **nunca** o `random` global (o global é estado compartilhado e destruiria o determinismo se outro teste o tocasse).
- `gerar()` produz, nesta ordem, para que a fixture fique legível e o diff estável:
  1. **Bloco patológico explícito**, escrito à mão, um vetor por linha, cobrindo pelo menos: `w ≈ g` e `ke ≈ g` (custo colado no crescimento); `roic <= 0` e `roe <= 0`; `g/roic > 1` (RiR acima de 100%); `gp >= w` e `gp >= ke`; `gp <= -1`; `n = 1` (o mínimo que o motor aceita) e `n = 0` (que ele recusa); `g <= -1`; `roic_book`/`roe_book` **acima** do marginal **com `g` fortemente negativo** — é essa a combinação que alcança `IC_n ≤ 0`/`E_n ≤ 0` (uma versão anterior deste plano dizia "abaixo do marginal", e estava errada: reescrevendo a forma fechada como `IC_n = (1+g)/rb + (1+g)·[(1+g)^n − 1]/marginal`, com `g ≥ 0` o segundo termo nunca é negativo e o guarda é inalcançável por qualquer `rb > 0`); `roe = ke` com caixa/E em 0, 0.2 e 0.5; `roic = w`; `politica_tv` nas duas opções; `mid_year` nos dois lados.
  2. **Bloco aleatório** com a instância semeada, cobrindo as três funções × as três convenções, com faixas amplas o bastante para gerar tanto casos saudáveis quanto degenerados. Inclua deliberadamente sorteios de `roic_book`/`roe_book` independentes do marginal, para que médio ≠ marginal apareça com frequência.
  3. Cada vetor recebe `id` sequencial ao final, para que o harness possa nomear a divergência.
- `avaliar_python(vetores)` importa `ev_nopat`, `ev_ebitda` e `pe` de `vendor/multiplos-justos/scripts/justos.py` (insira o caminho no `sys.path`, derivado de `__file__` — deixe um comentário dizendo de onde vem a contagem de `parents`), chama cada uma com `**args`, e converte resultado não-finito em `None`.
- `escrever(vetores, destino)` grava com `json.dumps(..., indent=2, ensure_ascii=False)` mais `\n` final, `encoding="utf-8"`, `newline="\n"` — a mesma receita determinística do resto do projeto.
- CLI com `argparse`: `--out` obrigatório.

Alvo de tamanho: entre 300 e 800 vetores. Grande o bastante para varrer, pequeno o bastante para a fixture continuar revisável e o harness rodar rápido.

- [ ] **Step 4: Gerar a fixture**

Run: `PYTHONUTF8=1 python skills/er-valuation/scripts/vetores_paridade.py --out tests/fixtures/vetores_paridade.json`

- [ ] **Step 5: Rodar para ver passar**

Run: `PYTHONUTF8=1 python -m pytest tests/test_vetores_paridade.py -q`
Expected: PASS — 9 passed.

Se `test_fixture_tem_finitos_e_nao_finitos_em_quantidade` falhar por poucos não-finitos, **amplie as faixas do bloco aleatório** — não relaxe o limiar. O ponto do teste é que os guardas sejam exercitados.

- [ ] **Step 6: Suíte inteira**

Run: `PYTHONUTF8=1 python -m pytest tests/ -q`
Expected: PASS (base 400 + 9).

- [ ] **Step 7: Commit**

```bash
git add skills/er-valuation/scripts/vetores_paridade.py tests/fixtures/vetores_paridade.json tests/test_vetores_paridade.py
git commit -m "$(cat <<'EOF'
feat(er-valuation): gerador determinista de vetores de paridade

Fixture com semente fixa, bloco patologico escrito a mao e bloco aleatorio,
commitada e regeneravel byte a byte. Exige nao-finitos em quantidade: fixture
so com casos bem-comportados nao testa os guardas, que sao metade do valor
do espelho.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: O espelho JS

**Files:**
- Create: `skills/er-valuation/assets/motor_espelho.js`
- Create: `tests/test_espelho_js.py`

**Interfaces:**
- Consumes: `tests/fixtures/vetores_paridade.json` (Task 1).
- Produces (no módulo JS): `evNopat(args)`, `evEbitda(args)`, `pe(args)`, `ponteParaPreco({ev, ndEfetivo, acoes})`, `avaliarVetores(vetores)`. Todas recebem **um objeto** com as mesmas chaves de `args` da fixture — não posicional, para que a correspondência com o motor seja verificável por leitura.
- `avaliarVetores(vetores)` devolve `[{id, valor}]`, com `valor` `null` para não-finito.
- CLI: `node skills/er-valuation/assets/motor_espelho.js <arquivo.json>` imprime `JSON.stringify(resultados)` em stdout.
- Consumed by: `tests/test_paridade_js.py` (Task 3) e, no item 5, o banner de paridade do relatório.

- [ ] **Step 1: Escrever os testes (vão falhar)**

`tests/test_espelho_js.py`:

```python
import json
import shutil
import subprocess
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
ESPELHO = RAIZ / "skills" / "er-valuation" / "assets" / "motor_espelho.js"
FIXTURE = RAIZ / "tests" / "fixtures" / "vetores_paridade.json"

SEM_NODE = shutil.which("node") is None
RAZAO = "node ausente do PATH — a paridade roda sempre no CI (setup-node)"


def test_espelho_nao_tem_dependencia_externa():
    """Zero npm: o espelho sera embutido num HTML autocontido, sem rede.

    Casa por REGEX, nao por substring: comentarios em portugues contem
    "importante", que dispara um `"import " in texto` ingenuo, e o unico
    require legitimo e o de "fs" na secao do CLI.
    """
    import re
    texto = ESPELHO.read_text(encoding="utf-8")
    nucleo = texto.split("// CLI")[0]
    assert not re.search(r"^\s*import\s", nucleo, re.M), "import ES6 no nucleo"
    requires = re.findall(r"""require\(\s*['"]([^'"]+)['"]\s*\)""", texto)
    assert set(requires) <= {"fs"}, f"dependencia alem de fs: {sorted(set(requires))}"
    assert not re.search(r"require\(", nucleo), "require no nucleo — so na secao do CLI"


def test_espelho_nao_e_transcricao_de_outra_fonte():
    """O espelho cita o arquivo e as linhas do motor que ele reproduz."""
    texto = ESPELHO.read_text(encoding="utf-8")
    assert "vendor/multiplos-justos/scripts/justos.py" in texto


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_cli_do_espelho_devolve_um_resultado_por_vetor():
    r = subprocess.run(["node", str(ESPELHO), str(FIXTURE)],
                       capture_output=True, text=True, encoding="utf-8", timeout=120)
    assert r.returncode == 0, r.stdout + r.stderr
    resultados = json.loads(r.stdout)
    vetores = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert len(resultados) == len(vetores)
    assert [x["id"] for x in resultados] == [v["id"] for v in vetores]


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_espelho_emite_null_para_nao_finito():
    r = subprocess.run(["node", str(ESPELHO), str(FIXTURE)],
                       capture_output=True, text=True, encoding="utf-8", timeout=120)
    resultados = json.loads(r.stdout)
    assert any(x["valor"] is None for x in resultados), "nenhum null — os guardas nao rodaram"
    assert all(x["valor"] is None or isinstance(x["valor"], (int, float))
               for x in resultados)


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_ponte_para_preco_no_espelho():
    """A ponte tambem vive no espelho: o laboratorio recalcula preco/acao ao vivo."""
    script = (
        "const m = require(%s);"
        "const r = m.ponteParaPreco({ev: 6690.59, ndEfetivo: 500.0, acoes: 100.0});"
        "console.log(JSON.stringify(r));"
    ) % json.dumps(str(ESPELHO))
    r = subprocess.run(["node", "-e", script],
                       capture_output=True, text=True, encoding="utf-8", timeout=60)
    assert r.returncode == 0, r.stdout + r.stderr
    d = json.loads(r.stdout)
    assert d["equity"] == pytest.approx(6190.59, abs=1e-9)
    assert d["precoAcao"] == pytest.approx(61.9059, abs=1e-9)
```

- [ ] **Step 2: Rodar para ver falhar**

Run: `PYTHONUTF8=1 python -m pytest tests/test_espelho_js.py -q`
Expected: FAIL — `FileNotFoundError` em `motor_espelho.js`.

- [ ] **Step 3: Escrever o espelho**

Abra `vendor/multiplos-justos/scripts/justos.py` e espelhe **as linhas 32–72 e 214–271**. Requisitos de forma:

- Cabeçalho do arquivo dizendo, em uma frase, que este é o espelho verificado por paridade do núcleo de `vendor/multiplos-justos/scripts/justos.py`, citando as linhas espelhadas e a versão do vendor (v9.31), e que **nenhuma alteração pode ser feita aqui sem que o harness de paridade a aprove**.
- **Ordem das operações idêntica à do Python.** Some os termos do explícito no mesmo laço `t = 1..n`, na mesma ordem. Divergência de ordem em ponto flutuante é a causa mais provável de erro na casa que interessa.
- Cada guarda do Python vira uma guarda aqui, devolvendo `NaN`. Não invente guardas a mais nem omita nenhuma — a fixture patológica cobra os dois lados.
- `avaliarVetores` despacha por `fn` e converte não-finito em `null` com `Number.isFinite`.
- O CLI lê o arquivo passado em `process.argv[2]` com `fs.readFileSync` e imprime `JSON.stringify`. Mantenha a seção do CLI **depois** de um marcador `// CLI` e exporte via `module.exports` — o teste de ausência de dependência olha só o que vem antes do marcador.
- Zero npm. Só `fs` do node, e só na seção do CLI.

Confira-se contra as âncoras da seção "Contrato do espelho" enquanto trabalha; elas existem para você não descobrir um erro só na Task 3.

- [ ] **Step 4: Rodar para ver passar**

Run: `PYTHONUTF8=1 python -m pytest tests/test_espelho_js.py -q`
Expected: PASS — 5 passed.

- [ ] **Step 5: Suíte inteira** · **Step 6: `git status --short vendor` vazio**

- [ ] **Step 7: Commit**

```bash
git add skills/er-valuation/assets/motor_espelho.js tests/test_espelho_js.py
git commit -m "$(cat <<'EOF'
feat(er-valuation): espelho JS do nucleo de valor, sem dependencia

Espelha ev_nopat, ev_ebitda e pe do vendor v9.31 na mesma ordem de operacoes,
com todos os guardas devolvendo NaN. Um ponto de entrada em lote serve o
harness de paridade e, no item 5, o banner do relatorio — um caminho de
codigo, dois chamadores.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: O harness de paridade

**Files:**
- Create: `tests/test_paridade_js.py`
- Modify: `.github/workflows/ci.yml`
- Modify: `skills/er-valuation/SKILL.md`

**Interfaces:**
- Consumes: `vetores_paridade.avaliar_python`, a fixture, e o CLI do espelho.

- [ ] **Step 1: Escrever o harness (vai falhar se o espelho divergir)**

`tests/test_paridade_js.py`:

```python
"""Paridade Python <-> JS do espelho do nucleo (regra inviolavel 1 do desenho v4).

O espelho e a UNICA matematica de valuation em JS que o projeto admite, e o que
a torna admissivel e este arquivo. Sem node o teste PULA com razao explicita; o
CI tem node (setup-node) e sempre roda.

Tolerancia: erro RELATIVO com piso absoluto, |py - js| <= max(TAU*|py|, TAU).
As grandezas vao de multiplos (~10) a valores de equity (~1e9), entao numero
fixo de casas seria frouxo num extremo e impossivel no outro. TAU nao e
escolhido e esquecido: `test_tau_tem_folga_medida` mede o erro maximo real e
reprova se a folga encolher — limiar sem propriedade medida e constante magica.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
ESPELHO = RAIZ / "skills" / "er-valuation" / "assets" / "motor_espelho.js"
FIXTURE = RAIZ / "tests" / "fixtures" / "vetores_paridade.json"
sys.path.insert(0, str(RAIZ / "skills" / "er-valuation" / "scripts"))
from vetores_paridade import avaliar_python  # noqa: E402

TAU = 1e-12
SEM_NODE = shutil.which("node") is None
RAZAO = "node ausente do PATH — a paridade roda sempre no CI (setup-node)"


def _vetores():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _lado_js(vetores):
    r = subprocess.run(["node", str(ESPELHO), str(FIXTURE)],
                       capture_output=True, text=True, encoding="utf-8", timeout=180)
    assert r.returncode == 0, r.stdout + r.stderr
    por_id = {x["id"]: x["valor"] for x in json.loads(r.stdout)}
    return [por_id[v["id"]] for v in vetores]


def _erro_relativo(p, j):
    return abs(p - j) / max(abs(p), 1.0)


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_os_dois_lados_concordam_sobre_finitude():
    """Verificado ANTES do valor: numero onde o motor da NaN e defeito grave,
    e uma comparacao numerica ingenua o esconderia."""
    vetores = _vetores()
    py, js = avaliar_python(vetores), _lado_js(vetores)
    divergentes = [(v["id"], v["fn"], v["args"], p, j)
                   for v, p, j in zip(vetores, py, js)
                   if (p is None) != (j is None)]
    assert not divergentes, (
        f"{len(divergentes)} vetores discordam sobre finitude; primeiros 3: "
        f"{divergentes[:3]}")


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_paridade_numerica_dentro_de_tau():
    vetores = _vetores()
    py, js = avaliar_python(vetores), _lado_js(vetores)
    piores = sorted(
        ((_erro_relativo(p, j), v["id"], v["fn"], v["args"], p, j)
         for v, p, j in zip(vetores, py, js) if p is not None and j is not None),
        reverse=True)
    fora = [x for x in piores if x[0] > TAU]
    assert not fora, f"{len(fora)} vetores fora de TAU={TAU}; piores 3: {fora[:3]}"


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_tau_tem_folga_medida():
    """TAU entra na suite como propriedade MEDIDA, nao como constante magica."""
    vetores = _vetores()
    py, js = avaliar_python(vetores), _lado_js(vetores)
    maximo = max((_erro_relativo(p, j)
                  for p, j in zip(py, js) if p is not None and j is not None),
                 default=0.0)
    print(f"\nerro relativo maximo observado: {maximo:.3e} (TAU={TAU:.0e})")
    assert maximo < TAU / 1000, (
        f"folga encolheu: maximo observado {maximo:.3e} contra TAU {TAU:.0e}. "
        "Investigue a causa antes de mexer em TAU — a tolerancia existe para "
        "absorver ordem de avaliacao em ponto flutuante, nao erro de espelho.")


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_cobertura_da_fixture_no_harness():
    """O harness so vale se a fixture exercitar o que ele promete cobrir."""
    vetores = _vetores()
    py = avaliar_python(vetores)
    assert sum(1 for x in py if x is None) >= 20
    assert len(vetores) >= 300


def test_ausencia_de_node_pula_com_razao_explicita():
    """Pulo silencioso e defeito: quem roda local tem de saber que nao rodou."""
    assert RAZAO and "CI" in RAZAO
```

- [ ] **Step 2: Rodar**

Run: `PYTHONUTF8=1 python -m pytest tests/test_paridade_js.py -q -s`
Expected: PASS, com a linha `erro relativo maximo observado: ...` impressa.

**Se `test_paridade_numerica_dentro_de_tau` falhar:** o espelho divergiu. A saída nomeia o vetor, a função e os argumentos. Conserte o **espelho** contra o motor. **Não afrouxe TAU** — o número existe para absorver ordem de avaliação em ponto flutuante, não erro de transcrição, e um erro de transcrição é ordens de grandeza maior.

**Se `test_tau_tem_folga_medida` falhar** com um máximo muito acima do esperado (~1e-15), investigue antes de acomodar: soma em ordem diferente, `Math.pow` onde o Python usa multiplicação repetida, ou um guarda a menos.

- [ ] **Step 3: Registrar o valor medido**

Anote no relatório o erro relativo máximo observado. Se ele for da ordem de 1e-16 a 1e-14, é o esperado (~`n` × epsilon da máquina) e TAU tem a folga que deveria.

- [ ] **Step 4: Ligar ao CI**

Em `.github/workflows/ci.yml`, acrescente um passo nomeado **depois** do `pytest` (o pytest já roda o harness; este passo dá sinal separado e prova que o node do CI executa o espelho):

```yaml
      - name: Paridade Python↔JS do espelho
        env:
          PYTHONUTF8: "1"
        run: |
          node skills/er-valuation/assets/motor_espelho.js tests/fixtures/vetores_paridade.json > /dev/null
          python -m pytest tests/test_paridade_js.py -q
```

- [ ] **Step 5: `SKILL.md`**

Acrescente ao `skills/er-valuation/SKILL.md` uma seção curta: o espelho existe em `assets/motor_espelho.js`, é a única matemática de valuation em JS admitida, espelha o núcleo do vendor, e sua licença para existir é o harness de paridade — divergência reprova, e sem node o teste pula declarando isso. Duas ou três frases; **não reproduza metodologia** (os testes anti-paráfrase continuam valendo).

- [ ] **Step 6: Suíte inteira** · **Step 7: Validar o YAML do CI** (parse + o passo de paridade existe e vem depois do `pytest`)

- [ ] **Step 8: Commit** — mensagem sua, conventional em PT-BR: assunto dizendo que o harness entra, corpo dizendo por que ele é a licença de existência do espelho, e registrando o erro máximo medido. Trailer `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`.

---

## Verificação final da fatia 4A

- [ ] `PYTHONUTF8=1 python -m pytest tests/ -q` — verde
- [ ] `python -m pytest tests/test_paridade_js.py -q -s` — imprime o erro máximo observado
- [ ] `node skills/er-valuation/assets/motor_espelho.js tests/fixtures/vetores_paridade.json` — JSON bem formado, um resultado por vetor
- [ ] Regenerar a fixture reproduz o arquivo commitado byte a byte
- [ ] `git status --short vendor` vazio
- [ ] Uma alteração deliberada no espelho (trocar um sinal) faz o harness reprovar — **prove isso e reverta**; um harness que não pode ficar vermelho não é harness
