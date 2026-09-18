# Laboratório como interface da tese

O laboratório não é uma planilha com sliders. Ele deve tornar manipulável a cadeia causal que decide a tese:

> **driver do mundo real → impacto operacional → premissa econômica → valuation → preço / retorno implícito**

## Drivers

Escolha apenas os drivers que um comitê realmente discutiria sobre **esta** companhia. Não existe quantidade padrão.

Exemplos:

- software: pricing, retention, seat growth, upsell;
- oil & gas: petróleo, gás, produção, refining margins, capex;
- royalties: commodity price, produção, GEOs, ramp-ups;
- seguradora: sinistralidade, cat load, custo de aquisição, retorno do float.

Cada driver material tem valor base, faixa plausível e fonte. Quando houver sensibilidade publicada pela companhia, use-a dentro do domínio em que vale. Cenários são vetores coerentes de drivers com uma narrativa econômica, nunca produto mecânico de extremos.

## Interface

- Mostre primeiro drivers intuitivos do negócio; parâmetros financeiros entram apenas onde ajudam a entender a conta.
- Recalcule imediatamente valor por ação e outputs intermediários que contem a história.
- Traduza a reversa para a linguagem do negócio: "o preço exige X de produção", "Y de retenção", "Z de margem", conforme o caso.
- Use presets de cenários apenas se facilitarem comparação.
- Use matriz de duas entradas somente quando dois eixos dominarem a decisão; caso contrário, escolha visualização melhor.
- Inclua retorno anualizado ou múltiplo de saída apenas quando relevante para a decisão.
- Entrada inválida deve gerar mensagem clara, nunca `NaN` silencioso.

## Reconciliação

JavaScript fica no próprio HTML, sem rede. Quando reproduzir uma conta coberta por `justos.py`, o laboratório deve reconciliar com os outputs canônicos nos presets publicados. Ajustes materiais calculados fora do motor (excesso transitório, claims, cenários contratuais) também reconciliam com os artefatos canônicos, e o laboratório declara quais componentes recalcula e quais mantém fixos. O valuation canônico continua sendo o motor; o JavaScript é interface.

Os números citados na prosa devem ser exatamente os calculados pelo preset correspondente.

## Honestidade

Mostre qual premissa vira a conclusão, o que o modelo não captura e a direção do erro. Quando o terminal dominar o valor, torne isso visível e sensibilize o horizonte/hipótese que o sustenta.
