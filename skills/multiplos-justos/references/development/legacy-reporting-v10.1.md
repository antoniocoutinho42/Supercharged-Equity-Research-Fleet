# v10.1: reporting/process rules retained as migration record

> This file is NOT runtime guidance. It preserves the exact v10.1 product/process text that was deliberately simplified or reassigned in Fleet v6. Economic rules were migrated to active modules.

## A entrega é um relatório de research — e um produto de mercado (fluxos 2 e 3)

**Parede processo×produto:** o leitor recebe ACHADOS, nunca infraestrutura — cada escolha
justificada pela razão econômica em uma frase (com o número) ou por fonte externa citável, nunca
pela autoridade da regra. Lista de banimento, tabela de tradução e regime da saída do motor:
`aplicacao.md` §5. **Texto integral desta seção — obrigatório antes de qualquer relatório
completo: `aplicacao.md` §5b** (regra de substituição, quadro pedagógico, as onze escolhas por
extenso, primeira aparição, formato dentro de seção).

**Estrutura fixa, nesta ordem — conclusões na largada:**

1. **Conclusão** (abre o documento): faixa piso–base–teto com veredicto contra o preço de tela
   (data e banda); múltiplos de tela corrente E forward com base declarada; consenso (PT médio,
   nº de analistas) ou lacuna declarada; **4–6 premissas decisivas ABERTAS já aqui**, cada uma com
   número e justificativa própria — **quatro vagas FIXAS, sempre: (i) base de lucro/EBITDA;
   (ii) rentabilidade marginal, com a derivação em uma linha; (iii) g; (iv) custo de capital — e
   quando o beta não for observado na sessão, a vaga (iv) declara isso e carrega a banda em beta,
   porque nesse caso parte da faixa de valor não vem de premissa econômica nenhuma.**
   - **Quadro "como o valor é formado"** (fixo, ≤ meia página, entre Conclusão e Premissas):
     a mecânica em linguagem plana — encargo de reposição (d) → imposto (t) → fração reinvestida
     para crescer (crescimento ÷ retorno do capital novo) → desconto pela margem entre custo de
     capital e crescimento — cada variável com função em UMA linha e o valor do caso; fecha com a
     frase-síntese do múltiplo como cadeia comprimida. Lista de banimento vale dentro do quadro.
2. **Premissas principais**: estimativas próprias × consenso (t, t+1, t+2), desvios justificados
   linha a linha; derivação em prosa com a conta inline (cadeias de §11) e os cinco atributos
   embutidos; **triângulo por cenário** — g = RiR × retorno com dois inputs e um output
   declarados; cenário com RiR silencioso é cenário opaco.
3. **Companhia, números & indústria** (mandato completo em relatório de companhia; dispensado em
   reversa rápida e screening; **NUNCA em delta** — reavaliação roda o mandato completo, sem
   herança): perfil, segmentos e posição competitiva; históricos de 3–5 anos em tabela curta com
   leitura de tendência; guidance × realizado; administração e governança quando materiais;
   competição, share, bull/bear do sell-side (§1); verificações narradas pelos ACHADOS com as
   rubricas de tradução, nunca pelos nomes internos; proveniência de tudo (verificado nesta
   sessão / derivado por regra / hipótese de construção / fornecido e revalidado).
