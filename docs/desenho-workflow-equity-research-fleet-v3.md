# Equity Research Fleet v3.0.0 — Desenho do Workflow

Data: 2026-08-05 · Autor do desenho: Antonio (rascunho) + reescrita estruturada pós grill-me
Base factual: plugin `equity-research-fleet` v2.2.0 e skill `justified-pe-valuation` (V2.2.1), lidos na íntegra.
Uso: este documento é a fonte para o prompt de kickoff no Claude Code (esqueleto na Seção 12).

---

## 0. Objetivo

Reconstruir o fleet como um processo de research **centrado no Analista**, com apenas dois agentes, sem gates burocráticos, com dados financeiros exclusivamente via OpenBB e entrega em **HTML interativo de duas abas** (engine simulável + análise qualitativa/financeira). A matemática de valuation é 100% do motor determinístico K3 V2.2.1 (Justified P/E, 2 fases + fade linear de ROE até Ke2), copiado para dentro do plugin. O usuário participa em três momentos: grill-me inicial, gaps materiais de dados e (opcionalmente) validação de premissas antes da entrega.

## 1. Princípios da v3

1. **Analista no centro.** Um único fio condutor entende a empresa de ponta a ponta: briefing, qualitativo, financeiro, calibração, interpretação. Sem fronteiras artificiais entre "quem julga" e "quem modela".
2. **Dois agentes, zero cerimônia.** Analista (loop principal, também coordenador) + Data Manager (subagente de coleta). Sem guardrails eliminatórios, sem auditor, sem PM, sem redator, sem cadeia de gates com estado formal.
3. **Julgamento humano no lugar certo.** O que a v1 resolvia com burocracia, a v3 resolve com interação: grill-me inicial, pergunta em gap material, checkpoint opcional de premissas.
4. **Matemática só no engine.** Nenhum número de valuation nasce em prosa ou em JS escrito à mão. K3 V2.2.1 congelado, regression gate obrigatório, espelho JS verificado por paridade.
5. **Sempre olhando para a frente.** Toda análise converge para duas perguntas: como a empresa será no FUTURO e como isso se traduz em números — os 16 inputs canônicos.
6. **QC por código, não por agente.** Regression suite, parity banner do HTML e checagem número-citado ↔ `results.json` substituem a auditoria como rede de segurança default.
7. **Memória de trabalho e memória durável.** O Analista anota enquanto trabalha (`notas.md`) e fecha cada análise com nota durável por ticker gerada por código + lições.

## 2. Componentes

### 2.1 Agentes (2)

**Analista (loop principal — não é subagente).**
Papéis: coordenador do processo, pesquisador qualitativo, analista financeiro, calibrador dos 16 inputs, operador do engine, autor do conteúdo do relatório. Interage com o usuário em todos os checkpoints. Mantém `notas.md` como memória de trabalho contínua (bullet points datados por fase) para não se perder no volume de informação.

**Data Manager (`agents/data-manager.md` — subagente).**
Único dono das chamadas OpenBB (exceção única: snapshot de perfil/preço do briefing, F1). Recebe briefing + resultado do grill-me + lista de dados; valida cobertura, coleta, salva tudo em `dados/` com ledger de proveniência (endpoint, parâmetros, data da chamada, gaps). Proativo: pode sugerir dados adicionais úteis que o Analista não pediu (ex.: série de commodity relevante, dados de pares, estimates disponíveis). Reporta gaps classificados como MATERIAL (bloqueia input crítico do valuation) ou NÃO-MATERIAL (degrada gráfico/contexto).

### 2.2 Skills do plugin v3 (4)

| Skill | Papel | Conteúdo |
|---|---|---|
| `er-analise` | Workflow master (usada pelo Analista) | Trigger, os dois modos, fases F0–F11, checkpoints com usuário, regras duras, P2/pontual, fechamento com memória |
| `er-dados-openbb` | Doutrina de coleta (usada pelo Data Manager) | Categorias de dados, mapeamento dos endpoints OpenBB por categoria, formato dos arquivos em `dados/`, ledger de proveniência, validade de preço (>24h útil = vencido), classificação de gaps |
| `er-motor-k3` | Motor + manuais (cópia congelada da metodologia) | Manual V2.2.1 completo (relações financeiras e derivações — FCFE, funding, ponte; ordem de calibração §4; política de Ke §6; **arquétipos/perfis de empresa** §7 — cíclicas, asset-light, early stage etc.; invariantes §11), `valuation_engine.py`, `run_regressions.py`, `input_validator.py`, contrato de inputs. **Sem workflow standalone** (sem pergunta de formato, sem grill-me próprio, sem etapas de pesquisa): isso é papel do fleet — é assim que o overlap morre |
| `er-relatorio-html` | Builder novo do relatório (determinístico) | Template próprio de 2 abas, `k3_engine.js` embutido (espelho verificado), gráficos interativos com dados embutidos, parity self-test, `checar_relatorio.py` |

