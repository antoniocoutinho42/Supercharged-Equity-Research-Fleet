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
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SCRIPTS = RAIZ / "skills" / "er-relatorio" / "scripts"
ASSETS_RELATORIO = RAIZ / "skills" / "er-relatorio" / "assets"
INTEGRACAO_SCRIPTS = RAIZ / "skills" / "er-valuation" / "scripts"
INTEGRACAO_ASSETS = RAIZ / "skills" / "er-valuation" / "assets"
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
    alvos = ("er-valuation", "multiplos-justos", "vendor")
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
    por SHA-256 (não por nome de arquivo) pega a cópia mesmo renomeada."""
    fontes = list(INTEGRACAO_ASSETS.rglob("*")) + list(VENDOR.rglob("*"))
    hashes_da_integracao = {_sha256_de(p): p for p in fontes if p.is_file()}

    for arquivo in ASSETS_RELATORIO.rglob("*"):
        if not arquivo.is_file():
            continue
        origem = hashes_da_integracao.get(_sha256_de(arquivo))
        assert origem is None, f"{arquivo} tem o mesmo conteúdo de {origem} (integração/vendor)"


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
