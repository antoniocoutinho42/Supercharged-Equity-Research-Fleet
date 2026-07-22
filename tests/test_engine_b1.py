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
