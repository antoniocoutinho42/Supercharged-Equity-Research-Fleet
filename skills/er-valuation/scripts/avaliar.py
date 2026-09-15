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
- rota rampa (Fatia C, Task 1): o motor recebe `--nd/--acoes` e faz a
  composição bifásica inteira internamente (fase 1 rampa de utilização +
  fase 2 expansão, costuradas no ano `--t-rampa`) — `EV`, `Equity` e
  `Preco_acao` saem prontos do motor, usados aqui verbatim, como no ramo
  EBITDA da rota firm. A saída do subcomando `rampa` não tem o mesmo shape
  de `ev`/`pe` (não carrega `diagnosticos`/`coerencia_vetor`/
  `convencao_temporal`); por isso `precificar_rampa` e a composição do
  cenário rampa não reaproveitam `_monta_cenario`, que presume esse shape.
  É também a única rota cujo cenário NÃO declara `triangulo` — e a isenção
  tem razão, não é esquecimento: a regra do triângulo existe para que a
  taxa de reinvestimento nunca fique silenciosa ("cenário com RiR
  silencioso é cenário opaco"), e nesta rota o próprio motor a reporta por
  fase (`rir_fase1_%`, que varia ano a ano e por isso não tem vetor único,
  e `rir2_%`). O propósito da regra é atendido por construção; exigir a
  declaração duplicaria o que o motor já entrega.

`caso["moeda"]` é sempre repassado ao motor como `--moeda` (nas duas rotas) —
`caso.py` já exige e valida esse campo; sem repassá-lo, toda saída carregava
o aviso falso do motor de moeda/regime não declarados, causado pelo wrapper.

Fatia B, Task 4: a lógica de escala acima — decidir o caminho por
rota/métrica, chamar o motor, recusar `null` — está isolada em
`precificar_firm`/`precificar_equity`, que tomam um vetor de premissas
qualquer (não só o vetor central de um cenário declarado). `avaliar()`
continua o único lugar que lê `EV`/`Equity`/`algebra`; `sensibilidades.py`
reusa as mesmas duas funções, célula a célula, para preço por ação e o
múltiplo de referência — nunca uma segunda cópia desta lógica. As duas
aceitam `moeda=None` por default (o mesmo default de `motor.rodar`), mas
`avaliar()` e `sensibilidades.py` sempre passam `caso["moeda"]`
explicitamente — a mesma disciplina nos dois lugares, para que nenhuma
saída (cenário principal ou célula de grade) carregue o alarme falso
"MOEDA/REGIME NÃO DECLARADOS" (ver docstring de `sensibilidades.py`).

Fatia B, Task 5: os blocos `reversa` (menu de reconciliação por eixo,
`reversa.reverter`) e `sensibilidades` (grades 1D/2D célula a célula,
`sensibilidades.calcular`) entram no resultado só quando o caso os declara
— `"reversa" in caso`/`"sensibilidades" in caso`, checado depois que
`cenarios` já está montado. Nenhuma conta de valuation nova: os dois
módulos já fazem toda a aritmética que a metodologia autoriza (o alvo de
múltiplo de mercado, o beta implícito); `avaliar()` só decide QUANDO
chamá-los e com que `nd_efetivo`. Na rota firm, é o mesmo `nd_efetivo` que
`precificar_firm` já usa (`ponte["nd_efetivo"]`); na rota equity não há
ponte de dívida — `nd_efetivo` é `0.0`, e é assim que `reversa.
alvo_de_mercado` sabe usar `base="pl"` em vez de somar dívida a um EV que,
do lado equity, nunca existe. Um caso sem os dois blocos (toda fixture da
fatia A) não sofre nenhuma mudança de shape: os dois `if` abaixo são
no-op, e o resultado sai byte a byte igual ao que saía antes desta fatia.

Fatia C, Task 4: o bloco `sotp` entra no resultado com a MESMA disciplina
aditiva dos dois blocos acima — `"sotp" in caso`, checado depois deles —
via `sotp.compor_partes(caso, caso["sotp"]["cenario"])`, sem filtrar nem
reformatar o que `compor_partes` devolve (`partes`, `ev_das_partes`,
`materialidade`, `topo`, `ev_total`, `equity`, `preco_acao`,
`ponte_unica`). Diferente de `reverter`/`calcular`, não recebe
`nd_efetivo`: `compor_partes` cruza a própria ponte do caso internamente,
uma única vez, no topo (D3). Duas guardas de `caso.py` fecham os achados
da revisão da Task 3 antes que este módulo precise se preocupar com eles:
um caso com `sotp` declarado na rota equity é recusado no gate (SOTP soma
EV; a rota equity não produz EV nem admite `ponte`) — sem essa recusa
nomeada, a combinação alcançaria `compor_partes` e quebraria fundo, em
`KeyError` sobre `caso["ponte"]`, nunca uma mensagem para o analista; e
`sotp.cenario` (contrato novo desta task, mesma semântica de
`reversa.cenario`/`sensibilidades.cenario`) já chega validado como um
nome que existe em `caso["cenarios"]`. Um caso sem `sotp` (toda fixture
das fatias A e B, e a própria fixture de rampa desta fatia) não sofre
nenhuma mudança de shape: o `if` abaixo é no-op, e o resultado sai byte a
byte igual ao que saía antes.

Todo valor que este módulo lê ou copia da saída do motor (`EV`, `Equity`,
`Preco_acao`, o múltiplo do ramo NOPAT, os múltiplos copiados para a saída)
passa por `_exigir_valor`: o serializador do motor converte float não-finito
em `null` e sai com código 0 mesmo assim — um `null` aqui vira `MotorFalhou`
nomeando o campo, nunca um valor inventado nem um `null` silencioso dentro de
`resultados.json`.

A saída é determinística: função pura do `caso` recebido, sem hora de
execução, caminho absoluto ou qualquer valor do ambiente. A data que aparece
no resultado é `data_analise`, do próprio caso.
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

import diagnosticos
from caso import CasoInvalido, _tv_canon, carregar, reversa_indisponivel
from motor import MotorFalhou, _campo_do_multiplo, _exigir_valor, rodar
from ponte import compor
from reversa import alvo_de_mercado, limitacoes_da_leitura, reverter

# `sensibilidades.calcular` NÃO entra aqui em cima: `sensibilidades.py` faz
# `from avaliar import precificar_equity, precificar_firm` no topo dela — um
# `from sensibilidades import calcular` neste ponto do arquivo criaria um
# ciclo (avaliar -> sensibilidades -> avaliar) resolvido ANTES de
# `precificar_firm`/`precificar_equity` existirem no namespace deste módulo,
# e o import quebraria com "cannot import name ... from partially
# initialized module". `reversa.py` não tem esse problema (não importa
# `avaliar`), por isso `reverter` é import de topo normal. O import de
# `calcular` é feito dentro de `avaliar()`, na hora de usar — ver ali.

# --------------------------------------------------------------------------
# Fatia 5A, item 5, Task 1: contrato `resultados/1` (E3, amendment do
# desenho v4 §15) — `versao_contrato`, `origem` (regra 2), `manchete`
# (regra 3/A4), `mercado_tela` (regra 4) e `diagnosticos_chaves` (regra 5,
# aplicada dentro de `_monta_cenario`/`_monta_cenario_rampa` abaixo).
# Fatia 5D, Task 1: `fronteira_de_escopo` e `limitacoes`, sempre publicados
# (fim de `avaliar`).
# --------------------------------------------------------------------------

# Versão do contrato publicado — acréscimos compatíveis (campo novo, nunca
# removido nem com semântica trocada) não mudam este literal; uma mudança
# incompatível vira "resultados/2". Fixo, não derivado de nada — é este
# módulo que DECLARA a versão do contrato que produz.
VERSAO_CONTRATO: str = "resultados/1"

# `origem.metodologia` (regra 2): lido do manifesto do vendor, nunca
# hardcoded — trocar o pacote e regenerar o manifesto (a única forma
# suportada de evoluir a metodologia, `manifest_vendor.json:"regenerar"`)
# already muda o que este módulo publica, sem precisar tocar aqui. Mesmo
# padrão de `RAIZ_VENDOR` em `motor.py`: lido uma vez, no import.
_CAMINHO_MANIFEST_VENDOR = (
    Path(__file__).resolve().parents[3] / "skills" / "er-multiplos-justos" / "manifest_vendor.json"
)
_MANIFEST_VENDOR: dict = json.loads(_CAMINHO_MANIFEST_VENDOR.read_text(encoding="utf-8"))


def _sha256_canonico(obj: dict) -> str:
    """SHA-256 do JSON canônico de `obj` (A2, decisão do plano da fatia 5A).

    Canonicalização: `sort_keys=True`, `separators=(",", ":")`,
    `ensure_ascii=False`, utf-8 — reordenar chaves ou mudar espaçamento do
    `caso.json` de origem não muda o hash. `er-relatorio` (fatia 5A, Task
    3) recalcula esta MESMA receita sobre o caso que recebe, para provar
    correspondência com `origem.caso_sha256` sem rodar nada — a
    canonicalização é contrato documentado nos dois lados; duplicar estas
    poucas linhas é o preço de o relatório nunca importar este módulo
    (E3, `docs/desenho-arquitetura-v4.md` §15).
    """
    canonico = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonico.encode("utf-8")).hexdigest()


