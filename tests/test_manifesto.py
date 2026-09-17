import json
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent

VERSAO = "4.0.0"

# As cinco skills da §3.2 do desenho e o agente de tipo unico da §3.3. O vendor NAO
# entra: ele vive em vendor/multiplos-justos/, fora de skills/, de proposito -- a
# invariante "nenhum SKILL.md aninhado sob skills/" e o porque dela estao em
# tests/test_vendor_multiplos_justos.py, e nao sao duplicados aqui.
SKILLS_DA_V4 = {"er-multiplos-justos", "er-valuation", "er-evidencia", "er-analise", "er-relatorio"}
AGENTES_DA_V4 = {"pesquisa-evidencia"}

def test_plugin_json_v4():
    p = json.loads((RAIZ / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    assert p["version"] == VERSAO
    assert p["name"] == "equity-research-fleet"
    assert p["description"].strip()

def test_marketplace_json_v4():
    m = json.loads((RAIZ / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
    assert m["metadata"]["version"] == VERSAO
    assert m["plugins"][0]["version"] == VERSAO


def test_manifestos_nao_descrevem_mais_a_v3():
    """A versao e a descricao andam juntas.

    Subir o numero e deixar a descricao da v3 (Data Manager, motor K3, OpenBB
    exclusivo, 2 abas) publica no marketplace um plugin que nao existe mais.
    """
    p = json.loads((RAIZ / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    m = json.loads((RAIZ / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
    mortos = ("Data Manager", "K3", "2 abas", "v3")
    for onde, texto in (("plugin.json", p["description"]),
                        ("marketplace.json/metadata", m["metadata"]["description"]),
                        ("marketplace.json/plugins[0]", m["plugins"][0]["description"])):
        for morto in mortos:
            assert morto not in texto, f"descricao da v3 em {onde}: {morto!r}"

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


# --------------------------------------------------------------------------
# A estrutura da v4 (item 10). A remocao do legado v3/K3 do carregamento e um
# estado, nao um evento: sem trava, uma skill da v3 volta num merge e ninguem
# ve. As tres travas abaixo dizem o que EXISTE, nao so o que saiu.
# --------------------------------------------------------------------------

def test_skills_carregaveis_sao_exatamente_as_cinco_da_v4():
    """§3.2: cinco skills, nem mais nem menos.

    Skill carregavel e diretorio com SKILL.md no topo de skills/ -- e assim que o
    loader as descobre. Sobrar uma reprova (legado que voltou); faltar tambem
    (algo que deveria carregar e nao carrega).
    """
    carregaveis = {p.parent.name for p in (RAIZ / "skills").glob("*/SKILL.md")}
    assert carregaveis == SKILLS_DA_V4, (
        f"sobrando: {sorted(carregaveis - SKILLS_DA_V4)} · faltando: {sorted(SKILLS_DA_V4 - carregaveis)}")


def test_o_unico_agente_e_o_pesquisa_evidencia():
    """§3.3: um tipo de agente, instanciado N vezes com mandatos distintos.

    A especializacao mora no mandato da execucao, nunca na arquitetura -- um
    segundo arquivo em agents/ seria a v3 (data-manager) voltando ou a §3.3
    sendo contrariada em silencio.
    """
    agentes = {p.stem for p in (RAIZ / "agents").glob("*.md")}
    assert agentes == AGENTES_DA_V4, f"agentes em agents/: {sorted(agentes)}"


@pytest.mark.parametrize("morto", [
    "skills/er-motor-k3", "skills/er-dados-openbb", "skills/er-relatorio-html",
    "agents/data-manager.md", "scripts/memoria.py",
    "tests/test_motor_k3.py", "tests/test_dados_openbb.py", "tests/test_build_report.py",
    "tests/test_checar_relatorio.py", "tests/test_memoria_v3.py", "tests/test_parity_js.py",
])
def test_legado_v3_nao_voltou(morto):
    """Os caminhos que o item 10 removeu, um a um -- o par de `test_v2_removida`."""
    assert not (RAIZ / morto).exists(), f"resto v3: {morto}"


# Os tres arquivos que nomeiam o legado DE PROPOSITO, e por que. Qualquer outro
# que o nomeie esta com uma referencia pendurada para algo que nao existe mais.
CITACOES_LEGITIMAS = {
    # cita os nomes como termos PROIBIDOS no SKILL.md do er-analise.
    "tests/test_analise_skill.py",
    # explica de onde vieram os sha256 congelados do uPlot (a ancora legada que saiu).
    "tests/test_relatorio_graficos.py",
    # esta lista.
    "tests/test_manifesto.py",
}

TERMOS_DA_V3 = ("er-motor-k3", "er-dados-openbb", "er-relatorio-html", "data-manager",
                "k3_engine", "manifest_copia", "scripts/memoria", "build_report",
                "checar_relatorio", "run_regressions")


def test_nenhuma_citacao_viva_do_legado_v3():
    """Nada em skills/, agents/ ou tests/ aponta para o que saiu.

    Caminho removido e facil de ver; REFERENCIA pendurada nao e -- uma linha
    "NAO use para X (essa e a skill Y)" apontando para uma skill que nao existe
    mais manda o Analista procurar o que nao ha. Historico (docs/, .superpowers/)
    fica de fora de proposito: la o legado e registro, nao carregamento.
    """
    pendentes = []
    for base in ("skills", "agents", "tests"):
        for arq in (RAIZ / base).rglob("*"):
            if not arq.is_file() or arq.suffix == ".pyc" or "__pycache__" in arq.parts:
                continue
            rel = arq.relative_to(RAIZ).as_posix()
            if rel in CITACOES_LEGITIMAS:
                continue
            try:
                texto = arq.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            for termo in TERMOS_DA_V3:
                if termo in texto:
                    pendentes.append(f"{rel}: {termo}")
    assert not pendentes, "referencia viva ao legado v3:\n  " + "\n  ".join(pendentes)