Memória durável não vira skill separada: é uma seção de `er-analise` + `scripts/memoria.py` adaptado.

### 2.3 Skill standalone `justified-pe-valuation`

**Fica intocada.** Continua sendo o caminho para valuation standalone fora do fleet, com o workflow próprio dela. O plugin trabalha com a própria cópia (er-motor-k3 + er-relatorio-html). Disciplina de sincronização: a cópia registra no README do plugin a versão/hash da metodologia copiada (V2.2.1 + sha256 da fórmula-fonte, já presente no JSON de regressão); qualquer evolução futura da metodologia precisa ser replicada manualmente nos dois lugares, por decisão humana.

### 2.4 Conector

OpenBB MCP (`openbb-mcp`). Regra de alcance na Seção 9.

## 3. Repositório v3.0.0 (mesmo repo, major bump)

**Sai do carregamento (preservado só no histórico git):**

- Skills v2: `er-processo`, `er-guardrails`, `er-dossie`, `er-dados`, `er-valuation` (engine v3.3.0 + `cap_check.py` inclusos), `er-auditoria`, `er-portfolio`, `er-relatorio` (compor/checar/render_pdf), `er-memoria`.
- Agentes v2: `analista.md`, `modelador.md`, `auditor.md`, `portfolio-manager.md`, `redator.md`.
- `scripts/`: `pipeline.py`, `validar.py`, `snapshot.py`, `delta.py`, `memoria.py` (versão antiga).
- `schemas/` inteiro (estado, handoff, claims, metodo, decisao, classificacao, red_team_header).
- Testes v2 e fixtures atrelados ao engine antigo.
- Entrega em PDF (morre; a entrega é o HTML).

**Entra:**

- 4 skills novas (Seção 2.2) + `agents/data-manager.md`.
- Cópia dos assets K3 dentro de `er-motor-k3` (manual, engine, regressões, validator) e do `k3_engine.js` dentro de `er-relatorio-html`.
- `er-relatorio-html/build_report.py` (builder novo) + template 2 abas + `checar_relatorio.py`.
- `scripts/memoria.py` adaptado (extrai âncoras de `case.json`/`results.json`, sem `estado.yaml`).
- Testes: suíte de regressão K3 (cópia), teste de paridade Python↔JS, testes do builder (HTML gerado contém os números do `results.json`; recusa emitir com paridade divergente).
- `plugin.json` e `marketplace.json` com bump para 3.0.0; README reescrito do zero (o atual já estava desatualizado).

## 4. Workspace da análise

Namespace por análise: `analises/<TICKER>/` (relativo ao diretório de trabalho). Memória durável central: `analises/_memoria/<TICKER>.md`.

```
analises/<TICKER>/
├── 00_briefing.md          # briefing inicial da companhia (F1)
├── 01_grill_me.md          # perguntas, respostas do usuário, decisões (modo, hurdle, validação)
├── notas.md                # memória de trabalho do Analista, contínua, por fase
├── dados/                  # domínio do Data Manager
│   ├── *.json / *.csv      # um arquivo por categoria coletada
│   ├── ledger.md           # proveniência: endpoint, parâmetros, data, gaps (MATERIAL / NÃO-MATERIAL)
│   └── pedidos.md          # log de pedidos do Analista e respostas do DM
├── qualitativa.md          # análise qualitativa (F5)
├── financeira.md           # análise financeira histórica (F6)
├── calibracao.md           # 16 inputs × cenários, justificativa + evidência por input (F7)
├── case.json               # input do engine (cenários, escala, mercado)
├── saida/
│   └── results.json        # outputs do engine (+ sensibilidades, implied, hurdle se houver)
├── relatorio/
│   └── relatorio_<TICKER>.html
```

## 5. Fluxo — modo ANÁLISE COMPLETA

