# Rotas especiais e marca de estoque

## 13. Rotas especiais e marca de estoque dentro do framework Múltiplos Justos

A v10.1 reconhece economias em que uma perpetuidade operacional agregada não é a representação correta. No Fleet, isso NÃO autoriza abandonar Múltiplos Justos: esses casos passam a ser **rotas internas do framework**, preservando gates, rastreabilidade, disciplina de premissas, diagnósticos e autoridade determinística do `justos.py` para tudo que o motor cobre. Para ativos de vida econômica finita, use a rota `finite-life / reserve NAV`; para REITs e imobiliárias, `asset NAV`; para holdings, `holding / SOTP`; para pré-lucro, `option / scale`; para financeiras, a rota `equity`; e para base operacional inválida, normalize ou migre para a rota interna que representa o ativo. Comparáveis são contexto e sanity check, nunca a metodologia que determina o valor justo. A escolha de rota é explicitada em `references/core/routes.md`.

**Marca de estoque — teste da identidade. Obrigatório quando ≥ ~20% do valor vem de marca de
estoque** (laudo, NAV, cap rate, valor de reposição, landbank, estoque pronto, carteira marcada,
participação avaliada). A rota interna escolhida acima NÃO dispensa testar
a marca que essa rota entrega — e é exatamente aí que o parágrafo anterior vinha terminando
cedo demais. Marca de estoque é PREÇO PRESUMIDO, não observado: laudo, NAV, cap rate e valor de
reposição são marcações, e a última transação é observação de UM ativo, não do portfólio. Todo
estoque obedece a uma identidade só:

```
Marca = VP(aluguel que o estoque comanda, anos 1..T) + VP(Marca_T),
com Marca_T = Marca × (1 + apreciação)^T
```

Dela saem as três saídas obrigatórias, e nada mais precisa ser decidido:

- **Fator de tempo.** `VP(Marca_T) ÷ Marca` — quanto da marca sobrevive só ao tempo, antes de
  qualquer aluguel. Com aluguel ≈ 0 (terreno ocioso, landbank, estoque não alugado) a marca inteira
  depende dele; com aluguel NEGATIVO (condomínio, IPTU, custo de guarda, pastagem em manutenção) o
  fator é TETO, não centro.
- **Apreciação implícita** = custo de capital DO ATIVO − yield corrente, confrontada com a série
  observada na janela LONGA e na RECENTE. **Use o custo de capital do ativo, não o da companhia:**
  um estoque de terra, imóvel ou concessão não carrega o beta do equity que o detém, e herdar o custo
  médio ponderado consolidado é o erro mais comum deste teste. A direção do viés depende de qual dos
  dois é maior — calcule, não deduza.
- **T é derivado, não arbitrado:** giro observado do estoque (monetização média ÷ estoque). **T não
  declarado ⟹ a marca entra líquida hoje**, o ramo mais otimista, e o silêncio equivale a adotá-lo.
  Giro do exercício corrente materialmente diferente da média ⟹ reporte os DOIS horizontes e o que
  precisa acontecer para o ritmo voltar.

**Parede estoque↔fluxo — o lado do ATIVO da parede do §12.** Quando o estoque marcado é INSUMO
PRODUTIVO do fluxo avaliado (terra e lavoura; landbank e incorporação; imóvel e operação hoteleira ou
hospitalar; navio e afretamento; ativo de concessão e operação; participação marcada e equivalência),
duas rotas fecham a conta e a mistura conta o mesmo ativo duas vezes:
**(a) marca à vista + aluguel imputado** — o estoque entra a preço de hoje e o fluxo é cobrado do
aluguel de mercado do estoque que emprega, ancorado em OBSERVÁVEL (o que a própria companhia recebe
ao arrendar/afretar/alugar; a taxa da região; o contrato comparável), nunca só em construção.
**(b) fluxo pleno até T + marca descontada de T** — o fluxo usa o estoque de graça durante T e a
marca é descontada até T pela apreciação declarada acima.
As duas são idênticas SE, e somente se, a identidade fechar. **Quando não fecha, o gap entre as
rotas MEDE a violação — e é o gap que vai à entrega, não a escolha entre elas.** Rodar uma rota só e
batizar a diferença de "desconto de holding" ou "preço do tempo" é dar nome de conclusão a uma
premissa não testada.

**Razão R — generalização do sub-alerta de recuperação (§3).** `R = marca do estoque ÷ capitalização
perpétua do fluxo corrente`. R mede quanta RECUPERAÇÃO a marca embute acima do que o negócio, como
está, sustenta; o cruzamento é exato em R = 1. A convenção ancorada no capital investido é o caso
PARTICULAR com `R = custo de capital ÷ retorno médio` — a marca de estoque é o caso geral, e vale com
laudo, NAV ou valor de reposição no lugar do book. **Reporte R sempre que o gatilho disparar.**

**Deságio é operação sobre ATIVO, nunca sobre líquido de passivos.** Percentual aplicado a agregado
já líquido de dívida desconta a dívida junto: conservadorismo aparente com o sinal invertido, e o
erro cresce com o deságio. Declare o OBJETO e, se o agregado for líquido, o percentual equivalente
sobre os ativos brutos.

**Na entrega.** O NÍVEL da marca é a **11ª escolha metodológica nomeada** (gatilho ≥ ~20% do valor):
marca de AVALIAÇÃO × marca de TRANSAÇÃO realizada, esta com a dispersão das operações — média de
transações dispersas não é marca, é média. A ROTA (a)/(b) fica FORA da lista: é invariante de
coerência, ao lado da base monetária, e escolha coerente entre elas não cria nem destrói valor.

**Corolário sobre a base de lucro — vale ABAIXO do gatilho de 20%.** Realização de estoque (ganho de
alienação do ativo marcado, reavaliação, marcação a mercado) NUNCA ancora nem VALIDA uma base de
FLUXO. Agregado que some as duas — "EBITDA ajustado" contendo ganho de venda de ativo, "lucro"
contendo reavaliação — está do lado errado da parede, e usá-lo como conferência devolve falso
positivo justamente quando os dois componentes se compensam. Reconstrua a série de fluxo pela fonte
primária e, **se a companhia publica a série isolada, a derivação por subtração é proibida** —
subtrair um agregado do outro transfere para a série o erro dos dois.
