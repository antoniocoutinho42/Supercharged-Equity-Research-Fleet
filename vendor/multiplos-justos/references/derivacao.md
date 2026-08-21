# Derivação, provas e limites de validade

Base: planilha "Justified Multiples Model" do usuário (modelo de 3 demonstrativos simulado
por 10 anos + TV, com fechamento algébrico exato — checks = 0) e bloco APV vF8.

## 1. A identidade do reinvestimento

Se todo crescimento vem de novos investimentos e o capital marginal rende ROIC constante:
g = RiR × ROIC ⟹ RiR = g/ROIC ⟹ **FCFF = NOPAT × (1 − g/ROIC)**.
Provado por 3 vias independentes na planilha (contábil via CFO+CFI; fórmula; NOPAT anterior
crescido × retenção). ROIC validado por 3 decomposições: NOPAT/(ND+E)ant; g_sust/RiR;
giro do NOA × margem operacional líquida.

Lado equity: retenção necessária = g/ROE, mas parte do crescimento do ativo é financiada por
dívida nova (D/E constante) e parte é caixa que acumula:
**FCFE = LL × [(1 − g/ROE) + (GD/E − ND/E)·(g/ROE)]**, onde GD/E − ND/E = Caixa/Equity.
g sustentável = ROE × (1 − payout). Payout emerge endogenamente do sweep de caixa.

## 2. O múltiplo justo

EV/NOPAT_curr = Σₜ₌₁ⁿ (1−g/ROIC)(1+g)ᵗ/(1+W)ᵗ + TV_desc.
Forward = current/(1+g). EV/EBITDA = EV/NOPAT × (1−d)(1−t) porque NOPAT = EBITDA(1−d)(1−t).
P/L análogo com Ke, ROE e o fator de conversão do FCFE.
Implementar sempre por SOMA EXPLÍCITA (loop) — elimina a singularidade g=W da forma fechada
(ROIC=W isolado não é singularidade; g=ROIC=W é indeterminação 0/0 removível, limite NOPAT/W).
Casos degenerados: ROIC=W ⟹ múltiplo FWD = 1/W (Miller-Modigliani) — sob `book`, exige o BOOK
igual a W também (marginal=W com book≠W NÃO dá 1/W; ver §2); o corrente é 1/W × (1+g). Atenção: g=0 NÃO é caso degenerado na convenção `book` com n finito — ver §4.

## 3. Valor terminal — as TRÊS convenções

A frase "a vantagem competitiva se exaure no ano n" admite duas matemáticas diferentes, e a
diferença não é cosmética. A v8 separa as duas e mantém a Gordon livre como terceira:

**(a) `book` (ex-`ic`) — renda residual truncada:** o NOPAT **inteiro** colapsa de ROIC×IC para
W×IC no ano n+1. Consequências provadas: TV = capital investido no fim do CAP (excess returns = 0
sobre TODO o capital); g de valor na perpetuidade = 0 mesmo com crescimento nominal;
TV_desc = (1+g)ⁿ⁺¹/(ROIC_book·(1+W)ⁿ) — divide por ROIC porque IC_n = NOPAT_{n+1}/ROIC.
Equivalência exata com Preinreich–Lücke: EV = IC₀ + Σ_{t≤n} EVA_t (reconcilia a 1e-15 no motor).
Leitura econômica (v9.7): a convenção ANCORA o TV no capital investido MENSURADO — lê-la como
"fim da vantagem competitiva" exige adicionalmente que o book seja medida economicamente
confiável (classificação obrigatória em `aplicacao.md` §1) e que não existam rendas residuais
futuras omitidas. ATENÇÃO: penaliza estruturalmente franquias persistentes — ROIC alto ⟹ book pequeno ⟹ TV pequeno.
Há um TETO matemático no múltiplo atingível **nesta convenção com ROIC fixo**; o múltiplo justo
CAI à medida que o ROIC sobe, e coincide com 1/W exatamente em ROIC = WACC.

