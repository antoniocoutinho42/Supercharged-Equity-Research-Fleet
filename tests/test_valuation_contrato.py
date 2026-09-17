"""Contrato `resultados/1` (fatia 5A, item 5, Task 1).

Ver docs/superpowers/plans/2026-09-11-v4-item5a-contratos-builder.md, seção
"Task 1", para as seis regras do contrato. Os testes abaixo discriminam a
matemática (hash canônico, múltiplo de tela por rota) e o contrato (versão,
origem, manchete, diagnósticos classificados, cenário-base) — não repetem
metodologia, que já é coberta por `tests/test_valuation_*.py`.
"""

import copy
import hashlib
import json
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
FIXTURES = RAIZ / "tests" / "fixtures"
sys.path.insert(0, str(RAIZ / "skills" / "er-valuation" / "scripts"))
from avaliar import avaliar  # noqa: E402
from caso import (  # noqa: E402
    LIMITACOES_DE_REVERSA, TV_CANON, CasoInvalido, carregar, reversa_indisponivel, validar,
)
import diagnosticos  # noqa: E402
import reversa as reversa_modulo  # noqa: E402
from reversa import limitacoes_da_leitura  # noqa: E402

# O construtor do bloco 'reversa' de teste e as variantes compostas (D14 da 5F) moram em
# `tests/relatorio_apoio.py`: são os mesmos que compõem as entregas de teste do relatório.
sys.path.insert(0, str(RAIZ / "tests"))
from relatorio_apoio import VARIANTES_DO_CASO, carregar_fixture_ou_variante, com_bloco_de_reversa_valido  # noqa: E402

CASOS = sorted(p.name for p in FIXTURES.glob("caso_*.json"))
MANIFEST = json.loads((RAIZ / "skills" / "er-multiplos-justos" / "manifest_vendor.json").read_text(encoding="utf-8"))


def _sha(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False).encode("utf-8")).hexdigest()


@pytest.fixture(scope="module")
def resultados():
    """As fixtures e, desde a 5F, as variantes compostas: `nome -> (caso, resultados)`."""
    return {nome: (carregar_fixture_ou_variante(nome), avaliar(carregar_fixture_ou_variante(nome)))
            for nome in CASOS + sorted(VARIANTES_DO_CASO)}


def test_versao_e_origem_em_todo_resultado(resultados):
    for nome, (caso, r) in resultados.items():
        assert r["versao_contrato"] == "resultados/1", nome
        assert r["origem"]["caso_sha256"] == _sha(caso), nome
        assert r["origem"]["metodologia"] == {"nome": "multiplos-justos", "versao": MANIFEST["versao"]}, nome


def test_hash_ignora_ordem_de_chaves_do_arquivo(tmp_path):
    caso = json.loads((FIXTURES / "caso_minimo_firm.json").read_text(encoding="utf-8"))
    invertido = tmp_path / "caso.json"
    invertido.write_text(json.dumps(dict(reversed(list(caso.items()))), indent=4), encoding="utf-8")
    assert avaliar(carregar(invertido))["origem"]["caso_sha256"] == _sha(caso)


def test_diagnosticos_chaves_paralelas_e_classificadas(resultados):
    for nome, (_caso, r) in resultados.items():
        for cen, reg in r["cenarios"].items():
            if "diagnosticos" in reg:
                assert len(reg["diagnosticos_chaves"]) == len(reg["diagnosticos"]), (nome, cen)
                assert reg["diagnosticos_chaves"] == [diagnosticos.classificar(m) for m in reg["diagnosticos"]]
            assert None not in reg["diagnosticos_chaves"], (nome, cen)


def test_manchete_aponta_um_preco_que_existe(resultados):
    for nome, (caso, r) in resultados.items():
        m = r["manchete"]
        if "sotp" in caso:
            assert m["fonte"] == "sotp" and m["preco_acao"] == r["sotp"]["preco_acao"] and "multiplo" not in m
        else:
            assert m["fonte"] == "cenarios"
            assert m["preco_acao"] == r["cenarios"][m["cenario"]]["valor"]["preco_acao"]
        assert m["upside"] == m["preco_acao"] / caso["preco"]["valor"] - 1, nome


