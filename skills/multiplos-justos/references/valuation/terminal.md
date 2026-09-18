# Convenção terminal

## 3. Convenção de TV — a decisão que mais move o valor

**A escolha é pela DURAÇÃO ECONÔMICA do claim, não pelo rótulo do setor nem pela conveniência do
número, e é o Gate 1 do SKILL.md.** O motor exige `--tv` explícito e não tem default. São três
convenções (ver `derivacao.md` §3); declare a escolhida E a hipótese que ela carrega na entrega.
- **`book`** (ex-`ic`): o NOPAT inteiro colapsa para W×IC — TV ancorado no capital investido
  MENSURADO; ler como fim de TODA renda econômica exige book confiável (classificação do §1) e é
  hipótese mais dura que a exaustão no capital incremental. O colapso ocorre no ano n+1 e o TV é o
  capital investido. Adequada quando o book é âncora crível de saída (price-taker de commodity,
  regulado com base de remuneração). **Enterprise:** `--roic-book` é a média **inicial/forward** do
  estoque, temporalmente alinhada a NOPAT₁: `IC₀ = NOPAT₁/ROIC_book`. Se a fonte for ROIC trailing,
  reconcilie-a para essa base antes de usar. Quando marginal ≠ médio, o TV é o IC **ACUMULADO**:
  parte de IC₀ e recebe o capital novo ao ROIC marginal; o retorno médio no ano n é output, não
  parâmetro congelado. **Equity [v9.30]:** `--roe-book` acumula o patrimônio por
  clean surplus. A forma fechada de E_n coincide com a do firm, mas o valuation `book` é
  **Div + E_n**: `Div_t = LL_t − ΔE_t = LL_t(1−g/ROE_marg)`. O termo `+Δcaixa` do módulo FCFE
  não entra nesta convenção porque o caixa retido já está em E_n; somá-lo de novo é dupla contagem.
  Assim, Caixa/E é neutro na `book` e excess cash/rendimento de caixa deve ser tratado separadamente.
- **`convergencia`**: só o capital NOVO deixa de criar valor (RONIC = W); o NOPAT existente é
  preservado; TV = NOPAT/W. Exaustão da vantagem NO CAPITAL INCREMENTAL — as rendas dos ativos
  existentes não são eliminadas (o desaparecimento total é a `book`). Não referencia o book
  nem gp. Na dúvida entre "a vantagem acaba" e "o negócio vira medíocre nos projetos novos",
  esta é a convenção — a `book` assume bem mais que isso.
- **`gordon`** (ex-`spread`): ROIC_TV e gp livres. Claims de LONGA DURAÇÃO (royalty, streaming,
  rede, marca dominante) justificados pela duração — um contrato com termo de 15 anos é horizonte
  explícito longo, não perpetuidade; e um regime declarado de ROIC_TV < W é legítimo para
  destruição persistente. **Rentabilidade terminal (`--roic-tv`/`--roe-tv`) = a MARGINAL
  TERMINAL (RONIC/ROIIC)**: gp/ROIC_TV é o RiR do capital NOVO que sustenta gp — é o retorno
  incremental que a álgebra exige (v9.8, C-01). NÃO perpetue o marginal do EXPLÍCITO (regra do
  degrau: a rentabilidade terminal não acompanha, paper §6.10); o blended do portfólio é proxy
  ADMISSÍVEL só sob hipótese DECLARADA de estado estacionário com médio e marginal convergidos —
  declare a hipótese e a direção do erro: blended > RONIC real ⟹ RiR subestimado ⟹ TV
  SUPERESTIMADO (caso maduro comum); inverte se RONIC > blended. No lado equity com caixa ≠ 0, declare a política de caixa no terminal:
  `--politica-tv continua` (default, FCFE canônico — a proporção de caixa segue na perpetuidade)
  ou `encerra` (a política morre no ano n); a escolha move 2–6% do P/L e sai no diagnóstico.
