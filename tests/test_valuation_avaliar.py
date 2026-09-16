import filecmp
import json
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures"
SCRIPTS = RAIZ / "skills" / "er-valuation" / "scripts"
sys.path.insert(0, str(SCRIPTS))
from caso import carregar  # noqa: E402
from avaliar import _exigir_valor, avaliar, escrever  # noqa: E402
from motor import MotorFalhou, rodar as _motor_rodar  # noqa: E402
from ponte import compor as _compor_ponte  # noqa: E402


def _res_firm() -> dict:
    return avaliar(carregar(FIXTURES / "caso_minimo_firm.json"))


def test_cabecalho_vem_do_caso():
    r = _res_firm()
    assert r["companhia"] == "Sintética S.A."
    assert r["rota"] == "firm" and r["moeda"] == "BRL-nominal"


def test_valor_por_acao_reproduz_o_motor():
    v = _res_firm()["cenarios"]["base"]["valor"]
    assert v["EV"] == pytest.approx(6690.59, abs=0.01)
    assert v["Equity"] == pytest.approx(6190.59, abs=0.01)
    assert v["preco_acao"] == pytest.approx(61.91, abs=0.01)


def test_upside_e_calculado_contra_o_preco_do_caso():
    r = _res_firm()["cenarios"]["base"]
    esperado = 61.91 / 55.0 - 1
    assert r["vs_preco"]["upside"] == pytest.approx(esperado, abs=1e-4)


def test_ponte_aparece_decomposta_e_bate_com_o_nd_usado():
    r = _res_firm()
    assert r["ponte"]["nd_efetivo"] == pytest.approx(500.0)
    assert sum(p["valor"] * p["sinal"] for p in r["ponte"]["parcelas"]) == pytest.approx(500.0)


def test_diagnosticos_do_motor_chegam_ao_resultado():
    d = _res_firm()["cenarios"]["base"]["diagnosticos"]
    assert isinstance(d, list) and any("RiR" in x for x in d)


def test_rota_equity_produz_equity_sem_ponte():
    r = avaliar(carregar(FIXTURES / "caso_minimo_equity.json"))
    assert "ponte" not in r or r["ponte"] is None
    v = r["cenarios"]["base"]["valor"]
    assert v["Equity"] == pytest.approx(4501.51, abs=0.01)
    assert v["preco_acao"] == pytest.approx(45.02, abs=0.01)
    assert "EV" not in v


# --------------------------------------------------------------------------
# Revisão final, FIX 1 (Crítico): o serializador do motor congelado converte
# todo float não-finito (NaN, Infinity) em `null` e ainda assim sai com
# código 0. Terminal 'gordon' sem 'roic_tv' é um caso que caso.validar()
# aceita (roic_tv é opcional no schema — só é semanticamente exigido pelo
# motor sob a convenção gordon) e que produz exatamente esse null. Sem
# guarda, isso ou quebra com TypeError cru na primeira divisão (upside) ou —
# pior — grava null em silêncio em resultados.json quando só um múltiplo
# secundário nula e o preço sobrevive.
# --------------------------------------------------------------------------

def test_avaliar_recusa_quando_motor_devolve_null_por_nao_finito():
    c = carregar(FIXTURES / "caso_minimo_firm.json")
    del c["cenarios"]["base"]["premissas"]["roic_tv"]
    with pytest.raises(MotorFalhou, match="EV") as excinfo:
        avaliar(c)
    mensagem = str(excinfo.value)
    # diagnósticos do próprio motor têm de ser ecoados, não reinterpretados.
    assert "RiR" in mensagem


def test_exigir_valor_recusa_null_nomeando_campo_e_ecoando_diagnosticos():
    """Unidade da normalização: _exigir_valor é o único ponto por onde toda
    leitura de EV/Equity/Preco_acao/múltiplo do motor passa."""
    saida = {"EV": None, "diagnosticos": ["diagnóstico de teste do motor"]}
    with pytest.raises(MotorFalhou, match="EV") as excinfo:
        _exigir_valor(saida, "EV")
    assert "diagnóstico de teste do motor" in str(excinfo.value)


def test_exigir_valor_devolve_o_valor_quando_nao_e_null():
    saida = {"EV": 123.45, "diagnosticos": []}
    assert _exigir_valor(saida, "EV") == 123.45


def test_multiplo_copiado_null_recusa(monkeypatch):
    """Um múltiplo secundário — só copiado para a saída, nunca usado em
    conta — vindo null do motor tem de recusar também, não só EV/Equity/
    Preco_acao. Motor mockado (sem subprocess) para isolar exatamente este
    campo, com todo o resto do vetor válido."""
    def _saida_com_multiplo_nulo(rota, premissas, escala, moeda=None, rf=None):
        return {
            "EV/NOPAT_curr": 11.151, "EV/NOPAT_fwd": None,
            "EV/EBITDA_curr": 6.6906, "EV/EBITDA_fwd": 6.372,
            "EV": 6690.59, "Equity": 6190.59, "Preco_acao": 61.91,
            "diagnosticos": ["diagnóstico de teste"],
            "coerencia_vetor": {}, "convencao_temporal": "fim de ano",
        }
    monkeypatch.setattr("avaliar.rodar", _saida_com_multiplo_nulo)
    c = carregar(FIXTURES / "caso_minimo_firm.json")
    with pytest.raises(MotorFalhou, match=r"EV/NOPAT_fwd"):
        avaliar(c)


# --------------------------------------------------------------------------
# Revisão final, FIX 2: roic_tv:null é ausência legítima segundo caso.py —
# mas só de verdade se argv_para pular a premissa (não a transformar em
# '--roic-tv None'). Sob tv='gordon' (a fixture padrão), roic_tv É exigido
# pelo motor, então testar a null ali dispararia o null-guard do FIX 1, não
# provaria nada sobre FIX 2. Sob tv != gordon, roic_tv é genuinamente
# inerte — o cenário certo para prova de ponta a ponta com avaliar() real.
# --------------------------------------------------------------------------

def test_avaliar_aceita_premissa_opcional_nula_no_pipeline_completo():
    c = carregar(FIXTURES / "caso_minimo_firm.json")
    c["cenarios"]["base"]["premissas"]["tv"] = "convergencia"
    c["cenarios"]["base"]["premissas"]["roic_tv"] = None
    r = avaliar(c)
    assert r["cenarios"]["base"]["valor"]["EV"] > 0


# --------------------------------------------------------------------------
# Revisão final, FIX 4: 'moeda' é obrigatório, validado por caso.py e ecoado
# em resultados.json — mas nunca chegava ao motor. Toda saída deste pipeline
# carregava o aviso falso "MOEDA/REGIME NÃO DECLARADOS", causado pelo
# wrapper. Passar --moeda não muda nenhum número.
# --------------------------------------------------------------------------

def test_moeda_do_caso_e_repassada_ao_motor_sem_mudar_numeros():
    r = _res_firm()
    diagnosticos = r["cenarios"]["base"]["diagnosticos"]
    assert not any("MOEDA/REGIME" in d for d in diagnosticos)
    v = r["cenarios"]["base"]["valor"]
    assert v["EV"] == pytest.approx(6690.59, abs=0.01)
    assert v["preco_acao"] == pytest.approx(61.91, abs=0.01)


