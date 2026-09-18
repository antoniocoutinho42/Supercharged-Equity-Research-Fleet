# Degrau e capacidade pré-construída

## 8. Degrau de nível e capacidade ociosa — o nível que ainda pode mudar

Generalização do §7 para eventos que **elevam o lucro sem consumir capital novo**. A teoria e a
prova do sinal do erro estão em `derivacao.md` §8. Aqui, a aplicação.

**Classes de degrau, e onde cada uma entra:**

| Evento | Entrada correta no motor |
|---|---|
| Nível de commodity, câmbio, frete, energia | re-base da métrica + queda de d (§7) |
| Re-precificação regulatória (teto de juros, tarifa, take-rate) | re-base do lucro; g inalterado |
| Deployment de capacidade ociosa de balanço | rentabilidade × h; g inalterado |
| Ganho de escala / diluição de custo fixo | re-base da métrica; excluído por premissa do modelo |
| Aquisição a valor de livro | rentabilidade inalterada; re-base de lucro E capital |
| Mudança de estrutura de capital | via Ku, nunca via g |
| Crescimento orgânico gratuito (RiR = 0) | não representável em g; representável em nível/degrau se a trajetória for declarável (paper §6.9); caso-limite tem forma fechada — ver "teto do crescimento gratuito" abaixo |
| **Capacidade PRÉ-CONSTRUÍDA em rampa** (parque fabril ocioso, planta/rodovia atingindo regime, racks vazios) — v9.22 | g de rampa com **RiR por componente** (só giro na fase 1), ou re-base ao estacionário − VP do capex COMPROMETIDO quando a rampa é instantânea — mecânica completa em §8f; nunca degrau × h (ignoraria o giro), nunca g com RiR pleno (cobraria capex que não será incorrido) |
| **Ativo próprio PARADO por evento regulatório, judicial ou político** (mina suspensa, concessão cassada, licença travada) | re-base da métrica com fator de captura **E probabilidade**; nunca g, nunca rentabilidade × h |

**Classe do ativo parado (v9.12) — o que ela tem de diferente.** Nas outras classes o que falta é
capital, tempo ou preço; aqui o ativo **existe, está pago e está produzindo zero**, e o que falta é
a decisão de um terceiro (regulador, tribunal, governo). Três consequências operacionais:
(i) o degrau é de NÍVEL — o ativo volta ao patamar que já tinha, não a um patamar novo —, então
entra por re-base da métrica e nunca por rentabilidade × h, que é a classe da capacidade ociosa de
BALANÇO; (ii) além do fator de captura da rampa, ele carrega uma **probabilidade** explícita, porque
a decisão pode não vir; (iii) a reversa útil deixa de ser o múltiplo implícito e passa a ser a
**PROBABILIDADE implícita no preço** — que converte "está caro?" numa pergunta binária e testável.
Se a probabilidade implícita passar de 100%, o preço exige mais do que o religamento pleno entrega,
e isso é um achado, não um arredondamento (jurisprudência J2).

**Nunca em g.** Se o evento não consome capital novo financiado por lucro retido, ele não é g por
definição. O delator é o RiR: se lançar o evento como crescimento estoura RiR > 100% sem captação
planejada, a classificação está errada. **(v9.22)** O delator aplica-se POR COMPONENTE: preencher
capacidade pré-construída consome giro — RiR_wk > 0 —, e é exatamente isso que legitima a entrada
como g na fase de rampa (§8f), com o teste de 100% rodado sobre o RiR da fase, não o agregado. E o erro **não tem sinal definido** — destrói valor com
spread negativo, desaparece na neutralidade, e com spread positivo distorce em duas direções.
Não existe ajuste conservador; existe classificação certa ou errada.

**O teto do crescimento gratuito (v9.13) — obrigatório quando a reversa não fecha.** O caso-limite
RiR → 0 tem forma fechada: com reinvestimento zero, o FCFF é o NOPAT inteiro e o valor colapsa num
Gordon puro — rodável no motor como `gordon` com rentabilidade terminal → ∞ (RiR_TV = gp/RONIC → 0)
e gp = g. É o TETO do que qualquer história de crescimento pode valer: nenhuma hipótese de
crescimento *pago* chega lá, porque pagar reinvestimento só subtrai fluxo. Regra: **sempre que a
engenharia reversa não encontrar raiz em nenhum eixo primário (rentabilidade, g), rode o teto** — o
motor passou a sugerir isso no próprio output do `rev` (campo `sugestao`), junto com a curva
iso-valor. Duas leituras saem dele: a distância entre o teto e o caso-base é o preço que o mercado
está pagando pela hipótese de gratuidade do crescimento; e o g gratuito implícito que iguala o teto
ao preço de tela é a premissa única em que a tese de mercado se apoia — confrontável com o teto
macro (gp ≤ rf) e com a pergunta de contraditório: *se o crescimento é grátis, por que a companhia
está deployando capital?* (jurisprudência J3).

