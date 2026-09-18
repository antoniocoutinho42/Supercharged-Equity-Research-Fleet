# equity-research-fleet v4

Plugin de equity research que opera um **analista autônomo e thesis-driven**: descobre as poucas
perguntas que determinam a tese, pesquisa a evidência onde ela estiver, e converte isso num valuation
rigoroso, auditável e interativo. A matemática não é dele — vem de uma cópia congelada da metodologia
`multiplos-justos` v10.1, que o fleet orquestra mas nunca reimplementa.

Desenho completo e **fonte de verdade**:
[`docs/desenho-arquitetura-v4.md`](docs/desenho-arquitetura-v4.md). Conflito entre este README e
aquele documento resolve-se por ele.

## Os dois produtos

- **Análise** — o fluxo completo: perguntas da tese, pesquisa, valuation e relatório de três abas.
- **Leitura de preço** — a engenharia reversa da metodologia: o que o preço embute, menu de
  reconciliação, custo de capital implícito e nível implícito, com o escopo declarado. Entrega
  reduzida à aba Valuation.

São produtos, não níveis de esforço. **Na dúvida, Análise.**

## As cinco skills e o agente

| Componente | Papel |
|---|---|
| [`er-multiplos-justos`](skills/er-multiplos-justos/SKILL.md) | Índice e manifest de hashes do vendor congelado. Diz o que existe, onde está e quando ler — **nunca parafraseia metodologia**. |
| [`er-valuation`](skills/er-valuation/SKILL.md) | Wrapper de orquestração: contrato do caso, rotas, cenários, ponte para preço, SOTP, reversa e sensibilidades. Chama o motor; **nunca faz conta de valuation por fora dele**. |
| [`er-evidencia`](skills/er-evidencia/SKILL.md) | Doutrina de pesquisa e proveniência, agnóstica de fonte. Dona do contrato `ledger/1`, da hierarquia por claim, da reconciliação e da classificação de gaps. |
| [`er-analise`](skills/er-analise/SKILL.md) | Workflow master: quatro marcos (escopo · perguntas da tese · pesquisa e derivação · valuation e entrega), autonomia por default e as regras invioláveis. |
| [`er-relatorio`](skills/er-relatorio/SKILL.md) | Builder determinístico e QC. **Único caminho de emissão**: não interpreta prosa, não busca dado e aceita uma única raiz de execução. |
| [`pesquisa-evidencia`](agents/pesquisa-evidencia.md) | Agente de tipo único, instanciado N vezes em paralelo, um mandato por instância (filings; RI e transcripts; setorial; macro; pares). **Encontra e estrutura evidência — não interpreta nem calibra.** |

A separação é a regra: Pesquisa & Evidência encontra; o Analista interpreta e calibra.

## O vendor congelado

A metodologia vive em [`vendor/multiplos-justos/`](vendor/multiplos-justos/) — cópia **read-only** da
skill de usuário `multiplos-justos` v10.1, que permanece intocada fora deste repositório. Origem,
data e sha256 por arquivo em
[`skills/er-multiplos-justos/manifest_vendor.json`](skills/er-multiplos-justos/manifest_vendor.json).

O pacote fica **fora de `skills/`** por necessidade: ele declara `name: multiplos-justos` no próprio
`SKILL.md`, e sob `skills/` um loader recursivo registraria uma segunda skill com esse nome,
colidindo com a do usuário. A invariante — nenhum `SKILL.md` aninhado sob `skills/` — é travada por
teste.

Evoluir a metodologia é decisão humana explícita: troca-se o pacote inteiro e regenera-se o manifest.
Alteração local quebra a suíte, por desenho.

## Como uma execução roda

Cada execução é autocontida e **não herda nada** de nenhuma outra: sem memória durável, sem cache
entre execuções, sem premissa ou conclusão anterior entrando em silêncio.

```bash
# 1. a raiz da execução
python skills/er-analise/scripts/execucao.py nova <TICKER> [--produto leitura_de_preco]

# 2. o valuation, pelo wrapper que chama o motor congelado
python skills/er-valuation/scripts/avaliar.py <raiz>/caso.json --out <raiz>/resultados.json

# 3. a suíte da metodologia, rodada e registrada na raiz
python skills/er-analise/scripts/execucao.py suite <raiz>

# 4. a entrega: compõe entrega.json e roda o builder
python skills/er-analise/scripts/execucao.py montar <raiz>
```

```
analises/<TICKER>/<AAAA-MM-DD-NNN>/
├── execucao.json                                 # id, ticker, idioma, produto
├── evidencia/                                    # fragmentos do ledger; `montar` junta num só
├── quarentena/                                   # análise anterior fornecida, aberta só no M4
├── caso.json · resultados.json · analise.json    # partes obrigatórias
├── dados.json · confronto.json                   # partes opcionais
├── entrega.json                                  # composto por `montar`, validado por schema
└── relatorio.html · qc.json · ficha-tecnica.json # o que o builder emite
```

O relatório é um **arquivo único autocontido, zero rede**, com três abas: **Tese** (a decisão de
investimento), **Valuation** (laboratório econômico interativo, com premissas editáveis e diagnóstico
ao vivo) e **Evidência** (ledger, reconciliações e limitações declaradas).

## QC em três níveis

O QC impõe integridade econômica e matemática, não preferência editorial — e roda por código, não por
agente:

- **`HARD_FAIL`** — não emite. Paridade Python↔JS divergente, suíte da metodologia falhando, número
  material sem proveniência, gráfico com dados não rastreáveis, pergunta de tese sem vínculo
  econômico, fair value por ação como conclusão principal sob fronteira de escopo declarada.
- **`REQUIRED_DISCLOSURE`** — emite, mas o fato aparece explicitamente na entrega.
- **`QUALITY_WARNING`** — interno, para revisão.

Em HARD FAIL o builder escreve `qc.json` e **nenhum `relatorio.html`**. A paridade entre o motor em
Python e o espelho em JS é **falha fechada**: divergiu, não emite.

## Testes

```bash
python -m pytest tests/ -q
```

```bash
python vendor/multiplos-justos/scripts/justos.py selftest
python vendor/multiplos-justos/scripts/testes.py --phase model
python vendor/multiplos-justos/scripts/testes.py --phase cli
```

A suíte do vendor roda em **duas invocações frescas**: uma invocação única sem `--phase` é recusada de
propósito pelo próprio script (a fase `cli` abre 20+ subprocessos reais, e somar as duas num
processo-pai produz falso negativo sob quota agressiva de subprocessos).

- Dependências: Python 3.12+, `pytest`, `pyyaml`. O motor e os builders são stdlib pura.
- **Node.js** (opcional, recomendado): com `node` no PATH os testes de paridade rodam de verdade e o
  builder verifica a paridade por caso no build. Sem node, a entrega sai com o REQUIRED DISCLOSURE
  `paridade_nao_verificada_no_build`. No CI (ubuntu + setup-node) a paridade roda sempre.
- Windows: os arquivos congelados são protegidos de conversão de EOL por `.gitattributes`.

O golden case real fica **fora do CI**, rodado à mão como aceitação de release: o sintético testa a
engenharia, o real testa se o fleet produz bom equity research.

## CI e release

`ci.yml`: suíte da metodologia, paridade Python↔JS, `pytest tests/` e sanity do manifesto, em todo
push/PR. `release.yml` (tag `v*`): valida tag == versão do `plugin.json`, empacota ZIP e publica
GitHub Release com corpo opcional de `docs/releases/<tag>.md`.
