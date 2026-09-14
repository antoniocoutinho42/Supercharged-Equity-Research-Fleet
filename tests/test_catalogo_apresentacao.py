"""Contrato `catalogo/1` (fatia 5A, item 5, Task 2).

Ver docs/superpowers/plans/2026-09-11-v4-item5a-contratos-builder.md, seção
"Task 2", para as decisões de conteúdo (bloco/unidade/entrada de cada
premissa, severidade de diagnóstico, limiar de disclosure). Os testes abaixo
são as travas de upgrade: trocar o vendor, acrescentar premissa ao gate,
acrescentar chave ao classificador ou o wrapper passar a emitir um múltiplo
novo sem revisar o catálogo reprova AQUI, na integração — nunca no relatório.
"""

import functools
import itertools
import json
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
FIXTURES = RAIZ / "tests" / "fixtures"
sys.path.insert(0, str(RAIZ / "skills" / "er-valuation" / "scripts"))
from avaliar import _CHAVE_DIVERGENCIA_DE_BASE, _CHAVES_DO_DEGRAU_ORDEM, avaliar  # noqa: E402
from caso import TV_CANON as TV_CANON_GATE  # noqa: E402
from caso import CAMPOS_DA_PONTE, POLITICA_TV_OPCOES, _PREMISSAS_POR_ROTA, carregar  # noqa: E402
from caso import CLASSES_DE_FRONTEIRA_DE_ESCOPO, LIMITACOES_DE_REVERSA, reversa_indisponivel  # noqa: E402
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
# Fatia 5C, item 5, Task 3 (T1/T2): as chaves que o WRAPPER dá aos dois alertas do
# degrau (`ALERTA`/`ALERTA_RiR`, prosa do motor sem chave) — e, desde a onda de
# correção da revisão final da 5C (F1), a da divergência de base acima do limiar da
# integração. Derivadas da constante que as publica (`_CHAVES_DO_DEGRAU_ORDEM`, montada
# em `avaliar.py` a partir das mesmas constantes que `_chaves_do_degrau` usa), nunca de
# uma lista à mão.
CHAVES_DO_DEGRAU = set(_CHAVES_DO_DEGRAU_ORDEM)
CASOS = sorted(p.name for p in FIXTURES.glob("caso_*.json"))


def test_versao_da_metodologia_bate_com_o_vendor():
    """Trava de upgrade: trocar o vendor sem revisar o catalogo reprova AQUI, na integracao."""
    assert CAT["metodologia"]["versao"] == MANIFEST["versao"]


def test_premissas_do_catalogo_sao_exatamente_as_do_gate():
    assert {r: set(p) for r, p in CAT["premissas"].items()} == {r: set(p) for r, p in _PREMISSAS_POR_ROTA.items()}


def test_diagnosticos_do_catalogo_sao_exatamente_os_do_classificador():
    """Trava de upgrade dos diagnósticos: todo vocabulário de chave que a
    integração publica tem entrada no catálogo, e nada além dele — as chaves
    do classificador, os avisos da rampa e (fatia 5C) as chaves que o wrapper
    publica em `degrau.diagnosticos_chaves` — os dois alertas do degrau e a
    divergência de base acima do limiar."""
    assert CHAVES_DO_DEGRAU, "constante do wrapper vazia — a união ficaria vacuamente igual"
    assert set(CAT["diagnosticos"]) == set(diagnosticos.CHAVES) | AVISOS_RAMPA | CHAVES_DO_DEGRAU


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
        "unidades", "ponte", "premissas", "multiplos", "diagnosticos", "disclosures", "recusas",
        "fronteiras_de_escopo", "limitacoes", "conclusoes_de_valor",
    }


