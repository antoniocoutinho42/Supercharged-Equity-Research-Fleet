---
name: er-relatorio-html
description: >-
  USE QUANDO for gerar, regenerar ou validar o relatório HTML interativo de uma análise do fleet
  (F10): montar o arquivo de 2 abas via build_report.py, preparar o analise.json da aba 2, checar
  consistência com checar_relatorio.py, ou diagnosticar banner de paridade. NÃO use para rodar o
  valuation (er-motor-k3), coletar dados (er-dados-openbb) nem para o workflow da análise
  (er-analise).
---

# er-relatorio-html — builder determinístico do relatório de 2 abas

REGRA CENTRAL: o relatório é MONTADO POR CÓDIGO, nunca escrito ou editado à mão. `build_report.py`
é o ÚNICO caminho de emissão; editar o HTML gerado é PROIBIDO (o `checar_relatorio.py` detecta).
Toda a matemática vem do engine Python (er-motor-k3) e do espelho `assets/k3_engine.js` — copiado
verificado, jamais editado. PROIBIDO escrever qualquer matemática de valuation em JS novo
(`charts.js` só desenha; o template só formata).

## 1. Comandos

```bash
python skills/er-relatorio-html/build_report.py analises/<TICKER>            # modo completo
python skills/er-relatorio-html/build_report.py analises/<TICKER> --modo valuation
python skills/er-relatorio-html/checar_relatorio.py analises/<TICKER>        # QC pós-emissão
```

Entradas no namespace: `case.json` (schema do er-motor-k3), `analise.json` (aba 2, contrato
abaixo), `dados/*.json` (fonte das séries). Saídas: `saida/results.json` (engine, fonte de
verdade), `saida/market_implied.json` (diagnóstico reverso, auditável) e
`relatorio/relatorio_<TICKER>.html` (autocontido, zero rede).

## 2. Recusas do builder (nada é emitido)

1. Suíte canônica de regressão falhou (SUITE PASS obrigatório; `--skip-regressions` só em debug).
2. `engine_fingerprint_ok == False`.
3. Espelho JS divergiu do Python na pré-verificação sob node (com node ausente, o self-test do
   browser cobre no load — banner verde obrigatório na entrega).
4. Placeholder de número não resolvível.
5. Carregamento externo de recurso (autocontenção; `<a href>` de citação é permitido).

## 3. Contrato do analise.json (aba 2 — conteúdo do Analista)

Campos (todos opcionais, mas o modo completo exige o conjunto que a Seção 8 do desenho pede):
`positives` / `negatives` (listas de strings), `header.sintese` (1 linha do cabeçalho),
`sumario_html`, `perfil_html`, `qualitativa_html`, `financeira_html`, `calibracao_racional_html`,
`riscos_html`, `market_pricing_html`, `limitacoes_html`, `fontes_html` (fragmentos HTML),
`charts` (specs abaixo), `market_implied_params` (default `["ROE2","g2","Ke2","n2"]`),
`implied_interpretations` (por param), `sensitivity_presets` (2D), `sensitivity_default`,
`default_scenario`.

**Números em prosa**: todo número de valuation citado nos fragmentos DEVE usar placeholder —

- `{{r:<chave>|<fmt>}}` → `saida/results.json` (ex.: `{{r:scenarios.base.value_per_share|2}}`)
- `{{c:<chave>|<fmt>}}` → `case.json` (ex.: `{{c:market.price_per_share|2}}`)
- `{{d:<arquivo>:<chave>|<fmt>}}` → `dados/<arquivo>` (ex.: `{{d:precos.json:results.-1.close|2}}`)
- `{{m:<PARAM>.implied|<fmt>}}` → `saida/market_implied.json`, `params.<PARAM>.implied`
- `{{m:<PARAM>.base_value|<fmt>}}` → idem, valor base do Analista no diagnóstico reverso
- `{{m:<PARAM>.nearest_value|<fmt>}}` / `{{m:<PARAM>.nearest_metric|<fmt>}}` → param inteiro sem
  solução exata (n2): valor mais próximo e a métrica que ele atinge

Formatos: `2` (decimais), `pct1` (percentual), `x` (múltiplo). O builder resolve, registra no log
de consistência embutido e RECUSA placeholder órfão (param inexistente ou campo nulo inclusive).

