# Ficha de fatos (inputs_valuation.md) e contrato do bloco fatos (inputs.yaml)

Fonte: `docs/fontes/Analista Sênior de Ações.md`, Seção 6 (análise financeira,
as quatro perguntas) e Seção 9 (entregáveis factuais para o valuation). Esta
seção não é valuation: nenhum Ke, CAP, valor justo, upside ou sinal sai
daqui; ela produz a base que os pilares julgam e que o Modelador consome. O
schema canônico COMENTADO, com um exemplo real completo (meta, fatos e
premissas), é `skills/er-valuation/inputs_exemplo_vrsk.yaml`; consulte-o
sempre que o contrato abaixo parecer ambíguo.

## 6.1 Reconstrução histórica (5 a 10 anos, calculada em Python em uma única passada)

Receita e variação; EBITDA, EBIT, lucro e margens; LPA; OCF/CFI/CFF; FCF (e
FCFF quando fizer sentido); conversões (FCF/lucro, FCFF/EBITDA); capex total
e manutenção vs. expansão; WC/receita; dívida bruta e líquida, caixa, dívida
líquida/EBITDA, dívida/PL E dívida líquida/PL medidas (o DE e o NDE que o
engine consome), cobertura, custo médio, cronograma; patrimônio; alíquota
efetiva; share count básico e diluído; dividendos, recompras com preços,
SBC. ROIC reconstruído por você, ROE, e ROIIC em janelas de 3 a 5 anos (é o
ROIIC que revela se o crescimento recente criou valor; também alimenta a
evidência de renovação do moat do Pilar 6).

SÉRIE DE SPREAD por ano DA COMPANHIA CONSOLIDADA (ROIC menos o custo de
capital de referência): entregável de primeira classe, não subproduto;
alimenta a persistência realizada do Pilar 6 e `fatos.duracao.consolidada`.

SÉRIE DE MÚLTIPLOS históricos da própria companhia (P/E e, quando fizer
sentido ao modelo de negócio, EV/EBITDA), 5 a 10 anos, com mínimo, mediana e
máximo por métrica e a base contábil declarada (GAAP ou ADJUSTED, nunca
misturadas). Métricas núcleo na MESMA grade para a empresa e 3 a 5 pares,
INCLUINDO os múltiplos atuais de cada par (mesma base contábil, com data e
fonte). Rotule cada série FATO ou ESTIMATIVA.

As séries anuais de receita, lucro líquido e ROE, e a série anual de P/L (na
base contábil declarada), além de entrarem na ficha, são emitidas de forma
ESTRUTURADA no `inputs.yaml` (`fatos.series_historicas` e
`fatos.multiplos_historicos.pe.serie`) para alimentar os gráficos do
relatório final. É a mesma série já reconstruída aqui, apenas serializada;
sem nova pesquisa.

## Ficha (inputs_valuation.md), só fatos e estimativas rotuladas, com fonte por linha

LEDGER DE DOCUMENTOS primeiro (documento, período, data de publicação, URL, o
que foi extraído; ausências com a busca que as sustenta); identificação e
mercado com data; base histórica completa da Seção 6.1 (incluindo DE e NDE
medidos com o caixa explícito, a série de spread consolidada por ano e a
série de múltiplos históricos próprios com min/mediana/máx por métrica e
base contábil declarada); LPA TTM reportado e ajustado com a ponte completa;
share count e instrumentos dilutivos com termos; projeções em três
trajetórias (guidance e alíquota efetiva "limpa" ficam AQUI, como fatos da
ficha); base pro forma quando houver evento; DOSSIÊ DE DURAÇÃO DO MOAT
completo (ver `references/moat-duracao.md`); crescimento histórico e
guidance vs. entrega; consenso e targets (dado bruto); matéria-prima de
variant perception (consenso sell-side, narrativa de mercado com 2 a 3
fontes datadas, posicionamento observável); 3 a 5 pares na mesma grade COM
os múltiplos atuais de cada um; bloco das quatro respostas (cresce? é
rentável? é alavancada? há red flags?); flag de financeira (se sim, capital
regulatório, mínimo e folga).

