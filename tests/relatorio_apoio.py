"""Apoio de teste para o builder do relatório (fatia 5A, item 5, Task 3).

Roda `avaliar()` de VERDADE sobre uma fixture de `caso.json` e monta uma
raiz de execução com `entrega.json` válido — para os testes de contrato e
de fronteira montarem cenários (válido, e cada recusa) sem duplicar a
orquestração caso -> resultados.

Só este arquivo, dentro de `tests/`, importa `er-valuation`
(`avaliar`/`caso`) — o boundary test de `er-relatorio`
(`tests/test_relatorio_fronteira.py`) só varre
`skills/er-relatorio/scripts/`; testes não são a camada do relatório (E3
governa o PRODUTO, não a suíte que o exercita).

Fatia 5D, item 5, Task 2: uma Análise válida exige mais do que o caso — a Tese
do analista (D1) e a reversa que a metodologia pede (D4, HARD FAIL
`analise_sem_reversa`). `montar_entrega` passa a compor as duas por padrão: a
Tese de `_tese_padrao`, e o bloco `reversa` de `com_bloco_de_reversa_valido`
sempre que o gate o admite (`caso.reversa_indisponivel` devolve `None`) e o caso
ainda não o declara. Onde o gate não o admite (`caso_degrau`, `caso_rampa`), a
entrega sai sem reversa e com o disclosure nomeado da limitação — nunca com a
regra enfraquecida e nunca com a fixture editada.

Fatia 5E, item 5, Task 2: a entrega também exige o ledger `ledger/1` do
`er-evidencia` e o consenso da Tese. `montar_entrega` os compõe por padrão
(`completar_ledger`), derivados do mapa `catalogo.insumos_do_caso` sobre o caso
já composto — nunca de uma lista por fixture: um padrão novo no mapa se cobre
sozinho, e uma fixture nova também. O contrato é lido uma vez, aqui
(`CONTRATO_LEDGER`), e o estatuto, a classe e o tipo de localizador dos registros
compostos saem dele, nunca de um literal.
"""

import copy
import json
import math
import re
import sys
from pathlib import Path
from typing import Callable

RAIZ = Path(__file__).resolve().parent.parent
FIXTURES = RAIZ / "tests" / "fixtures"

sys.path.insert(0, str(RAIZ / "skills" / "er-relatorio" / "scripts"))
import qc  # noqa: E402

sys.path.insert(0, str(RAIZ / "skills" / "er-valuation" / "scripts"))
from avaliar import avaliar  # noqa: E402
from caso import CAMPOS_DE_MERCADO_OBRIGATORIOS, reversa_indisponivel, validar  # noqa: E402
from caso import carregar as carregar_caso  # noqa: E402

CATALOGO = json.loads(
    (RAIZ / "skills" / "er-valuation" / "assets" / "catalogo_apresentacao.json").read_text(encoding="utf-8"))
CONTRATO_LEDGER = json.loads(
    (RAIZ / "skills" / "er-evidencia" / "assets" / "contrato_ledger.json").read_text(encoding="utf-8"))

_PADRAO_ESTILO_BLOCO = re.compile(r'(<style\b[^>]*>)(.*?)(</style\s*>)', re.IGNORECASE | re.DOTALL)


def prosa_da_pagina(html_texto: str) -> str:
    """A página com o MIOLO de todo `<script>`/`<style>` neutralizado — o
    escopo certo para toda asserção sobre a PROSA que o relatório escreveu.

    B6 (onda de correção da revisão final, achado F10): a regra de PRODUÇÃO
    (`placeholder_malformado`) sempre esteve certa -- varre a lista de
    prosa (`placeholders.campos_de_prosa`, desde a 5D), nunca a página. Foram os TESTES que confundiram
    "nenhum placeholder cru sobrou" com "nenhum `}}` na página": uma página
    com exhibit tem 50 ocorrências de `}}`, todas do uPlot minificado, e no
    dia em que a 5C/5D rodasse essas asserções sobre uma entrega com
    gráfico elas ficariam vermelhas pelo bundle -- com o conserto natural
    (enfraquecer a asserção) apagando a regra que importa. Escopo, não lista
    de exclusão por arquivo: `qc._sem_conteudo_de_script` já existe e não
    envelhece a cada asset novo."""
    return _PADRAO_ESTILO_BLOCO.sub(
        lambda m: m.group(1) + m.group(3), qc._sem_conteudo_de_script(html_texto))

