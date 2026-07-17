---
name: er-valuation
description: Motor determinístico de valuation do processo de Antonio (etapa G3 do fleet de research). USE SEMPRE que a tarefa envolver valuation de uma ação, P/L Justo, Preço Máximo para o Hurdle, Valor Intrínseco Econômico, entry ladder, expectativas implícitas no preço (g/CAP/Ke implícitos), validação por múltiplos de comparáveis ou por histórico próprio, julgamento de CAP (cap_check), ou o gate de proporcionalidade G3.0 — mesmo que o pedido diga apenas "calcule o valor justo", "roda o valuation de X" ou "o preço atual faz sentido?". REGRA CENTRAL: nunca calcular valuation à mão em prosa; preencher inputs.yaml, rodar cap_check.py e engine.py e interpretar resultados.json citando por chave. Também usar quando o Auditor pedir re-execução, testes de limite ou verificação do motor.
---

# valuation-engine v2 — cálculo em código, prosa só interpreta

Este skill codifica a etapa G3 do processo de research de Antonio. O princípio:
**toda aritmética vive em `engine.py` (versionado e coberto por golden tests);
o Modelador decide premissas e interpreta; ninguém narra contas em prosa.**

Responder em PT-BR, tom profissional e direto.

---

## 1. Métodos do fluxo padrão (e SOMENTE eles)

| Papel | Método | Chave em `resultados.json` |
|---|---|---|
| Motor principal (único gerador de preço) | P/L Justo (franchise-fade, Bracket DE/NDE) nas duas âncoras: Preço Máximo p/ Hurdle e Valor Intrínseco Econômico (grade de Ke CAPM), 3 cenários + ponderado, cross-check GAAP | `hurdle`, `economico` |
| Validação 1 | Múltiplos de comparáveis: P/L justo e múltiplo atual vs. mediana dos pares (mesma base contábil) | `validacao_multiplos.comparaveis` |
| Validação 2 | Múltiplo atual vs. banda histórica da própria companhia (P/L ou EV/EBITDA, métrica primária declarada) | `validacao_multiplos.historico_proprio` |
| Expectativas implícitas | g implícito (hurdle), CAP implícito (econ.), Ke que reconcilia o preço com o teto do CAP | `reverse` |
| Entry ladder | Ke e CAP implícitos por degrau + delta até o valor central | `ladder` |
| Elasticidades | Valor por +1 ano de CAP, +1pp g, +1pp ROE, −0,5pp Ke (duas âncoras) | `elasticidades` |
| Sinais e gate | Entrada (ACIONAVEL/LIMITROFE/NAO_ACIONAVEL), econômico (SUB/DENTRO/SOBRE), profundidade G3.0 | `sinais`, `gate` |
| Rastreabilidade | Eco do julgamento de CAP (cenários, teto, confiança, justificativas) e das checagens de coerência | `cap`, `validacao` |

**Removidos na v2 (não recriar à mão):** DCF-fade, grade de sensibilidade Ke×g×CAP,
múltiplos-alvo com preços por cenário. Múltiplos NÃO são preços-alvo nem entram em
média com o P/L Justo: são teste de razoabilidade. Divergência material (> limiar,
default 30%) vira flag em `validacao_multiplos.flags` e obriga revisão das premissas
ou explicação premissa a premissa — nunca combinação mecânica.

## 2. Julgamento de CAP (cap_check.py — parecer, não gate)

CAP é a duração econômica provável dos retornos excedentes da COMPANHIA CONSOLIDADA,
não o número de anos de histórico disponível de um produto. `python cap_check.py
inputs_<TICKER>.yaml` lê `fatos.duracao` (Analista: persistência consolidada e/ou por
segmentos com pesos de lucro, fontes estruturais, renovação do moat, vetores de erosão
com materialidade/probabilidade/horizonte, precedentes) e devolve um PARECER: bandas de
REFERÊNCIA (8-12 default | 12-18 moat claro | 18-25 excepcional | 25-35 geracional),
persistência ponderada e ALERTAS. O Modelador responde cada alerta na tabela de
premissas e PODE sobrescrever com justificativa registrada; o engine exige
`justificativa_cap`, `justificativa_cenarios` e `cap_confianca` (ALTA | MEDIA | BAIXA —
BAIXA amplia o spread bear-bull, nunca encurta o CAP mecanicamente). CAP base >= 25:
recomendar auditoria ao Coordenador. `--selftest` valida a régua.

## 3. Fluxo de uso (Modelador)

1. Conferir `meta` e `fatos` do Analista no `inputs_<TICKER>.yaml` (schema canônico:
   `inputs_exemplo_vrsk.yaml`); preencher `premissas` (decisão sua, defendida no valuation.md).
