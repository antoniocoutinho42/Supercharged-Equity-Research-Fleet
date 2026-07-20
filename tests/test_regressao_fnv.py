# -*- coding: utf-8 -*-
"""Regressão FNV — fixture COMMITADA (Task 5.1).

Diferente de tests/test_delta.py (família B) e tests/test_engine_m_terminal.py,
que dependem de uma fonte somente-leitura FORA do repo (skip quando ausente),
este módulo usa SÓ os arquivos commitados em tests/fixtures/fnv/ — dados reais
da sessão FNV (15/07/2026) que originou o plugin, convertidos para os schemas
atuais. Roda em qualquer máquina, sem skip.

Exercita o namespace completo ponta a ponta:
  1. engine sobre P1 (derivado: CAP pré-revisão, sem m_terminal)
  2. engine sobre P3 (real, byte-a-byte — hash_inputs é o teste de fidelidade
     da cópia) e comparação com o oráculo resultados_p3.json
  3. snapshot.py + validar.py (estado.yaml, red_team.md)
  4. checar.py --etapa dossie/claims/valuation/decisao
  5. compor.py (relatorio.md + log_consistencia.md, 100% dos números rastreados)
  6. memoria.py (nota gerada, sem duplicar o corpo do dossiê)
  7. delta.py P1 -> P3 (reuso barato do arco já coberto em test_delta.py, mas
     aqui 100% sobre a fixture commitada)

Encoding: todos os arquivos-fonte têm acentos; cópias são byte-a-byte
(shutil.copyfile, sempre binário) — nunca reabertas e regravadas como texto,
para não arriscar transcodificação.
"""
import json
import os
import re
import shutil
import subprocess
import sys

import pytest
import yaml

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXT_DIR = os.path.join(REPO_ROOT, "tests", "fixtures", "fnv")

ENGINE_PATH = os.path.join(REPO_ROOT, "skills", "er-valuation", "engine.py")
SNAPSHOT_PATH = os.path.join(REPO_ROOT, "scripts", "snapshot.py")
DELTA_PATH = os.path.join(REPO_ROOT, "scripts", "delta.py")
VALIDAR_PATH = os.path.join(REPO_ROOT, "scripts", "validar.py")
CHECAR_PATH = os.path.join(REPO_ROOT, "skills", "er-relatorio", "checar.py")
COMPOR_PATH = os.path.join(REPO_ROOT, "skills", "er-relatorio", "compor.py")
MEMORIA_PATH = os.path.join(REPO_ROOT, "scripts", "memoria.py")

PYTHON = sys.executable

# ATUALIZAÇÃO INTENCIONAL (engine v3.0.0, correções pós-HG): inputs_p3.yaml ganhou
# premissas.respostas_sinais (R4) e premissas.resolucao_divergencia (R5) — os novos
# comportamentos bloqueantes exigem esses registros; os números-âncora do caso
# (hurdle 116,46 / central 188,49 / sinais) permanecem IDÊNTICOS à sessão real.
# Hash anterior (fixture byte-a-byte da sessão de 15/07/2026): 34e6680992b5b76e.
HASH_P3_ESPERADO = "089ea8e6f4fc398b"

# frase única do dossiê (governança/ownership — nunca citada pela nota de
# memória, que só ecoa cabeçalho/decisão/pendências/âncoras) usada como
# sentinela de não-duplicação no bloco 6.
_SENTINELA_DOSSIE = "Massachusetts Financial Services"


def _tol(obtido, esperado, tol, rotulo):
    assert obtido is not None, f"{rotulo}: obtido None, esperado {esperado}"
    assert abs(obtido - esperado) <= tol, f"{rotulo}: obtido {obtido}, esperado {esperado} (tol {tol})"


def _rodar(argv, **kw):
    r = subprocess.run([PYTHON] + argv, capture_output=True, text=True, **kw)
    return r