**F0. Intake.** Usuário informa a empresa. Analista desambigua ticker/listagem/moeda; consulta `analises/_memoria/` — se o ticker já foi analisado, propõe P2 (Seção 7) em vez de análise nova. Cria o workspace.

**F1. Briefing inicial.** Analista monta `00_briefing.md`: o que a empresa é, segmentos e modelo de receita, posição de mercado, estrutura societária e listagem, snapshot de perfil/preço/market cap (única chamada OpenBB permitida ao Analista; o resto é do DM). Fontes qualitativas livres (web, RI). Curto: 1 página, o suficiente para sustentar um grill-me inteligente.

**F2. Grill-me com o usuário.** Com base no briefing, o Analista pergunta, nesta ordem:

1. **Modo**: análise única e profunda, ou somente valuation? (pergunta expressa, sempre).
2. **Hurdle**: retorno mínimo exigido? Opcional, **nunca com default** (12% não é assumido). Se informado, o engine roda também a rodada hurdle-conditioned (`label_mode: "hurdle"`) e o HTML a exibe rotulada.
3. **Validação de premissas**: quer validar os inputs do valuation antes da entrega? (define se F9 acontece).
4. **Perguntas específicas da empresa**, geradas do briefing: pontos que o usuário quer aprofundar; conhecimento prévio dele (contábil, setorial, judicial, societário, específico); divergências dele vs consenso; eventos próximos relevantes.

Respostas são registradas em `01_grill_me.md` e tratadas como **evidência a verificar, nunca fato**.

**F3. Estudo do método e do perfil.** Analista lê `er-motor-k3` (manual: relações financeiras e como os inputs derivam uns dos outros; ordem de calibração; política de Ke; arquétipos §7) e classifica o perfil da empresa (cíclica, asset-light, intensiva em capital, early stage, financeira etc.). Disso derivam: (a) a lista de dados a pedir ao DM; (b) os riscos de calibração típicos do perfil; (c) os gráficos específicos do negócio que a aba 2 vai precisar (ex.: preço de commodity, margens, asset turnover).

**F4. Despacho do Data Manager (assíncrono).** Brief curto com ponteiros para `00_briefing.md` e `01_grill_me.md` + lista de dados por categoria: demonstrações 10 anos (DRE, balanço, fluxo de caixa), séries de preço e múltiplos, EPS histórico, dividendos/splits/buybacks, estimates e consenso, ownership/insiders, segmentos/geografia, séries setoriais/commodities do perfil, pares para contexto. O DM valida cobertura, coleta, salva em `dados/`, escreve `ledger.md`, sugere adições e classifica gaps. **Gap MATERIAL → o Analista pergunta ao usuário (que pode fornecer o dado manualmente); NÃO-MATERIAL → nota de limitação e segue.**

**F5. Análise qualitativa (em paralelo à coleta).** Enquanto o DM coleta, o Analista executa tudo que não depende de dados OpenBB: modelo de negócio em profundidade, setor e dinâmica competitiva, vantagens competitivas e sua duração, management e capital allocation, riscos (incl. judiciais/regulatórios), pontos levantados no grill-me. Análise que precisar de dado ainda não entregue: pula e volta depois. Saída: `qualitativa.md`. `notas.md` atualizado continuamente.

**F6. Análise financeira histórica.** Com `dados/` completo: decomposição do ROE (DuPont), margens e giro, alavancagem e cobertura, conversão de caixa e FCFE pelas relações do manual, EPS e CAGR, payout e recompras, P/L histórico. Obrigatório **conectar o qualitativo aos números** (cada tendência numérica ganha explicação causal, cada tese qualitativa é testada nos números) e **gerar insights novos** a partir dos dados, não só confirmar o qualitativo. Iteração livre com o DM para dados adicionais (setoriais, estimates, pares). Norte permanente: como a empresa será no futuro e como isso vira número. Saída: `financeira.md`.

**F7. Calibração dos 16 inputs.** Ordem canônica do manual (Normalize → ROE1 → g1 → n1 → ROE2 → g2 → n2 → F → Ke1/Ke2 → GDE/NDE → Kd_F2/t → g_T). Normalização de NI0 e book (ciclo, one-offs, leases, buybacks, caixa distribuível vs exigido). Cenários bear/base/bull internamente coerentes (menos/mais cenários se o caso pedir; pesos opcionais; falha discreta material → protocolo de distress do manual, nunca escondida no Ke). Justificativa + evidência por input em `calibracao.md`. **Nunca calibrar contra o preço de mercado.**

