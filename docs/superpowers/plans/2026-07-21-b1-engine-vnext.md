# B1 — Engine vNEXT (v3.1.0): Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans (inline). Steps usam
> checkbox. TDD estrito: teste RED antes de cada implementação. Commits por task NA BRANCH
> `upgrade-v2-b1`; merge na main SOMENTE após aprovação do gate da fase pelo usuário.

**Goal:** engine v3.1.0 aditivo com `sensibilidade_phi` (exclusão mútua com m_terminal),
`fatos.reformulado` validado na carga + gates H7 provisórios, bloco `ebit_justo` (âncora
operacional no motor único, com bridge de claims, paridade-WARNING, reverse e elasticidades) e
tabela história→números — mais a passada única de contrato (checar/compor/linter).

**Architecture:** todos os blocos são ADITIVOS e gated por presença: inputs antigos produzem
todas as chaves antigas idênticas (+ `sensibilidade_phi`, sempre emitido). Núcleo `pl_justo()`
INTOCADO. A âncora operacional reusa `pl_justo(g, roic, cap, wacc)` trailing (fator (1+g) só
documenta comparação com forward; NUNCA aplicado — restrição m_terminal≠1 medida no B0).

**Tech Stack:** Python stdlib (engine), pytest; portable python `C:\Claude\tools\python-nupkg\tools\python.exe`.

## Global Constraints

- Regressão: chaves antigas de `resultados.json` idênticas para inputs antigos (exceto
  `engine.{versao,gerado_em}`); núcleo 1e-12; `test_golden_vrsk.py`, `test_regressao_fnv.py`,
  `test_correcoes_hg.py` e demais 212 testes SEM EDIÇÃO e verdes.
- Nada de: segundo motor, DCF, projeção de demonstrativos, WACC derivado do balanço, sinal novo
  no contrato `sinais` (âncora operacional é ROTA DE RECONCILIAÇÃO).
- Condição 3 (aprovação): paridade divergente = WARNING + nota de resolução; checar emite AVISO
  (nunca `falta`) quando DIVERGE sem nota — ZERO bloqueio novo de publicação. Decisão registrada
  no CHANGELOG; reavaliar após 3 análises reais.
- Condição 7: limiares H7 com constante `H7_CALIBRACAO = "PROVISORIO_N3"` + comentário de
  recalibração; ecoada no JSON.
- Convenções do repo: mensagens de commit em pt-BR minúsculo estilo `feat:`/`test:`/`docs:`;
  sem alterar fixtures FNV/VRSK existentes.

---

### Task 1: Baseline + fixture TFCO4

**Files:** Create: `tests/fixtures/tfco4/inputs_b1.yaml`; Create: `tests/test_engine_b1.py` (só baseline)
**Interfaces → Produces:** fixture TFCO4 com os números reconstruídos no B0
(`C:\Claude\referencia\verificacao\tfco4_inputs.yaml` — copiar conteúdo, é hash-livre aqui);
helper `rodar_fixture(path) -> dict` usado por todas as tasks seguintes.

- [ ] **Step 1:** copiar o inputs TFCO4 do B0 para `tests/fixtures/tfco4/inputs_b1.yaml`.
- [ ] **Step 2:** `test_engine_b1.py::test_baseline_tfco4` — roda o engine e asserta o estado ATUAL
  (âncora da regressão B1): `economico.central_ponderado == 8.34`, `sinais.premio_sobre_econ_central_pct == 79.7`,
  `reverse.cap_implicito_econ_base == 42.8631`, `hurdle.cenarios.ponderado == 9.01`.
- [ ] **Step 3:** rodar (`pytest tests/test_engine_b1.py -q`) → PASS; commit
  `test: baseline b1 com fixture tfco4 reconstruida (b0)`.

### Task 2: `sensibilidade_phi` + exclusão mútua φ×m_terminal

**Files:** Modify: `skills/er-valuation/engine.py` (novo `bloco_sensibilidade_phi`, chamada em
`rodar()`, validação da exclusão mútua em `bloco_validacao`); Test: `tests/test_engine_b1.py`
**Interfaces → Produces:** chave `sensibilidade_phi` SEMPRE presente:
`{aplicavel: bool, motivo_na: str|None, ancora: "economico_central", grid: [{phi, m_por_cenario:{bear,base,bull}, central_ponderado, premio_vs_preco_pct, cap_equivalente_base}], nota}`.
Fórmula (validada no B0 com erro 0,00 vs engine): `m(φ) = 1 + φ·(roe−ke)/ke` por cenário;
`cap_equivalente_base` = bisseção de `pl_justo(g,roe,c,ke,de,nde,1) == pl_justo(g,roe,cap,ke,de,nde,m(φ))` no cenário base.
Grid fixo `[0, 0.25, 0.5, 1.0]` (φ>1 é incoerente — B0/φ*: spread terminal > spread de franquia).

