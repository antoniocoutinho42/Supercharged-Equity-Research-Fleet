"""Matriz rota x bloco: a classe de teste que teria pego o Crítico.

Revisão final (task 3c), FIX 7. Este módulo NÃO testa nenhum bloco em
profundidade — isso já é responsabilidade de `test_valuation_caso.py`,
`test_valuation_avaliar.py`, `test_valuation_reversa.py`,
`test_valuation_sensibilidades.py` e `test_valuation_sotp.py`, e continua
sendo depois deste arquivo. A responsabilidade ÚNICA aqui é o PRODUTO rota
x bloco: para cada uma das 3 rotas (`firm`, `equity`, `rampa`) cruzada com
cada um dos 3 blocos opcionais (`mercado+reversa`, `sensibilidades`,
`sotp`) — 9 células — confirma que o resultado é SEMPRE um destes dois,
nunca um terceiro:

  - `validar()` aceita (a combinação é suportada nesta fatia), ou
  - `validar()` recusa com `CasoInvalido`, nomeando o motivo (a combinação
    não é suportada — limitação declarada, não bug).

Para toda célula que PASSA na validação, este módulo também roda
`avaliar()` e confirma que ela devolve um resultado de verdade ou levanta
`CasoInvalido`/`MotorFalhou` — nunca um `KeyError`/`TypeError`/
`AttributeError` cru vazando de um dict indexado por rota ou de uma
premissa que o motor não reconhece.

É esta classe de teste — o PRODUTO sistemático, não mais uma suíte por
bloco — que teria pego o Crítico desta revisão: `rampa+sensibilidades`
batia `KeyError: 'rampa'` NO PORTÃO (os validadores de grade indexam o
mapa do triângulo sem checar se a rota tem um); `rampa+reversa` passava o
portão inteiro e só batia `KeyError: 'rampa'` DENTRO de `avaliar()`,
depois do motor já ter rodado os cenários principais do caso — subprocessos
desperdiçados antes da recusa. Nenhuma suíte por bloco cruzava essas duas
coisas: `test_valuation_reversa.py`/`test_valuation_sensibilidades.py`
testam o bloco só sobre a rota para a qual a fixture canônica foi
desenhada (sempre `firm`); nada testava sistematicamente o PRODUTO. FIX 1
fechou os dois achados; este módulo é o fechamento durável — a garantia de
que a MESMA classe de lacuna (bloco novo, rota nova, ninguém testou o
produto) não reabre em silêncio na próxima fatia.

Cada célula usa o menor caso válido possível, adaptado das fixtures já
existentes (`caso_minimo_firm.json`, `caso_minimo_equity.json`,
`caso_rampa.json`, o bloco `sotp` de `caso_sotp_segmento.json`) — uma
grade de sensibilidade com um único ponto, um único eixo de reversa
(`custo_capital`, o obrigatório), as duas partes mínimas de SOTP (SOTP
exige >= 2). Nenhuma célula foi assumida: as 9 foram sondadas por fora
antes deste arquivo existir, e os vereditos abaixo (`MATRIZ`) refletem
exatamente o que `validar()`/`avaliar()` fazem hoje, não uma expectativa.
"""

import copy
import json
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures"
sys.path.insert(0, str(RAIZ / "skills" / "er-valuation" / "scripts"))
from caso import CasoInvalido, validar  # noqa: E402
from avaliar import avaliar  # noqa: E402
from motor import MotorFalhou  # noqa: E402


def _carregado(nome: str) -> dict:
    return json.loads((FIXTURES / nome).read_text(encoding="utf-8"))


def _firm() -> dict:
    return _carregado("caso_minimo_firm.json")


def _equity() -> dict:
    return _carregado("caso_minimo_equity.json")


def _rampa() -> dict:
    return _carregado("caso_rampa.json")


# Menor bloco mercado+reversa válido: só o eixo obrigatório da metodologia
# (`custo_capital`) — sem ele 'reversa' já é recusada por outro motivo,
# irrelevante ao que esta matriz mede.
_MERCADO_MINIMO = {"rf": 12.0, "erp": 5.5, "fonte": "fixture da matriz", "data": "2026-08-25"}

