import hashlib, json, subprocess, sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
MK3 = RAIZ / "skills" / "er-motor-k3"

def _sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def test_manifest_congelado():
    man = json.loads((MK3 / "manifest_copia.json").read_text(encoding="utf-8"))
    assert man["formula_version"] == "K3-vF19-2026-08-03 / manual-v2.2.1"
    assert man["source_formula_sha256_stored"] == "ed5163103b73a226d47692ad6a9595416ce38ea2e2e9ea0d217072d4243b5420"
    for rel, sha in man["arquivos"].items():
        assert _sha(MK3 / rel) == sha, f"arquivo copiado alterado: {rel}"

def test_regressao_suite_pass():
    r = subprocess.run([sys.executable, str(MK3 / "scripts" / "run_regressions.py")],
                       capture_output=True, text=True, encoding="utf-8", timeout=300)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "SUITE PASS" in r.stdout

def test_skill_md_sem_workflow_standalone():
    texto = (MK3 / "SKILL.md").read_text(encoding="utf-8")
    assert texto.startswith("---")
    for proibido in ["Markdown ou", "grill me", "grill-me", "Mandatory opening interaction"]:
        assert proibido not in texto, f"workflow standalone vazou: {proibido}"
    for obrigatorio in ["16", "run_regressions.py", "SUITE PASS", "case.json", "arquétipo"]:
        assert obrigatorio in texto
