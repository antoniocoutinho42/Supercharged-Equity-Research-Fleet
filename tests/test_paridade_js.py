"""Paridade Python <-> JS do espelho do nucleo (regra inviolavel 1 do desenho v4).

O espelho e a UNICA matematica de valuation em JS que o projeto admite, e o que
a torna admissivel e este arquivo. Sem node o teste PULA com razao explicita; o
CI tem node (setup-node) e sempre roda.

Tolerancia: erro RELATIVO com piso absoluto, |py - js| <= max(TAU*|py|, TAU).
As grandezas vao de multiplos (~10) a valores de equity (~1e9), entao numero
fixo de casas seria frouxo num extremo e impossivel no outro. TAU nao e
escolhido e esquecido: `test_tau_tem_folga_medida` mede o erro maximo real e
reprova se a folga encolher — limiar sem propriedade medida e constante magica.
"""
import inspect
import json
import subprocess
import sys

import pytest

from test_espelho_js import ESPELHO, FIXTURE, RAIZ, RAZAO, SEM_NODE  # FIX 7f: nao duplica

sys.path.insert(0, str(RAIZ / "skills" / "er-valuation" / "scripts"))
from vetores_paridade import avaliar_python, ev_nopat, pe  # noqa: E402

TAU = 1e-12
# FOLGA_MINIMA: quantas vezes TAU tem de estar acima do erro observado.
# MEDIDO, nao escolhido: sobre os 440 vetores da fixture o erro relativo
# maximo e 2.07e-15 (~9 ULP de um double — o ruido esperado de somar ~30
# termos com potencias), o que da folga de 482x contra TAU. O piso de 100x
# deixa espaco para variacao entre maquinas e versoes do node sem deixar de
# reprovar um colapso real. Um erro de TRANSCRICAO no espelho seria da ordem
# de 1e-3 ou maior — nove ordens de grandeza acima de TAU, nunca perto desta
# fronteira. Uma versao anterior deste plano exigia 1000x, numero que eu
# nao havia medido e que a medicao reprovou.
FOLGA_MINIMA = 100


def _vetores():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _lado_js(vetores):
    r = subprocess.run(["node", str(ESPELHO), str(FIXTURE)],
                       capture_output=True, text=True, encoding="utf-8", timeout=180)
    assert r.returncode == 0, r.stdout + r.stderr
    por_id = {x["id"]: x["valor"] for x in json.loads(r.stdout)}
    return [por_id[v["id"]] for v in vetores]


def _lado_js_adhoc(vetores, tmp_path):
    """Como `_lado_js`, mas roda o CLI sobre um arquivo TEMPORARIO com os
    vetores passados — para os casos "fora da fixture" abaixo, que nao podem
    entrar em `tests/fixtures/vetores_paridade.json` (ver o comentario antes
    de `test_tv_e_politica_tv_null_aliases_e_tv_ausente_fora_da_fixture`)."""
    arq = tmp_path / "adhoc_paridade.json"
    arq.write_text(json.dumps(vetores), encoding="utf-8")
    r = subprocess.run(["node", str(ESPELHO), str(arq)],
                       capture_output=True, text=True, encoding="utf-8", timeout=60)
    assert r.returncode == 0, r.stdout + r.stderr
    por_id = {x["id"]: x["valor"] for x in json.loads(r.stdout)}
    return [por_id[v["id"]] for v in vetores]