# --------------------------------------------------------------------------
# Fatia 5D, Task 1 (D3/D4): o relatório mostra a classe da fronteira de escopo
# e cada limitação pelo rótulo daqui, nunca pela chave crua — e as chaves são
# as do gate. Mesma trava de upgrade das rotas e da ponte: uma classe nova em
# `caso.CLASSES_DE_FRONTEIRA_DE_ESCOPO`, ou uma limitação nova em
# `caso.LIMITACOES_DE_REVERSA`, sem entrada aqui reprova na integração.
# --------------------------------------------------------------------------

def _rotulos_em_todo_idioma(secao: str) -> None:
    for chave, info in CAT[secao].items():
        for idioma in CAT["idiomas"]:
            assert info.get("rotulo", {}).get(idioma, "").strip(), (secao, chave, idioma)


def test_fronteiras_de_escopo_do_catalogo_sao_exatamente_as_classes_do_gate():
    assert set(CAT["fronteiras_de_escopo"]) == CLASSES_DE_FRONTEIRA_DE_ESCOPO
    _rotulos_em_todo_idioma("fronteiras_de_escopo")


def test_limitacoes_do_catalogo_sao_exatamente_as_que_reversa_indisponivel_pode_devolver():
    """O registro que `reversa_indisponivel` consulta tem de ser exatamente o
    catálogo, e toda chave que ela de fato devolve sobre as fixtures tem de
    estar nele — uma chave devolvida por fora do registro também reprova."""
    assert set(CAT["limitacoes"]) == set(LIMITACOES_DE_REVERSA)
    devolvidas = {reversa_indisponivel(carregar(FIXTURES / nome)) for nome in CASOS} - {None}
    assert devolvidas, "nenhuma fixture com limitação — trava vacuamente verde?"
    assert devolvidas <= set(CAT["limitacoes"]), devolvidas - set(CAT["limitacoes"])
    _rotulos_em_todo_idioma("limitacoes")


def test_toda_limitacao_declara_o_bloco_que_suprime_e_as_da_reversa_sao_as_do_gate():
    """Fatia 5D, Task 2 (E3). O QC do relatório decide entre o HARD FAIL
    `analise_sem_reversa` e o disclosure `limitacao_metodologica` lendo `afeta`
    — o bloco de `resultados` que a limitação suprime —, nunca o nome da chave:
    que `reversa_com_degrau` é uma limitação DE REVERSA é saber da integração.
    A trava: toda limitação declara `afeta`; as que declaram `"reversa"` são
    exatamente o registro que `reversa_indisponivel` consulta; e tudo o que ela
    devolve sobre as fixtures está entre elas. Uma limitação de reversa nova no
    gate sem a declaração, ou uma declaração que esqueça uma delas, reprova aqui."""
    for chave, info in CAT["limitacoes"].items():
        assert isinstance(info.get("afeta"), str) and info["afeta"].strip(), chave
    da_reversa = {chave for chave, info in CAT["limitacoes"].items() if info["afeta"] == "reversa"}
    assert da_reversa == set(LIMITACOES_DE_REVERSA), da_reversa ^ set(LIMITACOES_DE_REVERSA)
    devolvidas = {reversa_indisponivel(carregar(FIXTURES / nome)) for nome in CASOS} - {None}
    assert devolvidas, "nenhuma fixture com limitação — trava vacuamente verde?"
    assert devolvidas <= da_reversa, devolvidas - da_reversa


# --------------------------------------------------------------------------
# Fatia 5D, onda de correção da revisão final (F2, a raiz; emenda E3). O que é
# CONCLUSÃO DE VALOR — o número que, sob fronteira de escopo, a Tese não pode
# afirmar e a Valuation só mostra como leitura condicional — é saber da
# integração, nunca do relatório: a D3 o reconhecia pelo nome do campo
# (`preco_acao`), e a célula da grade, o upside e o múltiplo justo passavam. O
# catálogo publica o mapa `conclusoes_de_valor`, `{<unidade>: [<padrão>]}`: cada
# padrão é um caminho de `resultados` em que `*` casa exatamente um segmento, e
# a unidade de cada família é do vocabulário `unidades` — a mesma que a grade de
# sensibilidade publica para as suas células. O QC e a tela do relatório só leem
# o mapa. As travas abaixo o amarram ao que o wrapper publica de fato, fixture a
# fixture: toda folha numérica é conclusão de valor pelo mapa ou tem, aqui, a
# razão declarada para não ser — um número novo sem classificação reprova AQUI.
# --------------------------------------------------------------------------

