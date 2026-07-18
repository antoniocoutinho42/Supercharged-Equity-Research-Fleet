# Cadeia de gates do processo (P1) e atualização por delta (P2)

Fonte: `docs/fontes/Coordenador de Research.md`, Seção 4 (cadeia do P1), com o
G1_5 (pré-profundidade) adicionado como camada de economia entre o G1 e o G2.
Um turno por gate. Validação SEMPRE por código (`scripts/pipeline.py`,
`skills/er-relatorio/checar.py`), nunca por releitura em prosa. Todo veredicto
gravado em `estado.yaml` é um enum de UMA palavra: `PENDENTE`,
`EM_ANDAMENTO`, `APROVADO`, `APROVADO_COM_RESSALVA`, `REPROVADO`, `VETO`,
`PULADO`, `ENTREGUE` (ver `GATES`/`VEREDICTOS` em `scripts/pipeline.py`). O
racional de cada gate é 1 a 3 frases no campo, ou no `--racional` do comando;
nunca narrativa longa dentro do `estado.yaml`.

## G1 — Guardrails

- O que faz: primeira triagem de veto/nogo da empresa.
- Quem executa: Analista, skill `er-guardrails`. Delegação: "rode SOMENTE os
  guardrails de [empresa]".
- Pré-condição: nenhuma (primeiro gate; `init` já cria `estado.yaml` com todos
  os gates em `PENDENTE`).
- Em VETO: reporte o veredicto com "o que teria de mudar" e ENCERRE o
  processo; nenhum gate seguinte pode fechar depois de um VETO. Exceção
  única: veto apoiado em dado incerto autoriza UMA verificação dirigida antes
  de encerrar.
- Verificação por código: `python scripts/pipeline.py <ns> gate G1
  --veredicto APROVADO|APROVADO_COM_RESSALVA|VETO --racional "..."`.

## G1_5 — Pré-profundidade (NOVO)

- O que faz: com fatos mínimos já disponíveis após o G1 (preço atual, LPA
  aproximado, consenso de mercado, quando existirem), o Modelador roda o
  engine em modo coarse (rascunho, sem inputs completos do Analista) só para
  carimbar uma profundidade PROVISÓRIA, ANTES de encomendar o dossiê
  completo. Evita orçar um dossiê de 8 páginas para um caso obviamente
  SUMÁRIA, ou o inverso.
- Quem executa: Modelador, skill `er-valuation` (rodada leve do engine); o
  Coordenador registra o veredicto e a profundidade provisória.
- Pré-condição: `G1` em `{APROVADO, APROVADO_COM_RESSALVA}`.
- Sem fatos mínimos disponíveis rapidamente (ex.: sem cobertura de consenso):
  o gate é `PULADO` e o processo segue para o G2 com profundidade `PADRAO`
  como default.
- REGRA DE ADITIVIDADE: a profundidade do G1_5 é provisória e existe só para
  dimensionar o dossiê com economia; o G3_0 sempre confirma ou eleva depois
  dos fatos completos. Elevar depois do G1_5 é aditivo (mais diligência
  encomendada ao Analista/Modelador, nunca descarte do que já foi produzido).
  Rebaixar a profundidade depois do G1_5 exige justificativa registrada no
  racional do gate que rebaixa (evita destruir trabalho já orçado sem causa).
- Verificação por código: `python scripts/pipeline.py <ns> gate G1_5
  --veredicto APROVADO|PULADO --racional "..." --ref <arquivo do rascunho do
  engine>` (e, se já souber a profundidade provisória, `python
  scripts/pipeline.py <ns> set profundidade <SUMARIA|PADRAO|REFORCADA>`
  antes ou depois).

## G2 — Dossiê

- O que faz: dossiê completo, ficha de valuation (`inputs_valuation.md`) e
  `inputs.yaml` (meta e fatos), no orçamento de páginas da profundidade
  corrente (provisória do G1_5, ou `PADRAO` default).
- Quem executa: Analista, skill `er-dossie`, com o foco e as prioridades do
  intake.
