"""E3 mecanizada (fatia 5A, item 5, Task 3): o relatório nunca importa a
integração nem o vendor, e nenhum literal de código nomeia a integração
fora da constante `ASSETS_DA_INTEGRACAO`.

Ver docs/superpowers/plans/2026-09-11-v4-item5a-contratos-builder.md,
seção "Task 3", "Teste de fronteira". Os dois testes abaixo varrem só
`skills/er-relatorio/scripts/` — testes (`tests/relatorio_apoio.py`) não
são a camada do relatório, e podem importar `er-valuation` livremente.
"""

import ast
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SCRIPTS = RAIZ / "skills" / "er-relatorio" / "scripts"
PROIBIDOS = {"caso", "motor", "avaliar", "reversa", "sensibilidades", "sotp", "ponte", "diagnosticos",
             "justos", "vetores_paridade", "vetores_solver"}


def test_relatorio_nao_importa_a_integracao_nem_o_vendor():
    """E3: o relatorio consome contratos (dados), nunca codigo da integracao ou da metodologia.
    E isto que torna a troca da multiplos-justos um trabalho da camada de integracao."""
    for arquivo in SCRIPTS.glob("*.py"):
        for no in ast.walk(ast.parse(arquivo.read_text(encoding="utf-8"))):
            nomes = []
            if isinstance(no, ast.Import):
                nomes = [a.name.split(".")[0] for a in no.names]
            elif isinstance(no, ast.ImportFrom) and no.module:
                nomes = [no.module.split(".")[0]]
            assert not (set(nomes) & PROIBIDOS), f"{arquivo.name} importa {set(nomes) & PROIBIDOS}"


def test_caminho_da_integracao_so_na_constante_de_assets():
    """So literais de CODIGO contam: docstrings e comentarios podem falar da integracao a vontade."""
    alvos = ("er-valuation", "multiplos-justos", "vendor")
    for arquivo in SCRIPTS.glob("*.py"):
        arvore = ast.parse(arquivo.read_text(encoding="utf-8"))
        permitidos = set()
        for no in ast.walk(arvore):
            if isinstance(no, ast.Assign) and any(
                    isinstance(t, ast.Name) and t.id == "ASSETS_DA_INTEGRACAO" for t in no.targets):
                permitidos |= {id(c) for c in ast.walk(no) if isinstance(c, ast.Constant)}
        docstrings = {id(n.body[0].value) for n in ast.walk(arvore)
                      if isinstance(n, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                      and n.body and isinstance(n.body[0], ast.Expr)
                      and isinstance(n.body[0].value, ast.Constant)}
        for no in ast.walk(arvore):
            if (isinstance(no, ast.Constant) and isinstance(no.value, str)
                    and id(no) not in permitidos | docstrings):
                assert not any(a in no.value for a in alvos), (arquivo.name, no.value)


def test_scripts_do_relatorio_existem():
    """Guarda-corpo: se o diretório estiver vazio ou os dois testes acima
    varrerem zero arquivo, eles passam vacuamente e escondem uma regressão
    grave (skill inteira apagada). Falha alto e nomeado nesse caso."""
    arquivos = sorted(p.name for p in SCRIPTS.glob("*.py"))
    esperados = {"entrega.py", "placeholders.py", "qc.py", "builder.py"}
    faltando = esperados - set(arquivos)
    assert not faltando, f"scripts esperados ausentes em {SCRIPTS}: {faltando}"
