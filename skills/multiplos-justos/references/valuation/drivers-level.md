# Drivers exógenos e nível

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

**O capital também tem nível — nota declaratória com gatilho de materialidade (v10).** O
`normaliza` re-baseia a métrica e o `d`; ele **não** toca o capital. Mas as pernas de giro indexadas
ao driver acompanham o nível: estoque ao custo de reposição do insumo, recebíveis e adiantamentos ao
preço de venda, fornecedores ao custo de compra. O capital FIXO **não** re-baseia — o parque não muda
de tamanho porque a commodity subiu, e é exatamente isso que a armadilha do ROIC de pico descreve
(numerador dispara, denominador é book histórico). Consequência: normalizar o numerador e deixar o
giro no nível velho mede rentabilidade em dois pontos do ciclo. **Direção do erro, sistemática:** no
TOPO, EBITDA cai na normalização enquanto o giro observado está inflado — a rentabilidade normalizada
sai duplamente deprimida e o valor subestimado; no FUNDO, o inverso. **Gatilho de materialidade:**
recalcule as pernas indexadas quando o estoque indexado ao driver passar de ~10% da receita; abaixo
disso, declare a direção do erro e siga. Na maioria dos casos o efeito é de um a dois por cento do
capital investido — o que justifica declarar sempre e recalcular só acima do gatilho.

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
