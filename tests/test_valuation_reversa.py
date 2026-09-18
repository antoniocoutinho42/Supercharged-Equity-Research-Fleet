import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures"
sys.path.insert(0, str(RAIZ / "skills" / "er-valuation" / "scripts"))
from caso import carregar  # noqa: E402
import diagnosticos  # noqa: E402
from reversa import alvo_de_mercado, reverter  # noqa: E402


def _caso() -> dict:
    return carregar(FIXTURES / "caso_reversa_firm.json")


def test_alvo_e_o_multiplo_de_mercado_com_algebra_declarada():
    # preco 55 x 100 acoes = 5500 de market cap; + nd 500 = EV 6000; / EBITDA 1000 = 6,0x
    alvo = alvo_de_mercado(_caso(), "base", 500.0)
    assert alvo["valor"] == pytest.approx(6.0)
    assert "6000" in alvo["algebra"] or "6.000" in alvo["algebra"]
    assert alvo["base"] == "ebitda"


def test_custo_de_capital_implicito_tem_raiz_e_identificacao():
    r = reverter(_caso(), "base", 500.0)
    eixo = r["eixos"]["custo_capital"]
    raizes = eixo["raizes_wacc_%"]
    assert raizes and all(isinstance(x, float) for x in raizes)
    assert eixo["identificacao_por_raiz"]


def test_beta_implicito_sai_do_capm_com_algebra():
    r = reverter(_caso(), "base", 500.0)
    b = r["eixos"]["custo_capital"]["beta_implicito"]
    wacc = r["eixos"]["custo_capital"]["raizes_wacc_%"][0]
    assert b["valor"] == pytest.approx((wacc - 12.0) / 5.5, abs=1e-6)
    assert "12" in b["algebra"] and "5,5" in b["algebra"].replace(".", ",")


def test_beta_implicito_diz_a_posicao_contra_a_banda():
    """FIX 8 (revisão final): a versão anterior só checava que a posição era
    UM dos três valores possíveis e que a chave 'distancia' existia --
    passava verde mesmo se a posição ou a distância certas trocassem de
    lugar. Valores reais pinados contra a fixture: beta -0.2315 contra a
    banda [0.85, 1.35] dá posição 'abaixo' e distância 1.0815."""
    r = reverter(_caso(), "base", 500.0)
    b = r["eixos"]["custo_capital"]["beta_implicito"]
    assert b["valor"] == pytest.approx(-0.2315, abs=1e-3)
    assert b["posicao_na_banda"] == "abaixo"
    assert b["distancia"] == pytest.approx(1.0815, abs=1e-3)


def test_beta_implicito_so_existe_no_eixo_de_custo_de_capital():
    r = reverter(_caso(), "base", 500.0)
    for nome, eixo in r["eixos"].items():
        if nome != "custo_capital":
            assert "beta_implicito" not in eixo


def test_diagnosticos_do_motor_chegam_integros():
    r = reverter(_caso(), "base", 500.0)
    eixo = r["eixos"]["custo_capital"]
    assert eixo["premissas_fixadas"]["nota"]
    assert isinstance(eixo["guardas_v9_4"], list)
    assert eixo["faixa_de_busca"]["variavel"] == "wacc"


def test_alvo_base_corrente_e_declarado_explicitamente():
    """Tela NTM contra base corrente injeta erro de (1+g); a base vai declarada."""
    r = reverter(_caso(), "base", 500.0)
    assert "corrente" in r["eixos"]["custo_capital"]["base_do_alvo"]


def test_eixo_sem_raiz_preserva_sem_solucao_e_sugestao():
    c = _caso()
    c["preco"]["valor"] = 900.0  # alvo absurdo: nenhum eixo primario fecha
    r = reverter(c, "base", 500.0)
    rent = r["eixos"]["rentabilidade"]
    assert rent["raizes_roic_%"] == []
    assert "sem_solucao" in rent and "máximo atingível" in rent["sem_solucao"]
    assert "sugestao" in rent and "TETO DO CRESCIMENTO GRATUITO" in rent["sugestao"]


def test_todos_os_eixos_declarados_sao_rodados():
    r = reverter(_caso(), "base", 500.0)
    assert set(r["eixos"]) == {"custo_capital", "crescimento", "rentabilidade", "cap"}


def test_eixo_cap_passa_com_shape_proprio():
    """O motor devolve CAP_implicito_anos, nao raizes_* — repassar, nao uniformizar."""
    cap = reverter(_caso(), "base", 500.0)["eixos"]["cap"]
    assert "CAP_implicito_anos" in cap
    assert not any(k.startswith("raizes") for k in cap)
    assert cap["faixa_de_busca"]["variavel"] == "cap(n)"


def test_cap_inalcancavel_chega_como_string_sem_quebrar():
    """CAP_implicito_anos vira STRING quando o alvo esta fora de 1-60 anos.

    FIX 8 (revisão final): a versão anterior aceitava (float, int, str) --
    tautológico, já que o motor só devolve um desses três tipos para este
    campo, e o nome do teste promete string especificamente. Verificado
    contra o vendor: preco=70.0 produz a string
    '>60 — alvo incompatível com estas premissas sob esta convenção
    (máx em n=60: 12.14)'.
    """
    c = _caso()
    c["preco"]["valor"] = 70.0
    cap = reverter(c, "base", 500.0)["eixos"]["cap"]
    assert isinstance(cap["CAP_implicito_anos"], str)


