"""Orquestração: caso.json -> resultados.json.

Este módulo NÃO faz conta de valuation. Ele compõe os três módulos que já
carregam essa responsabilidade — `caso.carregar` (lê e valida), `motor.rodar`
(chama o motor congelado por subprocess) e `ponte.compor` (soma as linhas de
balanço em `nd_efetivo`) — e organiza o que eles devolvem no formato de saída
canônico. `avaliar` não chama `caso.validar` de novo: validar é
responsabilidade exclusiva de quem carrega o caso (a CLI deste módulo, ou
qualquer outro consumidor), como o próprio `caso.py` documenta. `avaliar`
confia no dict que recebe.

Por cenário, a rota do caso decide o fluxo:

- rota firm, métrica EBITDA: o motor recebe `--ebitda/--nd/--acoes` e faz a
  ponte inteira internamente — `EV`, `Equity` e `Preco_acao` saem prontos do
  motor, usados aqui verbatim.
- rota firm, métrica NOPAT: o motor não tem flag equivalente para essa
  escala. Roda-se sem escala (o motor devolve só os múltiplos) e a álgebra —
  `EV = EV/NOPAT_curr × NOPAT`, depois `Equity = EV − nd_efetivo`, depois
  `preco_acao = Equity / acoes_diluidas` — é feita aqui, em cima do múltiplo
  que o motor emitiu. É a única conta que este módulo faz: a definição de um
  múltiplo (preço = múltiplo × métrica), nunca uma reinterpretação do que o
  motor devolveu.
- rota equity: o motor recebe `--ni/--acoes` e devolve `Equity`/`Preco_acao`
  prontos — não há ponte de dívida nesta rota (`caso.py` já recusa um caso
  equity que declare `ponte`).

A saída é determinística: função pura do `caso` recebido, sem hora de
execução, caminho absoluto ou qualquer valor do ambiente. A data que aparece
no resultado é `data_analise`, do próprio caso.
"""

import argparse
import json
import sys
from pathlib import Path

from caso import CasoInvalido, carregar
from motor import MotorFalhou, rodar
from ponte import compor

# Subconjunto do que o motor devolve que vira o campo "multiplos" de cada
# cenário — não é passthrough do dict inteiro do motor (que carrega chaves de
# apresentação como 'tv', 'aviso_tv', 'convencao_fluxo_transicao_C7' etc.,
# irrelevantes para o shape de resultados.json). Uma chave ausente na saída do
# motor (não deveria acontecer, dado o contrato de `motor.rodar`) é omitida em
# vez de virar `None` inventado.
_MULTIPLOS_POR_ROTA: dict[str, tuple[str, ...]] = {
    "firm": ("EV/NOPAT_curr", "EV/NOPAT_fwd", "EV/EBITDA_curr", "EV/EBITDA_fwd"),
    "equity": ("PL_curr", "PL_fwd"),
}


def _cenario_firm(cenario: dict, tipo_metrica: str, valor_metrica: float,
                   nd_efetivo: float, acoes: float) -> tuple[dict, dict, str]:
    """Roda o motor para um cenário da rota firm; devolve (saída, valor, álgebra).

    `tipo_metrica` já chegou validado por `caso.py` como 'EBITDA' ou 'NOPAT'
    (as únicas métricas que `METRICAS_POR_ROTA["firm"]` aceita) — este ponto
    confia nisso e não trata um terceiro caso.
    """
    premissas = cenario["premissas"]

    if tipo_metrica == "EBITDA":
        escala = {"ebitda": valor_metrica, "nd": nd_efetivo, "acoes": acoes}
        saida = rodar("firm", premissas, escala)
        valor = {
            "EV": saida["EV"],
            "Equity": saida["Equity"],
            "preco_acao": saida["Preco_acao"],
        }
        algebra = "EV = EV/EBITDA_curr x EBITDA (ponte feita pelo motor)"
    else:  # NOPAT
        saida = rodar("firm", premissas, None)
        ev = saida["EV/NOPAT_curr"] * valor_metrica
        equity = ev - nd_efetivo
        preco_acao = equity / acoes
        valor = {"EV": ev, "Equity": equity, "preco_acao": preco_acao}
        algebra = (
            "EV = EV/NOPAT_curr x NOPAT; Equity = EV - nd_efetivo; "
            "preco_acao = Equity / acoes_diluidas (ponte aplicada aqui, fora do motor)"
        )

    return saida, valor, algebra


def _cenario_equity(cenario: dict, valor_metrica: float, acoes: float) -> tuple[dict, dict, str]:
    """Roda o motor para um cenário da rota equity; devolve (saída, valor, álgebra).

    Sem ponte: a rota equity chega em Equity diretamente (P/L x LL) — não há
    dívida líquida a subtrair.
    """
    premissas = cenario["premissas"]
    escala = {"ni": valor_metrica, "acoes": acoes}
    saida = rodar("equity", premissas, escala)
    valor = {"Equity": saida["Equity"], "preco_acao": saida["Preco_acao"]}
    algebra = "Equity = PL_curr x LL (motor); rota equity nao usa ponte"
    return saida, valor, algebra


