"""O ledger no contrato `entrega/1`, o consenso e o confronto, e as regras da §11 que dependem do
ledger (fatia 5E, item 5, Task 2); e a aba Evidência, o consenso na Conclusão, os avisos da Tese
com a prosa resolvida e a ficha técnica em arquivo (Task 3).

Ver docs/superpowers/plans/2026-09-14-v4-item5e-evidencia.md: D1 (a forma de `ledger/1`, lida do
contrato do `er-evidencia`), D3 (as regras), D4 (o consenso), D5 (o confronto) e D6
(`ficha_tecnica` sai do contrato). Duas famílias de teste, como na 5D:

- FORMA, código 1 (`entrega.carregar`): chave desconhecida, campo obrigatório ausente, tipo errado
  e vocabulário fechado — a recusa nomeia o campo e sugere por `difflib`. Uma recusa por nível
  novo, e as condicionais de D1, D4 e D5.
- CONTEÚDO (`qc.avaliar`), código 2 quando HARD FAIL: cada regra de D3 com um caso que dispara e
  um vizinho que não dispara.

Os testes também não escrevem doutrina: o estatuto que é estimativa, o que exige fórmula, a
materialidade que exige disclosure, a classe, o tipo de localizador e a âncora saem das flags e
dos vocabulários do contrato lido. Renomear um estatuto no contrato não deixa um teste daqui verde
por acidente.

Entregas vêm de `tests/relatorio_apoio.py`, que compõe o ledger padrão derivado do mapa
`catalogo.insumos_do_caso` sobre o caso composto; cada teste recebe a sua cópia.
"""

import copy
import functools
import json
import math
import os
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
SCRIPTS = RAIZ / "skills" / "er-relatorio" / "scripts"
BUILDER = SCRIPTS / "builder.py"

sys.path.insert(0, str(SCRIPTS))
import builder  # noqa: E402
import entrega  # noqa: E402
import exhibits  # noqa: E402
import placeholders  # noqa: E402
import qc  # noqa: E402
import render  # noqa: E402

sys.path.insert(0, str(RAIZ / "tests"))
import relatorio_apoio as apoio  # noqa: E402
# A Task 3 lê a página como a aba Tese a lê: a mesma árvore do texto que o analista vê, sobre
# `apoio.prosa_da_pagina`, e a mesma variante de fronteira de escopo — uma leitura só.
from test_relatorio_tese import (  # noqa: E402
    _aba, _com_fronteira_de_escopo, _secao, _secoes, _titulo, _todos, _um, _visivel)

CATALOGO = apoio.CATALOGO
CONTRATO = apoio.CONTRATO_LEDGER
DICIONARIO = placeholders.carregar_dicionario("pt-BR")
CASOS = sorted(p.name for p in apoio.FIXTURES.glob("caso_*.json"))
FIXTURE = "caso_minimo_firm.json"
# Um caso com lista (`mercado.beta_observado`) e com número que não é insumo (os pontos de grade).
FIXTURE_COM_LISTA_E_GRADE = "caso_reversa_firm.json"
ENV_UTF8 = {**os.environ, "PYTHONUTF8": "1", "PYTHONDONTWRITEBYTECODE": "1", "PYTHONIOENCODING": "utf-8"}

_VOCABULARIOS = CONTRATO["vocabularios"]
ESTATUTO_OBSERVADO = apoio.ESTATUTO_OBSERVADO
ESTATUTO_COM_FORMULA = next(nome for nome, flags in _VOCABULARIOS["estatutos"].items() if flags["exige_formula"])
ESTATUTO_ESTIMADO = next(nome for nome, flags in _VOCABULARIOS["estatutos"].items()
                         if flags["e_estimativa"] and not flags["exige_formula"])
MATERIALIDADE_COM_DISCLOSURE = next(nome for nome, flags in _VOCABULARIOS["materialidades"].items()
                                    if flags["exige_disclosure"])
MATERIALIDADE_SEM_DISCLOSURE = next(nome for nome, flags in _VOCABULARIOS["materialidades"].items()
                                    if not flags["exige_disclosure"])
CLASSE = _VOCABULARIOS["classes_de_fonte"][0]
TIPO_DE_LOCALIZADOR = _VOCABULARIOS["tipos_de_localizador"][0]
ANCORA = _VOCABULARIOS["ancoras_do_consenso"][0]

CODIGOS_DO_LEDGER = frozenset({
    "insumos_do_caso_desconhecidos", "insumo_sem_proveniencia", "usado_em_fora_dos_insumos",
    "insumo_nao_reconciliado", "conflito_de_fontes_silenciado", "referencia_fora_do_ledger",
    "dataset_sem_proveniencia", "insumo_estimado", "sem_contraprova_independente", "lacuna_material",
    "consenso_indisponivel", "concentracao_de_fontes",
})


def _rodar_builder(raiz: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(BUILDER), str(raiz)],
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace", env=ENV_UTF8, timeout=120)


def _ler_qc(raiz: Path) -> dict:
    return json.loads((raiz / "qc.json").read_text(encoding="utf-8"))


@functools.lru_cache(maxsize=None)
def _entrega_serializada(fixture: str) -> str:
    """`montar_entrega` cacheado (roda o motor por subprocesso), devolvido como JSON para que
    cada teste receba a sua cópia — quase todos adulteram a entrega."""
    return json.dumps(apoio.montar_entrega(fixture), ensure_ascii=False)


def _entrega(fixture: str = FIXTURE) -> dict:
    return json.loads(_entrega_serializada(fixture))


def _achados(entrega_dict: dict, catalogo: dict = CATALOGO, contrato: dict | None = CONTRATO) -> list:
    return qc.avaliar(entrega_dict, catalogo, contrato, html=None)


def _do_codigo(achados: list, codigo: str) -> list:
    return [a for a in achados if a.codigo == codigo]


def _como(achados: list) -> list:
    return [(a.nivel, a.onde, a.params) for a in achados]


def _carregar(entrega_dict: dict, tmp_path: Path) -> dict:
    raiz = tmp_path / "raiz"
    apoio.escrever_raiz(raiz, entrega_dict)
    return entrega.carregar(raiz, CONTRATO)


def _registros(entrega_dict: dict) -> list:
    return entrega_dict["ledger"]["registros"]


def _que_sustenta(entrega_dict: dict, caminho: str) -> dict:
    (registro,) = [r for r in _registros(entrega_dict) if caminho in r.get("usado_em", [])]
    return registro


def _indice(entrega_dict: dict, registro: dict) -> int:
    return next(indice for indice, r in enumerate(_registros(entrega_dict)) if r is registro)


def _caminho_da_premissa_decisiva(entrega_dict: dict) -> str:
    cenario = entrega_dict["resultados"]["manchete"]["cenario"]
    return f"cenarios.{cenario}.premissas.{entrega_dict['analise']['premissas_decisivas'][0]['chave']}"


def _contraprova_de(entrega_dict: dict, alvo: dict) -> dict:
    (registro,) = [r for r in _registros(entrega_dict) if r.get("contraprova_de") == alvo["id"]]
    return registro


def _renomear(objeto: dict, de: str, para: str) -> None:
    objeto[para] = objeto.pop(de)


def _renomeada(objeto: dict, de: str, para: str) -> dict:
    copia = copy.deepcopy(objeto)
    _renomear(copia, de, para)
    return copia


def _primeiro(entrega_dict: dict) -> dict:
    return _registros(entrega_dict)[0]


def _lacuna(**campos) -> dict:
    lacuna = {"id": "segmentos", "descricao": "A companhia não publica a abertura por segmento.",
              "materialidade": MATERIALIDADE_SEM_DISCLOSURE, "tratamento": "A análise usa o consolidado."}
    lacuna.update(campos)
    return lacuna


def _confronto(**divergencia) -> dict:
    item = {"item": "Crescimento de longo prazo", "classificacao": "premissa_revista",
            "anterior": "6,0% ao ano", "atual": "5,0% ao ano",
            "explicacao": "A capacidade instalada limita a expansão."}
    item.update(divergencia)
    return {"analise_fornecida": {"identificacao": "Relatório de cobertura anterior", "data": "2026-03-02"},
            "divergencias": [item]}


def _confronto_sem(campo: str) -> dict:
    confronto = _confronto()
    del confronto["divergencias"][0][campo]
    return confronto


def _dataset(ledger: list) -> dict:
    return {"ledger": ledger, "x": ["2024", "2025"], "campos": {"receita": [100.0, 110.0]}}


# ==========================================================================
# FORMA (código 1): uma recusa por nível novo e as condicionais de D1, D4 e D5.
# ==========================================================================

