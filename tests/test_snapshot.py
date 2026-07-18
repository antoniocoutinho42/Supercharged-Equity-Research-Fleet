# -*- coding: utf-8 -*-
"""Testes de scripts/snapshot.py — runs/<hash8>/ imutáveis (Task 1.1).

Importa scripts/snapshot.py dinamicamente via importlib (o script não faz parte
de um pacote instalável) e chama snapshot.main(argv) diretamente, capturando
stdout/stderr via capsys — evita subprocess (mais rápido, mais fácil de
depurar) mantendo o comportamento idêntico ao uso via linha de comando.
"""
import hashlib
import importlib.util
import json
import os
import time

import pytest
import yaml

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SNAPSHOT_PATH = os.path.join(REPO_ROOT, "scripts", "snapshot.py")


def _carregar_snapshot():
    spec = importlib.util.spec_from_file_location("snapshot", SNAPSHOT_PATH)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


snapshot = _carregar_snapshot()


def _montar_ns(tmp_path, ticker="TST", engine_versao="2.3.0", nome_dir="analise"):
    """Monta um diretório de análise fake: inputs.yaml + saida_<TICKER>/resultados.json
    com engine.hash_inputs calculado com o MESMO algoritmo do engine real
    (sha256 do texto utf-8 de inputs.yaml, 16 chars hex)."""
    ns = tmp_path / nome_dir
    ns.mkdir()
    inputs_texto = (
        "meta:\n"
        f"  ticker: {ticker}\n"
        "  nome: \"Empresa Teste SA\"\n"
        "  moeda: USD\n"
    )
    (ns / "inputs.yaml").write_text(inputs_texto, encoding="utf-8")
    hash8 = hashlib.sha256(inputs_texto.encode("utf-8")).hexdigest()[:16]

    saida = ns / f"saida_{ticker}"
    saida.mkdir()
    resultados = {
        "engine": {
            "versao": engine_versao,
            "hash_inputs": hash8,
            "gerado_em": "2026-07-17T12:00:00+00:00",
        },
        "meta": {"ticker": ticker},
    }
    (saida / "resultados.json").write_text(
        json.dumps(resultados, ensure_ascii=False), encoding="utf-8"
    )
    return ns, hash8


def test_cria_run_imutavel(tmp_path, capsys):
    ns, hash8 = _montar_ns(tmp_path)

    codigo = snapshot.main([str(ns)])
    saida = capsys.readouterr()

    assert codigo == 0
    assert f"SNAPSHOT {hash8}" in saida.out

    run_dir = ns / "runs" / hash8
    assert run_dir.is_dir()
    for nome in ("inputs.yaml", "resultados.json", "meta.yaml"):
        assert (run_dir / nome).is_file(), f"{nome} ausente em {run_dir}"

    # conteúdo copiado bate com a origem
    assert (run_dir / "inputs.yaml").read_text(encoding="utf-8") == (
        ns / "inputs.yaml"
    ).read_text(encoding="utf-8")
    resultados_copiado = json.loads((run_dir / "resultados.json").read_text(encoding="utf-8"))
    assert resultados_copiado["engine"]["hash_inputs"] == hash8

    meta = yaml.safe_load((run_dir / "meta.yaml").read_text(encoding="utf-8"))
    assert meta["hash"] == hash8
    assert meta["engine_versao"] == "2.3.0"
    assert "criado_em" in meta and meta["criado_em"]
    assert "origem" in meta
    assert "inputs" in meta["origem"]
    assert "resultados" in meta["origem"]


def test_idempotente(tmp_path, capsys):
    ns, hash8 = _montar_ns(tmp_path)

    codigo1 = snapshot.main([str(ns)])
    capsys.readouterr()
    assert codigo1 == 0

    run_dir = ns / "runs" / hash8
    mtime_antes = (run_dir / "meta.yaml").stat().st_mtime
    time.sleep(0.05)

    codigo2 = snapshot.main([str(ns)])
    saida = capsys.readouterr()

    assert codigo2 == 0
    assert f"EXISTENTE {hash8}" in saida.out
    mtime_depois = (run_dir / "meta.yaml").stat().st_mtime
    assert mtime_antes == mtime_depois


def test_run_e_somente_leitura(tmp_path, capsys):
    """Item 4 do contrato: os arquivos copiados ficam sem permissão de escrita.

    Em NTFS o atributo read-only bloqueia escrita em ARQUIVO de forma
    confiável; se a plataforma não bloquear (chmod best-effort sem efeito),
    pula com motivo em vez de falhar."""
    ns, hash8 = _montar_ns(tmp_path)

    codigo = snapshot.main([str(ns)])
    capsys.readouterr()
    assert codigo == 0

    run_dir = ns / "runs" / hash8
    bloqueados = []
    for nome in ("inputs.yaml", "resultados.json", "meta.yaml"):
        caminho = run_dir / nome
        try:
            with open(caminho, "a", encoding="utf-8") as fh:
                fh.write("x")
            bloqueados.append((nome, False))
        except PermissionError:
            bloqueados.append((nome, True))

    if not any(ok for _, ok in bloqueados):
        pytest.skip(
            "plataforma não bloqueia escrita via chmod read-only "
            "(best-effort documentado no contrato, item 4)"
        )
    falhas = [nome for nome, ok in bloqueados if not ok]
    assert not falhas, f"escrita permitida em arquivos do run: {falhas}"


