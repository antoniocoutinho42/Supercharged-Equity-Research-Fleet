# engine v3.3.0 — WACC consistente, paridade decomposta e diagnóstico de alavancagem — Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tornar a rota de reconciliação (`ebit_justo`) exata em taxa (WACC a pesos de MERCADO), devolver a divergência de paridade DECOMPOSTA por cunha nomeada (`paridade_decomposta`) e emitir o diagnóstico de alavancagem `ke_alavancagem` (Ku MM vs Harris–Pringle) — três entregas ADITIVAS, nenhum novo gerador de preço.

**Architecture:** Tudo em `engine.py` (stdlib), seguindo os padrões já existentes: gating por presença, degrade declarado (`aplicavel: false` + motivo), decomposição one-at-a-time com interação (mesmo padrão do `central_neutro`), constantes nomeadas no topo do bloco. A rota `premissa` (chaves atuais de `ebit_justo`) fica byte-idêntica; as novidades entram como chaves novas.

**Tech Stack:** Python 3.12 (stdlib; pyyaml para inputs .yaml), suíte golden própria (`tests/test_golden_vrsk.py`, script com exit code — NÃO é pytest).

## Global Constraints (regras duras — violação = trabalho rejeitado)

- **Aditividade estrita:** para inputs existentes, TODAS as chaves atuais de `resultados.json` produzem valores IDÊNTICOS aos de v3.2.0 (regressão byte-a-byte nas chaves antigas do golden VRSK). Chaves novas apenas se somam. Em particular: NÃO alterar o texto de `ebit_justo.paridade.instrucao` nem qualquer valor existente.
- Nenhum novo gerador de preço; nada entra em média com o P/L Justo; nenhum DCF explícito — formas fechadas somente. `hurdle` e `economico` intocados.
- Invariantes existentes preservados (ROE=Ke → 1/Ke; Gordon; monotonia em Ke; DE=NDE neutro) + novos: (a) premissas consistentes e ND=0 → divergência ≈ 0 e cunhas ≈ 0; (b) WACC premissa == consistente → `cunha_taxa` == 0; (c) soma das cunhas + interação == divergência total (exato, tol 1e-9, assert no engine E no teste).
- Determinismo total: stdlib, sem aleatoriedade, sem rede.
- `ENGINE_VERSION = "3.3.0"` + entrada de CHANGELOG ≤ 10 linhas no topo do engine.py.
- Campos novos de input OPCIONAIS com default seguro, documentados em `inputs_exemplo_vrsk.yaml`; inputs antigos rodam sem alteração.
- `SKILL.md`: 3 linhas novas na tabela da Seção 1 (`paridade_decomposta`, `ke_alavancagem`, `ebit_justo.consistente`) + 1 parágrafo na Seção 2b. Não reescrever o resto.
- `cap_check.py` e `scripts/snapshot.py` INTOCADOS.
- Limiares e comportamento do warning `PARIDADE_DIVERGENTE` INALTERADOS (não bloqueia publicação — condição 3); ele passa apenas a APONTAR para o bloco novo via chave nova.
- TDD estrito: teste falhando primeiro, sempre.
- Python nesta máquina: `$env:LOCALAPPDATA\Programs\Python\Python312\python.exe` (instalado nesta sessão; não está no PATH).

---

## Validação conceitual (Damodaran) — corroborativa, registrada

Orçamento de 3 buscas usado (home → frame home.htm → `relval.pdf`). Resultado:

1. **Múltiplos justificados = funções fechadas dos fundamentos + consistência numerador/denominador — CONFIRMADO com URL e trecho.**
   URL: `https://pages.stern.nyu.edu/~adamodar/pdfiles/eqnotes/relval.pdf` (deck "Relative Valuation", 178 pp.).
   p. 6, Proposition 1: *"Both the value (the numerator) and the standardizing variable (the denominator) should be to the same claimholders in the firm. In other words, the value of equity should be divided by equity earnings or equity book value, and firm value should be divided by firm earnings or book value."*
   p. 8, Proposition 2: *"Embedded in every multiple are all of the variables that drive every discounted cash flow valuation - growth, risk and cash flow patterns"* — *"using a simple discounted cash flow model and basic algebra should yield the fundamentals that drive a multiple"*.
2. **Custo de capital com pesos a valor de MERCADO — página exata não alcançada dentro do orçamento.** Registro de indisponibilidade; citar por teoria consagrada: prática canônica de custo de capital (Damodaran, *Investment Valuation*; Modigliani–Miller 1963). A especificação da Seção 2 do pedido é a fonte de verdade.
3. **Equivalência FCFF@WACC − dívida ≡ FCFE@Ke sob premissas consistentes; MM vs Harris–Pringle/Miles–Ezzell como convenções de política de dívida — página exata não alcançada dentro do orçamento.** Citar por nome: Modigliani–Miller 1963; Miles–Ezzell 1980; Harris–Pringle 1985. A especificação (Seção 2/Entrega C do pedido) é a fonte de verdade das fórmulas.

Nenhuma fórmula foi "descoberta" na busca: tudo o que se implementa abaixo veio da especificação do pedido.

---

## Decisões de desenho (resoluções dentro da especificação — aprovar antes de codar)

- **D1 — ND do bridge:** `ND = −Σ claims_bridge` (claims líquidos). É a ÚNICA leitura fiel à identidade do bloco (`equity = EV + Σ claims` ⇒ `EV − equity = −Σ claims`). Declarada por chave `nd_bridge_mi`.
- **D2 — Convenção da ponte NOPAT→LL (Entrega B): LÍQUIDA.** Verificação feita: o `bloco_ebit_justo` atual NÃO tem ponte NOPAT→LL — mas o bloco inteiro opera em claims LÍQUIDOS e o custo de dívida novo entra como `kd_liquido` (após imposto). A única convenção coerente com o bloco é `LL_implicito = NOPAT − kd_liquido × ND_bridge` (sem `(1−t)` extra: kd já é líquido). Não reportar a convenção bruta: o engine não é ambíguo — ele é integralmente líquido no bridge. Uma frase no CHANGELOG registra a escolha.
- **D3 — Claims implícitas do gerador (cunha 3):** o gerador equity embute alavancagem via bracket DE/NDE sobre book contábil; o book que o próprio gerador implica é `LL_efetivo / ROE_base`. Logo `claims_implicitas = −NDE × (LL_efetivo/ROE_base)` — determinístico, sem input novo; com a exceção 0/0 (VRSK-like) dá 0, expondo exatamente a cunha de medição. (Alternativa rejeitada: exigir `pl_contabil_mi` como obrigatório — quebraria inputs antigos.)
- **D4 — VTS (Entrega C):** forma fechada de perpetuidade descontada a Kd: `VTS = t × ND` (= t·Kd·ND/Kd). Alíquota: `premissas.impostos.marginal` se declarada, senão `aliquota_operacional` — fonte declarada por chave. (Alternativa rejeitada: VTS truncado no CAP — introduziria uma segunda estrutura temporal não especificada; YAGNI.)
- **D5 — Kd da Entrega C = o MESMO `kd_liquido` da Entrega A**, declarado por chave (`kd_liquido`). Um único custo de dívida medido, sem duplicação de input.
- **D6 — Drift de Ke re-alavancado:** convenção Harris–Pringle (sem VTS): `ke_realav_contabil = Ku_HP + (Ku_HP − Kd)·ND/E_contabil`; `drift_pp = |ke_realav_contabil − Ke|×100`; alerta se `> KE_REALAVANCAGEM_DRIFT_PP = 0.5` (constante nomeada). Requer `fatos.pl_contabil_mi` (opcional novo); ausente → degrade com nota.
- **D7 — Inputs novos, todos OPCIONAIS:** `premissas.operacional.kd_liquido` (fração, custo de dívida líquido após imposto; se presente exige `fonte_kd` — mesma disciplina H8 do `fonte_wacc`) e `fatos.pl_contabil_mi`. Sem `kd_liquido`: `consistente`, `paridade_decomposta` e `ke_alavancagem` degradam com `aplicavel: false` + motivo.
- **D8 — `ebit_justo.premissa` = espelho compacto** (wacc, cadeia por cenário, ponderado) duplicando os números já existentes — dá a simetria `premissa`/`consistente` que a spec pede SEM tocar nas chaves atuais.
- **D9 — Alvo da decomposição sem arredondamento:** internamente a Entrega B recompõe a rota equity SEM arredondar (mesmas chamadas `pl_justo`) para o invariante fechar a 1e-9; as chaves publicadas continuam com o arredondamento padrão. O alvo publicado ecoa `equity_alvo_mi` e a nota de que `economico.central_ponderado` é a visão arredondada por ação.
- **D10 — Semântica dos sinais (declarada no JSON):** `divergencia_total = rota_operacional(premissa) − rota_equity` (mesma direção do `paridade.delta_pct` atual); `cunha_X = valor_op_premissa − valor_op_com_X_corrigido` = parcela da divergência ELIMINADA ao corrigir X sozinho; `interacao = divergencia_total − Σ cunhas` (resíduo explícito: interações + diferença estrutural ROIC-vs-ROE do motor).

