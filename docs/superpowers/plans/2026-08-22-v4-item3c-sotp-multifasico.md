# `er-valuation` — SOTP e multifásico (item 3, fatia C)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Avaliar companhias em que "um negócio só" é ficção — por segmento economicamente distinto, por safra de capital (base instalada × expansão) — e a rota de rampa que a base instalada exige, somando as partes e atravessando a ponte para preço **uma única vez, no topo**.

**Architecture:** Uma rota nova (`rampa`, que o motor já implementa no comando homônimo) e um módulo novo `sotp.py` que compõe partes, cada uma avaliada pelo caminho que já existe, e soma. `avaliar.py` ganha o bloco `sotp`. Nenhuma conta de valuation sai do motor: a soma de EVs de partes e a ponte no topo são a mesma categoria de aritmética já autorizada nas fatias A e B.

**Tech Stack:** Python 3.12+, stdlib pura, pytest.

## Global Constraints

- **Fonte de verdade:** `docs/desenho-arquitetura-v4.md`. Nenhuma decisão de produto é reaberta.
- **Regra inviolável 1:** a matemática de valuation vem do motor congelado. Nesta fatia acrescenta-se **uma** operação: a soma dos EVs das partes. Nada além disso.
- **Nunca ajustar um output do motor.** Diagnósticos, `checks_internos` e `travas` chegam íntegros.
- **Nenhum default para escolha sem default.** Recusar é o comportamento correto.
- **Determinismo:** o mesmo `caso.json` produz `resultados.json` byte a byte idêntico.
- **A árvore congelada não pode ser suja:** toda chamada mantém `sys.executable`, `encoding="utf-8"`, `PYTHONDONTWRITEBYTECODE=1`, `PYTHONUTF8=1`, e passa `caso["moeda"]`.
- Python 3.12+, stdlib pura, pytest. Nada de rede.
- Commits: conventional commits em PT-BR, trailer `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`.
- Não tocar em `vendor/`, `skills/er-motor-k3/`, `skills/er-dados-openbb/`, `skills/er-relatorio-html/`, `skills/er-multiplos-justos/`.
- Use Write/Edit para conteúdo de arquivo, nunca heredoc de shell.
- **`PYTHONUTF8=1` em tudo que imprime saída do motor** — o console desta máquina não codifica alguns caracteres e o `UnicodeEncodeError` parece falha de teste sem ser.

## Fora do escopo desta fatia

Curva `iso`; registro de drivers, `normaliza` e nível implícito (Gates 2 e 3 são fatia própria); confronto temporal contra consenso; degrau; ponte de releveraging; espelho JS (item 4); relatório (item 5). Não antecipe nada.

## Contrato do motor — comando `rampa`, shape real capturado em 2026-08-22

Vocabulário do CLI (`rampa --help`), obrigatórios sem colchete:

```
--receita0  --ebitda0  --da-parque  --wk  --kappa  --g2  --wacc  --tax  --t-rampa  --tv
[--n]  [--util | --g1]  [--roic-tv]  [--gp]  [--roic-book]  [--nd]  [--acoes]  [--rf]  [--moeda]
```

`--util` e `--g1` são alternativas: `util` deriva `g1 = (1/u)^(1/T) − 1` e faz `Receita_T = capacidade` por construção; `--g1` negativo roda o bloco de colheita. `--t-rampa` é declarado no próprio help do motor como **delimitador observável obrigatório**.

Saída de `rampa --receita0 265 --ebitda0 26.8 --da-parque 6.8 --wk 19.1 --util 65 --t-rampa 5 --g2 8 --kappa 17.9364 --wacc 11.9 --tax 35 --n 10 --tv convergencia --nd -104.6 --acoes 30.46`:

```
bloco (str) · g1_% 8.9977 · g2_% 8.0 · T_rampa 5 · n_total 10
d_trajetoria_fase1_% {ano_1: 23.279, ano_5: 16.493}
rir_fase1_% {ano_1: 31.263, ano_5: 28.722, nota: "VARIA — a rampa não tem vetor único..."}
alfa 13.24176 · beta -4.42 · rir2_% 49.977 · roic2_% 16.007
vp_fase1 45.2592 · valor_fase2_no_ano_T 220.4887
EV 170.9304 · EV/EBITDA0 6.378
checks_internos {P1_fluxo_a_fluxo_max_abs 1.07e-14, P1b_vp_fechado_vs_explicito 0.0,
                 P3 "fase 2 = ev_nopat do próprio motor", P4_receita_T_menos_capacidade 0.0}
travas (3 strings) · capacidade_receita 407.6923 · convencao_moeda
Equity 275.53 · Preco_acao 9.05        # só com --nd/--acoes
```

**Três observações que mudam o desenho:**

1. O múltiplo-manchete é `EV/EBITDA0` — sobre o EBITDA do **ano 0**, não sobre um EBITDA normalizado. A métrica-base da rota `rampa` é, portanto, `ebitda0`.
2. `rir_fase1_%` traz a nota de que **varia ano a ano** — a rampa não tem vetor único. Isso não é ruído: é a razão de a forma fechada α/β existir. Chega íntegro.
3. As `travas` incluem o **delimitador**: "declare o evento observável — comissionamento datado, plena capacidade, termo de contrato, marco de guidance". O motor não pode verificar isso; o gate precisa exigir.

## Decisões de projeto já tomadas — não reabra, implemente

**D1 — `rampa` é uma terceira rota canônica, com vocabulário próprio.** Não é variação de `firm`. Métrica-base `EBITDA0`. A ponte para preço é a mesma das outras rotas firm: o `nd_efetivo` da `ponte.py` vai em `--nd`.

**D2 — O delimitador é campo obrigatório do caso na rota `rampa`.** String não-vazia descrevendo o **evento observável** que fecha a fase 1. Sem ele o caso é recusado, com a razão: fase sem delimitador é grau de liberdade disfarçado de análise, e um modelo multifásico sem essa trava racionaliza qualquer preço.

**D3 — SOTP soma EVs de partes e atravessa a ponte UMA vez, no topo.** Cada parte tem rota, métrica, convenção, âncora e triângulo próprios — uma parte em `gordon` e outra em `book` é normal, não inconsistência. Custos corporativos não alocados e participações não consolidadas entram **só no topo**, junto com a ponte do caso. Ponte por parte é o erro que a trava existe para impedir.

**D4 — Desconto de holding só existe declarado com razão, e incide sobre o equity.** Percentual presente exige razão não-vazia — a metodologia é explícita: não aplique por hábito. Quando existir, incide **depois da ponte**, sobre o equity value, e a saída traz o valor antes e depois, nunca só o líquido.

**D4b — Sinais do topo, para não ficarem à interpretação.** `ev_total = soma_das_partes − custos_corporativos_vp + participacoes_nao_consolidadas`. Custo corporativo não alocado é despesa capitalizada, subtrai; participação não consolidada é ativo, soma. Depois disso, e só depois, a ponte do caso.

**D5 — A verificação de materialidade é um número com sinal, não uma opinião.** Quando o caso declarar o vetor `blended`, roda-se também o consolidado e reporta-se `EV_segmentado − EV_blended` com o sinal. A direção do viés **se calcula, não se deduz** — a Hessiana é indefinida na região relevante e a intuição erra.

**D6 — Na safra de capital existe uma parede, e ela é checável.** `tipo: "safra"` exige exatamente **uma** parte na rota `rampa` (a base instalada) e nenhuma outra nela (a expansão vai pelo fluxo padrão). É a tradução mecânica da regra "o crescimento da parte instalada é SÓ rampa; o da expansão é SÓ capital novo — a mesma receita nunca aparece nas duas".

**D7 — Claims homogêneos: a soma tem de bater com o consolidado, e isso é teste.** Para um dado vetor de premissas o múltiplo não depende da escala, então duas partes com premissas idênticas e métricas `m1` e `m2` dão `mult×m1 + mult×m2 = mult×(m1+m2)` — exatamente o consolidado. É identidade, não aproximação, e é o teste que prova que a soma faz o que diz. A metodologia usa isso normativamente: com claims homogêneos, declare a equivalência e rode consolidado em vez de abrir SOTP.

