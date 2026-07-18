# -*- coding: utf-8 -*-
"""Testes de scripts/delta.py — diff estruturado entre runs (Task 3.1).

Duas famílias de teste:

  A. Mecânica isolada (rápida, sem subprocess): monta runs/<hash8>/ "à mão"
     (sem passar pelo engine real) para exercitar flatten/diff/CLI em
     isolamento — mesmo padrão de tests/test_snapshot.py (importlib +
     chamada direta de main(argv), capsys).

  B. Regressão FNV (subprocess, engine real v2.2.0): reproduz o arco P1->P3
     da sessão FNV real. Fonte somente-leitura fora do repo; se ausente,
     pytest.skip (mesmo padrão de tests/test_engine_m_terminal.py).
"""
import copy
import importlib.util
import json
import os
import shutil
import subprocess
import sys

import pytest
import yaml

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DELTA_PATH = os.path.join(REPO_ROOT, "scripts", "delta.py")
ENGINE_PATH = os.path.join(REPO_ROOT, "skills", "er-valuation", "engine.py")

FNV_DIR = r"C:\Claude\Workflows\Equity Research\15.07.2025\FNV"
FNV_INPUTS = os.path.join(FNV_DIR, "inputs (1).yaml")

PYTHON = sys.executable


def _carregar_delta():
    spec = importlib.util.spec_from_file_location("delta", DELTA_PATH)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


delta = _carregar_delta()


# ----------------------------------------------------------------------------
# Helpers de fixture (família A — runs "à mão")
# ----------------------------------------------------------------------------

def _escrever_yaml(caminho, dados):
    with open(caminho, "w", encoding="utf-8") as fh:
        yaml.safe_dump(dados, fh, allow_unicode=True, sort_keys=False)


def _escrever_json(caminho, dados):
    with open(caminho, "w", encoding="utf-8") as fh:
        json.dump(dados, fh, ensure_ascii=False)


def _merge(base, novo):
    """Deep-merge simples (novo sobrepõe base) para variar fixtures de resultados.json."""
    out = copy.deepcopy(base)
    for k, v in novo.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


_RESULTADOS_TEMPLATE = {
    "engine": {"versao": "9.9.9", "hash_inputs": "0000000000000000",
               "gerado_em": "2026-01-01T00:00:00+00:00"},
    "meta": {"ticker": "TST", "preco_atual": 100.0},
    "sinais": {"economico": "SOBREAVALIADO", "entrada": "NAO_ACIONAVEL"},
    "gate": {"modo_recomendado": "SUMARIA"},
    "hurdle": {"cenarios": {"ponderado": 50.0}},
    "economico": {"central_ponderado": 70.0, "faixa_ponderada": [60.0, 80.0]},
    "validacao": {"erros": [], "avisos": [], "status": "APROVADO"},
}


def _resultados(hash_inputs, **overrides):
    r = _merge(_RESULTADOS_TEMPLATE, {"engine": {"hash_inputs": hash_inputs}})
    return _merge(r, overrides)


_FATOS_MIN = {"lpa_ajustado_fy": 5.0, "ledger": [{"doc": "a"}, {"doc": "b"}]}
_PREMISSAS_MIN = {
    "ke_hurdle": 0.12,
    "cap_teto_defensavel": 20,
    "cap_confianca": "MEDIA",
    "justificativa_cap": "x",
    "justificativa_cenarios": "y",
    "cenarios": {
        "bear": {"prob": 0.25, "g": 0.04, "roe": 0.09, "cap": 10},
        "base": {"prob": 0.50, "g": 0.07, "roe": 0.12, "cap": 15},
        "bull": {"prob": 0.25, "g": 0.09, "roe": 0.15, "cap": 20},
    },
}


def _montar_run(ns, hash8, fatos=None, premissas=None, resultados=None,
                 claims=None, decisao=None, meta_extra=None):
    """Cria <ns>/runs/<hash8>/ com inputs.yaml + resultados.json (e
    opcionalmente claims.yaml/estado.yaml), imitando a saída de snapshot.py
    sem depender dele (unidade rápida)."""
    run_dir = ns / "runs" / hash8
    run_dir.mkdir(parents=True, exist_ok=True)

    inputs = {
        "meta": {"ticker": "TST", "preco_atual": 100.0},
        "fatos": fatos if fatos is not None else copy.deepcopy(_FATOS_MIN),
        "premissas": premissas if premissas is not None else copy.deepcopy(_PREMISSAS_MIN),
    }
    _escrever_yaml(run_dir / "inputs.yaml", inputs)

    res = resultados if resultados is not None else _resultados(hash8)
    _escrever_json(run_dir / "resultados.json", res)

    if claims is not None:
        _escrever_yaml(run_dir / "claims.yaml", {"claims": claims})
    if decisao is not None:
        _escrever_yaml(run_dir / "estado.yaml", {"ticker": "TST", "decisao": decisao})

    meta = {"hash": hash8, "congelados": sorted(
        ["inputs.yaml", "resultados.json"]
        + (["claims.yaml"] if claims is not None else [])
        + (["estado.yaml"] if decisao is not None else [])
    )}
    if meta_extra:
        meta.update(meta_extra)
    _escrever_yaml(run_dir / "meta.yaml", meta)
    return run_dir