- [ ] **Step 1 (RED):** testes com os números MEDIDOS no B0/FASE A (fixture TFCO4, Ke central 14%):
```python
def test_phi_grid_tfco4():
    res = rodar_fixture(FIX_TFCO4)
    sp = res["sensibilidade_phi"]; assert sp["aplicavel"] is True
    pond = {g["phi"]: g["central_ponderado"] for g in sp["grid"]}
    assert pond[0.0] == res["economico"]["central_ponderado"]          # identidade φ=0
    assert abs(pond[0.25] - 8.88) <= 0.01 and abs(pond[0.5] - 9.41) <= 0.01 and abs(pond[1.0] - 10.49) <= 0.01
    caps = {g["phi"]: g["cap_equivalente_base"] for g in sp["grid"]}
    assert abs(caps[0.25] - 13.76) <= 0.05 and abs(caps[0.5] - 15.58) <= 0.05 and abs(caps[1.0] - 19.41) <= 0.05

def test_phi_na_com_m_terminal_manual():
    res = rodar_fixture(FIX_FNV_P3)      # FNV usa m_terminal 2.5/4.0/5.2
    sp = res["sensibilidade_phi"]
    assert sp["aplicavel"] is False and "m_terminal" in sp["motivo_na"]

def test_phi_exclusao_mutua_recusa():
    inp = carregar(FIX_FNV_P3); inp["premissas"]["phi"] = 0.5
    with pytest.raises(ValueError, match="exclus"):
        engine.rodar(inp)
```
- [ ] **Step 2:** rodar → FAIL (KeyError sensibilidade_phi). **Step 3:** implementar. **Step 4:** PASS + 212 antigos verdes. **Step 5:** commit `feat: sensibilidade_phi de primeira classe com exclusao mutua m_terminal (h11)`.

### Task 3: `fatos.reformulado` — validação na carga + derivados + diagnóstico

**Files:** Modify: `skills/er-valuation/engine.py`; Test: `tests/test_engine_b1.py`; Create: `tests/fixtures/tfco4/reformulado_tf.yaml` (série TF real 2020-2024 dos recomputos B0/FASE A)
**Interfaces → Produces:** input opcional `fatos.reformulado {unidade, fonte, serie: [{ano, receita, ebit, nopat, noa_medio, nd_medio, e_medio, e_fim, nie_pos_imposto, ni_recorrente?, noa_medio_ex_goodwill?}]}`.
Saída `fatos_reformulado {serie: [entrada + margem_nopat, giro_noa, roic, roic_ex_goodwill?, nbc|None, flev, roe_ponte, roe_direto], diagnostico: {janela, roiic_acumulado, rir_medio, g_nopat_acumulado}, validacoes: [...]}`.
Regras (ERRO na carga, tol relativa 0,5% — inputs coletados à mão): CE≡NOA
(`|nd_medio+e_medio−noa_medio| ≤ 0.005·|noa_medio|`); `ni_recorrente ≈ nopat + nie_pos_imposto`;
se o input declarar `roic`/`roe`, validar contra o derivado (1e-3 abs). `nbc = None` (com nota)
quando `|nd_medio| < 0.02·noa_medio` (base minúscula — TF 2024, evidência FASE A).
Diagnóstico H6 em JANELA ACUMULADA (nunca anual): `roiic_acumulado = (nopat_N − nopat_1)/(noa_N−1 − noa_0)`.

- [ ] **Step 1 (RED):** série TF 2020-2024 (números REAIS do recomputo B0 — h6_h7): NOA 167.078,6/283.662,5/371.531,5/467.425,2/470.714,0; NOPAT 31.364,9/81.389,3/100.302,2/124.256,1/120.214,4; asserts: `serie[-1].roic ≈ 0.2563` (1e-3), `roe_ponte ≈ roe_direto` (1e-6), `diagnostico.roiic_acumulado ≈ 0.293` (recompute no teste), erro com CE≢NOA (mutila nd_medio → pytest.raises), erro com ni ≠ nopat+nie.
- [ ] **Step 2:** FAIL. **Step 3:** implementar (`bloco_fatos_reformulado`, chamado só quando input presente). **Step 4:** PASS. **Step 5:** commit `feat: fatos.reformulado com invariantes na carga e diagnostico roiic/rir em janela (h1/h6)`.