def _nome_cenario_base(caso: dict) -> str:
    """Nome do cenário-base (A3): `caso['cenario_base']` quando declarado,
    ou o único cenário do caso quando `caso.validar` já confirmou (no
    gate, `_validar_cenario_base`) que só existe um. Esta função não
    revalida nada disso — só lê a mesma decisão que o gate já travou.
    """
    declarado = caso.get("cenario_base")
    if declarado is not None:
        return declarado
    (unico,) = caso["cenarios"]
    return unico


def _chave_e_base_do_multiplo(rota: str, tipo_metrica: str) -> tuple[str, str]:
    """Chave (campo de `multiplos`) e `base` (rótulo curto, regra 3/4) do
    múltiplo de referência da rota — usado por `manchete` e `mercado_tela`
    para nomear qual múltiplo pareia com qual preço.

    Espelha `motor._campo_do_multiplo`, generalizado para cobrir também a
    rota `rampa` — que aquele helper não cobre porque nenhum call site
    dele hoje o chama com `rota="rampa"` (`precificar_rampa` lê
    'EV/EBITDA0' direto de `_exigir_valor`; a reversa recusa 'rampa' no
    gate, então `reversa.teto_do_crescimento_gratuito`, o único outro
    chamador de `_campo_do_multiplo`, nunca roda para essa rota). Vive
    aqui, não em `motor.py`, para não mudar o contrato de um helper
    compartilhado por um motivo que só a manchete/o múltiplo de tela têm.

    Rota firm: `EV/EBITDA_curr`/`"ebitda"` quando `tipo_metrica ==
    "EBITDA"`, `EV/NOPAT_curr`/`"nopat"` caso contrário — mesma dicotomia
    de `precificar_firm`. Rota rampa: sempre `EV/EBITDA0`/`"ebitda0"` — o
    headline da rota (`caso.METRICAS_POR_ROTA["rampa"] == {"EBITDA0"}`,
    nunca uma escolha a fazer aqui). Rota equity: sempre `PL_curr`/`"pl"`.
    Rota desconhecida levanta `ValueError` — mesma disciplina de
    `reversa.alvo_de_mercado`, nunca alcançável por um caso validado.
    """
    if rota == "firm":
        if tipo_metrica == "EBITDA":
            return "EV/EBITDA_curr", "ebitda"
        return "EV/NOPAT_curr", "nopat"
    if rota == "rampa":
        return "EV/EBITDA0", "ebitda0"
    if rota == "equity":
        return "PL_curr", "pl"
    raise ValueError(f"rota desconhecida para múltiplo de referência: {rota!r}")


def _chave_e_base_do_multiplo_forward(rota: str, tipo_metrica: str) -> tuple[str, str] | None:
    """Fatia 5F, Task 2 (D5): chave (campo de `multiplos`) e `base` do múltiplo
    FORWARD de referência da rota — o par forward de `_chave_e_base_do_multiplo`,
    que o motor já publica em `cenarios.*.multiplos`, com a mesma `base` do
    corrente. A rota rampa não tem forward: o headline dela é EV/EBITDA do ano 0
    (`None`). Rota desconhecida levanta `ValueError`, a mesma disciplina."""
    if rota == "firm":
        if tipo_metrica == "EBITDA":
            return "EV/EBITDA_fwd", "ebitda"
        return "EV/NOPAT_fwd", "nopat"
    if rota == "equity":
        return "PL_fwd", "pl"
    if rota == "rampa":
        return None
    raise ValueError(f"rota desconhecida para múltiplo forward de referência: {rota!r}")


def _montar_manchete(caso: dict, resultado: dict) -> dict:
    """Monta o campo `manchete` (A4, regra 3): qual preço é "a resposta".

    Com `sotp` declarado, a manchete é o preço do SOTP — soma de partes é
    a composição mais completa que o caso oferece, e não carrega UM único
    múltiplo de referência (cada parte tem o seu, em bases possivelmente
    diferentes) — por isso não tem `multiplo`, nem `convencao_terminal`: as
    partes podem divergir de convenção entre si (`caso_sotp_segmento.json`
    mistura 'convergencia' e 'gordon' entre as duas partes — ver
    `tests/test_valuation_sotp.py::test_cada_parte_e_avaliada_com_a_propria_convencao`),
    então publicar UMA convenção aqui seria o wrapper escolhendo por elas.

    Sem `sotp`, a manchete é o preço do cenário-base (A3): `multiplo` é o
    mesmo que o wrapper já devolve para aquele preço — nunca uma conta
    nova, só um apontamento para um valor que já está em `resultado`.
    Num cenário com degrau aplicado (`"degrau" in cenario_base` — só
    possível na rota equity, `caso._validar_degrau`), o múltiplo é
    `PVP_com_degrau`/`"pvp"`, o `com_transicao` que o próprio degrau já
    calculou; sem degrau, é o múltiplo padrão da rota
    (`_chave_e_base_do_multiplo`), lido de `multiplos`, onde
    `_monta_cenario`/`_monta_cenario_rampa` já o deixaram validado.

    A1 (onda de correção da revisão final, achado F2): `convencao_terminal`
    é o código CANÔNICO (`_tv_canon`, o mesmo mapeamento que o motor aplica
    — 'ic'->'book', 'spread'->'gordon', identidade para as demais) da
    premissa 'tv' do cenário-base — nunca o literal que o caso declarou.
    Antes desta correção o relatório lia `caso...premissas.tv` cru e
    rotulava pelo literal: um alias legado ('ic'/'spread') passava pelo
    gate (que só exige a PRESENÇA de 'tv', nunca um valor específico — ver
    `caso._validar_premissas`) e pelo wrapper, e só quebrava no builder do
    relatório, tarde demais. Publicar o canônico aqui, uma vez, fecha o
    mesmo buraco para qualquer alias futuro sem o relatório precisar saber
    que alias existem — ele só lê um código já canônico e busca o rótulo em
    `catalogo.convencoes_terminais` (fonte única, Task 2/A1).
    """
    preco_valor = caso["preco"]["valor"]

    if "sotp" in caso:
        sotp_resultado = resultado["sotp"]
        preco_acao = sotp_resultado["preco_acao"]
        return {
            "fonte": "sotp",
            "cenario": sotp_resultado["cenario"],
            "preco_acao": preco_acao,
            "upside": preco_acao / preco_valor - 1,
        }

    nome_base = _nome_cenario_base(caso)
    cenario_base = resultado["cenarios"][nome_base]
    preco_acao = cenario_base["valor"]["preco_acao"]

    # Fatia 5F, Task 2 (D5): o múltiplo justo FORWARD da manchete, lido de
    # `multiplos` pela chave forward da rota — só fora do degrau e da rampa, que não
    # têm forward (o SOTP já saiu acima, sem múltiplo nenhum).
    multiplo_forward = None
    if "degrau" in cenario_base:
        multiplo = {
            "chave": "PVP_com_degrau",
            "base": "pvp",
            "valor": cenario_base["degrau"]["com_transicao"],
        }
    else:
        chave, base = _chave_e_base_do_multiplo(caso["rota"], caso["metrica_base"]["tipo"])
        multiplo = {"chave": chave, "base": base, "valor": cenario_base["multiplos"][chave]}
        par_forward = _chave_e_base_do_multiplo_forward(caso["rota"], caso["metrica_base"]["tipo"])
        if par_forward is not None:
            chave_forward, base_forward = par_forward
            multiplo_forward = {"chave": chave_forward, "base": base_forward,
                                "valor": _exigir_valor(cenario_base["multiplos"], chave_forward)}

    tv_declarado = caso["cenarios"][nome_base]["premissas"]["tv"]

    manchete = {
        "fonte": "cenarios",
        "cenario": nome_base,
        "preco_acao": preco_acao,
        "upside": preco_acao / preco_valor - 1,
        "multiplo": multiplo,
    }
    if multiplo_forward is not None:
        manchete["multiplo_forward"] = multiplo_forward
    manchete["convencao_terminal"] = _tv_canon(tv_declarado)
    return manchete


