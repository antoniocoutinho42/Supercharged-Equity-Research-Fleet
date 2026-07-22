# -*- coding: utf-8 -*-
"""B4 — exercício operacional completo TFCO4 (condições 1 e 2 da aprovação).
Trava os números citados em docs/impacto_TFCO4.md: regressão do contrato antigo,
modo completo (todos os blocos v3.2) e as variantes de decomposição POR CAUSA."""
import os
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "skills", "er-valuation"))
sys.dont_write_bytecode = True
import engine  # noqa: E402

from test_engine_b1 import FIX_TFCO4, rodar_fixture  # noqa: E402

FIX_B4 = os.path.join(REPO_ROOT, "tests", "fixtures", "tfco4", "inputs_b4_completo.yaml")


def test_regressao_contrato_antigo_sob_v32():
    """Inputs do contrato antigo (inputs_b1) sob o engine novo: TODAS as chaves
    antigas idênticas (critério aprovado: exceto engine.{versao,gerado_em})."""
    res = rodar_fixture(FIX_TFCO4)
    assert res["economico"]["central_ponderado"] == 8.34
    assert res["sinais"]["premio_sobre_econ_central_pct"] == 79.7
    assert res["reverse"]["cap_implicito_econ_base"] == 42.8631
    assert res["hurdle"]["cenarios"]["ponderado"] == 9.01
    assert res["gate"]["modo_recomendado"] == "SUMARIA"
    assert res["sensibilidade_phi"]["aplicavel"] is True       # único bloco novo sempre emitido


def test_b4_completo():
    res = rodar_fixture(FIX_B4)
    # baseline intacto mesmo com todos os blocos novos presentes
    assert res["economico"]["central_ponderado"] == 8.34
    assert res["hurdle"]["cenarios"]["ponderado"] == 9.01
    # âncora operacional: convergência independente das âncoras
    ej = res["ebit_justo"]
    assert ej["ponderado_preco"] == pytest.approx(8.15, abs=0.01)
    par = ej["paridade"]
    assert par["delta_pct"] == pytest.approx(-2.3, abs=0.1)
    assert par["status"] == "CONVERGE" and par["warning"] is None
    # reversa operacional: o que o preço exige
    rev = ej["reverse"]
    assert rev["alvo_ev_nopat_implicito"] == pytest.approx(15.5793, abs=1e-3)
    assert rev["roic_implicito_no_preco"] is None              # nem rentabilidade extrema alcança
    assert rev["cap_implicito_op"] == pytest.approx(33.9, abs=0.1)
    assert rev["wacc_implicito"] == pytest.approx(0.062, abs=1e-3)
    # gates H7 na série 2020-2025 (com FY2025 reconstruído)
    g7 = res["fatos_reformulado"]["gates_aplicabilidade"]
    assert g7["ancora_equity"] == "EQUITY_OK"
    assert [f["codigo"] for f in g7["flags"]] == ["FLEV_CRUZA_SINAL"]
    s25 = res["fatos_reformulado"]["serie"][-1]
    assert s25["roic"] == pytest.approx(0.2636, abs=1e-3)
    assert res["fatos_reformulado"]["diagnostico"]["roiic_acumulado"] == pytest.approx(0.2805, abs=1e-3)
    # central neutro (R2) — números do B0 reproduzidos no exercício completo
    cn = res["central_neutro"]
    assert cn["premio_econ_pct"] == pytest.approx(41.7, abs=0.15)
    assert cn["premio_hurdle_pct"] == pytest.approx(47.5, abs=0.15)
    assert cn["gate_recomputado"]["modo"] == "PADRAO"
    # implícitos dos múltiplos (R3)
    imp = res["validacao_multiplos"]["implicitos"]
    assert imp["historico_proprio"]["cap_implicito"] == pytest.approx(74.3, abs=0.2)
    assert imp["historico_proprio"]["g_implicito"] == pytest.approx(0.3365, abs=1e-3)
    assert imp["historico_proprio"]["ke_implicito"] == pytest.approx(0.0414, abs=1e-3)
    assert imp["comparaveis"]["cap_implicito"] == pytest.approx(1.9, abs=0.1)
    assert imp["comparaveis"]["g_implicito"] is None
    assert imp["comparaveis"]["ke_implicito"] == pytest.approx(0.2102, abs=1e-3)
    # grade de Ke (R4) e φ (H11)
    grade = {g["ke"]: g["central_ponderado"] for g in res["ke_dossier"]["grade_ke"]}
    assert grade[0.11] == pytest.approx(10.60, abs=0.01) and grade[0.15] == pytest.approx(7.73, abs=0.01)
    phi = {g["phi"]: g["premio_vs_preco_pct"] for g in res["sensibilidade_phi"]["grid"]}
    assert phi[1.0] == pytest.approx(42.9, abs=0.1)
    # norma contábil ecoada; nenhum aviso operacional pendente
    assert res["norma_contabil"]["leasing_pacote"] == "IFRS16_PURO"
    assert ej["avisos"] == []


def test_b4_decomposicao_por_causa():
    """Condição 2: variação de cada âncora atribuída por causa."""
    # (ii) ROE derivado pela ponte (0,2548 medido na série 2024) em vez do input livre 0,22
    def roe_ponte(inp):
        inp["premissas"]["cenarios"]["base"]["roe"] = 0.2548
    res2 = rodar_fixture(FIX_B4, roe_ponte)
    assert res2["economico"]["central_ponderado"] == pytest.approx(8.40, abs=0.01)
    assert res2["sinais"]["premio_sobre_econ_central_pct"] == pytest.approx(78.5, abs=0.1)
    # (iii) base de lucro: LPA ajustado 1,12 (aux do PDF, re-executada no B0)
    def lpa_112(inp):
        inp["fatos"]["lpa_ajustado_fy"] = 1.12
    res3 = rodar_fixture(FIX_B4, lpa_112)
    assert res3["economico"]["central_ponderado"] == pytest.approx(9.83, abs=0.01)
    assert res3["sinais"]["premio_sobre_econ_central_pct"] == pytest.approx(52.5, abs=0.1)
    assert res3["sinais"]["premio_sobre_hurdle_pct"] == pytest.approx(41.1, abs=0.1)
    # com a base ajustada, a paridade contra a âncora operacional reabre exatamente o wedge
    par3 = res3["ebit_justo"]["paridade"]
    assert par3["delta_pct"] == pytest.approx(-17.1, abs=0.2)
    assert par3["status"] == "DIVERGE"
