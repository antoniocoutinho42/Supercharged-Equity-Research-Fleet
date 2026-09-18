# v10.1: schema técnico legado

> Registro de migração, não formulário obrigatório do Fleet v6.

## 6. Memória técnica — bloco de inputs reprodutível (obrigatório; NUNCA dentro do relatório)

Artefato separado, rotulado "memória técnica — uso interno" (arquivo próprio quando a entrega for
arquivo; bloco final destacado quando for chat). É onde a reprodutibilidade e a língua interna
moram — campos, enums e comandos ficam livres aqui. No relatório, o lugar dele é um quadro de
premissas em linguagem plana (SKILL.md, item 8 do template).

Fecha toda valuation. É o que permite reproduzir a análise idêntica numa sessão futura — e é a
única forma legítima de "herança", porque vem do usuário e é revalidada.

```yaml
companhia: TICKER
data_analise: AAAA-MM-DD
fase: investimento|distribuicao|mista|hibrida_financeira
regime_base: A_reportada|B_normalizada
consenso: {t1_eps: 0.0, t2_eps: 0.0, pt_medio: 0.0, n_analistas: 0, fonte: "...", data: AAAA-MM-DD}
preco: {valor: 0.00, moeda: USD, fonte: "...", data: AAAA-MM-DD}
fx: {par: USDBRL, valor: 0.000, fonte: "...", data: AAAA-MM-DD}
acoes: {total: 0, tesouraria: 0, classes: "A/B pari passu em dividendos"}
metrica_base: {tipo: EBITDA|LL, valor: 0, periodo: "1T26 anualizado", fonte: "..."}
capital: {tipo: equity|capital_investido, valor: 0, data: AAAA-MM-DD,
          mudou_12m_%: 0, evento: "IPO fev/26"}
drivers:
  - {nome: "...", base: 0.00, spot: 0.00, elast: 1.0,
     elast_fonte: "derivada = receita_driver/metrica | declarada porque ...",
     receita_driver: 0.00, impacto_%: 0.0, tratamento: "cenario|sensibilidade",
     fonte: "...", data: AAAA-MM-DD}
degrau:
  indice: {nome: "Basileia", atual: 0.0, piso_regulatorio: 0.0, piso_administravel: 0.0}
  m_eficiencia_marginal: 1.0
  anos_transicao: 0
  perfil_transicao: rampa|pontual
  restricao_efetiva: "capital|funding|originacao|share"
qualidade_do_lucro:
  caixa_operacional_publicado: 0.0
  caixa_operacional_reconstruido: 0.0  # §11.8
  gap_%: 0.0
  conteudo_do_gap: "..."               # classificação de juros/IR, litígios, descontinuados
base_monetaria:
  regime: nominal|real                 # invariante obrigatório; não é 12ª bifurcação econômica
  moeda: USD
  coerencia: "g, gp, rentabilidade e custo de capital reconciliados na mesma base"
  fisher: real_exato|nominal_exato|terminal_only_aproximado
capital:
  serie_3_pontos:                      # §1 — trimestre corrente, mesmo trimestre a-1, último anual
    k_wk_%: [0.0, 0.0, 0.0]
    k_fixo_%: [0.0, 0.0, 0.0]
    capex_sobre_receita_%: [0.0, 0.0, 0.0]
    amplitude_%: 0.0                   # > ~20% ⟹ input é hipótese, vai à sensibilidade
    centro_adotado: corrente|media_da_serie|guidance
  ciclo_de_caixa_dias: 0               # COM SINAL: negativo = giro financia o crescimento
  wc_operacional: 0.0
  capital_investido: 0.0
  capital_investido_companhia: 0.0     # confronto declarado
rir:
  rota: deployment_observado|intensidade_por_perna
  delta_receita_janela_%: 0.0          # <= 0 invalida a rota por deployment (§2, 2ª exceção)
  delta_wc_janela: 0.0
  razao_dwc_dreceita: 0.0              # deve ficar perto de WC/receita, em razão E sinal
  delator_contracao: nao_disparou|disparou_rota_migrada
  k_marginal_%: 0.0
  rir_output_%: 0.0
crescimento:
  total: 0.0
  volume: 0.0
  preco:
    inflacao: 0.0
    repasse: 0.0
    real: 0.0
  rir_por_componente: {volume: 0.0, preco_nominal: 0.0, preco_real: 0.0, criterio: "..."}
depreciacao:
  d_final: 0.0
  rota_contabil: 0.0                  # D&A do DFC, run-rate declarado
  rota_caixa: 0.0                     # capex de manutenção (rubricas declaradas) + amort. arrendamento
  rubricas_de_manutencao: ["...", "..."]
  gap_entre_rotas_%: 0.0
  idade_media_do_parque: "..."        # o gap NÃO se lê sem ela (§2, contraprova de caixa)
  status_do_d: validado_por_duas_rotas|hipotese_gap_declarado|contraprova_nao_executavel
  origem: fluxo_economico_corrente|proxy_contabil_historica|outra
  moeda_origem: USD
  historico_ou_corrente: corrente|historica
  idade_ativos: "..."
  fator_reposicao: 1.0
  ajuste_aplicado: false
  justificativa: "..."
clean_surplus:
  aplicavel: false
  gap: 0.0
  status: fecha|fluxo_nao_explicado|nao_aplicavel
  fluxo_nao_explicado: "..."
book:
  qualidade: reportado|ajustado|reconstruido|proxy|nao_confiavel
  retorno_medio_inicial: 0.0            # ROIC_book ou ROE_book conforme lado
  base_temporal: forward_NOPAT1_sobre_IC0|forward_LL1_sobre_PL0|trailing_reconciliado
  nopat_ou_ll_associado: 0.0
  capital_inicial_implicito: 0.0
  rentabilidade_marginal: 0.0
  retorno_medio_ano_n: 0.0              # output do IC/E acumulado nos dois lados
  implementacao: enterprise_IC_acumulado_e_equity_E_acumulado_clean_surplus_DDM (v9.30)
marca_de_estoque:
  aplicavel: true|false
  ativo: "..."                        # terra, landbank, estoque pronto, frota, participação marcada
  peso_no_valor_%: 0                  # gatilho da 11ª escolha nomeada em ~20%
  marca: {tipo: laudo|NAV|cap_rate|reposicao|transacao, valor: 0, por_unidade: 0,
          data: AAAA-MM-DD, defasagem_meses: 0, avaliador: "..."}
  marca_alternativa: {tipo: transacao_realizada, por_unidade: 0, n: 0, dispersao: "min–max e por quê"}
  custo_capital_do_ativo_%: 0.0       # DO ATIVO; se herdado do consolidado, declarar e dar a direção
  yield_corrente_%: 0.0
  apreciacao_implicita_%: 0.0         # = custo de capital do ativo − yield
  apreciacao_observada: {longa_%: 0.0, recente_%: 0.0, fonte: "..."}
  T_anos: 0
  giro_observado: "monetização média ÷ estoque = ...; exercício corrente = ..."
  fator_de_tempo: 0.00                # VP(Marca_T) ÷ Marca
  R: 0.0                              # marca ÷ capitalização perpétua do fluxo corrente
  rota: a_marca_a_vista_com_aluguel | b_fluxo_pleno_e_marca_descontada
  aluguel_imputado: {valor: 0, ancora: "observável: ... | construção: ...", banda: [0, 0]}
  gap_entre_rotas: 0                  # MEDE a violação da identidade — obrigatório na entrega
  desagio: {objeto: ativos_brutos|liquido_de_passivos, pct: 0, equivalente_sobre_brutos_%: 0}
  parede_base_de_lucro: "série de fluxo por fonte primária | derivada por subtração (PROIBIDA se a
                         companhia publica a série isolada)"
caixa:
  cash_e: 0.0
  cash_yield_bruto: 0.0
  rendimento_caixa_no_ll: true|false
  tratamento: separado_da_operacao|incluido_com_ajuste
taxas:
  g: 0.0
  rentabilidade: {tipo: ROE|ROIC, valores_por_cenario: [0,0,0,0], ancoras: ["...","..."]}
  custo_capital: {tipo: Ke|WACC, valor: 0.0, rf: 0.0, beta: 0.0, erp: 0.0, fonte_beta: "...",
                  canal_risco_pais: "i_beta_local+CRP_por_lucro | ii_beta_ADR_sem_CRP"}
  cap_anos: 10
  beta_banda: [0.0, 0.0]               # >= +-0,20 quando o beta não é mensurável na sessão
  beta_implicito_no_preco: 0.0         # MESMA unidade da banda acima
  deriva_dv_pp: 0.0                    # D/V hoje vs D/V no ano n; >= ~10 p.p. ⟹ rodar `apv`
  convencao_tv: book|convergencia|gordon
  convencao_preliminar: book|convergencia|gordon
  revalidacao_convencao: "mantida | trocada porque rentab marginal X% < custo Y%"
  rentab_tv: 0.0
  gp: 0.0
  d: 0.0
  t: 0.0
  caixa_sobre_equity: 0.0
resultados:
  decomposicao_mm:                     # SAI DO MOTOR: campo `decomposicao_mm` do `ev` (v10.1)
    ativos_instalados: 0.0             # valor sem crescimento nenhum (g=0 e gp=0)
    ativos_instalados_por_acao: 0.00
    valor_do_crescimento: 0.0
    participacao_do_crescimento_%: 0.0
    peso_do_terminal_%: 0.0
    sensibilidade_cap_pm3anos_%: 0.0   # > ~10% ⟹ sensibilidade ao horizonte obrigatória
    vies_mortalidade_declarado: true|false|nao_aplicavel   # obrigatório com terminal > ~50%
  breakeven_premissas_fixas:
    base_de_lucro: 0.0
    rentabilidade_marginal_%: 0.0
    g_%: 0.0
    custo_de_capital_%: 0.0
    dentro_da_banda_declarada: [".."]  # veredicto frágil nesses eixos
reversa:
  nivel_implicito_congelado: 0.0       # LIMITE SUPERIOR (vale com D&A absoluta fixa)
  nivel_implicito_vetor_travado: 0.0   # CENTRAL — sai do `nivel` com o 2º bloco de flags
  nivel_implicito_rentab_derivada: 0.0 # PISO — grade célula a célula
  configuracao_declarada: "vetor travado | rentabilidade derivada do nível"
  teto_crescimento_gratuito: 0.0
  teto_condicional_ao_g: 0.0           # o teto NÃO é teto sobre todas as taxas
  reversa_em_g_tem_raiz: true|false    # só com FALSE se conclui "nenhuma taxa explica o preço"
  gap_vs_preco_alvo_consenso: "variável que sozinha leva do vetor próprio ao PT do consenso"
segmentos: "negocio unico | rodado por partes: [...] | blended declarado, direcao do erro: ..."
comandos_executados: ["selftest", "drivers ...", "pe ...", "degrau ...", "tabela pe ...", "rev ..."]
status_premissas: {verificado: [...], regra_travada: [...], hipotese: [...]}
```

## 10. Status das premissas (template do resumo final)

verificado nesta sessão / derivado por regra travada (citar a regra) / hipótese de construção /
fornecido pelo usuário e revalidado (dizer o que foi revalidado). Sinalizar sempre o que é qual, e
o vintage (data e nível de driver, e data da base de capital) de cada premissa sensível.