# O que o wrapper publica e NÃO é conclusão de valor, com a razão. Além destas
# famílias, toda folha que ecoa o caso (mesmo caminho, mesmo valor) é o que o
# caso declara. `**` casa zero ou mais segmentos — só aqui, nunca no mapa.
_NAO_SAO_CONCLUSAO_DE_VALOR: dict[str, tuple[str, ...]] = {
    "leitura de mercado — o preço e o múltiplo de tela, que a §14 mantém sob fronteira": (
        "preco.**", "mercado_tela.**"),
    "o que o preço embute — a reversa, que a §14 mantém sob fronteira": (
        "reversa.**",),
    "a ponte da dívida líquida — as linhas de balanço do caso e a soma delas": (
        "ponte.**", "sotp.ponte_unica.**"),
    "a métrica de referência, o eixo e o diagnóstico de cada ponto de grade": (
        "sensibilidades.*.*.metrica_de_referencia.**",
        "sensibilidades.*.*.pontos.*.x", "sensibilidades.*.*.pontos.*.diag.**",
        "sensibilidades.*.*.celulas.*.*.x", "sensibilidades.*.*.celulas.*.*.y",
        "sensibilidades.*.*.celulas.*.*.diag.**"),
    "o diagnóstico do degrau — capacidade, rentabilidade pós-degrau, transição, eficiência e divergência de base": tuple(
        f"cenarios.*.degrau.{campo}"
        for campo in ("h", "rentabilidade_pos_%", "fator_transicao", "m", "divergencia_de_base_%")),
    "a trajetória e as checagens da composição bifásica, por cenário e por parte de SOTP": tuple(
        f"{dono}.{campo}"
        for dono in ("cenarios.*", "sotp.partes.*")
        for campo in ("T_rampa", "alfa", "beta", "capacidade_receita", "checks_internos.**", "d2_fase2_%",
                      "d_trajetoria_fase1_%.**", "g1_%", "g2_%", "n_total", "rir2_%", "rir_fase1_%.**",
                      "roic2_%")),
    "o efeito, sobre o múltiplo de uma parte, da convenção terminal alternativa (C7)": (
        "sotp.partes.*.efeito_c7_alternativa_gp_%",),
}
_ECOA_O_CASO = "o que o caso declara — premissa, preço, métrica, bloco declarado"


@functools.lru_cache(maxsize=None)
def _caso_e_resultados_serializados(nome: str) -> str:
    """`avaliar()` roda o motor por subprocesso; cacheado, e devolvido como JSON
    para que cada teste receba a sua cópia."""
    caso = carregar(FIXTURES / nome)
    return json.dumps({"caso": caso, "resultados": avaliar(caso)}, ensure_ascii=False)


def _caso_e_resultados(nome: str) -> tuple[dict, dict]:
    par = json.loads(_caso_e_resultados_serializados(nome))
    return par["caso"], par["resultados"]


def _folhas_numericas(no, caminho: tuple = ()):
    """`(caminho, valor)` de toda folha numérica, com o índice de lista como segmento
    — a mesma forma do caminho de um placeholder."""
    if isinstance(no, dict):
        for chave, valor in no.items():
            yield from _folhas_numericas(valor, caminho + (str(chave),))
    elif isinstance(no, list):
        for indice, valor in enumerate(no):
            yield from _folhas_numericas(valor, caminho + (str(indice),))
    elif isinstance(no, (int, float)) and not isinstance(no, bool):
        yield caminho, no


