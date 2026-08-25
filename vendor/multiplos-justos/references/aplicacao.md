# Playbook: aplicando o framework a uma companhia real

Leia este arquivo SEMPRE antes de rodar valuation de empresa real. Ordem de trabalho:
pesquisar → gate de nível (dois braços) → derivar premissas pelas REGRAS TRAVADAS (§2) →
escolher convenção de TV → grade canônica de cenários → reversa (inclusive em nível) →
tabela → apresentar → bloco de inputs → encerramento.

**Princípio de determinismo:** a mesma companhia, rodada em sessões diferentes, deve chegar
às mesmas conclusões. O motor já é determinístico; a variância mora na derivação de premissas.
Por isso este arquivo trava **regras**, não números — a regra atravessa o tempo, o número não.
Onde a regra não decide, a premissa é declarada como hipótese de construção e vai para a reversa.

## 1. Pesquisa (sempre — nunca números de memória, nunca herdados)

Buscar: último trimestre e último anual (receita, EBITDA ajustado e margem, depletion/D&A,
alíquota efetiva, lucro); guidance do ano e outlook plurianual (volumes!); preço atual,
market cap, nº de ações (e classes, se houver mais de uma); caixa, dívida, equity investments;
capital deployado nos últimos 2 anos (para RiR); folga de capacidade/capital regulatório; e o
SPOT ATUAL de TODOS os drivers exógenos, com data e fonte. Ordem de fontes: dado licenciado/
conector → press releases/filings da companhia → agregadores/web.

**Coleta adicional obrigatória (v9.15):**
- **Consenso**: receita e EPS/LL para o ano corrente, t+1 e t+2, com data e nº de analistas;
  price target médio e faixa. Fonte agregadora serve; registre a data (consenso pós-resultado
  difere do pré). Alimenta o confronto temporal da reversa (§4) e a seção Estimativas da entrega.
- **Margem estrutural**: margem operacional dos 2–3 anos pré-ciclo de investimento, quando houver
  ciclo declarado (alimenta o regime B do teorema da base coerente — SKILL.md, Gate 0).
- **Runway**: penetração do mercado endereçável e share, sempre que CAP > 10 for candidato.
- 2–3 leituras de sell-side/imprensa especializada sobre bull/bear case e competição (alimentam a
  seção Negócio & indústria e o teto de normalização de margem — competição pode tornar parte do
  "investimento" permanente).

**Não existe premissa herdada.** A skill não guarda casos e não reaproveita análise anterior.
Se o usuário fornecer um bloco de inputs de sessão passada, revalidar obrigatoriamente preço,
spot dos drivers, base de capital e existência de resultado novo — e declarar o que foi
revalidado.

**Checagem de vintage de capital (obrigatória).** Antes de usar qualquer ROE/ROIC de LTM ou TTM,
verifique se a base de capital mudou ≥ 10% nos últimos 12 meses: IPO, follow-on, recompra
relevante, baixa contábil, aquisição paga em ações. Se mudou, **o indicador de LTM é inválido** —
numerador de uma empresa, denominador de outra. Recalcule a rentabilidade sobre a base de capital
ATUAL, usando lucro anualizado do trimestre mais recente e/ou consenso, e declare qual usou.

## 2. Regras travadas de derivação de premissas

O objetivo é que dois analistas, com os mesmos dados públicos, cheguem ao mesmo input. Cada regra
abaixo é obrigatória; desviar dela exige declarar o desvio e o motivo.

**Custo de capital (a maior fonte de variância — travar sempre).**
`Ke = rf + β × ERP`, com:
- `rf` = taxa livre de risco observável na moeda dos fluxos, com fonte e data. Para fluxos em BRL
  nominal, a taxa básica corrente ou o vértice longo da curva nominal — declare qual e por quê.
- `ERP` = prêmio de risco do mercado de listagem/operação, com fonte e data.
- `β` = beta observado quando existir histórico suficiente. **Se não existir** (IPO recente,
  liquidez baixa), usar beta de pares diretos do mesmo modelo de negócio e declarar os pares —
  nunca escolher um número "razoável" sem lastro.
- **Canal do risco-país — escolha UM e declare (v9.15):** (i) β contra índice local/amplo + ERP
  maduro + CRP explícito ponderado por LUCRO (não receita); ou (ii) β do ADR contra o índice do
  mercado de listagem + ERP maduro, SEM CRP adicional — a covariância medida em moeda forte já
  embute parte do risco-país, e empilhar CRP por cima conta duas vezes. Empilhamento é PROIBIDO
  como estimativa central; admissível só como extremo declarado da banda de sensibilidade (que
  segue ±200 bps quando o prêmio-país é volátil). Jurisprudência J8: +2,3 p.p. empilhados =
  −35% de valor sem violar nenhuma regra da v9.14.
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
- **RiR requerido** = capital que o g de fato consome ÷ lucro da MESMA base (regime A ou B do
  teorema da base coerente — SKILL.md, Gate 0). Do consumo, EXCLUI-SE deployment autofinanciado
  por passivo próprio: funding de carteira de crédito, depósitos, securitização, float — capital
  que o acionista não financia não entra no RiR equity-side. **É este que entra no motor.**
- **RiR discricionário** = opções de crescimento que a companhia pode ou não exercer (expansão de
  carteira além do orgânico, M&A programático). Nunca no g: modelar como degrau/opcionalidade
  (§8) com probabilidade, ou excluir declarando o upside.

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

**Base nominal vs real — invariante de coerência, declare e não misture.** Esta é uma convenção
obrigatória de consistência, **não uma 11ª bifurcação econômica**: uma conversão nominal↔real feita
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

## 3. Convenção de TV — a decisão que mais move o valor

**A escolha é pela DURAÇÃO ECONÔMICA do claim, não pelo rótulo do setor nem pela conveniência do
número, e é o Gate 1 do SKILL.md.** O motor exige `--tv` explícito e não tem default. São três
convenções (ver `derivacao.md` §3); declare a escolhida E a hipótese que ela carrega na entrega.
- **`book`** (ex-`ic`): o NOPAT inteiro colapsa para W×IC — TV ancorado no capital investido
  MENSURADO; ler como fim de TODA renda econômica exige book confiável (classificação do §1) e é
  hipótese mais dura que a exaustão no capital incremental. O colapso ocorre no ano n+1 e o TV é o
  capital investido. Adequada quando o book é âncora crível de saída (price-taker de commodity,
  regulado com base de remuneração). **Enterprise:** `--roic-book` é a média **inicial/forward** do
  estoque, temporalmente alinhada a NOPAT₁: `IC₀ = NOPAT₁/ROIC_book`. Se a fonte for ROIC trailing,
  reconcilie-a para essa base antes de usar. Quando marginal ≠ médio, o TV é o IC **ACUMULADO**:
  parte de IC₀ e recebe o capital novo ao ROIC marginal; o retorno médio no ano n é output, não
  parâmetro congelado. **Equity [v9.30]:** `--roe-book` acumula o patrimônio por
  clean surplus. A forma fechada de E_n coincide com a do firm, mas o valuation `book` é
  **Div + E_n**: `Div_t = LL_t − ΔE_t = LL_t(1−g/ROE_marg)`. O termo `+Δcaixa` do módulo FCFE
  não entra nesta convenção porque o caixa retido já está em E_n; somá-lo de novo é dupla contagem.
  Assim, Caixa/E é neutro na `book` e excess cash/rendimento de caixa deve ser tratado separadamente.
- **`convergencia`**: só o capital NOVO deixa de criar valor (RONIC = W); o NOPAT existente é
  preservado; TV = NOPAT/W. Exaustão da vantagem NO CAPITAL INCREMENTAL — as rendas dos ativos
  existentes não são eliminadas (o desaparecimento total é a `book`). Não referencia o book
  nem gp. Na dúvida entre "a vantagem acaba" e "o negócio vira medíocre nos projetos novos",
  esta é a convenção — a `book` assume bem mais que isso.
- **`gordon`** (ex-`spread`): ROIC_TV e gp livres. Claims de LONGA DURAÇÃO (royalty, streaming,
  rede, marca dominante) justificados pela duração — um contrato com termo de 15 anos é horizonte
  explícito longo, não perpetuidade; e um regime declarado de ROIC_TV < W é legítimo para
  destruição persistente. **Rentabilidade terminal (`--roic-tv`/`--roe-tv`) = a MARGINAL
  TERMINAL (RONIC/ROIIC)**: gp/ROIC_TV é o RiR do capital NOVO que sustenta gp — é o retorno
  incremental que a álgebra exige (v9.8, C-01). NÃO perpetue o marginal do EXPLÍCITO (regra do
  degrau: a rentabilidade terminal não acompanha, paper §6.10); o blended do portfólio é proxy
  ADMISSÍVEL só sob hipótese DECLARADA de estado estacionário com médio e marginal convergidos —
  declare a hipótese e a direção do erro: blended > RONIC real ⟹ RiR subestimado ⟹ TV
  SUPERESTIMADO (caso maduro comum); inverte se RONIC > blended. No lado equity com caixa ≠ 0, declare a política de caixa no terminal:
  `--politica-tv continua` (default, FCFE canônico — a proporção de caixa segue na perpetuidade)
  ou `encerra` (a política morre no ano n); a escolha move 2–6% do P/L e sai no diagnóstico.
- **Se rentabilidade marginal < custo de capital, o caminho depende de haver book separado.** SEM
  book separado, a `book` conflaciona médio×marginal e pode premiar o destruidor de valor (o TV cresce
  quando a variável única de retorno cai): separe os papéis ou use `gordon` com rentabilidade
  terminal ABAIXO do custo e declare o spread negativo persistente. **Enterprise, com
  `--roic-book`:** o TV parte de IC₀ e acumula o capital novo ao marginal; com g>0, elevar apenas o
  marginal eleva o valor. A raiz é CONDICIONADA à tese declarada de saída pelo capital investido
  (turnaround, capex regulatório, reconstrução operacional, liquidação). Isso não torna toda reversa
  unívoca: o gradiente em g tem sinal do spread na **base forward**, mas a base corrente pode ter
  máximo interior e duas raízes. **Equity, com `--roe-book`:** o patrimônio parte da média
  inicial e acumula o lucro retido ao marginal. Na `book`, Caixa/E não altera o valor por si só;
  o fluxo é dividendo e o terminal é E_n. Se o próprio book estiver abaixo do custo, some o
  sub-alerta de RECUPERAÇÃO.

