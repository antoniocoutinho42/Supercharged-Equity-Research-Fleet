"""Contrato dos exhibits e de `dados` (fatia 5B, item 5, Task 1) — a
gramática de gráfico da §10 do desenho, como `analise.exhibits[]` +
`entrega.dados` no contrato `entrega/1` (aditivo à 5A).

**A spec não declara número nenhum** (a decisão que esta fatia acrescenta
sobre o que a §10 pedia): uma série `direta` aponta para um campo de
`entrega.dados`, uma série `derivada` traz uma fórmula sobre campos do
MESMO dataset, uma série `engine` aponta para um caminho de `resultados`.
Este módulo lê os valores; nunca os declara. Uma série cuja fonte/fórmula/
caminho não resolve é "não rastreável" — o builder recusa emitir (QC HARD
FAIL, nunca um número inventado ou omitido em silêncio).

Este módulo NÃO importa nada de `er-valuation` nem do vendor (E3,
`docs/desenho-arquitetura-v4.md` §15) — `dados`, `resultados` e `caso`
chegam aqui como dicts OPACOS; só navegação e aritmética de FÓRMULA
DECLARADA (nunca de valuation) acontecem aqui.

**Por que este módulo não importa `entrega.py`** (e duplica, de propósito,
`_recusar_chave_desconhecida`/`_exigir_objeto`/`_exigir_texto_nao_vazio`):
`entrega.py` precisa chamar `validar_dados`/`validar_exhibits` daqui de
dentro de `_validar()` (a única forma de uma chave desconhecida ou um
`tipo` fora do enum virar recusa de contrato -- código 1 -- é levantar
`EntregaInvalida` de dentro de `entrega.carregar()`; `builder.py` só
captura essa exceção, e a Task 1 não toca `builder.py`). Se este módulo
importasse `entrega.py` de volta, o import ficaria circular. A duplicação
é de ~15 linhas de utilitário genérico (rejeitar chave fora de um
vocabulário, exigir objeto/texto não vazio) — mesmo espírito da duplicação
deliberada do `sha256_canonico` em `entrega.py` (E3/A2): melhor duplicar
um pedaço pequeno e estável do que acoplar dois módulos em ciclo.
`ContratoDeExhibitInvalido`, portanto, é a exceção PRÓPRIA deste módulo;
`entrega.py` a captura e relança como `EntregaInvalida`.

**Como uma série `derivada` sabe de qual dataset seus campos vêm** (G3,
corrigido em 11/09/2026 -- ver `docs/superpowers/plans/2026-09-11-v4-item5b-
graficos.md`, decisão G3): a série DECLARA o dataset em `fonte`, simétrico
à `direta` (`fonte = "<dataset>.<campo>"`) mas só o id do dataset, sem
campo (`fonte = "<dataset>"`) -- a fórmula roda sobre os campos DESSE
dataset. A primeira versão deste módulo inferia o dataset pelo `id` do
próprio exhibit (`entrega["dados"][exhibit["id"]]`); essa convenção
IMPLÍCITA foi removida sem fallback nenhum -- ela acoplava a identidade do
gráfico à do dado e impedia dois exhibits de compartilharem um dataset
(cada um exigiria sua própria cópia dos mesmos números, num artefato que um
agente futuro escreve à mão). Declaração explícita vence convenção
implícita, mesmo princípio já decidido no `cenario_base`. Três causas
DISTINTAS de `serie_nao_rastreavel` para uma `derivada` (nunca um fallback,
sempre nomeando qual das três ocorreu, ver `resolver_serie`): `fonte`
ausente; `fonte` com ponto (a sintaxe de `direta`, usada por engano); ou
`fonte` nomeando um dataset que não existe em `entrega.dados`. Uma série
`engine` não usa dataset nenhum — lê `resultados` direto.

**Rastreabilidade (G8):** cada série/overlay resolvido gera UMA entrada de
log `{exhibit, serie, origem, detalhe}` — `serie` carrega o índice
posicional (de `series[]` ou de `overlays[]`; `origem` desambigua:
`direta`/`derivada`/`engine` para série, `caso`/`resultados` para
overlay), `detalhe` a referência exata (fonte, fórmula ou caminho). A aba
Evidência (Task 2/3) exibe este log; este módulo só o produz.
"""

import ast
import difflib
import math
from typing import Any

import placeholders

# --------------------------------------------------------------------------
# G2 — enum fechado de `tipo`. `decomposicao` fica fora desta fatia (5D é
# quem teria consumidor para ela — construir para consumidor inexistente é
# o erro que o `degrau` já ensinou a evitar).
# --------------------------------------------------------------------------

TIPOS_CARTESIANOS: frozenset = frozenset({"linha", "barras", "area", "empilhado", "dispersao"})

