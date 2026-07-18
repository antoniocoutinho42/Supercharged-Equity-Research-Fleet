# Recomputo independente (implementação de referência)

Fonte: `docs/fontes/Red Team - auditor.md`, Seção 3 passo 3 e Apêndice A.
Escopo `calculo`. O engine usa a forma fechada; a sua referência soma
dividendos ano a ano (Bracket com DE/NDE) e desconta o book no fim do CAP.
Caminho de cálculo diferente, deve coincidir a ~1e-9 para CAP inteiro:

```python
def pl_justo_ref(g, roe, cap, ke, de=0.0, nde=0.0):
    """Referencia do Auditor: DDM explicito + book terminal (P/B=1 no fim do CAP)."""
    bracket = (1.0 - g/roe) + (de - nde) * (g/roe)
    lucro, vp = 1.0, 0.0
    for t in range(1, int(cap) + 1):
        vp += lucro * bracket / (1.0 + ke) ** t
        lucro *= (1.0 + g)            # ao final: lucro = E_(CAP+1)
    return vp + (lucro / roe) / (1.0 + ke) ** cap
# uso, contra resultados.json (exemplos do caso de calibracao VRSK):
# pl_justo_ref(0.10, 0.20, 12, 0.12) * 7.16 -> 63.64  (hurdle.cenarios.base.preco)
# pl_justo_ref(0.10, 0.20, 12, 0.09) * 7.16 -> 81.41  (economico ke=0.090 base)
# validacao por multiplos: pl_justo_ponderado_econ == economico.central_ponderado / lpa
```

EXTENSÃO m_terminal (padrão do engine v2.2.0, ver `skills/er-valuation/
engine.py`): o motor não reverte sempre a book contábil (P/B=1) no fim do
CAP; ele desconta `m_terminal * (lucro_final/ROE) / (1+Ke)^CAP`, com
`m_terminal` default 1.0 (retrocompatível byte-a-byte) e multiplicador
livre quando o Modelador justifica (`justificativa_m_terminal`) um book
econômico diferente do contábil. Para manter os dois caminhos de cálculo
comparáveis quando `m_terminal != 1.0`, multiplique o mesmo termo terminal
na referência:

```python
def pl_justo_ref(g, roe, cap, ke, de=0.0, nde=0.0, m_terminal=1.0):
    bracket = (1.0 - g/roe) + (de - nde) * (g/roe)
    lucro, vp = 1.0, 0.0
    for t in range(1, int(cap) + 1):
        vp += lucro * bracket / (1.0 + ke) ** t
        lucro *= (1.0 + g)
    return vp + m_terminal * (lucro / roe) / (1.0 + ke) ** cap
# M*(lucro_final/ROE)/(1+Ke)^CAP eh o termo terminal de referencia acima
```

Recompute nesta ordem: os dois ponderados (hurdle e econômico central), um
degrau do ladder, um reverse (re-resolva por bisseção simples ou confira
por substituição), o P/L justo implícito da validação por múltiplos
(`validacao_multiplos.pl_justo_ponderado_econ = central/LPA`, conferível
por divisão). Divergência acima de 1e-6 no múltiplo é issue CRÍTICA
imediata. PROIBIDO modelo paralelo em planilha ou em segundo script: a
referência é esta implementação, com o mesmo `m_terminal` do cenário
auditado, não um exercício livre.
