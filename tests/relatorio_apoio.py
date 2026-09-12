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
"""

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
from caso import carregar as carregar_caso  # noqa: E402

_PADRAO_ESTILO_BLOCO = re.compile(r'(<style\b[^>]*>)(.*?)(</style\s*>)', re.IGNORECASE | re.DOTALL)


def prosa_da_pagina(html_texto: str) -> str:
    """A página com o MIOLO de todo `<script>`/`<style>` neutralizado — o
    escopo certo para toda asserção sobre a PROSA que o relatório escreveu.

    B6 (onda de correção da revisão final, achado F10): a regra de PRODUÇÃO
    (`placeholder_malformado`) sempre esteve certa -- varre
    `qc._campos_de_prosa`, nunca a página. Foram os TESTES que confundiram
    "nenhum placeholder cru sobrou" com "nenhum `}}` na página": uma página
    com exhibit tem 50 ocorrências de `}}`, todas do uPlot minificado, e no
    dia em que a 5C/5D rodasse essas asserções sobre uma entrega com
    gráfico elas ficariam vermelhas pelo bundle -- com o conserto natural
    (enfraquecer a asserção) apagando a regra que importa. Escopo, não lista
    de exclusão por arquivo: `qc._sem_conteudo_de_script` já existe e não
    envelhece a cada asset novo."""
    return _PADRAO_ESTILO_BLOCO.sub(
        lambda m: m.group(1) + m.group(3), qc._sem_conteudo_de_script(html_texto))

IDIOMA_PADRAO = "pt-BR"
TEXTO_CONCLUSAO_PADRAO = "Valor justo de {{resultados:manchete.preco_acao|moeda}} por ação."


def montar_entrega(nome_fixture: str, *, id_execucao: str = "2026-09-11-001",
                    ticker: str | None = None, idioma: str = IDIOMA_PADRAO,
                    texto_conclusao: str | None = None,
                    mutar_caso: Callable[[dict], None] | None = None,
                    dados: dict | None = None,
                    exhibits: list | None = None) -> dict:
    """Monta um `entrega.json` válido (dict) a partir de uma fixture de caso.

    Roda `avaliar()` pelo caminho de produção — o `resultados` embutido
    bate com `caso` por construção, então `resultados_nao_correspondem_ao_
    caso` nunca dispara aqui; para exercer essa regra, o teste chamador
    troca `entrega["resultados"]` por um de OUTRA fixture depois de
    receber o dict.

    `texto_conclusao` default cita `manchete.preco_acao` em `moeda` — o
    único número na prosa, sempre com proveniência.

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
    G10 do desenho). Isto preserva TODO teste existente que chama
    `montar_entrega` sem os dois argumentos novos: a entrega continua
    idêntica à de antes desta fatia, byte a byte.
    """
    caso = carregar_caso(FIXTURES / nome_fixture)
    if mutar_caso is not None:
        mutar_caso(caso)
    resultados = avaliar(caso)

    entrega_dict = {
        "versao_contrato": "entrega/1",
        "execucao": {
            "id": id_execucao,
            "ticker": ticker or caso.get("ticker") or "TESTE3",
            "idioma": idioma,
        },
        "caso": caso,
        "resultados": resultados,
        "analise": {
            "conclusao": {"texto": texto_conclusao or TEXTO_CONCLUSAO_PADRAO},
            "exhibits": exhibits if exhibits is not None else [],
        },
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