# RESERVADO, fora do enum aceito (B7, onda de correção da revisão final,
# achado F11): os dois gráficos NÃO-cartesianos existem como PAINÉIS da aba
# Valuation (`render._paineis_valuation_para_json` + `assets/svg.js`),
# alimentados direto por `resultados.ponte`/`sensibilidades.grades_2d` --
# nunca como exhibit declarado. A spec resolvida de um exhibit é `eixoX +
# séries de números` (`render._exhibit_para_json`), que genuinamente não
# expressa `{rotulo, valor, sinal}` nem uma grade com dois eixos de
# premissa: até esta correção, um exhibit `tipo: "waterfall"` saía com rc 0,
# QC limpo, e caía no fallback textual no browser. Mesma decisão que o plano
# já tomou para `decomposicao` -- "construir para consumidor inexistente é o
# erro que o `degrau` já ensinou a evitar". O nome fica declarado aqui (é
# vocabulário reservado do desenho, §10) para quando existir uma forma de
# série que os expresse.
TIPOS_PROPRIOS: frozenset = frozenset({"waterfall", "matriz"})

TIPOS: frozenset = TIPOS_CARTESIANOS | frozenset({"tabela"})

# G3 — as três formas de proveniência de uma série; nenhuma outra existe.
DERIVACOES: frozenset = frozenset({"direta", "derivada", "engine"})

# --------------------------------------------------------------------------
# G1/G3/G4 — vocabulário fechado por nível. `?` no comentário do plano vira,
# aqui, "não está em CHAVES_..._OBRIGATORIAS".
# --------------------------------------------------------------------------

# Fatia 5D, item 5, Task 2 (D5): `vinculo` saiu deste vocabulário. A 5B o
# validava aqui como lista de textos, à espera das perguntas da tese; com elas
# no contrato, a ligação mora só na pergunta (`analise.perguntas[].exhibits`) —
# duas declarações da mesma ligação divergiriam.
CHAVES_DE_EXHIBIT: frozenset = frozenset({
    "id", "pergunta", "tipo", "series", "overlays", "nota_janela", "caption",
})
CHAVES_DE_EXHIBIT_OBRIGATORIAS: frozenset = frozenset({"id", "pergunta", "tipo", "series"})

CHAVES_DE_OVERLAY: frozenset = frozenset({"chave", "rotulo"})

# G3 — cada `derivacao` tem o SEU PRÓPRIO conjunto fechado de chaves
# (nenhuma é "comum" às três, exceto a própria `derivacao`); todas as
# chaves de cada conjunto são obrigatórias (nenhuma série tem campo
# opcional além do que já está listado aqui).
#
# Fatia 5D, onda de correção da revisão final (N12): a série `engine` declara o
# `rotulo` que o gráfico escreve na legenda e no cabeçalho da tabela — prosa
# auditável (`placeholders.campos_de_prosa`), como a `formula_nota` da derivada.
# Sem ele, o adaptador recebia a própria `chave` ("resultados:manchete.preco_acao")
# e a mostrava dentro da aba Tese, sob a pergunta.
_CHAVES_SERIE_POR_DERIVACAO: dict = {
    "direta": frozenset({"derivacao", "fonte"}),
    "derivada": frozenset({"derivacao", "fonte", "formula", "formula_nota"}),
    "engine": frozenset({"derivacao", "chave", "rotulo"}),
}

CHAVES_DE_DATASET: frozenset = frozenset({"ledger", "x", "campos"})


class ContratoDeExhibitInvalido(Exception):
    """Vocabulário fechado violado em `analise.exhibits`/`entrega.dados`
    (G1-G4): chave desconhecida, campo obrigatório ausente, `tipo`/
    `derivacao` fora do enum. Sempre capturada por `entrega.py` e relançada
    como `EntregaInvalida` (código 1) — ver o docstring do módulo para o
    motivo de não ser a própria `EntregaInvalida`."""


class FormulaInvalida(Exception):
    """A fórmula de uma série `derivada` usa sintaxe fora do avaliador
    fechado (só `+ - * /`, menos unário, parênteses, números e nomes de
    campo — nunca `eval`/`exec`), referencia um nome fora dos campos do
    dataset, ou produz um resultado não finito."""


class SerieInvalida(Exception):
    """Uma série ou overlay cujo valor não pôde ser resolvido de forma
    rastreável. Carrega o código de QC já pronto (`serie_nao_rastreavel`,
    `formula_invalida`, `overlay_nao_resolvido` ou
    `serie_de_tamanho_incompativel`) e os `params` para virar um
    `qc.Achado` sem que `qc.py` precise recomputar a causa. `params` NUNCA
    inclui a chave `'onde'` — quem constrói o `Achado` passa `onde`
    separadamente (mesma disciplina do resto de `qc.py`)."""

    def __init__(self, codigo: str, onde: str, params: dict):
        self.codigo = codigo
        self.onde = onde
        self.params = dict(params)
        super().__init__(f"{codigo} em {onde}: {self.params}")


# --------------------------------------------------------------------------
# Utilitários genéricos duplicados de `entrega.py` (ver docstring do
# módulo) — mesmo comportamento, exceção própria.
# --------------------------------------------------------------------------