**Teste do teto — procedimento, não impressão.**
```
1. rev --resolver cap --alvo <múltiplo de mercado> --tv book ...
2. Saiu "incompatível com estas premissas sob esta convenção"?
   NÃO  -> a `book` reconcilia o preço; siga com ela e reporte o CAP implícito (interpolado,
           condicional às demais premissas).
   SIM  -> ANTES de trocar de convenção, cheque o Gate de nível (§7 e §8): o problema pode ser
           nível defasado ou degrau não modelado, não a convenção. Inverter essa ordem é o erro
           mais caro da sequência.
3. Nível descartado e ainda incompatível -> a franquia está sendo percebida como mais longa que
   a convenção. Rode `convergencia` (o meio-termo: preserva o NOPAT, mata o valor do capital
   novo) e, se o claim justificar por DURAÇÃO, `gordon` com:
     rentabilidade terminal = o RONIC/ROIIC TERMINAL — o retorno do capital novo que sustenta
       gp (é ele que entra em gp/ROIC_TV). NÃO o marginal corrente do explícito (perpetuá-lo
       superestima o TV — quanto maior o R, menor o RiR imputado); o blended entra só como proxy
       declarada de convergência médio↔marginal no steady state, com a direção do erro anotada.
     gp = 2–4%, pela regra de §2, sempre < custo de capital.
4. Rode as convenções candidatas e mostre os gaps: cada gap é a parte do valor que depende da
   hipótese terminal correspondente (book→convergencia: preservação do NOPAT existente;
   convergencia→gordon: perpetuidade do spread no capital novo).
```

**Antes de qualquer reversa contra múltiplo de tela — trave a BASE (D2).** Múltiplo de tela vem
em TTM (corrente) ou NTM (forward), e as duas diferem por (1+g): a 12% de crescimento, confrontar
um NTM contra a base corrente do motor injeta 12% de erro no alvo, que volta como premissa
implícita falsa e com cara de precisão. Registre a base da fonte com data, e rode
`rev --alvo-base forward` quando a tela for NTM. O motor ecoa a base usada no output; se a fonte
não declara a base, isso é lacuna de dado — trate como tal, não como detalhe.

