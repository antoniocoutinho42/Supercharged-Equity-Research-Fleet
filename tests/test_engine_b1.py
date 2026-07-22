# -*- coding: utf-8 -*-
"""B1 (engine v3.1.0) — blocos aditivos: sensibilidade_phi, fatos.reformulado + gates H7,
ebit_justo (âncora operacional no motor único), paridade-WARNING, história→números.

Âncoras numéricas: recomputos verificados no B0 (referencia/verificacao_referencia.py,
226/226 PASS) e na FASE A (C:/Claude/upgrade_fleet_v2_fase_a/). Fixture TFCO4 reconstruída
do relatorio_final_1.pdf (namespace original não existe nesta máquina — B4 usa reconstrução).
"""
import copy
import json
import os
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENG_DIR = os.path.join(REPO_ROOT, "skills", "er-valuation")
sys.path.insert(0, ENG_DIR)
sys.dont_write_bytecode = True
import engine  # noqa: E402

FIX_TFCO4 = os.path.join(REPO_ROOT, "tests", "fixtures", "tfco4", "inputs_b1.yaml")
FIX_FNV_P3 = os.path.join(REPO_ROOT, "tests", "fixtures", "fnv", "inputs_p3.yaml")


def carregar(path):
    return engine.carregar_inputs(path)


def rodar_fixture(path, mutador=None):
    inp = carregar(path)
    if mutador:
        mutador(inp)
    return engine.rodar(inp)


# ---------------------------------------------------------------------------
# Task 1 — baseline: o estado atual da fixture TFCO4 (âncora da regressão B1)
# ---------------------------------------------------------------------------

def test_baseline_tfco4():
    res = rodar_fixture(FIX_TFCO4)
    assert res["economico"]["central_ponderado"] == 8.34
    assert res["sinais"]["premio_sobre_econ_central_pct"] == 79.7
    assert res["reverse"]["cap_implicito_econ_base"] == 42.8631
    assert res["hurdle"]["cenarios"]["ponderado"] == 9.01
    assert res["gate"]["modo_recomendado"] == "SUMARIA"


# ---------------------------------------------------------------------------
# Task 2 — sensibilidade_phi (H11) com exclusão mútua φ × m_terminal
# Números medidos no phi_experiment do B0/FASE A (validado com erro 0,00 vs engine)
# ---------------------------------------------------------------------------

def test_phi_grid_tfco4():
    res = rodar_fixture(FIX_TFCO4)
    sp = res["sensibilidade_phi"]
    assert sp["aplicavel"] is True
    assert sp["motivo_na"] is None
    pond = {p["phi"]: p["central_ponderado"] for p in sp["grid"]}
    assert pond[0.0] == res["economico"]["central_ponderado"]  # identidade φ=0
    assert abs(pond[0.25] - 8.88) <= 0.01
    assert abs(pond[0.5] - 9.41) <= 0.01
    assert abs(pond[1.0] - 10.49) <= 0.01
    caps = {p["phi"]: p["cap_equivalente_base"] for p in sp["grid"]}
    assert caps[0.0] == pytest.approx(12.0, abs=0.01)
    assert abs(caps[0.25] - 13.76) <= 0.05
    assert abs(caps[0.5] - 15.58) <= 0.05
    assert abs(caps[1.0] - 19.41) <= 0.05
    # m(φ) = 1 + φ·(ROE−Ke)/Ke — cenário base ROE 0,22, Ke 0,14
    m_base = {p["phi"]: p["m_por_cenario"]["base"] for p in sp["grid"]}
    assert m_base[0.5] == pytest.approx(1.0 + 0.5 * (0.22 - 0.14) / 0.14, abs=5e-5)  # JSON arredonda m a 4 casas


def test_phi_na_com_m_terminal_manual():
    res = rodar_fixture(FIX_FNV_P3)  # FNV declara m_terminal 2.5/4.0/5.2
    sp = res["sensibilidade_phi"]
    assert sp["aplicavel"] is False
    assert "m_terminal" in sp["motivo_na"]
    assert sp["grid"] is None


