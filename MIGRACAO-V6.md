# Migração v5 → v6.0.0

## Objetivo

A v6 transforma a `multiplos-justos v10.1` de skill monolítica em kernel metodológico + progressive disclosure, sem alterar o motor determinístico. O Analista continua dono da tese; valuation ganha operador e auditor especializados; comunicação HTML sai da metodologia.

## Integridade da fonte

Arquivos recebidos como autoridade de v10.1:

- `SKILL.md`: `5882190c03b3bad9343ba8a1f66c1e0d12d81c8118509995acb950d7ab2550ef`
- `references/aplicacao.md`: `e5b1b281f688afeaa65ee37c42553270e6e58b88a231bc90c7afce2e88a5da50`
- `references/derivacao.md`: `bdfcecc5b60db207b6c4ef30c9f0ff3c0c360dbf17b475e945015b2493f776c6`
- `scripts/justos.py`: `a6a2e692801f351f9d76ef1bf76e97e3130f30c2551e7c08cc99a6009c1912fe`
- `scripts/testes.py` original: `2fea048a6ee1d49718622d0c308ea9c02d23558731b275640ea08e9d80b1a534`

O `justos.py` foi preservado byte a byte. A lógica numérica de `testes.py` foi preservada, mas o arquivo recebeu uma adaptação documental mínima para localizar os mesmos anchors e lints na estrutura modular. `CHANGELOG.md`, paper e derivação foram preservados como fonte histórica/doutrinária; notas de roteamento do Fleet foram acrescentadas apenas onde necessário para impedir que linguagem histórica de “outra arquitetura” seja interpretada como saída do framework.

## Mapa de desmembramento da v10.1

| Conteúdo antigo | Responsabilidade atual | Destino | Tratamento |
|---|---|---|---|
| SKILL: identidades/autoridade | metodologia central | `skills/multiplos-justos/SKILL.md` | condensado em kernel |
| SKILL: Gates 0–3 | metodologia central | `references/core/gates.md` | preservado |
| SKILL: moeda/regime | metodologia central | `references/core/monetary-regime.md` | preservado |
| SKILL: releveraging | caso especial | `references/special-cases/releveraging.md` | preservado |
| SKILL: motor | cálculo determinístico | `references/core/motor.md` | preservado |
| SKILL: sem herança + fluxos | operação | `references/operations/operating-rules.md` | simplificado para o Fleet; texto original arquivado em `development/legacy-entry-and-flow-v10.1.md` |
| SKILL: entrega de research | comunicação | `skills/relatorio-html/references/mj-required-content.md` | conteúdo econômico destilado; texto original arquivado em `development/legacy-reporting-v10.1.md` |
| SKILL: diagnósticos | QA metodológico | `references/diagnostics/mandatory.md` | preservado |
| aplicação §1 | disciplina de evidência | `references/operations/research-evidence.md` | preservado; execução primária é do pesquisador/Analista |
| aplicação §2 | derivação de premissas | `references/valuation/premise-derivation.md` | preservado |
| aplicação §3 | terminal | `references/valuation/terminal.md` | preservado |
| aplicação §4 | reversa/cenários | `references/diagnostics/scenarios-reverse.md` | preservado |
| aplicação §5/5b | comunicação | `skills/relatorio-html/references/mj-writing-and-delivery.md` | simplificado para comunicação; texto original arquivado em `development/legacy-reporting-v10.1.md` |
| aplicação §6/§10/§11 | caso canônico/rastreabilidade | `operations/case-record.md` + `operations/calculation-chains.md` | cadeias econômicas preservadas; schema burocrático arquivado em `development/legacy-case-schema-v10.1.md` |
| aplicação §7 | nível/drivers | `references/valuation/drivers-level.md` | preservado |
| aplicação §8/§8f | degrau/capacidade | `references/valuation/capacity.md` | preservado |
| aplicação §9 | financeiras | `references/special-cases/financials.md` | preservado |
| aplicação §12 | multi-segmento | `references/special-cases/multi-segment.md` | preservado |
| aplicação §13 | fronteira/stock mark | `references/special-cases/stock-mark-and-scope.md` | regras preservadas; enquadramento reescrito para rotas internas do framework |
| aplicação Ap. J | jurisprudência | `references/theory/jurisprudence.md` | preservado |
| derivação + paper | teoria | `references/theory/` | preservado |
| manutenção | desenvolvimento | `references/development/manutencao.md` | preservado |

`references/aplicacao.md`, `derivacao.md`, `manutencao.md` e `paper-multiplos-justos-v3.md` permanecem como routers de compatibilidade para referências históricas, sem reintroduzir o monólito no contexto.

## Testes

A lógica numérica de `testes.py` foi preservada. Somente o resolvedor de documentos foi adaptado para ler bundles modulares em vez de presumir `SKILL.md` e `aplicacao.md` monolíticos; os mesmos anchors, lints semânticos e checks cross-layer continuam executando.

## Mudanças arquiteturais deliberadas

1. `er-analise` passa a ser inequivocamente o Analista-chefe e único dono da tese.
2. `economic-map.md` vira a interface leve research → valuation.
3. Múltiplos Justos passa a ser o framework guarda-chuva; rotas especiais são internas, não fallback externo.
4. Novo `operador-mj` traduz economia em metodologia e pode devolver `RESEARCH REQUIRED`.
5. Novo `auditor-mj` revisa metodologia independentemente do fact-check.
6. `relatorio-html` vira skill própria; a metodologia não dita sumário nem número de gráficos.
7. Fechamento separa três perguntas: fato correto, metodologia correta, research bom.
8. Workspace padrão foi reduzido ao mínimo auditável.
9. `scripts/validate-report.py` adiciona QC mecânico mínimo de HTML/JS/recursos externos sem transformar julgamento intelectual em hook.

## O que foi removido da v5

- regra que autorizava abandonar Múltiplos Justos em commodity, vida finita, NAV, holdings e pré-lucro;
- obrigação de um "segundo método" de valuation como conferência;
- `relatorio-html.md` e `valuation-e-laboratorio.md` misturados dentro de `er-analise`;
- comando redundante `/iniciar-cobertura`, substituído por `/analisar`.

Nada disso remove a sofisticação econômica correspondente: ela foi incorporada às rotas internas do framework ou à skill de comunicação.