def _erro_relativo(p, j):
    return abs(p - j) / max(abs(p), 1.0)


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_os_dois_lados_concordam_sobre_finitude():
    """Verificado ANTES do valor: numero onde o motor da NaN e defeito grave,
    e uma comparacao numerica ingenua o esconderia."""
    vetores = _vetores()
    py, js = avaliar_python(vetores), _lado_js(vetores)
    divergentes = [(v["id"], v["fn"], v["args"], p, j)
                   for v, p, j in zip(vetores, py, js)
                   if (p is None) != (j is None)]
    assert not divergentes, (
        f"{len(divergentes)} vetores discordam sobre finitude; primeiros 3: "
        f"{divergentes[:3]}")


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_paridade_numerica_dentro_de_tau():
    vetores = _vetores()
    py, js = avaliar_python(vetores), _lado_js(vetores)
    piores = sorted(
        ((_erro_relativo(p, j), v["id"], v["fn"], v["args"], p, j)
         for v, p, j in zip(vetores, py, js) if p is not None and j is not None),
        reverse=True)
    fora = [x for x in piores if x[0] > TAU]
    assert not fora, f"{len(fora)} vetores fora de TAU={TAU}; piores 3: {fora[:3]}"


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_tau_tem_folga_medida():
    """TAU entra na suite como propriedade MEDIDA, nao como constante magica."""
    vetores = _vetores()
    py, js = avaliar_python(vetores), _lado_js(vetores)
    maximo = max((_erro_relativo(p, j)
                  for p, j in zip(py, js) if p is not None and j is not None),
                 default=0.0)
    print(f"\nerro relativo maximo observado: {maximo:.3e} (TAU={TAU:.0e}, "
          f"folga {TAU / maximo:.0f}x)" if maximo else "")
    assert maximo < TAU / FOLGA_MINIMA, (
        f"folga encolheu: maximo observado {maximo:.3e} contra TAU {TAU:.0e}. "
        "Investigue a causa antes de mexer em TAU — a tolerancia existe para "
        "absorver ordem de avaliacao em ponto flutuante, nao erro de espelho.")


# ---------------------------------------------------------------------------
# Casos "fora da fixture" (revisao final da fatia 4A — ver relatorio
# task-4a-final-fixes-report.md). `tv`/`politica_tv` explicitos como null, os
# aliases de `tv_canon` ('ic'/'spread') e `tv` ausente NAO podem entrar em
# tests/fixtures/vetores_paridade.json: tests/test_vetores_paridade.py (fora
# do escopo desta revisao) fixa o dominio de `args["tv"]` por IGUALDADE
# ESTRITA a {"book","convergencia","gordon"}
# (`test_fixture_cobre_as_tres_convencoes_terminais`) e indexa `a["tv"]` sem
# `.get()` em `test_fixture_exercita_book_com_medio_diferente_do_marginal` —
# um vetor com `tv` ausente ali estoura KeyError, e um vetor com tv
# null/alias quebra a igualdade estrita. Os dois sao testes fora da lista de
# arquivos desta tarefa; a paridade destes casos e verificada aqui, com
# vetores construidos em memoria via `_lado_js_adhoc`, sem tocar a fixture
# commitada nem o teste que a governa.
#
# `gp: null` e `n` nao-inteiro tem um motivo DIFERENTE para ficar de fora: o
# Python ESTOURA (TypeError) para os dois — nao ha valor `float | None`
# nenhum para `avaliar_python` devolver, e abrir uma excecao dentro daquela
# funcao so para estes vetores contaminaria o contrato que as outras 440
# linhas respeitam.
# ---------------------------------------------------------------------------

