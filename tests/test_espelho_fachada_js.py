"""A fachada do espelho (camada de integração) contra o `resultados` que o
Python publica — fatia 5C, item 5, Task 1.

`skills/er-valuation/assets/espelho_fachada.js` é o equivalente em JS do
caminho de `avaliar.py` que produz o preço de cada cenário: recebe o `caso`
e devolve o subconjunto VIVO do `resultados.json` (preço, múltiplo de
referência e ponte), nas mesmas chaves. Ela mora na integração, não no
relatório (L1 do plano/E3): traduzir `caso` -> shape de `resultados` é
conhecimento de integração e paridade; o relatório só embute e chama.

Este harness é o que torna essa fachada admissível — o mesmo papel que
`test_paridade_js.py` cumpre para o espelho do núcleo, e a mesma tolerância
(erro RELATIVO com piso absoluto, |py - js| <= max(TAU*|py|, TAU)). Sem node
os testes PULAM com razão explícita; o CI tem node (setup-node) e sempre
roda.

O lado Python é `relatorio_apoio.montar_entrega`, que roda `avaliar()` de
VERDADE (motor congelado por subprocesso) sobre cada fixture de caso — nunca
um `resultados` forjado à mão: o que a fachada tem de reproduzir é o número
que o Python publica, não um número que este arquivo inventou.
"""

import functools
import json
import re
import subprocess
import sys
from collections import Counter

import pytest

from relatorio_apoio import FIXTURES, VARIANTES_DO_CASO, listas_de_chaves_de_diagnostico, montar_entrega
from test_espelho_js import ESPELHO, RAIZ, RAZAO, SEM_NODE

sys.path.insert(0, str(RAIZ / "skills" / "er-valuation" / "scripts"))
from avaliar import (_ALERTAS_DEGRAU_ORDEM, _CHAVE_DIVERGENCIA_DE_BASE, _CHAVES_DA_CONSERVACAO,  # noqa: E402
                     _LIMIAR_DIVERGENCIA_DE_BASE_PCT, avaliar)
from caso import _PREMISSAS_POR_ROTA, TV_CANON, CasoInvalido, carregar, validar  # noqa: E402
from motor import MotorFalhou  # noqa: E402

FACHADA = RAIZ / "skills" / "er-valuation" / "assets" / "espelho_fachada.js"
CATALOGO = json.loads(
    (RAIZ / "skills" / "er-valuation" / "assets" / "catalogo_apresentacao.json").read_text(encoding="utf-8"))

# Mesma tolerância dos três harnesses de paridade (ver `test_paridade_js.py`,
# que a documenta e mede a folga): as grandezas aqui vão de múltiplo (~6) a
# preço por ação (~60), e a fachada não introduz conta nenhuma além das do
# espelho — um desvio acima disto é erro de orquestração, não ruído de
# ponto flutuante.
TAU = 1e-12

# Toda fixture de caso do repositório — derivada por glob, não uma lista
# estática: uma fixture nova entra neste harness no instante em que o arquivo
# passa a existir. A fachada admite as três rotas (firm, equity, rampa) e o
# bloco `degrau`, então nenhuma fixture de caso fica de fora hoje.
FIXTURES_DE_CASO: list = sorted(p.name for p in FIXTURES.glob("caso_*.json"))

# Fatia 5F, Task 3 (D6): as variantes compostas do apoio com a conservação de capital — a forma de
# diagnóstico que nenhuma fixture publica. As travas da lista exibida e das chaves as incluem.
VARIANTES_COM_CONSERVACAO: list = ["conservacao_fecha", "conservacao_nao_fecha"]

# Harness em node: carrega a fachada, avalia o caso e compara com o
# `resultados`, devolvendo TUDO num JSON só — inclusive a recusa, quando a
# fachada lança (é assim que o laboratório vai vê-la: uma exceção nomeada,
# nunca um número desenhado em silêncio).
_HARNESS = (
    "const fs = require('fs');"
    "const F = require(%s);"
    "const p = JSON.parse(fs.readFileSync(%s, 'utf-8'));"
    "const saida = {versao_contrato: F.VERSAO_CONTRATO, rotas: F.ROTAS_ATENDIDAS,"
    " motivos: F.MOTIVOS_DE_RECUSA};"
    "try {"
    "  saida.vivo = F.avaliarCaso(p.caso);"
    "  saida.comparacao = F.compararComResultados(p.caso, p.resultados);"
    "} catch (erro) {"
    "  saida.erro = {mensagem: String(erro && erro.message), codigo: erro && erro.codigo};"
    "}"
    "console.log(JSON.stringify(saida));"
)


def _compor(variante: str):
    """`mutar_caso` que aplica, no lugar, a composição de uma variante do apoio ao caso carregado."""
    def _mutar(caso: dict) -> None:
        caso.update(VARIANTES_DO_CASO[variante][1](caso))
    return _mutar


@functools.lru_cache(maxsize=None)
def _entrega(fixture: str, nopat: bool = False) -> str:
    """`montar_entrega` cacheado (roda o motor por subprocesso, cenário a
    cenário — sem cache, cada teste parametrizado pagaria de novo).

    Devolve JSON (string) porque `lru_cache` exige retorno hashável só para
    a CHAVE, mas um dict devolvido seria compartilhado e mutável entre
    testes — e dois testes abaixo ADULTERAM o `resultados` de propósito. A
    string é desserializada a cada chamada, então cada teste recebe a sua
    própria cópia.

    `nopat=True`: mesma fixture firm, com a métrica-base trocada para NOPAT
    (`mutar_caso` roda ANTES de `avaliar()`, então o `resultados` reflete a
    troca por construção). Nenhuma fixture commitada exercita o ramo NOPAT
    da rota firm — e é justamente o ramo em que a chave do múltiplo de
    referência muda (`EV/NOPAT_curr`), o que este arquivo prende.
    """
    def _para_nopat(caso: dict) -> None:
        caso["metrica_base"] = {"tipo": "NOPAT", "valor": 600.0,
                                "fonte": "harness da fachada"}

    if fixture in VARIANTES_DO_CASO:
        # Fatia 5F, Task 3: `fixture` pode ser o nome de uma variante composta do apoio (D14) — a
        # fixture-base com a composição aplicada antes de `avaliar()`.
        return json.dumps(montar_entrega(VARIANTES_DO_CASO[fixture][0], mutar_caso=_compor(fixture)),
                          ensure_ascii=False)
    entrega = montar_entrega(fixture, mutar_caso=_para_nopat if nopat else None)
    return json.dumps(entrega, ensure_ascii=False)


def _caso_e_resultados(fixture: str, nopat: bool = False) -> tuple[dict, dict]:
    entrega = json.loads(_entrega(fixture, nopat))
    return entrega["caso"], entrega["resultados"]


def _fachada(caso: dict, resultados: dict, tmp_path) -> dict:
    arq = tmp_path / "payload.json"
    arq.write_text(json.dumps({"caso": caso, "resultados": resultados}, ensure_ascii=False),
                   encoding="utf-8")
    script = _HARNESS % (json.dumps(str(FACHADA)), json.dumps(str(arq)))
    r = subprocess.run(["node", "-e", script],
                       capture_output=True, text=True, encoding="utf-8", timeout=120)
    assert r.returncode == 0, r.stdout + r.stderr
    return json.loads(r.stdout)


def _erro_relativo(p: float, j: float) -> float:
    """Mesma fórmula de `test_paridade_js.py`: relativo com piso absoluto."""
    return abs(p - j) / max(abs(p), 1.0)


# ---------------------------------------------------------------------------
# O subconjunto vivo reproduz o que o Python publicou
# ---------------------------------------------------------------------------

