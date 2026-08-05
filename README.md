# equity-research-fleet v3

Plugin de equity research centrado no Analista: **2 agentes, 4 skills, matemática 100% em motor
determinístico congelado, dados financeiros exclusivamente via OpenBB e entrega em HTML
interativo de 2 abas**. Desenho completo (fonte de verdade):
[`docs/desenho-workflow-equity-research-fleet-v3.md`](docs/desenho-workflow-equity-research-fleet-v3.md).

## Arquitetura

- **Analista** — o loop principal (não é subagente). Coordena o processo, pesquisa o
  qualitativo, reconstrói o financeiro histórico, calibra os 16 inputs, opera o engine e assina
  o conteúdo. Workflow: skill [`er-analise`](skills/er-analise/SKILL.md) (fases F0–F11, modo
  "somente valuation", P2 por materialidade, memória durável).
- **Data Manager** — único subagente ([`agents/data-manager.md`](agents/data-manager.md)), dono
  exclusivo das chamadas OpenBB (exceção única: snapshot de perfil/preço do briefing, F1).
  Doutrina: skill [`er-dados-openbb`](skills/er-dados-openbb/SKILL.md) (mapa real de endpoints,
  ledger de proveniência, gaps MATERIAL/NÃO-MATERIAL, validade de preço >24h útil).
- **Motor** — skill [`er-motor-k3`](skills/er-motor-k3/SKILL.md): cópia congelada da metodologia
  Justified P/E V2.2.1 (manual de calibração, engine, validador de contrato de inputs e suíte
  canônica de regressão). Sem workflow standalone — quem orquestra é o fleet.
- **Relatório** — skill [`er-relatorio-html`](skills/er-relatorio-html/SKILL.md):
  `build_report.py` (builder determinístico, único caminho de emissão) + template de 2 abas
  (Valuation interativo com recálculo ao vivo · Análise com Positives/Negatives, gráficos
  interativos e calibração) + `checar_relatorio.py` (QC pós-emissão). uPlot 1.6.27 (MIT)
  vendorizado; arquivo final autocontido, zero rede.

QC por código, não por agente: **SUITE PASS** da regressão canônica antes de qualquer entrega,
**banner de paridade Python↔JS verde** no HTML (self-test no load; pré-verificação sob node no
build, com recusa em divergência) e **`checar_relatorio.py` exit 0** (estrutura, log de
consistência número↔chave, paridade, autocontenção, gráficos, números órfãos).

## Fluxo (modo completo)

Intake → briefing (1 página) → grill-me (modo → hurdle, **sem default** → validação de
premissas → perguntas específicas) → estudo do método + arquétipo → despacho do DM em background
→ qualitativa ∥ coleta → financeira histórica → calibração dos 16 inputs × cenários → engine
(SUITE PASS → value → sensibilidades → congelar → market-implied → hurdle rotulada) → checkpoint
opcional → HTML de 2 abas → memória durável por código. Detalhe fase a fase em
[`skills/er-analise/references/fases.md`](skills/er-analise/references/fases.md).

## Workspace por análise

```
analises/<TICKER>/
├── 00_briefing.md · 01_grill_me.md · notas.md
├── dados/            # domínio do Data Manager (categoria.json + ledger.md + pedidos.md)
├── qualitativa.md · financeira.md · calibracao.md
├── case.json         # input do engine
├── analise.json      # conteúdo da aba 2 (placeholders {{r:...}}/{{c:...}}/{{d:...}})
├── saida/results.json
└── relatorio/relatorio_<TICKER>.html
analises/_memoria/<TICKER>.md   # nota durável, gerada por scripts/memoria.py
```

## Metodologia — versão e disciplina de sincronização

O motor é **cópia byte a byte** da skill de usuário `justified-pe-valuation` (que permanece
INTOCADA e continua sendo o caminho para valuation standalone fora do fleet):

- Metodologia: **Justified P/E V2.2.1 (congelada)** —
  `formula_version: K3-vF19-2026-08-03 / manual-v2.2.1`
- sha256 da fórmula-fonte (stored, sem newline final):
  `ed5163103b73a226d47692ad6a9595416ce38ea2e2e9ea0d217072d4243b5420`
- Íntegra da cópia (origem, data, contagem observada da suíte e sha256 por arquivo, incluindo o
  espelho `k3_engine.js` e o uPlot vendorizado):
  [`skills/er-motor-k3/manifest_copia.json`](skills/er-motor-k3/manifest_copia.json)

**Disciplina de sincronização:** qualquer evolução futura da metodologia precisa ser replicada
MANUALMENTE nos dois lugares (skill standalone e esta cópia), por decisão humana. O teste
`tests/test_motor_k3.py` compara os arquivos copiados com o manifest a cada execução — qualquer
alteração local quebra a suíte. Nenhuma matemática de valuation é escrita à mão em prosa, Python
novo ou JS novo (o único motor JS é o `k3_engine.js` copiado e verificado por paridade).

## Regras invioláveis (Seção 9 do desenho)

Metodologia congelada · regression gate + paridade + checar antes de qualquer entrega · dados
financeiros só OpenBB via DM · gaps MATERIAL perguntam, NÃO-MATERIAL degradam com nota (janela
curta de fundamentals inclusa — gráficos usam a "janela máxima disponível" declarada no próprio
gráfico) · hurdle sem default e sempre rotulada · market-implied nunca recalibra · grill-me é
evidência, não fato · `notas.md` por fase · memória por código · sem guardrails, sem auditor,
sem portfolio fit, sem PDF (carteira → skill `portfolio-construction`, fora do fleet).

## Como rodar os testes

```bash
python -m pytest tests/ -q
```

```bash
python skills/er-motor-k3/scripts/run_regressions.py
```

- Dependências de teste: Python 3.12+, `pytest`, `pyyaml`. O engine e os builders são stdlib pura.
- **Node.js** (opcional, recomendado): com `node` no PATH, o teste de paridade Python↔JS roda de
  verdade e o `build_report.py` ganha o gate de recusa por divergência no build (sem node, a
  paridade é verificada pelo self-test do browser no load — banner verde continua obrigatório).
  No CI (ubuntu + setup-node) a paridade roda sempre.
- Windows: os arquivos congelados são protegidos de conversão de EOL por `.gitattributes`.

## CI e release

`ci.yml`: pytest (inclui SUITE PASS, paridade e builders) + sanity do manifesto, em todo push/PR.
`release.yml` (tag `v*`): valida tag == versão do `plugin.json`, empacota ZIP e publica GitHub
Release com corpo opcional de `docs/releases/<tag>.md`.