### Task 4: Gates H7 (PROVISÓRIOS n=3)

**Files:** Modify: `skills/er-valuation/engine.py` (constantes + `_gates_h7(serie)` dentro do bloco reformulado); Test: `tests/test_engine_b1.py`
**Interfaces → Produces:** `fatos_reformulado.gates_aplicabilidade {calibracao: "PROVISORIO_N3", ancora_equity: "EQUITY_OK"|"GATE_DISPARA", ancora_primaria_recomendada: "EQUITY"|"OPERACIONAL", eliminatorios: {a1_e_positivo, a2_mediana_e_noa, a3_lucro_recorrente}, flags: [{codigo: "FLEV_CRUZA_SINAL"|"NBC_INSTAVEL"|"ND_IMATERIAL", detalhe}], limiares: {...}, nota_recalibracao}`.
Constantes com comentário obrigatório (condição 7):
```python
H7_CALIBRACAO = "PROVISORIO_N3"  # calibrado em n=3 (TF/Lopes/PVV, FASE A+B0); RECALIBRAR a cada caso novo
H7_MIN_E_NOA_MEDIANA = 0.30      # separação medida: PVV max -0.04 vs TF/Lopes min 0.93
H7_ND_IMATERIAL = 0.10
H7_NBC_RATIO_MAX = 2.0
H7_FLEV_MATERIAL = 0.20
```
Eliminatórios (A1 `e_fim > 0` todos os anos; A2 mediana `e_medio/noa_medio ≥ 0.30`; A3 último
`ni_recorrente > 0` E mediana > 0) decidem a âncora; A4/F1/F2 são FLAGS (degradam o diagnóstico
da ponte — evidência TF: 1 cruzamento benigno não pode expulsar a âncora).

- [ ] **Step 1 (RED):** série TF → `EQUITY_OK` com flag `FLEV_CRUZA_SINAL` (2020 net cash) e SEM
  `NBC_INSTAVEL`... (asserts pela tabela do B0: TF |FLEV|méd 0.126 < 0.20 → F1 não dispara);
  série PVV 2022-2025 (E −7.624,9/−25.724,6/+1.414,3/+9.211,7; NOA 30.012,9/19.610,5/16.742,3/20.370,2;
  NI −44.361,6/−29.990,1/−15.110,0/−13.504,7) → `GATE_DISPARA` (A1+A2+A3) e
  `ancora_primaria_recomendada == "OPERACIONAL"`; `calibracao == "PROVISORIO_N3"`.
- [ ] **Step 2:** FAIL. **Step 3:** implementar. **Step 4:** PASS. **Step 5:** commit `feat: gates de aplicabilidade da ancora equity, provisorios n=3 (h7)`.

### Task 5: `ebit_justo` núcleo — cenários margem×giro, cadeia, bridge, preço

**Files:** Modify: `skills/er-valuation/engine.py`; Test: `tests/test_engine_b1.py`
**Interfaces → Consumes:** `pl_justo` (inalterado). **Produces:** inputs opcionais:
```yaml
fatos:
  nopat_fy_mi: 147.7          # base trailing, mesma moeda de claims; gate de base normalizada via nota
  da_sobre_ebitda: 0.0667     # opcional: habilita ev_ebitda
  claims_bridge:              # H4: sinal = contribuição ao EQUITY (dívida negativa, caixa/NOL positivos)
    - {nome: caixa_livre, valor_mi: 0.0, fonte: "..."}
premissas:
  operacional:
    wacc: 0.14                # RECEBIDO como premissa (H8); nunca derivado
    fonte_wacc: "dossiê de Ke §..."
    aliquota_operacional: 0.27
    fonte_aliquotas: "..."
    cenarios: {bear: {margem_nopat: 0.13, giro_noa: 1.5}, base: {...}, bull: {...}}
    drivers_narrativos: {bear: "...", base: "...", bull: "..."}   # opcional (história→números)
    nota_paridade: "..."      # obrigatória SÓ quando paridade DIVERGE
```
Saída `ebit_justo {wacc, fonte_wacc, aliquotas, cenarios: {<n>: {margem_nopat, giro_noa, roic, rir_implicito_terminal, ev_nopat_justo, ev_ebit_justo, ev_ebitda_justo?, ev_mi, equity_mi, preco}}, ponderado_preco, bridge {claims, total_mi}, convencao: "trailing; forward = (1+g)×trailing SÓ com m_terminal=1 (B0)"}`.
Cálculo: `roic = margem×giro` (validação g < roic por cenário — mesmo erro do motor equity);
`ev_nopat_justo = pl_justo(g, roic, cap, wacc, 0, 0, m_terminal_cen)` (g/cap/prob/m_terminal
HERDADOS de `premissas.cenarios` — uma única tabela de cenários, anti-empilhamento);
`ev_ebit = ev_nopat×(1−t_oper)`; `ev_ebitda = ev_nopat×(1−t_oper)(1−d)`;
`ev_mi = ev_nopat×nopat_fy_mi`; `equity_mi = ev_mi + Σ claims`; `preco = equity_mi/acoes_mi`.

