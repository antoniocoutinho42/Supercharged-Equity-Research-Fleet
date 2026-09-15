---
name: er-relatorio
description: >-
  USE QUANDO montar, validar ou entender o `entrega.json` da fatia v4 do
  relatório: o contrato de entrada do builder `er-relatorio`, os
  placeholders auditáveis (`{{resultados:...}}`/`{{caso:...}}`/
  `{{livre:...}}`), o QC de três níveis (HARD FAIL, REQUIRED DISCLOSURE,
  QUALITY WARNING), as três abas (Tese/Valuation/Evidência, `render.py`) ou
  a gramática de gráfico (`analise.exhibits[]` + `entrega.dados`) ou
  o CLI `builder.py` que emite `relatorio.html` + `qc.json` a partir de uma
  raiz de execução — ou recusa, nomeando a razão. Item 5 do v4, fatias 5A
  (contrato + QC + render das três abas), 5B (exhibits, uPlot e os painéis
  SVG da Valuation), 5C (laboratório), 5D (a Tese: perguntas, faixa,
  veredicto, fronteira de escopo e a aba renderizada) e 5E (o ledger
  `ledger/1` do `er-evidencia`, a proveniência dos insumos do caso, o
  consenso e o confronto), com as ondas de correção das revisões finais.
  NÃO use para o relatório de 2 abas em produção (esse é
  `er-relatorio-html`, v3); não use para rodar o valuation (`er-valuation`)
  nem para o workflow da análise (`er-analise`).
---

# er-relatorio — builder determinístico do relatório v4 (três abas)

Esta skill é a camada de apresentação do v4: consome contratos publicados
pela integração (`er-valuation`) e monta o relatório — nunca decide,
calcula ou nomeia nada que seja metodologia. Emenda **E3** do desenho
(`docs/desenho-arquitetura-v4.md` §15): o relatório não duplica nem
reimplementa valuation. Concretamente:

- **Nenhum módulo de `scripts/` (nem de um subpacote futuro) importa
  `er-valuation` nem o vendor, direto ou indireto.** Trava mecânica em
  `tests/test_relatorio_fronteira.py`, varredura recursiva: nenhum import
  proibido (nomes DERIVADOS dos arquivos reais de
  `skills/er-valuation/scripts/*.py` e `vendor/multiplos-justos/scripts/*.py`
  — um módulo novo da integração fica proibido automaticamente, sem editar
  este teste); nenhum `importlib`/`__import__`/`exec`/`eval`; nenhum literal
  de código (nem montado por concatenação) fora da constante
  `ASSETS_DA_INTEGRACAO` (`builder.py`) nomeia a integração — só
  docstring/comentário pode; nenhum asset de `skills/er-relatorio/assets/`
  tem o sha256 de um asset da integração/vendor (pega cópia/espelho).
- **`caso`/`resultados` chegam como dados, nunca por execução.** A
  correspondência entre os dois é provada por hash
  (`resultados.origem.caso_sha256` contra o JSON canônico do `caso`,
  recalculado por `entrega.sha256_canonico` — a mesma receita de
  `avaliar.py`, duplicada em três linhas de propósito) — nunca rodando o
  motor de novo.
- **Toda prosa é auditável.** Todo número de valuation citado em
  `analise` vem de um placeholder `{{resultados:...}}`/`{{caso:...}}`;
  número livre legítimo é `{{livre:...}}`; qualquer outro dígito na prosa é
  HARD FAIL (`numero_sem_proveniencia`); qualquer `{{...}}` que não seja um
  placeholder reconhecido é HARD FAIL (`placeholder_malformado`) — nenhum
  bloco malformado ganha imunidade da busca de dígito. A prosa é **uma
  lista só** (`placeholders.campos_de_prosa`): o texto da fronteira de escopo
  (`arquitetura_dominante` e `razao`), a conclusão, todo texto da Tese e, de
  cada exhibit, `pergunta`, `nota_janela`, `caption` e os textos que o gráfico
  escreve (`formula_nota` de série derivada, `rotulo` de série engine e de
  overlay). O QC a varre e o log da Evidência registra cada placeholder dela.
  Todo TEXTO que a aba Tese exibe sai dela; o resto do que a aba mostra é
  rótulo de vocabulário (catálogo ou dicionário), número de `resultados`/`caso`
  formatado, ou o nome do campo de `dados` que rotula uma série direta —
  identificador do contrato de dados (5E), fora da lista —, e um overlay sem
  `rotulo` mostra a própria `chave`.
- **Rótulo de metodologia vem sempre do catálogo, nunca de `caso` cru.** O
  cabeçalho da Valuation lê `resultados.rota` e
  `manchete.convencao_terminal` (já canonicalizados pela integração) e
  busca o rótulo em `catalogo_apresentacao.json` — nunca interpreta
  `caso...premissas.tv` nem nenhum alias.
- **HARD FAIL nunca emite.** Regra inviolável 2: se o QC acha nível
  `HARD_FAIL`, `relatorio.html` não é escrito — só `qc.json`. Todo build
  também remove `relatorio.html`/`qc.json` de uma rodada anterior na MESMA
  raiz antes de começar (desfazendo symlink, nunca seguindo) — uma recusa
  nunca deixa a saída de uma rodada anterior no lugar.

## Como rodar

```bash
python skills/er-relatorio/scripts/builder.py <raiz-de-execucao>
```

`<raiz>` contém um único `entrega.json` (contrato `entrega/1`, ver abaixo).
Códigos de saída:

| Código | Significado | O que é escrito |
|---|---|---|
| `0` | QC sem `HARD_FAIL` | `relatorio.html` + `qc.json` |
| `2` | QC achou `HARD_FAIL` | só `qc.json` |
| `1` | uso incorreto, ou `entrega.json` ausente/malformado/fora da raiz/versão incompatível/idioma sem dicionário/`execucao.ticker` divergente de `caso.ticker`, ou o contrato do ledger ilegível ou fora da forma que o relatório lê | nada |

