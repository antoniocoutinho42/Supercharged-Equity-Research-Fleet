# Fatia D — `degrau` (Gate 3) no wrapper e no espelho

> **Para agentes:** execute com `superpowers:subagent-driven-development`. Calibragem de rigor em
> vigor (ledger, 26/08/2026): implementação simples, testes que discriminam a matemática e os
> contratos, sem revisor por task, **uma** revisão final da fatia. Achado não material: registre e siga.

**Goal:** um caso da rota equity pode declarar capacidade ociosa de balanço (Gate 3), e o valuation
passa a incorporá-la como a metodologia manda — **rentabilidade × h, g inalterado, rentabilidade
terminal parada, fator de captura só sobre o incremento** —, com o espelho JS recalculando ao vivo.

**Por que existe:** decisão do dono de 10/09/2026. O desenho lista o `degrau` como rota nativa (§4.3)
e como camada viva (§8.4), e o Gate 3 é um dos cinco gates obrigatórios; nenhuma fatia do item 3 o
ligou ao wrapper.

**Dependências:** entra depois da correção do `rf` no wrapper e da Task 2 da fatia 4C (os
predicados de diagnóstico no espelho, que a Task 2 daqui reusa). Confira as duas no HEAD antes de começar.

**Tech Stack:** Python stdlib; JS sem dependências.

## Global Constraints

- `vendor/` read-only; `git status --short vendor` vazio ao fim de cada task.
- Nenhuma aritmética de valuation fora do motor (desenho §4.2, regra inviolável 1). Comparações
  entre outputs do motor são permitidas, como o `upside` já é.
- Nenhuma escolha sem default na metodologia recebe default (regra inviolável 3).
- Fixtures regeneram byte a byte; suíte inteira verde; baseline = a do HEAD ao começar.
- Commite assim que a suíte ficar verde, antes do relatório. Mutação de falseabilidade, teste e
  restauração num único comando.

## A metodologia, em uma tela (fonte: `vendor/multiplos-justos/references/aplicacao.md` §8 e §11.4)

```
h = índice_atual / índice_alvo                 (piso ADMINISTRÁVEL, não o teórico)
rentabilidade_pós = rentabilidade × [1 + (h − 1) × m]     m = eficiência marginal, declarada
g inalterado; rentabilidade terminal inalterada
valor = base + (pós − base) × fator_de_captura          (captura só sobre o incremento)
```

Leia o §8 inteiro antes de começar — as quatro travas obrigatórias estão lá, e o handler do motor
(`elif a.cmd == 'degrau'` no `main()` de `justos.py`) é a implementação de referência.

## Decisões de desenho — tomadas, com a razão

- **D1 — Bloco do caso, não rota nova.** Mesmo padrão de `reversa`/`sotp`: o degrau muda a
  rentabilidade dos cenários, não o vocabulário da rota.
- **D2 — Só rota equity.** Só nela o motor fecha o preço sozinho (`--vpa`, `--fx`). Na firm,
  transformar EV/Capital em EV exigiria aritmética de valuation no wrapper. Rotas `firm` e `rampa`
  recusam por nome (a rampa é, além disso, o domínio da capacidade *pré-construída*, que a
  metodologia manda nunca tratar como degrau × h).
- **D3 — O preço do cenário passa a ser o COM degrau; o sem degrau fica ao lado.** A metodologia manda
  usar o piso administrável *como cenário* e tratar a banda de `m` como faixa. Um preço por cenário:
  não abre um terceiro preço concorrente em `resultados.json` (resíduo já registrado com o SOTP).
- **D4 — `m` por cenário, declarado com razão, sem default.** A banda de `m` é a faixa bear–bull.
- **D5 — `anos` obrigatório.** O motor defaulta `--anos 0` (degrau instantâneo), exatamente o que a
  trava 2 proíbe presumir. `perfil_transicao` pode vir por default `rampa` — a própria metodologia o
  declara padrão —, mas `pontual` só com o evento datado declarado em texto.
- **D6 — `tv = book` com degrau exige `roe_book`** (SKILL.md:265, "obrigatório de fato"): sem ele o TV
  usaria a rentabilidade pós-degrau como média do estoque — conflação agravada pelo degrau.
