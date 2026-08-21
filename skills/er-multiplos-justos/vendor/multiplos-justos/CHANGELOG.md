# CHANGELOG — Múltiplos Justos

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
