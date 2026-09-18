# CHANGELOG — Múltiplos Justos

## v10 → v10.1 (ago/2026) — "o que a doutrina exigia e o motor não entregava"

Origem: diligência do próprio pacote v10, feita comando a comando contra as obrigações que a v10
criou. Escopo: **quatro correções, três delas de auto-contradição introduzida na v10**. Nenhuma
fórmula de valuation alterada, **nenhum anchor movido**; `selftest` verde e as duas fases de
`testes.py` passaram. A refatoração de `ev_nopat` em partes foi verificada contra a v10 em 596
casos aleatórios cobrindo as três convenções: **maior divergência 7,1e-15**.

**1. As saídas obrigatórias passam a sair do motor.** A v10 mandou reportar peso do valor terminal,
valor dos ativos instalados e nível implícito recalculado — e nenhum dos três tinha comando, contra
a regra do próprio pacote ("nunca calcule na mão"). Agora: `ev_nopat_partes` e `decomposicao_mm` no
núcleo, o campo `decomposicao_mm` no `ev` (em múltiplos de NOPAT sempre, em moeda com `--ebitda`), e
`nivel` com o segundo bloco de flags devolvendo a leitura recalculada. `ev_nopat` passou a ser a
SOMA das partes, de modo que decomposição e múltiplo não podem divergir.

**2. O nível implícito é uma ESCADA, não duas leituras.** A diligência mostrou que existem três
configurações, não duas: congelada (múltiplo fixo) > vetor travado (só o encargo de reposição
responde — é o que o motor faz) > rentabilidade também derivada do nível. Num caso medido, **263 /
244 / 229**. A v10 chamava a segunda de "central" sem dizer que a terceira existia. Agora a ordem é
declarada como propriedade e a configuração vai à entrega. **Identidade que economiza uma conta:** a
leitura recalculada contra o preço de tela É o break-even da base de lucro.

**3. O viés de mortalidade atravessa para o playbook.** O paper quantifica desde sempre (**−16% a
−27% para hazards de 2% a 5% ao ano**, unidirecional) e a palavra não aparecia uma vez sequer no
`SKILL.md`, no `aplicacao.md` nem no `derivacao.md` — justamente quando a v10 tornou obrigatório
reportar o peso do terminal, que é o gatilho que o paper pede. Agora: `derivacao.md` §5b, regra em
`aplicacao.md` §11.7, item 4 da entrega, e **diagnóstico do motor quando o terminal passa de 50%**.

**4. Confronto com o caixa operacional publicado (§11.8, Gate 0).** Todas as cadeias partiam de peças
montadas pelo analista; nenhuma confrontava contra o caixa que a companhia publica. Declaratório por
construção — a classificação de juros e IR varia por norma —, entrega o **gap e o que ele contém**.
Gap > ~10% sem explicação nominada ⟹ a base de lucro é hipótese, e isso sobe para a Conclusão.

**5. Duas camadas no entregável.** Corpo do memo (seções 1, 2, 3, 5, 6, 7, 8) e anexo analítico
(grades, sensibilidades, break-even, fronteiras). Nada é cortado; muda onde mora. Regra da divisão:
no corpo o que o leitor precisa para SEGUIR; no anexo o que ele precisa para CRITICAR.

**6. Beta construído sobe para a Conclusão.** Quando o beta não é observado na sessão, a premissa
fixa (iv) declara isso e carrega a banda em beta — porque nesse caso parte da faixa de valor não vem
de premissa econômica nenhuma.

**7. Beta bottom-up passa a ser a rota central; regressão da própria ação vira confronto.** A v10
mandava usar o beta observado e cair em pares só na ausência de série — ordenação invertida frente à
prática consolidada: regressão de ação individual tem erro-padrão de 0,20 a 0,30 e mede a estrutura
de capital do passado, enquanto a mediana setorial desalavancada tem erro dividido por √n e é
realavancada ao D/E de hoje. Procedimento completo (seleção por modelo de negócio, desalavancagem,
mediana, realavancagem, ponderação por VALOR em multi-segmento) no §2, com o beta de regressão como
confronto — divergência grande é achado.

**8. Alíquota: convergência à marginal no terminal.** Diferimentos, incentivos com prazo e prejuízo
acumulado são temporários por natureza. O motor tem `t` ÚNICO para explícito e terminal — limitação
agora declarada —, e a regra passa a exigir escolha explícita: marginal ajustada no caso-base com a
efetiva como sensibilidade, ou efetiva com declaração escrita de qual benefício é estrutural.
Divergência acima de ~5 p.p. sem declaração é premissa silenciosa; no caso de referência, 25% contra
34% valiam ~7% do valor.

**Deliberadamente FORA, e por quê.** (a) *Elasticidade efetiva por regressão da margem bruta contra o
preço do driver* — o observável existe e resolveria o input menos ancorado do pacote, mas prescrevê-lo
sem definir janela, tratamento de defasagem e teste de estabilidade trocaria um número declarado por
um número com aparência de medido; fica como roadmap com o desenho a fazer. (b) *Faixa de entrada e
dimensionamento de posição* — o pacote entrega valor e veredicto contra o preço; a decisão de porte é
de mandato, não de valuation.

## v9.32 → v10 (ago/2026) — "os ativos instalados e as duas pernas do capital"

Origem: rodada KEPL3 (Kepler Weber) revisada pelo dono do pacote, mais uma revisão fria do pacote
inteiro contra arquétipos que não originaram nenhuma regra (banco, varejo de ciclo negativo,
siderúrgica, software, concessão, incorporadora, mineradora). Escopo: **doutrinário + três guardas
no motor**. Nenhuma fórmula de valuation foi alterada, **nenhum anchor se moveu**, `selftest` verde
e as duas fases de `testes.py` passaram. A lista de escolhas metodológicas nomeadas permanece em
**onze** — a 8ª foi generalizada, não somada.

**1. Decomposição de Miller-Modigliani como saída obrigatória (§11.7).** `EV(g=0) = NOPAT/W` é
identidade em `convergencia`/`gordon` e depende SÓ de `d` e da alíquota. O pacote tinha teto
obrigatório (crescimento gratuito) e nenhum piso. Passa a reportar ativos instalados, valor do
crescimento e peso do terminal, com a condição de validade declarada. Qualificador de convenção
espelhado em `derivacao.md` §2 (na `book` com CAP finito a identidade não vale).

**2. Contraprova de caixa do `d` (§2).** O teste de natureza era binário e só decidia se o `d` sai;
nunca se o NÚMERO mede o custo de repor. Segunda rota independente pela distribuição divulgada do
capex, limiar de 10% — **e o gap não se lê sozinho**: sob inflação a manutenção verdadeira deve
exceder a D&A a custo histórico (capex excedeu depreciação em ~16–21% na média de longo prazo), logo
igualdade nominal valida o `d` com parque novo e denuncia reposição adiada com parque velho.
Explicitada a insuficiência da conservação (§11.1b), que testa o par e fecha com as duas metades
erradas.

**3. Delator de contração (§2, camadas do RiR).** Terceira exceção à informatividade do deployment
observado: `Δreceita ≤ 0` na janela invalida a rota por deployment. **O teste secundário foi
corrigido antes de entrar:** a versão intuitiva ("sinal de ΔWC diferente do sinal de Δreceita") seria
falso positivo em TODA companhia de giro negativo; a forma correta compara `ΔWC/Δreceita` com
`WC/receita` em razão e em sinal.

**4. Decomposição do g muda de domicílio e de gatilho (§5 → §2; cadeia §11.1c).** Era regra de
cálculo enterrada no capítulo de redação e sem gatilho em nenhum gate. O gatilho deixa de ser
"quando o RiR é a perna derivada" — que a autoexcluía justamente quando o RiR é input — e passa a
valer para toda projeção nominal. **Acoplamento novo e inegociável:** o componente de preço não
consome capital de CRESCIMENTO, mas eleva o custo de REPOSIÇÃO do parque, que pertence ao `d`; sem o
acoplamento, a inflação do estoque de capital desaparece do modelo.

**5. §11.1b incondicional**, com a ressalva de necessidade sem suficiência.

