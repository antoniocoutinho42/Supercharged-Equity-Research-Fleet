#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""memoria.py — nota de memória durável por ticker, GERADA (F11 do fleet v3).

Uso:
    python scripts/memoria.py <ns> [--saida <dir>] [--sintese <arq.md>] [--licoes <arq.md>]

<ns> é o diretório de análise `analises/<TICKER>` (contém case.json e
saida/results.json, ambos obrigatórios). O script gera/ATUALIZA
`<saida | irmão _memoria do ns>/<TICKER>.md` com estrutura FIXA de 4 seções:

  1. Cabeçalho: ticker + empresa, data da análise, moeda, preço usado e
     versão do engine — sempre regenerado do zero a partir da fonte.
  2. Âncoras numéricas: tabela por cenário + bullets (faixa fair value,
     probability-weighted, hurdle-conditioned) — TUDO extraído por código
     de case.json/results.json via chave pontilhada; NUNCA digitado.
  3. Síntese e decisão: verbatim de --sintese; sem --sintese, a seção da
     nota anterior é preservada (ou placeholder).
  4. Lições reutilizáveis: CUMULATIVA — o conteúdo de --licoes é APENDADO
     sob "### Atualização YYYY-MM-DD"; uma regeneração NUNCA apaga lições.

Escrita atômica (tmp + os.replace). Correção de número: na fonte
(case/results) + regenerar — editar a nota à mão é PROIBIDO.

Exit codes: 0 sucesso; 1 erro de uso/arquivo (mensagens PT-BR em stderr).
Dependências: stdlib pura (as fontes são JSON).
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone

_HEADING_ANCORAS = "## Âncoras numéricas"
_HEADING_SINTESE = "## Síntese e decisão"
_HEADING_LICOES = "## Lições reutilizáveis"
_PLACEHOLDER_SINTESE = "(síntese ainda não registrada)"
_PLACEHOLDER_LICOES = "(nenhuma lição registrada ainda)"

# Colunas numéricas da tabela por cenário: (título, chave pontilhada no
# cenário do results.json, formatador). O rótulo e o peso são resolvidos à
# parte (rótulo: label/output_label do results; peso: case.json).
_COLUNAS_CENARIO = (
    ("K3 (P/L)", "K3_trailing_PE", "num"),
    ("Equity Value", "equity_value", "num"),
    ("Valor/ação", "value_per_share", "num"),
    ("Upside", "vs_market.upside", "pct"),
)


# ----------------------------------------------------------------------------
# IO auxiliar
# ----------------------------------------------------------------------------

def _ler_json(caminho, papel):
    """Retorna (dict, None) ou (None, mensagem_erro_pt_br)."""
    if not os.path.isfile(caminho):
        return None, (
            f"{papel} não encontrado: {caminho} "
            "(o ns deve ser analises/<TICKER> com case.json e saida/results.json)"
        )
    try:
        with open(caminho, "r", encoding="utf-8") as fh:
            dados = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        return None, f"{caminho} não é JSON válido: {exc}"
    if not isinstance(dados, dict):
        return None, f"{caminho} malformado (esperado objeto JSON no topo)"
    return dados, None


# ----------------------------------------------------------------------------
# Navegação e formatação (porte da v2)
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


def _fmt_pct(v):
    if v is None:
        return "—"
    return f"{v * 100:.1f}%"


def _fmt(v, modo):
    return _fmt_pct(v) if modo == "pct" else _fmt_valor(v)


def _tabela_md(cabecalho, linhas):
    out = [
        "| " + " | ".join(cabecalho) + " |",
        "| " + " | ".join(["---"] * len(cabecalho)) + " |",
    ]
    out.extend("| " + " | ".join(linha) + " |" for linha in linhas)
    return "\n".join(out)


def _ordem_cenarios(nomes):
    """Cenário default do engine ('base') primeiro; demais em ordem alfabética."""
    nomes = list(nomes)
    ordem = []
    if "base" in nomes:
        ordem.append("base")
    ordem.extend(sorted(n for n in nomes if n != "base"))
    return ordem