def test_manchete_convencao_terminal_e_canonica_ou_ausente_no_sotp(resultados):
    """A1 (onda de correção da revisão final, achado F2): `manchete` publica
    o código CANÔNICO da convenção terminal do cenário-base — nunca o
    literal que o caso declarou — e fica ausente quando a manchete vem do
    SOTP (as partes podem ter convenções diferentes entre si; ver
    `caso_sotp_segmento.json`, que mistura 'convergencia' e 'gordon' — a
    manchete nunca escolhe uma pelas partes)."""
    for nome, (caso, r) in resultados.items():
        m = r["manchete"]
        if m["fonte"] == "sotp":
            assert "convencao_terminal" not in m, nome
            continue
        tv_declarado = caso["cenarios"][m["cenario"]]["premissas"]["tv"]
        assert m["convencao_terminal"] == TV_CANON.get(tv_declarado, tv_declarado), nome
        # sempre um dos três canônicos hoje — nunca o literal cru quando o
        # literal é um alias (nenhuma fixture usa alias, mas a igualdade
        # acima já cobre isso; esta linha documenta a garantia adicional de
        # que o campo nunca fica fora do vocabulário do catálogo).
        assert m["convencao_terminal"] in {"book", "convergencia", "gordon"}, nome


def test_manchete_convencao_terminal_canoniza_alias_legado():
    """VERIFICAÇÃO end-to-end do achado F2 da revisão: um caso que declara
    'tv' por um alias legado ('ic'/'spread' — o motor os aceita e os
    canoniza antes de qualquer handler, `justos.py` tv_canon) publica o
    código CANÔNICO na manchete, nunca o alias. Preços conferidos contra a
    evidência VERIFICADA da revisão (review-5a-final.md, achado F2): 'ic' em
    `caso_minimo_firm.json` -> R$ 55,31; 'spread' -> R$ 61,91."""
    base = json.loads((FIXTURES / "caso_minimo_firm.json").read_text(encoding="utf-8"))

    ic = json.loads(json.dumps(base))
    ic["cenarios"]["base"]["premissas"]["tv"] = "ic"
    validar(ic)
    r_ic = avaliar(ic)
    assert r_ic["manchete"]["convencao_terminal"] == "book"
    assert r_ic["manchete"]["preco_acao"] == pytest.approx(55.31, abs=0.01)

    spread = json.loads(json.dumps(base))
    spread["cenarios"]["base"]["premissas"]["tv"] = "spread"
    validar(spread)
    r_spread = avaliar(spread)
    assert r_spread["manchete"]["convencao_terminal"] == "gordon"
    assert r_spread["manchete"]["preco_acao"] == pytest.approx(61.91, abs=0.01)


def test_mercado_tela_da_rampa_e_do_lado_do_ev():
    caso = carregar(FIXTURES / "caso_rampa.json")
    tela = avaliar(caso)["mercado_tela"]
    assert tela["base"] == "ebitda0"
    ev_mercado = caso["preco"]["valor"] * caso["acoes_diluidas"] + avaliar(caso)["ponte"]["nd_efetivo"]
    assert tela["valor"] == ev_mercado / caso["metrica_base"]["valor"]


def test_cenario_base_obrigatorio_com_mais_de_um_cenario():
    caso = json.loads((FIXTURES / "caso_minimo_firm.json").read_text(encoding="utf-8"))
    caso["cenarios"]["bull"] = caso["cenarios"]["base"]
    with pytest.raises(CasoInvalido, match="cenario_base"):
        validar(caso)
    caso["cenario_base"] = "inexistente"
    with pytest.raises(CasoInvalido, match="cenario_base"):
        validar(caso)
    caso["cenario_base"] = "base"
    validar(caso)


# --------------------------------------------------------------------------
# Casos extras listados pelo plano: mercado_tela para firm, equity e degrau;
# recusa de cenario_base de tipo errado.
# --------------------------------------------------------------------------

def test_mercado_tela_do_firm_bate_no_caso_reversa_firm():
    """O mesmo 6.0 que `alvo_de_mercado`/`reversa.reverter` já produzem para
    esta fixture (`tests/test_valuation_reversa.py`) — `mercado_tela` publica
    o MESMO número, agora sempre, fora do bloco `reversa`."""
    caso = carregar(FIXTURES / "caso_reversa_firm.json")
    tela = avaliar(caso)["mercado_tela"]
    assert tela["base"] == "ebitda"
    assert tela["chave"] == "EV/EBITDA_curr"
    assert tela["valor"] == pytest.approx(6.0)


def test_mercado_tela_do_equity_e_market_cap_sobre_ll():
    caso = carregar(FIXTURES / "caso_minimo_equity.json")
    tela = avaliar(caso)["mercado_tela"]
    assert tela["base"] == "pl"
    assert tela["chave"] == "PL_curr"
    market_cap = caso["preco"]["valor"] * caso["acoes_diluidas"]
    assert tela["valor"] == pytest.approx(market_cap / caso["metrica_base"]["valor"])


