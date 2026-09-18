# Cenários, reversa e confronto temporal

## 4. Grade canônica de cenários e reversa

**Cenários não se inventam: derivam-se de âncoras observáveis.** Quatro cenários, sempre nesta
ordem e sempre declarando a âncora de cada um:

| Cenário | Âncora obrigatória |
|---|---|
| Piso / trough | **o MENOR entre** (i) o run-rate anualizado do trimestre mais recente sobre a base de capital ATUAL e (ii) a média normalizada do período-base — ver a trava abaixo |
| Base | ponto médio entre trough e consenso, OU a média do próprio histórico normalizado — declare |
| Alta / consenso | consenso de mercado com data e nº de analistas, ou guidance da companhia |
| Teto | rentabilidade pré-disrupção / pico do ciclo, **rotulada como teto da alavanca, não cenário** |

**TRAVA do piso (v9.12) — em price-taker no TOPO do ciclo, o trimestre recente é o TETO, não o
piso.** A regra "anualize o trimestre mais recente" pressupõe que o último dado é o pior, o que vale
em trough e se INVERTE em pico: anualizar um trimestre que realizou o driver acima do spot empilha o
topo do ciclo no numerador e chama isso de cenário conservador. Antes de usar (i), compare o preço
realizado do trimestre com o SPOT: se o realizado estiver acima, (i) é teto e o piso é (ii).
*Jurisprudência J1: realizado 16% acima do spot — anualizar o trimestre teria produzido um
"piso" acima do cenário-base.*

**Sensibilidades obrigatórias, com amplitude travada pelo tipo de premissa:**
- **Custo de capital:** ±50bps quando o beta é observado e a moeda é forte; ±200bps quando o beta
  vem de pares (sem histórico próprio) ou o prêmio-país é volátil. Declare qual caso e por quê —
  amplitude escolhida sem critério é sensibilidade decorativa.
- **gp: ±50bps sempre que a convenção for `gordon`.** Ali o gp é alavanca de primeira ordem: o TV
  responde pela maior parte do valor e o gp entra no denominador (custo − gp). Omitir essa
  sensibilidade esconde a fragilidade estrutural do resultado.
- **Degrau:** banda de `m` e perfil de transição, quando houver (§8).

Cada cenário com preço/ação pela ponte explícita.

**Menu de reconciliação (v9.17) — a reversa é um cardápio, não um eixo.** O preço admite mais de
uma explicação univariada; entregar uma só é escolher a conclusão. A seção de expectativas
embutidas cobre os eixos APLICÁVEIS, cada um resolvido com os demais no vetor central:
(i) nível do driver implícito (quando houver driver/degrau); (ii) base temporal (confronto com o
consenso — regra abaixo); (iii) g implícito; (iv) rentabilidade implícita e/ou curva iso;
(v) CAP implícito (quando candidato); (vi) **custo de capital implícito — eixo OBRIGATÓRIO em
toda rodada** (`rev --resolver ke|wacc`), traduzido para a âncora externa: beta implícito =
(custo_impl − rf)/ERP, confrontado com a banda histórica do beta observado. Nível e custo de
capital são os DOIS eixos com observável direto de mercado — e o segundo é o mais barato de
esquecer (jurisprudência J10). Depois dos univariados, teste as fronteiras bivariadas plausíveis
(base futura × custo de capital; base futura × regime terminal) e **feche a seção com o
julgamento comparativo: qual reconciliação exige a menor violência às âncoras observáveis — essa
é a que o mercado provavelmente usa — e qual observável a testaria.**

**Dualidade dos eixos de denominador (v9.17).** Custo de capital menor e crescimento de preço
gratuito no terminal comprimem o MESMO spread (custo − crescimento); são quase-duais. Quando os
dois aparecem como explicações candidatas, declare a dualidade — senão o leitor conta o mesmo
eixo econômico como duas evidências independentes (J10: o "regime inflacionário do ouro" e o
"beta no fundo da banda" eram a mesma compressão de spread por portas diferentes).

**Gatilho de duração (v9.17).** Quando custo de capital − g < ~3 p.p., o valor é hipersensível ao
denominador: a reversa em custo de capital roda PRIMEIRO, e a sensibilidade de ±50bps reporta
preço E múltiplo.

**Break-even das quatro premissas fixas (v10) — a margem de segurança do veredicto.** As
sensibilidades respondem "se X mudar, o valor vai para Y". O comitê pergunta o contrário: "quanto X
precisa mudar para o veredicto virar?". É a mesma máquina da reversa, com alvo no preço de tela,
resolvendo uma premissa fixa por vez. **Rota executável de cada uma, para não sobrar nenhuma à mão:**
rentabilidade marginal, `g` e custo de capital saem de `rev --resolver roic|g|wacc`; a **base de
lucro** sai de `nivel` na leitura recalculada — e é o MESMO número do nível implícito da seção de
expectativas, então se calcula uma vez e se cita duas.
Reporte o valor de break-even e a distância em pontos percentuais até o adotado. **Premissa cujo
break-even cai DENTRO da banda de sensibilidade já declarada ⟹ o veredicto é frágil naquele eixo**,
e a entrega diz isso com todas as letras em vez de deixar o leitor descobrir. É o fecho natural da
seção de riscos.