@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_tv_e_politica_tv_null_aliases_e_tv_ausente_fora_da_fixture(tmp_path):
    """FIX 2 + FIX 7a (revisao final). O Python so aplica os defaults de
    `tv='book'`/`politica_tv='continua'` na AUSENCIA da chave — um `None`
    explicito atravessa `**args` direto para dentro da funcao e muda o
    caminho (`tv=None` nao bate em nenhuma entrada de `tv_canon`, cai no
    ramo "senao" do terminal mas NAO no ramo `tv == 'book'` do `ret` de
    `pe` contra caixa; `politica_tv=None` nao bate em `'continua'` e se
    comporta como `'encerra'`). O espelho tinha `args.tv ?? 'book'` (idem
    gp/politica_tv): `??` trata ausencia e null presente do mesmo jeito, e o
    Python NAO trata — so ausencia usa o default. Compara os dois lados
    nestes seis vetores: `tv=None` (`ev_nopat` e `pe`, este ultimo com caixa
    != 0, onde a divergencia aparecia), `politica_tv=None` sob `gordon`, os
    aliases 'ic'/'spread' de `tv_canon`, e `tv` ausente."""
    vetores = [
        {"id": 0, "fn": "ev_nopat",
         "args": {"g": 0.04, "roic": 0.15, "w": 0.09, "n": 10, "tv": None, "roic_book": 0.12}},
        {"id": 1, "fn": "pe",
         "args": {"g": 0.05, "roe": 0.15, "ke": 0.11, "n": 10, "gde": 0.30, "nde": 0.10,
                  "tv": None, "roe_book": 0.10}},
        {"id": 2, "fn": "pe",
         "args": {"g": 0.05, "roe": 0.15, "ke": 0.10, "n": 10, "gde": 0.30, "nde": 0.10,
                  "tv": "gordon", "roe_tv": 0.09, "gp": 0.03, "politica_tv": None}},
        {"id": 3, "fn": "ev_nopat",
         "args": {"g": 0.04, "roic": 0.15, "w": 0.09, "n": 10, "tv": "ic", "roic_book": 0.12}},
        {"id": 4, "fn": "pe",
         "args": {"g": 0.05, "roe": 0.15, "ke": 0.10, "n": 10, "gde": 0.20, "nde": 0.10,
                  "tv": "spread", "roe_tv": 0.09, "gp": 0.02}},
        {"id": 5, "fn": "ev_nopat",
         "args": {"g": 0.04, "roic": 0.15, "w": 0.09, "n": 10, "roic_book": 0.12}},  # tv ausente
    ]
    py = avaliar_python(vetores)
    assert all(p is not None for p in py), (
        f"guarda disparou onde nao deveria: "
        f"{[v for v, p in zip(vetores, py) if p is None]}")
    js = _lado_js_adhoc(vetores, tmp_path)
    for v, p, j in zip(vetores, py, js):
        assert j is not None, f"js devolveu null onde python devolveu {p}: {v}"
        assert _erro_relativo(p, j) <= TAU, f"{v}: py={p} js={j}"


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_gp_none_estoura_no_python_e_o_espelho_recusa_por_nan(tmp_path):
    """FIX 2 (revisao final), a nota sobre `gp: null`. `gp <= -1` com
    `gp=None` estoura TypeError no Python — nao ha NaN para devolver, o
    guarda nunca chega a rodar. Escolha desta revisao: EXCLUIR este caso da
    fixture commitada (`avaliar_python` nao tem canal de excecao, e abrir um
    so' para este vetor contaminaria o contrato `float | None` que as outras
    440 linhas respeitam) e cobrir com este teste dedicado. Do lado JS, uma
    funcao pura nao pode propagar um TypeError do Python para quem chama do
    outro lado do processo — a convencao explicita desta revisao e que `gp`
    null recusa por NaN, a mesma linguagem de todo outro guarda deste
    arquivo."""
    with pytest.raises(TypeError):
        ev_nopat(g=0.05, roic=0.12, w=0.10, n=10, tv="gordon", roic_tv=0.10, gp=None)
    with pytest.raises(TypeError):
        pe(g=0.05, roe=0.15, ke=0.11, n=10, gde=0.20, nde=0.10, tv="gordon",
           roe_tv=0.10, gp=None)
    vetores = [
        {"id": 0, "fn": "ev_nopat",
         "args": {"g": 0.05, "roic": 0.12, "w": 0.10, "n": 10, "tv": "gordon",
                  "roic_tv": 0.10, "gp": None}},
        {"id": 1, "fn": "pe",
         "args": {"g": 0.05, "roe": 0.15, "ke": 0.11, "n": 10, "gde": 0.20, "nde": 0.10,
                  "tv": "gordon", "roe_tv": 0.10, "gp": None}},
    ]
    js = _lado_js_adhoc(vetores, tmp_path)
    assert js == [None, None], js


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_n_nao_inteiro_estoura_no_python_e_o_espelho_recusa_por_nan(tmp_path):
    """FIX 3 (revisao final). Python usa `range(1, n+1)`: `n` nao-inteiro
    estoura TypeError la (o guarda `n < 1` nao pega `n=7.5`, por exemplo), e
    o espelho, sem guarda propria, so somava um laco truncado e devolvia um
    numero silenciosamente errado. `n` e o horizonte: o input numerico de
    edicao livre mais provavel do laboratorio do item 5. Contrato explicito
    desta revisao: `Number.isInteger(n)` falso recusa por NaN, a mesma
    linguagem de todo outro guarda deste arquivo."""
    with pytest.raises(TypeError):
        ev_nopat(g=0.05, roic=0.15, w=0.09, n=7.5, tv="book", roic_book=0.10)
    with pytest.raises(TypeError):
        pe(g=0.05, roe=0.15, ke=0.09, n=7.5, gde=0.20, nde=0.10, tv="book", roe_book=0.10)
    vetores = [
        {"id": 0, "fn": "ev_nopat",
         "args": {"g": 0.05, "roic": 0.15, "w": 0.09, "n": 7.5, "tv": "book", "roic_book": 0.10}},
        {"id": 1, "fn": "pe",
         "args": {"g": 0.05, "roe": 0.15, "ke": 0.09, "n": 7.5, "gde": 0.20, "nde": 0.10,
                  "tv": "book", "roe_book": 0.10}},
    ]
    js = _lado_js_adhoc(vetores, tmp_path)
    assert js == [None, None], js


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_cobertura_da_fixture_no_harness():
    """O harness so vale se a fixture exercitar o que ele promete cobrir.

    Revisao final, FIX 5: a versao anterior so checava `len(vetores) >= 300`
    — passa mesmo se quase todos forem NaN, porque D6 exige >= 200
    FINITOS, nao >= 300 vetores. Tambem nao checava nada sobre as 3 funcoes
    x 3 convencoes terminais: uma fixture reseeded que perdesse 'gordon' por
    inteiro passaria mesmo assim. Agora as duas coisas sao diretas."""
    vetores = _vetores()
    py = avaliar_python(vetores)
    assert sum(1 for x in py if x is None) >= 20
    assert sum(1 for x in py if x is not None) >= 200, "poucos finitos: piso do D6 (>=200) nao bate"
    assert len(vetores) >= 300
    combos = {(v["fn"], v["args"]["tv"]) for v in vetores}
    esperados = {(fn, tv) for fn in ("ev_nopat", "ev_ebitda", "pe")
                 for tv in ("book", "convergencia", "gordon")}
    faltando = esperados - combos
    assert not faltando, f"combinacoes (fn, tv) ausentes da fixture: {sorted(faltando)}"