2. Rodar `python cap_check.py inputs_<TICKER>.yaml` ANTES de fixar o CAP; responder os alertas.
3. Rodar `python engine.py inputs_<TICKER>.yaml --out saida_<TICKER> --chart` (`--xlsx` opcional).
   O engine RECUSA inputs incoerentes (LPA <= 0 → modo custom com autorização do
   Coordenador; probabilidades erradas; g >= ROE; CAPs fora de ordem; justificativas ausentes).
4. Rodar `python scripts/snapshot.py <ns>` (caminho relativo à raiz do plugin): congela
   `inputs.yaml` + `resultados.json` em `runs/<hash8>/` imutável; o hash impresso é o
   identificador canônico da rodada, reportado ao Coordenador junto com o gate.
5. Reportar o `gate.modo_recomendado` (e o hash do passo 4) ao Coordenador ANTES de
   escrever prosa (é o G3.0).
6. Escrever `valuation.md` interpretando `resultados.json`. Citar números pela chave
   (ex.: `hurdle.cenarios.ponderado`). Limite: 1 página (SUMÁRIA), 2 (PADRÃO/REFORÇADA).

**Proibições:** narrar aritmética em prosa; construir método manual paralelo (DCF de
qualquer tipo, SOTP, grades) fora do modo custom autorizado; digitar número que não
exista no JSON; tratar múltiplos como preço-alvo; alterar fórmula sem subir a versão (Seção 5).

## 4. Fluxo de uso (Auditor)

1. Re-executar o engine a partir de `<ns>/runs/<hash>/inputs.yaml` (o hash canônico vem
   de `estado.yaml` campo `engine.hash`), comparando com `runs/<hash>/resultados.json`.
   REGRA DURA: o Auditor NUNCA lê nem usa o `<ns>/inputs.yaml` mutável; se `runs/<hash>/`
   não existir, a auditoria DEVOLVE ao Coordenador com "snapshot ausente; Modelador deve
   rodar snapshot.py" — nunca prossegue sobre o arquivo mutável.
2. Recomputar à mão 5-8 números sinal-críticos com a implementação de referência
   (apêndice do mandato do Auditor: DDM explícito com Bracket DE/NDE) — independência real.
3. Re-rodar `cap_check.py` e auditar o JULGAMENTO de CAP: justificativas respondem aos
   alertas? Dupla penalização do mesmo risco em lucro/g/ROE/Ke/CAP/probabilidades?
4. Revisar o código SOMENTE quando `engine.versao` mudar: ler o diff e rodar
   `python tests/test_golden_vrsk.py` (precisa terminar 100% verde).
5. Discordância numérica se expressa como TESTE QUE FALHA em `tests/`, nunca como modelo paralelo.

## 5. Versionamento (regras duras)

- SemVer em `ENGINE_VERSION`. Mudou fórmula/desenho → minor ou major + entrada no CHANGELOG do topo.
- Nenhuma versão é promovida com golden test vermelho. O caso VRSK é o teste de regressão
  permanente; as propriedades matemáticas do P/L Justo (ROE=Ke → 1/Ke; limite de Gordon;
  monotonicidade em Ke; neutralidade DE=NDE) são invariantes.
- Cada análise registra `engine.versao` e `engine.hash_inputs` no manifesto do Coordenador.
- Novo método = novo bloco + novo golden test + assinatura do Auditor (quando acionado).

## 6. Limitações declaradas (não esconder do usuário)

- Motor pensado para operações não financeiras com lucro contábil significativo e
  representativo. Sem lucro representativo (pré-lucro, projeto em desenvolvimento),
  financeiras com float e cíclicas profundas: o engine recusa ou o método é inadequado —
  usar `modo custom` SOMENTE com autorização explícita do Coordenador, com métricas
  adequadas à natureza econômica do ativo, cálculo em Python citável, limitações e
  probabilidades declaradas, sem falsa precisão.
- O xlsx gerado (`--xlsx`) é dump de valores para conferência, não template vivo.
- A validação por múltiplos depende da qualidade dos dados do Analista
  (`fatos.multiplos_historicos`, `fatos.pares`, mesma base contábil); sem eles o bloco
  reporta SEM_DADOS e o Modelador decide se pede calibração.

## 7. Arquivos deste skill

- `engine.py` — motor (stdlib; opcionais: pyyaml, matplotlib, openpyxl)
- `cap_check.py` — parecer de julgamento do CAP (com --selftest); NÃO é gate
- `inputs_exemplo_vrsk.yaml` — schema canônico comentado (contrato Analista/Modelador)
- `tests/test_golden_vrsk.py` — suíte golden (rodar antes de qualquer promoção)
- `scripts/snapshot.py` (fora desta pasta, na raiz do plugin) — congela o run em `runs/<hash8>/`
