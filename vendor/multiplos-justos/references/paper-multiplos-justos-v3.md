# Múltiplos Justos

**v3 · documento de trabalho**

*O múltiplo como output de um DCF comprimido em poucas variáveis: crescimento, retorno marginal, custo de capital, duração da vantagem competitiva e contabilidade.*

---

## Resumo

Este documento reúne a fundamentação teórica do framework de múltiplos justos, catorze proposições derivadas dele (as duas últimas adicionadas na v3.1) e os limites de validade de cada uma. A tese central é que o múltiplo não é primitivo: é o resultado comprimido de um DCF, e explicitar a compressão devolve ao múltiplo o poder analítico que a agregação destruiu — inclusive na direção inversa, lendo o múltiplo de tela como um sistema de equações a resolver.

**Definição (v3.4).** Neste framework, **múltiplo justo** significa o múltiplo forward implícito em um DCF especificado, condicionado à métrica-base normalizada e ao conjunto declarado de premissas econômicas, financeiras, contábeis, temporais e terminais. Não é um múltiplo universal nem independente do modelo; é um múltiplo *justificado* pelos fundamentos declarados — daí o nome em inglês, *justified multiples*. Todo o restante, inclusive o tagline do "DCF comprimido", lê-se sob esta definição: a compressão é uma especificação particular de DCF (as relações da §7), não uma equivalência sem perda com qualquer DCF — a trajetória que ela impõe a lucros, reinvestimento e retorno marginal é parte da premissa, não conclusão.

Três avisos de leitura, todos consequência da revisão v2 → v3:

**Primeiro: o status das afirmações não é uniforme.** Cada proposição da §6 vem rotulada como **[identidade]** (verdadeira por álgebra, sob as premissas da §7), **[propriedade condicional]** (verdadeira sob uma convenção declarada, e possivelmente de sinal invertido sob outra) ou **[regularidade empírica]** (fato observado, não teorema). A v2 apresentava as três espécies com o mesmo peso retórico, e isso produziu pelo menos um erro de conclusão — documentado na nota de revisão.

**Segundo: a escolha da convenção terminal é a decisão que mais move o valor, e ela é ternária, não binária.** A v2 operava com duas convenções e as descrevia como os extremos de um eixo de fade. Estava errado: as duas convenções da v2 respondem a perguntas diferentes (o que colapsa vs. se colapsa), e faltava exatamente a convenção que corresponde ao sentido corrente de "a vantagem competitiva se exaure". Várias das proposições contraintuitivas da v2 eram propriedades de uma convenção específica apresentadas como propriedades da convergência competitiva em geral.

**Terceiro: reprodução numérica não é verificação.** Todas as tabelas da v2 reproduziam exatamente no motor do framework, e mesmo assim uma delas sustentava uma conclusão falsa, porque o defeito estava no rótulo e não no número. A v3 descreve o protocolo de validação de fato usado (Apêndice A) e enuncia as condições sob as quais suas proposições seriam falseadas (Apêndice B).

---

## Sumário

1. O problema: o múltiplo como heurística versus como resultado
2. Fundamentação I: o que o mercado realmente capitaliza
   - 2.1 Miller-Modigliani (1961) e a decomposição commodity/franquia
   - 2.2 A identidade do reinvestimento
   - 2.3 A fórmula dos value drivers
   - 2.4 A ponte para EBITDA — e por que ela é o elo fraco
   - 2.5 Equivalência com renda residual (EVA)
3. Fundamentação II: valor terminal é uma tese estratégica, não um parâmetro
   - 3.1 CAP: a variável negligenciada
   - 3.2 O que os dados dizem sobre a persistência — e sobre a mortalidade
   - 3.3 As três convenções do framework
   - 3.4 Por que o framework não implementa fade
4. Fundamentação III: consistência do custo de capital — e em que camada ela vale
5. O núcleo formal do framework
6. Resultados derivados (catorze proposições)
7. Limites de validade
8. Protocolo de aplicação e estado das extensões
9. Conclusão
- Apêndice A — protocolo de validação
- Apêndice B — condições de falseamento
- Apêndice C — caso trabalhado de ponta a ponta
- Referências · Nota de revisão v2 → v3

---

## 1. O problema: o múltiplo como heurística versus como resultado

A prática de mercado é dominada por múltiplos. Levantamento de mais de um milhão de relatórios de sell-side entre 2000 e 2025 mostra que múltiplos — e o P/L em particular — dominam o DCF na frequência de uso, com variação geográfica relevante (múltiplos predominam na América do Norte e Ásia; DCF na Europa, América do Sul e Austrália). O mesmo estudo encontra um resultado desconfortável: analistas mais habilidosos ficam mais precisos quando usam DCF, enquanto os menos habilidosos ficam piores — o modelo não substitui o julgamento (Bastianello, Décaire & Guenzel, 2025, apud Mauboussin & Callahan, 2026).

A objeção teórica ao múltiplo como ferramenta primária é conhecida e tem duas formulações complementares:

**(i) Damodaran.** Todo múltiplo carrega, embutidas, todas as variáveis que dirigem qualquer DCF — crescimento, risco e padrão de caixa. Com álgebra elementar sobre um DCF simples é possível extrair explicitamente os fundamentos que dirigem cada múltiplo. Daí decorre a proposição frequentemente ignorada: empresa comparável não é empresa do mesmo setor, é empresa com os mesmos fundamentos — não há razão para não comparar firmas de negócios completamente distintos se compartilham risco, crescimento e características de fluxo de caixa. Cada múltiplo tem uma *companion variable* que o dirige de forma dominante: para EV/EBITDA, a necessidade de reinvestimento; para EV/Capital, o retorno sobre o capital; para P/B, o ROE.

**(ii) Mauboussin.** Múltiplos não ajudam a pensar sobre a duração da vantagem competitiva porque são o produto conjunto de ROIC, crescimento, risco e vantagem competitiva, praticamente impossíveis de destrinchar depois de agregados. Pode-se dizer que uma empresa negociando ao "múltiplo de commodity" não embute criação de valor e que múltiplos altos embutem expectativas altas — mas as premissas permanecem implícitas.

O framework aceita ambas as objeções e responde com uma inversão: em vez de abandonar o múltiplo, derivá-lo. Se o múltiplo é um DCF comprimido, explicitar a compressão devolve o poder analítico destruído pela agregação — e permite ler o múltiplo de tela como um sistema de equações a resolver (engenharia reversa).

Uma qualificação que a v2 não fazia e que organiza todo o resto: **derivar o múltiplo não elimina o julgamento, apenas o desloca e o torna auditável.** O que era um julgamento agregado e tácito ("15x parece caro") vira um conjunto de julgamentos separados e discutíveis (duração da vantagem, retorno do capital novo, nível normalizado da métrica-base). O ganho é de rastreabilidade e de localização do desacordo, não de objetividade. Um framework que promete objetividade a partir de premissas escolhidas pelo analista está mentindo sobre a própria natureza.

---

## 2. Fundamentação I: o que o mercado realmente capitaliza

### 2.1 Miller-Modigliani (1961) e a decomposição commodity/franquia

O ponto de partida moderno é *Dividend Policy, Growth, and the Valuation of Shares* (Miller & Modigliani, 1961). O artigo pergunta o que o mercado de fato capitaliza e mostra que, tratadas corretamente, as diversas abordagens (dividendos, fluxo de caixa, lucros, oportunidades de investimento) convergem ao mesmo valor — de onde decorre, como implicação e não como premissa, a irrelevância da política de dividendos.

Da abordagem "lucros correntes mais oportunidades futuras de investimento" resulta a formulação que interessa aqui:

> Valor = NOPAT/W + [Investimento × (ROIC − W) × T] / [W × (1 + W)]

onde T é o horizonte de oportunidades de investimento com retorno acima do normal — que a literatura posterior batizaria de CAP.

Essa decomposição é a espinha dorsal do framework, por três razões:

1. **Separa o múltiplo em componente commodity e componente franquia.** O primeiro termo, NOPAT/W, é o valor de uma **perpetuidade de NOPAT normalizado e sustentável, sem crescimento incremental com VPL adicional** — não automaticamente "o valor dos ativos existentes": essa leitura exige NOPAT normalizado, nível sustentável por prazo indefinido, reinvestimento de manutenção refletido e ausência de vida útil finita relevante. Uma mina, patente ou concessão pode valer legitimamente *menos* que NOPAT/W sem nenhuma expectativa de destruição de valor. Para uma empresa financiada só com equity, o "P/L de commodity" é simplesmente 1/Ke: a 8% de custo de equity, 12,5x. Qualquer prêmio sobre isso é, por construção, expectativa de criação de valor futura (PVGO) — condicionado à sustentabilidade do nível.
2. **Torna óbvio o papel do retorno marginal.** Se o ROIC do capital novo iguala o custo de capital, o segundo termo zera — independentemente do tamanho do investimento.
3. **Qualifica o crescimento pelo retorno incremental.** Crescimento acelerado adiciona muito valor com spread grande e destrói valor com spread negativo. MM são explícitos: a essência do crescimento não é expansão, mas a existência de oportunidades de aplicar volumes relevantes de capital acima da taxa normal.

Magnitude empírica **[regularidade empírica]**: entre 1961 e 2025, o valor de estado estacionário representou em média dois terços do preço do S&P 500 e o PVGO um terço; no início de 2026 os dois estavam aproximadamente equalizados. Há evidência de que a razão PVGO/preço prevê retornos de dez anos — razões baixas antecedem retornos acima da média (Mauboussin & Callahan, 2026).

### 2.2 A identidade do reinvestimento

A ponte entre MM e a forma operacional do framework é uma identidade contábil-econômica:

> Se todo crescimento vem de capital novo e o capital marginal rende ROIC constante, então **g = RiR × ROIC**, logo RiR = g/ROIC e **FCFF = NOPAT × (1 − g/ROIC)**.

A genealogia é a literatura de crescimento sustentável. Higgins (1977) formalizou a pergunta "quanto crescimento a firma pode bancar" e derivou g_sustentável = ROE × (1 − payout) sob política de dividendos e alavancagem-alvo constantes, argumentando que qualquer trajetória diferente da sustentável não se mantém: crescer acima obriga a captar; crescer abaixo acumula caixa ocioso. A versão enterprise substitui ROE por ROIC e payout por (1 − RiR).

O conteúdo econômico é mais forte do que parece: crescimento não é grátis e tem preço explícito — cada ponto de g custa 1/ROIC de reinvestimento por unidade de NOPAT. Quando g/ROIC > 1, o crescimento não é autofinanciável; o FCFF é negativo e a firma consome capital externo, mesmo que o P&L pareça saudável. Este é o primeiro diagnóstico obrigatório do framework.

**Qualificação da v3 (o corolário do RiR foi rebaixado de veredicto a hipótese).** A v2 afirmava que RiR > 100% sem captação planejada significa que o evento foi classificado errado. A afirmação correta é mais fraca e mais útil: RiR > 100% torna o crescimento não autofinanciável e **exige uma fonte de funding declarada**. Sem funding plausível, a hipótese forte é erro de classificação (um degrau de nível lançado como taxa — §6.10). Mas empresas reais crescem acima do autofinanciável com funding externo legítimo, e um diagnóstico que trata financiamento como impossibilidade produz falsos positivos em toda companhia em fase de expansão financiada. O RiR estourado **abre a investigação; não a encerra**.

**O lado equity, e a natureza do termo de caixa.** No lado equity a identidade é análoga, com um termo adicional que a literatura de manual normalmente omite: parte do crescimento do ativo é financiada por dívida nova (mantendo D/E constante) e parte do lucro retido vira caixa que se acumula no balanço:

> FCFE = LL × [ (1 − g/ROE) + (GD/E − ND/E) × (g/ROE) ]

onde GD/E − ND/E = Caixa/Equity, e o payout emerge endogenamente do sweep de caixa em vez de ser input. Isso importa para empresas com caixa líquido relevante, cujo P/L justo é sistematicamente subestimado pelas fórmulas de manual.

A v3 acrescenta duas precisões ausentes da v2, ambas materiais:

**(a) Isto é um módulo de política financeira, não uma identidade universal.** O termo pressupõe proporção de caixa constante com payout endógeno. Sob outra política — caixa excedente distribuível de uma vez, por exemplo — a rota correta é avaliar a operação com caixa/E = 0 e somar o caixa excedente separadamente. As duas rotas devem ser reconciliadas sob a política declarada, e a política precisa aparecer na entrega.

**(b) A política vale também no terminal.** Se a proporção de caixa é constante e o equity cresce a gp na perpetuidade, o FCFE terminal canônico é

> FCFE_TV = LL_{n+1} × [ (1 − gp/ROE_TV) + (Caixa/E) × (gp/ROE_TV) ]

O termo de caixa **no terminal** foi omitido pela v2, e a omissão subestima o P/L em 2% a 6% em parâmetros plausíveis. A forma acima é o FCFE canônico — verificável por três rotas independentes que devem coincidir no balanço terminal crescendo a gp: dividendos + Δcaixa; FCFF − juros(1−t) + emissão de dívida; e o fator fechado acima. Encerrar a política de caixa no ano n é hipótese legítima, mas é hipótese e precisa ser declarada como tal.

### 2.3 A fórmula dos value drivers

Substituindo a identidade na perpetuidade de Gordon obtém-se a *key value driver formula*, popularizada por Rappaport e pela McKinsey (Koller, Goedhart & Wessels):

> EV = NOPAT₁ × (1 − g/ROIC) / (W − g) ⟹ EV/NOPAT₁ = (1 − g/ROIC) / (W − g)

Duas leituras imediatas: (a) a empresa só cria valor se ROIC > custo de capital; (b) só nesse caso o crescimento aumenta o valor — com ROIC < W, crescer reduz o valor. Fazendo ROIC = W, a fórmula colapsa em NOPAT/W, independente de g: é a neutralidade de MM reaparecendo por outro caminho.

O framework **não usa a forma fechada como motor**. Usa soma explícita dos fluxos ao longo do CAP mais valor terminal, por dois motivos técnicos e um conceitual:

- a singularidade g → W da forma fechada desaparece no somatório (a rigor, ROIC = W isolado não é singularidade — o ponto conjunto g = ROIC = W é indeterminação 0/0 removível, com limite NOPAT/W);
- o CAP finito permite rentabilidade diferente no explícito e no terminal — o problema que Bodmer identifica como o principal defeito da forma fechada (ela quebra quando o retorno terminal difere do histórico);
- conceitualmente, separar explícito e terminal é o que permite **decidir** sobre a duração da vantagem competitiva em vez de assumi-la implicitamente.

