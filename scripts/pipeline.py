#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pipeline.py — máquina de estados dos gates do processo (Task 1.3).

Codifica em código as regras de sequência de gates que hoje só vivem em
prosa no mandato do Coordenador (docs/fontes/Coordenador de Research.md,
Seção 4). É a ÚNICA via de escrita de `<ns>/estado.yaml`: todo comando
valida as pré-condições ANTES de gravar, revalida o candidato inteiro
contra `schemas/estado.schema.json` (reusando os helpers internos de
`scripts/validar.py`, carregado por caminho via importlib — funciona de
qualquer cwd) e só então grava. O racional denso de cada operação vai para
`<ns>/eventos.jsonl` (append-only, um objeto JSON por linha); o estado.yaml
guarda apenas o veredicto (enum de uma palavra) por gate.

Uso:
    pipeline.py <ns> init --ticker FNV [--profundidade-provisoria SUMARIA]
                                        [--snapshot|--sem-snapshot]
    pipeline.py <ns> gate <G> --veredicto <V> --racional "..." [--ref path]...
    pipeline.py <ns> set engine --versao 2.2.0 --hash <16hex>
    pipeline.py <ns> set snapshot true|false
    pipeline.py <ns> set profundidade <SUMARIA|PADRAO|REFORCADA>
    pipeline.py <ns> set modo <CALIBRADO|PARCIAL|PROVISORIO>
    pipeline.py <ns> set auditoria --acionada true|false [--agregado <enum>]
    pipeline.py <ns> status

