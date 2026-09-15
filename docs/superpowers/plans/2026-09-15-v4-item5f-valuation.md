# Item 5, fatia F — o que está no preço, o cabeçalho completo, a formação do valor e a §11 da Valuation

> **Plano da fatia 5F.** Rascunho revisado pelo controlador contra as §5, §8, §9, §11, §17 e §18 do desenho, ajustado à
> onda de correção da 5E (`5431c43`) e ao regime de execução de 15/09. A seção abaixo vale sobre o resto do plano onde
> conflitar.
>
> **Para agentes:** execute as tasks do seu lote em ordem, com um commit por task.

## Regime de execução (15/09) e ajustes — valem sobre o resto deste plano

**O regime.** Concluir a v4 com eficiência e qualidade suficiente.
- **Escopo:** implementar o que a task pede, sem abstração preventiva nem escopo novo. Melhoria fora do desenho vira uma
  linha de dívida no relatório.
- **Testes:** na proporção do risco — um teste que discrimina cada regra ou número novo. Nada de mutation test, prova
  independente ou fixture nova.
- **Falseabilidade:** as seções assim chamadas nas tasks dizem o que o teste tem de pegar; não são mutações a rodar.
- **Quando rodar:** por task, os arquivos de teste que ela toca; a suíte inteira, uma vez no fim de cada lote.
- **Revisão:** nenhuma por task. No fim da fatia, uma checagem de blockers: funciona, está coerente com o desenho e não
  tem problema material.

**Lotes.**
1. Tasks 1–3 (integração).
2. Tasks 4–5 (relatório).

**Ajustes às decisões:**
- **D9 — a âncora do cenário sai como dado,** por `render._texto_de_dado_html`, fora da prosa auditada.
  - Não se usa `{{livre:...}}` nas âncoras, e os testes que embutem caso de fixture não mudam: a armadilha 3 da Task 4
    cai.
  - Dívida: auditar a âncora como prosa.
- **D12 — `analise.o_que_esta_no_preco` é opcional.** A forma é validada quando o campo é declarado, e a Valuation o
  mostra quando ele existe.
  - Dívida: exigir o julgamento quando há reversa. Quem instrui o analista é o `er-analise`, no item 8.
- **Revisão final da fatia:** a lista daquela seção vira o roteiro da checagem de blockers.

**A onda da 5E (`5431c43`) resolve as "Dependências da 5E":**
- **Endereço da parte de SOTP:** o gate recusa chave do caso com `.` ou `*`. A parte já é endereçada por índice
  (`sotp.partes.<índice>.premissas.<chave>`), como D13 diz.
- **`qc._caminho_da_premissa_no_caso`:** ficou como estava (N5 da revisão, não material).
- **F6 e F7:** não viraram trava, e nada depende deles.
- **Texto de dado novo:** continua saindo por `render._texto_de_dado_html`.
- **Tabela "Cobertura da §11":** manteve a forma; a onda só acrescentou códigos.
- **Baseline:** `5431c43`, com 1173 passed + 1 skipped.

**Goal.** A aba Valuation passa a responder o que a §9 pede além do laboratório, e a §11 fica sem pendência da 5F.
- **O que está no preço:** lido eixo a eixo, sem o relatório aprender as quatro formas de saída do motor.
- **Cabeçalho:** o par de múltiplos forward, com a base declarada.
- **Formação do valor e cenários:** o quadro "como o valor é formado" e os cenários com âncora e triângulo.
- **Sensibilidades 1D:** a integração já as publica e a aba não as mostra.
- **Conservação de capital:** o alerta anda com o número no laboratório.
- **Escala:** os montantes saem com a escala declarada.
- **§11:** o builder passa a declarar a conservação que não fecha, a premissa central fora do ponto central da grade e o
  eixo obrigatório da reversa sem raiz, e a registrar a sensibilidade pouco informativa.
- **SOTP:** a premissa decisiva de uma parte deixa de ser HARD FAIL.

**Architecture.** Três camadas donas, e o relatório lê as três, como na 5E.
- **Integração** (`er-valuation`). Publica:
  - ao lado do payload do motor, a leitura normalizada da reversa;
  - o múltiplo de tela forward e a escala que o caso declara;
  - a conservação de capital, também no espelho e na fachada.
- **Catálogo** (da integração). Carrega o texto de metodologia (a formação do valor, os eixos, os motivos, a
  identificação, o teto) e os vocabulários, travados contra o gate e o wrapper.
- **Relatório.** Valida a forma do que o analista escreve na Valuation, aplica as regras da §11 comparando só números
  publicados ou declarados, e compõe a aba na ordem da §9.

**Fontes.**
- **`docs/desenho-arquitetura-v4.md`:**
  - §5 (os dois produtos);
  - §8.1 a §8.4 (rota e cross-check; cenários, escolhas, retorno exigido e ponderado; triângulo; vivo × precomputado);
  - §9 (a aba Valuation, na ordem; os múltiplos de tela forward na Tese);
  - §11;
  - §14 (sob fronteira, a leitura do preço continua);
  - §15 (decisões 8, 14, 15 e E3);
  - §16.1.
- **Vendor**, lido e nunca copiado:
  - `vendor/multiplos-justos/SKILL.md`: "Fluxo por tipo de pedido", item 3; "A entrega é um relatório de research",
    itens 1, 4 e 5; "Diagnósticos obrigatórios";
  - `references/aplicacao.md`: §4 (grade canônica, menu de reconciliação, confronto temporal, iso), §5b (itens 1, 4 e
    5) e §11.1b;
  - `scripts/justos.py`: `conservacao_capital`, `identificacao`, os ramos do `rev` (inclusive o do `cap`) e
    `nivel_implicito`.
- **Ledger** (`.superpowers/sdd/progress.md`):
  - o mapa da 5D;
  - os registrados da onda da 5D: N2, N3, N9, N11 e "a trava exaustiva do catálogo vai reprovar na 5F";
  - a pendência da 5E: "o confronto temporal da reversa contra o consenso".

## Achados de desenho — o código conferido contra o desenho

1. **O escopo registrado para a 5F são três fatias.**
   - **Medido, no escopo inteiro:**
     - oito blocos novos no caso;
     - doze campos novos em `resultados`;
     - cerca de quinze seções no catálogo;
     - seis campos novos na entrega;
     - uma peça ao vivo no espelho e na fachada;
     - um produto de entrega novo.
   - **O precedente:** a 5D dividiu uma fatia menor pelo mesmo motivo (custo de revisão e quedas de agente).
   - **A proposta** está no mapa abaixo (D1).
2. **"O que está no preço" não é só render.** `resultados.reversa` repassa o motor íntegro, e ler esse payload na tela
   obrigaria o relatório a aprender o motor (E3):
   - `resolucao.motivo` é frase em português, fora do dicionário (§16.1);
   - `beta_implicito.posicao_na_banda` são palavras ("banda não declarada");
   - a variável resolvida só existe no nome da chave (`raizes_wacc_%`);
   - a identificação de cada raiz é chaveada pelo número formatado (`identificacao_por_raiz["10.727%"]`);
   - o intervalo mora numa chave que carrega a tolerância (`intervalo_para_alvo_±1%`);
   - o eixo `cap` tem quatro saídas;
   - o teto do crescimento gratuito publica o múltiplo sem a chave dele.
3. **N9 — o eixo obrigatório sem raiz é resultado, não omissão.**
   - **Medido pela revisão da 5D:** `caso_minimo_firm` com preço 0,5 publica os três eixos percentuais com
     `resolveu: false`, e o QC não diz nada.
   - **O que o vendor manda** quando o alvo é inalcançável: reportar com honestidade. Não é recusar.
4. **A curva iso não está ligada** (nem `iso` nem `nivel` aparecem em `skills/er-valuation/scripts/`).
   - **O que o desenho pede:** §8.4 a lista como precomputada; §9 a pede "quando houver dois vetores".
   - **O que o vendor exige:** a curva é obrigatória quando nenhum eixo primário tem raiz, junto do teto, que o wrapper
     já roda.
   - **Os dois vetores são hoje inalcançáveis com reversa:** rentabilidade e degrau não coexistem com ela (limitação
     `reversa_com_degrau`).
5. **O múltiplo de tela forward não tem de onde sair.**
   - `mercado_tela` é valor de mercado sobre a métrica-base corrente (`reversa.alvo_de_mercado`), e o caso não declara
     métrica forward nenhuma.
   - O justo forward já é publicado (`cenarios.*.multiplos.*_fwd`), mas a manchete não o aponta.
6. **A conservação de capital (§11.1b) só é executável num lugar do motor, e depende de premissas editáveis.**
   - **Onde o motor a executa:** só no subcomando `ev`, com `--capex-total`, `--dwc` e `--ebitda`. O `pe` não tem a
     flag, e a rampa garante a conservação por construção (RiR por componente, §8f).
   - **O conflito com a §8.4:** `da`, `g` e `roic` mudam no laboratório. Um alerta publicado só pelo Python fica
     congelado ao lado de um número vivo, o que a §8.4 proíbe.
