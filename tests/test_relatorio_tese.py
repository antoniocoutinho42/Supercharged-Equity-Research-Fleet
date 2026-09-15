"""A Tese no contrato `entrega/1` e as regras da §11 que são dela (fatia 5D, item 5,
Task 2) — sem render.

Ver docs/superpowers/plans/2026-09-14-v4-item5d-tese.md: D1 (a Tese no contrato),
D2 (vocabulário de vínculo), D4 (a reversa exigida), D5 (o vínculo mora só na
pergunta) e D6 (as regras da §11). Três famílias de teste:

- FORMA, código 1 (`entrega.carregar`): chave desconhecida, tipo errado, campo
  obrigatório ausente e vocabulário fechado — a recusa nomeia o campo e sugere por
  `difflib`. Uma recusa por nível do contrato.
- CONTEÚDO, código 2 (`qc.avaliar`): cada regra de D6 com um caso que dispara e um
  vizinho que não dispara.
- A limitação da reversa: o disclosure nomeado no `qc.json` de `caso_degrau` e de
  `caso_rampa`, pelo CLI de verdade.
- A ABA RENDERIZADA (Task 3, D3/D5/D7): a ordem das seções, a faixa e o preço de tela,
  os rótulos no lugar das chaves, o pareamento de cada gráfico ao seu host, o log de
  toda a prosa na Evidência, a fronteira de escopo e a faixa de um caso SOTP. Toda
  asserção lê o TEXTO que o analista vê (`apoio.prosa_da_pagina`), nunca um atributo.

E3: o relatório nunca aprende metodologia. O vocabulário de vínculo sai do catálogo
(`test_o_vocabulario_de_vinculo_sai_do_catalogo`), e o que torna uma limitação "de
reversa" é a declaração `afeta` da integração, nunca o nome da chave
(`test_o_qc_le_a_declaracao_afeta_e_nunca_o_nome_da_chave`).

Entregas vêm de `tests/relatorio_apoio.py`, que roda `avaliar()` de verdade e compõe
a Tese padrão e a reversa onde o gate a admite; cada teste recebe a sua cópia.
"""

import copy
import functools
import json
import os
import re
import shutil
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
SCRIPTS = RAIZ / "skills" / "er-relatorio" / "scripts"
BUILDER = SCRIPTS / "builder.py"

sys.path.insert(0, str(SCRIPTS))
import builder  # noqa: E402
import entrega  # noqa: E402
import exhibits as exhibits_mod  # noqa: E402
import placeholders  # noqa: E402
import qc  # noqa: E402
import render  # noqa: E402

sys.path.insert(0, str(RAIZ / "tests"))
import relatorio_apoio as apoio  # noqa: E402

CATALOGO = json.loads(
    (RAIZ / "skills" / "er-valuation" / "assets" / "catalogo_apresentacao.json").read_text(encoding="utf-8"))
CASOS = sorted(p.name for p in apoio.FIXTURES.glob("caso_*.json"))
FIXTURE = "caso_minimo_firm.json"
ENV_UTF8 = {**os.environ, "PYTHONUTF8": "1", "PYTHONDONTWRITEBYTECODE": "1", "PYTHONIOENCODING": "utf-8"}


def _rodar_builder(raiz: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(BUILDER), str(raiz)],
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace", env=ENV_UTF8, timeout=120)


def _ler_qc(raiz: Path) -> dict:
    return json.loads((raiz / "qc.json").read_text(encoding="utf-8"))


def _tres_cenarios(caso: dict) -> None:
    """Um cenário de cada lado do base, pelo crescimento. A ordem dos preços é
    conferida no teste que usa esta variante, nunca presumida."""
    for nome, g in (("pessimista", 3.0), ("otimista", 7.0)):
        caso["cenarios"][nome] = json.loads(json.dumps(caso["cenarios"]["base"]))
        caso["cenarios"][nome]["premissas"]["g"] = g
    caso["cenario_base"] = "base"


def _com_fronteira_de_escopo(caso: dict) -> None:
    caso["fronteira_de_escopo"] = {
        "classe": "pre_lucro",
        "arquitetura_dominante": "opção sobre a conversão do funil em receita recorrente",
        "razao": "sem lucro operacional; a métrica-manchete da metodologia não se aplica",
    }


def _alias_legado_de_tv(caso: dict) -> None:
    """`spread` é alias de `gordon`: o gate o aceita, e `resultados.cenarios.<nome>.
    premissas` o repete como o caso o declara."""
    caso["cenarios"]["base"]["premissas"]["tv"] = "spread"


def _tres_cenarios_sob_fronteira(caso: dict) -> None:
    _tres_cenarios(caso)
    _com_fronteira_de_escopo(caso)


_VARIANTES = {"padrao": None, "tres_cenarios": _tres_cenarios, "fronteira": _com_fronteira_de_escopo,
              "alias_tv": _alias_legado_de_tv, "tres_cenarios_sob_fronteira": _tres_cenarios_sob_fronteira}


@functools.lru_cache(maxsize=None)
def _entrega_serializada(fixture: str, variante: str, compor_reversa: bool) -> str:
    """`montar_entrega` cacheado (roda o motor por subprocesso). Devolve JSON para
    que cada teste receba a sua própria cópia — quase todos adulteram a entrega."""
    entrega_dict = apoio.montar_entrega(fixture, mutar_caso=_VARIANTES[variante],
                                        compor_reversa=compor_reversa)
    return json.dumps(entrega_dict, ensure_ascii=False)


def _entrega(fixture: str = FIXTURE, variante: str = "padrao", compor_reversa: bool = True) -> dict:
    return json.loads(_entrega_serializada(fixture, variante, compor_reversa))


def _achados(entrega_dict: dict, catalogo: dict = CATALOGO) -> list:
    return qc.avaliar(entrega_dict, catalogo, apoio.CONTRATO_LEDGER, html=None)


def _do_codigo(achados: list, codigo: str) -> list:
    return [a for a in achados if a.codigo == codigo]


def _carregar(entrega_dict: dict, tmp_path: Path) -> dict:
    raiz = tmp_path / "raiz"
    apoio.escrever_raiz(raiz, entrega_dict)
    return entrega.carregar(raiz, apoio.CONTRATO_LEDGER)


# --------------------------------------------------------------------------
# A entrega padrão do apoio: válida no contrato e sem disparar regra nenhuma por
# conta própria (armadilha 2 do briefing). Os únicos achados são os disclosures
# NOMEADOS que o próprio caso impõe — o de divergência de base do degrau, e o da
# limitação que torna a reversa impossível (D4) em `caso_degrau` e `caso_rampa`. Desde a
# 5F (D3), também o da curva iso-valor não calculada nas duas SOTP: a reversa composta
# sobre o cenário consolidado deixa um eixo primário sem raiz, e a integração publica
# `iso_nao_calculada` em `resultados.limitacoes`. E, desde a 5F (Task 4, D11), o da premissa
# central fora do ponto central da grade em `caso_reversa_firm`: a grade 2D tem o ROIC em
# quatro pontos em torno de 12, e um eixo de comprimento par não tem ponto central.
# --------------------------------------------------------------------------

_ACHADOS_DA_ENTREGA_PADRAO = {
    "caso_degrau.json": [("REQUIRED_DISCLOSURE", "divergencia_de_base_degrau"),
                         ("REQUIRED_DISCLOSURE", "limitacao_metodologica")],
    "caso_rampa.json": [("REQUIRED_DISCLOSURE", "limitacao_metodologica")],
    "caso_reversa_firm.json": [("REQUIRED_DISCLOSURE", "premissa_central_fora_do_ponto_central_da_grade")],
    "caso_sotp_homogeneo.json": [("REQUIRED_DISCLOSURE", "limitacao_metodologica")],
    "caso_sotp_safra.json": [("REQUIRED_DISCLOSURE", "limitacao_metodologica")],
}


@pytest.mark.parametrize("fixture", CASOS)
def test_a_entrega_padrao_passa_no_contrato_e_so_traz_os_achados_nomeados(fixture, tmp_path):
    entrega_dict = _entrega(fixture)
    _carregar(entrega_dict, tmp_path)
    assert [(a.nivel, a.codigo) for a in _achados(entrega_dict)] == _ACHADOS_DA_ENTREGA_PADRAO.get(fixture, [])


# --------------------------------------------------------------------------
# FORMA (código 1): uma recusa por nível do contrato da Tese, e as condicionais
# de D1/D5 — `faixa` exigida fora da fronteira; `exhibits` XOR `sem_exhibit`;
# exhibit citado que existe; `exhibits[].vinculo` fora do vocabulário (D5).
# --------------------------------------------------------------------------

_EXHIBIT = {
    "id": "margem", "pergunta": "Quanto vale a ação no cenário da manchete?", "tipo": "barras",
    "nota_janela": "um único ponto, de propósito",
    "series": [{"derivacao": "engine", "chave": "resultados:manchete.preco_acao",
                "rotulo": "preço por ação no cenário da manchete"}],
}


def _renomear(objeto: dict, de: str, para: str) -> None:
    objeto[para] = objeto.pop(de)


def _citar_exhibit(entrega_dict: dict, exhibit_id: str) -> None:
    analise = entrega_dict["analise"]
    analise["exhibits"] = [copy.deepcopy(_EXHIBIT)]
    pergunta = analise["perguntas"][0]
    del pergunta["sem_exhibit"]
    pergunta["exhibits"] = [exhibit_id]


def _exhibits_e_sem_exhibit(entrega_dict: dict) -> None:
    _citar_exhibit(entrega_dict, _EXHIBIT["id"])
    entrega_dict["analise"]["perguntas"][0]["sem_exhibit"] = {"razao": "Um gráfico não acrescenta."}


def _id_repetido(entrega_dict: dict) -> None:
    perguntas = entrega_dict["analise"]["perguntas"]
    perguntas[1]["id"] = perguntas[0]["id"]


