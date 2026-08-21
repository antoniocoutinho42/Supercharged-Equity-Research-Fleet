# `er-valuation` núcleo — Plano de Implementação (item 3, fatia A)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Um pipeline determinístico `caso.json` → `resultados.json` que roda o motor congelado por cenário na rota canônica declarada, compõe a ponte para preço e normaliza os diagnósticos — recusando qualquer caso que omita uma escolha que a metodologia declara sem default.

**Architecture:** Quatro módulos com uma responsabilidade cada, sob `skills/er-valuation/scripts/`: `caso.py` (schema e validação), `motor.py` (invocação do motor congelado por subprocess), `ponte.py` (composição da ponte para preço) e `avaliar.py` (orquestração e CLI). Nenhum deles escreve matemática de valuation: `motor.py` monta argv e devolve o JSON do motor; `ponte.py` soma linhas de balanço declaradas pelo usuário e entrega o líquido ao motor, que faz a conta.

**Tech Stack:** Python 3.12+, stdlib pura, pytest.

## Global Constraints

- **Fonte de verdade:** `docs/desenho-arquitetura-v4.md`. Nenhuma decisão de produto é reaberta aqui.
- **Regra inviolável 1:** a matemática de valuation vem do motor congelado. Proibido recomputar, aproximar ou reimplementar em Python novo. O que este wrapper faz é montar entrada, somar linhas de balanço declaradas e normalizar saída.
- **Regra inviolável 3:** nenhuma escolha que a metodologia declara sem default recebe default. O wrapper **recusa** o caso; não escolhe por ele.
- **Vendor read-only:** nada sob `vendor/multiplos-justos/` é modificado. É chamado por subprocess.
- **Chamada ao motor:** sempre `sys.executable`, sempre `encoding="utf-8"`, sempre com `PYTHONDONTWRITEBYTECODE=1` e `PYTHONUTF8=1` no ambiente — o vendor não pode ser sujado por bytecode nem lido sob cp1252. Mesma disciplina de `tests/test_vendor_multiplos_justos.py`.
- **Determinismo:** o mesmo `caso.json` produz `resultados.json` byte a byte idêntico. Proibido carimbar hora de execução, caminho absoluto ou qualquer valor de ambiente na saída.
- Python 3.12+, stdlib pura, pytest. Nada de rede.
- Commits: conventional commits em PT-BR, com o trailer `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`.
- Não tocar em `skills/er-motor-k3/`, `skills/er-dados-openbb/`, `skills/er-relatorio-html/` nem em qualquer arquivo v3/K3 — o legado sai no item 10.
- Use as ferramentas Write/Edit para conteúdo de arquivo, nunca heredoc de shell.

## Fora do escopo desta fatia

Reversa e sensibilidades (fatia 3B). SOTP por segmento e por safra, composição multifásica/rampa, degrau, ponte de releveraging (fatia 3C). Espelho JS (item 4). Relatório (item 5). Não antecipe nada disso — nem "só o esqueleto".

**Métricas suportadas nesta fatia:** somente as que o motor emite diretamente — rota firm: `EBITDA` e `NOPAT`; rota equity: `LL`. `EBIT`, `EPS`, `EBITDA/ação` e demais transformações de apresentação entram numa fatia posterior, com a álgebra exibida. Um caso que peça métrica fora dessa lista é recusado com mensagem clara.

## Contrato do motor — shapes reais, capturados em 2026-08-21

Rodados nesta máquina, contra o vendor congelado. Use estas chaves; não invente nem suponha outras.

`python vendor/multiplos-justos/scripts/justos.py ev --g 5 --roic 12 --wacc 10 --n 10 --da 20 --tax 25 --tv gordon --roic-tv 10 --gp 3 --ebitda 1000 --nd 500 --acoes 100 --moeda BRL-nominal --rf 12` devolve:

```
EV/NOPAT_curr, EV/NOPAT_fwd, EV/EBITDA_curr, EV/EBITDA_fwd,
convencao_temporal, diagnosticos (lista de strings), tv,
coerencia_vetor {identidades_checadas, nao_checadas_por_falta_de_input, nota},
convencao_fluxo_transicao_C7, efeito_c7_alternativa_gp_%,
EV, Equity, Preco_acao        # só quando --ebitda/--nd/--acoes são passados
```

Valores do exemplo, para o teste de fumaça: `EV/EBITDA_curr` 6.6906, `EV` 6690.59, `Equity` 6190.59, `Preco_acao` 61.91.

`python vendor/multiplos-justos/scripts/justos.py pe --g 8 --roe 18 --ke 14 --n 10 --gde 30 --nde 20 --tv convergencia --ni 500 --acoes 100` devolve:

```
PL_curr, PL_fwd, politica_caixa_tv, convencao_temporal,
diagnosticos (lista), tv, coerencia_vetor, decomposicao, Equity, Preco_acao
```

Valores do exemplo: `PL_curr` 9.003, `Equity` 4501.51, `Preco_acao` 45.02.

O motor **exige `--tv`** e recusa rodar sem ele. Taxas entram em % (`--g 5` = 5%). `--nd` negativo = caixa líquido.

## File Structure

| Arquivo | Responsabilidade |
|---|---|
| `skills/er-valuation/scripts/caso.py` | Carregar e validar o `caso.json`; recusar omissão de escolha sem default; nada mais |
| `skills/er-valuation/scripts/motor.py` | Montar o argv do motor por rota e executar; devolver o JSON cru; nada mais |
| `skills/er-valuation/scripts/ponte.py` | Somar as linhas da ponte num líquido a entregar ao motor; nada mais |
| `skills/er-valuation/scripts/avaliar.py` | Orquestrar cenários × rota, montar `resultados.json`, CLI |
| `skills/er-valuation/SKILL.md` | Doutrina do wrapper: o que faz, o que nunca faz, o contrato do caso, como rodar |
| `tests/test_valuation_caso.py` · `test_valuation_motor.py` · `test_valuation_ponte.py` · `test_valuation_avaliar.py` | Um por módulo |
| `tests/fixtures/caso_minimo_firm.json` · `caso_minimo_equity.json` | Casos sintéticos usados pelos testes |
| `tests/test_manifesto.py` | Ajuste da colisão conhecida (Task 5) |

