---
name: er-analise
description: >-
  USE SEMPRE, ANTES de qualquer resposta, quando o pedido envolver analisar uma
  empresa ou ação com ticker: iniciar ou refazer uma análise, montar ou
  revisar uma tese, rodar valuation, ler o que o preço embute ("o preço de X
  faz sentido?", "essa ação está cara?", "o que o mercado precifica em Y?") ou
  decidir compra ou venda. Workflow master do equity-research-fleet v4: dois
  produtos (Análise e Leitura de preço), quatro marcos (escopo, perguntas da
  tese, pesquisa e derivação, valuation e entrega), autonomia por padrão,
  pesquisa pelo agente pesquisa-evidencia, valuation pelo er-valuation sobre o
  motor congelado e entrega pelo builder do er-relatorio. NÃO use para
  sourcing sem ticker nem para questões de carteira inteira (essas vão para a
  skill portfolio-construction, fora do fleet); e não use como fonte de
  metodologia (er-multiplos-justos) nem de doutrina de evidência
  (er-evidencia).
---

# er-analise — o workflow master da v4

O Analista é o loop principal: escopa, formula as perguntas da tese, pesquisa, deriva, decide, monta o
caso, escreve a tese e entrega. Esta skill é **processo e julgamento** — nunca conta nem validação
(emenda E3 de `docs/desenho-arquitetura-v4.md`, a fonte de verdade):

- **a conta é do motor congelado**, chamado pelo `er-valuation`: nenhum número de valuation nasce em prosa,
  planilha, Python ou JS escrito na análise;
- **a validação da entrega é do builder** do `er-relatorio`, o único caminho de emissão;
- **a metodologia é do vendor**, indexado pelo `er-multiplos-justos`, e o que dela a execução precisa como
  dado — os comandos da suíte, os gates, a lista de banimento, os insumos do caso — vem publicado no
  catálogo da integração (`skills/er-valuation/assets/catalogo_apresentacao.json`).

| Peça | Papel na execução |
|---|---|
| `er-multiplos-justos` | índice do vendor congelado: onde ler os gates, as regras de derivação, a convenção terminal, a reversa |
| `er-evidencia` | a doutrina de pesquisa e proveniência e o contrato `ledger/1` |
| agente `pesquisa-evidencia` | uma instância por mandato de pesquisa, várias em paralelo |
| `er-valuation` | o caso (`caso.json`) e o motor: `skills/er-valuation/scripts/avaliar.py` grava `resultados.json` |
| `er-relatorio` | o contrato da entrega, os placeholders, o QC de três níveis e o builder (`skills/er-relatorio/scripts/builder.py`) |
| `skills/er-analise/scripts/execucao.py` | a raiz da execução: `nova`, `suite` e `montar` |

## 1. Os dois produtos

Dois produtos, não dois níveis de esforço (§5):

- **Análise** — o fluxo completo: tese, valuation e o relatório de três abas (Tese, Valuation, Evidência).
  É o fluxo de valuation de companhia real do vendor, com a engenharia reversa dentro.
- **Leitura de preço** — o fluxo de engenharia reversa do vendor: o que o preço embute, o menu de
  reconciliação, o custo de capital implícito e o nível implícito, com o escopo declarado (cobertura e
  encerramento não se aplicam). A entrega é só a aba Valuation. Use quando o pedido é sobre o preço — "faz
  sentido?", "o que está precificado?" — e não pede tese nem recomendação.

**Na dúvida, Análise.** O produto é declarado em `execucao.json` (`execucao.py nova --produto
leitura_de_preco`); sem o campo, a entrega é Análise. Os dois fluxos do vendor estão em
`vendor/multiplos-justos/SKILL.md`, "Fluxo por tipo de pedido".

O que cada produto exige — a forma da entrega recusa o que falta, com código 1:

| Exigência | Análise | Leitura de preço |
|---|---|---|
| Tese inteira (conclusão, veredicto, premissas decisivas, Positives e Negatives, perguntas, riscos) | sim | a forma pede os blocos; a página não os mostra |
| faixa piso–base–teto | sim, fora da fronteira de escopo | proibida: é o HARD FAIL `produto_com_preco_alvo` |
| reversa | sim, salvo limitação que o catálogo declara (degrau, rampa) | sempre: sem ela, `analise_sem_reversa`; a rota rampa não serve a este produto |
| `analise.o_que_esta_no_preco`, com a reversa | sim | sim |
| `analise.reteste_terminal` | sim | não |
| cross-check publicado ou `analise.cross_check.ausente` | um dos dois | não |

## 2. Autonomia e interrupção

**Autônomo por padrão** (§5). O Analista interrompe o usuário **apenas** quando:

1. há lacuna MATERIAL que impede uma conclusão responsável;
2. há ambiguidade de escopo genuinamente irredutível — a companhia, a listagem ou a classe da ação não se
   resolvem pela pesquisa;
3. o usuário pediu, explicitamente, modo colaborativo.

Fora disso, decide — inclusive convenção terminal, regime contábil, política de caixa, leitura de
capacidade e earning power —, justifica pela razão econômica em uma frase e mostra o custo da alternativa
no painel de escolhas (o caso declara a escolha, o `er-valuation` precifica o outro ramo, e
`analise.escolhas` traz a razão). **Nenhuma escolha que a metodologia deixa sem default recebe default**,
nem uma pergunta ao usuário no lugar da decisão.

O M2 é gate interno de qualidade, não checkpoint de aprovação. A resposta do usuário, quando há, é
evidência a verificar, nunca fato: registre-a pela doutrina do `er-evidencia` e procure a fonte que a prove.

## 3. A raiz da execução e a quarentena

Cada execução é uma raiz autocontida, criada no M1:

```bash
python skills/er-analise/scripts/execucao.py nova <TICKER> [--produto leitura_de_preco]
```

O comando imprime a raiz, `analises/<TICKER>/<AAAA-MM-DD-NNN>/`:

| Parte | O que é | Quem escreve |
|---|---|---|
| `execucao.json` | `id`, `ticker`, `idioma`, `produto`; `gates` (M3); `suite_da_metodologia` (M4) | `nova`; o Analista, os gates; `suite`, o registro da suíte |
| `evidencia/<mandato>.json` | um fragmento `ledger/1` por mandato, e o do Analista | os agentes e o Analista |
| `caso.json` | o caso de valuation | o Analista |
| `resultados.json` | a saída do motor | `avaliar.py`, do `er-valuation` |
| `analise.json` | a Tese e os blocos do produto | o Analista |
| `dados.json` | os datasets dos exhibits, quando algum lê série | o Analista |
| `confronto.json` | o confronto com a análise fornecida, quando há | o Analista, no M4 |
| `quarentena/` | relatório ou valuation anterior com conclusão | o Analista, no M1 |
| `entrega.json`, `relatorio.html`, `qc.json`, `ficha-tecnica.json` | a entrega e o que o builder emite | `montar` e o builder |

**Sem herança** (§18.4): nenhuma premissa, tese, pergunta, conclusão, registro ou valuation de outra execução
entra nesta — nem como ponto de partida. Execuções anteriores ficam no disco como arquivos inertes; uma
delas só é lida quando o usuário a aponta, e então ela é documento com conclusão.

**Quarentena** (§12). No M1, classifique cada documento fornecido:

- **evidência** — filing, deck, relatório setorial, nota própria: lido desde o início, pela doutrina do
  `er-evidencia`;
- **quarentena** — relatório ou valuation anterior **com conclusão** (preço-alvo, fair value, recomendação,
  veredicto), inclusive a saída de uma execução anterior: vai para `quarentena/` e só é aberto no M4,
  depois de toda a derivação pronta. Ler antes contamina com ancoragem invisível. Os números de dentro dele
  se buscam na fonte primária.

## 4. Os quatro marcos

Marcos com saída verificável, **adaptativos por dentro** e atravessados sem pedir licença. A profundidade
de cada um segue a tese: uma pergunta que decide o valor ganha mais pesquisa, mais contraprova e mais
exhibits do que uma que só contextualiza.

| Marco | Saída verificável |
|---|---|
| **M1 — Escopo** | a raiz criada; companhia, moeda e regime declarados; produto; documentos classificados em evidência e quarentena; data-base, se explícita |
| **M2 — Perguntas da tese** | de três a cinco perguntas, cada uma com o observável que a falsificaria e a lista de variáveis ou mecanismos do valuation a que se liga |
| **M3 — Pesquisa e derivação** | os fragmentos de evidência completos; os cinco gates decididos e declarados em `execucao.json`; premissas derivadas com a cadeia de conta explícita; escolhas metodológicas decididas e justificadas |
| **M4 — Valuation e entrega** | `resultados.json` do caso final; a suíte com todo código 0; o confronto com a análise fornecida, se houver; `montar` com código 0 e o checklist de revisão feito |

### M1 — Escopo

Identifique a companhia (ticker, listagem, classe), a moeda e o regime contábil e monetário, e a data-base,
se o pedido a fixa: com data-base, a análise inteira se ancora nela — o preço e o spot dos drivers são os
daquela data. Escolha o produto, crie a raiz e classifique os documentos. Verifique a **fronteira de escopo**
(§14): vida econômica finita, REIT ou imobiliária, pré-lucro. Sob fronteira, o caso a declara
(`fronteira_de_escopo`, com a classe, a arquitetura dominante e a razão) e a entrega é condicional: as
perguntas da tese, a leitura do que o preço embute e a conclusão qualitativa — **nenhum fair value por ação
como conclusão principal**.

### M2 — Perguntas da tese

Três temas são cobertura obrigatória, porque são as três alavancas do múltiplo justo (§7), cada um com uma
pergunta específica da companhia:

- **`moat`** — a barreira é real e sustentável? Por que existe, por que não se replica, como desaparece, que
  evidência mostraria a deterioração;
- **`crescimento`** — quanto a companhia pode crescer? Mercado, share, preço, mix, capacidade, utilização,
  produtos, geografias, clientes, adjacências: runway econômico, nunca CAGR extrapolado;
- **`rentabilidade_do_crescimento`** — quanto capital o próximo real exige e quanto rende: ROIC histórico,
  normalizado e incremental, capex de manutenção e de crescimento, capital de giro, margens incrementais.
  Crescimento que destrói valor não é positivo.

Até duas perguntas `especifica` a mais, quando um fator domina a tese; teto de cinco. Cada pergunta é
**específica da companhia**, **falsificável** — com o observável nomeado — e **ligada a uma ou mais**
variáveis ou mecanismos do valuation (`vinculo`: premissas da rota em `catalogo.premissas`, ou blocos
econômicos em `catalogo.blocos`). O vínculo é uma lista, nunca um par forçado: deterioração competitiva pode
mover share, margem, retorno incremental e duração ao mesmo tempo. Sem vínculo, é contexto, não pergunta.

### M3 — Pesquisa e derivação

**Mandatos de pesquisa.** Despache o agente `pesquisa-evidencia` (`agents/pesquisa-evidencia.md`), uma
instância por mandato, em paralelo, com os domínios que a tese pede — filings; RI e transcripts; setorial e
competição; macro e drivers; pares. Cada despacho carrega:

```text
Mandato: <domínio>
Companhia: <nome> (<TICKER>), <moeda> e <regime>; data-base: <AAAA-MM-DD ou nenhuma>
Claims: <claim, período> — marcando os críticos, que pedem contraprova independente
Documentos de evidência: <caminhos> (nunca os de quarentena/)
Saída: <raiz>/evidencia/<mandato>.json, com os ids prefixados por "<mandato>:"
```

O Analista também pesquisa — para fechar lacunas, testar hipóteses e procurar evidência contrária — e grava
o que acha no próprio fragmento (`evidencia/analista.json`). Toda evidência segue a doutrina do
`er-evidencia`: a fonte mais autoritativa para cada claim, conflito nunca silenciado, contraprova
independente para os inputs críticos, consenso buscado quando material, lacuna MATERIAL ou NÃO-MATERIAL.

**A junção do ledger.** Cada fragmento é um objeto `ledger/1` com `versao_contrato`, `registros` e
`lacunas`. O agente entrega sem ligação com o caso; o Analista acrescenta, nos fragmentos, `usado_em` (os
caminhos do caso que o número sustenta), `reconciliacao` (a conta, quando o número do caso difere) e
`contraprova_de` quando a confirmação veio de outro mandato. O `montar` junta os fragmentos num ledger único,
na ordem do nome do arquivo, e recusa um id repetido — o prefixo por mandato evita a colisão.

**Os cinco gates.** Antes de qualquer conta, decida os cinco gates da metodologia. O `er-multiplos-justos`
aponta onde eles estão: `vendor/multiplos-justos/SKILL.md`, "Cinco gates antes de qualquer conta", e as
seções de `vendor/multiplos-justos/references/aplicacao.md` que cada gate manda ler — leia no vendor, nunca
de memória nem por resumo. Cada decisão vai para `execucao.json`:

```json
"gates": [{"gate": "gate_0", "decisao": "a decisão, com os observáveis que a sustentam"}]
```

O `gate` é o código que `catalogo.gates` publica (os cinco, com o título do vendor como rótulo); a `decisao`
é texto da ficha técnica, na aba Evidência, onde a linguagem interna é admitida. Faltando algum, o builder
recusa (`gates_nao_declarados`). A decisão de cada gate chega ao valuation pelo caso — a convenção terminal
nas premissas, o registro de drivers, o degrau, a rota de rampa, as escolhas metodológicas —, pelo contrato
que o `er-valuation` documenta.

**Derivação.** Cada premissa sai com a cadeia de conta explícita, a partir de registros do ledger — a conta
que declara uma premissa é do Analista, registrada com fórmula e insumos; a conta de valuation, nunca: essa é
do motor. Cada escolha metodológica é decidida (seção 2), com a razão e a alternativa.

### M4 — Valuation e entrega

1. **O caso.** Escreva `caso.json` pelo contrato do `er-valuation` (`skills/er-valuation/SKILL.md`,
   "Contrato do caso": rota, métrica-base, ponte, cenários com âncora, triângulo e premissas, mercado,
   reversa, sensibilidades, escolhas, drivers, soma das partes, degrau, fronteira de escopo) e rode o motor:

   ```bash
   python skills/er-valuation/scripts/avaliar.py <raiz>/caso.json --out <raiz>/resultados.json
   ```

   Caso recusado sai com código 1 e a razão nomeada: corrija o caso, nunca contorne o gate. Toda mudança no
   caso roda o motor de novo — o builder recusa `resultados.json` que não é do caso
   (`resultados_nao_correspondem_ao_caso`).
2. **A proveniência.** Todo número do caso que `catalogo.insumos_do_caso` cobre precisa de um registro cujo
   `usado_em` o nomeie, com o mesmo número ou a reconciliação.
3. **A quarentena.** Só agora abra o que está em `quarentena/`. O confronto vai em `confronto.json`, cada
   divergência classificada como `dado_novo`, `premissa_revista`, `erro_anterior` ou `pergunta_resolvida`;
   o que mudou, em até três linhas e só quando material, vai em `analise.mudou_desde_analise_fornecida`.
4. **A análise.** Escreva `analise.json` pelo contrato do `er-relatorio` (`skills/er-relatorio/SKILL.md`, "O
   contrato `entrega/1`" e "A Tese"), com a prosa da seção 5.
5. **A suíte e a entrega**, pelo `execucao.py` (seção 6), e o que o builder devolver (seção 7).
6. **O checklist de revisão do M4** (seção 8).

## 5. A prosa e os placeholders

**Todo número de valuation citado em prosa é um placeholder auditável** — `{{resultados:<caminho>|<formato>}}`
ou `{{caso:<caminho>|<formato>}}` —, e o número livre legítimo, `{{livre:<texto>}}`. Qualquer outro dígito na
prosa, ano e trimestre inclusive, é o HARD FAIL `numero_sem_proveniencia`. Os formatos, e o formato que
cada unidade aceita, estão em `skills/er-relatorio/SKILL.md`, "Placeholders auditáveis". Prosa é o que
`placeholders.campos_de_prosa` lista: os textos da Tese, a descrição e o tratamento das lacunas, a razão do
consenso ausente, a razão de cada escolha, o julgamento do que está no preço, a razão da ausência do
cross-check, o texto do re-teste terminal e os textos dos exhibits. Os textos dos registros do ledger e do
confronto são dado da aba Evidência e podem citar números.

**O corpo fala a língua do mercado.** Nomes e números de gates, códigos de regra, versões, comandos, flags e
enums não entram nas abas Tese e Valuation: a lista de banimento da metodologia, que o catálogo publica
(`catalogo.linguagem_interna`), acende o aviso `linguagem_interna_no_corpo`. O conceito entra traduzido — a
tabela de tradução está em `vendor/multiplos-justos/references/aplicacao.md`, §5. A regra é de rótulo, nunca
de conteúdo: a conta, a direção do erro e o "não verificado nesta execução" continuam no texto.

**Sem preço-alvo onde a conclusão é condicional.** Sob fronteira de escopo ou sob a Leitura de preço, nenhum
número que o catálogo declara conclusão de valor entra na prosa da Tese (`fronteira_com_preco_alvo`,
`produto_com_preco_alvo`).

## 6. A suíte e a entrega pelo `execucao.py`

```bash
python skills/er-analise/scripts/execucao.py suite <raiz>
python skills/er-analise/scripts/execucao.py montar <raiz>
```

**`suite`** roda cada comando que `catalogo.suite_da_metodologia` exige, cada um numa invocação fresca, e
grava o código de saída de cada um em `execucao.json`. Sai com 1 se algum não passou — e a entrega com esse
registro é recusada (`suite_da_metodologia_nao_passou`). Rode a suíte em toda execução, no M4. Uma falha que
persiste significa vendor ou ambiente quebrados: pare e reporte; **o vendor é read-only**, e editar a cópia
congelada é o que a suíte existe para pegar.

**`montar`** compõe `entrega.json` das partes da raiz e roda o builder, devolvendo o código dele:

| Código | Significado | O que fazer |
|---|---|---|
| `0` | emitido: `relatorio.html`, `qc.json`, `ficha-tecnica.json` | triar os achados do `qc.json` e fazer o checklist |
| `2` | HARD FAIL: só `qc.json`, nada emitido | corrigir na origem e montar de novo |
| `1` | recusa de forma, ou raiz sem uma parte: nada emitido | ler a mensagem, que nomeia o campo ou o arquivo |

Código diferente de 0 é "nada publicável nesta raiz": um `relatorio.html` só vale se o último `montar`
devolveu 0.

## 7. O que o builder devolve

| Nível | O que significa | O que o Analista faz |
|---|---|---|
| HARD FAIL | a entrega é matemática ou contratualmente inválida; nada sai | corrige na origem — o caso (e roda o motor), o fragmento, a análise — e monta de novo. Nunca enfraquece a afirmação só para passar |
| REQUIRED DISCLOSURE | a entrega sai, com o aviso visível | confere se o aviso é verdadeiro e esperado. Se aponta trabalho por fazer — a contraprova não buscada, o consenso não procurado —, faz; se é a honestidade da análise, fica. Nunca apaga um aviso rebaixando a evidência |
| QUALITY WARNING | interno: `qc.json` e a ficha em arquivo, nunca a página | tria no checklist e corrige o que é material |

Os códigos que pedem ação específica do Analista:

| Código | Nível | O que fazer |
|---|---|---|
| `suite_da_metodologia_nao_passou` | HARD FAIL | rodar `suite` de novo; falha persistente é vendor ou ambiente quebrados — parar e reportar |
| `gates_nao_declarados` | HARD FAIL | declarar em `execucao.json` a decisão de cada gate que o catálogo publica |
| `paridade_divergente` | HARD FAIL | a correção é da camada de integração: parar e reportar, nunca contornar |
| `resultados_nao_correspondem_ao_caso` | HARD FAIL | rodar o `er-valuation` de novo sobre o caso final |
| `insumo_sem_proveniencia` | HARD FAIL | registrar a fonte do número, com o caminho em `usado_em` |
| `insumo_nao_reconciliado` | HARD FAIL | igualar o número ao da fonte, ou declarar a reconciliação com a conta |
| `conflito_de_fontes_silenciado` | HARD FAIL | decidir o conflito pelo princípio da fonte e declarar o vencedor |
| `numero_sem_proveniencia` | HARD FAIL | trocar o dígito solto por um placeholder |
| `perguntas_da_tese_incompletas` | HARD FAIL | cobrir os três temas, uma vez cada, com três a cinco perguntas |
| `analise_sem_reversa` | HARD FAIL | declarar a reversa no caso; sem ela, o produto não é Leitura de preço |
| `escolha_sem_razao` | HARD FAIL | dar a razão econômica de cada escolha precificada |
| `fronteira_com_preco_alvo` | HARD FAIL | tirar a faixa e todo número de valor da Tese |
| `produto_com_preco_alvo` | HARD FAIL | tirar a faixa, ou entregar como Análise |
| `lacuna_material` | REQUIRED DISCLOSURE | confirmar a materialidade; se a lacuna impede conclusão responsável, interromper o usuário |
| `sem_contraprova_independente` | REQUIRED DISCLOSURE | buscar a segunda fonte de outra identidade; sem ela, o aviso fica |
| `insumo_estimado` | REQUIRED DISCLOSURE | buscar o dado observado; sem ele, o aviso fica |
| `consenso_indisponivel` | REQUIRED DISCLOSURE | conferir que o consenso foi procurado e a âncora substituta é a melhor |
| `linguagem_interna_no_corpo` | QUALITY WARNING | traduzir o conceito para a língua do mercado |
| `contagem_de_premissas_fora_do_usual` | QUALITY WARNING | rever quais premissas decidem a tese: de duas a cinco |
| `tese_dependente_de_uma_premissa` | QUALITY WARNING | ligar as perguntas às variáveis que elas movem de fato |
| `concentracao_de_fontes` | QUALITY WARNING | diversificar só onde há fonte à altura |
| `sensibilidade_pouco_informativa` | QUALITY WARNING | ampliar a amplitude da grade ou trocar a premissa |

A lista inteira, com o gatilho de cada código, está em `skills/er-relatorio/SKILL.md`, "QC de três níveis".

## 8. Checklist de revisão do M4

Com `montar` em 0, antes de encerrar, o Analista revê o que é julgamento editorial e nenhum código decide:

1. **Cada exhibit responde à pergunta que o cita?** O gráfico mostra o observável ou o mecanismo da
   pergunta, e o tipo serve à leitura — cinco números numa tabela podem comunicar melhor que um gráfico.
   Exhibit decorativo sai, ou vira a decisão explícita de que visualização não acrescenta.
2. **Cada pergunta da tese discrimina?** Um resultado plausível do observável mudaria o valuation; a
   pergunta que qualquer companhia do setor responderia igual não é da tese.
3. **Positives e Negatives estão ligados ao valuation?** Cada item material está refletido numa variável do
   valuation ou declarado como não incorporado, com a razão; o mecanismo nomeado é o que o item move de fato.
4. **Drivers acima do limiar:** cada um virou cenário ou alternativa precificada, ou a razão de não virar
   está declarada — `resultados.drivers` marca os que passam do limiar, e a decisão é do Analista.
5. **Os avisos:** cada REQUIRED DISCLOSURE é verdadeiro e esperado, e cada QUALITY WARNING do `qc.json` foi
   triado.
6. **A tese fecha:** o veredicto contra o preço de tela, a faixa, as premissas decisivas com a derivação, o
   cross-check ou a razão da ausência e o re-teste terminal dizem a mesma coisa.
7. **O leitor de mercado entende o corpo sem outro documento** — nenhum rótulo interno, e a razão de cada
   escolha numa frase econômica.

## 9. Regras invioláveis

1. A matemática de valuation vem do motor congelado; é proibido recomputar, aproximar ou reimplementar em
   prosa, Python novo ou JS novo. O único JS de valuation é o espelho verificado por paridade.
2. Paridade divergente, suíte falhando ou QC em HARD FAIL: **nada é emitido**.
3. Nenhuma escolha que a metodologia declara sem default recebe default: o Analista decide, justifica pela
   razão econômica e exibe o custo da alternativa.
4. Sem herança: nenhuma premissa, tese, pergunta, conclusão ou valuation anterior entra automaticamente.
5. Todo número material do valuation tem proveniência, reconciliação e justificativa da fonte para aquele
   claim; conflito entre fontes é registrado, nunca silenciado.
6. O builder é o único caminho de emissão, aceita uma única raiz de execução, não interpreta prosa e não busca
   dado.
7. Toda pergunta da tese é específica da companhia, falsificável e ligada a variável ou mecanismo do
   valuation.
8. Fronteira de escopo declarada: nenhum fair value por ação como conclusão principal.
9. Resposta do usuário é evidência a verificar, nunca fato.
10. O vendor é read-only; alteração local quebra a suíte, por desenho.

Desenho: `docs/desenho-arquitetura-v4.md` (§5, §6, §7, §9, §11, §12, §14 e §18).
