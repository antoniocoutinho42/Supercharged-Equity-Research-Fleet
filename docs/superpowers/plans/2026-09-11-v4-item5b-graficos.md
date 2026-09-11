# Item 5, fatia B — gráficos: gramática, uPlot e módulo SVG

> **Para agentes:** REQUIRED SUB-SKILL: `superpowers:subagent-driven-development`. Calibragem de rigor em
> vigor (ledger, 26/08/2026): implementação simples, testes que discriminam a matemática e os contratos,
> sem revisor por task, **uma** revisão final da fatia. Achado não material: registre no relatório e siga.

**Goal:** um exhibit declarado na análise vira gráfico validado e rastreável no HTML — cartesiano no uPlot
vendorizado, não-cartesiano num módulo SVG próprio — e o builder recusa série não rastreável ou tipo fora do
enum.

**Architecture:** a gramática da §10 do desenho entra como `analise.exhibits[]` no contrato `entrega/1`
(aditivo, vocabulário fechado como todo o resto). **A spec não declara número nenhum**: série `direta` aponta
para um campo de `entrega.dados`, `derivada` traz uma fórmula sobre campos do mesmo dataset, `engine` aponta
para um caminho de `resultados` — o builder lê os valores. É mais forte que o §10 pede e que o legado fazia
(declarar os números e conferir depois): o que o relatório não declara não pode divergir. Renderização em dois
módulos JS: `graficos.js` (adaptador fino sobre o uPlot, formatação pelo dicionário) e `svg.js` (funções puras
que devolvem string SVG, rodáveis em node para teste e no browser para o laboratório da 5C).

**E3 (emenda do desenho §15):** o waterfall lê `resultados.ponte.parcelas` com os sinais que o wrapper já
guardou; a matriz lê `resultados.sensibilidades`; rótulos vêm do catálogo. O relatório desenha; não calcula.

**Tech Stack:** Python stdlib; uPlot v1.6.27 (MIT, vendorizado); JS sem dependências; pytest + node.

## Global Constraints

- As da 5A continuam valendo: E3 mecanizada pelo teste de fronteira; nada de aritmética de valuation fora do
  motor; HARD FAIL não emite; raiz única; texto de interface só pelo dicionário; determinismo byte a byte.
- **uPlot byte a byte**: copie `uPlot.iife.min.js`, `uPlot.min.css` e `uPlot.LICENSE` de
  `skills/er-relatorio-html/assets/` para `skills/er-relatorio/assets/`, acrescente os dois primeiros ao
  `.gitattributes` com `-text`, e trave por teste de sha256 contra a cópia legada (que sai só no item 10).
- **`string.Template`**: o uPlot minificado tem `$` no código. Ele entra como **valor** substituído
  (`$js_uplot`), nunca colado no arquivo do template — senão a substituição estoura ou corrompe o script.
- **JSON embutido** em `<script type="application/json">` escapa `</` como `<\/`. Esta fatia é a primeira a
  embutir JSON; a revisão da 5A registrou a regra como ainda não implementada.
- Nenhum recurso externo: a regra `relatorio_nao_autocontido` já é lista branca (`#fragmento` ou `data:`).
- `vendor/` read-only; suíte em primeiro plano; commit assim que verde, antes do relatório; mutação, teste e
  restauração num único comando. Baseline **600 passed, 1 skipped**.

## Decisões de desenho — tomadas, com a razão

- **G1 — `analise.exhibits[]`.** Vocabulário fechado por nível:
  `{id, pergunta, tipo, series[], overlays[]?, nota_janela?, caption?, vinculo?}`. `pergunta` é obrigatória —
  é o campo que a §10 criou para impedir gráfico decorativo.
- **G2 — Enum fechado de `tipo`.** Cartesianos: `linha`, `barras`, `area`, `empilhado`, `dispersao`.
  Próprios: `waterfall`, `matriz`. Mais `tabela` (cada série é uma coluna, o `x` do dataset é a primeira).
  Fora do enum → recusa de contrato (código 1), como a §10 manda. **`decomposicao` não entra nesta fatia**: só a
  5D teria consumidor, e construir para consumidor inexistente é o erro que o `degrau` já ensinou a evitar.
- **G3 — `entrega.dados` (novo, opcional, no topo).** `{<id>: {"ledger": [...], "x": [...], "campos": {<campo>: [...]}}}`.
  `ledger` lista os registros de onde os números vieram (o schema do ledger é do item 7; aqui só a referência).
  Série `direta`: `{"derivacao": "direta", "fonte": "<dataset>.<campo>"}`. Série `derivada`:
  `{"derivacao": "derivada", "fonte": "<dataset>", "formula": "<expr>", "formula_nota": "<texto>"}` — o dataset é
  **declarado**, simétrico à `direta`, e a fórmula roda sobre os campos dele, recomputada por um avaliador fechado
  (só `+ - * / ( )`, números e nomes de campo — nada de `eval`). *Correção da primeira versão deste plano, que dizia
  só "campos do mesmo dataset" sem dizer qual: a implementação teve de inferir pelo `id` do exhibit, o que acopla a
  identidade do gráfico à do dado e impede dois gráficos de compartilharem um dataset. Convenção implícita perde
  para declaração explícita, como já foi decidido no `cenario_base`.* Série `engine`:
  `{"derivacao": "engine", "chave": "resultados:<caminho>"}` — não usa dataset.