_RECUSAS_DE_FORMA = [
    # ledger
    pytest.param(lambda e: e.update(ledger=[]),
                 ["'ledger' não é um objeto"], id="ledger-lista-da-forma-antiga"),
    pytest.param(lambda e: _renomear(e["ledger"], "lacunas", "lacuna"),
                 ["chave desconhecida em 'ledger'", "'lacuna'", "Você quis dizer 'lacunas'?"],
                 id="ledger-chave-desconhecida"),
    pytest.param(lambda e: e["ledger"].pop("registros"),
                 ["campo obrigatório ausente em 'ledger': 'registros'"], id="ledger-campo-obrigatorio"),
    pytest.param(lambda e: e["ledger"].update(versao_contrato="ledger/0"),
                 ["'ledger.versao_contrato' incompatível", "'ledger/0'"], id="ledger-versao"),
    # registro
    pytest.param(lambda e: _renomear(_primeiro(e), "justificativa_da_fonte", "justificativa"),
                 ["chave desconhecida em 'ledger.registros.0'", "'justificativa'",
                  "Você quis dizer 'justificativa_da_fonte'?"],
                 id="registro-chave-desconhecida"),
    pytest.param(lambda e: _primeiro(e).pop("periodo"),
                 ["campo obrigatório ausente em 'ledger.registros.0': 'periodo'"], id="registro-campo-obrigatorio"),
    pytest.param(lambda e: _primeiro(e).update(claim=7),
                 ["'ledger.registros.0.claim' ausente ou vazio"], id="registro-claim-que-nao-e-texto"),
    pytest.param(lambda e: _primeiro(e).update(moeda=""),
                 ["'ledger.registros.0.moeda'"], id="registro-moeda-vazia"),
    pytest.param(lambda e: _primeiro(e).update(valor="55,0"),
                 ["'ledger.registros.0.valor'", "número"], id="registro-valor-texto"),
    pytest.param(lambda e: _primeiro(e).update(valor=True),
                 ["'ledger.registros.0.valor'", "número"], id="registro-valor-booleano-nao-e-numero"),
    pytest.param(lambda e: _primeiro(e).update(estatuto=ESTATUTO_OBSERVADO + "x"),
                 ["'ledger.registros.0.estatuto' fora do vocabulário", f"Você quis dizer '{ESTATUTO_OBSERVADO}'?"],
                 id="registro-estatuto"),
    pytest.param(lambda e: _primeiro(e).update(data_acesso="11/09/2026"),
                 ["'ledger.registros.0.data_acesso'", "AAAA-MM-DD"], id="registro-data-fora-do-formato"),
    pytest.param(lambda e: _primeiro(e).update(data_acesso="2026-02-30"),
                 ["'ledger.registros.0.data_acesso'", "AAAA-MM-DD"], id="registro-data-inexistente"),
    pytest.param(lambda e: _primeiro(e).update(formula="receita menos custos"),
                 ["'ledger.registros.0.formula'", f"'{ESTATUTO_OBSERVADO}'"],
                 id="registro-formula-sem-estatuto-que-a-exige"),
    pytest.param(lambda e: _primeiro(e).update(estatuto=ESTATUTO_COM_FORMULA),
                 ["campo obrigatório ausente em 'ledger.registros.0': 'formula'"],
                 id="registro-estatuto-que-exige-formula-sem-formula"),
    pytest.param(lambda e: _primeiro(e).update(insumos=[_registros(e)[1]["id"]]),
                 ["'ledger.registros.0.insumos'", f"'{ESTATUTO_OBSERVADO}'"],
                 id="registro-insumos-sem-estatuto-que-exige-formula"),
    pytest.param(lambda e: _primeiro(e).update(valor=None),
                 ["'ledger.registros.0.usado_em'", "'valor'"], id="registro-usado-em-com-valor-nulo"),
    pytest.param(lambda e: _primeiro(e).update(usado_em=[]),
                 ["'ledger.registros.0.usado_em'"], id="registro-usado-em-vazio"),
    pytest.param(lambda e: _registros(e)[1].update(id=_primeiro(e)["id"]),
                 ["'ledger.registros' repete o id"], id="registro-id-repetido"),
    pytest.param(lambda e: _primeiro(e).update(contraprova_de=[_registros(e)[1]["id"]]),
                 ["'ledger.registros.0.contraprova_de' ausente ou vazio"], id="registro-contraprova-de-que-nao-e-id"),
    # fonte
    pytest.param(lambda e: _renomear(_primeiro(e)["fonte"], "identidade", "identidad"),
                 ["chave desconhecida em 'ledger.registros.0.fonte'", "'identidad'", "Você quis dizer 'identidade'?"],
                 id="fonte-chave-desconhecida"),
    pytest.param(lambda e: _primeiro(e)["fonte"].update(classe=CLASSE + "s"),
                 ["'ledger.registros.0.fonte.classe' fora do vocabulário", f"Você quis dizer '{CLASSE}'?"],
                 id="fonte-classe"),
    # localizador
    pytest.param(lambda e: _primeiro(e)["localizador"].update(parametro={"symbol": "SINT3"}),
                 ["chave desconhecida em 'ledger.registros.0.localizador'", "'parametro'",
                  "Você quis dizer 'parametros'?"],
                 id="localizador-chave-desconhecida"),
    pytest.param(lambda e: _primeiro(e)["localizador"].update(tipo=TIPO_DE_LOCALIZADOR + "s"),
                 ["'ledger.registros.0.localizador.tipo' fora do vocabulário",
                  f"Você quis dizer '{TIPO_DE_LOCALIZADOR}'?"],
                 id="localizador-tipo"),
    pytest.param(lambda e: _primeiro(e)["localizador"].update(parametros="symbol=SINT3"),
                 ["'ledger.registros.0.localizador.parametros' não é um objeto"], id="localizador-parametros"),
    # reconciliacao e conflito
    pytest.param(lambda e: _primeiro(e).update(reconciliacao={"text": "A fonte arredonda o fechamento."}),
                 ["chave desconhecida em 'ledger.registros.0.reconciliacao'", "'text'", "Você quis dizer 'texto'?"],
                 id="reconciliacao"),
    pytest.param(lambda e: _primeiro(e).update(conflito={"vencedor": _primeiro(e)["id"]}),
                 ["campo obrigatório ausente em 'ledger.registros.0.conflito': 'razao'"], id="conflito"),
    # lacuna
    pytest.param(lambda e: e["ledger"].update(lacunas=[_renomeada(_lacuna(), "descricao", "descrição")]),
                 ["chave desconhecida em 'ledger.lacunas.0'", "'descrição'", "Você quis dizer 'descricao'?"],
                 id="lacuna-chave-desconhecida"),
    pytest.param(lambda e: e["ledger"].update(lacunas=[_lacuna(materialidade=MATERIALIDADE_COM_DISCLOSURE + "s")]),
                 ["'ledger.lacunas.0.materialidade' fora do vocabulário",
                  f"Você quis dizer '{MATERIALIDADE_COM_DISCLOSURE}'?"],
                 id="lacuna-materialidade"),
    pytest.param(lambda e: e["ledger"].update(lacunas=[_lacuna(), _lacuna()]),
                 ["'ledger.lacunas' repete o id 'segmentos'"], id="lacuna-id-repetido"),
    # consenso (D4)
    pytest.param(lambda e: e["analise"].pop("consenso"),
                 ["campo obrigatório ausente em 'analise': 'consenso'"], id="consenso-ausente-da-analise"),
    pytest.param(lambda e: _renomear(e["analise"]["consenso"], "registros", "registro"),
                 ["chave desconhecida em 'analise.consenso'", "'registro'", "Você quis dizer 'registros'?"],
                 id="consenso-chave-desconhecida"),
    pytest.param(lambda e: e["analise"]["consenso"].update(
                     ausente={"ancora": ANCORA, "razao": "Nenhum provedor cobre a companhia."}),
                 ["'analise.consenso' declara 'registros' e 'ausente'"], id="consenso-os-dois"),
    pytest.param(lambda e: e["analise"].update(consenso={}),
                 ["'analise.consenso' não declara 'registros' nem 'ausente'"], id="consenso-nenhum"),
    pytest.param(lambda e: e["analise"].update(consenso={"registros": []}),
                 ["'analise.consenso.registros'"], id="consenso-registros-vazio"),
    pytest.param(lambda e: e["analise"].update(
                     consenso={"ausente": {"ancora": ANCORA + "s", "razao": "Nenhum provedor cobre a companhia."}}),
                 ["'analise.consenso.ausente.ancora' fora do vocabulário", f"Você quis dizer '{ANCORA}'?"],
                 id="consenso-ancora"),
    pytest.param(lambda e: e["analise"].update(consenso={"ausente": {"ancora": ANCORA}}),
                 ["campo obrigatório ausente em 'analise.consenso.ausente': 'razao'"], id="consenso-ausente-sem-razao"),
    # confronto (D5)
    pytest.param(lambda e: e.update(confronto=_renomeada(_confronto(), "divergencias", "divergencia")),
                 ["chave desconhecida em 'confronto'", "'divergencia'", "Você quis dizer 'divergencias'?"],
                 id="confronto-chave-desconhecida"),
    pytest.param(lambda e: e.update(confronto=dict(
                     _confronto(), analise_fornecida={"identificacao": "Relatório anterior", "data": "março"})),
                 ["'confronto.analise_fornecida.data'", "AAAA-MM-DD"], id="confronto-data"),
    pytest.param(lambda e: e.update(confronto=_confronto(classificacao="dado novo")),
                 ["'confronto.divergencias.0.classificacao' fora do vocabulário", "Você quis dizer 'dado_novo'?"],
                 id="confronto-classificacao"),
    pytest.param(lambda e: e.update(confronto=_confronto_sem("explicacao")),
                 ["campo obrigatório ausente em 'confronto.divergencias.0': 'explicacao'"],
                 id="confronto-divergencia-campo-obrigatorio"),
    pytest.param(lambda e: e["analise"].update(mudou_desde_analise_fornecida={"linhas": ["A margem subiu."]}),
                 ["'analise.mudou_desde_analise_fornecida'", "'confronto'"], id="mudou-sem-confronto"),
    # ficha técnica (D6)
    pytest.param(lambda e: e.update(ficha_tecnica={}),
                 ["chave desconhecida em 'entrega'", "'ficha_tecnica'"], id="ficha-tecnica-fora-do-contrato"),
    # dados.<id>.ledger
    pytest.param(lambda e: e.update(dados={"fin": _dataset([3])}),
                 ["'dados.fin.ledger'"], id="dataset-ledger-com-item-que-nao-e-id"),
]


@pytest.mark.parametrize("adulterar,trechos", _RECUSAS_DE_FORMA)
def test_forma_do_ledger_do_consenso_e_do_confronto_e_recusa_de_contrato_nomeada(adulterar, trechos, tmp_path):
    entrega_dict = _entrega()
    _carregar(entrega_dict, tmp_path)  # o vizinho: sem a adulteração, o contrato aceita

    adulterar(entrega_dict)
    with pytest.raises(entrega.EntregaInvalida) as erro:
        _carregar(entrega_dict, tmp_path)
    for trecho in trechos:
        assert trecho in str(erro.value), str(erro.value)


def test_toda_forma_opcional_valida_passa_no_contrato(tmp_path):
    """O vizinho das recusas: fórmula e insumos com o estatuto que exige fórmula, parâmetros do
    localizador, reconciliação, conflito, contraprova, as duas materialidades, o consenso ausente,
    o confronto com o que mudou e um dataset que cita registros."""
    entrega_dict = _entrega()
    alvo = _que_sustenta(entrega_dict, "preco.valor")
    _registros(entrega_dict).append(apoio.registro_do_ledger(
        "ebitda-calculado", "EBITDA de 2025", "Demonstrações auditadas", 1000.0,
        estatuto=ESTATUTO_COM_FORMULA, formula="lucro operacional mais depreciação", insumos=[alvo["id"]],
        moeda="BRL", localizador={"tipo": TIPO_DE_LOCALIZADOR, "valor": "dfp-2025", "parametros": {"nota": "12"}},
        reconciliacao={"texto": "A DFP consolida a controlada adquirida em março."},
        conflito={"vencedor": alvo["id"], "razao": "A bolsa é a fonte primária do preço."},
        contraprova_de=alvo["id"]))
    entrega_dict["ledger"]["lacunas"] = [_lacuna(), _lacuna(id="guidance", materialidade=MATERIALIDADE_COM_DISCLOSURE)]
    entrega_dict["analise"]["consenso"] = {"ausente": {"ancora": ANCORA, "razao": "Nenhum provedor cobre a companhia."}}
    entrega_dict["confronto"] = _confronto()
    entrega_dict["analise"]["mudou_desde_analise_fornecida"] = {"linhas": ["O crescimento de longo prazo foi revisto."]}
    entrega_dict["dados"] = {"fin": _dataset([alvo["id"]])}

    carregada = _carregar(entrega_dict, tmp_path)

    assert carregada["confronto"] == _confronto()
    assert entrega.CLASSIFICACOES_DE_DIVERGENCIA == {"dado_novo", "premissa_revista", "erro_anterior",
                                                     "pergunta_resolvida"}


def test_recusa_de_forma_do_ledger_sai_pelo_codigo_1_sem_escrever_nada(tmp_path):
    entrega_dict = _entrega()
    _primeiro(entrega_dict)["fonte"]["classe"] = CLASSE + "s"
    raiz = tmp_path / "classe_errada"
    apoio.escrever_raiz(raiz, entrega_dict)

    resultado = _rodar_builder(raiz)

    assert resultado.returncode == 1, resultado.stdout + resultado.stderr
    assert not (raiz / "qc.json").exists()
    assert not (raiz / "relatorio.html").exists()
    assert "'ledger.registros.0.fonte.classe'" in resultado.stderr
    assert f"'{CLASSE}'" in resultado.stderr


def test_o_builder_le_o_contrato_do_ledger_do_er_evidencia_pela_constante():
    assert builder.ASSETS_DA_INTEGRACAO["contrato_ledger"] == (
        RAIZ / "skills" / "er-evidencia" / "assets" / "contrato_ledger.json")


