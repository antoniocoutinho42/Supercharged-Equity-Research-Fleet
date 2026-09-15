"""A tabela que dá dono a todo item da §11 (fatia 5E, item 5, Task 3, D8).

Ver docs/superpowers/plans/2026-09-14-v4-item5e-evidencia.md, D8. A §11 do desenho lista o que o QC
impõe em três níveis; a seção "Cobertura da §11" do `skills/er-relatorio/SKILL.md` diz, item a item,
como cada um é garantido: por código de QC, por mecanismo fora do QC (o gate do caso, a CI, o badge
do laboratório) ou por pendência com dono (`item 6` ou `item 8`) e razão. Uma segunda tabela
lista os códigos de QC que servem a outras seções do desenho.

A trava lê as três fontes — o desenho, as duas tabelas e o `qc.py` — e confere que:
- os itens de cada nível são os do desenho, com espaço e crase normalizados;
- todo código citado existe no `qc.py` com o nível da linha e tem mensagem em todo dicionário;
- todo código que o `qc.py` constrói aparece numa das duas tabelas;
- toda linha tem ao menos uma garantia, e toda pendência tem dono permitido e razão.

Os códigos do `qc.py` saem da AST — toda chamada `Achado(<nível>, <código>, ...)` —, nunca de uma
lista escrita aqui: um código novo entra na trava no instante em que passa a ser construído.
"""

import ast
import json
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DESENHO = RAIZ / "docs" / "desenho-arquitetura-v4.md"
SKILL_MD = RAIZ / "skills" / "er-relatorio" / "SKILL.md"
QC_PY = RAIZ / "skills" / "er-relatorio" / "scripts" / "qc.py"
DIR_I18N = RAIZ / "skills" / "er-relatorio" / "assets" / "i18n"

TITULO_DA_SECAO = "## Cobertura da §11"
CABECALHO_DA_COBERTURA = ("Nível", "Item da §11", "Códigos de QC", "Fora do QC", "Pendência")
CABECALHO_DOS_DE_FORA = ("Código", "Nível", "Onde o desenho o pede")
NIVEIS = frozenset({"HARD_FAIL", "REQUIRED_DISCLOSURE", "QUALITY_WARNING"})
# Fatia 5F, Task 4: as três pendências da 5F viraram códigos de QC, e `5F` saiu dos donos.
DONOS_PERMITIDOS = frozenset({"item 6", "item 8"})
SEM_GARANTIA = "—"

_CODIGO_CITADO = re.compile(r"`([a-z_]+)`")
_PENDENCIA = re.compile(r"\*\*(?P<dono>[^*]+)\*\*: (?P<razao>\S.*)")
# Um nível da §11: o título em negrito ("**HARD FAIL — não emite:**") e o parágrafo que o segue, até a
# linha em branco, com os itens separados por "·".
_NIVEL_DO_DESENHO = re.compile(
    r"^\*\*(HARD FAIL|REQUIRED DISCLOSURE|QUALITY WARNING) — [^\n]*\*\*\n((?:[^\n]+\n)+)", re.M)


def _normalizado(texto: str) -> str:
    """Espaço e crase normalizados: o desenho quebra a linha no meio de um item e marca `selftest`
    com crase."""
    return " ".join(texto.replace("`", "").split())


def _nivel(texto: str) -> str:
    """'HARD FAIL', como o desenho e as tabelas escrevem, é 'HARD_FAIL' no `qc.py`."""
    return texto.strip().replace(" ", "_")


def _itens_da_secao_11() -> dict:
    texto = DESENHO.read_text(encoding="utf-8")
    secao = texto.split("\n## 11. ", 1)[1].split("\n## 12. ", 1)[0]
    return {_nivel(nivel): [_normalizado(item) for item in _normalizado(paragrafo).rstrip(".").split("·")]
            for nivel, paragrafo in _NIVEL_DO_DESENHO.findall(secao)}


def _secao_da_cobertura() -> str:
    texto = SKILL_MD.read_text(encoding="utf-8")
    assert TITULO_DA_SECAO + "\n" in texto, f"o SKILL.md não tem a seção '{TITULO_DA_SECAO}'"
    return texto.split(TITULO_DA_SECAO + "\n", 1)[1].split("\n## ", 1)[0]


def _celulas(linha: str) -> tuple:
    return tuple(celula.strip() for celula in linha.strip().strip("|").split("|"))


def _tabela(cabecalho: tuple) -> list:
    """As linhas da tabela da seção da cobertura cujo cabeçalho é `cabecalho`, como dicts."""
    linhas = _secao_da_cobertura().splitlines()
    inicios = [indice for indice, linha in enumerate(linhas) if linha.startswith("|") and _celulas(linha) == cabecalho]
    assert len(inicios) == 1, f"esperada exatamente uma tabela com o cabeçalho {cabecalho}, vieram {len(inicios)}"
    corpo = []
    for linha in linhas[inicios[0] + 2:]:
        if not linha.startswith("|"):
            break
        celulas = _celulas(linha)
        assert len(celulas) == len(cabecalho), f"linha com {len(celulas)} células: {linha}"
        corpo.append(dict(zip(cabecalho, celulas)))
    assert corpo, f"a tabela {cabecalho} está vazia — a trava ficaria vacuamente verde"
    return corpo


