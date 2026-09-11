---
name: er-relatorio
description: >-
  USE QUANDO montar, validar ou entender o `entrega.json` da fatia v4 do
  relatório: o contrato de entrada do builder `er-relatorio`, os
  placeholders auditáveis (`{{resultados:...}}`/`{{caso:...}}`/
  `{{livre:...}}`), o QC de três níveis (HARD FAIL, REQUIRED DISCLOSURE,
  QUALITY WARNING), as três abas (Tese/Valuation/Evidência, `render.py`) ou
  o CLI `builder.py` que emite `relatorio.html` + `qc.json` a partir de uma
  raiz de execução — ou recusa, nomeando a razão. Item 5 do v4, fatia 5A
  (contrato + QC + render das três abas) mais a onda de correção da revisão
  final. NÃO use para o relatório de 2 abas em produção (esse é
  `er-relatorio-html`, v3); não use para rodar o valuation (`er-valuation`)
  nem para o workflow da análise (`er-analise`).
---

# er-relatorio — builder determinístico do relatório v4 (três abas)

Esta skill é a camada de apresentação do v4: consome contratos publicados
pela integração (`er-valuation`) e monta o relatório — nunca decide,
calcula ou nomeia nada que seja metodologia. Emenda **E3** do desenho
(`docs/desenho-arquitetura-v4.md` §15): o relatório não duplica nem
reimplementa valuation. Concretamente:

- **Nenhum módulo de `scripts/` (nem de um subpacote futuro) importa
  `er-valuation` nem o vendor, direto ou indireto.** Trava mecânica em
  `tests/test_relatorio_fronteira.py`, varredura recursiva: nenhum import
  proibido (nomes DERIVADOS dos arquivos reais de
  `skills/er-valuation/scripts/*.py` e `vendor/multiplos-justos/scripts/*.py`
  — um módulo novo da integração fica proibido automaticamente, sem editar
  este teste); nenhum `importlib`/`__import__`/`exec`/`eval`; nenhum literal
  de código (nem montado por concatenação) fora da constante
  `ASSETS_DA_INTEGRACAO` (`builder.py`) nomeia a integração — só
  docstring/comentário pode; nenhum asset de `skills/er-relatorio/assets/`
  tem o sha256 de um asset da integração/vendor (pega cópia/espelho).
- **`caso`/`resultados` chegam como dados, nunca por execução.** A
  correspondência entre os dois é provada por hash
  (`resultados.origem.caso_sha256` contra o JSON canônico do `caso`,
  recalculado por `entrega.sha256_canonico` — a mesma receita de
  `avaliar.py`, duplicada em três linhas de propósito) — nunca rodando o
  motor de novo.
- **Toda prosa é auditável.** Todo número de valuation citado em
  `analise` vem de um placeholder `{{resultados:...}}`/`{{caso:...}}`;
  número livre legítimo é `{{livre:...}}`; qualquer outro dígito na prosa é
  HARD FAIL (`numero_sem_proveniencia`); qualquer `{{...}}` que não seja um
  placeholder reconhecido é HARD FAIL (`placeholder_malformado`) — nenhum
  bloco malformado ganha imunidade da busca de dígito.
- **Rótulo de metodologia vem sempre do catálogo, nunca de `caso` cru.** O
  cabeçalho da Valuation lê `resultados.rota` e
  `manchete.convencao_terminal` (já canonicalizados pela integração) e
  busca o rótulo em `catalogo_apresentacao.json` — nunca interpreta
  `caso...premissas.tv` nem nenhum alias.
- **HARD FAIL nunca emite.** Regra inviolável 2: se o QC acha nível
  `HARD_FAIL`, `relatorio.html` não é escrito — só `qc.json`. Todo build
  também remove `relatorio.html`/`qc.json` de uma rodada anterior na MESMA
  raiz antes de começar (desfazendo symlink, nunca seguindo) — uma recusa
  nunca deixa a saída de uma rodada anterior no lugar.

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
| `1` | uso incorreto, ou `entrega.json` ausente/malformado/fora da raiz/versão incompatível/idioma sem dicionário/`execucao.ticker` divergente de `caso.ticker` | nada |

A razão de uma recusa código `1` sai em stderr, nomeando o campo (e, para
chave desconhecida, uma sugestão por `difflib`). Regra inviolável 6: o
builder aceita uma única raiz de execução — lê só `entrega.json` dela e
escreve só dentro dela; um `entrega.json` cujo caminho resolvido (symlink
seguido) sai da raiz é recusado, nunca lido através do link; nenhuma
escrita de `relatorio.html`/`qc.json` passa através de um symlink.

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
revalidado aqui. Exceção pontual: quando `caso` declara um `ticker`, ele
tem de bater com `execucao.ticker` (identidade da empresa que o título da
página nomeia e a que o valuation avaliou). `execucao.idioma` precisa ter
dicionário em `assets/i18n/<idioma>.json`. `ledger`/`ficha_tecnica` só têm o
tipo confirmado nesta fatia (lista / objeto); a fatia 5D detalha o conteúdo
dos dois. Produzir a entrega em produção é `er-analise` (item 8); nesta
fatia, `tests/relatorio_apoio.py` monta raízes de teste rodando `avaliar()`
de verdade sobre uma fixture de caso.

## Placeholders auditáveis (A7)

