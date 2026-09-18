# Derivação de premissas

## 2. Regras travadas de derivação de premissas

O objetivo é que dois analistas, com os mesmos dados públicos, cheguem ao mesmo input. Cada regra
abaixo é obrigatória; desviar dela exige declarar o desvio e o motivo.

**Custo de capital (a maior fonte de variância — travar sempre).**
`Ke = rf + β × ERP`, com:
- `rf` = taxa livre de risco observável na moeda dos fluxos, com fonte e data. Para fluxos em BRL
  nominal, a taxa básica corrente ou o vértice longo da curva nominal — declare qual e por quê.
- `ERP` = prêmio de risco do mercado de listagem/operação, com fonte e data.
- `β` — **a rota central é o beta BOTTOM-UP, não a regressão da própria ação (v10.1).** O beta de
  regressão de uma ação individual carrega erro-padrão típico de 0,20 a 0,30 e é medido sobre a
  estrutura de capital do PASSADO; a média setorial desalavancada tem o erro dividido por √n e é
  realavancada para o D/E e a alíquota de HOJE. Procedimento: (i) selecionar os pares pelo modelo de
  NEGÓCIO, não pelo código setorial, e nomeá-los; (ii) desalavancar cada um,
  `β_u = β_L / [1 + (1−t)·D/E]`; (iii) tomar a mediana; (iv) realavancar ao D/E a mercado e à
  alíquota da companhia; (v) em multi-segmento, ponderar os betas desalavancados por VALOR de cada
  segmento, nunca por receita. O beta de regressão da própria ação, quando existir, entra como
  **confronto** — divergência grande é achado (mudança de estrutura, iliquidez, evento societário),
  não motivo para trocar de rota em silêncio. Sem pares defensáveis e sem série, é hipótese de
  construção com a cadeia exibida e a banda em beta do parágrafo abaixo — nunca um número "razoável"
  sem lastro.
- **Canal do risco-país — escolha UM e declare (v9.15):** (i) β contra índice local/amplo + ERP
  maduro + CRP explícito ponderado por LUCRO (não receita); ou (ii) β do ADR contra o índice do
  mercado de listagem + ERP maduro, SEM CRP adicional — a covariância medida em moeda forte já
  embute parte do risco-país, e empilhar CRP por cima conta duas vezes. Empilhamento é PROIBIDO
  como estimativa central; admissível só como extremo declarado da banda de sensibilidade (que
  segue ±200 bps quando o prêmio-país é volátil). Jurisprudência J8: +2,3 p.p. empilhados =
  −35% de valor sem violar nenhuma regra da v9.14.
- **Beta não mensurável na sessão** (sem série, sem terminal de mercado): declare como hipótese de
  construção, exiba a cadeia (pares nomeados, ou `ρ × σ_ação/σ_índice` com as três entradas), e a
  **sensibilidade obrigatória passa a ser em BETA, banda de no mínimo ±0,20** — a ordem de grandeza
  do erro-padrão típico de um beta de ação individual —, com o preço por ação nas três pontas. A
  razão de mudar a unidade é operacional: a reversa já devolve o **beta implícito** no preço
  `(custo_impl − rf)/ERP`, e com as duas grandezas na MESMA unidade o confronto vira uma frase
  ("nossa banda é 0,60–1,00; o preço exige 0,01"), enquanto em pontos-base ele exige uma conversão
  que na prática ninguém faz. O custo de capital em pontos-base fica para a memória técnica.
- Empresa sem dívida ⟹ WACC = Ke. Com dívida, derivar via Ku (`kewacc`), pesos a mercado.
- Moeda: o Ke tem que estar na moeda dos fluxos. Se lucro em moeda local e preço em moeda
  estrangeira, avalie em moeda local com Ke local e converta o resultado ao câmbio spot — nunca
  misture Ke de uma moeda com crescimento nominal de outra.
