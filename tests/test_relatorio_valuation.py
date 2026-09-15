"""A aba Valuation no contrato `entrega/1` e as regras da §11 que são dela (fatia 5F, item 5,
Task 4) — sem render.

Ver docs/superpowers/plans/2026-09-15-v4-item5f-valuation.md, com os ajustes do regime de 15/09:
D4 (o eixo obrigatório da reversa sem raiz), D5 (as bases do par forward), D6 (a conservação de
capital), D11 (o ponto central da grade e a sensibilidade pouco informativa), D12 (o julgamento do
que está no preço, opcional) e D13 (a premissa decisiva de uma parte de SOTP).

- FORMA, código 1 (`entrega.carregar`): uma recusa por campo novo.
- CONTEÚDO, código 2 (`qc.avaliar`): cada regra com um caso que dispara e um vizinho que não
  dispara. Nenhuma regra guarda limiar de metodologia: a conservação acende pela chave que o
  catálogo nomeia, o eixo obrigatório pela flag, o ponto central por igualdade exata.

Entregas vêm de `tests/relatorio_apoio.py`, que roda `avaliar()` de verdade sobre uma fixture ou
sobre uma variante composta (`apoio.VARIANTES_DO_CASO`); cada teste recebe a sua cópia. Um teste que
reescreve números publicados confere só o código da regra (`_do_codigo`): o hash do caso continua
batendo, mas a entrega deixa de ser a que o motor produziu.
"""

import copy
import functools
import json
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "skills" / "er-relatorio" / "scripts"))
import entrega  # noqa: E402
import placeholders  # noqa: E402
import qc  # noqa: E402

sys.path.insert(0, str(RAIZ / "tests"))
import relatorio_apoio as apoio  # noqa: E402

CATALOGO = apoio.CATALOGO
IDIOMA = "pt-BR"
# A única fixture com grades de sensibilidade (1D de WACC, 2D de ROIC × g) e reversa declarada.
GRADES = "caso_reversa_firm.json"
# Duas partes de rotas diferentes: "Base instalada" (rampa) e "Expansão" (firm).
SOTP_SAFRA = "caso_sotp_safra.json"
SEM_REVERSA = "caso_rampa.json"


@functools.lru_cache(maxsize=None)
def _entrega_serializada(fonte: str) -> str:
    """`montar_entrega` cacheado (roda o motor por subprocesso), de uma fixture ou de uma variante
    composta, como JSON — cada teste recebe a sua cópia."""
    if fonte in apoio.VARIANTES_DO_CASO:
        fixture, compor = apoio.VARIANTES_DO_CASO[fonte]
        entrega_dict = apoio.montar_entrega(fixture, mutar_caso=lambda caso: caso.update(compor(caso)))
    else:
        entrega_dict = apoio.montar_entrega(fonte)
    return json.dumps(entrega_dict, ensure_ascii=False)


def _entrega(fonte: str = GRADES) -> dict:
    return json.loads(_entrega_serializada(fonte))


def _achados(entrega_dict: dict, catalogo: dict = CATALOGO) -> list:
    return qc.avaliar(entrega_dict, catalogo, apoio.CONTRATO_LEDGER, html=None)


def _do_codigo(achados: list, codigo: str) -> list:
    return [a for a in achados if a.codigo == codigo]


def _carregar(entrega_dict: dict, tmp_path: Path) -> dict:
    raiz = tmp_path / "raiz"
    apoio.escrever_raiz(raiz, entrega_dict)
    return entrega.carregar(raiz, apoio.CONTRATO_LEDGER)


def _renomear(objeto: dict, de: str, para: str) -> None:
    objeto[para] = objeto.pop(de)


# --------------------------------------------------------------------------
# FORMA (código 1): `analise.o_que_esta_no_preco` (D12) e `premissas_decisivas[].parte` (D13).
# --------------------------------------------------------------------------

_JULGAMENTO = {"julgamento": "A reconciliação que exige menos violência às âncoras é a do custo de capital.",
               "observavel": "O custo de capital implícito nos próximos resultados."}