Verificação numérica da referência da spec (feita à mão, entra como teste): Ke=22%, Kd_liq=11,655%, ND=30, E_book=65, E_mkt=150,5 → WACC contábil = 0,22·65/95 + 0,11655·30/95 = **18,733%** ✓; WACC consistente = 0,22·150,5/180,5 + 0,11655·30/180,5 = **20,281%** ✓; Ku_HP = 20,281% (= WACC consistente com Kd líquido) e `ke_realav_contabil` = 0,20281 + (0,20281−0,11655)·30/65 = **24,26%** → drift 2,26 p.p. > 0,5 → alerta ✓.

---

## File Structure

- `skills/er-valuation/engine.py` — CHANGELOG + versão; constantes novas; `bloco_ebit_justo` ganha `premissa`/`consistente` e ponteiro `paridade.decomposicao`; funções novas `bloco_paridade_decomposta` e `bloco_ke_alavancagem`; fiação em `rodar()`.
- `skills/er-valuation/tests/golden_v320_vrsk.json` — NOVO fixture: dump v3.2.0 do golden VRSK (todas as chaves top-level exceto `engine`), gerado ANTES de qualquer mudança.
- `skills/er-valuation/tests/test_golden_vrsk.py` — CAMADA H (v3.3.0): regressão byte-a-byte + fixtures sintéticos + invariantes novos.
- `skills/er-valuation/inputs_exemplo_vrsk.yaml` — comentários documentando os campos opcionais novos (dados inalterados).
- `skills/er-valuation/SKILL.md` — 3 linhas na tabela §1 + parágrafo na §2b.

Comando de teste (sempre): 
`& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" tests\test_golden_vrsk.py` a partir de `skills/er-valuation` (exit 0 = verde).

---

### Task 0: Branch + fixture de regressão v3.2.0 (ANTES de tocar no engine)

**Files:**
- Create: `skills/er-valuation/tests/golden_v320_vrsk.json`

**Interfaces:**
- Produces: fixture JSON com todas as chaves top-level v3.2.0 (exceto `engine`) do golden VRSK, `json.dumps(..., sort_keys=True, ensure_ascii=False, indent=1)`.

- [ ] **Step 1: criar branch**

```bash
cd /c/Claude/equity-research-fleet && git checkout -b feat/engine-v330
```

- [ ] **Step 2: gerar o fixture com o engine v3.2.0 ATUAL (script one-off no scratchpad, não commitado)**

```python
# scratchpad/gera_fixture_v320.py
import json, os, sys
BASE = r"C:\Claude\equity-research-fleet\skills\er-valuation"
sys.path.insert(0, BASE)
from engine import carregar_inputs, rodar, ENGINE_VERSION
assert ENGINE_VERSION == "3.2.0", "fixture DEVE ser gerado antes de qualquer mudança"
res = rodar(carregar_inputs(os.path.join(BASE, "inputs_exemplo_vrsk.yaml")))
res.pop("engine")  # única chave com timestamp/hash — excluída do contrato de regressão
dest = os.path.join(BASE, "tests", "golden_v320_vrsk.json")
with open(dest, "w", encoding="utf-8") as fh:
    json.dump(res, fh, sort_keys=True, ensure_ascii=False, indent=1)
print("fixture ->", dest)
```

Run: `& $py scratchpad\gera_fixture_v320.py` — Expected: `fixture -> ...\tests\golden_v320_vrsk.json`

- [ ] **Step 3: teste de regressão (CAMADA H0) no test_golden_vrsk.py — deve passar JÁ em v3.2.0 (sanidade do fixture)**

Acrescentar ao final da CAMADA G (antes do bloco final de resultado):

```python
print("=" * 100)
print("CAMADA H — v3.3.0: regressão byte-a-byte + rota consistente + paridade decomposta")
print("=" * 100)
import json as _json
with open(os.path.join(AQUI, "golden_v320_vrsk.json"), "r", encoding="utf-8") as _fh:
    _golden_v320 = _json.load(_fh)
for _chave, _valor in sorted(_golden_v320.items()):
    chk_bool(f"H0 regressão v3.2.0 byte-a-byte: chave '{_chave}' idêntica",
             _json.dumps(res.get(_chave), sort_keys=True, ensure_ascii=False)
             == _json.dumps(_valor, sort_keys=True, ensure_ascii=False))
chk_bool("H0b golden VRSK sem bloco operacional: chaves novas AUSENTES (gating por presença)",
         "paridade_decomposta" not in res and "ke_alavancagem" not in res
         and "ebit_justo" not in res)
```

- [ ] **Step 4: rodar a suíte — 100% verde (fixture consistente com o engine atual)**

Run: `& $py tests\test_golden_vrsk.py` — Expected: `RESULTADO: TODOS OS GOLDEN TESTS PASSARAM`, exit 0.

- [ ] **Step 5: commit**

```bash
git add skills/er-valuation/tests/golden_v320_vrsk.json skills/er-valuation/tests/test_golden_vrsk.py
git commit -m "test: fixture de regressao byte-a-byte v3.2.0 do golden VRSK (camada H0)"
```

---

### Task 1: Entrega A — `ebit_justo.premissa` + `ebit_justo.consistente` (WACC a pesos de mercado)

**Files:**
- Modify: `skills/er-valuation/engine.py` (bloco_ebit_justo, ~linhas 1330–1593; constantes ~1330)
- Test: `skills/er-valuation/tests/test_golden_vrsk.py` (camada H, após H0)

**Interfaces:**
- Consumes: `econ["central_ponderado"]`, `econ["ke_central"]`, `pl_justo`, `_pond`, `_m_terminal`.
- Produces: `ebit_justo.premissa = {wacc, cenarios{n: {ev_nopat_justo, ev_ebit_justo[, ev_ebitda_justo], ev_mi, equity_mi, preco}}, ponderado_preco}`; `ebit_justo.consistente = {aplicavel, motivo?, wacc_consistente, ke, kd_liquido, fonte_kd, e_mkt_mi, ancora_e_mkt, nd_bridge_mi, peso_equity, peso_divida, cenarios{...mesma cadeia...}, ponderado_preco, nota}`; `ebit_justo.paridade.decomposicao = "paridade_decomposta"` (chave NOVA; `instrucao` intocada). Inputs novos: `premissas.operacional.kd_liquido` + `fonte_kd`.

- [ ] **Step 1: fixture sintético + testes falhando (camada H1)**

Acrescentar ao test_golden_vrsk.py, após o bloco H0 (o helper e o fixture são consumidos também pelas camadas H2/H3 das Tasks 2–3):