@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
@pytest.mark.parametrize("fixture", FIXTURES_DE_CASO)
def test_a_fachada_reproduz_o_preco_de_cada_cenario_de_cada_fixture(fixture, tmp_path):
    """O contrato central: para TODA fixture que a rota admita, o preço por
    ação de cada cenário sai do JS dentro de TAU do que o Python publicou —
    e `compararComResultados` concorda (`ok: true`, sem divergência)."""
    caso, resultados = _caso_e_resultados(fixture)
    saida = _fachada(caso, resultados, tmp_path)
    assert "erro" not in saida, saida.get("erro")

    cenarios_js = saida["vivo"]["cenarios"]
    assert sorted(cenarios_js) == sorted(resultados["cenarios"])
    for nome, cenario_py in resultados["cenarios"].items():
        preco_py = cenario_py["valor"]["preco_acao"]
        preco_js = cenarios_js[nome]["valor"]["preco_acao"]
        assert preco_js is not None, f"{fixture}/{nome}: fachada recusou onde o Python precificou"
        assert _erro_relativo(preco_py, preco_js) <= TAU, \
            f"{fixture}/{nome}: py={preco_py} js={preco_js}"
        # As premissas voltam ecoadas — é o vetor que produziu o preço, e o
        # laboratório edita exatamente essas chaves.
        assert cenarios_js[nome]["premissas"] == caso["cenarios"][nome]["premissas"]

    assert saida["comparacao"]["ok"] is True, saida["comparacao"]["divergencias"]


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
@pytest.mark.parametrize("fixture,nopat,chave_esperada", [
    ("caso_minimo_firm.json", False, "EV/EBITDA_curr"),
    ("caso_minimo_firm.json", True, "EV/NOPAT_curr"),
    ("caso_minimo_equity.json", False, "PL_curr"),
    ("caso_rampa.json", False, "EV/EBITDA0"),
])
def test_o_multiplo_da_fachada_e_a_chave_curr_da_metrica_declarada(
        fixture, nopat, chave_esperada, tmp_path):
    """A correspondência que o plano mandou CONFIRMAR, não presumir.

    `precificarCelula` devolve UM múltiplo (o da métrica declarada) enquanto
    `resultados.cenarios.<n>.multiplos` traz quatro chaves na rota firm. A
    hipótese do plano — que o múltiplo da fachada é a chave `_curr` da
    métrica declarada — foi confirmada por execução e fica presa aqui: a
    chave publicada é a esperada, o valor bate com a entrada correspondente
    de `multiplos` dentro de TAU, e — o que torna o teste discriminante —
    NENHUMA outra chave de `multiplos` casa com esse mesmo número, então a
    correspondência não pode passar por coincidência aritmética.
    """
    caso, resultados = _caso_e_resultados(fixture, nopat)
    saida = _fachada(caso, resultados, tmp_path)
    assert "erro" not in saida, saida.get("erro")

    for nome, cenario_py in resultados["cenarios"].items():
        multiplo_js = saida["vivo"]["cenarios"][nome]["multiplo"]
        assert multiplo_js["chave"] == chave_esperada
        assert multiplo_js["valor"] is not None
        casam = {chave for chave, valor in cenario_py["multiplos"].items()
                 if _erro_relativo(valor, multiplo_js["valor"]) <= TAU}
        assert casam == {chave_esperada}, (
            f"{fixture}/{nome}: múltiplo {multiplo_js['valor']} casa com {sorted(casam)}, "
            f"esperado só {chave_esperada} — multiplos={cenario_py['multiplos']}")


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_um_caso_com_degrau_reproduz_o_preco_COM_degrau(tmp_path):
    """L3: o caso com degrau publica o preço COM degrau (D3 da fatia D) — uma
    fachada que só rodasse a perna P/L acusaria divergência num caso
    legítimo. O preço da perna sem degrau entra na asserção como CONTROLE:
    os dois números são materialmente diferentes, então reproduzir o
    primeiro não é reproduzir o segundo por acaso. O múltiplo de referência
    acompanha o preço (`PVP_com_degrau`, o `com_transicao` do próprio
    degrau — a mesma escolha que `avaliar._montar_manchete` publica).
    """
    caso, resultados = _caso_e_resultados("caso_degrau.json")
    saida = _fachada(caso, resultados, tmp_path)
    assert "erro" not in saida, saida.get("erro")

    cenario_py = resultados["cenarios"]["base"]
    preco_com_degrau = cenario_py["valor"]["preco_acao"]
    preco_sem_degrau = cenario_py["sem_degrau"]["valor"]["preco_acao"]
    assert _erro_relativo(preco_com_degrau, preco_sem_degrau) > 0.1, \
        "fixture deixou de discriminar as duas pernas — o controle deste teste morreu"

    cenario_js = saida["vivo"]["cenarios"]["base"]
    assert _erro_relativo(preco_com_degrau, cenario_js["valor"]["preco_acao"]) <= TAU
    assert cenario_js["multiplo"]["chave"] == "PVP_com_degrau"
    assert _erro_relativo(cenario_py["degrau"]["com_transicao"],
                          cenario_js["multiplo"]["valor"]) <= TAU
    assert saida["comparacao"]["ok"] is True, saida["comparacao"]["divergencias"]


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
@pytest.mark.parametrize("fixture", FIXTURES_DE_CASO)
def test_a_ponte_publicada_e_a_mesma_do_resultados(fixture, tmp_path):
    """A ponte é parte do escopo vivo (L3): o `nd_efetivo` que a fachada soma
    do `caso` é o mesmo que `ponte.compor` publicou. Na rota equity não há
    ponte de dívida — `resultados.json` não publica o bloco, e a fachada
    também não (mesmas chaves, L2)."""
    caso, resultados = _caso_e_resultados(fixture)
    saida = _fachada(caso, resultados, tmp_path)
    assert "erro" not in saida, saida.get("erro")

    if "ponte" in resultados:
        assert _erro_relativo(resultados["ponte"]["nd_efetivo"],
                              saida["vivo"]["ponte"]["nd_efetivo"]) <= TAU
    else:
        assert "ponte" not in saida["vivo"], saida["vivo"].get("ponte")


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
@pytest.mark.parametrize("fixture", ["caso_minimo_firm.json", "caso_rampa.json",
                                     "caso_degrau.json"])
def test_um_vetor_fora_de_dominio_recusa_o_cenario_em_vez_de_inventar_numero(fixture, tmp_path):
    """O que o laboratório vai produzir o tempo todo: uma premissa editada
    para fora do domínio da CLI do motor (`n < 1`, `avaliar_dominios_cli`).
    As três pernas têm de responder no MESMO vocabulário do espelho — `null`
    nos dois números, nunca um preço inventado — e o comparador tem de contar
    isso como divergência (falha FECHADA), nunca como "ok por ausência de
    número". Sem esta asserção, a perna da rampa e a do degrau estourariam um
    TypeError dentro do laboratório em vez de recusar."""
    caso, resultados = _caso_e_resultados(fixture)
    caso["cenarios"]["base"]["premissas"]["n"] = 0

    saida = _fachada(caso, resultados, tmp_path)
    assert "erro" not in saida, saida.get("erro")
    cenario = saida["vivo"]["cenarios"]["base"]
    assert cenario["valor"]["preco_acao"] is None, cenario
    assert cenario["multiplo"]["valor"] is None, cenario
    # Task 2: sem preço não há upside — `null`, nunca `-100%` (o que
    # `null / preco - 1` produziria em JS, um número plausível e falso).
    assert cenario["vs_preco"]["upside"] is None, cenario

    comparacao = saida["comparacao"]
    assert comparacao["ok"] is False
    divergencia = next(d for d in comparacao["divergencias"] if d["chave"] == "valor.preco_acao")
    assert divergencia["js"] is None
    assert divergencia["erro_relativo"] is None
    assert divergencia["python"] == resultados["cenarios"]["base"]["valor"]["preco_acao"]

    # Onda de correção da revisão final (F2): um cenário recusado não afirma "nenhum
    # diagnóstico". As listas saem `null` — nunca `[]` —, a lista exibível também, e o motivo
    # sai nomeado: n < 1 é recusa de domínio da CLI (`avaliar_dominios_cli`, código 2 no motor).
    assert cenario["diagnosticos_chaves"] is None, cenario
    assert cenario["diagnosticos_exibidos"] is None, cenario
    assert cenario["recusa"] == {"codigo": "dominio_da_cli"}, cenario
    if "degrau" in resultados["cenarios"]["base"]:
        assert cenario["degrau"]["diagnosticos_chaves"] is None, cenario
    lista = next(d for d in comparacao["divergencias"] if d["chave"] == "diagnosticos_chaves")
    assert lista["js"] is None and lista["erro_relativo"] is None, lista


# ---------------------------------------------------------------------------
# Fatia 5C, Task 2 — o upside, e a trava de rotas contra o gate
# ---------------------------------------------------------------------------