def _exigir_objeto(valor: Any, campo: str) -> dict:
    if not isinstance(valor, dict):
        raise ContratoDeExhibitInvalido(f"'{campo}' não é um objeto: {valor!r}.")
    return valor


def _exigir_texto_nao_vazio(valor: Any, campo: str) -> str:
    if not isinstance(valor, str) or not valor.strip():
        raise ContratoDeExhibitInvalido(f"'{campo}' ausente ou vazio: {valor!r}.")
    return valor


def _recusar_chave_desconhecida(objeto: dict, permitidas: frozenset, onde: str) -> None:
    desconhecidas = sorted(set(objeto) - permitidas)
    if not desconhecidas:
        return
    chave = desconhecidas[0]
    sugestao = difflib.get_close_matches(chave, sorted(permitidas), n=1)
    dica = f" Você quis dizer '{sugestao[0]}'? " if sugestao else " "
    raise ContratoDeExhibitInvalido(
        f"chave desconhecida em '{onde}': '{chave}'.{dica}"
        f"Chaves aceitas: {', '.join(sorted(permitidas))}."
    )


# --------------------------------------------------------------------------
# Validação de contrato (código 1) — chamada por `entrega.py`. Vocabulário
# fechado e presença; NUNCA tenta resolver fonte/fórmula/chave (isso é
# rastreabilidade, QC, ver `resolver_serie`/`resolver_overlay` abaixo).
# --------------------------------------------------------------------------

def validar_dados(valor: Any) -> None:
    """`entrega.dados` (G3): `{<id>: {"ledger": [...], "x": [...], "campos":
    {<campo>: [...]}}}`. `ledger` só tem o tipo confirmado aqui — o schema
    de cada registro é do item 7."""
    dados = _exigir_objeto(valor, "dados")
    for dataset_id in sorted(dados):
        _validar_dataset(dados[dataset_id], f"dados.{dataset_id}")


def _validar_dataset(valor: Any, onde: str) -> None:
    dataset = _exigir_objeto(valor, onde)
    _recusar_chave_desconhecida(dataset, CHAVES_DE_DATASET, onde)
    for campo in sorted(CHAVES_DE_DATASET):
        if campo not in dataset:
            raise ContratoDeExhibitInvalido(f"campo obrigatório ausente em '{onde}': '{campo}'.")
    if not isinstance(dataset["ledger"], list):
        raise ContratoDeExhibitInvalido(f"'{onde}.ledger' não é uma lista: {dataset['ledger']!r}.")
    if not isinstance(dataset["x"], list):
        raise ContratoDeExhibitInvalido(f"'{onde}.x' não é uma lista: {dataset['x']!r}.")
    campos = _exigir_objeto(dataset["campos"], f"{onde}.campos")
    for nome_campo in sorted(campos):
        if not isinstance(campos[nome_campo], list):
            raise ContratoDeExhibitInvalido(
                f"'{onde}.campos.{nome_campo}' não é uma lista: {campos[nome_campo]!r}."
            )


def validar_exhibits(valor: Any) -> None:
    """`analise.exhibits` (G1): lista de exhibits, cada um no vocabulário
    fechado de `CHAVES_DE_EXHIBIT`. Lista vazia é válida (G10 do desenho:
    "não há gráfico obrigatório")."""
    if not isinstance(valor, list):
        raise ContratoDeExhibitInvalido(f"'analise.exhibits' não é uma lista: {valor!r}.")
    for indice, exhibit in enumerate(valor):
        _validar_exhibit(exhibit, f"analise.exhibits.{indice}")

    # Fatia 5D, Task 3: uma pergunta da tese cita o exhibit pelo `id`, e o
    # gráfico encontra o seu host pelo índice desse `id` na lista — com um id
    # repetido, as duas ligações ficariam ambíguas, e um dos exhibits sumiria da
    # página em silêncio.
    ids = [exhibit["id"] for exhibit in valor]
    repetidos = sorted({ident for ident in ids if ids.count(ident) > 1})
    if repetidos:
        raise ContratoDeExhibitInvalido(
            f"'analise.exhibits' repete o id '{repetidos[0]}': cada exhibit tem um id próprio — é por "
            "ele que uma pergunta da tese o cita e que o gráfico encontra o seu lugar na página."
        )


def _validar_tipo(tipo: Any, onde: str) -> None:
    if tipo in TIPOS:
        return
    sugestao = difflib.get_close_matches(str(tipo), sorted(TIPOS), n=1)
    dica = f" Você quis dizer '{sugestao[0]}'? " if sugestao else " "
    raise ContratoDeExhibitInvalido(
        f"'{onde}.tipo' fora do enum fechado: {tipo!r}.{dica}Tipos aceitos: {', '.join(sorted(TIPOS))}."
    )


