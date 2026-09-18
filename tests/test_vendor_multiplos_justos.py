"""Congelamento e integridade do vendor `multiplos-justos` v10.1.

O vendor é read-only por desenho: além do manifest de sha256 verificado aqui, o
próprio `scripts/testes.py` do pacote faz lint semântico dos docs — editar a
metodologia localmente quebra a suíte sem que ninguém precise lembrar da regra.
"""
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SKILL = RAIZ / "skills" / "er-multiplos-justos"
VENDOR = RAIZ / "vendor" / "multiplos-justos"

ARQUIVOS = (
    "CHANGELOG.md",
    "SKILL.md",
    "references/aplicacao.md",
    "references/derivacao.md",
    "references/manutencao.md",
    "references/paper-multiplos-justos-v3.md",
    "scripts/justos.py",
    "scripts/testes.py",
)


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _manifest() -> dict:
    return json.loads((SKILL / "manifest_vendor.json").read_text(encoding="utf-8"))


def test_manifest_declara_a_versao_e_a_raiz():
    man = _manifest()
    assert man["versao"] == "v10.1"
    assert man["raiz_do_pacote"] == "vendor/multiplos-justos"


def test_todo_arquivo_do_manifest_bate_no_disco():
    for rel, sha in _manifest()["arquivos"].items():
        alvo = VENDOR / rel
        assert alvo.is_file(), f"arquivo do manifest ausente no disco: {rel}"
        assert _sha(alvo) == sha, (
            f"arquivo do vendor ALTERADO: {rel} "
            "(se TODOS falharem juntos, suspeite de conversao de EOL fora do git)"
        )


def test_sha_do_motor_pinado_no_proprio_teste():
    """Ancora fora do manifest: editar o motor E regenerar o manifest ainda reprova.

    Mesmo idioma de tests/test_motor_k3.py, que fixa o sha da formula no teste.
    """
    assert _manifest()["arquivos"]["scripts/justos.py"] == (
        "a6a2e692801f351f9d76ef1bf76e97e3130f30c2551e7c08cc99a6009c1912fe"
    )


def test_disco_nao_tem_arquivo_fora_do_manifest():
    no_disco = {
        p.relative_to(VENDOR).as_posix()
        for p in VENDOR.rglob("*")
        if p.is_file() and "__pycache__" not in p.relative_to(VENDOR).parts
    }
    assert no_disco == set(ARQUIVOS), (
        f"conjunto de arquivos do vendor divergiu do congelado: "
        f"sobrando={sorted(no_disco - set(ARQUIVOS))} "
        f"faltando={sorted(set(ARQUIVOS) - no_disco)}"
    )


def test_vendor_sem_bytecode_compilado():
    """.pyc sombreia o .py no import — o sha do fonte casaria com outro codigo rodando."""
    pyc = sorted(p.relative_to(VENDOR).as_posix() for p in VENDOR.rglob("*.pyc"))
    assert pyc == [], f"bytecode dentro da arvore congelada: {pyc}"


def test_manifest_cobre_exatamente_os_arquivos_esperados():
    assert set(_manifest()["arquivos"]) == set(ARQUIVOS)


def _copias_do_motor():
    """Todo `justos.py` do repositório, fora de .git, das raízes de execução e de caches."""
    for raiz, dirs, arquivos in os.walk(RAIZ):
        dirs[:] = [d for d in dirs if d not in {".git", "analises", "node_modules", "__pycache__"}]
        if "justos.py" in arquivos:
            yield (Path(raiz) / "justos.py").resolve()


def test_uma_so_copia_do_motor_e_todo_caminho_de_execucao_aponta_para_ela():
    """Versão única em runtime (migração v10.1): existe UM `justos.py`, e os três caminhos que o
    executam — o subprocesso do wrapper (`motor.RAIZ_VENDOR`) e os dois geradores de paridade,
    que o importam no próprio processo — resolvem para ele. Com o sha do manifest conferido
    acima, nenhuma outra versão do motor é alcançável pelo Fleet."""
    alvo = (VENDOR / "scripts" / "justos.py").resolve()
    assert sorted(_copias_do_motor()) == [alvo]
    sys.path.insert(0, str(RAIZ / "skills" / "er-valuation" / "scripts"))
    import motor
    import vetores_paridade
    import vetores_solver
    assert (motor.RAIZ_VENDOR / "scripts" / "justos.py").resolve() == alvo
    assert (vetores_paridade._VENDOR_SCRIPTS / "justos.py").resolve() == alvo
    assert (vetores_solver._VENDOR_SCRIPTS / "justos.py").resolve() == alvo
    import justos  # já carregado pelos geradores, com a escrita de bytecode desligada
    assert Path(justos.__file__).resolve() == alvo
    assert hasattr(justos, "decomposicao_mm") and hasattr(justos, "nivel_recalculado")


