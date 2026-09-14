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
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
SCRIPTS = RAIZ / "skills" / "er-relatorio" / "scripts"
BUILDER = SCRIPTS / "builder.py"

sys.path.insert(0, str(SCRIPTS))
import entrega  # noqa: E402
import placeholders  # noqa: E402
import qc  # noqa: E402

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


_VARIANTES = {"padrao": None, "tres_cenarios": _tres_cenarios, "fronteira": _com_fronteira_de_escopo}


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
    return qc.avaliar(entrega_dict, catalogo, html=None)


def _do_codigo(achados: list, codigo: str) -> list:
    return [a for a in achados if a.codigo == codigo]


def _carregar(entrega_dict: dict, tmp_path: Path) -> dict:
    raiz = tmp_path / "raiz"
    apoio.escrever_raiz(raiz, entrega_dict)
    return entrega.carregar(raiz)


# --------------------------------------------------------------------------
# A entrega padrão do apoio: válida no contrato e sem disparar regra nenhuma por
# conta própria (armadilha 2 do briefing). Os únicos achados são os disclosures
# NOMEADOS que o próprio caso impõe — o de divergência de base do degrau, e o da
# limitação que torna a reversa impossível (D4) em `caso_degrau` e `caso_rampa`.
# --------------------------------------------------------------------------

_ACHADOS_DA_ENTREGA_PADRAO = {
    "caso_degrau.json": [("REQUIRED_DISCLOSURE", "divergencia_de_base_degrau"),
                         ("REQUIRED_DISCLOSURE", "limitacao_metodologica")],
    "caso_rampa.json": [("REQUIRED_DISCLOSURE", "limitacao_metodologica")],
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
    "series": [{"derivacao": "engine", "chave": "resultados:manchete.preco_acao"}],
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


def test_preco_de_tela_sob_fronteira_nao_e_preco_alvo():
    sob = _sob_fronteira()
    _acrescentar(sob, ("veredicto", "texto"), " Preço de tela: {{caso:preco.valor|moeda}}.")
    assert _do_codigo(_achados(sob), "fronteira_com_preco_alvo") == []


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
    return entrega_dict


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
    ondes = [onde for onde, _texto in qc._campos_de_prosa(entrega_dict)]
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
