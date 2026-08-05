import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

def test_plugin_json_v3():
    p = json.loads((RAIZ / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    assert p["version"] == "3.0.0"
    assert p["name"] == "equity-research-fleet"
    assert p["description"].strip()

def test_marketplace_json_v3():
    m = json.loads((RAIZ / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
    assert m["metadata"]["version"] == "3.0.0"
    assert m["plugins"][0]["version"] == "3.0.0"

def test_v2_removida():
    for morto in ["schemas", "scripts/pipeline.py", "scripts/validar.py", "scripts/snapshot.py",
                  "scripts/delta.py", "skills/er-processo", "skills/er-valuation",
                  "skills/er-relatorio", "skills/er-auditoria", "skills/er-portfolio",
                  "skills/er-guardrails", "skills/er-dossie", "skills/er-dados",
                  "skills/er-memoria", "agents/analista.md", "agents/modelador.md",
                  "agents/auditor.md", "agents/portfolio-manager.md", "agents/redator.md"]:
        assert not (RAIZ / morto).exists(), f"resto v2: {morto}"