Sobre o segundo ponto, a v3 registra uma correção importante ao que a v2 afirmava: separar explícito e terminal é condição **necessária mas não suficiente** para endereçar a crítica de Bodmer. A conflação entre retorno médio e retorno marginal pode reaparecer dentro do próprio valor terminal, e reaparecia. Ver §6.11.

### 2.4 A ponte para EBITDA — e por que ela é o elo fraco

Como NOPAT = EBITDA × (1 − d) × (1 − t), segue-se diretamente

> EV/EBITDA = EV/NOPAT × (1 − d) × (1 − t)

Isso significa que EV/EBITDA **não é um múltiplo primitivo**: é o múltiplo de NOPAT contaminado por dois parâmetros contábeis-fiscais. Duas empresas idênticas em g, ROIC, W e CAP negociarão a múltiplos de EBITDA diferentes se tiverem intensidade de D&A ou alíquota efetiva diferentes — sem nenhuma diferença econômica. Damodaran chega ao mesmo lugar por outra rota, decompondo o FCFF em termos de EBITDA e mostrando que depreciação e capex entram separadamente na determinação do múltiplo.

Historicamente o EV/EBITDA é recente — popularizado nos anos 1970-80, associado a John Malone e à indústria de buyout — e sua adoção tem mais a ver com comparabilidade entre estruturas de capital do que com fundamento econômico. O framework o usa porque é a linguagem do mercado, mas sempre como derivado, nunca como âncora.

**Decomposição obrigatória do d (v3).** Tratar d como um número só é fonte de erro silencioso quando a D&A tem componentes de naturezas distintas: *depletion* e amortização de direitos minerários seguem produção (§6.6); amortização de arrendamento sob IFRS-16 é aluguel reclassificado, e exige coerência de fronteira (ou EBITDA pré-IFRS-16 com aluguel no custo, ou d incluindo a amortização **e** a dívida de arrendamento no endividamento líquido — nunca meio a meio); amortização de PPA de aquisições é não-caixa sem capex de reposição correspondente e infla o d economicamente relevante. Reporte o d contábil e o d ajustado quando divergirem.

### 2.5 Equivalência com renda residual (EVA)

Um teste de consistência interna do framework é a reconciliação exata com a abordagem de lucros econômicos:

> EV = Capital Investido₀ + Σ IC_{t−1} × (ROIC − W) / (1 + W)ᵗ

Essa equivalência não é coincidência: é o *clean surplus* / teorema de Preinreich–Lücke, reconhecido desde Lücke (1955) e formalizado na literatura contábil moderna por Edwards & Bell (1961), Peasnell (1982), Ohlson (1995) e Feltham & Ohlson (1995) — o valor de mercado equivale ao valor contábil mais o valor presente dos lucros anormais futuros, desde que toda variação de patrimônio passe pelo resultado.

Duas advertências, ambas relevantes na prática. Primeira, a equivalência DCF↔renda residual só é rigorosa em horizonte infinito (Penman); em horizontes finitos, os dois métodos alocam valor de forma diferente entre explícito e terminal, e a escolha deixa de ser inócua. Segunda, Ohlson modela a extinção do lucro anormal por um processo autorregressivo — o poder monopolista decai com a competição até o retorno igualar o custo de capital.

**A v3 acrescenta o que esta equivalência de fato demonstra, e o que ela não demonstra.** A reconciliação exata (verificada a 1e-15 no motor) prova que a convenção terminal de valor-contábil é **internamente consistente**: se o valor terminal é o capital investido, então o valor total é o capital inicial mais a renda residual descontada, sem resíduo. Isso é um teorema. O que a reconciliação **não** prova é que essa convenção corresponda a qualquer afirmação econômica particular sobre competição — em especial, não prova que ela seja a tradução de "a vantagem competitiva se exaure". A v2 tratava a consistência algébrica como se validasse o rótulo econômico. São camadas distintas, e a §3.3 as separa.

---

## 3. Fundamentação II: valor terminal é uma tese estratégica, não um parâmetro

### 3.1 CAP: a variável negligenciada

A duração da vantagem competitiva foi tratada por Rappaport, em *Creating Shareholder Value*, sob o nome "value growth duration", e formalizada por Mauboussin & Johnson (1997) como *competitive advantage period*. O insight operacional de Rappaport é que o CAP pode ser lido do preço: estende-se o horizonte explícito até que o modelo reproduza a cotação, e o número de anos resultante é o CAP implícito no mercado (MICAP). A pergunta deixa de ser "o que eu acho" e passa a ser "o que o mercado está exigindo".

Isso importa porque o valor terminal costuma responder por 70% ou mais do valor total em modelos com horizonte explícito de dez anos ou menos — e porque Graham já apontava, revisando John Burr Williams em 1938, que o terminal calculado por múltiplo convencional respondia por 95% do valor no estudo de caso do próprio Williams.

**Precisão da v3 sobre o CAP implícito.** O CAP implícito é uma leitura **condicional a todas as demais premissas e à convenção terminal**, não uma medida do horizonte de vantagem percebido pelo mercado. Mudou a convenção, mudou o CAP implícito; mudou o ROIC marginal, idem. Reportá-lo sem esse condicionamento é o mesmo erro de superprecisão que a §6.7 denuncia na reversa em geral. O motor devolve o CAP interpolado entre anos inteiros, com a condicionalidade explicitada — e, quando a série valor(n) não é monótona, avisa que mais de um horizonte reconcilia o preço.

### 3.2 O que os dados dizem sobre a persistência — e sobre a mortalidade

**[regularidade empírica]** A escolha da convenção terminal não precisa ser arbitrária. A evidência sobre companhias americanas (1970–2024, excluindo financeiras) fornece âncoras:

| Fato empírico | Implicação para o framework |
|---|---|
| Cerca de metade das observações firma-ano tem spread ROIC−WACC positivo; ROIC agregado ajustado médio de 9,2% | Spread positivo não é regra, é seleção |
| Correlações de 5 anos do ROIC por setor: 0,59 (consumo básico) a 0,16 (utilities) | A persistência é setorial, não universal |
| Fade implícito: média 0,21, faixa de 0,10 a 0,30 | Um fade de 0,20 equivale a spread por ~5 anos e depois convergência |
| Persistência caiu de 1950 a 2000 e subiu desde então; grandes empresas persistem mais | O CAP não é constante no tempo nem no *size* |
| Tempo médio de listagem 11,7 anos, mediana 6,8; de cada 100 IPOs, 18 sobrevivem | Perpetuidade é uma ficção contábil, não um fato |

Cerca de 70% das companhias produziram lucros de vida inteira insuficientes para justificar o preço da própria abertura de capital.

**O problema que a v2 levantou e não resolveu.** A v2 afirmava que "modelar crescimento perpétuo sem considerar mortalidade corporativa é um descasamento estrutural, não um detalhe de calibragem" — e em seguida usava perpetuidades sem nenhum ajuste de sobrevivência. Isso é uma inconsistência entre o que o documento diz saber e o que o motor faz, e ela precisa ser resolvida em uma de duas direções.

**O que os dados de listagem medem, e o que não medem (qualificação da v3.2).** Os números acima são hazards de **saída de bolsa**, e saída de bolsa não é extinção econômica com recuperação zero: uma aquisição realiza valor para o acionista e transfere o ativo ao comprador, sem zerar o claim; um fechamento de capital muda o dono da informação, não o fluxo. O λ que o ajuste abaixo consome é o hazard de **extinção econômica**, com recuperação declarada — objeto diferente, e menor. Os dados de listagem motivam a pergunta e ancoram a ordem de grandeza; não estimam o parâmetro.

A magnitude não é decorativa. Sob a convenção `gordon`, um *hazard rate* λ de extinção econômica com **recuperação zero**, incorporado ao crescimento perpétuo pela aproximação contínua gp líquido = gp − λ, produz:

| λ (hazard anual) | gp efetivo | EV/NOPAT | efeito |
|---|---|---|---|
| 0% | +3% | 23,41 | — |
| 2% | +1% | 19,54 | −16,5% |
| 3% | 0% | 18,44 | −21,2% |
| 5% | −2% | 16,97 | −27,5% |

*(ROIC 15%, ROIC_TV 15%, W 7%, g 5%, n 10.)*

**A forma exata em tempo discreto.** gp − λ é aproximação. Com extinção exponencial e recuperação zero, o fluxo esperado do período t é o fluxo condicional vezes a probabilidade de sobrevivência, e o crescimento líquido exato é

> (1 + g_liq) = (1 + g)(1 − λ)  ⟹  **g_liq = g − λ − gλ**

O termo cruzado −gλ é de segunda ordem (a 5% e 3% vale −0,15 p.p.) e a aproximação contínua é adequada para taxas pequenas, mas a forma exata é a que deve constar quando λ ou g forem grandes. Com recuperação R > 0 no evento de extinção, o ajuste deixa de ser um deslocamento de g e vira um termo aditivo próprio — e nesse caso a sensibilidade tem de ser recalculada, não reaproveitada da tabela.

**A posição da v3 é a segunda direção, declarada:** o framework **não** embute mortalidade, e o viés resultante é conhecido e unidirecional — o valor terminal de qualquer convenção com gp > 0 está superestimado em relação a um mundo com extinção corporativa. Duas razões para não embutir: (i) o hazard rate relevante é específico da firma e do momento, e uma taxa genérica trocaria um viés explícito por um parâmetro falsamente preciso; (ii) o analista que quiser incorporá-lo pode fazê-lo sem alteração no motor, informando gp líquido de λ — o que mantém a hipótese visível na entrada em vez de escondida na engrenagem. O que a v3 exige é que a **direção do viés seja declarada** quando o valor terminal dominar o valor total, que é o caso normal.

### 3.3 As três convenções do framework

A frase "a vantagem competitiva se exaure no ano n" admite mais de uma matemática, e a distinção entre elas é a correção mais importante desta revisão.

**(a) `book` — renda residual truncada.** O NOPAT **inteiro** colapsa de ROIC × IC para W × IC no ano n+1; como os excess returns zeram sobre **todo** o capital, o valor terminal é o capital investido, e crescimento perpétuo é value-neutral.

> TV_desc = (1+g)ⁿ⁺¹ / [ROIC_book × (1+W)ⁿ]

**(b) `convergencia` — RONIC = W no capital novo.** Apenas os investimentos **novos** deixam de criar valor; o NOPAT existente é preservado e continua rendendo o que rende.

> TV_desc = (1+g)ⁿ⁺¹ / [W × (1+W)ⁿ]

**(c) `gordon` — spread declarado na perpetuidade.** Rentabilidade terminal e crescimento perpétuo livres, com gp < W obrigatório. A rentabilidade terminal é a **marginal terminal** (RONIC/ROIIC): na identidade gp = RiR_TV × RONIC_TV, é o retorno do capital incremental que sustenta gp — o blended do portfólio só serve de proxy sob hipótese declarada de convergência entre retorno médio e marginal no estado estacionário (v3.5).

> TV_desc = (1+g)ⁿ⁺¹ × (1 − gp/ROIC_TV) / [(W − gp) × (1+W)ⁿ]

**Por que isto importa mais do que parece.** A convenção (b) é o significado corrente de "a vantagem competitiva se exaure" na literatura de referência (McKinsey, Mauboussin): o crescimento terminal vira value-neutral porque o capital novo passa a render o custo de capital, e não porque o negócio existente deixa de ser rentável. A convenção (a) afirma algo bem mais forte — que o valor de saída da empresa é o capital contábil. A v2 usava (a) sob o rótulo de (b).

A diferença é da ordem do dobro do valor. Com ROIC 50%, g 5%, W 7%, n 10: **`book` 9,86x contra `convergencia` 20,55x** em EV/NOPAT corrente. As duas coincidem exatamente em ROIC = WACC, e divergem monotonicamente à medida que o ROIC se afasta do custo de capital — o que significa que a escolha entre elas é irrelevante para empresas medíocres e decisiva para franquias, exatamente onde a análise importa.

**O critério de escolha é a duração econômica do claim, não o rótulo do setor.** A v2 oferecia uma tabela por classe de negócio (royalty ⟹ spread; commodity ⟹ ic). É um atalho que funciona no caso fácil e falha no caso interessante: um contrato de streaming com termo de 15 anos é horizonte explícito longo, não perpetuidade; uma "marca dominante" em categoria sob disrupção não é claim de longa duração. O que decide é o argumento sobre **por quanto tempo o claim gera retorno acima do custo de capital, e o que sobra quando ele acaba** — e esse argumento tem que ser escrito, não inferido do setor.

Três guias operacionais:

- **`book`** quando o valor contábil for âncora crível de valor de saída: price-taker de commodity sem franquia, negócio regulado com base de remuneração, ativo cuja alternativa é a liquidação.
- **`convergencia`** como default reflexivo quando a tese é "a vantagem acaba" sem afirmação adicional sobre o valor do estoque. É a convenção menos comprometida das três.
- **`gordon`** quando houver argumento de duração (claim contratual longo, rede, marca) **ou** quando a tese for de destruição persistente declarada (ROIC_TV < W) — regime legítimo que as outras duas não conseguem representar. Nomeie a hipótese pelo que ela é: **spread terminal positivo pressupõe oportunidades de reinvestimento com VPL positivo em perpetuidade** — o modelo precifica essa hipótese, não demonstra sua origem, defesa ou limite de mercado.

**Trava condicional (revista na v3.2).** Quando a rentabilidade marginal fica abaixo do custo de capital, a convenção `book` é **inadmissível no caso conflacionado e condicionada no caso separado**. Conflacionado (um único retorno nos dois papéis): vale a perversidade demonstrada em §6.3 — o TV = NOPAT/ROIC cresce quando o ROIC cai, e a convergência do ROIC *para cima* até o WACC é, para um destruidor de valor, uma hipótese criadora de valor embutida sem declaração. Separado (retorno médio informado à parte): o TV = NOPAT/ROIC_médio **não acompanha o marginal**, a perversidade não existe — o múltiplo cai monotonicamente com o marginal — e a convenção permanece admissível sob **tese declarada** de saída pelo capital investido (turnaround, capex regulatório, reconstrução operacional, liquidação, venda pelo patrimônio). O que a separação marginal×médio (§6.11) corrigiu no valor terminal vale igualmente para a regra de uso. **Sub-condição:** se o próprio retorno médio ficar abaixo do custo de capital, o TV excede NOPAT/WACC pelo fator W/ROIC_médio — cruzamento exato em ROIC_médio = WACC — e a hipótese passa a ser de **recuperação** acima do valor capitalizado de lucros sub-custo, que exige tese própria.

### 3.4 Por que o framework não implementa fade