def listas_de_chaves_de_diagnostico(no, caminho: tuple = ()):
    """Toda lista `diagnosticos_chaves` DENTRO de `no` (um cenário publicado),
    em qualquer profundidade, na ordem em que aparece — `(caminho, lista)`.

    Onda de correção da revisão final da 5C (F4): é a derivação que as travas
    usam para saber que listas de chaves um cenário publica SEM nomear onde elas
    moram. Hoje são duas formas (`diagnosticos_chaves` do cenário e
    `degrau.diagnosticos_chaves`); uma forma aditiva de uma v10
    (`transicao.diagnosticos_chaves`, a sonda P6 da revisão) entra aqui no
    instante em que o wrapper a publica, sem editar teste nenhum — e é isso que
    faz a trava da lista exibível reprovar na INTEGRAÇÃO quando a fachada a
    esquece."""
    if isinstance(no, dict):
        for chave, valor in no.items():
            if chave == "diagnosticos_chaves" and isinstance(valor, list):
                yield caminho + (chave,), valor
            else:
                yield from listas_de_chaves_de_diagnostico(valor, caminho + (chave,))
    elif isinstance(no, list):
        for indice, item in enumerate(no):
            yield from listas_de_chaves_de_diagnostico(item, caminho + (indice,))


# --------------------------------------------------------------------------
# Fatia 5D, Task 1 (a trava se-e-só-se de D4, em tests/test_valuation_contrato.py)
# — movido para cá na Task 2, sem reescrever: o mesmo construtor serve à trava da
# integração e à composição da reversa que a Análise exige.
# --------------------------------------------------------------------------

_MODELO_DE_REVERSA = json.loads((FIXTURES / "caso_reversa_firm.json").read_text(encoding="utf-8"))


def com_bloco_de_reversa_valido(caso: dict) -> dict:
    """`caso` com o bloco 'reversa' de `caso_reversa_firm.json`, adaptado a ele.

    O bloco não carrega premissa por eixo: `eixos` são nomes, e a premissa que
    cada eixo resolve em cada rota mora em `reversa.RESOLVER_POR_EIXO` (wacc/ke,
    roic/roe, g, cap). Os quatro eixos seguem como estão; o que se adapta é o
    que o bloco aponta no caso — `cenario` vira o cenário da manchete
    (`cenario_base`, ou o único declarado) — e o `mercado` que a reversa exige:
    `rf`/`erp` do modelo onde o caso não os declara, porque sem eles o gate
    recusaria a reversa por forma, não por limitação."""
    c = copy.deepcopy(caso)
    reversa = copy.deepcopy(_MODELO_DE_REVERSA["reversa"])
    reversa["cenario"] = c.get("cenario_base") or next(iter(c["cenarios"]))
    c["reversa"] = reversa
    mercado = dict(c.get("mercado") or {})
    for campo in CAMPOS_DE_MERCADO_OBRIGATORIOS:
        if mercado.get(campo) is None:
            mercado[campo] = _MODELO_DE_REVERSA["mercado"][campo]
    c["mercado"] = mercado
    return c


# --------------------------------------------------------------------------
# Fatia 5F (D14): variantes compostas, não fixture nova. Uma fixture nova entraria em
# toda parametrização da suíte, e editar fixture é proibido; as travas do catálogo
# (`tests/test_catalogo_apresentacao.py`) iteram as fixtures E estas variantes, para que
# todo padrão novo seja exercido por algum caso real. Cada variante é (fixture-base,
# composição): a composição recebe o caso carregado e devolve uma cópia composta.
# --------------------------------------------------------------------------

def _reversa_sem_raiz(caso: dict) -> dict:
    """A sonda P7 da revisão da 5D (N9): `caso_minimo_firm` com a reversa composta e preço
    0,5. Os três eixos percentuais saem sem raiz (o alvo fica abaixo do mínimo atingível),
    o teto do crescimento gratuito roda e a curva iso-valor fica como limitação publicada;
    o CAP ainda fecha."""
    c = com_bloco_de_reversa_valido(caso)
    c["preco"]["valor"] = 0.5
    return c


def _forward_firm(caso: dict) -> dict:
    """`caso_minimo_firm` com a métrica forward declarada (D5 da 5F): EBITDA de 1.100 no ano
    seguinte, contra 1.000 da métrica-base — a tela forward é o mesmo valor de mercado sobre ela."""
    c = copy.deepcopy(caso)
    c["metrica_forward"] = {"tipo": "EBITDA", "valor": 1100.0, "periodo": "2026E", "fonte": "consenso sintético"}
    return c


