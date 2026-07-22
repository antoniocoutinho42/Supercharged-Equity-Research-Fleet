# -*- coding: utf-8 -*-
"""Regressão FNV P3 — Task 1.0b (engine v2.1.0 -> v2.2.0, parâmetro m_terminal).

O engine empacotado em skills/er-valuation/ foi capturado ANTES do patch final
da sessão FNV (v2.1.0, ignora m_terminal). Este teste roda o engine real via
subprocess contra os inputs REAIS da sessão FNV e compara o resultados.json
gerado contra o oráculo (resultados (3).json) produzido pela sessão original
em v2.2.0. Enquanto o m_terminal não for reconstruído, este teste FALHA
(v2.1.0 dá hurdle.cenarios.ponderado=52.37 e sinais.economico=SOBREAVALIADO).

Fontes (somente leitura — NÃO commitadas nesta task; a fixture permanente
vem na Task 5.1):
  inputs: C:\\Claude\\Workflows\\Equity Research\\15.07.2025\\FNV\\inputs (1).yaml
  oráculo: C:\\Claude\\Workflows\\Equity Research\\15.07.2025\\FNV\\resultados (3).json
"""
import json
import os
import shutil
import subprocess
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENGINE_PATH = os.path.join(REPO_ROOT, "skills", "er-valuation", "engine.py")

FNV_DIR = r"C:\Claude\Workflows\Equity Research\15.07.2025\FNV"
FNV_INPUTS = os.path.join(FNV_DIR, "inputs (1).yaml")
FNV_ORACULO = os.path.join(FNV_DIR, "resultados (3).json")

pytestmark = pytest.mark.skipif(
    not (os.path.isfile(FNV_INPUTS) and os.path.isfile(FNV_ORACULO)),
    reason="fixtures FNV somente-leitura ausentes fora deste ambiente de dev",
)


def _tol(a, b, tol):
    assert a is not None, f"obtido None, esperado {b}"
    assert abs(a - b) <= tol, f"obtido {a}, esperado {b} (tol {tol})"


@pytest.fixture(scope="module")
def oraculo():
    with open(FNV_ORACULO, "r", encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture(scope="module")
def resultado_gerado(tmp_path_factory):
    tmp_path = tmp_path_factory.mktemp("fnv_m_terminal")
    inputs_copia = tmp_path / "inputs_fnv.yaml"
    shutil.copyfile(FNV_INPUTS, inputs_copia)
    out_dir = tmp_path / "saida_FNV"
    subprocess.run(
        [sys.executable, ENGINE_PATH, str(inputs_copia), "--out", str(out_dir)],
        check=True, capture_output=True, text=True,
    )
    with open(out_dir / "resultados.json", "r", encoding="utf-8") as fh:
        return json.load(fh)


def test_engine_versao_e_hash(resultado_gerado):
    # v3.0.0: correções sistêmicas pós-HG (R2/R3/R4/R5/R6) — núcleo matemático e
    # números do caso FNV/m_terminal INALTERADOS (só validação de inputs e blocos
    # novos); ver CHANGELOG no topo de engine.py.
    # B1 (v3.1.0): pino de versão relaxado para MAJOR — o critério de regressão
    # aprovado na FASE B é "chaves idênticas exceto engine.{versao,gerado_em}";
    # minors aditivos não podem quebrar este teste (única edição autorizada).
    major = str(resultado_gerado["engine"]["versao"]).split(".")[0]
    assert major == "3"
    assert resultado_gerado["engine"]["hash_inputs"] == "34e6680992b5b76e"


def test_hurdle_ponderado(resultado_gerado, oraculo):
    _tol(resultado_gerado["hurdle"]["cenarios"]["ponderado"],
         oraculo["hurdle"]["cenarios"]["ponderado"], 0.01)
    _tol(resultado_gerado["hurdle"]["cenarios"]["ponderado"], 116.46, 0.01)


def test_economico_central_ponderado(resultado_gerado, oraculo):
    _tol(resultado_gerado["economico"]["central_ponderado"],
         oraculo["economico"]["central_ponderado"], 0.01)
    _tol(resultado_gerado["economico"]["central_ponderado"], 188.49, 0.01)


def test_faixa_economica_ponderada(resultado_gerado, oraculo):
    faixa_g = resultado_gerado["economico"]["faixa_ponderada"]
    faixa_o = oraculo["economico"]["faixa_ponderada"]
    _tol(faixa_g[0], faixa_o[0], 0.01)
    _tol(faixa_g[1], faixa_o[1], 0.01)
    _tol(faixa_g[0], 175.05, 0.01)
    _tol(faixa_g[1], 203.18, 0.01)


def test_sinais_e_gate(resultado_gerado, oraculo):
    assert resultado_gerado["sinais"]["economico"] == "DENTRO_DA_FAIXA" == oraculo["sinais"]["economico"]
    assert resultado_gerado["gate"]["modo_recomendado"] == "PADRAO" == oraculo["gate"]["modo_recomendado"]


def test_validacao_multiplos_veredicto(resultado_gerado, oraculo):
    assert (resultado_gerado["validacao_multiplos"]["veredicto"]
            == "DIVERGE_MATERIAL" == oraculo["validacao_multiplos"]["veredicto"])


def test_reverse_bate_com_oraculo(resultado_gerado, oraculo):
    r_g, r_o = resultado_gerado["reverse"], oraculo["reverse"]
    for chave in ("g_implicito_hurdle_base", "cap_implicito_econ_base", "ke_implicito_cap_teto"):
        if r_o[chave] is None:
            assert r_g[chave] is None, f"reverse.{chave}: esperado None, obtido {r_g[chave]}"
        else:
            _tol(r_g[chave], r_o[chave], 0.01)


def test_ladder_bate_com_oraculo(resultado_gerado, oraculo):
    lad_g = {x["preco"]: x for x in resultado_gerado["ladder"]}
    lad_o = {x["preco"]: x for x in oraculo["ladder"]}
    assert set(lad_g.keys()) == set(lad_o.keys())
    for preco, item_o in lad_o.items():
        item_g = lad_g[preco]
        for chave in ("ke_implicito", "cap_implicito_econ", "delta_ate_econ_central_pct"):
            if item_o[chave] is None:
                assert item_g[chave] is None, f"ladder[{preco}].{chave}: esperado None, obtido {item_g[chave]}"
            else:
                _tol(item_g[chave], item_o[chave], 0.01)


def test_m_terminal_ecoado_por_cenario(resultado_gerado, oraculo):
    cen_g = resultado_gerado["cap"]["premissas_cenarios"]
    cen_o = oraculo["cap"]["premissas_cenarios"]
    for nome in ("bear", "base", "bull"):
        assert cen_g[nome]["m_terminal"] == cen_o[nome]["m_terminal"]
    assert resultado_gerado["cap"]["justificativa_m_terminal"] == oraculo["cap"]["justificativa_m_terminal"]
