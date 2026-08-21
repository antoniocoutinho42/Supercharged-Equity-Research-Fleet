# Equity Research Fleet v4.0.0 — Desenho da Arquitetura

Data: 2026-08-21 · Origem: `/grill-me` de redesenho (23 decisões + 2 emendas, registradas na Seção 15)
Base factual: plugin `equity-research-fleet` v3.0.0 e skill `multiplos-justos` v9.24, lidos na íntegra.
Uso: **fonte de verdade** deste trabalho. Conflito entre este documento e qualquer outro resolve-se por
este documento.

---

## 0. Objetivo

Transformar o Fleet de um sistema que coleta dados predefinidos, alimenta um valuation predefinido e
gera um relatório predefinido em **um analista de equity research autônomo e thesis-driven**: descobre
as poucas perguntas que determinam a tese, pesquisa livremente a melhor evidência onde ela estiver,
entende quanto a companhia pode crescer, se o moat sustenta esse crescimento e qual o retorno do
capital incremental — e converte tudo num valuation rigoroso, auditável e interativo.

A metodologia de valuation passa a ser a skill **`multiplos-justos` v9.24**, tratada como fonte
canônica congelada. O motor K3 / Justified P/E é removido integralmente.

## 1. Princípios da v4

1. **Determinístico onde precisa ser; autônomo onde julgamento vale.** Matemática, proveniência,
   reconciliação, renderização, testes e QC são determinísticos. Pesquisa, seleção de fontes,
   formulação das perguntas da tese, profundidade, escolha de exibição e interpretação são autônomos.
2. **O múltiplo é output da economia do negócio**, nunca premissa arbitrária. A metodologia inteira da
   `multiplos-justos` entra — não uma fórmula extraída dela.
3. **Sem herança, em hipótese alguma.** Nenhuma premissa, tese, pergunta, conclusão ou valuation
   anterior é carregado automaticamente. Cada execução re-deriva tudo do zero.
4. **A melhor fonte para o fato específico**, não uma hierarquia universal. Liberdade de fonte com
   contrato de proveniência mais duro do que a restrição que ela substitui.
5. **Estrutura metodológica sim, template editorial não.** A sequência da `multiplos-justos` disciplina
   o argumento de valor; o miolo analítico se organiza pelas perguntas que definem a tese.
6. **Insight antes de formato.** Nenhuma lista fixa de gráficos ou de capítulos. A escolha semântica é
   do Analista; o renderer permanece determinístico e rastreável ao dado.
7. **O Analista decide e justifica; não terceiriza.** Escolhas sem default (convenção terminal, regime
   contábil, política de caixa, leitura de capacidade, earning power) são decididas, justificadas pela
   razão econômica e têm o custo da alternativa exibido — nunca viram pergunta ao usuário.
8. **Fronteira honesta em vez de falsa precisão.** Onde a arquitetura correta está fora do escopo da
   metodologia, o Fleet declara e entrega o que continua íntegro, sem fabricar fair value.

## 2. O que sai, o que entra, o que se adapta

**Removido (só no histórico git; remoção executada apenas na Seção 17, item 10):**

- Motor K3 / Justified P/E V2.2.1 inteiro: `valuation_engine.py`, `input_validator.py`,
  `run_regressions.py`, `K3_Regression_Tests_v2.2.1.json`, `Justified_PE_AI_Manual_v2.2.1.md`,
  `assets/k3_engine.js`, skill `er-motor-k3`, `manifest_copia.json`.
- Os 16 canonical inputs como contrato de calibração.
- Skill `er-dados-openbb` e a exclusividade OpenBB.
- Memória durável: `analises/_memoria/`, `scripts/memoria.py`, notas por ticker, estado persistente de
  qualquer natureza, P2 por materialidade, gatilho "pergunta sobre ticker já analisado".
- Cache de dados entre execuções.
- Lista fixa de 6 gráficos obrigatórios e a ordem fixa de 8 seções da aba 2.
- Modo "somente valuation" como nível de esforço.
- Hurdle como quarto cenário.

**Entra:**

- Vendor congelado `skills/er-multiplos-justos/` (cópia read-only da skill v9.24 + manifest de hashes).
- Skill `er-valuation` (wrapper de orquestração), `er-evidencia` (doutrina de pesquisa e proveniência),
  agente `pesquisa-evidencia` (tipo único, N instâncias paralelas).
- Espelho JS do núcleo da `multiplos-justos` com teste de paridade e falha fechada.
- Relatório de **3 abas** (Tese · Valuation · Evidência) com laboratório interativo.
- Gramática de gráficos insight-first + módulo SVG próprio para famílias não-cartesianas.
- QC em **três níveis** (HARD FAIL · REQUIRED DISCLOSURE · QUALITY WARNING).
- Workspace por execução com trava de raiz única.
- Fixture sintética offline no CI, incluindo caso que deve falhar.