_RECUSAS_DE_FORMA = [
    pytest.param(lambda e: _renomear(e["analise"], "perguntas", "pergunta"),
                 ["chave desconhecida em 'analise'", "'pergunta'", "Você quis dizer 'perguntas'?"],
                 id="analise-chave-desconhecida"),
    pytest.param(lambda e: e["analise"].pop("riscos"),
                 ["campo obrigatório ausente em 'analise': 'riscos'"],
                 id="analise-campo-obrigatorio"),
    pytest.param(lambda e: e["analise"].pop("faixa"),
                 ["campo obrigatório ausente em 'analise': 'faixa'"],
                 id="faixa-ausente-fora-da-fronteira"),
    pytest.param(lambda e: _renomear(e["analise"]["faixa"], "teto", "tetto"),
                 ["chave desconhecida em 'analise.faixa'", "'tetto'", "Você quis dizer 'teto'?"],
                 id="faixa"),
    pytest.param(lambda e: e["analise"]["veredicto"].update(texto="   "),
                 ["'analise.veredicto.texto' ausente ou vazio"],
                 id="veredicto"),
    pytest.param(lambda e: _renomear(e["analise"]["premissas_decisivas"][0], "derivacao", "derivação"),
                 ["chave desconhecida em 'analise.premissas_decisivas.0'", "'derivação'",
                  "Você quis dizer 'derivacao'?"],
                 id="premissas_decisivas"),
    pytest.param(lambda e: e["analise"]["positives"][0].update(vetor="earning-power"),
                 ["'analise.positives.0.vetor' fora do vocabulário", "'earning-power'",
                  "Você quis dizer 'earning_power'?"],
                 id="positives-vetor"),
    pytest.param(lambda e: e["analise"]["positives"][0].update(mecanismo=[]),
                 ["'analise.positives.0.mecanismo'"],
                 id="positives-mecanismo-vazio"),
    pytest.param(lambda e: e["analise"]["negatives"][0].pop("razao"),
                 ["campo obrigatório ausente em 'analise.negatives.0': 'razao'"],
                 id="negatives-nao-incorporado-sem-razao"),
    pytest.param(lambda e: e["analise"]["perguntas"][2].update(tema="rentabilidade"),
                 ["'analise.perguntas.2.tema' fora do vocabulário",
                  "Você quis dizer 'rentabilidade_do_crescimento'?"],
                 id="perguntas-tema"),
    pytest.param(lambda e: e["analise"]["perguntas"][0].update(vinculo=[]),
                 ["'analise.perguntas.0.vinculo'"],
                 id="perguntas-vinculo-vazio"),
    pytest.param(_id_repetido,
                 ["'analise.perguntas' repete o id"],
                 id="perguntas-id-repetido"),
    pytest.param(lambda e: e["analise"]["perguntas"][1].pop("sem_exhibit"),
                 ["'analise.perguntas.1' não declara 'exhibits' nem 'sem_exhibit'"],
                 id="perguntas-sem-exhibits-nem-sem-exhibit"),
    pytest.param(_exhibits_e_sem_exhibit,
                 ["'analise.perguntas.0' declara 'exhibits' e 'sem_exhibit' ao mesmo tempo"],
                 id="perguntas-exhibits-e-sem-exhibit"),
    pytest.param(lambda e: _citar_exhibit(e, "margen"),
                 ["'analise.perguntas.0.exhibits.0'", "'margen'", "Você quis dizer 'margem'?"],
                 id="perguntas-exhibit-inexistente"),
    pytest.param(lambda e: e["analise"]["perguntas"][0].update(sem_exhibit={}),
                 ["campo obrigatório ausente em 'analise.perguntas.0.sem_exhibit': 'razao'"],
                 id="perguntas-sem_exhibit"),
    pytest.param(lambda e: e["analise"]["riscos"][0].pop("observavel"),
                 ["campo obrigatório ausente em 'analise.riscos.0': 'observavel'"],
                 id="riscos"),
    pytest.param(lambda e: e["analise"].update(visao_nao_consensual={"text": "O mercado subestima a vantagem."}),
                 ["chave desconhecida em 'analise.visao_nao_consensual'", "'text'", "Você quis dizer 'texto'?"],
                 id="visao_nao_consensual"),
    pytest.param(lambda e: e["analise"].update(
                     mudou_desde_analise_fornecida={"linhas": ["Uma.", "Outra.", "Mais uma.", "E a última."]}),
                 ["'analise.mudou_desde_analise_fornecida.linhas'", "no máximo"],
                 id="mudou_desde_analise_fornecida"),
    pytest.param(lambda e: e["analise"].update(exhibits=[dict(copy.deepcopy(_EXHIBIT), vinculo=["moat"])]),
                 ["chave desconhecida em 'analise.exhibits.0'", "'vinculo'"],
                 id="exhibits-vinculo-D5"),
    # Task 3: a pergunta cita o exhibit pelo id, e o gráfico é pareado ao seu host pelo
    # índice desse id — um id repetido tornaria as duas ligações ambíguas.
    pytest.param(lambda e: e["analise"].update(exhibits=[copy.deepcopy(_EXHIBIT), copy.deepcopy(_EXHIBIT)]),
                 ["'analise.exhibits' repete o id 'margem'"],
                 id="exhibits-id-repetido"),
    # Onda de correção da revisão final (N12): a série `engine` declara o rótulo que o gráfico
    # escreve — sem ele, a legenda e o cabeçalho da tabela mostravam a chave crua.
    pytest.param(lambda e: e["analise"].update(exhibits=[dict(
                     copy.deepcopy(_EXHIBIT),
                     series=[{"derivacao": "engine", "chave": "resultados:manchete.preco_acao"}])]),
                 ["'analise.exhibits.0.series.0.rotulo' ausente ou vazio"],
                 id="serie-engine-sem-rotulo-N12"),
    pytest.param(lambda e: e["resultados"].pop("fronteira_de_escopo"),
                 ["'resultados.fronteira_de_escopo' ausente"],
                 id="resultados-sem-fronteira-de-escopo"),
]


@pytest.mark.parametrize("adulterar,trechos", _RECUSAS_DE_FORMA)
def test_forma_da_tese_e_recusa_de_contrato_nomeada(adulterar, trechos, tmp_path):
    entrega_dict = _entrega()
    _carregar(entrega_dict, tmp_path)  # o vizinho: sem a adulteração, o contrato aceita

    adulterar(entrega_dict)
    with pytest.raises(entrega.EntregaInvalida) as erro:
        _carregar(entrega_dict, tmp_path)
    for trecho in trechos:
        assert trecho in str(erro.value), str(erro.value)


def test_pergunta_que_cita_um_exhibit_declarado_passa_no_contrato(tmp_path):
    entrega_dict = _entrega()
    _citar_exhibit(entrega_dict, _EXHIBIT["id"])
    assert _carregar(entrega_dict, tmp_path)["analise"]["perguntas"][0]["exhibits"] == [_EXHIBIT["id"]]


def test_recusa_de_forma_da_tese_sai_pelo_codigo_1_sem_escrever_nada(tmp_path):
    """O mesmo canal de toda recusa de contrato (5A/5B): código 1, nada escrito,
    a razão em stderr nomeando o campo e sugerindo."""
    entrega_dict = _entrega()
    entrega_dict["analise"]["perguntas"][2]["tema"] = "rentabilidade"
    raiz = tmp_path / "tema_errado"
    apoio.escrever_raiz(raiz, entrega_dict)

    resultado = _rodar_builder(raiz)

    assert resultado.returncode == 1, resultado.stdout + resultado.stderr
    assert not (raiz / "qc.json").exists()
    assert not (raiz / "relatorio.html").exists()
    assert "'analise.perguntas.2.tema'" in resultado.stderr
    assert "'rentabilidade_do_crescimento'" in resultado.stderr


# --------------------------------------------------------------------------
# HARD FAIL `perguntas_da_tese_incompletas` (§7): de três a cinco perguntas, cada
# tema obrigatório exatamente uma vez, no máximo duas específicas.
# --------------------------------------------------------------------------

def _pergunta_especifica(ident: str) -> dict:
    return {
        "id": ident, "tema": "especifica",
        "pergunta": "A renovação da concessão se confirma no prazo?",
        "evidencia": "Histórico de renovações do regulador.",
        "observavel": "Edital de renovação publicado.",
        "vinculo": ["wacc"],
        "sem_exhibit": {"razao": "Evento binário; um gráfico não acrescenta informação."},
    }


def _incompletas(entrega_dict: dict) -> list:
    return _do_codigo(_achados(entrega_dict), "perguntas_da_tese_incompletas")


def test_duas_perguntas_sao_incompletas_e_tres_nao():
    padrao = _entrega()
    assert len(padrao["analise"]["perguntas"]) == 3
    assert _incompletas(padrao) == []

    duas = _entrega()
    retirada = duas["analise"]["perguntas"].pop()
    (achado,) = _incompletas(duas)
    assert (achado.nivel, achado.onde) == ("HARD_FAIL", "analise.perguntas")
    assert achado.params["quantidade"] == 2
    assert achado.params["temas_ausentes"] == retirada["tema"]


def test_tema_obrigatorio_repetido_e_incompleto():
    entrega_dict = _entrega()
    perguntas = entrega_dict["analise"]["perguntas"]
    assert [p["tema"] for p in perguntas] == ["moat", "crescimento", "rentabilidade_do_crescimento"]
    perguntas[0]["tema"] = "crescimento"

    (achado,) = _incompletas(entrega_dict)
    assert achado.params["quantidade"] == 3
    assert achado.params["temas_repetidos"] == "crescimento"
    assert achado.params["temas_ausentes"] == "moat"


def test_tres_especificas_sao_demais_e_duas_nao():
    cinco = _entrega()
    cinco["analise"]["perguntas"] += [_pergunta_especifica("concessao"), _pergunta_especifica("tarifa")]
    assert _incompletas(cinco) == []

    seis = _entrega()
    seis["analise"]["perguntas"] += [_pergunta_especifica(nome) for nome in ("concessao", "tarifa", "cambio")]
    (achado,) = _incompletas(seis)
    assert achado.params["quantidade"] == 6
    assert achado.params["especificas"] == 3


# --------------------------------------------------------------------------
# HARD FAIL `vinculo_fora_do_vocabulario` (D2): premissa da ROTA no catálogo, ou
# bloco econômico do catálogo — nada escrito no relatório.
# --------------------------------------------------------------------------

def test_pergunta_com_vinculo_fora_do_vocabulario_nao_emite(tmp_path):
    entrega_dict = _entrega()
    entrega_dict["analise"]["perguntas"][1]["vinculo"] = ["margem_ebitda"]
    raiz = tmp_path / "vinculo_fora"
    apoio.escrever_raiz(raiz, entrega_dict)

    resultado = _rodar_builder(raiz)

    assert resultado.returncode == 2, resultado.stdout + resultado.stderr
    assert not (raiz / "relatorio.html").exists()
    achados = _ler_qc(raiz)["achados"]
    assert [a["codigo"] for a in achados if a["nivel"] == "HARD_FAIL"] == ["vinculo_fora_do_vocabulario"]
    (achado,) = achados
    assert achado["onde"] == "analise.perguntas.1.vinculo.0"
    assert (achado["params"]["item"], achado["params"]["rota"]) == ("margem_ebitda", "firm")


@pytest.mark.parametrize("vinculo,fora", [
    pytest.param(["wacc"], [], id="premissa-da-rota"),
    pytest.param(["custo_capital"], [], id="bloco-economico"),
    pytest.param(["wacc", "ke"], ["ke"], id="premissa-de-outra-rota"),
])
def test_vinculo_da_pergunta_e_premissa_da_rota_ou_bloco_economico(vinculo, fora):
    entrega_dict = _entrega()
    entrega_dict["analise"]["perguntas"][1]["vinculo"] = vinculo
    achados = _do_codigo(_achados(entrega_dict), "vinculo_fora_do_vocabulario")
    assert [(a.nivel, a.params["item"]) for a in achados] == [("HARD_FAIL", item) for item in fora]


@pytest.mark.parametrize("lado", ["positives", "negatives"])
def test_mecanismo_fora_do_vocabulario_e_hard_fail(lado):
    entrega_dict = _entrega()
    entrega_dict["analise"][lado][0]["mecanismo"] = ["roic", "alavancagem_operacional"]
    achados = _do_codigo(_achados(entrega_dict), "vinculo_fora_do_vocabulario")
    assert [(a.nivel, a.onde, a.params["item"]) for a in achados] == [
        ("HARD_FAIL", f"analise.{lado}.0.mecanismo.1", "alavancagem_operacional")]


def test_o_vocabulario_de_vinculo_sai_do_catalogo():
    """D2 e E3: uma premissa nova entra pelo catálogo e o vínculo a aceita, sem
    tocar no relatório."""
    entrega_dict = _entrega()
    entrega_dict["analise"]["perguntas"][1]["vinculo"] = ["margem_ebitda"]
    assert _do_codigo(_achados(entrega_dict), "vinculo_fora_do_vocabulario")

    com_premissa_nova = copy.deepcopy(CATALOGO)
    com_premissa_nova["premissas"]["firm"]["margem_ebitda"] = copy.deepcopy(CATALOGO["premissas"]["firm"]["roic"])
    assert _do_codigo(_achados(entrega_dict, com_premissa_nova), "vinculo_fora_do_vocabulario") == []


# --------------------------------------------------------------------------
# HARD FAIL `premissa_decisiva_fora_do_cenario` (D1): a chave é premissa da rota
# no catálogo e está declarada no cenário da manchete — é desse cenário o número.
# --------------------------------------------------------------------------

@pytest.mark.parametrize("chave,dispara", [
    pytest.param("wacc", False, id="da-rota-e-do-cenario"),
    pytest.param("ke", True, id="de-outra-rota"),
    pytest.param("roic_book", True, id="da-rota-mas-nao-declarada-no-cenario"),
])
def test_premissa_decisiva_e_da_rota_e_do_cenario_da_manchete(chave, dispara):
    entrega_dict = _entrega()
    cenario = entrega_dict["resultados"]["manchete"]["cenario"]
    premissas_do_cenario = entrega_dict["resultados"]["cenarios"][cenario]["premissas"]
    assert "roic_book" in CATALOGO["premissas"]["firm"] and "roic_book" not in premissas_do_cenario

    entrega_dict["analise"]["premissas_decisivas"][0]["chave"] = chave
    achados = _do_codigo(_achados(entrega_dict), "premissa_decisiva_fora_do_cenario")
    esperado = [("HARD_FAIL", "analise.premissas_decisivas.0.chave", chave, cenario)] if dispara else []
    assert [(a.nivel, a.onde, a.params["chave"], a.params["cenario"]) for a in achados] == esperado