## Decisões de projeto já tomadas — não reabra, implemente

**D1 — A ponte é soma de linhas declaradas, entregue ao motor como líquido.** O motor recebe `--nd` (dívida líquida escalar) e faz `Equity = EV − nd`. A ponte rica do desenho (caixa, dívida, outros ativos/passivos, minoritários) é a **decomposição** desse escalar. `ponte.py` calcula
`nd_efetivo = divida_bruta − caixa_e_equivalentes + minoritarios + outros_passivos − outros_ativos`
e guarda cada parcela para o waterfall. A conta de valor continua inteira no motor.

**D2 — A ponte só existe na rota firm.** Na rota equity o motor devolve `Equity` direto de `--ni`, e a metodologia é explícita: financeira não tem ponte de dívida. Caso equity com bloco `ponte` preenchido é **recusado**, não ignorado em silêncio.

**D3 — EV vem do motor, e o wrapper confere.** Na rota firm com métrica EBITDA, o wrapper passa `--ebitda/--nd/--acoes` e usa o `EV`, `Equity` e `Preco_acao` que o motor devolve. Com métrica NOPAT, o motor não tem flag de escala equivalente: o wrapper aplica `EV = EV/NOPAT_curr × NOPAT` — a definição do múltiplo, com a álgebra registrada na saída — e a Task 4 traz um teste que, com a mesma economia, reconcilia as duas rotas de escala.

**D4 — Determinismo é testável.** `resultados.json` não carrega hora de execução nem caminho absoluto. A data que aparece é a `data_analise` do caso. Um teste roda o mesmo caso duas vezes e compara os bytes.

**D5 — Recusar é o comportamento correto.** Toda recusa levanta `CasoInvalido` com mensagem em PT-BR nomeando o campo e o porquê. Nunca `assert`, nunca `sys.exit` dentro dos módulos — só o CLI de `avaliar.py` converte exceção em exit code 1.

## Contrato do `caso.json` (fatia A)

```json
{
  "companhia": "Sintética S.A.",
  "ticker": "SINT3",
  "moeda": "BRL-nominal",
  "data_analise": "2026-08-21",
  "data_base": null,
  "preco": {"valor": 55.0, "fonte": "fixture sintética", "data": "2026-08-21"},
  "rota": "firm",
  "metrica_base": {"tipo": "EBITDA", "valor": 1000.0, "periodo": "2025A", "fonte": "fixture sintética"},
  "acoes_diluidas": 100.0,
  "ponte": {
    "divida_bruta": 800.0, "caixa_e_equivalentes": 300.0,
    "outros_ativos": 0.0, "outros_passivos": 0.0, "minoritarios": 0.0
  },
  "cenarios": {
    "base": {
      "ancora": "média normalizada 2023-2025",
      "triangulo": {"inputs": ["g", "roic"], "output": "rir"},
      "premissas": {
        "g": 5.0, "roic": 12.0, "wacc": 10.0, "n": 10,
        "da": 20.0, "tax": 25.0, "tv": "gordon", "roic_tv": 10.0, "gp": 3.0
      }
    }
  }
}
```

Rota equity troca `premissas` para `{g, roe, ke, n, gde, nde, tv, roe_tv?, gp?, politica_tv?}`, `metrica_base.tipo` para `LL`, e **omite** `ponte`.

Campos obrigatórios: `companhia`, `moeda`, `data_analise`, `preco.{valor,fonte,data}`, `rota`, `metrica_base.{tipo,valor,fonte}`, `acoes_diluidas`, `cenarios` com ao menos um cenário, e por cenário `ancora`, `triangulo.{inputs,output}` e `premissas` com `tv` presente.

---

### Task 1: Contrato do caso — carregar, validar, recusar

**Files:**
- Create: `skills/er-valuation/scripts/caso.py`
- Create: `tests/test_valuation_caso.py`
- Create: `tests/fixtures/caso_minimo_firm.json`, `tests/fixtures/caso_minimo_equity.json`

**Interfaces:**
- Produces: `class CasoInvalido(Exception)`; `carregar(caminho: Path) -> dict` (lê JSON, valida, devolve o dict validado); `validar(caso: dict) -> None` (levanta `CasoInvalido` na primeira violação); `PREMISSAS_FIRM: frozenset`, `PREMISSAS_EQUITY: frozenset`, `METRICAS_POR_ROTA: dict[str, frozenset]`.
- Consumed by: `motor.py` (lê `caso["rota"]` e as premissas), `ponte.py` (lê `caso["ponte"]`), `avaliar.py` (orquestra).

- [ ] **Step 1: Escrever as fixtures**

`tests/fixtures/caso_minimo_firm.json` — exatamente o JSON do contrato acima.

`tests/fixtures/caso_minimo_equity.json`:

```json
{
  "companhia": "Financeira Sintética S.A.",
  "ticker": "FSIN4",
  "moeda": "BRL-nominal",
  "data_analise": "2026-08-21",
  "data_base": null,
  "preco": {"valor": 40.0, "fonte": "fixture sintética", "data": "2026-08-21"},
  "rota": "equity",
  "metrica_base": {"tipo": "LL", "valor": 500.0, "periodo": "2025A", "fonte": "fixture sintética"},
  "acoes_diluidas": 100.0,
  "cenarios": {
    "base": {
      "ancora": "consenso t+1, 9 analistas",
      "triangulo": {"inputs": ["g", "roe"], "output": "rir"},
      "premissas": {"g": 8.0, "roe": 18.0, "ke": 14.0, "n": 10,
                    "gde": 30.0, "nde": 20.0, "tv": "convergencia"}
    }
  }
}
```

- [ ] **Step 2: Escrever os testes (vão falhar)**

`tests/test_valuation_caso.py`:

