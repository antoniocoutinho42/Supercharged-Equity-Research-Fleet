# -*- coding: utf-8 -*-
"""Testes de forma/estrutura das skills de domínio A: er-guardrails e
er-dossie (Task 2.2a).

Mesmo espírito de tests/test_kernel_skill.py: estas skills são conteúdo
(porte de mandato), não código com lógica própria para TDD clássico. Os
testes verificam a FORMA exigida pelo brief (task-2.2a-brief.md): frontmatter
válido, orçamento de palavras (+100 de folga sobre o alvo), a heurística
anti-resumo da description, e a presença/conteúdo mínimo dos references de
er-dossie.
"""
import os

import yaml

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS_DIR = os.path.join(REPO_ROOT, "skills")

GUARDRAILS_MD = os.path.join(SKILLS_DIR, "er-guardrails", "SKILL.md")
DOSSIE_DIR = os.path.join(SKILLS_DIR, "er-dossie")
DOSSIE_MD = os.path.join(DOSSIE_DIR, "SKILL.md")
DOSSIE_REFS = os.path.join(DOSSIE_DIR, "references")

# Alvos do brief + 100 palavras de folga.
LIMITE_GUARDRAILS = 450 + 100
LIMITE_DOSSIE = 550 + 100


def _ler(caminho):
    with open(caminho, "r", encoding="utf-8") as fh:
        return fh.read()


def _frontmatter(texto):
    partes = texto.split("---")
    assert len(partes) >= 3, "SKILL.md deve ter frontmatter delimitado por '---'"
    return yaml.safe_load(partes[1])


# ---------------------------------------------------------------------------
# Existência e frontmatter
# ---------------------------------------------------------------------------

def test_skills_md_existem():
    assert os.path.isfile(GUARDRAILS_MD), f"SKILL.md ausente em {GUARDRAILS_MD}"
    assert os.path.isfile(DOSSIE_MD), f"SKILL.md ausente em {DOSSIE_MD}"


def test_frontmatter_name_correto():
    fm_guardrails = _frontmatter(_ler(GUARDRAILS_MD))
    assert fm_guardrails.get("name") == "er-guardrails"

    fm_dossie = _frontmatter(_ler(DOSSIE_MD))
    assert fm_dossie.get("name") == "er-dossie"


def test_frontmatter_description_nao_vazia():
    for caminho in (GUARDRAILS_MD, DOSSIE_MD):
        fm = _frontmatter(_ler(caminho))
        descricao = fm.get("description")
        assert isinstance(descricao, str) and descricao.strip(), (
            f"{caminho}: description ausente ou vazia no frontmatter"
        )


def test_description_e_gatilho_nao_resumo_de_gates():
    """Heurística anti-resumo: a description é condição de disparo, nunca o
    passo a passo dos gates em sequência (sem seta, sem cadeia G1->G2->G3)."""
    for caminho in (GUARDRAILS_MD, DOSSIE_MD):
        fm = _frontmatter(_ler(caminho))
        descricao = fm.get("description", "")
        assert "→" not in descricao, f"{caminho}: description não deve usar seta de fluxo"
        # não é uma cadeia de 2+ gates em sequência (ex.: "G1, G2, G3" ou "G1 -> G2")
        gates_citados = [g for g in ("G1,", "G2,", "G3,", "G1 e G2", "G2 e G3") if g in descricao]
        assert not gates_citados, (
            f"{caminho}: description não deve listar gates em sequência: {gates_citados}"
        )


# ---------------------------------------------------------------------------
# Orçamento de palavras
# ---------------------------------------------------------------------------

def test_er_guardrails_respeita_orcamento_de_palavras():
    n_palavras = len(_ler(GUARDRAILS_MD).split())
    assert n_palavras <= LIMITE_GUARDRAILS, (
        f"er-guardrails/SKILL.md tem {n_palavras} palavras, acima do limite de "
        f"{LIMITE_GUARDRAILS} (alvo é <= 450; ver task-2.2a-brief.md)"
    )


def test_er_dossie_respeita_orcamento_de_palavras():
    n_palavras = len(_ler(DOSSIE_MD).split())
    assert n_palavras <= LIMITE_DOSSIE, (
        f"er-dossie/SKILL.md tem {n_palavras} palavras, acima do limite de "
        f"{LIMITE_DOSSIE} (alvo é <= 550; ver task-2.2a-brief.md)"
    )


# ---------------------------------------------------------------------------
# references/ de er-dossie
# ---------------------------------------------------------------------------

def test_references_de_er_dossie_existem_e_nao_vazios():
    for nome in ("pilares.md", "ficha-e-fatos.md", "moat-duracao.md", "delta.md"):
        caminho = os.path.join(DOSSIE_REFS, nome)
        assert os.path.isfile(caminho), f"reference ausente: {caminho}"
        conteudo = _ler(caminho)
        assert conteudo.strip(), f"reference vazio: {caminho}"


def test_moat_duracao_contem_persistencia_e_taxa_base():
    conteudo = _ler(os.path.join(DOSSIE_REFS, "moat-duracao.md"))
    assert "persistência" in conteudo
    assert "taxa-base" in conteudo


def test_pilares_contem_pilar_6():
    conteudo = _ler(os.path.join(DOSSIE_REFS, "pilares.md"))
    assert "Pilar 6" in conteudo


def test_skill_md_er_dossie_referencia_os_quatro_references():
    texto = _ler(DOSSIE_MD)
    assert "references/pilares.md" in texto
    assert "references/ficha-e-fatos.md" in texto
    assert "references/moat-duracao.md" in texto
    assert "references/delta.md" in texto


# ---------------------------------------------------------------------------
# Conteúdo mínimo de er-guardrails (G1.5, coarse, 1.4)
# ---------------------------------------------------------------------------

def test_er_guardrails_menciona_g1_5_coarse_e_limiar():
    texto = _ler(GUARDRAILS_MD)
    assert "G1.5" in texto
    assert "coarse" in texto
    assert "1.4" in texto
