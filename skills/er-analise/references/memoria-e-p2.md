# Memória, pergunta pontual e P2

## Protocolo de leitura (qualquer pedido sobre ticker já analisado)

Ordem de confiança e custo: 1º `analises/_memoria/<TICKER>.md` (âncoras + lições); 2º
`analises/<TICKER>/saida/results.json` (citar por chave); 3º workspace completo — ÚLTIMO recurso,
nunca por reflexo. Se a memória responde, pare nela.

## Pergunta pontual

Responder da memória + `results.json`, sem reabrir a análise. Se a pergunta exigir número novo do
engine (ex.: outra sensibilidade), rodar `sens`/`implied` sobre o `case.json` congelado — sem
re-calibrar nada. Registrar em `notas.md` se gerar aprendizado.

## P2 — fato novo (release, guidance, evento)

1. DM re-coleta DIRIGIDA só do que mudou (brief curto; ledger atualizado).
2. Analista re-calibra APENAS os inputs afetados (justificativa nova em `calibracao.md`, seção
   datada "P2 <data>").
3. Re-rodar F8 completo (SUITE PASS → value → sens nos drivers afetados → implied; hurdle se
   havia).
4. **Decisão por materialidade, declarada pelo Analista** (com uma linha de racional):
   - MATERIAL (muda sinal, valor ou tese de forma relevante) → regenerar o HTML completo com
     seção destacada "O que mudou" no topo da aba 2 (`analise.json`: bloco `sumario_html`
     iniciando por "O que mudou") e regenerar a memória por código.
   - IMATERIAL → nota curta apensada à memória do ticker (via `--licoes`), HTML preservado.
5. Memória sempre regenerada por código ao fechar P2 material.

## Fechamento F11 (memória durável)

```bash
python scripts/memoria.py analises/<TICKER> --sintese <sintese.md> --licoes <licoes.md>
```

- Âncoras numéricas: extraídas por código de `case.json`/`saida/results.json` — NUNCA digitadas.
- Síntese/decisão: 3–6 linhas do Analista (tese, veredicto, condicionantes) — verbatim.
- Lições reutilizáveis: 2–6 bullets; teste da lição: "isso muda como analiso OUTRA empresa, ou
  este ticker no futuro?". Lição transversal ao processo → sugestão explícita de atualização do
  plugin, decidida pelo humano.
- Regeneração NUNCA apaga lições anteriores (append por data). Correção de número: na fonte
  (case/results) + regenerar — editar a nota à mão é PROIBIDO.
- Teto de ~150 linhas por nota; acima disso, enxugar síntese, nunca as âncoras.
