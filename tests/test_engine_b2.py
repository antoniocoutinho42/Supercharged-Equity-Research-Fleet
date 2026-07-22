# -*- coding: utf-8 -*-
"""B2 (engine v3.2.0) — respostas R2–R5 por chave: central_neutro + robustez_conjunta,
validacao_multiplos.implicitos, ke_dossier + grade de Ke. Aceitação: números medidos
no B0 (tfco4_repro.md §4, h8_quant.out.txt) com o engine REAL."""
import os
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "skills", "er-valuation"))
sys.dont_write_bytecode = True
import engine  # noqa: E402

from test_engine_b1 import FIX_TFCO4, carregar, rodar_fixture  # noqa: E402


# ---------------------------------------------------------------------------
# Task 1 — central_neutro + robustez_conjunta (R2)
# ---------------------------------------------------------------------------

def com_central_neutro(inp):
    inp["premissas"]["central_neutro"] = {
        "lpa": 1.05, "cap_base": 13, "ke": 0.125,
        "justificativa": ("Caso conjunto moderado (R2): base de lucro neutra entre o reportado "
                          "0,95 e o ajustado 1,12; CAP base dentro da banda moat-claro; Ke na "
                          "média das rotas do dossiê — desfaz o empilhamento conservador sem "
                          "escolher premissa pelo resultado.")}


def test_central_neutro_tfco4():
    res = rodar_fixture(FIX_TFCO4, com_central_neutro)
    cn = res["central_neutro"]
    assert cn["premio_econ_pct"] == pytest.approx(41.7, abs=0.15)
    assert cn["premio_hurdle_pct"] == pytest.approx(47.5, abs=0.15)
    rc = cn["robustez_conjunta"]
    assert rc["baseline"]["premio_econ_pct"] == pytest.approx(79.7, abs=0.05)
    assert rc["baseline"]["premio_hurdle_pct"] == pytest.approx(66.4, abs=0.05)
    d = rc["decomposicao"]
    assert d["so_lpa_pp"] == pytest.approx(-17.1, abs=0.15)
    assert d["so_cap_pp"] == pytest.approx(-2.9, abs=0.15)
    assert d["so_ke_pp"] == pytest.approx(-19.9, abs=0.15)
    assert d["interacao_pp"] == pytest.approx(1.9, abs=0.25)   # sub-aditiva
    assert cn["gate_recomputado"]["modo"] == "PADRAO"          # SUMARIA -> PADRAO (R2 processual)


def test_central_neutro_justificativa_obrigatoria():
    def mut(inp):
        com_central_neutro(inp)
        inp["premissas"]["central_neutro"]["justificativa"] = "curta"
    with pytest.raises(ValueError, match="central_neutro"):
        rodar_fixture(FIX_TFCO4, mut)


def test_central_neutro_ausente_nao_emite():
    res = rodar_fixture(FIX_TFCO4)
    assert "central_neutro" not in res


# ---------------------------------------------------------------------------
# Task 2 — validacao_multiplos.implicitos (R3): que premissas justificam cada
# múltiplo de referência — reverse aplicado à mediana histórica e à dos pares
# ---------------------------------------------------------------------------

def test_implicitos_round_trip_e_monotonia():
    res = rodar_fixture(FIX_TFCO4)
    imp = res["validacao_multiplos"]["implicitos"]
    inp = carregar(FIX_TFCO4)
    base = inp["premissas"]["cenarios"]["base"]
    de, nde = inp["fatos"]["de"], inp["fatos"]["nde"]
    hist = imp["historico_proprio"]
    assert hist["multiplo"] == 20.0
    got = engine.pl_justo(base["g"], base["roe"], hist["cap_implicito"], 0.14, de, nde, 1.0)
    assert got == pytest.approx(20.0, abs=0.05)                # round-trip da bisseção (cap 1 casa)
    pares = imp["comparaveis"]
    assert pares["multiplo"] == pytest.approx(5.24, abs=0.01)
    # monotonia: justificar 20x exige MAIS duração que o justo (8,16x); 5,24x exige menos
    pl_justo_econ = res["validacao_multiplos"]["pl_justo_ponderado_econ"]
    assert hist["cap_implicito"] > base["cap"]
    if pares["cap_implicito"] is not None:
        assert pares["cap_implicito"] < base["cap"]
    # ke implícito da mediana dos pares > Ke central (múltiplo menor = desconto maior)
    if pares["ke_implicito"] is not None:
        assert pares["ke_implicito"] > 0.14
    assert "decomposicao" in imp["nota"].lower() or "driver" in imp["nota"].lower()
    assert pl_justo_econ == pytest.approx(8.78, abs=0.01)      # PDF/B0: justo 8,78x


# ---------------------------------------------------------------------------
# Task 3 — ke_dossier (R4): duas rotas + prêmio de tamanho com critério + grade
# Aceitação: grade de Ke medida no B0 (h8_quant): 11%→10,60 | 14%→8,34 | 15%→7,73
# ---------------------------------------------------------------------------

def com_dossie_ke(inp):
    inp["premissas"]["dossie_ke"] = {
        "rota_paridade_us": {"componentes": {"rf_us": 0.042, "beta": 1.0, "erp": 0.055,
                                             "premio_pais": 0.035, "dif_inflacao": 0.0146},
                             "total": 0.1466},
        "rota_local": {"componentes": {"rf_local": 0.135, "beta": 1.0, "erp_local": 0.055},
                       "total": 0.19},
        "premio_tamanho": {"valor_pp": 0.0, "criterio": "liquidez adequada; sem prêmio (critério: ADTV > R$10mi)"},
        "escolhido": 0.14,
        "reconciliacao_hurdle": "hurdle 13% do usuário fica 1pp abaixo do Ke econômico central.",
    }


def test_ke_dossier_grade():
    res = rodar_fixture(FIX_TFCO4, com_dossie_ke)
    kd = res["ke_dossier"]
    grade = {g["ke"]: g for g in kd["grade_ke"]}
    assert grade[0.11]["central_ponderado"] == pytest.approx(10.60, abs=0.01)
    assert grade[0.14]["central_ponderado"] == pytest.approx(8.34, abs=0.01)
    assert grade[0.15]["central_ponderado"] == pytest.approx(7.73, abs=0.01)
    assert grade[0.11]["premio_pct"] == pytest.approx(41.4, abs=0.2)
    assert grade[0.15]["premio_pct"] == pytest.approx(93.9, abs=0.2)
    assert kd["rota_paridade_us"]["total"] == 0.1466
    assert kd["rota_local"]["total"] == 0.19
    assert kd["premio_tamanho"]["criterio"]


def test_ke_dossier_exige_duas_rotas_e_criterio():
    def mut(inp):
        com_dossie_ke(inp)
        del inp["premissas"]["dossie_ke"]["rota_local"]
    with pytest.raises(ValueError, match="dossie_ke"):
        rodar_fixture(FIX_TFCO4, mut)

    def mut2(inp):
        com_dossie_ke(inp)
        inp["premissas"]["dossie_ke"]["premio_tamanho"] = {"valor_pp": 0.09}  # sem critério
    with pytest.raises(ValueError, match="criterio|critério"):
        rodar_fixture(FIX_TFCO4, mut2)


def test_ke_dossier_ausente_nao_emite():
    res = rodar_fixture(FIX_TFCO4)
    assert "ke_dossier" not in res