# --------------------------------------------------------------------------
# Correção do item 3: 'mercado.rf' do caso nunca chegava ao motor, então
# `_guardas_damodaran` (a âncora macro do gp, Damodaran) nunca via 'rf' —
# todo terminal 'gordon' com gp > 0 saía "PREMISSA NÃO ANCORADA", mesmo com
# rf declarado no caso, e um gp perpétuo acima do rf nominal (erro clássico
# de sobrevalorização) nunca era alertado. 'rf' segue o mesmo trajeto que
# 'moeda' já percorre (ver teste acima). caso_minimo_firm.json e
# caso_reversa_firm.json compartilham a mesma companhia/preço/ponte/
# métrica_base e o MESMO vetor central do cenário 'base' (mesmo g/roic/
# wacc/gp/tv) — a única diferença declarada é caso_reversa_firm.json ter
# 'mercado' (e 'reversa'/'sensibilidades', que não tocam o cenário
# principal).
# --------------------------------------------------------------------------

def test_guarda_damodaran_reage_a_rf_nos_tres_ramos():
    """A âncora macro do gp (Damodaran) tem três ramos para tv='gordon' com
    gp > 0, e os três têm de continuar alcançáveis com 'rf' repassado:
      (a) sem bloco 'mercado' no caso: 'PREMISSA NÃO ANCORADA' — o
          comportamento de hoje, que tem de continuar valendo quando o
          caso genuinamente não declara rf;
      (b) com 'mercado.rf' e gp <= rf: 'ÂNCORA MACRO OK';
      (c) com 'mercado.rf' e gp > rf: 'ALERTA (âncora macro, Damodaran)'.
    """
    sem_mercado = _res_firm()  # caso_minimo_firm.json: gordon, gp=3.0, sem mercado
    assert any("PREMISSA NÃO ANCORADA" in d
               for d in sem_mercado["cenarios"]["base"]["diagnosticos"])

    c_ok = carregar(FIXTURES / "caso_minimo_firm.json")
    c_ok["mercado"] = {"rf": 12.0, "erp": 5.5, "fonte": "teste", "data": "2026-08-21"}
    r_ok = avaliar(c_ok)  # gp=3.0 <= rf=12.0
    assert any("ÂNCORA MACRO OK" in d
               for d in r_ok["cenarios"]["base"]["diagnosticos"])

    c_alerta = carregar(FIXTURES / "caso_minimo_firm.json")
    c_alerta["mercado"] = {"rf": 12.0, "erp": 5.5, "fonte": "teste", "data": "2026-08-21"}
    # wacc sobe junto com gp só para o Gordon do cenário ficar bem definido
    # (gp < wacc); o que este teste mede é o diagnóstico, não este número.
    c_alerta["cenarios"]["base"]["premissas"]["wacc"] = 20.0
    c_alerta["cenarios"]["base"]["premissas"]["gp"] = 15.0
    r_alerta = avaliar(c_alerta)  # gp=15.0 > rf=12.0
    assert any("ALERTA (âncora macro, Damodaran)" in d
               for d in r_alerta["cenarios"]["base"]["diagnosticos"])


def test_rf_do_caso_e_repassado_ao_motor_sem_mudar_numeros():
    """Espelho de test_moeda_do_caso_e_repassada_ao_motor_sem_mudar_numeros
    para 'rf': EV/Equity/preco_acao do cenário 'base' têm de sair idênticos
    com e sem 'mercado' declarado — 'rf' só muda diagnóstico (a âncora
    macro do gp), nunca entra na álgebra de precificação."""
    sem_mercado = _res_firm()
    com_mercado = avaliar(carregar(FIXTURES / "caso_reversa_firm.json"))

    assert sem_mercado["cenarios"]["base"]["valor"] == com_mercado["cenarios"]["base"]["valor"]

    assert any("PREMISSA NÃO ANCORADA" in d
               for d in sem_mercado["cenarios"]["base"]["diagnosticos"])
    assert any("ÂNCORA MACRO OK" in d
               for d in com_mercado["cenarios"]["base"]["diagnosticos"])


# --------------------------------------------------------------------------
# Revisão final, FIX 5: metrica_base.fonte é documentado no SKILL.md como
# obrigatório, mas avaliar() cortava a saída para {tipo, valor} — descartando
# periodo e fonte, enquanto 'preco' mantém as duas. A métrica-base é a escala
# de todo o valuation; era o único número do caso sem proveniência no
# arquivo final.
# --------------------------------------------------------------------------

def test_metrica_base_carrega_periodo_e_fonte_na_saida():
    r = _res_firm()
    m = r["metrica_base"]
    assert m["tipo"] == "EBITDA" and m["valor"] == pytest.approx(1000.0)
    assert m["fonte"] == "fixture sintética"
    assert m["periodo"] == "2025A"


def test_metrica_base_sem_periodo_nao_inclui_a_chave_na_saida():
    """periodo continua opcional — só entra na saída quando presente no caso."""
    c = carregar(FIXTURES / "caso_minimo_firm.json")
    del c["metrica_base"]["periodo"]
    r = avaliar(c)
    assert "periodo" not in r["metrica_base"]
    assert r["metrica_base"]["fonte"] == "fixture sintética"


# --------------------------------------------------------------------------
# Fatia B, Task 5: os blocos 'reversa' e 'sensibilidades' entram no
# resultados.json só quando o caso os declara. O caso da fatia A
# (`caso_minimo_firm.json`, sem os dois blocos) não pode ganhar nenhuma
# chave nova — é a propriedade que mais importa, porque tudo a jusante (o
# builder de relatório, num item futuro) é escrito contra as duas formas.
# --------------------------------------------------------------------------

def test_resultado_sem_blocos_novos_nao_ganha_chaves():
    """Caso da fatia A continua produzindo exatamente o que produzia."""
    r = avaliar(carregar(FIXTURES / "caso_minimo_firm.json"))
    assert "reversa" not in r and "sensibilidades" not in r


def test_resultado_com_reversa_traz_o_bloco():
    r = avaliar(carregar(FIXTURES / "caso_reversa_firm.json"))
    assert r["reversa"]["eixos"]["custo_capital"]["beta_implicito"]["valor"]
    assert r["reversa"]["alvo"]["valor"] == pytest.approx(6.0)


def test_resultado_com_sensibilidades_traz_o_bloco():
    r = avaliar(carregar(FIXTURES / "caso_reversa_firm.json"))
    assert r["sensibilidades"]["grades_1d"]
    assert r["sensibilidades"]["grades_2d"]


def test_saida_com_reversa_continua_deterministica(tmp_path):
    import filecmp
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    escrever(avaliar(carregar(FIXTURES / "caso_reversa_firm.json")), a)
    escrever(avaliar(carregar(FIXTURES / "caso_reversa_firm.json")), b)
    assert filecmp.cmp(a, b, shallow=False)


def test_valores_consumidos_nao_sao_null_mas_o_repasse_do_motor_e_integro():
    """A recusa de null vale para o que o wrapper CONSOME.

    O payload de diagnostico do motor chega integro, e pode legitimamente
    conter null (o proprio motor serializa nao-finito como null nos campos
    que ele mesmo declara nao aplicaveis). Uniformizar isso seria ajustar
    output do motor — proibido.
    """
    r = avaliar(carregar(FIXTURES / "caso_reversa_firm.json"))
    v = r["cenarios"]["base"]["valor"]
    assert all(v[k] is not None for k in v)
    assert all(x is not None for x in r["cenarios"]["base"]["multiplos"].values())


