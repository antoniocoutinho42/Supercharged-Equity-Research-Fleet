---
name: multiplos-justos
description: "Framework de múltiplos justos (justified multiples) — o múltiplo como output de um DCF comprimido em poucas variáveis (g, ROIC/ROE, WACC/Ke, CAP, alíquota, D&A), com degraus de nível tratados separadamente das taxas. Use APENAS quando o usuário invocar explicitamente o comando \"/multiplos-justos\" ou pedir de forma inequívoca para \"rodar o framework de múltiplos justos\" / \"rodar múltiplos justos\". Esta skill NUNCA deve disparar automaticamente, mesmo que o contexto sugira que seria útil — perguntas sobre múltiplo justo, valuation rápido, EV/EBITDA justo, P/L justo, engenharia reversa de múltiplo ou 'quanto vale a companhia' NÃO acionam a skill por si só. Nesses casos, responda normalmente e OFEREÇA em uma linha: 'isso é caso de /multiplos-justos, quer que eu rode?' — e espere a confirmação."
---

# Múltiplos Justos — o múltiplo como output de um DCF

Sob premissas estáveis o DCF colapsa numa fórmula fechada de poucas variáveis, e o múltiplo justo
sai delas. Derivado e provado na planilha do usuário (checks algébricos = 0). **Versão v9.24**
(v9.15: base coerente, Gate 0.5, camadas do RiR, confronto temporal, canal único de risco-país —
origem J8; v9.16: parede processo×produto, conclusões na largada, memória técnica separada,
caixa/E em híbrida; v9.17: menu de reconciliação com custo de capital implícito obrigatório,
dualidade dos eixos de denominador, gatilho de duração — origem J10; v9.18: premissas fixas
da largada e variante do RiR por retenção observada — origem J11; v9.19: conservação de
capital d×RiR, migração de par em D&A-overhang e 8ª escolha nomeada — origem J12; v9.20:
elevação da fronteira de consolidação a 9ª escolha nomeada e exceção de payout sobre base ≠
lucro — origem J13/J14; v9.21: quadro "como o valor é formado", primeira aparição ensina, e
mandato de perfil/históricos/guidance no item 3 — apresentação apenas; v9.22: RiR por
componente e leitura de capacidade como 10ª escolha nomeada, rota SOTP por safra de capital no
§12, e unit economics como canal de validação do triângulo — origem J15; v9.23: forma fechada
da rampa, composição de fases (recursão, biblioteca de blocos, trava do delimitador, bloco de
colheita), reversa sob intensidade constante, fallback da contraprova e item 3 em delta na
reavaliação — origem J15, teste frio + derivação em planilha; v9.24: SEM herança em hipótese
alguma (bloco do usuário vira dado de confronto; fluxo completo sempre, delta do item 3
revertido) e motor fechado — comando `rampa`, `--roic-ue`, `--capex-total`/`--dwc`, âncora e
suíte em testes.py).

**Acionamento:** só com `/multiplos-justos`, "rodar múltiplos justos" ou "rodar o framework". Não
infira intenção. Sem o comando, responda normalmente e ofereça a skill em uma linha.

**Identidade central:** g = RiR × ROIC (RiR = taxa de reinvestimento; é a 'value driver formula' de Copeland/McKinsey) ⟹ **FCFF = NOPAT × (1 − g/ROIC)**
**Ponte EBITDA:** EV/EBITDA = EV/NOPAT × (1−d)(1−t), d = D&A % EBITDA, t = alíquota
**Equity:** FCFE = LL × [(1 − g/ROE) + (GD/E − ND/E)·(g/ROE)], onde GD/E − ND/E = caixa/equity
**Drivers de valor:** só rentabilidade acima do custo de capital e o crescimento que expõe capital
novo a esse spread.

**Neutralidades — nunca cite sem o qualificador:**

| Neutralidade | Vale quando | Quebra quando |
|---|---|---|
| ROIC=WACC ⟹ fwd = 1/W [identidade] | `convergencia`/`gordon` com marginal=W; `book` com marginal **E** book = W | `book` com book≠W (o diagnóstico avisa); o corrente varia com g por reajuste de base — não é criação de valor |
| g=0 ⟹ invariante a ROIC | `gordon`/`convergencia`, ou n→∞ | `book` com CAP finito: TV = 1/(ROIC_book(1+W)ⁿ) (W 7%, n 10: 23,97x a ROIC 3% vs 8,04x a 50%) |
| sinal ∂múltiplo/∂g = sinal do spread | só na base **forward** | base corrente |
| ROE=Ke neutro (equity) | **caixa/E = 0** | com caixa líquido o P/L fwd sobe com g sem spread (Ke 12%, n 10, caixa/E 20%: 8,33x a g=0 → 9,04x a g=6% — módulo de política de caixa; o `pe` decompõe); no `gordon` a política vale no terminal por default — `--politica-tv continua|encerra` move 2–6% do P/L |

## Cinco gates antes de qualquer conta

### Gate 0 — Capital econômico e qualidade dos inputs contábeis (v9.7, ampliado na v9.11)

Quatro verificações ANTES de aceitar qualquer input contábil — todas declaratórias (registram e
avisam, nunca bloqueiam nem convertem), com detalhe operacional em `aplicacao.md` §1:
- **Capital econômico.** Pergunta obrigatória, resposta registrada: *P&D, aquisição de clientes,
  software, marca são despesa ou investimento econômico neste negócio?* Expensar investimento
  reduz o NOPAT, omite capital, infla o ROIC médio e oculta reinvestimento — quatro erros na
  mesma direção; derive o marginal pelo deployment TOTAL quando a resposta for "investimento".
- **Teorema da base coerente (v9.15).** Base de lucro e RiR devem vir do MESMO regime contábil —
  misturá-los cobra o mesmo investimento duas vezes ou nenhuma:

  | Regime | Base | RiR que entra no motor |
  |---|---|---|
  | **A — investimento é despesa** (GAAP puro) | LL/NOPAT reportado (deprimido pelo investimento despesado) | SÓ o capital de balanço financiado por equity: capex de crescimento + ΔWC + M&A − funding próprio do braço financeiro. NUNCA a retenção integral. |
  | **B — investimento é capital** (Damodaran, capitalização de intangíveis) | LL/NOPAT normalizado: soma-se de volta o investimento despesado e subtrai-se a amortização do ativo criado, com vida útil DECLARADA (hipótese, com direção do erro) | Retenção + investimento via DRE, sobre a base normalizada |

  **Quadrante proibido: base do regime A com RiR do regime B** (base deprimida + retenção
  integral) — cobra o investimento duas vezes (jurisprudência J8: −60% de valor). O inverso
  (base normalizada + RiR só de balanço) não cobra nenhuma; também proibido. Em fase de
  investimento (Gate 0.5), a entrega traz OS DOIS regimes — regime A = piso, regime B = base —
  como a 6ª bifurcação nomeada da dupla entrega. Camadas do RiR em `aplicacao.md` §2.