# ----------------------------------------------------------------------------
# A.1 — CLI: help, erros de uso
# ----------------------------------------------------------------------------

def test_ajuda_curta():
    with pytest.raises(SystemExit) as excinfo:
        delta.main(["--help"])
    assert excinfo.value.code == 0


def test_erro_run_base_ausente(tmp_path, capsys):
    ns = tmp_path / "ns"
    ns.mkdir()
    codigo = delta.main([str(ns), "--desde", "aaaaaaaaaaaaaaaa", "--ate", "bbbbbbbbbbbbbbbb"])
    saida = capsys.readouterr()
    assert codigo == 1
    assert "run base" in (saida.out + saida.err)


def test_erro_alvo_ausente(tmp_path, capsys):
    ns = tmp_path / "ns"
    ns.mkdir()
    _montar_run(ns, "aaaaaaaaaaaaaaaa")
    codigo = delta.main([str(ns), "--desde", "aaaaaaaaaaaaaaaa", "--ate", "bbbbbbbbbbbbbbbb"])
    saida = capsys.readouterr()
    assert codigo == 1
    assert "run alvo" in (saida.out + saida.err)


def test_erro_sem_ate_e_sem_estado(tmp_path, capsys):
    ns = tmp_path / "ns"
    ns.mkdir()
    _montar_run(ns, "aaaaaaaaaaaaaaaa")
    codigo = delta.main([str(ns), "--desde", "aaaaaaaaaaaaaaaa"])
    saida = capsys.readouterr()
    assert codigo == 1
    assert "estado.yaml" in (saida.out + saida.err)


def test_erro_estado_sem_engine_hash(tmp_path, capsys):
    ns = tmp_path / "ns"
    ns.mkdir()
    _montar_run(ns, "aaaaaaaaaaaaaaaa")
    (ns / "estado.yaml").write_text("ticker: TST\nengine: {versao: '1.0', hash: '0000000000000000'}\n",
                                     encoding="utf-8")
    codigo = delta.main([str(ns), "--desde", "aaaaaaaaaaaaaaaa"])
    saida = capsys.readouterr()
    assert codigo == 1
    assert "engine.hash" in (saida.out + saida.err)


def test_usa_engine_hash_do_estado_quando_sem_ate(tmp_path, capsys):
    ns = tmp_path / "ns"
    ns.mkdir()
    _montar_run(ns, "aaaaaaaaaaaaaaaa")
    _montar_run(ns, "bbbbbbbbbbbbbbbb")
    (ns / "estado.yaml").write_text("ticker: TST\nengine: {versao: '1.0', hash: bbbbbbbbbbbbbbbb}\n",
                                     encoding="utf-8")
    codigo = delta.main([str(ns), "--desde", "aaaaaaaaaaaaaaaa"])
    saida = capsys.readouterr()
    assert codigo == 0
    assert "bbbbbbbbbbbbbbbb" in saida.out
    assert (ns / "delta.json").is_file()


def test_saida_dir_customizado(tmp_path, capsys):
    ns = tmp_path / "ns"
    ns.mkdir()
    _montar_run(ns, "aaaaaaaaaaaaaaaa")
    _montar_run(ns, "bbbbbbbbbbbbbbbb")
    saida_dir = tmp_path / "saida_custom"
    codigo = delta.main([str(ns), "--desde", "aaaaaaaaaaaaaaaa", "--ate", "bbbbbbbbbbbbbbbb",
                          "--saida", str(saida_dir)])
    capsys.readouterr()
    assert codigo == 0
    assert (saida_dir / "delta.json").is_file()
    assert (saida_dir / "delta.md").is_file()
    assert not (ns / "delta.json").exists()


# ----------------------------------------------------------------------------
# A.2 — fatos (flatten parar-em-lista, ledger, listas resumidas)
# ----------------------------------------------------------------------------