- Pré-condição: `G1_5` em `{APROVADO, APROVADO_COM_RESSALVA, PULADO}`.
- `nogo.md`: reporte e encerre, salvo ordem em contrário do usuário.
- Verificação por código: `python skills/er-relatorio/checar.py <ns> --etapa
  dossie` (presença de arquivos, schema do `inputs.yaml`, ledger da ficha).
  REPROVADO volta ao Analista com a lista de faltas do próprio script, sem
  prosa sua. Depois de reprovado e corrigido: `python scripts/pipeline.py
  <ns> gate G2 --veredicto APROVADO --racional "..."`.

## G3_0 — Profundidade (confirmação)

- O que faz: o Modelador roda `cap_check.py` + `engine.py` completos (com os
  fatos do G2) e reporta `gate.modo_recomendado` com razões numéricas. O
  Coordenador carimba a profundidade final em UMA linha: `SUMARIA` (lado
  inequivocamente caro) | `PADRAO` (zona de debate) | `REFORCADA` (entrada
  acionável ou limítrofe: diligência final do Analista, PM com política
  quando houver snapshot, recomendação de auditoria em uma linha).
- Quem executa: Modelador (roda o engine); Coordenador (carimba).
- Pré-condição: `G2 = APROVADO`.
- Sobrescrever a recomendação do engine exige justificativa registrada no
  racional do gate.
- Verificação por código: `python scripts/pipeline.py <ns> gate G3_0
  --veredicto APROVADO --racional "..." --ref <arquivo do gate do engine>
  --profundidade <SUMARIA|PADRAO|REFORCADA>` (a profundidade é obrigatória
  na primeira vez que o G3_0 fecha, se ainda não foi definida via `set
  profundidade`).

## G3 — Valuation

- O que faz: o Modelador entrega `valuation.md` no orçamento de páginas da
  profundidade carimbada.
- Quem executa: Modelador, skill `er-valuation`.
- Pré-condição: `G3_0 = APROVADO` e `engine` definido (`python
  scripts/pipeline.py <ns> set engine --versao X --hash Y`).
- Pedido de calibração do Modelador (precisa de dado novo do Analista):
  roteie ao Analista como delta, uma rodada por padrão. Modo custom: só com
  o motivo registrado no racional do gate.
- Verificação por código: `python skills/er-relatorio/checar.py <ns> --etapa
  valuation` (chaves obrigatórias e citadas), depois `python
  scripts/pipeline.py <ns> gate G3 --veredicto APROVADO --racional "..."`.

## G4 — Auditoria (SOMENTE sob ordem explícita do usuário)

- O que faz: o Auditor entrega `red_team.md` com cabeçalho YAML (agregado,
  dimensões, issues, `cap_auditoria`). Pode ser acionada no kickoff, no meio
  do processo ou pós-entrega (pós-hoc: audita os arquivos canônicos;
  críticas disparam correção estilo P2 e re-composição do relatório).
- Quem executa: Auditor, skill `er-auditoria`. Nunca por iniciativa do
  Coordenador.
- Pré-condição: `G3 = APROVADO` (ou `G8 = ENTREGUE`, para auditoria
  pós-entrega).
- MOMENTOS DE RECOMENDAÇÃO de auditoria (uma linha, uma única vez cada):
  (a) `REFORCADA` carimbada no G3_0; (b) o Modelador propõe CAP base >= 25
  anos. Formato: "Recomendo acionar a auditoria porque [meia linha]; autoriza?".
  Sem autorização do usuário: siga sem G4.
- Verificação por código: sem ordem, `python scripts/pipeline.py <ns> set
  auditoria --acionada false` e o processo segue sem fechar G4. Com ordem e
  entrega: `python scripts/pipeline.py <ns> set auditoria --acionada true
  --agregado <DEMONSTRADA|DEMONSTRADA_COM_RESSALVAS|NAO_DEMONSTRADA|REPROVADA>`
  seguido de `python scripts/pipeline.py <ns> gate G4 --veredicto ENTREGUE
  --racional "..."`.

## G5 — Contraditório (só quando o G4 rodou; SÓ CRÍTICAS; uma rodada)

