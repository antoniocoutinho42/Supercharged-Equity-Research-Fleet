---
name: er-relatorio
description: >-
  USE QUANDO montar, validar ou entender o `entrega.json` da fatia v4 do
  relatório: o contrato de entrada do builder `er-relatorio`, os
  placeholders auditáveis (`{{resultados:...}}`/`{{caso:...}}`/
  `{{livre:...}}`), o QC de três níveis (HARD FAIL, REQUIRED DISCLOSURE,
  QUALITY WARNING) ou o CLI `builder.py` que emite `relatorio.html` +
  `qc.json` a partir de uma raiz de execução — ou recusa, nomeando a razão.
  Em construção (item 5 do v4, fatia 5A: só contrato + QC + casca mínima de
  HTML; as três abas completas são a Task 4). NÃO use para o relatório de 2
  abas em produção (esse é `er-relatorio-html`, v3); não use para rodar o
  valuation (`er-valuation`) nem para o workflow da análise (`er-analise`).
---

# er-relatorio — builder determinístico do relatório v4 (três abas)

Esta skill é a camada de apresentação do v4: consome contratos publicados
pela integração (`er-valuation`) e monta o relatório — nunca decide,
calcula ou nomeia nada que seja metodologia. Emenda **E3** do desenho
(`docs/desenho-arquitetura-v4.md` §15): o relatório não duplica nem
reimplementa valuation. Concretamente:

- **Nenhum módulo de `scripts/` importa `er-valuation` nem o vendor.**
  Trava mecânica em `tests/test_relatorio_fronteira.py`: nenhum import
  proibido (`caso`, `avaliar`, `motor`, `reversa`, `sensibilidades`, `sotp`,
  `ponte`, `diagnosticos`, `justos`, `vetores_paridade`, `vetores_solver`),
  e nenhum literal de código fora da constante `ASSETS_DA_INTEGRACAO`
  (`builder.py`) nomeia a integração — só docstring/comentário pode.
- **`caso`/`resultados` chegam como dados, nunca por execução.** A
  correspondência entre os dois é provada por hash
  (`resultados.origem.caso_sha256` contra o JSON canônico do `caso`,
  recalculado por `entrega.sha256_canonico` — a mesma receita de
  `avaliar.py`, duplicada em três linhas de propósito) — nunca rodando o
  motor de novo.
- **Toda prosa é auditável.** Todo número de valuation citado em
  `analise` vem de um placeholder `{{resultados:...}}`/`{{caso:...}}`;
  número livre legítimo é `{{livre:...}}`; qualquer outro dígito na prosa é
  HARD FAIL (`numero_sem_proveniencia`).
- **HARD FAIL nunca emite.** Regra inviolável 2: se o QC acha nível
  `HARD_FAIL`, `relatorio.html` não é escrito — só `qc.json`.

## Como rodar

```bash
python skills/er-relatorio/scripts/builder.py <raiz-de-execucao>
```

`<raiz>` contém um único `entrega.json` (contrato `entrega/1`, ver abaixo).
Códigos de saída:

| Código | Significado | O que é escrito |
|---|---|---|
| `0` | QC sem `HARD_FAIL` | `relatorio.html` + `qc.json` |
| `2` | QC achou `HARD_FAIL` | só `qc.json` |
| `1` | uso incorreto, ou `entrega.json` ausente/malformado/fora da raiz/versão incompatível/idioma sem dicionário | nada |

A razão de uma recusa código `1` sai em stderr, nomeando o campo (e, para
chave desconhecida, uma sugestão por `difflib`). Regra inviolável 6: o
builder aceita uma única raiz de execução — lê só `entrega.json` dela e
escreve só dentro dela; um `entrega.json` cujo caminho resolvido (symlink
seguido) sai da raiz é recusado, nunca lido através do link.

## O contrato `entrega/1`

```json
{
  "versao_contrato": "entrega/1",
  "execucao": {"id": "2026-09-11-001", "ticker": "SINT3", "idioma": "pt-BR"},
  "caso": {},
  "resultados": {},
  "analise": {"conclusao": {"texto": "Valor justo de {{resultados:manchete.preco_acao|moeda}} por ação."}},
  "ledger": [],
  "ficha_tecnica": {}
}
```

