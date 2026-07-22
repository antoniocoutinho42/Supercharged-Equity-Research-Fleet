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
     Duas âncoras (hurdle SOMENTE quando o usuário informa o retorno exigido — sem
     default — e econômico), 3 cenários + ponderado, cross-check GAAP.
     Propriedades validadas: ROE=Ke -> P/L = 1/Ke; limite de Gordon; monotonia em Ke.
  2. VALIDAÇÃO POR MÚLTIPLOS (contextualização, NUNCA preço-alvo, NUNCA média):
     (a) comparáveis: P/L justo e múltiplo atual vs. mediana dos pares (mesma base);
     (b) histórico próprio: múltiplo atual vs. banda 5-10a da própria companhia
         (P/L ou EV/EBITDA, métrica primária declarada pelo Modelador).
     Divergência material (> limiar) vira FLAG: revisar premissas e explicar,
     nunca combinar mecanicamente.
  3. Expectativas implícitas no preço (reverse enxuto) + entry ladder + elasticidades
     (com experimento declarado e alerta de sinal contraintuitivo — R4) + matrizes de
     sensibilidade 3x3 por âncora (R6).
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
# v3.0.0 (2026-07-20): correções sistêmicas pós-feedback do caso HG (R2/R3/R4/R5/R6).
#   BREAKING (contrato de inputs):
#   (1) R2 — INPUTS ESTRUTURAIS NUNCA ZERADOS POR LACUNA: fatos.de/fatos.nde
#       ausentes deixam de virar 0/0 com aviso; o engine RECUSA, salvo exceção
#       declarada em premissas.excecao_de_nde {motivo, de_substituto, nde_substituto,
#       faixa_alternativa {de, nde}}. Com a exceção, o engine CALCULA a sensibilidade
#       da premissa substituta (novo bloco de_nde.excecao.sensibilidade) — a
#       declaração sozinha não basta. Semântica confirmada na fonte: DE = dívida
#       bruta/PL, NDE = dívida líquida/PL, medidos; (DE − NDE) = caixa/PL; o "caixa"
#       do bracket é caixa livre no sentido econômico da fórmula (em negócios com
#       float, decidir o que é caixa livre é decisão econômica do Modelador).
#   (2) R3 — HURDLE EXCLUSIVAMENTE DO USUÁRIO: premissas.ke_hurdle passa a ser
#       OPCIONAL. Ausente: hurdle = null, sinais.entrada = SEM_HURDLE, reverse e
#       elasticidades da âncora hurdle nulos, gate degrada para a âncora econômica,
#       e sinais.nota_hurdle declara a ausência em uma linha. Nenhum default.
#   NOVOS BLOCOS (aditivos):
#   (3) R4 — elasticidades.experimento declara o ceteris paribus de cada
#       elasticidade; elasticidades.alertas_sinal compara sinal observado vs.
#       esperado economicamente e exige resposta do Modelador
#       (premissas.respostas_sinais.<parametro>) — publicação bloqueada pelo
#       checar.py enquanto houver alerta sem resposta.
#   (4) R5 — premissas.resolucao_divergencia {via: REVISAO_PREMISSAS |
#       EXPLICACAO_FUNDAMENTADA | ADAPTACAO_METODOLOGICA, texto} ecoada em
#       validacao_multiplos.resolucao; DIVERGE_MATERIAL sem resolução bloqueia a
#       publicação (checar.py), nunca segue como "ressalva declarada".
#   (5) R6 — bloco matrizes: 3 matrizes 3×3 por âncora (CAP×ROE com g base fixo;
#       CAP×g com ROE base fixo; ROE×g com CAP base fixo), preço por ação em cada
#       célula, eixos nas premissas bear/base/bull, fixos declarados (herda o R4);
#       célula com g >= ROE vira null (retenção > 100%, economicamente incoerente).
#   Núcleo matemático pl_justo() INALTERADO (golden camadas A/B intactas).
# v2.2.0 (2026-07-15): m_terminal (multiplicador do termo terminal, default 1.0,
#   retrocompatível): permite valor terminal por book econômico em vez de book
#   contábil; exige justificativa_m_terminal quando != 1.0.
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
ENGINE_VERSION = "3.0.0"

# ----------------------------------------------------------------------------
# Núcleo matemático (inalterado desde v1.1.0 — coberto por golden tests)
# ----------------------------------------------------------------------------

