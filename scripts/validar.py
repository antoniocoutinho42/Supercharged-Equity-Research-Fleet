#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""validar.py — valida um arquivo (YAML/JSON/front-matter de .md) contra um
JSON Schema (draft 2020-12) de schemas/<nome>.schema.json.

Uso:
    python validar.py <arquivo> --schema <nome>

<nome> ∈ {estado, handoff, claims, decisao, red_team_header}

Substitui handoffs/estado/claims/decisão em prosa por validação de código:
o formato é fixado nos JSON Schemas de schemas/ (derivados dos arquivos
REAIS da sessão FNV), este script apenas os aplica.

Resolve schemas/<nome>.schema.json relativo ao próprio script (__file__),
não ao cwd — funciona de qualquer diretório de trabalho. Schemas podem se
referenciar entre si via $ref (ex.: estado.schema.json -> decisao.schema.json);
para isso, TODOS os schemas de schemas/ são carregados num Registry local
antes da validação.

Carregamento do documento a validar, por extensão:
  .yaml / .yml -> yaml.safe_load do arquivo inteiro
  .json        -> json.load do arquivo inteiro
  .md          -> extrai o front-matter YAML entre os dois primeiros '---'
                  (caso real: cabeçalho de red_team.md) e faz yaml.safe_load
                  só desse trecho — o corpo em prosa do .md NUNCA é parseado
                  como YAML.

Saída: "VALIDO" em stdout e exit 0 se o documento é válido; senão, uma lista
objetiva de erros em stderr (um por linha: caminho JSON + mensagem) e exit 1.
"""
import argparse
import json
import os
import re
import sys

try:
    import yaml
except ImportError:
    yaml = None

try:
    import jsonschema
    from referencing import Registry, Resource
    from referencing.jsonschema import DRAFT202012
except ImportError:
    jsonschema = None

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SCHEMAS_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, "..", "schemas"))

NOMES_VALIDOS = ("estado", "handoff", "claims", "decisao", "red_team_header")

_RE_FRONT_MATTER = re.compile(r"^-{3,}[ \t]*\r?\n(.*?\r?\n)-{3,}[ \t]*(\r?\n|$)", re.S)


def _extrair_front_matter(texto):
    """Extrai o trecho YAML entre os dois primeiros '---' de um .md.
    Levanta ValueError com mensagem PT-BR se não encontrar o padrão."""
    inicio = texto.lstrip("﻿ \t\r\n")
    m = _RE_FRONT_MATTER.match(inicio)
    if not m:
        raise ValueError(
            "front-matter YAML não encontrado (esperado bloco entre '---' no início do arquivo)"
        )
    return m.group(1)


def _carregar_documento(caminho):
    """Lê <caminho> e retorna (dados, None) ou (None, mensagem_de_erro_pt_br)."""
    if not os.path.isfile(caminho):
        return None, f"arquivo não encontrado: {caminho}"

    ext = os.path.splitext(caminho)[1].lower()
    try:
        with open(caminho, "r", encoding="utf-8") as fh:
            texto = fh.read()
    except OSError as exc:
        return None, f"falha ao ler {caminho}: {exc}"

    if ext in (".yaml", ".yml"):
        if yaml is None:
            return None, "pyyaml ausente: instale (pip install pyyaml) para validar YAML"
        try:
            dados = yaml.safe_load(texto)
        except yaml.YAMLError as exc:
            return None, f"{caminho} não é YAML válido: {exc}"
        return dados, None

    if ext == ".json":
        try:
            dados = json.loads(texto)
        except json.JSONDecodeError as exc:
            return None, f"{caminho} não é JSON válido: {exc}"
        return dados, None

    if ext == ".md":
        if yaml is None:
            return None, "pyyaml ausente: instale (pip install pyyaml) para validar front-matter"
        try:
            bloco = _extrair_front_matter(texto)
        except ValueError as exc:
            return None, f"{caminho}: {exc}"
        try:
            dados = yaml.safe_load(bloco)
        except yaml.YAMLError as exc:
            return None, f"{caminho}: front-matter não é YAML válido: {exc}"
        return dados, None

    return None, f"extensão não suportada: {ext} (use .yaml, .yml, .json ou .md)"


def _carregar_schema(nome):
    """Retorna (schema_dict, caminho) ou (None, mensagem_de_erro_pt_br)."""
    caminho = os.path.join(SCHEMAS_DIR, f"{nome}.schema.json")
    if not os.path.isfile(caminho):
        return None, f"schema desconhecido: {nome} (esperado {caminho})"
    with open(caminho, "r", encoding="utf-8") as fh:
        return json.load(fh), None


def _construir_registry():
    """Carrega TODOS os schemas/*.schema.json num Registry local, indexados
    pelo próprio $id (nome do arquivo) — permite $ref entre schemas (ex.:
    estado.schema.json -> decisao.schema.json) sem depender de rede."""
    recursos = []
    for nome in os.listdir(SCHEMAS_DIR):
        if not nome.endswith(".schema.json"):
            continue
        caminho = os.path.join(SCHEMAS_DIR, nome)
        with open(caminho, "r", encoding="utf-8") as fh:
            conteudo = json.load(fh)
        id_ = conteudo.get("$id", nome)
        recursos.append((id_, Resource.from_contents(conteudo, default_specification=DRAFT202012)))
    return Registry().with_resources(recursos)


def _caminho_erro(erro):
    """Formata error.absolute_path como caminho pontilhado (arr[i] para índices)."""
    partes = []
    for p in erro.absolute_path:
        if isinstance(p, int):
            if partes:
                partes[-1] = f"{partes[-1]}[{p}]"
            else:
                partes.append(f"[{p}]")
        else:
            partes.append(str(p))
    return ".".join(partes) if partes else "(raiz)"


def _construir_parser():
    parser = argparse.ArgumentParser(
        prog="validar.py",
        description="Valida <arquivo> (YAML/JSON/front-matter de .md) contra schemas/<nome>.schema.json.",
    )
    parser.add_argument("arquivo", help="caminho do arquivo a validar")
    parser.add_argument(
        "--schema", required=True, choices=NOMES_VALIDOS,
        help="nome do schema (sem sufixo .schema.json)",
    )
    return parser


def main(argv=None):
    parser = _construir_parser()
    args = parser.parse_args(argv)

    if jsonschema is None:
        print(
            "erro: jsonschema (com o pacote referencing) ausente: "
            "instale (pip install jsonschema) para rodar validar.py",
            file=sys.stderr,
        )
        return 1

    schema, erro = _carregar_schema(args.schema)
    if erro:
        print(f"erro: {erro}", file=sys.stderr)
        return 1

    dados, erro = _carregar_documento(args.arquivo)
    if erro:
        print(f"erro: {erro}", file=sys.stderr)
        return 1

    registry = _construir_registry()
    validator = jsonschema.Draft202012Validator(schema, registry=registry)
    erros = sorted(
        validator.iter_errors(dados),
        key=lambda e: [str(p) for p in e.absolute_path],
    )

    if not erros:
        print("VALIDO")
        return 0

    for e in erros:
        print(f"{_caminho_erro(e)}: {e.message}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
