"""Paridade do WRAPPER: alvo de mercado, eixo de reversa e grades.

Natureza diferente da paridade do solver: aqui o lado Python NAO e o motor
congelado, e sim `reversa.py`/`sensibilidades.py`. Um espelho fiel ao motor e
infiel ao wrapper produziria numeros certos no lugar errado — por isso os dois
harnesses sao arquivos separados.
"""
import functools
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
import diagnosticos  # noqa: E402
from avaliar import (_CHAVE_DIVERGENCIA_DE_BASE, _CHAVES_DA_CONSERVACAO,  # noqa: E402
                     _CHAVES_DO_DEGRAU_ORDEM, _LIMIAR_DIVERGENCIA_DE_BASE_PCT)
from vetores_solver import CAMPOS_CONSERVACAO, avaliar_python  # noqa: E402

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

# A classificação em si (mensagem -> chave, por prefixo) foi promovida para
# `diagnosticos.classificar` (fatia 5A, item 5, Task 1, decisão A5) — uma
# fonte só, também usada por `avaliar.py`/`sensibilidades.py` para publicar
# `diagnosticos_chaves`/`diagnosticos_unicos_chaves` em `resultados.json`.
# `CHAVES` (a lista bruta {chave, prefixo}) continua aqui: este arquivo
# ainda precisa do `prefixo` de cada entrada para filtrar "alertas", algo
# que `diagnosticos.CHAVES` (só os nomes) não carrega.


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_toda_mensagem_do_motor_casa_com_exatamente_uma_chave():
    """Tripwire da troca de vendor: mensagem nova ou prefixo ambiguo reprova AQUI, nomeando a
    mensagem, antes de o laboratorio mostrar um diagnostico sem chave."""
    probs = _problemas({"diag"})
    assert probs, "fixture sem problemas de diagnostico"
    py = avaliar_python(probs)
    ruins = [(p["id"], m[:80]) for p, a in zip(probs, py)
             for m in a["mensagens"] if diagnosticos.classificar(m) is None]
    assert not ruins, f"{len(ruins)} mensagens sem chave unica; primeiras 3: {ruins[:3]}"


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_chaves_de_diagnostico_batem_em_ordem():
    """O diagnostico se move junto com o numero (desenho, 8.4): QUAIS disparam e em que
    ordem tem de bater exatamente — chave a mais ou a menos e alerta errado na tela."""
    probs = _problemas({"diag"})
    py, js = avaliar_python(probs), _lado_js()
    fora = []
    for p, a in zip(probs, py):
        esperado = [diagnosticos.classificar(m) for m in a["mensagens"]]
        if esperado != js[p["id"]]["chaves"]:
            fora.append((p["id"], p["args"]["rota"], esperado, js[p["id"]]["chaves"]))
    assert not fora, f"{len(fora)} divergencias; primeiras 2: {fora[:2]}"


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_fixture_de_diagnostico_cobre_os_alertas():
    py = avaliar_python(_problemas({"diag"}))
    disparadas = {diagnosticos.classificar(m) for a in py for m in a["mensagens"]}
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
# Fatia 5C, Task 3 (T3): `diagnosticos_chaves` — as chaves que o wrapper passou a dar aos dois
# alertas, na ordem de `_ALERTAS_DEGRAU_ORDEM` — tambem por igualdade exata: a MESMA lista, na
# MESMA ordem, dos dois lados (a presenca de ALERTA/ALERTA_RiR sozinha nao prende o nome da chave).
CAMPOS_DEGRAU_EXATOS = ("h", "rentabilidade_pos_%", "multiplo", "multiplo_x_rentab",
                        "com_transicao", "fator_transicao", "perfil_transicao", "m",
                        "ALERTA", "ALERTA_RiR", "diagnosticos_chaves")


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
    # Fatia 5C, Task 3: toda chave que o wrapper publica em `degrau.diagnosticos_chaves` aparece em
    # pelo menos um problema — sem isto, a igualdade da lista em test_degrau_bate_campo_a_campo
    # poderia estar comparando so' listas vazias. Desde a onda de correcao da revisao final (F1),
    # o vocabulario inclui a chave da divergencia de base, derivado da constante do wrapper.
    vistas = {chave for a in ok for chave in (a["degrau"]["diagnosticos_chaves"] or [])}
    assert vistas == set(_CHAVES_DO_DEGRAU_ORDEM), vistas
    # F1: a chave da divergencia de base so' prende o LIMIAR se a fixture tiver os dois lados dele —
    # um problema com a divergencia dentro do limiar (chave apagada) e divergencias acima dele nos
    # DOIS sinais (a regra e' sobre o modulo: um espelho sem o `abs` so' reprova com uma negativa).
    assert any(abs(a["degrau"]["divergencia_de_base_%"]) <= _LIMIAR_DIVERGENCIA_DE_BASE_PCT
               for a in ok), "nenhuma divergencia de base dentro do limiar — o limiar nao e' discriminado"
    assert any(a["degrau"]["divergencia_de_base_%"] > _LIMIAR_DIVERGENCIA_DE_BASE_PCT for a in ok), \
        "nenhuma divergencia positiva acima do limiar"
    assert any(a["degrau"]["divergencia_de_base_%"] < -_LIMIAR_DIVERGENCIA_DE_BASE_PCT for a in ok), \
        "nenhuma divergencia negativa acima do limiar — o modulo da regra nao e' discriminado"

    # F1, a REGRA no lado Python, problema a problema: a chave acende se e so' se o modulo da
    # divergencia publicada passa do limiar do wrapper. O lado JS nao precisa de checagem propria:
    # test_degrau_bate_campo_a_campo exige a MESMA lista, na mesma ordem, dos dois lados.
    fora_da_regra = [
        (a["degrau"]["divergencia_de_base_%"], a["degrau"]["diagnosticos_chaves"]) for a in ok
        if (abs(a["degrau"]["divergencia_de_base_%"]) > _LIMIAR_DIVERGENCIA_DE_BASE_PCT)
        != (_CHAVE_DIVERGENCIA_DE_BASE in a["degrau"]["diagnosticos_chaves"])]
    assert not fora_da_regra, fora_da_regra

    # h=1 nao inventa valor sem capacidade ociosa real (test_2, tests/test_valuation_degrau.py) —
    # sanidade da fixture: confirma que o problema de h=1 exibe a MESMA identidade que a Task 1 já
    # discrimina no wrapper, agora tambem visível nesta paridade JS via test_degrau_bate_campo_a_campo.
    h1 = next(a for a in ok if a["degrau"]["h"] == pytest.approx(1.0))
    assert h1["degrau"]["com_transicao"] == pytest.approx(h1["degrau"]["multiplo_x_rentab"])
    assert h1["degrau"]["multiplo"] == pytest.approx(h1["sem_degrau"]["multiplos"]["PL_curr"])


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_o_limiar_e_a_chave_da_divergencia_de_base_do_espelho_sao_os_do_wrapper():
    """Onda de correcao da revisao final da 5C (F1): a decisao "divergencia de base acima do
    limiar" passou a ser da integracao, e tem UMA fonte numerica — `avaliar.
    _LIMIAR_DIVERGENCIA_DE_BASE_PCT`. O espelho carrega uma copia (o navegador nao le Python), e
    a copia e' travada aqui por IGUALDADE contra a fonte, junto com a chave que ela acende. A
    paridade campo a campo prende o comportamento so' onde a fixture tem problema dos dois lados
    do limiar; esta igualdade prende o numero inteiro, qualquer que seja a fixture."""
    script = ("const M = require(%s);"
              "console.log(JSON.stringify({limiar: M.LIMIAR_DIVERGENCIA_DE_BASE_PCT,"
              " chave: M.CHAVE_DIVERGENCIA_DE_BASE}));") % json.dumps(str(ESPELHO))
    r = subprocess.run(["node", "-e", script], capture_output=True, text=True, encoding="utf-8",
                       timeout=120)
    assert r.returncode == 0, r.stdout + r.stderr
    assert json.loads(r.stdout) == {"limiar": _LIMIAR_DIVERGENCIA_DE_BASE_PCT,
                                    "chave": _CHAVE_DIVERGENCIA_DE_BASE}