@pytest.mark.parametrize("conteudo", [
    pytest.param(None, id="ausente"),
    pytest.param("{", id="json-invalido"),
    pytest.param(json.dumps({"versao_contrato": "ledger/1"}), id="sem-niveis-nem-vocabularios"),
])
def test_contrato_do_ledger_ilegivel_e_codigo_1_sem_escrever_nada(conteudo, tmp_path, monkeypatch, capsys):
    raiz = tmp_path / "raiz"
    apoio.escrever_raiz(raiz, _entrega())
    contrato = tmp_path / "contrato_ledger.json"
    if conteudo is not None:
        contrato.write_text(conteudo, encoding="utf-8")
    monkeypatch.setitem(builder.ASSETS_DA_INTEGRACAO, "contrato_ledger", contrato)

    assert builder.main([str(raiz)]) == 1

    assert not (raiz / "qc.json").exists()
    assert not (raiz / "relatorio.html").exists()
    assert "contrato do ledger" in capsys.readouterr().err


# ==========================================================================
# CONTEÚDO: as regras de D3, cada uma com um caso que dispara e um vizinho que não.
# ==========================================================================

@pytest.mark.parametrize("fixture", CASOS)
def test_o_ledger_padrao_cobre_exatamente_os_insumos_que_o_qc_exige_e_nao_dispara_regra_do_ledger(fixture):
    """Armadilha 1 medida: o ledger padrão não dispara regra de ledger nenhuma, com identidades
    distintas. E não é verde vazio: os caminhos que ele nomeia são exatamente os que o QC exige
    de um ledger sem registros — duas derivações independentes do mesmo mapa, a do apoio e a do
    QC, que precisam concordar folha a folha."""
    entrega_dict = _entrega(fixture)
    assert not {a.codigo for a in _achados(entrega_dict)} & CODIGOS_DO_LEDGER

    registros = _registros(entrega_dict)
    identidades = [registro["fonte"]["identidade"] for registro in registros]
    assert len(set(identidades)) == len(identidades)
    nomeados = sorted(caminho for registro in registros for caminho in registro.get("usado_em", []))

    vazio = copy.deepcopy(entrega_dict)
    vazio["ledger"]["registros"] = []
    exigidos = sorted(a.params["caminho"] for a in _do_codigo(_achados(vazio), "insumo_sem_proveniencia"))
    assert exigidos, "o QC não exigiu insumo nenhum — trava vacuamente verde"
    assert nomeados == exigidos


# --- insumo_sem_proveniencia (HARD FAIL) -----------------------------------

@pytest.mark.parametrize("fixture,caminho", [
    pytest.param(FIXTURE, "preco.valor", id="folha-de-objeto"),
    pytest.param(FIXTURE_COM_LISTA_E_GRADE, "mercado.beta_observado.1", id="indice-de-lista-e-segmento"),
])
def test_insumo_sem_registro_que_o_nomeie_e_hard_fail(fixture, caminho):
    entrega_dict = _entrega(fixture)
    assert _do_codigo(_achados(entrega_dict), "insumo_sem_proveniencia") == []

    _registros(entrega_dict).remove(_que_sustenta(entrega_dict, caminho))
    assert _como(_do_codigo(_achados(entrega_dict), "insumo_sem_proveniencia")) == [
        ("HARD_FAIL", f"caso.{caminho}", {"caminho": caminho})]


def test_booleano_do_caso_nao_e_folha_numerica_e_o_numero_no_mesmo_caminho_e():
    entrega_dict = _entrega()
    premissas = entrega_dict["caso"]["cenarios"]["base"]["premissas"]

    premissas["premissa_de_teste"] = True
    assert _do_codigo(_achados(entrega_dict), "insumo_sem_proveniencia") == []

    premissas["premissa_de_teste"] = 1
    assert [a.onde for a in _do_codigo(_achados(entrega_dict), "insumo_sem_proveniencia")] == [
        "caso.cenarios.base.premissas.premissa_de_teste"]


# --- usado_em_fora_dos_insumos (HARD FAIL) ---------------------------------

@pytest.mark.parametrize("caminho", [
    pytest.param("cenarios.base.premissas.inexistente", id="caminho-que-o-caso-nao-tem"),
    pytest.param("cenarios.base.premissas.tv", id="texto-que-o-padrao-casa"),
    pytest.param("sensibilidades.grades_1d.0.pontos.0", id="numero-que-o-mapa-nao-declara"),
    pytest.param("mercado.beta_observado.-1", id="indice-que-nao-e-o-da-folha"),
    pytest.param("ponte", id="objeto-e-nao-folha"),
])
def test_usado_em_que_nao_nomeia_insumo_do_caso_e_hard_fail(caminho):
    entrega_dict = _entrega(FIXTURE_COM_LISTA_E_GRADE)
    registro = _que_sustenta(entrega_dict, "preco.valor")
    assert _do_codigo(_achados(entrega_dict), "usado_em_fora_dos_insumos") == []

    registro["usado_em"].append(caminho)
    assert _como(_do_codigo(_achados(entrega_dict), "usado_em_fora_dos_insumos")) == [
        ("HARD_FAIL", f"ledger.registros.{_indice(entrega_dict, registro)}.usado_em.1",
         {"id": registro["id"], "caminho": caminho})]


# --- insumo_nao_reconciliado (HARD FAIL) -----------------------------------

def test_valor_do_registro_diferente_do_caso_sem_reconciliacao_e_hard_fail():
    entrega_dict = _entrega()
    registro = _que_sustenta(entrega_dict, "preco.valor")
    preco = entrega_dict["caso"]["preco"]["valor"]
    divergente = preco * 1.01

    registro["valor"] = divergente
    assert _como(_do_codigo(_achados(entrega_dict), "insumo_nao_reconciliado")) == [
        ("HARD_FAIL", f"ledger.registros.{_indice(entrega_dict, registro)}.valor", {
            "id": registro["id"], "caminho": "preco.valor", "valor_registro": divergente, "valor_caso": preco,
            "valor_registro_fmt": placeholders.formatar(divergente, "num4", "pt-BR"),
            "valor_caso_fmt": placeholders.formatar(preco, "num4", "pt-BR")})]

    registro["reconciliacao"] = {"texto": "A fonte publica o preço médio do dia, não o de fechamento."}
    assert _do_codigo(_achados(entrega_dict), "insumo_nao_reconciliado") == []


@pytest.mark.parametrize("caminho,fator,dispara", [
    pytest.param("preco.valor", 1 + qc.TOLERANCIA_RELATIVA_DE_RECONCILIACAO / 10, False, id="dentro-da-relativa"),
    pytest.param("preco.valor", 1 + qc.TOLERANCIA_RELATIVA_DE_RECONCILIACAO * 10, True, id="fora-da-relativa"),
])
def test_a_reconciliacao_compara_com_a_tolerancia_relativa_nomeada(caminho, fator, dispara):
    entrega_dict = _entrega()
    registro = _que_sustenta(entrega_dict, caminho)
    registro["valor"] = registro["valor"] * fator
    assert bool(_do_codigo(_achados(entrega_dict), "insumo_nao_reconciliado")) is dispara


@pytest.mark.parametrize("valor,dispara", [
    pytest.param(qc.TOLERANCIA_ABSOLUTA_DE_RECONCILIACAO / 10, False, id="dentro-do-piso-absoluto"),
    pytest.param(qc.TOLERANCIA_ABSOLUTA_DE_RECONCILIACAO * 10, True, id="fora-do-piso-absoluto"),
])
def test_a_reconciliacao_de_um_zero_usa_o_piso_absoluto_nomeado(valor, dispara):
    entrega_dict = _entrega()
    caminho = next(caminho for caminho, numero in apoio.insumos_do_caso(entrega_dict["caso"]) if numero == 0)
    _que_sustenta(entrega_dict, caminho)["valor"] = valor
    assert bool(_do_codigo(_achados(entrega_dict), "insumo_nao_reconciliado")) is dispara


# --- conflito_de_fontes_silenciado (HARD FAIL) -----------------------------

def _concorrente(registro: dict, valor, ident: str = "concorrente", **campos) -> dict:
    """Outro registro do mesmo claim e período, de outra fonte, que não sustenta insumo."""
    outro = copy.deepcopy(registro)
    outro.pop("usado_em", None)
    outro.update(id=ident, valor=valor, fonte={"identidade": f"fonte {ident}", "classe": CLASSE}, **campos)
    return outro


def test_conflito_entre_fontes_sem_vencedor_e_hard_fail_um_por_grupo():
    entrega_dict = _entrega()
    alvo = _que_sustenta(entrega_dict, "preco.valor")
    _registros(entrega_dict).append(_concorrente(alvo, alvo["valor"] + 1.0))
    assert _como(_do_codigo(_achados(entrega_dict), "conflito_de_fontes_silenciado")) == [
        ("HARD_FAIL", f"ledger.registros.{_indice(entrega_dict, alvo)}",
         {"claim": alvo["claim"], "periodo": alvo["periodo"], "ids": f"'{alvo['id']}', 'concorrente'"})]

    segundo = _que_sustenta(entrega_dict, "acoes_diluidas")
    _registros(entrega_dict).append(_concorrente(segundo, segundo["valor"] * 2, ident="outro concorrente"))
    assert [a.params["claim"] for a in _do_codigo(_achados(entrega_dict), "conflito_de_fontes_silenciado")] == [
        alvo["claim"], segundo["claim"]]


@pytest.mark.parametrize("vizinho,dispara", [
    pytest.param(lambda alvo: _concorrente(alvo, alvo["valor"] + 1.0,
                                           conflito={"vencedor": alvo["id"], "razao": "A bolsa é a fonte primária."}),
                 False, id="vencedor-do-grupo-declarado"),
    pytest.param(lambda alvo: _concorrente(alvo, alvo["valor"] + 1.0,
                                           conflito={"vencedor": "consenso", "razao": "O consenso vence."}),
                 True, id="vencedor-fora-do-grupo"),
    pytest.param(lambda alvo: _concorrente(alvo, alvo["valor"]), False, id="mesmo-valor"),
    pytest.param(lambda alvo: _concorrente(alvo, alvo["valor"] + 1.0, periodo="outro período"),
                 False, id="outro-periodo"),
    pytest.param(lambda alvo: _concorrente(alvo, None), False, id="valor-nulo-nao-conflita"),
])
def test_conflito_e_so_de_valores_numericos_do_mesmo_claim_e_periodo_sem_vencedor_do_grupo(vizinho, dispara):
    entrega_dict = _entrega()
    alvo = _que_sustenta(entrega_dict, "preco.valor")
    _registros(entrega_dict).append(vizinho(alvo))
    assert bool(_do_codigo(_achados(entrega_dict), "conflito_de_fontes_silenciado")) is dispara


