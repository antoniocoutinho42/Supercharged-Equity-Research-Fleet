"""Classificador de diagnósticos do motor: mensagem -> chave pública (A5).

Promovido do teste de paridade da 4C (`tests/test_paridade_wrapper_js.py`,
antiga função `_classificar`) para função pública da integração — o
relatório (fatias 5B–5D) precisa das CHAVES para decidir severidade, bloco e
rótulo (catálogo de apresentação, Task 2 desta fatia), nunca da prosa do
motor. Uma fonte só a partir de agora: o teste de paridade passa a chamar
esta função em vez de manter a própria cópia.

Vocabulário: `assets/diagnosticos_chaves.json`, uma lista de
`{"chave": str, "prefixo": str}` — a mesma lista que `motor_espelho.js` e o
harness de paridade da 4C já usam. Casamento por PREFIXO
(`mensagem.startswith(prefixo)`), nunca por igualdade nem substring no meio
da frase — mesma disciplina do teste que esta função substitui.

Este módulo NÃO calcula nada e NÃO chama o motor: só classifica uma string
que o motor já produziu. Lido uma única vez, na hora do import — o arquivo é
read-only (`assets/`) e não muda durante a vida do processo.
"""

import json
from pathlib import Path

_CAMINHO_CHAVES = Path(__file__).resolve().parent.parent / "assets" / "diagnosticos_chaves.json"
_CHAVES_E_PREFIXOS: tuple[dict, ...] = tuple(
    json.loads(_CAMINHO_CHAVES.read_text(encoding="utf-8")))

# Todas as chaves do arquivo, na ordem declarada — vocabulário público que o
# catálogo de apresentação (Task 2 desta fatia) confronta: `set(CAT["diagnosticos"])
# == set(diagnosticos.CHAVES) | AVISOS_RAMPA`.
CHAVES: tuple[str, ...] = tuple(c["chave"] for c in _CHAVES_E_PREFIXOS)


def classificar(mensagem: str) -> str | None:
    """A chave cujo `prefixo` casa com `mensagem` (`mensagem.startswith(prefixo)`).

    `None` quando nenhum prefixo casa (mensagem nova, fora do vocabulário —
    o tripwire de troca de vendor que `test_toda_mensagem_do_motor_casa_
    com_exatamente_uma_chave`, em `tests/test_paridade_wrapper_js.py`, já
    trava) ou quando mais de um casa (prefixo ambíguo — dois prefixos que
    deveriam se distinguir colidiram). Nos dois casos `None` é a resposta
    certa: esta função não adivinha qual chave o chamador quis dizer. Quem
    chama decide o que fazer com uma mensagem sem chave única — o builder
    do relatório (fatia 5A, Task 3) trata `null` aqui como HARD FAIL, nunca
    inventa uma chave.
    """
    casadas = [c["chave"] for c in _CHAVES_E_PREFIXOS if mensagem.startswith(c["prefixo"])]
    if len(casadas) == 1:
        return casadas[0]
    return None
