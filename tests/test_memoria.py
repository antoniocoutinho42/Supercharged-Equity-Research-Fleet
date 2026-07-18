# -*- coding: utf-8 -*-
"""Testes de scripts/memoria.py — nota de memória durável por ticker (Task 3.2).

A nota é GERADA por código a partir de estado.yaml + eventos.jsonl + o run
canônico (runs/<hash8>/resultados.json + meta.yaml); apenas a seção de lições
é preservada/apendada entre regenerações (nunca reescrita à mão). Dados de
fixture são FICTÍCIOS (ticker TST) — a fixture real da FNV vem na Task 5.1.
"""
import importlib.util
import json
import os

import pytest
import yaml

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEMORIA_PATH = os.path.join(REPO_ROOT, "scripts", "memoria.py")
SKILL_MD = os.path.join(REPO_ROOT, "skills", "er-memoria", "SKILL.md")

HASH = "aaaaaaaaaaaaaaaa"


def _carregar_memoria():
    spec = importlib.util.spec_from_file_location("memoria", MEMORIA_PATH)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


memoria = _carregar_memoria()


# ----------------------------------------------------------------------------
# Fixture helpers
# ----------------------------------------------------------------------------

def _escrever_yaml(caminho, dados):
    with open(caminho, "w", encoding="utf-8") as fh:
        yaml.safe_dump(dados, fh, allow_unicode=True, sort_keys=False)


def _escrever_json(caminho, dados):
    with open(caminho, "w", encoding="utf-8") as fh:
        json.dump(dados, fh, ensure_ascii=False)


_ESTADO_BASE = {
    "ticker": "TST",
    "data": "2026-07-15",
    "profundidade": "PADRAO",
    "modo": "CALIBRADO",
    "snapshot": True,
    "engine": {"versao": "2.2.0", "hash": HASH},
    "gates": {
        "G1": "APROVADO", "G1_5": "APROVADO", "G2": "APROVADO", "G3_0": "APROVADO",
        "G3": "APROVADO", "G4": "PULADO", "G5": "PULADO", "G6": "PULADO",
        "G7": "APROVADO", "G8": "ENTREGUE",
    },
    "decisao": {
        "recomendacao": "WATCHLIST (PROXIMA)",
        "confianca": "MEDIA",
        "racional": "Preco dentro da faixa economica, sem margem de seguranca no hurdle.",
        "ressalvas": ["cap_teto_defensavel calibrado sem cross-check GAAP completo"],
        "gatilhos": ["preco cair abaixo de 45 (hurdle ponderado)"],
        "revisao": "proximo trimestre",
    },
    "pendencias": [
        {"id": "P1", "texto": "confirmar guidance do proximo call", "dono": "Analista"},
        {"id": "P2", "texto": "recalcular cap_teto apos 10-K", "dono": "Modelador"},
    ],
    "status_final": "ENCERRADO NO G8 (ENTREGUE)",
}

_EVENTOS_BASE = [
    {"ts": "2026-07-15T10:00:00+00:00", "gate": "G1", "veredicto": "APROVADO",
     "racional": "sem red flags de fraude ou governanca", "refs": ["guardrails.md"]},
    {"ts": "2026-07-15T10:05:00+00:00", "gate": "G2", "veredicto": "APROVADO",
     "racional": "dossie completo, 8 pilares avaliados", "refs": ["dossie.md"]},
    {"ts": "2026-07-15T10:10:00+00:00", "gate": "G3", "veredicto": "REPROVADO",
     "racional": "premissas de cap inconsistentes com o dossie", "refs": ["inputs.yaml"]},
    {"ts": "2026-07-15T10:20:00+00:00", "gate": "G3", "veredicto": "APROVADO",
     "racional": "cap ajustado apos revisao, consistente com o dossie e o historico proprio",
     "refs": ["inputs.yaml", "resultados.json"]},
    {"ts": "2026-07-15T10:30:00+00:00", "gate": "G7", "veredicto": "APROVADO",
     "racional": "decisao registrada, sem auditoria acionada", "refs": []},
    {"ts": "2026-07-15T10:35:00+00:00", "gate": "G8", "veredicto": "ENTREGUE",
     "racional": "relatorio composto e entregue", "refs": ["relatorio.md"]},
]

_RESULTADOS_BASE = {
    "engine": {"versao": "2.2.0", "hash_inputs": HASH, "gerado_em": "2026-07-15T09:00:00+00:00"},
    "meta": {"ticker": "TST", "preco_atual": 65.0},
    "sinais": {"economico": "DENTRO_DA_FAIXA", "entrada": "NAO_ACIONAVEL"},
    "gate": {"modo_recomendado": "PADRAO"},
    "hurdle": {"cenarios": {"ponderado": 51.71}},
    "economico": {"central_ponderado": 73.35, "faixa_ponderada": [60.0, 85.0]},
}

