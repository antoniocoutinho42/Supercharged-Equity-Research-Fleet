"""A paridade Python↔JS por caso, no build (item 6, Task 2, D2 do plano
docs/superpowers/plans/2026-09-16-v4-item6-fixture-sintetica.md).

A verificação é da integração (`skills/er-valuation/scripts/paridade.py`): roda a fachada do
espelho em node sobre o caso e compara com o `resultados` pelo mesmo comparador do badge. O
builder a chama uma vez por build e o QC converte o veredito em achado:
- com node, uma entrega legítima verifica `ok` e emite sem achado de paridade;
- um `resultados` adulterado num número que o comparador lê dá `divergente`, e nada é emitido
  (HARD FAIL `paridade_divergente`);
- sem node — o executável forçado a ausente pelo PATH do processo do builder, sem desinstalar
  nada —, a entrega emite com o REQUIRED DISCLOSURE `paridade_nao_verificada_no_build`.

Os testes que precisam de node PULAM sem ele, com a razão; o CI tem node e sempre os roda.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
SCRIPTS = RAIZ / "skills" / "er-relatorio" / "scripts"
BUILDER = SCRIPTS / "builder.py"

sys.path.insert(0, str(SCRIPTS))
import builder  # noqa: E402
import placeholders  # noqa: E402
import qc  # noqa: E402

sys.path.insert(0, str(RAIZ / "tests"))
import relatorio_apoio as apoio  # noqa: E402
from test_espelho_js import RAZAO, SEM_NODE  # noqa: E402

# `relatorio_apoio` já pôs `er-valuation/scripts` no path: testes não são a camada do relatório.
import paridade  # noqa: E402

FIXTURE = "caso_minimo_firm.json"
ENV_UTF8 = {**os.environ, "PYTHONUTF8": "1", "PYTHONDONTWRITEBYTECODE": "1", "PYTHONIOENCODING": "utf-8"}
MENSAGENS = placeholders.carregar_dicionario("pt-BR")["qc"]


def _rodar_builder(raiz: Path, env: dict = ENV_UTF8) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(BUILDER), str(raiz)], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", env=env, timeout=180)


def _achados(raiz: Path) -> list:
    return json.loads((raiz / "qc.json").read_text(encoding="utf-8"))["achados"]


def _da_paridade(achados: list) -> list:
    return [(achado["nivel"], achado["codigo"]) for achado in achados if achado["codigo"].startswith("paridade_")]


def test_os_estados_do_veredito_sao_os_mesmos_nos_dois_lados_do_contrato():
    """O veredito atravessa a fronteira da E3 como dado: os três estados da integração são os
    que o QC do relatório converte, na mesma ordem."""
    assert qc.ESTADOS_DA_PARIDADE == paridade.ESTADOS


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_com_node_a_entrega_legitima_verifica_ok_e_emite_sem_achado_de_paridade(tmp_path):
    entrega_dict = apoio.montar_entrega(FIXTURE)
    assert paridade.verificar(entrega_dict["caso"], entrega_dict["resultados"]) == {"estado": paridade.ESTADO_OK}

    raiz = tmp_path / "legitima"
    apoio.escrever_raiz(raiz, entrega_dict)
    resultado = _rodar_builder(raiz)

    assert resultado.returncode == 0, resultado.stdout + resultado.stderr
    assert (raiz / "relatorio.html").exists()
    assert _da_paridade(_achados(raiz)) == []


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_um_resultados_adulterado_num_numero_que_o_comparador_le_diverge_e_nada_e_emitido(tmp_path):
    """O preço publicado do cenário, 1% acima do que o motor produziu: o hash do caso continua
    batendo e nenhuma outra regra do QC o lê como defeito — o único HARD FAIL é a paridade, que
    nomeia a chave e os dois números."""
    entrega_dict = apoio.montar_entrega(FIXTURE)
    publicado = entrega_dict["resultados"]["cenarios"]["base"]["valor"]["preco_acao"]
    entrega_dict["resultados"]["cenarios"]["base"]["valor"]["preco_acao"] = publicado * 1.01

    veredito = paridade.verificar(entrega_dict["caso"], entrega_dict["resultados"])
    assert veredito["estado"] == paridade.ESTADO_DIVERGENTE and veredito["erro"] is None
    assert [(item["cenario"], item["chave"]) for item in veredito["divergencias"]] == [("base", "valor.preco_acao")]

    raiz = tmp_path / "adulterada"
    apoio.escrever_raiz(raiz, entrega_dict)
    resultado = _rodar_builder(raiz)

    assert resultado.returncode == 2, resultado.stdout + resultado.stderr
    assert not (raiz / "relatorio.html").exists() and not (raiz / "ficha-tecnica.json").exists()
    achados = _achados(raiz)
    assert [achado["codigo"] for achado in achados if achado["nivel"] == "HARD_FAIL"] == ["paridade_divergente"]
    (achado,) = [achado for achado in achados if achado["codigo"] == "paridade_divergente"]
    assert achado["params"]["quantidade"] == 1
    assert "valor.preco_acao" in achado["params"]["divergencias"] and "valor.preco_acao" in achado["mensagem"]


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_uma_verificacao_que_nao_fecha_diverge_com_a_razao_e_nunca_vale_como_ok():
    """Falha fechada: a fachada recusa um `resultados` de outro contrato — a verificação não
    chega a comparar número nenhum, e o veredito é `divergente` com a razão."""
    entrega_dict = apoio.montar_entrega(FIXTURE)
    outro_contrato = {**entrega_dict["resultados"], "versao_contrato": "resultados/9"}

    veredito = paridade.verificar(entrega_dict["caso"], outro_contrato)

    assert veredito["estado"] == paridade.ESTADO_DIVERGENTE and veredito["divergencias"] == []
    assert "contrato_desconhecido" in veredito["erro"]
    achado = qc._achado_da_paridade(veredito)
    assert (achado.nivel, achado.codigo) == ("HARD_FAIL", "paridade_divergente")
    assert "contrato_desconhecido" in achado.params["divergencias"]


def test_sem_node_a_entrega_emite_com_o_disclosure_da_paridade_nao_verificada(tmp_path):
    """O PATH do processo do builder aponta para um diretório vazio: o interpretador é chamado
    pelo caminho absoluto, e a verificação da integração não acha node. A entrega emite, e o
    aviso sai no `qc.json` e na Tese."""
    entrega_dict = apoio.montar_entrega(FIXTURE)
    raiz = tmp_path / "sem_node"
    apoio.escrever_raiz(raiz, entrega_dict)
    sem_node = tmp_path / "path_sem_node"
    sem_node.mkdir()

    resultado = _rodar_builder(raiz, env={**ENV_UTF8, "PATH": str(sem_node)})

    assert resultado.returncode == 0, resultado.stdout + resultado.stderr
    assert _da_paridade(_achados(raiz)) == [("REQUIRED_DISCLOSURE", "paridade_nao_verificada_no_build")]
    html = (raiz / "relatorio.html").read_text(encoding="utf-8")
    assert MENSAGENS["paridade_nao_verificada_no_build"] in apoio.prosa_da_pagina(html)


def test_uma_verificacao_sem_veredito_e_codigo_1_e_nada_e_escrito(tmp_path, monkeypatch, capsys):
    """A CLI da integração que nem devolve veredito — aqui, um caminho que não existe — não é um
    caso que diverge: é a verificação que não rodou. Código 1, a razão em stderr, e nenhum
    arquivo na raiz."""
    entrega_dict = apoio.montar_entrega(FIXTURE)
    raiz = tmp_path / "sem_veredito"
    apoio.escrever_raiz(raiz, entrega_dict)
    monkeypatch.setitem(builder.ASSETS_DA_INTEGRACAO, "paridade", tmp_path / "nao_existe.py")

    assert builder.main([str(raiz)]) == 1
    assert "a verificação de paridade saiu com código" in capsys.readouterr().err
    assert not (raiz / "qc.json").exists() and not (raiz / "relatorio.html").exists()