- **D7 — `degrau` × `reversa`/`sensibilidades`/`sotp` recusado no gate, por nome.** As grades e a
  reversa hoje precificam sem degrau; misturar quebraria a regra da célula central (a célula na
  premissa do caso-base bate com a manchete). Limitação declarada, a reabrir quando um caso pedir.
  `tests/test_valuation_matriz.py` ganha as células.
- **D8 — Divergência de base registrada, não resolvida por conta.** Com `h = 1`, o P/VP base do
  degrau × VPA deveria reproduzir o preço da rota P/L. O wrapper registra
  `divergencia_de_base_%` — comparação entre dois outputs do motor — e o QC do item 5 decide a
  severidade. Sem isso, a diferença entre com e sem degrau atribuiria ao degrau um descasamento de base.
- **D9 — Fora desta fatia:** `--alvo-pvp` (índice implícito no preço — candidato a eixo da reversa
  depois); `classificacao` (prova do teorema — informativa, não entra no preço); rota firm; e as
  classes de evento que a tabela do §8 manda entrar por **re-base da métrica** (re-precificação
  regulatória, ativo parado), que não usam o comando `degrau`.

---

## Task 1: degrau no wrapper

**Files:** modify `skills/er-valuation/scripts/caso.py`, `skills/er-valuation/scripts/avaliar.py`,
`skills/er-valuation/scripts/motor.py`, `tests/test_valuation_matriz.py`,
`skills/er-valuation/SKILL.md` (uma seção curta, índice, sem metodologia);
create `tests/test_valuation_degrau.py`.

**O bloco:**

```json
"degrau": {
  "indice_atual": {"valor": 19.3, "fonte": "...", "data": "2026-06-30"},
  "piso_teorico": 11.0,
  "indice_alvo": {"valor": 14.0, "razao": "piso administrável: mínimo regulatório + buffer ..."},
  "anos": 4,
  "perfil_transicao": "rampa",
  "razao_transicao": "deployment gradual em tranches anuais ...",
  "vpa": {"valor": 29.11, "fonte": "...", "data": "2026-06-30"},
  "fx": 1.0,
  "m": {"bear": {"valor": 70, "razao": "..."},
        "base": {"valor": 100, "razao": "..."},
        "bull": {"valor": 130, "razao": "..."}}
}
```

**Gate (`caso.py`), por nome, no padrão dos outros blocos (`_exigir_texto`/`_exigir_lista`/`_numero_valido`):**
- rota ≠ `equity` → recusa (D2);
- `indice_atual.valor`, `indice_alvo.valor`, `piso_teorico` > 0; `indice_alvo.valor >= piso_teorico`
  (o alvo é o administrável, que nunca fica abaixo do teórico);
- `anos` presente e ≥ 0 (D5); `perfil_transicao` ∈ {`rampa`, `pontual`}, default `rampa`;
  `razao_transicao` texto não vazio — com `pontual`, é ali que o evento datado é declarado;
- `vpa.valor` > 0 com `fonte`; `fx` > 0, default 1.0;
- `m`: exatamente uma entrada por cenário do caso, cada uma com `valor` ≥ 0 (em %) e `razao`;
- `tv = book` em algum cenário sem `roe_book` nesse cenário → recusa (D6);
- `mid_year` em algum cenário → recusa: o subparser `degrau` não aceita `--mid-year`;
- `degrau` junto de `reversa`, `sensibilidades` ou `sotp` → recusa (D7).

**Motor (`motor.py`):** o subparser `degrau` não aceita `--ni`, `--acoes` nem `--mid-year` — o argv
do degrau não leva a escala da rota equity. Passe `--rf` e `--moeda` como nos outros subcomandos.
`indice_alvo` vai como um único valor (a flag aceita lista separada por vírgula). Confira a
tradução de nomes de flag (`indice_atual` → `--indice-atual`, `perfil_transicao` →
`--perfil-transicao`) contra a definição do subparser.

**Avaliação (`avaliar.py`):** com `degrau` no caso, cada cenário roda `pe` como hoje **e** `degrau`
com as premissas do cenário + o `m` do cenário. Shape de `resultados.json`:
- `cenarios.<nome>.valor.preco_acao` ← `niveis[0].preco_acao` do degrau (D3);
- `cenarios.<nome>.sem_degrau` ← o `valor` e os `multiplos` da rota P/L, íntegros;
- `cenarios.<nome>.degrau` ← `h`, `rentabilidade_pos_%`, `multiplo`, `multiplo_x_rentab`,
  `com_transicao`, `fator_transicao`, `perfil_transicao`, o `m` usado, os alertas que o motor
  emitir na linha do nível (`ALERTA`, `ALERTA_RiR`) e `divergencia_de_base_%` (D8);