```python
def fixture_sintetico(kd=0.06, wacc=0.10, claims=(), nopat=None, pl_contabil=None,
                      nde_medido=0.0, de_medido=0.0):
    """Caso sintético mínimo e CONSISTENTE: margem×giro == ROE por cenário,
    NOPAT default == LPA×ações, grade de Ke degenerada no central 10%."""
    acoes = 100.0
    lpa = 1.0
    fx = {
        "meta": {"ticker": "SINT", "nome": "Sintético", "moeda": "USD",
                 "preco_atual": 12.0, "acoes_mi": acoes},
        "fatos": {
            "lpa_ajustado_fy": lpa,
            "de": de_medido, "nde": nde_medido,
            "nopat_fy_mi": (lpa * acoes) if nopat is None else nopat,
            "claims_bridge": [dict(c) for c in claims],
        },
        "premissas": {
            "ke_economico": [0.09, 0.10, 0.11],
            "cap_teto_defensavel": 15,
            "cap_confianca": "MEDIA",
            "justificativa_cap": "caso sintético de teste do invariante de paridade v3.3.0",
            "justificativa_cenarios": "caso sintético de teste do invariante de paridade v3.3.0",
            "cenarios": {
                "bear": {"prob": 0.25, "g": 0.03, "roe": 0.15, "cap": 8},
                "base": {"prob": 0.50, "g": 0.05, "roe": 0.15, "cap": 10},
                "bull": {"prob": 0.25, "g": 0.07, "roe": 0.15, "cap": 12},
            },
            "multiplos_validacao": {"metrica_primaria": "PE", "base_lucro": "ADJUSTED",
                                    "limiar_divergencia": 0.30},
            "operacional": {
                "wacc": wacc, "fonte_wacc": "teste sintético (fixture v3.3.0)",
                "kd_liquido": kd, "fonte_kd": "teste sintético (fixture v3.3.0)",
                "aliquota_operacional": 0.20, "fonte_aliquotas": "teste sintético",
                "cenarios": {"bear": {"margem_nopat": 0.15, "giro_noa": 1.0},
                             "base": {"margem_nopat": 0.15, "giro_noa": 1.0},
                             "bull": {"margem_nopat": 0.15, "giro_noa": 1.0}},
            },
        },
    }
    if pl_contabil is not None:
        fx["fatos"]["pl_contabil_mi"] = pl_contabil
    fx["_hash_inputs"] = "sintetico_teste"
    return fx

# H1 — Entrega A: rota consistente com ND=0 -> wacc_consistente == ke_central
res_s0 = rodar(fixture_sintetico(kd=0.06, wacc=0.10, claims=()))
eb0 = res_s0["ebit_justo"]
chk_bool("H1a ebit_justo.premissa espelha as chaves existentes byte-a-byte",
         all(eb0["premissa"]["cenarios"][n]["preco"] == eb0["cenarios"][n]["preco"]
             and eb0["premissa"]["cenarios"][n]["ev_nopat_justo"] == eb0["cenarios"][n]["ev_nopat_justo"]
             and eb0["premissa"]["cenarios"][n]["ev_ebit_justo"] == eb0["cenarios"][n]["ev_ebit_justo"]
             for n in ("bear", "base", "bull"))
         and eb0["premissa"]["wacc"] == eb0["wacc"]
         and eb0["premissa"]["ponderado_preco"] == eb0["ponderado_preco"])
chk("H1b ND=0: wacc_consistente == ke_central (pesos 100% equity)",
    eb0["consistente"]["wacc_consistente"], 0.10, 1e-12)
chk_bool("H1c consistente declara âncora do E_mkt e ND do bridge",
         "central_ponderado" in eb0["consistente"]["ancora_e_mkt"]
         and eb0["consistente"]["nd_bridge_mi"] == 0.0
         and eb0["consistente"]["aplicavel"] is True)
# H1d — cadeia EV/NOPAT -> EV/EBIT=(1-t) -> preservada na rota consistente
_c = eb0["consistente"]["cenarios"]["base"]
chk("H1d cadeia consistente: ev_ebit == ev_nopat*(1-t)",
    _c["ev_ebit_justo"], round(_c["ev_nopat_justo"] * (1 - 0.20), 4), 1e-9)
# H1e — com dívida: wacc_consistente reproduz a fórmula de pesos de mercado
_claims_d = ({"nome": "dívida líquida", "valor_mi": -300.0, "fonte": "teste"},)
res_s1 = rodar(fixture_sintetico(kd=0.06, wacc=0.10, claims=_claims_d))
eb1 = res_s1["ebit_justo"]["consistente"]
_e, _nd = eb1["e_mkt_mi"], eb1["nd_bridge_mi"]
chk("H1e wacc_consistente == kd*ND/(ND+E) + ke*E/(ND+E)",
    eb1["wacc_consistente"],
    round(0.06 * _nd / (_nd + _e) + 0.10 * _e / (_nd + _e), 6), 1e-9)
chk_bool("H1f nd_bridge = -total de claims (D1)", _nd == 300.0)
# H1g — kd sem fonte_kd -> recusa (disciplina H8)
def _kd_sem_fonte(i):
    i["premissas"]["operacional"] = dict(i["premissas"]["operacional"])
    i["premissas"]["operacional"].pop("fonte_kd")
inp_kdsf = fixture_sintetico()
_kd_sem_fonte(inp_kdsf)
try:
    rodar(inp_kdsf)
    chk_bool("H1g kd_liquido sem fonte_kd -> recusa", False)
except ValueError as exc:
    chk_bool("H1g kd_liquido sem fonte_kd -> recusa", "fonte_kd" in str(exc))
# H1h — sem kd_liquido: consistente degrada declarado, rota premissa intacta
inp_semkd = fixture_sintetico()
inp_semkd["premissas"]["operacional"].pop("kd_liquido")
inp_semkd["premissas"]["operacional"].pop("fonte_kd")
res_semkd = rodar(inp_semkd)
chk_bool("H1h sem kd_liquido: consistente.aplicavel=False com motivo; premissa intacta",
         res_semkd["ebit_justo"]["consistente"]["aplicavel"] is False
         and "kd_liquido" in res_semkd["ebit_justo"]["consistente"]["motivo"]
         and res_semkd["ebit_justo"]["ponderado_preco"] is not None)
chk_bool("H1i paridade ganha ponteiro para o bloco de decomposição (chave nova, instrucao intocada)",
         res_s0["ebit_justo"]["paridade"].get("decomposicao") == "paridade_decomposta"
         and "ROTA DE RECONCILIAÇÃO" in res_s0["ebit_justo"]["paridade"]["instrucao"])
```

- [ ] **Step 2: rodar — H1 FALHA (KeyError `premissa`/`consistente`), H0 e A–G verdes**

Run: `& $py tests\test_golden_vrsk.py` — Expected: FAIL nas H1*, exit 1.

- [ ] **Step 3: implementar no engine.py**

3a. Constantes (logo abaixo de `EBIT_PARIDADE_LIMIAR_PCT`):

```python
KE_REALAVANCAGEM_DRIFT_PP = 0.5  # Entrega C (v3.3.0): drift de Ke re-alavancado contábil vs mercado
PARIDADE_DECOMP_TOL = 1e-9       # Entrega B (v3.3.0): fechamento exato da decomposição
```

3b. Validação do kd (dentro do bloco de `erros` do `bloco_ebit_justo`, após a validação de `fonte_aliquotas`):

```python
    kd_in = op.get("kd_liquido")
    if kd_in is not None:
        if not isinstance(kd_in, (int, float)) or float(kd_in) <= 0:
            erros.append("premissas.operacional.kd_liquido, quando declarado, deve ser numérico "
                         "> 0 (custo de dívida LÍQUIDO após imposto, fração — v3.3.0)")
        elif not str(op.get("fonte_kd", "")).strip():
            erros.append("premissas.operacional.fonte_kd obrigatória quando kd_liquido é "
                         "declarado (mesma disciplina do fonte_wacc — H8)")
```

3c. Depois do cálculo de `paridade` e ANTES do `return`, montar as duas rotas (o `paridade` ganha só a chave nova):

