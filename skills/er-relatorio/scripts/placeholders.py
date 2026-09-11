"""Placeholders auditáveis (A7) e formatação numérica por idioma (§16.1).

`{{resultados:<caminho>|<formato>}}`, `{{caso:<caminho>|<formato>}}` e
`{{livre:<texto>}}` são as três únicas formas pelas quais um número (ou
texto livre) pode entrar na prosa de `analise` — todo dígito fora de uma
dessas três é `numero_sem_proveniencia` (HARD FAIL, ver `qc.py`).
`<caminho>` é pontuado, com índice de lista como segmento numérico
(`cenarios.base.valor.preco_acao`).

Este módulo NÃO importa nada de `er-valuation` nem do vendor (E3):
`resolver` recebe os dicts já carregados pelo chamador
(`fontes = {"resultados": ..., "caso": ...}`) e só navega neles — nunca
interpreta o que encontra, nunca faz conta de valuation.

Formatação numérica é local a este módulo, sem o módulo `locale` da
stdlib (§16.1: determinístico, por idioma declarado em `_SEPARADORES`) —
hoje só `pt-BR` (milhar `.`, decimal `,`).
"""

import difflib
import json
import math
import re
from pathlib import Path
from typing import Any

Fontes = dict[str, Any]


class ResolucaoInvalida(Exception):
    """Base de erro de resolução de placeholder/formatação — nunca
    levantada direto; ver `CaminhoInvalido` e `FormatoInvalido`."""


class CaminhoInvalido(ResolucaoInvalida):
    """`<caminho>` não resolve dentro da fonte (`resultados`/`caso`) dada."""


class FormatoInvalido(ResolucaoInvalida):
    """`<formato>` desconhecido, valor incompatível com o formato pedido,
    ou (só em `moeda`) idioma/código de moeda sem dicionário/símbolo."""


_DIR_I18N: Path = Path(__file__).resolve().parent.parent / "assets" / "i18n"

# Separador de milhar e de decimal, por idioma — a ÚNICA forma de
# formatação numérica localizada admitida (§16.1 proíbe o módulo `locale`:
# sem ele, não determinístico entre máquinas). Hoje só pt-BR; um idioma
# novo (Task 4 pode precisar) ganha uma entrada aqui, nunca um `if` a mais
# espalhado pelo módulo.
_SEPARADORES: dict[str, tuple[str, str]] = {
    "pt-BR": (".", ","),
}

_CASAS_NUM: dict[str, int] = {f"num{n}": n for n in range(5)}
_CASAS_PCT: dict[str, int] = {f"pct{n}": n for n in range(3)}
_CASAS_PP: dict[str, int] = {f"pp{n}": n for n in range(3)}
_CASAS_X: dict[str, int] = {f"x{n}": n for n in (1, 2)}
_FORMATOS_CONHECIDOS: frozenset = frozenset(
    set(_CASAS_NUM) | set(_CASAS_PCT) | set(_CASAS_PP) | set(_CASAS_X) | {"moeda"})

_PADRAO_PLACEHOLDER = re.compile(r"\{\{\s*(resultados|caso|livre)\s*:(.*?)\}\}")


def carregar_dicionario(idioma: str) -> dict:
    """Lê `assets/i18n/<idioma>.json`. Único carregador deste asset PRÓPRIO
    do skill (não é a integração — E3 não se aplica aqui); usado tanto por
    `_formatar_moeda` (símbolo da moeda) quanto por `builder.py` (mensagens
    de QC). Sem cache: cada chamada devolve um dict novo, para que ninguém
    mute acidentalmente um dict compartilhado entre chamadas.
    """
    caminho = _DIR_I18N / f"{idioma}.json"
    if not caminho.exists():
        raise FormatoInvalido(f"idioma sem dicionário: '{idioma}' ('{caminho}' não existe).")
    try:
        return json.loads(caminho.read_text(encoding="utf-8"))
    except json.JSONDecodeError as erro:
        raise FormatoInvalido(f"dicionário de '{idioma}' não é um JSON válido: {erro}.") from erro


