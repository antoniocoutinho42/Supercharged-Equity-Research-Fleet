# `er-valuation` — reversa e sensibilidades (item 3, fatia B)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Responder "o que está no preço" — o menu de reconciliação por eixo, com custo de capital implícito obrigatório e beta implícito confrontável — e produzir grades de sensibilidade construídas célula a célula no motor congelado, cada uma declarando a configuração do triângulo e a métrica de referência.

**Architecture:** Dois módulos novos sob `skills/er-valuation/scripts/`: `reversa.py` (alvo de mercado, eixos, tradução para beta implícito, teto do crescimento gratuito) e `sensibilidades.py` (grades 1D e 2D, célula a célula). Ambos consumidos por `avaliar.py`, que passa a emitir os blocos `reversa` e `sensibilidades` no mesmo `resultados.json`. Nenhuma conta de valuation sai do motor.

**Tech Stack:** Python 3.12+, stdlib pura, pytest.

## Global Constraints

- **Fonte de verdade:** `docs/desenho-arquitetura-v4.md`. Nenhuma decisão de produto é reaberta.
- **Regra inviolável 1:** a matemática de valuation vem do motor congelado. A única aritmética permitida nesta fatia, além da já existente, é: (i) o múltiplo de mercado, que é a definição de múltiplo aplicada a dados declarados; (ii) o beta implícito, que é a inversão declarada do CAPM sobre um output do motor. Ambas com a álgebra registrada na saída. Nada além disso.
- **Nunca ajustar um output do motor.** `sem_solucao`, `sugestao`, `assumidas_por_default`, `identificacao_por_raiz` e `guardas_v9_4` chegam ao resultado **íntegros** — são o produto, não ruído a filtrar.
- **Nenhum default para escolha sem default.** O custo de capital implícito é eixo obrigatório da metodologia em toda rodada: um caso que peça reversa sem ele é **recusado**, não completado em silêncio.
- **Determinismo:** o mesmo `caso.json` produz `resultados.json` byte a byte idêntico. Sem hora de execução, sem caminho absoluto, sem valor de ambiente.
- **A árvore congelada não pode ser suja:** toda chamada mantém `sys.executable`, `encoding="utf-8"`, `PYTHONDONTWRITEBYTECODE=1`, `PYTHONUTF8=1`.
- Python 3.12+, stdlib pura, pytest. Nada de rede.
- Commits: conventional commits em PT-BR, trailer `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`.
- Não tocar em `vendor/`, `skills/er-motor-k3/`, `skills/er-dados-openbb/`, `skills/er-relatorio-html/`, `skills/er-multiplos-justos/`.
- Use Write/Edit para conteúdo de arquivo, nunca heredoc de shell.

## Fora do escopo desta fatia

Curva `iso`; registro de drivers, `normaliza` e nível implícito (a maquinaria dos Gates 2 e 3 é fatia própria); confronto temporal contra consenso; SOTP e multifásico (fatia 3C); espelho JS (item 4); relatório (item 5). Não antecipe nada — nem esqueleto.

Quando um eixo primário não tiver raiz, o motor **sugere** rodar a curva iso; esta fatia repassa a sugestão íntegra e executa apenas o teto do crescimento gratuito, que é o passo que ela cobre.

## Contrato do motor — shapes reais, capturados em 2026-08-21

Rodados contra o vendor congelado nesta máquina. Use estas chaves.

`rev --alvo 8 --resolver wacc --g 5 --roic 12 --n 10 --da 20 --tax 25 --tv gordon --roic-tv 10 --gp 3` devolve, no caso COM raiz:

```
premissa_regime (str)
premissas_fixadas {informadas, assumidas_por_default, nao_aplicaveis, nota}
guardas_v9_4 (lista de str)
alvo_normalizado_EV/NOPAT (float)     # o nome da chave varia com --base
base_do_alvo (str)
faixa_de_busca {variavel, de_%, ate_%, restricao}
raizes_<variavel>_% (lista de float)  # ex.: raizes_wacc_%
identificacao_por_raiz {"<raiz>%": {slope_dM_dx, curvatura_d2M_dx2, elasticidade,
                                    "intervalo_para_alvo_±1%", largura_relativa_%,
                                    identificacao, nota}}
```

Com `--alvo 8 --resolver wacc` sobre esse vetor: `raizes_wacc_%` = `[8.947]`, identificação **forte**, largura relativa 0,6%.

No caso SEM raiz (`--alvo 60 --resolver roic --tv book`), `raizes_roic_%` vem `[]` e aparecem duas chaves a mais:

```
sem_solucao (str)   # "máximo atingível 13.18 | mínimo 7.99 — alvo incompatível..." + ordem de investigação
sugestao (str)      # os dois passos obrigatórios: teto do crescimento gratuito e curva iso
```

Sob `--tv book` sem `--roic-book`, `premissas_fixadas.assumidas_por_default` traz o aviso de conflação marginal×médio ("erro pode passar de 30%"). Ele **tem de** chegar ao resultado.

**O eixo `cap` tem shape PRÓPRIO — não assuma uniformidade.** `rev --resolver cap` não devolve `raizes_*`, nem `identificacao_por_raiz`, nem `sem_solucao`, nem `sugestao`. Devolve:

```
CAP_implicito_anos   # float quando alcançável (ex.: 1.0)
                     # STRING quando não (ex.: ">60 — alvo incompatível ... (máx em n=60: 12.14)")
alvo_normalizado (float) · direcao (str) · nota (str) · faixa_de_busca {variavel, de_anos, ate_anos, restricao}
```

Consequências obrigatórias: o wrapper **repassa cada eixo com o shape que o motor deu**, sem normalizar para um formato comum; e o gatilho do teto (Task 3) olha só os eixos primários `rentabilidade` e `crescimento`, que são os que usam `raizes_*`. Código que faça `eixo["raizes_..."]` sem checar a existência quebra no `cap`.

**`--base`:** obrigatório e determinado pela rota e pela métrica — firm + EBITDA ⟹ `--base ebitda`; firm + NOPAT ⟹ `--base nopat`; equity ⟹ `--base pl`. O motor **trava** combinações inconsistentes (resolver `ke`/`roe` exige `--base pl`).

**`--alvo-base`:** default `corrente`. A métrica-base do caso é corrente, então passe `--alvo-base corrente` **explicitamente** — a metodologia avisa que alvo de tela NTM confrontado contra base corrente injeta erro de `(1+g)` que volta como premissa falsa.

**`tabela`:** imprime **texto formatado, não JSON**. Não é fonte de dado. Grades se constroem célula a célula com `ev`, como a metodologia manda.

## Decisões de projeto já tomadas — não reabra, implemente

**D1 — Blocos novos são opcionais; exigências surgem quando são usados.** `mercado` e `reversa` são blocos opcionais do caso. As fixtures da fatia A continuam válidas sem eles. **Se** `reversa` estiver presente, então `mercado.rf` e `mercado.erp` passam a ser obrigatórios (sem eles não há beta implícito) e `custo_capital` **tem de** estar entre os eixos.

**D2 — O alvo é o múltiplo de mercado, com a álgebra declarada.** Rota firm: `EV_mercado = preço × ações + nd_efetivo`, `alvo = EV_mercado ÷ métrica`. Rota equity: `alvo = preço × ações ÷ lucro`. É a definição de múltiplo aplicada a dados declarados — mesma categoria da escala da fatia A —, e o campo `algebra_do_alvo` registra a conta com os números.

**D3 — Beta implícito é inversão declarada do CAPM.** `beta_impl = (custo_implícito − rf) ÷ erp`, calculado só para o eixo de custo de capital, com a álgebra registrada. Quando o caso declarar `mercado.beta_observado` como faixa `[min, max]`, o resultado diz se o implícito cai dentro, abaixo ou acima dela — sem adjetivo, só a posição e a distância.

**D4 — Teto do crescimento gratuito roda automaticamente quando um eixo primário não fecha.** Eixos primários são `rentabilidade` e `crescimento`. Sem raiz em algum deles, roda-se o caso-limite: `tv=gordon`, `gp = g`, e rentabilidade terminal muito alta. O "muito alta" é uma **constante declarada** (`RENTABILIDADE_TERMINAL_INFINITA = 1e6`, em %), e a Task 3 traz um teste de que o resultado é insensível à escolha — 1e5, 1e6 e 1e7 têm de coincidir na precisão de centavos. Constante mágica sem teste de estabilidade é número inventado.

**D5 — Grades declaram os pontos; nada de faixa automática.** O caso lista os pontos de cada eixo explicitamente. Isso deixa o custo sob controle do analista e torna a grade reprodutível. Grade sem pontos declarados é recusada.

**D6 — Diagnóstico por célula, sem duplicar prosa.** Cada grade carrega `diagnosticos_unicos` (lista das strings distintas que o motor emitiu em qualquer célula) e cada célula carrega `diag` (lista de índices nessa lista). A informação é integral e o arquivo não repete a mesma frase 49 vezes. A Task 4 traz um teste que reconstrói os diagnósticos de uma célula pelos índices e compara com uma execução direta do motor.

**D7 — Um arquivo só.** `reversa` e `sensibilidades` entram como blocos do próprio `resultados.json`. Uma entrada determinística, uma composição canônica. Se o arquivo ficar grande demais quando o relatório existir (item 5), a divisão se decide lá, com o problema à vista.

## Contrato do caso — o que a fatia B acrescenta

```json
{
  "mercado": {
    "rf": 12.0,
    "erp": 5.5,
    "beta_observado": [0.85, 1.35],
    "fonte": "fixture sintética",
    "data": "2026-08-21"
  },
  "reversa": {
    "cenario": "base",
    "eixos": ["custo_capital", "crescimento", "rentabilidade", "cap"]
  },
  "sensibilidades": {
    "cenario": "base",
    "grades_1d": [
      {"premissa": "wacc", "pontos": [8.0, 9.0, 10.0, 11.0, 12.0],
       "triangulo": {"inputs": ["g", "roic"], "output": "rir"}}
    ],
    "grades_2d": [
      {"premissa_x": "roic", "pontos_x": [10.0, 12.0, 14.0],
       "premissa_y": "g", "pontos_y": [3.0, 5.0, 7.0],
       "triangulo": {"inputs": ["g", "roic"], "output": "rir"}}
    ]
  }
}
```

Eixos aceitos em `reversa.eixos`: `custo_capital` (obrigatório), `crescimento`, `rentabilidade`, `cap`. Cada um traduz para o `--resolver` do motor conforme a rota: `custo_capital` → `wacc` (firm) / `ke` (equity); `rentabilidade` → `roic` / `roe`; `crescimento` → `g`; `cap` → `cap`.