# Chaves de aviso da rampa, na ordem canônica (regra 5) — mesma tupla e
# mesma ordem que `vetores_solver.py`/`motor_espelho.js` já usam
# (`AVISOS_RAMPA`) para o mesmo propósito (só a PRESENÇA importa).
# Duplicada aqui, não importada de lá: `vetores_solver.py` é harness de
# paridade (não é dependência de produção), e este módulo não depende dele.
_AVISOS_RAMPA_ORDEM: tuple[str, ...] = ("aviso_colheita", "aviso_delator", "aviso_gp")

# Fatia 5C, item 5, Task 3 (T1): as CHAVES dos dois alertas do degrau. O
# handler `degrau` do motor publica `ALERTA`/`ALERTA_RiR` como prosa sem chave
# (a segunda ainda interpola o RiR), e `_aplicar_degrau_ao_cenario` a repassa
# verbatim, para auditoria. Dar chave a um alerta é trabalho desta camada, a que
# conhece o motor: se o relatório mapeasse "`ALERTA` dentro de `degrau`
# significa X", um v10 que renomeasse o campo quebraria o relatório — aqui,
# quebra a paridade da integração. `degrau.diagnosticos_chaves` é a lista, na
# ordem desta tupla, das chaves cujo campo o motor de fato emitiu no nível-alvo
# (só a PRESENÇA importa, mesmo padrão de `_AVISOS_RAMPA_ORDEM`).
# `motor_espelho.js` carrega a mesma tabela (`ALERTAS_DEGRAU`), e
# `tests/test_paridade_wrapper_js.py` compara as duas listas por igualdade exata.
_ALERTAS_DEGRAU_ORDEM: tuple[tuple[str, str], ...] = (
    ("ALERTA", "degrau_alerta"),
    ("ALERTA_RiR", "degrau_alerta_rir"),
)

# Onda de correção da revisão final da 5C (F1): a DIVERGÊNCIA DE BASE do degrau
# também vira chave — e o limiar que a decide mora AQUI, fonte numérica única.
# `divergencia_de_base_%` (D8, publicada desde a fatia D) mede quanto do
# incremento que o degrau parece criar vem do descasamento entre as duas bases
# (LL x ROE.VPA), e não do degrau. Até esta onda, "acima do limiar" era decidido
# pela QC do relatório contra um `limiar_pct` do catálogo de apresentação: uma
# decisão metodológica fora da integração (E3), e congelada no build — o
# laboratório movia o preço e o disclosure ficava onde estava (§8.4). Agora o
# wrapper publica `_CHAVE_DIVERGENCIA_DE_BASE` em `degrau.diagnosticos_chaves`,
# DEPOIS dos alertas do motor (o motor os emite no nível-alvo; a divergência é a
# comparação que esta camada faz em seguida), e a QC só a consome.
#
# Por que uma constante do wrapper, e não um número lido do catálogo: a mesma
# decisão tem de ser tomada no navegador, e o navegador não lê arquivo. Lido do
# catálogo, o limiar teria de viajar no payload que o RELATÓRIO monta — o
# relatório no caminho de uma regra. `motor_espelho.js` carrega a cópia
# (`LIMIAR_DIVERGENCIA_DE_BASE_PCT`), travada por igualdade contra esta em
# `tests/test_paridade_wrapper_js.py`; o catálogo ficou só com o texto do
# disclosure e o nome da chave que o dispara. O valor é o que o catálogo
# carregava desde a 5A (5%).
_LIMIAR_DIVERGENCIA_DE_BASE_PCT: float = 5.0
_CHAVE_DIVERGENCIA_DE_BASE: str = "degrau_divergencia_de_base"

# O vocabulário inteiro de `degrau.diagnosticos_chaves`, na ordem em que as
# chaves saem — DERIVADO das constantes que `_chaves_do_degrau` usa, para que a
# trava do catálogo (`tests/test_catalogo_apresentacao.py`) nunca dependa de uma
# lista escrita à mão.
_CHAVES_DO_DEGRAU_ORDEM: tuple[str, ...] = (
    tuple(chave for _campo, chave in _ALERTAS_DEGRAU_ORDEM) + (_CHAVE_DIVERGENCIA_DE_BASE,))

# Fatia 5F, Task 3 (D6): a CHAVE do alerta da conservação de capital (§11.1b). O motor
# publica `conservacao_capital.ALERTA` como prosa sem chave quando o gap passa do
# limiar DELE (10%, justos.py); dar a chave é trabalho desta camada, por presença — o
# padrão de `_ALERTAS_DEGRAU_ORDEM`. `motor_espelho.js:conservacaoCapital` toma a mesma
# decisão ao vivo, com a paridade presa em tests/test_paridade_wrapper_js.py.
_ALERTAS_DA_CONSERVACAO: tuple[tuple[str, str], ...] = (("ALERTA", "conservacao_capital_nao_fecha"),)
_CHAVES_DA_CONSERVACAO: tuple[str, ...] = tuple(chave for _campo, chave in _ALERTAS_DA_CONSERVACAO)


def _conservacao_publicada(saida_motor: dict, conservacao: dict) -> dict:
    """`cenarios.<n>.conservacao_capital` (fatia 5F, Task 3, D6): a saída do motor
    para a verificação da §11.1b, íntegra, mais `ano_base` (a declaração do caso) e
    `diagnosticos_chaves` (as chaves dos alertas presentes, na ordem de
    `_ALERTAS_DA_CONSERVACAO`).

    O motor devolve TEXTO no lugar do bloco ("NAO CHECAVEL...") quando falta
    `--capex-total`, `--dwc` ou `--ebitda` — inalcançável com o gate, e recusado aqui
    pelo nome, nunca publicado no lugar do bloco. `gap_%` passa por `_exigir_valor`:
    capital consumido nulo, ou retorno do capital novo nulo, vira `null` no motor."""
    bloco = saida_motor.get("conservacao_capital")
    if not isinstance(bloco, dict):
        raise MotorFalhou(
            f"motor não devolveu a conservação de capital como bloco: {bloco!r}. A identidade "
            "exige --capex-total, --dwc e --ebitda juntos; o wrapper não publica texto no lugar do "
            "bloco."
        )
    _exigir_valor(bloco, "gap_%")
    return {
        **bloco,
        "ano_base": conservacao["capex_total"]["ano_base"],
        "diagnosticos_chaves": [chave for campo, chave in _ALERTAS_DA_CONSERVACAO if campo in bloco],
    }


def _chaves_do_degrau(nivel_alvo: dict, divergencia_de_base_pct: float) -> list[str]:
    """`degrau.diagnosticos_chaves` de um cenário: as chaves dos alertas que o
    motor emitiu no nível-alvo (por presença, na ordem de
    `_ALERTAS_DEGRAU_ORDEM`) e, depois delas, a da divergência de base quando o
    MÓDULO passa do limiar — o descasamento contamina a leitura do incremento
    nos dois sentidos, com a base de LL acima ou abaixo de ROE.VPA."""
    chaves = [chave for campo, chave in _ALERTAS_DEGRAU_ORDEM if campo in nivel_alvo]
    if abs(divergencia_de_base_pct) > _LIMIAR_DIVERGENCIA_DE_BASE_PCT:
        chaves.append(_CHAVE_DIVERGENCIA_DE_BASE)
    return chaves


def _montar_mercado_tela(caso: dict, resultado: dict, nd_efetivo: float) -> dict:
    """Monta o campo `mercado_tela` (regra 4): o múltiplo de mercado
    (screen), SEMPRE publicado — antes só existia dentro do bloco
    `reversa`, condicionado à presença dele.

    Mesma `base` da manchete, por construção (as duas derivam de
    `caso["rota"]`/`caso["metrica_base"].tipo`, nunca do cenário
    escolhido) — EXCETO no degrau, onde a manchete usa o P/VP JUSTO
    (`PVP_com_degrau`, o `com_transicao` que o degrau calcula) e a tela
    usa o P/VP OBSERVADO (`preco / vpa`, os dois números crus do caso, sem
    passar pelo motor): o relatório pareia os dois pela `base` comum
    (`"pvp"`), nunca pela `chave` — que é deliberadamente diferente nesse
    caso (`"PVP"` de tela contra `"PVP_com_degrau"` justo).

    Fora do degrau, `valor`/`algebra` vêm de `reversa.alvo_de_mercado` —
    a MESMA função que o bloco opcional `reversa` já usa (regra inviolável
    1: nenhuma aritmética de valuation fora do motor/das funções que já a
    fazem); `chave` é só rótulo, resolvido por `_chave_e_base_do_multiplo`.
    """
    nome_base = _nome_cenario_base(caso)
    cenario_base = resultado["cenarios"][nome_base]

    if "degrau" in cenario_base:
        preco = caso["preco"]["valor"]
        vpa = caso["degrau"]["vpa"]["valor"]
        valor = preco / vpa
        return {
            "chave": "PVP",
            "base": "pvp",
            "valor": valor,
            "algebra": f"PVP_tela = preco {preco} / vpa {vpa} = {valor}",
        }

    chave, base = _chave_e_base_do_multiplo(caso["rota"], caso["metrica_base"]["tipo"])
    alvo = alvo_de_mercado(caso, nome_base, nd_efetivo)
    return {"chave": chave, "base": base, "valor": alvo["valor"], "algebra": alvo["algebra"]}