Mauboussin & Callahan (2026) apresentam quatro modelos terminais — Gordon, value driver, perpetuidade e fade (este devido a David Holland) — e demonstram que todos coincidem quando o retorno incremental iguala o custo de capital, divergindo apenas sob excess returns sustentados. No modelo de fade, o terminal se escreve como *estado estacionário + valor do moat × persistência*, com f = 1 significando convergência imediata e f = 0 criação de valor perpétua. A evidência empírica oferece calibragem setorial (média 0,21, faixa 0,10–0,30).

A v2 afirmava que suas duas convenções eram "exatamente os dois extremos desse eixo" e recomendava implementar fade intermediário como extensão prioritária. **A v3 retira as duas afirmações.**

A primeira estava errada de fato: `book` não é o extremo f = 1 de um eixo de fade. Um fade alto descreve a velocidade com que o **spread** decai; a convenção `book` descreve o **valor do estoque** ao fim do CAP. São eixos diferentes, e é por isso que faltava uma convenção — a `convergencia`, que é o que um fade completo de fato produz.

A segunda é uma decisão de projeto, e as razões são explícitas:

1. **O parâmetro não é observável na firma, só na população.** Fades setoriais são médias de amostras heterogêneas; aplicá-los a uma firma específica importa dispersão como se fosse informação. Substituir uma escolha declarada ("assumo que a vantagem acaba no ano 10") por um parâmetro contínuo calibrado em outra amostra troca uma hipótese visível por uma hipótese invisível com aparência de calibragem.
2. **Ele suaviza exatamente o que precisa ficar áspero.** O valor do framework está em forçar a decisão sobre duração da vantagem a ser escrita e defendida. Um fade de 0,21 dilui essa decisão em um número que ninguém discute.
3. **O ganho de precisão é ilusório dentro do próprio framework.** Com três convenções nomeadas, o intervalo entre `book` e `gordon` já é reportado e já mede quanto do valor depende da hipótese terminal. Um ponto interior a esse intervalo não adiciona informação — apenas escolhe um ponto sem argumento.
4. **Interação com a mortalidade (§3.2).** Fade e hazard rate atuam sobre a mesma região do valor por mecanismos diferentes; calibrar um enquanto se ignora o outro produz falsa precisão em cima de viés não corrigido.

A posição da v3, portanto: **o eixo de fade é uma boa descrição do fenômeno e um mau parâmetro de modelo.** Reportar o intervalo entre convenções é declarar honestamente a ignorância sobre a duração; estimar f é fingir tê-la resolvido.

---

## 4. Fundamentação III: consistência do custo de capital — e em que camada ela vale

O framework impõe que Ke e WACC nunca sejam inputs independentes. A razão é teórica e o histórico do debate é instrutivo.

Modigliani & Miller (1958, 1963) estabeleceram o efeito da alavancagem sobre o valor, mas trataram apenas perpetuidades e não enfrentaram o risco do próprio benefício fiscal. Myers (1974) introduziu o APV — valor da firma desalavancada mais o valor presente dos escudos fiscais — descontando os escudos ao custo da dívida, sob o argumento de que o risco dos escudos é o risco da dívida. Miles & Ezzell (1980) mostraram que, sob dívida rebalanceada para manter alavancagem-alvo a valor de mercado, os escudos passam a carregar risco operacional e devem ser descontados a Ku a partir do primeiro período. Harris & Pringle (1985) levaram isso ao limite, descontando tudo a Ku. Fernández sistematizou até 23 teorias concorrentes de valor dos escudos fiscais e demonstrou que descontar escudos de dívida livre de risco à taxa livre de risco produz resultados inconsistentes para empresas em crescimento.

A resposta do framework é metodológica, não doutrinária: **ancorar em Ku** (custo do equity desalavancado, exógeno) e tratar Ke e WACC como outputs período a período, via recursão *backward*. A recursão está implementada e reconcilia por construção: o FCFE descontado à trilha Ke_t reproduz o equity inicial, e o FCFF descontado à trilha WACC_t reproduz o valor da firma, ambos a zero de resíduo, com o Ke dinâmico coincidindo com a fórmula de Fernández.

**A distinção que a v2 não fazia — e é uma inconsistência interna corrigida aqui.** A v2 listava entre os erros "eliminados por construção" o *Ke fixo quando a alavancagem a mercado deriva*. Isso é verdade na camada APV e **falso na camada do múltiplo**. O motor de múltiplos toma Ke como input exógeno e constante ao longo do CAP, enquanto a política de caixa e dívida (GD/E, ND/E) entra separadamente. São duas camadas com garantias diferentes:

| Camada | Ke | Garantia |
|---|---|---|
| APV / recursão | output período a período, ancorado em Ku | consistência FCFE↔FCFF exata |
| Fórmula de múltiplos | input fixo | nenhuma — o Ke não responde à estrutura de capital informada |

A consequência prática é específica e vale a pena enunciar como regra: **comparar cenários que diferem em estrutura de capital sob o mesmo Ke atribui à política de caixa um efeito que em parte pertence à taxa de desconto.** A ordem de grandeza: com Ku 14%, Kd 9% e alíquota 30%, passar de D/E = 0 para D/E = 0,5 eleva o Ke consistente de 14,00% para 15,75%; manter o Ke congelado nesse movimento superestima o P/L em 16%. E mesmo dentro de um único cenário, a alavancagem a mercado deriva ao longo do CAP — no caso-base do modelo de referência, o Ke consistente vai de 20,56% no ano 1 a 21,74% no ano 10, de modo que um Ke único não é o Ke de nenhum período.

Duas saídas admissíveis, ambas explícitas: (i) rodar a recursão APV, extrair Ke_t e realimentar a fórmula de múltiplos cenário a cenário; (ii) manter Ke fixo e **declarar** que a comparação entre cenários é *ceteris paribus* em custo de capital. O que não é admissível é a terceira, que era a prática implícita da v2: apresentar a garantia da camada APV como se cobrisse a camada do múltiplo.

Três erros clássicos permanecem eliminados na camada APV: (i) pesos contábeis no WACC — que quebram a reconciliação FCFF↔FCFE, produzindo valores distintos pelas duas rotas (159,0 vs 150,5 no caso-base do modelo de referência); (ii) Ke fixo com alavancagem a mercado derivando; (iii) circularidade Ke↔WACC resolvida por iteração — comum na prática, mas que apenas esconde a inconsistência em vez de removê-la.

Na prática, o mais importante é a escolha da política de dívida implícita. Dívida determinística (MM) e dívida rebalanceada a uma alavancagem-alvo (Miles-Ezzell, Harris-Pringle) não são convenções intercambiáveis: são hipóteses econômicas diferentes sobre o comportamento financeiro da empresa, e produzem Ke diferentes. **O que o motor implementa (nota da v3.2):** dois regimes — `mm` e `ku`. O segundo aplica a convenção de *risco* dos shields de Harris-Pringle (todos descontados a Ku) sobre uma trajetória de dívida **exógena**, D_t = D₀(1+g)^t. Ele **não** resolve D_t = L×V_t e portanto não mantém D/V constante, que é a política subjacente tanto de Miles-Ezzell quanto de Harris-Pringle; a série D/V sai no output (`DV_t_%`) exatamente para que a diferença não fique implícita. Implementar rebalanceamento-alvo verdadeiro exige resolver a circularidade entre dívida e valor, e é roadmap planilha-primeiro. A discussão teórica desta seção descreve a literatura, não o estado do motor.

---

## 5. O núcleo formal do framework

**Múltiplo enterprise, base corrente:**

> EV/NOPAT_corrente = Σ_{t=1}^{n} (1 − g/ROIC)(1+g)ᵗ/(1+W)ᵗ + TV_desc

**Valor terminal, três convenções (§3.3):**

> TV_desc = (1+g)ⁿ⁺¹ / [ROIC_book × (1+W)ⁿ]  ............................ `book`
> TV_desc = (1+g)ⁿ⁺¹ / [W × (1+W)ⁿ]  ..................................... `convergencia`
> TV_desc = (1+g)ⁿ⁺¹ (1 − gp/ROIC_TV) / [(W − gp)(1+W)ⁿ]  ................ `gordon`

**Conversões:**

> EV/NOPAT_forward = EV/NOPAT_corrente / (1+g)
> EV/EBITDA = EV/NOPAT × (1−d)(1−t)

**Lado equity** — análogo com Ke, ROE e o fator de conversão do FCFE, com o termo de política de caixa no explícito **e** no terminal (§2.2):

> fator_explícito = (1 − g/ROE) + (Caixa/E)(g/ROE)
> fator_terminal (`gordon`) = (1 − gp/ROE_TV) + (Caixa/E)(gp/ROE_TV)

**Custo de capital (camada APV):**

> Ke_t = Ku + (D_{t−1} − VTS_{t−1})(Ku − Kd)/E_{t−1}  ..... MM/Fernández, dívida determinística
> Ke = Ku + (Ku − Kd) D/E  ................................ shields a Ku (Harris-Pringle; regime `ku` do motor, sobre dívida exógena)

**Convenções que precisam ser declaradas** (nenhuma é neutra, todas movem o resultado):

| Convenção | Default do motor | Efeito de trocar |
|---|---|---|
| Terminal (§3.3) | nenhum — escolha obrigatória | até ~2x no valor |
| Temporal: fim de ano vs meio de ano | fim de ano | × (1+W)^0,5 — +3,4% a 7%, +4,4% a 9% |
| Base do múltiplo: corrente/TTM vs forward/NTM | corrente | fator (1+g) |
| Política de caixa no terminal (§2.2) | contínua | 2% a 6% do P/L |
| Rentabilidade no TV da `book`: média vs marginal (§6.11) | marginal, com alerta | até ~30% do valor |
| Fluxo de transição no `gordon`: ano n+1 cresce a (1+g) ou a (1+gp) | (1+g), fiel à planilha de referência | **TV_share × [(1+gp)/(1+g) − 1]** — dirigido pelo gap g−gp; medições de −0,4% a −3,5% |

Sobre a última linha: a soma explícita termina no ano n e o terminal capitaliza o fluxo do ano
n+1 — mas o ano n+1 é o ano de **transição**, e há duas convenções para o seu crescimento. O
framework usa base_n × (1+g) (o ano de transição ainda cresce à taxa do explícito, retendo já à
razão gp/rentabilidade terminal — timing em que o investimento de t financia o crescimento de
t+1, internamente consistente e fiel à planilha de referência, que só arbitra o caso `book`, onde
NOPAT_TV/NOPAT_n = 1+g exatamente). Parte do sell-side usa base_n × (1+gp). A diferença atinge só
o termo de TV, pelo fator (1+gp)/(1+g), logo o efeito relativo é a fórmula da tabela — e o motor
o calcula caso a caso em vez de reportar faixa. Nenhuma das duas é errada; não declarar qual está
em uso é.

Seis variáveis para o lado enterprise (g, ROIC, W, n, d, t) e seis para o lado equity (g, ROE, Ke, n, caixa/equity, payout implícito) — mais as seis convenções acima, que a v2 tratava como detalhes de implementação e a v3 trata como parte da especificação. Toda a §6 são consequências dessas expressões.

---

## 6. Resultados derivados

As proposições a seguir foram verificadas no motor do framework (soma explícita, sem forma fechada), com W = 7%, n = 10, d = 15%, t = 15% salvo indicação em contrário. **Cada uma vem rotulada com seu status epistemológico** — a v2 apresentava identidades, propriedades condicionais e regularidades empíricas com o mesmo peso, e isso produziu erro de conclusão. Onde a proposição contraria a intuição corrente, isso está sinalizado.

### 6.1 A neutralidade é exata, não aproximada · **[identidade]**

**Proposição.** Com ROIC = W, o múltiplo forward é exatamente 1/W, invariante a g.

| g | EV/NOPAT corrente | EV/NOPAT forward | 1/W |
|---|---|---|---|
| 0% | 14,2857 | 14,2857 | 14,2857 |
| 3% | 14,7143 | 14,2857 | 14,2857 |
| 6% | 15,1429 | 14,2857 | 14,2857 |
| 9% | 15,5714 | 14,2857 | 14,2857 |

A identidade vale nas convenções `book` e `convergencia`, que **coincidem exatamente** neste ponto — ROIC = WACC é o único ponto do espaço de parâmetros em que a escolha da convenção terminal é irrelevante. Verificada por *property test* em 360 combinações de (W, n, g) e nas duas convenções.

**Consequência prática.** O "P/L de commodity" de MM (§2.1) não é aproximação didática: é o valor exato ao qual a empresa converge quando a franquia desaparece **e o nível de NOPAT é sustentável**. Ele fornece um piso analítico — condicionado à sustentabilidade: para NOPAT de vida finita ou em erosão estrutural (mina, patente, concessão, negócio em declínio), o múltiplo justo fica legitimamente *abaixo* de 1/W sem que isso precifique destruição de valor futura. Onde a condição vale, qualquer múltiplo acima de 1/W é, por identidade, precificação de criação de valor futura, e pode ser interrogado como tal. (A identidade de §6.1 em si — ROIC = W ⟹ forward = 1/W — não carrega este qualificador: ela é exata *dentro* das premissas de §7; o qualificador pertence à leitura econômica do 1/W como piso, não à álgebra.)

**Adendo — o lado equity tem uma condição a mais.** ROE = Ke só é linha de neutralidade quando caixa/E = 0. Com caixa líquido, o termo (GD/E − ND/E)(g/ROE) do FCFE libera caixa a cada ponto de crescimento e o P/L forward sobe com g mesmo sem spread algum (Ke 12%, n 10: caixa/E 0% mantém 8,3333 = 1/Ke para todo g; caixa/E 20% vai a 9,04 em g = 6%; caixa/E 50%, a 10,10). Não é artefato — é o valor de não precisar reter o lucro inteiro para financiar o crescimento, já que dívida nova acompanha a expansão do balanço. Consequência analítica: a matriz g × ROE de uma empresa com caixa **não tem coluna plana**, e o gradiente em g mistura spread com liberação de caixa; separe os dois antes de atribuir o movimento do múltiplo à rentabilidade.

**Adendo 3 (v3.3, auditoria matemática) — a condição completa sob `book`.** O enunciado acima pressupõe marginal = médio. Com os papéis separados (P6.11), a neutralidade sob `book` exige **simultaneamente** ROIC marginal = W (zera o efeito-valor do reinvestimento no explícito) e ROIC book = W (o TV = 1/(ROIC_book(1+W)ⁿ) só entrega o complemento da anuidade nesse ponto). Com marginal = W e book = 20% (W 7%, n 10, g 6%), o forward é 5,83x — não 14,29x. A exceção é g = 0 com book = W: o marginal só entra via g/ROIC e a neutralidade vale para qualquer marginal. Sob `convergencia` e `gordon` o book não referencia o TV e marginal = W basta. Verificado por *property test* dedicado aos casos cruzados (marginal = W × book ≠ W e vice-versa).