def test_mercado_tela_do_degrau_e_pvp_observado_contra_pvp_com_degrau():
    """A tela usa o P/VP OBSERVADO (preco/vpa, sem passar pelo motor); a
    manchete usa o P/VP JUSTO (PVP_com_degrau). As duas bases são 'pvp' — é
    assim que o relatório pareia os dois — mas as chaves são deliberadamente
    diferentes."""
    caso = carregar(FIXTURES / "caso_degrau.json")
    r = avaliar(caso)
    tela = r["mercado_tela"]
    assert tela["chave"] == "PVP"
    assert tela["base"] == "pvp"
    assert tela["valor"] == pytest.approx(caso["preco"]["valor"] / caso["degrau"]["vpa"]["valor"])

    manchete = r["manchete"]
    assert manchete["multiplo"]["chave"] == "PVP_com_degrau"
    assert manchete["multiplo"]["base"] == "pvp"
    assert manchete["multiplo"]["valor"] == pytest.approx(
        r["cenarios"]["base"]["degrau"]["com_transicao"])


def test_cenario_base_de_tipo_errado_e_recusado():
    caso = json.loads((FIXTURES / "caso_minimo_firm.json").read_text(encoding="utf-8"))
    caso["cenario_base"] = 123
    with pytest.raises(CasoInvalido, match="cenario_base"):
        validar(caso)


# --------------------------------------------------------------------------
# Fatia 5D, Task 1 (D3/D4 do plano docs/superpowers/plans/2026-09-14-v4-item5d-
# tese.md): o que só a integração sabe sobre o escopo do caso — a fronteira de
# escopo declarada e as limitações que tornam a reversa impossível —, sempre
# publicado. O relatório lê as chaves; as regras ficam em `caso.py`.
# --------------------------------------------------------------------------

def test_fronteira_de_escopo_e_limitacoes_sao_sempre_publicadas(resultados):
    """Campo de contrato ausente não some em silêncio: toda fixture (e variante)
    publica os dois. Nenhuma declara fronteira (`null`), e `limitacoes` é exatamente
    o que `caso.reversa_indisponivel` devolve, numa lista — vazia quando `None` —,
    seguido, desde a 5F (D3), do que `reversa.limitacoes_da_leitura` devolve sobre a
    reversa publicada. As duas famílias têm de aparecer, senão a igualdade seria
    vacuamente verde de um dos lados."""
    vistas = {"da_reversa": 0, "da_leitura": 0}
    for nome, (caso, r) in resultados.items():
        assert "fronteira_de_escopo" in r and r["fronteira_de_escopo"] is None, nome
        chave = reversa_indisponivel(caso)
        da_leitura = limitacoes_da_leitura(r["reversa"]) if "reversa" in r else []
        assert r["limitacoes"] == ([] if chave is None else [chave]) + da_leitura, nome
        vistas["da_reversa"] += chave is not None
        vistas["da_leitura"] += bool(da_leitura)
    assert all(vistas.values()), f"trava vacuamente verde: {vistas}"


def test_fronteira_de_escopo_declarada_sai_publicada_como_o_gate_a_validou():
    fronteira = {
        "classe": "pre_lucro",
        "arquitetura_dominante": "opção sobre a conversão do funil em receita recorrente",
        "razao": "sem lucro operacional; a métrica-manchete da metodologia não se aplica",
    }
    caso = json.loads((FIXTURES / "caso_minimo_firm.json").read_text(encoding="utf-8"))
    caso["fronteira_de_escopo"] = copy.deepcopy(fronteira)
    validar(caso)
    assert avaliar(caso)["fronteira_de_escopo"] == fronteira


