import importlib
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "skills" / "er-valuation" / "scripts"))
import caso as caso_mod  # noqa: E402
import ponte as ponte_mod  # noqa: E402
from ponte import compor  # noqa: E402

PONTE = {"divida_bruta": 800.0, "caixa_e_equivalentes": 300.0,
         "outros_ativos": 50.0, "outros_passivos": 20.0, "minoritarios": 100.0}


def test_nd_efetivo_e_a_soma_com_sinal():
    # 800 - 300 + 100 + 20 - 50 = 570
    assert compor(PONTE)["nd_efetivo"] == pytest.approx(570.0)


def test_caixa_liquido_produz_nd_negativo():
    p = dict(PONTE, divida_bruta=0.0, caixa_e_equivalentes=500.0,
             outros_ativos=0.0, outros_passivos=0.0, minoritarios=0.0)
    assert compor(p)["nd_efetivo"] == pytest.approx(-500.0)


def test_parcelas_cobrem_todas_as_linhas_com_sinal():
    parcelas = compor(PONTE)["parcelas"]
    assert [p["rotulo"] for p in parcelas] == [
        "divida_bruta", "caixa_e_equivalentes", "outros_ativos",
        "outros_passivos", "minoritarios"]
    sinais = {p["rotulo"]: p["sinal"] for p in parcelas}
    assert sinais["divida_bruta"] == 1 and sinais["minoritarios"] == 1
    assert sinais["caixa_e_equivalentes"] == -1 and sinais["outros_ativos"] == -1
    # Antes coberto só indiretamente via test_nd_efetivo_e_a_soma_com_sinal
    # (a soma agregada também mudaria se este sinal estivesse errado) — mas
    # uma asserção direta, no mesmo formato das outras quatro linhas, não
    # depende de fazer essa dedução a partir do agregado.
    assert sinais["outros_passivos"] == 1


def test_soma_das_parcelas_reconstroi_o_nd_efetivo():
    """A parcela exibida no waterfall e a MESMA que entra na conta."""
    r = compor(PONTE)
    assert sum(p["valor"] * p["sinal"] for p in r["parcelas"]) == pytest.approx(r["nd_efetivo"])


def test_ponte_zerada_produz_nd_zero():
    assert compor({k: 0.0 for k in PONTE})["nd_efetivo"] == pytest.approx(0.0)


def test_linha_ausente_e_erro_nao_zero_implicito():
    p = dict(PONTE)
    del p["minoritarios"]
    with pytest.raises(KeyError):
        compor(p)


# --------------------------------------------------------------------------
# Guarda de consistência entre SINAIS (ponte.py) e CAMPOS_DA_PONTE (caso.py):
# roda uma vez, no import, e nunca tinha teste. Sem este teste, uma futura
# "simplificação" da checagem para conjunto (set(...) == set(...)) perderia
# a sensibilidade à ordem e deixaria passar em silêncio uma reordenação de
# CAMPOS_DA_PONTE — o waterfall que `compor` produz (ordem das parcelas,
# sinal por linha) dessincronizaria da lista que `caso.py` valida, sem
# nenhum sinal de erro no import.
# --------------------------------------------------------------------------

def test_guarda_de_consistencia_e_real_e_sensivel_a_ordem():
    """Reordenar CAMPOS_DA_PONTE (mesmo conjunto de rótulos, ordem diferente
    de SINAIS) tem de disparar o ImportError no reload de `ponte` — prova
    que a checagem é tupla==tupla (sensível a ordem), não conjunto==conjunto
    (que aceitaria essa reordenação em silêncio).

    `caso.CAMPOS_DA_PONTE` é restaurado e `ponte` é recarregado de volta a
    um estado válido no `finally`, para não deixar nenhum dos dois módulos
    inconsistente para os testes que rodam depois deste.
    """
    original = caso_mod.CAMPOS_DA_PONTE
    reordenado = tuple(reversed(original))
    assert set(reordenado) == set(original)  # mesmo conjunto de rótulos
    assert reordenado != original  # mas ordem diferente

    caso_mod.CAMPOS_DA_PONTE = reordenado
    try:
        with pytest.raises(ImportError, match="divergiram"):
            importlib.reload(ponte_mod)
    finally:
        caso_mod.CAMPOS_DA_PONTE = original
        importlib.reload(ponte_mod)
