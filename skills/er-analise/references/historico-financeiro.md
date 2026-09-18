# Histórico financeiro: reconstrução e anexo

Serve ao `/analisar`, onde a série é insumo do raciocínio, e ao
`/anexo-financeiro`, que a publica. Método, não template.

## Janela

A janela é o ciclo, não o calendário. Em cíclica, um ciclo inteiro, o que pode
exigir mais de dez anos; em companhia transformada por aquisição, o período
pós-perímetro com a quebra explicitada; em negócio estável, cinco anos podem
ensinar mais que doze. Oito a dez anos é referência, não regra.

## Fontes e reconciliação

Ordem: dado licenciado por conector, depois demonstrações da companhia, depois
agregadores. Conectores aceleram, mas reconcilie contra as demonstrações nos
anos-âncora: o último ano, cada breakpoint e o ano mais antigo da janela.
Divergência vira nota, não silêncio. Companhia brasileira: DFP e ITR na CVM,
Formulário de Referência para segmentos e indicadores operacionais. Se a
cobertura do conector for ruim e a reconstrução manual for longa, isso é caso
de consulta ao usuário antes de reconstruir dez anos à mão.

## Comparabilidade

Antes de comparar anos, trate: republicações (use a versão mais recente e diga
qual); operações descontinuadas; mudanças de perímetro (aquisições, cisões,
desconsolidações) com o ano da quebra; mudanças de norma (IFRS 16 em
arrendamentos, IFRS 17 em seguros, IFRS 9) e seu efeito nas métricas; moeda
funcional e de apresentação; itens não recorrentes e a definição de "ajustado"
da companhia contra a sua. Cada série carrega uma linha de notas de
comparabilidade.

## Definições

Explícitas, uma vez, e coerentes com o valuation: capital investido segue o
Gate 0 de Múltiplos Justos (não crie definição concorrente); retorno sobre
capital e sobre patrimônio declaram numerador, denominador e base temporal
(média, inicial, final); retorno médio nunca se apresenta como marginal; ações
médias servem ao lucro por ação e ações da data-base servem ao valuation;
caixa livre, dívida líquida e EBITDA ajustado têm composição declarada.
Métrica sem significado econômico para o negócio (dívida sobre EBITDA em banco)
aparece como não aplicável, com a razão.

## Conteúdo, conforme o negócio

- demonstrações: resultado, balanço e fluxo de caixa reclassificados em linhas
  econômicas (operacional, financeiro, não recorrente);
- segmentos: receita, resultado, capital e retorno por segmento quando a
  companhia divulga;
- métricas: crescimento e sua decomposição, margens, lucro operacional após
  impostos, lucro, caixa livre e conversão, capex e depreciação (capex sobre
  depreciação), capital de giro e ciclo de caixa, retorno sobre capital
  investido e sobre patrimônio, giro de ativos e de capital investido, dívida
  líquida, dívida sobre EBITDA, cobertura de juros, ações diluídas, lucro e
  caixa livre por ação;
- indicadores operacionais específicos: produção e custo unitário, clientes e
  retenção, lojas e vendas por loja, carteira e spread, o que explica esta
  companhia;
- linha de breakpoints: o evento que explica cada inflexão (aquisição, ciclo,
  mudança de norma, troca de comando).

## Uso na análise

A série não é ilustração; ela gera perguntas. Cada inflexão vira uma linha em
`investment-thesis.md`. Quando a reconstrução for feita durante o `/analisar`,
salve dados e notas em `historico/` para reutilização pelo anexo, sem formato
obrigatório.

## Anexo

Entrega padrão: um HTML autocontido com tabelas, definições, notas de
comparabilidade e fontes, separado do relatório ou como aba final quando o
usuário pedir, sem tocar a narrativa. Planilha ou CSV apenas a pedido ou quando
a reutilização justificar. O `verificador` reconcilia o anexo com o relatório
quando os dois existirem.
