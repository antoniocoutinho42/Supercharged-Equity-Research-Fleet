# Multi-segmento

## 12. Multi-segmento — quando o negócio único é ficção

A fórmula descreve UM negócio: um `g`, uma rentabilidade marginal, um CAP, uma classe de
convenção. Companhia com segmentos economicamente distintos viola isso na origem.

**Teste de materialidade (rode antes de decidir):** os segmentos diferem materialmente em (i)
rentabilidade marginal, (ii) CAP/durabilidade da vantagem, ou (iii) classe de convenção terminal?
Se qualquer um dos três for sim para um segmento que pese mais de ~20% do EBITDA ou do capital,
o blended é erro sistemático, não aproximação. **Gatilho adicional (v9.20):** veículo de
coinvestimento consolidado com sócio externo relevante (o mesmo do gatilho de elevação da
fronteira, §2) é segmento com economia própria POR CONSTRUÇÃO — o sócio precificou aquela fatia
isoladamente ao entrar — e dispara este teste ainda que a operação pareça integrada.

**Gatilho por safra de capital (v9.22).** O teste dispara também SEM segmentos operacionais
distintos, quando a base INSTALADA e a EXPANSÃO em curso carregam claims de natureza/duração
distintas — concessão com termo + plataforma de originar concessões novas; mina + exploração;
contrato regulado + mercado livre. Nenhuma convenção terminal única serve ao consolidado: é a
decomposição de Miller-Modigliani (ativos instalados + PVGO) executada como soma de partes por
safra. Como rodar: a parte instalada com rampa a RiR_wk (§8f) e terminal da NATUREZA do claim
(anuidade com TV zero no termo; convenção normal se perpétuo); a expansão pelo fluxo padrão
quando programática, ou como NPV de projetos discretos quando datados com capex declarado —
soma, e a ponte para preço uma vez, sobre o topo (passos 3–5 acima). **Trava da parede entre
safras:** o crescimento da parte instalada é SÓ rampa; o da expansão é SÓ capital novo — a mesma
receita nunca aparece nas duas (canal único do §8f, elevado de nível). **Lado do ativo:** quando o
ativo de uma safra é o INSUMO PRODUTIVO da outra, a parede não é só de receita — ou a safra
operacional é cobrada do aluguel de mercado do ativo já marcado, ou o ativo é descontado até a venda
com o fluxo usando-o de graça até lá. Rotas, identidade e gap em §13. **Quando NÃO usar:**
claims homogêneos (fábrica em rampa + fábrica nova, ambos perpétuos) — a soma das partes e o
consolidado devolvem o mesmo número sob premissas coerentes, e abrir a SOTP só dobra terminais e
cria fronteira nova para dupla contagem se esconder; declare a equivalência e rode consolidado.

**Fase × safra (v9.23) — os dois eixos são ortogonais.** Fases compõem NO TEMPO dentro de uma
safra (recursão do §8f); safras compõem NO CAPITAL pela soma deste §12 — e cada safra pode ter,
internamente, suas próprias fases (segmento em rampa + segmento em investimento, simultâneos: é
uma matriz fase × safra, e a matriz cobre o caso geral). O múltiplo-manchete é output da soma.
Com uma safra investindo, o caixa CONSOLIDADO pode ser negativo com cada safra saudável — a
conservação de capital roda POR FASE E POR SAFRA, nunca só no consolidado. A trava do
delimitador do §8f vale em cada célula da matriz.

**Por que é sistemático, e não ruído.** O blended é média ponderada pelo tamanho e a criação de
valor não é — o múltiplo é não linear e g/rentabilidade nem são ponderados pela mesma medida (g
por NOPAT, rentabilidade por capital); a Hessiana é indefinida na região relevante (paper §6.12),
então o sinal do viés **se calcula, não se deduz**. Direção típica: subestima a joia pequena num
corpo de baixo retorno, superestima o corpo medíocre carregado por um segmento pequeno de ROIC
alto — mas é HIPÓTESE, pode inverter. Verificação barata e obrigatória quando a materialidade
dispara: **calcule EV_segmentado − EV_blended e reporte o número com o sinal**.

**Como rodar por partes:**
1. Métrica-base, capital e deployment por segmento (fonte: nota de segmentos). Se a companhia não
   abre capital por segmento, diga isso — é limitação de dado, e a solução é aproximar o capital por
   ativos identificáveis, declarando a aproximação.
2. Cada segmento com sua classe (Gate 1), sua convenção, seu CAP, sua rentabilidade marginal e seus
   drivers. Um segmento pode ser `gordon` e outro `book` na mesma companhia — isso é normal, não
   inconsistência.
3. Some os EVs dos segmentos.
4. **No topo, e só no topo:** custos corporativos não alocados (capitalizados a perpetuidade, ou
   alocados por critério declarado), participações não consolidadas, caixa, dívida. A ponte para
   preço acontece uma vez, sobre a soma — nunca por segmento.