_META_BASE = {
    "hash": HASH,
    "engine_versao": "2.2.0",
    "criado_em": "2026-07-15T09:05:00+00:00",
    "origem": {"inputs": "inputs.yaml", "resultados": "saida_TST/resultados.json"},
    "congelados": ["inputs.yaml", "resultados.json", "estado.yaml"],
}

_DOSSIE_SENTINELA = "FRASE-SENTINELA-DOSSIE-NAO-DEVE-VAZAR-PARA-A-MEMORIA"


def _montar_ns(tmp_path, estado=None, eventos=None, resultados=None, meta=None,
                escrever_dossie=True):
    ns = tmp_path / "ns"
    ns.mkdir()
    _escrever_yaml(ns / "estado.yaml", estado if estado is not None else _ESTADO_BASE)

    with open(ns / "eventos.jsonl", "w", encoding="utf-8") as fh:
        for ev in (eventos if eventos is not None else _EVENTOS_BASE):
            fh.write(json.dumps(ev, ensure_ascii=False) + "\n")

    run_dir = ns / "runs" / HASH
    run_dir.mkdir(parents=True)
    _escrever_json(run_dir / "resultados.json", resultados if resultados is not None else _RESULTADOS_BASE)
    _escrever_yaml(run_dir / "meta.yaml", meta if meta is not None else _META_BASE)

    if escrever_dossie:
        (ns / "dossie.md").write_text(
            f"# Dossie TST\n\n{_DOSSIE_SENTINELA}\n", encoding="utf-8"
        )

    return ns


# ----------------------------------------------------------------------------
# CLI básico / ajuda
# ----------------------------------------------------------------------------

def test_ajuda_curta():
    with pytest.raises(SystemExit) as excinfo:
        memoria.main(["--help"])
    assert excinfo.value.code == 0


# ----------------------------------------------------------------------------
# test_gera_nota_completa
# ----------------------------------------------------------------------------

def test_gera_nota_completa(tmp_path, capsys):
    ns = _montar_ns(tmp_path)
    codigo = memoria.main([str(ns)])
    capsys.readouterr()
    assert codigo == 0

    caminho_nota = ns / "memoria" / "TST.md"
    assert caminho_nota.is_file()
    nota = caminho_nota.read_text(encoding="utf-8")

    secoes = [
        "# TST — nota de memória",
        "## Decisão",
        "## Linha do tempo dos gates",
        "## Pendências",
        "## Âncoras numéricas",
        "## Lições reutilizáveis",
    ]
    indices = [nota.index(s) for s in secoes]
    assert indices == sorted(indices), "seções fora de ordem"

    # Cabeçalho: data, profundidade, modo, engine, status_final
    assert "2026-07-15" in nota
    assert "PADRAO" in nota
    assert "CALIBRADO" in nota
    assert "2.2.0" in nota
    assert HASH in nota

    # Decisão: verbatim, ressalvas/gatilhos como listas, revisao
    assert "WATCHLIST (PROXIMA)" in nota
    assert "Preco dentro da faixa economica, sem margem de seguranca no hurdle." in nota
    assert "cap_teto_defensavel calibrado sem cross-check GAAP completo" in nota
    assert "preco cair abaixo de 45 (hurdle ponderado)" in nota
    assert "proximo trimestre" in nota

    # Linha do tempo: último evento de G3 (re-executado 2x), refs do último
    assert "(re-executado 2x)" in nota
    assert "cap ajustado apos revisao" in nota[:nota.index("## Pendências")]
    assert "premissas de cap inconsistentes" not in nota  # evento antigo de G3 não aparece

    # Pendências
    assert "P1" in nota and "confirmar guidance do proximo call" in nota
    assert "P2" in nota and "recalcular cap_teto apos 10-K" in nota

    # Âncoras numéricas: formato "valor (chave)", só as 6-8 linhas do contrato
    secao_ancoras = nota[nota.index("## Âncoras numéricas"):nota.index("## Lições reutilizáveis")]
    assert "51.71 (hurdle.cenarios.ponderado)" in secao_ancoras
    assert "(economico.faixa_ponderada)" in secao_ancoras
    assert "73.35 (economico.central_ponderado)" in secao_ancoras
    assert "DENTRO_DA_FAIXA (sinais.economico)" in secao_ancoras
    assert "NAO_ACIONAVEL (sinais.entrada)" in secao_ancoras
    assert "PADRAO (gate.modo_recomendado)" in secao_ancoras
    n_linhas_ancoras = len([l for l in secao_ancoras.splitlines() if l.strip().startswith("-")])
    assert 6 <= n_linhas_ancoras <= 8

    # Nota não duplica o dossiê
    assert _DOSSIE_SENTINELA not in nota


def test_saida_customizada(tmp_path, capsys):
    ns = _montar_ns(tmp_path)
    saida_dir = tmp_path / "mnt_memory"
    codigo = memoria.main([str(ns), "--saida", str(saida_dir)])
    capsys.readouterr()
    assert codigo == 0
    assert (saida_dir / "memoria" / "TST.md").is_file()
    assert not (ns / "memoria").exists()