**Adendo 2 (v3) — a linha g = 0 por convenção.** A linha g = 0 é plana em rentabilidade nas convenções `gordon` e `convergencia` (cujos terminais não referenciam o ROIC do explícito) e no limite n → ∞. Na `book` com CAP finito ela **não** é plana: o terminal 1/(ROIC_book(1+W)ⁿ) depende da rentabilidade — 23,97x a ROIC 3% contra 8,04x a ROIC 50% (W 7%, n 10). A neutralidade da matriz perpétua clássica não sobrevive integralmente à implementação com horizonte finito e terminal de valor contábil.

### 6.2 O sinal do gradiente em g é o sinal do spread — mas só na base forward · **[identidade]**

**Proposição.** ∂(múltiplo)/∂g tem o sinal de (ROIC − W) na base forward. Na base corrente, o reajuste (1+g) contamina o resultado e pode inverter o sinal aparente.

| ROIC | spread | base | g=0% | g=2% | g=4% | g=6% |
|---|---|---|---|---|---|---|
| 5% | −2,0 p.p. | corrente | 17,191 | 17,297 | 17,368 | 17,400 |
| 5% | −2,0 p.p. | forward | 17,191 | 16,957 | 16,700 | 16,415 |
| 7% | 0,0 | forward | 14,286 | 14,286 | 14,286 | 14,286 |
| 10% | +3,0 p.p. | forward | 12,107 | 12,282 | 12,475 | 12,689 |

**Consequência prática — e armadilha.** Na base corrente, uma empresa que destrói valor ao crescer (ROIC 5% contra WACC 7%) exibe múltiplo justo crescente em g. Um analista que monte a matriz g × ROIC na base corrente e leia "o múltiplo sobe com o crescimento, logo crescer é bom" chegará à conclusão oposta à verdadeira. Declarar a base da tabela não é preciosismo de formatação: é condição de validade da leitura econômica.

### 6.3 A monotonicidade em ROIC depende da convenção — e inverte de sinal · **[propriedade condicional]**

**Proposição (revista na v3).** O sinal de ∂(múltiplo)/∂ROIC é **propriedade da convenção terminal**, não da hipótese de convergência competitiva: negativo sob `book`, positivo sob `convergencia` e sob `gordon`.

g = 5%, EV/NOPAT corrente, W = 7%, n = 10:

| ROIC | `book` | `convergencia` | `gordon` (ROIC_TV 20%, gp 3%) |
|---|---|---|---|
| 5% | 17,389 | 12,421 | 18,476 |
| 7% | 15,000 | 15,000 | 21,055 |
| 10% | 13,208 | 16,934 | 22,990 |
| 20% | 11,118 | 19,191 | 25,246 |
| 50% | 9,864 | 20,545 | 26,601 |

**Explicação.** Sob `book` o valor terminal é o capital investido: uma empresa de ROIC alto precisa de pouco capital para gerar o mesmo NOPAT e portanto herda um terminal pequeno. A convenção penaliza estruturalmente franquias de alto retorno. Sob `convergencia`, o terminal é NOPAT/W e não referencia o book — o ROIC alto entra só pelo lado bom (menos reinvestimento para o mesmo g), e o múltiplo sobe.

**A correção mais importante desta revisão.** A v2 concluía: *"quem defende múltiplo alto por ROIC alto está, sem saber, assumindo que o moat é perpétuo"*. **Isso é falso.** Sob `convergencia` — que é convergência competitiva no sentido corrente, com o capital novo deixando de criar valor no ano n+1 — o múltiplo justo **sobe** com o ROIC, sem nenhuma hipótese de moat perpétuo. O que a v2 demonstrou, e continua verdadeiro, é mais estreito: *quem defende múltiplo alto por ROIC alto está rejeitando a convenção de valor terminal contábil*. Rejeitar `book` não é afirmar perpetuidade; é afirmar que o negócio existente vale mais que o capital que o financia — o que é uma tese muito mais fácil de defender e muito menos exigente.

**Corolário — a região condicionada (revisto na v3.2).** A monotonicidade decrescente da `book` vale em toda a faixa de ROIC, inclusive **abaixo** do custo de capital, onde vira perversidade **no caso conflacionado**: com W 7% e g 3%, o múltiplo forward é 30,20x a ROIC 2% contra 10,89x a ROIC 15%. Dois efeitos se somam — o terminal NOPAT/ROIC explode quando o ROIC cai, e a convergência do ROIC para cima até o WACC é, para um destruidor de valor, hipótese criadora de valor embutida sem declaração. **A perversidade é da conflação, não da convenção.** Com o retorno médio informado à parte, o terminal fica preso nele e a monotonicidade se inverte para o sinal correto: com W 7%, g 3% e ROIC_médio 10%, o múltiplo corrente vai de 2,96x a ROIC marginal 2% até 12,14x a 8% — sobe com a qualidade do investimento novo, como deve. Regra de uso: **sem retorno médio separado, a `book` é inadmissível abaixo do custo — modele o spread negativo persistente em `gordon` com rentabilidade terminal declarada abaixo do custo; com retorno médio separado, a raiz é condicionada a tese declarada de saída pelo capital investido**, e ganha sub-condição própria se o médio também ficar abaixo do custo.

### 6.4 O teto da convenção `book` · **[propriedade condicional]**

**Proposição.** Dados ROIC, W e n, existe um supremo finito para o múltiplo justo **na convenção `book`**, atingido quando g → ROIC (RiR → 100%). Múltiplos de tela acima desse supremo são inatingíveis nessa convenção **para qualquer g, com ROIC e n fixos**.

W = 7%, n = 10, sup sobre g ∈ (0, ROIC):

| ROIC | sup EV/NOPAT fwd | g do máximo | sup EV/EBITDA (d = t = 15%) |
|---|---|---|---|
| 8,5% | 13,52 | → 8,5% | 9,77 |
| 10,0% | 13,19 | → 10,0% | 9,53 |
| 15,0% | 13,71 | → 15,0% | 9,91 |
| 30,0% | 23,36 | → 30,0% | 16,88 |

**Correção numérica da v2 (o erro mais consequente do documento anterior).** A v2 apresentava uma segunda tabela sob o título "o teto cresce com o CAP, mas devagar", cujos valores eram na verdade o múltiplo **a g = 5% fixo** — não o supremo sobre g. A comparação correta:

| n | **teto** (sup sobre g) | valor a g = 5% (o que a v2 tabulou) |
|---|---|---|
| 5 | 9,11 | 9,07 |
| 10 | 9,77 | 9,60 |
| 15 | 10,47 | 10,07 |
| 20 | 11,23 | 10,50 |
| 30 | 12,91 | 11,26 |
| 50 | 17,05 | 12,39 |
| 100 | **34,20** | 13,91 |

*(ROIC 8,5%, W 7%, EV/EBITDA forward, convenção `book`.)*

A v2 concluía, do valor 13,91: *"nem alongar o CAP resolve — com CAP de 100 anos o teto ainda é ~13,9x"*, e usava isso para descartar o alongamento do horizonte como saída para o caso motivador de 27x. **A conclusão é falsa como afirmação matemática**: o teto real em n = 100 é 34,20x, acima dos 27x. O argumento correto é de outra natureza e continua válido: alcançar 27x por alongamento de CAP exige o par (n ≈ 100, g → ROIC) — um século de vantagem competitiva com reinvestimento integral do NOPAT durante todo o período —, que é **economicamente implausível, não matematicamente impossível**. A regra de reporte que decorre disso: quando o alongamento do CAP for cogitado como saída, **reporte o n implícito necessário e discuta sua plausibilidade contra base rates**, em vez de invocar um teto absoluto que não existe.

**Duas qualificações adicionais.** Primeira: o teto é relativo à variável revertida. Se a reversa resolver em ROIC em vez de g, alvos altos encontram raiz — abaixo do WACC, pela perversidade do corolário de §6.3 quando o retorno médio não foi informado à parte (leitura de mercado vazia), e condicionada a tese declarada de saída pelo capital investido quando foi. "Incompatível" é sempre uma afirmação relativa à variável e à convenção, e deve ser reportada assim. Segunda: a `convergencia` não tem teto análogo na faixa relevante (sup 11,86 em n = 10; 41,52 em n = 100) — outra razão pela qual o teto não é propriedade da convergência competitiva, e sim do terminal contábil.

**Regra de inferência.** Um múltiplo incompatível na variável economicamente relevante é evidência sobre a convenção — ou sobre o nível (§6.10) —, não sobre o preço. **Ordem obrigatória de investigação:** (1) falta um degrau de nível na métrica-base? (2) a convenção terminal é a certa? (3) as demais premissas? (4) só então o preço.

### 6.5 CAP e convenção terminal: eixos relacionados, não idênticos · **[propriedade condicional]**

**Proposição.** Quando n → ∞, todas as três convenções convergem para a fórmula de value driver perpétua, e os gaps entre elas se fecham monotonicamente.

ROIC 8,5%, g 5%, W 7%, EV/NOPAT forward:

| n | `book` | `convergencia` | perpétua (1−g/ROIC)/(W−g) |
|---|---|---|---|
| 100 | 19,251 | 19,633 | 20,588 |
| 400 | 20,584 | 20,585 | 20,588 |
| 800 | 20,588 | 20,588 | 20,588 |

Gaps contra `book` (ROIC_TV 20%, gp 3% na `gordon`):

| n | `convergencia` − `book` | `gordon` − `book` |
|---|---|---|
| 10 | +15,7% | +59,1% |
| 20 | +11,9% | +44,7% |
| 40 | +7,2% | +27,1% |
| 80 | +3,0% | +11,2% |

**Qualificação da v3.** A v2 concluía que "CAP e convenção terminal são a mesma pergunta parametrizada de duas formas" e que fazer sensibilidade nos dois simultaneamente é dupla contagem. Com a taxonomia ternária, isso é forte demais. Os dois gaps acima têm naturezas diferentes: `gordon` − `book` mede **se e quando** o spread morre, e é de fato largamente redutível a CAP; `convergencia` − `book` mede **o que sobra quando ele morre**, e não é redutível a horizonte nenhum — em qualquer n finito as duas descrevem terminais distintos. O que sobrevive da proposição da v2: (a) a sensibilidade conjunta em CAP e em *persistência do spread* é parcialmente redundante; (b) o gap entre convenções mede quanto do valor depende da hipótese terminal e encolhe com CAPs longos, dando um critério para saber quando a escolha importa (CAPs curtos) e quando é quase irrelevante (CAPs muito longos).

### 6.6 Cíclicas: a dupla alavanca ao preço do driver — e o efeito Molodovsky · **[identidade + regularidade empírica]**

Este é o ponto onde o framework encontra seu limite estrutural, e onde a análise precisa sair do modelo.

**Premissa contábil.** Em mineração, óleo e gás, a depreciação de PP&E e a exaustão de reservas são reconhecidas pelo método de unidades de produção: custo dividido por reservas recuperáveis, multiplicado pelas unidades extraídas. A D&A é fixa por tonelada/onça/barril — **não** por dólar de receita. Se o preço da commodity sobe com volume constante, a D&A em valor absoluto não se move.

**Proposição (dupla alavanca).** Sob custo de caixa e volume fixos no curto prazo, um aumento do preço do driver exógeno eleva simultaneamente (i) o EBITDA-base e (ii) o próprio múltiplo justo, via queda de d = D&A/EBITDA na ponte EV/EBITDA = EV/NOPAT × (1−d)(1−t).

Premissas do motor fixas (g 5%, ROIC 15%, W 11%, n 10, t 18,5%); EBITDA-base 446,4 ao preço 5,00 com D&A 130,05 e volume 146,2:

| Preço do driver | EBITDA | d | EV/EBITDA justo | EV |
|---|---|---|---|---|
| 4,00 | 300,2 | 43,3% | 4,15 | 1.246,9 |
| 5,00 | 446,4 | 29,1% | 5,19 | 2.317,9 |
| 6,26 (+25%) | 630,6 (+41%) | 20,6% | 5,82 (+12%) | 3.667,5 (+58%) |
| 7,50 (+50%) | 811,9 (+82%) | 16,0% | 6,15 (+19%) | 4.995,6 (+116%) |

Um movimento de +25% no preço da commodity produz **+58% de EV** — sem que nenhuma variável do motor (g, ROIC, WACC, CAP) tenha mudado.

**Conexão com Molodovsky (1953).** A observação clássica é que o P/L é contracíclico: alto no fundo do ciclo (lucros deprimidos caem mais rápido que o preço) e baixo no topo. A resposta padrão da literatura é normalizar o lucro. O resultado acima permite formular a versão pelo lado do múltiplo justo, mais forte que a formulação padrão:

> No topo do ciclo, o múltiplo observado cai (Molodovsky) enquanto o múltiplo justo sobe (dupla alavanca). Os dois se movem em direções opostas, o que faz o desconto aparente contra o "justo" parecer muito maior do que é. No fundo do ciclo o erro se inverte: o múltiplo observado explode e o justo comprime, fazendo a ação parecer cara exatamente quando o EBITDA-base está deprimido.

Comparar múltiplo de tela com múltiplo justo em uma cíclica sem normalizar ambos ao mesmo preço de driver não é aproximação ruim — **é um erro de sinal duplo**.

**Correção da v3 — o gate é por impacto, não por gap.** A v2 prescrevia: "se o preço realizado do período-base divergir do spot em mais de 10%, é obrigatório rodar o cenário normalizado". O critério está errado porque ignora a exposição. A elasticidade operacional relevante é derivável, não arbitrável:

> elasticidade = linha exposta ÷ métrica-base   (com sinal, ver abaixo)
> **impacto = |elasticidade × gap|** — e o gate dispara sobre o impacto, não sobre o gap

Um gap de 12% em um driver com elasticidade 0,1 produz impacto de 1,2% e não justifica cenário nenhum; um gap de 4% em um driver com elasticidade 3,0 produz 12% e justifica. O gate por gap bruto gera falso positivo no primeiro caso e falso negativo no segundo.

**Complemento da v3 — drivers de custo e o sinal da elasticidade.** A v2 tratava apenas drivers de receita. A generalização: a linha exposta é a que se move 1-para-1 com o driver, e o **sinal vem do lado da DRE** — driver de receita (commodity vendida, take-rate, tarifa) entra positivo; driver de custo (frete, energia, insumo, câmbio no COGS) entra **negativo**, e a linha exposta é o custo do insumo, não a receita total. Um gate cego ao sinal soma o que deveria compensar: alta de 20% no preço do produto com alta de 40% no insumo não são 60% de impacto. Quando há drivers em direções opostas, reporte **efeito líquido** (com sinal) e **soma dos brutos** — o líquido decide o gate agregado; os brutos medem o risco de a compensação se desfazer, que é um risco real e não capturado pelo líquido.