@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
@pytest.mark.parametrize("fixture", FIXTURES_DE_CASO)
def test_a_fachada_publica_o_upside_de_cada_cenario(fixture, tmp_path):
    """Achado 2 da Task 1: o painel promete "preço, múltiplo e upside
    recalculados", e `upside` é comparação entre dois números (preço justo ×
    preço de tela) — conta que NÃO pode nascer em `laboratorio.js` (fronteira
    E3). A definição é a de `avaliar._monta_cenario`: `preco_acao /
    caso.preco.valor - 1`, a mesma que o Python publica em
    `cenarios.<n>.vs_preco.upside`.

    Discriminante: além de bater com o número publicado dentro de TAU, o
    upside tem de ser DIFERENTE do resultado que sairia da definição errada
    mais provável — dividir pelo preço justo do cenário-base, ou esquecer o
    `-1`. As duas alternativas são checadas explicitamente, para que o teste
    não passe por um `0.0` acidental."""
    caso, resultados = _caso_e_resultados(fixture)
    saida = _fachada(caso, resultados, tmp_path)
    assert "erro" not in saida, saida.get("erro")

    preco_de_tela = caso["preco"]["valor"]
    for nome, cenario_py in resultados["cenarios"].items():
        upside_py = cenario_py["vs_preco"]["upside"]
        upside_js = saida["vivo"]["cenarios"][nome]["vs_preco"]["upside"]
        assert upside_js is not None, f"{fixture}/{nome}: fachada não publicou upside"
        assert _erro_relativo(upside_py, upside_js) <= TAU, \
            f"{fixture}/{nome}: py={upside_py} js={upside_js}"
        # A razão sem o `-1` (o erro de sinal/base mais provável) é outro
        # número: se fossem iguais, este teste não discriminaria nada.
        razao = cenario_py["valor"]["preco_acao"] / preco_de_tela
        assert _erro_relativo(razao, upside_js) > TAU, \
            f"{fixture}/{nome}: upside indistinguível da razão preço/tela"


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_o_comparador_tambem_prende_o_upside_do_cenario(tmp_path):
    """O upside é o TERCEIRO número que a fachada passa a publicar, e o badge
    o compara como compara os outros dois: adultera só `vs_preco.upside` no
    `resultados` e exige a divergência nomeada por aquela chave — o preço e o
    múltiplo continuam batendo, então o comparador não reprova em bloco."""
    caso, resultados = _caso_e_resultados("caso_minimo_firm.json")
    verdadeiro = resultados["cenarios"]["base"]["vs_preco"]["upside"]
    resultados["cenarios"]["base"]["vs_preco"]["upside"] = verdadeiro + 0.25

    saida = _fachada(caso, resultados, tmp_path)
    comparacao = saida["comparacao"]
    assert comparacao["ok"] is False
    assert [d["chave"] for d in comparacao["divergencias"]] == ["vs_preco.upside"], \
        comparacao["divergencias"]
    d = comparacao["divergencias"][0]
    assert d["cenario"] == "base"
    assert d["python"] == pytest.approx(verdadeiro + 0.25, rel=1e-12)
    assert _erro_relativo(verdadeiro, d["js"]) <= TAU


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_as_rotas_que_a_fachada_trata_sao_exatamente_as_do_gate(tmp_path):
    """Achado 5 da Task 1, fechado: até aqui, uma rota NOVA em `avaliar.py`
    que a fachada não espelhasse só apareceria em runtime — a fachada falha
    fechada (`rota_desconhecida`), o que está certo, mas nada REPROVAVA a
    ausência.

    Mesma trava de upgrade que o catálogo já usa
    (`test_catalogo_apresentacao.py::test_premissas_do_catalogo_sao_
    exatamente_as_do_gate`): o conjunto de rotas que a fachada atende é
    exatamente o que o gate aceita (`caso._PREMISSAS_POR_ROTA`). Uma rota
    nova na integração passa a reprovar na INTEGRAÇÃO — onde a diretriz de
    upgrade manda o custo cair —, nunca no relatório nem no browser do
    analista.

    `ROTAS_ATENDIDAS` não é uma lista paralela: é derivada do mesmo objeto
    que `chaveDoMultiplo` consulta para decidir se sabe tratar a rota, então
    não pode divergir do comportamento real por esquecimento."""
    caso, resultados = _caso_e_resultados("caso_minimo_firm.json")
    saida = _fachada(caso, resultados, tmp_path)
    assert saida["rotas"], "fachada não expõe ROTAS_ATENDIDAS — trava vacuamente verde"
    assert set(saida["rotas"]) == set(_PREMISSAS_POR_ROTA)


# ---------------------------------------------------------------------------
# As duas recusas: contrato desconhecido e divergência numérica
# ---------------------------------------------------------------------------

@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_a_fachada_recusa_um_resultados_de_contrato_desconhecido(tmp_path):
    """L2, a lição do F7 da 5B: um contrato que a fachada não sabe ler
    REPROVA em voz alta — exceção nomeada, citando as duas versões — em vez
    de desenhar número errado em silêncio. É o que a v10 vai encontrar."""
    caso, resultados = _caso_e_resultados("caso_minimo_firm.json")
    resultados["versao_contrato"] = "resultados/2"
    saida = _fachada(caso, resultados, tmp_path)

    assert saida["versao_contrato"] == "resultados/1"
    assert "comparacao" not in saida, "comparou um contrato que não sabe ler"
    erro = saida["erro"]
    assert erro["codigo"] == "contrato_desconhecido", erro
    assert "resultados/1" in erro["mensagem"] and "resultados/2" in erro["mensagem"], erro


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_o_comparador_nomeia_cenario_chave_e_os_dois_numeros(tmp_path):
    """L4: vermelho é um fato utilizável — nomeia o cenário, a chave e os
    dois números. Adultera o preço de UM cenário só, num caso de dois, e
    exige que a divergência apontada seja exatamente aquela (o outro
    cenário continua batendo, então o comparador não está reprovando em
    bloco)."""
    def _dois_cenarios(caso: dict) -> None:
        caso["cenarios"]["otimista"] = json.loads(json.dumps(caso["cenarios"]["base"]))
        caso["cenarios"]["otimista"]["premissas"]["g"] = 7.0
        caso["cenario_base"] = "base"

    entrega = montar_entrega("caso_minimo_firm.json", mutar_caso=_dois_cenarios)
    caso, resultados = entrega["caso"], entrega["resultados"]

    preco_verdadeiro = resultados["cenarios"]["otimista"]["valor"]["preco_acao"]
    adulterado = preco_verdadeiro + 1.0
    resultados["cenarios"]["otimista"]["valor"]["preco_acao"] = adulterado

    saida = _fachada(caso, resultados, tmp_path)
    comparacao = saida["comparacao"]
    assert comparacao["ok"] is False
    assert len(comparacao["divergencias"]) == 1, comparacao["divergencias"]
    d = comparacao["divergencias"][0]
    assert d["cenario"] == "otimista"
    assert d["chave"] == "valor.preco_acao"
    assert d["python"] == pytest.approx(adulterado, rel=1e-12)
    assert _erro_relativo(preco_verdadeiro, d["js"]) <= TAU
    assert d["erro_relativo"] > TAU


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_o_comparador_tambem_prende_o_multiplo_do_cenario(tmp_path):
    """O preço e o múltiplo são DOIS números publicados — um comparador que
    só olhasse o preço passaria por todos os testes acima. Adultera só o
    múltiplo de referência e exige a divergência nomeada por aquela chave."""
    caso, resultados = _caso_e_resultados("caso_minimo_firm.json")
    verdadeiro = resultados["cenarios"]["base"]["multiplos"]["EV/EBITDA_curr"]
    resultados["cenarios"]["base"]["multiplos"]["EV/EBITDA_curr"] = verdadeiro + 0.5

    saida = _fachada(caso, resultados, tmp_path)
    comparacao = saida["comparacao"]
    assert comparacao["ok"] is False
    assert [d["chave"] for d in comparacao["divergencias"]] == ["EV/EBITDA_curr"], \
        comparacao["divergencias"]
    d = comparacao["divergencias"][0]
    assert d["cenario"] == "base"
    assert d["python"] == pytest.approx(verdadeiro + 0.5, rel=1e-12)
    assert _erro_relativo(verdadeiro, d["js"]) <= TAU