`{{resultados:<caminho>|<formato>}}`, `{{caso:<caminho>|<formato>}}`,
`{{livre:<texto>}}` — reconhecidos mesmo quando quebrados por uma quebra de
linha. `<caminho>` é pontuado, com índice de lista como segmento numérico
(`cenarios.base.valor.preco_acao`). Formatos: `num0`–`num4` (casas
decimais, verbatim); `pct0`–`pct2` (`valor x 100`, `valor` é FRAÇÃO);
`pp0`–`pp2` (verbatim, `valor` já em PONTOS PERCENTUAIS — nunca
multiplicado de novo); `x1`/`x2` (múltiplo, sufixo `x`); `moeda` (2 casas,
símbolo do dicionário para o código antes do hífen de `caso.moeda` —
`"BRL-nominal"` → `"BRL"` → `"R$"`; código sem símbolo declarado usa o
próprio código ISO como prefixo, nunca levanta erro). pt-BR: milhar `.`,
decimal `,` — sem o módulo `locale` (§16.1), determinístico por construção.

Um placeholder que não resolve (caminho inexistente, valor não numérico,
formato desconhecido) fica LITERAL no texto e vira `placeholder_nao_
resolvido` (QC); um `{{...}}` que não é um placeholder reconhecido (fonte
fora do vocabulário, maiúscula, sem `|formato`) é `placeholder_malformado`;
o formato pedido tem de casar com a unidade do valor (`formato_incompativel_
com_unidade` — uma premissa em `pp` só aceita `pp*`/`num*`, `moeda` só
`moeda`/`num*`, `anos` só `num0`; um caminho de `resultados` terminado em
`_%` só aceita `pp*`, `upside` só `pct*`). Nunca uma exceção que derruba o
processo, nunca um valor inventado.

## QC de três níveis (A8)

`HARD_FAIL` (não emite), `REQUIRED_DISCLOSURE` (visível no HTML),
`QUALITY_WARNING` (só em `qc.json`). Regras:

| Código | Nível | Gatilho |
|---|---|---|
| `resultados_nao_correspondem_ao_caso` | HARD FAIL | hash do `caso` ≠ `resultados.origem.caso_sha256` |
| `placeholder_nao_resolvido` | HARD FAIL | caminho inexistente ou valor não numérico |
| `placeholder_malformado` | HARD FAIL | `{{...}}` que não é um placeholder reconhecido |
| `numero_sem_proveniencia` | HARD FAIL | dígito na prosa de `analise` fora de placeholder |
| `diagnostico_sem_chave` | HARD FAIL | `diagnosticos_chaves`/`diagnosticos_unicos_chaves` ausente, com comprimento diferente do `diagnosticos`/`diagnosticos_unicos` correspondente, ou com `null` num item — em QUALQUER par publicado em `resultados.json` (varredura recursiva) |
| `degrau_sem_divergencia_de_base` | HARD FAIL | cenário com `degrau` sem `divergencia_de_base_%` numérico |
| `formato_incompativel_com_unidade` | HARD FAIL | formato de placeholder não bate com a unidade do valor |
| `multiplos_com_bases_diferentes` | HARD FAIL | `manchete.multiplo.base` ≠ `mercado_tela.base` |
| `relatorio_nao_autocontido` | HARD FAIL | referência (`src`/`href`/`srcset`/`data`/`url()`/`@import`) que não é `#fragmento` nem URI `data:` |
| `divergencia_de_base_degrau` | REQUIRED DISCLOSURE | `\|divergencia_de_base_%\|` acima do limiar de `catalogo.disclosures.divergencia_de_base_degrau` |

Mensagem de cada achado vem de `assets/i18n/<idioma>.json` (`qc.<codigo>`,
`params` substituídos) — nunca hardcoded (§16.1); o "porquê" metodológico de
`divergencia_de_base_degrau` vem do catálogo
(`catalogo.disclosures.divergencia_de_base_degrau.texto`), não do
dicionário do relatório. `qc.json` sai sempre, em ordem determinística,
mesmo quando o builder recusa emitir o HTML.

## As três abas (`render.py`)

Tese (conclusão resolvida + disclosures obrigatórios), Valuation (preço
justo, upside, múltiplo justo pareado com o de tela pela mesma base, rota e
convenção terminal — do catálogo, nunca de `caso` cru — e preço por cenário
quando houver mais de um; SOTP mostra só preço/upside, sem rota/convenção
única) e Evidência (metodologia, ficha técnica, log de resolução de
placeholders). `assets/template.html` é a casca estática — CSS e JS
100% inline, nenhum `src`/`href`/`url()`/`@import` que não seja
`#fragmento` ou `data:`. Toda string de interface vem do dicionário
(`t()`), todo rótulo de rota/convenção terminal/múltiplo vem do catálogo —
chave ausente é `ChaveDeInterfaceAusente`/`RotuloDoCatalogoAusente`,
nomeada, nunca um código cru na tela.

## Módulos

| Arquivo | Responsabilidade |
|---|---|
| `scripts/entrega.py` | Contrato de `entrega.json`: carrega, valida, recusa; `sha256_canonico`; identidade de ticker |
| `scripts/placeholders.py` | Resolve `{{...}}`; formata número por idioma (sem `locale`) |
| `scripts/qc.py` | Achados estruturados dos três níveis |
| `scripts/render.py` | Compõe as três abas do HTML a partir de `entrega`/`catalogo`/achados |
| `scripts/builder.py` | CLI: orquestra, limpa saída anterior, resolve mensagem do dicionário, decide o exit code |

## Metodologia

Não está aqui e não é resumida aqui. Todo conhecimento metodológico que
este relatório precisa exibir (bloco/unidade/rótulo de premissa, rótulo e
base de múltiplo, rótulo de convenção terminal, severidade e rótulo de
diagnóstico, limiar e texto do disclosure de divergência de base) vem de
`skills/er-valuation/assets/catalogo_apresentacao.json` — lido via
`ASSETS_DA_INTEGRACAO`, nunca hardcoded aqui. A fonte canônica da
metodologia é `skills/er-multiplos-justos/SKILL.md`; da orquestração,
`skills/er-valuation/SKILL.md`. Desenho: `docs/desenho-arquitetura-v4.md`.
