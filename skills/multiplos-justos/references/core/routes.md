# Rotas econômicas dentro de Múltiplos Justos

A pergunta do Fleet nunca é "Múltiplos Justos serve para esta companhia?". A pergunta é:

> **Como a economia desta companhia deve ser representada corretamente dentro do framework Múltiplos Justos?**

Múltiplos Justos é o framework guarda-chuva. A fórmula de perpetuidade operacional é uma rota, não o framework inteiro.

## Rotas

| Economia predominante | Rota interna | Autoridade de cálculo |
|---|---|---|
| Operação em continuidade, retorno e reinvestimento legíveis | `firm / operating perpetuity` | `justos.py ev`, com módulos de nível, degrau, drivers, APV e diagnósticos quando aplicáveis |
| Banco, seguradora ou economics dominado por equity | `equity` | `justos.py pe` e sub-playbook de financeiras |
| Segmentos com economics materialmente diferentes | `multi-segment` | cada segmento usa sua rota; agregação preserva fronteiras e evita blended artificial |
| Reservas, concessões e claims de vida finita | `finite-life / reserve NAV` | curva explícita de produção/vida do ativo; `justos.py` continua obrigatório para diagnósticos cobertos pelo motor e para qualquer bloco de continuidade |
| Imobiliário, landbank ou ativos cujo valor é marca patrimonial | `asset NAV / stock-mark` | identidade de marca de estoque, yield, apreciação, giro e parede estoque↔fluxo |
| Holding ou conglomerado | `holding / SOTP` | soma das rotas dos ativos/segmentos, com dívida, impostos, custos da holding e desconto explicitado como hipótese, não resíduo |
| Pré-lucro ou transição até escala | `option / scale` | economia unitária, milestones e cenários explícitos; nenhum múltiplo comparável pode substituir a derivação econômica |
| Mudança discreta de estrutura de capital | `transition / releveraging` | `justos.py ponte` e, quando necessário, `apv` / `iso --transicao ponte` |
| Nível corrente não representativo | `normalized-level` | normalização por drivers, `normaliza`, `drivers`, `nivel`; depois retorna à rota econômica subjacente |

## Regras que valem em todas as rotas

1. Gates e invariantes da metodologia continuam válidos sempre que economicamente aplicáveis.
2. Observado, derivado, inferido e assumido não podem ser misturados.
3. Premissa material sem evidência vira `RESEARCH REQUIRED`, não preenchimento silencioso.
4. `justos.py` é a fonte canônica para todos os cálculos que ele cobre. Não replique fórmulas manualmente no relatório.
5. Múltiplos comparáveis podem contextualizar preço, história e consenso. Não determinam o valor justo.
6. Um DCF genérico separado não é fallback. Se fluxos explícitos forem necessários, eles são a implementação da rota econômica interna e obedecem às mesmas regras de base, capital, terminal, rastreabilidade e auditoria.
7. A escolha de rota fica registrada no `valuation-case.md`, com a razão econômica em uma frase e os gates/módulos carregados.
8. Se o `justos.py` legado emitir a frase **"troque de arquitetura"**, leia operacionalmente como **"migre para a rota interna adequada"**. O warning do motor foi preservado para não alterar o núcleo determinístico; ele não autoriza sair do framework.