**Regra transferível:** um múltiplo de tela incompatível na variável economicamente relevante é
evidência sobre a convenção (ou sobre o nível), não veredicto sobre o preço. Quem defende múltiplo
alto por rentabilidade alta está, sem saber, assumindo claim de longa duração — e é essa premissa
(a duração) que precisa ser defendida, não o múltiplo. Simetricamente: o teto famoso ("nem CAP
longo alcança o múltiplo") é propriedade da `book`; sob `convergencia` o teto sobe com o CAP e a
afirmação não se transfere.

## 4. Grade canônica de cenários e reversa

**Cenários não se inventam: derivam-se de âncoras observáveis.** Quatro cenários, sempre nesta
ordem e sempre declarando a âncora de cada um:

| Cenário | Âncora obrigatória |
|---|---|
| Piso / trough | **o MENOR entre** (i) o run-rate anualizado do trimestre mais recente sobre a base de capital ATUAL e (ii) a média normalizada do período-base — ver a trava abaixo |
| Base | ponto médio entre trough e consenso, OU a média do próprio histórico normalizado — declare |
| Alta / consenso | consenso de mercado com data e nº de analistas, ou guidance da companhia |
| Teto | rentabilidade pré-disrupção / pico do ciclo, **rotulada como teto da alavanca, não cenário** |

**TRAVA do piso (v9.12) — em price-taker no TOPO do ciclo, o trimestre recente é o TETO, não o
piso.** A regra "anualize o trimestre mais recente" pressupõe que o último dado é o pior, o que vale
em trough e se INVERTE em pico: anualizar um trimestre que realizou o driver acima do spot empilha o
topo do ciclo no numerador e chama isso de cenário conservador. Antes de usar (i), compare o preço
realizado do trimestre com o SPOT: se o realizado estiver acima, (i) é teto e o piso é (ii).
*Jurisprudência J1: realizado 16% acima do spot — anualizar o trimestre teria produzido um
"piso" acima do cenário-base.*

**Sensibilidades obrigatórias, com amplitude travada pelo tipo de premissa:**
- **Custo de capital:** ±50bps quando o beta é observado e a moeda é forte; ±200bps quando o beta
  vem de pares (sem histórico próprio) ou o prêmio-país é volátil. Declare qual caso e por quê —
  amplitude escolhida sem critério é sensibilidade decorativa.
- **gp: ±50bps sempre que a convenção for `gordon`.** Ali o gp é alavanca de primeira ordem: o TV
  responde pela maior parte do valor e o gp entra no denominador (custo − gp). Omitir essa
  sensibilidade esconde a fragilidade estrutural do resultado.
- **Degrau:** banda de `m` e perfil de transição, quando houver (§8).

Cada cenário com preço/ação pela ponte explícita.

**Menu de reconciliação (v9.17) — a reversa é um cardápio, não um eixo.** O preço admite mais de
uma explicação univariada; entregar uma só é escolher a conclusão. A seção de expectativas
embutidas cobre os eixos APLICÁVEIS, cada um resolvido com os demais no vetor central:
(i) nível do driver implícito (quando houver driver/degrau); (ii) base temporal (confronto com o
consenso — regra abaixo); (iii) g implícito; (iv) rentabilidade implícita e/ou curva iso;
(v) CAP implícito (quando candidato); (vi) **custo de capital implícito — eixo OBRIGATÓRIO em
toda rodada** (`rev --resolver ke|wacc`), traduzido para a âncora externa: beta implícito =
(custo_impl − rf)/ERP, confrontado com a banda histórica do beta observado. Nível e custo de
capital são os DOIS eixos com observável direto de mercado — e o segundo é o mais barato de
esquecer (jurisprudência J10). Depois dos univariados, teste as fronteiras bivariadas plausíveis
(base futura × custo de capital; base futura × regime terminal) e **feche a seção com o
julgamento comparativo: qual reconciliação exige a menor violência às âncoras observáveis — essa
é a que o mercado provavelmente usa — e qual observável a testaria.**

**Dualidade dos eixos de denominador (v9.17).** Custo de capital menor e crescimento de preço
gratuito no terminal comprimem o MESMO spread (custo − crescimento); são quase-duais. Quando os
dois aparecem como explicações candidatas, declare a dualidade — senão o leitor conta o mesmo
eixo econômico como duas evidências independentes (J10: o "regime inflacionário do ouro" e o
"beta no fundo da banda" eram a mesma compressão de spread por portas diferentes).

**Gatilho de duração (v9.17).** Quando custo de capital − g < ~3 p.p., o valor é hipersensível ao
denominador: a reversa em custo de capital roda PRIMEIRO, e a sensibilidade de ±50bps reporta
preço E múltiplo.

Reportar honestamente múltiplas raízes, neutralidades (perto da neutralidade a variável implícita
é ruído numérico com aparência de precisão — sempre reporte a curvatura) e alvos inalcançáveis
com o máximo atingível.

**Confronto temporal obrigatório (v9.15) — antes de qualquer conclusão de fantasia terminal.**
O `nivel` devolve a métrica implícita no preço; confronte-a com o consenso de t+1 e t+2
(coletado em §1; passe `--consenso-t1`/`--consenso-t2` e o motor emite a leitura):
- métrica implícita ≈ consenso t+1/t+2 (até ~+25%, calibrado em J8) ⟹ leitura é **antecipação temporal**: o mercado
  desconta uma base futura — comportamento padrão em fase de investimento (Gate 0.5). A reversa
  correta passa a ser sobre o vetor consenso (ex.: `rev --resolver cap` contra a base t+2) — o
  horizonte implícito de mercado de Rappaport/Mauboussin (*Expectations Investing*): resolver o
  horizonte que justifica o preço dado o consenso, em vez de declarar o preço impossível dado o
  passado.
- métrica implícita ≫ qualquer consenso ⟹ aí sim a hipótese terminal está no preço; siga para o
  teto do crescimento gratuito e o gp implícito (protocolo v9.13, inalterado).
Jurisprudência J8: nível implícito 2,55x o LTM ≈ consenso t+2 — antecipação temporal lida como
fantasia terminal foi o erro que este parágrafo existe para impedir.

**Curva iso-valor.** Quando houver dois vetores de valor de naturezas distintas (ex.: recuperação
de rentabilidade e degrau de capacidade), apresente o conjunto de pares que reconcilia o preço.
Ela converte "está barato?" em "qual dos dois vetores o mercado não está pagando?", que é uma
pergunta testável.

## 5. Escrita e tradução — o relatório fala a língua do mercado (v9.16)

A estrutura, a parede processo×produto e a lista de banimento estão no SKILL.md ("A entrega é um
relatório de research — e um produto de mercado") — aquela seção é a autoridade. Aqui ficam a
tabela de tradução e o exemplo da regra mais violada.

**Tabela de tradução (interno → no relatório):**

| Interno | No relatório |
|---|---|
| convenção `book` | valor terminal ancorado no capital investido (renda residual truncada) |
| convenção `convergencia` | convergência do retorno incremental ao custo de capital — só o capital novo deixa de criar valor; as rendas existentes se preservam (prática McKinsey/Mauboussin) |
| convenção `gordon` | perpetuidade de Gordon com retorno incremental terminal declarado |
| Gate 0 / base coerente / regimes A×B | qualidade do lucro e do capital: lucro reportado × lucro normalizado (investimento despesado capitalizado, à Damodaran), com o reinvestimento derivado da MESMA base |
| Gate 0.5 / fase | estágio do ciclo de capital (investimento / distribuição / misto / híbrido financeiro) |
| Gate 1 / revalidação | hipótese de valor terminal, re-testada depois de derivada a rentabilidade marginal |
| Gate 2 / nível×taxa | representatividade da base: drivers do período-base contra o spot |
| Gate 3 / degrau | alavancas identificadas de lucro (maturação, reversão, religamento) e seu tratamento |
| dupla entrega / bifurcações | sensibilidade às escolhas metodológicas (tabela com o custo de cada escolha) |
| guarda anti-empilhamento | coerência interna dos cenários: caso-base = escolha central em todas; extremos = bear/bull |
| reversa / nível implícito | expectativas embutidas no preço (reverse DCF, Rappaport/Mauboussin) |
| leitura `antecipacao_temporal` | o preço desconta a base de lucro de t+1/t+2, não uma hipótese terminal |
| teto do crescimento gratuito | crescimento sem consumo de capital implícito no preço |
| RiR | taxa de reinvestimento (termo de mercado; mantém) |
| RiR por componente / RiR_wk | o custo de crescer, separado entre capital de giro e capital fixo |
| leitura de capacidade / rampa (§8f) | quanto o parque já construído consegue entregar, e o prazo para chegar lá |
| re-base do encargo de reposição (§8f) | a depreciação fixa diluída pelo parque cheio — eficiência permanente de nível |
| composição de fases / biblioteca de blocos (§8f) | avaliação por etapas com marcos observáveis, cada etapa com seu custo de crescer |
| colheita (§8f) | contração que devolve capital de giro — o caixa melhora com a receita caindo |
| safra de capital (§12) | soma das partes entre a base instalada e o programa de investimento |
| validação por unit economics | margem e giro medidos num ciclo completo de contrato, contra o retorno derivado |

A tradução carrega os marcadores de honestidade intactos: "hipótese de construção", "não
verificado nesta sessão", "direção do erro" são linguagem de mercado legítima e obrigatória.

**O exemplo da regra mais violada** — prosa com a conta inline versus grade órfã (o trecho abaixo
é ele mesmo publicável, sem referência interna alguma):

*Grade órfã (proibido):* `| ROIC marginal | 8,5% | g/RiR |` — todos os números, nenhum raciocínio.

*Prosa com a conta inline (obrigatório):* "A rentabilidade que entra é a **marginal**, não a
contábil de 28% inflada por ativos antigos rendendo a preços de hoje. A cadeia: deployment de
US$ 1,0bn (demonstração de fluxo de caixa) sobre lucro operacional pós-imposto de US$ 1,41bn ⟹
taxa de reinvestimento de 58,8%; com crescimento de 5%, o retorno marginal implícito é
5% ÷ 58,8% = **8,5%** — crescimento e reinvestimento são os inputs, o retorno é a saída. Significa
reinvestir 59 centavos de cada real de lucro para sustentar 5% de crescimento: negócio caro de
crescer, e por isso o spread sobre o custo de capital, não o crescimento, domina o valor. Se o
deployment for majoritariamente reposição, a taxa de reinvestimento cai e o valor sobe — é a
premissa cuja inversão mais move o resultado."

**RiR por componente (v9.22).** A conservação de capital já contém a soma — a regra apenas a
abre: `RiR × NOPAT = capex_fixo_de_crescimento + ΔWC ⟹ RiR = RiR_fixo + RiR_wk`. O preço do
crescimento é um vetor, e a pergunta correta é *quais componentes o crescimento dos próximos T
anos de fato consome*. Com capacidade pré-construída (gatilho no Gate 3), o crescimento até a
plena consome só giro — RiR agregado cobraria capex fixo que não será incorrido (dupla cobrança,
valor subestimado — jurisprudência J15). Tratamento completo em §8f. Corolário epistêmico: ROIC
que sai como resíduo do triângulo (g e RiR inputs) é aritmética, não evidência — sem a validação
por unit economics do §11.2 ou fonte independente, a entrega declara "rentabilidade marginal
derivada por resíduo, não validada".

**Decomposição do g por componente (v9.25) — o espelho do lado do crescimento.** A v9.22 decompôs o
custo do crescimento (RiR = RiR_fixo + RiR_wk); esta regra decompõe o próprio crescimento. Gatilho:
**qualquer projeção NOMINAL** — que, por prática de mercado, já embute repasse de inflação no preço
(o §2 reconhece: "o g já contém reajustes"). Decomposição declarada: g = g_volume + g_preço, com
g_preço = inflação × repasse + preço real (repasse ∈ [0, 1], declarado; os extremos repasse 0 e 1
SÃO as duas âncoras congelado × acompanhando da dupla entrega do §7 — mesmo eixo, agora nomeado).
Acoplamento: capital FIXO só é cobrado pela expansão do VOLUME de vendas — planta fabril e
capacidade instalada não crescem porque o PREÇO do produto subiu; GIRO é cobrado perna a perna, cada
uma com o índice do SEU fluxo — recebíveis com o preço de venda, estoque com o custo de reposição do
insumo, fornecedores com o custo de compra (funding, sinal oposto) — e o consumo do componente-preço
é o ciclo de caixa (financeiro) ponderado por esses índices, com o SINAL do ciclo: ciclo de caixa
negativo converte inflação de preço em geração de caixa. **Aplica-se quando o RiR é a perna DERIVADA
do triângulo** (dois inputs livres, um output): o blendado é RiR = (g_volume × custo pleno + g_preço
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

**Padrão para verificações** — nunca "a verificação passou"; sempre o que foi testado, o número,
a consequência: *"o único driver com gap relevante é o câmbio, a 3,1% do spot — abaixo do limiar
de 10%, então os últimos doze meses seguem representando o nível corrente e não há normalização
a fazer."*

**Onde a prosa pode ser curta:** disclaimer, limitações e riscos podem ser lista. Conclusão,
premissas, verificações, memória de cálculo e expectativas embutidas, não — são o raciocínio.
**Nunca um número único. Sempre a ponte para preço explícita.**

## 5b. Entrega — texto integral (migrado do corpo da skill na v9.26)

Leitura OBRIGATÓRIA antes de qualquer relatório completo (fluxos 2 e 3). O corpo da skill mantém
o esqueleto da entrega; este é o texto integral que o esqueleto referencia — regra de
substituição, quadro pedagógico, as dez bifurcações por extenso, primeira aparição e formato
dentro de seção. Nada foi cortado na migração.

### A entrega é um relatório de research — e um produto de mercado (fluxos 2 e 3)

**Princípio da parede.** Gates, regras, convenções, jurisprudência, comandos e versões são a
infraestrutura do analista — o leitor recebe os ACHADOS, nunca a infraestrutura. Teste de
aceitação: um gestor que nunca viu esta skill entende 100% do texto, incluindo o porquê de cada
escolha, sem pedir nenhum documento adicional.

**Regra de substituição (o coração da parede).** Cada regra travada codifica uma razão econômica.
No relatório, a escolha é justificada pela RAZÃO — em uma frase, com o número — ou por fonte
externa citável (Damodaran, Mauboussin/Rappaport, McKinsey), nunca pela autoridade da regra.
"Pela regra §9, caixa/E = 0" vira: "num negócio com braço financeiro, o caixa é liquidez
operacional e regulatória, não excedente devolvível — e a companhia tem dívida líquida positiva".
Se a razão não couber em uma frase, a escolha não foi entendida: volte à regra antes de escrever.

**A saída do motor é processo, não produto.** O texto que os comandos imprimem — avisos, travas,
nomes internos, referências de seção — é artefato de auditoria do analista. O CONTEÚDO de um aviso
material atravessa a parede (omiti-lo esconderia achado); a REDAÇÃO dele, nunca — todo texto do
motor passa pela tabela de tradução (`aplicacao.md` §5) antes de virar produto. A memória técnica é
processo e pode carregar saída do motor verbatim; o relatório, não.

**Lista de banimento no corpo do relatório** (uso interno segue livre): nomes e números de gates;
códigos de regra/convenção/jurisprudência (R#, C#, D#, J#, §#, "paper §"); números de versão da
skill; nomes de comandos e flags; enums do motor na prosa (`antecipacao_temporal`,
`nao_confiavel`); os termos internos "dupla entrega", "bifurcação", "quadrante proibido", "guarda
anti-empilhamento", "trava", "motor", "framework", "skill", "jurisprudência", "regra travada".
Conceitos entram TRADUZIDOS (tabela em `aplicacao.md` §5). O banimento é de rótulo, nunca de
conteúdo: grades, memórias de cálculo e marcadores de honestidade ("hipótese de construção",
"não verificado nesta sessão", "direção do erro") continuam obrigatórios.

**Formato dentro de cada seção** (inalterado): prosa com a conta inline; a tabela de seis colunas
é formato de Excel, nunca o corpo; grades provam o raciocínio (uma frase acima, uma abaixo) e
toda grade cujo output é preço por ação declara a métrica de referência.
**Primeira aparição ensina (v9.21):** na primeira vez que cada variável da cadeia (encargo de
reposição, alíquota, crescimento, retorno do capital novo, taxa de reinvestimento, custo de
capital) é USADA fora do quadro, até duas frases explicam sua função na formação de valor — por
que existe, não só qual número foi escolhido. Aparições seguintes não repetem. Teto duro: a
explicação nunca vira parágrafo.

Estrutura fixa, nesta ordem — conclusões na largada:

1. **Conclusão** (abre o documento): faixa de valor (piso–base–teto) com veredicto explícito
   contra o preço de tela (data e banda); múltiplos de tela corrente E forward com base
   declarada; consenso (PT médio, nº de analistas) como referência externa, ou a lacuna
   declarada quando não houver cobertura; e as **4–6 premissas
   decisivas ABERTAS já aqui** — cada uma com o número e uma linha de justificativa própria.
   **Quatro vagas da lista são FIXAS, sempre: (i) base de lucro/EBITDA; (ii) rentabilidade
   marginal (ROIC/ROE), com a derivação em uma linha; (iii) g; (iv) custo de capital.** As
   demais vagas são do caso (hipótese terminal, driver dominante, alavanca); a verificação das
   fixas está nos critérios de aceitação. O
   leitor com 60 segundos sai daqui com a tese, os números que a sustentam e a premissa cuja
   inversão a derruba.

   **Quadro "como o valor é formado" (v9.21 — fixo, ≤ meia página, entre a Conclusão e as
   Premissas).** Box destacado, em linguagem plana, que ensina a mecânica antes de qualquer
   variável ser usada: do EBITDA, (i) desconta-se o que a operação consome para **repor os
   ativos existentes** — o encargo de reposição, "d" (sem repor, o lucro de hoje não se repete
   amanhã); (ii) desconta-se o **imposto** sobre o lucro operacional, "t"; (iii) do que sobra,
   separa-se a fração **reinvestida para crescer** — e quanto custa crescer depende do retorno
   do capital novo (crescimento ÷ retorno = taxa de reinvestimento); (iv) o caixa residual é
   descontado pela margem entre **custo de capital e crescimento**. Cada variável nomeada com
   sua função em UMA linha e o valor adotado no caso. Fecha com a frase-síntese: o múltiplo
   justo é essa cadeia comprimida — muda a variável, muda o múltiplo; o quadro é o mapa para
   ler todo o resto do relatório. A lista de banimento vale integralmente dentro do quadro.

2. **Premissas principais**: estimativas próprias × consenso (t, t+1, t+2) com desvios
   justificados linha a linha; e a derivação premissa a premissa em prosa com a conta inline
   (cadeias de §11) e os cinco atributos embutidos. **Regra do triângulo por cenário**:
   g = RiR × ROIC tem dois graus de liberdade — declare quais dois são input e qual é output, e
   mostre a taxa de reinvestimento de cada cenário. Cenário com RiR silencioso é cenário opaco.
3. **Companhia, números & indústria** (mandato completo quando o fluxo é relatório de
   companhia; dispensado em reversa rápida e screening — e NUNCA em delta: reavaliação roda o
   mandato completo, sem herança, v9.24): **perfil** — o que a companhia é,
   segmentos, ativos relevantes, posição competitiva; **históricos de 3–5 anos** em tabela
   curta (receita, EBITDA e margem, lucro, dívida líquida/EBITDA, capex, retorno sobre o
   capital) com a leitura de tendência em prosa; **guidance vigente** — o que a administração
   promete, o que descontinuou, e o confronto com o realizado; **administração e governança**
   quando materiais à tese; competição, share, penetração, bull/bear do sell-side (§1); as
   verificações narradas pelos seus ACHADOS com as rubricas de tradução — qualidade do lucro e
   do capital; estágio do ciclo de capital; representatividade da base (drivers × spot);
   alavancas identificadas — nunca pelos nomes internos. Verificação silenciosa segue proibida:
   o que foi testado, o número, a consequência. Proveniência de tudo: verificado nesta sessão /
   derivado por regra / hipótese de construção / fornecido e revalidado.
4. **Valuation**: cenários da grade canônica (§4) com âncora observável e preço/ação pela ponte
   explícita; tabela de múltiplos justos centrada no caso-base com a base declarada (a célula
   central reconcilia com a manchete); sensibilidades travadas (custo de capital, gp, degrau);
   grade de sensibilidade ao driver quando a elasticidade do dominante ≥ 0,5 (§7). Cross-check
   por segundo método declarado (múltiplo de saída sobre t+2, ou soma das partes no híbrido).
   **A hipótese de valor terminal é re-testada aqui**, agora que a rentabilidade marginal existe
   — uma linha mesmo quando não muda nada; é onde o erro mais caro é pego.
   **Sensibilidade às escolhas metodológicas** (nome externo da dupla entrega; interno segue
   "bifurcações"): as DEZ — base do lucro (reportada × normalizada); alavanca de lucro
   (modelada com probabilidade × absorvida/excluída como opcionalidade); rentabilidade (marginal
   × forward de consenso); g (reinvestimento × guidance/consenso); hipótese terminal; regime do
   driver no terminal (congelado × acompanha inflação); **caixa/excedente em híbrida
   financeira** (zero central × bruto — v9.16, regra em §9); **(v9.19) o ano de capex de
   estado estacionário no par d×RiR** (corrente × guidance de longo prazo), com o RiR
   re-derivado pela conservação em CADA ramo — nunca com o triângulo congelado; e **(v9.20) a
   fronteira de consolidação quando minoritários/coinvestimento > ~20% do PL** (fatia de
   terceiros no EV pelo valor contábil × econômico estimado — ignorá-la não é ramo, é erro;
   gatilho em `aplicacao.md` §2); e **(v9.22) a leitura de capacidade quando o gatilho da
   capacidade pré-construída dispara** (ramo corrente: ociosidade ignorada, RiR pleno, d
   contábil × ramo capacidade: RiR por componente, fases do §8f, d do estado estacionário da
   capacidade) — o ramo capacidade só é caso-base com observável direto de utilização OU
   contraprova de receita-por-ativo contra pares a plena fechando dentro de ±15%; derivado só
   do protocolo físico sem contraprova, é sensibilidade identificada, nunca base em silêncio.
   **Base monetária não entra nessas dez escolhas:** é reportada separadamente como invariante de
   coerência (nominal ou real), com g/gp/rentabilidade/custo de capital reconciliados na mesma base.
   Escolha alternativa movendo > ~10%
   ⟹ a tabela traz as duas, com o custo de cada uma e a escolha central justificada pela razão.
   **Coerência interna dos cenários** (nome externo da guarda anti-empilhamento): o caso-base
   usa a escolha CENTRAL de todas; o produto dos extremos conservadores É o bear (rotulado), o
   dos otimistas, o bull — escolher o ramo conservador de tudo no caso-base não é prudência, é
   cenário incoerente.
5. **O que está no preço**: o menu de reconciliação (§4) — nível implícito COM o confronto
   temporal contra o consenso, horizonte implícito, crescimento sem consumo de capital
   implícito, curva iso quando houver dois vetores, e **custo de capital implícito SEMPRE**
   (beta implícito contra a banda observada do beta — a explicação mais barata de esquecer).
   Fronteiras bivariadas plausíveis depois dos univariados, com a dualidade dos eixos de
   denominador declarada quando existir; **a seção fecha com o julgamento comparativo: qual
   reconciliação exige a menor violência às âncoras observáveis, e qual observável a testaria.**
   Perto da neutralidade a variável implícita é ruído com cara de precisão — reporte a
   curvatura. É a seção onde a abordagem é insubstituível — recebe o espaço.
6. **Riscos + veredicto**: os 4–6 que movem a tese, cada um com o observável que o monitoraria;
   fecha com alavanca dominante, o que a fórmula não captura, e a premissa cuja inversão viraria
   a conclusão.
7. **Visão não-consensual** (obrigatória, ≤ 15 linhas): leitura que não está na cobertura,
   construída SÓ com fatos já citados, com a cadeia factual explícita. Sem nenhuma, declare
   "sem visão não-consensual nesta rodada" — não invente.
8. **Metodologia, limitações e disclaimer**: um parágrafo de metodologia em linguagem plana —
   a identidade central (abordagem de múltiplos justificados: o múltiplo como saída de um DCF
   comprimido em poucas variáveis), citável sem mencionar a skill; a mecânica variável a
   variável NÃO se repete aqui: mora no quadro de abertura, que este parágrafo referencia;
   e o disclaimer específico ao caso, nunca genérico
   (lista aceitável): pocket valuation e não DCF nem DD; o que não captura por construção;
   premissas de estabilidade e quais o caso viola; contabilidade específica; direção do erro de
   cada premissa congelada.

**Memória técnica — o segundo artefato (v9.16).** O bloco YAML (§6) NÃO entra no relatório:
é entregue como artefato separado rotulado "memória técnica — uso interno" (arquivo próprio
quando a entrega for arquivo; bloco final destacado quando for chat). Mantém todos os campos
internos — é onde a reprodutibilidade mora. No relatório, seu lugar é um quadro de premissas em
linguagem plana (custo de capital, crescimento, retorno, taxa de reinvestimento, horizonte,
hipótese terminal — uma linha cada), dentro do item 8. Título e nome de arquivo do relatório sem
versão da skill; a versão vai na memória técnica. **Captura de aprendizado e oferta de
aprofundamento são chat-only: nunca dentro de arquivo entregável.**

**Critérios de aceitação, antes de enviar:** (i) leitor frio refaz a análise inteira só com o
texto — número sem a conta = incompleto; (ii) só a prosa, pulando grades e contas, sustenta o
raciocínio da conclusão ao detalhe; (iii) zero termos da lista de banimento no corpo (verifique
por busca literal antes de entregar); (iv) as quatro premissas fixas presentes na Conclusão,
cada uma com o número e a derivação — fixa ausente ou sem número = entrega incompleta; (v) um
analista que não conhece teoria de múltiplos entende a FUNÇÃO de cada variável a partir do
quadro e das primeiras aparições — variável usada sem função explicada = entrega incompleta.

**Trava de encerramento:** não ofereça aprofundamento com a cobertura incompleta. Faltando
espaço, corte prosa do veredicto e do disclaimer — nunca as premissas, a memória de cálculo ou a
memória técnica.

## 6. Memória técnica — bloco de inputs reprodutível (obrigatório; NUNCA dentro do relatório)

Artefato separado, rotulado "memória técnica — uso interno" (arquivo próprio quando a entrega for
arquivo; bloco final destacado quando for chat). É onde a reprodutibilidade e a língua interna
moram — campos, enums e comandos ficam livres aqui. No relatório, o lugar dele é um quadro de
premissas em linguagem plana (SKILL.md, item 8 do template).

Fecha toda valuation. É o que permite reproduzir a análise idêntica numa sessão futura — e é a
única forma legítima de "herança", porque vem do usuário e é revalidada.

```yaml
companhia: TICKER
data_analise: AAAA-MM-DD
fase: investimento|distribuicao|mista|hibrida_financeira
regime_base: A_reportada|B_normalizada
consenso: {t1_eps: 0.0, t2_eps: 0.0, pt_medio: 0.0, n_analistas: 0, fonte: "...", data: AAAA-MM-DD}
preco: {valor: 0.00, moeda: USD, fonte: "...", data: AAAA-MM-DD}
fx: {par: USDBRL, valor: 0.000, fonte: "...", data: AAAA-MM-DD}
acoes: {total: 0, tesouraria: 0, classes: "A/B pari passu em dividendos"}
metrica_base: {tipo: EBITDA|LL, valor: 0, periodo: "1T26 anualizado", fonte: "..."}
capital: {tipo: equity|capital_investido, valor: 0, data: AAAA-MM-DD,
          mudou_12m_%: 0, evento: "IPO fev/26"}
drivers:
  - {nome: "...", base: 0.00, spot: 0.00, elast: 1.0,
     elast_fonte: "derivada = receita_driver/metrica | declarada porque ...",
     receita_driver: 0.00, impacto_%: 0.0, tratamento: "cenario|sensibilidade",
     fonte: "...", data: AAAA-MM-DD}
degrau:
  indice: {nome: "Basileia", atual: 0.0, piso_regulatorio: 0.0, piso_administravel: 0.0}
  m_eficiencia_marginal: 1.0
  anos_transicao: 0
  perfil_transicao: rampa|pontual
  restricao_efetiva: "capital|funding|originacao|share"
base_monetaria:
  regime: nominal|real                 # invariante obrigatório; não é 11ª bifurcação econômica
  moeda: USD
  coerencia: "g, gp, rentabilidade e custo de capital reconciliados na mesma base"
  fisher: real_exato|nominal_exato|terminal_only_aproximado
crescimento:
  total: 0.0
  volume: 0.0
  preco:
    inflacao: 0.0
    repasse: 0.0
    real: 0.0
  rir_por_componente: {volume: 0.0, preco_nominal: 0.0, preco_real: 0.0, criterio: "..."}
depreciacao:
  d_final: 0.0
  origem: fluxo_economico_corrente|proxy_contabil_historica|outra
  moeda_origem: USD
  historico_ou_corrente: corrente|historica
  idade_ativos: "..."
  fator_reposicao: 1.0
  ajuste_aplicado: false
  justificativa: "..."
clean_surplus:
  aplicavel: false
  gap: 0.0
  status: fecha|fluxo_nao_explicado|nao_aplicavel
  fluxo_nao_explicado: "..."
book:
  qualidade: reportado|ajustado|reconstruido|proxy|nao_confiavel
  retorno_medio_inicial: 0.0            # ROIC_book ou ROE_book conforme lado
  base_temporal: forward_NOPAT1_sobre_IC0|forward_LL1_sobre_PL0|trailing_reconciliado
  nopat_ou_ll_associado: 0.0
  capital_inicial_implicito: 0.0
  rentabilidade_marginal: 0.0
  retorno_medio_ano_n: 0.0              # output do IC/E acumulado nos dois lados
  implementacao: enterprise_IC_acumulado_e_equity_E_acumulado_clean_surplus_DDM (v9.30)
caixa:
  cash_e: 0.0
  cash_yield_bruto: 0.0
  rendimento_caixa_no_ll: true|false
  tratamento: separado_da_operacao|incluido_com_ajuste
taxas:
  g: 0.0
  rentabilidade: {tipo: ROE|ROIC, valores_por_cenario: [0,0,0,0], ancoras: ["...","..."]}
  custo_capital: {tipo: Ke|WACC, valor: 0.0, rf: 0.0, beta: 0.0, erp: 0.0, fonte_beta: "...",
                  canal_risco_pais: "i_beta_local+CRP_por_lucro | ii_beta_ADR_sem_CRP"}
  cap_anos: 10
  convencao_tv: book|convergencia|gordon
  convencao_preliminar: book|convergencia|gordon
  revalidacao_convencao: "mantida | trocada porque rentab marginal X% < custo Y%"
  rentab_tv: 0.0
  gp: 0.0
  d: 0.0
  t: 0.0
  caixa_sobre_equity: 0.0
segmentos: "negocio unico | rodado por partes: [...] | blended declarado, direcao do erro: ..."
comandos_executados: ["selftest", "drivers ...", "pe ...", "degrau ...", "tabela pe ...", "rev ..."]
status_premissas: {verificado: [...], regra_travada: [...], hipotese: [...]}
```

## 7. Múltiplos drivers exógenos — o nível que já mudou

O problema mais traiçoeiro do framework: **os financials reportados/TTM embutem o nível MÉDIO dos
drivers exógenos no período-base**. Se o spot divergiu, o múltiplo congelado responde à pergunta
errada — "quanto vale ao preço de ontem" — e nenhuma variável do motor (g, rentabilidade, custo de
capital, CAP) revela isso.

**Não existe "o" driver.** Praticamente toda companhia real tem mais de um: mineradora (metal +
câmbio + diesel), exportadora (preço + câmbio + frete), gerador (energia + hidrologia), banco
(spread de captação + teto/tarifa regulatória + câmbio na ponte de preço quando listado fora),
plataforma (take-rate + custo de aquisição). Monte o **registro de drivers** e rode `drivers`.

**Trava anticombinatória.** Só os dois de maior |elasticidade × gap| viram cenário; os demais
viram linha de sensibilidade declarada. Sem isso, a entrega deixa de ser comparável entre sessões.

**Compensação entre drivers.** Drivers podem se anular (commodity subindo com moeda apreciando).
Reporte o efeito líquido E os brutos: a compensação é resultado, não motivo para omitir. Atenção
ao caso em que os dois se movem juntos — aí a elasticidade combinada é maior que a soma intuitiva.

**Sintoma de defasagem:** ao rodar o TTM, a empresa parece cara e o preço de tela sai
"inalcançável"; o analista fica "apertando" g/rentabilidade/custo de capital atrás de um resultado
que não fecha. O problema não está nessas variáveis — está no nível da métrica-base.

**Ponte de alavancagem operacional (`normaliza`):** com custo de caixa e volume fixos no curto
prazo, cada unidade de nível cai quase inteira na métrica-base:
`EBITDA(P) = EBITDA_base + Volume × (P_spot − P_base)`, com `Volume = receita_do_driver /
preço_realizado_base`.

**Cadeia contábil — a dupla alavanca:** a D&A absoluta é ~fixa ao nível, logo **d = D&A/EBITDA
CAI quando o nível sobe** — métrica-base E múltiplo justo sobem juntos (efeito Molodovsky pelo
lado do justo: no topo o observado cai e o justo sobe; no fundo, o inverso). Comparar tela com
justo sem normalizar os dois ao mesmo nível é **erro de sinal duplo**. **Armadilha do pico:** ROIC
de pico no motor de g barateia o reinvestimento e empilha o ciclo duas vezes — use
mid-cycle/marginal.

**Reversa específica:** além de custo de capital/g/gp implícitos, reverta o NÍVEL implícito no
preço (`nivel`). Costuma ser a variável implícita mais informativa, porque é a única com
observável de mercado direto para confronto.

**Dependência ≠ defasagem — dois gates, duas perguntas (v9.13).** O gate anti-defasagem responde
"a fotografia de partida está velha?". Ele NÃO responde "o valor desta companhia é uma aposta num
único preço?" — e as duas perguntas se dissociam exatamente no caso mais perigoso: spot colado no
período-base (gate mudo) com elasticidade altíssima (jurisprudência J5: 74% da métrica num driver
com gap pequeno — alarme verde, valor inteiro pendurado num preço). Regra: **elasticidade do driver
dominante ≥ 0,5 ⟹ a grade de sensibilidade ao preço do driver é entrega OBRIGATÓRIA,
independentemente do gate**. O gate decide se a BASE precisa ser normalizada; a elasticidade
decide se o VALOR precisa ser exibido como função do preço.

**Grades de sensibilidade ao driver — regras de construção (v9.13).** A grade é
`preço do driver × um segundo eixo` (custo de capital OU g), com o preço/ação por célula, montada
chamando `ev` célula a célula — nenhum número fora do motor. Quatro regras:

1. **Configuração do triângulo declarada por grade.** g = RiR × ROIC tem dois graus de liberdade;
   toda grade fixa dois papéis e deixa um implícito. Declare qual: "RiR travado, ROIC derivado do
   nível, g output"; "g travado, ROIC derivado, RiR implícito"; "grade driver × g, RiR implícito
   por célula". Grade sem configuração declarada não é reproduzível.
2. **Dupla configuração obrigatória quando divergem.** Derivar a rentabilidade do lucro corrente
   sobre capital histórico E o g dessa rentabilidade via RiR fixo **conta o ciclo duas vezes** — o
   mesmo preço infla o ROIC (efeito vintage) e o g por arrasto (jurisprudência J6: +22% no
   extremo da grade). Entregue a configuração disciplinada (g travado) E a derivada (limite superior),
   e reporte o spread nas extremidades como a magnitude da dupla contagem. As duas coincidem no
   ponto-base por construção — se não coincidirem, a grade está errada.
3. **A variável implícita é comentada, não silenciada.** Cada célula/região carrega os
   diagnósticos que o motor já emite para a variável que a configuração deixou implícita:
   RiR > 100% ⟹ exige funding externo declarado; spread negativo ⟹ crescer destrói valor;
   gp acima do teto macro. Numa grade driver × g, o RiR implícito de cada célula é o comentário;
   numa grade driver × custo de capital com g travado, o RiR que resulta do ROIC derivado também.
   Grade com região condicionada sem o comentário convida a ler o canto superior como cenário.
4. **Curva iso-preço como fechamento.** O par (preço do driver, segundo eixo) que reconcilia o
   preço de tela — a fronteira "o que precisa ser verdade" — fecha a grade e conecta com a
   reversa em nível.
5. **EBITDA de referência em TODA grade com output em preço (v9.14).** A mesma análise circula
   legitimamente com vários EBITDAs (reportado, normalizado ao spot, com degrau capturado — na
   jurisprudência J7) e uma tabela de preço/ação sem a métrica-base declarada é ambígua
   por construção. Toda grade cujo output é preço por ação carrega, no cabeçalho ou na frase de
   abertura, o EBITDA de referência sobre o qual foi construída.

**O regime do driver no terminal — a dupla entrega dos dois regimes (v9.28).** Gate de nível
disparado E convenção terminal sem crescimento de preço (`convergencia`, ou `gordon` com gp ≈ 0)
⟹ o caso-base está assumindo, sem dizer, o driver congelado em termos nominais — caindo ~inflação
a.a. em termos REAIS, em perpetuidade — descontado a Ke nominal (a consistência de Fisher está em
§2; o `normaliza` avisa). Como nenhuma das duas âncoras é "a verdade", a entrega traz OS DOIS
regimes obrigatoriamente: **driver congelado nominal** × **driver acompanhando a inflação declarada**.
A segunda âncora precisa usar uma rota Fisher exata: **A**, fluxos reais com Ke real (central no motor
comprimido), ou **B**, TODO o horizonte nominalizado com Ke nominal. Devolver inflação apenas no TV
é a rota **C terminal-only**, uma aproximação que pode aparecer somente como sensibilidade rotulada.
A diferença entre as âncoras é informação. É a 5ª bifurcação nomeada da dupla entrega (SKILL.md).
Limite honesto: "acompanha inflação sem custo" é um teto; no mundo real, repor capacidade e girar
capital a preços correntes pode consumir parte do ganho.

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
(a ponte do §8b compõe na mesma recursão — o iso bifásico já o faz); *colheita* (g < 0 com
LIBERAÇÃO de giro, FCFF > NOPAT — a forma α/β funciona com g₁ negativo sem alteração:
processadora pós-pico, run-off, footprint encolhendo; é o espelho formal da leitura
não-consensual de J15). **Trava do delimitador (inegociável):** cada fase adicional exige um
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

## 9. Financeiras — sub-playbook

Bancos, seguradoras e financeiras **não têm leitura de EV/EBITDA nem de capital investido**:
dívida é matéria-prima, não estrutura de capital. Rode só o lado equity.

- **Métrica-manchete: P/VP = P/L × ROE.** É a forma natural do setor e reconcilia exatamente com o
  motor. A ponte de preço não tem dívida: `equity = múltiplo × lucro`; `preço = equity ÷ ações`
  (÷ câmbio, se listada fora).
- **caixa/E = 0** (`--gde 0 --nde 0`): caixa é ativo operacional, não excedente devolvível. A
  neutralidade ROE = Ke vale exatamente nesse caso (com marginal e book iguais ao Ke — sob
  `book`, marginal = Ke com book ≠ Ke não é neutro).
- **Caixa/E em HÍBRIDA financeira (v9.16, origem J8/MELI).** É a alavanca esquecida mais cara:
  no caso-origem, o caixa bruto era 86% do PL e o tratamento movia 45% do valor sem estar na
  lista de escolhas. Regra: com **dívida líquida positiva OU funding de carteira relevante**,
  caixa/E = 0 é a escolha central obrigatória — o caixa é liquidez operacional e regulatória do
  braço financeiro. O tratamento bruto entra como a 7ª escolha metodológica nomeada na tabela de
  sensibilidade (SKILL.md, item 4), nunca como caso-base. O critério é a DEVOLVIBILIDADE ao
  acionista, não a presença no balanço.
- **Vintage do book é crítico.** Evento de capital nos últimos 12 meses invalida o ROE de LTM
  (ver §1). Recalcule sobre a base atual.
- **Qualidade do patrimônio.** Crédito tributário relevante no PL muda a leitura de P/VP (sobre
  book tangível o múltiplo é maior e a rentabilidade também) — o P/L é imune, o P/VP não. Reporte
  os dois quando o CTA for material.
- **Capacidade é restrição regulatória**, não física: índice de capital acima do piso é degrau
  disponível (§8). Mas a restrição efetiva costuma ser **funding**, não capital — teste.
- **Cessão com retenção de risco fica no balanço** e consome capital; só venda verdadeira (sem
  coobrigação) libera — migrar de regime é mudança de modelo, não degrau; trate fora do framework.
- **Hedge muda a elasticidade:** carteira pré convertida em flutuante trava o spread — verifique o
  hedge antes de atribuir elasticidade ao driver de juros.
- **Crescimento é limitado por capital:** g sustentável ≤ rentabilidade × retenção, e a retenção
  tem piso legal/estatutário de payout. Se g proposto exceder isso, ou há emissão implícita ou o
  crescimento recente não é sustentável — reporte.

## 10. Status das premissas (template do resumo final)

verificado nesta sessão / derivado por regra travada (citar a regra) / hipótese de construção /
fornecido pelo usuário e revalidado (dizer o que foi revalidado). Sinalizar sempre o que é qual, e
o vintage (data e nível de driver, e data da base de capital) de cada premissa sensível.

## 11. Memória de cálculo — cadeias obrigatórias (templates)

Regra: premissa derivada nunca aparece só como número. Mostre a cadeia com os valores de cada
etapa e a fonte de cada insumo. Os templates abaixo são o mínimo; adapte os rótulos ao caso.

**Critério de aceitação:** o leitor refaz a conta sem perguntar nada. Se ele precisa perguntar
"de onde veio esse número?", a memória está incompleta.

### 11.1 Rentabilidade marginal (a mais cobrada — nunca pule)

```
Capital deployado 2025 .......... X  (fonte: DFC, linha "aquisições"/capex de crescimento)
NOPAT (ou LL) 2025 .............. Y  (fonte: DRE, ajustado por Z)
(=) RiR = X / Y ................. R%
g adotado ....................... G%  (âncora: guidance de volume + ...)
(=) ROIC marginal = G / R ....... M%
Rentabilidade contábil .......... C%  (NOPAT ÷ capital investido médio)
Diferença M vs C explicada por: [vintage de ativos / nível de ciclo no numerador /
alavancagem anterior a evento de capital / mix]. Usamos M porque a fórmula só usa a
rentabilidade via RiR = g/ROIC — o que importa é o retorno do capital NOVO.
```
**Variante fase DISTRIBUIÇÃO (payout > 0), obrigatória do mesmo jeito:** quando a derivação vem
da retenção observada e não do deployment do DFC, a cadeia muda de insumo, não de exigência.
**Pré-condição (v9.20): payout definido sobre LUCRO.** Política sobre EBITDA, receita ou valor
fixo ⟹ esta variante NÃO se aplica (retenção observada não-informativa — §2, camadas do RiR);
use a cadeia por deployment do DFC e declare a troca:

```
Payout observado ................ P%  (proventos ordinários ÷ lucro recorrente; fonte, período;
                                       EXCLUIR devoluções extraordinárias — redução de capital,
                                       dividendo de monetização — que são estoque, não fluxo)
(=) Retenção = 1 − P ............ R%  (= RiR requerido, fase de distribuição)
g adotado ....................... G%  (âncora)
(=) ROE marginal = G / R ........ M%
Rentabilidade contábil .......... C%  (sobre a base de capital ATUAL — checar vintage, §1)
Diferença M vs C explicada por: [excesso estrutural de capital / vintage / ciclo / mix].
```
**A configuração do triângulo NÃO dispensa a cadeia.** Declarar "rentabilidade como input" (§11.2)
diz qual variável é livre — não autoriza um número sem âncora: o input exige a cadeia que o
justifica (esta variante, ou a de deployment acima, ou pares com fonte). Rentabilidade marginal
citada sem cadeia é o defeito mais recorrente da entrega, e ela é premissa FIXA da lista de
abertura do relatório (SKILL.md, item 1 da estrutura).

### 11.1b Conservação de capital (obrigatória sempre que d ≠ D&A contábil, ou D&A > capex)

```
Capex total (ano-base declarado) .... X   (fonte; corrente | guidance LP — declare qual)
ΔWC estrutural ...................... W   (fonte)
(=) Capital consumido ............... X + W
Encargo de reposição d×EBITDA ....... A
Encargo de crescimento RiR×NOPAT .... B
(=) A + B vs X + W .................. fecha / gap de ...% (direção do erro declarada)
```

Gap > 10% ⟹ o par (d, RiR) está na base errada — reclassifique antes de qualquer cenário.
**(v9.22)** Sob a leitura de capacidade (§8f), a verificação roda POR FASE: cada fase com seu
capex, seu ΔWC e seu par (d, RiR) — a rampa com capex só de manutenção e RiR_wk; a pós-plena
com o vetor pleno. Fase sem conservação exibida = fase opaca.

**Trava da `book`:** se a convenção for `book` e M ≠ C, separe MÉDIA e marginal. **Enterprise:**
passe `--roic-book C`; C é a média inicial/forward que ancora `IC₀ = NOPAT₁/C`, e o TV acumula o
capital novo ao marginal M. Se a fonte for trailing, alinhe a base temporal antes. Usar M nos dois
papéis conflaciona marginal×médio e pode mover materialmente o valor — no anchor do paper §6.11
(g 4%, M 25%, C 10%, W 8%, n 10), 9,718x conflacionado contra 12,608x separado (−22,9%).
**Equity:** passe `--roe-book C`; C ancora `E₀ = LL₁/C` e o patrimônio é acumulado por
clean surplus ao ROE marginal. No `book`, a identidade de validação obrigatória é
`DDM = residual income = motor`; Caixa/E não entra no valor por si só porque Δcaixa retido já está
em E_n. O motor alerta sempre que `book` roda sem o parâmetro separado quando ele é economicamente
necessário.

### 11.2 A regra do triângulo (g, RiR, rentabilidade)

`g = RiR × ROIC` tem **dois graus de liberdade**. Em cada cenário, declare em uma linha quais dois
são input e qual é output. As três configurações legítimas:

| Configuração | Quando usar | O que declarar |
|---|---|---|
| g e RiR observados ⟹ ROIC output | há histórico de deployment confiável | o RiR observado e o período |
| ROIC e g escolhidos ⟹ RiR output | a rentabilidade marginal é a tese | o RiR resultante e se é factível |
| ROIC e RiR ⟹ g output | negócio limitado por capacidade de reinvestir | de onde vem o teto de RiR |

Se a rentabilidade marginal é mantida constante entre cenários e o g varia, **o RiR é o que se
move** — mostre o RiR de cada cenário e confirme que nenhum passa de 100% sem captação declarada.
Cenário com RiR silencioso é cenário opaco.

**Validação por unit economics (v9.22) — o terceiro canal, condicional.** Quando o ROIC sai como
RESÍDUO (g e RiR inputs), ele é aritmeticamente consistente por construção — e consistência não é
evidência. A armadilha: DuPont sobre os MESMOS agregados (NOPAT/receita × receita/capital)
devolve o mesmo número por identidade — informação zero. O teste só existe medido de baixo para
cima, num ciclo completo de contrato (aquisição do insumo → transformação → entrega →
recebimento), com fonte INDEPENDENTE da cadeia (economics por contrato/segmento/loja/planta, ou
guidance de margem incremental). Cinco linhas de conta:

```
Margem de contribuição do ciclo ......... a%   (fonte)
(−) G&A incremental DECLARADO ........... b%   (a diluição do fixo é declarada, não presumida)
(=) Margem incremental .................. m%
Giro incremental = receita do ciclo ÷ (estoque + recebível − fornecedor − adiantamento) = x
ROIC_ue = m% × x ........ vs ROIC residual do triângulo — gap e leitura
```

Divergir é legítimo, ficar calado não (mesmo protocolo do RiR observado): margem incremental ≫
média sugere g subestimado ou RiR medido em ano de deployment atípico; giro do ciclo ≪ implícito
sugere giro estrutural subdimensionado na cadeia. **Peso assimétrico:** unit economics OBSERVADO
pode mover o vetor central, com a mudança declarada; CONSTRUÍDO é linha de sensibilidade — nunca
sobrescreve o residual em silêncio. Sem fonte nem construção declarável, uma linha resolve:
"rentabilidade marginal derivada por resíduo, não validada por unit economics — sem disclosure".
Não é quarto vértice: o triângulo segue com dois graus de liberdade — isto valida, nunca deriva.
Flag `--roic-ue` (espelho do `--rir-observado`): implementada no `ev` (v9.24) — divergência
acima do limiar sai DECLARADA, com a leitura direcional e o estatuto do peso assimétrico.
**Corolário (v9.23):** quando o custo do crescimento tem intensidade constante por Δreceita
(ramo capacidade, §8f), ROIC_ue e ROIC marginal coincidem POR IDENTIDADE — o canal valida a
coerência interna dos ramos, e a bifurcação inteira colapsa na pergunta única: *o crescimento
novo carrega capital fixo?*

### 11.3 Normalização de nível (as duas pontas, sempre)

```
Período-base .................... 2025 (ou LTM até .../...)
Receita do driver no período .... A   (fonte)
Volume do período ............... V   (fonte; ou derivado = A / preço realizado)
(=) Preço realizado base ........ Pb = A / V
Spot na data da análise ......... Ps  (fonte, data)
(=) Gap ......................... Ps/Pb − 1 = ...%
Elasticidade operacional ........ e = A / Eb   (receita do driver ÷ métrica-base)
(=) IMPACTO = |e × gap| ......... ...%   [gate por IMPACTO no limiar (10% default): disparou / não]
EBITDA base ..................... Eb  (fonte)
(=) EBITDA normalizado .......... Eb + V × (Ps − Pb) = En
D&A absoluta .................... D   (fixa por unidade produzida, não escala com preço)
(=) d base = D/Eb ............... ...%      (=) d normalizado = D/En ....... ...%
Efeito no múltiplo: EV/EBITDA = EV/NOPAT × (1−d)(1−t) ⟹ o múltiplo justo SOBE quando d cai.
```
Apresente sempre o cenário-base E o normalizado, lado a lado. Nunca só um.

### 11.4 Degrau de capacidade

```
Índice atual .................... Ia  (fonte, data)
Piso regulatório / administrável  Ir / Iad  (fonte; e por que o administrável é esse)
(=) h = Ia / Iad ................ h
m (eficiência marginal) ......... m   (razão declarada: funding, preço, mix)
(=) Rentabilidade pós ........... rentab × [1 + (h−1) × m] = ...%
Anos de transição ............... T   (razão)
(=) Fator de captura ............ 1/(1+custo)^T = ...  (incide SÓ sobre o incremento)
```

### 11.5 Custo de capital e ponte para preço

```
rf .......... ...%  (instrumento, fonte, data)     β ...... ...  (observado | pares: X, Y, Z)
ERP ......... ...%  (fonte, data)                  (=) Ke = rf + β × ERP = ...%
```
```
EV justo ........................ ...
(+) caixa e investimentos ....... ...   (fonte, data)
(−) dívida bruta ................ ...   (fonte, data)
(=) Equity ...................... ...
(÷) ações (líquidas de tesouraria) ...
(=) Preço por ação .............. ...   (÷ câmbio = ... na moeda de listagem)
```
Financeiras: sem ponte de dívida — `equity = múltiplo × lucro`, e o lucro vem declarado com a
âncora do cenário.

### 11.6 Grade/fronteira iso-nível — ponte de construção (v9.14)

Toda tabela que varre o PREÇO DO DRIVER (grade driver × eixo, fronteira iso-preço, matriz
ROIC × driver) carrega esta ponte, como as demais cadeias — sem ela a tabela não é reproduzível:

```
EBITDA de referência ....... US$ ...   (reportado | normalizado ao spot | com degrau — declare QUAL)
EBITDA(P) = EBITDA_ref + Volume × (P − P_ref)     Volume = ... (unidade na MESMA escala da métrica)
d(P) = D&A ÷ EBITDA(P)                            D&A absoluta = ... (fixa por unidade produzida)
Triângulo: [qual travado: RiR ...% | g ...%] ⟹ [qual derivado por célula]
Múltiplo por célula: FIXO em ...x | RECALCULADO no motor (`ev` por célula)
  — se FIXO, o preço implícito do driver é LIMITE SUPERIOR (dupla alavanca, §7; o `nivel` avisa)
Regime do driver no terminal: congelado nominal | acompanha inflação π = ...% (dupla entrega, §7)
```

Validação obrigatória: a célula (P_ref, eixo do caso-base) reproduz a manchete. Se não reproduz,
a grade é outra análise, não uma sensibilidade desta.

## 12. Multi-segmento — quando o negócio único é ficção

A fórmula descreve UM negócio: um `g`, uma rentabilidade marginal, um CAP, uma classe de
convenção. Companhia com segmentos economicamente distintos viola isso na origem.

**Teste de materialidade (rode antes de decidir):** os segmentos diferem materialmente em (i)
rentabilidade marginal, (ii) CAP/durabilidade da vantagem, ou (iii) classe de convenção terminal?
Se qualquer um dos três for sim para um segmento que pese mais de ~20% do EBITDA ou do capital,
o blended é erro sistemático, não aproximação. **Gatilho adicional (v9.20):** veículo de
coinvestimento consolidado com sócio externo relevante (o mesmo do gatilho de elevação da
fronteira, §2) é segmento com economia própria POR CONSTRUÇÃO — o sócio precificou aquela fatia
isoladamente ao entrar — e dispara este teste ainda que a operação pareça integrada.

**Gatilho por safra de capital (v9.22).** O teste dispara também SEM segmentos operacionais
distintos, quando a base INSTALADA e a EXPANSÃO em curso carregam claims de natureza/duração
distintas — concessão com termo + plataforma de originar concessões novas; mina + exploração;
contrato regulado + mercado livre. Nenhuma convenção terminal única serve ao consolidado: é a
decomposição de Miller-Modigliani (ativos instalados + PVGO) executada como soma de partes por
safra. Como rodar: a parte instalada com rampa a RiR_wk (§8f) e terminal da NATUREZA do claim
(anuidade com TV zero no termo; convenção normal se perpétuo); a expansão pelo fluxo padrão
quando programática, ou como NPV de projetos discretos quando datados com capex declarado —
soma, e a ponte para preço uma vez, sobre o topo (passos 3–5 acima). **Trava da parede entre
safras:** o crescimento da parte instalada é SÓ rampa; o da expansão é SÓ capital novo — a mesma
receita nunca aparece nas duas (canal único do §8f, elevado de nível). **Quando NÃO usar:**
claims homogêneos (fábrica em rampa + fábrica nova, ambos perpétuos) — a soma das partes e o
consolidado devolvem o mesmo número sob premissas coerentes, e abrir a SOTP só dobra terminais e
cria fronteira nova para dupla contagem se esconder; declare a equivalência e rode consolidado.

**Fase × safra (v9.23) — os dois eixos são ortogonais.** Fases compõem NO TEMPO dentro de uma
safra (recursão do §8f); safras compõem NO CAPITAL pela soma deste §12 — e cada safra pode ter,
internamente, suas próprias fases (segmento em rampa + segmento em investimento, simultâneos: é
uma matriz fase × safra, e a matriz cobre o caso geral). O múltiplo-manchete é output da soma.
Com uma safra investindo, o caixa CONSOLIDADO pode ser negativo com cada safra saudável — a
conservação de capital roda POR FASE E POR SAFRA, nunca só no consolidado. A trava do
delimitador do §8f vale em cada célula da matriz.

**Por que é sistemático, e não ruído.** O blended é média ponderada pelo tamanho e a criação de
valor não é — o múltiplo é não linear e g/rentabilidade nem são ponderados pela mesma medida (g
por NOPAT, rentabilidade por capital); a Hessiana é indefinida na região relevante (paper §6.12),
então o sinal do viés **se calcula, não se deduz**. Direção típica: subestima a joia pequena num
corpo de baixo retorno, superestima o corpo medíocre carregado por um segmento pequeno de ROIC
alto — mas é HIPÓTESE, pode inverter. Verificação barata e obrigatória quando a materialidade
dispara: **calcule EV_segmentado − EV_blended e reporte o número com o sinal**.

**Como rodar por partes:**
1. Métrica-base, capital e deployment por segmento (fonte: nota de segmentos). Se a companhia não
   abre capital por segmento, diga isso — é limitação de dado, e a solução é aproximar o capital por
   ativos identificáveis, declarando a aproximação.
2. Cada segmento com sua classe (Gate 1), sua convenção, seu CAP, sua rentabilidade marginal e seus
   drivers. Um segmento pode ser `gordon` e outro `book` na mesma companhia — isso é normal, não
   inconsistência.
3. Some os EVs dos segmentos.
4. **No topo, e só no topo:** custos corporativos não alocados (capitalizados a perpetuidade, ou
   alocados por critério declarado), participações não consolidadas, caixa, dívida. A ponte para
   preço acontece uma vez, sobre a soma — nunca por segmento.
5. Declare o desconto (ou prêmio) de holding se aplicar, e por quê. Não aplique por hábito.

**Se rodar blended mesmo assim** — porque o dado não permite, ou porque a diferença não é material
— declare os três testes, o resultado de cada um e a direção do erro esperada. Blended silencioso
é o defeito, não o blended.

### §8b — Ponte de releveraging: caso aplicado (v9)

**Quando disparar:** evento de estrutura de capital DATADO no horizonte — plano de desalavancagem
pós-recuperação judicial, dividend recap anunciado, capitalização de financeira para crescer,
covenant forçando amortização. Não confundir com deriva lenta de D/E (essa é a limitação C2 do
Ke fixo, tratada via `apv`), nem com degrau de rentabilidade (esse é o §8).

**Template de deleveraging (perfil pós-RJ).** Companhia sai de D/E 1,5 para 0,4 após 3 anos:

```bash
python scripts/justos.py ponte --n1 3 --ke1 26 --ke2 17 --gde1 150 --nde1 130 \
  --gde2 40 --nde2 30 --kd 13 --tax 34 --g1 6 --roe1 9 --pl-base 13.0
```

Leitura da saída, na ordem: (1) o sinal — negativo aqui: o acionista financia a amortização
antes do primeiro dividendo do regime novo; medido em casos-padrão, a ponte chega a −40% do
valor num deleveraging pesado e +10 a +21% em recap — ignorá-la superavalia o turnaround na
direção mais cara; (2) o diagnóstico de Ku — se o gap entre fases passa de 0,5 p.p., ou o
de-risking operacional é justificado por escrito (saída da RJ reduz risco do NEGÓCIO, não só da
dívida?) ou os Ke se re-derivam de Ku único via `apv` antes de qualquer conclusão; (3) o rebase —
com razão ≠ 1, a convenção bifásica declara que o NI da fase 2 entra ×(ROE₂/ROE₁)·razão.
Esse fator é uma **hipótese de rebase de nível**, não uma identidade que decorra do ROE marginal;
ROE₂ continua sendo o marginal usado na retenção da fase 2. A entrega deve narrar explicitamente o
degrau composto e qualificar qualquer ROE₂ implícito como condicionado a essa convenção:
"o lucro rebasa h× na transição por [margem/juros], e o crescimento g₂ aplica SOBRE a base
rebasada"; (4) o gate de 10% — ponte dominante pede modelagem explícita das fases, não ajuste.

**Na entrega:** a ponte aparece como premissa própria na memória de cálculo (valor, derivação
com a conta inline, fonte da estrutura-alvo e DATA do evento, status), e o veredicto declara a
direção do erro se o evento atrasar — deleveraging adiado = valor presente da ponte encolhe
(bom para o acionista de hoje se ela é negativa? não: o Ke₂ menor também adia — reporte o
líquido, nunca só um lado).


### §8d — Composição iso ↔ ponte: nada depende de o analista lembrar (v9.2)

Com evento de estrutura datado, a ordem de operações é FORÇADA pelo motor, não lembrada: o `iso`
exige `--transicao` (sem default). Declarando `ponte` com os parâmetros do regime 1, o motor
calcula o PV internamente (nunca transcreva o número à mão — erro de sinal em transcrição é o
modo de falha clássico), desconta do alvo e roda a curva sobre o alvo líquido no regime 2,
resolvendo a rentabilidade do regime 2 por uma INVERSÃO BIFÁSICA FECHADA — f1, ponte e TV
saem com os regimes declarados e ROE₂ sai em forma fechada **condicionada à convenção de rebase**, com cada ponto verificado contra o
bifásico completo. Declarando `nenhuma`, o output registra a premissa de regime único.
No `rev`, a mesma premissa sai como campo fixo do output e combinações resolver×base
inconsistentes falham com explicação em vez de rodar no lado errado. Na entrega: alvo cheio,
PV da ponte, alvo líquido e o rótulo da composição entram na memória de cálculo como quatro
linhas separadas.


### §6b — Moeda, regime e âncora macro no bloco de inputs (v9.4)

Todo bloco de inputs de valuation real declara, na primeira linha: moeda e regime (`--moeda`).
Essa linha é **invariante de coerência, não uma escolha econômica adicional**: com conversão completa,
nominal e real devem representar o mesmo valor. g, gp, rentabilidade e custo de capital são verificados
na mesma unidade, e o rf nominal da moeda (`--rf`)
quando houver perpetuidade com crescimento. Na memória de cálculo, a convenção de moeda é linha
própria, e qualquer gp acima do teto macro entra como premissa EXCEPCIONAL com a tese que a
sustenta — nunca como número solto. Erro-alvo destas guardas: g projetado em BRL nominal
descontado a Ke construído em USD (ou misturar real e nominal), que não produz nenhum sintoma
numérico e distorce o valor em dezenas de %.

## 13. Fronteira de escopo — onde outra arquitetura prevalece (v9.7)

Casos em que o framework segue útil como linguagem de premissas, mas NÃO como métrica-manchete —
declare a arquitetura dominante na entrega: **ativos de vida econômica finita** (mineração, óleo
e gás, concessão com termo): DCF de reservas/curva de produção; a perpetuidade agregada
superestima (paper §2.1 — NOPAT/W exige sustentabilidade indefinida). **REITs/imobiliárias**:
NAV, cap rates, FFO/AFFO; D&A contábil não informa. **Holdings**: soma das partes com dívida,
impostos e custos da holding, e desconto declarado. **Pré-lucro/introdução**: opções reais.
**Financeiras**: já cobertas no §9 (lado equity, P/VP = P/L × ROE). Nesses casos o comando
continua servindo para explicitar o que o múltiplo de tela embute — mas o veredicto de valor vem
da outra arquitetura.

## Apêndice J — Jurisprudência (casos-origem, uma linha cada)

Registro dos casos que geraram regras. Cite pelo código; não re-narre na entrega.

- **J1 (FNV 1T26)** — trava do piso: em pico de ciclo, o trimestre recente é TETO, não piso
  (realizado 16% acima do spot).
- **J2 (FNV/Cobre Panamá)** — classe do ativo parado: degrau +30,6% com probabilidade implícita
  de 103% no preço; sensibilidade US$ 4,05/ação por 10 p.p.
- **J3 (FNV rodada 2)** — teto do crescimento gratuito: nenhum eixo primário fechava; g gratuito
  ~5% > rf 4,74% foi a única hipótese que reconciliou o preço.
- **J4 (FNV)** — natureza do d: depleção de royalty (16,4%) é capex de reposição com outro nome;
  tratá-la como PPA decidiria ~20% do valor na direção errada.
- **J5 (FNV)** — dependência ≠ defasagem: 74% da métrica num driver com gap pequeno — gate mudo
  com o valor inteiro pendurado num preço; daí a grade obrigatória por elasticidade ≥ 0,5.
- **J6 (FNV)** — dupla contagem do ciclo na grade (+22% no extremo) e regime do driver no
  terminal (Fisher, ~28% do valor sem sintoma): daí a dupla configuração e a dupla entrega de
  regimes.
- **J7 (FNV)** — três EBITDAs legítimos na mesma análise (1.656/1.963/2.556): daí a métrica de
  referência obrigatória em toda grade de preço.
- **J8 (MELI, ago/26)** — origem da v9.15: companhia INVESTIMENTO + HÍBRIDA rodada como
  DISTRIBUIÇÃO de payout zero. Base reportada deprimida + RiR 100% (quadrante proibido, −60% de
  valor); retenção lida como RiR requerido; nível implícito 2,55x ≈ consenso t+2 lido como
  fantasia terminal; CRP empilhado sobre β de ADR (−35%); quatro ramos conservadores empilhados
  no caso-base. Gerou: teorema da base coerente, Gate 0.5, camadas do RiR, confronto temporal,
  canal único de risco-país, guarda anti-empilhamento. O teste frio da v9.15 no mesmo caso
  gerou a v9.16: parede processo×produto (25+ referências internas vazadas no relatório) e a
  regra de caixa/E em híbrida (alavanca de +45% fora da lista de escolhas).
- **J9 (duas execuções frias, mesma companhia/semana)** — US$ 197,52 × US$ 114,17, ambas
  defensáveis, divergindo nas bifurcações de julgamento: a dispersão não é defeito; escondê-la
  seria. Daí a dupla entrega nomeada.
- **J10 (FNV, ago/26)** — origem do menu de reconciliação: a seção de expectativas entregou a
  fronteira "consenso 2027 × regime inflacionário do ouro no terminal" sem rodar o eixo do custo
  de capital. Rodado depois: na base corrente o custo implícito era 4,50% < rf (beta negativo —
  eixo impossível sozinho), mas na base 2028 com o ativo parado religado, beta 0,55 — o FUNDO da
  banda observada — reconciliava a tela quase sem resíduo (238,08 × 239,00). A explicação mais
  barata não era o regime terminal heroico; era antecipação + denominador no piso da evidência.
  E os dois eixos eram quase-duais (mesma compressão de custo − crescimento). Gerou: menu
  obrigatório com Ke implícito sempre, dualidade declarada, gatilho de duração.
- **J11 (ALLD3, ago/26)** — origem da v9.18: rentabilidade marginal entrou como input do
  triângulo, validada nos bastidores contra a retenção observada, mas sem cadeia de derivação
  exibida e fora da lista de abertura. Gerou: as quatro premissas fixas da Conclusão (critério
  de aceitação iv) e a variante do §11.1 por retenção observada, com a regra de que a
  configuração do triângulo não dispensa a âncora do input.
- **J12 (KLBN, ago/26)** — conservação d×RiR: D&A contábil (62% do EBITDA) > capex total
  tornou o par canônico não representável (RiR < 0 com g > 0); a migração para d de caixa sem
  re-derivar o RiR deixou ~R$ 0,5 bi/ano de capital sem cobrança (+20% no valor), e a
  sensibilidade em d com triângulo congelado inflou a faixa para R$ 0–22 quando a coerente era
  R$ 12–22. Gerou: identidade de conservação, quadrantes proibidos do lado do capital,
  migração de par em D&A-overhang e a 8ª escolha nomeada (ano de capex de estado estacionário).
- **J13 (KLBN, ago/26)** — fronteira de consolidação: coinvestimento florestal (Plateau) dobrou
  a participação de não controladores para 40,6% do PL consolidado com o EBITDA consolidando
  100% das SPEs; a tela que não levava a fatia ao EV mostrava 6,36x contra 7,24x corretos —
  0,9x de múltiplo e 30% do preço (R$ 5,32/unit) de valor que não pertencia ao acionista.
  Gerou: gatilho de elevação (>~20% do PL ⟹ 9ª escolha nomeada, contábil × econômico) e o
  gatilho de multi-segmento por coinvestimento no §12.
- **J14 (KLBN, ago/26)** — payout sobre base ≠ lucro: política de proventos de 10–20% do EBITDA
  ajustado pagou dividendo integral em semestre de PREJUÍZO atribuível; a retenção observada
  (1 − payout) perdeu qualquer conteúdo informativo sobre o custo do crescimento mesmo com
  payout > 0. Gerou: exceção nas camadas do RiR e pré-condição da variante DISTRIBUIÇÃO do
  §11.1 (payout sobre lucro), com fallback obrigatório ao deployment do DFC.
- **J15 (ELMT, ago/26)** — capacidade pré-construída: RiR agregado cobrou capex fixo de
  crescimento numa companhia com parque em ramp-up (linhas "reaching rate", capex de crescimento
  identificável, guidance de margem por escala), e o d contábil refletia D&A do parque pleno
  sobre EBITDA de utilização parcial — dois erros na mesma direção; correção coerente pela
  conservação = +11% a +31% de valor (US$ 7,71 → 8,58–10,12), veredicto inalterado. Gerou: RiR
  por componente, Gate 3 estendido, 10ª escolha nomeada (leitura de capacidade), §8f (fases e
  compressões, com a anualização corrigida para (capacidade/produção)^(1/T) − 1), gatilho por
  safra de capital no §12, e a validação por unit economics do §11.2. **Teste frio + planilhas
  (20/ago, gerou a v9.23):** a regra de centralidade segurou a base no ramo corrente na primeira
  rodada real; a reversa sob o ramo achou raiz em g (24,3% a.a. com RiR de 95% na raiz — aposta
  legível, cara); o bifásico provou a forma fechada da rampa (duas anuidades α/β, RiR variando
  31,3→28,7%) e mediu o custo da rodada única (8,58 → 9,04: o re-base do d, ~5% do valor).
  Gerou: composição de fases com trava do delimitador, bloco de colheita, reversa sob
  intensidade constante, fallback da contraprova e item 3 em delta na reavaliação (delta
  REVERTIDO na v9.24 — decisão de princípio do dono: sem herança em hipótese alguma, o fluxo
  completo roda sempre; o bloco do usuário vira dado de confronto pós-derivação).