**6. Série de três pontos para inputs de balanço (§1).** Resultado é fluxo de um período; balanço é
estoque num ponto do ciclo. Amplitude > ~20% ⟹ o input é hipótese. A **8ª escolha nomeada foi
generalizada** de "ano de capex de estado estacionário" para "ponto do ciclo dos inputs de capital",
sem criar uma 12ª.

**7. Sinal do ciclo de caixa (§2 item vi, §8f, Gate 0) — e o motor.** O pacote afirmava em §5 que
ciclo negativo gera caixa e em §8f que contração sempre libera giro; e `rampa` recusava `wk < 0`.
Contradição resolvida: a álgebra é a mesma, muda o sinal. O motor passa a aceitar giro negativo
quando `wk + kappa > 0`, com mensagem específica no caso degenerado.

**8. Guardas de domínio no motor.** `d ≥ 100%` devolvia EV/EBITDA **negativo em silêncio**, violando
a regra que o próprio pacote enuncia. Três diagnósticos novos (`d ≥ 100%`, `d ≥ ~60%`, alíquota fora
de 0–100%) e a contraparte doutrinária na fronteira de escopo (§13): cenário com lucro operacional
após imposto ≤ 0 não tem múltiplo justo.

**9. Nível implícito nas duas leituras, com a condição de validade (§4).** Congelado é limite
superior **quando a D&A absoluta não escala com o nível**; se o nível vem de volume, as duas
convergem.

**10. Qualificador do teto do crescimento gratuito (§4, fluxo 3).** O teto é limite superior
**condicional ao g declarado**. Só com a reversa em g também sem raiz no domínio declarado é lícito
concluir que nenhuma hipótese de taxa explica o preço — e nunca "o mercado é irracional". Corrigido
antes de entrar: a formulação sem o qualificador teria ensinado uma inferência falsa.

**11. Break-even das quatro premissas fixas (§4, entrega item 6)** e **decomposição do gap contra o
preço-alvo do consenso (§4)**.

**12. Beta não mensurável: banda em BETA (≥ ±0,20), não em pontos-base (§2)** — mesma unidade do
beta implícito da reversa, para que o confronto seja direto.

**13. Gatilho para a trilha consistente de custo de capital (diagnósticos):** deriva de D/V a mercado
≥ ~10 p.p. ao longo do horizonte ⟹ rodar `apv`. Reformulado antes de entrar: a versão inicial usava
níveis arbitrários de alavancagem em vez de medir a deriva, que é a coisa que importa.

**14. Camadas de leitura (D1) e a entrega de volta ao caminho obrigatório (D2).** `aplicacao.md`
passa a declarar NÚCLEO (sempre) e MÓDULOS (abertos pelo gate que os dispara); o §5b vira passo
numerado do fluxo 2, não ponteiro. Critérios de aceitação (vii) e (viii) nos dois espelhos.

**Deliberadamente FORA (e por quê).** Normalização do CAPITAL ao nível do driver entrou apenas como
**nota declaratória com gatilho de materialidade** (§7), não como recálculo obrigatório: a direção é
certa (estoque indexado ao insumo re-baseia com ele; capital fixo não), mas a magnitude é de um a
dois por cento do capital investido na maioria dos casos, e uma regra correta e imaterial consome
atenção sem mudar conclusão.

## v9.31 → v9.32 (25/ago/2026) — "marca de estoque"

Origem: três execuções frias independentes de AGRO3 (BrasilAgro), 24/ago/2026, devolvendo
**R$ 17,07 / R$ 22,40 / R$ 29,63** — 74% de dispersão com os MESMOS fatos, concentrada numa decisão
que nenhuma das três declarou como escolha: como a marca do estoque de terras entra no valor e o que
vale o balanço da lavoura que a emprega. Escopo **doutrinário**: nenhuma fórmula de valuation foi
alterada, nenhum anchor se moveu, `selftest` e as duas fases de release seguem verdes.

**1. §13 deixa de ser órfão.** A fronteira de escopo — a seção que decide se o framework é a
métrica-manchete ou apenas linguagem de premissas — era citada uma única vez em todo o pacote desde a
v9.7, de dentro do próprio `aplicacao.md`, e não aparecia em nenhum gate, diagnóstico ou na
enumeração do bloco "Referências". Passa a ser disparada pelo Gate 0 e listada. §10 (status das
premissas) também estava fora da enumeração e volta.

**2. Teste da identidade da marca de estoque (§13).** Gatilho ≥ ~20% do valor vindo de marca de
estoque. Uma identidade única — `Marca = VP(aluguel 1..T) + VP(Marca_T)` — de onde saem fator de
tempo, apreciação implícita (contra o custo de capital DO ATIVO, não o da companhia) e T derivado do
giro observado. Silêncio sobre T equivale a adotar a marca como líquida hoje, o ramo mais otimista.

**3. Parede estoque↔fluxo, o lado do ATIVO da parede do §12.** Estoque marcado que é insumo produtivo
do fluxo admite duas rotas — marca à vista com aluguel imputado × fluxo pleno até T com marca
descontada. São idênticas se a identidade fechar; quando não fecha, **o gap entre elas MEDE a
violação**, e é o gap que vai à entrega, não a escolha silenciosa entre as rotas.

**4. Razão R restaurada e generalizada.** A v9.24 trazia em §3 o sub-alerta de recuperação com a
fórmula (`o TV excede NOPAT/WACC por W/ROIC_book`); revisões posteriores reduziram o texto ao rótulo
"sub-alerta de RECUPERAÇÃO" e a fórmula sobreviveu apenas no motor e no paper. Volta ao playbook em
forma geral — `R = marca do estoque ÷ capitalização perpétua do fluxo corrente`, cruzamento exato em
R = 1 — porque a camada que decide a convenção é a que o analista lê, não a que o motor imprime.

**5. Deságio é operação sobre ATIVO, nunca sobre líquido de passivos.** Percentual aplicado a
agregado já líquido de dívida desconta a dívida junto: conservadorismo aparente com o sinal
invertido, e o erro cresce com o deságio.

**6. 11ª escolha metodológica nomeada:** o NÍVEL da marca (avaliação × transação realizada, com a
dispersão das operações). A ROTA (a)/(b) fica FORA da lista, como invariante de coerência ao lado da
base monetária. Renumeração em cascata: a base monetária passa a ser citada como "não é 12ª
bifurcação", e a lista integral do §5b vai a ONZE.

**7. Corolário da base de lucro — vale abaixo do gatilho.** Realização de estoque (ganho de
alienação, reavaliação, marcação) não ancora nem VALIDA base de FLUXO; usar agregado que some as duas
como conferência devolve falso positivo justamente quando os componentes se compensam. Se a companhia
publica a série de fluxo isolada, derivá-la por subtração é proibido.

**8. Critério de aceitação (vi).** Alerta do motor filtrado da saída não conta como alerta lido — o
sub-alerta de recuperação disparou verbatim numa das três rodadas e foi descartado por filtragem de
campo do output.

**9. Composição dos efeitos no registro de drivers (§2).** A soma vale para linhas expostas
DISJUNTAS; drivers que atuam sobre a MESMA linha compõem-se multiplicativamente e entram como driver
único, já composto na moeda em que a companhia realiza. Correção doutrinária: o motor **não** foi
alterado.

**10. Novo arquivo `references/manutencao.md`** — manual de adição de conhecimento: três camadas
obrigatórias, árvore de domicílio, bifurcação × invariante, teste de extrapolação, checklist de
consistência e os cinco anti-padrões. Citado no bloco "Referências" do corpo.

## v9.30 → v9.31 (24/ago/2026) — "fechamento semântico / cross-layer"

Origem: diligência independente da v9.30. Escopo **estritamente semântico e cross-layer**: nenhuma
fórmula central de valuation foi alterada e nenhuma nova feature/metodologia foi criada. Entraram apenas
correções de linguagem, metadados, interface e documentação necessárias para que o pacote descreva
exatamente a matemática já executada.

**1. Bifásico qualificado corretamente.** A solução continua algébrica e fechada, mas passa a ser
descrita como **condicionada à convenção de rebase** `NI2_1 = NI1_next·(ROE2/ROE1)·razão`. O fator
`ROE2/ROE1` é hipótese de degrau de nível do primeiro lucro, não identidade derivada do ROE marginal;
logo `ROE2*` não é rotulado como identificação estrutural pura do marginal. Nenhuma conta mudou.