def _forward_equity(caso: dict) -> dict:
    """`caso_minimo_equity` com a métrica forward declarada (D5 da 5F): lucro de 560 no ano
    seguinte, contra 500 da métrica-base."""
    c = copy.deepcopy(caso)
    c["metrica_forward"] = {"tipo": "LL", "valor": 560.0, "periodo": "2026E", "fonte": "consenso sintético"}
    return c


def _escala(caso: dict) -> dict:
    """`caso_rampa` com os montantes declarados em milhões (D7 da 5F): a única rota com premissa
    monetária (receita e EBITDA do ano 0, D&A do parque), e com ponte."""
    c = copy.deepcopy(caso)
    c["escala_monetaria"] = "milhoes"
    return c


def _com_conservacao_de_capital(caso: dict, capex_total: float, dwc: float) -> dict:
    c = copy.deepcopy(caso)
    c["conservacao_de_capital"] = {
        "capex_total": {"valor": capex_total, "fonte": "demonstração sintética", "ano_base": "corrente"},
        "dwc": {"valor": dwc, "fonte": "demonstração sintética"},
    }
    return c


def _conservacao_fecha(caso: dict) -> dict:
    """`caso_minimo_firm` (EBITDA 1.000, d 20%, t 25%, g 5%, ROIC 12%) com a conservação de capital
    declarada (D6 da 5F): encargos de 450 — reposição 200, crescimento 250 — contra capex 430 e
    ΔWC 20. Gap zero, sem alerta."""
    return _com_conservacao_de_capital(caso, 430.0, 20.0)


def _conservacao_nao_fecha(caso: dict) -> dict:
    """A mesma companhia com capex 300 e ΔWC zero: gap de −50%, acima do limiar do motor."""
    return _com_conservacao_de_capital(caso, 300.0, 0.0)


def _escolhas(caso: dict) -> dict:
    """`caso_minimo_firm` (preço da manchete R$ 61,91) com três escolhas metodológicas
    declaradas (D1 da 5G), escolhidas para exercer os dois lados do limiar de
    materialidade e o alerta de coerência interna dos cenários:

    - `rentabilidade` com o caso-base no ramo ALTERNATIVO: o retorno do capital novo
      do consenso (ROIC 20%) leva o preço a ≈ R$ 69,72, impacto ≈ +12,6% — acima do
      limiar, material;
    - `crescimento` também no ramo ALTERNATIVO: g de 8% leva a ≈ R$ 67,04, impacto
      ≈ +8,3% — abaixo do limiar. As duas fora da central na mesma direção acendem o
      alerta de empilhamento (`conservadora`: o caso-base vale menos que os dois
      ramos centrais);
    - `ano_de_capex_no_par_d_rir` no ramo CENTRAL, com o gatilho declarado como
      disparado: d de 24% leva a ≈ R$ 58,56, impacto ≈ −5,4%. Central, não entra no
      empilhamento;
    - `caixa_excedente_em_hibrida_financeira` no ramo CENTRAL, sobrepondo uma LINHA DA
      PONTE (Task 1b): o caixa deixa de ser excedente devolvível e vai a zero, a dívida
      líquida sobe 300 e o preço cai para ≈ R$ 58,91. É o alvo de sobreposição que não
      é premissa — sem ele, o caminho `sobreposicoes.<bloco>.<campo>` ficaria ocioso nas
      travas do catálogo.
    """
    c = copy.deepcopy(caso)
    c["escolhas_metodologicas"] = [
        {"chave": "rentabilidade", "no_caso_base": "alternativa",
         "sobreposicoes": {"roic": 20.0}},
        {"chave": "crescimento", "no_caso_base": "alternativa",
         "sobreposicoes": {"g": 8.0}},
        {"chave": "ano_de_capex_no_par_d_rir", "no_caso_base": "central",
         "sobreposicoes": {"da": 24.0},
         "gatilho_disparou": {"observavel": "Capex do guidance de longo prazo acima do capex do ano corrente."}},
        {"chave": "caixa_excedente_em_hibrida_financeira", "no_caso_base": "central",
         "sobreposicoes": {"ponte": {"caixa_e_equivalentes": 0.0}},
         "gatilho_disparou": {"observavel": "Carteira de crédito própria dentro do balanço consolidado."}},
    ]
    return c


