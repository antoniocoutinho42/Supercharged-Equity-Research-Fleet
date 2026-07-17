#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
valuation-engine — motor determinístico de valuation do fleet (etapa G3).

Filosofia: TODO cálculo vive aqui (código versionado, testado por golden tests).
O Modelador preenche inputs (.yaml/.json), roda o engine e escreve prosa
interpretativa citando as chaves de resultados.json. Nenhuma aritmética em prosa.

Métodos (fluxo padrão — nada além disso):
  1. MOTOR PRINCIPAL — P/L Justo (franchise-fade, fórmula imutável do mandato):
       P/L = Bracket * SUM_{t=1..CAP} (1+g)^(t-1)/(1+Ke)^t + (1+g)^CAP/[(1+Ke)^CAP * ROE]
       Bracket = (1 - g/ROE) + (DE - NDE) * (g/ROE)
     Duas âncoras (hurdle e econômico), 3 cenários + ponderado, cross-check GAAP.
     Propriedades validadas: ROE=Ke -> P/L = 1/Ke; limite de Gordon; monotonia em Ke.
  2. VALIDAÇÃO POR MÚLTIPLOS (contextualização, NUNCA preço-alvo, NUNCA média):
     (a) comparáveis: P/L justo e múltiplo atual vs. mediana dos pares (mesma base);
     (b) histórico próprio: múltiplo atual vs. banda 5-10a da própria companhia
         (P/L ou EV/EBITDA, métrica primária declarada pelo Modelador).
     Divergência material (> limiar) vira FLAG: revisar premissas e explicar,
     nunca combinar mecanicamente.
  3. Expectativas implícitas no preço (reverse enxuto) + entry ladder + elasticidades.
  4. Gate G3.0 — proporcionalidade -> profundidade (SUMARIA | PADRAO | REFORCADA).

REMOVIDOS na v2.0.0 (decisão de processo, ver CHANGELOG): DCF-fade, grade de
sensibilidade Ke x g x CAP, múltiplos-alvo com preços por cenário. Casos fora do
motor (sem lucro representativo): modo custom, SOMENTE com autorização do
Coordenador — o engine recusa LPA <= 0 com instrução explícita.

Uso:
  python engine.py inputs.yaml [--out DIR] [--chart] [--xlsx]

Saídas em DIR (default: ./saida_<TICKER>):
  resultados.json    — fonte única de verdade numérica (citar por chave)
  grafico_faixas.png (opcional --chart)
  modelo_valores.xlsx (opcional --xlsx; dump de valores, não template vivo)

