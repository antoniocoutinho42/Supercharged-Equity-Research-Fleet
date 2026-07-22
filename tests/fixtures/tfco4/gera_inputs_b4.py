# -*- coding: utf-8 -*-
"""Gera inputs_b4_completo.yaml (determinístico): inputs_b1.yaml + blocos v3.2 do
exercício B4 (condição 1 da aprovação da FASE B). Rodar uma vez; o resultado é
commitado como fixture. Fontes anotadas campo a campo abaixo."""
import os

import yaml

AQUI = os.path.dirname(os.path.abspath(__file__))
inp = yaml.safe_load(open(os.path.join(AQUI, "inputs_b1.yaml"), encoding="utf-8"))

# --- fatos.reformulado: 2020-2024 do T&F_CG_3Q24.xlsm (recomputo B0, médios de EoP
# consecutivos; ver upgrade_fleet_v2_fase_a/h6_h7_recompute.run.out) + FY2025 do PDF.
inp["fatos"]["reformulado"] = {
    "unidade": "R$ mil",
    "fonte": ("2020-2024: T&F_CG_3Q24.xlsm 'Reformulated Accounts' (recomputo B0); "
              "FY2025: relatorio_final_1.pdf p.3-4 — LACUNAS ROTULADAS: nie_pos_imposto "
              "ESTIMATIVA (escala 2024); noa_medio por identidade CE≡NOA (NOA FY2025 não "
              "medido — DILIGÊNCIA: DFP primário)"),
    "serie": [
        dict(ano=2020, receita=267320.0, nopat=31364.9, noa_medio=147095.05, nd_medio=41589.9,
             e_medio=105505.15, e_fim=200190.8, nie_pos_imposto=-3730.9, ni_recorrente=27634.0),
        dict(ano=2021, receita=434592.0, nopat=81389.3, noa_medio=225370.55, nd_medio=-6140.85,
             e_medio=231511.4, e_fim=262832.0, nie_pos_imposto=-1423.3, ni_recorrente=79966.0),
        dict(ano=2022, receita=567426.0, nopat=100302.2, noa_medio=327597.0, nd_medio=37491.0,
             e_medio=290106.0, e_fim=317380.0, nie_pos_imposto=-3842.0, ni_recorrente=96460.2),
        dict(ano=2023, receita=683690.1, nopat=124256.1, noa_medio=419478.35, nd_medio=64314.85,
             e_medio=355163.5, e_fim=392947.0, nie_pos_imposto=-9846.1, ni_recorrente=114410.0),
        dict(ano=2024, receita=787411.5, nopat=120214.4, noa_medio=469069.6, nd_medio=43087.6,
             e_medio=425982.0, e_fim=459017.0, nie_pos_imposto=-11659.7, ni_recorrente=108554.7),
        # FY2025 reconstruído: e_fim = PL 588,4mi e ND fim 115,2mi (PDF p.4); receita 1.046mi e
        # NI 142,3mi (p.3-4); nie ESTIMATIVA −12,5mi; nopat = ni − nie; noa_medio = nd+e médios.
        dict(ano=2025, receita=1046000.0, nopat=154800.0, noa_medio=587157.05, nd_medio=63448.5,
             e_medio=523708.5, e_fim=588400.0, nie_pos_imposto=-12500.0, ni_recorrente=142300.0),
    ],
}

