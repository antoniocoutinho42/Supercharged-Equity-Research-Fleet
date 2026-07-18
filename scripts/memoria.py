#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""memoria.py — nota de memória durável por ticker, GERADA (Task 3.2).

Uso:
    python memoria.py <ns> [--saida <dir>] [--licoes <arquivo.md>]

<ns> é o diretório de análise (contém estado.yaml, eventos.jsonl e
runs/<hash8>/). O script:
  1. Lê <ns>/estado.yaml (obrigatório), <ns>/eventos.jsonl (opcional) e o run
     canônico <ns>/runs/<engine.hash>/ (resultados.json obrigatório,
     meta.yaml opcional, usado para a versão do engine).
  2. Gera/ATUALIZA <dir>/memoria/<TICKER>.md (default <dir> = <ns>; em
     produção o Coordenador passa --saida /mnt/memory/research).
  3. Estrutura FIXA da nota, sempre nesta ordem:
       1. Cabeçalho: ticker + data, profundidade, modo, engine versão+hash,
          status_final.
       2. Decisão: recomendação, confiança, racional (VERBATIM do bloco
          `decisao`), ressalvas e gatilhos como listas, revisão.
       3. Linha do tempo dos gates: 1 linha por ÚLTIMO evento de cada gate em
          eventos.jsonl; gates re-executados ganham a nota
          "(re-executado Nx)".
       4. Pendências: {id, texto, dono} de estado.yaml.
       5. Âncoras numéricas: SOMENTE hurdle ponderado, faixa e central
          econômicos, sinais e gate.modo_recomendado, extraídos de
          resultados.json no formato "valor (chave.json)". Nada além dessas
          6-8 linhas — a nota NÃO duplica o valuation nem o dossiê.
       6. Lições reutilizáveis: conteúdo de --licoes (quando informado) É
          APENDADO à seção da nota anterior (se existir), com marcador de
          data; sem --licoes, a seção anterior é preservada INTACTA. Uma
          regeneração NUNCA apaga lições antigas.
  4. As seções 1-5 são sempre regeneradas do zero a partir da fonte; só a
     seção 6 é cumulativa. Escreve com tmp + os.replace (atômico).

Exit codes: 0 sucesso; 1 erro de uso/arquivo (mensagens PT-BR em stderr).
Dependências: stdlib + pyyaml.
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone

try:
    import yaml
except ImportError:
    yaml = None

HASH_VAZIO = "0000000000000000"

_GATES_ORDEM = ("G1", "G1_5", "G2", "G3_0", "G3", "G4", "G5", "G6", "G7", "G8")

_ANCORAS = (
    ("Hurdle ponderado", "hurdle.cenarios.ponderado"),
    ("Faixa econômica", "economico.faixa_ponderada"),
    ("Central econômico", "economico.central_ponderado"),
    ("Sinal econômico", "sinais.economico"),
    ("Sinal de entrada", "sinais.entrada"),
    ("Modo recomendado", "gate.modo_recomendado"),
)

_HEADING_LICOES = "## Lições reutilizáveis"
_PLACEHOLDER_LICOES = "(nenhuma lição registrada ainda)"


# ----------------------------------------------------------------------------
# IO auxiliar
# ----------------------------------------------------------------------------

def _ler_estado(ns):
    """Retorna (estado_dict, None) ou (None, mensagem_erro_pt_br)."""
    caminho = os.path.join(ns, "estado.yaml")
    if not os.path.isfile(caminho):
        return None, f"estado não encontrado: {caminho} (rode pipeline.py init primeiro)"
    with open(caminho, "r", encoding="utf-8") as fh:
        try:
            dados = yaml.safe_load(fh)
        except yaml.YAMLError as exc:
            return None, f"{caminho} não é YAML válido: {exc}"
    if not isinstance(dados, dict):
        return None, f"{caminho} malformado (esperado objeto no topo)"
    return dados, None


def _ler_eventos(ns):
    """Lê eventos.jsonl (lista de dicts); arquivo ausente -> lista vazia
    (a memória ainda é gerável antes do primeiro gate fechar)."""
    caminho = os.path.join(ns, "eventos.jsonl")
    if not os.path.isfile(caminho):
        return []
    eventos = []
    with open(caminho, "r", encoding="utf-8") as fh:
        for linha in fh:
            linha = linha.strip()
            if not linha:
                continue
            try:
                eventos.append(json.loads(linha))
            except json.JSONDecodeError:
                continue
    return eventos


def _ler_run_canonico(ns, hash8):
    """Retorna (resultados_dict, meta_dict, None) ou (None, None, erro_pt_br)."""
    run_dir = os.path.join(ns, "runs", hash8)
    resultados_path = os.path.join(run_dir, "resultados.json")
    if not os.path.isfile(resultados_path):
        return None, None, (
            f"run canônico não encontrado/sem resultados.json: {run_dir} "
            "(rode snapshot.py antes de gerar a memória)"
        )
    try:
        with open(resultados_path, "r", encoding="utf-8") as fh:
            resultados = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        return None, None, f"falha ao ler {resultados_path}: {exc}"

    meta = {}
    meta_path = os.path.join(run_dir, "meta.yaml")
    if os.path.isfile(meta_path):
        try:
            with open(meta_path, "r", encoding="utf-8") as fh:
                meta = yaml.safe_load(fh) or {}
        except yaml.YAMLError as exc:
            return None, None, f"{meta_path} não é YAML válido: {exc}"

    return resultados, meta, None


