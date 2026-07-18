# -*- coding: utf-8 -*-
"""Testes de forma dos 3 documentos da Task 5.2 (protocolos que CI nao cobre).

Estes documentos sao protocolos EXECUTAVEIS por humano/agente (testes de
ativacao de skills e smoke no Cowork), nao codigo: nao ha logica propria
para TDD classico. Os testes aqui verificam a FORMA exigida pelo brief
(task-5.2-brief.md): os 3 docs existem e contem as secoes/contagens minimas
listadas no brief. Nao validam o CONTEUDO analitico (isso e o proprio
protocolo, rodado por humano/agente fresco, nao por pytest).
"""
import os
import re

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS_DIR = os.path.join(REPO_ROOT, "docs")

TESTES_ATIVACAO = os.path.join(DOCS_DIR, "testes-ativacao.md")
SMOKE_COWORK = os.path.join(DOCS_DIR, "smoke-cowork.md")
PLATAFORMA = os.path.join(DOCS_DIR, "plataforma.md")

MIN_GREEN = 12
MIN_RED = 5


def _ler(caminho):
    assert os.path.isfile(caminho), "arquivo ausente: %s" % caminho
    with open(caminho, "r", encoding="utf-8") as fh:
        return fh.read()


def _secao(texto, titulo_inicio, titulo_fim=None):
    """Extrai o corpo de uma secao markdown '## <titulo>' ate a proxima '## '."""
    m = re.search(r"^## .*" + re.escape(titulo_inicio), texto, re.M)
    assert m, "secao '%s' nao encontrada" % titulo_inicio
    inicio = m.end()
    prox = re.search(r"^## ", texto[inicio:], re.M)
    fim = inicio + prox.start() if prox else len(texto)
    return texto[inicio:fim]


# ---------------------------------------------------------------------------
# Os 3 docs existem
# ---------------------------------------------------------------------------


def test_os_tres_docs_existem():
    for caminho in (TESTES_ATIVACAO, SMOKE_COWORK, PLATAFORMA):
        assert os.path.isfile(caminho), "arquivo ausente: %s" % caminho


# ---------------------------------------------------------------------------
# docs/testes-ativacao.md
# ---------------------------------------------------------------------------


def test_testes_ativacao_tem_pelo_menos_12_cenarios_green():
    texto = _ler(TESTES_ATIVACAO)
    secao_green = _secao(texto, "Cenários GREEN")
    linhas_numeradas = [
        l for l in secao_green.splitlines() if re.match(r"^\d+\.", l.strip())
    ]
    linhas_com_skill = [l for l in linhas_numeradas if re.search(r"\(er-", l)]
    assert len(linhas_numeradas) >= MIN_GREEN, (
        "esperado >= %d cenarios GREEN numerados, achou %d"
        % (MIN_GREEN, len(linhas_numeradas))
    )
    assert len(linhas_com_skill) >= MIN_GREEN, (
        "esperado >= %d cenarios GREEN com skill 'er-' entre parenteses, achou %d"
        % (MIN_GREEN, len(linhas_com_skill))
    )


def test_testes_ativacao_tem_pelo_menos_5_cenarios_red():
    texto = _ler(TESTES_ATIVACAO)
    secao_red = _secao(texto, "Cenários RED")
    linhas_numeradas = [
        l for l in secao_red.splitlines() if re.match(r"^\d+\.", l.strip())
    ]
    assert len(linhas_numeradas) >= MIN_RED, (
        "esperado >= %d cenarios RED numerados, achou %d"
        % (MIN_RED, len(linhas_numeradas))
    )


def test_testes_ativacao_contem_frase_antes_de_qualquer_resposta():
    # Case-insensitive: a frase aparece tanto em prosa ("Antes de qualquer
    # resposta?") quanto enfatizada no criterio de aceite ("ANTES de
    # qualquer resposta"); o requisito do brief e a presenca da frase, nao
    # uma capitalizacao especifica.
    texto = _ler(TESTES_ATIVACAO).lower()
    assert "antes de qualquer resposta" in texto


def test_testes_ativacao_tem_tabela_de_registro_e_criterio_de_aceite():
    texto = _ler(TESTES_ATIVACAO)
    assert re.search(r"^## .*Tabela de registro", texto, re.M)
    assert re.search(r"^## .*[Cc]rit[ée]rio de aceite", texto, re.M)


# ---------------------------------------------------------------------------
# docs/smoke-cowork.md
# ---------------------------------------------------------------------------


def test_smoke_cowork_contem_termos_obrigatorios():
    texto = _ler(SMOKE_COWORK)
    for termo in ("marketplace", "ZIP", "subagente", "chat"):
        assert termo in texto, "termo obrigatorio ausente em smoke-cowork.md: %r" % termo


def test_smoke_cowork_tem_registro():
    texto = _ler(SMOKE_COWORK)
    assert re.search(r"^## .*Registro", texto, re.M)


# ---------------------------------------------------------------------------
# docs/plataforma.md
# ---------------------------------------------------------------------------


def test_plataforma_contem_limite_200mb_e_owner_repo():
    texto = _ler(PLATAFORMA)
    assert "200" in texto, "limite de 200MB nao citado em plataforma.md"
    assert "owner/repo" in texto, "formato 'owner/repo' nao citado em plataforma.md"


def test_plataforma_tem_quatro_secoes_obrigatorias():
    texto = _ler(PLATAFORMA)
    for titulo in (
        "O que sabemos",
        "A verificar no primeiro smoke",
        "Registro de smokes",
        "Decisão de distribuição",
    ):
        assert re.search(r"^## .*" + re.escape(titulo), texto, re.M), (
            "secao ausente em plataforma.md: %r" % titulo
        )
