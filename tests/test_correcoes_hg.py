# -*- coding: utf-8 -*-
"""Correções sistêmicas pós-feedback do caso HG — testes de recusa/degradação.

Complementa as camadas D-G do golden (engine-level, em
skills/er-valuation/tests/test_golden_vrsk.py) com o nível de PROCESSO:
os bloqueios do checar.py e o degrade/composição do compor.py.

Cobertura exigida pela missão:
  R1  metodo.yaml ausente/ inválido / não revisado bloqueia dossiê/valuation.
  R3  ausência de hurdle degrada limpo ponta a ponta (engine -> compor -> linter).
  R4  sinal contraintuitivo sem resposta bloqueia o valuation.
  R5  divergência material sem resolução bloqueia o valuation.
  R6  relatório composto passa no linter; linguagem operacional no corpo reprova;
      campos da decisão com linguagem operacional reprovam no G7; matrizes 3×3
      presentes com experimento declarado.
"""
import json
import os
import re
import shutil
import subprocess
import sys

import pytest
import yaml

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXT_DIR = os.path.join(REPO_ROOT, "tests", "fixtures", "fnv")
ENGINE_PATH = os.path.join(REPO_ROOT, "skills", "er-valuation", "engine.py")
CHECAR_PATH = os.path.join(REPO_ROOT, "skills", "er-relatorio", "checar.py")
COMPOR_PATH = os.path.join(REPO_ROOT, "skills", "er-relatorio", "compor.py")
PYTHON = sys.executable

ARQUIVOS_BASE = ("dossie.md", "valuation.md", "red_team.md", "claims.yaml",
                 "inputs_valuation.md", "metodo.yaml")


def _rodar(argv):
    return subprocess.run([PYTHON] + argv, capture_output=True, text=True)


def _checar(ns, etapa):
    r = _rodar([CHECAR_PATH, str(ns), "--etapa", etapa, "--json"])
    return json.loads(r.stdout)


def _montar_ns(tmp_path, mut_inputs=None, mut_estado=None, mut_metodo=None,
               sem_metodo=False, rodar_engine=True):
    """Namespace derivado da fixture FNV com mutações declarativas."""
    ns = tmp_path / "FNV"
    ns.mkdir()
    for nome in ARQUIVOS_BASE:
        if nome == "metodo.yaml" and sem_metodo:
            continue
        shutil.copyfile(os.path.join(FIXT_DIR, nome), ns / nome)
    estado = yaml.safe_load(open(os.path.join(FIXT_DIR, "estado_final.yaml"), encoding="utf-8"))
    if mut_estado:
        mut_estado(estado)
    with open(ns / "estado.yaml", "w", encoding="utf-8") as fh:
        yaml.safe_dump(estado, fh, allow_unicode=True, sort_keys=False)
    inp = yaml.safe_load(open(os.path.join(FIXT_DIR, "inputs_p3.yaml"), encoding="utf-8"))
    if mut_inputs:
        mut_inputs(inp)
    with open(ns / "inputs.yaml", "w", encoding="utf-8") as fh:
        yaml.safe_dump(inp, fh, allow_unicode=True, sort_keys=False)
    if mut_metodo and not sem_metodo:
        met = yaml.safe_load(open(ns / "metodo.yaml", encoding="utf-8"))
        mut_metodo(met)
        with open(ns / "metodo.yaml", "w", encoding="utf-8") as fh:
            yaml.safe_dump(met, fh, allow_unicode=True, sort_keys=False)
    if rodar_engine:
        r = _rodar([ENGINE_PATH, str(ns / "inputs.yaml"), "--out", str(ns / "saida_FNV")])
        assert r.returncode == 0, f"engine falhou: {r.stderr}"
    return ns


# ---------------------------------------------------------------------------
# R1 — julgamento metodológico
# ---------------------------------------------------------------------------

def test_dossie_reprova_sem_metodo(tmp_path):
    ns = _montar_ns(tmp_path, sem_metodo=True, rodar_engine=False)
    dados = _checar(ns, "dossie")
    assert dados["status"] == "REPROVADO"
    assert any("metodo.yaml ausente" in f for f in dados["faltas"])