**F8. Engine.** Montar `case.json` → rodar `run_regressions.py` (**SUITE PASS obrigatório**) → `value` → resolver INVALID / justificar REVIEW do contrato de inputs → sensibilidades 1D/2D nos drivers que realmente importam para ESTA empresa → congelar calibração → `implied` por premissa principal (market-implied) → rodada hurdle se hurdle informado em F2.

**F9. Checkpoint de premissas (só se o usuário optou em F2).** Analista apresenta: tabela consolidada dos 16 inputs × cenários, justificativa resumida por input, e a leitura market-implied — **se alguma premissa divergir muito do que o preço reflete (caso TFCO: o Ke), dizer explicitamente o que o preço embute naquela premissa, mantidas as demais constantes**. Usuário pede ajustes → re-calibra → re-roda engine (F8) → repete até aprovação. Sem ajustes: segue.

**F10. Relatório HTML.** `build_report.py` gera o HTML de duas abas (spec na Seção 8). Checagens obrigatórias antes da entrega: parity banner verde (Python ↔ JS) e `checar_relatorio.py` (todo número citado no HTML existe e bate com `results.json`; builder recusa emitir divergente). Entrega do arquivo ao usuário.

**F11. Fechamento e memória.** `scripts/memoria.py` gera/regenera a nota `analises/_memoria/<TICKER>.md`: âncoras numéricas e metadados extraídos por código de `case.json`/`results.json` (nunca à mão) + decisão/síntese + o Analista apensa 2–6 **lições reutilizáveis** (teste: "isso muda como analiso outra empresa, ou este ticker no futuro?"). Lição transversal ao processo vira sugestão explícita de atualização do plugin, decidida pelo humano.

## 6. Fluxo — modo SOMENTE VALUATION

Escolhido em F2 (pergunta 1). Calibração dirigida, sem dossiê:

- F0–F1 iguais (briefing curto).
- F2 grill-me **curto**: modo, hurdle, validação de premissas + 2–4 perguntas essenciais da empresa.
- F3 igual (método + perfil — indispensável para calibrar).
- F4 coleta **essencial**: o que os 16 inputs e a escala exigem (demonstrações, EPS, estrutura de capital, preço/ações diluídas) + P/L histórico para contexto mínimo.
- F5–F6 **substituídas** por pesquisa dirigida: só o necessário para calibrar cada input com justificativa e evidência (sem `qualitativa.md`/`financeira.md` completos; racional vai direto em `calibracao.md`).
- F7–F9 iguais (calibração, engine, checkpoint opcional).
- F10 HTML **reduzido**: aba do engine interativo + seção de premissas com justificativas (sem aba 2 completa, sem bateria de gráficos).
- F11 igual (memória fecha sempre).

## 7. P2, perguntas pontuais e memória

- **Leitura antes de tudo**: qualquer pedido sobre ticker já analisado começa pela nota de memória, depois `results.json`/workspace se precisar. Nunca reler o workspace inteiro por reflexo.
- **Pergunta pontual**: responder da memória + `results.json`, sem reabrir a análise, salvo necessidade real.
- **P2 (fato novo: release, guidance, evento)**: DM re-coleta dirigida só do que mudou → Analista re-calibra apenas os inputs afetados → engine re-roda → **decisão por materialidade, declarada pelo Analista**: fato material (muda sinal, valor ou tese de forma relevante) → regenera o HTML completo com seção destacada "O que mudou"; fato imaterial → nota curta apensada à memória do ticker, HTML preservado.
- Memória sempre regenerada por código ao fechar P2 material.

## 8. Relatório HTML — especificação

Arquivo único autocontido: CSS/JS inline, biblioteca de gráficos embutida, dados embutidos, zero dependência de rede.

**Cabeçalho comum às abas**: empresa, ticker, data da análise, preço usado (com data e fonte), síntese (fair value/ação base, upside/downside, faixa bear–bull, hurdle-conditioned se houver), badge de paridade Python↔JS.

**Aba 1 — Valuation interativo** (gerada pelo builder; matemática só no `k3_engine.js` verificado):

