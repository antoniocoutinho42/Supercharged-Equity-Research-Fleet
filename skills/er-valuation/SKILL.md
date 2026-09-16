---
name: er-valuation
description: USE QUANDO montar o caso de valuation de uma análise, rodar o motor congelado por cenário, compor a ponte para preço ou interpretar o resultados.json. É a camada de orquestração entre a análise e a metodologia congelada. NÃO use para coletar evidência (er-evidencia), compor o relatório (er-relatorio) nem conduzir a análise (er-analise); e não use como fonte de metodologia — essa é er-multiplos-justos.
---

# er-valuation — wrapper de orquestração do motor congelado

Esta camada existe para uma coisa: transformar um caso declarado em resultado
auditável **sem tocar na conta**. Toda a matemática de valuation vem do motor
congelado; aqui só se monta entrada, soma linha de balanço declarada e
normaliza saída.

## O que faz

- **Contrato do caso** — valida o `caso.json` e recusa o que estiver incompleto.
- **Rota canônica** — traduz a rota declarada no subcomando certo do motor.
- **Cenários** — roda cada cenário com o vetor de premissas dele.
- **Ponte para preço** — soma as linhas de balanço declaradas num líquido e
  entrega ao motor, guardando cada parcela com seu sinal para o waterfall.
- **Normalização da saída** — junta múltiplos, valor, diagnósticos e a
  coerência do vetor num `resultados.json` determinístico.
- **Reversa por eixo** — dado o preço observado, resolve no motor o menu de
  reconciliação (custo de capital implícito, obrigatório, e os demais eixos
  declarados), com o beta implícito confrontado contra a banda de mercado
  quando ela é declarada. Cada eixo devolve o shape que o motor deu — nunca
  uniformizado — mais uma chave `resolucao` (`{"resolveu": bool, "motivo":
  str}`) do wrapper, ao lado do payload do motor: o ponto único onde
  perguntar "este eixo resolveu?" sem ter que conhecer os quatro shapes
  possíveis (raiz, raiz vazia, CAP alcançável/fora da faixa, CAP
  indefinido por spread não positivo). Ao lado dos dois, a chave `leitura`
  (`reversa.leitura_do_eixo`), a forma normalizada que o relatório lê para
  mostrar o que está no preço sem aprender as saídas do motor: `premissa`,
  `unidade` e `unidade_da_curvatura` (chaves de `catalogo.unidades`),
  `motivo` (`reversa.MOTIVOS_DA_LEITURA`), `raizes` (`valor`,
  `identificacao` de `reversa.IDENTIFICACOES`, `intervalo`, `curvatura` —
  cada raiz pareada com a identificação pela ordem em que o motor as
  devolve), `tangenciais`, `cap_anos` e, no eixo de custo de capital, `beta`
  (`valor`, `posicao` de `reversa.POSICOES_NA_BANDA`, `distancia`, `banda`,
  `unidade`). Com um eixo primário sem raiz, o teto do crescimento gratuito
  roda e publica também `chave`, o múltiplo que carrega.
- **Grades de sensibilidade** — constrói, célula a célula no motor, as
  grades 1D e 2D de preço por ação que o caso declarar. Cada célula é um
  subprocesso do motor — a soma de células declaradas (`grades_1d` +
  `grades_2d`, cada grade 2D contando `len(pontos_x) x len(pontos_y)`) tem
  um teto padrão (2.000) recusado no gate, antes de qualquer chamada ao
  motor; `sensibilidades.limite_de_celulas` levanta ou reduz esse teto
  deliberadamente (ver "Contrato do caso").
- **SOTP (soma das partes)** — soma o EV de cada parte (segmento
  economicamente distinto, ou base instalada x capital novo numa safra),
  aplica os ajustes de topo e cruza a ponte do caso uma única vez — nunca
  por parte. Só nas rotas que produzem EV (`firm`, `rampa`); a rota
  `equity` não admite o bloco.
- **Rota rampa** — composição bifásica (rampa de utilização seguida de
  expansão), costurada num ano-delimitador que o caso declara; `EV`,
  `Equity` e preço por ação saem prontos do motor, como na rota `firm`.