def test_teto_roda_quando_eixo_primario_nao_fecha():
    c = _caso()
    c["preco"]["valor"] = 900.0
    r = reverter(c, "base", 500.0)
    teto = r["teto_do_crescimento_gratuito"]
    assert teto["multiplo"] > 0
    assert "RiR" in teto["leitura"] or "reinvestimento" in teto["leitura"]


def test_teto_nao_roda_quando_todos_os_eixos_fecham():
    r = reverter(_caso(), "base", 500.0)
    assert "teto_do_crescimento_gratuito" not in r


def test_teto_do_crescimento_gratuito_nao_perde_rf():
    """Correção do item 3: `teto_do_crescimento_gratuito` roda o motor por
    conta própria (subcomando de avaliação direta, não 'rev') — um segundo
    call site de `rodar()` dentro de reversa.py, distinto do de
    `reverter()`, e sob 'tv=gordon' forçado (a única convenção terminal do
    teto) com 'gp' igualado ao 'g' do cenário (3.0 > 0 na fixture). Sem
    'rf' repassado aqui também, o teto sairia "PREMISSA NÃO ANCORADA"
    mesmo quando `reverter()` já corrigiu os quatro eixos."""
    c = _caso()
    c["preco"]["valor"] = 900.0  # alvo absurdo: nenhum eixo primario fecha
    teto = reverter(c, "base", 500.0)["teto_do_crescimento_gratuito"]
    assert not any("PREMISSA NÃO ANCORADA" in d for d in teto["diagnosticos"])
    assert any("ÂNCORA MACRO OK" in d for d in teto["diagnosticos"])


def test_teto_do_crescimento_gratuito_tem_diagnosticos_chaves_paralelas():
    """A3 (onda de correção da revisão final, achado S1 generalizado): esta
    é a segunda lista 'diagnosticos' de resultados.json fora de
    `cenarios`/`sotp.partes` (achada ao mapear todo `diagnosticos` do
    contrato, não só o que a revisão já tinha verificado em SOTP) — mesma
    disciplina de paralelo, mesmo comprimento, mesma ordem, mesmo
    classificador por prefixo."""
    c = _caso()
    c["preco"]["valor"] = 900.0  # alvo absurdo: nenhum eixo primario fecha
    teto = reverter(c, "base", 500.0)["teto_do_crescimento_gratuito"]
    assert teto["diagnosticos"], "fixture não produziu diagnosticos — teste vacuamente verde?"
    assert len(teto["diagnosticos_chaves"]) == len(teto["diagnosticos"])
    assert teto["diagnosticos_chaves"] == [diagnosticos.classificar(m) for m in teto["diagnosticos"]]


def test_teto_e_insensivel_a_escolha_do_infinito():
    """A constante e uma aproximacao numerica; se o resultado depender dela, e invencao."""
    import reversa as mod
    c = _caso()
    c["preco"]["valor"] = 900.0
    valores = []
    original = mod.RENTABILIDADE_TERMINAL_INFINITA
    try:
        for grande in (1e5, 1e6, 1e7):
            mod.RENTABILIDADE_TERMINAL_INFINITA = grande
            valores.append(mod.teto_do_crescimento_gratuito(c, "base", 500.0)["multiplo"])
    finally:
        mod.RENTABILIDADE_TERMINAL_INFINITA = original
    # medido contra o vendor: 1e5 -> 10.6467, 1e6 -> 10.647, 1e7 -> 10.647
    assert max(valores) - min(valores) < 0.01, valores


def test_teto_declara_as_premissas_que_alterou():
    c = _caso()
    c["preco"]["valor"] = 900.0
    teto = reverter(c, "base", 500.0)["teto_do_crescimento_gratuito"]
    assert teto["premissas_alteradas"]["tv"] == "gordon"
    assert teto["premissas_alteradas"]["gp"] == c["cenarios"]["base"]["premissas"]["g"]


def test_teto_e_maior_que_o_multiplo_do_caso_base():
    """Nenhuma historia de crescimento PAGO chega ao teto do crescimento gratuito."""
    c = _caso()
    c["preco"]["valor"] = 900.0
    r = reverter(c, "base", 500.0)
    from motor import rodar
    base = rodar("firm", c["cenarios"]["base"]["premissas"], None)
    assert r["teto_do_crescimento_gratuito"]["multiplo"] > base["EV/EBITDA_curr"]


# --------------------------------------------------------------------------
# Revisão final, FIX 1 (Crítico): o teto força tv="gordon" com gp=g -- um
# cenário com g == wacc zera o denominador de Gordon, o motor serializa o
# múltiplo resultante como `null` e ainda sai com código 0. A leitura de
# `teto_do_crescimento_gratuito` lia esse campo raw (`saida[campo_multiplo]`),
# sem passar pela mesma recusa (`_exigir_valor`) que toda outra leitura do
# motor neste módulo já usa -- o `null` chegava intacto até
# `resultados.json`. Reproduzido de ponta a ponta pelo controlador com
# preco=400, g=10.0 (wacc da fixture também é 10.0).
# --------------------------------------------------------------------------