def test_registro_vencido_que_sustenta_insumo_sem_reconciliacao_e_hard_fail():
    """Revisão da 5E (F3): o conflito declara o vencedor, mas o caso continua com o número do
    registro vencido."""
    entrega_dict = _entrega()
    alvo = _que_sustenta(entrega_dict, "preco.valor")
    alvo["conflito"] = {"vencedor": "vencedor", "razao": "A fonte primária publica o número revisado."}
    _registros(entrega_dict).append(_concorrente(alvo, alvo["valor"] + 1.0, ident="vencedor"))
    achados = _achados(entrega_dict)
    assert _do_codigo(achados, "conflito_de_fontes_silenciado") == []
    assert _como(_do_codigo(achados, "insumo_sustentado_pela_fonte_vencida")) == [
        ("HARD_FAIL", f"ledger.registros.{_indice(entrega_dict, alvo)}", {
            "id": alvo["id"], "vencedor": "vencedor", "claim": alvo["claim"], "periodo": alvo["periodo"],
            "caminhos": ", ".join(f"'{caminho}'" for caminho in alvo["usado_em"])})]

    alvo["reconciliacao"] = {"texto": "O caso usa o fechamento, que a fonte vencedora revisou."}
    assert _do_codigo(_achados(entrega_dict), "insumo_sustentado_pela_fonte_vencida") == []

    del alvo["reconciliacao"]
    alvo["conflito"]["vencedor"] = alvo["id"]
    assert _do_codigo(_achados(entrega_dict), "insumo_sustentado_pela_fonte_vencida") == []


# --- referencia_fora_do_ledger (HARD FAIL) ---------------------------------

def _citar_em_insumos(entrega_dict: dict, ident: str) -> str:
    registro = _que_sustenta(entrega_dict, "preco.valor")
    registro.update(estatuto=ESTATUTO_COM_FORMULA, formula="último preço de fechamento", insumos=[ident])
    return f"ledger.registros.{_indice(entrega_dict, registro)}.insumos.0"


def _citar_como_vencedor(entrega_dict: dict, ident: str) -> str:
    registro = _que_sustenta(entrega_dict, "preco.valor")
    registro["conflito"] = {"vencedor": ident, "razao": "A bolsa é a fonte primária do preço."}
    return f"ledger.registros.{_indice(entrega_dict, registro)}.conflito.vencedor"


def _citar_como_contraprova(entrega_dict: dict, ident: str) -> str:
    contraprova = _contraprova_de(entrega_dict, _que_sustenta(entrega_dict, _caminho_da_premissa_decisiva(entrega_dict)))
    contraprova["contraprova_de"] = ident
    return f"ledger.registros.{_indice(entrega_dict, contraprova)}.contraprova_de"


def _citar_no_consenso(entrega_dict: dict, ident: str) -> str:
    entrega_dict["analise"]["consenso"] = {"registros": [ident]}
    return "analise.consenso.registros.0"


def _citar_no_dataset(entrega_dict: dict, ident: str) -> str:
    entrega_dict["dados"] = {"fin": _dataset([ident])}
    return "dados.fin.ledger.0"


@pytest.mark.parametrize("citar", [_citar_em_insumos, _citar_como_vencedor, _citar_como_contraprova,
                                   _citar_no_consenso, _citar_no_dataset],
                         ids=["insumos", "conflito-vencedor", "contraprova-de", "consenso", "dataset"])
def test_id_citado_que_o_ledger_nao_tem_e_hard_fail_nomeando_o_lugar(citar):
    existente = _entrega()
    citar(existente, _que_sustenta(existente, "preco.valor")["id"])
    assert _do_codigo(_achados(existente), "referencia_fora_do_ledger") == []

    quebrada = _entrega()
    onde = citar(quebrada, "registro-que-nao-existe")
    assert _como(_do_codigo(_achados(quebrada), "referencia_fora_do_ledger")) == [
        ("HARD_FAIL", onde, {"id": "registro-que-nao-existe"})]


# --- dataset_sem_proveniencia (HARD FAIL) ----------------------------------

_DADOS_DO_EXHIBIT = {"fin": {
    "ledger": [], "x": [str(ano) for ano in range(2016, 2026)],
    "campos": {"receita": [100.0 + 10.0 * i for i in range(10)], "ebitda": [20.0 + 3.0 * i for i in range(10)]},
}}
_SERIES = {
    "direta": {"derivacao": "direta", "fonte": "fin.receita"},
    "derivada": {"derivacao": "derivada", "fonte": "fin", "formula": "ebitda / receita", "formula_nota": "margem EBITDA"},
    "engine": {"derivacao": "engine", "chave": "resultados:manchete.preco_acao", "rotulo": "preço justo da manchete"},
}


def _exhibit(derivacao: str) -> dict:
    return {"id": "margem", "pergunta": "Como a margem evoluiu no período?", "tipo": "linha",
            "series": [copy.deepcopy(_SERIES[derivacao])]}


@pytest.mark.parametrize("derivacao,dispara", [
    pytest.param("direta", True, id="direta"),
    pytest.param("derivada", True, id="derivada"),
    pytest.param("engine", False, id="engine-nao-usa-dataset"),
])
def test_dataset_de_serie_direta_ou_derivada_com_ledger_vazio_e_hard_fail(derivacao, dispara):
    exhibit = _exhibit(derivacao)
    composta = apoio.montar_entrega(FIXTURE, dados=_DADOS_DO_EXHIBIT, exhibits=[exhibit])
    assert composta["dados"]["fin"]["ledger"] != []
    assert _do_codigo(_achados(composta), "dataset_sem_proveniencia") == []

    declarada = apoio.montar_entrega(FIXTURE, dados=_DADOS_DO_EXHIBIT, exhibits=[exhibit], compor_ledger=False,
                                     ledger=composta["ledger"], consenso=composta["analise"]["consenso"])
    assert declarada["dados"]["fin"]["ledger"] == []
    esperado = [("HARD_FAIL", "dados.fin.ledger", {"dataset": "fin"})] if dispara else []
    assert _como(_do_codigo(_achados(declarada), "dataset_sem_proveniencia")) == esperado


# --- insumo_estimado (REQUIRED DISCLOSURE) ---------------------------------

def test_registro_estimado_que_sustenta_insumo_e_disclosure_com_o_claim():
    entrega_dict = _entrega()
    registro = _que_sustenta(entrega_dict, "preco.valor")
    assert _do_codigo(_achados(entrega_dict), "insumo_estimado") == []

    registro["estatuto"] = ESTATUTO_ESTIMADO
    assert _como(_do_codigo(_achados(entrega_dict), "insumo_estimado")) == [
        ("REQUIRED_DISCLOSURE", f"ledger.registros.{_indice(entrega_dict, registro)}",
         {"id": registro["id"], "claim": registro["claim"],
          "valor_fmt": placeholders.formatar(registro["valor"], "num4", "pt-BR"), "unidade": registro["unidade"]})]


def test_registro_estimado_que_nao_sustenta_insumo_nao_e_disclosure():
    entrega_dict = _entrega()
    (consenso,) = [r for r in _registros(entrega_dict) if r["id"] in entrega_dict["analise"]["consenso"]["registros"]]
    consenso["estatuto"] = ESTATUTO_ESTIMADO
    assert _do_codigo(_achados(entrega_dict), "insumo_estimado") == []


def test_estimativa_que_alimenta_o_registro_de_um_insumo_pelos_insumos_e_disclosure():
    """Revisão da 5E (F2): o número calculado a partir de uma estimativa é "baseado em estimativa"
    (§11), também em dois níveis e com um ciclo declarado."""
    entrega_dict = _entrega()
    registro = _que_sustenta(entrega_dict, "preco.valor")
    intermediario = _concorrente(registro, 1.0, ident="intermediario", claim="Ajuste intermediário",
                                 estatuto=ESTATUTO_COM_FORMULA, formula="soma dos ajustes", insumos=["ingrediente"])
    ingrediente = _concorrente(registro, 2.0, ident="ingrediente", claim="Ajuste do analista",
                               estatuto=ESTATUTO_OBSERVADO, insumos=[registro["id"]])
    registro.update(estatuto=ESTATUTO_COM_FORMULA, formula="último preço mais os ajustes", insumos=["intermediario"])
    _registros(entrega_dict).extend([intermediario, ingrediente])
    assert _do_codigo(_achados(entrega_dict), "insumo_estimado") == []

    ingrediente["estatuto"] = ESTATUTO_ESTIMADO
    assert [a.onde for a in _do_codigo(_achados(entrega_dict), "insumo_estimado")] == [
        f"ledger.registros.{_indice(entrega_dict, ingrediente)}"]


def test_placeholder_em_dado_do_ledger_que_a_tese_exibe_e_hard_fail():
    """Revisão da 5E (F4): a Tese mostra os campos do registro como dado — um placeholder sairia cru."""
    entrega_dict = _entrega()
    (consenso,) = [r for r in _registros(entrega_dict) if r["id"] in entrega_dict["analise"]["consenso"]["registros"]]
    consenso["claim"] = "Preço-alvo médio de R$ 72,00 para 12 meses"
    estimado = _que_sustenta(entrega_dict, "preco.valor")
    estimado["estatuto"] = ESTATUTO_ESTIMADO
    assert _do_codigo(_achados(entrega_dict), "placeholder_em_dado_da_tese") == []

    consenso["claim"] = "Preço-alvo médio ({{resultados:manchete.preco_acao|moeda}})"
    estimado["claim"] = "Preço estimado ({{caso:preco.valor|moeda}})"
    esperado = sorted((_indice(entrega_dict, r), r["id"]) for r in (consenso, estimado))
    assert _como(_do_codigo(_achados(entrega_dict), "placeholder_em_dado_da_tese")) == [
        ("HARD_FAIL", f"ledger.registros.{indice}.claim", {"id": ident, "campo": "claim"}) for indice, ident in esperado]


# --- sem_contraprova_independente (REQUIRED DISCLOSURE) --------------------

def _sem_registro_de_contraprova(entrega_dict: dict, alvo: dict) -> None:
    _registros(entrega_dict).remove(_contraprova_de(entrega_dict, alvo))


def _contraprova_da_mesma_identidade(entrega_dict: dict, alvo: dict) -> None:
    _contraprova_de(entrega_dict, alvo)["fonte"]["identidade"] = alvo["fonte"]["identidade"]


def _contraprova_de_registro_que_nao_sustenta_a_premissa(entrega_dict: dict, alvo: dict) -> None:
    _contraprova_de(entrega_dict, alvo)["contraprova_de"] = _que_sustenta(entrega_dict, "preco.valor")["id"]


@pytest.mark.parametrize("tirar", [_sem_registro_de_contraprova, _contraprova_da_mesma_identidade,
                                   _contraprova_de_registro_que_nao_sustenta_a_premissa],
                         ids=["sem-contraprova", "mesma-identidade-nao-conta", "contraprova-de-outro-registro"])
def test_premissa_decisiva_sem_contraprova_independente_e_disclosure_com_o_rotulo_do_catalogo(tirar):
    entrega_dict = _entrega()
    caminho = _caminho_da_premissa_decisiva(entrega_dict)
    chave = entrega_dict["analise"]["premissas_decisivas"][0]["chave"]
    alvo = _que_sustenta(entrega_dict, caminho)
    assert _do_codigo(_achados(entrega_dict), "sem_contraprova_independente") == []

    tirar(entrega_dict, alvo)
    rotulo = CATALOGO["premissas"][entrega_dict["resultados"]["rota"]][chave]["rotulo"]["pt-BR"]
    assert _como(_do_codigo(_achados(entrega_dict), "sem_contraprova_independente")) == [
        ("REQUIRED_DISCLOSURE", "analise.premissas_decisivas.0.chave",
         {"chave": chave, "rotulo": rotulo, "caminho": caminho})]


