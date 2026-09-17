# Item 8 — `er-analise`: o workflow master da v4

**Goal.** O item 8 da §17: o `er-analise` com os quatro marcos, a política de autonomia e interrupção e as regras
invioláveis. Ele fecha também as pendências que a tabela "Cobertura da §11" e as fatias 5F–5I deixaram com o dono
"item 8":
- a suíte da metodologia por execução;
- os gates e comandos na ficha técnica;
- os QUALITY WARNING que dá para mecanizar e o checklist de revisão para os que são julgamento editorial;
- o que cada produto exige;
- o formato da saída dos mandatos de pesquisa e a junção deles no ledger único.

**Regime (15/09).** Implementar o que o desenho pede, sem abstração preventiva nem escopo novo. Um teste que
discrimina cada regra nova; nada de mutation test nem fixture nova (variantes no apoio e a fixture sintética do item
6). Um commit por task, a suíte inteira uma vez no fim.

**E3.** O `er-analise` orquestra processo e julgamento, sem calcular nem validar metodologia:
- a conta é do motor, chamada pelo `er-valuation`;
- a validação da entrega é do builder;
- o vocabulário dos gates e a lista de banimento são da metodologia, publicados pelo catálogo da integração.

**Fontes.**
- **Desenho:** §5 (os quatro marcos, a política de interrupção, os dois produtos), §7 (as perguntas da tese), §9, §11,
  §12 (workspace, quarentena, contrato do builder), §13 (a suíte em duas fases, cada uma numa invocação fresca) e §18.
- **Vendor:** `SKILL.md`, "Cinco gates antes de qualquer conta" (Gate 0, 0.5, 1, 2 e 3); `references/aplicacao.md`,
  a "lista de banimento no corpo do relatório".

## Decisões

- **D1 — a suíte da metodologia roda por execução e fica registrada.**
  - O `er-analise` roda os três comandos, cada um numa invocação fresca: `justos.py selftest`,
    `testes.py --phase model` e `testes.py --phase cli`.
  - O resultado vai em `execucao.suite_da_metodologia: [{comando, codigo_saida}]`.
  - O catálogo da integração declara a lista dos comandos exigidos.
  - HARD FAIL `suite_da_metodologia_nao_passou` quando falta um comando ou quando algum código de saída não é 0. A
    linha da §11 perde a pendência item 8.
- **D2 — os cinco gates ficam declarados.**
  - O bloco é `execucao.gates: [{gate, decisao}]`, com `gate` no vocabulário que o catálogo publica (os cinco do
    vendor, com rótulo) e `decisao` em texto.
  - HARD FAIL `gates_nao_declarados` quando falta algum dos cinco.
  - A ficha técnica passa a trazer os gates e os comandos da suíte, com código de saída.
- **D3 — o que cada produto exige, como recusa de forma (código 1).**
  - **Com reversa publicada,** nos dois produtos: `analise.o_que_esta_no_preco`.
  - **Sob `analise`:**
    - `analise.reteste_terminal`;
    - o cross-check publicado ou `analise.cross_check.ausente`, um dos dois.
  - O apoio compõe os padrões, e os testes continuam montando entregas válidas.
