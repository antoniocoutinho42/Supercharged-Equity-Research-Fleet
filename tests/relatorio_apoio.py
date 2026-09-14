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
"""

import copy
import json
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
from caso import CAMPOS_DE_MERCADO_OBRIGATORIOS, reversa_indisponivel  # noqa: E402
from caso import carregar as carregar_caso  # noqa: E402

CATALOGO = json.loads(
    (RAIZ / "skills" / "er-valuation" / "assets" / "catalogo_apresentacao.json").read_text(encoding="utf-8"))

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
    return tese


def montar_entrega(nome_fixture: str, *, id_execucao: str = "2026-09-11-001",
                    ticker: str | None = None, idioma: str = IDIOMA_PADRAO,
                    texto_conclusao: str | None = None,
                    mutar_caso: Callable[[dict], None] | None = None,
                    dados: dict | None = None,
                    exhibits: list | None = None,
                    tese: dict | None = None,
                    compor_reversa: bool = True) -> dict:
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
        "ledger": [],
        "ficha_tecnica": {},
    }
    if dados is not None:
        entrega_dict["dados"] = dados
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