@pytest.mark.parametrize("ajustar,dispara", [
    pytest.param(lambda contraprova, alvo: contraprova.update(valor=alvo["valor"] * 1.5),
                 True, id="valor-divergente-sem-reconciliacao"),
    pytest.param(lambda contraprova, alvo: contraprova.update(valor=None),
                 True, id="sem-valor-nao-confirma"),
    pytest.param(lambda contraprova, alvo: contraprova.update(valor=alvo["valor"]),
                 False, id="mesmo-valor"),
    pytest.param(lambda contraprova, alvo: contraprova.update(
                     valor=alvo["valor"] * (1 + qc.TOLERANCIA_RELATIVA_DE_RECONCILIACAO / 10)),
                 False, id="dentro-da-tolerancia-da-reconciliacao"),
    pytest.param(lambda contraprova, alvo: contraprova.update(
                     valor=alvo["valor"] * 1.5,
                     reconciliacao={"texto": "A outra via mede o retorno antes do ajuste de arrendamentos."}),
                 False, id="divergencia-reconciliada"),
])
def test_contraprova_so_confirma_com_o_mesmo_valor_ou_com_a_divergencia_reconciliada(ajustar, dispara):
    """§6.3: contraprova é confirmação. Uma fonte independente que diverge do número não o
    confirma — a menos que declare a reconciliação, que a Evidência mostra. Com outro claim, o
    conflito entre fontes (mesmo claim e período) não enxerga a divergência: só esta regra a pega."""
    entrega_dict = _entrega()
    alvo = _que_sustenta(entrega_dict, _caminho_da_premissa_decisiva(entrega_dict))
    contraprova = _contraprova_de(entrega_dict, alvo)
    contraprova["claim"] = f"{alvo['claim']}, por outra via"
    ajustar(contraprova, alvo)

    achados = _achados(entrega_dict)
    assert _do_codigo(achados, "conflito_de_fontes_silenciado") == []
    assert bool(_do_codigo(achados, "sem_contraprova_independente")) is dispara


# --- lacuna_material e consenso_indisponivel (REQUIRED DISCLOSURE) ---------

def test_lacuna_material_e_disclosure_com_a_prosa_crua_e_o_campo_que_a_tese_resolve():
    entrega_dict = _entrega()
    descricao = "O preço de tela, {{caso:preco.valor|moeda}}, não tem série histórica ajustada."
    tratamento = "O histórico entra só como referência qualitativa."
    entrega_dict["ledger"]["lacunas"] = [
        _lacuna(id="historico", descricao=descricao, tratamento=tratamento, materialidade=MATERIALIDADE_COM_DISCLOSURE),
        _lacuna()]

    achados = _achados(entrega_dict)
    assert _do_codigo(achados, "numero_sem_proveniencia") == []
    assert _como(_do_codigo(achados, "lacuna_material")) == [
        ("REQUIRED_DISCLOSURE", "ledger.lacunas.0", {
            "id": "historico", "descricao": descricao, "tratamento": tratamento,
            "campos_de_prosa": {"descricao": "ledger.lacunas.0.descricao", "tratamento": "ledger.lacunas.0.tratamento"}})]

    # É pelo mapa que a Tese troca o texto cru pelo resolvido: cada campo citado está na lista de
    # prosa com o mesmo texto, e resolve sem `{{...}}`.
    (achado,) = _do_codigo(achados, "lacuna_material")
    prosa = dict(placeholders.campos_de_prosa(entrega_dict))
    resolvida, _log = placeholders.resolver_prosa(entrega_dict, "pt-BR")
    for param, onde in achado.params["campos_de_prosa"].items():
        assert prosa[onde] == achado.params[param]
        assert "{{" not in resolvida[onde]
    preco = placeholders.formatar(entrega_dict["caso"]["preco"]["valor"], "moeda", "pt-BR", entrega_dict["caso"]["moeda"])
    assert preco in resolvida["ledger.lacunas.0.descricao"]


def test_consenso_ausente_e_disclosure_com_a_ancora_a_razao_e_o_campo():
    entrega_dict = _entrega()
    assert _do_codigo(_achados(entrega_dict), "consenso_indisponivel") == []

    razao = "Nenhum provedor cobre a companhia; o histórico normalizado ancora o cenário de alta."
    entrega_dict["analise"]["consenso"] = {"ausente": {"ancora": ANCORA, "razao": razao}}
    assert _como(_do_codigo(_achados(entrega_dict), "consenso_indisponivel")) == [
        ("REQUIRED_DISCLOSURE", "analise.consenso.ausente",
         {"ancora": ANCORA, "razao": razao, "campos_de_prosa": {"razao": "analise.consenso.ausente.razao"}})]
    assert dict(placeholders.campos_de_prosa(entrega_dict))["analise.consenso.ausente.razao"] == razao


def _consenso_ausente(entrega_dict: dict, sufixo: str = "") -> None:
    entrega_dict["analise"]["consenso"] = {"ausente": {"ancora": ANCORA, "razao": "Nenhum provedor cobre a companhia." + sufixo}}


def _lacuna_na_descricao(entrega_dict: dict, sufixo: str = "") -> None:
    entrega_dict["ledger"]["lacunas"] = [_lacuna(descricao="A companhia não publica a abertura por segmento." + sufixo)]


def _lacuna_no_tratamento(entrega_dict: dict, sufixo: str = "") -> None:
    entrega_dict["ledger"]["lacunas"] = [_lacuna(tratamento="A análise usa o consolidado." + sufixo)]


@pytest.mark.parametrize("onde,declarar", [
    pytest.param("analise.consenso.ausente.razao", _consenso_ausente, id="razao-do-consenso-ausente"),
    pytest.param("ledger.lacunas.0.descricao", _lacuna_na_descricao, id="descricao-da-lacuna"),
    pytest.param("ledger.lacunas.0.tratamento", _lacuna_no_tratamento, id="tratamento-da-lacuna"),
])
def test_digito_solto_na_razao_do_consenso_ausente_e_nas_lacunas_e_numero_sem_proveniencia(onde, declarar):
    limpa = _entrega()
    declarar(limpa)
    assert _do_codigo(_achados(limpa), "numero_sem_proveniencia") == []

    suja = _entrega()
    declarar(suja, " A cobertura acabou em 2024.")
    assert [(a.nivel, a.onde) for a in _do_codigo(_achados(suja), "numero_sem_proveniencia")] == [("HARD_FAIL", onde)]


def test_textos_dos_registros_e_do_confronto_sao_dado_da_evidencia_e_nao_prosa_auditada():
    """§9: linguagem interna é permitida na Evidência. O claim, a justificativa, a reconciliação
    de um registro e o confronto podem citar números sem placeholder — nenhum deles entra na lista
    de prosa."""
    entrega_dict = _entrega()
    _que_sustenta(entrega_dict, "preco.valor").update(
        claim="Preço de fechamento de 21/08/2026", justificativa_da_fonte="A B3 publica o fechamento às 18h.",
        reconciliacao={"texto": "Arredondado a 2 casas."})
    entrega_dict["confronto"] = _confronto()

    assert [onde for onde, _texto in placeholders.campos_de_prosa(entrega_dict)
            if onde.startswith(("ledger.registros", "confronto"))] == []
    assert _do_codigo(_achados(entrega_dict), "numero_sem_proveniencia") == []


# --- concentracao_de_fontes (QUALITY WARNING) ------------------------------

def test_os_limiares_da_concentracao_sao_os_da_decisao():
    assert (qc.LIMIAR_DE_CONCENTRACAO_DE_FONTES, qc.MINIMO_DE_INSUMOS_PARA_CONCENTRACAO) == (0.5, 4)


def test_uma_fonte_que_sustenta_mais_da_metade_dos_insumos_e_quality_warning():
    entrega_dict = _entrega()
    insumos = [registro for registro in _registros(entrega_dict) if registro.get("usado_em")]
    total = len(insumos)
    assert total >= qc.MINIMO_DE_INSUMOS_PARA_CONCENTRACAO
    no_limiar = math.floor(total * qc.LIMIAR_DE_CONCENTRACAO_DE_FONTES)

    for registro in insumos[:no_limiar]:
        registro["fonte"]["identidade"] = "fonte dominante"
    assert _do_codigo(_achados(entrega_dict), "concentracao_de_fontes") == []

    insumos[no_limiar]["fonte"]["identidade"] = "fonte dominante"
    assert _como(_do_codigo(_achados(entrega_dict), "concentracao_de_fontes")) == [
        ("QUALITY_WARNING", "ledger.registros", {
            "identidade": "fonte dominante", "insumos": no_limiar + 1, "total": total,
            "parcela_fmt": placeholders.formatar((no_limiar + 1) / total, "pct0", "pt-BR"),
            "limiar_fmt": placeholders.formatar(qc.LIMIAR_DE_CONCENTRACAO_DE_FONTES, "pct0", "pt-BR")})]


def test_abaixo_do_minimo_de_insumos_a_concentracao_nao_e_medida():
    assert "ponte.*" in CATALOGO["insumos_do_caso"]
    entrega_dict = _entrega()

    def _concentracao_com(quantos: int) -> list:
        entrega_dict["caso"] = {"ponte": {f"linha_{i}": float(i + 1) for i in range(quantos)}}
        entrega_dict["ledger"]["registros"] = [
            apoio.registro_do_ledger(f"linha-{i}", f"linha {i} da ponte", "fonte única", float(i + 1),
                                     usado_em=[f"ponte.linha_{i}"])
            for i in range(quantos)]
        return _do_codigo(_achados(entrega_dict), "concentracao_de_fontes")

    minimo = qc.MINIMO_DE_INSUMOS_PARA_CONCENTRACAO
    assert _concentracao_com(minimo - 1) == []
    assert [(a.params["insumos"], a.params["total"]) for a in _concentracao_com(minimo)] == [(minimo, minimo)]


# --- falha fechada: sem o mapa ou sem o contrato ---------------------------

_SEM_MAPA = object()


@pytest.mark.parametrize("mapa", [_SEM_MAPA, [], ["preco.valor", ""], "preco.valor"],
                         ids=["ausente", "lista-vazia", "padrao-vazio", "texto"])
def test_sem_o_mapa_de_insumos_o_qc_falha_fechado(mapa):
    entrega_dict = _entrega()
    assert _do_codigo(_achados(entrega_dict), "insumos_do_caso_desconhecidos") == []

    catalogo = copy.deepcopy(CATALOGO)
    if mapa is _SEM_MAPA:
        del catalogo["insumos_do_caso"]
    else:
        catalogo["insumos_do_caso"] = mapa
    assert _como(_do_codigo(_achados(entrega_dict, catalogo), "insumos_do_caso_desconhecidos")) == [
        ("HARD_FAIL", "catalogo.insumos_do_caso", {})]


def test_sem_o_contrato_do_ledger_o_qc_falha_fechado():
    entrega_dict = _entrega()
    sem_flag = copy.deepcopy(CONTRATO)
    del sem_flag["vocabularios"]["estatutos"][ESTATUTO_ESTIMADO]["e_estimativa"]
    for contrato in (None, {}, sem_flag):
        with pytest.raises(entrega.ContratoDoLedgerInvalido):
            _achados(entrega_dict, contrato=contrato)


# --- pelo CLI --------------------------------------------------------------

