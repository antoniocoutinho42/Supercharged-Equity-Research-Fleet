# Casos de aceitação da v6.1

Este arquivo não é carregado durante uma análise. Serve para comparar a v6.1 com a v6 sob condições equivalentes: mesmos documentos, mesma data-base, orçamento comparável.

## Método

1. Antes de rodar, escreva um **gabarito oculto** por caso: os fatos, direitos, riscos e mecanismos que uma análise excelente precisa encontrar. Mantenha o gabarito fora do repositório e fora do contexto do Fleet.
2. Rode o Fleet sem pistas.
3. Meça: recall do gabarito; rubrica do `revisor-comite` em contexto limpo, lado a lado com a análise da v6; tempo e custo; e se os relatórios dos casos têm esqueletos diferentes entre si (sinal de que a v6.1 não virou template).
4. A pergunta final é qualitativa: o leitor entende melhor o mecanismo, identifica melhor como perde dinheiro e consegue contestar as premissas que determinam o valor? Contagem de páginas não é critério.

## Casos

**TotalEnergies (rerun na data-base de 18/09/2026).** Espera-se: ponte com abandono, previdência e híbridos, ou declaração de imaterialidade com fonte; varredura de exposição residual à Rússia, garantias de projetos de LNG e dívida proporcional de afiliadas; perfil de dívida; soma das partes quantificada contra o consolidado; alternativa de duração da renda (vida finita ou hazard); beta bottom-up com cadeia; preço normal do petróleo defendido pela curva de custo e pelo ciclo de capital; lucro do upstream decomposto em preço, volume e custo; perfis de CEO, CFO e do responsável pelo segmento de eletricidade; números idênticos entre chat, relatório e `outputs.json`; retorno do acionista distinto do custo de capital da firma. Reprova: justificar o consolidado só por integração operacional; extrapolar retorno médio como marginal; publicar versões divergentes.

**LPS Brasil e CrediPronto.** Espera-se: dossiê do acordo lido no original; cenário de término com o runoff da carteira existente precificado; quatro estados com probabilidade em julgamento; contingências fiscais dimensionadas; histórico de opções no ledger de decisões; receita decomposta em transações, ticket e comissão, mais franquias, mais a JV. Reprova: zerar a JV no encerramento; perpetuar direitos sem suporte documental.

**Compounder asset-light (Copart ou Constellation Software).** Espera-se: crescimento decomposto em unidades e receita por unidade, ou em orgânico e adquirido com o capital pago; diagnóstico de legado contra reinvestimento pelo retorno marginal por safra; ativos não evidentes (terrenos, carteira de aquisições) avaliados se materiais; mecanismo de moat com assinatura quantitativa; crescimento por ação. Reprova: concluir "reinvestment moat" só por retorno alto ou histórico de crescimento.

## Variações

- Contrato indisponível: a conclusão fica condicionada no ponto afetado, com a lacuna declarada.
- Mudança material depois da auditoria: as aprovações afetadas são refeitas e os resultados superados saem do conjunto ativo.
- Passivo já incorporado ao fluxo: não há segunda dedução.
- Companhia simples e sem dívida: a investigação de claims termina em uma linha, sem dossiê desproporcional.
- Anexo com republicação: comparabilidade preservada e fonte correta.
- Pesquisa acima do orçamento: pedido de autorização apenas para a expansão, com custo e efeito.

## Regressão técnica

`scripts/validate-plugin.py`, `testes.py --phase model` e `--phase cli`, `validate-report.py` sobre cada relatório gerado. Eles provam integridade técnica, não qualidade de research.