- **Se rentabilidade marginal < custo de capital, o caminho depende de haver book separado.** SEM
  book separado, a `book` conflaciona médio×marginal e pode premiar o destruidor de valor (o TV cresce
  quando a variável única de retorno cai): separe os papéis ou use `gordon` com rentabilidade
  terminal ABAIXO do custo e declare o spread negativo persistente. **Enterprise, com
  `--roic-book`:** o TV parte de IC₀ e acumula o capital novo ao marginal; com g>0, elevar apenas o
  marginal eleva o valor. A raiz é CONDICIONADA à tese declarada de saída pelo capital investido
  (turnaround, capex regulatório, reconstrução operacional, liquidação). Isso não torna toda reversa
  unívoca: o gradiente em g tem sinal do spread na **base forward**, mas a base corrente pode ter
  máximo interior e duas raízes. **Equity, com `--roe-book`:** o patrimônio parte da média
  inicial e acumula o lucro retido ao marginal. Na `book`, Caixa/E não altera o valor por si só;
  o fluxo é dividendo e o terminal é E_n. Se o próprio book estiver abaixo do custo, some o
  sub-alerta de RECUPERAÇÃO.

**Teste do teto — procedimento, não impressão.**
```
1. rev --resolver cap --alvo <múltiplo de mercado> --tv book ...
2. Saiu "incompatível com estas premissas sob esta convenção"?
   NÃO  -> a `book` reconcilia o preço; siga com ela e reporte o CAP implícito (interpolado,
           condicional às demais premissas).
   SIM  -> ANTES de trocar de convenção, cheque o Gate de nível (§7 e §8): o problema pode ser
           nível defasado ou degrau não modelado, não a convenção. Inverter essa ordem é o erro
           mais caro da sequência.
3. Nível descartado e ainda incompatível -> a franquia está sendo percebida como mais longa que
   a convenção. Rode `convergencia` (o meio-termo: preserva o NOPAT, mata o valor do capital
   novo) e, se o claim justificar por DURAÇÃO, `gordon` com:
     rentabilidade terminal = o RONIC/ROIIC TERMINAL — o retorno do capital novo que sustenta
       gp (é ele que entra em gp/ROIC_TV). NÃO o marginal corrente do explícito (perpetuá-lo
       superestima o TV — quanto maior o R, menor o RiR imputado); o blended entra só como proxy
       declarada de convergência médio↔marginal no steady state, com a direção do erro anotada.
     gp = 2–4%, pela regra de §2, sempre < custo de capital.
4. Rode as convenções candidatas e mostre os gaps: cada gap é a parte do valor que depende da
   hipótese terminal correspondente (book→convergencia: preservação do NOPAT existente;
   convergencia→gordon: perpetuidade do spread no capital novo).
```

**Antes de qualquer reversa contra múltiplo de tela — trave a BASE (D2).** Múltiplo de tela vem
em TTM (corrente) ou NTM (forward), e as duas diferem por (1+g): a 12% de crescimento, confrontar
um NTM contra a base corrente do motor injeta 12% de erro no alvo, que volta como premissa
implícita falsa e com cara de precisão. Registre a base da fonte com data, e rode
`rev --alvo-base forward` quando a tela for NTM. O motor ecoa a base usada no output; se a fonte
não declara a base, isso é lacuna de dado — trate como tal, não como detalhe.

**Regra transferível:** um múltiplo de tela incompatível na variável economicamente relevante é
evidência sobre a convenção (ou sobre o nível), não veredicto sobre o preço. Quem defende múltiplo
alto por rentabilidade alta está, sem saber, assumindo claim de longa duração — e é essa premissa
(a duração) que precisa ser defendida, não o múltiplo. Simetricamente: o teto famoso ("nem CAP
longo alcança o múltiplo") é propriedade da `book`; sob `convergencia` o teto sobe com o CAP e a
afirmação não se transfere.