def test_hard_fail_do_ledger_nao_emite_e_sai_pelo_codigo_2(tmp_path):
    entrega_dict = _entrega()
    _registros(entrega_dict).remove(_que_sustenta(entrega_dict, "preco.valor"))
    raiz = tmp_path / "sem_proveniencia"
    apoio.escrever_raiz(raiz, entrega_dict)

    resultado = _rodar_builder(raiz)

    assert resultado.returncode == 2, resultado.stdout + resultado.stderr
    assert not (raiz / "relatorio.html").exists()
    assert [(a["codigo"], a["mensagem"]) for a in _ler_qc(raiz)["achados"]] == [
        ("insumo_sem_proveniencia",
         DICIONARIO["qc"]["insumo_sem_proveniencia"].format(onde="caso.preco.valor", caminho="preco.valor"))]


def test_disclosures_e_aviso_do_ledger_emitem_com_a_mensagem_do_dicionario(tmp_path):
    entrega_dict = _entrega()
    estimado = _que_sustenta(entrega_dict, "preco.valor")
    estimado["estatuto"] = ESTATUTO_ESTIMADO
    _sem_registro_de_contraprova(entrega_dict, _que_sustenta(entrega_dict, _caminho_da_premissa_decisiva(entrega_dict)))
    entrega_dict["ledger"]["lacunas"] = [_lacuna(materialidade=MATERIALIDADE_COM_DISCLOSURE)]
    _consenso_ausente(entrega_dict)
    for registro in _registros(entrega_dict):
        if registro.get("usado_em"):
            registro["fonte"]["identidade"] = "fonte dominante"
    raiz = tmp_path / "disclosures"
    apoio.escrever_raiz(raiz, entrega_dict)

    resultado = _rodar_builder(raiz)

    assert resultado.returncode == 0, resultado.stdout + resultado.stderr
    achados = _ler_qc(raiz)["achados"]
    assert [(a["nivel"], a["codigo"]) for a in achados] == [
        ("REQUIRED_DISCLOSURE", "insumo_estimado"), ("REQUIRED_DISCLOSURE", "sem_contraprova_independente"),
        ("REQUIRED_DISCLOSURE", "lacuna_material"), ("REQUIRED_DISCLOSURE", "consenso_indisponivel"),
        ("QUALITY_WARNING", "concentracao_de_fontes")]
    for achado in achados:
        assert achado["mensagem"] == DICIONARIO["qc"][achado["codigo"]].format(onde=achado["onde"], **achado["params"])
    assert estimado["claim"] in achados[0]["mensagem"]


# ==========================================================================
# Task 3 (D4, D6, D7): a aba Evidência, o consenso na Conclusão, os avisos da Tese com a prosa
# resolvida e a ficha técnica em arquivo. Toda asserção lê o TEXTO que o analista vê; classe só
# LOCALIZA a seção.
# ==========================================================================

EVIDENCIA = DICIONARIO["interface"]["evidencia"]
TESE = DICIONARIO["interface"]["tese"]
NOME_DA_FICHA = "ficha-tecnica.json"


def _pagina(entrega_dict: dict) -> str:
    """O HTML pelo caminho que `builder.py` percorre depois de uma primeira passada de QC sem HARD FAIL:
    o log de toda a prosa, os exhibits resolvidos uma vez e a ficha técnica que o builder compõe."""
    achados = _achados(entrega_dict)
    assert not [a for a in achados if a.nivel == "HARD_FAIL"], achados
    _prosa, log = placeholders.resolver_prosa(entrega_dict, "pt-BR")
    resolvidos, log_exhibits = exhibits.resolver(entrega_dict)
    return render.compor(entrega_dict, CATALOGO, achados, log, "pt-BR", resolvidos, log_exhibits,
                         ficha_tecnica=builder.compor_ficha_tecnica(entrega_dict, CATALOGO, achados))


def _rotulo(vocabulario: str, codigo: str) -> str:
    """O rótulo do dicionário para um código de vocabulário — nunca a própria chave, senão a asserção
    não distinguiria o rótulo da chave crua."""
    rotulo = EVIDENCIA[vocabulario][codigo]
    assert rotulo != codigo, (vocabulario, codigo)
    return rotulo


def _pares(tabela: dict) -> list:
    """`(rótulo, valor)` de cada linha de uma tabela de chave e valor."""
    return [(_visivel(_um(linha, tag="th")), _visivel(_um(linha, tag="td"))) for linha in _todos(tabela, tag="tr")]


def _linhas(tabela: dict) -> list:
    """As células de cada linha do corpo de uma tabela com cabeçalho."""
    return [[_visivel(celula) for celula in _todos(linha, tag="td")]
            for linha in _todos(_um(tabela, tag="tbody"), tag="tr")]


def _tabela_do_registro(ledger: dict, ident: str) -> dict:
    (tabela,) = [tabela for tabela in _todos(ledger, tag="table")
                 if (EVIDENCIA["registro_campos"]["id"], ident) in _pares(tabela)]
    return tabela


def _valor_do_ledger(valor) -> str:
    return placeholders.formatar(valor, render.FORMATO_DO_VALOR_DO_LEDGER, "pt-BR")


def _contagem(quantidade: int) -> str:
    return placeholders.formatar(quantidade, "num0", "pt-BR")


def _moeda_do_caso(entrega_dict: dict, valor: float) -> str:
    return placeholders.formatar(valor, "moeda", "pt-BR", entrega_dict["caso"]["moeda"])


# --- D7: a ordem e as seções da aba ----------------------------------------

def test_a_aba_evidencia_segue_a_ordem_do_desenho():
    """D7: fontes → ledger → lacunas e limitações declaradas → confronto, se houver → ficha técnica →
    metodologia, log de placeholders e rastreabilidade dos exhibits. Sem confronto, nenhuma seção vazia
    no lugar dele."""
    com_confronto = _entrega()
    com_confronto["confronto"] = _confronto()
    esperados = [EVIDENCIA[chave] for chave in (
        "fontes_titulo", "ledger_titulo", "lacunas_titulo", "confronto_titulo", "ficha_tecnica_titulo",
        "metodologia_titulo", "log_titulo", "exhibits_titulo")]
    assert [_titulo(secao) for secao in _secoes(_aba(_pagina(com_confronto), "evidencia"))] == esperados

    sem_confronto = [titulo for titulo in esperados if titulo != EVIDENCIA["confronto_titulo"]]
    assert [_titulo(secao) for secao in _secoes(_aba(_pagina(_entrega()), "evidencia"))] == sem_confronto


def test_as_fontes_sao_as_identidades_distintas_na_ordem_da_primeira_aparicao_com_a_classe_e_os_registros():
    """Uma linha por identidade, na ordem em que o ledger a cita pela primeira vez, com o rótulo de cada
    classe com que ela aparece e o número de registros dela."""
    entrega_dict = _entrega()
    repetida, outra = _que_sustenta(entrega_dict, "preco.valor"), _que_sustenta(entrega_dict, "acoes_diluidas")
    outra_classe = next(classe for classe in _VOCABULARIOS["classes_de_fonte"] if classe != repetida["fonte"]["classe"])
    outra["fonte"] = {"identidade": repetida["fonte"]["identidade"], "classe": outra_classe}
    registros = _registros(entrega_dict)

    identidades = list(dict.fromkeys(registro["fonte"]["identidade"] for registro in registros))
    assert len(identidades) == len(registros) - 1
    esperadas = []
    for identidade in identidades:
        da_fonte = [registro for registro in registros if registro["fonte"]["identidade"] == identidade]
        classes = dict.fromkeys(registro["fonte"]["classe"] for registro in da_fonte)
        esperadas.append([identidade, ", ".join(_rotulo("classes_de_fonte", classe) for classe in classes),
                          _contagem(len(da_fonte))])
    (da_repetida,) = [linha for linha in esperadas if linha[0] == repetida["fonte"]["identidade"]]
    assert da_repetida[2] == _contagem(2) and ", " in da_repetida[1], "a identidade repetida não discriminaria"

    fontes = _secao(_aba(_pagina(entrega_dict), "evidencia"), EVIDENCIA["fontes_titulo"])
    assert _linhas(_um(fontes, tag="table")) == esperadas


def test_um_registro_do_ledger_mostra_todos_os_campos_rotulados_e_nenhuma_chave_crua_de_vocabulario():
    """D7: fonte e classe, estatuto, período, valor e unidade, moeda, data de acesso, localizador (tipo,
    valor e parâmetros), justificativa, fórmula e insumos, usado_em, reconciliação, conflito e
    contraprova — cada um sob o rótulo do dicionário, e todo vocabulário do contrato pelo rótulo."""
    entrega_dict = _entrega()
    alvo = _que_sustenta(entrega_dict, "preco.valor")
    classe = next(classe for classe in _VOCABULARIOS["classes_de_fonte"] if classe != CLASSE)
    tipo = next(tipo for tipo in _VOCABULARIOS["tipos_de_localizador"] if tipo != TIPO_DE_LOCALIZADOR)
    completo = apoio.registro_do_ledger(
        "preco-medio", alvo["claim"], "Consolidadora de cotações", alvo["valor"] * 1.001,
        fonte={"identidade": "Consolidadora de cotações", "classe": classe},
        localizador={"tipo": tipo, "valor": "cotacoes/diarias", "parametros": {"ativo": "SINT3", "janela": "fechamento"}},
        periodo=alvo["periodo"], moeda="BRL", unidade="R$ por ação", estatuto=ESTATUTO_COM_FORMULA,
        formula="média ponderada pelo volume dos negócios do dia", insumos=[alvo["id"]], usado_em=["preco.valor"],
        reconciliacao={"texto": "A média ponderada difere do fechamento por menos de um centavo."},
        conflito={"vencedor": alvo["id"], "razao": "A bolsa é a fonte primária do preço negociado."},
        contraprova_de=alvo["id"])
    _registros(entrega_dict).append(completo)

    ledger = _secao(_aba(_pagina(entrega_dict), "evidencia"), EVIDENCIA["ledger_titulo"])
    campos = EVIDENCIA["registro_campos"]
    assert _pares(_tabela_do_registro(ledger, completo["id"])) == [
        (campos["id"], completo["id"]),
        (campos["fonte"], "Consolidadora de cotações"),
        (campos["classe"], _rotulo("classes_de_fonte", classe)),
        (campos["estatuto"], _rotulo("estatutos", ESTATUTO_COM_FORMULA)),
        (campos["periodo"], alvo["periodo"]),
        (campos["valor"], _valor_do_ledger(completo["valor"])),
        (campos["unidade"], "R$ por ação"),
        (campos["moeda"], "BRL"),
        (campos["data_acesso"], completo["data_acesso"]),
        (campos["localizador_tipo"], _rotulo("tipos_de_localizador", tipo)),
        (campos["localizador_valor"], "cotacoes/diarias"),
        (campos["localizador_parametros"], "ativo: SINT3; janela: fechamento"),
        (campos["justificativa_da_fonte"], completo["justificativa_da_fonte"]),
        (campos["formula"], completo["formula"]),
        (campos["insumos"], alvo["id"]),
        (campos["usado_em"], "preco.valor"),
        (campos["reconciliacao"], completo["reconciliacao"]["texto"]),
        (campos["conflito_vencedor"], alvo["id"]),
        (campos["conflito_razao"], completo["conflito"]["razao"]),
        (campos["contraprova_de"], alvo["id"]),
    ]
    chaves_cruas = {classe, CLASSE, tipo, TIPO_DE_LOCALIZADOR, ESTATUTO_COM_FORMULA, ESTATUTO_OBSERVADO}
    assert sorted(chaves_cruas & {_visivel(celula) for celula in _todos(ledger, tag="td")}) == []