## File Structure

| Arquivo | Responsabilidade |
|---|---|
| `skills/er-valuation/scripts/reversa.py` | Alvo de mercado, argv de `rev` por eixo, normalização, beta implícito, teto do crescimento gratuito |
| `skills/er-valuation/scripts/sensibilidades.py` | Grades 1D e 2D célula a célula, com dedup de diagnóstico |
| `skills/er-valuation/scripts/caso.py` | Validação dos blocos novos (modificado) |
| `skills/er-valuation/scripts/avaliar.py` | Integração dos dois blocos no `resultados.json` (modificado) |
| `skills/er-valuation/SKILL.md` | Escopo atualizado (modificado) |
| `tests/test_valuation_reversa.py` · `test_valuation_sensibilidades.py` | Um por módulo novo |
| `tests/fixtures/caso_reversa_firm.json` | Fixture com os blocos novos |

---

### Task 1: Contrato dos blocos `mercado`, `reversa` e `sensibilidades`

**Files:**
- Modify: `skills/er-valuation/scripts/caso.py`
- Modify: `tests/test_valuation_caso.py`
- Create: `tests/fixtures/caso_reversa_firm.json`

**Interfaces:**
- Produces: `EIXOS_DE_REVERSA: frozenset` = `{"custo_capital", "crescimento", "rentabilidade", "cap"}`; `EIXO_OBRIGATORIO = "custo_capital"`; `CAMPOS_DE_MERCADO_OBRIGATORIOS = ("rf", "erp")`. Validação dos três blocos novos dentro de `validar`.
- Consumed by: `reversa.py`, `sensibilidades.py`, `avaliar.py`.

- [ ] **Step 1: Criar a fixture**

`tests/fixtures/caso_reversa_firm.json` — cópia de `caso_minimo_firm.json` acrescida dos três blocos exatamente como no contrato acima.

- [ ] **Step 2: Escrever os testes (vão falhar)**

Acrescente a `tests/test_valuation_caso.py`:

```python
def _reversa() -> dict:
    return json.loads((FIXTURES / "caso_reversa_firm.json").read_text(encoding="utf-8"))


def test_fixture_de_reversa_e_valida():
    assert carregar(FIXTURES / "caso_reversa_firm.json")["reversa"]["eixos"]


def test_caso_sem_blocos_novos_continua_valido():
    """A fatia A nao pode ser quebrada: mercado/reversa/sensibilidades sao opcionais."""
    assert carregar(FIXTURES / "caso_minimo_firm.json")["rota"] == "firm"


def test_reversa_sem_custo_de_capital_recusa():
    """Eixo obrigatorio da metodologia em toda rodada — omitir nao e escolha."""
    c = _reversa()
    c["reversa"]["eixos"] = ["crescimento", "rentabilidade"]
    with pytest.raises(CasoInvalido, match="custo de capital"):
        validar(c)


def test_reversa_com_eixo_desconhecido_recusa():
    c = _reversa()
    c["reversa"]["eixos"] = ["custo_capital", "volatilidade"]
    with pytest.raises(CasoInvalido, match="volatilidade"):
        validar(c)


def test_reversa_sem_bloco_mercado_recusa():
    """Sem rf e erp nao ha beta implicito, e o beta implicito e o confronto."""
    c = _reversa()
    del c["mercado"]
    with pytest.raises(CasoInvalido, match="mercado"):
        validar(c)


@pytest.mark.parametrize("campo", ["rf", "erp"])
def test_reversa_sem_campo_de_mercado_recusa(campo):
    c = _reversa()
    del c["mercado"][campo]
    with pytest.raises(CasoInvalido, match=campo):
        validar(c)


def test_reversa_aponta_cenario_inexistente_recusa():
    c = _reversa()
    c["reversa"]["cenario"] = "otimista"
    with pytest.raises(CasoInvalido, match="otimista"):
        validar(c)


def test_beta_observado_invalido_recusa():
    c = _reversa()
    c["mercado"]["beta_observado"] = [1.4, 0.8]
    with pytest.raises(CasoInvalido, match="beta"):
        validar(c)


def test_grade_1d_sem_pontos_recusa():
    c = _reversa()
    c["sensibilidades"]["grades_1d"][0]["pontos"] = []
    with pytest.raises(CasoInvalido, match="pontos"):
        validar(c)


def test_grade_1d_com_premissa_fora_da_rota_recusa():
    c = _reversa()
    c["sensibilidades"]["grades_1d"][0]["premissa"] = "roe"
    with pytest.raises(CasoInvalido, match="roe"):
        validar(c)


def test_grade_sem_triangulo_declarado_recusa():
    """Grade sem configuracao do triangulo nao e reproduzivel."""
    c = _reversa()
    del c["sensibilidades"]["grades_1d"][0]["triangulo"]
    with pytest.raises(CasoInvalido, match="triângulo"):
        validar(c)


def test_grade_2d_com_eixos_iguais_recusa():
    c = _reversa()
    c["sensibilidades"]["grades_2d"][0]["premissa_y"] = "roic"
    with pytest.raises(CasoInvalido, match="mesma premissa"):
        validar(c)


def test_sensibilidades_sem_reversa_e_permitido():
    """Os dois blocos sao independentes."""
    c = _reversa()
    del c["reversa"]
    del c["mercado"]
    validar(c)
```

