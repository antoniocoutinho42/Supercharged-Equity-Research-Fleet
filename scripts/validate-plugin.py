#!/usr/bin/env python3
from pathlib import Path
import json, subprocess, sys

ROOT = Path(__file__).resolve().parents[1]
required = [
    '.claude-plugin/plugin.json', '.claude-plugin/marketplace.json',
    'commands/analisar.md', 'commands/leitura-de-preco.md', 'commands/revisar-relatorio.md',
    'skills/er-analise/SKILL.md', 'skills/multiplos-justos/SKILL.md', 'skills/relatorio-html/SKILL.md',
    'agents/pesquisador.md', 'agents/operador-mj.md', 'agents/auditor-mj.md',
    'agents/verificador.md', 'agents/revisor-comite.md',
    'skills/multiplos-justos/scripts/justos.py', 'scripts/validate-report.py',
]
missing=[p for p in required if not (ROOT/p).is_file()]
if missing:
    raise SystemExit('Missing required files: ' + ', '.join(missing))

plugin=json.loads((ROOT/'.claude-plugin/plugin.json').read_text(encoding='utf-8'))
market=json.loads((ROOT/'.claude-plugin/marketplace.json').read_text(encoding='utf-8'))
version=plugin['version']
if market.get('metadata',{}).get('version') != version:
    raise SystemExit('Version mismatch: plugin vs marketplace metadata')
entries=[p for p in market.get('plugins',[]) if p.get('name')==plugin.get('name')]
if not entries or entries[0].get('version') != version:
    raise SystemExit('Version mismatch: plugin vs marketplace entry')

# Architectural guardrails: these are deterministic text checks, not intellectual QA.
er=(ROOT/'skills/er-analise/SKILL.md').read_text(encoding='utf-8').lower()
if 'não pode ser substituída silenciosamente por comparáveis ou dcf genérico' not in er:
    raise SystemExit('ER skill lost mandatory MJ guardrail')
route=(ROOT/'skills/multiplos-justos/references/core/routes.md').read_text(encoding='utf-8').lower()
for token in ['finite-life / reserve nav','holding / sotp','multi-segment','transition / releveraging']:
    if token not in route:
        raise SystemExit(f'Missing MJ internal route: {token}')

subprocess.run([sys.executable, str(ROOT/'skills/multiplos-justos/scripts/justos.py'), 'selftest'], check=True, cwd=ROOT)
print(f'OK equity-research-fleet {version}: structure, manifests, MJ guardrails and justos.py selftest')