**Conflação marginal×médio — a trava da `book`:** o denominador do TV é o ROIC **médio** do
estoque (IC_n = NOPAT/ROIC_médio), mas o motor de g usa o **marginal** — e §11.1 de `aplicacao.md`
manda derivar o marginal justamente porque difere do contábil. Usar a mesma variável nos dois
papéis é erro estrutural: marginal 25% vs médio 10% ⟹ TV subdimensionado em 60% e valor −33%.
O motor aceita `--roic-book`/`--roe-book` para o papel de médio e alerta quando falta.

**(b) `convergencia` — RONIC = W no capital novo:** o NOPAT existente é preservado; só os
investimentos NOVOS deixam de criar valor. TV = NOPAT_{n+1}/W ⟹ TV_desc = (1+g)ⁿ⁺¹/(W·(1+W)ⁿ).
É uma interpretação corrente de exaustão da vantagem NO CAPITAL INCREMENTAL (McKinsey,
Mauboussin): o retorno dos novos investimentos converge ao custo de capital, enquanto o nível
normalizado de NOPAT terminal — incluindo as rendas dos ativos existentes — é preservado. NÃO é
o desaparecimento de todas as rendas econômicas: essa hipótese, mais dura, é a `book`. Invariante a gp por
construção — equivale exatamente à `gordon` com ROIC_TV = W, qualquer gp. Sob esta convenção o
múltiplo justo **SOBE** com o ROIC. Magnitude do gap: ROIC 50%, g 5%, W 7%, n 10 ⟹ `book` 9,86x
vs `convergencia` 20,55x — mesmas palavras, o dobro do valor. As duas cruzam em ROIC = WACC.

**(c) `gordon` (ex-`spread`) — ROIC_TV e gp livres:** TV = NOPAT_{n+1}(1 − gp/ROIC_TV)/(W − gp),
gp < W obrigatório. **Semântica do parâmetro (v9.8, C-01):** ROIC_TV é a rentabilidade MARGINAL
TERMINAL (RONIC/ROIIC) — gp/ROIC_TV é o RiR do capital novo que sustenta gp, pela identidade
gp = RiR_TV × RONIC_TV. O blended do portfólio é proxy só sob convergência médio↔marginal
declarada; quanto maior o R usado, menor o RiR imputado e maior o TV — blended > RONIC real
superestima o terminal. Três regimes legítimos, todos declarados — e ROIC_TV > W nomeado pelo que é: oportunidades de
reinvestimento com VPL POSITIVO EM PERPETUIDADE (o modelo precifica a hipótese; origem, defesa e
limite da vantagem ficam fora dele): ROIC_TV > W (claims de longa
duração — royalty, rede, marca — justificados por DURAÇÃO econômica, não por rótulo de setor);
ROIC_TV = W (colapsa na `convergencia`); ROIC_TV < W (destruição persistente declarada). Aqui o
múltiplo justo sobe com o ROIC do explícito e o TV não encolhe com o book.

**Assimetria da `book` abaixo do WACC (não usar):** monotonicamente decrescente em ROIC em TODA a
faixa, inclusive abaixo do custo de capital. Como IC = NOPAT/ROIC, o TV explode quando o ROIC cai;
e assumir convergência do ROIC PARA CIMA até o WACC é, para um destruidor de valor, hipótese
criadora de valor embutida. Resultado (W=7%, g=3%, fwd): 30,20x a ROIC 2% · 19,06x a 4% · 14,29x a
7% · 12,38x a 10% · 10,89x a 15%. Para spread negativo persistente, `gordon` com ROIC_TV < W.
Corolário: o teto da `book` é teto em g e CAP com ROIC FIXO **sob esta convenção** — não teto
absoluto e não propriedade da convergência competitiva (sob `convergencia` não há teto análogo:
o sup em n cresce sem esse limite).

## 4. Prova de que os drivers são spread e crescimento

Abordagem excess returns (EVA): EV = IC₀ + Σ ICₜ₋₁(ROIC−WACC)/(1+W)ᵗ — reconcilia
exatamente com o DCF. Fora das neutralidades, o sinal do gradiente em g é o sinal do spread —
**na base forward**. Na base corrente o fator (1+g) domina e um destruidor de valor exibe múltiplo
crescente em g (ROIC 5%, W 7%, n 10: corrente 17,19 → 17,40 de g=0 a 6%; forward 17,19 → 16,42).
É essa matriz que o comando `tabela` imprime; declarar a base é condição de validade da leitura.