def test_escala_por_nopat_reconcilia_com_a_escala_por_ebitda():
    """Mesma economia, duas rotas de escala: EV, Equity e preco_acao tem de bater.

    Com EBITDA 1000, d 20% e t 25%, o NOPAT coerente e 1000*(1-0.20)*(1-0.25) = 600.
    EV/NOPAT_curr x 600 tem de dar o mesmo EV que EV/EBITDA_curr x 1000 — e dali em
    diante a ponte (Equity = EV - nd_efetivo) e a divisão por ações
    (preco_acao = Equity / acoes_diluidas) são a única aritmética que este wrapper
    faz fora do motor. FIX 6 (revisão final): antes só EV era conferido; um sinal
    trocado em "ev - nd_efetivo" (para "ev + nd_efetivo", por exemplo) deixava a
    suíte inteira verde. Equity e preco_acao aqui fecham essa lacuna.
    """
    c = carregar(FIXTURES / "caso_minimo_firm.json")
    c["metrica_base"] = {"tipo": "NOPAT", "valor": 600.0, "periodo": "2025A",
                         "fonte": "derivado do EBITDA da fixture"}
    r = avaliar(c)
    valor = r["cenarios"]["base"]["valor"]
    assert valor["EV"] == pytest.approx(6690.59, abs=0.05)
    assert valor["Equity"] == pytest.approx(6190.59, abs=0.05)
    assert valor["preco_acao"] == pytest.approx(61.91, abs=0.05)


def test_saida_e_deterministica(tmp_path):
    """FIX 7 (revisão final): a versão anterior comparava com sort_keys=True,
    cancelando exatamente a diferença de ordem de chave que quebraria
    byte-identidade — e rodava as duas chamadas no mesmo processo Python, sem
    nunca provar nada sobre dois processos distintos. A garantia que importa é
    byte a byte, entre duas invocações reais da CLI, sem normalizar nada."""
    destino_a = tmp_path / "a.json"
    destino_b = tmp_path / "b.json"
    for destino in (destino_a, destino_b):
        r = subprocess.run(
            [sys.executable, str(SCRIPTS / "avaliar.py"),
             str(FIXTURES / "caso_minimo_firm.json"), "--out", str(destino)],
            capture_output=True, text=True, encoding="utf-8", timeout=120)
        assert r.returncode == 0, r.stdout + r.stderr
    assert filecmp.cmp(destino_a, destino_b, shallow=False)


def test_saida_nao_carrega_hora_nem_caminho_absoluto():
    texto = json.dumps(_res_firm(), ensure_ascii=False)
    assert "C:\\" not in texto and "/c/" not in texto
    for suspeito in ("timestamp", "gerado_em", "executado_em"):
        assert suspeito not in texto


def test_escrever_e_reler_preserva(tmp_path):
    destino = tmp_path / "resultados.json"
    escrever(_res_firm(), destino)
    assert json.loads(destino.read_text(encoding="utf-8"))["rota"] == "firm"


def test_cli_gera_o_arquivo(tmp_path):
    destino = tmp_path / "out.json"
    r = subprocess.run(
        [sys.executable, str(SCRIPTS / "avaliar.py"),
         str(FIXTURES / "caso_minimo_firm.json"), "--out", str(destino)],
        capture_output=True, text=True, encoding="utf-8", timeout=120)
    assert r.returncode == 0, r.stdout + r.stderr
    assert json.loads(destino.read_text(encoding="utf-8"))["companhia"] == "Sintética S.A."


def test_cli_recusa_caso_invalido_com_exit_1(tmp_path):
    ruim = tmp_path / "ruim.json"
    c = json.loads((FIXTURES / "caso_minimo_firm.json").read_text(encoding="utf-8"))
    del c["cenarios"]["base"]["premissas"]["tv"]
    ruim.write_text(json.dumps(c), encoding="utf-8")
    r = subprocess.run(
        [sys.executable, str(SCRIPTS / "avaliar.py"), str(ruim), "--out", str(tmp_path / "x.json")],
        capture_output=True, text=True, encoding="utf-8", timeout=120)
    assert r.returncode == 1
    assert "convenção terminal" in (r.stdout + r.stderr)


# --------------------------------------------------------------------------
# FIX 2: o CLI tem de tratar todo erro alcançável de forma limpa — não só
# CasoInvalido/MotorFalhou. `carregar` pode levantar FileNotFoundError
# (caminho ruim) e json.JSONDecodeError (JSON malformado); a escrita de
# --out pode levantar OSError. Sem tratamento, os três vazam traceback cru
# para o usuário, mesmo saindo com código 1 (comportamento padrão do
# Python para exceção não capturada) — o bug não é o exit code, é o
# traceback bruto substituindo uma mensagem legível em PT-BR.
# --------------------------------------------------------------------------

def test_cli_recusa_caminho_inexistente_sem_traceback(tmp_path):
    inexistente = tmp_path / "nao_existe.json"
    r = subprocess.run(
        [sys.executable, str(SCRIPTS / "avaliar.py"), str(inexistente), "--out", str(tmp_path / "x.json")],
        capture_output=True, text=True, encoding="utf-8", timeout=120)
    saida = r.stdout + r.stderr
    assert r.returncode == 1
    assert "Traceback" not in saida
    assert str(inexistente) in saida


def test_cli_recusa_json_malformado_sem_traceback(tmp_path):
    ruim = tmp_path / "ruim.json"
    ruim.write_text("{ nao e json", encoding="utf-8")
    r = subprocess.run(
        [sys.executable, str(SCRIPTS / "avaliar.py"), str(ruim), "--out", str(tmp_path / "x.json")],
        capture_output=True, text=True, encoding="utf-8", timeout=120)
    saida = r.stdout + r.stderr
    assert r.returncode == 1
    assert "Traceback" not in saida


def test_cli_recusa_falha_ao_gravar_out_sem_traceback(tmp_path):
    destino = tmp_path / "pasta_inexistente" / "out.json"
    r = subprocess.run(
        [sys.executable, str(SCRIPTS / "avaliar.py"),
         str(FIXTURES / "caso_minimo_firm.json"), "--out", str(destino)],
        capture_output=True, text=True, encoding="utf-8", timeout=120)
    saida = r.stdout + r.stderr
    assert r.returncode == 1
    assert "Traceback" not in saida
    assert str(destino) in saida


# --------------------------------------------------------------------------
# FIX 3: MotorFalhou alcançando o CLI não tinha teste, embora CasoInvalido
# tivesse. Gatilho: 'tv' com um valor que caso.py aceita — é string
# presente e não-nula, e caso.py não valida 'tv' contra o vocabulário
# fechado do motor (TVS = book/convergencia/gordon/ic/spread), só presença
# e tipo — mas que o motor congelado recusa via `choices` do argparse
# (saída não-zero). Confirmado manualmente antes deste teste: este 'tv'
# atravessa `caso.validar` sem recusa e só é pego no subprocess do motor.
# --------------------------------------------------------------------------

def test_cli_recusa_motor_falhou_sem_traceback(tmp_path):
    ruim = tmp_path / "tv_desconhecido_do_motor.json"
    c = json.loads((FIXTURES / "caso_minimo_firm.json").read_text(encoding="utf-8"))
    c["cenarios"]["base"]["premissas"]["tv"] = "nao_existe"
    ruim.write_text(json.dumps(c), encoding="utf-8")
    r = subprocess.run(
        [sys.executable, str(SCRIPTS / "avaliar.py"), str(ruim), "--out", str(tmp_path / "x.json")],
        capture_output=True, text=True, encoding="utf-8", timeout=120)
    saida = r.stdout + r.stderr
    assert r.returncode == 1
    assert "Traceback" not in saida
    assert "nao_existe" in saida


