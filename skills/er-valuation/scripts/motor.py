"""Invocação do motor congelado: monta o argv por rota, executa, devolve o JSON.

Este módulo NÃO calcula nada. A responsabilidade dele é traduzir uma rota e
um vetor de premissas na chamada de subprocess certa para
`vendor/multiplos-justos/scripts/justos.py` e devolver o JSON que o motor
imprime, sem tocar em nenhum número dele.

A tradução de chave para flag é genérica — não importa `caso.py` de volta.
Quem valida que uma chave de premissa é conhecida e que o tipo do valor está
certo é a Task 1 (`caso.py`); por aqui, qualquer chave que chegue no dict vira
flag, e qualquer chave ausente do dict simplesmente não vira flag nenhuma.
Isso é deliberado: uma premissa que falta não vira default silencioso, ela
some da chamada, e o motor — que já recusa rodar sem `--tv`, por exemplo — é
quem recusa por conta própria.

`argv_para` monta a lista de argumentos sem executar nada, o que a torna
testável sem nunca abrir um subprocess. `executar` faz o oposto: recebe um
argv pronto e só chama o processo. Mantê-las separadas é o que permite testar
a tradução (rota certa, flag certa, premissa ausente vira ausência) e a
execução (código de saída, JSON, ambiente do processo) como duas perguntas
independentes.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

# Path(__file__) é .../skills/er-valuation/scripts/motor.py. .resolve() torna
# absoluto; a partir daí, cada índice de .parents sobe um nível de diretório:
#   parents[0] = .../skills/er-valuation/scripts   (pasta do próprio arquivo)
#   parents[1] = .../skills/er-valuation
#   parents[2] = .../skills
#   parents[3] = .../                               (raiz do repo)
# O "3" vem exatamente dessa contagem — não é arbitrário. Se este arquivo for
# movido para outra profundidade, o índice tem de mudar junto; o sintoma de
# esquecer é `RAIZ_VENDOR` apontar para fora do repo e o primeiro teste deste
# módulo (`test_vendor_esta_onde_o_modulo_espera`) falhar alto, no import,
# em vez de intoxicar silenciosamente uma chamada de motor mais adiante.
RAIZ_VENDOR = Path(__file__).resolve().parents[3] / "vendor" / "multiplos-justos"

# Rota declarada no caso -> subcomando do motor congelado.
SUBCOMANDO: dict[str, str] = {"firm": "ev", "equity": "pe"}

# Apenas estas seis chaves de premissa têm flag com hífen no motor; a chave do
# caso usa underscore (para ser identificador Python válido em caso.json),
# a flag do motor usa hífen. Qualquer chave fora desta tabela vira `--chave`
# direto — é a regra genérica que dispensa este módulo de conhecer o
# vocabulário completo de premissas (isso é papel de `caso.py`).
_FLAGS_COM_HIFEN: dict[str, str] = {
    "roic_tv": "--roic-tv",
    "roe_tv": "--roe-tv",
    "roic_book": "--roic-book",
    "roe_book": "--roe-book",
    "politica_tv": "--politica-tv",
    "mid_year": "--mid-year",
}

# 'mid_year' é a única premissa booleana do motor (store_true): a flag entra
# sozinha, sem valor depois dela, e só quando o valor é truthy — ausente ou
# False têm o mesmo efeito (motor assume fim de ano), então nenhum dos dois
# emite a flag.
_FLAGS_BOOLEANAS: frozenset = frozenset({"mid_year"})


class MotorFalhou(Exception):
    """Levantada quando o motor congelado sai com código != 0, ou quando a
    stdout dele não é JSON válido.

    A mensagem carrega o argv chamado, a stdout e a stderr do processo — o
    motor já explica por que recusou (por exemplo, `--tv` ausente); este
    wrapper não reformula o motivo, só propaga o que o motor disse.
    """


def _flag(chave: str) -> str:
    """Traduz uma chave de premissa (ou de escala) na flag correspondente."""
    return _FLAGS_COM_HIFEN.get(chave, f"--{chave}")


def argv_para(rota: str, premissas: dict, escala: dict | None) -> list[str]:
    """Monta `[subcomando, *flags]` para `rota` — sem executar nada.

    Não inclui o interpretador nem o caminho do script: só o subcomando
    (`ev` ou `pe`) e as flags. Cada chave de `premissas` vira uma flag com o
    valor logo depois (exceto `mid_year`, booleana); chave ausente do dict
    não produz flag nenhuma — nunca um valor inventado.

    `escala` é `None` (sem escala, o motor devolve só os múltiplos) ou o
    dict de métrica de escala da rota — `{"ebitda", "nd", "acoes"}` na rota
    firm, `{"ni", "acoes"}` na equity. Nenhuma chave de escala tem hífen na
    flag do motor, então a mesma tradução genérica de `_flag` se aplica.
    """
    argv = [SUBCOMANDO[rota]]

    for chave, valor in premissas.items():
        if chave in _FLAGS_BOOLEANAS:
            if valor:
                argv.append(_flag(chave))
            continue
        argv.append(_flag(chave))
        argv.append(str(valor))

    if escala:
        for chave, valor in escala.items():
            argv.append(_flag(chave))
            argv.append(str(valor))

    return argv


def executar(argv: list[str]) -> dict:
    """Roda o motor congelado com `argv` e devolve o JSON parseado da stdout.

    Disciplina de chamada, sem exceção:
    - `sys.executable`, nunca um `python` resolvido por PATH — o interpretador
      que roda este processo é o mesmo que roda o motor.
    - `encoding="utf-8"` no subprocess e `PYTHONUTF8=1` no ambiente — o motor
      emite acento e símbolo (≡, ⟹) que estouram sob um locale cp1252
      (Windows PT-BR) assim que a saída é capturada por outro processo.
    - `PYTHONDONTWRITEBYTECODE=1` no ambiente — sem isso, o interpretador
      escreve `__pycache__` dentro de `vendor/multiplos-justos` a cada
      chamada, e um `.pyc` ali quebra o freeze verificado por sha256. Mesma
      disciplina de `tests/test_vendor_multiplos_justos.py`.
    - `timeout=120` — o motor é determinístico e local; não deve travar.
    """
    script = RAIZ_VENDOR / "scripts" / "justos.py"
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONUTF8": "1"}

    resultado = subprocess.run(
        [sys.executable, str(script), *argv],
        capture_output=True, text=True, encoding="utf-8", timeout=120, env=env,
    )

    if resultado.returncode != 0:
        raise MotorFalhou(
            f"motor congelado saiu com código {resultado.returncode} para "
            f"argv {argv!r}.\n--- stdout ---\n{resultado.stdout}\n"
            f"--- stderr ---\n{resultado.stderr}"
        )

    try:
        return json.loads(resultado.stdout)
    except json.JSONDecodeError as erro:
        raise MotorFalhou(
            f"saída do motor não é JSON válido para argv {argv!r}: {erro}.\n"
            f"--- stdout ---\n{resultado.stdout}\n--- stderr ---\n{resultado.stderr}"
        ) from erro


def rodar(rota: str, premissas: dict, escala: dict | None = None) -> dict:
    """Compõe `argv_para` e `executar`: monta o argv da rota e roda o motor."""
    return executar(argv_para(rota, premissas, escala))