- **Degrau (Gate 3)** — bloco opcional `degrau`, só na rota `equity`:
  aplica capacidade ociosa de balanço como rentabilidade × h (g inalterado,
  rentabilidade terminal parada, fator de captura só sobre o incremento
  via transição `rampa`/`pontual`). O preço do cenário passa a ser o COM
  degrau; o SEM degrau fica ao lado em `sem_degrau`, e
  `divergencia_de_base_%` compara os dois. Recusado junto de `reversa`,
  `sensibilidades` ou `sotp` (limitação declarada desta fatia). Metodologia,
  `m` (eficiência marginal) e as quatro travas obrigatórias:
  `vendor/multiplos-justos/references/aplicacao.md` §8.

## O que NUNCA faz

- Aritmética de valuation fora do motor. Nenhuma fórmula é reescrita aqui.
- Ajuste "conservador", arredondamento de conveniência ou correção de um
  output do motor. O que o motor devolve é o que sai.
- Default para escolha que a metodologia declara **sem default**. Caso
  incompleto é **recusado**, com o campo e a razão nomeados — a escolha é do
  analista, e silenciá-la com um padrão de fábrica seria decidir por ele.
- Deixar um `null` do motor virar número ou vazar para `resultados.json`. O
  serializador do motor congelado converte todo float não-finito (NaN,
  Infinity) em `null` e sai com código 0 mesmo assim — todo valor que este
  wrapper lê ou copia da saída do motor (EV, Equity, preço por ação,
  múltiplos) é checado; um `null` vira recusa nomeada, ecoando os
  diagnósticos do próprio motor, nunca um número inventado nem um `null`
  silencioso no arquivo final.

## Módulos

| Arquivo | Responsabilidade |
|---|---|
| `scripts/caso.py` | Carrega e valida o caso; recusa omissão de escolha sem default |
| `scripts/motor.py` | Monta o argv por rota e executa o motor congelado |
| `scripts/ponte.py` | Soma as linhas da ponte num líquido, com sinal por parcela |
| `scripts/reversa.py` | Resolve o menu de reconciliação por eixo e o beta implícito |
| `scripts/sensibilidades.py` | Constrói as grades 1D/2D célula a célula no motor |
| `scripts/sotp.py` | Soma o EV das partes de uma SOTP e cruza a ponte única no topo |
| `scripts/diagnosticos.py` | Classifica mensagem do motor -> chave pública de diagnóstico |
| `scripts/avaliar.py` | Orquestra cenários × rota e escreve o `resultados.json` |

## Como rodar

```bash
python skills/er-valuation/scripts/avaliar.py <caso.json> --out <resultados.json>
```

Caso inválido, ou motor que falhou (código != 0, saída não é JSON válido,
timeout, ou um `null` onde deveria haver número), sai com código 1 e a razão
em stderr. O motor é chamado no interpretador corrente, com utf-8 fixo,
bytecode desligado e `--moeda` sempre repassado — a árvore congelada não é
suja nem pelo uso.

## Contrato do caso

Campos de topo: `companhia`, `moeda`, `data_analise`, `preco` (valor, fonte,
data), `rota`, `metrica_base` (tipo, valor, fonte), `acoes_diluidas`,
`cenarios`. A rota `firm` exige o bloco `ponte`; a rota `equity` o proíbe —
não há ponte de dívida quando o resultado já é do acionista.

Cada cenário declara `ancora` (o observável de que ele vem), `triangulo`
(quais duas variáveis são input e qual é output) e `premissas`. Cenário sem
âncora é cenário inventado; cenário sem a configuração do triângulo esconde
a taxa de reinvestimento que ele implica.

Bloco opcional `mercado` (obrigatório, com `rf` e `erp`, quando o caso
declara `reversa`): `rf` e `erp` são declarados em **pontos percentuais**
(`12.0` significa 12%, nunca `0.12`) — a mesma convenção de `raizes_*_%`
que o motor devolve. Um valor no intervalo aberto `0 < x < 1` é recusado:
nenhuma taxa livre de risco nem prêmio de risco de mercado abaixo de um
ponto percentual ocorre na prática, então esse intervalo só pode ser uma
fração digitada por engano, não uma taxa válida. `erp` também é recusado
quando `<= 0` — é o denominador da inversão do CAPM em beta implícito.