_RECUSAS_DE_FORMA = [
    pytest.param(GRADES, lambda e: e["analise"]["o_que_esta_no_preco"].update(julgamento="   "),
                 ["'analise.o_que_esta_no_preco.julgamento' ausente ou vazio"],
                 id="julgamento-vazio"),
    pytest.param(GRADES, lambda e: e["analise"]["o_que_esta_no_preco"].pop("observavel"),
                 ["campo obrigatório ausente em 'analise.o_que_esta_no_preco': 'observavel'"],
                 id="observavel-ausente"),
    pytest.param(GRADES, lambda e: _renomear(e["analise"]["o_que_esta_no_preco"], "julgamento", "julgamentos"),
                 ["chave desconhecida em 'analise.o_que_esta_no_preco'", "'julgamentos'",
                  "Você quis dizer 'julgamento'?"],
                 id="o-que-esta-no-preco-chave-desconhecida"),
    pytest.param(SEM_REVERSA, lambda e: e["analise"].update(o_que_esta_no_preco=copy.deepcopy(_JULGAMENTO)),
                 ["'analise.o_que_esta_no_preco' declarado sem 'resultados.reversa'"],
                 id="o-que-esta-no-preco-sem-reversa"),
    pytest.param(SOTP_SAFRA, lambda e: e["analise"]["premissas_decisivas"][0].update(parte=""),
                 ["'analise.premissas_decisivas.0.parte' ausente ou vazio"],
                 id="parte-vazia"),
]


@pytest.mark.parametrize("fonte,adulterar,trechos", _RECUSAS_DE_FORMA)
def test_forma_dos_campos_novos_e_recusa_de_contrato_nomeada(fonte, adulterar, trechos, tmp_path):
    entrega_dict = _entrega(fonte)
    _carregar(entrega_dict, tmp_path)  # o vizinho: sem a adulteração, o contrato aceita

    adulterar(entrega_dict)
    with pytest.raises(entrega.EntregaInvalida) as erro:
        _carregar(entrega_dict, tmp_path)
    for trecho in trechos:
        assert trecho in str(erro.value), str(erro.value)


def test_o_julgamento_do_que_esta_no_preco_e_opcional_com_a_reversa(tmp_path):
    """D12 ajustado: com a reversa, a entrega sem o julgamento continua válida no contrato e no QC."""
    entrega_dict = _entrega()
    assert "o_que_esta_no_preco" in entrega_dict["analise"], "a Tese padrão o declara quando há reversa"
    del entrega_dict["analise"]["o_que_esta_no_preco"]
    _carregar(entrega_dict, tmp_path)
    assert [a for a in _achados(entrega_dict) if a.nivel == "HARD_FAIL"] == []


# --------------------------------------------------------------------------
# REQUIRED DISCLOSURE `conservacao_de_capital_nao_fecha` (D6): a chave publicada pela integração.
# --------------------------------------------------------------------------

def _conservacao(entrega_dict: dict) -> tuple[str, dict]:
    (nome, cenario), = entrega_dict["resultados"]["cenarios"].items()
    return nome, cenario["conservacao_capital"]


def test_a_conservacao_que_nao_fecha_e_disclosure_com_o_gap_publicado_o_ano_base_e_o_texto_do_catalogo():
    nao_fecha = _entrega("conservacao_nao_fecha")
    nome, bloco = _conservacao(nao_fecha)
    declaracao = CATALOGO["disclosures"]["conservacao_de_capital"]
    assert bloco["diagnosticos_chaves"] == [declaracao["chave"]]

    achados = _do_codigo(_achados(nao_fecha), "conservacao_de_capital_nao_fecha")
    assert [(a.nivel, a.onde, a.params["cenario"], a.params["gap_fmt"], a.params["ano_base_rotulo"],
             a.params["texto"]) for a in achados] == [
        ("REQUIRED_DISCLOSURE", f"resultados.cenarios.{nome}.conservacao_capital.gap_%", nome,
         placeholders.formatar(bloco["gap_%"], "pp1", IDIOMA),
         CATALOGO["anos_base_do_capex"][bloco["ano_base"]]["rotulo"][IDIOMA], declaracao["texto"][IDIOMA])]

    fecha = _entrega("conservacao_fecha")
    assert _conservacao(fecha)[1]["diagnosticos_chaves"] == []
    assert _do_codigo(_achados(fecha), "conservacao_de_capital_nao_fecha") == []