def test_fatos_inputs_diff_simples_e_ledger_no_resumo(tmp_path, capsys):
    ns = tmp_path / "ns"
    ns.mkdir()
    fatos_base = {"lpa_ajustado_fy": 5.0, "ledger": [{"doc": "a"}]}
    fatos_alvo = {"lpa_ajustado_fy": 5.9, "ledger": [{"doc": "a"}, {"doc": "b"}, {"doc": "c"}]}
    _montar_run(ns, "aaaaaaaaaaaaaaaa", fatos=fatos_base)
    _montar_run(ns, "bbbbbbbbbbbbbbbb", fatos=fatos_alvo)

    codigo = delta.main([str(ns), "--desde", "aaaaaaaaaaaaaaaa", "--ate", "bbbbbbbbbbbbbbbb"])
    capsys.readouterr()
    assert codigo == 0

    dados = json.loads((ns / "delta.json").read_text(encoding="utf-8"))
    chaves = {d["chave"]: d for d in dados["fatos"]["inputs"]}
    assert chaves["fatos.lpa_ajustado_fy"]["antes"] == 5.0
    assert chaves["fatos.lpa_ajustado_fy"]["depois"] == 5.9
    # ledger não aparece em fatos.inputs (é ignorado, tratado à parte)
    assert not any(c.startswith("fatos.ledger") for c in chaves)
    assert dados["resumo"]["ledger"] == "+2 documentos"


def test_fatos_lista_longa_e_resumida_no_antes_depois(tmp_path, capsys):
    ns = tmp_path / "ns"
    ns.mkdir()
    serie_base = [{"ano": a, "pe": a * 1.1} for a in range(2016, 2026)]
    serie_alvo = [{"ano": a, "pe": a * 1.2} for a in range(2016, 2026)]
    fatos_base = {"lpa_ajustado_fy": 5.0, "multiplos_historicos": {"pe": {"serie": serie_base}}}
    fatos_alvo = {"lpa_ajustado_fy": 5.0, "multiplos_historicos": {"pe": {"serie": serie_alvo}}}
    _montar_run(ns, "aaaaaaaaaaaaaaaa", fatos=fatos_base)
    _montar_run(ns, "bbbbbbbbbbbbbbbb", fatos=fatos_alvo)

    codigo = delta.main([str(ns), "--desde", "aaaaaaaaaaaaaaaa", "--ate", "bbbbbbbbbbbbbbbb"])
    capsys.readouterr()
    assert codigo == 0

    dados = json.loads((ns / "delta.json").read_text(encoding="utf-8"))
    chaves = {d["chave"]: d for d in dados["fatos"]["inputs"]}
    entrada = chaves["fatos.multiplos_historicos.pe.serie"]
    # resumido: não é o dump completo de 10 dicts, é uma contagem
    assert entrada["antes"] == "10 item(ns)"
    assert entrada["depois"] == "10 item(ns)"


def test_fatos_lista_curta_de_escalares_nao_e_resumida(tmp_path, capsys):
    ns = tmp_path / "ns"
    ns.mkdir()
    fatos_base = {"lpa_ajustado_fy": 5.0, "ladder_precos": [175, 155]}
    fatos_alvo = {"lpa_ajustado_fy": 5.0, "ladder_precos": [175, 155, 135]}
    _montar_run(ns, "aaaaaaaaaaaaaaaa", fatos=fatos_base)
    _montar_run(ns, "bbbbbbbbbbbbbbbb", fatos=fatos_alvo)

    codigo = delta.main([str(ns), "--desde", "aaaaaaaaaaaaaaaa", "--ate", "bbbbbbbbbbbbbbbb"])
    capsys.readouterr()
    assert codigo == 0

    dados = json.loads((ns / "delta.json").read_text(encoding="utf-8"))
    chaves = {d["chave"]: d for d in dados["fatos"]["inputs"]}
    entrada = chaves["fatos.ladder_precos"]
    assert entrada["antes"] == [175, 155]
    assert entrada["depois"] == [175, 155, 135]


# ----------------------------------------------------------------------------
# A.3 — claims
# ----------------------------------------------------------------------------

def test_claims_ausentes_nos_dois_lados(tmp_path, capsys):
    ns = tmp_path / "ns"
    ns.mkdir()
    _montar_run(ns, "aaaaaaaaaaaaaaaa")
    _montar_run(ns, "bbbbbbbbbbbbbbbb")

    codigo = delta.main([str(ns), "--desde", "aaaaaaaaaaaaaaaa", "--ate", "bbbbbbbbbbbbbbbb"])
    capsys.readouterr()
    assert codigo == 0

    dados = json.loads((ns / "delta.json").read_text(encoding="utf-8"))
    assert dados["fatos"]["claims"] is None
    assert "claims_nota" in dados["fatos"]
    assert dados["resumo"]["n_claims"] == 0


