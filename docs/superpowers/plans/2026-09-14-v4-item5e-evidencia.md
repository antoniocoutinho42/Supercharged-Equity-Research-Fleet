# Item 5, fatia E — a aba Evidência: o ledger, a proveniência dos insumos e a §11 com dono

> **Para agentes:** REQUIRED SUB-SKILL: `superpowers:subagent-driven-development`.
>
> **Calibragem de rigor em vigor** (ledger, 26/08/2026, e a lição de 14/09):
> - implementação simples;
> - testes que discriminam a matemática e os contratos;
> - sem revisor por task, e **uma** revisão final da fatia;
> - achado não material: registre e siga — mas **meça antes de rotular como não material**.

**Goal.** A aba Evidência deixa de ser log e ficha opaca e vira a camada de auditabilidade da §9: ledger completo,
fontes, reconciliações, lacunas e limitações, confronto com a análise fornecida e ficha técnica. O builder passa a
recusar emitir quando:
- um número que move o valuation não tem proveniência;
- um número diverge do ledger sem reconciliação;
- um conflito entre fontes foi silenciado.

A entrega passa a declarar o que a §11 manda declarar: estimativa no lugar de dado, contraprova ausente, lacuna
material e consenso indisponível. E todo item da §11 ganha dono.

**Architecture.** Três camadas donas, e o relatório lê as três.
- **Evidência.** A §3.2 faz do `er-evidencia` o **dono do schema do ledger**, então o contrato `ledger/1` mora em
  `skills/er-evidencia/assets/contrato_ledger.json`, como dado.
- **Integração.** Declara quais números do caso são insumo do valuation (`catalogo.insumos_do_caso`) — o relatório
  nunca decide isso pelo nome do campo, a lição da D3 da 5D.
- **Relatório.** Valida a forma pelo contrato lido, aplica a §11 e renderiza.