# --------------------------------------------------------------------------
# HARD FAIL `faixa_fora_de_ordem` (D1/D6): nomes de cenários publicados, preços em
# ordem (comparação entre outputs, nenhuma conta) e base igual ao cenário da
# manchete.
# --------------------------------------------------------------------------

def _faixa_fora_de_ordem(entrega_dict: dict, **faixa) -> list:
    entrega_dict["analise"]["faixa"] = faixa
    return _do_codigo(_achados(entrega_dict), "faixa_fora_de_ordem")


def _tres_cenarios_conferidos() -> tuple[dict, dict]:
    entrega_dict = _entrega(variante="tres_cenarios")
    precos = {nome: c["valor"]["preco_acao"] for nome, c in entrega_dict["resultados"]["cenarios"].items()}
    assert precos["pessimista"] < precos["base"] < precos["otimista"], precos
    assert entrega_dict["resultados"]["manchete"]["cenario"] == "base"
    assert entrega_dict["analise"]["faixa"] == {"piso": "pessimista", "base": "base", "teto": "otimista"}
    assert _do_codigo(_achados(entrega_dict), "faixa_fora_de_ordem") == []
    return entrega_dict, precos


def test_faixa_com_piso_acima_do_teto_e_hard_fail():
    entrega_dict, precos = _tres_cenarios_conferidos()
    moeda = entrega_dict["caso"]["moeda"]

    (achado,) = _faixa_fora_de_ordem(entrega_dict, piso="otimista", base="base", teto="pessimista")
    assert (achado.nivel, achado.onde) == ("HARD_FAIL", "analise.faixa")
    assert achado.params["preco_piso"] == placeholders.formatar(precos["otimista"], "moeda", "pt-BR", moeda)
    assert achado.params["preco_teto"] == placeholders.formatar(precos["pessimista"], "moeda", "pt-BR", moeda)


def test_faixa_com_base_fora_do_cenario_da_manchete_e_hard_fail():
    entrega_dict, _precos = _tres_cenarios_conferidos()
    (achado,) = _faixa_fora_de_ordem(entrega_dict, piso="pessimista", base="otimista", teto="otimista")
    assert (achado.params["base"], achado.params["cenario_manchete"]) == ("otimista", "base")


def test_faixa_com_cenario_inexistente_e_hard_fail():
    entrega_dict, _precos = _tres_cenarios_conferidos()
    (achado,) = _faixa_fora_de_ordem(entrega_dict, piso="pessimista", base="base", teto="bull")
    assert (achado.params["teto"], achado.params["preco_teto"]) == ("bull", "—")


# --------------------------------------------------------------------------
# HARD FAIL `fronteira_com_preco_alvo` (D3): sob fronteira de escopo, nem faixa
# nem placeholder de preço por ação num texto da Tese. Fora dela, a faixa ausente
# é recusa de FORMA (código 1), testada acima.
# --------------------------------------------------------------------------

def _sob_fronteira() -> dict:
    entrega_dict = _entrega(variante="fronteira")
    assert entrega_dict["resultados"]["fronteira_de_escopo"]["classe"] == "pre_lucro"
    return entrega_dict


def test_sob_fronteira_a_tese_sem_faixa_nem_preco_por_acao_emite_sem_hard_fail(tmp_path):
    entrega_dict = _sob_fronteira()
    assert "faixa" not in _carregar(entrega_dict, tmp_path)["analise"]
    assert [a for a in _achados(entrega_dict) if a.nivel == "HARD_FAIL"] == []


def test_faixa_declarada_sob_fronteira_passa_na_forma_e_e_hard_fail(tmp_path):
    entrega_dict = _sob_fronteira()
    entrega_dict["analise"]["faixa"] = {"piso": "base", "base": "base", "teto": "base"}
    _carregar(entrega_dict, tmp_path)

    achados = _do_codigo(_achados(entrega_dict), "fronteira_com_preco_alvo")
    assert [(a.nivel, a.onde, a.params["classe"]) for a in achados] == [("HARD_FAIL", "analise.faixa", "pre_lucro")]


@pytest.mark.parametrize("caminho,token", [
    pytest.param(("veredicto", "texto"), "{{resultados:manchete.preco_acao|moeda}}", id="manchete-no-veredicto"),
    pytest.param(("positives", 0, "afirmacao"), "{{resultados:cenarios.base.valor.preco_acao|moeda}}",
                 id="cenario-num-positive"),
])
def test_placeholder_de_preco_por_acao_sob_fronteira_e_hard_fail(caminho, token):
    fora = _entrega()
    _acrescentar(fora, caminho, f" Referência: {token}.")
    assert _do_codigo(_achados(fora), "fronteira_com_preco_alvo") == []

    sob = _sob_fronteira()
    _acrescentar(sob, caminho, f" Referência: {token}.")
    achados = _do_codigo(_achados(sob), "fronteira_com_preco_alvo")
    onde = "analise." + ".".join(map(str, caminho))
    assert [(a.nivel, a.onde, a.params["trecho"]) for a in achados] == [("HARD_FAIL", onde, token)]


@pytest.mark.parametrize("token", [
    pytest.param("{{caso:preco.valor|moeda}}", id="preco-de-tela"),
    pytest.param("{{resultados:mercado_tela.valor|x2}}", id="multiplo-de-tela"),
])
def test_leitura_de_mercado_sob_fronteira_nao_e_preco_alvo(token):
    """§14: sob fronteira a entrega mantém a leitura de mercado — o preço e o múltiplo
    de tela não são conclusão de valor."""
    sob = _sob_fronteira()
    _acrescentar(sob, ("veredicto", "texto"), f" Na tela: {token}.")
    assert _do_codigo(_achados(sob), "fronteira_com_preco_alvo") == []


# --------------------------------------------------------------------------
# Onda de correção da revisão final (F2): o QC reconhece conclusão de valor pelo
# mapa que a integração publica (`catalogo.conclusoes_de_valor`), nunca pelo nome
# do campo, e varre os três lugares por onde um número de `resultados` chega à
# Tese: placeholder da prosa, série `engine` e overlay de exhibit. Os quatro casos
# da revisão passavam com RC=0.
# --------------------------------------------------------------------------

_CELULA_DA_GRADE = "{{resultados:sensibilidades.grades_2d.0.celulas.1.1.valor|moeda}}"


@pytest.mark.parametrize("fixture,token,unidade", [
    pytest.param("caso_reversa_firm.json", _CELULA_DA_GRADE, "preço por ação", id="celula-da-grade"),
    pytest.param(FIXTURE, "{{resultados:manchete.upside|pct1}}", "fração", id="upside"),
    pytest.param(FIXTURE, "{{resultados:manchete.multiplo.valor|x2}}", "múltiplo", id="multiplo-justo"),
    pytest.param(FIXTURE, "{{resultados:cenarios.base.valor.Equity|moeda}}", "moeda", id="equity-do-cenario"),
    pytest.param("caso_sotp_segmento.json", "{{resultados:sotp.preco_acao|moeda}}", "preço por ação",
                 id="preco-do-sotp"),
])
def test_conclusao_de_valor_num_texto_da_tese_sob_fronteira_e_hard_fail_nomeando_o_caminho(fixture, token, unidade):
    caminho = token[len("{{resultados:"):].split("|", 1)[0]
    fora = _entrega(fixture)
    _acrescentar(fora, ("veredicto", "texto"), f" Referência: {token}.")
    assert _do_codigo(_achados(fora), "fronteira_com_preco_alvo") == []

    sob = _entrega(fixture, variante="fronteira")
    _acrescentar(sob, ("veredicto", "texto"), f" Referência: {token}.")
    achados = _do_codigo(_achados(sob), "fronteira_com_preco_alvo")
    assert [(a.nivel, a.onde, a.params["trecho"], a.params["caminho"], a.params["unidade"]) for a in achados] == [
        ("HARD_FAIL", "analise.veredicto.texto", token, caminho, unidade)]


_EXHIBIT_DO_PRECO = {"id": "preco", "pergunta": "Quanto vale a ação no cenário da manchete?", "tipo": "tabela",
                     "nota_janela": "Um único ponto: o da manchete.",
                     "series": [{"derivacao": "engine", "chave": "resultados:manchete.preco_acao",
                                 "rotulo": "preço por ação no cenário da manchete"}]}
_EXHIBIT_DA_RECEITA_COM_OVERLAY = {"id": "receita", "pergunta": "Como a receita evoluiu no período?", "tipo": "linha",
                                   "series": [{"derivacao": "direta", "fonte": "fin.receita"}],
                                   "overlays": [{"chave": "resultados:manchete.preco_acao", "rotulo": "preço justo"}]}


def _com_exhibit_sob_a_pergunta(entrega_dict: dict, exhibit: dict) -> dict:
    """O exhibit desenhado sob a pergunta de moat — dentro da aba Tese."""
    entrega_dict["analise"]["exhibits"] = [copy.deepcopy(exhibit)]
    entrega_dict["dados"] = copy.deepcopy(_DADOS_DOS_EXHIBITS)
    pergunta = entrega_dict["analise"]["perguntas"][0]
    del pergunta["sem_exhibit"]
    pergunta["exhibits"] = [exhibit["id"]]
    # 5E, Task 2: o dataset entra depois de `montar_entrega` — o apoio completa o registro
    # que o sustenta, sem o qual ele seria `dataset_sem_proveniencia`.
    return apoio.completar_ledger(entrega_dict)


@pytest.mark.parametrize("exhibit,onde,chave_de_mercado", [
    pytest.param(_EXHIBIT_DO_PRECO, "analise.exhibits.0.series.0.chave",
                 lambda e: e["series"][0].update(chave="resultados:mercado_tela.valor"), id="serie-engine"),
    pytest.param(_EXHIBIT_DA_RECEITA_COM_OVERLAY, "analise.exhibits.0.overlays.0.chave",
                 lambda e: e["overlays"][0].update(chave="resultados:mercado_tela.valor", rotulo="múltiplo de tela"),
                 id="overlay"),
])
def test_conclusao_de_valor_num_exhibit_sob_a_pergunta_sob_fronteira_e_hard_fail(exhibit, onde, chave_de_mercado,
                                                                                 tmp_path):
    """P1d e P1e da revisão: a tabela "Quanto vale a ação no cenário da manchete?" e um
    overlay chamado "preço justo" desenhavam R$ 61,91 sob uma pergunta da tese, com
    RC=0. Fora da fronteira os dois continuam válidos; sob ela, a mesma referência ao
    múltiplo de tela continua permitida."""
    fora = _com_exhibit_sob_a_pergunta(_entrega(), exhibit)
    _carregar(fora, tmp_path)
    assert _achados(fora) == []

    sob = _com_exhibit_sob_a_pergunta(_sob_fronteira(), exhibit)
    achados = _do_codigo(_achados(sob), "fronteira_com_preco_alvo")
    assert [(a.nivel, a.onde, a.params["trecho"], a.params["caminho"]) for a in achados] == [
        ("HARD_FAIL", onde, "resultados:manchete.preco_acao", "manchete.preco_acao")]

    de_mercado = copy.deepcopy(exhibit)
    chave_de_mercado(de_mercado)
    assert _do_codigo(_achados(_com_exhibit_sob_a_pergunta(_sob_fronteira(), de_mercado)),
                      "fronteira_com_preco_alvo") == []


def test_o_qc_reconhece_conclusao_de_valor_pelo_mapa_da_integracao_e_nunca_pelo_nome_do_campo():
    """E3: a mesma entrega sob dois catálogos. Sem o padrão das células no mapa, a
    célula da grade deixa de ser conclusão de valor; com `reversa.alvo.valor` — um
    múltiplo que nenhum nome de campo sugere — declarado no mapa, citá-lo passa a
    reprovar. Um QC que decidisse pelo nome ficaria igual nos dois catálogos."""
    sob = _entrega("caso_reversa_firm.json", variante="fronteira")
    alvo_da_reversa = "{{resultados:reversa.alvo.valor|x2}}"
    _acrescentar(sob, ("veredicto", "texto"), f" A célula vale {_CELULA_DA_GRADE}; a tela embute {alvo_da_reversa}.")

    def _trechos(catalogo: dict) -> list:
        return [a.params["trecho"] for a in _do_codigo(_achados(sob, catalogo), "fronteira_com_preco_alvo")]

    assert _trechos(CATALOGO) == [_CELULA_DA_GRADE]
    outro = copy.deepcopy(CATALOGO)
    outro["conclusoes_de_valor"]["preço por ação"].remove("sensibilidades.grades_2d.*.celulas.*.*.valor")
    outro["conclusoes_de_valor"]["múltiplo"].append("reversa.alvo.valor")
    assert _trechos(outro) == [alvo_da_reversa]


