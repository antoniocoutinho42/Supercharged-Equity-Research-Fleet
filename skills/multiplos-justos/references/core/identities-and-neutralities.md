# Identidades e neutralidades qualificadas

> Núcleo preservado da v10.1. As neutralidades só valem com os qualificadores abaixo.

# Múltiplos Justos — o múltiplo como output de um DCF

Sob premissas estáveis o DCF colapsa numa fórmula fechada de poucas variáveis, e o múltiplo justo
sai delas. Derivado e provado na planilha do usuário (checks algébricos = 0). **Versão v10.1.** Histórico completo de versões e a proveniência de cada regra: `CHANGELOG.md`.

**Identidade central:** g = RiR × ROIC (RiR = taxa de reinvestimento; é a 'value driver formula' de Copeland/McKinsey) ⟹ **FCFF = NOPAT × (1 − g/ROIC)**
**Ponte EBITDA:** EV/EBITDA = EV/NOPAT × (1−d)(1−t), d = D&A % EBITDA, t = alíquota
**Equity:** nas convenções FCFE (`gordon`/`convergencia`), FCFE = LL × [(1 − g/ROE) + (GD/E − ND/E)·(g/ROE)]. Na `book`, clean surplus exige **Div = LL × (1−g/ROE)** + patrimônio terminal E_n; somar Δcaixa e depois E_n duplicaria caixa. GD/E − ND/E = caixa/equity.
**Drivers de valor:** só rentabilidade acima do custo de capital e o crescimento que expõe capital
novo a esse spread.

**Neutralidades — nunca cite sem o qualificador:**

| Neutralidade | Vale quando | Quebra quando |
|---|---|---|
| ROIC=WACC ⟹ fwd = 1/W [identidade] | `convergencia`/`gordon` com marginal=W; `book` com marginal **E** book = W | `book` com book≠W (o diagnóstico avisa); o corrente varia com g por reajuste de base — não é criação de valor |
| g=0 ⟹ invariante à rentabilidade marginal | `gordon`/`convergencia`, ou n→∞ | `book` com CAP finito continua dependente da âncora média inicial: TV = 1/(ROIC_book(1+W)ⁿ) (W 7%, n 10: 23,97x a book 3% vs 8,04x a 50%) |
| sinal ∂múltiplo/∂g = sinal do spread | só na base **forward** | base corrente |
| ROE=Ke neutro (equity) | `book`: ROE marginal **e** book = Ke, independentemente de caixa/E; `gordon`/`convergencia`: caixa/E = 0 | na `book`, Caixa/E é neutro porque o valuation é Div + E_n; nas convenções FCFE, caixa proporcional pode alterar o P/L mesmo sem spread; no `gordon` a política vale no terminal por default — `--politica-tv continua|encerra` move 2–6% do P/L |