def _casa(padrao: tuple, caminho: tuple) -> bool:
    """`*` casa exatamente um segmento; `**` casa zero ou mais."""
    if not padrao:
        return not caminho
    if padrao[0] == "**":
        return any(_casa(padrao[1:], caminho[inicio:]) for inicio in range(len(caminho) + 1))
    return bool(caminho) and padrao[0] in ("*", caminho[0]) and _casa(padrao[1:], caminho[1:])


def _familias_que_cobrem(caminho: tuple) -> list[tuple[str, str]]:
    return [(unidade, padrao) for unidade, padroes in CAT["conclusoes_de_valor"].items()
            for padrao in padroes if _casa(tuple(padrao.split(".")), caminho)]


def _ecoa_o_caso(caso: dict, caminho: tuple, valor) -> bool:
    atual = caso
    for segmento in caminho:
        if isinstance(atual, dict) and segmento in atual:
            atual = atual[segmento]
        elif isinstance(atual, list) and segmento.isdigit() and int(segmento) < len(atual):
            atual = atual[int(segmento)]
        else:
            return False
    return not isinstance(atual, bool) and atual == valor


def test_o_mapa_de_conclusoes_de_valor_declara_padroes_por_unidade_do_catalogo():
    """A forma do mapa: cada família é uma unidade do vocabulário `unidades`, com
    padrões de caminho bem formados (`*` por segmento, nunca `**`), sem repetição, e
    nenhum caminho concreto casado por famílias de unidades diferentes — um número tem
    uma unidade só."""
    mapa = CAT["conclusoes_de_valor"]
    assert isinstance(mapa, dict) and mapa, mapa
    assert set(mapa) <= set(CAT["unidades"]), set(mapa) - set(CAT["unidades"])
    declarados = []
    for unidade, padroes in mapa.items():
        assert isinstance(padroes, list) and padroes, unidade
        for padrao in padroes:
            assert isinstance(padrao, str), (unidade, padrao)
            segmentos = tuple(padrao.split("."))
            assert all(segmento and segmento.strip() == segmento and segmento != "**"
                       for segmento in segmentos), (unidade, padrao)
            declarados.append((unidade, segmentos))
    assert len({segmentos for _unidade, segmentos in declarados}) == len(declarados), "padrão repetido no mapa"
    for (unidade_a, a), (unidade_b, b) in itertools.combinations(declarados, 2):
        casam_o_mesmo_caminho = len(a) == len(b) and all(x == y or "*" in (x, y) for x, y in zip(a, b))
        assert unidade_a == unidade_b or not casam_o_mesmo_caminho, (unidade_a, ".".join(a), unidade_b, ".".join(b))


def test_o_mapa_nao_cobre_o_multiplo_de_tela_nem_o_que_o_caso_declara():
    """§14: sob fronteira de escopo a entrega mantém a leitura de mercado — o múltiplo
    de tela — e nada do que o caso declara (premissa, preço, métrica, bloco) é
    conclusão de valor."""
    vistas = {"mercado_tela": 0, "caso": 0}
    for nome in CASOS:
        caso, resultados = _caso_e_resultados(nome)
        for caminho, valor in _folhas_numericas(resultados):
            if caminho[0] == "mercado_tela":
                vistas["mercado_tela"] += 1
                assert not _familias_que_cobrem(caminho), (nome, ".".join(caminho))
            if _ecoa_o_caso(caso, caminho, valor):
                vistas["caso"] += 1
                assert not _familias_que_cobrem(caminho), (nome, ".".join(caminho), valor)
    assert all(vistas.values()), f"trava vacuamente verde: {vistas}"