**2. `E_pre` sincronizado.** `derivacao.md §8b` deixa de carregar a fórmula antiga de book congelado e
usa a mesma variável de estado acumulada por clean surplus já usada pelo motor, §8e, ponte e testes.

**3. Input aceito-mas-ignorado eliminado.** `--rent-book` passa a ser rejeitado com
`iso --transicao ponte`: no bifásico, a média da fase 1 é `--pt-roe1-book` e `ROE2_book` separado não
é implementado. Antes o argumento silenciava o warning sem alterar o cálculo.

**4. Metadado `alpha` corrigido.** Em `tv=book`, o JSON reporta `alpha=1`, exatamente o coeficiente
usado por clean surplus também no equity; fora da `book`, permanece a política FCFE existente.

**5. Anchors e teoria sincronizados.** O anchor P/L canônico passa a 5,617295x em derivação e paper;
a ressalva de horizonte finito passa a dizer corretamente que DDM/DCF↔RI exige terminais consistentes,
em vez de afirmar impossibilidade geral de equivalência finita. Comentário residual sobre planilha
"entregue com o release" é removido.

**6. Testes cross-layer endurecidos.** A suíte agora trava: fórmula antiga de `E_pre` ausente, rebase
qualificado como hipótese, anchor P/L sincronizado, metadado `alpha_book=1`, rejeição de `--rent-book`
na ponte e linguagem correta sobre horizonte finito.

**Fora do escopo:** não foi criado `ROE2_book`; não foi alterada a convenção de rebase; não foi
redesenhada a ponte; não houve mudança em enterprise, equity monofásico, Fisher, APV, solver ou rampa.

## v9.29 → v9.30 (24/ago/2026) — "correções inegociáveis do equity"

Origem: diligência adversarial da v9.29. Escopo deliberadamente conservador: **somente bugs objetivos,
violações de identidade e inconsistências internas** foram corrigidos. Nenhuma nova escolha metodológica
foi introduzida; o núcleo enterprise e os hardenings da v9.28 não foram reabertos.

**1. Dupla contagem de caixa removida da `book` equity.** A v9.29 acumulava corretamente `E_n`, mas
valorizava `PV(FCFE)+PV(E_n)` com `FCFE = Div + Δcaixa`. Como o caixa retido já está dentro de `E_n`,
`PV(Δcaixa)` era contado duas vezes. A v9.30 torna a identidade canônica da `book`:
`Div_t = LL_t − ΔE_t = LL_t(1−g/ROE_marg)` e `P = PV(Div)+PV(E_n)`. Consequência obrigatória:
Caixa/E é neutro nessa convenção (sem rendimento de caixa separado) e `DDM = residual income = motor`.
O caso 5%/20%/book 10%/Ke 8%/n10 passa a **12,8374x** com qualquer Caixa/E; o 13,2670x da v9.29
fica explicitamente supersedido por dupla contagem.

**2. Equity bifásico passa a carregar patrimônio como state variable.** `_pe2_book` não reestima mais
`E_pre = NI/ROE_book` no corte. O patrimônio da fase 1 é acumulado por clean surplus, a fase 2 carrega
separadamente o estado de lucro e o estado de patrimônio, e o TV soma retenções da fase 2 em vez de
recalcular book por um retorno congelado. Teste estrutural novo: dividir artificialmente uma trajetória
idêntica em 1+9, 3+7, 5+5 ou 9+1 anos reproduz o monofásico a erro de máquina, inclusive com
`ROE_book ≠ ROE_marginal`.

**3. Ponte e inversão bifásica sincronizadas ao mesmo E_pre.** `ponte_releveraging` usa o patrimônio
acumulado quando ancorada por `--roe1-book`; `_pe2_book` e `iso --transicao ponte` usam a mesma
variável de estado. A inversão continua fechada porque apenas `f2` depende de ROE2. `--pt-equity`
é agora bloqueado dentro de `iso --transicao ponte`: o input é monetário enquanto `--alvo` é múltiplo
por NI0 e, sem uma base NI0 explícita, misturar as escalas era objetivamente inconsistente. O comando
`ponte` standalone continua aceitando `--equity`.

**4. Cross-layer corrigido.** `SKILL.md`, `aplicacao.md`, `derivacao.md`, paper, diagnósticos e testes
passam a distinguir o módulo FCFE (`gordon`/`convergencia`) da `book` por clean surplus. Saem os trechos
que ainda diziam que equity/`roe-book` estava congelado ou pendente. A fórmula `iso` da `book` equity
usa `α_book=1`, igual ao enterprise, porque Caixa/E não entra no DDM+book.

**5. Novos invariantes de release.** 1.000 property tests exigem `DDM = residual income = motor`;
neutralidade `ROE_marg = ROE_book = Ke` é testada com Caixa/E 0%, 20% e 50%; bifásico→monofásico,
E_pre único e inversão bifásica com book separado entram na suíte. Os anchors antigos de equity/book
que dependiam da dupla contagem deixam de ser referências de verdade.

**6. Proveniência.** A menção da v9.29 a `planilha-equity-book-v9_29.xlsx` como artefato "entregue
junto" era factualmente incorreta para o ZIP canônico de sete arquivos. A derivação permanece descrita
em `derivacao.md` e reproduzida por testes independentes; nenhum arquivo inexistente é prometido.

**Fora do escopo por haver escolha metodológica:** não foi criado `ROE2_book` separado; não foi
redesenhada a semântica monetária do `--equity` standalone; não foi alterado o tratamento de excess
cash/rendimento de caixa fora da correção estrita de dupla contagem da `book`.

## v9.28 → v9.29 (24/ago/2026) — "o espelho do equity"

> **Nota de auditoria v9.30:** esta seção preserva o registro histórico da v9.29, mas as afirmações de sincronização integral e neutralidade dos anchors com caixa foram posteriormente falseadas. Os itens 1–5 abaixo estão supersedidos, quando conflitantes, pelas correções v9.30 acima.

Origem: port da derivação do lado equity (linha paralela iniciada sobre a v9.26 e aposentada como
artefato — a numeração "v9.27" daquela linha colide com a v9.27 cross-layer e não deve circular)
sobre a base v9.28. Derivação originalmente apoiada em planilha de desenvolvimento (`planilha-equity-book-v9_29.xlsx`, não integrante do ZIP canônico; a suíte embute a simulação equivalente em `rec_v929_equity_book`). Regra de release da
v9.27 cumprida: motor, derivação, paper, aplicação e testes sincronizados NESTA versão.

**1. TV da `book` no `pe`/`degrau` com `--roe-book` por clean surplus (justos.py, pe).** Resolve a
pendência declarada na v9.27 item 4. A interação temida com o módulo de política de caixa se
resolve NA derivação: sob C = caixa·E (proporção constante) e a identidade vF8
(FCFE = Div + Δcaixa), a retenção líquida sofre o gross-up da política e o caixa CANCELA —
ΔE_t = (LL_t − FCFE_t)/(1 − caixa) = (g/ROE_marg)·LL_t, INVARIANTE a caixa/E. Logo
E_n = (1+g)·(1/ROE_médio_inicial − 1/ROE_marg) + (1+g)^{n+1}/ROE_marg — a mesma forma do firm,
por cancelamento PROVADO, não por analogia (a proibição da v9.27 de "copiar por analogia" foi
respeitada: a planilha prova linha a linha clean surplus = 0, lucro retido rendendo exatamente o
marginal, FCFE − Div − ΔC = 0, fechada = acumulação, motor = simulação a 1e-10). Guarda
E_n ≤ 0 ⟹ NaN. Colapsos que preservam TODOS os anchors: médio = marginal ⟹ legado EXATO com
QUALQUER caixa (âncoras vF8 do pe — 8,33x/9,04x — e selftest intactos); `--roe-book` omitido ⟹
legado; g = 0 ⟹ E_n = 1/médio; caixa = 0 ⟹ espelho algébrico do firm (P/L corrente 12,8374 =
EV/NOPAT do caso da auditoria). Caso-espelho com caixa 20%: P/L corrente 13,2670; o congelado
superava em +11,5%.