TRIANGULO_FIRM = {"inputs": ["g", "roic"], "output": "rir"}
TRIANGULO_EQUITY = {"inputs": ["g", "roe"], "output": "rir"}


def _com_reversa(caso: dict) -> dict:
    """Adapta um caso mínimo (qualquer rota) com o menor bloco
    mercado+reversa válido: um eixo só (o obrigatório), cenário 'base'."""
    c = copy.deepcopy(caso)
    c["mercado"] = dict(_MERCADO_MINIMO)
    c["reversa"] = {"cenario": "base", "eixos": ["custo_capital"]}
    return c


def _com_sensibilidades(caso: dict, premissa: str, triangulo: dict) -> dict:
    """Adapta um caso mínimo com a menor grade de sensibilidade válida:
    uma grade 1D de UM ponto só — runtime mínimo (uma célula = um
    subprocesso do motor), sem perder nada que esta matriz precisa medir
    (o formato da grade, não a superfície que ela varre)."""
    c = copy.deepcopy(caso)
    c["sensibilidades"] = {
        "cenario": "base",
        "grades_1d": [{"premissa": premissa, "pontos": [9.0], "triangulo": triangulo}],
        "grades_2d": [],
    }
    return c


def _com_sotp_do_segmento(caso: dict, *, com_materialidade: bool) -> dict:
    """Adapta um caso mínimo com o bloco 'sotp' da fixture do segmento:
    duas partes na rota 'firm' (SOTP exige >= 2; as duas são
    self-contained — carregam a própria rota/premissas, independentes da
    rota do CASO). `materialidade.blended` não declara rota própria: roda
    sob a rota do CASO — só é mantida quando essa rota já é 'firm' (a
    mesma para a qual a fixture do segmento foi desenhada); nas demais
    combinações minimamente válidas é omitida (o bloco é opcional)."""
    c = copy.deepcopy(caso)
    sotp = copy.deepcopy(_carregado("caso_sotp_segmento.json")["sotp"])
    if not com_materialidade:
        sotp.pop("materialidade", None)
    c["sotp"] = sotp
    return c


def _caso_firm_com_reversa() -> dict:
    return _com_reversa(_firm())


def _caso_firm_com_sensibilidades() -> dict:
    return _com_sensibilidades(_firm(), "wacc", TRIANGULO_FIRM)


def _caso_firm_com_sotp() -> dict:
    return _com_sotp_do_segmento(_firm(), com_materialidade=True)


def _caso_equity_com_reversa() -> dict:
    return _com_reversa(_equity())


def _caso_equity_com_sensibilidades() -> dict:
    return _com_sensibilidades(_equity(), "ke", TRIANGULO_EQUITY)


def _caso_equity_com_sotp() -> dict:
    # SOTP soma EV; a rota equity não produz EV (D3) -- recusada no gate
    # antes de examinar o conteúdo do bloco. Reusa o mesmo builder por
    # uniformidade (o conteúdo em si não importa para esta célula).
    return _com_sotp_do_segmento(_equity(), com_materialidade=False)


def _caso_rampa_com_reversa() -> dict:
    return _com_reversa(_rampa())


def _caso_rampa_com_sensibilidades() -> dict:
    return _com_sensibilidades(_rampa(), "g2", TRIANGULO_FIRM)


def _caso_rampa_com_sotp() -> dict:
    return _com_sotp_do_segmento(_rampa(), com_materialidade=False)


# --------------------------------------------------------------------------
# Fatia D, Task 1: 'degrau' (Gate 3) x os três blocos opcionais já cobertos
# acima (D7 do plano: "degrau junto de reversa, sensibilidades ou sotp
# recusado no gate, por nome"). Só faz sentido na rota equity (D2 já recusa
# 'degrau' nas outras duas rotas — não é célula desta matriz, é
# `test_valuation_degrau.py`). Menor bloco 'degrau' válido, adaptado do
# mesmo exemplo do SKILL.md do vendor usado na âncora de
# `test_valuation_degrau.py`; 'm' tem só 'base' — o único cenário de
# `caso_minimo_equity.json`.
# --------------------------------------------------------------------------