def _codigos_da_celula(celula: str) -> list:
    """Os códigos de uma célula de códigos: `—`, ou códigos entre crases separados por vírgula — nada
    mais, para que um texto solto na coluna nunca passe por código citado."""
    if celula == SEM_GARANTIA:
        return []
    codigos = _CODIGO_CITADO.findall(celula)
    assert codigos and ", ".join(f"`{codigo}`" for codigo in codigos) == celula, (
        f"célula de códigos fora da forma: {celula!r}")
    return codigos


def _citados() -> list:
    """`(nível, código)` de todo código citado nas duas tabelas, na ordem em que aparecem."""
    citados = [(_nivel(linha["Nível"]), codigo) for linha in _tabela(CABECALHO_DA_COBERTURA)
               for codigo in _codigos_da_celula(linha["Códigos de QC"])]
    for linha in _tabela(CABECALHO_DOS_DE_FORA):
        codigos = _codigos_da_celula(linha["Código"])
        assert len(codigos) == 1, f"a tabela dos códigos de fora da §11 cita um código por linha: {linha}"
        citados.append((_nivel(linha["Nível"]), codigos[0]))
    return citados


def _niveis_dos_codigos_do_qc() -> dict:
    """`{código: {nível}}` de toda chamada `Achado(...)` do `qc.py`."""
    chamadas = [no for no in ast.walk(ast.parse(QC_PY.read_text(encoding="utf-8")))
                if isinstance(no, ast.Call) and isinstance(no.func, ast.Name) and no.func.id == "Achado"]
    assert chamadas, "nenhuma chamada Achado(...) no qc.py — a trava ficaria vacuamente verde"
    niveis: dict = {}
    for chamada in chamadas:
        argumentos = chamada.args[:2]
        assert len(argumentos) == 2 and all(
            isinstance(argumento, ast.Constant) and isinstance(argumento.value, str) for argumento in argumentos), (
            f"qc.py:{chamada.lineno}: Achado sem nível e código literais — esta trava não saberia ler o código")
        nivel, codigo = (argumento.value for argumento in argumentos)
        niveis.setdefault(codigo, set()).add(nivel)
    return niveis


def test_os_itens_de_cada_nivel_da_tabela_sao_os_da_secao_11_do_desenho():
    desenho = _itens_da_secao_11()
    assert set(desenho) == NIVEIS and all(desenho.values()), desenho

    tabela: dict = {}
    for linha in _tabela(CABECALHO_DA_COBERTURA):
        tabela.setdefault(_nivel(linha["Nível"]), []).append(_normalizado(linha["Item da §11"]))
    assert tabela == desenho


def test_todo_codigo_citado_existe_no_qc_com_o_nivel_da_linha_e_tem_mensagem_em_todo_dicionario():
    niveis = _niveis_dos_codigos_do_qc()
    dicionarios = {caminho.name: json.loads(caminho.read_text(encoding="utf-8"))
                   for caminho in sorted(DIR_I18N.glob("*.json"))}
    assert dicionarios, f"nenhum dicionário em {DIR_I18N}"
    citados = _citados()

    fora_do_qc = sorted({(nivel, codigo) for nivel, codigo in citados if nivel not in niveis.get(codigo, set())})
    sem_mensagem = sorted({(nome, codigo) for _nivel_citado, codigo in citados
                           for nome, dicionario in dicionarios.items() if codigo not in dicionario["qc"]})
    assert (fora_do_qc, sem_mensagem) == ([], [])


def test_todo_codigo_que_o_qc_constroi_aparece_numa_das_duas_tabelas():
    citados = {codigo for _nivel_citado, codigo in _citados()}
    assert sorted(set(_niveis_dos_codigos_do_qc()) - citados) == []


def test_toda_linha_tem_uma_garantia_e_toda_pendencia_tem_dono_permitido_e_razao():
    problemas = []
    for linha in _tabela(CABECALHO_DA_COBERTURA):
        item = linha["Item da §11"]
        if all(linha[coluna] == SEM_GARANTIA for coluna in ("Códigos de QC", "Fora do QC", "Pendência")):
            problemas.append((item, "nenhuma garantia: nem código, nem mecanismo, nem pendência com dono"))
        pendencia = linha["Pendência"]
        if pendencia != SEM_GARANTIA:
            forma = _PENDENCIA.fullmatch(pendencia)
            if forma is None or forma["dono"] not in DONOS_PERMITIDOS:
                problemas.append((item, pendencia))
    assert problemas == []
