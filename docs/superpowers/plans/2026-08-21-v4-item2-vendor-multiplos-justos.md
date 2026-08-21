# Vendor congelado `multiplos-justos` v9.24 — Plano de Implementação (item 2 do desenho v4)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Trazer a skill `multiplos-justos` v9.24 para dentro do plugin como cópia congelada,
verificável por sha256, com a suíte da metodologia rodando no CI e um `SKILL.md` que é índice —
nunca paráfrase — da metodologia canônica.

**Architecture:** O pacote da skill é copiado byte a byte para
`skills/er-multiplos-justos/vendor/multiplos-justos/`, preservando a estrutura original de
diretórios (o pacote a exige: `scripts/testes.py` resolve `SKILL.md` e `references/*.md` a partir
do pai de `scripts/`). Um `manifest_vendor.json` registra a versão e o sha256 de cada arquivo. Um
teste pytest confronta o manifest com o disco, roda `selftest` e a suíte completa por subprocess, e
verifica que o `SKILL.md` do fleet não reproduz metodologia. O congelamento é auto-reforçado: além
do manifest, o próprio `testes.py` do vendor faz lint semântico dos docs, então editar a metodologia
localmente quebra a suíte por desenho.

**Tech Stack:** Python 3.12+ (stdlib pura — o vendor não tem dependências), pytest, GitHub Actions.

## Global Constraints

- **Fonte de verdade:** `docs/desenho-arquitetura-v4.md`. Nenhuma decisão de produto é reaberta aqui.
- **Vendor read-only** (regra inviolável 10): alteração local quebra a suíte, por desenho.
- **Zero paráfrase de metodologia fora do vendor** (Seção 3.2 do desenho): o `SKILL.md` do fleet diz
  o que existe, onde está, qual hash e quando ler cada arquivo.
- **A matemática de valuation vem do motor congelado** (regra inviolável 1): nenhum cálculo novo em
  Python ou JS neste item.
- **EOL congelado:** todo path do vendor entra em `.gitattributes` com `-text`. Conversão de EOL
  quebra os sha256.
- **Python 3.12+**, `pytest` como runner (`pyproject.toml` já aponta `testpaths = ["tests"]`).
- **Nada de rede** em nenhum teste.
- **Commits:** conventional commits em PT-BR, seguindo o estilo do repositório
  (`feat(escopo): ...`, `test(escopo): ...`, `chore(escopo): ...`), com o trailer
  `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`.
- **Branch:** `feat/v4-multiplos-justos` (já criado; `main` permanece na v3 funcional).
- **O legado v3/K3 não é tocado neste item.** `skills/er-motor-k3` e seus testes continuam
  passando; a remoção é o item 10 do desenho.

## File Structure

| Arquivo | Responsabilidade |
|---|---|
| `skills/er-multiplos-justos/vendor/multiplos-justos/**` (7 arquivos) | Cópia congelada, byte a byte, do pacote v9.24. Nunca editada |
| `skills/er-multiplos-justos/manifest_vendor.json` | Identidade da cópia: versão, origem, sha256 por arquivo, comandos da suíte, receita de regeneração |
| `skills/er-multiplos-justos/SKILL.md` | Índice do fleet: o que existe, onde, qual hash, quando ler. Sem metodologia |
| `tests/test_vendor_multiplos_justos.py` | Congelamento (manifest × disco), suíte do vendor por subprocess, e as travas do índice |
| `.gitattributes` | `-text` no path do vendor |
| `.gitignore` | Ignora arquivos temporários do Word (`~$*`), que podem cair dentro do vendor e corromper o congelamento |
| `.github/workflows/ci.yml` | Passo nomeado da suíte da metodologia, antes do pytest |

**Layout do vendor — a profundidade é deliberada:**