**Adaptado:** `er-analise` (quatro marcos adaptativos, autônomo por default) · ledger (agnóstico de
fonte, hierarquia por claim) · `er-relatorio` (builder de 3 abas) · intake (mínimo) · CI e release.

**Permanece intacto em espírito:** QC por código e não por agente · builder determinístico como único
caminho de emissão · todo número em prosa resolvido por placeholder auditável · paridade Python↔JS com
recusa de emissão · manifest de hashes · HTML autocontido, zero rede · separação Analista julga ×
subagente coleta · gaps MATERIAL / NÃO-MATERIAL · resposta do usuário é evidência, nunca fato ·
marketplace-first com fallback de ZIP.

## 3. Componentes

### 3.1 Camadas

```
vendor congelado (multiplos-justos v9.24, read-only, hash + suíte)
   └─> er-valuation      (wrapper: contrato do caso, rotas, cenários, ponte, reversa, sensibilidades)
         └─> er-analise  (processo, julgamento, autonomia)
               └─> er-relatorio (builder de 3 abas + QC de 3 níveis)
er-evidencia  (transversal: doutrina de pesquisa, schema do ledger, reconciliação)
agente pesquisa-evidencia (tipo único, instanciado N vezes com mandatos distintos)
```

### 3.2 Skills (5)

| Skill | Papel | Regra dura |
|---|---|---|
| `er-multiplos-justos` | Vendor congelado: `SKILL.md`, `aplicacao.md`, `derivacao.md`, `paper-*.md`, `scripts/justos.py`, `scripts/testes.py` + manifest de hashes | **Índice, não paráfrase.** Diz o que existe, onde está, qual hash e quando ler cada arquivo. Zero reprodução de metodologia. Read-only: alteração local quebra a suíte |
| `er-valuation` | Wrapper de orquestração | Chama o motor; **nunca reimplementa conta**. Dono do contrato do caso, das rotas, da composição de cenários, da ponte para preço, da reversa e das sensibilidades |
| `er-evidencia` | Doutrina de pesquisa e proveniência | Agnóstica de fonte. Dona do schema do ledger, da hierarquia por claim, da reconciliação e da classificação de gaps |
| `er-analise` | Workflow master | Quatro marcos, autonomia por default, política de interrupção, regras invioláveis |
| `er-relatorio` | Builder determinístico + QC | Único caminho de emissão. Não interpreta prosa, não busca dado, aceita **uma** raiz de execução |

### 3.3 Agente (1 tipo)

`pesquisa-evidencia`: encontra e estrutura evidência com proveniência; **não interpreta, não calibra,
não escreve análise**. A especialização mora no mandato da execução (filings, RI e transcripts,
setorial e competição, macro e drivers, pares), nunca na arquitetura. Instanciável várias vezes em
paralelo. O Analista também pesquisa livremente — para preencher gaps, testar hipóteses, buscar
evidência contraditória e aprofundar achados —, preservada a separação conceitual: **Pesquisa &
Evidência encontra; Analista interpreta e calibra.**

### 3.4 Skill standalone do usuário

`multiplos-justos` permanece **intocada** fora do repositório e continua acionável só por
`/multiplos-justos`. Dentro do Fleet ela é biblioteca, não skill acionável: o gatilho é do
`er-analise`. As duas coexistem sem conflito. Evolução da metodologia é decisão humana explícita,
replicada manualmente e verificada por hash — mesma disciplina que funcionou na v3.

## 4. A metodologia

### 4.1 O que o vendor traz

Identidade central `g = RiR × ROIC` ⟹ `FCFF = NOPAT × (1 − g/ROIC)`; ponte
`EV/EBITDA = EV/NOPAT × (1−d)(1−t)`; lado equity com `FCFE` e caixa/E.

**Cinco gates antes de qualquer conta**, todos obrigatórios e todos declarados na entrega:

| Gate | Decide |
|---|---|
| **0** — capital econômico e qualidade dos inputs | Investimento despesado × capitalizado; teorema da base coerente (regimes A × B); qualidade do book; fronteira EV/EBITDA; natureza do `d`; conservação `capex+ΔWC = d×EBITDA + RiR×NOPAT`; coerência do vetor por quatro identidades |
| **0.5** — fase da companhia | Investimento / distribuição / mista / híbrida financeira. Fase mal classificada é o erro upstream de todos os outros |
| **1** — convenção terminal | `book` × `convergencia` × `gordon`. **Sem default — o motor recusa rodar.** Escolha pela duração econômica do claim, revalidada na entrega |
| **2** — nível: defasagem | Registro de drivers com elasticidade **derivada e com sinal**; gate dispara por `\|elasticidade × gap\|`, não por gap |
| **3** — nível: degrau e capacidade | Capacidade ociosa de balanço (entra como rentabilidade × h) e capacidade pré-construída em rampa (RiR por componente) |

