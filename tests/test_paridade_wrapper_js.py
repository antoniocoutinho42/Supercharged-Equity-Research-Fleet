"""Paridade do WRAPPER: alvo de mercado, eixo de reversa e grades.

Natureza diferente da paridade do solver: aqui o lado Python NAO e o motor
congelado, e sim `reversa.py`/`sensibilidades.py`. Um espelho fiel ao motor e
infiel ao wrapper produziria numeros certos no lugar errado — por isso os dois
harnesses sao arquivos separados.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
ESPELHO = RAIZ / "skills" / "er-valuation" / "assets" / "motor_espelho.js"
FIXTURE = RAIZ / "tests" / "fixtures" / "vetores_solver.json"
sys.path.insert(0, str(RAIZ / "skills" / "er-valuation" / "scripts"))
from vetores_solver import avaliar_python  # noqa: E402

TAU = 1e-12
SEM_NODE = shutil.which("node") is None
RAZAO = "node ausente do PATH — a paridade roda sempre no CI (setup-node)"


def _problemas(tipos):
    todos = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return [p for p in todos if p.get("tipo") in tipos]


def _lado_js():
    r = subprocess.run(["node", str(ESPELHO), str(FIXTURE)],
                       capture_output=True, text=True, encoding="utf-8", timeout=300)
    assert r.returncode == 0, r.stdout + r.stderr
    return {x["id"]: x for x in json.loads(r.stdout)}


def _rel(a, b):
    return abs(a - b) / max(abs(a), 1.0)


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_alvo_de_mercado_bate_nas_duas_rotas():
    probs = _problemas({"alvo"})
    assert probs, "fixture sem problemas de alvo"
    py, js = avaliar_python(probs), _lado_js()
    fora = [(p["id"], p["args"]["rota"], a["alvo"], js[p["id"]]["alvo"])
            for p, a in zip(probs, py) if _rel(a["alvo"], js[p["id"]]["alvo"]) > TAU]
    assert not fora, f"alvo divergente: {fora[:3]}"
    assert {p["args"]["rota"] for p in probs} >= {"firm", "equity"}
    assert any(p["args"].get("nd_efetivo", 0) < 0 for p in probs), "nenhum caso com caixa liquido"


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_grades_tem_a_orientacao_do_wrapper():
    """Grade NAO quadrada de proposito: a fatia 3C descobriu que uma 3x3
    esconde uma transposicao de eixos — o teste passava com os eixos trocados."""
    probs = _problemas({"grade2d"})
    assert probs, "fixture sem grades 2D"
    js = _lado_js()
    nao_quadradas = [p for p in probs
                     if len(p["args"]["pontos_x"]) != len(p["args"]["pontos_y"])]
    assert nao_quadradas, "toda grade 2D e quadrada — transposicao ficaria invisivel"
    for p in nao_quadradas:
        g = js[p["id"]]
        px, py_ = p["args"]["pontos_x"], p["args"]["pontos_y"]
        assert len(g["celulas"]) == len(py_)
        assert all(len(linha) == len(px) for linha in g["celulas"])
        for i, linha in enumerate(g["celulas"]):
            for j, cel in enumerate(linha):
                assert cel["x"] == px[j] and cel["y"] == py_[i]


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_valor_e_multiplo_de_cada_celula_dentro_de_tau():
    probs = _problemas({"grade1d", "grade2d"})
    assert probs, "fixture sem grades"
    py, js = avaliar_python(probs), _lado_js()
    piores = []
    for p, a in zip(probs, py):
        b = js[p["id"]]
        cel_py = a["celulas"] if p["tipo"] == "grade1d" else [c for lin in a["celulas"] for c in lin]
        cel_js = b["celulas"] if p["tipo"] == "grade1d" else [c for lin in b["celulas"] for c in lin]
        assert len(cel_py) == len(cel_js), f"contagem de celulas difere no problema {p['id']}"
        for cp, cj in zip(cel_py, cel_js):
            for campo in ("valor", "multiplo"):
                if cp[campo] is None or cj[campo] is None:
                    assert (cp[campo] is None) == (cj[campo] is None), (p["id"], campo)
                    continue
                piores.append((_rel(cp[campo], cj[campo]), p["id"], campo, cp[campo], cj[campo]))
    piores.sort(reverse=True)
    fora = [x for x in piores if x[0] > TAU]
    assert not fora, f"{len(fora)} celulas fora de TAU; piores 3: {fora[:3]}"


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_celula_central_reproduz_o_caso_base():
    """Regra da metodologia: a celula na premissa do caso-base bate com a manchete."""
    probs = _problemas({"grade1d"})
    py, js = avaliar_python(probs), _lado_js()
    checados = 0
    for p, a in zip(probs, py):
        central = p["args"]["premissas"].get(p["args"]["premissa"])
        if central is None or central not in p["args"]["pontos"]:
            continue
        k = p["args"]["pontos"].index(central)
        assert _rel(a["celulas"][k]["valor"], js[p["id"]]["celulas"][k]["valor"]) <= TAU
        checados += 1
    assert checados >= 1, "nenhuma grade inclui o ponto central — a regra nao foi exercitada"