def test_claims_adicionado_modificado_removido(tmp_path, capsys):
    ns = tmp_path / "ns"
    ns.mkdir()
    claims_base = [
        {"id": "F-01", "tipo": "FATO", "texto": "original", "fonte": "src1", "data": "2026-01-01"},
        {"id": "F-02", "tipo": "FATO", "texto": "removido", "fonte": "src2", "data": "2026-01-01"},
    ]
    claims_alvo = [
        {"id": "F-01", "tipo": "FATO", "texto": "modificado", "fonte": "src1", "data": "2026-01-01"},
        {"id": "F-03", "tipo": "ESTIMATIVA", "texto": "novo"},
    ]
    _montar_run(ns, "aaaaaaaaaaaaaaaa", claims=claims_base)
    _montar_run(ns, "bbbbbbbbbbbbbbbb", claims=claims_alvo)

    codigo = delta.main([str(ns), "--desde", "aaaaaaaaaaaaaaaa", "--ate", "bbbbbbbbbbbbbbbb"])
    capsys.readouterr()
    assert codigo == 0

    dados = json.loads((ns / "delta.json").read_text(encoding="utf-8"))
    bloco = dados["fatos"]["claims"]
    assert bloco["adicionados"] == ["F-03"]
    assert bloco["modificados"] == ["F-01"]
    assert bloco["removidos"] == ["F-02"]
    assert dados["resumo"]["n_claims"] == 3


def test_claims_congelado_malformado_exit_1_sem_traceback(tmp_path, capsys):
    """Fix 1 (review): claims.yaml congelado com YAML inválido -> exit 1 com
    mensagem 'erro: ...', nunca traceback não-tratado."""
    ns = tmp_path / "ns"
    ns.mkdir()
    run_base = _montar_run(ns, "aaaaaaaaaaaaaaaa")
    _montar_run(ns, "bbbbbbbbbbbbbbbb")
    # YAML sintaticamente inválido (flow sequence não fechada)
    (run_base / "claims.yaml").write_text("claims: [\n  - id: F-01\n", encoding="utf-8")

    codigo = delta.main([str(ns), "--desde", "aaaaaaaaaaaaaaaa", "--ate", "bbbbbbbbbbbbbbbb"])
    saida = capsys.readouterr()

    assert codigo == 1
    mensagem = saida.out + saida.err
    assert "erro" in mensagem
    assert "Traceback" not in mensagem


def test_claims_base_nunca_cai_no_fallback_do_ns(tmp_path, capsys):
    """Fix 1 (review): o lado BASE nunca usa <ns>/claims.yaml — run base sem
    claims congelado é tratado como ausente mesmo com claims.yaml presente no
    ns. Prova: alvo congela os MESMOS claims do ns; se a base caísse no
    fallback, o diff seria vazio; correto é todos os claims do alvo virarem
    'adicionados'."""
    ns = tmp_path / "ns"
    ns.mkdir()
    claims = [
        {"id": "F-01", "tipo": "FATO", "texto": "x", "fonte": "y", "data": "2026-01-01"},
        {"id": "F-02", "tipo": "FATO", "texto": "z", "fonte": "w", "data": "2026-01-02"},
    ]
    _montar_run(ns, "aaaaaaaaaaaaaaaa")  # base SEM claims.yaml congelado
    _montar_run(ns, "bbbbbbbbbbbbbbbb", claims=claims)
    _escrever_yaml(ns / "claims.yaml", {"claims": claims})  # idêntico ao alvo

    codigo = delta.main([str(ns), "--desde", "aaaaaaaaaaaaaaaa", "--ate", "bbbbbbbbbbbbbbbb"])
    capsys.readouterr()
    assert codigo == 0

    dados = json.loads((ns / "delta.json").read_text(encoding="utf-8"))
    bloco = dados["fatos"]["claims"]
    # base = ausente (não o arquivo do ns) -> tudo do alvo é "adicionado"
    assert bloco["adicionados"] == ["F-01", "F-02"]
    assert bloco["modificados"] == []
    assert bloco["removidos"] == []


def test_claims_fallback_para_claims_yaml_atual_do_ns(tmp_path, capsys):
    """Quando o run alvo não tem claims.yaml congelado, cai para <ns>/claims.yaml atual."""
    ns = tmp_path / "ns"
    ns.mkdir()
    claims_base = [{"id": "F-01", "tipo": "FATO", "texto": "x", "fonte": "y", "data": "2026-01-01"}]
    _montar_run(ns, "aaaaaaaaaaaaaaaa", claims=claims_base)
    _montar_run(ns, "bbbbbbbbbbbbbbbb")  # sem claims.yaml congelado

    claims_atual = [
        {"id": "F-01", "tipo": "FATO", "texto": "x", "fonte": "y", "data": "2026-01-01"},
        {"id": "F-02", "tipo": "FATO", "texto": "z", "fonte": "w", "data": "2026-01-02"},
    ]
    _escrever_yaml(ns / "claims.yaml", {"claims": claims_atual})

    codigo = delta.main([str(ns), "--desde", "aaaaaaaaaaaaaaaa", "--ate", "bbbbbbbbbbbbbbbb"])
    capsys.readouterr()
    assert codigo == 0

    dados = json.loads((ns / "delta.json").read_text(encoding="utf-8"))
    assert dados["fatos"]["claims"]["adicionados"] == ["F-02"]


