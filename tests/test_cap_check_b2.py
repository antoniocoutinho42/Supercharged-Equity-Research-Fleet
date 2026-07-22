# -*- coding: utf-8 -*-
"""B2 Task 4 — cap_check v2.1 (R5): confiança da banda SEPARADA da declarada e
ônus de sobrescrever para BAIXO (hoje inexistente — FASE A: FNV real com banda
sugerida 18-25, CAP base 17 e ZERO alertas)."""
import os
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "skills", "er-valuation"))
sys.dont_write_bytecode = True
import cap_check  # noqa: E402


def caso_fnv_like():
    """Evidência forte (âncora 14,3 + renovação + precedente 25a + 2 fontes →
    banda excepcional 18-25) com CAP base 17 ABAIXO da banda — o caso real FNV."""
    return {"fatos": {"duracao": {
                "consolidada": {"persistencia_spread_anos": 14.3, "fonte": "s"},
                "fontes_estruturais": [{"nome": "a", "evidencia": "x"},
                                       {"nome": "b", "evidencia": "y"}],
                "renovacao_moat": {"evidencia": "pipeline"},
                "precedentes": [{"nome": "p", "anos": 25}],
                "vetores_erosao": []}},
            "premissas": {"cenarios": {"bear": {"cap": 12}, "base": {"cap": 17},
                                       "bull": {"cap": 22}},
                          "cap_teto_defensavel": 25, "cap_confianca": "MEDIA",
                          "justificativa_cap": "x", "justificativa_cenarios": "y"}}


def test_versao_2_1():
    assert cap_check.VERSAO == "2.1"


def test_onus_para_baixo_fnv_like():
    r = cap_check.avaliar(caso_fnv_like())
    assert "excepcional" in r["banda_referencia"]
    assert any("ABAIXO da banda" in a for a in r["alertas"])   # a reforma R5: hoje zero alertas


def test_confianca_da_banda_separada():
    r = cap_check.avaliar(caso_fnv_like())
    cb = r["confianca_da_banda"]
    assert cb["nivel"] == "ALTA"                               # 4 pontos de evidência
    assert r["confianca_declarada"] == "MEDIA"                 # separada da declarada
    assert "separada" in cb["criterio"].lower() or "declarada" in cb["criterio"].lower()

    fraco = caso_fnv_like()
    fraco["fatos"]["duracao"]["fontes_estruturais"] = []
    fraco["fatos"]["duracao"]["renovacao_moat"] = {}
    fraco["fatos"]["duracao"]["precedentes"] = []
    r2 = cap_check.avaliar(fraco)
    assert r2["confianca_da_banda"]["nivel"] == "BAIXA"        # só a âncora = 1 ponto


def test_selftest_verde():
    r = subprocess.run([sys.executable,
                        os.path.join(REPO_ROOT, "skills", "er-valuation", "cap_check.py"),
                        "--selftest"], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