**As duas linhas de neutralidade, com os qualificadores corretos:**
- **Coluna ROIC=WACC:** múltiplo forward constante em g e igual a 1/W. Exata, verificada. Sob
  `book` com papéis separados, a coluna exige marginal E book iguais a W: com marginal=W e book=20%
  (W 7%, n 10, g 6%) o forward é 5,83x, não 14,29x. Sob `convergencia`/`gordon` o book não entra
  no TV e marginal=W basta. Exceção pontual: g=0 com book=W é neutro para qualquer marginal (o
  marginal só entra via g/ROIC).
- **Linha g=0:** constante em ROIC apenas (a) na forma perpétua (1−g/ROIC)/(W−g), onde g=0 ⟹ 1/W
  para qualquer ROIC; (b) nas convenções `gordon` e `convergencia`, cujos TVs não referenciam o
  ROIC do explícito; ou (c) na `book` com n→∞. **Na `book` com CAP finito a linha NÃO é plana**:
  com g=0 o explícito vale a anuidade a_n (7,0236 para W=7%, n=10) e o TV vale 1/(ROIC_book(1+W)ⁿ),
  que depende do book — 23,97x a ROIC 3%, 14,29x a 7%, 9,57x a 20%, 8,04x a 50%. A planura só
  reaparece quando o peso do TV vai a zero (n≈200 ⟹ 14,2857 para qualquer ROIC). A generalização
  veio da matriz perpétua e não sobrevive à implementação com CAP finito e TV = capital investido.

**Lado equity — uma neutralidade a menos.** A simetria ROIC→ROE, WACC→Ke vale para tudo acima
(qualificador de base, linha g=0 por convenção, assimetria da `book` abaixo do custo de capital), com
uma exceção: **ROE = Ke só é linha de neutralidade quando caixa/E = 0**. O termo
(GD/E − ND/E)·(g/ROE) do FCFE devolve caixa a cada ponto de crescimento, de modo que uma empresa com
caixa líquido tem P/L forward crescente em g mesmo sem spread algum (Ke = 12%, n = 10: com caixa/E
= 0 o P/L fica em 8,3333 = 1/Ke para g = 0/3/6%; com caixa/E = 20% vai a 8,3333 → 8,6485 → 9,0390;
com 50%, a 8,3333 → 9,1212 → 10,0975). Isso não é artefato: é o valor de não precisar reter o
lucro inteiro para financiar o crescimento. Mas significa que a matriz g×ROE de uma empresa com
caixa não tem coluna plana, e que o gradiente em g mistura spread com liberação de caixa — separe
os dois antes de atribuir o movimento do múltiplo à rentabilidade.

**Política de caixa no terminal (correção C1, v8.1).** O FCFE canônico com o balanço crescendo a
gp e proporção de caixa constante inclui o termo de caixa TAMBÉM no terminal:
FCFE_TV = LL_{n+1}·[(1−gp/ROE_TV) + caixa·(gp/ROE_TV)]. É a mesma identidade de três rotas da
planilha (Div + Δcaixa = FCFF − juros(1−t) + ΔD, linhas 226–235), estendida ao terminal e provada
no motor por identidade contábil e por força bruta (simulação ano a ano, erro < 1e-14). No
`gordon`, `politica_tv='continua'` é o default; `'encerra'` (política morre no ano n) é hipótese
legítima mas declarável — omiti-la silenciosamente subestima o P/L em 2–6% em parâmetros
plausíveis. Consequência documentada: sob 'continua', a identidade equity
convergencia ≡ gordon(ROE_TV=Ke) deixa de ser invariante a gp quando caixa ≠ 0 (o balanço
crescente traz emissão de dívida que financia distribuição, com Ke fixo por input — a forma
fechada do TV vira [(Ke−gp)+caixa·gp]/[Ke(Ke−gp)]); sob 'encerra' ou com caixa = 0 a invariância
segue exata. Na `book` o termo é nulo por construção (crescimento de valor zero no terminal,
Δcaixa = 0 — exatamente o caso provado na planilha); na `convergencia`, sem gp declarado, idem.

## 5. Consistência Ke↔WACC (APV, sem circularidade)

