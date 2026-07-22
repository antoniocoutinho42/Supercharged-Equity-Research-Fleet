# Impacto do upgrade v2 no caso TFCO4 — antes/depois por chave

**O que este documento é.** O exercício operacional completo da FASE B (B4, condições 1 e 2 da
aprovação de 2026-07-21): o caso TFCO4 re-executado no engine v3.2.0 com TODOS os blocos novos,
com a variação de cada âncora **decomposta por causa**. Todos os números vêm de
`resultados.json` de runs reais (fixture `tests/fixtures/tfco4/inputs_b4_completo.yaml`,
gerada por script determinístico commitado) e estão TRAVADOS em `tests/test_b4_impacto.py` —
se qualquer número desta página divergir do engine, a suíte fica vermelha.
**Sem recomendação nova de compra/venda** (regra do escopo). Proveniência: o namespace original
da análise não existe nesta máquina; a base é a reconstrução do `relatorio_final_1.pdf`
validada no B0 com **delta zero em todas as chaves publicadas** (preços, ladder, elasticidades,
matrizes 54/54 células).

## 1. Regressão: o que NÃO mudou

Os inputs originais (contrato antigo), rodados no engine novo, reproduzem TODAS as chaves
antigas: `economico.central_ponderado` **8,34**; `sinais.premio_sobre_econ_central_pct`
**79,7%**; `hurdle.cenarios.ponderado` **9,01**; `reverse.cap_implicito_econ_base` **42,8631**;
gate **SUMARIA**. O único acréscimo automático é `sensibilidade_phi` (aditivo). Critério de
regressão aprovado: chaves idênticas exceto `engine.{versao,gerado_em}`.

## 2. Antes/depois por chave (modo completo)

| Chave | Antes (v3.0.0) | Depois (v3.2.0) | Leitura |
|---|---|---|---|
| `economico.central_ponderado` | 8,34 | 8,34 | intacto |
| `ebit_justo.ponderado_preco` | — | **8,15** | âncora operacional NOVA, rota independente |
| `ebit_justo.paridade.delta_pct` | — | **−2,3% (CONVERGE)** | as duas âncoras se confirmam |
| `ebit_justo.reverse` | — | alvo **15,58x** EV/NOPAT; ROIC implícito **inalcançável**; CAP op **33,9a**; WACC implícito **6,2%** | o preço não fecha por rentabilidade |
| `central_neutro.premio_econ_pct` | — | **41,7%** (gate → **PADRÃO**) | R2 respondida |
| `validacao_multiplos.implicitos` | — | 20x hist ⇒ CAP **74,3a** OU g **33,6%** OU Ke **4,1%**; pares 5,24x ⇒ CAP **1,9a** OU Ke **21,0%** | R3 respondida |
| `ke_dossier.grade_ke` | — | 11%→**10,60** … 15%→**7,73** (prêmio +41,4%…+93,9%) | R4 respondida |
| `sensibilidade_phi` | — | φ=0,25→prêmio 68,8%; φ=0,5→59,3%; φ=1→**42,9%** | H11 quantificada |
| `fatos_reformulado.gates_aplicabilidade` | — | **EQUITY_OK** (flag: alavancagem cruza sinal na janela) | âncora patrimonial validada |
| `sinais.economico` / `entrada` | SOBREAVALIADO / NÃO ACIONÁVEL | idem em TODAS as variantes | **nenhuma variante vira o sinal** |

## 3. A âncora operacional e a paridade (o achado central)

A âncora operacional foi construída com dados INDEPENDENTES da âncora patrimonial: NOPAT FY2025
reconstruído (R$154,8mi), cenários margem×giro ancorados na série reformulada real do próprio
workbook de cobertura (2024 medido: 15,3% × 1,679x = ROIC 25,6%), WACC 13,4% (o do modelo de
cobertura, recebido como premissa), bridge = dívida líquida −R$115,2mi (IFRS-16 puro).

Resultado: **8,15 por ação vs 8,34 da âncora patrimonial — delta de −2,3%, dentro do limiar.**
Duas rotas com bases, taxas e rentabilidades diferentes chegam ao mesmo lugar; o preço de
mercado (14,99) fica ~80% acima de AMBAS. A leitura reversa operacional reforça: o preço embute
15,58x o resultado operacional líquido — **nenhum nível de rentabilidade** alcança esse múltiplo
com duração e crescimento do caso base (ROIC implícito sem raiz); seriam necessários **33,9
anos** de vantagem ou um custo de capital de **6,2%**.

## 4. Decomposição por causa (condição 2)

### (i) Alavancas intencionais — LPA / CAP / Ke / φ