def test_dossie_reprova_metodo_invalido(tmp_path):
    def quebra(met):
        met["decisao"] = "PADRAO_COM_ADAPTACAO"
        met.pop("adaptacoes", None)  # adaptação declarada sem o bloco de adaptações
    ns = _montar_ns(tmp_path, mut_metodo=quebra, rodar_engine=False)
    dados = _checar(ns, "dossie")
    assert dados["status"] == "REPROVADO"
    assert any("metodo.yaml" in f for f in dados["faltas"])


def test_valuation_reprova_metodo_nao_revisado(tmp_path):
    def sem_revisao(met):
        met["revisao_valuation"] = {"confirmada": False}
    ns = _montar_ns(tmp_path, mut_metodo=sem_revisao)
    dados = _checar(ns, "valuation")
    assert dados["status"] == "REPROVADO"
    assert any("revisao_valuation" in f for f in dados["faltas"])


# ---------------------------------------------------------------------------
# R4 — sinal contraintuitivo sem resposta bloqueia
# ---------------------------------------------------------------------------

def test_valuation_reprova_alerta_sem_resposta(tmp_path):
    ns = _montar_ns(tmp_path, mut_inputs=lambda i: i["premissas"].pop("respostas_sinais"))
    dados = _checar(ns, "valuation")
    assert dados["status"] == "REPROVADO"
    assert any("alertas_sinal" in f and "SEM" in f for f in dados["faltas"])


# ---------------------------------------------------------------------------
# R5 — divergência material sem resolução bloqueia
# ---------------------------------------------------------------------------

def test_valuation_reprova_divergencia_sem_resolucao(tmp_path):
    ns = _montar_ns(tmp_path, mut_inputs=lambda i: i["premissas"].pop("resolucao_divergencia"))
    dados = _checar(ns, "valuation")
    assert dados["status"] == "REPROVADO"
    assert any("DIVERGE_MATERIAL sem resolução" in f for f in dados["faltas"])


def test_valuation_fixture_completa_aprovada(tmp_path):
    ns = _montar_ns(tmp_path)
    dados = _checar(ns, "valuation")
    assert dados["status"] == "APROVADO", f"faltas: {dados['faltas']}"