A razão de uma recusa código `1` sai em stderr, nomeando o campo (e, para
chave desconhecida, uma sugestão por `difflib`). Regra inviolável 6: o
builder aceita uma única raiz de execução — lê só `entrega.json` dela e
escreve só dentro dela; um `entrega.json` cujo caminho resolvido (symlink
seguido) sai da raiz é recusado, nunca lido através do link; nenhuma
escrita de `relatorio.html`/`qc.json` passa através de um symlink.

## O contrato `entrega/1`

```json
{
  "versao_contrato": "entrega/1",
  "execucao": {"id": "2026-09-11-001", "ticker": "SINT3", "idioma": "pt-BR"},
  "caso": {},
  "resultados": {},
  "analise": {
    "conclusao": {"texto": "Valor justo de {{resultados:manchete.preco_acao|moeda}} por ação."},
    "faixa": {"piso": "base", "base": "base", "teto": "base"},
    "veredicto": {"texto": "O preço de tela embute um retorno sobre o capital abaixo do que a companhia sustenta."},
    "consenso": {"registros": ["consenso-ebitda-2026"]},
    "premissas_decisivas": [
      {"chave": "roic", "derivacao": "Média normalizada do retorno sobre o capital investido no ciclo."}
    ],
    "positives": [
      {"afirmacao": "A expansão da capacidade sustenta o crescimento do volume.",
       "vetor": "crescimento", "mecanismo": ["g", "crescimento_reinvestimento"],
       "observavel": "Utilização da capacidade instalada.", "incorporacao": "refletido"}
    ],
    "negatives": [
      {"afirmacao": "A entrada de um concorrente pode comprimir a margem.",
       "vetor": "rentabilidade", "mecanismo": ["roic"],
       "observavel": "Margem bruta trimestral.", "incorporacao": "nao_incorporado",
       "razao": "Sem evidência suficiente para calibrar a compressão."}
    ],
    "perguntas": [
      {"id": "moat", "tema": "moat",
       "pergunta": "A vantagem de custo resiste à entrada de um concorrente?",
       "evidencia": "Participação estável frente aos rivais do setor.",
       "observavel": "Perda de participação para um entrante.",
       "vinculo": ["roic", "n"],
       "sem_exhibit": {"razao": "Evidência qualitativa; um gráfico não acrescenta informação."}},
      {"id": "crescimento", "tema": "crescimento",
       "pergunta": "Quanto a demanda ainda comporta de expansão da capacidade?",
       "evidencia": "Carteira de pedidos acima da capacidade instalada.",
       "observavel": "Utilização da capacidade instalada.",
       "vinculo": ["g"],
       "sem_exhibit": {"razao": "A série de utilização é curta demais para um gráfico."}},
      {"id": "rentabilidade", "tema": "rentabilidade_do_crescimento",
       "pergunta": "O capital da expansão rende acima do seu custo?",
       "evidencia": "Retorno incremental das expansões recentes.",
       "observavel": "Retorno sobre o capital das novas unidades.",
       "vinculo": ["roic", "wacc"],
       "sem_exhibit": {"razao": "Evidência qualitativa; um gráfico não acrescenta informação."}}
    ],
    "riscos": [
      {"risco": "Regulação tarifária mais restritiva.", "observavel": "Decisões do regulador setorial."}
    ],
    "exhibits": []
  },
  "ledger": {
    "versao_contrato": "ledger/1",
    "registros": [
      {"id": "preco-b3", "claim": "Preço de fechamento da ação",
       "fonte": {"identidade": "B3", "classe": "api"},
       "localizador": {"tipo": "endpoint", "valor": "equity.price.historical", "parametros": {"symbol": "SINT3"}},
       "data_acesso": "2026-08-21", "periodo": "2026-08-21", "moeda": "BRL", "unidade": "R$ por ação",
       "estatuto": "reported", "valor": 55.0,
       "justificativa_da_fonte": "A bolsa é a fonte primária do preço negociado.",
       "usado_em": ["preco.valor"]},
      {"id": "roic-dfp", "claim": "Retorno sobre o capital investido normalizado",
       "fonte": {"identidade": "Demonstrações auditadas", "classe": "filing"},
       "localizador": {"tipo": "documento", "valor": "DFP de 2025, nota de capital investido"},
       "data_acesso": "2026-08-20", "periodo": "2023-2025", "moeda": null, "unidade": "pp",
       "estatuto": "calculated", "formula": "média do NOPAT sobre o capital investido, de 2023 a 2025",
       "valor": 12.0,
       "justificativa_da_fonte": "As demonstrações auditadas são a fonte do lucro e do capital da própria companhia.",
       "usado_em": ["cenarios.base.premissas.roic"]},
      {"id": "roic-release", "claim": "Retorno sobre o capital investido normalizado",
       "fonte": {"identidade": "Release de resultados", "classe": "release"},
       "localizador": {"tipo": "documento", "valor": "Release do quarto trimestre de 2025"},
       "data_acesso": "2026-08-20", "periodo": "2023-2025", "moeda": null, "unidade": "pp",
       "estatuto": "reported", "valor": 12.0,
       "justificativa_da_fonte": "A companhia publica o indicador com a mesma definição, por outra via.",
       "contraprova_de": "roic-dfp"},
      {"id": "consenso-ebitda-2026", "claim": "Consenso de EBITDA",
       "fonte": {"identidade": "Provedor de consenso", "classe": "api"},
       "localizador": {"tipo": "endpoint", "valor": "equity.estimates.consensus", "parametros": {"symbol": "SINT3"}},
       "data_acesso": "2026-08-21", "periodo": "2026E", "moeda": "BRL", "unidade": "R$ milhões",
       "estatuto": "reported", "valor": 1100.0,
       "justificativa_da_fonte": "A expectativa de mercado vem do consenso dos analistas que cobrem a companhia."}
    ],
    "lacunas": [
      {"id": "segmentos", "descricao": "A companhia não publica a abertura da receita por segmento.",
       "materialidade": "nao_material", "tratamento": "A análise usa o consolidado, e a limitação fica declarada."}
    ]
  }
}
```

