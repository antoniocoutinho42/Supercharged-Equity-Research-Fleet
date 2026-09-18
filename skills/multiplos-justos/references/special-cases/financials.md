# Financeiras

## 9. Financeiras — sub-playbook

Bancos, seguradoras e financeiras **não têm leitura de EV/EBITDA nem de capital investido**:
dívida é matéria-prima, não estrutura de capital. Rode só o lado equity.

- **Métrica-manchete: P/VP = P/L × ROE.** É a forma natural do setor e reconcilia exatamente com o
  motor. A ponte de preço não tem dívida: `equity = múltiplo × lucro`; `preço = equity ÷ ações`
  (÷ câmbio, se listada fora).
- **caixa/E = 0** (`--gde 0 --nde 0`): caixa é ativo operacional, não excedente devolvível. A
  neutralidade ROE = Ke vale exatamente nesse caso (com marginal e book iguais ao Ke — sob
  `book`, marginal = Ke com book ≠ Ke não é neutro).
- **Caixa/E em HÍBRIDA financeira (v9.16, origem J8/MELI).** É a alavanca esquecida mais cara:
  no caso-origem, o caixa bruto era 86% do PL e o tratamento movia 45% do valor sem estar na
  lista de escolhas. Regra: com **dívida líquida positiva OU funding de carteira relevante**,
  caixa/E = 0 é a escolha central obrigatória — o caixa é liquidez operacional e regulatória do
  braço financeiro. O tratamento bruto entra como a 7ª escolha metodológica nomeada na tabela de
  sensibilidade (SKILL.md, item 4), nunca como caso-base. O critério é a DEVOLVIBILIDADE ao
  acionista, não a presença no balanço.
- **Vintage do book é crítico.** Evento de capital nos últimos 12 meses invalida o ROE de LTM
  (ver §1). Recalcule sobre a base atual.
- **Qualidade do patrimônio.** Crédito tributário relevante no PL muda a leitura de P/VP (sobre
  book tangível o múltiplo é maior e a rentabilidade também) — o P/L é imune, o P/VP não. Reporte
  os dois quando o CTA for material.
- **Capacidade é restrição regulatória**, não física: índice de capital acima do piso é degrau
  disponível (§8). Mas a restrição efetiva costuma ser **funding**, não capital — teste.
- **Cessão com retenção de risco fica no balanço** e consome capital; só venda verdadeira (sem
  coobrigação) libera — migrar de regime é mudança de modelo, não degrau; trate fora do framework.
- **Hedge muda a elasticidade:** carteira pré convertida em flutuante trava o spread — verifique o
  hedge antes de atribuir elasticidade ao driver de juros.
- **Crescimento é limitado por capital:** g sustentável ≤ rentabilidade × retenção, e a retenção
  tem piso legal/estatutário de payout. Se g proposto exceder isso, ou há emissão implícita ou o
  crescimento recente não é sustentável — reporte.