## Contrato do caso — o que a fatia C acrescenta

Rota `rampa` (alternativa a `firm`/`equity` no campo `rota`):

```json
{
  "rota": "rampa",
  "metrica_base": {"tipo": "EBITDA0", "valor": 26.8, "periodo": "2025A", "fonte": "..."},
  "delimitador": "comissionamento da linha 3 datado no guidance de 4T25",
  "cenarios": {
    "base": {
      "ancora": "utilização divulgada de 65% no 3T25",
      "triangulo": {"inputs": ["g", "roic"], "output": "rir"},
      "premissas": {
        "receita0": 265.0, "ebitda0": 26.8, "da_parque": 6.8, "wk": 19.1,
        "kappa": 17.9364, "util": 65.0, "t_rampa": 5, "g2": 8.0,
        "wacc": 11.9, "tax": 35.0, "n": 10, "tv": "convergencia"
      }
    }
  }
}
```

Bloco `sotp` (opcional, e independente da rota do caso):

```json
"sotp": {
  "tipo": "segmento",
  "partes": [
    {"nome": "Industrial", "rota": "firm",
     "metrica_base": {"tipo": "EBITDA", "valor": 700.0, "fonte": "nota de segmentos"},
     "ancora": "média normalizada 2023-2025",
     "triangulo": {"inputs": ["g", "roic"], "output": "rir"},
     "premissas": {"g": 4.0, "roic": 11.0, "wacc": 10.0, "n": 10,
                   "da": 22.0, "tax": 25.0, "tv": "convergencia"}},
    {"nome": "Serviços", "rota": "firm",
     "metrica_base": {"tipo": "EBITDA", "valor": 300.0, "fonte": "nota de segmentos"},
     "ancora": "consenso t+1",
     "triangulo": {"inputs": ["g", "roic"], "output": "rir"},
     "premissas": {"g": 8.0, "roic": 22.0, "wacc": 11.0, "n": 12,
                   "da": 8.0, "tax": 25.0, "tv": "gordon", "roic_tv": 14.0, "gp": 3.0}}
  ],
  "topo": {
    "custos_corporativos_vp": 400.0,
    "participacoes_nao_consolidadas": 0.0,
    "desconto_de_holding_pct": null,
    "razao_do_desconto": null
  },
  "materialidade": {
    "blended": {"ancora": "consolidado, premissas ponderadas por EBITDA",
                "triangulo": {"inputs": ["g", "roic"], "output": "rir"},
                "metrica_base": {"tipo": "EBITDA", "valor": 1000.0, "fonte": "consolidado"},
                "premissas": {"g": 5.2, "roic": 14.3, "wacc": 10.3, "n": 10,
                              "da": 17.8, "tax": 25.0, "tv": "convergencia"}}
  }
}
```

## File Structure

| Arquivo | Responsabilidade |
|---|---|
| `skills/er-valuation/scripts/sotp.py` | Compor partes, somar EVs, aplicar o topo, calcular a materialidade |
| `skills/er-valuation/scripts/caso.py` | Rota `rampa`, delimitador, bloco `sotp` (modificado) |
| `skills/er-valuation/scripts/motor.py` | Subcomando `rampa` no argv (modificado) |
| `skills/er-valuation/scripts/avaliar.py` | Rota `rampa` e bloco `sotp` no resultado (modificado) |
| `skills/er-valuation/SKILL.md` | Escopo atualizado (modificado) |
| `tests/test_valuation_sotp.py` | Testes do módulo novo |
| `tests/fixtures/caso_rampa.json` · `caso_sotp_segmento.json` · `caso_sotp_homogeneo.json` | Fixtures |

---

### Task 1: Rota `rampa`

**Files:**
- Modify: `skills/er-valuation/scripts/caso.py`, `motor.py`, `avaliar.py`
- Modify: `tests/test_valuation_caso.py`, `tests/test_valuation_motor.py`, `tests/test_valuation_avaliar.py`
- Create: `tests/fixtures/caso_rampa.json`