Âncora única: **Ku** (desalavancado, exógeno). Então, com dívida determinística (MM):
1. Vu_t = PV(FCFF a Ku) por recursão backward; VTS_t = PV(shields t·Kd·D a Kd)
2. V_t = Vu_t + VTS_t; E_t = V_t − D_t (bruta, a mercado; cupom=Kd ⟹ mercado=face)
3. **Ke_t = Ku + (D_{t−1} − VTS_{t−1})(Ku − Kd)/E_{t−1}** (Fernandez) ≡ (E_t+FCFE_t)/E_{t−1}−1
4. WACC_t = [E·Ke_t + D·Kd(1−t)]/V a mercado, período a período
Provas: FCFE @ Ke_t reproduz E₀ exatamente; FCFF @ WACC_t reproduz V₀ (identidades).
**A recursão está IMPLEMENTADA no motor** (`justos.py apv`): devolve a trilha Ke_t/WACC_t e os
três checks da planilha vF8 (FCFE@Ke_t=E0, Ke dinâmico = fórmula de Fernández, FCFF@WACC_t=V0),
zerados por construção; anchors do bloco APV no selftest. O comando `kewacc` é o caso ESTÁTICO
(perpetuidade com alavancagem constante) — sanity check, não a trilha. Um WACC único aplicado a
todos os períodos não corresponde a nenhum período da trilha consistente quando a alavancagem a
mercado deriva (no caso-base, WACC_t vai de 18,65% a 18,08% e Ke_t de 20,56% a 21,74%; o WACC estático de 18,73% não corresponde a nenhum período).
Perpetuidade MM: Ke = Ku + (Ku−Kd)(1−t)D/E. Regime `ku` (shields a Ku): Ke = Ku + (Ku−Kd)D/E — a
forma de perpetuidade associada a Harris-Pringle. ATENÇÃO ao que o motor implementa: ele aplica a
convenção de RISCO dos shields (todos a Ku) sobre uma trajetória de dívida EXÓGENA, D_t = D0(1+g)^t;
não resolve D_t = L×V_t, logo NÃO mantém D/V constante — a série sai em `DV_t_%` e, na âncora, vai
de 18,75% a 36,28%. Harris-Pringle e Miles-Ezzell verdadeiros são roadmap planilha-primeiro. ERROS CLÁSSICOS: pesos contábeis no WACC (usar mercado); Ke fixo
quando alavancagem a mercado deriva; Ke e WACC como inputs independentes (rotas FCFF e FCFE
divergem — na planilha, 159,0 vs 150,5 por isso).

**Regime monetário e consistência de Fisher (v9.14 — paper §6.15).** O Ke do CAPM é NOMINAL. Em
análise price-taker normalizada a nível, o g da fórmula é volume (o preço foi expulso para o nível
pela taxonomia) e os fluxos ficam em preços de hoje — reais na moeda do driver. Consistência exige
uma das duas rotas, idênticas por Fisher:

    (1 + Ke_real) = (1 + Ke_nominal) / (1 + π)          [π = inflação declarada]

    Rota A:  V = Σ CF_hoje,t / (1 + Ke_real)^t          [fluxos de hoje, taxa real — horizonte inteiro]
    Rota B:  V = Σ CF_hoje,t (1+π)^t / (1 + Ke_nom)^t   [preço cresce π de graça, taxa nominal]

No motor: rota A = passar Ke_real em `--wacc`/`--ke` com `--moeda *-real` (o teto real do gp da
guarda v9.4 se ajusta sozinho); rota B no terminal = `gordon` com rentabilidade terminal → ∞ e
gp = π (o crescimento de preço não consome reinvestimento — é o caso-limite RiR→0 do §6.9 do
paper). A rota B aplicada só no TV é aproximação (o explícito continua congelado); declarar.
Descontar fluxo de hoje a Ke nominal sem nenhuma das rotas = assumir o driver caindo π a.a. em
termos reais em perpetuidade — hipótese substantiva que precisa ser declarada, nunca default
silencioso (Modigliani-Cohn, 1979).

