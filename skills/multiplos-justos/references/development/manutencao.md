# Manual de adição de conhecimento à skill

Leia ANTES de editar qualquer arquivo deste pacote. Não é lido durante valuation.

Este arquivo existe porque a skill aprende por incidente: cada regra travada nasceu de um caso que
custou dinheiro ou credibilidade (apêndice J). O que decide se o aprendizado sobrevive não é a
qualidade da regra — é onde ela aterrissa. Regra certa no lugar errado não é lida.

---

## 0. A pergunta anterior a todas

**Isso é invariante ou é achado?**

Escreva a regra sem nomear a companhia, o setor e o número. Se não conseguir, você tem um achado.

> *"Terra agrícola marcada a laudo precisa cobrar aluguel da lavoura"* → achado.
> *"Estoque marcado que é insumo produtivo do fluxo exige uma das duas rotas, e o gap entre elas mede
> a violação"* → invariante.

Números e casos vão para o **apêndice J**. Regras vão para o **playbook**. Misturar os dois produz um
playbook que envelhece com o caso que o originou.

---

## 1. As três camadas obrigatórias, e as duas de proveniência

Um conhecimento novo tem que aterrissar em **exatamente três** camadas. Menos, e a regra é inerte;
mais, e ela duplica e diverge.

| # | Camada | Arquivo | O que vai ali | Se faltar |
|---|---|---|---|---|
| 1 | **Gatilho** | `SKILL.md` | quando dispara, em ≤ 8 linhas, apontando para a regra | seção órfã: existe, está certa, ninguém lê |
| 2 | **Regra** | `references/aplicacao.md` | o raciocínio, os números, o procedimento — a autoridade | vira folclore: cada rodada reinventa |
| 3 | **Campo** | `aplicacao.md` §6 (YAML) | o campo da memória técnica | não sobrevive à próxima sessão (não há herança) |
| + | **Jurisprudência** | `aplicacao.md` apêndice J | uma linha: caso, magnitude, o que gerou | a regra é re-litigada em seis meses |
| + | **Proveniência** | `CHANGELOG.md` | origem e escopo da mudança | ninguém sabe se pode reverter |

As camadas 4 e 5 (`derivacao.md`, `paper`) só entram quando há **matemática nova** ou quando o
**estatuto epistemológico** muda (teorema × convenção × hipótese falsificável). `scripts/` só entra
quando a regra vira executável — ver §5.

---

## 2. Onde é o domicílio ÚNICO

Uma regra mora em um lugar só. A árvore, pela natureza do conhecimento:

| A regra muda… | Domicílio |
|---|---|
| o que se ACEITA como input contábil | Gate 0 + `aplicacao.md` §1/§2 |
| o REGIME da base (fase da companhia) | Gate 0.5 |
| a hipótese TERMINAL | Gate 1 + §3 |
| o NÍVEL que já se moveu (drivers × spot) | Gate 2 + §7 |
| o NÍVEL que ainda pode mover (degrau, capacidade) | Gate 3 + §8/§8f |
| a DECOMPOSIÇÃO do negócio (segmentos, safras) | §12 |
| qual ROTA ECONÔMICA interna prevalece sobre a perpetuidade operacional | §13 |
| uma CONTA que passa a ser obrigatória | §11 (nova cadeia) |
| COMO SE ESCREVE a entrega | §5 / §5b |
| o custo de capital / estrutura de capital | §2 + `derivacao.md` §5 |
| MATEMÁTICA do motor | `derivacao.md` + `testes.py` + anchor |

**Duplicar é o pior desfecho, e há prova no pacote:** a fórmula do sub-alerta de recuperação vivia em
`§3` **e** no paper. Uma revisão enxugou o §3 e o paper manteve. As duas cópias divergiram, e a que o
analista lê ao escolher a convenção foi justamente a que perdeu a razão — sobrou o rótulo.

Quando dois lugares parecem candidatos, escolha o que é lido **no momento da decisão**, e do outro
faça uma referência de uma linha.