- **Qualidade do book** (obrigatória sob `--tv book`): classifique em `reportado` / `ajustado` /
  `reconstruído` / `proxy` / `nao_confiavel`. `nao_confiavel` ⟹ `book` fora do cenário-base
  (vira sensibilidade identificada); sem classificação ⟹ a entrega declara "qualidade do book:
  NÃO AVALIADA" — `reportado` não significa confiável.
- **Fronteira EV/EBITDA** (obrigatória quando a base é EBITDA): IFRS-16 e coerência com o EV,
  PPA/depletion no d, SBC, reportado vs ajustado, alíquota normalizada, fronteira de
  consolidação — checklist completo na `aplicacao.md` §1. Não declarado = "não avaliado", nunca
  implícito.
- **Natureza do `d`, antes da composição** (v9.12): *"para manter o volume, a companhia precisa
  comprar outro ativo igual?"* Se SIM — royalty, catálogo musical, carteira de patentes, licença
  exaurível —, a D&A é o capex de reposição com outro nome: o `d` é economicamente REAL e não sai
  do cálculo. Se NÃO (PPA de aquisição), é não-caixa sem ativo a repor e infla o `d`. Confundir os
  dois **inverte o sinal do ajuste**; regra completa em `aplicacao.md` §2. Depois da natureza, a
  **conservação (v9.19)**: d e RiR são duas metades do mesmo capital
  (capex_total + ΔWC = d×EBITDA + RiR×NOPAT); d econômico ≠ contábil obriga re-derivar o RiR na
  mesma base, e D&A > capex (fim de ciclo) obriga migrar o PAR inteiro para base caixa — regra e
  quadrantes proibidos em `aplicacao.md` §2, verificação em §11.1b.
- **Coerência do vetor (v9.11).** O motor recebe (g, ROIC, W, d, t, D/E) como parâmetros LIVRES,
  mas na planilha de referência eles são OUTPUTS acoplados por identidades. Montar cenário
  perturbando um driver que veio da reversa — o uso normal — pode produzir vetor que nenhuma
  DRE/BP gera. Passe os opcionais `--roe`/`--roic`, `--kd`, `--gde`, `--nde`, `--rir-observado`,
  `--ebitda-ic` e o motor confronta quatro identidades: **ROE = ROIC·(1 + ND/E) − Kd(1−t)·(D/E)**;
  **WACC = [Ke + Kd(1−t)·(D/E)] / (1 + ND/E)** (a MESMA transformação — é ela que faz
  ROIC=WACC ⟺ ROE=Ke ser exata); **RiR observado × g/ROIC** (divergir é legítimo, ficar calado
  não — e com payout ≈ 0 a retenção observada é NÃO-INFORMATIVA: camadas do RiR, `aplicacao.md`
  §2); e **EBITDA/capital investido = ROIC/((1−d)(1−t))**, que o balanço tem de confirmar. Sem os
  opcionais nada quebra — o output declara o que NÃO pôde ser checado. **(v9.22)** Quando o ROIC
  for resíduo do triângulo (g e RiR inputs), a validação por unit economics do §11.2 da
  `aplicacao.md` é o terceiro canal, no mesmo estatuto do RiR observado — divergir é legítimo,
  ficar calado não; flag `--roic-ue` executável no `ev` (v9.24).
  **Este gate não deriva drivers de demonstrações**: a cadeia DRE/BP/FC → drivers segue fora do
  motor por decisão de projeto. A skill aplica o framework; não substitui o modelo do analista.

### Gate 0.5 — Fase da companhia (v9.15): decide o regime da base, ANTES das premissas

Classifique e declare, com os observáveis:
- **INVESTIMENTO** (payout ≈ 0 E margem comprimida por decisão declarada da administração E/OU
  consenso t+2 ≫ LTM): teorema da base coerente obriga a dupla base (regime A = piso, regime
  B = base); a reversa em nível SÓ conclui após o confronto temporal (`aplicacao.md` §4); RiR
  contábil não-informativo (camadas do RiR, `aplicacao.md` §2).
- **DISTRIBUIÇÃO** (payout relevante e estável): retenção observada É informativa; base
  reportada serve; fluxo padrão sem mudanças.
- **MISTA** (payout > 0 com programa de investimento declarado): dupla base, com o RiR requerido
  derivado do deployment líquido — o caso comum em maduras que reinvestem.
- **HÍBRIDA FINANCEIRA** (carteira de crédito > 50% do equity OU receita financeira > 30% da
  receita, com funding próprio): rode `aplicacao.md` §12 (multi-segmento) com o braço financeiro
  pelo §9 (P/L; P/VP = P/L × ROE — prática padrão de SOTP: método por segmento, P/VP para a
  subsidiária financeira) e o operacional pelo fluxo normal; blended só com os testes declarados
  e a direção do erro. **Caixa/E (v9.16):** com dívida líquida positiva ou funding de carteira
  relevante, caixa/E = 0 é a escolha central obrigatória (§9) — o ramo bruto é a 7ª escolha
  metodológica nomeada, nunca o caso-base.

Fase mal classificada é o erro upstream de todos os outros (jurisprudência J8: companhia
INVESTIMENTO + HÍBRIDA rodada como DISTRIBUIÇÃO de payout zero).

### Gate 1 — Convenção terminal: qual hipótese sobre a morte do spread

**Não existe default:** o motor exige `--tv` e recusa rodar sem ele. A escolha é pela **DURAÇÃO
ECONÔMICA do claim**, não pelo rótulo do setor — regras completas, teste do teto e travas em
`aplicacao.md` §3 (a autoridade desta decisão).

