---
name: er-analise
description: >-
  USE SEMPRE, ANTES de qualquer resposta, quando o pedido envolver analisar uma empresa ou ação
  com ticker, iniciar cobertura, atualizar tese, rodar valuation, decidir compra ou venda, ou
  qualquer pergunta de equity research sobre ticker já analisado — inclusive "o preço de X faz
  sentido?", "vale a pena entrar em Y?", "essa ação está cara?", release novo, P2 e pergunta
  pontual. Workflow master do fleet v3: Analista no loop principal (F0–F11), Data Manager como
  único subagente de coleta, motor K3 V2.2.1 congelado, entrega em HTML de 2 abas, memória
  durável por código. NÃO use para sourcing sem ticker nem para questões de carteira inteira
  (essas vão para a skill portfolio-construction, fora do fleet).
---

# er-analise — workflow master do Analista (fleet v3)

O Analista é o loop principal: coordena, pesquisa, analisa, calibra, opera o engine e assina o
conteúdo. Um único subagente existe — o Data Manager (`agents/data-manager.md`, skill
`er-dados-openbb`), dono exclusivo das chamadas OpenBB (exceção única: snapshot de perfil/preço
do briefing, F1). Sem gates, sem auditor, sem PM, sem redator: o QC é por código
(SUITE PASS, paridade Python↔JS, `checar_relatorio.py`).

Norte permanente: como a empresa será no FUTURO e como isso se traduz nos 16 inputs canônicos.

## 1. Modos e roteamento

- **Análise completa** ou **somente valuation** — perguntado expressamente no grill-me (F2),
  nunca assumido em sessão atendida.
- **Ticker já analisado** (existe `analises/_memoria/<TICKER>.md`) → NUNCA reabrir a análise por
  reflexo: seguir `references/memoria-e-p2.md` (pergunta pontual responde da memória +
  `results.json`; fato novo vira P2 por materialidade).
- Fora de escopo: sourcing sem ticker; carteira → apontar `portfolio-construction` em 1 linha.

## 2. Fases F0–F11 (detalhe: `references/fases.md`)

| Fase | Objetivo | Saída |
|---|---|---|
| F0 | Intake: desambiguar ticker/listagem/moeda; consultar memória; criar workspace | `analises/<TICKER>/` |
| F1 | Briefing inicial (1 página; única chamada OpenBB do Analista) | `00_briefing.md` |
| F2 | Grill-me com o usuário (ordem fixa: modo → hurdle → validação → específicas) | `01_grill_me.md` |
| F3 | Estudo do método (er-motor-k3) e classificação do perfil/arquétipo §7 | notas + lista de dados |
| F4 | Despacho do Data Manager em background (brief + categorias) | `dados/` + `ledger.md` |
| F5 | Análise qualitativa (em paralelo à coleta) | `qualitativa.md` |
| F6 | Análise financeira histórica (sincroniza com dados/) | `financeira.md` |
| F7 | Calibração dos 16 inputs × cenários (ordem canônica §4.0) | `calibracao.md` |
| F8 | Engine: SUITE PASS → value → sens → congelar → implied → hurdle | `case.json`, `saida/results.json` |
| F9 | Checkpoint de premissas (SÓ se optado em F2) | ajustes → re-F8 |
| F10 | Relatório HTML (builder + checar; banner verde) | `relatorio/relatorio_<TICKER>.html` |
| F11 | Fechamento: memória durável por código + lições | `analises/_memoria/<TICKER>.md` |

Modo somente-valuation (Seção 6 do desenho): F0–F3 iguais (grill-me curto), F4 essencial,
F5–F6 substituídas por pesquisa dirigida com racional direto em `calibracao.md`, F7–F9 iguais,
F10 com `--modo valuation`, F11 igual (memória fecha SEMPRE).

## 3. Regras duras (invioláveis — Seção 9 do desenho)

1. Metodologia congelada V2.2.1: o engine faz TODA a matemática; PROIBIDO recomputar ou
   aproximar em prosa, planilha ou JS novo.
2. Regression gate: SUITE PASS antes de qualquer entrega; banner de paridade verde no HTML;
   builder recusa emitir divergente.
3. Dados financeiros SÓ via OpenBB e SÓ pelo Data Manager (exceção única: snapshot do F1).
   Pesquisa qualitativa (setor, concorrência, jurídico, management, RI, filings, notícias) é livre.
4. Gaps: MATERIAL (bloqueia input crítico ou a escala) → perguntar ao usuário, que pode fornecer
   o dado manualmente; NÃO-MATERIAL (degrada gráfico/contexto, incl. janela curta de fundamentals)
   → nota de limitação e segue. Nunca inventar, nunca silenciar.
5. Hurdle NUNCA tem default (12% não é assumido; ausência é declarada). Rodada hurdle sempre via
   `label_mode: "hurdle"` e sempre rotulada Hurdle-conditioned — nunca chamada de fair value.
6. Market-implied NUNCA recalibra o fair value; comparação com preço só depois da calibração
   congelada. Nunca calibrar contra o preço de mercado.
7. Respostas do usuário no grill-me são evidência a verificar, nunca fato.
8. `notas.md` atualizado a CADA fase (bullets datados) — memória de trabalho obrigatória.
9. Memória durável gerada por código (`scripts/memoria.py`); correção de número é na fonte +
   regenerar, NUNCA editar a nota à mão.
10. Sem guardrails eliminatórios, sem auditor, sem portfolio fit, sem PDF.

## 4. Checkpoints com o usuário

Três momentos: grill-me (F2), gap MATERIAL (a qualquer tempo) e checkpoint de premissas (F9, só
se optado). **Sessão desatendida** (usuário não responde o grill-me): declarar defaults em
`01_grill_me.md` — modo completo, sem hurdle, sem checkpoint de premissas — marcar cada resposta
simulada explicitamente como SUPOSIÇÃO (também no relatório) e seguir.

## 5. Workspace

`analises/<TICKER>/` (memória central em `analises/_memoria/`): `00_briefing.md`,
`01_grill_me.md`, `notas.md`, `dados/` (domínio do DM: arquivos por categoria + `ledger.md` +
`pedidos.md`), `qualitativa.md`, `financeira.md`, `calibracao.md`, `case.json`,
`saida/results.json`, `relatorio/relatorio_<TICKER>.html`. Sem `estado.yaml`, sem runs
imutáveis: re-rodar é barato e o regression gate protege o motor.

## Referências

- `references/fases.md`: detalhe operacional de cada fase (F0–F11) e do modo somente-valuation.
- `references/qualitativa-e-financeira.md`: roteiro de F5 (pilares, moat/duração) e F6
  (reconstrução histórica, DuPont, FCFE pelas relações do manual).
- `references/memoria-e-p2.md`: protocolo de leitura da memória, pergunta pontual, P2 por
  materialidade e fechamento F11.
