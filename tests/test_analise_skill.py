"""O `SKILL.md` v4 do `er-analise` (item 8, Task 3 do plano
docs/superpowers/plans/2026-09-16-v4-item8-er-analise.md).

Travas leves de documentação, sem motor. O `SKILL.md` é o que o Analista lê para conduzir a execução;
uma referência que não existe ou um código de QC digitado errado o mandam procurar o que não há.

- o frontmatter;
- todo arquivo do repositório, skill, agente e caminho do catálogo que o `SKILL.md` cita existe;
- todo código de QC citado existe no `qc.py`: os da tabela dos códigos, com o nível que o `qc.py` lhes dá,
  e nenhuma citação solta que seja quase um código — o erro de digitação que a leitura não pega;
- o checklist de revisão do M4 existe e trata dos três julgamentos editoriais que a "Cobertura da §11" do
  `er-relatorio` aponta para ele (D5);
- nenhuma referência ao fluxo v3: as fases, o motor K3, o data-manager e as skills da v3.
"""

import ast
import difflib
import json
import re
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parent.parent
SKILL = RAIZ / "skills" / "er-analise"
SKILL_MD = SKILL / "SKILL.md"
SKILL_DO_RELATORIO = RAIZ / "skills" / "er-relatorio" / "SKILL.md"
QC_PY = RAIZ / "skills" / "er-relatorio" / "scripts" / "qc.py"
CATALOGO = RAIZ / "skills" / "er-valuation" / "assets" / "catalogo_apresentacao.json"

# Uma citação que começa por um destes é caminho de arquivo do repositório; as outras (`evidencia/<mandato>.json`,
# `analises/<TICKER>/...`) são da raiz da execução, que só existe em uso.
PREFIXOS_DO_REPOSITORIO = ("skills/", "agents/", "vendor/", "docs/", "tests/", "scripts/")
CABECALHO_DOS_CODIGOS = ("Código", "Nível", "O que fazer")
# Quão parecida com um código de QC uma citação precisa ser, sem ser igual, para ser erro de digitação.
SEMELHANCA_DE_ERRO_DE_DIGITACAO = 0.88

_CITACAO = re.compile(r"`([^`\n]+)`")
_IDENTIFICADOR = re.compile(r"[a-z][a-z0-9_]*")
_SKILL_DO_FLEET = re.compile(r"er-[a-z0-9-]+")
_AGENTE = re.compile(r"agente `([a-z0-9-]+)`")
_CAMINHO_DO_CATALOGO = re.compile(r"catalogo(?:\.[a-z_]+)+")
_CHECKLIST = re.compile(r"^## (?:\d+\. )?Checklist de revisão do M4$", re.M)
# O fluxo v3: as fases F0–F11, o motor K3, o subagente de coleta, as skills que a v4 substitui e a memória durável.
_FLUXO_V3 = re.compile(r"\bF(?:[0-9]|1[01])\b|\bK3\b|data-manager|er-motor-k3|er-dados-openbb|er-relatorio-html|memoria\.py")


def _texto() -> str:
    return SKILL_MD.read_text(encoding="utf-8")


def _celulas(linha: str) -> tuple:
    return tuple(celula.strip() for celula in linha.strip().strip("|").split("|"))


def _codigos_do_qc() -> dict:
    """`{código: {nível}}` de toda chamada `Achado(<nível>, <código>, ...)` do `qc.py` — a leitura de
    `tests/test_relatorio_cobertura_11.py`: um código novo entra sem editar este teste."""
    niveis: dict = {}
    for no in ast.walk(ast.parse(QC_PY.read_text(encoding="utf-8"))):
        if isinstance(no, ast.Call) and isinstance(no.func, ast.Name) and no.func.id == "Achado":
            nivel, codigo = (argumento.value for argumento in no.args[:2])
            niveis.setdefault(codigo, set()).add(nivel)
    assert niveis, "nenhuma chamada Achado(...) no qc.py — a trava ficaria vacuamente verde"
    return niveis


def _resolve(documento, segmentos: list) -> bool:
    for segmento in segmentos:
        if not (isinstance(documento, dict) and segmento in documento):
            return False
        documento = documento[segmento]
    return True


def test_frontmatter():
    texto = _texto()
    assert texto.startswith("---"), "SKILL.md sem frontmatter"
    _vazio, bruto, _corpo = texto.split("---", 2)
    frontmatter = yaml.safe_load(bruto)
    assert set(frontmatter) == {"name", "description"}, sorted(frontmatter)
    assert frontmatter["name"] == "er-analise"
    descricao = frontmatter["description"]
    assert isinstance(descricao, str) and "USE SEMPRE" in descricao and "NÃO use" in descricao, descricao