| Convenção | Hipótese terminal | TV |
|---|---|---|
| **`book`** (ex-`ic`) | Renda residual truncada: o NOPAT inteiro colapsa para W×IC no ano n+1; exige book confiável (Gate 0) E âncora crível de saída (price-taker, regulado) | capital investido |
| **`convergencia`** | RONIC = W só no capital NOVO; rendas existentes preservadas (McKinsey/Mauboussin) | NOPAT/W |
| **`gordon`** (ex-`spread`) | rentabilidade terminal = RONIC/ROIIC **MARGINAL** do capital novo que sustenta gp; spread persistente, nulo ou negativo, justificado por DURAÇÃO | perpetuidade com gp |

**A diferença não é cosmética** (ROIC 50%, g 5%, W 7%, n 10: `book` 9,86x × `convergencia`
20,55x); cruzam exatamente em ROIC = WACC, e as propriedades famosas — múltiplo cai com ROIC,
teto em g — são da `book`: sob `convergencia` o múltiplo SOBE com o ROIC. Na dúvida, rode as
candidatas e mostre o gap: ele É a informação. Nunca escolha em silêncio. **A preliminar não é
final** — revalidação obrigatória na entrega, quando a rentabilidade marginal existir.

**TRAVAS (resumo executivo; detalhe e números em `aplicacao.md` §3):** `book` SEM
`--roic-book`/`--roe-book` com marginal < custo ⟹ conflação premia o destruidor de valor
(TV = NOPAT/ROIC sobe quando o ROIC cai) — informe o book ou use `gordon` com terminal < custo
declarado. COM o book informado, o múltiplo cai monotonicamente com o
marginal (W 7%, g 3%, book 10%: 2,96x a marginal 2% × 12,14x a 8% — comportamento correto) e a
raiz é CONDICIONADA (tese declarada de saída pelo capital investido), com sub-alerta se o próprio
book < custo (a tese vira RECUPERAÇÃO). Marginal ≠ médio
sob `book` ⟹ `--roic-book`/`--roe-book` obrigatório — sem ele o motor conflaciona os dois papéis
e alerta (erro pode passar de 30%).

### Gate 2 — Nível: defasagem (o nível que já mudou)

Financials reportados/TTM embutem o nível MÉDIO dos drivers no período-base. Se o spot divergiu, o
múltiplo congelado responde à pergunta errada.

Monte o **registro de drivers** — não existe "o" driver: commodity, câmbio, frete, energia, spread
de captação, teto/tarifa regulatória, take-rate, insumo. **A elasticidade é DERIVADA, não
arbitrada:** com custo e volume fixos no curto prazo é alavancagem operacional pura,
`elasticidade = linha exposta ÷ métrica-base`, **com sinal** (use `auto:LINHA:METRICA[:custo]`):
driver de **receita** (commodity vendida, take-rate, tarifa) entra positivo; driver de **custo**
(frete, energia, insumo, câmbio no COGS) entra **negativo** — a linha exposta é o custo do insumo,
não a receita total. Só arbitre quando não houver como derivar, e diga por quê.

Rode `drivers`. **O gate dispara pelo IMPACTO = |elasticidade × gap|, não pelo gap:** gap de 12%
com elasticidade 0,1 é irrelevante (1,2%); gap de 8% com elasticidade 3,0 move o valor (24%).
**Trava anticombinatória:** viram cenário só os dois de maior impacto entre os que passam do
limiar; o resto é linha de sensibilidade, e quem ficar de fora acima do limiar tem que ser
declarado. Drivers podem se compensar — o registro reporta **efeito líquido (com sinal)** e
**soma dos brutos**, e alerta quando o líquido é menos da metade dos brutos: reporte os dois, o
líquido decide o gate agregado e os brutos mostram o risco de a compensação não se sustentar. Gate disparado ⟹ `normaliza`
ALÉM do período-base e reversa do nível implícito (`nivel`).

### Gate 3 — Nível: degrau disponível e capacidade pré-construída (v9.22)

Capacidade ociosa que eleva o lucro sem reinvestimento: índice de capital acima do piso, caixa
excedente estrutural, capacidade licenciada, folga de covenant, margem regulatória. Se existir,
rode `degrau`. **Regra inegociável: o degrau GRATUITO entra como RENTABILIDADE (× h), nunca como
g, e a rentabilidade terminal NÃO acompanha.**

**Gatilho da capacidade pré-construída (v9.22).** Caso distinto do degrau gratuito: crescimento
que consome GIRO mas não capital fixo, porque o parque já foi pago. Disparam simultaneamente:
(i) capital fixo intensivo — imobilizado + direito de uso ≥ ~40% dos ativos operacionais, OU
d ≥ ~20% do EBITDA; e (ii) evidência de ociosidade material — utilização divulgada < ~85%,
linhas/plantas "atingindo regime" declaradas, capex recente ≫ D&A com receita ainda respondendo,
ou guidance de margem "por escala". Disparado ⟹ decompõe-se o RiR por componente
(RiR = RiR_fixo + RiR_wk, pela conservação de capital) e a **leitura de capacidade** vira a 10ª
escolha metodológica nomeada. Entrada, fases, compressões, composição multifásica e travas em
`aplicacao.md` §8f — fases compõem NO TEMPO (§8f), safras NO CAPITAL (§12); quando os claims da
base instalada e da expansão tiverem durações distintas, §12 (safra de capital).

**Coerência:** o deployment viola D/E constante por construção. O resultado vale para o **estado
estacionário pós-deployment**, nunca para a trajetória — por isso existem o fator de transição
sobre o incremento (rampa linear por padrão; `pontual` só com evento datado — a 20% e 4 anos, 0,647
contra 0,482) e a rentabilidade terminal parada.

Teoria em `derivacao.md` §8, aplicação em `aplicacao.md` §8.

## Moeda, regime e âncora macro (v9.4 — guardas opcionais)

Regra travada: g, gp e custo de capital na MESMA moeda e MESMO regime (nominal/real), sempre
declarados — `--moeda` (ex.: BRL-nominal, USD-nominal, BRL-real) ecoa como convenção em todo
output e viaja até a memória de cálculo; sem ela, o motor avisa. Âncora macro do gp (Damodaran):
gp perpétuo ≤ rf NOMINAL da moeda (`--rf` ativa a verificação; em regime real, teto ~3% de PIB
real). gp acima do teto não é bloqueado — é hipótese legítima SE declarada por escrito na
entrega; o motor quantifica o excesso e exige a declaração. O motor nunca converte moeda nem
verifica moeda a partir de números: a guarda é declarativa, e é exatamente aí que mora o valor.

