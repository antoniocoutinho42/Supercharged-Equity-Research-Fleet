# Releveraging

## Ponte de releveraging — mudança discreta de estrutura de capital

A fórmula assume D/E constante; quando a estrutura MUDA uma vez (deleveraging pós-RJ, dividend
recap, banco capitalizando), o salto não é taxa nem degrau de rentabilidade — é um **evento de
caixa único** entre empresa e acionista, e tem preço: `fluxo = E_pré·(GD/E₂·razão − GD/E₁)·
(1+Kd_at)` no ano n1+1, com `razão = (1+ND/E₁)/(1+ND/E₂)`. Rode `ponte`. Sinal negativo =
acionista financia a amortização; positivo = dívida levantada vira distribuição. Derivada da
planilha bifásica do usuário (vF19, checks ~1e-13); com estrutura igual é identicamente zero e o
caso volta a ser o `pe` monofásico. Ordem de grandeza medida: −40% do valor num deleveraging
pesado, +10 a +21% em recap/alavancagem — nunca ignorar, nunca somar sem as DUAS travas:
**(i)** a ponte precifica o movimento de caixa, não o risco — Ke por fase TEM que sair de um Ku
único (`apv`); o motor reporta o Ku implícito de cada fase e alerta o gap (MM: com Ke
reprecificado, o efeito líquido da alavancagem é só o tax shield); **(ii)** com `razão ≠ 1`, a convenção bifásica declara também um **rebase de nível**: o NI da
fase 2 entra ×(ROE₂/ROE₁)·razão. O fator ROE₂/ROE₁ é uma hipótese de rebase do primeiro lucro,
não uma identidade que decorra do ROE marginal. ROE₂ continua sendo o retorno marginal da fase 2
para reinvestimento; usar o mesmo parâmetro no rebase é uma convenção composta que deve viajar com
o resultado. Somar a ponte a valuation não-rebasado mistura as camadas. Derivação e prova do
colapso em `derivacao.md` §8b; caso aplicado em `aplicacao.md` §8.
