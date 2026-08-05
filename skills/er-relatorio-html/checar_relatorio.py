#!/usr/bin/env python3
"""checar_relatorio.py — QC final por código do relatório HTML (fleet v3).

Audita um HTML JÁ EMITIDO pelo build_report.py contra o namespace da análise
(case.json, saida/results.json, dados/*) e contra o próprio contrato do
relatório — detecção de adulteração e de contrato quebrado. NUNCA recomputa
valuation: só compara valores já emitidos pelo engine.

Uso:
  python skills/er-relatorio-html/checar_relatorio.py <ns> [--html <path>]

Default de --html: <ns>/relatorio/relatorio_<TICKER>.html (ticker do case.json
ou, na falta, o nome do diretório do namespace).

Exit 0: limpo — imprime "LIMPO: N checagens".
Exit 1: imprime CADA violação em linha própria, prefixada pela categoria:

  [estrutura]     REPORT_DATA extraído e parseado; por cenário, inputs
                  idênticos ao case.json (os 16 canônicos) e python_expected
                  (K3, equity_value) igual ao results.json (tol 1e-9);
                  header.fair_value_base_ps == value_per_share do cenário
                  default. Bloco ausente = violação.
  [log]           cada entrada do script#log-consistencia re-resolvida na
                  fonte declarada (results.json / case.json / dados/<arquivo> /
                  saida/market_implied.json — nesta, a chave é <PARAM>.<campo>
                  navegada sob params.; chave pontilhada, índices de lista, -1
                  permitido): valor bate (tol 1e-9), texto == re-formatação do
                  valor da fonte e texto aparece no HTML. Bloco ausente =
                  violação; fonte citada com arquivo inexistente = violação.
  [paridade]      chamada k3SelfTest presente, elemento id="parity" presente,
                  REPORT_DATA.parity_vectors não-vazio; COM node, o engine
                  EMBUTIDO no HTML é extraído e re-executado (--selftest)
                  contra os python_expected dos cenários + parity_vectors —
                  divergência = engine adulterado dentro do HTML. Sem node o
                  sub-check é pulado com aviso (não é violação).
  [autocontencao] mesmas regexes RE_RECURSO_EXTERNO do build_report.py sobre
                  o HTML sem os <a href=http...> (anchors de citação
                  permitidos).
  [charts]        overlays exigem fonte_chave (case:<chave>|results:<chave>) e
                  valor conferido (tol 1e-9); série "direta" tem cada y
                  não-nulo presente numericamente no arquivo fonte (tol
                  max(1e-9, 1e-6*|v|)); "derivada" exige formula_nota; série
                  com <10 pontos exige nota_janela; modo completo exige >= 5
                  gráficos.
  [numeros]       números órfãos na prosa (campos *_html + header.sintese +
                  positives/negatives): todo candidato numérico fora de
                  <span class="num-livre"> deve constar em algum texto do log
                  de consistência. Referências de seção (§4.1) e versões
                  (V2.2.1) são removidas antes de tokenizar; inteiros puros
                  (anos inclusive) não são candidatos; decimal PT-BR é UM token
                  (3,74x continua violação, reportada inteira).

Sem dependências fora da stdlib.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

TOL = 1e-9

CANONICAL_INPUTS = ["ROE1", "ROE2", "g1", "g2", "Ke1", "Ke2", "n1", "n2",
                    "NDE1", "NDE2", "GDE1", "GDE2", "F", "g_T", "Kd_F2", "t"]

# --- contrato compartilhado com build_report.py (cópia deliberada: o checar é
# --- um auditor autônomo e não importa o builder que ele audita) -------------
RE_RECURSO_EXTERNO = (
    re.compile(r"(?:src|srcset)\s*=\s*[\"']https?://", re.I),
    re.compile(r"<link[^>]+href\s*=\s*[\"']https?://", re.I),
    re.compile(r"@import\s+(?:url\()?[\"']?https?://", re.I),
    re.compile(r"\bXMLHttpRequest\b"),
    re.compile(r"\bfetch\s*\("),
    re.compile(r"\bimport\s*\(\s*[\"']https?://"),
)
RE_ANCHOR_CITACAO = re.compile(r"<a\s[^>]*href\s*=\s*[\"']https?://[^>]*>", re.I)

RE_REPORT_DATA = re.compile(r"var REPORT_DATA = (\{.*?\});\n</script>", re.S)
RE_LOG_CONSISTENCIA = re.compile(
    r'<script type="application/json" id="log-consistencia">(.*?)</script>', re.S)
RE_SELFTEST_CALL = re.compile(r"\bk3SelfTest\s*\(")
RE_SCRIPT_SIMPLES = re.compile(r"<script>(.*?)</script>", re.S)
MARCA_ENGINE = "k3_engine.js — Justified P/E"

FONTE_IMPLIED = "saida/market_implied.json"

RE_NUM_LIVRE = re.compile(r'<span class="num-livre">.*?</span>', re.S)
RE_TAG = re.compile(r"<[^>]+>")
# ruído removido ANTES de tokenizar: referência de seção do manual e versão colada
RE_REF_SECAO = re.compile(r"§\s*\d+(?:\.\d+)*")
RE_VERSAO = re.compile(r"\bV\d+(?:\.\d+)+", re.I)
# um número = UM token; alternativas em ordem (milhar inglês, percentual, múltiplo,
# decimal solto — PT-BR com vírgula inclusive). Inteiros puros ficam FORA.
RE_NUM_CANDIDATO = re.compile(
    r"\d{1,3}(?:,\d{3})+(?:\.\d+)?(?:%|x)?"
    r"|\d+(?:[.,]\d+)?\s*%"
    r"|\d+(?:[.,]\d+)?x"
    r"|\d+[.,]\d+")
RE_ANO = re.compile(r"(19|20)\d{2}")


def get_path(obj, dotted: str):
    """Navegação por chave pontilhada; índices inteiros p/ listas (-1 = último)."""
    cur = obj
    for part in dotted.split("."):
        if isinstance(cur, dict):
            if part not in cur:
                return None
            cur = cur[part]
        elif isinstance(cur, list):
            try:
                cur = cur[int(part)]
            except (ValueError, IndexError):
                return None
        else:
            return None
    return cur


def fmt_placeholder(valor, spec: str | None) -> str:
    """Mesma formatação do build_report.py (re-deriva o texto esperado do log)."""
    if valor is None or not isinstance(valor, (int, float)) or isinstance(valor, bool):
        raise ValueError("valor ausente ou não numérico")
    spec = spec or "2"
    if spec.startswith("pct"):
        nd = int(spec[3:] or "1")
        return f"{100.0 * valor:.{nd}f}%"
    if spec == "x":
        return f"{valor:.2f}x"
    nd = int(spec)
    return f"{valor:,.{nd}f}"


def eh_num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def num_eq(a, b, tol: float = TOL) -> bool:
    if a is None and b is None:
        return True
    if not (eh_num(a) and eh_num(b)):
        return False
    return abs(a - b) <= tol


def coletar_numeros(obj, out=None) -> list:
    """Todos os números de um JSON, recursivamente (bool excluído)."""
    if out is None:
        out = []
    if eh_num(obj):
        out.append(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            coletar_numeros(v, out)
    elif isinstance(obj, list):
        for v in obj:
            coletar_numeros(v, out)
    return out


class Checador:
    def __init__(self):
        self.violacoes: list[str] = []
        self.checagens = 0

    def check(self, categoria: str, ok: bool, msg: str) -> bool:
        self.checagens += 1
        if not ok:
            self.violacoes.append(f"[{categoria}] {msg}")
        return ok

    def viola(self, categoria: str, msg: str) -> None:
        self.checagens += 1
        self.violacoes.append(f"[{categoria}] {msg}")


# ----------------------------------------------------------------------------
# 1. [estrutura]
# ----------------------------------------------------------------------------

def checar_estrutura(chk: Checador, html: str, case: dict, results: dict):
    m = RE_REPORT_DATA.search(html)
    if not chk.check("estrutura", bool(m), "bloco REPORT_DATA ausente do HTML"):
        return None
    try:
        data = json.loads(m.group(1))
    except json.JSONDecodeError as e:
        chk.viola("estrutura", f"REPORT_DATA não é JSON válido ({e})")
        return None

    rd_scens = data.get("scenarios") or {}
    res_scens = results.get("scenarios") or {}
    for nome, sc_case in (case.get("scenarios") or {}).items():
        rd = rd_scens.get(nome)
        if not chk.check("estrutura", rd is not None,
                         f"cenário {nome} ausente do REPORT_DATA.scenarios"):
            continue
        inputs_rd = rd.get("inputs") or {}
        inputs_case = sc_case.get("inputs") or {}
        for k in CANONICAL_INPUTS:
            chk.check("estrutura", inputs_rd.get(k) == inputs_case.get(k),
                      f"cenário {nome}: input {k} do REPORT_DATA "
                      f"({inputs_rd.get(k)!r}) difere do case.json ({inputs_case.get(k)!r})")
        rres = res_scens.get(nome) or {}
        pe = rd.get("python_expected")
        if pe:
            chk.check("estrutura", num_eq(pe.get("K3"), rres.get("K3_trailing_PE")),
                      f"cenário {nome}: python_expected.K3 ({pe.get('K3')!r}) difere de "
                      f"results.json scenarios.{nome}.K3_trailing_PE "
                      f"({rres.get('K3_trailing_PE')!r})")
            chk.check("estrutura", num_eq(pe.get("equity_value"), rres.get("equity_value")),
                      f"cenário {nome}: python_expected.equity_value "
                      f"({pe.get('equity_value')!r}) difere de results.json "
                      f"scenarios.{nome}.equity_value ({rres.get('equity_value')!r})")
        else:
            chk.check("estrutura", not rres.get("computed"),
                      f"cenário {nome}: python_expected ausente com resultado "
                      f"computado em results.json")

    default = data.get("default_scenario") or "base"
    esperado = (res_scens.get(default) or {}).get("value_per_share")
    fv = (data.get("header") or {}).get("fair_value_base_ps")
    chk.check("estrutura", num_eq(fv, esperado),
              f"header.fair_value_base_ps ({fv!r}) difere de "
              f"scenarios.{default}.value_per_share ({esperado!r}) no results.json")
    return data


# ----------------------------------------------------------------------------
# 2. [log]
# ----------------------------------------------------------------------------

def checar_log(chk: Checador, html: str, case: dict, results: dict, ns: Path):
    m = RE_LOG_CONSISTENCIA.search(html)
    if not chk.check("log", bool(m), "bloco script#log-consistencia ausente do HTML"):
        return None
    try:
        log = json.loads(m.group(1))
    except json.JSONDecodeError as e:
        chk.viola("log", f"log-consistencia não é JSON válido ({e})")
        return None

    dados_cache: dict[str, object] = {}
    implied_cache: list = []  # [obj|None] — lido no máximo uma vez
    for i, e in enumerate(log):
        fonte, chave = e.get("fonte"), e.get("chave")
        rot = f"log[{i}] ({e.get('onde')}: {fonte}:{chave})"
        if fonte == "results.json":
            base = results
        elif fonte == "case.json":
            base = case
        elif fonte == FONTE_IMPLIED:
            if not implied_cache:
                p = ns / FONTE_IMPLIED
                implied_cache.append(json.loads(p.read_text(encoding="utf-8"))
                                     if p.exists() else None)
            base = implied_cache[0]
            if not chk.check("log", base is not None,
                             f"{rot}: arquivo {FONTE_IMPLIED} inexistente no namespace "
                             "(o relatório cita market-implied sem a fonte persistida)"):
                continue
            chave = f"params.{chave}" if isinstance(chave, str) else chave
        elif isinstance(fonte, str) and fonte.startswith("dados/"):
            if fonte not in dados_cache:
                p = ns / fonte
                dados_cache[fonte] = (json.loads(p.read_text(encoding="utf-8"))
                                      if p.exists() else None)
            base = dados_cache[fonte]
            if not chk.check("log", base is not None,
                             f"{rot}: arquivo {fonte} inexistente no namespace"):
                continue
        else:
            chk.viola("log", f"{rot}: fonte desconhecida {fonte!r}")
            continue

        valor_fonte = get_path(base, chave) if isinstance(chave, str) else None
        v_log = e.get("valor")
        chk.check("log", eh_num(valor_fonte) and num_eq(valor_fonte, v_log),
                  f"{rot}: valor registrado {v_log!r} não bate com a fonte "
                  f"({valor_fonte!r}, tol {TOL})")
        texto = e.get("texto")
        try:
            texto_esperado = fmt_placeholder(valor_fonte, e.get("spec"))
        except ValueError:
            texto_esperado = None
        chk.check("log", texto_esperado is not None and texto == texto_esperado,
                  f"{rot}: texto {texto!r} difere da re-formatação do valor da fonte "
                  f"({texto_esperado!r})")
        chk.check("log", isinstance(texto, str) and texto in html,
                  f"{rot}: texto {texto!r} não aparece no HTML")
    return log


# ----------------------------------------------------------------------------
# 3. [paridade]
# ----------------------------------------------------------------------------

def checar_paridade(chk: Checador, html: str, data: dict | None):
    chk.check("paridade", bool(RE_SELFTEST_CALL.search(html)),
              "chamada k3SelfTest ausente do HTML (self-test de paridade removido)")
    chk.check("paridade", 'id="parity"' in html, 'elemento id="parity" ausente do HTML')
    if data is not None:
        chk.check("paridade", bool(data.get("parity_vectors")),
                  "REPORT_DATA.parity_vectors vazio ou ausente")

    node = shutil.which("node")
    if not node:
        print("[paridade] aviso: node indisponível — sub-check do engine embutido "
              "PULADO (não é violação)")
        return

    engine = next((m.group(1) for m in RE_SCRIPT_SIMPLES.finditer(html)
                   if MARCA_ENGINE in m.group(1)), None)
    if not chk.check("paridade", engine is not None,
                     "engine embutido (k3_engine.js) não encontrado no HTML"):
        return
    if data is None:
        return
    vectors = [{"name": n, "inputs": s.get("inputs"), "NI0": s.get("NI0"),
                "Book0": s.get("Book0"), "expected": s["python_expected"]}
               for n, s in (data.get("scenarios") or {}).items()
               if s.get("python_expected")]
    vectors += data.get("parity_vectors") or []
    if not vectors:
        return  # parity_vectors vazio já é violação acima

    fd, tmp = tempfile.mkstemp(suffix=".js", prefix="k3_embutido_")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(engine)
        proc = subprocess.run([node, tmp, "--selftest"], input=json.dumps(vectors),
                              capture_output=True, text=True, encoding="utf-8",
                              timeout=60)
        try:
            r = json.loads(proc.stdout)
        except json.JSONDecodeError:
            chk.viola("paridade", "selftest do engine embutido não rodou sob node: "
                      f"{(proc.stderr or proc.stdout)[:200]!r}")
            return
        chk.check("paridade", bool(r.get("pass")),
                  "engine embutido no HTML divergiu dos python_expected/parity_vectors "
                  "(engine ADULTERADO dentro do HTML?): "
                  + "; ".join(str(f) for f in (r.get("failures") or [])[:3]))
    finally:
        os.unlink(tmp)


# ----------------------------------------------------------------------------
# 4. [autocontencao]
# ----------------------------------------------------------------------------

def checar_autocontencao(chk: Checador, html: str):
    corpo = RE_ANCHOR_CITACAO.sub("", html)  # anchors de citação permitidos
    for rx in RE_RECURSO_EXTERNO:
        m = rx.search(corpo)
        chk.check("autocontencao", m is None,
                  f"carregamento externo de recurso no HTML: {m.group(0)!r}" if m else "")


# ----------------------------------------------------------------------------
# 5. [charts]
# ----------------------------------------------------------------------------

def checar_charts(chk: Checador, data: dict | None, case: dict, results: dict, ns: Path):
    if data is None:
        return
    charts = (data.get("analise") or {}).get("charts") or []
    if data.get("modo") == "completo":
        chk.check("charts", len(charts) >= 5,
                  "modo completo exige >= 5 gráficos (obrigatórios 1-5 do desenho; "
                  "spec com série vazia degrada mas conta)")

    fontes_cache: dict[str, list | None] = {}
    for idx, ch in enumerate(charts):
        rot = f"gráfico {ch.get('id') or idx}"
        for j, ov in enumerate(ch.get("overlays") or []):
            nome_ov = ov.get("label") or f"overlay[{j}]"
            fk = ov.get("fonte_chave")
            if not chk.check("charts", bool(fk), f"{rot}: {nome_ov} sem fonte_chave"):
                continue
            origem, _, chave = fk.partition(":")
            base = {"case": case, "results": results}.get(origem)
            if not chk.check("charts", base is not None,
                             f"{rot}: {nome_ov} com fonte_chave de origem desconhecida "
                             f"({fk!r}; use case:<chave> ou results:<chave>)"):
                continue
            v_fonte = get_path(base, chave)
            chk.check("charts", eh_num(v_fonte) and num_eq(v_fonte, ov.get("valor")),
                      f"{rot}: {nome_ov} valor {ov.get('valor')!r} não bate com "
                      f"{fk} ({v_fonte!r}, tol {TOL})")

        serie_curta = False
        for s in ch.get("series") or []:
            nome_s = s.get("label") or "série"
            y = s.get("y") or []
            if len(y) < 10:
                serie_curta = True
            deriv = s.get("derivacao")
            if deriv == "direta":
                fonte = s.get("fonte")
                if not chk.check("charts", bool(fonte),
                                 f"{rot}: série '{nome_s}' direta sem fonte"):
                    continue
                if fonte not in fontes_cache:
                    p = ns / fonte
                    fontes_cache[fonte] = (coletar_numeros(
                        json.loads(p.read_text(encoding="utf-8")))
                        if p.exists() else None)
                nums = fontes_cache[fonte]
                if not chk.check("charts", nums is not None,
                                 f"{rot}: série '{nome_s}' com fonte inexistente "
                                 f"({fonte})"):
                    continue
                for v in y:
                    if v is None:
                        continue
                    if not chk.check("charts", eh_num(v), f"{rot}: série '{nome_s}' "
                                     f"com valor não numérico {v!r}"):
                        continue
                    tol_v = max(TOL, 1e-6 * abs(v))
                    chk.check("charts", any(abs(n - v) <= tol_v for n in nums),
                              f"{rot}: valor {v!r} da série '{nome_s}' (derivação "
                              f"direta) não existe numericamente em {fonte}")
            elif deriv == "derivada":
                chk.check("charts", bool(str(s.get("formula_nota") or "").strip()),
                          f"{rot}: série '{nome_s}' derivada sem formula_nota")
        if serie_curta:
            chk.check("charts", bool(str(ch.get("nota_janela") or "").strip()),
                      f"{rot}: série com menos de 10 pontos exige nota_janela não-vazia")


# ----------------------------------------------------------------------------
# 6. [numeros]
# ----------------------------------------------------------------------------

def checar_numeros(chk: Checador, data: dict | None, log: list | None):
    if data is None:
        return
    textos = [e.get("texto") for e in (log or []) if isinstance(e.get("texto"), str)]
    analise = data.get("analise") or {}
    campos: list[tuple[str, str]] = [(k, v) for k, v in analise.items()
                                     if k.endswith("_html") and isinstance(v, str)]
    sintese = (data.get("header") or {}).get("sintese")
    if isinstance(sintese, str):
        campos.append(("header.sintese", sintese))
    for lista in ("positives", "negatives"):
        campos += [(f"{lista}[{i}]", item)
                   for i, item in enumerate(analise.get(lista) or [])
                   if isinstance(item, str)]

    for campo, conteudo in campos:
        limpo = RE_NUM_LIVRE.sub(" ", conteudo)  # num-livre não é auditado
        limpo = RE_TAG.sub(" ", limpo)
        limpo = RE_REF_SECAO.sub(" ", limpo)     # §4.1 não é candidato numérico
        limpo = RE_VERSAO.sub(" ", limpo)        # V2.2.1 idem
        vistos: set[str] = set()
        for tok in RE_NUM_CANDIDATO.findall(limpo):
            if tok in vistos:
                continue
            vistos.add(tok)
            if RE_ANO.fullmatch(tok):
                continue  # anos inteiros não são candidatos
            chk.check("numeros", any(tok in t for t in textos),
                      f"número órfão {tok!r} em {campo} (sem correspondência em "
                      f"nenhum texto do log de consistência e sem <span "
                      f'class="num-livre">)')


# ----------------------------------------------------------------------------
# main
# ----------------------------------------------------------------------------

def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("ns", help="diretório da análise: analises/<TICKER>")
    ap.add_argument("--html", help="caminho do HTML a auditar "
                                   "(default: <ns>/relatorio/relatorio_<TICKER>.html)")
    a = ap.parse_args(argv)

    ns = Path(a.ns)
    chk = Checador()

    case_path = ns / "case.json"
    if not case_path.exists():
        print(f"[estrutura] case.json ausente: {case_path}")
        return 1
    results_path = ns / "saida" / "results.json"
    if not results_path.exists():
        print(f"[estrutura] saida/results.json ausente: {results_path} "
              "(o relatório foi emitido pelo build_report.py?)")
        return 1
    try:
        case = json.loads(case_path.read_text(encoding="utf-8"))
        results = json.loads(results_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"[estrutura] case.json/results.json não é JSON válido ({e})")
        return 1

    ticker = case.get("ticker") or ns.name
    html_path = Path(a.html) if a.html else ns / "relatorio" / f"relatorio_{ticker}.html"
    if not html_path.exists():
        print(f"[estrutura] relatório não encontrado: {html_path}")
        return 1
    html = html_path.read_text(encoding="utf-8")

    data = checar_estrutura(chk, html, case, results)     # 1. [estrutura]
    log = checar_log(chk, html, case, results, ns)        # 2. [log]
    checar_paridade(chk, html, data)                      # 3. [paridade]
    checar_autocontencao(chk, html)                       # 4. [autocontencao]
    checar_charts(chk, data, case, results, ns)           # 5. [charts]
    checar_numeros(chk, data, log)                        # 6. [numeros]

    if chk.violacoes:
        for v in chk.violacoes:
            print(v)
        print(f"FALHOU: {len(chk.violacoes)} violação(ões) em {chk.checagens} checagens "
              f"— {html_path}")
        return 1
    print(f"LIMPO: {chk.checagens} checagens — {html_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