- **Regime do MODELO, não só da moeda — Fisher.** O Ke acima é NOMINAL. Pergunte: *o g contém
  inflação?* Em price-taker normalizado a nível, NÃO: o g remanescente é volume e os fluxos ficam
  em preços de hoje. Descontar fluxo real a taxa nominal é o erro de Modigliani-Cohn. Há duas rotas
  **EXATAMENTE equivalentes** por Fisher: **(A)** manter os fluxos reais e usar Ke REAL,
  `(1+Ke_real)=(1+Ke_nom)/(1+π)`; **(B)** manter Ke nominal e inflacionar **todo o horizonte
  explícito e o terminal** à inflação coerente. A antiga rota "Ke nominal + inflação somente no
  terminal" NÃO é Fisher equivalente: é uma aproximação terminal-only e só pode aparecer como
  sensibilidade rotulada, com o erro/direção declarados. Enquanto o motor não carregar trajetória
  nominal explícita por componente, a rota central é **A (real exata)**. NÃO aplicar em companhia
  com poder de preço sem normalização (o g já contém reajustes — corrigir contaria a inflação em
  dobro). "Driver acompanha a inflação" continua hipótese: congelado × acompanhando são as duas
  âncoras da dupla entrega (§7).

**Crescimento perpétuo (gp), quando a convenção `gordon` for usada** (a `convergencia` é invariante a gp por construção).
`gp = meta de inflação de longo prazo da moeda + crescimento real declarado`, ambos com fonte.
Nunca um número redondo escolhido por conveniência. `gp < custo de capital` é obrigatório.

**CAP (n).** 10 anos como base. Régua empírica (Mauboussin/Rappaport, *Expectations Investing*):
CAPs implícitos de mercado agrupam-se em 5–15 anos, chegando a ~30 para posições competitivas
fortes. **15–20 exige DOIS observáveis, coletados em §1:** penetração do endereçável < ~50% do
teto comparável E evidência de vantagem em curso (share estável/subindo sob ataque,
NPS/engajamento líderes) — "moat" sem observável não estica CAP. Abaixo de 10 para ativos
depletáveis (limite: vida de reserva) ou contratos com prazo definido. **Se o moat é perpétuo por
natureza — royalty, stream, concessão sem termo —, o CAP NÃO resolve: a resposta é a convenção de
TV.** Esticar o horizonte explícito não substitui a decisão sobre se o spread morre — mas note a
correção da v8: o teto "nem CAP longo alcança" é propriedade da `book` com ROIC fixo, e mesmo
nela o teto SOBE com o CAP (n=10: ~9,8x fwd; n=100: ~34x no caso motivador). O argumento correto
contra resolver via CAP não é impossibilidade matemática, é implausibilidade econômica do n
implícito — reporte o n necessário e discuta a plausibilidade. Lembre de §6.5 do paper:
CAP e convenção terminal são a mesma pergunta parametrizada de duas formas — **não faça
sensibilidade nas duas ao mesmo tempo**, é dupla contagem.

**Rentabilidade marginal: sempre marginal, nunca contábil.** O ROIC/ROE contábil pode estar
inflado por (a) efeito vintage — ativos comprados barato rendendo a preços correntes; (b) ciclo —
nível alto do driver inflando o numerador sobre capital histórico fixo; (c) alavancagem pré-evento
de capital; (d) capital fora do balanço (investimento despesado — Gate 0). A fórmula usa a
rentabilidade só via RiR = g/ROIC (capital necessário por unidade de crescimento): o que importa é
o retorno do capital NOVO em condições mid-cycle.