```python
import json
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures"
import sys
sys.path.insert(0, str(RAIZ / "skills" / "er-valuation" / "scripts"))
from caso import CasoInvalido, carregar, validar  # noqa: E402


def _firm() -> dict:
    return json.loads((FIXTURES / "caso_minimo_firm.json").read_text(encoding="utf-8"))


def _equity() -> dict:
    return json.loads((FIXTURES / "caso_minimo_equity.json").read_text(encoding="utf-8"))


def test_fixture_firm_e_valida():
    assert carregar(FIXTURES / "caso_minimo_firm.json")["rota"] == "firm"


def test_fixture_equity_e_valida():
    assert carregar(FIXTURES / "caso_minimo_equity.json")["rota"] == "equity"


@pytest.mark.parametrize("campo", ["companhia", "moeda", "data_analise", "rota",
                                   "acoes_diluidas", "cenarios"])
def test_campo_obrigatorio_ausente_recusa(campo):
    c = _firm()
    del c[campo]
    with pytest.raises(CasoInvalido, match=campo):
        validar(c)


def test_tv_ausente_recusa_por_ser_escolha_sem_default():
    c = _firm()
    del c["cenarios"]["base"]["premissas"]["tv"]
    with pytest.raises(CasoInvalido, match="convenção terminal"):
        validar(c)


def test_ancora_ausente_recusa():
    """A metodologia exige âncora observável por cenário — cenário sem âncora e inventado."""
    c = _firm()
    del c["cenarios"]["base"]["ancora"]
    with pytest.raises(CasoInvalido, match="âncora"):
        validar(c)


def test_triangulo_ausente_recusa():
    """Cenario com RiR silencioso e cenario opaco: a configuracao tem de ser declarada."""
    c = _firm()
    del c["cenarios"]["base"]["triangulo"]
    with pytest.raises(CasoInvalido, match="triângulo"):
        validar(c)


def test_triangulo_com_output_entre_os_inputs_recusa():
    c = _firm()
    c["cenarios"]["base"]["triangulo"] = {"inputs": ["g", "roic"], "output": "g"}
    with pytest.raises(CasoInvalido, match="triângulo"):
        validar(c)


def test_rota_desconhecida_recusa():
    c = _firm()
    c["rota"] = "hibrida"
    with pytest.raises(CasoInvalido, match="rota"):
        validar(c)


def test_metrica_incompativel_com_a_rota_recusa():
    c = _firm()
    c["metrica_base"]["tipo"] = "LL"
    with pytest.raises(CasoInvalido, match="métrica"):
        validar(c)


def test_metrica_fora_da_fatia_recusa_com_mensagem_clara():
    c = _firm()
    c["metrica_base"]["tipo"] = "EBIT"
    with pytest.raises(CasoInvalido, match="EBIT"):
        validar(c)


def test_ponte_na_rota_equity_recusa():
    """Financeira nao tem ponte de divida — aceitar e ignorar seria silenciar."""
    c = _equity()
    c["ponte"] = {"divida_bruta": 10.0, "caixa_e_equivalentes": 0.0,
                  "outros_ativos": 0.0, "outros_passivos": 0.0, "minoritarios": 0.0}
    with pytest.raises(CasoInvalido, match="ponte"):
        validar(c)


def test_ponte_ausente_na_rota_firm_recusa():
    c = _firm()
    del c["ponte"]
    with pytest.raises(CasoInvalido, match="ponte"):
        validar(c)


def test_premissa_desconhecida_recusa():
    """Chave que o motor nao conhece e erro de digitacao, nao extensao silenciosa."""
    c = _firm()
    c["cenarios"]["base"]["premissas"]["roe"] = 20.0
    with pytest.raises(CasoInvalido, match="roe"):
        validar(c)


def test_cenarios_vazio_recusa():
    c = _firm()
    c["cenarios"] = {}
    with pytest.raises(CasoInvalido, match="cenário"):
        validar(c)


def test_acoes_diluidas_nao_positiva_recusa():
    c = _firm()
    c["acoes_diluidas"] = 0
    with pytest.raises(CasoInvalido, match="ações"):
        validar(c)
```

- [ ] **Step 3: Rodar para ver falhar**

Run: `python -m pytest tests/test_valuation_caso.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'caso'`.

- [ ] **Step 4: Implementar `caso.py`**

Escreva `skills/er-valuation/scripts/caso.py` com:

- docstring de módulo dizendo o que ele faz e o que não faz (não calcula nada, não chama o motor);
- `class CasoInvalido(Exception)`;
- `PREMISSAS_FIRM = frozenset({"g", "roic", "wacc", "n", "da", "tax", "tv", "roic_tv", "gp", "roic_book", "mid_year"})`;
- `PREMISSAS_EQUITY = frozenset({"g", "roe", "ke", "n", "gde", "nde", "tv", "roe_tv", "gp", "roe_book", "politica_tv", "mid_year"})`;
- `PREMISSAS_OBRIGATORIAS_FIRM = frozenset({"g", "roic", "wacc", "n", "da", "tax", "tv"})` e a equivalente equity `{"g", "roe", "ke", "n", "tv"}`;
- `METRICAS_POR_ROTA = {"firm": frozenset({"EBITDA", "NOPAT"}), "equity": frozenset({"LL"})}`;
- `METRICAS_FORA_DA_FATIA = frozenset({"EBIT", "EPS", "EBITDA/acao", "NOPAT/acao"})` — recusadas com mensagem dizendo que entram numa fatia posterior;
- `CAMPOS_DA_PONTE = ("divida_bruta", "caixa_e_equivalentes", "outros_ativos", "outros_passivos", "minoritarios")`;
- `validar(caso)` percorrendo, em ordem: campos de topo → rota → métrica × rota → ponte × rota → cada cenário (âncora, triângulo, premissas obrigatórias, premissas desconhecidas);
- `carregar(caminho)` lendo com `encoding="utf-8"`, chamando `validar` e devolvendo o dict.

Cada mensagem de `CasoInvalido` nomeia o campo e diz por que ele é exigido. A do `tv` cita a razão econômica — a escolha da convenção terminal não tem default porque a hipótese sobre a morte do spread é decisão declarada, não convenção de fábrica.

