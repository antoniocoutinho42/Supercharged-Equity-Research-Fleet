"""A doutrina `er-evidencia` e o agente `pesquisa-evidencia` (item 7 do desenho v4).

Testes leves de documentação, sem motor. O `SKILL.md` do `er-evidencia` explica o contrato
`ledger/1`, que mora como dado em `skills/er-evidencia/assets/contrato_ledger.json` e é lido pelo
builder do relatório. As travas impedem que a doutrina escrita e o contrato lido se afastem:

- o `SKILL.md` tem frontmatter e aponta o contrato, e todo arquivo que ele cita existe;
- toda citação entre crases que nomeia algo do contrato existe no contrato lido. Um identificador
  simples é termo do contrato (nível, campo, vocabulário, entrada ou flag) ou código de QC que o
  builder constrói; um caminho que começa num nível do contrato tem campos do contrato; um caminho
  que começa em `vocabularios.` ou `niveis.` resolve no contrato, e um que começa em `catalogo.`, no
  catálogo de apresentação. Caminho de outro contrato (o caso, a entrega) fica fora desta trava;
- todo campo, todo vocabulário e toda flag do contrato são explicados, e nenhum vocabulário é
  copiado inteiro: as listas só existem no contrato;
- a tabela do que o builder recusa cita cada código com o nível que o `qc.py` lhe dá;
- o agente existe, com frontmatter válido, e segue a skill.
"""

import ast
import json
import re
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parent.parent
SKILL_MD = RAIZ / "skills" / "er-evidencia" / "SKILL.md"
CAMINHO_DO_CONTRATO = "skills/er-evidencia/assets/contrato_ledger.json"
CONTRATO = RAIZ / CAMINHO_DO_CONTRATO
CATALOGO = RAIZ / "skills" / "er-valuation" / "assets" / "catalogo_apresentacao.json"
QC_PY = RAIZ / "skills" / "er-relatorio" / "scripts" / "qc.py"
AGENTE = RAIZ / "agents" / "pesquisa-evidencia.md"

CABECALHO_DA_TABELA_DE_QC = ("O que falta ou está errado", "Código", "Nível")

_CITACAO = re.compile(r"`([^`\n]+)`")
_CAMINHO_DE_IDENTIFICADORES = re.compile(r"[a-z][a-z0-9_]*(?:\.[a-z0-9_]+)*")
_ARQUIVO = re.compile(r"[\w.-]+(?:/[\w.-]+)+\.[a-z]+")
_CODIGO = re.compile(r"`([a-z_]+)`")


def _frontmatter(caminho: Path) -> tuple[dict, str]:
    texto = caminho.read_text(encoding="utf-8")
    assert texto.startswith("---"), f"{caminho.name} sem frontmatter"
    _vazio, bruto, corpo = texto.split("---", 2)
    return yaml.safe_load(bruto), corpo


def _texto_da_skill() -> str:
    return SKILL_MD.read_text(encoding="utf-8")


def _contrato() -> dict:
    return json.loads(CONTRATO.read_text(encoding="utf-8"))


def _campos(contrato: dict) -> set:
    return {campo for nivel in contrato["niveis"].values() for campo in nivel["obrigatorias"] + nivel["opcionais"]}


def _flags(contrato: dict) -> set:
    return {flag for vocabulario in contrato["vocabularios"].values() if isinstance(vocabulario, dict)
            for flags in vocabulario.values() for flag in flags}


def _termos(contrato: dict) -> set:
    """Todo nome que o contrato declara: as chaves de topo e as de cada nível, os níveis, os campos,
    os vocabulários, as entradas e as flags."""
    termos = set(contrato) | set(contrato["niveis"]) | _campos(contrato) | _flags(contrato)
    for nivel in contrato["niveis"].values():
        termos |= set(nivel)
    for nome, vocabulario in contrato["vocabularios"].items():
        termos |= {nome, *vocabulario}
    return termos