def test_teto_recusa_null_quando_g_igual_wacc_zera_gordon():
    from motor import MotorFalhou
    c = _caso()
    c["preco"]["valor"] = 400.0
    c["cenarios"]["base"]["premissas"]["g"] = 10.0  # wacc da fixture também é 10.0
    with pytest.raises(MotorFalhou, match="EV/EBITDA_curr"):
        reverter(c, "base", 500.0)


# --------------------------------------------------------------------------
# Endurecimento (task 3B), RISCO 1+3: marcador uniforme "resolucao", ao
# lado do payload do motor — nunca no lugar dele. Os quatro shapes que o
# motor legitimamente devolve para um eixo de reversa (docstring do
# módulo, tabela do brief): (1) eixo '%' com raiz — raizes_<var>_% não
# vazia + identificacao_por_raiz; (2) eixo '%' sem raiz — raizes_<var>_%
# vazia + sem_solucao, com 'sugestao' só nos eixos PRIMÁRIOS; (3) 'cap'
# com CAP_implicito_anos — float quando alcançável, string quando fora da
# faixa 1-60; (4) 'cap' com spread <= 0 — nem CAP_implicito_anos nem
# raizes_*, só {"erro", "alvo_normalizado"}. Gatilhos verificados contra o
# vendor (probe manual antes do TDD, mesmos números do brief): preco=5.0
# zera raizes_wacc_% (alvo 1,0x < mínimo atingível 1,76); roic=8/wacc=12/
# tv=book zera o spread do eixo cap (-4.0 p.p.).
# --------------------------------------------------------------------------

def test_resolucao_eixo_percentual_com_raiz_resolve():
    r = reverter(_caso(), "base", 500.0)
    for nome_eixo in ("custo_capital", "crescimento", "rentabilidade"):
        resolucao = r["eixos"][nome_eixo]["resolucao"]
        assert resolucao["resolveu"] is True
        assert isinstance(resolucao["motivo"], str) and resolucao["motivo"]


def test_resolucao_raiz_em_zero_ainda_conta_como_resolvida():
    """raizes_g_% == [0.0] na fixture-base: uma raiz EM ZERO é lista
    NÃO-VAZIA — 'resolveu' tem de olhar vazio/não-vazio, nunca o valor da
    raiz (0.0 é falsy; '[0.0]' não é)."""
    r = reverter(_caso(), "base", 500.0)
    crescimento = r["eixos"]["crescimento"]
    assert crescimento["raizes_g_%"] == [0.0]
    assert crescimento["resolucao"]["resolveu"] is True


def test_resolucao_eixo_percentual_sem_raiz_nao_resolve():
    """Gatilho verificado: preco=5.0 -> alvo 1,0x fica abaixo do mínimo
    atingível (1,76) — raizes_wacc_% vazia, sem_solucao presente,
    sugestao AUSENTE (custo_capital não é eixo primário)."""
    c = _caso()
    c["preco"]["valor"] = 5.0
    r = reverter(c, "base", 500.0)
    eixo = r["eixos"]["custo_capital"]
    assert eixo["raizes_wacc_%"] == []
    assert "sugestao" not in eixo
    resolucao = eixo["resolucao"]
    assert resolucao["resolveu"] is False
    assert isinstance(resolucao["motivo"], str) and resolucao["motivo"]


def test_resolucao_eixo_primario_sem_raiz_tambem_nao_resolve():
    """Mesmo padrão do eixo não-primário (custo_capital): raizes vazia ->
    resolveu=False, independente de 'sugestao' estar presente (só eixos
    primários têm sugestao) — 'resolucao' não pode depender da presença
    de 'sugestao', senão custo_capital (que nunca tem sugestao) sairia
    classificado errado."""
    c = _caso()
    c["preco"]["valor"] = 900.0
    r = reverter(c, "base", 500.0)
    rent = r["eixos"]["rentabilidade"]
    assert "sugestao" in rent  # eixo primário: sugestao presente
    assert rent["resolucao"]["resolveu"] is False


def test_beta_implicito_com_zero_raizes_sai_com_valor_none():
    """O ramo valor=None de _beta_implicito existe no código desde a fatia
    B mas a suíte nunca o produziu — fixa o shape por teste (brief da
    task 3B)."""
    c = _caso()
    c["preco"]["valor"] = 5.0
    r = reverter(c, "base", 500.0)
    b = r["eixos"]["custo_capital"]["beta_implicito"]
    assert b["valor"] is None
    assert b["posicao_na_banda"] == "sem raiz"
    assert b["distancia"] is None
    assert "algebra" in b and isinstance(b["algebra"], str) and b["algebra"]
    assert "raiz_usada" not in b
    assert "nota_multiplas_raizes" not in b


def test_resolucao_cap_alcancavel_resolve():
    r = reverter(_caso(), "base", 500.0)
    cap = r["eixos"]["cap"]
    assert isinstance(cap["CAP_implicito_anos"], float)
    assert cap["resolucao"]["resolveu"] is True


def test_resolucao_cap_fora_da_faixa_nao_resolve():
    c = _caso()
    c["preco"]["valor"] = 70.0
    r = reverter(c, "base", 500.0)
    cap = r["eixos"]["cap"]
    assert isinstance(cap["CAP_implicito_anos"], str)
    assert cap["resolucao"]["resolveu"] is False