**2. Camadas sincronizadas.** `iso`: inversão UNIFICADA nos dois lados na mesma forma fechada
(α = 1−caixa no pe, 1 no ev) — a forma equity provisória da v9.27 morre. `diag_eq`: PENDÊNCIA sai;
entra o ECO da deriva do médio (espelho do firm) e os textos de CONDICIONADA/sub-alerta/
neutralidade atualizados para a âncora inicial. `rev`: leitura_book do lado equity atualizada.
`derivacao.md` §8c-bis, paper (espelho equity após a proposição do IC acumulado), `aplicacao.md`
§3 e schema da memória técnica (`equity_book_congelado_pendente` → `equity_E_acumulado`) — tudo na
mesma versão.

**3. ERRATA da v9.27 estendida ao equity — e a topologia da base corrente DEPENDE do caixa.** Com
caixa = 0 a álgebra do P/L é idêntica à do firm e o contraexemplo canônico transpõe (marginal 10%,
Ke 12%, book 10%, n 15: máximo interior, duas raízes). Com caixa > 0 o termo de payout
caixa·(g/ROE) CRESCE com g e pode empurrar o máximo para a fronteira — no mesmo caso com caixa
20%, a base corrente fica monotônica e a raiz é única. Consequência para a reversa: a taxonomia
multi-raiz vale nos dois lados e a unicidade nunca é presumida — nem afirmada — sem varrer a
grade; o caixa é agora variável de topologia, não só de fluxo. Contraprovas permanentes nos dois
regimes em `rec_v929_equity_book`.

**4. Cross-layer estendido.** `rec_v927_consistencia_cross_layer` ganha as assinaturas do equity
acumulado (motor, derivação e paper) e proíbe os literais do estado pendente
(`equity_book_congelado_pendente`, "explicitamente pendente e o motor avisa") — a regressão ao
congelado quebra a suíte em qualquer camada.

**5. Validação.** `selftest` OK sem alteração de anchors; fases `model` e `cli` verdes em
invocações frescas.


## v9.27 → v9.28 (24/ago/2026) — "hardening adversarial"

Origem: diligência completa da v9.27 após o fechamento cross-layer. O núcleo enterprise foi
revalidado por reconstrução independente e **não foi reaberto**. A v9.28 incorpora correções de
domínio, edge cases e proposições auxiliares que podiam ser internamente consistentes e ainda
estarem erradas.

**1. Fisher corrigido.** A Skill passa a distinguir (A) rota real exata, (B) rota nominal exata
com inflação em TODO o horizonte explícito e terminal, e (C) inflação apenas no terminal, agora
rotulada como aproximação terminal-only. A e B são as únicas rotas equivalentes por Fisher.
Enquanto o motor não nominalizar integralmente cada componente do fluxo, a rota real exata é a
central para price-taker normalizado a preços de hoje.

**2. Caixa remunerado entra no Gate ROIC↔ROE.** Nova flag opcional `--cash-yield` (bruto). Com
`Cash/E = D/E − ND/E`, a reconciliação usa `+Kcash(1−t)Cash/E` no ROE e o termo simétrico negativo
no WACC operacional. Caixa positivo sem yield informado gera aviso. Rota preferida: operação
separada de excess cash.

**3. CAP longo qualificado.** A convergência n→∞ requer g<W. Com book=marginal o fechamento do gap
é monotônico; com book inicial separado, a convergência continua no limite sob g<W, mas o caminho
pode primeiro abrir e depois fechar. A suíte ganha contraprovas permanentes para g≥W e para
não-monotonicidade com book separado.

**4. Domínio de inputs.** g/gp/gtv ≤ −100%, custos de capital ≤ −100% e n<1 viram hard errors no
CLI. Tax fora de 0–100% e d fora de 0–100% continuam admissíveis como regimes extraordinários, mas
aparecem em `avisos_dominio` e exigem reconciliação explícita. O núcleo também rejeita g≤−100% com
NaN quando chamado como biblioteca.

**5. Solver deduplica raízes.** Uma raiz exatamente sobre um ponto da grade não pode mais aparecer
duas vezes por pertencer aos dois intervalos adjacentes. A taxonomia econômica uma/múltiplas raízes
fica protegida contra duplicação numérica.

**6. Rampa endurecida.** A fase 2 usa `ROIC₂=(1+g₂)m_NOPAT/(wk+κ)`, definida em g₂=0; o antigo
`g₂/RiR₂` gerava 0/0. O VP fechado trata WACC=0 pelo limite da anuidade. `--anos` fracionário deixa
de ser arredondado: a última tranche é proporcional, eliminando saltos artificiais.

**7. APV: C7 explícita e aliases semânticos removidos.** O output mostra FCFF_n, FCFF_{n+1}
usado no TV, g de transição, gtv e o efeito de iniciar gtv já em n+1. `hp` e `me` deixam de ser
aliases de `ku`: Miles–Ezzell e Harris–Pringle exigem políticas próprias. O paper corrige
Miles–Ezzell: primeiro shield a Kd, posteriores a Ku.

**8. Limpeza e referências.** Mid-year passa a ser descrito como convenção midpoint; o gate
agregado de drivers decide com valores não arredondados; o paper passa a contar 15 proposições e
adiciona Mauboussin & Callahan (18/06/2026) sobre PVGO.

**9. Regra de release v9.28.** Todo achado acima tem teste dedicado. A validação de release continua
em duas invocações frescas: `--phase model` e `--phase cli`.

## v9.26 → v9.27 (24/ago/2026) — "fechamento cross-layer"

Origem: auditoria integral de regressão v9.24 × v9.26, seguida de validação matemática independente.
Objetivo: fazer a v9.27 **dominar** a v9.24 sem reverter a correção central da v9.26 — preservar o
framework, sincronizar todas as camadas e transformar os achados da auditoria em testes permanentes.

**1. Matemática `book` enterprise preservada e formalizada em todas as camadas.** O núcleo correto da
v9.26 permanece: `ROIC_book` é a âncora média **inicial/forward** do estoque,
`IC_0 = NOPAT_1/ROIC_book`, e o capital novo do período explícito entra ao ROIC marginal. Portanto:
`IC_n = (1+g)(1/ROIC_book − 1/ROIC_marginal) + (1+g)^(n+1)/ROIC_marginal` e
`TV_desc = IC_n/(1+W)^n`. `derivacao.md`, paper, `SKILL.md`, `aplicacao.md`, diagnósticos e testes
agora usam a mesma semântica. ROIC trailing só pode alimentar `ROIC_book` depois de alinhamento ao
NOPAT_1. O retorno médio no ano n é output (`NOPAT_{n+1}/IC_n`), não parâmetro terminal congelado.

**2. ERRATA da v9.26 — monotonicidade forward NÃO elimina múltiplas raízes na base corrente.** A frase
do changelog anterior segundo a qual a topologia bi-radicular em g “não existe mais” estava errada.
Com book separado, o gradiente do múltiplo **forward** em g segue o spread marginal − W, mas
`M_corrente=(1+g)M_forward` pode ter máximo interior. Contraprova permanente no motor/testes:
ROIC marginal 10%, W 12%, book 10%, n=15, alvo corrente 8,65x ⟹ duas raízes,
g≈0,7552% e g≈4,4109%, ambas reconstruindo o alvo. A taxonomia de reversa (sem raiz / uma raiz /
múltiplas / tangência) permanece válida.

**3. Teoria sincronizada, inclusive exemplos e consequências.** `references/derivacao.md` e
`references/paper-multiplos-justos-v3.md` deixam de ensinar o terminal congelado da v9.24. O paper
passa a distinguir três gradientes: marginal com book inicial fixo (valor sobe), book inicial com
marginal fixo (valor cai) e caso conflacionado (a antiga monotonicidade negativa pode reaparecer).
Anchors reconciliados: auditoria 5%/20%/10%/8%/n10 = 12,8374x corrente = 12,2261x forward; exemplo
25% marginal / 10% book / W 8% / g 4% / n10 = 12,608x separado acumulado contra 9,718x conflado
(−22,9% no conflado). O valor 13,996x fica registrado apenas como contrafactual do book congelado.

