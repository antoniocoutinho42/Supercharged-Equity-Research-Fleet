---
name: relatorio-html
description: >-
  Skill de comunicação e produto do Equity Research Fleet. USE somente depois
  de o Analista-chefe ter formado a tese e recebido valuation auditado. Ensina
  a transformar investment research em HTML autocontido, responsivo,
  visualmente claro e interativo, sem decidir a tese, a arquitetura econômica
  ou a ordem narrativa.
---

# Relatório HTML

Esta skill cuida da **forma**. O conteúdo e o investment judgment pertencem ao `er-analise`; a metodologia pertence a `multiplos-justos`.

Exceção de escopo: o `/anexo-financeiro` usa esta skill para o HTML do anexo sem exigir tese e valuation auditados. O anexo não é initiating coverage e não carrega laboratório.

## Princípios

- A forma serve ao achado central. Não existe número padrão de abas, capítulos, tabelas ou gráficos.
- O próprio Analista escreve o relatório; não delegue para writer agent.
- O arquivo final é um único HTML autocontido, offline e responsivo.
- Todo gráfico responde a uma pergunta econômica. Se uma tabela comunica melhor, use tabela.
- O laboratório é uma interface da tese: driver real → efeito operacional → premissa econômica → valuation → preço/retorno implícito.
- A prosa traduz a metodologia para linguagem de mercado sem esconder derivação ou risco metodológico.

Leia sob demanda:

- `references/report-craft.md` para escrita, visual e robustez do HTML;
- `references/laboratory.md` para o laboratório interativo;
- `references/mj-writing-and-delivery.md` para a doutrina de tradução da v10.1;
- `references/mj-required-content.md` para o conteúdo metodológico obrigatório que deve aparecer quando material, sem impor ordem narrativa.

Antes de entregar, valide que o HTML abre offline, o JavaScript não quebra, não há NaN, recursos externos proibidos ou inconsistência entre presets, prosa e valuation canônico. Rode também:

```bash
python scripts/validate-report.py analises/<TICKER>/<AAAA-MM-DD>/relatorio.html
```

Esse script só responde "está quebrado?". Qualidade intelectual continua com os agentes.
