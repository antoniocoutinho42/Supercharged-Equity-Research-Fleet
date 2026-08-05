# Fases F0–F11 — detalhe operacional

PT-BR direto; nomes canônicos dos 16 inputs e rótulos técnicos do engine em inglês.

## F0 — Intake

Desambiguar ticker, listagem e moeda (ex.: PETR4 vs PBR; ON vs PN; ADR). Consultar
`analises/_memoria/<TICKER>.md`: se existir, propor P2 ou pergunta pontual
(`references/memoria-e-p2.md`) em vez de análise nova — reabrir só se o usuário pedir. Criar
`analises/<TICKER>/` e abrir `notas.md` (primeiro bullet datado).

## F1 — Briefing inicial (`00_briefing.md`, 1 página)

O que a empresa é, segmentos e modelo de receita, posição de mercado, estrutura societária e
listagem, snapshot de perfil/preço/market cap — esta é a ÚNICA chamada OpenBB permitida ao
Analista (equity_profile + equity_price_quote; provider yfinance; B3 = sufixo `.SA`). Fontes
qualitativas livres (web, RI). Objetivo: sustentar um grill-me inteligente, não um dossiê.

## F2 — Grill-me (`01_grill_me.md`)

Perguntar NESTA ordem:
1. **Modo**: análise única e profunda, ou somente valuation? (pergunta expressa, sempre).
2. **Hurdle**: retorno mínimo exigido? Opcional e SEM default — se informado, o engine roda
   também a rodada `label_mode: "hurdle"` e o HTML exibe rotulado; se não, a ausência é declarada.
3. **Validação de premissas**: quer revisar os 16 inputs antes da entrega? (define se F9 existe).
4. **Específicas da empresa**, derivadas do briefing: pontos a aprofundar; conhecimento prévio
   do usuário (contábil, setorial, judicial, societário); divergências dele vs consenso; eventos
   próximos relevantes.

Registrar perguntas E respostas. Toda resposta é evidência a verificar, nunca fato. Sessão
desatendida: defaults declarados (modo completo, sem hurdle, sem F9); cada resposta simulada
marcada como SUPOSIÇÃO em `01_grill_me.md` E no relatório (seção de limitações).

## F3 — Método e perfil

Ler `er-motor-k3` (SKILL.md + manual: relações financeiras §3, ordem de calibração §4.0, política
de Ke §6, arquétipos §7) e classificar o perfil da empresa nas linhas relevantes do §7 (pode ser
mais de uma: ex. cíclica + capital intensive + estatal). Derivar e anotar em `notas.md`:
(a) lista de dados a pedir ao DM (categorias + séries setoriais/commodities do perfil);
(b) riscos de calibração típicos do perfil (coluna "principal failure mode" do §7);
(c) gráficos específicos do negócio que a aba 2 vai precisar (ex.: preço de commodity, margens,
asset turnover, produção).

## F4 — Despacho do Data Manager (assíncrono)

Brief curto: ponteiros para `00_briefing.md` e `01_grill_me.md` + lista de dados por categoria
(doutrina e nomes de arquivo: skill `er-dados-openbb`). Despachar em BACKGROUND e seguir para F5
sem esperar. O DM valida cobertura, coleta, salva em `dados/`, escreve `ledger.md`, sugere
adições e classifica gaps. Gap MATERIAL → perguntar ao usuário (que pode fornecer o dado
manualmente; registrar proveniência manual no ledger); NÃO-MATERIAL → nota e segue.

## F5 — Análise qualitativa (`qualitativa.md`, em paralelo à coleta)

Tudo que não depende de dados OpenBB: modelo de negócio em profundidade, setor e dinâmica
competitiva, vantagens competitivas e sua DURAÇÃO (insumo direto de n2/F), management e capital
allocation, riscos (incl. judiciais/regulatórios), pontos do grill-me. Roteiro:
`references/qualitativa-e-financeira.md`. Análise que precisar de dado ainda não entregue: pular
e voltar. `notas.md` atualizado continuamente.

## F6 — Análise financeira histórica (`financeira.md`)