def _num_localizado(valor: float, casas: int, idioma: str) -> str:
    """`valor` com `casas` decimais, separador de milhar/decimal do
    `idioma`. Sinal só aparece quando o valor ARREDONDADO não é zero (evita
    `"-0,00"` para um valor negativo que arredonda a zero)."""
    if idioma not in _SEPARADORES:
        raise FormatoInvalido(f"idioma sem formatação numérica definida: '{idioma}'.")
    milhar, decimal = _SEPARADORES[idioma]

    negativo = valor < 0
    texto = f"{abs(valor):.{casas}f}"
    parte_inteira, _, parte_decimal = texto.partition(".")

    grupos = []
    while len(parte_inteira) > 3:
        grupos.insert(0, parte_inteira[-3:])
        parte_inteira = parte_inteira[:-3]
    grupos.insert(0, parte_inteira)
    inteiro_formatado = milhar.join(grupos)

    formatado = inteiro_formatado if casas == 0 else f"{inteiro_formatado}{decimal}{parte_decimal}"
    if negativo and float(texto) != 0.0:
        formatado = f"-{formatado}"
    return formatado


def _formatar_moeda(valor: float, idioma: str, moeda: str | None) -> str:
    """2 casas, símbolo do dicionário para o código antes do hífen de
    `caso.moeda` (`"BRL-nominal"` -> código `"BRL"` -> símbolo `"R$"`)."""
    codigo = (moeda or "").split("-", 1)[0]
    dicionario = carregar_dicionario(idioma)
    simbolos = dicionario.get("moeda_simbolo", {})
    simbolo = simbolos.get(codigo)
    if simbolo is None:
        raise FormatoInvalido(
            f"símbolo de moeda desconhecido para o código '{codigo}' (de "
            f"caso.moeda={moeda!r}). Símbolos declarados no dicionário: "
            f"{', '.join(sorted(simbolos)) or '(nenhum)'}."
        )
    return f"{simbolo} {_num_localizado(valor, 2, idioma)}"


def formatar(valor: float, formato: str, idioma: str, moeda: str | None = None) -> str:
    """Formata `valor` (sempre um número) segundo `formato`, no `idioma` dado.

    `num0`-`num4`: `valor` verbatim, N casas. `pct0`-`pct2`: `valor x 100`,
    N casas, sufixo `%` — `valor` é FRAÇÃO (`0.12563` -> `"12,6%"`).
    `pp0`-`pp2`: `valor` verbatim, N casas, sufixo `%` — `valor` já está em
    PONTOS PERCENTUAIS, como o caso declara (`5.0` -> `"5,00%"`; nunca
    multiplicado de novo). `x1`/`x2`: `valor` verbatim, N casas, sufixo `x`
    (múltiplo). `moeda`: 2 casas, símbolo do dicionário para o código antes
    do hífen de `caso.moeda`.

    Levanta `FormatoInvalido` — nomeando o formato, com sugestão por
    `difflib` quando aplicável — para formato desconhecido, valor não
    numérico/não finito, ou (só em `moeda`) código de moeda sem símbolo no
    dicionário. Quem chama (`resolver`, abaixo) decide o que fazer com a
    recusa — este módulo nunca inventa um valor.
    """
    if not isinstance(valor, (int, float)) or isinstance(valor, bool):
        raise FormatoInvalido(f"valor não numérico para o formato '{formato}': {valor!r}.")
    if not math.isfinite(valor):
        raise FormatoInvalido(f"valor não é um número finito para o formato '{formato}': {valor!r}.")

    if formato in _CASAS_NUM:
        return _num_localizado(float(valor), _CASAS_NUM[formato], idioma)
    if formato in _CASAS_PCT:
        return _num_localizado(float(valor) * 100, _CASAS_PCT[formato], idioma) + "%"
    if formato in _CASAS_PP:
        return _num_localizado(float(valor), _CASAS_PP[formato], idioma) + "%"
    if formato in _CASAS_X:
        return _num_localizado(float(valor), _CASAS_X[formato], idioma) + "x"
    if formato == "moeda":
        return _formatar_moeda(float(valor), idioma, moeda)

    sugestao = difflib.get_close_matches(formato, sorted(_FORMATOS_CONHECIDOS), n=1)
    dica = f" Você quis dizer '{sugestao[0]}'? " if sugestao else " "
    raise FormatoInvalido(
        f"formato desconhecido: '{formato}'.{dica}"
        f"Formatos aceitos: {', '.join(sorted(_FORMATOS_CONHECIDOS))}."
    )