def test_ausencia_de_node_pula_com_razao_explicita():
    """Pulo silencioso e defeito: quem roda local tem de saber que nao rodou.

    Revisao final, FIX 7c: a versao anterior so checava uma propriedade da
    STRING `RAZAO` ("nao vazia e contem 'CI'") — nao podia falhar por causa
    do comportamento de pular, so por causa do texto da constante. Esta
    versao inspeciona toda funcao `test_*` deste modulo e confere que quem
    carrega `skipif` carrega exatamente `SEM_NODE`/`RAZAO` — e que a busca
    achou funcoes suficientes para a checagem nao passar vazia por
    acidente."""
    modulo = sys.modules[__name__]
    marcadas = []
    for nome, func in inspect.getmembers(modulo, inspect.isfunction):
        if not nome.startswith("test_"):
            continue
        marks = [m for m in getattr(func, "pytestmark", []) if m.name == "skipif"]
        if not marks:
            continue
        marcadas.append(nome)
        assert marks[0].args[0] is SEM_NODE, f"{nome}: skipif nao usa SEM_NODE"
        assert marks[0].kwargs.get("reason") == RAZAO, f"{nome}: skipif nao usa RAZAO"
    assert len(marcadas) >= 4, f"poucas funcoes com skipif encontradas: {marcadas}"
