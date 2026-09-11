"""Paridade do WRAPPER: alvo de mercado, eixo de reversa e grades.

Natureza diferente da paridade do solver: aqui o lado Python NAO e o motor
congelado, e sim `reversa.py`/`sensibilidades.py`. Um espelho fiel ao motor e
infiel ao wrapper produziria numeros certos no lugar errado — por isso os dois
harnesses sao arquivos separados.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
ESPELHO = RAIZ / "skills" / "er-valuation" / "assets" / "motor_espelho.js"
FIXTURE = RAIZ / "tests" / "fixtures" / "vetores_solver.json"
sys.path.insert(0, str(RAIZ / "skills" / "er-valuation" / "scripts"))
from vetores_solver import avaliar_python  # noqa: E402

TAU = 1e-12
SEM_NODE = shutil.which("node") is None
RAZAO = "node ausente do PATH — a paridade roda sempre no CI (setup-node)"


def _problemas(tipos):
    todos = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return [p for p in todos if p.get("tipo") in tipos]


def _lado_js():
    r = subprocess.run(["node", str(ESPELHO), str(FIXTURE)],
                       capture_output=True, text=True, encoding="utf-8", timeout=300)
    assert r.returncode == 0, r.stdout + r.stderr
    return {x["id"]: x for x in json.loads(r.stdout)}


def _rel(a, b):
    return abs(a - b) / max(abs(a), 1.0)


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_alvo_de_mercado_bate_nas_duas_rotas():
    probs = _problemas({"alvo"})
    assert probs, "fixture sem problemas de alvo"
    py, js = avaliar_python(probs), _lado_js()
    fora = [(p["id"], p["args"]["rota"], a["alvo"], js[p["id"]]["alvo"])
            for p, a in zip(probs, py) if _rel(a["alvo"], js[p["id"]]["alvo"]) > TAU]
    assert not fora, f"alvo divergente: {fora[:3]}"
    assert {p["args"]["rota"] for p in probs} >= {"firm", "equity"}
    assert any(p["args"].get("nd_efetivo", 0) < 0 for p in probs), "nenhum caso com caixa liquido"


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_grades_tem_a_orientacao_do_wrapper():
    """Grade NAO quadrada de proposito: a fatia 3C descobriu que uma 3x3
    esconde uma transposicao de eixos — o teste passava com os eixos trocados."""
    probs = _problemas({"grade2d"})
    assert probs, "fixture sem grades 2D"
    js = _lado_js()
    nao_quadradas = [p for p in probs
                     if len(p["args"]["pontos_x"]) != len(p["args"]["pontos_y"])]
    assert nao_quadradas, "toda grade 2D e quadrada — transposicao ficaria invisivel"
    for p in nao_quadradas:
        g = js[p["id"]]
        px, py_ = p["args"]["pontos_x"], p["args"]["pontos_y"]
        assert len(g["celulas"]) == len(py_)
        assert all(len(linha) == len(px) for linha in g["celulas"])
        for i, linha in enumerate(g["celulas"]):
            for j, cel in enumerate(linha):
                assert cel["x"] == px[j] and cel["y"] == py_[i]


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_valor_e_multiplo_de_cada_celula_dentro_de_tau():
    probs = _problemas({"grade1d", "grade2d"})
    assert probs, "fixture sem grades"
    py, js = avaliar_python(probs), _lado_js()
    piores = []
    for p, a in zip(probs, py):
        b = js[p["id"]]
        cel_py = a["celulas"] if p["tipo"] == "grade1d" else [c for lin in a["celulas"] for c in lin]
        cel_js = b["celulas"] if p["tipo"] == "grade1d" else [c for lin in b["celulas"] for c in lin]
        assert len(cel_py) == len(cel_js), f"contagem de celulas difere no problema {p['id']}"
        for cp, cj in zip(cel_py, cel_js):
            for campo in ("valor", "multiplo"):
                if cp[campo] is None or cj[campo] is None:
                    assert (cp[campo] is None) == (cj[campo] is None), (p["id"], campo)
                    continue
                piores.append((_rel(cp[campo], cj[campo]), p["id"], campo, cp[campo], cj[campo]))
    piores.sort(reverse=True)
    fora = [x for x in piores if x[0] > TAU]
    assert not fora, f"{len(fora)} celulas fora de TAU; piores 3: {fora[:3]}"


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_celula_central_reproduz_o_caso_base():
    """Regra da metodologia: a celula na premissa do caso-base bate com a manchete."""
    probs = _problemas({"grade1d"})
    py, js = avaliar_python(probs), _lado_js()
    checados = 0
    for p, a in zip(probs, py):
        central = p["args"]["premissas"].get(p["args"]["premissa"])
        if central is None or central not in p["args"]["pontos"]:
            continue
        k = p["args"]["pontos"].index(central)
        assert _rel(a["celulas"][k]["valor"], js[p["id"]]["celulas"][k]["valor"]) <= TAU
        checados += 1
    assert checados >= 1, "nenhuma grade inclui o ponto central — a regra nao foi exercitada"


# ---------------------------------------------------------------------------
# Rota RAMPA (item 4, fatia C, task 1). Mesmo harness, mesma fixture — a paridade e' contra o
# WRAPPER (avaliar.precificar_rampa), nao contra o motor direto: ver o comentario no topo deste
# arquivo e o cabecalho da secao RAMPA em motor_espelho.js.
# ---------------------------------------------------------------------------

CAMPOS_RAMPA = ("g1_%", "d_trajetoria_fase1_%", "d2_fase2_%", "rir_fase1_%", "alfa", "beta",
                "rir2_%", "roic2_%", "vp_fase1", "valor_fase2_no_ano_T", "capacidade_receita")


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_rampa_recusa_onde_o_motor_recusa():
    probs = _problemas({"rampa"})
    assert probs, "fixture sem problemas de rampa"
    py, js = avaliar_python(probs), _lado_js()
    fora = [(p["id"], a["recusado"], js[p["id"]]["recusado"])
            for p, a in zip(probs, py) if a["recusado"] != js[p["id"]]["recusado"]]
    assert not fora, f"recusa divergente (id, py, js): {fora}"


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_rampa_bate_campo_a_campo():
    """O que o motor arredonda compara EXATAMENTE — o arredondamento e contrato."""
    probs = _problemas({"rampa"})
    py, js = avaliar_python(probs), _lado_js()
    fora = []
    for p, a in zip(probs, py):
        if a["recusado"]:
            continue
        b = js[p["id"]]
        for campo in ("multiplo", "valor", "saida", "avisos"):
            if a[campo] != b[campo]:
                fora.append((p["id"], campo, a[campo], b[campo]))
    assert not fora, f"{len(fora)} divergencias; primeiras 3: {fora[:3]}"


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_fixture_de_rampa_cobre_o_que_discrimina():
    probs = _problemas({"rampa"})
    py = avaliar_python(probs)
    ok = [a for a in py if not a["recusado"]]
    assert sum(a["recusado"] for a in py) >= 4, "poucas recusas de dominio"
    assert any("capacidade_receita" in a["saida"] for a in ok), "g1 derivado de util nunca exercitado"
    assert any("aviso_colheita" in a["avisos"] for a in ok), "colheita nunca exercitada"
    assert any("aviso_delator" in a["avisos"] for a in ok), "rir2 >= 100% nunca exercitado"
    assert any(isinstance(a["saida"]["roic2_%"], str) for a in ok), "capital incremental zero nunca exercitado"
    assert any("Equity" not in a["valor"] for a in ok), "rampa sem ponte nunca exercitada"
    assert {p["args"]["premissas"]["tv"] for p in probs} >= {"book", "convergencia", "gordon"}
    # [item 4, fatia C, task 2] aviso_gp: cobre disparo (tv='gordon'/'spread' com gp>rf) e
    # nao-disparo genuino (tv nao-gordon, ex. 'ic', com o MESMO gp>rf) — ver os problemas
    # N/O/P em _bloco_rampa (vetores_solver.py) e o achado sobre o alias 'spread' registrado la'
    # e no relatorio desta task.
    assert any("aviso_gp" in a["avisos"] for a in ok), "aviso_gp nunca exercitado"
    assert {p["args"]["premissas"]["tv"] for p in probs
            if p["args"].get("rf") is not None and p["args"]["premissas"].get("gp", 0) > 0} >= {
        "gordon", "spread", "ic"}, "faltam as tres convencoes na fronteira de aviso_gp (gordon/spread disparam, ic nao)"


# ---------------------------------------------------------------------------
# Predicados de diagnostico (item 4, fatia C, task 2). Mesmo harness, mesma fixture — paridade
# contra o WRAPPER (`motor.rodar`, nunca diag_firm/diag_eq direto). `diagnosticos_chaves.json` e'
# o vocabulario que classifica cada mensagem do motor pelo PREFIXO; ver o comentario no topo de
# `diagnosticosFirm`/`diagnosticosEquity` (motor_espelho.js) e de `_bloco_diag`
# (vetores_solver.py) para o porque de so' UMA chave de `coerencia_vetor` ser alcancavel (rota
# firm) e NENHUMA na rota equity.
# ---------------------------------------------------------------------------

CHAVES = json.loads((RAIZ / "skills" / "er-valuation" / "assets" / "diagnosticos_chaves.json")
                    .read_text(encoding="utf-8"))


def _classificar(msg):
    return [c["chave"] for c in CHAVES if msg.startswith(c["prefixo"])]


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_toda_mensagem_do_motor_casa_com_exatamente_uma_chave():
    """Tripwire da troca de vendor: mensagem nova ou prefixo ambiguo reprova AQUI, nomeando a
    mensagem, antes de o laboratorio mostrar um diagnostico sem chave."""
    probs = _problemas({"diag"})
    assert probs, "fixture sem problemas de diagnostico"
    py = avaliar_python(probs)
    ruins = [(p["id"], m[:80], _classificar(m)) for p, a in zip(probs, py)
             for m in a["mensagens"] if len(_classificar(m)) != 1]
    assert not ruins, f"{len(ruins)} mensagens sem chave unica; primeiras 3: {ruins[:3]}"


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_chaves_de_diagnostico_batem_em_ordem():
    """O diagnostico se move junto com o numero (desenho, 8.4): QUAIS disparam e em que
    ordem tem de bater exatamente — chave a mais ou a menos e alerta errado na tela."""
    probs = _problemas({"diag"})
    py, js = avaliar_python(probs), _lado_js()
    fora = []
    for p, a in zip(probs, py):
        esperado = [_classificar(m)[0] for m in a["mensagens"]]
        if esperado != js[p["id"]]["chaves"]:
            fora.append((p["id"], p["args"]["rota"], esperado, js[p["id"]]["chaves"]))
    assert not fora, f"{len(fora)} divergencias; primeiras 2: {fora[:2]}"


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_fixture_de_diagnostico_cobre_os_alertas():
    py = avaliar_python(_problemas({"diag"}))
    disparadas = {_classificar(m)[0] for a in py for m in a["mensagens"]}
    alertas = {c["chave"] for c in CHAVES
               if c["prefixo"].startswith(("ALERTA", "SUB-ALERTA", "INCOERÊNCIA", "DOMÍNIO"))}
    assert alertas <= disparadas, f"alertas nunca exercitados: {sorted(alertas - disparadas)}"


# ---------------------------------------------------------------------------
# DEGRAU (Fatia D, Task 2). Mesmo harness, mesma fixture — a paridade e' contra o WRAPPER
# (avaliar.avaliar sobre um caso mínimo com bloco 'degrau'), nao contra o motor direto: ver o
# comentario no topo deste arquivo e o cabecalho da secao DEGRAU em motor_espelho.js.
# ---------------------------------------------------------------------------

# Campos de `degrau` comparados por IGUALDADE EXATA — todos arredondados pelo motor (`round`),
# exceto ALERTA/ALERTA_RiR, que comparam por PRESENCA (True/ausente: `.get(campo)` devolve `None`
# dos dois lados quando a chave nao existe) — nunca a prosa do motor, mesma convencao de
# `avisos`/AVISOS_RAMPA acima. `divergencia_de_base_%` fica DE FORA desta lista de propósito: nao
# e' arredondada pelo wrapper (D8) — compara por TAU em teste separado, abaixo.
CAMPOS_DEGRAU_EXATOS = ("h", "rentabilidade_pos_%", "multiplo", "multiplo_x_rentab",
                        "com_transicao", "fator_transicao", "perfil_transicao", "m",
                        "ALERTA", "ALERTA_RiR")


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_degrau_recusa_onde_o_motor_recusa():
    probs = _problemas({"degrau"})
    assert probs, "fixture sem problemas de degrau"
    py, js = avaliar_python(probs), _lado_js()
    fora = [(p["id"], a["recusado"], js[p["id"]]["recusado"])
            for p, a in zip(probs, py) if a["recusado"] != js[p["id"]]["recusado"]]
    assert not fora, f"recusa divergente (id, py, js): {fora}"


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_degrau_bate_campo_a_campo():
    """O que o motor arredonda compara EXATAMENTE — o arredondamento e' contrato (mesma disciplina
    de test_rampa_bate_campo_a_campo, acima). `valor`/`sem_degrau` sao dicts com todo campo
    arredondado; `degrau` compara campo a campo via CAMPOS_DEGRAU_EXATOS."""
    probs = _problemas({"degrau"})
    py, js = avaliar_python(probs), _lado_js()
    fora = []
    for p, a in zip(probs, py):
        if a["recusado"]:
            continue
        b = js[p["id"]]
        for campo in ("valor", "sem_degrau"):
            if a[campo] != b[campo]:
                fora.append((p["id"], campo, a[campo], b[campo]))
        da, db = a["degrau"], b["degrau"]
        for campo in CAMPOS_DEGRAU_EXATOS:
            if da.get(campo) != db.get(campo):
                fora.append((p["id"], f"degrau.{campo}", da.get(campo), db.get(campo)))
    assert not fora, f"{len(fora)} divergencias; primeiras 3: {fora[:3]}"


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_degrau_divergencia_e_upside_dentro_de_tau():
    """`divergencia_de_base_%` (D8) e `vs_preco.upside` NAO sao arredondados pelo wrapper —
    comparados por TAU, como as outras contas encadeadas fora do motor neste harness (ex.:
    test_alvo_de_mercado_bate_nas_duas_rotas, acima), nao por igualdade exata."""
    probs = _problemas({"degrau"})
    py, js = avaliar_python(probs), _lado_js()
    piores = []
    for p, a in zip(probs, py):
        if a["recusado"]:
            continue
        b = js[p["id"]]
        piores.append((_rel(a["degrau"]["divergencia_de_base_%"], b["degrau"]["divergencia_de_base_%"]),
                       p["id"], "divergencia_de_base_%"))
        piores.append((_rel(a["vs_preco"]["upside"], b["vs_preco"]["upside"]), p["id"], "upside"))
    piores.sort(reverse=True)
    fora = [x for x in piores if x[0] > TAU]
    assert not fora, f"{len(fora)} fora de TAU; piores 3: {fora[:3]}"


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_fixture_de_degrau_cobre_o_que_discrimina():
    probs = _problemas({"degrau"})
    py = avaliar_python(probs)
    ok = [a for a in py if not a["recusado"]]
    assert sum(a["recusado"] for a in py) >= 1, "nenhuma recusa de dominio"
    assert any(a["degrau"]["h"] == pytest.approx(1.0) for a in ok), "h=1 nunca exercitado"
    assert {a["degrau"]["m"] for a in ok} >= {0.0, 70.0, 130.0}, "faltam variacoes de m"
    assert any(p["args"]["bloco_degrau"]["anos"] % 1 != 0 for p in probs), "anos fracionario nunca exercitado"
    assert any(a["degrau"]["perfil_transicao"] == "pontual" for a in ok), "perfil pontual nunca exercitado"
    assert any(p["args"]["premissas"].get("tv") == "book"
              and p["args"]["premissas"].get("roe_book") is not None
              for p in probs), "tv=book com roe_book nunca exercitado"
    assert any("ALERTA" in a["degrau"] for a in ok), "ALERTA nunca exercitado"
    assert any("ALERTA_RiR" in a["degrau"] for a in ok), "ALERTA_RiR nunca exercitado"

    # h=1 nao inventa valor sem capacidade ociosa real (test_2, tests/test_valuation_degrau.py) —
    # sanidade da fixture: confirma que o problema de h=1 exibe a MESMA identidade que a Task 1 já
    # discrimina no wrapper, agora tambem visível nesta paridade JS via test_degrau_bate_campo_a_campo.
    h1 = next(a for a in ok if a["degrau"]["h"] == pytest.approx(1.0))
    assert h1["degrau"]["com_transicao"] == pytest.approx(h1["degrau"]["multiplo_x_rentab"])
    assert h1["degrau"]["multiplo"] == pytest.approx(h1["sem_degrau"]["multiplos"]["PL_curr"])
