# O relatório em HTML

Leia só depois de fechar a tese. Aqui está o ofício de escrever e montar o
arquivo, não o conteúdo (a régua está em `skills/er-analise/references/initiating-coverage.md`).

## O arquivo

- Um único `.html`, autocontido, que abre offline: CSS e JavaScript no próprio
  arquivo, nenhuma biblioteca externa, nenhuma chamada de rede, nenhuma fonte
  remota (use pilha de fontes do sistema).
- Responsivo e legível no celular. Tabela larga rola dentro do próprio bloco.
- Navegação que nasce do conteúdo: abas ou âncoras com os nomes que a análise
  pedir. Não existe conjunto padrão de abas.
- Se a skill `frontend-design` estiver disponível, leia-a antes de escrever o
  CSS. O relatório deve parecer um documento de research bem editado, não um
  painel de ferramenta.

## A escrita

- Títulos afirmam achados. "Alocação de capital: o registro é bom e a decisão
  de 2026 é ruim" ensina algo antes de o leitor ler o parágrafo. "Alocação de
  capital" não ensina.
- Conclusão primeiro, explicação depois, em todos os níveis: relatório,
  capítulo, parágrafo.
- Números dentro da frase, com período e unidade. Fonte por perto: uma linha
  de fonte ao fim do bloco ou uma citação curta entre parênteses. O registro
  completo de fontes, com links, fica no fim.
- Marque o estatuto das afirmações quando houver risco de confusão: fato,
  julgamento, hipótese. Uma etiqueta discreta resolve.
- Explique o porquê, não só o quê. Cada bloco responde "e daí?".
- Língua de mercado. Jargão interno de metodologia, nomes de comandos, códigos
  e versões ficam na memória técnica. Toda variável do valuation tem a função
  explicada na primeira vez que aparece.
- Densidade sem enchimento. O tamanho segue a complexidade da companhia: os
  bons relatórios desta casa variaram de três mil a vinte e três mil palavras.
- Limitações e ressalvas vão para o fim, salvo a que muda a conclusão.

## Tabelas e gráficos

- Tabela desenhada para o conteúdo ganha de gráfico genérico. Cinco números
  ficam melhor numa tabela. Use gráfico quando a forma importa: tendência
  longa, ciclo, composição, faixa de valor contra o preço.
- Gráfico em SVG inline ou em HTML e CSS simples. Todo gráfico tem: título que
  diz o que se deve enxergar, unidade, eixos legíveis sem sobreposição, barras
  partindo do zero, janela longa o bastante (um ciclo inteiro, se o ponto é o
  ciclo), anotação dos eventos que explicam a curva, e fonte.
- Não trunque eixo para dramatizar variação pequena. Não use gráfico com dois
  ou três pontos.
- Elementos úteis, quando couberem: faixa de indicadores no topo, cartões de
  debate (a tese do mercado, a sua leitura, o que resolve), tabela de decisões
  do management com leitura e teste, linha do tempo de catalisadores, quadro
  "precisa acontecer para o retorno ser excepcional" contra "o que leva à
  decepção", painel de monitoramento com níveis de alerta. São ideias, não
  lista de presença.

## O laboratório dentro do arquivo

Siga `laboratory.md`. No arquivo: as entradas agrupadas pelo
sentido econômico, as saídas em destaque, o recálculo imediato a cada edição,
nenhum estado quebrado (entrada inválida mostra mensagem clara, não "NaN"), e
os valores de preset idênticos aos que a prosa cita.

## Antes de entregar

- Abra o arquivo. Se houver navegador automatizado no ambiente, renderize e
  olhe capturas de tela de cada parte, em largura de desktop e de celular. Se
  não houver, revise o HTML e execute o JavaScript do laboratório em `node`
  com os presets.
- Confira que não há erro de JavaScript, recurso externo, caractere
  corrompido ou texto sem acento.
- Rode os testes de aceitação de `skills/er-analise/references/initiating-coverage.md`.

## Artefatos técnicos

Não duplique o `valuation-case.md` em uma segunda memória técnica obrigatória. Comandos do motor, derivação de premissas, outputs, divergências entre fontes e validação do laboratório ficam nos artefatos canônicos da análise. Crie nota técnica adicional apenas se ela reduzir perda de contexto real.
