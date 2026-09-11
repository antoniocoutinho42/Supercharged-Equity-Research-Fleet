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
