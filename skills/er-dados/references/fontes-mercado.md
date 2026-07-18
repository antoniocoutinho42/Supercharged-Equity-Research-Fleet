# Fontes de mercado, múltiplos e consenso

## Preço, market cap e EV

Sempre por busca datada em fonte de mercado confiável OU conector de
mercado disponível (categoria b, ver `references/conectores.md`); nunca use
preço de memória ou de treinamento. Registre `meta.fonte_preco` e
`meta.data_preco` no `inputs.yaml` para todo dado de mercado usado na
análise. VALIDADE: preço com mais de 24h em dia útil está VENCIDO para
decisão, recolete antes de usar em tese ou valuation.

## Múltiplos históricos e de pares

Preferir conector de fundamentals estruturados (categoria c) sempre que
disponível: a série sai pronta, com a base contábil já identificada, sem
risco de leitura errada de agregador. Fallback quando não houver conector:
agregadores públicos, com verificação cruzada de 2 fontes (duas fontes)
sempre que o número for decisivo para tese ou valuation. Este é o padrão
que a coleta manual da FNV não tinha (usava um único agregador sem
segunda checagem) e que passa a ser regra dura a partir desta skill.

Regra dura herdada do engine: a comparação entre a empresa e os pares só é
válida na MESMA BASE CONTÁBIL (GAAP com GAAP, ou ajustado com ajustado,
nunca misturados). Divergência entre agregador e filing resolve a favor do
filing, com a divergência registrada no ledger.

## Consenso sell-side

Uso é apenas de calibração, nunca de tese (regra herdada da hierarquia de
fontes de `er-dossie`). Registre a data da amostra do consenso
(`fatos.consenso.fonte` e a data da coleta) junto com min, max e mediana.
