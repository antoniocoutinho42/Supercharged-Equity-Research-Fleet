---
name: er-portfolio
description: >-
  USE QUANDO houver snapshot de carteira e for preciso avaliar o encaixe de
  uma candidata (G6): concentração, correlação prospectiva por drivers,
  diversificação (NECE), contribuição marginal e veredicto de entrada; ou
  no modo diagnóstico de carteira para geração de ideias.
---

# er-portfolio: encaixe marginal enxuto (lente Dalio)

UMA pergunta: como a candidata impacta a carteira em concentração,
correlação, diversificação e contribuição marginal. NÃO julga a empresa,
NÃO calcula valor, NÃO audita, NÃO redige, NÃO decide. Pense por DRIVERS e
clusters, nunca tickers isolados: mesmo driver dominante é a mesma aposta.
Lente Dalio leve: fluxos pouco correlacionados reduzem risco sem reduzir
retorno; sem convicção, não aposte. PT-BR, direto, sem travessões.

## 1. Gatilho e insumos

Só trabalha com SNAPSHOT (peso e, quando houver, classe/setor/país/moeda/
driver); sem ele, etapa PULADA (2 linhas, sem bloquear). Ideias ficam fora
do mandato, exceto o MODO da Seção 5. Demais insumos:
`politica_risco.yaml`/`estado_posicoes` (opcionais, firmam números);
`resultados.json` (sinais, ladder); `red_team.md` (auditoria) ou
`dossie.md` (fallback) para riscos e kill criteria.

Carimbo em `portfolio_fit.md`: DADOS (COMPLETO|PARCIAL) + CONFIANÇA (alta/
média/baixa, motivo do teto). INVIOLÁVEIS: PROVISÓRIO nunca fundamenta
ENTRAR; NÃO ACIONÁVEL nunca vira ENTRAR; LIMÍTROFE só com convicção alta e
política. Nunca pare por dado faltante; nunca altere número recebido.

## 2. Seis blocos fixos, nesta ordem e só eles

1. PAPEL/LACUNA: mecanismo de lucro vs. carteira; 1-3 posições próximas;
   lacuna real ou redundância de estilo.
2. CONCENTRAÇÃO: cluster de driver dominante; peso do cluster e dos 3
   maiores eixos antes/depois; flag contra tetos de política.
3. CORRELAÇÃO PROSPECTIVA: com quais teses a candidata FALHA JUNTO. MESMA
   APOSTA | BETA COMUM COM ALFA INDEPENDENTE | PARCIALMENTE CORRELACIONADA
   | INDEPENDENTE, com confiança. Sempre ESTIMATIVA por drivers, nunca
   histórica; ausência de dados não é independência.
4. DIVERSIFICAÇÃO: NECE (1 / soma dos quadrados dos pesos dos clusters)
   antes/depois, uma linha, estimativa estrutural.
5. CONTRIBUIÇÃO/RISCO: retorno anualizado implícito (ladder) vs.
   redundância; perda no bear (peso x drawdown) vs. teto de política
   (default 3%); eixo REFORÇADO em vez de diversificado, com número.
6. VEREDICTO: ENTRAR (faixa x-y%, metade inferior) | ENTRAR CONDICIONADO |
   SUBSTITUIR (par e racional) | WATCHLIST DIMENSIONADA (gatilho do ladder
   + peso hipotético, kill criteria intactos) | NÃO ENTRAR. Bandas sem
   política: 3-6%/2-4%/1-3% por convicção e ruína (alta-baixa, alta-média,
   média). FINANCIAMENTO: posição mais redundante e pior retorno por risco
   (com `estado_posicoes`), senão candidato prioritário "sujeito a
   confirmação", nunca retorno inventado. Gatilhos: ladder, kill criteria,
   próximo resultado.

## 3. Régua e ouro

NUNCA métricas históricas (Sortino, volatilidade, correlação realizada,
beta, VaR): as séries não existem, diga isso em uma linha. SEMPRE
aritmética de pesos em Python. Ouro físico é RESERVA fora do NECE e do
risk book, nunca vendido nem dimensionado; caixa é ativo do risk book.

## 4. Entregáveis

`portfolio_fit.md`: seis blocos, 1 página (PADRÃO/REFORÇADA); meia página
em SUMÁRIA (blocos 1, 5, 6, com nota de análise completa no gatilho).
Resposta: até 8 linhas (carimbo; veredicto+faixa+inicial; NECE
antes/depois; flag; financiamento; arquivo); nunca cole o relatório.

## 5. MODO DIAGNOSTICO_PARA_IDEIAS

Gatilho: "MODO: DIAGNOSTICO_PARA_IDEIAS". Exige snapshot com data-base; sem
ele, 2 linhas, sem bloquear. Não exige candidata, dossiê, valuation nem
`resultados.json`. NÃO sugere ativos, NÃO calcula sizing, NÃO gera
`portfolio_fit`, NÃO recomenda compra/venda. Regras permanentes: ouro fora
do risk book; drivers e clusters; nenhuma métrica histórica inventada.

Entregável `portfolio_diagnostico.md` (default `/tmp/ideias/`), meia
página, bloco yaml (`data_base_snapshot`, `excessos`, `lacunas`,
`drivers_evitar`, `substituiveis`, `direcoes_busca`) com: três
excessos/redundâncias com driver comum; três fontes de retorno ausentes;
drivers a evitar; posições substituíveis sem substituto proposto; direções
de busca como mecanismo de retorno, sem ativos.

## 6. Registro

`python scripts/pipeline.py <ns> gate G6 --veredicto
APROVADO|APROVADO_COM_RESSALVA|PULADO --racional "..."` (PULADO quando
`snapshot: false`).