# ----------------------------------------------------------------------------
# A.4 — valuation (flatten completo, engine à parte, mudou_sinal)
# ----------------------------------------------------------------------------

def test_valuation_ignora_gerado_em_mas_mostra_engine_a_parte(tmp_path, capsys):
    ns = tmp_path / "ns"
    ns.mkdir()
    res_base = _resultados("aaaaaaaaaaaaaaaa", engine={"gerado_em": "2026-01-01T00:00:00+00:00"})
    res_alvo = _resultados("bbbbbbbbbbbbbbbb", engine={"gerado_em": "2026-02-02T00:00:00+00:00"})
    _montar_run(ns, "aaaaaaaaaaaaaaaa", resultados=res_base)
    _montar_run(ns, "bbbbbbbbbbbbbbbb", resultados=res_alvo)

    codigo = delta.main([str(ns), "--desde", "aaaaaaaaaaaaaaaa", "--ate", "bbbbbbbbbbbbbbbb"])
    capsys.readouterr()
    assert codigo == 0

    dados = json.loads((ns / "delta.json").read_text(encoding="utf-8"))
    assert not any(d["chave"].startswith("engine.") for d in dados["valuation"])
    assert dados["engine"]["antes"]["hash"] == "aaaaaaaaaaaaaaaa"
    assert dados["engine"]["depois"]["hash"] == "bbbbbbbbbbbbbbbb"
    # mesmo engine.versao (9.9.9 nos dois) -> não é diff
    assert dados["engine"]["antes"]["versao"] == dados["engine"]["depois"]["versao"] == "9.9.9"


def test_valuation_mudou_sinal_para_sinais_e_gate(tmp_path, capsys):
    ns = tmp_path / "ns"
    ns.mkdir()
    res_base = _resultados("aaaaaaaaaaaaaaaa",
                            sinais={"economico": "SOBREAVALIADO"},
                            gate={"modo_recomendado": "SUMARIA"},
                            hurdle={"cenarios": {"ponderado": 51.71}})
    res_alvo = _resultados("bbbbbbbbbbbbbbbb",
                            sinais={"economico": "DENTRO_DA_FAIXA"},
                            gate={"modo_recomendado": "PADRAO"},
                            hurdle={"cenarios": {"ponderado": 116.46}})
    _montar_run(ns, "aaaaaaaaaaaaaaaa", resultados=res_base)
    _montar_run(ns, "bbbbbbbbbbbbbbbb", resultados=res_alvo)

    codigo = delta.main([str(ns), "--desde", "aaaaaaaaaaaaaaaa", "--ate", "bbbbbbbbbbbbbbbb"])
    capsys.readouterr()
    assert codigo == 0

    dados = json.loads((ns / "delta.json").read_text(encoding="utf-8"))
    por_chave = {d["chave"]: d for d in dados["valuation"]}

    assert por_chave["sinais.economico"]["antes"] == "SOBREAVALIADO"
    assert por_chave["sinais.economico"]["depois"] == "DENTRO_DA_FAIXA"
    assert por_chave["sinais.economico"]["mudou_sinal"] is True

    assert por_chave["gate.modo_recomendado"]["mudou_sinal"] is True

    assert por_chave["hurdle.cenarios.ponderado"]["antes"] == 51.71
    assert por_chave["hurdle.cenarios.ponderado"]["depois"] == 116.46
    assert por_chave["hurdle.cenarios.ponderado"]["mudou_sinal"] is False

    assert dados["resumo"]["sinais_mudaram"] is True


def test_valuation_tolerancia_numerica_nao_reporta_ruido(tmp_path, capsys):
    ns = tmp_path / "ns"
    ns.mkdir()
    res_base = _resultados("aaaaaaaaaaaaaaaa", hurdle={"cenarios": {"ponderado": 51.71}})
    res_alvo = _resultados("bbbbbbbbbbbbbbbb", hurdle={"cenarios": {"ponderado": 51.71 + 1e-12}})
    _montar_run(ns, "aaaaaaaaaaaaaaaa", resultados=res_base)
    _montar_run(ns, "bbbbbbbbbbbbbbbb", resultados=res_alvo)

    codigo = delta.main([str(ns), "--desde", "aaaaaaaaaaaaaaaa", "--ate", "bbbbbbbbbbbbbbbb"])
    capsys.readouterr()
    assert codigo == 0

    dados = json.loads((ns / "delta.json").read_text(encoding="utf-8"))
    assert not any(d["chave"] == "hurdle.cenarios.ponderado" for d in dados["valuation"])


