---
name: er-memoria
description: >-
  USE ao INICIAR qualquer P2 ou pergunta sobre ticker já analisado (ler
  memória antes de reler arquivos), e ao FECHAR qualquer análise (G8) para
  gerar a nota durável do ticker.
---

# er-memoria: nota durável por ticker, gerada, nunca escrita à mão

A nota de memória (`memoria/<TICKER>.md`) é GERADA por código a partir de
`estado.yaml`, `eventos.jsonl` e o run canônico, não duplicada à mão a partir
do dossiê ou do red_team. Isso evita o defeito P9 do diagnóstico: nota e
estado divergindo com o tempo porque alguém editou só um dos dois.

## Leitura (início de P2 ou pergunta pontual)

Antes de reler o namespace inteiro, procure `memoria/<TICKER>.md` (em
`/mnt/memory/research/` no Cowork; localmente em `<ns>/memoria/`) e leia SÓ a
nota, não o namespace inteiro. Se houver run mais novo que o registrado na
nota, rode `python scripts/delta.py <ns> --desde <hash da nota>` e leia o
`delta.md` resultante. Só releia arquivos-fonte (dossiê, inputs, resultados)
que o delta ou um fato novo do usuário efetivamente tocarem. Ordem de
confiança: a nota é a porta de entrada e o resumo; `estado.yaml` é a verdade
do estado atual; o namespace completo é o detalhe, último recurso.

## Escrita (fechamento G8, ou pós-P2 relevante)

Escreva as lições novas em um arquivo temporário de lições: 2 a 6 bullets,
cada um passando o teste "isso muda como eu vou analisar OUTRA empresa, ou
este mesmo ticker no futuro?". Uma lição não é um resumo do que aconteceu
nesta rodada, é uma regra ou heurística reutilizável. Depois rode:

```
python scripts/memoria.py <ns> --licoes <arquivo_de_licoes.md>
```

Isso regenera as seções 1-5 (cabeçalho, decisão, linha do tempo dos gates,
pendências, âncoras numéricas) do zero a partir da fonte e apenda as lições
novas à seção 6 preservada, com marcador de data. Regra fixa: não edite as seções geradas à mão. Se um número mudou, a correção é na fonte
(estado.yaml, eventos.jsonl, resultados.json) seguida de `memoria.py` de
novo, nunca um edit direto no `.md`.

## Promoção de lições transversais

Uma lição que vale para o PROCESSO inteiro, não só para este ticker, por
exemplo "P/L Justo padrão é estruturalmente conservador para negócios de
royalty/streaming; considerar `m_terminal`", é candidata a virar atualização
de uma skill do plugin. Registre-a normalmente na nota (via `--licoes`) E
aponte-a, na resposta final ao usuário, como "candidata a atualização do
plugin": descreva a lição e qual skill/arquivo ela afetaria. O humano decide
se e como promovê-la; nenhuma skill se auto-edita.

## Regra de custo

A nota tem teto de aproximadamente 150 linhas (`memoria.py` avisa em stderr
se passar). Se isso acontecer, o problema são as seções GERADAS (bug em
`memoria.py` ou `estado.yaml` inchado com pendências/ressalvas demais);
nunca corte lições para caber no teto: reporte o estouro ao usuário e
investigue a fonte.

## Referências

- `scripts/memoria.py --help`: contrato completo de flags e defaults.
- `scripts/delta.py`: diff estruturado entre runs, usado para saber o que
  releu desde a última nota.