# ----------------------------------------------------------------------------
# Seções 1-2 (sempre regeneradas do zero, por código)
# ----------------------------------------------------------------------------

def _secao_cabecalho(ticker, case, results):
    campos = (
        ("Empresa", _get_path(case, "company")),
        ("Data da análise", _get_path(case, "valuation_date")),
        ("Moeda", _get_path(case, "currency")),
    )
    partes = [f"{rotulo}: {_fmt_valor(v)}" for rotulo, v in campos]
    preco = _fmt_valor(_get_path(case, "market.price_per_share"))
    preco_data = _fmt_valor(_get_path(case, "market.price_date"))
    preco_fonte = _fmt_valor(_get_path(case, "market.price_source"))
    partes.append(f"Preço usado: {preco} ({preco_data}, {preco_fonte})")
    engine = _fmt_valor(_get_path(results, "engine_version"))
    impl = _fmt_valor(_get_path(results, "implementation_version"))
    partes.append(f"Engine: {engine} (impl {impl})")
    return f"# {ticker} — nota de memória\n\n" + " | ".join(partes) + "\n"


def _rotulo_cenario(cen):
    return cen.get("label") or cen.get("output_label") or "—"


def _linha_cenario(nome, cen, peso):
    if not cen.get("computed"):
        valores = ["—"] * len(_COLUNAS_CENARIO)
        return [nome, "INVALID"] + valores + [_fmt_valor(peso)]
    valores = [_fmt(_get_path(cen, chave), modo) for _, chave, modo in _COLUNAS_CENARIO]
    return [nome, _rotulo_cenario(cen)] + valores + [_fmt_valor(peso)]


def _secao_ancoras(case, results):
    cenarios = results.get("scenarios") or {}
    ordem = _ordem_cenarios(cenarios.keys())

    linhas = []
    for nome in ordem:
        peso = _get_path(case, f"scenarios.{nome}.weight")
        linhas.append(_linha_cenario(nome, cenarios[nome] or {}, peso))
    cabecalho = ["cenário", "rótulo"] + [c[0] for c in _COLUNAS_CENARIO] + ["Peso"]
    tabela = _tabela_md(cabecalho, linhas)

    bullets = []

    # faixa fair value: só cenários SEM label_mode "hurdle" no case.json
    fair = [
        _get_path(cenarios.get(nome) or {}, "value_per_share")
        for nome in ordem
        if _get_path(case, f"scenarios.{nome}.label_mode") != "hurdle"
    ]
    fair = [v for v in fair if v is not None]
    if fair:
        faixa = f"{_fmt_valor(min(fair))} – {_fmt_valor(max(fair))}"
    else:
        faixa = "—"
    bullets.append(f"- Faixa fair value/ação (cenários fair_value): {faixa}")

    pw = results.get("probability_weighted") or {}
    if pw.get("value") is not None:
        rotulo = pw.get("label") or "Probability-weighted Equity Value"
        bullets.append(
            f"- Probability-weighted Equity Value: {_fmt_valor(pw.get('value'))} ({rotulo})"
        )

    for nome in ordem:
        if _get_path(case, f"scenarios.{nome}.label_mode") != "hurdle":
            continue
        cen = cenarios.get(nome) or {}
        vps = _fmt_valor(_get_path(cen, "value_per_share"))
        bullets.append(f"- Hurdle-conditioned/ação: {vps} ({nome} — {_rotulo_cenario(cen)})")

    return f"{_HEADING_ANCORAS}\n\n{tabela}\n\n" + "\n".join(bullets) + "\n"


# ----------------------------------------------------------------------------
# Seções 3-4 (3: regenerável/preservada; 4: cumulativa — porte da v2)
# ----------------------------------------------------------------------------

def _extrair_secao(texto_nota, heading, placeholder):
    """Conteúdo atual da seção `heading` (recorte até o próximo heading `## `),
    ou None se a nota/seção não existe ou está no estado placeholder."""
    if texto_nota is None:
        return None
    idx = texto_nota.find(heading)
    if idx == -1:
        return None
    resto = texto_nota[idx + len(heading):]
    m = re.search(r"^## ", resto, flags=re.M)
    if m:
        resto = resto[: m.start()]
    resto = resto.strip("\n").strip()
    if not resto or resto == placeholder:
        return None
    return resto