def pl_justo(g: float, roe: float, cap: float, ke: float,
             de: float = 0.0, nde: float = 0.0, m_terminal: float = 1.0) -> float:
    """Múltiplo P/L Justo (franchise-fade com reversão a book no fim do CAP).
    Bracket = (1 - g/ROE) + (DE - NDE) x (g/ROE), conforme fórmula imutável do mandato;
    DE = dívida/PL e NDE = dívida líquida/PL, MEDIDOS; DE=NDE=0 é exceção declarada.
    m_terminal (v2.2.0): multiplicador do TERMO TERMINAL, default 1.0 (retrocompatível
    byte-a-byte). Permite valor terminal por book econômico em vez de book contábil."""
    if roe <= 0 or ke <= 0 or cap <= 0:
        raise ValueError("roe, ke e cap devem ser > 0")
    if m_terminal <= 0:
        raise ValueError("m_terminal deve ser > 0")
    payout = (1.0 - g / roe) + (de - nde) * (g / roe)
    x = (1.0 + g) / (1.0 + ke)
    xcap = x ** cap
    if abs(ke - g) < 1e-12:
        annuity = cap / (1.0 + ke)
    else:
        annuity = (1.0 - xcap) / (ke - g)
    return payout * annuity + m_terminal * xcap / roe


def preco_justo(lpa: float, g: float, roe: float, cap: float, ke: float,
                de: float = 0.0, nde: float = 0.0, m_terminal: float = 1.0) -> float:
    return lpa * pl_justo(g, roe, cap, ke, de, nde, m_terminal)


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


def g_implicito(preco, lpa, roe, cap, ke, de=0.0, nde=0.0, m_terminal=1.0, lo=-0.20, hi=2.0):
    alvo = preco / lpa
    return _bisseccao(lambda g: pl_justo(g, roe, cap, ke, de, nde, m_terminal) - alvo, lo, hi)


def cap_implicito(preco, lpa, g, roe, ke, de=0.0, nde=0.0, m_terminal=1.0, lo=0.5, hi=400.0):
    alvo = preco / lpa
    return _bisseccao(lambda c: pl_justo(g, roe, c, ke, de, nde, m_terminal) - alvo, lo, hi)


def ke_implicito(preco, lpa, g, roe, cap, de=0.0, nde=0.0, m_terminal=1.0, lo=1e-6, hi=0.60):
    alvo = preco / lpa
    return _bisseccao(lambda k: pl_justo(g, roe, cap, k, de, nde, m_terminal) - alvo, lo, hi)


def _excecao_de_nde(inp):
    """Exceção declarada (R2) quando DE/NDE não puderam ser medidos.
    Formato: premissas.excecao_de_nde {motivo, de_substituto, nde_substituto,
    faixa_alternativa {de, nde}}. A validação dura vive em bloco_validacao."""
    exc = (inp.get("premissas") or {}).get("excecao_de_nde")
    return exc if isinstance(exc, dict) else None


