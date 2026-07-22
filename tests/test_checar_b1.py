# -*- coding: utf-8 -*-
"""B1 Task 8 — passada única de contrato: checar (gating por presença v3.1 +
paridade como AVISO, condição 3) e compor (seções novas + humano(), linter-safe)."""
import copy
import json
import os
import shutil
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "skills", "er-relatorio"))
sys.path.insert(0, os.path.join(REPO_ROOT, "skills", "er-valuation"))
sys.dont_write_bytecode = True
import checar  # noqa: E402
import compor  # noqa: E402

from test_engine_b1 import (FIX_TFCO4, carregar, com_operacional,  # noqa: E402
                            com_reformulado, rodar_fixture)

FIX_METODO = os.path.join(REPO_ROOT, "tests", "fixtures", "fnv", "metodo.yaml")


def res_completo():
    def mut(inp):
        com_reformulado(inp)
        com_operacional(inp, nopat_fy=1.12 * inp["meta"]["acoes_mi"])  # paridade DIVERGE (wedge)
    return rodar_fixture(FIX_TFCO4, mut)


def monta_ns(tmp_path, res):
    ns = str(tmp_path)
    with open(os.path.join(ns, "valuation.md"), "w", encoding="utf-8") as f:
        f.write("Memorando de teste, sem chaves citadas.\n")
    shutil.copy(FIX_METODO, os.path.join(ns, "metodo.yaml"))
    saida = os.path.join(ns, "saida_TST")
    os.makedirs(saida, exist_ok=True)
    with open(os.path.join(saida, "resultados.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False)
    return ns


def roda_checar(tmp_path, res):
    ns = monta_ns(tmp_path, res)
    faltas, avisos = [], []
    checar.checar_valuation(ns, faltas, avisos)
    return faltas, avisos


def test_paridade_diverge_sem_nota_e_aviso_nao_falta(tmp_path):
    res = res_completo()
    res["engine"]["versao"] = "3.1.0"
    assert res["ebit_justo"]["paridade"]["status"] == "DIVERGE"
    assert res["ebit_justo"]["paridade"]["nota_resolucao"] is None
    faltas, avisos = roda_checar(tmp_path, res)
    assert not any("paridade" in f.lower() for f in faltas)      # condição 3: nunca falta
    assert any("paridade" in a.lower() for a in avisos)          # mas o aviso existe


def test_ebit_justo_presente_sem_subchave_e_falta(tmp_path):
    res = res_completo()
    res["engine"]["versao"] = "3.1.0"
    del res["ebit_justo"]["historia_numeros"]
    faltas, _ = roda_checar(tmp_path, res)
    assert any("historia_numeros" in f for f in faltas)


def test_sensibilidade_phi_obrigatoria_no_v31(tmp_path):
    res = res_completo()
    res["engine"]["versao"] = "3.1.0"
    del res["sensibilidade_phi"]
    faltas, _ = roda_checar(tmp_path, res)
    assert any("sensibilidade_phi" in f for f in faltas)


def test_namespace_v30_sem_blocos_novos_nao_reprova(tmp_path):
    res = rodar_fixture(FIX_TFCO4)                               # sem blocos novos
    res["engine"]["versao"] = "3.0.0"
    del res["sensibilidade_phi"]                                 # como um run v3.0.0 real
    faltas, _ = roda_checar(tmp_path, res)
    assert faltas == []                                          # gating nunca retroativo


def test_humano_cobre_enums_novos():
    for enum in ("EQUITY_OK", "GATE_DISPARA", "OPERACIONAL", "PARIDADE_DIVERGENTE",
                 "DIVERGE", "PROVISORIO_N3", "FLEV_CRUZA_SINAL", "NBC_INSTAVEL",
                 "ND_IMATERIAL"):
        assert compor.humano(enum) != enum, f"humano() sem entrada para {enum}"


def test_contrato_b2_gating(tmp_path):
    from test_engine_b2 import com_central_neutro, com_dossie_ke

    def mut(inp):
        com_central_neutro(inp)
        com_dossie_ke(inp)

    res = rodar_fixture(FIX_TFCO4, mut)
    res["engine"]["versao"] = "3.2.0"
    del res["central_neutro"]["robustez_conjunta"]
    faltas, _ = roda_checar(tmp_path, res)
    assert any("robustez_conjunta" in f for f in faltas)

    res2 = rodar_fixture(FIX_TFCO4, mut)
    res2["engine"]["versao"] = "3.2.0"
    del res2["validacao_multiplos"]["implicitos"]
    faltas2, _ = roda_checar(tmp_path, res2)
    assert any("implicitos" in f for f in faltas2)

    res3 = rodar_fixture(FIX_TFCO4)
    res3["engine"]["versao"] = "3.1.0"                          # run pré-B2 (phi existe; implicitos não)
    del res3["validacao_multiplos"]["implicitos"]
    faltas3, _ = roda_checar(tmp_path, res3)
    assert not any("implicitos" in f for f in faltas3)          # gating nunca retroativo

    res4 = rodar_fixture(FIX_TFCO4, mut)
    res4["engine"]["versao"] = "3.2.0"
    del res4["ke_dossier"]["grade_ke"]
    faltas4, _ = roda_checar(tmp_path, res4)
    assert any("grade_ke" in f for f in faltas4)


def test_secoes_b2_linter_safe():
    from test_engine_b2 import com_central_neutro, com_dossie_ke

    def mut(inp):
        com_central_neutro(inp)
        com_dossie_ke(inp)
    res = rodar_fixture(FIX_TFCO4, mut)
    dados = {"res": res, "inputs": carregar(FIX_TFCO4)}
    secoes = [compor.secao_central_neutro(dados), compor.secao_ke_dossier(dados),
              compor.secao_implicitos(dados)]
    for texto in secoes:
        assert texto and len(texto) > 80
        for nome, padrao in checar._LINTER_CORPO:
            hits = padrao.findall(texto)
            assert not hits, f"linter '{nome}' pegaria no corpo: {hits[:3]}"


def test_secoes_novas_linter_safe():
    res = res_completo()
    inputs = carregar(FIX_TFCO4)
    dados = {"res": res, "inputs": inputs}
    secoes = [compor.secao_reformulado(dados), compor.secao_ebit_justo(dados),
              compor.secao_phi(dados)]
    for texto in secoes:
        assert texto and len(texto) > 100
        for nome, padrao in checar._LINTER_CORPO:
            hits = padrao.findall(texto)
            assert not hits, f"linter '{nome}' pegaria no corpo: {hits[:3]}"
    assert "história" in secoes[1].lower() or "História" in secoes[1]