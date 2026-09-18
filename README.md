# Equity Research Fleet v6.0.0

Fleet de equity research orientado a investimento, reconstruído a partir da própria `multiplos-justos v10.1`.

A v6 reduz a arquitetura ao que melhora efetivamente o raciocínio:

```text
/analisar
   ↓
er-analise  ←→  pesquisador
   ↓
economic map + investment thesis
   ↓
operador-mj → multiplos-justos v10.1 → justos.py
   ↑                ↓
   └── RESEARCH REQUIRED       auditor-mj
                                  ↓
                              er-analise
                                  ↓
                             relatorio-html
                                  ↓
                    verificador + revisor-comite
```

Não é pipeline rígido. O Analista volta entre pesquisa, hipótese e valuation quando a evidência exige.

## Princípios

- **Analista-chefe único:** `er-analise` entende a companhia, forma a tese, interpreta o valuation e escreve o relatório.
- **Research recursivo:** `pesquisador` investiga perguntas específicas e devolve evidência interpretada.
- **Múltiplos Justos obrigatório:** é o framework guarda-chuva do valuation. Comparáveis são contexto/sanity check, não método substituto.
- **Progressive disclosure:** a v10.1 foi quebrada em módulos econômicos; o operador carrega só o que o caso exige.
- **Cálculo determinístico:** `justos.py` continua autoridade para tudo o que cobre.
- **Loop de evidência:** falta material de informação vira `RESEARCH REQUIRED`, não chute silencioso.
- **Auditoria independente:** fato, metodologia e qualidade de research têm revisores diferentes.
- **Relatório livre:** nenhuma estrutura fixa, número de abas ou gráficos. A forma segue a tese.

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
| `commands/revisar-relatorio.md` | três lentes de revisão |

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

O mapa completo da migração da v10.1 está em `MIGRACAO-V6.md`.