def test_o_ledger_agrupa_por_claim_na_ordem_da_primeira_aparicao_e_mostra_conflito_e_reconciliacao():
    """Um registro concorrente, declarado no fim do ledger, fica sob o claim que ele disputa, com o
    vencedor e a razão; o registro que diverge do número do caso mostra a reconciliação."""
    entrega_dict = _entrega()
    alvo = _que_sustenta(entrega_dict, "preco.valor")
    razao = "A bolsa é a fonte primária do preço negociado."
    concorrente = _concorrente(alvo, alvo["valor"] + 1.0, conflito={"vencedor": alvo["id"], "razao": razao})
    _registros(entrega_dict).append(concorrente)
    reconciliado = _que_sustenta(entrega_dict, "acoes_diluidas")
    reconciliado["valor"] = reconciliado["valor"] * 1.01
    reconciliado["reconciliacao"] = {"texto": "A fonte publica as ações em circulação, e o caso usa as diluídas."}
    registros = _registros(entrega_dict)

    ledger = _secao(_aba(_pagina(entrega_dict), "evidencia"), EVIDENCIA["ledger_titulo"])
    campos = EVIDENCIA["registro_campos"]
    claims = list(dict.fromkeys(registro["claim"] for registro in registros))
    grupos = _todos(ledger, classe="ledger-claim")
    assert [(_titulo(grupo), [dict(_pares(tabela))[campos["id"]] for tabela in _todos(grupo, tag="table")])
            for grupo in grupos] == [
        (claim, [registro["id"] for registro in registros if registro["claim"] == claim]) for claim in claims]
    (do_preco,) = [grupo for grupo in grupos if _titulo(grupo) == alvo["claim"]]
    assert len(_todos(do_preco, tag="table")) == 2, "o concorrente não ficou sob o claim que disputa"

    disputa = dict(_pares(_tabela_do_registro(ledger, concorrente["id"])))
    assert (disputa[campos["conflito_vencedor"]], disputa[campos["conflito_razao"]]) == (alvo["id"], razao)
    divergente = dict(_pares(_tabela_do_registro(ledger, reconciliado["id"])))
    assert (divergente[campos["valor"]], divergente[campos["reconciliacao"]]) == (
        _valor_do_ledger(reconciliado["valor"]), reconciliado["reconciliacao"]["texto"])


def test_lacunas_limitacoes_e_fronteira_de_escopo_saem_rotuladas_e_com_a_prosa_resolvida():
    """Cada lacuna com a materialidade rotulada e a descrição e o tratamento resolvidos pela lista de
    prosa; cada limitação publicada com o rótulo do catálogo; a fronteira de escopo com o rótulo da
    classe. Sem nada declarado, a seção diz isso."""
    degrau = _entrega("caso_degrau.json")
    limitacoes = degrau["resultados"]["limitacoes"]
    assert limitacoes, "caso_degrau publica a limitação da reversa — sem ela, a asserção seria vácua"
    placeholder = "{{caso:preco.valor|moeda}}"
    degrau["ledger"]["lacunas"] = [
        _lacuna(id="historico", descricao=f"O preço de tela, {placeholder}, não tem série histórica ajustada.",
                materialidade=MATERIALIDADE_COM_DISCLOSURE),
        _lacuna()]
    preco = _moeda_do_caso(degrau, degrau["caso"]["preco"]["valor"])

    secao = _secao(_aba(_pagina(degrau), "evidencia"), EVIDENCIA["lacunas_titulo"])
    assert _linhas(_um(secao, tag="table")) == [
        [lacuna["id"], _rotulo("materialidades", lacuna["materialidade"]),
         lacuna["descricao"].replace(placeholder, preco), lacuna["tratamento"]]
        for lacuna in degrau["ledger"]["lacunas"]]
    assert [_visivel(item) for item in _todos(_um(secao, classe="limitacoes"), tag="li")] == [
        CATALOGO["limitacoes"][chave]["rotulo"]["pt-BR"] for chave in limitacoes]
    assert "{{" not in _visivel(secao)

    sob_fronteira = apoio.montar_entrega(FIXTURE, mutar_caso=_com_fronteira_de_escopo)
    classe = sob_fronteira["resultados"]["fronteira_de_escopo"]["classe"]
    secao = _secao(_aba(_pagina(sob_fronteira), "evidencia"), EVIDENCIA["lacunas_titulo"])
    assert _visivel(_um(secao, classe="fronteira-de-escopo")) == (
        CATALOGO["fronteiras_de_escopo"][classe]["rotulo"]["pt-BR"])

    nada = _secao(_aba(_pagina(_entrega()), "evidencia"), EVIDENCIA["lacunas_titulo"])
    assert _visivel(nada) == f'{EVIDENCIA["lacunas_titulo"]} {EVIDENCIA["lacunas_vazio"]}'


def test_o_confronto_mostra_a_analise_fornecida_e_cada_divergencia_com_a_classificacao_rotulada():
    entrega_dict = _entrega()
    confronto = _confronto()
    outra = sorted(entrega.CLASSIFICACOES_DE_DIVERGENCIA - {confronto["divergencias"][0]["classificacao"]})[0]
    confronto["divergencias"].append({
        "item": "Margem normalizada", "classificacao": outra, "anterior": "Sem o segmento novo",
        "atual": "Com o segmento novo consolidado", "explicacao": "A companhia passou a publicar o segmento."})
    entrega_dict["confronto"] = confronto

    secao = _secao(_aba(_pagina(entrega_dict), "evidencia"), EVIDENCIA["confronto_titulo"])
    fornecida = confronto["analise_fornecida"]
    cabecalho = _visivel(_um(secao, classe="confronto-analise-fornecida"))
    assert cabecalho == render.t(DICIONARIO, "evidencia.confronto_analise_fornecida",
                                 identificacao=fornecida["identificacao"], data=fornecida["data"])
    assert fornecida["identificacao"] in cabecalho and fornecida["data"] in cabecalho
    assert _linhas(_um(secao, tag="table")) == [
        [divergencia["item"], _rotulo("classificacoes_de_divergencia", divergencia["classificacao"]),
         divergencia["anterior"], divergencia["atual"], divergencia["explicacao"]]
        for divergencia in confronto["divergencias"]]


def test_todo_valor_de_vocabulario_do_contrato_do_ledger_e_do_entrega_tem_rotulo_em_todo_dicionario():
    """Trava de cobertura: classes de fonte, tipos de localizador, estatutos, materialidades e âncoras
    do consenso, lidos do contrato, e as classificações de divergência do `entrega.py` — cada grupo
    rotulado exatamente, sem rótulo faltando nem sobrando, em todo dicionário publicado."""
    esperados = {nome: set(vocabulario) for nome, vocabulario in _VOCABULARIOS.items()}
    esperados["classificacoes_de_divergencia"] = set(entrega.CLASSIFICACOES_DE_DIVERGENCIA)
    dicionarios = sorted((SCRIPTS.parent / "assets" / "i18n").glob("*.json"))
    assert dicionarios and len(esperados) == 6

    for caminho in dicionarios:
        evidencia = json.loads(caminho.read_text(encoding="utf-8"))["interface"]["evidencia"]
        for nome, valores in esperados.items():
            rotulos = evidencia.get(nome) or {}
            assert set(rotulos) == valores, (caminho.name, nome, sorted(set(rotulos) ^ valores))
            assert all(isinstance(rotulo, str) and rotulo.strip() and rotulo != chave
                       for chave, rotulo in rotulos.items()), (caminho.name, nome)


# --- D3/D4: os avisos e o consenso na Tese ---------------------------------

def test_a_lacuna_material_sai_nos_avisos_com_o_numero_resolvido_e_o_qc_json_guarda_o_texto_cru(tmp_path):
    """A Tese mostra a descrição que a lista de prosa resolveu — o preço formatado, nunca `{{...}}` —, e o
    `qc.json`, o artefato interno, continua com o texto cru."""
    entrega_dict = _entrega()
    descricao = "O preço de tela, {{caso:preco.valor|moeda}}, não tem série histórica ajustada."
    tratamento = "O histórico entra só como referência qualitativa."
    entrega_dict["ledger"]["lacunas"] = [_lacuna(id="historico", descricao=descricao, tratamento=tratamento,
                                                 materialidade=MATERIALIDADE_COM_DISCLOSURE)]
    raiz = tmp_path / "lacuna_material"
    apoio.escrever_raiz(raiz, entrega_dict)

    resultado = _rodar_builder(raiz)

    assert resultado.returncode == 0, resultado.stdout + resultado.stderr
    preco = _moeda_do_caso(entrega_dict, entrega_dict["caso"]["preco"]["valor"])
    pagina = (raiz / "relatorio.html").read_text(encoding="utf-8")
    (aviso,) = [_visivel(item) for item in _todos(_secao(_aba(pagina, "tese"), TESE["disclosures_titulo"]), tag="li")]
    assert aviso == DICIONARIO["qc"]["lacuna_material"].format(
        descricao=descricao.replace("{{caso:preco.valor|moeda}}", preco), tratamento=tratamento)
    assert preco in aviso and "{{" not in aviso

    (achado,) = _ler_qc(raiz)["achados"]
    assert (achado["params"]["descricao"], achado["mensagem"]) == (
        descricao, DICIONARIO["qc"]["lacuna_material"].format(descricao=descricao, tratamento=tratamento))


def test_o_consenso_sai_na_conclusao_com_uma_linha_por_registro_tambem_sob_fronteira_de_escopo():
    """D4: sob o título de referência externa, uma linha por registro citado — claim e período, valor
    formatado pelo idioma e unidade, fonte e data de acesso. Sob fronteira de escopo, igual: é leitura
    de mercado, como o múltiplo de tela."""
    for entrega_dict in (_entrega(), apoio.montar_entrega(FIXTURE, mutar_caso=_com_fronteira_de_escopo)):
        segundo = apoio.registro_do_ledger(
            "consenso-receita", "Consenso de receita líquida", "Provedor de consenso", 2750.5,
            periodo="2026E", moeda="BRL", unidade="R$ milhões", data_acesso="2026-09-10")
        _registros(entrega_dict).append(segundo)
        entrega_dict["analise"]["consenso"]["registros"].append(segundo["id"])
        por_id = {registro["id"]: registro for registro in _registros(entrega_dict)}
        citados = [por_id[ident] for ident in entrega_dict["analise"]["consenso"]["registros"]]
        assert len(citados) == 2

        consenso = _um(_secoes(_aba(_pagina(entrega_dict), "tese"))[0], classe="tese-consenso")
        linhas = [_visivel(item) for item in _todos(consenso, tag="li")]
        assert (_titulo(consenso), linhas) == (TESE["consenso_titulo"], [
            render.t(DICIONARIO, "tese.consenso_linha", claim=registro["claim"], periodo=registro["periodo"],
                     valor=_valor_do_ledger(registro["valor"]), unidade=registro["unidade"],
                     fonte=registro["fonte"]["identidade"], data=registro["data_acesso"])
            for registro in citados])
        for linha, registro in zip(linhas, citados):
            for trecho in (registro["claim"], registro["periodo"], _valor_do_ledger(registro["valor"]),
                           registro["fonte"]["identidade"], registro["data_acesso"]):
                assert trecho in linha, (trecho, linha)


