# -*- coding: utf-8 -*-
"""Testes de forma/estrutura da skill er-dados (Task 4.1).

Esta skill é conteúdo (adapters de fontes por categoria, não código): não há
lógica própria para TDD clássico. Os testes aqui verificam a FORMA exigida
pelo brief (task-4.1-brief.md): frontmatter válido, orçamento de palavras,
existência e conteúdo mínimo dos três references, e a regra central da
task: nenhum fornecedor citado fora de references/conectores.md.
"""
import os

import yaml

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL_DIR = os.path.join(REPO_ROOT, "skills", "er-dados")
SKILL_MD = os.path.join(SKILL_DIR, "SKILL.md")
REFERENCES_DIR = os.path.join(SKILL_DIR, "references")

FONTES_FILINGS = os.path.join(REFERENCES_DIR, "fontes-filings.md")
FONTES_MERCADO = os.path.join(REFERENCES_DIR, "fontes-mercado.md")
CONECTORES = os.path.join(REFERENCES_DIR, "conectores.md")

# Alvo do brief é <= 450 palavras; folga de 100 no mesmo espírito dos
# demais testes de forma (test_skills_dominio_a.py).
WORD_LIMIT = 450 + 100

# Nomes de fornecedor que só podem aparecer em references/conectores.md.
FORNECEDORES = ("Daloopa", "FactSet", "CapIQ", "LSEG", "Quartr")


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

def test_skill_md_existe():
    assert os.path.isfile(SKILL_MD), f"SKILL.md ausente em {SKILL_MD}"


def test_frontmatter_valido_e_name_correto():
    fm = _frontmatter(_ler(SKILL_MD))
    assert fm.get("name") == "er-dados"
    descricao = fm.get("description")
    assert isinstance(descricao, str) and descricao.strip(), (
        "description ausente ou vazia no frontmatter"
    )


# ---------------------------------------------------------------------------
# Orçamento de palavras
# ---------------------------------------------------------------------------

def test_skill_md_respeita_orcamento_de_palavras():
    n_palavras = len(_ler(SKILL_MD).split())
    assert n_palavras <= WORD_LIMIT, (
        f"er-dados/SKILL.md tem {n_palavras} palavras, acima do limite de "
        f"{WORD_LIMIT} (alvo é <= 450; ver task-4.1-brief.md)"
    )


# ---------------------------------------------------------------------------
# References existem e não são vazios
# ---------------------------------------------------------------------------

def test_references_existem_e_nao_vazios():
    for caminho in (FONTES_FILINGS, FONTES_MERCADO, CONECTORES):
        assert os.path.isfile(caminho), f"reference ausente: {caminho}"
        conteudo = _ler(caminho)
        assert conteudo.strip(), f"reference vazio: {caminho}"


# ---------------------------------------------------------------------------
# Conteúdo mínimo exigido pelo brief
# ---------------------------------------------------------------------------

def test_skill_md_contem_categoria_fallback_ledger():
    texto = _ler(SKILL_MD)
    assert "categoria" in texto
    assert "fallback" in texto
    assert "ledger" in texto


def test_fontes_filings_contem_edgar_sedar_cvm():
    texto = _ler(FONTES_FILINGS)
    assert "EDGAR" in texto
    assert "SEDAR" in texto
    assert "CVM" in texto


def test_fontes_mercado_contem_regra_das_2_fontes_e_mesma_base_contabil():
    texto = _ler(FONTES_MERCADO)
    assert "2 fontes" in texto or "duas fontes" in texto
    assert "mesma base contábil" in texto or "MESMA BASE CONTÁBIL" in texto.upper() or (
        "mesma base contábil" in texto.lower()
    )


# ---------------------------------------------------------------------------
# Regra central: nenhum fornecedor fora de conectores.md
# ---------------------------------------------------------------------------

def test_skill_md_nao_cita_fornecedor():
    texto = _ler(SKILL_MD)
    citados = [nome for nome in FORNECEDORES if nome.lower() in texto.lower()]
    assert not citados, (
        f"SKILL.md cita nome(s) de fornecedor {citados}; isso só pode "
        "aparecer em references/conectores.md"
    )


def test_fontes_filings_nao_cita_fornecedor():
    texto = _ler(FONTES_FILINGS)
    citados = [nome for nome in FORNECEDORES if nome.lower() in texto.lower()]
    assert not citados, (
        f"fontes-filings.md cita nome(s) de fornecedor {citados}; isso só "
        "pode aparecer em references/conectores.md"
    )


def test_fontes_mercado_nao_cita_fornecedor():
    texto = _ler(FONTES_MERCADO)
    citados = [nome for nome in FORNECEDORES if nome.lower() in texto.lower()]
    assert not citados, (
        f"fontes-mercado.md cita nome(s) de fornecedor {citados}; isso só "
        "pode aparecer em references/conectores.md"
    )


def test_conectores_cita_os_fornecedores_conhecidos():
    texto = _ler(CONECTORES)
    ausentes = [nome for nome in FORNECEDORES if nome.lower() not in texto.lower()]
    assert not ausentes, (
        f"conectores.md deveria citar os fornecedores conhecidos, faltam: {ausentes}"
    )


def test_skill_md_referencia_os_tres_references():
    texto = _ler(SKILL_MD)
    assert "references/fontes-filings.md" in texto
    assert "references/fontes-mercado.md" in texto
    assert "references/conectores.md" in texto
