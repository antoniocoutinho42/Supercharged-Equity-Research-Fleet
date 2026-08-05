# Mapa de endpoints OpenBB por categoria (F4)

Mapa validado com chamadas reais nesta máquina em 2026-08-05. O que não foi chamado está marcado
**"a confirmar na coleta"** — nunca afirme cobertura que não foi observada.

## Regras transversais

1. **`provider` é parâmetro OBRIGATÓRIO** em quase todas as tools. Sempre passe explicitamente.
2. **Chaves configuradas nesta máquina: NENHUMA.** Chamada com `provider=fmp` sem chave retorna o
   erro literal: `Missing credential 'fmp_api_key'` (intrinio/tiingo falham de forma análoga).
   Nunca nomeie um provider pago como se estivesse ativo.
3. **Providers utilizáveis HOJE:** `yfinance` (default de fato, sem chave, cobre B3) e `sec`
   (US apenas, sem chave, só demonstrações/filings).
4. **Parametrize `provider` em toda chamada e no ledger**: se uma chave (fmp/intrinio/tiingo) for
   configurada depois, troca-se o provider **sem refactor** — o mapa abaixo já lista os
   providers possíveis de cada tool.
5. **B3 = sufixo `.SA`** no yfinance (ex.: `PETR4.SA`). `sec` não cobre B3.
6. **Moeda e fuso**: yfinance retorna valores na moeda da listagem (`.SA` → BRL). Registrar
   moeda e data/hora da chamada no ledger (ver `ledger-e-gaps.md`).
7. **Prefixo real das tools nesta máquina**: `mcp__openbb-mcp__<rota_com_underscores>`
   (ex.: `mcp__openbb-mcp__equity_fundamental_income`).

## 1. Demonstrações (DRE, balanço, fluxo de caixa) → `demonstracoes.json`

| Tool | Providers possíveis | Utilizável hoje | Parâmetros típicos | Janela observada | Gap típico → mitigação |
|---|---|---|---|---|---|
| `equity_fundamental_income` | fmp, intrinio, sec, yfinance | yfinance (sec p/ US) | `symbol=PETR4.SA, provider=yfinance, period=annual, limit=5` | ~4–5 anos anuais (verificado AAPL: FY2023–FY2025 com `period=annual, limit=3`) | Horizonte curto vs "10 anos" → **NÃO-MATERIAL**: nota de janela efetiva no ledger e no gráfico |
| `equity_fundamental_balance` | fmp, intrinio, sec, yfinance | yfinance (sec p/ US) | idem | ~4–5 anos anuais | idem |
| `equity_fundamental_cash` | fmp, intrinio, sec, yfinance | yfinance (sec p/ US) | idem | ~4–5 anos anuais | idem |

Campos ricos verificados na DRE yfinance: `basic/diluted_earnings_per_share`,
`weighted_average_diluted_shares_outstanding`, `ebitda`, `tax_rate_for_calcs`.
A janela curta de fundamentals é **limitação estrutural** do provider sem chave: gap
NÃO-MATERIAL de horizonte (correção 9 do plano) — declarar, nunca bloquear.

## 2. Preço e múltiplos → `precos.json`

| Tool | Providers possíveis | Utilizável hoje | Parâmetros típicos | Janela observada | Gap típico → mitigação |
|---|---|---|---|---|---|
| `equity_price_historical` | fmp, intrinio, tiingo, yfinance | yfinance | `symbol, provider=yfinance, interval=1d\|1M, start_date, end_date` | LONGA (verificado PETR4.SA mensal desde 2010; traz coluna `dividend`) | — |
| `equity_price_quote` | fmp, intrinio, yfinance | yfinance | `symbol, provider=yfinance` | snapshot | Validade >24h útil = VENCIDO → recoletar |
| `equity_profile` | fmp, intrinio, yfinance | yfinance | `symbol, provider=yfinance` | snapshot (verificado PETR4.SA: nome, setor, market cap, shares_outstanding, beta, dividend_yield, descrição) | — |
| `equity_fundamental_metrics` | fmp, intrinio, yfinance | yfinance **a confirmar na coleta** (campos/janela) | `symbol, provider=yfinance` | a confirmar na coleta | — |
| `equity_historical_market_cap` | a confirmar na coleta | a confirmar na coleta | `symbol` | a confirmar na coleta | — |
| `equity_fundamental_ratios` | fmp, intrinio | **INDISPONÍVEL** (sem chave) | — | — | Ratios/múltiplos **derivam das demonstrações** — trabalho do Analista, não do DM |

P/L histórico: sem tool utilizável de ratio pronta — o Analista deriva de preço
(`equity_price_historical`, longa) ÷ EPS da DRE (~4–5a); a janela derivada é limitada pelo
EPS → declarar o corte (NÃO-MATERIAL).

## 3. EPS histórico → `eps.json`