Bloco opcional `sensibilidades`: `cenario` (nome de um cenário declarado),
`grades_1d` e `grades_2d`. Cada célula de grade é um subprocesso do motor
congelado (não uma conta em memória), e a soma de células declaradas —
`grades_1d` + `grades_2d`, cada grade 2D contando `len(pontos_x) x
len(pontos_y)`, nunca a soma das duas dimensões — tem um teto **padrão de
2.000 células** (~3 min ao custo medido nesta máquina em 2026-08-24,
0,093 s/célula), recusado no gate — dentro de `caso.validar`, antes de
`avaliar` chamar o motor para qualquer coisa — nomeando quantas células
foram declaradas e o tempo estimado. Campo opcional
`sensibilidades.limite_de_celulas` (número finito e positivo): levanta o
teto padrão deliberadamente quando a rodada precisa de mais células, ou
reduz — um limite abaixo do padrão também é uma escolha válida do
analista, mais restritiva que o padrão de fábrica.

Campo opcional-condicional `cenario_base`: nome de um cenário declarado em
`cenarios`. Obrigatório quando o caso declara mais de um cenário — sem essa
declaração não há como saber qual preço é "a resposta" (a `manchete`, ver
abaixo); implícito (dispensável) quando há um só cenário.

Bloco opcional `fronteira_de_escopo` (§14 do desenho): declara que a
companhia está fora do escopo da metodologia como métrica-manchete. `classe`
é uma de `vida_economica_finita` (mineração, óleo e gás, concessão com
termo), `reit_imobiliaria` ou `pre_lucro` — fora desse vocabulário, recusa
nomeando a classe, com sugestão; `arquitetura_dominante` (a arquitetura
necessária) e `razao` (por que o caso está fora) são textos não vazios, que o
relatório exibe como prosa auditável — dígito só por placeholder
(`{{livre:...}}`, `{{caso:...}}`, `{{resultados:...}}`); o bloco não aceita
outra chave, e nulo é ausência. Sob fronteira declarada a análise continua,
sem preço-alvo de manchete — regra do relatório, que lê
`resultados.fronteira_de_escopo` e o mapa `conclusoes_de_valor` do catálogo.

Bloco opcional `metrica_forward` (`{tipo, valor, periodo, fonte}`): a métrica
forward (consenso, guidance) que o múltiplo de tela forward usa no
denominador — fato de mercado com proveniência, nunca uma escolha do wrapper.
`tipo` igual ao de `metrica_base`, `valor` finito e positivo, `periodo` e
`fonte` textos não vazios, nenhuma outra chave (recusa com sugestão); nulo é
ausência. Recusado na rota `rampa` e junto de `degrau`: EV/EBITDA do ano 0 e
P/VP com degrau não têm forward.

Campo opcional `escala_monetaria`: a escala em que os montantes do caso estão
declarados — `milhares`, `milhoes` ou `bilhoes` (`caso.ESCALAS_MONETARIAS`;
fora disso, recusa nomeando, com sugestão); nulo é ausência. Não entra em
conta nenhuma: o relatório a aplica às unidades que o catálogo marca com
`escala_monetaria` (hoje só `moeda`, nunca preço por ação).

Bloco opcional `conservacao_de_capital`
(`{capex_total: {valor, fonte, ano_base}, dwc: {valor, fonte}}`): a verificação
da conservação de capital da metodologia — o capital consumido (capex total
mais ΔWC) contra os encargos de reposição e de crescimento do vetor de cada
cenário. Só na rota `firm` com métrica `EBITDA` (fora dela, recusa nomeada: o
motor só confronta a identidade sobre o EBITDA declarado, e a rota rampa a
garante por construção); `capex_total.valor` finito e positivo, `dwc.valor`
finito, as duas fontes textos não vazios, `ano_base` `corrente` ou
`guidance_longo_prazo` (`caso.ANOS_BASE_DO_CAPEX`), nenhuma outra chave em
nível nenhum; nulo é ausência.