- [ ] **Step 5: Rodar para ver passar**

Run: `python -m pytest tests/test_valuation_caso.py -q`
Expected: PASS — 20 passed (2 de fixture + 6 parametrizados + 12 de recusa).

- [ ] **Step 6: Rodar a suíte inteira**

Run: `python -m pytest tests/ -q`
Expected: PASS, contagem sobe em 20.

- [ ] **Step 7: Commit**

```bash
git add skills/er-valuation/scripts/caso.py tests/test_valuation_caso.py tests/fixtures/
git commit -m "$(cat <<'EOF'
feat(er-valuation): contrato do caso com recusa de escolha sem default

Valida rota, metrica por rota, ponte por rota, ancora e triangulo por cenario.
Escolha que a metodologia declara sem default (convencao terminal) faz o caso
ser recusado, nunca preenchida por conta propria.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: Invocação do motor congelado

**Files:**
- Create: `skills/er-valuation/scripts/motor.py`
- Create: `tests/test_valuation_motor.py`

**Interfaces:**
- Consumes: nada. `motor.py` traduz chaves em flags genericamente e nao importa `caso.py` — quem valida o vocabulario de premissas e a Task 1.
- Produces: `class MotorFalhou(Exception)`; `RAIZ_VENDOR: Path` (aponta `vendor/multiplos-justos`); `argv_para(rota: str, premissas: dict, escala: dict | None) -> list[str]` (só a lista de argumentos, sem executar — testável sem subprocess); `executar(argv: list[str]) -> dict` (roda e devolve o JSON parseado); `rodar(rota, premissas, escala=None) -> dict` (compõe as duas).
- Consumed by: `avaliar.py`.

`escala` é `None` ou `{"ebitda": float, "nd": float, "acoes": float}` (rota firm) ou `{"ni": float, "acoes": float}` (rota equity).

- [ ] **Step 1: Escrever os testes (vão falhar)**

`tests/test_valuation_motor.py`:

```python
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "skills" / "er-valuation" / "scripts"))
from motor import MotorFalhou, RAIZ_VENDOR, argv_para, rodar  # noqa: E402

PREMISSAS_FIRM = {"g": 5.0, "roic": 12.0, "wacc": 10.0, "n": 10, "da": 20.0,
                  "tax": 25.0, "tv": "gordon", "roic_tv": 10.0, "gp": 3.0}
PREMISSAS_EQUITY = {"g": 8.0, "roe": 18.0, "ke": 14.0, "n": 10,
                    "gde": 30.0, "nde": 20.0, "tv": "convergencia"}


def test_vendor_esta_onde_o_modulo_espera():
    assert (RAIZ_VENDOR / "scripts" / "justos.py").is_file()


def test_argv_firm_usa_o_subcomando_ev_e_traduz_as_chaves():
    argv = argv_para("firm", PREMISSAS_FIRM, None)
    assert argv[0] == "ev"
    assert "--wacc" in argv and "--roic-tv" in argv
    assert "--tv" in argv and argv[argv.index("--tv") + 1] == "gordon"
    assert "--roe" not in argv


def test_argv_equity_usa_o_subcomando_pe():
    argv = argv_para("equity", PREMISSAS_EQUITY, None)
    assert argv[0] == "pe"
    assert "--roe" in argv and "--ke" in argv and "--gde" in argv
    assert "--wacc" not in argv


def test_argv_inclui_a_escala_quando_informada():
    argv = argv_para("firm", PREMISSAS_FIRM, {"ebitda": 1000.0, "nd": 500.0, "acoes": 100.0})
    for flag in ("--ebitda", "--nd", "--acoes"):
        assert flag in argv


def test_argv_omite_premissa_ausente_em_vez_de_inventar_default():
    premissas = dict(PREMISSAS_FIRM)
    del premissas["gp"]
    assert "--gp" not in argv_para("firm", premissas, None)


def test_rodar_firm_reproduz_os_numeros_do_motor():
    """Ancora capturada do vendor em 2026-08-21 — se mudar, o wrapper ou o motor mudou."""
    out = rodar("firm", PREMISSAS_FIRM, {"ebitda": 1000.0, "nd": 500.0, "acoes": 100.0})
    assert out["EV/EBITDA_curr"] == pytest.approx(6.6906, abs=1e-4)
    assert out["EV"] == pytest.approx(6690.59, abs=0.01)
    assert out["Equity"] == pytest.approx(6190.59, abs=0.01)
    assert out["Preco_acao"] == pytest.approx(61.91, abs=0.01)


def test_rodar_equity_reproduz_os_numeros_do_motor():
    out = rodar("equity", PREMISSAS_EQUITY, {"ni": 500.0, "acoes": 100.0})
    assert out["PL_curr"] == pytest.approx(9.003, abs=1e-3)
    assert out["Equity"] == pytest.approx(4501.51, abs=0.01)
    assert out["Preco_acao"] == pytest.approx(45.02, abs=0.01)


def test_diagnosticos_chegam_intactos():
    out = rodar("firm", PREMISSAS_FIRM, None)
    assert isinstance(out["diagnosticos"], list) and out["diagnosticos"]
    assert any("RiR" in d for d in out["diagnosticos"])


def test_motor_sem_tv_falha_com_a_saida_do_motor():
    premissas = dict(PREMISSAS_FIRM)
    del premissas["tv"]
    with pytest.raises(MotorFalhou):
        rodar("firm", premissas, None)


def test_rodar_nao_suja_o_vendor_com_bytecode():
    rodar("firm", PREMISSAS_FIRM, None)
    assert list(RAIZ_VENDOR.rglob("*.pyc")) == []
