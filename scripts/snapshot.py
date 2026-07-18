#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""snapshot.py — cria runs/<hash8>/ imutável a partir de inputs.yaml + resultados.json.

Uso:
    python snapshot.py <ns>

<ns> é o diretório de análise. O script:
  1. Lê <ns>/inputs.yaml como texto utf-8 e calcula hash8 = sha256(texto)[:16]
     (EXATAMENTE o algoritmo do engine — skills/er-valuation/engine.py, função
     carregar_inputs — o mesmo valor que o engine grava em
     resultados.json -> engine.hash_inputs).
  2. Localiza <ns>/saida_<TICKER>/resultados.json (TICKER = meta.ticker do
     inputs.yaml; se ausente/ilegível, usa o primeiro diretório saida_* do ns).
     Valida que resultados["engine"]["hash_inputs"] == hash8.
  3. Cria <ns>/runs/<hash8>/ com cópias imutáveis de inputs.yaml,
     resultados.json e um meta.yaml novo. Também congela <ns>/claims.yaml e
     <ns>/estado.yaml QUANDO existirem (best-effort — arquivos opcionais,
     ausência não falha o snapshot; usados por scripts/delta.py para comparar
     claims e a decisão entre runs). meta.yaml ganha a chave "congelados" com
     a lista de arquivos efetivamente copiados para o run.
  4. Remove a permissão de escrita dos arquivos copiados e do diretório
     (best effort — não falha se o SO não suportar).
  5. É idempotente: se runs/<hash8>/ já existe, não regrava.

