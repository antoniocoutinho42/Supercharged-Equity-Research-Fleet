# Item 5, fatia I — o laboratório completo (última fatia do item 5)

**Goal:** a aba Valuation deixa de ter número congelado ao lado de número vivo. Reversa e
sensibilidades passam a rodar no espelho, com paridade; o triângulo e a ponte viram controles; cada
premissa mostra o registro do ledger que a sustenta; o badge sobe para o cabeçalho.

**Regime (dono, 15/09):** implementar o que o desenho pede, sem abstração preventiva nem escopo novo.
Um teste que discrimina cada comportamento novo; **nenhum** mutation test, **nenhuma** fixture nova
(variantes compostas em `tests/relatorio_apoio.py` e entradas novas em `tests/fixtures/vetores_solver.json`,
que é gerada). Suíte inteira **uma vez por lote**, pelo controlador. Um commit por task.

**A regra inegociável (§8.4):** o diagnóstico anda junto com o número. Onde este plano deixa algo
congelado, ele o rotula no próprio bloco e diz por quê.

**Paridade:** aqui o rigor é máximo. Todo cálculo novo do espelho entra com teste nos harnesses que já
existem (`tests/test_paridade_wrapper_js.py`, `tests/test_espelho_fachada_js.py`), nunca em arquivo novo.

---

## Achados de desenho — medidos por leitura

**A1 — O espelho já tem o solver inteiro, com paridade.** `resolver` (= `solve`), `resolverCompleto`
(= `solve_full`, raízes + tangenciais), `identificacao`, `dedupeRaizes`, `arredondarPy` e
`resolverProblema` estão em `skills/er-valuation/assets/motor_espelho.js:255-496`, exportados, e batem
com o motor congelado em `tests/test_paridade_solver_js.py` (42 problemas `tipo:"solver"`).
`alvoDeMercado`, `grade1D` e `grade2D` idem, contra `reversa.py`/`sensibilidades.py`, em
`tests/test_paridade_wrapper_js.py` (4 `alvo`, 5 `grade1d`, 2 `grade2d`).
**O que falta não é matemática de raiz — é a orquestração por eixo.**

**A2 — O que falta no espelho para a reversa rodar no browser** (medido contra o handler `rev`,
`vendor/multiplos-justos/scripts/justos.py:2021-2300`, e `reversa.reverter`, `reversa.py:795-888`):

| Peça | Onde está hoje | Custo |
|---|---|---|
| `M = alvo / conv`, `conv = (1−d)(1−t)` só na base EBITDA | justos.py:2035-2036 | baixo |
| Faixas de busca `rngs` por variável, derivadas das outras premissas | justos.py:2058-2065 | baixo |
| `steps=800` | justos.py:281/298 | trivial |
| Eixo `cap`: série `valor(n)` n=1..60, monotonicidade, interpolação, `round(hit,1)`, 4 saídas | justos.py:2137-2200 | **médio** |
| `beta_implicito` (CAPM invertido + posição na banda) | reversa.py:334-388 | baixo |
| `leitura_do_eixo` normalizada — o que a aba lê desde a 5F (D2) | reversa.py:503-566 | médio |
| `teto_do_crescimento_gratuito` (3 sobreposições + avaliação direta `ev`/`pe`) | reversa.py:598-713 | baixo |
| `limitacoes_da_leitura` / `iso_nao_calculada` (gatilho = eixo primário sem raiz) | reversa.py:569-595 | trivial |

Hoje `lo`/`hi`/`steps` chegam **de fora**, fixados por problema em `vetores_solver._problema`
(`_LO_HI_POR_RESOLVER`, linhas 353-367) — nunca derivados.

**A3 — O que NÃO precisa entrar no espelho, e é o que torna a fatia barata.** A 5F (D2) já decidiu que
o relatório lê `resultados.reversa.eixos.<eixo>.leitura` + `.resolucao`, **não** o payload do motor.
Ficam fora, portanto: `sem_solucao`, `sugestao`, `guardas_v9_4`, `premissas_fixadas`, `premissa_regime`,
`nota_regime` — prosa do motor que a tela nunca mostra.