4. **Valuation**: grade canônica (§4) com âncora observável e preço/ação pela ponte explícita;
   **decomposição de Miller-Modigliani, obrigatória em toda grade de cenários** — valor dos ativos
   instalados (lucro operacional após imposto ÷ custo de capital), valor das oportunidades de
   crescimento (EV − ativos instalados) e peso do valor terminal, com a participação de cada um.
   Em `convergencia` e `gordon` o primeiro termo é identidade exata; na `book` com CAP finito NÃO é,
   e sai do motor com `--g 0` (`derivacao.md` §2 e §4). **Condição de validade declarada:** ele só é
   "ativos instalados" se o `d` for encargo de reposição verdadeiro — a contraprova de caixa do
   Gate 0 e esta decomposição são o mesmo argumento. A sensibilidade ao horizonte de vantagem deixa
   de ser opcional quando ±3 anos de CAP movem mais de ~10% do valor. **Peso do terminal acima de
   ~50% ⟹ declare também o viés de mortalidade não modelado:** nenhuma convenção terminal embute
   hazard de extinção, o viés é unidirecional (terminal superestimado) e da ordem de −16% a −27%
   para hazards de 2% a 5% ao ano. O motor emite o alerta.
   Tabela de múltiplos centrada no caso-base reconciliando com a manchete; sensibilidades
   travadas; cross-check por segundo método declarado; **hipótese terminal re-testada aqui** (uma
   linha mesmo quando não muda nada — é onde o erro mais caro é pego); **sensibilidade às ONZE
   escolhas metodológicas** (a base monetária é reportada à parte como invariante de coerência, não
   como 12ª bifurcação econômica) (lista integral e gatilhos: §5b) — alternativa movendo > ~10% ⟹ a
   tabela traz as duas com o custo de cada uma; **coerência interna dos cenários**: caso-base =
   escolha central de todas; produto dos extremos = bear/bull rotulados.
5. **O que está no preço**: menu de reconciliação (§4) COM confronto temporal contra o consenso;
   **nível implícito como ESCADA, com a configuração declarada** — congelada (múltiplo fixo) é
   LIMITE SUPERIOR; recalculada com o vetor travado, em que só o encargo de reposição responde ao
   nível, é a leitura CENTRAL e sai do motor; e recalculada com a rentabilidade também derivada do
   nível (intensidade de capital constante) é o PISO da escada, montada célula a célula. Quanto mais
   variáveis respondem ao nível, menor o nível exigido — declare qual configuração está reportando.
   A propriedade de teto vale quando a D&A absoluta não escala com o nível (margem ou preço); se o
   nível vem de VOLUME, a D&A escala e as leituras convergem. **A leitura recalculada é, por
   identidade, o break-even da base de lucro** — não a calcule duas vezes; **decomposição do gap contra o preço-alvo do consenso** — a
   mesma reversa com alvo no preço-alvo médio, dizendo em qual premissa mora a diferença (ou a
   lacuna declarada quando não houver cobertura); **custo de capital implícito SEMPRE** (beta
   implícito contra a banda observada, na MESMA unidade da sensibilidade — beta, não pontos-base); fronteiras
   bivariadas depois dos univariados; fecha com o julgamento comparativo — qual reconciliação
   exige a menor violência às âncoras observáveis, e qual observável a testaria. Perto da
   neutralidade a variável implícita é ruído com cara de precisão — reporte a curvatura.
6. **Riscos + veredicto**: 4–6 que movem a tese, cada um com o observável que o monitora;
   **break-even das quatro premissas fixas** — rentabilidade marginal, g e custo de capital saem de
   `rev --resolver`; a base de lucro sai de `nivel` na leitura recalculada, e é o MESMO número do
   nível implícito (não o calcule duas vezes). Reporte o valor de break-even e a distância até o
   adotado;
   premissa cujo break-even cai DENTRO da banda de sensibilidade já declarada ⟹ o veredicto é
   frágil naquele eixo e a entrega diz isso; alavanca dominante; o que a fórmula não captura; a
   premissa cuja inversão vira a conclusão.
7. **Visão não-consensual** (obrigatória, ≤ 15 linhas): só com fatos já citados e cadeia factual
   explícita; sem nenhuma, declare "sem visão não-consensual nesta rodada" — não invente.
8. **Metodologia, limitações e disclaimer**: parágrafo citável em linguagem plana referenciando o
   quadro de abertura; quadro de premissas em uma linha cada; disclaimer específico ao caso,
   nunca genérico (pocket valuation e não DCF nem DD; o que não captura; premissas de
   estabilidade e quais o caso viola; direção do erro de cada premissa congelada).

**Duas camadas no entregável (v10.1).** O **corpo do memo** carrega as seções 1, 2, 3, 5, 6, 7 e 8 —
é o que sustenta o raciocínio em prosa e o que o critério de aceitação (ii) testa. O **anexo
analítico** carrega as grades que provam o raciocínio: tabela de múltiplos justos, sensibilidades às
onze escolhas, grade do driver dominante, break-even e fronteiras bivariadas — cada uma com a frase
de leitura que a acompanha no corpo. Nada é cortado; o que muda é onde mora. Regra da divisão: fica
no corpo o que o leitor precisa para SEGUIR o argumento; vai ao anexo o que ele precisa para
CRITICAR. A trava de encerramento continua valendo — faltando espaço, corte prosa do veredicto e do
disclaimer, nunca premissas, memória de cálculo ou memória técnica.

