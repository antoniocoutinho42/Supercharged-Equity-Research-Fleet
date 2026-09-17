---
name: er-evidencia
description: >-
  USE QUANDO pesquisar, registrar ou revisar a evidência de uma análise do
  fleet v4: escolher a fonte mais autoritativa para um claim, escrever
  registros e lacunas no contrato `ledger/1`, declarar conflito, contraprova e
  reconciliação, classificar lacuna MATERIAL ou NÃO-MATERIAL, tratar consenso
  ausente, preço e data-base, separar documento fornecido entre evidência e
  quarentena, registrar a resposta do usuário — ou despachar o agente
  `pesquisa-evidencia` com um mandato. É a doutrina de pesquisa e
  proveniência, agnóstica de fonte. NÃO use para calibrar premissa, montar o
  caso ou rodar o valuation (`er-valuation`), validar a entrega ou compor o
  relatório (`er-relatorio`, cujo builder é quem valida o ledger), conduzir a
  análise (`er-analise`) nem como fonte de metodologia
  (`er-multiplos-justos`).
---

# er-evidencia — doutrina de pesquisa e proveniência

Esta skill diz como se encontra e se registra evidência numa análise do fleet v4. É agnóstica
de fonte e dona de quatro coisas (§3.2 de `docs/desenho-arquitetura-v4.md`): o schema do ledger,
a hierarquia de fontes por claim, a reconciliação e a classificação de lacunas.

A separação que ela protege é a da §3.3: **Pesquisa & Evidência encontra; o Analista interpreta e
calibra.** Quem pesquisa é o agente `pesquisa-evidencia` (`agents/pesquisa-evidencia.md`) — um tipo
só, instanciado N vezes com mandatos distintos — e também o Analista, que pesquisa livremente para
preencher lacunas, testar hipóteses e buscar evidência contrária. A doutrina vale para os dois.

**O schema é dado.** O contrato `ledger/1` mora em `skills/er-evidencia/assets/contrato_ledger.json`:
`niveis` declara, por nível, as chaves `obrigatorias` e `opcionais`; `vocabularios` declara as listas
fechadas, algumas com flags. Esta skill explica o que cada campo e cada flag significam; as listas,
só o contrato as tem. Leia o contrato antes do primeiro registro, nunca de memória.

**A validação é do builder.** Não há validador de ledger aqui, e duplicá-lo criaria uma segunda
regra que diverge da primeira. O builder do relatório lê o contrato e valida a entrega: a forma é
recusa com código 1 (`skills/er-relatorio/scripts/entrega.py`, nomeando o campo) e o conteúdo é QC
(`skills/er-relatorio/scripts/qc.py`). Os tipos que o contrato não declara — data de acesso em
AAAA-MM-DD, valor número ou nulo — estão na tabela do ledger de `skills/er-relatorio/SKILL.md`
("O ledger, o consenso e o confronto"); o nível de cada código, na tabela de QC e em "Cobertura da
§11".

**Exemplo completo e executável:** `tests/fixtures/analises/SINT3/firm_escolha_driver/ledger.json`,
o ledger de uma companhia fictícia que passa no builder sem achado — contas declaradas,
contraprovas, consenso, drivers e uma lacuna.

## O princípio da fonte (§6.1)

Para cada claim, **a fonte mais autoritativa e mais próxima do fato específico que está sendo
provado**. Não existe hierarquia universal: a mesma fonte vence um claim e perde outro.

| Claim | Fonte que tende a vencer | Por quê |
|---|---|---|
| Receita histórica | o filing da companhia | é o registro primário do fato |
| Guidance | a companhia, pelo RI | só ela emite a própria orientação |
| Market share | research setorial especializado, que pode superar o filing | mede o mercado inteiro; o filing vê a companhia |
| Tamanho de mercado | fonte setorial independente, que pode superar a companhia | a companhia não é neutra sobre o próprio mercado |
| Ação de concorrente | o filing do concorrente | é o registro primário daquele fato |
| Expectativa de mercado | consenso de provedor | o fato é a expectativa agregada, e o provedor a mede |

**Fontes admissíveis:** filings, RI, releases, transcripts, apresentações, reguladores, APIs e
conectores MCP (OpenBB, SEC, provedores de mercado), industry reports, fontes governamentais,
imprensa especializada, web e documentos fornecidos pelo usuário. **Nenhuma é obrigatória; nenhuma
é exclusiva.** Um conector indisponível não é lacuna quando outra fonte admissível prova o mesmo
fato. O código de cada classe, para `fonte.classe`, está em `vocabularios.classes_de_fonte`.