# --------------------------------------------------------------------------
# N10: sob fronteira, o bloco de avisos não pode dizer "nenhum aviso obrigatório" —
# a §11 lista "limitação de escopo" como REQUIRED DISCLOSURE. O QC a emite com o
# rótulo da classe, do catálogo; sem essa declaração (ou sem o mapa das conclusões
# de valor), o relatório não sabe nomear a fronteira nem reconhecer um número de
# valor sob ela, e recusa nomeando.
# --------------------------------------------------------------------------

def test_sob_fronteira_o_qc_declara_a_limitacao_de_escopo_com_o_rotulo_da_classe():
    assert _do_codigo(_achados(_entrega()), "fronteira_de_escopo_declarada") == []

    sob = _sob_fronteira()
    classe = sob["resultados"]["fronteira_de_escopo"]["classe"]
    assert [(a.nivel, a.onde, a.params) for a in _do_codigo(_achados(sob), "fronteira_de_escopo_declarada")] == [
        ("REQUIRED_DISCLOSURE", "resultados.fronteira_de_escopo",
         {"classe": classe, "rotulo": CATALOGO["fronteiras_de_escopo"][classe]["rotulo"]["pt-BR"]})]


@pytest.mark.parametrize("falta", ["rotulo_da_classe", "mapa_de_conclusoes_de_valor"])
def test_fronteira_que_o_catalogo_nao_declara_e_hard_fail_nomeado(falta):
    sob = _sob_fronteira()
    classe = sob["resultados"]["fronteira_de_escopo"]["classe"]
    assert _do_codigo(_achados(sob), "fronteira_de_escopo_desconhecida") == []

    catalogo = copy.deepcopy(CATALOGO)
    if falta == "rotulo_da_classe":
        del catalogo["fronteiras_de_escopo"][classe]["rotulo"]["pt-BR"]
    else:
        del catalogo["conclusoes_de_valor"]
    assert [(a.nivel, a.onde, a.params) for a in _do_codigo(_achados(sob, catalogo),
                                                            "fronteira_de_escopo_desconhecida")] == [
        ("HARD_FAIL", "resultados.fronteira_de_escopo", {"classe": classe, "idioma": "pt-BR"})]


# --------------------------------------------------------------------------
# HARD FAIL `analise_sem_reversa` e REQUIRED DISCLOSURE `limitacao_metodologica`
# (D4). A decisão entre os dois lê `catalogo.limitacoes.<chave>.afeta` — a
# declaração da integração —, nunca o nome da chave.
# --------------------------------------------------------------------------

def test_analise_sem_a_reversa_que_o_gate_admite_nao_emite(tmp_path):
    sem_reversa = _entrega(compor_reversa=False)
    assert "reversa" not in sem_reversa["resultados"]
    assert sem_reversa["resultados"]["limitacoes"] == []
    raiz = tmp_path / "sem_reversa"
    apoio.escrever_raiz(raiz, sem_reversa)

    resultado = _rodar_builder(raiz)

    assert resultado.returncode == 2, resultado.stdout + resultado.stderr
    assert not (raiz / "relatorio.html").exists()
    achados = _ler_qc(raiz)["achados"]
    assert [(a["nivel"], a["codigo"], a["onde"]) for a in achados] == [
        ("HARD_FAIL", "analise_sem_reversa", "resultados.reversa")]

    com_reversa = _entrega()
    assert "reversa" in com_reversa["resultados"]
    assert _do_codigo(_achados(com_reversa), "analise_sem_reversa") == []


@pytest.mark.parametrize("fixture,esperados", [
    pytest.param("caso_degrau.json", _ACHADOS_DA_ENTREGA_PADRAO["caso_degrau.json"], id="degrau"),
    pytest.param("caso_rampa.json", _ACHADOS_DA_ENTREGA_PADRAO["caso_rampa.json"], id="rampa"),
])
def test_a_limitacao_da_reversa_emite_com_o_disclosure_nomeado(fixture, esperados, tmp_path):
    entrega_dict = _entrega(fixture)
    assert "reversa" not in entrega_dict["resultados"]
    (chave,) = entrega_dict["resultados"]["limitacoes"]
    raiz = tmp_path / "limitacao"
    apoio.escrever_raiz(raiz, entrega_dict)

    resultado = _rodar_builder(raiz)

    assert resultado.returncode == 0, resultado.stdout + resultado.stderr
    assert (raiz / "relatorio.html").exists()
    achados = _ler_qc(raiz)["achados"]
    assert [(a["nivel"], a["codigo"]) for a in achados] == esperados
    disclosure = next(a for a in achados if a["codigo"] == "limitacao_metodologica")
    rotulo = CATALOGO["limitacoes"][chave]["rotulo"]["pt-BR"]
    assert disclosure["onde"] == "resultados.limitacoes.0"
    assert disclosure["params"] == {"limitacao": chave, "rotulo": rotulo}
    assert rotulo in disclosure["mensagem"]


def test_o_qc_le_a_declaracao_afeta_e_nunca_o_nome_da_chave():
    """A mesma chave publicada, com a declaração trocada no catálogo: se a limitação
    passa a suprimir outro bloco, ela deixa de justificar a reversa ausente. Um QC
    que decidisse pelo nome (`startswith("reversa_")`) continuaria calado aqui."""
    entrega_dict = _entrega("caso_degrau.json")
    (chave,) = entrega_dict["resultados"]["limitacoes"]
    assert chave.startswith("reversa_"), "o nome da chave tem de sugerir reversa para o teste discriminar"
    assert _do_codigo(_achados(entrega_dict), "analise_sem_reversa") == []

    outro_sujeito = copy.deepcopy(CATALOGO)
    outro_sujeito["limitacoes"][chave]["afeta"] = "sensibilidades"
    achados = _achados(entrega_dict, outro_sujeito)
    assert [(a.nivel, a.onde) for a in _do_codigo(achados, "analise_sem_reversa")] == [
        ("HARD_FAIL", "resultados.reversa")]
    assert [a.params["limitacao"] for a in _do_codigo(achados, "limitacao_metodologica")] == [chave]


@pytest.mark.parametrize("declaracao", ["ausente", "sem_afeta", "sem_rotulo"])
def test_limitacao_que_o_catalogo_nao_declara_e_hard_fail_nomeado(declaracao):
    """Defesa em profundidade: uma limitação publicada que o catálogo não declara
    (rótulo no idioma e `afeta`) não some em silêncio nem vira disclosure sem texto."""
    entrega_dict = _entrega("caso_rampa.json")
    (chave,) = entrega_dict["resultados"]["limitacoes"]
    assert _do_codigo(_achados(entrega_dict), "limitacao_desconhecida") == []

    catalogo = copy.deepcopy(CATALOGO)
    if declaracao == "ausente":
        del catalogo["limitacoes"][chave]
    elif declaracao == "sem_afeta":
        del catalogo["limitacoes"][chave]["afeta"]
    else:
        del catalogo["limitacoes"][chave]["rotulo"]
    achados = _achados(entrega_dict, catalogo)
    assert [(a.nivel, a.onde, a.params["limitacao"]) for a in _do_codigo(achados, "limitacao_desconhecida")] == [
        ("HARD_FAIL", "resultados.limitacoes.0", chave)]
    assert _do_codigo(achados, "limitacao_metodologica") == []


# --------------------------------------------------------------------------
# QUALITY WARNING `tese_dependente_de_uma_premissa` (D6): todas as perguntas com o
# mesmo vínculo de um item só.
# --------------------------------------------------------------------------

def test_todas_as_perguntas_no_mesmo_vinculo_de_um_item_e_quality_warning():
    entrega_dict = _entrega()
    for pergunta in entrega_dict["analise"]["perguntas"]:
        pergunta["vinculo"] = ["wacc"]
    assert [(a.nivel, a.codigo, a.params["item"]) for a in _achados(entrega_dict)] == [
        ("QUALITY_WARNING", "tese_dependente_de_uma_premissa", "wacc")]

    vizinha = _entrega()
    for pergunta in vizinha["analise"]["perguntas"]:
        pergunta["vinculo"] = ["wacc"]
    vizinha["analise"]["perguntas"][-1]["vinculo"] = ["wacc", "g"]
    assert _achados(vizinha) == []


# --------------------------------------------------------------------------
# Todo campo de texto novo passa pelos placeholders auditáveis: dígito fora de
# placeholder é `numero_sem_proveniencia` (A7 da 5A) em cada um deles.
# --------------------------------------------------------------------------

_CAMPOS_NOVOS_DE_PROSA = [
    ("veredicto", "texto"),
    ("premissas_decisivas", 0, "derivacao"),
    ("positives", 0, "afirmacao"),
    ("positives", 0, "observavel"),
    ("positives", 0, "razao"),
    ("negatives", 0, "afirmacao"),
    ("negatives", 0, "observavel"),
    ("negatives", 0, "razao"),
    ("perguntas", 0, "pergunta"),
    ("perguntas", 0, "evidencia"),
    ("perguntas", 0, "observavel"),
    ("perguntas", 0, "sem_exhibit", "razao"),
    ("riscos", 0, "risco"),
    ("riscos", 0, "observavel"),
    ("visao_nao_consensual", "texto"),
    ("mudou_desde_analise_fornecida", "linhas", 1),
    # Task 3 (achado 4): com os exhibits desenhados dentro da aba Tese, os três textos
    # de cada um são prosa da Tese.
    ("exhibits", 0, "pergunta"),
    ("exhibits", 0, "nota_janela"),
    ("exhibits", 0, "caption"),
    # Onda de correção da revisão final (F3, N12): os textos que o gráfico escreve sob a
    # pergunta — o rótulo da série engine, a nota da série derivada e o rótulo do overlay.
    ("exhibits", 0, "series", 0, "rotulo"),
    ("exhibits", 0, "series", 1, "formula_nota"),
    ("exhibits", 0, "overlays", 0, "rotulo"),
    # Fatia 5F, Task 4 (D12): o julgamento do que está no preço, que a Valuation exibe — a Tese
    # padrão o declara porque a entrega tem a reversa.
    ("o_que_esta_no_preco", "julgamento"),
    ("o_que_esta_no_preco", "observavel"),
]


def _acrescentar(entrega_dict: dict, caminho: tuple, sufixo: str) -> None:
    pai = entrega_dict["analise"]
    for passo in caminho[:-1]:
        pai = pai[passo]
    pai[caminho[-1]] = pai[caminho[-1]] + sufixo


def _entrega_com_todos_os_campos_de_prosa() -> dict:
    entrega_dict = _entrega()
    analise = entrega_dict["analise"]
    analise["positives"][0]["razao"] = "Refletido no crescimento do cenário-base."
    analise["visao_nao_consensual"] = {"texto": "O mercado subestima a duração da vantagem de custo."}
    analise["mudou_desde_analise_fornecida"] = {
        "linhas": ["A margem normalizada subiu.", "O custo de capital caiu."]}
    # 5E, D5: o que mudou sai do confronto com a análise fornecida — e o texto do confronto é
    # dado da Evidência, fora da lista de prosa.
    entrega_dict["confronto"] = copy.deepcopy(_CONFRONTO)
    analise["exhibits"] = [dict(
        copy.deepcopy(_EXHIBIT), caption="Fonte: o cenário da manchete.",
        series=[*copy.deepcopy(_EXHIBIT["series"]),
                {"derivacao": "derivada", "fonte": "fin", "formula": "ebitda / receita",
                 "formula_nota": "margem EBITDA"}],
        overlays=[{"chave": "caso:preco.valor", "rotulo": "preço de tela"}])]
    entrega_dict["dados"] = copy.deepcopy(_DADOS_DOS_EXHIBITS)
    # 5E, Task 2: o dataset entra depois de `montar_entrega` — o apoio completa o registro que o sustenta.
    return apoio.completar_ledger(entrega_dict)


