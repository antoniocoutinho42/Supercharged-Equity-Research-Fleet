# Upgrade v2 — FASE B: Roadmap B0→B5 (arquitetura A aprovada + 7 condições)

> **For agentic workers:** este é o ROADMAP mestre. Cada fase ganha um plano detalhado próprio
> (`YYYY-MM-DD-bN-*.md`) escrito NO INÍCIO da fase, executado com superpowers:executing-plans
> (inline) ou subagent-driven. Fases NUNCA começam sem o plano detalhado e NUNCA terminam sem:
> diff + testes verdes + PAUSA para aprovação do usuário. Não reabrir a FASE A.

**Goal:** incorporar ao fleet a metodologia adjudicada na FASE A (evidência em
`C:\Claude\upgrade_fleet_v2_fase_a\`): âncora operacional EV/EBIT justo no motor único, gates de
aplicabilidade, sensibilidade a spread terminal, camadas de imposto, série reformulada,
classificação por natureza com ledger, norma contábil na coleta — com regressão preservada.

**Arquitetura (A, aprovada):** blocos ADITIVOS no motor único (`pl_justo`); gating por presença
(nunca retroativo); ledger `classificacao.yaml` congelado no snapshot; normalização contábil na
coleta; engine agnóstico. Sem segundo motor, sem projeção de demonstrativos, sem dicionário de
rubricas, sem WACC derivado, sem sinal novo.

## Restrições globais (valem para TODAS as fases)

- Regressão: `resultados.json` com chaves idênticas exceto `engine.{versao,gerado_em}`; núcleo a 1e-12.
- Nenhuma versão promovida com teste vermelho; SemVer + CHANGELOG (comentário no engine.py, padrão da casa).
- Commits no repo somente APÓS aprovação da fase pelo usuário (gate humano por fase; diff mostrado antes).
- Python desta máquina: `C:\Claude\tools\python-nupkg\tools\python.exe` (não há python no PATH).
- Toda aritmética em código versionado; prosa interpreta citando chaves.
- Premissas nunca escolhidas pelo resultado (regra 6 do prompt master).

## As 7 condições da aprovação (2026-07-21) e onde cada uma fecha

| # | Condição | Fase dona | Registro |
|---|---|---|---|
| 1 | **B4 restaurado**: além da reprodução delta-zero, exercício operacional completo do TFCO4 — semear `fatos.reformulado` com a série 2020–2024 extraída do `T&F_CG_3Q24.xlsm` (aba Reformulated Accounts) + FY2025 reconstruído do PDF/DFP, lacunas rotuladas como diligência; `impacto_TFCO4.md` exercita no caso real: `ebit_justo`, paridade de âncoras (wedge 1,1789), reversa operacional (ROIC implícito) e `central_neutro` | B4 | plano detalhado do B4 |
| 2 | **Impacto decomposto por causa**: variação de cada âncora atribuída a (i) alavancas intencionais (LPA/CAP/Ke/φ), (ii) ROE derivado pela ponte vs input livre, (iii) base de lucro | B4 | seção obrigatória do `impacto_TFCO4.md` |
| 3 | **Paridade = WARNING** com nota de resolução obrigatória no relatório; NÃO bloqueia publicação; reavaliar após 3 análises reais | B1 (engine/checar) | decisão registrada no CHANGELOG e na SKILL; item de reavaliação em docs |
| 4 | **Rótulo Lopes H1 corrigido**: COM goodwill = 25,63% (reportado l.103); EX-goodwill = 27,10% | FEITO (pré-B0) | errata em `upgrade_fleet_v2_fase_a\hip_roic_classificacao.md` (verificação aritmética por recomputo direto) |
| 5 | **Diligências de fonte única fecham no B0** com segunda via independente, antes de qualquer edição no engine: flag §1.3.2 (Lopes, efeito por ação), flag §1.3.4 (PVV EoP), matrizes 3×3 do TFCO4 célula a célula | B0 | `verificacao_referencia.out` + memo |
| 6 | **História→números com dono**: tabela "história→premissa→implícito→evidência" entra no contrato do compor.py e no `OBRIG_JSON_V4` na MESMA passada única de contrato do B1/B2 | B1/B2 (passada única) | plano detalhado do B1 lista a passada única: chave nova → OBRIG_JSON_V4 → compor → humano()/linter → golden → fixture |
| 7 | **Limiares H7 PROVISÓRIOS** (E>0; mediana E/NOA ≥ 0,30; lucro recorrente >0; flags FLEV/NBC/ND) marcados como calibrados em n=3 no código E na SKILL, com instrução de recalibração a cada caso novo | B1 (código) + B5 (SKILL) | constante `H7_CALIBRACAO = "PROVISORIO_N3"` + texto na SKILL |

## Decisões ratificadas (não reabrir)

Dois ROICs por natureza; par média/inicial com EoP proibido; leasing em 3 pacotes fechados com trava
declarativa `leasing_pacote` e materialidade 5% do EV; NOL como claim valorado fora do engine;
Ke/WACC recebidos como premissa com dossiê de 2 rotas + prêmio de tamanho com critério; φ default 0,
sensibilidade de 1ª classe, **EXCLUSÃO MÚTUA φ × m_terminal** (ambos documentados na SKILL — item de
aceite duro do B5); norma contábil IFRS/CPC + US GAAP com stubs J-GAAP/CAS/Ind AS.

## Fases

- **B0 — Verificação de referência** (plano: `2026-07-21-b0-verificacao-referencia.md`):
  `referencia/verificacao_referencia.py` reproduz as identidades §1.2 nos 4 workbooks (tabelas de
  aceitação da FASE A), registra a adjudicação dos 5 flags §1.3 com recomputo e FECHA as 3
  diligências da condição 5. Output: `verificacao_referencia.out` + `verificacao_referencia_memo.md`.
  Não toca o engine. Fora do repo (referencia/ não é git) — o "diff" da fase é a lista de arquivos novos.
- **B1 — Engine vNEXT** (bump minor, aditivo): `fatos.reformulado` validado quando presente;
  `ebit_justo` (pl_justo trailing com g/ROIC/CAP/WACC + cadeia (1−t)(1−d) + bridge de claims +
  paridade como WARNING com resolução obrigatória — condição 3); gates H7 (eliminatórios A1–A3 +
  flags; PROVISÓRIOS n=3 — condição 7); `sensibilidade_phi` sobre m_terminal com exclusão mútua;
  camadas de imposto; RiR/ROIIC implícitos por cenário; **passada única de contrato** (OBRIG_JSON_V4 +
  compor + humano()/linter + goldens + fixtures) incluindo a tabela história→números (condição 6).
- **B2 — Respostas R2–R5**: `central_neutro` + `robustez.conjunta`; `validacao_multiplos.implicitos`
  com decomposição do prêmio por driver; `dossie_ke` (2 rotas, prêmio de tamanho com critério, grade
  Ke); `cap_check` reformado (confiança separada da banda, ônus de sobrescrever para BAIXO, CAP
  equivalente do fade). Itens de contrato de relatório do B2 entram na mesma passada única do B1.
- **B3 — Classificação por natureza + norma contábil**: critérios nos references dos mandatos (teto
  4096 bytes respeitado); `classificacao.yaml` por análise (schema próprio, congelado no snapshot,
  linhas ambíguas flagadas ao Auditor); jurisprudência consultiva; pacotes de leasing com trava;
  `fatos.norma_contabil` + checklist por regime aplicada no G2.
- **B4 — Exercício TFCO4 completo (condições 1 e 2)**: série reformulada 2020–2024 do próprio
  workbook TF + FY2025 do PDF/DFP (lacunas = diligência rotulada); engine novo em modo regressão
  (inputs antigos: chaves idênticas exceto engine.{versao,gerado_em}) e modo completo;
  `impacto_TFCO4.md` por chave com decomposição por causa (i)/(ii)/(iii). SEM recomendação nova.
- **B5 — Documentação e mandatos**: SKILL.md do er-valuation (m_terminal + φ com exclusão mútua —
  aceite duro; limiares H7 provisórios — condição 7; correção do rótulo "v2"; nomenclatura
  "franchise-fade" → "spread constante + cliff modulável"); mandatos (Analista: coleta reformulada +
  detecção de norma; Modelador: cenários margem×giro, dossiê de Ke, CAP novo; Auditor: recomputo da
  ponte, paridade e gates); CHANGELOG; CLAUDE.md/README.

## Critérios de aceite finais (prompt §7, corrigidos por evidência da FASE A)

- [ ] `verificacao_referencia.py` reproduz os 4 workbooks + 5 flags + 3 diligências da condição 5 (B0)
- [ ] Golden tests antigos: chaves idênticas exceto `engine.{versao,gerado_em}`, núcleo 1e-12; novos verdes
- [ ] `ebit_justo` + paridade-WARNING + reverse operacional + gates H7 (provisórios n=3) funcionando
- [ ] Cenários margem×giro com RiR/ROIIC implícitos; tabela história→números no contrato do compor (condição 6)
- [ ] R2–R5 respondidas (central_neutro, implícitos, dossiê de Ke, cap_check novo)
- [ ] Sensibilidade φ reportada; exclusão mútua φ×m_terminal; contribuição do φ=0 ao prêmio quantificada
- [ ] Ledger por análise + invariantes; norma contábil detecção+checklist; engine agnóstico
- [ ] `impacto_TFCO4.md` por chave COM decomposição por causa (condição 2); sem recomendação nova
- [ ] SKILL/mandatos/CHANGELOG/CLAUDE.md atualizados; versão bumpada