**Interfaces:**
- Produces: `PREMISSAS_RAMPA: frozenset` e `PREMISSAS_OBRIGATORIAS_RAMPA: frozenset`; `"rampa"` em `_PREMISSAS_POR_ROTA`, `_PREMISSAS_OBRIGATORIAS_POR_ROTA`, `METRICAS_POR_ROTA` (`{"EBITDA0"}`) e no mapa de subcomandos de `motor.py`; `precificar_rampa` em `avaliar.py`, na forma dos irmãos `precificar_firm`/`precificar_equity`.

`PREMISSAS_RAMPA` = `{receita0, ebitda0, da_parque, wk, kappa, g2, wacc, tax, t_rampa, n, util, g1, tv, roic_tv, gp, roic_book}`.
`PREMISSAS_OBRIGATORIAS_RAMPA` = `{receita0, ebitda0, da_parque, wk, kappa, g2, wacc, tax, t_rampa, tv}`.

- [ ] **Step 1: Fixture**

`tests/fixtures/caso_rampa.json` — o caso do contrato acima, com `preco` (valor 9.0, fonte e data), `acoes_diluidas` 30.46, `ponte` com `divida_bruta` 0.0, `caixa_e_equivalentes` 104.6 e o resto zero (⟹ `nd_efetivo` = −104.6, o caixa líquido da âncora do motor), `companhia`, `moeda` `BRL-nominal`, `data_analise`.

- [ ] **Step 2: Testes (vão falhar)**

Em `tests/test_valuation_caso.py`:

```python
def _rampa() -> dict:
    return json.loads((FIXTURES / "caso_rampa.json").read_text(encoding="utf-8"))


def test_fixture_rampa_e_valida():
    assert carregar(FIXTURES / "caso_rampa.json")["rota"] == "rampa"


def test_rampa_sem_delimitador_recusa():
    """Fase sem delimitador observavel e grau de liberdade disfarcado de analise."""
    c = _rampa()
    del c["delimitador"]
    with pytest.raises(CasoInvalido, match="delimitador"):
        validar(c)


def test_rampa_com_delimitador_vazio_recusa():
    c = _rampa()
    c["delimitador"] = "   "
    with pytest.raises(CasoInvalido, match="delimitador"):
        validar(c)


def test_delimitador_em_outra_rota_recusa():
    """So a rota rampa tem fronteira de fase para delimitar."""
    c = _firm()
    c["delimitador"] = "qualquer coisa"
    with pytest.raises(CasoInvalido, match="delimitador"):
        validar(c)


@pytest.mark.parametrize("campo", ["receita0", "ebitda0", "da_parque", "wk",
                                   "kappa", "g2", "wacc", "tax", "t_rampa", "tv"])
def test_rampa_sem_premissa_obrigatoria_recusa(campo):
    c = _rampa()
    del c["cenarios"]["base"]["premissas"][campo]
    with pytest.raises(CasoInvalido, match=campo):
        validar(c)


def test_rampa_sem_util_nem_g1_recusa():
    """util deriva g1; sem um dos dois a rampa nao tem crescimento de fase 1."""
    c = _rampa()
    del c["cenarios"]["base"]["premissas"]["util"]
    with pytest.raises(CasoInvalido, match="util"):
        validar(c)


def test_rampa_com_util_e_g1_juntos_recusa():
    c = _rampa()
    c["cenarios"]["base"]["premissas"]["g1"] = 9.0
    with pytest.raises(CasoInvalido, match="util"):
        validar(c)


def test_rampa_com_metrica_errada_recusa():
    c = _rampa()
    c["metrica_base"]["tipo"] = "EBITDA"
    with pytest.raises(CasoInvalido, match="EBITDA0"):
        validar(c)
```

Em `tests/test_valuation_motor.py`:

```python
PREMISSAS_RAMPA = {"receita0": 265.0, "ebitda0": 26.8, "da_parque": 6.8, "wk": 19.1,
                   "kappa": 17.9364, "util": 65.0, "t_rampa": 5, "g2": 8.0,
                   "wacc": 11.9, "tax": 35.0, "n": 10, "tv": "convergencia"}


def test_argv_rampa_usa_o_subcomando_rampa_e_traduz_as_chaves():
    argv = argv_para("rampa", PREMISSAS_RAMPA, None)
    assert argv[0] == "rampa"
    assert "--da-parque" in argv and "--t-rampa" in argv
    assert "--receita0" in argv and "--ebitda0" in argv
    assert "--roic" not in argv and "--roe" not in argv


def test_rodar_rampa_reproduz_a_ancora_do_motor():
    """Ancora da planilha ELMT, travada no selftest do vendor."""
    out = rodar("rampa", PREMISSAS_RAMPA, {"nd": -104.6, "acoes": 30.46})
    assert out["EV"] == pytest.approx(170.9304, abs=1e-3)
    assert out["vp_fase1"] == pytest.approx(45.2592, abs=1e-3)
    assert out["valor_fase2_no_ano_T"] == pytest.approx(220.4887, abs=1e-3)
    assert out["EV/EBITDA0"] == pytest.approx(6.378, abs=1e-3)
    assert out["Preco_acao"] == pytest.approx(9.05, abs=0.01)


def test_checks_internos_e_travas_chegam_intactos():
    out = rodar("rampa", PREMISSAS_RAMPA, None)
    assert out["checks_internos"]["P4_receita_T_menos_capacidade"] == pytest.approx(0.0)
    assert abs(out["checks_internos"]["P1_fluxo_a_fluxo_max_abs"]) < 1e-10
    assert any("DELIMITADOR" in t for t in out["travas"])
    assert "VARIA" in out["rir_fase1_%"]["nota"]
```

Em `tests/test_valuation_avaliar.py`:

```python
def test_rota_rampa_produz_valor_e_multiplo_sobre_ebitda0():
    r = avaliar(carregar(FIXTURES / "caso_rampa.json"))
    v = r["cenarios"]["base"]["valor"]
    assert v["EV"] == pytest.approx(170.9304, abs=1e-2)
    assert v["preco_acao"] == pytest.approx(9.05, abs=0.01)
    assert r["cenarios"]["base"]["multiplos"]["EV/EBITDA0"] == pytest.approx(6.378, abs=1e-3)


def test_rampa_leva_checks_e_travas_ao_resultado():
    r = avaliar(carregar(FIXTURES / "caso_rampa.json"))["cenarios"]["base"]
    assert r["checks_internos"]["P4_receita_T_menos_capacidade"] == pytest.approx(0.0)
    assert len(r["travas"]) == 3
```

- [ ] **Step 3: Rodar para ver falhar** — `PYTHONUTF8=1 python -m pytest tests/ -q -k "rampa"` → FAIL.

- [ ] **Step 4: Implementar**

Em `caso.py`: as duas constantes, a rota nos três mapas, `METRICAS_POR_ROTA["rampa"] = frozenset({"EBITDA0"})`, a exigência do `delimitador` **apenas** na rota `rampa` (e a recusa dele nas outras), e a regra `util` XOR `g1`. Reaproveite os helpers de guarda e de número que já existem — não escreva variante nova.

Em `motor.py`: `"rampa"` no mapa de subcomandos, e a tradução de chave para flag (`da_parque` → `--da-parque`, `t_rampa` → `--t-rampa`) acrescentada à tabela de hífens existente. O teste de invariante cross-module que já existe vai cobrar essas duas — é para isso que ele foi escrito.

Em `avaliar.py`: `precificar_rampa`, na forma dos irmãos: usa `EV`, `Equity`, `Preco_acao` do motor (a rota tem `--nd`/`--acoes`), passa pela mesma recusa de `null`, e leva ao resultado `checks_internos`, `travas`, `d_trajetoria_fase1_%`, `rir_fase1_%`, `capacidade_receita` além dos campos que as outras rotas já levam.

- [ ] **Step 5: Rodar para ver passar** · **Step 6: Suíte inteira** (base 307) · **Step 7: `git status --short vendor` vazio**

- [ ] **Step 8: Commit**