# ----------------------------------------------------------------------------
# Formatação
# ----------------------------------------------------------------------------

def _get_path(d, caminho):
    cur = d
    for parte in caminho.split("."):
        if isinstance(cur, dict):
            cur = cur.get(parte)
        else:
            return None
    return cur


def _fmt_valor(v):
    if v is None:
        return "—"
    if isinstance(v, float):
        return f"{v:.2f}"
    return str(v)


def _truncar(texto, limite=110):
    texto = " ".join(str(texto).split())
    if len(texto) > limite:
        return texto[: limite - 1].rstrip() + "…"
    return texto


def _tabela_md(cabecalho, linhas):
    out = [
        "| " + " | ".join(cabecalho) + " |",
        "| " + " | ".join(["---"] * len(cabecalho)) + " |",
    ]
    out.extend("| " + " | ".join(linha) + " |" for linha in linhas)
    return "\n".join(out)


# ----------------------------------------------------------------------------
# Seções (geradas)
# ----------------------------------------------------------------------------

def _secao_cabecalho(ticker, estado, meta):
    data = estado.get("data") or "—"
    profundidade = estado.get("profundidade") or "—"
    modo = estado.get("modo") or "—"
    engine = estado.get("engine") or {}
    hash8 = engine.get("hash") or "—"
    versao = (meta or {}).get("engine_versao") or engine.get("versao") or "—"
    status_final = estado.get("status_final") or "(em andamento)"
    linha = (
        f"Data: {data} | Profundidade: {profundidade} | Modo: {modo} | "
        f"Engine: {versao} ({hash8}) | Status final: {status_final}"
    )
    return f"# {ticker} — nota de memória\n\n{linha}\n"


def _secao_decisao(decisao):
    if not isinstance(decisao, dict):
        return "## Decisão\n\n(decisão ainda não registrada)\n"

    linhas = ["## Decisão\n"]
    linhas.append(
        f"**Recomendação:** {decisao.get('recomendacao', '—')} "
        f"(confiança: {decisao.get('confianca', '—')})\n"
    )
    racional = decisao.get("racional")
    if racional:
        linhas.append(racional + "\n")

    ressalvas = decisao.get("ressalvas") or []
    linhas.append("Ressalvas:")
    linhas.extend(f"- {r}" for r in ressalvas) if ressalvas else linhas.append("- (nenhuma)")
    linhas.append("")

    gatilhos = decisao.get("gatilhos") or []
    linhas.append("Gatilhos:")
    linhas.extend(f"- {g}" for g in gatilhos) if gatilhos else linhas.append("- (nenhum)")
    linhas.append("")

    revisao = decisao.get("revisao")
    linhas.append(f"Revisão: {revisao if revisao else '—'}")
    return "\n".join(linhas) + "\n"


def _linhas_do_tempo(eventos):
    """1 linha por ÚLTIMO evento de cada gate (na ordem canônica dos gates),
    com nota '(re-executado Nx)' quando o gate apareceu N>1 vezes."""
    por_gate = {}
    for ev in eventos:
        gate = ev.get("gate")
        if gate not in _GATES_ORDEM:
            continue
        por_gate.setdefault(gate, []).append(ev)

    linhas = []
    for gate in _GATES_ORDEM:
        evs = por_gate.get(gate)
        if not evs:
            continue
        ultimo = evs[-1]
        veredicto = ultimo.get("veredicto", "—")
        n = len(evs)
        if n > 1:
            veredicto = f"{veredicto} (re-executado {n}x)"
        racional_curto = _truncar(ultimo.get("racional", ""))
        refs = ultimo.get("refs") or []
        refs_txt = ", ".join(refs) if refs else "—"
        linhas.append([gate, veredicto, racional_curto, refs_txt])
    return linhas


def _secao_timeline(eventos):
    linhas = _linhas_do_tempo(eventos)
    corpo = ["## Linha do tempo dos gates\n"]
    if not linhas:
        corpo.append("_nenhum gate registrado ainda._")
    else:
        corpo.append(_tabela_md(["gate", "veredicto", "racional_curto", "refs"], linhas))
    return "\n".join(corpo) + "\n"


def _secao_pendencias(pendencias):
    linhas = ["## Pendências\n"]
    if not pendencias:
        linhas.append("(nenhuma pendência aberta)")
    else:
        for p in pendencias:
            linhas.append(
                f"- **{p.get('id', '?')}**: {p.get('texto', '')} (dono: {p.get('dono', '?')})"
            )
    return "\n".join(linhas) + "\n"


def _secao_ancoras(resultados):
    linhas = ["## Âncoras numéricas\n"]
    for rotulo, chave in _ANCORAS:
        valor = _get_path(resultados, chave)
        if isinstance(valor, list):
            texto_valor = " – ".join(_fmt_valor(x) for x in valor)
        else:
            texto_valor = _fmt_valor(valor)
        linhas.append(f"- {rotulo}: {texto_valor} ({chave})")
    return "\n".join(linhas) + "\n"