# ---------------------------------------------------------------------------
# Onde a fachada de fato roda: um <script> de browser
# ---------------------------------------------------------------------------

@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_a_fachada_roda_em_contexto_de_browser_sem_module_nem_require(tmp_path):
    """O consumidor real é um `<script>` dentro do HTML: sem `module`, sem
    `require`, sem `process`. É o FIX 1 da revisão final da 4A repetido —
    uma fachada que só funcionasse sob `require` teria harness verde e
    laboratório morto. Carrega os FONTES (espelho e fachada, nesta ordem)
    num `vm.createContext({})` vazio e exige que `globalThis.FachadaEspelho`
    reproduza o preço por esse caminho."""
    caso, resultados = _caso_e_resultados("caso_minimo_firm.json")
    arq = tmp_path / "payload.json"
    arq.write_text(json.dumps({"caso": caso, "resultados": resultados}, ensure_ascii=False),
                   encoding="utf-8")
    script = (
        "const fs = require('fs');"
        "const vm = require('vm');"
        "const ctx = vm.createContext({});"
        "vm.runInContext(fs.readFileSync(%s, 'utf8'), ctx);"
        "vm.runInContext(fs.readFileSync(%s, 'utf8'), ctx);"
        "const p = JSON.parse(fs.readFileSync(%s, 'utf-8'));"
        "const F = ctx.FachadaEspelho;"
        "const ok = !!(F && typeof F.avaliarCaso === 'function'"
        " && typeof F.compararComResultados === 'function');"
        "ctx.__p = p;"
        "const r = ok ? vm.runInContext("
        "  'JSON.stringify({vivo: FachadaEspelho.avaliarCaso(__p.caso),"
        "   comparacao: FachadaEspelho.compararComResultados(__p.caso, __p.resultados)})', ctx)"
        "  : 'null';"
        "console.log(JSON.stringify({ok, r}));"
    ) % (json.dumps(str(ESPELHO)), json.dumps(str(FACHADA)), json.dumps(str(arq)))
    r = subprocess.run(["node", "-e", script],
                       capture_output=True, text=True, encoding="utf-8", timeout=120)
    assert r.returncode == 0, r.stdout + r.stderr
    d = json.loads(r.stdout)
    assert d["ok"], "superfície pública (globalThis.FachadaEspelho) inalcançável no contexto vm"
    saida = json.loads(d["r"])
    assert saida["comparacao"]["ok"] is True, saida["comparacao"]["divergencias"]
    assert _erro_relativo(resultados["cenarios"]["base"]["valor"]["preco_acao"],
                          saida["vivo"]["cenarios"]["base"]["valor"]["preco_acao"]) <= TAU


def test_a_fachada_nao_tem_dependencia_externa():
    """Zero npm, como o espelho: a fachada vai ser embutida num HTML
    autocontido, sem rede. O único `require` admitido é o do espelho irmão,
    no ramo de node — no browser os dois chegam como `<script>` e a fachada
    acha o espelho por `globalThis`."""
    texto = FACHADA.read_text(encoding="utf-8")
    assert not re.search(r"^\s*import\s", texto, re.M), "import ES6 na fachada"
    requires = re.findall(r"""require\(\s*['"]([^'"]+)['"]\s*\)""", texto)
    assert set(requires) <= {"./motor_espelho.js"}, \
        f"dependência além do espelho irmão: {sorted(set(requires))}"


# ---------------------------------------------------------------------------
# Fatia 5C, Task 3 — o diagnóstico ao vivo (§8.4 do desenho, regra
# inegociável: o diagnóstico se move junto com o número)
# ---------------------------------------------------------------------------

# Várias avaliações NO MESMO PROCESSO, como o laboratório faz a cada edição: a
# mesma instância da fachada recebe a carga, a edição e o desfazer. Um harness
# que abrisse um processo por chamada não enxergaria uma fachada que guardasse
# (congelasse) o que respondeu da primeira vez.
_HARNESS_SEQUENCIA = (
    "const fs = require('fs');"
    "const F = require(%s);"
    "const casos = JSON.parse(fs.readFileSync(%s, 'utf-8'));"
    "console.log(JSON.stringify(casos.map((caso) => F.avaliarCaso(caso))));"
)


def _avaliar_em_sequencia(casos: list, tmp_path) -> list:
    arq = tmp_path / "sequencia.json"
    arq.write_text(json.dumps(casos, ensure_ascii=False), encoding="utf-8")
    script = _HARNESS_SEQUENCIA % (json.dumps(str(FACHADA)), json.dumps(str(arq)))
    r = subprocess.run(["node", "-e", script],
                       capture_output=True, text=True, encoding="utf-8", timeout=120)
    assert r.returncode == 0, r.stdout + r.stderr
    return json.loads(r.stdout)


def _lista(cenario: dict, caminho: tuple, lado: str) -> list:
    """A lista de chaves em `caminho` dentro de um cenário (vivo ou publicado)
    — e a exigência de que ela EXISTA como lista: ausência nunca vale como
    lista vazia."""
    atual = cenario
    for parte in caminho:
        assert isinstance(atual, dict) and parte in atual, f"{lado}: sem '{'.'.join(caminho)}'"
        atual = atual[parte]
    assert isinstance(atual, list), f"{lado}: '{'.'.join(caminho)}' não é lista: {atual!r}"
    return atual


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
@pytest.mark.parametrize("fixture", FIXTURES_DE_CASO + VARIANTES_COM_CONSERVACAO)
def test_as_chaves_de_diagnostico_da_fachada_sao_as_do_resultados_em_ordem(fixture, tmp_path):
    """Carga (T3): para toda fixture, as chaves que a fachada devolve são
    exatamente as que o wrapper publicou, na mesma ordem e no mesmo lugar —
    `cenarios.<n>.diagnosticos_chaves` em toda perna, e
    `cenarios.<n>.degrau.diagnosticos_chaves` só nos cenários com degrau (a
    fachada não inventa um bloco `degrau` onde o `resultados` não tem)."""
    caso, resultados = _caso_e_resultados(fixture)
    saida = _fachada(caso, resultados, tmp_path)
    assert "erro" not in saida, saida.get("erro")

    for nome, cenario_py in resultados["cenarios"].items():
        cenario_js = saida["vivo"]["cenarios"][nome]
        caminho = ("diagnosticos_chaves",)
        assert _lista(cenario_js, caminho, "fachada") == _lista(cenario_py, caminho, "wrapper"), \
            f"{fixture}/{nome}"
        if "degrau" in cenario_py:
            caminho = ("degrau", "diagnosticos_chaves")
            assert _lista(cenario_js, caminho, "fachada") == _lista(cenario_py, caminho, "wrapper"), \
                f"{fixture}/{nome}"
        else:
            assert "degrau" not in cenario_js, f"{fixture}/{nome}: {cenario_js.get('degrau')}"
        if "conservacao_capital" in cenario_py:
            caminho = ("conservacao_capital", "diagnosticos_chaves")
            assert _lista(cenario_js, caminho, "fachada") == _lista(cenario_py, caminho, "wrapper"), \
                f"{fixture}/{nome}"
        else:
            assert "conservacao_capital" not in cenario_js, f"{fixture}/{nome}"
        # F2: um cenário precificado declara que NÃO foi recusado — o campo existe e é `null`.
        assert cenario_js["recusa"] is None, f"{fixture}/{nome}: {cenario_js['recusa']}"