# --------------------------------------------------------------------------
# Fatia C, Task 1: rota rampa — EV/Equity/Preco_acao vêm prontos do motor
# (composição bifásica), múltiplo-manchete é EV/EBITDA0, e checks_internos/
# travas chegam ao resultado intactos (produto, não ruído).
# --------------------------------------------------------------------------

def test_rota_rampa_produz_valor_e_multiplo_sobre_ebitda0():
    r = avaliar(carregar(FIXTURES / "caso_rampa.json"))
    v = r["cenarios"]["base"]["valor"]
    assert v["EV"] == pytest.approx(170.9304, abs=1e-2)
    assert v["preco_acao"] == pytest.approx(9.05, abs=0.01)
    assert r["cenarios"]["base"]["multiplos"]["EV/EBITDA0"] == pytest.approx(6.378, abs=1e-3)


def test_rampa_leva_checks_e_travas_ao_resultado():
    r = avaliar(carregar(FIXTURES / "caso_rampa.json"))["cenarios"]["base"]
    assert r["checks_internos"]["P4_receita_T_menos_capacidade"] == pytest.approx(0.0)
    assert len(r["travas"]) == 3


# --------------------------------------------------------------------------
# Correção de achado (pós Fatia C, Task 1): a composição do cenário rampa
# lia a saída do motor por uma WHITELIST nomeada (checks_internos, travas,
# d_trajetoria_fase1_%, rir_fase1_%, capacidade_receita) — cinco chaves
# entravam, treze não, entre elas rir2_%/roic2_% (a taxa e o retorno
# marginal de reinvestimento da FASE 2 — sem elas o cenário fica opaco
# sobre quase metade do lucro operacional sendo reinvestido) e
# vp_fase1/valor_fase2_no_ano_T (a decomposição de valor entre as duas
# fases — o ponto central de uma composição bifásica). O teste abaixo é a
# guarda contra essa classe de regressão voltar: toda chave que o motor
# devolveu tem de sobreviver no cenário, exceto as que o wrapper PROMOVE de
# propósito para dentro de `valor`/`multiplos`. O conjunto de promovidas é
# nomeado AQUI, à mão — nunca importado de `avaliar.py` — para que uma
# mudança futura na promoção precise atualizar este teste deliberadamente,
# em vez de o teste herdar a mudança em silêncio e parar de proteger nada.
# --------------------------------------------------------------------------

_CHAVES_PROMOVIDAS_ROTA_RAMPA = frozenset({"EV", "Equity", "Preco_acao", "EV/EBITDA0"})


def test_rampa_repassa_toda_chave_do_motor_exceto_as_promovidas():
    c = carregar(FIXTURES / "caso_rampa.json")
    nd_efetivo = _compor_ponte(c["ponte"])["nd_efetivo"]
    premissas = c["cenarios"]["base"]["premissas"]
    saida_motor = _motor_rodar(
        "rampa", premissas,
        {"nd": nd_efetivo, "acoes": c["acoes_diluidas"]}, c["moeda"])

    resultado_cenario = avaliar(c)["cenarios"]["base"]

    faltando = [
        chave for chave in saida_motor
        if chave not in resultado_cenario
        and chave not in _CHAVES_PROMOVIDAS_ROTA_RAMPA
    ]
    assert faltando == []


def test_rampa_carrega_rir_e_decomposicao_de_valor_da_fase_2():
    """As chaves centrais do achado: rir2_%/roic2_% (RiR e retorno marginal
    da fase 2 — a metodologia exige que todo cenário declare o triângulo
    RiR x retorno exatamente para que a taxa de reinvestimento nunca fique
    silenciosa) e vp_fase1/valor_fase2_no_ano_T (a decomposição de valor
    entre as duas fases — o ponto inteiro de uma composição bifásica)."""
    r = avaliar(carregar(FIXTURES / "caso_rampa.json"))["cenarios"]["base"]
    assert r["rir2_%"] == pytest.approx(49.977, abs=1e-3)
    assert r["roic2_%"] == pytest.approx(16.007, abs=1e-3)
    assert r["vp_fase1"] == pytest.approx(45.2592, abs=1e-3)
    assert r["valor_fase2_no_ano_T"] == pytest.approx(220.4887, abs=1e-3)


# --------------------------------------------------------------------------
# Fatia C, Task 4: bloco 'sotp' no resultado -- mesma disciplina aditiva de
# 'reversa'/'sensibilidades' (Fatia B, Task 5): só aparece quando o caso
# declara 'sotp', via sotp.compor_partes(caso, caso["sotp"]["cenario"]), sem
# filtrar nem reformatar o que compor_partes devolve. Um caso sem 'sotp'
# (toda fixture das fatias A/B, e a própria fixture de rampa da fatia C)
# não pode ganhar a chave nova -- byte a byte igual ao que produzia antes.
# --------------------------------------------------------------------------

def test_resultado_sem_sotp_nao_ganha_o_bloco():
    r = avaliar(carregar(FIXTURES / "caso_minimo_firm.json"))
    assert "sotp" not in r


def test_resultado_com_sotp_traz_partes_e_ponte_unica():
    r = avaliar(carregar(FIXTURES / "caso_sotp_segmento.json"))
    assert len(r["sotp"]["partes"]) == 2
    assert r["sotp"]["preco_acao"] > 0
    assert r["sotp"]["materialidade"]["sinal"] in ("+", "-", "0")


def test_sotp_e_deterministico(tmp_path):
    import filecmp
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    escrever(avaliar(carregar(FIXTURES / "caso_sotp_segmento.json")), a)
    escrever(avaliar(carregar(FIXTURES / "caso_sotp_segmento.json")), b)
    assert filecmp.cmp(a, b, shallow=False)


# --------------------------------------------------------------------------
# Correção do item 3: o risco desta correção não é a conta, é esquecer um
# chamador — exatamente a classe de bug que este repo já pagou com 'moeda'
# (um chamador que o esquecia fazia toda célula de grade carregar um alarme
# falso). Com 'rf', o sintoma seria pior: o cenário principal diz "ÂNCORA
# MACRO OK" enquanto uma célula de grade, um eixo de reversa ou uma parte
# de SOTP — que também rodam 'gordon' com gp > 0 — ainda dizem "PREMISSA
# NÃO ANCORADA", cada um lido de um `rodar()` esquecido. Este teste combina
# caso_reversa_firm.json (mercado+reversa+sensibilidades, gordon+gp=3.0 no
# cenário 'base') com o bloco 'sotp' de caso_sotp_segmento.json (a parte
# 'Serviços' também é gordon+gp=3.0) num caso só — os dois blocos já são
# testados isoladamente alhures; é o PRODUTO dos quatro (cenário, grades,
# reversa, sotp) que discrimina um caminho esquecido.
# --------------------------------------------------------------------------