- [ ] **Step 1 (RED):** caso JM sintético (aceitação do B0, 1e-9): cenários iguais nos 3 (margem×giro
  = ROIC do JM = `C180`; g=0.11; cap=10; wacc=0.187332; t=0.30; d=`C181`) →
  `ev_nopat_justo == 5.792402102481976`; `ev_ebit == 5.7924021×0.70`; `ev_ebitda == C193/1.11` (=3.7843693735...; calcular no teste como `4.200650004719926/1.11`); com `nopat_fy_mi=29.4`, claims=[caixa 0] e acoes=1 → `preco == 5.7924021×29.4×...`; erro quando `g >= roic`.
- [ ] **Step 2:** FAIL. **Step 3:** implementar `bloco_ebit_justo` (gated: presente sse
  `premissas.operacional` E `fatos.nopat_fy_mi`). **Step 4:** PASS. **Step 5:** commit
  `feat: bloco ebit_justo no motor unico — cenarios margem x giro, cadeia (1-t)(1-d), bridge de claims (h9/h4)`.

### Task 6: Paridade (WARNING), reverse operacional, elasticidades operacionais

**Files:** Modify: `skills/er-valuation/engine.py`; Test: `tests/test_engine_b1.py`
**Produces:** dentro de `ebit_justo`:
- `paridade {preco_equity_central, preco_op_ponderado, delta_pct, limiar_pct: 10.0, status: CONVERGE|DIVERGE, warning: "PARIDADE_DIVERGENTE"|None, nota_resolucao: str|None, instrucao}` — condição 3: warning, NUNCA erro; nota vem de `premissas.operacional.nota_paridade`.
- `reverse {roic_implicito_no_preco, cap_implicito_op, wacc_implicito}` (bisseções sobre pl_justo com inputs operacionais; base = cenário base op; alvo = EV implícito no preço: `(preco_atual×acoes − Σclaims)/nopat_fy`).
- `elasticidades {preco_base, mais_1pp_margem, mais_01x_giro, mais_1a_cap, menos_05pp_wacc, experimento: {...4 textos...}, alertas_sinal: [...]}` (padrão R4: spread = roic>wacc).

- [ ] **Step 1 (RED):** paridade exata: fixture TFCO4 + operacional consistente (margem×giro = ROE
  0.22, wacc = 0.14 = Ke central, nopat_fy = 0.95×acoes, claims vazio+caixa 0, m_terminal 1) →
  `delta_pct == 0.0` (1e-6), `status == "CONVERGE"`; wedge de add-backs: `nopat_fy = 1.12×acoes`
  → `preco_op/preco_equity == 1.1789` (1e-3) → `DIVERGE` + `warning == "PARIDADE_DIVERGENTE"` e
  `nota_resolucao is None`; reverse: `roic_implicito` devolve alvo (round-trip 1e-6);
  alertas: cenário com roic < wacc e `mais_1a_cap > 0` → alerta (construído no teste).
- [ ] **Step 2:** FAIL. **Step 3:** implementar. **Step 4:** PASS. **Step 5:** commit
  `feat: paridade das ancoras como warning com nota, reverse e elasticidades operacionais (h9/r4; condicao 3)`.

### Task 7: História→números + camadas de imposto (eco)

**Files:** Modify: `skills/er-valuation/engine.py`; Test: `tests/test_engine_b1.py`
**Produces:** `ebit_justo.historia_numeros {<cenario>: {historia: drivers_narrativos|"—", premissa: "margem X × giro Y", implicito: {roic, rir_terminal: "g/roic", g}, evidencia: fonte_wacc/fonte_aliquotas eco}}` (chave SEMPRE presente quando ebit_justo presente — condição 6; aviso quando drivers ausentes);
`impostos {operacional, marginal?, terminal?, fontes}` (eco de `premissas.impostos` + `aliquota_operacional`; warning nomeado `ALIQUOTA_TERMINAL_NAO_DECLARADA` quando ebit_justo presente sem `premissas.impostos.terminal` — evidência TF: 27→34% move EV −12,6%).