**As três camadas do RiR (v9.15) — o motor recebe a do meio.**
- **RiR contábil** = 1 − payout observado. Com payout ≈ 0 é 100% POR CONSTRUÇÃO e
  **não-informativo** sobre o custo do crescimento (o motor avisa quando retenção ≥ 95%). Só
  informa quando existe payout: aí retenção observada ≈ retenção requerida é evidência real, e a
  derivação robusta ROIC_fórmula = g / RiR_observado (RiR = deployment anual / NOPAT) vale.
  **Exceção (v9.20): payout definido sobre base ≠ lucro** — política de proventos como % do
  EBITDA, da receita ou valor fixo desacopla o dividendo do lucro (paga igual em ano de
  prejuízo), e a retenção observada vira não-informativa MESMO com payout > 0: proibida como
  âncora; ancore no deployment de crescimento do DFC ou no guidance, com a troca declarada
  (jurisprudência J14).
  **Segunda exceção: período-base em CONTRAÇÃO.** Deployment medido num período de receita caindo
  é não-informativo com o SINAL invertido: em contração, com giro positivo, o capital de giro é
  LIBERADO e o "capital consumido" observado subestima (ou inverte) o custo de crescer. O pacote já
  conhece o fenômeno pelo lado da modelagem — o bloco de colheita do §8f; esta exceção é o mesmo
  fato aplicado ao lado do INPUT. **Delator: Δreceita ≤ 0 na janela do deployment (≥ 12 meses).**
  Teste secundário, válido para os DOIS sinais de giro: `ΔWC/Δreceita` deve ficar próximo de
  `WC/receita` em razão e em sinal — divergir indica que o deployment observado não mede
  intensidade marginal. (Note que o teste ingênuo "sinal de ΔWC diferente do sinal de Δreceita"
  seria falso positivo em toda companhia de giro NEGATIVO, onde crescer reduz o giro por
  construção.) Disparado o delator, a rota é §11.1c.
- **RiR requerido** = capital que o g de fato consome ÷ lucro da MESMA base (regime A ou B do
  teorema da base coerente — SKILL.md, Gate 0). Do consumo, EXCLUI-SE deployment autofinanciado
  por passivo próprio: funding de carteira de crédito, depósitos, securitização, float — capital
  que o acionista não financia não entra no RiR equity-side. **É este que entra no motor.**
- **RiR discricionário** = opções de crescimento que a companhia pode ou não exercer (expansão de
  carteira além do orgânico, M&A programático). Nunca no g: modelar como degrau/opcionalidade
  (§8) com probabilidade, ou excluir declarando o upside.

**Decomposição do g por componente (v9.25) — o espelho do lado do crescimento.** A v9.22 decompôs o
custo do crescimento (RiR = RiR_fixo + RiR_wk); esta regra decompõe o próprio crescimento. Gatilho:
**qualquer projeção NOMINAL** — que, por prática de mercado, já embute repasse de inflação no preço
(a regra de custo de capital acima reconhece: "o g já contém reajustes"). Decomposição declarada: g = g_volume + g_preço, com
g_preço = inflação × repasse + preço real (repasse ∈ [0, 1], declarado; os extremos repasse 0 e 1
SÃO as duas âncoras congelado × acompanhando da dupla entrega do §7 — mesmo eixo, agora nomeado).
Acoplamento: capital FIXO só é cobrado pela expansão do VOLUME de vendas — planta fabril e
capacidade instalada não crescem porque o PREÇO do produto subiu; GIRO é cobrado perna a perna, cada
uma com o índice do SEU fluxo — recebíveis com o preço de venda, estoque com o custo de reposição do
insumo, fornecedores com o custo de compra (funding, sinal oposto) — e o consumo do componente-preço
é o ciclo de caixa (financeiro) ponderado por esses índices, com o SINAL do ciclo: ciclo de caixa
negativo converte inflação de preço em geração de caixa. **Aplica-se a QUALQUER projeção nominal, com o RiR sendo input ou output (v10).** Quando o RiR é
OUTPUT, a decomposição é a rota de derivação; quando é INPUT, ela é o teste de coerência dele — um
RiR que cobra intensidade MÉDIA sobre o `g` inteiro está cobrando fábrica nova para repassar
inflação, e o delator é comparar a intensidade marginal implícita `RiR×NOPAT/(g×receita)` com a
decomposição por perna, declarando divergência acima de 10%. (A redação anterior restringia a regra
ao caso "RiR derivado" e com isso se autoexcluía justamente na configuração em que o erro é
cometido.) Na perna derivada: o blendado é RiR = (g_volume × custo pleno + g_preço
× custo só-de-giro) ÷ g, sobre o g TOTAL — nunca um componente escolhido. Ilustração pela identidade
de abertura deste bloco: custo pleno = (capex fixo de crescimento + Δgiro) ÷ NOPAT; custo só-de-giro
= Δgiro causado pelo componente-preço ÷ NOPAT. RiR OBSERVADO em moeda corrente já nasce blendado por
construção (o deployment efetivo já reflete que o fixo não subiu com o preço) — re-blendar é dupla
contagem, proibido. Fora do gatilho: price-taker normalizado a nível não tem componente de preço no
g (fluxos em preços de hoje; inflação tratada pela rota real exata ou nominal exata). A rota
terminal-only com preço "gratuito" no TV e rentab_TV → ∞ é **aproximação**, não Fisher equivalente:
é o caso-limite desta regra com giro ≈ 0 e pode ser exata para royalty/streaming; em price-taker com
giro material, a inflação de preço consome giro pelo ciclo ponderado, ou declara-se a direção — a
aproximação terminal-only tende a superestimar quando o ciclo de caixa é positivo);
na rampa, o g₁ da forma fechada e o delimitador são volume por âncora física, e o componente de
preço "declarado à parte" (compressão 2 do §8f, texto vigente) segue esta regra — giro sim, fixo
não. Em base real, o componente de preço é só o real acima da inflação. Duas omissões, duas
direções: RiR pleno sobre g nominal subestima o valor; giro zero sobre o componente-preço
superestima em ciclo de caixa positivo e subestima em ciclo de caixa negativo.
**Acoplamento inegociável com o `d` (v10).** Dizer que o componente de PREÇO não consome capital
FIXO é correto e incompleto: a inflação não expande a planta, mas eleva o CUSTO DE REPOSIÇÃO da
planta existente — e esse custo pertence ao `d`, não ao RiR. Declarar a decomposição do `g` e
manter um `d` de D&A contábil a custo histórico faz a inflação do estoque de capital desaparecer do
modelo inteiro. Por isso a decomposição só é legítima com o `d` vindo de rota em moeda CORRENTE
(capex de manutenção observado, deployment recente, guidance) ou com a guarda de moeda do `d`
(§2, item v) aplicada. As duas regras se leem juntas ou nenhuma das duas está certa.

