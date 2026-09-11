# Item 4, fatia C — rampa e predicados de diagnóstico no espelho

> **Para agentes:** execute com `superpowers:subagent-driven-development`. Calibragem de rigor em
> vigor desde 26/08/2026 (ver ledger): implementação simples, testes que discriminam a matemática e
> os contratos, **sem revisor por task**, uma revisão final da fatia. Achado não material: registre
> no relatório e siga.

**Goal:** o espelho JS passa a recalcular ao vivo, com paridade, a rota **rampa** e os **predicados
dos diagnósticos** que o motor emite nas rotas firm e equity — fechando a lista "ao vivo" da §8.4 do
desenho, menos o `degrau` (ver "Fora do escopo").

**Architecture:** mesma mecânica da 4B — gerador `skills/er-valuation/scripts/vetores_solver.py`,
fixture `tests/fixtures/vetores_solver.json`, harness `tests/test_paridade_wrapper_js.py`. A paridade
é **contra o wrapper**, não contra o motor direto: a revisão final da 4B mostrou que
`motor.py:217` (`if valor is None: continue`) muda a semântica de default no caminho do wrapper, e é
esse caminho que o laboratório do item 5 consome.

**Tech Stack:** JS sem dependências; Python stdlib.

## Global Constraints

- `vendor/` é read-only; `git status --short vendor` vazio ao fim de cada task.
- As fixtures regeneram byte a byte (teste existente cobra).
- Campos que o motor arredonda comparam **exatamente**, com `arredondarPy` (já existe no espelho — reuse).
- Caminho do wrapper: `null` e ausência **colapsam** e vale o default do argparse do subcomando
  (comentário de `premissasParaNucleo`). O caminho do núcleo (fixture da 4A) não muda.
- Baseline **436 passed**; só sobe.

## Fora do escopo — e por quê

- **`degrau`**: nenhuma rota do wrapper o usa hoje. É lacuna do item 3 em relação ao desenho (§4.3,
  §8.4). Decisão do dono (10/09): ligar — fatia D, plano próprio, depois desta.
- **`_pe2_book`**: o plano da 4A disse que entrava aqui "junto com `rampa`". **Estava errado**: ele só
  é chamado por `iso_curva` (justos.py:1242/1254) e pelo selftest, e o desenho põe `iso` na camada
  precomputada.
- **Números dentro da prosa dos diagnósticos** (`RiR = 45,0%`, `excede NOPAT/WACC em 1,32x`…): esta
  fatia entrega **quais** diagnósticos disparam, e em que ordem. Os números interpolados ficam para o
  item 5, que define o que exibe e com que precisão.
- **Campos das saídas `ev`/`pe` que a §8.4 não lista como vivos**: resumo de `coerencia_vetor`,
  `efeito_c7_alternativa_gp_%`, `validacao_unit_economics`, `conservacao_capital`, nota de caixa,
  múltiplos forward. Precomputados e rotulados; reabrir se o item 5 precisar deles ao vivo.
- **Asserts internos de `rampa_bifasica`** (P1, P1b, P4): autovalidação do motor entre duas contas da
  mesma grandeza, não recusa de domínio. Não espelhar.
- **Grades e reversa sobre a rampa**: o wrapper recusa no gate. Não existem.

## Decisões do dono (10/09/2026)

- **D-degrau** — ligar: fatia D (`docs/superpowers/plans/2026-09-10-v4-fatia-degrau.md`), depois desta.
- **D-rf** — **aprovada.** O wrapper passa `mercado.rf` ao motor e a guarda de Damodaran (`gp` perpétuo
  ≤ `rf` nominal) volta a rodar. A correção entra **antes da Task 2**; a Task 1 segue tratando `rf` como
  ausente.

---

## Task 1: rampa no espelho

**Files:** modify `skills/er-valuation/assets/motor_espelho.js`, `skills/er-valuation/scripts/vetores_solver.py`,
`tests/fixtures/vetores_solver.json`, `tests/test_paridade_wrapper_js.py`.

**Contrato — leia e espelhe de lá (este plano não transcreve fórmulas, de propósito):**
- Motor: `rampa_bifasica` (`vendor/multiplos-justos/scripts/justos.py:74-172`) e a composição do handler
  `elif a.cmd == 'rampa'` no `main()` (`convencao_moeda`, `aviso_gp`, ponte para `Equity`/`Preco_acao`).
- Wrapper: `avaliar.precificar_rampa` (`skills/er-valuation/scripts/avaliar.py:268`) — é o lado Python
  da paridade.

**Interfaces:**
- JS: `rampaBifasica(args)` (frações, mesma assinatura do motor) e
  `precificarRampa({premissas, ndEfetivo, acoes, moeda})`, que devolve `{recusado: true}` ou
  `{recusado: false, multiplo, valor, saida, avisos}`.
