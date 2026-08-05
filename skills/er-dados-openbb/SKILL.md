---
name: er-dados-openbb
description: USE QUANDO coletar dados financeiros para uma análise via OpenBB, validar cobertura de endpoints/providers, registrar proveniência no ledger ou classificar gaps de dados (MATERIAL/NÃO-MATERIAL). NÃO use para análise, calibração de inputs ou relatório (er-analise, er-motor-k3, er-relatorio-html).
---

# er-dados-openbb — Doutrina de coleta OpenBB (Data Manager)

## Papel

O **Data Manager é o único dono das chamadas OpenBB** do fleet. Exceção única: o snapshot de
perfil/preço/market cap do briefing (F1), feito pelo Analista com uma chamada. Todo o resto —
demonstrações, séries de preço, dividendos, estimates, ownership, setoriais, pares — passa pelo
DM, que coleta, salva, registra proveniência e classifica gaps. O DM **não interpreta, não
calibra e não escreve análise**: entrega dados com proveniência.

## Regras duras

1. **Dados financeiros SÓ OpenBB** (`mcp__openbb-mcp__*`). **Sem fallback de web scraping**, sem
   copiar número de site, sem memória de treino como fonte. Indisponível no OpenBB = gap
   declarado, nunca substituído por outra fonte.
2. **Qualitativo NÃO é do DM**: segmentos/geografia, RI, notícias interpretadas, teses — pesquisa
   livre do Analista. O DM pode coletar `news_company` como matéria-prima, sem interpretar.
3. **`provider` explícito em toda chamada e todo registro** (hoje: `yfinance` sem chave, `sec` só
   US; fmp/intrinio/tiingo SEM chave nesta máquina). Se uma chave for configurada depois,
   troca-se o provider **sem refactor** — ver `references/endpoints.md`.
4. **Nunca inventar, nunca silenciar**: todo dado tem proveniência no ledger; toda ausência tem a
   chamada real que a sustenta (anti-cascata — ver `references/ledger-e-gaps.md`).
5. **Preço >24h útil = VENCIDO** → recoletar antes de qualquer uso.

## Fluxo de coleta (F4 e re-coleta de P2)

1. **Receber o brief** do Analista: ponteiros para `00_briefing.md` e `01_grill_me.md` do
   workspace + lista de dados por categoria.
2. **Validar cobertura**: conferir em `references/endpoints.md` tool/provider por categoria;
   B3 usa sufixo `.SA`; o que estiver "a confirmar na coleta" é testado com chamada real.
3. **Coletar** categoria a categoria, com `provider` explícito e parâmetros registrados.
4. **Salvar** em `analises/<TICKER>/dados/` (formato abaixo).
5. **Escrever o ledger** (`dados/ledger.md`): proveniência completa — arquivo, endpoint,
   parâmetros, provider, data/hora (com fuso), moeda, janela obtida, gaps.
6. **Reportar ao Analista**: contagem de arquivos, janelas obtidas e gaps classificados
   **MATERIAL** (bloqueia input crítico do valuation ou a escala → o Analista pergunta ao
   usuário) ou **NÃO-MATERIAL** (degrada gráfico/contexto, incluindo horizonte curto de
   fundamentals → nota de limitação e segue).

## Formato dos arquivos em `analises/<TICKER>/dados/`

**Um arquivo JSON por categoria, nome fixo:**

| Categoria | Arquivo |
|---|---|
| Demonstrações (DRE, balanço, fluxo de caixa) | `demonstracoes.json` |
| Preço e múltiplos | `precos.json` |
| EPS histórico (extraído da DRE) | `eps.json` |
| Dividendos, splits e buybacks | `dividendos.json` |
| Estimates e consenso | `estimates.json` |
| Ownership e insiders | `ownership.json` |
| Setoriais, commodities e macro | `setoriais.json` |
| Pares (screener + coleta individual) | `pares.json` |

(Segmentos/geografia não têm arquivo: categoria fora do domínio do DM — qualitativo do Analista.)

**Payload** = resposta OpenBB relevante + bloco `meta` obrigatório:

```json
{
  "meta": {
    "endpoint": "equity_fundamental_income",
    "params": {"symbol": "PETR4.SA", "period": "annual", "limit": 10},
    "provider": "yfinance",
    "data_chamada": "2026-08-05T14:32:00-03:00",
    "moeda": "BRL",
    "janela_obtida": "FY2021–FY2025"
  },
  "dados": [ ... ]
}
```

Categorias com várias tools (ex.: demonstrações = income+balance+cash) agrupam um bloco
`meta` + `dados` por endpoint dentro do mesmo arquivo.

## Proatividade

O DM **sugere séries úteis não pedidas** quando o perfil da empresa indicar: commodity do perfil
(ex.: petróleo para petroleira), câmbio relevante, índice de referência, estimates disponíveis.
Toda sugestão é registrada em `dados/pedidos.md` (sugestão → decisão do Analista); coleta só
após aceite, ou junto do lote quando o custo for trivial — sempre registrada.

## Iteração com o Analista

Pedidos adicionais (F6, P2) e respostas passam por `dados/pedidos.md`: log cronológico
pedido → resposta (formato em `references/ledger-e-gaps.md`). O ledger é atualizado a cada
coleta nova; nunca sobrescrever entradas antigas — apensar.

## Referências

- `references/endpoints.md` — mapa por categoria: tool, providers possíveis, provider utilizável
  hoje, parâmetros, janela observada, gap típico e mitigação (validado 2026-08-05).
- `references/ledger-e-gaps.md` — formato do ledger e de pedidos.md, validade de preço (24h útil),
  anti-cascata, classificação MATERIAL/NÃO-MATERIAL.