```

- [ ] **Step 2: Rodar para ver falhar**

Run: `python -m pytest tests/test_valuation_motor.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'motor'`.

- [ ] **Step 3: Implementar `motor.py`**

- `RAIZ_VENDOR` derivado do próprio arquivo: `Path(__file__).resolve().parents[3] / "vendor" / "multiplos-justos"`. Confirme a contagem de níveis contra o layout real (`skills/er-valuation/scripts/motor.py` → 3 níveis acima é a raiz do repo) e escreva um comentário dizendo de onde vem o número.
- `SUBCOMANDO = {"firm": "ev", "equity": "pe"}`.
- Tradução de chave para flag: `roic_tv` → `--roic-tv`, `roe_tv` → `--roe-tv`, `roic_book` → `--roic-book`, `roe_book` → `--roe-book`, `politica_tv` → `--politica-tv`, `mid_year` → `--mid-year` (flag booleana, sem valor); as demais viram `--<chave>`.
- `argv_para` monta a lista **sem** o interpretador e sem o caminho do script — só subcomando e flags. Premissa ausente não vira flag.
- `executar(argv)` roda `[sys.executable, str(RAIZ_VENDOR / "scripts" / "justos.py"), *argv]` com `capture_output=True, text=True, encoding="utf-8", timeout=120` e `env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONUTF8": "1"}`. `returncode != 0` ⟹ `MotorFalhou` com stdout e stderr na mensagem. JSON inválido ⟹ `MotorFalhou` dizendo isso.
- `rodar(rota, premissas, escala)` = `executar(argv_para(...))`.

- [ ] **Step 4: Rodar para ver passar**

Run: `python -m pytest tests/test_valuation_motor.py -q`
Expected: PASS — 10 passed.

- [ ] **Step 5: Suíte inteira e vendor limpo**

Run: `python -m pytest tests/ -q`
Expected: PASS.

Run: `git status --short vendor`
Expected: vazio.

- [ ] **Step 6: Commit**

```bash
git add skills/er-valuation/scripts/motor.py tests/test_valuation_motor.py
git commit -m "$(cat <<'EOF'
feat(er-valuation): invocacao do motor congelado por rota

argv_para monta o subcomando e as flags sem executar (testavel isolado);
executar roda com o interpretador corrente, utf-8 fixo e bytecode desligado
para nao sujar a arvore congelada. Premissa ausente nao vira default.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Ponte para preço

**Files:**
- Create: `skills/er-valuation/scripts/ponte.py`
- Create: `tests/test_valuation_ponte.py`

**Interfaces:**
- Consumes: `caso.py` (`CAMPOS_DA_PONTE`), apenas para a guarda de consistencia descrita no Step 3.
- Produces: `SINAIS: tuple[tuple[str, int], ...]`; `compor(ponte: dict) -> dict` devolvendo `{"nd_efetivo": float, "parcelas": [{"rotulo": str, "valor": float, "sinal": int}, ...]}`. `parcelas` preserva a ordem do waterfall e o sinal com que cada linha entra.
- Consumed by: `avaliar.py`.

- [ ] **Step 1: Escrever os testes (vão falhar)**

`tests/test_valuation_ponte.py`:

```python
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "skills" / "er-valuation" / "scripts"))
from ponte import compor  # noqa: E402

PONTE = {"divida_bruta": 800.0, "caixa_e_equivalentes": 300.0,
         "outros_ativos": 50.0, "outros_passivos": 20.0, "minoritarios": 100.0}


def test_nd_efetivo_e_a_soma_com_sinal():
    # 800 - 300 + 100 + 20 - 50 = 570
    assert compor(PONTE)["nd_efetivo"] == pytest.approx(570.0)


def test_caixa_liquido_produz_nd_negativo():
    p = dict(PONTE, divida_bruta=0.0, caixa_e_equivalentes=500.0,
             outros_ativos=0.0, outros_passivos=0.0, minoritarios=0.0)
    assert compor(p)["nd_efetivo"] == pytest.approx(-500.0)


def test_parcelas_cobrem_todas_as_linhas_com_sinal():
    parcelas = compor(PONTE)["parcelas"]
    assert [p["rotulo"] for p in parcelas] == [
        "divida_bruta", "caixa_e_equivalentes", "outros_ativos",
        "outros_passivos", "minoritarios"]
    sinais = {p["rotulo"]: p["sinal"] for p in parcelas}
    assert sinais["divida_bruta"] == 1 and sinais["minoritarios"] == 1
    assert sinais["caixa_e_equivalentes"] == -1 and sinais["outros_ativos"] == -1


def test_soma_das_parcelas_reconstroi_o_nd_efetivo():
    """A parcela exibida no waterfall e a MESMA que entra na conta."""
    r = compor(PONTE)
    assert sum(p["valor"] * p["sinal"] for p in r["parcelas"]) == pytest.approx(r["nd_efetivo"])


def test_ponte_zerada_produz_nd_zero():
    assert compor({k: 0.0 for k in PONTE})["nd_efetivo"] == pytest.approx(0.0)


def test_linha_ausente_e_erro_nao_zero_implicito():
    p = dict(PONTE)
    del p["minoritarios"]
    with pytest.raises(KeyError):
        compor(p)
```

- [ ] **Step 2: Rodar para ver falhar**

Run: `python -m pytest tests/test_valuation_ponte.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'ponte'`.

- [ ] **Step 3: Implementar `ponte.py`**

Um `SINAIS = (("divida_bruta", 1), ("caixa_e_equivalentes", -1), ("outros_ativos", -1), ("outros_passivos", 1), ("minoritarios", 1))` e um laço. A ordem de `SINAIS` é a ordem do waterfall.

**Guarda de consistência, no nível do módulo** — `caso.py` valida a PRESENÇA das linhas e `ponte.py` define a ORDEM e o SINAL delas; as duas listas têm de descrever o mesmo conjunto, e nada além de um teste as manteria juntas. Uma linha resolve, e falha no import se divergirem:

```python
from caso import CAMPOS_DA_PONTE

if tuple(rotulo for rotulo, _ in SINAIS) != CAMPOS_DA_PONTE:
    raise ImportError(
        "SINAIS (ponte.py) e CAMPOS_DA_PONTE (caso.py) divergiram — "
        "a ponte validada e a ponte somada tem de ser a mesma"
    )