Com `dados/` completo: decomposição do ROE (DuPont), margens e giro, alavancagem e cobertura,
conversão de caixa e FCFE pelas relações do manual (§3 — nunca fórmula própria), EPS e CAGR,
payout e recompras, P/L histórico. OBRIGATÓRIO conectar o qualitativo aos números (cada tendência
ganha explicação causal; cada tese qualitativa é testada nos números) e gerar insights NOVOS a
partir dos dados. Janela curta de série: usar a janela máxima disponível e declarar o corte
(alimenta `nota_janela` dos gráficos e a seção de Limitações). Iteração livre com o DM
(`dados/pedidos.md`) para séries adicionais.

## F7 — Calibração (`calibracao.md`)

Ordem canônica: `Normalize → ROE1 → g1 → n1 → ROE2 → g2 → n2 → F → Ke1/Ke2 → GDE/NDE → Kd_F2/t
→ g_T`. Normalização de NI0 e book (ciclo, one-offs, leases, buybacks, caixa distribuível vs
exigido — manual §4.1). Cenários bear/base/bull internamente coerentes (menos/mais se o caso
pedir; pesos opcionais; falha discreta material → protocolo de distress §6.5, NUNCA escondida no
Ke). Por input × cenário: justificativa + evidência (fonte nomeada). Quando a série histórica for
curta (janela OpenBB), DECLARAR na justificativa de ROE2/g2/n2 que a âncora histórica está
enfraquecida e qual evidência compensa. NUNCA calibrar contra o preço de mercado.

## F8 — Engine

Sequência inegociável:
1. Montar `case.json` (schema no SKILL.md do er-motor-k3; `market.price_date` e
   `market.price_source` preenchidos; preço com mais de 24h úteis está VENCIDO — pedir recoleta).
2. `python skills/er-motor-k3/scripts/run_regressions.py` → SUITE PASS obrigatório.
   (O CLI congelado do engine NÃO cria diretório: criar `analises/<TICKER>/saida/` antes do
   `--out`. O `build_report.py` cria sozinho.)
3. `value` → ler `validation` e `sanity_notes`; resolver INVALID (corrigir, nunca forçar);
   justificar cada REVIEW em `calibracao.md`.
4. Sensibilidades 1D/2D nos drivers que REALMENTE importam para esta empresa (prioridade quando
   aplicável: ROE2, g2, Ke, n2/CAP, F, estrutura) — via `sens`; os presets 2D entram no
   `analise.json`.
5. CONGELAR a calibração (registrar em notas.md).
6. `implied` por premissa principal (market-implied) — diagnóstico rotulado.
7. Se hurdle informado em F2: rodada com `label_mode: "hurdle"`.

## F9 — Checkpoint de premissas (só se optado em F2)

Apresentar: tabela consolidada 16 inputs × cenários; justificativa resumida por input; leitura
market-implied — se alguma premissa divergir muito do que o preço embute (caso típico: Ke),
dizer EXPLICITAMENTE o que o preço embute naquela premissa, mantidas as demais constantes.
Ajustes → re-calibrar → re-rodar F8 → repetir até aprovação. Sem ajustes: seguir.

## F10 — Relatório HTML

Preparar `analise.json` (contrato: SKILL.md do er-relatorio-html — placeholders para TODO número
de valuation em prosa; charts com fonte/derivação/overlays/nota de janela; Positives/Negatives;
limitações a partir do ledger). Rodar:
`python skills/er-relatorio-html/build_report.py analises/<TICKER>` (+ `--modo valuation` no modo
reduzido) e `python skills/er-relatorio-html/checar_relatorio.py analises/<TICKER>` → exit 0
obrigatório. Abrir o HTML e confirmar banner VERDE antes de entregar o arquivo ao usuário.

## F11 — Fechamento e memória

`python scripts/memoria.py analises/<TICKER> --sintese <arquivo> --licoes <arquivo>` →
`analises/_memoria/<TICKER>.md`. Âncoras numéricas extraídas por código de
`case.json`/`results.json` (nunca à mão); síntese/decisão curta; 2–6 lições reutilizáveis
(teste da lição: "isso muda como analiso OUTRA empresa, ou este ticker no futuro?"). Lição
transversal ao processo vira SUGESTÃO explícita de atualização do plugin, decidida pelo humano —
nenhuma skill se auto-edita. Memória fecha SEMPRE, nos dois modos.
