"""Contrato `entrega/1`, placeholders e QC de três níveis (fatia 5A, item 5,
Task 3).

Ver docs/superpowers/plans/2026-09-11-v4-item5a-contratos-builder.md, seção
"Task 3", para a lista de cenários. Cada teste discrimina um contrato: o
CLI (`builder.py`, via subprocess — exit code + `qc.json` + presença/
ausência de `relatorio.html`) ou uma função pura (`placeholders.formatar`,
`entrega.sha256_canonico`, `qc.NIVEIS`).

Raízes de execução vêm de `tests/relatorio_apoio.py`, que roda `avaliar()`
de verdade sobre uma fixture de caso — nenhum `resultados.json` é forjado
à mão neste arquivo.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
SCRIPTS = RAIZ / "skills" / "er-relatorio" / "scripts"
BUILDER = SCRIPTS / "builder.py"

sys.path.insert(0, str(SCRIPTS))
import entrega  # noqa: E402
import placeholders  # noqa: E402
import qc  # noqa: E402

sys.path.insert(0, str(RAIZ / "tests"))
import relatorio_apoio as apoio  # noqa: E402

ENV_UTF8 = {**os.environ, "PYTHONUTF8": "1", "PYTHONDONTWRITEBYTECODE": "1", "PYTHONIOENCODING": "utf-8"}

CATALOGO = json.loads(
    (RAIZ / "skills" / "er-valuation" / "assets" / "catalogo_apresentacao.json").read_text(encoding="utf-8"))


def rodar_builder(raiz: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(BUILDER), str(raiz)],
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace", env=ENV_UTF8, timeout=60)


def ler_qc(raiz: Path) -> dict:
    return json.loads((raiz / "qc.json").read_text(encoding="utf-8"))


def codigos_de(qc_json: dict) -> set:
    return {a["codigo"] for a in qc_json["achados"]}


# --------------------------------------------------------------------------
# Formatação pt-BR (placeholders.formatar) — unidade, sem CLI.
# --------------------------------------------------------------------------

@pytest.mark.parametrize("valor,formato,esperado", [
    (6690.59, "num2", "6.690,59"),
    (0.12563, "pct1", "12,6%"),
    (6.6906, "x2", "6,69x"),
    (-1234.5, "num2", "-1.234,50"),
    (0.0, "num2", "0,00"),
])
def test_formatacao_pt_br(valor, formato, esperado):
    assert placeholders.formatar(valor, formato, "pt-BR") == esperado


def test_formatacao_moeda_usa_simbolo_do_dicionario():
    assert placeholders.formatar(61.91, "moeda", "pt-BR", "BRL-nominal") == "R$ 61,91"


def test_formato_desconhecido_recusa_com_sugestao():
    with pytest.raises(placeholders.FormatoInvalido, match="num5"):
        placeholders.formatar(1.0, "num5", "pt-BR")


# --------------------------------------------------------------------------
# sha256_canonico (A2) — duplicação deliberada da receita de avaliar.py;
# teste cruzado contra um resultados.json de verdade.
# --------------------------------------------------------------------------

def test_sha256_canonico_ignora_ordem_de_chaves():
    assert entrega.sha256_canonico({"b": 2, "a": 1}) == entrega.sha256_canonico({"a": 1, "b": 2})


def test_sha256_canonico_bate_com_origem_de_resultados_real():
    """A2: a canonicalização de entrega.py tem de ser A MESMA que
    avaliar.py já usa em resultados.origem.caso_sha256 — teste cruzado,
    não duas implementações que por acaso convergem."""
    entrega_dict = apoio.montar_entrega("caso_reversa_firm.json")
    assert (entrega.sha256_canonico(entrega_dict["caso"])
            == entrega_dict["resultados"]["origem"]["caso_sha256"])


def test_niveis_de_qc():
    assert qc.NIVEIS == ("HARD_FAIL", "REQUIRED_DISCLOSURE", "QUALITY_WARNING")


# --------------------------------------------------------------------------
# CLI: caminho feliz.
# --------------------------------------------------------------------------

def test_emite_para_entrega_valida(tmp_path):
    entrega_dict = apoio.montar_entrega("caso_reversa_firm.json")
    raiz = tmp_path / "valida"
    apoio.escrever_raiz(raiz, entrega_dict)

    resultado = rodar_builder(raiz)

    assert resultado.returncode == 0, resultado.stdout + resultado.stderr
    assert (raiz / "relatorio.html").exists()
    qc_json = ler_qc(raiz)
    assert qc_json["achados"] == []
    html = (raiz / "relatorio.html").read_text(encoding="utf-8")
    assert "R$ 61,91" in html


def test_livre_com_digito_nao_dispara_numero_sem_provenencia(tmp_path):
    texto = ("Fundada em {{livre:2005}}, entrega valor justo de "
             "{{resultados:manchete.preco_acao|moeda}}.")
    entrega_dict = apoio.montar_entrega("caso_reversa_firm.json", texto_conclusao=texto)
    raiz = tmp_path / "livre_ok"
    apoio.escrever_raiz(raiz, entrega_dict)

    resultado = rodar_builder(raiz)

    assert resultado.returncode == 0, resultado.stdout + resultado.stderr
    assert ler_qc(raiz)["achados"] == []


def test_saida_e_deterministica(tmp_path):
    entrega_dict = apoio.montar_entrega("caso_reversa_firm.json")
    raiz1, raiz2 = tmp_path / "det1", tmp_path / "det2"
    apoio.escrever_raiz(raiz1, entrega_dict)
    apoio.escrever_raiz(raiz2, entrega_dict)

    r1, r2 = rodar_builder(raiz1), rodar_builder(raiz2)

    assert r1.returncode == r2.returncode == 0
    assert (raiz1 / "qc.json").read_bytes() == (raiz2 / "qc.json").read_bytes()
    assert (raiz1 / "relatorio.html").read_bytes() == (raiz2 / "relatorio.html").read_bytes()


# --------------------------------------------------------------------------
# CLI: HARD FAIL (código 2) — QC achou algo, nenhum relatorio.html sai.
# --------------------------------------------------------------------------

def test_numero_sem_provenencia_falha_no_caso_que_deve_falhar(tmp_path):
    """O 'must-fail case' da §13: número material de valuation na prosa
    sem placeholder nenhum."""
    texto = ("Valor justo de {{resultados:manchete.preco_acao|moeda}} por ação, "
             "acima dos R$ 50 negociados ontem.")
    entrega_dict = apoio.montar_entrega("caso_reversa_firm.json", texto_conclusao=texto)
    raiz = tmp_path / "numero_solto"
    apoio.escrever_raiz(raiz, entrega_dict)

    resultado = rodar_builder(raiz)

    assert resultado.returncode == 2, resultado.stdout + resultado.stderr
    assert not (raiz / "relatorio.html").exists()
    qc_json = ler_qc(raiz)
    achado = next(a for a in qc_json["achados"] if a["codigo"] == "numero_sem_proveniencia")
    assert achado["nivel"] == "HARD_FAIL"
    assert achado["onde"] == "analise.conclusao.texto"


def test_placeholder_nao_resolvido_falha(tmp_path):
    texto = "Valor justo de {{resultados:manchete.caminho_que_nao_existe|num2}} por ação."
    entrega_dict = apoio.montar_entrega("caso_reversa_firm.json", texto_conclusao=texto)
    raiz = tmp_path / "placeholder_ruim"
    apoio.escrever_raiz(raiz, entrega_dict)

    resultado = rodar_builder(raiz)

    assert resultado.returncode == 2, resultado.stdout + resultado.stderr
    assert not (raiz / "relatorio.html").exists()
    codigos = codigos_de(ler_qc(raiz))
    assert "placeholder_nao_resolvido" in codigos
    assert "numero_sem_proveniencia" not in codigos


# --------------------------------------------------------------------------
# B1 (achado F1, onda de correção da revisão final): só placeholder
# RECONHECIDO é descontado antes da busca de dígito solto -- qualquer outro
# '{{...}}' é HARD FAIL 'placeholder_malformado', e o dígito dentro dele
# conta para 'numero_sem_proveniencia' também (nenhuma imunidade).
# --------------------------------------------------------------------------

def test_bloco_duplo_chave_sem_namespace_e_malformado_e_digito_conta(tmp_path):
    """VERIFICADO pela revisão: '{{R$ 99,99}}' passava com rc 0 (o padrão
    de desconto de qc.py era só '\\{\\{.*?\\}\\}', sem exigir namespace/
    formato -- descontava ISSO também, escondendo o dígito da busca)."""
    texto = "Valor justo de {{R$ 99,99}} por ação."
    entrega_dict = apoio.montar_entrega("caso_reversa_firm.json", texto_conclusao=texto)
    raiz = tmp_path / "placeholder_sem_namespace"
    apoio.escrever_raiz(raiz, entrega_dict)

    resultado = rodar_builder(raiz)

    assert resultado.returncode == 2, resultado.stdout + resultado.stderr
    assert not (raiz / "relatorio.html").exists()
    codigos = codigos_de(ler_qc(raiz))
    assert "placeholder_malformado" in codigos
    assert "numero_sem_proveniencia" in codigos
    achado = next(a for a in ler_qc(raiz)["achados"] if a["codigo"] == "placeholder_malformado")
    assert achado["params"]["trecho"] == "{{R$ 99,99}}"


def test_namespace_no_singular_e_malformado(tmp_path):
    """'resultado:' (singular) não é 'resultados'/'caso'/'livre' -- nunca
    reconhecido por `placeholders.resolver`, então ficava literal na tela
    com rc 0 antes desta correção (VERIFICADO pela revisão)."""
    texto = "Valor justo de {{resultado:manchete.preco_acao|moeda}} por ação."
    entrega_dict = apoio.montar_entrega("caso_reversa_firm.json", texto_conclusao=texto)
    raiz = tmp_path / "namespace_singular"
    apoio.escrever_raiz(raiz, entrega_dict)

    resultado = rodar_builder(raiz)

    assert resultado.returncode == 2, resultado.stdout + resultado.stderr
    assert not (raiz / "relatorio.html").exists()
    assert "placeholder_malformado" in codigos_de(ler_qc(raiz))


def test_namespace_capitalizado_e_malformado(tmp_path):
    """'Resultados:' (maiúscula) -- mesma classe de fuga que o singular,
    caso diferente (VERIFICADO pela revisão)."""
    texto = "Valor justo de {{Resultados:manchete.preco_acao|moeda}} por ação."
    entrega_dict = apoio.montar_entrega("caso_reversa_firm.json", texto_conclusao=texto)
    raiz = tmp_path / "namespace_capitalizado"
    apoio.escrever_raiz(raiz, entrega_dict)

    resultado = rodar_builder(raiz)

    assert resultado.returncode == 2, resultado.stdout + resultado.stderr
    assert not (raiz / "relatorio.html").exists()
    assert "placeholder_malformado" in codigos_de(ler_qc(raiz))


def test_placeholder_quebrado_por_quebra_de_linha_agora_resolve(tmp_path):
    """Um placeholder válido partido por uma quebra de linha também ficava
    literal na tela com rc 0 antes desta correção (nem `placeholders.
    resolver` nem o desconto de qc.py usavam DOTALL). A correção do B1
    (DOTALL em `placeholders._PADRAO_PLACEHOLDER`, a única fonte de verdade
    de "placeholder reconhecido") faz este caso ser corretamente
    RECONHECIDO E RESOLVIDO -- não mais um '{{...}}' cru na tela, e não um
    'placeholder_malformado' (a forma É válida, só quebrada em duas linhas)."""
    texto = "Valor justo de {{resultados:\nmanchete.preco_acao|moeda}} por ação."
    entrega_dict = apoio.montar_entrega("caso_reversa_firm.json", texto_conclusao=texto)
    raiz = tmp_path / "placeholder_multilinha"
    apoio.escrever_raiz(raiz, entrega_dict)

    resultado = rodar_builder(raiz)

    assert resultado.returncode == 0, resultado.stdout + resultado.stderr
    qc_json = ler_qc(raiz)
    assert qc_json["achados"] == []
    html = (raiz / "relatorio.html").read_text(encoding="utf-8")
    assert "{{" not in html and "}}" not in html
    assert "R$ 61,91" in html


def test_numero_solto_de_controle_continua_falhando(tmp_path):
    """Controle da revisão: um dígito solto de verdade (sem chaves nenhuma)
    continua HARD FAIL -- a correção do B1 não afrouxou a regra original."""
    texto = "Valor justo acima dos R$ 50 negociados ontem."
    entrega_dict = apoio.montar_entrega("caso_reversa_firm.json", texto_conclusao=texto)
    raiz = tmp_path / "numero_solto_controle"
    apoio.escrever_raiz(raiz, entrega_dict)

    resultado = rodar_builder(raiz)

    assert resultado.returncode == 2, resultado.stdout + resultado.stderr
    assert "numero_sem_proveniencia" in codigos_de(ler_qc(raiz))


# --------------------------------------------------------------------------
# B2 (achado F2): o cabeçalho lê `manchete.convencao_terminal` (já
# canônico), nunca `caso...premissas.tv` cru -- um alias legado ('spread'/
# 'ic') passa pelo gate e pelo wrapper e tem de emitir normalmente.
# --------------------------------------------------------------------------

def test_alias_legado_de_tv_emite_com_rotulo_canonico(tmp_path):
    """VERIFICADO pela revisão: com o relatório lendo `caso...premissas.tv`
    cru, 'tv: spread' (alias de 'gordon' em `caso.TV_CANON`) passava a
    integração inteira e só quebrava no builder do relatório
    (RotuloDoCatalogoAusente: catálogo sem rótulo para a opção 'spread')."""
    def _usar_alias_spread(caso):
        caso["cenarios"]["base"]["premissas"]["tv"] = "spread"

    entrega_dict = apoio.montar_entrega("caso_reversa_firm.json", mutar_caso=_usar_alias_spread)
    assert entrega_dict["caso"]["cenarios"]["base"]["premissas"]["tv"] == "spread"
    assert entrega_dict["resultados"]["manchete"]["convencao_terminal"] == "gordon"
    raiz = tmp_path / "alias_tv"
    apoio.escrever_raiz(raiz, entrega_dict)

    resultado = rodar_builder(raiz)

    assert resultado.returncode == 0, resultado.stdout + resultado.stderr
    assert ler_qc(raiz)["achados"] == []
    html = (raiz / "relatorio.html").read_text(encoding="utf-8")
    assert CATALOGO["convencoes_terminais"]["gordon"]["pt-BR"] in html
    assert "spread" not in html


# --------------------------------------------------------------------------
# B3/B4 (regras invioláveis 2 e 6, achado F3): nada de uma rodada anterior
# sobra na raiz depois de uma recusa nesta MESMA raiz.
# --------------------------------------------------------------------------

def test_recusa_na_mesma_raiz_nao_deixa_relatorio_de_rodada_anterior(tmp_path):
    """VERIFICADO pela revisão: rodada 1 boa (rc 0, relatorio.html+qc.json);
    rodada 2, MESMA raiz, com um HARD FAIL -> antes desta correção, rc 2
    escrevia um qc.json novo mas deixava o relatorio.html da rodada 1 no
    lugar. Uma rodada 3, MESMA raiz, com entrega.json inválido (rc 1) tem
    de deixar a raiz completamente limpa (nem relatorio.html, nem qc.json)."""
    raiz = tmp_path / "raiz_reusada"

    entrega_boa = apoio.montar_entrega("caso_reversa_firm.json")
    apoio.escrever_raiz(raiz, entrega_boa)
    r1 = rodar_builder(raiz)
    assert r1.returncode == 0, r1.stdout + r1.stderr
    assert (raiz / "relatorio.html").exists()
    conteudo_rodada_1 = (raiz / "relatorio.html").read_bytes()

    texto_ruim = "Valor justo acima dos R$ 50 negociados ontem."
    entrega_ruim = apoio.montar_entrega("caso_reversa_firm.json", texto_conclusao=texto_ruim)
    apoio.escrever_raiz(raiz, entrega_ruim)
    r2 = rodar_builder(raiz)
    assert r2.returncode == 2, r2.stdout + r2.stderr
    assert not (raiz / "relatorio.html").exists(), "relatorio.html da rodada 1 sobrou depois do HARD FAIL"
    assert ler_qc(raiz)["achados"], "qc.json da rodada 2 tem de descrever a rodada 2"

    (raiz / "entrega.json").write_text("{ isto não é json", encoding="utf-8")
    r3 = rodar_builder(raiz)
    assert r3.returncode == 1, r3.stdout + r3.stderr
    assert not (raiz / "relatorio.html").exists()
    assert not (raiz / "qc.json").exists(), "qc.json da rodada 2 sobrou depois da recusa código 1"
    del conteudo_rodada_1  # só provado que NÃO sobrevive; não há mais o que comparar


# --------------------------------------------------------------------------
# B7 (achado F6): identidade do ticker entre `caso` e `execucao`.
# --------------------------------------------------------------------------

def test_ticker_da_execucao_diferente_do_caso_falha(tmp_path):
    """VERIFICADO pela revisão: `execucao.ticker='PETR4'` sobre caso/
    resultados de outra empresa emitia rc 0, título "Sintética S.A.
    (PETR4)" -- o título nomeava uma empresa diferente da que o valuation
    avaliou."""
    entrega_dict = apoio.montar_entrega("caso_reversa_firm.json", ticker="PETR4")
    entrega_dict["caso"]["ticker"] = "SINT3"
    raiz = tmp_path / "ticker_divergente"
    apoio.escrever_raiz(raiz, entrega_dict)

    resultado = rodar_builder(raiz)

    assert resultado.returncode == 1, resultado.stdout + resultado.stderr
    assert not (raiz / "qc.json").exists()
    assert not (raiz / "relatorio.html").exists()
    assert "PETR4" in resultado.stderr
    assert "SINT3" in resultado.stderr


def test_ticker_da_execucao_igual_ao_caso_emite(tmp_path):
    """Controle: quando os dois batem (o caso normal, sem mutação), nada
    muda -- a checagem de identidade não é falso positivo no caminho feliz."""
    entrega_dict = apoio.montar_entrega("caso_reversa_firm.json")
    raiz = tmp_path / "ticker_igual"
    apoio.escrever_raiz(raiz, entrega_dict)

    resultado = rodar_builder(raiz)

    assert resultado.returncode == 0, resultado.stdout + resultado.stderr


def test_resultados_de_outro_caso_falha(tmp_path):
    entrega_dict = apoio.montar_entrega("caso_reversa_firm.json")
    entrega_dict["resultados"] = apoio.resultados_de("caso_minimo_firm.json")
    raiz = tmp_path / "resultados_trocados"
    apoio.escrever_raiz(raiz, entrega_dict)

    resultado = rodar_builder(raiz)

    assert resultado.returncode == 2, resultado.stdout + resultado.stderr
    assert not (raiz / "relatorio.html").exists()
    achado = next(a for a in ler_qc(raiz)["achados"]
                  if a["codigo"] == "resultados_nao_correspondem_ao_caso")
    assert achado["nivel"] == "HARD_FAIL"


def test_null_em_diagnosticos_chaves_falha(tmp_path):
    entrega_dict = apoio.montar_entrega("caso_reversa_firm.json")
    entrega_dict["resultados"]["cenarios"]["base"]["diagnosticos_chaves"][0] = None
    raiz = tmp_path / "diagnostico_sem_chave"
    apoio.escrever_raiz(raiz, entrega_dict)

    resultado = rodar_builder(raiz)

    assert resultado.returncode == 2, resultado.stdout + resultado.stderr
    assert not (raiz / "relatorio.html").exists()
    achado = next(a for a in ler_qc(raiz)["achados"] if a["codigo"] == "diagnostico_sem_chave")
    assert achado["nivel"] == "HARD_FAIL"
    assert achado["onde"] == "resultados.cenarios.base.diagnosticos_chaves.0"


# --------------------------------------------------------------------------
# B9 (achado S1 generalizado): presença e paralelismo de `diagnosticos_chaves`
# em TODO `diagnosticos` de `resultados.json`, não só `cenarios`/grades.
# --------------------------------------------------------------------------

def test_sotp_sem_diagnosticos_chaves_falha(tmp_path):
    """VERIFICADO pela revisão (achado S1): partes de SOTP publicavam
    'diagnosticos' sem 'diagnosticos_chaves' e o QC não reclamava (só
    olhava `null` DENTRO de uma lista que já existisse). 'Industrial' é a
    primeira parte de `caso_sotp_segmento.json`, rota firm (publica
    'diagnosticos')."""
    entrega_dict = apoio.montar_entrega("caso_sotp_segmento.json")
    parte = entrega_dict["resultados"]["sotp"]["partes"][0]
    assert isinstance(parte.get("diagnosticos"), list) and parte["diagnosticos"]
    del parte["diagnosticos_chaves"]
    raiz = tmp_path / "sotp_sem_chaves"
    apoio.escrever_raiz(raiz, entrega_dict)

    resultado = rodar_builder(raiz)

    assert resultado.returncode == 2, resultado.stdout + resultado.stderr
    assert not (raiz / "relatorio.html").exists()
    achado = next(a for a in ler_qc(raiz)["achados"] if a["codigo"] == "diagnostico_sem_chave")
    assert achado["onde"] == "resultados.sotp.partes.0.diagnosticos_chaves"


def test_sotp_com_diagnosticos_chaves_mais_curta_falha(tmp_path):
    """Paralelismo: as duas listas existem, mas com comprimentos diferentes
    -- o achado antigo (só `null` dentro de uma lista já existente) também
    não cobria este caso."""
    entrega_dict = apoio.montar_entrega("caso_sotp_segmento.json")
    parte = entrega_dict["resultados"]["sotp"]["partes"][0]
    assert len(parte["diagnosticos_chaves"]) == len(parte["diagnosticos"]) >= 2
    parte["diagnosticos_chaves"].pop()
    raiz = tmp_path / "sotp_chaves_curta"
    apoio.escrever_raiz(raiz, entrega_dict)

    resultado = rodar_builder(raiz)

    assert resultado.returncode == 2, resultado.stdout + resultado.stderr
    codigos = codigos_de(ler_qc(raiz))
    assert "diagnostico_sem_chave" in codigos


def test_reversa_teto_do_crescimento_sem_diagnosticos_chaves_falha(tmp_path):
    """`reversa.teto_do_crescimento_gratuito` (A3) é o segundo lugar, fora de
    `cenarios`/SOTP, onde `diagnosticos` aparece -- não estava na lista de
    achados da revisão (só verificou SOTP), mas a checagem genérica de B9
    (varredura recursiva) cobre qualquer lugar, sem precisar conhecer este
    especificamente. Sintetizado aqui (o gatilho real -- rentabilidade ou
    crescimento sem raiz -- não dispara em nenhuma fixture existente; a
    forma é a mesma que `reversa.reverter` de fato produz, ver
    `skills/er-valuation/scripts/reversa.py`)."""
    entrega_dict = apoio.montar_entrega("caso_reversa_firm.json")
    entrega_dict["resultados"]["reversa"]["teto_do_crescimento_gratuito"] = {
        "multiplo": 6.5,
        "premissas_alteradas": {"tv": "gordon"},
        "leitura": "teto sintético para teste",
        "diagnosticos": ["mensagem sintética 1", "mensagem sintética 2"],
        "diagnosticos_chaves": ["firm_rir"],  # comprimento errado de propósito
    }
    raiz = tmp_path / "reversa_teto_chaves_curta"
    apoio.escrever_raiz(raiz, entrega_dict)

    resultado = rodar_builder(raiz)

    assert resultado.returncode == 2, resultado.stdout + resultado.stderr
    achado = next(a for a in ler_qc(raiz)["achados"] if a["codigo"] == "diagnostico_sem_chave")
    assert achado["onde"] == "resultados.reversa.teto_do_crescimento_gratuito.diagnosticos_chaves"


# --------------------------------------------------------------------------
# B10 (achado S2): degrau sem 'divergencia_de_base_%' numérico é HARD FAIL,
# não mais um `continue` silencioso.
# --------------------------------------------------------------------------

def test_degrau_sem_divergencia_de_base_falha(tmp_path):
    entrega_dict = apoio.montar_entrega("caso_degrau.json")
    del entrega_dict["resultados"]["cenarios"]["base"]["degrau"]["divergencia_de_base_%"]
    raiz = tmp_path / "degrau_sem_campo"
    apoio.escrever_raiz(raiz, entrega_dict)

    resultado = rodar_builder(raiz)

    assert resultado.returncode == 2, resultado.stdout + resultado.stderr
    achado = next(a for a in ler_qc(raiz)["achados"] if a["codigo"] == "degrau_sem_divergencia_de_base")
    assert achado["nivel"] == "HARD_FAIL"
    assert achado["params"]["cenario"] == "base"


# --------------------------------------------------------------------------
# B11 (achado S3): formato do placeholder tem de casar com a unidade.
# --------------------------------------------------------------------------

def test_formato_pct_em_premissa_pp_falha(tmp_path):
    """VERIFICADO pela revisão: '{{caso:cenarios.base.premissas.wacc|pct1}}'
    multiplicava por 100 um valor já em pontos percentuais -- "1.000,0%"
    para um WACC de 10 (dez pontos percentuais), rc 0."""
    texto = "WACC de {{caso:cenarios.base.premissas.wacc|pct1}} no cenário-base."
    entrega_dict = apoio.montar_entrega("caso_reversa_firm.json", texto_conclusao=texto)
    raiz = tmp_path / "formato_pct_em_pp"
    apoio.escrever_raiz(raiz, entrega_dict)

    resultado = rodar_builder(raiz)

    assert resultado.returncode == 2, resultado.stdout + resultado.stderr
    achado = next(a for a in ler_qc(raiz)["achados"] if a["codigo"] == "formato_incompativel_com_unidade")
    assert achado["params"]["unidade"] == "pp"
    assert achado["params"]["formato"] == "pct1"


def test_formato_pp_em_premissa_pp_emite(tmp_path):
    """Controle: o formato correto ('pp1') para a mesma premissa emite
    normalmente -- a checagem não é falso positivo no caminho feliz."""
    texto = "WACC de {{caso:cenarios.base.premissas.wacc|pp1}} no cenário-base."
    entrega_dict = apoio.montar_entrega("caso_reversa_firm.json", texto_conclusao=texto)
    raiz = tmp_path / "formato_pp_ok"
    apoio.escrever_raiz(raiz, entrega_dict)

    resultado = rodar_builder(raiz)

    assert resultado.returncode == 0, resultado.stdout + resultado.stderr
    assert ler_qc(raiz)["achados"] == []


def test_formato_num_em_resultados_percentual_falha(tmp_path):
    """Heurística pelo nome do caminho de `resultados`: um caminho que
    termina em '_%' só aceita formato 'pp*'."""
    texto = ("Divergência de base de "
             "{{resultados:cenarios.base.degrau.divergencia_de_base_%|num1}} no degrau.")
    entrega_dict = apoio.montar_entrega("caso_degrau.json", texto_conclusao=texto)
    raiz = tmp_path / "formato_num_em_percentual"
    apoio.escrever_raiz(raiz, entrega_dict)

    resultado = rodar_builder(raiz)

    assert resultado.returncode == 2, resultado.stdout + resultado.stderr
    achado = next(a for a in ler_qc(raiz)["achados"] if a["codigo"] == "formato_incompativel_com_unidade")
    assert achado["params"]["unidade"] == "pp"


# --------------------------------------------------------------------------
# B12 (achado S4): múltiplo justo e múltiplo de tela em bases diferentes é
# contrato quebrado -- HARD FAIL, nunca lado a lado.
# --------------------------------------------------------------------------

def test_multiplos_com_bases_diferentes_falha(tmp_path):
    """VERIFICADO pela revisão: um `mercado_tela` em base 'pl' ao lado de um
    múltiplo justo em base 'ebitda' renderizava os dois lado a lado, rc 0."""
    entrega_dict = apoio.montar_entrega("caso_reversa_firm.json")
    assert entrega_dict["resultados"]["manchete"]["multiplo"]["base"] == "ebitda"
    entrega_dict["resultados"]["mercado_tela"]["base"] = "pl"
    raiz = tmp_path / "bases_divergentes"
    apoio.escrever_raiz(raiz, entrega_dict)

    resultado = rodar_builder(raiz)

    assert resultado.returncode == 2, resultado.stdout + resultado.stderr
    achado = next(a for a in ler_qc(raiz)["achados"] if a["codigo"] == "multiplos_com_bases_diferentes")
    assert achado["params"]["base_manchete"] == "ebitda"
    assert achado["params"]["base_mercado_tela"] == "pl"


# --------------------------------------------------------------------------
# B14 (não-material): moeda sem símbolo no dicionário usa o código ISO como
# prefixo, nunca um traceback cru.
# --------------------------------------------------------------------------

def test_moeda_sem_simbolo_usa_codigo_iso_sem_traceback(tmp_path):
    """VERIFICADO pela revisão: uma `caso.moeda` não-BRL sem `|moeda` na
    prosa (nada para `resolver()` capturar o erro) derrubava `render.compor`
    com um `FormatoInvalido` não tratado -- rc 1, traceback cru no stderr,
    em vez da recusa nomeada que todo o resto do relatório garante."""
    def _usar_dolar(caso):
        caso["moeda"] = "USD-nominal"

    entrega_dict = apoio.montar_entrega("caso_reversa_firm.json", mutar_caso=_usar_dolar)
    raiz = tmp_path / "moeda_sem_simbolo"
    apoio.escrever_raiz(raiz, entrega_dict)

    resultado = rodar_builder(raiz)

    assert resultado.returncode == 0, resultado.stdout + resultado.stderr
    assert "Traceback" not in resultado.stderr
    html = (raiz / "relatorio.html").read_text(encoding="utf-8")
    assert "USD " in html


# --------------------------------------------------------------------------
# CLI: REQUIRED DISCLOSURE (código 0, mas visível em qc.json).
# --------------------------------------------------------------------------

def test_degrau_com_divergencia_emite_com_disclosure(tmp_path):
    """caso_degrau.json: divergencia_de_base_% ~= 16.4%, acima do limiar de
    5.0% do catálogo — REQUIRED DISCLOSURE, não HARD FAIL."""
    entrega_dict = apoio.montar_entrega("caso_degrau.json")
    raiz = tmp_path / "degrau"
    apoio.escrever_raiz(raiz, entrega_dict)

    resultado = rodar_builder(raiz)

    assert resultado.returncode == 0, resultado.stdout + resultado.stderr
    assert (raiz / "relatorio.html").exists()
    qc_json = ler_qc(raiz)
    assert not any(a["nivel"] == "HARD_FAIL" for a in qc_json["achados"])
    achado = next(a for a in qc_json["achados"] if a["codigo"] == "divergencia_de_base_degrau")
    assert achado["nivel"] == "REQUIRED_DISCLOSURE"
    assert achado["params"]["cenario"] == "base"
    assert achado["params"]["valor"] == pytest.approx(16.4, abs=0.05)


# --------------------------------------------------------------------------
# CLI: uso ou contrato inválido (código 1) — nada é escrito.
# --------------------------------------------------------------------------

def test_chave_desconhecida_na_entrega_falha_com_sugestao(tmp_path):
    entrega_dict = apoio.montar_entrega("caso_reversa_firm.json")
    entrega_dict["execucaoo"] = entrega_dict.pop("execucao")
    raiz = tmp_path / "chave_desconhecida"
    apoio.escrever_raiz(raiz, entrega_dict)

    resultado = rodar_builder(raiz)

    assert resultado.returncode == 1, resultado.stdout + resultado.stderr
    assert not (raiz / "qc.json").exists()
    assert not (raiz / "relatorio.html").exists()
    assert "execucaoo" in resultado.stderr
    assert "execucao" in resultado.stderr


def test_versao_da_entrega_incompativel_falha(tmp_path):
    entrega_dict = apoio.montar_entrega("caso_reversa_firm.json")
    entrega_dict["versao_contrato"] = "entrega/2"
    raiz = tmp_path / "versao_entrega"
    apoio.escrever_raiz(raiz, entrega_dict)

    resultado = rodar_builder(raiz)

    assert resultado.returncode == 1, resultado.stdout + resultado.stderr
    assert not (raiz / "qc.json").exists()
    assert "versao_contrato" in resultado.stderr


def test_versao_dos_resultados_incompativel_falha(tmp_path):
    entrega_dict = apoio.montar_entrega("caso_reversa_firm.json")
    entrega_dict["resultados"]["versao_contrato"] = "resultados/2"
    raiz = tmp_path / "versao_resultados"
    apoio.escrever_raiz(raiz, entrega_dict)

    resultado = rodar_builder(raiz)

    assert resultado.returncode == 1, resultado.stdout + resultado.stderr
    assert not (raiz / "qc.json").exists()
    assert "resultados.versao_contrato" in resultado.stderr


def test_entrega_ausente_falha(tmp_path):
    raiz = tmp_path / "vazia"
    raiz.mkdir()

    resultado = rodar_builder(raiz)

    assert resultado.returncode == 1, resultado.stdout + resultado.stderr
    assert not (raiz / "qc.json").exists()
    assert "ausente" in resultado.stderr


def test_entrega_symlink_fora_da_raiz_falha(tmp_path):
    entrega_dict = apoio.montar_entrega("caso_reversa_firm.json")
    fora = tmp_path / "fora"
    alvo_externo = apoio.escrever_raiz(fora, entrega_dict)

    raiz = tmp_path / "raiz_symlink"
    raiz.mkdir()
    link = raiz / "entrega.json"
    try:
        link.symlink_to(alvo_externo)
    except OSError as erro:
        pytest.skip(f"symlink indisponível nesta máquina (privilégio do SO): {erro}")

    resultado = rodar_builder(raiz)

    assert resultado.returncode == 1, resultado.stdout + resultado.stderr
    assert not (raiz / "qc.json").exists()
    assert not (raiz / "relatorio.html").exists()
    assert "fora da raiz" in resultado.stderr


def test_idioma_sem_dicionario_falha(tmp_path):
    entrega_dict = apoio.montar_entrega("caso_reversa_firm.json", idioma="en-US")
    raiz = tmp_path / "idioma_invalido"
    apoio.escrever_raiz(raiz, entrega_dict)

    resultado = rodar_builder(raiz)

    assert resultado.returncode == 1, resultado.stdout + resultado.stderr
    assert not (raiz / "qc.json").exists()
    assert "idioma" in resultado.stderr