**4. Firm × equity separados explicitamente.** A correção de acumulação é somente enterprise.
`pe --roe-book` continua provisoriamente com patrimônio terminal congelado porque a evolução de E
precisa ser derivada junto com clean surplus e política de caixa. `diag_eq`, `iso`, `rev`, `SKILL`
e aplicação agora dizem isso sem transportar a semântica firm para equity. Esta dívida técnica fica
marcada; nenhuma fórmula foi copiada por analogia.

**5. Reversa e diagnósticos corrigidos.** `iso` mantém a inversão fechada firm com IC acumulado e a
forma equity provisória separada. Mensagens que diziam genericamente que o TV “não acompanha o
marginal” foram bifurcadas. A `book` sem book separado continua sinalizando conflação; com
`ROIC_book`, raízes abaixo do WACC são condicionadas à tese de saída pelo capital investido, sem
falsa convergência implícita. O relatório deve distinguir base forward de base corrente ao discutir
unicidade.

**6. Gate 1: ausência de `--tv` ≠ valor inválido.** `ParserGate1` só converte em parada pedagógica do
Gate 1 o erro de argumento **ausente**. `--tv xyz` volta a receber o erro correto de `argparse`
(`invalid choice`) em vez de ser diagnosticado como “convenção não declarada”. Teste CLI dedicado.

**7. Suíte endurecida e regressão da própria v9.26 corrigida.** `ev_ebitda` foi importado; o teste
`rec_v926_book_acumulado()` agora é realmente chamado na fase `model`; round-trip inclui a contraprova
bi-radicular corrente; foi criado `rec_v927_consistencia_cross_layer()` para impedir que motor,
derivação, paper e aplicação voltem a divergir na matemática crítica. A suíte também trava a
semântica da base monetária e os novos campos da memória técnica.

**8. Base monetária reclassificada: invariante obrigatório, não 11ª escolha econômica.** A v9.25
chamou nominal×real de “11ª escolha”. A v9.27 preserva a regra substantiva — g, gp, rentabilidade e
custo de capital sempre na mesma base — mas corrige a taxonomia: conversões nominal↔real coerentes
não deveriam criar valor; portanto a base monetária é uma **convenção/invariante de consistência**
reportada à parte. As dez bifurcações metodológicas da entrega permanecem dez.

**9. Memória técnica expandida para reproduzir o caminho, não só os escalares finais.** O schema em
`aplicacao.md` passa a registrar decomposição do crescimento (volume, inflação, repasse, preço real e
RiR por componente), proveniência/ajustes de `d`, check de clean surplus, regime monetário e bloco
`book` com qualidade, base temporal, retorno médio inicial, capital inicial implícito, marginal,
retorno médio no ano n e indicação explícita da implementação firm acumulada × equity pendente.

**10. Regra de release.** Mudança de uma proposição matemática central exige sincronização entre
motor, derivação, paper, aplicação e testes na mesma versão. Histórico permanece neste changelog;
marcadores antigos no corpo só são mantidos quando têm função operacional/proveniência real.

## v9.25 → v9.26 (24/ago/2026) — "o capital novo chega ao terminal"

Origem: auditoria externa de motor e arquitetura (ago/2026) + validação numérica independente
com contraprova de fechamento. Fase de MOTOR (primeira desde a v9.24) + emagrecimento do corpo.

**1. TV da `book` com `--roic-book` por IC ACUMULADO (justos.py, ev_nopat — o único bug
matemático do ciclo).** O TV usava o ROIC médio CONGELADO no valor inicial: IC_n = NOPAT_{n+1}
/média. Incoerente com os fluxos descontados — o capital novo entra ao MARGINAL (RiR = g/ROIC) e
a média deriva na direção dele. Caso da auditoria (g 5%, marginal 20%, média 10%, W 8%, n 10):
congelado dava EV/NOPAT₁ 13,68; o coerente é 12,23 (**+11,9% de erro, silencioso** — a flag
criada para corrigir a conflação de >30% entregava ~10% sem aviso). Correção em forma fechada:
IC_n = (1+g)·(1/média − 1/marginal) + (1+g)^{n+1}/marginal. Três colapsos preservam tudo que era
válido: média = marginal ⟹ fórmula antiga EXATA (selftest intacto, nenhum anchor de planilha
alterado); `--roic-book` omitido ⟹ legado (conflação sinalizada como antes); g = 0 ⟹ IC = 1/média
(neutralidades da tabela preservadas). Guarda nova: IC_n ≤ 0 ⟹ NaN. Consequências de
comportamento: o TV passa a ACOMPANHAR o marginal (capital-light sai com menos patrimônio;
capital despejado a marginal baixo reaparece na saída pelo patrimônio — coerente com a tese da
convenção); dM/dg sob book separado volta a seguir o sinal do spread marginal − W; a topologia
bi-radicular em g do antigo §6.7 era ARTEFATO do congelamento e não existe mais. Diagnóstico
ganha ECO da deriva (média inicial → média no ano n). Inversão fechada do `iso` (lado ev)
atualizada — continua linear em 1/rent, só os coeficientes mudam. Suíte: anchor B-01 10,30x →
12,10x; exemplos do Gate 1 2,96x/12,14x → 10,16x/12,59x; teste novo com o caso da auditoria
(12,8374 por NOPAT₀), contraprova por acumulação explícita ano a ano e os três colapsos.

**2. PENDÊNCIA — lado equity (`pe`/`degrau`, `--roe-book`).** Mesmo defeito estrutural; a
acumulação do patrimônio sob clean surplus interage com o módulo de política de caixa (C1,
planilha vF8) e NÃO entra no motor sem derivação em planilha. Interino: `diag_eq` avisa a
pendência com a direção do erro quando `--roe-book` ≠ marginal e g > 0.

**3. `--tv` ausente vira instrução de parada do Gate 1 (justos.py, ParserGate1).** O usage cru
do argparse convidava o agente a "resolver" adivinhando uma convenção — o oposto do Gate 1.
Agora: JSON em stdout com erro, instrução de PARAR e perguntar, e o menu das três convenções;
rc = 2 preservado; demais erros de argparse inalterados. Teste de CLI próprio.

**4. Emagrecimento do corpo (49,4 KB → 40,8 KB, −17%) sem perda de regra.** (a) Histórico de versões
migrou INTEGRALMENTE para este CHANGELOG — o corpo cita só a versão corrente (regra de
manutenção nova na seção Referências, anti-regressão). (b) Seção de entrega: o corpo mantém o
ESQUELETO completo do relatório (estrutura fixa de 8 itens, quadro, quatro premissas fixas,
critérios de aceitação, travas); a prosa integral — regra de substituição, pedagogia do quadro,
dez bifurcações por extenso, primeira aparição, formato — migrou verbatim para `aplicacao.md`
§5b, de leitura obrigatória antes de relatório completo. (c) Sufixos de versão removidos dos
títulos de seção (mantido "endurecida na v9.24 — SEM exceção", que distingue comportamento).
Gates preservados na íntegra por decisão de projeto: disparam em todos os fluxos, inclusive no
screening que não obriga a leitura de `aplicacao.md` — a prosa deles é a razão econômica de cada
verificação, não decoração.


## v9.24 → v9.25 (21/ago/2026) — "a moeda do dado decide"

Origem: auditoria externa por literatura (Lundholm & O'Keefe 2000; Bradley & Jarrell; Cornell;
Chan, Karceski & Lakonishok) + quatro rodadas de revisão comentada do dono da skill. Fase
documental; motor intocado.

**1. Decomposição do g por componente (aplicacao.md, bloco "RiR por componente").** Fecho do
espelho da v9.22: o custo do crescimento já era vetor; agora o crescimento também. Gatilho geral:
qualquer projeção nominal (o g já contém reajustes — §2); não restrito a price-maker (correção da
terceira rodada de revisão). g_preço = inflação × repasse + preço real; repasse 0/1 são as
âncoras congelado × acompanhando do §7. Blend só na perna DERIVADA do triângulo — RiR observado
em moeda corrente já nasce blendado; re-blendar é dupla contagem. Fronteiras: price-taker
normalizado a nível sem componente de preço (rota Fisher v9.14); rampa com preço "declarado à
parte" (texto vigente da compressão 2) seguindo a regra — giro sim, fixo não. Triângulo usa g
TOTAL com RiR blendado, ilustrado pela identidade v9.22 do próprio bloco (custo pleno e custo
só-de-giro ÷ NOPAT). Quarta rodada: rota B da v9.14 identificada como caso-limite da regra com
giro ≈ 0 (exato para royalty/streaming; direção declarada em price-taker com giro material) —
responde por que price-taker normalizado fica fora do gatilho sem negar que commodity acompanha
inflação no terminal. Vocabulário: ciclo de caixa (financeiro), desambiguado do ciclo de
capital/commodity.