**A justificativa é do claim.** `justificativa_da_fonte` diz por que esta fonte é a mais
autoritativa **para este claim** — a relação dela com o fato: registro primário, emissora da
orientação, medidora do mercado —, nunca um adjetivo genérico como "fonte confiável".

## O contrato por registro (§6.2)

O ledger tem `versao_contrato` (o literal do contrato), `registros` e `lacunas`. Qual chave é
obrigatória em cada nível, o contrato diz. O que cada uma declara:

| Campo | O que declara |
|---|---|
| `id` | identificador único na execução; é por ele que `insumos`, `conflito`, `contraprova_de`, o consenso da Tese e os datasets dos gráficos citam o registro |
| `claim` | o fato específico que o número prova, com a definição quando ela importa ("EBITDA ajustado pela companhia"). Registros do mesmo fato usam **o mesmo texto** de `claim` e de `periodo`: o builder agrupa fontes por igualdade exata dos dois para achar conflito — o mesmo fato escrito de dois jeitos esconde o conflito, e duas definições com o mesmo texto inventam um |
| `fonte` | `identidade`: quem **produziu** o número (a companhia, o regulador, o provedor que calcula a regressão), nunca o canal por onde ele chegou; `classe`: o tipo de fonte pelo qual ele chegou. Um agregador que republica o número do filing tem a identidade da companhia — e o builder só conta como contraprova outra `identidade` |
| `localizador` | onde outra pessoa acha o mesmo número: `tipo` (de `vocabularios.tipos_de_localizador`), `valor` (o endereço; o documento com página, nota ou tabela; a rota do endpoint) e `parametros` (os argumentos da chamada, inclusive o provedor por onde ela passou) |
| `data_acesso` | o dia em que **esta execução** acessou a fonte |
| `periodo` | o que o número cobre: exercício, trimestre, janela, ou a data do preço |
| `moeda` | a moeda do número, ou nulo quando ele não tem (razão, pontos percentuais) |
| `unidade` | unidade e escala como a fonte as dá ("R$ milhões", "pp", "R$ por ação") |
| `estatuto` | a relação do número com o fato (as flags abaixo) |
| `valor` | o número, na unidade declarada; nulo quando o claim não é um número só — a série de um dataset de gráfico, ou um fato qualitativo |
| `justificativa_da_fonte` | por que esta fonte vence para este claim (acima) |
| `formula` | a conta, legível, quando o estatuto a exige |
| `insumos` | os ids dos registros que entraram na conta |
| `usado_em`, `reconciliacao`, `conflito`, `contraprova_de` | a ligação do número com o valuation (abaixo) |

Evidência qualitativa — um anúncio, uma fala da administração num transcript, a ação de um
concorrente — também é registro, com a mesma proveniência: o `claim` diz o fato, o `periodo` a data
dele, `valor` e `moeda` são nulos e a `unidade` diz que não há número ("qualitativo").

A lacuna tem `id`, `descricao` (o que falta e onde se procurou), `materialidade` e `tratamento` (o
que a análise faz sem o dado: proxy declarado, sensibilidade, limitação). **A `descricao` e o
`tratamento` são prosa auditável da Tese:** nenhum dígito fora de placeholder — ano e trimestre
inclusive —, ou o builder recusa com `numero_sem_proveniencia`; número livre legítimo vai em
`{{livre:...}}`.

**As flags decidem; o nome nunca.** As regras seguem as flags que o contrato declara em cada entrada:

- **`vocabularios.estatutos`** — cada estatuto declara duas flags.
  - `exige_formula`: verdadeira, o registro traz `formula` e só ele pode trazer `insumos`; falsa, os
    dois são recusados. Número calculado sem a conta declarada não tem proveniência.
  - `e_estimativa`: verdadeira, o número não é observação do fato, é estimativa — da própria fonte
    ou do Analista; o agente não estima, registra a estimativa que acha. Quando um registro assim
    sustenta insumo do caso, direto ou pelos `insumos` de um registro que sustenta, o builder o
    declara (`insumo_estimado`). Estimativa nunca se disfarça de observação para apagar o aviso.
  - Escolha o estatuto pela relação do número com o claim: lido na fonte como ela o publica,
    derivado por conta declarada de outros registros, ou estimado. O consenso é observação: o
    claim é "o consenso de X para t+1", e o provedor o publica.
