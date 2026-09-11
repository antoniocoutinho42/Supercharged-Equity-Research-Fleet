import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

def test_plugin_json_v3():
    p = json.loads((RAIZ / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    assert p["version"] == "3.0.0"
    assert p["name"] == "equity-research-fleet"
    assert p["description"].strip()

def test_marketplace_json_v3():
    m = json.loads((RAIZ / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
    assert m["metadata"]["version"] == "3.0.0"
    assert m["plugins"][0]["version"] == "3.0.0"

def test_v2_removida():
    for morto in ["schemas", "scripts/pipeline.py", "scripts/validar.py", "scripts/snapshot.py",
                  "scripts/delta.py", "skills/er-processo",
                  "skills/er-auditoria", "skills/er-portfolio",
                  "skills/er-guardrails", "skills/er-dossie", "skills/er-dados",
                  "skills/er-memoria", "agents/analista.md", "agents/modelador.md",
                  "agents/auditor.md", "agents/portfolio-manager.md", "agents/redator.md"]:
        assert not (RAIZ / morto).exists(), f"resto v2: {morto}"


def test_er_valuation_da_v4_nao_e_a_da_v2():
    """`skills/er-valuation` existe de novo, com outro papel.

    Na v2 era uma skill com engine proprio (cap_check, engine v3.3.0). Na v4 e o
    wrapper que chama o motor congelado por subprocess e nao tem matematica
    nenhuma. Por isso a entrada saiu da lista de mortos acima: a garantia deixa
    de ser AUSENCIA e passa a ser CONTEUDO — a skill nova nao pode ser a antiga
    voltando com o mesmo nome.
    """
    nova = RAIZ / "skills" / "er-valuation"
    assert nova.exists()
    assert not (nova / "scripts" / "cap_check.py").exists(), "cap_check da v2 ressuscitou"
    for arq in nova.rglob("*.py"):
        texto = arq.read_text(encoding="utf-8")
        assert "engine v3.3.0" not in texto, f"engine da v2 referenciado em {arq.name}"


def test_er_relatorio_da_v4_nao_e_a_da_v2():
    """`skills/er-relatorio` existe de novo, com outro papel.

    Na v2 era o compositor de um relatorio em PDF: arquivos soltos direto
    na raiz da skill (`compor.py`, `checar.py`, `render_pdf.py`,
    `template.css`; removidos em 6fa94d5). Na v4 (item 5, fatia 5A) e o
    builder do contrato `entrega.json` -> HTML autocontido: `scripts/`
    (`entrega.py`, `placeholders.py`, `qc.py`, `builder.py`) e
    `assets/i18n/`, sem PDF nenhum e sem importar a integração (E3). Por
    isso a entrada saiu da lista de mortos acima: a garantia deixa de ser
    AUSÊNCIA e passa a ser CONTEÚDO — a skill nova não pode ser a antiga
    voltando com o mesmo nome.
    """
    nova = RAIZ / "skills" / "er-relatorio"
    assert nova.exists()
    for morto in ("checar.py", "compor.py", "render_pdf.py", "template.css"):
        assert not (nova / morto).exists(), f"arquivo solto da v2 ressuscitou: {morto}"
    assert (nova / "scripts" / "builder.py").exists()
    for arq in nova.rglob("*.py"):
        assert "render_pdf" not in arq.read_text(encoding="utf-8"), f"PDF da v2 referenciado em {arq.name}"
