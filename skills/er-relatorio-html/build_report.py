#!/usr/bin/env python3
"""build_report.py — builder determinístico do relatório HTML de 2 abas (fleet v3).

Único caminho de emissão do relatório. Monta um arquivo autocontido a partir de:

  <ns>/case.json      — input do engine (schema da skill er-motor-k3)
  <ns>/analise.json   — conteúdo da aba 2 escrito pelo Analista (fragmentos HTML,
                        positives/negatives, specs de gráficos, interpretações)
  <ns>/dados/*.json   — arquivos do Data Manager (fonte das séries dos gráficos)

e grava:

  <ns>/saida/results.json                — saída integral do engine (fonte de verdade)
  <ns>/saida/market_implied.json         — diagnóstico reverso rotulado (auditável)
  <ns>/relatorio/relatorio_<TICKER>.html — o relatório

Recusas (exit 1, nada é emitido):
  * suíte canônica de regressão falhou (a menos de --skip-regressions, não
    recomendado para entrega);
  * engine_fingerprint_ok == False;
  * espelho JS divergiu do Python na pré-verificação sob node (quando node existe);
  * placeholder de número não resolvível em analise.json;
  * carregamento externo de recurso no HTML final (autocontenção).

Contrato de números citados em prosa (aba 2): todo número de valuation citado nos
fragmentos HTML DEVE usar placeholder, resolvido daqui e registrado no log de
consistência embutido (script#log-consistencia), que o checar_relatorio.py audita:

  {{r:scenarios.base.value_per_share|2}}     -> results.json, 2 casas
  {{r:scenarios.base.vs_market.upside|pct1}} -> results.json, percentual 1 casa
  {{c:market.price_per_share|2}}             -> case.json
  {{d:precos.json:results.-1.close|2}}       -> dados/<arquivo>, chave pontilhada
                                                (índices inteiros p/ listas; -1 = último)
  {{m:ROE2.implied|pct1}}                    -> saida/market_implied.json,
  {{m:n2.nearest_value|2}}                      params.<PARAM>.<campo>
  {{m:n2.nearest_metric|2}}

O namespace `m:` torna o market-implied AUDITÁVEL: o diagnóstico reverso é
calculado uma única vez, persistido em saida/market_implied.json (mesma fonte da
tabela do HTML) e re-resolvido pelo checar_relatorio.py. Valor market-implied
citado em prosa DEVE usar `m:` — num-livre não é aceitável para ele.

Números livres legítimos (anos, fatos qualitativos) podem ser marcados com
<span class="num-livre">…</span> — o checar não os audita.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent
ASSETS = SKILL_DIR / "assets"
MOTOR_SCRIPTS = SKILL_DIR.parent / "er-motor-k3" / "scripts"
sys.path.insert(0, str(MOTOR_SCRIPTS))

import valuation_engine as ve  # noqa: E402

PCT_PARAMS = {"ROE1", "ROE2", "g1", "g2", "Ke1", "Ke2", "g_T", "Kd_F2", "t"}

RE_PLACEHOLDER = re.compile(r"\{\{([rcdm]):([^}|]+?)(?:\|([a-z0-9]+))?\}\}")

FONTE_IMPLIED = "saida/market_implied.json"
NOTA_IMPLIED = "diagnóstico reverso rotulado — nunca recalibra o fair value"
RE_RECURSO_EXTERNO = (
    re.compile(r"(?:src|srcset)\s*=\s*[\"']https?://", re.I),
    re.compile(r"<link[^>]+href\s*=\s*[\"']https?://", re.I),
    re.compile(r"@import\s+(?:url\()?[\"']?https?://", re.I),
    re.compile(r"\bXMLHttpRequest\b"),
    re.compile(r"\bfetch\s*\("),
    re.compile(r"\bimport\s*\(\s*[\"']https?://"),
)


def fail(msg: str) -> int:
    print(f"FATAL: {msg}")
    return 1


# ----------------------------------------------------------------------------
# navegação por chave pontilhada (case/results/dados)
# ----------------------------------------------------------------------------

def get_path(obj, dotted: str):
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
    if valor is None or not isinstance(valor, (int, float)):
        raise ValueError("valor ausente ou não numérico")
    spec = spec or "2"
    if spec.startswith("pct"):
        nd = int(spec[3:] or "1")
        return f"{100.0 * valor:.{nd}f}%"
    if spec == "x":
        return f"{valor:.2f}x"
    nd = int(spec)
    return f"{valor:,.{nd}f}"


class Resolvedor:
    """Resolve placeholders {{r:...}}/{{c:...}}/{{d:...}}/{{m:...}} e acumula o log."""

    def __init__(self, results: dict, case: dict, dados_dir: Path, implied: dict | None = None):
        self.results = results
        self.case = case
        self.dados_dir = dados_dir
        self.implied = implied or {"meta": {}, "params": {}}
        self._dados_cache: dict[str, object] = {}
        self.log: list[dict] = []
        self.erros: list[str] = []

    def _fonte(self, tipo: str, chave: str):
        if tipo == "r":
            return get_path(self.results, chave), "results.json", chave
        if tipo == "c":
            return get_path(self.case, chave), "case.json", chave
        if tipo == "m":
            return get_path(self.implied, f"params.{chave}"), FONTE_IMPLIED, chave
        arquivo, _, resto = chave.partition(":")
        if arquivo not in self._dados_cache:
            p = self.dados_dir / arquivo
            self._dados_cache[arquivo] = json.loads(p.read_text(encoding="utf-8")) if p.exists() else None
        base = self._dados_cache[arquivo]
        if base is None:
            return None, f"dados/{arquivo}", resto
        return get_path(base, resto), f"dados/{arquivo}", resto

    def resolver_html(self, html: str, onde: str) -> str:
        def sub(m: re.Match) -> str:
            tipo, chave, spec = m.group(1), m.group(2), m.group(3)
            try:
                valor, fonte, chave_reg = self._fonte(tipo, chave)
                texto = fmt_placeholder(valor, spec)
            except Exception as e:
                self.erros.append(f"{onde}: placeholder {{{{{tipo}:{chave}}}}} não resolvido ({e})")
                return m.group(0)
            self.log.append({"onde": onde, "fonte": fonte, "chave": chave_reg,
                             "valor": valor, "texto": texto, "spec": spec or "2"})
            return texto

        return RE_PLACEHOLDER.sub(sub, html)


# ----------------------------------------------------------------------------
# blocos do payload (mesma lógica do builder da skill standalone, adaptada)
# ----------------------------------------------------------------------------

def fmt_param(param, v):
    if v is None:
        return "sem solução válida no domínio"
    if param in PCT_PARAMS:
        return f"{100 * v:.1f}%"
    if param in ("n1", "n2", "F"):
        return f"{v:g} anos"
    return f"{v:.2f}x"


def build_implied(case, params, notes, engine_version=None):
    """Diagnóstico reverso do cenário base, calculado UMA vez e persistível.

    Devolve {"meta": {...}, "params": {<PARAM>: {...}}} — a mesma estrutura gravada
    em saida/market_implied.json, resolvida pelo namespace `m:` e re-auditada pelo
    checar_relatorio.py. A tabela do HTML sai deste mesmo objeto (implied_rows).
    """
    price = (case.get("market") or {}).get("price_per_share")
    obj = {"meta": {"gerado_por": "build_report.py", "engine_version": engine_version,
                    "scenario": "base", "price_per_share": price, "nota": NOTA_IMPLIED},
           "params": {}}
    if not price:
        return obj
    for p in params:
        sol = ve.solve_market_implied(case, "base", p)
        if "error" in sol:
            continue
        implied = sol.get("solution")
        display = fmt_param(p, implied)
        nearest_value = nearest_metric = None
        if implied is None and sol.get("nearest"):
            nearest_value = sol["nearest"]["value"]
            nearest_metric = sol["nearest"]["metric"]
            display = (f"~{fmt_param(p, nearest_value)} mais próximo "
                       f"(atinge {nearest_metric:.2f}/ação)")
            implied = nearest_value
        base_v = sol["base_value"]
        interp = notes.get(p)
        if not interp and implied is not None and isinstance(base_v, (int, float)):
            direcao = "acima" if implied > base_v else "abaixo"
            interp = (f"O preço é consistente com {fmt_param(p, implied)} vs base do Analista "
                      f"{fmt_param(p, base_v)} ({direcao}).")
        elif not interp:
            interp = sol.get("reason") or ""
        obj["params"][p] = {"param": p, "base_value": base_v, "implied": implied,
                            "implied_display": display, "label": sol.get("label"),
                            "interpretation": interp, "nearest_value": nearest_value,
                            "nearest_metric": nearest_metric}
    return obj


def implied_rows(implied: dict) -> list:
    """Linhas da tabela do HTML — projeção do MESMO objeto persistido (sem recálculo)."""
    return [{**v, "base_display": fmt_param(v["param"], v["base_value"])}
            for v in (implied.get("params") or {}).values()]


def build_presets(case, presets):
    out = []
    for p in presets:
        grid = ve.sensitivity_2d(case, p.get("scenario", "base"), p["param_rows"], p["values_rows"],
                                 p["param_cols"], p["values_cols"])
        metric = p.get("metric", "value_per_share")
        cells = [[(c or {}).get(metric) for c in row] for row in grid["grid"]]
        base_in = case["scenarios"][p.get("scenario", "base")]["inputs"]

        def idx_of(vals, target):
            for i, v in enumerate(vals):
                if isinstance(target, (int, float)) and abs(v - target) < 1e-12:
                    return i
            return None

        ri = idx_of(p["values_rows"], base_in.get(p["param_rows"]))
        ci = idx_of(p["values_cols"], base_in.get(p["param_cols"]))
        out.append({
            "title": p.get("title", f"{p['param_rows']} x {p['param_cols']}"),
            "param_rows": p["param_rows"], "values_rows": p["values_rows"],
            "param_cols": p["param_cols"], "values_cols": p["values_cols"],
            "rows_pct": p["param_rows"] in PCT_PARAMS, "cols_pct": p["param_cols"] in PCT_PARAMS,
            "metric_label": metric.replace("_", " "), "grid": cells,
            "base_cell": [ri, ci] if ri is not None and ci is not None else None,
            "decimals": p.get("decimals", 2),
        })
    return out


def default_presets(case):
    b = case["scenarios"].get("base")
    if not b:
        return []
    i = b["inputs"]
    roe2, n2 = i["ROE2"], int(i["n2"])
    rows = sorted({round(roe2 * f, 4) for f in (0.7, 0.85, 1.0, 1.15, 1.3)})
    cols = sorted({max(0, n2 + d) for d in (-4, -2, 0, 2, 4)})
    return [{"title": "ROE2 x n2 — valor por ação", "param_rows": "ROE2", "values_rows": rows,
             "param_cols": "n2", "values_cols": cols, "metric": "value_per_share"}]


def build_header(case, results, analise):
    scens = results["scenarios"]
    default = "base" if "base" in scens else next(iter(scens))
    fv = {n: r for n, r in scens.items()
          if r.get("computed") and (case["scenarios"][n].get("label_mode", "fair_value") != "hurdle")}
    base = scens.get(default) or {}
    header = {
        "fair_value_base_ps": base.get("value_per_share"),
        "upside_base": (base.get("vs_market") or {}).get("upside"),
        "k3_base": base.get("K3_trailing_PE"),
        "sintese": (analise.get("header") or {}).get("sintese"),
    }
    vps = [r.get("value_per_share") for r in fv.values() if r.get("value_per_share") is not None]
    if len(vps) >= 2:
        header["faixa_bear_bull"] = f"{min(vps):,.2f} – {max(vps):,.2f}"
    hurdles = [r.get("value_per_share") for n, r in scens.items()
               if case["scenarios"][n].get("label_mode") == "hurdle" and r.get("value_per_share") is not None]
    if hurdles:
        header["hurdle_ps"] = hurdles[0]
    return header


# ----------------------------------------------------------------------------
# main
# ----------------------------------------------------------------------------

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("ns", help="diretório da análise: analises/<TICKER>")
    ap.add_argument("--out", help="caminho do HTML (default: <ns>/relatorio/relatorio_<TICKER>.html)")
    ap.add_argument("--modo", choices=["completo", "valuation"], default="completo")
    ap.add_argument("--skip-regressions", action="store_true",
                    help="pula a suíte canônica (NÃO recomendado para entrega)")
    a = ap.parse_args(argv)

    ns = Path(a.ns)
    case_path = ns / "case.json"
    if not case_path.exists():
        return fail(f"{case_path} não existe")
    case = json.loads(case_path.read_text(encoding="utf-8"))
    analise_path = ns / "analise.json"
    analise = json.loads(analise_path.read_text(encoding="utf-8")) if analise_path.exists() else {}
    if a.modo == "completo" and not analise:
        return fail("modo completo exige analise.json (conteúdo da aba 2)")

    ticker = case.get("ticker") or analise.get("ticker") or ns.name
    out = Path(a.out) if a.out else ns / "relatorio" / f"relatorio_{ticker}.html"

    # 1. regression gate
    reg = None
    if not a.skip_regressions:
        sys.path.insert(0, str(MOTOR_SCRIPTS))
        from run_regressions import run as reg_run
        reg = reg_run().summary()
        if reg["failed"]:
            return fail("suíte canônica de regressão FALHOU — recuso emitir o relatório.")

    # 2. engine
    results = ve.value_case(case)
    if not results["engine_fingerprint_ok"]:
        return fail("engine fingerprint falhou — recuso emitir o relatório.")
    saida = ns / "saida"
    saida.mkdir(parents=True, exist_ok=True)
    (saida / "results.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

    # 3. market-implied: calculado UMA vez, persistido e auditável (namespace m:)
    implied_params = analise.get("market_implied_params", ["ROE2", "g2", "Ke2", "n2"])
    implied = build_implied(case, implied_params,
                            analise.get("implied_interpretations", {}),
                            results.get("engine_version"))
    (saida / "market_implied.json").write_text(
        json.dumps(implied, indent=2, ensure_ascii=False), encoding="utf-8")

    # 4. resolver placeholders da aba 2
    res = Resolvedor(results, case, ns / "dados", implied)
    campos_html = ["sumario_html", "perfil_html", "qualitativa_html", "financeira_html",
                   "calibracao_racional_html", "riscos_html", "market_pricing_html",
                   "limitacoes_html", "fontes_html"]
    analise_resolvida = dict(analise)
    for campo in campos_html:
        if analise.get(campo):
            analise_resolvida[campo] = res.resolver_html(analise[campo], campo)
    for lista in ("positives", "negatives"):
        if analise.get(lista):
            analise_resolvida[lista] = [res.resolver_html(x, lista) for x in analise[lista]]
    header_cfg = analise.get("header") or {}
    if header_cfg.get("sintese"):
        header_cfg = dict(header_cfg)
        header_cfg["sintese"] = res.resolver_html(header_cfg["sintese"], "header.sintese")
        analise_resolvida["header"] = header_cfg
    if res.erros:
        for e in res.erros:
            print("ERRO:", e)
        return fail("placeholders não resolvidos na aba 2 — recuso emitir o relatório.")

    # 5. payload por cenário com python_expected (self-test do browser)
    scen_payload = {}
    for name, sc in case["scenarios"].items():
        r = results["scenarios"][name]
        scen_payload[name] = {
            "inputs": sc["inputs"],
            "NI0": (sc.get("scale") or {}).get("NI0"),
            "Book0": (sc.get("scale") or {}).get("Book0"),
            "weight": sc.get("weight"),
            "label_mode": sc.get("label_mode", "fair_value"),
            "shares_diluted_t0": sc.get("shares_diluted_t0"),
            "python_expected": {
                "K3": r.get("K3_trailing_PE"), "K_PB": r.get("K_PB"),
                "equity_value": r.get("equity_value"),
                "blocks": r.get("blocks"), "pb_blocks": r.get("pb_blocks"),
                "funding": {k: r.get(k) for k in (
                    "equity_reinvestment_ratio_F1", "fcfe_distribution_ratio_F1",
                    "equity_reinvestment_ratio_F2", "fcfe_distribution_ratio_F2")},
            } if r.get("computed") else None,
        }

    market = case.get("market", {}) or {}
    data = {
        "modo": a.modo,
        "company": case.get("company", "Company"),
        "ticker": ticker,
        "currency": case.get("currency"),
        "valuation_date": case.get("valuation_date"),
        "price_per_share": market.get("price_per_share"),
        "price_date": market.get("price_date"),
        "price_source": market.get("price_source"),
        "shares_diluted_t0": market.get("shares_diluted_t0"),
        "default_scenario": analise.get("default_scenario", "base"),
        "scenarios": scen_payload,
        "market_implied": implied_rows(implied),
        "sensitivity_presets": build_presets(case, analise.get("sensitivity_presets")
                                             or default_presets(case)),
        "sensitivity_default": analise.get("sensitivity_default", "ROE2"),
        "header": {**build_header(case, results, analise_resolvida),
                   **({"sintese": analise_resolvida.get("header", {}).get("sintese")}
                      if analise_resolvida.get("header", {}).get("sintese") else {})},
        "analise": {} if a.modo == "valuation" else {
            k: analise_resolvida.get(k) for k in
            ["positives", "negatives", "sumario_html", "perfil_html", "qualitativa_html",
             "financeira_html", "calibracao_racional_html", "riscos_html",
             "market_pricing_html", "limitacoes_html", "fontes_html", "charts"]
            if analise_resolvida.get(k)
        },
        "parity_vectors": ve.js_parity_vectors(),
        "regression_summary": reg,
    }
    if a.modo == "valuation":
        # HTML reduzido: aba 1 + calibração/racional (Seção 6 do desenho)
        data["analise"] = {k: analise_resolvida.get(k) for k in
                           ["calibracao_racional_html", "limitacoes_html", "fontes_html"]
                           if analise_resolvida.get(k)}

    # 6. montagem
    template = (ASSETS / "template_relatorio.html").read_text(encoding="utf-8")
    html = (template
            .replace("__PAGE_TITLE__", f"{data['company']} — Equity Research (K3 V2.2.1)")
            .replace("__UPLOT_CSS__", (ASSETS / "uPlot.min.css").read_text(encoding="utf-8"))
            .replace("__UPLOT_JS__", (ASSETS / "uPlot.iife.min.js").read_text(encoding="utf-8"))
            .replace("__CHARTS_JS__", (ASSETS / "charts.js").read_text(encoding="utf-8"))
            .replace("__K3_ENGINE_JS__", (ASSETS / "k3_engine.js").read_text(encoding="utf-8"))
            .replace("__LOG_CONSISTENCIA__", json.dumps(res.log, ensure_ascii=False))
            .replace("__REPORT_DATA__", json.dumps(data, ensure_ascii=False)))

    # 7. autocontenção (belt and braces — o checar repete)
    corpo_sem_anchors = re.sub(r"<a\s[^>]*href\s*=\s*[\"']https?://[^>]*>", "", html, flags=re.I)
    for rx in RE_RECURSO_EXTERNO:
        m = rx.search(corpo_sem_anchors)
        if m:
            return fail(f"carregamento externo de recurso no HTML ({m.group(0)!r}) — recuso emitir.")

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(f"relatorio escrito: {out} ({len(html) / 1024:.0f} KiB); results: {saida / 'results.json'}")

    # 8. pré-verificação de paridade sob node (recusa em divergência)
    node = shutil.which("node")
    if node:
        vectors = [{"name": n, "inputs": s["inputs"], "NI0": s["NI0"], "Book0": s["Book0"],
                    "expected": s["python_expected"]}
                   for n, s in scen_payload.items() if s["python_expected"]]
        vectors += data["parity_vectors"]
        proc = subprocess.run([node, str(ASSETS / "k3_engine.js"), "--selftest"],
                              input=json.dumps(vectors), capture_output=True, text=True,
                              encoding="utf-8", timeout=60)
        try:
            r = json.loads(proc.stdout)
        except json.JSONDecodeError:
            out.unlink(missing_ok=True)
            return fail(f"pré-verificação node não rodou: {proc.stderr[:200]}")
        if r["pass"]:
            print(f"paridade pré-verificada sob node: {r['checks']} checks, "
                  f"max |diff| {r['max_abs_diff']:.2e} -> banner verde no load")
        else:
            out.unlink(missing_ok=True)
            return fail(f"espelho JS divergiu do Python: {r['failures'][:3]} — relatório NÃO emitido.")
    else:
        print("nota: node indisponível — a página ainda se autoverifica no browser no load.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
