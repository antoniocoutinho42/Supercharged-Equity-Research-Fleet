# Roteiro de F5 (qualitativa) e F6 (financeira histórica)

## Disciplina de evidência (vale para as duas fases)

- Rotule cada afirmação relevante: FATO (com fonte e data), ESTIMATIVA (com premissa) ou
  HIPÓTESE (com o observável que a arbitraria).
- Hierarquia de fontes: filing/demonstração auditada > comunicado da companhia/RI > dado
  OpenBB > imprensa especializada > agregador/consenso. Filing vence agregador; divergência é
  registrada, nunca silenciada.
- Uma pesquisa por fato decisivo: não herde ausência declarada por terceiros ("dado indisponível"
  exige a busca que o sustenta).
- Recalcule você mesmo as métricas decisivas a partir dos dados coletados (nunca as de
  valuation — essas são do engine).

## F5 — Análise qualitativa (`qualitativa.md`)

Blocos (profundidade proporcional à importância para ESTE caso; norte: o que isso implica para
os 16 inputs):

1. **Modelo de negócio em profundidade** — como o dinheiro é ganho: unidade de receita, estrutura
   de custos, intensidade de capital, sazonalidade/ciclo, dependências (fornecedores, clientes,
   regulador). "So what": aponta ROE1 normalizado e arquétipo §7.
2. **Setor e dinâmica competitiva** — tamanho e crescimento do mercado, estrutura (concentração,
   racionalidade de preço), forças de entrada/substituição, posição relativa da companhia.
   "So what": sustenta g1/g2 e o realismo de ROE2 vs pares.
3. **Vantagens competitivas e DURAÇÃO** — inventário de evidências (switching costs, retenção,
   rede, custo, marca/preço, IP/licenças, contratos longos, estabilidade de share, barreiras,
   risco tecnológico, velocidade de imitação, runway de reinvestimento): para cada uma, a
   evidência OBSERVÁVEL e o que a erodiria. "So what": n2 (quanto tempo o spread pleno dura) e
   F (velocidade de convergência) — sem converter contagem de fatores em anos mecanicamente.
4. **Management e capital allocation** — histórico de alocação (orgânico, M&A, dividendos,
   recompras a que preços), alinhamento, governança, controlador (estatal? família?). "So what":
   payout implícito nos funding ratios, risco de ROE2, eventos societários.
5. **Riscos** — operacionais, regulatórios/judiciais, societários, de balanço, discretos
   (falha binária → candidatos a distress §6.5, nunca só Ke). Para cada risco material: mecanismo,
   observável antecedente, onde entra no modelo (cenário, input ou probabilidade).
6. **Pontos do grill-me** — cada resposta do usuário tratada como evidência: verificada,
   confirmada ou refutada, com fonte.

## F6 — Análise financeira histórica (`financeira.md`)

Com a janela máxima disponível em `dados/` (janela curta: declarar o corte e o efeito na âncora):

1. **Decomposição do ROE (DuPont)** — margem líquida × giro do ativo × alavancagem, ano a ano;
   separar efeito operacional de efeito de estrutura; ROE médio vs marginal.
2. **Margens e giro** — bruta/EBIT/líquida e asset turnover: tendência e explicação CAUSAL
   (preço? mix? escala? câmbio? ciclo?).
3. **Alavancagem e cobertura** — dívida bruta/líquida sobre equity (convenção do manual: book,
   nunca market cap), custo médio, cobertura de juros, perfil de vencimento.
4. **Conversão de caixa e FCFE** — pelas relações do manual (§3): NI → FCFE via funding
   requirement; nunca fórmula própria. Onde o caixa some (capex, working capital, provisões)?
5. **EPS e CAGR** — série de EPS diluído (da DRE), CAGR por janela, efeito de recompras vs
   crescimento orgânico.
6. **Payout e recompras** — dividendos + buybacks vs FCFE; sustentabilidade da distribuição.
7. **P/L histórico** — série de preço/EPS trailing: onde o mercado costumou pagar; contexto para
   a leitura do K3 justo (validação por múltiplos é ANÁLISE, não input).

Regras de ouro: (a) conectar o qualitativo aos números — cada tendência numérica ganha explicação
causal e cada tese qualitativa é testada nos números; (b) gerar insights NOVOS dos dados (o que
os números revelam que a narrativa não contava?); (c) tudo que alimentar gráfico da aba 2 sai
daqui com fonte (`dados/<arquivo>`) e derivação declarada.
