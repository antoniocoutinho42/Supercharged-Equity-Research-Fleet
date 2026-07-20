# Correções sistêmicas pós-HG — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans (execução inline nesta sessão).

**Goal:** Tratar os 7 requisitos (R1-R7) do feedback do relatório HG como causas sistêmicas no fleet, preservando determinismo, goldens, snapshot/hash, gates e o contrato entre agentes.

**Architecture:** As mudanças vivem onde cada comportamento nasce: engine.py (inputs estruturais, hurdle opcional, experimentos/sinais de sensibilidade, matrizes 3×3, eco de resolução de divergência), checar.py (bloqueios de publicação por código), compor.py (relatório institucional + anexo técnico), schemas/validar (metodo.yaml do R1), e skills/agentes/mandatos (julgamento metodológico, hurdle do usuário, auditoria proporcional).

**Tech Stack:** Python stdlib + pyyaml/jsonschema/matplotlib (já usados), pytest + golden scripts standalone.

## Confirmação de semântica na fonte (pré-requisito do mandato)

- **DE/NDE (engine.py:88-106,150-155):** `payout = (1 − g/ROE) + (DE − NDE)·(g/ROE)`; docstring: "DE = dívida/PL e NDE = dívida líquida/PL, MEDIDOS; DE=NDE=0 é exceção declarada". Logo (DE−NDE) = caixa/PL. Confirmado também em `ficha-e-fatos.md` ("dívida/PL E dívida líquida/PL medidas") e no golden A4/A5 (DE=NDE neutro; DE>NDE eleva múltiplo com g>0). Fixture FNV mede `de: 0.00, nde: −0.088` (caixa líquido ⇒ NDE negativo é válido).
- **Base de LPA (engine.py:251-252, 262):** preço = `lpa_ajustado_fy × P/L`; cross-check GAAP com `lpa_gaap_fy`. Elasticidades e matrizes herdam o MESMO `lpa` fixo.
- **Ceteris paribus das elasticidades (engine.py:352-368):** cada elasticidade varia UM parâmetro do cenário base mantendo fixos LPA, os demais drivers, DE/NDE e m_terminal. Em particular `mais_1pp_roe` mantém lucro e g fixos ⇒ book implícito (lucro/ROE) encolhe e o termo terminal (∝ m/ROE) cai — exatamente o experimento do sintoma HG.
- **Hurdle:** `premissas.ke_hurdle` é obrigatório hoje (KeyError sem ele); o default de fato (12%) vive em `docs/fontes/Modelador Financeiro.md` §3.1 ("padrão 12%"), no exemplo canônico (`inputs_exemplo_vrsk.yaml: ke_hurdle: 0.12`) e no fluxo coarse do G1_5 (er-guardrails, "premissas default").

## Mapeamento sintoma → causa → mudança

