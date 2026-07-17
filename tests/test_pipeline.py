# -*- coding: utf-8 -*-
"""Testes de scripts/pipeline.py — máquina de estados dos gates (Task 1.3).

Via subprocess do script (não import direto), conforme task-1.3-brief.md:
cada comando do CLI é invocado como um processo separado
(`python scripts/pipeline.py <ns> <comando> ...`), o que exercita o parser
de argumentos e a leitura/escrita real de estado.yaml/eventos.jsonl em
tmp_path, do jeito que o Coordenador (usuário real do script) vai chamá-lo.
"""
import json
import os
import subprocess
import sys

import yaml

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PIPELINE_PATH = os.path.join(REPO_ROOT, "scripts", "pipeline.py")
VALIDAR_PATH = os.path.join(REPO_ROOT, "scripts", "validar.py")
PYTHON = sys.executable

# No Windows, um subprocesso Python com stdout/stderr redirecionado para pipe
# usa por padrão o codepage do console (cp1252/mbcs), não UTF-8 — mensagens
# PT-BR com acentos (é, ç, ã...) então quebram a decodificação no lado do
# pai. Força UTF-8 nos dois lados via PYTHONIOENCODING/PYTHONUTF8.
_ENV_UTF8 = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")


def _pipeline(*args):
    return subprocess.run(
        [PYTHON, PIPELINE_PATH, *args],
        capture_output=True, text=True, encoding="utf-8", env=_ENV_UTF8,
    )


def _validar(caminho, schema):
    return subprocess.run(
        [PYTHON, VALIDAR_PATH, caminho, "--schema", schema],
        capture_output=True, text=True, encoding="utf-8", env=_ENV_UTF8,
    )