def test_nenhum_caminho_perde_rf_cenarios_grades_reversa_sotp():
    caso = carregar(FIXTURES / "caso_reversa_firm.json")
    sotp = json.loads((FIXTURES / "caso_sotp_segmento.json").read_text(encoding="utf-8"))["sotp"]
    caso["sotp"] = sotp

    r = avaliar(caso)

    serializado = json.dumps(r, ensure_ascii=False)
    assert "PREMISSA NÃO ANCORADA" not in serializado
    # As 8 pernas gordon+gp>0 deste caso combinado (cenário base, os 4
    # eixos de reversa, as 2 grades de sensibilidade, a parte 'Serviços' do
    # sotp) — confirmado por sondagem direta, pré-correção, que são
    # exatamente estas 8 que hoje saem "PREMISSA NÃO ANCORADA".
    assert serializado.count("ÂNCORA MACRO OK") == 8


# --------------------------------------------------------------------------
# F5 (revisão final, fatia 4C): o teste acima só cobre a rota FIRM — todos os
# quatro casos que exercitam o threading do rf (`caso_minimo_firm.json` via
# `caso_reversa_firm.json`) rodam pela rota firm, tanto no cenário principal
# quanto nas grades/reversa/sotp. Achado da revisão: tirar `rf=rf` da rota
# equity ou da rota rampa (em `avaliar.py`, em `sensibilidades.py` ou em
# `sotp.py`) mantém os 135 testes do wrapper verdes — exatamente a classe de
# "chamador esquecido" que o teste acima já cobra uma vez, com uma rota a
# menos. Irmã do teste acima: mesma prova (ALERTA/ÂNCORA MACRO OK presente,
# PREMISSA NÃO ANCORADA ausente), cobrindo os quatro pontos que faltavam:
#
#   W1 (avaliar.py, cenário principal da rota rampa)
#   W2 (avaliar.py, cenário principal da rota equity)
#   W3 (sensibilidades.py, célula de grade da rota equity)
#   W4 (sotp.py, parte de SOTP na rota rampa)
#
# Dois casos bastam: um de rota equity (cenário + uma grade, cobre W2+W3) e
# um de rota rampa com um bloco sotp cuja parte também é rampa (cenário +
# parte, cobre W1+W4) — mesma disciplina do teste acima, "é o PRODUTO dos
# caminhos que discrimina um caminho esquecido", com o mínimo de casos que
# cobre os quatro pontos. `aviso_gp` (rampa) é uma chave BOOLEANA que
# `_monta_cenario_rampa`/`_compor_parte` repassam verbatim — não a mesma
# prosa Damodaran de firm/equity — por isso é checado por presença de
# chave, não por substring.
# --------------------------------------------------------------------------

def _caso_equity_rf_com_grade() -> dict:
    return {
        "companhia": "RF Equity Sintética S.A.",
        "moeda": "BRL-nominal",
        "data_analise": "2026-09-10",
        "rota": "equity",
        "metrica_base": {"tipo": "LL", "valor": 500.0, "fonte": "fixture sintética"},
        "acoes_diluidas": 100.0,
        "preco": {"valor": 40.0, "fonte": "fixture sintética", "data": "2026-09-10"},
        "mercado": {"rf": 5.0, "erp": 6.0},
        "cenarios": {
            "base": {
                "ancora": "consenso t+1",
                "triangulo": {"inputs": ["g", "roe"], "output": "rir"},
                "premissas": {
                    "g": 8.0, "roe": 18.0, "ke": 14.0, "n": 10,
                    "gde": 30.0, "nde": 20.0,
                    "tv": "gordon", "roe_tv": 20.0, "gp": 8.0,
                },
            },
        },
        "sensibilidades": {
            "cenario": "base",
            "grades_1d": [
                {"premissa": "n", "pontos": [8, 10],
                 "triangulo": {"inputs": ["g", "roe"], "output": "rir"}},
            ],
        },
    }


def _caso_rampa_rf_com_sotp() -> dict:
    premissas_rampa_gordon = {
        "receita0": 265.0, "ebitda0": 26.8, "da_parque": 6.8, "wk": 19.1,
        "kappa": 17.9364, "util": 65.0, "t_rampa": 5, "g2": 8.0,
        "wacc": 11.9, "tax": 35.0, "n": 10,
        "tv": "gordon", "roic_tv": 20.0, "gp": 8.0,
    }
    return {
        "companhia": "RF Rampa+SOTP Sintética S.A.",
        "moeda": "BRL-nominal",
        "data_analise": "2026-09-10",
        "rota": "rampa",
        "delimitador": "comissionamento datado no guidance de 4T25",
        "metrica_base": {"tipo": "EBITDA0", "valor": 26.8, "fonte": "fixture sintética"},
        "acoes_diluidas": 30.46,
        "preco": {"valor": 9.0, "fonte": "fixture sintética", "data": "2026-09-10"},
        "ponte": {"divida_bruta": 0.0, "caixa_e_equivalentes": 104.6,
                  "outros_ativos": 0.0, "outros_passivos": 0.0, "minoritarios": 0.0},
        "mercado": {"rf": 5.0, "erp": 6.0},
        "cenarios": {
            "base": {
                "ancora": "utilização divulgada de 65% no 3T25",
                "premissas": dict(premissas_rampa_gordon),
            },
        },
        "sotp": {
            "tipo": "segmento",
            "cenario": "base",
            "partes": [
                {
                    "nome": "Base instalada",
                    "rota": "rampa",
                    "delimitador": "comissionamento datado no guidance de 4T25",
                    "metrica_base": {"tipo": "EBITDA0", "valor": 26.8, "fonte": "fixture sintética"},
                    "ancora": "utilização divulgada de 65% no 3T25",
                    "premissas": dict(premissas_rampa_gordon),
                },
                {
                    "nome": "Expansão",
                    "rota": "firm",
                    "metrica_base": {"tipo": "EBITDA", "valor": 50.0, "fonte": "fixture sintética"},
                    "ancora": "capex aprovado, cronograma interno",
                    "triangulo": {"inputs": ["g", "roic"], "output": "rir"},
                    "premissas": {
                        "g": 7.0, "roic": 16.0, "wacc": 10.5, "n": 10,
                        "da": 12.0, "tax": 25.0, "tv": "convergencia",
                    },
                },
            ],
            "topo": {
                "custos_corporativos_vp": 0.0, "participacoes_nao_consolidadas": 0.0,
                "desconto_de_holding_pct": None, "razao_do_desconto": None,
            },
        },
    }


def test_nenhum_caminho_perde_rf_equity_rampa_grade_e_sotp_rampa():
    """Irmã de `test_nenhum_caminho_perde_rf_cenarios_grades_reversa_sotp` — cobre os quatro
    pontos que aquele teste (só rota firm) não alcança: W1/W2 (cenário principal das rotas
    rampa/equity, avaliar.py), W3 (célula de grade da rota equity, sensibilidades.py) e W4 (parte
    de SOTP na rota rampa, sotp.py)."""
    r_equity = avaliar(_caso_equity_rf_com_grade())
    serializado_equity = json.dumps(r_equity, ensure_ascii=False)
    assert "ALERTA (âncora macro" in serializado_equity  # W2: cenário principal, rota equity
    assert "PREMISSA NÃO ANCORADA" not in serializado_equity

    diagnosticos_da_grade = r_equity["sensibilidades"]["grades_1d"][0]["diagnosticos_unicos"]
    assert any(m.startswith("ALERTA (âncora macro") for m in diagnosticos_da_grade)  # W3
    assert not any(m.startswith("PREMISSA NÃO ANCORADA") for m in diagnosticos_da_grade)

    r_rampa = avaliar(_caso_rampa_rf_com_sotp())
    assert "aviso_gp" in r_rampa["cenarios"]["base"]  # W1: cenário principal, rota rampa

    partes_por_nome = {p["nome"]: p for p in r_rampa["sotp"]["partes"]}
    assert "aviso_gp" in partes_por_nome["Base instalada"]  # W4: parte de SOTP, rota rampa