def test_a_conservacao_acende_pela_chave_que_o_catalogo_nomeia_e_nunca_por_um_limiar_do_relatorio():
    """No molde de `test_o_qc_le_a_declaracao_afeta_e_nunca_o_nome_da_chave`. Os dois sentidos: a entrega
    que fecha (gap publicado zero) acende quando a lista publicada traz a chave, e a que não fecha apaga
    quando o catálogo nomeia outra chave — um QC que comparasse o `gap_%` com um limiar ficaria vermelho
    nos dois."""
    fecha = _entrega("conservacao_fecha")
    nome, bloco = _conservacao(fecha)
    chave = CATALOGO["disclosures"]["conservacao_de_capital"]["chave"]
    bloco["diagnosticos_chaves"] = [chave]
    assert [(a.onde, a.params["gap_fmt"]) for a in _do_codigo(_achados(fecha), "conservacao_de_capital_nao_fecha")] == [
        (f"resultados.cenarios.{nome}.conservacao_capital.gap_%", placeholders.formatar(bloco["gap_%"], "pp1", IDIOMA))]

    nao_fecha = _entrega("conservacao_nao_fecha")
    outra_chave = copy.deepcopy(CATALOGO)
    outra_chave["disclosures"]["conservacao_de_capital"]["chave"] = "degrau_alerta"
    assert _do_codigo(_achados(nao_fecha, outra_chave), "conservacao_de_capital_nao_fecha") == []


def test_um_bloco_de_conservacao_sem_lista_de_chaves_e_hard_fail_nomeado_e_nunca_um_aviso_que_some():
    nao_fecha = _entrega("conservacao_nao_fecha")
    nome, bloco = _conservacao(nao_fecha)
    del bloco["diagnosticos_chaves"]

    achados = _achados(nao_fecha)
    assert [(a.nivel, a.onde) for a in _do_codigo(achados, "diagnostico_sem_chave")] == [
        ("HARD_FAIL", f"resultados.cenarios.{nome}.conservacao_capital.diagnosticos_chaves")]
    assert _do_codigo(achados, "conservacao_de_capital_nao_fecha") == []


# --------------------------------------------------------------------------
# REQUIRED DISCLOSURE `premissa_central_fora_do_ponto_central_da_grade` (D11, leitura (a)).
# --------------------------------------------------------------------------

def _pontos_centrais(entrega_dict: dict) -> list:
    return [(a.nivel, a.onde, a.params["cenario_da_grade"], a.params["cenario_manchete"], a.params["eixos"])
            for a in _do_codigo(_achados(entrega_dict), "premissa_central_fora_do_ponto_central_da_grade")]


def _rotulo(rota: str, premissa: str) -> str:
    return CATALOGO["premissas"][rota][premissa]["rotulo"][IDIOMA]