# ----------------------------------------------------------------------------
# test_idempotente_preserva_licoes
# ----------------------------------------------------------------------------

def test_idempotente_preserva_licoes(tmp_path, capsys):
    ns = _montar_ns(tmp_path)
    caminho_nota = ns / "memoria" / "TST.md"

    codigo = memoria.main([str(ns)])
    capsys.readouterr()
    assert codigo == 0
    nota_v1 = caminho_nota.read_text(encoding="utf-8")

    licoes1 = tmp_path / "licoes1.md"
    licoes1.write_text(
        "- royalty/streaming: P/L Justo padrao e conservador; considerar m_terminal\n",
        encoding="utf-8",
    )
    codigo = memoria.main([str(ns), "--licoes", str(licoes1)])
    capsys.readouterr()
    assert codigo == 0
    nota_v2 = caminho_nota.read_text(encoding="utf-8")
    assert "considerar m_terminal" in nota_v2

    # Regenerar SEM --licoes: lições intactas
    codigo = memoria.main([str(ns)])
    capsys.readouterr()
    assert codigo == 0
    nota_v3 = caminho_nota.read_text(encoding="utf-8")
    assert "considerar m_terminal" in nota_v3
    secao_v3 = nota_v3[nota_v3.index("## Lições reutilizáveis"):]
    secao_v2 = nota_v2[nota_v2.index("## Lições reutilizáveis"):]
    assert secao_v3 == secao_v2

    # Regenerar com --licoes NOVO: apendado, antigo preservado
    licoes2 = tmp_path / "licoes2.md"
    licoes2.write_text(
        "- guidance de margem historicamente conservador nos ultimos 4 trimestres\n",
        encoding="utf-8",
    )
    codigo = memoria.main([str(ns), "--licoes", str(licoes2)])
    capsys.readouterr()
    assert codigo == 0
    nota_v4 = caminho_nota.read_text(encoding="utf-8")
    assert "considerar m_terminal" in nota_v4
    assert "guidance de margem historicamente conservador" in nota_v4

    # As seções 1-5 foram regeneradas do zero (não duplicadas)
    assert nota_v4.count("## Decisão") == 1
    assert nota_v4.count("## Âncoras numéricas") == 1


# ----------------------------------------------------------------------------
# test_nao_duplica
# ----------------------------------------------------------------------------

def test_nao_duplica(tmp_path, capsys):
    ns = _montar_ns(tmp_path, escrever_dossie=True)
    codigo = memoria.main([str(ns)])
    capsys.readouterr()
    assert codigo == 0
    nota = (ns / "memoria" / "TST.md").read_text(encoding="utf-8")
    assert _DOSSIE_SENTINELA not in nota


# ----------------------------------------------------------------------------
# test_estado_ausente
# ----------------------------------------------------------------------------

def test_estado_ausente(tmp_path, capsys):
    ns = tmp_path / "ns_vazio"
    ns.mkdir()
    codigo = memoria.main([str(ns)])
    saida = capsys.readouterr()
    assert codigo == 1
    assert "estado.yaml" in (saida.out + saida.err)


def test_run_canonico_ausente(tmp_path, capsys):
    ns = tmp_path / "ns"
    ns.mkdir()
    _escrever_yaml(ns / "estado.yaml", _ESTADO_BASE)
    with open(ns / "eventos.jsonl", "w", encoding="utf-8") as fh:
        for ev in _EVENTOS_BASE:
            fh.write(json.dumps(ev, ensure_ascii=False) + "\n")
    # runs/<hash>/ nunca foi criado (sem snapshot.py)
    codigo = memoria.main([str(ns)])
    saida = capsys.readouterr()
    assert codigo == 1
    assert "run" in (saida.out + saida.err).lower()


# ----------------------------------------------------------------------------
# Forma da skill
# ----------------------------------------------------------------------------

def _frontmatter(texto):
    partes = texto.split("---")
    assert len(partes) >= 3, "SKILL.md deve ter frontmatter delimitado por '---'"
    return yaml.safe_load(partes[1])


def test_skill_existe_e_frontmatter_valido():
    assert os.path.isfile(SKILL_MD), f"SKILL.md ausente em {SKILL_MD}"
    with open(SKILL_MD, "r", encoding="utf-8") as fh:
        texto = fh.read()
    fm = _frontmatter(texto)
    assert fm.get("name") == "er-memoria"
    assert isinstance(fm.get("description"), str) and fm["description"].strip()


def test_skill_respeita_orcamento_de_palavras():
    with open(SKILL_MD, "r", encoding="utf-8") as fh:
        texto = fh.read()
    n_palavras = len(texto.split())
    assert n_palavras <= 550, f"SKILL.md tem {n_palavras} palavras, acima do limite de 550"


def test_skill_menciona_delta_memoria_e_regra_de_nao_editar():
    with open(SKILL_MD, "r", encoding="utf-8") as fh:
        texto = fh.read()
    assert "delta.py" in texto
    assert "memoria.py" in texto
    assert "não edite as seções geradas" in texto
