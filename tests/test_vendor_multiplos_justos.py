"""Congelamento e integridade do vendor `multiplos-justos` v9.24.

O vendor é read-only por desenho: além do manifest de sha256 verificado aqui, o
próprio `scripts/testes.py` do pacote faz lint semântico dos docs — editar a
metodologia localmente quebra a suíte sem que ninguém precise lembrar da regra.
"""
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SKILL = RAIZ / "skills" / "er-multiplos-justos"
VENDOR = SKILL / "vendor" / "multiplos-justos"

ARQUIVOS = (
    "CHANGELOG.md",
    "SKILL.md",
    "references/aplicacao.md",
    "references/derivacao.md",
    "references/paper-multiplos-justos-v3.md",
    "scripts/justos.py",
    "scripts/testes.py",
)


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _manifest() -> dict:
    return json.loads((SKILL / "manifest_vendor.json").read_text(encoding="utf-8"))


def test_manifest_declara_a_versao_e_a_raiz():
    man = _manifest()
    assert man["versao"] == "v9.24"
    assert man["raiz_do_pacote"] == "vendor/multiplos-justos"


def test_todo_arquivo_do_manifest_bate_no_disco():
    for rel, sha in _manifest()["arquivos"].items():
        alvo = VENDOR / rel
        assert alvo.is_file(), f"arquivo do manifest ausente no disco: {rel}"
        assert _sha(alvo) == sha, f"arquivo do vendor ALTERADO: {rel}"


def test_disco_nao_tem_arquivo_fora_do_manifest():
    no_disco = {
        p.relative_to(VENDOR).as_posix()
        for p in VENDOR.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts
    }
    assert no_disco == set(ARQUIVOS), (
        f"conjunto de arquivos do vendor divergiu do congelado: "
        f"sobrando={sorted(no_disco - set(ARQUIVOS))} "
        f"faltando={sorted(set(ARQUIVOS) - no_disco)}"
    )


def test_manifest_cobre_exatamente_os_arquivos_esperados():
    assert set(_manifest()["arquivos"]) == set(ARQUIVOS)


def _ambiente() -> dict:
    """Ambiente dos subprocessos do vendor.

    PYTHONDONTWRITEBYTECODE evita que rodar a suite crie __pycache__ dentro da
    arvore congelada — o vendor nao e mutado nem pelos proprios testes dele.
    PYTHONUTF8 protege a leitura do pipe em locale cp1252 (Windows PT-BR).
    """
    return {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONUTF8": "1"}


def _rodar(*argv: str) -> subprocess.CompletedProcess:
    """Executa o vendor no MESMO interpretador que roda a suite, com utf-8 fixo."""
    return subprocess.run(
        [sys.executable, *argv],
        capture_output=True, text=True, encoding="utf-8",
        env=_ambiente(), timeout=300,
    )


def test_selftest_do_motor_reproduz_as_ancoras():
    r = _rodar(str(VENDOR / "scripts" / "justos.py"), "selftest")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "SELFTEST OK" in r.stdout, r.stdout[-2000:]


def test_suite_completa_do_vendor_passa():
    r = _rodar(str(VENDOR / "scripts" / "testes.py"))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "TODOS OS TESTES PASSARAM" in r.stdout, r.stdout[-2000:]
