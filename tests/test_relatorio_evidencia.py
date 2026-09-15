"""O ledger no contrato `entrega/1`, o consenso e o confronto, e as regras da §11 que dependem do
ledger (fatia 5E, item 5, Task 2) — sem render.

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
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
SCRIPTS = RAIZ / "skills" / "er-relatorio" / "scripts"
BUILDER = SCRIPTS / "builder.py"

sys.path.insert(0, str(SCRIPTS))
import builder  # noqa: E402
import entrega  # noqa: E402
import placeholders  # noqa: E402
import qc  # noqa: E402

sys.path.insert(0, str(RAIZ / "tests"))
import relatorio_apoio as apoio  # noqa: E402

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
         {"id": registro["id"], "claim": registro["claim"]})]


def test_registro_estimado_que_nao_sustenta_insumo_nao_e_disclosure():
    entrega_dict = _entrega()
    (consenso,) = [r for r in _registros(entrega_dict) if r["id"] in entrega_dict["analise"]["consenso"]["registros"]]
    consenso["estatuto"] = ESTATUTO_ESTIMADO
    assert _do_codigo(_achados(entrega_dict), "insumo_estimado") == []


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
