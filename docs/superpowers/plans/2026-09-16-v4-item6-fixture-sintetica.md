# Item 6 — fixture sintética offline, o caso que deve falhar e a paridade por caso no build

**Goal.** Cumprir a §13 e o item 6 da §17:
- uma companhia fictícia, com dados inventados e economicamente coerentes, que exercita os caminhos raros: rota firm,
  um segmento de SOTP, o gatilho de capacidade pré-construída, um driver exógeno com gap acima do limiar e uma
  escolha metodológica que move mais de 10%;
- **um caso que deve falhar** (número material sem proveniência), testado como comportamento pelo builder de verdade;
- a **paridade Python↔JS verificada por caso no build**, com falha fechada — a pendência "item 6" da tabela da §11.

**Regime (15/09).** Implementar o que o desenho pede, sem abstração preventiva nem escopo novo. Um teste que
discrimina cada comportamento novo; nada de mutation test. Um commit por task, a suíte inteira uma vez no fim e uma
checagem de blockers.

**E3.** A paridade é da integração: ela oferece a verificação, e o builder só a chama e converte o resultado em
achado. A conta dos drivers é do motor (`justos.registro_drivers`); o wrapper a roda e publica.

**Fontes.** Desenho §8.4 (drivers precomputados e rotulados), §11 (HARD FAIL "paridade Python↔JS divergente"), §13
(a fixture sintética, o τ medido, a falha fechada), §17 item 6 e §18.2. Vendor: `scripts/justos.py`,
`registro_drivers` (o gate por impacto |elasticidade × gap|, limiar de 10%).

## Decisões

- **D1 — drivers exógenos, precomputados.** Bloco opcional `drivers` no caso, na forma que `registro_drivers`
  aceita: cada driver com `nome`, `base`, `spot` e a elasticidade declarada, ou os insumos para derivá-la. O wrapper
  roda o motor e publica `resultados.drivers` com a saída íntegra e as chaves por driver que o payload já traz (o
  impacto, se passou do limiar e se vira cenário). A aba mostra a tabela rotulada como congelada. Nenhuma regra de QC
  nova: transformar o driver em cenário é decisão do analista, e exigi-la é do `er-analise` (item 8).
- **D2 — paridade por caso no build, com falha fechada.**
  - A integração oferece `paridade.verificar(caso, resultados)`, que roda o espelho e a fachada em node sobre o
    caso e compara com `resultados` pelo mesmo comparador do badge. Devolve `ok`, `divergente` (com as divergências)
    ou `indisponivel` (node ausente).
  - O builder a chama antes de emitir. `divergente` é HARD FAIL `paridade_divergente`: nada é emitido (§18.2).
    `indisponivel` é REQUIRED DISCLOSURE `paridade_nao_verificada_no_build`: o badge ainda confere quando o
    relatório abre.
  - A linha da §11 "paridade Python↔JS divergente" passa a citar `paridade_divergente` e perde a pendência item 6.
- **D3 — a fixture sintética são raízes de execução versionadas, compostas no teste.** Em
  `tests/fixtures/analises/SINT3/`, cada raiz guarda o `caso.json` e as partes da entrega que o analista escreveria
  (análise, ledger, dados). O teste compõe `resultados` pelo motor de verdade (`avaliar()`), monta a raiz num
  diretório temporário e roda o builder pela CLI. Nenhum `resultados` congelado no repositório.
  1. `firm_escolha_driver`: rota firm, reversa, uma escolha metodológica com impacto acima de 10% e um driver
     exógeno acima do limiar → emite, RC 0.
  2. `sotp_capacidade`: SOTP com um segmento na rota rampa (a capacidade pré-construída) e um na firm → emite, RC 0.
  3. `sem_proveniencia`: a raiz 1 com um insumo material sem registro no ledger → HARD FAIL
     `insumo_sem_proveniencia`, RC 2, nenhum `relatorio.html`.
- **D4 — CI.** O pytest do CI já roda a suíte inteira com node instalado; o teste ponta a ponta da fixture entra
  nele. Nenhum passo novo no workflow.

---

## Task 1: drivers exógenos, na integração

**Arquivos:** `skills/er-valuation/scripts/caso.py` e `avaliar.py`; `assets/catalogo_apresentacao.json`;
`skills/er-valuation/SKILL.md`; `tests/relatorio_apoio.py` (variante `drivers`); `tests/test_valuation_caso.py`,
`test_valuation_avaliar.py`, `test_valuation_matriz.py`, `test_catalogo_apresentacao.py`.

**Produz:** o bloco `drivers` no caso, com recusas nomeadas (base ou spot não finitos ou não positivos, elasticidade
ausente sem os insumos para derivá-la, chave desconhecida, nome repetido); `resultados.drivers` com a saída do motor
íntegra e as chaves por driver; a classificação dos números novos no catálogo (não são conclusão de valor; `base` e
`spot` são insumo do caso).

**Testes-chave:** o impacto de cada driver bate com o do motor; um driver acima do limiar sai marcado como tal, e um
abaixo não; sem o bloco, `resultados.drivers` sai `null` em toda fixture; uma recusa por mensagem.

## Task 2: a seção de drivers e a paridade no build, no relatório

**Arquivos:** `skills/er-valuation/scripts/paridade.py` (novo, da integração); `skills/er-relatorio/scripts/builder.py`,
`qc.py` e `render.py`; `assets/i18n/pt-BR.json`; os dois `SKILL.md`; `tests/test_relatorio_valuation.py`,
`tests/test_relatorio_cobertura_11.py`, um teste novo da paridade no build.

**Produz:** `paridade.verificar(caso, resultados)` na forma de D2; os códigos `paridade_divergente` (HARD FAIL) e
`paridade_nao_verificada_no_build` (REQUIRED DISCLOSURE), com mensagens e as linhas na tabela da §11; a seção de
drivers na aba Valuation, rotulada como congelada, depois das sensibilidades.

**Testes-chave:** com node, uma entrega legítima verifica `ok` e emite; um `resultados` adulterado num número que o
comparador lê dá `divergente`, e o builder não emite; sem node (o caminho do executável forçado a ausente no teste),
a entrega emite com o disclosure; a seção de drivers aparece com o rótulo de congelado quando o bloco existe, e some
quando não existe.

## Task 3: a fixture sintética e o teste ponta a ponta

**Arquivos:** `tests/fixtures/analises/SINT3/` (as três raízes); `tests/test_fixture_sintetica.py` (novo).

**Produz:** as três raízes de D3, com dados inventados e coerentes — âncoras observáveis, ledger completo com fonte e
localizador fictícios, perguntas da tese, consenso — e o teste que compõe cada raiz e roda o builder de verdade.

**Testes-chave:** as raízes 1 e 2 emitem com RC 0, sem HARD FAIL, e a página traz o painel de escolhas com a escolha
material, a seção de drivers com o driver acima do limiar e, na raiz 2, o segmento em rampa; a raiz 3 sai com RC 2,
o achado `insumo_sem_proveniencia` no `qc.json` e nenhum `relatorio.html`.

---

## Dívidas registradas

- Exigir que um driver acima do limiar vire cenário é do `er-analise` (item 8).
- A paridade no build cobre o que o comparador do badge cobre; a curvatura continua fora dele (5I, D4).
