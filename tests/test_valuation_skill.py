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