_CONFRONTO = {
    "analise_fornecida": {"identificacao": "Relatório de cobertura anterior", "data": "2026-03-02"},
    "divergencias": [{"item": "Custo de capital", "classificacao": "premissa_revista",
                      "anterior": "11,0%", "atual": "10,0%",
                      "explicacao": "A estrutura de capital ficou menos alavancada."}],
}


def _ondes_do_molde(analise: dict, molde: tuple) -> set:
    """Todo `onde` que um caminho-molde de `_CAMPOS_NOVOS_DE_PROSA` cobre na
    entrega: um índice do molde vale por todos os itens da lista naquela posição."""
    nos = [((), analise)]
    for passo in molde:
        proximos = []
        for prefixo, no in nos:
            if isinstance(passo, int):
                proximos += [(prefixo + (indice,), item) for indice, item in enumerate(no)]
            elif isinstance(no, dict) and passo in no:
                proximos.append((prefixo + (passo,), no[passo]))
        nos = proximos
    return {"analise." + ".".join(map(str, prefixo)) for prefixo, _no in nos}


def test_todo_campo_de_texto_da_tese_e_campo_de_prosa(tmp_path):
    entrega_dict = _entrega_com_todos_os_campos_de_prosa()
    _carregar(entrega_dict, tmp_path)
    ondes = [onde for onde, _texto in placeholders.campos_de_prosa(entrega_dict)]
    assert len(ondes) == len(set(ondes)), ondes
    esperados = {"analise.conclusao.texto"}.union(
        *(_ondes_do_molde(entrega_dict["analise"], molde) for molde in _CAMPOS_NOVOS_DE_PROSA))
    assert "analise.perguntas.2.sem_exhibit.razao" in esperados, "o molde deixou de cobrir as outras perguntas"
    assert set(ondes) == esperados


@pytest.mark.parametrize("caminho", _CAMPOS_NOVOS_DE_PROSA, ids=lambda c: ".".join(map(str, c)))
def test_digito_solto_num_campo_novo_da_tese_e_hard_fail(caminho):
    limpa = _entrega_com_todos_os_campos_de_prosa()
    assert _achados(limpa) == []

    _acrescentar(limpa, caminho, " Negociada a R$ 50 ontem.")
    onde = "analise." + ".".join(map(str, caminho))
    assert [(a.nivel, a.onde) for a in _do_codigo(_achados(limpa), "numero_sem_proveniencia")] == [
        ("HARD_FAIL", onde)]


# ==========================================================================
# Task 3 (D3, D5, D7): a aba Tese renderizada.
#
# O analista lê TEXTO: a página com o miolo de <script>/<style> neutralizado
# (`apoio.prosa_da_pagina`) e, dela, só o texto dos nós. Classe e atributo só
# LOCALIZAM a seção — nenhuma asserção compara um atributo (lição do F1 da 5B), e
# nenhuma varre a página inteira (lição do F10).
# ==========================================================================

DICIONARIO = placeholders.carregar_dicionario("pt-BR")
TESE = DICIONARIO["interface"]["tese"]
VALUATION = DICIONARIO["interface"]["valuation"]
SEM_NODE = shutil.which("node") is None
RAZAO_SEM_NODE = "node ausente do PATH -- o harness do bootstrap roda sempre no CI (setup-node)"


class _ArvoreDaPagina(HTMLParser):
    """A página como árvore `{tag, attrs, filhos, pai}`, com o texto desescapado como o
    browser o entrega ao leitor. Elemento vazio do HTML não abre nível, e texto contíguo
    vira um nó só."""

    VAZIOS = frozenset({"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta",
                        "source", "wbr"})

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.raiz = {"tag": "#documento", "attrs": {}, "filhos": [], "pai": None}
        self._pilha = [self.raiz]

    def _abrir(self, tag, attrs, vazio):
        no = {"tag": tag, "attrs": {k: ("" if v is None else v) for k, v in attrs},
              "filhos": [], "pai": self._pilha[-1]}
        self._pilha[-1]["filhos"].append(no)
        if not vazio:
            self._pilha.append(no)

    def handle_starttag(self, tag, attrs):
        self._abrir(tag, attrs, tag in self.VAZIOS)

    def handle_startendtag(self, tag, attrs):
        self._abrir(tag, attrs, True)

    def handle_endtag(self, tag):
        for posicao in range(len(self._pilha) - 1, 0, -1):
            if self._pilha[posicao]["tag"] == tag:
                del self._pilha[posicao:]
                return

    def handle_data(self, data):
        filhos = self._pilha[-1]["filhos"]
        if filhos and "texto" in filhos[-1]:
            filhos[-1]["texto"] += data
        else:
            filhos.append({"texto": data})


def _arvore(pagina: str) -> dict:
    parser = _ArvoreDaPagina()
    parser.feed(apoio.prosa_da_pagina(pagina))
    parser.close()
    return parser.raiz


def _elementos(no: dict):
    """Todo elemento abaixo de `no`, na ordem do documento."""
    for filho in no["filhos"]:
        if "tag" in filho:
            yield filho
            yield from _elementos(filho)


def _classes(no: dict) -> list:
    return no["attrs"].get("class", "").split()


def _todos(no: dict, *, classe: str | None = None, tag: str | None = None) -> list:
    return [el for el in _elementos(no)
            if (classe is None or classe in _classes(el)) and (tag is None or el["tag"] == tag)]


def _um(no: dict, **filtro) -> dict:
    achados = _todos(no, **filtro)
    assert len(achados) == 1, f"esperado exatamente um elemento {filtro}, vieram {len(achados)}"
    return achados[0]


def _ancestral(no: dict, classe: str) -> dict | None:
    atual = no["pai"]
    while atual is not None and classe not in _classes(atual):
        atual = atual["pai"]
    return atual


def _visivel(no: dict) -> str:
    """O texto que o leitor vê dentro de `no`, com o espaço normalizado."""
    partes: list[str] = []

    def _varrer(atual: dict) -> None:
        for filho in atual["filhos"]:
            if "texto" in filho:
                partes.append(filho["texto"])
            else:
                _varrer(filho)

    _varrer(no)
    return " ".join(" ".join(partes).split())


def _aba(pagina: str, nome: str) -> dict:
    return next(el for el in _elementos(_arvore(pagina)) if el["attrs"].get("data-aba-painel") == nome)


def _secoes(aba: dict) -> list:
    """As seções da aba, na ordem em que o leitor as encontra."""
    return [filho for filho in aba["filhos"] if filho.get("tag") == "section"]


def _titulo(no: dict) -> str:
    """O texto do primeiro título (`h2`, `h3` ou `h4`) diretamente dentro de `no`."""
    return _visivel(next(filho for filho in no["filhos"] if filho.get("tag") in ("h2", "h3", "h4")))


def _secao(aba: dict, titulo: str) -> dict:
    (secao,) = [secao for secao in _secoes(aba) if _titulo(secao) == titulo]
    return secao


def _moeda(entrega_dict: dict, valor: float) -> str:
    return placeholders.formatar(valor, "moeda", "pt-BR", entrega_dict["caso"]["moeda"])


def _pagina_da_tese(entrega_dict: dict) -> str:
    """O HTML pelo caminho que `builder.py` percorre depois de uma primeira passada de QC
    limpa: o log de TODA a prosa e os exhibits resolvidos uma vez."""
    achados = _achados(entrega_dict)
    assert not [a for a in achados if a.nivel == "HARD_FAIL"], achados
    _prosa, log = placeholders.resolver_prosa(entrega_dict, "pt-BR")
    resolvidos, log_exhibits = exhibits_mod.resolver(entrega_dict)
    return render.compor(entrega_dict, CATALOGO, achados, log, "pt-BR", resolvidos, log_exhibits)


def _pagina_pelo_builder(entrega_dict: dict, raiz: Path) -> str:
    """O `relatorio.html` do CLI de verdade — com o laboratório e o log que o builder monta."""
    apoio.escrever_raiz(raiz, entrega_dict)
    resultado = _rodar_builder(raiz)
    assert resultado.returncode == 0, resultado.stdout + resultado.stderr
    return (raiz / "relatorio.html").read_text(encoding="utf-8")


_DADOS_DOS_EXHIBITS = {"fin": {
    "ledger": [], "x": [str(ano) for ano in range(2016, 2026)],
    "campos": {"receita": [100.0 + 10.0 * i for i in range(10)], "ebitda": [20.0 + 3.0 * i for i in range(10)]},
}}
_EXHIBITS_DAS_PERGUNTAS = [
    {"id": "receita", "pergunta": "Como a receita evoluiu no período?", "tipo": "linha",
     "series": [{"derivacao": "direta", "fonte": "fin.receita"}]},
    {"id": "margem", "pergunta": "A margem acompanha a expansão da capacidade?", "tipo": "linha",
     "series": [{"derivacao": "derivada", "fonte": "fin", "formula": "ebitda / receita",
                 "formula_nota": "margem EBITDA"}],
     "caption": "Fonte: demonstrações auditadas."},
    {"id": "preco", "pergunta": "Quanto vale a ação no cenário da manchete?", "tipo": "tabela",
     "series": [{"derivacao": "engine", "chave": "resultados:manchete.preco_acao",
                 "rotulo": "preço por ação no cenário da manchete"}],
     "nota_janela": "Um único ponto: o da manchete."},
]


@functools.lru_cache(maxsize=None)
def _entrega_com_exhibits_serializada() -> str:
    entrega_dict = apoio.montar_entrega(FIXTURE, dados=copy.deepcopy(_DADOS_DOS_EXHIBITS),
                                        exhibits=copy.deepcopy(_EXHIBITS_DAS_PERGUNTAS))
    moat, crescimento, _rentabilidade = entrega_dict["analise"]["perguntas"]
    for pergunta, citados in ((moat, ["margem", "receita"]), (crescimento, ["receita"])):
        del pergunta["sem_exhibit"]
        pergunta["exhibits"] = citados
    return json.dumps(entrega_dict, ensure_ascii=False)


def _entrega_com_exhibits_nas_perguntas() -> dict:
    """Três exhibits declarados, nesta ordem: `receita`, `margem`, `preco`. A pergunta de
    moat cita `[margem, receita]` — fora da ordem declarada —, a de crescimento cita
    `[receita]` — o mesmo exhibit numa segunda pergunta —, a de rentabilidade não tem
    exhibit, e nenhuma pergunta cita `preco`."""
    return json.loads(_entrega_com_exhibits_serializada())


# --------------------------------------------------------------------------
# D7: a ordem da aba.
# --------------------------------------------------------------------------

def test_a_aba_tese_segue_a_ordem_do_desenho():
    """Conclusão → avisos obrigatórios → premissas decisivas → o que mudou (se declarado) →
    Positives/Negatives → perguntas → riscos → visão não-consensual (se declarada) →
    exhibits que nenhuma pergunta cita. A vizinha sem os opcionais, e sem exhibit fora das
    perguntas, não ganha seção vazia nenhuma."""
    completa = _entrega_com_exhibits_nas_perguntas()
    completa["analise"]["mudou_desde_analise_fornecida"] = {"linhas": ["A margem normalizada subiu."]}
    completa["analise"]["visao_nao_consensual"] = {"texto": "O mercado subestima a duração da vantagem."}
    aba = _aba(_pagina_da_tese(completa), "tese")

    assert [_titulo(secao) for secao in _secoes(aba)] == [
        TESE["conclusao_titulo"], TESE["disclosures_titulo"], TESE["premissas_decisivas_titulo"],
        TESE["o_que_mudou_titulo"], TESE["positives_negatives_titulo"], TESE["perguntas_titulo"],
        TESE["riscos_titulo"], TESE["visao_nao_consensual_titulo"], TESE["exhibits_nao_citados_titulo"]]
    assert "A margem normalizada subiu." in _visivel(_secao(aba, TESE["o_que_mudou_titulo"]))
    assert "O mercado subestima a duração da vantagem." in _visivel(_secao(aba, TESE["visao_nao_consensual_titulo"]))
    riscos = _secao(aba, TESE["riscos_titulo"])
    assert [(_visivel(_um(item, classe="tese-risco")), _visivel(_um(item, classe="tese-observavel")))
            for item in _todos(riscos, classe="tese-item")] == [
        (risco["risco"], risco["observavel"]) for risco in completa["analise"]["riscos"]]

    minima = _aba(_pagina_da_tese(_entrega()), "tese")
    assert [_titulo(secao) for secao in _secoes(minima)] == [
        TESE["conclusao_titulo"], TESE["disclosures_titulo"], TESE["premissas_decisivas_titulo"],
        TESE["positives_negatives_titulo"], TESE["perguntas_titulo"], TESE["riscos_titulo"]]