```python
    paridade["decomposicao"] = "paridade_decomposta"  # v3.3.0: warning passa a referenciar o bloco

    def _cadeia(nopat_x, wacc_x):
        """Cadeia EV/NOPAT → EV/EBIT=(1−t) → EV/EBITDA=×(1−d) por cenário, numa taxa dada."""
        cen_out = {}
        for n in nomes:
            c = cen_eq[n]
            evn = pl_justo(float(c["g"]), roics[n], float(c["cap"]), wacc_x, 0.0, 0.0,
                           _m_terminal(c))
            ev_mi = evn * nopat_x
            eq_mi = ev_mi + total_claims
            cen_out[n] = {"ev_nopat_justo": round(evn, 4),
                          "ev_ebit_justo": round(evn * (1.0 - t), 4),
                          "ev_mi": round(ev_mi, 2),
                          "equity_mi": round(eq_mi, 2),
                          "preco": round(eq_mi / float(acoes), 2)}
            if dsobre is not None:
                cen_out[n]["ev_ebitda_justo"] = round(evn * (1.0 - t) * (1.0 - float(dsobre)), 4)
        return cen_out

    # Rota PREMISSA: espelho compacto das chaves existentes (mesmos números; aditivo — D8).
    premissa = {"wacc": w,
                "cenarios": {n: {k: v for k, v in out_cen[n].items()
                                 if k in ("ev_nopat_justo", "ev_ebit_justo", "ev_ebitda_justo",
                                          "ev_mi", "equity_mi", "preco")}
                             for n in nomes},
                "ponderado_preco": ponderado}

    # Rota CONSISTENTE (Entrega A): WACC a pesos de MERCADO. E_mkt é OUTPUT do gerador
    # equity (que não depende do WACC) — sem circularidade, sem solver. ND medida do
    # bridge de claims (= −Σ claims, identidade equity = EV + Σ claims — D1).
    e_mkt_mi = float(econ["central_ponderado"]) * float(acoes)
    nd_bridge_mi = -total_claims
    ke_c = float(econ["ke_central"])
    kd_l = op.get("kd_liquido")
    v_total = e_mkt_mi + nd_bridge_mi
    if kd_l is None:
        consistente = {"aplicavel": False,
                       "motivo": "premissas.operacional.kd_liquido ausente — sem custo de dívida "
                                 "medido o WACC consistente não é calculável (campo opcional "
                                 "v3.3.0; degrade declarado, rota premissa intacta)"}
    elif v_total <= 0:
        consistente = {"aplicavel": False,
                       "motivo": "E_mkt + ND do bridge <= 0 — pesos de mercado degenerados "
                                 "(claims líquidos positivos excedem o equity justo)"}
    else:
        kd_l = float(kd_l)
        wacc_cons = kd_l * nd_bridge_mi / v_total + ke_c * e_mkt_mi / v_total
        cen_cons = _cadeia(float(nopat_fy), wacc_cons)
        consistente = {
            "aplicavel": True,
            "wacc_consistente": round(wacc_cons, 6),
            "ke": ke_c,
            "kd_liquido": kd_l,
            "fonte_kd": str(op["fonte_kd"]),
            "e_mkt_mi": round(e_mkt_mi, 2),
            "ancora_e_mkt": "economico.central_ponderado × meta.acoes_mi (equity justo do "
                            "gerador principal, âncora econômica central)",
            "nd_bridge_mi": round(nd_bridge_mi, 2),
            "peso_equity": round(e_mkt_mi / v_total, 6),
            "peso_divida": round(nd_bridge_mi / v_total, 6),
            "cenarios": cen_cons,
            "ponderado_preco": round(_pond(cen_eq, {n: cen_cons[n]["preco"] for n in nomes}), 2),
            "nota": "Sem circularidade nem solver: E_mkt vem do gerador equity, que não depende "
                    "do WACC; a teoria exige pesos a valor de MERCADO (pesos contábeis geram a "
                    "cunha de taxa isolada em paridade_decomposta.cunha_taxa).",
        }
```

E no dicionário de retorno do `bloco_ebit_justo`, acrescentar (sem tocar nas chaves atuais):

```python
        "premissa": premissa,
        "consistente": consistente,
```

- [ ] **Step 4: rodar — H1 verde, H0 e A–G verdes**

Run: `& $py tests\test_golden_vrsk.py` — Expected: exit 0.

- [ ] **Step 5: commit**

```bash
git add skills/er-valuation/engine.py skills/er-valuation/tests/test_golden_vrsk.py
git commit -m "feat(engine): entrega A v3.3.0 - rota consistente do ebit_justo (WACC a pesos de mercado)"
```

---

### Task 2: Entrega B — bloco `paridade_decomposta`

**Files:**
- Modify: `skills/er-valuation/engine.py` (nova função após `bloco_ebit_justo`; fiação em `rodar()`)
- Test: `skills/er-valuation/tests/test_golden_vrsk.py` (camada H2)

**Interfaces:**
- Consumes: `fixture_sintetico(...)` (Task 1), `ebit_justo.consistente`, `_de_nde`, `pl_justo`, `_pond`, `_m_terminal`, `PARIDADE_DECOMP_TOL`.
- Produces: chave top-level `paridade_decomposta = {aplicavel, ordem, baseline, alvo, equity_alvo_mi, divergencia_total{valor_mi, valor_por_acao, pct_equity_justo}, cunhas{cunha_taxa, cunha_base_lucro, cunha_bridge_claims, interacao — cada uma {valor_mi, valor_por_acao, pct_equity_justo, leitura}}, convencoes{...}, invariante}`.

- [ ] **Step 1: testes falhando (camada H2)**

```python
# H2 — Entrega B: caso sintético de paridade PERFEITA (aceite: divergência e cunhas <= 1e-9)
pd0 = res_s0["paridade_decomposta"]
chk("H2a paridade perfeita: divergencia_total ~ 0 (mi)",
    pd0["divergencia_total"]["valor_mi"], 0.0, 1e-9)
for _cn in ("cunha_taxa", "cunha_base_lucro", "cunha_bridge_claims", "interacao"):
    chk(f"H2b paridade perfeita: {_cn} ~ 0", pd0["cunhas"][_cn]["valor_mi"], 0.0, 1e-9)
chk_bool("H2c ordem declarada no JSON",
         pd0["ordem"] == ["cunha_taxa", "cunha_base_lucro", "cunha_bridge_claims", "interacao"])
# H2d — caso com as três cunhas ativas: NOPAT com add-backs, dívida e wacc contábil
_claims_d2 = ({"nome": "dívida líquida", "valor_mi": -300.0, "fonte": "teste"},)
inp_div = fixture_sintetico(kd=0.06, wacc=0.12, claims=_claims_d2, nopat=118.0,
                            nde_medido=0.5, de_medido=0.5)
res_div = rodar(inp_div)
pdd = res_div["paridade_decomposta"]
_soma = sum(pdd["cunhas"][c]["valor_mi"] for c in
            ("cunha_taxa", "cunha_base_lucro", "cunha_bridge_claims", "interacao"))
chk("H2d INVARIANTE DURO: soma das cunhas + interação == divergência total",
    _soma, pdd["divergencia_total"]["valor_mi"], 1e-9)
chk_bool("H2e cada cunha publica valor_mi, valor_por_acao, pct_equity_justo e leitura",
         all(set(pdd["cunhas"][c]) >= {"valor_mi", "valor_por_acao", "pct_equity_justo",
                                       "leitura"}
             for c in pdd["ordem"]))
chk_bool("H2f convenção da ponte NOPAT->LL declarada como LÍQUIDA (D2)",
         "LIQUIDA" in pdd["convencoes"]["base_lucro"]
         and pdd["convencoes"]["ll_implicito_mi"] is not None)
# H2g — invariante (b): WACC premissa == consistente -> cunha_taxa == 0
_wc = res_div["ebit_justo"]["consistente"]
_wcons_exato = (0.06 * 300.0 / (300.0 + _wc["e_mkt_mi"])
                + 0.10 * _wc["e_mkt_mi"] / (300.0 + _wc["e_mkt_mi"]))
inp_wc = fixture_sintetico(kd=0.06, wacc=_wcons_exato, claims=_claims_d2, nopat=118.0,
                           nde_medido=0.5, de_medido=0.5)
res_wc = rodar(inp_wc)
chk("H2g wacc premissa == consistente -> cunha_taxa == 0",
    res_wc["paridade_decomposta"]["cunhas"]["cunha_taxa"]["valor_mi"], 0.0, 1e-9)
# H2h — sem kd: bloco degrada declarado
chk_bool("H2h sem kd_liquido: paridade_decomposta.aplicavel=False com motivo",
         res_semkd["paridade_decomposta"]["aplicavel"] is False
         and res_semkd["paridade_decomposta"]["motivo"])
```

- [ ] **Step 2: rodar — H2 FALHA (KeyError `paridade_decomposta`)**

Run: `& $py tests\test_golden_vrsk.py` — Expected: FAIL nas H2*, exit 1.