## Ponte de releveraging — mudança discreta de estrutura de capital (v9)

A fórmula assume D/E constante; quando a estrutura MUDA uma vez (deleveraging pós-RJ, dividend
recap, banco capitalizando), o salto não é taxa nem degrau de rentabilidade — é um **evento de
caixa único** entre empresa e acionista, e tem preço: `fluxo = E_pré·(GD/E₂·razão − GD/E₁)·
(1+Kd_at)` no ano n1+1, com `razão = (1+ND/E₁)/(1+ND/E₂)`. Rode `ponte`. Sinal negativo =
acionista financia a amortização; positivo = dívida levantada vira distribuição. Derivada da
planilha bifásica do usuário (vF19, checks ~1e-13); com estrutura igual é identicamente zero e o
caso volta a ser o `pe` monofásico. Ordem de grandeza medida: −40% do valor num deleveraging
pesado, +10 a +21% em recap/alavancagem — nunca ignorar, nunca somar sem as DUAS travas:
**(i)** a ponte precifica o movimento de caixa, não o risco — Ke por fase TEM que sair de um Ku
único (`apv`); o motor reporta o Ku implícito de cada fase e alerta o gap (MM: com Ke
reprecificado, o efeito líquido da alavancagem é só o tax shield); **(ii)** com `razão ≠ 1` o
lucro rebasa junto — o NI da fase 2 entra ×(ROE₂/ROE₁)·razão (degrau composto, teorema da
classificação) — somar a ponte a valuation não-rebasado mistura as camadas. Derivação e prova do
colapso em `derivacao.md` §8b; caso aplicado em `aplicacao.md` §8.

## Motor de cálculo

**Provas vs proveniência (leia antes de auditar):** a prova VERIFICÁVEL de cada resultado está
DENTRO do pacote — `testes.py` reconstrói independentemente o núcleo (DCF↔EVA, fluxos explícitos,
terminal C1 em 300 sorteios, APV com checks zerados, contraprova da ponte por soma explícita,
autovalidação do iso por re-avaliação) e `selftest` trava os números. As planilhas citadas (vF8,
vF8.1, vF19) são a PROVENIÊNCIA HISTÓRICA dos anchors — de onde os números vieram — e não são
necessárias para verificar nada: quem não as tem roda `python scripts/testes.py` e obtém a mesma
garantia.

SEMPRE use `scripts/justos.py` — nunca calcule na mão. Auto-valida contra os anchors da planilha e
aborta se divergir.

```bash
python scripts/justos.py selftest                     # 1x por sessão (anchors, incl. APV vF8)
python scripts/testes.py                              # suíte completa: propriedades, reconciliações, boundaries (rodar se o motor for questionado ou alterado)
python scripts/justos.py ev  --g 5 --roic 8.5 --wacc 7 --n 10 --da 15 --tax 15 --tv gordon --roic-tv 20 --gp 3 [--ebitda 100 --nd -20 --acoes 50] [--mid-year] [--roic-book X, obrigatório em `book` com marginal ≠ médio] [--roic-ue X — validação por unit economics §11.2, v9.24] [--capex-total X --dwc Y — conservação §11.1b executável, v9.24]
python scripts/justos.py rampa --receita0 265 --ebitda0 26.8 --da-parque 6.8 --wk 19.1 --util 65 --t-rampa 5 --g2 8 --kappa 17.9364 --wacc 11.9 --tax 35 --n 10 --tv convergencia [--g1 X em vez de --util; negativo = colheita] [--nd -104.6 --acoes 30.46]   # v9.24 — composição bifásica §8f: rampa (forma fechada α/β, autovalidada fluxo a fluxo) + expansão costurada como TV; ecoa d re-basado, RiR por fase, travas e delator
python scripts/justos.py pe  --g 11 --roe 44.83 --ke 22 --n 10 --gde 53.85 --nde 46.15 --tv book [--ni 26.25] [--politica-tv continua|encerra]   # decomposição operacional × efeito-caixa; politica-tv só afeta gordon com caixa
python scripts/justos.py rev --alvo 27 --resolver wacc|roic|g|gp|cap --g 5 --roic 8.5 --n 10 --tv gordon --roic-tv 20 --gp 3 [--tol 1] [--alvo-base corrente|forward] [--mid-year] [--rir-externo]   # lado FIRM (base ebitda|nopat)
python scripts/justos.py rev --alvo 8.5 --base pl --resolver ke|roe|g|gp|cap --g 8 --ke 15 --n 10 --gde 40 --nde 30 --tv convergencia   # lado EQUITY: resolver ke/roe EXIGE --base pl (o motor trava a combinação errada)
python scripts/justos.py kewacc --ku 20 --kd 14.27 --tax 30 --de 46.15 [--conv mm|ku]   # sanity check ESTÁTICO
python scripts/justos.py apv --fcff1 22.184 --g 11 --n 10 --ku 20 --kd 14.27 --tax 30 --d0 35 [--fcff-tv 50.53 --gtv 0 --conv mm|ku]   # recursão dinâmica: Ke_t/WACC_t por período, checks FCFE@Ke_t=E0 e FCFF@WACC_t=V0
python scripts/justos.py tabela ev --wacc 7 --da 15 --tax 15 --n 10 --centro-roic 8.5 --centro-g 5 --tv gordon --roic-tv 20 --gp 3 [--base forward|corrente]
python scripts/justos.py drivers --driver "ouro:4050:4550:auto:730.95:446.43" --driver "frete:100:130:auto:80:446.43:custo"   # ":custo" inverte o sinal
python scripts/justos.py normaliza --ebitda-base 446 --da 130 --preco-base 5.00 --preco-novo 6.26 --rev-driver 731 --tax 18.5 --tv book [--limiar 10] [--g 5 --roic 15 --wacc 11 --nd 512 --acoes 104]
python scripts/justos.py degrau --indice-atual 19.3 --indice-alvo 16,14,13,11 --m 100 --anos 4 --perfil-transicao rampa --roe 20 --ke 20 --g 12 --n 10 --tv gordon --roe-tv 20 --gp 6.5 [--roe-book X | --roic-book X, obrigatório de fato com --tv book] [--vpa 29.11 --fx 5.115] [--alvo-pvp 1.25]
python scripts/justos.py nivel --alvo-valor 5824 --multiplo 5.60 --metrica-base 931 [--vol 146.2 --preco-base 5.00]
python scripts/justos.py iso pe --alvo 5.73 --ke 22 --n 10 --gde 53.85 --nde 46.15 --tv book --transicao nenhuma [--rent-book 28] --g-min 8 --g-max 16 --pontos 5   # curva iso-valor; --transicao OBRIGATÓRIA (nenhuma = regime único declarado); --rent-book separa marginal×médio no TV da book (sem ela o motor avisa)
python scripts/justos.py iso pe --alvo 36.4 --ke 16 --n 12 --gde 30 --nde 20 --tv book --transicao ponte --pt-n1 5 --pt-ke1 22 --pt-gde1 80 --pt-nde1 60 --pt-kd 11 --pt-tax 30 --pt-g1 12 --pt-roe1 10.85 [--pt-roe1-book X]   # evento de estrutura datado: inversão bifásica EXATA (book, sem fade) — remove f1, ponte e TV com os regimes declarados e resolve ROE2 em forma fechada, verificando cada ponto contra o bifásico completo
python scripts/justos.py ponte --n1 5 --ke1 22 --ke2 16 --gde1 80 --nde1 60 --gde2 30 --nde2 20 --kd 11 --tax 30 --g1 12 --roe1 10.85 [--roe1-book 9.2] [--kd1 16] [--ni X | --equity Y] [--pl-base 36.6]   # mudança discreta de estrutura de capital
```
Taxas em %, monetários na unidade do usuário. `--nd` negativo = caixa líquido. Aliases legados
`ic`/`spread` continuam aceitos com aviso, número a número. `rev` reporta múltiplas raízes,
**raízes tangenciais** (alvo ≈ extremo da função — a bissecção pura as perde), neutralidades e
alvos incompatíveis, e traz **métricas de identificação por raiz** (slope, curvatura,
elasticidade, intervalo para alvo ±tol, classificação forte/moderada/fraca) — raiz com
identificação fraca é ruído com cara de precisão e não se apresenta sem o intervalo. `cap`
sai interpolado entre anos inteiros, sempre condicional às demais premissas.