- **`vocabularios.materialidades`** — cada materialidade declara `exige_disclosure`: verdadeira, a
  lacuna sai como aviso obrigatório na Tese (`lacuna_material`); falsa, fica declarada na aba
  Evidência, sem aviso. A regra de classificação está em "As regras".
- **`vocabularios.ancoras_do_consenso`** — o código da âncora que entra no lugar do consenso
  ausente.

**Quem calcula o quê.** Quem pesquisa só faz conta mecânica sobre números registrados — somar
trimestres, converter escala, converter moeda por uma taxa também registrada, a média de uma janela
que o mandato fixou — e a declara em `formula` e `insumos`. Normalizar, excluir não recorrente ou
escolher a janela que representa o ciclo é julgamento: é do Analista, que registra a conta do mesmo
jeito.

## As regras (§6.3)

**Conflito nunca é silenciado.** Duas fontes que dão números diferentes para o mesmo `claim` e o
mesmo `periodo` ficam as duas no ledger, e cada registro vencido declara `conflito`: `vencedor`, o
id do registro que venceu, do mesmo grupo, e `razao`, por que ele é o mais autoritativo para este
claim. "Número diferente" é o que passa da tolerância de reconciliação do builder, que só absorve
ruído de arredondamento. Quando o princípio da fonte não decide:

- a diferença é de definição: não é conflito — separe os claims, nomeando a definição de cada um;
- as fontes são igualmente autoritativas: o agente não escolhe — registra as duas sem `conflito` e
  devolve o conflito aberto ao Analista, que decide. Até alguém decidir, o builder recusa
  (`conflito_de_fontes_silenciado`).

**Contraprova independente para inputs críticos.** Para cada input crítico — o mandato os nomeia; no
fim, são as premissas decisivas da Tese —, procure uma segunda fonte cujo caminho até o número não
passe pelo registro que ela confirma, e registre-a com `contraprova_de`, o id desse registro — o que
sustenta, ou vai sustentar, o input. A `justificativa_da_fonte` da contraprova diz de onde vem a
independência: outro produtor, outra medição, outra conta. **Cópia não conta**, mesmo com outro
nome: o agregador que
republica o filing e a matéria que cita o release carregam a identidade de quem produziu o número.
Sem contraprova independente, declara-se — uma lacuna, com onde se procurou — e o ramo permanece
sensibilidade, nunca base em silêncio. Essa ausência, sozinha, não impede conclusão responsável e
não faz a lacuna MATERIAL; para premissa decisiva, o builder a declara por conta própria
(`sem_contraprova_independente`). Nunca fabrique contraprova para apagar o aviso.

**Lacunas: MATERIAL e NÃO-MATERIAL.** Lacuna é o fato de que a análise precisa e que nenhuma fonte
admissível provou.

- **MATERIAL** — impede conclusão responsável. O Analista interrompe o usuário (§5, política de
  interrupção); o agente nunca interrompe, devolve a lacuna. Se a análise segue, ela sai como aviso
  obrigatório, pela flag `exige_disclosure`.
- **NÃO-MATERIAL** — não impede: nota de limitação declarada, e a análise segue.
- Nunca inventar o número que falta, nunca silenciar a falta. Quem pesquisa classifica pelo
  mandato — o que ele nomeia como crítico —, e o Analista revê a classificação à luz da tese.

**Consenso.** Buscado quando disponível e material: receita e EPS de t, t+1 e t+2, preço-alvo médio,
número de analistas e data. Ele alimenta o confronto temporal da reversa (os pontos de consenso que
o caso declara em `reversa.consenso`) e a âncora do cenário de alta. A Tese cita os registros em
`analise.consenso.registros` e mostra o `claim`, o `periodo`, a `unidade` e a `fonte` deles como
dado: placeholder ali é recusado (`placeholder_em_dado_da_tese`). **A ausência não impede a
análise:** substitui-se por outras âncoras observáveis — guidance vigente da companhia, histórico
normalizado, run-rate do trimestre mais recente sobre a base de capital atual, pares diretos — e
`analise.consenso.ausente` declara a âncora que entrou (o código vem de
`vocabularios.ancoras_do_consenso`) e a razão, que é prosa auditável. O builder declara a ausência
(`consenso_indisponivel`); o confronto temporal sai indisponível, e a leitura das expectativas
embutidas sai qualificada, nunca omitida. Quem pesquisa registra a ausência, com onde procurou, e a
evidência das âncoras; escolher a âncora é do Analista.