Nota de consistência com a derivação (`derivacao.md` §1): a fórmula usa a retenção NECESSÁRIA
g/ROE — "payout emerge endogenamente do sweep de caixa". A retenção observada é um check contra
essa necessidade, e o check é VAZIO quando payout = 0.

**Verificação executável (v9.11).** Passe `--rir-observado` e o motor confronta o RiR de
deployment contra o g/ROIC do vetor. Divergir é legítimo — a planilha de referência exibe 42,2%
observado contra 32,0% da fórmula — mas a divergência sai declarada, com a leitura escolhida: g
defasado do capital já comprometido (crescimento de RiR = 0, paper §6.9), ou rentabilidade
marginal do capital novo diferente da do vetor, ou (v9.15) retenção não-informativa por payout
zero. O que o gate proíbe é ficar calado. Junto com `--roe`/`--roic`, `--kd`, `--gde`, `--nde` e
`--ebitda-ic`, fecha as quatro identidades do Gate 0 do `SKILL.md`.

**Gate de qualidade do capital investido — Gate 0 do SKILL.md.** Pergunta registrada na trilha:
*P&D, aquisição de clientes, software, marca são despesa ou investimento econômico?* Expensar
investimento produz quatro erros na MESMA direção (NOPAT reduzido, capital omitido, ROIC médio
inflado, reinvestimento oculto). O denominador captura o capital ECONÔMICO: deployment = capex de
crescimento + ΔWC + intangíveis capitalizáveis (R&D e a parte de S&M que constrói ativo, mesmo
despesada). **ROIC alto com book pequeno e R&D/S&M altos = capital fora do balanço** — a empresa
"reinveste via DRE" e o RiR = g/ROIC subestima o reinvestimento real: derive o marginal pelo
deployment TOTAL, ou declare ROIC contábil-estreito com a direção do viés (valor superestimado).
A escolha de regime (A × B) que isto abre é o teorema da base coerente (SKILL.md, Gate 0).

