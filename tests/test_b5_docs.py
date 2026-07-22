# -*- coding: utf-8 -*-
"""B5 — aceites duros de documentação da aprovação da FASE B (2026-07-21):
m_terminal + φ com exclusão mútua DOCUMENTADOS na SKILL; limiares H7 provisórios
com instrução de recalibração; paridade não-bloqueante; nomenclatura
'franchise-fade' eliminada; rótulos de versão corrigidos; mandatos atualizados."""
import json
import os

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _ler(*partes):
    return open(os.path.join(REPO_ROOT, *partes), encoding="utf-8").read()


def test_skill_documenta_m_terminal_e_phi_exclusao_mutua():
    s = _ler("skills", "er-valuation", "SKILL.md")
    assert "m_terminal" in s
    assert "sensibilidade_phi" in s
    assert "exclusão mútua" in s.lower() or "exclusao mutua" in s.lower()


def test_skill_documenta_gates_provisorios_e_paridade():
    s = _ler("skills", "er-valuation", "SKILL.md")
    assert "PROVISÓRIO" in s.upper() or "PROVISORIO" in s.upper()
    assert "recalibra" in s.lower()                            # condição 7
    assert "paridade" in s.lower()
    assert "não bloqueia" in s.lower() or "nao bloqueia" in s.lower()   # condição 3


def test_nomenclatura_franchise_fade_eliminada():
    assert "franchise-fade" not in _ler("skills", "er-valuation", "SKILL.md")
    assert "franchise-fade" not in _ler("skills", "er-valuation", "engine.py")


def test_rotulos_de_versao():
    s = _ler("skills", "er-valuation", "SKILL.md")
    assert "valuation-engine v3" in s and "valuation-engine v2 " not in s
    assert "valuation-engine v3" in _ler("skills", "er-valuation", "inputs_exemplo_vrsk.yaml")
    plugin = json.loads(_ler(".claude-plugin", "plugin.json"))
    assert plugin["version"] == "2.1.0"
    assert "v3.2.0" in _ler("README.md")


def test_mandatos_citam_blocos_novos():
    analista = _ler("agents", "analista.md")
    assert "classificacao.yaml" in analista and "reformulad" in analista.lower()
    modelador = _ler("agents", "modelador.md")
    assert "margem" in modelador.lower() and "giro" in modelador.lower()
    assert "dossiê de ke" in modelador.lower() or "dossie de ke" in modelador.lower() \
        or "dossie_ke" in modelador.lower()
    auditor = _ler("agents", "auditor.md")
    assert "paridade" in auditor.lower()
    assert "ambígua" in auditor.lower() or "ambigua" in auditor.lower()


def test_mandatos_dentro_do_teto():
    for nome in ("analista", "modelador", "auditor"):
        tam = os.path.getsize(os.path.join(REPO_ROOT, "agents", f"{nome}.md"))
        assert tam <= 4096, f"{nome}.md com {tam} bytes"
