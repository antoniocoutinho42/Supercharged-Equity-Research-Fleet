import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "skills" / "er-valuation" / "scripts"))
from motor import MotorFalhou, RAIZ_VENDOR, argv_para, rodar  # noqa: E402

PREMISSAS_FIRM = {"g": 5.0, "roic": 12.0, "wacc": 10.0, "n": 10, "da": 20.0,
                  "tax": 25.0, "tv": "gordon", "roic_tv": 10.0, "gp": 3.0}
PREMISSAS_EQUITY = {"g": 8.0, "roe": 18.0, "ke": 14.0, "n": 10,
                    "gde": 30.0, "nde": 20.0, "tv": "convergencia"}


def test_vendor_esta_onde_o_modulo_espera():
    assert (RAIZ_VENDOR / "scripts" / "justos.py").is_file()


def test_argv_firm_usa_o_subcomando_ev_e_traduz_as_chaves():
    argv = argv_para("firm", PREMISSAS_FIRM, None)
    assert argv[0] == "ev"
    assert "--wacc" in argv and "--roic-tv" in argv
    assert "--tv" in argv and argv[argv.index("--tv") + 1] == "gordon"
    assert "--roe" not in argv


def test_argv_equity_usa_o_subcomando_pe():
    argv = argv_para("equity", PREMISSAS_EQUITY, None)
    assert argv[0] == "pe"
    assert "--roe" in argv and "--ke" in argv and "--gde" in argv
    assert "--wacc" not in argv


def test_argv_inclui_a_escala_quando_informada():
    argv = argv_para("firm", PREMISSAS_FIRM, {"ebitda": 1000.0, "nd": 500.0, "acoes": 100.0})
    for flag in ("--ebitda", "--nd", "--acoes"):
        assert flag in argv


def test_argv_omite_premissa_ausente_em_vez_de_inventar_default():
    premissas = dict(PREMISSAS_FIRM)
    del premissas["gp"]
    assert "--gp" not in argv_para("firm", premissas, None)


def test_rodar_firm_reproduz_os_numeros_do_motor():
    """Ancora capturada do vendor em 2026-08-21 — se mudar, o wrapper ou o motor mudou."""
    out = rodar("firm", PREMISSAS_FIRM, {"ebitda": 1000.0, "nd": 500.0, "acoes": 100.0})
    assert out["EV/EBITDA_curr"] == pytest.approx(6.6906, abs=1e-4)
    assert out["EV"] == pytest.approx(6690.59, abs=0.01)
    assert out["Equity"] == pytest.approx(6190.59, abs=0.01)
    assert out["Preco_acao"] == pytest.approx(61.91, abs=0.01)


def test_rodar_equity_reproduz_os_numeros_do_motor():
    out = rodar("equity", PREMISSAS_EQUITY, {"ni": 500.0, "acoes": 100.0})
    assert out["PL_curr"] == pytest.approx(9.003, abs=1e-3)
    assert out["Equity"] == pytest.approx(4501.51, abs=0.01)
    assert out["Preco_acao"] == pytest.approx(45.02, abs=0.01)


def test_diagnosticos_chegam_intactos():
    out = rodar("firm", PREMISSAS_FIRM, None)
    assert isinstance(out["diagnosticos"], list) and out["diagnosticos"]
    assert any("RiR" in d for d in out["diagnosticos"])


def test_motor_sem_tv_falha_com_a_saida_do_motor():
    premissas = dict(PREMISSAS_FIRM)
    del premissas["tv"]
    with pytest.raises(MotorFalhou):
        rodar("firm", premissas, None)


def test_rodar_nao_suja_o_vendor_com_bytecode():
    rodar("firm", PREMISSAS_FIRM, None)
    assert list(RAIZ_VENDOR.rglob("*.pyc")) == []