**Classificação da qualidade do capital investido (v9.7 — obrigatória sob `book`).** Classifique
o book em: `reportado` (balanço como está), `ajustado` (correções pontuais declaradas — leases,
provisões, PPA), `reconstruído` (capital econômico remontado, intangíveis capitalizados via
deployment — parágrafo acima), `proxy` (aproximação declarada com direção de viés) ou
`nao_confiavel` (write-offs relevantes, aquisições em série, inflação acumulada, intangíveis
dominantes não reconhecidos, diferenças de GAAP). Regras: (i) `nao_confiavel` ⟹ a convenção
`book` NÃO pode ser cenário-base — permanece disponível como sensibilidade identificada;
(ii) sem classificação informada, a entrega declara "qualidade do book: NÃO AVALIADA" — nunca
assuma que `reportado` significa confiável; (iii) sob `book`, a classificação entra na memória
de cálculo ao lado do `--roic-book`/`--roe-book`, porque o IC mensurado É o valuation terminal.

**Crescimento (g): decompor orgânico vs adquirido, e nível vs taxa.** Crescimento orgânico já
capitalizado (expansões prontas, ramp-ups, exploração no portfólio existente) tem RiR = 0 — é
gratuito e a fórmula não o precifica; se relevante, cite como upside não capturado, e **nunca**
o adicione a g (corromperia o RiR e o FCFF). Para price-takers: separar volume de nível do driver;
nível NÃO é g (ver §7 e §8).

**Elasticidade dos drivers (derivar com SINAL, nunca arbitrar).** Com volume e demais linhas
fixos no curto prazo, EBITDA = R − C, logo a elasticidade ao driver é alavancagem operacional
pura: `elasticidade = linha exposta ÷ métrica-base`, onde a linha exposta é a que se move
1-para-1 com o driver. **O sinal vem do lado da DRE:** driver de RECEITA (commodity vendida,
take-rate, tarifa regulada, preço realizado) entra positivo; driver de CUSTO (frete, energia,
insumo, câmbio no COGS, spread de captação no lado passivo) entra NEGATIVO — e a linha exposta é
o custo do insumo, não a receita total. Gate cego ao sinal soma o que deveria compensar: uma alta
de 20% no preço do produto com alta de 40% no insumo não são 60% de impacto, e o registro reporta
o líquido (com sinal) ao lado da soma dos brutos justamente por isso. Derive sempre que a linha
exposta for separável (segmento, produto, contrato, nota de custos). Só declare um número à mão quando não houver como derivar
— e diga por quê, porque elasticidade chutada é o maior buraco de determinismo que resta: muda o
gate, muda quem vira cenário e muda o nível normalizado.

**Composição: aditiva por construção, e a linearização quebra na MESMA linha exposta.** O registro
soma os efeitos individuais, o que é correto quando as linhas expostas são DISJUNTAS. Dois drivers
que atuam sobre a MESMA linha compõem-se multiplicativamente — o efeito conjunto é (1+g₁)(1+g₂)−1,
não g₁+g₂ — e a soma erra tanto mais quanto maiores os gaps e quanto mais as linhas expostas
diferirem de tamanho (câmbio sobre toda a receita dolarizada, preço sobre um produto só). Regra:
drivers sobre a mesma linha entram como **UM driver único, já composto na moeda e na unidade em que
a companhia REALIZA** — preço da commodity em moeda local na porteira, não preço em dólar mais
câmbio. Decompor é legítimo para narrar; somar, não. Quando a decomposição for necessária porque as
linhas expostas têm tamanhos diferentes, calcule o efeito POR LINHA e leve ao registro a soma dos
efeitos em MOEDA, nunca a soma dos impactos percentuais.

**Base nominal vs real — invariante de coerência, declare e não misture.** Esta é uma convenção
obrigatória de consistência, **não uma 12ª bifurcação econômica**: uma conversão nominal↔real feita
integralmente não deve, por si só, criar ou destruir valor. `g`, gp, rentabilidade e custo de capital
têm que estar na mesma base.
O erro caro: `g` nominal (que embute inflação) combinado com rentabilidade contábil calculada sobre
capital a custo histórico não reajustado. O ROIC sai inflado, o RiR = g/ROIC subestima o
reinvestimento necessário, e o valor infla — o mesmo mecanismo da armadilha do ROIC de pico, por
outra porta. Duas saídas, escolha e declare:
- **Nominal:** exige capital reajustado, ou a rentabilidade derivada de `g/RiR` a partir do
  deployment em moeda corrente — que é imune ao problema, porque numerador e denominador estão na
  mesma moeda do período. Só é exata quando **todos** os fluxos explícitos foram nominalizados
  de forma coerente.
