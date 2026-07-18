# Testes de ativação de skills

CI cobre a camada determinística (engine, schemas, pipeline, scripts): 187+
testes. O que CI não cobre é se as skills DISPARAM quando devem — isso só se
observa rodando um agente de verdade contra um pedido em linguagem natural.
Este documento é o protocolo executável para esse gap, adaptado do método
`superpowers:writing-skills` (RED/GREEN/REFACTOR aplicado a descriptions de
skill em vez de código).

## 1. Método

Cada cenário é um teste, não uma leitura. Para cada cenário GREEN ou RED:

1. Rode um agente **fresco** — subagente novo no Claude Code (sem histórico
   desta sessão) ou uma sessão nova no claude.ai/Cowork — **com o plugin
   instalado**. Nunca reutilize uma sessão que já viu outro cenário: contexto
   acumulado contamina o teste (o agente pode disparar a skill certa porque
   "lembra" do cenário anterior, não porque a description funcionou sozinha).
2. Dê ao agente só o pedido do cenário, nada mais. Não mencione o nome da
   skill, não diga "isso é um teste".
3. Registre, na ordem em que aconteceram:
   - **Disparou?** (sim/não) — a skill certa foi carregada.
   - **Antes de qualquer resposta?** — para os GREEN de er-processo em
     especial: a description manda "USE SEMPRE, ANTES de qualquer resposta";
     se o agente respondeu prosa substantiva e só depois (ou nunca) invocou a
     skill, isso é falha mesmo que a skill tenha disparado eventualmente.
   - **Seguiu o corpo ou só a description?** — verifique se o agente aplicou
     as regras do `SKILL.md` (ex.: papéis, gates, formato) ou só reagiu à
     frase-gatilho da description sem ler o resto.
   - **Racionalização observada (verbatim)** — se o agente NÃO disparou a
     skill esperada, copie a explicação/raciocínio dele palavra por palavra.
     Essa frase é o que vai orientar o endurecimento da description, exatamente
     como no writing-skills: o defeito real é o que o agente diz para justificar
     não ter disparado, não uma suposição nossa.
4. **Controle sem a skill**: rode ao menos os cenários GREEN mais ambíguos
   (os que exigem roteamento, ex. "o preço atual faz sentido?") também numa
   sessão SEM o plugin instalado, e registre o comportamento default (o que
   o Claude puro faz sem nenhuma skill do fleet). Isso dá a linha de base
   (RED) contra a qual o resultado COM plugin (GREEN) é comparado — sem essa
   comparação não dá para saber se a skill mudou alguma coisa ou se o agente
   já ia fazer aquilo de qualquer forma.
5. Cenário falhou (não disparou, disparou a skill errada, disparou tarde
   demais, ou seguiu só a description ignorando o corpo) → **endurecer a
   description da skill em questão** (descriptions são o único gatilho de
   ativação; são código, no sentido do writing-skills) → re-rodar o cenário
   que falhou. Qualquer edição de description é seguida de re-execução do
   LOTE INTEIRO (ver critério de aceite, item 5) porque endurecer uma
   description pode roubar disparo de outra skill vizinha (ex.: apertar
   er-valuation pode fazer er-processo parar de rotear para ela corretamente).

## 2. Cenários GREEN (devem disparar, skill esperada entre parênteses)

Mínimo 12. A skill entre parênteses é o disparo correto; quando há seta
(`→`), o primeiro disparo é o esperado no primeiro turno e o segundo é o
roteamento esperado em seguida (ex.: er-processo classifica e depois chama
er-valuation).

1. "Analisa a Vale para mim" (er-processo)
2. "Vale a pena comprar FNV a esse preço?" (er-processo)
3. "O preço atual da Franco-Nevada faz sentido?" (er-processo → er-valuation)
4. "Roda o valuation da VRSK com essas premissas" (er-processo classifica
   PONTUAL → er-valuation; aceitável também er-valuation direto)
5. "Quanto vale a ação X pelo método de vocês?" (er-processo classifica
   PONTUAL → er-valuation; aceitável também er-valuation direto)
6. "Atualiza a tese da FNV com o resultado do 2T" (er-processo P2 → er-memoria)
7. "O que a gente concluiu sobre FNV da última vez?" (er-memoria)
8. "Audita esse valuation" / "roda o red team só no cálculo" (er-auditoria,
   escopo cálculo)
9. "Gera o PDF do relatório" (er-relatorio)
10. "Como essa empresa encaixa na minha carteira? [com snapshot]" (er-portfolio)
11. "Onde acho o 10-K da empresa X? De onde tirar múltiplos de pares?" (er-dados)
12. "Faz a triagem/guardrails da empresa Y" (er-guardrails)

## 3. Cenários RED (NÃO devem disparar o pipeline completo)

Mínimo 5. "Nenhuma" significa nenhuma skill do plugin — resposta direta do
Claude, no máximo.

1. "O que é P/L?" (pergunta conceitual; nenhuma skill ou no máximo resposta direta)
2. "Resume esse artigo de notícias sobre mineração" (nenhuma)
3. "Monta uma planilha de fluxo de caixa pessoal" (nenhuma)
4. "O que é DCF e quando usar?" (conceitual; não deve abrir P1 nem rodar engine)
5. "Traduz esse trecho do 10-K" (tarefa de tradução; não abre pipeline)

## 4. Tabela de registro

Preencher a cada execução do lote. Uma linha por cenário por execução
(re-execuções após ajuste de description viram novas linhas, não substituem
a anterior — o histórico de racionalizações é o que prova que o endurecimento
funcionou).

| Cenário | Data | Ambiente | Resultado | Racionalização observada | Ação |
|---|---|---|---|---|---|
| | | | | | |

Legenda de ambiente: `cowork` (plugin instalado via marketplace/ZIP),
`chat` (claude.ai sem fleet, skills isoladas), `subagente-cc` (Claude Code,
subagente fresco), `controle-sem-plugin` (baseline RED do item 4 do método).

## 5. Critério de aceite do lote

- 12/12 cenários GREEN disparam a skill certa (e, para er-processo, ANTES de
  qualquer resposta substantiva).
- 5/5 cenários RED não abrem o pipeline completo (nenhuma skill do fleet, ou
  no máximo uma resposta direta/conceitual sem invocar er-processo).
- Qualquer falha em qualquer cenário → ajustar a description da skill
  responsável → re-rodar o LOTE INTEIRO (não só o cenário que falhou):
  descriptions são código, mudou uma, todas precisam ser re-verificadas contra
  regressão de roteamento.
- O lote só é considerado aprovado quando uma execução completa (17
  cenários, sem re-ajuste de description no meio) bate 12/12 + 5/5 seguidos.