**Convenção temporal (C3).** Todas as fórmulas descontam fluxos ao FIM de cada período:
Σ FCFF_t/(1+W)^t. Sob fluxo uniforme ao longo do ano, o desconto correto é o do meio do período,
e a razão entre as duas convenções é (1+W)^0,5. Esse fator é EXATO para a convenção de **midpoint**
— todo o fluxo anual concentrado no ponto médio —, que é a que `--mid-year` implementa. Para fluxo
perfeitamente uniforme ao longo do ano, PV = FCF ∫₀¹ (1+W)^(−t) dt e a razão exata contra o fim de
ano é W/ln(1+W): a 9% dá 1,044354 contra 1,044031 do midpoint, diferença de 0,031% — imaterial,
mas não nula, e a palavra "exatamente" pertence ao midpoint, não ao fluxo uniforme. Em qualquer dos
dois casos o fator é constante, logo não altera nenhuma
neutralidade nem monotonicidade, só o NÍVEL (a 9% de custo, +4,4%). O motor mantém fim de ano por
default (é a convenção da planilha de referência) e oferece `--mid-year`. Comparações de nível com
múltiplos justos de terceiros exigem declarar qual convenção está em uso — parte relevante das
divergências de 4–5% entre modelos é isto, e não premissa econômica.

**Custo de capital como input no lado equity (C2).** As fórmulas de `pe` tomam Ke como EXÓGENO e
fixo ao longo do CAP, enquanto GD/E e ND/E entram como política de caixa/dívida. Isso é
internamente coerente para um cenário único, mas comparar cenários com estruturas de capital
diferentes sob o MESMO Ke atribui à política de caixa um efeito que em parte pertence ao custo de
capital — e a própria trilha consistente mostra o Ke derivando (§5). Duas saídas: (a) rodar `apv`,
extrair Ke_t e realimentar o `pe` cenário a cenário; (b) manter Ke fixo e declarar que a
comparação entre cenários é ceteris paribus em custo de capital. O motor emite a limitação no
diagnóstico sempre que caixa/E ≠ 0.

## 6. Premissas de validade (citar as violadas no caso concreto)

Modelo econômico: (1) crescimento só por novos investimentos — exclui ganhos de escala e
expansão de margem; (2) retornos marginais constantes no CAP (giro do NOA constante);
(3) D/E constante; (4) proporção de caixa constante; (5) Kd constante.
Fórmula de múltiplos: margens, RiR e payout constantes. RiR fixo + g muito alto pode gerar
caixa negativo (teste de estresse de consistência do par g–RiR).
g efetivo ≠ g sustentável embute trajetória: g<g_s ⟹ ROIC/ROE/Kd declinantes;
g>g_s ⟹ crescentes. A identidade "FCFF cresce a g" quebra quando RiR muda (ex.: transição
para o TV) — Check 3 da planilha. Preço de driver exógeno (commodity, câmbio) NÃO está no
modelo: margem congelada — re-basear via `normaliza` (ver §7 de `aplicacao.md`).

## 7. Anchors de validação (caso-base da planilha)

g=11%, ROIC=34,352%, WACC=18,733%, n=10, d=6,667%, t=30%, ROE=44,827%, Ke=22%,
GD/E=53,846%, ND/E=46,154% ⟹ EV/NOPAT 6,4296x · EV/EBITDA 4,2007x · P/L 5,7337x ·
EV=189,03 · reversa recupera g=11% e ROIC=34,35% exatos. Anchor da ponte `normaliza`:
EBITDA_base 446,43 + (730,95/5,00)×(6,26−5,00) = 630,6294. O script aborta se divergir.

## 8. Nível, taxa e rentabilidade — teorema da classificação

**As portas do motor.** Eventos elementares entram por exatamente uma porta: (1) NÍVEL — altera a
métrica-base (EBITDA₀, LL₀) ou o capital, sem alterar taxa nenhuma; (2) TAXA (g) — altera o ritmo
de comprometimento de capital novo, sujeito a g = RiR × ROIC; (3) RENTABILIDADE — altera o retorno
por unidade de capital, sujeito à mesma identidade. Eventos COMPOSTOS (aquisição, cisão, virada de
ciclo com capex) decompõem-se num vetor (ΔNível, Δg, ΔRentabilidade, ΔFunding) com componentes em
mais de um eixo — a proposição vale para cada componente, não obriga o evento inteiro a uma porta
só. O erro clássico continua sendo o mesmo: lançar o componente de nível como taxa.