**Fontes:** `docs/desenho-arquitetura-v4.md`:
- §3.2 (`er-evidencia`: "dona do schema do ledger, da hierarquia por claim, da reconciliação e da classificação de
  gaps");
- §6 (princípio da fonte, contrato por registro, regras);
- §9 (aba Evidência; consenso na Tese);
- §11;
- §12 (quarentena, confronto, contrato do builder);
- §15, decisões 10 e 20;
- §18, regras 5 e 9.

## O mapa do item 5

| Fatia | Entrega |
|---|---|
| 5A–5D | **completas**: contratos e builder; gráficos; laboratório ao vivo; aba Tese |
| **5E** (este plano) | Aba Evidência; `ledger/1` do `er-evidencia`; insumos do caso declarados pela integração; as regras da §11 que dependem do ledger; consenso na Tese; confronto; ficha técnica em arquivo; a tabela que dá dono a todo item da §11 |
| 5F | Sem mudança de escopo: o restante da aba Valuation, o múltiplo de tela forward e a conservação de capital. Mais os dois itens da §11 que são da Valuation: premissa central fora do ponto central da grade e sensibilidade pouco informativa |

## Global Constraints

- **As regras da 5A–5D continuam valendo:**
  - E3 mecanizada pelo teste de fronteira;
  - nenhuma aritmética de valuation fora do motor — comparar números declarados é permitido;
  - HARD FAIL não emite;
  - raiz única;
  - texto de interface só pelo dicionário ou catálogo;
  - determinismo byte a byte;
  - autocontenção;
  - CSS sem faixa lateral.
- **Nenhum vocabulário de evidência escrito no relatório.** Classes de fonte, estatutos, materialidades e âncoras do
  consenso vêm do `contrato_ledger.json`, e os rótulos vêm do dicionário, com trava de cobertura. Quais números do
  caso exigem proveniência vem do catálogo.
- **Todo campo de texto novo que a Tese exibe entra em `placeholders.campos_de_prosa`**, a lista única lida pelo QC,
  pelo log e pela tela. Os textos do ledger e do confronto são **dado da Evidência** (§9: linguagem interna
  permitida) e ficam fora da prosa auditada. A Tese só mostra deles:
  - os campos estruturados dos registros de consenso;
  - o `claim` do disclosure de insumo estimado.
- **Não edite `tests/fixtures/caso_*.json`.** O `relatorio_apoio` compõe o que falta.
- **Asserções sobre o texto que o analista lê** (`apoio.prosa_da_pagina`), nunca atributo e nunca a página inteira.
- **Operação:**
  - `vendor/` read-only.
  - Suíte **desanexada** (passa de 10 min):
    `python -m pytest tests -q > .superpowers/sdd/<log> 2>&1; echo EXIT=$? >> .superpowers/sdd/<log>`. Confirme
    que o processo subiu e espere a notificação.
  - Não rode a suíte para confirmar a baseline: **1025 passed, 1 skipped**.
  - Commit assim que `EXIT=0`, antes do relatório; um commit por task.
  - Mutação, teste e restauração num único comando.

## Decisões de desenho — tomadas, com a razão

- **D1 — `ledger/1` é contrato do `er-evidencia`, publicado como dado.**
  - **O asset.** `skills/er-evidencia/assets/contrato_ledger.json` declara as chaves de cada nível (obrigatórias e
    opcionais) e os vocabulários fechados:
    - `classes_de_fonte`, pela §6.1: `filing`, `ri`, `release`, `transcript`, `apresentacao`, `regulador`, `api`,
      `relatorio_setorial`, `governo`, `imprensa_especializada`, `web`, `documento_do_usuario`,
      `resposta_do_usuario` (§18.9: resposta do usuário é evidência a verificar);
    - `estatutos` = `reported`, `calculated`, `estimated` (§6.2);
    - `materialidades` = `material`, `nao_material` (§6.3);
    - `ancoras_do_consenso` = `guidance`, `historico_normalizado`, `run_rate`, `pares` (§6.3).
  - **Sem `SKILL.md` nesta fatia.** A doutrina e o agente são do item 7, e o plugin descobre skill por `SKILL.md`
    (o `plugin.json` não lista skills). Um diretório só com o contrato não vira meia skill.
  - **Como o builder lê.** Pela mesma constante dos assets externos (`ASSETS_DA_INTEGRACAO["contrato_ledger"]`). A
    trava E3 passa a cobrir `er-evidencia`: o nome só aparece nessa constante, e nenhum asset do relatório copia o
    contrato.
  - **A forma** (código 1, sugestão por `difflib`):
    - ledger: `{versao_contrato: "ledger/1", registros: [...], lacunas: [...]}`;
    - registro: `{id, claim, fonte: {identidade, classe}, localizador: {tipo ∈ {url, documento, endpoint}, valor,
      parametros?}, data_acesso (AAAA-MM-DD), periodo, moeda (texto ou null), unidade, estatuto, formula?,
      insumos?, valor (número ou null), justificativa_da_fonte, usado_em?, reconciliacao?, conflito?,
      contraprova_de?}`;
    - `formula` é obrigatória **se e só se** `calculated`; `insumos` (ids) só com `calculated`;
    - `usado_em` exige `valor` numérico;
    - `conflito` = `{vencedor, razao}`; `reconciliacao` = `{texto}`; `contraprova_de` é um id;
    - lacuna: `{id, descricao, materialidade, tratamento}`;
    - id repetido é recusa.
- **D2 — Quais números do caso exigem proveniência: a integração declara.**
  - **O mapa.** `catalogo.insumos_do_caso` é uma lista de padrões de caminho do caso (`*` casa exatamente um
    segmento), com a mesma gramática de `conclusoes_de_valor`. O casador de padrão do `placeholders.py` é
    **fatorado e reusado**, nunca duplicado.
  - **Todo insumo mapeado é material.** Um limiar de materialidade seria o relatório estimando impacto no valuation,
    e a §18.5 quer proveniência para todo número material. Quem diz o que é insumo é a integração.
  - **Travas na integração**, em `tests/test_catalogo_apresentacao.py`, no molde das de `conclusoes_de_valor`:
    - fixture a fixture, toda folha numérica do caso é insumo pelo mapa **ou** tem razão declarada em
      `_NAO_SAO_INSUMOS` (pontos declarados de grade, configuração da reversa, limites) — nunca as duas, nunca
      nenhuma;
    - todo padrão do mapa é exercido por alguma fixture.
- **D3 — As regras da §11 que dependem do ledger.**
  - **HARD FAIL, código 2:**
    - `insumo_sem_proveniencia`: caminho do caso coberto pelo mapa sem registro cujo `usado_em` o nomeie
      (§11: "número material do valuation sem proveniência").
    - `usado_em_fora_dos_insumos`: caminho de `usado_em` que o caso não tem ou que o mapa não declara. A ligação é
      falsa.
    - `insumo_nao_reconciliado`: registro cujo `valor` difere do número do caso num caminho do seu `usado_em`, sem
      `reconciliacao`. A comparação é igualdade entre dois números declarados, com tolerância relativa e piso
      absoluto em constante nomeada (§6.2: "reconciliação dos números materiais").
    - `conflito_de_fontes_silenciado`: registros com o mesmo `claim` e `periodo` e `valor` diferentes (mesma
      tolerância), sem nenhum deles declarar `conflito.vencedor` dentre os ids do grupo (§6.3: "nunca é
      silenciado").
    - `referencia_fora_do_ledger`: id citado que o ledger não tem. Vale para `insumos`, `conflito.vencedor`,
      `contraprova_de`, `analise.consenso.registros` e `dados.<id>.ledger`.
    - `dataset_sem_proveniencia`: dataset de `dados` usado por série `direta` ou `derivada` com `ledger` vazio. Hoje
      `dados.<id>.ledger` só tem o tipo (§11: "gráfico com dados não rastreáveis").
  - **REQUIRED DISCLOSURE:**
    - `insumo_estimado`: um por registro `estimated` que sustenta um insumo, citando o `claim`.
    - `sem_contraprova_independente`: premissa decisiva da Tese (`analise.premissas_decisivas`) sem registro de
      contraprova. Isto é: nenhum registro com `contraprova_de` apontando para um registro que a sustenta vindo de
      **outra** `fonte.identidade` — cópia da mesma fonte não conta (§6.3). O rótulo da premissa vem do catálogo.
      O caminho da premissa no caso é o do cenário da manchete; confira em `qc.py` como
      `premissa_decisiva_fora_do_cenario` já a encontra, e use o mesmo leitor.
    - `lacuna_material`: um por lacuna `material` (§11: "gap material que não inviabiliza o valuation").
    - `consenso_indisponivel`: com a âncora substituta e a frase de que o confronto temporal da reversa fica
      indisponível (§6.3).
    - **A mensagem de um disclosure que cita texto de prosa** leva no achado o **campo** da prosa. A Tese exibe o
      texto resolvido pela lista de prosa, nunca o cru com `{{...}}`.
  - **QUALITY WARNING:**
    - `concentracao_de_fontes`: uma `fonte.identidade` sustenta mais da metade dos insumos mapeados, quando há ao
      menos quatro. Os dois limiares são constantes nomeadas no `qc.py`: é regra de QC do Fleet, não metodologia.
- **D4 — Consenso na Tese** (§9: "consenso como referência externa"; §6.3).
  - **O contrato.** `analise.consenso` é obrigatório: `{registros: [ids]}` **ou** `{ausente: {ancora, razao}}`,
    nunca os dois. A `razao` é prosa da Tese.
  - **O que a Conclusão mostra:** uma linha de referência externa com `claim`, período, valor e unidade, fonte e
    data de acesso de cada registro. O valor é formatado pelo idioma, sem conta.
  - **Sob fronteira de escopo o consenso continua.** É leitura de mercado, como o múltiplo de tela (§14). Fica
    registrado para a revisão medir se isso vira preço-alvo de manchete.
- **D5 — Confronto com a análise fornecida** (§12, decisão 20).
  - **O contrato.** `confronto` é opcional na raiz: `{analise_fornecida: {identificacao, data}, divergencias:
    [{item, classificacao, anterior, atual, explicacao}]}`, com `classificacao` ∈ {`dado_novo`, `premissa_revista`,
    `erro_anterior`, `pergunta_resolvida`}.
  - **Onde o vocabulário mora.** Em `entrega.py`: é processo do Fleet, como o vocabulário da Tese.
  - **O que exige o quê.** `analise.mudou_desde_analise_fornecida` exige `confronto` (forma, código 1): o que mudou,
    sem o confronto que o sustenta, é afirmação solta.
- **D6 — A ficha técnica é composta pelo builder, nunca declarada** (§9: "gerada com a execução"; §15, decisão 10:
  "também em arquivo").
  - **Sai do contrato.** `entrega.ficha_tecnica` sai do `entrega/1`.
  - **O que o builder compõe:**
    - a execução (id, ticker, idioma);
    - de `resultados.origem`: a metodologia com a versão e `caso_sha256`;
    - as versões dos contratos consumidos (`entrega/1`, `resultados/1`, `catalogo/1`, `ledger/1`);
    - a contagem de registros por estatuto e por classe de fonte;
    - o resumo do QC por nível e código.
  - **Arquivo.** Grava `ficha-tecnica.json` ao lado de `relatorio.html` só quando emite. A limpeza da saída
    anterior o inclui; num HARD FAIL continua saindo só `qc.json`.
  - **Registrado para o item 8:** gates declarados e comandos executados. Hoje nenhum produtor os tem, e inventar o
    formato agora é o que a §12 proíbe.
- **D7 — A aba Evidência** (§9), nesta ordem:
  1. fontes: identidades distintas, com classe e número de registros;
  2. ledger, agrupado por `claim`, com:
     - estatuto, período, valor e unidade, moeda;
     - data de acesso, localizador e justificativa da fonte;
     - fórmula e insumos;
     - reconciliação, conflito e contraprova;
  3. lacunas e limitações declaradas: as lacunas do ledger, `resultados.limitacoes` e a fronteira de escopo, com
     os rótulos do catálogo;
  4. confronto, se houver;
  5. ficha técnica;
  6. metodologia, log de placeholders e rastreabilidade dos exhibits (os três já existem).

  Todo vocabulário do ledger aparece pelo rótulo do dicionário, **nunca pela chave crua** (a lição do B2).
- **D8 — A tabela que dá dono a todo item da §11** fica numa seção "Cobertura da §11" do
  `skills/er-relatorio/SKILL.md`.
  - **A linha.** Uma por item da §11 do desenho, com o nível e como é garantido: códigos de QC, mecanismo fora do QC
    (gate do caso, CI, badge do laboratório) ou pendência com dono (`5F`, `item 6` ou `item 8`) e razão.
  - **Códigos de fora da §11.** Uma segunda tabela lista os códigos de QC que servem a outras seções, como
    `relatorio_nao_autocontido` (§9).
  - **A trava** (`tests/test_relatorio_cobertura_11.py`) lê a §11 do desenho e as duas tabelas do `SKILL.md` e
    confere:
    - os itens de cada nível são iguais aos do desenho, com espaço e crase normalizados;
    - todo código citado existe no `qc.py` com aquele nível e tem mensagem no dicionário;
    - todo código do `qc.py` aparece numa das duas tabelas;
    - pendência só com dono do conjunto permitido.
  - **O conteúdo esperado.** A implementação confere contra o código e corrige onde o código disser outra coisa.

    **HARD FAIL**

    | Item da §11 | Como é garantido |
    |---|---|
    | paridade Python↔JS | CI (`tests/test_paridade_*.py`) e badge do laboratório que bloqueia a edição (5C). A verificação por caso no build fica pendente, dono **item 6**: o builder não roda node |
    | `selftest`/suíte | CI (`tests/test_vendor_multiplos_justos.py`). Por execução, pendente, dono **item 8**: o M4 exige "suíte PASS" |
    | número material sem proveniência | `insumo_sem_proveniencia`, `usado_em_fora_dos_insumos`, `numero_sem_proveniencia`, `placeholder_nao_resolvido`, `placeholder_malformado` |
    | gráfico não rastreável | `serie_nao_rastreavel`, `formula_invalida`, `serie_de_tamanho_incompativel`, `series_de_datasets_incompativeis`, `overlay_nao_resolvido`, `dataset_sem_proveniencia` |
    | inconsistência estrutural | `resultados_nao_correspondem_ao_caso`, `multiplos_com_bases_diferentes`, `unidade_desconhecida`, `formato_incompativel_com_unidade`, `diagnostico_sem_chave`, `degrau_sem_divergencia_de_base`, `faixa_fora_de_ordem`, `premissa_decisiva_fora_do_cenario`, e as recusas do gate do caso |
    | perguntas sem vínculo | `perguntas_da_tese_incompletas`, `vinculo_fora_do_vocabulario` |
    | reversa e custo de capital implícito | `analise_sem_reversa`, `limitacao_desconhecida`, e o eixo obrigatório no gate (`caso.EIXO_OBRIGATORIO`) |
    | conflito sem reconciliação | `insumo_nao_reconciliado`, `conflito_de_fontes_silenciado`, `referencia_fora_do_ledger` |
    | fronteira com fair value | `fronteira_com_preco_alvo`, `fronteira_de_escopo_desconhecida` |

    **REQUIRED DISCLOSURE**

    | Item da §11 | Como é garantido |
    |---|---|
    | conservação de capital | pendente, dono **5F** |
    | contraprova | `sem_contraprova_independente` |
    | ponto central da grade | pendente, dono **5F** |
    | gap material | `lacuna_material`, `consenso_indisponivel` |
    | metodologia especial ou escopo | `limitacao_metodologica`, `fronteira_de_escopo_declarada`, `divergencia_de_base_degrau` |
    | estimativa | `insumo_estimado` |

    **QUALITY WARNING**

    | Item da §11 | Como é garantido |
    |---|---|
    | exhibit fraco | `serie_curta_sem_nota_janela`; o resto pendente, dono **item 8** |
    | concentração de fontes | `concentracao_de_fontes` |
    | sensibilidade pouco informativa | pendente, dono **5F** |
    | dependência de uma premissa | `tese_dependente_de_uma_premissa` |
    | pergunta pouco discriminante | pendente, dono **item 8** |
    | P/N pouco ligados | pendente, dono **item 8** |
    | linguagem interna | pendente, dono **item 8**: a lista de banimento é da metodologia e entra pelo catálogo |
    | contagem de premissas na Conclusão | pendente, dono **item 8** |

**Fora desta fatia — registrado:**
- gates e comandos na ficha técnica (item 8);
- paridade por caso no build (item 6);
- os QUALITY WARNING de julgamento editorial (item 8);
- a doutrina de pesquisa, a hierarquia por claim e o agente `pesquisa-evidencia` (item 7);
- o confronto temporal da reversa contra o consenso (5F, "o que está no preço").

## File Structure

| Arquivo | Responsabilidade |
|---|---|
| `skills/er-evidencia/assets/contrato_ledger.json` (novo) | `ledger/1`: chaves por nível e vocabulários fechados |
| `skills/er-valuation/assets/catalogo_apresentacao.json` | `insumos_do_caso` |
| `skills/er-valuation/SKILL.md` | O mapa `insumos_do_caso`, onde o `er-analise` vai lê-lo |
| `skills/er-relatorio/scripts/entrega.py` | Ledger validado pelo contrato lido; `analise.consenso`; `confronto`; `ficha_tecnica` fora; `dados.<id>.ledger` como ids |
| `skills/er-relatorio/scripts/placeholders.py` | Casador de padrão fatorado; leitor de `insumos_do_caso`; `campos_de_prosa` estendido |
| `skills/er-relatorio/scripts/qc.py` | Regras de D3 |
| `skills/er-relatorio/scripts/builder.py` | `contrato_ledger` na constante de assets externos; `ficha-tecnica.json` |
| `skills/er-relatorio/scripts/render.py`, `assets/template.html`, `assets/i18n/pt-BR.json` | Aba Evidência (D7); consenso na Conclusão; disclosures com prosa resolvida |
| `skills/er-relatorio/SKILL.md` | Contratos novos; a tabela de D8 |
| `tests/relatorio_apoio.py` | Ledger e consenso padrão válidos para cada fixture |

---

## Task 1: os contratos — `ledger/1` do `er-evidencia` e os insumos da integração (sem relatório)

**Files:**
- `skills/er-evidencia/assets/contrato_ledger.json` (novo);
- `skills/er-valuation/assets/catalogo_apresentacao.json` e `skills/er-valuation/SKILL.md`;
- `tests/test_catalogo_apresentacao.py`;
- `tests/test_contrato_ledger.py` (novo).

**Interfaces — produz:** o asset de D1, com `versao_contrato: "ledger/1"`; `catalogo.insumos_do_caso: list[str]`.

**Testes:**
- as travas de D2 sobre **todas** as fixtures de caso;
- a forma do asset: vocabulários não vazios e sem repetição, chaves obrigatórias disjuntas das opcionais;
- `classes_de_fonte` travada por igualdade de conjunto contra a lista da §6.1 citada no teste.

**Falseabilidade:**
- tire um padrão do mapa → a trava de classificação fica vermelha nomeando a folha;
- acrescente um padrão que nenhuma fixture exerce → vermelha.

---

## Task 2: `entrega/1` com ledger, consenso e confronto; as regras da §11 do ledger (sem render)

**Files:**
- `entrega.py`, `placeholders.py`, `qc.py`, `builder.py`, `assets/i18n/pt-BR.json`;
- `tests/relatorio_apoio.py`, `tests/test_relatorio_fronteira.py`;
- `tests/test_relatorio_evidencia.py` (novo);
- os testes que hoje montam `"ledger": []`, `"ficha_tecnica": {}` ou datasets com `"ledger": []`;
- o exemplo executável do `skills/er-relatorio/SKILL.md`.

**Interfaces — consome:** Task 1. **Produz:**
- os códigos de D3;
- `apoio.montar_entrega(..., ledger=None, consenso=None)`: por padrão, compõe um ledger e um consenso válidos para
  a fixture.

**Três armadilhas — leia antes do primeiro teste:**
1. **O ledger padrão do apoio não pode, ele mesmo, disparar regra.**
   - Derive os registros **do mapa sobre o caso composto**, nunca de uma lista escrita à mão por fixture, para que um
     padrão novo se cubra sozinho.
   - Cada registro vem `reported`, com `valor` igual ao do caso e identidades distintas (senão
     `concentracao_de_fontes`).
   - As premissas decisivas da Tese padrão ganham registro de contraprova de outra identidade (senão
     `sem_contraprova_independente`).
   - O consenso vem com um registro, e cada dataset de `dados` ganha o registro que o sustenta.
   - Todo `achados == []` existente continua valendo **sem** ser afrouxado.
2. **Forma × conteúdo, como na 5D.** Chave desconhecida, tipo errado e campo obrigatório ausente são recusa de
   contrato: código 1, com `difflib`. As regras de D3 são achados de QC.
3. **O relatório não sabe o que é insumo nem o que é classe de fonte.** Tudo sai do catálogo e do contrato lido.
   `tests/test_relatorio_fronteira.py` passa a cobrir `er-evidencia`: o nome só aparece na constante, e nenhum asset
   do relatório espelha o contrato.

**Testes:**
- uma recusa de forma por nível novo;
- cada regra de D3 com um caso que dispara e um vizinho que não dispara;
- o disclosure com prosa carregando o campo, não o texto cru.

**Falseabilidade:**
- desligue `insumo_sem_proveniencia` → vermelho;
- aceite `valor` divergente sem `reconciliacao` → vermelho;
- conte a cópia da mesma identidade como contraprova → vermelho.

---

## Task 3: a aba Evidência, o consenso na Tese, a ficha técnica em arquivo e a tabela da §11

**Files:**
- `render.py`, `builder.py`, `assets/template.html`, `assets/i18n/pt-BR.json`;
- `skills/er-relatorio/SKILL.md`;
- `tests/test_relatorio_evidencia.py`, `tests/test_relatorio_render.py`;
- `tests/test_relatorio_cobertura_11.py` (novo).

**Interfaces — consome:** Tasks 1 e 2.

**O que renderiza:** D7 na ordem; a linha de consenso na Conclusão (D4); os disclosures de D3 na Tese com a prosa
resolvida; a ficha de D6 na Evidência e em `ficha-tecnica.json`.

**Testes, sobre o texto que o analista lê:**
- a ordem das seções da Evidência;
- um registro com todos os campos rotulados, sem chave crua;
- conflito e reconciliação visíveis;
- a lacuna material na Tese com um placeholder resolvido;
- a linha de consenso com valor, período, fonte e data;
- consenso ausente como disclosure com o rótulo da âncora;
- `ficha-tecnica.json` igual byte a byte em duas emissões e ausente num HARD FAIL;
- a trava de D8.

**Falseabilidade:**
- renderize a chave crua de uma classe de fonte → vermelho;
- tire um item da §11 da tabela → vermelho;
- cite um código que não existe → vermelho.

---

## Revisão final da fatia

Uma só, depois da Task 3. Carregue para ela:
- se `insumos_do_caso` cobre todo número que move o preço — um insumo fora do mapa é número material sem
  proveniência que passa calado;
- se o ledger padrão do apoio esconde alguma regra;
- se um insumo estimado ou uma premissa decisiva sem contraprova escapa do disclosure;
- se o consenso sob fronteira de escopo vira preço-alvo de manchete;
- se sobrou doutrina de evidência escrita no relatório, fora do contrato lido.