def _alternativas(caso: dict) -> dict:
    """`caso_minimo_firm` com as três leituras da 5G Task 2 declaradas de uma vez —
    nenhuma delas se recusa junto das outras, e uma variante só as exerce todas:

    - um segundo cenário (`bull`, ROIC 16% e g 6%) e `cenario_base`, porque ponderar
      exige dois cenários ou mais;
    - `retorno_exigido` de 14 pontos percentuais, que substitui o WACC de 10% do
      cenário da manchete;
    - `pesos_de_probabilidade` 70/30 sobre base e bull;
    - `cross_check` pela rota equity — a oposta da do caso —, com métrica, âncora e
      vetor próprios (a rota equity não atravessa ponte, então o segundo método
      chega a preço sem nada além do que declara aqui).
    """
    c = copy.deepcopy(caso)
    bull = copy.deepcopy(c["cenarios"]["base"])
    bull["ancora"] = "guidance de longo prazo da companhia"
    bull["premissas"] = {**bull["premissas"], "roic": 16.0, "g": 6.0}
    c["cenarios"]["bull"] = bull
    c["cenario_base"] = "base"
    c["retorno_exigido"] = {"taxa": 14.0}
    c["pesos_de_probabilidade"] = {"base": 70.0, "bull": 30.0}
    c["cross_check"] = {
        "rota": "equity",
        "metrica_base": {"tipo": "LL", "valor": 450.0},
        "ancora": "lucro líquido normalizado 2023-2025",
        "premissas": {"g": 5.0, "roe": 15.0, "ke": 12.0, "n": 10, "tv": "convergencia"},
    }
    return c


VARIANTES_DO_CASO: dict[str, tuple[str, Callable[[dict], dict]]] = {
    "reversa_sem_raiz": ("caso_minimo_firm.json", _reversa_sem_raiz),
    "forward_firm": ("caso_minimo_firm.json", _forward_firm),
    "forward_equity": ("caso_minimo_equity.json", _forward_equity),
    "escala": ("caso_rampa.json", _escala),
    "conservacao_fecha": ("caso_minimo_firm.json", _conservacao_fecha),
    "conservacao_nao_fecha": ("caso_minimo_firm.json", _conservacao_nao_fecha),
    "escolhas": ("caso_minimo_firm.json", _escolhas),
    "alternativas": ("caso_minimo_firm.json", _alternativas),
}


def caso_da_variante(nome: str) -> dict:
    """O caso da variante `nome`: a fixture-base carregada (e validada), composta e validada de
    novo — uma variante que o gate recusa não é caso."""
    fixture, compor = VARIANTES_DO_CASO[nome]
    caso = compor(carregar_caso(FIXTURES / fixture))
    validar(caso)
    return caso


def carregar_fixture_ou_variante(nome: str) -> dict:
    """O caso de uma fixture (`caso_*.json`, pelo nome do arquivo) ou de uma variante (pelo nome
    em `VARIANTES_DO_CASO`) — o ponto único por onde as travas iteram as duas coisas."""
    return caso_da_variante(nome) if nome in VARIANTES_DO_CASO else carregar_caso(FIXTURES / nome)


IDIOMA_PADRAO = "pt-BR"
TEXTO_CONCLUSAO_PADRAO = "Valor justo de {{resultados:manchete.preco_acao|moeda}} por ação."
# Sob fronteira de escopo (D3) a conclusão é condicional: citar o preço por ação
# seria o HARD FAIL `fronteira_com_preco_alvo`.
TEXTO_CONCLUSAO_SOB_FRONTEIRA = "Conclusão condicional, sem preço-alvo de manchete sob fronteira de escopo."