# ---------------------------------------------------------------------------
# CONSERVACAO DE CAPITAL (fatia 5F, Task 3). Mesmo harness, mesma fixture — a paridade e' contra o
# WRAPPER (`avaliar.precificar_firm` com as flags, e o bloco que `avaliar()` publica), nao contra
# `conservacao_capital` importada direto: o numero que a fachada compara no browser e' o que
# atravessou a CLI do motor. Os cinco numeros sao arredondados pelo motor e comparam EXATAMENTE;
# ALERTA por presenca; `diagnosticos_chaves` pela lista.
# ---------------------------------------------------------------------------

@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_conservacao_de_capital_bate_campo_a_campo_nos_dois_lados_do_limiar():
    probs = _problemas({"conservacao"})
    assert probs, "fixture sem problemas de conservacao de capital"
    py, js = avaliar_python(probs), _lado_js()
    campos = CAMPOS_CONSERVACAO + ("ALERTA", "diagnosticos_chaves")
    fora = [(p["id"], campo, a["conservacao"].get(campo), js[p["id"]]["conservacao"].get(campo))
            for p, a in zip(probs, py) for campo in campos
            if a["conservacao"].get(campo) != js[p["id"]]["conservacao"].get(campo)]
    assert not fora, f"{len(fora)} divergencias; primeiras 3: {fora[:3]}"
    # O limiar do motor (10%) so' fica preso se a fixture tiver o gap perto dele dos dois lados e nos
    # dois sinais: um limiar diferente no espelho, ou um sem o modulo, reprova acima.
    gaps = [(a["conservacao"]["gap_%"], bool(a["conservacao"]["diagnosticos_chaves"])) for a in py]
    assert any(5 < abs(gap) <= 10 and not acesa for gap, acesa in gaps), gaps
    assert any(10 < gap < 20 and acesa for gap, acesa in gaps), gaps
    assert any(-20 < gap < -10 and acesa for gap, acesa in gaps), gaps
    assert {chave for a in py for chave in a["conservacao"]["diagnosticos_chaves"]} == set(_CHAVES_DA_CONSERVACAO)


