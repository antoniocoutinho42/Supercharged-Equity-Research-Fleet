"""Contrato `ledger/1` do `er-evidencia` (fatia 5E, item 5, Task 1).

Ver docs/superpowers/plans/2026-09-14-v4-item5e-evidencia.md, D1. A §3.2 do
desenho faz do `er-evidencia` o dono do schema do ledger, e o contrato mora em
`skills/er-evidencia/assets/contrato_ledger.json` como DADO: as chaves de cada
nível, obrigatórias e opcionais, e os vocabulários fechados. O relatório valida
um ledger contra o contrato lido e decide pelas flags que ele declara — "exige
fórmula", "é estimativa", "lacuna que vira disclosure" —, nunca pelo nome de um
estatuto ou de uma materialidade: a regra de doutrina é declarada, como o
`afeta` das limitações na 5D, e nunca inferida pelo relatório.

Os testes abaixo travam a forma do asset. O conteúdo dos vocabulários é
doutrina da evidência; só as classes de fonte são amarradas, por igualdade de
conjunto, ao texto do desenho que as enumera.
"""

import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CONTRATO_LEDGER = RAIZ / "skills" / "er-evidencia" / "assets" / "contrato_ledger.json"

# Os nomes pelos quais o relatório lê o contrato (Task 2). Sem eles, um nível ou um
# vocabulário ausente deixaria as checagens de forma abaixo vacuamente verdes.
NIVEIS = {"ledger", "registro", "fonte", "localizador", "reconciliacao", "conflito", "lacuna"}
VOCABULARIOS = {"classes_de_fonte", "tipos_de_localizador", "estatutos", "materialidades", "ancoras_do_consenso"}
FLAGS_DE_ESTATUTO = {"exige_formula", "e_estimativa"}
FLAGS_DE_MATERIALIDADE = {"exige_disclosure"}

# §6.1 do desenho, "Fontes admissíveis": cada classe do contrato ao lado do termo que
# ela traduz. A última não está na §6.1: a §18.9 manda tratar a resposta do usuário
# como evidência a verificar, nunca como fato — ela entra no ledger como fonte, com
# classe própria, e não se confunde com o documento que o usuário fornece.
CLASSES_DE_FONTE_DO_DESENHO = {
    "filing": "filings (§6.1)",
    "ri": "RI (§6.1)",
    "release": "releases (§6.1)",
    "transcript": "transcripts (§6.1)",
    "apresentacao": "apresentações (§6.1)",
    "regulador": "reguladores (§6.1)",
    "api": "APIs e conectores MCP (§6.1)",
    "relatorio_setorial": "industry reports (§6.1)",
    "governo": "fontes governamentais (§6.1)",
    "imprensa_especializada": "imprensa especializada (§6.1)",
    "web": "web (§6.1)",
    "documento_do_usuario": "documentos fornecidos pelo usuário (§6.1)",
    "resposta_do_usuario": "resposta do usuário, evidência a verificar (§18.9)",
}


def _sem_chave_repetida(pares: list) -> dict:
    """`object_pairs_hook` da leitura: o `json` do Python fica com a última de duas
    chaves iguais e cala a primeira — um estatuto ou uma materialidade declarados duas
    vezes seriam vocabulário repetido que nenhuma checagem sobre o dict enxergaria."""
    chaves = [chave for chave, _valor in pares]
    repetidas = sorted({chave for chave in chaves if chaves.count(chave) > 1})
    if repetidas:
        raise ValueError(f"chave repetida num objeto do contrato: {repetidas}")
    return dict(pares)


def _contrato() -> dict:
    return json.loads(CONTRATO_LEDGER.read_text(encoding="utf-8"), object_pairs_hook=_sem_chave_repetida)


