# -*- coding: utf-8 -*-
"""Testes de forma/estrutura da skill kernel er-processo (Task 2.1).

Este skill é conteúdo (porte de mandato, não código): não há lógica para
testar com TDD clássico. Os testes aqui verificam a FORMA exigida pelo brief
(task-2.1-brief.md): frontmatter válido, orçamento de palavras, a heurística
anti-resumo da description (trigger, não workflow) e a presença dos
references com o conteúdo mínimo esperado.
"""
import os
import re

import yaml

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL_DIR = os.path.join(REPO_ROOT, "skills", "er-processo")
SKILL_MD = os.path.join(SKILL_DIR, "SKILL.md")
REFERENCES_DIR = os.path.join(SKILL_DIR, "references")

WORD_LIMIT = 600


def _ler(caminho):
    with open(caminho, "r", encoding="utf-8") as fh:
        return fh.read()


def _frontmatter(texto):
    """Extrai o bloco YAML entre os dois primeiros '---' do SKILL.md."""
    partes = texto.split("---")
    assert len(partes) >= 3, "SKILL.md deve ter frontmatter delimitado por '---'"
    return yaml.safe_load(partes[1])


def test_skill_md_existe():
    assert os.path.isfile(SKILL_MD), f"SKILL.md ausente em {SKILL_MD}"


def test_frontmatter_tem_name_e_description_nao_vazia():
    texto = _ler(SKILL_MD)
    fm = _frontmatter(texto)
    assert fm.get("name") == "er-processo"
    descricao = fm.get("description")
    assert isinstance(descricao, str) and descricao.strip(), (
        "description ausente ou vazia no frontmatter"
    )


def test_skill_md_respeita_orcamento_de_palavras():
    texto = _ler(SKILL_MD)
    n_palavras = len(texto.split())
    assert n_palavras <= WORD_LIMIT, (
        f"SKILL.md tem {n_palavras} palavras, acima do limite de {WORD_LIMIT} "
        "(alvo é <= 550; ver task-2.1-brief.md)"
    )


def test_description_e_gatilho_nao_resumo_de_gates():
    """Heurística anti-resumo (lição Superpowers): a description é condição
    de disparo, nunca o passo a passo dos gates. Se ela cita a sequência
    literal de gates (G1, G2, G3, ... ou setas de fluxo), é sinal de que virou
    resumo do workflow em vez de gatilho — o corpo do SKILL.md tende a ser
    ignorado pelo agente nesse caso."""
    texto = _ler(SKILL_MD)
    fm = _frontmatter(texto)
    descricao = fm.get("description", "")
    assert "G1" not in descricao, "description não deve citar gates (ex.: G1)"
    assert "→" not in descricao, "description não deve descrever fluxo com setas"


def test_references_existem_e_nao_vazios():
    for nome in ("gates.md", "regras-decisao.md", "chat-mode.md"):
        caminho = os.path.join(REFERENCES_DIR, nome)
        assert os.path.isfile(caminho), f"reference ausente: {caminho}"
        conteudo = _ler(caminho)
        assert conteudo.strip(), f"reference vazio: {caminho}"


def test_gates_md_menciona_g1_5_g3_0_e_pipeline():
    conteudo = _ler(os.path.join(REFERENCES_DIR, "gates.md"))
    assert "G1_5" in conteudo
    assert "G3_0" in conteudo
    assert "pipeline.py" in conteudo


def test_regras_decisao_menciona_watchlist_e_comprar():
    conteudo = _ler(os.path.join(REFERENCES_DIR, "regras-decisao.md"))
    assert "WATCHLIST" in conteudo
    assert "COMPRAR" in conteudo


def test_chat_mode_menciona_subagentes_e_chat():
    conteudo = _ler(os.path.join(REFERENCES_DIR, "chat-mode.md"))
    assert "subagentes" in conteudo
    assert "chat" in conteudo


def test_skill_md_referencia_os_tres_arquivos_de_references():
    texto = _ler(SKILL_MD)
    assert "references/gates.md" in texto
    assert "references/regras-decisao.md" in texto
    assert "references/chat-mode.md" in texto
