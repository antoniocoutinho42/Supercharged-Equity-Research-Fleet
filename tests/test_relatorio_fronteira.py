"""E3 mecanizada (fatia 5A, item 5, Task 3; endurecida na onda de correção
da revisão final, achado F4/B5): o relatório nunca importa a integração nem
o vendor, nunca importa por um caminho indireto (`importlib`/`__import__`/
`exec`/`eval`), nenhum literal de código (nem montado por concatenação)
nomeia a integração fora da constante `ASSETS_DA_INTEGRACAO`, e nenhum
asset do relatório é uma cópia (por conteúdo, não por nome) de um asset da
integração ou do vendor.

Ver docs/superpowers/plans/2026-09-11-v4-item5a-contratos-builder.md,
seção "Task 3", "Teste de fronteira", e `.superpowers/sdd/review-5a-final.md`
(achado F4) para as seis fugas que motivaram o endurecimento abaixo. Os
testes abaixo varrem só `skills/er-relatorio/scripts/`/`skills/er-relatorio/
assets/` — testes (`tests/relatorio_apoio.py`) não são a camada do
relatório, e podem importar `er-valuation` livremente.
"""

import ast
import hashlib
import json
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SCRIPTS = RAIZ / "skills" / "er-relatorio" / "scripts"
ASSETS_RELATORIO = RAIZ / "skills" / "er-relatorio" / "assets"
INTEGRACAO_SCRIPTS = RAIZ / "skills" / "er-valuation" / "scripts"
INTEGRACAO_ASSETS = RAIZ / "skills" / "er-valuation" / "assets"
# Fatia 5E, Task 2: o contrato `ledger/1` é do `er-evidencia` (§3.2), e o relatório o lê pela
# mesma constante dos assets externos — nunca por um literal fora dela, nunca por uma cópia.
EVIDENCIA_ASSETS = RAIZ / "skills" / "er-evidencia" / "assets"
VENDOR = RAIZ / "vendor" / "multiplos-justos"

# B5 (achado F4, fuga 5 -- "import de um módulo da integração que não está
# na lista"): PROIBIDOS é DERIVADO dos arquivos que de fato existem em
# skills/er-valuation/scripts/ e vendor/multiplos-justos/scripts/, recomputado
# a cada rodada da suíte -- não uma lista estática que alguém precisa lembrar
# de atualizar. Um módulo novo da integração (ex.: a fachada do espelho que a
# 5C vai acrescentar) fica proibido automaticamente, no instante em que o
# arquivo passa a existir, sem editar este teste.
PROIBIDOS: frozenset = frozenset(
    {p.stem for p in INTEGRACAO_SCRIPTS.glob("*.py")}
    | {p.stem for p in VENDOR.glob("scripts/*.py")}
)

# B5 (achado F4, fuga 3 -- "importlib.import_module('caso')"/"__import__('motor')"):
# qualquer um destes quatro nomes, em QUALQUER posição sintática (chamada,
# referência solta, `import importlib`), é proibido em scripts do relatório
# -- são exatamente os mecanismos que tornam um import indireto possível,
# fora do alcance da checagem de `ast.Import`/`ast.ImportFrom` por nome.
NOMES_DE_IMPORT_INDIRETO_PROIBIDOS: frozenset = frozenset({"importlib", "__import__", "exec", "eval"})


def _dobrar_constante(no: ast.AST) -> str | None:
    """Tenta dobrar `no` numa única string: um `ast.Constant` de texto, ou
    uma cadeia de `ast.BinOp` (operador '+') cujos dois lados dobram para
    texto -- a forma exata que 'er-' + 'valuation' assume na AST (achado F4,
    fuga 4: "caminho montado por fragmentos"). Nenhum dos fragmentos
    individuais ('er-', 'valuation') contém 'er-valuation' -- só o valor
    DOBRADO contém; sem esta função, concatenar em dois pedaços bastava para
    escapar da varredura por literal. Devolve `None` quando `no` não é
    nenhuma dessas formas (não foldável estaticamente -- ex.: um dos lados é
    uma variável ou chamada de função)."""
    if isinstance(no, ast.Constant) and isinstance(no.value, str):
        return no.value
    if isinstance(no, ast.BinOp) and isinstance(no.op, ast.Add):
        esquerda = _dobrar_constante(no.left)
        direita = _dobrar_constante(no.right)
        if esquerda is not None and direita is not None:
            return esquerda + direita
    return None


