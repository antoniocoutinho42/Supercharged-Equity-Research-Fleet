# Ledger de proveniência e classificação de gaps

Princípio: **nunca inventar, nunca silenciar.** Todo dado salvo tem proveniência registrada;
todo dado ausente tem gap classificado e a chamada real que comprova a ausência.

## `dados/ledger.md` — formato

Uma linha por arquivo salvo (ou por tentativa que resultou em gap):

```markdown
| arquivo | endpoint | parâmetros | provider | data/hora da chamada | janela obtida | gaps |
|---|---|---|---|---|---|---|
| demonstracoes.json | equity_fundamental_income (+balance, cash) | symbol=PETR4.SA, period=annual, limit=10 | yfinance | 2026-08-05 14:32 BRT | FY2021–FY2025 (5a) | NÃO-MATERIAL: janela < 10a; nota de horizonte nos gráficos |
| precos.json | equity_price_historical | symbol=PETR4.SA, interval=1M, start_date=2010-01-01 | yfinance | 2026-08-05 14:35 BRT | 2010-01 → 2026-08 | — |
```

Regras do ledger:

- **Moeda e fuso**: registrar a moeda dos valores (ex.: BRL para `.SA`) e a data/hora da chamada
  com fuso. Sem isso a proveniência é incompleta.
- **Provider sempre explícito** — é o que permite trocar de provider depois (chave nova) sem refactor.
- **Janela obtida = janela observada na resposta**, nunca a janela pedida.
- Cada gap na coluna final leva a classificação (`MATERIAL` / `NÃO-MATERIAL`) e a mitigação em uma frase.

## `dados/pedidos.md` — formato

Log cronológico da iteração Analista ↔ Data Manager. Uma entrada por pedido ou sugestão:

```markdown
## 2026-08-05 — Pedido do Analista
- Pedido: série de preço do Brent para contexto do perfil commodity.
- Resposta do DM: coletado em setoriais.json (commodity_price_spot); janela X–Y; sem gaps.

## 2026-08-05 — Sugestão do DM (proatividade)
- Sugestão: estimates de consenso disponíveis para o ticker, não pedidos.
- Decisão do Analista: aceitar → estimates.json.
```

## Validade de preço

Preço/quote com mais de **24h úteis** desde a chamada registrada no ledger = **VENCIDO** →
recoletar antes de qualquer uso a jusante (engine, relatório). A data/hora do ledger é a
referência; nunca reutilizar preço vencido em silêncio.

## Anti-cascata

**Nenhum "indisponível" sem a chamada que o sustenta; nunca herdar ausência.**

- Só declare um dado indisponível depois de uma chamada real (nesta sessão de coleta) com o erro
  ou resposta vazia registrado no ledger.
- Nunca propagar indisponibilidade de outra sessão, de outro ticker, de outro provider ou de
  memória: a cobertura muda (chaves novas, tickers diferentes) — re-testar sempre.
- Falha de um endpoint NÃO implica falha da categoria: tentar as alternativas mapeadas em
  `endpoints.md` antes de declarar gap.

## Classificação de gaps

| Classe | Critério | Ação |
|---|---|---|
| **MATERIAL** | Bloqueia input crítico do valuation ou a escala (NI0/Book0, preço, ações diluídas, estrutura de capital) | O DM reporta; o **Analista pergunta ao usuário**, que pode fornecer o dado manualmente |
| **NÃO-MATERIAL** | Degrada gráfico ou contexto — **incluindo horizonte curto de fundamentals** (janela ~4–5a quando o desenho pede 10a) | Nota de limitação no ledger (e depois na seção "Limitações" do relatório) e **segue** — nunca pergunta, nunca bloqueia |

Regras de aplicação:

- Horizonte curto de demonstrações/EPS é **sempre NÃO-MATERIAL** (limitação estrutural do
  provider sem chave; correção 9): gráficos usam a "janela máxima disponível" com a janela
  efetiva + nota exibidas.
- Classificação é do DM no ledger; a decisão de perguntar ao usuário (gap MATERIAL) é do Analista.
- Dado parcial ≠ dado ausente: salvar o que veio, declarar o corte.
