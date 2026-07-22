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