_DEGRAU_MINIMO = {
    "indice_atual": {"valor": 19.3, "fonte": "fixture da matriz", "data": "2026-08-25"},
    "piso_teorico": 11.0,
    "indice_alvo": {"valor": 14.0, "razao": "fixture da matriz"},
    "anos": 4,
    "perfil_transicao": "rampa",
    "razao_transicao": "fixture da matriz",
    "vpa": {"valor": 29.11, "fonte": "fixture da matriz", "data": "2026-08-25"},
    "fx": 1.0,
    "m": {"base": {"valor": 100.0, "razao": "fixture da matriz"}},
}


def _com_degrau(caso: dict) -> dict:
    c = copy.deepcopy(caso)
    c["degrau"] = copy.deepcopy(_DEGRAU_MINIMO)
    return c


def _caso_equity_com_degrau_e_reversa() -> dict:
    return _com_reversa(_com_degrau(_equity()))


def _caso_equity_com_degrau_e_sensibilidades() -> dict:
    return _com_sensibilidades(_com_degrau(_equity()), "ke", TRIANGULO_EQUITY)


def _caso_equity_com_degrau_e_sotp() -> dict:
    return _com_sotp_do_segmento(_com_degrau(_equity()), com_materialidade=False)


# Fatia 5F, Task 2 (D5): a menor métrica forward válida, do mesmo tipo da métrica-base do caso —
# a única recusa possível é a da combinação.
_METRICA_FORWARD_MINIMA = {"valor": 30.0, "periodo": "2026E", "fonte": "fixture da matriz"}


def _com_metrica_forward(caso: dict) -> dict:
    c = copy.deepcopy(caso)
    c["metrica_forward"] = {"tipo": c["metrica_base"]["tipo"], **_METRICA_FORWARD_MINIMA}
    return c


def _caso_rampa_com_metrica_forward() -> dict:
    return _com_metrica_forward(_rampa())


def _caso_equity_com_degrau_e_metrica_forward() -> dict:
    return _com_metrica_forward(_com_degrau(_equity()))


# --------------------------------------------------------------------------
# A matriz: 3 rotas x 3 blocos opcionais = 9 células. `constroi` monta o
# caso minimamente válido da célula; `deve_passar` é o veredito de
# `validar()` — `True` (aceita) ou `False` (`CasoInvalido` nomeado).
#
# As 3 recusas, e por quê:
#   - equity+sotp: SOTP soma EV (D3); a rota equity não produz EV nem
#     admite ponte de dívida (Fatia C, Task 4).
#   - rampa+mercado+reversa: `RESOLVER_POR_EIXO` (reversa.py) não tem
#     entrada 'rampa' — vocabulário de reversa não definido para a
#     composição bifásica nesta fatia (FIX 1, Crítico, revisão final).
#   - rampa+sensibilidades: a rota rampa não usa o triângulo
#     g = RiR x retorno — vocabulário de grade não definido para a
#     composição bifásica nesta fatia (FIX 1, Crítico, revisão final).
#
# As 6 aceitas rodam avaliar() de ponta a ponta contra o motor congelado de
# verdade, sem mock — inclusive rampa+sotp, a célula que nenhuma fixture
# nem teste anterior exercitava (a rota do CASO inteiro sendo rampa, com
# um bloco sotp de partes 'firm' por cima): confirmado por sondagem antes
# deste arquivo existir que ela passa limpo, sem crash.
# --------------------------------------------------------------------------