def _extrair_licoes_existentes(caminho_nota):
    """Conteúdo atual da seção '## Lições reutilizáveis' da nota anterior, ou
    None se a nota não existe ainda ou a seção estiver no estado placeholder
    (nada a preservar)."""
    if not os.path.isfile(caminho_nota):
        return None
    with open(caminho_nota, "r", encoding="utf-8") as fh:
        texto = fh.read()
    idx = texto.find(_HEADING_LICOES)
    if idx == -1:
        return None
    resto = texto[idx + len(_HEADING_LICOES):].strip("\n")
    if not resto or resto == _PLACEHOLDER_LICOES:
        return None
    return resto


def _secao_licoes(caminho_nota, licoes_path):
    existente = _extrair_licoes_existentes(caminho_nota)

    novo_conteudo = None
    if licoes_path:
        with open(licoes_path, "r", encoding="utf-8") as fh:
            novo_conteudo = fh.read().strip()

    partes = []
    if existente:
        partes.append(existente)
    if novo_conteudo:
        marcador = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        partes.append(f"### Atualização {marcador}\n\n{novo_conteudo}")

    corpo = "\n\n".join(partes) if partes else _PLACEHOLDER_LICOES
    return f"{_HEADING_LICOES}\n\n{corpo}\n"


# ----------------------------------------------------------------------------
# Orquestração
# ----------------------------------------------------------------------------

def gerar_nota(ns, estado, eventos, resultados, meta, caminho_nota, licoes_path):
    ticker = estado["ticker"]
    secoes = [
        _secao_cabecalho(ticker, estado, meta),
        _secao_decisao(estado.get("decisao")),
        _secao_timeline(eventos),
        _secao_pendencias(estado.get("pendencias") or []),
        _secao_ancoras(resultados),
        _secao_licoes(caminho_nota, licoes_path),
    ]
    return "\n".join(secoes)


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------

def _construir_parser():
    parser = argparse.ArgumentParser(
        prog="memoria.py",
        description=(
            "Gera/atualiza a nota de memória durável por ticker "
            "(<dir>/memoria/<TICKER>.md) a partir de estado.yaml, eventos.jsonl "
            "e do run canônico runs/<hash8>/ — a nota NÃO duplica dossiê nem "
            "valuation. Idempotente: lições preservadas entre regenerações. "
            "Em produção o Coordenador passa --saida /mnt/memory/research."
        ),
    )
    parser.add_argument("ns", help="diretório de análise (contém estado.yaml, eventos.jsonl, runs/)")
    parser.add_argument(
        "--saida", default=None,
        help="diretório base para memoria/<TICKER>.md (default: <ns>; produção: /mnt/memory/research)",
    )
    parser.add_argument(
        "--licoes", default=None,
        help="arquivo .md com lições novas (2-6 bullets) a APENDAR na seção preservada",
    )
    return parser


def main(argv=None):
    parser = _construir_parser()
    args = parser.parse_args(argv)
    ns = args.ns

    if yaml is None:
        print("erro: pyyaml ausente: instale (pip install pyyaml) para rodar memoria.py",
              file=sys.stderr)
        return 1

    estado, erro = _ler_estado(ns)
    if erro:
        print(f"erro: {erro}", file=sys.stderr)
        return 1

    ticker = estado.get("ticker")
    if not ticker:
        print(f"erro: estado.yaml sem campo 'ticker' em {ns}", file=sys.stderr)
        return 1

    engine = estado.get("engine") or {}
    hash8 = engine.get("hash")
    if not hash8 or hash8 == HASH_VAZIO:
        print(
            "erro: estado.yaml sem engine.hash definido (rode 'pipeline.py set engine' e "
            "'snapshot.py' antes de gerar a memória)",
            file=sys.stderr,
        )
        return 1

    resultados, meta, erro = _ler_run_canonico(ns, hash8)
    if erro:
        print(f"erro: {erro}", file=sys.stderr)
        return 1

    if args.licoes and not os.path.isfile(args.licoes):
        print(f"erro: arquivo de lições não encontrado: {args.licoes}", file=sys.stderr)
        return 1

    eventos = _ler_eventos(ns)

    saida_dir = args.saida or ns
    memoria_dir = os.path.join(saida_dir, "memoria")
    caminho_nota = os.path.join(memoria_dir, f"{ticker}.md")

    nota = gerar_nota(ns, estado, eventos, resultados, meta, caminho_nota, args.licoes)

    os.makedirs(memoria_dir, exist_ok=True)
    tmp = caminho_nota + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(nota)
    os.replace(tmp, caminho_nota)

    n_linhas = nota.count("\n") + 1
    print(f"MEMORIA {ticker}: {caminho_nota} ({n_linhas} linhas)")
    if n_linhas > 150:
        print(
            f"aviso: nota com {n_linhas} linhas, acima do teto de ~150 "
            "(as seções geradas são as culpadas: bug ou estado inchado; nunca corte lições)",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