def test_phi_exclusao_mutua_recusa():
    inp = carregar(FIX_FNV_P3)
    inp["premissas"]["phi"] = 0.5
    with pytest.raises(ValueError, match="exclus"):
        engine.rodar(inp)


# ---------------------------------------------------------------------------
# Task 3 — fatos.reformulado: invariantes na carga (ERRO), derivados, diagnóstico
# Série TF REAL (recomputo B0/h6_h7: EoP NOA/ND/TE + NOPAT + NI; médios = média de EoP consecutivos)
# ---------------------------------------------------------------------------

SERIE_TF = [
    # ano, receita, nopat, noa_medio, nd_medio, e_medio, e_fim, nie_pos, ni
    dict(ano=2020, receita=267320.0, nopat=31364.9, noa_medio=147095.05, nd_medio=41589.9,
         e_medio=105505.15, e_fim=200190.8, nie_pos_imposto=-3730.9, ni_recorrente=27634.0),
    dict(ano=2021, receita=434592.0, nopat=81389.3, noa_medio=225370.55, nd_medio=-6140.85,
         e_medio=231511.4, e_fim=262832.0, nie_pos_imposto=-1423.3, ni_recorrente=79966.0),
    dict(ano=2022, receita=567426.0, nopat=100302.2, noa_medio=327597.0, nd_medio=37491.0,
         e_medio=290106.0, e_fim=317380.0, nie_pos_imposto=-3842.0, ni_recorrente=96460.2),
    dict(ano=2023, receita=683690.1, nopat=124256.1, noa_medio=419478.35, nd_medio=64314.85,
         e_medio=355163.5, e_fim=392947.0, nie_pos_imposto=-9846.1, ni_recorrente=114410.0),
    dict(ano=2024, receita=787411.5, nopat=120214.4, noa_medio=469069.6, nd_medio=43087.6,
         e_medio=425982.0, e_fim=459017.0, nie_pos_imposto=-11659.7, ni_recorrente=108554.7),
]


def com_reformulado(inp, serie=None):
    inp["fatos"]["reformulado"] = {
        "unidade": "R$ mil", "fonte": "T&F_CG_3Q24.xlsm Reformulated Accounts (recomputo B0)",
        "serie": copy.deepcopy(serie if serie is not None else SERIE_TF)}


def test_reformulado_derivados_tf():
    res = rodar_fixture(FIX_TFCO4, com_reformulado)
    fr = res["fatos_reformulado"]
    s24 = fr["serie"][-1]
    assert s24["roic"] == pytest.approx(0.2563, abs=1e-3)
    assert s24["margem_nopat"] * s24["giro_noa"] == pytest.approx(s24["roic"], abs=1e-6)
    assert s24["nbc"] == pytest.approx(0.2706, abs=1e-3)          # spread financeiro NEGATIVO 2024
    assert s24["roe_ponte"] == pytest.approx(s24["roe_direto"], abs=1e-6)
    assert s24["roe_direto"] == pytest.approx(0.254834, abs=1e-4)
    d = fr["diagnostico"]
    esperado_roiic = (120214.4 - 31364.9) / (469069.6 - 147095.05)
    assert d["roiic_acumulado"] == pytest.approx(esperado_roiic, abs=1e-6)
    assert d["janela"] == "2020-2024"


def test_reformulado_ce_noa_erro():
    def quebra(inp):
        com_reformulado(inp)
        inp["fatos"]["reformulado"]["serie"][2]["nd_medio"] *= 1.10  # CE != NOA além de 0,5%
    with pytest.raises(ValueError, match="CE"):
        rodar_fixture(FIX_TFCO4, quebra)


def test_reformulado_ni_inconsistente_erro():
    def quebra(inp):
        com_reformulado(inp)
        inp["fatos"]["reformulado"]["serie"][3]["ni_recorrente"] *= 1.05
    with pytest.raises(ValueError, match="ni_recorrente"):
        rodar_fixture(FIX_TFCO4, quebra)