**Mecânica (comando `degrau`):**
```
h = índice_atual / índice_alvo                  (expansão máxima da base geradora)
rentabilidade_pós = rentabilidade × [1 + (h − 1) × m]
g inalterado; rentabilidade terminal inalterada
```
`m` = eficiência marginal do capital liberado (retorno marginal ÷ retorno médio). Declare o valor
e a razão. Rode sempre uma banda (ex.: 0,7 / 1,0 / 1,3) e trate a banda como faixa, não como
cenários independentes.

**Quatro travas obrigatórias, sempre reportadas:**
1. **A rentabilidade terminal não acompanha.** A competição não deixa o spread do capital marginal
   sobreviver ao CAP. Rentabilidades pós-degrau muito acima do custo de capital, perpetuadas, são
   aritmética e não economia — reporte como teto da alavanca, não como cenário.
2. **O degrau não é instantâneo.** Fator de captura aplicado **só ao incremento**, nunca à base.
   O padrão é **rampa linear** — média dos fatores de desconto de 1 a T —, porque deployment é
   gradual; `pontual` (1/(1+custo)^T) só com evento datado, tipo licença ou fechamento de aquisição.
   A escolha importa: a 20% e 4 anos, rampa dá 0,647 e pontual dá 0,482, uma diferença de 34% no
   incremento. Ignorar a transição superestima; usar `pontual` numa rampa subestima.
3. **Coerência com as premissas: D/E constante é violado por construção.** O deployment muda a
   alavancagem — é literalmente o que ele faz. O resultado do motor vale para o **estado
   estacionário pós-deployment**, com a nova alavancagem já estabilizada, e não para a trajetória.
   Declare isso: é a diferença entre um número defensável e um número errado. E é por isso que
   existem (i) o fator de transição sobre o incremento e (ii) a rentabilidade terminal parada.
4. **O degrau não é grátis: é uma opção vendida.** Consumir o colchão eleva a probabilidade de
   evento de capital, e o custo é assimétrico ao múltiplo de tela (emitir acima do valor
   patrimonial é acretivo; abaixo, destrutivo). Além disso: **verifique qual é a restrição
   EFETIVA.** Frequentemente não é a que se está relaxando — capacidade de funding, de originação
   ou de share satura antes do capital. Quando isso ocorre, `m < 1` é consequência mecânica, não
   pessimismo. Sempre teste a restrição alternativa com uma conta explícita (necessidade anual
   vs. capacidade observada).

**Piso teórico ≠ piso administrável.** O mínimo regulatório inclui buffers cuja violação dispara
restrição a distribuição. Declare os dois e use o administrável como cenário; o teórico é limite
matemático.

**Reversa em degrau:** `degrau --alvo-pvp` devolve o índice-alvo implícito no preço; combinado com
a reversa em rentabilidade, produz a curva iso-valor. Leitura padrão: o mercado paga por um dos
vetores, raramente pelos dois.

### §8f — Capacidade pré-construída: RiR por componente, fases e compressões (v9.22, origem J15)

**O fenômeno.** Capital fixo pago ANTES da receita que vai servir. O crescimento até a capacidade
plena é parcialmente gratuito: gratuito no componente fixo, pago no giro. Dois erros gêmeos na
mesma direção (subavaliar): o RiR agregado cobra capex fixo que não será incorrido e deprime o
ROIC marginal residual; o `d` contábil reflete D&A do parque pleno sobre EBITDA de utilização
parcial. Gatilho no Gate 3 do SKILL.md; a leitura de capacidade é a 10ª escolha nomeada.

**Duas fases:** rampa (duração T: receita preenche a capacidade; `g_volume =
(capacidade ÷ produção_atual)^(1/T) − 1`; RiR₁ = ΔWC ÷ NOPAT; capex só de manutenção) e
pós-plena (RiR₂ pleno, fluxo padrão). **Atenção à anualização:** a composição geométrica é sobre
a razão capacidade/produção — `(1 + ociosidade)^(1/T) − 1` subestima, e tanto mais quanto mais
ociosa a planta (u = 50%, T = 10: 4,1% contra os 7,2% corretos). T é âncora do caso — carteira ÷
receita, guidance de ramp, rampas anteriores da própria companhia — sempre declarada.