Bloco opcional `escolhas_metodologicas`: a lista das escolhas metodológicas da
metodologia (as dez de `references/aplicacao.md` §5b, item 4), **declaradas pelo
analista** — o wrapper nunca avalia gatilho, só precifica. Cada entrada traz
`chave` (uma de `caso.ESCOLHAS_METODOLOGICAS`; fora do vocabulário, recusa com
sugestão — e repetida, recusa), `no_caso_base` (`central` ou `alternativa`,
`caso.POSICOES_DA_ESCOLHA`), `sobreposicoes` (mapa não vazio de alvos do caso →
valor, que leva o cenário da manchete ao outro ramo) e, opcional,
`gatilho_disparou: {observavel}` (texto não vazio). Nenhuma outra chave, em
nível nenhum; lista vazia e nulo são recusa e ausência, respectivamente.

Os **alvos** de uma sobreposição são os que as dez escolhas de fato movem, e nada
além deles — um alvo fora do conjunto é recusa nomeada, com sugestão:

- cada **premissa numérica da rota**, com número finito;
- a **convenção terminal** `tv` (`PREMISSAS_NAO_NUMERICAS_DA_SOBREPOSICAO`), com um
  código de `caso.TV_CANON` — a única premissa não numérica alcançada, porque é a
  única cujo vocabulário este gate conhece; `politica_tv` e `mid_year` ficam de fora;
- `metrica_base` (só `valor`, finito — o tipo é da rota e não muda por escolha);
- `ponte` (as linhas de `caso.CAMPOS_DA_PONTE`, valores finitos), só nas rotas que
  declaram o bloco.

A sobreposição é uma sobreposição **parcial do caso**, com a estrutura do caso — e
não um caminho textual (`"ponte.divida_bruta"`), porque `_validar_chaves_enderecaveis`
recusa qualquer chave do caso com `.`: o caminho de um número do caso separa
segmentos por `.` no mapa de insumos, no ledger e nos placeholders.
Recusado inteiro junto de `sotp` (com soma de partes o preço da manchete vem da
composição das partes, e o impacto compararia bases que não se correspondem);
`leitura_de_capacidade` é recusada pelo nome (trocaria a arquitetura do vetor, não
uma sobreposição — fora desta versão) e `alavanca_de_lucro` só é aceita num caso
que declare `degrau`.

Bloco opcional `retorno_exigido` (`{taxa}`): que valor resulta ao exigir retorno
de X%. `taxa` em **pontos percentuais** (a convenção de `wacc`/`ke`), finita,
acima de zero e até 100; nenhuma outra chave. Recusado junto de `sotp` (a
manchete vem da composição das partes, cada uma com o próprio custo de capital) e
de `degrau` (a manchete é o P/VP justo com degrau). É leitura, nunca fair value —
o rótulo é do relatório.

Campo opcional `pesos_de_probabilidade` (`{<cenário>: pp}`): os pesos, em pontos
percentuais, de que sai o valor ponderado. Dois cenários ou mais, cada nome
declarado em `cenarios`, cada peso finito e não negativo, soma **exatamente**
`caso.SOMA_DOS_PESOS` (100) — o wrapper não normaliza em silêncio. Recusados
junto de `sotp`, que tem um preço só. São julgamento do analista, fora da fórmula
do valuation, e fora dos insumos que exigem proveniência.

Bloco opcional `cross_check` (`{rota, metrica_base: {tipo, valor}, ancora,
premissas}`): o segundo método declarado — o vetor coerente da rota OPOSTA. `rota`
é uma rota conhecida e diferente da do caso (a do caso é recusada: não seria
segundo método); uma rota que atravessa a ponte da dívida (`firm`, `rampa`) exige
que o caso declare `ponte` — sem ela não existem inputs coerentes, e a
metodologia manda declarar a ausência em vez de calcular. `metrica_base.tipo` é
uma métrica daquela rota, `ancora` é texto não vazio e `premissas` é um vetor
COMPLETO dela, validado pela mesma regra dos cenários (obrigatórias presentes,
desconhecidas recusadas, numéricas finitas).