def test_reformulado_roic_declarado_divergente_erro():
    def quebra(inp):
        com_reformulado(inp)
        inp["fatos"]["reformulado"]["serie"][-1]["roic"] = 0.30    # declarado != derivado 0,2563
    with pytest.raises(ValueError, match="roic"):
        rodar_fixture(FIX_TFCO4, quebra)


def test_reformulado_ausente_nao_emite_bloco():
    res = rodar_fixture(FIX_TFCO4)
    assert "fatos_reformulado" not in res


# ---------------------------------------------------------------------------
# Task 4 — Gates H7 (PROVISÓRIOS n=3): A1-A3 eliminatórios; A4/F1/F2 flags
# Séries reais: TF (B0/h6_h7 → EQUITY_OK com flag de FLEV) e PVV (→ GATE_DISPARA)
# ---------------------------------------------------------------------------

SERIE_PVV = [
    # EoP usados como e_medio/e_fim (aproximação de teste; não muda o veredicto);
    # nd reconstruído de FLEV×E (h6_h7); nie=0 → ni≡nopat (identidade preservada)
    dict(ano=2022, receita=10000.0, nopat=-44361.6, noa_medio=30012.9, nd_medio=37637.8,
         e_medio=-7624.9, e_fim=-7624.9, nie_pos_imposto=0.0, ni_recorrente=-44361.6),
    dict(ano=2023, receita=10000.0, nopat=-29990.1, noa_medio=19610.5, nd_medio=45335.1,
         e_medio=-25724.6, e_fim=-25724.6, nie_pos_imposto=0.0, ni_recorrente=-29990.1),
    dict(ano=2024, receita=10000.0, nopat=-15110.0, noa_medio=16742.3, nd_medio=15328.0,
         e_medio=1414.3, e_fim=1414.3, nie_pos_imposto=0.0, ni_recorrente=-15110.0),
    dict(ano=2025, receita=10000.0, nopat=-13504.7, noa_medio=20370.2, nd_medio=11158.5,
         e_medio=9211.7, e_fim=9211.7, nie_pos_imposto=0.0, ni_recorrente=-13504.7),
]


def test_gates_h7_tf_equity_ok():
    res = rodar_fixture(FIX_TFCO4, com_reformulado)
    g7 = res["fatos_reformulado"]["gates_aplicabilidade"]
    assert g7["calibracao"] == "PROVISORIO_N3"
    assert g7["ancora_equity"] == "EQUITY_OK"
    assert g7["ancora_primaria_recomendada"] == "EQUITY"
    assert g7["eliminatorios"]["a1_e_positivo"]["passa"] is True
    assert g7["eliminatorios"]["a2_mediana_e_noa"]["passa"] is True
    assert g7["eliminatorios"]["a3_lucro_recorrente"]["passa"] is True
    codigos = [f["codigo"] for f in g7["flags"]]
    assert "FLEV_CRUZA_SINAL" in codigos       # net cash transitório: flag, NUNCA eliminatório
    assert "NBC_INSTAVEL" not in codigos       # |FLEV| médio TF < 0,20 (limiar de materialidade)
    assert "recalibra" in g7["nota_recalibracao"].lower()


def test_gates_h7_pvv_dispara():
    res = rodar_fixture(FIX_TFCO4, lambda inp: com_reformulado(inp, SERIE_PVV))
    g7 = res["fatos_reformulado"]["gates_aplicabilidade"]
    assert g7["ancora_equity"] == "GATE_DISPARA"
    assert g7["ancora_primaria_recomendada"] == "OPERACIONAL"
    assert g7["eliminatorios"]["a1_e_positivo"]["passa"] is False
    assert g7["eliminatorios"]["a2_mediana_e_noa"]["passa"] is False
    assert g7["eliminatorios"]["a3_lucro_recorrente"]["passa"] is False
