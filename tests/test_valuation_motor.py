import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "skills" / "er-valuation" / "scripts"))
# Aliasados: caso.PREMISSAS_FIRM/PREMISSAS_EQUITY são os VOCABULÁRIOS de
# chave aceitos pela rota (frozenset); este arquivo já usa os nomes
# PREMISSAS_FIRM/PREMISSAS_EQUITY abaixo para os dicts CONCRETOS de premissa
# usados nos testes — são conceitos diferentes, daí o alias para não colidir.
from caso import PREMISSAS_EQUITY as VOCABULARIO_EQUITY  # noqa: E402
from caso import PREMISSAS_FIRM as VOCABULARIO_FIRM  # noqa: E402
from motor import (  # noqa: E402
    MotorFalhou,
    RAIZ_VENDOR,
    _FLAGS_BOOLEANAS,
    _FLAGS_COM_HIFEN,
    argv_para,
    executar,
    rodar,
)

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


def test_executar_timeout_vira_motorfalhou_com_diagnostico():
    """Um timeout é o terceiro modo de falha do motor (junto de código != 0
    e JSON inválido) — tem de virar MotorFalhou, nunca escapar como
    subprocess.TimeoutExpired cru, senão quem captura só MotorFalhou (a
    razão do wrapper existir) não pega um motor travado. `timeout` minúsculo
    aqui força esse caminho sem esperar 120s de verdade."""
    argv = argv_para("firm", PREMISSAS_FIRM, None)

    with pytest.raises(MotorFalhou) as excinfo:
        executar(argv, timeout=0.001)

    mensagem = str(excinfo.value)
    assert repr(argv) in mensagem
    assert "0.001" in mensagem
    assert isinstance(excinfo.value.__cause__, subprocess.TimeoutExpired)


def test_argv_mid_year_true_emite_flag_sem_valor_depois():
    premissas = dict(PREMISSAS_FIRM)
    premissas["mid_year"] = True
    argv = argv_para("firm", premissas, None)

    assert "--mid-year" in argv
    indice = argv.index("--mid-year")
    proximo = argv[indice + 1] if indice + 1 < len(argv) else None
    assert proximo is None or proximo.startswith("--")


def test_argv_mid_year_false_nao_emite_flag():
    premissas = dict(PREMISSAS_FIRM)
    premissas["mid_year"] = False
    argv = argv_para("firm", premissas, None)

    assert "--mid-year" not in argv


def test_todo_vocabulario_de_caso_tem_flag_com_hifen_coberta():
    """Trava o invariante implícito entre módulos: o fallback genérico de
    `argv_para`/`_flag` vira `--<chave>` verbatim para qualquer chave fora
    de `_FLAGS_COM_HIFEN`. Se uma chave do vocabulário de `caso.py` tiver
    underscore e não estiver em `_FLAGS_COM_HIFEN` (nem em `_FLAGS_BOOLEANAS`,
    que hoje também tem hífen próprio, mas não é a tabela em si), a flag
    gerada teria underscore onde o motor espera hífen (ex.: '--rir_observado'
    em vez de '--rir-observado') e o motor congelado recusaria o argv. Hoje
    isso não é alcançável só porque o vocabulário de `caso.py` é um
    subconjunto do que a tabela cobre — nada além deste teste garante isso.
    `motor.py` não importa `caso.py` (e continua sem importar); só este
    teste faz a ponte, de fora, para fechar o contrato."""
    for chave in sorted(VOCABULARIO_FIRM | VOCABULARIO_EQUITY):
        coberta = (
            chave in _FLAGS_COM_HIFEN
            or chave in _FLAGS_BOOLEANAS
            or "_" not in chave
        )
        assert coberta, (
            f"premissa '{chave}' (vocabulário de caso.PREMISSAS_FIRM ou "
            "caso.PREMISSAS_EQUITY) tem underscore mas não está em "
            "motor._FLAGS_COM_HIFEN nem em motor._FLAGS_BOOLEANAS: o "
            f"fallback genérico de motor.py emitiria '--{chave}' verbatim "
            "(underscore, não hífen), e o motor congelado recusa flag "
            "assim. Corrija adicionando a chave à tabela _FLAGS_COM_HIFEN "
            "em motor.py."
        )
