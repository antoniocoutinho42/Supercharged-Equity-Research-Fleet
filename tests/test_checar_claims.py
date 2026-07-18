# -*- coding: utf-8 -*-
"""Testes de skills/er-relatorio/checar.py --etapa claims (Task 2.2a).

Via subprocess (mesmo padrão de tests/test_pipeline.py): cada chamada invoca
o script real como processo separado, exercitando o parser de argumentos e a
leitura real de dossie.md/claims.yaml em tmp_path.

Cobertura exigida pelo brief (task-2.2a-brief.md):
  - dossie.md citando [F-01][E-02] + claims.yaml correspondente -> APROVADO exit 0
  - claim orfao no yaml (sem citacao no dossie) -> exit 1
  - ID citado no dossie sem entrada no yaml -> exit 1
  - FATO sem fonte -> exit 1 (via schema, reuso de validar.py)
  - claims.yaml ausente -> exit 1
  - dossie.md ausente -> exit 1
  - --etapa tudo sem claims.yaml -> aviso, sem reprovar por causa disso
"""
import os
import subprocess
import sys

import yaml

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHECAR_PATH = os.path.join(REPO_ROOT, "skills", "er-relatorio", "checar.py")
PYTHON = sys.executable

# Mesmo motivo de tests/test_pipeline.py: forcar UTF-8 nos dois lados do
# subprocesso no Windows, ou mensagens PT-BR acentuadas quebram a decodificacao.
_ENV_UTF8 = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")


def _checar(*args):
    return subprocess.run(
        [PYTHON, CHECAR_PATH, *args],
        capture_output=True, text=True, encoding="utf-8", env=_ENV_UTF8,
    )


def _escreve(caminho, texto):
    with open(caminho, "w", encoding="utf-8") as fh:
        fh.write(texto)


def _escreve_claims_yaml(caminho, claims):
    with open(caminho, "w", encoding="utf-8") as fh:
        yaml.safe_dump({"claims": claims}, fh, allow_unicode=True, sort_keys=False)


_DOSSIE_OK = (
    "# Dossie de teste\n\n"
    "A empresa tem divida liquida negativa [F-01], conforme reconstrucao propria.\n"
    "O ROE 2026E projetado e de aproximadamente 18% [E-02].\n"
)

_CLAIMS_OK = [
    {"id": "F-01", "tipo": "FATO", "texto": "Divida liquida negativa em 2025.",
     "fonte": "10-K 2025, p. 40", "data": "2026-01-01", "pilar": 3},
    {"id": "E-02", "tipo": "ESTIMATIVA", "texto": "ROE 2026E ~18%."},
]


def test_dossie_e_claims_consistentes_aprova(tmp_path):
    """Caso feliz: dossie.md cita [F-01] e [E-02], claims.yaml tem as duas entradas
    correspondentes (e nada mais) -> APROVADO, exit 0."""
    _escreve(tmp_path / "dossie.md", _DOSSIE_OK)
    _escreve_claims_yaml(tmp_path / "claims.yaml", _CLAIMS_OK)

    r = _checar(str(tmp_path), "--etapa", "claims")

    assert r.returncode == 0, r.stdout + r.stderr
    assert "APROVADO" in r.stdout


def test_claim_orfao_no_yaml_reprova(tmp_path):
    """claims.yaml tem um claim [H-03] que o dossie.md nunca cita -> exit 1."""
    _escreve(tmp_path / "dossie.md", _DOSSIE_OK)
    claims = _CLAIMS_OK + [
        {"id": "H-03", "tipo": "HIPOTESE", "texto": "Premio sobre pares e estrutural."},
    ]
    _escreve_claims_yaml(tmp_path / "claims.yaml", claims)

    r = _checar(str(tmp_path), "--etapa", "claims")

    assert r.returncode == 1
    assert "H-03" in r.stdout


def test_id_citado_sem_entrada_no_yaml_reprova(tmp_path):
    """dossie.md cita [F-09], que nao existe em claims.yaml -> exit 1."""
    dossie = _DOSSIE_OK + "Ha tambem um risco de concentracao de clientes [F-09].\n"
    _escreve(tmp_path / "dossie.md", dossie)
    _escreve_claims_yaml(tmp_path / "claims.yaml", _CLAIMS_OK)

    r = _checar(str(tmp_path), "--etapa", "claims")

    assert r.returncode == 1
    assert "F-09" in r.stdout


def test_fato_sem_fonte_reprova_via_schema(tmp_path):
    """claim tipo FATO sem campo fonte viola o schema (fonte + data obrigatorias
    para FATO) -> exit 1, mensagem aponta o schema, nao o cross-check."""
    dossie = "# Dossie\n\nDivida liquida zero [F-01].\n"
    _escreve(tmp_path / "dossie.md", dossie)
    claims = [
        {"id": "F-01", "tipo": "FATO", "texto": "Divida liquida zero em 2025.",
         "data": "2026-01-01"},  # falta 'fonte'
    ]
    _escreve_claims_yaml(tmp_path / "claims.yaml", claims)

    r = _checar(str(tmp_path), "--etapa", "claims")

    assert r.returncode == 1
    assert "claims.yaml" in r.stdout


def test_claims_yaml_ausente_reprova(tmp_path):
    _escreve(tmp_path / "dossie.md", _DOSSIE_OK)

    r = _checar(str(tmp_path), "--etapa", "claims")

    assert r.returncode == 1
    assert "claims.yaml" in r.stdout


def test_dossie_md_ausente_reprova(tmp_path):
    _escreve_claims_yaml(tmp_path / "claims.yaml", _CLAIMS_OK)

    r = _checar(str(tmp_path), "--etapa", "claims")

    assert r.returncode == 1
    assert "dossie.md" in r.stdout


def test_etapa_tudo_sem_claims_yaml_avisa_sem_reprovar_por_isso(tmp_path):
    """Namespace sem claims.yaml (analise anterior ao sistema de claims): a
    etapa tudo deve emitir um AVISO sobre claims.yaml, e esse aviso NUNCA deve
    aparecer como FALTA (a reprovacao pode continuar acontecendo por outras
    causas do namespace incompleto, mas nao por causa de claims.yaml)."""
    r = _checar(str(tmp_path), "--etapa", "tudo")

    assert "claims.yaml" in r.stdout
    linhas_falta = [l for l in r.stdout.splitlines() if l.strip().startswith("FALTA:")]
    assert not any("claims.yaml" in l for l in linhas_falta), (
        "claims.yaml ausente deveria virar aviso em --etapa tudo, nao FALTA:\n" + r.stdout
    )
    linhas_aviso = [l for l in r.stdout.splitlines() if l.strip().startswith("aviso:")]
    assert any("claims.yaml" in l for l in linhas_aviso)


def test_etapa_claims_isolada_nao_e_afetada_por_outras_etapas(tmp_path):
    """--etapa claims roda isolada: nao exige dossie completo (inputs.yaml,
    inputs_valuation.md) nem nenhum outro arquivo das demais etapas."""
    _escreve(tmp_path / "dossie.md", _DOSSIE_OK)
    _escreve_claims_yaml(tmp_path / "claims.yaml", _CLAIMS_OK)
    # nenhum inputs.yaml, inputs_valuation.md, valuation.md, estado.yaml etc.

    r = _checar(str(tmp_path), "--etapa", "claims")

    assert r.returncode == 0, r.stdout + r.stderr