```bash
git commit -m "$(cat <<'EOF'
feat(er-valuation): rota rampa com delimitador obrigatorio

Terceira rota canonica, vocabulario proprio e metrica-base EBITDA0. O
delimitador observavel da fronteira de fase e exigido no gate: fase sem
delimitador e grau de liberdade disfarcado de analise.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: SOTP — partes, soma e ponte única no topo

**Files:**
- Create: `skills/er-valuation/scripts/sotp.py`, `tests/test_valuation_sotp.py`
- Create: `tests/fixtures/caso_sotp_segmento.json`
- Modify: `skills/er-valuation/scripts/caso.py`, `tests/test_valuation_caso.py`

**Interfaces:**
- Consumes: `motor.rodar`, `ponte.compor`, e as funções `precificar_*` de `avaliar.py`.
- Produces: `compor_partes(caso, nome_cenario) -> dict` com `{"partes": [...], "ev_das_partes": float, "topo": {...}, "ev_total": float, "equity": float, "preco_acao": float, "ponte_unica": {...}}`.

- [ ] **Step 1: Fixture** — `caso_sotp_segmento.json`: rota do caso `firm`, dois segmentos como no contrato acima, `topo` com `custos_corporativos_vp` 400.0, `participacoes_nao_consolidadas` 0.0, `desconto_de_holding_pct` e `razao_do_desconto` nulos, `ponte` do caso com dívida 800 e caixa 300, `acoes_diluidas` 100.0, `preco` 55.0, mais o bloco `materialidade.blended` do contrato.

Acrescente também, no topo de `tests/test_valuation_sotp.py`, os helpers que os testes usam:

```python
def _sotp() -> dict:
    return json.loads((FIXTURES / "caso_sotp_segmento.json").read_text(encoding="utf-8"))


def _safra() -> dict:
    return json.loads((FIXTURES / "caso_sotp_safra.json").read_text(encoding="utf-8"))
```

- [ ] **Step 2: Testes (vão falhar)**

```python
def test_cada_parte_e_avaliada_com_a_propria_convencao():
    r = compor_partes(_sotp(), "base")
    convs = {p["nome"]: p["premissas"]["tv"] for p in r["partes"]}
    assert convs == {"Industrial": "convergencia", "Serviços": "gordon"}


def test_ev_total_e_a_soma_das_partes_menos_o_topo():
    r = compor_partes(_sotp(), "base")
    soma = sum(p["EV"] for p in r["partes"])
    assert r["ev_das_partes"] == pytest.approx(soma)
    assert r["ev_total"] == pytest.approx(soma - 400.0)


def test_a_ponte_atravessa_uma_vez_so():
    """Ponte por parte e o erro que a trava existe para impedir."""
    r = compor_partes(_sotp(), "base")
    for p in r["partes"]:
        assert "Equity" not in p and "preco_acao" not in p
    assert r["ponte_unica"]["nd_efetivo"] == pytest.approx(500.0)
    assert r["equity"] == pytest.approx(r["ev_total"] - 500.0)
    assert r["preco_acao"] == pytest.approx(r["equity"] / 100.0)


def test_desconto_de_holding_sem_razao_recusa():
    c = _sotp()
    c["sotp"]["topo"]["desconto_de_holding_pct"] = 15.0
    with pytest.raises(CasoInvalido, match="razão"):
        validar(c)


def test_desconto_de_holding_com_razao_e_aplicado_e_declarado():
    c = _sotp()
    c["sotp"]["topo"]["desconto_de_holding_pct"] = 15.0
    c["sotp"]["topo"]["razao_do_desconto"] = "controlador com histórico de não distribuir"
    r = compor_partes(c, "base")
    assert r["topo"]["desconto_de_holding_pct"] == 15.0
    assert r["topo"]["razao_do_desconto"]


def test_parte_sem_ancora_ou_triangulo_recusa():
    for campo in ("ancora", "triangulo"):
        c = _sotp()
        del c["sotp"]["partes"][0][campo]
        with pytest.raises(CasoInvalido, match=campo.replace("ancora", "âncora")):
            validar(c)


def test_sotp_com_uma_parte_so_recusa():
    """Soma de uma parte e o consolidado com passos a mais."""
    c = _sotp()
    c["sotp"]["partes"] = c["sotp"]["partes"][:1]
    with pytest.raises(CasoInvalido, match="partes"):
        validar(c)


