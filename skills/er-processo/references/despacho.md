# Template de despacho por gate

Cada despacho a um subagente descartável (agents/*.md) é um brief curto que o
Coordenador preenche, com contexto fresco (o subagente não herda a thread) e
sem colar conteúdo de arquivo. Um despacho por gate.

## Template do brief (handoff válido)

O brief usa EXATAMENTE o schema `handoff` (`schemas/handoff.schema.json`,
`additionalProperties: false`): chaves `gate`, `de`, `para`, `insumos`,
`entregaveis`, `foco`, `restricoes` (opcional), `status`. O agente-alvo vai
em `para`; o namespace fica implícito no path do arquivo do brief e nos paths
de `insumos`/`entregaveis`. Exemplo preenchido (G2, Analista):

```yaml
gate: G2
de: Coordenador
para: analista
foco: >-
  Dossiê completo de FNV com prioridade nas questões decisivas do intake
  (alocação de capital, duração do moat de royalties); não repetir a
  evidência já coletada nos guardrails do G1.
insumos:
  - /tmp/analise/FNV/estado.yaml
  - /tmp/analise/FNV/handoffs/G1.yaml
entregaveis:
  - /tmp/analise/FNV/dossie.md
  - /tmp/analise/FNV/inputs_valuation.md
  - /tmp/analise/FNV/inputs.yaml
restricoes:
  - "profundidade: PADRAO"
  - "orcamento_paginas: dossie ate 6 paginas"
status: ABERTO
```

Em `restricoes` entram profundidade, orçamento de páginas e, no G4/G5, o
escopo de auditoria coberto pela ordem explícita do usuário.

## Regras

- Nunca cole conteúdo de arquivo no brief nem na resposta: aponte paths, o
  agente lê ele mesmo.
- O brief vai como arquivo `<ns>/handoffs/<gate>-brief.yaml` (schema
  `handoff`, `status: ABERTO`), OU inline no despacho quando a plataforma
  não permitir escrever arquivo antes do dispatch (declare qual modo foi
  usado).
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
| G1_5      | analista            | er-guardrails                |
| G2        | analista            | er-dossie                    |
| G3_0      | modelador           | er-valuation                 |
| G3        | modelador           | er-valuation                 |
| G4        | auditor             | er-auditoria                 |
| G5        | auditor             | er-auditoria                 |
| G6        | portfolio-manager   | er-portfolio                 |
| G8        | redator (PADRAO/REFORCADA); o próprio Coordenador em SUMARIA | er-relatorio |

G7 (decisão) não tem agente despachado: o Coordenador aplica
`references/regras-decisao.md` e escreve o bloco `decisao` diretamente.
