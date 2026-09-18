# Disciplina de evidência da metodologia

## 1. Pesquisa (sempre — nunca números de memória, nunca herdados)

Buscar: último trimestre e último anual (receita, EBITDA ajustado e margem, depletion/D&A,
alíquota efetiva, lucro); guidance do ano e outlook plurianual (volumes!); preço atual,
market cap, nº de ações (e classes, se houver mais de uma); caixa, dívida, equity investments;
capital deployado nos últimos 2 anos (para RiR); folga de capacidade/capital regulatório; e o
SPOT ATUAL de TODOS os drivers exógenos, com data e fonte. Ordem de fontes: dado licenciado/
conector → press releases/filings da companhia → agregadores/web.

**Coleta adicional obrigatória (v9.15):**
- **Consenso**: receita e EPS/LL para o ano corrente, t+1 e t+2, com data e nº de analistas;
  price target médio e faixa. Fonte agregadora serve; registre a data (consenso pós-resultado
  difere do pré). Alimenta o confronto temporal da reversa (§4) e a seção Estimativas da entrega.
- **Margem estrutural**: margem operacional dos 2–3 anos pré-ciclo de investimento, quando houver
  ciclo declarado (alimenta o regime B do teorema da base coerente — SKILL.md, Gate 0).
- **Runway**: penetração do mercado endereçável e share, sempre que CAP > 10 for candidato.
- 2–3 leituras de sell-side/imprensa especializada sobre bull/bear case e competição (alimentam a
  seção Negócio & indústria e o teto de normalização de margem — competição pode tornar parte do
  "investimento" permanente).

**Não existe premissa herdada.** A skill não guarda casos e não reaproveita análise anterior.
Se o usuário fornecer um bloco de inputs de sessão passada, revalidar obrigatoriamente preço,
spot dos drivers, base de capital e existência de resultado novo — e declarar o que foi
revalidado.

**Série de três pontos para inputs de BALANÇO (obrigatória).** Capital de giro/receita, capital
fixo/receita, capital investido, ciclo de caixa em dias e capex/receita entram com **três
observações** — o trimestre corrente, o mesmo trimestre do ano anterior e o último fechamento
anual —, e a entrega declara qual foi adotada como centro e por quê. Razão econômica: a
demonstração de resultado é FLUXO de um período, mas o balanço é ESTOQUE medido num ponto do ciclo;
um único ponto de estoque numa cíclica carrega o ciclo inteiro sem produzir sintoma nenhum, e o
ponto mais recente é justamente o mais tentador de usar. **Amplitude > ~20% entre o maior e o menor
ponto da série ⟹ o input é hipótese, não medição:** o centro vai à sensibilidade obrigatória com as
três pontas precificadas. A escolha do ponto do ciclo é a **8ª escolha metodológica nomeada**, que
deixa de ser só "o ano de capex de estado estacionário" e passa a ser *o ponto do ciclo dos inputs
de capital — corrente × média da série × guidance de longo prazo*, com o par (d, RiR) re-derivado
pela conservação em CADA ramo.

**Checagem de vintage de capital (obrigatória).** Antes de usar qualquer ROE/ROIC de LTM ou TTM,
verifique se a base de capital mudou ≥ 10% nos últimos 12 meses: IPO, follow-on, recompra
relevante, baixa contábil, aquisição paga em ações. Se mudou, **o indicador de LTM é inválido** —
numerador de uma empresa, denominador de outra. Recalcule a rentabilidade sobre a base de capital
ATUAL, usando lucro anualizado do trimestre mais recente e/ou consenso, e declare qual usou.