- Problema: `{"id", "tipo": "rampa", "args": {"premissas": {...em %, shape do caso...}, "nd_efetivo": float|null, "acoes": float|null, "moeda": str}}`.
- Resultado Python: o mesmo shape. `avaliar_python` captura `MotorFalhou` **só neste tipo** e registra
  `{"recusado": true}`; os outros tipos não mudam.
- `saida` = os campos de `CAMPOS_RAMPA` presentes na saída do motor, com `rir_fase1_%` **sem** a chave
  `nota` (texto estático); `avisos` = lista ordenada dos de `AVISOS_RAMPA` presentes.

```python
CAMPOS_RAMPA = ("g1_%", "d_trajetoria_fase1_%", "d2_fase2_%", "rir_fase1_%", "alfa", "beta",
                "rir2_%", "roic2_%", "vp_fase1", "valor_fase2_no_ano_T", "capacidade_receita")
AVISOS_RAMPA = ("aviso_colheita", "aviso_delator")
```

**Detalhes que um espelho apressado erra:**

1. **Unidades.** No handler, `wk`, `kappa`, `g2`, `wacc`, `tax`, `util`, `g1`, `roic_tv`, `gp`,
   `roic_book` passam por `pc()` (% → fração); `receita0`, `ebitda0`, `da_parque`, `n`, `t_rampa` e `tv`
   **não**. `CHAVES_NAO_PERCENTUAIS` hoje só tem `{n, tv, mid_year, politica_tv}` — reaproveitar
   `premissasParaNucleo` sem estender o conjunto divide o EBITDA por 100.
2. **Defaults do subparser `rampa`.** Leia a definição dele no `main()` do motor; não suponha. `gp`
   chega como `pc(a.gp) or 0.0`; `n` não é obrigatório no caso.
3. **`g1` × `util`.** Com `g1` presente, `util` é ignorado e `capacidade_receita` não sai; com `g1`
   ausente, `util` deriva `g1` e `capacidade_receita` sai.
4. **Ordem de arredondamento da ponte.** `EV = round(ev, 4)`; `EV/EBITDA0` sobre o `ev` **não**
   arredondado; `Equity` e `Preco_acao` sobre `EV_arredondado − nd`.
5. **Ramos fechados.** `abs(r1 − 1) < 1e-12`; `abs(w) < 1e-14`; `wk + kappa <= 1e-15` → `roic2_%` vira
   a **string** do motor.
6. **Recusas de domínio** (`ValueError` no motor, `MotorFalhou` no wrapper): `t_rampa < 1` ou
   `n <= t_rampa`; `w <= -1` ou `g2 <= -1`; `wk < 0` ou `kappa < 0`; `util` fora de (0,1) sem `g1`;
   margem NOPAT da fase 2 `<= 0`. O espelho recusa — nunca devolve número onde o motor recusa.
   `tv: null` também recusa (Gate 1), como `precificarCelula` já faz.
7. **`aviso_gp` não entra nesta task**: exige `rf`, que o wrapper ainda não passa. A Task 2 o acrescenta
   (ver o detalhe 3 dela). *Correção: a versão anterior deste item dizia que a comparação de `avisos`
   reprovaria sozinha quando o `rf` chegasse — não reprovaria, porque `avisos` é filtrado por
   `AVISOS_RAMPA`, que não inclui `aviso_gp`.*
8. **A fase 2 chama `ev_nopat` do próprio motor**: use o `evNopat` já espelhado, não reescreva.

**Fixture (~15 problemas):** `g1` direto; `g1` derivado de `util`; `g1 < 0` (colheita); `rir2 >= 1`
(delator); `wk = kappa = 0`; fase 2 nas três convenções; `g1 = w` (`r1 = 1`); `w = 0`; sem ponte
(`nd_efetivo`/`acoes` nulos → só `EV`); e uma recusa de cada família do item 6.

**Testes** (acrescentar a `tests/test_paridade_wrapper_js.py`):

