#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""delta.py — "git diff" do research: diff estruturado entre dois runs/<hash8>/.

Uso:
    python delta.py <ns> --desde <hash8> [--ate <hash8>] [--saida <dir>]

<ns> é o diretório de análise (contém runs/<hash8>/, inputs.yaml, claims.yaml
e estado.yaml). O script:
  1. Base = <ns>/runs/<desde>/ (deve existir — erro se não).
  2. Alvo = <ns>/runs/<ate>/ se --ate for dado; senão o run apontado por
     <ns>/estado.yaml campo engine.hash (erro claro se estado.yaml ausente,
     sem engine.hash, ou o hash apontado ainda não foi congelado via
     scripts/snapshot.py).
  3. Compara, entre base e alvo:
       fatos.inputs   — flatten (sem descer em listas) do bloco `fatos` dos
                        dois inputs.yaml, ignorando fatos.ledger (reportado
                        à parte no resumo como "ledger: +/-N documentos").
       fatos.claims   — runs/<hash>/claims.yaml de cada lado (ou o
                        <ns>/claims.yaml atual quando o lado não tiver
                        claims.yaml congelado); diff por id.
       premissas      — flatten (mesma mecânica) do bloco `premissas`.
       valuation      — flatten completo (desce em listas) dos dois
                        resultados.json, exceto o bloco `engine` (reportado
                        à parte no campo `engine` do delta.json).
       decisao        — bloco `decisao` de runs/<hash>/estado.yaml de cada
                        lado (ou o <ns>/estado.yaml atual quando o lado não
                        tiver estado.yaml congelado).
  4. Grava <ns>/delta.json (máquina) e <ns>/delta.md (humano, PT-BR), ou em
     --saida <dir> se informado.