**2. Guarda de moeda do d (aplicacao.md, cadeia do d, item v).** A moeda do dado de origem
decide: d de fluxo em moeda corrente é proibido de ajustar (dupla contagem contra a taxa
nominal); o ajuste a custo de reposição só existe no gatilho duplo — proxy contábil pura E
inflação × idade materiais (âncora: ~15% acumulado, fator ≳ 1,15 — padronização entre sessões,
precedente do "> ~20%" v9.20). Rebaixada de regra-com-mecânica para guarda, na segunda rodada de
revisão: incidência residual, caso pesado raro, e o risco de misfire (ajustar d já econômico)
subestimaria valor — o erro simétrico ao que a regra corrige. A trava 4 da rampa recebe só a nota
de degeneração: parque recém-construído ⟹ fator ≈ 1; o ajuste tipicamente não se aplica na rampa.

**3. Base monetária vira 11ª escolha nomeada (SKILL.md, Gate 0 — agora seis verificações).**
Escolha central nominal, base ecoada na entrega; verificação de mesma base manual e declarada até
existir trava de motor.

**4. Clean surplus (SKILL.md, Gate 0).** Condicional a projeções fornecidas pelo usuário; declara
"fluxo não explicado", nunca corrige. Fecha a terceira inconsistência de Lundholm & O'Keefe — as
outras duas o framework já bloqueava por construção (reconstrução do fluxo T+1 nas convenções de
TV; recursão período a período no APV).

**5. Parede motor→relatório (SKILL.md).** O conteúdo de um aviso material atravessa; a redação,
nunca. Memória técnica pode carregar saída do motor verbatim; relatório, não.

**Pendências de motor (exigem planilha antes de código):** trava de metadado da base monetária;
conversão Fisher exata com o ajuste do escudo fiscal nominal; fator de reposição como parâmetro
opcional com eco; clean surplus executável.

**Roadmap declarado (avaliado e adiado):** confronto de premissas com base rates de coortes
(custo de execução por rodada > benefício; a visão externa permanece do analista); diagnóstico de
convexidade da grade (até derivação em planilha com limiar fixado — sem âncora, a resposta
despadroniza entre rodadas).

**Não alterado:** motor (`justos.py`), suíte (`testes.py`), âncoras, convenções de TV, escolhas
nomeadas 1ª–10ª, regras vigentes de preço (price-taker→nível §2; volume≠preço §8f; gp no
terminal), parede v9.16, sem-herança v9.24.

**Vigilância declarada (não é regra):** observação do dono de que rodadas recentes tendem a
subestimar o valor central. Hipótese a investigar em sessão própria: empilhamento de defaults
conservadores em rodada central ("o produto dos extremos conservadores É o bear"). Nenhuma regra
foi calibrada por resultado agregado — cada edição se justifica pela verdade do input.

## v9.23 → v9.24 (20/ago/2026) — "sem atalho, e o motor fechou"

Origem: decisão de princípio do dono da skill + fechamento das pendências de código com a
derivação já provada. Duas frentes:

**1. Sem herança — SEM exceção (reversão parcial da v9.23).**
- A exceção do bloco de inputs do usuário foi REMOVIDA (SKILL.md, "Sem herança"): toda rodada
  re-deriva TUDO e roda o fluxo COMPLETO — gates, derivações e todas as seções da entrega —
  mesmo que fique pesado. O peso certo vem de não rodar o que não foi pedido; pedido o
  framework, ele roda inteiro. Bloco anexado vira DADO DE CONFRONTO pós-derivação, com
  divergências declaradas (dado novo / premissa revista / erro anterior) — nunca atalho.
- O carve-out do item 3 em delta na reavaliação (v9.23) foi REVERTIDO: reavaliação roda o
  mandato completo. Registro no J15; o changelog é append-only e a entrada da v9.23 permanece
  como histórico.

**2. Motor fechado (planilha-primeiro cumprido nas duas pontas).**
- **Comando `rampa`** (justos.py): composição bifásica do §8f — fase 1 pela forma fechada
  α/β com autovalidação interna exata (fluxo a fluxo; VP fechado = explícito;
  Receita_T = capacidade quando g1 vem da utilização), fase 2 no PRÓPRIO `ev_nopat` costurada
  como TV. g1 < 0 = bloco de colheita (rotulado, com o aviso da liberação de giro);
  RiR₂ ≥ 100% dispara o delator; output ecoa d re-basado, RiR por fase (variável — sem vetor
  único), travas (terminal/delimitador/volume≠preço) e a ponte de preço.
- **`--roic-ue`** no `ev`: terceiro canal do triângulo (§11.2), espelho do `--rir-observado` —
  divergência acima do limiar sai DECLARADA com leitura direcional e estatuto do peso
  assimétrico.
- **`--capex-total`/`--dwc`** no `ev`: conservação de capital §11.1b executável — gap > 10%
  sai com o alerta de reclassificação do par (d, RiR).
- **Âncora nova no `selftest`** (planilha ELMT ago/26: EV 170,9304; fase 1 45,2592; fase 2 no
  ano T 220,4887; d 25,4→16,5%) e **suíte v9.24 no `testes.py`**: P1–P5 com reconstrução 3DF
  INDEPENDENTE (o teste remonta as linhas ano a ano, sem usar a forma fechada), colheita,
  delator, conservação (par coerente × par quebrado) e unit economics (identidade
  g/RiR_wk = (1+g)·margem×giro com a convenção temporal declarada). Suíte completa: PASSA.
- **Pendência deixada ABERTA por princípio:** HP verdadeiro e Miles-Ezzell verdadeiro no
  `kewacc`/`apv` seguem roadmap — não têm derivação em planilha, e planilha-primeiro não se
  suspende para "fechar pendência". Derivação antes do código, sempre.
- Docs atualizados nos pontos de status (Gate 0, §2, §8f, §11.2, lista de comandos). Gates,
  escolhas nomeadas e regras de análise: inalterados. Sem renumeração.

---

## v9.22 → v9.23 (20/ago/2026) — "a rampa tem forma fechada"

Origem: teste frio da v9.22 no próprio caso-origem (ELMT, J15 estendido) + derivação
planilha-primeiro do bifásico (duas planilhas de prova: 3DF→DCF↔múltiplo em estágio único e em
rampa+expansão). Só documento; ~45 linhas líquidas, tudo dentro de estruturas existentes:

- **Forma fechada da rampa** (§8f, compressão 2): o RiR da rampa varia ano a ano (D&A fixa
  diluindo) — sem vetor único —, mas o fluxo colapsa em DUAS anuidades, FCFF_t = α(1+g₁)^t + β,
  com α = (1−t)·EBITDA₀ − wk·g₁·Receita₀/(1+g₁) e β = −(1−t)·D&A_parque. Duas verificações
  executáveis da costura: fase 2 isolada no motor (`ev`, base do ano T, n = CAP−T) e
  Receita_T = capacidade por construção. Comando `rampa` promovido a "derivação PROVADA"
  (proveniência: planilhas ELMT ago/26, suíte de cinco provas); código pendente de `testes.py`.
- **Direção do erro da rodada única** (§8f, compressão 3): d corrente congelado SUBESTIMA o
  ramo — o re-base do d é permanente (~5% no caso de referência, com a ressalva de origem);
  trava 4 ganha a âncora do d da plena (D&A ÷ EBITDA a plena) e a linha-irmã do G&A fixo.
- **Composição de fases** (§8f): recursão de trás para frente — cada fase é bloco com par
  (d, RiR) e conservação próprios; biblioteca de blocos (investimento, rampa geométrica, rampa
  de/para zero via fator de transição linear, bloco padrão, ponte do §8b, colheita com g < 0 e
  liberação de giro); **trava do delimitador**: fase sem evento observável que a delimite é
  grau de liberdade disfarçado.
