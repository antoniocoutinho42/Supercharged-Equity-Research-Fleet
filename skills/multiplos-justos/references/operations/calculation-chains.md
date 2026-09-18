# Cadeias de cálculo obrigatórias quando aplicáveis

## 11. Memória de cálculo — cadeias obrigatórias (templates)

Regra: premissa derivada nunca aparece só como número. Mostre a cadeia com os valores de cada
etapa e a fonte de cada insumo. Os templates abaixo são o mínimo; adapte os rótulos ao caso.

**Critério de aceitação:** o leitor refaz a conta sem perguntar nada. Se ele precisa perguntar
"de onde veio esse número?", a memória está incompleta.

### 11.1 Rentabilidade marginal (a mais cobrada — nunca pule)

```
Δreceita na janela do deployment  ±X%  (>= 12 meses; se <= 0, esta cadeia é INVÁLIDA — vá para 11.1c)
ΔWC na MESMA janela ............. ±Y    (ΔWC/Δreceita deve ficar perto de WC/receita, em razão E sinal)
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

### 11.1b Conservação de capital (obrigatória em TODA valuation de companhia real)

**Necessária, não suficiente.** A identidade testa o PAR: mover capital de `d` para `RiR` mantém a
soma e a identidade fecha com as duas metades erradas — falso positivo por compensação, o mesmo
mecanismo que o corolário da base de lucro do §13 descreve. Por isso ela vem acompanhada, e nunca
substituída, pela contraprova de caixa do `d` (§2) e pela decomposição por perna (§11.1c). Os casos
antes citados como gatilho — `d` ≠ D&A contábil, D&A > capex — deixam de ser condição de acionamento
e passam a ser os dois regimes que mais frequentemente a fazem falhar.

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

### 11.1c RiR por perna de capital — giro × fixo (obrigatória em toda projeção nominal)

Executa a decomposição do §2. Configuração declarada: `g` e a intensidade de capital são as entradas,
a rentabilidade marginal é derivada do ciclo de caixa, e **o RiR é OUTPUT**.

```
Capital de giro operacional (recebíveis + estoques − fornecedores − adiantamentos) .... WC
(÷) receita do mesmo período .......................................................... k_wk
     série de 3 pontos (§1): ...% / ...% / ...%   — declare o centro e por quê
Ciclo de caixa = PMR + PME − PMP − prazo de adiantamentos ............................. ... dias
     ciclo POSITIVO ⟹ inflação de preço CONSOME giro; NEGATIVO ⟹ gera caixa (§2, item vi)
Capital fixo (imobilizado + intangível + direito de uso) ÷ receita .................... k_fixo
     valor contábil líquido SUBESTIMA o custo de repor capacidade — declare o viés e a direção
(=) Confronto: WC + fixo vs capital investido reportado pela companhia ................ gap ...%

Decomposição do g:   g = g_volume + g_preço      (g_preço = inflação × repasse + preço real)
(=) k_marginal = (g_volume × (k_fixo + k_wk) + g_preço × k_wk) / g .................... ...%
(=) ROIC marginal = margem NOPAT ÷ k_marginal ........................................ ...%
(=) RiR = g / ROIC  [OUTPUT] ......................................................... ...%

Três confrontos obrigatórios, os três exibidos:
 1. conservação (§11.1b): d×EBITDA + RiR×NOPAT = capex_total + ΔWC ......... gap ...%
 2. capex implícito em estado estacionário vs capex observado .............. gap ...%
 3. rentabilidade contábil divulgada pela companhia vs marginal derivada ... leitura