```
skills/er-multiplos-justos/
├── SKILL.md                       <- índice do fleet (name: er-multiplos-justos)
├── manifest_vendor.json
└── vendor/
    └── multiplos-justos/          <- RAIZ DO PACOTE (testes.py resolve a partir daqui)
        ├── SKILL.md               <- metodologia canônica (name: multiplos-justos)
        ├── CHANGELOG.md
        ├── references/{aplicacao,derivacao,paper-multiplos-justos-v3}.md
        └── scripts/{justos,testes}.py
```

O `SKILL.md` do vendor declara `name: multiplos-justos` no frontmatter. Ele fica a três níveis
abaixo de `skills/`, fora do glob de descoberta `skills/*/SKILL.md` — se fosse descoberto, colidiria
com a skill standalone do usuário. A Task 3 trava isso com teste.

---

### Task 1: Cópia congelada + manifest de hashes

**Files:**
- Create: `skills/er-multiplos-justos/vendor/multiplos-justos/` (7 arquivos, cópia byte a byte)
- Create: `skills/er-multiplos-justos/manifest_vendor.json`
- Create: `tests/test_vendor_multiplos_justos.py`
- Modify: `.gitattributes` (acrescentar bloco no fim)
- Modify: `.gitignore` (acrescentar `~$*`)

**Interfaces:**
- Produces: constantes que as Tasks 2 e 3 consomem de `tests/test_vendor_multiplos_justos.py` —
  `RAIZ: Path` (raiz do repo), `SKILL: Path` (`RAIZ/"skills"/"er-multiplos-justos"`),
  `VENDOR: Path` (`SKILL/"vendor"/"multiplos-justos"`), `ARQUIVOS: tuple[str, ...]` (os 7 paths
  relativos ao vendor), `_sha(p: Path) -> str`.
- Produces: `skills/er-multiplos-justos/manifest_vendor.json` com as chaves `versao: str`,
  `raiz_do_pacote: str`, `arquivos: dict[str, str]` (path relativo → sha256 hex).

- [ ] **Step 1: Extrair o pacote para dentro do plugin**

O pacote v9.24 fornecido pelo dono é o artefato de origem. Extrair e remover qualquer
`__pycache__` (o zip é limpo, mas rodar os scripts antes da cópia geraria um):

```bash
mkdir -p skills/er-multiplos-justos/vendor
unzip -o -q "/c/Users/antonio.coutinho/Downloads/multiplos-justos-v9 24 (1).zip" \
  -d skills/er-multiplos-justos/vendor
find skills/er-multiplos-justos/vendor -type d -name __pycache__ -prune -exec rm -rf {} +
find skills/er-multiplos-justos/vendor -type f | sort
```

Esperado, exatamente estes 7 arquivos:

```
skills/er-multiplos-justos/vendor/multiplos-justos/CHANGELOG.md
skills/er-multiplos-justos/vendor/multiplos-justos/SKILL.md
skills/er-multiplos-justos/vendor/multiplos-justos/references/aplicacao.md
skills/er-multiplos-justos/vendor/multiplos-justos/references/derivacao.md
skills/er-multiplos-justos/vendor/multiplos-justos/references/paper-multiplos-justos-v3.md
skills/er-multiplos-justos/vendor/multiplos-justos/scripts/justos.py
skills/er-multiplos-justos/vendor/multiplos-justos/scripts/testes.py
```

- [ ] **Step 2: Congelar EOL e ignorar temporários do Word**

Acrescentar ao FIM de `.gitattributes` (o bloco do K3 permanece — o legado só sai no item 10):

```
# Cópia congelada multiplos-justos v9.24 (byte a byte, sha256 em manifest_vendor.json):
# nunca converter EOL nestes paths — qualquer conversão quebra o congelamento.
skills/er-multiplos-justos/vendor/** -text
```

Acrescentar ao FIM de `.gitignore`:

```
~$*
```

Racional do `~$*`: o Word cria arquivos de lock com esse prefixo ao abrir um `.md`. Um deles dentro
do vendor viraria arquivo não declarado no manifest e derrubaria o teste de congelamento por um
motivo que não tem nada a ver com metodologia. (Já existe um solto no repo em
`skills/er-motor-k3/references/~$stified_PE_AI_Manual_v2.2.1.md`.)