**Market-implied em prosa**: o diagnóstico reverso é calculado uma única vez pelo builder,
persistido em `saida/market_implied.json` (a mesma fonte da tabela market-implied da aba 1) e
re-resolvido pelo `checar_relatorio.py`. Todo valor market-implied citado em prosa DEVE usar o
namespace `m:` — `num-livre` NÃO é aceitável para ele.

Número livre legítimo (ano, fato qualitativo com fonte própria) → envolva em
`<span class="num-livre">…</span>`; o checar não o audita, mas exige a marcação.

## 4. Spec de gráfico (`charts[]`)

```json
{"id": "roe", "titulo": "ROE — janela disponível", "tipo": "line|bars", "unidade": "%|x|BRL",
 "x": [2021, 2022], "x_tempo": false,
 "series": [{"label": "ROE", "y": [0.18, 0.21], "fonte": "dados/demonstracoes.json",
             "derivacao": "derivada", "formula_nota": "NI_t / Equity_(t-1) (DuPont em financeira.md)"}],
 "overlays": [{"label": "ROE1 assumido (base)", "valor": 0.185, "fonte_chave": "case:scenarios.base.inputs.ROE1"}],
 "nota_janela": "Janela efetiva 2021–2025 (OpenBB/yfinance); pedido: 10 anos — gap NÃO-MATERIAL declarado no ledger.",
 "caption": "..."}
```

Regras: `derivacao: "direta"` = valores conferíveis 1:1 no arquivo de `fonte` (o checar confere
numericamente); `"derivada"` = série calculada de dados/ (DuPont etc.) — exige `formula_nota`
exibida no gráfico. Overlays de premissas SEMPRE com `fonte_chave` (`case:` ou `results:` +
chave pontilhada; o checar confere o valor). Série incompleta NUNCA bloqueia: renderiza a janela
máxima disponível com `nota_janela` no próprio gráfico (gap NÃO-MATERIAL); série ausente vira
nota de degradação visível.

**Gráficos obrigatórios do modo completo** (âncora de realidade das premissas): 1. ROE histórico
(+ indicadores do caso) com overlays ROE1/ROE2; 2. EPS com CAGR; 3. endividamento; 4. P/L
histórico com overlay do K3 justo base; 5. crescimento por ano + CAGR acumulado com overlays
g1/g2; 6. específicos do perfil (a critério do Analista, F3).

## 5. As 2 abas

Cabeçalho comum: empresa/ticker, data da análise, preço usado (data + fonte), síntese de 1 linha,
KPIs (fair value base/ação, faixa bear–bull, upside, K3; hurdle-conditioned rotulado quando
houver) e badge de paridade. **Aba 1 — Valuation** (só template + engine, sem conteúdo do
Analista além do case): cenários com inputs editáveis (original vs modificado + reset), recálculo
ao vivo, bridge de blocos, resumo de cenários, sensibilidade 1D ao vivo + 2D pré-computada,
market-implied, comparação com preço. **Aba 2 — Análise** (ordem fixa da Seção 8 do desenho):
Positives/Negatives → sumário executivo → perfil/qualitativa → financeira histórica (gráficos) →
calibração 16×cenários + racional → riscos → What Is the Market Pricing? → limitações de dados e
fontes. Modo `valuation`: aba 2 reduzida a premissas/racional + limitações.

## 6. Limitações declaradas

- Sem node no PATH, a divergência de espelho só aparece no load do browser (banner vermelho
  desativa a edição); a entrega continua condicionada ao banner VERDE.
- O checar não audita semântica de prosa: número sem placeholder e sem `num-livre` é violação,
  mas um placeholder da chave errada (valor certo de outra grandeza) é responsabilidade do
  Analista — revisar a aba 2 antes da entrega.

## Referências

- `build_report.py`: builder (docstring = contrato completo de CLI e recusas).
- `checar_relatorio.py`: QC pós-emissão (exit 0 limpo; lista violações).
- `assets/template_relatorio.html`: template de 2 abas (placeholders `__*__`).
- `assets/k3_engine.js`: espelho JS verificado (INTOCÁVEL; sha no manifest do er-motor-k3).
- `assets/charts.js` + `assets/uPlot.iife.min.js` (v1.6.27, MIT): gráficos, zero rede.
