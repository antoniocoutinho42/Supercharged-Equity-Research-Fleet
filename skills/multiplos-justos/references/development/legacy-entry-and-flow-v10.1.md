# v10.1: entrypoint e fluxo legado

> Registro de migração, não orientação runtime do Fleet v6.

**Acionamento:** só com `/multiplos-justos`, "rodar múltiplos justos" ou "rodar o framework". Não
infira intenção. Sem o comando, responda normalmente e ofereça a skill em uma linha.

## Sem herança de premissas (endurecida na v9.24 — SEM exceção)

A skill não guarda casos e não reaproveita premissas de análise anterior — premissa herdada
contamina com ancoragem invisível. Toda rodada re-deriva TUDO do zero e roda o fluxo COMPLETO:
todos os gates, todas as derivações, todas as seções da entrega — sem atalho, mesmo que fique
pesado. Bloco de inputs anexado pelo usuário (memória técnica de rodada anterior) NÃO isenta
nenhum passo: ele entra como DADO DE CONFRONTO — depois de re-derivar, compare os outputs com o
bloco e declare as divergências e suas causas (dado novo, premissa revista, erro anterior). O
peso certo da skill vem de não rodar o que não foi pedido; pedido o framework, ele roda inteiro.

## Fluxo por tipo de pedido

**1. Sanity check rápido de DCF:** extraia as variáveis, rode `ev`/`pe`, compare com o múltiplo do
modelo ou de tela. Divergência grande = inconsistência interna (RiR incompatível com g e ROIC;
spread perpétuo não declarado no terminal) ou erro mecânico. *Cobertura e encerramento não se
aplicam.*

**2. Valuation de companhia real:** dados ATUAIS, nunca de memória. Fontes: dado licenciado/
conector → documentos primários (release/ITR/DFP/20-F/deck de RI) → web para preço, consenso
(t/t+1/t+2, obrigatório — §1) e lacunas, com fonte e data. Aplique os gates 0, 0.5, 1, 2 e 3.
**Antes de escrever uma linha do relatório, leia `aplicacao.md` §5b integralmente** — parede,
banimento, estrutura fixa e critérios de aceitação; é passo do fluxo, não ponteiro opcional.
Núcleo de leitura obrigatória: §1 pesquisa, §2 regras travadas, §3 convenção, §4 cenários,
§5/§5b escrita e entrega, §10 status, §11 cadeias, §6 memória técnica. Os módulos (§7 drivers,
§8/§8b/§8f degrau e capacidade, §9 financeiras, §12 multi-segmento, §13 fronteira e marca de
estoque) abrem pelo gate que os dispara — cada gate nomeia o seu.

**3. Engenharia reversa:** entregue o MENU de reconciliação (`aplicacao.md` §4) — os eixos
univariados aplicáveis com os demais no vetor central, sendo o **custo de capital implícito
OBRIGATÓRIO** (beta implícito contra a banda observada) e o NÍVEL implícito obrigatório havendo
driver ou degrau: são os dois eixos com observável de mercado direto para confronto.
**Confronto temporal ANTES de qualquer conclusão:** nível implícito ≈ consenso t+1/t+2
(até ~+25%) ⟹ antecipação temporal, não fantasia terminal — a reversa migra para o vetor consenso
(`rev --resolver cap` contra a base futura = horizonte implícito de mercado); só acima de qualquer
consenso a hipótese terminal está no preço. Regra completa em `aplicacao.md` §4.
Com dois vetores de valor distintos, apresente a curva iso-valor (comando `iso`) e explicite que o mercado paga
por um, raramente pelos dois. **Quando NENHUM eixo primário (rentabilidade, g) tiver raiz:**
dois passos deixam de ser opcionais — (a) o TETO DO CRESCIMENTO GRATUITO (caso-limite RiR→0,
`gordon` com rentabilidade terminal → ∞ e gp = g; a distância até o caso-base é o preço da
hipótese de gratuidade) e (b) a curva `iso` no mesmo alvo (mostra a partir de que g o alvo passa a
ter solução). O `rev` sugere ambos no próprio output (`sugestao`); a mecânica está em
`aplicacao.md` §8 (jurisprudência J3). **Leitura do teto, com o qualificador que a torna
verdadeira:** o teto do crescimento gratuito é limite superior **CONDICIONAL AO g DECLARADO** — não
é teto sobre todas as hipóteses de taxa, porque um g maior o desloca para cima. Só quando a reversa
em g TAMBÉM não tem raiz no domínio declarado (RiR ≤ 100%, gp ≤ teto macro) é lícito concluir que
nenhuma hipótese de TAXA explica o preço; aí o achado é necessariamente sobre o NÍVEL da
métrica-base, sobre a fronteira do ativo (§13 — valor fora do fluxo: marca de estoque,
opcionalidade de controle, ativo parado) ou sobre o denominador. **Concluir "o mercado é
irracional" nesse ponto é erro de leitura**, e a ordem de investigação do teto se aplica inteira.

**4. Consistência Ke↔WACC:** âncora única em Ku elimina circularidade; Ke e WACC viram outputs. Dois
regimes: `mm` (dívida determinística, shields a Kd) e `ku` (shields a Ku sobre a trajetória EXÓGENA
D_t = D0(1+g)^t). **O nome `ku` descreve o mecanismo, não uma teoria:** é a convenção de RISCO dos
shields de Harris-Pringle sobre uma política de dívida exógena — o motor NÃO impõe D/V constante,
que é o que Harris-Pringle exige. O output ecoa `DV_t_%` justamente por isso (na âncora, 18,75% →
36,28%). `hp` e `me` **não são aliases**: o CLI os rejeita para impedir que uma política de dívida seja
silenciosamente substituída por outra. HP verdadeiro (D = L×V, com a circularidade resolvida) e
Miles-Ezzell verdadeiro (primeiro shield a Kd e posteriores a Ku sob rebalanceamento-alvo) são
roadmap planilha-primeiro. Pesos SEMPRE a mercado. `kewacc` é o sanity check ESTÁTICO de perpetuidade; a trilha consistente é a recursão
`apv` (Ke_t e WACC_t período a período, com FCFE@Ke_t = E0 e FCFF@WACC_t = V0 por construção) —
um WACC único aplicado a todos os períodos não corresponde a nenhum período da trilha quando a
alavancagem a mercado deriva. Detalhes em `derivacao.md` §5.
