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
    # B4 (onda de correção da revisão final, achado F8): 'pp' é o formato de
    # um valor JÁ em pontos percentuais -- 10.0 é dez por cento, nunca mil.
    # O achado estava aberto desde a 5A: com `pp` multiplicando por 100, 68
    # testes seguiam verdes, porque nenhum afirmava a STRING que `pp`
    # produz. Estes três são a asserção direta que faltava.
    (10.0, "pp1", "10,0%"),
    (10.0, "pp0", "10%"),
    (16.428571428571427, "pp2", "16,43%"),
    (-2.5, "pp1", "-2,5%"),
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
    # B6 (achado F10): o invariante é sobre a PROSA que o relatório
    # escreveu, não sobre a página -- ver `apoio.prosa_da_pagina`.
    prosa = apoio.prosa_da_pagina(html)
    assert "{{" not in prosa and "}}" not in prosa
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
    # Escopo, não lista de exclusão (B6): o alias não pode aparecer na PROSA
    # que o relatório escreve. Desde a fatia 5C o `caso` inteiro viaja num
    # `<script type="application/json">` para o laboratório recalcular preço
    # no navegador -- e lá dentro o alias existe, porque é o que o caso
    # declara e é o que a fachada tem de receber. `prosa_da_pagina` neutraliza
    # o miolo de todo `<script>`/`<style>`, que é exatamente a fronteira que
    # esta asserção sempre quis: nenhum código interno na TELA.
    # `test_relatorio_laboratorio.py::test_um_valor_que_o_catalogo_nao_sabe_
    # nomear_nao_vaza_o_codigo_cru` cobra a mesma coisa no campo do painel.
    assert "spread" not in apoio.prosa_da_pagina(html)


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
    normalmente -- a checagem não é falso positivo no caminho feliz.

    B4 (achado F8): este teste afirmava só `rc == 0` e `achados == []`, e
    por isso ficava VERDE com `pp` multiplicando por 100 -- nunca lia a
    string renderizada. Agora afirma o TEXTO que o analista lê: um WACC de
    10 pontos percentuais imprime "10,0%", não "1.000,0%"."""
    texto = "WACC de {{caso:cenarios.base.premissas.wacc|pp1}} no cenário-base."
    entrega_dict = apoio.montar_entrega("caso_reversa_firm.json", texto_conclusao=texto)
    raiz = tmp_path / "formato_pp_ok"
    apoio.escrever_raiz(raiz, entrega_dict)

    resultado = rodar_builder(raiz)

    assert resultado.returncode == 0, resultado.stdout + resultado.stderr
    assert ler_qc(raiz)["achados"] == []
    wacc = entrega_dict["caso"]["cenarios"]["base"]["premissas"]["wacc"]
    html = (raiz / "relatorio.html").read_text(encoding="utf-8")
    assert f"WACC de {placeholders.formatar(wacc, 'pp1', 'pt-BR')} no cenário-base." in html
    assert "WACC de 10,0% no cenário-base." in html


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
    """caso_degrau.json: divergencia_de_base_% ~= 16.4%, acima do limiar da
    integração, que publica a chave que o disclosure nomeia no catálogo —
    REQUIRED DISCLOSURE, não HARD FAIL."""
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
# Onda de correção da revisão final da 5C (F1): a QC CONSOME a chave que a
# integração publica em `degrau.diagnosticos_chaves` — a que
# `catalogo.disclosures.divergencia_de_base_degrau.chave` nomeia — e não
# compara limiar nenhum. O limiar é da integração (`avaliar.py`, espelhado na
# fachada), e é por isso que o disclosure e o laboratório não podem mais
# discordar: os dois leem a mesma decisão.
# --------------------------------------------------------------------------

def _disclosures_de_divergencia(entrega_dict: dict) -> list:
    return [a for a in qc.avaliar(entrega_dict, CATALOGO) if a.codigo == "divergencia_de_base_degrau"]


def test_o_disclosure_de_divergencia_segue_a_chave_da_integracao_nunca_um_limiar():
    """Os dois lados que só uma QC que lê a CHAVE acerta — e que uma QC que
    voltasse a comparar o número com um limiar erraria, qualquer que fosse o
    limiar escolhido:
    - número bem acima de qualquer limiar plausível (16,4%), chave retirada:
      nenhum disclosure;
    - número irrisório (0,1234%), chave presente: disclosure, imprimindo o
      número publicado — e nenhum parâmetro de limiar no achado."""
    chave = CATALOGO["disclosures"]["divergencia_de_base_degrau"]["chave"]
    publicada = apoio.montar_entrega("caso_degrau.json")
    degrau = publicada["resultados"]["cenarios"]["base"]["degrau"]
    assert degrau["divergencia_de_base_%"] > 10 and chave in degrau["diagnosticos_chaves"], degrau

    sem_chave = json.loads(json.dumps(publicada))
    sem_chave["resultados"]["cenarios"]["base"]["degrau"]["diagnosticos_chaves"].remove(chave)
    assert _disclosures_de_divergencia(sem_chave) == []

    irrisoria = json.loads(json.dumps(publicada))
    irrisoria["resultados"]["cenarios"]["base"]["degrau"]["divergencia_de_base_%"] = 0.1234
    achados = _disclosures_de_divergencia(irrisoria)
    assert len(achados) == 1, achados
    assert achados[0].params["valor_fmt"] == placeholders.formatar(0.1234, "pp1", "pt-BR")
    assert not [nome for nome in achados[0].params if nome.startswith("limiar")], achados[0].params


@pytest.mark.parametrize("roe,valor_esperado", [(17.2, None), (25.0, 45.5)])
def test_o_disclosure_de_divergencia_anda_com_a_premissa_editada(roe, valor_esperado):
    """Os dois casos concretos da revisão, pelo caminho de produção
    (`avaliar()` de verdade sobre o caso editado): ROE 17,2 leva a divergência
    a 0,16% e o disclosure some; ROE 25 a leva a 45,5% e o disclosure imprime
    esse número, não os 16,4% da carga."""
    def _editar(caso: dict) -> None:
        caso["cenarios"]["base"]["premissas"]["roe"] = roe

    achados = _disclosures_de_divergencia(apoio.montar_entrega("caso_degrau.json", mutar_caso=_editar))
    if valor_esperado is None:
        assert achados == []
    else:
        assert len(achados) == 1, achados
        assert achados[0].params["valor"] == pytest.approx(valor_esperado, abs=0.05)


def test_degrau_sem_lista_de_chaves_e_hard_fail():
    """Defesa em profundidade, a mesma do B10: consumir a chave não pode abrir
    um caminho em que o disclosure some em silêncio. Um degrau publicado sem
    `diagnosticos_chaves` é contrato quebrado da integração — HARD FAIL
    nomeando o caminho, nunca "sem chave, sem disclosure"."""
    entrega_dict = apoio.montar_entrega("caso_degrau.json")
    del entrega_dict["resultados"]["cenarios"]["base"]["degrau"]["diagnosticos_chaves"]

    achados = qc.avaliar(entrega_dict, CATALOGO)
    achado = next(a for a in achados if a.onde == "resultados.cenarios.base.degrau.diagnosticos_chaves")
    assert (achado.nivel, achado.codigo) == ("HARD_FAIL", "diagnostico_sem_chave")
    assert not [a for a in achados if a.codigo == "divergencia_de_base_degrau"]


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


# --------------------------------------------------------------------------
# B3 (onda de correção da revisão final, achado F6): quatro caminhos de
# CRASH CRU -- traceback, rc 1 e nenhum `qc.json` -- todos a partir de
# entrada que o contrato ACEITA, e todos contradizendo o que o docstring de
# `builder.py` promete para o código 1 ("a razão sai em stderr, nomeando o
# campo/chave"). Aqui, pelo CLI de verdade, como a revisão os provou.
# --------------------------------------------------------------------------

def _dataset(x, campos):
    return {"ledger": [], "x": x, "campos": campos}


def _exhibit_derivado(formula="a + b"):
    return {
        "id": "d", "pergunta": "pergunta válida", "tipo": "linha",
        "nota_janela": "janela curta de propósito",
        "series": [{"derivacao": "derivada", "fonte": "fin", "formula": formula,
                    "formula_nota": "soma"}],
    }


def test_formula_sobre_campos_de_comprimentos_diferentes_recusa_nomeada(tmp_path):
    """(a) `tamanho` saía do PRIMEIRO campo em ordem alfabética:
    `IndexError: list index out of range`, rc 1, sem `qc.json`."""
    dados = {"fin": _dataset([1, 2, 3], {"a": [1.0, 2.0, 3.0], "b": [1.0]})}
    entrega_dict = apoio.montar_entrega(
        "caso_reversa_firm.json", dados=dados, exhibits=[_exhibit_derivado()])
    raiz = tmp_path / "formula_campos_desiguais"
    apoio.escrever_raiz(raiz, entrega_dict)

    resultado = rodar_builder(raiz)

    assert resultado.returncode == 2, resultado.stdout + resultado.stderr
    assert "Traceback" not in resultado.stderr
    assert "formula_invalida" in codigos_de(ler_qc(raiz))
    assert not (raiz / "relatorio.html").exists()


def test_null_em_campo_lido_pela_formula_recusa_nomeada(tmp_path):
    """(b) o mais provável e o mais feio: `float(None)` -> `TypeError`, rc 1,
    sem `qc.json`. `null` é documentado como "o jeito natural de um dataset
    marcar ponto ausente" e a série `direta` o trata com elegância."""
    dados = {"fin": _dataset([1, 2, 3], {"a": [1.0, None, 3.0], "b": [1.0, 2.0, 3.0]})}
    entrega_dict = apoio.montar_entrega(
        "caso_reversa_firm.json", dados=dados, exhibits=[_exhibit_derivado()])
    raiz = tmp_path / "formula_com_null"
    apoio.escrever_raiz(raiz, entrega_dict)

    resultado = rodar_builder(raiz)

    assert resultado.returncode == 2, resultado.stdout + resultado.stderr
    assert "Traceback" not in resultado.stderr
    assert "formula_invalida" in codigos_de(ler_qc(raiz))