def test_resultados_malformado(tmp_path, capsys):
    """resultados.json com JSON válido porém não-dict (ex.: lista) é arquivo
    malformado -> exit 1 com mensagem própria, NÃO exit 2 de hash divergente."""
    ns, hash8 = _montar_ns(tmp_path)
    (ns / "saida_TST" / "resultados.json").write_text("[1, 2, 3]", encoding="utf-8")

    codigo = snapshot.main([str(ns)])
    saida = capsys.readouterr()

    assert codigo == 1
    mensagem = saida.out + saida.err
    assert "re-rode o engine" not in mensagem
    assert mensagem.strip() != ""
    assert not (ns / "runs" / hash8).exists()


def test_hash_divergente(tmp_path, capsys):
    ns, hash8 = _montar_ns(tmp_path)

    # altera inputs.yaml DEPOIS que resultados.json já foi "gerado" pelo engine
    (ns / "inputs.yaml").write_text(
        "meta:\n  ticker: TST\n  nome: \"Mudou Depois\"\n  moeda: USD\n",
        encoding="utf-8",
    )

    codigo = snapshot.main([str(ns)])
    saida = capsys.readouterr()

    assert codigo == 2
    mensagem = saida.out + saida.err
    assert "re-rode o engine" in mensagem
    assert not (ns / "runs" / hash8).exists()


def test_inputs_ausente(tmp_path, capsys):
    ns = tmp_path / "vazio"
    ns.mkdir()

    codigo = snapshot.main([str(ns)])
    saida = capsys.readouterr()

    assert codigo == 1
    assert (saida.out + saida.err).strip() != ""


def test_resultados_ausente(tmp_path, capsys):
    ns = tmp_path / "sem_saida"
    ns.mkdir()
    (ns / "inputs.yaml").write_text("meta:\n  ticker: TST\n", encoding="utf-8")

    codigo = snapshot.main([str(ns)])
    saida = capsys.readouterr()

    assert codigo == 1
    assert (saida.out + saida.err).strip() != ""


def test_fallback_sem_ticker_usa_primeiro_saida(tmp_path, capsys):
    """meta.ticker ausente/ilegível -> usa o primeiro diretório saida_* do ns."""
    ns = tmp_path / "sem_ticker"
    ns.mkdir()
    inputs_texto = "meta:\n  nome: \"Sem ticker\"\n"
    (ns / "inputs.yaml").write_text(inputs_texto, encoding="utf-8")
    hash8 = hashlib.sha256(inputs_texto.encode("utf-8")).hexdigest()[:16]

    saida = ns / "saida_XYZ"
    saida.mkdir()
    resultados = {"engine": {"versao": "9.9.9", "hash_inputs": hash8}}
    (saida / "resultados.json").write_text(json.dumps(resultados), encoding="utf-8")

    codigo = snapshot.main([str(ns)])
    saida_captura = capsys.readouterr()

    assert codigo == 0
    assert f"SNAPSHOT {hash8}" in saida_captura.out
    assert (ns / "runs" / hash8 / "meta.yaml").is_file()


def test_ajuda_curta():
    with pytest.raises(SystemExit) as excinfo:
        snapshot.main(["--help"])
    assert excinfo.value.code == 0


def test_congela_claims_e_estado_quando_presentes(tmp_path, capsys):
    """Task 3.1: claims.yaml e estado.yaml são congelados no run QUANDO existem
    no ns, e meta.yaml ganha a chave 'congelados' listando o que foi copiado."""
    ns, hash8 = _montar_ns(tmp_path)
    claims_texto = "claims:\n  - id: F-01\n    tipo: FATO\n    texto: \"x\"\n    fonte: \"y\"\n    data: \"2026-01-01\"\n"
    (ns / "claims.yaml").write_text(claims_texto, encoding="utf-8")
    estado_texto = "ticker: TST\ndecisao:\n  recomendacao: WATCHLIST\n  confianca: MEDIA\n  racional: \"x\"\n"
    (ns / "estado.yaml").write_text(estado_texto, encoding="utf-8")

    codigo = snapshot.main([str(ns)])
    capsys.readouterr()
    assert codigo == 0

    run_dir = ns / "runs" / hash8
    assert (run_dir / "claims.yaml").is_file()
    assert (run_dir / "estado.yaml").is_file()
    assert (run_dir / "claims.yaml").read_text(encoding="utf-8") == claims_texto
    assert (run_dir / "estado.yaml").read_text(encoding="utf-8") == estado_texto

    meta = yaml.safe_load((run_dir / "meta.yaml").read_text(encoding="utf-8"))
    assert sorted(meta["congelados"]) == sorted(
        ["inputs.yaml", "resultados.json", "claims.yaml", "estado.yaml"]
    )


def test_nao_congela_claims_e_estado_quando_ausentes(tmp_path, capsys):
    """Ausência de claims.yaml/estado.yaml no ns não falha o snapshot
    (best-effort, item 3 do contrato atualizado)."""
    ns, hash8 = _montar_ns(tmp_path)

    codigo = snapshot.main([str(ns)])
    capsys.readouterr()
    assert codigo == 0

    run_dir = ns / "runs" / hash8
    assert not (run_dir / "claims.yaml").exists()
    assert not (run_dir / "estado.yaml").exists()

    meta = yaml.safe_load((run_dir / "meta.yaml").read_text(encoding="utf-8"))
    assert sorted(meta["congelados"]) == sorted(["inputs.yaml", "resultados.json"])
