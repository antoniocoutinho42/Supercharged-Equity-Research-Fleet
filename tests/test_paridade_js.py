"""Paridade Python <-> JS do espelho do nucleo (regra inviolavel 1 do desenho v4).

O espelho e a UNICA matematica de valuation em JS que o projeto admite, e o que
a torna admissivel e este arquivo. Sem node o teste PULA com razao explicita; o
CI tem node (setup-node) e sempre roda.

Tolerancia: erro RELATIVO com piso absoluto, |py - js| <= max(TAU*|py|, TAU).
As grandezas vao de multiplos (~10) a valores de equity (~1e9), entao numero
fixo de casas seria frouxo num extremo e impossivel no outro. TAU nao e
escolhido e esquecido: `test_tau_tem_folga_medida` mede o erro maximo real e
reprova se a folga encolher — limiar sem propriedade medida e constante magica.
"""
import json
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

TAU = 1e-12
# FOLGA_MINIMA: quantas vezes TAU tem de estar acima do erro observado.
# MEDIDO, nao escolhido: sobre os 440 vetores da fixture o erro relativo
# maximo e 2.07e-15 (~9 ULP de um double — o ruido esperado de somar ~30
# termos com potencias), o que da folga de 482x contra TAU. O piso de 100x
# deixa espaco para variacao entre maquinas e versoes do node sem deixar de
# reprovar um colapso real. Um erro de TRANSCRICAO no espelho seria da ordem
# de 1e-3 ou maior — nove ordens de grandeza acima de TAU, nunca perto desta
# fronteira. Uma versao anterior deste plano exigia 1000x, numero que eu
# nao havia medido e que a medicao reprovou.
FOLGA_MINIMA = 100
SEM_NODE = shutil.which("node") is None
RAZAO = "node ausente do PATH — a paridade roda sempre no CI (setup-node)"


def _vetores():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _lado_js(vetores):
    r = subprocess.run(["node", str(ESPELHO), str(FIXTURE)],
                       capture_output=True, text=True, encoding="utf-8", timeout=180)
    assert r.returncode == 0, r.stdout + r.stderr
    por_id = {x["id"]: x["valor"] for x in json.loads(r.stdout)}
    return [por_id[v["id"]] for v in vetores]


def _erro_relativo(p, j):
    return abs(p - j) / max(abs(p), 1.0)


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_os_dois_lados_concordam_sobre_finitude():
    """Verificado ANTES do valor: numero onde o motor da NaN e defeito grave,
    e uma comparacao numerica ingenua o esconderia."""
    vetores = _vetores()
    py, js = avaliar_python(vetores), _lado_js(vetores)
    divergentes = [(v["id"], v["fn"], v["args"], p, j)
                   for v, p, j in zip(vetores, py, js)
                   if (p is None) != (j is None)]
    assert not divergentes, (
        f"{len(divergentes)} vetores discordam sobre finitude; primeiros 3: "
        f"{divergentes[:3]}")


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_paridade_numerica_dentro_de_tau():
    vetores = _vetores()
    py, js = avaliar_python(vetores), _lado_js(vetores)
    piores = sorted(
        ((_erro_relativo(p, j), v["id"], v["fn"], v["args"], p, j)
         for v, p, j in zip(vetores, py, js) if p is not None and j is not None),
        reverse=True)
    fora = [x for x in piores if x[0] > TAU]
    assert not fora, f"{len(fora)} vetores fora de TAU={TAU}; piores 3: {fora[:3]}"


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_tau_tem_folga_medida():
    """TAU entra na suite como propriedade MEDIDA, nao como constante magica."""
    vetores = _vetores()
    py, js = avaliar_python(vetores), _lado_js(vetores)
    maximo = max((_erro_relativo(p, j)
                  for p, j in zip(py, js) if p is not None and j is not None),
                 default=0.0)
    print(f"\nerro relativo maximo observado: {maximo:.3e} (TAU={TAU:.0e}, "
          f"folga {TAU / maximo:.0f}x)" if maximo else "")
    assert maximo < TAU / FOLGA_MINIMA, (
        f"folga encolheu: maximo observado {maximo:.3e} contra TAU {TAU:.0e}. "
        "Investigue a causa antes de mexer em TAU — a tolerancia existe para "
        "absorver ordem de avaliacao em ponto flutuante, nao erro de espelho.")


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_cobertura_da_fixture_no_harness():
    """O harness so vale se a fixture exercitar o que ele promete cobrir."""
    vetores = _vetores()
    py = avaliar_python(vetores)
    assert sum(1 for x in py if x is None) >= 20
    assert len(vetores) >= 300


def test_ausencia_de_node_pula_com_razao_explicita():
    """Pulo silencioso e defeito: quem roda local tem de saber que nao rodou."""
    assert RAZAO and "CI" in RAZAO
