---
name: er-motor-k3
description: USE QUANDO precisar da metodologia K3 V2.2.1 — relações financeiras do modelo, calibração dos 16 canonical inputs, arquétipos/perfis de empresa, rodar o engine determinístico ou a suíte de regressões. NÃO use para coleta de dados (er-dados-openbb), composição de relatório HTML (er-relatorio-html) ou workflow de análise (er-analise).
---

# er-motor-k3 — Motor K3 V2.2.1 (cópia congelada)

Princípio, nesta ordem exata: **AI calibra → engine calcula → regressão valida → AI interpreta.**
A metodologia é **congelada em V2.2.1** (`formula_version K3-vF19-2026-08-03 / manual-v2.2.1`; íntegra em `manifest_copia.json`). Nunca edite os arquivos de `scripts/` e `references/`, nunca introduza outro motor de valuation (sem WACC, FCFF ou Gordon Growth) e nunca recompute ou aproxime a fórmula em prosa: o julgamento entra nos 16 inputs, o código faz todo o resto.

## Canonical sources (ler sob demanda, não reproduzir)

| Arquivo | O que é | Quando ler |
|---|---|---|
| `references/Justified_PE_AI_Manual_v2.2.1.md` | Metodologia completa: fórmula K3 exata (§1), mapa de inputs (§2), dependências econômicas (§3), rulebook de calibração (§4), convenções críticas (§5), política de Ke (§6), arquétipos (§7), sanity checks (§8), failure modes de AI (§9), protocolo de execução (§10), invariantes e regressões (§11), quick reference (§12) | §4+§7 durante a calibração; §6 ao fixar Ke/hurdle/distress; §8 antes de fechar números; §12 como recall compacto |
| `references/K3_Regression_Tests_v2.2.1.json` | Âncoras de regressão executáveis por máquina + contrato de inputs | Raramente direto — `run_regressions.py` o executa |

## Os 16 canonical inputs

`ROE1, ROE2, g1, g2, Ke1, Ke2, n1, n2, NDE1, NDE2, GDE1, GDE2, F, g_T, Kd_F2, t`

São os únicos inputs econômicos. `NI0` (forma P/L) ou `Book0` (companion P/B) são **escala de output, não um 17º input**. Receita, margens, giro, múltiplos de mercado e preço NUNCA entram como input direto — evidência operacional calibra `ROE`/`g`, não os substitui (manual §2.2).

## Calibração — ordem §4.0 e regras §4.1–4.8

Ordem obrigatória: `Normalize NI/Book → ROE1 → g1 → n1 → ROE2 → g2 → n2 → F → Ke1/Ke2 → GDE/NDE → Kd_F2/t → g_T`. Iterar quando a economia liga inputs (`ROE ↔ estrutura ↔ Ke`, `g ↔ funding`); NUNCA iterar contra o preço de mercado.

- **§4.1 Normalizar antes do ROE** — remover não-recorrentes e pico/vale de ciclo; ajustar book econômico (R&D, leases, buybacks); gap material entre `Book0 implied = NI0·(1+g1)/ROE1` e o book normalizado é flag de revisão.
- **§4.2 ROE1 e ROE2** — ROE sobre book inicial (`NI_t/Equity_{t-1}`); ROE1 = economia normalizada do regime atual; ROE2 = retorno marginal do regime-alvo com mecanismo nomeado; mudança material de estrutura → revisitar ROE2 e Ke2.
- **§4.3 g1 e g2** — crescimento de lucro/book sob ROE constante; TAM/share/unit economics são evidência a traduzir; mudança de ROE vai na fronteira de fase ou no fade, nunca escondida em `g`.
- **§4.4 n1** — termina quando F1 deixa de ser a melhor descrição da economia (cronograma observável); nunca é o mero horizonte de projeção do analista.
- **§4.5 n2 e F** — `n2` = duração do spread pleno (evidência competitiva; os ranges de CAP citados no manual são priors de revisão, não cortes); `F` = velocidade de erosão ROE2→Ke2 depois de F2; nunca usar como plug.
- **§4.6 Intensidade de capital** — prior direcional de spread menor em negócios capital-intensivos; testar compensadores explícitos; não assumir `ROE≈Ke` mecanicamente.
- **§4.7 GDE, NDE, Kd_F2 e t** — denominador é o book-model equity do K3, nunca market cap; `GDE≥NDE` (`NDE<0` permitido para net cash); separar caixa distribuível do requerido; `Kd_F2`/`t` só afetam K3 via bridge.
- **§4.8 g_T** — ponto final do fade finito, nunca input de perpetuidade; consistente com moeda, inflação e escala; o efeito cresce com `F`.

