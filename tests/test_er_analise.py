"""Testes de forma e ancoras de conteudo da skill master er-analise (Task 7)."""

from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parent.parent
SKILL = RAIZ / "skills" / "er-analise"


def _frontmatter(p):
    texto = p.read_text(encoding="utf-8")
    assert texto.startswith("---")
    fm = yaml.safe_load(texto.split("---")[1])
    assert set(fm) == {"name", "description"}
    return fm, texto


def test_skill_analise():
    fm, texto = _frontmatter(SKILL / "SKILL.md")
    assert fm["name"] == "er-analise"
    for ancora in ["F0", "F11", "somente valuation", "hurdle", "nunca", "default",
                   "notas.md", "grill-me", "MATERIAL", "market-implied", "memória"]:
        assert ancora.lower() in texto.lower(), ancora
    # invariantes textuais que NAO podem faltar (Secao 9 do desenho):
    for regra in ["nunca tem default", "evidência a verificar", "nunca recalibra"]:
        assert regra.lower() in texto.lower(), regra


def test_references_existem_e_referenciadas():
    _, texto = _frontmatter(SKILL / "SKILL.md")
    for ref in ["fases.md", "qualitativa-e-financeira.md", "memoria-e-p2.md"]:
        assert (SKILL / "references" / ref).exists(), ref
        assert ref in texto, f"SKILL.md nao aponta references/{ref}"


def test_fases_cobrem_workflow():
    texto = (SKILL / "references" / "fases.md").read_text(encoding="utf-8")
    for fase in ["F0", "F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F10", "F11"]:
        assert f"## {fase} " in texto or f"## {fase}\n" in texto or f"## {fase}–" in texto, fase
    # ordem canonica de calibracao e sequencia do engine
    for ancora in ["Normalize", "ROE1", "g_T", "SUITE PASS", "label_mode", "checar_relatorio",
                   "memoria.py", "SUPOSIÇÃO", "24h"]:
        assert ancora in texto, ancora
    # correcao 9c: serie curta enfraquece a ancora historica na justificativa
    assert "âncora histórica" in texto


def test_memoria_e_p2():
    texto = (SKILL / "references" / "memoria-e-p2.md").read_text(encoding="utf-8")
    for ancora in ["materialidade", "O que mudou", "--licoes", "--sintese",
                   "regenerar", "PROIBIDO", "150 linhas"]:
        assert ancora in texto, ancora


def test_qualitativa_financeira():
    texto = (SKILL / "references" / "qualitativa-e-financeira.md").read_text(encoding="utf-8")
    for ancora in ["DuPont", "FCFE", "FATO", "HIPÓTESE", "duração", "n2", "P/L histórico",
                   "insights", "causal"]:
        assert ancora.lower() in texto.lower(), ancora
