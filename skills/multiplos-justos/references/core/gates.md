# Gates metodológicos

> Conteúdo migrado da v10.1 sem simplificação econômica.

## Cinco gates antes de qualquer conta

### Gate 0 — Capital econômico e qualidade dos inputs contábeis

Oito verificações ANTES de aceitar qualquer input contábil — todas declaratórias (registram e
avisam, nunca bloqueiam nem convertem), com detalhe operacional em `aplicacao.md` §1:
- **Capital econômico.** Pergunta obrigatória, resposta registrada: *P&D, aquisição de clientes,
  software, marca são despesa ou investimento econômico neste negócio?* Expensar investimento
  reduz o NOPAT, omite capital, infla o ROIC médio e oculta reinvestimento — quatro erros na
  mesma direção; derive o marginal pelo deployment TOTAL quando a resposta for "investimento".
- **Teorema da base coerente.** Base de lucro e RiR devem vir do MESMO regime contábil —
  misturá-los cobra o mesmo investimento duas vezes ou nenhuma:

  | Regime | Base | RiR que entra no motor |
  |---|---|---|
  | **A — investimento é despesa** (GAAP puro) | LL/NOPAT reportado (deprimido pelo investimento despesado) | SÓ o capital de balanço financiado por equity: capex de crescimento + ΔWC + M&A − funding próprio do braço financeiro. NUNCA a retenção integral. |
  | **B — investimento é capital** (Damodaran, capitalização de intangíveis) | LL/NOPAT normalizado: soma-se de volta o investimento despesado e subtrai-se a amortização do ativo criado, com vida útil DECLARADA (hipótese, com direção do erro) | Retenção + investimento via DRE, sobre a base normalizada |

  **Quadrante proibido: base do regime A com RiR do regime B** (base deprimida + retenção
  integral) — cobra o investimento duas vezes (jurisprudência J8: −60% de valor). O inverso
  (base normalizada + RiR só de balanço) não cobra nenhuma; também proibido. Em fase de
  investimento (Gate 0.5), a entrega traz OS DOIS regimes — regime A = piso, regime B = base —
  como a 6ª bifurcação nomeada da dupla entrega. Camadas do RiR em `aplicacao.md` §2.
- **Qualidade do book** (obrigatória sob `--tv book`): classifique em `reportado` / `ajustado` /
  `reconstruído` / `proxy` / `nao_confiavel`. `nao_confiavel` ⟹ `book` fora do cenário-base
  (vira sensibilidade identificada); sem classificação ⟹ a entrega declara "qualidade do book:
  NÃO AVALIADA" — `reportado` não significa confiável.
- **Marca de estoque.** ≥ ~20% do valor vindo de MARCA DE ESTOQUE (laudo, NAV, cap rate, valor de
  reposição, landbank, estoque pronto, carteira marcada) ⟹ a marca é HIPÓTESE, não dado, e obedece a
  `Marca = VP(aluguel 1..T) + VP(Marca_T)`. Saídas obrigatórias: **fator de tempo**
  `VP(Marca_T)/Marca`; **apreciação implícita** (custo de capital DO ATIVO − yield corrente) contra a
  série observada, janela longa E recente; **T** derivado do giro observado do estoque — silêncio ⟹
  marca líquida hoje, o ramo mais otimista. Estoque que é INSUMO do fluxo ⟹ duas rotas (marca à vista
  com aluguel cobrado × fluxo pleno até T com marca descontada) e o **GAP entre elas reportado**,
  porque é ele que mede a violação. Reporte também `R = marca ÷ capitalização do fluxo corrente`
  (generalização do sub-alerta de recuperação). Nível da marca = **11ª escolha nomeada**; rota
  (a)/(b) = invariante de coerência. Regra completa em `aplicacao.md` §13, que este gate torna
  obrigatória.
- **Fronteira EV/EBITDA** (obrigatória quando a base é EBITDA): IFRS-16 e coerência com o EV,
  PPA/depletion no d, SBC, reportado vs ajustado, alíquota normalizada, fronteira de
  consolidação — checklist completo na `aplicacao.md` §1. Não declarado = "não avaliado", nunca
  implícito.