def _validar_exhibit(valor: Any, onde: str) -> None:
    exhibit = _exigir_objeto(valor, onde)
    _recusar_chave_desconhecida(exhibit, CHAVES_DE_EXHIBIT, onde)
    for campo in sorted(CHAVES_DE_EXHIBIT_OBRIGATORIAS):
        if campo not in exhibit:
            raise ContratoDeExhibitInvalido(f"campo obrigatório ausente em '{onde}': '{campo}'.")

    _exigir_texto_nao_vazio(exhibit["id"], f"{onde}.id")
    _exigir_texto_nao_vazio(exhibit["pergunta"], f"{onde}.pergunta")
    _validar_tipo(exhibit["tipo"], onde)

    series = exhibit["series"]
    if not isinstance(series, list) or not series:
        raise ContratoDeExhibitInvalido(f"'{onde}.series' vazio ou não é uma lista: {series!r}.")
    for indice, serie in enumerate(series):
        _validar_serie(serie, f"{onde}.series.{indice}")

    if "overlays" in exhibit:
        overlays = exhibit["overlays"]
        if not isinstance(overlays, list):
            raise ContratoDeExhibitInvalido(f"'{onde}.overlays' não é uma lista: {overlays!r}.")
        for indice, overlay in enumerate(overlays):
            _validar_overlay(overlay, f"{onde}.overlays.{indice}")

    if "nota_janela" in exhibit:
        _exigir_texto_nao_vazio(exhibit["nota_janela"], f"{onde}.nota_janela")
    if "caption" in exhibit:
        _exigir_texto_nao_vazio(exhibit["caption"], f"{onde}.caption")


def _validar_serie(valor: Any, onde: str) -> None:
    serie = _exigir_objeto(valor, onde)
    if "derivacao" not in serie:
        raise ContratoDeExhibitInvalido(f"campo obrigatório ausente em '{onde}': 'derivacao'.")

    derivacao = serie["derivacao"]
    chaves_esperadas = _CHAVES_SERIE_POR_DERIVACAO.get(derivacao)
    if chaves_esperadas is None:
        sugestao = difflib.get_close_matches(str(derivacao), sorted(DERIVACOES), n=1)
        dica = f" Você quis dizer '{sugestao[0]}'? " if sugestao else " "
        raise ContratoDeExhibitInvalido(
            f"'{onde}.derivacao' fora do enum fechado: {derivacao!r}.{dica}"
            f"Valores aceitos: {', '.join(sorted(DERIVACOES))}."
        )
    _recusar_chave_desconhecida(serie, chaves_esperadas, onde)
    for campo in sorted(chaves_esperadas - {"derivacao"}):
        _exigir_texto_nao_vazio(serie.get(campo), f"{onde}.{campo}")


def _validar_overlay(valor: Any, onde: str) -> None:
    overlay = _exigir_objeto(valor, onde)
    _recusar_chave_desconhecida(overlay, CHAVES_DE_OVERLAY, onde)
    if "chave" not in overlay:
        raise ContratoDeExhibitInvalido(f"campo obrigatório ausente em '{onde}': 'chave'.")
    _exigir_texto_nao_vazio(overlay["chave"], f"{onde}.chave")
    if "rotulo" in overlay:
        _exigir_texto_nao_vazio(overlay["rotulo"], f"{onde}.rotulo")


# --------------------------------------------------------------------------
# Avaliador fechado da fórmula (G3): `ast.parse` + caminhada explícita sobre
# nós permitidos -- nunca `eval`/`exec` (o teste de fronteira da 5A bane os
# dois em qualquer forma, `tests/test_relatorio_fronteira.py`). Gramática:
# `+ - * /` binários, menos unário, `Name` (campo do dataset), `Constant`
# numérica, parênteses (o parser já resolve agrupamento -- não é um nó à
# parte). Qualquer outro nó (Call, Attribute, Subscript, Compare, BoolOp,
# Lambda, comprehension...) é recusado ANTES de qualquer avaliação --
# whitelist, nunca blacklist de nome perigoso.
# --------------------------------------------------------------------------

_NOS_PERMITIDOS: tuple = (
    ast.Expression, ast.BinOp, ast.UnaryOp, ast.Name, ast.Constant, ast.Load,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.USub,
)


def _validar_nos(arvore: ast.AST, expr: str) -> None:
    for no in ast.walk(arvore):
        if not isinstance(no, _NOS_PERMITIDOS):
            raise FormulaInvalida(
                f"operação não permitida na fórmula '{expr}': {type(no).__name__} "
                "(só '+ - * /', menos unário, nomes de campo, números e parênteses são aceitos)."
            )


