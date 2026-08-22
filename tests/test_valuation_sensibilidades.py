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
    # FIX 6 (revisao final): so "valor" era conferido aqui -- uma regressao
    # que devolvesse o multiplo forward em vez do corrente (ou o campo da
    # rota errada) passava verde. "multiplo" tem de bater tambem, contra o
    # mesmo EV/EBITDA_curr do caso-base.
    assert ponto["multiplo"] == pytest.approx(esperado["EV/EBITDA_curr"], abs=1e-4)


def test_grade_declara_triangulo_e_metrica_de_referencia():
    spec = _caso()["sensibilidades"]["grades_1d"][0]
    g = grade_1d(_caso(), "base", spec, 500.0)
    assert g["triangulo"] == spec["triangulo"]
    assert g["metrica_de_referencia"]["tipo"] == "EBITDA"
    assert g["metrica_de_referencia"]["valor"] == 1000.0


def test_diagnosticos_deduplicados_reconstroem_a_execucao_direta():
    """Os indices tem de devolver exatamente o que o motor emitiu naquela celula.

    A celula passa `caso["moeda"]` ao motor (ver sensibilidades.py); a
    chamada direta usada aqui para comparacao precisa da mesma moeda, senao
    as duas listas de diagnostico nunca batem (uma carregaria o alarme de
    moeda nao declarada, a outra nao) — o teste deixaria de provar
    reconstrucao por indice e passaria a provar duas execucoes divergentes.

    FIX 8 (revisão final): a versão anterior só reconstruía o PRIMEIRO
    ponto, onde a lista de índices é trivialmente 0,1,2... (nenhum índice
    aponta para trás, porque nada foi visto antes dele). Isso não exercita
    a propriedade de dedup em si — só provaria isso um ponto cujos índices
    reaproveitam índice de um ponto ANTERIOR. Verificado contra a fixture:
    o último ponto (wacc=12.0) tem `diag = [6, 8, 9, 1, 2]` — os índices 1,
    2 e 6 foram introduzidos por pontos anteriores (wacc=8.0 e wacc=11.0) e
    reaproveitados aqui, não reinseridos.
    """
    c = _caso()
    spec = c["sensibilidades"]["grades_1d"][0]
    g = grade_1d(c, "base", spec, 500.0)

    for ponto in (g["pontos"][0], g["pontos"][-1]):
        premissas = dict(c["cenarios"]["base"]["premissas"])
        premissas[spec["premissa"]] = ponto["x"]
        direto = rodar("firm", premissas, {"ebitda": 1000.0, "nd": 500.0, "acoes": 100.0},
                        moeda=c["moeda"])
        reconstruido = [g["diagnosticos_unicos"][i] for i in ponto["diag"]]
        assert reconstruido == direto["diagnosticos"]

    # o ultimo ponto de fato reaproveita indice de um ponto anterior --
    # sem isso, o loop acima poderia passar mesmo se cada ponto sempre
    # introduzisse indice novo (nenhuma reutilizacao real acontecendo).
    assert set(g["pontos"][-1]["diag"]) & set(g["pontos"][0]["diag"])


def test_regressao_sem_alarme_falso_de_moeda_nas_celulas():
    """Fix da regressao: celula de grade tem de repassar `caso["moeda"]` ao
    motor, exatamente como o cenario principal (`avaliar()`) ja faz — sem
    isso toda celula, 1D e 2D, carregava o alarme falso "MOEDA/REGIME NAO
    DECLARADOS" (mesma causa-raiz do FIX 4 coberto para o cenario principal
    em test_valuation_avaliar.py e test_valuation_motor.py, agora tambem
    provado para a grade)."""
    c = _caso()
    r = calcular(c, "base", 500.0)
    for grade in r["grades_1d"]:
        assert not any("MOEDA/REGIME" in d for d in grade["diagnosticos_unicos"])
    for grade in r["grades_2d"]:
        assert not any("MOEDA/REGIME" in d for d in grade["diagnosticos_unicos"])