**Proposição.** Seja um evento que eleve permanentemente o lucro por um fator h > 1 SEM consumir
capital novo financiado por lucro retido. Sua representação correta é um degrau — em rentabilidade,
se o capital contábil permanece constante (ROIC → ROIC·h; ROE → ROE·h), ou equivalentemente um
re-base da métrica — e NUNCA um incremento em g. A identidade g = RiR × ROIC é o classificador: sem
reinvestimento proporcional, o evento não é g por definição, não por convenção de modelagem.

**Corolário 1 — o RiR delator (hipótese diagnóstica, não veredicto).** Se ao incorporar um suposto
"crescimento" o RiR = g/ROIC implícito ultrapassa 100% (payout negativo), o crescimento não é
autofinanciável e EXIGE fonte de funding declarada — captação, dívida, capital de terceiros. Sem
funding plausível, a hipótese FORTE é erro de classificação: degrau lançado como taxa. Mas empresas
reais crescem acima do autofinanciável com funding externo legítimo; o RiR > 100% abre a
investigação, não a encerra. O diagnóstico de RiR (§6) é, portanto, um classificador de eventos
condicional ao funding.

**Corolário 2 — o erro tem sinal dependente do regime.** Dois erros distintos: (B) classificação —
o degrau vai só para g; (C) dupla contagem — vai para a métrica-base E para g. Verificado no motor
(lado equity, Ke 20%, n 10, `gordon` com rentabilidade terminal fixa no ROE original, gp 6,5%,
caixa/E 0; h = 1,485 traduzido por um analista desavisado como Δg = h^(1/4) − 1 = +10,4 p.p. sobre
g de 12%). Valores em P/VP = P/L corrente × ROE:

| ROE | regime | base | (A) correto | (B) só no g | erro (B) | (C) nível+g | erro (C) |
|---|---|---|---|---|---|---|---|
| 16% | ROE < Ke | 0,67 | 1,41 | 0,34 | −76% | 1,71 | +22% |
| 20% | ROE = Ke | 1,12 | 2,07 | 1,22 | −41% | 3,03 | +46% |
| 24% | ROE > Ke | 1,57 | 2,73 | 2,11 | −23% | 4,35 | +59% |
| 28% | ROE > Ke | 2,01 | 3,39 | 3,00 | −12% | 5,67 | +67% |

RiR implícito na rota (B): 139,9% a ROE 16%; 112,0% a 20%; 93,3% a 24%.

Três leituras, uma por regime:
- **Rentabilidade < custo de capital:** a rota errada INVERTE o sinal do evento — um degrau
  inequivocamente criador de valor registra como destruição. Causa: §4 — o gradiente em g tem o
  sinal do spread.
- **Rentabilidade = custo de capital:** o evento DESAPARECE. Pela neutralidade exata (§2), o
  múltiplo forward é invariante a g: 5,0000 antes e depois. Na base corrente aparece um ganho
  espúrio de +9,3%, que é puro reajuste (1+g), não valor.
- **Rentabilidade > custo de capital:** o múltiplo infla, mas o VALOR fica subestimado, porque o
  degrau nunca entrou na métrica-base. Múltiplo maior sobre lucro menor.

Consequência: **não existe ajuste conservador** para um degrau mal classificado. Só existe
classificar certo. E, na vizinhança da neutralidade, o erro não deixa rastro — é a única patologia
do framework que se manifesta como "nenhum efeito" em vez de número estranho ou raiz ausente.

**Mecânica do degrau em negócios com restrição de capacidade** (índice regulatório ou estrutural
limitando a base geradora — capital regulatório, solvência, licença, covenant):
```
h = índice_atual / índice_alvo
rentabilidade_pós = rentabilidade × [1 + (h − 1) × m]        m = retorno marginal ÷ retorno médio
g inalterado; rentabilidade terminal inalterada
captura = 1/(1 + custo de capital)^T, aplicada SOMENTE ao incremento
```
A rentabilidade terminal não acompanha porque a competição não deixa o spread do capital marginal
sobreviver ao CAP; perpetuar a rentabilidade pós-degrau produz valores que nenhum equilíbrio
competitivo sustenta — aritmética, não economia.