- [ ] **Step 3: Escrever o teste de congelamento (vai falhar)**

Criar `tests/test_vendor_multiplos_justos.py`:

```python
"""Congelamento e integridade do vendor `multiplos-justos` v9.24.

O vendor é read-only por desenho: além do manifest de sha256 verificado aqui, o
próprio `scripts/testes.py` do pacote faz lint semântico dos docs — editar a
metodologia localmente quebra a suíte sem que ninguém precise lembrar da regra.
"""
import hashlib
import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SKILL = RAIZ / "skills" / "er-multiplos-justos"
VENDOR = SKILL / "vendor" / "multiplos-justos"

ARQUIVOS = (
    "CHANGELOG.md",
    "SKILL.md",
    "references/aplicacao.md",
    "references/derivacao.md",
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
    assert man["versao"] == "v9.24"
    assert man["raiz_do_pacote"] == "vendor/multiplos-justos"


def test_todo_arquivo_do_manifest_bate_no_disco():
    for rel, sha in _manifest()["arquivos"].items():
        alvo = VENDOR / rel
        assert alvo.is_file(), f"arquivo do manifest ausente no disco: {rel}"
        assert _sha(alvo) == sha, f"arquivo do vendor ALTERADO: {rel}"


def test_disco_nao_tem_arquivo_fora_do_manifest():
    no_disco = {
        p.relative_to(VENDOR).as_posix()
        for p in VENDOR.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts
    }
    assert no_disco == set(ARQUIVOS), (
        f"conjunto de arquivos do vendor divergiu do congelado: "
        f"sobrando={sorted(no_disco - set(ARQUIVOS))} "
        f"faltando={sorted(set(ARQUIVOS) - no_disco)}"
    )


def test_manifest_cobre_exatamente_os_arquivos_esperados():
    assert set(_manifest()["arquivos"]) == set(ARQUIVOS)
```

- [ ] **Step 4: Rodar para ver falhar**

Run: `python -m pytest tests/test_vendor_multiplos_justos.py -q`
Expected: FAIL — 4 erros de `FileNotFoundError` em `manifest_vendor.json`
(`test_disco_nao_tem_arquivo_fora_do_manifest` pode passar isolado; os outros três falham).

- [ ] **Step 5: Gerar o manifest**

Gerar os sha256 a partir do disco (nunca digitar hash à mão) e escrever o JSON:

```bash
python - <<'PY'
import hashlib, json
from pathlib import Path
SKILL = Path("skills/er-multiplos-justos")
VENDOR = SKILL / "vendor" / "multiplos-justos"
ARQUIVOS = ("CHANGELOG.md", "SKILL.md", "references/aplicacao.md",
            "references/derivacao.md", "references/paper-multiplos-justos-v3.md",
            "scripts/justos.py", "scripts/testes.py")
man = {
  "metodologia": "multiplos-justos",
  "versao": "v9.24",
  "copiado_em": "2026-08-21",
  "raiz_do_pacote": "vendor/multiplos-justos",
  "origem": ("pacote v9.24 da skill de usuario `multiplos-justos`, fornecido pelo dono "
             "(arquivo `multiplos-justos-v9 24.zip`). O caminho da skill instalada e EFEMERO "
             "e nao e registrado: a identidade da copia e dada por versao + os sha256 abaixo."),
  "read_only": ("Copia congelada. Alterar qualquer arquivo quebra "
                "tests/test_vendor_multiplos_justos.py E a propria suite do vendor (o lint "
                "semantico de scripts/testes.py le os docs). Evolucao da metodologia e decisao "
                "humana explicita: substituir o pacote inteiro e regenerar este manifest."),
  "regenerar": "ver docs/superpowers/plans/2026-08-21-v4-item2-vendor-multiplos-justos.md, Task 1 Step 5",
  "suite": {
    "selftest": "python skills/er-multiplos-justos/vendor/multiplos-justos/scripts/justos.py selftest",
    "completa": "python skills/er-multiplos-justos/vendor/multiplos-justos/scripts/testes.py",
    "observado_em_2026-08-21": ("selftest OK (0,2s); suite completa: TODOS OS TESTES PASSARAM "
                                "(10,4s, exit 0) — portatil, sem rede e sem planilha externa"),
  },
  "arquivos": {rel: hashlib.sha256((VENDOR / rel).read_bytes()).hexdigest() for rel in ARQUIVOS},
}
(SKILL / "manifest_vendor.json").write_text(
    json.dumps(man, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print("manifest escrito com", len(man["arquivos"]), "arquivos")
PY
```

