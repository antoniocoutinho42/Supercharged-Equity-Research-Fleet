"""O script da execução do `er-analise` (item 8, Task 2; D6 e D7 do plano
docs/superpowers/plans/2026-09-16-v4-item8-er-analise.md).

Uma execução é uma raiz `analises/<TICKER>/<execution-id>/`, autocontida (§12 do desenho). Três
subcomandos, um para cada momento em que o Analista precisa de código:

- `nova <TICKER>` (M1) cria a raiz: `evidencia/`, onde cada mandato do agente `pesquisa-evidencia`
  grava o seu fragmento `ledger/1`; `quarentena/`, onde fica o relatório ou valuation anterior com
  conclusão, fechado até o M4; e `execucao.json`, com `id`, `ticker`, `idioma` e, quando declarado,
  `produto`. O id é a data e o primeiro número livre do dia — nenhuma outra execução é lida (§18.4).
- `suite <raiz>` (M4) roda cada comando que o catálogo da integração exige
  (`catalogo.suite_da_metodologia`), cada um numa invocação fresca do interpretador corrente, e grava
  `[{comando, codigo_saida}]` em `execucao.json`. Sai com código 1 quando algum comando não passa: o
  registro fica, e o builder recusa a entrega (`suite_da_metodologia_nao_passou`).
- `montar <raiz>` (M4) compõe `entrega.json` a partir das partes da raiz — `execucao.json`,
  `caso.json`, `resultados.json` (a saída do `er-valuation`), `analise.json`, os fragmentos de
  `evidencia/` juntados num ledger único (D7) e, quando existem, `dados.json` e `confronto.json` — e
  roda o builder do relatório sobre a raiz, devolvendo o código dele. Antes de juntar, recusa um
  `resultados.json` de outra versão da metodologia que a do catálogo (migração v10.1: versão única
  também do lado dos resultados).

E3: este script orquestra, e só. Os comandos da suíte são declaração da metodologia, lida do catálogo; a
conta é do motor, pelo `er-valuation`; a validação da entrega é do builder, que recusa o que não fecha.
Nenhuma regra de metodologia nem de contrato é conferida aqui além do que a junção precisa para não
perder nada em silêncio — nem misturar, em silêncio, resultados de uma versão da metodologia com o
catálogo de outra.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

RAIZ_DO_REPO = Path(__file__).resolve().parents[3]
# Os dois únicos caminhos para fora deste skill: a declaração da integração que diz quais comandos a
# suíte exige, e o builder, que é o único caminho de emissão (§18.6).
CATALOGO = RAIZ_DO_REPO / "skills" / "er-valuation" / "assets" / "catalogo_apresentacao.json"
BUILDER = RAIZ_DO_REPO / "skills" / "er-relatorio" / "scripts" / "builder.py"

BASE_PADRAO = Path("analises")
IDIOMA_PADRAO = "pt-BR"

EXECUCAO = "execucao.json"
EVIDENCIA = "evidencia"
QUARENTENA = "quarentena"
ENTREGA = "entrega.json"
# As partes que a raiz guarda, pelo campo do contrato `entrega/1` em que cada uma entra.
PARTES_OBRIGATORIAS = {"caso": "caso.json", "resultados": "resultados.json", "analise": "analise.json"}
PARTES_OPCIONAIS = {"dados": "dados.json", "confronto": "confronto.json"}
# A versão do contrato que o builder lê; `tests/test_analise_execucao.py` a prende à do `entrega.py`.
VERSAO_DA_ENTREGA = "entrega/1"
# D7: o fragmento de um mandato tem a forma do ledger — a versão e as duas listas que se juntam.
LISTAS_DO_FRAGMENTO = ("registros", "lacunas")
CHAVES_DO_FRAGMENTO = frozenset({"versao_contrato", *LISTAS_DO_FRAGMENTO})

# O prazo de um comando da suíte. A fase `model` leva ~11 s nesta máquina; o prazo só existe para um
# processo travado não segurar a execução para sempre.
TIMEOUT_DO_COMANDO_SEGUNDOS = 900
# O código registrado quando o comando não terminou — estourou o prazo ou nem abriu. Diferente de 0,
# e por isso reprovado no QC como qualquer falha.
CODIGO_SEM_CONCLUSAO = -1

_TICKER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")


class ExecucaoInvalida(Exception):
    """A raiz não tem o que o subcomando precisa, ou uma parte está fora da forma que a junção lê.
    A mensagem nomeia o arquivo; a CLI a converte em código 1."""


def _ler_json(caminho: Path):
    try:
        return json.loads(Path(caminho).read_text(encoding="utf-8"))
    except FileNotFoundError as erro:
        raise ExecucaoInvalida(f"'{caminho}' ausente.") from erro
    except json.JSONDecodeError as erro:
        raise ExecucaoInvalida(f"'{caminho}' não é um JSON válido: {erro}.") from erro


def _escrever_json(caminho: Path, dados) -> None:
    Path(caminho).write_text(json.dumps(dados, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def _ambiente() -> dict:
    """O ambiente dos subprocessos: sem bytecode (a árvore congelada do vendor não ganha `__pycache__`)
    e em utf-8 (um console Windows PT-BR não quebra na saída) — a disciplina de
    `tests/test_vendor_multiplos_justos.py`."""
    return {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONUTF8": "1"}


# --------------------------------------------------------------------------
# nova
# --------------------------------------------------------------------------

def nova(ticker: str, base: Path = BASE_PADRAO, idioma: str = IDIOMA_PADRAO, produto: str | None = None,
         hoje: date | None = None) -> Path:
    """Cria a raiz da execução e devolve o caminho dela. `produto`, quando dado, entra como declarado — o
    vocabulário é do contrato da entrega, e quem o confere é o builder."""
    if not _TICKER.fullmatch(ticker or ""):
        raise ExecucaoInvalida(
            f"ticker fora da forma: {ticker!r} — letras, dígitos, ponto, hífen e sublinhado, começando por "
            "letra ou dígito; ele vira o nome de um diretório.")
    pasta = Path(base) / ticker
    dia = (hoje or date.today()).isoformat()
    numero = 1
    while (pasta / f"{dia}-{numero:03d}").exists():
        numero += 1
    raiz = pasta / f"{dia}-{numero:03d}"
    (raiz / EVIDENCIA).mkdir(parents=True)
    (raiz / QUARENTENA).mkdir()
    execucao = {"id": raiz.name, "ticker": ticker, "idioma": idioma}
    if produto is not None:
        execucao["produto"] = produto
    _escrever_json(raiz / EXECUCAO, execucao)
    return raiz


# --------------------------------------------------------------------------
# suite
# --------------------------------------------------------------------------

def comandos_da_suite(catalogo: dict | None = None) -> list[tuple[str, list[str]]]:
    """`(comando, argv)` de cada comando que o catálogo exige, na ordem dele: o nome pelo qual a execução
    o registra, e o argv — o interpretador corrente, o script a partir da raiz do repositório e os
    argumentos."""
    catalogo = _ler_json(CATALOGO) if catalogo is None else catalogo
    declarados = catalogo.get("suite_da_metodologia") if isinstance(catalogo, dict) else None
    if not (isinstance(declarados, list) and declarados and all(
            isinstance(item, dict) and isinstance(item.get("comando"), str)
            and isinstance(item.get("argv"), list) and item["argv"] for item in declarados)):
        raise ExecucaoInvalida(
            "o catálogo de apresentação não declara 'suite_da_metodologia' na forma — uma lista de "
            "{comando, argv}; a correção é da camada de integração.")
    return [(item["comando"], [sys.executable, str(RAIZ_DO_REPO / item["argv"][0]), *map(str, item["argv"][1:])])
            for item in declarados]


def suite(raiz: Path, comandos: list[tuple[str, list[str]]] | None = None) -> list[dict]:
    """Roda cada comando, cada um no seu processo, e grava `suite_da_metodologia` em `execucao.json` —
    substituindo o registro de uma rodada anterior, nunca somando a ele. Devolve os registros.

    `comandos` é injetável: `[(comando, argv)]`, com o argv inteiro. Sem ele, os do catálogo
    (`comandos_da_suite`)."""
    caminho = Path(raiz) / EXECUCAO
    execucao = _ler_json(caminho)
    if not isinstance(execucao, dict):
        raise ExecucaoInvalida(f"'{caminho}' não é um objeto: crie a execução com o subcomando 'nova'.")
    registros = []
    for comando, argv in (comandos_da_suite() if comandos is None else comandos):
        try:
            processo = subprocess.run(argv, capture_output=True, text=True, encoding="utf-8", errors="replace",
                                      env=_ambiente(), cwd=RAIZ_DO_REPO, timeout=TIMEOUT_DO_COMANDO_SEGUNDOS)
            codigo, saida = processo.returncode, processo.stdout + processo.stderr
        except (OSError, subprocess.TimeoutExpired) as erro:
            codigo, saida = CODIGO_SEM_CONCLUSAO, str(erro)
        registros.append({"comando": comando, "codigo_saida": codigo})
        print(f"{comando}: código de saída {codigo}")
        if codigo != 0:
            print(f"--- '{comando}' não passou; o fim da saída:\n{saida[-3000:]}", file=sys.stderr)
    execucao["suite_da_metodologia"] = registros
    _escrever_json(caminho, execucao)
    return registros


# --------------------------------------------------------------------------
# montar
# --------------------------------------------------------------------------

def juntar_evidencia(raiz: Path) -> dict:
    """D7: o ledger único da entrega, a partir dos fragmentos `evidencia/*.json`, na ordem do nome do
    arquivo.

    Cada fragmento é um objeto com exatamente `versao_contrato`, `registros` e `lacunas` (listas), e
    todos declaram a mesma versão — uma chave a mais sumiria na junção, em silêncio. Registros e lacunas
    entram na ordem em que vêm. Um id que aparece duas vezes, no mesmo fragmento ou em dois, é recusado
    com os dois arquivos: o prefixo de cada mandato é o que evita a colisão, e qual dos dois vale seria
    adivinhação. O conteúdo de cada registro não é conferido aqui — é do builder."""
    fragmentos = sorted((Path(raiz) / EVIDENCIA).glob("*.json"))
    if not fragmentos:
        raise ExecucaoInvalida(
            f"'{Path(raiz) / EVIDENCIA}' não tem fragmento nenhum: o ledger da entrega é a junção dos "
            "fragmentos dos mandatos e do Analista.")
    ledger: dict = {"versao_contrato": None, **{lista: [] for lista in LISTAS_DO_FRAGMENTO}}
    origem_do_id: dict = {lista: {} for lista in LISTAS_DO_FRAGMENTO}
    for caminho in fragmentos:
        fragmento = _ler_json(caminho)
        if not (isinstance(fragmento, dict) and set(fragmento) == CHAVES_DO_FRAGMENTO
                and all(isinstance(fragmento[lista], list) for lista in LISTAS_DO_FRAGMENTO)):
            raise ExecucaoInvalida(
                f"'{caminho.name}' fora da forma do fragmento: um objeto com exatamente 'versao_contrato', "
                "'registros' e 'lacunas', as duas últimas listas.")
        if ledger["versao_contrato"] is None:
            ledger["versao_contrato"] = fragmento["versao_contrato"]
        elif fragmento["versao_contrato"] != ledger["versao_contrato"]:
            raise ExecucaoInvalida(
                f"'{caminho.name}' declara 'versao_contrato' {fragmento['versao_contrato']!r}, e o primeiro "
                f"fragmento declara {ledger['versao_contrato']!r}: o ledger é um só.")
        for lista in LISTAS_DO_FRAGMENTO:
            for item in fragmento[lista]:
                ident = item.get("id") if isinstance(item, dict) else None
                if isinstance(ident, str):
                    if ident in origem_do_id[lista]:
                        raise ExecucaoInvalida(
                            f"id repetido em '{lista}': '{ident}', em '{origem_do_id[lista][ident]}' e em "
                            f"'{caminho.name}' — cada registro e cada lacuna tem um id próprio na execução.")
                    origem_do_id[lista][ident] = caminho.name
                ledger[lista].append(item)
    return ledger


def _versao_da_metodologia(documento, onde: str):
    """A versão da metodologia que `documento` declara em `metodologia.versao` (o catálogo) — ou, com
    `onde == "resultados"`, em `origem.metodologia.versao` (a saída do `er-valuation`). Ausente, `None`:
    quem compara é `exigir_a_mesma_metodologia`, e a ausência também é versão diferente."""
    no = documento.get("origem") if onde == "resultados" and isinstance(documento, dict) else documento
    metodologia = no.get("metodologia") if isinstance(no, dict) else None
    return metodologia.get("versao") if isinstance(metodologia, dict) else None


def exigir_a_mesma_metodologia(resultados, catalogo: dict | None = None) -> None:
    """Versão única do lado dos resultados (migração v10.1): o `resultados.json` da raiz tem de ter
    saído da mesma versão da metodologia que o catálogo desta instalação declara — os números de outra
    versão não casam com o motor, os rótulos e o mapa de conclusões de valor que o relatório lê. Versão
    diferente, ou ausente, é `ExecucaoInvalida` que nomeia as duas e o remédio. É a checagem que a
    junção precisa para não misturar versões em silêncio; o QC do builder não ganha código novo."""
    catalogo = _ler_json(CATALOGO) if catalogo is None else catalogo
    do_catalogo = _versao_da_metodologia(catalogo, "catalogo")
    dos_resultados = _versao_da_metodologia(resultados, "resultados")
    if dos_resultados != do_catalogo:
        raise ExecucaoInvalida(
            f"'resultados.json' foi produzido pela metodologia {dos_resultados!r} "
            f"('origem.metodologia.versao'), e o catálogo desta instalação é da {do_catalogo!r}: rode "
            "skills/er-valuation/scripts/avaliar.py de novo sobre o caso ('python skills/er-valuation/"
            "scripts/avaliar.py <raiz>/caso.json --out <raiz>/resultados.json') antes de montar.")


def compor_entrega(raiz: Path) -> dict:
    """A entrega `entrega/1` das partes da raiz, sem escrever nada. Recusa um `resultados.json` de outra
    versão da metodologia que a do catálogo (`exigir_a_mesma_metodologia`) antes de juntar o resto."""
    raiz = Path(raiz)
    if not raiz.is_dir():
        raise ExecucaoInvalida(f"raiz de execução não é um diretório: '{raiz}'.")
    entrega = {"versao_contrato": VERSAO_DA_ENTREGA, "execucao": _ler_json(raiz / EXECUCAO)}
    for campo, nome in PARTES_OBRIGATORIAS.items():
        entrega[campo] = _ler_json(raiz / nome)
    exigir_a_mesma_metodologia(entrega["resultados"])
    entrega["ledger"] = juntar_evidencia(raiz)
    for campo, nome in PARTES_OPCIONAIS.items():
        if (raiz / nome).exists():
            entrega[campo] = _ler_json(raiz / nome)
    return entrega


def _rodar_builder(raiz: Path) -> int:
    return subprocess.run([sys.executable, str(BUILDER), str(raiz)], env=_ambiente()).returncode


def montar(raiz: Path) -> int:
    """Compõe e grava `entrega.json` e roda o builder sobre a raiz; devolve o código dele (0 emitido, 2
    HARD FAIL, 1 recusa de forma).

    Uma composição recusada levanta `ExecucaoInvalida` — mas antes a `entrega.json` anterior sai, e o
    builder roda assim mesmo: sem entrega ele só desfaz a saída de uma rodada anterior e recusa. Código
    diferente de 0 significa "nada publicável nesta raiz", como no builder (§18.2)."""
    raiz = Path(raiz)
    try:
        (raiz / ENTREGA).unlink()
    except OSError:
        pass
    try:
        entrega = compor_entrega(raiz)
    except ExecucaoInvalida:
        _rodar_builder(raiz)
        raise
    _escrever_json(raiz / ENTREGA, entrega)
    return _rodar_builder(raiz)


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def main(argv: list[str] | None = None, comandos: list[tuple[str, list[str]]] | None = None) -> int:
    """`comandos` é a lista injetável da suíte (só testes a passam); a CLI usa a do catálogo."""
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="A raiz de uma execução do er-analise: criar, rodar a "
                                                 "suíte da metodologia e montar a entrega.")
    subcomandos = parser.add_subparsers(dest="subcomando", required=True)
    parser_nova = subcomandos.add_parser("nova", help="cria analises/<TICKER>/<execution-id>/")
    parser_nova.add_argument("ticker")
    parser_nova.add_argument("--base", type=Path, default=BASE_PADRAO, help="onde fica analises/ (padrão: ./analises)")
    parser_nova.add_argument("--idioma", default=IDIOMA_PADRAO)
    parser_nova.add_argument("--produto", help="analise (padrão do contrato) ou leitura_de_preco")
    parser_suite = subcomandos.add_parser("suite", help="roda a suíte da metodologia e a registra")
    parser_suite.add_argument("raiz", type=Path)
    parser_montar = subcomandos.add_parser("montar", help="compõe entrega.json e roda o builder")
    parser_montar.add_argument("raiz", type=Path)
    args = parser.parse_args(argv)

    try:
        if args.subcomando == "nova":
            print(nova(args.ticker, base=args.base, idioma=args.idioma, produto=args.produto))
            return 0
        if args.subcomando == "suite":
            registros = suite(args.raiz, comandos)
            return 0 if all(registro["codigo_saida"] == 0 for registro in registros) else 1
        return montar(args.raiz)
    except (ExecucaoInvalida, OSError) as erro:
        print(str(erro), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