# ---------------------------------------------------------------------------
# REVERSA (item 5, fatia I, task 1). O lado Python e `reversa.reverter` de verdade
# — o WRAPPER inteiro, um caso minimo por problema. Comparamos o que a aba le desde
# a 5F: `leitura` + `resolucao` por eixo, `limitacoes` e o teto.
#
# D4 do plano desta fatia, MEDIDO antes de o comparador ser escrito (relatorio do
# lote): `curvatura_d2M_dx2` sai do comparador NOMEADAMENTE, e so' ela. A razao e'
# estrutural, nao de tolerancia: `identificacao` divide a segunda diferenca por
# `h**2`, e h = max(|x|,1e-4)*1e-4 vale 1e-8 numa raiz perto de zero — /1e-16. UM
# ULP de diferenca numa das tres avaliacoes vizinhas (as outras duas bit-a-bit
# IGUAIS) vira dezenas de unidades na curvatura: medido no primeiro problema de
# reversa, eixo 'crescimento', Python 266,45 x JS 230,93, com mp e mm identicos e
# so' m0 distante 1 ULP. Nenhum espelho fiel evita isso, e um badge vermelho num
# caso legitimo TRAVA o laboratorio inteiro (laboratorio.js:394-416). A curvatura
# continua PUBLICADA nos dois lados — e' leitura, nao decisao —, e
# `test_a_curvatura_continua_publicada_dos_dois_lados` prende isso.
# ---------------------------------------------------------------------------