- [ ] **Step 3: implementar `bloco_paridade_decomposta` (após `bloco_ebit_justo`)**

```python
def bloco_paridade_decomposta(inp, econ, ebit):
    """Entrega B (v3.3.0): a divergência de paridade NÃO é 'dois sinais' — é diagnóstico
    de cunhas específicas. Decomposição determinística por substituição one-at-a-time
    (mesmo padrão do central_neutro), ordem declarada, interação como RESÍDUO explícito.
    Semântica (D10): divergencia_total = rota operacional (WACC premissa) − rota equity;
    cunha_X = parcela da divergência ELIMINADA ao corrigir X sozinho. INVARIANTE DURO:
    cunha_taxa + cunha_base_lucro + cunha_bridge_claims + interacao == divergencia_total
    (tol PARIDADE_DECOMP_TOL). Internamente NADA é arredondado (D9); as chaves publicadas
    arredondam no final. Limiar e comportamento do warning PARIDADE_DIVERGENTE: intocados."""
    if ebit is None:
        return None
    cons = ebit["consistente"]
    if not cons.get("aplicavel"):
        return {"aplicavel": False,
                "motivo": "rota consistente indisponível: " + str(cons.get("motivo"))}
    p, f, meta = inp["premissas"], inp["fatos"], inp["meta"]
    op = p["operacional"]
    nomes = ("bear", "base", "bull")
    cen_eq = p["cenarios"]
    acoes = float(meta["acoes_mi"])
    nopat = float(f["nopat_fy_mi"])
    kd_l = float(op["kd_liquido"])
    w_prem = float(op["wacc"])
    ke_c = float(econ["ke_central"])
    claims_med = sum(float(c["valor_mi"]) for c in f["claims_bridge"])
    nd = -claims_med
    e_mkt = float(econ["central_ponderado"]) * acoes
    v_total = e_mkt + nd
    w_cons = kd_l * nd / v_total + ke_c * e_mkt / v_total
    roics = {n: float(op["cenarios"][n]["margem_nopat"]) * float(op["cenarios"][n]["giro_noa"])
             for n in nomes}
    de, nde, _ = _de_nde(inp)

    def valor_op(wacc_x, nopat_x, claims_x):
        """Rota operacional ponderada em mi, SEM arredondar (D9)."""
        precos = {}
        for n in nomes:
            c = cen_eq[n]
            evn = pl_justo(float(c["g"]), roics[n], float(c["cap"]), wacc_x, 0.0, 0.0,
                           _m_terminal(c))
            precos[n] = evn * nopat_x + claims_x
        return _pond(cen_eq, precos)

    # Alvo: rota equity do gerador, recomputada SEM arredondar (mesmas chamadas pl_justo).
    lpa = float(f["lpa_ajustado_fy"])
    equity_alvo = _pond(cen_eq, {
        n: lpa * pl_justo(float(cen_eq[n]["g"]), float(cen_eq[n]["roe"]),
                          float(cen_eq[n]["cap"]), ke_c, de, nde,
                          _m_terminal(cen_eq[n])) * acoes
        for n in nomes})

    v0 = valor_op(w_prem, nopat, claims_med)
    divergencia = v0 - equity_alvo

    # Cunha 2 — base de lucro, convenção LÍQUIDA (D2): LL_impl = NOPAT − kd_liq × ND
    # (kd já é após imposto — coerente com o bridge de claims líquidos do bloco).
    ll_efetivo = lpa * acoes
    ll_implicito = nopat - kd_l * nd
    nopat_equiv_ll = ll_efetivo + kd_l * nd
    # Cunha 3 — claims implícitas do gerador (D3): bracket NDE sobre o book que o próprio
    # gerador implica (LL_efetivo / ROE_base); com exceção 0/0 dá 0 (cunha de medição).
    book_implicito = ll_efetivo / float(cen_eq["base"]["roe"])
    claims_impl = -(nde * book_implicito)

    cunha_taxa = v0 - valor_op(w_cons, nopat, claims_med)
    cunha_base = v0 - valor_op(w_prem, nopat_equiv_ll, claims_med)
    cunha_claims = v0 - valor_op(w_prem, nopat, claims_impl)
    interacao = divergencia - (cunha_taxa + cunha_base + cunha_claims)
    if abs((cunha_taxa + cunha_base + cunha_claims + interacao) - divergencia) \
            > PARIDADE_DECOMP_TOL:
        raise AssertionError("paridade_decomposta: decomposição não fecha "
                            "(invariante duro v3.3.0 violado)")

    def item(valor, leitura):
        return {"valor_mi": round(valor, 6),
                "valor_por_acao": round(valor / acoes, 4),
                "pct_equity_justo": round(100.0 * valor / equity_alvo, 2),
                "leitura": leitura}

    cunhas = {
        "cunha_taxa": item(cunha_taxa,
            f"Trocar o WACC premissa ({w_prem:.4f}) pelo consistente a pesos de mercado "
            f"({w_cons:.4f}) elimina {cunha_taxa / acoes:+.2f}/ação da divergência."),
        "cunha_base_lucro": item(cunha_base,
            f"Trocar o LL implícito no NOPAT ({ll_implicito:,.1f} mi, convenção líquida) "
            f"pelo LL do gerador ({ll_efetivo:,.1f} mi) elimina "
            f"{cunha_base / acoes:+.2f}/ação — o teste independente dos add-backs."),
        "cunha_bridge_claims": item(cunha_claims,
            f"Trocar as claims medidas ({claims_med:,.1f} mi) pelas implícitas no bracket "
            f"do gerador ({claims_impl:,.1f} mi) elimina "
            f"{cunha_claims / acoes:+.2f}/ação — a cunha de medição do bridge."),
        "interacao": item(interacao,
            "Resíduo explícito da decomposição: interação entre cunhas + diferença "
            "estrutural ROIC-vs-ROE do motor único."),
    }
    return {
        "aplicavel": True,
        "ordem": ["cunha_taxa", "cunha_base_lucro", "cunha_bridge_claims", "interacao"],
        "baseline": "rota operacional ponderada com WACC premissa (mi, sem arredondamento)",
        "alvo": "rota equity do gerador recomputada sem arredondamento "
                "(economico.central_ponderado é a visão arredondada por ação)",
        "equity_alvo_mi": round(equity_alvo, 6),
        "divergencia_total": item(divergencia,
            "Rota operacional (premissa) menos rota equity — mesma direção do "
            "ebit_justo.paridade.delta_pct."),
        "cunhas": cunhas,
        "convencoes": {
            "base_lucro": "LIQUIDA: LL_implicito = NOPAT − kd_liquido × ND_bridge "
                          "(kd líquido já após imposto; coerente com o bridge de claims "
                          "líquidos e o kd_liquido do input — D2/CHANGELOG)",
            "ll_implicito_mi": round(ll_implicito, 2),
            "ll_efetivo_mi": round(ll_efetivo, 2),
            "claims_implicitas_mi": round(claims_impl, 2),
            "claims_medidas_mi": round(claims_med, 2),
            "book_implicito_mi": round(book_implicito, 2),
            "nde_usado": nde,
            "wacc_premissa": w_prem,
            "wacc_consistente": round(w_cons, 6),
        },
        "invariante": "cunha_taxa + cunha_base_lucro + cunha_bridge_claims + interacao == "
                      "divergencia_total (tol 1e-9, verificado no engine e no golden)",
    }
```

Fiação em `rodar()` — trocar o bloco `ebit`/`central_neutro` por:

```python
    ebit = bloco_ebit_justo(inp, econ)
    if ebit is not None:
        res["ebit_justo"] = ebit
        pdec = bloco_paridade_decomposta(inp, econ, ebit)
        if pdec is not None:
            res["paridade_decomposta"] = pdec
```

- [ ] **Step 4: rodar — H2 verde, tudo verde**

Run: `& $py tests\test_golden_vrsk.py` — Expected: exit 0.

- [ ] **Step 5: commit**

```bash
git add skills/er-valuation/engine.py skills/er-valuation/tests/test_golden_vrsk.py
git commit -m "feat(engine): entrega B v3.3.0 - paridade_decomposta por cunha nomeada com invariante duro"
```

---

