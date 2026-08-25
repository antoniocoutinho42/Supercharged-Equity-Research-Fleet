import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
ESPELHO = RAIZ / "skills" / "er-valuation" / "assets" / "motor_espelho.js"
FIXTURE = RAIZ / "tests" / "fixtures" / "vetores_paridade.json"
sys.path.insert(0, str(RAIZ / "skills" / "er-valuation" / "scripts"))
from vetores_paridade import avaliar_python  # noqa: E402

SEM_NODE = shutil.which("node") is None
RAZAO = "node ausente do PATH — a paridade roda sempre no CI (setup-node)"
# NOTA (revisao final, FIX 7f): RAIZ/ESPELHO/FIXTURE/SEM_NODE/RAZAO sao a copia
# CANONICA — tests/test_paridade_js.py as importa daqui em vez de duplicar.


def test_espelho_nao_tem_dependencia_externa():
    """Zero npm: o espelho sera embutido num HTML autocontido, sem rede.

    Casa por REGEX, nao por substring: comentarios em portugues contem
    "importante", que dispara um `"import " in texto` ingenuo, e o unico
    require legitimo e o de "fs" na secao do CLI.
    """
    texto = ESPELHO.read_text(encoding="utf-8")
    nucleo = texto.split("// CLI")[0]
    assert not re.search(r"^\s*import\s", nucleo, re.M), "import ES6 no nucleo"
    requires = re.findall(r"""require\(\s*['"]([^'"]+)['"]\s*\)""", texto)
    assert set(requires) <= {"fs"}, f"dependencia alem de fs: {sorted(set(requires))}"
    assert not re.search(r"require\(", nucleo), "require no nucleo — so na secao do CLI"


def test_espelho_nao_e_transcricao_de_outra_fonte():
    """O espelho cita o arquivo E as faixas de linha do motor que ele reproduz —
    nao so que existe uma fonte, mas QUAIS linhas, para a citacao continuar
    verificavel por leitura (revisao final, FIX 7d: a versao anterior so
    checava o caminho do arquivo, nunca as faixas)."""
    texto = ESPELHO.read_text(encoding="utf-8")
    assert "vendor/multiplos-justos/scripts/justos.py" in texto
    assert re.search(r"\b32\s*[-–]\s*72\b", texto), \
        "faixa de linhas do ev_nopat/ev_ebitda (32-72) nao citada"
    assert re.search(r"\b214\s*[-–]\s*271\b", texto), \
        "faixa de linhas do pe (214-271) nao citada"


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
def test_espelho_carrega_em_contexto_vm_sem_module_require_process():
    """FIX 1 — Critico (revisao final). `module.exports = {...}` incondicional
    no topo do arquivo estourava `ReferenceError: module is not defined` num
    contexto sem `module` — exatamente o contexto de um `<script>` de browser
    (o banner de paridade e o laboratorio do item 5, os dois chamadores que a
    Decisao D2 do plano promete). A execucao morria antes de `avaliarVetores`
    ficar alcancavel: o segundo chamador nunca existiu de fato.

    Este teste carrega o FONTE do espelho — nao um `require()`, o proprio
    texto do arquivo — num `vm.createContext({})` vazio: sem `module`, sem
    `require`, sem `process`. Prova duas coisas: que o arquivo AVALIA sem
    estourar, e que a superficie publica (`globalThis.MotorEspelho`) fica
    alcancavel e devolve o MESMO valor que o motor Python para o mesmo vetor
    — nao so' "nao quebrou", mas "calcula certo" dentro desse contexto.
    """
    esperado = avaliar_python([{
        "id": 0, "fn": "ev_nopat",
        "args": {"g": 0.05, "roic": 0.12, "w": 0.10, "n": 10,
                 "tv": "gordon", "roic_tv": 0.10, "gp": 0.03},
    }])[0]
    script = (
        "const fs = require('fs');"
        "const vm = require('vm');"
        "const src = fs.readFileSync(%s, 'utf8');"
        "const ctx = vm.createContext({});"
        "vm.runInContext(src, ctx);"
        "const M = ctx.MotorEspelho;"
        "const ok = !!(M && typeof M.avaliarVetores === 'function' "
        "&& typeof M.evNopat === 'function' && typeof M.evEbitda === 'function' "
        "&& typeof M.pe === 'function' && typeof M.ponteParaPreco === 'function');"
        "const valor = ok ? M.evNopat({g:0.05, roic:0.12, w:0.10, n:10, "
        "tv:'gordon', roic_tv:0.10, gp:0.03}) : null;"
        "console.log(JSON.stringify({ok, valor}));"
    ) % json.dumps(str(ESPELHO))
    r = subprocess.run(["node", "-e", script],
                       capture_output=True, text=True, encoding="utf-8", timeout=60)
    assert r.returncode == 0, r.stdout + r.stderr
    d = json.loads(r.stdout)
    assert d["ok"], "superficie publica (globalThis.MotorEspelho) inalcancavel no contexto vm"
    assert d["valor"] == pytest.approx(esperado, rel=1e-9)


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_ponte_para_preco_reproduz_avaliar_py_rota_firm_nopat():
    """FIX 4 (revisao final). A ponte espelha SOMENTE
    `avaliar.py:precificar_firm`, ramo NOPAT (linhas 233-234 daquele
    arquivo): `equity = ev - nd_efetivo`; `preco_acao = equity / acoes`. O
    teste anterior comparava contra constantes calculadas a mao, sem lado
    Python nenhum. Este compara contra ESSA formula, numa mao-cheia de
    casos que inclui caixa liquido (`nd_efetivo` negativo) e uma ordem de
    grandeza de equity (~1e9)."""
    casos = [
        {"ev": 6690.59, "nd_efetivo": 500.0, "acoes": 100.0},
        {"ev": 1000.0, "nd_efetivo": 0.0, "acoes": 50.0},
        {"ev": 800.0, "nd_efetivo": -150.0, "acoes": 40.0},  # caixa liquido: nd < 0
        {"ev": 1234567890.12, "nd_efetivo": 987654321.0, "acoes": 1_000_000.0},
        {"ev": 250.75, "nd_efetivo": 30.25, "acoes": 12.5},
    ]
    script = (
        "const m = require(%s);"
        "const casos = %s;"
        "console.log(JSON.stringify(casos.map((c) => m.ponteParaPreco(c))));"
    ) % (json.dumps(str(ESPELHO)), json.dumps(casos))
    r = subprocess.run(["node", "-e", script],
                       capture_output=True, text=True, encoding="utf-8", timeout=60)
    assert r.returncode == 0, r.stdout + r.stderr
    resultados = json.loads(r.stdout)
    for caso, resultado in zip(casos, resultados):
        # avaliar.py linhas 233-234 (precificar_firm, ramo NOPAT):
        equity_esperado = caso["ev"] - caso["nd_efetivo"]
        preco_esperado = equity_esperado / caso["acoes"]
        assert resultado["equity"] == pytest.approx(equity_esperado, rel=1e-12)
        assert resultado["preco_acao"] == pytest.approx(preco_esperado, rel=1e-12)