- [ ] **Step 3: Rodar para ver falhar**

Run: `python -m pytest tests/test_valuation_caso.py -q -k "reversa or grade or mercado or beta or blocos"`
Expected: FAIL — a fixture não existe e os blocos não são validados.

- [ ] **Step 4: Implementar a validação**

Em `caso.py`, acrescente as constantes da seção Interfaces e a validação dos três blocos, seguindo a ordem e o estilo que o módulo já usa (guarda de container `dict`, campo por campo, mensagem nomeando o campo e a razão). Regras:

- `mercado`, `reversa`, `sensibilidades`: opcionais; quando presentes, têm de ser dicionários.
- `reversa` presente ⟹ `mercado` obrigatório, com `rf` e `erp` numéricos finitos; `eixos` lista não-vazia, todos em `EIXOS_DE_REVERSA`, com `custo_capital` presente; `cenario` tem de existir em `caso["cenarios"]`.
- `mercado.beta_observado`, quando presente: lista de dois números finitos com `min < max`.
- `sensibilidades` presente ⟹ `cenario` existente; cada grade 1D com `premissa` do vocabulário da rota, `pontos` lista não-vazia de números finitos e `triangulo` válido (reaproveite a validação de triângulo que já existe); cada grade 2D idem para os dois eixos, com `premissa_x != premissa_y`.

Reaproveite os helpers numéricos e de triângulo existentes — não escreva uma quarta cópia da guarda.

- [ ] **Step 5: Rodar para ver passar**

Run: `python -m pytest tests/test_valuation_caso.py -q`
Expected: PASS, incluindo os 13 testes novos e todos os anteriores.

- [ ] **Step 6: Suíte inteira**

Run: `python -m pytest tests/ -q`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add skills/er-valuation/scripts/caso.py tests/test_valuation_caso.py tests/fixtures/caso_reversa_firm.json
git commit -m "$(cat <<'EOF'
feat(er-valuation): contrato dos blocos mercado, reversa e sensibilidades

Blocos opcionais; presentes, exigem o que a metodologia exige — custo de
capital implicito e eixo obrigatorio da reversa, e toda grade declara a
configuracao do triangulo e seus pontos.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: Reversa por eixo

**Files:**
- Create: `skills/er-valuation/scripts/reversa.py`
- Create: `tests/test_valuation_reversa.py`

**Interfaces:**
- Consumes: `motor.rodar`/`motor.argv_para` (subcomando `rev`), `caso.EIXOS_DE_REVERSA`.
- Produces: `alvo_de_mercado(caso, cenario, nd_efetivo) -> dict` com `{"valor": float, "algebra": str, "base": str}`; `RESOLVER_POR_EIXO: dict[str, dict[str, str]]`; `reverter(caso, nome_cenario, nd_efetivo) -> dict` devolvendo `{"alvo": ..., "eixos": {nome: <saída do motor normalizada>}}`.
- Consumed by: `avaliar.py`.

`motor.argv_para` hoje só conhece `ev` e `pe`. Estenda-o para `rev` **sem quebrar** as duas rotas existentes: o subcomando passa a ser escolhido pelo chamador em vez de derivado só da rota. Mantenha `argv_para(rota, premissas, escala)` funcionando com a assinatura atual (os testes da fatia A dependem dela) e acrescente o caminho novo de forma aditiva.

- [ ] **Step 1: Escrever os testes (vão falhar)**

`tests/test_valuation_reversa.py`:

```python
import json
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures"
sys.path.insert(0, str(RAIZ / "skills" / "er-valuation" / "scripts"))
from caso import carregar  # noqa: E402
from reversa import alvo_de_mercado, reverter  # noqa: E402


def _caso() -> dict:
    return carregar(FIXTURES / "caso_reversa_firm.json")


def test_alvo_e_o_multiplo_de_mercado_com_algebra_declarada():
    # preco 55 x 100 acoes = 5500 de market cap; + nd 500 = EV 6000; / EBITDA 1000 = 6,0x
    alvo = alvo_de_mercado(_caso(), "base", 500.0)
    assert alvo["valor"] == pytest.approx(6.0)
    assert "6000" in alvo["algebra"] or "6.000" in alvo["algebra"]
    assert alvo["base"] == "ebitda"


def test_custo_de_capital_implicito_tem_raiz_e_identificacao():
    r = reverter(_caso(), "base", 500.0)
    eixo = r["eixos"]["custo_capital"]
    raizes = eixo["raizes_wacc_%"]
    assert raizes and all(isinstance(x, float) for x in raizes)
    assert eixo["identificacao_por_raiz"]


def test_beta_implicito_sai_do_capm_com_algebra():
    r = reverter(_caso(), "base", 500.0)
    b = r["eixos"]["custo_capital"]["beta_implicito"]
    wacc = r["eixos"]["custo_capital"]["raizes_wacc_%"][0]
    assert b["valor"] == pytest.approx((wacc - 12.0) / 5.5, abs=1e-6)
    assert "12" in b["algebra"] and "5,5" in b["algebra"].replace(".", ",")


def test_beta_implicito_diz_a_posicao_contra_a_banda():
    r = reverter(_caso(), "base", 500.0)
    b = r["eixos"]["custo_capital"]["beta_implicito"]
    assert b["posicao_na_banda"] in ("dentro", "abaixo", "acima")
    assert "distancia" in b


def test_beta_implicito_so_existe_no_eixo_de_custo_de_capital():
    r = reverter(_caso(), "base", 500.0)
    for nome, eixo in r["eixos"].items():
        if nome != "custo_capital":
            assert "beta_implicito" not in eixo


def test_diagnosticos_do_motor_chegam_integros():
    r = reverter(_caso(), "base", 500.0)
    eixo = r["eixos"]["custo_capital"]
    assert eixo["premissas_fixadas"]["nota"]
    assert isinstance(eixo["guardas_v9_4"], list)
    assert eixo["faixa_de_busca"]["variavel"] == "wacc"


def test_alvo_base_corrente_e_declarado_explicitamente():
    """Tela NTM contra base corrente injeta erro de (1+g); a base vai declarada."""
    r = reverter(_caso(), "base", 500.0)
    assert "corrente" in r["eixos"]["custo_capital"]["base_do_alvo"]


def test_eixo_sem_raiz_preserva_sem_solucao_e_sugestao():
    c = _caso()
    c["preco"]["valor"] = 900.0  # alvo absurdo: nenhum eixo primario fecha
    r = reverter(c, "base", 500.0)
    rent = r["eixos"]["rentabilidade"]
    assert rent["raizes_roic_%"] == []
    assert "sem_solucao" in rent and "máximo atingível" in rent["sem_solucao"]
    assert "sugestao" in rent and "TETO DO CRESCIMENTO GRATUITO" in rent["sugestao"]


def test_todos_os_eixos_declarados_sao_rodados():
    r = reverter(_caso(), "base", 500.0)
    assert set(r["eixos"]) == {"custo_capital", "crescimento", "rentabilidade", "cap"}


def test_eixo_cap_passa_com_shape_proprio():
    """O motor devolve CAP_implicito_anos, nao raizes_* — repassar, nao uniformizar."""
    cap = reverter(_caso(), "base", 500.0)["eixos"]["cap"]
    assert "CAP_implicito_anos" in cap
    assert not any(k.startswith("raizes") for k in cap)
    assert cap["faixa_de_busca"]["variavel"] == "cap(n)"


def test_cap_inalcancavel_chega_como_string_sem_quebrar():
    """CAP_implicito_anos vira STRING quando o alvo esta fora de 1-60 anos."""
    c = _caso()
    c["preco"]["valor"] = 70.0
    cap = reverter(c, "base", 500.0)["eixos"]["cap"]
    assert isinstance(cap["CAP_implicito_anos"], (float, int, str))
```

- [ ] **Step 2: Rodar para ver falhar**

Run: `python -m pytest tests/test_valuation_reversa.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'reversa'`.

- [ ] **Step 3: Implementar `reversa.py`**

- `alvo_de_mercado`: rota firm ⟹ `market_cap = preço × ações`, `ev_mercado = market_cap + nd_efetivo`, `valor = ev_mercado ÷ métrica`, `base` = `"ebitda"` ou `"nopat"` conforme a métrica; rota equity ⟹ `valor = market_cap ÷ lucro`, `base = "pl"`. `algebra` é uma frase com os números da conta.
- `RESOLVER_POR_EIXO = {"custo_capital": {"firm": "wacc", "equity": "ke"}, "rentabilidade": {"firm": "roic", "equity": "roe"}, "crescimento": {"firm": "g", "equity": "g"}, "cap": {"firm": "cap", "equity": "cap"}}`.
- `reverter`: para cada eixo declarado, monta o argv de `rev` com o alvo, `--resolver`, `--base`, `--alvo-base corrente`, `--moeda`, e o vetor central de premissas do cenário **menos** a variável que está sendo resolvida; roda; guarda a saída do motor **íntegra**; no eixo de custo de capital acrescenta `beta_implicito`.
- `beta_implicito`: `{"valor": (custo − rf) / erp, "algebra": "...", "posicao_na_banda": ..., "distancia": ...}` quando houver `beta_observado`; sem banda, `posicao_na_banda` é `"banda não declarada"` e `distancia` é `None`. Calculado sobre a **primeira** raiz, com o campo `raiz_usada` dizendo qual — e quando houver mais de uma raiz, o campo `nota_multiplas_raizes` diz que o beta corresponde só àquela.

- [ ] **Step 4: Rodar para ver passar**

Run: `python -m pytest tests/test_valuation_reversa.py -q`
Expected: PASS — 9 passed.

- [ ] **Step 5: Suíte inteira e vendor limpo**

Run: `python -m pytest tests/ -q` · `git status --short vendor`
Expected: PASS; vendor vazio.

- [ ] **Step 6: Commit**

