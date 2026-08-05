"""Testes do build_report.py: emissao, autocontencao, placeholders, recusas e modo valuation.

A recusa por paridade divergente e testada copiando as DUAS skills para um tmp e
adulterando a COPIA do k3_engine.js (o arquivo do repo permanece intocado) — exige node.
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


def make_analise():
    return {
        "header": {"sintese": "Fair value base {{r:scenarios.base.value_per_share|2}}/acao vs preco {{c:market.price_per_share|2}}."},
        "positives": ["Retornos marginais altos no regime F2"],
        "negatives": ["Serie de fundamentals curta (janela OpenBB)"],
        "sumario_html": "<p>Valor por acao base: {{r:scenarios.base.value_per_share|2}} "
                        "({{r:scenarios.base.vs_market.upside|pct1}} de upside). "
                        "Fundada em <span class=\"num-livre\">2005</span>.</p>",
        "financeira_html": "<p>Ultimo fechamento: {{d:precos.json:results.1.close|2}}.</p>",
        "calibracao_racional_html": "<p><b>ROE2</b>: sustentado por vantagem de custo.</p>",
        "riscos_html": "<p>Risco regulatorio.</p>",
        "market_pricing_html": "<p>O preco embute K3 de {{r:scenarios.base.K3_trailing_PE|x}} "
                               "e ROE2 market-implied de {{m:ROE2.implied|pct1}}.</p>",
        "limitacoes_html": "<p>Janela de demonstracoes limitada.</p>",
        "fontes_html": "<p><a href=\"https://exemplo.com/ri\">RI da companhia</a></p>",
        "charts": [{
            "id": "precos", "titulo": "Preco mensal", "tipo": "line", "unidade": "BRL",
            "x": [2024, 2025],
            "series": [{"label": "Fechamento", "y": [22.5, 24.1],
                        "fonte": "dados/precos.json", "derivacao": "direta"}],
            "overlays": [{"label": "Fair value base", "valor": None,
                          "fonte_chave": "results:scenarios.base.value_per_share"}],
            "nota_janela": "Janela efetiva 2024-2025.",
        }],
    }


@pytest.fixture
def ns(tmp_path):
    d = tmp_path / "analises" / "TST3"
    (d / "dados").mkdir(parents=True)
    (d / "case.json").write_text(json.dumps(make_case()), encoding="utf-8")
    analise = make_analise()
    # overlay do fair value: valor preenchido pelo teste apos rodar o engine
    r = ve.value_case(make_case())
    analise["charts"][0]["overlays"][0]["valor"] = r["scenarios"]["base"]["value_per_share"]
    (d / "analise.json").write_text(json.dumps(analise, ensure_ascii=False), encoding="utf-8")
    (d / "dados" / "precos.json").write_text(json.dumps({
        "results": [{"date": "2024-12-31", "close": 22.5}, {"date": "2025-12-31", "close": 24.1}],
        "meta": {"endpoint": "equity_price_historical", "provider": "yfinance"},
    }), encoding="utf-8")
    return d


import os

ENV_UTF8 = {**os.environ, "PYTHONIOENCODING": "utf-8"}


def run_build(ns, *args):
    return subprocess.run([sys.executable, str(BUILD), str(ns), *args],
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace", env=ENV_UTF8, timeout=300)


def test_html_emitido_autocontido_numeros_batem(ns):
    r = run_build(ns)
    assert r.returncode == 0, r.stdout + r.stderr
    html_path = ns / "relatorio" / "relatorio_TST3.html"
    assert html_path.exists()
    assert (ns / "saida" / "results.json").exists()
    html = html_path.read_text(encoding="utf-8")

    # autocontencao: nenhum CARREGAMENTO externo; <a href> de citacao permitido
    sem_anchors = re.sub(r"<a\s[^>]*href\s*=\s*[\"']https?://[^>]*>", "", html, flags=re.I)
    assert not re.search(r"(?:src|srcset)\s*=\s*[\"']https?://", sem_anchors, re.I)
    assert not re.search(r"<link[^>]+href\s*=\s*[\"']https?://", sem_anchors, re.I)
    assert not re.search(r"@import\s+(?:url\()?[\"']?https?://", sem_anchors, re.I)
    assert "XMLHttpRequest" not in sem_anchors
    assert "https://exemplo.com/ri" in html  # citacao preservada

    # numeros citados existem e batem com results.json
    results = json.loads((ns / "saida" / "results.json").read_text(encoding="utf-8"))
    vps = results["scenarios"]["base"]["value_per_share"]
    k3 = results["scenarios"]["base"]["K3_trailing_PE"]
    assert f"{vps:,.2f}" in html
    assert f"{k3:.2f}x" in html
    assert ("{{r:" not in html and "{{c:" not in html and "{{d:" not in html
            and "{{m:" not in html)
    assert "24.10" in html  # placeholder de dados/ (results.1.close = 24.1) resolvido

    # log de consistencia embutido com fonte/chave/valor
    m = re.search(r'<script type="application/json" id="log-consistencia">(.*?)</script>', html, re.S)
    assert m, "bloco log-consistencia ausente"
    log = json.loads(m.group(1))
    assert any(e["chave"] == "scenarios.base.value_per_share" and e["fonte"] == "results.json" for e in log)
    assert any(e["fonte"] == "dados/precos.json" for e in log)

    # payloads estruturais
    data = json.loads(re.search(r"var REPORT_DATA = (\{.*?\});\n</script>", html, re.S).group(1))
    assert data["modo"] == "completo"
    assert data["scenarios"]["base"]["python_expected"]["K3"] == pytest.approx(k3)
    assert data["analise"]["charts"][0]["series"][0]["y"] == [22.5, 24.1]
    assert data["header"]["fair_value_base_ps"] == pytest.approx(vps)


def test_formato_bi_e_mi(ns):
    """Cifras de balanço em bilhões/milhões: auditáveis por placeholder, não num-livre."""
    analise = json.loads((ns / "analise.json").read_text(encoding="utf-8"))
    analise["financeira_html"] = ("<p>Escala: {{d:grandes.json:ativo|bi}} bi e "
                                 "{{d:grandes.json:ativo|mi}} mi.</p>")
    (ns / "analise.json").write_text(json.dumps(analise, ensure_ascii=False), encoding="utf-8")
    (ns / "dados" / "grandes.json").write_text(json.dumps({"ativo": 10530000000}),
                                               encoding="utf-8")
    r = run_build(ns)
    assert r.returncode == 0, r.stdout + r.stderr
    html = (ns / "relatorio" / "relatorio_TST3.html").read_text(encoding="utf-8")
    assert "10.53 bi" in html
    assert "10,530.0 mi" in html
    log = json.loads(re.search(
        r'<script type="application/json" id="log-consistencia">(.*?)</script>', html, re.S).group(1))
    entradas = [e for e in log if e["fonte"] == "dados/grandes.json"]
    assert len(entradas) == 2
    assert all(e["valor"] == 10530000000 for e in entradas)


def test_placeholder_orfao_recusa(ns):
    analise = json.loads((ns / "analise.json").read_text(encoding="utf-8"))
    analise["sumario_html"] = "<p>{{r:scenarios.base.chave_inexistente|2}}</p>"
    (ns / "analise.json").write_text(json.dumps(analise, ensure_ascii=False), encoding="utf-8")
    r = run_build(ns)
    assert r.returncode == 1
    assert "placeholder" in (r.stdout + r.stderr).lower()
    assert not (ns / "relatorio" / "relatorio_TST3.html").exists()


CAMPOS_IMPLIED = {"param", "base_value", "implied", "implied_display", "label",
                  "interpretation", "nearest_value", "nearest_metric"}


def test_market_implied_json_persistido(ns):
    r = run_build(ns)
    assert r.returncode == 0, r.stdout + r.stderr
    mi_path = ns / "saida" / "market_implied.json"
    assert mi_path.exists(), "saida/market_implied.json nao foi persistido"
    mi = json.loads(mi_path.read_text(encoding="utf-8"))
    assert set(mi) == {"meta", "params"}

    results = json.loads((ns / "saida" / "results.json").read_text(encoding="utf-8"))
    assert mi["meta"]["gerado_por"] == "build_report.py"
    assert mi["meta"]["engine_version"] == results["engine_version"]
    assert mi["meta"]["scenario"] == "base"
    assert mi["meta"]["price_per_share"] == 25.0
    assert isinstance(mi["meta"]["nota"], str) and mi["meta"]["nota"]

    roe2 = mi["params"]["ROE2"]
    assert set(roe2) == CAMPOS_IMPLIED
    esperado = ve.solve_market_implied(make_case(), "base", "ROE2")["solution"]
    assert roe2["implied"] == pytest.approx(esperado, rel=0, abs=1e-12)
    assert roe2["param"] == "ROE2"
    assert roe2["nearest_value"] is None and roe2["nearest_metric"] is None

    # n2 e inteiro: sem solucao exata -> nearest_* preenchidos a partir de sol["nearest"]
    sol_n2 = ve.solve_market_implied(make_case(), "base", "n2")
    n2 = mi["params"]["n2"]
    assert set(n2) == CAMPOS_IMPLIED
    assert n2["nearest_value"] == sol_n2["nearest"]["value"]
    assert n2["nearest_metric"] == pytest.approx(sol_n2["nearest"]["metric"], rel=0, abs=1e-12)

    # a tabela do HTML sai do MESMO objeto (mesma ordem, mesmos valores)
    html = (ns / "relatorio" / "relatorio_TST3.html").read_text(encoding="utf-8")
    data = json.loads(re.search(r"var REPORT_DATA = (\{.*?\});\n</script>", html, re.S).group(1))
    assert [row["param"] for row in data["market_implied"]] == list(mi["params"])
    for row in data["market_implied"]:
        assert row["implied"] == pytest.approx(mi["params"][row["param"]]["implied"], rel=0, abs=1e-12)


def test_placeholder_m_resolve_e_loga(ns):
    r = run_build(ns)
    assert r.returncode == 0, r.stdout + r.stderr
    html = (ns / "relatorio" / "relatorio_TST3.html").read_text(encoding="utf-8")
    mi = json.loads((ns / "saida" / "market_implied.json").read_text(encoding="utf-8"))
    esperado = f"{100 * mi['params']['ROE2']['implied']:.1f}%"
    assert esperado in html
    assert "{{m:" not in html

    m = re.search(r'<script type="application/json" id="log-consistencia">(.*?)</script>',
                  html, re.S)
    log = json.loads(m.group(1))
    entradas = [e for e in log if e["fonte"] == "saida/market_implied.json"]
    assert entradas, log
    e = entradas[0]
    assert e["chave"] == "ROE2.implied"
    assert e["texto"] == esperado
    assert e["valor"] == pytest.approx(mi["params"]["ROE2"]["implied"], rel=0, abs=1e-12)


@pytest.mark.parametrize("ph", ["{{m:ROE2.inexistente|2}}", "{{m:XX.implied|2}}"])
def test_placeholder_m_invalido_recusa(ns, ph):
    analise = json.loads((ns / "analise.json").read_text(encoding="utf-8"))
    analise["sumario_html"] = f"<p>{ph}</p>"
    (ns / "analise.json").write_text(json.dumps(analise, ensure_ascii=False), encoding="utf-8")
    r = run_build(ns)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "placeholder" in (r.stdout + r.stderr).lower()
    assert not (ns / "relatorio" / "relatorio_TST3.html").exists()


def test_modo_valuation_reduzido(ns):
    r = run_build(ns, "--modo", "valuation")
    assert r.returncode == 0, r.stdout + r.stderr
    html = (ns / "relatorio" / "relatorio_TST3.html").read_text(encoding="utf-8")
    data = json.loads(re.search(r"var REPORT_DATA = (\{.*?\});\n</script>", html, re.S).group(1))
    assert data["modo"] == "valuation"
    assert "sumario_html" not in data["analise"]
    assert "calibracao_racional_html" in data["analise"]


def test_recusa_paridade_divergente(ns, tmp_path):
    if not shutil.which("node"):
        pytest.skip("node indisponivel (recusa por paridade so e verificavel com node)")
    skills_tmp = tmp_path / "skills"
    shutil.copytree(RAIZ / "skills" / "er-motor-k3", skills_tmp / "er-motor-k3")
    shutil.copytree(RAIZ / "skills" / "er-relatorio-html", skills_tmp / "er-relatorio-html")
    js = skills_tmp / "er-relatorio-html" / "assets" / "k3_engine.js"
    texto = js.read_text(encoding="utf-8")
    assert "(gT - g2) * k / F" in texto
    js.write_text(texto.replace("(gT - g2) * k / F", "(gT - g2) * k / (F * 1.001)"),
                  encoding="utf-8")
    r = subprocess.run([sys.executable, str(skills_tmp / "er-relatorio-html" / "build_report.py"),
                        str(ns)], capture_output=True, text=True, encoding="utf-8",
                       errors="replace", env=ENV_UTF8, timeout=300)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "diverg" in (r.stdout + r.stderr).lower()
    assert not (ns / "relatorio" / "relatorio_TST3.html").exists()