def _tese_padrao(resultados: dict) -> dict:
    """Uma Tese válida (D1) para o `resultados` que `avaliar()` acabou de
    publicar — e que não dispara, ela mesma, regra nenhuma (armadilha 2 do
    briefing da Task 2):

    - nenhum dígito em texto nenhum (senão `numero_sem_proveniencia`);
    - vínculos e mecanismos só com blocos econômicos do catálogo, que são
      vocabulário de toda rota (D2), e distintos entre as perguntas (senão
      `tese_dependente_de_uma_premissa`);
    - faixa com nomes de `resultados.cenarios`: a base no cenário da manchete, o
      piso e o teto nos cenários de menor e de maior preço — os três coincidem num
      caso de cenário único —, e nenhuma faixa sob fronteira de escopo (D3);
    - uma premissa decisiva: a primeira premissa da rota, na ordem do catálogo,
      que o cenário da manchete declara;
    - todas as perguntas com `sem_exhibit` — um exhibit passado a
      `montar_entrega` fica fora das perguntas, como antes da 5D.
    """
    blocos = sorted(CATALOGO["blocos"], key=lambda bloco: CATALOGO["blocos"][bloco]["ordem"])
    earning_power, crescimento, custo_de_capital, duracao = blocos[:4]
    cenario_da_manchete = resultados["manchete"]["cenario"]
    premissas_do_cenario = resultados["cenarios"][cenario_da_manchete]["premissas"]
    premissa_decisiva = next(chave for chave in CATALOGO["premissas"][resultados["rota"]]
                             if chave in premissas_do_cenario)
    sem_exhibit = {"razao": "Evidência qualitativa; um gráfico não acrescenta informação."}

    tese = {
        "veredicto": {"texto": "O preço de tela fica abaixo do que o cenário da manchete sustenta."},
        "premissas_decisivas": [
            {"chave": premissa_decisiva, "derivacao": "Calibrada pelo histórico normalizado da companhia."},
        ],
        "positives": [{
            "afirmacao": "A expansão da capacidade sustenta o crescimento do volume.",
            "vetor": "crescimento", "mecanismo": [crescimento],
            "observavel": "Utilização da capacidade instalada.",
            "incorporacao": "refletido",
        }],
        "negatives": [{
            "afirmacao": "A entrada de um concorrente pode comprimir a margem.",
            "vetor": "rentabilidade", "mecanismo": [earning_power],
            "observavel": "Margem bruta trimestral.",
            "incorporacao": "nao_incorporado",
            "razao": "Sem evidência suficiente para calibrar a compressão.",
        }],
        "perguntas": [
            {"id": "moat", "tema": "moat",
             "pergunta": "A vantagem de custo resiste à entrada de um concorrente?",
             "evidencia": "Participação estável frente aos rivais do setor.",
             "observavel": "Perda de participação para um entrante.",
             "vinculo": [duracao], "sem_exhibit": dict(sem_exhibit)},
            {"id": "crescimento", "tema": "crescimento",
             "pergunta": "Quanto a demanda ainda comporta de expansão da capacidade?",
             "evidencia": "Carteira de pedidos acima da capacidade instalada.",
             "observavel": "Utilização da capacidade instalada.",
             "vinculo": [crescimento], "sem_exhibit": dict(sem_exhibit)},
            {"id": "rentabilidade", "tema": "rentabilidade_do_crescimento",
             "pergunta": "O capital da expansão rende acima do seu custo?",
             "evidencia": "Retorno incremental das expansões recentes.",
             "observavel": "Retorno sobre o capital das novas unidades.",
             "vinculo": [crescimento, custo_de_capital], "sem_exhibit": dict(sem_exhibit)},
        ],
        "riscos": [
            {"risco": "Regulação tarifária mais restritiva.", "observavel": "Decisões do regulador setorial."},
        ],
    }
    if resultados["fronteira_de_escopo"] is None:
        precos = {nome: cenario["valor"]["preco_acao"] for nome, cenario in resultados["cenarios"].items()}
        tese["faixa"] = {"piso": min(precos, key=precos.get), "base": cenario_da_manchete,
                         "teto": max(precos, key=precos.get)}
    # Fatia 5F, Task 4 (D12): o julgamento do que está no preço é opcional e só cabe com a
    # reversa; a Tese padrão o declara sempre que ela existe, para a aba Valuation exercê-lo.
    if resultados.get("reversa") is not None:
        tese["o_que_esta_no_preco"] = {
            "julgamento": "A reconciliação que exige menos violência às âncoras observáveis é a do custo de "
                          "capital, e não a do crescimento.",
            "observavel": "O custo de capital implícito nos próximos resultados trimestrais.",
        }
    return tese


# --------------------------------------------------------------------------
# Fatia 5E, Task 2: o ledger padrão e o consenso padrão.
#
# Armadilha 1 do briefing: o ledger que o apoio compõe não pode, ele mesmo,
# disparar regra nenhuma — nem concentração (identidades distintas), nem
# contraprova (a premissa decisiva ganha a de outra identidade), nem estimativa
# (o estatuto sem nenhuma flag), nem reconciliação (o `valor` é o do caso), nem
# referência quebrada. O percurso das folhas e o casamento de padrão abaixo são
# deste apoio, e não os do QC, de propósito: o teste que cruza os dois
# (`tests/test_relatorio_evidencia.py`) só discrimina se as duas derivações do
# mapa forem independentes.
# --------------------------------------------------------------------------

