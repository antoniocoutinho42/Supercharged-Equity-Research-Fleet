# Item 5, fatia C — laboratório ao vivo na aba Valuation

> **Para agentes:** REQUIRED SUB-SKILL: `superpowers:subagent-driven-development`. Calibragem de rigor em
> vigor (ledger, 26/08/2026): implementação simples, testes que discriminam a matemática e os contratos,
> sem revisor por task, **uma** revisão final da fatia. Achado não material: registre no relatório e siga.

**Goal:** o analista muda uma premissa na aba Valuation e vê, na mesma ação, o preço, o múltiplo e **o
diagnóstico** se moverem — com um badge dizendo que o motor do browser reproduz o que o Python publicou.

**Architecture:** a peça nova é uma **fachada versionada do espelho**, e ela mora na **camada de
integração** (`skills/er-valuation/assets/`), não no relatório. Ela recebe um `caso` e devolve o
subconjunto vivo do `resultados.json`; o relatório apenas a embute e a chama. É a emenda **E3** aplicada
ao caso mais difícil do item 5: toda a metodologia que o laboratório executa continua do lado da
integração, e um upgrade para a v10 mexe no motor, no espelho e na fachada — nunca no laboratório.

**§8.4 do desenho (camada viva × precomputada)** é a fonte: o que é vivo é o núcleo de valor, a ponte,
e os **predicados numéricos dos diagnósticos** — "a prosa longa vem de dicionário estático gerado no
build". E a **regra inegociável**: o diagnóstico se move junto com o número; não existe número
interativo com diagnóstico congelado.

**Tech Stack:** JS sem dependências (o espelho e a fachada), Python stdlib no builder, pytest + node.

## Global Constraints

- As da 5A/5B continuam valendo: E3 mecanizada pelo teste de fronteira; nenhuma aritmética de valuation
  fora do motor; HARD FAIL não emite; raiz única; texto de interface só pelo dicionário/catálogo;
  determinismo byte a byte.
- **O relatório NUNCA copia o espelho nem a fachada para `skills/er-relatorio/assets/`.** Ele os lê de
  `ASSETS_DA_INTEGRACAO` (`builder.py:48`, hoje só o catálogo) e os embute. `test_relatorio_fronteira.py`
  reprova cópia **por sha256**, não por nome — copiar quebra a suíte, e é essa a intenção.
- **O laboratório não muda o HTML emitido nem o `qc.json`.** Ele é interface sobre dados já embutidos; o
  relatório continua byte a byte determinístico e continua abrindo offline.
- `vendor/` read-only; suíte em primeiro plano; commit assim que verde, antes do relatório; mutação,
  teste e restauração num único comando. Baseline **758 passed, 1 skipped**.

## Decisões de desenho — tomadas, com a razão

- **L1 — A fachada é da integração, não do relatório.** `skills/er-valuation/assets/espelho_fachada.js`.
  Razão E3: traduzir `caso` → shape de `resultados` é conhecimento de integração e paridade, exatamente o
  que o `avaliar.py` faz do lado Python. Pôr isso no relatório seria reimplementar o wrapper em JS — o
  acoplamento que a diretriz do dono proíbe.
- **L2 — A fachada devolve o shape do `resultados.json`**, para o badge e o laboratório compararem chave
  a chave sem tradução. Ela declara `versao_contrato` e **recusa** um `resultados` cuja
  `versao_contrato` não seja a que ela sabe ler — a v10 reprova aqui, em voz alta, não desenha número
  errado em silêncio (a lição do F7 da 5B).
- **L3 — Escopo vivo = o que produz o preço de cada cenário.** `precificarCelula` (firm/equity),
  `precificarRampa` e `precificarDegrau`, mais a ponte. **Isto não é conservadorismo, é uma exigência do
  badge:** um caso com degrau publica o preço COM degrau (D3 da fatia D), então uma fachada que só
  rodasse `pe` acusaria divergência num caso legítimo — o badge tem de comparar igual com igual.
  **Fora do vivo nesta fatia, e rotulado "congelado nas premissas originais" na tela** (§8.4 manda
  rotular): SOTP (que o §8.4 nem lista como vivo), reversa e sensibilidades. O espelho já tem
  `resolverCompleto`, `grade1D` e `grade2D`; eles entram quando houver consumidor, não antes — é o erro
  do `degrau` e do `decomposicao`, já cometido duas vezes neste projeto.