def test_nomes_de_parte_repetidos_recusam():
    c = _sotp()
    c["sotp"]["partes"][1]["nome"] = c["sotp"]["partes"][0]["nome"]
    with pytest.raises(CasoInvalido, match="nome"):
        validar(c)


def test_diagnosticos_de_cada_parte_chegam():
    r = compor_partes(_sotp(), "base")
    assert all(p["diagnosticos"] for p in r["partes"])
```

- [ ] **Step 3: Rodar para ver falhar** · **Step 4: Implementar `sotp.py` + a validação em `caso.py`** · **Step 5: ver passar** · **Step 6: suíte inteira** · **Step 7: commit**

Nas Tasks 2, 3 e 4 a mensagem de commit é sua — conventional commit em PT-BR, assunto dizendo o que a task entrega e corpo dizendo a razão econômica ou estrutural, com o trailer. As Tasks anteriores traziam a mensagem pronta; aqui não trazem porque o conteúdo depende de escolhas que você fará ao implementar.

Regras da validação: `sotp` opcional; presente, exige `tipo` em `{"segmento","safra"}`, `partes` lista com ≥ 2 itens, nomes distintos, cada parte com `nome`, `rota`, `metrica_base`, `ancora`, `triangulo` e `premissas` válidos para a rota **dela**; `topo` com os quatro campos, `desconto_de_holding_pct` exigindo `razao_do_desconto` não-vazia.

---

### Task 3: Materialidade, parede da safra e identidade dos claims homogêneos

**Files:**
- Modify: `skills/er-valuation/scripts/sotp.py`, `caso.py`
- Modify: `tests/test_valuation_sotp.py`, `tests/test_valuation_caso.py`
- Create: `tests/fixtures/caso_sotp_homogeneo.json`

**Interfaces:**
- Produces: `materialidade(caso, nome_cenario, ev_segmentado) -> dict | None` com `{"ev_blended": float, "ev_segmentado": float, "diferenca": float, "sinal": "+"|"-"|"0", "leitura": str}`. `compor_partes` passa a chamá-la e a devolver o resultado sob a chave `materialidade` — `None` quando o caso não declara `blended`.

- [ ] **Step 1: Testes (vão falhar)**

```python
def test_materialidade_reporta_a_diferenca_com_sinal():
    """A direcao do vies se calcula, nao se deduz."""
    r = compor_partes(_sotp(), "base")
    m = r["materialidade"]
    assert m["diferenca"] == pytest.approx(m["ev_segmentado"] - m["ev_blended"])
    assert m["sinal"] in ("+", "-", "0")


def test_materialidade_ausente_quando_o_caso_nao_declara_blended():
    c = _sotp()
    del c["sotp"]["materialidade"]
    assert compor_partes(c, "base").get("materialidade") is None


def test_safra_exige_exatamente_uma_parte_em_rampa():
    """Parede: a instalada e SO rampa, a expansao e SO capital novo."""
    c = _sotp()
    c["sotp"]["tipo"] = "safra"
    with pytest.raises(CasoInvalido, match="rampa"):
        validar(c)


def test_safra_com_duas_rampas_recusa():
    c = _safra()
    c["sotp"]["partes"][1]["rota"] = "rampa"
    c["sotp"]["partes"][1]["premissas"] = dict(c["sotp"]["partes"][0]["premissas"])
    c["sotp"]["partes"][1]["metrica_base"] = {"tipo": "EBITDA0", "valor": 10.0, "fonte": "x"}
    with pytest.raises(CasoInvalido, match="rampa"):
        validar(c)


def test_claims_homogeneos_somam_exatamente_o_consolidado():
    """Identidade, nao aproximacao: para um vetor de premissas o multiplo nao
    depende da escala, entao mult*m1 + mult*m2 = mult*(m1+m2)."""
    r = compor_partes(carregar(FIXTURES / "caso_sotp_homogeneo.json"), "base")
    from motor import rodar
    partes = carregar(FIXTURES / "caso_sotp_homogeneo.json")["sotp"]["partes"]
    soma_metrica = sum(p["metrica_base"]["valor"] for p in partes)
    consolidado = rodar("firm", partes[0]["premissas"],
                        {"ebitda": soma_metrica, "nd": 0.0, "acoes": 1.0})
    assert r["ev_das_partes"] == pytest.approx(consolidado["EV"], abs=0.01)