## Política de Ke (manual §6)

- **Convenção de country risk (§6.1):** `Ke = default-free risk-free na moeda do valuation + bottom-up beta × mature-market ERP + λ_company × CRP`. `λ_company` mede exposição econômica real (operações/receitas), não incorporação; nunca contar risco soberano duas vezes.
- **Ke1 vs Ke2 (§6.2):** `Ke2<Ke1` exige queda real de risco contínuo (maturidade, alavancagem menor); nunca reduzir Ke2 porque a tese parece atraente ou porque ROE2 melhora.
- **Hurdle (§6.3):** hurdle **não tem default** — só existe se o usuário fornecer. Rodar como cenário com `label_mode: "hurdle"`, cujo output é rotulado **"Hurdle-conditioned Equity Value"** — nunca "fair value" nem "IRR". Para fair value, usar Ke econômico.
- **Reverse Ke (§6.4):** Ke implícito por inversão do K3 é parâmetro de ponto fixo (Ke2 também move o fade); rotular **"reverse Ke / market-implied Ke"**, nunca automaticamente IRR.
- **Distress (§6.5):** falha discreta material (falência, perda de licença, funding) NÃO é absorvida só em Ke: rodar K3 por cenário going-concern coerente e ponderar por probabilidade **fora da fórmula** → **"Probability-weighted Equity Value"**, nunca chamado de K3.

## Arquétipos (manual §7)

Arquétipos **mudam a calibração, nunca o modelo**: toda linha usa o mesmo K3 de 16 inputs. Nenhuma linha é gate de aplicabilidade nem corte numérico. As 4 famílias de tabelas:

1. **§7.1 Ciclo de vida, rentabilidade e estrutura de capital** — early-stage, pre-revenue, negative earnings, turnaround, compounder, cash cow, capital intensive, asset-light, high leverage, net cash, declining, serial acquirer, negative book equity.
2. **§7.2 Ciclos, recursos e ativos regulados** — cíclicas, commodities, utilities reguladas, concessões, real estate, depleção de recursos.
3. **§7.3 Serviços financeiros** — geral, banco, seguradora, broker, asset manager (convenção de neutralização equity-consistent; depósitos não são dívida corporativa).
4. **§7.4 Contratos, produto e modelo de negócio** — pharma/IP cliff, project-based, subscription, marketplace/network. (§7.5 traz as convenções de borda para `NI0≤0` e book negativo.)

Ao classificar o perfil da empresa (insumo da fase F3 do fleet): identificar a(s) linha(s) relevante(s) — pode ser mais de uma — e extrair de cada uma a orientação por input, a normalização exigida e o **principal failure mode**, que vira risco de calibração declarado.

## Como rodar o engine

Escreva um `case.json` e chame o CLI (ou importe `scripts/valuation_engine.py`):

```json
{
  "company": "XYZ S.A.", "currency": "BRL", "valuation_date": "2026-08-05",
  "market": {"price_per_share": 20.0, "shares_diluted_t0": 8.4},
  "scenarios": {
    "base": {"inputs": {"ROE1": 0.185, "...": "as 16 chaves"},
             "scale": {"NI0": 5.75}, "weight": 0.6},
    "bear": {"...": "..."}, "bull": {"...": "..."},
    "hurdle": {"...": "...", "label_mode": "hurdle"}
  }
}
```