**Decomposição do gap contra o preço-alvo do consenso (v10).** O §1 manda coletar o preço-alvo médio
e o número de analistas; a Conclusão manda reportá-lo. Sem uma terceira regra, o consenso entra como
enfeite. Rode a reversa uma segunda vez com alvo no **preço-alvo médio** em vez do preço de tela e
diga qual variável, sozinha, leva do vetor próprio ao alvo do consenso. Custo: uma execução. Retorno:
converte "discordamos do sell-side" em "o sell-side está usando margem de X% ou custo de capital de
Y%", que é falsificável. Sem cobertura, declare a lacuna — não a preencha com estimativa própria.

Reportar honestamente múltiplas raízes, neutralidades (perto da neutralidade a variável implícita
é ruído numérico com aparência de precisão — sempre reporte a curvatura) e alvos inalcançáveis
com o máximo atingível.

**Confronto temporal obrigatório (v9.15) — antes de qualquer conclusão de fantasia terminal.**
O `nivel` devolve a métrica implícita no preço; confronte-a com o consenso de t+1 e t+2
(coletado em §1; passe `--consenso-t1`/`--consenso-t2` e o motor emite a leitura):
- métrica implícita ≈ consenso t+1/t+2 (até ~+25%, calibrado em J8) ⟹ leitura é **antecipação temporal**: o mercado
  desconta uma base futura — comportamento padrão em fase de investimento (Gate 0.5). A reversa
  correta passa a ser sobre o vetor consenso (ex.: `rev --resolver cap` contra a base t+2) — o
  horizonte implícito de mercado de Rappaport/Mauboussin (*Expectations Investing*): resolver o
  horizonte que justifica o preço dado o consenso, em vez de declarar o preço impossível dado o
  passado.
- métrica implícita ≫ qualquer consenso ⟹ aí sim a hipótese terminal está no preço; siga para o
  teto do crescimento gratuito e o gp implícito (protocolo v9.13, inalterado).
Jurisprudência J8: nível implícito 2,55x o LTM ≈ consenso t+2 — antecipação temporal lida como
fantasia terminal foi o erro que este parágrafo existe para impedir.

**Leitura do teto do crescimento gratuito — o qualificador que a torna verdadeira (v10).** O teto
(RiR → 0, `gordon` com rentabilidade terminal → ∞ e gp = g) é limite superior **CONDICIONAL AO g
DECLARADO**: ele não é teto sobre todas as hipóteses de taxa, porque um g maior o desloca para cima.
Só é lícito concluir que **nenhuma hipótese de TAXA explica o preço** quando a reversa em g TAMBÉM
não tem raiz dentro do domínio declarado (RiR ≤ 100% sem funding, gp ≤ teto macro) — e "sem raiz" é
sempre relativo ao intervalo varrido, como o §6.7 do paper insiste. Satisfeita a condição, o achado
é necessariamente sobre (i) o NÍVEL da métrica-base, (ii) a fronteira do ativo (§13 — valor fora do
fluxo: marca de estoque, opcionalidade de controle, ativo parado) ou (iii) o denominador.
**Concluir "o mercado está irracional" nesse ponto é erro de leitura.** Caso concreto do risco: numa
rodada o teto ficou 12% abaixo do preço com g de 7%, e a reversa em g devolveu raiz a 19,8% — a
afirmação forte teria sido falsa.

**Nível implícito é uma ESCADA, não um número — declare a configuração (v10.1).** `alvo ÷ múltiplo
justo` com o múltiplo CONGELADO é **limite superior**. Recalculando o múltiplo a cada nível com o
VETOR TRAVADO — só o encargo de reposição responde, porque a D&A absoluta é fixa e `d = D&A/métrica`
cai — obtém-se a leitura **CENTRAL**, que o `nivel` devolve. E se a **rentabilidade marginal também
for derivada do nível** (intensidade de capital constante: margem NOPAT sobe, capital por unidade de
receita não), o múltiplo sobe mais ainda e o nível exigido cai mais: é o **PISO** da escada, montado
célula a célula. A ordem `congelada > vetor travado > rentabilidade derivada` é propriedade, não
coincidência — quanto mais variáveis respondem ao nível, menos nível o preço exige. Num caso medido:
**263 / 244 / 229** de EBITDA implícito, uma amplitude de 15% no achado central da seção de
expectativas. É a mesma exigência do §7 sobre grades: **a configuração do triângulo se declara**;
grade sem configuração declarada não é reproduzível, e nível implícito sem configuração declarada
tampouco.
**Condição de validade da propriedade de teto:** vale quando a D&A absoluta NÃO escala com o nível —
recuperação de margem ou de preço. Se o nível vem de VOLUME, a D&A escala com as unidades produzidas,
o `d` não cai e as leituras convergem.
**Identidade que economiza uma conta:** a leitura recalculada contra o preço de tela É o break-even
da base de lucro. São o mesmo número; não o calcule duas vezes.

**Curva iso-valor.** Quando houver dois vetores de valor de naturezas distintas (ex.: recuperação
de rentabilidade e degrau de capacidade), apresente o conjunto de pares que reconcilia o preço.
Ela converte "está barato?" em "qual dos dois vetores o mercado não está pagando?", que é uma
pergunta testável.
