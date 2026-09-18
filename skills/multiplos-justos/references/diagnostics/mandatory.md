# Diagnósticos obrigatórios

## Diagnósticos obrigatórios (reporte sempre que dispararem)

Os das travas do Gate 1 (conflações da `book`, raiz condicionada, sub-alerta) e do Gate 0.5
(payout ≈ 0 ⟹ retenção não-informativa; quadrante proibido) já estão nos gates — narre-os lá.
Os demais:

- Cadeia §11.1b com gap > 10% entre (d×EBITDA + RiR×NOPAT) e (capex_total + ΔWC) → par d×RiR
  em base errada; RiR canônico < 0 com g > 0 (D&A > capex) → vetor não representável: migrar o
  par para base caixa, nunca ajustar uma metade só
- **Δreceita ≤ 0 no período do deployment (janela ≥ 12 meses)** → o reinvestimento observado mede
  DESINVESTIMENTO, não o custo de crescer: proibido como âncora, ao lado de payout ≈ 0 e de payout
  sobre base ≠ lucro. Rota obrigatória: derivar prospectivamente por intensidade de capital POR
  PERNA — giro pelo ciclo de caixa observado, fixo pela base de ativos — com o RiR como OUTPUT
  (`aplicacao.md` §2 e §11.1c). Teste secundário, válido nos dois sinais de giro: `ΔWC/Δreceita`
  deve ficar próximo de `WC/receita` em razão E em sinal; divergir indica que o deployment
  observado não está medindo intensidade marginal
- **Deriva da alavancagem a mercado ≥ ~10 p.p. de D/V ao longo do horizonte** (compare D/V hoje com
  o D/V implícito no ano n pelos fluxos) → um custo de capital único não corresponde a NENHUM
  período da trilha consistente: rode `apv` e reporte a faixa `Ke_t`/`WACC_t` ao lado do valor
  único, com o efeito no valor. Abaixo do gatilho, declare que a deriva é imaterial — nunca o
  silêncio
- RiR = g/ROIC > 100% → não autofinanciável; EXIGE funding declarado. Sem funding plausível,
  hipótese FORTE de erro de classificação (degrau lançado como taxa) — a investigar. Na reversa,
  a busca fica restrita a RiR ≤ 100% (`faixa_de_busca`); raiz via `--rir-externo` só se apresenta
  com a fonte de funding
- Spread < 0 com g > 0 → crescer destrói valor | g/ROE > 100% → emissão implícita |
  rentabilidade ≈ custo → neutralidade, a reversa não identifica | g ≈ 0 → neutro em
  rentabilidade SÓ em `gordon`/`convergencia` ou n→∞
- `degrau` com `book` sem `--roe-book`/`--roic-book` → conflação AGRAVADA (o pós-degrau entraria
  como médio do TV); informe a média ou use `gordon`/`convergencia` | pós-degrau implausível como
  estado estacionário → teto da alavanca, não cenário | degrau disponível não modelado → valor
  subestimado
- Impacto |elast × gap| > 10% em qualquer driver OU líquido agregado > 10% (a luz `GATE` dispara
  pelos dois; leia `GATE_agregado`) → múltiplo congelado defasado | drivers de receita e custo em
  direções opostas → reporte líquido E brutos | elasticidade do dominante ≥ 0,5 → grade de
  sensibilidade obrigatória MESMO com gate mudo (`aplicacao.md` §7)
- Gate de nível disparado COM terminal sem crescimento de preço (`convergencia`, ou `gordon` com
  gp ≈ 0) → fluxo real a taxa nominal (Modigliani-Cohn); dupla entrega exige rota Fisher **exata**:
  fluxo real + taxa real (central) ou nominalização de TODO o horizonte + taxa nominal. Inflação
  somente no TV é aproximação terminal-only, nunca a âncora exata (`aplicacao.md` §2; `normaliza` avisa)
- Tela NTM vs base corrente → alvo deslocado em (1+g) | comparação com terceiros sem checar
  mid-year vs fim de ano
- Mudança ≥ 10% na base de capital em 12m (IPO, follow-on, recompra, baixa, M&A) → ROE/ROIC de
  LTM inválido: numerador de uma empresa, denominador de outra
- Evento de estrutura DATADO → `ponte` com as duas travas (Ku único; rebase se razão ≠ 1); ponte
  > 10% do valor → modele as fases; reversa/iso com evento datado → NUNCA monofásica sobre o alvo
  cheio: `iso --transicao ponte` (inversão bifásica fechada **condicionada ao rebase declarado**; não é
  identificação estrutural pura de ROE₂ marginal) | `iso book --transicao nenhuma` sem `--rent-book`
  conflaciona marginal×médio (o motor avisa); com `--transicao ponte`, `--rent-book` é rejeitado
  porque o book da fase 1 é `--pt-roe1-book` e não existe `ROE2_book` separado nesta versão
- **Alíquota efetiva ≠ marginal em mais de ~5 p.p.** → `t` é parâmetro ÚNICO no motor (explícito e
  terminal), e diferimentos, incentivos com prazo e prejuízo acumulado são temporários por natureza:
  ou o caso-base usa a marginal ajustada com a efetiva como sensibilidade, ou a entrega declara por
  escrito qual benefício é estrutural e por que sobrevive à perpetuidade (`aplicacao.md` §2)
- **Beta de regressão da própria ação usado como rota central** → é confronto, não âncora: a rota
  central é o beta bottom-up de pares desalavancados e realavancados ao D/E a mercado
  (`aplicacao.md` §2). Divergência grande entre os dois é achado, não motivo para trocar de rota
- **Domínio:** g/gp/gtv ≤ −100% ou custo de capital ≤ −100% → hard error. **d ≥ 100% do EBITDA** →
  lucro operacional após imposto negativo e múltiplo de EBITDA com o SINAL INVERTIDO: o múltiplo
  justo não está definido nessa base — normalize a métrica, migre o par (d, RiR) para base caixa ou
  migre para a rota interna adequada do framework (`aplicacao.md` §13). **d ≥ ~60%** → regime de D&A-overhang, e a conservação
  deixa de ser opcional. **t fora de 0–100%** → regime anômalo, não bloqueado, com justificativa
  explícita. O motor emite os três (v10); até a v9.32 a regra existia só na doutrina e um `d` de
  120% devolvia EV/EBITDA negativo em silêncio. Erro de unidade nunca pode virar múltiplo
  aparentemente plausível.
- gp sem `--rf` → não ancorada (avisada); gp > rf nominal (ou > ~3% real) → excesso quantificado
  e tese da exceção por escrito | `--moeda` ausente → aviso | base nominal×real inconsistente →
  ROIC inflado, RiR subestimado, valor inflado (`aplicacao.md` §2)
- Marca de estoque ≥ ~20% do valor sem fator de tempo, apreciação implícita, T ou gap entre rotas
  → marca adotada como líquida hoje sem rótulo | custo de capital do ativo herdado do consolidado
  sem declaração | deságio aplicado sobre agregado LÍQUIDO de passivos → desconta a dívida junto |
  base de fluxo ancorada ou VALIDADA em métrica que contém realização de estoque → parede violada
- Segmentos com economia materialmente diferente → blended é erro sistemático (`aplicacao.md`
  §12) | premissas de validade violadas pelo caso (margens, D/E, caixa, RiR, payout constantes;
  crescimento só por novos investimentos) → citar quais