def _montar_mercado_tela_forward(caso: dict, nd_efetivo: float) -> dict | None:
    """Fatia 5F, Task 2 (D5): o múltiplo de tela FORWARD — `null` quando o caso não
    declara `metrica_forward`. É a conta de `mercado_tela` (`reversa.alvo_de_mercado`,
    a mesma função) com a métrica forward declarada no denominador: nunca uma
    segunda conta, nunca uma métrica escolhida pelo wrapper. O gate já recusou a
    métrica forward na rota rampa e junto de degrau, então a chave forward da rota
    sempre existe aqui. `metrica` repete a declaração com a proveniência (tipo,
    valor, período, fonte), para a tela citá-la."""
    metrica_forward = caso.get("metrica_forward")
    if metrica_forward is None:
        return None
    chave, base = _chave_e_base_do_multiplo_forward(caso["rota"], caso["metrica_base"]["tipo"])
    alvo = alvo_de_mercado(caso, _nome_cenario_base(caso), nd_efetivo, metrica_forward["valor"])
    return {
        "chave": chave,
        "base": base,
        "valor": alvo["valor"],
        "algebra": alvo["algebra"],
        "metrica": {campo: metrica_forward[campo] for campo in ("tipo", "valor", "periodo", "fonte")},
    }


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


# `_exigir_valor` e `_campo_do_multiplo` moraram aqui até a revisão final;
# viveram agora em `motor.py`, ao lado de `MotorFalhou` (FIX 1 e FIX 2): é o
# único módulo que `avaliar.py`, `reversa.py` e `sensibilidades.py`
# alcançam sem ciclo de import, então os três leem a mesma guarda e a mesma
# tradução rota/métrica → campo em vez de cada um manter cópia própria — a
# cópia dentro de `reversa.teto_do_crescimento_gratuito` era exatamente a
# que tinha divergido, perdendo a recusa de `null`. Este módulo continua
# importando os dois nomes (linha de import no topo do arquivo), só não os
# define mais.


def precificar_firm(premissas: dict, tipo_metrica: str, valor_metrica: float,
                     nd_efetivo: float | None = None, acoes: float | None = None,
                     moeda: str | None = None,
                     rf: float | None = None,
                     conservacao: dict | None = None) -> tuple[dict, dict, str, float]:
    """Roda o motor para um vetor de premissas da rota firm; devolve
    (saída, valor, álgebra, múltiplo de referência).

    Extraída do antigo `_cenario_firm` (Fatia B, Task 4) para ser
    reutilizável: mesma escolha de escala (EBITDA direto do motor vs.
    álgebra do ramo NOPAT) e mesma recusa de `null` via `_exigir_valor`,
    agora sobre um vetor de premissas qualquer — não só o vetor central de
    um cenário declarado em `caso["cenarios"]`. `avaliar()` continua o
    único lugar que lê `EV`/`Equity`/`algebra`; `sensibilidades.py` usa
    esta mesma função célula a célula, para `valor["preco_acao"]` e
    `multiplo`. Duplicar esta lógica numa segunda função seria abrir
    espaço para as duas divergirem — exatamente o que a metodologia
    proíbe (todo número vem do motor, pela mesma conta).

    `tipo_metrica` já chegou validado por `caso.py` como 'EBITDA' ou 'NOPAT'
    (as únicas métricas que `METRICAS_POR_ROTA["firm"]` aceita) — este ponto
    confia nisso e não trata um terceiro caso.

    `multiplo` é o múltiplo de referência da métrica-base, já validado por
    `_exigir_valor` sobre o campo que `_campo_do_multiplo("firm",
    tipo_metrica)` resolve (FIX 2, revisão final: `EV/EBITDA_curr` quando
    `tipo_metrica == "EBITDA"`, `EV/NOPAT_curr` caso contrário — a mesma
    tradução que `precificar_equity` e `reversa.teto_do_crescimento_gratuito`
    também leem de `motor.py`, em vez de cada um repetir a própria cópia).
    No ramo EBITDA é uma leitura adicional (o motor sempre devolve os
    múltiplos, mesmo com escala aplicada); no ramo NOPAT é o mesmo valor
    que a álgebra abaixo já usava, agora também devolvido ao chamador.

    `moeda` tem default `None` — o mesmo de `motor.rodar` — porque quem
    chama decide se passa `--moeda`: `avaliar()` e `sensibilidades.py`
    sempre passam `caso["moeda"]` (ver docstring do módulo e de
    `sensibilidades.py`).

    `rf` (correção do item 3) segue a mesma disciplina de `moeda`, último
    parâmetro para que toda chamada posicional existente continue
    funcionando sem tocar: `None` por default, repassado direto a
    `motor.rodar` nas duas chamadas abaixo. É `caso["mercado"]["rf"]`
    quando o caso declara o bloco `mercado`, `None` quando não — quem
    chama (`avaliar()`, `sensibilidades.py`, `sotp.py`) decide, do mesmo
    jeito que já decide `moeda`. Não entra em nenhuma conta deste módulo:
    só ativa a âncora macro do gp (Damodaran) nos `diagnosticos` que o
    motor devolve.

    Fatia C, Task 2: `nd_efetivo`/`acoes` ganharam default `None` — sinal de
    que quem chama não quer cruzar a ponte (uma parte de SOTP, por exemplo:
    D3 do plano da fatia C proíbe ponte por parte — "é o erro que a trava
    existe para impedir"). Com `nd_efetivo is None`, `valor` só tem `"EV"`
    (nunca `"Equity"`/`"preco_acao"` — as duas chaves que uma ponte
    cruzada produziria): no ramo EBITDA a escala passada ao motor leva só
    `ebitda` (sem `nd`/`acoes` — o motor devolve `EV` e os múltiplos
    normalmente; `Equity`/`Preco_acao` saem ausentes, porque a ponte nunca
    foi informada — confirmado por sondagem direta do motor); no ramo
    NOPAT a chamada em si não muda (já rodava sem escala nenhuma), só o
    `valor` devolvido para de derivar `equity`/`preco_acao` da álgebra.
    Todo call site existente (`avaliar.py`, `sensibilidades.py`) sempre
    passa `nd_efetivo`/`acoes` explícitos — o default novo não muda
    nenhum comportamento pré-existente, só abre um caminho a mais.

    Fatia 5F, Task 3 (D6): `conservacao` é o bloco `conservacao_de_capital` do
    caso, ou `None`. Dado, o capex total e o ΔWC vão ao motor (`--capex-total`,
    `--dwc`), que publica `conservacao_capital` na saída — lido por
    `_conservacao_publicada`. Só o laço de cenários de `avaliar()` o passa: as
    células de grade, as partes de SOTP e o teto também precificam por esta
    função, e a verificação não é delas.
    """
    campo_multiplo = _campo_do_multiplo("firm", tipo_metrica)
    sem_ponte = nd_efetivo is None
    flags_da_conservacao = ({} if conservacao is None else
                            {"capex_total": conservacao["capex_total"]["valor"],
                             "dwc": conservacao["dwc"]["valor"]})
    if tipo_metrica == "EBITDA":
        escala = {"ebitda": valor_metrica}
        if not sem_ponte:
            escala["nd"] = nd_efetivo
            escala["acoes"] = acoes
        saida = rodar("firm", premissas, {**escala, **flags_da_conservacao}, moeda, rf=rf)
        multiplo = _exigir_valor(saida, campo_multiplo)
        if sem_ponte:
            valor = {"EV": _exigir_valor(saida, "EV")}
            algebra = (
                "EV = EV/EBITDA_curr x EBITDA (motor, sem ponte — parte de SOTP)"
            )
        else:
            valor = {
                "EV": _exigir_valor(saida, "EV"),
                "Equity": _exigir_valor(saida, "Equity"),
                "preco_acao": _exigir_valor(saida, "Preco_acao"),
            }
            algebra = "EV = EV/EBITDA_curr x EBITDA (ponte feita pelo motor)"
    else:  # NOPAT
        saida = rodar("firm", premissas, flags_da_conservacao or None, moeda, rf=rf)
        multiplo = _exigir_valor(saida, campo_multiplo)
        ev = multiplo * valor_metrica
        if sem_ponte:
            valor = {"EV": ev}
            algebra = (
                "EV = EV/NOPAT_curr x NOPAT (mesma definição de múltiplo; "
                "sem ponte — parte de SOTP)"
            )
        else:
            equity = ev - nd_efetivo
            preco_acao = equity / acoes
            valor = {"EV": ev, "Equity": equity, "preco_acao": preco_acao}
            algebra = (
                "EV = EV/NOPAT_curr x NOPAT; Equity = EV - nd_efetivo; "
                "preco_acao = Equity / acoes_diluidas (ponte aplicada aqui, fora do motor)"
            )

    return saida, valor, algebra, multiplo