def _resolve(documento, segmentos: list) -> bool:
    """O caminho existe no JSON: chave de objeto, ou entrada de uma lista de vocabulário no fim."""
    no = documento
    for segmento in segmentos:
        if isinstance(no, dict) and segmento in no:
            no = no[segmento]
        elif isinstance(no, list) and segmento in no:
            no = segmento
        else:
            return False
    return True


def _niveis_dos_codigos_do_qc() -> dict:
    """`{código: {nível}}` de toda chamada `Achado(<nível>, <código>, ...)` do `qc.py` — a mesma
    leitura de `tests/test_relatorio_cobertura_11.py`: um código novo entra sem editar este teste."""
    niveis: dict = {}
    for no in ast.walk(ast.parse(QC_PY.read_text(encoding="utf-8"))):
        if isinstance(no, ast.Call) and isinstance(no.func, ast.Name) and no.func.id == "Achado":
            argumentos = no.args[:2]
            if len(argumentos) == 2 and all(isinstance(a, ast.Constant) and isinstance(a.value, str)
                                            for a in argumentos):
                niveis.setdefault(argumentos[1].value, set()).add(argumentos[0].value)
    assert niveis, "nenhuma chamada Achado(...) no qc.py — a trava ficaria vacuamente verde"
    return niveis


def _citacoes_do_contrato(texto: str, contrato: dict) -> list:
    """As citações que nomeiam o contrato, como listas de segmentos: identificador simples, caminho
    que começa num nível do contrato, e caminho em `vocabularios.` ou `niveis.`."""
    citacoes = []
    for citacao in _CITACAO.findall(texto):
        if not _CAMINHO_DE_IDENTIFICADORES.fullmatch(citacao):
            continue
        segmentos = citacao.split(".")
        if len(segmentos) == 1 or segmentos[0] in contrato["niveis"] or segmentos[0] in contrato:
            citacoes.append(segmentos)
    return citacoes


def test_skill_tem_frontmatter_e_aponta_o_contrato_do_ledger():
    frontmatter, _corpo = _frontmatter(SKILL_MD)
    assert set(frontmatter) == {"name", "description"}, sorted(frontmatter)
    assert frontmatter["name"] == "er-evidencia"
    descricao = frontmatter["description"]
    assert isinstance(descricao, str) and "USE QUANDO" in descricao and "NÃO use" in descricao, descricao
    assert f"`{CAMINHO_DO_CONTRATO}`" in _texto_da_skill()
    assert CONTRATO.is_file()


def test_todo_arquivo_que_a_skill_cita_existe():
    citados = [citacao for citacao in _CITACAO.findall(_texto_da_skill()) if _ARQUIVO.fullmatch(citacao)]
    assert CAMINHO_DO_CONTRATO in citados
    ausentes = [citado for citado in citados if not (RAIZ / citado).exists()]
    assert not ausentes, f"o SKILL.md cita arquivos que não existem: {ausentes}"


def test_toda_citacao_do_contrato_existe_no_contrato_lido():
    contrato = _contrato()
    termos, codigos = _termos(contrato), set(_niveis_dos_codigos_do_qc())
    inexistentes = []
    citacoes = _citacoes_do_contrato(_texto_da_skill(), contrato)
    assert citacoes, "nenhuma citação do contrato — a trava ficaria vacuamente verde"
    for segmentos in citacoes:
        if segmentos[0] in contrato:
            existe = _resolve(contrato, segmentos)
        elif len(segmentos) == 1:
            existe = segmentos[0] in termos or segmentos[0] in codigos
        else:
            existe = all(segmento in termos for segmento in segmentos[1:])
        if not existe:
            inexistentes.append(".".join(segmentos))
    assert not inexistentes, (
        f"o SKILL.md cita o que o contrato lido não declara (nem o qc.py constrói): {inexistentes}. "
        "Caminho de outro contrato vai com a raiz dele (analise.consenso.ausente), fora desta trava.")