def test_resolucao_cap_spread_nao_positivo_atravessa_sem_quebrar():
    """Gatilho verificado: roic=8, wacc=12, tv=book -> spread -4.0 p.p.
    <= 0. O eixo cap volta só com 'erro' e 'alvo_normalizado' — nem
    CAP_implicito_anos nem raizes_* — e reverter() tem de atravessar sem
    KeyError nem TypeError."""
    c = _caso()
    c["cenarios"]["base"]["premissas"]["roic"] = 8.0
    c["cenarios"]["base"]["premissas"]["wacc"] = 12.0
    c["cenarios"]["base"]["premissas"]["tv"] = "book"
    r = reverter(c, "base", 500.0)
    cap = r["eixos"]["cap"]
    assert "erro" in cap and "spread" in cap["erro"]
    assert cap["alvo_normalizado"] == pytest.approx(10.0)
    assert "CAP_implicito_anos" not in cap
    assert not any(k.startswith("raizes") for k in cap)
    assert cap["resolucao"]["resolveu"] is False


def test_resolucao_motivos_distinguem_os_casos_de_nao_resolvido():
    """Os três motivos de 'resolveu=False' têm de ser frases distintas —
    sem raiz, CAP fora da faixa e CAP indefinido por spread são defeitos
    diferentes e o relatório precisa poder diferenciá-los."""
    c_sem_raiz = _caso()
    c_sem_raiz["preco"]["valor"] = 5.0
    motivo_sem_raiz = reverter(c_sem_raiz, "base", 500.0)["eixos"]["custo_capital"]["resolucao"]["motivo"]

    c_fora_da_faixa = _caso()
    c_fora_da_faixa["preco"]["valor"] = 70.0
    motivo_fora_da_faixa = reverter(c_fora_da_faixa, "base", 500.0)["eixos"]["cap"]["resolucao"]["motivo"]

    c_spread = _caso()
    c_spread["cenarios"]["base"]["premissas"]["roic"] = 8.0
    c_spread["cenarios"]["base"]["premissas"]["wacc"] = 12.0
    c_spread["cenarios"]["base"]["premissas"]["tv"] = "book"
    motivo_spread = reverter(c_spread, "base", 500.0)["eixos"]["cap"]["resolucao"]["motivo"]

    motivos = {motivo_sem_raiz, motivo_fora_da_faixa, motivo_spread}
    assert len(motivos) == 3, motivos


def test_resolucao_motivo_nao_e_copia_do_texto_do_motor():
    """'motivo' é frase curta DO WRAPPER — o texto do motor (sem_solucao/
    erro) já está lá ao lado, íntegro; 'motivo' não pode ser uma cópia
    dele."""
    c = _caso()
    c["preco"]["valor"] = 5.0
    eixo = reverter(c, "base", 500.0)["eixos"]["custo_capital"]
    assert eixo["resolucao"]["motivo"] != eixo["sem_solucao"]
    assert len(eixo["resolucao"]["motivo"]) < len(eixo["sem_solucao"])


def _saida_direta_do_eixo(caso: dict, nome_eixo: str, nd_efetivo: float,
                           nome_cenario: str = "base") -> dict:
    """Reconstrói a chamada direta ao motor para um eixo — a mesma
    montagem de vetor que reverter() faz internamente — para comparar,
    chave a chave, contra o que reverter() devolveu: prova que nenhuma
    chave do motor foi removida ou alterada pela adição de 'resolucao'
    (e, no eixo de custo de capital, 'beta_implicito')."""
    from motor import rodar as rodar_motor
    from reversa import RESOLVER_POR_EIXO, _ALVO_BASE

    rota = caso["rota"]
    moeda = caso["moeda"]
    # Correção do item 3: reverter() agora também repassa mercado["rf"] a
    # rodar() — esta reconstrução tem de fazer o mesmo, ou diverge do que
    # reverter() de fato devolve (mesma disciplina que já vale para moeda
    # acima).
    rf = caso["mercado"]["rf"]
    cenario = caso["cenarios"][nome_cenario]
    variavel = RESOLVER_POR_EIXO[nome_eixo][rota]
    alvo = alvo_de_mercado(caso, nome_cenario, nd_efetivo)

    vetor = {k: v for k, v in cenario["premissas"].items() if k != variavel}
    vetor["alvo"] = alvo["valor"]
    vetor["resolver"] = variavel
    vetor["base"] = alvo["base"]
    vetor["alvo-base"] = _ALVO_BASE

    return rodar_motor(rota, vetor, None, moeda, subcomando="rev", rf=rf)