def test_versao_niveis_e_vocabularios_do_contrato():
    contrato = _contrato()
    assert set(contrato) == {"versao_contrato", "niveis", "vocabularios"}, sorted(contrato)
    assert contrato["versao_contrato"] == "ledger/1"
    assert set(contrato["niveis"]) == NIVEIS, set(contrato["niveis"]) ^ NIVEIS
    assert set(contrato["vocabularios"]) == VOCABULARIOS, set(contrato["vocabularios"]) ^ VOCABULARIOS


def test_todo_nivel_declara_obrigatorias_e_opcionais_disjuntas_e_sem_repeticao():
    for nome, nivel in _contrato()["niveis"].items():
        assert isinstance(nivel, dict) and set(nivel) == {"obrigatorias", "opcionais"}, (nome, nivel)
        for lado in ("obrigatorias", "opcionais"):
            chaves = nivel[lado]
            assert isinstance(chaves, list), (nome, lado, chaves)
            assert all(isinstance(chave, str) and chave and chave.strip() == chave for chave in chaves), (
                nome, lado, chaves)
            assert len(set(chaves)) == len(chaves), (nome, lado, "chave repetida", chaves)
        comuns = set(nivel["obrigatorias"]) & set(nivel["opcionais"])
        assert not comuns, (nome, "chave obrigatória e opcional ao mesmo tempo", sorted(comuns))


def test_todo_vocabulario_e_nao_vazio_e_sem_repeticao():
    """Lista, ou objeto quando cada entrada carrega flags: nunca vazio, entradas textuais,
    sem repetição. A repetição dentro de um objeto é recusada na leitura
    (`_sem_chave_repetida`)."""
    for nome, vocabulario in _contrato()["vocabularios"].items():
        assert isinstance(vocabulario, (list, dict)) and vocabulario, (nome, vocabulario)
        entradas = list(vocabulario)
        assert all(isinstance(entrada, str) and entrada and entrada.strip() == entrada for entrada in entradas), (
            nome, entradas)
        assert len(set(entradas)) == len(entradas), (nome, "entrada repetida", entradas)


def test_todo_estatuto_declara_as_duas_flags_e_ha_estimativa_e_formula():
    """A Task 2 decide "exige fórmula" por `exige_formula` e "é estimativa" (o disclosure
    `insumo_estimado`) por `e_estimativa` — nunca pelo nome do estatuto. Toda entrada
    declara as duas, booleanas, e há ao menos um estatuto de cada: sem eles, as regras que
    leem as flags nunca disparariam."""
    estatutos = _contrato()["vocabularios"]["estatutos"]
    for nome, flags in estatutos.items():
        assert isinstance(flags, dict) and set(flags) == FLAGS_DE_ESTATUTO, (nome, flags)
        assert all(isinstance(valor, bool) for valor in flags.values()), (nome, flags)
    assert any(flags["e_estimativa"] for flags in estatutos.values()), "nenhum estatuto é estimativa"
    assert any(flags["exige_formula"] for flags in estatutos.values()), "nenhum estatuto exige fórmula"


def test_toda_materialidade_declara_se_a_lacuna_exige_disclosure():
    """Mesma regra para a lacuna: a Task 2 decide "lacuna que vira disclosure" por
    `exige_disclosure`, nunca pelo nome da materialidade."""
    materialidades = _contrato()["vocabularios"]["materialidades"]
    for nome, flags in materialidades.items():
        assert isinstance(flags, dict) and set(flags) == FLAGS_DE_MATERIALIDADE, (nome, flags)
        assert isinstance(flags["exige_disclosure"], bool), (nome, flags)
    assert any(flags["exige_disclosure"] for flags in materialidades.values()), "nenhuma materialidade exige disclosure"


def test_classes_de_fonte_sao_as_do_desenho():
    classes = set(_contrato()["vocabularios"]["classes_de_fonte"])
    assert classes == set(CLASSES_DE_FONTE_DO_DESENHO), classes ^ set(CLASSES_DE_FONTE_DO_DESENHO)