**Corolário — a armadilha do ROIC de pico.** O ROIC contábil sobe mais que proporcionalmente ao preço, porque o NOPAT dispara enquanto o capital investido é book histórico praticamente fixo. Plugar esse ROIC no motor faz o reinvestimento necessário para um dado g parecer barato (RiR = g/ROIC) e infla o valor — empilhando o ciclo duas vezes. A defesa é usar ROIC mid-cycle/marginal no motor de g, versão enterprise do "ROE médio do ciclo" de Molodovsky.

**Corolário — nível versus taxa.** Preço de commodity é re-rating de nível, não taxa de crescimento. Ele só se conecta a g por duas vias indiretas: (i) um ROIC sustentadamente mais alto eleva o g sustentável por unidade de reinvestimento, mas apenas se o preço alto for permanente e não cíclico; (ii) mais caixa afrouxa a restrição de funding e pode acelerar o capex de crescimento. Tratar aumento de preço como g orgânico contamina simultaneamente o numerador e a taxa efetiva. Caso particular do teorema da classificação (§6.10).

### 6.7 O problema de identificação na engenharia reversa · **[propriedade condicional]**

**Proposição.** A reversa é um problema inverso mal-posto em **quatro** regiões: (i) alvos acima do supremo da convenção (nenhuma raiz); (ii) vizinhança das linhas de neutralidade (a função é quase plana e a variável implícita é não identificada); (iii) regiões com múltiplas raízes; (iv) **alvos tangentes ao extremo da função** — a raiz existe mas não há mudança de sinal, e qualquer método de bisseção pura a perde silenciosamente.

Com ROIC 8,5%, W 7%, n 10, d = t = 15%, os múltiplos de EBITDA atingíveis variando g são 9,396 (g = 0%), 9,552 (g = 4%) e 9,743 (g = 8%): a função é quase plana. Um alvo de 19,5x retorna conjunto vazio; um alvo de 9,0x só é alcançável com g = −16,3%.

**Operacionalização (v3).** A v2 concluía que "nunca se deve apresentar uma variável implícita sem a curvatura da função em torno dela", sem dar critério. A v3 define o reporte mínimo por raiz: **slope** (∂múltiplo/∂variável), **curvatura**, **elasticidade** e o **intervalo da variável compatível com o alvo ± tolerância** (default 1%). A classificação por largura relativa desse intervalo:

| Largura relativa | Classificação | Conduta |
|---|---|---|
| < 5% | forte | reportar a raiz |
| 5% – 20% | moderada | reportar raiz **e** intervalo |
| > 20% | fraca | a raiz é ruído com aparência de precisão — não apresentar sem o intervalo, e preferir reverter outra variável |

O caso (iv) merece nota própria porque é o mais enganoso: quando o alvo coincide com o extremo da função, existe uma raiz tangencial cuja identificação é **estruturalmente** fraca — qualquer perturbação do alvo a remove ou a desdobra em duas. Reportá-la como ponto é superprecisão por construção.

**O domínio de busca é, ele próprio, uma convenção — e precisa ser declarado.** "Nenhuma raiz" e "alvo incompatível" são afirmações relativas não só à variável e à convenção terminal, mas ao **intervalo em que se procurou**. O framework restringe a busca padrão da reversa à região autofinanciável (RiR ≤ 100%, isto é, g ≤ rentabilidade marginal), e todo resultado da reversa declara a faixa varrida e a restrição vigente. A região além dela existe e é economicamente admissível — é o corolário 1 de §6.10: crescimento acima do autofinanciável, com FCFF/FCFE negativos no explícito, legítimo **sob fonte de funding declarada**. Por isso a abertura dessa região não é um parâmetro de tolerância: é um ato de declaração. O motor a abre somente sob pedido explícito, e qualquer raiz encontrada ali sai carimbada com a exigência de funding — no caso-teste, um alvo de 16x com rentabilidade marginal de 8% só reconcilia com g = 13,8% (RiR de 172%), que é uma afirmação sobre **captação**, não sobre operação, e deve ser lida e defendida como tal. A alternativa — buscar sempre no domínio amplo e deixar ao leitor notar que a raiz implica payout negativo — é exatamente o tipo de premissa silenciosa que o framework existe para impedir.

### 6.8 O que o framework diz sobre comparáveis · **[implicação condicional] · (rótulo corrigido na v3.2)**

Combinando §2.4 com §6.1–6.3: duas empresas que compartilhem, aproximadamente, **seis parâmetros — g, ROIC, W, CAP, d e t — e a convenção terminal** negociam ao mesmo múltiplo justo de EBITDA. A implicação vale **numa direção só**: compartilhar o vetor é condição **suficiente**, não necessária. A recíproca é falsa, e o adendo abaixo mostra por quê — múltiplos iguais podem resultar de vetores econômicos distintos. (A v3 enunciava um "se e somente se" e, no mesmo parágrafo seguinte, o caráter many-to-one do mapeamento; as duas proposições não podem ser verdadeiras ao mesmo tempo. Corrigido na v3.2.) Os dois penúltimos são puramente contábil-fiscais; a última é uma tese estratégica. Disso decorre uma reformulação da proposição de Damodaran: setor é proxy ruim para comparabilidade não porque seja arbitrário, mas porque a dispersão de ROIC dentro de setores é maior que entre setores. E decorre que boa parte do que o mercado chama de "arbitragem de múltiplos" é arbitragem de premissas não declaradas: diferenças de d (intensidade de capital), de t (jurisdição fiscal) ou de convenção terminal implícita.

**Adendo da v3 — o mapeamento é many-to-one.** A função (premissas, convenção) → múltiplo não é injetora: vetores de premissas diferentes, sob convenções diferentes, produzem o mesmo múltiplo. Isso tem duas consequências que a v2 não extraía. Primeira, na direção direta: múltiplos iguais **não** implicam fundamentos iguais, e o "comparável perfeito" pode estar reconciliando o mesmo número por um caminho econômico distinto. Segunda, na direção inversa (§6.7): a reversa devolve **um conjunto de raízes condicional à convenção e às demais premissas**, nunca "a" premissa implícita do mercado. Apresentar "o g implícito" no singular, sem o condicionamento, é erro de tipo lógico, não de cálculo.

### 6.9 Crescimento orgânico gratuito não é representável no parâmetro g · **[propriedade condicional] · (rótulo e enunciado corrigidos na v3.2)**

**Proposição.** Crescimento com RiR = 0 (expansões já capitalizadas, ramp-ups, exploração dentro do portfólio existente) não aparece na identidade g = RiR × ROIC porque a identidade pressupõe que todo crescimento consome capital novo.

**Consequência.** Ele não pode ser "acrescentado" ajustando g — isso corromperia o RiR e, por consequência, o FCFF. Mas *não representável em g* não é o mesmo que *fora do modelo*, e a v3 conflava as duas coisas. A hierarquia correta tem três degraus: (i) **não representável no parâmetro g**, sempre, pela identidade; (ii) **representável em nível**, quando a trajetória e o observável forem declaráveis — é exatamente para isso que existem `normaliza`, `degrau` e `nivel`, que tratam capacidade já construída, ramp-up, repricing, capital ocioso, rebase de métrica e mudança de margem; (iii) **fora do modelo**, como opcionalidade não capturada, apenas quando a trajetória não é explicitável. Declarar fora do modelo um evento que a maquinaria de nível representa é subutilizar o framework, não protegê-lo. O mesmo vale, com sinal contrário, para capex de manutenção subdimensionado: se a D&A não repõe a capacidade econômica, o NOPAT está superestimado e a fórmula inteira herda o erro.

### 6.10 Nível, taxa, rentabilidade e funding: a taxonomia operacional de classificação · **[convenção de modelagem] · (rótulo corrigido na v3.2)**

§6.6 estabeleceu, para price-takers, que preço de commodity é nível e não taxa; §6.9 estabeleceu que crescimento com RiR = 0 não é representável. As duas são instâncias de um mesmo resultado.

**As portas do motor (revistas na v3).** A v2 enunciava "todo evento econômico entra por exatamente uma de três portas" — e a própria taxonomia da seção listava eventos que entram por duas (aquisição: lucro **e** capital) e um que entra por uma quarta não enumerada (mudança de estrutura de capital, que é custo de capital). O enunciado correto é vetorial:

1. **Nível** — altera a métrica-base (EBITDA₀, LL₀) ou o capital, sem alterar taxa nenhuma.
2. **Taxa (g)** — altera o ritmo de comprometimento de capital novo, sujeito a g = RiR × ROIC.
3. **Rentabilidade (ROIC/ROE)** — altera o retorno por unidade de capital, sujeito à mesma identidade.
4. **Funding / custo de capital** — altera a estrutura de capital ou o Ku, e entra pela camada da §4, nunca por g.

**Proposição (classificação).** Eventos **elementares** entram por exatamente uma porta. Eventos **compostos** decompõem-se num vetor (ΔNível, Δg, ΔRentabilidade, ΔFunding), e a proposição vale componente a componente. Seja um evento que eleve permanentemente o lucro por um fator h > 1 **sem consumir capital novo financiado por lucro retido**: sua representação correta é um degrau — em rentabilidade, se o capital contábil permanece constante (ROIC → ROIC × h), ou, equivalentemente, um re-base da métrica-base — e **nunca** um incremento em g. A identidade g = RiR × ROIC é o classificador **negativo**, e essa parte é algébrica: se o evento não vem acompanhado de reinvestimento proporcional, ele não é g — por definição, não por convenção. Mas a atribuição **positiva** de um evento a uma porta é decisão de modelagem, e o próprio exemplo acima a exibe: o mesmo degrau entra por rentabilidade *ou*, equivalentemente, por rebase da métrica-base, conforme qual variável de estado se mantenha constante. Por isso a seção enuncia uma taxonomia operacional, não um teorema: o que é invariante é a identidade; o que é convenção é a porta escolhida — e ela precisa ser declarada, como qualquer outra convenção do framework.

**Corolário 1 — o RiR delator (hipótese, não veredicto).** Se, ao incorporar um suposto "crescimento", o RiR = g/ROIC implícito ultrapassa 100%, o crescimento não é autofinanciável e **exige fonte de funding declarada**. Sem funding plausível, a hipótese forte é erro de classificação: degrau lançado como taxa. Ver a qualificação em §2.2 — o diagnóstico abre a investigação, não a encerra.

**Corolário 2 — o erro tem sinal dependente do regime.** Existem dois erros distintos, e o primeiro muda de sinal conforme o spread:

- **(B) Erro de classificação:** o degrau vai para g e a métrica-base fica intocada.
- **(C) Erro de dupla contagem:** o degrau vai para a métrica-base **e** para g.

Lado equity; Ke = 20%, n = 10, `gordon` com ROE_TV fixo no ROE original, gp = 6,5%, caixa/E = 0. Evento: degrau permanente de h = 1,485 no lucro com capital constante, implementado ao longo de 4 anos — que um analista desavisado traduz como Δg = 1,485^(1/4) − 1 = +10,4 p.p. sobre um g base de 12%. Valores em P/VP justo (= P/L corrente × ROE):

| ROE | regime | base | (A) correto: ROE×h | (B) só no g | erro (B) | (C) nível + g | erro (C) |
|---|---|---|---|---|---|---|---|
| 16% | ROE < Ke | 0,67 | 1,41 | 0,34 | −76% | 1,71 | +22% |
| 20% | ROE = Ke | 1,12 | 2,07 | 1,22 | −41% | 3,03 | +46% |
| 24% | ROE > Ke | 1,57 | 2,73 | 2,11 | −23% | 4,35 | +59% |
| 28% | ROE > Ke | 2,01 | 3,39 | 3,00 | −12% | 5,67 | +67% |

RiR implícito no caminho (B): 139,9% a ROE 16%, 112,0% a 20%, 93,3% a 24% — os dois primeiros com payout negativo, isto é, emissão implícita que ninguém planejou.

Três leituras, uma por regime:

- **ROE < Ke.** O caminho errado **inverte o sinal do evento**: um degrau inequivocamente criador de valor registra como destruição (0,67 → 0,34, contra 1,41 no caminho correto). A causa está em §6.2 — o gradiente em g tem o sinal do spread, e aqui o spread é negativo. É o pior caso possível: o analista rejeita uma tese correta por causa de um erro de classificação.
- **ROE = Ke.** O evento simplesmente **desaparece**. Pela neutralidade exata de §6.1, o P/L forward é invariante a g: 5,0000 antes e 5,0000 depois. Na base corrente aparece um ganho espúrio de +9,3%, que é puro reajuste (1+g) e não valor — a armadilha de §6.2 em estado puro.
- **ROE > Ke.** O múltiplo infla (P/L corrente de 6,52x para 8,80x), mas o valor ainda fica subestimado, porque o degrau nunca entrou na métrica-base. Múltiplo maior sobre lucro menor: o erro se disfarça de precificação de crescimento.

O caminho (C) infla monotonicamente com o spread (+22% a +67%). É o erro mais comum entre analistas cuidadosos, justamente porque fazem a metade certa (normalizar a base) e não percebem que a outra metade é a mesma coisa contada de novo.

> **Síntese: o erro de classificação não tem sinal definido.** Destrói com spread negativo, desaparece na neutralidade e distorce em duas direções simultâneas com spread positivo. Não existe regra de ajuste conservadora — só existe classificar certo.

**A classe dos degraus.**

| Evento | Natureza | Entrada correta no motor |
|---|---|---|
| Preço de commodity, câmbio, frete, energia | degrau exógeno no nível | re-base do EBITDA + queda de d (dupla alavanca, §6.6) |
| Re-precificação regulatória (teto de juros, tarifa, take-rate) | degrau exógeno na margem | re-base do lucro; g inalterado |
| Deployment de capacidade ociosa de balanço (Basileia, caixa excedente, covenant) | degrau endógeno no nível | degrau em ROE/ROIC × h; g inalterado |
| Ganho de escala / diluição de custo fixo | degrau na margem | re-base do EBITDA; excluído pela premissa (1) de §7 |
| Aquisição a valor de livro | **composto**: lucro e capital | vetor: re-base de ambos, ROIC inalterado |
| Mudança de estrutura de capital | degrau no custo de capital | porta 4 — via Ku (§4), nunca via g |
| Crescimento orgânico gratuito (RiR = 0) | taxa sem custo de capital | não representável; declarar fora do modelo (§6.9) |