```bash
git add skills/er-valuation/scripts/reversa.py skills/er-valuation/scripts/motor.py tests/test_valuation_reversa.py
git commit -m "$(cat <<'EOF'
feat(er-valuation): menu de reconciliacao por eixo com beta implicito

Alvo e o multiplo de mercado com a algebra declarada; cada eixo roda no motor
e a saida chega integra — sem_solucao, sugestao e conflacao inclusos. Custo de
capital ganha o beta implicito confrontado contra a banda observada.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Teto do crescimento gratuito

**Files:**
- Modify: `skills/er-valuation/scripts/reversa.py`
- Modify: `tests/test_valuation_reversa.py`

**Interfaces:**
- Produces: `RENTABILIDADE_TERMINAL_INFINITA: float`; `teto_do_crescimento_gratuito(caso, nome_cenario, nd_efetivo) -> dict`. `reverter` passa a incluir a chave `teto_do_crescimento_gratuito` no resultado quando algum eixo primário (`rentabilidade` ou `crescimento`) voltar sem raiz, e a omite quando todos fecharem.

- [ ] **Step 1: Escrever os testes (vão falhar)**

```python
def test_teto_roda_quando_eixo_primario_nao_fecha():
    c = _caso()
    c["preco"]["valor"] = 900.0
    r = reverter(c, "base", 500.0)
    teto = r["teto_do_crescimento_gratuito"]
    assert teto["multiplo"] > 0
    assert "RiR" in teto["leitura"] or "reinvestimento" in teto["leitura"]


def test_teto_nao_roda_quando_todos_os_eixos_fecham():
    r = reverter(_caso(), "base", 500.0)
    assert "teto_do_crescimento_gratuito" not in r


def test_teto_e_insensivel_a_escolha_do_infinito():
    """A constante e uma aproximacao numerica; se o resultado depender dela, e invencao."""
    import reversa as mod
    c = _caso()
    c["preco"]["valor"] = 900.0
    valores = []
    original = mod.RENTABILIDADE_TERMINAL_INFINITA
    try:
        for grande in (1e5, 1e6, 1e7):
            mod.RENTABILIDADE_TERMINAL_INFINITA = grande
            valores.append(mod.teto_do_crescimento_gratuito(c, "base", 500.0)["multiplo"])
    finally:
        mod.RENTABILIDADE_TERMINAL_INFINITA = original
    # medido contra o vendor: 1e5 -> 10.6467, 1e6 -> 10.647, 1e7 -> 10.647
    assert max(valores) - min(valores) < 0.01, valores


def test_teto_declara_as_premissas_que_alterou():
    c = _caso()
    c["preco"]["valor"] = 900.0
    teto = reverter(c, "base", 500.0)["teto_do_crescimento_gratuito"]
    assert teto["premissas_alteradas"]["tv"] == "gordon"
    assert teto["premissas_alteradas"]["gp"] == c["cenarios"]["base"]["premissas"]["g"]


def test_teto_e_maior_que_o_multiplo_do_caso_base():
    """Nenhuma historia de crescimento PAGO chega ao teto do crescimento gratuito."""
    c = _caso()
    c["preco"]["valor"] = 900.0
    r = reverter(c, "base", 500.0)
    from motor import rodar
    base = rodar("firm", c["cenarios"]["base"]["premissas"], None)
    assert r["teto_do_crescimento_gratuito"]["multiplo"] > base["EV/EBITDA_curr"]
```

- [ ] **Step 2: Rodar para ver falhar** · `python -m pytest tests/test_valuation_reversa.py -q -k teto` → FAIL.

- [ ] **Step 3: Implementar**

`RENTABILIDADE_TERMINAL_INFINITA = 1e6` com comentário dizendo que é a aproximação de `RiR_TV = gp/RONIC → 0` e que a Task 3 trava sua irrelevância por teste. `teto_do_crescimento_gratuito` copia as premissas do cenário, força `tv="gordon"`, `roic_tv`/`roe_tv` = a constante e `gp` = o `g` do cenário, roda o motor, e devolve `{"multiplo": ..., "premissas_alteradas": {...}, "leitura": "...", "diagnosticos": [...]}`. A `leitura` explica em uma frase o que a distância até o caso-base significa: o preço que o mercado paga pela hipótese de crescimento que não consome capital.

- [ ] **Step 4: Rodar para ver passar** · `python -m pytest tests/test_valuation_reversa.py -q` → PASS, 14 passed.

- [ ] **Step 5: Suíte inteira** → PASS.

- [ ] **Step 6: Commit**

```bash
git add skills/er-valuation/scripts/reversa.py tests/test_valuation_reversa.py
git commit -m "$(cat <<'EOF'
feat(er-valuation): teto do crescimento gratuito quando eixo primario nao fecha

Caso-limite RiR->0 rodado automaticamente, com as premissas alteradas
declaradas e teste de que o resultado nao depende da constante que aproxima
o infinito.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: Grades de sensibilidade

**Files:**
- Create: `skills/er-valuation/scripts/sensibilidades.py`
- Create: `tests/test_valuation_sensibilidades.py`

**Interfaces:**
- Consumes: `motor.rodar`.
- Produces: `grade_1d(caso, nome_cenario, spec, nd_efetivo) -> dict`; `grade_2d(...) -> dict`; `calcular(caso, nome_cenario, nd_efetivo) -> dict` com `{"grades_1d": [...], "grades_2d": [...]}`.

Shape de uma grade 1D:

```json
{
  "premissa": "wacc",
  "triangulo": {"inputs": ["g", "roic"], "output": "rir"},
  "metrica_de_referencia": {"tipo": "EBITDA", "valor": 1000.0},
  "unidade": "preço por ação",
  "diagnosticos_unicos": ["...", "..."],
  "pontos": [{"x": 8.0, "valor": 0.0, "multiplo": 0.0, "diag": [0, 1]}]
}
```