MATRIZ = {
    ("firm", "mercado+reversa"): (_caso_firm_com_reversa, True),
    ("firm", "sensibilidades"): (_caso_firm_com_sensibilidades, True),
    ("firm", "sotp"): (_caso_firm_com_sotp, True),
    ("equity", "mercado+reversa"): (_caso_equity_com_reversa, True),
    ("equity", "sensibilidades"): (_caso_equity_com_sensibilidades, True),
    ("equity", "sotp"): (_caso_equity_com_sotp, False),
    ("rampa", "mercado+reversa"): (_caso_rampa_com_reversa, False),
    ("rampa", "sensibilidades"): (_caso_rampa_com_sensibilidades, False),
    ("rampa", "sotp"): (_caso_rampa_com_sotp, True),
    # Fatia D, Task 1 (D7): 'degrau' só existe na rota equity (D2); as três
    # células abaixo cruzam 'degrau' com cada um dos três blocos já
    # cobertos acima, todas recusadas por nome (D7) -- "as grades, a
    # reversa e o SOTP hoje precificam sem degrau, e misturar quebraria a
    # regra da célula central".
    ("equity", "degrau+mercado+reversa"): (_caso_equity_com_degrau_e_reversa, False),
    ("equity", "degrau+sensibilidades"): (_caso_equity_com_degrau_e_sensibilidades, False),
    ("equity", "degrau+sotp"): (_caso_equity_com_degrau_e_sotp, False),
    # Fatia 5F, Task 2 (D5): 'metrica_forward' não tem múltiplo justo forward para parear na
    # rota rampa (EV/EBITDA do ano 0) nem junto de degrau (P/VP com degrau) -- recusada no
    # gate, por nome.
    ("rampa", "metrica_forward"): (_caso_rampa_com_metrica_forward, False),
    ("equity", "degrau+metrica_forward"): (_caso_equity_com_degrau_e_metrica_forward, False),
}

assert len(MATRIZ) == 14, "a matriz tem de cobrir as 3 rotas x 3 blocos, as 3 células degrau x bloco (D7, só na rota equity) e as 2 recusas de metrica_forward (5F, D5), exatamente uma vez cada"


def _id(chave: tuple[str, str]) -> str:
    rota, bloco = chave
    return f"{rota}_x_{bloco}"


@pytest.mark.parametrize("chave", sorted(MATRIZ), ids=_id)
def test_matriz_validar_aceita_ou_recusa_nomeando_nunca_outra_excecao(chave):
    """Para toda célula da matriz, validar() só pode fazer duas coisas:
    aceitar em silêncio, ou recusar nomeando o motivo (CasoInvalido).
    Qualquer outra exceção (KeyError, TypeError, AttributeError...) aqui é
    exatamente a classe de defeito que deixou o Crítico escapar: um dict
    indexado por rota, ou um vocabulário por rota, tocado sem checar
    pertencimento antes."""
    constroi, deve_passar = MATRIZ[chave]
    caso = constroi()
    if deve_passar:
        validar(caso)  # não pode levantar nada
    else:
        with pytest.raises(CasoInvalido):
            validar(caso)


@pytest.mark.parametrize(
    "chave", sorted(k for k, (_, ok) in MATRIZ.items() if ok), ids=_id,
)
def test_matriz_avaliar_devolve_ou_recusa_nomeando_nunca_crua(chave):
    """Só para as células que PASSAM na validação (as outras nunca chegam
    a avaliar() na CLI real — `carregar` sempre valida primeiro). Roda o
    motor congelado de verdade, sem mock: avaliar() só pode devolver um
    resultado de verdade, ou levantar CasoInvalido/MotorFalhou — nunca um
    KeyError/TypeError/AttributeError cru. É este teste, não o de
    validar() acima, que teria pego a segunda metade do Crítico
    (rampa+reversa: passava o portão, batia KeyError DENTRO de
    avaliar(), depois dos cenários principais já terem rodado no motor)."""
    constroi, _ = MATRIZ[chave]
    caso = constroi()
    try:
        resultado = avaliar(caso)
    except (CasoInvalido, MotorFalhou):
        return  # recusa nomeada é resultado aceitável
    except Exception as erro:  # noqa: BLE001 -- é exatamente isto que este teste mede
        pytest.fail(
            f"{chave[0]}+{chave[1]}: avaliar() vazou {type(erro).__name__} cru "
            f"(esperado apenas um resultado ou CasoInvalido/MotorFalhou): {erro}"
        )
    assert isinstance(resultado, dict) and resultado