- **G4 — Overlays sem número declarado.** `{"chave": "caso:<caminho>"|"resultados:<caminho>", "rotulo"?}` — o
  builder resolve o valor. O legado declarava `valor` e conferia contra a chave; aqui não há o que conferir.
- **G5 — Cobertura por pergunta da tese fica para a 5D**, onde as perguntas nascem. Nesta fatia não existem
  perguntas: `vinculo`, quando presente, é validado só como lista de textos; o cruzamento com os ids reais é da 5D.
- **G6 — Módulo SVG em JS, não em Python.** O laboratório da 5C precisa redesenhar waterfall e matriz ao vivo;
  duas implementações divergiriam. Funções puras, testadas em node, usadas pelo HTML estático e pelo laboratório.
- **G7 — Exhibits aparecem numa seção da aba Tese.** A 5D os reposiciona sob as perguntas, quando elas
  existirem; nesta fatia, uma seção própria, na ordem declarada.
- **G8 — Rastreabilidade também aparece na Evidência**: uma linha por série, dizendo de onde veio (dataset e
  campo, fórmula, ou caminho de resultado) — o mesmo espírito do log de placeholders.

**Fora desta fatia — registrado:** cobertura por pergunta (5D); edição ao vivo de gráfico (5C); `ficha_tecnica`
com `str()` cru (5D); qualquer gráfico que exigisse conta de valuation nova (não existe: waterfall e matriz leem
`resultados`).

## File Structure

| Arquivo | Responsabilidade |
|---|---|
| `skills/er-relatorio/scripts/exhibits.py` (novo) | Contrato dos exhibits e de `dados`; resolução de séries e overlays; avaliador fechado da fórmula |
| `skills/er-relatorio/scripts/entrega.py` | Vocabulário: `dados` no topo, `exhibits` em `analise` |
| `skills/er-relatorio/scripts/qc.py` | Regras novas de rastreabilidade |
| `skills/er-relatorio/scripts/render.py` | Seção de exhibits na Tese; dados embutidos; linhas de rastreabilidade na Evidência |
| `skills/er-relatorio/assets/template.html` | `$css_uplot`, `$js_uplot`, `$js_graficos`, `$js_svg`, `$dados_exhibits` |
| `skills/er-relatorio/assets/graficos.js` (novo) | Adaptador sobre uPlot: spec resolvida → gráfico |
| `skills/er-relatorio/assets/svg.js` (novo) | `waterfall` e `matriz` → string SVG (funções puras) |
| `skills/er-relatorio/assets/uPlot.*` (novos) | Vendor MIT, byte a byte do legado |
| `tests/test_relatorio_exhibits.py`, `tests/test_relatorio_svg_js.py` (novos) | Contrato/QC e o módulo SVG em node |

---

## Task 1: contrato dos exhibits e rastreabilidade (sem render)

**Files:** create `skills/er-relatorio/scripts/exhibits.py`, `tests/test_relatorio_exhibits.py`;
modify `skills/er-relatorio/scripts/entrega.py`, `skills/er-relatorio/scripts/qc.py`,
`tests/relatorio_apoio.py` (compor `dados` e `exhibits` nas raízes de teste).

**Interfaces — produz:**
- `exhibits.resolver(entrega: dict) -> tuple[list[dict], list[dict]]` — exhibits com séries e overlays já
  resolvidos em números, mais o log de rastreabilidade (uma entrada por série/overlay: `{exhibit, serie, origem,
  detalhe}`).
- `exhibits.TIPOS_CARTESIANOS`, `exhibits.TIPOS_PROPRIOS`, `exhibits.TIPOS` (enum fechado, G2).
- `exhibits.avaliar_formula(expr: str, campos: dict[str, list]) -> list[float]` — avaliador fechado; recusa
  qualquer nome fora de `campos` e qualquer operador fora de `+ - * / ( )`.
- `entrega`: `CHAVES_DE_TOPO` ganha `dados`; `CHAVES_DE_ANALISE` ganha `exhibits`; vocabulários fechados novos
  para exhibit, série, overlay e dataset.

**Regras (recusa de contrato, código 1):** `tipo` fora do enum; `pergunta` ausente ou vazia; exhibit sem `series`;
chave desconhecida em qualquer nível.

**Regras de QC (HARD FAIL, salvo indicação):**
- `serie_nao_rastreavel` — `fonte` aponta para dataset/campo inexistente, ou `chave` para caminho inexistente em
  `resultados`/`caso`.
