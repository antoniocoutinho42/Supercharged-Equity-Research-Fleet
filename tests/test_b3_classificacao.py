# -*- coding: utf-8 -*-
"""B3 — ledger de classificação (schema + invariantes + ambíguas), congelamento no
snapshot e norma contábil (eco + trava H3×H13 no engine)."""
import os
import sys

import pytest
import yaml

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "skills", "er-relatorio"))
sys.path.insert(0, os.path.join(REPO_ROOT, "skills", "er-valuation"))
sys.dont_write_bytecode = True
import checar  # noqa: E402

from test_engine_b1 import FIX_TFCO4, rodar_fixture  # noqa: E402


def ledger_valido():
    """Mini-ledger coerente (números fictícios que FECHAM): A=1000 = P 400 + E 600."""
    return {
        "ticker": "TST", "fonte": "DFP 2025 (teste)", "data_balanco": "2025-12-31",
        "norma_contabil": {"regime": "IFRS_CPC", "leasing_pacote": "IFRS16_PURO",
                          "fonte_filing": "DFP/CVM", "ajustes_aplicados": []},
        "linhas": [
            {"rubrica": "Caixa e equivalentes", "valor": 200.0, "classe": "ATIVO_FINANCEIRO",
             "justificativa": "reserva de valor remunerada, não operacional", "fonte": "BP l.1"},
            {"rubrica": "Contas a receber", "valor": 300.0, "classe": "ATIVO_OPERACIONAL",
             "justificativa": "nasce da operação de vender o produto", "fonte": "BP l.2"},
            {"rubrica": "Imobilizado e intangível operacional", "valor": 500.0,
             "classe": "ATIVO_OPERACIONAL",
             "justificativa": "base física e contratual da operação", "fonte": "BP l.3"},
            {"rubrica": "Fornecedores", "valor": 150.0, "classe": "PASSIVO_OPERACIONAL",
             "justificativa": "crédito espontâneo da operação", "fonte": "BP l.4"},
            {"rubrica": "Arrendamentos", "valor": 250.0, "classe": "PASSIVO_FINANCEIRO",
             "justificativa": "custa juros; existiria só com financiamento", "fonte": "BP l.5",
             "ambigua": False, "claim_bridge": "divida"},
            {"rubrica": "Patrimônio líquido", "valor": 600.0, "classe": "EQUITY",
             "justificativa": "claim residual dos acionistas", "fonte": "BP l.6"},
        ],
        "totais_reportados": {"ativo_total": 1000.0, "passivo_total": 400.0,
                              "equity_total": 600.0},
    }


def roda_classificacao(tmp_path, ledger):
    ns = str(tmp_path)
    with open(os.path.join(ns, "classificacao.yaml"), "w", encoding="utf-8") as f:
        yaml.safe_dump(ledger, f, allow_unicode=True)
    faltas, avisos = [], []
    checar.checar_classificacao(ns, faltas, avisos)
    return faltas, avisos


def test_ledger_valido_sem_faltas(tmp_path):
    faltas, avisos = roda_classificacao(tmp_path, ledger_valido())
    assert faltas == []
    assert not any("ambígua" in a or "ambigua" in a for a in avisos)


def test_ledger_ausente_nao_reprova(tmp_path):
    faltas, avisos = [], []
    checar.checar_classificacao(str(tmp_path), faltas, avisos)
    assert faltas == [] and avisos == []            # gating por presença: análises antigas intactas


def test_invariante_quebrada_e_falta(tmp_path):
    led = ledger_valido()
    led["linhas"][1]["valor"] = 350.0               # AO+AF = 1050 != ativo_total 1000
    faltas, _ = roda_classificacao(tmp_path, led)
    assert any("ativo" in f.lower() for f in faltas)


def test_linha_ambigua_vira_aviso_ao_auditor(tmp_path):
    led = ledger_valido()
    led["linhas"][4]["ambigua"] = True
    faltas, avisos = roda_classificacao(tmp_path, led)
    assert faltas == []
    assert any("Auditor" in a for a in avisos)


def test_schema_recusa_classe_invalida(tmp_path):
    led = ledger_valido()
    led["linhas"][0]["classe"] = "ATIVO_MISTERIOSO"
    faltas, _ = roda_classificacao(tmp_path, led)
    assert any("classificacao.yaml" in f for f in faltas)


def test_snapshot_congela_classificacao():
    src = open(os.path.join(REPO_ROOT, "scripts", "snapshot.py"), encoding="utf-8").read()
    assert '"classificacao.yaml"' in src            # tupla de congelados opcionais


def test_engine_norma_contabil_eco_e_trava():
    def mut(inp):
        inp["fatos"]["norma_contabil"] = {"regime": "US_GAAP", "leasing_pacote": "ASC842_NATIVO",
                                          "fonte_filing": "10-K"}
    res = rodar_fixture(FIX_TFCO4, mut)
    assert res["norma_contabil"]["regime"] == "US_GAAP"

    def mut2(inp):                                   # pacote não-nativo SEM ajuste declarado
        inp["fatos"]["norma_contabil"] = {"regime": "US_GAAP", "leasing_pacote": "IFRS16_PURO",
                                          "fonte_filing": "10-K"}
    res2 = rodar_fixture(FIX_TFCO4, mut2)
    assert any("PACOTE_LEASING_NAO_NATIVO" in a for a in res2["validacao"]["avisos"])

    def mut3(inp):                                   # com ajuste declarado: sem aviso
        inp["fatos"]["norma_contabil"] = {"regime": "US_GAAP", "leasing_pacote": "IFRS16_PURO",
                                          "fonte_filing": "10-K",
                                          "ajustes_aplicados": ["capitalização estilo IFRS-16 dos op-leases"]}
    res3 = rodar_fixture(FIX_TFCO4, mut3)
    assert not any("PACOTE_LEASING_NAO_NATIVO" in a for a in res3["validacao"]["avisos"])

    def mut4(inp):
        inp["fatos"]["norma_contabil"] = {"regime": "MARTE_GAAP", "leasing_pacote": "IFRS16_PURO"}
    with pytest.raises(ValueError, match="norma_contabil"):
        rodar_fixture(FIX_TFCO4, mut4)


def test_engine_norma_ausente_nao_emite():
    res = rodar_fixture(FIX_TFCO4)
    assert "norma_contabil" not in res
