---
description: Anexo financeiro histórico (resultado, balanço, fluxo de caixa e métricas) para entender evolução e ciclo
argument-hint: "[ticker ou pasta da análise] [janela opcional] [destino: separado | no relatório]"
---

Carregue `er-analise` em modo de histórico financeiro e leia `references/historico-financeiro.md`. Alvo: $ARGUMENTS

Se a pasta da análise existir, reutilize `historico/`, as definições de capital do `valuation/valuation-case.md` e as fontes já verificadas, conferindo atualidade. Caso contrário, reconstrua a série do zero pela ordem de fontes da referência.

Entregue um HTML autocontido (skill `relatorio-html`) com demonstrações, métricas, indicadores operacionais, notas de comparabilidade, definições e fontes, separado ou como aba final do `relatorio.html` quando pedido. Planilha só a pedido. Rode `verificador` sobre os números-âncora e, quando houver relatório, sobre a reconciliação com ele.

Este comando não dispara initiating coverage nem valuation. Se a série revelar inflexões que mudariam uma tese existente, registre-as e avise o usuário.