Vocabulário fechado em todo nível que este contrato define (topo,
`execucao`, `analise`, `analise.conclusao`) — chave desconhecida é
recusada pelo nome, com sugestão. `caso` e `resultados` são opacos: este
módulo só confirma que são objetos e que `resultados.versao_contrato` é
`"resultados/1"` — o conteúdo pertence ao contrato de `er-valuation`, nunca
revalidado aqui. `execucao.idioma` precisa ter dicionário em
`assets/i18n/<idioma>.json`. `ledger`/`ficha_tecnica` só têm o tipo
confirmado nesta fatia (lista / objeto); a fatia 5D detalha o conteúdo dos
dois. Produzir a entrega em produção é `er-analise` (item 8); nesta fatia,
`tests/relatorio_apoio.py` monta raízes de teste rodando `avaliar()` de
verdade sobre uma fixture de caso.

## Placeholders auditáveis (A7)

`{{resultados:<caminho>|<formato>}}`, `{{caso:<caminho>|<formato>}}`,
`{{livre:<texto>}}`. `<caminho>` é pontuado, com índice de lista como
segmento numérico (`cenarios.base.valor.preco_acao`). Formatos: `num0`–
`num4` (casas decimais, verbatim); `pct0`–`pct2` (`valor x 100`, `valor` é
FRAÇÃO); `pp0`–`pp2` (verbatim, `valor` já em PONTOS PERCENTUAIS — nunca
multiplicado de novo); `x1`/`x2` (múltiplo, sufixo `x`); `moeda` (2 casas,
símbolo do dicionário para o código antes do hífen de `caso.moeda` —
`"BRL-nominal"` → `"BRL"` → `"R$"`). pt-BR: milhar `.`, decimal `,` — sem o
módulo `locale` (§16.1), determinístico por construção.

Um placeholder que não resolve (caminho inexistente, valor não numérico,
formato desconhecido) fica LITERAL no texto e vira `placeholder_nao_
resolvido` (QC); nunca uma exceção que derruba o processo, nunca um valor
inventado.

## QC de três níveis (A8)

`HARD_FAIL` (não emite), `REQUIRED_DISCLOSURE` (visível no HTML — Task 4),
`QUALITY_WARNING` (só em `qc.json`). Regras desta fatia:

| Código | Nível | Gatilho |
|---|---|---|
| `resultados_nao_correspondem_ao_caso` | HARD FAIL | hash do `caso` ≠ `resultados.origem.caso_sha256` |
| `placeholder_nao_resolvido` | HARD FAIL | caminho inexistente ou valor não numérico |
| `numero_sem_proveniencia` | HARD FAIL | dígito na prosa de `analise` fora de placeholder |
| `diagnostico_sem_chave` | HARD FAIL | `null` em `diagnosticos_chaves`/`diagnosticos_unicos_chaves` |
| `divergencia_de_base_degrau` | REQUIRED DISCLOSURE | `\|divergencia_de_base_%\|` acima do limiar do catálogo |

Mensagem de cada achado vem de `assets/i18n/<idioma>.json` (`qc.<codigo>`,
`params` substituídos) — nunca hardcoded (§16.1). `qc.json` sai sempre, em
ordem determinística, mesmo quando o builder recusa emitir o HTML.

## Módulos

| Arquivo | Responsabilidade |
|---|---|
| `scripts/entrega.py` | Contrato de `entrega.json`: carrega, valida, recusa; `sha256_canonico` |
| `scripts/placeholders.py` | Resolve `{{...}}`; formata número por idioma (sem `locale`) |
| `scripts/qc.py` | Achados estruturados dos três níveis (regras desta fatia) |
| `scripts/builder.py` | CLI: orquestra, resolve mensagem do dicionário, decide o exit code |

`scripts/render.py` (as três abas) e `assets/template.html` nascem na
Task 4 — nesta fatia, `builder.py` escreve uma casca de HTML mínima
(sem nenhuma string de interface: só título e conclusão resolvida,
escapados), suficiente para os testes de contrato desta task.

## Metodologia

Não está aqui e não é resumida aqui. Todo conhecimento metodológico que
este relatório precisa exibir (bloco/unidade/rótulo de premissa, rótulo e
base de múltiplo, severidade e rótulo de diagnóstico, limiar de disclosure)
vem de `skills/er-valuation/assets/catalogo_apresentacao.json` — lido via
`ASSETS_DA_INTEGRACAO`, nunca hardcoded aqui. A fonte canônica da
metodologia é `skills/er-multiplos-justos/SKILL.md`; da orquestração,
`skills/er-valuation/SKILL.md`. Desenho: `docs/desenho-arquitetura-v4.md`.