2D acrescenta `premissa_x`/`premissa_y`, `pontos_x`/`pontos_y` e `celulas` como lista de listas de células.

- [ ] **Step 1: Escrever os testes (vão falhar)**

```python
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures"
sys.path.insert(0, str(RAIZ / "skills" / "er-valuation" / "scripts"))
from caso import carregar  # noqa: E402
from motor import rodar  # noqa: E402
from sensibilidades import calcular, grade_1d  # noqa: E402


def _caso() -> dict:
    return carregar(FIXTURES / "caso_reversa_firm.json")


def test_grade_1d_tem_um_ponto_por_valor_declarado():
    spec = _caso()["sensibilidades"]["grades_1d"][0]
    g = grade_1d(_caso(), "base", spec, 500.0)
    assert [p["x"] for p in g["pontos"]] == spec["pontos"]


def test_celula_do_ponto_central_reproduz_o_caso_base():
    """A celula na premissa do caso-base TEM de bater com o caso-base."""
    c = _caso()
    spec = c["sensibilidades"]["grades_1d"][0]
    central = c["cenarios"]["base"]["premissas"][spec["premissa"]]
    assert central in spec["pontos"], "a fixture precisa incluir o ponto central"
    g = grade_1d(c, "base", spec, 500.0)
    ponto = next(p for p in g["pontos"] if p["x"] == central)
    esperado = rodar("firm", c["cenarios"]["base"]["premissas"],
                     {"ebitda": 1000.0, "nd": 500.0, "acoes": 100.0})
    assert ponto["valor"] == pytest.approx(esperado["Preco_acao"], abs=0.01)


def test_grade_declara_triangulo_e_metrica_de_referencia():
    spec = _caso()["sensibilidades"]["grades_1d"][0]
    g = grade_1d(_caso(), "base", spec, 500.0)
    assert g["triangulo"] == spec["triangulo"]
    assert g["metrica_de_referencia"]["tipo"] == "EBITDA"
    assert g["metrica_de_referencia"]["valor"] == 1000.0


def test_diagnosticos_deduplicados_reconstroem_a_execucao_direta():
    """Os indices tem de devolver exatamente o que o motor emitiu naquela celula."""
    c = _caso()
    spec = c["sensibilidades"]["grades_1d"][0]
    g = grade_1d(c, "base", spec, 500.0)
    ponto = g["pontos"][0]
    premissas = dict(c["cenarios"]["base"]["premissas"])
    premissas[spec["premissa"]] = ponto["x"]
    direto = rodar("firm", premissas, {"ebitda": 1000.0, "nd": 500.0, "acoes": 100.0})
    reconstruido = [g["diagnosticos_unicos"][i] for i in ponto["diag"]]
    assert reconstruido == direto["diagnosticos"]


def test_grade_2d_tem_a_forma_declarada():
    c = _caso()
    r = calcular(c, "base", 500.0)
    g2 = r["grades_2d"][0]
    assert len(g2["celulas"]) == len(g2["pontos_y"])
    assert all(len(linha) == len(g2["pontos_x"]) for linha in g2["celulas"])


def test_calcular_devolve_todas_as_grades_declaradas():
    c = _caso()
    r = calcular(c, "base", 500.0)
    assert len(r["grades_1d"]) == len(c["sensibilidades"]["grades_1d"])
    assert len(r["grades_2d"]) == len(c["sensibilidades"]["grades_2d"])


def test_celula_que_nula_no_motor_e_recusada_nao_silenciada():
    """Mesma disciplina da fatia A: null do motor nao vira null no arquivo.

    Verificado contra o vendor: sob tv=gordon, roic_tv = 0 faz o motor devolver
    EV e Preco_acao nulos com exit 0.
    """
    from motor import MotorFalhou
    c = _caso()
    spec = {"premissa": "roic_tv", "pontos": [0.0],
            "triangulo": c["sensibilidades"]["grades_1d"][0]["triangulo"]}
    with pytest.raises(MotorFalhou):
        grade_1d(c, "base", spec, 500.0)
```

- [ ] **Step 2: Rodar para ver falhar** → `ModuleNotFoundError: No module named 'sensibilidades'`.

- [ ] **Step 3: Implementar `sensibilidades.py`**

Cada célula: copia as premissas do cenário, substitui a(s) premissa(s) do eixo, roda o motor com a escala do cenário, e extrai o preço por ação e o múltiplo — **usando o mesmo caminho de escala e a mesma recusa de `null` que `avaliar.py` já implementa**. Não duplique essa lógica: extraia-a para uma função reutilizável se ainda não for, ou importe-a. Se extrair exigir mexer em `avaliar.py`, faça — e diga no relatório o que mudou e por quê.

Dedup de diagnóstico: acumule as strings distintas na ordem de primeira aparição; cada célula guarda os índices.

- [ ] **Step 4: Rodar para ver passar** → PASS, 7 passed.

- [ ] **Step 5: Suíte inteira e vendor limpo** → PASS; vendor vazio.

- [ ] **Step 6: Commit**