**Convenções do motor — declaradas na entrega (default ≠ neutro):**

| Conv. | Default | Alternativa / efeito |
|---|---|---|
| **C3 temporal** | fim de ano (= planilha) | `--mid-year` eleva ~4,4% a custo 9%; divergência de 4–5% com terceiros costuma ser isto |
| **D2 base do alvo** | `rev` em corrente/TTM | tela NTM sem `--alvo-base forward` desloca o alvo em (1+g) — a 12% de g, 12% de erro devolvido como premissa falsa |
| **C1 política de caixa no TV** | `continua` | `encerra` (só `gordon` com caixa ≠ 0); move 2–6% do P/L |
| **C2 Ke fixo** | Ke input, insensível à deriva da alavancagem | estruturas diferentes sob o mesmo Ke ⟹ rode `apv` e realimente o Ke (o motor declara a limitação) |
| **C7 fluxo de transição** | ano n+1 = base_n × (1+g), retendo gp/rentab_TV | alternativa (1+gp) muda SÓ o TV: efeito = TV_share × [(1+gp)/(1+g) − 1] — reporte o campo exato `efeito_c7_alternativa_gp_%`, não uma faixa |
| **C6 limiares** | ident. forte < 5%, moderada < 20% de largura; gate de drivers 10% (`--limiar`); tol do alvo 1% (`--tol`) | ajustáveis — declare se alterar |

**Teto da `book`:** é teto em g e CAP **com ROIC fixo e sob esta convenção** — propriedade do
terminal-book, não lei da convergência competitiva. Revertendo em ROIC, alvos altos acham raiz
abaixo do custo de capital — economicamente vazio; o motor sinaliza. Ao dizer "incompatível",
diga em qual variável e sob qual convenção. **Ordem de investigação:** (1) falta um degrau de
nível na métrica-base? (2) a convenção é a certa? (3) as demais premissas? (4) só então o preço.

## Sem herança de premissas (endurecida na v9.24 — SEM exceção)

A skill não guarda casos e não reaproveita premissas de análise anterior — premissa herdada
contamina com ancoragem invisível. Toda rodada re-deriva TUDO do zero e roda o fluxo COMPLETO:
todos os gates, todas as derivações, todas as seções da entrega — sem atalho, mesmo que fique
pesado. Bloco de inputs anexado pelo usuário (memória técnica de rodada anterior) NÃO isenta
nenhum passo: ele entra como DADO DE CONFRONTO — depois de re-derivar, compare os outputs com o
bloco e declare as divergências e suas causas (dado novo, premissa revista, erro anterior). O
peso certo da skill vem de não rodar o que não foi pedido; pedido o framework, ele roda inteiro.

## Fluxo por tipo de pedido

**1. Sanity check rápido de DCF:** extraia as variáveis, rode `ev`/`pe`, compare com o múltiplo do
modelo ou de tela. Divergência grande = inconsistência interna (RiR incompatível com g e ROIC;
spread perpétuo não declarado no terminal) ou erro mecânico. *Cobertura e encerramento não se
aplicam.*

**2. Valuation de companhia real:** dados ATUAIS, nunca de memória. Fontes: dado licenciado/
conector → documentos primários (release/ITR/DFP/20-F/deck de RI) → web para preço, consenso
(t/t+1/t+2, obrigatório — §1) e lacunas, com fonte e data. Aplique os gates 0, 0.5, 1, 2 e 3.
Leia `aplicacao.md` (pesquisa §1, regras travadas §2, convenção §3, cenários §4, financeiras §9,
memória de cálculo §11, multi-segmento §12).