``` Docstring explicando que isto é composição de linhas de balanço declaradas, não cálculo de valor: o líquido vai para `--nd` e quem faz `Equity = EV − nd` é o motor.

Linha ausente propaga `KeyError` — a validação de presença é do `caso.py`, e transformar ausência em zero seria inventar dado.

- [ ] **Step 4: Rodar para ver passar**

Run: `python -m pytest tests/test_valuation_ponte.py -q`
Expected: PASS — 6 passed.

- [ ] **Step 5: Commit**

```bash
git add skills/er-valuation/scripts/ponte.py tests/test_valuation_ponte.py
git commit -m "$(cat <<'EOF'
feat(er-valuation): ponte para preco como soma de linhas declaradas

Cada linha entra com sinal explicito e fica registrada para o waterfall; o
liquido vai para --nd e quem faz Equity = EV - nd e o motor. Linha ausente
levanta erro em vez de virar zero implicito.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: Orquestração e `resultados.json`

**Files:**
- Create: `skills/er-valuation/scripts/avaliar.py`
- Create: `tests/test_valuation_avaliar.py`

**Interfaces:**
- Consumes: `caso.carregar`, `motor.rodar`, `ponte.compor`.
- Produces: `avaliar(caso: dict) -> dict` (o conteúdo do `resultados.json`); `escrever(resultados: dict, destino: Path) -> None`; CLI `python skills/er-valuation/scripts/avaliar.py <caso.json> --out <resultados.json>`.

Shape de `resultados.json`:

```json
{
  "companhia": "...", "ticker": "...", "moeda": "...", "data_analise": "...",
  "rota": "firm",
  "metrica_base": {"tipo": "EBITDA", "valor": 1000.0},
  "preco": {"valor": 55.0, "fonte": "...", "data": "..."},
  "acoes_diluidas": 100.0,
  "ponte": {"nd_efetivo": 500.0, "parcelas": [...]},
  "cenarios": {
    "base": {
      "ancora": "...",
      "triangulo": {"inputs": ["g", "roic"], "output": "rir"},
      "premissas": {...},
      "multiplos": {"EV/EBITDA_curr": 6.6906, "EV/EBITDA_fwd": 6.372,
                    "EV/NOPAT_curr": 11.151, "EV/NOPAT_fwd": 10.62},
      "valor": {"EV": 6690.59, "Equity": 6190.59, "preco_acao": 61.91},
      "algebra_da_escala": "EV = EV/EBITDA_curr x EBITDA (ponte feita pelo motor)",
      "vs_preco": {"upside": 0.1256},
      "diagnosticos": [...],
      "coerencia_vetor": {...},
      "convencao_temporal": "..."
    }
  }
}
```

- [ ] **Step 1: Escrever os testes (vão falhar)**

`tests/test_valuation_avaliar.py`:

```python
import json
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures"
SCRIPTS = RAIZ / "skills" / "er-valuation" / "scripts"
sys.path.insert(0, str(SCRIPTS))
from caso import carregar  # noqa: E402
from avaliar import avaliar, escrever  # noqa: E402


def _res_firm() -> dict:
    return avaliar(carregar(FIXTURES / "caso_minimo_firm.json"))


def test_cabecalho_vem_do_caso():
    r = _res_firm()
    assert r["companhia"] == "Sintética S.A."
    assert r["rota"] == "firm" and r["moeda"] == "BRL-nominal"


def test_valor_por_acao_reproduz_o_motor():
    v = _res_firm()["cenarios"]["base"]["valor"]
    assert v["EV"] == pytest.approx(6690.59, abs=0.01)
    assert v["Equity"] == pytest.approx(6190.59, abs=0.01)
    assert v["preco_acao"] == pytest.approx(61.91, abs=0.01)


def test_upside_e_calculado_contra_o_preco_do_caso():
    r = _res_firm()["cenarios"]["base"]
    esperado = 61.91 / 55.0 - 1
    assert r["vs_preco"]["upside"] == pytest.approx(esperado, abs=1e-4)


def test_ponte_aparece_decomposta_e_bate_com_o_nd_usado():
    r = _res_firm()
    assert r["ponte"]["nd_efetivo"] == pytest.approx(500.0)
    assert sum(p["valor"] * p["sinal"] for p in r["ponte"]["parcelas"]) == pytest.approx(500.0)


def test_diagnosticos_do_motor_chegam_ao_resultado():
    d = _res_firm()["cenarios"]["base"]["diagnosticos"]
    assert isinstance(d, list) and any("RiR" in x for x in d)


def test_rota_equity_produz_equity_sem_ponte():
    r = avaliar(carregar(FIXTURES / "caso_minimo_equity.json"))
    assert "ponte" not in r or r["ponte"] is None
    v = r["cenarios"]["base"]["valor"]
    assert v["Equity"] == pytest.approx(4501.51, abs=0.01)
    assert v["preco_acao"] == pytest.approx(45.02, abs=0.01)
    assert "EV" not in v


def test_escala_por_nopat_reconcilia_com_a_escala_por_ebitda():
    """Mesma economia, duas rotas de escala: EV tem de bater.

    Com EBITDA 1000, d 20% e t 25%, o NOPAT coerente e 1000*(1-0.20)*(1-0.25) = 600.
    EV/NOPAT_curr x 600 tem de dar o mesmo EV que EV/EBITDA_curr x 1000.
    """
    c = carregar(FIXTURES / "caso_minimo_firm.json")
    c["metrica_base"] = {"tipo": "NOPAT", "valor": 600.0, "periodo": "2025A",
                         "fonte": "derivado do EBITDA da fixture"}
    r = avaliar(c)
    assert r["cenarios"]["base"]["valor"]["EV"] == pytest.approx(6690.59, abs=0.05)


def test_saida_e_deterministica():
    a = json.dumps(_res_firm(), sort_keys=True, ensure_ascii=False)
    b = json.dumps(_res_firm(), sort_keys=True, ensure_ascii=False)
    assert a == b


def test_saida_nao_carrega_hora_nem_caminho_absoluto():
    texto = json.dumps(_res_firm(), ensure_ascii=False)
    assert "C:\\" not in texto and "/c/" not in texto
    for suspeito in ("timestamp", "gerado_em", "executado_em"):
        assert suspeito not in texto


def test_escrever_e_reler_preserva(tmp_path):
    destino = tmp_path / "resultados.json"
    escrever(_res_firm(), destino)
    assert json.loads(destino.read_text(encoding="utf-8"))["rota"] == "firm"


def test_cli_gera_o_arquivo(tmp_path):
    destino = tmp_path / "out.json"
    r = subprocess.run(
        [sys.executable, str(SCRIPTS / "avaliar.py"),
         str(FIXTURES / "caso_minimo_firm.json"), "--out", str(destino)],
        capture_output=True, text=True, encoding="utf-8", timeout=120)
    assert r.returncode == 0, r.stdout + r.stderr
    assert json.loads(destino.read_text(encoding="utf-8"))["companhia"] == "Sintética S.A."


def test_cli_recusa_caso_invalido_com_exit_1(tmp_path):
    ruim = tmp_path / "ruim.json"
    c = json.loads((FIXTURES / "caso_minimo_firm.json").read_text(encoding="utf-8"))
    del c["cenarios"]["base"]["premissas"]["tv"]
    ruim.write_text(json.dumps(c), encoding="utf-8")
    r = subprocess.run(
        [sys.executable, str(SCRIPTS / "avaliar.py"), str(ruim), "--out", str(tmp_path / "x.json")],
        capture_output=True, text=True, encoding="utf-8", timeout=120)
    assert r.returncode == 1
    assert "convenção terminal" in (r.stdout + r.stderr)
```