def precificar_equity(premissas: dict, valor_metrica: float, acoes: float,
                       moeda: str | None = None,
                       rf: float | None = None) -> tuple[dict, dict, str, float]:
    """Roda o motor para um vetor de premissas da rota equity; devolve
    (saída, valor, álgebra, múltiplo de referência).

    Extraída do antigo `_cenario_equity` (Fatia B, Task 4) — mesmo motivo
    de `precificar_firm`, ver aquele docstring. Sem ponte: a rota equity
    chega em Equity diretamente (P/L x LL) — não há dívida líquida a
    subtrair. `multiplo` é `PL_curr`, resolvido por
    `_campo_do_multiplo("equity", None)` (FIX 2) e já validado por
    `_exigir_valor`. `rf` (correção do item 3): mesmo default, mesma
    disciplina de último parâmetro e mesmo repasse direto de
    `precificar_firm`, ver aquele docstring.
    """
    campo_multiplo = _campo_do_multiplo("equity", None)
    escala = {"ni": valor_metrica, "acoes": acoes}
    saida = rodar("equity", premissas, escala, moeda, rf=rf)
    valor = {
        "Equity": _exigir_valor(saida, "Equity"),
        "preco_acao": _exigir_valor(saida, "Preco_acao"),
    }
    multiplo = _exigir_valor(saida, campo_multiplo)
    algebra = "Equity = PL_curr x LL (motor); rota equity nao usa ponte"
    return saida, valor, algebra, multiplo


def precificar_rampa(premissas: dict, nd_efetivo: float | None = None,
                      acoes: float | None = None,
                      moeda: str | None = None,
                      rf: float | None = None) -> tuple[dict, dict, str, float]:
    """Roda o motor para um vetor de premissas da rota rampa; devolve
    (saída, valor, álgebra, múltiplo de referência).

    Irmã de `precificar_firm`/`precificar_equity` (Fatia C, Task 1), mesma
    forma de assinatura e mesma recusa de `null` via `_exigir_valor` — mas
    sem ramo de escala por fora do motor: `ebitda0` já é premissa
    OBRIGATÓRIA do vetor da rota (`PREMISSAS_OBRIGATORIAS_RAMPA`), não uma
    escala aplicada depois, como no ramo NOPAT da rota firm. O subcomando
    `rampa` do motor recebe `--nd`/`--acoes` e faz a composição bifásica
    inteira internamente (fase 1 rampa + fase 2 expansão, costuradas no
    ano `--t-rampa`) — `EV`, `Equity` e `Preco_acao` saem prontos, do mesmo
    jeito que o ramo EBITDA da rota firm já usa o motor para fazer a ponte
    inteira.

    `multiplo` é `EV/EBITDA0` — o headline desta rota é o múltiplo sobre o
    EBITDA do ANO 0, não uma métrica normalizada (é por isso que
    `METRICAS_POR_ROTA['rampa'] == {'EBITDA0'}`, ao contrário de
    `EV/EBITDA_curr`/`PL_curr` das outras duas rotas).

    Fatia C, Task 2: `nd_efetivo`/`acoes` ganharam default `None`, mesmo
    motivo e mesma disciplina de `precificar_firm` (ver aquele docstring)
    — uma parte de SOTP na rota rampa nunca cruza ponte. Com `nd_efetivo
    is None`, a chamada ao motor não leva `--nd`/`--acoes` nenhum (escala
    `None` — `ebitda0`/`receita0` já ancoram `EV`/`EV/EBITDA0` sozinhos;
    confirmado por sondagem direta do motor que os dois saem populados sem
    nd/acoes, e só `Equity`/`Preco_acao` saem ausentes) e `valor` só tem
    `"EV"`. Todo call site existente (`avaliar.py`) sempre passa
    `nd_efetivo`/`acoes` explícitos — comportamento antigo intacto.

    `rf` (correção do item 3): mesmo default, mesma disciplina de último
    parâmetro e mesmo repasse direto de `precificar_firm`, ver aquele
    docstring — inclusive aqui, `vetores_solver.py` (parity harness da
    rota rampa) chama esta função com quatro posicionais
    (`premissas, nd_efetivo, acoes, moeda`); `rf` fica de fora dessa
    chamada e cai no default `None`, comportamento inalterado.
    """
    sem_ponte = nd_efetivo is None
    escala = None if sem_ponte else {"nd": nd_efetivo, "acoes": acoes}
    saida = rodar("rampa", premissas, escala, moeda, rf=rf)
    multiplo = _exigir_valor(saida, "EV/EBITDA0")
    if sem_ponte:
        valor = {"EV": _exigir_valor(saida, "EV")}
        algebra = (
            "EV vem pronto do motor (composicao bifasica fase1+fase2; "
            "sem ponte — parte de SOTP)"
        )
    else:
        valor = {
            "EV": _exigir_valor(saida, "EV"),
            "Equity": _exigir_valor(saida, "Equity"),
            "preco_acao": _exigir_valor(saida, "Preco_acao"),
        }
        algebra = (
            "EV, Equity e Preco_acao vem prontos do motor "
            "(composicao bifasica fase1+fase2; ponte feita pelo motor)"
        )
    return saida, valor, algebra, multiplo


def precificar_degrau(premissas_cenario: dict, bloco_degrau: dict, m_valor: float,
                       moeda: str | None = None, rf: float | None = None) -> dict:
    """Roda o motor (subcomando `degrau`) para um cenário da rota equity;
    devolve a saída do motor verbatim (shape diferente das irmãs
    `precificar_firm`/`precificar_equity`/`precificar_rampa` — não há um
    único `multiplo` de referência nem uma `valor`/`algebra` a montar aqui;
    quem chama, `_aplicar_degrau_ao_cenario`, é quem lê `niveis`/
    `travas_obrigatorias` da saída).

    `premissas_cenario` é `cenario["premissas"]` do caso — já validado por
    `caso.py` (`_validar_degrau`) como isento de `mid_year` sempre que
    `degrau` está no caso, e cujas demais chaves (g, roe, ke, n, gde, nde,
    tv, roe_tv, gp, roe_book, politica_tv) são TODAS vocabulário válido do
    subparser `degrau` também — por isso a base do vetor é uma cópia direta
    dessas premissas, sem filtro. `bloco_degrau` é `caso["degrau"]`, já
    validado; `m_valor` é `bloco_degrau["m"][<nome do cenário>]["valor"]`,
    escolhido por quem chama (esta função não conhece o nome do cenário).

    `indice_alvo` vai como DOIS valores no mesmo `--indice-alvo` (a flag
    aceita lista separada por vírgula): o alvo do cenário primeiro
    (`niveis[0]`, D3 — o preço do cenário) e o próprio `indice_atual`
    depois (`niveis[1]`, h=1 por construção — D8, `divergencia_de_base_%`).
    Pedir os dois no MESMO subprocesso mantém "cada cenário roda `pe`... e
    `degrau`" (Task 1) como uma chamada de degrau só, e os dois preços
    (`niveis[0].preco_acao`, `niveis[1].preco_acao`) saem do MOTOR, prontos
    — nunca de uma multiplicação por `vpa` refeita neste wrapper (regra
    inviolável 1).

    `perfil_transicao` aplica o default 'rampa' explicitamente aqui (em vez
    de omitir a flag e confiar no default do subparser) — é o literal que a
    prova de falseabilidade da Task 1 muta para 'pontual' e confirma o
    teste da âncora ficar vermelho.

    `fx` some da chamada quando o caso não declara (`bloco_degrau.get("fx")
    is None`): o subparser `degrau` já defaulta `--fx` para 1.0, mesma
    disciplina de `politica_tv`/`gp`/`gde`/`nde` nas outras rotas (chave
    ausente do dict não vira flag; quem decide o default é o motor).
    """
    indice_atual = bloco_degrau["indice_atual"]["valor"]
    indice_alvo = bloco_degrau["indice_alvo"]["valor"]
    premissas = dict(premissas_cenario)
    premissas["indice_atual"] = indice_atual
    premissas["indice_alvo"] = f"{indice_alvo},{indice_atual}"
    premissas["anos"] = bloco_degrau["anos"]
    premissas["perfil_transicao"] = bloco_degrau.get("perfil_transicao") or "rampa"
    premissas["vpa"] = bloco_degrau["vpa"]["valor"]
    if bloco_degrau.get("fx") is not None:
        premissas["fx"] = bloco_degrau["fx"]
    premissas["m"] = m_valor
    return rodar("equity", premissas, None, moeda, subcomando="degrau", rf=rf)