| Alavanca movida sozinha (caso base → neutro) | Efeito no prêmio de 79,7% |
|---|---|
| Base de lucro 0,95 → 1,05 | **−17,1 p.p.** |
| CAP base 12 → 13 anos | **−2,9 p.p.** |
| Ke central 14% → 12,5% | **−19,9 p.p.** |
| Soma dos isolados | −39,9 p.p. |
| Conjunto (`central_neutro`) | −38,0 p.p. → **41,7%** (interação +1,9 p.p., sub-aditiva) |
| Spread terminal φ=0→0,25 / 0,5 / 1,0 | prêmio → 68,8% / 59,3% / **42,9%** (CAP equivalente 13,8 / 15,6 / 19,4 anos) |

Ke e base de lucro dominam; CAP marginal; e mesmo com spread terminal INTEGRAL perpétuo (φ=1)
o prêmio segue >40%. A consequência processual (R2): sob o caso neutro o gate degrada de
SUMÁRIA para **PADRÃO** — o empilhamento conservador é o que define o tratamento do caso, e
agora isso é auditável por chave.

### (ii) ROE derivado pela ponte em vez de input livre

A série reformulada mede ROE pela ponte (≡ direto) de **25,48%** em 2024 — acima do input livre
do caso base (22%). Substituindo só o ROE base pelo medido: central 8,34 → **8,40** (+0,7%);
prêmio 79,7% → **78,5%** (−1,2 p.p.). **Quase neutro** — coerente com a elasticidade publicada
(+1 p.p. de ROE ≈ +0,04/ação com lucro fixo): o input livre de ROE não era fonte relevante de
conservadorismo.

### (iii) Base de lucro

Com o LPA ajustado da companhia (1,12): central 9,83; prêmios **52,5%** (econ) e **41,1%**
(hurdle) — e a paridade contra a âncora operacional (que usa NOPAT reportado, sem add-backs)
**reabre exatamente o wedge: −17,1%, DIVERGE**. É o teste independente dos ajustes de ~R$29mi:
a divergência de paridade isola a escolha da base de lucro, separada de qualquer outra premissa
(razão medida no B0: 1,12/0,95 = 1,1789).

## 5. Série reformulada, gates e diagnóstico

Série 2020–2024 extraída do próprio `T&F_CG_3Q24.xlsm` (invariantes CE≡NOA e ponte≡direto
verificados na carga) + FY2025 reconstruído do PDF. Gates de aplicabilidade: **âncora
patrimonial aplicável** (patrimônio positivo em toda a janela; mediana E/NOA 0,89 ≫ 0,30; lucro
recorrente positivo), com uma ressalva de diagnóstico (alavancagem cruza de sinal em 2021 —
net cash transitório; limiares provisórios, calibrados em três casos). Diagnóstico em janela
acumulada: retorno sobre capital incremental **28,0%** com reinvestimento acumulado de **75,7%**
do resultado operacional — a fase 2020-2025 foi de expansão intensiva de capital; o RiR
terminal implícito do caso operacional base é 47% (g/ROIC), consistente com a tese de
crescimento franqueado ficando "mais barato" à frente.

**Lacunas rotuladas do FY2025 (diligência para a próxima atualização com DFP primário):**
`nie_pos_imposto` FY2025 é ESTIMATIVA (−12,5mi, escala de 2024) e `noa_medio` FY2025 vem da
identidade CE≡NOA (não medido de forma independente); PL 588,4mi, ND 115,2mi, receita 1.046mi e
NI 142,3mi vêm do PDF (p.3-4).

## 6. O que o upgrade responde das críticas

R2 (empilhamento): `central_neutro` + decomposição — seção 4(i). R3 (âncora externa): a tabela
de implícitos converte "20x histórico" e "5,24x dos pares" em premissas exigidas — o histórico
20x só se justifica com CAP de 74 anos, g de 33,6% a.a. ou Ke de 4,1%; a mediana dos pares
implica CAP de ~2 anos ou Ke de 21%. R4 (Ke): dossiê com as duas rotas na mesa (paridade-US
14,56% do próprio modelo de cobertura; build local ~19% calculado e rejeitado), prêmio de
tamanho explícito (zero, com critério) e grade — Ke segue a maior alavanca isolada. R5 (CAP):
banda estrutural não muda sinal nem gate (B0); a reforma real é processual (confiança da banda
separada + ônus de encurtar), no `cap_check` v2.1.

**Conclusão do exercício (sem recomendação nova):** com metodologia mais forte, o sinal
econômico do caso TFCO4 não muda em nenhuma variante testada — o que muda é a PROFUNDIDADE
processual exigida (caso neutro → PADRÃO) e a qualidade da fundamentação: cada prêmio agora tem
dono, decomposto por causa e travado em teste.