Dependências: stdlib. Opcionais: pyyaml (inputs .yaml), matplotlib (--chart), openpyxl (--xlsx).
"""

import argparse
import hashlib
import json
import math
import os
import sys
from datetime import datetime, timezone

# CHANGELOG
# v2.1.0 (2026-07-15): transparência de premissas por cenário (comentários R2/R3/R4).
#   (1) NOVO eco opcional em cap: justificativa_g e justificativa_roe (premissas.*),
#       para o Modelador fundamentar g e ROE por cenário com a mesma disciplina do CAP.
#       ECO PURO: não entra em nenhuma conta; o núcleo matemático e todos os números
#       são idênticos à v2.0.0. Por isso é minor (novo campo, zero mudança de fórmula),
#       e os golden tests do caso VRSK permanecem 100% verdes sem alteração de valores.
#   (2) Sem novos campos obrigatórios: ausência de justificativa_g/roe não recusa o input
#       (retrocompatível com inputs v2.0.0). O mandato do Modelador é que passa a exigi-las.
# v2.0.0 (2026-07-15): reconstrução do escopo de métodos.
#   (1) REMOVIDOS: DCF-fade (duas definições + sem fade), grade Ke x g x CAP,
#       múltiplos-alvo (P/E alvo e EV/EBITDA alvo com preços por cenário).
#       Racional: métodos paralelos e sensibilidades que não mudavam a decisão
#       e dobravam tokens; múltiplos deixam de ser preços concorrentes.
#   (2) NOVO bloco validacao_multiplos: comparáveis (pares) e histórico próprio
#       como teste de razoabilidade do P/L Justo, com flags de divergência
#       material (limiar default 30%) — revisão de premissas, nunca média.
#   (3) NOVO bloco validacao: checagens de coerência dos inputs (probabilidades,
#       g < ROE, ordem dos CAPs, justificativas e confiança do CAP obrigatórias).
#       LPA <= 0 -> erro com instrução de modo custom autorizado.
#   (4) Reverse enxuto (3 chaves) e ladder com downside até o valor central.
#   (5) CAP deixa de ter verificador-gate; cap_check.py (novo) emite PARECER.
#       O engine apenas ecoa cap/cap_confianca/justificativas para rastreabilidade.
#   (6) Motor P/L Justo, sinais (3 estados), gate G3.0 e elasticidades: intactos.
#       Chaves preservadas: hurdle.*, economico.*, sinais.*, gate.*,
#       elasticidades.*, ladder[*], reverse.{g_implicito_hurdle_base,
#       cap_implicito_econ_base, ke_implicito_cap_teto}.
# v1.1.0 (2026-07-12): Bracket com DE/NDE; sinal de entrada em 3 estados;
#       gate renomeado para PROFUNDIDADE (SUMARIA | PADRAO | REFORCADA).
# v1.0.0: versão inicial calibrada no caso VRSK.
ENGINE_VERSION = "2.1.0"

# ----------------------------------------------------------------------------
# Núcleo matemático (inalterado desde v1.1.0 — coberto por golden tests)
# ----------------------------------------------------------------------------

def pl_justo(g: float, roe: float, cap: float, ke: float,
             de: float = 0.0, nde: float = 0.0) -> float:
    """Múltiplo P/L Justo (franchise-fade com reversão a book no fim do CAP).
    Bracket = (1 - g/ROE) + (DE - NDE) x (g/ROE), conforme fórmula imutável do mandato;
    DE = dívida/PL e NDE = dívida líquida/PL, MEDIDOS; DE=NDE=0 é exceção declarada."""
    if roe <= 0 or ke <= 0 or cap <= 0:
        raise ValueError("roe, ke e cap devem ser > 0")
    payout = (1.0 - g / roe) + (de - nde) * (g / roe)
    x = (1.0 + g) / (1.0 + ke)
    xcap = x ** cap
    if abs(ke - g) < 1e-12:
        annuity = cap / (1.0 + ke)
    else:
        annuity = (1.0 - xcap) / (ke - g)
    return payout * annuity + xcap / roe


def preco_justo(lpa: float, g: float, roe: float, cap: float, ke: float,
                de: float = 0.0, nde: float = 0.0) -> float:
    return lpa * pl_justo(g, roe, cap, ke, de, nde)


def _bisseccao(f, lo: float, hi: float, tol: float = 1e-10, maxit: int = 300):
    """Raiz de f em [lo,hi]; devolve None se não houver troca de sinal."""
    flo, fhi = f(lo), f(hi)
    if flo == 0.0:
        return lo
    if fhi == 0.0:
        return hi
    if flo * fhi > 0:
        return None
    for _ in range(maxit):
        mid = 0.5 * (lo + hi)
        fm = f(mid)
        if abs(fm) < tol or (hi - lo) < 1e-12:
            return mid
        if flo * fm < 0:
            hi, fhi = mid, fm
        else:
            lo, flo = mid, fm
    return 0.5 * (lo + hi)


def g_implicito(preco, lpa, roe, cap, ke, de=0.0, nde=0.0, lo=-0.20, hi=2.0):
    alvo = preco / lpa
    return _bisseccao(lambda g: pl_justo(g, roe, cap, ke, de, nde) - alvo, lo, hi)


def cap_implicito(preco, lpa, g, roe, ke, de=0.0, nde=0.0, lo=0.5, hi=400.0):
    alvo = preco / lpa
    return _bisseccao(lambda c: pl_justo(g, roe, c, ke, de, nde) - alvo, lo, hi)


def ke_implicito(preco, lpa, g, roe, cap, de=0.0, nde=0.0, lo=1e-6, hi=0.60):
    alvo = preco / lpa
    return _bisseccao(lambda k: pl_justo(g, roe, cap, k, de, nde) - alvo, lo, hi)


def _de_nde(inp):
    f = inp["fatos"]
    de = float(f.get("de", 0.0) or 0.0)
    nde = float(f.get("nde", 0.0) or 0.0)
    medido = ("de" in f) and ("nde" in f)
    return de, nde, medido


# ----------------------------------------------------------------------------
# Validação de inputs (o engine recusa entrada incoerente)
# ----------------------------------------------------------------------------

def bloco_validacao(inp):
    """Checagens duras (erro) e brandas (aviso). Devolve o registro para o JSON."""
    erros, avisos = [], []
    f, p = inp.get("fatos", {}), inp.get("premissas", {})

    lpa = f.get("lpa_ajustado_fy")
    if lpa is None or float(lpa) <= 0:
        erros.append(
            "lpa_ajustado_fy ausente ou <= 0: sem lucro representativo o método padrão "
            "(P/L Justo) é economicamente inadequado. Não force o motor: proponha ao "
            "Coordenador um método específico (modo custom) e aguarde autorização explícita.")

    cen = p.get("cenarios", {})
    nomes = ("bear", "base", "bull")
    if sorted(cen.keys()) != sorted(nomes):
        erros.append("premissas.cenarios deve conter exatamente bear, base e bull")
    else:
        soma_p = sum(float(cen[n]["prob"]) for n in nomes)
        if abs(soma_p - 1.0) > 1e-9:
            erros.append(f"probabilidades dos cenários somam {soma_p:.3f}, devem somar 1,0")
        for n in nomes:
            c = cen[n]
            if float(c["g"]) >= float(c["roe"]):
                erros.append(f"cenário {n}: g ({c['g']}) >= ROE ({c['roe']}) implica retenção "
                             f">100% — incoerente com o motor; reveja g ou ROE")
        caps = {n: float(cen[n]["cap"]) for n in nomes}
        if not (caps["bear"] <= caps["base"] <= caps["bull"]):
            erros.append(f"CAPs fora de ordem (bear {caps['bear']} <= base {caps['base']} "
                         f"<= bull {caps['bull']} é obrigatório)")

    if not str(p.get("justificativa_cap", "")).strip():
        erros.append("premissas.justificativa_cap ausente: o CAP exige justificativa "
                     "econômica escrita (duração dos retornos excedentes da companhia "
                     "consolidada, não anos de histórico disponível)")
    if not str(p.get("justificativa_cenarios", "")).strip():
        erros.append("premissas.justificativa_cenarios ausente: as diferenças de CAP "
                     "bear/base/bull exigem justificativa econômica simples")
    if str(p.get("cap_confianca", "")).upper() not in ("ALTA", "MEDIA", "MÉDIA", "BAIXA"):
        erros.append("premissas.cap_confianca deve ser ALTA, MEDIA ou BAIXA")

    _, _, medido = _de_nde(inp)
    if not medido:
        avisos.append("DE/NDE ausentes dos fatos: assumidos 0/0 — só aceitável como "
                      "exceção declarada com motivo na tabela de premissas")

    mv = p.get("multiplos_validacao", {})
    if str(mv.get("metrica_primaria", "PE")).upper() not in ("PE", "EV_EBITDA"):
        erros.append("multiplos_validacao.metrica_primaria deve ser PE ou EV_EBITDA")
    if not f.get("multiplos_historicos"):
        avisos.append("fatos.multiplos_historicos ausente: validação vs. histórico próprio "
                      "não roda — peça calibração ao Analista se o dado for decisivo")
    if not f.get("pares"):
        avisos.append("fatos.pares ausente: validação vs. comparáveis não roda — peça "
                      "calibração ao Analista se o dado for decisivo")

    if erros:
        raise ValueError("inputs recusados pelo engine:\n- " + "\n- ".join(erros))
    return {"erros": [], "avisos": avisos, "status": "APROVADO"}


# ----------------------------------------------------------------------------
# Blocos de cálculo
# ----------------------------------------------------------------------------

def _pond(cen, valores):
    return sum(cen[n]["prob"] * valores[n] for n in ("bear", "base", "bull"))


def bloco_pl_justo(inp):
    p = inp["premissas"]
    lpa = inp["fatos"]["lpa_ajustado_fy"]
    lpa_gaap = inp["fatos"].get("lpa_gaap_fy")
    cen = p["cenarios"]
    ke_h = p["ke_hurdle"]
    de, nde, medido = _de_nde(inp)

    def rodar(lpa_base, ke):
        out = {}
        for nome in ("bear", "base", "bull"):
            c = cen[nome]
            mult = pl_justo(c["g"], c["roe"], c["cap"], ke, de, nde)
            out[nome] = {"pl": round(mult, 4), "preco": round(lpa_base * mult, 2)}
        out["ponderado"] = round(_pond(cen, {n: out[n]["preco"] for n in ("bear", "base", "bull")}), 2)
        return out

    hurdle = {"ke": ke_h, "lpa_base": lpa, "cenarios": rodar(lpa, ke_h),
              "de_nde": {"de": de, "nde": nde, "medido": medido}}
    if lpa_gaap:
        hurdle["cross_check_gaap"] = rodar(lpa_gaap, ke_h)

    econ = {"por_ke": {}, "lpa_base": lpa}
    for ke in p["ke_economico"]:
        econ["por_ke"][f"{ke:.3f}"] = {"ke": ke, "cenarios": rodar(lpa, ke)}
    ponderados = [v["cenarios"]["ponderado"] for v in econ["por_ke"].values()]
    econ["faixa_ponderada"] = [min(ponderados), max(ponderados)]
    ke_mid = sorted(p["ke_economico"])[len(p["ke_economico"]) // 2]
    econ["ke_central"] = ke_mid
    econ["central_ponderado"] = econ["por_ke"][f"{ke_mid:.3f}"]["cenarios"]["ponderado"]
    todos = [econ["por_ke"][k]["cenarios"][n]["preco"]
             for k in econ["por_ke"] for n in ("bear", "base", "bull")]
    econ["faixa_completa"] = [min(todos), max(todos)]
    return hurdle, econ


def bloco_cap(inp):
    """Eco de rastreabilidade do julgamento de CAP (o parecer vive em cap_check.py)."""
    p = inp["premissas"]
    cen = p["cenarios"]
    out = {
        "cenarios": {n: cen[n]["cap"] for n in ("bear", "base", "bull")},
        "premissas_cenarios": {n: {"prob": cen[n]["prob"], "g": cen[n]["g"],
                                   "roe": cen[n]["roe"], "cap": cen[n]["cap"]}
                               for n in ("bear", "base", "bull")},
        "teto_defensavel": p["cap_teto_defensavel"],
        "confianca": str(p["cap_confianca"]).upper().replace("É", "E"),
        "justificativa_cap": p["justificativa_cap"],
        "justificativa_cenarios": p["justificativa_cenarios"],
    }
    # eco opcional (v2.1.0): fundamentação de g e ROE por cenário (comentário R2).
    # ECO PURO — não entra em nenhuma conta. Ausente = campo omitido (retrocompatível).
    if str(p.get("justificativa_g", "")).strip():
        out["justificativa_g"] = p["justificativa_g"]
    if str(p.get("justificativa_roe", "")).strip():
        out["justificativa_roe"] = p["justificativa_roe"]
    return out


def bloco_reverse(inp, econ):
    """Expectativas implícitas no preço (enxuto): o que o preço exige."""
    p, f = inp["premissas"], inp["fatos"]
    preco, lpa = inp["meta"]["preco_atual"], f["lpa_ajustado_fy"]
    base = p["cenarios"]["base"]
    ke_h, ke_mid = p["ke_hurdle"], econ["ke_central"]
    de, nde, _ = _de_nde(inp)
    r = {
        "g_implicito_hurdle_base": g_implicito(preco, lpa, base["roe"], base["cap"], ke_h, de, nde),
        "cap_implicito_econ_base": cap_implicito(preco, lpa, base["g"], base["roe"], ke_mid, de, nde),
        "ke_implicito_cap_teto": ke_implicito(preco, lpa, base["g"], base["roe"],
                                              p["cap_teto_defensavel"], de, nde),
    }
    return {k: (round(v, 4) if v is not None else None) for k, v in r.items()}


def bloco_ladder(inp, econ):
    p, f = inp["premissas"], inp["fatos"]
    lpa = f["lpa_ajustado_fy"]
    cen = p["cenarios"]["base"]
    ke_mid = econ["ke_central"]
    central = econ["central_ponderado"]
    de, nde, _ = _de_nde(inp)
    precos = [inp["meta"]["preco_atual"]] + list(p.get("ladder_precos", []))
    out = []
    for pr in precos:
        ke_i = ke_implicito(pr, lpa, cen["g"], cen["roe"], cen["cap"], de, nde)
        cap_i = cap_implicito(pr, lpa, cen["g"], cen["roe"], ke_mid, de, nde)
        out.append({
            "preco": pr,
            "ke_implicito": round(ke_i, 4) if ke_i is not None else None,
            "cap_implicito_econ": round(cap_i, 1) if cap_i is not None else None,
            "delta_ate_econ_central_pct": round(100.0 * (central / pr - 1.0), 1),
        })
    return out


def bloco_elasticidades(inp, econ):
    f, p = inp["fatos"], inp["premissas"]
    lpa = f["lpa_ajustado_fy"]
    base = p["cenarios"]["base"]
    de, nde, _ = _de_nde(inp)

    def elast(ke):
        p0 = preco_justo(lpa, base["g"], base["roe"], base["cap"], ke, de, nde)
        return {
            "preco_base": round(p0, 2),
            "mais_1a_cap": round(preco_justo(lpa, base["g"], base["roe"], base["cap"] + 1, ke, de, nde) - p0, 2),
            "mais_1pp_g": round(preco_justo(lpa, base["g"] + 0.01, base["roe"], base["cap"], ke, de, nde) - p0, 2),
            "mais_1pp_roe": round(preco_justo(lpa, base["g"], base["roe"] + 0.01, base["cap"], ke, de, nde) - p0, 2),
            "menos_05pp_ke": round(preco_justo(lpa, base["g"], base["roe"], base["cap"], ke - 0.005, de, nde) - p0, 2),
        }
    return {"hurdle": elast(p["ke_hurdle"]), "economico": elast(econ["ke_central"])}


def _cmp_pct(a, b):
    """a vs b em %, None se b indisponível."""
    if a is None or not b:
        return None
    return round(100.0 * (a / b - 1.0), 1)


def bloco_validacao_multiplos(inp, hurdle, econ):
    """Múltiplos como teste de razoabilidade do P/L Justo — nunca preço-alvo.
    (a) comparáveis: mediana dos pares vs. P/L justo e vs. múltiplo atual;
    (b) histórico próprio: múltiplo atual e P/L justo vs. banda 5-10a própria.
    Divergência material (> limiar) vira flag: revisar premissas e explicar."""
    f, p, m = inp["fatos"], inp["premissas"], inp["meta"]
    mv = p.get("multiplos_validacao", {})
    metrica = str(mv.get("metrica_primaria", "PE")).upper()
    limiar = float(mv.get("limiar_divergencia", 0.30))
    preco, lpa = m["preco_atual"], f["lpa_ajustado_fy"]

    pe_atual = round(preco / lpa, 2)
    pl_justo_econ = round(econ["central_ponderado"] / lpa, 2)
    pl_justo_hurdle = round(hurdle["cenarios"]["ponderado"] / lpa, 2)

    ev_ebitda_atual = None
    chave_ttm = None
    base_lucro = str(mv.get("base_lucro", "ADJUSTED")).upper()
    chave_ttm = "ebitda_adj_ttm_mi" if base_lucro == "ADJUSTED" else "ebitda_gaap_ttm_mi"
    if f.get(chave_ttm) and f.get("divida_liquida_mi") is not None and m.get("acoes_mi"):
        ev = preco * m["acoes_mi"] + f["divida_liquida_mi"]
        ev_ebitda_atual = round(ev / f[chave_ttm], 2)

    flags = []
    out = {
        "metrica_primaria": metrica,
        "base_lucro": base_lucro,
        "limiar_divergencia_pct": round(100.0 * limiar, 0),
        "pe_atual": pe_atual,
        "ev_ebitda_atual": ev_ebitda_atual,
        "pl_justo_ponderado_econ": pl_justo_econ,
        "pl_justo_ponderado_hurdle": pl_justo_hurdle,
    }

    # (a) histórico próprio
    hist_all = f.get("multiplos_historicos") or {}
    chave_hist = "pe" if metrica == "PE" else "ev_ebitda"
    hist = hist_all.get(chave_hist) or {}
    if hist.get("mediana"):
        med = float(hist["mediana"])
        atual = pe_atual if metrica == "PE" else ev_ebitda_atual
        pos = ("ACIMA_DA_BANDA" if atual is not None and atual > float(hist.get("max", med)) else
               "ABAIXO_DA_BANDA" if atual is not None and atual < float(hist.get("min", med)) else
               "DENTRO_DA_BANDA")
        out["historico_proprio"] = {
            "metrica": metrica,
            "min": hist.get("min"), "mediana": med, "max": hist.get("max"),
            "janela": hist.get("janela"), "base": hist.get("base", base_lucro),
            "posicao_atual": pos,
            "atual_vs_mediana_pct": _cmp_pct(atual, med),
            "pl_justo_econ_vs_mediana_pct": _cmp_pct(pl_justo_econ, med) if metrica == "PE" else None,
        }
        if metrica == "PE" and abs(pl_justo_econ / med - 1.0) > limiar:
            flags.append(f"DIVERGENCIA_MATERIAL_HISTORICO: P/L justo econômico ({pl_justo_econ}x) "
                         f"diverge {_cmp_pct(pl_justo_econ, med)}% da mediana histórica própria "
                         f"({med}x) — revisar premissas ou explicar premissa a premissa")
    else:
        out["historico_proprio"] = None

    # (b) comparáveis
    pares = f.get("pares") or []
    chave_par = "pe" if metrica == "PE" else "ev_ebitda"
    valores = sorted(float(x[chave_par]) for x in pares if x.get(chave_par))
    if valores:
        n = len(valores)
        mediana_pares = (valores[n // 2] if n % 2 == 1
                         else 0.5 * (valores[n // 2 - 1] + valores[n // 2]))
        mediana_pares = round(mediana_pares, 2)
        atual = pe_atual if metrica == "PE" else ev_ebitda_atual
        out["comparaveis"] = {
            "metrica": metrica, "n": n,
            "pares": [{"nome": x.get("nome"), chave_par: x.get(chave_par)} for x in pares],
            "mediana_pares": mediana_pares,
            "atual_vs_pares_pct": _cmp_pct(atual, mediana_pares),
            "pl_justo_econ_vs_pares_pct": _cmp_pct(pl_justo_econ, mediana_pares) if metrica == "PE" else None,
        }
        if metrica == "PE" and abs(pl_justo_econ / mediana_pares - 1.0) > limiar:
            flags.append(f"DIVERGENCIA_MATERIAL_COMPARAVEIS: P/L justo econômico ({pl_justo_econ}x) "
                         f"diverge {_cmp_pct(pl_justo_econ, mediana_pares)}% da mediana dos pares "
                         f"({mediana_pares}x) — revisar premissas ou explicar premissa a premissa")
    else:
        out["comparaveis"] = None

    veredicto = "SEM_DADOS"
    if out["historico_proprio"] or out["comparaveis"]:
        veredicto = "DIVERGE_MATERIAL" if flags else "CONVERGE"
    out["veredicto"] = veredicto
    out["flags"] = flags
    out["instrucao"] = ("Divergência material NÃO se resolve por média ou combinação: "
                        "revise as premissas do motor principal ou explique a diferença; "
                        "sem resolução, rebaixe a confiança declarada.")
    return out


def bloco_sinais_e_gate(inp, hurdle, econ, reverse):
    m, p, g = inp["meta"], inp["premissas"], inp.get("gate", {})
    preco = m["preco_atual"]
    hurdle_pond = hurdle["cenarios"]["ponderado"]
    faixa = econ["faixa_ponderada"]
    if preco > faixa[1]:
        sinal_econ = "SOBREAVALIADO"
    elif preco < faixa[0]:
        sinal_econ = "SUBAVALIADO"
    else:
        sinal_econ = "DENTRO_DA_FAIXA"
    ms_min = p.get("ms_minima", 0.12)
    lim_teto = p.get("limitrofe_teto", 1.10)
    if preco <= (1.0 - ms_min) * hurdle_pond:
        sinal_entrada = "ACIONAVEL"
    elif preco <= lim_teto * hurdle_pond:
        sinal_entrada = "LIMITROFE"
    else:
        sinal_entrada = "NAO_ACIONAVEL"
    sinais = {
        "economico": sinal_econ,
        "entrada": sinal_entrada,
        "preco_sobre_hurdle_pond": round(preco / hurdle_pond, 2),
        "premio_sobre_hurdle_pct": round(100.0 * (preco / hurdle_pond - 1.0), 1),
        "premio_sobre_econ_central_pct": round(100.0 * (preco / econ["central_ponderado"] - 1.0), 1),
    }
    teto_bull_econ = econ["faixa_completa"][1]
    razao_preco = preco / teto_bull_econ
    cap_impl = reverse["cap_implicito_econ_base"]
    razao_cap = (cap_impl / p["cap_teto_defensavel"]) if cap_impl else None
    lim_preco = g.get("limiar_preco_vs_bull_econ", 1.4)
    lim_cap = g.get("limiar_cap_implicito_vs_teto", 2.0)
    razoes = []
    if razao_preco >= lim_preco:
        razoes.append(f"preco/teto_bull_econ = {razao_preco:.2f} >= {lim_preco}")
    if razao_cap is not None and razao_cap >= lim_cap:
        razoes.append(f"cap_implicito/teto_defensavel = {razao_cap:.2f} >= {lim_cap}")
    if razoes:
        modo = "SUMARIA"
    elif sinal_entrada in ("ACIONAVEL", "LIMITROFE"):
        modo = "REFORCADA"
        razoes.append(f"entrada {sinal_entrada} (preco ate {lim_teto:.2f}x o hurdle ponderado): proximidade de compra")
    else:
        modo = "PADRAO"
        razoes.append("zona de debate (nem inequivocamente caro, nem em zona de compra)")
    gate = {"modo_recomendado": modo,
            "razao_preco_vs_teto_bull_econ": round(razao_preco, 2),
            "razao_cap_implicito_vs_teto": round(razao_cap, 2) if razao_cap else None,
            "limiares": {"preco_vs_bull_econ": lim_preco,
                         "cap_implicito_vs_teto": lim_cap,
                         "ms_minima": ms_min, "limitrofe_teto": lim_teto},
            "razoes": razoes}
    return sinais, gate


# ----------------------------------------------------------------------------
# Orquestração, IO e saídas
# ----------------------------------------------------------------------------

def carregar_inputs(caminho):
    with open(caminho, "r", encoding="utf-8") as fh:
        bruto = fh.read()
    if caminho.endswith((".yaml", ".yml")):
        try:
            import yaml
        except ImportError:
            sys.exit("pyyaml ausente: instale (pip install pyyaml) ou use inputs em .json")
        dados = yaml.safe_load(bruto)
    else:
        dados = json.loads(bruto)
    dados["_hash_inputs"] = hashlib.sha256(bruto.encode("utf-8")).hexdigest()[:16]
    return dados


def rodar(inp):
    validacao = bloco_validacao(inp)
    hurdle, econ = bloco_pl_justo(inp)
    cap = bloco_cap(inp)
    reverse = bloco_reverse(inp, econ)
    ladder = bloco_ladder(inp, econ)
    elast = bloco_elasticidades(inp, econ)
    val_mult = bloco_validacao_multiplos(inp, hurdle, econ)
    sinais, gate = bloco_sinais_e_gate(inp, hurdle, econ, reverse)
    return {
        "engine": {"versao": ENGINE_VERSION,
                   "hash_inputs": inp["_hash_inputs"],
                   "gerado_em": datetime.now(timezone.utc).isoformat(timespec="seconds")},
        "meta": inp["meta"],
        "validacao": validacao,
        "gate": gate,
        "sinais": sinais,
        "hurdle": hurdle,
        "economico": econ,
        "cap": cap,
        "reverse": reverse,
        "ladder": ladder,
        "elasticidades": elast,
        "validacao_multiplos": val_mult,
    }


def gerar_grafico(res, caminho):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    preco = res["meta"]["preco_atual"]
    h = res["hurdle"]["cenarios"]
    e = res["economico"]
    linhas = [
        ("Preço máx. hurdle", h["bear"]["preco"], h["bull"]["preco"], h["ponderado"]),
        ("Valor econômico (P/L Justo)", e["faixa_completa"][0], e["faixa_completa"][1], e["central_ponderado"]),
    ]
    fig, ax = plt.subplots(figsize=(9, 3.2))
    for i, (rot, lo, hi, centro) in enumerate(reversed(linhas)):
        ax.hlines(i, lo, hi, lw=8, alpha=0.45)
        ax.plot(centro, i, "o", ms=9)
        ax.annotate(f"US$ {lo:.0f}-{hi:.0f}", (hi, i), xytext=(6, -3),
                    textcoords="offset points", fontsize=8)
    ax.axvline(preco, ls="--", color="k", lw=1)
    ax.annotate(f"Preço atual\nUS$ {preco:.2f}", (preco, len(linhas) - 0.4),
                fontsize=8, ha="center")
    ax.set_yticks(range(len(linhas)))
    ax.set_yticklabels([r[0] for r in reversed(linhas)], fontsize=8)
    ax.set_xlabel("Preço por ação")
    ax.set_title(f"{res['meta']['ticker']} — preço atual vs. faixas do motor principal "
                 f"(círculo = ponderado/central)", fontsize=10)
    fig.tight_layout()
    fig.savefig(caminho, dpi=150)
    plt.close(fig)


def gerar_xlsx(inp, res, caminho):
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Inputs"
    ws.append(["Bloco", "Chave", "Valor"])
    for bloco in ("meta", "fatos"):
        for k, v in inp[bloco].items():
            ws.append([bloco, k, json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v])
    ws2 = wb.create_sheet("Resultados")
    ws2.append(["Chave (usar na prosa)", "Valor"])

    def achatar(prefixo, obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                achatar(f"{prefixo}.{k}" if prefixo else k, v)
        elif isinstance(obj, list):
            ws2.append([prefixo, json.dumps(obj, ensure_ascii=False)])
        else:
            ws2.append([prefixo, obj])
    achatar("", res)
    wb.save(caminho)


def main(argv=None):
    ap = argparse.ArgumentParser(description="valuation-engine (G3)")
    ap.add_argument("inputs", help="inputs .yaml ou .json")
    ap.add_argument("--out", default=None, help="diretório de saída")
    ap.add_argument("--chart", action="store_true")
    ap.add_argument("--xlsx", action="store_true")
    args = ap.parse_args(argv)
    inp = carregar_inputs(args.inputs)
    res = rodar(inp)
    out = args.out or f"saida_{inp['meta']['ticker']}"
    os.makedirs(out, exist_ok=True)
    dest = os.path.join(out, "resultados.json")
    with open(dest, "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=2)
    print(f"[engine v{ENGINE_VERSION}] resultados -> {dest}")
    print(f"  gate: {res['gate']['modo_recomendado']} | sinais: entrada="
          f"{res['sinais']['entrada']}, economico={res['sinais']['economico']}")
    print(f"  hurdle ponderado: {res['hurdle']['cenarios']['ponderado']} | "
          f"econ faixa ponderada: {res['economico']['faixa_ponderada']}")
    print(f"  validacao_multiplos: {res['validacao_multiplos']['veredicto']}")
    for a in res["validacao"]["avisos"]:
        print("  AVISO:", a)
    if args.chart:
        c = os.path.join(out, "grafico_faixas.png")
        gerar_grafico(res, c)
        print(f"  grafico -> {c}")
    if args.xlsx:
        x = os.path.join(out, "modelo_valores.xlsx")
        gerar_xlsx(inp, res, x)
        print(f"  xlsx -> {x}")
    return res


if __name__ == "__main__":
    main()