Isola o Auditor do Modelador: o Auditor sempre audita um run imutável em
runs/<hash8>/, nunca o inputs.yaml mutável que o Modelador pode estar editando.
"""
import argparse
import hashlib
import json
import os
import shutil
import stat
import sys
from datetime import datetime, timezone

try:
    import yaml
except ImportError:
    yaml = None


def _calcular_hash(caminho_inputs):
    """Lê inputs.yaml como texto utf-8 e retorna (hash8, texto)."""
    with open(caminho_inputs, "r", encoding="utf-8") as fh:
        texto = fh.read()
    hash8 = hashlib.sha256(texto.encode("utf-8")).hexdigest()[:16]
    return hash8, texto


def _extrair_ticker(texto_inputs):
    """Extrai meta.ticker do texto de inputs.yaml. Retorna None se ausente/ilegível."""
    if yaml is None:
        return None
    try:
        dados = yaml.safe_load(texto_inputs)
    except yaml.YAMLError:
        return None
    if not isinstance(dados, dict):
        return None
    meta = dados.get("meta")
    if not isinstance(meta, dict):
        return None
    ticker = meta.get("ticker")
    return str(ticker) if ticker else None


def _localizar_resultados(ns, ticker):
    """Localiza <ns>/saida_<TICKER>/resultados.json; fallback: primeiro saida_* do ns."""
    if ticker:
        candidato = os.path.join(ns, f"saida_{ticker}", "resultados.json")
        if os.path.isfile(candidato):
            return candidato
    if os.path.isdir(ns):
        for nome in sorted(os.listdir(ns)):
            if nome.startswith("saida_"):
                candidato = os.path.join(ns, nome, "resultados.json")
                if os.path.isfile(candidato):
                    return candidato
    return None


def _somente_leitura(caminho):
    """Remove a permissão de escrita de arquivo/diretório. Best effort: nunca lança."""
    try:
        if os.path.isdir(caminho):
            os.chmod(caminho, stat.S_IREAD | stat.S_IEXEC)
        else:
            os.chmod(caminho, stat.S_IREAD)
    except OSError:
        pass


def _construir_parser():
    parser = argparse.ArgumentParser(
        prog="snapshot.py",
        description=(
            "Cria runs/<hash8>/ imutável a partir de <ns>/inputs.yaml e "
            "<ns>/saida_<TICKER>/resultados.json."
        ),
    )
    parser.add_argument(
        "ns", help="diretório de análise (contém inputs.yaml e saida_<TICKER>/)"
    )
    return parser


def main(argv=None):
    parser = _construir_parser()
    args = parser.parse_args(argv)
    ns = args.ns

    caminho_inputs = os.path.join(ns, "inputs.yaml")
    if not os.path.isfile(caminho_inputs):
        print(f"erro: inputs.yaml não encontrado em {caminho_inputs}", file=sys.stderr)
        return 1

    if yaml is None:
        print(
            "erro: pyyaml ausente: instale (pip install pyyaml) para rodar snapshot.py",
            file=sys.stderr,
        )
        return 1

    hash8, texto_inputs = _calcular_hash(caminho_inputs)
    ticker = _extrair_ticker(texto_inputs)

    caminho_resultados = _localizar_resultados(ns, ticker)
    if caminho_resultados is None:
        print(
            f"erro: resultados.json não encontrado (esperado em "
            f"{ns}/saida_<TICKER>/resultados.json); rode o engine antes do snapshot",
            file=sys.stderr,
        )
        return 1

    try:
        with open(caminho_resultados, "r", encoding="utf-8") as fh:
            resultados = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"erro: falha ao ler {caminho_resultados}: {exc}", file=sys.stderr)
        return 1

    engine_info = resultados.get("engine") if isinstance(resultados, dict) else None
    if not isinstance(engine_info, dict) or "hash_inputs" not in engine_info:
        print(
            f"erro: {caminho_resultados} malformado: esperado objeto JSON com "
            "engine.hash_inputs (saída do engine)",
            file=sys.stderr,
        )
        return 1
    hash_resultados = engine_info.get("hash_inputs")

    if hash_resultados != hash8:
        print(
            "erro: inputs.yaml mudou desde a última execução do engine; "
            "re-rode o engine antes do snapshot",
            file=sys.stderr,
        )
        return 2

    run_dir = os.path.join(ns, "runs", hash8)
    if os.path.isdir(run_dir):
        print(f"EXISTENTE {hash8}")
        return 0

    runs_dir = os.path.join(ns, "runs")
    os.makedirs(runs_dir, exist_ok=True)

    tmp_dir = run_dir + ".tmp"
    if os.path.isdir(tmp_dir):
        shutil.rmtree(tmp_dir)
    os.makedirs(tmp_dir)

    shutil.copy2(caminho_inputs, os.path.join(tmp_dir, "inputs.yaml"))
    shutil.copy2(caminho_resultados, os.path.join(tmp_dir, "resultados.json"))
    congelados = ["inputs.yaml", "resultados.json"]

    # claims.yaml e estado.yaml (Task 3.1): opcionais, best-effort — congelados
    # QUANDO existirem no ns, sem quebrar o snapshot se ausentes ou se a cópia
    # falhar por algum motivo do SO.
    for nome_opcional in ("claims.yaml", "estado.yaml"):
        origem_opcional = os.path.join(ns, nome_opcional)
        if os.path.isfile(origem_opcional):
            try:
                shutil.copy2(origem_opcional, os.path.join(tmp_dir, nome_opcional))
                congelados.append(nome_opcional)
            except OSError:
                pass

    engine_versao = engine_info.get("versao") if isinstance(engine_info, dict) else None
    meta = {
        "hash": hash8,
        "engine_versao": engine_versao,
        "criado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "origem": {
            "inputs": caminho_inputs,
            "resultados": caminho_resultados,
        },
        "congelados": sorted(congelados),
    }
    meta_path = os.path.join(tmp_dir, "meta.yaml")
    with open(meta_path, "w", encoding="utf-8") as fh:
        yaml.safe_dump(meta, fh, allow_unicode=True, sort_keys=False)

    os.replace(tmp_dir, run_dir)

    for nome in congelados + ["meta.yaml"]:
        _somente_leitura(os.path.join(run_dir, nome))
    _somente_leitura(run_dir)

    print(f"SNAPSHOT {hash8}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