**Três compressões, pela relação entre T e o CAP:**
- **T ≈ 0–2 anos (rampa instantânea — rodovia entregue):** re-base da métrica ao estacionário de
  capacidade plena, fluxo SEM crescimento de rampa; capital fixo já incorrido é afundado (nada a
  subtrair); capital COMPROMETIDO a incorrer (obra em andamento, investimento obrigatório de
  contrato) subtrai seu VP — é passivo econômico, não opção. Coerência de regime obrigatória:
  fluxo em moeda de hoje = regime REAL = custo de capital real (ou nominal com a inflação
  devolvida no terminal) — Modigliani-Cohn, J6. Concessão com termo continua roteada ao §13
  (DCF de projeto como manchete); esta compressão traduz, não substitui.
- **2 < T < CAP (rampa dentro do horizonte):** duas rodadas costuradas — fase 1 com n = T,
  g = g_rampa (+ componente de preço declarado à parte), RiR₁ e d₁ da fase; fase 2 é o TV da
  primeira, rodada com o vetor pleno e trazida a VP. Precedente arquitetural: ponte e iso
  bifásicos. **Forma fechada da fase 1 (v9.23, provada em planilha):** o RiR da rampa VARIA
  ano a ano (a D&A fixa dilui num lucro que cresce mais que a receita) — não há vetor único —,
  mas o fluxo colapsa em DUAS anuidades: `FCFF_t = α(1+g₁)^t + β`, com
  `α = (1−t)·EBITDA₀ − wk·g₁·Receita₀/(1+g₁)` e `β = −(1−t)·D&A_parque`; a anuidade PLANA da
  depreciação fixa é o termo que a rodada única não representa. **Verificações obrigatórias da
  costura, executáveis hoje:** (i) a fase 2 isolada confere no motor — `ev` sobre a base do ano
  T com n = CAP−T, contra o TV da fase 1; (ii) Receita_T = capacidade, por construção da fórmula
  da rampa — diferença ≠ 0 denuncia erro de montagem. Conservação POR FASE segue obrigatória
  (§11.1b). Comando `rampa`: derivação PROVADA (proveniência: planilhas ELMT ago/26, suíte de
  cinco provas). **Comando `rampa` IMPLEMENTADO (v9.24)**, com a suíte incorporada a
  `testes.py` — P1 fluxo a fluxo contra α/β, P2 contra reconstrução 3DF independente, P3
  fase 2 = `ev` do próprio motor, P4 Receita_T = capacidade, P5 âncora da planilha (EV 170,93;
  d re-basando 25,4→16,5%) — e âncora travada no `selftest`. g1 < 0 roda o bloco de COLHEITA;
  RiR₂ ≥ 100% dispara o delator; o output ecoa as travas (terminal, delimitador, volume≠preço).
- **T ≥ CAP:** rodada única com RiR = RiR_wk e terminal na convenção escolhida sobre a base de
  saída, declarando que o CAP faz papel duplo (prazo de rampa E horizonte de vantagem); quando
  os dois divergirem materialmente, migre para a compressão bifásica. **Direção do erro
  (v9.23):** com o d corrente congelado, a rodada única SUBESTIMA o ramo — o re-base do d é
  permanente (magnitude do caso de referência: ~5% do valor, J15; ordem de grandeza de UM caso,
  não constante); o par coerente usa o d médio da trajetória (trava 4).

