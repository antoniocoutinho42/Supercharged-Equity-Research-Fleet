import json
import shutil
import subprocess
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
ESPELHO = RAIZ / "skills" / "er-valuation" / "assets" / "motor_espelho.js"
FIXTURE = RAIZ / "tests" / "fixtures" / "vetores_paridade.json"

SEM_NODE = shutil.which("node") is None
RAZAO = "node ausente do PATH — a paridade roda sempre no CI (setup-node)"


def test_espelho_nao_tem_dependencia_externa():
    """Zero npm: o espelho sera embutido num HTML autocontido, sem rede.

    Casa por REGEX, nao por substring: comentarios em portugues contem
    "importante", que dispara um `"import " in texto` ingenuo, e o unico
    require legitimo e o de "fs" na secao do CLI.
    """
    import re
    texto = ESPELHO.read_text(encoding="utf-8")
    nucleo = texto.split("// CLI")[0]
    assert not re.search(r"^\s*import\s", nucleo, re.M), "import ES6 no nucleo"
    requires = re.findall(r"""require\(\s*['"]([^'"]+)['"]\s*\)""", texto)
    assert set(requires) <= {"fs"}, f"dependencia alem de fs: {sorted(set(requires))}"
    assert not re.search(r"require\(", nucleo), "require no nucleo — so na secao do CLI"


def test_espelho_nao_e_transcricao_de_outra_fonte():
    """O espelho cita o arquivo e as linhas do motor que ele reproduz."""
    texto = ESPELHO.read_text(encoding="utf-8")
    assert "vendor/multiplos-justos/scripts/justos.py" in texto


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_cli_do_espelho_devolve_um_resultado_por_vetor():
    r = subprocess.run(["node", str(ESPELHO), str(FIXTURE)],
                       capture_output=True, text=True, encoding="utf-8", timeout=120)
    assert r.returncode == 0, r.stdout + r.stderr
    resultados = json.loads(r.stdout)
    vetores = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert len(resultados) == len(vetores)
    assert [x["id"] for x in resultados] == [v["id"] for v in vetores]


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_espelho_emite_null_para_nao_finito():
    r = subprocess.run(["node", str(ESPELHO), str(FIXTURE)],
                       capture_output=True, text=True, encoding="utf-8", timeout=120)
    resultados = json.loads(r.stdout)
    assert any(x["valor"] is None for x in resultados), "nenhum null — os guardas nao rodaram"
    assert all(x["valor"] is None or isinstance(x["valor"], (int, float))
               for x in resultados)


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_ponte_para_preco_no_espelho():
    """A ponte tambem vive no espelho: o laboratorio recalcula preco/acao ao vivo."""
    script = (
        "const m = require(%s);"
        "const r = m.ponteParaPreco({ev: 6690.59, ndEfetivo: 500.0, acoes: 100.0});"
        "console.log(JSON.stringify(r));"
    ) % json.dumps(str(ESPELHO))
    r = subprocess.run(["node", "-e", script],
                       capture_output=True, text=True, encoding="utf-8", timeout=60)
    assert r.returncode == 0, r.stdout + r.stderr
    d = json.loads(r.stdout)
    assert d["equity"] == pytest.approx(6190.59, abs=1e-9)
    assert d["precoAcao"] == pytest.approx(61.9059, abs=1e-9)
