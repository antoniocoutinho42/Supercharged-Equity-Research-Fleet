"""A aba Valuation no contrato `entrega/1` e as regras da §11 que são dela (fatia 5F, item 5,
Task 4) — sem render.

Ver docs/superpowers/plans/2026-09-15-v4-item5f-valuation.md, com os ajustes do regime de 15/09:
D4 (o eixo obrigatório da reversa sem raiz), D5 (as bases do par forward), D6 (a conservação de
capital), D11 (o ponto central da grade e a sensibilidade pouco informativa), D12 (o julgamento do
que está no preço, opcional) e D13 (a premissa decisiva de uma parte de SOTP).

E a fatia 5G (docs/superpowers/plans/2026-09-15-v4-item5g-alternativas.md), Task 3: os três blocos
opcionais que a Tese ganha (D1/D4/D5) e as duas regras do painel de escolhas metodológicas —
`escolha_sem_razao` e `escolhas_desconhecidas`, os dois HARD FAIL.

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

# Só para as travas de vocabulário da Task 4: o que a INTEGRAÇÃO pode publicar (a posição do
# caso-base de uma escolha, a direção do empilhamento) tem de ter rótulo no dicionário do
# relatório. `relatorio_apoio` já põe `er-valuation/scripts` no path; testes não são a camada do
# relatório, e a fronteira da E3 (`tests/test_relatorio_fronteira.py`) varre só `scripts/`.
import avaliar as avaliar_da_integracao  # noqa: E402
import caso as caso_da_integracao  # noqa: E402

CATALOGO = apoio.CATALOGO
IDIOMA = "pt-BR"
# A única fixture com grades de sensibilidade (1D de WACC, 2D de ROIC × g) e reversa declarada.
GRADES = "caso_reversa_firm.json"
# Duas partes de rotas diferentes: "Base instalada" (rampa) e "Expansão" (firm).
SOTP_SAFRA = "caso_sotp_safra.json"
SEM_REVERSA = "caso_rampa.json"
# Fatia 5G: as duas variantes compostas do lote A — quatro escolhas metodológicas
# precificadas, e as três leituras opcionais (retorno exigido, pesos, cross-check).
ESCOLHAS = "escolhas"
ALTERNATIVAS = "alternativas"
# As duas juntas, sobre a mesma fixture: a única entrega que exercita as quatro seções novas
# da aba de uma vez (e, com elas, os quatro rótulos condicionais).
TODAS_AS_ALTERNATIVAS = f"{ESCOLHAS}+{ALTERNATIVAS}"


@functools.lru_cache(maxsize=None)
def _entrega_serializada(fonte: str) -> str:
    """`montar_entrega` cacheado (roda o motor por subprocesso), de uma fixture, de uma variante
    composta ou de VÁRIAS variantes da mesma fixture (nomes separados por `+`, aplicadas na
    ordem), como JSON — cada teste recebe a sua cópia."""
    nomes = fonte.split("+")
    if nomes[0] in apoio.VARIANTES_DO_CASO:
        fixtures = {apoio.VARIANTES_DO_CASO[nome][0] for nome in nomes}
        assert len(fixtures) == 1, f"variantes de fixtures diferentes não compõem: {fonte}"

        def _compor(caso: dict) -> None:
            for nome in nomes:
                caso.update(apoio.VARIANTES_DO_CASO[nome][1](caso))

        entrega_dict = apoio.montar_entrega(fixtures.pop(), mutar_caso=_compor)
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
    # Fatia 5G, Task 3 (D1/D4/D5): os três blocos novos, um campo cada.
    pytest.param(ESCOLHAS, lambda e: e["analise"]["escolhas"][0].update(razao="   "),
                 ["'analise.escolhas.0.razao' ausente ou vazio"],
                 id="razao-de-escolha-vazia"),
    pytest.param(ESCOLHAS, lambda e: e["analise"]["escolhas"][0].update(chave="rentabilidad"),
                 ["'analise.escolhas.0.chave' dá razão a uma escolha que "
                  "'resultados.escolhas_metodologicas' não publica", "'rentabilidad'",
                  "Você quis dizer 'rentabilidade'?"],
                 id="razao-de-escolha-que-nao-foi-publicada"),
    pytest.param(GRADES, lambda e: e["analise"].update(escolhas=[{"chave": "rentabilidade", "razao": "A âncora."}]),
                 ["'analise.escolhas' declarado sem escolha nenhuma em 'resultados.escolhas_metodologicas'"],
                 id="escolhas-sem-escolha-publicada"),
    pytest.param(ALTERNATIVAS, lambda e: e["analise"].update(cross_check={"ausente": {"razao": "Sem vetor coerente."}}),
                 ["'analise.cross_check' declarado com 'resultados.cross_check' publicado"],
                 id="ausencia-do-cross-check-com-cross-check-publicado"),
    pytest.param(GRADES, lambda e: e["analise"].update(cross_check={"ausente": {"razao": "Sem vetor.", "motivo": "x"}}),
                 ["chave desconhecida em 'analise.cross_check.ausente'", "'motivo'"],
                 id="cross-check-ausente-com-chave-desconhecida"),
    pytest.param(GRADES, lambda e: e["analise"].update(reteste_terminal={"resultado": "mantido", "texto": "A regra."}),
                 ["'analise.reteste_terminal.resultado' fora do vocabulário fechado", "'mantido'",
                  "Você quis dizer 'mantida'?"],
                 id="reteste-terminal-fora-do-vocabulario"),
    # Fatia 5H, Task 2 (D3): o produto da execução, opcional e de vocabulário fechado.
    pytest.param(GRADES, lambda e: e["execucao"].update(produto="leitura"),
                 ["'execucao.produto' fora do vocabulário fechado", "'leitura'",
                  "analise, leitura_de_preco"],
                 id="produto-fora-do-vocabulario"),
    pytest.param(GRADES, lambda e: e["execucao"].update(produtos="analise"),
                 ["chave desconhecida em 'execucao'", "'produtos'", "Você quis dizer 'produto'?"],
                 id="produto-com-nome-errado"),
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


# ==========================================================================
# Fatia 5G, Task 3 (D1): o painel de escolhas metodológicas no QC — a razão de cada escolha
# publicada (§8.2/§18.3) e a declaração delas no catálogo (a regra falha fechada). E os três
# textos novos na lista de prosa auditada (D1/D4/D5).
# ==========================================================================

def _rotulo_da_escolha(chave: str) -> str:
    return CATALOGO["escolhas_metodologicas"][chave]["rotulo"][IDIOMA]


def _sem_razao(entrega_dict: dict, chaves: list) -> list:
    """Os achados `escolha_sem_razao` da entrega com as razões de `chaves` retiradas."""
    sem = copy.deepcopy(entrega_dict)
    sem["analise"]["escolhas"] = [escolha for escolha in sem["analise"]["escolhas"]
                                  if escolha["chave"] not in chaves]
    return [(a.nivel, a.onde, a.params["chave"], a.params["rotulo"])
            for a in _do_codigo(_achados(sem), "escolha_sem_razao")]


def test_a_escolha_publicada_sem_razao_reprova_com_o_rotulo_do_catalogo_e_com_a_razao_passa():
    """§18.3: nenhuma escolha que a metodologia deixa em aberto recebe default. A variante
    publica quatro escolhas; a Tese padrão dá razão às quatro, e a entrega passa. Retirada a
    razão de uma, só ela acende, no seu índice — uma regra que olhasse a lista inteira, ou
    que parasse na primeira, não distinguiria isso."""
    escolhas = _entrega(ESCOLHAS)
    publicadas = [escolha["chave"] for escolha in escolhas["resultados"]["escolhas_metodologicas"]]
    assert len(publicadas) > 2, "a variante precisa de mais de duas escolhas para o teste discriminar"
    assert [escolha["chave"] for escolha in escolhas["analise"]["escolhas"]] == publicadas
    assert _do_codigo(_achados(escolhas), "escolha_sem_razao") == []

    assert _sem_razao(escolhas, [publicadas[1]]) == [
        ("HARD_FAIL", "resultados.escolhas_metodologicas.1.chave", publicadas[1],
         _rotulo_da_escolha(publicadas[1]))]
    assert _sem_razao(escolhas, publicadas) == [
        ("HARD_FAIL", f"resultados.escolhas_metodologicas.{indice}.chave", chave, _rotulo_da_escolha(chave))
        for indice, chave in enumerate(publicadas)]

    sem_escolhas = _entrega()
    assert sem_escolhas["resultados"]["escolhas_metodologicas"] == []
    assert "escolhas" not in sem_escolhas["analise"]
    assert _do_codigo(_achados(sem_escolhas), "escolha_sem_razao") == []


@pytest.mark.parametrize("adulterar", [
    pytest.param(lambda catalogo: catalogo.pop("escolhas_metodologicas"), id="sem-a-secao"),
    pytest.param(lambda catalogo: catalogo["escolhas_metodologicas"]["rentabilidade"]["rotulo"].pop(IDIOMA),
                 id="sem-rotulo-no-idioma"),
    pytest.param(lambda catalogo: catalogo["escolhas_metodologicas"]["crescimento"].pop("gatilho"),
                 id="sem-o-gatilho"),
])
def test_sem_as_escolhas_declaradas_no_catalogo_a_regra_da_razao_falha_fechada(adulterar):
    """No molde de `eixos_de_reversa_desconhecidos`: sem rótulo e gatilho no idioma, o painel
    sairia com o código cru da escolha. A entrega do teste é a que acenderia `escolha_sem_razao`
    nas quatro — sob o catálogo adulterado, nenhuma acende, e sai o HARD FAIL fechado."""
    escolhas = _entrega(ESCOLHAS)
    del escolhas["analise"]["escolhas"]
    assert len(_do_codigo(_achados(escolhas), "escolha_sem_razao")) == 4
    assert _do_codigo(_achados(escolhas), "escolhas_desconhecidas") == []

    catalogo = copy.deepcopy(CATALOGO)
    adulterar(catalogo)
    achados = _achados(escolhas, catalogo)
    assert [(a.nivel, a.onde, a.params["idioma"]) for a in _do_codigo(achados, "escolhas_desconhecidas")] == [
        ("HARD_FAIL", "resultados.escolhas_metodologicas", IDIOMA)]
    assert _do_codigo(achados, "escolha_sem_razao") == []

    sem_escolhas = _entrega()
    assert _do_codigo(_achados(sem_escolhas, catalogo), "escolhas_desconhecidas") == []


_TEXTO_SEM_DIGITO = "A âncora observável sustenta a leitura sem forçar nenhuma premissa."
_TEXTO_COM_DIGITO = "O consenso projeta retorno de 20% sobre o capital novo."


@pytest.mark.parametrize("fonte,instalar,onde", [
    pytest.param(ESCOLHAS, lambda e, texto: e["analise"]["escolhas"][0].update(razao=texto),
                 "analise.escolhas.0.razao", id="razao-da-escolha"),
    pytest.param(GRADES, lambda e, texto: e["analise"].update(cross_check={"ausente": {"razao": texto}}),
                 "analise.cross_check.ausente.razao", id="razao-da-ausencia-do-cross-check"),
    pytest.param(GRADES, lambda e, texto: e["analise"].update(
        reteste_terminal={"resultado": "mantida", "texto": texto}),
        "analise.reteste_terminal.texto", id="texto-do-reteste-terminal"),
])
def test_os_textos_novos_sao_prosa_auditada_e_um_digito_solto_neles_e_numero_sem_proveniencia(
        fonte, instalar, onde, tmp_path):
    entrega_dict = _entrega(fonte)
    instalar(entrega_dict, _TEXTO_SEM_DIGITO)
    _carregar(entrega_dict, tmp_path)
    assert dict(placeholders.campos_de_prosa(entrega_dict)).get(onde) == _TEXTO_SEM_DIGITO
    assert _do_codigo(_achados(entrega_dict), "numero_sem_proveniencia") == []

    instalar(entrega_dict, _TEXTO_COM_DIGITO)
    assert [(a.nivel, a.onde) for a in _do_codigo(_achados(entrega_dict), "numero_sem_proveniencia")] == [
        ("HARD_FAIL", onde)]

# ==========================================================================
# Task 5 (D15): a aba Valuation renderizada, na ordem da §9, e o par forward e a premissa de parte na
# Tese. Toda asserção lê o TEXTO que o analista vê (a árvore de `test_relatorio_tese.py`, sobre
# `apoio.prosa_da_pagina`); classe e atributo só localizam.
# ==========================================================================

import shutil  # noqa: E402

import builder  # noqa: E402
import exhibits as exhibits_mod  # noqa: E402
import render  # noqa: E402
from test_relatorio_svg_js import _chamar_node, _textos  # noqa: E402
from test_relatorio_tese import (  # noqa: E402
    _aba, _elementos, _metricas, _secoes, _titulo, _todos, _um, _visivel)

DICIONARIO = placeholders.carregar_dicionario(IDIOMA)
VALUATION = DICIONARIO["interface"]["valuation"]
TESE = DICIONARIO["interface"]["tese"]
SEM_NODE = shutil.which("node") is None


def _pagina(entrega_dict: dict, com_laboratorio: bool = False) -> str:
    """O HTML pelo caminho que o builder percorre depois de uma primeira passada de QC sem HARD FAIL — com
    o laboratório quando pedido (os dois JS da integração, lidos de `builder.ASSETS_DA_INTEGRACAO`)."""
    achados = _achados(entrega_dict)
    assert not [a for a in achados if a.nivel == "HARD_FAIL"], achados
    _prosa, log = placeholders.resolver_prosa(entrega_dict, IDIOMA)
    resolvidos, log_exhibits = exhibits_mod.resolver(entrega_dict)
    js = ({nome: builder.ASSETS_DA_INTEGRACAO[nome].read_text(encoding="utf-8") for nome in ("espelho", "fachada")}
          if com_laboratorio else None)
    return render.compor(entrega_dict, CATALOGO, achados, log, IDIOMA, resolvidos, log_exhibits, js)


def _titulo_da(secao: dict) -> str | None:
    return next((_visivel(filho) for filho in secao["filhos"] if filho.get("tag") in ("h2", "h3", "h4")), None)


def _secao(aba: dict, titulo: str) -> dict:
    """A seção da aba cujo título é `titulo`. A aba Valuation abre com seções sem título (o cabeçalho), que o
    `_secao` da Tese não pula."""
    (secao,) = [secao for secao in _secoes(aba) if _titulo_da(secao) == titulo]
    return secao


def _moeda(entrega_dict: dict, valor: float) -> str:
    return placeholders.formatar(valor, "moeda", IDIOMA, entrega_dict["caso"]["moeda"])


def _na_unidade(valor, unidade: str, entrega_dict: dict) -> str:
    return placeholders.formatar(valor, CATALOGO["unidades"][unidade]["formato"], IDIOMA, entrega_dict["caso"]["moeda"])


def test_a_aba_valuation_segue_a_ordem_da_secao_9():
    """Cabeçalho (preço e upside, faixa piso–teto, múltiplos, rota) → como o valor é formado → cenários →
    laboratório → ponte → sensibilidades (a 1D e depois a 2D) → o que está no preço → cross-check
    (fatia 5G: a seção sai sempre, e sem os blocos das alternativas nenhuma outra aparece)."""
    entrega_dict = _entrega()
    aba = _aba(_pagina(entrega_dict, com_laboratorio=True), "valuation")
    secoes = _secoes(aba)
    titulos = [_titulo_da(secao) for secao in secoes]
    primeira_com_titulo = next(indice for indice, titulo in enumerate(titulos) if titulo is not None)

    assert [titulo for titulo in titulos if titulo is not None] == [
        VALUATION["formacao_titulo"], VALUATION["cenarios_titulo"], VALUATION["laboratorio_titulo"],
        VALUATION["ponte_titulo"],
        VALUATION["grade_1d_titulo"].format(cenario="base", premissa=_rotulo("firm", "wacc")),
        VALUATION["matriz_titulo"].format(cenario="base", y=_rotulo("firm", "g"), x=_rotulo("firm", "roic")),
        VALUATION["o_que_esta_no_preco_titulo"], VALUATION["cross_check_titulo"]]
    cabecalho = " ".join(_visivel(secao) for secao in secoes[:primeira_com_titulo])
    posicoes = [cabecalho.find(rotulo) for rotulo in (
        VALUATION["preco_justo_titulo"], TESE["papeis_da_faixa"]["piso"], VALUATION["multiplo_justo_titulo"],
        VALUATION["rota_titulo"])]
    assert -1 not in posicoes and posicoes == sorted(posicoes), (posicoes, cabecalho)


def test_o_que_esta_no_preco_mostra_cada_eixo_pela_unidade_da_leitura_com_a_identificacao_e_o_beta():
    entrega_dict = _entrega()
    eixos = entrega_dict["resultados"]["reversa"]["eixos"]
    secao = _secao(_aba(_pagina(entrega_dict), "valuation"), VALUATION["o_que_esta_no_preco_titulo"])
    artigos = _todos(secao, classe="reversa-eixo")
    assert [_titulo(artigo) for artigo in artigos] == [
        CATALOGO["eixos_de_reversa"][nome]["rotulo"][IDIOMA] for nome in eixos]

    for artigo, eixo in zip(artigos, eixos.values()):
        leitura = eixo["leitura"]
        assert _visivel(_um(artigo, classe="reversa-motivo")) == (
            CATALOGO["motivos_da_leitura"][leitura["motivo"]]["rotulo"][IDIOMA])
        raizes = leitura["raizes"]
        assert [_visivel(_um(item, classe="reversa-raiz-valor")) for item in _todos(artigo, classe="reversa-raiz")] == [
            VALUATION["reversa_raiz"].format(valor=_na_unidade(raiz["valor"], leitura["unidade"], entrega_dict),
                                             identificacao=CATALOGO["identificacoes"][raiz["identificacao"]]["rotulo"][IDIOMA])
            for raiz in raizes]
        assert [_visivel(el) for el in _todos(artigo, classe="reversa-intervalo")] == [
            VALUATION["reversa_intervalo"].format(de=_na_unidade(raiz["intervalo"][0], leitura["unidade"], entrega_dict),
                                                  ate=_na_unidade(raiz["intervalo"][1], leitura["unidade"], entrega_dict))
            for raiz in raizes]
        if leitura["cap_anos"] is not None:
            assert _visivel(_um(artigo, classe="reversa-cap")) == VALUATION["reversa_cap"].format(
                valor=_na_unidade(leitura["cap_anos"], leitura["unidade"], entrega_dict))
    assert all(eixo["leitura"]["raizes"] for nome, eixo in eixos.items() if nome != "cap"), "sem raiz, o teste não discrimina"

    beta = eixos["custo_capital"]["leitura"]["beta"]
    (artigo_do_custo,) = [artigo for artigo, nome in zip(artigos, eixos) if nome == "custo_capital"]
    assert [_visivel(_um(artigo_do_custo, classe=classe)) for classe in ("reversa-beta", "reversa-beta-posicao",
                                                                          "reversa-banda")] == [
        VALUATION["reversa_beta"].format(valor=_na_unidade(beta["valor"], beta["unidade"], entrega_dict)),
        CATALOGO["posicoes_na_banda"][beta["posicao"]]["rotulo"][IDIOMA],
        VALUATION["reversa_beta_banda"].format(minimo=_na_unidade(beta["banda"][0], beta["unidade"], entrega_dict),
                                               maximo=_na_unidade(beta["banda"][1], beta["unidade"], entrega_dict),
                                               distancia=_na_unidade(beta["distancia"], beta["unidade"], entrega_dict))]
    julgamento = entrega_dict["analise"]["o_que_esta_no_preco"]
    assert [_visivel(_um(secao, classe=classe)) for classe in ("reversa-julgamento-texto", "reversa-observavel")] == [
        julgamento["julgamento"], julgamento["observavel"]]


def test_sem_raiz_o_que_esta_no_preco_rotula_o_motivo_mostra_o_teto_e_a_limitacao_da_iso_sem_codigo_cru():
    sem_raiz = _entrega("reversa_sem_raiz")
    reversa = sem_raiz["resultados"]["reversa"]
    teto = reversa["teto_do_crescimento_gratuito"]
    secao = _secao(_aba(_pagina(sem_raiz), "valuation"), VALUATION["o_que_esta_no_preco_titulo"])
    rotulo_sem_raiz = CATALOGO["motivos_da_leitura"]["sem_raiz_na_faixa"]["rotulo"][IDIOMA]

    motivos = [_visivel(_um(artigo, classe="reversa-motivo")) for artigo in _todos(secao, classe="reversa-eixo")]
    assert motivos.count(rotulo_sem_raiz) == 3
    (bloco_do_teto,) = _todos(secao, classe="reversa-teto")
    assert [_titulo(bloco_do_teto), _visivel(_um(bloco_do_teto, classe="reversa-teto-multiplo")),
            _visivel(_um(bloco_do_teto, classe="reversa-teto-texto"))] == [
        CATALOGO["teto_do_crescimento_gratuito"]["rotulo"][IDIOMA],
        VALUATION["reversa_teto_multiplo"].format(valor=placeholders.formatar(teto["multiplo"], "x2", IDIOMA),
                                                  multiplo=CATALOGO["multiplos"][teto["chave"]]["rotulo"][IDIOMA]),
        CATALOGO["teto_do_crescimento_gratuito"]["texto"][IDIOMA]]
    assert CATALOGO["limitacoes"]["iso_nao_calculada"]["rotulo"][IDIOMA] in [
        _visivel(item) for item in _todos(_um(secao, classe="reversa-limitacoes"), tag="li")]

    texto = _visivel(_aba(_pagina(sem_raiz), "valuation"))
    crus = ["sem_raiz_na_faixa", "raiz_na_faixa", "custo_capital", "iso_nao_calculada", teto["leitura"]]
    crus += [reversa["eixos"][nome][campo] for nome in reversa["eixos"] for campo in ("sem_solucao", "sugestao")
             if isinstance(reversa["eixos"][nome].get(campo), str)]
    assert [cru for cru in crus if cru in texto] == []


def test_sem_reversa_o_que_esta_no_preco_diz_a_limitacao_que_a_suprime():
    rampa = _entrega(SEM_REVERSA)
    (limitacao,) = rampa["resultados"]["limitacoes"]
    secao = _secao(_aba(_pagina(rampa), "valuation"), VALUATION["o_que_esta_no_preco_titulo"])
    assert _todos(secao, classe="reversa-eixo") == []
    assert [_visivel(item) for item in _todos(_um(secao, classe="reversa-limitacoes"), tag="li")] == [
        CATALOGO["limitacoes"][limitacao]["rotulo"][IDIOMA]]


def test_o_par_forward_sai_no_cabecalho_e_na_conclusao_da_tese_com_o_periodo_e_a_fonte_da_metrica():
    forward = _entrega("forward_firm")
    resultados = forward["resultados"]
    justo, tela = resultados["manchete"]["multiplo_forward"], resultados["mercado_tela_forward"]
    esperados = [
        (VALUATION["multiplo_justo_forward_titulo"], placeholders.formatar(justo["valor"], "x2", IDIOMA),
         CATALOGO["multiplos"][justo["chave"]]["rotulo"][IDIOMA]),
        (VALUATION["multiplo_tela_forward_titulo"], placeholders.formatar(tela["valor"], "x2", IDIOMA),
         VALUATION["multiplo_tela_forward_nota"].format(multiplo=CATALOGO["multiplos"][tela["chave"]]["rotulo"][IDIOMA],
                                                        periodo=tela["metrica"]["periodo"],
                                                        fonte=tela["metrica"]["fonte"]))]
    pagina = _pagina(forward)
    assert _metricas(_um(_aba(pagina, "valuation"), classe="valuation-multiplos"))[2:] == esperados
    assert _metricas(_um(_aba(pagina, "tese"), classe="tese-multiplos"))[2:] == esperados


def test_a_escala_entra_no_valor_original_e_nos_montantes_da_rampa_e_nunca_no_preco_por_acao():
    escala = _entrega("escala")
    resultados = escala["resultados"]
    assert resultados["escala_monetaria"] == "milhoes"
    rotulo = CATALOGO["escalas_monetarias"]["milhoes"]["rotulo"][IDIOMA]
    premissas = escala["caso"]["cenarios"]["base"]["premissas"]
    aba = _aba(_pagina(escala, com_laboratorio=True), "valuation")

    def _original(chave: str) -> str:
        (campo,) = [el for el in _elementos(aba) if el["attrs"].get("data-laboratorio-premissa") == chave]
        return _visivel(_um(campo, classe="lab-original"))

    assert _original("receita0") == VALUATION["laboratorio_original"].format(
        valor=f"{_moeda(escala, premissas['receita0'])} {rotulo}")
    assert _original("wk") == VALUATION["laboratorio_original"].format(valor=_na_unidade(premissas["wk"], "pp", escala))

    formacao = _secao(aba, VALUATION["formacao_titulo"])
    montantes = [(_visivel(_um(metrica, classe="metrica-rotulo")), _visivel(_um(metrica, classe="metrica-valor")))
                 for metrica in _todos(_um(formacao, classe="formacao-montantes"), classe="metrica")]
    cenario = resultados["cenarios"]["base"]
    assert montantes == [
        (VALUATION["formacao_vp_fase1_titulo"], f"{_moeda(escala, cenario['vp_fase1'])} {rotulo}"),
        (VALUATION["formacao_valor_fase2_titulo"], f"{_moeda(escala, cenario['valor_fase2_no_ano_T'])} {rotulo}")]

    precos = [_um(aba, classe="valuation-cabecalho"), _secao(aba, VALUATION["cenarios_titulo"])]
    assert [rotulo in _visivel(bloco) for bloco in precos] == [False, False]
    assert _moeda(escala, resultados["manchete"]["preco_acao"]) in _visivel(precos[0])


@pytest.mark.skipif(SEM_NODE, reason="node ausente do PATH -- o harness do svg.js roda sempre no CI (setup-node)")
def test_o_waterfall_desenha_a_ponte_com_a_escala_e_sem_ela_quando_o_caso_nao_a_declara():
    rotulo = CATALOGO["escalas_monetarias"]["milhoes"]["rotulo"][IDIOMA]

    def _valores(fonte: str) -> list:
        entrega_dict = _entrega(fonte)
        payload = render._paineis_valuation_para_json(entrega_dict["caso"], entrega_dict["resultados"], CATALOGO,
                                                      IDIOMA, DICIONARIO)
        svg = _chamar_node("FleetSVG.waterfall(ponte.parcelas, {total: ponte.total, formato: ponte.formato})",
                           ponte=payload["ponte"])
        return _textos(svg, "fleet-svg-valor")

    com_escala, sem_escala = _valores("escala"), _valores(SEM_REVERSA)
    assert com_escala and [texto.endswith(f" {rotulo}") for texto in com_escala] == [True] * len(com_escala)
    assert [texto for texto in sem_escala if rotulo in texto] == []


@pytest.mark.parametrize("fonte", [GRADES, "caso_minimo_equity.json", SEM_REVERSA])
def test_a_formacao_do_valor_mostra_os_passos_que_o_cenario_declara_os_multiplos_e_a_sintese(fonte):
    entrega_dict = _entrega(fonte)
    resultados = entrega_dict["resultados"]
    rota = resultados["rota"]
    cenario = resultados["cenarios"][resultados["manchete"]["cenario"]]
    formacao = CATALOGO["formacao_do_valor"][rota]
    secao = _secao(_aba(_pagina(entrega_dict), "valuation"), VALUATION["formacao_titulo"])

    passos = [passo for passo in formacao["passos"] if passo["premissa"] in cenario["premissas"]]
    assert [tuple(_visivel(_um(item, classe=classe)) for classe in ("formacao-premissa", "formacao-valor", "formacao-funcao"))
            for item in _todos(secao, classe="formacao-passo")] == [
        (_rotulo(rota, passo["premissa"]),
         _na_unidade(cenario["premissas"][passo["premissa"]], CATALOGO["premissas"][rota][passo["premissa"]]["unidade"],
                     entrega_dict),
         passo["funcao"][IDIOMA])
        for passo in passos]
    assert [(_visivel(_um(item, classe="formacao-multiplo-rotulo")), _visivel(_um(item, classe="formacao-multiplo-valor")))
            for item in _todos(secao, classe="formacao-multiplo")] == [
        (CATALOGO["multiplos"][chave]["rotulo"][IDIOMA], placeholders.formatar(valor, "x2", IDIOMA))
        for chave, valor in cenario["multiplos"].items()]
    assert _visivel(_um(secao, classe="formacao-sintese")) == formacao["sintese"][IDIOMA]
    if rota == "rampa":
        assert "util" in cenario["premissas"] and "g1" not in cenario["premissas"]
        assert _todos(secao, classe="formacao-montantes")


@pytest.mark.parametrize("fonte,chave", [
    pytest.param(SOTP_SAFRA, "formacao_rotulo_consolidado", id="sotp"),
    pytest.param("caso_degrau.json", "formacao_rotulo_degrau", id="degrau"),
])
def test_a_formacao_do_valor_diz_de_que_cenario_e_no_sotp_e_no_degrau(fonte, chave):
    entrega_dict = _entrega(fonte)
    secao = _secao(_aba(_pagina(entrega_dict), "valuation"), VALUATION["formacao_titulo"])
    assert _visivel(_um(secao, classe="formacao-rotulo")) == VALUATION[chave].format(
        cenario=entrega_dict["resultados"]["manchete"]["cenario"])

    vizinha = _secao(_aba(_pagina(_entrega()), "valuation"), VALUATION["formacao_titulo"])
    assert _todos(vizinha, classe="formacao-rotulo") == []


def test_os_cenarios_mostram_a_ancora_como_dado_o_triangulo_rotulado_o_preco_e_o_upside():
    entrega_dict = _entrega()
    (nome, cenario), = entrega_dict["resultados"]["cenarios"].items()
    (artigo,) = _todos(_secao(_aba(_pagina(entrega_dict), "valuation"), VALUATION["cenarios_titulo"]),
                       classe="valuation-cenario")

    def _rotulo_do_triangulo(chave: str) -> str:
        info = CATALOGO["premissas"]["firm"].get(chave) or CATALOGO["variaveis_do_triangulo"][chave]
        return info["rotulo"][IDIOMA]

    triangulo = cenario["triangulo"]
    assert [_titulo(artigo), _visivel(_um(artigo, classe="cenario-ancora")),
            _visivel(_um(artigo, classe="cenario-triangulo"))] == [
        nome, cenario["ancora"],
        VALUATION["cenario_triangulo_valor"].format(entradas=", ".join(_rotulo_do_triangulo(c) for c in triangulo["inputs"]),
                                                    saida=_rotulo_do_triangulo(triangulo["output"]))]
    assert [(_visivel(_um(metrica, classe="metrica-rotulo")), _visivel(_um(metrica, classe="metrica-valor")))
            for metrica in _todos(artigo, classe="metrica")] == [
        (VALUATION["preco_justo_titulo"], _moeda(entrega_dict, cenario["valor"]["preco_acao"])),
        (VALUATION["upside_titulo"], placeholders.formatar(cenario["vs_preco"]["upside"], "pct1", IDIOMA))]

    rampa = _entrega(SEM_REVERSA)
    (artigo_da_rampa,) = _todos(_secao(_aba(_pagina(rampa), "valuation"), VALUATION["cenarios_titulo"]),
                                classe="valuation-cenario")
    assert _visivel(_um(artigo_da_rampa, classe="cenario-triangulo")) == VALUATION["cenario_triangulo_nao_se_aplica"]


def test_a_grade_1d_de_wacc_e_uma_tabela_com_o_ponto_do_cenario_marcado_por_igualdade_exata():
    entrega_dict = _entrega()
    caso = entrega_dict["caso"]
    grade = entrega_dict["resultados"]["sensibilidades"]["grades_1d"][0]
    premissa = caso["cenarios"][caso["sensibilidades"]["cenario"]]["premissas"][grade["premissa"]]
    titulo = VALUATION["grade_1d_titulo"].format(cenario=caso["sensibilidades"]["cenario"],
                                                 premissa=_rotulo("firm", grade["premissa"]))
    secao = _secao(_aba(_pagina(entrega_dict), "valuation"), titulo)

    assert [_visivel(celula) for celula in _todos(_um(secao, tag="thead"), tag="th")] == [
        _rotulo("firm", grade["premissa"]), VALUATION["grade_1d_coluna_preco"], VALUATION["grade_1d_coluna_multiplo"]]
    ponto = lambda x: _na_unidade(x, CATALOGO["premissas"]["firm"][grade["premissa"]]["unidade"], entrega_dict)
    assert [[_visivel(celula) for celula in _todos(linha, tag="td")] for linha in _todos(_um(secao, tag="tbody"), tag="tr")] == [
        [VALUATION["grade_1d_ponto_do_cenario"].format(valor=ponto(p["x"]), cenario=caso["sensibilidades"]["cenario"])
         if p["x"] == premissa else ponto(p["x"]),
         _moeda(entrega_dict, p["valor"]), placeholders.formatar(p["multiplo"], "x2", IDIOMA)]
        for p in grade["pontos"]]
    assert sum(1 for p in grade["pontos"] if p["x"] == premissa) == 1


def test_num_sotp_a_premissa_decisiva_de_parte_e_o_vinculo_multi_rota_saem_rotulados():
    sotp = _entrega(SOTP_SAFRA)
    indice, parte = _base_instalada(sotp)
    _com_premissa_de_parte(sotp, parte["nome"], "util")
    sotp["analise"]["perguntas"][1]["vinculo"] = ["util", "custo_capital"]
    aba = _aba(_pagina(sotp), "tese")

    (premissa,) = _todos(aba, classe="tese-premissa")
    assert [_visivel(_um(premissa, classe=classe)) for classe in ("metrica-rotulo", "metrica-valor", "tese-premissa-parte")] == [
        _rotulo("rampa", "util"), _na_unidade(parte["premissas"]["util"], "pp", sotp),
        TESE["premissa_da_parte"].format(numero=placeholders.formatar(indice + 1, "num0", IDIOMA), nome=parte["nome"])]
    pergunta = _todos(aba, classe="tese-pergunta")[1]
    assert [_visivel(chip) for chip in _todos(pergunta, classe="tese-rotulo")] == [
        _rotulo("rampa", "util"), CATALOGO["blocos"]["custo_capital"]["rotulo"][IDIOMA]]


# ==========================================================================
# Fatia 5G, Task 4: as seções novas da aba — o painel de escolhas entre a ponte e as
# sensibilidades (§8.2) e, depois do que está no preço, o retorno exigido, o valor ponderado,
# o cross-check e o re-teste da hipótese terminal (§9).
# ==========================================================================

_RETESTE_TERMINAL = {"resultado": "trocada",
                     "texto": "A convergência do retorno ao custo de capital resiste melhor à âncora do setor."}


def _rotulo_da_escolha_no_catalogo(chave: str) -> str:
    return CATALOGO["escolhas_metodologicas"][chave]["rotulo"][IDIOMA]


def _metricas_simples(no: dict) -> list:
    return [(_visivel(_um(metrica, classe="metrica-rotulo")), _visivel(_um(metrica, classe="metrica-valor")))
            for metrica in _todos(no, classe="metrica")]


def _com_as_alternativas() -> dict:
    """A entrega das duas variantes juntas, com o re-teste terminal declarado — as quatro
    seções novas de uma vez."""
    entrega_dict = _entrega(TODAS_AS_ALTERNATIVAS)
    entrega_dict["analise"]["reteste_terminal"] = copy.deepcopy(_RETESTE_TERMINAL)
    return entrega_dict


def test_a_aba_com_as_alternativas_poe_o_painel_entre_a_ponte_e_as_sensibilidades_e_as_leituras_no_fim():
    """A ordem da §9: … ponte → ESCOLHAS → sensibilidades → o que está no preço → retorno
    exigido → valor ponderado → cross-check → re-teste terminal. `caso_minimo_firm` não declara
    grade, então a 1D e a matriz não entram — o que esta ordem fixa é a vizinhança do painel."""
    aba = _aba(_pagina(_com_as_alternativas()), "valuation")
    titulos = [titulo for titulo in (_titulo_da(secao) for secao in _secoes(aba)) if titulo is not None]

    assert titulos == [
        VALUATION["formacao_titulo"], VALUATION["cenarios_titulo"], VALUATION["ponte_titulo"],
        VALUATION["escolhas_titulo"], VALUATION["o_que_esta_no_preco_titulo"],
        VALUATION["retorno_exigido_titulo"], VALUATION["valor_ponderado_titulo"],
        VALUATION["cross_check_titulo"], VALUATION["reteste_terminal_titulo"]]


def test_o_painel_separa_o_nivel_principal_do_avancado_pelo_gatilho_e_pela_materialidade():
    """A variante traz as combinações que importam: material sem gatilho (`rentabilidade`),
    não-material sem gatilho (`crescimento`, a única do avançado) e duas com gatilho declarado.
    Cada escolha sai com o rótulo e o gatilho do catálogo, a posição do caso-base, o preço do
    outro ramo, o impacto e a razão do analista."""
    entrega_dict = _entrega(ESCOLHAS)
    escolhas = entrega_dict["resultados"]["escolhas_metodologicas"]
    por_chave = {escolha["chave"]: escolha for escolha in escolhas}
    assert (por_chave["rentabilidade"]["material"], "gatilho_disparou" in por_chave["rentabilidade"]) == (True, True)
    assert por_chave["rentabilidade"]["gatilho_disparou"] is None
    assert (por_chave["crescimento"]["material"], por_chave["crescimento"]["gatilho_disparou"]) == (False, None)

    secao = _secao(_aba(_pagina(entrega_dict), "valuation"), VALUATION["escolhas_titulo"])
    avancadas = _todos(_um(secao, tag="details"), classe="valuation-escolha")
    principais = [artigo for artigo in _todos(secao, classe="valuation-escolha") if artigo not in avancadas]
    assert [_titulo(artigo) for artigo in avancadas] == [_rotulo_da_escolha_no_catalogo("crescimento")]
    assert [_titulo(artigo) for artigo in principais] == [
        _rotulo_da_escolha_no_catalogo(escolha["chave"]) for escolha in escolhas if escolha["chave"] != "crescimento"]

    escolha = por_chave["rentabilidade"]
    (artigo,) = [a for a in principais if _titulo(a) == _rotulo_da_escolha_no_catalogo("rentabilidade")]
    assert [_visivel(_um(artigo, classe=classe))
            for classe in ("escolha-gatilho", "escolha-posicao", "escolha-razao")] == [
        CATALOGO["escolhas_metodologicas"]["rentabilidade"]["gatilho"][IDIOMA],
        VALUATION["posicoes_da_escolha"][escolha["no_caso_base"]],
        entrega_dict["analise"]["escolhas"][0]["razao"]]
    assert _metricas_simples(artigo) == [
        (VALUATION["escolha_preco_titulo"], _moeda(entrega_dict, escolha["preco_alternativa"])),
        (VALUATION["escolha_impacto_titulo"], placeholders.formatar(escolha["impacto"], "pct1", IDIOMA))]

    com_gatilho = por_chave["ano_de_capex_no_par_d_rir"]
    (artigo_do_gatilho,) = [a for a in principais
                            if _titulo(a) == _rotulo_da_escolha_no_catalogo(com_gatilho["chave"])]
    assert _visivel(_um(artigo_do_gatilho, classe="escolha-observavel")) == (
        com_gatilho["gatilho_disparou"]["observavel"])


def test_o_alerta_de_empilhamento_sai_acima_do_painel_com_a_direcao_e_as_escolhas_rotuladas():
    entrega_dict = _entrega(ESCOLHAS)
    empilhamento = entrega_dict["resultados"]["empilhamento"]
    assert len(empilhamento["chaves"]) > 1
    secao = _secao(_aba(_pagina(entrega_dict), "valuation"), VALUATION["escolhas_titulo"])

    assert _visivel(_um(secao, classe="escolhas-empilhamento")) == VALUATION["escolhas_empilhamento"].format(
        direcao=VALUATION["direcoes_do_empilhamento"][empilhamento["direcao"]],
        escolhas=", ".join(_rotulo_da_escolha_no_catalogo(chave) for chave in empilhamento["chaves"]))
    assert empilhamento["direcao"] not in _visivel(secao), "a direção sai rotulada, nunca como código"

    sem_empilhamento = copy.deepcopy(entrega_dict)
    sem_empilhamento["resultados"]["empilhamento"] = None
    vizinha = _secao(_aba(_pagina(sem_empilhamento), "valuation"), VALUATION["escolhas_titulo"])
    assert _todos(vizinha, classe="escolhas-empilhamento") == []


def test_as_tres_leituras_saem_com_os_numeros_publicados_e_com_os_rotulos_que_as_qualificam():
    """O retorno exigido com a taxa pela unidade da premissa que ela substitui e o rótulo de que
    não é fair value; o valor ponderado com os pesos e o rótulo de que não substitui bear, base e
    bull; o cross-check com a rota oposta rotulada, o preço e a diferença; e o re-teste terminal
    com o resultado rotulado."""
    entrega_dict = _com_as_alternativas()
    resultados = entrega_dict["resultados"]
    retorno, ponderado, cross = (resultados["retorno_exigido"], resultados["valor_ponderado"],
                                 resultados["cross_check"])
    aba = _aba(_pagina(entrega_dict), "valuation")

    secao = _secao(aba, VALUATION["retorno_exigido_titulo"])
    assert [_visivel(_um(secao, classe=classe)) for classe in
            ("retorno-exigido-taxa", "retorno-exigido-premissa", "retorno-exigido-nota")] == [
        _na_unidade(retorno["taxa"], CATALOGO["premissas"]["firm"][retorno["premissa_substituida"]]["unidade"],
                    entrega_dict),
        _rotulo("firm", retorno["premissa_substituida"]), VALUATION["retorno_exigido_nota"]]
    assert _metricas_simples(secao) == [
        (VALUATION["retorno_exigido_preco_titulo"], _moeda(entrega_dict, retorno["preco_acao"]))]

    secao = _secao(aba, VALUATION["valor_ponderado_titulo"])
    assert _metricas_simples(secao) == [
        (VALUATION["valor_ponderado_valor_titulo"], _moeda(entrega_dict, ponderado["valor"]))]
    assert [_visivel(item) for item in _todos(secao, classe="valor-ponderado-peso")] == [
        VALUATION["valor_ponderado_peso"].format(cenario=nome, peso=placeholders.formatar(peso, "pp0", IDIOMA))
        for nome, peso in ponderado["pesos"].items()]
    assert _visivel(_um(secao, classe="valor-ponderado-nota")) == VALUATION["valor_ponderado_nota"]

    secao = _secao(aba, VALUATION["cross_check_titulo"])
    assert _visivel(_um(secao, classe="cross-check-rota")) == CATALOGO["rotas"][cross["rota"]]["rotulo"][IDIOMA]
    assert _metricas_simples(secao) == [
        (VALUATION["cross_check_preco_titulo"], _moeda(entrega_dict, cross["preco_acao"])),
        (VALUATION["cross_check_diferenca_titulo"],
         placeholders.formatar(cross["diferenca_vs_manchete"], "pct1", IDIOMA))]

    secao = _secao(aba, VALUATION["reteste_terminal_titulo"])
    assert [_visivel(_um(secao, classe=classe))
            for classe in ("reteste-terminal-resultado", "reteste-terminal-texto")] == [
        VALUATION["resultados_do_reteste_terminal"][_RETESTE_TERMINAL["resultado"]], _RETESTE_TERMINAL["texto"]]


def test_sem_os_blocos_nenhuma_secao_nova_aparece_e_o_cross_check_diz_o_que_a_analise_declarou():
    """Duas leituras do cross-check sem ele publicado: declarado ausente (a razão do analista,
    prosa auditada) e não declarado (a frase do dicionário). E, sem os blocos, nem painel de
    escolhas, nem retorno exigido, nem valor ponderado, nem re-teste terminal."""
    entrega_dict = _entrega()
    aba = _aba(_pagina(entrega_dict), "valuation")
    titulos = [_titulo_da(secao) for secao in _secoes(aba)]
    for chave in ("escolhas_titulo", "retorno_exigido_titulo", "valor_ponderado_titulo", "reteste_terminal_titulo"):
        assert VALUATION[chave] not in titulos, chave
    assert _visivel(_um(_secao(aba, VALUATION["cross_check_titulo"]), classe="cross-check-nao-declarado")) == (
        VALUATION["cross_check_nao_declarado"])

    razao = "A rota oposta não tem vetor coerente nas âncoras observáveis desta companhia."
    com_ausencia = _entrega()
    com_ausencia["analise"]["cross_check"] = {"ausente": {"razao": razao}}
    secao = _secao(_aba(_pagina(com_ausencia), "valuation"), VALUATION["cross_check_titulo"])
    assert _visivel(_um(secao, classe="cross-check-ausente")) == razao
    assert _todos(secao, classe="cross-check-nao-declarado") == []


@pytest.mark.parametrize("grupo,vocabulario", [
    pytest.param("posicoes_da_escolha", lambda: set(caso_da_integracao.POSICOES_DA_ESCOLHA),
                 id="posicoes-da-escolha"),
    pytest.param("direcoes_do_empilhamento", lambda: set(avaliar_da_integracao.DIRECOES_DO_EMPILHAMENTO),
                 id="direcoes-do-empilhamento"),
    pytest.param("resultados_do_reteste_terminal", lambda: set(entrega.RESULTADOS_DO_RETESTE_TERMINAL),
                 id="resultados-do-reteste-terminal"),
])
def test_o_dicionario_rotula_todo_codigo_dos_vocabularios_novos(grupo, vocabulario):
    """O que a integração pode publicar (a posição do caso-base de uma escolha e a direção do
    empilhamento) e o que o contrato aceita (o resultado do re-teste) têm rótulo no dicionário —
    nenhum código cru chega à tela por um vocabulário que cresceu do outro lado."""
    assert set(VALUATION[grupo]) == vocabulario()


# ==========================================================================
# Fatia 5H, Task 2 (D2/D4): o produto da execução — a reversa que a Leitura de preço exige,
# e o nível implícito na seção "o que está no preço".
# ==========================================================================

# A fixture sem reversa publica a limitação que, na Análise, a dispensa.
CONSENSO = "consenso"


def _com_produto(fonte: str, produto: str, com_faixa: bool = False) -> dict:
    """A entrega de `fonte` declarada sob `produto`. Sob `leitura_de_preco` a faixa sai junto
    (`com_faixa=False`): ela não é exigida ali e, declarada, é o HARD FAIL
    `produto_com_preco_alvo` — `com_faixa=True` é justamente para exercer essa recusa."""
    entrega_dict = _entrega(fonte)
    entrega_dict["execucao"]["produto"] = produto
    if produto == entrega.PRODUTO_DA_LEITURA_DE_PRECO and not com_faixa:
        entrega_dict["analise"].pop("faixa", None)
    return entrega_dict


def test_a_leitura_de_preco_exige_a_reversa_mesmo_com_a_limitacao_publicada_e_nomeia_o_produto():
    """D4: na Análise, uma limitação declarada pelo catálogo como supressora da reversa
    dispensa a reversa; sob `leitura_de_preco`, nenhuma dispensa — a entrega inteira É a
    leitura do que o preço embute. Mesmo código, com o produto nos parâmetros."""
    sem_reversa = _entrega(SEM_REVERSA)
    assert sem_reversa["resultados"]["limitacoes"], "a fixture tem de publicar a limitação"
    assert sem_reversa["resultados"].get("reversa") is None
    assert _do_codigo(_achados(sem_reversa), "analise_sem_reversa") == []

    como_leitura = _com_produto(SEM_REVERSA, entrega.PRODUTO_DA_LEITURA_DE_PRECO)
    (achado,) = _do_codigo(_achados(como_leitura), "analise_sem_reversa")
    assert achado.nivel == "HARD_FAIL"
    assert achado.params["produto"] == entrega.PRODUTO_DA_LEITURA_DE_PRECO
    assert achado.params["limitacoes"] == ", ".join(sem_reversa["resultados"]["limitacoes"])

    com_reversa = _com_produto(GRADES, entrega.PRODUTO_DA_LEITURA_DE_PRECO)
    assert _do_codigo(_achados(com_reversa), "analise_sem_reversa") == []


def test_a_mensagem_da_regra_nomeia_o_produto_e_a_linha_da_11_continua_uma_so():
    """A §11 não ganhou linha: é o mesmo código nos dois produtos, e o dicionário resolve o
    `{produto}` que o QC passa."""
    como_leitura = _com_produto(SEM_REVERSA, entrega.PRODUTO_DA_LEITURA_DE_PRECO)
    (achado,) = _do_codigo(_achados(como_leitura), "analise_sem_reversa")
    mensagem = DICIONARIO["qc"][achado.codigo].format(onde=achado.onde, **achado.params)
    assert entrega.PRODUTO_DA_LEITURA_DE_PRECO in mensagem
    assert "{" not in mensagem


def test_o_nivel_implicito_entra_no_que_esta_no_preco_com_o_rotulo_do_catalogo():
    """D2: a métrica implícita como montante, o degrau em pontos percentuais, uma razão por
    ponto de consenso declarado e a leitura pelo RÓTULO do catálogo — nunca a chave, nunca a
    prosa do motor, que continua publicada em `resultados` e não chega à tela."""
    entrega_dict = _entrega(CONSENSO)
    nivel = entrega_dict["resultados"]["reversa"]["nivel_implicito"]
    secao = _secao(_aba(_pagina(entrega_dict), "valuation"), VALUATION["o_que_esta_no_preco_titulo"])
    bloco = _um(secao, classe="reversa-nivel-implicito")

    assert _titulo_da(bloco) == VALUATION["nivel_implicito_titulo"]
    assert list(zip([_visivel(el) for el in _todos(bloco, classe="metrica-rotulo")],
                    [_visivel(el) for el in _todos(bloco, classe="metrica-valor")])) == [
        (VALUATION["nivel_implicito_metrica_titulo"], _moeda(entrega_dict, nivel["metrica_base_implicita"])),
        (VALUATION["nivel_implicito_degrau_titulo"],
         placeholders.formatar(nivel["degrau_implicito_%"], render.FORMATO_DO_DEGRAU_IMPLICITO, IDIOMA)),
        (VALUATION["nivel_implicito_razao_t1_titulo"],
         placeholders.formatar(nivel["razao_vs_consenso_t1"], render.FORMATO_DA_RAZAO_CONTRA_O_CONSENSO, IDIOMA)),
        (VALUATION["nivel_implicito_razao_t2_titulo"],
         placeholders.formatar(nivel["razao_vs_consenso_t2"], render.FORMATO_DA_RAZAO_CONTRA_O_CONSENSO, IDIOMA)),
    ]

    chave = nivel["leitura_chave"]
    assert chave == "antecipacao_temporal", "a variante tem de exercer uma leitura de verdade"
    assert _visivel(_um(bloco, classe="nivel-implicito-leitura")) == (
        CATALOGO["leituras_do_nivel"][chave]["rotulo"][IDIOMA])
    texto_da_aba = _visivel(_aba(_pagina(entrega_dict), "valuation"))
    assert chave not in texto_da_aba
    assert nivel["leitura"][:40] not in texto_da_aba


def test_sem_consenso_o_nivel_sai_so_com_o_degrau_e_sem_leitura():
    """A fixture sem `reversa.consenso`: nenhuma razão, nenhuma leitura — e o bloco continua,
    porque o degrau que o preço embute não depende de haver consenso."""
    entrega_dict = _entrega()
    assert entrega_dict["resultados"]["reversa"]["nivel_implicito"]["leitura_chave"] is None
    bloco = _um(_secao(_aba(_pagina(entrega_dict), "valuation"), VALUATION["o_que_esta_no_preco_titulo"]),
                classe="reversa-nivel-implicito")
    assert [_visivel(el) for el in _todos(bloco, classe="metrica-rotulo")] == [
        VALUATION["nivel_implicito_metrica_titulo"], VALUATION["nivel_implicito_degrau_titulo"]]
    assert _todos(bloco, classe="nivel-implicito-leitura") == []


def test_toda_aba_declarada_por_produto_tem_rotulo_e_todo_produto_tem_abas():
    """Um produto novo no contrato sem abas declaradas no render — ou uma aba sem rótulo no
    dicionário — reprova aqui, e não com uma página sem navegação."""
    assert set(render.ABAS_DO_PRODUTO) == entrega.PRODUTOS
    for abas in render.ABAS_DO_PRODUTO.values():
        for nome in abas:
            assert DICIONARIO["interface"]["abas"][nome].strip(), nome


# --------------------------------------------------------------------------
# Fatia 5H, Task 2b: a faixa piso–teto sob `leitura_de_preco` — não exigida na forma, e
# recusada como preço-alvo quando declarada, pela mesma regra da fronteira de escopo.
# --------------------------------------------------------------------------

def test_sob_leitura_de_preco_a_faixa_nao_e_exigida_e_a_entrega_passa(tmp_path):
    """Lado de cá: sem faixa, a entrega passa na forma e emite sem HARD FAIL — enquanto a
    MESMA entrega sob `analise` é recusada na forma por faltar a faixa."""
    sem_faixa = _com_produto(GRADES, entrega.PRODUTO_DA_LEITURA_DE_PRECO)
    assert "faixa" not in sem_faixa["analise"]
    _carregar(sem_faixa, tmp_path / "leitura")
    assert [a.codigo for a in _achados(sem_faixa) if a.nivel == "HARD_FAIL"] == []

    como_analise = copy.deepcopy(sem_faixa)
    como_analise["execucao"]["produto"] = entrega.PRODUTO_PADRAO
    with pytest.raises(entrega.EntregaInvalida) as erro:
        _carregar(como_analise, tmp_path / "analise")
    assert "campo obrigatório ausente em 'analise': 'faixa'" in str(erro.value)


def test_a_faixa_declarada_sob_leitura_de_preco_passa_na_forma_e_e_hard_fail_nomeando_o_produto():
    """Lado de lá: a forma continua validando a faixa (o QC é quem nomeia o problema), e a
    recusa nomeia o produto, o caminho dos preços que a faixa aponta e a unidade da família —
    reconhecida pelo MAPA da integração, nunca pelo nome do campo. Sob `analise` a mesma
    entrega não dispara nada."""
    com_faixa = _com_produto(GRADES, entrega.PRODUTO_DA_LEITURA_DE_PRECO, com_faixa=True)
    faixa = com_faixa["analise"]["faixa"]
    assert isinstance(faixa, dict)

    (achado,) = _do_codigo(_achados(com_faixa), "produto_com_preco_alvo")
    assert (achado.nivel, achado.onde) == ("HARD_FAIL", "analise.faixa")
    assert achado.params["produto"] == entrega.PRODUTO_DA_LEITURA_DE_PRECO
    assert achado.params["caminho"] == f"cenarios.{faixa['piso']}.valor.preco_acao"
    assert achado.params["unidade"] == "preço por ação"
    # O `{` que sobra na mensagem é o do `trecho` (a faixa serializada), não um marcador.
    mensagem = DICIONARIO["qc"][achado.codigo].format(onde=achado.onde, **achado.params)
    assert entrega.PRODUTO_DA_LEITURA_DE_PRECO in mensagem and achado.params["caminho"] in mensagem

    como_analise = copy.deepcopy(com_faixa)
    como_analise["execucao"]["produto"] = entrega.PRODUTO_PADRAO
    assert _do_codigo(_achados(como_analise), "produto_com_preco_alvo") == []
    assert [a.codigo for a in _achados(como_analise) if a.nivel == "HARD_FAIL"] == []


def test_a_faixa_e_preco_alvo_pelo_mapa_da_integracao_e_nunca_pelo_nome_do_campo():
    """E3, a lição de F2 da 5D aplicada aos dois gatilhos: tirando do mapa o padrão dos preços
    por cenário, a faixa deixa de ser preço-alvo — nos dois regimes. Um QC que decidisse pelo
    nome do campo ficaria igual nos dois catálogos."""
    com_faixa = _com_produto(GRADES, entrega.PRODUTO_DA_LEITURA_DE_PRECO, com_faixa=True)
    sem_o_padrao = copy.deepcopy(CATALOGO)
    sem_o_padrao["conclusoes_de_valor"]["preço por ação"].remove("cenarios.*.valor.preco_acao")

    assert _do_codigo(_achados(com_faixa), "produto_com_preco_alvo") != []
    assert _do_codigo(_achados(com_faixa, sem_o_padrao), "produto_com_preco_alvo") == []


# ==========================================================================
# Item 6, Task 2 (D1 do plano docs/superpowers/plans/2026-09-16-v4-item6-fixture-sintetica.md): a seção
# dos drivers exógenos, depois das sensibilidades, rotulada como congelada. A tabela lê as marcas que a
# integração publica, e nunca o limiar nem a prosa do motor.
# ==========================================================================

def _com_drivers_nas_grades() -> dict:
    """`caso_reversa_firm` — a fixture com as duas grades — com os drivers da variante `drivers` do apoio:
    a única entrega em que a posição da seção depois das sensibilidades é observável."""
    drivers = apoio.VARIANTES_DO_CASO["drivers"][1](apoio.carregar_fixture_ou_variante(GRADES))["drivers"]
    return apoio.montar_entrega(GRADES, mutar_caso=lambda caso: caso.update(drivers=drivers))


def test_a_secao_dos_drivers_sai_depois_das_sensibilidades_rotulada_como_congelada_com_as_marcas():
    entrega_dict = _com_drivers_nas_grades()
    registro = entrega_dict["resultados"]["drivers"]
    aba = _aba(_pagina(entrega_dict), "valuation")
    titulos = [titulo for titulo in (_titulo_da(secao) for secao in _secoes(aba)) if titulo is not None]
    assert titulos[titulos.index(VALUATION["drivers_titulo"]) - 1:titulos.index(VALUATION["drivers_titulo"]) + 2] == [
        VALUATION["matriz_titulo"].format(cenario="base", y=_rotulo("firm", "g"), x=_rotulo("firm", "roic")),
        VALUATION["drivers_titulo"], VALUATION["o_que_esta_no_preco_titulo"]]

    secao = _secao(aba, VALUATION["drivers_titulo"])
    assert _visivel(_um(secao, classe="drivers-congelado-nota")) == VALUATION["drivers_congelado"]
    linhas = [[_visivel(celula) for celula in _todos(linha, tag="td")]
              for linha in _todos(_um(secao, tag="tbody"), tag="tr")]
    pp = lambda valor: placeholders.formatar(valor, "pp1", IDIOMA)  # noqa: E731
    num = lambda valor: placeholders.formatar(valor, "num2", IDIOMA)  # noqa: E731
    assert linhas == [
        [driver["nome"], num(driver["base"]), num(driver["spot"]), pp(driver["gap_%"]), num(driver["elast"]),
         pp(driver["impacto_%"]),
         VALUATION["drivers_acima_do_limiar" if driver["acima_do_limiar"] else "drivers_abaixo_do_limiar"],
         VALUATION["drivers_vira_cenario" if driver["vira_cenario"] else "drivers_linha_de_sensibilidade"]]
        for driver in registro["drivers"]]
    # A variante traz os dois lados do limiar, e a tela os distingue pelas marcas.
    assert [linha[6:] for linha in linhas] == [
        [VALUATION["drivers_acima_do_limiar"], VALUATION["drivers_vira_cenario"]],
        [VALUATION["drivers_abaixo_do_limiar"], VALUATION["drivers_linha_de_sensibilidade"]]]
    assert _visivel(_um(secao, classe="drivers-liquido")) == VALUATION["drivers_liquido"].format(
        liquido=pp(registro["compensacao"]["efeito_liquido_total_%"]),
        brutos=pp(registro["compensacao"]["soma_dos_brutos_%"]))
    # A prosa do motor não chega à tela: nem a fonte da elasticidade, nem a nota do gate.
    for driver in registro["drivers"]:
        assert driver["elast_fonte"] not in _visivel(secao)
    assert registro["nota"] not in _visivel(secao)


def test_sem_o_registro_de_drivers_a_secao_some():
    entrega_dict = _entrega()
    assert entrega_dict["resultados"]["drivers"] is None
    aba = _aba(_pagina(entrega_dict), "valuation")
    assert VALUATION["drivers_titulo"] not in [_titulo_da(secao) for secao in _secoes(aba)]
    assert _todos(aba, classe="drivers-congelado-nota") == []