# ----------------------------------------------------------------------------
# A.5 — decisão
# ----------------------------------------------------------------------------

def test_decisao_diff_simples(tmp_path, capsys):
    ns = tmp_path / "ns"
    ns.mkdir()
    dec_base = {"recomendacao": "WATCHLIST (DISTANTE)", "confianca": "MEDIA", "racional": "x"}
    dec_alvo = {"recomendacao": "WATCHLIST (PROXIMA)", "confianca": "MEDIA", "racional": "y"}
    _montar_run(ns, "aaaaaaaaaaaaaaaa", decisao=dec_base)
    _montar_run(ns, "bbbbbbbbbbbbbbbb", decisao=dec_alvo)

    codigo = delta.main([str(ns), "--desde", "aaaaaaaaaaaaaaaa", "--ate", "bbbbbbbbbbbbbbbb"])
    capsys.readouterr()
    assert codigo == 0

    dados = json.loads((ns / "delta.json").read_text(encoding="utf-8"))
    por_campo = {d["campo"]: d for d in dados["decisao"]}
    assert por_campo["recomendacao"]["antes"] == "WATCHLIST (DISTANTE)"
    assert por_campo["recomendacao"]["depois"] == "WATCHLIST (PROXIMA)"
    assert por_campo["racional"]["antes"] == "x"
    assert "nota" not in por_campo["recomendacao"]
    assert "confianca" not in por_campo  # inalterado, não aparece


def test_decisao_ausente_de_um_lado_gera_nota_sem_erro(tmp_path, capsys):
    ns = tmp_path / "ns"
    ns.mkdir()
    dec_alvo = {"recomendacao": "WATCHLIST", "confianca": "MEDIA", "racional": "y"}
    _montar_run(ns, "aaaaaaaaaaaaaaaa")  # sem estado.yaml congelado, sem <ns>/estado.yaml
    _montar_run(ns, "bbbbbbbbbbbbbbbb", decisao=dec_alvo)

    codigo = delta.main([str(ns), "--desde", "aaaaaaaaaaaaaaaa", "--ate", "bbbbbbbbbbbbbbbb"])
    capsys.readouterr()
    assert codigo == 0

    dados = json.loads((ns / "delta.json").read_text(encoding="utf-8"))
    por_campo = {d["campo"]: d for d in dados["decisao"]}
    assert por_campo["recomendacao"]["antes"] is None
    assert por_campo["recomendacao"]["depois"] == "WATCHLIST"
    assert "nota" in por_campo["recomendacao"]
    assert "base" in por_campo["recomendacao"]["nota"]


# ----------------------------------------------------------------------------
# A.6 — caso vazio (run vs ele mesmo) + delta.md
# ----------------------------------------------------------------------------

def test_caso_vazio_run_contra_si_mesmo(tmp_path, capsys):
    ns = tmp_path / "ns"
    ns.mkdir()
    claims = [{"id": "F-01", "tipo": "FATO", "texto": "x", "fonte": "y", "data": "2026-01-01"}]
    decisao = {"recomendacao": "WATCHLIST", "confianca": "MEDIA", "racional": "x"}
    _montar_run(ns, "aaaaaaaaaaaaaaaa", claims=claims, decisao=decisao)

    codigo = delta.main([str(ns), "--desde", "aaaaaaaaaaaaaaaa", "--ate", "aaaaaaaaaaaaaaaa"])
    capsys.readouterr()
    assert codigo == 0

    dados = json.loads((ns / "delta.json").read_text(encoding="utf-8"))
    assert dados["fatos"]["inputs"] == []
    assert dados["fatos"]["claims"] == {"adicionados": [], "modificados": [], "removidos": []}
    assert dados["premissas"] == []
    assert dados["valuation"] == []
    assert dados["decisao"] == []
    r = dados["resumo"]
    assert r["n_fatos"] == r["n_claims"] == r["n_premissas"] == r["n_valuation"] == r["n_decisao"] == 0
    assert r["sinais_mudaram"] is False

    md = (ns / "delta.md").read_text(encoding="utf-8")
    assert "nenhuma mudança" in md.lower()