def _ambiente() -> dict:
    """Ambiente dos subprocessos do vendor.

    PYTHONDONTWRITEBYTECODE evita que rodar a suite crie __pycache__ dentro da
    arvore congelada — o vendor nao e mutado nem pelos proprios testes dele.
    PYTHONUTF8 protege a leitura do pipe em locale cp1252 (Windows PT-BR).
    """
    return {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONUTF8": "1"}


def _rodar(*argv: str) -> subprocess.CompletedProcess:
    """Executa o vendor no MESMO interpretador que roda a suite, com utf-8 fixo."""
    return subprocess.run(
        [sys.executable, *argv],
        capture_output=True, text=True, encoding="utf-8",
        env=_ambiente(), timeout=300,
    )


def test_selftest_do_motor_reproduz_as_ancoras():
    r = _rodar(str(VENDOR / "scripts" / "justos.py"), "selftest")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "SELFTEST OK" in r.stdout, r.stdout[-2000:]
    # [v10.1] O próprio motor se identifica: a versão que roda é a do manifest.
    assert _manifest()["versao"] in r.stdout, r.stdout[-2000:]


def test_suite_completa_do_vendor_passa():
    """[v9.31, mantido na v10.1] A suíte completa vira duas invocações frescas, uma por fase.

    `--phase model` roda 'advanced' seguido de 'core' no mesmo processo e termina
    em 'FASE CORE PASSOU.'; `--phase cli` abre os 20+ subprocessos de integração e
    termina em 'FASE CLI PASSOU.'. A antiga invocação única e a string
    'TODOS OS TESTES PASSARAM' não existem mais (ver os dois testes abaixo).
    """
    r_model = _rodar(str(VENDOR / "scripts" / "testes.py"), "--phase", "model")
    assert r_model.returncode == 0, r_model.stdout + r_model.stderr
    assert "FASE CORE PASSOU." in r_model.stdout, r_model.stdout[-2000:]

    r_cli = _rodar(str(VENDOR / "scripts" / "testes.py"), "--phase", "cli")
    assert r_cli.returncode == 0, r_cli.stdout + r_cli.stderr
    assert "FASE CLI PASSOU." in r_cli.stdout, r_cli.stdout[-2000:]


def test_suite_sem_phase_recusa_com_instrucao():
    """[v9.31] Invocação única (contrato antigo) não roda mais nada por padrão.

    Deliberado: a fase CLI abre 20+ subprocessos reais e misturar as duas fases
    numa invocação só arrisca falso negativo por quota de subprocessos do
    ambiente. Sem `--phase`, o script recusa e imprime as duas invocações
    corretas em vez de silenciosamente rodar (ou pior, rodar só parte).
    """
    r = _rodar(str(VENDOR / "scripts" / "testes.py"))
    saida = r.stdout + r.stderr
    assert r.returncode == 2, saida
    assert "--phase model" in saida and "--phase cli" in saida, saida


def test_tv_ausente_sai_com_json_de_parada_do_gate_1():
    """[v9.31] Ausência de --tv é produto, não acidente: JSON de parada citando o
    Gate 1 (rc=2), não mais usage cru do argparse. O rc continua não-zero, então
    `motor.MotorFalhou` do wrapper continua sendo levantado sem nenhuma mudança
    lá — este teste só fixa o contrato novo do vendor.
    """
    r = _rodar(str(VENDOR / "scripts" / "justos.py"), "ev")
    assert r.returncode == 2, r.stdout + r.stderr
    parada = json.loads(r.stdout)
    assert "Gate 1" in parada["erro"], r.stdout


DOCS_DO_VENDOR = tuple(a for a in ARQUIVOS if a.endswith(".md") and a != "CHANGELOG.md")
PROSCRITOS = ("g = RiR", "EV/EBITDA = EV/NOPAT", "FCFF = NOPAT", "P/VP = P/L")


def test_indice_aponta_para_todo_arquivo_do_vendor():
    idx = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    assert idx.startswith("---"), "SKILL.md sem frontmatter"
    assert "name: er-multiplos-justos" in idx
    for rel in ARQUIVOS:
        assert f"vendor/multiplos-justos/{rel}" in idx, f"o indice nao aponta para {rel}"
    assert "manifest_vendor.json" in idx


def test_indice_nao_reproduz_metodologia():
    idx = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    for expr in PROSCRITOS:
        assert expr not in idx, f"formula da metodologia reproduzida no indice: {expr}"
    for rel in DOCS_DO_VENDOR:
        for linha in (VENDOR / rel).read_text(encoding="utf-8").splitlines():
            trecho = linha.strip()
            if len(trecho) >= 60:
                assert trecho not in idx, f"copia literal de {rel}: {trecho[:60]}..."


def test_nenhum_skill_md_aninhado_sob_skills():
    """Invariante estrutural: nada sob skills/ tem SKILL.md aninhado.

    Um SKILL.md mais fundo depende da profundidade de varredura do loader para
    NAO ser descoberto — premissa que o repositorio nao controla. A regra aqui
    e mais forte e verificavel: sob skills/, SKILL.md so existe em skills/<nome>/.
    """
    todos = {p.resolve() for p in (RAIZ / "skills").rglob("SKILL.md")}
    de_topo = {p.resolve() for p in (RAIZ / "skills").glob("*/SKILL.md")}
    aninhados = sorted(p.relative_to(RAIZ).as_posix() for p in todos - de_topo)
    assert aninhados == [], (
        f"SKILL.md aninhado sob skills/ — risco de descoberta e colisao de nome: {aninhados}"
    )


def test_pacote_vendorizado_vive_fora_de_skills():
    """O pacote declara `name: multiplos-justos` e colidiria com a skill standalone."""
    assert VENDOR.is_dir(), f"pacote vendorizado nao encontrado em {VENDOR}"
    assert (RAIZ / "skills") not in VENDOR.parents, (
        "o pacote vendorizado esta sob skills/ — pode ser descoberto como skill"
    )
    assert "name: multiplos-justos" in (VENDOR / "SKILL.md").read_text(encoding="utf-8"), (
        "premissa do teste mudou: o pacote nao declara mais esse nome"
    )