**3. Engenharia reversa:** entregue o MENU de reconciliação (`aplicacao.md` §4) — os eixos
univariados aplicáveis com os demais no vetor central, sendo o **custo de capital implícito
OBRIGATÓRIO** (beta implícito contra a banda observada) e o NÍVEL implícito obrigatório havendo
driver ou degrau: são os dois eixos com observável de mercado direto para confronto.
**Confronto temporal ANTES de qualquer conclusão (v9.15):** nível implícito ≈ consenso t+1/t+2
(até ~+25%) ⟹ antecipação temporal, não fantasia terminal — a reversa migra para o vetor consenso
(`rev --resolver cap` contra a base futura = horizonte implícito de mercado); só acima de qualquer
consenso a hipótese terminal está no preço. Regra completa em `aplicacao.md` §4.
Com dois vetores de valor distintos, apresente a curva iso-valor (comando `iso`) e explicite que o mercado paga
por um, raramente pelos dois. **Quando NENHUM eixo primário (rentabilidade, g) tiver raiz (v9.13):**
dois passos deixam de ser opcionais — (a) o TETO DO CRESCIMENTO GRATUITO (caso-limite RiR→0,
`gordon` com rentabilidade terminal → ∞ e gp = g; a distância até o caso-base é o preço da
hipótese de gratuidade) e (b) a curva `iso` no mesmo alvo (mostra a partir de que g o alvo passa a
ter solução). O `rev` sugere ambos no próprio output (`sugestao`); a mecânica está em
`aplicacao.md` §8 (jurisprudência J3).

**4. Consistência Ke↔WACC:** âncora única em Ku elimina circularidade; Ke e WACC viram outputs. Dois
regimes: `mm` (dívida determinística, shields a Kd) e `ku` (shields a Ku sobre a trajetória EXÓGENA
D_t = D0(1+g)^t). **O nome `ku` descreve o mecanismo, não uma teoria:** é a convenção de RISCO dos
shields de Harris-Pringle sobre uma política de dívida exógena — o motor NÃO impõe D/V constante,
que é o que Harris-Pringle exige. O output ecoa `DV_t_%` justamente por isso (na âncora, 18,75% →
36,28%). `hp` e `me` seguem aceitos como aliases legados com aviso; HP verdadeiro (D = L×V, com a
circularidade resolvida) e Miles-Ezzell verdadeiro (primeiro shield a Kd) são roadmap
planilha-primeiro. Pesos SEMPRE a mercado. `kewacc` é o sanity check ESTÁTICO de perpetuidade; a trilha consistente é a recursão
`apv` (Ke_t e WACC_t período a período, com FCFE@Ke_t = E0 e FCFF@WACC_t = V0 por construção) —
um WACC único aplicado a todos os períodos não corresponde a nenhum período da trilha quando a
alavancagem a mercado deriva. Detalhes em `derivacao.md` §5.

## A entrega é um relatório de research — e um produto de mercado (fluxos 2 e 3, v9.16)

**Princípio da parede.** Gates, regras, convenções, jurisprudência, comandos e versões são a
infraestrutura do analista — o leitor recebe os ACHADOS, nunca a infraestrutura. Teste de
aceitação: um gestor que nunca viu esta skill entende 100% do texto, incluindo o porquê de cada
escolha, sem pedir nenhum documento adicional.

**Regra de substituição (o coração da parede).** Cada regra travada codifica uma razão econômica.
No relatório, a escolha é justificada pela RAZÃO — em uma frase, com o número — ou por fonte
externa citável (Damodaran, Mauboussin/Rappaport, McKinsey), nunca pela autoridade da regra.
"Pela regra §9, caixa/E = 0" vira: "num negócio com braço financeiro, o caixa é liquidez
operacional e regulatória, não excedente devolvível — e a companhia tem dívida líquida positiva".
Se a razão não couber em uma frase, a escolha não foi entendida: volte à regra antes de escrever.