- **Natureza do `d`, antes da composição**: *"para manter o volume, a companhia precisa
  comprar outro ativo igual?"* Se SIM — royalty, catálogo musical, carteira de patentes, licença
  exaurível —, a D&A é o capex de reposição com outro nome: o `d` é economicamente REAL e não sai
  do cálculo. Se NÃO (PPA de aquisição), é não-caixa sem ativo a repor e infla o `d`. Confundir os
  dois **inverte o sinal do ajuste**; regra completa em `aplicacao.md` §2. **Respondida a natureza,
  falta a MAGNITUDE, e ela exige uma segunda medição:** capex de MANUTENÇÃO declarado (sustentação +
  adequação a normas + reposição, pelas rubricas que a companhia divulga) ÷ EBITDA, mais amortização
  de arrendamento quando o EBITDA for pós-IFRS-16. **O gap entre as duas rotas vai à entrega, e não
  se lê sozinho:** sob inflação a manutenção verdadeira DEVE exceder a D&A a custo histórico
  (evidência de mercado: capex excedeu depreciação em ~16–21% na média de longo prazo), logo
  D&A ≈ manutenção em termos nominais só valida o `d` quando o parque é NOVO — com parque velho é
  sinal de reposição adiada, e cruza com a guarda de moeda do `d` (`aplicacao.md` §2). Gap > 10% sem
  essa leitura ⟹ o `d` é hipótese de construção, não medição. Depois da natureza e da magnitude, a
  **composição**: em projeção nominal, capital FIXO só é cobrado pela expansão de VOLUME — planta não
  cresce porque o preço do produto subiu; o componente de PREÇO paga apenas GIRO, perna a perna e com
  o SINAL do ciclo de caixa. Cobrar intensidade MÉDIA de capital sobre o `g` inteiro superestima o
  custo de crescer (`aplicacao.md` §2, cadeia em §11.1c). **Acoplamento inegociável:** o componente de
  preço não consome capital de CRESCIMENTO, mas eleva o custo de REPOSIÇÃO do parque — que pertence ao
  `d`. Declarar um e esquecer o outro faz a inflação do estoque de capital desaparecer do modelo. E a
  **conservação**: d e RiR são duas metades do mesmo capital
  (capex_total + ΔWC = d×EBITDA + RiR×NOPAT); d econômico ≠ contábil obriga re-derivar o RiR na
  mesma base, e D&A > capex (fim de ciclo) obriga migrar o PAR inteiro para base caixa — regra e
  quadrantes proibidos em `aplicacao.md` §2, verificação em §11.1b (obrigatória em toda valuation
  real, e NECESSÁRIA mas não suficiente: ela testa o par, e mover capital de `d` para `RiR` a mantém
  fechada com as duas metades erradas).
- **Sinal do ciclo de caixa, antes de qualquer leitura do reinvestimento.** Com giro POSITIVO,
  crescer consome capital e encolher o libera. Com giro NEGATIVO — fornecedor e adiantamento
  financiando o cliente (varejo alimentar, marketplace, aérea, assinatura pré-paga, float de
  seguro) — o sinal INVERTE: crescer é parcialmente autofinanciado, o componente de giro do
  reinvestimento é negativo, e ENCOLHER consome caixa. O delator de RiR > 100% perde poder nesse
  regime e o teste migra para o componente FIXO isolado. Verifique o sinal antes de nomear
  qualquer bloco (`aplicacao.md` §2 e §8f).
