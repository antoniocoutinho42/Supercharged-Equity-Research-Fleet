# Regras operacionais do Fleet

## Sem herança

Cada companhia re-deriva premissas do zero. Inputs ou valuations anteriores podem ser usados como confronto **depois** da derivação independente; nunca como âncora silenciosa.

## Sem pipeline rígido

O operador sempre respeita gates e invariantes aplicáveis, mas carrega somente os módulos que a economia exige. Não existe obrigação de percorrer toda a biblioteca ou todas as seções de relatório em toda rodada.

## Modos de uso

- **Valuation de companhia real:** parte do `economic-map.md`, escolhe rota interna, deriva premissas, calcula, diagnostica e gera `valuation-case.md`.
- **Reverse valuation / leitura de preço:** mantém a mesma disciplina, mas concentra a pesquisa nos eixos que o preço torna decisivos.
- **Sanity check:** pode ter escopo menor, desde que deixe explícito o que não foi investigado e não seja apresentado como initiating coverage.
- **Consistência Ke↔WACC / releveraging:** usa os comandos e módulos específicos quando disparados, sem transformar essa trilha em requisito universal.

## Research loop

Se uma premissa material não for defensável com a evidência disponível, retorne `RESEARCH REQUIRED`. O objetivo não é preencher o modelo; é representar corretamente a economia.