CURVATURA_FORA_DO_COMPARADOR = "curvatura"

EIXOS_PERCENTUAIS = ("custo_capital", "crescimento", "rentabilidade")


@functools.lru_cache(maxsize=1)
def _py_reversa():
    """`avaliar_python` dos problemas de reversa, uma vez por sessao: cada problema
    roda o motor por SUBPROCESSO uma vez por eixo declarado, mais duas (o multiplo
    justo corrente e o nivel implicito). Sem o cache, cada teste desta secao pagaria
    a conta inteira de novo."""
    probs = _problemas({"reversa"})
    return probs, avaliar_python(probs)


def _diferencas(python, js, caminho=""):
    """Diferencas estruturais entre os dois lados, por igualdade EXATA — o
    arredondamento do motor e contrato (mesma disciplina de
    `test_rampa_bate_campo_a_campo`). `curvatura` e pulada PELO NOME, e so' ela (D4)."""
    if isinstance(python, dict) and isinstance(js, dict):
        fora = []
        for chave in set(python) | set(js):
            if chave == CURVATURA_FORA_DO_COMPARADOR:
                continue
            if chave not in python or chave not in js:
                fora.append((f"{caminho}/{chave}", python.get(chave, "<ausente>"),
                             js.get(chave, "<ausente>")))
                continue
            fora += _diferencas(python[chave], js[chave], f"{caminho}/{chave}")
        return fora
    if isinstance(python, list) and isinstance(js, list):
        if len(python) != len(js):
            return [(f"{caminho} (comprimento)", len(python), len(js))]
        return [d for i, (a, b) in enumerate(zip(python, js))
                for d in _diferencas(a, b, f"{caminho}[{i}]")]
    return [] if python == js else [(caminho, python, js)]


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_reversa_por_eixo_bate_com_o_wrapper():
    """Contagem de raizes e de tangenciais EXATA ANTES de qualquer numero — a
    divergencia DISCRETA (uma raiz a mais ou a menos) e a que uma comparacao de
    valor nao pega, a licao de `test_paridade_solver_js.py`."""
    probs, py = _py_reversa()
    assert probs, "fixture sem problemas de reversa"
    js = _lado_js()

    contagens = []
    for p, a in zip(probs, py):
        if a["recusa_da_cli"]:
            continue
        b = js[p["id"]]
        for eixo in EIXOS_PERCENTUAIS:
            if eixo not in a["eixos"]:
                continue
            la, lb = a["eixos"][eixo]["leitura"], b["eixos"][eixo]["leitura"]
            if len(la["raizes"]) != len(lb["raizes"]):
                contagens.append((p["id"], eixo, "raizes", len(la["raizes"]), len(lb["raizes"])))
            if len(la["tangenciais"]) != len(lb["tangenciais"]):
                contagens.append((p["id"], eixo, "tangenciais",
                                  len(la["tangenciais"]), len(lb["tangenciais"])))
    assert not contagens, f"contagem divergente (id, eixo, campo, py, js): {contagens}"

    fora = []
    for p, a in zip(probs, py):
        if a["recusa_da_cli"]:
            continue
        b = js[p["id"]]
        fora += _diferencas(a["alvo"], b["alvo"], f"id{p['id']}/alvo")
        fora += _diferencas(a["limitacoes"], b["limitacoes"], f"id{p['id']}/limitacoes")
        for eixo in EIXOS_PERCENTUAIS:
            if eixo not in a["eixos"]:
                continue
            fora += _diferencas(a["eixos"][eixo], b["eixos"][eixo], f"id{p['id']}/{eixo}")
    assert not fora, f"{len(fora)} divergencias; primeiras 3: {fora[:3]}"


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_cap_implicito_bate_com_o_wrapper():
    """As QUATRO saidas do eixo 'cap', incluindo as duas SEM numero
    (`cap_indefinido`, `cap_fora_da_faixa`): o espelho decide o codigo pelo mesmo
    predicado que escolhe as duas frases verbatim do vendor (D3), e nunca monta a
    frase."""
    probs, py = _py_reversa()
    js = _lado_js()
    fora, motivos = [], set()
    for p, a in zip(probs, py):
        if a["recusa_da_cli"] or "cap" not in a["eixos"]:
            continue
        motivos.add(a["eixos"]["cap"]["leitura"]["motivo"])
        fora += _diferencas(a["eixos"]["cap"], js[p["id"]]["eixos"]["cap"], f"id{p['id']}/cap")
    assert not fora, f"{len(fora)} divergencias; primeiras 3: {fora[:3]}"
    assert motivos == {"cap_na_faixa", "cap_na_faixa_decrescente",
                       "cap_fora_da_faixa", "cap_indefinido"}, motivos


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_teto_do_crescimento_gratuito_bate_com_o_wrapper():
    """O teto so' existe quando um eixo PRIMARIO nao fecha — e' o mesmo gatilho da
    limitacao `iso_nao_calculada`. Presenca e conteudo, nos dois lados."""
    probs, py = _py_reversa()
    js = _lado_js()
    fora, com_teto = [], 0
    for p, a in zip(probs, py):
        if a["recusa_da_cli"]:
            continue
        b = js[p["id"]]
        tem_py = "teto_do_crescimento_gratuito" in a
        assert tem_py == ("teto_do_crescimento_gratuito" in b), (p["id"], tem_py)
        if not tem_py:
            continue
        com_teto += 1
        assert a["limitacoes"] == ["iso_nao_calculada"], (p["id"], a["limitacoes"])
        fora += _diferencas(a["teto_do_crescimento_gratuito"],
                            b["teto_do_crescimento_gratuito"], f"id{p['id']}/teto")
    assert com_teto >= 1, "nenhum problema aciona o teto — o gatilho nao foi exercitado"
    assert not fora, f"{len(fora)} divergencias; primeiras 3: {fora[:3]}"


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_a_curvatura_continua_publicada_dos_dois_lados():
    """D4: a curvatura sai do COMPARADOR — e, desde o ajuste do lote 2 da 5I, tambem da
    TELA (o relatorio nao a pinta) —, mas continua no CONTRATO: a leitura a publica dos
    dois lados, nas mesmas chaves do `resultados.json` (L2). Um espelho que a omitisse
    quebraria o shape sem que o badge percebesse, porque ela esta fora do comparador.
    Prende tambem o caso que JUSTIFICA a excecao: sem ele, a excecao nomeada estaria
    protegendo o que nao precisa."""
    probs, py = _py_reversa()
    js = _lado_js()
    publicadas, divergentes = 0, 0
    for p, a in zip(probs, py):
        if a["recusa_da_cli"]:
            continue
        for eixo in EIXOS_PERCENTUAIS:
            if eixo not in a["eixos"]:
                continue
            ra = a["eixos"][eixo]["leitura"]["raizes"]
            rb = js[p["id"]]["eixos"][eixo]["leitura"]["raizes"]
            for xa, xb in zip(ra, rb):
                assert "curvatura" in xa and "curvatura" in xb, (p["id"], eixo)
                publicadas += 1
                if xa["curvatura"] != xb["curvatura"]:
                    divergentes += 1
    assert publicadas >= 1, "nenhuma raiz publicou curvatura"
    assert divergentes >= 1, (
        "nenhuma curvatura divergiu nesta fixture — a excecao nomeada do comparador "
        "perdeu o caso que a justifica; remedir antes de retira-la (D4)")


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_a_reversa_recusa_onde_a_cli_do_motor_recusa():
    """D5/A6: `gp = -150%` faz a CLI do motor sair com codigo 2 ANTES de qualquer
    handler — `reverter` levanta, e o espelho tem de recusar em vez de resolver uma
    raiz que o motor nunca calcularia."""
    probs, py = _py_reversa()
    js = _lado_js()
    fora = [(p["id"], a["recusa_da_cli"], js[p["id"]]["recusa_da_cli"])
            for p, a in zip(probs, py) if a["recusa_da_cli"] != js[p["id"]]["recusa_da_cli"]]
    assert not fora, f"recusa divergente (id, py, js): {fora}"
    assert sum(a["recusa_da_cli"] for a in py) >= 1, "nenhuma recusa de CLI exercitada"


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_fixture_de_reversa_cobre_o_que_discrimina():
    probs, py = _py_reversa()
    ok = [a for a in py if not a["recusa_da_cli"]]
    motivos = {e["leitura"]["motivo"] for a in ok for e in a["eixos"].values()}
    assert motivos == {"raiz_na_faixa", "sem_raiz_na_faixa", "cap_na_faixa",
                       "cap_na_faixa_decrescente", "cap_fora_da_faixa",
                       "cap_indefinido"}, motivos
    posicoes = {a["eixos"]["custo_capital"]["leitura"]["beta"]["posicao"]
                for a in ok if "custo_capital" in a["eixos"]}
    assert posicoes >= {"abaixo", "dentro", "acima", "sem_banda"}, posicoes
    assert any(a["limitacoes"] == ["iso_nao_calculada"] for a in ok), "iso_nao_calculada nunca acende"
    assert any(a["limitacoes"] == [] for a in ok), "iso_nao_calculada nunca apaga"
    assert {p["args"]["rota"] for p in probs} >= {"firm", "equity"}, "uma rota so"