# Uma edição por FORMA em que o wrapper publica diagnóstico, escolhida lendo o
# predicado do espelho — não por tentativa — e confirmada rodando o wrapper (o
# teste compara com o `resultados` que `avaliar()` publica para o caso
# editado, então o nome da chave nunca é presumido):
#
# - firm (`diagnosticosFirm`): `roic < w && g > 0` acende
#   `firm_alerta_roic_abaixo_wacc`. `caso_minimo_firm`: g=5, wacc=10, roic=12;
#   roic=8 cruza. Nenhum outro predicado cruza junto: RiR = 5/8 = 62,5% < 100%,
#   e |roic − wacc| = 2 p.p. fica longe da faixa de neutralidade (0,05 p.p.).
# - rampa (`rampaBifasica`): `rir2 >= 1` acende `aviso_delator`, com
#   rir2 = (wk + kappa)·g2 / ((1 + g2)·m2n). Na fixture, wk + kappa = 37,04% e
#   a margem NOPAT da fase 2 é m2n ≈ 5,49%: rir2 ≈ 50% com g2 = 8%, e o limiar
#   cai em g2 ≈ 17,4%. g2 = 20 leva rir2 a ≈ 112%.
# - degrau (`nivelDegrau`): `r2 > max(2·ke, 30%)` acende o ALERTA do motor, que o
#   wrapper publica como `degrau_alerta`, com r2 = roe·(1 + (h − 1)·m). Na
#   fixture, h = 19,3/14 ≈ 1,3786, m = 100% e ke = 20% (limiar de 40%): cruza
#   com roe > ≈ 29,0%. roe = 30 leva r2 a ≈ 41,4%.
_EDICOES_QUE_CRUZAM_UM_PREDICADO = [
    pytest.param("caso_minimo_firm.json", "roic", 8.0, ("diagnosticos_chaves",),
                 "firm_alerta_roic_abaixo_wacc", id="firm"),
    pytest.param("caso_rampa.json", "g2", 20.0, ("diagnosticos_chaves",),
                 "aviso_delator", id="rampa"),
    pytest.param("caso_degrau.json", "roe", 30.0, ("degrau", "diagnosticos_chaves"),
                 "degrau_alerta", id="degrau"),
]


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
@pytest.mark.parametrize("fixture,premissa,editado,caminho,chave", _EDICOES_QUE_CRUZAM_UM_PREDICADO)
def test_o_diagnostico_se_move_com_o_numero_na_mesma_chamada(
        fixture, premissa, editado, caminho, chave, tmp_path):
    """§8.4, a regra inegociável, uma vez por forma: partindo de um cenário SEM
    o alerta, UMA edição que cruza o predicado acende a chave na MESMA chamada
    de `avaliarCaso` que move o preço — e desfazer a edição devolve a lista
    original. As três chamadas acontecem no mesmo processo, na ordem em que o
    laboratório as faria (carga, edição, desfazer).

    Os dois lados são o wrapper de verdade: a lista da carga é a que
    `avaliar()` publicou para o caso, e a da edição é a que ele publica para o
    caso EDITADO — mesma lista, mesma ordem. Discriminante nos dois sentidos:
    a edição acende exatamente a chave esperada sem apagar nenhuma outra
    daquela lista, e o preço se move na mesma chamada."""
    caso, resultados = _caso_e_resultados(fixture)
    original = caso["cenarios"]["base"]["premissas"][premissa]

    def _editar(c: dict) -> None:
        c["cenarios"]["base"]["premissas"][premissa] = editado

    editada = montar_entrega(fixture, mutar_caso=_editar)
    caso_editado, resultados_editados = editada["caso"], editada["resultados"]
    caso_desfeito = json.loads(json.dumps(caso_editado))
    caso_desfeito["cenarios"]["base"]["premissas"][premissa] = original

    carga, na_edicao, desfeito = [
        vivo["cenarios"]["base"]
        for vivo in _avaliar_em_sequencia([caso, caso_editado, caso_desfeito], tmp_path)]
    publicado = resultados["cenarios"]["base"]
    publicado_editado = resultados_editados["cenarios"]["base"]

    # Partida: o cenário publicado não tem o alerta, e a fachada concorda.
    assert chave not in _lista(publicado, caminho, "wrapper")
    assert _lista(carga, caminho, "fachada") == _lista(publicado, caminho, "wrapper")

    # A edição: o wrapper acende a chave (o nome é confirmado rodando), e a
    # fachada devolve a MESMA lista, na MESMA chamada que move o preço.
    antes = _lista(carga, caminho, "fachada")
    depois = _lista(na_edicao, caminho, "fachada")
    assert chave in _lista(publicado_editado, caminho, "wrapper")
    assert depois == _lista(publicado_editado, caminho, "wrapper")
    assert [c for c in depois if c not in antes] == [chave]
    assert [c for c in antes if c not in depois] == []
    assert na_edicao["diagnosticos_chaves"] == publicado_editado["diagnosticos_chaves"]
    assert _erro_relativo(publicado_editado["valor"]["preco_acao"],
                          na_edicao["valor"]["preco_acao"]) <= TAU
    assert _erro_relativo(carga["valor"]["preco_acao"], na_edicao["valor"]["preco_acao"]) > TAU, \
        "a edição não moveu o preço — o teste deixou de provar que número e diagnóstico andam juntos"

    # Desfazer: a lista original volta, exatamente, com o preço original.
    assert _lista(desfeito, caminho, "fachada") == antes
    assert desfeito["diagnosticos_chaves"] == carga["diagnosticos_chaves"]
    assert desfeito["valor"]["preco_acao"] == carga["valor"]["preco_acao"]


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_os_dois_alertas_do_degrau_saem_na_ordem_do_wrapper(tmp_path):
    """A ordem das chaves do degrau só é observável com os DOIS alertas acesos
    no mesmo cenário — e a fixture de paridade do degrau
    (`vetores_solver._bloco_degrau`) tem um problema para cada alerta, nenhum
    com os dois. Este caso cruza os dois predicados de uma vez
    (`r2 > max(2·ke, 30%)` e `g/r2 > 1`): roe=22 e ke=14 levam r2 a ≈ 30,3%,
    acima do piso de 30%, e g=31 fica acima de r2. O wrapper publica as duas
    chaves, e a fachada tem de devolvê-las na MESMA ordem. (A lista pode trazer
    também a chave da divergência de base, depois dos alertas — F1 da onda de
    correção; o que este teste prende é a ordem dos dois alertas entre si.)"""
    def _dois_alertas(caso: dict) -> None:
        caso["cenarios"]["base"]["premissas"].update(roe=22.0, ke=14.0, g=31.0)

    entrega = montar_entrega("caso_degrau.json", mutar_caso=_dois_alertas)
    caso, resultados = entrega["caso"], entrega["resultados"]
    caminho = ("degrau", "diagnosticos_chaves")
    publicadas = _lista(resultados["cenarios"]["base"], caminho, "wrapper")
    alertas = [chave for _campo, chave in _ALERTAS_DEGRAU_ORDEM]
    assert [chave for chave in publicadas if chave in alertas] == alertas, publicadas

    saida = _fachada(caso, resultados, tmp_path)
    assert "erro" not in saida, saida.get("erro")
    assert _lista(saida["vivo"]["cenarios"]["base"], caminho, "fachada") == publicadas
    assert saida["comparacao"]["ok"] is True, saida["comparacao"]["divergencias"]


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
@pytest.mark.parametrize("fixture,caminho,adulterar", [
    # A mesma lista em ordem invertida: só um comparador ORDENADO acusa.
    pytest.param("caso_minimo_firm.json", ("diagnosticos_chaves",),
                 lambda chaves: list(reversed(chaves)), id="cenario-ordem"),
    # Uma chave a mais no bloco do degrau (na fixture, a lista só traz a divergência de base).
    pytest.param("caso_degrau.json", ("degrau", "diagnosticos_chaves"),
                 lambda chaves: chaves + ["degrau_alerta"], id="degrau-presenca"),
    # A chave da conservação de capital apagada da lista publicada (fatia 5F, Task 3).
    pytest.param("conservacao_nao_fecha", ("conservacao_capital", "diagnosticos_chaves"),
                 lambda chaves: [], id="conservacao-presenca"),
])
def test_o_comparador_prende_as_chaves_de_diagnostico_por_igualdade_ordenada(
        fixture, caminho, adulterar, tmp_path):
    """T4: o badge cobre as chaves — igualdade EXATA e ORDENADA, nos dois
    lugares em que o contrato as publica. Adultera só a lista no `resultados`
    e exige UMA divergência, nomeando o cenário, o caminho e as DUAS listas
    inteiras (a publicada, adulterada, e a recalculada). Preço, múltiplo e
    upside continuam batendo, então o comparador não reprova em bloco."""
    caso, resultados = _caso_e_resultados(fixture)
    no = resultados["cenarios"]["base"]
    for parte in caminho[:-1]:
        no = no[parte]
    verdadeiras = list(_lista(resultados["cenarios"]["base"], caminho, "wrapper"))
    adulteradas = adulterar(list(verdadeiras))
    assert adulteradas != verdadeiras, "a adulteração não mudou a lista — teste vacuamente verde"
    no[caminho[-1]] = adulteradas

    saida = _fachada(caso, resultados, tmp_path)
    comparacao = saida["comparacao"]
    assert comparacao["ok"] is False
    assert comparacao["divergencias"] == [{
        "cenario": "base", "chave": ".".join(caminho),
        "python": adulteradas, "js": verdadeiras, "erro_relativo": None,
    }]


