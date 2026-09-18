"""O script da execução do `er-analise` (item 8, Task 2; D6 e D7 do plano
docs/superpowers/plans/2026-09-16-v4-item8-er-analise.md).

- `nova` cria a árvore da raiz com o id da execução e nunca herda nada de outra execução;
- `suite` grava o código de saída de cada comando e sai com erro quando um deles falha. A lista de
  comandos é injetada: a CI roda a suíte real do vendor (`tests/test_vendor_multiplos_justos.py`), e
  rodá-la a cada caso custaria minutos. Os comandos injetados têm os nomes que o catálogo exige;
- `montar` junta os fragmentos de `evidencia/` num ledger único e recusa id repetido;
- `montar` sobre as partes de uma raiz da fixture sintética gera a entrega que o builder emite com código
  0 — um build de verdade, com a paridade por caso (o único do arquivo).
"""

import json
import shutil
import sys
from datetime import date
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "skills" / "er-analise" / "scripts"))
import execucao  # noqa: E402

sys.path.insert(0, str(RAIZ / "tests"))
import relatorio_apoio as apoio  # noqa: E402

# `relatorio_apoio` já pôs as camadas do relatório e da integração no path: testes não são a camada.
import entrega as contrato_entrega  # noqa: E402
from avaliar import avaliar  # noqa: E402
from caso import carregar as carregar_caso  # noqa: E402

RAIZ_SINTETICA = RAIZ / "tests" / "fixtures" / "analises" / "SINT3" / "firm_escolha_driver"
HOJE = date(2026, 9, 17)


def _json(caminho: Path):
    return json.loads(caminho.read_text(encoding="utf-8"))


def _escrever(caminho: Path, dados) -> None:
    caminho.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")


def _comando_que_sai_com(codigo: int) -> list[str]:
    return [sys.executable, "-c", f"raise SystemExit({codigo})"]


def _nomes_da_suite() -> list[str]:
    return [item["comando"] for item in apoio.CATALOGO["suite_da_metodologia"]]


def _fragmento(registros=(), lacunas=()) -> dict:
    return {"versao_contrato": apoio.CONTRATO_LEDGER["versao_contrato"],
            "registros": list(registros), "lacunas": list(lacunas)}


def test_nova_cria_a_arvore_com_o_id_da_execucao_e_nao_herda_nada_da_anterior(tmp_path):
    base = tmp_path / "analises"
    primeira = execucao.nova("SINT3", base=base, hoje=HOJE)
    assert primeira == base / "SINT3" / "2026-09-17-001"
    assert (primeira / "evidencia").is_dir() and (primeira / "quarentena").is_dir()
    assert _json(primeira / "execucao.json") == {"id": "2026-09-17-001", "ticker": "SINT3", "idioma": "pt-BR"}

    _escrever(primeira / "evidencia" / "filings.json", _fragmento())
    segunda = execucao.nova("SINT3", base=base, produto="leitura_de_preco", hoje=HOJE)
    assert segunda.name == "2026-09-17-002"
    assert _json(segunda / "execucao.json") == {
        "id": "2026-09-17-002", "ticker": "SINT3", "idioma": "pt-BR", "produto": "leitura_de_preco"}
    assert list((segunda / "evidencia").iterdir()) == [] and (primeira / "evidencia" / "filings.json").exists()

    with pytest.raises(execucao.ExecucaoInvalida, match="ticker fora da forma"):
        execucao.nova("../SINT3", base=base, hoje=HOJE)


def test_suite_grava_os_codigos_de_saida_e_sai_com_erro_quando_um_comando_falha(tmp_path):
    nomes = _nomes_da_suite()
    do_catalogo = execucao.comandos_da_suite()
    assert [nome for nome, _argv in do_catalogo] == nomes
    assert all(argv[0] == sys.executable and Path(argv[1]).is_file() for _nome, argv in do_catalogo)

    raiz = execucao.nova("SINT3", base=tmp_path / "analises", hoje=HOJE)
    passam = [(nome, _comando_que_sai_com(0)) for nome in nomes]
    assert execucao.main(["suite", str(raiz)], comandos=passam) == 0
    assert _json(raiz / "execucao.json")["suite_da_metodologia"] == [
        {"comando": nome, "codigo_saida": 0} for nome in nomes]

    uma_falha = [(nome, _comando_que_sai_com(3 if indice == 1 else 0)) for indice, nome in enumerate(nomes)]
    assert execucao.main(["suite", str(raiz)], comandos=uma_falha) == 1
    execucao_gravada = _json(raiz / "execucao.json")
    assert [registro["codigo_saida"] for registro in execucao_gravada["suite_da_metodologia"]] == [0, 3, 0]
    assert execucao_gravada["id"] == raiz.name, "a suíte grava o registro sem tocar no resto da execução"