```

**Duas fixtures novas nesta task:**

`caso_sotp_homogeneo.json` — duas partes com premissas **idênticas** e métricas 600 e 400, `topo` todo zerado, sem `materialidade`. É a fixture da identidade.

`caso_sotp_safra.json` — `tipo: "safra"`, duas partes: a base instalada na rota `rampa` (as premissas da fixture `caso_rampa.json`, com o `delimitador` **na parte**, não no caso) e a expansão na rota `firm` pelo fluxo padrão. `topo` zerado. É a fixture da parede.

**Consequência de contrato:** na rota `rampa` o `delimitador` é campo do caso quando a rota é do caso, e campo **da parte** quando a rampa é uma parte de SOTP. Valide nos dois lugares, com a mesma regra e a mesma mensagem.

- [ ] **Step 2–6:** ver falhar, implementar, ver passar, suíte, commit.

A `leitura` da materialidade é uma frase do wrapper dizendo o que o sinal significa — segmentado acima do blended significa que o consolidado **subestima**, e vice-versa — sem adjetivar se é muito ou pouco.

---

### Task 4: Integração e escopo da skill

**Files:**
- Modify: `skills/er-valuation/scripts/avaliar.py`, `skills/er-valuation/SKILL.md`
- Modify: `tests/test_valuation_avaliar.py`, `tests/test_valuation_skill.py`

- [ ] **Step 1: Testes (vão falhar)**

```python
def test_resultado_sem_sotp_nao_ganha_o_bloco():
    r = avaliar(carregar(FIXTURES / "caso_minimo_firm.json"))
    assert "sotp" not in r


def test_resultado_com_sotp_traz_partes_e_ponte_unica():
    r = avaliar(carregar(FIXTURES / "caso_sotp_segmento.json"))
    assert len(r["sotp"]["partes"]) == 2
    assert r["sotp"]["preco_acao"] > 0
    assert r["sotp"]["materialidade"]["sinal"] in ("+", "-", "0")


def test_sotp_e_deterministico(tmp_path):
    import filecmp
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    escrever(avaliar(carregar(FIXTURES / "caso_sotp_segmento.json")), a)
    escrever(avaliar(carregar(FIXTURES / "caso_sotp_segmento.json")), b)
    assert filecmp.cmp(a, b, shallow=False)
```

E em `test_valuation_skill.py`, que o `SKILL.md` já não declara SOTP e multifásico como fatia futura, e que a rota `rampa` aparece.

- [ ] **Step 2–5:** ver falhar, implementar, ver passar, suíte inteira.

- [ ] **Step 6: Verificação de ponta a ponta**

```bash
PYTHONUTF8=1 python skills/er-valuation/scripts/avaliar.py tests/fixtures/caso_sotp_segmento.json --out /tmp/sotp.json
PYTHONUTF8=1 python skills/er-valuation/scripts/avaliar.py tests/fixtures/caso_rampa.json --out /tmp/rampa.json
```

Registre os dois no relatório: partes, EV somado, topo, ponte, preço/ação, sinal da materialidade; e para a rampa, EV, `EV/EBITDA0`, `checks_internos` e as travas.

- [ ] **Step 7: Commit**

---

## Verificação final da fatia 3C

- [ ] `PYTHONUTF8=1 python -m pytest tests/ -q` — verde
- [ ] caso da fatia A produz exatamente o que produzia (sem `sotp`, sem `rampa`)
- [ ] duas execuções do mesmo caso, byte a byte idênticas
- [ ] a âncora do motor na rampa reproduz (EV 170,9304 · fase1 45,2592 · fase2@T 220,4887)
- [ ] claims homogêneos somam exatamente o consolidado
- [ ] `git status --short vendor` vazio
- [ ] `PYTHONUTF8=1 python vendor/multiplos-justos/scripts/testes.py` — `TODOS OS TESTES PASSARAM`
