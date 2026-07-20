# Escopos da auditoria

Fonte: `docs/fontes/Red Team - auditor.md`, Seções 2 a 6, reorganizadas por
escopo (a fonte original roda tudo sempre; este porte permite acionar só a
fatia pedida). Independente do escopo, a Etapa 0 roda sempre primeiro, é
barata: reconstrua em até 6 linhas a tese na forma MAIS FORTE, o mecanismo
de criação de valor e as 3 a 5 premissas de sustentação (com valores) que,
se caírem, derrubam o valor; confirme qual dos dois números está sob teste
em cada afirmação (PREÇO MÁXIMO PARA O HURDLE, origem do sinal de entrada;
VALOR INTRÍNSECO ECONÔMICO, origem do sinal econômico); confundir os dois é
achado. `completa` roda os cinco escopos abaixo, na ordem em que aparecem.

## calculo

PRINCÍPIO (R7 — auditoria proporcional ao risco): quando o valuation foi
produzido pelo engine determinístico, versionado, coberto por golden tests
e testes de cenários válidos, e a execução é rastreável (snapshot/hash), a
auditoria de cálculo VERIFICA A RASTREABILIDADE e concentra o tempo em
integridade dos inputs, premissas e adequação econômica da especificação
(escopos `evidencia`/`especificacao`/`robustez`). Testes validam a
execução do código; não validam a qualidade dos inputs nem a adequação
econômica da especificação — é aí que a auditoria agrega.

RE-EXECUÇÃO DETERMINÍSTICA (sempre, é barata): rode o engine com o MESMO
`inputs.yaml` de `<ns>/runs/<hash>/` (hash de `estado.yaml` campo
`engine.hash`; NUNCA o `inputs.yaml` mutável do namespace); confira
`engine.versao`, `engine.hash_inputs` e `resultados.json` byte-idênticos
salvo timestamp. Rode também `python cap_check.py inputs_<TICKER>.yaml` e
compare o parecer com as respostas do Modelador na tabela de premissas.
Determinismo substitui replicação: PROIBIDO refazer o modelo em planilha
ou num segundo script.

RECOMPUTO INDEPENDENTE (ver `references/recomputo-referencia.md`) — NÃO é
rotina de toda rodada; fica RESTRITO aos gatilhos: (a) resultado gerado
FORA do fluxo determinístico (modo custom, script novo, número sem chave);
(b) fórmula ou adaptação ainda não coberta por golden test (ex.: um
`m_terminal` novo, um bloco novo do engine); (c) falha nos controles
existentes (golden vermelho, hash divergente, snapshot ausente); (d)
anomalia que levante dúvida razoável sobre o cálculo (ex.: sinal
contraintuitivo sem resposta registrada que se sustente). Acionado um
gatilho: recalcule 5 a 8 números sinal-críticos com a implementação de
referência, caminho de cálculo diferente do engine (soma DDM explícita ano
a ano com Bracket DE/NDE vs. a forma fechada); divergência acima de 1e-6
no múltiplo é issue CRÍTICA imediata. Sem gatilho: declare no corpo
"recomputo não acionado (fluxo determinístico rastreável; gatilhos do R7
não presentes)" e siga para os escopos onde a auditoria agrega.

CODE REVIEW DO ENGINE (só quando `engine.versao` mudou desde a última
análise assinada; caso contrário este passo não existe): leia o diff, rode
`tests/test_golden_vrsk.py` (100% verde é condição de promoção; golden
vermelho jamais se "conserta" editando o esperado sem decisão documentada)
e `python cap_check.py --selftest`, confira o CHANGELOG e ASSINE a
promoção (registro no `red_team.md` e no `estado.yaml` via Coordenador).
Alteração de fórmula sem versão nova é achado CRÍTICO.

## evidencia

DIFF DE FATOS (integridade): 8 a 12 itens sinal-críticos do `inputs.yaml` e
da ficha contra o ledger e as fontes primárias (LPA das duas bases,
dívidas, DE/NDE, ações diluídas, EBITDA das duas bases,
`multiplos_historicos` e pares, e a SÉRIE DE SPREAD consolidada que
sustenta a persistência), dirigidos ao que move o sinal. Completude
documental ATIVA: verifique por busca dirigida se existe filing mais novo
que o citado; ausência material declarada é re-checada com UMA busca
independente; ausência refutada é achado de integridade. NUNCA aceite
ausência herdada.

AMOSTRAGEM DE CLAIMS (NOVO): amostre `claims.yaml` por ID, checando 5 a 8
claims `FATO` decisivos na fonte primária citada no campo `fonte`; claim
sem fonte verificável, ou fonte que não sustenta o texto, é achado de
integridade.

## especificacao

