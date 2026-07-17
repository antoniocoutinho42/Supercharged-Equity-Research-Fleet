# -*- coding: utf-8 -*-
"""Teste end-to-end (Task 1.4): integração da skill er-valuation com os runs
imutáveis de scripts/snapshot.py.

Fecha o bug de concorrência da sessão FNV: inputs.yaml foi editado pelo
Modelador durante a auditoria; o Auditor DEVE auditar o snapshot congelado em
runs/<hash>/, nunca o inputs.yaml mutável.

Fluxo exercitado (subprocess, engine e snapshot reais — sem mocks):
  1. Monta um ns em tmp_path copiando inputs_exemplo_vrsk.yaml como
     inputs.yaml (ticker VRSK já bate com saida_VRSK).
  2. Roda engine.py <ns>/inputs.yaml --out <ns>/saida_VRSK (sem --chart).
  3. Roda snapshot.py <ns> -> captura hash8.
  4. Edita <ns>/inputs.yaml (simula o Modelador mexendo durante a auditoria).
  5. Assertions de imutabilidade + proteção contra snapshot de estado
     inconsistente (nova chamada sem re-rodar o engine -> exit 2).

Também valida (teste barato, sem subprocess) que o SKILL.md contém as
strings-chave da integração, para não regredir a doc.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL_DIR = os.path.join(REPO_ROOT, "skills", "er-valuation")
ENGINE_PATH = os.path.join(SKILL_DIR, "engine.py")
SNAPSHOT_PATH = os.path.join(REPO_ROOT, "scripts", "snapshot.py")
INPUTS_EXEMPLO = os.path.join(SKILL_DIR, "inputs_exemplo_vrsk.yaml")
SKILL_MD = os.path.join(SKILL_DIR, "SKILL.md")

PYTHON = sys.executable


def _montar_ns(tmp_path):
    ns = tmp_path / "analise_vrsk"
    ns.mkdir()
    shutil.copyfile(INPUTS_EXEMPLO, ns / "inputs.yaml")
    return ns


def _rodar(args, cwd=None):
    resultado = subprocess.run(
        [PYTHON, *args],
        cwd=cwd or REPO_ROOT,
        capture_output=True,
        text=True,
    )
    return resultado


def test_fluxo_engine_snapshot_auditor_isola_edicao_concorrente(tmp_path):
    ns = _montar_ns(tmp_path)
    inputs_path = ns / "inputs.yaml"
    conteudo_original = inputs_path.read_text(encoding="utf-8")

    # passo 1-2 (Modelador): roda o engine real sobre o inputs.yaml original.
    r_engine = _rodar([
        ENGINE_PATH,
        str(inputs_path),
        "--out",
        str(ns / "saida_VRSK"),
    ])
    assert r_engine.returncode == 0, (
        f"engine.py falhou: stdout={r_engine.stdout!r} stderr={r_engine.stderr!r}"
    )

    resultados_path = ns / "saida_VRSK" / "resultados.json"
    assert resultados_path.is_file()
    resultados_originais = json.loads(resultados_path.read_text(encoding="utf-8"))
    hash_engine = resultados_originais["engine"]["hash_inputs"]

    hash_esperado = hashlib.sha256(
        conteudo_original.encode("utf-8")
    ).hexdigest()[:16]
    assert hash_engine == hash_esperado

    # passo 3 (Modelador): congela o run com snapshot.py -> captura hash canônico.
    r_snap = _rodar([SNAPSHOT_PATH, str(ns)])
    assert r_snap.returncode == 0, (
        f"snapshot.py falhou: stdout={r_snap.stdout!r} stderr={r_snap.stderr!r}"
    )
    assert f"SNAPSHOT {hash_engine}" in r_snap.stdout

    run_dir = ns / "runs" / hash_engine
    assert run_dir.is_dir()

    # passo 4: simula o Modelador editando inputs.yaml DURANTE a auditoria
    # (bug real da sessão FNV: concorrência entre Modelador e Auditor).
    inputs_path.write_text(
        conteudo_original + "\n# edicao concorrente do Modelador durante auditoria\n",
        encoding="utf-8",
    )
    assert inputs_path.read_text(encoding="utf-8") != conteudo_original

    # o run congelado NUNCA muda: byte-idêntico ao conteúdo ORIGINAL, não ao editado.
    conteudo_run = (run_dir / "inputs.yaml").read_text(encoding="utf-8")
    assert conteudo_run == conteudo_original
    assert conteudo_run != inputs_path.read_text(encoding="utf-8")

    # resultados.json do run tem o engine.hash_inputs == hash canônico do snapshot.
    resultados_run = json.loads((run_dir / "resultados.json").read_text(encoding="utf-8"))
    assert resultados_run["engine"]["hash_inputs"] == hash_engine

    # passo 5: nova chamada de snapshot com o inputs.yaml editado, SEM re-rodar o
    # engine -> o engine ainda não gravou resultados.json para o novo hash, então
    # o hash do resultados.json existente (do estado anterior) diverge do hash do
    # inputs.yaml atual -> snapshot.py recusa com exit 2 (proteção contra
    # snapshot de estado inconsistente).
    r_snap_inconsistente = _rodar([SNAPSHOT_PATH, str(ns)])
    assert r_snap_inconsistente.returncode == 2, (
        f"esperado exit 2 (hash divergente); obtido {r_snap_inconsistente.returncode}: "
        f"stdout={r_snap_inconsistente.stdout!r} stderr={r_snap_inconsistente.stderr!r}"
    )

    hash_editado = hashlib.sha256(
        inputs_path.read_text(encoding="utf-8").encode("utf-8")
    ).hexdigest()[:16]
    assert not (ns / "runs" / hash_editado).exists()

    # o run original permanece intacto e imutável.
    assert (run_dir / "inputs.yaml").read_text(encoding="utf-8") == conteudo_original


def test_skill_md_documenta_fluxo_de_runs_imutaveis():
    texto = open(SKILL_MD, "r", encoding="utf-8").read()

    # Fluxo do Modelador: novo passo rodando snapshot.py.
    secao_modelador = texto.split("## 3. Fluxo de uso (Modelador)")[1].split(
        "## 4. Fluxo de uso (Auditor)"
    )[0]
    assert "snapshot.py" in secao_modelador
    assert "runs/" in secao_modelador

    # Fluxo do Auditor: regra dura de nunca usar o inputs.yaml mutável.
    secao_auditor = texto.split("## 4. Fluxo de uso (Auditor)")[1].split(
        "## 5."
    )[0]
    assert "runs/" in secao_auditor
    assert "hash" in secao_auditor
    assert "NUNCA" in secao_auditor
    assert "mutável" in secao_auditor
    assert "snapshot ausente" in secao_auditor

    # Seção 7 (arquivos): nota sobre scripts/snapshot.py estar fora da pasta da skill.
    secao_arquivos = texto.split("## 7. Arquivos deste skill")[1]
    assert "scripts/snapshot.py" in secao_arquivos