# ---------------------------------------------------------------------------
# Fatia 5I, Task 2 — o diagnostico por CELULA das grades, e o triangulo
# ---------------------------------------------------------------------------

@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_grade_publica_as_chaves_de_diagnostico_da_celula():
    """A §8.4 proibe numero VIVO com diagnostico CONGELADO, e a grade e' numero vivo
    desde esta fatia. A comparacao e' CELULA A CELULA, sobre a lista ORDENADA de
    chaves daquela celula — NUNCA sobre `diag` nem sobre a lista deduplicada da
    grade (A5): o wrapper dedupa por MENSAGEM e classifica depois, o espelho nunca
    teve as mensagens e dedupa por CHAVE. As duas listas tem comprimentos
    diferentes sempre que duas mensagens colapsam na mesma chave — e e' o que
    acontece de verdade nesta fixture, porque a mensagem de `firm_rir` carrega o
    valor do RiR e muda de celula para celula. O teste EXIGE esse caso: sem ele,
    comparar `diag` passaria por acidente e a armadilha ficaria aberta."""
    probs = _problemas({"grade1d", "grade2d"})
    assert probs, "fixture sem grades"
    py, js = avaliar_python(probs), _lado_js()

    fora, celulas_com_chave, colapso_exercitado = [], 0, False
    for p, a in zip(probs, py):
        b = js[p["id"]]
        cel_py = (a["celulas"] if p["tipo"] == "grade1d"
                  else [c for lin in a["celulas"] for c in lin])
        cel_js = (b["celulas"] if p["tipo"] == "grade1d"
                  else [c for lin in b["celulas"] for c in lin])
        assert len(cel_py) == len(cel_js), p["id"]
        for i, (cp, cj) in enumerate(zip(cel_py, cel_js)):
            if cp["diagnosticos_chaves"] != cj["diagnosticos_chaves"]:
                fora.append((p["id"], i, cp["diagnosticos_chaves"], cj["diagnosticos_chaves"]))
            celulas_com_chave += len(cj["diagnosticos_chaves"])
        # A armadilha, medida: a dedup do wrapper (por MENSAGEM) e a do espelho (por
        # CHAVE) nao tem o mesmo comprimento quando a mensagem varia com a celula.
        if len(a["diagnosticos_unicos_chaves"]) != len(b["diagnosticos_unicos_chaves"]):
            colapso_exercitado = True
    assert not fora, f"{len(fora)} celulas com chaves divergentes; primeiras 3: {fora[:3]}"
    assert celulas_com_chave >= 1, "nenhuma celula publicou chave de diagnostico"
    assert colapso_exercitado, (
        "nenhuma grade exercita o colapso mensagem->chave — comparar `diag` passaria "
        "por acidente nesta fixture, e a armadilha de A5 ficaria sem trava")
    # A orientacao nao-quadrada da grade 2D continua exigida: uma grade quadrada
    # esconde transposicao de eixos (a licao da 3C), e as chaves por celula nao a
    # denunciariam sozinhas.
    assert any(len(p["args"]["pontos_x"]) != len(p["args"]["pontos_y"])
               for p in probs if p["tipo"] == "grade2d"), "toda grade 2D e quadrada"


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_triangulo_resolve_a_terceira_variavel():
    """D7: o `rir` vira NUMERO publicado. As tres configuracoes de `{inputs, output}`,
    nas duas rotas, contra a identidade `g = rir x retorno` do caso — e, o que trava
    de verdade, contra o VALOR QUE A PROSA DO MOTOR TRAZ (a eco `RiR = g/ROIC` na
    rota firm, `Retencao g/ROE` na equity), na precisao em que o motor a escreve
    (`{:.1%}`). Sem esse segundo ancora, o numero novo seria conferido contra a
    conta que o proprio espelho faz."""
    probs = _problemas({"triangulo"})
    assert probs, "fixture sem problemas de triangulo"
    py, js = avaliar_python(probs), _lado_js()

    fora, contra_a_prosa = [], []
    for p, a in zip(probs, py):
        b = js[p["id"]]
        for campo in ("variavel", "valor", "rir"):
            if a[campo] != b[campo]:
                fora.append((p["id"], campo, a[campo], b[campo]))
        # O ancora do motor: o `rir` do espelho, escrito como o motor o escreve.
        if f"{b['rir']:.1%}" != f"{a['rir_da_prosa_do_motor']:.1%}":
            contra_a_prosa.append((p["id"], b["rir"], a["rir_da_prosa_do_motor"]))
    assert not fora, f"divergencias (id, campo, py, js): {fora[:3]}"
    assert not contra_a_prosa, f"rir fora do que a prosa do motor traz: {contra_a_prosa}"

    saidas = {(p["args"]["rota"], p["args"]["triangulo"]["output"]) for p in probs}
    assert saidas == {("firm", "rir"), ("firm", "roic"), ("firm", "g"),
                      ("equity", "rir"), ("equity", "roe"), ("equity", "g")}, saidas


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_avisos_dominio_da_rampa_acende_no_espelho_como_no_wrapper():
    """A7: `tax` fora de [0%, 100%] e' REGIME ANOMALO em `avaliar_dominios_cli` —
    aviso, nao recusa: o vetor e' calculado assim mesmo, e `jprint` injeta
    `avisos_dominio` na saida. So' chega ao `resultados` pela rota RAMPA (o
    `_monta_cenario` de firm/equity e' whitelist fechada), e por isso a quarta
    entrada de `AVISOS_RAMPA` e a checagem vivem aqui."""
    probs = _problemas({"rampa"})
    py, js = avaliar_python(probs), _lado_js()
    fora = [(p["id"], a["avisos"], js[p["id"]]["avisos"])
            for p, a in zip(probs, py)
            if not a["recusado"] and a["avisos"] != js[p["id"]]["avisos"]]
    assert not fora, f"avisos divergentes (id, py, js): {fora[:3]}"
    acesos = [a for a in py if not a["recusado"] and "avisos_dominio" in a["avisos"]]
    apagados = [a for a in py if not a["recusado"] and "avisos_dominio" not in a["avisos"]]
    assert acesos, "nenhum problema de rampa acende avisos_dominio"
    assert apagados, "todo problema de rampa acende avisos_dominio — trava vacuamente verde"