Schema completo, executável: `tests/fixtures/caso_minimo_firm.json` e
`tests/fixtures/caso_minimo_equity.json`.

## Contrato de saída (`resultados/1`)

Além dos campos que `avaliar()` sempre produziu (`cenarios`, `ponte`, e os
blocos aditivos `reversa`/`sensibilidades`/`sotp`/`degrau`), `resultados.json`
publica, como contrato versionado, o que o relatório (`er-relatorio`) precisa
para exibir sem reimplementar metodologia — emenda E3 do desenho
(`docs/desenho-arquitetura-v4.md` §15: o relatório nunca duplica cálculo ou
convenção que já mora aqui):

- `versao_contrato` — `"resultados/1"` nesta fatia; acréscimos compatíveis
  não mudam o literal, mudança incompatível vira `"resultados/2"`.
- `origem.caso_sha256` — sha256 do JSON canônico do caso **como carregado**
  (`sort_keys=True`, `separators=(",", ":")`, `ensure_ascii=False`, utf-8) —
  prova de correspondência com o `caso.json` de origem, sem rodar nada.
  `origem.metodologia` — nome e versão, lidos de
  `skills/er-multiplos-justos/manifest_vendor.json`.
- `manchete` — qual preço é "a resposta": o do SOTP quando o caso declara
  `sotp`; senão o do cenário-base (`cenario_base`), com o múltiplo que o
  wrapper já devolve para aquele preço e `convencao_terminal` — o código
  CANÔNICO da convenção 'tv' do cenário-base (`caso._tv_canon`, nunca o
  literal/alias declarado), rotulado pelo catálogo (`convencoes_terminais`);
  ausente quando a manchete vem do SOTP. Fora do degrau e da rampa, também
  `multiplo_forward` (`{chave, base, valor}`): o múltiplo justo forward do
  cenário-base, lido de `multiplos` pela chave forward da rota, com a mesma
  `base` do corrente.
- `mercado_tela` — o múltiplo de mercado (tela), sempre publicado — antes só
  existia dentro do bloco opcional `reversa`. Pareado com o múltiplo da
  manchete pela mesma `base`.
- `mercado_tela_forward` — o múltiplo de tela forward, sempre publicado:
  `{chave, base, valor, algebra, metrica}` quando o caso declara
  `metrica_forward` — a mesma conta de `mercado_tela`
  (`reversa.alvo_de_mercado`) com a métrica forward no denominador, e
  `metrica` com tipo, valor, período e fonte —, ou `null`.
- `escala_monetaria` — a escala dos montantes que o caso declara, ou `null`;
  sempre publicada.
- `cenarios.<n>.conservacao_capital` — só quando o caso declara
  `conservacao_de_capital`: a saída do motor para a verificação, íntegra
  (capital consumido, encargos de reposição e de crescimento, gap e `gap_%`,
  e o `ALERTA` ou a `leitura` do motor), mais `ano_base` e
  `diagnosticos_chaves` — `conservacao_capital_nao_fecha` quando o motor emite
  `ALERTA`, por presença (`avaliar._ALERTAS_DA_CONSERVACAO`). O limiar (10%) é
  do motor; o espelho o reproduz ao vivo (`motor_espelho.js:conservacaoCapital`),
  e a fachada publica a lista, a exibe e a compara.
- `diagnosticos_chaves` (por cenário) / `diagnosticos_unicos_chaves` (por
  grade de sensibilidade) — a chave pública de cada mensagem do motor
  (`diagnosticos.classificar`), paralela a `diagnosticos`/
  `diagnosticos_unicos` onde quer que a lista apareça (cenários,
  `sotp.partes[*]`, `reversa.teto_do_crescimento_gratuito`); na rota rampa,
  que não emite `diagnosticos`, as chaves de aviso presentes
  (`aviso_colheita`, `aviso_delator`, `aviso_gp`); e, num cenário com degrau,
  `degrau.diagnosticos_chaves` — a chave de cada alerta que o motor emitiu no
  nível-alvo (`degrau_alerta` ← `ALERTA`, `degrau_alerta_rir` ← `ALERTA_RiR`),
  por presença, ao lado da prosa do motor, que continua publicada para
  auditoria; e, depois delas, `degrau_divergencia_de_base` quando
  `|divergencia_de_base_%|` passa do limiar do wrapper
  (`avaliar._LIMIAR_DIVERGENCIA_DE_BASE_PCT`, fonte única, espelhado e travado
  em `motor_espelho.js`). A decisão "acima do limiar" é desta camada: a QC do
  relatório consome a chave e não compara limiar nenhum.
