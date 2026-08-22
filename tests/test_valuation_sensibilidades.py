import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures"
sys.path.insert(0, str(RAIZ / "skills" / "er-valuation" / "scripts"))
from caso import carregar  # noqa: E402
from motor import rodar  # noqa: E402
from sensibilidades import calcular, grade_1d  # noqa: E402


def _caso() -> dict:
    return carregar(FIXTURES / "caso_reversa_firm.json")


def test_grade_1d_tem_um_ponto_por_valor_declarado():
    spec = _caso()["sensibilidades"]["grades_1d"][0]
    g = grade_1d(_caso(), "base", spec, 500.0)
    assert [p["x"] for p in g["pontos"]] == spec["pontos"]


def test_celula_do_ponto_central_reproduz_o_caso_base():
    """A celula na premissa do caso-base TEM de bater com o caso-base."""
    c = _caso()
    spec = c["sensibilidades"]["grades_1d"][0]
    central = c["cenarios"]["base"]["premissas"][spec["premissa"]]
    assert central in spec["pontos"], "a fixture precisa incluir o ponto central"
    g = grade_1d(c, "base", spec, 500.0)
    ponto = next(p for p in g["pontos"] if p["x"] == central)
    esperado = rodar("firm", c["cenarios"]["base"]["premissas"],
                     {"ebitda": 1000.0, "nd": 500.0, "acoes": 100.0})
    assert ponto["valor"] == pytest.approx(esperado["Preco_acao"], abs=0.01)


def test_grade_declara_triangulo_e_metrica_de_referencia():
    spec = _caso()["sensibilidades"]["grades_1d"][0]
    g = grade_1d(_caso(), "base", spec, 500.0)
    assert g["triangulo"] == spec["triangulo"]
    assert g["metrica_de_referencia"]["tipo"] == "EBITDA"
    assert g["metrica_de_referencia"]["valor"] == 1000.0


def test_diagnosticos_deduplicados_reconstroem_a_execucao_direta():
    """Os indices tem de devolver exatamente o que o motor emitiu naquela celula."""
    c = _caso()
    spec = c["sensibilidades"]["grades_1d"][0]
    g = grade_1d(c, "base", spec, 500.0)
    ponto = g["pontos"][0]
    premissas = dict(c["cenarios"]["base"]["premissas"])
    premissas[spec["premissa"]] = ponto["x"]
    direto = rodar("firm", premissas, {"ebitda": 1000.0, "nd": 500.0, "acoes": 100.0})
    reconstruido = [g["diagnosticos_unicos"][i] for i in ponto["diag"]]
    assert reconstruido == direto["diagnosticos"]


def test_grade_2d_tem_a_forma_declarada():
    c = _caso()
    r = calcular(c, "base", 500.0)
    g2 = r["grades_2d"][0]
    assert len(g2["celulas"]) == len(g2["pontos_y"])
    assert all(len(linha) == len(g2["pontos_x"]) for linha in g2["celulas"])


def test_calcular_devolve_todas_as_grades_declaradas():
    c = _caso()
    r = calcular(c, "base", 500.0)
    assert len(r["grades_1d"]) == len(c["sensibilidades"]["grades_1d"])
    assert len(r["grades_2d"]) == len(c["sensibilidades"]["grades_2d"])


def test_celula_que_nula_no_motor_e_recusada_nao_silenciada():
    """Mesma disciplina da fatia A: null do motor nao vira null no arquivo.

    Verificado contra o vendor: sob tv=gordon, roic_tv = 0 faz o motor devolver
    EV e Preco_acao nulos com exit 0.
    """
    from motor import MotorFalhou
    c = _caso()
    spec = {"premissa": "roic_tv", "pontos": [0.0],
            "triangulo": c["sensibilidades"]["grades_1d"][0]["triangulo"]}
    with pytest.raises(MotorFalhou):
        grade_1d(c, "base", spec, 500.0)