def test_toda_folha_numerica_publicada_e_conclusao_de_valor_pelo_mapa_ou_tem_razao_para_nao_ser():
    """A trava de upgrade do mapa, fixture a fixture: toda folha numérica que o wrapper
    publica é conclusão de valor pelo mapa ou tem a razão declarada em
    `_NAO_SAO_CONCLUSAO_DE_VALOR` (ou ecoa o caso) — nunca as duas, nunca nenhuma. Um
    número novo (a 5F publica valor ponderado e cross-check) reprova aqui até alguém
    decidir de que lado ele está; e nenhum padrão do mapa fica sem folha que o exerça."""
    sem_classificacao, nos_dois_lados, padroes_exercidos = [], [], set()
    for nome in CASOS:
        caso, resultados = _caso_e_resultados(nome)
        for caminho, valor in _folhas_numericas(resultados):
            familias = _familias_que_cobrem(caminho)
            padroes_exercidos.update(padrao for _unidade, padrao in familias)
            razoes = [razao for razao, padroes in _NAO_SAO_CONCLUSAO_DE_VALOR.items()
                      if any(_casa(tuple(padrao.split(".")), caminho) for padrao in padroes)]
            if _ecoa_o_caso(caso, caminho, valor):
                razoes.append(_ECOA_O_CASO)
            folha = f"{nome}: {'.'.join(caminho)} = {valor!r}"
            if familias and razoes:
                nos_dois_lados.append(f"{folha} — mapa {familias}; não é, por {razoes}")
            elif not familias and not razoes:
                sem_classificacao.append(folha)
    assert not sem_classificacao, (
        "número publicado sem classificação — é conclusão de valor (catalogo.conclusoes_de_valor) "
        "ou não é (declare a razão em _NAO_SAO_CONCLUSAO_DE_VALOR)?\n" + "\n".join(sem_classificacao))
    assert not nos_dois_lados, "\n".join(nos_dois_lados)
    declarados = {padrao for padroes in CAT["conclusoes_de_valor"].values() for padrao in padroes}
    assert not declarados - padroes_exercidos, (
        f"padrão do mapa que nenhuma fixture publica: {sorted(declarados - padroes_exercidos)}")


def test_celula_de_grade_e_coberta_pela_familia_da_unidade_que_a_grade_publica():
    """Uma fonte da verdade: a grade de sensibilidade declara a unidade das suas células
    (`unidade`, hoje "preço por ação"), e o mapa declara a família de cada caminho. As
    duas declarações amarradas: toda célula é coberta por exatamente uma família, e é a
    da unidade que a grade publica. Um v10 que troque a métrica da grade reprova aqui
    até o mapa ser revisto."""
    vistas = {"grades_1d": 0, "grades_2d": 0}
    for nome in CASOS:
        _caso, resultados = _caso_e_resultados(nome)
        for caminho, _valor in _folhas_numericas(resultados):
            if not (_casa(("sensibilidades", "*", "*", "pontos", "*", "valor"), caminho)
                    or _casa(("sensibilidades", "*", "*", "celulas", "*", "*", "valor"), caminho)):
                continue
            grade = resultados["sensibilidades"][caminho[1]][int(caminho[2])]
            assert grade["unidade"] in CAT["unidades"], (nome, grade["unidade"])
            assert [unidade for unidade, _padrao in _familias_que_cobrem(caminho)] == [grade["unidade"]], (
                nome, ".".join(caminho), grade["unidade"], _familias_que_cobrem(caminho))
            vistas[caminho[1]] += 1
    assert all(vistas.values()), f"trava vacuamente verde: {vistas}"


def test_todo_motivo_de_recusa_tem_rotulo_em_todo_idioma():
    """Onda de correção da revisão final da 5C (F2): o laboratório diz por que
    um cenário foi recusado, com o rótulo que o catálogo dá ao código que a
    fachada publica. A trava contra a FACHADA (o conjunto exato de motivos) mora
    em `tests/test_espelho_fachada_js.py`, que roda node; esta confere só que
    nenhum motivo fica sem texto em algum idioma declarado."""
    assert CAT["recusas"], "catálogo sem motivos de recusa"
    for codigo, info in CAT["recusas"].items():
        for idioma in CAT["idiomas"]:
            assert info.get("rotulo", {}).get(idioma, "").strip(), (codigo, idioma)