### Task 3: Entrega C — bloco `ke_alavancagem` (flag, não gerador)

**Files:**
- Modify: `skills/er-valuation/engine.py` (nova função após `bloco_paridade_decomposta`; fiação em `rodar()`)
- Test: `skills/er-valuation/tests/test_golden_vrsk.py` (camada H3)

**Interfaces:**
- Consumes: `fixture_sintetico(..., pl_contabil=...)`, `ebit_justo.consistente`, `KE_REALAVANCAGEM_DRIFT_PP`.
- Produces: chave top-level `ke_alavancagem = {aplicavel, ke, kd_liquido, e_mkt_mi, nd_bridge_mi, vts{valor_mi, formula, aliquota, fonte_aliquota}, ku_mm{valor, formula, politica}, ku_harris_pringle{valor, formula, politica}, nota_convencoes, nota_ke_flat, alavancagem{nd_e_mkt, nd_e_contabil, ke_realavancado_contabil?, convencao_drift?, drift_pp?, limiar_drift_pp?, alerta_drift?, nota?}}`.

- [ ] **Step 1: testes falhando (camada H3)**

```python
# H3 — Entrega C: Ku nas duas convenções DECLARADAS + drift contábil vs mercado
_claims_d3 = ({"nome": "dívida líquida", "valor_mi": -300.0, "fonte": "teste"},)
inp_ka = fixture_sintetico(kd=0.06, wacc=0.10, claims=_claims_d3, pl_contabil=200.0,
                           nde_medido=0.5, de_medido=0.5)
res_ka = rodar(inp_ka)
ka = res_ka["ke_alavancagem"]
_e, _nd, _t = ka["e_mkt_mi"], ka["nd_bridge_mi"], ka["vts"]["aliquota"]
_vts = _t * _nd
chk("H3a VTS = t x ND (perpetuidade a Kd — D4)", ka["vts"]["valor_mi"], round(_vts, 2), 0.01)
chk("H3b Ku_MM == [Ke*E + Kd*(ND-VTS)] / [E + ND - VTS]",
    ka["ku_mm"]["valor"],
    round((0.10 * _e + 0.06 * (_nd - _vts)) / (_e + _nd - _vts), 6), 1e-9)
chk("H3c Ku_HP == (Ke*E + Kd*ND) / (E + ND)",
    ka["ku_harris_pringle"]["valor"],
    round((0.10 * _e + 0.06 * _nd) / (_e + _nd), 6), 1e-9)
chk_bool("H3d VTS>0 -> Ku_MM != Ku_HP (esperado, não é bug) e nenhuma promovida a 'a' resposta",
         ka["ku_mm"]["valor"] != ka["ku_harris_pringle"]["valor"]
         and "julgamento do Modelador" in ka["nota_convencoes"])
_ku_hp = ka["ku_harris_pringle"]["valor"]
_ke_rc = _ku_hp + (_ku_hp - 0.06) * _nd / 200.0
chk("H3e drift: ke_realavancado_contabil na convenção HP (D6)",
    ka["alavancagem"]["ke_realavancado_contabil"], round(_ke_rc, 6), 1e-9)
chk_bool("H3f alerta de drift quando > 0,5 p.p. (constante nomeada como limiar)",
         ka["alavancagem"]["limiar_drift_pp"] == 0.5
         and ka["alavancagem"]["alerta_drift"] == (ka["alavancagem"]["drift_pp"] > 0.5))
chk_bool("H3g ND/E contábil vs mercado reportados lado a lado",
         ka["alavancagem"]["nd_e_mkt"] == round(_nd / _e, 4)
         and ka["alavancagem"]["nd_e_contabil"] == round(_nd / 200.0, 4))
chk_bool("H3h nota: Ke flat do gerador é aproximação da média da trajetória",
         "aproximação da média da trajetória" in ka["nota_ke_flat"])
# H3i — sem pl_contabil: drift degrada com nota; bloco ainda emite os dois Ku
inp_ka2 = fixture_sintetico(kd=0.06, wacc=0.10, claims=_claims_d3)
res_ka2 = rodar(inp_ka2)
chk_bool("H3i sem fatos.pl_contabil_mi: nd_e_contabil=None com nota, Ku presentes",
         res_ka2["ke_alavancagem"]["alavancagem"]["nd_e_contabil"] is None
         and "pl_contabil_mi" in res_ka2["ke_alavancagem"]["alavancagem"]["nota"]
         and res_ka2["ke_alavancagem"]["ku_mm"]["valor"] is not None)
# H3j — sem kd: degrade declarado
chk_bool("H3j sem kd_liquido: ke_alavancagem.aplicavel=False",
         res_semkd["ke_alavancagem"]["aplicavel"] is False)
```

- [ ] **Step 2: rodar — H3 FALHA (KeyError `ke_alavancagem`)**

Run: `& $py tests\test_golden_vrsk.py` — Expected: FAIL nas H3*, exit 1.

- [ ] **Step 3: implementar `bloco_ke_alavancagem`**

```python
def bloco_ke_alavancagem(inp, econ, ebit):
    """Entrega C (v3.3.0): diagnóstico de alavancagem — FLAG, não gerador. Ku implícito
    nas DUAS convenções de política de dívida, com fórmula exata declarada:
    MM/textbook (dívida pré-determinada; VTS descontado a Kd, com net-off) e
    Harris–Pringle (dívida rebalanceada a D/V constante; SEM net-off — o shield tem o
    risco do negócio). Divergem sempre que VTS > 0 — esperado, não é bug; qual se
    aplica é julgamento do Modelador sobre a política de dívida REAL. Ambas usam
    E_mkt do gerador e VTS = PV dos tax shields a Kd (perpetuidade: t × ND — D4)."""
    if ebit is None:
        return None
    cons = ebit["consistente"]
    if not cons.get("aplicavel"):
        return {"aplicavel": False,
                "motivo": "rota consistente indisponível: " + str(cons.get("motivo"))}
    p, f, meta = inp["premissas"], inp["fatos"], inp["meta"]
    op = p["operacional"]
    ke = float(econ["ke_central"])
    kd_l = float(op["kd_liquido"])
    acoes = float(meta["acoes_mi"])
    e_mkt = float(econ["central_ponderado"]) * acoes
    nd = -sum(float(c["valor_mi"]) for c in f["claims_bridge"])
    imp = p.get("impostos") or {}
    if imp.get("marginal") is not None:
        t_vts, fonte_t = float(imp["marginal"]), "premissas.impostos.marginal"
    else:
        t_vts = float(op["aliquota_operacional"])
        fonte_t = "premissas.operacional.aliquota_operacional (fallback: marginal não declarada)"
    vts = t_vts * nd
    den_mm = e_mkt + nd - vts
    ku_mm = ((ke * e_mkt + kd_l * (nd - vts)) / den_mm) if abs(den_mm) > 1e-9 else None
    ku_hp = (ke * e_mkt + kd_l * nd) / (e_mkt + nd)
    out = {
        "aplicavel": True,
        "ke": ke,
        "kd_liquido": kd_l,
        "e_mkt_mi": round(e_mkt, 2),
        "nd_bridge_mi": round(nd, 2),
        "vts": {"valor_mi": round(vts, 2),
                "formula": "VTS = t × ND (PV perpétuo dos tax shields descontado a Kd: "
                           "t·Kd·ND/Kd — forma fechada)",
                "aliquota": t_vts, "fonte_aliquota": fonte_t},
        "ku_mm": {"valor": round(ku_mm, 6) if ku_mm is not None else None,
                  "formula": "Ku_MM = [Ke·E_mkt + Kd·(ND − VTS)] / [E_mkt + ND − VTS] "
                             "(equivale a Ke = Ku + (Ku − Kd)·(ND − VTS)/E_mkt)",
                  "politica": "dívida PRÉ-DETERMINADA; VTS descontado a Kd (MM 1963)"},
        "ku_harris_pringle": {"valor": round(ku_hp, 6),
                              "formula": "Ku_HP = (Ke·E_mkt + Kd·ND) / (E_mkt + ND) "
                                         "(equivale a Ke = Ku + (Ku − Kd)·ND/E_mkt, SEM o "
                                         "termo −VTS)",
                              "politica": "dívida REBALANCEADA a D/V de mercado constante; "
                                          "shield com o risco do negócio (Harris–Pringle 1985)"},
        "nota_convencoes": "As duas convenções divergem sempre que VTS > 0 — esperado, não é "
                           "bug. Nenhuma é promovida a 'a' resposta: a política de dívida REAL "
                           "(pré-determinada vs rebalanceada) decide qual se aplica, e isso é "
                           "julgamento do Modelador, não do engine.",
        "nota_ke_flat": "O Ke flat do gerador é aproximação da média da trajetória de "
                        "alavancagem; este diagnóstico quantifica quando a aproximação importa.",
    }
    alav = {"nd_e_mkt": round(nd / e_mkt, 4)}
    pl_cont = f.get("pl_contabil_mi")
    if pl_cont is not None and float(pl_cont) > 0:
        e_cont = float(pl_cont)
        ke_rc = ku_hp + (ku_hp - kd_l) * nd / e_cont
        drift_pp = abs(ke_rc - ke) * 100.0
        alav.update({
            "nd_e_contabil": round(nd / e_cont, 4),
            "ke_realavancado_contabil": round(ke_rc, 6),
            "convencao_drift": "Harris–Pringle (sem net-off de VTS — D6)",
            "drift_pp": round(drift_pp, 2),
            "limiar_drift_pp": KE_REALAVANCAGEM_DRIFT_PP,
            "alerta_drift": drift_pp > KE_REALAVANCAGEM_DRIFT_PP,
        })
    else:
        alav["nd_e_contabil"] = None
        alav["nota"] = ("fatos.pl_contabil_mi ausente — ND/E contábil e o alerta de drift de "
                       "Ke re-alavancado degradam com nota (campo opcional novo, v3.3.0)")
    out["alavancagem"] = alav
    return out
```

