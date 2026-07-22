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


# ---------------------------------------------------------------------------
# Task 5 — ebit_justo núcleo: cenários margem×giro, cadeia (1−t)(1−d), bridge, preço
# Razão da cadeia validada contra o JM medido no B0: C193/C187 = 4,200650.../6,429566...
# ---------------------------------------------------------------------------

JM_RATIO_EBITDA_NOPAT = 4.200650004719926 / 6.429566333754988   # (1−t)(1−d) do JM (B0, 1e-12)
T_OPER = 0.30                                                    # t do JM
D_JM = 1.0 - JM_RATIO_EBITDA_NOPAT / (1.0 - T_OPER)              # d implícito do JM


def com_operacional(inp, margens=None, giros=None, nopat_fy=100.0, claims=None,
                    wacc=0.14, com_ebitda=True):
    margens = margens or {"bear": 0.13, "base": 0.15, "bull": 0.17}
    giros = giros or {"bear": 1.5, "base": 1.6, "bull": 1.7}
    inp["fatos"]["nopat_fy_mi"] = nopat_fy
    if com_ebitda:
        inp["fatos"]["da_sobre_ebitda"] = D_JM
    inp["fatos"]["claims_bridge"] = claims if claims is not None else [
        {"nome": "divida_bruta", "valor_mi": -500.0, "fonte": "teste"},
        {"nome": "caixa_livre", "valor_mi": 50.0, "fonte": "teste"},
    ]
    inp["premissas"]["operacional"] = {
        "wacc": wacc, "fonte_wacc": "dossiê de Ke (teste)",
        "aliquota_operacional": T_OPER, "fonte_aliquotas": "teste",
        "cenarios": {n: {"margem_nopat": margens[n], "giro_noa": giros[n]}
                     for n in ("bear", "base", "bull")},
    }


def test_ebit_justo_nucleo():
    res = rodar_fixture(FIX_TFCO4, com_operacional)
    ej = res["ebit_justo"]
    cen_eq = carregar(FIX_TFCO4)["premissas"]["cenarios"]
    for n in ("bear", "base", "bull"):
        c = ej["cenarios"][n]
        roic = c["margem_nopat"] * c["giro_noa"]
        assert c["roic"] == pytest.approx(roic, abs=1e-9)
        # identidade do motor único: mesma pl_justo, inputs operacionais, trailing, de=nde=0
        esperado = engine.pl_justo(cen_eq[n]["g"], roic, cen_eq[n]["cap"], 0.14, 0.0, 0.0, 1.0)
        assert c["ev_nopat_justo"] == pytest.approx(esperado, abs=5e-5)   # JSON 4 casas
        assert c["ev_ebit_justo"] == pytest.approx(esperado * (1 - T_OPER), abs=1e-4)
        assert c["ev_ebitda_justo"] == pytest.approx(esperado * JM_RATIO_EBITDA_NOPAT, abs=1e-4)
    b = ej["cenarios"]["base"]
    assert b["rir_implicito_terminal"] == pytest.approx(0.12 / (0.15 * 1.6), abs=1e-6)
    assert ej["bridge"]["total_mi"] == pytest.approx(-450.0, abs=1e-9)
    assert b["ev_mi"] == pytest.approx(b["ev_nopat_justo"] * 100.0, abs=1e-2)
    assert b["equity_mi"] == pytest.approx(b["ev_mi"] - 450.0, abs=1e-2)
    acoes = res["meta"]["acoes_mi"]
    assert b["preco"] == pytest.approx(b["equity_mi"] / acoes, abs=1e-2)
    assert ej["ponderado_preco"] == pytest.approx(
        0.30 * ej["cenarios"]["bear"]["preco"] + 0.50 * b["preco"] + 0.20 * ej["cenarios"]["bull"]["preco"], abs=0.02)
    assert "trailing" in ej["convencao"]


def test_ebit_justo_recusa_g_maior_que_roic():
    def quebra(inp):
        com_operacional(inp, margens={"bear": 0.05, "base": 0.05, "bull": 0.05},
                        giros={"bear": 1.0, "base": 1.0, "bull": 1.0})  # roic 0,05 < g bull 0,17
    with pytest.raises(ValueError, match="roic|ROIC"):
        rodar_fixture(FIX_TFCO4, quebra)


def test_ebit_justo_ausente_nao_emite_bloco():
    res = rodar_fixture(FIX_TFCO4)
    assert "ebit_justo" not in res


# ---------------------------------------------------------------------------
# Task 6 — paridade (WARNING, condição 3), reverse e elasticidades operacionais
# Wedge de add-backs 1,1789 = 1,12/0,95 medido no B0 (h9h10 [5])
# ---------------------------------------------------------------------------

