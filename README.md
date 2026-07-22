# equity-research-fleet

Plugin Claude que empacota o fleet de equity research buy-side de Antonio: dossiê,
valuation determinístico, auditoria e relatório institucional.

## v2.1.0 — upgrade metodológico (FASE B; engine v3.2.0, ADITIVO)

Metodologia adjudicada contra quatro modelos de referência (FASE A + verificação B0) e
exercitada no caso TFCO4 (`docs/impacto_TFCO4.md`). Tudo com GATING POR PRESENÇA — inputs
antigos produzem as chaves antigas idênticas (exceto `engine.{versao,gerado_em}`):

- **Âncora operacional** `ebit_justo` no motor único (margem×giro→ROIC, WACC como premissa,
  trailing; bridge de claims; paridade das âncoras como warning com nota) + série reformulada
  `fatos.reformulado` com invariantes na carga e gates de aplicabilidade (provisórios n=3).
- **R2–R5**: `central_neutro` + robustez conjunta; `validacao_multiplos.implicitos`;
  `ke_dossier` (duas rotas + prêmio de tamanho com critério + grade); cap_check v2.1
  (confiança da banda separada; ônus de sobrescrever para baixo).
- **Spread terminal**: `sensibilidade_phi` de primeira classe, exclusão mútua com `m_terminal`.
- **Classificação por natureza**: `classificacao.yaml` (schema + invariantes + congelamento no
  snapshot) e `fatos.norma_contabil` com trava de pacote de leasing — sem dicionário de rubricas.

## v2.0.0 — correções sistêmicas pós-feedback do caso HG (BREAKING)

Engine v3.0.0 e processo revisados; o contrato de inputs MUDA:

- **R1** Julgamento metodológico prévio (`metodo.yaml`, `schemas/metodo.schema.json`):
  aderência do P/L Justo ao modelo de negócio decidida ANTES da coleta completa e
  revisitada antes do valuation (`checar.py` bloqueia sem ele).
- **R2** `fatos.de`/`fatos.nde` (dívida bruta/PL e dívida líquida/PL) nunca mais são
  zerados por lacuna: engine recusa sem `premissas.excecao_de_nde` (motivo econômico +
  faixa alternativa) e calcula a sensibilidade da premissa substituta.
- **R3** `premissas.ke_hurdle` é OPCIONAL e exclusivamente informado pelo usuário
  (nenhum default de 12%); ausente, tudo degrada para a âncora econômica
  (`sinais.entrada = SEM_HURDLE`).
- **R4** Elasticidades com experimento declarado (`elasticidades.experimento`) e
  alertas de sinal contraintuitivo bloqueantes (`premissas.respostas_sinais`).
- **R5** `DIVERGE_MATERIAL` bloqueia a publicação sem `premissas.resolucao_divergencia`.
- **R6** Relatório em duas audiências: corpo institucional (linter em
  `checar.py --etapa relatorio`) + anexo técnico; matrizes de sensibilidade 3×3
  (`matrizes` no engine); gráficos com rótulos de dados.
- **R7** Auditoria proporcional: recomputo independente restrito a gatilhos.

## Estrutura

```
.claude-plugin/plugin.json   Manifesto do plugin
skills/
  er-valuation/               Motor determinístico de valuation (P/L Justo, cap_check, golden tests)
    SKILL.md
    engine.py
    cap_check.py
    inputs_exemplo_vrsk.yaml
    tests/test_golden_vrsk.py
  er-relatorio/                Composição e renderização do relatório final (PDF institucional)
    SKILL.md
    compor.py
    checar.py
    render_pdf.py
    template.css
docs/fontes/                  Mandatos originais (Analista, Coordenador, Modelador, PM, Auditor, Redator)
```

As duas skills (`er-valuation` e `er-relatorio`) são cópias byte-a-byte das versões
originais (`valuation-engine` e `research-report`), apenas com o campo `name` do
frontmatter do `SKILL.md` renomeado para casar com o novo namespace do plugin.
Descriptions e corpo não foram alterados.

## Como rodar os testes

Requer Python 3 com `pyyaml` instalado (`pip install pyyaml`) — o `engine.py` usa
`pyyaml` para ler inputs em `.yaml` (com fallback documentado para `.json` caso a
biblioteca não esteja disponível).

Da raiz do repositório:

```bash
python skills/er-valuation/tests/test_golden_vrsk.py
```

O teste resolve o `engine.py` e o `inputs_exemplo_vrsk.yaml` por caminho relativo ao
próprio arquivo de teste (via `__file__`), portanto funciona a partir da raiz do repo
sem depender do diretório de trabalho.

**Não use `pytest` para rodar o golden test.** `test_golden_vrsk.py` é um script
standalone (chama `sys.exit(...)` no nível de módulo), não um módulo de testes no
estilo pytest — coletar esse arquivo via pytest quebra a coleta com
`INTERNALERROR` (o `SystemExit` escapa do import). A execução correta é sempre
direta:

```bash
python skills/er-valuation/tests/test_golden_vrsk.py
```

Via pytest (usa `pyproject.toml`, `testpaths = ["tests"]`): `tests/` contém a
suíte pytest real (196 testes, fora de `skills/`) cobrindo pipeline, schemas,
delta, memória, skills de domínio e a regressão de fixture FNV.

```bash
python -m pytest tests/ -q
```

O golden do valuation-engine e o selftest do `cap_check` continuam fora do
pytest (scripts standalone, ver seção acima):

```bash
python skills/er-valuation/tests/test_golden_vrsk.py
python skills/er-valuation/cap_check.py --selftest
```

No Windows, se `python` não estiver disponível via PATH, tente `py -3`.