**Dez escolhas metodológicas nomeadas** com o custo de cada uma, e a guarda de coerência interna: o
caso-base usa a escolha central de todas; o produto dos extremos conservadores **é** o bear.

### 4.2 O que o wrapper faz — e o que ele nunca faz

Faz: contrato estruturado do caso; composição de cenários; seleção e declaração de rota; ponte para
preço; composição de SOTP por segmento e por safra de capital; costura multifásica; execução da
reversa por eixo; geração de sensibilidades; coleta e normalização dos diagnósticos que o motor emite.

Nunca faz: qualquer aritmética de valuation fora do motor; qualquer ajuste "conservador" a um output;
qualquer default para uma escolha que a metodologia declara sem default.

### 4.3 Rotas nativas

Nativas por composição do motor: firm-side (`ev`), equity-side (`pe`), rampa bifásica (`rampa`), degrau
(`degrau`), ponte de releveraging (`ponte`), reversa (`rev`), curva iso (`iso`), normalização de nível
(`normaliza`), registro de drivers (`drivers`), nível implícito (`nivel`), consistência Ke↔WACC
(`kewacc`, `apv`), **SOTP por segmento e por safra de capital**, **financeiras equity-side**
(P/VP = P/L × ROE), **holdings** (soma das partes com desconto de holding como escolha nomeada e
precificada).

## 5. Processo — quatro marcos

Marcos com saída verificável; **adaptativo dentro de cada um**; atravessados autonomamente.

| Marco | Saída verificável |
|---|---|
| **M1 — Escopo** | Identificação da companhia; moeda e regime declarados; documentos fornecidos classificados (evidência × quarentena); data-base se explicitada |
| **M2 — Perguntas da tese** | 3–5 perguntas formuladas, cada uma com observável de falsificação e lista de variáveis/mecanismos ligados. **Gate interno de qualidade, não checkpoint de aprovação** |
| **M3 — Pesquisa e derivação** | Ledger completo; cinco gates fechados e declarados; premissas derivadas com cadeia de conta explícita; escolhas metodológicas decididas e justificadas |
| **M4 — Valuation e entrega** | Caso montado; suíte PASS; valuation + reversa + sensibilidades; confronto com relatório anterior se fornecido; relatório emitido com QC verde |

**Política de interrupção.** O Fleet interrompe o usuário **apenas** quando: (i) há gap MATERIAL que
impede conclusão responsável; (ii) há ambiguidade de escopo genuinamente irredutível; (iii) o usuário
pediu explicitamente modo colaborativo. Fora disso o Analista decide — inclusive convenção terminal,
regime contábil, política de caixa, leitura de capacidade e earning power — justificando em uma frase
econômica e exibindo o custo da alternativa no painel de escolhas.

**Dois produtos, não dois níveis de esforço:**