def test_nan_em_dataset_recusa_nomeada(tmp_path):
    """(c) `json.loads` aceita o literal `NaN`; `json.dumps(allow_nan=False)`
    do `_json_embutido` estourava `ValueError` do `json.encoder` -- a defesa
    em profundidade estava certa, a exceção é que não era NOMEADA."""
    dados = {"fin": _dataset([1, 2, 3], {"receita": [1.0, float("nan"), 3.0]})}
    exhibit = {
        "id": "fin", "pergunta": "pergunta válida", "tipo": "linha",
        "nota_janela": "janela curta de propósito",
        "series": [{"derivacao": "direta", "fonte": "fin.receita"}],
    }
    entrega_dict = apoio.montar_entrega("caso_reversa_firm.json", dados=dados, exhibits=[exhibit])
    raiz = tmp_path / "dataset_com_nan"
    apoio.escrever_raiz(raiz, entrega_dict)

    resultado = rodar_builder(raiz)

    assert resultado.returncode == 1, resultado.stdout + resultado.stderr
    assert "Traceback" not in resultado.stderr
    assert "JSON" in resultado.stderr
    assert not (raiz / "relatorio.html").exists()


def test_contrato_do_motor_renomeado_recusa_nomeada(tmp_path):
    """(d) um v10 que renomeie `resultados.ponte.nd_efetivo`: `KeyError:
    'nd_efetivo'` com traceback, rc 1 e nenhuma menção ao campo. Agora a
    recusa NOMEIA o caminho."""
    entrega_dict = apoio.montar_entrega("caso_reversa_firm.json")
    entrega_dict["resultados"]["ponte"]["nd_efetivo_v10"] = \
        entrega_dict["resultados"]["ponte"].pop("nd_efetivo")
    raiz = tmp_path / "ponte_renomeada"
    apoio.escrever_raiz(raiz, entrega_dict)

    resultado = rodar_builder(raiz)

    assert resultado.returncode == 1, resultado.stdout + resultado.stderr
    assert "Traceback" not in resultado.stderr
    assert "resultados.ponte" in resultado.stderr
    assert "nd_efetivo" in resultado.stderr
    assert not (raiz / "relatorio.html").exists()