_VOCABULARIOS_DO_LEDGER = CONTRATO_LEDGER["vocabularios"]
# O estatuto sem nenhuma flag: não exige fórmula e não é estimativa.
ESTATUTO_OBSERVADO = next(nome for nome, flags in _VOCABULARIOS_DO_LEDGER["estatutos"].items()
                          if not any(flags.values()))
DATA_DE_ACESSO_PADRAO = "2026-09-11"


def _mesmo_valor(a, b) -> bool:
    """Dois números declarados iguais pela tolerância da reconciliação do QC (as constantes
    nomeadas de `qc.py`)."""
    numeros = all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in (a, b))
    return numeros and math.isclose(a, b, rel_tol=qc.TOLERANCIA_RELATIVA_DE_RECONCILIACAO,
                                    abs_tol=qc.TOLERANCIA_ABSOLUTA_DE_RECONCILIACAO)


def ledger_vazio() -> dict:
    return {"versao_contrato": CONTRATO_LEDGER["versao_contrato"], "registros": [], "lacunas": []}


def _folhas_numericas_do_caso(no, caminho: tuple = ()):
    if isinstance(no, dict):
        for chave, valor in no.items():
            yield from _folhas_numericas_do_caso(valor, caminho + (str(chave),))
    elif isinstance(no, list):
        for indice, valor in enumerate(no):
            yield from _folhas_numericas_do_caso(valor, caminho + (str(indice),))
    elif isinstance(no, (int, float)) and not isinstance(no, bool):
        yield caminho, no


def insumos_do_caso(caso: dict) -> list[tuple[str, float]]:
    """`(caminho, valor)` de toda folha numérica do caso que `catalogo.insumos_do_caso`
    cobre (`*` casa exatamente um segmento; o índice de lista é segmento), na ordem do
    caso."""
    padroes = [tuple(padrao.split(".")) for padrao in CATALOGO["insumos_do_caso"]]
    return [(".".join(caminho), valor) for caminho, valor in _folhas_numericas_do_caso(caso)
            if any(len(padrao) == len(caminho) and all(p in ("*", s) for p, s in zip(padrao, caminho))
                   for padrao in padroes)]


def registro_do_ledger(ident: str, claim: str, identidade: str, valor, **campos) -> dict:
    """Um registro `ledger/1` válido na forma, com o estatuto sem flag, a primeira classe
    de fonte e o primeiro tipo de localizador do contrato; `campos` completa ou
    substitui."""
    registro = {
        "id": ident, "claim": claim,
        "fonte": {"identidade": identidade, "classe": _VOCABULARIOS_DO_LEDGER["classes_de_fonte"][0]},
        "localizador": {"tipo": _VOCABULARIOS_DO_LEDGER["tipos_de_localizador"][0],
                        "valor": f"fonte-de-teste/{ident}"},
        "data_acesso": DATA_DE_ACESSO_PADRAO, "periodo": "2025", "moeda": None, "unidade": "unidade do caso",
        "estatuto": ESTATUTO_OBSERVADO, "valor": valor,
        "justificativa_da_fonte": "A fonte primária do número, a mais próxima do fato.",
    }
    registro.update(campos)
    return registro