- `resultado.degrau` ← o bloco declarado + as `travas_obrigatorias` do motor, verbatim.

**Testes (`tests/test_valuation_degrau.py`) — os que discriminam:**
1. **Âncora:** o exemplo do SKILL.md do vendor (`--indice-atual 19.3 --m 100 --anos 4
   --perfil-transicao rampa --roe 20 --ke 20 --g 12 --n 10 --tv gordon --roe-tv 20 --gp 6.5`, com
   um único índice-alvo) — o que o wrapper grava bate com a saída da CLI do motor para os mesmos argumentos.
2. **`h = 1`** (`indice_alvo = indice_atual`): o P/VP com transição é igual ao base — o degrau não
   inventa valor sem capacidade ociosa.
3. **`m = 0`**: rentabilidade pós = base.
4. **Rentabilidade terminal parada:** sem `roe_tv` declarado, o TV usa a rentabilidade **base**, não a
   pós-degrau (é o `or rent` do handler) — o número bate com o motor.
5. **Recusas nomeadas:** rota firm, rota rampa, `anos` ausente, `pontual` sem razão, `tv = book` sem
   `roe_book`, `mid_year`, `m` faltando para um cenário, e as três combinações do D7.
6. **`test_valuation_matriz.py`:** as células `degrau` × bloco — nenhuma combinação crasha cru.

Uma prova de falseabilidade: troque `rampa` por `pontual` na chamada ao motor, confirme vermelho
no teste da âncora, restaure.

---

## Task 2: degrau no espelho

**Files:** modify `skills/er-valuation/assets/motor_espelho.js`, `skills/er-valuation/scripts/vetores_solver.py`,
`tests/fixtures/vetores_solver.json`, `tests/test_paridade_wrapper_js.py`.

**Espelhar**, lendo do vendor: `fator_h`, `rentab_pos_degrau`, `desconto_transicao`,
`valor_transicionado` (`justos.py:792-830`) e o cálculo por nível do handler `degrau` (múltiplo
base, múltiplo pós, com transição, `preco_acao = round(v_tr × vpa / fx, 2)`, os dois alertas da
linha e o `ALERTA_CONVENCAO_BOOK`), mais `divergencia_de_base_%`. Os diagnósticos do cenário reusam
os predicados da Task 2 da 4C. **Paridade contra o wrapper** (`avaliar` com o bloco `degrau`), como
toda a paridade de wrapper.

**Detalhes que um espelho apressado erra:**
1. **`desconto_transicao` com `anos` fracionário** — tranche proporcional no último período; e
   `anos <= 0` devolve 1.0.
2. **`roe_tv` ausente vira a rentabilidade base** (`pc(roe_tv) or rent`) — inclusive quando é `0`,
   por causa do `or`. Espelhe o `or`, não uma checagem de presença.
3. **`m` chega em %** e passa por `pc()`; `indice_atual`/`indice_alvo` **não** (razão sem unidade).
4. **`preco_acao` arredonda `v_tr × vpa / fx`** sobre o `v_tr` não arredondado.

**Fixture (~10 problemas `degrau`):** âncora do SKILL.md; `h = 1`; `m` ∈ {0, 70, 130}; `anos`
fracionário; `pontual`; `book` com `roe_book`; um nível que dispare `ALERTA` (rentabilidade pós
implausível) e um que dispare `ALERTA_RiR`.

**Testes:** valores e alertas por problema, exatos nos campos arredondados; e cobertura mínima dos
casos acima. Uma prova de falseabilidade: aplique o fator de captura sobre o valor inteiro, não só
sobre o incremento — confirme vermelho, restaure.

---

## Verificação final da fatia D

Uma revisão (opus) da fatia inteira. Material: o que faria o Fleet atribuir ao degrau um valor
diferente do que a metodologia atribui, ou mostrar no laboratório um número ou alerta diferente do
wrapper. Suíte inteira, fixtures byte a byte, `vendor/` limpo.
