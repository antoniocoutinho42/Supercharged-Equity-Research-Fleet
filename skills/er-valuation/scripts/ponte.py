"""Composição de linhas de balanço declaradas para net debt.

Este módulo NÃO faz cálculo de valor. Sua responsabilidade é somar as linhas
de balanço declaradas — cada uma com sinal explícito — para produzir o scalar
`nd` que o motor congelado recebe. O motor faz `Equity = EV - nd`; a ponte é
apenas a decomposição daquele scalar, com cada parcela registrada para o
waterfall.

`caso.py` valida a PRESENÇA das linhas; `ponte.py` define a ORDEM e o SINAL
delas — um para validação, outro para soma. Nada além de um teste no import
manteria as duas listas juntas; uma divergência silenciosa seria fatal. Linha
ausente levanta erro em vez de virar zero implícito — a validação de presença
é responsabilidade de `caso.py`, não deste módulo.
"""

from caso import CAMPOS_DA_PONTE

SINAIS: tuple = (
    ("divida_bruta", 1),
    ("caixa_e_equivalentes", -1),
    ("outros_ativos", -1),
    ("outros_passivos", 1),
    ("minoritarios", 1),
)

# Guarda de consistência: `caso.py` valida presença, `ponte.py` define ordem
# e sinal. Duas listas descrevendo o mesmo conjunto. Divergência é erro
# fatal — importação faz a guarda, nunca silencia.
if tuple(rotulo for rotulo, _ in SINAIS) != CAMPOS_DA_PONTE:
    raise ImportError(
        "SINAIS (ponte.py) e CAMPOS_DA_PONTE (caso.py) divergiram — "
        "a ponte validada e a ponte somada tem de ser a mesma"
    )


def compor(ponte: dict) -> dict:
    """Soma linhas de balanço declaradas em net debt e parcelas de waterfall.

    Args:
        ponte: Dicionário com linhas de balanço como números finitos positivos
               (ou zero). KeyError se alguma linha faltar — validação de
               presença é do `caso.py`.

    Returns:
        Dicionário com:
        - "nd_efetivo": float, a soma das linhas com seus sinais
        - "parcelas": lista de {"rotulo": str, "valor": float, "sinal": int}
                      na ordem do waterfall, cada parcela reproduz a linha
                      com seu sinal para exibição
    """
    parcelas = []
    nd_efetivo = 0.0

    for rotulo, sinal in SINAIS:
        valor = ponte[rotulo]  # KeyError se ausente
        parcelas.append({
            "rotulo": rotulo,
            "valor": valor,
            "sinal": sinal,
        })
        nd_efetivo += valor * sinal

    return {
        "nd_efetivo": nd_efetivo,
        "parcelas": parcelas,
    }
