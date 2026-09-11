"""Contrato `catalogo/1` (fatia 5A, item 5, Task 2).

Ver docs/superpowers/plans/2026-09-11-v4-item5a-contratos-builder.md, seção
"Task 2", para as decisões de conteúdo (bloco/unidade/entrada de cada
premissa, severidade de diagnóstico, limiar de disclosure). Os testes abaixo
são as travas de upgrade: trocar o vendor, acrescentar premissa ao gate,
acrescentar chave ao classificador ou o wrapper passar a emitir um múltiplo
novo sem revisar o catálogo reprova AQUI, na integração — nunca no relatório.
"""

import json
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
FIXTURES = RAIZ / "tests" / "fixtures"
sys.path.insert(0, str(RAIZ / "skills" / "er-valuation" / "scripts"))
from avaliar import avaliar  # noqa: E402
from caso import _PREMISSAS_POR_ROTA, carregar  # noqa: E402
import diagnosticos  # noqa: E402

CAT = json.loads(
    (RAIZ / "skills" / "er-valuation" / "assets" / "catalogo_apresentacao.json").read_text(encoding="utf-8"))
MANIFEST = json.loads(
    (RAIZ / "skills" / "er-multiplos-justos" / "manifest_vendor.json").read_text(encoding="utf-8"))
AVISOS_RAMPA = {"aviso_colheita", "aviso_delator", "aviso_gp"}
CASOS = sorted(p.name for p in FIXTURES.glob("caso_*.json"))


def test_versao_da_metodologia_bate_com_o_vendor():
    """Trava de upgrade: trocar o vendor sem revisar o catalogo reprova AQUI, na integracao."""
    assert CAT["metodologia"]["versao"] == MANIFEST["versao"]


def test_premissas_do_catalogo_sao_exatamente_as_do_gate():
    assert {r: set(p) for r, p in CAT["premissas"].items()} == {r: set(p) for r, p in _PREMISSAS_POR_ROTA.items()}


def test_diagnosticos_do_catalogo_sao_exatamente_os_do_classificador():
    assert set(CAT["diagnosticos"]) == set(diagnosticos.CHAVES) | AVISOS_RAMPA


def test_todo_rotulo_existe_em_todo_idioma_declarado():
    def rotulos(no):
        if isinstance(no, dict):
            if "rotulo" in no:
                yield no["rotulo"]
            for v in no.values():
                yield from rotulos(v)
    for r in rotulos(CAT):
        for idioma in CAT["idiomas"]:
            assert r.get(idioma, "").strip(), r


def test_todo_bloco_referenciado_existe():
    blocos = set(CAT["blocos"])
    for rota in CAT["premissas"].values():
        assert {p["bloco"] for p in rota.values()} <= blocos
    assert {d["bloco"] for d in CAT["diagnosticos"].values() if d["bloco"]} <= blocos


# --------------------------------------------------------------------------
# Testes extras listados pelo plano (Calibração): cobertura de chave de
# múltiplo em todas as fixtures; chaves de topo exatas do catálogo.
# --------------------------------------------------------------------------

def test_toda_chave_de_multiplo_emitida_pelas_fixtures_esta_no_catalogo():
    """`multiplos` de cada cenário, `manchete.multiplo.chave` e
    `mercado_tela.chave`, em toda fixture — nenhuma chave que o wrapper de
    fato emite pode faltar em `CAT["multiplos"]` (upgrade tripwire: o
    wrapper passando a emitir uma chave nova sem catálogo revisado reprova
    aqui)."""
    vistas = set()
    for nome in CASOS:
        r = avaliar(carregar(FIXTURES / nome))
        for cenario in r["cenarios"].values():
            vistas.update(cenario.get("multiplos", {}))
        if "multiplo" in r["manchete"]:
            vistas.add(r["manchete"]["multiplo"]["chave"])
        vistas.add(r["mercado_tela"]["chave"])
    assert vistas, "nenhuma chave de múltiplo vista — fixtures vazias?"
    assert vistas <= set(CAT["multiplos"]), vistas - set(CAT["multiplos"])


def test_chaves_de_topo_do_catalogo():
    assert set(CAT.keys()) == {
        "versao_contrato", "metodologia", "idiomas", "blocos", "rotas", "premissas",
        "multiplos", "diagnosticos", "limiares",
    }


# --------------------------------------------------------------------------
# Task 4 (fatia 5A, item 5): rótulos de rota e de opção de premissa de
# escolha — sem eles o cabeçalho da Valuation exibiria código cru ("firm",
# "gordon") em vez de rótulo. O relatório só lê; quem nomeia é o catálogo.
# --------------------------------------------------------------------------

def test_toda_rota_do_gate_tem_rotulo_em_todo_idioma():
    """Mesma trava de upgrade de `test_premissas_do_catalogo_sao_exatamente_as_do_gate`,
    agora para `CAT["rotas"]`: uma rota nova em `_PREMISSAS_POR_ROTA` sem entrada aqui
    reprova na integração, nunca no relatório."""
    assert set(CAT["rotas"]) == set(_PREMISSAS_POR_ROTA)
    for rota, info in CAT["rotas"].items():
        for idioma in CAT["idiomas"]:
            assert info.get("rotulo", {}).get(idioma, "").strip(), (rota, idioma)


def test_toda_opcao_de_premissa_de_escolha_tem_rotulo_em_todo_idioma():
    """Toda premissa com `"entrada": "escolha"` declara `rotulos_opcoes` cobrindo
    CADA entrada de `opcoes`, em todo idioma declarado — sem isso o relatório
    exibiria o código interno da opção ('gordon', 'book', 'continua'...) cru."""
    encontrou_alguma = False
    for rota, premissas in CAT["premissas"].items():
        for nome, info in premissas.items():
            if info.get("entrada") != "escolha":
                continue
            encontrou_alguma = True
            opcoes = set(info.get("opcoes", []))
            rotulos_opcoes = info.get("rotulos_opcoes", {})
            assert opcoes, (rota, nome, "premissa de escolha sem 'opcoes'")
            assert set(rotulos_opcoes) == opcoes, (rota, nome, rotulos_opcoes.keys(), opcoes)
            for opcao in opcoes:
                for idioma in CAT["idiomas"]:
                    assert rotulos_opcoes[opcao].get(idioma, "").strip(), (rota, nome, opcao, idioma)
    assert encontrou_alguma, "nenhuma premissa de escolha encontrada — teste vacuamente verde?"