Vocabulário fechado em todo nível que este contrato define (topo,
`execucao`, `analise` e cada bloco da Tese, `analise.conclusao`,
`analise.exhibits[]` e cada série/overlay, `dados.<id>`) — chave desconhecida
é recusada pelo nome, com sugestão. `caso` e `resultados` são opacos: este
módulo só confirma que são objetos, que `resultados.versao_contrato` é
`"resultados/1"` e que `resultados.fronteira_de_escopo` está presente (é ele
que decide se `analise.faixa` é exigida) — o conteúdo pertence ao contrato de
`er-valuation`, nunca revalidado aqui. Exceção pontual: quando `caso` declara
um `ticker`, ele tem de bater com `execucao.ticker` (identidade da empresa que
o título da página nomeia e a que o valuation avaliou). `execucao.idioma`
precisa ter dicionário em `assets/i18n/<idioma>.json`. O `ledger` tem a forma
do contrato `ledger/1` do `er-evidencia`, e `analise.consenso` é obrigatório (ver
"O ledger, o consenso e o confronto"); `ficha_tecnica` não faz parte do
contrato — uma entrega que a declare é recusada. Produzir a entrega em produção
é `er-analise` (item 8); por ora, `tests/relatorio_apoio.py` monta raízes de
teste rodando `avaliar()` de verdade sobre uma fixture de caso, com uma Tese
válida, a reversa onde o gate a admite, e o ledger e o consenso derivados do
mapa dos insumos do caso. No exemplo acima, o teste que o executa troca `caso` e
`resultados` pelos de uma fixture e completa o ledger só com os insumos do caso
real que o exemplo não nomeia.

## A Tese (`analise`, fatia 5D)

A Tese é declaração do analista, com vocabulário fechado em todo nível. A
**forma** abaixo é recusa de contrato (`RC=1`, nomeando o campo, com sugestão);
o **conteúdo** — o que depende do catálogo e dos números publicados — é QC
(`RC=2`, ver a tabela de QC).

| Nível | Chaves | Forma |
|---|---|---|
| `analise` | `conclusao`, `exhibits`, `veredicto`, `premissas_decisivas`, `positives`, `negatives`, `perguntas`, `riscos` obrigatórias; `faixa` obrigatória **fora** da fronteira de escopo; `visao_nao_consensual`, `mudou_desde_analise_fornecida` opcionais | sob fronteira, `faixa` declarada passa na forma e é o HARD FAIL `fronteira_com_preco_alvo` |
| `faixa` | `piso`, `base`, `teto` | cada um o NOME de um cenário de `resultados.cenarios` — o número vem de lá, nunca do analista |
| `veredicto` | `texto` | o preço de tela, a data e a fonte vêm de `caso.preco` |
| `premissas_decisivas[]` | `chave`, `derivacao` | `chave`: premissa da rota no catálogo, declarada no cenário da manchete (QC) |
| `positives[]`, `negatives[]` | `afirmacao`, `vetor`, `mecanismo`, `observavel`, `incorporacao` obrigatórias; `razao` | `vetor` ∈ `crescimento`, `moat`, `rentabilidade`, `risco`, `earning_power`, `valuation`; `mecanismo` lista não vazia; `incorporacao` ∈ `refletido`, `nao_incorporado` — este exige `razao` |
| `perguntas[]` | `id`, `tema`, `pergunta`, `evidencia`, `observavel`, `vinculo` obrigatórias; `exhibits` **ou** `sem_exhibit` | `tema` ∈ `moat`, `crescimento`, `rentabilidade_do_crescimento`, `especifica`; `id` único; `vinculo` lista não vazia; `exhibits` cita ids de `analise.exhibits`; `sem_exhibit` é `{"razao": ...}`; nunca os dois, nunca nenhum |
| `riscos[]` | `risco`, `observavel` | |
| `visao_nao_consensual` | `texto` | |
| `mudou_desde_analise_fornecida` | `linhas` | de uma a três linhas |

**O vínculo mora só na pergunta:** `vinculo` (e o `mecanismo` de um Positive ou
Negative) aponta para premissas da rota (`catalogo.premissas.<rota>`) ou blocos
econômicos (`catalogo.blocos`) — o vocabulário vem do catálogo, nunca deste
skill. Um exhibit não declara vínculo. Todo campo de texto da Tese — e, de cada
exhibit, que a aba desenha sob as perguntas, `pergunta`, `nota_janela`,
`caption` e os textos que o gráfico escreve (`formula_nota`, o `rotulo` da série
`engine` e o do overlay), além do texto da fronteira de escopo que a Conclusão
exibe — passa pelos placeholders auditáveis, como a conclusão. A Análise exige a reversa
(`resultados.reversa`); quando o caso a torna impossível, a integração publica a
limitação em `resultados.limitacoes`, e o catálogo declara o bloco que ela
suprime (`catalogo.limitacoes.<chave>.afeta`) — a entrega sai com o disclosure,
nunca calada.

