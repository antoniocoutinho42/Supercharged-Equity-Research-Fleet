import json
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
FIXTURE = RAIZ / "tests" / "fixtures" / "vetores_paridade.json"
SCRIPTS = RAIZ / "skills" / "er-valuation" / "scripts"
sys.path.insert(0, str(SCRIPTS))
from vetores_paridade import avaliar_python, gerar, tv_canon  # noqa: E402


def test_gerador_e_deterministico():
    assert gerar() == gerar()


def test_fixture_commitada_reproduz_o_gerador(tmp_path):
    """A semente cumpre reprodutibilidade; a fixture commitada e revisavel."""
    destino = tmp_path / "regerado.json"
    r = subprocess.run(
        [sys.executable, str(SCRIPTS / "vetores_paridade.py"), "--out", str(destino)],
        capture_output=True, text=True, encoding="utf-8", timeout=120)
    assert r.returncode == 0, r.stdout + r.stderr
    assert destino.read_bytes() == FIXTURE.read_bytes()


def test_fixture_cobre_as_tres_funcoes():
    vetores = json.loads(FIXTURE.read_text(encoding="utf-8"))
    fns = {v["fn"] for v in vetores}
    assert fns == {"ev_nopat", "ev_ebitda", "pe"}


def test_fixture_cobre_as_tres_convencoes_terminais():
    """As tres canonicas presentes E o fechamento do dominio conhecido (F5,
    task-4b-1-review.md): o `>=` sozinho deixa um `tv` desconhecido entrar
    calado -- o motor o trataria como 'book' pelo `else` de `tv_canon`, e
    fixar comportamento nao-especificado nao e trabalho desta fixture."""
    vetores = json.loads(FIXTURE.read_text(encoding="utf-8"))
    tvs = {v["args"].get("tv") for v in vetores}
    assert {"book", "convergencia", "gordon"} <= tvs
    assert tvs <= {"book", "convergencia", "gordon", "ic", "spread", None}


def test_fixture_cobre_os_aliases_legados_de_convencao():
    """tv_canon mapeia 'ic'->'book' e 'spread'->'gordon'. Um alias transposto no
    espelho embarcaria em silencio sem estes vetores."""
    vetores = json.loads(FIXTURE.read_text(encoding="utf-8"))
    tvs = {v["args"].get("tv") for v in vetores}
    assert {"ic", "spread"} <= tvs


def test_fixture_cobre_tv_ausente():
    """Trava o VALOR do default do ramo 'else' do motor ('book') no caminho
    de resolucao por AUSENCIA de chave -- nao a distincao presenca x '??'
    (retificado pela revisao de 4B.1, task-4b-1-review.md achado F1): para
    uma chave ausente, checagem de presenca e '??' sao identicas por
    construcao -- so um `tv: null` EXPLICITO as separa, e nenhum vetor desta
    fixture usa tv null. Essa distincao para `tv` e travada FORA da fixture
    por test_paridade_js.py::test_tv_e_politica_tv_null_aliases_e_tv_
    ausente_fora_da_fixture; para `politica_tv` (mesmo padrao de default no
    Python) ela ESTA na fixture, ver
    test_fixture_cobre_politica_tv_ausente_e_null_explicito abaixo."""
    vetores = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert any("tv" not in v["args"] for v in vetores)


def test_fixture_cobre_politica_tv_ausente_e_null_explicito():
    """F2 (task-4b-1-review.md): o CRITICAL da revisao final da 4A -- o
    motor so aplica o default 'continua' de politica_tv na AUSENCIA da
    chave (assinatura de pe() no vendor); um None explicito cai no mesmo
    ramo que 'encerra' (justos.py:246) -- nao tinha vetor NENHUM na fixture,
    so um teste in-memory fora dela (test_paridade_js.py::
    test_tv_e_politica_tv_null_aliases_e_tv_ausente_fora_da_fixture)."""
    vetores = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def gordon_pe(v):
        return v["fn"] == "pe" and v["args"].get("tv") == "gordon"

    assert any(gordon_pe(v) and "politica_tv" not in v["args"] for v in vetores)
    assert any(gordon_pe(v) and "politica_tv" in v["args"] and v["args"]["politica_tv"] is None
               for v in vetores)