def test_delta_md_tem_secoes_e_marca_mudanca_de_categoria(tmp_path, capsys):
    ns = tmp_path / "ns"
    ns.mkdir()
    res_base = _resultados("aaaaaaaaaaaaaaaa", sinais={"economico": "SOBREAVALIADO"})
    res_alvo = _resultados("bbbbbbbbbbbbbbbb", sinais={"economico": "DENTRO_DA_FAIXA"})
    _montar_run(ns, "aaaaaaaaaaaaaaaa", resultados=res_base)
    _montar_run(ns, "bbbbbbbbbbbbbbbb", resultados=res_alvo)

    codigo = delta.main([str(ns), "--desde", "aaaaaaaaaaaaaaaa", "--ate", "bbbbbbbbbbbbbbbb"])
    capsys.readouterr()
    assert codigo == 0

    md = (ns / "delta.md").read_text(encoding="utf-8")
    for secao in ("## Fatos", "## Premissas", "## Valuation", "## Decisão", "## Resumo"):
        assert secao in md
    assert "**MUDANÇA DE CATEGORIA**" in md


# ----------------------------------------------------------------------------
# B — Regressão FNV (arco P1 -> P3 real, engine v2.2.0)
# ----------------------------------------------------------------------------

pytestmark_fnv = pytest.mark.skipif(
    not os.path.isfile(FNV_INPUTS),
    reason="fixture FNV somente-leitura ausente fora deste ambiente de dev",
)