Fiação em `rodar()` (dentro do `if ebit is not None:` da Task 2):

```python
        keal = bloco_ke_alavancagem(inp, econ, ebit)
        if keal is not None:
            res["ke_alavancagem"] = keal
```

- [ ] **Step 4: rodar — H3 verde, tudo verde**

Run: `& $py tests\test_golden_vrsk.py` — Expected: exit 0.

- [ ] **Step 5: commit**

```bash
git add skills/er-valuation/engine.py skills/er-valuation/tests/test_golden_vrsk.py
git commit -m "feat(engine): entrega C v3.3.0 - diagnostico ke_alavancagem (Ku MM vs Harris-Pringle, drift contabil vs mercado)"
```

---

### Task 4: Versão, CHANGELOG, schema e SKILL.md

**Files:**
- Modify: `skills/er-valuation/engine.py` (`ENGINE_VERSION`, CHANGELOG topo)
- Modify: `skills/er-valuation/inputs_exemplo_vrsk.yaml` (comentários; dados INALTERADOS)
- Modify: `skills/er-valuation/SKILL.md` (tabela §1 + parágrafo §2b)

**Interfaces:**
- Consumes: nomes de chave produzidos nas Tasks 1–3 (exatamente: `ebit_justo.premissa`, `ebit_justo.consistente`, `paridade_decomposta`, `ke_alavancagem`).

- [ ] **Step 1: teste falhando — versão**

```python
from engine import ENGINE_VERSION as _EV
chk_bool("H4a ENGINE_VERSION == 3.3.0", _EV == "3.3.0")
```

Run: Expected FAIL (`3.2.0`).

- [ ] **Step 2: bump + CHANGELOG (topo do engine.py, acima da entrada v3.2.0; ≤ 10 linhas)**

```python
# v3.3.0 (2026-07-28): paridade EXATA em taxa + divergência decomposta (aditivo; gerador intocado).
#   (A) ebit_justo.consistente: WACC a pesos de MERCADO (E_mkt = equity justo do gerador ×
#       ações; ND = −Σ claims do bridge; kd_liquido input opcional H8) ao lado da premissa —
#       sem circularidade: E_mkt não depende do WACC. Cadeia EV/NOPAT→EBIT→EBITDA nas duas taxas.
#   (B) paridade_decomposta: divergência op−equity por cunha nomeada one-at-a-time (taxa, base
#       de lucro, bridge de claims) + interação residual; INVARIANTE soma==divergência (1e-9).
#       Ponte NOPAT→LL na convenção LÍQUIDA (kd_liquido a.t. × ND do bridge) — o bloco opera
#       integralmente em claims líquidos; PARIDADE_DIVERGENTE passa a referenciar o bloco.
#   (C) ke_alavancagem (flag): Ku_MM vs Ku_HP com fórmulas declaradas, VTS=t×ND a Kd, ND/E
#       contábil vs mercado e alerta de drift de Ke re-alavancado > 0,5 p.p. (constante).
ENGINE_VERSION = "3.3.0"
```

- [ ] **Step 3: schema — inserir comentários no `inputs_exemplo_vrsk.yaml`** (no fim do bloco `fatos`, e como referência do bloco `premissas`; NENHUM dado ativo muda):

```yaml
  # NOVO v3.3.0 (OPCIONAL): patrimônio líquido contábil (mi) — alimenta ND/E contábil e o
  # alerta de drift de Ke re-alavancado em ke_alavancagem. Ausente = diagnóstico degrada
  # com nota. Exemplo VRSK: não coletado na sessão original (por isso comentado).
  # pl_contabil_mi: 9300

  # NOVO v3.3.0 (OPCIONAIS, dentro de premissas.operacional — só relevantes quando o bloco
  # operacional existe; este exemplo não o usa):
  #   kd_liquido: 0.045       # custo de dívida LÍQUIDO após imposto (fração). Habilita
  #                           # ebit_justo.consistente (WACC a pesos de MERCADO),
  #                           # paridade_decomposta e ke_alavancagem. Ausente = os três
  #                           # degradam com aplicavel=false declarado (default seguro).
  #   fonte_kd: "..."         # obrigatória quando kd_liquido é declarado (disciplina H8).
```

- [ ] **Step 4: SKILL.md — 3 linhas novas na tabela da §1** (após a linha do `central_neutro`):

```markdown
| Rota consistente em taxa (v3.3) | WACC a pesos de MERCADO na rota de reconciliação (E_mkt = equity justo do gerador; ND do bridge), lado a lado com o WACC premissa; cadeia EV/NOPAT→EBIT→EBITDA nas duas taxas | `ebit_justo.consistente` |
| Paridade decomposta (v3.3) | Divergência das âncoras decomposta por cunha nomeada one-at-a-time (taxa, base de lucro, bridge de claims) + interação residual; invariante soma==divergência (1e-9) | `paridade_decomposta` |
| Diagnóstico de alavancagem (v3.3) | Ku implícito nas duas convenções (MM/textbook e Harris–Pringle) com fórmula declarada, ND/E contábil vs mercado e alerta de drift de Ke re-alavancado (>0,5 p.p.) — flag, nunca gerador | `ke_alavancagem` |
```

- [ ] **Step 5: SKILL.md — parágrafo novo na §2b** (após o bullet "Paridade das âncoras"):

```markdown
- **Paridade decomposta e WACC consistente (v3.3.0).** A divergência de paridade não é
  "dois sinais": é diagnóstico de cunhas específicas. Com `premissas.operacional.kd_liquido`
  declarado, o engine emite a rota operacional TAMBÉM no `wacc_consistente` (pesos a valor
  de MERCADO, com E_mkt = equity justo do gerador — pesos contábeis são artefato
  metodológico, não sinal) e decompõe a divergência em `paridade_decomposta`: cunha de taxa,
  cunha de base de lucro (ponte NOPAT→LL na convenção líquida — o teste independente dos
  add-backs) e cunha do bridge de claims, com interação residual explícita e invariante duro
  (soma == divergência, 1e-9). O warning `PARIDADE_DIVERGENTE` referencia o bloco; limiar de
  10% e o não-bloqueio de publicação (condição 3) ficam INALTERADOS. `ke_alavancagem`
  quantifica quando o Ke flat importa (Ku MM vs Harris–Pringle — a política de dívida real é
  julgamento do Modelador).
```

- [ ] **Step 6: rodar suíte + engine no exemplo canônico sem modificação**