def _secao_sintese(texto_nota_anterior, sintese_path):
    if sintese_path:
        with open(sintese_path, "r", encoding="utf-8") as fh:
            corpo = fh.read().strip()
    else:
        corpo = _extrair_secao(texto_nota_anterior, _HEADING_SINTESE, _PLACEHOLDER_SINTESE)
    if not corpo:
        corpo = _PLACEHOLDER_SINTESE
    return f"{_HEADING_SINTESE}\n\n{corpo}\n"


def _secao_licoes(texto_nota_anterior, licoes_path):
    existente = _extrair_secao(texto_nota_anterior, _HEADING_LICOES, _PLACEHOLDER_LICOES)

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

def gerar_nota(ticker, case, results, texto_nota_anterior, sintese_path, licoes_path):
    secoes = [
        _secao_cabecalho(ticker, case, results),
        _secao_ancoras(case, results),
        _secao_sintese(texto_nota_anterior, sintese_path),
        _secao_licoes(texto_nota_anterior, licoes_path),
    ]
    return "\n".join(secoes)


def _construir_parser():
    parser = argparse.ArgumentParser(
        prog="memoria.py",
        description=(
            "Gera/atualiza a nota de memória durável por ticker "
            "(<dir>/<TICKER>.md; default: irmão _memoria do ns) a partir de "
            "case.json e saida/results.json — âncoras extraídas por código, "
            "nunca digitadas. Idempotente: síntese preservada e lições "
            "cumulativas entre regenerações."
        ),
    )
    parser.add_argument("ns", help="diretório de análise analises/<TICKER> (contém case.json e saida/results.json)")
    parser.add_argument(
        "--saida", default=None,
        help="diretório para <TICKER>.md (default: <ns>/../_memoria)",
    )
    parser.add_argument(
        "--sintese", default=None,
        help="arquivo .md com a síntese/decisão (3-6 linhas), copiado VERBATIM para a seção 3",
    )
    parser.add_argument(
        "--licoes", default=None,
        help="arquivo .md com lições novas (2-6 bullets) a APENDAR na seção cumulativa",
    )
    return parser


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    parser = _construir_parser()
    args = parser.parse_args(argv)
    ns = os.path.abspath(args.ns)

    case, erro = _ler_json(os.path.join(ns, "case.json"), "case.json")
    if erro:
        print(f"erro: {erro}", file=sys.stderr)
        return 1

    results, erro = _ler_json(os.path.join(ns, "saida", "results.json"), "results.json")
    if erro:
        print(f"erro: {erro}", file=sys.stderr)
        return 1

    for rotulo, caminho in (("síntese", args.sintese), ("lições", args.licoes)):
        if caminho and not os.path.isfile(caminho):
            print(f"erro: arquivo de {rotulo} não encontrado: {caminho}", file=sys.stderr)
            return 1

    ticker = case.get("ticker") or os.path.basename(ns)

    saida_dir = args.saida or os.path.join(os.path.dirname(ns), "_memoria")
    caminho_nota = os.path.join(saida_dir, f"{ticker}.md")

    texto_nota_anterior = None
    if os.path.isfile(caminho_nota):
        with open(caminho_nota, "r", encoding="utf-8") as fh:
            texto_nota_anterior = fh.read()

    nota = gerar_nota(ticker, case, results, texto_nota_anterior, args.sintese, args.licoes)

    os.makedirs(saida_dir, exist_ok=True)
    tmp = caminho_nota + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(nota)
    os.replace(tmp, caminho_nota)

    n_linhas = nota.count("\n") + 1
    print(f"MEMORIA {ticker}: {caminho_nota} ({n_linhas} linhas)")
    if n_linhas > 150:
        print(
            f"aviso: nota com {n_linhas} linhas, acima do teto de ~150 "
            "(enxugar a síntese, nunca as âncoras nem as lições)",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