def test_montar_junta_os_fragmentos_de_evidencia_e_recusa_id_repetido(tmp_path):
    raiz = execucao.nova("SINT3", base=tmp_path / "analises", hoje=HOJE)
    evidencia = raiz / "evidencia"
    receita = apoio.registro_do_ledger("filings:receita", "Receita líquida de 2025", "Companhia", 10500.0)
    preco = apoio.registro_do_ledger("mercado:preco", "Preço de fechamento", "Bolsa", 22.4)
    lacuna = {"id": "mercado:segmentos", "descricao": "Sem abertura por segmento.", "materialidade": "nao_material",
              "tratamento": "A análise usa o consolidado."}
    _escrever(evidencia / "b-mercado.json", _fragmento([preco], [lacuna]))
    _escrever(evidencia / "a-filings.json", _fragmento([receita]))
    assert execucao.juntar_evidencia(raiz) == _fragmento([receita, preco], [lacuna])

    _escrever(evidencia / "c-pares.json", _fragmento([dict(preco, claim="Preço de fechamento ajustado")]))
    with pytest.raises(execucao.ExecucaoInvalida) as erro:
        execucao.juntar_evidencia(raiz)
    for trecho in ("'mercado:preco'", "'b-mercado.json'", "'c-pares.json'"):
        assert trecho in str(erro.value), str(erro.value)


def test_montar_recusa_resultados_de_outra_versao_da_metodologia_nomeando_as_duas_e_o_remedio(tmp_path):
    """Versão única do lado dos resultados (migração v10.1, onda da revisão final, M13): um
    `resultados.json` produzido por outra versão da metodologia que a do catálogo desta instalação não
    entra na entrega — nem os números, nem os rótulos casariam. `montar` recusa antes de compor, nomeando
    as duas versões e o remédio (rodar o `avaliar.py` de novo sobre o caso), e nada sai: sem
    `entrega.json` e sem relatório. A vizinha com a versão do catálogo passa da checagem (e para adiante,
    no ledger que esta raiz mínima não tem)."""
    raiz = execucao.nova("SINT3", base=tmp_path / "analises", hoje=HOJE)
    versao_do_catalogo = apoio.CATALOGO["metodologia"]["versao"]
    for parte in ("caso.json", "analise.json"):
        _escrever(raiz / parte, {})

    _escrever(raiz / "resultados.json", {"origem": {"metodologia": {"nome": "multiplos-justos", "versao": "v9.31"}}})
    with pytest.raises(execucao.ExecucaoInvalida) as erro:
        execucao.montar(raiz)
    for trecho in ("'v9.31'", f"'{versao_do_catalogo}'", "avaliar.py"):
        assert trecho in str(erro.value), str(erro.value)
    assert not (raiz / "entrega.json").exists() and not (raiz / "relatorio.html").exists()
    assert execucao.main(["montar", str(raiz)]) == 1

    _escrever(raiz / "resultados.json",
              {"origem": {"metodologia": {"nome": "multiplos-justos", "versao": versao_do_catalogo}}})
    with pytest.raises(execucao.ExecucaoInvalida, match="não tem fragmento nenhum"):
        execucao.compor_entrega(raiz)


def test_montar_sobre_as_partes_da_raiz_sintetica_gera_a_entrega_que_o_builder_emite(tmp_path):
    """O percurso do M4 sobre a raiz 1 da fixture sintética: o caso e a análise do analista, os resultados
    do `er-valuation`, o ledger chegando em dois fragmentos de mandato, os gates declarados na execução e a
    suíte registrada — e o `montar` devolve o código 0 do builder, com o ledger único igual ao original."""
    raiz = execucao.nova("SINT3", base=tmp_path / "analises", hoje=HOJE)
    for parte in ("caso.json", "analise.json"):
        shutil.copyfile(RAIZ_SINTETICA / parte, raiz / parte)
    _escrever(raiz / "resultados.json", avaliar(carregar_caso(raiz / "caso.json")))
    ledger = _json(RAIZ_SINTETICA / "ledger.json")
    meio = len(ledger["registros"]) // 2
    _escrever(raiz / "evidencia" / "1-filings.json", _fragmento(ledger["registros"][:meio]))
    _escrever(raiz / "evidencia" / "2-mercado.json", _fragmento(ledger["registros"][meio:], ledger["lacunas"]))
    _escrever(raiz / "execucao.json", {**_json(raiz / "execucao.json"),
                                       "gates": _json(RAIZ_SINTETICA / "execucao.json")["gates"]})
    execucao.suite(raiz, [(nome, _comando_que_sai_com(0)) for nome in _nomes_da_suite()])

    assert execucao.montar(raiz) == 0
    entrega = _json(raiz / "entrega.json")
    assert entrega["versao_contrato"] == contrato_entrega.VERSAO_CONTRATO
    assert entrega["ledger"] == ledger
    assert (raiz / "relatorio.html").exists() and (raiz / "ficha-tecnica.json").exists()
    assert [achado["codigo"] for achado in _json(raiz / "qc.json")["achados"] if achado["nivel"] == "HARD_FAIL"] == []