**`analise.exhibits` é OBRIGATÓRIO** (fatia 5B): uma análise sem gráfico
nenhum declara `[]` **em voz alta**, como o `cenario_base` já faz — nunca
por omissão. Uma entrega sem essa chave sai com `RC=1` (`campo obrigatório
ausente em 'analise': 'exhibits'`). `dados` é o único campo de topo
OPCIONAL: uma análise cujos exhibits são todos `engine` (leem `resultados`
direto) não precisa de dataset nenhum.

## O ledger, o consenso e o confronto (fatia 5E)

O **ledger** tem a forma do contrato `ledger/1`, que é do `er-evidencia` (§3.2 do
desenho) e mora em `skills/er-evidencia/assets/contrato_ledger.json`. O builder o
lê por `ASSETS_DA_INTEGRACAO["contrato_ledger"]` e valida a entrega contra ele —
nunca contra uma cópia neste skill. As chaves aceitas e obrigatórias de cada nível
e os vocabulários fechados vêm do contrato; este skill confere os tipos. A forma é
recusa de contrato (`RC=1`, nomeando o campo, com sugestão); o conteúdo é QC.

| Nível | Forma |
|---|---|
| `ledger` | `versao_contrato` (a do contrato, `"ledger/1"`), `registros`, `lacunas` |
| `ledger.registros[]` | `id` (único), `claim`, `periodo`, `unidade` e `justificativa_da_fonte`, textos; `fonte`; `localizador`; `data_acesso` em `AAAA-MM-DD`; `moeda`, texto ou `null`; `estatuto`, do vocabulário do contrato; `valor`, número ou `null` (booleano não é número); `formula` **se e só se** o estatuto declara `exige_formula`, e `insumos` (ids) só nesse caso; `usado_em` (caminhos do caso, com o índice de lista como segmento) exige `valor` numérico; `reconciliacao`, `conflito` e `contraprova_de` (um id) opcionais |
| `fonte` | `identidade` (texto) e `classe` (vocabulário `classes_de_fonte`) |
| `localizador` | `tipo` (vocabulário `tipos_de_localizador`), `valor` (texto) e `parametros` (objeto, opcional) |
| `reconciliacao` | `texto` |
| `conflito` | `vencedor` (um id) e `razao` |
| `ledger.lacunas[]` | `id` (único), `descricao`, `materialidade` (vocabulário do contrato) e `tratamento` |
| `analise.consenso` | `{"registros": [ids]}` **ou** `{"ausente": {"ancora", "razao"}}`, nunca os dois; `ancora` do vocabulário `ancoras_do_consenso` |
| `confronto` (opcional, na raiz) | `analise_fornecida` (`identificacao`, `data` em `AAAA-MM-DD`) e `divergencias[]` (`item`, `classificacao` ∈ `dado_novo`, `premissa_revista`, `erro_anterior`, `pergunta_resolvida`, `anterior`, `atual`, `explicacao`); `analise.mudou_desde_analise_fornecida` exige o confronto |
| `dados.<id>.ledger` | lista dos ids dos registros que sustentam o dataset |

**Quais números exigem proveniência é declaração da integração:** o mapa
`catalogo.insumos_do_caso`, com a gramática de `conclusoes_de_valor`. Cada folha
numérica do caso que ele cobre precisa de um registro cujo `usado_em` a nomeie,
com o mesmo número. **A doutrina de evidência é do contrato:** estimativa, fórmula
e lacuna que vira disclosure saem das flags `e_estimativa`, `exige_formula` e
`exige_disclosure`, nunca do nome de um estatuto ou de uma materialidade. **Prosa
e dado:** a `descricao` e o `tratamento` de uma lacuna e a `razao` do consenso
ausente são prosa auditável da Tese (lista de prosa); os demais textos do ledger e
os do confronto são dado da Evidência (§9) e podem citar números. A **ficha
técnica** não é declarada: é da execução, e a Evidência a mostra vazia até o
builder compô-la.

## Placeholders auditáveis (A7)

`{{resultados:<caminho>|<formato>}}`, `{{caso:<caminho>|<formato>}}`,
`{{livre:<texto>}}` — reconhecidos mesmo quando quebrados por uma quebra de
linha. `<caminho>` é pontuado, com índice de lista como segmento numérico
(`cenarios.base.valor.preco_acao`). Formatos: `num0`–`num4` (casas
decimais, verbatim); `pct0`–`pct2` (`valor x 100`, `valor` é FRAÇÃO);
`pp0`–`pp2` (verbatim, `valor` já em PONTOS PERCENTUAIS — nunca
multiplicado de novo); `x1`/`x2` (múltiplo, sufixo `x`); `moeda` (2 casas,
símbolo do dicionário para o código antes do hífen de `caso.moeda` —
`"BRL-nominal"` → `"BRL"` → `"R$"`; código sem símbolo declarado usa o
próprio código ISO como prefixo, nunca levanta erro). pt-BR: milhar `.`,
decimal `,` — sem o módulo `locale` (§16.1), determinístico por construção.

Um placeholder que não resolve (caminho inexistente, valor não numérico,
formato desconhecido) fica LITERAL no texto e vira `placeholder_nao_
resolvido` (QC); um `{{...}}` que não é um placeholder reconhecido (fonte
fora do vocabulário, maiúscula, sem `|formato`) é `placeholder_malformado`;
o formato pedido tem de casar com a unidade do valor (`formato_incompativel_
com_unidade` — uma premissa em `pp` só aceita `pp*`/`num*`, `moeda` só
`moeda`/`num*`, `anos` só `num0`; um caminho de `resultados` terminado em
`_%` só aceita `pp*`, `upside` só `pct*`). Nunca uma exceção que derruba o
processo, nunca um valor inventado.

## A gramática de exhibits (`analise.exhibits[]` + `entrega.dados`)

A §10 do desenho, como contrato. **Uma spec de exhibit nunca declara número
nenhum** — ela diz DE ONDE o número vem, e o builder o lê:

```json
"dados": {
  "fin": {"ledger": ["dfp-2021-2024"], "x": ["2021", "2022", "2023", "2024"],
          "campos": {"receita": [100.0, 110.0, 120.0, 130.0],
                     "ebitda": [20.0, 23.0, 27.0, 31.0]}}
},
"ledger": {
  "versao_contrato": "ledger/1",
  "registros": [
    {"id": "dfp-2021-2024", "claim": "Receita e EBITDA anuais",
     "fonte": {"identidade": "Demonstrações auditadas", "classe": "filing"},
     "localizador": {"tipo": "documento", "valor": "DFPs de 2021 a 2024, demonstração do resultado"},
     "data_acesso": "2026-08-20", "periodo": "2021-2024", "moeda": "BRL", "unidade": "R$ milhões",
     "estatuto": "reported", "valor": null,
     "justificativa_da_fonte": "As demonstrações auditadas são a fonte primária do resultado histórico."}
  ],
  "lacunas": []
},
"analise": {
  "exhibits": [{
    "id": "margem",
    "pergunta": "Como a margem EBITDA evoluiu no período?",
    "tipo": "linha",
    "series": [
      {"derivacao": "direta",   "fonte": "fin.receita"},
      {"derivacao": "derivada", "fonte": "fin", "formula": "ebitda / receita",
       "formula_nota": "margem EBITDA"},
      {"derivacao": "engine",   "chave": "resultados:manchete.preco_acao",
       "rotulo": "preço justo da manchete"}
    ],
    "overlays": [{"chave": "resultados:manchete.preco_acao", "rotulo": "preço justo"}],
    "nota_janela": "só os últimos {{livre:4}} anos têm dado comparável",
    "caption": "fonte: demonstrações auditadas"
  }]
}
```

| Nível | Chaves | Notas |
|---|---|---|
| `dados.<id>` | `ledger`, `x`, `campos` — todas obrigatórias | `x` é o eixo (número ou texto); `campos.<nome>` é uma lista paralela a `x`; `ledger` é a lista dos ids dos registros do ledger que sustentam o dataset — um dataset usado por série `direta` ou `derivada` sem nenhum é `dataset_sem_proveniencia` |
| `analise.exhibits[]` | `id`, `pergunta`, `tipo`, `series` obrigatórias; `overlays`, `nota_janela`, `caption` opcionais | `id` único; `tipo` ∈ `linha`, `barras`, `area`, `empilhado`, `dispersao`, `tabela`; o exhibit não declara vínculo (5D, D5) — a pergunta da tese que ele responde o cita em `perguntas[].exhibits`, e ele é desenhado sob ela; `pergunta`, `nota_janela` e `caption` são prosa auditável (dígito só por placeholder) |
| série `direta` | `derivacao`, `fonte` (`"<dataset>.<campo>"`) | o campo, verbatim; `null` é ponto ausente legítimo (travessão no gráfico) |
| série `derivada` | `derivacao`, `fonte` (**só o id do dataset**), `formula`, `formula_nota` | fórmula fechada: `+ - * /`, menos unário, parênteses, número e nome de campo do MESMO dataset — nunca `eval`; `formula_nota` é prosa auditável (o gráfico a escreve na legenda) |
| série `engine` | `derivacao`, `chave` (`"resultados:<caminho>"`), `rotulo` | tem de resolver num **número finito** ou lista deles; `rotulo` é obrigatório e é prosa auditável — o gráfico o escreve na legenda e no cabeçalho da tabela, nunca a chave crua |
| overlay | `chave` (`"resultados:<caminho>"`/`"caso:<caminho>"`) obrigatória; `rotulo` opcional | linha horizontal: um único número finito; `rotulo`, quando declarado, é prosa auditável (sem ele, a legenda mostra a `chave`) |

`waterfall` e `matriz` **não são tipos de exhibit** (são vocabulário
reservado, `exhibits.TIPOS_PROPRIOS`): os dois existem como **painéis** da
aba Valuation, alimentados direto por `resultados.ponte` e
`resultados.sensibilidades.grades_2d` — a spec resolvida de um exhibit
(`eixoX` + séries de números) não expressa `{rotulo, valor, sinal}` nem uma
grade de dois eixos. Declarar `tipo: "waterfall"` é recusa de contrato
(`RC=1`).

Todo número desenhado é formatado pela **unidade que o contrato declara**
(`catalogo.unidades`): a célula de uma matriz usa a `unidade` que o motor
publica na grade, e cada eixo usa a `unidade` da premissa no catálogo. O
relatório não decora casa decimal nenhuma — unidade fora do vocabulário do
catálogo é HARD FAIL (`unidade_desconhecida`).

## QC de três níveis (A8)

`HARD_FAIL` (não emite), `REQUIRED_DISCLOSURE` (visível no HTML),
`QUALITY_WARNING` (só em `qc.json`). Regras:

| Código | Nível | Gatilho |
|---|---|---|
| `resultados_nao_correspondem_ao_caso` | HARD FAIL | hash do `caso` ≠ `resultados.origem.caso_sha256` |
| `placeholder_nao_resolvido` | HARD FAIL | caminho inexistente ou valor não numérico |
| `placeholder_malformado` | HARD FAIL | `{{...}}` que não é um placeholder reconhecido |
| `numero_sem_proveniencia` | HARD FAIL | dígito na prosa de `analise` fora de placeholder |
| `diagnostico_sem_chave` | HARD FAIL | `diagnosticos_chaves`/`diagnosticos_unicos_chaves` ausente, com comprimento diferente do `diagnosticos`/`diagnosticos_unicos` correspondente, ou com `null` num item — em QUALQUER par publicado em `resultados.json` (varredura recursiva); ou `degrau.diagnosticos_chaves` ausente num cenário com degrau |
| `degrau_sem_divergencia_de_base` | HARD FAIL | cenário com `degrau` sem `divergencia_de_base_%` numérico |
| `formato_incompativel_com_unidade` | HARD FAIL | formato de placeholder não bate com a unidade do valor |
| `multiplos_com_bases_diferentes` | HARD FAIL | `manchete.multiplo.base` ≠ `mercado_tela.base` |
| `unidade_desconhecida` | HARD FAIL | `unidade` de uma grade 2D fora de `catalogo.unidades` |
| `serie_nao_rastreavel` | HARD FAIL | `fonte`/`chave` de série que não resolve, ou série `engine` que resolve em algo que não é número finito |
| `formula_invalida` | HARD FAIL | fórmula fora da gramática fechada, nome fora do dataset, campos de comprimentos diferentes, `null`/não-finito num campo lido, divisão por zero |
| `serie_de_tamanho_incompativel` | HARD FAIL | série com comprimento diferente do `x` do seu dataset |
| `series_de_datasets_incompativeis` | HARD FAIL | duas séries do mesmo exhibit vindas de datasets cujo `x` difere |
| `overlay_nao_resolvido` | HARD FAIL | `chave` de overlay que não resolve num número finito |
| `relatorio_nao_autocontido` | HARD FAIL | referência (`src`/`href`/`srcset`/`data`/`url()`/`@import`) que não é `#fragmento` nem URI `data:`; ou, no miolo de um `<script>`, chamada de rede (`fetch`, `XMLHttpRequest`, `WebSocket`, `Worker`, `importScripts`, `EventSource`, `sendBeacon`) ou atribuição de `src`/`srcset`/`href` a um endereço externo |
| `perguntas_da_tese_incompletas` | HARD FAIL | menos de 3 ou mais de 5 perguntas; tema obrigatório (`moat`, `crescimento`, `rentabilidade_do_crescimento`) ausente ou repetido; mais de 2 perguntas `especifica` (§7) |
| `vinculo_fora_do_vocabulario` | HARD FAIL | item de `perguntas[].vinculo` ou de `positives`/`negatives[].mecanismo` que não é premissa da rota (`catalogo.premissas.<rota>`) nem bloco econômico (`catalogo.blocos`) |
| `premissa_decisiva_fora_do_cenario` | HARD FAIL | `premissas_decisivas[].chave` que não é premissa da rota no catálogo declarada no cenário da manchete |
| `faixa_fora_de_ordem` | HARD FAIL | ponta da faixa que não nomeia um cenário publicado com preço; preço de `piso` acima do de `base`, ou de `base` acima do de `teto`; `base` diferente do cenário da manchete |
| `fronteira_com_preco_alvo` | HARD FAIL | sob `resultados.fronteira_de_escopo`: `faixa` declarada, ou um número que a integração declara conclusão de valor (`catalogo.conclusoes_de_valor`) chegando à Tese por um dos três lugares — placeholder `resultados:` num texto da lista de prosa, `chave` de série `engine` ou `chave` de overlay; o achado nomeia o lugar, o caminho e a unidade da família. A decisão lê o mapa, nunca o nome do campo; o preço e o múltiplo de tela não estão nele e continuam permitidos, e `livre:` fica fora |
| `fronteira_de_escopo_desconhecida` | HARD FAIL | sob fronteira de escopo, o catálogo não rotula a classe no idioma da entrega ou não publica `conclusoes_de_valor` — sem o mapa nenhum número de valor seria reconhecido, e a regra falha fechada |
| `analise_sem_reversa` | HARD FAIL | `resultados.reversa` ausente sem nenhuma limitação publicada que o catálogo declare com `afeta: "reversa"` — a decisão lê a declaração, nunca o nome da chave |
| `limitacao_desconhecida` | HARD FAIL | chave de `resultados.limitacoes` que o catálogo não declara com rótulo no idioma e com `afeta` |
| `insumo_sem_proveniencia` | HARD FAIL | folha numérica do caso que `catalogo.insumos_do_caso` cobre sem registro do ledger cujo `usado_em` a nomeie — booleano não é folha numérica, e o índice de lista é segmento |
| `usado_em_fora_dos_insumos` | HARD FAIL | caminho de `usado_em` que não nomeia uma folha numérica do caso coberta pelo mapa: o caso não tem esse número, ou ele não é insumo |
| `insumo_nao_reconciliado` | HARD FAIL | `valor` do registro diferente do número do caso naquele caminho (`math.isclose` com `qc.TOLERANCIA_RELATIVA_DE_RECONCILIACAO` e `qc.TOLERANCIA_ABSOLUTA_DE_RECONCILIACAO`), sem `reconciliacao` |
| `conflito_de_fontes_silenciado` | HARD FAIL | registros do mesmo `claim` e `periodo`, com `valor` numérico e algum par fora da mesma tolerância, sem nenhum deles declarar `conflito.vencedor` dentre os ids do grupo — um achado por grupo |
| `referencia_fora_do_ledger` | HARD FAIL | id que o ledger não tem, citado em `insumos`, `conflito.vencedor`, `contraprova_de`, `analise.consenso.registros` ou `dados.<id>.ledger` |
| `dataset_sem_proveniencia` | HARD FAIL | dataset usado por série `direta` ou `derivada` com `ledger` vazio |
| `insumos_do_caso_desconhecidos` | HARD FAIL | o catálogo não publica `insumos_do_caso` na forma do contrato — sem o mapa nenhum insumo seria exigido, e as regras de proveniência falham fechadas |
| `divergencia_de_base_degrau` | REQUIRED DISCLOSURE | a integração publicou, em `degrau.diagnosticos_chaves`, a chave que `catalogo.disclosures.divergencia_de_base_degrau.chave` nomeia — o limiar é da integração, e o relatório não compara limiar nenhum; a mensagem imprime o `divergencia_de_base_%` publicado |
| `limitacao_metodologica` | REQUIRED DISCLOSURE | cada limitação publicada em `resultados.limitacoes`, com o rótulo do catálogo — hoje, a razão de a Análise sair sem a reversa (`caso_degrau`, rota `rampa`) |
| `fronteira_de_escopo_declarada` | REQUIRED DISCLOSURE | sob `resultados.fronteira_de_escopo`: a limitação de escopo da §11, com o rótulo que o catálogo dá à classe — o bloco de avisos da Tese nunca diz "nenhum aviso" sob fronteira |
| `insumo_estimado` | REQUIRED DISCLOSURE | registro cujo estatuto declara `e_estimativa` e cujo `usado_em` nomeia insumo do caso — com o `claim` |
| `sem_contraprova_independente` | REQUIRED DISCLOSURE | premissa decisiva cujo número no caso (`cenarios.<manchete.cenario>.premissas.<chave>`) não tem registro com `contraprova_de` apontando para um registro que o sustenta, vindo de outra `fonte.identidade` e com o mesmo `valor` dele (pela tolerância da reconciliação) ou com `reconciliacao` declarada — a mesma identidade não conta, e uma fonte que diverge sem reconciliação não confirma; com o rótulo da premissa no catálogo |
| `lacuna_material` | REQUIRED DISCLOSURE | lacuna cuja materialidade declara `exige_disclosure` — com a `descricao` e o `tratamento`, e o campo de cada um na lista de prosa (`params.campos_de_prosa`) |
| `consenso_indisponivel` | REQUIRED DISCLOSURE | `analise.consenso.ausente` — com a âncora substituta, a razão e o campo dela na lista de prosa; sem consenso, o confronto temporal da reversa fica indisponível |
| `serie_curta_sem_nota_janela` | QUALITY WARNING | série com menos de 10 pontos e exhibit sem `nota_janela` |
| `tese_dependente_de_uma_premissa` | QUALITY WARNING | todas as perguntas com o mesmo `vinculo` de um item só |
| `concentracao_de_fontes` | QUALITY WARNING | uma `fonte.identidade` sustenta mais de `qc.LIMIAR_DE_CONCENTRACAO_DE_FONTES` (metade) dos insumos do caso, quando há ao menos `qc.MINIMO_DE_INSUMOS_PARA_CONCENTRACAO` (quatro) |

