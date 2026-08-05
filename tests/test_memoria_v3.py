"""Testes do scripts/memoria.py: nota durável por ticker a partir de case.json + saida/results.json.

Fixture determinística: case fingerprint (base/bear/bull ponderados 0.6/0.2/0.2 + hurdle_12
sem peso, label_mode "hurdle") rodado por ve.value_case; as âncoras da nota são comparadas
com os valores reais do results.json (nunca digitadas).
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
SCRIPT = RAIZ / "scripts" / "memoria.py"
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
            "base": {"inputs": dict(base), "scale": {"NI0": NI0}, "weight": 0.6},
            "bear": {"inputs": {**base, "ROE2": 0.30, "g2": 0.10, "n2": 8},
                     "scale": {"NI0": NI0}, "weight": 0.2},
            "bull": {"inputs": {**base, "n2": 15, "F": 8}, "scale": {"NI0": NI0}, "weight": 0.2},
            "hurdle_12": {"inputs": {**base, "Ke1": 0.20, "Ke2": 0.20}, "scale": {"NI0": NI0},
                          "label_mode": "hurdle"},
        },
    }


@pytest.fixture
def ns(tmp_path):
    d = tmp_path / "analises" / "TST3"
    (d / "saida").mkdir(parents=True)
    case = make_case()
    (d / "case.json").write_text(json.dumps(case), encoding="utf-8")
    results = ve.value_case(case)
    (d / "saida" / "results.json").write_text(json.dumps(results), encoding="utf-8")
    return d


def run_memoria(ns, *args):
    return subprocess.run([sys.executable, str(SCRIPT), str(ns), *args],
                          capture_output=True, text=True, encoding="utf-8", timeout=120)


def _results(ns):
    return json.loads((ns / "saida" / "results.json").read_text(encoding="utf-8"))


def nota_path(ns):
    return ns.parent / "_memoria" / "TST3.md"


def _nota(ns):
    return nota_path(ns).read_text(encoding="utf-8")


# (a) nota no default analises/_memoria/TST3.md, 4 seções, âncora do base == results.json
def test_nota_default_quatro_secoes_e_ancora_base(ns):
    r = run_memoria(ns)
    assert r.returncode == 0, r.stdout + r.stderr
    assert nota_path(ns).exists()
    nota = _nota(ns)

    assert nota.startswith("# TST3 — nota de memória")
    for heading in ["## Âncoras numéricas", "## Síntese e decisão", "## Lições reutilizáveis"]:
        assert heading in nota, heading

    # cabeçalho: campos do case + versão do engine do results
    res = _results(ns)
    assert "Empresa: Teste S.A." in nota
    assert "Data da análise: 2026-08-05" in nota
    assert res["engine_version"] in nota
    assert f"impl {res['implementation_version']}" in nota

    # âncora: value_per_share do base formatado exatamente como no results.json
    vps = res["scenarios"]["base"]["value_per_share"]
    assert f"{vps:.2f}" in nota
    # peso do base vem do case.json
    linha_base = next(l for l in nota.splitlines() if l.startswith("| base |"))
    assert "0.60" in linha_base

    # placeholders iniciais (sem --sintese/--licoes)
    assert "(síntese ainda não registrada)" in nota
    assert "(nenhuma lição registrada ainda)" in nota

    assert "MEMORIA TST3:" in r.stdout


# (b) --saida alternativo respeitado
def test_saida_alternativa(ns, tmp_path):
    out = tmp_path / "memoria_alt"
    r = run_memoria(ns, "--saida", str(out))
    assert r.returncode == 0, r.stdout + r.stderr
    assert (out / "TST3.md").exists()
    assert not nota_path(ns).exists()


# (c) hurdle presente, rotulado, e NUNCA "fair value" na mesma linha
def test_hurdle_rotulado_nunca_fair_value(ns):
    r = run_memoria(ns)
    assert r.returncode == 0, r.stdout + r.stderr
    nota = _nota(ns)

    linhas = [l for l in nota.splitlines() if "Hurdle-conditioned" in l]
    assert linhas, "nenhuma linha de hurdle na nota"
    assert any(l.startswith("|") and "hurdle_12" in l for l in linhas), "linha do hurdle ausente da tabela"
    assert any("Hurdle-conditioned/ação" in l for l in linhas), "bullet hurdle-conditioned ausente"
    for l in linhas:
        assert "fair value" not in l.lower(), l


# (d) faixa fair value exclui o cenário hurdle
def test_faixa_fair_value_exclui_hurdle(ns):
    res = _results(ns)
    fv = [res["scenarios"][n]["value_per_share"] for n in ("base", "bear", "bull")]
    hurdle_vps = res["scenarios"]["hurdle_12"]["value_per_share"]
    r = run_memoria(ns)
    assert r.returncode == 0, r.stdout + r.stderr
    nota = _nota(ns)

    linha = next(l for l in nota.splitlines() if "Faixa fair value" in l)
    assert f"{min(fv):.2f} – {max(fv):.2f}" in linha
    assert f"{hurdle_vps:.2f}" not in linha


# (e) regeneração idempotente sem --licoes
def test_regeneracao_idempotente_sem_licoes(ns):
    assert run_memoria(ns).returncode == 0
    primeira = _nota(ns)
    r = run_memoria(ns)
    assert r.returncode == 0, r.stdout + r.stderr
    assert _nota(ns) == primeira


# (e) lições cumulativas: L1 → sem licoes → L2; L1 E L2 presentes, L2 depois de L1
def test_licoes_cumulativas(ns, tmp_path):
    l1 = tmp_path / "l1.md"
    l1.write_text("- Licao L1: serie curta enfraquece a ancora historica.", encoding="utf-8")
    l2 = tmp_path / "l2.md"
    l2.write_text("- Licao L2: hurdle sempre rotulado, nunca fair value.", encoding="utf-8")

    assert run_memoria(ns, "--licoes", str(l1)).returncode == 0
    nota1 = _nota(ns)
    assert "Licao L1" in nota1
    assert "### Atualização" in nota1

    assert run_memoria(ns).returncode == 0
    nota2 = _nota(ns)
    assert "Licao L1" in nota2, "regeneração sem --licoes apagou lição anterior"

    assert run_memoria(ns, "--licoes", str(l2)).returncode == 0
    nota3 = _nota(ns)
    assert "Licao L1" in nota3 and "Licao L2" in nota3
    assert nota3.index("Licao L1") < nota3.index("Licao L2")
    assert "(nenhuma lição registrada ainda)" not in nota3


# (f) --sintese substitui; sem --sintese na rodada seguinte, preservada
def test_sintese_verbatim_e_preservada(ns, tmp_path):
    s1 = tmp_path / "s1.md"
    s1.write_text("Tese S1: compounder com spread duradouro; entrar abaixo do bear.", encoding="utf-8")
    s2 = tmp_path / "s2.md"
    s2.write_text("Tese S2: revisao pos-resultado, tese intacta.", encoding="utf-8")

    assert run_memoria(ns, "--sintese", str(s1)).returncode == 0
    assert "Tese S1" in _nota(ns)

    assert run_memoria(ns).returncode == 0
    assert "Tese S1" in _nota(ns), "síntese anterior não preservada sem --sintese"

    assert run_memoria(ns, "--sintese", str(s2)).returncode == 0
    nota = _nota(ns)
    assert "Tese S2" in nota
    assert "Tese S1" not in nota, "--sintese não substituiu a síntese anterior"


# (g) results.json ausente → exit 1 com mensagem PT-BR citando o caminho
def test_results_ausente_exit1(ns):
    (ns / "saida" / "results.json").unlink()
    r = run_memoria(ns)
    assert r.returncode == 1
    assert "não encontrado" in r.stderr
    assert str(ns / "saida" / "results.json") in r.stderr


def test_case_ausente_ou_invalido_exit1(ns):
    (ns / "case.json").unlink()
    r = run_memoria(ns)
    assert r.returncode == 1
    assert "não encontrado" in r.stderr
    assert str(ns / "case.json") in r.stderr

    (ns / "case.json").write_text("{ nao é json", encoding="utf-8")
    r = run_memoria(ns)
    assert r.returncode == 1
    assert "JSON" in r.stderr


def test_sintese_ou_licoes_inexistente_exit1(ns):
    r = run_memoria(ns, "--sintese", str(ns / "nao_existe.md"))
    assert r.returncode == 1
    assert "não encontrado" in r.stderr

    r = run_memoria(ns, "--licoes", str(ns / "nao_existe.md"))
    assert r.returncode == 1
    assert "não encontrado" in r.stderr


# (h) probability_weighted presente na nota (pesos 0.6/0.2/0.2 somam 1)
def test_probability_weighted_presente(ns):
    res = _results(ns)
    pw = res["probability_weighted"]
    assert pw.get("value") is not None, "fixture deveria produzir probability_weighted"
    r = run_memoria(ns)
    assert r.returncode == 0, r.stdout + r.stderr
    nota = _nota(ns)

    linha = next(l for l in nota.splitlines() if "Probability-weighted" in l)
    assert f"{pw['value']:.2f}" in linha
    assert pw["label"] in linha