- **Fase × safra** (§12): eixos ortogonais — fases no tempo, safras no capital; matriz cobre o
  caso geral (segmento em rampa + segmento investindo); conservação por fase E por safra.
- **Reversa sob intensidade constante** (§8f): ROIC independe de g (margem × giro, identidade
  do §11.2) — o eixo g pode ganhar raiz onde o ramo corrente não tem; raiz sempre com os dois
  confrontos (RiR na raiz × teto do componente; receita implícita × base). Corolário no §11.2.
- **Fallback da contraprova** (§8f, protocolo iii): receita/m², /funcionário, /ativo-chave;
  não executável ⟹ declarado, ramo segue sensibilidade — centralidade não relaxa por falta de
  dado.
- **Item 3 em delta na reavaliação** (SKILL.md, entrega): com bloco herdado e revalidado, o
  item 3 pode ser delta declarado sobre o memorando-base.
- Motor e testes: intocados. Gates e escolhas nomeadas: inalterados. Sem renumeração.

---

## v9.21 → v9.22 (20/ago/2026) — "o preço do crescimento é um vetor"

Origem: rodada ELMT (J15). O capital de crescimento tratado como bloco homogêneo subavalia
companhias com capacidade pré-construída — o RiR agregado cobra capex fixo que não será
incorrido, e o d contábil reflete o parque pleno sobre EBITDA de utilização parcial. Duas
adições, sem mudança de motor:

- **RiR por componente e leitura de capacidade** (SKILL.md Gate 3 + lista de escolhas;
  aplicacao.md §2, §8 tabela, §8f novo, §11.1b): a conservação de capital abre-se em
  RiR = RiR_fixo + RiR_wk; gatilho declaratório (capital fixo intensivo + ociosidade material);
  duas fases com três compressões (re-base − VP do capex comprometido / bifásico costurado /
  rodada única com RiR_wk); protocolo da capacidade física com teto = min(física, demanda,
  autofinanciamento do giro) e contraprova de pares; seis travas (canal único, volume ≠ preço,
  conservação por fase, d médio acoplado à re-derivação do RiR, terminal não herda a rampa,
  delator por componente). Leitura de capacidade = **10ª escolha nomeada**, com centralidade
  branda: caso-base só com observável direto OU contraprova de pares dentro de ±15%.
- **Gatilho por safra de capital** (aplicacao.md §12): SOTP Miller-Modigliani (instalado + PVGO)
  quando base instalada e expansão têm claims de duração distinta (concessão + pipeline); rota
  condicional — claims homogêneos seguem consolidados, com a equivalência declarada.
- **Validação por unit economics** (aplicacao.md §11.2; menção no Gate 0): terceiro canal do
  triângulo, condicional, no estatuto do `--rir-observado` — trava anti-identidade (DuPont sobre
  os mesmos agregados = informação zero), cinco linhas de conta, peso assimétrico
  (observado move o vetor; construído é sensibilidade). Valida, nunca deriva.
- Motor: nenhum. Comandos `rampa` e `--roic-ue`: roadmap planilha-primeiro. Tabela de tradução
  (§5) ganha os equivalentes externos. Testes: inalterados. Sem renumeração de seções.

---

## v9.20 → v9.21 (18/ago/2026) — "a entrega ensina"

Origem: revisão de entrega (decisão de produto do usuário; sem caso J — apresentação, não erro
de análise). O relatório deve ser legível por analista que não conhece teoria de múltiplos:
cada variável explicada pela sua FUNÇÃO na formação de valor, e a estrutura de equity research
completada com perfil, históricos e guidance. Cinco pontos, todos no SKILL.md (o §5 do livro de
regras delega a autoridade estrutural — nada mais muda):

- **Quadro "como o valor é formado"**: elemento fixo, ≤ meia página, entre a Conclusão e as
  Premissas — a cadeia EBITDA → reposição → imposto → financiamento do crescimento → desconto,
  cada variável com sua função em uma linha; lista de banimento vale dentro do quadro.
- **Primeira aparição ensina**: até duas frases sobre a função da variável na primeira vez que
  aparece fora do quadro; nunca vira parágrafo; não se repete.
- **Item 3 renomeado e expandido** — "Companhia, números & indústria": perfil, históricos de
  3–5 anos em tabela curta, guidance (vigente, descontinuado, confronto com realizado),
  administração/governança quando materiais. Mandato completo só no fluxo de relatório de
  companhia; dispensado em reversa rápida e screening.
- **Item 8 enxugado**: metodologia referencia o quadro em vez de re-derivar a mecânica; sem
  citação de referências externas.
- **5º critério de aceitação**: variável usada sem função explicada = entrega incompleta.
- Motor: nenhum. Testes: inalterados. Gates, escolhas nomeadas e livro de regras: intocados.
  Sem renumeração de seções.

---

## v9.19 → v9.20 (18/ago/2026) — "fronteira elevada e payout desacoplado"

Origem: rodada KLBN11 (J13/J14), itens 3 e 4 do backlog. Duas correções de documento, sem
mudança de motor:

- **Elevação da fronteira de consolidação** (aplicacao.md §2): minoritários/coinvestimento
  > ~20% do PL consolidado ⟹ 9ª escolha metodológica nomeada — a fatia de terceiros vai ao EV
  pelo valor contábil × econômico estimado, ambos os ramos precificados; ignorá-la não é ramo,
  é erro. Gatilho espelhado no §12 (coinvestimento consolidado é segmento com economia própria
  por construção) e na dupla entrega do SKILL.md (oito → NOVE escolhas).
- **Exceção de payout sobre base ≠ lucro** (aplicacao.md §2, camadas do RiR): política de
  proventos como % do EBITDA/receita/valor fixo torna a retenção observada não-informativa
  mesmo com payout > 0 — proibida como âncora; fallback ao deployment do DFC ou guidance, com
  troca declarada. Pré-condição correspondente na variante DISTRIBUIÇÃO do §11.1 (v9.18).
- **J13 e J14** registrados no Apêndice J.
- Motor: nenhum. Testes: inalterados (suíte re-executada por disciplina).

---

## v9.18 → v9.19 (18/ago/2026) — "conservação de capital d×RiR"

Origem: rodada KLBN11 (J12). Fim de ciclo de investimento (D&A > capex) forçou a migração do
`d` para base caixa, mas o RiR não migrou junto (~R$ 0,5 bi/ano sem cobrança, +20% de valor) e
a sensibilidade em d congelou o triângulo. Ajustes cirúrgicos, sem mudança de motor:

- **Conservação de capital** (aplicacao.md §2): capex_total + ΔWC = d×EBITDA + RiR×NOPAT —
  o teorema da base coerente estendido ao lado do capital, com quadrantes proibidos simétricos
  aos da v9.15, regra de migração de par em D&A-overhang e o ano-base do capex como premissa
  declarada.
- **§11.1b**: cadeia de verificação da conservação (obrigatória com d ≠ contábil ou D&A > capex).
- **SKILL.md**: Gate 0 (bullet do d) aponta a regra; dupla entrega passa de sete para OITO
  escolhas nomeadas (ano de capex de estado estacionário); diagnóstico novo na lista.
- **J12** registrado no Apêndice J.
- Motor: nenhum (verificação manual em §11.1b; `--capex-total`/`--dwc` no gate de coerência é
  roadmap planilha-primeiro). Testes: inalterados.

---

## v9.17 → v9.18 (18/ago/2026) — "premissas fixas da largada"

Origem: rodada fria ALLD3 (J11). A rentabilidade marginal entrou como input do triângulo,
foi validada nos bastidores contra a retenção observada, mas nunca ganhou cadeia de derivação
exibida e ficou fora da lista de premissas da Conclusão. Ajustes cirúrgicos, sem mudança de
motor:

- **Premissas fixas da lista de abertura** (SKILL.md, item 1 da estrutura): a lista passa de
  3–5 para **4–6**, com quatro vagas sempre obrigatórias — base de lucro/EBITDA, rentabilidade
  marginal (com derivação em uma linha), g e custo de capital. O enforcement mora num lugar
  só: novo critério de aceitação (iv) — fixa ausente ou sem número = entrega incompleta.