Run: `& $py tests\test_golden_vrsk.py` — Expected: exit 0 (inclui H0 byte-a-byte: comentários YAML não mudam dados).
Run: `& $py engine.py inputs_exemplo_vrsk.yaml --out <scratchpad>\v330_check` — Expected: `[engine v3.3.0] resultados -> ...` sem erro.

- [ ] **Step 7: commit**

```bash
git add skills/er-valuation/engine.py skills/er-valuation/inputs_exemplo_vrsk.yaml skills/er-valuation/SKILL.md skills/er-valuation/tests/test_golden_vrsk.py
git commit -m "docs(engine): v3.3.0 - CHANGELOG, schema opcional (kd_liquido/pl_contabil_mi) e SKILL.md (secoes 1 e 2b)"
```

---

### Task 5: Verificação final + code review por subagente + relatório

**Files:** nenhum novo (evidências no relatório).

- [ ] **Step 1 (verification-before-completion):** rodar a suíte completa e capturar a saída integral; rodar o diff byte-a-byte independente: `resultados.json` v3.3.0 do golden VRSK vs baseline v3.2.0 congelado no scratchpad (`baseline_v320/resultados.json`), comparando TODAS as chaves top-level exceto `engine` — diff vazio obrigatório.
- [ ] **Step 2:** conferir checklist de aceite item a item (suíte verde; regressão byte-a-byte; paridade perfeita ≤1e-9; soma das cunhas == divergência; yaml roda sem modificação; SKILL/CHANGELOG/versão; cap_check.py e snapshot.py intocados — `git diff --stat` como evidência).
- [ ] **Step 3 (requesting-code-review):** despachar subagente revisor com o diff completo `git diff main...feat/engine-v330` + regras duras da Seção 3 do pedido como critérios; tratar o retorno via superpowers:receiving-code-review (rigor técnico, nada de concordância performativa).
- [ ] **Step 4:** relatório final: o que mudou (por entrega), evidência dos testes (saída da suíte + diff de regressão), confirmações do Damodaran (URL + trechos + registro de indisponibilidade dos pontos 2–3), limitações remanescentes declaradas (Ke flat ≈ média da trajetória; VTS em forma fechada de perpetuidade; interação absorve a diferença estrutural ROIC-vs-ROE; decisão de qual convenção de Ku aplicar permanece com o Modelador).

---

## ADENDO PÓS-APROVAÇÃO (2026-07-28) — 4 ajustes do usuário, SUPERSEDEM os trechos correspondentes acima

**(1) D5 revisto (BLOQUEANTE) — `kd_pre_imposto` é o input primitivo.**
- Input novo: `premissas.operacional.kd_pre_imposto` (fração, PRÉ-imposto) + `fonte_kd` (obrigatória se presente). NÃO existe input `kd_liquido`.
- Derivação no engine: `kd_liquido = kd_pre_imposto × (1 − t_kd)`, com `t_kd = premissas.impostos.marginal` se declarada, senão `aliquota_operacional` — helper module-level, DRY:

```python
def _aliquota_kd(p, op):
    """v3.3.0: alíquota da camada de dívida (deriva kd líquido e a ponte NOPAT→LL).
    Marginal declarada tem precedência; fallback para a operacional, sempre declarado."""
    imp = p.get("impostos") or {}
    if imp.get("marginal") is not None:
        return float(imp["marginal"]), "premissas.impostos.marginal"
    return (float(op["aliquota_operacional"]),
            "premissas.operacional.aliquota_operacional (fallback: marginal não declarada)")
```

- **Usos:** WACC consistente (Entrega A) e ponte NOPAT→LL (Entrega B) usam `kd_liquido` (derivado); Ku_MM, Ku_HP e o drift de re-alavancagem (Entrega C) usam `kd_pre_imposto`. Saída declara os dois + `aliquota_kd`/`fonte_aliquota_kd`.
- Validação (substitui o 3b da Task 1): mesmo texto trocando `kd_liquido` → `kd_pre_imposto` ("custo de dívida PRÉ-imposto, fração").
- **Referência recomputada (congelar nos testes):** Ke=22%, kd_pre=16,65%, t=30% (⇒ kd_liq=11,655%), ND=30, E_book=65, E_mkt=150,5 → WACC consistente 20,281% (inalterado, usa líquido); Ku_HP = (0,22·150,5+0,1665·30)/180,5 = 21,111%; ke_realav_contabil = 21,111%+(21,111%−16,65%)·30/65 = 23,17% → **drift 1,17 p.p.** (não 2,26).
- Fixture sintético: parâmetro `kd_pre=0.075` com `aliquota_operacional=0.20` ⇒ kd_liquido = 0,06 (expectativas H1e/H2g preservadas). Teste novo H1e2: `chk("kd_liquido derivado = kd_pre×(1−t)", eb1["kd_liquido"], 0.06, 1e-12)`. Testes H1g/H1h/H3* trocam `kd_liquido` → `kd_pre_imposto`; fórmulas esperadas de H3b/H3c/H3e usam 0,075.

**(2) D4 mantido com premissa e viés DECLARADOS na saída.** O dict `vts` ganha:

```python
"premissa": "dívida CONSTANTE e perpétua (VTS = t×ND = PV a Kd de t·Kd·ND — forma fechada)",
"vies": "subestima o VTS quando a dívida CRESCE (caso de referência: 9,00 vs 15,86); com "
        "Ke > Kd, VTS subestimado implica Ku_MM SUBESTIMADO (Ku_HP não usa VTS)",
```

Teste novo H3k: `chk_bool(..., "constante" in ka["vts"]["premissa"] and "subestima" in ka["vts"]["vies"])`.

**(3) D10 + warning de interação dominante.** Constante nova `PARIDADE_INTERACAO_LIMIAR_PCT = 25.0`. Em `paridade_decomposta`:

```python
    warning = None
    if abs(divergencia) > 1e-6 and \
            abs(interacao) > (PARIDADE_INTERACAO_LIMIAR_PCT / 100.0) * abs(divergencia):
        warning = "DECOMPOSICAO_POUCO_INFORMATIVA"
```

(guarda `> 1e-6` mi evita disparo espúrio por ruído de ponto flutuante no caso de paridade perfeita). Saída ganha `"warning": warning` e `"limiar_interacao_pct": PARIDADE_INTERACAO_LIMIAR_PCT`. Testes: paridade perfeita → warning None; caso ajustado com cunhas que se cancelam (params congelados durante o TDD após cálculo determinístico) → warning presente.

**(4) D2 com alíquota da ponte declarada por chave.** `paridade_decomposta.convencoes` ganha `"aliquota_ponte": t_kd`, `"fonte_aliquota_ponte": fonte_t_kd`, `"kd_pre_imposto"`, `"kd_liquido"`; e, quando `impostos.marginal` declarada e ≠ `aliquota_operacional`:

```python
        convencoes["nota_camada_imposto"] = (
            f"aliquota operacional ({t_op}) ≠ marginal ({t_mg}): a diferença de camada de "
            "imposto cai DENTRO de cunha_base_lucro (não é cunha separada)")
```

CHANGELOG revisado menciona: kd_pre_imposto primitivo, alíquota declarada, warning novo — mantendo ≤ 10 linhas.

---

## Self-Review (executado)

1. **Cobertura da spec:** Entrega A → Task 1; Entrega B → Task 2 (ordem declarada, invariante, % equity, leitura por template, warning referencia o bloco, limiares intactos); Entrega C → Task 3 (fórmulas exatas, duas convenções lado a lado, ND/E contábil vs mercado, alerta 0,5 p.p. como constante, nota do Ke flat); regras duras → Global Constraints + Tasks 0/4/5; Damodaran → seção própria (1 confirmado com URL/trecho; 2–3 por teoria nomeada, degrade previsto); aceite → Task 5.
2. **Placeholders:** nenhum TBD/TODO; todo step com código completo.
3. **Consistência de tipos/nomes:** chaves `premissa`/`consistente`/`paridade_decomposta`/`ke_alavancagem` idênticas entre tasks, testes e SKILL.md; `fixture_sintetico` definido na Task 1 e consumido nas 2–3; constantes `KE_REALAVANCAGEM_DRIFT_PP`/`PARIDADE_DECOMP_TOL` definidas na Task 1 e usadas nas 2–3.
