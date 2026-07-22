# B3 — Ledger de classificação + norma contábil: Plano de Implementação

> **For agentic workers:** superpowers:executing-plans (inline), TDD. Encadeado após B2
> (mesma branch). Decisões da FASE A ratificadas: classificação por julgamento SEM dicionário
> de rubricas; ledger como DADO DA ANÁLISE congelado no snapshot; 3 pacotes de leasing com
> trava declarativa; norma contábil detectada na coleta, engine agnóstico (só eco + trava).

**Goal:** `classificacao.yaml` por análise (schema próprio + invariantes na carga + linhas
ambíguas flagadas ao Auditor + congelamento no snapshot), `fatos.norma_contabil` ecoado pelo
engine com trava H3×H13 (pacote de leasing não-nativo sem ajuste declarado → aviso nomeado), e
critérios/jurisprudência em `references/` do er-dossie (fora do orçamento de palavras).

### Task 1: `schemas/classificacao.schema.json` + `checar_classificacao` (gating por presença)
Classes fixas: ATIVO_OPERACIONAL | PASSIVO_OPERACIONAL | ATIVO_FINANCEIRO | PASSIVO_FINANCEIRO
| EQUITY. Toda linha: rubrica, valor, classe, justificativa (>=10c), fonte, ambigua?, claim_bridge?.
Invariantes (checar, tol 0,5%): AO+AF ≈ ativo_total; PO+PF ≈ passivo_total; EQUITY ≈ equity_total;
ativo ≈ passivo+equity (⇒ CE≡NOA automático). Ambíguas → AVISO direcionado ao contraditório do
Auditor. Ausência do arquivo → nada (análises antigas intactas).
- [ ] RED (tmp ns: válido/limpo; soma quebrada → falta; ambígua → aviso; schema inválido → falta) → implementar → GREEN → commit.

### Task 2: snapshot congela `classificacao.yaml` + engine eco/trava `norma_contabil`
snapshot.py: adicionar à tupla de opcionais (Auditor audita ledger IMUTÁVEL). Engine: eco
`norma_contabil` quando `fatos.norma_contabil` presente; validação: regime ∈ {IFRS_CPC, US_GAAP,
J_GAAP_STUB, CAS_STUB, IND_AS_STUB}, leasing_pacote ∈ {IFRS16_PURO, AS_IF_RENT, ASC842_NATIVO}
(erro se inválido); TRAVA H3×H13: pacote não-nativo do regime sem `ajustes_aplicados` → aviso
nomeado `PACOTE_LEASING_NAO_NATIVO` (GT-H13-5 da FASE A). checar: eco presente exige regime+pacote.
- [ ] RED → implementar → GREEN → commit.

### Task 3: `skills/er-dossie/references/classificacao.md`
Critérios por natureza (testes curtos), 5 classes, ledger obrigatório sem resíduo, jurisprudência
consultiva dos casos difíceis (goodwill TF vs Lopes; intangível-contrato Itaú; restricted cash;
dividendos a pagar; puts; warrants; impostos diferidos — simetria Lopes verificada no B0;
provisões; leasing), pacotes H3 com trava e checklists H13 (IFRS/CPC baseline; US GAAP com o
caso PVV; stubs J-GAAP/CAS/Ind AS). SEM dicionário de rubricas (decisão ratificada). Teste:
frontmatter/limites dos testes de skills continuam verdes (references não são orçados).
- [ ] Escrever → suíte completa GREEN → commit.

**Aceitação global:** suíte inteira verde; nenhum namespace antigo reprova (gating por presença).