---

## 3. O gatilho quantitativo é obrigatório

Regra sem limiar é conselho, e conselho é lido por quem já sabia.

Use a escala que o pacote já tem — não invente uma nova:

| Limiar | Onde já é usado |
|---|---|
| **10%** | impacto de driver; alternativa metodológica que exige as duas pontas |
| **~20%** | fronteira de consolidação; materialidade de segmento; marca de estoque |
| **~40% / ~85%** | capital fixo intensivo; utilização que dispara capacidade pré-construída |
| **95%** | retenção que vira não-informativa |
| **±15%** | contraprova de receita-por-ativo contra pares |
| **±25%** | nível implícito × consenso (antecipação temporal) |

Se o gatilho novo não couber em nenhuma dessas ordens de grandeza, desconfie: provavelmente a regra
está descrevendo um caso, não uma classe.

---

## 4. Bifurcação econômica ou invariante de coerência?

**A pergunta mais importante do manual**, e a que mais se erra.

- **Bifurcação econômica** — os dois ramos dão valores diferentes por razão econômica, e escolher é
  tomar posição. ⟹ entra na **lista de escolhas metodológicas nomeadas** (9ª, 10ª, 11ª…), e a entrega
  traz **as duas pontas precificadas** quando a alternativa move > ~10%.
- **Invariante de coerência** — uma escolha feita de forma coerente **não pode, por si só, criar ou
  destruir valor**. ⟹ **fica FORA da lista** e é reportado à parte.

Precedente: a **base monetária** (nominal × real) é invariante, não bifurcação — converter tudo de
forma coerente não muda o valor. Na v9.32, o **nível** da marca de estoque é bifurcação (11ª); a
**rota (a)/(b)** da parede estoque↔fluxo é invariante.

**Terceiro desfecho, além de bifurcação e invariante: GENERALIZAR uma escolha existente.** Antes de
criar a (n+1)-ésima, pergunte se a escolha nova tem a MESMA natureza econômica de alguma da lista —
se tiver, amplie o escopo daquela em vez de somar. Precedente da v10: "o ponto do ciclo dos inputs
de capital" tem a mesma natureza de "o ano de capex de estado estacionário" (as duas escolhem em que
ponto do ciclo o capital é medido), e a 8ª foi generalizada em vez de virar 12ª. A lista é o
instrumento de atenção mais caro do pacote; inflá-la por analogia frouxa custa mais do que a regra
nova entrega.

Errar para o lado da bifurcação infla a lista e cansa o leitor sem informação. Errar para o lado do
invariante esconde uma posição. **Teste prático:** se você consegue construir um exemplo em que as
duas pontas devolvem o MESMO valor sob premissas coerentes, é invariante.

---

## 5. Declaratório ou executável?

| | Custo | Quando |
|---|---|---|
| **Declaratório** (registra e avisa, nunca bloqueia) | uma seção, zero risco de release | default |
| **Executável** (flag no motor) | anchor + `testes.py` + duas fases de release | quando a CONTA é a parte difícil, ou quando o silêncio é indetectável |

**Nunca executável-só.** O sub-alerta de recuperação era executável-só: disparou verbatim numa rodada
real e foi descartado porque o analista filtrou a saída do motor por campo. Alerta sem contraparte
doutrinária é alerta que se filtra. Se vale um flag, vale um parágrafo no playbook.

Ao tornar algo executável: anchor novo em `testes.py`, e `python scripts/testes.py --phase model`
seguido de `--phase cli` **em invocações separadas**.

---

## 6. Teste de extrapolação — antes de fechar, não depois

Rode a regra nova, no papel, contra **duas classes de ativo ou setores que NÃO a originaram**.

- **Não dispara em nenhum** → o gatilho está errado, ou você tem um achado.
- **Dispara em tudo com a mesma resposta** → não é regra, é ruído.
- **Dispara e DISCRIMINA** → está pronta.