**O caso da capacidade restrita: mecânica do fator h.** Para um negócio cuja capacidade de gerar lucro é limitada por um índice regulatório ou estrutural — Basileia em bancos, solvência em seguradoras, capacidade licenciada, covenant —, a folga entre o índice corrente e o índice-alvo é um estoque de lucro futuro que não exige capital novo:

> h = índice corrente / índice-alvo
> ROE_deployed = ROE × [1 + (h − 1) × m], com m = ROA marginal ÷ ROA médio
> g permanece inalterado; ROE_TV permanece inalterado

Três qualificações obrigatórias:

1. **ROE_TV não acompanha.** Manter a rentabilidade terminal no valor original é o que impede que o degrau vire moat perpétuo por acidente. ROEs pós-deployment aritmeticamente altos (30–50%) perpetuados são incompatíveis com qualquer equilíbrio competitivo. O quadrante superior da grade de sensibilidade é aritmética, não economia.
2. **O degrau não é instantâneo.** O motor entrega o salto no ano 1; a realidade leva T anos. O fator de captura é 1/(1+Ke)ᵀ — a Ke 20%, 69% em 2 anos, 58% em 3, 48% em 4. Ignorar a transição superestima sistematicamente, e essa é a maior fonte de erro direcional do exercício.
3. **O degrau não é grátis: é uma opção vendida.** Consumir o colchão eleva a probabilidade de evento de capital, e o custo é assimétrico ao múltiplo de tela — emitir acima do valor patrimonial é acretivo, abaixo é destrutivo. Empiricamente, a restrição efetiva costuma não ser a que se está relaxando: em bancos, o funding satura antes do capital, o que força m < 1 por construção e não por pessimismo.

**Consequência para a engenharia reversa.** §6.6 já exigia, para cíclicas, reverter o preço do driver implícito. O teorema generaliza: **reverter o degrau implícito, qualquer que seja sua natureza**. Essa é com frequência a variável implícita mais informativa, por uma razão que as outras não têm — o degrau tem **observável de mercado direto**: o spot, o mínimo regulatório, a margem histórica. Ke implícito e g implícito só podem ser julgados contra a intuição do analista; um "Basileia implícita de 14,0%" ou um "cobre implícito de US$ 3,80/lb" pode ser confrontado com um número que existe no mundo. Quando há dois vetores de valor de naturezas distintas, a reversa produz uma **curva iso-valor** — o conjunto de pares que reconciliam o preço —, convertendo "está barato?" na pergunta mais tratável "qual dos dois vetores eu acredito que o mercado não está pagando?".

### 6.11 A conflação marginal × médio reaparece no valor terminal · **[identidade] · (nova na v3)**

**Proposição.** Na convenção `book`, o valor terminal TV = NOPAT_{n+1}/ROIC usa o ROIC no papel de **retorno médio do estoque de capital** (porque IC_n = NOPAT_{n+1}/ROIC_médio), enquanto o motor de g usa o mesmo símbolo no papel de **retorno marginal** (porque g = RiR × ROIC_marginal). Quando os dois diferem — o caso normal —, usar uma única variável nos dois papéis é erro estrutural, não aproximação.

Magnitude: ROIC marginal 25%, ROIC médio 10%, W 8%, g 4%, n 10 ⟹ EV/NOPAT de **9,718 com a variável conflada contra 13,996 com os papéis separados — erro de −30,6%**.

**Por que isto merece proposição própria.** A v2 afirmava, em §7, que o framework "mitiga" a crítica de Bodmer sobre ROIC ≠ RONIC ao usar soma explícita com terminal separado e ao exigir ROIC marginal derivado. A primeira metade é verdadeira — o horizonte explícito de fato permite rentabilidades diferentes. A segunda metade **produzia o erro que pretendia evitar**: exigir o marginal e depois usá-lo no denominador do terminal é exatamente a conflação de Bodmer, deslocada do explícito para o terminal. O enunciado correto: a crítica é **endereçada no explícito por construção, e no terminal apenas quando o retorno médio é informado separadamente**. As convenções `convergencia` e `gordon` não sofrem do problema — a primeira não referencia rentabilidade alguma no terminal, a segunda referencia uma rentabilidade terminal declarada — declarada **e marginal**: o papel de ROIC_TV é o do retorno incremental terminal (RONIC/ROIIC), nunca o médio do estoque por definição; o blended entra apenas como proxy sob convergência declarada (v3.5, achado C-01 do fechamento das Fases 1–2).

**O caso agravado: a conflação sob um degrau de rentabilidade.** Quando um evento de §6.10 eleva a rentabilidade marginal por um fator h (deployment de capacidade de balanço, por exemplo), a conflação muda de espécie: deixa de errar magnitude e passa a **inverter o sinal do gradiente**. Sob `book` conflada, a rentabilidade pós-degrau (marginal × h) entra no papel de média do estoque, o terminal NOPAT/ROIC **encolhe exatamente na proporção em que o degrau cresce**, e os dois efeitos podem se cancelar ou inverter: no caso medido, a rentabilidade sobe 48% e o múltiplo justo **cai** (7,199 → 7,198) — um evento inequivocamente criador de valor registrando como neutro-negativo. Com o retorno médio do estoque informado separadamente e mantido fixo, a direção corrige (9,12 → 10,06) e a decomposição fecha de forma exata: **o delta inteiro vem do horizonte explícito e o termo de TV fica idêntico** — que é precisamente a regra de §6.10 de que a rentabilidade terminal não acompanha o degrau, agora emergindo da álgebra em vez de ser imposta. A conflação simples custa magnitude (−30,6% acima); a conflação sob degrau custa o **sinal**, e sinal errado não tem ajuste conservador. O motor bloqueia o caminho com alerta explícito quando `book` roda em cenário de degrau sem o retorno médio informado.

### 6.12 A agregação de segmentos não preserva valor: o viés do blended não tem sinal universal · **[propriedade condicional / não linearidade do modelo] · (nova na v3, revista na v3.2)**

**Proposição.** O múltiplo justo é uma função **não linear** dos drivers, e a agregação não comuta com a avaliação: avaliar uma companhia multissegmento com ROIC e g *blended* não é uma aproximação centrada, e sim um estimador viesado, de magnitude calculável e **sinal não determinado a priori**.

**Por que não é um argumento de Jensen.** A v3 rotulava esta proposição como identidade e a sustentava por convexidade. Não se sustenta: a Hessiana de M(g, rentabilidade) é **indefinida** na região relevante — em W 8%, CAP 10, `convergencia`, g 4% e ROIC 15%, os autovalores são −398,55 e +733,40. Sem convexidade conjunta não há desigualdade de Jensen a invocar. Há uma segunda razão, independente: g é normalmente ponderado por NOPAT e o ROIC blended é derivado por capital, de modo que os dois inputs nem sequer são agregados pela mesma medida — não existe uma combinação convexa comum sobre a qual Jensen pudesse operar. O que resta, e basta, é não linearidade com pesos incompatíveis.

**Os dois sinais ocorrem em casos economicamente admissíveis** (ambos em W 8%, n 10, `convergencia`; ROIC blended ponderado por capital, g blended ponderado por NOPAT):

| Caso | Segmentos | Segmentado | Blended | Erro |
|---|---|---:|---:|---:|
| **A — blended subestima** | NOPAT 20, ROIC 40%, g 6% + NOPAT 80, ROIC 8%, g 2% | 1.393,4 | 1.328,1 | **−4,7%** |
| **B — blended superestima** | NOPAT 50, ROIC 35%, g 1% + NOPAT 50, ROIC 9%, g 6% | 1.365,4 | 1.447,7 | **+6,0%** |

O mecanismo do caso B é instrutivo: o segmento de retorno alto cresce devagar e o de retorno baixo cresce rápido, de modo que o blended (ROIC 14,3%, g 3,5%) descreve uma companhia que **não existe** — retorno alto *e* crescimento alto ao mesmo tempo, combinação que nenhum dos dois segmentos tem. O blended não erra por diluir: erra por inventar um par de drivers que nenhuma parte da companhia realiza.

**A direção do viés se calcula, não se deduz.** O padrão frequente é o do caso A — o blended subestima a companhia cujo valor vem de uma joia pequena dentro de um corpo grande de baixo retorno. Mas basta a correlação entre rentabilidade e crescimento inverter-se entre segmentos, como no caso B, para o sinal virar; e com convenções terminais diferentes por segmento há ainda outra fonte de inversão. Por isso a conduta correta não é afirmar a direção: é **calcular EV_segmentado − EV_blended e reportar o número com o sinal** sempre que a dispersão entre segmentos for material.

---

### 6.13 A ponte de releveraging é identidade condicional — o preço do evento, não do risco · **[identidade condicional] · (nova na v3.1)**

**Proposição.** Dado um evento datado de mudança de estrutura de capital entre dois regimes (GD/E, ND/E), o fluxo ao acionista no ano da transição é E_pré·(GD/E₂·razão − GD/E₁)·(1+Kd(1−t)), com razão = (1+ND/E₁)/(1+ND/E₂), e é identidade CONDICIONAL a três hipóteses declaradas: transição num único ano, dívida a valor de face, Kd = cupom. Sob estrutura igual, o termo é identicamente nulo e o modelo colapsa no monofásico (provado por soma explícita de FCFE na suíte). A ponte precifica o movimento de caixa, não o deslocamento de risco: sob Modigliani-Miller, com Ke reprecificado, o efeito líquido da troca é o tax shield — usar a ponte com Ke fixo entre regimes atribui à dívida valor que é de custo de capital (o motor reporta o Ku implícito por regime e alerta o gap).

**Falseamento.** Um caso real com transição datada em que o FCFE explícito ano a ano, construído das demonstrações, divirja do termo fechado além das três hipóteses declaradas, falsearia a identidade condicional.

### 6.14 A curva iso-valor herda o problema inverso — e a conflação da P6.11 · **[corolário de 6.7 e 6.11] · (nova na v3.1)**

**Proposição.** A curva de pares (g, rentabilidade) que reconciliam um alvo é um problema inverso e herda integralmente as quatro patologias da P6.7 (sem raiz, neutralidade, múltiplas raízes, tangência) PONTO A PONTO da grade. Adicionalmente, sob a convenção `book` a inversão fechada só é bem-posta com os papéis marginal×médio separados (P6.11): com rb declarado, rent* = α·g·S/(S + B/rb − alvo); sem rb, a inversão conflacionada pode devolver raízes sem sentido econômico (verificado: ROE implícito negativo em caso com marginal 44,8% e médio 28%). Identificabilidade: com retenção nula (α·g → 0), a rentabilidade marginal não entra no múltiplo e não é recuperável do alvo.

**Falseamento.** Qualquer par devolvido pela curva que, re-avaliado no motor direto com as mesmas convenções, não reproduza o alvo dentro da tolerância, falsearia a implementação (teste automático na suíte).

### 6.15 O regime monetário do g e a consistência de Fisher · **[propriedade condicional] · (nova na v3.2)**

**Proposição.** A identidade g = RiR × ROIC descreve crescimento **financiado** — o que consome capital novo. Crescimento de **preço** não pertence a ela: pela taxonomia da §6.10 ele é nível, e pela §6.9 ele tem RiR ≈ 0. Consequência que a v3 não extraía: **numa análise price-taker com a métrica normalizada ao nível (§6.6, §6.10), os fluxos do modelo ficam expressos em preços de hoje — são fluxos reais na moeda do driver — enquanto o custo de capital construído por CAPM sobre o juro nominal é nominal.** Descontar fluxo real a taxa nominal é o erro clássico de ilusão monetária de Modigliani & Cohn (1979): o pedágio da inflação é cobrado na taxa e nunca entregue no fluxo, e o valor sai sistematicamente subestimado — sem produzir sintoma numérico algum, porque nenhuma identidade interna é violada.

**A forma específica no framework.** Sob `convergencia` o valor terminal é NOPAT/W e não cresce; sob `gordon` com gp = 0, idem. Com a base normalizada ao spot nominal, essas convenções afirmam, sem declarar, que o preço do driver fica **congelado em termos nominais em perpetuidade** — isto é, caindo à taxa de inflação em termos reais, para sempre. Não é um default neutro: é um canto extremo do espaço de hipóteses sobre o preço real do driver. (Caso motivador: na terceira execução fria sobre uma royalty de ouro, tornar explícito o regime — driver acompanhando a inflação de 2,3% a.a. — moveu o caso-base em +28%; o custo de capital implícito no preço de mercado, 4,66%, estava colado no juro nominal de 4,62%, e refeita a conta em numerário-ouro a taxa implícita caiu a ~1,3 p.p. acima do juro real — o mercado fazia a conta consistente.)

**Resolução — duas rotas equivalentes por Fisher.** Com (1 + Ke_real) = (1 + Ke_nominal)/(1 + π): **(A)** manter os fluxos em preços de hoje e descontar a Ke real — corrige o horizonte inteiro; **(B)** manter o Ke nominal e conceder ao terminal o crescimento de preço **gratuito** (a mecânica da §6.9 no limite RiR → 0: rentabilidade terminal → ∞ com gp = π) — corrige o terminal, que é onde mora a maior parte do efeito. A escolha entre rotas é indiferente; a escolha entre **âncoras** — driver congelado nominal × driver acompanhando a inflação — é hipótese substantiva sobre o preço real do driver, e vai declarada e entregue em dupla.

**Três limites.** (i) A proposição vale para o caminho price-taker normalizado. Companhia com poder de preço analisada sem normalização carrega os reajustes DENTRO do g, e a conta nominal-com-nominal está correta — aplicar a correção ali conta a inflação em dobro. (ii) "O driver acompanha a inflação" é regularidade fraca, não lei: o preço real de commodities flutua por décadas; as duas âncoras delimitam o intervalo, nenhuma é a verdade. (iii) Crescimento por inflação não é integralmente gratuito no mundo real — repor capacidade e girar capital custam preços correntes; a âncora "acompanha sem custo" é limite superior. A crítica técnica à value driver formula sob inflação (Bodmer; Kiechle & Lampenius, *The Engineering Economist*, 2013) aponta o mesmo defeito pelo outro lado: aplicada em regime nominal ingênuo, a fórmula cobra reinvestimento g/ROIC sobre um crescimento de preço que não consome capital proporcional.

**Falseamento.** A proposição é falseável pela equivalência: para qualquer vetor, o valor por (A) — fluxos de hoje a Ke real de Fisher — deve coincidir com o valor por (B) — Ke nominal com o crescimento de preço gratuito composto no fluxo — dentro da aproximação declarada (B terminal-only). Divergência além disso falsearia a implementação, não a proposição.

