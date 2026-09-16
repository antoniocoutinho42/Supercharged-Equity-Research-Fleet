# Item 5, fatia G — as alternativas que o wrapper roda

**Goal.** A aba Valuation passa a mostrar o que a §9 pede depois das sensibilidades: o painel de escolhas
metodológicas, o retorno exigido, o valor ponderado por probabilidade, o cross-check por segundo método e o
re-teste da hipótese terminal.

**Regime (15/09).** Implementar o que o desenho pede, sem abstração preventiva nem escopo novo. Um teste que
discrimina cada regra ou número novo; nada de mutation test nem fixture nova (variantes compostas no apoio).
Dois lotes, um commit por task, a suíte inteira uma vez por lote e uma checagem de blockers no fim da fatia.

**E3.** A matemática vem do motor; o wrapper compõe e publica. O relatório nunca calcula metodologia: todo número
sai de `resultados` ou do catálogo, e todo texto de dado sai por `render._texto_de_dado_html`.

**Fontes.** Desenho §5, §8.1, §8.2, §9, §11 e §18. Vendor (read-only): `references/aplicacao.md` §5b, itens 4 e 5
(as dez escolhas, o limiar de ~10% e a guarda anti-empilhamento); `SKILL.md`, item 4.

## Decisões

- **D1 — as escolhas são declaradas pelo analista; o wrapper precifica.**
  - O caso declara cada escolha: a chave, a posição no caso-base, as sobreposições da alternativa sobre o cenário
    da manchete e, quando a escolha tem gatilho, o observável que o disparou. O wrapper nunca avalia gatilho.
  - O wrapper precifica a alternativa sobre o cenário da manchete e publica preço, impacto e materialidade.
  - **Limiar:** `avaliar.LIMIAR_DE_ESCOLHA_MATERIAL = 0.10`, o limiar de ~10% do vendor, constante nomeada na
    integração. O relatório nunca o conhece.
  - **Vocabulário:** as dez do vendor, declaradas no catálogo com rótulo e com o gatilho descrito.
  - **Empilhamento:** o wrapper publica o alerta quando duas ou mais escolhas ficam fora da central na mesma
    direção — a guarda anti-empilhamento do vendor. A aba o mostra; nesta fatia não vira código de QC.
  - **Fora da v4, como dívida:** a leitura de capacidade, que trocaria a rota inteira, é recusada com mensagem
    nomeada. A alavanca de lucro só existe com degrau.
- **D2 — retorno exigido** (§8.2: que valor resulta ao exigir retorno de X%). Campo opcional com a taxa em pp. Na
  rota firm substitui o WACC; na equity, o Ke; sempre no cenário da manchete. Recusado com SOTP e com degrau. Sai
  rotulado como leitura, nunca como fair value.
- **D3 — valor ponderado.** Pesos opcionais por cenário, somando 100, com dois cenários ou mais; recusado com SOTP.
  O wrapper compõe a soma de peso × preço. Os pesos são julgamento, ficam fora dos insumos de proveniência (§8.2:
  fora da fórmula), e a aba diz que o número nunca substitui bear, base e bull.
- **D4 — cross-check pela rota oposta** (§8.1; o desenho vence o vendor, que aceita múltiplo de saída ou SOTP).
  Bloco opcional no caso com o vetor coerente da rota oposta; o wrapper o precifica e publica o preço e a diferença
  contra a manchete. A ausência é declarada em `analise.cross_check.ausente.razao`, opcional, em prosa auditada.
  Sem nenhum dos dois, a aba diz que o cross-check não foi declarado — sem regra de forma; a dívida é exigir isso
  no `er-analise`.
- **D5 — re-teste da hipótese terminal.** `analise.reteste_terminal {resultado, texto}`, opcional, com `resultado`
  em `{mantida, trocada}`, vocabulário de processo em `entrega.py`, e o texto em prosa auditada.

## Números novos a classificar nas travas do catálogo

- **Conclusões de valor:** `escolhas_metodologicas.*.preco_alternativa`, `retorno_exigido.preco_acao`,
  `valor_ponderado.valor` e `cross_check.preco_acao`. Sob fronteira de escopo, todos saem como leitura condicional.
- **Não são conclusão de valor:** `escolhas_metodologicas.*.impacto`, que é fração de comparação, e
  `cross_check.diferenca_vs_manchete`.
- **Insumos do caso:** `retorno_exigido.taxa`, `cross_check.metrica_base.valor` e `cross_check.premissas.*` exigem
  proveniência. Os pesos e as sobreposições não são insumo: são julgamento declarado.

---

## Lote A — integração

### Task 1: as escolhas metodológicas

**Arquivos:** `skills/er-valuation/scripts/caso.py` e `avaliar.py`; `assets/catalogo_apresentacao.json`;
`skills/er-valuation/SKILL.md`; `tests/relatorio_apoio.py`, com a variante `escolhas`;
`tests/test_valuation_caso.py`, `test_valuation_avaliar.py`, `test_valuation_matriz.py` e
`test_catalogo_apresentacao.py`.

**Produz:**
- **No caso:** `escolhas_metodologicas: [{chave, no_caso_base, sobreposicoes, gatilho_disparou?}]`, com
  `no_caso_base` em `caso.POSICOES_DA_ESCOLHA = {"central", "alternativa"}`, `sobreposicoes` mapeando premissa da
  rota para número e `gatilho_disparou: {observavel}` quando declarado.
- **Em `resultados`:** `escolhas_metodologicas: [{chave, no_caso_base, sobreposicoes, preco_alternativa, impacto,
  material, gatilho_disparou}]` e `empilhamento: {direcao, chaves} | null`.