- **Coerência do vetor.** O motor recebe (g, ROIC, W, d, t, D/E) como parâmetros LIVRES,
  mas na planilha de referência eles são OUTPUTS acoplados por identidades. Montar cenário
  perturbando um driver que veio da reversa — o uso normal — pode produzir vetor que nenhuma
  DRE/BP gera. Passe os opcionais `--roe`/`--roic`, `--kd`, `--gde`, `--nde`, `--rir-observado`,
  `--ebitda-ic` e, se o LL/ROE inclui rendimento de caixa, `--cash-yield`. O motor confronta
  quatro identidades. Com `Cash/E = D/E − ND/E`, a perna de alavancagem é **ROE = ROIC·(1 + ND/E)
  − Kd(1−t)·(D/E) + Kcash(1−t)·(Cash/E)**; a transformação simétrica é **WACC = [Ke +
  Kd(1−t)·(D/E) − Kcash(1−t)·(Cash/E)]/(1+ND/E)**. Sem `--cash-yield`, caixa positivo exige
  que seu rendimento tenha sido retirado do LL (ou seja imaterial), e o motor avisa. A rota
  preferida é operação separada de excess cash. **RiR observado × g/ROIC** (divergir é legítimo, ficar calado
  não — e com payout ≈ 0 a retenção observada é NÃO-INFORMATIVA: camadas do RiR, `aplicacao.md`
  §2); e **EBITDA/capital investido = ROIC/((1−d)(1−t))**, que o balanço tem de confirmar. Sem os
  opcionais nada quebra — o output declara o que NÃO pôde ser checado. Quando o ROIC
  for resíduo do triângulo (g e RiR inputs), a validação por unit economics do §11.2 da
  `aplicacao.md` é o terceiro canal, no mesmo estatuto do RiR observado — divergir é legítimo,
  ficar calado não; flag `--roic-ue` executável no `ev`.
  **Este gate não deriva drivers de demonstrações**: a cadeia DRE/BP/FC → drivers segue fora do
  motor por decisão de projeto. A skill aplica o framework; não substitui o modelo do analista.
- **Base monetária — invariante obrigatório de coerência, não uma 12ª escolha metodológica.**
  Nominal ou real, declarada uma vez e ecoada na entrega; g, custo de capital e rentabilidade na
  MESMA base, sempre. As **onze escolhas metodológicas** continuam sendo bifurcações econômicas; a
  base monetária é uma convenção de consistência que não deve mudar o valor quando todos os inputs
  forem convertidos de forma coerente. Escolha operacional central: nominal — o confronto é contra
  o preço de mercado, que é nominal. Até existir trava de motor, a verificação de mesma base é
  manual e declarada. Regra completa e decomposição do g por componente em `aplicacao.md`
  ("Base nominal vs real" e "RiR por componente").
- **Confronto com o caixa operacional PUBLICADO.** Todas as cadeias partem de EBITDA, D&A, capex e
  giro — peças montadas pelo analista. Antes de aceitá-las, confronte a soma contra o caixa líquido
  gerado nas atividades operacionais que a companhia publica: `EBITDA − ΔWC − juros pagos − IR pago`
  contra a linha do fluxo de caixa, com os itens não-caixa do EBITDA ajustado devolvidos. **Não é
  identidade** — a classificação de juros e IR entre operacional e financiamento varia por norma e
  por companhia —, é confronto declaratório: reporte o gap e o que ele contém. Razão econômica: é o
  teste de qualidade de lucro mais barato que existe, e sem ele lucro sustentado por capitalização
  agressiva, provisões ou receita não realizada atravessa todos os demais gates sem sintoma. Cadeia
  em `aplicacao.md` §11.8.
- **Clean surplus.** SE o usuário fornecer balanço e DRE projetados: verifique ano a ano
  PL_t = PL_{t−1} + LL_t − Div_t. Diferença ≠ 0 é "fluxo não explicado", declarado com magnitude; o
  usuário decide — corrigir ou prosseguir com a ressalva na entrega. Nunca corrija em silêncio. Sem
  projeções fornecidas, não há o que verificar — os inputs serão derivados pelo fluxo normal.

### Gate 0.5 — Fase da companhia: decide o regime da base, ANTES das premissas

Classifique e declare, com os observáveis:
- **INVESTIMENTO** (payout ≈ 0 E margem comprimida por decisão declarada da administração E/OU
  consenso t+2 ≫ LTM): teorema da base coerente obriga a dupla base (regime A = piso, regime
  B = base); a reversa em nível SÓ conclui após o confronto temporal (`aplicacao.md` §4); RiR
  contábil não-informativo (camadas do RiR, `aplicacao.md` §2).
- **DISTRIBUIÇÃO** (payout relevante e estável): retenção observada É informativa; base
  reportada serve; fluxo padrão sem mudanças.
- **MISTA** (payout > 0 com programa de investimento declarado): dupla base, com o RiR requerido
  derivado do deployment líquido — o caso comum em maduras que reinvestem.