Expected: `manifest escrito com 7 arquivos`

- [ ] **Step 6: Conferir os sha256 contra os valores medidos no pacote original**

Os hashes do pacote pristino, medidos em 2026-08-21 antes da cópia, são estes. Se algum divergir, a
cópia foi corrompida (quase sempre conversão de EOL — revisar o Step 2 antes de seguir):

```bash
python -c "
import json
esperado = {
 'CHANGELOG.md': '70381f56235639394a8bc9d8ce16a44eb18ddae6603516496b56a91eef467b13',
 'SKILL.md': 'f1a9e15e7b1ae8d709c38fec2e199c50a84670be011133eb1afa46ff56a56871',
 'references/aplicacao.md': 'fc29e40a08b2f0f85d983a90d1b5ed84faae5444bb069321fc1c7c0db130810d',
 'references/derivacao.md': 'fcb406f01e9a67a05fd33542565e65bed35fd28125c0ae5f5ddc9fc386d5a5bb',
 'references/paper-multiplos-justos-v3.md': '15104b5790250dc33354017e35356a1f5ec07287a7c1a677f4e5d59be38927be',
 'scripts/justos.py': '919c38eafc3bc327a0fbd79eded70163eb43abe368a22040d4f7c2f25bd49867',
 'scripts/testes.py': 'd2a57192f2fad5a7162ab4d48cd07364b257c793c0bf3b9bd2b38456e81475db',
}
obtido = json.load(open('skills/er-multiplos-justos/manifest_vendor.json', encoding='utf-8'))['arquivos']
assert obtido == esperado, [k for k in esperado if obtido.get(k) != esperado[k]]
print('OK — copia identica ao pacote original')
"
```

Expected: `OK — copia identica ao pacote original`

- [ ] **Step 7: Rodar o teste para ver passar**

Run: `python -m pytest tests/test_vendor_multiplos_justos.py -q`
Expected: PASS — `4 passed`

- [ ] **Step 8: Rodar a suíte inteira do repo (o legado não pode quebrar)**

Run: `python -m pytest tests/ -q`
Expected: PASS — todos os testes da v3 continuam verdes; a contagem sobe em 4.

- [ ] **Step 9: Commit**

```bash
git add skills/er-multiplos-justos tests/test_vendor_multiplos_justos.py .gitattributes .gitignore
git commit -m "$(cat <<'EOF'
feat(er-multiplos-justos): copia congelada v9.24 com manifest de sha256

Vendor byte a byte em vendor/multiplos-justos (7 arquivos), com EOL travado
em .gitattributes e teste de congelamento manifest x disco nos dois sentidos.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: Suíte da metodologia rodando e travando

**Files:**
- Modify: `tests/test_vendor_multiplos_justos.py` (acrescentar dois testes ao fim)
- Modify: `.github/workflows/ci.yml` (novo passo antes do `pytest`)

**Interfaces:**
- Consumes: `VENDOR: Path` da Task 1.
- Produces: garantia executável de que `selftest` e a suíte completa passam — pré-requisito de
  qualquer emissão (regra inviolável 2 do desenho).

- [ ] **Step 1: Escrever os testes da suíte (vão falhar se o vendor estiver corrompido)**

Primeiro, acrescentar `os`, `subprocess` e `sys` ao bloco de imports **no topo** do arquivo, junto
com `hashlib` e `json` que já estão lá:

```python
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
```

Depois, acrescentar ao FIM de `tests/test_vendor_multiplos_justos.py`:

```python
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