**Memória técnica = segundo artefato**, sempre fora do relatório (rotulada "uso interno"; a
versão da skill vai nela, nunca no título do relatório). Captura de aprendizado e oferta de
aprofundamento são chat-only.

**Critérios de aceitação, antes de enviar:** (i) leitor frio refaz a análise inteira só com o
texto — número sem a conta = incompleto; (ii) só a prosa sustenta o raciocínio da conclusão ao
detalhe; (iii) zero termos da lista de banimento no corpo (busca literal antes de entregar);
(iv) as quatro premissas fixas na Conclusão, com número e derivação; (v) toda variável usada tem
a FUNÇÃO explicada na primeira aparição; (vii) a decomposição de Miller-Modigliani está reportada —
ativos instalados, crescimento e peso do terminal — e o `d` que a produz passou pela contraprova de
caixa, ou o gap entre as rotas está declarado; (viii) o `aplicacao.md` §5b foi lido nesta rodada;
(vi) todo alerta emitido pelo motor nas rodadas que
sustentam o caso-base foi lido na ÍNTEGRA e ou incorporado como premissa, ou declarado com a razão
de não o ter sido — rodada com saída filtrada por campo não conta como rodada.

**Trava de encerramento:** cobertura incompleta não oferece aprofundamento; faltando espaço,
corte prosa do veredicto e do disclaimer — nunca premissas, memória de cálculo ou memória técnica.

## Referências

**Regra de manutenção (v9.28):** histórico de versões vive SÓ no `CHANGELOG.md` — o corpo cita a
versão corrente e nada mais; marcador de versão em regra do corpo só quando distinguir o
comportamento novo do antigo for operacionalmente necessário. A prosa integral da seção de
entrega vive em `aplicacao.md` §5b; o corpo mantém o esqueleto.

- `references/aplicacao.md` — playbook de empresa real, em duas camadas de leitura.
  **NÚCLEO, leitura integral em toda rodada:** pesquisa §1, regras travadas §2, convenção §3,
  cenários e confronto temporal §4, escrita §5 e entrega §5b (a autoridade estrutural), bloco de
  inputs §6, status das premissas §10, memória de cálculo §11 — incluindo **§11.1c** (RiR por perna
  de capital), **§11.7** (decomposição de Miller-Modigliani) e **§11.8** (confronto com o caixa
  operacional publicado).
  **MÓDULOS, abertos pelo gate que os dispara:** multi-driver §7 (Gate 2), degrau §8, ponte §8b e
  capacidade §8f (Gate 3), financeiras §9 (Gate 0.5), multi-segmento §12 (teste de materialidade),
  fronteira de escopo e marca de estoque §13 (Gate 0). Apêndice J é consulta, não leitura corrida.
- `references/derivacao.md` — matemática, provas, as três convenções de TV §3, APV/recursão Ke_t
  (agora executável no comando `apv`) §5, mortalidade não modelada §5b, limites, §8 teorema da classificação, §8b ponte de
  releveraging (derivação, prova do colapso, limite MM). Leia se a teoria for questionada ou
  houver degrau ou mudança de estrutura de capital.
- `scripts/testes.py` — validação independente: property tests, reconciliação DCF↔EVA e APV,
  boundaries. Rode se alterar o motor ou se um resultado parecer estranho.
- `references/paper-multiplos-justos-v3.md` — fundamentação teórica completa: quinze proposições (6.1–6.15)
  com status epistemológico declarado, três convenções de TV (§3.3), por que não há fade (§3.4),
  as duas camadas de consistência do custo de capital (§4), protocolo de validação (Ap. A),
  condições de falseamento (Ap. B) e caso trabalhado de ponta a ponta (Ap. C). Leia quando a
  teoria for questionada ou quando precisar defender uma escolha de convenção por escrito.