Mensagem de cada achado vem de `assets/i18n/<idioma>.json` (`qc.<codigo>`,
`params` substituídos) — nunca hardcoded (§16.1); o "porquê" metodológico de
`divergencia_de_base_degrau` vem do catálogo
(`catalogo.disclosures.divergencia_de_base_degrau.texto`), e o de
`limitacao_metodologica` também (`catalogo.limitacoes.<chave>.rotulo`) —
nunca do dicionário do relatório. `qc.json` sai sempre, em ordem determinística,
mesmo quando o builder recusa emitir o HTML.

## As três abas (`render.py`)

**Tese** (fatia 5D) — a decisão de investimento, nesta ordem:

1. **Conclusão**: o texto da conclusão; a faixa piso–base–teto, cada ponta com
   o preço que `resultados.cenarios.<nome>.valor.preco_acao` publica e o nome
   do cenário; o veredicto, com o preço de tela, a data e a fonte de
   `caso.preco`; e o múltiplo justo ao lado do de tela. Num caso SOTP
   (`resultados.manchete.fonte` igual a `sotp`) a faixa sai rotulada como a
   dos cenários consolidados, nomeando o preço da soma das partes — que
   continua sendo a manchete. **Sob fronteira de escopo** o título é
   "conclusão condicional, sem preço-alvo", com a classe (rótulo do
   catálogo), a arquitetura dominante e a razão que
   `resultados.fronteira_de_escopo` publica — prosa auditável, que sai da
   lista de prosa —, nenhuma faixa e, da dupla de
   múltiplos, só o de tela: todo número que a integração declara conclusão de
   valor (`catalogo.conclusoes_de_valor`) fica fora da Conclusão;
2. avisos obrigatórios (todo REQUIRED DISCLOSURE — sob fronteira de escopo,
   a limitação de escopo com o rótulo da classe, nunca "nenhum aviso");
3. premissas decisivas: o rótulo do catálogo, o número do cenário da manchete
   formatado pela unidade do catálogo e a derivação. Num caso SOTP a seção sai
   rotulada como a do cenário consolidado (dicionário, sem número): as partes
   que formam a manchete usam premissas próprias, e a premissa por parte é da 5F;
4. o que mudou desde a análise fornecida, se declarado;
5. Positives e Negatives: a afirmação, o vetor, o que move no valuation, o
   observável, e se está refletido ou não incorporado (com a razão);
6. as perguntas da tese: tema, pergunta, evidência, observável e vínculo — e
   **os exhibits que ela cita, desenhados ali**, na ordem citada, ou a razão
   de não ter nenhum;
7. riscos, cada um com o observável;
8. visão não-consensual, se declarada;
9. os exhibits que nenhuma pergunta cita, se houver.

Vínculo, mecanismo, premissa e classe de fronteira saem pelo rótulo do
catálogo; tema, vetor, incorporação e papel da faixa, pelo dicionário — nunca
a chave crua. Todo texto de `analise` sai de `placeholders.resolver_prosa`: um
campo que o render tentasse exibir fora da lista de prosa é
`ProsaNaoAuditada` (`RC=1`). Cada host de gráfico carrega o índice da sua
spec no payload (`data-exhibit-indice`), e o bootstrap pareia host e spec por
esse índice, nunca pela posição no DOM — o mesmo exhibit pode aparecer sob
duas perguntas.