# --------------------------------------------------------------------------
# D1/D7: a Conclusão — faixa, veredicto com o preço de tela, múltiplos.
# --------------------------------------------------------------------------

def _metricas(no: dict) -> list:
    return [(_visivel(_um(metrica, classe="metrica-rotulo")), _visivel(_um(metrica, classe="metrica-valor")),
             _visivel(_um(metrica, classe="metrica-nota")))
            for metrica in _todos(no, classe="metrica")]


def test_a_conclusao_mostra_a_faixa_dos_cenarios_o_veredicto_e_o_preco_de_tela_com_data_e_fonte():
    """Os três preços vêm de `resultados.cenarios.<nome>.valor.preco_acao`, cada um no papel
    que a faixa declara; o preço de tela, a data e a fonte vêm de `caso.preco`, nunca do
    analista; o veredicto sai resolvido; o múltiplo justo sai ao lado do de tela."""
    entrega_dict = _entrega(variante="tres_cenarios")
    entrega_dict["analise"]["veredicto"]["texto"] = "A tela, a {{caso:preco.valor|moeda}}, fica abaixo da base."
    resultados, preco, faixa = entrega_dict["resultados"], entrega_dict["caso"]["preco"], entrega_dict["analise"]["faixa"]
    assert faixa == {"piso": "pessimista", "base": "base", "teto": "otimista"}
    conclusao = _secao(_aba(_pagina_da_tese(entrega_dict), "tese"), TESE["conclusao_titulo"])

    assert _metricas(_um(conclusao, classe="tese-faixa")) == [
        (TESE["papeis_da_faixa"][papel],
         _moeda(entrega_dict, resultados["cenarios"][faixa[papel]]["valor"]["preco_acao"]),
         render.t(DICIONARIO, "tese.faixa_cenario", cenario=faixa[papel]))
        for papel in entrega.PAPEIS_DA_FAIXA]

    veredicto = _um(conclusao, classe="tese-veredicto")
    assert _visivel(_um(veredicto, classe="tese-veredicto-texto")) == (
        f"A tela, a {_moeda(entrega_dict, preco['valor'])}, fica abaixo da base.")
    assert _visivel(_um(veredicto, classe="tese-preco-de-tela")) == render.t(
        DICIONARIO, "tese.preco_de_tela", preco=_moeda(entrega_dict, preco["valor"]),
        data=preco["data"], fonte=preco["fonte"])

    justo, tela = resultados["manchete"]["multiplo"], resultados["mercado_tela"]
    assert _metricas(_um(conclusao, classe="tese-multiplos")) == [
        (DICIONARIO["interface"]["valuation"]["multiplo_justo_titulo"], placeholders.formatar(justo["valor"], "x2", "pt-BR"),
         CATALOGO["multiplos"][justo["chave"]]["rotulo"]["pt-BR"]),
        (DICIONARIO["interface"]["valuation"]["multiplo_tela_titulo"], placeholders.formatar(tela["valor"], "x2", "pt-BR"),
         CATALOGO["multiplos"][tela["chave"]]["rotulo"]["pt-BR"])]


# --------------------------------------------------------------------------
# E3 e a lição do B2: o rótulo, nunca a chave.
# --------------------------------------------------------------------------

def test_vinculo_mecanismo_e_premissa_decisiva_saem_pelo_catalogo_e_tema_vetor_e_incorporacao_pelo_dicionario():
    """Vínculo e mecanismo misturam premissa da rota e bloco econômico — os dois rotulados
    pelo catálogo; a premissa decisiva sai com o rótulo e o número do cenário da manchete,
    formatado pela unidade do catálogo; tema, vetor e incorporação são vocabulário do Fleet,
    rotulados pelo dicionário. Nenhuma chave crua chega à tela."""
    entrega_dict = _entrega()
    analise, resultados = entrega_dict["analise"], entrega_dict["resultados"]
    analise["perguntas"][1]["vinculo"] = ["wacc", "custo_capital"]
    analise["positives"][0]["mecanismo"] = ["roic", "crescimento_reinvestimento"]
    analise["negatives"][0]["vetor"] = "earning_power"
    analise["premissas_decisivas"] = [{"chave": "wacc", "derivacao": "Custo de capital da companhia no ciclo."}]
    aba = _aba(_pagina_da_tese(entrega_dict), "tese")

    premissas_da_rota = CATALOGO["premissas"][resultados["rota"]]
    rotulo = {chave: info["rotulo"]["pt-BR"] for chave, info in premissas_da_rota.items()}
    rotulo.update({chave: info["rotulo"]["pt-BR"] for chave, info in CATALOGO["blocos"].items()})

    perguntas = _todos(aba, classe="tese-pergunta")
    assert [[_visivel(item) for item in _todos(bloco, classe="tese-rotulo")] for bloco in perguntas] == [
        [rotulo[item] for item in pergunta["vinculo"]] for pergunta in analise["perguntas"]]
    assert [_visivel(_um(bloco, classe="tese-tema")) for bloco in perguntas] == [
        TESE["temas"][pergunta["tema"]] for pergunta in analise["perguntas"]]

    positives, negatives = _todos(aba, classe="tese-lado")
    for lado, declarados in ((positives, analise["positives"]), (negatives, analise["negatives"])):
        itens = _todos(lado, classe="tese-item")
        assert [[_visivel(chip) for chip in _todos(item, classe="tese-rotulo")] for item in itens] == [
            [rotulo[mecanismo] for mecanismo in declarado["mecanismo"]] for declarado in declarados]
        assert [(_visivel(_um(item, classe="tese-vetor")), _visivel(_um(item, classe="tese-incorporacao")))
                for item in itens] == [
            (TESE["vetores"][declarado["vetor"]], TESE["incorporacoes"][declarado["incorporacao"]])
            for declarado in declarados]

    (premissa,) = _todos(aba, classe="tese-premissa")
    wacc = resultados["cenarios"][resultados["manchete"]["cenario"]]["premissas"]["wacc"]
    formato = CATALOGO["unidades"][premissas_da_rota["wacc"]["unidade"]]["formato"]
    assert [_visivel(_um(premissa, classe=classe)) for classe in ("metrica-rotulo", "metrica-valor", "tese-derivacao")] == [
        rotulo["wacc"], placeholders.formatar(wacc, formato, "pt-BR"), "Custo de capital da companhia no ciclo."]

    texto = _visivel(aba)
    chaves = ("wacc", "custo_capital", "roic", "crescimento_reinvestimento", "duracao_terminal", "earning_power",
              "rentabilidade_do_crescimento", "nao_incorporado")
    assert [chave for chave in chaves if chave in texto] == []


def test_uma_premissa_decisiva_de_escolha_sem_rotulo_no_catalogo_nunca_mostra_o_codigo_cru():
    """`resultados.cenarios.<nome>.premissas.tv` repete o alias legado que o caso declarou
    (`spread`), e o catálogo só rotula as opções canônicas. A tela diz que o valor está fora
    do vocabulário do catálogo — a mesma frase do laboratório —, nunca `spread`."""
    entrega_dict = _entrega(variante="alias_tv")
    resultados = entrega_dict["resultados"]
    assert resultados["cenarios"][resultados["manchete"]["cenario"]]["premissas"]["tv"] == "spread"
    entrega_dict["analise"]["premissas_decisivas"] = [
        {"chave": "tv", "derivacao": "Perpetuidade com retorno incremental declarado."}]
    aba = _aba(_pagina_da_tese(entrega_dict), "tese")

    (premissa,) = _todos(aba, classe="tese-premissa")
    assert _visivel(_um(premissa, classe="metrica-valor")) == (
        DICIONARIO["interface"]["valuation"]["laboratorio_valor_nao_rotulavel"])
    assert "spread" not in _visivel(aba)


def test_os_rotulos_de_tema_vetor_incorporacao_e_papel_da_faixa_cobrem_exatamente_o_vocabulario_do_contrato():
    """Vocabulário do contrato `entrega/1` (§7, §9), rotulado pelo dicionário: uma entrada
    nova no contrato sem rótulo — ou um rótulo sobrando — reprova aqui, e nunca vira chave
    crua na tela."""
    assert set(TESE["temas"]) == entrega.TEMAS_DE_PERGUNTA
    assert set(TESE["vetores"]) == entrega.VETORES
    assert set(TESE["incorporacoes"]) == entrega.INCORPORACOES
    assert set(TESE["papeis_da_faixa"]) == set(entrega.PAPEIS_DA_FAIXA)


# --------------------------------------------------------------------------
# D5 e achado 1: os exhibits sob as perguntas, e cada gráfico no seu host.
# --------------------------------------------------------------------------

def test_o_exhibit_fica_sob_a_pergunta_que_o_cita_e_o_nao_citado_vai_para_a_secao_final():
    """Cada pergunta mostra os exhibits que cita, na ordem em que os cita — inclusive fora
    da ordem declarada, e o mesmo exhibit em duas perguntas — ou a razão de não ter; o
    exhibit que nenhuma pergunta cita aparece na seção final, e só lá."""
    entrega_dict = _entrega_com_exhibits_nas_perguntas()
    aba = _aba(_pagina_da_tese(entrega_dict), "tese")
    por_id = {exhibit["id"]: exhibit for exhibit in entrega_dict["analise"]["exhibits"]}
    perguntas = entrega_dict["analise"]["perguntas"]

    blocos = _todos(_secao(aba, TESE["perguntas_titulo"]), classe="tese-pergunta")
    assert [_titulo(bloco) for bloco in blocos] == [pergunta["pergunta"] for pergunta in perguntas]
    assert [[_titulo(artigo) for artigo in _todos(bloco, classe="exhibit")] for bloco in blocos] == [
        [por_id[exhibit_id]["pergunta"] for exhibit_id in pergunta.get("exhibits", [])] for pergunta in perguntas]
    assert [_visivel(_um(bloco, classe="tese-evidencia")) for bloco in blocos] == [
        pergunta["evidencia"] for pergunta in perguntas]
    assert _visivel(_um(blocos[2], classe="tese-sem-exhibit")) == perguntas[2]["sem_exhibit"]["razao"]
    assert _visivel(_um(blocos[0], classe="exhibit-caption")) == por_id["margem"]["caption"]

    final = _secoes(aba)[-1]
    assert _titulo(final) == TESE["exhibits_nao_citados_titulo"]
    assert [_titulo(artigo) for artigo in _todos(final, classe="exhibit")] == [por_id["preco"]["pergunta"]]
    assert _visivel(_um(final, classe="exhibit-nota-janela")) == por_id["preco"]["nota_janela"]


_HARNESS_DOS_EXHIBITS = r"""
const fs = require('fs');
const vm = require('vm');
const entrada = JSON.parse(fs.readFileSync(__ENTRADA__, 'utf-8'));
const proprio = (objeto, nome) => Object.prototype.hasOwnProperty.call(objeto, nome);

// O mesmo subconjunto de seletor do harness do laboratório: qualquer outro LANÇA, para
// que um seletor que este DOM falso não entende reprove em voz alta.
function casa(el, seletor) {
  const m = /^\s*\[([\w-]+)(?:="([^"]*)")?\]\s*$/.exec(seletor);
  if (!m) { throw new Error('seletor fora do subconjunto do harness: ' + seletor); }
  if (!proprio(el.atributos, m[1])) { return false; }
  return m[2] === undefined || el.atributos[m[1]] === m[2];
}

const elementos = entrada.elementos.map((atributos, ordem) => ({
  ordem: ordem,
  atributos: atributos,
  getAttribute(nome) { return proprio(this.atributos, nome) ? this.atributos[nome] : null; },
}));
const desenhos = [];
const ctx = vm.createContext({
  document: {
    getElementById: (id) => (id === 'fleet-dados-exhibits' ? { textContent: entrada.dados } : null),
    querySelectorAll: (seletor) => elementos.filter((el) => casa(el, seletor)),
    querySelector: (seletor) => elementos.find((el) => casa(el, seletor)) || null,
  },
  // Um registrador no lugar do adaptador: a posição do host no documento e o id da spec
  // que o bootstrap entregou a ele.
  FleetGraficos: {
    renderizar: (host, spec) => { desenhos.push({ ordem: host.ordem, spec: spec ? spec.id : null }); },
  },
});
vm.runInContext(entrada.bootstrap, ctx, { filename: 'bootstrap-dos-exhibits' });
console.log(JSON.stringify(desenhos));
"""


