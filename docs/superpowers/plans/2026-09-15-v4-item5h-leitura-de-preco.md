# Item 5, fatia H — o produto Leitura de preço, o nível implícito e o confronto temporal

**Goal.** Fechar os dois produtos da §5. A análise ganha o nível implícito da métrica-base com o confronto temporal
contra o consenso, e a entrega passa a existir também como **Leitura de preço**, reduzida à aba Valuation.

**Regime (15/09).** Implementar o que o desenho pede, sem abstração preventiva nem escopo novo. Um teste que
discrimina cada regra ou número novo; nada de mutation test nem fixture nova (variantes compostas no apoio). Duas
tasks, um commit por task, a suíte inteira uma vez no fim e uma checagem de blockers.

**E3.** O nível implícito é conta do motor (`justos.nivel_implicito`, subcomando `nivel`); o wrapper o roda e
publica. O relatório nunca lê a prosa do motor: a leitura vem por chave, rotulada pelo catálogo.

**Fontes.** Desenho §5 (os dois produtos; "entrega reduzida à aba Valuation"), §9, §11, §14 e §18. Vendor:
`references/aplicacao.md` §4 (menu de reconciliação e confronto temporal) e `scripts/justos.py`
(`nivel_implicito`, linhas 957–1000).

## Decisões

- **D1 — o consenso da reversa é declarado no caso.** `reversa.consenso: {t1: {valor, periodo}, t2?: {valor,
  periodo}}`, opcional, com o valor na mesma métrica da base. Os dois valores são insumo com proveniência. O
  wrapper nunca lê o ledger.
- **D2 — o wrapper roda o `nivel`** com o valor de mercado (a conta de `reversa.alvo_de_mercado`) e o múltiplo
  justo corrente do cenário da reversa, mais o consenso declarado, e publica `reversa.nivel_implicito` com a saída
  do motor íntegra e a `leitura_chave` extraída do prefixo da prosa (`antecipacao_temporal`, `acima_do_consenso`)
  ou `null` sem consenso. É o padrão do degrau: chave classificada na integração, prosa nunca exibida.
- **D3 — o produto é declarado na execução.** `execucao.produto` em `{analise, leitura_de_preco}`, opcional, com
  `analise` como default — a §5 manda escolher Análise na dúvida.
- **D4 — sob `leitura_de_preco`:**
  - a entrega sai **só com a aba Valuation** (§5, literal). A Tese e a Evidência não são compostas, e a navegação
    tem uma aba só;
  - a **reversa é obrigatória**: nenhuma limitação publicada a dispensa, e sem ela é HARD FAIL. O código é o
    `analise_sem_reversa` que já existe, com a mensagem dizendo qual produto a exige;
  - os **avisos obrigatórios** sobem para o topo da aba;
  - as **conclusões de valor saem como leitura condicional**, pelo mesmo `render._leitura_condicional` da fronteira
    de escopo, com o produto como segundo gatilho, e não há preço-alvo de manchete;
  - um **banner do produto** declara o escopo: cobertura e encerramento não se aplicam.
- **D5 — o que a análise continua exigindo** não muda sob `leitura_de_preco`: os blocos da Tese ficam opcionais, sem
  regra nova que os proíba. Exigir o que cada produto pede é trabalho do `er-analise` (item 8) — fica como dívida.

## Números novos a classificar

- **Não são conclusão de valor:** todo `reversa.nivel_implicito.*` — nível da métrica-base, fator, degrau implícito
  e razões contra o consenso são leitura do preço, não preço.
- **Insumos do caso:** `reversa.consenso.t1.valor` e `reversa.consenso.t2.valor`.

---

## Task 1: o nível implícito, na integração