def _monta_cenario(cenario: dict, saida_motor: dict, rota: str, valor: dict,
                    algebra: str, preco_valor: float) -> dict:
    """Compõe o registro de um cenário no shape de `resultados.json`.

    `upside` é a única outra conta feita fora do motor: `preco_acao / preco.valor
    − 1`, comparação simples contra o preço declarado no caso — não é
    valuation, é a leitura de quanto o preço de mercado diverge do valor que
    saiu do motor (mais a álgebra de escala, quando aplicável).
    """
    chaves_multiplo = _MULTIPLOS_POR_ROTA[rota]
    multiplos = {chave: saida_motor[chave] for chave in chaves_multiplo if chave in saida_motor}
    upside = valor["preco_acao"] / preco_valor - 1

    return {
        "ancora": cenario["ancora"],
        "triangulo": cenario["triangulo"],
        "premissas": cenario["premissas"],
        "multiplos": multiplos,
        "valor": valor,
        "algebra_da_escala": algebra,
        "vs_preco": {"upside": upside},
        "diagnosticos": saida_motor["diagnosticos"],
        "coerencia_vetor": saida_motor["coerencia_vetor"],
        "convencao_temporal": saida_motor["convencao_temporal"],
    }


def avaliar(caso: dict) -> dict:
    """Roda o motor por cenário na rota do caso e monta o conteúdo de `resultados.json`.

    Função pura: mesma entrada, mesma saída, sempre — nenhum relógio, nenhum
    caminho absoluto, nenhum valor de ambiente entra no resultado. A única
    data que aparece é `caso["data_analise"]`.
    """
    rota = caso["rota"]
    metrica = caso["metrica_base"]
    acoes = caso["acoes_diluidas"]
    preco_valor = caso["preco"]["valor"]

    resultado: dict = {
        "companhia": caso["companhia"],
        "ticker": caso.get("ticker"),
        "moeda": caso["moeda"],
        "data_analise": caso["data_analise"],
        "rota": rota,
        "metrica_base": {"tipo": metrica["tipo"], "valor": metrica["valor"]},
        "preco": caso["preco"],
        "acoes_diluidas": acoes,
    }

    cenarios: dict = {}
    if rota == "firm":
        ponte = compor(caso["ponte"])
        resultado["ponte"] = ponte
        nd_efetivo = ponte["nd_efetivo"]
        for nome, cenario in caso["cenarios"].items():
            saida, valor, algebra = _cenario_firm(
                cenario, metrica["tipo"], metrica["valor"], nd_efetivo, acoes)
            cenarios[nome] = _monta_cenario(cenario, saida, rota, valor, algebra, preco_valor)
    else:  # equity
        for nome, cenario in caso["cenarios"].items():
            saida, valor, algebra = _cenario_equity(cenario, metrica["valor"], acoes)
            cenarios[nome] = _monta_cenario(cenario, saida, rota, valor, algebra, preco_valor)

    resultado["cenarios"] = cenarios
    return resultado


def escrever(resultados: dict, destino: Path) -> None:
    """Grava `resultados` como JSON determinístico em `destino`.

    `indent=2` e `ensure_ascii=False` (acento fica legível no arquivo, não
    vira `\\uXXXX`); `\n` final e `newline="\n"` desligam a tradução de fim de
    linha do Windows — o mesmo `resultados` sempre grava os mesmos bytes.
    """
    texto = json.dumps(resultados, indent=2, ensure_ascii=False) + "\n"
    Path(destino).write_text(texto, encoding="utf-8", newline="\n")


def main(argv: list[str] | None = None) -> int:
    # Saída deste processo pode carregar acento/símbolo de qualquer recusa
    # que este CLI converte em mensagem (CasoInvalido, MotorFalhou, caminho
    # inexistente, JSON malformado, falha ao gravar --out) — sem isto, um
    # console Windows PT-BR sem PYTHONUTF8 pode estourar UnicodeEncodeError
    # ao imprimir, mascarando o erro real. Mesma disciplina de `motor.executar`.
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(
        description="Roda o motor congelado por cenário e grava resultados.json.")
    parser.add_argument("caso", type=Path, help="caminho do caso.json de entrada")
    parser.add_argument("--out", type=Path, required=True, help="caminho do resultados.json de saída")
    args = parser.parse_args(argv)

    try:
        resultados = avaliar(carregar(args.caso))
    except FileNotFoundError as erro:
        print(f"arquivo de caso não encontrado: '{args.caso}' ({erro}).", file=sys.stderr)
        return 1
    except json.JSONDecodeError as erro:
        print(f"'{args.caso}' não é um JSON válido: {erro}.", file=sys.stderr)
        return 1
    except (CasoInvalido, MotorFalhou) as erro:
        print(str(erro), file=sys.stderr)
        return 1

    try:
        escrever(resultados, args.out)
    except OSError as erro:
        print(f"não foi possível gravar '{args.out}': {erro}.", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