7. **N11 é maior que a rampa.** A unidade `moeda` do catálogo é a de montante, e o waterfall da ponte usa o mesmo formato
   (`placeholders.especificacao_de_formato("moeda")`): "R$ 800,00" de dívida bruta ao lado de "R$ 61,91" por ação.
8. **As sensibilidades 1D não aparecem na aba.** `render._paineis_valuation_html` só desenha `grades_2d`, e a grade 1D
   de WACC que `caso_reversa_firm` declara é publicada e nunca exibida.
9. **"Premissa central fora do ponto central da grade" admite duas leituras.**
   - **(a)** A tabela de sensibilidade centrada no cenário-base. Vendor, §5b, item 4: "a célula central reconcilia com
     a manchete".
   - **(b)** A base da grade canônica de cenários como ponto médio entre piso e consenso. Vendor, §4: "Base: ponto médio
     entre trough e consenso, OU a média do próprio histórico normalizado — declare".
   - **A 5E já registrou** o item como "da Valuation, junto das sensibilidades". D11 fica com (a).
10. **"Como o valor é formado" é texto da metodologia, e o RiR não sai como número.**
    - **O quadro é metodologia:** fixo, com a função de cada variável em uma linha (vendor, §5b, item 1). Logo, é do
      catálogo.
    - **O RiR e o spread não têm campo numérico:** na rota firm só existem na prosa da eco `firm_rir` ("RiR = g/ROIC =
      41.7% | spread ROIC−WACC = +2.0 p.p."). `coerencia_vetor` também não os publica.
11. **A âncora de cenário é texto do caso com número dentro.** As fixtures a escrevem assim ("média normalizada
    2023-2025", "utilização divulgada de 65% no 3T25"), e mostrá-la numa aba de comitê é o caso que a F3 da 5D resolveu
    para `fronteira_de_escopo.razao`.
12. **SOTP (F4 da 5D).**
    - **A premissa decisiva de uma parte** é recusada como HARD FAIL (`util`, da parte rampa de `caso_sotp_safra`).
    - **O vínculo** também, porque o vocabulário é só o da rota do caso.
    - **É leitura de contrato:** `resultados.sotp.partes[*]` publica `nome` (único pelo gate), `rota` e `premissas`.
13. **As travas de classificação e as fixtures.**
    - **O que reprova:** os números novos (`manchete.multiplo_forward`, `mercado_tela_forward`,
      `cenarios.*.conservacao_capital`, `reversa.eixos.*.leitura`) reprovam as travas do catálogo até serem
      classificados. É o desejado.
    - **O que falta:** nenhuma fixture declara `metrica_forward`, `conservacao_de_capital` ou `escala_monetaria`, nem
      publica reversa sem raiz. A regra "todo padrão é exercido por alguma fixture" pede variantes compostas, porque não
      se edita fixture.
    - **N3:** `set(CAT["limitacoes"]) == set(LIMITACOES_DE_REVERSA)` reprova com a limitação nova de iso, como a revisão
      da 5D previu.
14. **O bootstrap pareia as matrizes pela posição.** `template.html` usa `hostsMatriz[m]` ↔ `matrizes[m]` e ignora o
    `data-painel-indice` que o host já carrega: é a mesma classe do defeito que a 5D corrigiu nos exhibits. Hoje passa
    por coincidência; reposicionar painéis na Task 5 o expõe.
15. **O desenho atribui ao item 5 partes da aba Valuation que nenhuma fatia tem:**
    - reversa e sensibilidades ao vivo (§8.4; a 5C registrou sem dono);
    - o triângulo como controle do laboratório (§8.3, §15.15);
    - a ponte editável no próprio degrau do waterfall (§9, §15.15);
    - a cadeia de derivação inline em cada premissa (§9);
    - a iso ligada (§8.4);
    - o badge de paridade no cabeçalho, pela ordem da §9;
    - o teto da alavanca rotulado como não-cenário (§8.2).

    Proposta de dono no mapa.

## O mapa do item 5, revisado — proposta

| Fatia | Entrega |
|---|---|
| 5A–5D | **completas** |
| 5E | **completa, em revisão** |
| **5F** (este plano) | O que está no preço lido pela integração (N9, iso como limitação); o par forward; a escala dos montantes (N11); a formação do valor; os cenários com âncora e triângulo; as sensibilidades 1D; a conservação de capital, também ao vivo; as regras da §11 da Valuation; a premissa decisiva por parte de SOTP; a trava de classificação para os números novos |
| 5G | As alternativas que o wrapper roda: painel de escolhas metodológicas, retorno exigido, valor ponderado por probabilidade, cross-check por segundo método e re-teste da hipótese terminal |
| 5H | O produto "Leitura de preço" (§5), com o nível implícito e o confronto temporal contra o consenso (a pendência da 5E) |
| 5I (sem dono hoje) | O laboratório completo: reversa e sensibilidades ao vivo, triângulo como controle, ponte editável no degrau, derivação inline, iso ligada, badge no cabeçalho, teto da alavanca rotulado |

## Global Constraints

- **E3, separação de camadas.**
  - O relatório nunca duplica nem reimplementa lógica metodológica.
  - A skill e o motor são donos da metodologia e do cálculo.
  - A integração (wrapper, espelho, fachada, catálogo) é dona da integração e da paridade.
  - O relatório é dono de interpretação, composição, UX e apresentação.
  - Todo número da aba sai de `resultados` (publicado pela integração a partir do motor) ou do catálogo. Quando o motor
    não entrega algo que o desenho pede, este plano diz de quem é o trabalho; nunca se calcula no relatório.
  - A trava mecânica continua sendo `tests/test_relatorio_fronteira.py`.
- **Calibragem de rigor.**
  - Rigor forte só onde uma divergência pode alterar materialmente o valuation ou a leitura dele, ou quebrar um contrato
    crítico; pragmatismo no resto.
  - Uma revisão por fatia, sem revisor por task.
  - Teste o que discrimina.
  - Não adicione complexidade só para deixar a suíte mais completa.
- **Git.** Sem merge na `main`, sem push. Um commit por task, na `feat/v4-multiplos-justos`.
- **As regras da 5A–5E continuam valendo:**
  - HARD FAIL não emite;
  - raiz única;
  - texto de interface só pelo dicionário ou pelo catálogo;
  - determinismo byte a byte;
  - autocontenção;
  - CSS sem faixa lateral;
  - todo texto de dado por `render._texto_de_dado_html`.
- **O relatório compara; ele não guarda limiar de metodologia.**
  - Comparar números publicados ou declarados é permitido.
  - Limiar de QC do Fleet é constante nomeada no `qc.py`.
  - Limiar da metodologia fica no motor, no wrapper e no espelho, e o QC consome a chave publicada — a lição da F1 da 5C.
    Exemplos: os 10% da conservação, os ~10% de materialidade de uma escolha.
- **O diagnóstico anda com o número (§8.4).** Diagnóstico novo sobre premissa editável entra no espelho e na fachada na
  mesma task, com paridade, e o badge o compara.
- **Número novo é classificado na task que o publica.**
  - Em `resultados`: `catalogo.conclusoes_de_valor` ou `_NAO_SAO_CONCLUSAO_DE_VALOR`.
  - No caso: `catalogo.insumos_do_caso` ou `_NAO_SAO_INSUMOS`.
  - Nenhuma trava de classificação é afrouxada.
- **Todo texto novo que uma aba de comitê exibe entra em `placeholders.campos_de_prosa`**, a lista única lida pelo QC,
  pelo log e pela tela.
  - A exceção é metadado declarado de um número com proveniência (período, fonte, data), que sai como dado — o precedente
    de `caso.preco` no veredicto.
- **Não edite `tests/fixtures/caso_*.json`.**
  - O apoio e as travas compõem variantes (D14).
  - `tests/fixtures/vetores_solver.json` só muda pelo gerador.
- **Asserções sobre o texto que o analista lê:** `apoio.prosa_da_pagina` e as funções de árvore de
  `tests/test_relatorio_tese.py`. Nunca atributo, nunca a página inteira.
- **Todo `achados == []` existente continua valendo, sem ser afrouxado.** Um disclosure novo legítimo sobre uma fixture
  entra nomeado na expectativa, nunca filtrado.
- **Operação.**
  - `vendor/` read-only.
  - A suíte passa de 15 min: rode-a desanexada, pela ferramenta Bash com `run_in_background: true` (nunca `&`, `start`
    nem `nohup`), com
    `python -m pytest tests -q > .superpowers/sdd/<log> 2>&1; echo EXIT=$? >> .superpowers/sdd/<log>`, e espere a
    notificação.
  - Nunca dois lotes pesados em paralelo: o motor dá timeout por contenção de CPU.
  - A baseline é a do fim da onda de correção da 5E (antes dela, 1167 passed + 1 skipped em `69222ca`). Não rode a suíte
    só para confirmá-la.
  - Commit assim que `EXIT=0`, antes do relatório.
  - Mutação, teste e restauração num único comando.
  - Implementadores em sequência no working tree principal: o isolamento por worktree ramifica da `main`.

## Decisões de desenho — tomadas, com a razão

- **D1 — Três fatias, uma revisão cada** (achado 1). A 5F entrega o que o motor e a integração já sabem produzir, mais
  três insumos pequenos (forward, escala, conservação). A 5G concentra os blocos que pedem ao wrapper rodar alternativas.
  A 5H concentra o produto novo. Cada uma fecha testável sozinha.

- **D2 — A leitura da reversa é da integração, ao lado do payload do motor.**
  - **Onde:** `reversa.py` acrescenta `reversa.eixos.<eixo>.leitura` em todo eixo, sem remover, renomear nem
    reformatar nenhuma chave do motor. É o princípio do `resolucao` da 3B.
  - **A forma:**
    ```json
    {"premissa": "wacc", "unidade": "pp", "unidade_da_curvatura": "curvatura", "motivo": "raiz_na_faixa",
     "raizes": [{"valor": 10.727, "identificacao": "forte", "intervalo": [10.61, 10.84], "curvatura": 12.34}],
     "tangenciais": [], "cap_anos": null}
    ```
    `unidade` vale para `valor`, `intervalo`, `tangenciais` e `cap_anos`; `unidade_da_curvatura`, para `curvatura`. As
    duas são chaves de `catalogo.unidades`: o relatório formata pela unidade que a leitura declara, nunca pelo nome do
    campo.
  - **O eixo `cap`:** `premissa` é `null`, `unidade` é `"anos_fracionarios"` e `raizes` é `[]`; `cap_anos` é número só
    quando alcançável.
  - **O eixo de custo de capital** leva também
    `"beta": {"valor", "posicao", "distancia", "banda", "unidade": "beta"}`.
  - **Os vocabulários** são tuplas da `reversa.py` (`MOTIVOS_DA_LEITURA`, `IDENTIFICACOES`, `POSICOES_NA_BANDA`),
    rotuladas pelo catálogo e travadas por igualdade de conjunto:
    - `motivo` ∈ `raiz_na_faixa`, `sem_raiz_na_faixa`, `cap_na_faixa`, `cap_na_faixa_decrescente`, `cap_fora_da_faixa`,
      `cap_indefinido`;
    - `posicao` ∈ `abaixo`, `acima`, `dentro`, `sem_banda`, `sem_raiz`.
  - **O teto** ganha `teto_do_crescimento_gratuito.chave`, a chave do múltiplo.
  - **A razão (E3):** quem conhece as quatro formas do `rev` é a integração. O relatório rotula códigos e formata pela
    `unidade`.

- **D3 — A iso não calculada é limitação publicada, e ligar `iso` fica registrado** (achado 4).
  - **O registro:** `reversa.LIMITACOES_DA_LEITURA = {"iso_nao_calculada": <o gatilho do teto>}`.
  - **O catálogo** declara a limitação com `afeta: "iso"`, e o QC existente a mostra como `limitacao_metodologica`, sem
    regra nova.
  - **A razão:** o gatilho é o do vendor e já está calculado. Ligar `iso` pede decisões próprias (faixa de `g`, número de
    pontos, `--transicao`) e um painel novo.

- **D4 — N9 é REQUIRED DISCLOSURE: `eixo_obrigatorio_da_reversa_sem_raiz`.**
  - **Como a regra sabe qual eixo é obrigatório:** o catálogo declara `eixos_de_reversa.<eixo>.obrigatorio`, travado
    contra `caso.EIXO_OBRIGATORIO`. A regra nunca lê o nome `custo_capital`.
  - **Falha fechada:** sem a seção no catálogo e com reversa publicada, HARD FAIL `eixos_de_reversa_desconhecidos`.
  - **Onde os dois códigos entram na tabela da §11:** na dos códigos de fora ("§9: o que está no preço — custo de capital
    implícito sempre"). O item da §11 "fair value sem reversa / custo de capital implícito" é HARD FAIL, e um alvo
    inalcançável é leitura do preço, não reversa ausente.

- **D5 — O par forward exige a métrica forward declarada no caso** (achado 5).
  - **O bloco no caso:** `metrica_forward: {tipo, valor, periodo, fonte}`, opcional, insumo com proveniência.
    - `tipo` igual ao de `metrica_base`.
    - Recusado na rota rampa e junto de degrau, porque EV/EBITDA0 e P/VP não têm forward.
  - **O que o wrapper publica:**
    - `mercado_tela_forward`, sempre: `{chave, base, valor, algebra, metrica}` ou `null`;
    - `manchete.multiplo_forward: {chave, base, valor}` sempre que a manchete tem múltiplo fora de degrau e rampa.
  - **A conta:** valor de mercado sobre a métrica declarada, pela mesma função de `alvo_de_mercado`, parametrizada.
  - **As bases:** `multiplos_com_bases_diferentes` passa a cobrir o par forward.
  - **Sem métrica declarada:** a tela diz "métrica forward não declarada", sem disclosure.
  - **A razão:** a §9 pede o par "com base declarada", e a métrica forward é fato de mercado (consenso, guidance) com
    proveniência — nunca uma escolha do wrapper.

- **D6 — A conservação de capital sai da integração, também ao vivo** (achado 6).
  - **O bloco no caso:** `conservacao_de_capital: {capex_total: {valor, fonte, ano_base}, dwc: {valor, fonte}}`, com
    `ano_base` ∈ `corrente`, `guidance_longo_prazo` (§11.1b: "corrente | guidance LP — declare qual").
  - **Onde vale:** só na rota firm com métrica EBITDA; fora dela, recusa nomeada.
  - **O que o wrapper faz:** passa as flags só no laço de cenários de `avaliar()` e publica
    `cenarios.<n>.conservacao_capital`, com:
    - a saída do motor, íntegra;
    - `ano_base`;
    - `diagnosticos_chaves`: `["conservacao_capital_nao_fecha"]` quando o motor emite `ALERTA`, `[]` quando não. É por
      presença, o padrão do degrau.
  - **Ao vivo:** o espelho ganha `conservacaoCapital`; a fachada publica a lista, a põe na lista exibida, e o comparador
    a compara.
  - **No QC:** consome a chave pelo catálogo (`disclosures.conservacao_de_capital.chave`), nunca os 10%.
  - **A razão:** §11 e §8.4. O limiar é do motor.

- **D7 — A escala dos montantes é declaração do caso** (achado 7).
  - **O campo:** `escala_monetaria` ∈ `milhares`, `milhoes`, `bilhoes`, opcional, publicado sempre (`null` sem
    declaração).
  - **O catálogo:**
    - rotula a escala (`escalas_monetarias`);
    - declara quais unidades a usam (`unidades.moeda.escala_monetaria: true`; `preço por ação` nunca).
  - **O relatório** aplica o sufixo a toda exibição de unidade que declara a escala. Sem escala declarada, nada muda.
  - **A razão:**
    - a unidade monetária é convenção do caso (§16.2);
    - a decisão por flag da unidade evita o relatório reconhecer montante pelo nome;
    - tornar a escala obrigatória exigiria editar fixtures.
  - **A alternativa descartada:** a `unidade` do registro do ledger é texto livre, e um mesmo waterfall poderia receber
    escalas diferentes por linha.

- **D8 — O quadro "como o valor é formado" é do catálogo, com os números publicados** (achado 10).
  - **O catálogo:** `formacao_do_valor.<rota> = {passos: [{premissa, funcao}], sintese}`.
  - **Os números:**
    - as premissas do cenário da manchete, pela unidade do catálogo;
    - os múltiplos que o cenário publica;
    - na rampa, `vp_fase1` e `valor_fase2_no_ano_T`.
  - **A taxa de reinvestimento** aparece pela função ("crescimento ÷ retorno do capital novo"), com `g` e o retorno ao
    lado, sem número próprio.
  - **Registrado:** extrair o RiR da prosa da eco `firm_rir`, travado contra o motor, seria trabalho da integração.
  - **SOTP:** o quadro sai com o rótulo do consolidado.

- **D9 — Cenários na Valuation: âncora auditada, triângulo rotulado.**
  - **O que a seção mostra:** nome, âncora, triângulo (entradas e saída) e preço e upside, com o rótulo condicional sob
    fronteira.
  - **A âncora** entra em `placeholders.campos_de_prosa` como `resultados.cenarios.<nome>.ancora`. É a regra da F3 da 5D
    para texto do caso exibido numa aba de comitê (achado 11).
  - **As fixtures:** o apoio compõe âncoras com os dígitos das fixtures marcados como `{{livre:...}}`, e um teste
    dispara `numero_sem_proveniencia` com um dígito solto.
  - **O triângulo:** premissas pelo catálogo, e `rir` por `catalogo.variaveis_do_triangulo`. A rampa diz que o triângulo
    não se aplica: o motor reporta o reinvestimento por fase.
  - **A conferir depois da onda de correção da 5E:** a revisão julga o mesmo ponto para o `claim` do insumo estimado
    exibido na Tese. Se ela decidir por dado fora da prosa, a âncora segue a decisão.

- **D10 — A grade 1D é uma tabela.**
  - **O que mostra:** o valor da premissa, o preço e o múltiplo.
  - **Como é feita:** HTML estático, sem JS (§10: "cinco números numa tabela podem comunicar melhor que um gráfico").
  - **O ponto do cenário** é marcado por igualdade exata, a regra da matriz.
  - **Sob fronteira**, o título é condicional.

- **D11 — As regras da §11 da Valuation, sobre números publicados ou declarados.**
  - **Conservação:** REQUIRED DISCLOSURE `conservacao_de_capital_nao_fecha` (D6).
  - **Ponto central:** REQUIRED DISCLOSURE `premissa_central_fora_do_ponto_central_da_grade`, na leitura (a) do achado
    9. Uma grade está centrada quando as duas condições valem:
    - ela perturba o cenário da manchete (`caso.sensibilidades.cenario == manchete.cenario`);
    - em todo eixo, a lista de pontos tem comprimento ímpar e o ponto do meio é igual à premissa desse cenário.

    Senão, disclosure. A igualdade é exata, porque os dois números saem do mesmo caso.
  - **Sensibilidade pouco informativa:** QUALITY WARNING `sensibilidade_pouco_informativa`, quando todas as células
    ficam dentro de `qc.TOLERANCIA_DE_SENSIBILIDADE_POUCO_INFORMATIVA = 0.01` (relativa, `math.isclose`) do preço
    publicado do cenário que a grade perturba.
    - Limiar baixo de propósito: só a grade que praticamente não move o preço acende.
    - A amplitude certa é do analista (vendor §4); é regra de QC do Fleet, não metodologia.
  - **N9:** D4.
  - **As bases do par forward:** D5.
  - **A razão:** a 5B já marca a célula-base por igualdade exata sobre o mesmo caso (`render._base_da_grade`). Nenhuma
    regra lê limiar da metodologia.

- **D12 — O julgamento comparativo é do analista.**
  - **O campo:** `analise.o_que_esta_no_preco: {julgamento, observavel}`, prosa auditada.
  - **Quando é exigido:** obrigatório com `resultados.reversa` e proibido sem ela. Forma, código 1.
  - **A razão:** a §9 e o vendor §5b, item 5, fecham a seção com "qual reconciliação exige a menor violência às âncoras
    observáveis, e qual observável a testaria".

- **D13 — A premissa decisiva de parte é endereçada pelo nome da parte.**
  - **O campo:** `analise.premissas_decisivas[].parte` (opcional), casado contra `resultados.sotp.partes[*].nome`.
  - **O vocabulário:** a chave é premissa da rota da parte e está declarada nela. `vinculo` e `mecanismo` aceitam as
    premissas das rotas das partes.
  - **Os códigos:** reusam `premissa_decisiva_fora_do_cenario` e `vinculo_fora_do_vocabulario`.
  - **A contraprova** usa o caminho da parte no caso (`sotp.partes.<índice>.premissas.<chave>`). **A conferir depois da
    onda de correção da 5E**, que julga `qc._caminho_da_premissa_no_caso` contra a E3.

- **D14 — Variantes compostas, não fixture nova** (achado 13).
  - **Onde moram:** `tests/relatorio_apoio.py` ganha `VARIANTES_DO_CASO: dict[str, tuple[str, Callable[[dict], dict]]]`
    (nome → fixture-base e composição), ao lado de `com_bloco_de_reversa_valido`, que os testes da integração já
    importam.
  - **Quem as usa:** as travas de `tests/test_catalogo_apresentacao.py` iteram fixtures e variantes. Os testes
    parametrizados sobre as fixtures seguem como estão.
  - **A razão:** uma fixture nova entraria em toda parametrização da suíte, e editar fixture é proibido.

- **D15 — A ordem da aba nesta fatia é a da §9.**
  1. Cabeçalho: preço e upside; a faixa piso–teto de `analise.faixa`, quando declarada; múltiplo justo × tela corrente e
     forward; rota e convenção.
  2. Como o valor é formado, colapsável.
  3. Cenários.
  4. O laboratório (premissas por bloco).
  5. A ponte.
  6. As sensibilidades (1D e 2D).
  7. O que está no preço.

  As seções da 5G entram nos lugares da §9: escolhas antes das sensibilidades; retorno exigido, ponderado e cross-check
  depois do que está no preço.

## Dependências da 5E — a conferir depois da onda de correção

1. **O caminho da premissa decisiva no caso.** `qc._caminho_da_premissa_no_caso` e `apoio.completar_ledger` o constroem
   como `cenarios.<cenario>.premissas.<chave>`, e a revisão o julga contra a E3. D13 estende esse caminho às partes.
2. **Texto do caso ou do ledger exibido fora da prosa auditada.** A revisão mede o `claim` do insumo estimado na Tese.
   D9 aplica à âncora a regra oposta (auditada) e segue a decisão da onda.
3. **`render._texto_de_dado_html` e a regra de autocontenção.** A revisão prova, com mutação, que o helper nunca toca
   marcação nem atributo. Todo texto novo da Valuation sai por ele.
4. **A tabela "Cobertura da §11" e `tests/test_relatorio_cobertura_11.py`.** A Task 4 troca as três pendências 5F por
   códigos e tira `5F` dos donos. Se a onda mudar a forma da tabela, a Task 4 segue a forma nova.
5. **O apoio** (`_tese_padrao`, `completar_ledger`, o ledger padrão). A Task 4 acrescenta `o_que_esta_no_preco` e o
   caminho por parte sobre a versão que a onda deixar.
6. **O consenso sob fronteira de escopo** (D4 da 5E). Só a 5H depende dele, no confronto temporal.
7. **A baseline de testes da 5F** é a do fim da onda.

## Fora desta fatia — registrado

- **Para a 5G:** escolhas metodológicas, retorno exigido, valor ponderado, cross-check e re-teste da hipótese terminal.
- **Para a 5H:** o produto Leitura de preço, o nível implícito e o confronto temporal.
- **Sem dono, com proposta 5I:** achado 15.
- **Da integração, se um dia fizer falta:**
  - a iso ligada (D3);
  - o RiR e o spread como número (D8);
  - o máximo e o mínimo atingíveis de um eixo sem raiz, que o motor só escreve na prosa de `sem_solucao`;
  - a conservação por fase na rampa e por parte no SOTP.
- **Da 4C, ainda abertos, com o laboratório:**
  - `avisos_dominio` da rampa sem contraparte no espelho;
  - a recusa de domínio quando a reversa for ao vivo.

## File Structure

| Arquivo | Responsabilidade |
|---|---|
| `skills/er-valuation/scripts/reversa.py` | A leitura por eixo (D2); a chave do teto; `LIMITACOES_DA_LEITURA` (D3); `alvo_de_mercado` parametrizado pela métrica (D5) |
| `skills/er-valuation/scripts/caso.py` | `metrica_forward`, `escala_monetaria` e `conservacao_de_capital` no gate, com recusas nomeadas |
| `skills/er-valuation/scripts/avaliar.py` | `manchete.multiplo_forward`, `mercado_tela_forward`, `escala_monetaria`, `limitacoes` com as duas fontes, `conservacao_capital` por cenário |
| `skills/er-valuation/scripts/motor.py` | `capex_total` em `_FLAGS_COM_HIFEN` |
| `skills/er-valuation/assets/motor_espelho.js`, `espelho_fachada.js` | `conservacaoCapital`; a lista na fachada, na lista exibida e no comparador |
| `skills/er-valuation/scripts/vetores_solver.py`, `tests/fixtures/vetores_solver.json` | Problemas de paridade da conservação, dos dois lados do limiar |
| `skills/er-valuation/assets/catalogo_apresentacao.json` | Os vocabulários de D2, D3, D4, D5, D6, D7, D8 e D9; a classificação dos números novos |
| `skills/er-valuation/SKILL.md` | Os blocos novos do caso e os campos novos de `resultados/1` |
| `skills/er-relatorio/scripts/entrega.py`, `placeholders.py`, `qc.py` | D11, D12 e D13; a âncora e o julgamento na lista de prosa |
| `skills/er-relatorio/scripts/render.py`, `assets/template.html`, `assets/i18n/pt-BR.json` | A aba na ordem de D15; o par forward na Conclusão da Tese; a escala; a premissa de parte |
| `skills/er-relatorio/SKILL.md` | O contrato novo, a tabela de QC, a "Cobertura da §11" e a seção da aba Valuation |
| `tests/relatorio_apoio.py` | `VARIANTES_DO_CASO`; `o_que_esta_no_preco` e âncoras auditáveis na composição padrão; o caminho da parte |
| `tests/test_relatorio_valuation.py` (novo) | Contrato, QC e render da Valuation |

---

## Task 1: a integração publica o que está no preço (sem relatório)

**Files:**
- `skills/er-valuation/scripts/reversa.py`, `avaliar.py`;
- `skills/er-valuation/assets/catalogo_apresentacao.json`, `skills/er-valuation/SKILL.md`;
- `tests/relatorio_apoio.py` (cria `VARIANTES_DO_CASO`, com `reversa_sem_raiz`);
- `tests/test_valuation_reversa.py`, `tests/test_valuation_contrato.py`, `tests/test_catalogo_apresentacao.py`.

**Interfaces — produz:**
- `resultados.reversa.eixos.<eixo>.leitura`, na forma de D2;
- `reversa.MOTIVOS_DA_LEITURA`, `reversa.IDENTIFICACOES`, `reversa.POSICOES_NA_BANDA`;
- `resultados.reversa.teto_do_crescimento_gratuito.chave`;
- `reversa.LIMITACOES_DA_LEITURA` e `reversa.limitacoes_da_leitura(resultado_da_reversa: dict) -> list[str]`;
- `resultados.limitacoes` = a de `caso.reversa_indisponivel` mais as da leitura;
- no catálogo:
  - `eixos_de_reversa.<eixo>`: `{obrigatorio, rotulo}`;
  - `motivos_da_leitura`, `identificacoes`, `posicoes_na_banda`: rótulos;
  - `teto_do_crescimento_gratuito`: `{rotulo, texto}`;
  - `limitacoes.iso_nao_calculada`: `{afeta: "iso", rotulo}`;
  - `unidades.anos_fracionarios` (`num1`), `unidades.beta` (`num2`), `unidades.curvatura` (`num2`);
- `apoio.VARIANTES_DO_CASO["reversa_sem_raiz"]` = (`caso_minimo_firm.json`, reversa composta e `preco.valor = 0.5`). É
  a sonda P7 da revisão da 5D; confira no motor que os eixos percentuais saem sem raiz.

**Armadilhas — leia antes do primeiro teste:**
1. **A leitura anda ao lado, nunca no lugar.** `resolucao` e `beta_implicito` ficam como estão: os testes da 3B os leem.
2. **Raiz e identificação pareiam pela ordem, nunca pela chave.**
   - Os dois lados nascem do mesmo `roots`, na mesma ordem: `raizes_<var>_%` guarda `round(x*100, 3)`, e
     `identificacao_por_raiz` é chaveado por `f'{x*100:.3f}%'`.
   - Faça zip pela ordem, com asserção de mesmo comprimento. Nunca reformate o número para achar a chave.
   - Ache o intervalo pelo prefixo `intervalo_para_alvo_±`.
   - `identificacao()` pode devolver só `{nota}` (derivadas indisponíveis): então `identificacao`, `intervalo` e
     `curvatura` saem `null`.
3. **O eixo `cap` tem quatro saídas no motor** (ramo `cap` do `rev`, `justos.py`):
   - número com valor crescente em `n` → `cap_na_faixa`;
   - número com `direcao` decrescente (anos de destruição de valor tolerados) → `cap_na_faixa_decrescente`;
   - texto → `cap_fora_da_faixa`;
   - `erro` → `cap_indefinido`.

   Confira os ramos no motor antes de escrever o classificador.
4. **O gatilho da iso é o do teto.** `reverter` já o calcula (`"sugestao"` num eixo de `EIXOS_PRIMARIOS`). Fatore a
   condição e use-a nos dois lugares, nunca numa segunda cópia (a lição do FIX 2 da 3B).
5. **N3 — reescreva a trava de conjunto das limitações sem afrouxá-la.**
   - As limitações com `afeta: "reversa"` são exatamente `caso.LIMITACOES_DE_REVERSA`; esta parte não muda.
   - As com `afeta: "iso"` são exatamente `reversa.LIMITACOES_DA_LEITURA`.
   - Toda chave dos dois registros aparece publicada em alguma fixture ou variante.
   - `test_limitacao_de_reversa_e_publicada_se_e_so_se_o_gate_recusa_reversa_valida` compara só as limitações de
     reversa: confira que a lista com mais de um item não a engana.

**Testes:**
- **A leitura contra o payload ao lado**, em `caso_reversa_firm` e em `reversa_sem_raiz`:
  - `premissa` é a de `RESOLVER_POR_EIXO[eixo][rota]`;
  - `raizes[].valor` é igual a `raizes_<var>_%`, em ordem;
  - `identificacao` é a do motor para a mesma raiz.
- **`reversa_sem_raiz`:**
  - os eixos percentuais saem com `motivo: "sem_raiz_na_faixa"`;
  - o teto sai com a `chave` do múltiplo de referência;
  - `iso_nao_calculada` está em `limitacoes`.
- **`caso_reversa_firm`:** nem o teto nem a limitação da iso.
- **As posições e as saídas do `cap` que nenhuma fixture alcança:** a função que monta a leitura, sobre um payload
  sintético no formato do motor.
- **O catálogo:**
  - `set(eixos_de_reversa) == caso.EIXOS_DE_REVERSA`, e `obrigatorio` só em `caso.EIXO_OBRIGATORIO`;
  - os três vocabulários iguais às tuplas da `reversa.py`;
  - rótulos em todo idioma;
  - `test_chaves_de_topo_do_catalogo` com as seções novas.

**Falseabilidade:**
- pareie a identificação pela chave reformatada com `.2f` → vermelho;
- tire a limitação do registro → a trava de `afeta: "iso"` fica vermelha;
- ponha `obrigatorio: true` no eixo `cap` → vermelho.

---

## Task 2: o par forward, a escala dos montantes e a formação do valor (sem relatório)

**Files:**
- `skills/er-valuation/scripts/caso.py`, `avaliar.py`, `reversa.py`;
- `skills/er-valuation/assets/catalogo_apresentacao.json`, `skills/er-valuation/SKILL.md`;
- `tests/relatorio_apoio.py` (variantes `forward_firm`, `forward_equity`, `escala`);
- `tests/test_valuation_caso.py`, `tests/test_valuation_contrato.py`, `tests/test_valuation_matriz.py`,
  `tests/test_catalogo_apresentacao.py`.

**Interfaces — consome:** Task 1 (variantes). **Produz:**
- **No caso:**
  - `metrica_forward: {tipo, valor, periodo, fonte}`;
  - `escala_monetaria`, com o vocabulário `caso.ESCALAS_MONETARIAS = frozenset({"milhares", "milhoes", "bilhoes"})`;
  - as duas chaves em `CHAVES_DE_TOPO_PERMITIDAS`.
- **Em `resultados`:**
  - `manchete.multiplo_forward: {chave, base, valor}`, lido de `cenarios.<base>.multiplos` pela chave `_fwd` da métrica
    (fora do SOTP, do degrau e da rampa);
  - `mercado_tela_forward`: `{chave, base, valor, algebra, metrica: {tipo, valor, periodo, fonte}}` ou `null`, sempre
    publicado;
  - `escala_monetaria`: o código ou `null`, sempre publicado.
- **Funções:**
  - `avaliar._chave_e_base_do_multiplo_forward(rota: str, tipo_metrica: str) -> tuple[str, str] | None`;
  - `reversa.alvo_de_mercado(caso, nome_cenario, nd_efetivo, valor_da_metrica: float | None = None)`, que sem o
    parâmetro faz a conta de hoje.
- **No catálogo:**
  - `escalas_monetarias` (rótulos) e `unidades.moeda.escala_monetaria: true`;
  - `formacao_do_valor.<rota>` (`passos: [{premissa, funcao}]`, `sintese`) e `variaveis_do_triangulo.rir`;
  - `conclusoes_de_valor["múltiplo"]` com `manchete.multiplo_forward.valor`, e `insumos_do_caso` com
    `metrica_forward.valor`.

**Recusas nomeadas no gate:**
- `metrica_forward` na rota `rampa` ou junto de `degrau`;
- `metrica_forward.tipo` diferente de `metrica_base.tipo`;
- `metrica_forward.valor` não finito ou menor ou igual a zero;
- chave desconhecida dentro de `metrica_forward` (a classe F3 da fatia D, com `difflib`);
- `escala_monetaria` fora do vocabulário.

**Armadilhas:**
1. **O múltiplo de tela forward é a conta de `alvo_de_mercado` com a métrica declarada.** Parametrize-a; não escreva
   uma segunda.
2. **`formacao_do_valor` é texto da metodologia.**
   - **A fonte:** `references/aplicacao.md`, §5b, item 1 (encargo de reposição, imposto, fração reinvestida, margem entre
     custo de capital e crescimento).
   - **Na `equity`:** a retenção e o caixa sobre patrimônio do `SKILL.md` do vendor.
   - **Na `rampa`:** as duas fases do §8f.
   - **O que nunca entra:** função inventada ou número de RiR (D8). A revisão confere o texto contra o vendor.
3. **As travas de classificação:**
   - `manchete.multiplo_forward.valor` é exercido pelas fixtures; `metrica_forward.valor`, só pela variante;
   - `mercado_tela_forward.**` entra na razão "leitura de mercado" de `_NAO_SAO_CONCLUSAO_DE_VALOR`;
   - `test_o_mapa_nao_cobre_o_multiplo_de_tela_nem_o_que_o_caso_declara` passa a cobrir `mercado_tela_forward`.
4. **A matriz rota × bloco** (`tests/test_valuation_matriz.py`) ganha as células das recusas novas (`metrica_forward` ×
   rampa e × degrau), e a asserção do tamanho acompanha. É a classe que já apareceu quatro vezes.
5. **As variantes, sem reversa nem grade, rodam rápido.**
   - `forward_firm` e `forward_equity` partem de `caso_minimo_firm` e `caso_minimo_equity`.
   - `escala` parte de `caso_rampa`, a única rota com premissa monetária, que também tem ponte. É nela que a Task 5
     afirma o sufixo no valor original da rampa e no waterfall.

**Testes:**
- **Nas variantes forward:**
  - `mercado_tela_forward.valor` bate com o valor de mercado sobre a métrica forward, com o oráculo montado no teste a
    partir do caso;
  - a `base` é a da manchete;
  - `manchete.multiplo_forward.valor` é o `_fwd` do cenário-base.
- **Sem declaração:** `mercado_tela_forward` e `escala_monetaria` saem `null` em toda fixture.
- **Cada recusa**, com a mensagem que a nomeia.
- **O catálogo:**
  - `set(escalas_monetarias) == caso.ESCALAS_MONETARIAS`;
  - `set(formacao_do_valor) == set(rotas)`;
  - todo `passos[].premissa` é premissa da rota;
  - `set(variaveis_do_triangulo)` é igual a `caso._TRIANGULO_POR_ROTA[rota] - set(premissas[rota])` nas rotas com
    triângulo;
  - rótulos em todo idioma.

**Falseabilidade:**
- use `metrica_base.valor` no forward → o teste do valor fica vermelho;
- aceite `metrica_forward` na rampa → a célula da matriz fica vermelha;
- ponha `rir` como `passos[].premissa` → a trava do catálogo fica vermelha.

---

## Task 3: a conservação de capital, publicada e ao vivo (sem relatório)

**Files:**
- `skills/er-valuation/scripts/caso.py`, `motor.py`, `avaliar.py`;
- `skills/er-valuation/assets/motor_espelho.js`, `espelho_fachada.js`, `catalogo_apresentacao.json`,
  `skills/er-valuation/SKILL.md`;
- `skills/er-valuation/scripts/vetores_solver.py` e `tests/fixtures/vetores_solver.json` (regenerada);
- `tests/relatorio_apoio.py` (variantes `conservacao_fecha`, `conservacao_nao_fecha`);
- `tests/test_valuation_avaliar.py`, `tests/test_valuation_caso.py`, `tests/test_valuation_matriz.py`,
  `tests/test_catalogo_apresentacao.py`, `tests/test_paridade_solver_js.py`, `tests/test_espelho_fachada_js.py`.

**Interfaces — consome:** Tasks 1 e 2. **Produz:**
- **No caso:** `conservacao_de_capital` na forma de D6, com `caso.ANOS_BASE_DO_CAPEX = frozenset({"corrente",
  "guidance_longo_prazo"})`.
- **No wrapper:** `avaliar.precificar_firm(..., conservacao: dict | None = None)`; só o laço de cenários de `avaliar()`
  a passa.
- **Em `resultados`:** `cenarios.<n>.conservacao_capital`, com a saída do motor íntegra, `ano_base` e
  `diagnosticos_chaves`. O vocabulário é `avaliar._CHAVES_DA_CONSERVACAO`.
- **No espelho:** `conservacaoCapital(capexTotal, dwc, ebitda, d, t, g, roic)`, com o arredondamento e o limiar do
  motor.
- **Na fachada:** o cenário firm publica `conservacao_capital: {diagnosticos_chaves}`, `listaExibida` a inclui, e
  `compararComResultados` a compara.
- **No catálogo:**
  - `diagnosticos.conservacao_capital_nao_fecha` (severidade `alerta`, bloco `crescimento_reinvestimento`);
  - `disclosures.conservacao_de_capital` (`chave`, `texto`);
  - `anos_base_do_capex` (rótulos);
  - `insumos_do_caso` com os dois `valor`.
- **As variantes** partem de `caso_minimo_firm` (EBITDA 1000, d 20, t 25, g 5, ROIC 12). Os encargos são 450
  (reposição 200, crescimento 250).
  - **Fecha:** capex 430 e ΔWC 20 dão gap 0.
  - **Não fecha:** capex 300 e ΔWC 0 dão gap de −50%.

  Confira no motor antes de prender o número.

**Recusas nomeadas no gate:**
- o bloco fora da rota `firm` ou com métrica diferente de `EBITDA`. O motor só confronta a identidade no `ev`, com
  `--ebitda`; a rampa a garante por construção (§8f). O degrau só existe na rota equity, então fica coberto por esta
  recusa;
- `capex_total.valor` não finito ou menor ou igual a zero;
- `dwc.valor` não finito;
- `ano_base` fora do vocabulário;
- chave desconhecida em qualquer nível do bloco.

**Armadilhas:**
1. **Só o cenário.** `precificar_firm` também serve às células de grade, às partes de SOTP e ao teto: as flags não
   entram nelas.
2. **A flag tem hífen** (`--capex-total`): `motor._FLAGS_COM_HIFEN` ganha `capex_total`, e `dwc` passa verbatim.
3. **A saída do motor pode ser texto** ("NAO CHECAVEL…") quando falta `--ebitda`.
   - Com o gate isso é inalcançável, e o wrapper recusa nomeando (`MotorFalhou`), nunca publica texto no lugar do bloco.
   - `gap_%` passa por `_exigir_valor`: capital consumido nulo vira `null` no motor.
4. **Os números do bloco não são conclusão de valor.** Razão nova em `_NAO_SAO_CONCLUSAO_DE_VALOR`: "o diagnóstico da
   conservação de capital: capital consumido × encargos de reposição e de crescimento".
5. **§8.4 — as travas da fachada só iteram fixtures.**
   - `test_a_lista_exibida_contem_toda_lista_de_chaves_do_cenario_em_ordem` e o teste do comparador ficariam vacuamente
     verdes para a lista nova: estenda-os às variantes com o bloco.
   - O catálogo de diagnósticos (`test_diagnosticos_do_catalogo_sao_exatamente_os_do_classificador`) passa a somar
     `avaliar._CHAVES_DA_CONSERVACAO`, derivado, nunca escrito à mão.

**Testes:**
- **As duas variantes:**
  - o bloco sai publicado;
  - a chave acende só onde o motor emite `ALERTA`;
  - `gap_%` é o do motor.
- **Sem o bloco:** nenhum cenário publica `conservacao_capital`.
- **Cada recusa**, e as células novas da matriz: × equity, × rampa, × firm com métrica NOPAT.
- **Paridade do espelho contra o motor:** problemas novos no gerador, com o gap abaixo e acima de 10%, e a fixture
  regenerada byte a byte. Confira em qual harness o problema entra (motor × wrapper).
- **Fachada:**
  - a variante reproduz a lista em ordem;
  - editar `da` através do limiar acende e apaga a chave na mesma chamada, no molde de
    `test_a_divergencia_de_base_do_degrau_acende_e_apaga_com_o_preco_na_mesma_chamada`;
  - uma lista publicada adulterada deixa o comparador vermelho, nomeando cenário e caminho.

**Falseabilidade:**
- limiar do espelho de 0,10 para 0,20 → a paridade fica vermelha no problema acima do limiar;
- tire a lista de `listaExibida` → a trava estendida fica vermelha;
- deixe de comparar a lista → o teste da adulteração fica vermelho.

---

## Task 4: o contrato e as regras da §11 da Valuation (sem render)

**Files:**
- `skills/er-relatorio/scripts/entrega.py`, `placeholders.py`, `qc.py`, `assets/i18n/pt-BR.json`;
- `skills/er-relatorio/SKILL.md`: o contrato, a tabela de QC e a "Cobertura da §11";
- `tests/relatorio_apoio.py`, `tests/test_relatorio_cobertura_11.py`, `tests/test_relatorio_tese.py`,
  `tests/test_relatorio_contrato.py`;
- `tests/test_relatorio_valuation.py` (novo);
- o exemplo executável do `skills/er-relatorio/SKILL.md` e os testes que montam `analise` à mão (grep por
  `premissas_decisivas` em `tests/`).

**Interfaces — consome:** Tasks 1–3. **Produz:**
- **No contrato:** `analise.o_que_esta_no_preco: {julgamento, observavel}` (D12) e
  `analise.premissas_decisivas[].parte` (D13).
- **Na lista de prosa:** `analise.o_que_esta_no_preco.julgamento` e `.observavel`, e `resultados.cenarios.<nome>.ancora`
  (D9).
- **No QC:** os códigos da tabela abaixo e `qc.TOLERANCIA_DE_SENSIBILIDADE_POUCO_INFORMATIVA = 0.01`.
- **No apoio:**
  - `montar_entrega` compõe `o_que_esta_no_preco` sem dígito quando `resultados.reversa` existe;
  - compõe âncoras com os dígitos marcados por `{{livre:...}}`;
  - `completar_ledger` usa o caminho da parte.

**As regras:**

| Código | Nível | Gatilho |
|---|---|---|
| `conservacao_de_capital_nao_fecha` | REQUIRED DISCLOSURE | Um por cenário cujo `conservacao_capital.diagnosticos_chaves` contém a chave de `catalogo.disclosures.conservacao_de_capital`. Leva `gap_%` publicado (`pp1`), o rótulo do ano-base e o texto do catálogo |
| `premissa_central_fora_do_ponto_central_da_grade` | REQUIRED DISCLOSURE | Uma por grade 1D ou 2D fora do centro de D11. Nomeia o cenário da grade, o da manchete e os eixos que falharam |
| `sensibilidade_pouco_informativa` | QUALITY WARNING | Uma por grade cujas células ficam todas dentro da tolerância do preço publicado do cenário perturbado |
| `eixo_obrigatorio_da_reversa_sem_raiz` | REQUIRED DISCLOSURE | Eixo que `catalogo.eixos_de_reversa` declara `obrigatorio`, publicado com `resolucao.resolveu` falso. Leva o rótulo do eixo e o de `leitura.motivo` |
| `eixos_de_reversa_desconhecidos` | HARD FAIL | `resultados.reversa` presente e o catálogo sem `eixos_de_reversa` na forma: a regra acima falha fechada |
| `multiplos_com_bases_diferentes` (existente) | HARD FAIL | Também `manchete.multiplo_forward.base` ≠ `mercado_tela_forward.base`, quando os dois existem |
| `premissa_decisiva_fora_do_cenario` (existente) | HARD FAIL | Com `parte`: a parte não está em `resultados.sotp.partes`, ou a chave não é premissa da rota dela declarada nela |
| `vinculo_fora_do_vocabulario` (existente) | HARD FAIL | O vocabulário passa a incluir as premissas das rotas das partes |

**Forma** (código 1, com `difflib`):
- `o_que_esta_no_preco` é obrigatório com `resultados.reversa` e proibido sem ela;
- `julgamento`, `observavel` e `parte` são textos não vazios.

**Armadilhas:**
1. **Nenhum limiar de metodologia no QC.**
   - A conservação acende pela chave que o catálogo nomeia, no molde de `_achados_divergencia_de_base`.
   - O eixo obrigatório sai da flag, nunca do nome `custo_capital`.
   - Um bloco `conservacao_capital` sem `diagnosticos_chaves` é HARD FAIL `diagnostico_sem_chave`:
     `_pares_diagnosticos` só vê pares com `diagnosticos`, e o disclosure não pode sumir calado.
2. **Meça antes de mexer num `achados == []`.**
   - **O que já se sabe:** o eixo `roic` da grade 2D de `caso_reversa_firm` tem quatro pontos (10, 12, 14, 16) em torno
     de 12. O disclosure do ponto central é correto ali, e os testes sobre essa fixture passam a esperá-lo, nomeado.
   - **O que falta medir:** a reversa que o apoio compõe nas outras fixtures pode ficar sem raiz ou acender
     `iso_nao_calculada`. Rode o QC fixture a fixture antes de mudar qualquer expectativa.
3. **A âncora entra na lista de prosa, e todo caso cru de fixture passa a reprovar.** As âncoras das fixtures têm dígito
   ("média normalizada 2023-2025"). O apoio compõe as âncoras marcadas, mas os testes que embutem um caso de fixture sem
   passar por `montar_entrega` escapam dessa composição: o exemplo executável do `SKILL.md` e todo teste que usa
   `carregar_caso` ou `resultados_de` direto (grep em `tests/test_relatorio_*.py`). Leve-os pela mesma composição;
   nunca tire a âncora da lista para eles passarem.
4. **O caminho da premissa de parte** (`sotp.partes.<índice>.premissas.<chave>`, com o índice da parte em
   `resultados.sotp.partes`) segue a forma que a onda da 5E der a `qc._caminho_da_premissa_no_caso`. **A conferir
   depois da onda de correção da 5E.**
5. **A tabela da §11:**
   - as três linhas com pendência **5F** passam a citar `conservacao_de_capital_nao_fecha`,
     `premissa_central_fora_do_ponto_central_da_grade` e `sensibilidade_pouco_informativa`, com "—" na pendência;
   - `eixo_obrigatorio_da_reversa_sem_raiz` e `eixos_de_reversa_desconhecidos` entram na tabela dos códigos de fora da
     §11;
   - `tests/test_relatorio_cobertura_11.py` tira `5F` de `DONOS_PERMITIDOS`.

**Testes:**
- **A forma:** uma recusa por campo novo.
- **Cada regra**, com um caso que dispara e um vizinho que não dispara:
  - a grade de comprimento ímpar centrada na premissa não dispara;
  - com o meio deslocado, dispara;
  - a que perturba outro cenário, dispara;
  - a grade achatada acende o warning, e a de `caso_reversa_firm` não. Para achatar, reescreva as células publicadas de
    uma grade com o preço do cenário e confira só o código do warning (`_do_codigo`). O hash do caso deixa de bater,
    e esse outro código fica fora da asserção.
- **SOTP**, sobre `caso_sotp_safra`:
  - `util` da parte "Base instalada" como premissa decisiva e como vínculo emite;
  - parte inexistente é HARD FAIL;
  - premissa fora da rota da parte é HARD FAIL.
- **Dígito solto:** no julgamento e na âncora, `numero_sem_proveniencia`.
- **A trava da §11**, verde com a tabela nova.

**Falseabilidade:**
- decida a conservação por um limiar do relatório em vez da chave → vermelho no teste que troca só o catálogo, no
  molde de `test_o_qc_le_a_declaracao_afeta_e_nunca_o_nome_da_chave`;
- aceite grade de comprimento par como centrada → vermelho;
- volte o vínculo ao vocabulário da rota do caso → o teste do SOTP fica vermelho;
- deixe uma linha com pendência **5F** → a trava da §11 fica vermelha.

---

## Task 5: a aba Valuation na ordem da §9

**Files:**
- `skills/er-relatorio/scripts/render.py`, `assets/template.html`, `assets/i18n/pt-BR.json`;
- `skills/er-relatorio/SKILL.md`: a seção da aba Valuation e a Conclusão da Tese;
- `tests/test_relatorio_valuation.py`, `tests/test_relatorio_render.py`, `tests/test_relatorio_tese.py`,
  `tests/test_relatorio_svg_js.py`, `tests/test_relatorio_laboratorio.py`.

**Interfaces — consome:** Tasks 1–4.

**O que renderiza** (D15, na ordem):
1. **Cabeçalho:**
   - o que já existe: preço, upside, rota e convenção;
   - a faixa piso–teto de `analise.faixa`, quando declarada;
   - o múltiplo justo × a tela, corrente e forward. O forward de tela leva o período e a fonte da métrica, ou "métrica
     forward não declarada".
2. **Como o valor é formado** (`<details>` fechado):
   - cada passo de `catalogo.formacao_do_valor.<rota>`, com o rótulo e a unidade da premissa, o valor do cenário da
     manchete e a função;
   - os múltiplos publicados;
   - a síntese.
   - No SOTP, o rótulo do consolidado. No degrau, o rótulo "antes do degrau": os múltiplos do cenário são os sem degrau
     (pendência 2 da 4C).
3. **Cenários:** nome, âncora pela lista de prosa, triângulo rotulado, preço e upside.
4. **Laboratório:** sem mudança.
5. **Ponte:** o waterfall, com a escala.
6. **Sensibilidades:** a tabela de cada grade 1D (D10) e a matriz de cada grade 2D.
7. **O que está no preço** (com a nota "congelado nas premissas originais"):
   - cada eixo pelo rótulo, com as raízes pela `unidade` da leitura, a identificação rotulada e o intervalo;
   - a curvatura, quando a identificação é fraca;
   - os tangenciais;
   - o CAP;
   - o beta implícito, com a posição, a distância e a banda;
   - o teto, com o rótulo do múltiplo e o texto do catálogo;
   - a limitação da iso, quando publicada;
   - o julgamento e o observável.
   - Sem reversa, o rótulo da limitação publicada.
8. **Na Tese:**
   - o par forward na Conclusão, por `_multiplos_html`;
   - a premissa decisiva de parte, com o número da parte e o nome dela;
   - o vínculo rotulado pela rota que o contém.

**Armadilhas:**
1. **O bootstrap pareia matriz por posição** (achado 14). Antes de reposicionar os painéis, faça o bootstrap parear
   pelo `data-painel-indice` que o host já carrega, com o teste da 5D adaptado: host fora de ordem e índice sem spec.
2. **Toda conclusão de valor nova sai por `_rotulo_do_numero`**, com a forma condicional no dicionário:
   - o múltiplo justo forward;
   - os múltiplos da formação do valor;
   - os preços da tabela 1D;
   - na rampa, `vp_fase1` e `valor_fase2_no_ano_T`.

   `test_sob_fronteira_nenhum_numero_de_valor_sai_com_rotulo_incondicional_nas_abas_tese_e_valuation` passa a varrer os
   rótulos novos.
3. **A escala entra só onde a unidade a declara:**
   - nos valores originais da rampa no laboratório;
   - nas premissas decisivas;
   - no waterfall, com o sufixo na receita que o `svg.js` recebe;
   - nos montantes da formação do valor.

   Nunca em preço por ação. Sem `resultados.escala_monetaria`, nada muda.
4. **Nenhum código cru e nenhuma prosa do motor na Valuation.**
   - Motivo, identificação, posição, eixo, ano-base e `rir` saem pelo rótulo do catálogo.
   - `sem_solucao`, `sugestao`, `leitura` e `algebra` nunca aparecem.

**Testes, sobre o texto que o analista lê:**
- a ordem das seções da aba;
- `caso_reversa_firm`:
  - os quatro eixos com a raiz formatada e a identificação rotulada;
  - o beta com posição e banda;
  - a grade 1D de WACC com o ponto do cenário marcado;
- `reversa_sem_raiz`: o motivo rotulado nos três eixos, o teto e a limitação da iso;
- `forward_firm`: o par forward no cabeçalho e na Conclusão da Tese, com o período da métrica;
- `escala`:
  - "milhões" no waterfall e no valor original da rampa;
  - nunca no preço por ação;
- a formação do valor nas três rotas, com a síntese;
- sob fronteira, os rótulos condicionais dos números novos;
- SOTP: a premissa decisiva de parte e o vínculo multi-rota rotulados.

**Falseabilidade:**
- renderize o `motivo` cru → vermelho;
- aplique a escala a toda unidade com formato `moeda`, inclusive preço por ação → vermelho;
- tire o rótulo condicional do múltiplo justo forward → a varredura sob fronteira fica vermelha;
- volte o pareamento das matrizes à posição com um host fora de ordem → vermelho.

---

## Revisão final da fatia

Uma só, depois da Task 5. Carregue para ela:
- **A leitura da reversa diz o mesmo que o motor?**
  - raiz × identificação;
  - o CAP decrescente;
  - os tangenciais;
  - a identificação indisponível.
- **Sob fronteira de escopo:**
  - algum número novo da aba escapa do rótulo condicional?
  - o teto do crescimento gratuito vira preço-alvo? Hoje `reversa.**` fica fora do mapa.
- **A conservação no laboratório:**
  - anda com `da`, `g` e `roic`?
  - o badge compara a lista nova?
- **O par forward** pareia base e período?
- **A escala** entra em algum preço por ação?
- **A regra do ponto central:**
  - dispara em grade legítima?
  - cala numa grade descentrada?
- **Limiar de metodologia** sobrou no relatório?
- **As variantes compostas** escondem padrão ocioso nas travas?
- **A premissa de parte** abre caminho para parte ou premissa inexistente, ou para contraprova no caminho errado?
- **Algum `achados == []`** foi afrouxado?

---

## As fatias seguintes — escopo e decisões a confirmar agora

Planejadas depois da revisão da 5F, com o código conferido de novo, como na 5D e na 5E.

### 5G — as alternativas que o wrapper roda (≈ 3 tasks: integração das escolhas; integração do retorno exigido, do ponderado e do cross-check; relatório)

- **G1 — Painel de escolhas metodológicas** (§8.2, §5; vendor §5b, item 4: as dez).
  - **O bloco no caso:** `escolhas_metodologicas[]`, com:
    - `chave`, do vocabulário das dez;
    - `no_caso_base` ∈ `central`, `alternativa`;
    - as sobreposições que a chave admite, sobre o cenário da manchete;
    - `gatilho_disparou` com o observável, nas quatro com gatilho (§8.2).
  - **O que o wrapper publica:** o preço da alternativa, o impacto (fração), `material` (limiar ~10% do wrapper, nunca do
    relatório) e o empilhamento (duas ou mais fora da central na mesma direção).
  - **O catálogo:** as dez chaves, com o rótulo, o gatilho e as sobreposições admitidas, travado contra o gate.
  - **A entrega:** `analise.escolhas[{chave, razao}]` em prosa, e HARD FAIL para escolha publicada sem razão.
  - **A confirmar:**
    - a leitura de capacidade muda a rota: alternativa como vetor completo de outra rota, ou fora do painel?
    - a alavanca de lucro depende do degrau;
    - quem decide o gatilho: declaração do analista com observável, ou avaliação do wrapper?
- **G2 — Retorno exigido** (§8.2).
  - **O campo:** `retorno_exigido.taxa`, em pp.
  - **O que o wrapper faz:** precifica o cenário da manchete com a taxa na premissa de custo de capital da rota;
    recusado com SOTP e com degrau.
  - **O rótulo:** "não é fair value".
  - **A confirmar:** na rota firm, a taxa entra como WACC. O retorno exigido pelo acionista é Ke, e convertê-lo pede Kd e
    D/E (`kewacc`/`apv`, precomputados).
- **G3 — Valor ponderado por probabilidade.**
  - **O campo:** `pesos_de_probabilidade {cenario: pp}`, somando 100, com dois cenários ou mais; recusado com SOTP.
  - **Quem compõe:** o wrapper compõe a soma dos pesos × preços, que é "composição de cenários" (§4.2). O relatório nunca
    a calcula.
  - **Os pesos** ficam fora dos insumos: julgamento fora da fórmula.
- **G4 — Cross-check por segundo método** (§8.1).
  - **O bloco no caso:** `cross_check` com o vetor da rota oposta (métrica, âncora, triângulo, premissas e o `kd` que as
    identidades pedem); a ausência é declarada em `analise.cross_check.ausente.razao`.
  - **O que o wrapper faz:** precifica e passa as variáveis cruzadas ao motor. As identidades 1–3 do `coerencia_vetor`,
    hoje inalcançáveis, passam a disparar → chaves novas no classificador.
  - **Onde vale:** firm e equity.
  - **Registrado:** o vendor diz "múltiplo de saída sobre t+2, ou soma das partes no híbrido", e o desenho, "rota oposta".
    O desenho vence.
- **G5 — Re-teste da hipótese terminal** (vendor §5b, item 4: "uma linha mesmo quando não muda nada").
  - **O campo:** `analise.reteste_terminal {resultado, texto}`, com `resultado` ∈ `mantida`, `trocada`, vocabulário de
    processo em `entrega.py`.

### 5H — o produto Leitura de preço e o confronto temporal (≈ 2 tasks: integração; relatório)

- **H1 — Nível implícito e confronto temporal** (vendor, "Fluxo por tipo de pedido", item 3; `aplicacao.md` §4).
  - **O bloco no caso:** `reversa.consenso {t1: {valor, periodo}, t2?}`, com a métrica do mesmo tipo da base, como
    insumos. O wrapper não lê o ledger.
  - **O que o wrapper faz:** roda `nivel` com o valor de mercado (a conta de `alvo_de_mercado`) e o múltiplo justo
    corrente do cenário da reversa.
  - **O que publica:** `reversa.nivel_implicito`, com `leitura_chave` extraída do motor (`antecipacao_temporal`,
    `acima_do_consenso`), rotulada pelo catálogo.
- **H2 — O produto** (§5).
  - **O campo:** `execucao.produto` ∈ `analise`, `leitura_de_preco`, obrigatório.
  - **Sob `leitura_de_preco`:**
    - `analise` traz conclusão, consenso, `o_que_esta_no_preco` e exhibits;
    - as regras da Tese ficam fora;
    - a reversa é obrigatória mesmo sob limitação (HARD FAIL);
    - os avisos obrigatórios vão para o topo da aba.
  - **Decidido pelo controlador (15/09):** a entrega fica **só com a Valuation**. A §5 diz literalmente "Entrega
    reduzida à aba Valuation". A auditabilidade da §18.5 segue garantida:
    - o QC continua exigindo a proveniência;
    - o ledger e a `ficha-tecnica.json` continuam gerados na raiz da execução.
  - **A decidir no plano da 5H:** se as conclusões de valor saem como leitura condicional, reusando
    `render._leitura_condicional` com um segundo gatilho, e se a conclusão sai sem preço-alvo. A §5 inclina para o sim:
    o produto é a leitura do que o preço embute, não um fair value de manchete.

### 5I — sem dono hoje

Achado 15:
- reversa e sensibilidades ao vivo (§8.4), com a recusa de domínio da 4C na reversa;
- triângulo como controle (§8.3, §15.15);
- ponte editável no degrau do waterfall (§9, §15.15);
- cadeia de derivação inline, compondo do registro do ledger que sustenta cada premissa (claim, fórmula, fonte), sem
  prosa nova;
- iso ligada;
- badge no cabeçalho. Fica na 5I, e não na Task 5: o bootstrap acha o badge dentro da raiz do laboratório
  (`laboratorio.js:389`, `raiz.querySelector("[data-laboratorio-badge]")`), e subi-lo mexe no bootstrap da paridade;
- teto da alavanca rotulado como não-cenário;
- `avisos_dominio` da rampa no espelho.
