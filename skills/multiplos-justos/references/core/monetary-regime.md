# Moeda e regime macro

## Moeda, regime e âncora macro (guardas opcionais)

Regra travada: g, gp e custo de capital na MESMA moeda e MESMO regime (nominal/real), sempre
declarados — `--moeda` (ex.: BRL-nominal, USD-nominal, BRL-real) ecoa como convenção em todo
output e viaja até a memória de cálculo; sem ela, o motor avisa. Âncora macro do gp (Damodaran):
gp perpétuo ≤ rf NOMINAL da moeda (`--rf` ativa a verificação; em regime real, teto ~3% de PIB
real). gp acima do teto não é bloqueado — é hipótese legítima SE declarada por escrito na
entrega; o motor quantifica o excesso e exige a declaração. O motor nunca converte moeda nem
verifica moeda a partir de números: a guarda é declarativa, e é exatamente aí que mora o valor.