- [ ] **Step 2: Rodar para ver falhar**

Run: `python -m pytest tests/test_valuation_avaliar.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'avaliar'`.

- [ ] **Step 3: Implementar `avaliar.py`**

Fluxo por cenário: monta a escala conforme a rota (firm ⟹ `ponte.compor` → `nd_efetivo`; se a métrica é `EBITDA`, passa `--ebitda/--nd/--acoes` e usa o `EV`/`Equity`/`Preco_acao` do motor; se é `NOPAT`, roda sem escala e aplica `EV = EV/NOPAT_curr × valor`, depois `Equity = EV − nd_efetivo` e `preco_acao = Equity / acoes_diluidas`, registrando a álgebra no campo `algebra_da_escala`); equity ⟹ passa `--ni/--acoes` e usa `Equity`/`Preco_acao` do motor. `upside = preco_acao / preco.valor − 1`.

`escrever` grava com `json.dumps(..., indent=2, ensure_ascii=False)` mais `\n` final, `encoding="utf-8"`, `newline="\n"`.

CLI com `argparse`: posicional `caso`, `--out` obrigatório; `CasoInvalido` e `MotorFalhou` viram mensagem em stderr e `sys.exit(1)`.

- [ ] **Step 4: Rodar para ver passar**

Run: `python -m pytest tests/test_valuation_avaliar.py -q`
Expected: PASS — 12 passed.

Se `test_escala_por_nopat_reconcilia_com_a_escala_por_ebitda` falhar, **não relaxe a tolerância**: investigue. As duas rotas de escala têm de dar o mesmo EV por identidade — divergência é erro de montagem, e é exatamente o que este teste existe para pegar.

- [ ] **Step 5: Suíte inteira**

Run: `python -m pytest tests/ -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add skills/er-valuation/scripts/avaliar.py tests/test_valuation_avaliar.py
git commit -m "$(cat <<'EOF'
feat(er-valuation): orquestracao caso -> resultados.json

Roda o motor por cenario na rota canonica, compoe a ponte e normaliza os
diagnosticos. Saida deterministica: sem hora de execucao, sem caminho
absoluto. As duas rotas de escala reconciliam o mesmo EV por identidade.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: `SKILL.md` do `er-valuation` e a colisão do manifesto

**Files:**
- Create: `skills/er-valuation/SKILL.md`
- Modify: `tests/test_manifesto.py`
- Create: `tests/test_valuation_skill.py`

**Interfaces:**
- Produces: a skill `er-valuation` carregável, que o `er-analise` (item 8) e o `er-relatorio` (item 5) citam.

**Colisão conhecida:** `tests/test_manifesto.py::test_v2_removida` afirma que `skills/er-valuation` **não** existe — era uma skill da v2, morta. Esta task cria uma skill nova com o mesmo nome. A entrada tem de sair da lista de mortos da v2, e a garantia que ela dava precisa ser substituída, não descartada.

- [ ] **Step 1: Escrever os testes (vão falhar)**

`tests/test_valuation_skill.py`:

```python
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SKILL = RAIZ / "skills" / "er-valuation"


def test_frontmatter_declara_o_nome_novo():
    texto = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    assert texto.startswith("---")
    assert "name: er-valuation" in texto


def test_skill_declara_o_que_nunca_faz():
    """A fronteira do wrapper e a razao de ele existir — tem de estar escrita."""
    texto = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    for obrigatorio in ("nunca", "motor", "sem default"):
        assert obrigatorio in texto.lower()


def test_skill_aponta_os_quatro_modulos():
    texto = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    for modulo in ("caso.py", "motor.py", "ponte.py", "avaliar.py"):
        assert modulo in texto


def test_skill_nao_e_a_v2_ressuscitada():
    """A v2 tinha engine proprio; a v4 chama o vendor. Nada da v2 pode voltar."""
    texto = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    for morto in ("cap_check", "engine v3.3.0", "K3", "16 canonical inputs", "justified"):
        assert morto.lower() not in texto.lower(), f"residuo da v2/v3: {morto}"
```

E em `tests/test_manifesto.py`, no teste `test_v2_removida`: remova `"skills/er-valuation"` da lista e acrescente, logo abaixo do laço, a garantia substituta:

```python
    # skills/er-valuation existe de novo na v4, com outro papel: wrapper do motor
    # congelado, sem engine proprio. A garantia que a entrada dava vira verificacao
    # de CONTEUDO — a skill nova nao pode ser a da v2 voltando.
    nova = RAIZ / "skills" / "er-valuation" / "SKILL.md"
    assert nova.is_file(), "er-valuation da v4 ausente"
    assert "name: er-valuation" in nova.read_text(encoding="utf-8")
    assert not (RAIZ / "skills" / "er-valuation" / "scripts" / "cap_check.py").exists()