def _avaliar_no(no: ast.AST, ambiente: dict) -> float:
    """Avalia `no` (já confirmado, por `_validar_nos`, como só contendo nós
    da gramática fechada) contra `ambiente` (nome de campo -> valor NUMÉRICO
    deste ponto). Nunca chama `eval`/`exec`."""
    if isinstance(no, ast.Expression):
        return _avaliar_no(no.body, ambiente)
    if isinstance(no, ast.Constant):
        if isinstance(no.value, bool) or not isinstance(no.value, (int, float)):
            raise FormulaInvalida(f"constante não numérica na fórmula: {no.value!r}.")
        return float(no.value)
    if isinstance(no, ast.Name):
        if no.id not in ambiente:
            raise FormulaInvalida(f"nome fora dos campos do dataset: '{no.id}'.")
        return float(ambiente[no.id])
    if isinstance(no, ast.UnaryOp):
        return -_avaliar_no(no.operand, ambiente)
    if isinstance(no, ast.BinOp):
        esquerda = _avaliar_no(no.left, ambiente)
        direita = _avaliar_no(no.right, ambiente)
        if isinstance(no.op, ast.Add):
            return esquerda + direita
        if isinstance(no.op, ast.Sub):
            return esquerda - direita
        if isinstance(no.op, ast.Mult):
            return esquerda * direita
        try:
            return esquerda / direita
        except ZeroDivisionError as erro:
            raise FormulaInvalida("divisão por zero na fórmula.") from erro
    raise FormulaInvalida(f"nó não suportado na fórmula: {type(no).__name__}.")  # pragma: no cover


def _exigir_campos_paralelos_e_numericos(expr: str, campos: dict, nomes_usados: list[str]) -> None:
    """B3 (onda de correção da revisão final, achado F6, casos a e b): os
    campos que a fórmula REFERENCIA têm de ser paralelos (mesmo
    comprimento) e conter só número finito. Sem isto, duas entradas que o
    contrato aceita derrubavam o builder com traceback cru e rc 1, sem
    `qc.json` nenhum -- contradizendo o que o docstring de `builder.py`
    promete para o código 1:

    - comprimentos diferentes: `tamanho` saía do PRIMEIRO campo em ordem
      alfabética e o acesso ao índice estourava `IndexError` no campo mais
      curto;
    - `null` num campo lido pela fórmula: `float(None)` -> `TypeError`.

    O segundo é o mais provável e o mais feio: o cabeçalho de `graficos.js`
    documenta `null` como "o jeito natural de um dataset marcar ponto
    ausente", e uma série `direta` com `null` emite normalmente (travessão
    no gráfico, rc 0) -- só a `derivada` estourava. A assimetria de
    COMPORTAMENTO continua (a `direta` tolera, a `derivada` recusa: uma
    fórmula sobre ausência não tem resultado defensável), mas agora a
    `derivada` recusa PELO NOME (`formula_invalida`, HARD FAIL, código de QC
    que já existia), com `qc.json` emitido, em vez de derrubar o processo.
    """
    if not nomes_usados:
        return
    tamanhos = {nome: len(campos[nome]) for nome in nomes_usados}
    if len(set(tamanhos.values())) > 1:
        detalhe = ", ".join(f"'{nome}' ({tamanhos[nome]})" for nome in nomes_usados)
        raise FormulaInvalida(
            f"campos de comprimentos diferentes na fórmula '{expr}': {detalhe} — "
            "uma fórmula só pode combinar campos paralelos do mesmo dataset."
        )
    for nome in nomes_usados:
        for indice, valor in enumerate(campos[nome]):
            if isinstance(valor, bool) or not isinstance(valor, (int, float)) or not math.isfinite(valor):
                raise FormulaInvalida(
                    f"campo '{nome}' tem valor não numérico/não finito no índice {indice} "
                    f"({valor!r}) e a fórmula '{expr}' o referencia — um ponto ausente "
                    "('null') é legítimo numa série 'direta' (vira travessão no gráfico), "
                    "nunca numa fórmula."
                )


def avaliar_formula(expr: str, campos: dict) -> list[float]:
    """Avalia `expr` (gramática fechada acima) uma vez por índice dos
    campos referenciados, devolvendo a lista de resultados. `campos`: dict
    completo do dataset (`dados[<id>]["campos"]") — nomes não referenciados
    por `expr` são ignorados; qualquer nome QUE `expr` referencia e não
    está em `campos` é `FormulaInvalida` (nomeando o nome).

    Levanta `FormulaInvalida` para: sintaxe fora da gramática fechada
    (inclusive qualquer coisa que não seja uma única expressão), nó fora do
    whitelist, nome fora dos campos do dataset, campos referenciados de
    comprimentos diferentes ou com elemento não numérico/não finito (B3,
    achado F6 -- ver `_exigir_campos_paralelos_e_numericos`), ou resultado
    não finito (`nan`/`inf`, inclusive divisão por zero) em qualquer índice.
    """
    if not isinstance(expr, str) or not expr.strip():
        raise FormulaInvalida(f"fórmula ausente ou vazia: {expr!r}.")
    try:
        arvore = ast.parse(expr, mode="eval")
    except SyntaxError as erro:
        raise FormulaInvalida(f"sintaxe inválida na fórmula '{expr}': {erro}.") from erro

    _validar_nos(arvore, expr)

    nomes_usados = sorted({no.id for no in ast.walk(arvore) if isinstance(no, ast.Name)})
    for nome in nomes_usados:
        if not isinstance(campos, dict) or nome not in campos or not isinstance(campos[nome], list):
            raise FormulaInvalida(f"nome fora dos campos do dataset: '{nome}' (fórmula '{expr}').")

    _exigir_campos_paralelos_e_numericos(expr, campos, nomes_usados)

    tamanho = len(campos[nomes_usados[0]]) if nomes_usados else 1
    resultado: list[float] = []
    for indice in range(tamanho):
        ambiente = {nome: campos[nome][indice] for nome in nomes_usados}
        valor = _avaliar_no(arvore, ambiente)
        if not math.isfinite(valor):
            raise FormulaInvalida(f"resultado não finito na fórmula '{expr}' (índice {indice}): {valor!r}.")
        resultado.append(valor)
    return resultado