- `escolhas_metodologicas` — o painel de escolhas, sempre publicado (lista vazia
  sem declaração): por escolha declarada, `chave`, `no_caso_base`,
  `sobreposicoes` e `gatilho_disparou` como o caso os declarou, mais
  `preco_alternativa` (a CÓPIA do caso com as sobreposições aplicadas, precificada no
  cenário da manchete pelo mesmo caminho que o cenário percorreu — inclusive o
  degrau, e com o `nd_efetivo` recomposto por `ponte.compor` quando a sobreposição
  move uma linha de balanço),
  `impacto` (esse preço contra o da manchete, fração de comparação) e `material`
  (o módulo do impacto acima de `avaliar.LIMIAR_DE_ESCOLHA_MATERIAL`, o limiar de
  ~10% da metodologia). O relatório lê o booleano e nunca compara limiar nenhum.
- `empilhamento` — `{direcao, chaves}` quando duas ou mais escolhas têm o
  caso-base FORA da posição central e na mesma direção (`conservadora` quando o
  caso-base vale menos que o ramo central, `otimista` quando vale mais —
  `avaliar.DIRECOES_DO_EMPILHAMENTO`), ou `null`; sempre publicado. É a leitura de
  coerência interna dos cenários da metodologia, e nesta fatia é alerta de tela,
  não disclosure de QC.
- `retorno_exigido` — `{taxa, premissa_substituida, preco_acao}` quando o caso
  declara o bloco, ou `null`; sempre publicado. O preço é o do cenário da manchete
  com a premissa de custo de capital da rota substituída pela taxa
  (`caso.PREMISSA_DE_CUSTO_DE_CAPITAL_POR_ROTA`: WACC em firm e rampa, Ke em
  equity), pelo mesmo motor de sempre.
- `valor_ponderado` — `{valor, pesos}` ou `null`; sempre publicado. `valor` é a
  soma de peso × preço sobre os preços que os cenários já publicaram; `pesos` ecoa
  o que o caso declarou.
- `cross_check` — `{rota, preco_acao, diferenca_vs_manchete}` ou `null`; sempre
  publicado. O preço vem das mesmas funções de precificação, sobre o vetor da rota
  oposta que o caso declara; a diferença é fração de comparação contra a manchete,
  positiva quando o segundo método vale mais.
- `fronteira_de_escopo` — o bloco que o gate validou, ou `null`; sempre
  publicado (ver "Contrato do caso").
- `limitacoes` — lista de chaves, sempre publicada e possivelmente vazia, das
  limitações que o caso impõe à entrega. Primeiro a da reversa, que a Análise
  exige mas o gate recusa em combinações não implementadas:
  `reversa_na_rota_rampa` (rota `rampa`) e `reversa_com_degrau` (bloco
  `degrau`). Quem decide é `caso.reversa_indisponivel(caso)`, que consulta o
  mesmo registro de recusas que o gate aplica (`caso.LIMITACOES_DE_REVERSA`),
  nunca uma lista paralela; a trava de `tests/test_valuation_contrato.py`
  confere, fixture a fixture, que a chave sai publicada se e só se o gate
  recusa um bloco `reversa` válido — nas condições que as fixtures
  exercitam. Fora delas a falha é fechada: o gate recusa a reversa,
  `limitacoes` sai vazia e a Análise não emite (`analise_sem_reversa`). Por
  isso toda limitação nova entra com uma fixture, ou uma variante composta de
  `tests/relatorio_apoio.py`, que a exercite (a trava já o exige das
  registradas). Depois dela, as da leitura da reversa publicada
  (`reversa.limitacoes_da_leitura`, registro `reversa.LIMITACOES_DA_LEITURA`):
  hoje `iso_nao_calculada`, com o gatilho do teto — um eixo primário sem
  raiz, quando o motor manda rodar o teto e a curva iso-valor e o Fleet só
  roda o teto. As duas famílias nunca coexistem: uma limitação de reversa
  implica caso sem reversa. O relatório lê a chave, o rótulo e a declaração
  `afeta` do catálogo; a regra fica aqui.