`scale` recebe `NI0` (forma P/L) ou `Book0` (companion P/B); `weight` é opcional (cenários probabilísticos); `label_mode` é opcional (`"hurdle"` para rodada de hurdle).

```bash
python scripts/run_regressions.py                                      # suíte completa V2.2.1 → exige SUITE PASS
python scripts/valuation_engine.py value   case.json --out results.json
python scripts/valuation_engine.py sens    case.json --param ROE2 --values 0.15:0.30:6
python scripts/valuation_engine.py sens    case.json --param ROE2 --values ... --param2 n2 --values2 8,12,16
python scripts/valuation_engine.py implied case.json --param Ke2       # reverse solve para o preço
```

**Regression gate:** rodar `run_regressions.py` e exigir a linha **SUITE PASS** antes de qualquer entrega baseada no engine na sessão. Falhou → arquivos alterados ou corrompidos: parar, restaurar da origem (hashes em `manifest_copia.json`), rodar de novo. `value` também autoverifica o fingerprint do caso-base. Nesta cópia a seção de paridade JS faz skip sem node (o espelho JS vive em `er-relatorio-html`); o SUITE PASS continua obrigatório.

## Contrato de inputs

- **INVALID bloqueia**: o engine se recusa a calcular (`validation.status`) — corrigir os inputs, nunca forçar.
- **REVIEW exige justificativa documentada**: matematicamente suportado, roda só com racional explícito (ex.: zona de estabilidade `|Ke−g|` pequena).
- **Boundaries e companions são automáticos**: limites exatos `Ke=g`, `n1=0`/`n2=0`/`F=0`, `A2_cancelled` em `ROE2=0`, companion P/B direto em `ROE1=0` (fornecer `Book0`). Não contornar à mão.
- **Sem thresholds inventados**: categorias qualitativas ("bridge material", "retorno extremo", "duração longa") não têm corte numérico universal em V2.2.1 — julgar economicamente no contexto; ranges documentados no manual são priors de revisão, âncoras de regressão nunca são thresholds de calibração.

## Disciplina de output

- **Citar por chave do `results.json`**, nunca re-derivar: `K3_trailing_PE`, `forward_PE`, `equity_value`, `value_per_share`, `vs_market.upside`, `blocks`, `pb_blocks`, `implied_PB0`, `K_PB`, `route`, `computed`, `validation`, `sanity_notes`, `funding`. Divergiu da intuição → investigar inputs, não a aritmética.
- **Funding α-adjusted vem do engine** (bloco `funding`): Equity reinvestment requirement = `α·g/ROE` e Net FCFE distribution ratio = `1 − α·g/ROE` — nunca derivar payout/funding de `g/ROE` à mão. `g > ROE` é só sinal de revisão; a condição exata de funding negativo é `1 − α·g/ROE < 0`. FCFE negativo = funding externo a testar, nunca rejeição automática nem haircut de diluição adicional.
- **Per-share** usa apenas diluted shares atuais em t=0 (manual §5.1); nunca somar ações futuras de funding.
- **Labels obrigatórios**: hurdle → "Hurdle-conditioned Equity Value"; inversão de Ke → "reverse Ke / market-implied Ke"; blend probabilístico → "Probability-weighted Equity Value" (campo `label`). Reverse valuation sempre rotulada em separado; outputs nunca calibram inputs.
- **`NI0 ≤ 0`** → reportar Equity Value (e P/B), nunca interpretar P/L como barato/caro (o engine sinaliza).

## Referências

- `references/Justified_PE_AI_Manual_v2.2.1.md` — manual completo da metodologia V2.2.1.
- `references/K3_Regression_Tests_v2.2.1.json` — âncoras canônicas de regressão.
- `scripts/valuation_engine.py` — engine determinístico (CLI `value|sens|implied`).
- `scripts/input_validator.py` — contrato de inputs (INVALID/REVIEW/boundaries).
- `scripts/run_regressions.py` — suíte de regressão (gate SUITE PASS).
- `manifest_copia.json` — identidade da cópia congelada (origem, data, sha256, contagem da suíte).
