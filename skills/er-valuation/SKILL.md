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
  indefinido por spread não positivo).
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
necessária) e `razao` (por que o caso está fora) são textos não vazios; o
bloco não aceita outra chave, e nulo é ausência. Sob fronteira declarada a
análise continua, sem preço-alvo de manchete — regra do relatório, que lê
`resultados.fronteira_de_escopo`.

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
  ausente quando a manchete vem do SOTP.
- `mercado_tela` — o múltiplo de mercado (tela), sempre publicado — antes só
  existia dentro do bloco opcional `reversa`. Pareado com o múltiplo da
  manchete pela mesma `base`.
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
- `fronteira_de_escopo` — o bloco que o gate validou, ou `null`; sempre
  publicado (ver "Contrato do caso").
- `limitacoes` — lista de chaves, sempre publicada e possivelmente vazia, das
  limitações que o caso impõe à entrega. Hoje só a da reversa, que a Análise
  exige mas o gate recusa em combinações não implementadas:
  `reversa_na_rota_rampa` (rota `rampa`) e `reversa_com_degrau` (bloco
  `degrau`). Quem decide é `caso.reversa_indisponivel(caso)`, que consulta o
  mesmo registro de recusas que o gate aplica (`caso.LIMITACOES_DE_REVERSA`),
  nunca uma lista paralela; a trava de `tests/test_valuation_contrato.py`
  confere, fixture a fixture, que a chave sai publicada se e só se o gate
  recusa um bloco `reversa` válido. O relatório lê a chave, o rótulo e a
  declaração `afeta` do catálogo; a regra fica aqui.

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
registro que `caso.reversa_indisponivel` consulta)
é publicado à parte,
como o catálogo de apresentação (A6):
`skills/er-valuation/assets/catalogo_apresentacao.json`, schema em
`tests/test_catalogo_apresentacao.py`.

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
— porque são garantias contra fontes Python diferentes (motor × wrapper).
