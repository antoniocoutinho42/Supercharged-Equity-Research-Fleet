# Backlog do engine — v3.4 (registrado no fechamento da v3.3.0, 2026-07-28)

Itens acordados no release v2.2.0 do plugin (engine v3.3.0). Nenhum é bug: são
extensões de cobertura e monitoramento.

1. **Fixture golden com bloco operacional** (recomendação do code review da v3.3.0):
   congelar um `golden_v33_sintetico_op.json` com `premissas.operacional` completo
   (incl. `kd_pre_imposto`) para que a aditividade byte-a-byte de `ebit_justo`,
   `paridade_decomposta` e `ke_alavancagem` fique coberta por REGRESSÃO, não só por
   gating de presença — hoje o golden VRSK não exercita o bloco operacional (H0b).
2. **Monitorar a frequência de `DECOMPOSICAO_POUCO_INFORMATIVA`** nas primeiras
   análises reais com bloco operacional: se o warning disparar com frequência
   (interação estrutural ROIC-vs-ROE dominando a decomposição), reavaliar o limiar de
   25% (`PARIDADE_INTERACAO_LIMIAR_PCT`) ou refinar a decomposição (ex.: cunha
   estrutural separada). Registrar cada ocorrência no valuation.md da análise.