```python
CAMPOS_RAMPA = ("g1_%", "d_trajetoria_fase1_%", "d2_fase2_%", "rir_fase1_%", "alfa", "beta",
                "rir2_%", "roic2_%", "vp_fase1", "valor_fase2_no_ano_T", "capacidade_receita")


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_rampa_recusa_onde_o_motor_recusa():
    probs = _problemas({"rampa"})
    assert probs, "fixture sem problemas de rampa"
    py, js = avaliar_python(probs), _lado_js()
    fora = [(p["id"], a["recusado"], js[p["id"]]["recusado"])
            for p, a in zip(probs, py) if a["recusado"] != js[p["id"]]["recusado"]]
    assert not fora, f"recusa divergente (id, py, js): {fora}"


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_rampa_bate_campo_a_campo():
    """O que o motor arredonda compara EXATAMENTE — o arredondamento e contrato."""
    probs = _problemas({"rampa"})
    py, js = avaliar_python(probs), _lado_js()
    fora = []
    for p, a in zip(probs, py):
        if a["recusado"]:
            continue
        b = js[p["id"]]
        for campo in ("multiplo", "valor", "saida", "avisos"):
            if a[campo] != b[campo]:
                fora.append((p["id"], campo, a[campo], b[campo]))
    assert not fora, f"{len(fora)} divergencias; primeiras 3: {fora[:3]}"


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_fixture_de_rampa_cobre_o_que_discrimina():
    probs = _problemas({"rampa"})
    py = avaliar_python(probs)
    ok = [a for a in py if not a["recusado"]]
    assert sum(a["recusado"] for a in py) >= 4, "poucas recusas de dominio"
    assert any("capacidade_receita" in a["saida"] for a in ok), "g1 derivado de util nunca exercitado"
    assert any("aviso_colheita" in a["avisos"] for a in ok), "colheita nunca exercitada"
    assert any("aviso_delator" in a["avisos"] for a in ok), "rir2 >= 100% nunca exercitado"
    assert any(isinstance(a["saida"]["roic2_%"], str) for a in ok), "capital incremental zero nunca exercitado"
    assert any("Equity" not in a["valor"] for a in ok), "rampa sem ponte nunca exercitada"
    assert {p["args"]["premissas"]["tv"] for p in probs} >= {"book", "convergencia", "gordon"}
```

**Uma prova de falseabilidade:** trate `da_parque` como percentual no espelho, confirme vermelho
nomeando problemas, reverta, confirme verde. Registre as duas saídas.

Suíte inteira · `git status --short vendor` vazio · fixture byte a byte · um commit.

---

## Task 2: predicados de diagnóstico no espelho

**Files:** create `skills/er-valuation/assets/diagnosticos_chaves.json`; modify
`skills/er-valuation/assets/motor_espelho.js`, `skills/er-valuation/scripts/vetores_solver.py`,
`tests/fixtures/vetores_solver.json`, `tests/test_paridade_wrapper_js.py`.

**Contrato — leia e espelhe de lá:**
- Motor: `diag_firm` (justos.py:513-603), `diag_eq` (604-732), `_guardas_damodaran` (348-381),
  `coerencia_vetor` (382-512), e a composição nos handlers `ev` e `pe` do `main()`:
  `diagnosticos = diag_* + coerencia_vetor(...)[0]`.
- Wrapper: a lista `diagnosticos` que chega a `resultados.json`. Lado Python pela **mesma chamada que
  o wrapper faz ao motor** (`motor.rodar` com as premissas do caso), nunca `diag_firm` direto — é o
  caminho do wrapper que decide quais entradas existem.

**Interfaces:**
- JS: `diagnosticosFirm(premissas, moeda)` e `diagnosticosEquity(premissas, moeda)` →
  `[chave, ...]` na ordem de emissão do motor; premissas em %, shape do caso, mesmo colapso de `null`.
- Problema: `{"id", "tipo": "diag", "args": {"rota": "firm"|"equity", "premissas": {...}, "moeda": str, "rf": float|null}}` —
  `rf` em pontos percentuais, como `mercado.rf`; `null` quando o caso não declara `mercado`.
- Resultado Python: `{"id", "mensagens": [str, ...]}` (a lista crua do motor); JS: `{"id", "chaves": [...]}`.
- `diagnosticos_chaves.json`: `[{"chave": "...", "prefixo": "..."}, ...]` — **uma entrada por mensagem
  distinta que o motor consegue emitir pelo caminho do wrapper**. Prefixos mutuamente não-prefixos. É
  também o vocabulário que o item 5 vai usar para chavear o dicionário estático de prosa.

**Detalhes que um espelho apressado erra:**

1. **Assimetria de rota em `coerencia_vetor`.** No handler `pe`, `gde`/`nde` chegam como
   `pc(x) or 0` — nunca `None`. No `ev`, como `pc(getattr(a, 'gde', None))` — `None` quando ausentes.
   A mesma identidade roda numa rota e é "não checada" na outra.
2. **O que o caso aceita delimita o que é alcançável.** `PREMISSAS_FIRM`/`PREMISSAS_EQUITY`
   (`caso.py`) decidem quais entradas de `coerencia_vetor` o wrapper consegue emitir. `cash_yield`,
   `rir_observado` e `ebitda_ic` não são expostos (decisão da 3A): os ramos que dependem deles são
   inalcançáveis — **não espelhe**. Se um dia forem expostos, a tripwire de classificação e a comparação
   exata de chaves reprovam sozinhas.