def test_a_grade_1d_impar_centrada_na_premissa_nao_dispara_e_a_2d_com_eixo_de_comprimento_par_dispara():
    """`caso_reversa_firm`: a grade 1D de WACC tem cinco pontos em torno do WACC do cenário; a 2D tem
    ROIC em quatro pontos (10, 12, 14, 16) em torno de 12 e g em três em torno de 5. Só a 2D dispara, e
    só pelo eixo de ROIC."""
    entrega_dict = _entrega()
    caso = entrega_dict["caso"]
    premissas = caso["cenarios"][caso["sensibilidades"]["cenario"]]["premissas"]
    uma = entrega_dict["resultados"]["sensibilidades"]["grades_1d"][0]
    pontos = [ponto["x"] for ponto in uma["pontos"]]
    assert len(pontos) % 2 == 1 and pontos[len(pontos) // 2] == premissas[uma["premissa"]]

    assert _pontos_centrais(entrega_dict) == [
        ("REQUIRED_DISCLOSURE", "resultados.sensibilidades.grades_2d.0", "base", "base", _rotulo("firm", "roic"))]


@pytest.mark.parametrize("pontos_x,dispara", [
    pytest.param([10.0, 12.0, 14.0], False, id="impar-centrada"),
    pytest.param([10.0, 11.0, 14.0], True, id="impar-com-o-meio-deslocado"),
    pytest.param([8.0, 10.0, 12.0, 14.0], True, id="par-com-a-premissa-na-posicao-do-meio"),
])
def test_o_eixo_esta_centrado_so_com_comprimento_impar_e_a_premissa_no_meio(pontos_x, dispara):
    """O terceiro caso tem a premissa (ROIC 12) no índice `len // 2` de uma lista par: uma regra que
    aceitasse comprimento par como centrado ficaria calada nele."""
    entrega_dict = _entrega()
    entrega_dict["resultados"]["sensibilidades"]["grades_2d"][0]["pontos_x"] = pontos_x
    esperado = [("REQUIRED_DISCLOSURE", "resultados.sensibilidades.grades_2d.0", "base", "base",
                 _rotulo("firm", "roic"))] if dispara else []
    assert _pontos_centrais(entrega_dict) == esperado


def test_a_grade_que_perturba_outro_cenario_que_nao_o_da_manchete_dispara_mesmo_centrada():
    entrega_dict = _entrega()
    caso = entrega_dict["caso"]
    caso["cenarios"]["bull"] = copy.deepcopy(caso["cenarios"]["base"])
    caso["sensibilidades"]["cenario"] = "bull"

    assert _pontos_centrais(entrega_dict) == [
        ("REQUIRED_DISCLOSURE", "resultados.sensibilidades.grades_1d.0", "bull", "base", "—"),
        ("REQUIRED_DISCLOSURE", "resultados.sensibilidades.grades_2d.0", "bull", "base", _rotulo("firm", "roic"))]


# --------------------------------------------------------------------------
# QUALITY WARNING `sensibilidade_pouco_informativa` (D11): a tolerância nomeada do QC.
# --------------------------------------------------------------------------

def test_a_grade_achatada_no_preco_do_cenario_acende_o_warning_e_a_da_fixture_nao():
    entrega_dict = _entrega()
    assert _do_codigo(_achados(entrega_dict), "sensibilidade_pouco_informativa") == []
    preco = entrega_dict["resultados"]["cenarios"]["base"]["valor"]["preco_acao"]
    pontos = entrega_dict["resultados"]["sensibilidades"]["grades_1d"][0]["pontos"]
    assert qc.TOLERANCIA_DE_SENSIBILIDADE_POUCO_INFORMATIVA == 0.01

    for ponto in pontos:
        ponto["valor"] = preco * 1.005
    achados = _do_codigo(_achados(entrega_dict), "sensibilidade_pouco_informativa")
    assert [(a.nivel, a.onde, a.params["cenario"]) for a in achados] == [
        ("QUALITY_WARNING", "resultados.sensibilidades.grades_1d.0", "base")]

    pontos[0]["valor"] = preco * 1.02
    assert _do_codigo(_achados(entrega_dict), "sensibilidade_pouco_informativa") == []


# --------------------------------------------------------------------------
# D4: o eixo obrigatório da reversa sem raiz (REQUIRED DISCLOSURE) e a declaração dos eixos no
# catálogo (HARD FAIL, a regra falha fechada).
# --------------------------------------------------------------------------

def test_o_eixo_obrigatorio_sem_raiz_e_disclosure_com_o_rotulo_do_eixo_e_o_do_motivo():
    sem_raiz = _entrega("reversa_sem_raiz")
    eixos = sem_raiz["resultados"]["reversa"]["eixos"]
    obrigatorios = [nome for nome, info in CATALOGO["eixos_de_reversa"].items() if info["obrigatorio"]]
    assert obrigatorios and all(eixos[nome]["resolucao"]["resolveu"] is False for nome in obrigatorios)

    achados = _do_codigo(_achados(sem_raiz), "eixo_obrigatorio_da_reversa_sem_raiz")
    assert [(a.nivel, a.onde, a.params["rotulo"], a.params["motivo_rotulo"]) for a in achados] == [
        ("REQUIRED_DISCLOSURE", f"resultados.reversa.eixos.{nome}.resolucao.resolveu",
         CATALOGO["eixos_de_reversa"][nome]["rotulo"][IDIOMA],
         CATALOGO["motivos_da_leitura"][eixos[nome]["leitura"]["motivo"]]["rotulo"][IDIOMA])
        for nome in obrigatorios]

    assert _do_codigo(_achados(_entrega()), "eixo_obrigatorio_da_reversa_sem_raiz") == []


def test_o_eixo_obrigatorio_sai_da_flag_do_catalogo_e_nunca_do_nome_do_eixo():
    """A mesma entrega, com a flag trocada no catálogo: o aviso passa a nomear o eixo que a flag declara."""
    sem_raiz = _entrega("reversa_sem_raiz")
    eixos = sem_raiz["resultados"]["reversa"]["eixos"]
    outro = next(nome for nome, info in CATALOGO["eixos_de_reversa"].items()
                 if not info["obrigatorio"] and nome in eixos and eixos[nome]["resolucao"]["resolveu"] is False)
    trocado = copy.deepcopy(CATALOGO)
    for nome, info in trocado["eixos_de_reversa"].items():
        info["obrigatorio"] = nome == outro

    assert [a.params["eixo"] for a in _do_codigo(_achados(sem_raiz, trocado), "eixo_obrigatorio_da_reversa_sem_raiz")] == [
        outro]


@pytest.mark.parametrize("adulterar", [
    pytest.param(lambda catalogo: catalogo.pop("eixos_de_reversa"), id="sem-a-secao"),
    pytest.param(lambda catalogo: catalogo["eixos_de_reversa"]["cap"].pop("obrigatorio"), id="sem-a-flag"),
    pytest.param(lambda catalogo: catalogo["eixos_de_reversa"]["crescimento"]["rotulo"].pop(IDIOMA),
                 id="sem-rotulo-no-idioma"),
])
def test_sem_os_eixos_declarados_no_catalogo_a_regra_do_eixo_obrigatorio_falha_fechada(adulterar):
    sem_raiz = _entrega("reversa_sem_raiz")
    assert _do_codigo(_achados(sem_raiz), "eixos_de_reversa_desconhecidos") == []
    catalogo = copy.deepcopy(CATALOGO)
    adulterar(catalogo)

    achados = _achados(sem_raiz, catalogo)
    assert [(a.nivel, a.onde) for a in _do_codigo(achados, "eixos_de_reversa_desconhecidos")] == [
        ("HARD_FAIL", "resultados.reversa.eixos")]
    assert _do_codigo(achados, "eixo_obrigatorio_da_reversa_sem_raiz") == []

    sem_reversa = _entrega(SEM_REVERSA)
    assert "reversa" not in sem_reversa["resultados"]
    assert _do_codigo(_achados(sem_reversa, catalogo), "eixos_de_reversa_desconhecidos") == []


# --------------------------------------------------------------------------
# D5: `multiplos_com_bases_diferentes` também sobre o par forward.
# --------------------------------------------------------------------------

def test_o_par_forward_em_bases_diferentes_e_hard_fail_e_sem_metrica_forward_nao_ha_par():
    forward = _entrega("forward_firm")
    manchete, tela = forward["resultados"]["manchete"], forward["resultados"]["mercado_tela_forward"]
    assert manchete["multiplo_forward"]["base"] == tela["base"]
    assert _do_codigo(_achados(forward), "multiplos_com_bases_diferentes") == []

    tela["base"] = "pl"
    achados = _do_codigo(_achados(forward), "multiplos_com_bases_diferentes")
    assert [(a.nivel, a.onde, a.params["base_manchete"], a.params["base_mercado_tela"]) for a in achados] == [
        ("HARD_FAIL", "resultados.manchete.multiplo_forward.base", manchete["multiplo_forward"]["base"], "pl")]

    sem_metrica = _entrega()
    assert sem_metrica["resultados"]["mercado_tela_forward"] is None
    sem_metrica["resultados"]["manchete"]["multiplo_forward"]["base"] = "pl"
    assert _do_codigo(_achados(sem_metrica), "multiplos_com_bases_diferentes") == []


# --------------------------------------------------------------------------
# D13: a premissa decisiva de uma parte de SOTP, pelo nome da parte; o vínculo multi-rota; e a
# contraprova no caminho da parte no caso.
# --------------------------------------------------------------------------

def _com_premissa_de_parte(entrega_dict: dict, parte: str, chave: str) -> dict:
    entrega_dict["analise"]["premissas_decisivas"] = [
        {"chave": chave, "parte": parte, "derivacao": "Utilização divulgada pela companhia."}]
    return apoio.completar_ledger(entrega_dict)


def _base_instalada(entrega_dict: dict) -> tuple[int, dict]:
    (indice, parte), = [(indice, parte) for indice, parte in enumerate(entrega_dict["resultados"]["sotp"]["partes"])
                        if parte["rota"] == "rampa"]
    return indice, parte


def test_a_premissa_de_uma_parte_e_o_vinculo_a_ela_emitem_e_a_contraprova_le_o_caminho_da_parte(tmp_path):
    """`util` é premissa da rota rampa, da parte "Base instalada", e não é da rota firm do caso. Como
    premissa decisiva da parte e como vínculo de uma pergunta, nenhum HARD FAIL; a contraprova que o apoio
    compõe no caminho da parte suprime o aviso, e sem ela o aviso nomeia esse caminho."""
    sotp = _entrega(SOTP_SAFRA)
    indice, parte = _base_instalada(sotp)
    assert "util" in parte["premissas"] and "util" not in CATALOGO["premissas"][sotp["resultados"]["rota"]]
    _com_premissa_de_parte(sotp, parte["nome"], "util")
    sotp["analise"]["perguntas"][1]["vinculo"] = ["util"]
    _carregar(sotp, tmp_path)

    achados = _achados(sotp)
    assert [(a.nivel, a.codigo) for a in achados if a.codigo in (
        "premissa_decisiva_fora_do_cenario", "vinculo_fora_do_vocabulario", "sem_contraprova_independente")] == []

    caminho = f"sotp.partes.{indice}.premissas.util"
    sem_contraprova = copy.deepcopy(sotp)
    registros = sem_contraprova["ledger"]["registros"]
    (sustenta,) = [registro for registro in registros if caminho in registro.get("usado_em", [])]
    registros[:] = [registro for registro in registros if registro.get("contraprova_de") != sustenta["id"]]
    assert [(a.nivel, a.onde, a.params["caminho"], a.params["rotulo"])
            for a in _do_codigo(_achados(sem_contraprova), "sem_contraprova_independente")] == [
        ("REQUIRED_DISCLOSURE", "analise.premissas_decisivas.0.chave", caminho, _rotulo("rampa", "util"))]


@pytest.mark.parametrize("parte,chave", [
    pytest.param("Base instalada nova", "util", id="parte-inexistente"),
    pytest.param("Base instalada", "roic", id="premissa-de-outra-rota"),
    pytest.param("Base instalada", "g1", id="premissa-da-rota-nao-declarada-na-parte"),
])
def test_a_premissa_de_uma_parte_que_nao_existe_ou_que_ela_nao_declara_e_hard_fail(parte, chave):
    """`roic` é premissa da rota firm do caso e do cenário consolidado: uma regra que ignorasse a parte
    a aceitaria."""
    sotp = _entrega(SOTP_SAFRA)
    _com_premissa_de_parte(sotp, parte, chave)
    achados = _do_codigo(_achados(sotp), "premissa_decisiva_fora_do_cenario")
    assert [(a.nivel, a.onde, a.params["chave"], a.params["parte"]) for a in achados] == [
        ("HARD_FAIL", "analise.premissas_decisivas.0.chave", chave, parte)]