## 7. Limites de validade

O framework é honesto sobre onde quebra. As premissas, e o que cada uma exclui:

**Premissas do modelo econômico.** (1) Crescimento apenas por novos investimentos — o que exclui, por construção, ganhos de escala, expansão de margem e toda a classe de degraus de §6.10; (2) retornos marginais constantes ao longo do CAP; (3) D/E constante — violada por definição durante qualquer deployment de capacidade de balanço, o que é exatamente por que o degrau precisa entrar como salto de rentabilidade e não como trajetória; (4) proporção de caixa constante — e, no `gordon`, também no terminal (§2.2); (5) Kd constante.

**Premissas da forma de múltiplos.** Margens, RiR e payout constantes. A combinação de RiR fixo com g muito alto pode gerar caixa negativo — teste de estresse da consistência do par (g, RiR) e, por §6.10, classificador de eventos mal alocados.

**Convenções que não são neutras (v3).** Seis escolhas movem o resultado sem aparecer como premissa econômica, e todas precisam ser declaradas: convenção terminal (§3.3, até ~2x); convenção temporal, fim de ano vs meio de ano (fator (1+W)^0,5 — +3,4% a 7% de custo, +4,4% a 9%); base do múltiplo, corrente/TTM vs forward/NTM (fator (1+g) — a 12% de crescimento, 12% de erro no alvo de uma reversa); política de caixa no terminal (2% a 6% do P/L); o papel da rentabilidade no terminal da `book` (§6.11, até ~30%); e o fluxo do ano de transição no `gordon` (§5 — efeito TV_share × [(1+gp)/(1+g) − 1], tipicamente −0,4% a −3,5%). A v2 não documentava nenhuma das cinco últimas. Uma divergência de 4–5% entre dois modelos "iguais" é, com frequência, convenção temporal ou de transição — não premissa.

**Custo de capital exógeno na camada do múltiplo.** Ver §4: o Ke é input fixo na fórmula de múltiplos e não responde à estrutura de capital nem à sua deriva. Cenários com alavancagem diferente sob o mesmo Ke atribuem à política de caixa efeito que pertence à taxa de desconto (ordem de grandeza: 16%).

**Mortalidade não modelada.** Ver §3.2: nenhuma convenção embute hazard de extinção; o viés é conhecido e unidirecional (valor terminal superestimado com gp > 0), da ordem de −16% a −27% para hazards de 2% a 5% a.a. Declarar quando o terminal dominar.

**Qualidade do capital investido.** O ROIC contábil pressupõe que o denominador captura o capital econômico. Em negócios com ativo intangível construído via DRE (R&D, parte de S&M), o capital fica fora do balanço: o ROIC contábil é inflado e, por RiR = g/ROIC, o reinvestimento necessário parece barato — o valor é superestimado por dois canais simultâneos. Sintoma diagnóstico: **ROIC alto com book pequeno e R&D/S&M altos**. A defesa é derivar o marginal pelo deployment total, incluindo o componente despesado, ou declarar que o ROIC é contábil-estreito e a direção do viés.

**Críticas externas relevantes.** Bodmer identifica dois defeitos estruturais da fórmula fechada de value driver: ela não trata corretamente aumentos nominais de lucro por inflação, e desmorona quando o retorno dos ativos existentes difere do retorno dos ativos novos (ROIC ≠ RONIC). O framework endereça o segundo no explícito por construção e no terminal apenas sob a separação de §6.11; **não** elimina o primeiro — em ambiente de inflação alta, g nominal e ROIC nominal precisam de tratamento explícito, sob pena de dupla contagem. Inflação é, ela própria, um degrau recorrente de nível travestido de taxa: a versão contínua do problema de §6.10.

**O maior limite: o framework não contém o nível.** Margem entra congelada, EBITDA-base entra congelado, capacidade instalada entra congelada. Para price-takers e para negócios com restrição de balanço, a variável que domina o valor em ordens de magnitude simplesmente não é uma variável do modelo — é um parâmetro da métrica-base. Nenhuma sensibilidade em g, ROIC, WACC ou CAP revela isso. Por isso a normalização ao dado corrente (§6.6, §6.10) não é refinamento opcional: é condição de validade.

**Onde a leitura não se aplica.** Instituições financeiras (capital investido e EV/EBITDA não têm leitura econômica; usar ROE/P-L), empresas em estágio de introdução (a literatura de *life cycle* sugere opções reais em vez de DCF puro) e negócios com D&A estruturalmente descolada do capex econômico (IFRS-16, SBC, intangíveis internamente gerados). **Fronteira de escopo (v3.4)** — casos em que outra arquitetura de valuation tende a prevalecer sobre a perpetuidade agregada do framework, e a escolha deve ser declarada: ativos de **vida econômica finita** (mineração, óleo e gás, concessões com termo — DCF de reservas/curva de produção; a perpetuidade superestima, ver §2.1); **REITs e imobiliárias** (NAV, cap rates, FFO/AFFO; a D&A contábil não informa); **holdings** (soma das partes com dívida, impostos e custos da holding); **pré-lucro** (opções reais). O framework segue útil nesses casos como *linguagem de premissas* — mas como métrica-manchete, não.

---

## 8. Protocolo de aplicação e estado das extensões

**Sequência operacional.** (1) Gate anti-defasagem, por **impacto** = |elasticidade × gap|, com elasticidade derivada e com sinal (§6.6); (2) classificação dos eventos no vetor nível/taxa/rentabilidade/funding (§6.10); (3) derivação de premissas com rentabilidade **marginal**, e do retorno **médio** em separado quando a convenção for `book` (§6.11); (4) escolha **declarada** da convenção terminal pelo critério de duração econômica do claim (§3.3), com as demais convenções da §7 declaradas junto; (5) cenários; (6) tabela g × rentabilidade na base declarada (§6.2); (7) engenharia reversa com métricas de identificação por raiz (§6.7), inclusive do degrau implícito (§6.10); (8) **revalidação da convenção** contra a rentabilidade marginal derivada — se ela ficou abaixo do custo de capital, a análise volta ao passo 4 quando não há retorno médio separado, e segue com tese de saída pelo capital investido declarada quando há (§3.4, trava condicional); (9) trilha de auditoria com vintage dos dados.

O passo 8 não existia na v2 e é o que fecha a circularidade do protocolo: a convenção precisa ser escolhida antes dos números (para não ser escolhida pela conveniência do resultado) e verificada depois deles (porque a trava de §6.3 só é testável com a rentabilidade marginal em mãos).

**Estado das três extensões propostas na v2:**

1. **Fade intermediário — rejeitado por decisão de projeto.** As razões estão em §3.4: o parâmetro não é observável na firma, suaviza exatamente a decisão que o framework existe para forçar, e não adiciona informação sobre o intervalo entre convenções que já é reportado. A v2 recomendava esta extensão como prioritária; a v3 a descarta explicitamente e substitui o eixo de fade pela taxonomia ternária de §3.3.
2. **CAP implícito como saída padrão — implementado.** Com as qualificações de §3.1: interpolado entre anos inteiros, condicional às demais premissas e à convenção, com aviso quando a série valor(n) não for monótona.
3. **Reversa em degrau com curva iso-valor — implementado.** É a extensão de maior retorno prático, pela razão de §6.10: produz a única variável implícita com observável de mercado direto para confronto.

**Extensão remanescente (nova na v3).** Realimentação automática da trilha Ke_t da recursão APV para a fórmula de múltiplos, cenário a cenário — hoje manual, e é o que fecharia a lacuna de camadas descrita em §4. É a única extensão que a v3 propõe, e é de engenharia, não de teoria.

---

## 9. Conclusão

O framework de múltiplos justos não é técnica de atalho: é a recusa em aceitar o múltiplo como primitivo. Sua tese é que a agregação que torna o múltiplo conveniente é exatamente a que destrói sua informação, e que desagregar — em crescimento, retorno marginal, custo de capital, duração da vantagem e contabilidade — devolve capacidade de julgamento. Não objetividade: **julgamento localizado e auditável**.

Seis conclusões que valem mais que a álgebra que as produz:

1. **O múltiplo justo não é monotônico em ROIC, e o sinal é propriedade da convenção terminal.** Sob valor terminal contábil, o múltiplo cai com o ROIC; sob convergência competitiva padrão ou spread persistente, sobe. A afirmação da v2 de que múltiplo alto por ROIC alto pressupõe moat perpétuo era falsa: pressupõe apenas rejeitar o valor contábil como valor de saída — tese bem menos exigente.
2. **Um múltiplo de tela incompatível é evidência sobre a convenção ou sobre o nível, não sobre o preço** — e a ordem de investigação é degrau ausente → convenção → demais premissas → preço. Alongar o CAP **pode** matematicamente alcançar múltiplos altos (o teto sobe com n, ao contrário do que a v2 afirmava); o que o descarta é a implausibilidade do par (n, g) implícito, que deve ser reportado e discutido, não a impossibilidade.
3. **CAP e convenção terminal são eixos relacionados, não idênticos.** A persistência do spread é largamente redutível a horizonte; o que sobra quando o spread morre não é.
4. **Em muitos negócios a variável dominante é um nível, e o motor só tem taxas.** Preço do driver em price-takers e capacidade ociosa em negócios com restrição de balanço são o mesmo fenômeno: eventos que multiplicam o lucro sem consumir capital novo. Lançá-los em g é o erro mais caro do framework, e ele não tem sinal definido — destrói com spread negativo, desaparece na neutralidade e, com spread positivo, distorce em duas direções ao mesmo tempo. Não há ajuste conservador; há classificação certa ou errada.
5. **A patologia perigosa é a que não deixa rastro.** As outras se manifestam como número estranho ou raiz ausente, e o analista percebe. O erro de classificação, na vizinhança da neutralidade, se manifesta como *nenhum efeito*; na cíclica, como um número perfeitamente plausível respondendo à pergunta errada. É a única classe de erro que exige passo de protocolo próprio, e não apenas atenção.
6. **Consistência interna não valida rótulo econômico** — e esta é a conclusão metodológica que a revisão v2 → v3 produziu. Todas as tabelas da v2 reproduziam exatamente no motor; a reconciliação DCF↔renda residual fechava a 1e-15; e ainda assim uma convenção estava rotulada com uma afirmação econômica que ela não faz, e uma tabela sustentava uma conclusão falsa. **Um modelo pode estar aritmeticamente perfeito e economicamente mal descrito**, e nenhuma quantidade de verificação numérica dentro do próprio motor detecta isso. O que detecta é auditoria adversarial da correspondência entre a fórmula e a frase em português que a acompanha.

---

## Apêndice A — Protocolo de validação

A v2 afirmava que as proposições foram "verificadas numericamente no motor". Isso é insuficiente e a própria revisão demonstrou por quê. O protocolo em uso, em quatro camadas:

1. **Anchors contra modelo de referência independente.** O motor reproduz uma planilha construída separadamente (DRE, balanço e fluxo simulados período a período, com reconciliação por três rotas de FCFE e checks de fechamento). Confronto em **trajetória**, não só em totais: FCFF e FCFE ano a ano (erro máx. 4,3e-14), EV por três rotas (modelo, fórmula, capital + renda residual: 2e-13), e as seis séries do bloco APV ao longo de 11 períodos (4,6e-7, limitado pela truncagem dos inputs).
2. **Property tests.** Identidades que devem valer em **qualquer** combinação válida de parâmetros, testadas por amostragem massiva: neutralidade ROIC = W (360 combinações); equivalência `convergencia` ≡ `gordon` com ROIC_TV = W, invariante a gp (144); monotonicidade por convenção; sinal do gradiente em g; inércia das convenções fora de seu escopo.
3. **Reconciliação por construção independente.** O valor calculado pela fórmula é confrontado com a soma de fluxos construídos explicitamente fora do motor — incluindo a simulação ano a ano do balanço terminal por 4.000 períodos para validar o fator fechado de FCFE terminal (pior erro relativo 7,6e-15) e a identidade contábil de três rotas no terminal.
4. **Boundary tests.** Limites e regiões degeneradas: g → ROIC, gp → W (deve retornar indefinido, não explodir em silêncio), ROIC → 0, n → ∞ (deve convergir à value driver perpétua), spread negativo declarado, caixa extremo, raízes tangenciais sintéticas, múltiplas raízes.

**O que este protocolo não cobre, e nenhum protocolo numérico cobre:** a correspondência entre a fórmula e a afirmação econômica que a acompanha. Esse é o objeto da auditoria conceitual, e foi ela — não os testes — que encontrou os erros corrigidos nesta versão.

---

## Apêndice B — Condições de falseamento

Enunciados que tornariam falsas as proposições centrais, para que o leitor possa testá-las em vez de acreditar nelas:

- **§6.1 (neutralidade)** seria falseada por um par (ROIC = W, g) — com ROIC marginal = ROIC book sob `book` (Adendo 3) — em que o múltiplo forward divergisse de 1/W. Como é identidade algébrica sob as premissas de §7, um contraexemplo indicaria violação de premissa — tipicamente margens ou RiR não constantes —, não erro da proposição.
- **§6.3 (monotonicidade)** seria falseada por uma convenção terminal, econômica e declarável, sob a qual o sinal de ∂múltiplo/∂ROIC não fosse determinado pela convenção. A proposição é condicional por construção: o que ela proíbe é a afirmação **incondicional** de qualquer dos sinais.
- **§6.4 (teto)** é falseada por qualquer alvo alcançável na `book` acima do supremo sobre g com ROIC e n fixos — o que não existe. A afirmação **derivada** ("alongar o CAP não resolve") foi de fato falseada nesta revisão, e é o exemplo que o leitor deve ter em mente ao ler as demais.
- **§6.10 (classificação)** seria falseada por um evento que eleve permanentemente o lucro sem reinvestimento proporcional e cuja representação correta no motor **seja** um incremento em g. Como a identidade g = RiR × ROIC é definicional, tal evento indicaria que o crescimento observado tem outra fonte de capital — o que é a porta 4, não a porta 2.
- **§3.2 (mortalidade)** e as regularidades empíricas em geral são falseáveis por dados: amostras, períodos ou geografias diferentes podem produzir persistências e hazards diferentes, e nesse caso mudam as âncoras, não a estrutura.

**Predições comprometedoras.** O framework prediz que (i) a dispersão de múltiplos justos dentro de um setor deve exceder a dispersão entre setores, acompanhando a dispersão de ROIC; (ii) discrepâncias persistentes entre múltiplo justo e múltiplo de tela devem se concentrar em companhias cujo valor depende de nível não normalizado (cíclicas no extremo do ciclo, negócios com capacidade ociosa de balanço), e não uniformemente; (iii) CAPs implícitos exigidos pelo mercado devem se concentrar na faixa de 5 a 20 anos para companhias em crescimento e maturidade. Qualquer das três pode ser testada e nenhuma é trivialmente verdadeira.