**Valuation** — preço justo, upside, múltiplo justo pareado com o de tela pela
mesma base, rota e convenção terminal — do catálogo, nunca de `caso` cru —,
preço por cenário quando houver mais de um, os painéis SVG (o waterfall da
ponte e uma matriz por grade 2D, cujo título nomeia o cenário que a grade
perturbou) e o laboratório; SOTP mostra só preço/upside, sem rota/convenção
única. **Sob fronteira de escopo**, todo número que o mapa da integração declara
conclusão de valor sai com o rótulo condicional do dicionário
(`valuation.condicional`): o preço e o upside do cabeçalho, o múltiplo justo, o
título da lista por cenário, as três saídas de cada cenário do laboratório e o
título da matriz. A decisão é uma só (`render._leitura_condicional`): quem exibe
o número diz o caminho que lê em `resultados`, e o mapa responde — nenhum nome
de campo decide.

**Evidência** — metodologia, ficha técnica (vazia até o builder compô-la: a
ficha é da execução e saiu do contrato na fatia 5E), o log de resolução de
**todo** placeholder da prosa (conclusão, textos da Tese, do consenso ausente,
das lacunas e dos exhibits) e a rastreabilidade série a série dos exhibits.

`assets/template.html` é a casca estática — CSS e JS
100% inline, nenhum `src`/`href`/`url()`/`@import` que não seja
`#fragmento` ou `data:`. Toda string de interface vem do dicionário
(`t()`), todo rótulo de rota/convenção terminal/múltiplo/linha da
ponte/premissa vem do catálogo —
chave ausente é `ChaveDeInterfaceAusente`/`RotuloDoCatalogoAusente`,
nomeada, nunca um código cru na tela; campo de `caso`/`resultados` que um
painel desenha e não está lá é `CampoDeContratoAusente` (`RC=1`, nomeando o
caminho), nunca um `KeyError` cru.

## Módulos

| Arquivo | Responsabilidade |
|---|---|
| `scripts/entrega.py` | Contrato de `entrega.json`: carrega, valida, recusa; `sha256_canonico`; identidade de ticker; a leitura do contrato `ledger/1` (`ler_contrato_do_ledger`), contra o qual valida o ledger, o consenso e o confronto |
| `scripts/exhibits.py` | Contrato de `analise.exhibits`/`entrega.dados`; avaliador fechado da fórmula (`ast`, nunca `eval`); resolve série/overlay em número e produz o log de rastreabilidade |
| `scripts/placeholders.py` | Resolve `{{...}}`; formata número por idioma (sem `locale`); publica a RECEITA de formatação que o JS aplica; a lista única da prosa auditável (`campos_de_prosa`/`resolver_prosa`), que o QC, o log da Evidência e a aba Tese leem; e o leitor do mapa das conclusões de valor (`conclusoes_de_valor`/`conclusao_de_valor`), que o QC e a tela consultam sob fronteira de escopo; e o do mapa dos insumos do caso (`insumos_do_caso`/`insumo_do_caso`), com o mesmo casador de padrão, que o QC consulta para exigir proveniência |
| `scripts/qc.py` | Achados estruturados dos três níveis |
| `scripts/render.py` | Compõe as três abas do HTML a partir de `entrega`/`catalogo`/achados; embute o payload dos exhibits e dos painéis |
| `scripts/builder.py` | CLI: orquestra, limpa saída anterior, resolve mensagem do dicionário, decide o exit code |

| Asset | Papel |
|---|---|
| `assets/template.html` | Casca estática das três abas + bootstrap que entrega o payload aos módulos JS, pareando cada gráfico ao seu host pelo índice (`data-exhibit-indice`) |
| `assets/graficos.js` | Adaptador fino sobre o uPlot: desenha os cinco cartesianos e a `tabela` a partir da spec já resolvida |
| `assets/svg.js` | Os dois painéis NÃO-cartesianos (waterfall da ponte, matriz de sensibilidade) como string SVG pura |
| `assets/uPlot.iife.min.js` / `.min.css` / `.LICENSE` | uPlot v1.6.27 vendorizado byte a byte, embutido só quando há exhibit |
| `assets/i18n/<idioma>.json` | Toda string de interface e toda mensagem de QC |

## Metodologia

Não está aqui e não é resumida aqui. Todo conhecimento metodológico que
este relatório precisa exibir (bloco/unidade/rótulo de premissa, rótulo e
base de múltiplo, rótulo de convenção terminal, severidade e rótulo de
diagnóstico, texto do disclosure de divergência de base e a chave que o
dispara, o vocabulário de vínculo das perguntas da tese — premissas da rota e
blocos econômicos —, o rótulo e o bloco suprimido, `afeta`, de cada
limitação, o mapa das conclusões de valor — quais números de `resultados`,
em que unidade, são leitura condicional sob fronteira de escopo — e o mapa dos
insumos do caso — quais números do caso exigem proveniência) vem de
`skills/er-valuation/assets/catalogo_apresentacao.json` — lido via
`ASSETS_DA_INTEGRACAO`, nunca hardcoded aqui. A doutrina de evidência que o QC
aplica — classes de fonte, estatutos, materialidades, âncoras do consenso e as
flags que decidem estimativa, fórmula e lacuna que vira disclosure — vem do
contrato `ledger/1` do `er-evidencia`
(`skills/er-evidencia/assets/contrato_ledger.json`), pela mesma constante. A fonte canônica da
metodologia é `skills/er-multiplos-justos/SKILL.md`; da orquestração,
`skills/er-valuation/SKILL.md`. Desenho: `docs/desenho-arquitetura-v4.md`.