def _ler_estado(ns):
    with open(os.path.join(ns, "estado.yaml"), "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _ler_eventos(ns):
    caminho = os.path.join(ns, "eventos.jsonl")
    if not os.path.isfile(caminho):
        return []
    with open(caminho, "r", encoding="utf-8") as fh:
        return [json.loads(linha) for linha in fh if linha.strip()]


def _levar_ate_g6_puladas(ns):
    """Fluxo feliz até G6 (inclusive), sem auditoria acionada e sem snapshot
    — reusado por test_g7_exige_decisao e test_fluxo_feliz."""
    passos = [
        ["init", "--ticker", "FNV"],
        ["gate", "G1", "--veredicto", "APROVADO_COM_RESSALVA", "--racional", "G1 ok com ressalva menor de tese."],
        ["gate", "G1_5", "--veredicto", "APROVADO", "--racional", "G1_5 ok, sem red flags adicionais."],
        ["gate", "G2", "--veredicto", "APROVADO", "--racional", "G2 ok, dossie suficiente."],
        ["set", "profundidade", "PADRAO"],
        ["gate", "G3_0", "--veredicto", "APROVADO", "--racional", "G3_0 ok, profundidade PADRAO confirmada.",
         "--ref", "dossie.md"],
        ["set", "engine", "--versao", "2.2.0", "--hash", "1234567890abcdef"],
        ["gate", "G3", "--veredicto", "APROVADO", "--racional", "G3 ok, engine rodado com sucesso."],
        ["gate", "G4", "--veredicto", "PULADO", "--racional", "Auditoria nao acionada nesta rodada."],
        ["gate", "G5", "--veredicto", "PULADO", "--racional", "Auditoria nao acionada nesta rodada."],
        ["gate", "G6", "--veredicto", "PULADO", "--racional", "Snapshot desativado para esta analise."],
    ]
    resultados = [_pipeline(ns, *p) for p in passos]
    return resultados


# ---------------------------------------------------------------------------
# init + status
# ---------------------------------------------------------------------------

def test_init_e_status(tmp_path):
    ns = str(tmp_path / "FNV")
    r = _pipeline(ns, "init", "--ticker", "FNV")
    assert r.returncode == 0, r.stderr

    estado = _ler_estado(ns)
    assert estado["ticker"] == "FNV"
    assert estado["profundidade"] == "PADRAO"
    assert estado["modo"] == "PARCIAL"
    assert estado["snapshot"] is False
    assert estado["engine"] == {"versao": "", "hash": "0000000000000000"}
    assert all(v == "PENDENTE" for v in estado["gates"].values())

    eventos = _ler_eventos(ns)
    assert len(eventos) == 1
    assert eventos[0]["gate"] == "INIT"
    assert eventos[0]["veredicto"] == "OK"

    r2 = _pipeline(ns, "status")
    assert r2.returncode == 0, r2.stderr
    for g in ("G1", "G1_5", "G2", "G3_0", "G3", "G4", "G5", "G6", "G7", "G8"):
        assert f"{g}: PENDENTE" in r2.stdout
    assert "PROXIMO: G1" in r2.stdout


def test_init_recusa_se_ja_existe(tmp_path):
    ns = str(tmp_path / "FNV")
    r1 = _pipeline(ns, "init", "--ticker", "FNV")
    assert r1.returncode == 0, r1.stderr

    r2 = _pipeline(ns, "init", "--ticker", "FNV")
    assert r2.returncode == 1
    assert r2.stderr.strip() != ""


# ---------------------------------------------------------------------------
# transição inválida (pré-condição violada)
# ---------------------------------------------------------------------------

def test_transicao_invalida(tmp_path):
    ns = str(tmp_path / "FNV")
    _pipeline(ns, "init", "--ticker", "FNV")
    estado_antes = _ler_estado(ns)

    r = _pipeline(ns, "gate", "G3", "--veredicto", "APROVADO",
                   "--racional", "Tentativa de fechar G3 sem G2 aprovado.")
    assert r.returncode == 1
    assert r.stderr.strip() != ""

    estado_depois = _ler_estado(ns)
    assert estado_depois == estado_antes

    eventos = _ler_eventos(ns)
    assert len(eventos) == 1  # só o INIT; a tentativa invalida nao gravou evento


# ---------------------------------------------------------------------------
# VETO encerra o processo no G1
# ---------------------------------------------------------------------------

def test_veto_encerra(tmp_path):
    ns = str(tmp_path / "FNV")
    _pipeline(ns, "init", "--ticker", "FNV")

    r = _pipeline(ns, "gate", "G1", "--veredicto", "VETO",
                   "--racional", "Veto por red flag contabil grave e irreconciliavel.")
    assert r.returncode == 0, r.stderr

    estado = _ler_estado(ns)
    assert estado["gates"]["G1"] == "VETO"
    assert estado.get("status_final") == "ENCERRADO NO G1 (VETO)"

    r2 = _pipeline(ns, "gate", "G2", "--veredicto", "APROVADO",
                    "--racional", "Tentativa de prosseguir apos veto.")
    assert r2.returncode == 1
    assert r2.stderr.strip() != ""

    # e nem o proprio G1 pode ser refechado
    r3 = _pipeline(ns, "gate", "G1", "--veredicto", "APROVADO",
                    "--racional", "Tentativa de reverter o veto.")
    assert r3.returncode == 1


# ---------------------------------------------------------------------------
# G5 exige G4
# ---------------------------------------------------------------------------

def test_g5_exige_g4(tmp_path):
    ns = str(tmp_path / "FNV")
    _pipeline(ns, "init", "--ticker", "FNV")

    r = _pipeline(ns, "gate", "G5", "--veredicto", "APROVADO",
                   "--racional", "Tentativa de fechar G5 sem G4.")
    assert r.returncode == 1
    assert r.stderr.strip() != ""


# ---------------------------------------------------------------------------
# G7 exige bloco decisao
# ---------------------------------------------------------------------------

def test_g7_exige_decisao(tmp_path):
    ns = str(tmp_path / "FNV")
    resultados = _levar_ate_g6_puladas(ns)
    for r in resultados:
        assert r.returncode == 0, r.stderr

    r = _pipeline(ns, "gate", "G7", "--veredicto", "APROVADO",
                   "--racional", "Tentativa de fechar G7 sem bloco decisao.")
    assert r.returncode == 1
    assert r.stderr.strip() != ""

    estado = _ler_estado(ns)
    assert estado["gates"]["G7"] == "PENDENTE"


# ---------------------------------------------------------------------------
# fluxo feliz completo, ate a entrega (G8)
# ---------------------------------------------------------------------------

def test_fluxo_feliz(tmp_path):
    ns = str(tmp_path / "FNV")
    resultados = _levar_ate_g6_puladas(ns)
    for r in resultados:
        assert r.returncode == 0, r.stderr

    # Coordenador escreve o bloco decisao diretamente no estado.yaml
    caminho_estado = os.path.join(ns, "estado.yaml")
    with open(caminho_estado, "r", encoding="utf-8") as fh:
        estado = yaml.safe_load(fh)
    estado["decisao"] = {
        "recomendacao": "WATCHLIST (PROXIMA) - NAO COMPRAR AGORA",
        "confianca": "MEDIA",
        "racional": "Tese estrutural intacta; sem gatilho de compra no preco atual.",
    }
    with open(caminho_estado, "w", encoding="utf-8") as fh:
        yaml.safe_dump(estado, fh, allow_unicode=True, sort_keys=False)

    r_g7 = _pipeline(ns, "gate", "G7", "--veredicto", "APROVADO",
                      "--racional", "G7 ok, bloco decisao presente e valido.")
    assert r_g7.returncode == 0, r_g7.stderr

    r_g8 = _pipeline(ns, "gate", "G8", "--veredicto", "ENTREGUE",
                      "--racional", "Relatorio entregue ao usuario.")
    assert r_g8.returncode == 0, r_g8.stderr

    eventos = _ler_eventos(ns)
    # 11 passos de _levar_ate_g6_puladas + G7 + G8 = 13, um evento por operacao
    assert len(eventos) == 13

    estado_final = _ler_estado(ns)
    assert estado_final["gates"]["G8"] == "ENTREGUE"
    assert estado_final["status_final"] == "ENCERRADO NO G8 (ENTREGUE)"
    assert estado_final["engine"]["hash"] == "1234567890abcdef"

    r_val = _validar(caminho_estado, "estado")
    assert r_val.returncode == 0, r_val.stderr
    assert "VALIDO" in r_val.stdout


# ---------------------------------------------------------------------------
# set: revalida contra o schema (nao grava se o candidato for invalido)
# ---------------------------------------------------------------------------

def test_set_engine_hash_invalido_reprovado(tmp_path):
    ns = str(tmp_path / "FNV")
    _pipeline(ns, "init", "--ticker", "FNV")
    estado_antes = _ler_estado(ns)

    r = _pipeline(ns, "set", "engine", "--versao", "2.2.0", "--hash", "hash-invalido-nao-hex")
    assert r.returncode == 1
    assert r.stderr.strip() != ""

    estado_depois = _ler_estado(ns)
    assert estado_depois == estado_antes


def test_g6_snapshot_false_so_aceita_pulado(tmp_path):
    ns = str(tmp_path / "FNV")
    _pipeline(ns, "init", "--ticker", "FNV")  # snapshot default = false
    _pipeline(ns, "gate", "G1", "--veredicto", "APROVADO", "--racional", "G1 ok.")
    _pipeline(ns, "gate", "G1_5", "--veredicto", "APROVADO", "--racional", "G1_5 ok.")
    _pipeline(ns, "gate", "G2", "--veredicto", "APROVADO", "--racional", "G2 ok.")
    _pipeline(ns, "set", "profundidade", "PADRAO")
    _pipeline(ns, "gate", "G3_0", "--veredicto", "APROVADO", "--racional", "G3_0 ok.", "--ref", "dossie.md")
    _pipeline(ns, "set", "engine", "--versao", "2.2.0", "--hash", "1234567890abcdef")
    _pipeline(ns, "gate", "G3", "--veredicto", "APROVADO", "--racional", "G3 ok.")

    r = _pipeline(ns, "gate", "G6", "--veredicto", "APROVADO",
                   "--racional", "Tentativa de aprovar G6 com snapshot desativado.")
    assert r.returncode == 1
    assert r.stderr.strip() != ""