- **L4 — O badge é um fato, não um enfeite.** A fachada recomputa cada cenário a partir do `caso`
  embutido e compara com o `resultados` embutido, com a mesma tolerância relativa dos harnesses de
  paridade (τ = 1e-12 com piso absoluto — ver `tests/test_paridade_js.py`). Verde: todos batem. Vermelho:
  **nomeia o cenário, a chave e os dois números, e o laboratório não deixa editar** — um editor cujo
  motor discorda do relatório mostraria ao analista um número que o relatório não sustenta. Não é HARD
  FAIL de build: a paridade de build já é provada pelos três harnesses da suíte; este badge prova a
  paridade **na máquina de quem abriu o arquivo**.
- **L5 — As premissas editáveis vêm do catálogo**, com bloco econômico, unidade, tipo de entrada e
  rótulo (`catalogo.premissas.<rota>.<chave>` já traz os quatro; `catalogo.blocos` traz os rótulos dos
  quatro blocos). Premissa presente no caso que o catálogo não conheça: **mostrada, não editável, e
  rotulada como tal** — o laboratório nunca inventa unidade nem widget.
- **L6 — Original × editado, sem sobrescrever** (§8.3: o usuário simula "sem sobrescrever a calibração
  original"). Os dois valores lado a lado, e um botão que restaura. O estado editado vive só na página.
- **L7 — Diagnóstico ao vivo por chave** (§8.4, regra inegociável). `diagnosticosFirm`/
  `diagnosticosEquity` do espelho devolvem as **chaves**; `catalogo.diagnosticos` dá texto e severidade
  por idioma. Mudou o número, mudou o diagnóstico na mesma ação. O relatório não conhece um único
  predicado.
- **L8 — Sem rede, sem relógio, sem armazenamento.** O laboratório roda inteiro no arquivo aberto. A
  regra de autocontenção da 5B (incluindo os sete tokens de rede no miolo dos scripts, fechados na onda
  de correção) continua valendo e vai ser exercitada por esta fatia.

**Fora desta fatia — registrado:** reversa e sensibilidades ao vivo; SOTP ao vivo; persistir o estado
editado; exportar o cenário editado como caso novo.

## File Structure

| Arquivo | Responsabilidade |
|---|---|
| `skills/er-valuation/assets/espelho_fachada.js` (novo) | `caso` → subconjunto vivo do `resultados`; versão do contrato; comparação de paridade |
| `skills/er-relatorio/scripts/builder.py` | `ASSETS_DA_INTEGRACAO` ganha espelho e fachada |
| `skills/er-relatorio/scripts/render.py` | Painel do laboratório: premissas por bloco, badge, original × editado |
| `skills/er-relatorio/assets/laboratorio.js` (novo) | Só interface: lê os campos, chama a fachada, redesenha |
| `skills/er-relatorio/assets/template.html` | `$js_espelho`, `$js_fachada`, `$js_laboratorio`, dados do laboratório |
| `tests/test_espelho_fachada_js.py` (novo) | A fachada contra o `resultados` que o Python produz, em node |
| `tests/test_relatorio_laboratorio.py` (novo) | Painel, badge, premissas por bloco, autocontenção |

---

## Task 1: a fachada (integração), sem nada de relatório

**Files:** create `skills/er-valuation/assets/espelho_fachada.js`, `tests/test_espelho_fachada_js.py`.

**Interfaces — produz:**
- `FachadaEspelho.VERSAO_CONTRATO` — a string de `resultados.versao_contrato` que ela sabe ler.
- `FachadaEspelho.avaliarCaso(caso) -> {cenarios: {<nome>: {premissas, valor: {preco_acao}, multiplo: {chave, valor}}}, ponte: {nd_efetivo}}`
  — o subconjunto vivo, nas mesmas chaves do `resultados.json`.
- `FachadaEspelho.compararComResultados(caso, resultados) -> {ok: bool, divergencias: [{cenario, chave, python, js, erro_relativo}]}`.

**O que verificar antes de escrever o comparador — não presuma:** `precificarCelula` devolve **um**
múltiplo (o da métrica declarada), enquanto `resultados.cenarios.<n>.multiplos` traz quatro chaves
(`EV/NOPAT_curr`, `EV/NOPAT_fwd`, `EV/EBITDA_curr`, `EV/EBITDA_fwd`). A hipótese é que o múltiplo da
fachada corresponde à chave `_curr` da métrica declarada (é o que `manchete.multiplo.chave` aponta na
fixture `caso_reversa_firm`: `EV/EBITDA_curr` = 6.6906). **Confirme rodando**, e escreva o teste que
prende a correspondência — se for outra, corrija o plano no relatório, não o silencie.

**Testes:** para cada fixture de `tests/fixtures/` que a rota admita, a fachada em node reproduz o
`preco_acao` de cada cenário do `resultados` que o Python produz (`relatorio_apoio.montar_entrega`),
dentro de τ; um caso com `degrau` reproduz o preço COM degrau; a fachada recusa `versao_contrato`
desconhecida; `compararComResultados` devolve `ok: false` **nomeando** cenário, chave e os dois números
quando o `resultados` é adulterado num cenário só. **Falseabilidade:** adultere o `preco_acao` de um
cenário na fixture montada e confirme que o comparador acusa; restaure.

---

## Task 2: o laboratório na aba Valuation

**Files:** create `skills/er-relatorio/assets/laboratorio.js`, `tests/test_relatorio_laboratorio.py`;
modify `builder.py` (`ASSETS_DA_INTEGRACAO`), `render.py`, `template.html`, `assets/i18n/pt-BR.json`.

**O painel:** um campo por premissa do cenário, **agrupado pelos quatro blocos do catálogo**, com rótulo
e unidade do catálogo (L5); o valor original ao lado do editado (L6); o preço, o múltiplo e o upside
recalculados a cada mudança; o badge de paridade no topo (L4). Premissa fora do catálogo: exibida,
desabilitada, rotulada. O que não é vivo (SOTP, reversa, sensibilidades) ganha o rótulo "congelado nas
premissas originais" (L3).

**A fronteira, mecanizada:** `laboratorio.js` **não tem uma linha de metodologia** — nenhuma fórmula de
valuation, nenhum limiar, nenhum nome de premissa hardcoded. Ele lê campos, chama
`FachadaEspelho.avaliarCaso` e escreve o resultado na tela. Acrescente ao
`tests/test_relatorio_fronteira.py` uma trava para esse arquivo: nenhum identificador do núcleo
(`evNopat`, `evEbitda`, `pe(`, `wacc`, `roic`, `gordon`, `book`…) aparece nele. **Prove a trava** com
uma fuga.

**Testes:** os dois JS da integração entram na página por leitura, não por cópia (sha256 contra o
original, e a suíte de fronteira continua verde); o painel traz os quatro blocos na ordem do catálogo;
uma premissa não catalogada sai desabilitada; a página continua autocontida (a regra dos sete tokens de
rede da 5B roda sobre o arquivo novo).

---

## Task 3: diagnóstico ao vivo

**Files:** modify `skills/er-valuation/assets/espelho_fachada.js` (expor os diagnósticos por chave),
`skills/er-relatorio/assets/laboratorio.js`, `render.py`, `tests/test_espelho_fachada_js.py`,
`tests/test_relatorio_laboratorio.py`.

`FachadaEspelho.avaliarCaso` passa a devolver as chaves de diagnóstico **na mesma forma e no mesmo lugar
em que o wrapper as publica**, e o laboratório pinta cada chave com o texto e a severidade de
`catalogo.diagnosticos`.

*Correção da primeira versão deste plano, que mandava usar só `diagnosticosFirm`/`diagnosticosEquity`:
isso cobre firm e equity, mas a fachada precifica quatro pernas, e o wrapper publica diagnóstico em três
formas. **Firm/equity** (inclusive as chaves próprias de um cenário com degrau, que vêm da chamada `pe`):
`cenarios.<n>.diagnosticos_chaves`, classificadas das mensagens do motor. **Rampa:** a mesma chave, mas
por presença dos avisos na ordem de `_AVISOS_RAMPA_ORDEM` — o espelho já os devolve em
`precificarRampa(...).avisos`. **Degrau:** `cenarios.<n>.degrau.ALERTA`/`ALERTA_RiR` com a **prosa do
motor e sem chave**, e sem entrada no catálogo. Seguir a primeira versão deixaria os avisos da rampa e os
alertas do degrau congelados enquanto o preço deles se move — exatamente o que a regra inegociável do
§8.4 proíbe.* Por isso a Task 3 começa na **integração**: o wrapper passa a publicar
`cenarios.<n>.degrau.diagnosticos_chaves` (ordenadas por presença, no padrão da rampa), o catálogo ganha
os dois rótulos, e a fachada espelha as três formas. O comparador do badge passa a cobrir as chaves, em
ordem.

**O teste que importa (§8.4, regra inegociável):** partindo de um cenário sem alerta, uma edição que
torne a combinação economicamente incoerente **muda a lista de chaves na mesma chamada** — e o contrário
também (desfazer a edição devolve a lista original). Escolha a edição pelo predicado do espelho, não por
tentativa: leia `diagnosticosFirm`/`diagnosticosEquity` e monte a entrada que cruza o limiar.
**Falseabilidade:** congele os diagnósticos (devolva sempre a lista original) e confirme que este teste
fica vermelho.

---

## Revisão final da fatia

Uma só, depois da Task 3, no formato das anteriores. Carregue para ela: se o badge vermelho realmente
bloqueia a edição; se algum conhecimento metodológico vazou para `laboratorio.js` ou para o `render.py`;
e se a fachada e o `avaliar.py` podem divergir sem que nada reprove.