def test_limitacao_de_reversa_e_publicada_se_e_so_se_o_gate_recusa_reversa_valida(resultados):
    """A trava de D4. A Análise exige reversa, mas o gate a recusa em
    combinações que o Fleet não implementa; `resultados.limitacoes` publica a
    chave de reversa exatamente nas fixtures em que acrescentar um bloco
    'reversa' válido faz `caso.validar` recusar — e a recusa é a da limitação
    que a chave nomeia (`caso.LIMITACOES_DE_REVERSA`). Quem decide é o gate:
    nenhuma fixture é nomeada aqui. Uma recusa de reversa escrita no gate por
    fora do registro, ou um `reversa_indisponivel` que esqueça uma limitação,
    reprovam. Os dois lados têm de aparecer — toda limitação registrada em
    alguma fixture, e alguma fixture que admita reversa —, senão a trava seria
    vacuamente verde."""
    exercitadas = set()
    admitem = []
    for nome, (caso, r) in resultados.items():
        publicadas = [chave for chave in r["limitacoes"] if chave in LIMITACOES_DE_REVERSA]
        try:
            validar(com_bloco_de_reversa_valido(caso))
            recusa = None
        except CasoInvalido as erro:
            recusa = str(erro)
        if recusa is None:
            assert not publicadas, (
                f"{nome}: o gate admite um bloco 'reversa' válido, mas resultados.limitacoes "
                f"publica {publicadas}")
            admitem.append(nome)
            continue
        assert len(publicadas) == 1, (
            f"{nome}: o gate recusa um bloco 'reversa' válido, mas resultados.limitacoes = "
            f"{r['limitacoes']}. Recusa do gate: {recusa}")
        assert recusa == LIMITACOES_DE_REVERSA[publicadas[0]](caso), (
            f"{nome}: a recusa do gate não é a da limitação publicada ({publicadas[0]}). "
            f"Recusa do gate: {recusa}")
        exercitadas.add(publicadas[0])
    assert admitem, "nenhuma fixture admite reversa — a trava perdeu o lado sem limitação"
    assert exercitadas == set(LIMITACOES_DE_REVERSA), (
        f"limitação registrada sem fixture que a exercite: "
        f"{sorted(set(LIMITACOES_DE_REVERSA) - exercitadas)}")



# --------------------------------------------------------------------------
# Fatia 5F, Task 2 (D5/D7 do plano docs/superpowers/plans/2026-09-15-v4-item5f-
# valuation.md): o par forward com a base declarada e a escala dos montantes.
# --------------------------------------------------------------------------

def test_o_multiplo_de_tela_forward_e_o_valor_de_mercado_sobre_a_metrica_forward_declarada(resultados):
    """O oráculo é montado aqui, a partir do caso: o valor de mercado (na rota firm, com a dívida
    líquida da ponte) sobre a métrica forward declarada, nunca sobre a métrica-base. A base é a da
    manchete, e o múltiplo justo forward da manchete é o `_fwd` do cenário-base."""
    esperados = {
        "forward_firm": ("EV/EBITDA_fwd", lambda caso, r: (
            caso["preco"]["valor"] * caso["acoes_diluidas"] + r["ponte"]["nd_efetivo"]) / caso["metrica_forward"]["valor"]),
        "forward_equity": ("PL_fwd", lambda caso, r: (
            caso["preco"]["valor"] * caso["acoes_diluidas"]) / caso["metrica_forward"]["valor"]),
    }
    for nome, (chave, oraculo) in esperados.items():
        caso, r = resultados[nome]
        tela, manchete = r["mercado_tela_forward"], r["manchete"]
        assert tela["chave"] == chave and tela["valor"] == pytest.approx(oraculo(caso, r)), nome
        assert tela["metrica"] == caso["metrica_forward"], nome
        assert tela["base"] == manchete["multiplo"]["base"] == manchete["multiplo_forward"]["base"], nome
        assert manchete["multiplo_forward"]["chave"] == chave, nome
        assert manchete["multiplo_forward"]["valor"] == r["cenarios"][manchete["cenario"]]["multiplos"][chave], nome


def test_o_multiplo_justo_forward_da_manchete_so_existe_fora_do_sotp_do_degrau_e_da_rampa(resultados):
    com_forward = 0
    for nome, (caso, r) in resultados.items():
        sem_forward = "sotp" in caso or "degrau" in caso or caso["rota"] == "rampa"
        assert ("multiplo_forward" in r["manchete"]) is not sem_forward, nome
        com_forward += not sem_forward
    assert com_forward, "nenhuma fixture com o múltiplo forward — trava vacuamente verde"


def test_sem_declaracao_a_tela_forward_e_a_escala_saem_nulas(resultados):
    """Campo de contrato ausente não some em silêncio: toda fixture publica os dois, nulos; a
    variante `escala` publica o código que declarou."""
    for nome in CASOS:
        _caso, r = resultados[nome]
        assert "mercado_tela_forward" in r and r["mercado_tela_forward"] is None, nome
        assert "escala_monetaria" in r and r["escala_monetaria"] is None, nome
    assert resultados["escala"][1]["escala_monetaria"] == "milhoes"


# --------------------------------------------------------------------------
# Fatia 5G, Tasks 1 e 2 (D1/D2/D3/D4 do plano docs/superpowers/plans/2026-09-15-v4-
# item5g-alternativas.md): o painel de escolhas e as três leituras da §9 — campos de
# contrato que nunca somem em silêncio.
# --------------------------------------------------------------------------

