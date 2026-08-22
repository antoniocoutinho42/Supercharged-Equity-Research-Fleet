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
    """Levantada quando o motor congelado sai com código != 0, quando a
    stdout dele não é JSON válido, ou quando o processo estoura o timeout.

    Três modos, uma exceção só — é por isso que este wrapper existe: quem
    chama captura só `MotorFalhou` e cobre os três de uma vez, sem precisar
    conhecer `subprocess.TimeoutExpired` nem `json.JSONDecodeError`. Nos
    dois primeiros modos a mensagem carrega o argv chamado, a stdout e a
    stderr do processo — o motor já explica por que recusou (por exemplo,
    `--tv` ausente); este wrapper não reformula o motivo, só propaga o que
    o motor disse. No modo de timeout a mensagem carrega o argv, o valor do
    timeout estourado e o que o processo tiver produzido em stdout/stderr
    até ser morto; a exceção original vem encadeada via `from`.
    """


def _flag(chave: str) -> str:
    """Traduz uma chave de premissa (ou de escala) na flag correspondente."""
    return _FLAGS_COM_HIFEN.get(chave, f"--{chave}")


def _exigir_valor(saida_motor: dict, campo: str) -> float:
    """Devolve `saida_motor[campo]`, recusando com `MotorFalhou` se for `None`.

    Único ponto de normalização: o serializador do motor congelado converte
    todo float não-finito (NaN, Infinity) em `null` — e o processo ainda
    assim sai com código 0, porque a recusa nunca chega a acontecer no
    motor; ele só devolve um número que não dá para representar em JSON.
    Sem esta guarda, esse `null` ou vira `TypeError` cru na primeira conta a
    jusante (o múltiplo do ramo NOPAT entra direto numa multiplicação) ou é
    copiado, em silêncio, para dentro de `resultados.json` (quando o campo
    só é passthrough, como os múltiplos que `avaliar._monta_cenario` copia,
    ou o `multiplo` do teto do crescimento gratuito em `reversa.py`).

    Toda leitura de EV/Equity/Preco_acao/múltiplo vinda do motor passa por
    aqui — nunca por uma checagem própria em cada consumidor — para que um
    builder de relatório futuro, que só lê o `resultados.json` já escrito,
    herde a garantia de que esses campos nunca são `null` em vez de ter de
    repetir a checagem.

    Movida para `motor.py` (FIX 1, revisão final): antes vivia em
    `avaliar.py`, mas `reversa.py` não pode importar `avaliar.py` no topo
    do arquivo (ciclo documentado: `avaliar.py` importa `reversa.reverter`
    no topo; um `from avaliar import _exigir_valor` em `reversa.py`
    fecharia o ciclo pelo lado errado). `motor.py` não importa nem
    `avaliar.py` nem `reversa.py` nem `sensibilidades.py` — é o único lugar
    que os três alcançam sem ciclo, por isso a guarda mora aqui, ao lado de
    `MotorFalhou`, e os três módulos a importam daqui. Foi exatamente a
    cópia sem este import — a leitura de `teto_do_crescimento_gratuito` em
    `reversa.py`, que lia `saida[campo_multiplo]` raw — que vazou `null`
    para `resultados.json`; ver FIX 2 (mesma revisão) sobre a duplicação da
    tradução rota/métrica → campo que acompanhava esse mesmo ponto.

    Nunca substitui um valor: o `None` é recusado, nunca trocado por um
    default — refusing é o comportamento certo aqui também, e a mensagem
    ecoa os `diagnosticos` do próprio motor, porque é ele quem explica o
    porquê (gp sem âncora, ROIC_TV ausente sob 'gordon' etc.), não este
    wrapper.
    """
    valor = saida_motor.get(campo)
    if valor is None:
        diagnosticos = saida_motor.get("diagnosticos") or []
        detalhe = "\n".join(f"- {d}" for d in diagnosticos) or "(nenhum)"
        raise MotorFalhou(
            f"motor devolveu 'null' para '{campo}': o serializador do "
            "motor converte todo float não-finito (NaN ou Infinity) em "
            "`null` e o processo sai com código 0 mesmo assim — este "
            "wrapper recusa em vez de propagar um null silencioso para "
            "resultados.json ou quebrar com TypeError cru na conta "
            f"seguinte.\ndiagnósticos do motor:\n{detalhe}"
        )
    return valor


# Rota (+ tipo de métrica-base, na rota firm) -> campo do motor que carrega o
# múltiplo de REFERÊNCIA da métrica-base. FIX 2 (revisão final): esta
# tradução existia em três cópias que podiam divergir silenciosamente —
# `avaliar.precificar_firm` (EBITDA vs. NOPAT), `avaliar.precificar_equity`
# (sempre PL_curr) e `reversa.teto_do_crescimento_gratuito` (a mesma
# dicotomia de `precificar_firm`, reescrita à mão) — e foi a terceira cópia
# que divergiu: a única sem a recusa de `null` de `_exigir_valor` (FIX 1,
# mesma revisão, mesma causa-raiz). Extraída aqui — o único módulo que
# `avaliar.py`, `reversa.py` e `sensibilidades.py` alcançam sem ciclo de
# import — para que as três leituras usem o mesmo mapeamento em vez de cada
# uma reafirmar a própria cópia.
def _campo_do_multiplo(rota: str, tipo_metrica: str | None) -> str:
    """Campo do motor com o múltiplo de referência da métrica-base.

    Rota firm: `EV/EBITDA_curr` quando `tipo_metrica == "EBITDA"`,
    `EV/NOPAT_curr` para qualquer outro valor — mesma dicotomia binária que
    `precificar_firm` já fazia (`caso.py` só aceita "EBITDA" ou "NOPAT"
    nesta rota; um terceiro valor não é alcançável por um caso validado).

    Rota equity: sempre `PL_curr`, então `tipo_metrica` não entra na
    escolha (a única métrica que `caso.py` aceita aqui é "LL") — o
    parâmetro aceita `None` por isso, para que o chamador não precise
    inventar um `tipo_metrica` só para preencher a assinatura.
    """
    if rota == "firm":
        return "EV/EBITDA_curr" if tipo_metrica == "EBITDA" else "EV/NOPAT_curr"
    return "PL_curr"