# ---------------------------------------------------------------------------
# Onda de correção da revisão final da 5C — F4 (a lista exibível) e F1 (a
# divergência de base do degrau como chave da integração)
# ---------------------------------------------------------------------------

def _subsequencia(curta: list, longa: list) -> bool:
    """`curta` aparece dentro de `longa` na mesma ordem (não necessariamente
    contígua)."""
    restante = iter(longa)
    return all(any(item == candidato for candidato in restante) for item in curta)


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
@pytest.mark.parametrize("fixture", FIXTURES_DE_CASO + VARIANTES_COM_CONSERVACAO)
def test_a_lista_exibida_contem_toda_lista_de_chaves_do_cenario_em_ordem(fixture, tmp_path):
    """F4 (MÉDIO, E3). O laboratório pinta UMA lista, `diagnosticos_exibidos`,
    que a fachada monta por cenário — e deixa de conhecer caminho de contrato.
    A trava que faltava mora aqui, na integração: as listas `diagnosticos_chaves`
    do cenário publicado são DERIVADAS descendo pelo cenário
    (`relatorio_apoio.listas_de_chaves_de_diagnostico`), sem nomear onde moram,
    e a lista exibida tem de conter cada uma, na ordem dela, e nada além delas.

    É o que faz uma forma aditiva de uma v10 (a sonda P6 da revisão:
    `cenarios.<n>.transicao.diagnosticos_chaves`, ainda `resultados/1`) reprovar
    AQUI quando a fachada a esquece — antes, o badge ficava verde, a tela não a
    mostrava e nada reprovava. A ordem ENTRE listas é escolha de apresentação da
    fachada; a ordem DENTRO de cada lista é a do motor e do wrapper, e é presa."""
    caso, resultados = _caso_e_resultados(fixture)
    saida = _fachada(caso, resultados, tmp_path)
    assert "erro" not in saida, saida.get("erro")

    for nome, cenario_py in resultados["cenarios"].items():
        listas = list(listas_de_chaves_de_diagnostico(cenario_py))
        assert listas, f"{fixture}/{nome}: cenário publicado sem lista de chaves — trava vacuamente verde"
        exibida = saida["vivo"]["cenarios"][nome].get("diagnosticos_exibidos")
        assert isinstance(exibida, list), f"{fixture}/{nome}: sem 'diagnosticos_exibidos': {exibida!r}"
        for caminho, lista in listas:
            assert _subsequencia(lista, exibida), (
                f"{fixture}/{nome}: '{'.'.join(map(str, caminho))}' = {lista} fora da lista exibida "
                f"{exibida}, ou fora de ordem")
        publicadas = Counter(chave for _caminho, lista in listas for chave in lista)
        assert Counter(exibida) == publicadas, \
            f"{fixture}/{nome}: exibida {exibida} x publicadas {dict(publicadas)}"


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_a_divergencia_de_base_do_degrau_acende_e_apaga_com_o_preco_na_mesma_chamada(tmp_path):
    """F1 (ALTO), a regra inegociável do §8.4 aplicada ao degrau. Antes, a
    fachada descartava `divergencia_de_base_%` e o limiar vivia na QC do build:
    com ROE 25 a tela mostrava R$ 64,30 e o disclosure seguia congelado em
    16,4%. Agora a integração decide "acima do limiar" e publica a chave em
    `degrau.diagnosticos_chaves`, do mesmo jeito no wrapper e na fachada.

    Quatro chamadas no MESMO processo (carga, ROE 17,2, ROE 25, desfazer), cada
    uma conferida contra o que `avaliar()` publica para o caso editado:
    - carga (ROE 20): 16,4% — a chave está lá;
    - ROE 17,2: 0,16% — a chave some na chamada em que o preço anda;
    - ROE 25: 45,5% e nenhum alerta do degrau (r2 ≈ 34,5% < 40%) — o caso da
      revisão em que a tela não dizia nada: a chave é o único diagnóstico do
      degrau, e chega à lista exibida;
    - desfazer: a lista e o preço da carga voltam."""
    fixture = "caso_degrau.json"
    caso, resultados = _caso_e_resultados(fixture)
    caminho = ("degrau", "diagnosticos_chaves")
    chave = _CHAVE_DIVERGENCIA_DE_BASE

    def _roe(valor: float):
        def _mutar(c: dict) -> None:
            c["cenarios"]["base"]["premissas"]["roe"] = valor
        return _mutar

    editadas = {roe: montar_entrega(fixture, mutar_caso=_roe(roe)) for roe in (17.2, 25.0)}
    carga, em_17, em_25, desfeito = [
        vivo["cenarios"]["base"] for vivo in _avaliar_em_sequencia(
            [caso, editadas[17.2]["caso"], editadas[25.0]["caso"], caso], tmp_path)]
    publicado = resultados["cenarios"]["base"]
    p17 = editadas[17.2]["resultados"]["cenarios"]["base"]
    p25 = editadas[25.0]["resultados"]["cenarios"]["base"]

    assert abs(publicado["degrau"]["divergencia_de_base_%"]) > _LIMIAR_DIVERGENCIA_DE_BASE_PCT
    assert chave in _lista(publicado, caminho, "wrapper")
    assert _lista(carga, caminho, "fachada") == _lista(publicado, caminho, "wrapper")

    assert abs(p17["degrau"]["divergencia_de_base_%"]) <= _LIMIAR_DIVERGENCIA_DE_BASE_PCT
    assert chave not in _lista(p17, caminho, "wrapper")
    assert _lista(em_17, caminho, "fachada") == _lista(p17, caminho, "wrapper")
    assert chave not in em_17["diagnosticos_exibidos"]
    assert _erro_relativo(p17["valor"]["preco_acao"], em_17["valor"]["preco_acao"]) <= TAU
    assert _erro_relativo(carga["valor"]["preco_acao"], em_17["valor"]["preco_acao"]) > TAU, \
        "a edição não moveu o preço — o teste deixou de provar que número e diagnóstico andam juntos"

    assert _lista(p25, caminho, "wrapper") == [chave]
    assert _lista(em_25, caminho, "fachada") == [chave]
    assert chave in em_25["diagnosticos_exibidos"]
    assert _erro_relativo(p25["valor"]["preco_acao"], em_25["valor"]["preco_acao"]) <= TAU

    assert _lista(desfeito, caminho, "fachada") == _lista(carga, caminho, "fachada")
    assert desfeito["valor"]["preco_acao"] == carga["valor"]["preco_acao"]


# ---------------------------------------------------------------------------
# Onda de correção da revisão final da 5C — F2 (recusa nomeada, listas `null`)
# e F3 (a D6 do gate aplicada ao caso editado)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_os_motivos_de_recusa_da_fachada_sao_exatamente_os_do_catalogo(tmp_path):
    """F2: todo motivo que a fachada pode publicar tem rótulo no catálogo, e o
    catálogo não rotula motivo que a fachada não publica — a mesma trava de
    upgrade das rotas e das chaves de diagnóstico. Um motivo novo na fachada
    sem rótulo reprova AQUI, na integração, e nunca chega à tela como código
    cru."""
    caso, resultados = _caso_e_resultados("caso_minimo_firm.json")
    saida = _fachada(caso, resultados, tmp_path)
    assert saida["motivos"], "fachada não expõe MOTIVOS_DE_RECUSA — trava vacuamente verde"
    assert len(saida["motivos"]) == len(set(saida["motivos"])), saida["motivos"]
    assert set(saida["motivos"]) == set(CATALOGO["recusas"])