Exit codes: 0 sucesso (mesmo sem diferenças); 1 erro de uso/arquivo.
Dependências: stdlib + pyyaml.
"""
import argparse
import json
import os
import sys

try:
    import yaml
except ImportError:
    yaml = None

HASH_VAZIO = "0000000000000000"


# ----------------------------------------------------------------------------
# IO auxiliar
# ----------------------------------------------------------------------------

def _carregar_yaml_opcional(caminho):
    """Lê um .yaml e devolve o dict, ou None se o arquivo não existir."""
    if not os.path.isfile(caminho):
        return None
    with open(caminho, "r", encoding="utf-8") as fh:
        dados = yaml.safe_load(fh)
    return dados if isinstance(dados, dict) else {}


def _carregar_json(caminho):
    with open(caminho, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _localizar_claims(run_dir, ns, permitir_fallback):
    """claims.yaml congelado no run; fallback para <ns>/claims.yaml atual
    SOMENTE quando permitir_fallback=True (contrato: só o lado ALVO cai para
    o claims.yaml atual — o lado BASE é sempre um run imutável do passado;
    se não tiver claims.yaml congelado, é tratado como ausente, nunca
    "atualizado" com o estado presente)."""
    congelado = os.path.join(run_dir, "claims.yaml")
    if os.path.isfile(congelado):
        dados = _carregar_yaml_opcional(congelado)
        return (dados or {}).get("claims", [])
    if not permitir_fallback:
        return None
    atual = _carregar_yaml_opcional(os.path.join(ns, "claims.yaml"))
    if atual is None:
        return None
    return atual.get("claims", [])


def _localizar_decisao(run_dir, ns, permitir_fallback):
    """bloco decisao do estado.yaml congelado no run; fallback para
    <ns>/estado.yaml atual SOMENTE quando permitir_fallback=True (mesma razão
    de _localizar_claims: só o lado ALVO usa o estado atual).
    Devolve (decisao_dict_ou_None, disponivel: bool) — disponivel=False quando
    NENHUM estado.yaml foi encontrado (nem congelado, nem atual quando aplicável)."""
    congelado = os.path.join(run_dir, "estado.yaml")
    if os.path.isfile(congelado):
        dados = _carregar_yaml_opcional(congelado) or {}
        return dados.get("decisao"), True
    if not permitir_fallback:
        return None, False
    atual = _carregar_yaml_opcional(os.path.join(ns, "estado.yaml"))
    if atual is None:
        return None, False
    return atual.get("decisao"), True


# ----------------------------------------------------------------------------
# Flatten / comparação
# ----------------------------------------------------------------------------

def achatar_parar_em_lista(obj, prefixo=""):
    """Flatten de dict em chaves pontilhadas; listas são tratadas como folha
    (não descidas) — usado para fatos/premissas."""
    itens = {}
    if isinstance(obj, dict):
        for chave, valor in obj.items():
            caminho = f"{prefixo}.{chave}" if prefixo else str(chave)
            itens.update(achatar_parar_em_lista(valor, caminho))
    else:
        itens[prefixo] = obj
    return itens


def achatar_completo(obj, prefixo=""):
    """Flatten total (desce em dicts E listas, listas viram chave[i]) — usado
    para o corpo do resultados.json (valuation)."""
    itens = {}
    if isinstance(obj, dict):
        for chave, valor in obj.items():
            caminho = f"{prefixo}.{chave}" if prefixo else str(chave)
            itens.update(achatar_completo(valor, caminho))
    elif isinstance(obj, list):
        for i, valor in enumerate(obj):
            caminho = f"{prefixo}[{i}]"
            itens.update(achatar_completo(valor, caminho))
    else:
        itens[prefixo] = obj
    return itens


def _resumir_valor(valor):
    """Resumo de valores-lista longos/complexos para o antes/depois do delta
    (contrato: 'reportar a chave da lista inteira com antes/depois resumidos')."""
    if isinstance(valor, list):
        if len(valor) <= 5 and all(not isinstance(x, (dict, list)) for x in valor):
            return valor
        return f"{len(valor)} item(ns)"
    return valor


def _sao_iguais(a, b):
    """Compara com tolerância numérica (1e-9); demais tipos por igualdade exata."""
    a_num = isinstance(a, (int, float)) and not isinstance(a, bool)
    b_num = isinstance(b, (int, float)) and not isinstance(b, bool)
    if a_num and b_num:
        return abs(a - b) <= 1e-9
    return a == b


def _diff_achatado(flat_base, flat_alvo, resumir=False):
    diffs = []
    for chave in sorted(set(flat_base) | set(flat_alvo)):
        a = flat_base.get(chave)
        b = flat_alvo.get(chave)
        if _sao_iguais(a, b):
            continue
        entrada = {
            "chave": chave,
            "antes": _resumir_valor(a) if resumir else a,
            "depois": _resumir_valor(b) if resumir else b,
        }
        diffs.append(entrada)
    return diffs


# ----------------------------------------------------------------------------
# Blocos do delta
# ----------------------------------------------------------------------------

def _diff_fatos(inputs_base, inputs_alvo):
    fatos_base = dict(inputs_base.get("fatos") or {})
    fatos_alvo = dict(inputs_alvo.get("fatos") or {})
    ledger_base = fatos_base.pop("ledger", None) or []
    ledger_alvo = fatos_alvo.pop("ledger", None) or []

    flat_base = achatar_parar_em_lista(fatos_base, "fatos")
    flat_alvo = achatar_parar_em_lista(fatos_alvo, "fatos")
    diffs = _diff_achatado(flat_base, flat_alvo, resumir=True)

    delta_ledger = len(ledger_alvo) - len(ledger_base)
    return diffs, delta_ledger


def _diff_claims(claims_base, claims_alvo):
    """Devolve (bloco_claims, nota). bloco_claims é None quando claims.yaml
    está ausente dos dois lados (compat com runs antigos, sem claims.yaml)."""
    if claims_base is None and claims_alvo is None:
        return None, ("claims.yaml ausente nos dois runs (compat com runs "
                       "anteriores ao sistema de claims)")

    base_por_id = {c["id"]: c for c in (claims_base or []) if isinstance(c, dict) and "id" in c}
    alvo_por_id = {c["id"]: c for c in (claims_alvo or []) if isinstance(c, dict) and "id" in c}

    adicionados = sorted(set(alvo_por_id) - set(base_por_id))
    removidos = sorted(set(base_por_id) - set(alvo_por_id))
    modificados = sorted(
        cid for cid in (set(base_por_id) & set(alvo_por_id))
        if base_por_id[cid].get("texto") != alvo_por_id[cid].get("texto")
        or base_por_id[cid].get("fonte") != alvo_por_id[cid].get("fonte")
    )
    bloco = {"adicionados": adicionados, "modificados": modificados, "removidos": removidos}
    return bloco, None


def _diff_premissas(inputs_base, inputs_alvo):
    flat_base = achatar_parar_em_lista(inputs_base.get("premissas") or {}, "premissas")
    flat_alvo = achatar_parar_em_lista(inputs_alvo.get("premissas") or {}, "premissas")
    return _diff_achatado(flat_base, flat_alvo, resumir=True)


def _diff_valuation(res_base, res_alvo):
    corpo_base = {k: v for k, v in res_base.items() if k != "engine"}
    corpo_alvo = {k: v for k, v in res_alvo.items() if k != "engine"}
    flat_base = achatar_completo(corpo_base)
    flat_alvo = achatar_completo(corpo_alvo)
    diffs = []
    for chave in sorted(set(flat_base) | set(flat_alvo)):
        a = flat_base.get(chave)
        b = flat_alvo.get(chave)
        if _sao_iguais(a, b):
            continue
        mudou_sinal = chave.startswith("sinais.") or chave == "gate.modo_recomendado"
        diffs.append({"chave": chave, "antes": a, "depois": b, "mudou_sinal": mudou_sinal})
    return diffs


def _engine_info(res):
    eng = res.get("engine") or {}
    return {"versao": eng.get("versao"), "hash": eng.get("hash_inputs")}


def _diff_decisao(decisao_base, decisao_alvo, base_disponivel, alvo_disponivel):
    campos = sorted(set((decisao_base or {}).keys()) | set((decisao_alvo or {}).keys()))
    diffs = []
    for campo in campos:
        a = (decisao_base or {}).get(campo)
        b = (decisao_alvo or {}).get(campo)
        if a == b:
            continue
        entrada = {"campo": campo, "antes": a, "depois": b}
        notas = []
        if not base_disponivel:
            notas.append("estado.yaml/decisao ausente no run base")
        if not alvo_disponivel:
            notas.append("estado.yaml/decisao ausente no run alvo")
        if notas:
            entrada["nota"] = "; ".join(notas)
        diffs.append(entrada)
    return diffs


# ----------------------------------------------------------------------------
# Orquestração
# ----------------------------------------------------------------------------

def calcular_delta(ns, desde, alvo_hash, base_dir, alvo_dir):
    inputs_base = _carregar_yaml_opcional(os.path.join(base_dir, "inputs.yaml")) or {}
    inputs_alvo = _carregar_yaml_opcional(os.path.join(alvo_dir, "inputs.yaml")) or {}
    res_base = _carregar_json(os.path.join(base_dir, "resultados.json"))
    res_alvo = _carregar_json(os.path.join(alvo_dir, "resultados.json"))

    fatos_diffs, delta_ledger = _diff_fatos(inputs_base, inputs_alvo)
    claims_base = _localizar_claims(base_dir, ns, permitir_fallback=False)
    claims_alvo = _localizar_claims(alvo_dir, ns, permitir_fallback=True)
    claims_bloco, claims_nota = _diff_claims(claims_base, claims_alvo)

    premissas_diffs = _diff_premissas(inputs_base, inputs_alvo)
    valuation_diffs = _diff_valuation(res_base, res_alvo)

    decisao_base, decisao_base_disp = _localizar_decisao(base_dir, ns, permitir_fallback=False)
    decisao_alvo, decisao_alvo_disp = _localizar_decisao(alvo_dir, ns, permitir_fallback=True)
    decisao_diffs = _diff_decisao(decisao_base, decisao_alvo, decisao_base_disp, decisao_alvo_disp)

    n_claims = 0
    if claims_bloco is not None:
        n_claims = (len(claims_bloco["adicionados"]) + len(claims_bloco["modificados"])
                    + len(claims_bloco["removidos"]))

    resumo = {
        "n_fatos": len(fatos_diffs),
        "n_claims": n_claims,
        "n_premissas": len(premissas_diffs),
        "n_valuation": len(valuation_diffs),
        "n_decisao": len(decisao_diffs),
        "sinais_mudaram": any(d["mudou_sinal"] for d in valuation_diffs),
    }
    if delta_ledger != 0:
        sinal = "+" if delta_ledger > 0 else ""
        resumo["ledger"] = f"{sinal}{delta_ledger} documentos"
    if claims_nota:
        resumo["claims_nota"] = claims_nota

    delta = {
        "de": desde,
        "para": alvo_hash,
        "engine": {"antes": _engine_info(res_base), "depois": _engine_info(res_alvo)},
        "fatos": {"inputs": fatos_diffs, "claims": claims_bloco},
        "premissas": premissas_diffs,
        "valuation": valuation_diffs,
        "decisao": decisao_diffs,
        "resumo": resumo,
    }
    if claims_nota:
        delta["fatos"]["claims_nota"] = claims_nota
    return delta


# ----------------------------------------------------------------------------
# delta.md (humano, PT-BR)
# ----------------------------------------------------------------------------

def _fmt_valor(v):
    if v is None:
        return "—"
    if isinstance(v, float):
        return f"{v:.4g}"
    return str(v)


def _tabela(cabecalho, linhas):
    if not linhas:
        return "_nenhuma mudança._\n"
    out = ["| " + " | ".join(cabecalho) + " |",
           "| " + " | ".join(["---"] * len(cabecalho)) + " |"]
    out.extend("| " + " | ".join(linha) + " |" for linha in linhas)
    return "\n".join(out) + "\n"


def gerar_markdown(delta):
    linhas = [f"# Delta: `{delta['de']}` -> `{delta['para']}`\n"]

    r = delta["resumo"]
    total = r["n_fatos"] + r["n_claims"] + r["n_premissas"] + r["n_valuation"] + r["n_decisao"]
    linhas.append("## Resumo\n")
    if total == 0:
        linhas.append("nenhuma mudança.\n")
    else:
        linhas.append(f"- fatos: {r['n_fatos']} mudança(s)")
        linhas.append(f"- claims: {r['n_claims']} mudança(s)")
        linhas.append(f"- premissas: {r['n_premissas']} mudança(s)")
        linhas.append(f"- valuation: {r['n_valuation']} mudança(s)")
        linhas.append(f"- decisão: {r['n_decisao']} mudança(s)")
        linhas.append(f"- sinais mudaram: {'SIM' if r['sinais_mudaram'] else 'não'}")
        if "ledger" in r:
            linhas.append(f"- ledger: {r['ledger']}")
        linhas.append("")
    eng = delta["engine"]
    linhas.append(f"- engine: `{eng['antes']['versao']}` (`{eng['antes']['hash']}`) -> "
                   f"`{eng['depois']['versao']}` (`{eng['depois']['hash']}`)\n")

    linhas.append("## Fatos\n")
    linhas.append("### Inputs\n")
    linhas.append(_tabela(
        ["chave", "antes", "depois"],
        [[d["chave"], _fmt_valor(d["antes"]), _fmt_valor(d["depois"])] for d in delta["fatos"]["inputs"]],
    ))
    linhas.append("### Claims\n")
    claims_bloco = delta["fatos"]["claims"]
    if claims_bloco is None:
        nota = delta["fatos"].get("claims_nota", "")
        linhas.append(f"_claims: indisponível ({nota})._\n")
    else:
        linhas.append(f"- adicionados: {', '.join(claims_bloco['adicionados']) or '—'}")
        linhas.append(f"- modificados: {', '.join(claims_bloco['modificados']) or '—'}")
        linhas.append(f"- removidos: {', '.join(claims_bloco['removidos']) or '—'}\n")

    linhas.append("## Premissas\n")
    linhas.append(_tabela(
        ["chave", "antes", "depois"],
        [[d["chave"], _fmt_valor(d["antes"]), _fmt_valor(d["depois"])] for d in delta["premissas"]],
    ))

    linhas.append("## Valuation\n")
    linhas_val = []
    for d in delta["valuation"]:
        linha = [d["chave"], _fmt_valor(d["antes"]), _fmt_valor(d["depois"])]
        linhas_val.append(linha)
        if d["mudou_sinal"]:
            linhas_val.append(["**MUDANÇA DE CATEGORIA**", "", ""])
    linhas.append(_tabela(["chave", "antes", "depois"], linhas_val))

    linhas.append("## Decisão\n")
    linhas_dec = []
    for d in delta["decisao"]:
        nota = f" _({d['nota']})_" if "nota" in d else ""
        linhas_dec.append([d["campo"] + nota, _fmt_valor(d["antes"]), _fmt_valor(d["depois"])])
    linhas.append(_tabela(["campo", "antes", "depois"], linhas_dec))

    return "\n".join(linhas) + "\n"


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------

def _construir_parser():
    parser = argparse.ArgumentParser(
        prog="delta.py",
        description=(
            "Diff estruturado de fatos, premissas, valuation e decisão entre "
            "dois runs/<hash8>/ imutáveis — o \"git diff\" do research."
        ),
    )
    parser.add_argument("ns", help="diretório de análise (contém runs/<hash8>/)")
    parser.add_argument("--desde", required=True, help="hash8 do run base")
    parser.add_argument("--ate", default=None,
                         help="hash8 do run alvo (default: estado.yaml campo engine.hash)")
    parser.add_argument("--saida", default=None,
                         help="diretório de saída para delta.md/delta.json (default: <ns>)")
    return parser


def main(argv=None):
    parser = _construir_parser()
    args = parser.parse_args(argv)
    ns = args.ns

    if yaml is None:
        print("erro: pyyaml ausente: instale (pip install pyyaml) para rodar delta.py",
              file=sys.stderr)
        return 1

    base_dir = os.path.join(ns, "runs", args.desde)
    if not os.path.isdir(base_dir):
        print(f"erro: run base não encontrado: {base_dir} (rode snapshot.py antes)",
              file=sys.stderr)
        return 1

    if args.ate:
        alvo_hash = args.ate
    else:
        estado_path = os.path.join(ns, "estado.yaml")
        estado = _carregar_yaml_opcional(estado_path)
        if estado is None:
            print(f"erro: --ate não informado e {estado_path} não existe: "
                  "informe --ate <hash8> ou crie estado.yaml com engine.hash",
                  file=sys.stderr)
            return 1
        alvo_hash = (estado.get("engine") or {}).get("hash")
        if not alvo_hash or alvo_hash == HASH_VAZIO:
            print(f"erro: --ate não informado e {estado_path} não tem engine.hash definido "
                  "(rode 'pipeline.py set engine' antes)", file=sys.stderr)
            return 1

    alvo_dir = os.path.join(ns, "runs", alvo_hash)
    if not os.path.isdir(alvo_dir):
        print(f"erro: run alvo não encontrado/não-snapshotado: {alvo_dir} "
              "(rode snapshot.py antes)", file=sys.stderr)
        return 1

    for rotulo, d in (("base", base_dir), ("alvo", alvo_dir)):
        for nome in ("inputs.yaml", "resultados.json"):
            if not os.path.isfile(os.path.join(d, nome)):
                print(f"erro: run {rotulo} ({d}) não tem {nome} — run congelado inválido",
                      file=sys.stderr)
                return 1

    try:
        delta = calcular_delta(ns, args.desde, alvo_hash, base_dir, alvo_dir)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"erro: falha ao calcular delta: {exc}", file=sys.stderr)
        return 1

    saida_dir = args.saida or ns
    os.makedirs(saida_dir, exist_ok=True)
    caminho_json = os.path.join(saida_dir, "delta.json")
    caminho_md = os.path.join(saida_dir, "delta.md")
    with open(caminho_json, "w", encoding="utf-8") as fh:
        json.dump(delta, fh, ensure_ascii=False, indent=2)
    with open(caminho_md, "w", encoding="utf-8") as fh:
        fh.write(gerar_markdown(delta))

    print(f"DELTA {args.desde} -> {alvo_hash}")
    print(f"  {caminho_json}")
    print(f"  {caminho_md}")
    print(f"  resumo: {delta['resumo']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