**A4 — Risco de paridade medido, e é o achado mais sério da fatia.** `vetores_solver.py:353-367`
restringe `roic`/`roe` a `(0.03, 0.80)` **de propósito**: perto do polo `1/roic`, os ULPs amplificados
por `/h²` na segunda diferença de `identificacao` fazem Python e JS divergirem no dígito arredondado de
`curvatura_d2M_dx2`. A faixa REAL do vendor para o eixo `rentabilidade` é
`(max(0.005, g+1e-4), 1.50)` — **inclui exatamente a região que a fixture evita**. Com `roic = 0.005`,
`h = 5e-7` e `h² = 2.5e-13`: a amplificação é ~4e12. Um badge que compare `curvatura` arredondada
ficaria **vermelho num caso legítimo**, e badge vermelho **trava o laboratório inteiro**
(`laboratorio.js:394-416`). Isto tem de ser medido antes de o comparador ser escrito (D4).

**A5 — Sensibilidades ao vivo: falta só o diagnóstico por célula.** `grade1D`/`grade2D` devolvem
`{x, valor, multiplo}`; o comentário de `motor_espelho.js:740-748` diz por quê ("a dedup de diagnostico
do wrapper NAO entra aqui"). Mas `sensibilidades.grade_1d/2d` publicam `diagnosticos_unicos`,
`diagnosticos_unicos_chaves` e `diag` (índices) por célula, e a §8.4 proíbe número vivo com diagnóstico
congelado. A fachada já sabe montar chaves (`diagnosticosDaCelula`, `espelho_fachada.js:339`).
**Armadilha:** o Python dedupa pela MENSAGEM e classifica depois; dedup pela CHAVE produz lista de outro
comprimento quando duas mensagens colapsam na mesma chave.

**A6 — A recusa de domínio da 4C não alcança o solver.** `dominioCliRecusa`/`cliRecusa`
(`motor_espelho.js:564-596`) são chamadas por cinco portas de precificação (677, 971, 1235, 1332, 1587)
— nunca por `resolverProblema` (472), que chama `DESPACHO[fn]` direto. Um vetor editado com `gp = −150%`
resolveria uma raiz onde o motor de verdade sai com código 2 sem calcular nada. Pendência já registrada
(`progress.md:160`).

**A7 — Os `avisos_dominio` da rampa (F3 da 4C) não tocam esta fatia.** `tax`/`da` fora de `[0,100]`
viram `avisos_dominio` (justos.py:1624-1629, injetados em 1641-1645) e chegam ao `resultados` **só na
rota rampa**, porque `_monta_cenario_rampa` é passthrough e `_monta_cenario` é whitelist fechada
(`avaliar.py:888-905`). O espelho não os tem (`AVISOS_RAMPA` tem três entradas, linha 787). Mas a rampa
**recusa reversa e sensibilidades no portão** (`caso._validar_reversa` FIX 1 / `_validar_sensibilidades`
FIX 1): o item é ortogonal ao laboratório desta fatia. Custo: uma quarta entrada em `AVISOS_RAMPA` mais
a checagem — baixo, e cabe na Task 2 sem crescer escopo.

**A8 — O badge move-se com uma linha, e falha em silêncio se ninguém mexer.** `laboratorio.js:389` faz
`raiz.querySelector("[data-laboratorio-badge]")`, onde `raiz` é o `[data-laboratorio]` de
`render.py:1747`. Fora dessa `<section>`, `alvo` vira `null` e `pintarBadge` **retorna no guarda da
linha 139** — sem badge, sem erro, com o painel destravado. O cabeçalho é
`<section class="valuation-cabecalho">` (`render.py:2684`), hoje sem atributo-âncora.

**A9 — A ponte é um SVG, e o degrau só é endereçável por posição.** `_ponte_html` (`render.py:1323`)
emite um host **vazio** `div[data-painel="ponte"]`; `svg.js:197` `waterfall(parcelas, opcoes)` desenha as
barras com `data-indice="{i}"` e `data-fechamento="1"` — nunca pela chave semântica do catálogo
(`divida_bruta`, `caixa_e_equivalentes`, `outros_ativos`, `outros_passivos`, `minoritarios`). Editor
**dentro** do SVG é caro (hit-testing, input flutuante, redesenho); editor **ancorado ao degrau** é barato.

**A10 — A cadeia de derivação existe como dado, não como tela.** O `ledger/1`
(`skills/er-evidencia/assets/contrato_ledger.json`) tem `claim`, `fonte`, `formula` (opcional),
`usado_em` (opcional); `catalogo.insumos_do_caso` já enumera `cenarios.*.premissas.*` e `ponte.*`. Hoje
`usado_em` só aparece como uma linha de texto na tabela do ledger, na aba Evidência
(`render.py:2829-2830`). O schema da premissa no catálogo tem quatro chaves (`bloco`, `entrada`,
`rotulo`, `unidade`) — sem `formula`, sem `fonte`. **Nada a inventar: é composição.**

**A11 — O teto da alavanca já tem chave viva; falta o rótulo no número.** `degrau_alerta`
(`catalogo_apresentacao.json:887-893`) tem rótulo que diz literalmente "reporte como teto da alavanca,
não como cenário", e o espelho já a acende ao vivo (`ALERTAS_DEGRAU`, `precificarDegrau`). O cenário com
o alerta aceso continua exibido como cenário. Custo: baixo.

**A12 — `_congelados_html`** (`render.py:1703-1718`) lista `sotp`, `reversa` e `sensibilidades`. A fatia
tira dois; SOTP fica. Há um segundo rótulo, `<p class="reversa-congelado-nota">` (`render.py:2347`), no
topo de "o que está no preço" — que precisa **descer** para o bloco que continuar congelado (D6).

**A13 — Custo por redesenho.** `resolverCompleto` faz ~2.400 avaliações do núcleo por eixo (800 da
varredura + 90 iterações de bissecção por troca de sinal + 801 do sweep tangencial + 80×2 por candidato);
o `cap` faz 60. Quatro eixos ≈ 10k chamadas de forma fechada, mais as grades. É browser, não CI — mas o
listener de `input` hoje redesenha a cada tecla (`laboratorio.js:346-351`).

---

## Decisões

- **D1 — A reversa ao vivo entra pela `leitura`, não pelo payload do motor** (§8.4; desenho §15, E3;
  5F D2). A fachada publica `reversa.eixos.<eixo>.{leitura, resolucao}` e `reversa.alvo`, nas **mesmas
  chaves** do `resultados.json`; o comparador compara essas, não a prosa. Um espelho que reproduzisse
  `sem_solucao`/`sugestao` estaria reimplementando a redação do motor, não a metodologia.
- **D2 — As faixas de busca são do vendor e entram no espelho como função, não como constante.**
  `rngs` (justos.py:2058-2065) depende das outras premissas; congelá-las num objeto daria a raiz certa
  para o vetor original e a raiz errada para o editado — que é exatamente o caso de uso.
  `--rir-externo` **não** entra: nenhum caso o declara e o caso não tem campo para ele (dívida).
- **D3 — O eixo `cap` entra ao vivo, e publica CÓDIGO, não a frase do motor.** `_MOTIVO_DO_CAP_POR_DIRECAO`
  (reversa.py:172-175) mapeia duas frases verbatim do vendor para código; o espelho decide o código pelo
  mesmo predicado (`crescente`), sem nunca montar a frase. Deixar `cap` congelado ao lado de três eixos
  vivos é o defeito que a §8.4 nomeia.
- **D4 — O que o badge compara na reversa sai de uma MEDIÇÃO, não de um palpite** (A4). A Task 1 abre
  medindo a divergência de `curvatura_d2M_dx2` sobre a faixa real de `roic`/`roe`, com o vetor mais
  próximo do polo que a rota admite. Se o dígito arredondado divergir, o comparador compara raízes,
  tangenciais, `motivo`, classe de `identificacao` e `intervalo` — e **exclui `curvatura` nomeadamente,
  com a razão no código**, em vez de afrouxar τ para todo mundo. `curvatura` continua exibida: ela é
  leitura, não decisão, e um badge vermelho num caso legítimo trava o laboratório inteiro (A8/L4 da 5C).
- **D5 — A recusa de domínio da 4C entra na montagem de `f`** (A6). `dominioCliRecusa` sobre o vetor
  editado ANTES de montar `f`, e o eixo recusado publica `resolucao: {resolveu: false}` com `motivo`
  próprio — nunca uma raiz. Mesma disciplina de `precificarCelula` (linha 677).
- **D6 — O que continua congelado é rotulado no próprio bloco, não na seção** (§8.4). Sai da seção "o
  que está no preço" o `reversa-congelado-nota` de topo; entra um rótulo no `nivel_implicito`
  (subcomando `nivel` do motor, não espelhado — D11) e nada mais. `_congelados_html` fica só com SOTP.
- **D7 — O triângulo é identidade da metodologia: mora no espelho** (§8.3; §15.15). `laboratorio.js` não
  pode conter `rir`/`roic`/`g` — `tests/test_relatorio_fronteira.py` varre o arquivo com uma lista
  **derivada** do espelho e do catálogo. O espelho ganha `resolverTriangulo({rota, premissas, triangulo})`,
  que aplica `g = RiR × retorno` e devolve a terceira variável mais o `rir` como número (hoje ele só
  existe na prosa da eco `firm_rir` — dívida aberta pela 5F, D8). Trocar a configuração **não sobrescreve
  a calibração**: o `data-laboratorio-original` e o botão de restaurar que a 5C já tem cobrem isso.
- **D8 — A ponte é editável no degrau por ancoragem, não por editor dentro do SVG** (A9; §9; §15.15).
  Uma linha de entrada por parcela, `data-ponte-linha="<chave do catálogo>"`, alinhada ao degrau, com o
  SVG redesenhado por `FleetSVG.waterfall` a cada mudança. O degrau continua sendo o controle
  visualmente; o hit-testing dentro do SVG fica de fora, nomeado.
- **D9 — A cadeia de derivação é composição do ledger, sem prosa nova** (§9; §6.2; A10). Para cada
  premissa, os registros cujo `usado_em` endereça `cenarios.<cenário>.premissas.<chave>` (e
  `ponte.<linha>` na ponte), exibidos com `claim`, `formula` quando houver e `fonte.identidade` +
  `localizador.valor`. Premissa sem registro: **sem linha**, nunca um texto inventado. A decisão de
  mostrar `formula` vem da flag do contrato (`estatutos.calculated.exige_formula`), nunca do nome do
  estatuto — regra de projeto de `tests/test_contrato_ledger.py:7-10`.
- **D10 — O teto da alavanca é derivado da chave viva, na integração** (§8.2; A11). A fachada marca o
  cenário quando `degrau_alerta` está na lista viva; o rótulo vem do catálogo. `laboratorio.js` lê um
  booleano e um rótulo — não conhece o predicado.
- **D11 — `nivel_implicito` fica congelado, rotulado** (D6). É o subcomando `nivel` do motor
  (justos.py:957-1000), não espelhado em lugar nenhum; trazê-lo ao vivo é uma peça de motor inteira para
  um número secundário. **Ponto para o controlador confirmar.**
- **D12 — A curva iso fica fora**, como o escopo manda: a §8.4 a lista como precomputada, os dois vetores
  são inalcançáveis hoje (`reversa_com_degrau`) e a 5F publicou `iso_nao_calculada`. O que muda é que a
  **limitação** passa a ser viva: o gatilho é `_algum_eixo_primario_sem_raiz`, que roda sobre as raízes
  vivas — some e reaparece com a edição.
- **D13 — Redesenho com `debounce`** (A13), no `laboratorio.js`, sobre o listener que já existe. É
  interface, não metodologia.

---

## Lote 1 — espelho e fachada (integração)

### Task 1 — a reversa ao vivo, com paridade

**Arquivos:** `skills/er-valuation/assets/motor_espelho.js`, `skills/er-valuation/assets/espelho_fachada.js`,
`skills/er-valuation/scripts/vetores_solver.py`, `tests/fixtures/vetores_solver.json` (regerada),
`tests/test_paridade_wrapper_js.py`, `tests/test_espelho_fachada_js.py`.

**Abre medindo (D4):** divergência de `curvatura_d2M_dx2` entre Python e JS sobre a faixa real de
`roic`/`roe`. O resultado da medição vai no relatório do lote e decide o comparador.

**Entra no espelho:** `faixaDeBusca(variavel, premissas)` (D2) · `alvoNormalizado(alvo, metrica, premissas)`
(o `conv`) · `capImplicito({...})` (D3) · `betaImplicito(saida, mercado)` · `leituraDoEixo(eixo, rota, saida, banda)`
na forma exata de `reversa.leitura_do_eixo` · `resolucaoDoEixo` · `tetoDoCrescimentoGratuito` ·
`limitacoesDaLeitura`. `resolverProblema` passa a recusar por `dominioCliRecusa` (D5).

**Fica no Python:** `sem_solucao`, `sugestao`, `guardas_v9_4`, `premissas_fixadas`, `nota_regime`,
`nivel_implicito` (D11), `iso` (D12).

**Interfaces produzidas:** `FachadaEspelho.avaliarCaso(caso)` ganha `reversa: {alvo, eixos:
{<eixo>: {leitura, resolucao}}, teto_do_crescimento_gratuito?, limitacoes}` quando o caso declara
`reversa`; `compararComResultados` cobre essas chaves. **Consumidas:** `caso.reversa`, `caso.mercado`,
`caso.metrica_base`, `resultados.reversa`.

**Testes-chave (um por comportamento):**
- **paridade:** `test_reversa_por_eixo_bate_com_o_wrapper` (novo `tipo:"reversa_eixo"` em
  `vetores_solver.json`, lado Python = `reversa.reverter` sobre um caso mínimo, comparando `leitura` +
  `resolucao`; contagem de raízes e tangenciais exata ANTES de qualquer número, como manda
  `test_paridade_solver_js.py`) — em `tests/test_paridade_wrapper_js.py`;
- **paridade:** `test_cap_implicito_bate_com_o_wrapper` (tipo `cap`: as quatro saídas, incluindo as duas
  sem número) — mesmo arquivo;
- **paridade:** `test_teto_do_crescimento_gratuito_bate_com_o_wrapper` (tipo `teto`);
- a fachada recusa o eixo por domínio da CLI quando o vetor editado cruza o limiar, e o motor de verdade
  confirma a recusa (`tests/test_espelho_fachada_js.py`, o padrão que a 4C já usa);
- `limitacoes` vive: a edição que fecha o eixo primário faz `iso_nao_calculada` desaparecer na mesma chamada.

### Task 2 — sensibilidades ao vivo, triângulo, teto da alavanca e os avisos da rampa

**Arquivos:** `motor_espelho.js`, `espelho_fachada.js`, `skills/er-valuation/assets/catalogo_apresentacao.json`,
`vetores_solver.py` + fixture regerada, `tests/test_paridade_wrapper_js.py`,
`tests/test_espelho_fachada_js.py`, `tests/test_catalogo_apresentacao.py`.

**Entra no espelho:** `grade1D`/`grade2D` devolvem também as chaves de diagnóstico por célula ·
`resolverTriangulo` (D7) · quarta entrada de `AVISOS_RAMPA` para `avisos_dominio` (A7).
**Entra na fachada:** `sensibilidades: {grades_1d, grades_2d}` no shape do `resultados` (com
`diagnosticos_unicos_chaves` e `diag` por célula) · `cenarios.<n>.teto_da_alavanca` (D10) · o `rir` como
número por cenário. **Entra no catálogo:** rótulo do teto da alavanca; classificação do `rir` no mapa de
insumos/conclusões (a trava da 5F reprova número novo sem classificação).

**Fica no Python:** `diagnosticos_unicos` (as MENSAGENS) — o espelho publica só chaves (A5).

**Testes-chave:**
- **paridade:** `test_grade_publica_as_chaves_de_diagnostico_da_celula` — compara **célula a célula**
  o conjunto de chaves, não a lista deduplicada (A5: dedup por mensagem × dedup por chave não têm o mesmo
  comprimento); a orientação não-quadrada da grade 2D continua exigida;
- **paridade:** `test_triangulo_resolve_a_terceira_variavel` — as três configurações de
  `{inputs, output}`, nas duas rotas, contra `g = rir × retorno` do caso;
- o cenário com `degrau_alerta` aceso sai marcado como não-cenário, e some a marca quando a edição apaga
  o alerta (a regra inegociável da §8.4 aplicada ao rótulo);
- `avisos_dominio`: `tax = −5` na rampa acende o aviso no espelho como acende no wrapper.

---

## Lote 2 — relatório e interface

### Task 3 — o badge no cabeçalho, e a reversa e as sensibilidades vivas na aba

**Arquivos:** `skills/er-relatorio/scripts/render.py`, `skills/er-relatorio/assets/template.html`,
`skills/er-relatorio/assets/laboratorio.js`, `skills/er-relatorio/assets/i18n/pt-BR.json`,
`skills/er-relatorio/SKILL.md`, `tests/test_relatorio_laboratorio.py`, `tests/test_relatorio_valuation.py`.

**No `render.py`:** o `div[data-laboratorio-badge]` sai de `_laboratorio_html` (1750) e entra em
`_valuation_html`, na `<section class="valuation-cabecalho">` (2684), na posição da §9 · `_congelados_html`
fica só com SOTP · `_o_que_esta_no_preco_html` perde o `reversa-congelado-nota` de topo (2347) e o
`nivel_implicito` ganha o rótulo próprio (D6/D11) · os eixos da reversa (`_eixo_da_reversa_html`, 2188),
a tabela 1D (`_grade_1d_html`, 1359) e o host da matriz 2D ganham âncoras de saída
(`data-laboratorio-saida`), e os vocabulários da leitura (`motivos_da_leitura`, `identificacoes`,
`posicoes_na_banda`, `limitacoes`) entram no payload como dicionário rótulo↔código, no padrão de
`_diagnosticos_do_catalogo` (1757).

**No `template.html`:** o bootstrap (776-778) localiza o badge por `document` e o passa a
`FleetLaboratorio.iniciar(raiz, dados, badge)`. **No `laboratorio.js`:** o badge vira parâmetro (A8);
`escrever` passa a repintar também os eixos da reversa, a tabela 1D e a matriz 2D (via `FleetSVG.matriz`);
`debounce` no listener (D13). Nenhuma linha de metodologia entra ali — a trava de
`tests/test_relatorio_fronteira.py` é a prova.

**Testes-chave:**
- o badge está no cabeçalho e **não** dentro de `[data-laboratorio]`, e `iniciar` o pinta a partir do
  parâmetro — com a prova de que o caminho antigo (busca descendente) devolveria `null`;
- badge vermelho continua travando a edição depois da mudança;
- reversa e sensibilidades **não** aparecem mais em `_congelados_html`, e `nivel_implicito` aparece
  rotulado (D6);
- em node, uma edição move a raiz do eixo de custo de capital e o `motivo` na mesma chamada (§8.4).

### Task 4 — triângulo como controle, ponte editável no degrau, derivação inline e teto rotulado

**Arquivos:** `render.py`, `laboratorio.js`, `skills/er-relatorio/assets/svg.js` (só se o waterfall
precisar de âncora semântica), `template.html`, `i18n/pt-BR.json`, `SKILL.md`,
`tests/relatorio_apoio.py` (variantes compostas), `tests/test_relatorio_laboratorio.py`,
`tests/test_relatorio_svg_js.py`.

**No `render.py`:** controle do triângulo por cenário (um seletor da configuração + o campo do `rir`
quando ele for input), com rótulos de `catalogo.variaveis_do_triangulo` e `catalogo.premissas.<rota>` —
o `_rotulo_do_triangulo` (2023) já resolve os dois · linha de entrada por parcela da ponte
(`data-ponte-linha`, D8), ao lado do host do waterfall · `_derivacao_da_premissa_html`, composto de
`entrega.ledger.registros` casados por `usado_em` contra `cenarios.<cenário>.premissas.<chave>` e
`ponte.<linha>` (D9) · rótulo de não-cenário no cartão do cenário (D10).

**No `laboratorio.js`:** colher a configuração do triângulo e as linhas da ponte junto com as premissas;
redesenhar o waterfall. **Consome:** `FachadaEspelho.avaliarCaso` (triângulo resolvido, `nd_efetivo`
recomposto, `teto_da_alavanca`), `FleetSVG.waterfall`.

**Testes-chave:**
- trocar a configuração do triângulo muda o preço e **não** altera os valores originais exibidos nem o
  que o botão de restaurar devolve (§8.3, "sem sobrescrever a calibração original");
- editar `divida_bruta` no degrau move `nd_efetivo`, o preço e o waterfall na mesma ação;
- uma premissa sustentada por registro do ledger mostra claim, fórmula e fonte; uma premissa sem
  registro não ganha linha nenhuma (D9);
- o cenário com o teto da alavanca sai rotulado como não-cenário na aba.

---

## Dívidas registradas

- **A curva iso continua desligada** (D12): a §8.4 a lista como precomputada e os dois vetores são
  inalcançáveis hoje (`reversa_com_degrau`). `iso_nao_calculada` fica publicada — agora viva.
- **`nivel_implicito` congelado e rotulado** (D11) — o subcomando `nivel` do motor não tem espelho.
- **`--rir-externo` não entra** (D2): o caso não tem campo para ele, e nenhuma fixture o declara.
- **`curvatura` possivelmente fora do comparador** (D4), conforme a medição. A exibição continua.
- **Edição dentro do SVG do waterfall** (D8) — hit-testing e input flutuante ficam fora.
- **`avisos_dominio` das rotas firm/equity** continuam descartados por `_monta_cenario` (A7): o espelho
  os produz, mas o wrapper não os publica fora da rampa. Assimetria herdada, não aberta aqui.
- **Nenhuma conferência visual no navegador** pelo agente (dívida contínua desde a 5F): a checagem de
  blockers é do controlador, com o relatório real.
- **Persistir ou exportar o estado editado** continua fora, desde a 5C.