def _aplicar_degrau_ao_cenario(cenario_montado: dict, cenario: dict, bloco_degrau: dict,
                                m_valor: float, moeda: str | None, rf: float | None,
                                preco_valor: float) -> tuple[dict, list]:
    """Substitui o preço do cenário pelo COM degrau; move o SEM degrau para
    `sem_degrau` ao lado (D3, Fatia D Task 1).

    `cenario_montado` já é o resultado normal de `_monta_cenario` (rota
    equity, sem degrau) — esta função só adiciona/substitui chaves por
    cima; `ancora`/`triangulo`/`premissas`/`algebra_da_escala`/
    `diagnosticos`/`coerencia_vetor`/`convencao_temporal` continuam vindo
    da rota P/L, intocados, e o `multiplos` de topo (PL_curr/PL_fwd)
    também — só o `sem_degrau` interno os duplica (plano: "sem_degrau ← o
    valor e os multiplos da rota P/L, íntegros").

    `divergencia_de_base_%` (D8) compara `niveis[1].preco_acao` (o nível
    h=1, calculado pelo MOTOR via `--vpa`/`--fx` dentro de
    `precificar_degrau`) contra `cenario_montado["valor"]["preco_acao"]`
    (a rota P/L, também motor) — "comparação entre dois outputs do motor",
    nunca a álgebra `base.multiplo_x_rentab x vpa / fx` refeita aqui: essa
    é exatamente a conta que o motor já faz para popular `preco_acao` de
    cada nível, e repeti-la sobre um `multiplo_x_rentab` arredondado a 4
    casas divergiria (por arredondamento) do que o motor responderia se
    perguntado diretamente — regra inviolável 1 (Global Constraints do
    plano).

    Devolve `(cenario_aumentado, travas_obrigatorias)` — o segundo elemento
    é repassado por quem chama para montar `resultado["degrau"]` (D8/Task 1:
    "o bloco declarado + as travas_obrigatorias do motor, verbatim"), uma
    única vez, fora do loop de cenários.
    """
    saida_degrau = precificar_degrau(cenario["premissas"], bloco_degrau, m_valor, moeda, rf=rf)
    niveis = saida_degrau.get("niveis") or []
    if len(niveis) < 2:
        raise MotorFalhou(
            f"motor devolveu {len(niveis)} nível(is) de degrau, esperados 2 "
            f"(alvo do cenário + indice_atual, D8): {saida_degrau!r}."
        )
    nivel_alvo, nivel_base = niveis[0], niveis[1]

    preco_com_degrau = _exigir_valor(nivel_alvo, "preco_acao")
    preco_base_h1 = _exigir_valor(nivel_base, "preco_acao")
    preco_sem_degrau = cenario_montado["valor"]["preco_acao"]

    degrau_cenario: dict = {
        "h": _exigir_valor(nivel_alvo, "h"),
        "rentabilidade_pos_%": _exigir_valor(nivel_alvo, "rentabilidade_pos_%"),
        "multiplo": _exigir_valor(nivel_alvo, "multiplo"),
        "multiplo_x_rentab": _exigir_valor(nivel_alvo, "multiplo_x_rentab"),
        "com_transicao": _exigir_valor(nivel_alvo, "com_transicao"),
        "fator_transicao": _exigir_valor(nivel_alvo, "fator_transicao"),
        "perfil_transicao": nivel_alvo["perfil_transicao"],
        "m": m_valor,
        "divergencia_de_base_%": (preco_base_h1 / preco_sem_degrau - 1) * 100,
    }
    if "ALERTA" in nivel_alvo:
        degrau_cenario["ALERTA"] = nivel_alvo["ALERTA"]
    if "ALERTA_RiR" in nivel_alvo:
        degrau_cenario["ALERTA_RiR"] = nivel_alvo["ALERTA_RiR"]
    # Fatia 5C, item 5, Task 3 (T1): a chave pública de cada alerta presente,
    # na ordem de `_ALERTAS_DEGRAU_ORDEM` — campo aditivo do `resultados/1`. A
    # prosa acima continua publicada para auditoria; o relatório nunca a lê.
    # Onda de correção da revisão final da 5C (F1): mais a da divergência de
    # base acima do limiar, decidida aqui (`_chaves_do_degrau`), nunca no
    # relatório.
    degrau_cenario["diagnosticos_chaves"] = _chaves_do_degrau(
        nivel_alvo, degrau_cenario["divergencia_de_base_%"])

    resultado = dict(cenario_montado)
    resultado["sem_degrau"] = {
        "valor": cenario_montado["valor"],
        "multiplos": cenario_montado["multiplos"],
    }
    resultado["valor"] = {"preco_acao": preco_com_degrau}
    resultado["vs_preco"] = {"upside": preco_com_degrau / preco_valor - 1}
    resultado["degrau"] = degrau_cenario
    return resultado, saida_degrau["travas_obrigatorias"]


def _monta_cenario(cenario: dict, saida_motor: dict, rota: str, valor: dict,
                    algebra: str, preco_valor: float,
                    tipo_metrica: str | None = None) -> dict:
    """Compõe o registro de um cenário no shape de `resultados.json`.

    `upside` é a única outra conta feita fora do motor: `preco_acao / preco.valor
    − 1`, comparação simples contra o preço declarado no caso — não é
    valuation, é a leitura de quanto o preço de mercado diverge do valor que
    saiu do motor (mais a álgebra de escala, quando aplicável).

    `tipo_metrica` só importa na rota firm com métrica EBITDA: nesse ramo,
    `precificar_firm` já leu `saida_motor["EV/EBITDA_curr"]` por
    `_exigir_valor` (é o `multiplo` que devolve ao chamador) antes deste
    ponto — reconferir aqui checaria duas vezes o mesmo campo do mesmo
    dict, sempre com o mesmo resultado. Nos outros casos (rota equity, ou
    ramo NOPAT desta própria rota firm) `EV/EBITDA_curr` nunca foi checado
    antes, então a guarda de `_exigir_valor` continua valendo — a garantia
    de que nenhum múltiplo nulo entra em `resultados.json` não afrouxa em
    nenhum desses casos, só para de repetir uma checagem cujo resultado já
    era certo.
    """
    chaves_multiplo = _MULTIPLOS_POR_ROTA[rota]
    multiplos: dict[str, float] = {}
    for chave in chaves_multiplo:
        if chave not in saida_motor:
            continue
        if chave == "EV/EBITDA_curr" and tipo_metrica == "EBITDA":
            multiplos[chave] = saida_motor[chave]  # já validado por precificar_firm
        else:
            multiplos[chave] = _exigir_valor(saida_motor, chave)
    upside = valor["preco_acao"] / preco_valor - 1
    diagnosticos_lista = saida_motor["diagnosticos"]

    return {
        "ancora": cenario["ancora"],
        "triangulo": cenario["triangulo"],
        "premissas": cenario["premissas"],
        "multiplos": multiplos,
        "valor": valor,
        "algebra_da_escala": algebra,
        "vs_preco": {"upside": upside},
        "diagnosticos": diagnosticos_lista,
        # Fatia 5A, item 5, Task 1 (regra 5 do contrato): mesmo comprimento
        # e mesma ordem de "diagnosticos" — a chave pública de cada
        # mensagem, publicada ao lado da prosa do motor. `None` (mensagem
        # sem chave única) não é filtrado aqui: o builder do relatório é
        # quem trata `null` como HARD FAIL (A5) — este wrapper só classifica.
        "diagnosticos_chaves": [diagnosticos.classificar(m) for m in diagnosticos_lista],
        "coerencia_vetor": saida_motor["coerencia_vetor"],
        "convencao_temporal": saida_motor["convencao_temporal"],
    }


