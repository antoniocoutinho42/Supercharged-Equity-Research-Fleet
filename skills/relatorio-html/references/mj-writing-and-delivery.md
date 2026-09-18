# Traduzindo Múltiplos Justos para linguagem de mercado

A metodologia não deve aparecer como manual de uso dentro do relatório. Traduza-a para perguntas de investimento.

## Tradução

- Em vez de listar `Gate 2`, explique que a base reportada está defasada porque determinado driver já mudou e quantifique o efeito.
- Em vez de apenas mostrar `ROIC marginal`, explique quanto capital novo a companhia consegue empregar, a que retorno e por quanto tempo.
- Em vez de discutir `TV book/convergencia/gordon` como nomenclatura, explique qual hipótese sobre duração econômica do spread sustenta o terminal e quanto a escolha move o valor.
- Em vez de uma tabela de parâmetros soltos, ligue cada premissa a um driver real da companhia.
- Reverse valuation deve responder "o que precisa acontecer no negócio para o preço estar certo?".
- Sensibilidade deve mostrar qual hipótese vira a conclusão e a distância entre o caso-base e esse ponto.

## Status das afirmações

Quando houver risco de confusão, deixe claro o que é observado, derivado, inferido ou assumido. Não exponha esse vocabulário como burocracia se a distinção já estiver inequívoca na prosa.

## Escolhas metodológicas

Leve ao leitor apenas as escolhas que mudam a interpretação ou o valor de forma material. Mostre direção e magnitude do efeito. Não despeje a árvore inteira de decisões da metodologia.

## Terminal, MM e reversa

O terminal deve ser compreensível economicamente e re-testado. A decomposição MM, quando aplicável, serve para mostrar quanto do valor vem da base instalada, do crescimento e do terminal. A reversa serve para transformar o preço em exigências econômicas observáveis.

A reversa é condicional: "o preço embute X do driver" vale para os demais inputs declarados e não prova o que o mercado acredita; diga a condição. Retorno implícito resolvido em custo de capital da firma é retorno da firma, não o retorno esperado do acionista; quando o relatório falar em retorno do acionista, ele vem do custo do equity ou de fluxo ao equity com saída coerente.

## O que fica fora da narrativa principal

Comandos do motor, nomes internos de gates, logs, JSON, checks mecânicos e memória de cálculo pertencem aos artefatos técnicos, salvo quando um deles for necessário para explicar um risco real da tese.