5. Declare o desconto (ou prêmio) de holding se aplicar, e por quê. Não aplique por hábito.

**Se rodar blended mesmo assim** — porque o dado não permite, ou porque a diferença não é material
— declare os três testes, o resultado de cada um e a direção do erro esperada. Blended silencioso
é o defeito, não o blended.

### §8b — Ponte de releveraging: caso aplicado (v9)

**Quando disparar:** evento de estrutura de capital DATADO no horizonte — plano de desalavancagem
pós-recuperação judicial, dividend recap anunciado, capitalização de financeira para crescer,
covenant forçando amortização. Não confundir com deriva lenta de D/E (essa é a limitação C2 do
Ke fixo, tratada via `apv`), nem com degrau de rentabilidade (esse é o §8).

**Template de deleveraging (perfil pós-RJ).** Companhia sai de D/E 1,5 para 0,4 após 3 anos:

```bash
python scripts/justos.py ponte --n1 3 --ke1 26 --ke2 17 --gde1 150 --nde1 130 \
  --gde2 40 --nde2 30 --kd 13 --tax 34 --g1 6 --roe1 9 --pl-base 13.0
```

Leitura da saída, na ordem: (1) o sinal — negativo aqui: o acionista financia a amortização
antes do primeiro dividendo do regime novo; medido em casos-padrão, a ponte chega a −40% do
valor num deleveraging pesado e +10 a +21% em recap — ignorá-la superavalia o turnaround na
direção mais cara; (2) o diagnóstico de Ku — se o gap entre fases passa de 0,5 p.p., ou o
de-risking operacional é justificado por escrito (saída da RJ reduz risco do NEGÓCIO, não só da
dívida?) ou os Ke se re-derivam de Ku único via `apv` antes de qualquer conclusão; (3) o rebase —
com razão ≠ 1, a convenção bifásica declara que o NI da fase 2 entra ×(ROE₂/ROE₁)·razão.
Esse fator é uma **hipótese de rebase de nível**, não uma identidade que decorra do ROE marginal;
ROE₂ continua sendo o marginal usado na retenção da fase 2. A entrega deve narrar explicitamente o
degrau composto e qualificar qualquer ROE₂ implícito como condicionado a essa convenção:
"o lucro rebasa h× na transição por [margem/juros], e o crescimento g₂ aplica SOBRE a base
rebasada"; (4) o gate de 10% — ponte dominante pede modelagem explícita das fases, não ajuste.

**Na entrega:** a ponte aparece como premissa própria na memória de cálculo (valor, derivação
com a conta inline, fonte da estrutura-alvo e DATA do evento, status), e o veredicto declara a
direção do erro se o evento atrasar — deleveraging adiado = valor presente da ponte encolhe
(bom para o acionista de hoje se ela é negativa? não: o Ke₂ menor também adia — reporte o
líquido, nunca só um lado).


### §8d — Composição iso ↔ ponte: nada depende de o analista lembrar (v9.2)

Com evento de estrutura datado, a ordem de operações é FORÇADA pelo motor, não lembrada: o `iso`
exige `--transicao` (sem default). Declarando `ponte` com os parâmetros do regime 1, o motor
calcula o PV internamente (nunca transcreva o número à mão — erro de sinal em transcrição é o
modo de falha clássico), desconta do alvo e roda a curva sobre o alvo líquido no regime 2,
resolvendo a rentabilidade do regime 2 por uma INVERSÃO BIFÁSICA FECHADA — f1, ponte e TV
saem com os regimes declarados e ROE₂ sai em forma fechada **condicionada à convenção de rebase**, com cada ponto verificado contra o
bifásico completo. Declarando `nenhuma`, o output registra a premissa de regime único.
No `rev`, a mesma premissa sai como campo fixo do output e combinações resolver×base
inconsistentes falham com explicação em vez de rodar no lado errado. Na entrega: alvo cheio,
PV da ponte, alvo líquido e o rótulo da composição entram na memória de cálculo como quatro
linhas separadas.


### §6b — Moeda, regime e âncora macro no bloco de inputs (v9.4)

Todo bloco de inputs de valuation real declara, na primeira linha: moeda e regime (`--moeda`).
Essa linha é **invariante de coerência, não uma escolha econômica adicional**: com conversão completa,
nominal e real devem representar o mesmo valor. g, gp, rentabilidade e custo de capital são verificados
na mesma unidade, e o rf nominal da moeda (`--rf`)
quando houver perpetuidade com crescimento. Na memória de cálculo, a convenção de moeda é linha
própria, e qualquer gp acima do teto macro entra como premissa EXCEPCIONAL com a tese que a
sustenta — nunca como número solto. Erro-alvo destas guardas: g projetado em BRL nominal
descontado a Ke construído em USD (ou misturar real e nominal), que não produz nenhum sintoma
numérico e distorce o valor em dezenas de %.