| Tool | Providers possíveis | Utilizável hoje | Parâmetros típicos | Janela observada | Gap típico → mitigação |
|---|---|---|---|---|---|
| `equity_fundamental_historical_eps` | fmp | **INDISPONÍVEL** (sem chave) | — | — | EPS sai da DRE yfinance: `basic/diluted_earnings_per_share` e `weighted_average_diluted_shares_outstanding` (categoria 1); janela ~4–5a → **declarar o corte** (NÃO-MATERIAL) |

`eps.json` é construído a partir de `demonstracoes.json` (extração, sem cálculo de valuation),
com `meta` apontando o endpoint de origem.

## 4. Dividendos, splits e buybacks → `dividendos.json`

| Tool | Providers possíveis | Utilizável hoje | Parâmetros típicos | Janela observada | Gap típico → mitigação |
|---|---|---|---|---|---|
| `equity_fundamental_dividends` | fmp, intrinio, yfinance | yfinance | `symbol, provider=yfinance` | LONGA (verificado PETR4.SA desde 2005) | — |
| `equity_fundamental_historical_splits` | a confirmar na coleta | a confirmar na coleta | `symbol` | a confirmar na coleta | — |
| `equity_fundamental_trailing_dividend_yield` | a confirmar na coleta | a confirmar na coleta | `symbol` | a confirmar na coleta | — |

Buybacks: sem série dedicada verificada → derivar da variação de
`weighted_average_diluted_shares_outstanding` (DRE) e/ou `equity_ownership_share_statistics`
(a confirmar na coleta); derivação declarada no ledger (NÃO-MATERIAL).

## 5. Estimates e consenso → `estimates.json`

| Tool | Providers possíveis | Utilizável hoje | Parâmetros típicos | Janela observada | Gap típico → mitigação |
|---|---|---|---|---|---|
| `equity_estimates_consensus` | fmp, intrinio, yfinance | yfinance | `symbol, provider=yfinance` | snapshot (verificado PETR4.SA: target high/low/consensus/median, recommendation, number_of_analysts, current_price em BRL) | Cobertura de analistas varia por ticker → NÃO-MATERIAL |
| `equity_estimates_price_target` | a confirmar na coleta | a confirmar na coleta | `symbol` | a confirmar na coleta | — |
| `equity_estimates_forward_eps` | a confirmar na coleta | a confirmar na coleta | `symbol` | a confirmar na coleta | — |
| `equity_estimates_forward_pe` | a confirmar na coleta | a confirmar na coleta | `symbol` | a confirmar na coleta | — |

## 6. Ownership e insiders → `ownership.json`

| Tool | Providers possíveis | Utilizável hoje | Parâmetros típicos | Janela observada | Gap típico → mitigação |
|---|---|---|---|---|---|
| `equity_ownership_major_holders` | a confirmar na coleta | a confirmar na coleta | `symbol` | a confirmar na coleta | Cobertura B3 incerta → se ausente após chamada real, NÃO-MATERIAL (contexto) |
| `equity_ownership_share_statistics` | a confirmar na coleta | a confirmar na coleta | `symbol` | a confirmar na coleta | idem |
| `equity_ownership_insider_trading` | a confirmar na coleta | a confirmar na coleta | `symbol` | a confirmar na coleta | idem |
| `equity_ownership_institutional` | a confirmar na coleta | a confirmar na coleta | `symbol` | a confirmar na coleta | idem |

## 7. Segmentos e geografia → SEM arquivo (fora do domínio do DM)

| Tool | Providers possíveis | Utilizável hoje | Mitigação |
|---|---|---|---|
| `equity_fundamental_revenue_per_segment` | fmp | **INDISPONÍVEL** (sem chave) | Segmentos/geografia viram **pesquisa qualitativa livre do Analista** (RI, filings) — fica FORA do domínio do DM; o DM apenas registra a indisponibilidade no ledger |

## 8. Setoriais, commodities e macro → `setoriais.json`

Existência confirmada no servidor; **provider a confirmar na coleta** em todas:

| Tool | Uso típico |
|---|---|
| `commodity_price_spot` | série da commodity do perfil (ex.: petróleo p/ PETR4) |
| `economy_fred_series` | séries macro/setoriais FRED |
| `economy_cpi`, `economy_interest_rates` | inflação e juros para contexto |
| `index_price_historical` | índice de referência (benchmark) |
| `currency_price_historical`, `currency_snapshots` | câmbio (ex.: BRL/USD) |
| `news_company` | notícias da companhia (contexto; interpretação é do Analista) |

## 9. Pares → `pares.json`

| Tool | Providers possíveis | Utilizável hoje | Mitigação |
|---|---|---|---|
| `equity_compare_peers` | fmp | **INDISPONÍVEL** (sem chave) | Lista de pares vem de `equity_screener` (provider a confirmar na coleta) + conhecimento do Analista; depois **coleta individual por ticker** (categorias 1, 2 e 5) para cada par |
| `equity_screener` | a confirmar na coleta | a confirmar na coleta | — |
| `equity_search` | a confirmar na coleta | a confirmar na coleta | resolver tickers/listagens |