**Preço.** Sempre o último disponível, com data e fonte: no registro, `periodo` é a data do preço e
`data_acesso` o dia do acesso. **Não há TTL** — preço não vence por idade. Com data-base explícita,
a análise inteira se ancora nela: o preço é o daquela data, e o spot dos drivers também
(`drivers.*.spot` no caso), nunca o de hoje.

**Sem cache entre execuções.** Cada execução pesquisa do zero: nenhum registro, dataset, lacuna ou
data de acesso vem de outra execução (`analises/<TICKER>/<outra-execução>/`), e a lacuna de uma
execução anterior não dispensa a busca desta. Cache efêmero dentro da execução é permitido, para
não reprocessar a mesma fonte, e morre com ela.

**A reconciliação traz a conta.** Quando o número do caso difere do número do registro, a
`reconciliacao` diz o `texto` que leva de um ao outro — a conversão de escala, o ajuste, com os
números —, nunca "ajustado". O builder aceita qualquer reconciliação declarada e não julga o texto:
a Evidência o mostra, e a doutrina é a única guarda.

## Documentos fornecidos e quarentena (§12)

Todo documento que o usuário fornece é classificado no M1, pelo Analista, antes de a pesquisa o ler:

- **Evidência** — filing, deck, relatório setorial, nota própria: evidência comum, lida desde o
  início. O número lido no arquivo fornecido entra com a classe `documento_do_usuario`, e o
  localizador aponta o arquivo e o lugar nele; achado o mesmo documento na fonte primária, o
  registro sai pela classe dela.
- **Quarentena** — relatório ou valuation anterior **com conclusão** (preço-alvo, fair value,
  recomendação, veredicto), inclusive a saída de uma execução anterior que o usuário aponte. Não é
  lido na pesquisa nem vira registro: só é aberto no M4, depois de toda a derivação pronta — ler
  antes contamina com ancoragem invisível. Os dados de dentro dele não se tiram dali; procure-os na
  fonte primária. O confronto que resulta classifica cada divergência em dado novo, premissa
  revista, erro anterior ou pergunta anterior resolvida pelo observável, e é bloco da entrega, não
  registro do ledger.

O agente só lê os documentos que o mandato lista como evidência. Documento que se revela com
conclusão no meio da leitura é largado sem registro, e o aviso volta ao Analista.

## Resposta do usuário (§18.9)

Resposta do usuário é **evidência a verificar, nunca fato**:

- registre-a com a classe `resposta_do_usuario`, que não se confunde com documento fornecido, e o
  localizador apontando onde a resposta ficou registrada na execução;
- verifique: procure uma fonte admissível que prove o mesmo claim. Achada, é ela que prova o fato;
  se diverge da resposta, é conflito, decidido pelo princípio da fonte — a resposta nunca vence por
  ser do usuário;
- a resposta não é contraprova de outro registro e não sustenta insumo do caso sozinha;
- não verificada, a lacuna fica declarada. O que o Analista faz com o número — hipótese,
  sensibilidade — é decisão dele, e nunca vira base em silêncio.

## Como um registro liga o número ao valuation

Regra inviolável 5 (§18): todo número material do valuation tem proveniência, reconciliação e
justificativa da fonte para aquele claim. **Quais números exigem proveniência não é decisão desta
skill:** é o mapa `catalogo.insumos_do_caso`
de `skills/er-valuation/assets/catalogo_apresentacao.json`, uma lista de padrões de caminho do caso
em que `*` casa exatamente um segmento e o índice de lista é segmento. Toda folha numérica do caso
que o mapa cobre precisa de um registro que a nomeie em `usado_em`, com o mesmo número — por
exemplo, `preco.valor`, `ponte.divida_bruta`, `cenarios.base.premissas.roic` ou `drivers.0.spot`.
Leia o mapa; não o copie.

| Campo | O que liga | Quem escreve |
|---|---|---|
| `usado_em` | os caminhos do caso que o número deste registro sustenta | o Analista, ao montar o caso: dizer que um número entrou no valuation é calibrar |
| `reconciliacao` | o `texto` que leva o número do registro ao do caso, quando diferem | o Analista |
| `conflito` | o `vencedor` do grupo e a `razao` | quem pesquisa, quando o princípio da fonte decide; senão, o Analista |
| `contraprova_de` | o id do registro que esta fonte confirma | quem pesquisa |
| `insumos` | os ids dos registros que a `formula` usou | quem fez a conta |