3. **`rf`** chega ao motor depois da correção aprovada (entra antes desta task). Espelhe os três ramos
   de `_guardas_damodaran` — alerta de âncora macro, âncora OK e "PREMISSA NÃO ANCORADA" (sem
   `mercado`) —, com `rf` em % e dividido por 100 só na chamada do diagnóstico, como o handler faz; a
   fixture cobre os três. **E a rampa ganha `aviso_gp`:** acrescente a chave a `AVISOS_RAMPA` e espelhe a
   condição do handler `rampa` — atenção, ali é `a.tv == 'gordon'` **sem** `tv_canon`: o alias `spread`
   não dispara o aviso. Espelhe a peculiaridade, não a corrija.
4. **`moeda`** sempre chega (o caso a exige) → "MOEDA/REGIME NÃO DECLARADOS" é inalcançável. Não espelhe.
5. **Limiares são contrato** (`5e-4`, `1e-6`, `1e-9`, `tol = 5e-3`, `2*tol`): copie do vendor. Este plano
   não os transcreve de propósito.
6. **Ordem.** O handler concatena `diag_*` — que já termina com as guardas de Damodaran — e depois
   `coerencia_vetor(...)[0]`.
7. **`tv` canonicalizado** (`tv_canon`) antes dos testes de convenção: `ic`/`spread` entram.

**Fixture (~30 problemas `diag`):** o suficiente para disparar cada `ALERTA`, as duas variantes de
B-01 (com e sem `roic_book`/`roe_book`), cada `NEUTRALIDADE`, `REGIME DECLARADO` e `NOTA` do `gordon`,
política de caixa `continua`/`encerra`, `DOMÍNIO` ND/E > GD/E, `ALERTA DE SENSIBILIDADE`, `CAIXA
REMUNERADO` e as `INCOERÊNCIA` que o caso consegue alcançar. Um problema por chave nova; não varie
combinações além disso.

**Testes** (acrescentar a `tests/test_paridade_wrapper_js.py`):

```python
CHAVES = json.loads((RAIZ / "skills" / "er-valuation" / "assets" / "diagnosticos_chaves.json")
                    .read_text(encoding="utf-8"))


def _classificar(msg):
    return [c["chave"] for c in CHAVES if msg.startswith(c["prefixo"])]


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_toda_mensagem_do_motor_casa_com_exatamente_uma_chave():
    """Tripwire da troca de vendor: mensagem nova ou prefixo ambiguo reprova AQUI, nomeando a
    mensagem, antes de o laboratorio mostrar um diagnostico sem chave."""
    probs = _problemas({"diag"})
    assert probs, "fixture sem problemas de diagnostico"
    py = avaliar_python(probs)
    ruins = [(p["id"], m[:80], _classificar(m)) for p, a in zip(probs, py)
             for m in a["mensagens"] if len(_classificar(m)) != 1]
    assert not ruins, f"{len(ruins)} mensagens sem chave unica; primeiras 3: {ruins[:3]}"


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_chaves_de_diagnostico_batem_em_ordem():
    """O diagnostico se move junto com o numero (desenho, 8.4): QUAIS disparam e em que
    ordem tem de bater exatamente — chave a mais ou a menos e alerta errado na tela."""
    probs = _problemas({"diag"})
    py, js = avaliar_python(probs), _lado_js()
    fora = []
    for p, a in zip(probs, py):
        esperado = [_classificar(m)[0] for m in a["mensagens"]]
        if esperado != js[p["id"]]["chaves"]:
            fora.append((p["id"], p["args"]["rota"], esperado, js[p["id"]]["chaves"]))
    assert not fora, f"{len(fora)} divergencias; primeiras 2: {fora[:2]}"


@pytest.mark.skipif(SEM_NODE, reason=RAZAO)
def test_fixture_de_diagnostico_cobre_os_alertas():
    py = avaliar_python(_problemas({"diag"}))
    disparadas = {_classificar(m)[0] for a in py for m in a["mensagens"]}
    alertas = {c["chave"] for c in CHAVES
               if c["prefixo"].startswith(("ALERTA", "SUB-ALERTA", "INCOERÊNCIA", "DOMÍNIO"))}
    assert alertas <= disparadas, f"alertas nunca exercitados: {sorted(alertas - disparadas)}"
```

**Uma prova de falseabilidade:** no espelho, troque o limiar de neutralidade `5e-4` por `5e-3`,
confirme vermelho, reverta, confirme verde. Registre as duas saídas.

Suíte inteira · `git status --short vendor` vazio · fixture byte a byte · um commit.

---

## Verificação final da fatia 4C

Uma revisão (opus) da fatia inteira, com a mesma calibragem da 4B: material é o que faria o espelho
mostrar ao analista um número ou um alerta diferente do que o wrapper mostraria. Suíte inteira,
fixtures byte a byte, `vendor/` limpo.