def test_suite_completa_do_vendor_passa():
    r = _rodar(str(VENDOR / "scripts" / "testes.py"))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "TODOS OS TESTES PASSARAM" in r.stdout, r.stdout[-2000:]
```

`selftest` é subcomando de `justos.py`, não um script à parte — por isso `_rodar` recebe o argv
completo em vez do nome do script.

- [ ] **Step 2: Rodar e ver passar**

Run: `python -m pytest tests/test_vendor_multiplos_justos.py -q`
Expected: PASS — `6 passed` em ~11s (a suíte completa leva ~10,4s; o selftest, 0,2s).

- [ ] **Step 3: Confirmar que a árvore congelada não foi mutada**

Run: `python -m pytest tests/test_vendor_multiplos_justos.py::test_disco_nao_tem_arquivo_fora_do_manifest -q`
Expected: PASS — nenhum `__pycache__` apareceu dentro do vendor.

- [ ] **Step 4: Ligar ao CI como tripwire, antes do pytest**

Em `.github/workflows/ci.yml`, inserir o passo abaixo ENTRE `Instalar dependências` e `pytest`:

```yaml
      - name: Suíte da metodologia (vendor multiplos-justos v9.24)
        env:
          PYTHONUTF8: "1"
          PYTHONDONTWRITEBYTECODE: "1"
        run: |
          python skills/er-multiplos-justos/vendor/multiplos-justos/scripts/justos.py selftest
          python skills/er-multiplos-justos/vendor/multiplos-justos/scripts/testes.py
```

Racional da duplicação com o pytest: vendor corrompido falha em ~11s com um nome de passo
inequívoco, antes de a suíte inteira rodar. O pytest mantém a mesma checagem para o
desenvolvimento local.

- [ ] **Step 5: Validar o YAML**

Run: `python -c "import yaml,sys; d=yaml.safe_load(open('.github/workflows/ci.yml',encoding='utf-8')); passos=[s['name'] for s in d['jobs']['test']['steps'] if 'name' in s]; print(passos); assert passos.index('Suíte da metodologia (vendor multiplos-justos v9.24)') < passos.index('pytest')"`
Expected: a lista de passos impressa, com a suíte antes do `pytest`, sem AssertionError.

- [ ] **Step 6: Commit**

```bash
git add tests/test_vendor_multiplos_justos.py .github/workflows/ci.yml
git commit -m "$(cat <<'EOF'
test(er-multiplos-justos): selftest e suite completa do vendor no pytest e no CI

Suite roda por subprocess com o interpretador corrente e encoding fixo;
PYTHONDONTWRITEBYTECODE mantem a arvore congelada intacta. No CI, passo
nomeado antes do pytest para falhar rapido em vendor corrompido.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: `SKILL.md` do fleet como índice, sem paráfrase

**Files:**
- Create: `skills/er-multiplos-justos/SKILL.md`
- Modify: `tests/test_vendor_multiplos_justos.py` (acrescentar dois testes ao fim)

**Interfaces:**
- Consumes: `RAIZ`, `SKILL`, `VENDOR`, `ARQUIVOS` da Task 1.
- Produces: a skill `er-multiplos-justos` carregável pelo plugin, que as skills `er-valuation`
  (item 3) e `er-analise` (item 8) citam como única porta de entrada da metodologia.

- [ ] **Step 1: Escrever os testes das travas do índice (vão falhar)**

Acrescentar ao fim de `tests/test_vendor_multiplos_justos.py`:

```python
DOCS_DO_VENDOR = ("SKILL.md", "references/aplicacao.md", "references/derivacao.md",
                  "references/paper-multiplos-justos-v3.md")
PROSCRITOS = ("g = RiR", "EV/EBITDA = EV/NOPAT", "FCFF = NOPAT", "P/VP = P/L")


def test_indice_aponta_para_todo_arquivo_do_vendor():
    idx = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    assert idx.startswith("---"), "SKILL.md sem frontmatter"
    assert "name: er-multiplos-justos" in idx
    for rel in ARQUIVOS:
        assert rel in idx, f"o indice nao aponta para {rel}"
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


def test_skill_md_do_vendor_fora_do_caminho_de_descoberta():
    descobriveis = {p.resolve() for p in (RAIZ / "skills").glob("*/SKILL.md")}
    assert (VENDOR / "SKILL.md").resolve() not in descobriveis, (
        "o SKILL.md do vendor declara `name: multiplos-justos` e colidiria com a skill "
        "standalone do usuario se fosse descoberto"
    )
    assert "name: multiplos-justos" in (VENDOR / "SKILL.md").read_text(encoding="utf-8")
```

- [ ] **Step 2: Rodar para ver falhar**

Run: `python -m pytest tests/test_vendor_multiplos_justos.py -q -k indice`
Expected: FAIL — `FileNotFoundError` em `skills/er-multiplos-justos/SKILL.md`.

- [ ] **Step 3: Escrever o índice**

Criar `skills/er-multiplos-justos/SKILL.md`:

```markdown
---
name: er-multiplos-justos
description: USE QUANDO precisar da metodologia canônica de valuation do fleet — localizar o arquivo certo do pacote congelado, rodar o motor ou a suíte, ou confirmar a integridade da cópia. É um índice do vendor congelado, não a metodologia. NÃO use para montar o caso de valuation (er-valuation), coletar evidência (er-evidencia), compor relatório (er-relatorio) ou conduzir a análise (er-analise).
---

# er-multiplos-justos — índice do vendor congelado

Este arquivo **não contém metodologia**. A metodologia canônica é a skill `multiplos-justos`
v9.24, copiada byte a byte para `vendor/multiplos-justos/` e verificada por sha256 em
`manifest_vendor.json`. Regra do desenho v4: **índice, nunca paráfrase** — resumir a metodologia
aqui cria uma segunda fonte que envelhece mal. Leia o arquivo do vendor.

## Mapa do pacote — o que ler, e quando

| Arquivo | O que é | Quando ler |
|---|---|---|
| `vendor/multiplos-justos/SKILL.md` | Núcleo: identidade central, os cinco gates, convenções do motor, catálogo de comandos, estrutura da entrega, diagnósticos obrigatórios | Sempre, antes de qualquer valuation |
| `vendor/multiplos-justos/references/aplicacao.md` | Playbook de empresa real: pesquisa, regras travadas de derivação de premissas, convenção terminal, grade de cenários e reversa, degrau e capacidade, financeiras, memória de cálculo, multi-segmento, jurisprudência | **Na íntegra**, antes de valuation de companhia real. O próprio pacote exige |
| `vendor/multiplos-justos/references/derivacao.md` | Matemática e provas: convenções de valor terminal, APV e recursão, teorema da classificação, ponte de releveraging | Quando a teoria for questionada, ou houver degrau ou mudança de estrutura de capital |
| `vendor/multiplos-justos/references/paper-multiplos-justos-v3.md` | Fundamentação: proposições com estatuto epistemológico declarado, protocolo de validação, condições de falseamento, caso trabalhado | Ao defender por escrito uma escolha de convenção |
| `vendor/multiplos-justos/scripts/justos.py` | O motor. Saída JSON, stdlib pura | Toda conta de valuation passa por aqui |
| `vendor/multiplos-justos/scripts/testes.py` | Suíte independente: property tests, reconciliações, boundaries, lint de portabilidade e lint semântico dos docs | Antes de entregar; e sempre que um resultado parecer estranho |
| `vendor/multiplos-justos/CHANGELOG.md` | Linhagem das versões e a origem de cada regra | Ao investigar por que uma regra existe |

## Como rodar

```bash
python skills/er-multiplos-justos/vendor/multiplos-justos/scripts/justos.py selftest
python skills/er-multiplos-justos/vendor/multiplos-justos/scripts/testes.py
```

O catálogo de comandos do motor está no `SKILL.md` do vendor — não é reproduzido aqui. Nenhuma
conta de valuation é feita fora do motor: sem prosa, sem planilha, sem Python novo, sem JS novo
(regra inviolável 1 do desenho v4).

## Integridade da cópia

`manifest_vendor.json` registra versão, origem e o sha256 de cada um dos 7 arquivos.
`tests/test_vendor_multiplos_justos.py` confronta manifest e disco **nos dois sentidos** — arquivo
alterado e arquivo a mais reprovam igualmente — e roda a suíte do vendor.

O congelamento é auto-reforçado: `scripts/testes.py` faz lint semântico dos próprios docs do
pacote, então editar a metodologia localmente quebra a suíte sem depender de ninguém lembrar da
regra. **O vendor é read-only.** Evoluir a metodologia é decisão humana explícita — substituir o
pacote inteiro, regenerar o manifest, rodar a suíte.

## Fronteira

A skill de usuário `multiplos-justos` permanece intocada fora deste repositório e continua
acionável só por `/multiplos-justos`. Aqui ela é biblioteca, não skill acionável: o gatilho de
análise é do `er-analise`. O `SKILL.md` do vendor declara `name: multiplos-justos` e por isso vive
fora do caminho de descoberta de skills — teste em
`tests/test_vendor_multiplos_justos.py::test_skill_md_do_vendor_fora_do_caminho_de_descoberta`.

Referência de desenho: `docs/desenho-arquitetura-v4.md`, Seções 3.2, 4 e 18.
```