def test_o_painel_e_as_tres_leituras_sao_sempre_publicados(resultados):
    """Toda fixture e toda variante publica os cinco campos. Sem o bloco que a declara,
    cada leitura sai `null` e o painel sai vazio, sem alerta; com ele, a variante
    correspondente publica o conteúdo. Os dois lados têm de aparecer."""
    vistas = {"escolhas": 0, "empilhamento": 0, "retorno_exigido": 0,
              "valor_ponderado": 0, "cross_check": 0}
    for nome, (caso, r) in resultados.items():
        assert isinstance(r["escolhas_metodologicas"], list), nome
        assert ("escolhas_metodologicas" in caso) is bool(r["escolhas_metodologicas"]), nome
        assert "empilhamento" in r, nome
        vistas["escolhas"] += bool(r["escolhas_metodologicas"])
        vistas["empilhamento"] += r["empilhamento"] is not None
        for campo, bloco in (("retorno_exigido", "retorno_exigido"),
                             ("valor_ponderado", "pesos_de_probabilidade"),
                             ("cross_check", "cross_check")):
            assert campo in r, (nome, campo)
            assert (r[campo] is not None) is (bloco in caso), (nome, campo)
            vistas[campo] += r[campo] is not None
    assert all(vistas.values()), f"trava vacuamente verde: {vistas}"


def test_o_registro_de_drivers_e_sempre_publicado_e_nulo_sem_o_bloco(resultados):
    """Item 6, Task 1 (D1): toda fixture sai com `drivers: null` — nenhuma declara o bloco —, e a
    variante que o declara sai com um registro por driver declarado."""
    com_bloco = 0
    for nome, (caso, r) in resultados.items():
        assert "drivers" in r, nome
        if "drivers" not in caso:
            assert r["drivers"] is None, nome
            continue
        assert len(r["drivers"]["drivers"]) == len(caso["drivers"]), nome
        com_bloco += 1
    assert all(resultados[nome][1]["drivers"] is None for nome in CASOS)
    assert com_bloco, "nenhuma variante com drivers — trava vacuamente verde"


# --------------------------------------------------------------------------
# Fatia 5H, Task 1 (D1/D2 do plano docs/superpowers/plans/2026-09-15-v4-item5h-leitura-
# de-preco.md): o nível implícito anda com a reversa — dentro dela, sempre, com as
# chaves do motor mais a leitura classificada; sem reversa, não há bloco onde procurá-lo.
# --------------------------------------------------------------------------

_CHAVES_DO_NIVEL_IMPLICITO = {"metrica_base_atual", "metrica_base_implicita",
                              "fator_k_implicito", "degrau_implicito_%", "leitura_chave"}


def test_o_nivel_implicito_existe_se_e_so_se_a_reversa_existe(resultados):
    """E as razões contra o consenso existem se e só se o caso o declara, ponto a ponto
    — nunca uma razão sem consenso, nunca um consenso sem razão."""
    vistas = {"com_reversa": 0, "sem_reversa": 0, "com_consenso": 0, "sem_consenso": 0}
    for nome, (caso, r) in resultados.items():
        if "reversa" not in r:
            vistas["sem_reversa"] += 1
            continue
        vistas["com_reversa"] += 1
        nivel = r["reversa"]["nivel_implicito"]
        assert _CHAVES_DO_NIVEL_IMPLICITO <= set(nivel), (nome, sorted(nivel))
        consenso = caso["reversa"].get("consenso") or {}
        vistas["com_consenso" if consenso else "sem_consenso"] += 1
        for ponto in ("t1", "t2"):
            assert (f"razao_vs_consenso_{ponto}" in nivel) is (ponto in consenso), (nome, ponto)
        assert (nivel["leitura_chave"] is not None) is bool(consenso), nome
        assert nivel["leitura_chave"] in (None, *reversa_modulo.LEITURAS_DO_NIVEL), nome
    assert all(vistas.values()), f"trava vacuamente verde: {vistas}"


def test_o_valor_de_mercado_do_alvo_e_o_numerador_do_multiplo_de_tela(resultados):
    """O número que o nível implícito recebe em `--alvo-valor` é o NUMERADOR da mesma
    conta que produz o múltiplo de mercado — nunca uma segunda conta: valor de mercado
    ÷ métrica-base = múltiplo do alvo, em toda rota que tem reversa."""
    vistos = 0
    for nome, (caso, r) in resultados.items():
        if "reversa" not in r:
            continue
        alvo = r["reversa"]["alvo"]
        assert alvo["valor_de_mercado"] / caso["metrica_base"]["valor"] == pytest.approx(alvo["valor"])
        vistos += 1
    assert vistos, "nenhuma fixture com reversa — trava vacuamente verde"