---

## Apêndice C — Caso trabalhado: um claim de longa duração a 27x

A v2 invocava três vezes um caso de royalties/streaming a 27x de tela sem apresentá-lo. Aqui ele está, de ponta a ponta, com os números do motor.

**Premissas.** Rentabilidade marginal do capital novo (novos streams contratados) 8,5%; W 7%; d 15%; t 15%; g 5%; CAP preliminar 10 anos. Tela: **27x EV/EBITDA forward**.

**Passo 1 — gate de nível (§6.6).** Antes de qualquer convenção: o EBITDA-base do período está defasado em relação ao spot dos metais subjacentes? Suponha gap de +8% com elasticidade operacional derivada de 0,9 ⟹ impacto 7,2%, abaixo do limiar de 10%: o gate **não** dispara e o período-base é representativo por materialidade. Registre assim mesmo — o gate que não dispara é informação.

**Passo 2 — as três convenções.**

| Convenção | n = 10 | n = 20 | supremo sobre g (n = 10) |
|---|---|---|---|
| `book` | 9,60 | 10,50 | 9,77 |
| `convergencia` | 11,10 | 11,75 | 11,86 |
| `gordon` (ROIC_TV 20%, gp 3%) | 15,27 | — | — |
| `gordon` (ROIC_TV 20%, gp 4%) | 18,51 | — | — |

Nenhuma alcança 27x. Este é o resultado interessante, e é o oposto do que a v2 sugeria: o diagnóstico **não** é "a convenção está errada, troque para spread e pronto".

**Passo 3 — o que 27x exige, por variável.**

- **Em gp**, sob `gordon` com ROIC_TV 20%: raiz em **gp = 5,19%** — ou seja, 74% do custo de capital como crescimento perpétuo. Matematicamente admissível, economicamente uma afirmação enorme: crescimento nominal perpétuo pouco abaixo do custo de capital, para sempre.
- **Em CAP**: incompatível. A série é decrescente em n nesta parametrização, e o alvo está acima do máximo — nenhum horizonte reconcilia.
- **Em nível**: um degrau de **2,43x** no EBITDA-base reconciliaria 27x sob `convergencia` sem mexer em nenhuma taxa.

**Passo 4 — leitura.** As três leituras são mutuamente exclusivas e todas testáveis contra o mundo, o que é exatamente o ponto de §6.10: o mercado está pagando (a) crescimento perpétuo de 5,2% para sempre, (b) uma métrica-base 2,4x maior que a reportada — expansão de portfólio já contratada mas ainda não em produção, tipicamente —, ou (c) alguma combinação das duas. A pergunta "está caro?" foi substituída por "eu acredito no pipeline contratado ou no crescimento perpétuo?", que é uma pergunta com resposta pesquisável: o pipeline tem observável direto (contratos assinados, cronograma de rampa), o gp não tem.

**Passo 5 — o que reportar.** A convenção escolhida e a hipótese que ela carrega; o gap entre as três (o valor que depende da hipótese terminal); a identificação da raiz em gp (moderada ou fraca — nesta região a função é sensível, mas o intervalo deve acompanhar); o degrau implícito com seu observável; e a declaração das quatro convenções de §7 usadas. Sem isso, "múltiplo justo de 15,3x contra 27x de tela" é um número que parece informação e é opinião comprimida.

---

## Referências

**Fontes primárias e canônicas**

- Miller, M. H. & Modigliani, F. (1961). "Dividend Policy, Growth, and the Valuation of Shares". *The Journal of Business*, 34(4), 411–433.
- Modigliani, F. & Miller, M. H. (1958, 1963). Proposições sobre estrutura de capital e o efeito fiscal da dívida.
- Modigliani, F. & Cohn, R. (1979). "Inflation, Rational Valuation and the Market". *Financial Analysts Journal* — o erro de descontar fluxos reais a taxas nominais (ilusão monetária); base da §6.15.
- Damodaran, A. Princípio de consistência nominal×real (fluxos e taxas na mesma base); a violação subestima o valor de forma material. NYU Stern, notas de DCF.
- Kiechle, D. & Lampenius, N. (2013). "Technical Note: Value Driver Formulas for Continuing Value". *The Engineering Economist*, 58(1) — a value driver formula não contabiliza crescimento nominal por inflação; ver também E. Bodmer sobre as distorções de inflação da fórmula.
- Molodovsky, N. (1953). "A Theory of Price Earnings Ratios". *Financial Analysts Journal*.
- Gordon, M. Modelo de crescimento perpétuo.
- Williams, J. B. (1938). *The Theory of Investment Value*.
- Graham, B. & Dodd, D. (1934). *Security Analysis* (4ª ed., 1962, com Cottle) — lucros normalizados.
- Higgins, R. C. (1977). "How Much Growth Can a Firm Afford?". *Financial Management*, 6(3), 7–16.
- Myers, S. (1974). Adjusted Present Value (APV).
- Miles, J. & Ezzell, J. (1980). Alavancagem-alvo D/V com rebalanceamento periódico; o PRIMEIRO escudo desconta a Kd e os posteriores a Ku.
- Harris, R. & Pringle, J. (1985). Escudos fiscais descontados a Ku em todos os períodos, sob rebalanceamento contínuo para a razão-alvo.
- Fernández, P. *The Correct Value of Tax Shields: An Analysis of 23 Theories*. IESE. Referência para a distinção entre as políticas de dívida e as taxas de desconto dos escudos.
- Edwards, E. & Bell, P. (1961); Peasnell, K. (1982); Ohlson, J. (1995); Feltham, G. & Ohlson, J. (1995). Renda residual e clean surplus. Lücke (1955) para o teorema Preinreich–Lücke.
- Rappaport, A. *Creating Shareholder Value* — "value growth duration".
- Mauboussin, M. & Johnson, P. (1997). "Competitive Advantage Period 'CAP': The Neglected Value Driver".
- Koller, T., Goedhart, M. & Wessels, D. *Valuation*, 7ª ed. (2020), Wiley/McKinsey — key value driver formula e apêndice de lucro econômico.
- Mauboussin, M. & Rappaport, A. (2021). *Expectations Investing*, ed. revisada.

**Fontes consultadas na pesquisa**

- Mauboussin, M. & Callahan, D. (14/04/2026). "Competitive Advantage Period: The Neglected Value Driver". Counterpoint Global Insights, Morgan Stanley — fade rates por setor, persistência de ROIC, longevidade corporativa, modelos terminais, MICAP.
- Damodaran, A. "Relative Valuation" e cap. 4 de *Damodaran on Valuation* — determinantes dos múltiplos, companion variables, comparáveis.
- Fernández, P. IESE — "Levered and Unlevered Beta", "The Correct Value of Tax Shields: An Analysis of 23 Theories", "Equivalence of ten different DCF valuation methods".
- Bodmer, E. "Biases in McKinsey Value Driver Formula"; "Use of Proofs in Corporate Valuation Analysis".
- Penman, S. "Valuation Models: An Issue of Accounting Theory" — equivalência DCF↔RI apenas em horizonte infinito.
- Efeito Molodovsky e normalização de lucros (material CFA e resenhas).
- Método de unidades de produção / exaustão de recursos naturais.

**Verificações numéricas.** Todas as tabelas foram geradas com o motor do framework (soma explícita), auto-validado contra os anchors do modelo de referência (EV/NOPAT 6,4296x · EV/EBITDA 4,2007x · P/L 5,7337x · ponte de normalização 630,6294 · bloco APV: V₀ 193,6592, E₀ 158,6592, Ke₁ 20,5633%, WACC₁ 18,6524%) e pela suíte descrita no Apêndice A. Parâmetros de replicação da tabela de §6.10: Ke 20%, n 10, `gordon` com ROE_TV fixo no ROE original de cada linha, gp 6,5%, caixa/E 0; h 1,485; Δg = h^(1/4) − 1 = 10,4 p.p. sobre g base de 12%; valores em P/VP justo = P/L corrente × ROE.

---

## Nota de revisão — v2 → v3

| Seção | Alteração |
|---|---|
| Resumo | "dez proposições" → "doze"; três avisos de leitura (status das afirmações, convenção ternária, reprodução ≠ verificação) |
| §1 | Acrescentado: derivar o múltiplo desloca e torna auditável o julgamento — não o elimina |
| §2.2 | Corolário do RiR rebaixado de veredicto a hipótese diagnóstica condicionada a funding; termo de caixa identificado como **módulo de política**; **fator de FCFE terminal acrescentado** (estava ausente e a omissão subestimava o P/L em 2–6%) |
| §2.3 / §2.5 | Registrado que separar explícito e terminal é necessário mas não suficiente contra a crítica de Bodmer (→ §6.11); e que a reconciliação com renda residual prova consistência algébrica, não correspondência do rótulo econômico |
| §2.4 | Decomposição obrigatória do d (depletion, IFRS-16, PPA) |
| §3.2 | **Mortalidade**: quantificada (−16% a −27% para hazard de 2% a 5%) e resolvida por declaração explícita de viés, em vez de citada e ignorada |
| §3.3 | **Reescrita**: duas convenções → **três** (`book`, `convergencia`, `gordon`); critério de escolha muda de classe de setor para **duração econômica do claim**; magnitude do erro de rótulo (9,86x vs 20,55x) |
| §3.4 | **Nova**: por que o framework não implementa fade — retirada a afirmação da v2 de que as convenções eram os extremos do eixo de fade, e retirada a recomendação de implementá-lo |
| §4 | **Inconsistência interna corrigida**: a garantia de Ke endógeno vale na camada APV e **não** na camada do múltiplo; tabela de camadas e ordem de grandeza do erro (16%) |
| §5 | Três convenções de TV; fator terminal do FCFE; **tabela das cinco convenções não neutras** com o efeito de cada troca |
| §6.3 | Conclusão da v2 ("múltiplo alto por ROIC alto pressupõe moat perpétuo") **retificada como falsa**; tabela ganha a coluna `convergencia` |
| §6.4 | **Erro numérico corrigido**: a tabela "teto por CAP" da v2 tabulava o múltiplo a g = 5%, não o supremo; teto real em n = 100 é 34,20x e não 13,91x; "alongar o CAP não resolve" reescrito como implausibilidade do par (n, g), não impossibilidade |
| §6.5 | Qualificada: CAP e convenção são eixos **relacionados**, não idênticos; a redutibilidade vale para persistência do spread, não para o valor do estoque |
| §6.6 | Gate migrado de **gap bruto** para **impacto** = \|elasticidade × gap\|; elasticidade generalizada para drivers de **custo**, com sinal; reporte de líquido e brutos |
| §6.7 | Quarta região mal-posta (raízes tangenciais); critério operacional de identificação (slope, curvatura, elasticidade, intervalo, classificação forte/moderada/fraca) |
| §6.8 | Acrescentado o caráter **many-to-one** do mapeamento premissas → múltiplo, nas duas direções |
| §6.10 | "Exatamente uma de três portas" → **vetor de quatro** (ΔNível, Δg, ΔRentabilidade, ΔFunding), resolvendo a contradição com a própria taxonomia da v2 (aquisição, estrutura de capital) |
| §6.11 | **Nova**: a conflação marginal × médio reaparece no terminal da `book`; a alegação da v2 sobre Bodmer em §7 era falsa; magnitude −30,6% |
| §6.12 | **Nova**: a agregação de segmentos não preserva valor; o blended é estimador viesado, com sinal e magnitude a calcular (a v3 atribuía o efeito a convexidade — corrigido na v3.2: a Hessiana é indefinida) |
| §6.15 | **Nova (v3.2)**: o regime monetário do g e a consistência de Fisher — em price-taker normalizado a nível, o g é volume e os fluxos são reais na moeda do driver; descontá-los a Ke nominal é Modigliani-Cohn; duas rotas equivalentes (Ke real; preço gratuito no terminal) e dupla entrega das duas âncoras |
| §7 | Acrescentados: convenções não neutras, Ke exógeno na camada do múltiplo, mortalidade, qualidade do capital investido (intangível fora do balanço) |
| §8 | Protocolo alinhado ao fluxo real, com **passo 8 de revalidação da convenção**; estado das três extensões da v2 (1 rejeitada, 2 implementadas); nova extensão de realimentação de Ke_t |
| §9 | Conclusões 1–4 revistas conforme acima; **conclusão 6 nova**: consistência interna não valida rótulo econômico |
| Apêndices | **Novos**: A (protocolo de validação em quatro camadas), B (condições de falseamento e predições comprometedoras), C (caso trabalhado de ponta a ponta, ausente da v2) |

**Adenda — sincronização com o motor v8.4–v8.5** (auditoria externa em três rodadas, pós-v3):

| Seção | Alteração |
|---|---|
| §5 / §7 | **Sexta convenção não neutra**: fluxo do ano de transição no `gordon` — (1+g), fiel à planilha, vs (1+gp) de parte do sell-side; efeito exato TV_share × [(1+gp)/(1+g) − 1], calculado caso a caso pelo motor em vez de reportado como faixa |
| §6.7 | O **domínio de busca da reversa** declarado como convenção: busca padrão restrita a RiR ≤ 100%; a região além é admissível sob funding declarado (§6.10, corolário 1) e sua abertura é um ato de declaração, com a raiz carimbada |
| §6.11 | **Caso agravado da conflação**: sob degrau de rentabilidade, a `book` conflada inverte o sinal do gradiente (rentabilidade +48% ⟹ múltiplo cai); com o médio separado, o delta migra inteiro para o explícito e o TV fica idêntico — a regra de §6.10 emergindo da álgebra |


## Nota v3.2 — posição do framework ante os dois apertos de Damodaran (custo de capital e âncora macro)

O framework adota como GUARDA a âncora macro do crescimento perpétuo (gp ≤ rf nominal da moeda;
~PIB real em regime real) e a declaração obrigatória de moeda/regime — implementadas no motor
como diagnósticos opcionais com aviso na ausência (v9.4). Sobre a ORIGEM do custo de capital
(build-up rf + ERP + beta + prêmio-país), a posição é deliberada e registrada: fora do escopo
pocket. O framework toma Ke/WACC como inputs declarados e garante a CONSISTÊNCIA entre camadas
(apv, Ku, WACC_t), não a origem do número — quem precisa do build-up o faz fora e declara o
resultado. É uma fronteira de escopo, não uma discordância: a crítica de que o input dominante
é o menos examinado é aceita, e a resposta do framework é torná-lo o MAIS declarado.