- **No catálogo:** `escolhas_metodologicas.<chave> = {rotulo, gatilho}`, as dez do vendor, e a classificação dos
  números novos.

**Recusas nomeadas do gate:** chave fora do vocabulário do catálogo, com sugestão por `difflib`; chave repetida;
`sobreposicoes` vazia numa alternativa; sobreposição que não é premissa da rota; `no_caso_base` fora do
vocabulário; a escolha da leitura de capacidade; a alavanca de lucro sem degrau.

**Testes-chave:** o preço alternativo bate com o oráculo montado no teste, que é o cenário da manchete com as
sobreposições; o impacto e a materialidade nos dois lados do limiar; o alerta de empilhamento com duas escolhas na
mesma direção, e o silêncio com uma só; uma recusa por mensagem; o catálogo com as dez chaves e rótulo em todo
idioma.

### Task 2: retorno exigido, valor ponderado e cross-check

**Arquivos:** os mesmos da Task 1, mais `tests/test_valuation_contrato.py`.

**Produz:**
- **No caso:** `retorno_exigido: {taxa}`; `pesos_de_probabilidade: {<cenario>: pp}`; `cross_check: {rota,
  metrica_base: {tipo, valor}, ancora, premissas}`.
- **Em `resultados`:** `retorno_exigido: {taxa, premissa_substituida, preco_acao} | null`;
  `valor_ponderado: {valor, pesos} | null`; `cross_check: {rota, preco_acao, diferenca_vs_manchete} | null`.

**Recusas nomeadas do gate:** `retorno_exigido` com SOTP, com degrau, ou com taxa não finita ou fora de 0 a 100;
pesos que não somam 100, com um cenário só, com nome fora de `cenarios`, ou com SOTP; `cross_check` com a rota do
caso, com vetor incompleto para a rota oposta, ou com chave desconhecida.

**Testes-chave:** o preço do retorno exigido é o do cenário da manchete com a premissa de custo de capital
substituída, uma rota por vez; o ponderado bate com a soma de peso × preço; o cross-check bate com a precificação
do vetor oposto, e a diferença sai com o sinal certo; uma recusa por mensagem; sem os blocos, os três saem `null`
em toda fixture.

---

## Lote B — relatório

### Task 3: contrato e QC

**Arquivos:** `skills/er-relatorio/scripts/entrega.py`, `placeholders.py` e `qc.py`; `assets/i18n/pt-BR.json`;
`skills/er-relatorio/SKILL.md`, no contrato, na tabela de QC e na "Cobertura da §11"; `tests/relatorio_apoio.py`,
`tests/test_relatorio_valuation.py`, `test_relatorio_contrato.py` e `test_relatorio_cobertura_11.py`.

**Produz:**
- **No contrato, todos opcionais:** `analise.escolhas: [{chave, razao}]`; `analise.cross_check: {ausente: {razao}}`;
  `analise.reteste_terminal: {resultado, texto}`.
- **Na prosa auditada:** `analise.escolhas.<i>.razao`, `analise.cross_check.ausente.razao` e
  `analise.reteste_terminal.texto`.
- **No QC:**
  - `escolha_sem_razao`, HARD FAIL: chave publicada em `resultados.escolhas_metodologicas` sem razão declarada em
    `analise.escolhas`. Entra na tabela dos códigos de fora da §11, com a referência ao §8.2 e ao §18.3 — nenhuma
    escolha sem default recebe default;
  - `escolhas_desconhecidas`, HARD FAIL: `resultados.escolhas_metodologicas` publicado com o catálogo sem
    `escolhas_metodologicas` na forma. É falha fechada, no molde de `eixos_de_reversa_desconhecidos`.

**Testes-chave:** uma recusa de forma por campo novo; a escolha publicada sem razão reprova, e com razão passa; o
catálogo sem a seção reprova; a trava da §11 fica verde com a tabela nova; um dígito solto na razão é
`numero_sem_proveniencia`.

### Task 4: a aba

**Arquivos:** `skills/er-relatorio/scripts/render.py`; `assets/template.html` e `assets/i18n/pt-BR.json`;
`skills/er-relatorio/SKILL.md`; `tests/test_relatorio_valuation.py` e `test_relatorio_tese.py`.

**O que renderiza,** na ordem da §9:
1. **O painel de escolhas,** entre a ponte e as sensibilidades. Cada escolha sai com o rótulo do catálogo, a
   posição no caso-base, o preço alternativo, o impacto, a razão do analista e o observável do gatilho. A escolha
   com gatilho disparado ou material fica no nível principal; as demais, num `<details>` fechado. O alerta de
   empilhamento sai acima do painel.
2. **Depois do "o que está no preço", colapsados:** o retorno exigido, com o rótulo de que não é fair value; e o
   valor ponderado, com o rótulo de que não substitui bear, base e bull.
3. **Cross-check:** o preço da rota oposta e a diferença; ou a razão da ausência; ou a frase de que não foi
   declarado.
4. **Re-teste da hipótese terminal:** o resultado rotulado e o texto, quando declarado.

**Testes-chave:** a ordem das seções; o painel separando o nível principal do avançado pelo gatilho e pela
materialidade; sob fronteira de escopo, todo número novo com rótulo condicional, com a varredura existente passando
a cobri-los; sem os blocos, nenhuma seção nova aparece e o cross-check diz que não foi declarado.

---

## Dívidas registradas

- A escolha da leitura de capacidade, que troca a rota, fica fora do painel.
- As identidades de coerência do motor entre os vetores do cross-check não são exercidas.
- O empilhamento é alerta na tela, não disclosure do QC.
- Exigir o cross-check e o re-teste terminal é trabalho do `er-analise`, no item 8.