def com_op_paridade(inp, lpa_op=0.95):
    """Âncora operacional CONSISTENTE com a equity: margem×giro = ROE por cenário,
    wacc = Ke econ central (0,14), DE=NDE (bracket sem caixa), claims vazio,
    nopat_fy = lpa_op × ações → com lpa_op = LPA do motor, paridade EXATA."""
    inp["fatos"]["de"] = inp["fatos"]["nde"] = 0.196          # (DE−NDE)=0: bracket = payout puro
    acoes = inp["meta"]["acoes_mi"]
    com_operacional(inp,
                    margens={"bear": 0.18, "base": 0.22, "bull": 0.25},
                    giros={"bear": 1.0, "base": 1.0, "bull": 1.0},
                    nopat_fy=lpa_op * acoes, claims=[], wacc=0.14, com_ebitda=False)


def test_paridade_exata_nd_zero():
    res = rodar_fixture(FIX_TFCO4, com_op_paridade)
    par = res["ebit_justo"]["paridade"]
    assert par["preco_equity_central"] == res["economico"]["central_ponderado"]
    assert par["preco_op_ponderado"] == res["ebit_justo"]["ponderado_preco"]
    assert par["delta_pct"] == pytest.approx(0.0, abs=0.2)     # arredondamento a 2 casas nos preços
    assert par["status"] == "CONVERGE"
    assert par["warning"] is None


def test_paridade_wedge_add_backs():
    res = rodar_fixture(FIX_TFCO4, lambda inp: com_op_paridade(inp, lpa_op=1.12))
    par = res["ebit_justo"]["paridade"]
    razao = par["preco_op_ponderado"] / par["preco_equity_central"]
    assert razao == pytest.approx(1.12 / 0.95, abs=2e-3)       # 1,1789: isola exatamente o wedge
    assert par["status"] == "DIVERGE"
    assert par["warning"] == "PARIDADE_DIVERGENTE"
    assert par["nota_resolucao"] is None                       # condição 3: warning, nunca erro


def test_paridade_nota_resolucao_ecoada():
    def mut(inp):
        com_op_paridade(inp, lpa_op=1.12)
        inp["premissas"]["operacional"]["nota_paridade"] = (
            "Wedge de add-backs de R$29mi: a âncora operacional usa NOPAT reportado sem os "
            "ajustes do LPA; divergência esperada e documentada no dossiê.")
    res = rodar_fixture(FIX_TFCO4, mut)
    par = res["ebit_justo"]["paridade"]
    assert par["status"] == "DIVERGE" and par["warning"] == "PARIDADE_DIVERGENTE"
    assert "add-backs" in par["nota_resolucao"]


def test_reverse_operacional_round_trip():
    res = rodar_fixture(FIX_TFCO4, com_op_paridade)
    ej = res["ebit_justo"]
    rev = ej["reverse"]
    inp = carregar(FIX_TFCO4)
    base = inp["premissas"]["cenarios"]["base"]
    alvo = (14.99 * res["meta"]["acoes_mi"] - ej["bridge"]["total_mi"]) / (0.95 * res["meta"]["acoes_mi"])
    assert rev["alvo_ev_nopat_implicito"] == pytest.approx(alvo, abs=1e-3)
    # round-trip pelo CAP (sempre solúvel neste caso; ROIC isolado pode não alcançar o alvo
    # com o preço 79,7% acima do justo — degrade declarado, nunca número falso)
    got = engine.pl_justo(base["g"], 0.22 * 1.0, rev["cap_implicito_op"], 0.14, 0.0, 0.0, 1.0)
    assert got == pytest.approx(alvo, abs=2e-2)
    assert rev["wacc_implicito"] is not None
    assert "roic_implicito_no_preco" in rev                    # presente; None permitido com nota


def test_elasticidades_operacionais():
    res = rodar_fixture(FIX_TFCO4, com_operacional)
    el = res["ebit_justo"]["elasticidades"]
    for k in ("preco_base", "mais_1pp_margem", "mais_01x_giro", "mais_1a_cap", "menos_05pp_wacc"):
        assert k in el
    assert el["mais_1pp_margem"] > 0                           # spread positivo (roic 0,24 > wacc 0,14)
    assert set(el["experimento"]) == {"mais_1pp_margem", "mais_01x_giro", "mais_1a_cap", "menos_05pp_wacc"}
    assert el["alertas_sinal"] == []                           # nenhum sinal contraintuitivo neste caso
