---
name: er-relatorio
description: >-
  Composição determinística e renderização do relatório final de equity research do processo de Antonio (etapa G8 do fleet). USE SEMPRE que a tarefa envolver montar, compor, revisar ou gerar o relatório final (relatorio.md / relatorio_final.pdf) de uma análise, validar o namespace da análise (checar.py), gerar log de consistência, ou converter um Markdown em PDF com o template institucional (capa, sumário, tabelas, rodapé, paginação) — mesmo que o pedido diga apenas "gera o PDF", "monta o relatório" ou "valida os arquivos da análise". REGRA CENTRAL: o relatório NÃO é escrito por agente; compor.py injeta dossie.md e valuation.md verbatim e gera tearsheet/tabelas de chaves do resultados.json; agentes apenas editam transições pontuais no relatorio.md composto. render_pdf.py é genérico e serve para qualquer Markdown do processo.
---

# research-report — o relatório é composto por código, não reescrito por agente

Este skill codifica a etapa G8 do processo. Princípios:
**conteúdo analítico entra verbatim (dossiê do Analista, valuation do Modelador);
todo número novo sai de uma chave (resultados.json/inputs.yaml/estado.yaml);
capa, sumário, tabelas, estilos, rodapé e paginação são template fixo; zero prosa de agente
para montar ou conferir.**

Responder em PT-BR.

## 1. Scripts

| Script | Função | Quem roda |
|---|---|---|
| `checar.py <ns> --etapa dossie\|valuation\|decisao\|relatorio\|tudo` | Valida por código: arquivos presentes por etapa, schema do inputs.yaml, chaves obrigatórias do resultados.json, chaves citadas no valuation.md existem, decisão presente. Exit 1 = reprovado com lista objetiva | Coordenador (substitui QC manual) |
| `compor.py <ns>` | Gera `relatorio.md` (tearsheet + dossiê verbatim + valuation verbatim + auditoria/encaixe/plano/notas) e `log_consistencia.md` (por construção); regenera `grafico_faixas.png` do JSON se faltar | Coordenador (SUMÁRIA) ou Redator |
| `render_pdf.py <arquivo.md> [--out x.pdf]` | GENÉRICO: Markdown + template.css → PDF com capa (front-matter), sumário automático, tabelas, imagens, rodapé e paginação. weasyprint, fallback wkhtmltopdf | Qualquer agente, para qualquer md |

## 2. Insumos do compor.py (namespace `/tmp/analise/<TICKER>/`)

Obrigatórios: `estado.yaml` (com bloco `decisao` — ver schema abaixo), `inputs.yaml`,
`dossie.md`, `valuation.md`, `saida_<TICKER>/resultados.json`.
Opcionais (ausência degrada com nota padronizada): `red_team.md` (com cabeçalho YAML do
Auditor: agregado, dimensoes, issues, cap_auditoria), `portfolio_fit.md`, `grafico_faixas.png`.

Schema mínimo do `estado.yaml` (dono: Coordenador):

```yaml
ticker: ABT
data: "2026-07-14"
profundidade: SUMARIA        # SUMARIA | PADRAO | REFORCADA
modo: PARCIAL                # carimbo do Modelador
snapshot: false
auditoria: {acionada: false, agregado: null}
engine: {versao: "2.0.0", hash: "..."}
decisao:                     # bloco escrito no G7; pré-requisito do compor.py
  recomendacao: "WATCHLIST (DISTANTE) — NÃO COMPRAR AGORA"
  confianca: MEDIA
  racional: "1-3 frases do G7"
  tese: "opcional: parágrafo de tese para a capa do tearsheet"
  ressalvas: ["opcional; as padronizadas (sem auditoria/sem snapshot) são automáticas"]
  gatilhos: ["US$80: diligência final", "US$70: entrada inicial"]
  plano_acao: ["opcional; default gerado da recomendação + gatilhos"]
  revisao: "após release 3T26"
pendencias: [{id: P1, texto: "...", dono: Modelador}]
```

**REGRA DE SCHEMA (dura):** `decisao.ressalvas`, `decisao.gatilhos` e `decisao.plano_acao`
são **LISTAS YAML** (`campo: ["item 1", "item 2"]` ou itens com `-`), nunca string escalar
nem bloco `>`/`|`. String escalar quebra a composição (um item por caractere no relatório).
O `checar.py --etapa decisao` reprova o tipo errado; o `compor.py` ainda aplica coerção
defensiva (string vira um item por linha), mas a coerção é rede de segurança, não licença.

## 3. Fluxo canônico (G8)

1. `python checar.py <ns> --etapa decisao` (pré-requisito; reprova sem decisão G7).
2. `python compor.py <ns>` → `relatorio.md` + `log_consistencia.md` + gráfico.
3. Profundidade SUMÁRIA: renderize direto (passo 5). PADRÃO/REFORÇADA: o Redator lê o
   `relatorio.md` UMA vez e faz edições pontuais de transição/dedup (mandato dele; máx. ~15,
   nunca em números, nunca reescrevendo parágrafos do dossiê/valuation).
4. `python checar.py <ns> --etapa relatorio` (marcadores resolvidos, arquivos presentes).
5. `python render_pdf.py <ns>/relatorio.md --out <ns>/relatorio_final.pdf`.

## 4. Regras duras

- NUNCA reescrever em prosa o que compor.py injeta; NUNCA digitar número no relatório
  (números novos = nova chave no JSON ou campo no estado.yaml, e re-compor).
- Re-compor é barato e idempotente: mudou um input, rode compor.py de novo ANTES das
  edições do Redator (as edições dele são a última etapa sobre o texto).
- O log_consistencia.md do compor.py é a checagem de consistência oficial (por construção);
  não refazer conferência numérica manual.
- Ausências (auditoria, snapshot) geram nota padronizada automática; nunca simule conteúdo.

## 5. Saídas visuais e tabelas geradas pelo compor.py

- **Tabela de premissas por limite** (substitui o gráfico de faixas): para cada âncora
  (Preço Máximo para o Hurdle e Valor Intrínseco Econômico), mostra CAP, ROE, g, Ke e o
  preço por ação do limite inferior e do superior, mais a linha ponderada/central. O
  gráfico de faixas (PNG) só é gerado com `--com-grafico` (opt-in).
- **Gráfico de histórico financeiro** (se `fatos.series_historicas` existir): receita e
  lucro líquido em barras, ROE em linha; cores fixas Receita #002060, Lucro Líquido
  #FFC000, ROE #7F7F7F. Injetado após o dossiê.
- **Gráfico de P/L histórico** (se `fatos.multiplos_historicos.pe.serie` existir): linha do
  P/L da companhia com pontilhadas na mediana e em mediana ± 1 desvio-padrão. Injetado após
  a validação por múltiplos.
- Todos degradam com nota (sem quebrar) quando a série ou o matplotlib faltam; o `checar.py
  --etapa dossie` avisa (não reprova) se as séries estiverem ausentes.

## 6. Arquivos deste skill

- `compor.py` — composição determinística do relatório + log de consistência + gráficos
- `checar.py` — validações de namespace/schema/chaves por etapa (exit code)
- `render_pdf.py` — renderizador genérico Markdown → PDF (template institucional)
- `template.css` — identidade visual fixa (capa, sumário, tabelas, rodapé, paginação)