# --------------------------------------------------------------------------
# Revisão final (task 3c), FIX 6d: `precificar_rampa` devolve `multiplo`,
# mas todo call site descartava (`_multiplo`) e `_monta_cenario_rampa`
# relia numa SEGUNDA leitura idêntica (`_exigir_valor(saida_motor,
# "EV/EBITDA0")`) do mesmo campo do motor -- duas leituras do mesmo número,
# confirmado morto por mutação. Escolha: usar o `multiplo` recebido como
# parâmetro em `_monta_cenario_rampa`, não redescobri-lo -- mantém a
# paridade de assinatura com `precificar_firm`/`precificar_equity` (as três
# irmãs devolvem `multiplo` e agora as três também o usam) e deixa exatamente
# UMA chamada a `_exigir_valor(saida, "EV/EBITDA0")` no módulo inteiro, dentro
# de `precificar_rampa` -- em vez de dropar o retorno, o que quebraria essa
# paridade documentada no próprio docstring de `precificar_rampa`.
# --------------------------------------------------------------------------

def test_monta_cenario_rampa_usa_o_multiplo_recebido_como_parametro():
    """Prova de fonte única: um `multiplo` passado DIFERENTE do que está em
    `saida_motor["EV/EBITDA0"]` aparece na saída -- confirmando que a função
    não re-deriva o campo do payload do motor."""
    from avaliar import _monta_cenario_rampa
    cenario = {"ancora": "x", "premissas": {"g2": 1.0}}
    saida_motor = {"EV/EBITDA0": 999.0, "EV": 1.0, "Equity": 1.0, "Preco_acao": 1.0}
    valor = {"EV": 1.0, "Equity": 1.0, "preco_acao": 10.0}
    resultado = _monta_cenario_rampa(cenario, saida_motor, valor, "algebra", 10.0, 6.378)
    assert resultado["multiplos"]["EV/EBITDA0"] == pytest.approx(6.378)


def test_rota_rampa_multiplo_continua_batendo_o_motor_no_pipeline_completo():
    """Ponta a ponta: com o motor de verdade (não mockado), o `multiplo`
    que passa a vir de `precificar_rampa` continua idêntico ao que o motor
    devolveu -- a mudança de fonte não muda nenhum número."""
    r = avaliar(carregar(FIXTURES / "caso_rampa.json"))
    assert r["cenarios"]["base"]["multiplos"]["EV/EBITDA0"] == pytest.approx(6.378, abs=1e-3)


# --------------------------------------------------------------------------
# Revisão final (task 3c), FIX 6e: colisão de ordenação no loop de repasse
# íntegro da rota rampa -- mesma guarda de `sotp._compor_parte` (ver o
# teste irmão em test_valuation_sotp.py). Nenhuma colisão existe hoje (o
# motor não emite nenhum campo autorado de `_monta_cenario_rampa`); este
# teste MANUFATURA uma via monkeypatch para provar que a guarda
# (`chave in resultado`) segura de verdade.
# --------------------------------------------------------------------------

def test_rampa_engine_key_colidindo_com_campo_autorado_nao_sobrescreve(monkeypatch):
    def _rodar_fake(rota, premissas, escala, moeda=None, subcomando=None, rf=None):
        return {
            "EV": 170.9304, "Equity": 100.0, "Preco_acao": 9.05,
            "EV/EBITDA0": 6.378,
            "ancora": "CLOBBERED-PELO-MOTOR",  # colisão manufaturada
        }

    monkeypatch.setattr("avaliar.rodar", _rodar_fake)
    c = carregar(FIXTURES / "caso_rampa.json")
    r = avaliar(c)
    assert r["cenarios"]["base"]["ancora"] == c["cenarios"]["base"]["ancora"]
    assert r["cenarios"]["base"]["ancora"] != "CLOBBERED-PELO-MOTOR"


# --------------------------------------------------------------------------
# Fatia 5F, Task 3 (D6 do plano docs/superpowers/plans/2026-09-15-v4-item5f-
# valuation.md): a conservação de capital (§11.1b), publicada por cenário na rota
# firm com EBITDA — a saída do motor íntegra, o ano-base declarado e a chave do
# alerta, por presença.
# --------------------------------------------------------------------------

sys.path.insert(0, str(RAIZ / "tests"))
from relatorio_apoio import caso_da_variante  # noqa: E402
from avaliar import _CHAVES_DA_CONSERVACAO, _conservacao_publicada  # noqa: E402


@pytest.mark.parametrize("variante,gap_pct,alerta", [
    ("conservacao_fecha", 0.0, False),
    ("conservacao_nao_fecha", -50.0, True),
])
def test_a_conservacao_de_capital_sai_publicada_com_a_chave_so_onde_o_motor_alerta(variante, gap_pct, alerta):
    """`caso_minimo_firm` tem encargos de 450: reposição 200 (20% de 1.000) e crescimento 250 (RiR 5/12
    sobre NOPAT 600). Capex 430 + ΔWC 20 fecha em zero; capex 300 dá gap de −50% — números conferidos
    rodando o motor. O bloco publicado é a saída dele, íntegra, mais `ano_base` e as chaves."""
    caso = caso_da_variante(variante)
    declarado = caso["conservacao_de_capital"]
    bloco = avaliar(caso)["cenarios"]["base"]["conservacao_capital"]
    do_motor = _motor_rodar(
        "firm", caso["cenarios"]["base"]["premissas"],
        {"ebitda": caso["metrica_base"]["valor"], "capex_total": declarado["capex_total"]["valor"],
         "dwc": declarado["dwc"]["valor"]},
        caso["moeda"])["conservacao_capital"]
    assert {campo: valor for campo, valor in bloco.items()
            if campo not in ("ano_base", "diagnosticos_chaves")} == do_motor
    assert bloco["gap_%"] == gap_pct
    assert ("ALERTA" in bloco) is alerta
    assert bloco["diagnosticos_chaves"] == (list(_CHAVES_DA_CONSERVACAO) if alerta else [])
    assert bloco["ano_base"] == declarado["capex_total"]["ano_base"]


def test_sem_o_bloco_nenhum_cenario_publica_a_conservacao_de_capital():
    assert all("conservacao_capital" not in cenario for cenario in _res_firm()["cenarios"].values())


@pytest.mark.parametrize("bloco_do_motor,nomeado", [
    ("NAO CHECAVEL — a identidade exige --capex-total, --dwc e --ebitda juntos", "conservação de capital"),
    ({"capital_consumido": 0.0, "encargo_reposicao_d_x_EBITDA": 200.0,
      "encargo_crescimento_RiR_x_NOPAT": 250.0, "gap": -450.0, "gap_%": None,
      "leitura": "identidade fecha dentro do limiar"}, "gap_%"),
], ids=["texto_no_lugar_do_bloco", "gap_nulo"])
def test_a_conservacao_que_o_motor_nao_fecha_em_numero_e_recusa_nomeada(bloco_do_motor, nomeado):
    """Armadilha 3 do plano: sem `--ebitda` o motor devolve TEXTO no lugar do bloco, e capital
    consumido nulo vira `gap_%` nulo — o wrapper recusa nomeando, nunca publica texto nem `null`."""
    with pytest.raises(MotorFalhou, match=nomeado):
        _conservacao_publicada({"conservacao_capital": bloco_do_motor},
                               caso_da_variante("conservacao_fecha")["conservacao_de_capital"])