- **Real:** `g` real e rentabilidade real, com `gp` real; converta ao final se o preço for nominal.
  **É a rota central enquanto a trajetória nominal explícita por componente não estiver modelada integralmente.**
Sinalize sempre que a inflação acumulada do período-base for material — nesse caso, a rentabilidade
contábil deixa de ser comparável à marginal e a diferença entre elas não é vintage, é indexação.

**Caixa remunerado no Gate ROIC↔ROE.** Se `Cash/E = D/E − ND/E > 0`, descubra se o LL/ROE
informado inclui rendimento desse caixa. Se SIM, a reconciliação exige `Kcash(1−t)×Cash/E`; passe
`--cash-yield` bruto. Se NÃO houver essa separação, o gate produz falso gap. A rota preferida é
normalizar o LL excluindo resultado financeiro de excess cash, valorar a operação e adicionar o
caixa separadamente. Nunca usar caixa remunerado para "explicar" ROIC operacional.

**Contabilidade (d e t).** d = D&A como % do EBITDA do ano-base; cuidado — D&A absoluta não escala
com o nível do driver (é por unidade produzida), então d cai quando o driver sobe. Decomponha o d
quando houver contaminação: depletion (depletáveis) e amortização de direitos minerários seguem
produção; amortização de arrendamento IFRS-16 é aluguel reclassificado (coerência: ou EBITDA
pré-IFRS-16 com aluguel no custo, ou d incluindo a amortização + dívida de arrendamento no ND —
nunca meio a meio); amortização de PPA de aquisições é não-caixa sem capex de reposição
correspondente e infla o d economicamente relevante — declare o d ajustado e o contábil.

**Teste de NATUREZA do d, antes do teste de composição (v9.12).** Decompor o d diz de *onde* ele
vem; falta a pergunta anterior, que é o que decide se ele fica: **"para manter o volume, a companhia
precisa comprar outro ativo igual?"** Quando a D&A é a amortização do PRÓPRIO ativo gerador de
receita e o custo de reposição é outro ativo da mesma natureza — royalty, catálogo musical, carteira
de patentes, direitos autorais, licença explorada até a exaustão —, o d é **economicamente real** e
NÃO deve ser ajustado para fora: a depleção é o capex de reposição, apenas com outro nome e outro
timing. É o oposto exato do PPA, que é não-caixa justamente porque não há ativo a repor. Confundir
os dois inverte o sinal do ajuste (jurisprudência J4). t = alíquota
efetiva média recente; se a efetiva do período divergir muito da estatutária, investigue a causa
(JCP, incentivo, crédito tributário) e declare se é recorrente — alíquota efetiva baixa e não
recorrente é lucro de baixa qualidade fiscal, e a premissa correta é a estatutária ajustada.
**Convergência no terminal (v10.1).** Diferimentos, incentivos com prazo, prejuízo fiscal acumulado e
crédito tributário são, por natureza, temporários: em estado estacionário a alíquota EFETIVA tende à
MARGINAL. **Limitação do motor, declarada:** `t` é parâmetro ÚNICO aplicado ao explícito E ao
terminal, então não há como diferenciar as duas fases dentro de uma rodada. Duas saídas, escolha e
declare: (a) usar a marginal ajustada no caso-base — rota conservadora, e a prescrita para
crescimento estável —, com a efetiva corrente como sensibilidade; ou (b) usar a efetiva e declarar
por escrito qual benefício é ESTRUTURAL e por que sobrevive à perpetuidade. Divergência efetiva ×
marginal acima de ~5 p.p. sem essa declaração é premissa silenciosa: no caso de referência foram 25%
contra 34%, e a diferença valia ~7% do valor.