**Lista de banimento no corpo do relatório** (uso interno segue livre): nomes e números de gates;
códigos de regra/convenção/jurisprudência (R#, C#, D#, J#, §#, "paper §"); números de versão da
skill; nomes de comandos e flags; enums do motor na prosa (`antecipacao_temporal`,
`nao_confiavel`); os termos internos "dupla entrega", "bifurcação", "quadrante proibido", "guarda
anti-empilhamento", "trava", "motor", "framework", "skill", "jurisprudência", "regra travada".
Conceitos entram TRADUZIDOS (tabela em `aplicacao.md` §5). O banimento é de rótulo, nunca de
conteúdo: grades, memórias de cálculo e marcadores de honestidade ("hipótese de construção",
"não verificado nesta sessão", "direção do erro") continuam obrigatórios.

**Formato dentro de cada seção** (inalterado): prosa com a conta inline; a tabela de seis colunas
é formato de Excel, nunca o corpo; grades provam o raciocínio (uma frase acima, uma abaixo) e
toda grade cujo output é preço por ação declara a métrica de referência.
**Primeira aparição ensina (v9.21):** na primeira vez que cada variável da cadeia (encargo de
reposição, alíquota, crescimento, retorno do capital novo, taxa de reinvestimento, custo de
capital) é USADA fora do quadro, até duas frases explicam sua função na formação de valor — por
que existe, não só qual número foi escolhido. Aparições seguintes não repetem. Teto duro: a
explicação nunca vira parágrafo.

Estrutura fixa, nesta ordem — conclusões na largada:

1. **Conclusão** (abre o documento): faixa de valor (piso–base–teto) com veredicto explícito
   contra o preço de tela (data e banda); múltiplos de tela corrente E forward com base
   declarada; consenso (PT médio, nº de analistas) como referência externa, ou a lacuna
   declarada quando não houver cobertura; e as **4–6 premissas
   decisivas ABERTAS já aqui** — cada uma com o número e uma linha de justificativa própria.
   **Quatro vagas da lista são FIXAS, sempre: (i) base de lucro/EBITDA; (ii) rentabilidade
   marginal (ROIC/ROE), com a derivação em uma linha; (iii) g; (iv) custo de capital.** As
   demais vagas são do caso (hipótese terminal, driver dominante, alavanca); a verificação das
   fixas está nos critérios de aceitação. O
   leitor com 60 segundos sai daqui com a tese, os números que a sustentam e a premissa cuja
   inversão a derruba.

   **Quadro "como o valor é formado" (v9.21 — fixo, ≤ meia página, entre a Conclusão e as
   Premissas).** Box destacado, em linguagem plana, que ensina a mecânica antes de qualquer
   variável ser usada: do EBITDA, (i) desconta-se o que a operação consome para **repor os
   ativos existentes** — o encargo de reposição, "d" (sem repor, o lucro de hoje não se repete
   amanhã); (ii) desconta-se o **imposto** sobre o lucro operacional, "t"; (iii) do que sobra,
   separa-se a fração **reinvestida para crescer** — e quanto custa crescer depende do retorno
   do capital novo (crescimento ÷ retorno = taxa de reinvestimento); (iv) o caixa residual é
   descontado pela margem entre **custo de capital e crescimento**. Cada variável nomeada com
   sua função em UMA linha e o valor adotado no caso. Fecha com a frase-síntese: o múltiplo
   justo é essa cadeia comprimida — muda a variável, muda o múltiplo; o quadro é o mapa para
   ler todo o resto do relatório. A lista de banimento vale integralmente dentro do quadro.

2. **Premissas principais**: estimativas próprias × consenso (t, t+1, t+2) com desvios
   justificados linha a linha; e a derivação premissa a premissa em prosa com a conta inline
   (cadeias de §11) e os cinco atributos embutidos. **Regra do triângulo por cenário**:
   g = RiR × ROIC tem dois graus de liberdade — declare quais dois são input e qual é output, e
   mostre a taxa de reinvestimento de cada cenário. Cenário com RiR silencioso é cenário opaco.
3. **Companhia, números & indústria** (mandato completo quando o fluxo é relatório de
   companhia; dispensado em reversa rápida e screening — e NUNCA em delta: reavaliação roda o
   mandato completo, sem herança, v9.24): **perfil** — o que a companhia é,
   segmentos, ativos relevantes, posição competitiva; **históricos de 3–5 anos** em tabela
   curta (receita, EBITDA e margem, lucro, dívida líquida/EBITDA, capex, retorno sobre o
   capital) com a leitura de tendência em prosa; **guidance vigente** — o que a administração
   promete, o que descontinuou, e o confronto com o realizado; **administração e governança**
   quando materiais à tese; competição, share, penetração, bull/bear do sell-side (§1); as
   verificações narradas pelos seus ACHADOS com as rubricas de tradução — qualidade do lucro e
   do capital; estágio do ciclo de capital; representatividade da base (drivers × spot);
   alavancas identificadas — nunca pelos nomes internos. Verificação silenciosa segue proibida:
   o que foi testado, o número, a consequência. Proveniência de tudo: verificado nesta sessão /
   derivado por regra / hipótese de construção / fornecido e revalidado.
4. **Valuation**: cenários da grade canônica (§4) com âncora observável e preço/ação pela ponte
   explícita; tabela de múltiplos justos centrada no caso-base com a base declarada (a célula
   central reconcilia com a manchete); sensibilidades travadas (custo de capital, gp, degrau);
   grade de sensibilidade ao driver quando a elasticidade do dominante ≥ 0,5 (§7). Cross-check
   por segundo método declarado (múltiplo de saída sobre t+2, ou soma das partes no híbrido).
   **A hipótese de valor terminal é re-testada aqui**, agora que a rentabilidade marginal existe
   — uma linha mesmo quando não muda nada; é onde o erro mais caro é pego.
   **Sensibilidade às escolhas metodológicas** (nome externo da dupla entrega; interno segue
   "bifurcações"): as DEZ — base do lucro (reportada × normalizada); alavanca de lucro
   (modelada com probabilidade × absorvida/excluída como opcionalidade); rentabilidade (marginal
   × forward de consenso); g (reinvestimento × guidance/consenso); hipótese terminal; regime do
   driver no terminal (congelado × acompanha inflação); **caixa/excedente em híbrida
   financeira** (zero central × bruto — v9.16, regra em §9); **(v9.19) o ano de capex de
   estado estacionário no par d×RiR** (corrente × guidance de longo prazo), com o RiR
   re-derivado pela conservação em CADA ramo — nunca com o triângulo congelado; e **(v9.20) a
   fronteira de consolidação quando minoritários/coinvestimento > ~20% do PL** (fatia de
   terceiros no EV pelo valor contábil × econômico estimado — ignorá-la não é ramo, é erro;
   gatilho em `aplicacao.md` §2); e **(v9.22) a leitura de capacidade quando o gatilho da
   capacidade pré-construída dispara** (ramo corrente: ociosidade ignorada, RiR pleno, d
   contábil × ramo capacidade: RiR por componente, fases do §8f, d do estado estacionário da
   capacidade) — o ramo capacidade só é caso-base com observável direto de utilização OU
   contraprova de receita-por-ativo contra pares a plena fechando dentro de ±15%; derivado só
   do protocolo físico sem contraprova, é sensibilidade identificada, nunca base em silêncio.
   Escolha alternativa movendo > ~10%
   ⟹ a tabela traz as duas, com o custo de cada uma e a escolha central justificada pela razão.
   **Coerência interna dos cenários** (nome externo da guarda anti-empilhamento): o caso-base
   usa a escolha CENTRAL de todas; o produto dos extremos conservadores É o bear (rotulado), o
   dos otimistas, o bull — escolher o ramo conservador de tudo no caso-base não é prudência, é
   cenário incoerente.
5. **O que está no preço**: o menu de reconciliação (§4) — nível implícito COM o confronto
   temporal contra o consenso, horizonte implícito, crescimento sem consumo de capital
   implícito, curva iso quando houver dois vetores, e **custo de capital implícito SEMPRE**
   (beta implícito contra a banda observada do beta — a explicação mais barata de esquecer).
   Fronteiras bivariadas plausíveis depois dos univariados, com a dualidade dos eixos de
   denominador declarada quando existir; **a seção fecha com o julgamento comparativo: qual
   reconciliação exige a menor violência às âncoras observáveis, e qual observável a testaria.**
   Perto da neutralidade a variável implícita é ruído com cara de precisão — reporte a
   curvatura. É a seção onde a abordagem é insubstituível — recebe o espaço.
6. **Riscos + veredicto**: os 4–6 que movem a tese, cada um com o observável que o monitoraria;
   fecha com alavanca dominante, o que a fórmula não captura, e a premissa cuja inversão viraria
   a conclusão.
7. **Visão não-consensual** (obrigatória, ≤ 15 linhas): leitura que não está na cobertura,
   construída SÓ com fatos já citados, com a cadeia factual explícita. Sem nenhuma, declare
   "sem visão não-consensual nesta rodada" — não invente.
8. **Metodologia, limitações e disclaimer**: um parágrafo de metodologia em linguagem plana —
   a identidade central (abordagem de múltiplos justificados: o múltiplo como saída de um DCF
   comprimido em poucas variáveis), citável sem mencionar a skill; a mecânica variável a
   variável NÃO se repete aqui: mora no quadro de abertura, que este parágrafo referencia;
   e o disclaimer específico ao caso, nunca genérico
   (lista aceitável): pocket valuation e não DCF nem DD; o que não captura por construção;
   premissas de estabilidade e quais o caso viola; contabilidade específica; direção do erro de
   cada premissa congelada.

**Memória técnica — o segundo artefato (v9.16).** O bloco YAML (§6) NÃO entra no relatório:
é entregue como artefato separado rotulado "memória técnica — uso interno" (arquivo próprio
quando a entrega for arquivo; bloco final destacado quando for chat). Mantém todos os campos
internos — é onde a reprodutibilidade mora. No relatório, seu lugar é um quadro de premissas em
linguagem plana (custo de capital, crescimento, retorno, taxa de reinvestimento, horizonte,
hipótese terminal — uma linha cada), dentro do item 8. Título e nome de arquivo do relatório sem
versão da skill; a versão vai na memória técnica. **Captura de aprendizado e oferta de
aprofundamento são chat-only: nunca dentro de arquivo entregável.**

**Critérios de aceitação, antes de enviar:** (i) leitor frio refaz a análise inteira só com o
texto — número sem a conta = incompleto; (ii) só a prosa, pulando grades e contas, sustenta o
raciocínio da conclusão ao detalhe; (iii) zero termos da lista de banimento no corpo (verifique
por busca literal antes de entregar); (iv) as quatro premissas fixas presentes na Conclusão,
cada uma com o número e a derivação — fixa ausente ou sem número = entrega incompleta; (v) um
analista que não conhece teoria de múltiplos entende a FUNÇÃO de cada variável a partir do
quadro e das primeiras aparições — variável usada sem função explicada = entrega incompleta.

**Trava de encerramento:** não ofereça aprofundamento com a cobertura incompleta. Faltando
espaço, corte prosa do veredicto e do disclaimer — nunca as premissas, a memória de cálculo ou a
memória técnica.

## Diagnósticos obrigatórios (reporte sempre que dispararem)

Os das travas do Gate 1 (conflações da `book`, raiz condicionada, sub-alerta) e do Gate 0.5
(payout ≈ 0 ⟹ retenção não-informativa; quadrante proibido) já estão nos gates — narre-os lá.
Os demais:

- Cadeia §11.1b com gap > 10% entre (d×EBITDA + RiR×NOPAT) e (capex_total + ΔWC) → par d×RiR
  em base errada; RiR canônico < 0 com g > 0 (D&A > capex) → vetor não representável: migrar o
  par para base caixa, nunca ajustar uma metade só
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
  gp ≈ 0) → fluxo real a taxa nominal (Modigliani-Cohn); dupla entrega dos dois regimes — Fisher
  em `aplicacao.md` §2 (o `normaliza` avisa)