**Composição de fases (v9.23) — o princípio geral.** As três compressões são casos de UMA
regra: qualquer sequência de fases se avalia DE TRÁS PARA FRENTE — a última fase é o valor
terminal da penúltima, descontada ao início dela, recursivamente até hoje; cada fase é um bloco
com seu par (d, RiR) coerente e sua conservação própria (§11.1b). **Biblioteca de blocos**
(maquinário existente, indexado): *investimento* (fluxo ≤ 0; −VP do capex COMPROMETIDO —
compressão 1); *rampa geométrica* (forma fechada α/β acima — exige base de partida positiva);
*rampa de/para ~zero* (planta comissionando do zero: a geométrica é indefinida — use re-base ao
estacionário × fator de transição linear do §8, que é exatamente a compressão da rampa linear);
*bloco padrão* (NOPAT×(1−RiR), qualquer convenção terminal); *evento de estrutura de capital*
(a ponte do §8b compõe na mesma recursão — o iso bifásico já o faz); *colheita* (g < 0 — a forma α/β funciona com g₁ negativo sem alteração: processadora pós-pico,
run-off, footprint encolhendo; é o espelho formal da leitura não-consensual de J15). **O sinal do
ciclo decide o sinal do bloco (v10):** com giro POSITIVO, contração LIBERA capital e `FCFF > NOPAT`
— é a colheita clássica. Com giro NEGATIVO, contração **consome** capital e `FCFF < NOPAT`, enquanto
o crescimento se autofinancia em parte e o componente de giro do reinvestimento é negativo. A
álgebra é a mesma; o que muda é o sinal de `wk`, e o motor passou a aceitá-lo (v10) desde que
`wk + kappa > 0` — quando o capital incremental total vira não positivo, a intensidade de capital
deixa de ser definida e as fases rodam pelo bloco padrão. **Trava do delimitador (inegociável):** cada fase adicional exige um
EVENTO OBSERVÁVEL que a delimite — comissionamento datado, plena capacidade, termo de contrato,
marco de guidance; fase sem delimitador é grau de liberdade disfarçado de análise, e a entrega
declara o delimitador de cada fronteira. Modelo multifásico sem essa trava é máquina de
racionalizar qualquer preço.

**Reversa sob o ramo (v9.23).** Sob intensidade de capital constante por Δreceita, o ROIC
marginal independe de g (margem × giro — a identidade do §11.2): a reversa em g fica bem
identificada e pode ganhar raiz onde o ramo corrente não tem nenhuma. A raiz se reporta SEMPRE
com dois confrontos — o RiR implícito na raiz contra o teto de autofinanciamento do componente,
e a receita implícita no horizonte contra a base. Raiz sem os confrontos é número sem leitura.

**Protocolo da capacidade física (quando não há utilização divulgada):** (i) a pergunta única —
*quanta receita este ativo fixo gera por período?* — respondida pelas características objetivas
do ativo (unidades/hora × horas × preço; veículos/dia × tarifa; MW × fator × preço);
(ii) o teto é `min(capacidade física, demanda endereçável, teto de autofinanciamento do giro)` —
a restrição efetiva frequentemente satura antes da física (trava 4 do §8, estendida);
(iii) contraprova obrigatória: receita-por-ativo contra pares operando perto da plena —
admitidos fallbacks declarados na melhor granularidade obtível (receita/m², receita/funcionário,
receita por ativo-chave: tonelada de prensa, MW, leito); contraprova NÃO executável ⟹ declarada
como tal e o ramo permanece sensibilidade — a regra de centralidade não se relaxa por
indisponibilidade de dado;
(iv) estatuto: hipótese de construção — cadeia de derivação exibida, banda de utilização
obrigatória, direção do erro declarada. Nunca número seco.

**Travas:** (1) **canal único** — a mesma capacidade entra por UM canal (g de rampa OU re-base OU
degrau), nunca dois; (2) **volume ≠ preço** — g_rampa é volume; repasse de preço entra separado
(price-taker: §7); (3) **conservação por fase** — a identidade fecha em cada fase com o par
(d, RiR) daquela fase (§11.1b); (4) **o d da fase 1 é média declarada entre o d corrente e o da
capacidade plena, SEMPRE acoplada à re-derivação do RiR** — mover d congelando o triângulo é o
quadrante proibido de sempre; âncora do d da plena (v9.23): D&A do parque ÷ EBITDA a plena
capacidade — a intensidade estacionária de reposição por unidade de EBITDA; capacidade NOVA da
fase 2 entra nessa mesma razão (aproximação declarada). A D&A do parque segue a guarda de moeda do d (item v da cadeia do d, §1); parque recém-construído tem idade média baixa e fator ≈ 1 por construção — na rampa, o ajuste tipicamente não se aplica. O mesmo raciocínio vale para G&A fixo
DENTRO do EBITDA: a rampa também o dilui — modelá-lo é re-base de margem declarado; omiti-lo tem
direção do erro conhecida (subestima) — conservadorismo consciente, nunca implícito; (5) **a rentabilidade terminal não herda a rampa** — o ROIC alto da
fase 1 é alto porque o fixo é gratuito, e morre com ela; fase 2 e terminal usam a rentabilidade
do capital que constrói; (6) **delator por componente** — RiR da fase > 100% sem captação
declarada = classificação errada.