**Contraprova de caixa do `d` (v10) — a segunda rota, obrigatória.** A natureza (acima) decide se o
`d` FICA; a contraprova decide se o NÚMERO mede o custo de repor. Razão econômica em uma frase: o
encargo de reposição é o que a companhia gasta para não encolher, e isso é fluxo de caixa
observável — a D&A contábil é apenas uma proxy dele, com vintage e vida útil embutidos.
Procedimento: (i) tomar a distribuição divulgada do capex e classificar as rubricas — sustentação,
manutenção, adequação a normas, revitalização e modernização de infraestrutura EXISTENTE são
MANUTENÇÃO; expansão de capacidade, novos produtos e transformação digital são CRESCIMENTO;
(ii) somar as rubricas de manutenção sobre o capex do ano; (iii) somar a amortização de direito de
uso quando o EBITDA for pós-IFRS-16, sob pena de comparar bases diferentes; (iv) reportar o gap
contra a D&A.
**O gap não se lê sozinho — cruze com a idade do parque.** Sob inflação, a manutenção verdadeira
DEVE exceder a D&A a custo histórico: a igualdade capex = depreciação só é apropriada num mundo sem
crescimento E sem inflação, e a evidência de longo prazo do mercado americano mostra capex
excedendo depreciação em ~16–21% na média (McConaughy & Bordi 1986–2001; levantamento NYU/Stern
2018; discussão em Matthews & Rosenbloom sobre a presunção contrária no Delaware). Consequência
operacional: **D&A ≈ manutenção em termos NOMINAIS valida o `d` quando o parque é novo** (capex
recorrente ≫ D&A, idade média baixa) e é **sinal de reposição adiada quando o parque é velho** — e
essa leitura é a mesma da guarda de moeda do `d` (item v abaixo), com a qual não pode conflitar.
Gap > 10% sem essa leitura ⟹ o `d` é hipótese de construção, e a direção do erro vai à entrega:
manutenção de caixa < D&A ⟹ o `d` superestima o encargo e o valor dos ativos instalados está
subestimado; manutenção > D&A ⟹ o inverso, e registre a reposição adiada. **Quando a companhia não
divulga a distribuição do capex**, a contraprova não é executável: declare isso, use o `d` contábil
e mova o resultado para a faixa de sensibilidade do §11.7. **Não é escolha metodológica nomeada** —
é medição por duas rotas, e a lista permanece em onze.

**Conservação de capital d×RiR (v9.19) — o teorema da base coerente, agora no lado do capital.**
O encargo de reposição e o reinvestimento são duas metades do MESMO capital consumido:
`capex_total + ΔWC = d×EBITDA + RiR×NOPAT` (identidade da definição de FCFF; vale em estado
estacionário, com d e RiR na MESMA base). Quatro regras:
(i) **Quadrantes proibidos, mesmo desenho do Gate 0:** `d` de caixa (capex de sustentação) com
RiR líquido da D&A contábil não cobra reposição em lugar nenhum; `d` contábil com RiR de capex
bruto cobra o mesmo capital duas vezes. Escolhido um `d` econômico ≠ contábil, o RiR
**re-deriva na mesma base** — nunca se herda o RiR do par antigo.
(ii) **Sensibilidade em `d` NUNCA congela o triângulo.** Mover d move o RiR coerente pela
identidade; grade de d com g/ROIC/RiR fixos infla a amplitude e responde à pergunta errada
(jurisprudência J12: faixa congelada R$ 0–22 contra coerente R$ 12–22).
(iii) **D&A-overhang (fim de ciclo de investimento):** D&A contábil > capex_total torna o RiR
canônico negativo e o vetor NÃO representável (g > 0 exige RiR > 0). Migre o **PAR inteiro**
para base caixa — d = capex de sustentação ÷ EBITDA; RiR = deployment de crescimento ÷ NOPAT
da mesma base — e reporte a identidade como verificação (§11.1b), com a direção do erro se a
D&A convergir ao capex mais rápido/devagar que o assumido.
(iv) **O ano-base do capex é premissa declarada.** A identidade converte "qual d?" em "qual
estado estacionário de capex?" — corrente × guidance de longo prazo são os dois ramos da
escolha metodológica correspondente (SKILL.md, item 4), cada um com seu par (d, RiR) coerente.
Verificação manual na cadeia §11.1b; confronto executável no `ev` via `--capex-total` e `--dwc`
(v9.24) — gap > 10% sai com o alerta de reclassificação.
(vi) **Sinal do ciclo de caixa (v10).** Toda a mecânica acima pressupõe implicitamente giro
POSITIVO. Com giro NEGATIVO — fornecedor e adiantamento financiando o cliente: varejo alimentar,
marketplace, companhia aérea, assinatura pré-paga, float de seguro — o componente de giro do
reinvestimento é NEGATIVO, crescer é parcialmente autofinanciado e ENCOLHER consome caixa. A
álgebra é a mesma; o que muda é o sinal de `wk`. Consequências: o delator de RiR > 100% perde poder
(o RiR agregado pode ser baixo ou negativo sem que o capital fixo esteja barato) e o teste migra
para o componente FIXO isolado; e o bloco de colheita do §8f inverte de sentido. Verifique o sinal
ANTES de nomear qualquer bloco.