- [ ] **Step 4: Rodar os testes do índice**

Run: `python -m pytest tests/test_vendor_multiplos_justos.py -q`
Expected: PASS — `9 passed`.

Se `test_indice_nao_reproduz_metodologia` falhar apontando uma linha de ≥60 caracteres copiada do
vendor, **reescreva a linha do índice** — não afrouxe o limiar. É exatamente o defeito que o teste
existe para pegar.

- [ ] **Step 5: Rodar a suíte inteira**

Run: `python -m pytest tests/ -q`
Expected: PASS — v3 intacta, 9 testes novos.

- [ ] **Step 6: Commit**

```bash
git add skills/er-multiplos-justos/SKILL.md tests/test_vendor_multiplos_justos.py
git commit -m "$(cat <<'EOF'
feat(er-multiplos-justos): SKILL.md como indice do vendor, com trava anti-parafrase

Indice aponta os 7 arquivos do pacote e quando ler cada um; teste reprova
copia literal de linha longa dos docs do vendor e formula de metodologia,
e trava o SKILL.md do vendor fora do caminho de descoberta de skills.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

## Verificação final do item 2

- [ ] `python -m pytest tests/ -q` — verde, v3 inclusa
- [ ] `python skills/er-multiplos-justos/vendor/multiplos-justos/scripts/justos.py selftest` — `SELFTEST OK`
- [ ] `python skills/er-multiplos-justos/vendor/multiplos-justos/scripts/testes.py` — `TODOS OS TESTES PASSARAM`
- [ ] `git status --short` — árvore limpa (nenhum `__pycache__` ou `~$*` dentro do vendor)
- [ ] `git diff main --stat` — só os arquivos previstos neste plano

## Colisão conhecida, para o item 3

`tests/test_manifesto.py::test_v2_removida` afirma que `skills/er-valuation` **não** existe (era uma
skill da v2). O item 3 do desenho cria `skills/er-valuation` com esse nome. Quando chegar lá, o
teste precisa ser ajustado — remover `skills/er-valuation` da lista de mortos da v2 e, se for
desejável manter a garantia, trocá-la por uma verificação de conteúdo (a skill nova tem
`name: er-valuation` e o frontmatter da v4). Registrado aqui para não virar surpresa.

## Fora de escopo deste item

Espelho JS e paridade (item 4), builder e QC (item 5), fixture sintética (item 6), `er-evidencia` e
agente (item 7), `er-analise` (item 8), golden case (item 9), remoção do legado e bump para 4.0.0
(item 10). Nada disso é antecipado aqui.