def test_relatorio_nao_importa_a_integracao_nem_o_vendor():
    """E3: o relatorio consome contratos (dados), nunca codigo da integracao ou da metodologia.
    E isto que torna a troca da multiplos-justos um trabalho da camada de integracao.

    B5: `rglob` (não `glob`) -- um módulo dentro de um subpacote futuro
    (ex.: `scripts/graficos/svg.py`, achado F4 fuga 2) tem de ser varrido
    igual a um módulo direto em `scripts/`."""
    for arquivo in SCRIPTS.rglob("*.py"):
        for no in ast.walk(ast.parse(arquivo.read_text(encoding="utf-8"))):
            nomes = []
            if isinstance(no, ast.Import):
                nomes = [a.name.split(".")[0] for a in no.names]
            elif isinstance(no, ast.ImportFrom) and no.module:
                nomes = [no.module.split(".")[0]]
            assert not (set(nomes) & PROIBIDOS), f"{arquivo.name} importa {set(nomes) & PROIBIDOS}"


def test_relatorio_nao_usa_import_indireto():
    """B5 (achado F4, fuga 3): `importlib.import_module(...)` e
    `__import__(...)` contornam a checagem de `ast.Import`/`ast.ImportFrom`
    acima -- nenhum dos dois é uma dessas duas formas sintáticas. `exec`/
    `eval` são o mesmo problema por outra porta (código arbitrário, inclusive
    um `import` dentro de uma string). Varredura por NOME (`ast.Name` E o
    módulo de `ast.Import`), não por padrão de chamada -- pega tanto
    `importlib.import_module("caso")` quanto `import importlib` sozinho,
    e uma referência solta (`x = eval`) sem precisar reconhecer toda forma
    de chamada possível."""
    for arquivo in SCRIPTS.rglob("*.py"):
        arvore = ast.parse(arquivo.read_text(encoding="utf-8"))
        for no in ast.walk(arvore):
            nome = None
            if isinstance(no, ast.Name):
                nome = no.id
            elif isinstance(no, (ast.Import, ast.ImportFrom)):
                modulos = [a.name.split(".")[0] for a in no.names] if isinstance(no, ast.Import) \
                    else ([no.module.split(".")[0]] if no.module else [])
                for modulo in modulos:
                    assert modulo not in NOMES_DE_IMPORT_INDIRETO_PROIBIDOS, \
                        f"{arquivo.name} importa '{modulo}'"
                continue
            if nome is not None:
                assert nome not in NOMES_DE_IMPORT_INDIRETO_PROIBIDOS, \
                    f"{arquivo.name} referencia '{nome}'"