Exemplo real (v9.32, teste da identidade da marca de estoque), com
`fator de tempo = VP(Marca_T)/Marca`:

| Caso | yield do estoque | T | fator | identidade fecha em |
|---|---|---|---|---|
| Incorporadora — landbank | 0% | 4a | 0,67 | 67% |
| Incorporadora — estoque pronto | −2% | 2a | 0,80 | 77% |
| Shopping / FII de tijolo | 8,5% | 10a | 0,40 | 91% |
| Armador — frota própria | 9,0% | 8a | 0,47 | 95% |
| Agro — terra (caso de origem) | 2,4% | 10a | 0,42 | 57% |

A regra discrimina: onde o aluguel é alto a marca é defensável; onde é nulo ou negativo, o buraco é o
tamanho da aposta em apreciação. **Se a sua tabela de extrapolação der a mesma resposta em todas as
linhas, volte ao §0.**

---

## 7. Consistência antes de fechar — checklist

Rode literalmente, com busca de texto:

1. **Renumeração em cascata.** Adicionou uma escolha nomeada? Procure `dez escolhas`, `10ª`, `11ª`,
   `12ª` em TODOS os arquivos — inclusive comentários do YAML do §6. O contador aparece em pelo menos
   cinco lugares.
2. **Referência cruzada existe nos dois sentidos.** A seção nova é citada pelo `SKILL.md`? Aparece na
   enumeração do bloco "Referências"? (O §13 ficou da v9.7 à v9.31 fora dela.)
3. **Espelhos sincronizados.** `SKILL.md` e `aplicacao.md` §5b carregam a mesma lista de critérios de
   aceitação e a mesma estrutura de entrega, um em esqueleto e outro por extenso. Mudou um, mude o
   outro.
4. **Lista de banimento.** Termo interno novo entrou? Ele precisa de uma linha na tabela de tradução
   (§5) e, se for rótulo, da lista de banimento (§5b).
5. **`selftest` verde.** Mesmo em mudança puramente doutrinária: `python scripts/justos.py selftest`.
   Anchor que se mexeu sem intenção é o erro mais caro do pacote.
6. **Versão.** `SKILL.md` cita a versão corrente e nada mais; o histórico vive só no `CHANGELOG.md`.
   Marcador de versão dentro de regra do corpo só quando distinguir o comportamento novo do antigo
   for operacionalmente necessário.

---

## 8. Os cinco anti-padrões

1. **Regra sem gatilho** → conselho. Lida por quem já sabia.
2. **Regra em dois domicílios** → divergem na próxima revisão, e a cópia que sobrevive costuma ser a
   errada.
3. **Regra só no motor** → alerta filtrável.
4. **Regra só na doutrina quando a conta é a parte difícil** → não é rodada.
5. **Seção órfã** — adicionar em `aplicacao.md` sem citar no `SKILL.md`. **O mais caro dos cinco**,
   porque a regra existe, está correta e ninguém a lê.

---

## 9. Formato de uma entrada nova

**No `SKILL.md` (gatilho, ≤ 8 linhas):** o que dispara, o limiar, as saídas obrigatórias em telegrama,
e o ponteiro. Nenhum raciocínio — o corpo é esqueleto.

**No playbook (regra):** abre com o gatilho em negrito; depois a razão econômica em uma frase; depois
o procedimento; depois a direção do erro de cada escolha; fecha com o efeito na entrega (é bifurcação
nomeada? é invariante?). Se a razão não couber em uma frase, a regra não foi entendida.

**No apêndice J (uma linha densa):** ticker, mês, o que aconteceu, **a magnitude em dinheiro ou em
percentual**, e o que gerou. Sem narrativa — a narrativa vive no `CHANGELOG`.

**No `CHANGELOG`:** cabeçalho `## vX → vY (data) — "título"`, um parágrafo de origem, itens numerados
em negrito. Declare explicitamente se o núcleo numérico foi alterado; se não foi, diga que não foi.