- `references/manutencao.md` — manual de adição de conhecimento: como uma regra nova entra no
  pacote sem virar conselho, duplicata ou seção órfã. Leia ANTES de editar qualquer arquivo desta
  skill; não é lido durante valuation.

**Excel, quando gerar:** fonte Gadugi, azul = input hardcoded, preto = fórmula, verde = referência
cruzada, subtotais "(=)" em negrito, aba "Premissas" com as seis colunas. PT-BR, tom direto.

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
| delator de contração | o reinvestimento observado veio de um período de queda de receita e por isso não mede o custo de crescer |
| decomposição de Miller-Modigliani / piso sem crescimento | de onde vem o valor: o lucro que já existe, o crescimento, e o que acontece depois do horizonte |
| break-even por premissa | quanto cada premissa precisa mudar para o veredicto virar |
| contraprova de caixa do `d` | o encargo de reposição medido por duas rotas — depreciação contábil e capex de manutenção declarado |
| viés de mortalidade | o valor terminal não desconta a probabilidade de a companhia deixar de existir — o erro é sempre para mais |
| corpo × anexo analítico | o que o leitor precisa para seguir o argumento × o que ele precisa para criticá-lo |
| confronto com o caixa operacional | a base de lucro montada conferida contra o caixa que a companhia publica |

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

**Decomposição do g e RiR por perna** — regra de DERIVAÇÃO, mora no §2 e é executada pela cadeia
§11.1c; aqui fica apenas a tradução dela para o relatório (tabela acima).

**RiR por componente (v9.22).** A conservação de capital já contém a soma — a regra apenas a
abre: `RiR × NOPAT = capex_fixo_de_crescimento + ΔWC ⟹ RiR = RiR_fixo + RiR_wk`. O preço do
crescimento é um vetor, e a pergunta correta é *quais componentes o crescimento dos próximos T
anos de fato consome*. Com capacidade pré-construída (gatilho no Gate 3), o crescimento até a
plena consome só giro — RiR agregado cobraria capex fixo que não será incorrido (dupla cobrança,
valor subestimado — jurisprudência J15). Tratamento completo em §8f. Corolário epistêmico: ROIC
que sai como resíduo do triângulo (g e RiR inputs) é aritmética, não evidência — sem a validação
por unit economics do §11.2 ou fonte independente, a entrega declara "rentabilidade marginal
derivada por resíduo, não validada".

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
substituição, quadro pedagógico, as onze escolhas metodológicas por extenso, primeira aparição e formato
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
   explícita; **decomposição de Miller-Modigliani obrigatória em toda grade** — ativos instalados
   (lucro operacional após imposto ÷ custo de capital), valor do crescimento e peso do terminal,
   com a condição de validade declarada (§11.7), a sensibilidade ao horizonte quando ±3 anos de
   CAP moverem > ~10% e a **declaração do viés de mortalidade quando o terminal passar de ~50%**; tabela de múltiplos justos centrada no caso-base com a base declarada (a
   célula central reconcilia com a manchete); sensibilidades travadas (custo de capital, gp, degrau);
   grade de sensibilidade ao driver quando a elasticidade do dominante ≥ 0,5 (§7). Cross-check
   por segundo método declarado (múltiplo de saída sobre t+2, ou soma das partes no híbrido).
   **A hipótese de valor terminal é re-testada aqui**, agora que a rentabilidade marginal existe
   — uma linha mesmo quando não muda nada; é onde o erro mais caro é pego.
   **Sensibilidade às escolhas metodológicas** (nome externo da dupla entrega; interno segue
   "bifurcações"): as ONZE — base do lucro (reportada × normalizada); alavanca de lucro
   (modelada com probabilidade × absorvida/excluída como opcionalidade); rentabilidade (marginal
   × forward de consenso); g (reinvestimento × guidance/consenso); hipótese terminal; regime do
   driver no terminal (congelado × acompanha inflação); **caixa/excedente em híbrida
   financeira** (zero central × bruto — v9.16, regra em §9); **o PONTO DO CICLO dos inputs de capital**
   (corrente × média da série de três pontos × guidance de longo prazo — capex, giro e base de
   ativos, §1), com o RiR re-derivado pela conservação em CADA ramo — nunca com o triângulo
   congelado; e **(v9.20) a
   fronteira de consolidação quando minoritários/coinvestimento > ~20% do PL** (fatia de
   terceiros no EV pelo valor contábil × econômico estimado — ignorá-la não é ramo, é erro;
   gatilho em `aplicacao.md` §2); e **(v9.22) a leitura de capacidade quando o gatilho da
   capacidade pré-construída dispara** (ramo corrente: ociosidade ignorada, RiR pleno, d
   contábil × ramo capacidade: RiR por componente, fases do §8f, d do estado estacionário da
   capacidade) — o ramo capacidade só é caso-base com observável direto de utilização OU
   contraprova de receita-por-ativo contra pares a plena fechando dentro de ±15%; derivado só
   do protocolo físico sem contraprova, é sensibilidade identificada, nunca base em silêncio; e
   **o NÍVEL da marca de estoque quando ela responde por > ~20% do valor** (marca de AVALIAÇÃO —
   laudo, NAV, cap rate — × marca de TRANSAÇÃO realizada, esta com a dispersão das operações
   exibida, porque média de transações dispersas não é marca, é média; gatilho e teste da
   identidade em §13). A ROTA (a)/(b) da parede estoque↔fluxo NÃO entra nesta lista: é invariante
   de coerência, ao lado da base monetária.
   **Base monetária não entra nessas onze escolhas:** é reportada separadamente como invariante de
   coerência (nominal ou real), com g/gp/rentabilidade/custo de capital reconciliados na mesma base.
   Escolha alternativa movendo > ~10%
   ⟹ a tabela traz as duas, com o custo de cada uma e a escolha central justificada pela razão.
   **Coerência interna dos cenários** (nome externo da guarda anti-empilhamento): o caso-base
   usa a escolha CENTRAL de todas; o produto dos extremos conservadores É o bear (rotulado), o
   dos otimistas, o bull — escolher o ramo conservador de tudo no caso-base não é prudência, é
   cenário incoerente.
