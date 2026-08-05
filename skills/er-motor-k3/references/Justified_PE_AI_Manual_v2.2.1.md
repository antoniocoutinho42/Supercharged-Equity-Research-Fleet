# JUSTIFIED P/E CLOSED FORMULA · AI INSTRUCTION MANUAL V2.2.1

- **Motor canônico:** célula `K3` da aba `JM 2 phases + Fade ROE` da planilha `Justified_Multiples_Model.Excel_vF19 (03.08.26)_2Phases_Fade_ROE(1).xlsx`.
- **Output canônico:** **P/L Justo trailing / Equity Value**. Nenhuma métrica de valor da firma integra o motor.
- **Papel da planilha:** especificação matemática, bancada de derivação e auditor ano a ano. A planilha não foi alterada.
- **Regra de precedência:** K3 prevalece em matemática; Damodaran prevalece na orientação econômica; heurísticas devem ser rotuladas.
- **Aplicabilidade:** nenhum arquétipo de empresa é excluído. A representação exige inputs e normalização economicamente consistentes.
- **Base:** K3 calcula valor por unidade de `NI₀` quando a normalização por earnings é válida; a forma P/B companheira preserva a mesma economia quando essa escala é singular.

## CLASSIFICATION LEGEND

- `[FF] FORMULA FACT` — regra observável diretamente em K3.
- `[MI] MATHEMATICAL INVARIANT` — identidade algébrica ou limite matemático da K3.
- `[DG] DAMODARAN-BACKED ECONOMIC GUIDANCE` — orientação econômica apoiada em fonte oficial de Damodaran e traduzida para `ROE/Ke` quando necessário.
- `[RA] CASE-BASE REGRESSION ANCHOR` — resultado numérico do vetor-base; teste de implementação, não regra econômica universal.
- `[HP] HOUSE HEURISTIC / REVIEW PRIOR` — julgamento operacional ou prior de revisão; não é identidade nem regra universal.

## OFFICIAL SOURCE REGISTER