def _de_nde(inp):
    """DE = dívida bruta/PL e NDE = dívida líquida/PL, MEDIDOS (fatos.de/fatos.nde).
    (DE − NDE) = caixa/PL — caixa LIVRE no sentido econômico da fórmula, decisão
    do Modelador registrada na ficha. R2: ausência de medição NUNCA vira 0/0
    silencioso; exige exceção declarada (premissas.excecao_de_nde), cujos
    substitutos alimentam o cálculo e cuja sensibilidade o engine calcula."""
    f = inp["fatos"]
    medido = (f.get("de") is not None) and (f.get("nde") is not None)
    if medido:
        return float(f["de"]), float(f["nde"]), True
    exc = _excecao_de_nde(inp) or {}
    de = float(exc.get("de_substituto", 0.0) or 0.0)
    nde = float(exc.get("nde_substituto", 0.0) or 0.0)
    return de, nde, False


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

        # m_terminal (v2.2.0): validação dura (<=0, justificativa quando != 1.0) e
        # branda (ordem bear <= base <= bull recomendada, mas não obrigatória).
        m_terminais = {n: _m_terminal(cen[n]) for n in nomes}
        for n in nomes:
            if m_terminais[n] <= 0:
                erros.append(f"cenário {n}: m_terminal ({m_terminais[n]}) deve ser > 0")
        if any(abs(m_terminais[n] - 1.0) > 1e-12 for n in nomes):
            if not str(p.get("justificativa_m_terminal", "")).strip():
                erros.append("premissas.justificativa_m_terminal ausente: m_terminal != 1.0 "
                             "exige justificativa registrada")
        if not (m_terminais["bear"] <= m_terminais["base"] <= m_terminais["bull"]):
            avisos.append("m_terminal fora de ordem (bear <= base <= bull recomendado)")

    if not str(p.get("justificativa_cap", "")).strip():
        erros.append("premissas.justificativa_cap ausente: o CAP exige justificativa "
                     "econômica escrita (duração dos retornos excedentes da companhia "
                     "consolidada, não anos de histórico disponível)")
    if not str(p.get("justificativa_cenarios", "")).strip():
        erros.append("premissas.justificativa_cenarios ausente: as diferenças de CAP "
                     "bear/base/bull exigem justificativa econômica simples")
    if str(p.get("cap_confianca", "")).upper() not in ("ALTA", "MEDIA", "MÉDIA", "BAIXA"):
        erros.append("premissas.cap_confianca deve ser ALTA, MEDIA ou BAIXA")

    # R2 — input estrutural nunca zerado por lacuna de coleta (regra dura).
    _, _, medido = _de_nde(inp)
    if not medido:
        exc = _excecao_de_nde(inp)
        if not exc:
            erros.append(
                "fatos.de/fatos.nde ausentes (DE = dívida bruta/PL; NDE = dívida líquida/PL, "
                "MEDIDOS): um input estrutural da fórmula não pode ser zerado por lacuna de "
                "coleta. Ou o Analista mede DE/NDE (o plano de coleta deve prever o dado que "
                "a definição do bracket exige, incluindo a discriminação de caixa livre), ou o "
                "Modelador declara premissas.excecao_de_nde {motivo, de_substituto, "
                "nde_substituto, faixa_alternativa {de, nde}} — justificativa econômica E "
                "sensibilidade, nunca só uma declaração.")
        else:
            if len(str(exc.get("motivo", "")).strip()) < 20:
                erros.append("premissas.excecao_de_nde.motivo ausente ou insuficiente: a exceção "
                             "exige justificativa econômica registrada (por que a medição é "
                             "genuinamente impossível e o que o substituto representa)")
            faixa = exc.get("faixa_alternativa") or {}
            if not (isinstance(faixa, dict) and faixa.get("de") is not None
                    and faixa.get("nde") is not None):
                erros.append("premissas.excecao_de_nde.faixa_alternativa {de, nde} ausente: sem a "
                             "faixa plausível alternativa o engine não consegue calcular a "
                             "sensibilidade do impacto da premissa substituta no valor")

    # H11 (v3.1.0) — φ é SAÍDA (sensibilidade_phi), nunca input do motor: exclusão
    # mútua com m_terminal (mesma alavanca — spread terminal). Declarar premissas.phi
    # é recusado sempre; a mensagem distingue o caso com m_terminal manual.
    if p.get("phi") is not None:
        if any(abs(_m_terminal(cen[n]) - 1.0) > 1e-12 for n in nomes if isinstance(cen.get(n), dict)):
            erros.append("premissas.phi e m_terminal != 1 são mutuamente exclusivos (a mesma "
                         "alavanca de spread terminal): declare UM só — m_terminal por cenário "
                         "com justificativa, OU nenhum (φ é saída de sensibilidade, não input)")
        else:
            erros.append("premissas.phi é reservado: a sensibilidade a spread terminal "
                         "(sensibilidade_phi) é SAÍDA de primeira classe com default "
                         "conservador φ=0; para terminal por book econômico use m_terminal "
                         "por cenário com justificativa_m_terminal (exclusão mútua)")

    # R3 — hurdle exclusivamente do usuário: opcional; quando presente, sanidade.
    ke_h = p.get("ke_hurdle")
    if ke_h is not None and (not isinstance(ke_h, (int, float)) or float(ke_h) <= 0):
        erros.append("premissas.ke_hurdle inválido: quando informado pelo usuário deve ser > 0; "
                     "sem resposta do usuário, OMITA o campo (nenhum default é permitido)")

    # R4 — respostas a sinais contraintuitivos: mapa parametro -> texto.
    rs = p.get("respostas_sinais")
    if rs is not None and not isinstance(rs, dict):
        erros.append("premissas.respostas_sinais deve ser um mapa parametro -> resposta "
                     "(mecanismo econômico E plausibilidade do experimento)")

    # R5 — resolução da divergência de múltiplos: estrutura validada quando presente.
    rd = p.get("resolucao_divergencia")
    if rd is not None:
        vias = ("REVISAO_PREMISSAS", "EXPLICACAO_FUNDAMENTADA", "ADAPTACAO_METODOLOGICA")
        if not isinstance(rd, dict) or str(rd.get("via", "")).upper() not in vias:
            erros.append("premissas.resolucao_divergencia.via deve ser REVISAO_PREMISSAS, "
                         "EXPLICACAO_FUNDAMENTADA ou ADAPTACAO_METODOLOGICA")
        elif len(str(rd.get("texto", "")).strip()) < 40:
            erros.append("premissas.resolucao_divergencia.texto insuficiente: a resolução exige "
                         "fundamentação econômica premissa a premissa, não uma declaração")

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