def completar_ledger(entrega_dict: dict) -> dict:
    """Acrescenta ao ledger da entrega só o que falta para ela não disparar regra de
    ledger nenhuma — nunca altera um registro que já está lá:

    - um registro por insumo do caso que nenhum `usado_em` nomeia, com o `valor` do
      caso e identidade própria;
    - para cada premissa decisiva da Tese (`cenarios.<manchete.cenario>.premissas.
      <chave>`) sustentada por um registro e sem contraprova que a confirme — de outra
      identidade, com o mesmo valor ou com a divergência reconciliada —, a contraprova,
      com o mesmo claim, período e valor e identidade própria;
    - sem `analise.consenso`, um registro de consenso e o consenso que o cita;
    - para cada dataset de `dados` com `ledger` vazio, o registro que o sustenta,
      citado ali.

    Muta e devolve `entrega_dict`. Uma entrega montada à mão num teste (o exemplo do
    `SKILL.md`, um dataset acrescentado depois de `montar_entrega`) passa por aqui para
    ganhar o ledger do caso real sem perder o que já declarou."""
    ledger = entrega_dict.setdefault("ledger", ledger_vazio())
    registros = ledger["registros"]
    ids = {registro["id"] for registro in registros}

    def _acrescentar(base: str, claim: str, valor, **campos) -> dict:
        ident, sufixo = base, 2
        while ident in ids:
            ident, sufixo = f"{base}#{sufixo}", sufixo + 1
        ids.add(ident)
        registro = registro_do_ledger(ident, claim, f"fonte-{ident}", valor, **campos)
        registros.append(registro)
        return registro

    caso = entrega_dict["caso"]
    nomeados = {caminho for registro in registros for caminho in registro.get("usado_em", [])}
    for caminho, valor in insumos_do_caso(caso):
        if caminho not in nomeados:
            _acrescentar(f"insumo:{caminho}", f"{caminho} do caso", valor, usado_em=[caminho])

    analise = entrega_dict["analise"]
    cenario = entrega_dict["resultados"]["manchete"]["cenario"]
    # 5F (D13): a premissa decisiva de uma parte de SOTP mora no caso em
    # `sotp.partes.<índice>.premissas.<chave>`, com o índice da parte que ela nomeia.
    partes = [parte["nome"] for parte in (entrega_dict["resultados"].get("sotp") or {}).get("partes", [])]
    for premissa in analise.get("premissas_decisivas", []):
        if "parte" in premissa:
            if premissa["parte"] not in partes:
                continue
            caminho = f"sotp.partes.{partes.index(premissa['parte'])}.premissas.{premissa['chave']}"
        else:
            caminho = f"cenarios.{cenario}.premissas.{premissa['chave']}"
        sustentam = [registro for registro in registros if caminho in registro.get("usado_em", [])]
        confirmada = any(registro.get("contraprova_de") == alvo["id"]
                         and registro["fonte"]["identidade"] != alvo["fonte"]["identidade"]
                         and (_mesmo_valor(registro.get("valor"), alvo.get("valor")) or "reconciliacao" in registro)
                         for alvo in sustentam for registro in registros)
        if sustentam and not confirmada:
            alvo = sustentam[0]
            _acrescentar(f"contraprova:{caminho}", alvo["claim"], alvo["valor"], periodo=alvo["periodo"],
                         moeda=alvo["moeda"], unidade=alvo["unidade"], contraprova_de=alvo["id"])

    if "consenso" not in analise:
        consenso = _acrescentar("consenso", "consenso de mercado da métrica-base",
                                (caso.get("metrica_base") or {}).get("valor"))
        analise["consenso"] = {"registros": [consenso["id"]]}

    for dataset_id, dataset in (entrega_dict.get("dados") or {}).items():
        if dataset.get("ledger") == []:
            registro = _acrescentar(f"dados:{dataset_id}", f"série do dataset {dataset_id}", None)
            dataset["ledger"] = [registro["id"]]
    return entrega_dict