def test_politica_tv_ausente_e_null_discriminam_valores_no_motor():
    """A distincao acima e MATERIAL, nao decorativa: com os MESMOS
    parametros fora de politica_tv (o par que a Secao 14 do gerador
    acrescenta), ausente (default Python 'continua') e None explicito
    (mesmo ramo que 'encerra') tem que devolver valores DIFERENTES no motor
    -- e essa diferenca que um espelho resolvendo por `??` (trata os dois
    igual) apagaria."""
    base = {"g": 0.05, "roe": 0.15, "ke": 0.11, "n": 10, "gde": 0.30, "nde": 0.10,
            "tv": "gordon", "roe_tv": 0.10, "gp": 0.03}
    ausente = avaliar_python([{"id": 0, "fn": "pe", "args": dict(base)}])[0]
    nulo = avaliar_python([{"id": 1, "fn": "pe", "args": dict(base, politica_tv=None)}])[0]
    assert ausente is not None and nulo is not None, "guarda disparou onde nao deveria"
    assert ausente != nulo, "ausente e null bateram no mesmo valor -- nao discrimina"


def test_fixture_exercita_book_com_medio_diferente_do_marginal():
    """O ramo que mudou na v9.26 — um espelho com a formula antiga so erra aqui."""
    vetores = json.loads(FIXTURE.read_text(encoding="utf-8"))
    def separado(v):
        a = v["args"]
        # F4 (task-4b-1-review.md): resolve o alias ANTES de comparar --
        # senao os vetores tv="ic" (book de verdade, so o nome do alias
        # muda) escapam da contagem por comparar contra a string crua.
        if tv_canon(a.get("tv")) != "book":
            return False
        med = a.get("roic_book") if v["fn"] != "pe" else a.get("roe_book")
        marg = a.get("roic") if v["fn"] != "pe" else a.get("roe")
        return med is not None and abs(med - marg) > 1e-9
    assert sum(1 for v in vetores if separado(v)) >= 30


def test_fixture_exercita_mid_year_nos_dois_lados():
    vetores = json.loads(FIXTURE.read_text(encoding="utf-8"))
    com_mid = [v for v in vetores if v["args"].get("mid_year")]
    assert {v["fn"] for v in com_mid} >= {"ev_nopat", "pe"}


def test_fixture_tem_finitos_e_nao_finitos_em_quantidade():
    """Fixture so com casos bem-comportados nao testa os guardas."""
    vetores = json.loads(FIXTURE.read_text(encoding="utf-8"))
    r = avaliar_python(vetores)
    assert sum(1 for x in r if x is None) >= 20, "poucos nao-finitos"
    assert sum(1 for x in r if x is not None) >= 200, "poucos finitos"


def test_avaliacao_python_reproduz_as_ancoras_do_motor():
    """Ancoras conferidas contra o vendor; se mudarem, o vendor mudou."""
    casos = [
        ({"fn": "ev_nopat", "args": {"g": 0.05, "roic": 0.20, "w": 0.08, "n": 10,
                                     "tv": "book", "roic_book": 0.10}}, 12.837404750556278),
        ({"fn": "ev_nopat", "args": {"g": 0.05, "roic": 0.20, "w": 0.08, "n": 10,
                                     "tv": "book", "roic_book": 0.20}}, 10.405638938111686),
        ({"fn": "pe", "args": {"g": 0.05, "roe": 0.20, "ke": 0.12, "n": 10,
                               "gde": 0.30, "nde": 0.10, "tv": "book",
                               "roe_book": 0.10}}, 9.79359664180879),
        ({"fn": "ev_nopat", "args": {"g": 0.05, "roic": 0.12, "w": 0.10, "n": 10,
                                     "tv": "gordon", "roic_tv": 0.10, "gp": 0.03,
                                     "mid_year": True}}, 11.69525022672858),
    ]
    obtido = avaliar_python([dict(c[0], id=i) for i, c in enumerate(casos)])
    for (_, esperado), got in zip(casos, obtido):
        assert got == esperado


def test_caixa_nao_move_o_book_equity_mas_move_o_gordon():
    """Invariancia da v9.30, checada no lado Python antes de exigi-la do espelho."""
    def um(args):
        return avaliar_python([{"id": 0, "fn": "pe", "args": args}])[0]
    base = {"g": 0.05, "roe": 0.20, "ke": 0.12, "n": 10, "tv": "book", "roe_book": 0.10}
    sem = um(dict(base, gde=0.0, nde=0.0))
    com = um(dict(base, gde=0.60, nde=0.10))
    assert sem == com
    g_base = {"g": 0.08, "roe": 0.18, "ke": 0.14, "n": 10, "tv": "gordon",
              "roe_tv": 0.12, "gp": 0.03}
    assert um(dict(g_base, gde=0.0, nde=0.0)) != um(dict(g_base, gde=0.30, nde=0.10))