O que o builder recusa ou declara quando falta cada um:

| O que falta ou está errado | Código | Nível |
|---|---|---|
| folha numérica do caso, coberta pelo mapa, sem registro cujo `usado_em` a nomeie | `insumo_sem_proveniencia` | HARD FAIL |
| caminho de `usado_em` que não é folha numérica coberta pelo mapa | `usado_em_fora_dos_insumos` | HARD FAIL |
| `valor` do registro diferente do número do caso, sem `reconciliacao` | `insumo_nao_reconciliado` | HARD FAIL |
| mesmo `claim` e `periodo`, números diferentes, nenhum `vencedor` do grupo declarado | `conflito_de_fontes_silenciado` | HARD FAIL |
| registro vencido ainda em `usado_em`, com número diferente do vencedor e sem `reconciliacao` | `insumo_sustentado_pela_fonte_vencida` | HARD FAIL |
| id citado em `insumos`, `vencedor`, `contraprova_de`, no consenso da Tese ou num dataset, que o ledger não tem | `referencia_fora_do_ledger` | HARD FAIL |
| dataset de gráfico usado sem os ids dos registros que o sustentam | `dataset_sem_proveniencia` | HARD FAIL |
| placeholder no `claim`, `periodo`, `unidade` ou `identidade` de registro de consenso citado, ou no `claim` ou `unidade` de estimativa que sustenta insumo | `placeholder_em_dado_da_tese` | HARD FAIL |
| dígito fora de placeholder na `descricao` ou no `tratamento` de uma lacuna, ou na razão do consenso ausente | `numero_sem_proveniencia` | HARD FAIL |
| registro cujo estatuto declara `e_estimativa` sustentando insumo, direto ou pelos `insumos` | `insumo_estimado` | REQUIRED DISCLOSURE |
| premissa decisiva sem contraprova de outra `identidade`, com o mesmo número ou `reconciliacao` | `sem_contraprova_independente` | REQUIRED DISCLOSURE |
| lacuna cuja materialidade declara `exige_disclosure` | `lacuna_material` | REQUIRED DISCLOSURE |
| consenso ausente, com a âncora que entrou no lugar | `consenso_indisponivel` | REQUIRED DISCLOSURE |
| uma identidade sustentando mais da metade dos insumos do caso, quando há ao menos quatro | `concentracao_de_fontes` | QUALITY WARNING |

Nenhum aviso se apaga trocando a melhor fonte por uma pior: a concentração de fontes pede
diversificar quando existe fonte à altura, nunca rebaixar a evidência.

A forma é recusa com código 1, nomeando o campo: chave fora do nível, chave obrigatória ausente,
valor fora do vocabulário, id repetido, data fora de AAAA-MM-DD, `formula` ausente sob
`exige_formula` ou presente sem ela (e `insumos` do mesmo jeito), `usado_em` sem `valor` numérico.

## O agente `pesquisa-evidencia`

Um tipo de agente, N instâncias em paralelo; a especialização mora no mandato, nunca na arquitetura.
O Analista passa o mandato no despacho:

- **domínio**: filings; RI e transcripts; setorial e competição; macro e drivers; ou pares;
- **companhia**: identificação, moeda e regime, e a data-base, se explícita;
- **claims** a provar, com o período, e quais são críticos (pedem contraprova independente);
- **documentos de evidência** que ele pode ler — nunca os da quarentena;
- **saída**: o arquivo, dentro da raiz da execução, e o prefixo dos ids, para que as instâncias não
  colidam.

Ele devolve, nesse arquivo, um objeto na forma do ledger (`versao_contrato`, `registros`,
`lacunas`) sem `usado_em` nem `reconciliacao`, e um retorno curto com as contagens, as lacunas, os
conflitos abertos e os claims não cobertos. O Analista junta os fragmentos no ledger único da
entrega e faz a ligação com o caso.

## O que esta skill nunca faz

- Calibrar premissa, escolher cenário ou âncora, montar o caso, escrever tese: é do Analista
  (`er-analise`, `er-valuation`).
- Validar o ledger: é do builder (`er-relatorio`).
- Copiar as listas do contrato ou o mapa dos insumos: os dois são dado, lidos na fonte.
- Metodologia de valuation: `er-multiplos-justos`.
