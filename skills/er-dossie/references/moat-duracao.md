# Dossiê de duração do moat (Pilar 6)

Fonte: `docs/fontes/Analista Sênior de Ações.md`, Seção 5, bloco "DOSSIÊ DE
DURAÇÃO DO MOAT" dentro do Pilar 6. Porte VERBATIM (é o insumo do julgamento
de CAP do Modelador; cada item vale dinheiro e exige fonte). O objeto medido
é a COMPANHIA CONSOLIDADA, nunca um produto isolado. Fronteira: você entrega
evidência, ponderação e taxa-base; o CAP, a confiança nele e a alocação dos
riscos são decisão do Modelador.

Obrigatório, com os 7 itens abaixo:

1. **PERSISTÊNCIA REALIZADA DA COMPANHIA CONSOLIDADA como NÚMERO**: quantos
   anos, contados por você na SÉRIE DE SPREAD da Seção 6.1 (ROIC, ou ROE
   para financeiras, acima de um custo de capital de referência declarado),
   a companhia JÁ sustentou spread positivo; liste os anos de exceção e diga
   se a série é contínua ou interrompida. A série consolidada é
   PRÉ-REQUISITO deste dossiê: se não puder reconstruí-la (acesso a
   filings), declare a impossibilidade com a busca que a sustenta, entregue
   o melhor proxy disponível (por segmento, pré-listagem, fonte secundária
   verificada) e rotule a limitação. NUNCA entregue a persistência de um
   produto no lugar da consolidada sem rotular exatamente isso.
2. **DECOMPOSIÇÃO POR SEGMENTOS** (obrigatória em grupos diversificados):
   para cada segmento relevante, o peso no lucro normalizado (ou em
   caixa/capital investido, declarando a base de ponderação) e a
   persistência/qualidade da vantagem daquele segmento, com fonte. Um ativo
   forte não representa o grupo; a ponderação é a matéria-prima que impede
   isso.
3. **FONTES ESTRUTURAIS** do moat, cada uma com evidência numérica e fonte:
   efeito de rede ou padrão de indústria (adoção, share de especificação),
   switching contratual (prazos médios, renovação), designação ou
   embutimento regulatório, dados proprietários contributivos, marca com
   pricing power demonstrado em série de preços, escala com vantagem de
   custo mensurada.
4. **RENOVAÇÃO DO MOAT**: evidência de capacidade recorrente de renovar a
   vantagem (pipeline e lançamentos com resultado, reinvestimento com ROIIC
   alto em janelas de 3 a 5 anos, aquisições disciplinadas com track record
   de integração, extensões de produto que ampliaram o mercado), cada uma
   com número e fonte. Ausência de evidência é declarada, não presumida em
   nenhuma direção.
5. **VETORES DE EROSÃO ativos**, cada um com QUATRO atributos: status
   (RESOLVIDO COM EVIDÊNCIA | ABERTO | AGRAVANDO), materialidade (alta/
   média/baixa, com o racional em meia linha), probabilidade (alta/média/
   baixa) e horizonte em anos. Inclua a lente IA nas três dimensões
   (substituição do produto, compressão de margem por entrantes,
   produtividade). Você entrega a avaliação como ESTIMATIVA; a alocação do
   efeito no valuation (bear, probabilidade, spread do CAP) é decisão do
   Modelador.
6. **TAXA-BASE HONESTA**: precedentes NOMEADOS de setores análogos com anos
   observados de spread sustentado (15/20/25 ou mais), o N de comparáveis
   identificados e o viés de sobrevivência declarado.
7. Trajetória de participação de mercado em janelas longas (décadas quando
   disponível) e vidas de patentes/ciclos regulatórios relevantes.

## Contrato com o `inputs.yaml` (bloco `fatos.duracao`)

Este dossiê é a fonte dos campos `fatos.duracao.consolidada` (persistência em
anos + fonte), `fatos.duracao.segmentos` (peso no lucro + persistência +
notas, obrigatório em grupos diversificados), `fatos.duracao.fontes_estruturais`
(nome + evidência), `fatos.duracao.renovacao_moat` (evidência; omita o bloco
se não houver evidência, declarando a ausência na ficha) e
`fatos.duracao.vetores_erosao` (nome, status, materialidade, probabilidade,
horizonte_anos), além de `fatos.duracao.precedentes` (nome + anos). Ver
`references/ficha-e-fatos.md` para o contrato completo do bloco `fatos` e o
schema canônico comentado em `skills/er-valuation/inputs_exemplo_vrsk.yaml`.
Campo de evidência (`evidencia`, `renovacao_moat`) só existe com número e
fonte dentro dele; texto negativo ("não calculado", "não confirmado") NUNCA
ocupa campo de evidência, vai para as limitações declaradas da ficha;
segmento sem peso não pondera, declare a lacuna.