@pytest.mark.parametrize("cenario_de_teste", [
    "base",
    "custo_capital_sem_raiz",
    "cap_fora_da_faixa",
    "cap_spread_nao_positivo",
])
def test_payload_do_motor_permanece_integro_com_resolucao_ao_lado(cenario_de_teste):
    """Nenhuma chave que o motor devolveu é removida nem alterada em
    nenhum dos quatro shapes — 'resolucao' (e 'beta_implicito', só em
    custo_capital) são as ÚNICAS chaves que reverter() acrescenta em cima
    do que uma chamada direta ao motor (mesmo vetor, subcomando 'rev')
    devolveria. Esta é a checagem central do RISCO 1+3: o marcador anda
    AO LADO do payload, nunca no lugar dele."""
    c = _caso()
    if cenario_de_teste == "custo_capital_sem_raiz":
        c["preco"]["valor"] = 5.0
    elif cenario_de_teste == "cap_fora_da_faixa":
        c["preco"]["valor"] = 70.0
    elif cenario_de_teste == "cap_spread_nao_positivo":
        c["cenarios"]["base"]["premissas"]["roic"] = 8.0
        c["cenarios"]["base"]["premissas"]["wacc"] = 12.0
        c["cenarios"]["base"]["premissas"]["tv"] = "book"

    r = reverter(c, "base", 500.0)

    for nome_eixo in ("custo_capital", "crescimento", "rentabilidade", "cap"):
        direto = _saida_direta_do_eixo(c, nome_eixo, 500.0)
        eixo = r["eixos"][nome_eixo]
        extras = {"resolucao", "leitura"} | ({"beta_implicito"} if nome_eixo == "custo_capital" else set())
        assert "resolucao" in eixo and "leitura" in eixo, nome_eixo  # as adicoes em si tem de estar la
        assert set(eixo) - extras == set(direto), nome_eixo
        for chave, valor in direto.items():
            assert eixo[chave] == valor, f"{nome_eixo}.{chave}"


# --------------------------------------------------------------------------
# Fatia 5F, Task 1 (D2/D3 do plano docs/superpowers/plans/2026-09-15-v4-item5f-
# valuation.md): a `leitura` de cada eixo diz o mesmo que o payload do motor ao
# lado; o teto publica a chave do múltiplo; e a curva iso-valor que o motor manda
# rodar junto do teto sai como limitação publicada, com o mesmo gatilho.
# --------------------------------------------------------------------------

import functools  # noqa: E402
import json  # noqa: E402

from avaliar import avaliar  # noqa: E402
from motor import MotorFalhou  # noqa: E402
from reversa import RESOLVER_POR_EIXO, _beta_implicito, _leitura_chave_do_nivel, leitura_do_eixo  # noqa: E402

sys.path.insert(0, str(RAIZ / "tests"))
from relatorio_apoio import carregar_fixture_ou_variante  # noqa: E402

_EIXOS_PERCENTUAIS = ("custo_capital", "crescimento", "rentabilidade")
_CRESCE = "valor cresce com n (spread positivo)"
_DECRESCE = "valor DECRESCE com n — interpretação invertida: n maior destrói valor"


@functools.lru_cache(maxsize=None)
def _publicado_serializado(nome: str) -> str:
    caso = carregar_fixture_ou_variante(nome)
    return json.dumps({"caso": caso, "resultados": avaliar(caso)}, ensure_ascii=False)


def _publicado(nome: str) -> tuple[dict, dict]:
    par = json.loads(_publicado_serializado(nome))
    return par["caso"], par["resultados"]


@pytest.mark.parametrize("nome", ["caso_reversa_firm.json", "reversa_sem_raiz"])
def test_a_leitura_de_cada_eixo_diz_o_que_o_payload_do_motor_ao_lado_diz(nome):
    """Premissa, raiz e identificação contra o payload do motor: a raiz é a de
    `raizes_<var>_%`, na ordem, e identificação, intervalo e curvatura são os que o
    motor calculou para AQUELA raiz — a chave do motor é o número com três casas."""
    caso, resultados = _publicado(nome)
    raizes_conferidas = 0
    for nome_eixo in _EIXOS_PERCENTUAIS:
        eixo = resultados["reversa"]["eixos"][nome_eixo]
        leitura = eixo["leitura"]
        variavel = RESOLVER_POR_EIXO[nome_eixo][caso["rota"]]
        assert (leitura["premissa"], leitura["unidade"]) == (variavel, "pp"), nome_eixo
        assert [raiz["valor"] for raiz in leitura["raizes"]] == eixo[f"raizes_{variavel}_%"], nome_eixo
        for raiz in leitura["raizes"]:
            do_motor = eixo["identificacao_por_raiz"][f"{raiz['valor']:.3f}%"]
            assert (raiz["identificacao"], raiz["intervalo"], raiz["curvatura"]) == (
                do_motor["identificacao"], do_motor["intervalo_para_alvo_±1%"],
                do_motor["curvatura_d2M_dx2"]), (nome_eixo, raiz)
            raizes_conferidas += 1
    cap = resultados["reversa"]["eixos"]["cap"]["leitura"]
    assert (cap["premissa"], cap["unidade"], cap["raizes"]) == (None, "anos_fracionarios", [])
    if nome == "caso_reversa_firm.json":
        assert raizes_conferidas >= 3, "fixture sem raiz — a trava do par raiz x identificação ficou vácua"


