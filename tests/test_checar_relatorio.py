"""Testes do checar_relatorio.py: QC final por codigo sobre um HTML ja emitido.

Fixture no padrao do test_build_report: monta analises/TST3 em tmp_path e roda o
build_report.py via subprocess para gerar um HTML limpo; cada teste adultera o
HTML (ou o analise.json + rebuild) e espera a categoria de violacao certa.
"""

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
BUILD = RAIZ / "skills" / "er-relatorio-html" / "build_report.py"
CHECAR = RAIZ / "skills" / "er-relatorio-html" / "checar_relatorio.py"
sys.path.insert(0, str(RAIZ / "skills" / "er-motor-k3" / "scripts"))

import valuation_engine as ve  # noqa: E402

NI0 = 5.75


def make_case():
    base = dict(ve._FINGERPRINT_INPUTS)
    return {
        "company": "Teste S.A.", "ticker": "TST3", "currency": "BRL",
        "valuation_date": "2026-08-05",
        "market": {"price_per_share": 25.0, "shares_diluted_t0": 8.4,
                   "price_date": "2026-08-05", "price_source": "openbb/yfinance"},
        "scenarios": {
            "base": {"inputs": dict(base), "scale": {"NI0": NI0}},
            "bear": {"inputs": {**base, "ROE2": 0.30, "g2": 0.10, "n2": 8}, "scale": {"NI0": NI0}},
            "bull": {"inputs": {**base, "n2": 15, "F": 8}, "scale": {"NI0": NI0}},
        },
    }


def make_analise(res_base, roe2_base):
    # modo completo exige >= 5 graficos no checar; specs cobrem direta/derivada/overlays
    fv = res_base["value_per_share"]
    k3 = res_base["K3_trailing_PE"]
    charts = [
        {"id": "precos", "titulo": "Preco mensal", "tipo": "line", "unidade": "BRL",
         "x": [2024, 2025],
         "series": [{"label": "Fechamento", "y": [22.5, 24.1],
                     "fonte": "dados/precos.json", "derivacao": "direta"}],
         "overlays": [{"label": "Fair value base", "valor": fv,
                       "fonte_chave": "results:scenarios.base.value_per_share"}],
         "nota_janela": "Janela efetiva 2024-2025."},
        {"id": "roe", "titulo": "ROE historico", "tipo": "line", "unidade": "%",
         "x": [2023, 2024, 2025],
         "series": [{"label": "ROE", "y": [0.31, 0.35, 0.41],
                     "fonte": "dados/fundamentals.json", "derivacao": "derivada",
                     "formula_nota": "NI_t / Equity_(t-1) (DuPont)"}],
         "overlays": [{"label": "ROE2 assumido (base)", "valor": roe2_base,
                       "fonte_chave": "case:scenarios.base.inputs.ROE2"}],
         "nota_janela": "Janela efetiva 2023-2025 (OpenBB/yfinance)."},
        {"id": "eps", "titulo": "EPS com CAGR", "tipo": "bars", "unidade": "BRL",
         "x": [2023, 2024, 2025],
         "series": [{"label": "EPS", "y": [0.52, 0.61, 0.68],
                     "fonte": "dados/fundamentals.json", "derivacao": "direta"}],
         "nota_janela": "Janela efetiva 2023-2025."},
        {"id": "endividamento", "titulo": "Endividamento", "tipo": "line", "unidade": "x",
         "x": [2023, 2024, 2025],
         "series": [{"label": "Divida liquida / book", "y": [0.7, 0.65, 0.6],
                     "fonte": "dados/fundamentals.json", "derivacao": "derivada",
                     "formula_nota": "NetDebt_t / BookEquity_t"}],
         "nota_janela": "Janela efetiva 2023-2025."},
        {"id": "pl", "titulo": "P/L historico", "tipo": "line", "unidade": "x",
         "x": [2024, 2025],
         "series": [{"label": "P/L", "y": [43.3, 35.4],
                     "fonte": "dados/fundamentals.json", "derivacao": "derivada",
                     "formula_nota": "Preco_t / EPS_t"}],
         "overlays": [{"label": "K3 justo base", "valor": k3,
                       "fonte_chave": "results:scenarios.base.K3_trailing_PE"}],
         "nota_janela": "Janela efetiva 2024-2025."},
    ]
    return {
        "header": {"sintese": "Fair value base {{r:scenarios.base.value_per_share|2}}/acao "
                              "vs preco {{c:market.price_per_share|2}}."},
        "positives": ["Retornos marginais altos no regime F2"],
        "negatives": ["Serie de fundamentals curta (janela OpenBB)"],
        "sumario_html": "<p>Valor por acao base: {{r:scenarios.base.value_per_share|2}} "
                        "({{r:scenarios.base.vs_market.upside|pct1}} de upside). "
                        "Fundada em <span class=\"num-livre\">2005</span>.</p>",
        "financeira_html": "<p>Ultimo fechamento: {{d:precos.json:results.-1.close|2}}.</p>",
        "calibracao_racional_html": "<p><b>ROE2</b>: sustentado por vantagem de custo.</p>",
        "riscos_html": "<p>Risco regulatorio.</p>",
        "market_pricing_html": "<p>O preco embute K3 de {{r:scenarios.base.K3_trailing_PE|x}}.</p>",
        "limitacoes_html": "<p>Janela de demonstracoes limitada.</p>",
        "fontes_html": "<p><a href=\"https://exemplo.com/ri\">RI da companhia</a></p>",
        "charts": charts,
    }


