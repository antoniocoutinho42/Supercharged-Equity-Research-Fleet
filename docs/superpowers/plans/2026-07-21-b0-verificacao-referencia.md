# B0 — Verificação de Referência: Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans (inline) ou
> superpowers:subagent-driven-development. Steps usam checkbox (`- [ ]`).

**Goal:** um script re-executável que reproduz as identidades §1.2 nos QUATRO workbooks de
referência, registra a adjudicação dos 5 flags §1.3 com recomputo e fecha as 3 diligências de
fonte única da condição 5 — tudo com PASS/FAIL explícito e exit code, ANTES de qualquer edição no engine.

**Architecture:** um único script `C:\Claude\referencia\verificacao_referencia.py` com harness de
checks + uma seção por workbook + seção de matrizes TFCO4; saída humana em
`verificacao_referencia.out`; adjudicação em `verificacao_referencia_memo.md`. Consolida a lógica
JÁ PROVADA nos scripts da FASE A (em `C:\Claude\upgrade_fleet_v2_fase_a\`) — endereços de células
vêm de lá, valores esperados vêm das tabelas de aceitação abaixo (medidos na FASE A).

**Tech Stack:** Python 3.12 portátil (`C:\Claude\tools\python-nupkg\tools\python.exe`), openpyxl
3.1.5 (carga dupla data_only), pypdf (matrizes do PDF), engine v3.0.0 importado read-only.

## Global Constraints

- READ-ONLY sobre o repo e sobre os workbooks; escrever APENAS `referencia/verificacao_referencia.{py,out}`, `referencia/verificacao_referencia_memo.md` e `referencia/verificacao/` (auxiliares).
- `sys.dont_write_bytecode = True` antes de importar o engine (não criar __pycache__ no repo).
- Tolerâncias MEDIDAS na FASE A (não inventar): identidades exatas 1e-9; rotas EV reais 1e-5 relativo; NOL 1e-6 relativo; fator JM 1e-12; matrizes = igualdade após arredondar como o PDF (2 casas).
- Workbooks (nomes reais): `T&F_CG_3Q24.xlsm`, `2024.3T - Modelo Lopes_V30.xlsx`, `Financial_Model_PVV_v6.3.xlsx`, `Justified_Multiples_Model.Excel_vF7 (07.04.25)_Vf.xlsx`, `relatorio_final_1.pdf`. Aba `'NOL_DCF '` tem espaço final.
- referencia/ não é repo git → sem commits; gate da fase = arquivos novos + .out verde + memo + aprovação.

---

### Task 1: Harness + import do engine

**Files:** Create: `C:\Claude\referencia\verificacao_referencia.py` (esqueleto)
**Produces:** `check(secao, nome, esperado, obtido, tol, tipo='abs'|'rel'|'exato')`, `secao(titulo)`,
`finaliza()` → escreve `.out`, imprime resumo `PASS/FAIL/TOTAL`, `sys.exit(0|1)`; `ENG` = módulo
engine importado de `C:\Claude\equity-research-fleet\skills\er-valuation`; `W(nome)` → workbook
duplo `(valores, formulas)` com cache.

- [ ] **Step 1:** escrever o esqueleto com um self-check deliberadamente falho (`check('SELF','harness',1,2,0)`), rodar e verificar exit 1 e linha FAIL no `.out`.
- [ ] **Step 2:** trocar o self-check por `check('SELF','harness',1,1,0)` + `check('SELF','engine importa', 'ok', 'ok' if hasattr(ENG,'pl_justo') else 'FALTA', 0, 'exato')`; rodar; exit 0.

### Task 2: Seção TF (identidades §1.2 + H10 + flag §1.3.1)

**Fonte de endereços:** `upgrade_fleet_v2_fase_a\verify_tf.py`, `ver3_tf_flag1.py`, `h10_spotcheck.py`.
**Tabela de aceitação (valores medidos na FASE A — o teste é escrito ANTES da implementação):**

| Check | Esperado | Tol |
|---|---|---|
| CE−NOA (K,L,M = 2022,2023,2024) | 0 | 1e-6 |
| margem×giro − ROIC r101 (M: 0,152670×1,678667=0,256283) | 0 | 1e-9 |
| ponte r104 − direto r105 (M: 0,2548340) | 0 | 1e-7 (5 casas exigidas) |
| NBC 2024 r102 | −0,2706031191050339 | 1e-9 |
| FLEV 2024 | 0,1011489153145708 | 1e-9 |
| FCFF 2025: 125290,76−122473,68+22423,74 vs r165 | 25240,8264 | 1e-4 |
| EV rota DCF C41 vs rota ER F41 | 1443559,8109500317 | 1e-8 rel |
| Flag1: C44 = C41 + C43 com C43=+11697,0154 (fórmulas conferidas em 5 blocos: C44,F44,I44,G66,C71,C87) | estrutura + valor | exato/1e-6 |
| Flag1 efeito: preço modelo 9,609961 vs sinal padrão 9,459549 (+1,5901%) vs ponte coerente 10,239831 (−6,1512%) | os 3 preços | 1e-4 |

- [ ] **Step 1:** registrar os checks com os esperados acima (falham por NameError da seção — verificar FAIL).
- [ ] **Step 2:** implementar a seção lendo as células (endereços do verify_tf.py/ver3) e recomputando por componentes-folha (nunca confiar no rótulo).
- [ ] **Step 3:** rodar; todos PASS.

### Task 3: Seção Lopes (identidades + tripla checagem + ER + flags §1.3.2/§1.3.5) — inclui DILIGÊNCIA D1

**Fonte de endereços:** `lopes_recompute.py` (+ `model_rows*.txt` para as fontes do bridge).
**Tabela de aceitação:**

| Check | Esperado | Tol |
|---|---|---|
| margem 2023 × giro 2023 − ROIC l.103 (0,1739×1,4738=0,256308; receita inclui apropriação Itaú 14,5) | 0 | 1e-6 |
| ponte ≡ direto 2023 (0,178; FLEV com ND MÉDIO −73,0 → −0,371) | 0 | 1e-6 |
| tripla checagem l.110-112 (ND+E ≡ FixedAssets+WK) | 0 | 1e-6 |
| ER: NOA + PV(ER) + PV(TV) = 642,918 ≡ rota DCF D40 | 642,9182897 | 1e-5 rel |
| **D1 (2ª via, flag 2)**: efeito POR AÇÃO de cada escolha do bridge, reconstruído DIRETO do Model/BP (rota independente da FASE A): leases no bridge; puts R$21mi fora; dividendos a pagar fora; OFA R$55,8mi fora; líquido | líquido **+4,7%/ação** (lopes.md); divergência >0,5pp → FAIL e re-adjudicar no memo | 0,5pp |
| Flag 5: D75=0,149236, E75=0,20985 (documental: dois builds no mesmo modelo) | valores | 1e-6 |

- [ ] **Step 1:** registrar checks (FAIL). **Step 2:** implementar — D1 obrigatoriamente por rota nova: partir do preço final do DCF e recompor o bridge alternativo item a item (shares 137,287764 = CP_Resumo!D6). **Step 3:** rodar; PASS.

### Task 4: Seção PVV (caso degenerado + NOL flag §1.3.3 + flag §1.3.4) — inclui DILIGÊNCIA D2

**Fonte de endereços:** `pvv_recompute.py`, `h8_quant.py`, `spotcheck_h3_h13.py`.
**Tabela de aceitação:**

| Check | Esperado | Tol |
|---|---|---|
| margem 2024 × giro EoP − ROIC (−0,830×0,949=−0,787) | 0 | 1e-3 (arredond. do prompt) recomputado exato | 
| ponte fecha (check l.133) com FLEV −4,936→+10,838→... | 0 | 1e-6 |
| rota DCF C36 ≡ rota ER F36 | 30403,3323 | 1e-5 rel |
| NOL (flag 3): runoff `'NOL_DCF '` reproduzido; C90 nominal 30141,7; NPV = C38 | 8866,45 | 1e-6 rel |
| **D2 (2ª via, flag 4)**: ROIC 2023 nas TRÊS bases lido de células BRUTAS (E56/E60/E25-equiv), sem reusar pvv_recompute: EoP vs MÉDIA vs INICIAL; wedge EoP−média | wedge ≈ **28,8pp** (hip_roic); divergência >1pp → FAIL e re-adjudicar | 1pp |

- [ ] **Step 1:** checks (FAIL). **Step 2:** implementar (colunas E..R=2022..2035; rows noa=25, nopat=81, rev=56). **Step 3:** rodar; PASS.

### Task 5: Seção JM (formas fechadas + rotas + propriedades + fator v3.0.0)

**Fonte de endereços:** `jm_recompute.py`, `h9h10_verify.py`.
**Tabela de aceitação:**

| Check | Esperado | Tol |
|---|---|---|
| C187 EV/NOPAT | 6,429566333754988 | 1e-12 |
| C193 EV/EBITDA = C187×(1−t)(1−d) | 4,200650004719926 | 1e-12 |
| C292 P/E | 5,733730022636558 | 1e-12 |
| C164 WACC contábil (pesos a livro, ND) | 0,187332 (recompute Ke×E/(ND+E)+NBC×ND/(ND+E)) | 1e-6 |
| 3 rotas (fechada, DCF, ER) → mesmo valor | delta | 1e-10 |
| ROIC=WACC → EV/NOPAT=1/WACC; CAP→∞ → Gordon | identidades | 1e-9 |
| fator C187/pl_justo(op) com engine REAL | 1+g (desvio ≤1e-12) | 1e-12 |
| fator com m_terminal=0,5 e 1,5 (restrição: ≠(1+g)) | 1,2731356501728872 / 0,9839231427597888 | 1e-9 |
| C292/pl_justo(eq) | 1+g | 1e-9 |

- [ ] **Step 1:** checks (FAIL). **Step 2:** implementar. **Step 3:** rodar; PASS.

### Task 6: Matrizes 3×3 TFCO4 célula a célula — DILIGÊNCIA D3

**Files:** Create: `C:\Claude\referencia\verificacao\tfco4_inputs.yaml` (cópia do reconstruído da FASE A)
**Método:** rodar o engine v3.0.0 real sobre o inputs (out em `referencia/verificacao/engine_out/`),
extrair `matrizes` do resultados.json; extrair as 6 matrizes (54 células) do texto do PDF
(`pypdf`, páginas 5-6) com parser novo (o da FASE A quebrou — NÃO reutilizar `ver2_repro.py`);
comparar célula a célula após arredondar a 2 casas (formato do PDF).

- [ ] **Step 1:** check `matrizes 54/54` registrado (FAIL). **Step 2:** parser + run. **Step 3:** 54/54 PASS (qualquer célula divergente → FAIL com endereço linha×coluna×matriz).

### Task 7: Memo de adjudicação + rodada final

**Files:** Create: `C:\Claude\referencia\verificacao_referencia_memo.md`

- [ ] **Step 1:** memo com os 5 flags (veredito, recomputo decisivo, referência de check no .out) + as 3 diligências D1/D2/D3 declaradas FECHADAS (ou re-adjudicadas se algum FAIL) + divergências prompt↔arquivos relevantes ao B0.
- [ ] **Step 2:** rodada final limpa: `python verificacao_referencia.py` → exit 0, `.out` completo; conferir que nada foi escrito fora de `referencia/verificacao*`.
- [ ] **Step 3:** PAUSA — apresentar arquivos novos + resumo PASS ao usuário para aprovação do B0 (sem commits: referencia/ não é git).

## Self-Review (executado)

- Cobertura: §1.2 (4 workbooks) ✓ tasks 2-5; 5 flags ✓ (1→T2, 2→T3/D1, 3→T4, 4→T4/D2, 5→T3); condição 5 ✓ (D1/D2/D3); fator v3.0.0 ✓ T5; memo ✓ T7.
- Sem placeholders: valores esperados explícitos em todas as tabelas; endereços com fonte nomeada.
- Consistência de tipos: `check()` única definida em T1 e usada igual em T2-T6.