| # | Sintoma (caso HG) | Causa no repo | Mudança |
|---|---|---|---|
| 1 | Fluxo padrão auto-autorizado p/ resseguradora; inadequação só no fim | Nenhuma etapa exige julgamento de aderência ANTES da coleta/valuation; só existe recusa tardia (LPA≤0) | **R1:** `metodo.yaml` (novo schema) produzido no G1_5/G2 pelo Analista e revisado pelo Modelador antes do G3; `checar.py` gate por código; skills er-guardrails/er-dossie/er-valuation/gates.md |
| 2 | NDE=0,0 arbitrário por lacuna de coleta | `engine._de_nde` assume 0/0 com AVISO brando; plano de coleta não antecipa caixa livre | **R2:** engine v3 recusa DE/NDE ausentes sem `premissas.excecao_de_nde{motivo, faixa_alternativa}`; com exceção, engine CALCULA a sensibilidade da premissa substituta; ficha-e-fatos exige discriminação de caixa livre quando há float (via R1) |
| 3 | Hurdle 12% aplicado como default | "padrão 12%" no mandato do Modelador; exemplo canônico; coarse G1_5 | **R3:** `ke_hurdle` opcional no engine (degrade limpo p/ âncora econômica, `SEM_HURDLE`); intake do er-processo pergunta o retorno exigido; mandato/exemplo deixam de oferecer default |
| 4 | DIVERGE_MATERIAL publicado como "pendência tratada" | Flag do engine não bloqueia; regras-decisao só "rebaixa confiança" | **R5:** `premissas.resolucao_divergencia{via,texto}` ecoada pelo engine; `checar --etapa valuation` REPROVA divergência sem resolução; regras-decisao G7 bloqueia |
| 5 | Elasticidade ROE negativa publicada só com justificativa algébrica | `bloco_elasticidades` não declara experimento nem checa sinal esperado | **R4:** engine emite `experimento` por parâmetro + `alertas_sinal` (esperado vs observado); resposta do Modelador (`premissas.respostas_sinais`) é item bloqueante no checar |
| 6 | Relatório com linguagem de máquina | compor injeta chaves/hashes/títulos operacionais no corpo; racional do G7 é log da matriz | **R6:** compor reorganiza corpo institucional + Anexo Técnico; strip determinístico de citações de chave; títulos institucionais; tese como cadeia causal; linter de linguagem operacional no checar |
| 7 | Tabelas de limite pouco decisórias; gráficos sem rótulos | `secao_tabela_premissas_por_limite`; gráficos sem annotate | **R6:** engine emite `matrizes` (6× 3×3 com preço/célula, fixos declarados); compor renderiza; rótulos de dados nos gráficos |
| 8 | Recomputo integral a cada rodada | escopos.md `calculo` exige recomputo 5-8 números sempre | **R7:** recomputo restrito a gatilhos (fora do fluxo determinístico, fórmula sem teste, falha de controle, anomalia); mandato explicita o que testes NÃO validam |

## Tasks

1. **Schema metodo + validar.py** — `schemas/metodo.schema.json`; registrar `metodo` em `NOMES_VALIDOS`; testes.
2. **Engine v3.0.0** — R2 (recusa/exceção/sensibilidade DE-NDE), R3 (hurdle opcional + degrade de sinais/gate/reverse/elasticidades), R4 (experimento + alertas_sinal + respostas), R5 (eco resolucao_divergencia), R6 (bloco matrizes). CHANGELOG + golden tests novos; camadas A/B intactas.
3. **inputs_exemplo_vrsk.yaml** — exceção DE/NDE declarada com faixa; comentário anti-default no ke_hurdle; docs de respostas_sinais/resolucao.
4. **checar.py** — metodo no dossie/valuation; R4/R5 bloqueantes no valuation; OBRIG_JSON ciente de sem-hurdle; linter de linguagem operacional no relatorio (corpo, pré-anexo).
5. **compor.py** — corpo institucional (renomeações, tese causal, matrizes, cenários, auditoria executiva, sem chaves/hash/enums crus, degrade sem hurdle) + Anexo Técnico (nota metodológica, trilha, red_team integral, resoluções); rótulos de dados nos gráficos.
6. **Skills/agentes/mandatos** — er-processo (intake hurdle), gates.md (metodo nos pré-requisitos), regras-decisao.md (R5 bloqueio, degrade sem hurdle), er-guardrails (metodo preliminar no G1_5; coarse sem hurdle), er-dossie + ficha-e-fatos (dados adicionais do metodo; caixa livre), er-valuation SKILL (R1-R5), er-auditoria + escopos.md (R7), agents/*.md, docs/fontes/Modelador (remoção do default 12%; novas regras).
7. **Fixtures FNV** — `metodo.yaml` novo; `inputs_p3.yaml` ganha respostas_sinais + resolucao_divergencia (mudança INTENCIONAL: novo hash + oráculo regenerado + constantes dos testes atualizadas com justificativa).
8. **Testes novos** — recusa/degradação: sem hurdle; exceção estrutural sem justificativa; divergência sem resolução; sinal contraintuitivo sem resposta; linter do relatório; matrizes vs pl_justo; metodo gating.
9. **Versão do plugin** — 2.0.0 (contrato de inputs quebra), README notas.
10. **Demonstração e2e** — recompor FNV; verificar R6; suíte 100% verde.