def test_reversa_sem_raiz_publica_os_eixos_sem_raiz_o_teto_com_a_chave_e_a_iso_como_limitacao():
    """N9 e D3 sobre a sonda P7 da revisão da 5D: o alvo inalcançável é resultado
    publicado, não omissão."""
    _caso_da_variante, resultados = _publicado("reversa_sem_raiz")
    eixos = resultados["reversa"]["eixos"]
    for nome_eixo in _EIXOS_PERCENTUAIS:
        leitura = eixos[nome_eixo]["leitura"]
        assert (leitura["motivo"], leitura["raizes"]) == ("sem_raiz_na_faixa", []), nome_eixo
    beta = eixos["custo_capital"]["leitura"]["beta"]
    assert (beta["valor"], beta["posicao"], beta["distancia"]) == (None, "sem_raiz", None)
    assert (eixos["cap"]["leitura"]["motivo"], eixos["cap"]["leitura"]["cap_anos"]) == (
        "cap_na_faixa", eixos["cap"]["CAP_implicito_anos"])
    teto = resultados["reversa"]["teto_do_crescimento_gratuito"]
    assert teto["chave"] == resultados["manchete"]["multiplo"]["chave"] == "EV/EBITDA_curr"
    assert "iso_nao_calculada" in resultados["limitacoes"]


def test_caso_reversa_firm_nao_publica_teto_nem_iso_e_le_o_beta_contra_a_banda():
    caso, resultados = _publicado("caso_reversa_firm.json")
    eixos = resultados["reversa"]["eixos"]
    assert "teto_do_crescimento_gratuito" not in resultados["reversa"]
    assert "iso_nao_calculada" not in resultados["limitacoes"]
    assert [eixos[nome]["leitura"]["motivo"] for nome in _EIXOS_PERCENTUAIS] == ["raiz_na_faixa"] * 3
    beta_do_wrapper = eixos["custo_capital"]["beta_implicito"]
    assert eixos["custo_capital"]["leitura"]["beta"] == {
        "valor": beta_do_wrapper["valor"], "posicao": "abaixo", "distancia": beta_do_wrapper["distancia"],
        "banda": caso["mercado"]["beta_observado"], "unidade": "beta"}
    assert (eixos["cap"]["leitura"]["motivo"], eixos["cap"]["leitura"]["cap_anos"]) == (
        "cap_na_faixa", eixos["cap"]["CAP_implicito_anos"])


@pytest.mark.parametrize("banda,posicao,distancia", [
    ([0.1, 0.4], "acima", pytest.approx(3.0 / 5.5 - 0.4)),
    ([0.5, 0.6], "dentro", 0.0),
    ([0.9, 1.3], "abaixo", pytest.approx(0.9 - 3.0 / 5.5)),
    (None, "sem_banda", None),
], ids=["acima", "dentro", "abaixo", "sem_banda"])
def test_a_posicao_do_beta_sai_pelo_codigo_do_vocabulario(banda, posicao, distancia):
    """As posições que nenhuma fixture alcança, sobre um payload no formato do motor:
    raiz de WACC em 15% com rf 12 e erp 5,5 dá beta implícito (15 − 12) ÷ 5,5 ≈ 0,545."""
    saida = {"raizes_wacc_%": [15.0], "identificacao_por_raiz": {"15.000%": {"nota": "derivadas indisponíveis"}}}
    saida["beta_implicito"] = _beta_implicito(saida, "wacc", {"rf": 12.0, "erp": 5.5, "beta_observado": banda})
    beta = leitura_do_eixo("custo_capital", "firm", saida, banda)["beta"]
    assert (beta["posicao"], beta["distancia"], beta["banda"], beta["unidade"]) == (posicao, distancia, banda, "beta")


@pytest.mark.parametrize("saida,motivo,cap_anos", [
    ({"CAP_implicito_anos": 12.5, "direcao": _CRESCE}, "cap_na_faixa", 12.5),
    ({"CAP_implicito_anos": 7.9, "direcao": _DECRESCE}, "cap_na_faixa_decrescente", 7.9),
    ({"CAP_implicito_anos": ">60 — alvo incompatível com estas premissas sob esta convenção (máx em n=60: 12.14)",
      "direcao": _CRESCE}, "cap_fora_da_faixa", None),
    ({"CAP_implicito_anos": "não cruza em n≤60 (faixa 5.69–8.55)", "direcao": _DECRESCE}, "cap_fora_da_faixa", None),
    ({"erro": "CAP implícito indefinido: spread = -4.0 p.p. ≤ 0.", "alvo_normalizado": 10.0}, "cap_indefinido", None),
], ids=["crescente", "decrescente", "texto_crescente", "texto_decrescente", "erro"])
def test_as_saidas_do_cap_viram_motivo_e_anos(saida, motivo, cap_anos):
    leitura = leitura_do_eixo("cap", "firm", saida)
    assert (leitura["motivo"], leitura["cap_anos"], leitura["premissa"], leitura["raizes"]) == (
        motivo, cap_anos, None, [])


def test_o_cap_decrescente_do_motor_de_verdade_e_lido_como_decrescente():
    """O literal da direção decrescente conferido contra o motor, não contra uma cópia
    dele: ROIC 8 abaixo do WACC 12 em convergência, com preço 40, faz o valor cair com n
    e o CAP fechar em 7,9 anos de destruição de valor tolerados."""
    c = _caso()
    c["cenarios"]["base"]["premissas"].update({"roic": 8.0, "wacc": 12.0, "tv": "convergencia"})
    c["preco"]["valor"] = 40.0
    c["reversa"]["eixos"] = ["cap"]
    cap = reverter(c, "base", 500.0)["eixos"]["cap"]
    assert cap["direcao"] == _DECRESCE
    assert (cap["leitura"]["motivo"], cap["leitura"]["cap_anos"]) == ("cap_na_faixa_decrescente", 7.9)
    assert cap["resolucao"]["resolveu"] is True