def montar_entrega(nome_fixture: str, *, id_execucao: str = "2026-09-11-001",
                    ticker: str | None = None, idioma: str = IDIOMA_PADRAO,
                    texto_conclusao: str | None = None,
                    mutar_caso: Callable[[dict], None] | None = None,
                    dados: dict | None = None,
                    exhibits: list | None = None,
                    tese: dict | None = None,
                    compor_reversa: bool = True,
                    ledger: dict | None = None,
                    consenso: dict | None = None,
                    compor_ledger: bool = True) -> dict:
    """Monta um `entrega.json` válido (dict) a partir de uma fixture de caso.

    Roda `avaliar()` pelo caminho de produção — o `resultados` embutido
    bate com `caso` por construção, então `resultados_nao_correspondem_ao_
    caso` nunca dispara aqui; para exercer essa regra, o teste chamador
    troca `entrega["resultados"]` por um de OUTRA fixture depois de
    receber o dict.

    `texto_conclusao` default cita `manchete.preco_acao` em `moeda` — o
    único número na prosa, sempre com proveniência. Sob fronteira de escopo
    (5D, D3), o default é `TEXTO_CONCLUSAO_SOB_FRONTEIRA`, sem preço.

    `mutar_caso` (onda de correção da revisão final, B2): quando dado, roda
    ANTES de `avaliar()`, mutando o `caso` já carregado in-place (ex.:
    trocar `tv` por um alias legado como 'spread'/'ic' num cenário) -- o
    `resultados` embutido reflete essa mutação por construção (rodou
    `avaliar()` de verdade sobre o caso já mutado), então o hash
    `caso_sha256` continua batendo; nenhum teste precisa forjar
    `resultados` à mão para exercer um caso que o gate aceita mas que usa
    vocabulário fora do canônico.

    `dados`/`exhibits` (fatia 5B, item 5, Task 1, G1/G3): passados só pelos
    testes que exercem a gramática de gráfico -- por padrão (`None`),
    `dados` fica DE FORA da entrega (é o único campo de topo opcional, ver
    `entrega.CHAVES_DE_TOPO_OBRIGATORIAS`) e `exhibits` vira `[]` (campo
    obrigatório em `analise`, mas uma análise sem gráfico nenhum é válida —
    G10 do desenho).

    `tese` (5D, Task 2, D1): os blocos da Tese em `analise`, além de
    `conclusao` e `exhibits` — por padrão (`None`), `_tese_padrao`. Dado, entra
    como está, para que um teste declare exatamente a Tese que quer exercer.

    `compor_reversa` (5D, Task 2, D4): por padrão, depois de `mutar_caso`, o
    bloco `reversa` é composto por `com_bloco_de_reversa_valido` quando o caso
    não o declara e o gate o admite. `False` monta a Análise sem a reversa que o
    gate admite — a entrega que o HARD FAIL `analise_sem_reversa` recusa; não há
    como usá-lo para fazer uma entrega passar.

    `ledger`, `consenso` e `compor_ledger` (5E, Task 2): `ledger` é o ledger de
    partida (por padrão, `ledger_vazio()`) e `consenso`, dado, entra como está em
    `analise.consenso`. Com `compor_ledger=True`, `completar_ledger` acrescenta o que
    falta — por padrão, o ledger inteiro e o consenso. Com `compor_ledger=False`, nada
    é acrescentado: a entrega leva exatamente `ledger` (ou o ledger vazio), `consenso`
    (ou nenhum) e os datasets como vieram — é assim que um teste declara, por exemplo,
    um dataset sem proveniência.
    """
    caso = carregar_caso(FIXTURES / nome_fixture)
    if mutar_caso is not None:
        mutar_caso(caso)
    if compor_reversa and caso.get("reversa") is None and reversa_indisponivel(caso) is None:
        caso = com_bloco_de_reversa_valido(caso)
    resultados = avaliar(caso)

    conclusao_padrao = (TEXTO_CONCLUSAO_PADRAO if resultados["fronteira_de_escopo"] is None
                        else TEXTO_CONCLUSAO_SOB_FRONTEIRA)
    analise = {
        "conclusao": {"texto": texto_conclusao or conclusao_padrao},
        "exhibits": exhibits if exhibits is not None else [],
    }
    analise.update(tese if tese is not None else _tese_padrao(resultados))
    if consenso is not None:
        analise["consenso"] = copy.deepcopy(consenso)

    entrega_dict = {
        "versao_contrato": "entrega/1",
        "execucao": {
            "id": id_execucao,
            "ticker": ticker or caso.get("ticker") or "TESTE3",
            "idioma": idioma,
        },
        "caso": caso,
        "resultados": resultados,
        "analise": analise,
        "ledger": copy.deepcopy(ledger) if ledger is not None else ledger_vazio(),
    }
    if dados is not None:
        entrega_dict["dados"] = copy.deepcopy(dados)
    if compor_ledger:
        completar_ledger(entrega_dict)
    return entrega_dict


def escrever_raiz(raiz: Path, entrega: dict) -> Path:
    """Grava `entrega.json` dentro de `raiz` (cria o diretório se preciso);
    devolve o caminho do arquivo gravado."""
    raiz.mkdir(parents=True, exist_ok=True)
    caminho = raiz / "entrega.json"
    caminho.write_text(json.dumps(entrega, indent=2, ensure_ascii=False) + "\n",
                       encoding="utf-8", newline="\n")
    return caminho


def resultados_de(nome_fixture: str) -> dict:
    """`avaliar()` de outra fixture, para montar o cenário 'resultados de
    outro caso' (`resultados_nao_correspondem_ao_caso`)."""
    return avaliar(carregar_caso(FIXTURES / nome_fixture))