- **HÍBRIDA FINANCEIRA** (carteira de crédito > 50% do equity OU receita financeira > 30% da
  receita, com funding próprio): rode `aplicacao.md` §12 (multi-segmento) com o braço financeiro
  pelo §9 (P/L; P/VP = P/L × ROE — prática padrão de SOTP: método por segmento, P/VP para a
  subsidiária financeira) e o operacional pelo fluxo normal; blended só com os testes declarados
  e a direção do erro. **Caixa/E:** com dívida líquida positiva ou funding de carteira
  relevante, caixa/E = 0 é a escolha central obrigatória (§9) — o ramo bruto é a 7ª escolha
  metodológica nomeada, nunca o caso-base.

Fase mal classificada é o erro upstream de todos os outros (jurisprudência J8: companhia
INVESTIMENTO + HÍBRIDA rodada como DISTRIBUIÇÃO de payout zero).

### Gate 1 — Convenção terminal: qual hipótese sobre a morte do spread

**Não existe default:** o motor exige `--tv` e recusa rodar sem ele. A escolha é pela **DURAÇÃO
ECONÔMICA do claim**, não pelo rótulo do setor — regras completas, teste do teto e travas em
`aplicacao.md` §3 (a autoridade desta decisão).

| Convenção | Hipótese terminal | TV |
|---|---|---|
| **`book`** (ex-`ic`) | Renda residual truncada: o NOPAT inteiro colapsa para W×IC no ano n+1; exige book confiável (Gate 0) E âncora crível de saída. No enterprise, `ROIC_book` é a **média inicial/forward** que ancora `IC₀ = NOPAT₁/ROIC_book`; trailing só entra após alinhamento temporal | capital investido acumulado |
| **`convergencia`** | RONIC = W só no capital NOVO; rendas existentes preservadas (McKinsey/Mauboussin) | NOPAT/W |
| **`gordon`** (ex-`spread`) | rentabilidade terminal = RONIC/ROIIC **MARGINAL** do capital novo que sustenta gp; spread persistente, nulo ou negativo, justificado por DURAÇÃO | perpetuidade com gp |

**A diferença não é cosmética.** No caso **conflacionado** (book=marginal=50%), com g 5%, W 7%,
n 10: `book` 9,86x × `convergencia` 20,55x; cruzam exatamente quando book=marginal=WACC. A velha
leitura "o múltiplo cai com ROIC" pertence a esse caso conflacionado. Com `--roic-book` separado,
o médio inicial ancora IC₀ e o marginal remunera o capital novo: elevar apenas o marginal, com g>0,
**aumenta** o valor enterprise; elevar apenas o book inicial reduz o valor. Sob `convergencia`, o
múltiplo também sobe com o marginal. Na dúvida, rode as candidatas e mostre o gap: ele É a
informação. Nunca escolha em silêncio. **A preliminar não é final** — revalidação obrigatória na
entrega, quando a rentabilidade marginal existir.

**TRAVAS (resumo executivo; detalhe e números em `aplicacao.md` §3):** `book` SEM book separado
com marginal < custo ⟹ a conflação médio×marginal pode premiar o destruidor de valor
(TV = NOPAT/retorno cresce quando a variável única cai) — separe os papéis ou use `gordon` com
terminal < custo declarado. **Enterprise:** com `--roic-book` informado, IC₀ = NOPAT₁/ROIC_book e
o TV acumula o capital novo ao ROIC marginal; com g>0 o múltiplo sobe quando apenas o marginal
sobe (W 7%, g 3%, book 10%: 10,16x a marginal 2% × 12,59x a 8%). A média do estoque no ano n é
output, não input congelado. A raiz continua CONDICIONADA à tese de saída pelo capital investido,
e a monotonicidade forward em g **não garante raiz única na base corrente**. **Equity [v9.30]:**
`--roe-book` acumula por clean surplus, derivado sem analogia: ΔE_t = (g/ROE_marg)·LL_t e E_n
coincide com a forma do firm. Na convenção `book`, os fluxos explícitos são **dividendos**, não
FCFE com Δcaixa: o caixa retido já está dentro de E_n e somá-lo aos fluxos duplicaria valor.
Consequência obrigatória: Caixa/E é neutro na `book`; DDM = residual income = motor. No bifásico,
E é carregado entre fases como state variable e o corte artificial de uma trajetória idêntica não
pode alterar o valor. Se o
próprio book < custo, some o sub-alerta de RECUPERAÇÃO. Marginal ≠ médio sob `book` ⟹
`--roic-book`/`--roe-book` obrigatório — sem ele o motor conflaciona os dois papéis e alerta.