# --------------------------------------------------------------------------
# B5 (onda de correção da revisão final, achado F9): o `SKILL.md` documentava
# um `entrega/1` que o builder RECUSA -- o exemplo não tinha
# `analise.exhibits`, que a Task 1 tornou obrigatório, e a entrega
# exatamente como documentada saía com `RC=1`. Quem produz a entrega em
# produção é `er-analise` (item 8), um agente que lê esse arquivo: "chave
# documentada só no plano e no código" é a classe de bug que já produziu o
# F3 da fatia D. Os dois exemplos do SKILL.md passam a ser EXECUTADOS.
# --------------------------------------------------------------------------

SKILL_MD = SCRIPTS.parent / "SKILL.md"


def _bloco_json_do_skill(indice: int) -> dict:
    """O `indice`-ésimo bloco ```json do SKILL.md, como dict. O bloco da
    gramática de exhibits é um FRAGMENTO (chaves de topo soltas), então é
    envolvido em chaves antes de parsear."""
    texto = SKILL_MD.read_text(encoding="utf-8")
    blocos = [b.split("```", 1)[0] for b in texto.split("```json\n")[1:]]
    bruto = blocos[indice].strip()
    return json.loads(bruto if bruto.startswith("{") else "{" + bruto + "}")


def test_exemplo_de_entrega_do_skill_md_emite(tmp_path):
    """O exemplo do contrato, verbatim, com `caso`/`resultados` de uma
    fixture real no lugar dos `{}` (o SKILL.md os documenta como opacos)."""
    exemplo = _bloco_json_do_skill(0)
    real = apoio.montar_entrega("caso_reversa_firm.json")
    exemplo["caso"], exemplo["resultados"] = real["caso"], real["resultados"]
    exemplo["execucao"]["ticker"] = real["execucao"]["ticker"]
    raiz = tmp_path / "exemplo_do_skill"
    apoio.escrever_raiz(raiz, exemplo)

    resultado = rodar_builder(raiz)

    assert resultado.returncode == 0, resultado.stdout + resultado.stderr
    assert (raiz / "relatorio.html").exists()
    assert ler_qc(raiz)["achados"] == []