def test_todo_arquivo_skill_agente_e_caminho_do_catalogo_citado_existe():
    texto = _texto()
    citacoes = _CITACAO.findall(texto)
    arquivos = [citacao for citacao in citacoes if citacao.startswith(PREFIXOS_DO_REPOSITORIO)]
    skills = [citacao for citacao in citacoes if _SKILL_DO_FLEET.fullmatch(citacao)]
    agentes = _AGENTE.findall(texto)
    do_catalogo = [citacao.split(".")[1:] for citacao in citacoes if _CAMINHO_DO_CATALOGO.fullmatch(citacao)]
    assert arquivos and skills and agentes and do_catalogo, "nenhuma citação de algum tipo — a trava ficaria vacuamente verde"
    assert "skills/er-analise/scripts/execucao.py" in arquivos

    catalogo = json.loads(CATALOGO.read_text(encoding="utf-8"))
    ausentes = ([arquivo for arquivo in arquivos if not (RAIZ / arquivo).exists()]
                + [skill for skill in skills if not (RAIZ / "skills" / skill / "SKILL.md").is_file()]
                + [agente for agente in agentes if not (RAIZ / "agents" / f"{agente}.md").is_file()]
                + ["catalogo." + ".".join(segmentos) for segmentos in do_catalogo if not _resolve(catalogo, segmentos)])
    assert ausentes == [], f"o SKILL.md cita o que não existe: {ausentes}"


def test_todo_codigo_de_qc_citado_existe_no_qc_py():
    niveis = _codigos_do_qc()
    linhas = _texto().splitlines()
    (cabecalho,) = [indice for indice, linha in enumerate(linhas)
                    if linha.startswith("|") and _celulas(linha) == CABECALHO_DOS_CODIGOS]
    tabela = []
    for linha in linhas[cabecalho + 2:]:
        if not linha.startswith("|"):
            break
        codigo, nivel, _acao = _celulas(linha)
        assert re.fullmatch(r"`[a-z_]+`", codigo), f"célula de código fora da forma: {codigo!r}"
        tabela.append((codigo.strip("`"), nivel.replace(" ", "_")))
    assert tabela, "a tabela dos códigos está vazia — a trava ficaria vacuamente verde"
    assert [(codigo, nivel) for codigo, nivel in tabela if nivel not in niveis.get(codigo, set())] == []

    identificadores = {citacao for citacao in _CITACAO.findall(_texto()) if _IDENTIFICADOR.fullmatch(citacao)}
    quase_codigos = {citacao: difflib.get_close_matches(citacao, sorted(niveis), n=1,
                                                        cutoff=SEMELHANCA_DE_ERRO_DE_DIGITACAO)
                     for citacao in identificadores - set(niveis)}
    assert {citacao: parecido for citacao, parecido in quase_codigos.items() if parecido} == {}


def test_o_checklist_do_m4_trata_dos_julgamentos_editoriais_que_a_cobertura_da_11_aponta_para_ele():
    cobertura = SKILL_DO_RELATORIO.read_text(encoding="utf-8").split("## Cobertura da §11\n", 1)[1].split("\n## ", 1)[0]
    apontados = [_celulas(linha)[1] for linha in cobertura.splitlines()
                 if linha.startswith("|") and "checklist de revisão do M4" in linha]
    assert apontados == ["exhibit fraco", "pergunta de tese pouco discriminante",
                         "Positives/Negatives pouco ligados ao valuation"], apontados

    (inicio,) = [encontrado.end() for encontrado in _CHECKLIST.finditer(_texto())]
    checklist = _texto()[inicio:].split("\n## ", 1)[0]
    for ancora in ("exhibit responde à pergunta", "pergunta da tese discrimina", "Positives e Negatives"):
        assert ancora in checklist, ancora


def test_nenhuma_referencia_ao_fluxo_v3():
    arquivos = sorted(caminho for caminho in SKILL.rglob("*") if caminho.suffix in (".md", ".py"))
    assert SKILL_MD in arquivos
    encontrados = [(caminho.relative_to(SKILL).as_posix(), achado.group(0)) for caminho in arquivos
                   for achado in _FLUXO_V3.finditer(caminho.read_text(encoding="utf-8"))]
    assert encontrados == []