def _desenhos_do_bootstrap(pagina: str, elementos: list, tmp_path: Path) -> list:
    """Roda no node o bootstrap dos exhibits EXTRAÍDO da página, com o JSON que a página
    embute, sobre os elementos da própria página — nunca relido de `template.html`."""
    (bootstrap,) = [m.group(1) for m in re.finditer(r"<script>(.*?)</script>", pagina, re.S)
                    if 'getElementById("fleet-dados-exhibits")' in m.group(1)]
    dados = re.search(r'<script type="application/json" id="fleet-dados-exhibits">(.*?)</script>',
                      pagina, re.S).group(1)
    arquivo = tmp_path / "bootstrap_dos_exhibits.json"
    arquivo.write_text(json.dumps({"bootstrap": bootstrap, "dados": dados,
                                   "elementos": [el["attrs"] for el in elementos]}, ensure_ascii=False),
                       encoding="utf-8")
    resultado = subprocess.run(
        ["node", "-e", _HARNESS_DOS_EXHIBITS.replace("__ENTRADA__", json.dumps(str(arquivo)))],
        capture_output=True, text=True, encoding="utf-8", timeout=120)
    assert resultado.returncode == 0, resultado.stdout + resultado.stderr
    return json.loads(resultado.stdout)


@pytest.mark.skipif(SEM_NODE, reason=RAZAO_SEM_NODE)
def test_cada_host_recebe_os_dados_do_exhibit_do_seu_indice_e_nunca_os_da_sua_posicao(tmp_path):
    """Achado 1 (MATERIAL). O bootstrap ligava `hosts[i]` a `dados.exhibits[i]` pela ORDEM no
    DOM; sob as perguntas, essa ordem é a das perguntas. Com a citação fora de ordem, o host
    de `margem` recebia os dados de `receita`, com rc 0; e o exhibit citado por duas
    perguntas cria mais hosts do que o payload tem, e o último ficava vazio. O que o leitor
    vê sobre cada host — a pergunta do exhibit — tem de ser a do exhibit cujos dados o host
    recebeu, e todo host recebe exatamente um desenho."""
    entrega_dict = _entrega_com_exhibits_nas_perguntas()
    pagina = _pagina_da_tese(entrega_dict)
    elementos = list(_elementos(_arvore(pagina)))
    hosts = [(ordem, el) for ordem, el in enumerate(elementos) if "exhibit-grafico" in _classes(el)]
    assert len(hosts) == 4 > len(entrega_dict["analise"]["exhibits"]), "a entrega tem de ter mais hosts que specs"

    desenhos = _desenhos_do_bootstrap(pagina, elementos, tmp_path)

    por_id = {exhibit["id"]: exhibit for exhibit in entrega_dict["analise"]["exhibits"]}
    spec_do_host = {desenho["ordem"]: desenho["spec"] for desenho in desenhos}
    assert [por_id.get(spec_do_host.get(ordem), {}).get("pergunta") for ordem, _host in hosts] == [
        _titulo(_ancestral(host, "exhibit")) for _ordem, host in hosts]
    assert [desenho["ordem"] for desenho in desenhos] == [ordem for ordem, _host in hosts]


# --------------------------------------------------------------------------
# D3 e achado 2: a fronteira de escopo na Tese e nos dois lugares da Valuation.
# --------------------------------------------------------------------------

def _rotulos_do_preco_na_valuation(pagina: str) -> tuple:
    """O rótulo do preço no cabeçalho da aba Valuation, o de cada cenário do laboratório e
    todos os rótulos de métrica da aba."""
    valuation = _aba(pagina, "valuation")
    cabecalho = _todos(_um(valuation, classe="valuation-cabecalho"), classe="metrica-rotulo")[0]
    laboratorio = [_todos(saidas, classe="metrica-rotulo")[0] for saidas in _todos(valuation, classe="lab-saidas")]
    return (_visivel(cabecalho), [_visivel(rotulo) for rotulo in laboratorio],
            [_visivel(rotulo) for rotulo in _todos(valuation, classe="metrica-rotulo")])


def test_sob_fronteira_a_conclusao_e_condicional_e_a_valuation_chama_o_preco_de_leitura_condicional(tmp_path):
    """Sob fronteira de escopo a Conclusão diz "conclusão condicional, sem preço-alvo", com a
    classe rotulada pelo catálogo, a arquitetura dominante e a razão, sem faixa e — onda de
    correção da revisão final (F1) — só com o múltiplo de tela: o múltiplo justo ao lado do de
    tela é o upside dito em outra unidade. O bloco de avisos traz a limitação de escopo (N10),
    nunca "nenhum aviso obrigatório". E o preço por ação vira leitura condicional NOS DOIS
    lugares da Valuation que o chamavam de preço justo — o cabeçalho e as saídas do
    laboratório. A vizinha fora da fronteira continua com "Conclusão", os dois múltiplos,
    nenhum aviso e "Preço justo" nos dois lugares."""
    sob = _sob_fronteira()
    fronteira = sob["resultados"]["fronteira_de_escopo"]
    pagina = _pagina_pelo_builder(sob, tmp_path / "sob")

    conclusao = _secoes(_aba(pagina, "tese"))[0]
    assert _titulo(conclusao) == TESE["conclusao_condicional_titulo"]
    assert [_visivel(_um(conclusao, classe=classe))
            for classe in ("tese-fronteira-classe", "tese-fronteira-arquitetura", "tese-fronteira-razao")] == [
        CATALOGO["fronteiras_de_escopo"][fronteira["classe"]]["rotulo"]["pt-BR"],
        fronteira["arquitetura_dominante"], fronteira["razao"]]
    assert _todos(conclusao, classe="tese-faixa") == []
    tela = sob["resultados"]["mercado_tela"]
    assert _metricas(_um(conclusao, classe="tese-multiplos")) == [
        (VALUATION["multiplo_tela_titulo"], placeholders.formatar(tela["valor"], "x2", "pt-BR"),
         CATALOGO["multiplos"][tela["chave"]]["rotulo"]["pt-BR"])]

    avisos = _secao(_aba(pagina, "tese"), TESE["disclosures_titulo"])
    rotulo_da_classe = CATALOGO["fronteiras_de_escopo"][fronteira["classe"]]["rotulo"]["pt-BR"]
    assert [_visivel(item) for item in _todos(avisos, tag="li")] == [
        DICIONARIO["qc"]["fronteira_de_escopo_declarada"].format(rotulo=rotulo_da_classe)]

    condicional = VALUATION["condicional"]["preco_justo_titulo"]
    justo = VALUATION["preco_justo_titulo"]
    cabecalho, laboratorio, todos = _rotulos_do_preco_na_valuation(pagina)
    assert laboratorio, "a página do builder traz o laboratório — sem ele, a asserção seria vácua"
    assert (cabecalho, set(laboratorio)) == (condicional, {condicional})
    assert justo not in todos

    fora = _pagina_pelo_builder(_entrega(), tmp_path / "fora")
    conclusao_fora = _secoes(_aba(fora, "tese"))[0]
    assert _titulo(conclusao_fora) == TESE["conclusao_titulo"]
    assert [rotulo for rotulo, _valor, _nota in _metricas(_um(conclusao_fora, classe="tese-multiplos"))] == [
        VALUATION["multiplo_justo_titulo"], VALUATION["multiplo_tela_titulo"]]
    assert _visivel(_secao(_aba(fora, "tese"), TESE["disclosures_titulo"])) == (
        f'{TESE["disclosures_titulo"]} {TESE["disclosures_vazio"]}')
    cabecalho, laboratorio, todos = _rotulos_do_preco_na_valuation(fora)
    assert (cabecalho, set(laboratorio)) == (justo, {justo})
    assert condicional not in todos


def _rotulos_e_titulos(aba: dict) -> list:
    """Todo título e todo rótulo da aba — o que o leitor lê como o nome de um número."""
    return [_visivel(el) for el in _elementos(aba)
            if el["tag"] in ("h1", "h2", "h3", "h4") or any(classe.endswith("rotulo") for classe in _classes(el))]


def _e_o_rotulo(texto: str, modelo: str) -> bool:
    """`texto` é o rótulo `modelo` do dicionário, com qualquer valor nos `{marcadores}`."""
    literais = re.split(r"\{[^{}]*\}", modelo)
    return re.fullmatch(".+".join(re.escape(literal) for literal in literais), texto) is not None


def test_sob_fronteira_nenhum_numero_de_valor_sai_com_rotulo_incondicional_nas_abas_tese_e_valuation(tmp_path):
    """F1 da revisão: sob fronteira, o upside do cabeçalho, o múltiplo justo, a lista de preços
    por cenário, as três saídas de cada cenário do laboratório e a matriz de sensibilidade
    saíam com os rótulos incondicionais — "Upside sobre o preço de mercado 12,6%" ao lado de
    "(sem preço-alvo)". A varredura lê TODO título e rótulo das duas abas contra a lista de
    rótulos incondicionais do dicionário — os que têm forma condicional
    (`valuation.condicional`) e os da faixa, que sob fronteira não existe: nenhum aparece. A
    vizinha fora da fronteira prova que a entrega exercita todos esses lugares — cabeçalho,
    múltiplos, três cenários, grade 2D e laboratório —, senão a varredura seria vácua."""
    condicionais = VALUATION["condicional"]
    incondicionais = {chave: VALUATION[chave] for chave in condicionais}
    da_faixa = [TESE["faixa_rotulo"], TESE["faixa_rotulo_consolidado"], *TESE["papeis_da_faixa"].values()]

    def _rotulos(pagina: str) -> list:
        return [texto for nome in ("tese", "valuation") for texto in _rotulos_e_titulos(_aba(pagina, nome))]

    def _presentes(rotulos: list, modelos: dict) -> set:
        return {chave for chave, modelo in modelos.items() if any(_e_o_rotulo(rotulo, modelo) for rotulo in rotulos)}

    fora = _rotulos(_pagina_pelo_builder(_entrega("caso_reversa_firm.json", variante="tres_cenarios"),
                                         tmp_path / "fora"))
    assert _presentes(fora, incondicionais) == set(incondicionais), "a entrega não exercita todo lugar da varredura"
    assert _presentes(fora, condicionais) == set()

    sob = _rotulos(_pagina_pelo_builder(_entrega("caso_reversa_firm.json", variante="tres_cenarios_sob_fronteira"),
                                        tmp_path / "sob"))
    assert [rotulo for rotulo in sob
            if any(_e_o_rotulo(rotulo, modelo) for modelo in [*incondicionais.values(), *da_faixa])] == []
    assert _presentes(sob, condicionais) == set(condicionais)


def test_a_tela_decide_pelo_mapa_da_integracao_qual_numero_e_leitura_condicional():
    """E3 na tela: a mesma entrega sob fronteira, dois catálogos. Com `manchete.upside` no mapa,
    o upside do cabeçalho é leitura condicional; fora dele, volta ao rótulo de sempre — a tela
    lê a declaração da integração, nunca o nome do campo. O múltiplo de tela, que o mapa não
    cobre, sai sempre com o seu rótulo."""
    sob = _sob_fronteira()
    condicional = VALUATION["condicional"]

    def _cabecalho_e_multiplos(catalogo: dict) -> tuple:
        achados = _achados(sob, catalogo)
        assert not [a for a in achados if a.nivel == "HARD_FAIL"], achados
        _prosa, log = placeholders.resolver_prosa(sob, "pt-BR")
        resolvidos, log_exhibits = exhibits_mod.resolver(sob)
        aba = _aba(render.compor(sob, catalogo, achados, log, "pt-BR", resolvidos, log_exhibits), "valuation")
        return ([_visivel(r) for r in _todos(_um(aba, classe="valuation-cabecalho"), classe="metrica-rotulo")],
                [_visivel(r) for r in _todos(_um(aba, classe="valuation-multiplos"), classe="metrica-rotulo")])

    assert _cabecalho_e_multiplos(CATALOGO) == (
        [condicional["preco_justo_titulo"], condicional["upside_titulo"]],
        [condicional["multiplo_justo_titulo"], VALUATION["multiplo_tela_titulo"]])

    sem_o_upside = copy.deepcopy(CATALOGO)
    sem_o_upside["conclusoes_de_valor"]["fração"].remove("manchete.upside")
    assert _cabecalho_e_multiplos(sem_o_upside) == (
        [condicional["preco_justo_titulo"], VALUATION["upside_titulo"]],
        [condicional["multiplo_justo_titulo"], VALUATION["multiplo_tela_titulo"]])