# --------------------------------------------------------------------------
# Resolução (rastreabilidade/QC + produção). `resolver_serie`/
# `resolver_overlay` são o ÚNICO lugar que decide se uma série/overlay é
# rastreável -- usadas tanto por `resolver()` (caminho de produção, deixa a
# exceção propagar) quanto por `qc.py` (captura por item, acumula todo
# achado da entrega inteira, nunca para no primeiro).
# --------------------------------------------------------------------------

def _checar_tamanho(valores: Any, dataset: dict, exhibit_id: str, indice: int, onde: str) -> None:
    """`serie_de_tamanho_incompativel`: só se aplica a série cujo valor é
    uma LISTA resolvida contra um dataset com `x` também lista (série
    `direta`/`derivada` sempre; `engine` nunca -- não tem dataset/x
    próprios, ver o docstring do módulo)."""
    x = dataset.get("x") if isinstance(dataset, dict) else None
    if isinstance(valores, list) and isinstance(x, list) and len(valores) != len(x):
        raise SerieInvalida("serie_de_tamanho_incompativel", onde, {
            "exhibit": exhibit_id, "serie": indice,
            "tamanho_serie": len(valores), "tamanho_x": len(x),
        })


def _e_numero_finito(valor: Any) -> bool:
    return isinstance(valor, (int, float)) and not isinstance(valor, bool) and math.isfinite(valor)


def _dataset_id_da_serie(serie: dict) -> str | None:
    """O id do dataset que uma série `direta`/`derivada` referencia (`None`
    para `engine`, que não usa dataset). Não valida nada: só extrai."""
    derivacao = serie.get("derivacao")
    fonte = serie.get("fonte")
    if not isinstance(fonte, str) or not fonte.strip():
        return None
    if derivacao == "direta":
        return fonte.partition(".")[0]
    if derivacao == "derivada":
        return fonte
    return None


def datasets_do_exhibit(exhibit: dict, dados: dict) -> list[str]:
    """Ids de dataset que as séries de `exhibit` referenciam, na ordem de
    primeira aparição e sem repetição -- o que `render.py` usa para decidir
    se um rótulo de série precisa do id do dataset para desambiguar (B1b)."""
    vistos: list[str] = []
    for serie in exhibit.get("series") or []:
        dataset_id = _dataset_id_da_serie(serie)
        if dataset_id is not None and dataset_id in (dados or {}) and dataset_id not in vistos:
            vistos.append(dataset_id)
    return vistos


def checar_datasets_do_exhibit(exhibit: dict, dados: dict) -> None:
    """`series_de_datasets_incompativeis` (HARD FAIL) -- B1 (achado F3): duas
    séries do MESMO exhibit não podem vir de datasets cujo `x` difere.

    `serie_de_tamanho_incompativel` compara cada série com o `x` DO SEU
    PRÓPRIO dataset, nunca as séries entre si: um exhibit com uma série de
    `fin` (x = anos 2021..2024) e outra de `peers` (x = ALFA..DELTA, mesmo
    comprimento) era perfeitamente "rastreável" pela regra e saía com rc 0 e
    `achados: []` -- com as margens dos PARES plotadas contra os ANOS, e as
    duas séries com o mesmo rótulo de legenda. Um gráfico assim não é um
    gráfico degradado: é um gráfico errado, emitido em silêncio.

    Compara o `x` de cada dataset com o do PRIMEIRO referenciado (a lista é
    pequena e a mensagem nomeia os dois lados). Dataset ausente/sem `x` não
    é assunto desta regra -- `serie_nao_rastreavel` já cobre."""
    ids = datasets_do_exhibit(exhibit, dados)
    if len(ids) < 2:
        return
    primeiro = ids[0]
    x_primeiro = (dados[primeiro] or {}).get("x")
    for outro in ids[1:]:
        x_outro = (dados[outro] or {}).get("x")
        if x_outro != x_primeiro:
            exhibit_id = exhibit["id"]
            raise SerieInvalida("series_de_datasets_incompativeis", f"analise.exhibits.{exhibit_id}", {
                "exhibit": exhibit_id, "dataset_a": primeiro, "dataset_b": outro,
                "x_a": _resumo_de_eixo(x_primeiro), "x_b": _resumo_de_eixo(x_outro),
            })