- `formula_invalida` — sintaxe fora do avaliador fechado, nome fora dos campos do dataset, ou resultado não finito.
- `overlay_nao_resolvido` — a `chave` não resolve em número.
- `serie_de_tamanho_incompativel` — série com comprimento diferente do `x` do dataset.
- `serie_curta_sem_nota_janela` — **QUALITY WARNING**: menos de 10 pontos sem `nota_janela` (regra que o QC do
  legado já tinha, e que a §11 classifica como "exhibit fraco").

**Testes (`tests/test_relatorio_exhibits.py`):** um exhibit `linha` com série `direta` resolve os números do
dataset; `derivada` com `(ebitda / receita)` reproduz a margem esperada; `engine` puxa um caminho real de
`resultados` (por exemplo o preço por ação de um cenário); `fonte` para campo inexistente → HARD FAIL nomeando
exhibit e série; fórmula com `__import__` ou nome estranho → HARD FAIL; overlay com chave inexistente → HARD
FAIL; série curta sem `nota_janela` → QUALITY WARNING que **não** impede emitir; `tipo` inventado → código 1.

**Prova de falseabilidade:** aceite silenciosamente um campo inexistente em `serie_nao_rastreavel`, confirme que
um exhibit com fonte quebrada passa a emitir, restaure.

---

## Task 2: cartesianos — uPlot vendorizado e adaptador

**Files:** copy `uPlot.iife.min.js`, `uPlot.min.css`, `uPlot.LICENSE` para `skills/er-relatorio/assets/`;
create `skills/er-relatorio/assets/graficos.js`, `tests/test_relatorio_graficos.py`;
modify `.gitattributes`, `render.py`, `template.html`, `assets/i18n/pt-BR.json`.

**Interfaces — produz:** `FleetGraficos.renderizar(hostEl, specResolvida, dicionarioFmt)` — spec **já resolvida**
(números dentro), sem nenhuma leitura de contrato no browser; `FleetGraficos.formatar(valor, unidade, idioma)`.

**Detalhes que um implementer apressado erra:**
1. **`$` do uPlot**: entra como valor (`$js_uplot`), nunca no arquivo do template.
2. **Formatação**: pt-BR pelo dicionário (milhar `.`, decimal `,`) — o adaptador legado usava `en-US`.
3. **JSON embutido**: escapa `</` como `<\/`.
4. **Sem rede**: nada de fonte, CDN ou imagem externa; a regra de autocontenção reprova.
5. **Determinismo**: o HTML tem de sair byte a byte igual para a mesma entrada — nenhuma id gerada por relógio
   ou aleatório.

**Testes:** sha256 do uPlot igual ao do legado; o HTML de uma entrega com dois exhibits contém os dois hosts e o
JSON com os números resolvidos; nenhum recurso externo; byte a byte em duas execuções; o dicionário tem toda
chave nova. **Prova de falseabilidade:** troque a formatação para `en-US`, confirme vermelho, restaure.

---

## Task 3: módulo SVG — waterfall, matriz e decomposição

**Files:** create `skills/er-relatorio/assets/svg.js`, `tests/test_relatorio_svg_js.py`;
modify `render.py`, `template.html`, `assets/i18n/pt-BR.json`.

**Interfaces — produz:** `FleetSVG.waterfall(parcelas, opcoes) -> string` e
`FleetSVG.matriz(grade, opcoes) -> string`. Funções **puras**:
mesma entrada, mesma string; todo texto escapado; nenhuma dependência de DOM (rodam em node).

**O que cada uma desenha, e de onde:**
- `waterfall`: a ponte do caso — `resultados.ponte.parcelas`, cada uma com `rotulo`, `valor` e `sinal` que o
  wrapper já guardou, fechando em `nd_efetivo`. A aba Valuation passa a mostrá-la.
- `matriz`: uma grade de sensibilidade de `resultados.sensibilidades` (`pontos_x`, `pontos_y`, `celulas` com
  `valor`). Marca a célula do caso-base: aquela cujo `x` (e `y`) é **exatamente** o valor da premissa
  correspondente no cenário-base — os dois números saem do mesmo `caso.json`, então a igualdade é exata. Se
  nenhuma célula casar, não marca nenhuma.

**Testes (`tests/test_relatorio_svg_js.py`, rodando node como os harnesses de paridade já fazem):** o waterfall de
uma ponte real de fixture tem uma barra por parcela e fecha no total; a matriz de uma grade real tem
`len(pontos_x) × len(pontos_y)` células e marca a do caso-base; uma grade cujos pontos não contenham a premissa
base não marca nenhuma; texto com `<` sai escapado; a mesma entrada dá a mesma string. **Prova de falseabilidade:** inverta o sinal de uma parcela no waterfall, confirme vermelho, restaure.

---

## Verificação final da fatia 5B

Uma revisão (opus). Material: um número no gráfico que não venha de `dados`/`resultados`; uma série que o QC
deixe passar sem rastreabilidade; recurso externo; perda de determinismo; ou qualquer conta de valuation que
tenha escorregado para o relatório (E3). Suíte inteira, fixtures byte a byte, `vendor/` limpo.