# ---------------------------------------------------------------------------
# R3 — ausência de hurdle degrada limpo ponta a ponta
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def ns_sem_hurdle(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("sem_hurdle")
    ns = _montar_ns(tmp, mut_inputs=lambda i: i["premissas"].pop("ke_hurdle"))
    return ns


def test_sem_hurdle_engine_degrada(ns_sem_hurdle):
    res = json.load(open(ns_sem_hurdle / "saida_FNV" / "resultados.json", encoding="utf-8"))
    assert res["hurdle"] is None
    assert res["sinais"]["entrada"] == "SEM_HURDLE"
    assert res["matrizes"]["hurdle"] is None
    assert res["elasticidades"]["hurdle"] is None


def test_sem_hurdle_checar_valuation_aprova(ns_sem_hurdle):
    dados = _checar(ns_sem_hurdle, "valuation")
    assert dados["status"] == "APROVADO", f"faltas: {dados['faltas']}"


def test_sem_hurdle_compor_declara_ausencia_e_passa_no_linter(ns_sem_hurdle):
    r = _rodar([COMPOR_PATH, str(ns_sem_hurdle)])
    assert r.returncode == 0, f"compor falhou: {r.stderr}"
    txt = open(ns_sem_hurdle / "relatorio.md", encoding="utf-8").read()
    corpo = txt[:re.search(r"^#\s*Anexo t", txt, re.M | re.I).start()]
    assert "retorno mínimo exigido não foi informado" in corpo.lower()
    # nada ancorado em hurdle no corpo (nem matrizes, nem linha do bloco de valor)
    assert "Preço Máximo para o Hurdle — CAP" not in corpo
    dados = _checar(ns_sem_hurdle, "relatorio")
    assert dados["status"] == "APROVADO", f"faltas: {dados['faltas']}"


# ---------------------------------------------------------------------------
# R6 — relatório institucional: linter, decisão e matrizes
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def ns_completo(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("completo")
    ns = _montar_ns(tmp)
    r = _rodar([COMPOR_PATH, str(ns)])
    assert r.returncode == 0, f"compor falhou: {r.stderr}"
    return ns


def test_relatorio_composto_passa_no_linter(ns_completo):
    dados = _checar(ns_completo, "relatorio")
    assert dados["status"] == "APROVADO", f"faltas: {dados['faltas']}"


def test_relatorio_linter_reprova_vazamento_no_corpo(ns_completo, tmp_path):
    ns2 = tmp_path / "vazado"
    shutil.copytree(ns_completo, ns2)
    txt = open(ns2 / "relatorio.md", encoding="utf-8").read()
    m = re.search(r"^#\s*Anexo t", txt, re.M | re.I)
    vazado = (txt[:m.start()]
              + "\nO veredicto foi DIVERGE_MATERIAL conforme `hurdle.cenarios.ponderado`.\n\n"
              + txt[m.start():])
    open(ns2 / "relatorio.md", "w", encoding="utf-8").write(vazado)
    dados = _checar(ns2, "relatorio")
    assert dados["status"] == "REPROVADO"
    rotulos = " ".join(dados["faltas"])
    assert "enum cru" in rotulos and "chave de dados" in rotulos


def test_relatorio_tem_matrizes_com_experimento(ns_completo):
    txt = open(ns_completo / "relatorio.md", encoding="utf-8").read()
    corpo = txt[:re.search(r"^#\s*Anexo t", txt, re.M | re.I).start()]
    # seis matrizes: 3 do hurdle (fixture tem ke_hurdle) + 3 econômicas
    for anc in ("Preço Máximo para o Hurdle", "Valor Intrínseco Econômico"):
        for par in ("CAP × ROE", "CAP × g", "ROE × g"):
            assert f"{anc} — {par}" in corpo, f"matriz ausente: {anc} — {par}"
    assert "mantém o terceiro no valor base" in corpo  # experimento declarado (R4)
    assert corpo.count("fixos:") >= 6


def test_relatorio_recomendacao_sem_log_de_matriz(ns_completo):
    """O racional operacional do G7 não aparece no corpo (vai ao anexo)."""
    txt = open(ns_completo / "relatorio.md", encoding="utf-8").read()
    m = re.search(r"^#\s*Anexo t", txt, re.M | re.I)
    corpo, anexo = txt[:m.start()], txt[m.start():]
    assert "Racional operacional da decisão" in anexo
    # fragmento distintivo do racional da fixture só pode viver no anexo
    assert "recomputo genuino confirmado" not in corpo
    assert "recomputo genuino confirmado" in anexo


def test_decisao_reprova_tese_curta(tmp_path):
    def tese_curta(est):
        est["decisao"]["tese"] = "curta demais"
    ns = _montar_ns(tmp_path, mut_estado=tese_curta, rodar_engine=False)
    dados = _checar(ns, "decisao")
    assert dados["status"] == "REPROVADO"
    assert any("tese" in f for f in dados["faltas"])


def test_decisao_reprova_linguagem_operacional(tmp_path):
    def ressalva_operacional(est):
        est["decisao"]["ressalvas"] = ["Validacao por multiplos em DIVERGE_MATERIAL (AC-04)"]
    ns = _montar_ns(tmp_path, mut_estado=ressalva_operacional, rodar_engine=False)
    dados = _checar(ns, "decisao")
    assert dados["status"] == "REPROVADO"
    assert any("linguagem operacional" in f and "ressalvas[0]" in f for f in dados["faltas"])


def test_decisao_fixture_aprovada(tmp_path):
    ns = _montar_ns(tmp_path, rodar_engine=False)
    dados = _checar(ns, "decisao")
    assert dados["status"] == "APROVADO", f"faltas: {dados['faltas']}"