def _resumo_de_eixo(x: Any) -> str:
    if not isinstance(x, list):
        return repr(x)
    if len(x) <= 4:
        return repr(x)
    return f"[{x[0]!r}, ..., {x[-1]!r}] ({len(x)} pontos)"


def resolver_serie(exhibit: dict, indice: int, serie: dict, dados: dict, resultados: dict) -> tuple[Any, dict]:
    """Resolve a `indice`-ésima série de `exhibit["series"]` em número(s);
    devolve `(valores, entrada_de_log)`. Levanta `SerieInvalida`
    (`serie_nao_rastreavel`, `formula_invalida` ou
    `serie_de_tamanho_incompativel`) quando não é possível.

    `derivada` (G3 corrigido): `fonte` é sempre revalidada aqui, mesmo já
    sendo chave obrigatória no contrato (código 1) -- este módulo é
    chamado tanto pelo caminho de produção quanto pelo QC (que acumula
    achado sobre entregas construídas direto em teste, sem passar por
    `entrega.carregar`/`validar_exhibits`, ver `test_relatorio_exhibits.py`).
    Três causas distintas de `serie_nao_rastreavel`, nunca um fallback:
    `fonte` ausente, `fonte` com ponto (sintaxe de `direta`, usada por
    engano) ou `fonte` nomeando um dataset que não existe."""
    exhibit_id = exhibit["id"]
    onde = f"analise.exhibits.{exhibit_id}.series.{indice}"
    derivacao = serie["derivacao"]

    if derivacao == "direta":
        fonte = serie["fonte"]
        dataset_id, ponto, campo = fonte.partition(".")
        dataset = dados.get(dataset_id) if (ponto and isinstance(dados, dict)) else None
        campos = dataset.get("campos") if isinstance(dataset, dict) else None
        if not isinstance(campos, dict) or campo not in campos:
            raise SerieInvalida("serie_nao_rastreavel", onde, {
                "exhibit": exhibit_id, "serie": indice, "referencia": fonte,
                "razao": f"'{fonte}' não resolve em entrega.dados (dataset ou campo ausente).",
            })
        valores = campos[campo]
        _checar_tamanho(valores, dataset, exhibit_id, indice, onde)
        return valores, {"exhibit": exhibit_id, "serie": indice, "origem": "direta", "detalhe": fonte}

    if derivacao == "derivada":
        formula = serie["formula"]
        fonte = serie.get("fonte")
        if not isinstance(fonte, str) or not fonte.strip():
            raise SerieInvalida("serie_nao_rastreavel", onde, {
                "exhibit": exhibit_id, "serie": indice, "referencia": "(fonte ausente)",
                "razao": "série 'derivada' sem 'fonte' -- o id do dataset é obrigatório (G3).",
            })
        if "." in fonte:
            raise SerieInvalida("serie_nao_rastreavel", onde, {
                "exhibit": exhibit_id, "serie": indice, "referencia": fonte,
                "razao": (f"'fonte' de uma série 'derivada' é só o id do dataset, sem campo -- "
                          f"'{fonte}' tem um '.' (essa é a sintaxe de 'direta')."),
            })
        dataset = dados.get(fonte) if isinstance(dados, dict) else None
        campos = dataset.get("campos") if isinstance(dataset, dict) else None
        if not isinstance(campos, dict):
            raise SerieInvalida("serie_nao_rastreavel", onde, {
                "exhibit": exhibit_id, "serie": indice, "referencia": fonte,
                "razao": f"'{fonte}' não é um dataset em entrega.dados.",
            })
        try:
            valores = avaliar_formula(formula, campos)
        except FormulaInvalida as erro:
            raise SerieInvalida("formula_invalida", onde, {
                "exhibit": exhibit_id, "serie": indice, "formula": formula, "razao": str(erro),
            }) from erro
        _checar_tamanho(valores, dataset, exhibit_id, indice, onde)
        return valores, {"exhibit": exhibit_id, "serie": indice, "origem": "derivada",
                          "detalhe": f"{fonte}: {formula}"}

    # derivacao == "engine" (única terceira opção -- validar_exhibits já
    # recusou qualquer outro valor no contrato, código 1, antes do QC rodar).
    chave = serie["chave"]
    prefixo = "resultados:"
    if not chave.startswith(prefixo):
        raise SerieInvalida("serie_nao_rastreavel", onde, {
            "exhibit": exhibit_id, "serie": indice, "referencia": chave,
            "razao": "série 'engine' só lê de 'resultados:<caminho>'.",
        })
    caminho = chave[len(prefixo):]
    try:
        valor = placeholders._resolver_caminho(resultados, caminho)
    except placeholders.CaminhoInvalido as erro:
        raise SerieInvalida("serie_nao_rastreavel", onde, {
            "exhibit": exhibit_id, "serie": indice, "referencia": chave, "razao": str(erro),
        }) from erro

    # B2 (achado F5): uma série é NÚMERO, sempre -- a mesma checagem que
    # `resolver_overlay` já fazia e que faltava só aqui. Antes desta
    # correção o ramo `engine` devolvia o que viesse: um dict do motor
    # inteiro (`resultados:origem.metodologia`) ou um texto
    # (`resultados:rota`) entravam no payload como série, rc 0 e QC limpo,
    # e o exhibit caía no fallback textual no browser -- degradava, em vez
    # de dizer "não rastreável", que é o que o contrato manda.
    if not (_e_numero_finito(valor)
            or (isinstance(valor, list) and all(_e_numero_finito(v) for v in valor))):
        raise SerieInvalida("serie_nao_rastreavel", onde, {
            "exhibit": exhibit_id, "serie": indice, "referencia": chave,
            "razao": (f"valor não numérico/finito: {valor!r} — uma série 'engine' tem de "
                      "resolver num número finito ou numa lista de números finitos."),
        })
    return valor, {"exhibit": exhibit_id, "serie": indice, "origem": "engine", "detalhe": chave}


