import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures"
sys.path.insert(0, str(RAIZ / "skills" / "er-valuation" / "scripts"))
from caso import carregar  # noqa: E402
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
    cenario = caso["cenarios"][nome_cenario]
    variavel = RESOLVER_POR_EIXO[nome_eixo][rota]
    alvo = alvo_de_mercado(caso, nome_cenario, nd_efetivo)

    vetor = {k: v for k, v in cenario["premissas"].items() if k != variavel}
    vetor["alvo"] = alvo["valor"]
    vetor["resolver"] = variavel
    vetor["base"] = alvo["base"]
    vetor["alvo-base"] = _ALVO_BASE

    return rodar_motor(rota, vetor, None, moeda, subcomando="rev")


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
        extras = {"resolucao"} | ({"beta_implicito"} if nome_eixo == "custo_capital" else set())
        assert "resolucao" in eixo, nome_eixo  # a adicao em si tem de estar la
        assert set(eixo) - extras == set(direto), nome_eixo
        for chave, valor in direto.items():
            assert eixo[chave] == valor, f"{nome_eixo}.{chave}"