# --------------------------------------------------------------------------
# Fatia 5G, Task 1 (D1 do plano docs/superpowers/plans/2026-09-15-v4-item5g-
# alternativas.md): o painel de escolhas metodológicas. O caso declara; o wrapper
# precifica a alternativa sobre o cenário da manchete e publica preço, impacto,
# materialidade e o alerta de coerência interna dos cenários.
# --------------------------------------------------------------------------

from avaliar import (  # noqa: E402
    DIRECOES_DO_EMPILHAMENTO, LIMIAR_DE_ESCOLHA_MATERIAL, _alternativa_do_caso, precificar_firm,
)


def _com_escolhas(fixture: str, escolhas: list) -> dict:
    caso = carregar(FIXTURES / fixture)
    caso["escolhas_metodologicas"] = escolhas
    return caso


def _preco_da_sobreposicao(caso: dict, nome_cenario: str, sobreposicoes: dict) -> float:
    """Oráculo do teste, montado aqui e não copiado do wrapper: a cópia do caso com as
    sobreposições aplicadas nos alvos que o gate admite — premissas do cenário,
    `metrica_base` e linhas da `ponte` —, precificada pela rota firm."""
    premissas = {**caso["cenarios"][nome_cenario]["premissas"],
                 **{alvo: valor for alvo, valor in sobreposicoes.items()
                    if alvo not in ("metrica_base", "ponte")}}
    metrica = {**caso["metrica_base"], **sobreposicoes.get("metrica_base", {})}
    nd_efetivo = _compor_ponte({**caso["ponte"], **sobreposicoes.get("ponte", {})})["nd_efetivo"]
    _saida, valor, _algebra, _multiplo = precificar_firm(
        premissas, metrica["tipo"], metrica["valor"], nd_efetivo,
        caso["acoes_diluidas"], caso["moeda"])
    return valor["preco_acao"]


def test_o_preco_da_alternativa_e_o_caso_da_manchete_com_as_sobreposicoes():
    """O oráculo é a cópia do caso com as sobreposições, precificada pela mesma função
    que precifica o cenário. E o impacto é esse preço contra o da manchete."""
    caso = caso_da_variante("escolhas")
    r = avaliar(caso)

    assert [escolha["chave"] for escolha in r["escolhas_metodologicas"]] == [
        "rentabilidade", "crescimento", "ano_de_capex_no_par_d_rir",
        "caixa_excedente_em_hibrida_financeira"]
    for publicada, declarada in zip(r["escolhas_metodologicas"], caso["escolhas_metodologicas"]):
        esperado = _preco_da_sobreposicao(
            caso, r["manchete"]["cenario"], declarada["sobreposicoes"])
        assert publicada["preco_alternativa"] == pytest.approx(esperado), declarada["chave"]
        assert publicada["impacto"] == pytest.approx(
            esperado / r["manchete"]["preco_acao"] - 1), declarada["chave"]
        assert publicada["sobreposicoes"] == declarada["sobreposicoes"]
        assert publicada["no_caso_base"] == declarada["no_caso_base"]
        assert publicada["gatilho_disparou"] == declarada.get("gatilho_disparou")


def test_a_materialidade_separa_os_dois_lados_do_limiar():
    """`caso_minimo_firm` vale R$ 61,91. ROIC 20% leva a R$ 69,72 (+12,6%, acima do
    limiar de 10%); g 8% leva a R$ 67,04 (+8,3%, abaixo). Números conferidos no motor."""
    escolhas = avaliar(caso_da_variante("escolhas"))["escolhas_metodologicas"]
    material, nao_material = escolhas[0], escolhas[1]
    assert material["preco_alternativa"] == pytest.approx(69.72, abs=0.01)
    assert abs(material["impacto"]) > LIMIAR_DE_ESCOLHA_MATERIAL and material["material"] is True
    assert nao_material["preco_alternativa"] == pytest.approx(67.04, abs=0.01)
    assert abs(nao_material["impacto"]) < LIMIAR_DE_ESCOLHA_MATERIAL and nao_material["material"] is False


def test_o_alerta_de_empilhamento_sai_com_duas_fora_da_central_na_mesma_direcao():
    """Duas escolhas com o caso-base FORA da posição central e impacto do mesmo sinal
    acendem o alerta, nomeando a direção e as chaves; uma só, ou uma alternativa ao lado
    de uma central, não acendem nada."""
    conservadora, otimista = DIRECOES_DO_EMPILHAMENTO
    duas_alternativas = [
        {"chave": "rentabilidade", "no_caso_base": "alternativa", "sobreposicoes": {"roic": 20.0}},
        {"chave": "crescimento", "no_caso_base": "alternativa", "sobreposicoes": {"g": 8.0}},
    ]
    r = avaliar(_com_escolhas("caso_minimo_firm.json", duas_alternativas))
    assert r["empilhamento"] == {"direcao": conservadora, "chaves": ["rentabilidade", "crescimento"]}

    uma_so = avaliar(_com_escolhas("caso_minimo_firm.json", duas_alternativas[:1]))
    assert uma_so["empilhamento"] is None

    uma_central = avaliar(_com_escolhas("caso_minimo_firm.json", [
        duas_alternativas[0], {**duas_alternativas[1], "no_caso_base": "central"}]))
    assert uma_central["empilhamento"] is None

    # Direções opostas não empilham: a que pesa mais é a que sai nomeada.
    direcoes_opostas = avaliar(_com_escolhas("caso_minimo_firm.json", duas_alternativas + [
        {"chave": "ano_de_capex_no_par_d_rir", "no_caso_base": "alternativa", "sobreposicoes": {"da": 24.0}}]))
    assert direcoes_opostas["empilhamento"]["direcao"] == conservadora
    assert otimista not in direcoes_opostas["empilhamento"]["chaves"]


def test_com_degrau_a_alternativa_e_precificada_com_degrau():
    """O preço publicado do cenário com degrau é o COM degrau; a alternativa passa pelo
    mesmo subcomando, sobre o vetor sobreposto — senão o impacto compararia o com-degrau
    contra o sem-degrau, e uma escolha sem efeito nenhum sairia material."""
    caso = _com_escolhas("caso_degrau.json", [
        {"chave": "alavanca_de_lucro", "no_caso_base": "central", "sobreposicoes": {"roe": 20.0}}])
    r = avaliar(caso)
    (escolha,) = r["escolhas_metodologicas"]
    cenario = r["cenarios"][r["manchete"]["cenario"]]
    assert escolha["preco_alternativa"] != pytest.approx(cenario["sem_degrau"]["valor"]["preco_acao"])
    assert escolha["impacto"] == pytest.approx(
        escolha["preco_alternativa"] / r["manchete"]["preco_acao"] - 1)


def test_sem_o_bloco_o_painel_sai_vazio_e_sem_alerta():
    r = _res_firm()
    assert r["escolhas_metodologicas"] == [] and r["empilhamento"] is None


# --------------------------------------------------------------------------
# Fatia 5G, Task 2 (D2/D3/D4 do plano docs/superpowers/plans/2026-09-15-v4-item5g-
# alternativas.md): o retorno exigido, o valor ponderado e o cross-check pela rota
# oposta. Os três oráculos são montados aqui, pelo motor ou pela aritmética da soma
# ponderada — nunca copiados do wrapper.
# --------------------------------------------------------------------------