def test_exemplo_da_gramatica_de_exhibits_do_skill_md_emite(tmp_path):
    """O segundo exemplo (dataset + exhibit com as três proveniências e um
    overlay), montado sobre a mesma entrega válida."""
    fragmento = _bloco_json_do_skill(1)
    entrega_dict = apoio.montar_entrega(
        "caso_reversa_firm.json",
        dados=fragmento["dados"], exhibits=fragmento["analise"]["exhibits"])
    raiz = tmp_path / "exemplo_de_exhibits"
    apoio.escrever_raiz(raiz, entrega_dict)

    resultado = rodar_builder(raiz)

    assert resultado.returncode == 0, resultado.stdout + resultado.stderr
    assert ler_qc(raiz)["achados"] == []
    html = (raiz / "relatorio.html").read_text(encoding="utf-8")
    assert fragmento["analise"]["exhibits"][0]["pergunta"] in html


def test_tabela_de_qc_do_skill_md_cobre_todo_codigo_emitido():
    """Nenhum código de QC que `qc.py` de fato constrói pode ficar fora da
    tabela do SKILL.md -- é ali que `er-analise` descobre o que o builder
    recusa."""
    texto = SKILL_MD.read_text(encoding="utf-8")
    codigos = set(placeholders.carregar_dicionario("pt-BR")["qc"])
    faltando = {codigo for codigo in codigos if f"`{codigo}`" not in texto}
    assert not faltando, faltando