```

**Guarda de coerência com o `d`:** a intensidade fixa usada aqui e o encargo de reposição do §2 têm
de estar na mesma moeda. `k_fixo` a valor contábil líquido com `d` de D&A histórica é internamente
coerente e conservador na rentabilidade; `k_fixo` a custo de reposição exige `d` na mesma base.
Misturar as duas é o quadrante proibido de sempre, por outra porta.

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

### 11.7 Decomposição de Miller-Modigliani — ativos instalados, crescimento e terminal (obrigatória)

A decomposição clássica de Miller-Modigliani (1961) separa o valor entre o que os ativos já
instalados sustentam e o que depende de crescimento futuro — é a mesma partição que o paper §2.1
usa, com a regularidade empírica de que o valor de estado estacionário representou em média dois
terços do preço do S&P 500 entre 1961 e 2025. Aqui ela vira saída obrigatória, por uma razão
operacional: **o primeiro termo não depende de g, de rentabilidade, de horizonte nem da hipótese
terminal — depende SÓ do encargo de reposição e da alíquota.** Toda a incerteza sobre a
classificação da depreciação desemboca nele, e em nenhum outro lugar do valuation.

O `ev` devolve o bloco `decomposicao_mm` pronto (v10.1) — em múltiplos de NOPAT sempre, e em moeda
quando `--ebitda` for informado. Não calcule à mão; a cadeia abaixo é a leitura do que sai.

```
EBITDA-base .................... E    (declare qual: reportado | normalizado | com degrau)
(−) Encargo de reposição d×E ... A    (contraprova de caixa do §2 anexada)
(×) (1 − t) .................... NOPAT
(=) ATIVOS INSTALADOS = NOPAT/W  ...  [identidade exata em `convergencia` e em `gordon` com gp=0]
                                      [na `book` com CAP finito NÃO vale: rode `ev --g 0`]
(+) caixa líquido ÷ ações ...... valor por ação dos ativos instalados
EV do caso-base ................ V
(=) Valor do crescimento ....... V − NOPAT/W        (=) participação: (V − NOPAT/W)/V
(=) Peso do valor terminal ..... VP(TV) ÷ V
```

**Condição de validade, declarada junto com o número:** `NOPAT/W` só é "valor dos ativos instalados"
se o `d` for encargo de reposição VERDADEIRO — isto é, se a reposição mantiver o lucro indefinidamente
sem capital novo. Com `d` subdimensionado, o NOPAT está superestimado e o termo inteiro herda o erro
(paper §6.9, in fine). É por isso que esta cadeia e a contraprova de caixa do §2 são um argumento só.

**Peso do terminal acima de ~50% ⟹ declare o viés de mortalidade (v10.1).** Nenhuma das três
convenções terminais embute hazard de extinção da companhia. O viés é **unidirecional** — terminal
superestimado — e a ordem de grandeza é **−16% a −27% para hazards de 2% a 5% ao ano** (paper §3.2 e
§7). Não existe correção dentro do motor; existe declaração com direção e magnitude, e ela vale
exatamente quando o terminal domina. O motor emite o alerta quando o peso passa de 50%.

**Leitura obrigatória, em uma frase:** participação alta dos ativos instalados ⟹ a tese se decide
pelo NÍVEL de lucro e pelo encargo de reposição, não pelo vetor de crescimento, e é ali que a
diligência deve ir. Participação alta do terminal ⟹ a tese se decide pela DURAÇÃO da vantagem, e a
sensibilidade ao horizonte deixa de ser opcional **quando ±3 anos de CAP movem mais de ~10% do
valor** — gatilho medido, não arbitrado por participação.

### 11.8 Confronto com o caixa operacional publicado (obrigatória)

Todas as cadeias acima partem de peças montadas pelo analista — EBITDA, D&A, capex, giro. Esta as
confronta contra o único número que a companhia publica sem intermediação: o caixa líquido gerado
nas atividades operacionais.

```
EBITDA da base adotada .......................... E
(−) itens não-caixa devolvidos ao EBITDA ajustado  ...  (provisões, o que o "ajustado" removeu)
(−) ΔWC operacional do período ................... ...  (mesma janela)
(−) juros pagos .................................. ...  (fonte: DFC)
(−) IR e CSLL pagos .............................. ...  (fonte: DFC)
(=) caixa operacional RECONSTRUÍDO ............... ...
     vs caixa líquido das atividades operacionais PUBLICADO ....... gap ...%
```

**Não é identidade, e dizer isso é parte da regra.** A classificação de juros e de imposto entre
atividades operacionais e de financiamento varia por norma e por companhia; itens como litígios,
antecipação de recebíveis e efeitos de descontinuados entram em um lado só. O que a cadeia entrega é
o **gap e o que ele contém** — não um teste de aprovação. Razão econômica: é o teste de qualidade de
lucro mais barato disponível, e sem ele lucro sustentado por capitalização agressiva, provisões ou
receita não realizada atravessa todos os demais gates sem produzir sintoma. **Gap > ~10% sem
explicação nominada ⟹ a base de lucro é hipótese, não medição**, e isso vai à Conclusão junto com a
premissa fixa (i).