**Relação com o teorema do teto (§3).** Um degrau eleva o valor sem mover o teto do múltiplo,
porque atua sobre a base e não sobre o múltiplo. Logo, um múltiplo de tela inalcançável tem TRÊS
explicações possíveis, e a ordem de investigação importa: (1) degrau ausente da métrica-base;
(2) convenção terminal errada; (3) preço. Inverter a ordem leva a trocar de convenção — decisão de
altíssimo impacto no valor — quando o problema era um EBITDA-base defasado.

**Reversa em nível.** Como valor = múltiplo × métrica, a métrica implícita no preço é
`alvo / múltiplo justo`, e o degrau implícito é a razão com a métrica atual. Quando há ponte de
alavancagem operacional, converte-se em nível de driver implícito. É a única variável implícita do
framework com observável de mercado direto para confronto (spot, piso regulatório, margem
histórica) — todas as outras só podem ser julgadas contra a intuição do analista.

## §8b — Ponte de releveraging: derivação e prova do colapso (v9)

**Setup.** Dois regimes de estrutura: fase 1 com (GD/E₁, ND/E₁) por n₁ anos; fase 2 com
(GD/E₂, ND/E₂) daí em diante. Balanço estilizado: ativos fixos financiados por equity e dívida
líquida, `E = AF/(1+ND/E)`; caixa = E·(GD/E − ND/E); dívida bruta = E·GD/E.

**O rebase do equity.** Na transição os ativos não mudam — muda quem os financia. Com AF fixo:

```
E₂/E₁ = (1+ND/E₁)/(1+ND/E₂) ≡ razão
```

**O fluxo do evento.** Dívida antes = GD/E₁·E₁; depois = GD/E₂·E₂ = GD/E₂·razão·E₁. A diferença
é caixa que entra (emissão) ou sai (amortização) do bolso do acionista no ano n₁+1 — no modelo
de três demonstrações da vF19, aparece em "Debt net amortization/raise" do CFF e cai inteiro em
dividendos/aporte. O fator (1+Kd_at) é o ajuste de timing: o lucro do ano n₁+1 já foi calculado
com juros da estrutura nova, mas os juros daquele ano correram sobre a dívida velha — a
diferença de um ano de serviço após impostos acompanha o principal. Logo:

```
fluxo_{n₁+1} = E_pré · (GD/E₂·razão − GD/E₁) · (1 + Kd·(1−t))
PV = fluxo / [(1+Ke₁)^{n₁} · (1+Ke₂)]
```

com `E_pré = E_{n₁}` na base da fase 1. Em base-lucro (NI₀ = 1, como a vF19):
`E_pré = (1+g₁)^{n₁+1}/ROE₁` — o equity lido como lucro forward sobre ROE marginal.

**Prova do colapso.** Estrutura igual ⟹ ND/E₂ = ND/E₁ ⟹ razão = 1 ⟹ GD/E₂·razão − GD/E₁ = 0 ⟹
ponte ≡ 0, para quaisquer Ke, g, n₁. O bifásico então soma anuidade + anuidade + TV com bases
contínuas e reproduz o `pe --tv book` monofásico — verificado no selftest a 1e-9 e na
contraprova por soma explícita de FCFE em `testes.py` (5 sorteios, 1e-10).

**O rebase do lucro acompanha.** ROE₂ aplica sobre E₂: `NI_{n₁+1} = (1+g₁)^{n₁+1}·(ROE₂/ROE₁)·
razão` na base NI₀ = 1. Nível (o salto) e taxa (g₂) compostos, nunca confundidos — é o teorema
da classificação (§8) operando na transição. A ponte NUNCA entra sozinha num valuation cuja
base de lucro não foi rebasada.

**Limite de validade (MM).** A ponte precifica o fluxo, não o risco. Sob Modigliani-Miller, a
troca de estrutura com Ke reprecificado tem efeito líquido = tax shield; segurar o Ke enquanto a
alavancagem muda transfere para a ponte um valor que é de custo de capital. Por isso o comando
reporta o Ku implícito de cada fase (MM estático: `Ku = (Ke + Kd(1−t)·D/E)/(1+(1−t)·D/E)`) e
alerta gaps > 0,5 p.p. A trilha consistente é a de sempre: Ku único, Ke por fase via `apv`.
Hipóteses herdadas da vF19: transição datada num único ano, dívida a valor de face, Kd = cupom.