def _rodar_engine(inputs_path, out_dir):
    r = _rodar([ENGINE_PATH, str(inputs_path), "--out", str(out_dir)])
    assert r.returncode == 0, f"engine.py falhou: stdout={r.stdout!r} stderr={r.stderr!r}"
    with open(os.path.join(out_dir, "resultados.json"), "r", encoding="utf-8") as fh:
        return json.load(fh)


def _rodar_snapshot(ns):
    r = _rodar([SNAPSHOT_PATH, str(ns)])
    assert r.returncode == 0, f"snapshot.py falhou: stdout={r.stdout!r} stderr={r.stderr!r}"
    return r.stdout


def _rodar_checar(ns, etapa):
    r = _rodar([CHECAR_PATH, str(ns), "--etapa", etapa, "--json"])
    dados = json.loads(r.stdout)
    return r, dados


# ----------------------------------------------------------------------------
# Fixture única: monta o namespace e roda o arco inteiro UMA vez (módulo).
# Blocos 1-7 do brief viram uma sequência de subprocessos reais sobre a
# fixture commitada; os test_* abaixo apenas verificam fatias do resultado.
# ----------------------------------------------------------------------------

@pytest.fixture(scope="module")
def pipeline(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("fnv_regressao")
    ns = tmp / "FNV"
    ns.mkdir()

    # namespace fixo (nota do brief): dossie, valuation, red_team, claims,
    # estado_final.yaml -> estado.yaml, inputs_valuation.md (exigido por
    # checar --etapa dossie). Cópia SEMPRE binária (shutil.copyfile), para
    # preservar os acentos/encoding byte-a-byte dos arquivos-fonte.
    shutil.copyfile(os.path.join(FIXT_DIR, "dossie.md"), ns / "dossie.md")
    shutil.copyfile(os.path.join(FIXT_DIR, "valuation.md"), ns / "valuation.md")
    shutil.copyfile(os.path.join(FIXT_DIR, "red_team.md"), ns / "red_team.md")
    shutil.copyfile(os.path.join(FIXT_DIR, "claims.yaml"), ns / "claims.yaml")
    shutil.copyfile(os.path.join(FIXT_DIR, "estado_final.yaml"), ns / "estado.yaml")
    shutil.copyfile(os.path.join(FIXT_DIR, "inputs_valuation.md"), ns / "inputs_valuation.md")
    # R1: julgamento metodológico prévio (obrigatório no checar --etapa dossie/valuation)
    shutil.copyfile(os.path.join(FIXT_DIR, "metodo.yaml"), ns / "metodo.yaml")

    inputs_path = ns / "inputs.yaml"
    saida_dir = ns / "saida_FNV"

    # --- Bloco 1: engine sobre P1 (derivado da P3 real) ---------------------
    shutil.copyfile(os.path.join(FIXT_DIR, "inputs_p1.yaml"), inputs_path)
    res_p1 = _rodar_engine(inputs_path, saida_dir)
    snap_p1_stdout = _rodar_snapshot(ns)
    hash_p1 = res_p1["engine"]["hash_inputs"]

    # --- Bloco 2: engine sobre P3 (real, byte-a-byte) ------------------------
    shutil.copyfile(os.path.join(FIXT_DIR, "inputs_p3.yaml"), inputs_path)
    res_p3 = _rodar_engine(inputs_path, saida_dir)
    snap_p3_stdout = _rodar_snapshot(ns)
    hash_p3 = res_p3["engine"]["hash_inputs"]

    with open(os.path.join(FIXT_DIR, "resultados_p3.json"), "r", encoding="utf-8") as fh:
        oraculo_p3 = json.load(fh)

    # --- Bloco 3: validar.py sobre estado.yaml e red_team.md -----------------
    val_estado = _rodar([VALIDAR_PATH, str(ns / "estado.yaml"), "--schema", "estado"])
    val_red_team = _rodar([VALIDAR_PATH, str(ns / "red_team.md"), "--schema", "red_team_header"])

    # --- Bloco 4: checar.py --etapa {dossie,claims,valuation,decisao} --------
    chk_dossie, chk_dossie_json = _rodar_checar(ns, "dossie")
    chk_claims, chk_claims_json = _rodar_checar(ns, "claims")
    chk_valuation, chk_valuation_json = _rodar_checar(ns, "valuation")
    chk_decisao, chk_decisao_json = _rodar_checar(ns, "decisao")

    # --- Bloco 5: compor.py (relatorio.md + log_consistencia.md) -------------
    compor_res = _rodar([COMPOR_PATH, str(ns)])
    relatorio = (ns / "relatorio.md").read_text(encoding="utf-8") if (ns / "relatorio.md").is_file() else None
    log_consistencia = ((ns / "log_consistencia.md").read_text(encoding="utf-8")
                         if (ns / "log_consistencia.md").is_file() else None)

    # --- Bloco 6: memoria.py (nota gerada) ------------------------------------
    memoria_res = _rodar([MEMORIA_PATH, str(ns)])
    nota_path = ns / "memoria" / "FNV.md"
    nota = nota_path.read_text(encoding="utf-8") if nota_path.is_file() else None

    # --- Bloco 7: delta.py P1 -> P3 (100% da fixture commitada) --------------
    delta_saida = ns / "delta_saida"
    delta_res = _rodar([DELTA_PATH, str(ns), "--desde", hash_p1, "--ate", hash_p3,
                         "--saida", str(delta_saida)])
    delta_json = None
    if delta_res.returncode == 0:
        with open(delta_saida / "delta.json", "r", encoding="utf-8") as fh:
            delta_json = json.load(fh)

    return {
        "ns": ns,
        "res_p1": res_p1, "hash_p1": hash_p1, "snap_p1_stdout": snap_p1_stdout,
        "res_p3": res_p3, "hash_p3": hash_p3, "snap_p3_stdout": snap_p3_stdout,
        "oraculo_p3": oraculo_p3,
        "val_estado": val_estado, "val_red_team": val_red_team,
        "chk_dossie": chk_dossie, "chk_dossie_json": chk_dossie_json,
        "chk_claims": chk_claims, "chk_claims_json": chk_claims_json,
        "chk_valuation": chk_valuation, "chk_valuation_json": chk_valuation_json,
        "chk_decisao": chk_decisao, "chk_decisao_json": chk_decisao_json,
        "compor_res": compor_res, "relatorio": relatorio, "log_consistencia": log_consistencia,
        "memoria_res": memoria_res, "nota": nota,
        "delta_res": delta_res, "delta_json": delta_json,
    }


# ----------------------------------------------------------------------------
# 0. Fidelidade da fixture (a cópia é o contrato: hash igual ao original)
# ----------------------------------------------------------------------------

def test_inputs_p3_hash_fiel_ao_original():
    """O hash8 do inputs_p3.yaml commitado DEVE bater com HASH_P3_ESPERADO — é o
    teste de que a fixture não muda silenciosamente (toda mudança intencional
    atualiza a constante COM justificativa no comentário dela)."""
    import hashlib
    caminho = os.path.join(FIXT_DIR, "inputs_p3.yaml")
    with open(caminho, "r", encoding="utf-8") as fh:
        texto = fh.read()
    hash8 = hashlib.sha256(texto.encode("utf-8")).hexdigest()[:16]
    assert hash8 == HASH_P3_ESPERADO


# ----------------------------------------------------------------------------
# 1. Engine P1 (derivado)
# ----------------------------------------------------------------------------

def test_engine_p1_hurdle_e_central(pipeline):
    res = pipeline["res_p1"]
    _tol(res["hurdle"]["cenarios"]["ponderado"], 51.71, 0.02, "hurdle ponderado P1")
    _tol(res["economico"]["central_ponderado"], 73.35, 0.02, "central econômico P1")


def test_engine_p1_sinais_e_gate(pipeline):
    res = pipeline["res_p1"]
    assert res["sinais"]["entrada"] == "NAO_ACIONAVEL"
    assert res["sinais"]["economico"] == "SOBREAVALIADO"
    assert res["gate"]["modo_recomendado"] == "SUMARIA"


# ----------------------------------------------------------------------------
# 2. Engine P3 (real) — hash_inputs, valores-âncora e comparação com o oráculo
# ----------------------------------------------------------------------------

def test_engine_p3_hash_inputs(pipeline):
    assert pipeline["res_p3"]["engine"]["hash_inputs"] == HASH_P3_ESPERADO
    assert pipeline["hash_p3"] == HASH_P3_ESPERADO


def test_engine_p3_hurdle_e_central(pipeline):
    res = pipeline["res_p3"]
    _tol(res["hurdle"]["cenarios"]["ponderado"], 116.46, 0.01, "hurdle ponderado P3")
    _tol(res["economico"]["central_ponderado"], 188.49, 0.01, "central econômico P3")
    faixa = res["economico"]["faixa_ponderada"]
    _tol(faixa[0], 175.05, 0.01, "faixa econômica[0] P3")
    _tol(faixa[1], 203.18, 0.01, "faixa econômica[1] P3")


def test_engine_p3_sinais_e_gate(pipeline):
    res = pipeline["res_p3"]
    assert res["sinais"]["economico"] == "DENTRO_DA_FAIXA"
    assert res["gate"]["modo_recomendado"] == "PADRAO"
    assert res["validacao_multiplos"]["veredicto"] == "DIVERGE_MATERIAL"


def test_engine_p3_bate_oraculo_chaves_ancora(pipeline):
    """Compara resultados.json gerado agora contra resultados_p3.json (oráculo
    commitado, cópia exata do resultado real da sessão) nas mesmas chaves-âncora."""
    res, oraculo = pipeline["res_p3"], pipeline["oraculo_p3"]
    for chave_topo, sub in (
        ("hurdle", ("cenarios", "ponderado")),
        ("economico", ("central_ponderado",)),
        ("economico", ("faixa_ponderada",)),
        ("sinais", ("economico",)),
        ("sinais", ("entrada",)),
        ("gate", ("modo_recomendado",)),
        ("validacao_multiplos", ("veredicto",)),
        ("engine", ("hash_inputs",)),
    ):
        obtido, esperado = res[chave_topo], oraculo[chave_topo]
        for parte in sub:
            obtido, esperado = obtido[parte], esperado[parte]
        assert obtido == esperado, f"{chave_topo}.{'.'.join(sub)}: {obtido!r} != oráculo {esperado!r}"


# ----------------------------------------------------------------------------
# 3. snapshot.py + validar.py (estado, red_team)
# ----------------------------------------------------------------------------

def test_snapshot_hash_p3(pipeline):
    assert HASH_P3_ESPERADO in pipeline["snap_p3_stdout"]
    assert (pipeline["ns"] / "runs" / HASH_P3_ESPERADO / "resultados.json").is_file()


def test_estado_valida_contra_schema(pipeline):
    r = pipeline["val_estado"]
    assert r.returncode == 0, f"validar.py --schema estado falhou: {r.stdout} {r.stderr}"
    assert "VALIDO" in r.stdout


def test_red_team_valida_contra_schema(pipeline):
    r = pipeline["val_red_team"]
    assert r.returncode == 0, f"validar.py --schema red_team_header falhou: {r.stdout} {r.stderr}"
    assert "VALIDO" in r.stdout


# ----------------------------------------------------------------------------
# 4. checar.py --etapa {dossie, claims, valuation, decisao}
# ----------------------------------------------------------------------------

def test_checar_dossie_aprovado(pipeline):
    dados = pipeline["chk_dossie_json"]
    assert dados["status"] == "APROVADO", f"faltas: {dados['faltas']}"


def test_checar_claims_aprovado(pipeline):
    dados = pipeline["chk_claims_json"]
    assert dados["status"] == "APROVADO", f"faltas: {dados['faltas']}"


def test_checar_valuation_aprovado(pipeline):
    dados = pipeline["chk_valuation_json"]
    assert dados["status"] == "APROVADO", f"faltas: {dados['faltas']}"


def test_checar_decisao_aprovado(pipeline):
    dados = pipeline["chk_decisao_json"]
    assert dados["status"] == "APROVADO", f"faltas: {dados['faltas']}"


# ----------------------------------------------------------------------------
# 5. compor.py — relatorio.md + log_consistencia.md (100% rastreado)
# ----------------------------------------------------------------------------

def test_compor_gera_relatorio_sem_erro(pipeline):
    r = pipeline["compor_res"]
    assert r.returncode == 0, f"compor.py falhou: stdout={r.stdout!r} stderr={r.stderr!r}"
    assert pipeline["relatorio"] is not None
    # nenhum marcador de composição não resolvido sobrou no texto
    assert not re.findall(r"\{\{[^}]+\}\}", pipeline["relatorio"])


def test_compor_log_consistencia_100_por_cento(pipeline):
    log = pipeline["log_consistencia"]
    assert log is not None
    m = re.search(r"(\d+) números injetados, (\d+) rastreados \(100%", log)
    assert m, f"padrão '100%' não encontrado em log_consistencia.md:\n{log[-500:]}"
    injetados, rastreados = int(m.group(1)), int(m.group(2))
    assert injetados > 0
    assert injetados == rastreados


# ----------------------------------------------------------------------------
# 6. memoria.py — nota gerada, sem duplicar o dossiê
# ----------------------------------------------------------------------------

def test_memoria_gera_nota_sem_erro(pipeline):
    r = pipeline["memoria_res"]
    assert r.returncode == 0, f"memoria.py falhou: stdout={r.stdout!r} stderr={r.stderr!r}"
    assert pipeline["nota"] is not None


def test_memoria_conteudo_esperado(pipeline):
    nota = pipeline["nota"]
    assert "WATCHLIST (PRÓXIMA)" in nota
    assert "AC-04" in nota          # trilha interna: pendências mantêm IDs de issue
    assert "089ea8e6" in nota       # hash8 do run canônico (engine v3, ver HASH_P3_ESPERADO)


def test_memoria_nao_duplica_dossie(pipeline):
    """A nota NÃO deve conter o corpo do dossiê — sentinela é uma frase única
    do dossiê (seção de governança/ownership) que a memória nunca ecoa (a
    memória só reproduz cabeçalho, decisão verbatim, timeline, pendências e
    âncoras numéricas — nunca o corpo analítico)."""
    dossie_texto = (pipeline["ns"] / "dossie.md").read_text(encoding="utf-8")
    assert _SENTINELA_DOSSIE in dossie_texto, "sentinela não encontrada no dossiê-fixture (ajustar teste)"
    assert _SENTINELA_DOSSIE not in pipeline["nota"]


# ----------------------------------------------------------------------------
# 7. delta.py P1 -> P3 (100% da fixture commitada; arco também coberto com
#    fonte externa em test_delta.py — mantemos os dois testes)
# ----------------------------------------------------------------------------

def test_delta_p1_p3_roda_sem_erro(pipeline):
    r = pipeline["delta_res"]
    assert r.returncode == 0, f"delta.py falhou: stdout={r.stdout!r} stderr={r.stderr!r}"
    assert pipeline["delta_json"] is not None


def test_delta_p1_p3_sinal_economico_mudou(pipeline):
    d = pipeline["delta_json"]
    por_chave = {x["chave"]: x for x in d["valuation"]}
    sinal = por_chave["sinais.economico"]
    assert sinal["antes"] == "SOBREAVALIADO"
    assert sinal["depois"] == "DENTRO_DA_FAIXA"
    assert sinal["mudou_sinal"] is True
    assert d["resumo"]["sinais_mudaram"] is True
