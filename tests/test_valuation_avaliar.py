import json
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures"
SCRIPTS = RAIZ / "skills" / "er-valuation" / "scripts"
sys.path.insert(0, str(SCRIPTS))
from caso import carregar  # noqa: E402
from avaliar import avaliar, escrever  # noqa: E402


def _res_firm() -> dict:
    return avaliar(carregar(FIXTURES / "caso_minimo_firm.json"))


def test_cabecalho_vem_do_caso():
    r = _res_firm()
    assert r["companhia"] == "Sintética S.A."
    assert r["rota"] == "firm" and r["moeda"] == "BRL-nominal"


def test_valor_por_acao_reproduz_o_motor():
    v = _res_firm()["cenarios"]["base"]["valor"]
    assert v["EV"] == pytest.approx(6690.59, abs=0.01)
    assert v["Equity"] == pytest.approx(6190.59, abs=0.01)
    assert v["preco_acao"] == pytest.approx(61.91, abs=0.01)


def test_upside_e_calculado_contra_o_preco_do_caso():
    r = _res_firm()["cenarios"]["base"]
    esperado = 61.91 / 55.0 - 1
    assert r["vs_preco"]["upside"] == pytest.approx(esperado, abs=1e-4)


def test_ponte_aparece_decomposta_e_bate_com_o_nd_usado():
    r = _res_firm()
    assert r["ponte"]["nd_efetivo"] == pytest.approx(500.0)
    assert sum(p["valor"] * p["sinal"] for p in r["ponte"]["parcelas"]) == pytest.approx(500.0)


def test_diagnosticos_do_motor_chegam_ao_resultado():
    d = _res_firm()["cenarios"]["base"]["diagnosticos"]
    assert isinstance(d, list) and any("RiR" in x for x in d)


def test_rota_equity_produz_equity_sem_ponte():
    r = avaliar(carregar(FIXTURES / "caso_minimo_equity.json"))
    assert "ponte" not in r or r["ponte"] is None
    v = r["cenarios"]["base"]["valor"]
    assert v["Equity"] == pytest.approx(4501.51, abs=0.01)
    assert v["preco_acao"] == pytest.approx(45.02, abs=0.01)
    assert "EV" not in v


def test_escala_por_nopat_reconcilia_com_a_escala_por_ebitda():
    """Mesma economia, duas rotas de escala: EV tem de bater.

    Com EBITDA 1000, d 20% e t 25%, o NOPAT coerente e 1000*(1-0.20)*(1-0.25) = 600.
    EV/NOPAT_curr x 600 tem de dar o mesmo EV que EV/EBITDA_curr x 1000.
    """
    c = carregar(FIXTURES / "caso_minimo_firm.json")
    c["metrica_base"] = {"tipo": "NOPAT", "valor": 600.0, "periodo": "2025A",
                         "fonte": "derivado do EBITDA da fixture"}
    r = avaliar(c)
    assert r["cenarios"]["base"]["valor"]["EV"] == pytest.approx(6690.59, abs=0.05)


def test_saida_e_deterministica():
    a = json.dumps(_res_firm(), sort_keys=True, ensure_ascii=False)
    b = json.dumps(_res_firm(), sort_keys=True, ensure_ascii=False)
    assert a == b


def test_saida_nao_carrega_hora_nem_caminho_absoluto():
    texto = json.dumps(_res_firm(), ensure_ascii=False)
    assert "C:\\" not in texto and "/c/" not in texto
    for suspeito in ("timestamp", "gerado_em", "executado_em"):
        assert suspeito not in texto


def test_escrever_e_reler_preserva(tmp_path):
    destino = tmp_path / "resultados.json"
    escrever(_res_firm(), destino)
    assert json.loads(destino.read_text(encoding="utf-8"))["rota"] == "firm"


def test_cli_gera_o_arquivo(tmp_path):
    destino = tmp_path / "out.json"
    r = subprocess.run(
        [sys.executable, str(SCRIPTS / "avaliar.py"),
         str(FIXTURES / "caso_minimo_firm.json"), "--out", str(destino)],
        capture_output=True, text=True, encoding="utf-8", timeout=120)
    assert r.returncode == 0, r.stdout + r.stderr
    assert json.loads(destino.read_text(encoding="utf-8"))["companhia"] == "Sintética S.A."


def test_cli_recusa_caso_invalido_com_exit_1(tmp_path):
    ruim = tmp_path / "ruim.json"
    c = json.loads((FIXTURES / "caso_minimo_firm.json").read_text(encoding="utf-8"))
    del c["cenarios"]["base"]["premissas"]["tv"]
    ruim.write_text(json.dumps(c), encoding="utf-8")
    r = subprocess.run(
        [sys.executable, str(SCRIPTS / "avaliar.py"), str(ruim), "--out", str(tmp_path / "x.json")],
        capture_output=True, text=True, encoding="utf-8", timeout=120)
    assert r.returncode == 1
    assert "convenção terminal" in (r.stdout + r.stderr)
