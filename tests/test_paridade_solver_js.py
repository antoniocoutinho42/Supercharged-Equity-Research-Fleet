"""Paridade do SOLVER: espelho JS contra o motor congelado.

Natureza de risco DIFERENTE da paridade do nucleo (tests/test_paridade_js.py,
fatia 4A). La o espelho e forma fechada e uma diferenca de 1e-15 permanece
1e-15; o solver aqui e ITERATIVO e AMPLIFICA — uma diferenca minuscula em `f`
pode inverter a comparacao de sinal `y0*y1<=0` num ponto da varredura e
produzir uma raiz A MAIS OU A MENOS. Essa e uma divergencia DISCRETA, nao
numerica, que uma comparacao de valores ingenua nao pega. Por isso a
CONTAGEM (raizes e tangenciais) e comparada primeiro e exatamente, antes de
qualquer numero.

Medido pelo controlador antes desta fatia, perturbando `f` em 1e-15 relativo
e re-resolvendo: contagem ESTAVEL em todos os casos amostrados (gordon
resolvendo `w` com alvos 8.0-13.3; book resolvendo `roic` perto da
neutralidade; casos tangenciais perto do teto), deslocamento da raiz entre 0
e 5.1e-15 (o erro do nucleo amplificado ~2-3x). Conclusao: o solver e bem
condicionado nas regioes que importam e TAU=1e-12 serve — mas a contagem
continua sendo o primeiro gate. Se ela divergir alguma vez, isso e um ACHADO
sobre a estabilidade do solver naquele ponto — reporte o problema completo,
nao afrouxe nada (ver `.superpowers/sdd/task-4b-2-brief.md`).

Quatro testes, nao sete: a calibragem de rigor deste brief (26/08/2026)
consolida contagem+valor+identificacao em tres testes (a 4A, mais cerimoniosa,
usava seis) mais um piso de cobertura da fixture — o MESMO padrao de rigor
(contagem exata antes de numero, folga medida, classe exata, campos
arredondados exatos), so' sem a decomposicao 1-teste-por-asserto.
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
# FOLGA_MINIMA: mesmo piso da 4A (tests/test_paridade_js.py). Nao re-derivado
# aqui por capricho de simetria — e a mesma pergunta ("quantas vezes TAU esta
# acima do erro observado antes de eu desconfiar de uma regressao, e nao de
# ruido de maquina/versao do node") sobre um numero medido por
# test_folga_de_tau_medida_no_solver, nao escolhido.
FOLGA_MINIMA = 100
SEM_NODE = shutil.which("node") is None
RAZAO = "node ausente do PATH — a paridade roda sempre no CI (setup-node)"


def _problemas():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _lado_js():
    r = subprocess.run(["node", str(ESPELHO), str(FIXTURE)],
                       capture_output=True, text=True, encoding="utf-8", timeout=300)
    assert r.returncode == 0, r.stdout + r.stderr
    return {x["id"]: x for x in json.loads(r.stdout)}


def _rel(a, b):
    return abs(a - b) / max(abs(a), 1.0)


def test_fixture_commitada_reproduz_o_gerador(tmp_path):
    """Determinismo da fixture — o mesmo contrato que a fixture da 4A ja tem.

    Sem isto, um gerador que perdesse a determinismo (`random` global, ordem de
    dict, tempo) ou uma fixture editada a mao em vez de regerada divergiriam em
    silencio: a paridade continuaria verde, mas a fixture deixaria de cobrir o
    que diz cobrir. Nao precisa de node — e comparacao Python x disco."""
    destino = tmp_path / "regerado.json"
    r = subprocess.run(
        [sys.executable, str(RAIZ / "skills" / "er-valuation" / "scripts" / "vetores_solver.py"),
         "--out", str(destino)],
        capture_output=True, text=True, encoding="utf-8", timeout=300)
    assert r.returncode == 0, r.stdout + r.stderr
    assert destino.read_bytes() == FIXTURE.read_bytes()


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_contagem_de_raizes_e_tangenciais_bate_exatamente():
    """As duas contagens — raizes E tangenciais —, EXATAS, antes de qualquer
    comparacao numerica. Uma raiz ou tangencial a mais ou a menos e uma
    divergencia DISCRETA (ver docstring do modulo), nunca um problema de
    tolerancia."""
    probs, js = _problemas(), _lado_js()
    py = avaliar_python(probs)
    fora = [
        (p["id"], p["resolver"], p["args"],
         len(a["raizes"]), len(js[p["id"]]["raizes"]),
         len(a["tangenciais"]), len(js[p["id"]]["tangenciais"]))
        for p, a in zip(probs, py)
        if len(a["raizes"]) != len(js[p["id"]]["raizes"])
        or len(a["tangenciais"]) != len(js[p["id"]]["tangenciais"])
    ]
    assert not fora, (
        f"{len(fora)} problemas com contagem divergente (raizes e/ou tangenciais) — "
        f"(id, resolver, args, #raizes_py, #raizes_js, #tang_py, #tang_js) "
        f"primeiros 3: {fora[:3]}"
    )


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_valor_das_raizes_dentro_de_tau():
    """Raiz a raiz NA ORDEM (os dois lados devolvem ordenado por
    `_dedupe_roots`/`dedupeRaizes`); pula problemas cuja CONTAGEM ja
    divergiu — esses ja estao cobertos, e comparar valor de listas de
    tamanhos diferentes nao diz nada novo. A folga contra TAU e MEDIDA
    aqui mesmo, um teste so, nao presumida."""
    probs, js = _problemas(), _lado_js()
    py = avaliar_python(probs)
    piores = []
    for p, a in zip(probs, py):
        b = js[p["id"]]
        if len(a["raizes"]) != len(b["raizes"]):
            continue
        for r_py, r_js in zip(a["raizes"], b["raizes"]):
            piores.append((_rel(r_py, r_js), p["id"], p["resolver"], r_py, r_js))
    piores.sort(reverse=True)
    maximo = piores[0][0] if piores else 0.0
    if maximo:
        print(f"\nsolver — erro relativo maximo nas raizes: {maximo:.3e} "
              f"(TAU={TAU:.0e}, folga {TAU / maximo:.0f}x)")
    else:
        print("\nsolver — todas as raizes comparaveis batem exatamente (erro 0)")
    fora = [x for x in piores if x[0] > TAU]
    assert not fora, f"{len(fora)} raizes fora de TAU={TAU}; piores 3: {fora[:3]}"
    assert maximo < TAU / FOLGA_MINIMA, (
        f"folga encolheu: {maximo:.3e} contra TAU {TAU:.0e}. O solver amplifica o erro "
        "do nucleo; investigue a causa antes de mexer em TAU.")


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_identificacao_bate():
    """presenca/ausencia do dict de identificacao; a CLASSE
    (forte/moderada/fraca — uma DECISAO, nao um numero) exata; e igualdade
    EXATA dos campos arredondados (slope_dM_dx, curvatura_d2M_dx2,
    elasticidade, largura_relativa_%) quando o dict nao e o degenerado
    (`{'nota': ...}`, sem esses campos). `nota` NAO entra na comparacao:
    e funcao pura da classe (justos.py:344-347) — compara-la e cobertura
    marginal de prosa depois que a classe ja bateu."""
    probs, js = _problemas(), _lado_js()
    py = avaliar_python(probs)
    fora = []
    for p, a in zip(probs, py):
        i_py, i_js = a["identificacao"], js[p["id"]]["identificacao"]
        if (i_py is None) != (i_js is None):
            fora.append((p["id"], "presenca", i_py, i_js))
            continue
        if i_py is None:
            continue
        if i_py.get("identificacao") != i_js.get("identificacao"):
            fora.append((p["id"], "classe", i_py.get("identificacao"), i_js.get("identificacao")))
            continue
        if "slope_dM_dx" not in i_py:
            continue  # degenerado nos dois lados (derivadas indisponiveis) -- ja cobre por 'presenca'/'classe'
        for campo in ("slope_dM_dx", "curvatura_d2M_dx2", "elasticidade", "largura_relativa_%"):
            if i_py.get(campo) != i_js.get(campo):
                fora.append((p["id"], campo, i_py.get(campo), i_js.get(campo)))
    assert not fora, f"{len(fora)} divergencias de identificacao; primeiras 3: {fora[:3]}"


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_fixture_cobre_o_que_discrimina():
    """Pisos baixos e honestos (calibragem do brief): pelo menos um caso sem
    raiz, um multi-raiz, uma tangencial, um `completo: true` exercitado, e a
    classe 'forte' presente. Nao inventa piso de contagem alto que so' da
    trabalho de retunar depois sem discriminar nada novo."""
    probs = _problemas()
    py = avaliar_python(probs)
    assert any(len(r["raizes"]) == 0 for r in py), "nenhum caso sem raiz na fixture"
    assert any(len(r["raizes"]) >= 2 for r in py), "nenhum caso multi-raiz na fixture"
    assert any(r["tangenciais"] for r in py), "nenhuma tangencial na fixture"
    assert any(p.get("completo") for p in probs), "solve_full (completo=true) nunca exercitado"
    classes = {r["identificacao"]["identificacao"] for r in py
               if r["identificacao"] and "identificacao" in r["identificacao"]}
    assert "forte" in classes, "nenhuma identificacao 'forte' na fixture"
