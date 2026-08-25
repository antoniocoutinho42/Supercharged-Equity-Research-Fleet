from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SKILL = RAIZ / "skills" / "er-valuation"


def test_frontmatter_declara_o_nome_novo():
    texto = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    assert texto.startswith("---")
    assert "name: er-valuation" in texto


def test_skill_declara_o_que_nunca_faz():
    """A fronteira do wrapper e a razao de ele existir — tem de estar escrita."""
    texto = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    for obrigatorio in ("nunca", "motor", "sem default"):
        assert obrigatorio in texto.lower()


def test_skill_aponta_os_quatro_modulos():
    texto = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    for modulo in ("caso.py", "motor.py", "ponte.py", "avaliar.py"):
        assert modulo in texto


def test_skill_nao_e_a_v2_ressuscitada():
    """A v2 tinha engine proprio; a v4 chama o vendor. Nada da v2 pode voltar."""
    texto = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    for morto in ("cap_check", "engine v3.3.0", "K3", "16 canonical inputs", "justified"):
        assert morto.lower() not in texto.lower(), f"residuo da v2/v3: {morto}"


def test_skill_nao_declara_reversa_e_sensibilidades_como_futuro():
    """Fatia B implementou os dois: a secao de pendencias nao pode mais cita-los.

    A versao anterior do SKILL.md listava 'reversa e sensibilidades' dentro
    de 'Ainda não implementados aqui'. Essa fatia implementou os dois — a
    frase tem de sumir dali (movida para o corpo), sem que o paragrafo de
    pendencias remanescente (soma das partes, multifasico) desapareca junto.
    """
    texto = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    marcador = "ainda não implementados"
    baixo = texto.lower()
    assert marcador in baixo, "secao de pendencias sumiu do SKILL.md"
    inicio = baixo.index(marcador)
    fim = texto.index("\n\n", inicio)
    trecho_pendencias = texto[inicio:fim]
    assert "reversa" not in trecho_pendencias.lower()
    assert "sensibilidades" not in trecho_pendencias.lower()
    # Fatia C, Task 4: SOTP e a rota rampa -- o que sobrava de pendência na
    # época desta asserção ("multifásic[a]", travado aqui até então) -- por
    # sua vez saem de 'ainda não implementados' NESSA fatia; quem passa a
    # travar essa remoção específica é
    # test_skill_nao_declara_sotp_e_multifasico_como_futuro, abaixo. Este
    # teste continua só responsável por reversa/sensibilidades.

    # movidos para o corpo (fora da secao de pendencias) e a tabela ganhou
    # os dois modulos novos.
    assert "reversa.py" in texto
    assert "sensibilidades.py" in texto


# --------------------------------------------------------------------------
# Fatia C, Task 4: SOTP (soma das partes) e a rota rampa (composição
# multifásica) implementados -- a seção de pendências não pode mais
# citá-los como fatia futura, e a rota rampa tem de aparecer no corpo.
# --------------------------------------------------------------------------

def test_skill_nao_declara_sotp_e_multifasico_como_futuro():
    texto = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    marcador = "ainda não implementados"
    baixo = texto.lower()
    assert marcador in baixo, "secao de pendencias sumiu do SKILL.md"
    inicio = baixo.index(marcador)
    fim = texto.index("\n\n", inicio)
    trecho_pendencias = texto[inicio:fim].lower()
    assert "sotp" not in trecho_pendencias
    assert "multifásic" not in trecho_pendencias and "multifasic" not in trecho_pendencias
    assert "soma das partes" not in trecho_pendencias

    # movidos para o corpo, e sotp.py entrou na tabela de módulos.
    assert "sotp.py" in texto


def test_skill_menciona_a_rota_rampa():
    texto = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    assert "rampa" in texto.lower()