(v) **Guarda de moeda do d (v9.25).** A moeda do dado de origem decide, não a rota da derivação: d
derivado de fluxo em moeda corrente — capex de sustentação observado, deployment recente do DFC,
guidance, unit economics — já está a preços de hoje e **é proibido ajustar por inflação** (ajustar
seria dupla contagem: a taxa nominal já desconta um fluxo corretamente nominal). O único caso de
ajuste é d que seja, em substância, D&A contábil pura a custo histórico, E com inflação acumulada
sobre a idade média do parque material — âncora de materialidade: ~15% acumulado (fator ≳ 1,15);
abaixo, declare e siga sem ajuste. Dentro do gatilho duplo, a proxy entra a custo de reposição
(fator ≡ inflação do bem de capital acumulada sobre a idade média; idade média ≈ depreciação
acumulada ÷ D&A anual, ambas só dos ativos ainda em depreciação — ativo totalmente depreciado em
operação é aviso de reposição adiada: registre). Fora do gatilho duplo, nada muda; dentro dele,
ajustar ou declarar a direção (proxy contábil pura superestima o valor) — nunca o silêncio.

**Declaração de fronteira EV/EBITDA (v9.7 — obrigatória quando a base é EBITDA).** A ponte
(1−d)(1−t) é o elo fraco declarado do framework (paper §2.4); nenhuma saída EV/EBITDA vai à
entrega sem declarar: EBITDA pré ou pós-IFRS-16 (e a coerência com o EV — dívida de arrendamento
dentro OU aluguel no custo, nunca meio a meio); amortização de PPA e depletion no d (contábil vs
ajustado, do parágrafo acima); SBC tratada em separado (é despesa econômica recorrente — EBITDA
"ajustado" que a exclui superestima a base); EBITDA reportado vs ajustado (e o que o ajuste
remove); alíquota normalizada; fronteira de consolidação (JVs, minoritários — a métrica e o EV na
MESMA fronteira); capex de manutenção quando a leitura econômica do d depender dele. O que não
for declarado entra na trilha como "não avaliado", nunca como implícito.

**Gatilho de elevação da fronteira (v9.20).** Participação de não controladores > ~20% do PL
consolidado, ou veículo de coinvestimento consolidado materialmente relevante (SPE/JV com sócio
externo), ⟹ a fronteira de consolidação deixa de ser item de checklist e vira **escolha
metodológica nomeada** (a 9ª — SKILL.md, item 4): a bifurcação é **por quanto** levar a
participação de terceiros ao EV — valor CONTÁBIL do balanço × valor ECONÔMICO estimado (p.ex.
o múltiplo justo aplicado à fatia, ou marca de transação recente do próprio veículo) —, ambos os
ramos precificados com a diferença em moeda. Ignorar a participação com métrica consolidada NÃO
é ramo — é erro: avalia fluxo que não pertence ao acionista (jurisprudência J13: 0,9x de múltiplo
de tela e 30% do preço). O gatilho também dispara o teste de multi-segmento do §12.