def _rodar_engine(inputs_path, out_dir):
    r = subprocess.run(
        [PYTHON, ENGINE_PATH, str(inputs_path), "--out", str(out_dir)],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, f"engine.py falhou: stdout={r.stdout!r} stderr={r.stderr!r}"
    with open(os.path.join(out_dir, "resultados.json"), "r", encoding="utf-8") as fh:
        return json.load(fh)


def _rodar_snapshot(ns):
    snapshot_path = os.path.join(REPO_ROOT, "scripts", "snapshot.py")
    r = subprocess.run([PYTHON, snapshot_path, str(ns)], capture_output=True, text=True)
    assert r.returncode == 0, f"snapshot.py falhou: stdout={r.stdout!r} stderr={r.stderr!r}"
    return r.stdout


def _derivar_p1(dados_p3):
    """P1 baseline (item 1 do brief): CAP base 17->15, bull 23->20;
    cap_teto_defensavel 23->20; remove m_terminal dos 3 cenários e
    justificativa_m_terminal."""
    p1 = copy.deepcopy(dados_p3)
    prem = p1["premissas"]
    prem["cenarios"]["base"]["cap"] = 15
    prem["cenarios"]["bull"]["cap"] = 20
    prem["cap_teto_defensavel"] = 20
    for nome in ("bear", "base", "bull"):
        prem["cenarios"][nome].pop("m_terminal", None)
    prem.pop("justificativa_m_terminal", None)
    return p1


@pytest.fixture(scope="module")
def arco_fnv(tmp_path_factory):
    if not os.path.isfile(FNV_INPUTS):
        pytest.skip("fixture FNV somente-leitura ausente fora deste ambiente de dev")

    tmp = tmp_path_factory.mktemp("fnv_delta")
    ns = tmp / "FNV"
    ns.mkdir()

    with open(FNV_INPUTS, "r", encoding="utf-8") as fh:
        dados_p3 = yaml.safe_load(fh)
    dados_p1 = _derivar_p1(dados_p3)

    # P1 (base)
    inputs_p1 = ns / "inputs.yaml"
    _escrever_yaml(inputs_p1, dados_p1)
    res_p1 = _rodar_engine(inputs_p1, ns / "saida_FNV")
    _escrever_yaml(ns / "claims.yaml", {"claims": [
        {"id": "F-01", "tipo": "FATO", "texto": "LPA ajustado FY2025 = 5,58", "fonte": "10-K", "data": "2026-03-10"},
        {"id": "F-02", "tipo": "FATO", "texto": "Preco atual 200,61", "fonte": "stockanalysis.com", "data": "2026-07-15"},
    ]})
    _rodar_snapshot(ns)
    hash_p1 = res_p1["engine"]["hash_inputs"]

    # P3 (alvo) — inputs REAIS da sessão, sem edição
    _escrever_yaml(inputs_p1, dados_p3)
    res_p3 = _rodar_engine(inputs_p1, ns / "saida_FNV")
    _escrever_yaml(ns / "claims.yaml", {"claims": [
        {"id": "F-01", "tipo": "FATO", "texto": "LPA ajustado FY2025 = 5,58 (non-GAAP)", "fonte": "10-K", "data": "2026-03-10"},
        {"id": "F-02", "tipo": "FATO", "texto": "Preco atual 200,61", "fonte": "stockanalysis.com", "data": "2026-07-15"},
        {"id": "F-31", "tipo": "FATO", "texto": "m_terminal calibrado no P/B implicito realizado", "fonte": "dossie.md", "data": "2026-07-15"},
    ]})
    _rodar_snapshot(ns)
    hash_p3 = res_p3["engine"]["hash_inputs"]

    saida = ns / "delta_saida"
    r = subprocess.run(
        [PYTHON, DELTA_PATH, str(ns), "--desde", hash_p1, "--ate", hash_p3, "--saida", str(saida)],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, f"delta.py falhou: stdout={r.stdout!r} stderr={r.stderr!r}"

    with open(saida / "delta.json", "r", encoding="utf-8") as fh:
        delta_json = json.load(fh)

    return {
        "ns": ns, "hash_p1": hash_p1, "hash_p3": hash_p3,
        "res_p1": res_p1, "res_p3": res_p3, "delta": delta_json,
        "saida": saida,
    }


@pytest.mark.skipif(not os.path.isfile(FNV_INPUTS), reason="fixture FNV ausente")
def test_baseline_p1_sanidade(arco_fnv):
    """Item 3 do brief: valores REAIS registrados da sessão FNV P1."""
    res_p1 = arco_fnv["res_p1"]
    hurdle = res_p1["hurdle"]["cenarios"]["ponderado"]
    central = res_p1["economico"]["central_ponderado"]
    assert abs(hurdle - 51.71) <= 0.02, f"hurdle ponderado P1 = {hurdle}, esperado 51.71"
    assert abs(central - 73.35) <= 0.02, f"central econômico P1 = {central}, esperado 73.35"


@pytest.mark.skipif(not os.path.isfile(FNV_INPUTS), reason="fixture FNV ausente")
def test_delta_sinais_e_gate(arco_fnv):
    d = arco_fnv["delta"]
    por_chave = {x["chave"]: x for x in d["valuation"]}

    sinal = por_chave["sinais.economico"]
    assert sinal["antes"] == "SOBREAVALIADO"
    assert sinal["depois"] == "DENTRO_DA_FAIXA"
    assert sinal["mudou_sinal"] is True

    gate = por_chave["gate.modo_recomendado"]
    assert gate["antes"] == "SUMARIA"
    assert gate["depois"] == "PADRAO"
    assert gate["mudou_sinal"] is True

    hurdle = por_chave["hurdle.cenarios.ponderado"]
    assert abs(hurdle["antes"] - 51.71) <= 0.02
    assert abs(hurdle["depois"] - 116.46) <= 0.02

    assert d["resumo"]["sinais_mudaram"] is True


@pytest.mark.skipif(not os.path.isfile(FNV_INPUTS), reason="fixture FNV ausente")
def test_delta_premissas_cap_e_m_terminal(arco_fnv):
    d = arco_fnv["delta"]
    por_chave = {x["chave"]: x for x in d["premissas"]}

    cap = por_chave["premissas.cenarios.base.cap"]
    assert cap["antes"] == 15
    assert cap["depois"] == 17

    m_term = por_chave["premissas.cenarios.base.m_terminal"]
    assert m_term["antes"] is None
    assert m_term["depois"] == 4.0


@pytest.mark.skipif(not os.path.isfile(FNV_INPUTS), reason="fixture FNV ausente")
def test_delta_claims(arco_fnv):
    d = arco_fnv["delta"]
    bloco = d["fatos"]["claims"]
    assert bloco["adicionados"] == ["F-31"]
    assert bloco["modificados"] == ["F-02"] or bloco["modificados"] == ["F-01"]
    # F-01 teve o texto alterado ("non-GAAP" adicionado); F-02 ficou idêntico
    assert "F-01" in bloco["modificados"]
    assert "F-02" not in bloco["modificados"]
    assert bloco["removidos"] == []


@pytest.mark.skipif(not os.path.isfile(FNV_INPUTS), reason="fixture FNV ausente")
def test_delta_caso_vazio_alvo_contra_si_mesmo(arco_fnv):
    ns = arco_fnv["ns"]
    hash_p3 = arco_fnv["hash_p3"]
    saida = arco_fnv["saida"].parent / "delta_vazio"
    r = subprocess.run(
        [PYTHON, DELTA_PATH, str(ns), "--desde", hash_p3, "--ate", hash_p3, "--saida", str(saida)],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, f"stdout={r.stdout!r} stderr={r.stderr!r}"
    with open(saida / "delta.json", "r", encoding="utf-8") as fh:
        dados = json.load(fh)
    assert dados["fatos"]["inputs"] == []
    assert dados["premissas"] == []
    assert dados["valuation"] == []
    assert dados["resumo"]["sinais_mudaram"] is False
