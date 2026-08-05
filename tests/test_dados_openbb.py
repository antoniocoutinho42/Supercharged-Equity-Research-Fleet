from pathlib import Path
import yaml

RAIZ = Path(__file__).resolve().parent.parent

def _frontmatter(p):
    texto = p.read_text(encoding="utf-8")
    assert texto.startswith("---")
    fm = yaml.safe_load(texto.split("---")[1])
    assert set(fm) == {"name", "description"}
    return fm, texto

def test_skill_dados():
    fm, texto = _frontmatter(RAIZ / "skills" / "er-dados-openbb" / "SKILL.md")
    assert fm["name"] == "er-dados-openbb"
    for ancora in ["MATERIAL", "NÃO-MATERIAL", "ledger", "openbb", "yfinance",
                   "24h", "proveniência", "pedidos.md"]:
        assert ancora.lower() in texto.lower(), ancora

def test_agent_data_manager():
    p = RAIZ / "agents" / "data-manager.md"
    fm, texto = _frontmatter(p)
    assert fm["name"] == "data-manager"
    assert p.stat().st_size <= 4096
    for secao in ["## 1. Identidade", "## 2. Fronteiras duras", "## 3. Skill obrigatória",
                  "## 4. Insumos e entregáveis", "## 5. Retorno"]:
        assert secao in texto
    assert "er-dados-openbb" in texto and "10 linhas" in texto