def test_identificacao_indisponivel_e_toque_tangencial_saem_sem_numero_inventado():
    """`identificacao()` sem derivadas devolve só `{nota}`: identificação, intervalo e
    curvatura saem nulos. Um eixo só com toque tangencial não tem raiz — o toque sai em
    `tangenciais`."""
    com_nota = leitura_do_eixo("crescimento", "firm", {
        "raizes_g_%": [4.2],
        "identificacao_por_raiz": {"4.200%": {"nota": "derivadas indisponíveis na vizinhança da raiz"}}})
    assert com_nota["motivo"] == "raiz_na_faixa"
    assert com_nota["raizes"] == [{"valor": 4.2, "identificacao": None, "intervalo": None, "curvatura": None}]

    so_toque = leitura_do_eixo("rentabilidade", "equity", {
        "raizes_roe_%": [],
        "raizes_tangenciais_roe_%": [{"x_%": 18.4, "residuo": 1e-07, "nota": "toque sem cruzamento"}]})
    assert (so_toque["premissa"], so_toque["motivo"], so_toque["raizes"], so_toque["tangenciais"]) == (
        "roe", "sem_raiz_na_faixa", [], [18.4])


@pytest.mark.parametrize("nome_eixo,saida", [
    ("crescimento", {"raizes_g_%": [4.2, 6.1], "identificacao_por_raiz": {"4.200%": {"identificacao": "forte"}}}),
    ("crescimento", {"raizes_g_%": [4.2], "identificacao_por_raiz": {"4.200%": {"identificacao": "nula"}}}),
    ("cap", {"CAP_implicito_anos": 9.0, "direcao": "valor oscila com n"}),
], ids=["raiz_sem_par", "identificacao_desconhecida", "direcao_desconhecida"])
def test_a_leitura_recusa_nomeando_a_saida_que_nao_sabe_ler(nome_eixo, saida):
    with pytest.raises(MotorFalhou):
        leitura_do_eixo(nome_eixo, "firm", saida)


# --------------------------------------------------------------------------
# Fatia 5H, Task 1 (D1/D2): o nível implícito da métrica-base e o confronto temporal
# contra o consenso declarado. A conta é do motor (subcomando `nivel`); o que se mede
# aqui é a chamada que este wrapper monta e a chave que ele classifica.
# --------------------------------------------------------------------------

_CONSENSO_ACIMA_DA_IMPLICITA = {"t1": {"valor": 1040.0, "periodo": "2026E"},
                                "t2": {"valor": 1100.0, "periodo": "2027E"}}


def _com_consenso(consenso: dict) -> dict:
    c = _caso()
    c["reversa"]["consenso"] = consenso
    return c


def test_o_nivel_implicito_e_o_valor_de_mercado_sobre_o_multiplo_justo_publicado():
    """O oráculo da conta, com os dois números que a própria integração publica: a
    métrica implícita é o valor de mercado do alvo dividido pelo múltiplo justo CORRENTE
    do cenário da reversa — o mesmo que `cenarios.<cenário>.multiplos` traz. Preço 55 x
    100 ações + dívida líquida 500 = 6.000 de EV de mercado; múltiplo justo 6,6906x =>
    EBITDA implícito 896,78 contra os 1.000 declarados, um degrau de −10,3%."""
    resultados = avaliar(_caso())
    reversa = resultados["reversa"]
    nivel = reversa["nivel_implicito"]
    justo = resultados["cenarios"]["base"]["multiplos"]["EV/EBITDA_curr"]

    assert reversa["alvo"]["valor_de_mercado"] == pytest.approx(6000.0)
    assert justo == pytest.approx(6.6906, abs=1e-4)
    assert nivel["metrica_base_implicita"] == pytest.approx(
        reversa["alvo"]["valor_de_mercado"] / justo, abs=0.01)
    assert nivel["metrica_base_atual"] == pytest.approx(1000.0)
    assert nivel["fator_k_implicito"] == pytest.approx(0.8968, abs=1e-4)
    assert nivel["degrau_implicito_%"] == pytest.approx(-10.3, abs=0.05)


def test_sem_consenso_declarado_nao_ha_razoes_nem_leitura():
    """Sem `reversa.consenso` o motor não emite razão nenhuma nem a prosa da leitura, e
    o wrapper não inventa classificação: `leitura_chave` sai nula, e o nível implícito
    continua publicado — o degrau que o preço embute não depende de haver consenso."""
    nivel = reverter(_caso(), "base", 500.0)["nivel_implicito"]
    assert nivel["leitura_chave"] is None
    assert "leitura" not in nivel
    assert not [chave for chave in nivel if chave.startswith("razao_vs_consenso")]