def test_todo_caminho_do_catalogo_citado_existe_no_catalogo():
    catalogo = json.loads(CATALOGO.read_text(encoding="utf-8"))
    citados = [citacao.split(".")[1:] for citacao in _CITACAO.findall(_texto_da_skill())
               if _CAMINHO_DE_IDENTIFICADORES.fullmatch(citacao) and citacao.startswith("catalogo.")]
    assert ["insumos_do_caso"] in citados, "o SKILL.md não aponta o mapa dos insumos do caso"
    assert all(_resolve(catalogo, segmentos) for segmentos in citados), citados


def test_todo_campo_vocabulario_e_flag_do_contrato_e_explicado():
    contrato = _contrato()
    citados = {segmento for segmentos in _citacoes_do_contrato(_texto_da_skill(), contrato) for segmento in segmentos}
    esperados = _campos(contrato) | set(contrato["vocabularios"]) | _flags(contrato)
    assert not esperados - citados, f"o SKILL.md não explica: {sorted(esperados - citados)}"


def test_nenhum_vocabulario_do_contrato_e_copiado_inteiro():
    """A lista fechada só existe no contrato: a doutrina diz onde ela está e explica as flags, e cita
    uma entrada só quando a regra depende dela (a resposta do usuário, o documento fornecido)."""
    contrato = _contrato()
    citados = {segmento for segmentos in _citacoes_do_contrato(_texto_da_skill(), contrato) for segmento in segmentos}
    for nome, vocabulario in contrato["vocabularios"].items():
        entradas = set(vocabulario)
        assert len(entradas) < 2 or not entradas <= citados, f"o SKILL.md copia o vocabulário '{nome}' inteiro"


def test_a_tabela_do_que_o_builder_recusa_cita_cada_codigo_com_o_nivel_do_qc():
    linhas = _texto_da_skill().splitlines()
    cabecalhos = [indice for indice, linha in enumerate(linhas)
                  if tuple(celula.strip() for celula in linha.strip().strip("|").split("|")) == CABECALHO_DA_TABELA_DE_QC]
    assert len(cabecalhos) == 1, f"esperada uma tabela com o cabeçalho {CABECALHO_DA_TABELA_DE_QC}"
    niveis = _niveis_dos_codigos_do_qc()
    corpo = []
    for linha in linhas[cabecalhos[0] + 2:]:
        if not linha.startswith("|"):
            break
        celulas = tuple(celula.strip() for celula in linha.strip().strip("|").split("|"))
        assert len(celulas) == len(CABECALHO_DA_TABELA_DE_QC), linha
        codigo = _CODIGO.fullmatch(celulas[1])
        assert codigo, f"célula de código fora da forma: {celulas[1]!r}"
        corpo.append((codigo.group(1), celulas[2].replace(" ", "_")))
    assert corpo, "a tabela do que o builder recusa está vazia — a trava ficaria vacuamente verde"
    divergentes = [(codigo, nivel, sorted(niveis.get(codigo, ()))) for codigo, nivel in corpo
                   if nivel not in niveis.get(codigo, ())]
    assert not divergentes, f"código ausente do qc.py ou com outro nível: {divergentes}"


def test_agente_existe_com_frontmatter_valido_e_segue_a_skill():
    """Sem `tools`: a lista restringe o agente aos conectores MCP que ela nomeia, e a §6.1 do desenho
    admite qualquer conector sem tornar nenhum obrigatório nem exclusivo — o que muda de máquina para
    máquina não se enumera. O agente herda as ferramentas da sessão e declara só o que nega
    (`disallowedTools`)."""
    frontmatter, corpo = _frontmatter(AGENTE)
    assert set(frontmatter) == {"name", "description", "disallowedTools"}, sorted(frontmatter)
    assert frontmatter["name"] == "pesquisa-evidencia"
    descricao = frontmatter["description"]
    assert isinstance(descricao, str) and "USE QUANDO" in descricao and "NÃO use" in descricao, descricao
    negadas = frontmatter["disallowedTools"]
    assert isinstance(negadas, str) and negadas.strip(), negadas
    assert "`er-evidencia`" in corpo
    assert "ledger/1" in corpo
