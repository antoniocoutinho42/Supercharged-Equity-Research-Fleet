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

Schema completo, executável: `tests/fixtures/caso_minimo_firm.json` e
`tests/fixtures/caso_minimo_equity.json`.

## Escopo desta fatia

Métricas suportadas: rota `firm` aceita `EBITDA` e `NOPAT`; rota `equity`
aceita `LL`. São as que o motor emite diretamente — demais métricas são
transformação de apresentação e entram depois, com a álgebra exibida.

Ainda não implementados aqui: soma das partes por segmento e por safra de
capital; composição multifásica. Cada um entra em sua própria fatia.

## Metodologia

Não está aqui e não é resumida aqui. A fonte canônica é o pacote congelado,
indexado por `skills/er-multiplos-justos/SKILL.md`. Desenho:
`docs/desenho-arquitetura-v4.md`.