@pytest.mark.parametrize("t2,leitura,razao_t1,razao_t2", [
    (720.0, "antecipacao_temporal", 1.3797, 1.2455),
    (700.0, "acima_do_consenso", 1.3797, 1.2811),
], ids=["dentro_de_125", "acima_de_125"])
def test_a_leitura_do_confronto_temporal_vira_dos_125_por_cento_do_maior_consenso(
        t2, leitura, razao_t1, razao_t2):
    """O limiar do vendor (§4 de `references/aplicacao.md`, calibrado em J8), medido dos
    dois lados com a MESMA implícita (896,78): contra t+2 de 720 o teto é 900 e a
    leitura é antecipação temporal; contra 700 o teto cai para 875 e a hipótese terminal
    passa a estar no preço. As duas razões saem do motor, uma por ponto declarado."""
    nivel = reverter(_com_consenso({"t1": {"valor": 650.0, "periodo": "2026E"},
                                    "t2": {"valor": t2, "periodo": "2027E"}}),
                     "base", 500.0)["nivel_implicito"]
    assert nivel["leitura_chave"] == leitura
    assert nivel["razao_vs_consenso_t1"] == pytest.approx(razao_t1, abs=1e-4)
    assert nivel["razao_vs_consenso_t2"] == pytest.approx(razao_t2, abs=1e-4)
    # A prosa do motor continua publicada, íntegra, ao lado da chave — o relatório lê a
    # chave e nunca o texto.
    assert nivel["leitura"].startswith(leitura + ":")


def test_so_o_ponto_declarado_vira_razao():
    """Um consenso só com t+1 produz uma razão só — o wrapper nunca completa o ponto que
    o caso não declarou."""
    nivel = reverter(_com_consenso({"t1": {"valor": 1040.0, "periodo": "2026E"}}),
                     "base", 500.0)["nivel_implicito"]
    assert nivel["razao_vs_consenso_t1"] == pytest.approx(896.78 / 1040.0, abs=1e-3)
    assert "razao_vs_consenso_t2" not in nivel
    assert nivel["leitura_chave"] == "antecipacao_temporal"


def test_uma_leitura_do_nivel_fora_do_vocabulario_e_motor_falhou_nomeado():
    """Mesma disciplina de `_identificacao_da_raiz`: um prefixo que o catálogo não
    rotula é recusa nomeada, nunca código cru na tela."""
    assert _leitura_chave_do_nivel({"leitura": "acima_do_consenso: texto do motor"}) == "acima_do_consenso"
    with pytest.raises(MotorFalhou):
        _leitura_chave_do_nivel({"leitura": "fantasia_terminal: texto do motor"})


# --------------------------------------------------------------------------
# Migração v10.1, Task 2 (Q2 do grill de 17/09): a leitura RECALCULADA do nível implícito. O
# `nivel` da v10.1 recalcula o múltiplo a cada nível, com a D&A fixa em moeda e o resto do vetor
# travado — é a leitura central; a de múltiplo fixo vira o extremo da escada. Só na rota firm com
# métrica EBITDA: em ×NOPAT a D&A não entra no múltiplo, e em P/L ela não existe.
# --------------------------------------------------------------------------

from caso import validar  # noqa: E402
from relatorio_apoio import com_bloco_de_reversa_valido  # noqa: E402


def test_a_leitura_central_do_nivel_recalcula_o_multiplo_e_fica_entre_a_base_e_o_limite():
    caso = _caso()  # firm/EBITDA com reversa (caso_reversa_firm.json)
    nivel = reverter(caso, "base", 500.0)["nivel_implicito"]
    rec = nivel["recalculado"]
    base, limite = caso["metrica_base"]["valor"], nivel["metrica_base_implicita"]
    central = rec["metrica_base_implicita_recalculada"]
    # a escada da v10.1: o múltiplo recalculado leva o nível para entre a base e a leitura congelada
    assert min(base, limite) < central < max(base, limite)
    # a D&A entrou em moeda, pelo encargo de reposição do cenário sobre a métrica-base
    da = caso["cenarios"]["base"]["premissas"]["da"]
    assert rec["d_no_nivel_implicito_%"] == pytest.approx(da * base / central, rel=1e-3)


def _firm_por_nopat() -> dict:
    """A mesma companhia escalada pelo NOPAT coerente (1.000 x 0,80 x 0,75 = 600)."""
    c = _caso()
    c["metrica_base"] = {"tipo": "NOPAT", "valor": 600.0, "periodo": "2025A", "fonte": "fixture sintética"}
    return c


def _equity_com_reversa() -> dict:
    return com_bloco_de_reversa_valido(carregar(FIXTURES / "caso_minimo_equity.json"))


@pytest.mark.parametrize("caso,nd_efetivo", [
    (_firm_por_nopat, 500.0),
    (_equity_com_reversa, 0.0),
], ids=["firm_por_nopat", "equity"])
def test_sem_a_metrica_ebitda_da_rota_firm_o_nivel_so_tem_a_leitura_congelada(caso, nd_efetivo):
    """O wrapper só manda ao `nivel` o segundo bloco de flags na rota firm com EBITDA: fora dela o
    motor devolve a leitura congelada sozinha, sem `recalculado` nem a nota dele."""
    c = caso()
    validar(c)
    nivel = reverter(c, "base", nd_efetivo)["nivel_implicito"]
    assert nivel["metrica_base_implicita"] > 0
    assert {"recalculado", "recalculado_nota"} & set(nivel) == set()
