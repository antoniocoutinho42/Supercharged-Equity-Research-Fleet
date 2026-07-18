---
name: er-dados
description: >-
  USE QUANDO precisar coletar dados para uma análise: filings e documentos
  primários, preço e múltiplos de mercado, séries de fundamentals,
  transcripts; ou quando decidir QUAL fonte usar e como registrá-la no
  ledger.
---

# er-dados: adapters de fontes por categoria

Você organiza a coleta de dados de qualquer etapa (dossiê, valuation,
auditoria, atualização) por CATEGORIA de fonte, nunca por dependência de um
fornecedor específico. Um script ou skill do plugin nunca referencia o nome
de um conector fora de `references/conectores.md`.

## 1. Princípio: adapter por categoria

Quatro categorias cobrem toda coleta: (a) filings primários (regulador ou
IR); (b) preço e mercado (cotação, market cap, EV); (c) fundamentals
estruturados (séries históricas, múltiplos de pares); (d) transcripts e
eventos (calls, apresentações). Para cada categoria, o fluxo é sempre o
mesmo: detectar conector disponível → usar o melhor disponível → fallback de
busca web datada da categoria (ver `references/fontes-filings.md` e
`references/fontes-mercado.md`).

## 2. Detecção de conectores

No início da coleta, verifique as ferramentas disponíveis no ambiente (o
nome do conector varia por conta; identifique por prefixo ou descrição, não
por lista fixa; ver `references/conectores.md` para o mapeamento categoria →
conector conhecido). Se existir conector da categoria, PREFIRA-O: dado estruturado
bate screenshot de agregador em custo de tokens e em confiabilidade. Se não
existir, use o fallback de busca web datada da categoria. NUNCA peça
credencial ao usuário dentro da análise; se um conector existir mas estiver
desconectado ou sem acesso, registre a limitação no ledger e siga pelo
fallback, sem bloquear a etapa.

## 3. Registro obrigatório

Toda coleta entra no `fatos.ledger` do `inputs.yaml` (doc, data_arquivamento
e uso; ver contrato em `skills/er-dossie/references/ficha-e-fatos.md`) e,
quando decisiva para tese ou valuation, vira claim `[F-xx]` com fonte e
data. Dado de mercado carrega SEMPRE `meta.data_preco` e `meta.fonte_preco`.
VALIDADE: preço com mais de 24h em dia útil está VENCIDO para decisão,
recolete antes de usar; fundamentals de agregador divergindo do filing, o
filing vence e a divergência é registrada no ledger, nunca silenciada.

## 4. Regras herdadas

Hierarquia completa de fontes: `skills/er-dossie/SKILL.md`, seção
Disciplina de Fontes. Anti-cascata: nenhum dado "indisponível" sem a busca
que sustenta a ausência registrada no ledger. Uma pesquisa por fato, não
repita a mesma busca. Recalcule você mesmo as métricas decisivas a partir do
filing, nunca aceite o número pronto do agregador para uma métrica que vira
tese.

## Referências

- `references/fontes-filings.md`: caminho primário de filings por
  jurisdição.
- `references/fontes-mercado.md`: adapters de preço, múltiplos e consenso.
- `references/conectores.md`: mapeamento categoria → conector conhecido e
  como usar sem acoplar o plugin a um fornecedor.
