# B4 — Exercício operacional completo TFCO4 + impacto decomposto por causa

> superpowers:executing-plans (inline). Condições 1 e 2 da aprovação. SEM recomendação nova.
> Namespace original não existe nesta máquina (divergência registrada na FASE A): o exercício
> usa a RECONSTRUÇÃO validada no B0 (delta zero em todas as chaves publicadas do PDF).

### Task 1: fixture completo `tests/fixtures/tfco4/inputs_b4_completo.yaml`
Gerado por script determinístico (uma vez, commitado): `inputs_b1.yaml` + blocos v3.2:
- `fatos.reformulado`: série 2020–2024 REAL do `T&F_CG_3Q24.xlsm` (recomputo B0; médios de EoP
  consecutivos) + **FY2025 reconstruído do PDF** com lacunas rotuladas: e_fim 588.400 e ND fim
  115.200 (p.4); receita 1.046.000 e NI 142.300 (p.3-4); `nie_pos_imposto` ESTIMATIVA (−12.500,
  escala de 2024) → nopat derivado; `noa_medio` por identidade CE≡NOA [DILIGÊNCIA: NOA FY2025
  não medido — exige DFP primário].
- `premissas.operacional`: margem×giro por cenário ancorados na série real (base 15,0%×1,70 ≈
  ROIC 25,5% ≈ 2024 medido 25,6%); `nopat_fy_mi` 154,8 (FY2025 reconstruído); claims = dívida
  líquida −115,2 (pacote IFRS16_PURO); WACC 13,4% (modelo de cobertura TF, B0) com fonte;
  `nota_paridade` declarada (bases e taxas propositalmente distintas das da âncora patrimonial).
- `premissas.central_neutro` (lpa 1,05/cap 13/ke 12,5), `premissas.dossie_ke` (rota paridade-US
  14,56% do próprio modelo TF vs build local ~19%; prêmio de tamanho 0 com critério; escolhido
  14%), `fatos.norma_contabil` (IFRS_CPC, IFRS16_PURO), `premissas.impostos` (27% operacional
  documentada vs 34% terminal statutory).
- [ ] Gerar + rodar engine (APROVADO) → commit.

### Task 2: `tests/test_b4_impacto.py` — trava os números do documento
(a) REGRESSÃO: sob v3.2, `inputs_b1.yaml` (contrato antigo) reproduz TODAS as chaves antigas
(8,34 / 79,7% / 42,8631 / 9,01 / SUMARIA — baseline B1 já cobre; assert explícito aqui também);
(b) modo completo: gates EQUITY_OK; paridade com delta medido; central_neutro 41,7%; grade de
Ke; φ grid; reverse operacional com round-trip; (c) variantes por CAUSA (condição 2):
(ii) ROE base ← ponte real 0,2548 (só o base) → Δ central medido; (iii) base de lucro: LPA 1,12
→ +41,1%/+52,5% (B0). Números medidos na primeira execução e travados no teste.
- [ ] RED (esqueleto com asserts de presença) → medir → travar → GREEN → commit.

### Task 3: `docs/impacto_TFCO4.md`
Antes/depois POR CHAVE + tabelas: âncoras (patrimonial vs operacional + paridade e wedge),
reversa operacional (ROIC/CAP/WACC implícitos), central_neutro + robustez conjunta, implícitos
dos múltiplos (20x hist / 5,24x pares), grade de Ke, φ (14–26% do prêmio), gates H7, camadas de
imposto; **decomposição por causa**: (i) alavancas LPA/CAP/Ke/φ, (ii) ROE pela ponte vs input
livre, (iii) base de lucro; lacunas/diligências FY2025; SEM recomendação nova.
- [ ] Escrever citando chaves dos runs → suíte completa → commit.