def _m_terminal(c):
    """m_terminal do cenário (v2.2.0): default 1.0 se ausente, retrocompatível."""
    m = c.get("m_terminal", 1.0)
    return 1.0 if m is None else float(m)


def bloco_pl_justo(inp):
    p = inp["premissas"]
    lpa = inp["fatos"]["lpa_ajustado_fy"]
    lpa_gaap = inp["fatos"].get("lpa_gaap_fy")
    cen = p["cenarios"]
    ke_h = p.get("ke_hurdle")  # R3: opcional; SOMENTE o usuário informa, sem default
    de, nde, medido = _de_nde(inp)

    def rodar(lpa_base, ke):
        out = {}
        for nome in ("bear", "base", "bull"):
            c = cen[nome]
            mult = pl_justo(c["g"], c["roe"], c["cap"], ke, de, nde, _m_terminal(c))
            out[nome] = {"pl": round(mult, 4), "preco": round(lpa_base * mult, 2)}
        out["ponderado"] = round(_pond(cen, {n: out[n]["preco"] for n in ("bear", "base", "bull")}), 2)
        return out

    if ke_h is None:
        hurdle = None
    else:
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


def bloco_de_nde(inp, hurdle, econ):
    """R2: rastreabilidade do bracket. Medido: eco simples. Exceção declarada:
    o engine CALCULA a sensibilidade da premissa substituta (ponderado com os
    substitutos vs. com a faixa alternativa plausível) — a exceção nunca é só
    uma declaração."""
    de, nde, medido = _de_nde(inp)
    out = {"de": de, "nde": nde, "medido": medido,
           "definicao": "DE = dívida bruta/PL; NDE = dívida líquida/PL; (DE − NDE) = "
                        "caixa livre/PL no sentido econômico do bracket (decisão registrada "
                        "do Modelador sobre o que conta como caixa livre)"}
    if medido:
        out["excecao"] = None
        return out
    exc = _excecao_de_nde(inp)
    faixa = exc["faixa_alternativa"]
    de_alt, nde_alt = float(faixa["de"]), float(faixa["nde"])
    p, f = inp["premissas"], inp["fatos"]
    lpa = f["lpa_ajustado_fy"]
    cen = p["cenarios"]

    def pond(ke, d, n_):
        precos = {n: lpa * pl_justo(cen[n]["g"], cen[n]["roe"], cen[n]["cap"], ke, d, n_,
                                    _m_terminal(cen[n]))
                  for n in ("bear", "base", "bull")}
        return round(_pond(cen, precos), 2)

    ke_c = econ["ke_central"]
    sens = {
        "econ_central_substituto": pond(ke_c, de, nde),
        "econ_central_alternativa": pond(ke_c, de_alt, nde_alt),
    }
    sens["delta_econ_central_pct"] = round(
        100.0 * (sens["econ_central_alternativa"] / sens["econ_central_substituto"] - 1.0), 1)
    if hurdle is not None:
        sens["hurdle_ponderado_substituto"] = pond(hurdle["ke"], de, nde)
        sens["hurdle_ponderado_alternativa"] = pond(hurdle["ke"], de_alt, nde_alt)
        sens["delta_hurdle_ponderado_pct"] = round(
            100.0 * (sens["hurdle_ponderado_alternativa"] / sens["hurdle_ponderado_substituto"] - 1.0), 1)
    out["excecao"] = {"motivo": exc.get("motivo"),
                      "de_substituto": de, "nde_substituto": nde,
                      "faixa_alternativa": {"de": de_alt, "nde": nde_alt},
                      "sensibilidade": sens}
    return out