# --------------------------------------------------------------------------
# A4 (onda de correção da revisão final, achado F7): `unidades` é o
# vocabulário de UNIDADE da integração — o que o motor publica em cada grade
# (`sensibilidades.unidade`) e o que o catálogo declara em cada premissa.
# O relatório formata um número lendo a unidade dele, em vez de decorar
# "célula de grade é número de 2 casas"; uma unidade fora deste vocabulário
# é HARD FAIL nomeado, na camada certa.
# --------------------------------------------------------------------------

def test_toda_unidade_de_premissa_numerica_esta_no_vocabulario_de_unidades():
    """Uma premissa nova com unidade nova (ou uma unidade renomeada) sem
    entrada em `unidades` reprova AQUI — e não com um eixo de matriz
    formatado ao acaso. Só premissa numérica: 'escolha'/'booleano' não são
    número e nunca viram eixo de grade (`caso._PREMISSAS_NAO_NUMERICAS`)."""
    for rota, premissas in CAT["premissas"].items():
        for nome, info in premissas.items():
            if info.get("entrada") != "numero":
                continue
            assert info["unidade"] in CAT["unidades"], (rota, nome, info.get("unidade"))


def test_toda_unidade_publicada_pelas_grades_das_fixtures_esta_no_catalogo():
    """Mesma trava de upgrade de `test_toda_chave_de_multiplo_emitida_pelas_
    fixtures_esta_no_catalogo`, agora para a `unidade` que o motor publica em
    cada grade de sensibilidade: um v10 que troque a métrica da grade reprova
    aqui, na integração, antes de o relatório desenhar outro número."""
    vistas = set()
    for nome in CASOS:
        r = avaliar(carregar(FIXTURES / nome))
        sensibilidades = r.get("sensibilidades") or {}
        for chave in ("grades_1d", "grades_2d"):
            for grade in sensibilidades.get(chave) or []:
                vistas.add(grade["unidade"])
    assert vistas, "nenhuma grade de sensibilidade nas fixtures — teste vacuamente verde?"
    assert vistas <= set(CAT["unidades"]), vistas - set(CAT["unidades"])


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

#
# Onda de correção da revisão final da 5C (F1): o LIMIAR saiu daqui. Ele decidia
# "acima do limiar" dentro da QC do relatório, e o laboratório ao vivo não tinha
# como mover o disclosure junto com o preço. A decisão agora é da integração
# (`avaliar._LIMIAR_DIVERGENCIA_DE_BASE_PCT`, espelhado em `motor_espelho.js` e
# travado contra ela em `tests/test_paridade_wrapper_js.py`), que publica a chave
# `degrau_divergencia_de_base`; o disclosure só NOMEIA a chave que o dispara e
# carrega o texto. Vocabulário fechado: um `limiar_pct` que voltasse aqui seria uma
# segunda fonte numérica, que ninguém lê e que diverge em silêncio.
# --------------------------------------------------------------------------

def test_disclosure_de_divergencia_de_base_nomeia_a_chave_da_integracao_sem_limiar():
    disclosure = CAT["disclosures"]["divergencia_de_base_degrau"]
    assert set(disclosure) == {"chave", "texto"}, sorted(disclosure)
    assert disclosure["chave"] == _CHAVE_DIVERGENCIA_DE_BASE
    assert disclosure["chave"] in CAT["diagnosticos"]
    for idioma in CAT["idiomas"]:
        assert disclosure["texto"].get(idioma, "").strip()


def test_limiares_nao_existe_mais_no_catalogo():
    """B8: o caminho antigo foi removido, não só esvaziado -- uma chave
    'limiares' vazia (`{}`) ainda seria uma superfície de contrato morta;
    o catálogo não a declara mais."""
    assert "limiares" not in CAT