- **D4 — dois QUALITY WARNING mecanizados.**
  - **`linguagem_interna_no_corpo`:** o catálogo publica a lista de banimento do vendor — termos literais e os
    padrões de código (R#, C#, D#, J#, §#, versão da skill) —, e o QC a aplica à prosa auditada das abas Tese e
    Valuation.
  - **`contagem_de_premissas_fora_do_usual`:** fora de `qc.MINIMO_DE_PREMISSAS_DECISIVAS = 2` e
    `qc.MAXIMO_DE_PREMISSAS_DECISIVAS = 5`. São constantes editoriais do Fleet, documentadas.
- **D5 — os três julgamentos editoriais viram checklist do M4, e não código:** exhibit que não responde à pergunta;
  pergunta de tese pouco discriminante; Positives e Negatives pouco ligados ao valuation. Na tabela da §11, a coluna
  "Fora do QC" passa a citar o checklist do `er-analise`, e nenhuma linha fica com pendência.
- **D6 — o workspace e a entrega saem de um script do `er-analise`.** O `execucao.py` tem três subcomandos:
  - `nova <TICKER>` cria `analises/<TICKER>/<execution-id>/`, com `evidencia/` para a saída dos mandatos e
    `quarentena/`;
  - `suite <raiz>` roda D1 e grava o resultado;
  - `montar <raiz>` compõe `entrega.json` a partir das partes da raiz — o caso, os resultados do `er-valuation`, a
    análise, `evidencia/*.json` (fragmentos `ledger/1`, juntados com recusa de id repetido), os dados e a execução
    — e roda o builder.
- **D7 — a saída de cada mandato** do `pesquisa-evidencia` é um arquivo `evidencia/<mandato>.json` com `registros` e
  `lacunas` no formato `ledger/1`. O Analista acrescenta `usado_em`, `reconciliacao` e `contraprova_de`; o `montar`
  junta tudo no ledger único.

---

## Task 1: contrato, QC e ficha técnica

**Arquivos:**
- `skills/er-relatorio/scripts/entrega.py`, `qc.py` e `builder.py`;
- `assets/i18n/pt-BR.json`;
- `skills/er-valuation/assets/catalogo_apresentacao.json`, com os comandos da suíte, os gates e a lista de banimento;
- os dois `SKILL.md`;
- os testes: `tests/relatorio_apoio.py`, `tests/test_relatorio_contrato.py`, `test_relatorio_tese.py`,
  `test_relatorio_valuation.py`, `test_relatorio_cobertura_11.py` e `test_catalogo_apresentacao.py`.

**Produz:**
- as formas de D1–D3;
- os códigos `suite_da_metodologia_nao_passou`, `gates_nao_declarados`, `linguagem_interna_no_corpo` e
  `contagem_de_premissas_fora_do_usual`, com mensagens;
- a ficha técnica com gates e comandos;
- a tabela da §11 sem pendência;
- o apoio compondo os padrões novos.

**Testes-chave:**
- um comando da suíte com código de saída diferente de 0 reprova;
- falta de comando reprova;
- um gate faltando reprova;
- as recusas de forma de D3, uma por campo e uma por produto;
- um termo da lista de banimento na prosa da Tese acende o warning, e o mesmo termo na Evidência não acende;
- premissas decisivas abaixo de 2 ou acima de 5 acendem o warning;
- a trava da §11 fica verde, sem pendência.

## Task 2: o script do workspace e da entrega

**Arquivos:** `skills/er-analise/scripts/execucao.py` (novo); `tests/test_analise_execucao.py` (novo).

**Produz:** os subcomandos `nova`, `suite` e `montar` de D6. A lista de comandos da suíte fica injetável no teste,
para não rodar o vendor inteiro a cada caso; a CI já roda a suíte real.

**Testes-chave:**
- `nova` cria a árvore com o id da execução;
- `suite` grava os códigos de saída e sai com erro quando um comando falha;
- `montar` junta os fragmentos de `evidencia/` e recusa id repetido;
- `montar` sobre as partes de uma raiz da fixture sintética gera uma entrega que o builder emite com RC 0.

## Task 3: o `SKILL.md` v4 do `er-analise`

**Arquivos:** `skills/er-analise/SKILL.md` (reescrito); `skills/er-analise/references/` (sai o que é do fluxo v3 —
os F0–F11 e o K3 —, entra só o que o corpo precisar); `tests/test_analise_skill.py` (novo).

**Produz:** o workflow da v4, operacional:
- os dois produtos e quando usar cada um;
- M1–M4, com a saída verificável de cada marco e a adaptação dentro de cada um;
- a política de autonomia e de interrupção;
- workspace e quarentena;
- os mandatos de pesquisa e a junção do ledger (D7);
- os cinco gates com o índice `er-multiplos-justos`;
- o caso do `er-valuation`;
- as perguntas da tese (§7);
- a prosa com placeholders;
- a suíte e o builder pelo `execucao.py`;
- como tratar HARD FAIL, disclosure e warning;
- o checklist de revisão do M4 (D5);
- as regras invioláveis (§18).

**Testes-chave:**
- o frontmatter;
- todo script, skill e agente citado existe;
- todo código de QC citado existe no `qc.py`;
- nenhuma referência ao fluxo v3 (F0–F11, K3, `data-manager`).

---

## Dívidas registradas

- O que só a doutrina do `er-evidencia` proíbe, e o QC não recusa (item 7).
- Um driver acima do limiar que não vira cenário continua sendo julgamento do Analista, no checklist do M4.
- Os skills e o agente da v3 continuam carregados até o item 10.