# Uma edição por motivo e por perna, cada uma alcançável com UM campo do painel.
# O motivo de cada linha é CONFERIDO contra o motor de verdade, nunca presumido:
# `avaliar()` sobre o caso editado levanta `MotorFalhou`, e a mensagem diz se o
# motor saiu com código 2 (a CLI recusou antes de calcular: argparse com `--n`/
# `--t-rampa` inteiros, ou `avaliar_dominios_cli`) ou se o núcleo não fechou um
# número (`null` serializado, ou erro do próprio núcleo — a composição da rampa
# sem fase 2 sai com código 1).
_RECUSAS_POR_EDICAO = [
    pytest.param("caso_minimo_firm.json", {"gp": 10.0}, "nucleo_nao_finito", id="firm-gp-igual-ao-wacc"),
    pytest.param("caso_minimo_firm.json", {"n": 10.5}, "dominio_da_cli", id="firm-n-fracionario"),
    pytest.param("caso_minimo_equity.json", {"tv": "gordon"}, "nucleo_nao_finito",
                 id="equity-gordon-sem-roe-tv"),
    pytest.param("caso_minimo_equity.json", {"ke": -150.0}, "dominio_da_cli", id="equity-ke-abaixo-de-menos-100"),
    pytest.param("caso_rampa.json", {"t_rampa": 2.5}, "dominio_da_cli", id="rampa-t-rampa-fracionario"),
    pytest.param("caso_rampa.json", {"t_rampa": 10}, "nucleo_nao_finito", id="rampa-sem-fase-2"),
    pytest.param("caso_degrau.json", {"gp": 20.0}, "nucleo_nao_finito", id="degrau-gp-igual-ao-ke"),
    pytest.param("caso_degrau.json", {"n": 10.5}, "dominio_da_cli", id="degrau-n-fracionario"),
]


def _motivo_segundo_o_motor(caso: dict) -> str:
    try:
        avaliar(caso)
    except MotorFalhou as erro:
        return "dominio_da_cli" if "saiu com código 2" in str(erro) else "nucleo_nao_finito"
    raise AssertionError("o motor precificou o caso editado — a edição deixou de ser uma recusa")


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
@pytest.mark.parametrize("fixture,edicao,motivo", _RECUSAS_POR_EDICAO)
def test_um_cenario_recusado_publica_null_e_o_motivo_que_o_motor_confirma(fixture, edicao, motivo, tmp_path):
    """F2 (MÉDIO). Antes, um cenário recusado publicava `[]` nas listas e a
    tela dizia "Nenhum diagnóstico disparado por estas premissas." — com
    `gp = 10` sob gordon, o motor emite quatro. Agora a fachada publica `null`
    em toda lista do cenário (e na exibível) e o motivo como código nomeado,
    o mesmo que o motor de verdade confirma para o caso editado, nas três
    rotas e no degrau."""
    caso, resultados = _caso_e_resultados(fixture)
    caso["cenarios"]["base"]["premissas"].update(edicao)
    assert _motivo_segundo_o_motor(json.loads(json.dumps(caso))) == motivo

    cenario = _avaliar_em_sequencia([caso], tmp_path)[0]["cenarios"]["base"]
    assert cenario["valor"]["preco_acao"] is None, cenario
    assert cenario["recusa"] == {"codigo": motivo}, cenario
    assert cenario["diagnosticos_chaves"] is None, cenario
    assert cenario["diagnosticos_exibidos"] is None, cenario
    if "degrau" in resultados["cenarios"]["base"]:
        assert cenario["degrau"]["diagnosticos_chaves"] is None, cenario


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_a_fachada_recusa_pela_d6_se_e_so_se_o_gate_recusa_o_caso_editado(tmp_path):
    """F3 (MÉDIO). O `select` da convenção terminal levava o degrau à
    combinação que o gate recusa por nome (D6: `tv` canônico 'book' sem
    `roe_book` — a conflação agravada pelo degrau), e a tela a mostrava como
    cenário: R$ 42,56 com badge verde. O relatório não reimplementa o gate; a
    FACHADA aplica a D6 ao caso editado e recusa com código nomeado. A revisão
    varreu as regras de cenário e só a D6 é alcançável pelos campos do painel.

    A trava: para cada fixture com degrau, cada cenário, cada grafia de `tv`
    (as opções do catálogo e os aliases que o gate canoniza) e `roe_book`
    ausente ou declarado, a fachada recusa pela D6 SE E SÓ SE `caso.validar`
    recusa o caso editado — e, quando o gate aceita, a fachada precifica."""
    com_degrau = [f for f in FIXTURES_DE_CASO
                  if "degrau" in json.loads((FIXTURES / f).read_text(encoding="utf-8"))]
    assert com_degrau, "nenhuma fixture com degrau — trava vacuamente verde"
    grafias_de_tv = sorted(set(CATALOGO["premissas"]["equity"]["tv"]["opcoes"]) | set(TV_CANON))

    variantes = []
    for fixture in com_degrau:
        base = carregar(FIXTURES / fixture)
        for nome in base["cenarios"]:
            for roe_book in (None, 18.0):
                for tv in grafias_de_tv:
                    caso = json.loads(json.dumps(base))
                    premissas = caso["cenarios"][nome]["premissas"]
                    premissas["tv"] = tv
                    premissas.pop("roe_book", None)
                    if roe_book is not None:
                        premissas["roe_book"] = roe_book
                    try:
                        validar(json.loads(json.dumps(caso)))
                        gate = None
                    except CasoInvalido as erro:
                        gate = str(erro)
                    variantes.append((f"{fixture}/{nome}/tv={tv}/roe_book={roe_book}", nome, caso, gate))

    vivos = _avaliar_em_sequencia([caso for _rotulo, _nome, caso, _gate in variantes], tmp_path)
    recusadas = 0
    for (rotulo, nome, _caso, gate), vivo in zip(variantes, vivos):
        cenario = vivo["cenarios"][nome]
        if gate is None:
            assert cenario["recusa"] is None, (rotulo, cenario["recusa"])
            assert cenario["valor"]["preco_acao"] is not None, rotulo
        else:
            assert "D6" in gate, (rotulo, gate)
            assert cenario["recusa"] == {"codigo": "degrau_book_sem_roe_book"}, (rotulo, cenario["recusa"])
            assert cenario["valor"]["preco_acao"] is None, rotulo
            assert cenario["diagnosticos_exibidos"] is None, rotulo
            recusadas += 1
    assert 0 < recusadas < len(variantes), f"a varredura não exercita os dois lados da D6: {recusadas}"


# ---------------------------------------------------------------------------
# Fatia 5F, Task 3 (D6; §8.4): a conservação de capital anda com o número
# ---------------------------------------------------------------------------

@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_a_conservacao_de_capital_acende_e_apaga_com_o_preco_na_mesma_chamada(tmp_path):
    """A regra inegociável do §8.4 aplicada à conservação de capital, que depende de premissas
    editáveis (`da`, `tax`, `g`, `roic`). `conservacao_fecha`: encargos de 450 contra capex 430 + ΔWC
    20, gap zero, sem a chave. `da` 30 leva os encargos a ≈ 518,75 — gap de ≈ −15,3%, acima do limiar
    do motor — e a chave acende na chamada em que o preço anda; desfazer a apaga. Três chamadas no
    mesmo processo, cada uma conferida contra o que `avaliar()` publica para o caso."""
    variante = "conservacao_fecha"
    caso, resultados = _caso_e_resultados(variante)
    caminho = ("conservacao_capital", "diagnosticos_chaves")
    (chave,) = _CHAVES_DA_CONSERVACAO

    def _editar(c: dict) -> None:
        _compor(variante)(c)
        c["cenarios"]["base"]["premissas"]["da"] = 30.0

    editada = montar_entrega(VARIANTES_DO_CASO[variante][0], mutar_caso=_editar)
    carga, na_edicao, desfeito = [
        vivo["cenarios"]["base"]
        for vivo in _avaliar_em_sequencia([caso, editada["caso"], caso], tmp_path)]
    publicado = resultados["cenarios"]["base"]
    publicado_editado = editada["resultados"]["cenarios"]["base"]

    assert _lista(publicado, caminho, "wrapper") == [] == _lista(carga, caminho, "fachada")
    assert chave not in carga["diagnosticos_exibidos"]

    assert _lista(publicado_editado, caminho, "wrapper") == [chave]
    assert _lista(na_edicao, caminho, "fachada") == [chave]
    assert chave in na_edicao["diagnosticos_exibidos"]
    assert _erro_relativo(publicado_editado["valor"]["preco_acao"], na_edicao["valor"]["preco_acao"]) <= TAU
    assert _erro_relativo(carga["valor"]["preco_acao"], na_edicao["valor"]["preco_acao"]) > TAU, \
        "a edição não moveu o preço — o teste deixou de provar que número e diagnóstico andam juntos"

    assert _lista(desfeito, caminho, "fachada") == []
    assert desfeito["valor"]["preco_acao"] == carga["valor"]["preco_acao"]


