"""A fixture sintética offline e o caso que deve falhar (item 6, Task 3; §13 do desenho).

Ver docs/superpowers/plans/2026-09-16-v4-item6-fixture-sintetica.md, D3. Uma companhia fictícia —
a Veltrana Sintética Celulose S.A., SINT3, com dados inventados e economicamente coerentes — em três
raízes de execução versionadas em `tests/fixtures/analises/SINT3/`. Cada raiz guarda só o que o
analista escreveria: o `caso.json` e as partes da entrega (a análise e o ledger). Nenhum
`resultados` congelado: o teste o compõe pelo motor de verdade (`avaliar()`), monta a raiz num
diretório temporário e roda o builder pela CLI, com a paridade por caso no build.

Item 8, Task 1 (D2): cada raiz guarda também a decisão do analista sobre os cinco gates, na parte
`execucao.json`; a suíte da metodologia não é escrita pelo analista — é rodada —, e o teste compõe o
registro dela com todo comando que o catálogo exige e código de saída 0 (a CI roda a suíte real).

1. `firm_escolha_driver`: rota firm com reversa, uma escolha metodológica que move o preço mais de
   dez por cento (a base do lucro normalizada ao spot da celulose) e um driver exógeno acima do
   limiar (o índice de celulose) — emite;
2. `sotp_capacidade`: soma das partes com um segmento na rota rampa (a máquina de papel-cartão, a
   capacidade pré-construída) e um na firm (a celulose de mercado) — emite;
3. `sem_proveniencia`: a raiz 1 sem o registro do ledger que sustenta a dívida bruta — o HARD FAIL
   `insumo_sem_proveniencia` testado como comportamento, e nada emitido.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
RAIZES = RAIZ / "tests" / "fixtures" / "analises" / "SINT3"
BUILDER = RAIZ / "skills" / "er-relatorio" / "scripts" / "builder.py"

sys.path.insert(0, str(RAIZ / "tests"))
import relatorio_apoio as apoio  # noqa: E402
from test_relatorio_tese import _aba, _secao, _secoes, _titulo, _todos, _um, _visivel  # noqa: E402

# `relatorio_apoio` já pôs as duas camadas no path: testes não são a camada do relatório.
import placeholders  # noqa: E402
from avaliar import avaliar  # noqa: E402
from caso import carregar as carregar_caso  # noqa: E402

LEGITIMAS = ("firm_escolha_driver", "sotp_capacidade")
QUE_DEVE_FALHAR = "sem_proveniencia"
# O que o analista escreve numa raiz; `dados.json` só quando algum exhibit lê um dataset. A parte da
# execução traz só os gates (item 8, D2): o id, o ticker, o idioma e a suíte o teste compõe.
PARTES_DA_RAIZ = {"caso.json", "analise.json", "ledger.json", "execucao.json"}
PARTE_OPCIONAL = "dados.json"

IDIOMA = "pt-BR"
ENV_UTF8 = {**os.environ, "PYTHONUTF8": "1", "PYTHONDONTWRITEBYTECODE": "1", "PYTHONIOENCODING": "utf-8"}
INTERFACE = placeholders.carregar_dicionario(IDIOMA)["interface"]
CATALOGO = apoio.CATALOGO


def _json(caminho: Path):
    return json.loads(caminho.read_text(encoding="utf-8"))


def _compor_entrega(nome: str) -> dict:
    """A entrega da raiz `nome`: o caso passa pelo gate, os resultados saem do motor, e a análise e o
    ledger entram como o analista os escreveu."""
    origem = RAIZES / nome
    caso = carregar_caso(origem / "caso.json")
    entrega = {
        "versao_contrato": "entrega/1",
        "execucao": {"id": nome, "ticker": caso["ticker"], "idioma": IDIOMA, **_json(origem / "execucao.json"),
                     "suite_da_metodologia": apoio.suite_da_metodologia_que_passou()},
        "caso": caso,
        "resultados": avaliar(caso),
        "analise": _json(origem / "analise.json"),
        "ledger": _json(origem / "ledger.json"),
    }
    if (origem / PARTE_OPCIONAL).exists():
        entrega["dados"] = _json(origem / PARTE_OPCIONAL)
    return entrega


@pytest.fixture(scope="module")
def builds(tmp_path_factory) -> dict:
    """Cada raiz composta e construída uma vez pelo builder de verdade: `{nome: (entrega, raiz, processo)}`."""
    saidas = {}
    for nome in LEGITIMAS + (QUE_DEVE_FALHAR,):
        entrega = _compor_entrega(nome)
        raiz = tmp_path_factory.mktemp(nome)
        apoio.escrever_raiz(raiz, entrega)
        processo = subprocess.run([sys.executable, str(BUILDER), str(raiz)], capture_output=True, text=True,
                                  encoding="utf-8", errors="replace", env=ENV_UTF8, timeout=300)
        saidas[nome] = (entrega, raiz, processo)
    return saidas


def _achados(raiz: Path) -> list:
    return _json(raiz / "qc.json")["achados"]


def _aba_da_pagina(raiz: Path, nome: str) -> dict:
    return _aba((raiz / "relatorio.html").read_text(encoding="utf-8"), nome)


def _secao_da_valuation(aba: dict, titulo: str) -> dict:
    """A seção da aba Valuation cujo título é `titulo` — a aba abre com seções sem título (o cabeçalho),
    que o `_secao` da Tese não pula."""
    (secao,) = [secao for secao in _secoes(aba)
                if any(filho.get("tag") in ("h2", "h3", "h4") for filho in secao["filhos"])
                and _titulo(secao) == titulo]
    return secao


def test_cada_raiz_guarda_so_o_que_o_analista_escreve_e_nenhum_resultados_congelado():
    raizes = sorted(caminho.name for caminho in RAIZES.iterdir() if caminho.is_dir())
    assert raizes == sorted(LEGITIMAS + (QUE_DEVE_FALHAR,))
    for nome in raizes:
        arquivos = {caminho.name for caminho in (RAIZES / nome).iterdir()}
        assert PARTES_DA_RAIZ <= arquivos <= PARTES_DA_RAIZ | {PARTE_OPCIONAL}, (nome, sorted(arquivos))


@pytest.mark.parametrize("nome", LEGITIMAS)
def test_as_raizes_legitimas_emitem_com_codigo_0_e_sem_hard_fail(builds, nome):
    _entrega, raiz, processo = builds[nome]
    assert processo.returncode == 0, processo.stdout + processo.stderr
    assert (raiz / "relatorio.html").exists() and (raiz / "ficha-tecnica.json").exists()
    assert [achado["codigo"] for achado in _achados(raiz) if achado["nivel"] == "HARD_FAIL"] == []


def test_a_raiz_firm_traz_a_escolha_material_no_painel_e_o_driver_acima_do_limiar_na_secao_dos_drivers(builds):
    entrega, raiz, _processo = builds["firm_escolha_driver"]
    resultados = entrega["resultados"]
    assert resultados["rota"] == "firm" and resultados["reversa"] is not None
    (escolha,) = resultados["escolhas_metodologicas"]
    assert escolha["material"] is True and abs(escolha["impacto"]) > 0.10
    acima = [driver for driver in resultados["drivers"]["drivers"] if driver["acima_do_limiar"]]
    assert [driver["nome"] for driver in acima] == ["preço do índice sintético de celulose de fibra curta"]
    valuation = INTERFACE["valuation"]
    aba = _aba_da_pagina(raiz, "valuation")

    # A escolha material sai no nível principal do painel, com o rótulo do catálogo.
    painel = _secao_da_valuation(aba, valuation["escolhas_titulo"])
    avancadas = [artigo for detalhes in _todos(painel, tag="details")
                 for artigo in _todos(detalhes, classe="valuation-escolha")]
    principais = [artigo for artigo in _todos(painel, classe="valuation-escolha") if artigo not in avancadas]
    assert [_titulo(artigo) for artigo in principais] == [
        CATALOGO["escolhas_metodologicas"][escolha["chave"]]["rotulo"][IDIOMA]]

    # O driver acima do limiar sai marcado como tal na seção dos drivers, rotulada como congelada.
    drivers = _secao_da_valuation(aba, valuation["drivers_titulo"])
    assert _visivel(_um(drivers, classe="drivers-congelado-nota")) == valuation["drivers_congelado"]
    linhas = [[_visivel(celula) for celula in _todos(linha, tag="td")]
              for linha in _todos(_um(drivers, tag="tbody"), tag="tr")]
    (linha,) = [linha for linha in linhas if linha[0] == acima[0]["nome"]]
    assert linha[6:] == [valuation["drivers_acima_do_limiar"], valuation["drivers_vira_cenario"]]


def test_a_raiz_sotp_traz_o_segmento_em_rampa_nas_partes_e_na_premissa_decisiva(builds):
    entrega, raiz, _processo = builds["sotp_capacidade"]
    partes = entrega["resultados"]["sotp"]["partes"]
    assert sorted(parte["rota"] for parte in partes) == ["firm", "rampa"]
    indice, rampa = next((indice, parte) for indice, parte in enumerate(partes) if parte["rota"] == "rampa")
    assert entrega["resultados"]["manchete"]["fonte"] == "sotp"

    tese = INTERFACE["tese"]
    premissas = _secao(_aba_da_pagina(raiz, "tese"), tese["premissas_decisivas_titulo"])
    da_rampa = [item for item in _todos(premissas, classe="tese-premissa")
                if _todos(item, classe="tese-premissa-parte")
                and _visivel(_um(item, classe="tese-premissa-parte")) == tese["premissa_da_parte"].format(
                    nome=rampa["nome"], numero=placeholders.formatar(indice + 1, "num0", IDIOMA))]
    assert len(da_rampa) == 1
    rotulo_da_utilizacao = CATALOGO["premissas"]["rampa"]["util"]["rotulo"][IDIOMA]
    assert _visivel(_um(da_rampa[0], classe="metrica-rotulo")) == rotulo_da_utilizacao


def test_a_raiz_que_deve_falhar_sai_com_codigo_2_insumo_sem_proveniencia_e_nenhum_relatorio(builds):
    _entrega, raiz, processo = builds[QUE_DEVE_FALHAR]
    assert processo.returncode == 2, processo.stdout + processo.stderr
    assert not (raiz / "relatorio.html").exists() and not (raiz / "ficha-tecnica.json").exists()
    assert [(achado["codigo"], achado["onde"]) for achado in _achados(raiz) if achado["nivel"] == "HARD_FAIL"] == [
        ("insumo_sem_proveniencia", "caso.ponte.divida_bruta")]


def test_a_raiz_que_deve_falhar_so_difere_da_legitima_pelo_registro_que_falta():
    """O que torna a falha discriminante: o caso e a análise são os da raiz 1, e o ledger é o dela
    menos exatamente o registro que sustenta a dívida bruta — a falha é a proveniência, e nada mais."""
    legitima, falha = RAIZES / "firm_escolha_driver", RAIZES / QUE_DEVE_FALHAR
    for parte in ("caso.json", "analise.json", "execucao.json"):
        assert _json(falha / parte) == _json(legitima / parte), parte
    registros = _json(legitima / "ledger.json")["registros"]
    faltantes = [registro for registro in registros if registro not in _json(falha / "ledger.json")["registros"]]
    assert [registro["usado_em"] for registro in faltantes] == [["ponte.divida_bruta"]]
    assert _json(falha / "ledger.json") == {**_json(legitima / "ledger.json"),
                                            "registros": [r for r in registros if r not in faltantes]}
