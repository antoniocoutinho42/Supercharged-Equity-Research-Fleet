# Classificação por natureza econômica (H2) — critérios, ledger e jurisprudência

**Decisão ratificada (FASE A + aprovação da FASE B, 2026-07-21): NÃO existe dicionário de
rubricas.** Os quatro modelos de referência compartilham classes e critérios, mas ZERO rubricas
em comum. Uma lista prévia deixaria linhas reais sem classificação e induziria matches errados.
Cada análise reclassifica DO ZERO pelos critérios abaixo; nunca copie a classificação de outra
empresa.

## Classes de destino (fixas e poucas)

`ATIVO_OPERACIONAL` | `PASSIVO_OPERACIONAL` | `ATIVO_FINANCEIRO` | `PASSIVO_FINANCEIRO` | `EQUITY`
(e, no bridge EV→equity, a classificação DUPLA via `claim_bridge` — H4.)

## Testes de natureza (aplique nesta ordem, uma linha de justificativa)

1. **Nasce da operação de vender o produto/serviço?** → operacional.
2. **Rende ou custa juros / é reserva de valor?** → financeiro.
3. **Existiria se a empresa fosse 100% financiada por equity?** Se sim → operacional.
4. **É claim de provedor de capital sobre o EV?** → financeiro (e candidata a `claim_bridge`).

## Ledger obrigatório (`classificacao.yaml`, schema `classificacao.schema.json`)

- TODA linha do balanço reportado entra, com justificativa de uma linha + fonte — **sem
  resíduo**: a exaustividade vem da obrigação de classificar tudo, não de um dicionário.
- Invariantes verificados na carga (checar): somas por classe ≡ totais reportados; ativo ≡
  passivo + equity (⇒ CE≡NOA por construção). Violou → **erro**, corrija a coleta.
- Linha em dúvida → `ambigua: true` (vai ao contraditório do Auditor, que re-deriva a classe
  de forma independente). O arquivo é **congelado no snapshot** do run.

## Jurisprudência consultiva (casos difíceis resolvidos — B0/FASE A; consulta, NUNCA lookup)

| Caso | Resolução | Critério que decide | Evidência |
|---|---|---|---|
| Goodwill | Fora do capital OPERACIONAL do 1º ROIC; dentro do 2º ROIC (com goodwill — alocação de capital) | Não gera receita por si; mede o preço pago | TF exclui (Tangible Equity l.41); Lopes 25,63% com vs 27,10% ex (B0) |
| Intangível-CONTRATO (ex.: contrato Itaú, R$177mi) | ATIVO_OPERACIONAL | Gera a receita de apropriação — excluí-lo destrói a base do negócio (remover: ROIC vira −51%, sem sentido) | Lopes RA l.12; FASE A H1 |
| Restricted cash / outros ativos financeiros | ATIVO_FINANCEIRO | Reserva de valor, não operação | PVV FA l.28; Lopes "Outros ativos financeiros" BP r20 (55,8mi) |
| Dividendos/JCP a pagar | PASSIVO_FINANCEIRO | Claim de provedor de capital | TF l.37; Lopes l.34 (BP r44) |
| Written puts de minoritários | PASSIVO_FINANCEIRO na reformulação; no bridge, tratar JUNTO com minoritários (fair value) | Claim sobre o EV; CP e LP podem estar em DUAS linhas do BP — some as ocorrências (lição B0) | Lopes l.36 (BP r45 21,1; r55 0) |
| Warrants | PASSIVO_FINANCEIRO | Claim de capital | PVV FL l.31 |
| Impostos diferidos | Operacional dos DOIS lados (ativo e passivo) | Nasce da operação tributada; simetria verificada (a suposta incoerência do prompt foi REFUTADA no B0) | TF r12 ativo op; Lopes ambos op |
| Provisões | PASSIVO_OPERACIONAL | Obrigação da operação | os três modelos reais |
| Leasing | Depende do PACOTE (abaixo) — nunca misturar | — | H3 |

## Pacotes de leasing (H3) — declare UM em `norma_contabil.leasing_pacote` e TRAVE

| Pacote | Balanço | Resultado | FCFF/EV | Nativo de |
|---|---|---|---|---|
| `IFRS16_PURO` | ROU ativo op; passivo de lease FINANCEIRO (entra no ND) | D&A do ROU + juros em despesa financeira; EBITDA "cheio" | Fluxo NÃO paga aluguel; lease no bridge | IFRS/CPC |
| `AS_IF_RENT` | Lease EXPURGADO do capital (IC ajustado) | Aluguel tratado como custo operacional | Fluxo paga o aluguel; lease FORA do bridge | conversão (declare os ajustes) |
| `ASC842_NATIVO` | ROU e passivo de op-lease OPERACIONAIS | Despesa única linear DENTRO do EBIT | Sem linha própria; fora do ND | US GAAP |

Misturar fluxo de um pacote com estoque de outro foi o erro clássico medido: TF −6,15% na ponte
e EV/EBITDA 7,82x vs 8,48x consistente; materialidade > 5% do EV é inaceitável sem correção.
Pacote não-nativo do regime exige `ajustes_aplicados` declarados (trava do engine:
`PACOTE_LEASING_NAO_NATIVO`).

## Checklist por regime (H13 — detecção NA COLETA; o engine é agnóstico)

- **IFRS/CPC (baseline)**: nenhum ajuste; escolher e travar o pacote de leasing. Camada fiscal
  BR: `aliquota_marginal` é input documentado por companhia (JCP/incentivos — TF usa 27% ≠ 34%).
- **US GAAP**: EBITDA NÃO comparável com IFRS-16 (op-lease dentro do EBIT — caso PVV);
  comparando com peers IFRS, capitalize os op-leases OU des-capitalize os peers (um lado só,
  declarado em `ajustes_aplicados`); LIFO → ajustar reserva quando material; R&D expensado →
  considerar capitalização pró-forma quando material; NOL em camadas (runoff fora do engine,
  claim no bridge — template PVV, reproduzido no B0 a 3,6e-12).
- **J-GAAP / CAS / Ind AS**: STUB — escalar ao Coordenador antes de qualquer análise
  (goodwill amortizado no J-GAAP; leases off-balance até 2027; carve-outs Ind AS). Escopo
  codificado é IFRS/CPC + US GAAP por decisão ratificada.
