# -*- coding: utf-8 -*-
"""Testes de forma/estrutura das skills de domínio B: er-auditoria e
er-portfolio (Task 2.2b).

Mesmo espírito de tests/test_skills_dominio_a.py: estas skills são
conteúdo (porte de mandato), não código com lógica própria para TDD
clássico. Os testes verificam a FORMA exigida pelo brief
(task-2.2b-brief.md): frontmatter válido, orçamento de palavras (+100 de
folga sobre o alvo), a heurística anti-resumo da description, e a
presença/conteúdo mínimo dos references de er-auditoria.
"""
import os
import re

import yaml

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS_DIR = os.path.join(REPO_ROOT, "skills")

AUDITORIA_DIR = os.path.join(SKILLS_DIR, "er-auditoria")
AUDITORIA_MD = os.path.join(AUDITORIA_DIR, "SKILL.md")
AUDITORIA_REFS = os.path.join(AUDITORIA_DIR, "references")
ESCOPOS_MD = os.path.join(AUDITORIA_REFS, "escopos.md")
RECOMPUTO_MD = os.path.join(AUDITORIA_REFS, "recomputo-referencia.md")

PORTFOLIO_DIR = os.path.join(SKILLS_DIR, "er-portfolio")
PORTFOLIO_MD = os.path.join(PORTFOLIO_DIR, "SKILL.md")

# Alvos do brief + 100 palavras de folga.
LIMITE_AUDITORIA = 550 + 100
LIMITE_PORTFOLIO = 500 + 100

# Sequências de gates em cadeia que a heurística anti-resumo proíbe (a
# description é gatilho de acionamento, não o passo a passo dos gates).
# Referências isoladas a um único gate entre parênteses, como as exigidas
# pelo brief ("(G4)", "(G5)", "(G6)"), são permitidas.
SEQUENCIAS_DE_GATES_PROIBIDAS = (
    "G4 e G5", "G4, G5", "G4->G5", "G4 -> G5",
    "G5 e G6", "G5, G6", "G5->G6", "G5 -> G6",
    "G4 e G6", "G4, G6",
)


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
    assert os.path.isfile(AUDITORIA_MD), f"SKILL.md ausente em {AUDITORIA_MD}"
    assert os.path.isfile(PORTFOLIO_MD), f"SKILL.md ausente em {PORTFOLIO_MD}"


def test_frontmatter_name_correto():
    fm_auditoria = _frontmatter(_ler(AUDITORIA_MD))
    assert fm_auditoria.get("name") == "er-auditoria"

    fm_portfolio = _frontmatter(_ler(PORTFOLIO_MD))
    assert fm_portfolio.get("name") == "er-portfolio"


def test_frontmatter_description_nao_vazia():
    for caminho in (AUDITORIA_MD, PORTFOLIO_MD):
        fm = _frontmatter(_ler(caminho))
        descricao = fm.get("description")
        assert isinstance(descricao, str) and descricao.strip(), (
            f"{caminho}: description ausente ou vazia no frontmatter"
        )


def test_description_e_gatilho_nao_resumo_de_gates():
    """Heurística anti-resumo: a description é condição de disparo, nunca o
    passo a passo dos gates em sequência (sem seta, sem cadeia G4->G5->G6).
    Menções isoladas a um único gate entre parênteses são o formato exigido
    pelo brief e não contam como sequência."""
    for caminho in (AUDITORIA_MD, PORTFOLIO_MD):
        fm = _frontmatter(_ler(caminho))
        descricao = fm.get("description", "")
        assert "→" not in descricao, f"{caminho}: description não deve usar seta de fluxo"
        sequencias = [s for s in SEQUENCIAS_DE_GATES_PROIBIDAS if s in descricao]
        assert not sequencias, (
            f"{caminho}: description não deve listar gates em sequência: {sequencias}"
        )


# ---------------------------------------------------------------------------
# Orçamento de palavras
# ---------------------------------------------------------------------------

def test_er_auditoria_respeita_orcamento_de_palavras():
    n_palavras = len(_ler(AUDITORIA_MD).split())
    assert n_palavras <= LIMITE_AUDITORIA, (
        f"er-auditoria/SKILL.md tem {n_palavras} palavras, acima do limite de "
        f"{LIMITE_AUDITORIA} (alvo é <= 550; ver task-2.2b-brief.md)"
    )


def test_er_portfolio_respeita_orcamento_de_palavras():
    n_palavras = len(_ler(PORTFOLIO_MD).split())
    assert n_palavras <= LIMITE_PORTFOLIO, (
        f"er-portfolio/SKILL.md tem {n_palavras} palavras, acima do limite de "
        f"{LIMITE_PORTFOLIO} (alvo é <= 500; ver task-2.2b-brief.md)"
    )


# ---------------------------------------------------------------------------
# references/ de er-auditoria (er-portfolio não tem references, por design)
# ---------------------------------------------------------------------------

def test_references_de_er_auditoria_existem_e_nao_vazios():
    for caminho in (ESCOPOS_MD, RECOMPUTO_MD):
        assert os.path.isfile(caminho), f"reference ausente: {caminho}"
        conteudo = _ler(caminho)
        assert conteudo.strip(), f"reference vazio: {caminho}"


def test_escopos_contem_os_cinco_escopos_e_runs():
    conteudo = _ler(ESCOPOS_MD)
    for palavra_chave in ("calculo", "evidencia", "especificacao", "robustez", "decisao"):
        assert palavra_chave in conteudo, f"escopos.md: palavra-chave ausente: {palavra_chave}"
    assert "runs/" in conteudo


def test_recomputo_referencia_contem_ddm_tolerancia_e_m_terminal():
    conteudo = _ler(RECOMPUTO_MD)
    assert "DDM" in conteudo
    assert "1e-6" in conteudo
    assert ("m_terminal" in conteudo) or ("M*" in conteudo)


def test_skill_md_er_auditoria_referencia_os_dois_references():
    texto = _ler(AUDITORIA_MD)
    assert "references/escopos.md" in texto
    assert "references/recomputo-referencia.md" in texto


# ---------------------------------------------------------------------------
# Conteúdo mínimo (regra de materialidade, acionamento, snapshot, NECE)
# ---------------------------------------------------------------------------

def test_er_auditoria_menciona_materialidade_e_ordem_explicita():
    texto = _ler(AUDITORIA_MD)
    assert "materialidade" in texto
    assert ("ordem explícita" in texto) or ("ordem explicita" in texto)


def test_er_portfolio_menciona_nece_snapshot_e_modo_diagnostico():
    texto = _ler(PORTFOLIO_MD)
    assert "NECE" in texto
    assert "snapshot" in texto
    assert "DIAGNOSTICO_PARA_IDEIAS" in texto


# ---------------------------------------------------------------------------
# Escopo do cabeçalho YAML de red_team.md permanece imutável (schema
# additionalProperties: false); a skill não deve instruir a adicionar um
# campo "escopos" ao YAML.
# ---------------------------------------------------------------------------

def test_er_auditoria_nao_adiciona_campo_escopos_ao_yaml_header():
    texto = _ler(AUDITORIA_MD)
    assert re.search(r"NÃO ganha campo", texto), (
        "er-auditoria/SKILL.md deve declarar explicitamente que o cabeçalho "
        "YAML do red_team.md não ganha campo de escopos (schema imutável)"
    )