**Arquivos:** `skills/er-valuation/scripts/caso.py`, `reversa.py` e `avaliar.py`;
`assets/catalogo_apresentacao.json`; `skills/er-valuation/SKILL.md`; `tests/relatorio_apoio.py` (variante
`consenso`); `tests/test_valuation_caso.py`, `test_valuation_reversa.py`, `test_valuation_contrato.py`,
`test_valuation_matriz.py`, `test_catalogo_apresentacao.py`.

**Produz:**
- **No caso:** `reversa.consenso`, na forma de D1.
- **Em `resultados`:** `reversa.nivel_implicito: {metrica_base_atual, metrica_base_implicita, fator_k_implicito,
  degrau_implicito_%, razao_vs_consenso_t1?, razao_vs_consenso_t2?, leitura_chave}` ou `null` quando não há reversa.
- **Em `reversa.py`:** `LEITURAS_DO_NIVEL = ("antecipacao_temporal", "acima_do_consenso")`.
- **No catálogo:** `leituras_do_nivel.<chave> = {rotulo}`, travado por igualdade de conjunto contra a tupla, e a
  classificação dos números novos.

**Recusas nomeadas do gate:** `consenso` sem `reversa`; valor não finito ou menor ou igual a zero; `periodo` vazio;
chave desconhecida dentro de `consenso` ou de `t1`/`t2`, com sugestão por `difflib`.

**Testes-chave:** a métrica implícita bate com o oráculo do teste (valor de mercado ÷ múltiplo justo); a
`leitura_chave` sai `antecipacao_temporal` com a implícita dentro de 125% do consenso e `acima_do_consenso` acima
disso; sem consenso, nem razões nem leitura; sem reversa, o bloco sai `null`; uma recusa por mensagem; o catálogo
com as duas leituras rotuladas.

---

## Task 2: o produto e a aba, no relatório

**Arquivos:** `skills/er-relatorio/scripts/entrega.py`, `qc.py`, `render.py`, `builder.py` se precisar;
`assets/template.html`, `assets/i18n/pt-BR.json`; `skills/er-relatorio/SKILL.md`; `tests/relatorio_apoio.py`,
`tests/test_relatorio_valuation.py`, `test_relatorio_contrato.py`, `test_relatorio_tese.py`,
`test_relatorio_cobertura_11.py`.

**Produz:**
- **No contrato:** `execucao.produto`, opcional, com o vocabulário `PRODUTOS = {"analise", "leitura_de_preco"}` e
  default `analise`.
- **No QC:** `analise_sem_reversa` passa a ignorar a limitação publicada quando o produto é `leitura_de_preco`. A
  linha da §11 continua a mesma; a tabela de QC diz a diferença por produto.
- **No render:**
  - com `leitura_de_preco`, a página tem uma aba só, a Valuation, sem navegação para Tese e Evidência;
  - o banner do produto, com o escopo declarado, abre a aba;
  - os avisos obrigatórios saem logo abaixo do banner;
  - toda conclusão de valor sai como leitura condicional, com o produto como segundo gatilho de
    `_leitura_condicional`;
  - o nível implícito entra na seção "o que está no preço": a métrica implícita, o degrau implícito, as razões
    contra o consenso e o rótulo da leitura, pelo catálogo.

**Testes-chave:** a recusa de forma de `execucao.produto` fora do vocabulário; sem o campo, nada muda na página de
hoje; com `leitura_de_preco`, a página tem uma aba só e o banner, os avisos vêm no topo e todo número de valor sai
com rótulo condicional (a varredura existente passa a cobrir o segundo gatilho); a reversa ausente é HARD FAIL
mesmo com limitação publicada; a seção do nível implícito mostra o rótulo da leitura, nunca a chave nem a prosa do
motor.

---

## Dívidas registradas

- Exigir de cada produto o que ele pede (a Tese sob `analise`, o escopo sob `leitura_de_preco`) é do `er-analise`,
  no item 8.
- O `preco_driver_implicito` do motor, que precisa de `vol` e `preco_base`, fica fora: nenhum caso declara volume.
