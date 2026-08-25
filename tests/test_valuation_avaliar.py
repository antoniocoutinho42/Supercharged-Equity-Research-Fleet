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
    def _saida_com_multiplo_nulo(rota, premissas, escala, moeda=None):
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