- Abas de cenário (bear/base/bull) com premissas editáveis, highlight original-vs-modificado e reset.
- Recálculo ao vivo do valuation completo a cada alteração.
- **Tabelas de sensibilidade que se ajustam ao vivo** às premissas correntes de cada cenário (1D ao vivo; 2D nos pares relevantes — ex.: ROE2×n2, Ke2×n2).
- Decomposição em blocos e bridge de valor.
- Tabela market-implied ("What Is the Market Pricing?") com interpretações.
- Comparação com o preço atual.
- Self-test de paridade no load; banner verde obrigatório.

**Aba 2 — Análise** (conteúdo do Analista, montagem pelo builder):

1. **Positives / Negatives** — seção inicial, dois blocos objetivos sobre a companhia.
2. Sumário executivo (tese, veredicto, principais divergências vs preço).
3. Perfil e modelo de negócio; análise qualitativa.
4. Análise financeira histórica (com os gráficos abaixo).
5. Calibração: tabela 16 inputs × cenários + racional e evidência por input.
6. Riscos e cenários alternativos.
7. What Is the Market Pricing? (narrativo).
8. Limitações de dados (gaps declarados do ledger) e fontes.

**Gráficos obrigatórios da aba 2** (interativos, dados embutidos; degradação com nota explícita quando a série for incompleta):

1. ROE 10 anos + indicadores financeiros relevantes do caso.
2. EPS histórico com CAGR.
3. Endividamento histórico.
4. P/L histórico.
5. Crescimento por ano (linhas) + CAGR acumulado por ano.
6. Gráficos específicos do negócio, a critério do Analista pelo perfil (commodities, margens, asset turnover etc.).

Função declarada dos gráficos 1–5: **âncora de realidade das premissas** (checar se o AI "não está viajando"). Proposta adicional (ver Seção 11): overlay das premissas correspondentes sobre cada gráfico — ROE1/ROE2 assumidos sobre o gráfico de ROE, g1/g2 sobre o de crescimento, P/L justo K3 sobre o P/L histórico.

## 9. Regras duras (invariantes da v3)

1. **Metodologia congelada** V2.2.1; o engine faz TODA a matemática; proibido recomputar/aproximar em prosa ou escrever matemática de valuation em JS à mão.
2. **Regression gate**: SUITE PASS antes de qualquer entrega; parity banner verde no HTML; builder recusa emitir divergente.
3. **Dados financeiros só OpenBB**, e só via Data Manager (exceção única: snapshot do briefing em F1). Pesquisa qualitativa (setor, concorrência, jurídico, management, notícias, leitura de RI/filings) é livre.
4. **Gaps**: MATERIAL → perguntar ao usuário; NÃO-MATERIAL → nota de limitação e segue. Nunca inventar, nunca silenciar.
5. **Hurdle nunca tem default**; ausência é declarada. Rodada hurdle sempre rotulada, nunca chamada de fair value.
6. **Market-implied nunca recalibra** o fair value; comparação com preço só depois da calibração congelada.
7. Respostas do usuário no grill-me são evidência a verificar, nunca fato.
8. `notas.md` atualizado a cada fase (memória de trabalho obrigatória do Analista).
9. Memória durável gerada por código; correção de número é na fonte + regenerar, nunca editar a nota à mão.
10. Sem guardrails eliminatórios, sem auditor, sem portfolio fit, sem PDF na v3 (carteira continua no domínio da skill `portfolio-construction`, fora do fleet).

## 10. Decisões registradas (grill-me de redesenho, 2026-08-05)

| # | Tema | Decisão |
|---|---|---|
| 1 | Motor | Só K3 V2.2.1; engine v3.3.0, cap_check, entry ladder e âncora dupla aposentados; hurdle via `label_mode`; razoabilidade por múltiplos vira análise do Analista com gráficos históricos |
| 2 | Herança v1 | Sobrevivem: memória durável + P2/delta e checks determinísticos. Morrem: guardrails, auditoria, portfolio fit, gates/estado, claims, PDF |
| 3 | Fontes | Financeiro só OpenBB; qualitativo livre (web/RI/filings) |
| 4 | Gaps OpenBB | Perguntar só se material; caso contrário nota e segue |
| 5 | Skill K3 | Copiar manuais/engine para dentro do plugin; `justified-pe-valuation` fica intocada (overlap morre porque a cópia não tem workflow standalone) |
| 6 | HTML | Builder novo no plugin, embutindo `k3_engine.js` |
| 7 | Profundidade | Dois modos perguntados expressamente no início: análise única e profunda, ou somente valuation |
| 8 | Repo | v3.0.0 no mesmo repositório; legado no histórico git |
| 9 | Modo valuation | Calibração dirigida, sem dossiê; HTML reduzido (aba engine + premissas) |
| 10 | Hurdle | Perguntar sempre no grill-me, opcional, sem default |
| 11 | Memória | Código extrai âncoras + Analista apensa lições; nota regenerável |
| 12 | P2 | Por materialidade: material regenera HTML com "O que mudou"; imaterial vira nota na memória |