- **§11.1 — variante fase DISTRIBUIÇÃO**: cadeia via retenção observada
  (payout → retenção = RiR → M = g/RiR), com exclusão explícita das devoluções
  extraordinárias do payout; e fechamento da porta de escape "rentabilidade como input" —
  a configuração do triângulo diz qual variável é livre, não dispensa a âncora do número.
- **J11** registrado no Apêndice J (aplicacao.md), seguindo a convenção de citação por código.
- **Acabamentos**: item 1 admite "lacuna declarada" quando não houver cobertura de consenso
  (caso J11 — small cap sem sell-side); Apêndice J reordenado em sequência numérica (J9 antes
  de J10), sem alteração de conteúdo.

# CHANGELOG — Múltiplos Justos

## v9.16 → v9.17 (12/ago/2026) — "menu de reconciliação"

Origem: teste frio FNV (J10). A seção de expectativas embutidas entregou UMA fronteira de
reconciliação (consenso 2027 × regime inflacionário do ouro) sem rodar o custo de capital
implícito — que, na base 2028 antecipada, fechava a tela com beta 0,55 (fundo da banda
observada), a explicação mais barata. Ajustes cirúrgicos, sem mudança de motor:

- **Menu de reconciliação** (aplicacao.md §4): expectativas embutidas cobrem os eixos univariados
  aplicáveis + fronteiras bivariadas, com **custo de capital implícito OBRIGATÓRIO em toda
  rodada** (beta implícito contra a banda observada) e julgamento comparativo obrigatório no
  fechamento (menor violência às âncoras observáveis).
- **Dualidade dos eixos de denominador**: Ke menor e crescimento de preço gratuito no terminal
  comprimem o mesmo spread — declarar quando ambos candidatos.
- **Gatilho de duração**: custo − g < ~3 p.p. ⟹ reversa em custo de capital roda primeiro;
  sensibilidade ±50bps reporta preço E múltiplo.
- SKILL.md: fluxo 3 e item 5 do template atualizados (correção: nível NÃO é a única variável
  implícita com observável direto — custo de capital também é); J10 no apêndice.
- Motor: nenhum (o `rev --resolver ke|wacc` já existia). Testes: suíte completa verde.

---

## v9.15 → v9.16 (11/ago/2026) — "o relatório é um produto de mercado"

Origem: teste frio MELI da v9.15 — mérito analítico aprovado; linguagem e estrutura da entrega
reprovadas no critério de produto (25+ referências à infraestrutura interna no texto).

- **P1 Parede processo×produto** (SKILL.md, template): o leitor recebe os achados, nunca a
  infraestrutura; teste do leitor frio sem a skill.
- **P2 Regra de substituição**: escolhas justificadas pela razão econômica em uma frase (ou
  fonte externa citável), nunca pela autoridade da regra. Lista de banimento explícita no corpo
  do relatório (gates, códigos R/C/D/J/§, versões, comandos, enums, termos internos).
- **P3 Tabela de tradução** (aplicacao.md §5): interno → linguagem de mercado; marcadores de
  honestidade preservados.
- **P4 Conclusões na largada**: item 1 = conclusão com as 3–5 premissas decisivas abertas;
  premissas principais promovidas ao item 2; indústria ao 3.
- **P5 Memória técnica**: YAML sai do relatório e vira artefato separado "uso interno"; no
  relatório, quadro de premissas em linguagem plana; captura de aprendizado e oferta são
  chat-only. Título/arquivo do relatório sem versão da skill.
- **P6 Caixa/E em híbrida financeira** (aplicacao.md §9): dívida líquida positiva ou funding de
  carteira relevante ⟹ caixa/E = 0 central obrigatório; ramo bruto = 7ª escolha metodológica
  nomeada. Critério: devolvibilidade, não presença no balanço. Descoberto pelo teste frio
  (alavanca de +45% fora da lista).
- **P7 Limpezas**: exemplo do §5 publicável (sem §11.2); narração das verificações por achados
  com rubricas traduzidas; sete escolhas metodológicas.
- Motor: sem mudanças. Testes: suíte completa verde (nenhuma regressão).
- Aceitação: relatório MELI reescrito nos novos moldes com zero termos da lista de banimento
  (verificado por busca literal) e conteúdo analítico integral preservado.

---

# CHANGELOG — v9.14 → v9.15 (11/ago/2026)

Origem: jurisprudência J8 (MELI) — cinco causas-raiz de erro sistemático em fase de
investimento. Padrão corrigido: regras que detectavam sem operar.

## Correções de acurácia
- **R1 — Teorema da base coerente** (SKILL.md, Gate 0): base e RiR do MESMO regime contábil
  (A reportada × B normalizada à Damodaran); quadrante proibido = base deprimida + retenção
  integral. Vira a 6ª bifurcação da dupla entrega.
- **R3 — Gate 0.5 de fase** (SKILL.md): INVESTIMENTO / DISTRIBUIÇÃO / MISTA / HÍBRIDA
  FINANCEIRA (limiar: carteira > 50% do equity ou receita financeira > 30%), decidindo regime
  da base, informatividade da retenção e rota SOTP.
- **R2 — Camadas do RiR** (aplicacao.md §2): contábil (não-informativo com payout ≈ 0) /
  requerido (líquido de funding próprio — é o que entra no motor) / discricionário (degrau).
- **R4 — Confronto temporal da reversa** (aplicacao.md §1 e §4): consenso t/t+1/t+2 vira
  coleta obrigatória; nível implícito ≤ ~+25% do consenso ⟹ antecipação temporal (reversa
  migra para o vetor consenso via `rev --resolver cap`), não fantasia terminal. Limiar
  calibrado em J8 (razão 1,16).
- **R5 — Canal único de risco-país** (aplicacao.md §2): β local + CRP por lucro OU β de ADR
  sem CRP; empilhar é proibido como central.
- **R6 — Guarda anti-empilhamento** (SKILL.md, entrega): caso-base = ramo central de cada
  bifurcação; produto dos conservadores = bear, dos otimistas = bull.
- **R7 — CAP com observável** (aplicacao.md §2): régua Mauboussin/Rappaport (5–15a, até ~30);
  15–20 exige penetração < ~50% do teto E vantagem em curso.

## Formato de entrega
- Seção de cobertura substituída por **template de relatório de research** (9 itens: capa,
  sumário, negócio & indústria, estimativas × consenso, valuation com as seis bifurcações e a
  guarda R6, o que está no preço, riscos, visão não-consensual obrigatória, disclaimer + YAML
  com campos fase/regime_base/canal_risco_pais/consenso).
- aplicacao.md §5 vira stub (exemplo de formato); autoridade única no SKILL.md.
- Apêndice J — jurisprudência J1–J9 (casos-origem em uma linha; MELI = J8).

## Motor (aditivo; anchors intactos)
- `pe`: diagnóstico de retenção ≥ 95% ⟹ RiR observado não-informativo.
- `nivel`: `--consenso-t1/--consenso-t2` ⟹ razões e leitura antecipacao_temporal /
  acima_do_consenso (limiar 1,25×).
- testes.py: bloco rec_v915 (5 checks). Suíte completa: TODOS OS TESTES PASSARAM.

## Regressão de aceitação
- MELI regime B (g20/ROE30/Ke11,5/gordon 20/4, NI 2.850): US$ 1.787 ∈ [1.700–2.200] ✓
- Ex-caso-base v9.14 vira bear: US$ 715 ∈ [700–900] ✓ com D-1 disparando ✓
- `nivel` 92.270/19,456x/1.863 com consenso t+2 4.084: antecipacao_temporal ✓
- Fase distribuição (payout 60%): sem aviso espúrio ✓

## Eficiência — nota honesta
Cortes aplicados (~200 linhas: convenções e neutralidades em tabela, Gate 1 compactado com
autoridade em §3, diagnósticos compactados, §5 stub, jurisprudência em uma linha, Fisher/gate
de qualidade/§7/§9/§12 comprimidos) foram compensados pelas adições (R1–R7, Gate 0.5, template
ER, apêndice J). Pacote de instrução: 1.298 → 1.296 linhas (≈ neutro; a meta de −23% da
especificação não foi atingida — substância prevaleceu sobre a meta de linhas). derivacao.md e
paper intocados.