- [ ] **Step 1 (RED):** asserts de presença/conteúdo da tabela por cenário; warning de terminal
  ausente; dupla penalização: bear com margem bear E giro bear simultâneos SEM
  `premissas.operacional.justificativa_dupla_penalizacao` → aviso nomeado `DUPLA_PENALIZACAO_BEAR`
  (H6/Seção 5 do prompt master; aviso, não erro).
- [ ] **Step 2:** FAIL. **Step 3:** implementar. **Step 4:** PASS. **Step 5:** commit
  `feat: tabela historia->numeros por chave e camadas de imposto ecoadas (condicao 6; h5)`.

### Task 8: Passada única de contrato — checar + compor + linter

**Files:** Modify: `skills/er-relatorio/checar.py` (`OBRIG_JSON_V31` condicional + aviso paridade),
`skills/er-relatorio/compor.py` (3 seções novas + `humano()`); Test: `tests/test_checar_b1.py`
**Regras:** engine ≥ 3.1 → `sensibilidade_phi` obrigatório; SE `fatos_reformulado` presente →
`serie`, `diagnostico`, `gates_aplicabilidade` obrigatórios; SE `ebit_justo` presente →
`cenarios`, `paridade`, `reverse`, `historia_numeros`, `bridge` obrigatórios; paridade
`DIVERGE` sem `nota_resolucao` → **AVISO** (nunca falta — condição 3). `humano()` ganha:
`EQUITY_OK`, `GATE_DISPARA`, `OPERACIONAL`, `EQUITY`, `PARIDADE_DIVERGENTE`, `CONVERGE`,
`DIVERGE`, `PROVISORIO_N3`. compor: `secao_reformulado` (série + diagnóstico + gates),
`secao_ebit_justo` (cenários + bridge + paridade + reverse + TABELA história→números),
`secao_phi` (grid) — todas no CORPO institucional, renderizadas apenas quando a chave existe.

- [ ] **Step 1 (RED):** `test_checar_b1.py`: namespace sintético v3.1 SEM ebit_justo → zero faltas
  novas; COM ebit_justo sem `historia_numeros` → falta; paridade DIVERGE sem nota → aviso e NÃO
  falta; relatório composto com enums novos passa no linter (precedente
  `test_correcoes_hg.py::test_relatorio_composto_passa_no_linter`).
- [ ] **Step 2:** FAIL. **Step 3:** implementar. **Step 4:** PASS + 212 antigos verdes. **Step 5:**
  commit `feat: contrato v3.1 no checar/compor — gating por presenca, secoes novas, paridade como aviso (passada unica)`.

### Task 9: Versão, CHANGELOG, suíte completa, gate

- [ ] **Step 1:** `ENGINE_VERSION = "3.1.0"` + CHANGELOG no topo do engine.py (v3.1.0: itens
  φ/reformulado/H7/ebit_justo/paridade-decisão da condição 3 com "reavaliar após 3 análises
  reais"/história→números/impostos; NADA breaking).
- [ ] **Step 2:** suíte completa (`pytest -q`) → 212 antigos + novos, todos verdes; rodar
  `referencia/verificacao_referencia.py` apontando o engine do WORKTREE via env var?
  NÃO — B0 valida o engine released; fica como está (nota no gate).
- [ ] **Step 3:** commit `docs: changelog v3.1.0`; `git log --oneline` + `git diff main --stat`
  para o gate; PAUSAR e apresentar ao usuário (sem merge, sem push).

## Self-Review (executado)

- Condições da aprovação: 3 (Task 6/8 — aviso, decisão no CHANGELOG Task 9), 6 (Task 7+8, mesma
  passada), 7 (Task 4 constantes + eco; SKILL fica para o B5 como aprovado). H11 exclusão mútua:
  Task 2. Camadas imposto: Task 7. RiR/ROIIC: Tasks 3 (histórico janela) e 5 (implícito terminal).
- Placeholders: nenhum — todos os asserts têm números medidos (B0/FASE A) ou derivação no teste.
- Tipos consistentes: `bloco_*` seguem o padrão existente (dict → chave em `rodar()`); nomes de
  chave definidos uma única vez nas Interfaces.