def bloco_cap(inp):
    """Eco de rastreabilidade do julgamento de CAP (o parecer vive em cap_check.py)."""
    p = inp["premissas"]
    cen = p["cenarios"]
    out = {
        "cenarios": {n: cen[n]["cap"] for n in ("bear", "base", "bull")},
        "premissas_cenarios": {n: {"prob": cen[n]["prob"], "g": cen[n]["g"],
                                   "roe": cen[n]["roe"], "cap": cen[n]["cap"],
                                   "m_terminal": _m_terminal(cen[n])}
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
    # eco opcional (v2.2.0): fundamentação do m_terminal (comentário item 6 do brief).
    # ECO PURO — não entra em nenhuma conta. Ausente = campo omitido (retrocompatível).
    if str(p.get("justificativa_m_terminal", "")).strip():
        out["justificativa_m_terminal"] = p["justificativa_m_terminal"]
    return out


def bloco_reverse(inp, econ):
    """Expectativas implícitas no preço (enxuto): o que o preço exige."""
    p, f = inp["premissas"], inp["fatos"]
    preco, lpa = inp["meta"]["preco_atual"], f["lpa_ajustado_fy"]
    base = p["cenarios"]["base"]
    ke_h, ke_mid = p.get("ke_hurdle"), econ["ke_central"]
    de, nde, _ = _de_nde(inp)
    m_base = _m_terminal(base)  # reverse usa o m_terminal do cenário BASE (âncora central)
    r = {
        # R3: sem hurdle informado pelo usuário, a leitura ancorada nele não existe
        "g_implicito_hurdle_base": (g_implicito(preco, lpa, base["roe"], base["cap"], ke_h, de, nde, m_base)
                                    if ke_h is not None else None),
        "cap_implicito_econ_base": cap_implicito(preco, lpa, base["g"], base["roe"], ke_mid, de, nde, m_base),
        "ke_implicito_cap_teto": ke_implicito(preco, lpa, base["g"], base["roe"],
                                              p["cap_teto_defensavel"], de, nde, m_base),
    }
    return {k: (round(v, 4) if v is not None else None) for k, v in r.items()}


def bloco_ladder(inp, econ):
    p, f = inp["premissas"], inp["fatos"]
    lpa = f["lpa_ajustado_fy"]
    cen = p["cenarios"]["base"]
    ke_mid = econ["ke_central"]
    central = econ["central_ponderado"]
    de, nde, _ = _de_nde(inp)
    m_base = _m_terminal(cen)
    precos = [inp["meta"]["preco_atual"]] + list(p.get("ladder_precos", []))
    out = []
    for pr in precos:
        ke_i = ke_implicito(pr, lpa, cen["g"], cen["roe"], cen["cap"], de, nde, m_base)
        cap_i = cap_implicito(pr, lpa, cen["g"], cen["roe"], ke_mid, de, nde, m_base)
        out.append({
            "preco": pr,
            "ke_implicito": round(ke_i, 4) if ke_i is not None else None,
            "cap_implicito_econ": round(cap_i, 1) if cap_i is not None else None,
            "delta_ate_econ_central_pct": round(100.0 * (central / pr - 1.0), 1),
        })
    return out


EXPERIMENTO_ELASTICIDADES = {
    # R4: toda sensibilidade declara seu experimento — o que fica FIXO e o que a
    # variação implica. Texto gerado por código, injetado no relatório pela composição.
    "mais_1a_cap": "Varia só a duração da vantagem (CAP +1 ano); mantém fixos lucro (LPA), "
                   "g, ROE, Ke, DE/NDE e m_terminal do cenário base.",
    "mais_1pp_g": "Varia só o crescimento (g +1 p.p.); mantém fixos lucro, ROE, CAP, Ke, "
                  "DE/NDE e m_terminal. Com ROE fixo, mais g exige mais retenção "
                  "(payout cai): o experimento move crescimento E retenção juntos.",
    "mais_1pp_roe": "Varia só a rentabilidade (ROE +1 p.p.); mantém fixos LUCRO, g, CAP, Ke, "
                    "DE/NDE e m_terminal. Com lucro fixo, mais ROE implica patrimônio "
                    "implícito MENOR (book = lucro/ROE) e book terminal menor — o experimento "
                    "move duas coisas ao mesmo tempo. Onde o patrimônio é observado e "
                    "regulatório (seguradoras, bancos), esta variação pode não corresponder a "
                    "nenhuma variação real da companhia: redesenhe ou reenquadre.",
    "menos_05pp_ke": "Varia só a taxa de desconto (Ke −0,5 p.p.); mantém todo o resto fixo.",
}


def bloco_elasticidades(inp, econ):
    f, p = inp["fatos"], inp["premissas"]
    lpa = f["lpa_ajustado_fy"]
    base = p["cenarios"]["base"]
    ke_h = p.get("ke_hurdle")
    de, nde, _ = _de_nde(inp)
    m_base = _m_terminal(base)
    respostas = p.get("respostas_sinais") or {}

    def elast(ke):
        p0 = preco_justo(lpa, base["g"], base["roe"], base["cap"], ke, de, nde, m_base)
        return {
            "preco_base": round(p0, 2),
            "mais_1a_cap": round(preco_justo(lpa, base["g"], base["roe"], base["cap"] + 1, ke, de, nde, m_base) - p0, 2),
            "mais_1pp_g": round(preco_justo(lpa, base["g"] + 0.01, base["roe"], base["cap"], ke, de, nde, m_base) - p0, 2),
            "mais_1pp_roe": round(preco_justo(lpa, base["g"], base["roe"] + 0.01, base["cap"], ke, de, nde, m_base) - p0, 2),
            "menos_05pp_ke": round(preco_justo(lpa, base["g"], base["roe"], base["cap"], ke - 0.005, de, nde, m_base) - p0, 2),
        }

    def sinais_esperados(ke):
        """Sinal ECONOMICAMENTE esperado por parâmetro. CAP e g criam valor sse há
        spread (ROE > Ke) — invariante ROE=Ke ⇒ P/L = 1/Ke. ROE: expectativa
        econômica ingênua é POSITIVO ('mais rentabilidade, mais valor'); quando o
        experimento (lucro fixo ⇒ book encolhe) inverte o sinal, isso é alerta,
        não erro — e exige explicação de mecanismo E plausibilidade (R4b)."""
        spread_pos = base["roe"] > ke
        return {
            "mais_1a_cap": "POSITIVO" if spread_pos else "NEGATIVO",
            "mais_1pp_g": "POSITIVO" if spread_pos else "NEGATIVO",
            "mais_1pp_roe": "POSITIVO",
            "menos_05pp_ke": "POSITIVO",
        }

    def alertas(nome_ancora, ke, valores):
        out = []
        esperados = sinais_esperados(ke)
        for parametro, esperado in esperados.items():
            v = valores[parametro]
            if abs(v) < 0.005:
                continue
            observado = "POSITIVO" if v > 0 else "NEGATIVO"
            if observado != esperado:
                resposta = str(respostas.get(parametro, "")).strip()
                out.append({
                    "ancora": nome_ancora, "parametro": parametro,
                    "valor": v, "sinal_esperado": esperado, "sinal_observado": observado,
                    "exigencia": "Sinal contrário à relação econômica esperada: verificar "
                                 "cálculo e interações entre premissas; se válido, explicar o "
                                 "MECANISMO econômico e a PLAUSIBILIDADE do experimento (a "
                                 "explicação algébrica sozinha não basta); se não, corrigir a "
                                 "especificação. Publicação bloqueada sem resposta.",
                    "respondido": bool(resposta),
                    "resposta": resposta or None,
                })
        return out

    econ_vals = elast(econ["ke_central"])
    todos_alertas = alertas("economico", econ["ke_central"], econ_vals)
    if ke_h is not None:
        hurdle_vals = elast(ke_h)
        todos_alertas += alertas("hurdle", ke_h, hurdle_vals)
    else:
        hurdle_vals = None  # R3: sem hurdle informado, a âncora não existe
    return {"hurdle": hurdle_vals, "economico": econ_vals,
            "experimento": EXPERIMENTO_ELASTICIDADES,
            "alertas_sinal": todos_alertas}


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
    pl_justo_hurdle = (round(hurdle["cenarios"]["ponderado"] / lpa, 2)
                       if hurdle is not None else None)

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
    # R5: a resolução registrada pelo Modelador é ecoada aqui; sem ela,
    # DIVERGE_MATERIAL BLOQUEIA a publicação (checar.py --etapa valuation).
    rd = p.get("resolucao_divergencia")
    if isinstance(rd, dict) and rd.get("via"):
        out["resolucao"] = {"via": str(rd["via"]).upper(), "texto": str(rd.get("texto", "")).strip()}
    else:
        out["resolucao"] = None
    out["instrucao"] = ("Divergência material NÃO se resolve por média, combinação nem "
                        "ressalva declarada: (a) revise premissas até reconciliar, (b) explique "
                        "premissa a premissa por que o mercado estaria errando (evidência + "
                        "observável que arbitra e quando), ou (c) adapte a metodologia via "
                        "julgamento metodológico (R1). Registre em premissas.resolucao_divergencia; "
                        "sem resolução o caso NÃO avança para publicação.")
    return out


def bloco_sinais_e_gate(inp, hurdle, econ, reverse):
    m, p, g = inp["meta"], inp["premissas"], inp.get("gate", {})
    preco = m["preco_atual"]
    faixa = econ["faixa_ponderada"]
    if preco > faixa[1]:
        sinal_econ = "SOBREAVALIADO"
    elif preco < faixa[0]:
        sinal_econ = "SUBAVALIADO"
    else:
        sinal_econ = "DENTRO_DA_FAIXA"
    ms_min = p.get("ms_minima", 0.12)
    lim_teto = p.get("limitrofe_teto", 1.10)
    if hurdle is None:
        # R3: sem retorno exigido informado pelo usuário não existe sinal de
        # entrada, disciplina de compra nem nada derivado do hurdle. Degrade
        # limpo para a âncora econômica, com a ausência declarada em uma linha.
        sinal_entrada = "SEM_HURDLE"
        sinais = {
            "economico": sinal_econ,
            "entrada": sinal_entrada,
            "preco_sobre_hurdle_pond": None,
            "premio_sobre_hurdle_pct": None,
            "premio_sobre_econ_central_pct": round(100.0 * (preco / econ["central_ponderado"] - 1.0), 1),
            "nota_hurdle": "Retorno mínimo exigido não informado pelo usuário: sinal de "
                           "entrada, preço máximo para o hurdle e degraus ancorados nele não "
                           "foram calculados; a leitura usa a âncora econômica.",
        }
    else:
        hurdle_pond = hurdle["cenarios"]["ponderado"]
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
    elif sinal_entrada == "SEM_HURDLE" and sinal_econ == "SUBAVALIADO":
        modo = "REFORCADA"
        razoes.append("sem hurdle informado: proximidade de decisão avaliada pela âncora "
                      "econômica (preço abaixo da faixa ponderada)")
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


def bloco_matrizes(inp, econ):
    """R6: três matrizes 3×3 por âncora com PREÇO POR AÇÃO em cada célula:
    CAP×ROE (g base fixo), CAP×g (ROE base fixo), ROE×g (CAP base fixo).
    Eixos usam as premissas bear/base/bull da tabela de cenários. Herda o R4:
    cada matriz declara em `fixos` o que permanece constante (lucro, o terceiro
    driver no valor base, Ke da âncora, DE/NDE, m_terminal base). Célula com
    g >= ROE seria retenção > 100% — emitida como null (incoerente), nunca um
    número falso. Cálculo 100% determinístico (pl_justo), nada em prosa."""
    p, f = inp["premissas"], inp["fatos"]
    lpa = f["lpa_ajustado_fy"]
    cen = p["cenarios"]
    base = cen["base"]
    de, nde, _ = _de_nde(inp)
    m_base = _m_terminal(base)
    eixos = {d: {n: cen[n][d] for n in ("bear", "base", "bull")} for d in ("cap", "roe", "g")}
    pares = (("cap", "roe", "g"), ("cap", "g", "roe"), ("roe", "g", "cap"))

    def matriz(linha, coluna, fixo, ke):
        precos = {}
        for ln in ("bear", "base", "bull"):
            precos[ln] = {}
            for cn in ("bear", "base", "bull"):
                drivers = {fixo: base[fixo], linha: eixos[linha][ln], coluna: eixos[coluna][cn]}
                if drivers["g"] >= drivers["roe"]:
                    precos[ln][cn] = None  # retenção > 100%: célula economicamente incoerente
                else:
                    precos[ln][cn] = round(lpa * pl_justo(drivers["g"], drivers["roe"],
                                                          drivers["cap"], ke, de, nde, m_base), 2)
        return {
            "linha": linha, "coluna": coluna,
            "valores_linha": eixos[linha], "valores_coluna": eixos[coluna],
            "fixos": {fixo: base[fixo], "ke": ke, "lpa": lpa, "de": de, "nde": nde,
                      "m_terminal": m_base},
            "precos": precos,
        }

    def por_ancora(ke):
        return {f"{a}_x_{b}": matriz(a, b, c, ke) for a, b, c in pares}

    ke_h = p.get("ke_hurdle")
    return {
        "economico": {"ke": econ["ke_central"], **por_ancora(econ["ke_central"])},
        "hurdle": ({"ke": ke_h, **por_ancora(ke_h)} if ke_h is not None else None),
        "nota_experimento": "Cada matriz varia DOIS drivers pelos valores bear/base/bull da "
                            "tabela de cenários e mantém fixos o terceiro driver (no valor "
                            "base), o lucro (LPA), Ke da âncora, DE/NDE e m_terminal base. "
                            "Células não são ponderadas por probabilidade (a leitura "
                            "probabilística é a tabela de Cenários).",
    }


PHI_GRID = (0.0, 0.25, 0.5, 1.0)  # φ>1 = spread terminal > spread de franquia: incoerente (B0/φ*)


def bloco_sensibilidade_phi(inp, econ):
    """H11 (v3.1.0): sensibilidade a spread terminal fracionário como SAÍDA de
    primeira classe, default conservador φ=0 (motor). ROE_term = Ke + φ·(ROE−Ke)
    ⇔ m_terminal(φ) = 1 + φ·(ROE−Ke)/Ke por cenário (identidade validada no B0
    com erro 0,00 vs engine). EXCLUSÃO MÚTUA com m_terminal manual: quando o
    input declara m_terminal != 1 (a mesma alavanca), o bloco degrada para
    aplicavel=false — nunca dois mecanismos de spread terminal no mesmo run.
    Âncora: econômica central. cap_equivalente_base = CAP que, com φ=0,
    reproduz o P/L do cenário base com m(φ) (régua prática do fade)."""
    p, f = inp["premissas"], inp["fatos"]
    cen = p["cenarios"]
    nomes = ("bear", "base", "bull")
    nota = ("Default do motor é φ=0 (spread zera no CAP; disciplina conservadora). A grade "
            "reporta o preço central ponderado permitindo spread terminal fracionário e o CAP "
            "equivalente que o reproduziria com φ=0 — φ e m_terminal são a MESMA alavanca "
            "(exclusão mútua).")
    if any(abs(_m_terminal(cen[n]) - 1.0) > 1e-12 for n in nomes):
        return {"aplicavel": False,
                "motivo_na": "m_terminal manual declarado nos cenários (mesma alavanca de "
                             "spread terminal que φ): a escolha de terminal já foi feita no "
                             "input; a grade φ não se aplica (exclusão mútua)",
                "ancora": "economico_central", "grid": None, "nota": nota}
    lpa = f["lpa_ajustado_fy"]
    ke = econ["ke_central"]
    de, nde, _ = _de_nde(inp)
    base = cen["base"]
    grid = []
    for phi in PHI_GRID:
        ms = {n: 1.0 + phi * (cen[n]["roe"] - ke) / ke for n in nomes}
        precos = {n: lpa * pl_justo(cen[n]["g"], cen[n]["roe"], cen[n]["cap"], ke, de, nde, ms[n])
                  for n in nomes}
        pond = round(_pond(cen, precos), 2)
        alvo = pl_justo(base["g"], base["roe"], base["cap"], ke, de, nde, ms["base"])
        cap_eq = _bisseccao(lambda c: pl_justo(base["g"], base["roe"], c, ke, de, nde, 1.0) - alvo,
                            0.5, 400.0)
        preco_atual = inp["meta"]["preco_atual"]
        grid.append({
            "phi": phi,
            "m_por_cenario": {n: round(ms[n], 4) for n in nomes},
            "central_ponderado": pond,
            "premio_vs_preco_pct": round(100.0 * (preco_atual / pond - 1.0), 1),
            "cap_equivalente_base": round(cap_eq, 2) if cap_eq is not None else None,
        })
    return {"aplicavel": True, "motivo_na": None, "ancora": "economico_central",
            "grid": grid, "nota": nota}


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
    de_nde = bloco_de_nde(inp, hurdle, econ)
    cap = bloco_cap(inp)
    reverse = bloco_reverse(inp, econ)
    ladder = bloco_ladder(inp, econ)
    elast = bloco_elasticidades(inp, econ)
    matrizes = bloco_matrizes(inp, econ)
    sens_phi = bloco_sensibilidade_phi(inp, econ)
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
        "de_nde": de_nde,
        "economico": econ,
        "cap": cap,
        "reverse": reverse,
        "ladder": ladder,
        "elasticidades": elast,
        "matrizes": matrizes,
        "sensibilidade_phi": sens_phi,
        "validacao_multiplos": val_mult,
    }


def gerar_grafico(res, caminho):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    preco = res["meta"]["preco_atual"]
    e = res["economico"]
    linhas = [
        ("Valor econômico (P/L Justo)", e["faixa_completa"][0], e["faixa_completa"][1], e["central_ponderado"]),
    ]
    if res.get("hurdle"):  # R3: sem hurdle informado, o gráfico degrada para a âncora econômica
        h = res["hurdle"]["cenarios"]
        linhas.insert(0, ("Preço máx. hurdle", h["bear"]["preco"], h["bull"]["preco"], h["ponderado"]))
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
    hurdle_txt = (res["hurdle"]["cenarios"]["ponderado"] if res.get("hurdle")
                  else "n/a (hurdle nao informado pelo usuario)")
    print(f"  hurdle ponderado: {hurdle_txt} | "
          f"econ faixa ponderada: {res['economico']['faixa_ponderada']}")
    print(f"  validacao_multiplos: {res['validacao_multiplos']['veredicto']}")
    for al in res["elasticidades"]["alertas_sinal"]:
        if not al["respondido"]:
            print(f"  ALERTA DE SINAL (bloqueante): {al['ancora']}.{al['parametro']} "
                  f"{al['sinal_observado']} vs esperado {al['sinal_esperado']} — responda em "
                  f"premissas.respostas_sinais.{al['parametro']}")
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