| Code | Official Damodaran material | Primary use in this manual |
|---|---|---|
| [D01] | [The Fundamental Determinants of Growth](https://pages.stern.nyu.edu/~adamodar/New_Home_Page/valquestions/growth.htm) | Net-income growth, retention, equity reinvestment, new equity, marginal ROE, efficiency growth |
| [D02] | [Growth Rates — The Little Book of Valuation](https://pages.stern.nyu.edu/~adamodar/New_Home_Page/littlebook/growthrates.htm) | Equity vs operating growth, marginal vs average returns, accounting adjustments |
| [D03] | [Excess Returns and Terminal Value](https://pages.stern.nyu.edu/~adamodar/New_Home_Page/valquestions/termvalueexreturns.htm) | ROE vs Ke, growth supported by reinvestment, no-value effect when excess return is zero |
| [D04] | [How Long Will High Growth Last?](https://pages.stern.nyu.edu/~adamodar/New_Home_Page/valquestions/highgrowthperiod.htm) | Competitive advantage duration, CAP, MICAP, size and barriers |
| [D05] | [Competitive Advantage Period — CAP](https://pages.stern.nyu.edu/~adamodar/pdfiles/eqnotes/cap.pdf) | CAP review priors, barriers, industry change, market-implied duration |
| [D06] | [Discount Rates — The Little Book of Valuation](https://pages.stern.nyu.edu/~adamodar/New_Home_Page/littlebook/discountrates.htm) | Equity risk, cost of equity, leverage, forward-looking beta |
| [D07] | [Ten Questions about Bottom-up Betas](https://pages.stern.nyu.edu/~adamodar/New_Home_Page/TenQs/TenQsBottomupBetas.htm) | Bottom-up beta construction and relevering |
| [D08] | [Measuring Company Exposure to Country Risk](https://pages.stern.nyu.edu/~adamodar/New_Home_Page/valquestions/CountryRisk.htm) | Country-risk exposure and currency consistency |
| [D09] | [ROC, ROIC and ROE: Measurement and Implications](https://pages.stern.nyu.edu/~adamodar/pdfiles/papers/returnmeasures.pdf) | Economic book, ROE measurement, accounting distortions, excess returns |
| [D10] | [Young Growth Companies: Value Drivers](https://pages.stern.nyu.edu/~adamodar/New_Home_Page/littlebook/younggrowthvaluedrivers.htm) | TAM, share, pathway to profitability, survival and funding |
| [D11] | [Mature Companies: Value Drivers](https://pages.stern.nyu.edu/~adamodar/New_Home_Page/littlebook/maturevaluedrivers.htm) | Mature growth, operating and financial slack |
| [D12] | [Declining Companies: Value Drivers](https://pages.stern.nyu.edu/~adamodar/New_Home_Page/littlebook/decliningvaluedrivers.htm) | Decline, distress and normalization |
| [D13] | [Distress in Discounted Cash Flow Valuation](https://pages.stern.nyu.edu/~adamodar/New_Home_Page/valquestions/distresspaper.htm) | Negative earnings, survival and distress |
| [D14] | [Characteristics of Financial Service Firms](https://pages.stern.nyu.edu/~adamodar/New_Home_Page/littlebook/financialsvccompanies.htm) | Regulatory capital, debt as operating input, equity focus |
| [D15] | [Financial Service Companies: Value Drivers](https://pages.stern.nyu.edu/~adamodar/New_Home_Page/littlebook/bankvaluedriver.htm) | Financial-company Ke, beta and equity calibration |
| [D16] | [Valuing Financial Service Firms](https://pages.stern.nyu.edu/~adamodar/pdfiles/papers/finfirm09.pdf) | Banks, insurers, book equity, ROE−Ke excess returns |
| [D17] | [Commodity Companies: Value Drivers](https://pages.stern.nyu.edu/~adamodar/New_Home_Page/littlebook/commodityvaluedrivers.htm) | Cycle normalization, scaled margins and capital needs |
| [D18] | [Companies with Intangible Assets: Value Drivers](https://pages.stern.nyu.edu/~adamodar/New_Home_Page/littlebook/intangiblevaluedriver.htm) | R&D, brand/customer acquisition and economic capital |
| [D19] | [Estimating Terminal Value](https://pages.stern.nyu.edu/~adamodar/New_Home_Page/valquestions/termvalapproaches.htm) | Stable-growth discipline; contrast with K3 terminal convention |
| [D20] | [Value Enhancement: Back to Basics](https://pages.stern.nyu.edu/~adamodar/pdfiles/execval/valenhX.pdf) | Margin × capital turnover and competitive-advantage drivers |

---

## 1. CLOSED FORMULA MAP

### 1.1 Exact K3 formula

`[FF]` The formula below is the exact `K3` formula, with only internal compatibility prefixes (`_xlfn.` and `_xlpm.`) removed and whitespace added. Do not simplify, substitute or alter it.

```excel
=LET(
  ke_f1,$C$294, ke_f2,$D$294, g_f1,$C$296, g_f2,$D$296,
  nde_f1,$C$300, nde_f2,$D$300, gde_f1,$C$301, gde_f2,$D$301,
  roe_f1,$C$303, roe_f2,$D$303, cap_f1,$C$304, cap_f2,$D$304,
  anos_fade,$E$8, g_terminal,$E$6, roe_terminal,$E$11,
  kd_at_f2,$D$5*(1-$D$52),
  alpha_f1,1-(gde_f1-nde_f1),
  alpha_f2,1-(gde_f2-nde_f2),
  razao_nde,(1+nde_f1)/(1+nde_f2),
  valor_f1,IF(ABS(ke_f1-g_f1)<0.000000000001,
    (1-alpha_f1*g_f1/roe_f1)*cap_f1,
    (1-alpha_f1*g_f1/roe_f1)*(1+g_f1)*(1-((1+g_f1)/(1+ke_f1))^cap_f1)/(ke_f1-g_f1)),
  valor_f2,((1+g_f1)^(cap_f1+1)/(1+g_f2)*(roe_f2/roe_f1)*razao_nde)/(1+ke_f1)^cap_f1
    *IF(ABS(ke_f2-g_f2)<0.000000000001,
      (1-alpha_f2*g_f2/roe_f2)*cap_f2,
      (1-alpha_f2*g_f2/roe_f2)*(1+g_f2)*(1-((1+g_f2)/(1+ke_f2))^cap_f2)/(ke_f2-g_f2)),
  ponte,((1+g_f1)^(cap_f1+1)/roe_f1)/(1+ke_f1)^cap_f1/(1+ke_f2)
    *(gde_f2*razao_nde-gde_f1)*(1+kd_at_f2),
  valor_fade,LET(
    pref_fade,(1+g_f1)^(cap_f1+1)/roe_f1*razao_nde/(1+ke_f1)^cap_f1*((1+g_f2)/(1+ke_f2))^cap_f2,
    IF(anos_fade=0,pref_fade,
      LET(k,SEQUENCE(anos_fade),
        g_fade,g_f2+(g_terminal-g_f2)*k/anos_fade,
        roe_fade,roe_f2+(roe_terminal-roe_f2)*k/anos_fade,
        prod_g,EXP(MMULT(--(k>TRANSPOSE(k)),LN(1+g_fade))),
        pref_fade*(SUM(prod_g*(roe_fade-alpha_f2*g_fade)/(1+ke_f2)^k)
                   +PRODUCT(1+g_fade)/(1+ke_f2)^anos_fade)))),
  valor_f1+valor_f2+ponte+valor_fade)
```

### 1.2 Four-block identity

`[FF] P/L Justo = V_F1 + V_F2 + Ponte + V_fade`.

| Block | Exact economic role | Direct inputs |
|---|---|---|
| `V_F1` | PV do FCFE distribuível enquanto F1 persiste | `ROE1, g1, Ke1, n1, GDE1, NDE1` |
| `V_F2` | PV do FCFE do regime-alvo sobre book/lucro reescalonado | F1 inputs + `ROE2, g2, Ke2, n2, GDE2, NDE2` |
| `Ponte` | Fluxo pontual de equity decorrente da recapitalização F1→F2 | Estrutura, `Kd_F2, t, Ke1, Ke2, ROE1, g1, n1` |
| `V_fade` | FCFE durante `ROE2→Ke2` + book terminal | F2 structure, `F, g_T, Ke2` |

### 1.3 F1

- `[FF]` `α1 = 1−(GDE1−NDE1)`.
- `[FF]` Net FCFE distribution ratio = `1−α1·g1/ROE1`.
- `[FF]` Standard branch: `(1−α1·g1/ROE1)·(1+g1)·[1−((1+g1)/(1+Ke1))^n1]/(Ke1−g1)`.
- `[MI]` Exact limit branch when `|Ke1−g1|<1e−12`: `(1−α1·g1/ROE1)·n1`.
- `[FF]` A negative distribution ratio is allowed and represents net equity contribution, not a formula error.
- `[FF]` The sign of `∂K3/∂n1` depends on the relative economics of F1 and the regimes displaced by one additional F1 year.

### 1.4 F2

- `[FF]` `rz = (1+NDE1)/(1+NDE2)`.
- `[FF]` F2 scale factor = `[(1+g1)^(n1+1)/(1+g2)]·(ROE2/ROE1)·rz/(1+Ke1)^n1`.
- `[FF]` F2 annuity uses `1−α2·g2/ROE2`, where `α2 = 1−(GDE2−NDE2)`.
- `[FF]` `ROE2/ROE1` captures the change in profitability at the regime boundary; do not hide that change inside `g2`.
- `[MI]` The `|Ke2−g2|<1e−12` branch is the exact finite limit and must remain.

### 1.5 Recapitalization bridge

- `[FF]` `kd_at = Kd_F2·(1−t)`.
- `[FF]` `Ponte = [(1+g1)^(n1+1)/ROE1]·(GDE2·rz−GDE1)·(1+kd_at)/[(1+Ke1)^n1·(1+Ke2)]`.
- `[FF]` `Ponte>0` may reflect net leverage proceeds to equity; `Ponte<0` may reflect equity required for deleveraging.
- `[FF]` `Kd_F2` and `t` enter K3 directly only through `Ponte`.
- `[MI]` IF `GDE2·rz=GDE1`, THEN `Ponte=0` and the direct effect of `Kd_F2/t` disappears.

### 1.6 Fade and terminal

- `[FF]` For `k=1…F`, `g_k=g2+(g_T−g2)·k/F`.
- `[FF]` For `k=1…F`, `ROE_k=ROE2+(Ke2−ROE2)·k/F`.
- `[FF]` F2 capital structure remains fixed during fade.
- `[FF]` Fade represents erosion of the `ROE−Ke` spread; it is not merely a slowdown in growth.
- `[FF]` `prod_g(k)` is the product of `(1+g_j)` for `j<k`; the first fade cash flow uses a product of `1`.
- `[FF]` `V_fade = PV(fade FCFE) + PV(Book_T)`.
- `[FF]` `ROE_T=Ke2`, `P/B_T=1` and `TV=Book_T`.
- `[FF]` `g_T` is the endpoint of the fade path. It is not a perpetual-growth denominator.
- `[MI]` IF `F=0`, THEN fade dividends are zero and `V_fade=pref_fade=PV(Book at end of F2)`.
- `[DG]` Damodaran's stable-growth discipline supports tying growth to reinvestment and returns; the K3 terminal closure itself is a formula-specific book-value convention, not a conventional perpetuity. ([D03], [D19])

---

## 2. EXACT INPUT MAP

### 2.1 Taxonomy

| Class | Items | Rule |
|---|---|---|
| `[FF] Canonical inputs` | `ROE1, ROE2, g1, g2, Ke1, Ke2, n1, n2, NDE1, NDE2, GDE1, GDE2, F, g_T, Kd_F2, t` | Exactly 16 direct inputs |
| `[FF] Fixed relationships` | `ROE_T=Ke2`; linear ROE/g fade; F2 structure through fade; `TV=Book_T`; phase-specific equity discounting | Never estimate or override |
| `[FF] Derived variables` | `α1, α2, rz, kd_at, distribution ratios, fade paths, products, prefixes and blocks` | Calculate; never calibrate |
| `[FF] Valuation scale` | `NI₀` for the P/L form; `Book₀` for the P/B companion form | Output scale only; neither is an additional K3 economic input |
| `[FF] Outputs` | `K3`, Equity Value, implied forward P/L, implied P/B, block decomposition | Do not use to calibrate inputs except in separately labelled reverse valuation |

### 2.2 Inputs that do not enter K3

- `[FF] DO NOT` insert revenue, margins, depreciation, operating-return metrics, asset turnover or fixed assets into K3.
- `[FF] DO NOT` insert a separate reinvestment rate into K3.
- `[FF] DO NOT` insert market multiples or market price into fundamental calibration.
- `[DG] DO` use operating evidence to understand and calibrate `ROE` and `g`. ([D01], [D02], [D09])

### 2.3 Exact meaning of g

- `[FF]` Within each full regime, net income and book equity grow at `g` while ROE remains constant.
- `[FF]` K3 derives the equity reinvestment/distribution requirement from `g`, `ROE` and `α`.
- `[DG]` Revenue, operating income, net income and EPS growth can differ because of operating leverage, financing, cash, taxes and share issuance. ([D02])
- `[DG]` Net-income growth can exceed EPS growth when new equity funds investment; an equity reinvestment rate can exceed 100%. ([D01])
- `[FF]` Therefore, `g` means **economic growth of earnings/book compatible with constant ROE in the regime**; revenue growth is evidence, not an automatic substitute.
- `[FF] IF` margins, turnover or ROE change materially, `THEN` represent the change through F1→F2 or fade; do not conceal it in `g`.

### 2.4 Input calibration table

| Input | Formula meaning | Calibration rule | Key interaction | Red flag | Class/source |
|---|---|---|---|---|---|
| `ROE1` | Return of F1 on beginning book | Normalize `NI1/Book0`; reconcile observed vs economic book | Anchors distribution and implicit book scale | Raw historical average; buyback/R&D distortion | `[FF]+[DG]` [D01], [D09] |
| `ROE2` | Sustainable target-regime return | Use marginal return and a named mechanism | `ROE2−Ke2`, `g2`, structure, CAP2 | Guidance without unit economics; leverage-only ROE | `[DG]` [D01], [D02] |
| `g1` | F1 earnings/book growth | Calibrate to the earnings/book path of F1 | Funding and F2 entry base | Revenue CAGR copied mechanically | `[FF]+[DG]` [D01], [D02] |
| `g2` | F2 earnings/book growth | Reconcile runway, returns and funding | Compounds with ROE2 and CAP2 | Growth unsupported by any economic pathway | `[FF]+[DG]` [D01] |
| `Ke1` | F1 equity opportunity cost | Same currency/terms as flows; use default-free risk-free + bottom-up beta × mature-market ERP + `λ×CRP` | Discounts F1 and all later value to boundary | Reverse-engineered from price; country risk counted twice | `[DG]` [D06]–[D08] |
| `Ke2` | F2/fade equity opportunity cost and terminal ROE target | Change from Ke1 only with real continuous-risk change; treat material discrete failure by scenarios | Discounting and `ROE_T` | Reduced because the thesis looks better; binary failure hidden only in Ke | `[FF]+[DG]` [D06], [D13] |
| `n1` | Duration of current regime | Tie to an observable regime-change timetable | Displaces F2 and fade | Generic forecast period | `[FF]+[HP]` |
| `n2` | Years of full F2 spread | Defend with competitive evidence | ROE2, g2, Ke2 | Chosen to hit price | `[DG]+[HP]` [D04], [D05] |
| `F` | Years of ROE2→Ke2 erosion | Calibrate to imitation/erosion speed | Spread height and g path | Used as plug for CAP2 | `[FF]+[HP]` [D04], [D05] |
| `g_T` | Last fade-year earnings/book growth | Set a mature path endpoint consistent with currency and scale | Effect increases with F | Treated as a perpetual growth rate | `[FF]+[DG]` [D03] |
| `GDE1/2` | Gross debt / K3 book-model equity | Use normalized actual and executable target structure | `α`, bridge, ROE, Ke | Market capitalization denominator | `[FF]+[DG]` [D01], [D09] |
| `NDE1/2` | Net debt / K3 book-model equity | Distinguish distributable from required cash | `α`, `rz`, bridge | Structure changed without ROE/Ke review | `[FF]+[DG]` [D01], [D09] |
| `Kd_F2` | F2 debt cost used in bridge | Use sustainable marginal cost relevant to recap | Only direct through bridge | Illiquid security yield used mechanically | `[FF]+[DG]` [D06] |
| `t` | Tax rate used in bridge debt carry | Use economic marginal shield rate for the transition | Only direct through `kd_at` | Full operating-tax model inferred from it | `[FF]+[DG]` [D06] |

---

## 3. ECONOMIC DEPENDENCY MAP

```text
EVIDENCE
  ↓
Normalize NI / book / structure / risk / competitive economics
  ↓
16 CANONICAL INPUTS
  ↓
ROE−Ke spread · earnings/book growth · equity funding · recapitalization
  ↓
K3 = V_F1 + V_F2 + Ponte + V_fade
  ↓
P/L JUSTO → EQUITY VALUE
```

- `[DG]` `ROE>Ke` creates value above book; `ROE=Ke` closes at book; `ROE<Ke` destroys value on reinvested equity. ([D03], [D09], [D16])
- `[FF]` `g>ROE` is mathematically allowed and can make the FCFE distribution ratio negative.
- `[DG]` `g>ROE` requires a credible external-equity/funding path; it is a financing question, not an automatic rejection. ([D01])
- `[FF]` `n2` is duration of the full spread; `F` is the speed of spread erosion after F2.
- `[FF]` A reduction in `g` does not itself imply a reduction in ROE.
- `[FF]` A structure change is an economic event that changes `α`, `rz` and `Ponte`; it can also require economic recalibration of ROE and Ke.
- `[FF]` No perpetual excess return is hidden in K3 because `ROE_T=Ke2` and `P/B_T=1`.

---

## 4. INPUT CALIBRATION RULEBOOK

### 4.0 Required order

`Normalize NI/Book → ROE1 → g1 → n1 → ROE2 → g2 → n2 → F → Ke1/Ke2 → GDE/NDE → Kd_F2/t → g_T`

- `[DG] DO` iterate when economics are linked, especially `ROE ↔ structure ↔ Ke` and `g ↔ funding`. ([D01], [D06])
- `[FF] DO NOT` iterate against market price during fundamental calibration.

### 4.1 Normalize NI and book before ROE

- `[DG] DO` remove cycle peaks/troughs, exceptional taxes, impairments, asset gains, reserve releases, restructuring and other non-recurring items when material. ([D09], [D12], [D17])
- `[DG] DO` adjust economic book for material R&D, customer acquisition, training, brand investment, operating leases, buybacks and accounting write-offs when they distort the capital base. ([D09], [D18])
- `[FF]` `Book₀ implied = NI₀·(1+g1)/ROE1`; a material gap versus normalized book is a review flag.
- `[DG]` Average ROE reflects old and new investments; marginal ROE is usually more informative for future reinvestment. ([D01], [D02])
- `[DG]` A change in ROE on existing assets creates efficiency growth distinct from reinvestment growth. ([D01], [D02])

### 4.2 ROE1 and ROE2

- `[FF] DO` measure K3 ROE on beginning book, consistent with `NI_t/Equity_{t−1}`.
- `[DG] DO` calibrate `ROE1` to the first regime's normalized economics, not a raw historical average. ([D01], [D09])
- `[DG] DO` calibrate `ROE2` to the expected marginal economics of the target regime and name the driver: pricing, scale, mix, cost advantage, efficiency, regulation, allocation or deleveraging. ([D01], [D02])
- `[DG] IF` target structure changes materially, `THEN` revisit both ROE2 and Ke2; leverage can raise ROE only when operating return exceeds debt carry and also changes equity risk. ([D01], [D06])
- `[DG] DO NOT` use peers as a mechanical ROE target; use peers to bound margins, returns and competition. ([D01], [D09])
- `[FF]` Calibration-bench identity, not an additional K3 input: `ROE = ROIC×(1+NDE) − kd_at×GDE`.
- `[FF]+[DG]` In the spreadsheet convention, cash earns zero while interest accrues on gross debt. Because `GDE−NDE=Cash/Equity`, simultaneous gross debt and cash depress ROE through negative carry, all else equal; reflect actual cash yield in normalized ROE when it exists. ROE remains the direct K3 input. ([D06], [D09])

### 4.3 g1 and g2

- `[FF] DO` calibrate both rates as earnings/book growth within constant-ROE regimes.
- `[DG] DO` use TAM, market share, capacity, pricing, unit economics and funding as evidence, then translate that evidence into earnings/book growth. ([D01], [D10])
- `[DG] IF` new equity funds growth, `THEN` permit a negative FCFE distribution ratio and explicitly test dilution/funding access. ([D01])
- `[FF] DO NOT` estimate a parallel reinvestment rate and force K3 to follow both that rate and a separate `g`.
- `[DG] IF` ROE changes on existing assets, `THEN` put that change at the phase boundary or fade; do not call the entire effect reinvestment growth. ([D01], [D02])

### 4.4 n1

- `[HP]` `n1` ends when F1 stops being the best description of the economics.
- `[HP]` Evidence can include ramp-up, integration, contract start/end, turnaround completion, regulatory reset, cycle normalization or recapitalization.
- `[FF] DO NOT` label `n1` merely as the analyst's forecast horizon.

### 4.5 n2 and F

- `[DG]` `n2` must reflect the expected duration of excess equity returns; size, current excess returns and sustainable competitive advantages are key evidence. ([D04])
- `[HP]` Evidence inventory: switching costs, retention/churn, network effects, cost advantage, brand/pricing, IP, licenses, long contracts, share stability, entry barriers, technology risk, imitation speed, reinvestment runway, scale, obsolescence, proprietary data and capital allocation.
- `[DG]` CAP literature hosted by Damodaran reports an aggregate historical estimate around `10–15 years` and company estimates from `0–2` to `>20 years`. ([D05])
- `[HP]` Those ranges are review priors, not hard cutoffs and not calibration rules.
- `[HP] DO NOT` count moat factors and convert the count mechanically into years.
- `[FF]` `n2` answers **how long the full spread persists**; `F` answers **how long the spread takes to converge after erosion begins**.
- `[HP]` Contractual cliffs, substitution and rapid imitation support faster fade; installed bases, long contracts and slow capacity entry support slower fade.
- `[DG]` MICAP is a reverse-valuation diagnostic of expectations; it cannot set fundamental `n2`. ([D04], [D05])

### 4.6 Capital intensity / low turnover prior

- `[DG]` **Capital intensity / low capital turnover creates a directional pull toward lower economic returns and smaller `ROE−Ke` spreads, all else equal. Do not assume `ROE≈Ke` mechanically; test whether margins, scarcity, regulation, cost advantages or financing economics offset that pull.** ([D20], translated from operating returns to the K3 equity framework)
- `[DG]` High reinvestment requirements amplify the burden of growth; growth creates value only when the return on the incremental equity exceeds Ke. ([D01], [D03], [D09])
- `[HP]` Test compensators explicitly: high margins, pricing power, cost advantage, scarce assets, location, regulation, concessions, long asset life, replacement cost and sustainable leverage.
- `[HP]` This is a prior for investigation, not an identity and not an applicability test.

### 4.7 GDE, NDE, Kd_F2 and t

- `[FF]` `GDE−NDE=Cash/Equity` in K3's convention.
- `[FF]` Use K3 book-model equity as denominator; never market capitalization.
- `[FF]` `GDE≥NDE` under the ordinary gross/net-debt definitions; `NDE<0` is allowed for net cash.
- `[DG]` Separate distributable excess cash from operating, regulatory or trapped cash before setting NDE. ([D09], [D14])
- `[FF]` F1 structure is normalized current structure; F2 structure is an executable target.
- `[DG] IF` structure changes, `THEN` check debt capacity, equity risk, ROE, Ke and bridge economics. ([D01], [D06], [D07])
- `[FF]` `ROE = ROIC×(1+NDE) − kd_at×GDE` is only a diagnostic reconciliation: when `GDE>NDE`, debt-financed cash creates negative carry in this zero-cash-yield convention. If cash earns a return, include it in normalized ROE rather than adding a new K3 input.
- `[FF]` Kd_F2 and `t` affect K3 directly only when the bridge is nonzero.

### 4.8 g_T

- `[FF]` `g_T` is the last point of a finite fade path and never a Gordon-growth input.
- `[DG]` Set `g_T` consistently with currency, inflation, maturity and company scale; conventional stable-growth discipline is evidence only. ([D03], [D19])
- `[RA]` In the case-base, a `+1pp` g_T bump changes P/L by about `+0.04%`, `+0.08%`, `+0.20%` and `+0.48%` for `F=3,5,10,20`, respectively.
- `[FF]` The effect of g_T grows with F; no fixed percentage threshold can diagnose a bug.

---

## 5. CRITICAL FORMULA CONVENTIONS — DO NOT MISINTERPRET

1. `[FF]` ROE is a direct K3 input; operating components only calibrate it.
2. `[FF]` `g` is earnings/book growth under constant ROE; revenue growth is evidence.
3. `[FF]` A change in ROE must not be hidden in `g`.
4. `[FF]` `ROE_T=Ke2`, `P/B_T=1` and terminal value equals terminal book.
5. `[FF]` `g_T` is the fade endpoint, not a perpetual-growth input.
6. `[FF]` `n2≠g2`; duration and growth are separate inputs.
7. `[FF]` `F≠n2`; erosion speed and full-spread duration are separate inputs.
8. `[FF]` Growth slowdown does not automatically imply competitive fade.
9. `[FF]` GDE/NDE use K3 book-model equity, never market capitalization.
10. `[FF]` Cash affects `α`; it is not mechanically neutral.
11. `[FF]` The F1→F2 structure change creates a bridge; omitting it breaks equity-DCF equivalence.
12. `[FF]` `Kd_F2` and `t` enter directly only through the bridge.
13. `[FF]` K3 is trailing on normalized `NI₀`.
14. `[MI]` `P/L forward implied=K3/(1+g1)` exactly inside K3.
15. `[FF]` Market NTM comparisons require a calendar/earnings-definition reconciliation; that caveat does not alter the model identity.
16. `[FF]` Outputs cannot calibrate inputs; reverse valuation must be separately labelled.
17. `[FF]` ROE uses beginning book, not average equity.
18. `[MI]` Both `|Ke−g|<1e−12` branches are exact mathematical limits; never remove them.
19. `[FF]` K3 has no 25-year limit; only the spreadsheet's explicit auditor has that horizon.
20. `[FF]` Negative FCFE distribution can be legitimate external funding.
21. `[FF]` `NI₀<0` does not invalidate K3 economics; P/L loses intuitive interpretation, so report Equity Value.
22. `[MI]` `NI₀→0` makes P/L normalization unstable even when the underlying book economics are not zero.
23. `[MI]` `NI₀=0` is singular for `Equity Value=K3×NI₀`; use a documented nonzero normalized earnings scale or the exact P/B conversion, without changing K3's economics.
24. `[FF]` A sign change from loss-making F1 to profitable F2 must occur at the regime boundary; a constant proportional `g1` path cannot cross zero within F1.
25. `[FF]` Year `n1+1` is the first F2 year; its F2 flow and the bridge use Ke2 after `n1` years discounted at Ke1.
26. `[FF]` `rz` rebases equity across NDE structures while preserving the operating-capital base embedded in K3.
27. `[FF]` IF `n1=0`, THEN `V_F1=0`, but ROE1, g1 and F1 structure remain boundary-scale inputs for F2, the bridge and fade.
28. `[MI]` IF `n1=0` and all other inputs are fixed, THEN K3 is exactly proportional to `(1+g1)`.
29. `[FF]` IF `n2=0`, THEN `V_F2=0` and the company transitions directly from the F1/F2 boundary to fade; F2 economics still set fade entry.
30. `[MI]` `ROE1=0` requires the algebraically cancelled P/B companion form; do not evaluate K3 and then multiply an infinite result by zero.
31. `[FF]+[MI]` `ROE2=0` is economically supported only through the algebraically cancelled `A2_cancelled` implementation; the literal K3 cell is numerically singular at that boundary.

### 5.1 Funding and Per-Share Convention

- `[FF]` K3 calculates aggregate equity value under the convention that shareholders bear the contributions required by the projected path.
- `[FF]` When `1−α·g/ROE<0`, the negative distribution is the additional capital needed to fund growth; the economic funding cost is already reflected in negative FCFE.
- `[MI]` A future issuance at fair value is economically equivalent to a proportional capital call: existing holders surrender an ownership interest whose value equals the capital received.
- `[FF]` Do not apply a generic dilution haircut after K3, infer future shares from K3, or add future funding shares again to the denominator. Each would count the same funding twice.
- `[MI]` `K3/(1+g1)` remains the exact forward P/L on aggregate net income.
- `[FF]` Reconcile calendar, earnings definition and the market share base before comparing the implied multiple with `Price/EPS NTM`.

Standard outputs:

`Current-holder Equity Value = K3 × NI₀`

`Value per current diluted share = Current-holder Equity Value / Current diluted shares outstanding at t=0`

`current diluted shares outstanding at t=0` includes only shares and instruments already outstanding at the valuation date. It excludes future shares issued solely to fund capital already deducted through negative FCFE, and no additional generic dilution discount is permitted.

---

## 6. KE POLICY

### 6.1 Canonical fair-value use

- `[DG] DO` use an economic cost of equity consistent with risk to the diversified marginal investor. ([D06])
- `[DG] DO` use a risk-free rate consistent with currency and cash-flow terms. ([D06], [D08])
- `[DG] DO` use a forward-looking bottom-up beta by business and adjust for the relevant equity leverage. ([D06], [D07])
- `[DG] DO` include country-risk exposure based on operations/exposure, not incorporation alone, and avoid double counting sovereign risk in the risk-free rate. ([D08])
- `[DG] DO` keep nominal/real terms consistent between Ke and growth. ([D06])

Country-risk convention:

`Ke = Default-free Risk-free Rate in valuation currency + Bottom-up Beta × Mature-Market ERP + λ_company × CRP`

- `[DG]` `λ_company` measures company-specific economic exposure using operations, revenues, assets, customers and economic risk, not incorporation alone. Use a documented weighted exposure for multinationals. ([D08])
- `[DG]` If the selected ERP already embeds the full country premium, do not add `λ×CRP` again; explicitly reconcile any alternative convention. ([D08])
- `[DG]` Do not duplicate sovereign risk in both the risk-free rate and CRP. Keep currency, inflation and nominal/real terms consistent. ([D06], [D08])

### 6.2 Ke1 vs Ke2

- `[DG] IF Ke2<Ke1, THEN` identify a real decline in business, operating, financing or survival risk. ([D06], [D07])
- `[DG]` Maturity, lower leverage and more predictable continuous economics can justify a lower Ke2; material discrete failure remains scenario-weighted outside K3. ([D06], [D07], [D13])
- `[DG] DO NOT` lower Ke2 solely because ROE2 or margins improve. ([D06])
- `[DG] IF` GDE/NDE change materially, `THEN` reassess Ke because equity leverage changes equity risk. ([D06], [D07])

### 6.3 Hurdle and target return

- `[FF]` Ke2 both discounts value and sets `ROE_T`; changing it changes cash-flow/fade economics as well as discounting.
- `[FF] DO NOT` call a K3 run with an arbitrary hurdle a pure target-IRR solution.
- `[HP]` For fair value, use economic Ke.
- `[HP]` Name a hurdle-based K3 output **Hurdle-conditioned Equity Value** or **Required-return scenario value**. It is not fair value, an automatically implied IRR or a pure target-IRR solve; it may serve operationally as a purchase ceiling conditional on K3 economics.
- `[MI]` A true target-return solve requires holding the economic cash-flow path fixed while solving price/rate; that is a separate diagnostic, not a K3 input-calibration rule.

### 6.4 Reverse Ke

- `[FF]` Ke implied by inverting K3 is a fixed-point parameter because Ke2 also changes the fade endpoint.
- `[FF]` Label it `reverse Ke` or `market-implied Ke`, not automatically `IRR`.

### 6.5 Discrete Failure and Distress

- `[DG]` Ke reflects continuous and systematic economic risk borne by the diversified marginal investor. ([D06])
- `[DG]` A material discrete probability of bankruptcy, technical failure, license loss, inability to raise capital or another binary event must not be absorbed exclusively by raising Ke: the K3 scenario would still assume the firm reaches fade and terminal. ([D13])
- `[DG]+[HP]` When discrete risk is material, run K3 separately for every economically coherent going-concern scenario and probability-weight Equity Values outside the formula. ([D13])

`Probability-weighted Equity Value = Σ_s p_s × Equity Value_s`

For two states:

`Probability-weighted Equity Value = p_survival × Equity Value_K3,going-concern + (1−p_survival) × Equity Recovery Value_failure`

Rules:

- probabilities sum to 100%; each going-concern scenario uses internally consistent K3 inputs;
- recovery is residual equity value after debt, costs and prior claims and may be zero;
- systematic risk inside each state remains in that state's Ke;
- do not count the same event in both the probability and an arbitrary Ke premium;
- probability weighting neither changes K3 nor creates a new engine;
- call the blend `Probability-weighted Equity Value`, never K3;
- do not report a probability-weighted P/L automatically. Only present a `derived blended P/E` when the earnings base is coherent and label it explicitly.

---

## 7. COMPANY ARCHETYPE CHEAT SHEET

- `[FF]` Every archetype uses the same 16-input K3; these rows change calibration, not the model.
- `[DG]` Damodaran sources support the economic starting points; `[HP]` marks the explicit translation into K3 inputs when the source does not prescribe this formula.
- `[HP]` No row is an applicability gate, hard cutoff or substitute for company-specific evidence.

### 7.1 Life cycle, profitability and capital structure

| Archetype | ROE1 | ROE2 | g1 | g2 | n1 | n2 | F | Ke | GDE/NDE | Normalization | Principal failure mode | Class/source |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **Early-stage** | Low/negative on economic book | Positive only if unit economics support it | Earnings/book path of the current scale-up regime | Post-scale earnings/book, not revenue CAGR | Until economics change materially | Moat/runway after scale | Imitation/erosion speed | Continuous risk in Ke; material funding/technical failure probability-weighted outside K3 | Include funding runway and expected equity raises | Capitalize material R&D/customer acquisition; normalize SBC and launch costs | Revenue growth copied into g; discrete failure hidden only in Ke | `[DG]+[HP]` [D01], [D10], [D13], [D18] |
| **Pre-revenue** | Nonzero negative ROE on a documented economic book/loss base | Post-launch sustainable ROE | Change in loss magnitude/book; keep sign within F1 | Profitable-regime earnings/book growth | To launch/breakeven boundary | Product-market fit and barriers after launch | Adoption-to-maturity erosion | Continuous risk in Ke; technical/funding failure probability-weighted outside K3 | Model expected external equity; debt only if executable | If `NI₀=0`, use the exact P/B companion scale | `K3×0`; loss-to-profit crossing inside F1; binary failure only in Ke | `[FF]+[DG]+[HP]` [D10], [D13] |
| **Negative earnings** | Negative on normalized economic book | Normalized positive or less-negative target economics | Growth of the loss/book regime; positive g can enlarge a negative loss | Earnings/book growth after regime change | To observable inflection | Advantage duration after normalization | Competitive erosion after F2 | Continuous risk in Ke; material distress/failure probability-weighted outside K3 | Validate funding capacity without generic dilution haircuts | Separate cyclical loss, investment loss, accounting loss and structural loss | Interpreting negative P/L as cheap/expensive; distress hidden only in Ke | `[FF]+[DG]` [D01], [D13] |
| **Turnaround** | Depressed ROE after one-off cleanup | ROE from a named margin/turnover/structure mechanism | F1 earnings/book under current operations | F2 growth after normalized economics are reached | Execution timetable | Durability of post-turnaround advantage | Speed of competitive normalization | Ke tracks continuous risk; material execution failure is scenario-weighted | Include recapitalization explicitly | Normalize restructuring, idle capacity, working capital and taxes | Hiding ROE recovery inside g or execution failure only in Ke | `[DG]+[HP]` [D01], [D02], [D12], [D13] |
| **High-ROE compounder** | Current sustainable economic ROE | Marginal ROE on the next reinvestment runway | Current-regime earnings/book | Reinvestment runway translated to earnings/book | Until current economics change | Core moat duration | Erosion speed after moat weakens | Risk-based; do not reward quality by lowering Ke twice | Structure consistent with reinvestment and optionality | Adjust buybacks, intangibles and acquisition accounting | Extrapolating historical ROE and CAP indefinitely | `[DG]+[HP]` [D01], [D04], [D09] |
| **Mature cash cow** | Normalized mature ROE | Sustainable ROE after remaining efficiency/competition effects | Low earnings/book growth | Mature earnings/book growth | Short transition if current state is already mature | Remaining franchise duration | Usually gradual unless disrupted | Mature business risk and leverage | Separate distributable cash from required cash | Normalize excess cash, buybacks and transitory margins | Treating high ROE without runway as high g | `[DG]+[HP]` [D11], [D09] |
| **Capital intensive** | Economic ROE after full maintenance capital | Marginal ROE on new capacity | Earnings/book growth consistent with capital needs | Target growth requiring sufficient equity funding | Construction/ramp or cycle timetable | Scarcity, cost or regulatory advantage duration | Capacity entry and asset-obsolescence speed | Reflect cyclicality, duration and leverage | Use sustainable target leverage and bridge | Correct depreciation, leases, asset age and replacement cost when material | Assuming `ROE≈Ke` mechanically or ignoring reinvestment burden | `[DG]+[HP]` [D09], [D20] |
| **Asset-light** | Recast ROE on economic intangible book | Marginal return after fully charging growth investment | Earnings/book on adjusted capital | Growth after capitalized R&D/CAC/training | Until margin/scale regime changes | Data, brand, switching and network advantage duration | Imitation/obsolescence speed | Business risk, not low accounting assets | Usually low operating debt; preserve required cash | Capitalize material intangible investment consistently | Treating accounting ROE as economic moat | `[DG]+[HP]` [D18], [D09] |
| **High leverage** | ROE decomposed into operating return and leverage/cash carry | ROE at an executable target structure | Growth compatible with covenants and cash needs | F2 growth after refinancing/deleveraging | To refinancing/recap event | Operating moat, not leverage duration | Competitive erosion | Continuous leverage risk in Ke; material default/refinancing failure probability-weighted outside K3 | Bridge and target ratios are central | Normalize debt-like obligations, interest and cash yield | Holding ROE/Ke fixed while changing leverage; default hidden only in Ke | `[DG]+[FF]` [D01], [D06], [D07], [D13] |
| **Net cash** | ROE including cash only if Ke also reflects it | ROE at sustainable cash policy | Earnings/book with required liquidity | Target growth after planned cash use/distribution | To distribution/investment event | Operating moat duration | Operating erosion | May be lower only if equity risk truly falls | `NDE<0` allowed; classify trapped/operating cash correctly | Separate excess, regulatory, trapped and operating cash | Treating all cash as immediately distributable | `[FF]+[DG]` [D09] |
| **Declining / run-off** | ROE on shrinking normalized book | ROE during managed run-off or residual franchise | `g1<0` allowed | `g2≤0` if decline persists; no forced recovery | To new run-off state | Residual contracts/brand economics | Attrition/depletion speed | Include distress and concentration risk | Delever as cash flows shrink unless evidence says otherwise | Normalize closure costs, asset sales and working-capital release | Forcing positive stable growth or ignoring liquidation of book | `[DG]+[HP]` [D12], [D13] |
| **Serial acquirer / roll-up** | ROE after acquisition accounting | Marginal ROE of future deals plus organic business | Separate organic earnings/book from integration period | Growth funded by deal cadence and capital access | Integration cycle | Duration of sourcing/allocation advantage | Fade of deal economics and multiple arbitrage | Include execution, financing and repricing risk | Model equity/debt issuance and bridge | Recast goodwill, earn-outs, stock consideration and one-offs | Treating acquired growth as free organic compounding | `[DG]+[HP]` [D01], [D09] |
| **Negative book equity** | Use documented economic equity; raw ROE may be meaningless | ROE on the same coherent economic base | Earnings/book growth on adjusted base | Target economics on adjusted base | To normalization event | Based on underlying advantage | Based on erosion | Risk-based | Ratios use the adjusted K3 book base consistently | Rebuild book for buybacks, losses, intangibles and write-offs | Feeding raw negative book and unstable ratios into K3 | `[DG]+[HP]` [D09] |

### 7.2 Cycles, resources and regulated assets

| Archetype | ROE1 | ROE2 | g1 | g2 | n1 | n2 | F | Ke | GDE/NDE | Normalization | Principal failure mode | Class/source |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **Cyclical** | Mid-cycle ROE unless F1 explicitly represents current cycle | Sustainable mid-cycle marginal ROE | Cycle-consistent earnings/book growth | Through-cycle earnings/book growth | To cycle normalization | Structural advantage duration, not cycle length | Erosion of structural advantage | Include systematic cyclicality | Use through-cycle leverage and liquidity | Normalize over a full cycle with scaled margins/capital | Capitalizing peak/trough earnings or calling the cycle a moat | `[DG]+[HP]` [D17] |
| **Commodity** | ROE at normalized commodity price and utilization | ROE on marginal projects at normalized curve | Production/book path under current assets | Reserve/capacity growth consistent with reinvestment | To price/capacity normalization | Cost-curve/asset-scarcity advantage duration | Entry, depletion and substitution speed | Commodity, sovereign and distress risk | Use conservative through-cycle leverage | Normalize price, grade, recovery, royalties, closure and sustaining capital | Perpetuating a supercycle or ignoring depletion | `[DG]+[HP]` [D17] |
| **Regulated utility** | Earned ROE on beginning regulatory/economic equity | Allowed-and-achievable ROE after next reset | Rate-base/book growth translated to NI/book | Sustainable rate-base/book growth | To next rate case or major project completion | Regulatory compact and asset-need persistence | Reset/competition/technology erosion | Reflect regulatory, duration and leverage risk | Use approved/executable capital structure | Reconcile accounting book, rate base, disallowances and CWIP | Equating allowed ROE with achieved ROE or assuming regulation guarantees spread | `[DG]+[HP]` [D01], [D09] |
| **Concession business** | ROE under current tariff/volume/asset base | ROE under enforceable target terms | Earnings/book growth through current ramp | Mature concession earnings/book growth | Construction/ramp or tariff reset | Anchor to enforceable term plus evidence on renewal economics | Cliff if rights expire; slower if renewal/embedded assets support it | Country, regulatory and demand risk | Match debt amortization to concession cash generation | Normalize construction accounting, inflation indexation and maintenance | Extending CAP beyond contractual economics without renewal evidence | `[HP]` grounded in [D04], [D09] |
| **Real-estate operating company** | ROE on economic property equity after normalized occupancy/rents | ROE on stabilized developments/services | Book/earnings growth through lease-up or pipeline | Stabilized earnings/book growth | To stabilization | Location, platform and replacement-cost advantage duration | Lease repricing, new supply and obsolescence | Property cycle, duration and leverage risk | Property-level and corporate leverage; required liquidity | Revalue distortions, capitalized interest, maintenance and development gains | Mixing asset revaluation gains with recurring ROE | `[HP]` grounded in [D09], [D11] |
| **Natural-resource depletion business** | ROE on producing assets at normalized prices | Marginal ROE on developed reserves/replacement projects | Production/book path including depletion | Often lower or negative absent reserve replacement | To plateau/decline or project start | Cost position and reserve-life economics | Geological depletion/substitution/permit erosion | Commodity, geology, country and closure risk | Debt sized to reserve life and price stress | Normalize reserves, depletion, royalties, stripping and closure liabilities | Treating finite reserves as perpetual growth | `[HP]` grounded in [D17], [D09] |

### 7.3 Financial services

| Archetype | ROE1 | ROE2 | g1 | g2 | n1 | n2 | F | Ke | GDE/NDE | Normalization | Principal failure mode | Class/source |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **Financial services — general** | Normalized ROE on beginning book/regulatory equity | Forward ROE after cycle and capital rules | NI/book growth consistent with capital creation/raising | Sustainable equity growth | To normalization or rule change | Distribution, underwriting, funding or data advantage | Competitive/regulatory erosion | Equity-only, bottom-up risk | Use an equity-consistent neutralization convention unless explicit equity recap is modeled | Normalize credit/market cycle and one-offs | Importing industrial debt mechanics into operating liabilities | `[DG]+[HP]` [D14]–[D16] |
| **Bank** | ROE/ROTE after normalized credit cost and NIM | Sustainable ROE under target capital and funding | NI/book growth consistent with regulatory capital | Loan/deposit/book growth supported by capital | To credit/NIM normalization | Funding, underwriting, distribution and scale advantage | Deposit repricing, competition and credit erosion | Do not mechanically relever beta with deposits as corporate debt | Usually set `GDE=NDE` and keep structure constant; change only for explicit equity recap | Normalize provisions, reserve releases, securities marks and excess capital | Double-counting deposits/debt or using peak credit ROE | `[DG]+[HP]` [D14]–[D16] |
| **Insurer** | ROE from normalized underwriting plus investment/float economics | Sustainable ROE under target reserves/capital | Premium/book growth compatible with solvency capital | Mature premium/book growth and capital retention | To pricing/reserve normalization | Underwriting, distribution, data and cost advantage | Pricing-cycle and imitation speed | Reflect catastrophe, reserve, asset and leverage risk | Equity-consistent neutralization; explicit capital release only when real | Normalize loss ratios, reserve development, catastrophe years and portfolio yield | Treating favorable reserve release or hard market as permanent ROE | `[DG]+[HP]` [D14], [D16] |
| **Broker** | ROE normalized for volumes, rates and client cash | Sustainable platform ROE | Account/activity/book growth, not trading revenue alone | Mature client/book earnings growth | To rate/volume normalization | Platform, custody, pricing and switching advantage | Fee compression and technology erosion | Market-activity, liquidity and operational risk | Neutralize operating client liabilities; model true equity recap only | Normalize interest income, activity, market levels and one-offs | Extrapolating rate windfall or bull-market activity | `[DG]+[HP]` [D14]–[D16] |
| **Asset manager** | ROE after normalized fees/performance and seed capital | Sustainable ROE at normalized fee rate/mix | AUM/flow economics translated to NI/book | Long-run NI/book growth after fee pressure | To fee/performance normalization | Distribution, brand, track record and switching duration | Outflows, fee compression and key-person erosion | Market beta, flow cyclicality and concentration | Separate operating cash/seed capital from distributable cash | Normalize market beta in AUM, performance fees and compensation | Treating market appreciation as persistent organic g | `[DG]+[HP]` [D14]–[D16] |

### 7.4 Contract, product and business-model archetypes

| Archetype | ROE1 | ROE2 | g1 | g2 | n1 | n2 | F | Ke | GDE/NDE | Normalization | Principal failure mode | Class/source |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **Pharma / IP cliff** | Product-portfolio ROE before exclusivity loss | ROE of post-cliff portfolio/pipeline on economic R&D book | Earnings/book through current exclusivity | Risk-adjusted post-transition earnings/book | To patent/launch/LOE milestone | Evidence-backed exclusivity and pipeline durability | Often fast at cliff; slower for biologics/complex substitution | Continuous pipeline/concentration risk in Ke; material trial, approval or license failure scenario-weighted | Separate true financing debt from collaboration obligations | Capitalize R&D consistently; normalize milestone/licensing gains | Infinite CAP for a patent; unproven pipeline treated as certain or hidden only in Ke | `[DG]+[HP]` [D04], [D13], [D18] |
| **Project-based business** | ROE on normalized project capital and working capital | Marginal ROE on future awarded projects | Backlog conversion translated to NI/book | Sustainable award/book growth | To backlog or project mix reset | Customer relationships, licenses and execution advantage | Backlog runoff and bid competition | Contract, execution, counterparty and working-capital risk | Include bonding, advances and project financing consistently | Normalize percentage-of-completion, claims and milestone volatility | Using backlog revenue as g without margin/book/funding reconciliation | `[HP]` grounded in [D01], [D09] |
| **Subscription business** | Cohort-adjusted ROE on economic CAC/product capital | Marginal ROE of mature cohorts | NI/book growth under current cohort mix | Growth from retention, price and new cohorts | To unit-economics maturity | Switching, workflow and retention advantage | Churn/competition and price compression speed | Product, concentration and execution risk | Funding must cover CAC/payback; classify deferred revenue consistently | Capitalize material CAC/R&D consistently; normalize upfront sales cost | Using ARR growth as g despite changing margins and capitalized acquisition cost | `[HP]` grounded in [D10], [D18] |
| **Marketplace / network** | ROE on economic platform and acquisition capital | ROE after scale/take-rate normalization | NI/book growth during liquidity build | Mature transaction/book earnings growth | To minimum efficient liquidity/scale | Network effects after testing multi-homing and disintermediation | User migration and imitation speed | Platform, regulation and concentration risk | Often net cash; retain required trust/safety liquidity | Capitalize material development/acquisition investment | Assigning long CAP from gross volume growth without retention or monetization proof | `[HP]` grounded in [D04], [D10], [D18] |

### 7.5 NI₀ and book-edge conventions

- `[FF] IF NI₀<0, THEN` calculate K3 only with a coherent nonzero ROE/book scale and report Equity Value, not a cheap/expensive P/L.
- `[MI] IF NI₀→0, THEN` test numerical stability because K3 is a value-per-earnings normalization.
- `[MI] IF NI₀=0 exactly, THEN` do not compute `K3×0`. Use the exact P/B companion form and `Equity Value=K_PB×Book₀`; when `ROE1=0`, use the algebraically cancelled P/B form directly and never evaluate `K3×ROE1/(1+g1)` as an `∞×0` path.
- `[FF] IF Book₀ is negative/distorted, THEN` reconstruct a documented economic book and use it consistently in ROE, GDE and NDE.

---

## 8. EQUITY-ONLY SANITY CHECKS

- `[DG] IF ROE2≫Ke2 for long n2, THEN CHECK` moat, marginal return, runway, competitive response and duration. ([D04], [D09])
- `[DG] IF ROE<Ke with high g, THEN CHECK` whether value-destructive growth is intentionally transitional. ([D03], [D09])
- `[FF] IF g>ROE, THEN CHECK` external funding, dilution, market access and cumulative negative distributions; do not reject automatically.
- `[FF] IF g came from revenue CAGR, THEN CHECK` whether NI and book actually grow at that rate under constant ROE.
- `[FF] IF` `ROE1` does not reconcile with normalized `NI1/Book0`, `THEN CHECK` book and earnings adjustments.
- `[DG] IF ROE2 differs materially from ROE1, THEN CHECK` the named mechanism and marginal-return evidence. ([D01], [D02])
- `[DG] IF Ke2<Ke1, THEN CHECK` real risk reduction. ([D06], [D07])
- `[FF] IF GDE/NDE change, THEN CHECK` book denominator, executability, bridge sign and recalibration of ROE/Ke.
- `[FF] IF cash is material, THEN CHECK` whether it is distributable, operating, regulatory or trapped.
- `[FF] IF GDE>NDE, THEN CHECK` whether zero cash yield is appropriate and reconcile the debt-financed cash carry through normalized ROE; the `GDE2+10pp` pure partial holds ROE2 artificially fixed.
- `[FF] IF GDE<NDE, THEN INVALID` under the canonical gross/net-debt definitions because it implies negative cash; correct the structure before use.
- `[FF] IF n1=0, THEN CHECK` F1 boundary-scale inputs; only F1 cash flows disappear.
- `[FF] IF n2=0, THEN CHECK` direct transition into fade and preserve ROE2, Ke2, g2 and F2 structure at fade entry.
- `[MI] IF ROE1=0, THEN CHECK` that the cancelled P/B companion form is used; do not evaluate literal K3 first.
- `[FF]+[MI] IF ROE2=0, THEN CHECK` `A2_cancelled`; the literal K3 cell is singular at this supported boundary.
- `[MI] IF 1e−12≤|Ke−g|<1e−6, THEN REVIEW` numerical conditioning and compare a stable `log1p/expm1` or exact-limit calculation with high precision.
- `[DG] IF a material discrete failure can prevent fade/terminal, THEN CHECK` separate probability-weighted going-concern and equity-recovery scenarios without duplicating the event in Ke. ([D13])
- `[FF] IF negative FCFE or future fair-value funding exists, THEN CHECK` that neither a generic dilution haircut nor future funding shares were added again.
- `[DG] IF country risk is included, THEN CHECK` mature-market ERP, `λ×CRP`, risk-free currency and absence of double counting. ([D08])
- `[HP] IF n2/F fall outside review priors, THEN CHECK` company-specific evidence; do not reject.
- `[HP] IF n2 came from a factor count, THEN CHECK` correlation, intensity and duration of the alleged barriers.
- `[FF] IF g_T sensitivity looks large, THEN CHECK` F first; longer fade mechanically increases path exposure.
- `[FF] IF terminal is implemented, THEN CHECK` `ROE_T=Ke2`, `P/B_T=1` and `TV=Book_T`.
- `[MI] IF structure is constant, cash is zero and ROE=Ke in every regime, THEN CHECK` `P/B₀=1`.
- `[FF] IF spreadsheet auditor is used, THEN CHECK` `K5≈0`, `G309≈0` and `n1+n2+F≤25` only for year-by-year audit coverage.
- `[FF] IF sensitivities are run, THEN CHECK` Ke monotonicity, F1-vs-F2 displacement and linked economics before interpreting partials.
- `[FF] IF P/B is extreme, THEN CHECK` spread, duration, economic book and structure; use no universal cutoff.
- `[FF] IF NI₀≤0, THEN CHECK` output units and normalization before communicating value.

---

## 9. AI FAILURE MODES

| Error | Detector | Correct treatment | Class/source |
|---|---|---|---|
| Revenue growth used as g | `g` equals revenue CAGR while ROE/margins change | Translate operating path into earnings/book regimes | `[FF]+[DG]` [D01], [D02] |
| Historical ROE extrapolated | Raw average with no book/earnings normalization | Normalize and prioritize marginal economics | `[DG]` [D01], [D09] |
| ROE high only because of leverage | Weak operating economics; high debt carry | Re-derive ROE and Ke at target structure | `[DG]` [D01], [D06] |
| Separate reinvestment plug | K3 g conflicts with another funding schedule | Let K3 derive equity funding from g/ROE/α | `[FF]` |
| External funding rejected | Negative distribution automatically marked invalid | Test funding and dilution; keep if executable | `[FF]+[DG]` [D01] |
| Generic dilution haircut after negative FCFE | Funding requirement was already deducted in K3 | Remove the haircut; funding was counted twice | `[FF]` |
| Future funding shares added to denominator | Capital requirement already reduced FCFE | Use current diluted shares at t=0; future fair-value funding shares would count funding twice | `[FF]+[MI]` |
| Discrete failure hidden only in Ke | Going-concern fade and terminal remain implicitly certain | Probability-weight K3 going-concern and equity-recovery scenarios without double counting | `[DG]+[HP]` [D13] |
| Arbitrary n2 | No duration evidence | Use competitive evidence plus review priors | `[DG]+[HP]` [D04], [D05] |
| Moat-factor scoring | “Three factors = 15 years” | Evaluate strength, independence and durability | `[HP]` |
| Fade used as plug | F changed to hit price | Calibrate imitation/erosion speed | `[HP]` |
| Slowdown confused with fade | Lower g automatically lowers ROE | Keep growth and competitive return as separate axes | `[FF]` |
| Hurdle called fair value or target IRR | Ke changed and output labelled fair value/IRR | Label `Hurdle-conditioned Equity Value` or `Required-return scenario value` | `[FF]+[HP]` |
| Country risk counted twice | Country-inclusive ERP plus separate CRP | Use Mature-Market ERP plus `λ×CRP`, or explicitly reconcile the alternative | `[DG]` [D08] |
| Ke reverse-engineered | Ke changed after viewing price | Restrict to labelled reverse valuation | `[FF]` |
| g_T treated as perpetual growth | Terminal discussion uses a `Ke−g_T` denominator | Restore finite path and `TV=Book_T` | `[FF]` |
| Fixed g_T bug threshold | A material sensitivity is called an error automatically | Interpret jointly with F | `[FF]+[RA]` |
| GDE/NDE use market cap | Ratios change with share price | Use K3 book-model equity | `[FF]` |
| All cash treated as excess | Regulatory/operating cash reduces α | Normalize economically attributable cash | `[FF]+[DG]` [D09], [D14] |
| Structure changes without ROE/Ke | Debt ratios move; returns/risk stay mechanical | Recalibrate linked economics | `[DG]` [D01], [D06], [D07] |
| Cash carry ignored | Gross debt and cash coexist but ROE is unchanged | Reconcile `ROE = ROIC×(1+NDE)−kd_at×GDE`; reflect actual cash yield in normalized ROE | `[FF]+[DG]` [D06], [D09] |
| `n1=0` interpreted as F1 inputs irrelevant | F2/book scale is mis-specified | Calibrate ROE1, g1 and F1 structure even with zero F1 cash-flow years | `[FF]+[MI]` |
| Hard duration cutoff | n2/F rejected solely by number | Treat ranges as review priors | `[HP]` |
| Intangible capital ignored | Asset-light ROE is implausibly high | Recast economic book and earnings | `[DG]` [D18], [D09] |
| P/L interpreted with NI₀<0 | Negative P/L called cheap/expensive | Report Equity Value and normalization | `[FF]` |
| `K3×0` used with NI₀=0 | Equity Value reported as zero | Use the exact P/B companion form and economic Book₀ | `[MI]` |
| Literal K3 evaluated at ROE2=0 | `ROE2/ROE1` multiplies a division by ROE2 | Use `A2_cancelled`; classify as supported only through the cancelled implementation | `[FF]+[MI]` |
| Loss-to-profit crossing inside F1 | Constant g path changes NI sign | Put sign change at F1→F2 boundary | `[FF]` |
| Bridge omitted | Two phase annuities added directly | Restore `rz` and recapitalization bridge | `[FF]` |
| F2 boundary discounted at Ke1 | Year n1+1 treated as F1 | Use Ke2 for first F2 flow and bridge | `[FF]` |

---

## 10. EXECUTION PROTOCOL

1. `[DG]` Normalize `NI₀` and economic book. ([D09], [D18])
2. `[DG]` Explain current ROE through operating economics, leverage, cash and accounting; use the cash-carry identity only as a calibration reconciliation. ([D01], [D06], [D09])
3. `[FF]` Calibrate `ROE1` and reconcile `NI1/Book0`.
4. `[FF]` Calibrate `g1` as F1 earnings/book growth.
5. `[HP]` Set `n1` from an observable regime-change timetable.
6. `[DG]` Calibrate `ROE2` from marginal economics and a named mechanism. ([D01], [D02])
7. `[FF]+[DG]` Calibrate `g2` from earnings/book runway and funding. ([D01], [D10])
8. `[DG]+[HP]` Defend `n2` with competitive evidence and review priors. ([D04], [D05])
9. `[HP]` Defend `F` with erosion/imitation speed.
10. `[DG]` Calibrate Ke1/Ke2 from continuous economic equity risk using the explicit country-risk convention and no double counting. ([D06]–[D08])
11. `[FF]+[DG]` Calibrate GDE/NDE on K3 book equity and revisit ROE/Ke if structure changes. ([D01], [D06], [D07], [D09])
12. `[FF]` Calibrate Kd_F2/t only for bridge economics.
13. `[FF]` Set g_T as the last fade-year growth rate.
14. `[FF]` Run K3 and record `V_F1, V_F2, Ponte, fade dividends, terminal book, V_fade`; use the P/B or `A2_cancelled` companion implementation at supported singular boundaries.
15. `[MI]` Select `NI₀` or `Book₀` only as the output scale and calculate Current-holder Equity Value and value per current diluted share without adding future funding shares.
16. `[MI]` Run all formula invariants, P/B/cancelled equivalence checks, boundary tests and machine regressions.
17. `[FF]` Run equity-only sanity checks and the input/numerical-stability contract.
18. `[DG]+[HP]` If material discrete failure exists, run internally coherent K3 going-concern states and blend Equity Values with equity recovery outside K3. ([D13])
19. `[HP]` Build a value range by varying economically linked inputs, not by haircutting output.
20. `[FF]` Compare with market price only after fundamental calibration is frozen.
21. `[FF]` Label reverse valuation, `Probability-weighted Equity Value` and hurdle-conditioned outputs separately.

---

## 11. FORMULA INVARIANTS & REGRESSION TESTS

### 11.1 Base-conversion invariants

- `[MI] Equity Value = K3 × NI₀`.
- `[MI] NI₁ = NI₀ × (1+g1)`.
- `[MI] Implied forward P/L = K3/(1+g1)`.
- `[MI] Implied Book₀ = NI₀×(1+g1)/ROE1`.
- `[MI] Implied P/B₀ = K3×ROE1/(1+g1)`.
- `[MI]` The forward P/L identity is exact inside K3 because its denominator is model `NI₁`; only an external market-NTM comparison may require calendar or earnings-definition alignment.

### 11.2 Exact P/B Companion Form

`[MI] K_PB = Equity Value / Book₀`.

For `ROE1≠0`:

`K_PB = K3×ROE1/(1+g1)`

The algebraically cancelled direct form is:

`K_PB = PB_F1 + PB_F2 + PB_Ponte + PB_fade`

This is an exact reparameterization of K3, not an alternative valuation engine. It uses the same 16 economic inputs. K3 remains canonical when earnings normalization is valid; use the direct P/B form when `ROE1=0` or earnings normalization is singular, with `Equity Value=K_PB×Book₀`. Never evaluate K3 first and then multiply an infinite result by zero.

#### 11.2.1 PB_F1

Standard branch:

`PB_F1 = (ROE1−α1·g1) × [1−((1+g1)/(1+Ke1))^n1] / (Ke1−g1)`

When `|Ke1−g1|<1e−12`:

`PB_F1 = (ROE1−α1·g1) × n1/(1+g1)`

#### 11.2.2 A2_cancelled and PB_F2

`[MI]` The literal K3 contains `ROE2/ROE1` outside F2 and a division by `ROE2` inside its annuity. Those terms cancel algebraically.

Standard branch:

`A2_cancelled = (ROE2−α2·g2)·(1+g2)·[1−((1+g2)/(1+Ke2))^n2]/(Ke2−g2)`

When `|Ke2−g2|<1e−12`:

`A2_cancelled = (ROE2−α2·g2)·n2`

Then:

`V_F2_cancelled = [(1+g1)^(n1+1)/(1+g2)] × rz/[ROE1·(1+Ke1)^n1] × A2_cancelled`

`PB_F2 = [(1+g1)^n1/(1+g2)] × rz/(1+Ke1)^n1 × A2_cancelled`

- `[MI]` For `ROE2≠0`, the cancelled and literal K3 F2 forms are exactly equivalent.
- `[FF]` `ROE2=0` is economically valid only through `A2_cancelled`; classify it `SUPPORTED_BOUNDARY VIA CANCELLED IMPLEMENTATION`.
- `[FF]` The literal spreadsheet K3 remains numerically singular at `ROE2=0` and must not be labelled valid at that boundary. The K3 cell itself is unchanged.

#### 11.2.3 PB_Ponte and PB_fade

`PB_Ponte = [(1+g1)^n1/(1+Ke1)^n1] × (GDE2·rz−GDE1) × (1+kd_at)/(1+Ke2)`

`PB_pref = (1+g1)^n1 × rz/(1+Ke1)^n1 × ((1+g2)/(1+Ke2))^n2`

For `F=0`:

`PB_fade = PB_pref`

For `F>0`:

`PB_fade = PB_pref × [Σ_{k=1}^{F} prod_g(k)·(ROE_k−α2·g_k)/(1+Ke2)^k + Π_{k=1}^{F}(1+g_k)/(1+Ke2)^F]`

#### 11.2.4 P/B and zero-ROE regressions

`[RA]` Case-base P/B equivalence:

| Route | Expected `K_PB` |
|---|---:|
| Direct P/B companion | 3.5411176854758883 |
| `K3×ROE1/(1+g1)` | 3.5411176854758883 |

`[MI]` Twenty-four deterministic cases with fixed seed `22021` covered positive/negative ROE1 and ROE2, `n1=0`, `n2=0`, `F=0`, both `Ke=g` limits, negative growth and different structures. Maximum absolute P/B difference was `2.67e−15`; maximum literal-versus-cancelled F2 difference for `ROE2≠0` was `1.43e−14`.

`[RA]` With base inputs except `ROE1=0`:

| P/B block | Expected value |
|---|---:|
| `PB_F1` | −0.3340174988523891 |
| `PB_F2` | 2.5694039778758824 |
| `PB_Ponte` | −0.2421634891293020 |
| `PB_fade` | 1.1705135214396996 |
| **K_PB** | **3.163736511333891** |
| Equity Value at `Book₀=100` | 316.3736511333891 |

`[RA]` With base inputs except `ROE2=0`, evaluated through `A2_cancelled`:

| K3-equivalent block | Expected value |
|---|---:|
| `V_F1` | 0.44777708179487147 |
| `V_F2_cancelled` | −11.960122850842113 |
| `Ponte` | −2.5006012464438787 |
| Fade dividends | 0.312049950182806 |
| Terminal book PV | 5.917724448075871 |
| `V_fade` | 6.229774398258678 |
| **K3-equivalent total** | **−7.783172617232443** |

Tolerances are `1e−12` for base P/B equivalence and `1e−10` for zero-ROE boundary anchors.

### 11.3 No-excess-return limit

`[MI] IF` all of the following hold:

- `ROE1=Ke1`;
- `ROE2=Ke2`;
- capital structure is constant;
- cash is zero, so `GDE=NDE`;
- there is no economic recapitalization;

`[MI] THEN`:

- `P/B₀=1`;
- `P/L forward=1/Ke1`;
- `P/L trailing=(1+g1)/Ke1`.

`[MI]` Algebra: zero excess return makes each unit of book worth one unit of equity. Therefore `Equity Value=Book₀`. Since `Book₀=NI₀(1+g1)/ROE1` and `ROE1=Ke1`, trailing K3 equals `(1+g1)/Ke1`; dividing by `(1+g1)` gives forward P/L `1/Ke1`.

`[DG]` Economic interpretation: growth without excess equity returns increases the scale of earnings and book but does not create value above book. ([D03], [D04], [D09])

`[RA]` Independent numerical test:

| Test input | Value |
|---|---:|
| `ROE1=Ke1` | 18.00% |
| `ROE2=Ke2` | 14.00% |
| `g1 / g2 / g_T` | 8.00% / 5.00% / 3.00% |
| `n1 / n2 / F` | 4 / 7 / 6 years |
| `GDE1=NDE1=GDE2=NDE2` | 25.00% |
| Expected / reproduced trailing P/L | 6.000000000000 / 6.000000000000 |
| Expected / reproduced forward P/L | 5.555555555556 / 5.555555555556 |
| Reproduced P/B₀ | 1.000000000000 |

### 11.4 Boundary conventions

- `[FF]` F1 contains years `1…n1`.
- `[FF]` Year `n1+1` belongs to F2.
- `[FF]` The first F2 cash flow is discounted by `(1+Ke1)^n1·(1+Ke2)`.
- `[FF]` The recapitalization bridge occurs at the same boundary and uses the same phase switch in discounting.
- `[FF]` `rz=(1+NDE1)/(1+NDE2)` rebases the equity base across the target net-debt structure.
- `[FF]` Omitting the bridge breaks equivalence with the direct equity cash-flow recurrence.
- `[FF]` Fade begins after `n2` full F2 years.
- `[FF]` At fade year F, `ROE_F=Ke2`; terminal `P/B=1`; terminal value equals book.

`[RA]` First-F2-year boundary test with base inputs and `n2=1`:

- Closed F2 block: `2.317788390817612`.
- Direct first-year F2 FCFE discounted at `Ke2`: `2.317788390817624`.
- Absolute difference: `1.20e−14`.

### 11.5 Exact base-case vector

`[RA]` Use the full-precision cell values below. The six-decimal ROE figures shown in prior prose were display rounds.

| Canonical input | Exact value | Unit |
|---|---:|---|
| `ROE1` | 0.10846315789473689 | decimal |
| `ROE2` | 0.43447894736842096 | decimal |
| `g1` | 0.12 | decimal |
| `g2` | 0.15 | decimal |
| `Ke1` | 0.22 | decimal |
| `Ke2` | 0.16 | decimal |
| `n1` | 5 | years |
| `n2` | 12 | years |
| `NDE1` | 0.60 | debt/book equity |
| `NDE2` | 0.20 | debt/book equity |
| `GDE1` | 0.80 | debt/book equity |
| `GDE2` | 0.30 | debt/book equity |
| `F` | 5 | years |
| `g_T` | 0.05 | decimal |
| `Kd_F2` | 0.11 | decimal |
| `t` | 0.30 | decimal |

`[RA]` Independently reproduced outputs:

| Output | Expected value |
|---|---:|
| `V_F1` | 0.447777081794871 |
| `V_F2` | 26.531888901979215 |
| `Ponte` | −2.500601246443879 |
| Fade dividends | 6.169099958094935 |
| Terminal book PV | 5.917724448075871 |
| `V_fade` | 12.086824406170805 |
| **K3 / trailing P/L** | **36.56588914350101** |
| Workbook cached K3 | 36.56588914350100 |
| Direct year-by-year recurrence | 36.56588914350114 |
| Maximum block/total difference | 1.28e−13 |

`[RA]` Base conversion at `NI₀=5.75`:

| Converted output | Value |
|---|---:|
| Equity Value | 210.25386257513082 |
| Implied forward P/L | 32.64811530669733 |
| Implied Book₀ | 59.37499999999998 |
| Implied P/B₀ | 3.541117685475888 |

### 11.6 CASE-BASE PARTIAL SENSITIVITIES — NOT UNIVERSAL ECONOMIC RULES

- `[RA]` Each row changes only the named input and holds all other base inputs constant.
- `[RA]` These are pure partial derivatives/differences, implementation tests and local nonlinearity illustrations.
- `[DG]` A real change in GDE/NDE normally requires re-deriving ROE2 and Ke2; the pure partial can therefore create an economically inconsistent counterfactual. ([D01], [D06], [D07])
- `[FF]+[DG]` The case-base `GDE2+10pp = +6.72%` partial holds ROE2 artificially fixed. Economically, more gross debt or associated cash can reduce ROE2 through negative carry in `ROE = ROIC×(1+NDE)−kd_at×GDE`; this is an implementation test, not a structure recommendation. ([D06], [D09])
- `[FF]` ROE1 has a counterintuitive local sign because it changes current distribution and inversely anchors implicit Book₀/F2 scale.
- `[FF]` The sign of n1 depends on F1 quality relative to the future regimes displaced.

| Pure partial | Bumped P/L | Change vs base | Expected sign |
|---|---:|---:|---|
| `n1 +1 year` | 33.674173354832 | **−7.91%** | Negative in this case only |
| `n2 +1 year` | 38.550757592007 | **+5.43%** | Positive in this case |
| `n2 −1 year` | 34.563760969356 | **−5.48%** | Negative in this case |
| `F +1 year` | 37.504320192422 | **+2.57%** | Positive in this case |
| `F −1 year` | 35.608196806811 | **−2.62%** | Negative in this case |
| `ROE1 +1pp` | 33.808152569183 | **−7.54%** | Counterintuitive book-anchor effect |
| `ROE2 +1pp` | 37.586630471230 | **+2.79%** | Positive |
| `g2 +1pp` | 38.377479491603 | **+4.95%** | Positive in this case |
| `Ke2 −50bps` | 38.052608695354 | **+4.07%** | Positive |
| `Ke1 −50bps` | 37.320443173482 | **+2.06%** | Positive |
| `GDE2 +10pp` | 39.023227711027 | **+6.72%** | Positive pure partial |
| `NDE2 +10pp` | 31.903968191261 | **−12.75%** | Negative pure partial |

### 11.7 Convexity grids — implementation tests, not calibration ranges

#### g2 convexity grid

| `g2` | Expected P/L |
|---:|---:|
| 5% | 24.0515 |
| 10% | 29.2195 |
| 15% | 36.5659 |
| 20% | 47.0880 |
| 25% | 62.2304 |

#### Ke2 convexity grid

| `Ke2` | Expected P/L |
|---:|---:|
| 12% | 51.0540 |
| 14% | 43.0213 |
| 16% | 36.5659 |
| 18% | 31.3386 |
| 20% | 27.0742 |

- `[RA]` The grids demonstrate nonlinearity and monotonicity around the case-base.
- `[RA]` Do not use the grid endpoints as suggested input ranges.

### 11.8 g_T × Fade interaction

| F | Base P/L | P/L after `g_T+1pp` | Change |
|---:|---:|---:|---:|
| 3 | 34.63037 | 34.64580 | +0.04% |
| 5 | 36.56589 | 36.59553 | +0.08% |
| 10 | 41.07866 | 41.16144 | +0.20% |
| 20 | 48.94109 | 49.17843 | +0.48% |

- `[RA]` Longer fade increases exposure to the g path; a larger g_T effect is not itself a bug.

### 11.9 Additional boundary regression tests

| Test | Input condition | Expected result | Classification |
|---|---|---|---|
| Zero bridge | Base case with `GDE2=GDE1/rz=0.60` | `Ponte=0` | `[MI]` |
| Zero fade | Base case with `F=0` | Fade dividends `=0`; `V_fade=8.091772946388359` | `[MI]` |
| F1 annuity limit | Base case with `Ke1=g1=12%` | Finite `V_F1=0.574534161490686` | `[MI]` |
| F2 annuity limit | Base case with `Ke2=g2=15%` and `ROE_T=Ke2` | Finite `V_F2=28.055316869722898` | `[MI]` |
| Closed vs direct recurrence | Exact base vector | Absolute total difference `<1e−12` | `[RA]` |
| Terminal closure | Every run | `ROE_T=Ke2`; terminal `P/B=1` | `[FF]` |

### 11.10 Zero-duration and negative-ROE boundaries

#### 11.10.1 n1=0

- `[FF] IF n1=0, THEN` `V_F1=0`, but do not ignore ROE1, g1 or F1 structure. They still define implicit book and the scale of F2, bridge and fade.
- `[MI] IF n1=0` and all other inputs are fixed, `THEN K3(g1_new)/K3(g1_old)=(1+g1_new)/(1+g1_old)` exactly.

`[RA]` Base inputs with `n1=0`:

| Output | Expected value |
|---|---:|
| `V_F1` | 0 |
| `V_F2` | 40.68901814220827 |
| `Ponte` | −3.834895052473763 |
| `V_fade` | 18.53622331079799 |
| **K3** | **55.39034640053250** |
| K3 with `ROE1+1pp` | 50.71460185810262 |
| Change from `ROE1+1pp` | −8.4414430425% |
| K3 with `g1+1pp` | 55.88490306482296 |
| Change from `g1+1pp` | +0.8928571429% |
| Exact check | `1.13/1.12−1 = 0.8928571429%` |

#### 11.10.2 n2=0

- `[FF]` F2 has no full-spread years and the firm moves directly from the F1/F2 boundary into fade.
- `[FF]` ROE2, Ke2, g2 and F2 structure remain relevant to fade entry and trajectory.

`[RA]` Base inputs with `n2=0`:

| Output | Expected value |
|---|---:|
| `V_F1` | 0.44777708179487147 |
| `V_F2` | 0 |
| `Ponte` | −2.5006012464438787 |
| `V_fade` | 13.410161228069203 |
| **K3** | **11.357337063420196** |

#### 11.10.3 ROE1<0 and negative earnings

`[FF]` Negative ROE1 and NI₀ are supported. A negative P/L has no intuitive cheap/expensive interpretation, while Equity Value and P/B can remain positive. Opposite block signs are not automatically errors. A loss-to-profit transition belongs at the phase boundary because a constant proportional-growth path cannot cross zero within one regime.

`[RA]` Base vector with `ROE1=−0.08` and output scale `NI₀=−2.0`:

| Output | Expected value |
|---|---:|
| `V_F1` | 8.573115803877988 |
| `V_F2` | −35.97165569026235 |
| `Ponte` | 3.390288847810229 |
| Fade dividends | −8.364000785290822 |
| Terminal book PV | −8.023188514864971 |
| `V_fade` | −16.38718930015579 |
| Trailing P/L | −40.39544033872993 |
| Implied Book₀ | 28.0 |
| Equity Value | 80.79088067745985 |
| Implied P/B₀ | 2.885388595623566 |

### 11.11 Input Domain and Numerical-Stability Contract

| Classification | Minimum conditions | Permitted implementation | Required agent message |
|---|---|---|---|
| `INVALID` | Non-finite input; negative or non-integer `n1/n2/F`; `Ke1≤−1`; `Ke2≤−1`; `g1≤−1`; `g2≤−1`; any fade `g_k≤−1`; `1+NDE2=0`; `GDE1<0`; `GDE2<0`; `GDE1<NDE1`; `GDE2<NDE2` | None until corrected | `INVALID INPUT — correct domain or structure before valuation.` |
| `SUPPORTED_BOUNDARY` | `n1=0`; `n2=0`; `F=0`; `Ke1=g1`; `Ke2=g2`; `ROE1<0`; `ROE2<0`; `NI₀<0`; `NDE<0`; `g>ROE`; finite-phase `g>Ke` | Canonical K3 with exact limit branches where applicable | `SUPPORTED BOUNDARY — preserve sign, scale and output-unit conventions.` |
| `SUPPORTED_VIA_COMPANION_IMPLEMENTATION` | `ROE1=0`; `ROE2=0`; Book₀ normalization when P/L scale is singular | Direct P/B for `ROE1=0`; `A2_cancelled` for `ROE2=0`; `Equity Value=K_PB×Book₀` | `SUPPORTED BOUNDARY VIA COMPANION/CANCELLED IMPLEMENTATION — literal K3 path is singular.` |
| `REVIEW, NOT INVALID` | `t<0` or `t>1`; `Kd<0`; `Ke≤Kd`; NDE near `−1`; cash/equity above 100%; extreme returns, growth or leverage; structure inconsistent with funding access; mathematically valid inputs lacking coherent economics | Run only with an explicit review warning and documented rationale | `REVIEW — mathematically supported, economically unusual or numerically sensitive.` |

`[FF] GDE−NDE=Cash/Equity`. Under the canonical definitions, `GDE<NDE` implies negative cash and is invalid, not a mere review item.

#### 11.11.1 Near Ke=g numerical-stability zone

`[MI] 1e−12 ≤ |Ke−g| < 1e−6 → REVIEW: numerically ill-conditioned standard branch`.

The K3 formula remains unchanged. Direct double-precision evaluation of `1−r^n` loses precision when `r≈1`; code implementations must use the exact limit or a stable `log1p/expm1` evaluation and compare against high precision. This is numerical, not economic, divergence. Apply the same discipline to F1 and F2.

`[RA]` Base case with `Ke1=g1+1e−12`:

| Evaluation | `V_F1` |
|---|---:|
| Standard double precision | 0.5744493264483829 |
| Exact limit | 0.5745341614906857 |
| Approximate relative error | −1.4765883e−4 |

The regression must detect this degradation rather than accept the unstable branch silently.

### 11.12 Distress and Funding Regressions

#### 11.12.1 Discrete distress

`[MI]` If `p_survival=1`, `Probability-weighted Equity Value=K3×NI₀` exactly.

| Test | Expected value | Tolerance |
|---|---:|---:|
| Base case, `p_survival=1` | 210.25386257513082 | `1e−12` |
| Base case, `p_survival=0.60`, recovery `=0` | 126.15231754507849 | `1e−12` |

#### 11.12.2 Fair-value funding equivalence

`[MI]` Start with Current-holder Equity Value `100`, 10 current shares and value per current share `10`. A required capital raise of `25` at fair value issues 2.5 shares at `10`, producing post-money equity value `125`. Old-holder ownership is `10/12.5=80%`; old-holder value remains `125×80%=100`, and value per original share remains `10`. No generic dilution haircut or second denominator adjustment is permitted.

### 11.13 Regression execution standard

1. Use exact numeric inputs, not displayed percentage rounds.
2. Compute closed K3 and return every block separately.
3. Independently compute F1/F2/fade by direct yearly recurrence.
4. Compare blocks and total with absolute tolerance `1e−10` unless a stricter implementation standard is specified.
5. Run both `Ke=g` branches, the near-`Ke=g` stability zone and `F=0`.
6. Run no-excess-return, zero-bridge and first-F2-year boundary tests.
7. Run all 12 pure partials, both convexity grids and the g_T/F grid.
8. Validate direct P/B versus `K3×ROE1/(1+g1)` across at least 20 fixed-seed cases and validate `A2_cancelled` against literal K3 whenever `ROE2≠0`.
9. Run `ROE1=0`, `ROE2=0`, `n1=0`, exact `(1+g1)` proportionality, `n2=0`, negative-ROE1, distress and fair-value-funding tests.
10. Enforce the input contract, current-share denominator and country-risk/hurdle output labels.
11. When using the spreadsheet auditor, confirm `K5≈0` and `G309≈0` within workbook precision.
12. Treat any regression failure as an implementation defect until input precision, units and formula fidelity are proven.

---

## 12. ONE-PAGE AI QUICK REFERENCE

### MOTOR

`[FF] K3 = V_F1 + V_F2 + Ponte + V_fade` — trailing P/L on normalized `NI₀`.

- `V_F1`: F1 FCFE annuity.
- `V_F2`: F2 FCFE annuity on re-scaled book/earnings.
- `Ponte`: one-time F1→F2 recapitalization flow.
- `V_fade`: fade FCFE + terminal book.

### 16 CANONICAL INPUTS

`ROE1, ROE2, g1, g2, Ke1, Ke2, n1, n2, NDE1, NDE2, GDE1, GDE2, F, g_T, Kd_F2, t`.

**Never direct inputs:** revenue, margin, turnover, operating-return metrics, market multiples or market price.

**Valuation scale:** `NI₀` for P/L; `Book₀` for the exact P/B companion. Neither is a seventeenth economic input.

### EXACT CONVERSIONS

- `Current-holder Equity Value=K3×NI₀` when earnings normalization is valid.
- `Value per current diluted share=Current-holder Equity Value/current diluted shares at t=0`.
- `P/L forward=K3/(1+g1)`.
- `Book₀=NI₀(1+g1)/ROE1`.
- For `ROE1≠0`, `P/B₀=K3·ROE1/(1+g1)`.
- For singular earnings normalization, calculate direct `K_PB` and `Equity Value=K_PB×Book₀`.

### CORE INVARIANTS

- `ROE_T=Ke2`.
- `P/B_T=1`.
- `TV=Book_T`.
- `g_T` is only the fade endpoint.
- IF `ROE1=Ke1`, `ROE2=Ke2`, structure is constant and cash/recap are zero, THEN `P/B₀=1`, forward P/L `=1/Ke1`, trailing P/L `=(1+g1)/Ke1`.
- Year `n1+1` is F2 and uses Ke2 after `n1` years at Ke1.
- IF `GDE2·rz=GDE1`, THEN bridge `=0`.
- IF `F=0`, THEN fade dividends `=0` and `V_fade=pref_fade`.
- IF `n1=0`, THEN `V_F1=0`, F1 inputs still scale later blocks and `K3∝(1+g1)`.
- IF `n2=0`, THEN `V_F2=0` and fade starts directly at the boundary.
- IF `ROE1=0`, THEN use direct P/B; IF `ROE2=0`, THEN use `A2_cancelled`. Literal K3 is singular at both paths.

### KE, COUNTRY RISK AND HURDLE

- `Ke=default-free risk-free in valuation currency + bottom-up beta×mature-market ERP + λ_company×CRP`.
- Do not embed the same country risk in risk-free, ERP and CRP.
- Material discrete failure is scenario-weighted outside K3, not hidden only in Ke.
- Hurdle mode output: `Hurdle-conditioned Equity Value` or `Required-return scenario value`; never fair value or pure target IRR.

### FUNDING, DISTRESS AND STRUCTURE

- Negative distribution is funding already deducted through FCFE. Do not add a generic dilution haircut or future funding shares to the denominator.
- Fair-value issuance preserves old-holder value per original share.
- `Probability-weighted Equity Value=Σp_s×Equity Value_s`; probabilities sum to 100%, recovery may be zero, and the blend is not K3.
- `GDE−NDE=Cash/Equity`; `GDE<NDE` is invalid under canonical definitions.
- Calibration diagnostic only: `ROE=ROIC×(1+NDE)−kd_at×GDE`; debt-financed zero-yield cash depresses ROE.

### CAP / FADE

- `n2` = years of full `ROE2−Ke2` spread.
- `F` = years for the spread to converge after erosion begins.
- Use competitive evidence and review priors; never count moat factors mechanically.
- Historical `10–15` aggregate and `0–2` to `>20` company CAP observations are priors, not cutoffs.
- MICAP belongs only to labelled reverse valuation.

### BASE REGRESSION ANCHORS

- Blocks: `0.447777 + 26.531889 − 2.500601 + 12.086824 = 36.565889`.
- Fade split: `6.169100 dividends + 5.917724 terminal book`.
- High-impact local partials: `n1+1 −7.91%`; `n2+1 +5.43%`; `F+1 +2.57%`; `ROE1+1pp −7.54%`; `g2+1pp +4.95%`; `Ke2−50bps +4.07%`; `GDE2+10pp +6.72%`; `NDE2+10pp −12.75%`.
- These are case-base pure partials, never universal economic rules.

### WORKFLOW

`Normalize → ROE1 → g1 → n1 → ROE2 → g2 → n2 → F → Ke/country risk → GDE/NDE/cash carry → Kd/t → g_T → K3 or companion blocks → full regressions → distress blend if material → current-holder output → market comparison → reverse optional`

### RED FLAGS

- Revenue CAGR copied into g.
- Raw accounting ROE used without normalization.
- ROE2 held fixed after leverage changes.
- n2 selected to match price.
- F used as a plug.
- Ke2 reduced without real de-risking.
- GDE/NDE divided by market capitalization.
- `g_T` treated as perpetual growth.
- Bridge omitted or first F2 year discounted at Ke1.
- External equity rejected automatically.
- Negative FCFE followed by a dilution haircut or future funding shares added again.
- Material discrete failure hidden only in Ke.
- Country risk counted twice.
- `n1=0` treated as making F1 inputs irrelevant.
- Literal K3 used at `ROE1=0` or `ROE2=0`.
- `GDE<NDE` accepted as ordinary structure.
- P/L interpreted with `NI₀<0`.
- `K3×0` used with `NI₀=0`.

### OUTPUT DISCIPLINE

- Report Equity Value when `NI₀≤0` or P/L is not economically interpretable.
- Label the direct P/B, probability-weighted and hurdle-conditioned outputs explicitly.
- Use only current diluted shares at t=0 for the standard per-share output; do not add future fair-value funding shares.
- Report block decomposition when explaining the thesis.
- Label every reverse valuation.
- Compare market price only after inputs are frozen.


[D01]: https://pages.stern.nyu.edu/~adamodar/New_Home_Page/valquestions/growth.htm
[D02]: https://pages.stern.nyu.edu/~adamodar/New_Home_Page/littlebook/growthrates.htm
[D03]: https://pages.stern.nyu.edu/~adamodar/New_Home_Page/valquestions/termvalueexreturns.htm
[D04]: https://pages.stern.nyu.edu/~adamodar/New_Home_Page/valquestions/highgrowthperiod.htm
[D05]: https://pages.stern.nyu.edu/~adamodar/pdfiles/eqnotes/cap.pdf
[D06]: https://pages.stern.nyu.edu/~adamodar/New_Home_Page/littlebook/discountrates.htm
[D07]: https://pages.stern.nyu.edu/~adamodar/New_Home_Page/TenQs/TenQsBottomupBetas.htm
[D08]: https://pages.stern.nyu.edu/~adamodar/New_Home_Page/valquestions/CountryRisk.htm
[D09]: https://pages.stern.nyu.edu/~adamodar/pdfiles/papers/returnmeasures.pdf
[D10]: https://pages.stern.nyu.edu/~adamodar/New_Home_Page/littlebook/younggrowthvaluedrivers.htm
[D11]: https://pages.stern.nyu.edu/~adamodar/New_Home_Page/littlebook/maturevaluedrivers.htm
[D12]: https://pages.stern.nyu.edu/~adamodar/New_Home_Page/littlebook/decliningvaluedrivers.htm
[D13]: https://pages.stern.nyu.edu/~adamodar/New_Home_Page/valquestions/distresspaper.htm
[D14]: https://pages.stern.nyu.edu/~adamodar/New_Home_Page/littlebook/financialsvccompanies.htm
[D15]: https://pages.stern.nyu.edu/~adamodar/New_Home_Page/littlebook/bankvaluedriver.htm
[D16]: https://pages.stern.nyu.edu/~adamodar/pdfiles/papers/finfirm09.pdf
[D17]: https://pages.stern.nyu.edu/~adamodar/New_Home_Page/littlebook/commodityvaluedrivers.htm
[D18]: https://pages.stern.nyu.edu/~adamodar/New_Home_Page/littlebook/intangiblevaluedriver.htm
[D19]: https://pages.stern.nyu.edu/~adamodar/New_Home_Page/valquestions/termvalapproaches.htm
[D20]: https://pages.stern.nyu.edu/~adamodar/pdfiles/execval/valenhX.pdf
