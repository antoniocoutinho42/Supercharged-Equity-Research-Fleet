# equity-research-fleet

Plugin Claude que empacota o fleet de equity research buy-side de Antonio: dossiê,
valuation determinístico, auditoria e relatório institucional.

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
