# Equity Research Fleet v6.1.0

Fleet de equity research orientado a investimento, reconstruído a partir da própria `multiplos-justos v10.1`.

A v6 reduziu a arquitetura ao que melhora efetivamente o raciocínio. A v6.1 aumenta a inteligência do research sem acrescentar etapas: o Analista só valora quando consegue explicar causalmente como o negócio transforma demanda em receita, receita em lucro, lucro em retorno sobre capital e retorno em valor por ação, e o que fica fora dessa cadeia.

```text
/analisar
   ↓
er-analise  ←→  pesquisador (hipóteses rivais, contratos no original, pre-mortem)
   ↓  teste de "entendido" + gates de research (instrumento material, resiliência financeira)
economic map (+ claims fora da cadeia) + investment thesis (hipóteses rivais)
   ↓
operador-mj → multiplos-justos v10.1 → justos.py
   ↑                ↓
   └── RESEARCH REQUIRED       auditor-mj (desafia rota e duração)
                                  ↓
                              er-analise
                                  ↓
                             relatorio-html
                                  ↓
                    verificador + revisor-comite (sobre a versão final)

/anexo-financeiro → série histórica publicada, reutilizando historico/ quando existir
```

Não é pipeline rígido. O Analista volta entre pesquisa, hipótese e valuation quando a evidência exige, e pode rodar uma conta exploratória antes de entender tudo, desde que rotulada.

## Princípios

- **Analista-chefe único:** `er-analise` entende a companhia, forma a tese, interpreta o valuation e escreve o relatório.
- **Research recursivo:** `pesquisador` investiga perguntas específicas e devolve evidência interpretada.
- **Múltiplos Justos obrigatório:** é o framework guarda-chuva do valuation. Comparáveis são contexto/sanity check, não método substituto.
- **Progressive disclosure:** a v10.1 foi quebrada em módulos econômicos; o operador carrega só o que o caso exige.
- **Cálculo determinístico:** `justos.py` continua autoridade para tudo o que cobre.
- **Loop de evidência:** falta material de informação vira `RESEARCH REQUIRED`, não chute silencioso.
- **Auditoria independente:** fato, metodologia e qualidade de research têm revisores diferentes.
- **Relatório livre:** nenhuma estrutura fixa, número de abas ou gráficos. A forma segue a tese.
- **Causalidade antes de valor (v6.1):** o valuation canônico só fecha depois do teste de "entendido". Investigar é obrigatório; publicar é condicional à materialidade.
- **O acionista é o último da fila (v6.1):** claims, contratos, dívida e obrigações entre o valor operacional e o valor por ação são varridos sempre e aprofundados quando materiais. Não perder dinheiro vem antes de ganhar muito.
- **Independência real ou declarada (v6.1):** revisores rodam sobre a versão final; sem contexto separado, o artefato diz isso. Existe uma única revisão vigente dos números.

## Componentes

| Peça | Responsabilidade |
|---|---|
| `skills/er-analise/` | Analista-chefe e dono da tese |
| `skills/multiplos-justos/` | kernel v10.1, rotas, referências e motor |
| `skills/relatorio-html/` | comunicação, visualização e laboratório |
| `agents/pesquisador.md` | investigação profunda |
| `agents/operador-mj.md` | tradução economia → metodologia → valuation |
| `agents/auditor-mj.md` | auditoria metodológica independente |
| `agents/verificador.md` | fact checking |
| `agents/revisor-comite.md` | qualidade do investment case |
| `commands/analisar.md` | entry point principal |
| `commands/leitura-de-preco.md` | reverse valuation focado |
| `commands/revisar-relatorio.md` | três lentes de revisão, mais a lente de omissões |
| `commands/anexo-financeiro.md` | anexo financeiro histórico, separado ou como aba do relatório |

## O que muda na v6.1

Nenhum agente novo, nenhuma skill de topo nova, nenhuma alteração em `multiplos-justos` (kernel, doutrina, `justos.py` e `testes.py` intactos). As mudanças vivem no `er-analise`, nos agentes e na skill de relatório:

- `skills/er-analise/SKILL.md`: teste de "entendido" como condição do valuation canônico; conta exploratória rotulada antes dele; dois gates de research condicionais (direitos e obrigações econômicas materiais; resiliência financeira); pre-mortem; versão única; modo de execução declarado; checkpoint de alto valor com o usuário.
- `references/economia-do-negocio.md`: método causal (escada do porquê, decomposição de receita e rentabilidade por mecanismo, crescimento endógeno por ação, safras de capital, indústria como implicação, perfis e ledger de management).
- `references/direitos-obrigacoes-e-perda.md`: onde procurar claims, protocolo do instrumento material em quatro estados, resiliência financeira, pre-mortem.
- `references/historico-financeiro.md` e `/anexo-financeiro`: série histórica pelo ciclo, comparabilidade, definições, anexo HTML.
- `pesquisador`: mandatos por hipótese, contratos no original, modo adversarial. `operador-mj`: ponte fechada com os claims, linha do tempo única, registro de diagnósticos, firma contra acionista. `auditor-mj`: desafio de rota e duração, staleness. `verificador` e `revisor-comite`: instrumentos, mensagem final, causalidade e perda.

Casos de aceitação e método de comparação com a v6 em `docs/casos-de-aceitacao.md`.

## Valuation

A rota é escolhida pela economia dentro do framework Múltiplos Justos. Consulte `skills/multiplos-justos/references/core/routes.md`.

Rotas incluem firma/perpetuidade operacional, equity, multi-segmento, vida finita/reserve NAV, asset NAV/stock-mark, holding/SOTP, option/scale, normalização de nível e releveraging.

## Testes

```bash
python scripts/validate-plugin.py
python skills/multiplos-justos/scripts/justos.py selftest
python skills/multiplos-justos/scripts/testes.py --phase model
python skills/multiplos-justos/scripts/testes.py --phase cli
# depois de gerar um relatório:
python scripts/validate-report.py analises/TICKER/AAAA-MM-DD/relatorio.html
```

O mapa completo da migração da v10.1 para a v6 está em `MIGRACAO-V6.md`. As notas da v6.1 estão em `docs/releases/v6.1.0.md`.