Schema completo: `tests/test_valuation_contrato.py`, sobre as fixtures de
`tests/fixtures/caso_*.json`.

Conhecimento metodológico que o relatório precisa exibir mas não calcula
(bloco/unidade/rótulo de cada premissa, rótulo por convenção terminal
canônica — `convencoes_terminais`, fonte única, nunca duplicado por rota —,
rótulo e base de cada múltiplo, severidade e rótulo de cada diagnóstico,
texto do disclosure de divergência de base e o nome da chave que o dispara,
rótulo de cada classe de fronteira de escopo — `fronteiras_de_escopo` — e, de
cada limitação — `limitacoes` —, o rótulo e o bloco de `resultados` que ela
suprime, `afeta`: é por essa declaração, nunca pelo nome da chave, que a QC do
relatório sabe que uma limitação justifica a reversa ausente; a trava de
`tests/test_catalogo_apresentacao.py` amarra as que declaram `"reversa"` ao
registro que `caso.reversa_indisponivel` consulta, e as que declaram `"iso"`
a `reversa.LIMITACOES_DA_LEITURA`; e os vocabulários da leitura da reversa —
`eixos_de_reversa`, com o rótulo e `obrigatorio` amarrado a
`caso.EIXO_OBRIGATORIO`; `motivos_da_leitura`, `identificacoes` e
`posicoes_na_banda`, as tuplas de `reversa.py`; e `teto_do_crescimento_gratuito`,
com rótulo e texto; o rótulo de cada escala monetária (`escalas_monetarias`,
as do gate) e a marca `escala_monetaria` das unidades de montante; o quadro
"como o valor é formado" de cada rota (`formacao_do_valor`: a função de
cada premissa, em uma linha, e a síntese — texto de metodologia, nunca um
número); e o rótulo das variáveis do triângulo que não são premissa
(`variaveis_do_triangulo`); o rótulo de cada ano-base do capex
(`anos_base_do_capex`); e, em `disclosures.conservacao_de_capital`, o texto e a
chave da conservação de capital que não fecha; e o rótulo e o gatilho descrito de
cada escolha metodológica — `escolhas_metodologicas`, as dez do gate)
é publicado à parte,
como o catálogo de apresentação (A6):
`skills/er-valuation/assets/catalogo_apresentacao.json`, schema em
`tests/test_catalogo_apresentacao.py`.

**Conclusões de valor (`conclusoes_de_valor`).** Quais números de `resultados`
são conclusão de valor — o que, sob fronteira de escopo, a Tese não pode afirmar
e a Valuation só mostra como leitura condicional — é declaração desta camada,
nunca do relatório: `{<unidade>: [<padrão>]}`, cada padrão um caminho de
`resultados` em que `*` casa exatamente um segmento
(`cenarios.*.valor.preco_acao`, `sensibilidades.grades_2d.*.celulas.*.*.valor`),
e cada unidade do vocabulário `unidades` — a mesma que a grade de sensibilidade
publica para as suas células. Não é só o preço por ação: o upside (`fração`), o
múltiplo justo (`múltiplo`) e o valor da firma e do equity (`moeda`) dizem a
mesma coisa em outra unidade. O preço e o múltiplo de tela, a reversa, a ponte e
tudo o que o caso declara ficam fora. As travas de
`tests/test_catalogo_apresentacao.py`, sobre as fixtures: toda folha numérica que
o wrapper publica é conclusão de valor pelo mapa ou tem ali a razão declarada
para não ser (um número novo sem classificação reprova); nenhum padrão sem folha
que o exerça; nenhum caminho com duas unidades; o mapa não cobre `mercado_tela`
nem o que o caso declara; e toda célula de grade é coberta pela família da
unidade que a grade publica.

