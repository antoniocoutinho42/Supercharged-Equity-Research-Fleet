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
import json
import sys
from pathlib import Path

from caso import CasoInvalido, carregar
from motor import MotorFalhou, _campo_do_multiplo, _exigir_valor, rodar
from ponte import compor
from reversa import reverter

# `sensibilidades.calcular` NÃO entra aqui em cima: `sensibilidades.py` faz
# `from avaliar import precificar_equity, precificar_firm` no topo dela — um
# `from sensibilidades import calcular` neste ponto do arquivo criaria um
# ciclo (avaliar -> sensibilidades -> avaliar) resolvido ANTES de
# `precificar_firm`/`precificar_equity` existirem no namespace deste módulo,
# e o import quebraria com "cannot import name ... from partially
# initialized module". `reversa.py` não tem esse problema (não importa
# `avaliar`), por isso `reverter` é import de topo normal. O import de
# `calcular` é feito dentro de `avaliar()`, na hora de usar — ver ali.

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
                     moeda: str | None = None) -> tuple[dict, dict, str, float]:
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
    """
    campo_multiplo = _campo_do_multiplo("firm", tipo_metrica)
    sem_ponte = nd_efetivo is None
    if tipo_metrica == "EBITDA":
        escala = {"ebitda": valor_metrica}
        if not sem_ponte:
            escala["nd"] = nd_efetivo
            escala["acoes"] = acoes
        saida = rodar("firm", premissas, escala, moeda)
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
        saida = rodar("firm", premissas, None, moeda)
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
                       moeda: str | None = None) -> tuple[dict, dict, str, float]:
    """Roda o motor para um vetor de premissas da rota equity; devolve
    (saída, valor, álgebra, múltiplo de referência).

    Extraída do antigo `_cenario_equity` (Fatia B, Task 4) — mesmo motivo
    de `precificar_firm`, ver aquele docstring. Sem ponte: a rota equity
    chega em Equity diretamente (P/L x LL) — não há dívida líquida a
    subtrair. `multiplo` é `PL_curr`, resolvido por
    `_campo_do_multiplo("equity", None)` (FIX 2) e já validado por
    `_exigir_valor`.
    """
    campo_multiplo = _campo_do_multiplo("equity", None)
    escala = {"ni": valor_metrica, "acoes": acoes}
    saida = rodar("equity", premissas, escala, moeda)
    valor = {
        "Equity": _exigir_valor(saida, "Equity"),
        "preco_acao": _exigir_valor(saida, "Preco_acao"),
    }
    multiplo = _exigir_valor(saida, campo_multiplo)
    algebra = "Equity = PL_curr x LL (motor); rota equity nao usa ponte"
    return saida, valor, algebra, multiplo


def precificar_rampa(premissas: dict, nd_efetivo: float | None = None,
                      acoes: float | None = None,
                      moeda: str | None = None) -> tuple[dict, dict, str, float]:
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
    """
    sem_ponte = nd_efetivo is None
    escala = None if sem_ponte else {"nd": nd_efetivo, "acoes": acoes}
    saida = rodar("rampa", premissas, escala, moeda)
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


# Chaves do motor PROMOVIDAS para dentro do shape do wrapper (`valor`/
# `multiplos`) na rota rampa — nomeado aqui de propósito, não inferido, para
# que qualquer mudança em quais chaves viram campo próprio seja deliberada.
# São as ÚNICAS chaves que `_monta_cenario_rampa` omite do repasse abaixo:
# entrariam duplicadas (mesmo número, dois nomes — uma vez como `EV`, outra
# como `valor["EV"]`) se também fossem copiadas verbatim.
_CHAVES_PROMOVIDAS_RAMPA: frozenset = frozenset(
    {"EV", "Equity", "Preco_acao", "EV/EBITDA0"})


def _monta_cenario_rampa(cenario: dict, saida_motor: dict, valor: dict,
                          algebra: str, preco_valor: float) -> dict:
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
    """
    multiplo_referencia = _exigir_valor(saida_motor, "EV/EBITDA0")
    upside = valor["preco_acao"] / preco_valor - 1

    resultado = {
        "ancora": cenario["ancora"],
        "premissas": cenario["premissas"],
        "multiplos": {"EV/EBITDA0": multiplo_referencia},
        "valor": valor,
        "algebra_da_escala": algebra,
        "vs_preco": {"upside": upside},
    }
    for chave, valor_do_motor in saida_motor.items():
        if chave in _CHAVES_PROMOVIDAS_RAMPA:
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
        "companhia": caso["companhia"],
        "ticker": caso.get("ticker"),
        "moeda": moeda,
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
        for nome, cenario in caso["cenarios"].items():
            saida, valor, algebra, _multiplo = precificar_firm(
                cenario["premissas"], metrica["tipo"], metrica["valor"],
                nd_efetivo, acoes, moeda)
            cenarios[nome] = _monta_cenario(
                cenario, saida, rota, valor, algebra, preco_valor, metrica["tipo"])
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
            saida, valor, algebra, _multiplo = precificar_rampa(
                cenario["premissas"], nd_efetivo, acoes, moeda)
            cenarios[nome] = _monta_cenario_rampa(
                cenario, saida, valor, algebra, preco_valor)
    else:  # equity
        # Rota equity chega em Equity direto (P/L x LL): não há ponte de
        # dívida (`caso.py` já recusa um caso equity que declare `ponte`),
        # então `nd_efetivo` é `0.0` aqui — mesma leitura que
        # `reversa.alvo_de_mercado` usa para decidir a base do alvo
        # ("pl", sem somar dívida a um EV que este lado nunca calcula).
        nd_efetivo = 0.0
        for nome, cenario in caso["cenarios"].items():
            saida, valor, algebra, _multiplo = precificar_equity(
                cenario["premissas"], metrica["valor"], acoes, moeda)
            cenarios[nome] = _monta_cenario(cenario, saida, rota, valor, algebra, preco_valor)

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