@pytest.fixture
def ns(tmp_path):
    d = tmp_path / "analises" / "TST3"
    (d / "dados").mkdir(parents=True)
    case = make_case()
    (d / "case.json").write_text(json.dumps(case), encoding="utf-8")
    r = ve.value_case(case)
    analise = make_analise(r["scenarios"]["base"], case["scenarios"]["base"]["inputs"]["ROE2"])
    (d / "analise.json").write_text(json.dumps(analise, ensure_ascii=False), encoding="utf-8")
    (d / "dados" / "precos.json").write_text(json.dumps({
        "results": [{"date": "2024-12-31", "close": 22.5}, {"date": "2025-12-31", "close": 24.1}],
        "meta": {"endpoint": "equity_price_historical", "provider": "yfinance"},
    }), encoding="utf-8")
    (d / "dados" / "fundamentals.json").write_text(json.dumps({
        "results": [
            {"ano": 2023, "eps": 0.52, "roe": 0.31, "nde": 0.7},
            {"ano": 2024, "eps": 0.61, "roe": 0.35, "nde": 0.65},
            {"ano": 2025, "eps": 0.68, "roe": 0.41, "nde": 0.6},
        ],
        "meta": {"endpoint": "equity_fundamental_metrics", "provider": "yfinance"},
    }), encoding="utf-8")
    rb = subprocess.run([sys.executable, str(BUILD), str(d)],
                        capture_output=True, text=True, encoding="utf-8", timeout=300)
    assert rb.returncode == 0, rb.stdout + rb.stderr
    return d


def run_checar(ns, *args):
    return subprocess.run([sys.executable, str(CHECAR), str(ns), *args],
                          capture_output=True, text=True, encoding="utf-8", timeout=300)


def rebuild(ns):
    r = subprocess.run([sys.executable, str(BUILD), str(ns)],
                       capture_output=True, text=True, encoding="utf-8", timeout=300)
    assert r.returncode == 0, r.stdout + r.stderr


def html_path(ns):
    return ns / "relatorio" / "relatorio_TST3.html"


def test_html_limpo_exit0(ns):
    r = run_checar(ns)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "LIMPO" in r.stdout


def test_numero_adulterado_no_html(ns):
    # substitui a 1a ocorrencia do fair value base formatado por outro numero
    html = html_path(ns).read_text(encoding="utf-8")
    results = json.loads((ns / "saida" / "results.json").read_text(encoding="utf-8"))
    fv = f"{results['scenarios']['base']['value_per_share']:,.2f}"
    assert fv in html
    adulterado = ns / "relatorio" / "adulterado_b.html"
    adulterado.write_text(html.replace(fv, "99.99", 1), encoding="utf-8")
    r = run_checar(ns, "--html", str(adulterado))
    assert r.returncode == 1, r.stdout + r.stderr
    assert "[log]" in r.stdout or "[estrutura]" in r.stdout, r.stdout


def test_selftest_de_paridade_removido(ns):
    html = html_path(ns).read_text(encoding="utf-8")
    adulterado = ns / "relatorio" / "adulterado_c.html"
    adulterado.write_text(re.sub(r"k3SelfTest", "k3SelfTestX", html), encoding="utf-8")
    r = run_checar(ns, "--html", str(adulterado))
    assert r.returncode == 1, r.stdout + r.stderr
    assert "[paridade]" in r.stdout, r.stdout


def test_recurso_externo_injetado(ns):
    html = html_path(ns).read_text(encoding="utf-8")
    adulterado = ns / "relatorio" / "adulterado_d.html"
    adulterado.write_text(
        html.replace("</body>", '<img src="https://tracker.example/pix.png"></body>'),
        encoding="utf-8")
    r = run_checar(ns, "--html", str(adulterado))
    assert r.returncode == 1, r.stdout + r.stderr
    assert "[autocontencao]" in r.stdout, r.stdout


def test_numero_orfao_na_prosa(ns):
    analise = json.loads((ns / "analise.json").read_text(encoding="utf-8"))
    analise["sumario_html"] += "<p>Margem de 77.77% garantida.</p>"
    (ns / "analise.json").write_text(json.dumps(analise, ensure_ascii=False), encoding="utf-8")
    rebuild(ns)
    r = run_checar(ns)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "[numeros]" in r.stdout and "77.77" in r.stdout, r.stdout


def test_numero_livre_marcado_passa(ns):
    analise = json.loads((ns / "analise.json").read_text(encoding="utf-8"))
    analise["sumario_html"] += ('<p>Margem de <span class="num-livre">77.77%</span> '
                                "garantida.</p>")
    (ns / "analise.json").write_text(json.dumps(analise, ensure_ascii=False), encoding="utf-8")
    rebuild(ns)
    r = run_checar(ns)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "LIMPO" in r.stdout


def test_engine_embutido_adulterado(ns):
    if not shutil.which("node"):
        pytest.skip("node indisponivel (sub-check do engine embutido so roda com node)")
    html = html_path(ns).read_text(encoding="utf-8")
    assert "(gT - g2) * k / F" in html
    adulterado = ns / "relatorio" / "adulterado_g.html"
    adulterado.write_text(
        html.replace("(gT - g2) * k / F", "(gT - g2) * k / (F * 1.001)"), encoding="utf-8")
    r = run_checar(ns, "--html", str(adulterado))
    assert r.returncode == 1, r.stdout + r.stderr
    assert "[paridade]" in r.stdout, r.stdout
