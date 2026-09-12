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
from caso import TV_CANON as TV_CANON_GATE  # noqa: E402
from caso import CAMPOS_DA_PONTE, POLITICA_TV_OPCOES, _PREMISSAS_POR_ROTA, carregar  # noqa: E402
import diagnosticos  # noqa: E402

# A2 (onda de correção da revisão final): o conjunto canônico do MOTOR,
# importado em processo — não por subprocesso — com bytecode desligado.
# Mesma dança de `vetores_solver.py` (comentário lá explica por que a
# variável de ambiente `PYTHONDONTWRITEBYTECODE` não basta para um import
# dentro do próprio processo): sem `sys.dont_write_bytecode = True` ANTES
# do import, um `.pyc` dentro de `vendor/` sobreviveria à árvore congelada
# e sombrearia o `.py` no próximo import — a mesma trava que
# `test_vendor_sem_bytecode_compilado` já cobre para o motor chamado por
# subprocesso, aqui repetida para este import direto.
_VENDOR_SCRIPTS = RAIZ / "vendor" / "multiplos-justos" / "scripts"
_bytecode_original = sys.dont_write_bytecode
sys.dont_write_bytecode = True
try:
    sys.path.insert(0, str(_VENDOR_SCRIPTS))
    from justos import TV_CANON as TV_CANON_VENDOR  # noqa: E402
finally:
    sys.dont_write_bytecode = _bytecode_original

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
        "versao_contrato", "metodologia", "idiomas", "blocos", "rotas", "convencoes_terminais",
        "ponte", "premissas", "multiplos", "diagnosticos", "disclosures",
    }


# --------------------------------------------------------------------------
# Fatia 5B, item 5, Task 3 (S2): o waterfall da ponte desenha um rótulo por
# linha de balanço, e quem nomeia é o catálogo -- nunca o JS, nunca o código
# cru ('divida_bruta') na tela. Mesma trava de upgrade das rotas e das
# convenções terminais: uma linha nova em `caso.CAMPOS_DA_PONTE` sem entrada
# aqui reprova na integração, não no relatório.
# --------------------------------------------------------------------------

def test_linhas_da_ponte_do_catalogo_sao_exatamente_as_do_gate():
    assert tuple(CAT["ponte"]) == CAMPOS_DA_PONTE


def test_toda_linha_da_ponte_tem_rotulo_em_todo_idioma():
    for linha, info in CAT["ponte"].items():
        for idioma in CAT["idiomas"]:
            assert info.get("rotulo", {}).get(idioma, "").strip(), (linha, idioma)


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


# --------------------------------------------------------------------------
# Onda de correção da revisão final (review-5a-final.md, achado F2) — A1/A2.
#
# A1: o catálogo ganha `convencoes_terminais` (código canônico -> rótulo por
# idioma), fonte única para o rótulo da convenção terminal — o wrapper
# publica só o código (`manchete.convencao_terminal`,
# `tests/test_valuation_contrato.py`), nunca o relatório escolhe o rótulo. Os
# três `premissas.<rota>.tv.rotulos_opcoes` (firm/equity/rampa) continuam
# existindo (cobrem o INPUT do caso, não só o cenário-base da manchete — o
# relatório de premissas por cenário ainda precisa rotular qualquer 'tv'
# declarada), mas o conteúdo tem de ser EXATAMENTE `convencoes_terminais`:
# sem este teste, editar um lado e esquecer o outro (4 cópias, contando
# `convencoes_terminais`) divergiria em silêncio.
#
# A2: a simulação v10 da revisão (achado D) mostrou que uma convenção
# canônica nova em `caso.TV_CANON` (ou no vendor) passa nos 9 testes deste
# arquivo que existiam antes desta onda — nenhum deles amarra
# `convencoes_terminais`/`politica_tv.opcoes` contra o motor ou o gate, só
# contra o vocabulário do próprio catálogo. Os dois testes abaixo fecham
# esse buraco.
# --------------------------------------------------------------------------

def test_rotulos_de_tv_por_rota_sao_exatamente_convencoes_terminais():
    """A1: `convencoes_terminais` é a fonte única do rótulo de cada convenção
    terminal canônica — `rotulos_opcoes` de 'tv' em CADA rota (firm/equity/
    rampa) tem de ser exatamente igual a ela, não uma cópia independente que
    poderia divergir (a que existia até esta onda: mesmo texto, três vezes)."""
    for rota in ("firm", "equity", "rampa"):
        assert CAT["premissas"][rota]["tv"]["rotulos_opcoes"] == CAT["convencoes_terminais"], rota


def test_convencoes_terminais_do_catalogo_batem_com_motor_e_gate():
    """A2 — a trava que faltava (achado D da simulação v10): as chaves de
    `convencoes_terminais` têm de ser EXATAMENTE o conjunto canônico do
    motor (os valores de `TV_CANON` do vendor, importado em processo com
    bytecode desligado) E o conjunto canônico do gate (`caso.TV_CANON` — a
    cópia que `caso.py` mantém DE PROPÓSITO desacoplada do motor, ver o
    comentário em `caso.py` ao lado de `TV_CANON`). Duas igualdades
    independentes: uma convenção nova em qualquer um dos dois lados sem o
    catálogo revisado reprova aqui — antes desta onda, nada reprovava (ver
    a simulação D no review-5a-final.md: 9/9 verdes com uma convenção nova
    só em `caso.py`)."""
    assert set(CAT["convencoes_terminais"]) == set(TV_CANON_VENDOR.values())
    assert set(CAT["convencoes_terminais"]) == set(TV_CANON_GATE.values())


def test_opcoes_de_politica_tv_do_catalogo_batem_com_o_gate():
    """A2, segunda metade: `politica_tv.opcoes` (só existe na rota equity)
    tem de ser exatamente `caso.POLITICA_TV_OPCOES` — o vocabulário que o
    gate reconhece para essa premissa de escolha."""
    opcoes = set(CAT["premissas"]["equity"]["politica_tv"]["opcoes"])
    assert opcoes == POLITICA_TV_OPCOES


# --------------------------------------------------------------------------
# A4/B8 (achado F7): a explicação de por que o limiar de divergência de base
# do degrau existe (descasamento LL x ROE.VPA) mora no catálogo, ao lado do
# limiar — antes da onda de correção, só o limiar (`limiares`) morava aqui;
# a explicação vivia hardcoded no dicionário do relatório
# (`skills/er-relatorio/assets/i18n/pt-BR.json`), fora do alcance de quem
# muda metodologia. A Parte B consolidou: `qc.py` agora lê limiar E texto só
# de `disclosures.divergencia_de_base_degrau` -- o caminho antigo
# (`limiares.divergencia_de_base_pct_disclosure`, um número solto, sem
# explicação, duplicando o mesmo valor por um segundo caminho) foi removido
# do catálogo; `limiares` desapareceu inteiro por ter ficado vazio.
# --------------------------------------------------------------------------

def test_disclosure_de_divergencia_de_base_tem_limiar_numerico_e_texto_em_todo_idioma():
    disclosure = CAT["disclosures"]["divergencia_de_base_degrau"]
    assert isinstance(disclosure["limiar_pct"], (int, float)) and disclosure["limiar_pct"] > 0
    for idioma in CAT["idiomas"]:
        assert disclosure["texto"].get(idioma, "").strip()


def test_limiares_nao_existe_mais_no_catalogo():
    """B8: o caminho antigo foi removido, não só esvaziado -- uma chave
    'limiares' vazia (`{}`) ainda seria uma superfície de contrato morta;
    o catálogo não a declara mais."""
    assert "limiares" not in CAT