# --- âncora operacional (H9): cenários margem×giro ancorados na série real
# (2024 medido: 15,3% × 1,679 = 25,6%; FY2025 reconstruído: 14,8% × 1,78 = 26,4%).
inp["fatos"]["nopat_fy_mi"] = 154.8          # FY2025 reconstruído (R$ mi)
inp["fatos"]["claims_bridge"] = [
    {"nome": "divida_liquida", "valor_mi": -115.2,
     "fonte": "PDF p.4 (essencialmente arrendamentos IFRS-16; pacote IFRS16_PURO)"},
]
inp["premissas"]["operacional"] = {
    "wacc": 0.134, "fonte_wacc": ("modelo de cobertura TF (Valuation!W17 = 13,37%, recomputado "
                                  "no B0); arredondado 13,4% — premissa RECEBIDA (H8)"),
    "aliquota_operacional": 0.27,
    "fonte_aliquotas": "TF Reformulated r74 (27% com incentivos; statutory 34% — B0/H5)",
    "cenarios": {"bear": {"margem_nopat": 0.135, "giro_noa": 1.55},
                 "base": {"margem_nopat": 0.150, "giro_noa": 1.70},
                 "bull": {"margem_nopat": 0.165, "giro_noa": 1.85}},
    "drivers_narrativos": {
        "bear": "desaceleração de aberturas; SSS fraco comprime margem; giro estagna",
        "base": "mix franquia avança (~40 aberturas/ano): margem cede e giro sobe — a mesma força move os dois",
        "bull": "novo formato 2x receita/loja + Europa: margem e giro sobem com alavanca operacional",
    },
    "justificativa_dupla_penalizacao": ("no bear a perda de escala comprime margem E giro "
                                        "simultaneamente: história específica declarada"),
    "nota_paridade": ("Divergência ESPERADA e decomposta no impacto: base NOPAT FY2025 "
                      "reconstruída (1,010/ação) vs LPA reportado 0,95; WACC 13,4% vs Ke 14%; "
                      "ROIC dos cenários operacionais ≠ ROE dos patrimoniais. O delta é o "
                      "teste independente dos ajustes de base — ver impacto_TFCO4.md."),
}

# --- R2: caso central neutro (aprovado; números do caso conjunto do B0)
inp["premissas"]["central_neutro"] = {
    "lpa": 1.05, "cap_base": 13, "ke": 0.125,
    "justificativa": ("Caso conjunto moderado (R2/B0): base de lucro neutra entre reportado "
                      "0,95 e ajustado 1,12; CAP base na banda moat-claro; Ke na média das "
                      "rotas do dossiê — desfaz o empilhamento conservador de uma vez."),
}

# --- R4: dossiê de Ke (rotas do próprio caso; B0/hip_ke_wacc)
inp["premissas"]["dossie_ke"] = {
    "rota_paridade_us": {"componentes": {"rf_us": 0.041, "cds_br": 0.035,
                                         "dif_inflacao": 0.0146, "beta": 1.0, "erp": 0.055},
                         "total": 0.1456,
                         "fonte": "build do próprio modelo de cobertura TF (Valuation!W6:W11, B0)"},
    "rota_local": {"componentes": {"rf_local": 0.135, "beta": 1.0, "erp_local": 0.055},
                   "total": 0.19,
                   "fonte": "build local padrão (rf NTN-B longa + ERP local); calculado e NÃO usado"},
    "premio_tamanho": {"valor_pp": 0.0,
                       "criterio": "liquidez adequada (ADTV > R$10mi) e follow-on recente: sem prêmio"},
    "escolhido": 0.14,
    "reconciliacao_hurdle": ("hurdle 13% do usuário = piso da grade econômica; 1pp abaixo do "
                             "Ke central escolhido — leitura de disciplina, não de custo de capital."),
}

# --- H13: norma contábil (detecção na coleta; engine agnóstico)
inp["fatos"]["norma_contabil"] = {
    "regime": "IFRS_CPC", "leasing_pacote": "IFRS16_PURO",
    "fonte_filing": "DFP/ITR (CVM)", "ajustes_aplicados": [],
}

# --- H5: camadas de imposto declaradas
inp["premissas"]["impostos"] = {
    "marginal": 0.27, "terminal": 0.34,
    "fontes": ("operacional/marginal 27% = TF r74 (incentivos; B0); terminal 34% statutory "
               "LP salvo evidência de incentivo perpétuo — a diferença move o EV em −12,6% (B0)"),
}

dest = os.path.join(AQUI, "inputs_b4_completo.yaml")
with open(dest, "w", encoding="utf-8") as f:
    f.write("# GERADO por gera_inputs_b4.py (B4, condição 1) — inputs_b1.yaml + blocos v3.2.\n"
            "# Fontes por campo no gerador; FY2025 reconstruído com lacunas rotuladas.\n")
    yaml.safe_dump(inp, f, allow_unicode=True, sort_keys=False, width=100)
print("gerado:", dest)
