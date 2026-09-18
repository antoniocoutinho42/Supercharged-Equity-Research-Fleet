---
name: multiplos-justos
description: >-
  Kernel metodológico de valuation do Equity Research Fleet, versão 10.1.
  USE quando o `er-analise` ou o `operador-mj` precisar traduzir a economia de
  uma companhia em valuation, engenharia reversa, sensibilidades ou
  diagnósticos. Também pode ser invocado explicitamente pelo usuário. É o
  framework guarda-chuva do valuation do Fleet: não existe fallback silencioso
  para múltiplos comparáveis ou DCF genérico.
---

# Múltiplos Justos v10.1: kernel metodológico

Esta skill é a **fonte de verdade do valuation** do Fleet. Ela foi reorganizada a partir da v10.1 para progressive disclosure: o kernel contém apenas identidades, autoridade, gates e roteamento; os detalhes vivem nas referências econômicas carregadas conforme o caso.

## Identidades centrais

- `g = RiR × ROIC` no lado firma e o análogo com ROE no lado equity.
- `FCFF = NOPAT × (1 − g/ROIC)` sob as premissas da metodologia.
- Ponte EBITDA: `EV/EBITDA = EV/NOPAT × (1−d)(1−t)`.
- Crescimento cria valor apenas quando expõe capital novo a retorno acima do custo de capital; crescimento com spread negativo destrói valor.
- Nível e taxa são problemas diferentes. Mudança de nível não vira `g` por conveniência.
- Capital econômico precede múltiplo. Base de lucro e reinvestimento têm de pertencer ao mesmo regime econômico/contábil.

As identidades e neutralidades qualificadas completas ficam em `references/core/identities-and-neutralities.md`; gates e condições de validade ficam em `references/core/gates.md` e `references/theory/derivacao.md`. Nunca cite uma neutralidade sem seu qualificador.

## Autoridades

1. **Economia e julgamento:** Analista-chefe.
2. **Tradução da economia para a metodologia:** `operador-mj`.
3. **Cálculo coberto pelo motor:** `scripts/justos.py`, nunca conta manual concorrente.
4. **Auditoria metodológica:** `auditor-mj`, em contexto independente.
5. **Doutrina:** esta skill e suas references. Em conflito com resumo, memória ou relatório anterior, vence a doutrina atual.

## Gates mínimos antes da conta

Leia `references/core/identities-and-neutralities.md` e `references/core/gates.md` antes de fechar qualquer valuation real. Em essência:

- **Gate 0:** capital econômico, qualidade dos inputs, base coerente, natureza de D&A/manutenção, ciclo de caixa, fronteiras contábeis e coerência do vetor.
- **Gate 0.5:** fase da companhia e regime correto da base.
- **Gate 1:** convenção terminal escolhida pela duração econômica do claim, sem default silencioso.
- **Gate 2:** nível já mudou? Drivers exógenos tornam a base reportada defasada?
- **Gate 3:** existe degrau ou capacidade pré-construída que não pode ser confundida com crescimento recorrente?

Base monetária também é uma invariante: nominal ou real, mas nunca mistura das duas.

## Escolha da rota

Leia `references/core/routes.md`. O framework possui rotas internas para firma, equity, multi-segmento, vida finita/reserve NAV, asset NAV/stock-mark, holding/SOTP, option/scale, normalização de nível e releveraging.

**Não pergunte se deve abandonar Múltiplos Justos.** Escolha a representação econômica correta dentro dele.

## Progressive disclosure

Depois dos gates e da rota, carregue apenas o necessário:

- **Derivação de premissas:** `references/valuation/premise-derivation.md`
- **Terminal:** `references/valuation/terminal.md`
- **Drivers e normalização de nível:** `references/valuation/drivers-level.md`
- **Degrau/capacidade:** `references/valuation/capacity.md`
- **Reverse valuation e cenários:** `references/diagnostics/scenarios-reverse.md`
- **Diagnósticos obrigatórios:** `references/diagnostics/mandatory.md`
- **Financeiras:** `references/special-cases/financials.md`
- **Multi-segmento:** `references/special-cases/multi-segment.md`
- **Marca de estoque/NAV:** `references/special-cases/stock-mark-and-scope.md`
- **Releveraging:** `references/special-cases/releveraging.md`
- **Registro do caso:** `references/operations/case-record.md`
- **Cadeias de cálculo:** `references/operations/calculation-chains.md`
- **Teoria/provas:** `references/theory/derivacao.md` e `references/theory/paper-multiplos-justos-v3.md`

O índice `references/aplicacao.md` mantém compatibilidade com todas as referências históricas a §1–§13 da v10.1 sem recolocar o playbook inteiro no contexto.

## Operação

Antes da primeira conta de uma análise:

```bash
python skills/multiplos-justos/scripts/justos.py selftest
```

O `operador-mj` deve:

1. receber `economic-map.md` e evidências materiais;
2. escolher rota e gates;
3. derivar as premissas materiais, separando observado / derivado / inferido / assumido;
4. pedir `RESEARCH REQUIRED` quando faltar evidência decisiva;
5. executar `justos.py` para toda conta coberta;
6. produzir `valuation-case.md` e, quando úteis, `inputs.json` e `outputs.json`;
7. executar reversa, sensibilidades, iso-valor e MM quando material;
8. ler integralmente os warnings das rodadas que sustentam o caso-base;
9. entregar o caso ao `auditor-mj` antes de o Analista incorporar o valuation ao relatório.

## Critérios fundamentais de validade

Um valuation não está pronto se:

- existe quadrante contábil/econômico proibido;
- um input material foi preenchido sem evidência ou rótulo de hipótese;
- a rota não representa a economia do ativo;
- base monetária, período, moeda ou definição não reconciliam;
- warnings relevantes do motor foram ignorados;
- o laboratório não reconcilia com o caso-base;
- comparáveis ou um modelo paralelo passaram a determinar o valor justo;
- auditoria metodológica material permanece sem resolução ou justificativa.

## Manutenção

Antes de alterar a metodologia, leia `references/development/manutencao.md`. O histórico vive em `CHANGELOG.md`. Não copie a doutrina inteira para agentes: eles apontam para esta skill e carregam referências sob demanda.
