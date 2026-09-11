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
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
FIXTURES = RAIZ / "tests" / "fixtures"

sys.path.insert(0, str(RAIZ / "skills" / "er-valuation" / "scripts"))
from avaliar import avaliar  # noqa: E402
from caso import carregar as carregar_caso  # noqa: E402

IDIOMA_PADRAO = "pt-BR"
TEXTO_CONCLUSAO_PADRAO = "Valor justo de {{resultados:manchete.preco_acao|moeda}} por ação."


def montar_entrega(nome_fixture: str, *, id_execucao: str = "2026-09-11-001",
                    ticker: str | None = None, idioma: str = IDIOMA_PADRAO,
                    texto_conclusao: str | None = None) -> dict:
    """Monta um `entrega.json` válido (dict) a partir de uma fixture de caso.

    Roda `avaliar()` pelo caminho de produção — o `resultados` embutido
    bate com `caso` por construção, então `resultados_nao_correspondem_ao_
    caso` nunca dispara aqui; para exercer essa regra, o teste chamador
    troca `entrega["resultados"]` por um de OUTRA fixture depois de
    receber o dict.

    `texto_conclusao` default cita `manchete.preco_acao` em `moeda` — o
    único número na prosa, sempre com proveniência.
    """
    caso = carregar_caso(FIXTURES / nome_fixture)
    resultados = avaliar(caso)

    return {
        "versao_contrato": "entrega/1",
        "execucao": {
            "id": id_execucao,
            "ticker": ticker or caso.get("ticker") or "TESTE3",
            "idioma": idioma,
        },
        "caso": caso,
        "resultados": resultados,
        "analise": {"conclusao": {"texto": texto_conclusao or TEXTO_CONCLUSAO_PADRAO}},
        "ledger": [],
        "ficha_tecnica": {},
    }


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
