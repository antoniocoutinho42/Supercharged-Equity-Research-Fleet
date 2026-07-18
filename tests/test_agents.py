# -*- coding: utf-8 -*-
"""Testa os 5 subagentes descartaveis (agents/*.md, Task 2.3).

No plugin, a metodologia vive nas skills; os agentes sao subagentes ENXUTOS
(identidade + fronteiras + skill obrigatoria + formato de retorno), sem
carregar a metodologia inteira. Este teste trava:
- frontmatter YAML valido, com name (== nome do arquivo sem .md) e
  description nao vazia;
- tamanho maximo por arquivo (4096 bytes, orcamento real ~2800);
- cada corpo menciona a skill obrigatoria correta e as proibicoes de papel
  portadas do mandato correspondente em docs/fontes/;
- cada corpo contem o contrato de retorno (handoff, 10 linhas).
"""
import re
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parents[1]
AGENTS_DIR = RAIZ / "agents"
TAMANHO_MAXIMO = 4096

AGENTES_ESPERADOS = (
    "analista",
    "modelador",
    "auditor",
    "portfolio-manager",
    "redator",
)

SKILL_OBRIGATORIA = {
    "analista": "er-dossie",
    "modelador": "er-valuation",
    "auditor": "er-auditoria",
    "portfolio-manager": "er-portfolio",
    "redator": "er-relatorio",
}


def _frontmatter(texto):
    m = re.match(r"^---\r?\n(.*?)\r?\n---", texto, re.S)
    assert m, "frontmatter delimitado por --- ausente"
    return yaml.safe_load(m.group(1))


def _ler(nome):
    caminho = AGENTS_DIR / f"{nome}.md"
    assert caminho.is_file(), f"arquivo ausente: {caminho}"
    return caminho, caminho.read_text(encoding="utf-8")


def test_todos_os_agentes_existem():
    for nome in AGENTES_ESPERADOS:
        caminho = AGENTS_DIR / f"{nome}.md"
        assert caminho.is_file(), f"arquivo ausente: {caminho}"


def test_frontmatter_yaml_valido_com_name_e_description():
    problemas = []
    for nome in AGENTES_ESPERADOS:
        caminho, texto = _ler(nome)
        try:
            d = _frontmatter(texto)
        except Exception as e:  # noqa: BLE001 - queremos listar todos os problemas
            problemas.append(f"{caminho.name}: {e}")
            continue
        if not isinstance(d, dict) or not d.get("name") or not d.get("description"):
            problemas.append(f"{caminho.name}: name/description ausentes")
            continue
        if d["name"] != nome:
            problemas.append(f"{caminho.name}: name '{d['name']}' != arquivo '{nome}'")
    assert not problemas, "frontmatter invalido:\n" + "\n".join(problemas)


def test_tamanho_maximo_por_arquivo():
    excedentes = []
    for nome in AGENTES_ESPERADOS:
        caminho, texto = _ler(nome)
        tamanho = len(texto.encode("utf-8"))
        if tamanho > TAMANHO_MAXIMO:
            excedentes.append(f"{caminho.name}: {tamanho} bytes (limite {TAMANHO_MAXIMO})")
    assert not excedentes, "arquivo(s) acima do limite:\n" + "\n".join(excedentes)


def test_cada_corpo_menciona_a_skill_obrigatoria_correta():
    problemas = []
    for nome, skill in SKILL_OBRIGATORIA.items():
        _, texto = _ler(nome)
        if skill not in texto:
            problemas.append(f"{nome}.md: nao menciona a skill obrigatoria '{skill}'")
    assert not problemas, "\n".join(problemas)


def test_cada_corpo_contem_contrato_de_retorno():
    problemas = []
    for nome in AGENTES_ESPERADOS:
        _, texto = _ler(nome)
        if "handoff" not in texto.lower():
            problemas.append(f"{nome}.md: nao contem 'handoff'")
        if "10 linhas" not in texto:
            problemas.append(f"{nome}.md: nao contem '10 linhas'")
    assert not problemas, "\n".join(problemas)


def test_auditor_menciona_ordem_explicita():
    _, texto = _ler("auditor")
    assert "ordem explícita" in texto.lower() or "ordem explicita" in texto.lower(), (
        "auditor.md deve mencionar 'ordem explicita' (acionamento sob demanda)"
    )


def test_portfolio_manager_menciona_snapshot():
    _, texto = _ler("portfolio-manager")
    assert "snapshot" in texto.lower(), "portfolio-manager.md deve mencionar 'snapshot'"


def test_redator_menciona_nao_altera():
    _, texto = _ler("redator")
    assert "não altera" in texto.lower() or "nao altera" in texto.lower(), (
        "redator.md deve mencionar 'nao altera' (fronteira dura de numeros/sinais)"
    )


def test_despacho_md_existe_com_gate_validar_e_tabela():
    caminho = RAIZ / "skills" / "er-processo" / "references" / "despacho.md"
    assert caminho.is_file(), f"arquivo ausente: {caminho}"
    texto = caminho.read_text(encoding="utf-8")
    assert "gate" in texto.lower(), "despacho.md deve conter 'gate'"
    assert "validar.py" in texto, "despacho.md deve conter 'validar.py'"
    # tabela gate -> agente: verifica que os 5 nomes de agente aparecem
    for nome in AGENTES_ESPERADOS:
        assert nome in texto, f"despacho.md nao menciona o agente '{nome}' na tabela"
