#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Golden tests do valuation-engine v2.

Três camadas:
  A) Propriedades matemáticas do P/L Justo (validações de primeiros princípios:
     neutralidade ROE=Ke, limite de Gordon, monotonicidade em Ke, alavancagem).
     O NÚCLEO MATEMÁTICO é idêntico ao da v1.1.0 auditada — estas propriedades
     e os preços do caso VRSK são invariantes de regressão.
  B) Reprodução do caso VRSK (números do motor principal auditados no
     red_team.md v2 / valuation.md v2, 09-10/07/2026) + os blocos novos da v2
     (validação por múltiplos, reverse enxuto, ladder com delta, eco de CAP).
  C) Validação de inputs: o engine RECUSA entradas incoerentes (LPA <= 0 sem
     modo custom, probabilidades erradas, g >= ROE, CAPs fora de ordem,
     justificativas/confiança do CAP ausentes).

Se qualquer número mudar, a versão nova do engine NÃO pode ser promovida sem
explicação e, quando a auditoria for acionada, assinatura do Auditor.

Rodar:  python tests/test_golden_vrsk.py   (exit code 0 = tudo verde)
"""
import copy
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(AQUI))

from engine import pl_justo, carregar_inputs, rodar  # noqa: E402

FALHAS = []


def chk(nome, obtido, esperado, tol):
    ok = obtido is not None and abs(obtido - esperado) <= tol
    print(f"{'PASS' if ok else 'FAIL':4s} | {nome:58s} | esperado {esperado:>10} | obtido {obtido}")
    if not ok:
        FALHAS.append(nome)


def chk_bool(nome, cond):
    print(f"{'PASS' if cond else 'FAIL':4s} | {nome}")
    if not cond:
        FALHAS.append(nome)


print("=" * 100)
print("CAMADA A — propriedades matemáticas do motor P/L Justo")
print("=" * 100)
# A1. Neutralidade ROE=Ke: crescimento não cria valor -> P/L = 1/Ke, para qualquer g e CAP
for g in (0.02, 0.08, 0.11):
    for cap in (5, 12, 30):
        chk(f"A1 ROE=Ke=12% (g={g}, CAP={cap}) -> 1/Ke", pl_justo(g, 0.12, cap, 0.12), 1 / 0.12, 1e-9)
# A2. Limite de Gordon: CAP -> inf (g<Ke) -> (1-g/ROE)/(Ke-g)
chk("A2 Gordon (g=6%, ROE=20%, Ke=10%, CAP=2000)",
    pl_justo(0.06, 0.20, 2000, 0.10), (1 - 0.06 / 0.20) / (0.10 - 0.06), 1e-6)
# A3. Monotonicidade: P/L decresce em Ke
chk_bool("A3 P/L decrescente em Ke",
         pl_justo(0.08, 0.20, 12, 0.09) > pl_justo(0.08, 0.20, 12, 0.12))
# A4. Alavancagem neutra: DE = NDE (qualquer nível) reproduz o caso base exatamente
chk("A4 DE=NDE=0,35 == base (g=8%,ROE=20%,CAP=12,Ke=10%)",
    pl_justo(0.08, 0.20, 12, 0.10, de=0.35, nde=0.35), pl_justo(0.08, 0.20, 12, 0.10), 1e-12)
# A5. DE > NDE (caixa líquido relativo) eleva o múltiplo quando g > 0
chk_bool("A5 (DE-NDE)>0 eleva o multiplo, g>0",
         pl_justo(0.08, 0.20, 12, 0.10, de=0.50, nde=0.20) > pl_justo(0.08, 0.20, 12, 0.10))

print("=" * 100)
print("CAMADA B — caso VRSK (golden) + blocos novos da v2")
print("=" * 100)
inp = carregar_inputs(os.path.join(os.path.dirname(AQUI), "inputs_exemplo_vrsk.yaml"))
res = rodar(inp)

h = res["hurdle"]["cenarios"]
chk("B1 hurdle bear", h["bear"]["preco"], 53.12, 0.03)
chk("B1 hurdle base", h["base"]["preco"], 63.64, 0.03)
chk("B1 hurdle bull", h["bull"]["preco"], 80.90, 0.03)
chk("B1 hurdle ponderado", h["ponderado"], 63.94, 0.03)
chk("B1 cross-check GAAP ponderado", res["hurdle"]["cross_check_gaap"]["ponderado"], 57.87, 0.03)

e = res["economico"]
chk("B2 econ Ke=9,0% bear", e["por_ke"]["0.090"]["cenarios"]["bear"]["preco"], 62.20, 0.03)
chk("B2 econ Ke=9,0% base", e["por_ke"]["0.090"]["cenarios"]["base"]["preco"], 81.41, 0.03)
chk("B2 econ Ke=9,0% bull", e["por_ke"]["0.090"]["cenarios"]["bull"]["preco"], 110.05, 0.05)
chk("B2 econ Ke=9,0% ponderado", e["por_ke"]["0.090"]["cenarios"]["ponderado"], 81.38, 0.03)
chk("B2 faixa ponderada piso (Ke=9,5%)", e["faixa_ponderada"][0], 78.06, 0.03)
chk("B2 faixa ponderada teto (Ke=8,5%)", e["faixa_ponderada"][1], 84.88, 0.03)
chk("B2 teto bull completo (Ke=8,5%)", e["faixa_completa"][1], 116.11, 0.05)
chk("B2 piso bear completo (Ke=9,5%)", e["faixa_completa"][0], 60.55, 0.03)
chk("B2 central ponderado (Ke=9,0%)", e["central_ponderado"], 81.38, 0.03)

r = res["reverse"]
chk("B3 g implícito no hurdle", r["g_implicito_hurdle_base"], 0.415, 0.004)
chk("B3 CAP implícito econ (base)", r["cap_implicito_econ_base"], 35.6, 0.25)
chk("B3 Ke implícito (CAP=15)", r["ke_implicito_cap_teto"], 0.0277, 0.0006)

lad = {x["preco"]: x for x in res["ladder"]}
chk("B4 ladder Ke implícito @187,01", lad[187.01]["ke_implicito"], 0.001, 0.002)
chk("B4 ladder Ke implícito @80", lad[80]["ke_implicito"], 0.0921, 0.0008)
chk("B4 ladder Ke implícito @65", lad[65]["ke_implicito"], 0.1173, 0.0008)
chk("B4 ladder Ke implícito @55", lad[55]["ke_implicito"], 0.1388, 0.0008)
chk("B4 ladder Ke implícito @52", lad[52]["ke_implicito"], 0.1463, 0.0008)
chk("B4 ladder delta até econ central @80", lad[80]["delta_ate_econ_central_pct"], 1.7, 0.2)

v = res["validacao_multiplos"]
chk("B5 P/E atual", v["pe_atual"], 26.12, 0.01)
chk("B5 EV/EBITDA atual (Adj/Adj)", v["ev_ebitda_atual"], 16.34, 0.02)
chk("B5 P/L justo ponderado econ (múltiplo)", v["pl_justo_ponderado_econ"], 11.37, 0.02)
chk("B5 P/L justo ponderado hurdle (múltiplo)", v["pl_justo_ponderado_hurdle"], 8.93, 0.02)
chk("B5 histórico: atual vs mediana %", v["historico_proprio"]["atual_vs_mediana_pct"], 8.8, 0.2)
chk("B5 histórico: P/L justo vs mediana %", v["historico_proprio"]["pl_justo_econ_vs_mediana_pct"], -52.6, 0.3)
chk("B5 comparáveis: mediana dos pares", v["comparaveis"]["mediana_pares"], 27.0, 0.01)
chk("B5 comparáveis: P/L justo vs pares %", v["comparaveis"]["pl_justo_econ_vs_pares_pct"], -57.9, 0.3)
chk_bool("B5 veredicto DIVERGE_MATERIAL com 2 flags",
         v["veredicto"] == "DIVERGE_MATERIAL" and len(v["flags"]) == 2)
chk_bool("B5 posição do múltiplo atual DENTRO_DA_BANDA",
         v["historico_proprio"]["posicao_atual"] == "DENTRO_DA_BANDA")
chk_bool("B5 nenhum preço-alvo emitido pelo bloco de múltiplos",
         "alvo" not in str(v) and "blended" not in str(v))

s, ga = res["sinais"], res["gate"]
chk("B6 preço/hurdle ponderado (~2,92x)", s["preco_sobre_hurdle_pond"], 2.92, 0.02)
chk("B6 prêmio s/ hurdle %", s["premio_sobre_hurdle_pct"], 192.5, 0.5)
chk("B6 prêmio s/ econ central %", s["premio_sobre_econ_central_pct"], 129.8, 0.5)
chk_bool("B6 sinais: SOBREAVALIADO / NAO_ACIONAVEL",
         s["economico"] == "SOBREAVALIADO" and s["entrada"] == "NAO_ACIONAVEL")
chk("B7 gate razão preço/teto bull econ", ga["razao_preco_vs_teto_bull_econ"], 1.61, 0.02)
chk("B7 gate razão CAP implícito/teto", ga["razao_cap_implicito_vs_teto"], 2.37, 0.03)
chk_bool("B7 gate: profundidade SUMARIA (caso VRSK)", ga["modo_recomendado"] == "SUMARIA")

c = res["cap"]
chk_bool("B8 eco de CAP com confiança e justificativas",
         c["cenarios"] == {"bear": 8, "base": 12, "bull": 15}
         and c["confianca"] == "MEDIA"
         and len(c["justificativa_cap"]) > 20 and len(c["justificativa_cenarios"]) > 20)
chk_bool("B8 blocos removidos ausentes do JSON (dcf_fade, grade, multiplos-alvo)",
         all(k not in res for k in ("dcf_fade", "grade", "multiplos")))

print("=" * 100)
print("CAMADA C — validação de inputs (o engine recusa entrada incoerente)")
print("=" * 100)


def espera_recusa(nome, mutacao, trecho):
    inp2 = copy.deepcopy(inp)
    mutacao(inp2)
    try:
        rodar(inp2)
        chk_bool(f"C {nome}", False)
    except ValueError as exc:
        chk_bool(f"C {nome}", trecho in str(exc))


espera_recusa("LPA <= 0 -> instrução de modo custom",
              lambda i: i["fatos"].update(lpa_ajustado_fy=-1.0), "modo custom")
espera_recusa("probabilidades não somam 1",
              lambda i: i["premissas"]["cenarios"]["base"].update(prob=0.60), "somam")
espera_recusa("g >= ROE recusado",
              lambda i: i["premissas"]["cenarios"]["bull"].update(g=0.30), "retenção")
espera_recusa("CAPs fora de ordem recusados",
              lambda i: i["premissas"]["cenarios"]["bear"].update(cap=20), "fora de ordem")
espera_recusa("justificativa_cap obrigatória",
              lambda i: i["premissas"].update(justificativa_cap=""), "justificativa econômica")
espera_recusa("cap_confianca obrigatória",
              lambda i: i["premissas"].update(cap_confianca="X"), "cap_confianca")
espera_recusa("justificativa_cenarios obrigatória",
              lambda i: i["premissas"].update(justificativa_cenarios=" "), "justificativa_cenarios")

print("=" * 100)
if FALHAS:
    print(f"RESULTADO: {len(FALHAS)} FALHA(S): {FALHAS}")
    sys.exit(1)
print("RESULTADO: TODOS OS GOLDEN TESTS PASSARAM")
sys.exit(0)