```bash
git add skills/er-valuation/scripts/sensibilidades.py skills/er-valuation/scripts/avaliar.py tests/test_valuation_sensibilidades.py
git commit -m "$(cat <<'EOF'
feat(er-valuation): grades 1D e 2D celula a celula no motor

Cada grade declara a configuracao do triangulo e a metrica de referencia; a
celula central reproduz o caso-base por construcao. Diagnostico por celula
sem duplicar prosa, via indices numa lista de strings distintas.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: Integração no `resultados.json` e escopo da skill

**Files:**
- Modify: `skills/er-valuation/scripts/avaliar.py`
- Modify: `skills/er-valuation/SKILL.md`
- Modify: `tests/test_valuation_avaliar.py`
- Modify: `tests/test_valuation_skill.py`

- [ ] **Step 1: Escrever os testes (vão falhar)**

```python
def test_resultado_sem_blocos_novos_nao_ganha_chaves():
    """Caso da fatia A continua produzindo exatamente o que produzia."""
    r = avaliar(carregar(FIXTURES / "caso_minimo_firm.json"))
    assert "reversa" not in r and "sensibilidades" not in r


def test_resultado_com_reversa_traz_o_bloco():
    r = avaliar(carregar(FIXTURES / "caso_reversa_firm.json"))
    assert r["reversa"]["eixos"]["custo_capital"]["beta_implicito"]["valor"]
    assert r["reversa"]["alvo"]["valor"] == pytest.approx(6.0)


def test_resultado_com_sensibilidades_traz_o_bloco():
    r = avaliar(carregar(FIXTURES / "caso_reversa_firm.json"))
    assert r["sensibilidades"]["grades_1d"]
    assert r["sensibilidades"]["grades_2d"]


def test_saida_com_reversa_continua_deterministica(tmp_path):
    import filecmp
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    escrever(avaliar(carregar(FIXTURES / "caso_reversa_firm.json")), a)
    escrever(avaliar(carregar(FIXTURES / "caso_reversa_firm.json")), b)
    assert filecmp.cmp(a, b, shallow=False)


def test_valores_consumidos_nao_sao_null_mas_o_repasse_do_motor_e_integro():
    """A recusa de null vale para o que o wrapper CONSOME.

    O payload de diagnostico do motor chega integro, e pode legitimamente
    conter null (o proprio motor serializa nao-finito como null nos campos
    que ele mesmo declara nao aplicaveis). Uniformizar isso seria ajustar
    output do motor — proibido.
    """
    r = avaliar(carregar(FIXTURES / "caso_reversa_firm.json"))
    v = r["cenarios"]["base"]["valor"]
    assert all(v[k] is not None for k in v)
    assert all(x is not None for x in r["cenarios"]["base"]["multiplos"].values())
```

E em `tests/test_valuation_skill.py`, um teste de que o `SKILL.md` já não declara reversa e sensibilidades como fatia futura.

- [ ] **Step 2: Rodar para ver falhar** → FAIL.

- [ ] **Step 3: Implementar**

Em `avaliar.py`: quando o caso trouxer `reversa`, chama `reversa.reverter` com o `nd_efetivo` do cenário apontado; quando trouxer `sensibilidades`, chama `sensibilidades.calcular`. Os blocos entram no resultado só quando existem. Na rota equity, `nd_efetivo` é `0.0` e a base do alvo é `pl`.

No `SKILL.md`: mova reversa e sensibilidades da lista de "ainda não implementados" para o corpo, com uma linha cada, e acrescente os dois módulos à tabela. Não reproduza metodologia.

- [ ] **Step 4: Rodar para ver passar** → PASS.

- [ ] **Step 5: Verificação de ponta a ponta**

```bash
python skills/er-valuation/scripts/avaliar.py tests/fixtures/caso_reversa_firm.json --out /tmp/rev.json
python -c "
import json; d=json.load(open('/tmp/rev.json',encoding='utf-8'))
e=d['reversa']['eixos']['custo_capital']
print('alvo', d['reversa']['alvo']['valor'])
print('wacc implicito', e['raizes_wacc_%'])
print('beta implicito', e['beta_implicito']['valor'], e['beta_implicito']['posicao_na_banda'])
print('grades 1d', len(d['sensibilidades']['grades_1d']), '| 2d', len(d['sensibilidades']['grades_2d']))
"
```

Registre a saída no relatório.

- [ ] **Step 6: Suíte inteira** → PASS.

- [ ] **Step 7: Commit**

```bash
git add skills/er-valuation/scripts/avaliar.py skills/er-valuation/SKILL.md tests/test_valuation_avaliar.py tests/test_valuation_skill.py
git commit -m "$(cat <<'EOF'
feat(er-valuation): reversa e sensibilidades no resultados.json

Blocos entram so quando o caso os declara; caso da fatia A produz exatamente
o que produzia. Determinismo e recusa de null preservados no arquivo completo.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

## Verificação final da fatia 3B

- [ ] `python -m pytest tests/ -q` — verde
- [ ] `python skills/er-valuation/scripts/avaliar.py tests/fixtures/caso_reversa_firm.json --out <tmp>` — exit 0, com os dois blocos
- [ ] `python skills/er-valuation/scripts/avaliar.py tests/fixtures/caso_minimo_firm.json --out <tmp>` — exit 0, **sem** os dois blocos
- [ ] duas execuções do mesmo caso produzem arquivos byte a byte idênticos
- [ ] `git status --short vendor` — vazio
- [ ] `python vendor/multiplos-justos/scripts/testes.py` — `TODOS OS TESTES PASSARAM`