def test_caminho_da_integracao_so_na_constante_de_assets():
    """So literais de CODIGO contam: docstrings e comentarios podem falar da
    integracao a vontade.

    B5 (achado F4, fugas 2 e 4): `rglob` (subpacotes futuros) e, além de
    cada `ast.Constant` isolado, toda cadeia de concatenação (`ast.BinOp`
    '+') é DOBRADA antes da checagem -- ver `_dobrar_constante`. Um literal
    (ou uma cadeia dobrada) só escapa da checagem quando está dentro da
    própria expressão de `ASSETS_DA_INTEGRACAO` ou é uma docstring."""
    alvos = ("er-valuation", "er-evidencia", "multiplos-justos", "vendor")
    for arquivo in SCRIPTS.rglob("*.py"):
        arvore = ast.parse(arquivo.read_text(encoding="utf-8"))
        permitidos = set()
        for no in ast.walk(arvore):
            if isinstance(no, ast.Assign) and any(
                    isinstance(t, ast.Name) and t.id == "ASSETS_DA_INTEGRACAO" for t in no.targets):
                permitidos |= {id(c) for c in ast.walk(no) if isinstance(c, (ast.Constant, ast.BinOp))}
        docstrings = {id(n.body[0].value) for n in ast.walk(arvore)
                      if isinstance(n, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                      and n.body and isinstance(n.body[0], ast.Expr)
                      and isinstance(n.body[0].value, ast.Constant)}
        isentos = permitidos | docstrings

        for no in ast.walk(arvore):
            if (isinstance(no, ast.Constant) and isinstance(no.value, str)
                    and id(no) not in isentos):
                assert not any(a in no.value for a in alvos), (arquivo.name, no.value)
            if isinstance(no, ast.BinOp) and id(no) not in isentos:
                dobrado = _dobrar_constante(no)
                if dobrado is not None:
                    assert not any(a in dobrado for a in alvos), (arquivo.name, dobrado)


def _sha256_de(caminho: Path) -> str:
    return hashlib.sha256(caminho.read_bytes()).hexdigest()


def test_nenhum_asset_do_relatorio_espelha_um_asset_da_integracao_ou_do_vendor():
    """B5 (achado F4, fuga 6 -- cópia de `motor_espelho.js` em
    `skills/er-relatorio/assets/`): um asset copiado não é um `import` nem
    um literal de código -- nenhuma das checagens acima o alcança. Comparar
    por SHA-256 (não por nome de arquivo) pega a cópia mesmo renomeada.

    Fatia 5E, Task 2: os assets do `er-evidencia` entram na mesma varredura — uma cópia do
    contrato do ledger dentro do relatório seria o vocabulário de evidência mantido em dois
    lugares, e a leitura pela constante deixaria de ser a única."""
    evidencia = [p for p in EVIDENCIA_ASSETS.rglob("*") if p.is_file()]
    assert evidencia, f"nenhum asset em {EVIDENCIA_ASSETS} — a varredura do er-evidencia ficaria vacuamente verde"
    fontes = list(INTEGRACAO_ASSETS.rglob("*")) + evidencia + list(VENDOR.rglob("*"))
    hashes_da_integracao = {_sha256_de(p): p for p in fontes if p.is_file()}

    for arquivo in ASSETS_RELATORIO.rglob("*"):
        if not arquivo.is_file():
            continue
        origem = hashes_da_integracao.get(_sha256_de(arquivo))
        assert origem is None, f"{arquivo} tem o mesmo conteúdo de {origem} (integração/vendor)"


# --------------------------------------------------------------------------
# Fatia 5C, Task 2 — a mesma fronteira, agora para o LABORATÓRIO.
#
# `skills/er-relatorio/assets/laboratorio.js` é só interface: lê os campos que
# `render.py` montou, chama `FachadaEspelho.avaliarCaso` e escreve o resultado
# na tela. Nenhuma fórmula de valuation, nenhum limiar, nenhum nome de
# premissa. As checagens acima não o alcançam — não é um `import`, não é um
# literal de caminho e não é uma cópia byte a byte —, e é exatamente por isso
# que a metodologia poderia vazar para lá sem nada reprovar.
#
# O vocabulário proibido é DERIVADO, como `PROIBIDOS` acima: os identificadores
# que o espelho do núcleo declara no topo (o motor propriamente dito) mais o
# vocabulário de premissas e de opções que o catálogo de apresentação publica.
# Uma premissa nova, uma opção nova ou uma função nova do núcleo entram na
# trava no instante em que passam a existir, sem editar este arquivo.
# --------------------------------------------------------------------------

LABORATORIO = ASSETS_RELATORIO / "laboratorio.js"
ESPELHO_DO_NUCLEO = INTEGRACAO_ASSETS / "motor_espelho.js"
CATALOGO_DE_APRESENTACAO = INTEGRACAO_ASSETS / "catalogo_apresentacao.json"

# Literais de texto e comentários, nesta ordem de alternância: o primeiro
# casamento ganha, então um `//` DENTRO de uma string é reconhecido como parte
# da string e nunca como início de comentário.
_LITERAIS_E_COMENTARIOS = re.compile(
    r'"(?:[^"\\\n]|\\.)*"'
    r"|'(?:[^'\\\n]|\\.)*'"
    r"|`(?:[^`\\]|\\.)*`"
    r"|/\*.*?\*/"
    r"|//[^\n]*",
    re.DOTALL,
)


def _codigo_js(texto: str) -> str:
    """`texto` com os comentários trocados por espaço e os literais de string
    PRESERVADOS -- mesma fronteira que `test_caminho_da_integracao_so_na_
    constante_de_assets` já aplica do lado Python ("só literais de CÓDIGO
    contam: docstrings e comentários podem falar da integração à vontade").
    Preservar as strings é o ponto: um `if (nome === "wacc")` é exatamente a
    forma que o vazamento assumiria, e ela tem de continuar visível."""
    return _LITERAIS_E_COMENTARIOS.sub(
        lambda m: " " if m.group(0).startswith("/") else m.group(0), texto)


def _vocabulario_do_nucleo() -> frozenset:
    espelho = ESPELHO_DO_NUCLEO.read_text(encoding="utf-8")
    nomes = set(re.findall(r"^(?:const|let|var|function)\s+([A-Za-z_$][\w$]*)", espelho, re.M))
    catalogo = json.loads(CATALOGO_DE_APRESENTACAO.read_text(encoding="utf-8"))
    for premissas in catalogo["premissas"].values():
        nomes |= set(premissas)
        for info in premissas.values():
            nomes |= set(info.get("opcoes", []))
    return frozenset(nomes)


def test_o_laboratorio_nao_carrega_uma_linha_de_metodologia():
    """E3 mecanizada no arquivo em que ela é mais fácil de violar: quem edita
    o laboratório está olhando para números de valuation, e a tentação de
    tratar uma premissa "só desta vez" é permanente. Varredura sensível a
    caixa (os nomes do contrato são minúsculos; identificadores de JS
    distinguem caixa) e por fronteira de identificador -- `da` não casa dentro
    de `data-laboratorio-premissa`, e `pe` não casa dentro de `especificacao`.
    """
    vocabulario = _vocabulario_do_nucleo()
    assert len(vocabulario) > 50, "vocabulário derivado pequeno demais — trava vacuamente verde"

    codigo = _codigo_js(LABORATORIO.read_text(encoding="utf-8"))
    assert "FleetLaboratorio" in codigo, "a varredura comeu o código do módulo"

    achados = sorted(
        nome for nome in vocabulario
        if re.search(r"(?<![\w$])" + re.escape(nome) + r"(?![\w$])", codigo)
    )
    assert not achados, (
        f"{LABORATORIO.name} nomeia metodologia: {achados}. O laboratório lê campos, "
        "chama a fachada e escreve na tela — quem conhece premissa, limiar e fórmula é "
        "a camada de integração."
    )


def test_o_laboratorio_nao_conhece_a_integracao_por_caminho_nem_por_copia():
    """As duas outras portas do mesmo vazamento: o módulo não pode localizar a
    integração por caminho (ele é embutido no HTML; no browser não existe
    sistema de arquivos), e não pode virar uma cópia do espelho — que
    `test_nenhum_asset_do_relatorio_espelha_um_asset_da_integracao_ou_do_vendor`
    já reprova por sha256, e que continua valendo para este arquivo."""
    texto = LABORATORIO.read_text(encoding="utf-8")
    for alvo in ("er-valuation", "multiplos-justos", "vendor"):
        assert alvo not in texto, f"{LABORATORIO.name} nomeia '{alvo}'"
    assert not re.search(r"""\brequire\s*\(""", texto), "o laboratório não roda em node"
    assert not re.search(r"^\s*import\s", texto, re.M), "import ES6 no laboratório"


def test_scripts_do_relatorio_existem():
    """Guarda-corpo: se o diretório estiver vazio ou os testes acima
    varrerem zero arquivo, eles passam vacuamente e escondem uma regressão
    grave (skill inteira apagada). Falha alto e nomeado nesse caso.

    B16: `render.py` (Task 4) estava ausente desta lista -- a checagem
    passava mesmo se o módulo das três abas fosse apagado."""
    arquivos = sorted(p.name for p in SCRIPTS.glob("*.py"))
    esperados = {"entrega.py", "placeholders.py", "qc.py", "builder.py", "render.py"}
    faltando = esperados - set(arquivos)
    assert not faltando, f"scripts esperados ausentes em {SCRIPTS}: {faltando}"