Saída: mensagem curta em stdout + exit 0 em sucesso; "erro: ..." em stderr
(um ou mais, um por linha) + exit 1 se uma pré-condição for violada ou o
candidato final não passar no schema — nesse caso o estado.yaml em disco
NUNCA é tocado (a validação acontece sobre um candidato em memória).
"""
import argparse
import copy
import importlib.util
import json
import os
import sys
from datetime import datetime, timezone

try:
    import yaml
except ImportError:
    yaml = None

GATES = ("G1", "G1_5", "G2", "G3_0", "G3", "G4", "G5", "G6", "G7", "G8")
VEREDICTOS = (
    "PENDENTE", "EM_ANDAMENTO", "APROVADO", "APROVADO_COM_RESSALVA",
    "REPROVADO", "VETO", "PULADO", "ENTREGUE",
)
PROFUNDIDADES = ("SUMARIA", "PADRAO", "REFORCADA")
MODOS = ("CALIBRADO", "PARCIAL", "PROVISORIO")
AGREGADOS = ("DEMONSTRADA", "DEMONSTRADA_COM_RESSALVAS", "NAO_DEMONSTRADA", "REPROVADA")
APROVADOS = ("APROVADO", "APROVADO_COM_RESSALVA")
HASH_VAZIO = "0000000000000000"

# Veredictos que "fecham" um gate de forma definitiva: refechar exige
# retrabalho explícito. REPROVADO é a única exceção (retrabalho comum).
_TERMINAIS_SEM_RETRABALHO = tuple(
    v for v in VEREDICTOS if v not in ("PENDENTE", "EM_ANDAMENTO", "REPROVADO")
)

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_VALIDAR_PATH = os.path.join(_SCRIPT_DIR, "validar.py")


def _carregar_validar():
    """Importa scripts/validar.py por caminho (não por pacote) — funciona
    de qualquer cwd, mesmo padrão de tests/test_schemas.py."""
    spec = importlib.util.spec_from_file_location("pipeline_validar_interno", _VALIDAR_PATH)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


# ---------------------------------------------------------------------------
# Pré-condições (a máquina de estados)
# ---------------------------------------------------------------------------

def _dep_g1(estado):
    return None


def _dep_g1_5(estado):
    if estado["gates"]["G1"] not in APROVADOS:
        return "G1_5 exige G1 em {APROVADO, APROVADO_COM_RESSALVA}"
    return None


def _dep_g2(estado):
    if estado["gates"]["G1_5"] not in APROVADOS + ("PULADO",):
        return "G2 exige G1_5 em {APROVADO, APROVADO_COM_RESSALVA, PULADO}"
    return None


def _dep_g3_0(estado):
    if estado["gates"]["G2"] != "APROVADO":
        return "G3_0 exige G2 = APROVADO"
    return None


def _dep_g3(estado):
    if estado["gates"]["G3_0"] != "APROVADO":
        return "G3 exige G3_0 = APROVADO"
    if estado.get("engine", {}).get("hash") == HASH_VAZIO:
        return "G3 exige engine definido (rode 'set engine' antes de fechar G3)"
    return None


def _dep_g4(estado):
    if estado["gates"]["G3"] != "APROVADO" and estado["gates"]["G8"] != "ENTREGUE":
        return "G4 exige G3 = APROVADO (ou G8 = ENTREGUE, para auditoria pós-entrega)"
    return None


def _dep_g5(estado):
    # G4 = ENTREGUE é o caso normal; G4 = PULADO também libera G5 (auditoria
    # inteira pulada quando não acionada — mesmo padrão de G1_5 -> G2).
    if estado["gates"]["G4"] not in ("ENTREGUE", "PULADO"):
        return "G5 exige G4 = ENTREGUE"
    return None


def _dep_g6(estado):
    if estado["gates"]["G3"] != "APROVADO":
        return "G6 exige G3 = APROVADO"
    return None


def _dep_g7(estado):
    if estado["gates"]["G3"] != "APROVADO":
        return "G7 exige G3 = APROVADO"
    auditoria = estado.get("auditoria") or {}
    if auditoria.get("acionada") and estado["gates"]["G5"] not in APROVADOS:
        return "G7 exige G5 em {APROVADO, APROVADO_COM_RESSALVA} quando auditoria.acionada = true"
    decisao = estado.get("decisao")
    if not isinstance(decisao, dict):
        return "G7 exige bloco 'decisao' presente em estado.yaml (o Coordenador escreve antes de fechar G7)"
    return None


def _dep_g8(estado):
    if estado["gates"]["G7"] != "APROVADO":
        return "G8 exige G7 = APROVADO"
    return None


_DEP = {
    "G1": _dep_g1, "G1_5": _dep_g1_5, "G2": _dep_g2, "G3_0": _dep_g3_0,
    "G3": _dep_g3, "G4": _dep_g4, "G5": _dep_g5, "G6": _dep_g6,
    "G7": _dep_g7, "G8": _dep_g8,
}


def _checar_refechamento(estado, gate):
    atual = estado["gates"][gate]
    if atual in _TERMINAIS_SEM_RETRABALHO:
        return (
            f"{gate} já fechado com veredicto {atual}; não é possível refechar "
            "(exceto retrabalho após REPROVADO)"
        )
    return None


# ---------------------------------------------------------------------------
# Leitura/escrita de estado.yaml e eventos.jsonl
# ---------------------------------------------------------------------------

def _caminho_estado(ns):
    return os.path.join(ns, "estado.yaml")


def _caminho_eventos(ns):
    return os.path.join(ns, "eventos.jsonl")


def _ler_estado(ns):
    """Retorna (estado_dict, None) ou (None, mensagem_erro_pt_br)."""
    caminho = _caminho_estado(ns)
    if not os.path.isfile(caminho):
        return None, f"estado não encontrado: {caminho} (rode 'init' primeiro)"
    with open(caminho, "r", encoding="utf-8") as fh:
        try:
            dados = yaml.safe_load(fh)
        except yaml.YAMLError as exc:
            return None, f"{caminho} não é YAML válido: {exc}"
    if not isinstance(dados, dict):
        return None, f"{caminho} malformado (esperado objeto no topo)"
    return dados, None


def _gravar_estado(ns, estado):
    """Escrita atômica (tmp + replace), mesmo padrão de snapshot.py."""
    caminho = _caminho_estado(ns)
    tmp = caminho + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        yaml.safe_dump(estado, fh, allow_unicode=True, sort_keys=False)
    os.replace(tmp, caminho)


def _apendar_evento(ns, gate, veredicto, racional, refs):
    evento = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "gate": gate,
        "veredicto": veredicto,
        "racional": racional,
        "refs": list(refs) if refs else [],
    }
    with open(_caminho_eventos(ns), "a", encoding="utf-8") as fh:
        fh.write(json.dumps(evento, ensure_ascii=False) + "\n")


def _evento_ja_ocorreu(ns, gate_valor):
    """True se algum evento passado tem gate == gate_valor (ex.: 'SET_PROFUNDIDADE')."""
    caminho = _caminho_eventos(ns)
    if not os.path.isfile(caminho):
        return False
    with open(caminho, "r", encoding="utf-8") as fh:
        for linha in fh:
            linha = linha.strip()
            if not linha:
                continue
            try:
                evento = json.loads(linha)
            except json.JSONDecodeError:
                continue
            if evento.get("gate") == gate_valor:
                return True
    return False


def _validar_estado(validar_mod, estado):
    """Valida `estado` (dict em memória) contra schemas/estado.schema.json,
    reusando os helpers internos de validar.py (mesmo schema, mesmo Registry
    de $ref, mesmas mensagens PT-BR) sem precisar gravar em disco antes.
    Retorna lista de mensagens de erro (vazia se válido)."""
    schema, erro = validar_mod._carregar_schema("estado")
    if erro:
        return [erro]
    registry = validar_mod._construir_registry()
    validator = validar_mod.jsonschema.Draft202012Validator(schema, registry=registry)
    erros = sorted(
        validator.iter_errors(estado),
        key=lambda e: [str(p) for p in e.absolute_path],
    )
    return [validar_mod._mensagem_pt(e) for e in erros]


# ---------------------------------------------------------------------------
# Comandos
# ---------------------------------------------------------------------------

def _cmd_init(ns, args, validar_mod):
    caminho = _caminho_estado(ns)
    if os.path.isfile(caminho):
        print(f"erro: {caminho} já existe; init recusado", file=sys.stderr)
        return 1

    profundidade = args.profundidade_provisoria or "PADRAO"
    snapshot = bool(args.snapshot) if args.snapshot is not None else False

    estado = {
        "ticker": args.ticker,
        "data": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "profundidade": profundidade,
        "modo": "PARCIAL",
        "snapshot": snapshot,
        "engine": {"versao": "", "hash": HASH_VAZIO},
        "gates": {g: "PENDENTE" for g in GATES},
    }

    erros = _validar_estado(validar_mod, estado)
    if erros:
        for e in erros:
            print(f"erro: {e}", file=sys.stderr)
        return 1

    os.makedirs(ns, exist_ok=True)
    _gravar_estado(ns, estado)
    racional = f"init ticker={args.ticker} profundidade={profundidade} snapshot={snapshot}"
    _apendar_evento(ns, "INIT", "OK", racional, [])
    print(f"INIT: {args.ticker} @ {ns}")
    return 0


def _cmd_gate(ns, args, validar_mod):
    estado, erro = _ler_estado(ns)
    if erro:
        print(f"erro: {erro}", file=sys.stderr)
        return 1

    gate = args.gate
    veredicto = args.veredicto
    refs = args.ref or []

    if args.profundidade is not None and gate != "G3_0":
        print("erro: --profundidade só é aplicável ao gate G3_0", file=sys.stderr)
        return 1

    if estado["gates"]["G1"] == "VETO":
        print(
            "erro: processo encerrado no G1 (VETO); nenhum gate pode ser fechado depois",
            file=sys.stderr,
        )
        return 1

    erro_refechamento = _checar_refechamento(estado, gate)
    if erro_refechamento:
        print(f"erro: {erro_refechamento}", file=sys.stderr)
        return 1

    erro_dep = _DEP[gate](estado)
    if erro_dep:
        print(f"erro: {erro_dep}", file=sys.stderr)
        return 1

    if gate == "G3_0" and veredicto == "APROVADO":
        if not refs:
            print(
                "erro: G3_0 aprovado exige pelo menos um --ref (arquivo com o gate do engine)",
                file=sys.stderr,
            )
            return 1
        ja_definida = _evento_ja_ocorreu(ns, "SET_PROFUNDIDADE")
        if args.profundidade is None and not ja_definida:
            print(
                "erro: G3_0 aprovado exige profundidade definida via 'set profundidade' "
                "antes, ou via --profundidade nesta chamada",
                file=sys.stderr,
            )
            return 1

    if gate == "G6" and estado.get("snapshot") is False and veredicto != "PULADO":
        print("erro: G6 com snapshot=false só aceita o veredicto PULADO", file=sys.stderr)
        return 1

    if gate == "G4" and veredicto == "ENTREGUE":
        auditoria = estado.get("auditoria") or {}
        if not auditoria.get("acionada"):
            print(
                "erro: G4 com ENTREGUE exige auditoria.acionada=true (rode 'set auditoria' antes)",
                file=sys.stderr,
            )
            return 1

    candidato = copy.deepcopy(estado)
    candidato["gates"][gate] = veredicto
    if gate == "G3_0" and args.profundidade is not None:
        candidato["profundidade"] = args.profundidade
    if gate == "G1" and veredicto == "VETO":
        candidato["status_final"] = "ENCERRADO NO G1 (VETO)"
    if gate == "G8" and veredicto == "ENTREGUE":
        candidato["status_final"] = "ENCERRADO NO G8 (ENTREGUE)"

    erros = _validar_estado(validar_mod, candidato)
    if erros:
        for e in erros:
            print(f"erro: {e}", file=sys.stderr)
        return 1

    _gravar_estado(ns, candidato)
    _apendar_evento(ns, gate, veredicto, args.racional, refs)
    print(f"{gate}: {veredicto}")
    return 0


def _cmd_set(ns, args, validar_mod):
    estado, erro = _ler_estado(ns)
    if erro:
        print(f"erro: {erro}", file=sys.stderr)
        return 1

    candidato = copy.deepcopy(estado)
    alvo = args.alvo

    if alvo == "engine":
        candidato["engine"] = {"versao": args.versao, "hash": args.hash}
        evento_gate = "SET_ENGINE"
        racional = f"engine.versao={args.versao} engine.hash={args.hash}"
    elif alvo == "snapshot":
        valor = args.valor == "true"
        candidato["snapshot"] = valor
        evento_gate = "SET_SNAPSHOT"
        racional = f"snapshot={valor}"
    elif alvo == "profundidade":
        candidato["profundidade"] = args.valor
        evento_gate = "SET_PROFUNDIDADE"
        racional = f"profundidade={args.valor}"
    elif alvo == "modo":
        candidato["modo"] = args.valor
        evento_gate = "SET_MODO"
        racional = f"modo={args.valor}"
    elif alvo == "auditoria":
        acionada = args.acionada == "true"
        aud = {"acionada": acionada}
        if args.agregado is not None:
            aud["agregado"] = args.agregado
        candidato["auditoria"] = aud
        evento_gate = "SET_AUDITORIA"
        racional = f"auditoria.acionada={acionada}"
        if args.agregado is not None:
            racional += f" agregado={args.agregado}"
    else:
        print(f"erro: alvo de set desconhecido: {alvo}", file=sys.stderr)
        return 1

    erros = _validar_estado(validar_mod, candidato)
    if erros:
        for e in erros:
            print(f"erro: {e}", file=sys.stderr)
        return 1

    _gravar_estado(ns, candidato)
    _apendar_evento(ns, evento_gate, "OK", racional, [])
    print(f"{evento_gate}: OK")
    return 0


def _cmd_status(ns, args, validar_mod):
    estado, erro = _ler_estado(ns)
    if erro:
        print(f"erro: {erro}", file=sys.stderr)
        return 1

    linhas = [f"{g}: {estado['gates'][g]}" for g in GATES]

    proximo = None
    for g in GATES:
        if estado["gates"][g] == "PENDENTE" and _DEP[g](estado) is None:
            proximo = g
            break
    linhas.append(f"PROXIMO: {proximo if proximo else '(nenhum)'}")

    pendencias = estado.get("pendencias") or []
    if pendencias:
        linhas.append("PENDENCIAS:")
        for p in pendencias:
            linhas.append(f"  - {p.get('id')}: {p.get('texto')} ({p.get('dono')})")
    else:
        linhas.append("PENDENCIAS: nenhuma")

    if estado.get("status_final"):
        linhas.append(f"STATUS_FINAL: {estado['status_final']}")

    print("\n".join(linhas))
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _construir_parser():
    parser = argparse.ArgumentParser(
        prog="pipeline.py",
        description="Máquina de estados dos gates do processo de research (única via de escrita de estado.yaml).",
    )
    parser.add_argument("ns", help="diretório de análise (contém/conterá estado.yaml e eventos.jsonl)")
    sub = parser.add_subparsers(dest="comando", required=True)

    p_init = sub.add_parser("init", help="cria estado.yaml + eventos.jsonl")
    p_init.add_argument("--ticker", required=True)
    p_init.add_argument(
        "--profundidade-provisoria", dest="profundidade_provisoria",
        choices=PROFUNDIDADES, default=None,
    )
    grupo_snapshot = p_init.add_mutually_exclusive_group()
    grupo_snapshot.add_argument("--snapshot", dest="snapshot", action="store_true", default=None)
    grupo_snapshot.add_argument("--sem-snapshot", dest="snapshot", action="store_false", default=None)

    p_gate = sub.add_parser("gate", help="fecha um gate com um veredicto")
    p_gate.add_argument("gate", choices=GATES)
    p_gate.add_argument("--veredicto", required=True, choices=VEREDICTOS)
    p_gate.add_argument("--racional", required=True)
    p_gate.add_argument("--ref", action="append", default=None)
    p_gate.add_argument("--profundidade", choices=PROFUNDIDADES, default=None)

    p_set = sub.add_parser("set", help="atualiza um campo do estado (fora dos gates)")
    set_sub = p_set.add_subparsers(dest="alvo", required=True)

    sp_engine = set_sub.add_parser("engine")
    sp_engine.add_argument("--versao", required=True)
    sp_engine.add_argument("--hash", required=True)

    sp_snapshot = set_sub.add_parser("snapshot")
    sp_snapshot.add_argument("valor", choices=("true", "false"))

    sp_profundidade = set_sub.add_parser("profundidade")
    sp_profundidade.add_argument("valor", choices=PROFUNDIDADES)

    sp_modo = set_sub.add_parser("modo")
    sp_modo.add_argument("valor", choices=MODOS)

    sp_auditoria = set_sub.add_parser("auditoria")
    sp_auditoria.add_argument("--acionada", required=True, choices=("true", "false"))
    sp_auditoria.add_argument("--agregado", choices=AGREGADOS, default=None)

    sub.add_parser("status", help="imprime a tabela de gates + próximo passo")

    return parser


def main(argv=None):
    parser = _construir_parser()
    args = parser.parse_args(argv)

    if yaml is None:
        print("erro: pyyaml ausente: instale (pip install pyyaml) para rodar pipeline.py", file=sys.stderr)
        return 1

    validar_mod = _carregar_validar()
    if validar_mod.jsonschema is None:
        print(
            "erro: jsonschema (com o pacote referencing) ausente: "
            "instale (pip install jsonschema) para rodar pipeline.py",
            file=sys.stderr,
        )
        return 1

    ns = args.ns

    if args.comando == "init":
        return _cmd_init(ns, args, validar_mod)
    if args.comando == "gate":
        return _cmd_gate(ns, args, validar_mod)
    if args.comando == "set":
        return _cmd_set(ns, args, validar_mod)
    if args.comando == "status":
        return _cmd_status(ns, args, validar_mod)

    print(f"erro: comando desconhecido: {args.comando}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