**Insumos do caso (`insumos_do_caso`).** Quais números do **caso** exigem
proveniência — o "número material do valuation" da §11 do desenho — também é
declaração desta camada, nunca do relatório: uma lista de padrões de caminho do
caso, com a gramática de `conclusoes_de_valor` (`*` casa exatamente um segmento;
o índice de lista é segmento). Insumo é o número que o motor ou o gate consome
para produzir ou balizar um número publicado: preço, métrica-base, ações e ponte;
toda premissa numérica de cenário, de parte de SOTP e do vetor `blended` da
materialidade; o topo do SOTP (custos corporativos, participações não
consolidadas e o desconto de holding, quando declarado); os números do degrau; e,
de `mercado`, `rf`, `erp` e a banda de beta observado, que alimentam a âncora
macro do gp e o beta implícito da reversa. Fica fora a configuração de execução
— os pontos declarados das grades de sensibilidade e o teto de células
(`limite_de_celulas`) —, e texto nunca é insumo. Todo insumo mapeado é material:
um limiar seria o relatório estimando impacto no valuation. O mapa é para o QC
do relatório: de cada folha numérica do caso que ele cobre, o QC exige o registro
do ledger que a sustenta (`ledger/1`, o contrato do `er-evidencia`, em
`skills/er-evidencia/assets/contrato_ledger.json`). As travas de
`tests/test_catalogo_apresentacao.py`, sobre as fixtures: toda folha numérica do
caso é insumo pelo mapa ou tem ali a razão declarada para não ser (um número novo
no caso reprova); nenhum padrão sem folha que o exerça; nenhum caminho casado por
dois padrões; e toda premissa `entrada: numero` presente nas fixtures cai no
mapa.

## Escopo desta fatia

Métricas suportadas: rota `firm` aceita `EBITDA` e `NOPAT`; rota `equity`
aceita `LL`; rota `rampa` aceita `EBITDA0` (o EBITDA do ano 0 — a escala
sobre a qual o motor reporta o múltiplo-manchete desta rota, `EV/EBITDA0`;
não é uma métrica normalizada como as demais). São as que o motor emite
diretamente — demais métricas são transformação de apresentação e entram
depois, com a álgebra exibida.

Ainda não implementados aqui: métricas de apresentação (`EBIT`, `EPS`,
`EBITDA/ação`, `NOPAT/ação`) — transformação sobre a métrica-base (divisão
por ações, álgebra entre múltiplos); entram numa fatia futura, com a
álgebra exibida.

## Metodologia

Não está aqui e não é resumida aqui. A fonte canônica é o pacote congelado,
indexado por `skills/er-multiplos-justos/SKILL.md`. Desenho:
`docs/desenho-arquitetura-v4.md`.

## Espelho JS (laboratório do relatório)

`assets/motor_espelho.js` é a única matemática de valuation em JavaScript
admitida neste projeto: espelha o núcleo do motor congelado
(`vendor/multiplos-justos/scripts/justos.py`) para que o relatório interativo
recalcule ao vivo quando o usuário edita premissas, sem depender de
subprocesso a cada edição. Sua licença para existir é o harness
`tests/test_paridade_js.py` — divergência numérica contra o motor reprova a
suíte nomeando o vetor culpado, e sem `node` no PATH o teste pula declarando
esse motivo explicitamente (o CI roda sempre, via `setup-node`).

Além do núcleo, o espelho também cobre o solver de reversa e as grades 1D/2D
de sensibilidade (alvo de mercado, `grade1D`, `grade2D`); a paridade
correspondente vive em dois harnesses separados —
`tests/test_paridade_solver_js.py` (contra o motor congelado) e
`tests/test_paridade_wrapper_js.py` (contra `reversa.py`/`sensibilidades.py`)
— porque são garantias contra fontes Python diferentes (motor × wrapper). A
conservação de capital (`conservacaoCapital`) é garantia contra o wrapper: o
harness roda `avaliar.precificar_firm` com as flags do motor.