- O que faz: roteia os IDs das críticas às threads dos donos do domínio; a
  resposta esperada é patch + re-execução; o Auditor revalida. Nenhuma
  crítica aberta segue adiante (fecha, rebaixa a recomendação, ou escala ao
  usuário). RELEVANTES viram `pendencias` no `estado.yaml`; MENORES nunca
  geram rodada.
- Quem executa: Coordenador roteia; os donos (Analista/Modelador) corrigem;
  Auditor revalida.
- Pré-condição: `G4 = ENTREGUE` (para qualquer veredicto real); `G5 = PULADO`
  só é permitido quando `G4 = PULADO` (auditoria pulada por inteiro).
- Verificação por código: `python scripts/pipeline.py <ns> gate G5
  --veredicto APROVADO|APROVADO_COM_RESSALVA|PULADO --racional "..."`.

## G6 — Encaixe (condicional a snapshot)

- O que faz: PM avalia encaixe na carteira e política de posição, entrega
  `portfolio_fit.md`.
- Quem executa: PM, skill `er-portfolio`. Delegação de 3 linhas com
  ponteiros e status da verificação.
- Pré-condição: `G3 = APROVADO`. Só roda com `snapshot: true` e, se houve
  auditoria, agregado `DEMONSTRADA` ou `DEMONSTRADA_COM_RESSALVAS`.
- Sem snapshot: `pipeline.py` recusa qualquer veredicto que não seja
  `PULADO`; registre `snapshot: false` e não insista com o usuário.
- Verificação por código: `python scripts/pipeline.py <ns> gate G6
  --veredicto APROVADO|APROVADO_COM_RESSALVA|PULADO --racional "..."`.

## G7 — Decisão

- O que faz: aplica `references/regras-decisao.md` e ESCREVE o bloco
  `decisao` completo no `estado.yaml` numa única passada (é o insumo direto
  da composição; sem ele o `checar.py --etapa decisao` reprova).
- Quem executa: Coordenador.
- Pré-condição: `G3 = APROVADO`; se `auditoria.acionada = true`, `G5` em
  `{APROVADO, APROVADO_COM_RESSALVA}`; bloco `decisao` presente no candidato.
- ATENÇÃO DE SCHEMA: `decisao.ressalvas`, `decisao.gatilhos` e
  `decisao.plano_acao` são LISTAS YAML, nunca string escalar nem bloco `>`/`|`.
- Verificação por código: `python scripts/pipeline.py <ns> gate G7
  --veredicto APROVADO --racional "..."` (o comando reprova sem o bloco
  `decisao` bem formado).

## G8 — Composição e entrega

- O que faz: composição determinística do relatório final.
- Quem executa: profundidade `SUMARIA`: o próprio Coordenador roda
  `compor.py`, `checar.py --etapa relatorio` e `render_pdf.py`, e entrega o
  PDF com os arquivos-fonte como apêndice (sem Redator). `PADRAO`/`REFORCADA`:
  delegue ao Redator em 2 linhas ("componha e edite o relatório de <ns>;
  profundidade X; extensão-alvo Y"); QC do Coordenador ao receber: exit code
  do `checar.py --etapa relatorio` + a lista de edições do Redator (edição em
  número ou em decisão devolve ao Redator).
- Pré-condição: `G7 = APROVADO`.
- Verificação por código: `python skills/er-relatorio/checar.py <ns> --etapa
  decisao` (pré-requisito), depois o fluxo de `er-relatorio` (compor,
  checar --etapa relatorio, render_pdf), e por fim `python
  scripts/pipeline.py <ns> gate G8 --veredicto ENTREGUE --racional "..."`.

## P2 — Atualização por delta

Fato novo (evento, release, guidance): Analista roda delta (fatos alterados
apontados) se houver fato novo; Modelador re-roda o engine só com o que
mudou; Auditor entra só sob ordem; a composição é re-executada (`compor.py`
é idempotente) e o PDF é re-renderizado. Reporte ao usuário só o que mudou
nos sinais (não repita o que não mudou). Até o `delta.py` dedicado existir
(Task 3.1), o delta é conduzido reabrindo os gates afetados no
`scripts/pipeline.py`, com o racional explicando a mudança de fonte.