def argv_para(rota: str, premissas: dict, escala: dict | None,
              moeda: str | None = None, subcomando: str | None = None) -> list[str]:
    """Monta `[subcomando, *flags]` para `rota` — sem executar nada.

    Não inclui o interpretador nem o caminho do script: só o subcomando
    (`ev` ou `pe`) e as flags. Cada chave de `premissas` vira uma flag com o
    valor logo depois (exceto `mid_year`, booleana); chave ausente do dict,
    OU presente com valor `None`, não produz flag nenhuma — nunca um valor
    inventado. O `None` explícito importa: `caso.py` documenta `None` numa
    premissa opcional (`roic_tv`, `gp`, `roic_book`...) como ausência
    legítima, e sem pular esse caso aqui a flag vira `--roic-tv None`
    (string literal `'None'`), que o motor recusa por tipo errado — os dois
    módulos têm de concordar sobre o que `None` significa.

    `escala` é `None` (sem escala, o motor devolve só os múltiplos) ou o
    dict de métrica de escala da rota — `{"ebitda", "nd", "acoes"}` na rota
    firm, `{"ni", "acoes"}` na equity. Nenhuma chave de escala tem hífen na
    flag do motor, então a mesma tradução genérica de `_flag` se aplica.

    `moeda` é o campo de topo do caso (não é premissa nem escala — por isso
    é parâmetro à parte, nunca uma chave dentro de `premissas`): `None`
    (default) não produz flag nenhuma; uma string produz `--moeda <valor>`,
    aceita pelas duas rotas (`ev` e `pe`) do motor congelado.

    `subcomando` (Fatia B, Task 2): `None` (default) preserva o
    comportamento de sempre — o subcomando sai de `SUBCOMANDO[rota]` (`ev`
    para firm, `pe` para equity), como antes desta fatia existir; os testes
    da fatia A dependem dessa assinatura continuar funcionando exatamente
    assim. Uma string (por exemplo `"rev"`) substitui essa derivação — a
    reversa por eixo usa a mesma `rota` (firm/equity, para escolher o
    vocabulário de premissas certo) mas precisa do subcomando `rev`, que
    não é função só da rota. Aditivo: o caminho antigo nunca muda de
    comportamento, só ganha um caminho novo ao lado.
    """
    argv = [subcomando or SUBCOMANDO[rota]]

    for chave, valor in premissas.items():
        if chave in _FLAGS_BOOLEANAS:
            if valor:
                argv.append(_flag(chave))
            continue
        if valor is None:
            continue
        argv.append(_flag(chave))
        argv.append(str(valor))

    if escala:
        for chave, valor in escala.items():
            argv.append(_flag(chave))
            argv.append(str(valor))

    if moeda:
        argv.append("--moeda")
        argv.append(str(moeda))

    return argv


def executar(argv: list[str], timeout: float = 120) -> dict:
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
    - `timeout` (parâmetro nomeado, default 120) — o motor é determinístico
      e local; não deve travar. O default cobre a chamada real; o parâmetro
      existe nomeado para que os testes possam forçar o caminho de timeout
      com um valor minúsculo, sem esperar 120s de verdade. Se o processo
      estourar o timeout mesmo assim, isso também vira `MotorFalhou` (ver
      abaixo) em vez de escapar como `subprocess.TimeoutExpired` cru —
      mesma disciplina dos outros dois modos de falha.
    """
    script = RAIZ_VENDOR / "scripts" / "justos.py"
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONUTF8": "1"}

    try:
        resultado = subprocess.run(
            [sys.executable, str(script), *argv],
            capture_output=True, text=True, encoding="utf-8",
            timeout=timeout, env=env,
        )
    except subprocess.TimeoutExpired as erro:
        raise MotorFalhou(
            f"motor congelado não respondeu em {timeout}s (timeout) para "
            f"argv {argv!r}.\n"
            f"--- stdout parcial ---\n{erro.stdout or ''}\n"
            f"--- stderr parcial ---\n{erro.stderr or ''}"
        ) from erro

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


def rodar(rota: str, premissas: dict, escala: dict | None = None,
          moeda: str | None = None, subcomando: str | None = None) -> dict:
    """Compõe `argv_para` e `executar`: monta o argv da rota e roda o motor.

    `subcomando` só repassa para `argv_para` (ver o docstring de lá) —
    `None` preserva a derivação antiga (`SUBCOMANDO[rota]`); uma string
    (`"rev"`) escolhe o subcomando explicitamente.
    """
    return executar(argv_para(rota, premissas, escala, moeda, subcomando))