def test_consenso_ausente_sai_so_nos_avisos_com_o_rotulo_da_ancora_e_a_razao_resolvida():
    """Sem consenso, nada na Conclusão: o aviso `consenso_indisponivel` diz a âncora que entra no lugar
    pelo rótulo do dicionário — nunca a chave crua (a lição do B2) — e a razão resolvida."""
    entrega_dict = _entrega()
    entrega_dict["analise"]["consenso"] = {
        "ausente": {"ancora": ANCORA, "razao": "Nenhum provedor cobre a companhia desde {{livre:2024}}."}}

    tese = _aba(_pagina(entrega_dict), "tese")

    (aviso,) = [_visivel(item) for item in _todos(_secao(tese, TESE["disclosures_titulo"]), tag="li")]
    assert aviso == DICIONARIO["qc"]["consenso_indisponivel"].format(
        razao="Nenhum provedor cobre a companhia desde 2024.", ancora=_rotulo("ancoras_do_consenso", ANCORA))
    assert f"'{ANCORA}'" not in aviso and "{{" not in aviso
    assert _todos(_secoes(tese)[0], classe="tese-consenso") == []


# --- D6: a ficha técnica ------------------------------------------------------

def test_a_ficha_tecnica_compoe_a_execucao_os_contratos_as_contagens_e_os_achados_e_a_evidencia_a_mostra():
    """D6: a execução; a metodologia e o hash do caso, de `resultados.origem`; as versões lidas dos
    próprios artefatos; os registros por estatuto e por classe de fonte e os achados por nível e código,
    em ordem que não depende da ordem do ledger nem da dos achados. A Evidência a mostra com os rótulos
    do dicionário — sem o QUALITY WARNING, que é interno (§11)."""
    entrega_dict = _entrega()
    _que_sustenta(entrega_dict, "preco.valor")["estatuto"] = ESTATUTO_ESTIMADO
    outra_classe = next(classe for classe in _VOCABULARIOS["classes_de_fonte"] if classe != CLASSE)
    _que_sustenta(entrega_dict, "acoes_diluidas")["fonte"]["classe"] = outra_classe
    for registro in _registros(entrega_dict):
        if registro.get("usado_em"):
            registro["fonte"]["identidade"] = "fonte dominante"
    achados = _achados(entrega_dict)
    assert [(a.nivel, a.codigo) for a in achados] == [
        ("REQUIRED_DISCLOSURE", "insumo_estimado"), ("QUALITY_WARNING", "concentracao_de_fontes")]

    registros, resultados = _registros(entrega_dict), entrega_dict["resultados"]
    esperada = {
        "execucao": {campo: entrega_dict["execucao"][campo] for campo in ("id", "ticker", "idioma")},
        "metodologia": {"nome": resultados["origem"]["metodologia"]["nome"],
                        "versao": resultados["origem"]["metodologia"]["versao"],
                        "caso_sha256": resultados["origem"]["caso_sha256"]},
        "contratos": {"entrega": entrega_dict["versao_contrato"], "resultados": resultados["versao_contrato"],
                      "catalogo": CATALOGO["versao_contrato"], "ledger": entrega_dict["ledger"]["versao_contrato"]},
        "registros_por_estatuto": dict(sorted(Counter(r["estatuto"] for r in registros).items())),
        "registros_por_classe_de_fonte": dict(sorted(Counter(r["fonte"]["classe"] for r in registros).items())),
        "achados": {nivel: dict(sorted(Counter(a.codigo for a in achados if a.nivel == nivel).items()))
                    for nivel in qc.NIVEIS},
    }
    assert len(esperada["registros_por_estatuto"]) == len(esperada["registros_por_classe_de_fonte"]) == 2
    como_arquivo = json.dumps(esperada, ensure_ascii=False)
    assert json.dumps(builder.compor_ficha_tecnica(entrega_dict, CATALOGO, achados), ensure_ascii=False) == como_arquivo
    invertida = copy.deepcopy(entrega_dict)
    invertida["ledger"]["registros"].reverse()
    assert json.dumps(builder.compor_ficha_tecnica(invertida, CATALOGO, achados[::-1]), ensure_ascii=False) == como_arquivo

    pagina = _pagina(entrega_dict)
    blocos, campos = EVIDENCIA["ficha_tecnica_blocos"], EVIDENCIA["ficha_tecnica_campos"]
    niveis = EVIDENCIA["ficha_tecnica_niveis"]
    secao = _secao(_aba(pagina, "evidencia"), EVIDENCIA["ficha_tecnica_titulo"])
    assert [(_titulo(grupo), _pares(_um(grupo, tag="table")))
            for grupo in _todos(secao, classe="ficha-tecnica-grupo")] == [
        *[(blocos[bloco], [(campos[bloco][campo], valor) for campo, valor in esperada[bloco].items()])
          for bloco in ("execucao", "metodologia", "contratos")],
        (blocos["registros_por_estatuto"], [(_rotulo("estatutos", estatuto), _contagem(quantidade))
                                            for estatuto, quantidade in esperada["registros_por_estatuto"].items()]),
        (blocos["registros_por_classe_de_fonte"], [(_rotulo("classes_de_fonte", classe), _contagem(quantidade))
                                                   for classe, quantidade in esperada["registros_por_classe_de_fonte"].items()]),
        (blocos["achados"], [(niveis["HARD_FAIL"], EVIDENCIA["ficha_tecnica_nenhum_achado"]),
                             (niveis["REQUIRED_DISCLOSURE"], render.t(DICIONARIO, "evidencia.ficha_tecnica_contagem",
                                                                      codigo="insumo_estimado", quantidade=_contagem(1)))]),
    ]
    assert "concentracao_de_fontes" not in apoio.prosa_da_pagina(pagina)


def test_a_ficha_tecnica_sai_em_arquivo_identica_byte_a_byte_em_duas_emissoes_e_sem_caminho(tmp_path):
    """D6 (§15, decisão 10: "também em arquivo"): o builder grava `ficha-tecnica.json` ao lado do
    relatório. Duas emissões da mesma entrega, em raízes de nomes diferentes, gravam os mesmos bytes —
    nenhum relógio e nenhum caminho —, e o arquivo é a ficha que a Evidência mostra."""
    entrega_dict = _entrega()
    conteudos = []
    for nome in ("primeira-raiz", "outra-raiz-de-execucao"):
        raiz = tmp_path / nome
        apoio.escrever_raiz(raiz, entrega_dict)
        resultado = _rodar_builder(raiz)
        assert resultado.returncode == 0, resultado.stdout + resultado.stderr
        conteudo = (raiz / NOME_DA_FICHA).read_bytes()
        assert nome.encode("utf-8") not in conteudo
        conteudos.append(conteudo)
    assert conteudos[0] == conteudos[1]

    ficha = json.loads(conteudos[0])
    assert ficha == builder.compor_ficha_tecnica(entrega_dict, CATALOGO, _achados(entrega_dict))
    pagina = (tmp_path / "primeira-raiz" / "relatorio.html").read_text(encoding="utf-8")
    exibida = _visivel(_secao(_aba(pagina, "evidencia"), EVIDENCIA["ficha_tecnica_titulo"]))
    assert ficha["metodologia"]["caso_sha256"] in exibida and ficha["execucao"]["id"] in exibida


def test_a_ficha_tecnica_nao_sobra_depois_de_um_hard_fail_nem_de_uma_recusa_codigo_1_na_mesma_raiz(tmp_path):
    """A ficha é gravada só quando o relatório é gravado, e a limpeza da saída anterior a inclui: um HARD
    FAIL deixa só `qc.json`, e uma recusa código 1 não deixa nada — nunca a ficha de uma rodada anterior."""
    raiz = tmp_path / "raiz_reusada"
    saidas = ("relatorio.html", "qc.json", NOME_DA_FICHA)
    sem_proveniencia = _entrega()
    _registros(sem_proveniencia).remove(_que_sustenta(sem_proveniencia, "preco.valor"))

    def _rodada(entrega_dict: dict | None, codigo: int) -> list:
        if entrega_dict is None:
            (raiz / "entrega.json").write_text("{ isto não é json", encoding="utf-8")
        else:
            apoio.escrever_raiz(raiz, entrega_dict)
        resultado = _rodar_builder(raiz)
        assert resultado.returncode == codigo, resultado.stdout + resultado.stderr
        return [nome for nome in saidas if (raiz / nome).exists()]

    assert _rodada(_entrega(), 0) == list(saidas)
    assert _rodada(sem_proveniencia, 2) == ["qc.json"]
    assert _rodada(_entrega(), 0) == list(saidas)
    assert _rodada(None, 1) == []


def test_texto_de_dado_com_a_assinatura_de_uma_referencia_emite_e_sai_como_declarado(tmp_path):
    """Medido na Task 3: a regra de autocontenção lê `data=`, `href=`, `src=`, `url(` e `@import` em todo o
    HTML fora dos `<script>`, e um localizador com `?data=` na query — dado da Evidência, nunca recurso que
    a página carrega — fazia o builder recusar um relatório válido (código 2); a prosa da Tese tem o mesmo
    falso positivo desde a 5A. A página escreve todo texto de dado por um helper só, e a regra do QC não
    muda: o endereço, o parâmetro, a justificativa e o texto da Tese emitem e saem idênticos ao declarado
    no texto que o analista lê, e a MESMA página, com uma referência externa de verdade na marcação,
    continua recusada."""
    entrega_dict = _entrega()
    registro = _que_sustenta(entrega_dict, "preco.valor")
    endereco = "https://ri.exemplo.com/doc?data=2025-12-31&href=x"
    justificativa = "A bolsa publica o fechamento; o feed antigo usava @import e src=legado."
    registro.update(localizador={"tipo": TIPO_DE_LOCALIZADOR, "valor": endereco, "parametros": {"url(": "fechamento"}},
                    justificativa_da_fonte=justificativa)
    veredicto = "A tela embute o fechamento de data=hoje, e o endereço url(ri) o confirma."
    entrega_dict["analise"]["veredicto"]["texto"] = veredicto
    raiz = tmp_path / "texto_de_dado"
    apoio.escrever_raiz(raiz, entrega_dict)

    resultado = _rodar_builder(raiz)

    assert resultado.returncode == 0, resultado.stdout + resultado.stderr
    assert _ler_qc(raiz)["achados"] == []
    pagina = (raiz / "relatorio.html").read_text(encoding="utf-8")
    campos = EVIDENCIA["registro_campos"]
    ledger = _secao(_aba(pagina, "evidencia"), EVIDENCIA["ledger_titulo"])
    exibidos = dict(_pares(_tabela_do_registro(ledger, registro["id"])))
    assert [exibidos[campos[nome]] for nome in ("localizador_valor", "localizador_parametros",
                                                "justificativa_da_fonte")] == [endereco, "url(: fechamento", justificativa]
    assert _visivel(_um(_aba(pagina, "tese"), classe="tese-veredicto-texto")) == veredicto

    assert _do_codigo(qc.avaliar(entrega_dict, CATALOGO, CONTRATO, html=pagina), "relatorio_nao_autocontido") == []
    externa = "https://externo.exemplo.com/marca.png"
    injetada = pagina.replace("</body>", f'<img src="{externa}"></body>', 1)
    assert [achado.params["valor"] for achado in _do_codigo(
        qc.avaliar(entrega_dict, CATALOGO, CONTRATO, html=injetada), "relatorio_nao_autocontido")] == [externa]
