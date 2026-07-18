# -*- coding: utf-8 -*-
"""Todo SKILL.md do plugin deve ter frontmatter YAML VALIDO com name e description.

Motivo: as skills originais tinham description escalar sem aspas contendo ": ",
que quebra o parse YAML (funcionava por leniencia do parser da plataforma, mas
e um defeito real de empacotamento). Este teste trava a regressao para todas as
skills presentes e futuras.
"""
import re
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parents[1]


def _frontmatter(texto):
    m = re.match(r"^---\r?\n(.*?)\r?\n---", texto, re.S)
    assert m, "frontmatter delimitado por --- ausente"
    return yaml.safe_load(m.group(1))


def test_todo_skill_md_tem_frontmatter_yaml_valido():
    skills = sorted((RAIZ / "skills").glob("*/SKILL.md"))
    assert skills, "nenhuma skill encontrada"
    problemas = []
    for p in skills:
        try:
            d = _frontmatter(p.read_text(encoding="utf-8"))
        except Exception as e:  # noqa: BLE001 - queremos listar todos os problemas
            problemas.append(f"{p.relative_to(RAIZ)}: {e}")
            continue
        if not isinstance(d, dict) or not d.get("name") or not d.get("description"):
            problemas.append(f"{p.relative_to(RAIZ)}: name/description ausentes")
    assert not problemas, "frontmatter invalido:\n" + "\n".join(problemas)


def test_name_do_frontmatter_bate_com_diretorio():
    for p in sorted((RAIZ / "skills").glob("*/SKILL.md")):
        d = _frontmatter(p.read_text(encoding="utf-8"))
        assert d["name"] == p.parent.name, (
            f"{p.relative_to(RAIZ)}: name '{d['name']}' != diretorio '{p.parent.name}'"
        )