from avaliar import precificar_equity  # noqa: E402
from caso import PREMISSA_DE_CUSTO_DE_CAPITAL_POR_ROTA, SOMA_DOS_PESOS  # noqa: E402


@pytest.mark.parametrize("fixture,taxa", [
    ("caso_minimo_firm.json", 14.0),
    ("caso_minimo_equity.json", 18.0),
])
def test_o_retorno_exigido_substitui_o_custo_de_capital_da_rota_uma_rota_por_vez(fixture, taxa):
    """O preço é o do cenário da manchete com a premissa de custo de capital da rota
    trocada pela taxa — WACC na rota firm, Ke na equity —, e nada mais do vetor muda."""
    caso = carregar(FIXTURES / fixture)
    caso["retorno_exigido"] = {"taxa": taxa}
    r = avaliar(caso)
    premissa = PREMISSA_DE_CUSTO_DE_CAPITAL_POR_ROTA[caso["rota"]]
    premissas = {**caso["cenarios"]["base"]["premissas"], premissa: taxa}
    metrica = caso["metrica_base"]
    if caso["rota"] == "firm":
        _saida, valor, _algebra, _multiplo = precificar_firm(
            premissas, metrica["tipo"], metrica["valor"], r["ponte"]["nd_efetivo"],
            caso["acoes_diluidas"], caso["moeda"])
    else:
        _saida, valor, _algebra, _multiplo = precificar_equity(
            premissas, metrica["valor"], caso["acoes_diluidas"], caso["moeda"])
    assert r["retorno_exigido"] == {
        "taxa": taxa, "premissa_substituida": premissa,
        "preco_acao": pytest.approx(valor["preco_acao"])}
    # Exigir mais retorno do que o caso descontava vale menos: o sinal da leitura.
    assert (valor["preco_acao"] < r["manchete"]["preco_acao"]) is (
        taxa > caso["cenarios"]["base"]["premissas"][premissa])


def test_o_valor_ponderado_e_a_soma_de_peso_x_preco_dos_cenarios():
    caso = caso_da_variante("alternativas")
    r = avaliar(caso)
    pesos = caso["pesos_de_probabilidade"]
    esperado = sum(peso / SOMA_DOS_PESOS * r["cenarios"][nome]["valor"]["preco_acao"]
                   for nome, peso in pesos.items())
    assert r["valor_ponderado"]["valor"] == pytest.approx(esperado)
    assert r["valor_ponderado"]["pesos"] == pesos
    # Entre o menor e o maior preço, nunca fora deles — e nunca igual à manchete aqui.
    precos = [cenario["valor"]["preco_acao"] for cenario in r["cenarios"].values()]
    assert min(precos) < r["valor_ponderado"]["valor"] < max(precos)


def test_o_cross_check_precifica_o_vetor_da_rota_oposta_e_a_diferenca_sai_com_o_sinal_certo():
    caso = caso_da_variante("alternativas")
    r = avaliar(caso)
    bloco = caso["cross_check"]
    _saida, valor, _algebra, _multiplo = precificar_equity(
        bloco["premissas"], bloco["metrica_base"]["valor"], caso["acoes_diluidas"], caso["moeda"])
    assert r["cross_check"]["rota"] == "equity" != caso["rota"]
    assert r["cross_check"]["preco_acao"] == pytest.approx(valor["preco_acao"])
    assert r["cross_check"]["diferenca_vs_manchete"] == pytest.approx(
        valor["preco_acao"] / r["manchete"]["preco_acao"] - 1)
    # O segundo método vale menos que a manchete nesta variante: diferença negativa.
    assert valor["preco_acao"] < r["manchete"]["preco_acao"]
    assert r["cross_check"]["diferenca_vs_manchete"] < 0


def test_sem_os_blocos_as_tres_leituras_saem_nulas():
    r = _res_firm()
    assert r["retorno_exigido"] is None
    assert r["valor_ponderado"] is None
    assert r["cross_check"] is None


# --------------------------------------------------------------------------
# Fatia 5G, Task 1b: as sobreposições alcançam os alvos que as dez escolhas de fato
# movem — a base do lucro move a métrica, o caixa em híbrida financeira move uma linha
# da ponte, e a hipótese terminal troca a convenção. Um alvo por teste, com o oráculo
# montado a partir da cópia do caso.
# --------------------------------------------------------------------------

@pytest.mark.parametrize("chave,sobreposicoes,confere", [
    pytest.param(
        "base_do_lucro", {"metrica_base": {"valor": 1100.0}},
        lambda caso, alt: alt["metrica_base"] == {**caso["metrica_base"], "valor": 1100.0},
        id="metrica_base_valor"),
    pytest.param(
        "caixa_excedente_em_hibrida_financeira", {"ponte": {"caixa_e_equivalentes": 0.0}},
        lambda caso, alt: alt["ponte"] == {**caso["ponte"], "caixa_e_equivalentes": 0.0},
        id="linha_da_ponte"),
    pytest.param(
        "hipotese_terminal", {"tv": "book"},
        lambda caso, alt: alt["cenarios"]["base"]["premissas"]["tv"] == "book",
        id="convencao_terminal"),
])
def test_a_sobreposicao_alcanca_cada_alvo_do_caso_e_o_preco_bate_com_a_copia(chave, sobreposicoes, confere):
    """O preço alternativo é o da CÓPIA do caso com a sobreposição aplicada naquele
    alvo, e o caso original nunca é mutado. `metrica_base.valor` 1.100 contra 1.000 sobe
    o preço; caixa a zero engrossa a dívida líquida em 300 e o derruba; a convenção
    'book' (contra 'gordon' do caso) o derruba de R$ 61,91 para R$ 55,31 — números
    conferidos no motor."""
    caso = carregar(FIXTURES / "caso_minimo_firm.json")
    caso["escolhas_metodologicas"] = [
        {"chave": chave, "no_caso_base": "central", "sobreposicoes": sobreposicoes}]
    original = json.loads(json.dumps(caso))
    r = avaliar(caso)
    (publicada,) = r["escolhas_metodologicas"]

    assert publicada["preco_alternativa"] == pytest.approx(
        _preco_da_sobreposicao(caso, "base", sobreposicoes))
    assert publicada["preco_alternativa"] != pytest.approx(r["manchete"]["preco_acao"])
    assert caso == original, "avaliar() mutou o caso ao compor a alternativa"

    # A cópia composta pelo wrapper aplica a sobreposição no alvo certo, e só nele.
    alternativo, _premissas, _nd = _alternativa_do_caso(
        caso, "base", sobreposicoes, r["ponte"]["nd_efetivo"])
    assert confere(caso, alternativo)


def test_a_convencao_terminal_alternativa_bate_com_o_preco_do_motor_para_ela():
    """Oráculo direto: 'book' em `caso_minimo_firm` vale R$ 55,31 (o mesmo número que
    `tests/test_valuation_contrato.py` já prende para o alias 'ic')."""
    caso = carregar(FIXTURES / "caso_minimo_firm.json")
    caso["escolhas_metodologicas"] = [
        {"chave": "hipotese_terminal", "no_caso_base": "central", "sobreposicoes": {"tv": "book"}}]
    (publicada,) = avaliar(caso)["escolhas_metodologicas"]
    assert publicada["preco_alternativa"] == pytest.approx(55.31, abs=0.01)
    assert publicada["material"] is True  # -10,66%, acima do limiar