## §8c — Iso-valor: inversão fechada da rentabilidade (v9.1)

Sob a convenção `book`, o múltiplo é LINEAR em 1/rentabilidade: M = S(g) + [B(g) − α·g·S(g)]/rent,
com S(g) = (1+g)(1−((1+g)/(1+K))ⁿ)/(K−g) (anuidade) e B(g) = (1+g)ⁿ⁺¹/(1+K)ⁿ (fator do TV);
α = 1−(GD/E−ND/E) no lado equity, α = 1 no lado firm. Logo, para qualquer alvo:

```
rent* = (B − α·g·S)/(alvo − S)
```

— forma fechada, sem solver. A curva iso-valor é a varredura do eixo "duro" (g) com a inversão
fechada do eixo "linear" (rentabilidade). Provada na planilha vF8.1 (aba Iso-Valor): prova por
fluxos explícitos linha a linha (checks = 0) e reconciliação com a aba Logic (o P/L justo dela
como alvo devolve o ROE dela a ~2e-15). Sob `convergencia`/`gordon` a linearidade não vale no TV
e a inversão usa a bissecção do motor, verificada por re-avaliação ponto a ponto. Propriedades da
curva: alvo → S(g) é polo (variável não identificada — ruído); o ramo com rent* < custo na `book`
é raiz CONDICIONADA (a trava do §3 aplicada ponto a ponto): vazia quando o book acompanha o
marginal (conflação), admissível sob tese de saída pelo capital investido quando o book foi
informado — e com sub-alerta próprio se o book também ficar abaixo do custo; RiR = g/rent* > 100%
exige funding declarado por ponto.


### §8c-bis — Inversão com os papéis separados (correção B1 da auditoria v9.1)

A forma `rent* = (B − α·g·S)/(alvo − S)` usa a MESMA variável nos papéis marginal (retenção) e
médio (TV) — a conflação da P6.11. Com o ROE médio contábil rb declarado, o múltiplo continua
linear na rentabilidade MARGINAL: M = S + B/rb − α·g·S/rent, logo

```
rent* = α·g·S / (S + B/rb − alvo)
```

— forma fechada preservada, papéis separados. Identificabilidade: com g·α → 0 (retenção nula), a
marginal sai do múltiplo e NÃO é identificável (só a média, via TV) — o motor sinaliza. A versão
conflacionada permanece disponível (sem rb) com aviso, por fidelidade à planilha vF8.1, que
conflaciona como a Logic historicamente conflacionava.


### §8e — Inversão bifásica exata (v9.3, correção do B2 da auditoria nº 2)

No bifásico book sem fade, o valor por unidade de NI₀ decompõe-se em f1 + f2 + ponte + TV, e
APENAS f2 depende de ROE₂ — linearmente: f2 = K·A₂·(ROE₂ − α₂g₂), com
K = (1+g₁)^(n₁+1)·razão/[(1+g₂)·rb₁·(1+Ke₁)^n₁] e A₂ a anuidade do regime 2. O TV (equity
contábil ao fim do CAP) independe de ROE₂ porque a trajetória de equity ancora em rb₁. Logo:

```
ROE₂* = (alvo − f1 − ponte − TV_desc)/(K·A₂) + α₂·g₂
```

— subtração e divisão; sem solver. A composição por subtração da v9.2 (alvo − ponte, curva
monofásica no resto) foi REMOVIDA: deixava f1, o rebase de nível h = (ROE₂/ROE₁)·razão e o
desconto bifásico dentro do "alvo líquido", produzindo rentabilidades sem sentido no caso
verdadeiro (ROE* de −2% quando o correto era 43,45%). Regra da suíte que nasce daqui: identidade
interna não valida semântica — todo comando de composição exige teste contra caso verdadeiro
EXTERNO (aqui, soma explícita de FCFE ano a ano, na suíte). Limites declarados: convenção book,
sem fade, conflação do rb₁ herdando o contrato do B1 (aviso sem --pt-roe1-book), e ROE₂
resolvido no papel duplo marginal=médio do regime 2 (como a vF19).