5. **O que está no preço**: o menu de reconciliação (§4) — nível implícito COM o confronto
   temporal contra o consenso e **como ESCADA com a configuração declarada** (congelada = limite
   superior; vetor travado = central, do motor; rentabilidade derivada = piso — §4), horizonte implícito, crescimento sem consumo
   de capital implícito **lido com o qualificador condicional ao g** (§4), decomposição do gap
   contra o preço-alvo do consenso, curva iso quando houver dois vetores, e **custo de capital
   implícito SEMPRE**
   (beta implícito contra a banda observada do beta — a explicação mais barata de esquecer).
   Fronteiras bivariadas plausíveis depois dos univariados, com a dualidade dos eixos de
   denominador declarada quando existir; **a seção fecha com o julgamento comparativo: qual
   reconciliação exige a menor violência às âncoras observáveis, e qual observável a testaria.**
   Perto da neutralidade a variável implícita é ruído com cara de precisão — reporte a
   curvatura. É a seção onde a abordagem é insubstituível — recebe o espaço.
6. **Riscos + veredicto**: os 4–6 que movem a tese, cada um com o observável que o monitoraria;
   **break-even das quatro premissas fixas** (§4), com a declaração explícita dos eixos em que o
   veredicto é frágil; fecha com alavanca dominante, o que a fórmula não captura, e a premissa cuja
   inversão viraria a conclusão.
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
quadro e das primeiras aparições — variável usada sem função explicada = entrega incompleta;
(vi) todo alerta emitido pelo motor nas rodadas que sustentam o caso-base foi lido na ÍNTEGRA e ou
incorporado como premissa, ou declarado com a razão de não o ter sido. Rodada com saída filtrada
por campo não conta como rodada: alerta que não é lido é achado que não atravessa a parede;
(vii) a decomposição de Miller-Modigliani está reportada — ativos instalados, crescimento e peso do
terminal — e o `d` que a produz passou pela contraprova de caixa, ou o gap entre as rotas está
declarado; (viii) esta seção §5b foi lida nesta rodada, antes de a primeira linha do relatório ser
escrita.

**Trava de encerramento:** não ofereça aprofundamento com a cobertura incompleta. Faltando
espaço, corte prosa do veredicto e do disclaimer — nunca as premissas, a memória de cálculo ou a
memória técnica.
