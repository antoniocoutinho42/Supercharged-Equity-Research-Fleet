"""Paridade Python <-> JS do espelho k3_engine.js (um dos 3 mecanismos de QC da v3).

Usa o CLI node embutido no proprio espelho copiado (`node k3_engine.js --selftest`,
vetores gerados por valuation_engine.js_parity_vectors()), sem wrapper e sem tocar
no arquivo congelado. Sem node no PATH o teste pula com aviso (no CI ubuntu ha node).
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "skills" / "er-motor-k3" / "scripts"))


def test_paridade_python_js():
    node = shutil.which("node")
    if not node:
        pytest.skip("node indisponivel nesta maquina (roda no CI)")
    import valuation_engine as ve
    js = RAIZ / "skills" / "er-relatorio-html" / "assets" / "k3_engine.js"
    vetores = ve.js_parity_vectors()
    assert vetores, "js_parity_vectors() vazio"
    r = subprocess.run([node, str(js), "--selftest"], input=json.dumps(vetores),
                       capture_output=True, text=True, encoding="utf-8", timeout=60)
    assert r.returncode == 0, r.stderr
    res = json.loads(r.stdout)
    assert res["pass"], res.get("failures")
    assert res["checks"] > 0