def test_grade_2d_tem_a_forma_declarada():
    """FIX 5 (revisao final): a fixture agora usa uma grade NAO QUADRADA
    (3 linhas x 4 colunas) -- numa grade quadrada, trocar premissa_x por
    premissa_y na hora de montar a celula (uma transposicao) passa por
    "len(celulas) == len(pontos_y)" sem quebrar, porque as duas contagens
    sao iguais. So uma grade nao quadrada, mais a checagem ponto a ponto de
    x/y abaixo, prova que celulas[i][j] de fato corresponde a
    (pontos_y[i], pontos_x[j]) -- nao so que a CONTAGEM de linhas/colunas
    bate."""
    c = _caso()
    r = calcular(c, "base", 500.0)
    g2 = r["grades_2d"][0]
    pontos_x = g2["pontos_x"]
    pontos_y = g2["pontos_y"]
    assert len(pontos_x) != len(pontos_y), "a grade da fixture precisa ser nao-quadrada"
    assert len(g2["celulas"]) == len(pontos_y)
    assert all(len(linha) == len(pontos_x) for linha in g2["celulas"])

    for i, y in enumerate(pontos_y):
        for j, x in enumerate(pontos_x):
            celula = g2["celulas"][i][j]
            assert celula["x"] == x
            assert celula["y"] == y

    # uma celula conferida contra chamada direta ao motor, nas mesmas
    # premissas -- prova que "valor" e "multiplo" tambem estao na celula
    # certa, nao so a forma (linhas x colunas) da grade.
    i, j = 1, 2
    premissas = dict(c["cenarios"]["base"]["premissas"])
    premissas[g2["premissa_x"]] = pontos_x[j]
    premissas[g2["premissa_y"]] = pontos_y[i]
    esperado = rodar("firm", premissas, {"ebitda": 1000.0, "nd": 500.0, "acoes": 100.0},
                      moeda=c["moeda"])
    celula = g2["celulas"][i][j]
    assert celula["valor"] == pytest.approx(esperado["Preco_acao"], abs=0.01)
    assert celula["multiplo"] == pytest.approx(esperado["EV/EBITDA_curr"], abs=1e-4)


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


# --------------------------------------------------------------------------
# Revisão final, FIX 7 (Importante): com métrica EBITDA o motor devolve o
# preço pronto e a célula não faz conta nenhuma fora dele. Com NOPAT, a
# célula roda o motor SEM escala e faz a álgebra ela mesma
# (ev = multiplo x metrica; equity = ev - nd_efetivo; preco = equity /
# acoes — ver avaliar.precificar_firm) — o único ramo em que uma célula de
# grade faz aritmética do wrapper, e que nenhuma grade exercitava até
# agora. NOPAT coerente com a fixture: EBITDA 1000 x (1 - d 20%) x
# (1 - t 25%) = 600 — mesma identidade de
# test_escala_por_nopat_reconcilia_com_a_escala_por_ebitda, em
# test_valuation_avaliar.py; reaproveitada aqui em vez de inventada de novo.
# --------------------------------------------------------------------------

def test_grade_1d_no_ramo_nopat_faz_a_algebra_da_ponte_na_celula():
    c = _caso()
    c["metrica_base"] = {"tipo": "NOPAT", "valor": 600.0, "periodo": "2025A",
                         "fonte": "derivado do EBITDA da fixture"}
    spec = c["sensibilidades"]["grades_1d"][0]
    g = grade_1d(c, "base", spec, 500.0)

    assert g["metrica_de_referencia"]["tipo"] == "NOPAT"
    assert g["metrica_de_referencia"]["valor"] == 600.0

    ponto = g["pontos"][0]
    premissas = dict(c["cenarios"]["base"]["premissas"])
    premissas[spec["premissa"]] = ponto["x"]
    direto = rodar("firm", premissas, None, moeda=c["moeda"])
    multiplo_esperado = direto["EV/NOPAT_curr"]
    ev_esperado = multiplo_esperado * 600.0
    preco_esperado = (ev_esperado - 500.0) / 100.0

    assert ponto["multiplo"] == pytest.approx(multiplo_esperado, abs=1e-4)
    assert ponto["valor"] == pytest.approx(preco_esperado, abs=0.01)