def _resolver_caminho(fonte: Any, caminho: str) -> Any:
    """Navega `caminho` (pontuado, índice de lista como segmento numérico)
    dentro de `fonte`; devolve o valor encontrado ou levanta
    `CaminhoInvalido` nomeando o trecho exato que não resolveu."""
    atual = fonte
    percorrido: list[str] = []
    for parte in caminho.split("."):
        percorrido.append(parte)
        if isinstance(atual, list):
            if not parte.lstrip("-").isdigit():
                raise CaminhoInvalido(
                    f"'{'.'.join(percorrido)}' inválido: '{parte}' não é índice de lista."
                )
            indice = int(parte)
            if not (-len(atual) <= indice < len(atual)):
                raise CaminhoInvalido(
                    f"'{'.'.join(percorrido)}' fora de alcance: lista tem {len(atual)} item(ns)."
                )
            atual = atual[indice]
        elif isinstance(atual, dict):
            if parte not in atual:
                raise CaminhoInvalido(f"'{'.'.join(percorrido)}' não existe.")
            atual = atual[parte]
        else:
            raise CaminhoInvalido(
                f"'{'.'.join(percorrido)}' não pode ser percorrido: o "
                f"trecho anterior não é objeto nem lista."
            )
    return atual


def resolver(texto: str, fontes: Fontes, idioma: str, onde: str) -> tuple[str, list[dict], list[dict]]:
    """Resolve todo `{{...}}` de `texto`; devolve `(texto_resolvido, log, erros)`.

    `fontes`: `{"resultados": <dict>, "caso": <dict>}` — os dois blocos já
    carregados da entrega (a moeda do formato `moeda` vem de
    `fontes["caso"]["moeda"]`). `onde` identifica o campo de onde `texto`
    veio (`"analise.conclusao.texto"`) — carregado em toda entrada de
    `log`/`erros` para que `qc.py` nomeie o campo na recusa.

    Um placeholder que falha (caminho inexistente, valor não numérico,
    formato desconhecido, `{{...}}` malformado) permanece LITERAL em
    `texto_resolvido` — nunca vira exceção nem string vazia — e ganha uma
    entrada em `erros`; decidir o que fazer com isso é responsabilidade de
    `qc.py` (`placeholder_nao_resolvido`, HARD FAIL), nunca deste módulo.
    """
    log: list[dict] = []
    erros: list[dict] = []
    caso_fonte = fontes.get("caso")
    moeda_do_caso = caso_fonte.get("moeda") if isinstance(caso_fonte, dict) else None

    def _substituir(m: "re.Match[str]") -> str:
        token = m.group(0)
        namespace = m.group(1)
        resto = m.group(2)

        if namespace == "livre":
            log.append({"onde": onde, "tipo": "livre", "caminho": None, "formato": None,
                        "bruto": resto, "resolvido": resto})
            return resto

        partes = resto.split("|", 1)
        if len(partes) != 2 or not partes[0].strip() or not partes[1].strip():
            erros.append({
                "onde": onde, "token": token,
                "razao": f"placeholder malformado: esperado '<caminho>|<formato>', recebido '{resto}'.",
            })
            return token
        caminho, formato = partes[0].strip(), partes[1].strip()

        fonte = fontes.get(namespace)
        if not isinstance(fonte, dict):
            erros.append({
                "onde": onde, "token": token,
                "razao": f"fonte '{namespace}' indisponível para resolver o placeholder.",
            })
            return token

        try:
            bruto = _resolver_caminho(fonte, caminho)
            resolvido = formatar(bruto, formato, idioma, moeda_do_caso)
        except ResolucaoInvalida as erro:
            erros.append({"onde": onde, "token": token, "razao": str(erro)})
            return token

        log.append({"onde": onde, "tipo": namespace, "caminho": caminho, "formato": formato,
                    "bruto": bruto, "resolvido": resolvido})
        return resolvido

    texto_resolvido = _PADRAO_PLACEHOLDER.sub(_substituir, texto)
    return texto_resolvido, log, erros
