# B2 — Respostas R2–R5 (engine v3.2.0 + cap_check v2.1): Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans (inline). TDD estrito.
> Encadeado após B1 aprovado (mesma branch `upgrade-v2-b1`; sem merge — ordem do usuário).
> Aceitação: números MEDIDOS no B0 (`tfco4_repro.md`, `h8_quant.out.txt`, `r5_cap_banda.out.txt`).

**Goal:** responder R2–R5 por chave: `central_neutro` + `robustez_conjunta` (R2), `validacao_multiplos.implicitos` com decomposição por driver (R3), `ke_dossier` com 2 rotas + grade de Ke (R4), cap_check v2.1 com confiança separada da banda + ônus de sobrescrever para BAIXO (R5).

**Global constraints:** os do roadmap; blocos aditivos; `pl_justo` intocado; engine bump 3.1.0→3.2.0; cap_check 2.0→2.1; gating por presença (exceto `validacao_multiplos.implicitos`, derivado de dados já existentes → sempre emitido em v3.2+).

### Task 1: `central_neutro` + `robustez_conjunta` (R2)
**Input:** `premissas.central_neutro {lpa, cap_base, ke, justificativa>=40c}` (opcional).
**Output:** `central_neutro {parametros, precos{bear,base,bull,ponderado}, hurdle_ponderado?, premio_econ_pct, premio_hurdle_pct?, gate_recomputado{modo, razao_preco, razao_cap}, robustez_conjunta{baseline{premio_econ_pct,premio_hurdle_pct}, decomposicao{so_lpa_pp, so_cap_pp, so_ke_pp, soma_isolados_pp, interacao_pp}}}`.
**Aceitação (fixture TFCO4 + neutro lpa 1,05/cap 13/ke 0,125; B0):** prêmio econ 79,7→**41,7**; hurdle 66,4→**47,5**; só_lpa **−17,1**pp; só_cap **−2,9**pp; só_ke **−19,9**pp; interação **+1,9**pp; gate SUMARIA→**PADRAO**.
- [ ] RED → implementar → GREEN (suíte inteira) → commit.

### Task 2: `validacao_multiplos.implicitos` (R3)
Sempre emitido (v3.2+): para `historico_proprio.mediana` e `comparaveis.mediana_pares` (métrica PE): `{multiplo, cap_implicito, g_implicito, ke_implicito}` via bisseções existentes (base = cenário base, Ke central; None com nota quando sem raiz). Round-trip como aceitação (pl_justo(implícito) ≡ múltiplo, 1e-3) + monotonia (cap_impl(20x) > cap_impl(justo 8,16x)).
- [ ] RED → implementar → GREEN → commit.

### Task 3: `ke_dossier` (R4)
**Input:** `premissas.dossie_ke {rota_paridade_us{componentes,total}, rota_local{componentes,total}, premio_tamanho{valor_pp,criterio}, escolhido, reconciliacao_hurdle?}` (opcional; validação: 2 rotas com total>0, critério do prêmio obrigatório mesmo se 0, aviso se |escolhido−ke_central|>0,5pp).
**Output:** `ke_dossier {eco..., grade_ke:[{ke, central_ponderado, premio_pct}]}` com grade = ke_central + offsets −3,0..+1,0pp (passo 0,5) → TFCO4: 11–15%.
**Aceitação (h8_quant B0):** pond@11% **10,60**; @14% **8,34**; @15% **7,73**; prêmio +**41,4**%→+**93,9**%.
- [ ] RED → implementar → GREEN → commit.

### Task 4: cap_check v2.1 (R5)
Aditivo: (a) `confianca_da_banda {nivel, criterio}` derivada da EVIDÊNCIA (pontos: âncora presente; ≥2 fontes; precedente ≥20a; renovação → ≥3 ALTA / 2 MEDIA / ≤1 BAIXA), SEPARADA de `confianca_declarada`; (b) **ônus para BAIXO**: `caps.base < lo(banda_sugerida)` → alerta nomeado (encurtar também exige justificativa — hoje zero alertas nesse caso, FNV real: banda 18-25 com base 17); (c) selftest ampliado. `VERSAO = "2.1"`.
- [ ] RED (pytest chama `avaliar()` com caso FNV-like) → implementar → selftest OK + GREEN → commit.

### Task 5: contrato (checar/compor) + bump 3.2.0 + CHANGELOG
checar: v3.2+ exige `validacao_multiplos.implicitos`; `central_neutro`/`ke_dossier` presentes exigem subchaves (`robustez_conjunta`, `grade_ke`). compor: seção "Caso central neutro e robustez conjunta"; implícitos na seção de múltiplos; seção "Dossiê da taxa de desconto" — linter-safe. CHANGELOG v3.2.0.
- [ ] RED → implementar → GREEN (suíte inteira) → commit.

**Self-review:** R2→T1, R3→T2, R4→T3, R5→T4, contrato→T5; números de aceitação todos com fonte B0; sem placeholder.