# --------------------------------------------------------------------------
# Achados 3 e 4: toda a prosa auditada — o log da Evidência e o caption.
# --------------------------------------------------------------------------

def test_um_placeholder_num_texto_da_tese_ou_de_um_exhibit_entra_no_log_da_evidencia(tmp_path):
    """O log de resolução da Evidência listava só a conclusão: um número citado num texto
    novo saía resolvido na tela e FORA da trilha de auditoria. O builder resolve toda a
    prosa pela mesma lista que o QC varre, e a tela mostra, no lugar do placeholder, o
    número que o log registra."""
    entrega_dict = _entrega_com_exhibits_nas_perguntas()
    analise = entrega_dict["analise"]
    analise["perguntas"][2]["evidencia"] = "Negociada a {{caso:preco.valor|moeda}} na tela."
    analise["exhibits"][2]["caption"] = "A manchete, {{resultados:manchete.preco_acao|moeda}} por ação."
    preco_de_tela = entrega_dict["caso"]["preco"]["valor"]
    manchete = entrega_dict["resultados"]["manchete"]["preco_acao"]
    pagina = _pagina_pelo_builder(entrega_dict, tmp_path / "log")

    tabela = _um(_aba(pagina, "evidencia"), classe="log-placeholders")
    linhas = [[_visivel(celula) for celula in _todos(linha, tag="td")] for linha in _todos(tabela, tag="tr")]
    for esperada in (
            ["analise.perguntas.2.evidencia", "caso", "preco.valor", "moeda", str(preco_de_tela),
             _moeda(entrega_dict, preco_de_tela)],
            ["analise.exhibits.2.caption", "resultados", "manchete.preco_acao", "moeda", str(manchete),
             _moeda(entrega_dict, manchete)]):
        assert esperada in linhas, linhas

    aba = _aba(pagina, "tese")
    assert _visivel(_um(_todos(aba, classe="tese-pergunta")[2], classe="tese-evidencia")) == (
        f"Negociada a {_moeda(entrega_dict, preco_de_tela)} na tela.")
    assert _visivel(_um(_secao(aba, TESE["exhibits_nao_citados_titulo"]), classe="exhibit-caption")) == (
        f"A manchete, {_moeda(entrega_dict, manchete)} por ação.")


def test_um_digito_solto_no_caption_de_um_exhibit_nao_emite(tmp_path):
    """Dentro da aba Tese, "a margem subiu de 12% para 18%" num caption é número sem
    proveniência no meio da tese — o HARD FAIL da §11. A mesma entrega sem o dígito não
    traz achado nenhum."""
    assert _achados(_entrega_com_exhibits_nas_perguntas()) == []
    entrega_dict = _entrega_com_exhibits_nas_perguntas()
    entrega_dict["analise"]["exhibits"][1]["caption"] = "A margem subiu de 12% para 18% no período."
    raiz = tmp_path / "caption_com_digito"
    apoio.escrever_raiz(raiz, entrega_dict)

    resultado = _rodar_builder(raiz)

    assert resultado.returncode == 2, resultado.stdout + resultado.stderr
    assert not (raiz / "relatorio.html").exists()
    assert [(a["nivel"], a["codigo"], a["onde"]) for a in _ler_qc(raiz)["achados"]] == [
        ("HARD_FAIL", "numero_sem_proveniencia", "analise.exhibits.1.caption")]


# --------------------------------------------------------------------------
# Achado 5: a faixa de um caso SOTP.
# --------------------------------------------------------------------------

def test_num_caso_sotp_a_faixa_sai_rotulada_como_a_do_consolidado_e_a_manchete_continua_o_sotp():
    """A manchete de um caso SOTP é o preço da soma das partes, e a faixa mostra os preços
    dos cenários CONSOLIDADOS — dois preços "base" na mesma página. A faixa sai rotulada como
    a do consolidado, nomeando o preço da manchete; fora do SOTP, o rótulo comum."""
    sotp = _entrega("caso_sotp_segmento.json")
    manchete = sotp["resultados"]["manchete"]
    assert manchete["fonte"] == "sotp", "o valor que avaliar._montar_manchete publica para a manchete do SOTP"
    base = sotp["resultados"]["cenarios"][sotp["analise"]["faixa"]["base"]]["valor"]["preco_acao"]
    assert _moeda(sotp, base) != _moeda(sotp, manchete["preco_acao"]), "sem os dois preços, o teste não discrimina"

    faixa = _um(_aba(_pagina_da_tese(sotp), "tese"), classe="tese-faixa")
    assert _visivel(_um(faixa, classe="tese-faixa-rotulo")) == render.t(
        DICIONARIO, "tese.faixa_rotulo_consolidado", preco=_moeda(sotp, manchete["preco_acao"]))
    assert [_visivel(valor) for valor in _todos(faixa, classe="metrica-valor")] == [_moeda(sotp, base)] * 3

    vizinha = _entrega()
    assert vizinha["resultados"]["manchete"]["fonte"] == "cenarios"
    faixa_vizinha = _um(_aba(_pagina_da_tese(vizinha), "tese"), classe="tese-faixa")
    assert _visivel(_um(faixa_vizinha, classe="tese-faixa-rotulo")) == TESE["faixa_rotulo"]


def test_num_caso_sotp_as_premissas_decisivas_saem_rotuladas_como_as_do_cenario_consolidado():
    """F4 da revisão: em `caso_sotp_safra` a Conclusão diz o preço da soma das partes, e as
    premissas decisivas mostravam o WACC, o g e o ROIC do cenário consolidado — que nenhuma
    parte usa — sem nada que o dissesse. A seção sai com o rótulo do consolidado, do
    dicionário, nomeando o cenário, e sem número: sob fronteira ela também aparece, e não
    leva conclusão de valor à Tese. Fora do SOTP, nenhum rótulo."""
    sotp = _entrega("caso_sotp_safra.json")
    resultados = sotp["resultados"]
    assert resultados["manchete"]["fonte"] == "sotp"
    modelo = TESE["premissas_decisivas_rotulo_consolidado"]
    assert not re.search(r"\d", modelo)
    secao = _secao(_aba(_pagina_da_tese(sotp), "tese"), TESE["premissas_decisivas_titulo"])
    assert _visivel(_um(secao, classe="tese-premissas-rotulo")) == modelo.format(
        cenario=resultados["manchete"]["cenario"])

    vizinha = _secao(_aba(_pagina_da_tese(_entrega()), "tese"), TESE["premissas_decisivas_titulo"])
    assert _todos(vizinha, classe="tese-premissas-rotulo") == []


# --------------------------------------------------------------------------
# Onda de correção da revisão final (F3, N12): o que a Tese exibe entra na lista de
# prosa — o texto da fronteira de escopo, que a Conclusão mostra, e os textos que o
# gráfico escreve sob a pergunta —, com o QC, o log da Evidência e a guarda
# `ProsaNaoAuditada` valendo para eles.
# --------------------------------------------------------------------------

def _entrega_sob_fronteira_com(**textos) -> dict:
    """Uma entrega sob fronteira com os textos da fronteira que o teste declara: o caso é
    mutado antes de `avaliar()`, e `resultados.fronteira_de_escopo` os publica."""
    def _mutar(caso: dict) -> None:
        _com_fronteira_de_escopo(caso)
        caso["fronteira_de_escopo"].update(textos)
    return apoio.montar_entrega(FIXTURE, mutar_caso=_mutar)


@pytest.mark.parametrize("campo", ["arquitetura_dominante", "razao"])
def test_digito_solto_no_texto_da_fronteira_de_escopo_e_hard_fail(campo):
    """F3 da revisão: "as reservas provadas cobrem 9 anos de produção e a concessão vence em
    2031" saía na Conclusão sem QC e sem linha no log — e a mesma frase no veredicto era
    HARD FAIL. O texto da fronteira é prosa da Tese."""
    assert _do_codigo(_achados(_sob_fronteira()), "numero_sem_proveniencia") == []

    com_digito = _entrega_sob_fronteira_com(
        **{campo: "as reservas provadas cobrem 9 anos de produção e a concessão vence em 2031"})
    assert [(a.nivel, a.onde) for a in _do_codigo(_achados(com_digito), "numero_sem_proveniencia")] == [
        ("HARD_FAIL", f"resultados.fronteira_de_escopo.{campo}")]


def test_o_texto_da_fronteira_sai_resolvido_na_conclusao_e_registrado_no_log_da_evidencia(tmp_path):
    """Com o número marcado, `{{livre:9}}`, a Conclusão mostra o texto resolvido e o log da
    Evidência registra o placeholder — como o de qualquer texto da Tese."""
    entrega_dict = _entrega_sob_fronteira_com(razao="as reservas provadas cobrem {{livre:9}} anos de produção")
    pagina = _pagina_pelo_builder(entrega_dict, tmp_path / "fronteira")

    conclusao = _secoes(_aba(pagina, "tese"))[0]
    assert _visivel(_um(conclusao, classe="tese-fronteira-razao")) == "as reservas provadas cobrem 9 anos de produção"
    tabela = _um(_aba(pagina, "evidencia"), classe="log-placeholders")
    linhas = [[_visivel(celula) for celula in _todos(linha, tag="td")] for linha in _todos(tabela, tag="tr")]
    assert ["resultados.fronteira_de_escopo.razao", "livre", "", "", "9", "9"] in linhas, linhas


def test_os_textos_que_o_grafico_escreve_saem_resolvidos_no_payload_e_nunca_a_chave_crua(tmp_path):
    """F3 e N12 da revisão: o rótulo da série engine, a nota da série derivada e o rótulo do
    overlay são escritos pelo gráfico dentro da aba Tese — na legenda e no cabeçalho da
    tabela. Saem da lista de prosa, resolvidos: um placeholder no rótulo de um overlay vira o
    número formatado no payload e uma linha no log da Evidência; e a série engine leva o
    rótulo que declara, nunca `resultados:manchete.preco_acao`."""
    entrega_dict = _entrega_com_exhibits_nas_perguntas()
    receita = next(exhibit for exhibit in entrega_dict["analise"]["exhibits"] if exhibit["id"] == "receita")
    receita["overlays"] = [{"chave": "caso:preco.valor", "rotulo": "preço de tela, {{caso:preco.valor|moeda}}"}]
    preco = entrega_dict["caso"]["preco"]["valor"]
    pagina = _pagina_pelo_builder(entrega_dict, tmp_path / "rotulos")

    dados = json.loads(re.search(r'<script type="application/json" id="fleet-dados-exhibits">(.*?)</script>',
                                 pagina, re.S).group(1))
    por_id = {spec["id"]: spec for spec in dados["exhibits"]}
    assert [overlay["rotulo"] for overlay in por_id["receita"]["overlays"]] == [
        f"preço de tela, {_moeda(entrega_dict, preco)}"]
    assert [serie["rotulo"] for serie in por_id["margem"]["series"]] == ["margem EBITDA"]
    assert [serie["rotulo"] for serie in por_id["preco"]["series"]] == ["preço por ação no cenário da manchete"]
    rotulos = [item["rotulo"] for spec in dados["exhibits"] for item in spec["series"] + spec["overlays"]]
    assert [rotulo for rotulo in rotulos if rotulo.startswith(("resultados:", "caso:"))] == []

    indice_da_receita = [spec["id"] for spec in dados["exhibits"]].index("receita")
    tabela = _um(_aba(pagina, "evidencia"), classe="log-placeholders")
    linhas = [[_visivel(celula) for celula in _todos(linha, tag="td")] for linha in _todos(tabela, tag="tr")]
    assert [f"analise.exhibits.{indice_da_receita}.overlays.0.rotulo", "caso", "preco.valor", "moeda", str(preco),
            _moeda(entrega_dict, preco)] in linhas, linhas
