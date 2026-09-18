# Migração do vendor `multiplos-justos` v9.31 → v10.1 — plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tornar a v10.1 da metodologia a única versão vendorizada, executada e autoritativa do Fleet, adaptando só o que a v10.1 obriga: vocabulário de diagnósticos, espelho JS, as duas saídas novas do motor e a doutrina mínima.

**Architecture:** Troca byte a byte do pacote em `vendor/multiplos-justos/` (manifest e sha pinado), e adaptação nas três camadas que dependem dele: integração (`er-valuation`: classificador de diagnósticos, catálogo, espelho JS e fixture de paridade, publicação das saídas novas), relatório (`er-relatorio`: dois blocos congelados na aba Valuation) e doutrina (`er-analise`: checklist do M4). Nenhuma conta de valuation fora do motor (§18.1); o relatório só lê contratos (E3).

**Tech Stack:** Python 3.12 (stdlib), pytest, Node ≥ 22 (espelho), JSON.

## Global Constraints

- O vendor é read-only: o conteúdo de `vendor/multiplos-justos/` são os bytes do zip `H:\Academy\Investment framework\AI Skills\Valuation Skill\multiplos-justos-v10.1 (1).zip`, já extraído em `C:\Users\ANTONI~1.COU\AppData\Local\Temp\claude\C--Claude\4fdc2dac-c5f1-45ec-aa78-63545414e479\scratchpad\v101\multiplos-justos\` (8 arquivos). Nunca editar um byte.
- `.gitattributes` já tem `vendor/** -text`; conferir os hashes do manifest depois do `git add` (a máquina tem `core.autocrlf=true`).
- Toda execução do vendor com `PYTHONDONTWRITEBYTECODE=1` e `PYTHONUTF8=1`; nenhum `__pycache__` pode ficar em `vendor/`.
- Regras invioláveis do desenho (§18) e E3: o relatório nunca calcula nem lê prosa do motor; a integração nunca faz conta de valuation.
- A v10.1 não move nenhuma âncora numérica (changelog: divergência máxima 7,1e-15). **Um número de teste existente que mude é fato novo: PARE e reporte**, não ajuste o teste.
- A suíte inteira passa de 10 min: o implementador roda só os arquivos de teste da task; a suíte inteira é do controlador, desanexada (`python -m pytest tests -q > .superpowers/sdd/<log> 2>&1; echo EXIT=$? >> .superpowers/sdd/<log>`), sequencial.
- Branch `feat/vendor-multiplos-justos-v10.1`, sem push. Commits conventional em PT-BR com o trailer `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`. Uma heredoc por comando de shell; conteúdo longo pela ferramenta de escrita.
- Não tocar em arquivo fora da lista da task.

## Contexto verificado pelo controlador (17/09)

O vendor em uso é a **v9.31** (commit `173174c`, 25/08), não a v9.24: book com IC acumulado (v9.26), clean surplus no equity (v9.29–9.30), `--cash-yield` e o fechamento semântico (v9.31) já estão absorvidos, e o espelho JS foi construído contra a v9.31. O delta desta migração é v9.32 + v10 + v10.1. `selftest` e as duas fases de `testes.py` da v10.1 passam standalone.

O que muda no motor (`scripts/justos.py`) e onde chega no Fleet:

| Mudança | Onde chega |
|---|---|
| `ev_nopat` vira a soma de `ev_nopat_partes` (explícito, terminal, total); com `mid_year` a soma é `expl·f + term·f`, antes `(expl+term)·f` | espelho `evNopat` precisa da mesma ordem de operações |
| `ev` devolve `decomposicao_mm` (ativos instalados e valor do crescimento em ×NOPAT, participação do crescimento e peso do terminal em %, prosa `identidade_ativos_instalados`/`trava_de_leitura`; com `--ebitda`, também `NOPAT_base`, `ativos_instalados`, `valor_do_crescimento` em moeda) | cenários da rota firm (`avaliar._monta_cenario`); partes firm de SOTP já a copiam por passthrough |
| `diag_firm` ganha, **no topo e nesta ordem**, `DOMÍNIO [d]` (≥ 100% ou ≥ 60%), `DOMÍNIO [NOPAT]`, `DOMÍNIO [t]`, e, **depois do bloco do gordon e antes da linha do RiR**, `TERMINAL DOMINANTE` (peso do terminal > 50%, calculado por `ev_nopat_partes` **sem** `mid_year`) | toda chamada `ev` do wrapper: cenários, sensibilidades, teto do crescimento gratuito, partes firm de SOTP; o classificador recusa mensagem sem chave (HARD FAIL `diagnostico_sem_chave`) e o espelho precisa emitir as mesmas chaves na mesma ordem |
| `rampa` aceita giro negativo se `wk + kappa > 1e-15`; mensagens novas para `kappa < 0` e para `|wk| ≥ kappa` | espelho `rampaBifasica` e o problema K da fixture do solver |
| `nivel` ganha a leitura **recalculada** (vetor travado: só `d = D&A/métrica` responde ao nível; é a central e, por identidade, o break-even da base de lucro) com `--da-absoluta --tax --g --roic --wacc --n --tv [--roic-tv --gp --roic-book --mid-year]`, e a prosa `leitura_congelada` | `reversa.nivel_implicito` |
| `references/manutencao.md` (arquivo novo; a suíte do vendor exige a presença) | manifest e teste de congelamento |

Sem mudança para o Fleet: `diag_eq` e `pe` (o ramo `--ebitda` acrescentado ao handler `pe` é inalcançável, porque `pe` não declara `--ebitda`); o degrau roda na perna equity (`precificar_degrau` → `rodar("equity", ..., subcomando="degrau")`); `avisos_dominio` continua fora de `diagnosticos`.

Doutrina nova sem motor: onze escolhas nomeadas (11ª = nível da marca de estoque; a 8ª generalizada para "ponto do ciclo dos inputs de capital", com a média da série de três pontos como terceira opção), Gate 0 ampliado, §11.1c, §11.7 (MM obrigatória), §11.8 (confronto com o caixa operacional publicado), beta bottom-up, alíquota marginal no terminal, viés de mortalidade, duas camadas no entregável.

Decisões do dono (grill de 17/09): **Q1** decomposição MM publicada por cenário e renderizada congelada na aba Valuation; **Q2** nível implícito recalculado na rota firm com métrica EBITDA, as duas leituras na tela; **Q3** doutrina mínima — contagem e vocabulário das escolhas, checklist do M4, nenhum código de QC novo; **Q4** plugin 4.1.0 no PR, sem tag; **Q5** PR pela CLI `gh`; **Q6** smoke pela VLID3 no fluxo real, sem refazer pesquisa, com diferença contra a rodada v9.31 explicada antes de ser tratada como regressão.

## Mapa de arquivos

| Arquivo | Task | Responsabilidade |
|---|---|---|
| `vendor/multiplos-justos/**` | 1 | pacote v10.1, byte a byte |
| `skills/er-multiplos-justos/manifest_vendor.json`, `SKILL.md` | 1 | identidade e índice da cópia |
| `tests/test_vendor_multiplos_justos.py` | 1 | congelamento e versão única em runtime |
| `.github/workflows/ci.yml`, `.gitattributes` | 1 | só o número da versão nos rótulos |
| `skills/er-valuation/assets/diagnosticos_chaves.json` | 1 | cinco prefixos novos |
| `skills/er-valuation/assets/catalogo_apresentacao.json` | 1, 2 | versão e diagnósticos (1); `decomposicao_mm`, escolhas, anos-base (2) |
| `skills/er-valuation/assets/motor_espelho.js` | 1 | `evNopatPartes`, chaves novas, guarda da rampa |
| `skills/er-valuation/scripts/vetores_solver.py`, `tests/fixtures/vetores_solver.json` | 1 | problemas novos, fixture regenerada |
| `tests/test_paridade_wrapper_js.py` | 1 | cobertura dos alertas novos e do giro negativo |
| `skills/er-valuation/scripts/avaliar.py`, `reversa.py`, `caso.py` | 2 | publicar as saídas novas; vocabulário das escolhas |
| `skills/er-valuation/SKILL.md` | 2 | contrato de saída |
| `tests/test_valuation_avaliar.py`, `test_valuation_reversa.py`, `test_catalogo_apresentacao.py` | 1, 2 | travas |
| `skills/er-relatorio/scripts/render.py`, `assets/i18n/pt-BR.json`, `SKILL.md` | 3 | dois blocos na aba Valuation |
| `tests/test_relatorio_valuation.py` | 3 | travas da tela |
| `skills/er-analise/SKILL.md`, `docs/desenho-arquitetura-v4.md`, `README.md`, `.claude-plugin/*.json`, `tests/test_manifesto.py`, `docs/releases/v4.1.0.md` | 4 | doutrina mínima, versão e documentos |

---

### Task 1: Vendor v10.1, versão única em runtime e compatibilidade de diagnóstico e espelho

**Files:** ver o mapa (linhas da Task 1).

**Interfaces:**
- Produces: chaves `firm_dominio_d_100`, `firm_dominio_d_overhang`, `firm_dominio_nopat`, `firm_dominio_t`, `firm_terminal_dominante` em `diagnosticos_chaves.json` e em `catalogo.diagnosticos`; `evNopatPartes(args) -> {explicito, terminal, total}` no espelho; `evNopat(args) === evNopatPartes(args).total`.

- [ ] **Step 1: testes do vendor primeiro (RED).** Em `tests/test_vendor_multiplos_justos.py`: docstring e `versao` para `v10.1`; `ARQUIVOS` ganha `"references/manutencao.md"` (ordem alfabética); o docstring de `test_suite_completa_do_vendor_passa` troca `[v9.31]` por `[v9.31, mantido na v10.1]`. Acrescente ao fim de `test_selftest_do_motor_reproduz_as_ancoras`:

```python
    # [v10.1] O próprio motor se identifica: a versão que roda é a do manifest.
    assert _manifest()["versao"] in r.stdout, r.stdout[-2000:]
```

E o teste novo de versão única em runtime:

```python
def _copias_do_motor():
    """Todo `justos.py` do repositório, fora de .git, das raízes de execução e de caches."""
    for raiz, dirs, arquivos in os.walk(RAIZ):
        dirs[:] = [d for d in dirs if d not in {".git", "analises", "node_modules", "__pycache__"}]
        if "justos.py" in arquivos:
            yield (Path(raiz) / "justos.py").resolve()


def test_uma_so_copia_do_motor_e_todo_caminho_de_execucao_aponta_para_ela():
    """Versão única em runtime (migração v10.1): existe UM `justos.py`, e os três caminhos que o
    executam — o subprocesso do wrapper (`motor.RAIZ_VENDOR`) e os dois geradores de paridade,
    que o importam no próprio processo — resolvem para ele. Com o sha do manifest conferido
    acima, nenhuma outra versão do motor é alcançável pelo Fleet."""
    alvo = (VENDOR / "scripts" / "justos.py").resolve()
    assert sorted(_copias_do_motor()) == [alvo]
    sys.path.insert(0, str(RAIZ / "skills" / "er-valuation" / "scripts"))
    import motor
    import vetores_paridade
    import vetores_solver
    assert (motor.RAIZ_VENDOR / "scripts" / "justos.py").resolve() == alvo
    assert (vetores_paridade._VENDOR_SCRIPTS / "justos.py").resolve() == alvo
    assert (vetores_solver._VENDOR_SCRIPTS / "justos.py").resolve() == alvo
    import justos  # já carregado pelos geradores, com a escrita de bytecode desligada
    assert Path(justos.__file__).resolve() == alvo
    assert hasattr(justos, "decomposicao_mm") and hasattr(justos, "nivel_recalculado")
```

Rode `PYTHONUTF8=1 python -m pytest tests/test_vendor_multiplos_justos.py -q`. Esperado: RED (versão, arquivos, sha, selftest sem "v10.1", `decomposicao_mm` ausente).

- [ ] **Step 2: troque o vendor.** Apague os 7 arquivos de `vendor/multiplos-justos/` e copie os 8 do scratchpad com os mesmos caminhos relativos (`cp` binário; sem editar). Confira: `find vendor -type f | wc -l` = 8 e nenhum `__pycache__`.

- [ ] **Step 3: regenere o manifest por script** (hashes do disco, nunca digitados):

```python
import hashlib, json
from pathlib import Path
man_p = Path("skills/er-multiplos-justos/manifest_vendor.json")
man = json.loads(man_p.read_text(encoding="utf-8"))
vendor = Path("vendor/multiplos-justos")
man["versao"] = "v10.1"
man["copiado_em"] = "2026-09-17"
man["origem"] = ("pacote v10.1 da skill de usuario `multiplos-justos`, fornecido pelo dono (arquivo "
                 "`multiplos-justos-v10.1 (1).zip`), substituindo a copia congelada da v9.31. O caminho da "
                 "skill instalada e EFEMERO e nao e registrado: a identidade da copia e dada por versao + os "
                 "sha256 abaixo.")
man["regenerar"] = man["regenerar"].replace("apagar os 7 arquivos antigos", "apagar os arquivos antigos")
suite = {k: v for k, v in man["suite"].items() if not k.startswith("observado_em")}
suite["observado_em_2026-09-17"] = (
    "selftest OK ('SELFTEST OK - anchors preservados. v10.1: ...'); fase model termina em 'FASE CORE "
    "PASSOU.'; fase cli termina em 'FASE CLI PASSOU.'; invocacao unica sem --phase recusa (rc=2). A v10.1 "
    "traz references/manutencao.md, que a propria suite exige.")
man["suite"] = suite
man["arquivos"] = {p.relative_to(vendor).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                   for p in sorted(vendor.rglob("*")) if p.is_file()}
man_p.write_text(json.dumps(man, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
print(man["arquivos"]["scripts/justos.py"])
```

Troque o sha pinado em `test_sha_do_motor_pinado_no_proprio_teste` pelo valor impresso. Rode o arquivo de teste: GREEN.

- [ ] **Step 4: vocabulário de diagnóstico.** Em `skills/er-valuation/assets/diagnosticos_chaves.json`, depois de `firm_atencao_g0_book`, acrescente, no formato multilinha do arquivo (prefixos copiados do motor; os dois do meio param antes do sinal de menos e do travessão Unicode de propósito):

```json
  {"chave": "firm_dominio_d_100", "prefixo": "DOMÍNIO [d]: encargo de reposição >= 100% do EBITDA"},
  {"chave": "firm_dominio_d_overhang", "prefixo": "DOMÍNIO [d]: encargo de reposição em "},
  {"chave": "firm_dominio_nopat", "prefixo": "DOMÍNIO [NOPAT]:"},
  {"chave": "firm_dominio_t", "prefixo": "DOMÍNIO [t]:"},
  {"chave": "firm_terminal_dominante", "prefixo": "TERMINAL DOMINANTE: "},
```

Em `catalogo_apresentacao.json`: `metodologia.versao` = `"v10.1"`, e em `diagnosticos`:

```json
"firm_dominio_d_100": {"severidade": "alerta", "bloco": "earning_power", "rotulo": {"pt-BR": "Fora do domínio: o encargo de reposição consome todo o EBITDA, e o múltiplo justo não está definido nesta base"}},
"firm_dominio_d_overhang": {"severidade": "alerta", "bloco": "earning_power", "rotulo": {"pt-BR": "Encargo de reposição acima de 60% do EBITDA: lucro após imposto fino e múltiplo hipersensível ao encargo"}},
"firm_dominio_nopat": {"severidade": "alerta", "bloco": "earning_power", "rotulo": {"pt-BR": "Fora do domínio: lucro operacional após imposto não positivo, cenário sem múltiplo justo"}},
"firm_dominio_t": {"severidade": "alerta", "bloco": "earning_power", "rotulo": {"pt-BR": "Alíquota fora de 0 a 100%: regime anômalo que exige justificativa e reconciliação"}},
"firm_terminal_dominante": {"severidade": "alerta", "bloco": "duracao_terminal", "rotulo": {"pt-BR": "Mais da metade do valor está no terminal: a sensibilidade ao horizonte e o viés de mortalidade entram na entrega"}}
```

Rode `tests/test_catalogo_apresentacao.py` e `tests/test_paridade_wrapper_js.py`: o catálogo passa; a paridade reprova (o espelho ainda não emite as chaves) — RED esperado.

- [ ] **Step 5: espelho.** Em `motor_espelho.js`:
  1. Substitua `evNopat` por `evNopatPartes` + `evNopat` (mesma ordem de operações do motor; mantenha as convenções de NaN já documentadas no arquivo para `n` fracionário e `gp` nulo, e o histórico do comentário da book):

```js
// ---------------- nucleo: ev_nopat_partes / ev_nopat (v10.1) ----------------
// v10.1: o motor devolve as PARTES e `ev_nopat` e' a soma delas. Com mid_year a ordem e'
// expl*f + term*f (antes (expl+term)*f) — o espelho segue a ordem nova para a paridade
// continuar exata. `diag_firm` usa as partes (sem mid_year) para o peso do terminal.
function evNopatPartes(args) {
  const g = args.g;
  const roic = args.roic;
  const w = args.w;
  const n = args.n;
  const tv = tvCanon('tv' in args ? args.tv : 'book');
  const roicTv = args.roic_tv ?? null;
  const gp = 'gp' in args ? args.gp : 0.0;
  const roicBook = args.roic_book ?? null;
  const midYear = args.mid_year ?? false;
  if (g <= -1 || roic <= 0 || w <= -1 || n < 1 || !Number.isInteger(n)) {
    return { explicito: NaN, terminal: NaN, total: NaN };
  }
  const ret = 1 - g / roic;
  let expl = 0;
  for (let t = 1; t <= n; t++) {
    expl += ret * (1 + g) ** t / (1 + w) ** t;
  }
  let term;
  if (tv === 'gordon') {
    term = (roicTv === null || roicTv <= 0 || gp === null || gp <= -1 || gp >= w)
      ? NaN
      : (1 + g) ** (n + 1) * (1 - gp / roicTv) / (w - gp) / (1 + w) ** n;
  } else if (tv === 'convergencia') {
    term = w <= 0 ? NaN : (1 + g) ** (n + 1) / (w * (1 + w) ** n);
  } else {
    const rb = roicBook !== null ? roicBook : roic;
    if (rb <= 0) {
      term = NaN;
    } else {
      const icN = (1 + g) * (1.0 / rb - 1.0 / roic) + (1 + g) ** (n + 1) / roic;
      term = icN <= 0 ? NaN : icN / (1 + w) ** n;
    }
  }
  const f = midYear ? (1 + w) ** 0.5 : 1.0;
  expl *= f;
  if (!Number.isNaN(term)) term *= f;
  return { explicito: expl, terminal: term, total: Number.isNaN(term) ? NaN : expl + term };
}

function evNopat(args) {
  return evNopatPartes(args).total;
}
```

  2. Em `CHAVE`, as cinco chaves novas (`FIRM_DOMINIO_D_100`, `FIRM_DOMINIO_D_OVERHANG`, `FIRM_DOMINIO_NOPAT`, `FIRM_DOMINIO_T`, `FIRM_TERMINAL_DOMINANTE`) com os valores do JSON.
  3. Em `diagnosticosFirm`, depois de `const chaves = [];` e ANTES do bloco `if (tv === 'book')`, as guardas de domínio (leia `d`/`tax` aqui e reuse-as no bloco da coerência no fim, apagando a leitura duplicada de lá):

```js
  // v10 (diag_firm recebe da=d e tax=t do handler `ev`): as guardas de dominio abrem a lista.
  const d = nucleo.d;
  const tax = nucleo.t;
  if (d !== undefined && d !== null) {
    if (d >= 1.0) {
      chaves.push(CHAVE.FIRM_DOMINIO_D_100);
    } else if (d >= 0.60) {
      chaves.push(CHAVE.FIRM_DOMINIO_D_OVERHANG);
    }
    if (tax !== undefined && tax !== null && d >= 0.0 && d < 1.0 && (1 - d) * (1 - tax) <= 0) {
      chaves.push(CHAVE.FIRM_DOMINIO_NOPAT);
    }
  }
  if (tax !== undefined && tax !== null && !(tax >= 0.0 && tax <= 1.0)) {
    chaves.push(CHAVE.FIRM_DOMINIO_T);
  }
```

     e, depois do bloco `if (tv === 'gordon' && roicTv !== null) {...}` e antes de `const rir = g / roic;`:

```js
  // v10.1: peso do terminal pelas partes do motor, sem mid_year (diag_firm chama
  // ev_nopat_partes sem ele); total NaN ou zero nao dispara, como no motor.
  const partes = evNopatPartes({ g, roic, w, n, tv, roic_tv: roicTv, gp, roic_book: roicBook });
  const pesoTv = partes.total ? partes.terminal / partes.total : NaN;
  if (!Number.isNaN(pesoTv) && pesoTv > 0.50) {
    chaves.push(CHAVE.FIRM_TERMINAL_DOMINANTE);
  }
```

  4. Em `rampaBifasica`, troque a guarda `if (wk < 0 || kappa < 0) {...}` por:

```js
  if (kappa < 0) {
    throw new Error('domínio inválido: kappa (intensidade de capital fixo) deve ser >= 0');
  }
  if (wk < 0 && (wk + kappa) <= 1e-15) {
    throw new Error('giro negativo com |wk| >= kappa: o capital incremental total é <= 0 e a '
      + 'intensidade de capital deixa de ser definida — rode as fases pelo bloco padrão '
      + '(`ev` por fase) em vez da rampa fechada');
  }
```

  5. No cabeçalho, `(v9.31)` → `(v10.1)`, e uma linha: "Referências `justos.py:<linha>` neste arquivo foram escritas contra a v9.31; na v10.1 as linhas deslocam (o núcleo ganhou `ev_nopat_partes` e `decomposicao_mm` no topo): localize pelo nome da função." Atualize as referências só nos trechos que esta task reescreve.

- [ ] **Step 6: fixture do solver.** Em `vetores_solver.py`, `_bloco_rampa`: o problema K passa a `"wk": -25.0` (com o `kappa` 20 da base: a recusa nova, `|wk| ≥ kappa`) e o comentário diz isso; logo depois, o problema K2 `{**base, "g1": 6.0, "tv": "book", "wk": -5.0, "n": 10}` com a mesma ponte (giro negativo autofinanciado, calculado). Em `_bloco_diag`, rota firm, cinco problemas: `{**bf, "da": 65.0}` (overhang), `{**bf, "da": 100.0}` (≥ 100%), `{**bf, "tax": 100.0}` (NOPAT), `{**bf, "tax": 110.0}` (alíquota e NOPAT), `{**bf, "tv": "convergencia", "wacc": 7.0}` (terminal dominante; a base `bf` fica abaixo de 50%). Regenere: `python skills/er-valuation/scripts/vetores_solver.py --out tests/fixtures/vetores_solver.json`. Em `tests/test_paridade_wrapper_js.py`: em `test_fixture_de_diagnostico_cobre_os_alertas`, o filtro de alertas inclui `"TERMINAL DOMINANTE"`; em `test_fixture_de_rampa_cobre_o_que_discrimina`, acrescente `assert any(p["args"]["premissas"].get("wk", 0) < 0 for p, a in zip(probs, py) if not a["recusado"]), "giro negativo calculado nunca exercitado"`.

- [ ] **Step 7: GREEN.** `PYTHONUTF8=1 python -m pytest tests/test_vendor_multiplos_justos.py tests/test_catalogo_apresentacao.py tests/test_paridade_js.py tests/test_paridade_solver_js.py tests/test_paridade_wrapper_js.py tests/test_espelho_js.py tests/test_espelho_fachada_js.py tests/test_vetores_paridade.py tests/test_valuation_motor.py tests/test_valuation_avaliar.py tests/test_valuation_contrato.py tests/test_valuation_reversa.py tests/test_valuation_sensibilidades.py tests/test_valuation_sotp.py -q` — tudo verde. Diagnóstico novo aparecendo em resultado de teste é esperado; número mudando não é (PARE).

- [ ] **Step 8: rótulos da versão.** `skills/er-multiplos-justos/SKILL.md`: `v9.31` → `v10.1`; a tabela do mapa ganha a linha `vendor/multiplos-justos/references/manutencao.md` ("Manual de adição de conhecimento ao pacote: camadas, domicílio, bifurcação × invariante, checklist" | "Ao propor mudança na metodologia"); "cada um dos 7 arquivos" → "cada um dos 8 arquivos". `.github/workflows/ci.yml`: o nome do passo diz `v10.1`. `.gitattributes`: o comentário diz `v10.1`. Rode `tests/test_vendor_multiplos_justos.py` de novo (o índice não pode copiar linha ≥ 60 caracteres do vendor).

- [ ] **Step 9: commit** e confira os hashes no índice (`git ls-files --eol vendor` todo `i/lf w/lf attr/-text`; `git status --short vendor` limpo). Mensagem: `feat(vendor): multiplos-justos v9.31 -> v10.1, versao unica em runtime, diagnosticos e espelho`.

---

### Task 2: Saídas novas da integração e vocabulário da v10

**Files:** `skills/er-valuation/scripts/avaliar.py`, `reversa.py`, `caso.py`; `skills/er-valuation/assets/catalogo_apresentacao.json`; `skills/er-valuation/SKILL.md`; `tests/test_valuation_avaliar.py`, `tests/test_valuation_reversa.py`, `tests/test_catalogo_apresentacao.py`.

**Interfaces:**
- Consumes: motor v10.1 (Task 1).
- Produces: `resultados.cenarios.<n>.decomposicao_mm` (rota firm: o bloco do motor, íntegro); `resultados.reversa.nivel_implicito.recalculado` (rota firm com métrica EBITDA: o bloco do motor, íntegro — ou com `sem_solucao`); `catalogo.decomposicao_mm = {"nota": {idioma: str}, "campos": {campo: {"rotulo": {idioma: str}, "unidade": str}}}`; escolha `nivel_da_marca_de_estoque`; ano-base `media_serie_tres_pontos`.

- [ ] **Step 1: testes (RED).** Em `tests/test_valuation_avaliar.py`, sobre os casos de fixture já usados no arquivo: todo cenário da rota firm publica `decomposicao_mm` igual ao bloco que `motor.rodar` devolve para as mesmas premissas e escala; nenhum cenário da rota equity ou rampa o publica. Em `tests/test_valuation_reversa.py`, sobre um caso firm/EBITDA com reversa:

```python
def test_a_leitura_central_do_nivel_recalcula_o_multiplo_e_fica_entre_a_base_e_o_limite():
    caso = _caso()  # firm/EBITDA com reversa; ajuste ao helper do arquivo
    nivel = reverter(caso, "base", 500.0)["nivel_implicito"]
    rec = nivel["recalculado"]
    base, limite = caso["metrica_base"]["valor"], nivel["metrica_base_implicita"]
    central = rec["metrica_base_implicita_recalculada"]
    # a escada da v10.1: o múltiplo recalculado leva o nível para entre a base e a leitura congelada
    assert min(base, limite) < central < max(base, limite)
    # a D&A entrou em moeda, pelo encargo de reposição do cenário sobre a métrica-base
    da = caso["cenarios"]["base"]["premissas"]["da"]
    assert rec["d_no_nivel_implicito_%"] == pytest.approx(da * base / central, rel=1e-3)
```

e um teste de que sem métrica EBITDA (ou fora da rota firm) não há `recalculado`. Em `tests/test_catalogo_apresentacao.py`: a lista das chaves de topo ganha `"decomposicao_mm"`; `test_escolhas_metodologicas_do_catalogo_sao_as_dez_do_gate_com_rotulo_e_gatilho` vira `..._sao_as_onze_...` com `len == 11`; teste novo — todo campo de `CAT["decomposicao_mm"]["campos"]` aparece, numérico, em todo `decomposicao_mm` que as fixtures publicam, e a unidade de cada um está em `CAT["unidades"]`.

- [ ] **Step 2: `avaliar._monta_cenario`.** Depois de montar o dict, `if rota == "firm": registro["decomposicao_mm"] = saida_motor["decomposicao_mm"]` (chave exigida: o `ev` da v10.1 sempre a devolve; ausência é motor errado e deve estourar alto). Comentário: é o bloco do motor, íntegro, como `coerencia_vetor`; nenhuma conta aqui.

- [ ] **Step 3: `reversa.nivel_implicito`.** Assinatura `nivel_implicito(caso, alvo, multiplo_justo, premissas=None)`. Constante e ramo:

```python
# v10.1: premissas do cenário que o `nivel` do motor usa na leitura RECALCULADA (vetor travado).
# `da` NÃO entra: `nivel` não tem `--da`, e o argparse aceitaria `--da` como abreviação de
# `--da-absoluta` em silêncio — o encargo de reposição entra em moeda, por `--da-absoluta`.
_PREMISSAS_DA_LEITURA_RECALCULADA: tuple[str, ...] = (
    "tax", "g", "roic", "wacc", "n", "tv", "roic_tv", "gp", "roic_book", "mid_year")
```

```python
    if premissas is not None:
        # D&A absoluta = encargo de reposição do cenário × métrica-base: álgebra de escala sobre
        # dois números declarados (a mesma natureza de `alvo_de_mercado`), para o motor
        # recalcular o múltiplo a cada nível com a D&A fixa em moeda.
        argumentos["da-absoluta"] = premissas["da"] / 100.0 * caso["metrica_base"]["valor"]
        for chave in _PREMISSAS_DA_LEITURA_RECALCULADA:
            if premissas.get(chave) is not None:
                argumentos[chave] = premissas[chave]
```

Em `reverter`, passe `caso["cenarios"][nome_cenario]["premissas"]` só quando `caso["rota"] == "firm" and caso["metrica_base"]["tipo"] == "EBITDA"` (em ×NOPAT a D&A não entra no múltiplo; em P/L não existe). Atualize a docstring (a leitura congelada é limite superior quando o nível sobe; a recalculada é a central). A publicação continua `{**saida, "leitura_chave": ...}`.

- [ ] **Step 4: vocabulário da v10 em `caso.py` e no catálogo.** `ESCOLHAS_METODOLOGICAS` ganha `"nivel_da_marca_de_estoque"`; `ANOS_BASE_DO_CAPEX` ganha `"media_serie_tres_pontos"`; comentários que dizem "as dez escolhas" dizem "as onze". Catálogo:

```json
"nivel_da_marca_de_estoque": {"rotulo": {"pt-BR": "Nível da marca de estoque: marca de avaliação ou de transação realizada"}, "gatilho": {"pt-BR": "Mais de cerca de 20% do valor vem de marca de estoque — laudo, NAV, cap rate, valor de reposição, banco de terras, estoque pronto ou carteira marcada."}}
```

`ano_de_capex_no_par_d_rir` passa a `{"rotulo": {"pt-BR": "Ponto do ciclo dos inputs de capital (capex, giro e base de ativos): corrente, média da série de três pontos ou guidance de longo prazo"}, "gatilho": {"pt-BR": "Os inputs de capital do ano corrente divergem da média da série de três pontos ou do estado estacionário que o guidance de longo prazo indica."}}` (a chave fica, para não quebrar caso existente). `anos_base_do_capex` ganha `"media_serie_tres_pontos": {"rotulo": {"pt-BR": "Média da série de três pontos"}}`. Seção nova de topo:

```json
"decomposicao_mm": {
  "nota": {"pt-BR": "Ativos instalados é o valor sem crescimento nenhum; o valor do crescimento é o restante. A leitura só vale se o encargo de reposição medir a reposição de verdade: com o encargo subdimensionado, o lucro está superestimado e os ativos instalados herdam o erro. Nas convenções de convergência e gordon os ativos instalados são exatamente um sobre o custo de capital; na convenção book dependem do retorno médio do capital existente."},
  "campos": {
    "ativos_instalados_x_NOPAT": {"rotulo": {"pt-BR": "Ativos instalados, em múltiplo do lucro operacional após imposto"}, "unidade": "múltiplo"},
    "valor_do_crescimento_x_NOPAT": {"rotulo": {"pt-BR": "Valor do crescimento, em múltiplo do lucro operacional após imposto"}, "unidade": "múltiplo"},
    "participacao_do_crescimento_%": {"rotulo": {"pt-BR": "Participação do crescimento no valor"}, "unidade": "pp"},
    "peso_do_terminal_%": {"rotulo": {"pt-BR": "Peso do valor terminal"}, "unidade": "pp"}
  }
}
```

(Os montantes em moeda ficam no `resultados.json`; a tela mostra a decomposição do múltiplo, que não é conclusão de valor e não depende do produto.)

- [ ] **Step 5: `skills/er-valuation/SKILL.md`.** No contrato de saída: `cenarios.<n>.decomposicao_mm` (rota firm; o bloco do motor, íntegro, e a tela lê só os campos do catálogo) e `reversa.nivel_implicito.recalculado` (firm/EBITDA; leitura central, com `--da-absoluta` = `da` × métrica-base). "dez escolhas" → "onze escolhas". Na seção do espelho: `evNopatPartes`, as chaves novas de `diagnosticosFirm` e a guarda nova da rampa.

- [ ] **Step 6: GREEN** — os arquivos de teste da task mais `tests/test_valuation_caso.py`, `tests/test_valuation_contrato.py`, `tests/test_espelho_fachada_js.py`, `tests/test_relatorio_valuation.py` (este pode reprovar só pela tela do nível: é a Task 3; anote e siga). Commit: `feat(er-valuation): decomposicao MM, nivel implicito recalculado e o vocabulario da v10`.

---

### Task 3: Relatório — os dois blocos congelados na aba Valuation

**Files:** `skills/er-relatorio/scripts/render.py`, `skills/er-relatorio/assets/i18n/pt-BR.json`, `skills/er-relatorio/SKILL.md`, `tests/test_relatorio_valuation.py`.

**Interfaces:**
- Consumes: `resultados.cenarios.<n>.decomposicao_mm`, `resultados.reversa.nivel_implicito.recalculado`, `catalogo.decomposicao_mm` (Task 2).

- [ ] **Step 1: testes (RED)** em `tests/test_relatorio_valuation.py`: (a) numa entrega firm, a seção `valuation-decomposicao-mm` existe, tem uma linha por cenário e, em cada linha, cada campo do catálogo formatado pela unidade do catálogo a partir do número publicado; numa entrega equity, a seção não existe; (b) com `recalculado`, o bloco do nível mostra primeiro a leitura central (métrica, degrau, encargo de reposição e múltiplo no nível implícito) e depois a de múltiplo fixo com o rótulo de limite superior; com `sem_solucao`, a frase do dicionário no lugar dos números centrais; sem `recalculado`, o bloco sai como antes. Atualize a lista esperada de `test_o_nivel_implicito_entra_no_que_esta_no_preco_com_o_rotulo_do_catalogo` se a fixture dela for firm/EBITDA.

- [ ] **Step 2: i18n** (`valuation.*`): `decomposicao_mm_titulo` "Decomposição do valor: ativos instalados e crescimento"; `decomposicao_mm_cenario` "Cenário"; `decomposicao_mm_congelado` "Bloco calculado nas premissas originais de cada cenário: não acompanha as edições do laboratório."; `nivel_implicito_central_metrica_titulo` "Métrica-base que o preço embute — leitura central, com o múltiplo recalculado no nível"; `nivel_implicito_central_degrau_titulo` "Degrau implícito — leitura central"; `nivel_implicito_central_d_titulo` "Encargo de reposição no nível implícito"; `nivel_implicito_central_multiplo_titulo` "Múltiplo justo no nível implícito"; `nivel_implicito_central_sem_solucao` "Leitura central: nenhum nível da métrica-base explica o preço sob este vetor."; `nivel_implicito_limite_metrica_titulo` "Métrica-base que o preço embute — múltiplo fixo, limite superior"; `nivel_implicito_limite_degrau_titulo` "Degrau implícito — múltiplo fixo, limite superior"; `nivel_implicito_escada` "A leitura central recalcula o múltiplo a cada nível, com a depreciação fixa em moeda; manter o múltiplo fixo dá o limite superior. A leitura central é também o ponto de equilíbrio da base de lucro contra o preço."

- [ ] **Step 3: `render.py`.** Função nova, chamada em `_valuation_html` logo depois de `_cenarios_da_valuation_html(...)`:

```python
def _decomposicao_mm_html(resultados: dict, catalogo: dict, idioma: str, dicionario: dict) -> str:
    """v10.1 (§11.7 do `aplicacao.md`): a decomposição de Miller-Modigliani de cada cenário que a
    publica, pelos campos, rótulos e unidades do catálogo — nunca pelos nomes crus do motor, nunca
    pela prosa dele. Precomputada: o laboratório não a reproduz, e o bloco diz isso. Sem cenário
    com o bloco (rotas equity e rampa), a seção não existe."""
    publicados = [(nome, cenario["decomposicao_mm"])
                  for nome, cenario in _campo_de_contrato(resultados, "cenarios", "resultados").items()
                  if isinstance(cenario.get("decomposicao_mm"), dict)]
    if not publicados:
        return ""
    secao = _campo_de_contrato(catalogo, "decomposicao_mm", "catalogo")
    campos = _campo_de_contrato(secao, "campos", "catalogo.decomposicao_mm")
    colunas = [t(dicionario, "valuation.decomposicao_mm_cenario")] + [
        info["rotulo"][idioma] for info in campos.values()]
    linhas = []
    for nome, bloco in publicados:
        onde = f"resultados.cenarios.{nome}.decomposicao_mm"
        linhas.append([str(nome)] + [
            _formatar_na_unidade(_campo_de_contrato(bloco, campo, onde), catalogo, info["unidade"], idioma, None)
            for campo, info in campos.items()])
    return ('<section class="valuation-decomposicao-mm">'
            f'<h2>{html.escape(t(dicionario, "valuation.decomposicao_mm_titulo"))}</h2>'
            f'<p class="reversa-congelado-nota">{html.escape(t(dicionario, "valuation.decomposicao_mm_congelado"))}</p>'
            + _tabela_html("decomposicao-mm", colunas, linhas)
            + f'<p class="decomposicao-mm-nota">{html.escape(secao["nota"][idioma])}</p></section>')
```

Em `_nivel_implicito_html`: com `recalculado` e `metrica_base_implicita_recalculada` nele, as quatro linhas centrais (métrica pela unidade `moeda` com a escala, como a linha existente; degrau por `FORMATO_DO_DEGRAU_IMPLICITO`; encargo pela unidade `pp`; múltiplo pela unidade `múltiplo`), depois as duas linhas de múltiplo fixo com os títulos `nivel_implicito_limite_*`, e a nota `nivel_implicito_escada`; com `recalculado` e sem aquela chave, a frase `nivel_implicito_central_sem_solucao` no lugar das linhas centrais; sem `recalculado`, exatamente o bloco de hoje. As razões contra o consenso e a leitura classificada continuam como estão (o motor as calcula sobre a leitura congelada).

- [ ] **Step 4: `skills/er-relatorio/SKILL.md`**, na descrição da aba Valuation: a seção da decomposição (depois dos cenários, congelada) e as duas leituras do nível implícito.

- [ ] **Step 5: GREEN** — `tests/test_relatorio_valuation.py tests/test_relatorio_render.py tests/test_relatorio_laboratorio.py tests/test_relatorio_contrato.py tests/test_relatorio_cobertura_11.py tests/test_fixture_sintetica.py tests/test_relatorio_paridade_build.py -q`. Commit: `feat(er-relatorio): decomposicao do valor e as duas leituras do nivel implicito na aba Valuation`.

---

### Task 4: Doutrina mínima, versão 4.1.0 e documentos (controlador)

**Files:** `skills/er-analise/SKILL.md`, `docs/desenho-arquitetura-v4.md`, `README.md`, `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `tests/test_manifesto.py`, `docs/releases/v4.1.0.md`.

- [ ] **Step 1:** `er-analise` — item novo no checklist do M4 com as obrigações de entrega que a v10.1 criou e nenhum código decide: decomposição MM reportada e o encargo de reposição com a contraprova de caixa (capex de manutenção declarado), ou o gap declarado; confronto com o caixa operacional publicado (`aplicacao.md` §11.8); alíquota marginal no terminal ou a efetiva com o benefício estrutural declarado; beta bottom-up como rota central, com o beta construído declarado; com o alerta de terminal dominante, sensibilidade ao horizonte e viés de mortalidade; nível implícito pela leitura central quando publicada; RiR por perna em projeção nominal (giro pelo ciclo de caixa, com o sinal dele; fixo só pela expansão de volume) e o delator de contração (Δreceita ≤ 0 invalida o deployment observado como âncora); deriva de D/V a mercado ≥ ~10 p.p. no horizonte declarada, com o efeito pelo `apv` do motor, ou declarada imaterial. No M3, uma linha: os mandatos cobrem a evidência que o Gate 0 da v10.1 pede (rubricas de capex de manutenção, fluxo de caixa operacional publicado, série de três pontos do balanço, betas de pares).
- [ ] **Step 2:** desenho (`v9.31` → `v10.1` onde nomeia a versão vendorizada; "Dez escolhas" → "Onze escolhas"; §9/§8.4 citam a decomposição e as duas leituras do nível como precomputadas), README (`v9.31` → `v10.1`), manifestos `4.1.0` com a descrição citando `v10.1`, `tests/test_manifesto.py` `VERSAO = "4.1.0"`, e `docs/releases/v4.1.0.md`.
- [ ] **Step 3:** `tests/test_manifesto.py tests/test_analise_skill.py tests/test_relatorio_cobertura_11.py tests/test_vendor_multiplos_justos.py -q` verdes; commit `docs: v4.1.0 -- metodologia v10.1, checklist do M4 e desenho`.

---

### Task 5: Verificação final e PR (controlador)

- [ ] **Step 1:** suíte inteira desanexada, com `EXIT` no log; `selftest` e as duas fases pela CLI.
- [ ] **Step 2:** smoke VLID3 pelo fluxo real, na raiz `analises/VLID3/2026-09-17-001`, depois de copiar os artefatos da rodada v9.31 para `analises/VLID3/2026-09-17-001.v931/`: `avaliar.py caso.json --out resultados.json`, `execucao.py suite <raiz>`, `execucao.py montar <raiz>`. Comparar manchete, faixa, cenários, reversa, diagnósticos, QC e ficha contra a rodada v9.31; toda diferença explicada pela v10.1 antes de ser chamada de regressão.
- [ ] **Step 3:** confirmação em runtime: `origem.metodologia.versao` do `resultados.json`, ficha técnica, linha do `selftest` e sha do `justos.py` executado contra o manifest.
- [ ] **Step 4:** passada no navegador pelos dois blocos novos e pelo badge de paridade.
- [ ] **Step 5:** push da branch e PR com `gh pr create`; CI acompanhada pelas ferramentas do app.