# ---------------------------------------------------------------------------
# Fatia 5I, Task 1 — a REVERSA ao vivo na fachada (D1/D4/D5/D12)
# ---------------------------------------------------------------------------

FIXTURE_DE_REVERSA = "caso_reversa_firm.json"


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_a_reversa_viva_reproduz_o_que_o_python_publicou(tmp_path):
    """D1: a fachada publica `reversa.{alvo, eixos.<eixo>.{leitura, resolucao},
    limitacoes}` nas MESMAS chaves do `resultados.json`, e o comparador as cobre.

    O que este teste prende, além da igualdade: que o badge fica VERDE no caso
    NÃO editado. É a condição que a decisão D4 protege — um comparador que
    incluísse a curvatura pintaria vermelho aqui um dia, num caso legítimo, e
    badge vermelho trava o laboratório inteiro."""
    caso, resultados = _caso_e_resultados(FIXTURE_DE_REVERSA)
    saida = _fachada(caso, resultados, tmp_path)
    assert "erro" not in saida, saida.get("erro")

    viva = saida["vivo"]["reversa"]
    assert set(viva) == {"alvo", "eixos", "limitacoes"}, viva.keys()
    assert set(viva["eixos"]) == set(caso["reversa"]["eixos"])
    assert _erro_relativo(resultados["reversa"]["alvo"]["valor"], viva["alvo"]) <= TAU

    for nome, eixo in viva["eixos"].items():
        publicado = resultados["reversa"]["eixos"][nome]
        assert eixo["resolucao"] == publicado["resolucao"], nome
        assert eixo["leitura"]["motivo"] == publicado["leitura"]["motivo"], nome
        assert eixo["leitura"]["premissa"] == publicado["leitura"]["premissa"], nome
        assert eixo["leitura"]["cap_anos"] == publicado["leitura"]["cap_anos"], nome
        vivas = eixo["leitura"]["raizes"]
        pubs = publicado["leitura"]["raizes"]
        assert len(vivas) == len(pubs), nome
        for viva_raiz, pub_raiz in zip(vivas, pubs):
            assert viva_raiz["valor"] == pub_raiz["valor"], nome
            assert viva_raiz["intervalo"] == pub_raiz["intervalo"], nome
            assert viva_raiz["identificacao"] == pub_raiz["identificacao"], nome
            # D4: a curvatura sai do COMPARADOR, não da TELA — publicada dos dois
            # lados, e nunca `null` onde o Python publicou número.
            assert ("curvatura" in viva_raiz) and (viva_raiz["curvatura"] is not None), nome

    assert saida["comparacao"]["ok"] is True, saida["comparacao"]["divergencias"]


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_o_comparador_prende_a_leitura_de_cada_eixo_da_reversa(tmp_path):
    """Adulterar a `leitura` publicada de um eixo tem de pintar vermelho, nomeando
    o eixo — senão a reversa estaria "no badge" só de nome."""
    caso, resultados = _caso_e_resultados(FIXTURE_DE_REVERSA)
    raiz = resultados["reversa"]["eixos"]["crescimento"]["leitura"]["raizes"][0]
    raiz["valor"] = raiz["valor"] + 1.0

    comparacao = _fachada(caso, resultados, tmp_path)["comparacao"]
    assert comparacao["ok"] is False
    divergencia = next(d for d in comparacao["divergencias"] if d["cenario"] == "crescimento")
    assert "raizes[0].valor" in divergencia["chave"], divergencia["chave"]


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_a_curvatura_sozinha_nao_pinta_o_badge_de_vermelho(tmp_path):
    """D4, medido: a curvatura divergente entre Python e JS é ULP amplificado por
    `/h**2`, não erro de espelho — e um badge vermelho num caso legítimo trava o
    laboratório. Uma curvatura DIFERENTE no `resultados` não pode reprovar; o
    mesmo desvio em qualquer campo vizinho (aqui, o intervalo) tem de reprovar."""
    caso, resultados = _caso_e_resultados(FIXTURE_DE_REVERSA)
    raiz = resultados["reversa"]["eixos"]["crescimento"]["leitura"]["raizes"][0]
    assert raiz["curvatura"] is not None, "a fixture não exercita a curvatura"
    raiz["curvatura"] = raiz["curvatura"] * 2 + 7.0
    assert _fachada(caso, resultados, tmp_path)["comparacao"]["ok"] is True

    caso2, resultados2 = _caso_e_resultados(FIXTURE_DE_REVERSA)
    vizinho = resultados2["reversa"]["eixos"]["crescimento"]["leitura"]["raizes"][0]
    vizinho["intervalo"] = [vizinho["intervalo"][0] + 1.0, vizinho["intervalo"][1]]
    assert _fachada(caso2, resultados2, tmp_path)["comparacao"]["ok"] is False


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_a_fachada_recusa_o_eixo_da_reversa_por_dominio_da_cli(tmp_path):
    """D5/A6: `dominioCliRecusa` nunca alcançava `resolverProblema` — um vetor
    editado com `gp = -150%` resolveria uma raiz onde o motor de verdade sai com
    código 2 sem calcular nada. Agora o eixo sai `resolveu: false` com motivo
    próprio e `leitura: null` — nunca uma raiz —, e o motor de verdade confirma a
    recusa (o padrão que a 4C já usa)."""
    caso, resultados = _caso_e_resultados(FIXTURE_DE_REVERSA)
    caso["cenarios"]["base"]["premissas"]["gp"] = -150.0

    assert _motivo_segundo_o_motor(caso) == "dominio_da_cli"

    saida = _fachada(caso, resultados, tmp_path)
    assert "erro" not in saida, saida.get("erro")
    eixos = saida["vivo"]["reversa"]["eixos"]
    assert set(eixos) == set(caso["reversa"]["eixos"])
    for nome, eixo in eixos.items():
        assert eixo["leitura"] is None, (nome, eixo)
        assert eixo["resolucao"]["resolveu"] is False, (nome, eixo)
        assert "domínio" in eixo["resolucao"]["motivo"], (nome, eixo)
    # A limitação não acende por recusa: sem cálculo não há "eixo primário sem
    # raiz" — o gatilho do Python é a `sugestao` que o motor nunca emitiu.
    assert saida["vivo"]["reversa"]["limitacoes"] == []


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_a_limitacao_da_leitura_acende_e_apaga_com_a_edicao_na_mesma_chamada(tmp_path):
    """D12: a curva iso continua desligada, mas a LIMITAÇÃO passa a ser viva — o
    gatilho é `_algum_eixo_primario_sem_raiz`, que roda sobre as raízes vivas.
    Um preço alto o bastante fecha os dois eixos primários; desfeita a edição, a
    limitação some na mesma sequência de chamadas (a regra do §8.4 aplicada à
    limitação: o diagnóstico anda junto com o número)."""
    caso, _ = _caso_e_resultados(FIXTURE_DE_REVERSA)
    caiu = json.loads(json.dumps(caso))
    caiu["preco"]["valor"] = 400.0

    original, editado = _avaliar_em_sequencia([caso, caiu], tmp_path)

    assert original["reversa"]["limitacoes"] == []
    assert original["reversa"]["eixos"]["rentabilidade"]["resolucao"]["resolveu"] is True
    assert "teto_do_crescimento_gratuito" not in original["reversa"]

    assert editado["reversa"]["limitacoes"] == ["iso_nao_calculada"]
    assert editado["reversa"]["eixos"]["rentabilidade"]["resolucao"]["resolveu"] is False
    assert editado["reversa"]["eixos"]["rentabilidade"]["leitura"]["motivo"] == "sem_raiz_na_faixa"
    # Mesmo gatilho, mesma chamada: o teto do crescimento gratuito aparece com a
    # limitação e some com ela.
    assert editado["reversa"]["teto_do_crescimento_gratuito"]["multiplo"] is not None