def resolver_overlay(exhibit: dict, indice: int, overlay: dict, resultados: dict, caso: dict) -> tuple[float, dict]:
    """Resolve a `indice`-ésima entrada de `exhibit["overlays"]` num único
    número; devolve `(valor, entrada_de_log)`. Levanta `SerieInvalida`
    (`overlay_nao_resolvido`) quando a `chave` não resolve num número finito."""
    exhibit_id = exhibit["id"]
    onde = f"analise.exhibits.{exhibit_id}.overlays.{indice}"
    chave = overlay["chave"]
    namespace, ponto, caminho = chave.partition(":")
    fontes = {"caso": caso, "resultados": resultados}
    fonte = fontes.get(namespace) if ponto else None
    if fonte is None:
        raise SerieInvalida("overlay_nao_resolvido", onde, {
            "exhibit": exhibit_id, "overlay": indice, "chave": chave,
            "razao": "namespace tem de ser 'caso:' ou 'resultados:'.",
        })
    try:
        bruto = placeholders._resolver_caminho(fonte, caminho)
    except placeholders.CaminhoInvalido as erro:
        raise SerieInvalida("overlay_nao_resolvido", onde, {
            "exhibit": exhibit_id, "overlay": indice, "chave": chave, "razao": str(erro),
        }) from erro
    if not isinstance(bruto, (int, float)) or isinstance(bruto, bool) or not math.isfinite(bruto):
        raise SerieInvalida("overlay_nao_resolvido", onde, {
            "exhibit": exhibit_id, "overlay": indice, "chave": chave,
            "razao": f"valor não numérico/finito: {bruto!r}.",
        })
    return float(bruto), {"exhibit": exhibit_id, "serie": indice, "origem": namespace, "detalhe": caminho}


def resolver(entrega: dict) -> tuple[list[dict], list[dict]]:
    """Resolve TODOS os exhibits de `entrega["analise"]["exhibits"]` em
    números — caminho de PRODUÇÃO (Task 2/3 chamam isto depois que
    `qc.avaliar` já confirmou zero HARD FAIL sobre a mesma entrega; ver
    `qc._achados_exhibits`, que roda a MESMA resolução item a item para
    ACUMULAR todo problema em vez de parar no primeiro). Numa entrega que o
    QC já aprovou nada aqui deveria levantar — mas continua podendo
    levantar `SerieInvalida`/`FormulaInvalida`, em vez de mascarar um
    problema real, se chamada sem QC prévio.

    Devolve `(exhibits_resolvidos, log)`: `exhibits_resolvidos` é
    `entrega["analise"]["exhibits"]`, com cada série ganhando `"valores"` e
    cada overlay ganhando `"valor"`; `log` é uma entrada por série/overlay
    resolvida (G8), na ordem em que os exhibits/séries/overlays aparecem.
    """
    analise = entrega.get("analise") or {}
    exhibits_decl = analise.get("exhibits") or []
    dados = entrega.get("dados") or {}
    resultados = entrega.get("resultados") or {}
    caso = entrega.get("caso") or {}

    exhibits_resolvidos: list[dict] = []
    log: list[dict] = []

    for exhibit in exhibits_decl:
        checar_datasets_do_exhibit(exhibit, dados)
        series_resolvidas = []
        for indice, serie in enumerate(exhibit.get("series", [])):
            valores, entrada = resolver_serie(exhibit, indice, serie, dados, resultados)
            series_resolvidas.append({**serie, "valores": valores})
            log.append(entrada)

        exhibit_resolvido = dict(exhibit)
        exhibit_resolvido["series"] = series_resolvidas

        if "overlays" in exhibit:
            overlays_resolvidos = []
            for indice, overlay in enumerate(exhibit["overlays"]):
                valor, entrada = resolver_overlay(exhibit, indice, overlay, resultados, caso)
                overlays_resolvidos.append({**overlay, "valor": valor})
                log.append(entrada)
            exhibit_resolvido["overlays"] = overlays_resolvidos

        exhibits_resolvidos.append(exhibit_resolvido)

    return exhibits_resolvidos, log
