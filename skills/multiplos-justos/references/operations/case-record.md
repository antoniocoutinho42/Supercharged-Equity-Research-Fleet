# Registro canônico do valuation

O objetivo é rastrear o que move valor, não documentar cada campo imaterial.

## `valuation-case.md`

Registre, conforme materialidade:

- rota econômica e razão;
- gates que mudaram a análise;
- premissas decisivas, com valor, unidade e status (`observado`, `derivado`, `inferido`, `assumido`);
- fonte ou derivação e racional econômico;
- ligação com o driver do negócio;
- alternativa plausível/faixa e nível de confiança;
- impacto aproximado no valuation;
- comandos do motor e outputs que sustentam o caso;
- warnings relevantes e tratamento;
- reverse valuation, sensitivities, MM e terminal quando material;
- lacunas abertas e direção do erro.

Use `inputs.json` e `outputs.json` quando isso facilitar execução, reconciliação com laboratório ou auditoria. Não crie JSON apenas para preencher schema.

## Cadeias metodológicas

Quando a conta exigir derivação econômica detalhada, carregue `calculation-chains.md`. Essas cadeias preservam as travas da v10.1 para rentabilidade marginal, conservação de capital, RiR por perna, triângulo de crescimento, normalização, degrau, custo de capital, iso-valor, MM e confronto com caixa operacional.
