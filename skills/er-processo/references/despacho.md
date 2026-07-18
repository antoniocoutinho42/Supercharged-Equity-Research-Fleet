# Template de despacho por gate

Cada despacho a um subagente descartável (agents/*.md) é um brief curto que o
Coordenador preenche, com contexto fresco (o subagente não herda a thread) e
sem colar conteúdo de arquivo. Um despacho por gate.

## Template do brief

```
gate: <G1|G1_5|G2|G3_0|G3|G4|G5|G6|G7|G8>
agente: <analista|modelador|auditor|portfolio-manager|redator>
ns: <caminho do namespace, ex.: /tmp/analise/<TICKER>/>
foco: |
  <2 a 4 linhas: o que decide neste gate, prioridades, o que NÃO repetir>
insumos: [<paths dos arquivos que o agente deve ler>]
entregaveis esperados: [<paths dos arquivos canônicos que o agente deve escrever>]
restricoes:
  - profundidade: <SUMARIA|PADRAO|REFORCADA, quando já carimbada>
  - orcamento_paginas: <ex.: dossiê até 6 páginas>
  - escopo_auditoria: <somente para G4/G5: o que a ordem explícita do usuário cobre>
```

## Regras

- Nunca cole conteúdo de arquivo no brief nem na resposta: aponte paths, o
  agente lê ele mesmo.
- O brief vai como arquivo `<ns>/handoffs/<gate>-brief.yaml` (mesmo schema
  `handoff` de `schemas/handoff.schema.json`, campo `status: ABERTO`), OU
  inline no despacho quando a plataforma não permitir escrever arquivo antes
  do dispatch (declare qual modo foi usado).
- Um despacho por gate: não acumule dois gates num único brief, mesmo que o
  mesmo agente execute os dois em sequência (ex.: Analista em G1_5 e G2).
- Contexto fresco: o subagente é despachado sem herdar a thread do
  Coordenador; todo o necessário está no brief e nos arquivos apontados.
- Ao receber a resposta do agente: valide o handoff de retorno com
  `python scripts/validar.py <ns>/handoffs/<gate>.yaml --schema handoff` e
  registre o gate via `python scripts/pipeline.py <ns> gate <G> --veredicto
  <V> --racional "..."` (nunca grave estado.yaml à mão).

## Tabela gate → agente → skill

| Gate      | Agente             | Skill obrigatória          |
|-----------|---------------------|-----------------------------|
| G1        | analista            | er-guardrails                |
| G1.5      | analista            | er-guardrails                |
| G2        | analista            | er-dossie                    |
| G3.0      | modelador           | er-valuation                 |
| G3        | modelador           | er-valuation                 |
| G4        | auditor             | er-auditoria                 |
| G5        | auditor             | er-auditoria                 |
| G6        | portfolio-manager   | er-portfolio                 |
| G8        | redator (PADRAO/REFORCADA); o próprio Coordenador em SUMARIA | er-relatorio |

G7 (decisão) não tem agente despachado: o Coordenador aplica
`references/regras-decisao.md` e escreve o bloco `decisao` diretamente.