### Gate 2 — Nível: defasagem (o nível que já mudou)

Financials reportados/TTM embutem o nível MÉDIO dos drivers no período-base. Se o spot divergiu, o
múltiplo congelado responde à pergunta errada.

Monte o **registro de drivers** — não existe "o" driver: commodity, câmbio, frete, energia, spread
de captação, teto/tarifa regulatória, take-rate, insumo. **A elasticidade é DERIVADA, não
arbitrada:** com custo e volume fixos no curto prazo é alavancagem operacional pura,
`elasticidade = linha exposta ÷ métrica-base`, **com sinal** (use `auto:LINHA:METRICA[:custo]`):
driver de **receita** (commodity vendida, take-rate, tarifa) entra positivo; driver de **custo**
(frete, energia, insumo, câmbio no COGS) entra **negativo** — a linha exposta é o custo do insumo,
não a receita total. Só arbitre quando não houver como derivar, e diga por quê.

Rode `drivers`. **O gate dispara pelo IMPACTO = |elasticidade × gap|, não pelo gap:** gap de 12%
com elasticidade 0,1 é irrelevante (1,2%); gap de 8% com elasticidade 3,0 move o valor (24%).
**Trava anticombinatória:** viram cenário só os dois de maior impacto entre os que passam do
limiar; o resto é linha de sensibilidade, e quem ficar de fora acima do limiar tem que ser
declarado. Drivers podem se compensar — o registro reporta **efeito líquido (com sinal)** e
**soma dos brutos**, e alerta quando o líquido é menos da metade dos brutos: reporte os dois, o
líquido decide o gate agregado e os brutos mostram o risco de a compensação não se sustentar. Gate disparado ⟹ `normaliza`
ALÉM do período-base e reversa do nível implícito (`nivel`).

### Gate 3 — Nível: degrau disponível e capacidade pré-construída

Capacidade ociosa que eleva o lucro sem reinvestimento: índice de capital acima do piso, caixa
excedente estrutural, capacidade licenciada, folga de covenant, margem regulatória. Se existir,
rode `degrau`. **Regra inegociável: o degrau GRATUITO entra como RENTABILIDADE (× h), nunca como
g, e a rentabilidade terminal NÃO acompanha.**

**Gatilho da capacidade pré-construída.** Caso distinto do degrau gratuito: crescimento
que consome GIRO mas não capital fixo, porque o parque já foi pago. Disparam simultaneamente:
(i) capital fixo intensivo — imobilizado + direito de uso ≥ ~40% dos ativos operacionais, OU
d ≥ ~20% do EBITDA; e (ii) evidência de ociosidade material — utilização divulgada < ~85%,
linhas/plantas "atingindo regime" declaradas, capex recente ≫ D&A com receita ainda respondendo,
ou guidance de margem "por escala". Disparado ⟹ decompõe-se o RiR por componente
(RiR = RiR_fixo + RiR_wk, pela conservação de capital) e a **leitura de capacidade** vira a 10ª
escolha metodológica nomeada. Entrada, fases, compressões, composição multifásica e travas em
`aplicacao.md` §8f — fases compõem NO TEMPO (§8f), safras NO CAPITAL (§12); quando os claims da
base instalada e da expansão tiverem durações distintas, §12 (safra de capital).

**Coerência:** o deployment viola D/E constante por construção. O resultado vale para o **estado
estacionário pós-deployment**, nunca para a trajetória — por isso existem o fator de transição
sobre o incremento (rampa linear por padrão; `pontual` só com evento datado — a 20% e 4 anos, 0,647
contra 0,482) e a rentabilidade terminal parada.

Teoria em `derivacao.md` §8, aplicação em `aplicacao.md` §8.