# Chaves do motor PROMOVIDAS para dentro do shape do wrapper (`valor`/
# `multiplos`) na rota rampa — nomeado aqui de propósito, não inferido, para
# que qualquer mudança em quais chaves viram campo próprio seja deliberada.
# São as ÚNICAS chaves que `_monta_cenario_rampa` omite do repasse abaixo:
# entrariam duplicadas (mesmo número, dois nomes — uma vez como `EV`, outra
# como `valor["EV"]`) se também fossem copiadas verbatim.
_CHAVES_PROMOVIDAS_RAMPA: frozenset = frozenset(
    {"EV", "Equity", "Preco_acao", "EV/EBITDA0"})


def _monta_cenario_rampa(cenario: dict, saida_motor: dict, valor: dict,
                          algebra: str, preco_valor: float, multiplo: float) -> dict:
    """Compõe o registro de um cenário da rota rampa no shape de `resultados.json`.

    Irmã de `_monta_cenario`, mas não a reaproveita: a saída do subcomando
    `rampa` do motor não tem o mesmo shape de `ev`/`pe` — não carrega
    `diagnosticos`/`coerencia_vetor`/`convencao_temporal` (só `ev`/`pe`
    emitem essas chaves), e o cenário não declara `triangulo` (ver o
    comentário na rota rampa, em `avaliar()`, sobre por que isso é seguro).

    Repasse íntegro, não whitelist: correção de um achado da revisão — a
    versão anterior desta função listava por nome as chaves que entravam
    (`checks_internos`, `travas`, `d_trajetoria_fase1_%`, `rir_fase1_%`,
    `capacidade_receita`), e essa lista, incompleta, derrubava treze outras
    chaves que o motor emite, entre elas `rir2_%`/`roic2_%` — a taxa e o
    retorno marginal de reinvestimento da FASE 2 — e
    `vp_fase1`/`valor_fase2_no_ano_T` — a decomposição de valor entre as
    duas fases, o ponto central de uma composição bifásica. Fabricar essas
    chaves com um default (`[]`, `{}`, `None`) para "completar" a lista
    seria inventar dado que o motor nunca produziu — proibido pela mesma
    disciplina que rege todo o resto deste módulo; a correção certa é não
    filtrar, não completar.

    O critério agora é o oposto de uma whitelist: toda chave que o motor
    devolveu sobrevive verbatim no cenário, SALVO as que
    `_CHAVES_PROMOVIDAS_RAMPA` nomeia — as quatro que já viraram
    `valor`/`multiplos` acima. Mesma disciplina que `reversa.reverter` já
    aplica à saída do subcomando `rev` (ver `reversa.py`): nenhuma chave do
    motor é removida, renomeada ou reformatada por decisão deste módulo. Uma
    chave nova que o motor passe a emitir amanhã (por exemplo, se
    `capacidade_receita` ganhar uma irmã) chega aqui sem exigir mudança
    nenhuma neste arquivo — só uma chave nova que o wrapper decida PROMOVER
    precisa entrar em `_CHAVES_PROMOVIDAS_RAMPA`.

    FIX 6d (revisão final): `multiplo` chega como PARÂMETRO — já validado
    por `_exigir_valor(saida, "EV/EBITDA0")` dentro de `precificar_rampa` —
    em vez de recalculado aqui com uma segunda chamada idêntica a
    `_exigir_valor` sobre o MESMO campo do MESMO `saida_motor`. Antes desta
    correção, o retorno `multiplo` de `precificar_rampa` estava morto em
    todo call site (`avaliar()` e `sotp._compor_parte` descartavam com
    `_multiplo`) — confirmado por mutação — enquanto esta função relia
    numa segunda leitura própria do mesmo campo. Escolhido usar o
    parâmetro (em vez de dropar o retorno de `precificar_rampa`) para
    manter a paridade de assinatura com `precificar_firm`/
    `precificar_equity` — as três irmãs devolvem `multiplo`, e agora as
    três também o usam a jusante. Fonte única de verdade: um só
    `_exigir_valor(saida, "EV/EBITDA0")` no módulo inteiro, dentro de
    `precificar_rampa`.

    Fatia 5A, item 5, Task 1 (regra 5 do contrato): esta rota não emite
    `diagnosticos` (ver acima) — `diagnosticos_chaves` aqui é, em vez
    disso, a lista das chaves de aviso da rampa (`_AVISOS_RAMPA_ORDEM`)
    que de fato estão PRESENTES em `saida_motor`, na ordem canônica
    `aviso_colheita`, `aviso_delator`, `aviso_gp` — nunca passadas pelo
    classificador de prefixo (`diagnosticos.classificar`): o nome da chave
    de aviso já É a chave, não uma mensagem livre a classificar.
    """
    upside = valor["preco_acao"] / preco_valor - 1

    resultado = {
        "ancora": cenario["ancora"],
        "premissas": cenario["premissas"],
        "multiplos": {"EV/EBITDA0": multiplo},
        "valor": valor,
        "algebra_da_escala": algebra,
        "vs_preco": {"upside": upside},
        "diagnosticos_chaves": [c for c in _AVISOS_RAMPA_ORDEM if c in saida_motor],
    }
    # FIX 6e (revisão final): além das quatro chaves já PROMOVIDAS acima
    # (consumidas dentro de `valor`/`multiplos`, nunca top-level), o loop
    # também pula qualquer chave que já exista em `resultado` — ancora,
    # premissas, multiplos, valor, algebra_da_escala, vs_preco e, desde a
    # fatia 5A, `diagnosticos_chaves`. Nenhuma colisão existe hoje (o motor
    # não emite nenhum desses nomes), mas sem
    # esta guarda uma chave nova do motor que algum dia colidisse com um
    # campo autorado sobrescreveria esse campo em silêncio — `chave in
    # resultado` fecha essa fronteira de forma estrutural, sem precisar
    # enumerar cada campo autorado à mão numa segunda lista que poderia
    # esquecer alguma.
    for chave, valor_do_motor in saida_motor.items():
        if chave in resultado or chave in _CHAVES_PROMOVIDAS_RAMPA:
            continue
        resultado[chave] = valor_do_motor
    return resultado


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
    moeda = caso["moeda"]
    # Correção do item 3: 'mercado' é bloco opcional (`caso.py`,
    # `_validar_mercado`) — diferente de 'moeda', que é sempre obrigatório
    # e por isso indexado direto acima. `rf` vem de `caso["mercado"]["rf"]`
    # quando o bloco existe; sem ele, `None` — o mesmo comportamento de
    # hoje (`_guardas_damodaran` sem `rf` responde "PREMISSA NÃO ANCORADA")
    # continua valendo para um caso que genuinamente não declara mercado.
    mercado = caso.get("mercado")
    rf = mercado.get("rf") if mercado else None

    # FIX 5 (revisão final): SKILL.md documenta metrica_base como (tipo,
    # valor, fonte) e caso.py agora valida 'fonte' com a mesma disciplina de
    # 'preco.fonte' — mas a saída cortava para {tipo, valor}, descartando
    # periodo e fonte, enquanto 'preco' abaixo mantém as duas. A
    # métrica-base é a escala de todo o valuation; não é o único número do
    # caso sem proveniência no resultado. 'periodo' continua opcional — só
    # entra quando presente no caso, do jeito que já era antes desta fatia.
    metrica_saida: dict = {"tipo": metrica["tipo"], "valor": metrica["valor"]}
    if metrica.get("periodo") is not None:
        metrica_saida["periodo"] = metrica["periodo"]
    metrica_saida["fonte"] = metrica["fonte"]

    resultado: dict = {
        # Fatia 5A, item 5, Task 1 (regras 1/2 do contrato): `versao_contrato`
        # e `origem` são as primeiras chaves, de propósito — provam a versão
        # do contrato e a correspondência com o caso ANTES de qualquer outro
        # campo, mesmo que a ordem de chaves não seja parte do contrato (JSON
        # é um objeto, não uma lista).
        "versao_contrato": VERSAO_CONTRATO,
        "origem": {
            "caso_sha256": _sha256_canonico(caso),
            "metodologia": {
                "nome": _MANIFEST_VENDOR["metodologia"],
                "versao": _MANIFEST_VENDOR["versao"],
            },
        },
        "companhia": caso["companhia"],
        "ticker": caso.get("ticker"),
        "moeda": moeda,
        # Fatia 5F, Task 2 (D7): a escala dos montantes que o caso declara, sempre
        # publicada — `null` sem declaração; o relatório a aplica às unidades que o
        # catálogo marca (`unidades.<unidade>.escala_monetaria`).
        "escala_monetaria": caso.get("escala_monetaria"),
        "data_analise": caso["data_analise"],
        "rota": rota,
        "metrica_base": metrica_saida,
        "preco": caso["preco"],
        "acoes_diluidas": acoes,
    }

    cenarios: dict = {}
    if rota == "firm":
        ponte = compor(caso["ponte"])
        resultado["ponte"] = ponte
        nd_efetivo = ponte["nd_efetivo"]
        # Fatia 5F, Task 3 (D6): a conservação de capital, só no cenário.
        conservacao = caso.get("conservacao_de_capital")
        for nome, cenario in caso["cenarios"].items():
            saida, valor, algebra, _multiplo = precificar_firm(
                cenario["premissas"], metrica["tipo"], metrica["valor"],
                nd_efetivo, acoes, moeda, rf=rf, conservacao=conservacao)
            cenarios[nome] = _monta_cenario(
                cenario, saida, rota, valor, algebra, preco_valor, metrica["tipo"])
            if conservacao is not None:
                cenarios[nome]["conservacao_capital"] = _conservacao_publicada(saida, conservacao)
    elif rota == "rampa":
        # Única rota sem `triangulo`, de propósito: a regra existe para a
        # RiR nunca ficar silenciosa, e aqui o motor já devolve
        # `rir_fase1_%`/`rir2_%` como resultado — cumprida por construção,
        # não por declaração.
        #
        # Mesma ponte da rota firm (D1 do plano da Fatia C: "a ponte para
        # preço é a mesma das outras rotas firm" — nd_efetivo vai em --nd
        # nas duas). `caso.py` já exige 'ponte' para 'rampa' do mesmo jeito
        # que exige para 'firm' (ver `_validar_ponte`).
        ponte = compor(caso["ponte"])
        resultado["ponte"] = ponte
        nd_efetivo = ponte["nd_efetivo"]
        for nome, cenario in caso["cenarios"].items():
            saida, valor, algebra, multiplo = precificar_rampa(
                cenario["premissas"], nd_efetivo, acoes, moeda, rf=rf)
            cenarios[nome] = _monta_cenario_rampa(
                cenario, saida, valor, algebra, preco_valor, multiplo)
    else:  # equity
        # Rota equity chega em Equity direto (P/L x LL): não há ponte de
        # dívida (`caso.py` já recusa um caso equity que declare `ponte`),
        # então `nd_efetivo` é `0.0` aqui — mesma leitura que
        # `reversa.alvo_de_mercado` usa para decidir a base do alvo
        # ("pl", sem somar dívida a um EV que este lado nunca calcula).
        nd_efetivo = 0.0
        # Fatia D, Task 1: bloco opcional 'degrau' — mesma disciplina
        # aditiva de 'reversa'/'sensibilidades'/'sotp' (só muda algo quando
        # o caso declara). `caso.py` já garante, no gate, que 'degrau' só
        # aparece na rota equity (D2) e que 'degrau.m' tem exatamente uma
        # entrada por cenário do caso — por isso `bloco_degrau["m"][nome]`
        # abaixo nunca levanta KeyError para um caso validado.
        bloco_degrau = caso.get("degrau")
        travas_obrigatorias_degrau: list | None = None
        for nome, cenario in caso["cenarios"].items():
            saida, valor, algebra, _multiplo = precificar_equity(
                cenario["premissas"], metrica["valor"], acoes, moeda, rf=rf)
            cenario_montado = _monta_cenario(cenario, saida, rota, valor, algebra, preco_valor)
            if bloco_degrau is not None:
                m_valor = bloco_degrau["m"][nome]["valor"]
                cenario_montado, travas_obrigatorias_degrau = _aplicar_degrau_ao_cenario(
                    cenario_montado, cenario, bloco_degrau, m_valor, moeda, rf, preco_valor)
            cenarios[nome] = cenario_montado
        if bloco_degrau is not None:
            resultado["degrau"] = {**bloco_degrau, "travas_obrigatorias": travas_obrigatorias_degrau}

    resultado["cenarios"] = cenarios

    # Fatia B, Task 5: os dois blocos são aditivos — só aparecem quando o
    # caso os declara. Um caso sem 'reversa'/'sensibilidades' (toda fixture
    # da fatia A) não passa por nenhum dos dois `if` abaixo, e o shape do
    # resultado não muda nem um byte em relação ao que saía antes desta
    # fatia. `nome_cenario` vem do próprio bloco (`reversa.cenario`/
    # `sensibilidades.cenario`) — já confirmado por `caso.validar` como um
    # cenário existente em `caso["cenarios"]` — nunca do cenário "base" por
    # convenção implícita.
    if "reversa" in caso:
        resultado["reversa"] = reverter(caso, caso["reversa"]["cenario"], nd_efetivo)

    if "sensibilidades" in caso:
        # Import local — ver o comentário junto dos imports de topo sobre o
        # ciclo avaliar -> sensibilidades -> avaliar.
        from sensibilidades import calcular
        resultado["sensibilidades"] = calcular(
            caso, caso["sensibilidades"]["cenario"], nd_efetivo)

    # Fatia C, Task 4: mesma disciplina aditiva dos dois blocos acima — só
    # aparece quando o caso declara 'sotp'. Import local pelo MESMO motivo
    # do import local de 'sensibilidades' logo acima: `sotp.py` já faz
    # `from avaliar import precificar_firm, precificar_rampa` no topo dele
    # — um `from sotp import compor_partes` no TOPO deste arquivo fecharia
    # o mesmo tipo de ciclo (avaliar -> sotp -> avaliar), como o próprio
    # `sotp.py` já documentava antes desta task. `compor_partes` cruza a
    # PRÓPRIA ponte do caso (`caso["ponte"]`) internamente — ao contrário
    # de `reverter`/`calcular` acima, não recebe `nd_efetivo` como
    # parâmetro, por isso não é passado aqui. `caso.py` já garante, no
    # gate, que um caso com 'sotp' não é rota equity (SOTP soma EV; a rota
    # equity não produz EV) — logo `caso["ponte"]` sempre existe quando
    # 'sotp' existe (`_validar_ponte` exige o bloco nas duas rotas que
    # sobram, firm e rampa) — e que `caso["sotp"]["cenario"]` aponta para
    # um cenário de fato declarado em `caso["cenarios"]`. Nenhuma chave do
    # que `compor_partes` devolve é filtrada, renomeada ou reformatada
    # aqui — mesma disciplina de `resultado["reversa"]`/
    # `resultado["sensibilidades"]` acima.
    if "sotp" in caso:
        from sotp import compor_partes
        resultado["sotp"] = compor_partes(caso, caso["sotp"]["cenario"])

    # Fatia 5A, item 5, Task 1 (regras 3/4 do contrato): `manchete` e
    # `mercado_tela` fecham a lista de campos novos. Rodam por ÚLTIMO, de
    # propósito — dependem de `resultado["cenarios"]` (sempre) e de
    # `resultado["sotp"]` (quando o caso declara 'sotp'), os dois já
    # montados nos blocos acima. `nd_efetivo` é o mesmo usado por
    # `reversa`/`sensibilidades` logo acima: `ponte["nd_efetivo"]` nas
    # rotas firm/rampa, `0.0` na equity (ver os três ramos de rota, no
    # início desta função).
    resultado["manchete"] = _montar_manchete(caso, resultado)
    resultado["mercado_tela"] = _montar_mercado_tela(caso, resultado, nd_efetivo)
    # Fatia 5F, Task 2 (D5): a tela forward, SEMPRE publicada — `null` sem
    # `metrica_forward` declarada no caso.
    resultado["mercado_tela_forward"] = _montar_mercado_tela_forward(caso, nd_efetivo)

    # Fatia 5D, Task 1 (D3/D4): o que só a integração sabe sobre o escopo do
    # caso, SEMPRE publicado — um campo de contrato ausente não pode sumir em
    # silêncio. `fronteira_de_escopo` é o bloco que o gate validou, ou `null`
    # (§14 do desenho: sob fronteira, nada de preço-alvo de manchete — regra do
    # relatório, que lê este campo). `limitacoes` é a lista de chaves das
    # limitações do caso, rotuladas pelo catálogo: hoje só a que torna a
    # reversa inadmissível, publicada exatamente como
    # `caso.reversa_indisponivel` a devolve — nunca decidida aqui.
    # Fatia 5F, Task 1 (D3): depois da limitação que suprime a reversa, as da LEITURA
    # da reversa publicada (`reversa.limitacoes_da_leitura` — hoje a curva iso-valor
    # não calculada, com o gatilho do teto). As duas famílias nunca coexistem: uma
    # limitação de reversa implica caso sem reversa.
    resultado["fronteira_de_escopo"] = caso.get("fronteira_de_escopo")
    limitacao_da_reversa = reversa_indisponivel(caso)
    resultado["limitacoes"] = ([] if limitacao_da_reversa is None else [limitacao_da_reversa]) + (
        limitacoes_da_leitura(resultado["reversa"]) if "reversa" in resultado else [])

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