```

- [ ] **Step 2: Rodar para ver falhar**

Run: `python -m pytest tests/test_valuation_skill.py tests/test_manifesto.py -q`
Expected: FAIL — `test_valuation_skill.py` não acha `SKILL.md`; `test_manifesto.py` falha por `skills/er-valuation` existir (Tasks 1-4 já criaram o diretório).

- [ ] **Step 3: Escrever o `SKILL.md`**

Crie `skills/er-valuation/SKILL.md` com exatamente este conteúdo:

````markdown
---
name: er-valuation
description: USE QUANDO montar o caso de valuation de uma análise, rodar o motor congelado por cenário, compor a ponte para preço ou interpretar o resultados.json. É a camada de orquestração entre a análise e a metodologia congelada. NÃO use para coletar evidência (er-evidencia), compor o relatório (er-relatorio) nem conduzir a análise (er-analise); e não use como fonte de metodologia — essa é er-multiplos-justos.
---

# er-valuation — wrapper de orquestração do motor congelado

Esta camada existe para uma coisa: transformar um caso declarado em resultado
auditável **sem tocar na conta**. Toda a matemática de valuation vem do motor
congelado; aqui só se monta entrada, soma linha de balanço declarada e
normaliza saída.

## O que faz

- **Contrato do caso** — valida o `caso.json` e recusa o que estiver incompleto.
- **Rota canônica** — traduz a rota declarada no subcomando certo do motor.
- **Cenários** — roda cada cenário com o vetor de premissas dele.
- **Ponte para preço** — soma as linhas de balanço declaradas num líquido e
  entrega ao motor, guardando cada parcela com seu sinal para o waterfall.
- **Normalização da saída** — junta múltiplos, valor, diagnósticos e a
  coerência do vetor num `resultados.json` determinístico.

## O que NUNCA faz

- Aritmética de valuation fora do motor. Nenhuma fórmula é reescrita aqui.
- Ajuste "conservador", arredondamento de conveniência ou correção de um
  output do motor. O que o motor devolve é o que sai.
- Default para escolha que a metodologia declara **sem default**. Caso
  incompleto é **recusado**, com o campo e a razão nomeados — a escolha é do
  analista, e silenciá-la com um padrão de fábrica seria decidir por ele.

## Módulos

| Arquivo | Responsabilidade |
|---|---|
| `scripts/caso.py` | Carrega e valida o caso; recusa omissão de escolha sem default |
| `scripts/motor.py` | Monta o argv por rota e executa o motor congelado |
| `scripts/ponte.py` | Soma as linhas da ponte num líquido, com sinal por parcela |
| `scripts/avaliar.py` | Orquestra cenários × rota e escreve o `resultados.json` |

## Como rodar

```bash
python skills/er-valuation/scripts/avaliar.py <caso.json> --out <resultados.json>
```

Caso inválido sai com código 1 e a razão em stderr. O motor é chamado no
interpretador corrente, com utf-8 fixo e bytecode desligado — a árvore
congelada não é suja nem pelo uso.

## Contrato do caso

Campos de topo: `companhia`, `moeda`, `data_analise`, `preco` (valor, fonte,
data), `rota`, `metrica_base` (tipo, valor, fonte), `acoes_diluidas`,
`cenarios`. A rota `firm` exige o bloco `ponte`; a rota `equity` o proíbe —
não há ponte de dívida quando o resultado já é do acionista.

Cada cenário declara `ancora` (o observável de que ele vem), `triangulo`
(quais duas variáveis são input e qual é output) e `premissas`. Cenário sem
âncora é cenário inventado; cenário sem a configuração do triângulo esconde
a taxa de reinvestimento que ele implica.

Schema completo, executável: `tests/fixtures/caso_minimo_firm.json` e
`tests/fixtures/caso_minimo_equity.json`.

## Escopo desta fatia

Métricas suportadas: rota `firm` aceita `EBITDA` e `NOPAT`; rota `equity`
aceita `LL`. São as que o motor emite diretamente — demais métricas são
transformação de apresentação e entram depois, com a álgebra exibida.

Ainda não implementados aqui: reversa e sensibilidades; soma das partes por
segmento e por safra de capital; composição multifásica. Cada um entra em sua
própria fatia.

## Metodologia

Não está aqui e não é resumida aqui. A fonte canônica é o pacote congelado,
indexado por `skills/er-multiplos-justos/SKILL.md`. Desenho:
`docs/desenho-arquitetura-v4.md`.
````

- [ ] **Step 4: Rodar para ver passar**

Run: `python -m pytest tests/test_valuation_skill.py tests/test_manifesto.py -q`
Expected: PASS.

- [ ] **Step 5: Suíte inteira**

Run: `python -m pytest tests/ -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add skills/er-valuation/SKILL.md tests/test_valuation_skill.py tests/test_manifesto.py
git commit -m "$(cat <<'EOF'
feat(er-valuation): SKILL.md do wrapper e ajuste da colisao com a v2

er-valuation volta a existir com outro papel: wrapper do motor congelado, sem
engine proprio. A entrada sai da lista de mortos da v2 e a garantia vira
verificacao de conteudo — a skill nova nao pode ser a da v2 voltando.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

## Verificação final da fatia 3A

- [ ] `python -m pytest tests/ -q` — verde
- [ ] `python skills/er-valuation/scripts/avaliar.py tests/fixtures/caso_minimo_firm.json --out /tmp/r.json` — exit 0
- [ ] `git status --short vendor` — vazio (o vendor não foi tocado nem sujado)
- [ ] `python vendor/multiplos-justos/scripts/testes.py` — `TODOS OS TESTES PASSARAM`
- [ ] Nenhum arquivo de `skills/er-motor-k3/`, `skills/er-dados-openbb/` ou `skills/er-relatorio-html/` no diff