## 11. Assunções declaradas (decididas por mim — revisar e vetar o que discordar)

1. **Idioma**: narrativa em PT-BR; nomes canônicos dos 16 inputs e rótulos técnicos do engine mantidos em inglês (convenção da skill).
2. **Cenários**: bear/base/bull por padrão; menos/mais quando fizer sentido econômico; pesos opcionais (regra atual do manual).
3. **Namespace**: `analises/<TICKER>/` relativo ao diretório de trabalho; memória em `analises/_memoria/`.
4. **Trigger da skill `er-analise`**: pedidos de análise/valuation de empresa com ticker + qualquer pergunta sobre ticker já analisado (P2/pontual via memória). Sourcing sem ticker e questões de carteira ficam fora (carteira → `portfolio-construction`).
5. **Paralelismo**: DM despachado em background no F4; Analista segue no F5 sem esperar; sincronização no F6.
6. **Biblioteca de gráficos**: uma lib JS leve embutida no HTML (sem CDN), escolhida na implementação; gráficos interativos (tooltip/zoom).
7. **Overlay de premissas nos gráficos históricos** (Seção 8): proposta minha, não estava no seu rascunho — corta na implementação se não quiser.
8. **Posição do Positives/Negatives**: topo da aba 2 (e síntese de uma linha no cabeçalho comum).
9. **Sem snapshot imutável de runs** (`runs/<hash>/` da v1 morre): `case.json` + `results.json` no workspace bastam, já que não há auditor; re-rodar é barato e o regression gate protege o motor.
10. **Comportamento não-atendido**: se o usuário não responder o grill-me em sessão desatendida, o Analista declara defaults (modo completo, sem hurdle, sem checkpoint de premissas) e segue.

## 12. Próximos passos + esqueleto do prompt para o Claude Code

Ordem de implementação sugerida (cada item termina verificável):

1. Limpeza do repo: remover skills/agents/scripts/schemas v2 do carregamento; bump 3.0.0 em `plugin.json` e `marketplace.json`.
2. `er-motor-k3`: copiar manual + engine + regressões + validator da skill standalone; escrever SKILL.md sem workflow (só manuais, arquétipos, uso do motor); rodar `run_regressions.py` → SUITE PASS.
3. `er-dados-openbb` + `agents/data-manager.md`: doutrina de coleta, mapeamento de endpoints, ledger, gaps.
4. `er-relatorio-html`: template 2 abas + `k3_engine.js` embutido + `build_report.py` + `checar_relatorio.py` + teste de paridade e teste do builder.
5. `er-analise`: workflow F0–F11, modo somente-valuation, P2/pontual, regras duras.
6. `scripts/memoria.py` adaptado + teste.
7. README novo + teste ponta a ponta com um ticker real (sugestão: um caso B3 para estressar cobertura OpenBB e a regra de gaps).

Esqueleto do prompt de kickoff (ajuste à vontade):

> Leia `desenho-workflow-equity-research-fleet-v3.md` (fonte de verdade deste trabalho) e o repositório atual do plugin `equity-research-fleet` (v2.2.0). Reescreva o plugin para a v3.0.0 exatamente como especificado: Seção 3 (o que sai/entra), Seções 2 e 4 (componentes e workspace), Seções 5–7 (fluxos), Seção 8 (spec do HTML), Seção 9 (invariantes). A skill de usuário `justified-pe-valuation` NÃO deve ser alterada; copie dela o manual, engine, regressões e `k3_engine.js` para dentro do plugin conforme a Seção 2.2. Trabalhe na ordem da Seção 12, um item por vez, com verificação por código ao fim de cada item (regression suite, paridade, builder). Ao terminar, rode um caso ponta a ponta e me apresente o HTML gerado.

---

*Documento gerado a partir do rascunho de brainstorming do Antonio + 12 decisões do grill-me. Qualquer conflito entre este documento e o rascunho original resolve-se por este documento.*