## Bloco fatos do inputs.yaml (contrato v2 do engine)

Crie `<ns>/inputs.yaml` com os blocos `meta` e `fatos`, extraídos da ficha,
todo campo com a MESMA fonte já registrada.

`meta`: `ticker, nome, moeda, preco_atual, data_preco, fonte_preco, acoes_mi`
(diluídas).

`fatos`:
- `ledger` (resumido: doc, data_arquivamento, uso).
- `lpa_ajustado_fy`, `lpa_gaap_fy`.
- `divida_liquida_mi`, `divida_bruta_mi`.
- `de`, `nde` (dívida BRUTA/PL e dívida LÍQUIDA/PL MEDIDOS; (DE − NDE) =
  caixa/PL, e o "caixa" que a fórmula consome é o caixa LIVRE no sentido
  econômico do bracket — em negócios com float/ativos que lastreiam passivos
  (seguradoras), colete a discriminação caixa livre vs. restrito/colateral que
  o metodo.yaml (R1) tiver pedido, para o Modelador decidir o tratamento.
  REGRA R2: NUNCA registre 0.0 por lacuna de coleta — se a medição for
  genuinamente impossível (ex.: PL distorcido a ponto de o quociente não fazer
  sentido), NÃO preencha os campos e registre a impossibilidade na ficha; a
  exceção formal é do Modelador (premissas.excecao_de_nde, com motivo
  econômico e faixa alternativa — o engine calcula a sensibilidade e recusa
  exceção sem os dois).
- `ebitda_gaap_ttm_mi`, `ebitda_adj_ttm_mi`.
- `consenso {min, max, mediana, fonte}`.
- `multiplos_historicos {pe {min, mediana, max, janela, base, fonte, serie
  [{ano, pe}]} (série anual da própria companhia, mesma base contábil;
  desvio_padrao opcional); ev_ebitda {idem, quando fizer sentido}}`.
- `series_historicas [{ano, receita, lucro_liquido, roe}]` (roe como fração;
  receita e lucro_liquido na unidade da ficha).
- `pares [{nome, pe e/ou ev_ebitda (múltiplo ATUAL, mesma base contábil dos
  multiplos_historicos), fonte}]` (na dúvida sobre a métrica primária do
  Modelador, entregue as duas).
- `duracao {consolidada {persistencia_spread_anos, fonte}; segmentos
  [{nome, peso_lucro, persistencia_anos, notas}] (obrigatório em grupos
  diversificados); fontes_estruturais [{nome, evidencia}];
  renovacao_moat {evidencia} (omita se não houver evidência); vetores_erosao
  [{nome, status, materialidade, probabilidade, horizonte_anos}]; precedentes
  [{nome, anos}]}`. Ver `references/moat-duracao.md`.

SÉRIES PARA OS GRÁFICOS: `series_historicas` alimenta o gráfico de receita e
lucro líquido (barras) com ROE (linha); `multiplos_historicos.pe.serie`
alimenta o gráfico de P/L histórico com mediana e mediana ± 1 desvio-padrão.
Ausência dessas séries não bloqueia o pipeline (o gráfico degrada com nota
automática); declare a lacuna na ficha.

CAMPOS EXTINTOS do contrato v2 (não os crie): `lpa_guidance_prox_fy`,
`receita_fy_mi`, `margem_ebit_fy`, `aliquota_efetiva` como campo solto
(guidance e alíquota ficam na ficha); `persistencia_realizada_anos` de
produto isolado (substituído por `duracao.consolidada`/`duracao.segmentos`);
`pricing_power_serie`, `kill_criteria_proximo`, `dominancia_decadas`,
`roiic_alto_recente` como campos soltos (a evidência entra em
`fontes_estruturais` ou `renovacao_moat`; kill criteria seguem no dossiê e na
ficha, não são campo do `inputs.yaml`).

Regras: NUNCA preencha o bloco `premissas` (é do Modelador); nunca coloque
valor GAAP em campo ADJUSTED ou vice-versa (mistura de bases é um erro real
já pego em auditoria); estimativa sua leva comentário ESTIMATIVA com o
método em uma linha.