- Tela NTM vs base corrente → alvo deslocado em (1+g) | comparação com terceiros sem checar
  mid-year vs fim de ano
- Mudança ≥ 10% na base de capital em 12m (IPO, follow-on, recompra, baixa, M&A) → ROE/ROIC de
  LTM inválido: numerador de uma empresa, denominador de outra
- Evento de estrutura DATADO → `ponte` com as duas travas (Ku único; rebase se razão ≠ 1); ponte
  > 10% do valor → modele as fases; reversa/iso com evento datado → NUNCA monofásica sobre o alvo
  cheio: `iso --transicao ponte` (inversão bifásica exata) | `iso book` sem `--rent-book`
  conflaciona marginal×médio (o motor avisa)
- gp sem `--rf` → não ancorada (avisada); gp > rf nominal (ou > ~3% real) → excesso quantificado
  e tese da exceção por escrito | `--moeda` ausente → aviso | base nominal×real inconsistente →
  ROIC inflado, RiR subestimado, valor inflado (`aplicacao.md` §2)
- Segmentos com economia materialmente diferente → blended é erro sistemático (`aplicacao.md`
  §12) | premissas de validade violadas pelo caso (margens, D/E, caixa, RiR, payout constantes;
  crescimento só por novos investimentos) → citar quais

## Referências

- `references/aplicacao.md` — playbook de empresa real: pesquisa §1, regras travadas §2,
  convenção §3, cenários e confronto temporal §4, escrita e tradução §5 (a autoridade estrutural é o template acima), bloco de inputs §6, multi-driver §7, degrau §8, ponte §8b, financeiras §9, memória de
  cálculo §11, multi-segmento §12, jurisprudência (apêndice J). Leia SEMPRE antes de valuation
  real.
- `references/derivacao.md` — matemática, provas, as três convenções de TV §3, APV/recursão Ke_t
  (agora executável no comando `apv`) §5, limites, §8 teorema da classificação, §8b ponte de
  releveraging (derivação, prova do colapso, limite MM). Leia se a teoria for questionada ou
  houver degrau ou mudança de estrutura de capital.
- `scripts/testes.py` — validação independente: property tests, reconciliação DCF↔EVA e APV,
  boundaries. Rode se alterar o motor ou se um resultado parecer estranho.
- `references/paper-multiplos-justos-v3.md` — fundamentação teórica completa: catorze proposições (6.1–6.14)
  com status epistemológico declarado, três convenções de TV (§3.3), por que não há fade (§3.4),
  as duas camadas de consistência do custo de capital (§4), protocolo de validação (Ap. A),
  condições de falseamento (Ap. B) e caso trabalhado de ponta a ponta (Ap. C). Leia quando a
  teoria for questionada ou quando precisar defender uma escolha de convenção por escrito.

**Excel, quando gerar:** fonte Gadugi, azul = input hardcoded, preto = fórmula, verde = referência
cruzada, subtotais "(=)" em negrito, aba "Premissas" com as seis colunas. PT-BR, tom direto.

## Encerramento (fluxos 2 e 3, só com a cobertura completa)

**1. Captura de aprendizado — Claude faz, não pergunta:** regra/armadilha GENERALIZÁVEL que a
skill não prevê? Enuncie em 1–3 linhas despersonalizadas e diga em qual arquivo entraria (número
ou conclusão sobre a empresa analisada não conta); senão, "nada novo a incorporar nesta rodada".
**2. Oferta de aprofundamento** (ferramenta de input, seleção múltipla): auditoria mecânica
(re-executar do bloco de inputs; todo número rastreia a output ou fonte com data); contraditório
das duas premissas mais decisivas; 2–4 análises específicas ao caso (iso, reversa em nível,
convenção alternativa, CAP implícito, ponte de câmbio, PVGO, Excel); aplicar o aprendizado.