JULGAMENTO DE CAP (você é o segundo guardião; `cap_check.py` é parecer, não
gate): a persistência usada é da companhia CONSOLIDADA (ou ponderada por
segmentos), não de um produto isolado? Cada alerta do `cap_check` tem
resposta real na tabela de premissas (resposta evasiva é achado)? A
justificativa econômica do CAP e das diferenças bear/base/bull se sustenta
em evidência da ficha? A confiança declarada (`cap_confianca`) é coerente
com a qualidade da evidência (BAIXA deveria alargar o spread, não encurtar
o CAP)? DUPLA PENALIZAÇÃO: o mapa risco -> parâmetro existe e nenhum risco
foi cobrado duas vezes sem justificativa (Ke E ROE E CAP E probabilidade
pelo mesmo motivo é achado clássico)? O teste vale nos DOIS SENTIDOS:
penalização dupla e mérito contado duas vezes. ANCORAGEM REVERSA: CAP
interno a menos de ~15% do CAP implícito no preço sem justificativa
reforçada é achado. DUPLA CHAVE DA BANDA GERACIONAL: CAP base de 25 anos ou
mais só vale no sinal com a SUA validação explícita registrada no
`red_team.md`; sem ela, determine a re-execução com CAP na banda abaixo e
as duas leituras reportadas. Trate cada pedido desses como exceção
estatística.

MOTOR E BASE: o caso cabia no motor padrão (lucro representativo), ou
exigia modo custom autorizado (pré-lucro, financeira com float, cíclica
profunda)? Custom usado sem necessidade, ou não usado quando devia? Evento
societário exigia base pro forma e o sinal saiu da consolidada?

PREMISSAS: Ke econômico (CAPM em grade, componentes datados, sanidade) e
hurdle distintos e justificados; lucro normalizado (SBC como custo, anti
dupla contagem de diluição); g dentro do teto de coerência; DE/NDE medidos
ou exceção declarada; probabilidades com racional; bear honesto ou
maquiado.

SINAIS E LEITURA: dois sinais das âncoras corretas (três estados no de
entrada, limiares 88%/110%), MODO e PROFUNDIDADE coerentes, MS re-expressa
sem MS negativa, ladder com crença por degrau, variant perception com o
observável que arbitra e prazo.

## robustez

TESTES ADVERSARIAIS POR INPUTS: usando o próprio engine, tente reverter a
DIREÇÃO dos sinais com o cenário mais generoso que você considere
defensável: CAP bull no teto justificado pelo julgamento (ou na banda de
referência acima, se a evidência de renovação o sustentar), ROE e g no
limite de coerência, Ke no piso da grade de sanidade, probabilidades
deslocadas um degrau ao bull. Registre cada teste com o resultado no padrão
"mesmo no cenário X, o preço obtido fica Y% abaixo/acima do preço atual".
Um sinal que só se sustenta com premissas indefensáveis do outro lado é
robusto; um sinal que vira com um ajuste defensável é achado CRÍTICO de
especificação.

VALIDAÇÃO POR MÚLTIPLOS (substitui a antiga triangulação DCF): leia
`validacao_multiplos.veredicto`. DIVERGE_MATERIAL exige do Modelador
revisão de premissas ou explicação premissa a premissa; explicação
ausente, circular ou "esperada por construção" sem exame é achado (a
régua: ou a premissa mudou, ou a diferença está explicada com evidência).
CONVERGE confortável demais também se checa: convergência comprada com
premissa ajustada ao múltiplo é ancoragem.

VARIANT vs. MERCADO (consenso é contraponto, não verdade): tabela curta de
divergências nas premissas decisivas, visão interna vs. consenso vs.
implícito no preço (`reverse.*`), discutida primeiro sob a âncora
econômica. Classifique cada divergência material: VISÃO CONTRÁRIA LEGÍTIMA
| PREMISSA AGRESSIVA | ERRO DE MODELO | MÁ INTERPRETAÇÃO DE DADO |
DIFERENÇA METODOLÓGICA, com as três respostas (por que o mercado erraria;
que evidência sustenta a visão interna; que observável arbitra e quando).
O teste vale nos dois sentidos do CAP: interno abaixo do implícito (o
mercado pode estar certo sobre a duração, cheque contra os precedentes da
taxa-base) e acima (nós podemos estar inflacionando).

FALSIFICAÇÃO ATIVA: a melhor tentativa séria de invalidação com evidência
existente (short reports, dados de cliente, histórico do setor). Afie kill
criteria até ficarem testáveis; cheque que os gatilhos positivos existem e
são testáveis (watchlist só bearish é achado RELEVANTE). Bear com drawdown
plausível pelo próprio modelo. Se nada derrubar após tentativa genuína,
registre que a tese sobreviveu e a QUE testes.

## decisao

A decisão (bloco `decisao` do `estado.yaml`) segue as regras de decisão
(`skills/er-processo/references/regras-decisao.md`) dado o que os sinais e
a auditoria mostram? Robustez DIVERGENTE não resolvida fundamentando compra
é achado CRÍTICO; ressalvas e gatilhos testáveis; kill criteria afiados;
watchlist só bearish é achado RELEVANTE.