- **Análise** — fluxo completo: tese + valuation + relatório de 3 abas.
- **Leitura de preço** — o fluxo de engenharia reversa da metodologia: o que o preço embute, menu de
  reconciliação, custo de capital implícito, nível implícito, com o escopo declarado ("cobertura e
  encerramento não se aplicam"). Entrega reduzida à aba Valuation.

Na dúvida entre os dois, **Análise**.

## 6. Pesquisa e proveniência

### 6.1 Princípio da fonte

**A fonte mais autoritativa e mais próxima do fato específico que está sendo provado** — não uma
hierarquia universal. Exemplos que a doutrina traz explicitamente: receita histórica → filing;
guidance → companhia/RI; market share → research setorial especializado pode superar o filing; tamanho
de mercado → fonte setorial independente pode superar a companhia; ação de concorrente → filing do
concorrente; expectativa de mercado → consenso/provider.

Fontes admissíveis: filings, RI, releases, transcripts, apresentações, reguladores, APIs e conectores
MCP (OpenBB, SEC, provedores de mercado), industry reports, fontes governamentais, imprensa
especializada, web, e documentos fornecidos pelo usuário. **Nenhuma é obrigatória; nenhuma é exclusiva.**

### 6.2 Contrato do ledger (por registro)

Identidade da fonte · classe · URL/documento/endpoint e parâmetros · data de acesso · período coberto ·
moeda · unidade · estatuto `reported | calculated | estimated` · fórmula quando calculado ·
**justificativa de por que esta fonte é a mais autoritativa para este claim** · conflitos registrados
com a escolha justificada · reconciliação dos números materiais usados no valuation.

### 6.3 Regras

- **Conflito entre fontes nunca é silenciado**: registram-se as duas, declara-se qual venceu e por quê.
- **Evidência independente para inputs críticos**: segunda fonte que copia a primeira não conta como
  confirmação. Quando não existir, declara-se — e o ramo permanece sensibilidade, não vira base em
  silêncio.
- **Gaps**: MATERIAL (impede conclusão responsável) → interrompe o usuário; NÃO-MATERIAL → nota de
  limitação declarada e segue. Nunca inventar, nunca silenciar.
- **Consenso é buscado quando disponível e material** (receita/EPS de t, t+1, t+2; price target médio;
  nº de analistas; data), porque alimenta o confronto temporal da reversa e a âncora do cenário de
  alta. **Ausência não impede a análise**: substitui-se por outras âncoras observáveis — guidance
  vigente da companhia, histórico normalizado, run-rate do trimestre mais recente sobre a base de
  capital atual, pares diretos — declarando qual âncora entrou no lugar. Sem consenso, o confronto
  temporal da reversa é declarado indisponível e a leitura de expectativas embutidas sai qualificada,
  nunca omitida.
- **Preço**: sempre o último disponível, com data e fonte registradas. **Não há TTL.** Se houver
  data-base explícita, a análise inteira se ancora nela — inclusive o **spot dos drivers, que passa a
  ser o daquela data**, nunca o de hoje.
- **Sem cache entre execuções.** Cache efêmero dentro da execução é permitido para não reprocessar a
  mesma fonte, e morre com ela.

## 7. Perguntas da tese

Três temas são cobertura obrigatória, porque são as três alavancas do múltiplo justo:

- **O moat é sustentável?** — barreira real, por que existe, por que não é replicável, como desaparece,
  qual evidência mostraria deterioração. Análise competitiva profunda, no espírito de *Competition
  Demystified*.
- **Quanto a companhia pode crescer?** — decomposição em mercado, share, preço, mix, capacidade,
  utilização, novos produtos, geografias, clientes, adjacências. Runway econômico, nunca extrapolação
  mecânica de CAGR.
- **Qual a rentabilidade desse crescimento?** — quanto capital o próximo dólar exige e o que ele rende.
  ROIC histórico × normalizado × ROIIC/RONIC; maintenance × growth capex; working capital; alavancagem
  operacional; margens incrementais; intensidade de capital. **Crescimento que destrói valor não é
  positivo.**

Cada tema gera **uma pergunta específica da companhia**; até **duas adicionais** quando um fator
específico realmente domina a tese. Teto de 5.

**Qualidade exigida por pergunta** (verificada no QC): específica da companhia · falsificável, com
observável nomeado · ligada explicitamente a **uma ou mais** variáveis ou mecanismos do valuation. Sem
o vínculo, é contexto, não pergunta de tese. O vínculo é uma **lista**, não um par: deterioração
competitiva pode mover share, margem, ROIIC e duração ao mesmo tempo — e forçar a correspondência
"moat = n, growth = g, profitability = ROIC" é proibido.

## 8. Valuation

### 8.1 Rota e métrica

**Uma rota canônica por análise**, escolhida e justificada pelo Analista. A rota oposta entra como
**cross-check rotulado** e só calcula quando existirem inputs coerentes; sem eles, declara-se a
ausência em vez de calcular silenciosamente um vetor que nenhuma DRE/BP gera.

O **seletor de métrica é livre dentro da rota**, com a álgebra exibida e dimensionalmente correta —
`EV/EBITDA = EV/NOPAT × (1−d)(1−t)`, `EV/EBIT = EV/NOPAT × (1−t)`, EPS e EBITDA/ação por divisão pelas
ações. A ponte até EV / Equity / preço por ação permanece explícita em qualquer métrica escolhida.

Em SOTP a aba exibe cards por segmento — cada um com rota, premissas e múltiplo próprios — e **uma
única ponte para preço no topo**, que é a trava contra dupla contagem.

### 8.2 Cenários × escolhas metodológicas

São eixos **separados**. Combinação de escolha metodológica não vira cenário.

- **Cenários**: bear / base / bull, cada um com **âncora observável obrigatória** (a grade canônica da
  metodologia, incluindo a trava do piso em pico de ciclo). O "teto da alavanca" é rotulado como
  não-cenário. Pesos probabilísticos opcionais, **fora da fórmula**, rotulados
  *valor ponderado por probabilidade* — nunca substituem bear/base/bull nem são apresentados como o
  fair value correto.
- **Escolhas metodológicas**: painel próprio com escolha central | alternativa | impacto no fair value |
  razão econômica, e alerta quando várias são empilhadas na mesma direção dentro do caso-base. O painel
  é **dinâmico**: a escolha aparece no nível principal quando o gatilho dela disparou (fronteira de
  consolidação com minoritários acima do limiar; leitura de capacidade com o Gate 3 disparado; caixa/E
  em híbrida financeira; ano de capex quando `d` econômico ≠ contábil); as demais ficam em avançado.
  Nenhuma dogmatização de "as dez" na interface.
- **Retorno exigido (hurdle)**: preservado, redefinido como reversa — "que valor resulta se eu exigir
  retorno de X%?". Rotulado, secundário, jamais chamado de fair value nem tratado como quarto cenário.

### 8.3 O triângulo

`g = RiR × ROIC` tem dois graus de liberdade. A análise canônica **registra quais dois foram inputs e
qual saiu como output**, por cenário. Na interface o usuário pode mudar essa configuração para simular,
**sem sobrescrever a calibração original**. Nenhum cenário existe com RiR silencioso.

### 8.4 Camada viva × precomputada

**Ao vivo no browser** (espelho JS com paridade obrigatória): núcleo de valor (`ev_nopat`/`ev_ebitda`,
`pe`, `degrau`, `rampa`), ponte para preço, solver de reversa (raiz única, varredura de múltiplas
raízes, métricas de identificação), sensibilidades 1D e 2D, e os **predicados numéricos dos
diagnósticos** — a prosa longa vem de dicionário estático gerado no build.

**Precomputado em Python e exibido rotulado** ("congelado nas premissas X"): `iso`, `apv`, `ponte`,
`drivers`, `normaliza`, `tabela`.

**Regra inegociável:** o diagnóstico se move junto com o número. Não existe número interativo com
diagnóstico congelado. Alterar um input para uma combinação economicamente incoerente muda o alerta na
mesma ação.

## 9. Entrega — três abas

Arquivo único autocontido, zero rede. Separação visual forte: **Tese e Valuation são o produto para o
comitê; Evidência é a camada de auditabilidade** e pode ser densa e técnica. Abrir o relatório não pode
parecer abrir uma ferramenta de engenharia.

**Aba Tese — decisão de investimento.** Conclusão com faixa piso–base–teto, veredicto explícito contra
o preço de tela (data e fonte), múltiplos de tela corrente e forward com base declarada, consenso como
referência externa, e as premissas realmente decisivas com número e uma linha de derivação → [o que
mudou desde a análise fornecida, 3 linhas, só quando material] → **Positives / Negatives** → **as
perguntas da tese**, cada uma com evidência, o observável que a falsificaria e o vínculo econômico →
Riscos, cada um com o observável que o monitoraria → Visão não-consensual. Organização interna dirigida
pelas perguntas, sem template editorial rígido.

**Positives / Negatives** — sem quantidade fixa. Cada item traz: a afirmação em uma frase; o vetor que
atinge (crescimento · moat · rentabilidade · risco · earning power · valuation); a variável ou mecanismo
do valuation que ele move; e o observável que o confirmaria ou o mataria. **Todo item material está
refletido no valuation ou explicitamente declarado como não incorporado** — sem obrigar Positive no
bull nem Negative no bear.

**Aba Valuation — laboratório econômico interativo.** Cabeçalho de resultado (valor/ação base, faixa
bear–bull, upside contra o preço com data e fonte, múltiplo justo × múltiplo de tela corrente e
forward, rota e convenção terminal em uma linha, badge de paridade) → quadro "como o valor é formado",
colapsável → cenários → **premissas agrupadas por bloco econômico**, cada uma com a cadeia de derivação
inline, original × editado, reset e diagnóstico ao vivo: *earning power e base* (métrica, valor, regime
contábil, `d`, `t`) · *crescimento e reinvestimento* (o triângulo) · *custo de capital* (WACC/Ke com rf,
beta, ERP) · *duração e terminal* (CAP, convenção, rentabilidade terminal, gp, política de caixa) → **a
ponte como waterfall**, com dívida, caixa, outros ajustes, minoritários e ações diluídas **editáveis no
próprio degrau** → painel de escolhas metodológicas → sensibilidades → o que está no preço (reversa por
eixo, custo de capital implícito sempre, beta implícito contra a banda observada, curva iso quando
houver dois vetores, e o julgamento comparativo de qual reconciliação exige menos violência às âncoras)
→ retorno exigido e valor ponderado por probabilidade, colapsados → cross-check por segundo método e
re-teste da hipótese terminal.

**Aba Evidência — auditabilidade.** Ledger completo · **ficha técnica da execução** · reconciliações ·
confronto com a análise fornecida, quando houver · limitações declaradas · fontes. Linguagem interna
permitida aqui.

*Ficha técnica da execução* é o nome do artefato que a metodologia vendorizada chama de "memória
técnica": o bloco estruturado de reprodutibilidade — premissas, gates, escolhas, comandos executados,
proveniência — que permite reconstruir **aquela** execução. O nome muda para não sugerir estado: ela
pertence a uma execução, é gerada com ela, persiste no workspace daquela execução e **nunca é lida por
outra**. Não é memória em nenhum sentido do termo.

## 10. Gráficos

**Substrato:** uPlot (vendorizado, MIT) para as famílias cartesianas — linhas, barras, área, stacked,
scatter — mais um **módulo SVG próprio** para waterfall/bridge, matriz de sensibilidade/heatmap e
decomposições. Sem dependência pesada nova.

**Gramática (spec por gráfico):** `pergunta` — qual insight ele responde, campo obrigatório, é o que
impede gráfico decorativo · `tipo` de **enum fechado** · `series[]` com `fonte`, `derivacao`
(`direta | derivada | engine`) e `formula_nota` quando derivada · `overlays[]` de premissa **sempre**
com chave rastreável ao caso ou aos resultados · `nota_janela` · `caption`.

**Validação no build:** série `direta` é conferida numericamente contra o arquivo de origem;
`derivada` exige fórmula e recomputação a partir da fonte; `engine` referencia chave de resultado.
Série não rastreável ⟹ o builder recusa emitir. Tipo fora do enum ⟹ recusa.

**Cobertura, não lista:** não há gráfico obrigatório. Cada pergunta da tese tem **pelo menos um exhibit
útil** — gráfico, tabela, matriz ou outro — **ou** uma decisão explícita de que visualização não
acrescenta informação. Cinco números numa tabela podem comunicar melhor que um gráfico, e nesse caso a
tabela é a resposta certa.

## 11. QC em três níveis

O QC impõe **integridade econômica e matemática**, não preferência editorial.

**HARD FAIL — não emite:**
paridade Python↔JS divergente · `selftest` ou suíte da metodologia falhando · número material do
valuation sem proveniência · gráfico com dados não rastreáveis · inconsistência estrutural que torne o
valuation matematicamente inválido · perguntas da tese ausentes ou sem vínculo econômico · fair value
sem reversa / custo de capital implícito quando a metodologia exigir · números materialmente
conflitantes sem reconciliação ou disclosure · fronteira de escopo declarada com fair value por ação
como conclusão principal.

**REQUIRED DISCLOSURE — emite, mas aparece explicitamente na entrega:**
conservação de capital que não fecha · ausência de contraprova independente · premissa central fora do
ponto central da grade · gap material que não inviabiliza o valuation · metodologia especial ou
limitação de escopo · input relevante baseado em estimativa em vez de dado observado.

**QUALITY WARNING — interno:**
exhibit fraco · concentração excessiva de fontes · sensibilidade pouco informativa · tese muito
dependente de uma única premissa · pergunta de tese pouco discriminante · Positives/Negatives pouco
ligados ao valuation · termos de linguagem interna vazando no corpo · contagem de premissas na
Conclusão fora do usual.

## 12. Workspace e contrato do builder

**Namespace por execução:** `analises/<TICKER>/<execution-id>/`, autocontido. Por default, **uma
execução não acessa outra**. A trava não é só a regra escrita: o builder aceita **uma única raiz de
execução** e recusa qualquer caminho fora dela. Execuções anteriores ficam no disco como arquivos
inertes de saída, disponíveis apenas quando o usuário aponta explicitamente.

**Quarentena.** Documento de evidência fornecido pelo usuário (filing, deck, relatório setorial, nota
própria) é evidência comum, lida desde o início. **Relatório ou valuation anterior com conclusão** vai
para quarentena e só é aberto no M4, depois de toda a derivação estar pronta — ler antes contamina com
ancoragem invisível. O confronto resultante classifica cada divergência em: dado novo · premissa
revista · erro anterior · pergunta anterior resolvida pelo observável.

**Contrato do builder.** Existe **um único artefato estruturado, validado por schema, como fonte de
verdade do builder**, com composição canônica e entrada determinística. O builder não interpreta prosa
e não busca dado por conta própria. O formato e a decomposição em arquivos são decisão de
implementação — **nenhum formato legado é herdado por inércia**. Todo número de valuation citado em
prosa é resolvido por placeholder auditável; número livre legítimo é marcado como tal.

## 13. Testes, fixtures e CI

**Suíte da metodologia:** `selftest` + `testes.py` do vendor. Verificado nesta máquina em 2026-08-21:
a suíte é **totalmente portátil** — importa apenas `sys`, `itertools`, `ast` e `os.path`, com as
âncoras das planilhas de referência *hardcoded*; não há dependência de planilha externa nem de rede, e
ambas passam. A suíte também verifica a integridade dos arquivos do próprio pacote, o que encaixa
diretamente no manifest de hashes.

Princípio mantido mesmo assim: **suíte portátil obrigatória no CI** × **regressões opcionais contra
fixtures proprietários**, para qualquer fixture futuro derivado de planilha do dono.

**Paridade Python↔JS.** Fixture reproduzível de vetores aleatórios com semente fixa **mais casos-limite
explícitos**: `Ke ≈ g`, `ROIC ≤ 0`, `RiR > 100%`, `gp ≥ W`, `ROE = Ke` com caixa, `n = 0`, `ROE2 = 0`,
`ROIC = WACC`. Critério: **erro relativo com piso absoluto** — `|py − js| ≤ max(τ·|py|, τ)` — e não
número fixo de casas, porque as grandezas vão de múltiplos (~10) a equity values (~10⁹). `τ` é definido
**empiricamente**: o motor faz somatórios explícitos de até `n` termos com potências, então o erro
acumulado é da ordem de `n × eps` (~2e-15 para n = 10); o teste **mede o erro máximo observado** sobre
a fixture, fixa `τ` com folga documentada acima dele, e **alerta se o observado se aproximar do
limiar** — o limiar entra na suíte como propriedade medida, nunca como constante mágica. Divergência ⟹
**falha fechada**: o builder não emite.

**Fixture sintética offline (CI).** Companhia fictícia com dados inventados mas economicamente
coerentes, desenhada para exercitar deliberadamente os caminhos raros: rota firm, um segmento de SOTP,
o gatilho de capacidade pré-construída, um driver exógeno com gap acima do limiar, uma escolha
metodológica que move mais de 10% — **e um caso que deve falhar** (número material sem proveniência),
para que o HARD FAIL seja testado como comportamento e não presumido.

**Golden case real, fora do CI.** Aceitação de release, rodada à mão. O sintético testa a engenharia;
o real testa se o Fleet produz bom equity research.

**CI passa a rodar:** suíte da metodologia · verificação de hashes do vendor contra o manifest ·
paridade sobre a fixture com patológicos · testes do wrapper · testes do builder · testes dos três
níveis de QC · validação do schema do ledger e do contrato do builder.

## 14. Fronteira de escopo

**Fora do escopo da metodologia como métrica-manchete:** vida econômica finita (mineração, óleo e gás,
concessão com termo) · REITs e imobiliárias · pré-lucro / introdução.

**Dentro, como rota nativa:** financeiras (equity-side, P/VP = P/L × ROE) · holdings (soma das partes,
com desconto de holding como escolha nomeada e precificada) · multi-segmento e safra de capital.

**Entregável quando a fronteira é declarada:** (i) a arquitetura dominante necessária e por quê;
(ii) as perguntas relevantes da tese — que não dependem da rota de valuation; (iii) a leitura do que o
preço/múltiplo embute, pela reversa; (iv) conclusão qualitativa e condicional — direção e o que teria
que ser verdade. **Sem preço-alvo de manchete.** Emitir fair value por ação como conclusão principal
sob fronteira declarada é HARD FAIL.

Nenhum motor de valuation novo é construído sem metodologia canônica e suíte próprias.

## 15. Decisões registradas

| # | Tema | Decisão |
|---|---|---|
| 1 | Estatuto da metodologia | Cópia congelada + wrapper fino; matemática nunca reimplementada; JS só como espelho com paridade e falha fechada; skill standalone intocada |
| 2 | Herança | Sem herança de premissas e conclusões; rederivação total; **relatório anterior só existe como confronto quando explicitamente fornecido** |
| 3 | Estrutura da entrega | Sequência metodológica preservada como disciplina do argumento; miolo thesis-driven; sem rigidez editorial |
| 4 | Perguntas da tese | Três temas obrigatórios + até duas adicionais; teto de 5; company-specific, falsificáveis, ligadas a variáveis (lista, não par) |
| 5 | Escopo | Nativo o que é composição do motor; fronteira honesta no resto; sem motores novos |
| 6 | Pesquisa e dados | Um tipo de agente, N instâncias; especialização no mandato; hierarquia de fontes **por claim**; provenance forte; evidência independente para inputs críticos |
| 7 | Camada viva | Núcleo + ponte + reversa + sensibilidades + diagnósticos numéricos ao vivo; `iso`/`apv` precomputados; paridade obrigatória |
| 8 | Cenários × escolhas | Eixos separados; painel de escolhas dinâmico; probabilidade e hurdle preservados como secundários e rotulados |
| 9 | Gráficos | uPlot + SVG próprio; gramática com `pergunta` obrigatória; sem lista fixa; cobertura por exhibit útil ou decisão explícita |
| 10 | Abas | Tese · Valuation · Evidência, com separação visual forte; ficha técnica da execução também em arquivo |
| 11 | Processo | Quatro marcos, autônomo por default; interrupção só por gap material, ambiguidade irredutível ou modo colaborativo; escolhas sem default são do Analista |
| 12 | QC | Três níveis: HARD FAIL · REQUIRED DISCLOSURE · QUALITY WARNING; integridade ≠ template |
| 13 | Seções | Premissas completas no Valuation; decisivas na Tese; P/N sem quantidade fixa, cada item material refletido ou declarado como não incorporado |
| 14 | Rota e métrica | Rota canônica por análise; oposta como cross-check condicionado a coerência; seletor de métrica livre com ponte explícita |
| 15 | Layout do Valuation | Ordem definida na Seção 9; ponte editável no waterfall; triângulo como controle sem sobrescrever calibração |
| 16 | Estado persistente | **Eliminado integralmente.** Sem memória durável, sem cache entre execuções, sem P2, sem gatilho por ticker; relatório anterior só entra fornecido explicitamente, como confronto |
| 17 | Skills | Cinco skills + um agente; vendor read-only; zero duplicação de metodologia |
| 18 | Migração | v4.0.0 breaking; legado removido só após validação end-to-end; suíte portátil separada de fixtures proprietários |
| 19 | Workspace | Namespace por execução; trava mecânica de raiz única |
| 20 | Confronto | Relatório anterior fornecido entra selado, aberto só após a derivação; confronto estruturado |
| 21 | Produtos | Análise × Leitura de preço; na dúvida, Análise |
| 22 | Fronteira | Entregável qualificado sem fair value de manchete; HARD FAIL se violado |
| 23 | Golden case | Sintético offline no CI (com caso que deve falhar) + real fora do CI |
| E1 | Preço | Sem TTL: último preço disponível, com data e fonte; data-base explícita ancora a análise inteira, inclusive o spot dos drivers |
| E2 | Contrato do builder | Um artefato estruturado validado por schema, composição canônica, entrada determinística; formato não herdado por inércia |

## 16. Premissas declaradas

1. **Idioma segue a execução; PT-BR é default, não hardcode.** O relatório é escrito no idioma do
   pedido, e PT-BR vale quando nada indicar outro. Consequência de implementação: rótulos do template,
   do builder e das mensagens de QC são **parametrizados**, nunca strings fixas em português. Termos de
   mercado permanecem na forma padrão (EBITDA, NOPAT, ROIC, WACC, capex, payout); a tabela de tradução
   da metodologia governa o resto. Leitor presumido: comitê de investimento.
2. Moeda e regime declarados no caso, com `g`, `gp` e custo de capital travados na mesma unidade.
3. Todos os conectores disponíveis são fontes possíveis; nenhum é obrigatório ou exclusivo.
4. Repositório e nome do plugin permanecem; atualizar o que está instalado no app é decisão do usuário.
5. A skill `multiplos-justos` não é modificada nem estendida. Necessidade do Fleet que ela não atenda
   vira limitação declarada ou pedido de evolução da skill pelo dono — nunca código do Fleet
   reimplementando a conta.

## 17. Ordem de implementação

Cada item termina verificável. O legado só sai no fim.

1. **Este documento** aprovado no repositório.
2. **Vendor congelado**: copiar a skill v9.24, gerar manifest de hashes, ligar `selftest` + `testes.py`
   ao CI, escrever `er-multiplos-justos` como índice sem paráfrase.
3. **`er-valuation`**: contrato do caso, rotas, cenários, ponte para preço, SOTP, reversa,
   sensibilidades — com testes.
4. **Espelho JS + paridade**: fixture com semente fixa e casos-limite, `τ` medido empiricamente, falha
   fechada.
5. **`er-relatorio`**: builder de 3 abas, gramática de gráficos, módulo SVG, QC de três níveis.
6. **Fixture sintética offline**, incluindo o caso que deve falhar.
7. **`er-evidencia`** + agente `pesquisa-evidencia`.
8. **`er-analise`**: quatro marcos, política de autonomia, regras invioláveis.
9. **Golden case real**, fora do CI, como aceitação.
10. **Só então**: remoção do legado v3/K3 do carregamento, bump para 4.0.0, release.

## 18. Regras invioláveis da v4

1. A matemática de valuation vem do motor congelado. Proibido recomputar, aproximar ou reimplementar em
   prosa, Python novo ou JS novo. O único JS de valuation é o espelho verificado por paridade.
2. Paridade divergente, suíte falhando ou QC em HARD FAIL ⟹ **nada é emitido**.
3. Nenhuma escolha que a metodologia declara sem default recebe default. O Analista decide, justifica
   pela razão econômica e exibe o custo da alternativa.
4. Sem herança: nenhuma premissa, tese, pergunta, conclusão ou valuation anterior entra automaticamente.
5. Todo número material do valuation tem proveniência, reconciliação e justificativa da fonte para
   aquele claim. Conflito entre fontes é registrado, nunca silenciado.
6. O builder é o único caminho de emissão, aceita uma única raiz de execução, não interpreta prosa e
   não busca dado.
7. Toda pergunta da tese é company-specific, falsificável e ligada a variável ou mecanismo do valuation.
8. Fronteira de escopo declarada ⟹ nenhum fair value por ação como conclusão principal.
9. Resposta do usuário é evidência a verificar, nunca fato.
10. O vendor é read-only. Alteração local quebra a suíte, por desenho.

---

*Documento gerado a partir do `/grill-me` de redesenho de 2026-08-21: 23 decisões e 2 emendas,
todas registradas na Seção 15. Nenhuma linha de código foi escrita antes desta aprovação.*
