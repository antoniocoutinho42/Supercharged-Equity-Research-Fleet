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
# v3.1.0 (2026-07-21): upgrade metodológico FASE B/B1 (arquitetura A aprovada; evidência
#   FASE A + B0 em C:\Claude\upgrade_fleet_v2_fase_a e referencia\verificacao_referencia.py).
#   MINOR ADITIVO — núcleo pl_justo() INALTERADO; inputs antigos produzem todas as chaves
#   antigas idênticas (critério de regressão: chaves idênticas exceto engine.{versao,
#   gerado_em}; núcleo 1e-12). Blocos novos com GATING POR PRESENÇA (nunca retroativo):
#   (1) H11 — sensibilidade_phi: grade φ∈{0;0,25;0,5;1} na âncora econômica central,
#       m(φ)=1+φ·(ROE−Ke)/Ke por cenário (identidade validada no B0 com erro 0,00),
#       CAP equivalente por bisseção; SEMPRE emitida. EXCLUSÃO MÚTUA com m_terminal
#       manual (mesma alavanca): premissas.phi é recusado como input; com m_terminal≠1
#       o bloco degrada para aplicavel=false. Default do motor segue φ=0 (conservador).
#   (2) H1/H6 — fatos.reformulado (opcional): série validada NA CARGA como ERRO de input
#       (CE≡NOA tol. 0,5%; ni≡nopat+nie; roic/roe declarados vs derivados); derivados
#       margem/giro/roic/roic_ex_goodwill/nbc/flev/ponte/direto por ano (base MÉDIA para
#       diagnóstico; EoP proibido — FASE A); NBC=None com nota quando |ND|<2% do NOA;
#       diagnóstico ROIIC/RiR/g em JANELA ACUMULADA (razão anual é instável — TF).
#   (3) H7 — gates_aplicabilidade da âncora equity: eliminatórios A1 (E>0 na janela),
#       A2 (mediana E/NOA >= 0,30), A3 (lucro recorrente último e mediana > 0) decidem a
#       âncora; FLEV cruza sinal / NBC instável / ND imaterial são FLAGS de diagnóstico
#       (TF: cruzamento benigno não expulsa a âncora). Limiares PROVISORIO_N3 (TF/Lopes/
#       PVV) com nota de RECALIBRAÇÃO obrigatória a cada caso novo (condição 7).
#   (4) H9/H4 — ebit_justo: âncora operacional no MOTOR ÚNICO (mesma pl_justo com
#       g/ROIC=margem×giro/CAP/WACC, TRAILING, de=nde=0; g/cap/prob/m_terminal herdados
#       da tabela única de cenários); cadeia EV/EBIT=(1−t)× e EV/EBITDA=×(1−d); bridge
#       de claims assinados (equity = EV + Σ claims); WACC RECEBIDO como premissa
#       documentada (H8), nunca derivado; reverse operacional com degrade declarado;
#       elasticidades margem/giro/CAP/WACC no padrão R4. Fator forward=(1+g)×trailing
#       SÓ com m_terminal=1 (B0) — o bloco nunca converte para forward.
#   (5) Condição 3 (aprovação 2026-07-21) — PARIDADE DAS ÂNCORAS: delta operacional vs
#       patrimonial central, limiar 10%; divergência = WARNING PARIDADE_DIVERGENTE com
#       nota de resolução obrigatória no relatório; NÃO bloqueia publicação (checar emite
#       AVISO). DECISÃO A REAVALIAR APÓS 3 ANÁLISES REAIS.
#   (6) Condição 6 — historia_numeros: tabela história→premissa→implícito→evidência por
#       cenário, SEMPRE presente no ebit_justo (drivers ausentes = "—" + aviso nomeado);
#       aviso DUPLA_PENALIZACAO_BEAR sem justificativa própria (H6/Seção 5).
#   (7) H5 — camadas de imposto: aliquota_operacional na cadeia; marginal/terminal eco
#       de premissas.impostos; terminal não declarada = aviso (TF: 27→34% move EV −12,6%).
#   Contrato (passada única, checar/compor): sensibilidade_phi obrigatória em v3.1+;
#   blocos presentes exigem subchaves; seções novas no corpo institucional; humano()
#   cobre os enums novos; linter intacto.
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
ENGINE_VERSION = "3.1.0"

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


REF_TOL_REL = 0.005      # inputs coletados à mão: invariantes com 0,5% relativo (B0: resíduos reais < 0,01%)
REF_ND_MINUSCULO = 0.02  # |ND médio| < 2% do NOA => NBC sem significado (TF 2024: base pequena, evidência FASE A)

# Gates H7 — LIMIARES PROVISÓRIOS, calibrados em n=3 casos (TF, Lopes, PVV; FASE A + B0).
# Condição 7 da aprovação (2026-07-21): RECALIBRAR a cada caso novo aplicado; os valores
# abaixo separam os 3 casos com folga, mas n=3 não é amostra — revisar limiares quando a
# jurisprudência crescer, registrando a mudança no CHANGELOG.
H7_CALIBRACAO = "PROVISORIO_N3"
H7_MIN_E_NOA_MEDIANA = 0.30   # zona de separação medida: PVV máx −0,04 vs TF/Lopes mín 0,93
H7_ND_IMATERIAL = 0.10        # |ND|/NOA médio < 10%: ND imaterial → diagnóstico da ponte fraco
H7_NBC_RATIO_MAX = 2.0        # |NBC| max/min > 2 (ou sinal instável) com FLEV material: NBC não interpretável
H7_FLEV_MATERIAL = 0.20       # F1 só relevante com alavancagem média material


def _gates_h7(serie):
    """H7: gate de aplicabilidade da âncora equity em DOIS níveis (evidência FASE A/B0):
    ELIMINATÓRIOS (decidem a âncora): A1 E>0 em toda a janela; A2 mediana(E/NOA) >= 0,30;
    A3 lucro recorrente (último E mediana) > 0. FLAGS (degradam o diagnóstico da ponte/NBC,
    NUNCA a âncora — TF passa com 1-2 cruzamentos benignos de FLEV): A4 FLEV cruza sinal;
    F1 NBC instável com FLEV material; F2 ND imaterial."""
    import statistics
    e_fins = [float(s["e_fim"]) for s in serie]
    e_noa = [float(s["e_medio"]) / float(s["noa_medio"]) for s in serie]
    nis = [float(s["ni_recorrente"]) for s in serie]
    flevs = [float(s["flev"]) for s in serie]
    nbcs = [float(s["nbc"]) for s in serie if s["nbc"] is not None]
    ndnoas = [abs(float(s["nd_medio"])) / abs(float(s["noa_medio"])) for s in serie]

    a1 = all(e > 0 for e in e_fins)
    med_enoa = statistics.median(e_noa)
    a2 = med_enoa >= H7_MIN_E_NOA_MEDIANA
    med_ni = statistics.median(nis)
    a3 = (nis[-1] > 0) and (med_ni > 0)

    flags = []
    cruzamentos = sum(1 for a, b in zip(flevs, flevs[1:]) if a * b < 0)
    if cruzamentos > 0:
        flags.append({"codigo": "FLEV_CRUZA_SINAL",
                      "detalhe": f"{cruzamentos} cruzamento(s) de sinal do FLEV na janela — "
                                 "ponte e NBC devem ser lidos com cautela nesses anos "
                                 "(não expulsa a âncora: evidência TF, net cash transitório)"})
    flev_medio = sum(abs(x) for x in flevs) / len(flevs)
    nbc_ratio = None
    if nbcs and min(abs(x) for x in nbcs) > 1e-12:
        nbc_ratio = max(abs(x) for x in nbcs) / min(abs(x) for x in nbcs)
    nbc_sinal_estavel = bool(nbcs) and (all(x > 0 for x in nbcs) or all(x < 0 for x in nbcs))
    if flev_medio >= H7_FLEV_MATERIAL and ((nbc_ratio is not None and nbc_ratio > H7_NBC_RATIO_MAX)
                                           or not nbc_sinal_estavel):
        flags.append({"codigo": "NBC_INSTAVEL",
                      "detalhe": f"|FLEV| médio {flev_medio:.3f} com NBC instável (razão "
                                 f"{'%.2f' % nbc_ratio if nbc_ratio else 'n/a'}, sinal estável "
                                 f"{nbc_sinal_estavel}) — NUNCA publicar NBC como custo de dívida"})
    ndnoa_medio = sum(ndnoas) / len(ndnoas)
    if ndnoa_medio < H7_ND_IMATERIAL:
        flags.append({"codigo": "ND_IMATERIAL",
                      "detalhe": f"|ND|/NOA médio {ndnoa_medio:.3f} < {H7_ND_IMATERIAL}: dívida "
                                 "líquida imaterial — decomposição da ponte pouco informativa"})

    ok = a1 and a2 and a3
    return {
        "calibracao": H7_CALIBRACAO,
        "ancora_equity": "EQUITY_OK" if ok else "GATE_DISPARA",
        "ancora_primaria_recomendada": "EQUITY" if ok else "OPERACIONAL",
        "eliminatorios": {
            "a1_e_positivo": {"passa": a1, "min_e_fim": round(min(e_fins), 2)},
            "a2_mediana_e_noa": {"passa": a2, "valor": round(med_enoa, 4),
                                 "limiar": H7_MIN_E_NOA_MEDIANA},
            "a3_lucro_recorrente": {"passa": a3, "ultimo": round(nis[-1], 2),
                                    "mediana": round(med_ni, 2)},
        },
        "flags": flags,
        "limiares": {"mediana_e_noa": H7_MIN_E_NOA_MEDIANA, "nd_imaterial": H7_ND_IMATERIAL,
                     "nbc_ratio_max": H7_NBC_RATIO_MAX, "flev_material": H7_FLEV_MATERIAL},
        "nota_recalibracao": ("Limiares PROVISÓRIOS calibrados em n=3 (TF, Lopes, PVV — FASE "
                              "A/B0): RECALIBRAR a cada caso novo aplicado, registrando a "
                              "revisão no CHANGELOG (condição 7 da aprovação da FASE B)."),
    }


def bloco_fatos_reformulado(inp):
    """H1/H6 (v3.1.0): série reformulada OPCIONAL (gating por presença) validada na
    CARGA — invariantes viram ERRO de input, nunca warning (mission §B1):
      CE ≡ NOA  (nd_medio + e_medio ≡ noa_medio, tolerância relativa 0,5%);
      ni_recorrente ≡ nopat + nie_pos_imposto;
      roic/roe DECLARADOS (opcionais) devem bater com os derivados.
    Deriva por ano: margem_nopat, giro_noa, roic (= margem×giro, base MÉDIA),
    roic_ex_goodwill (se noa_medio_ex_goodwill vier), nbc (None quando |ND| é
    minúsculo — base sem significado), flev, roe_ponte, roe_direto.
    Diagnóstico H6 em JANELA ACUMULADA (nunca anual — evidência TF: razão
    RiR/(g/ROIC) anual oscila 0,32–5,03): roiic_acumulado, rir_acumulado,
    g_nopat_acumulado. Convenção de base: MÉDIA para diagnóstico (par
    média/inicial da FASE A; EoP proibido)."""
    ref = inp["fatos"].get("reformulado")
    if not ref:
        return None
    serie_in = ref.get("serie") or []
    erros = []
    if len(serie_in) < 2:
        erros.append("fatos.reformulado.serie exige >= 2 anos (recomendado 5-6 + TTM)")
    obrig = ("ano", "receita", "nopat", "noa_medio", "nd_medio", "e_medio", "e_fim",
             "nie_pos_imposto")
    serie = []
    for i, row in enumerate(serie_in):
        faltando = [c for c in obrig if row.get(c) is None]
        if faltando:
            erros.append(f"serie[{i}] (ano {row.get('ano')}): campos ausentes: {', '.join(faltando)}")
            continue
        ano = row["ano"]
        receita, nopat = float(row["receita"]), float(row["nopat"])
        noa, nd, e_med = float(row["noa_medio"]), float(row["nd_medio"]), float(row["e_medio"])
        nie = float(row["nie_pos_imposto"])
        ce_delta = (nd + e_med) - noa
        if abs(ce_delta) > REF_TOL_REL * max(1.0, abs(noa)):
            erros.append(f"serie[{i}] (ano {ano}): CE != NOA (nd_medio + e_medio - noa_medio = "
                         f"{ce_delta:.1f}, acima de {REF_TOL_REL:.1%} do NOA) — a reformulação "
                         "não fecha; corrija a coleta, não o engine")
        ni = row.get("ni_recorrente")
        ni_derivado = nopat + nie
        if ni is None:
            ni = ni_derivado
        elif abs(float(ni) - ni_derivado) > REF_TOL_REL * max(1.0, abs(ni_derivado)):
            erros.append(f"serie[{i}] (ano {ano}): ni_recorrente ({float(ni):.1f}) != nopat + "
                         f"nie_pos_imposto ({ni_derivado:.1f}) — identidade da ponte violada na coleta")
        margem = nopat / receita
        giro = receita / noa
        roic = margem * giro
        if row.get("roic") is not None and abs(float(row["roic"]) - roic) > 1e-3:
            erros.append(f"serie[{i}] (ano {ano}): roic declarado ({float(row['roic']):.4f}) != "
                         f"derivado margem×giro ({roic:.4f})")
        nd_minusculo = abs(nd) < REF_ND_MINUSCULO * abs(noa)
        nbc = None if nd_minusculo else -(nie / nd)
        flev = nd / e_med
        roe_ponte = None if nbc is None else roic + flev * (roic - nbc)
        roe_direto = float(ni) / e_med
        if row.get("roe") is not None and abs(float(row["roe"]) - roe_direto) > 1e-3:
            erros.append(f"serie[{i}] (ano {ano}): roe declarado ({float(row['roe']):.4f}) != "
                         f"derivado ni/e_medio ({roe_direto:.4f})")
        saida = dict(row)
        saida["ni_recorrente"] = round(float(ni), 2)
        saida.update({
            "margem_nopat": round(margem, 6),
            "giro_noa": round(giro, 6),
            "roic": round(roic, 6),
            "nbc": None if nbc is None else round(nbc, 6),
            "nbc_nota": ("ND médio < 2% do NOA: NBC sem significado econômico (base "
                         "minúscula) — não interpretar como custo de dívida" if nd_minusculo else None),
            "flev": round(flev, 6),
            "roe_ponte": None if roe_ponte is None else round(roe_ponte, 6),
            "roe_direto": round(roe_direto, 6),
        })
        if row.get("noa_medio_ex_goodwill") is not None:
            saida["roic_ex_goodwill"] = round(nopat / float(row["noa_medio_ex_goodwill"]), 6)
        serie.append(saida)
    if erros:
        raise ValueError("fatos.reformulado recusado pelo engine:\n- " + "\n- ".join(erros))

    prim, ult = serie[0], serie[-1]
    n = len(serie)
    d_noa = float(ult["noa_medio"]) - float(prim["noa_medio"])
    diagnostico = {
        "janela": f"{prim['ano']}-{ult['ano']}",
        "base_capital": "MEDIA (diagnóstico); modelo de valor usa INICIAL — EoP proibido (FASE A)",
        "roiic_acumulado": (round((float(ult["nopat"]) - float(prim["nopat"])) / d_noa, 6)
                            if abs(d_noa) > 1e-9 else None),
        "rir_acumulado": (round(d_noa / sum(float(s["nopat"]) for s in serie[1:]), 6)
                          if sum(float(s["nopat"]) for s in serie[1:]) else None),
        "g_nopat_acumulado": (round((float(ult["nopat"]) / float(prim["nopat"])) ** (1.0 / (n - 1)) - 1.0, 6)
                              if float(prim["nopat"]) > 0 and n > 1 else None),
        "nota": ("ROIIC/RiR em janela acumulada — a razão anual RiR/(g/ROIC) é instável em "
                 "transição (evidência TF: 0,32–5,03); g/ROIC só vale como RiR terminal"),
    }
    validacoes = [
        f"CE≡NOA verificado nos {n} anos (tolerância {REF_TOL_REL:.1%})",
        "ni_recorrente ≡ nopat + nie_pos_imposto verificado (identidade da ponte)",
        "margem×giro ≡ roic por construção (base média)",
    ]
    if n < 4:
        validacoes.append(f"NOTA: série curta ({n} anos; recomendado 5-6 + TTM)")
    return {"unidade": ref.get("unidade"), "fonte": ref.get("fonte"),
            "serie": serie, "diagnostico": diagnostico, "validacoes": validacoes,
            "gates_aplicabilidade": _gates_h7(serie)}


EBIT_PARIDADE_LIMIAR_PCT = 10.0  # |delta| acima disso => PARIDADE_DIVERGENTE (warning, condição 3)


def bloco_ebit_justo(inp, econ):
    """H9/H4 (v3.1.0): âncora operacional no MOTOR ÚNICO — a MESMA pl_justo com
    inputs operacionais (g, ROIC = margem×giro, CAP, WACC), convenção TRAILING,
    de=nde=0 (o bracket equity não se aplica ao EV). Identidade medida no B0:
    EV/NOPAT forward do JM = (1+g) × pl_justo trailing, e o fator SÓ vale com
    m_terminal=1 — por isso o bloco NUNCA converte para forward. Cadeia:
    EV/EBIT = (1−t)×EV/NOPAT; EV/EBITDA = ×(1−d). Bridge de claims (H4): equity
    = EV + Σ claims assinados (dívida negativa; caixa/NOL positivos). Cenários
    g/cap/prob/m_terminal HERDADOS de premissas.cenarios (uma única tabela —
    anti-empilhamento); a rentabilidade operacional entra como margem×giro por
    cenário (história→números). WACC é RECEBIDO como premissa documentada (H8),
    nunca derivado do balanço. Gating por presença: sem premissas.operacional o
    bloco não existe."""
    p, f, meta = inp["premissas"], inp["fatos"], inp["meta"]
    op = p.get("operacional")
    if not op:
        return None
    nomes = ("bear", "base", "bull")
    erros = []
    nopat_fy = f.get("nopat_fy_mi")
    if nopat_fy is None or float(nopat_fy) <= 0:
        erros.append("fatos.nopat_fy_mi ausente ou <= 0: base trailing da âncora operacional; "
                     "sem NOPAT representativo a âncora não roda (base não normalizada → "
                     "registre a limitação, não force)")
    wacc = op.get("wacc")
    if not isinstance(wacc, (int, float)) or float(wacc) <= 0:
        erros.append("premissas.operacional.wacc ausente ou <= 0 — o WACC é RECEBIDO como "
                     "premissa documentada (H8); o engine nunca o deriva do balanço")
    if not str(op.get("fonte_wacc", "")).strip():
        erros.append("premissas.operacional.fonte_wacc obrigatória (dossiê de Ke/WACC com as "
                     "duas rotas — H8)")
    t = op.get("aliquota_operacional")
    if not isinstance(t, (int, float)) or not (0.0 <= float(t) < 1.0):
        erros.append("premissas.operacional.aliquota_operacional ausente ou fora de [0,1) — "
                     "camada de imposto da cadeia EV/EBIT (H5)")
    if not str(op.get("fonte_aliquotas", "")).strip():
        erros.append("premissas.operacional.fonte_aliquotas obrigatória (H5: alíquota é input "
                     "documentado por companhia, nunca constante universal)")
    cen_op = op.get("cenarios") or {}
    if sorted(cen_op.keys()) != sorted(nomes):
        erros.append("premissas.operacional.cenarios deve conter exatamente bear, base e bull "
                     "(margem_nopat e giro_noa por cenário)")
    claims = f.get("claims_bridge")
    if not isinstance(claims, list):
        erros.append("fatos.claims_bridge ausente: o bridge EV→equity exige a lista de claims "
                     "(H4; pode ser vazia apenas com ND≈0 e nota) — sinal = contribuição ao "
                     "equity (dívida negativa; caixa/NOL positivos)")
    else:
        for i, c in enumerate(claims):
            if not (isinstance(c, dict) and c.get("nome") and c.get("valor_mi") is not None
                    and str(c.get("fonte", "")).strip()):
                erros.append(f"claims_bridge[{i}]: exige nome, valor_mi e fonte")
    acoes = meta.get("acoes_mi")
    if not acoes:
        erros.append("meta.acoes_mi obrigatório para o preço por ação da âncora operacional")
    cen_eq = p.get("cenarios", {})
    roics = {}
    if not erros:
        for n in nomes:
            c = cen_op[n]
            mg, gr = c.get("margem_nopat"), c.get("giro_noa")
            if not (isinstance(mg, (int, float)) and isinstance(gr, (int, float))
                    and float(mg) > 0 and float(gr) > 0):
                erros.append(f"cenário operacional {n}: margem_nopat e giro_noa devem ser > 0")
                continue
            roics[n] = float(mg) * float(gr)
            if float(cen_eq[n]["g"]) >= roics[n]:
                erros.append(f"cenário {n}: g ({cen_eq[n]['g']}) >= roic operacional "
                             f"({roics[n]:.4f} = margem×giro) implica reinvestimento > 100% — "
                             "incoerente; reveja margem/giro ou g")
    dsobre = f.get("da_sobre_ebitda")
    if dsobre is not None and not (0.0 <= float(dsobre) < 1.0):
        erros.append("fatos.da_sobre_ebitda fora de [0,1)")
    if erros:
        raise ValueError("ebit_justo: inputs recusados pelo engine:\n- " + "\n- ".join(erros))

    t = float(t)
    total_claims = round(sum(float(c["valor_mi"]) for c in claims), 2)
    out_cen = {}
    for n in nomes:
        g_, cap_ = float(cen_eq[n]["g"]), float(cen_eq[n]["cap"])
        m_t = _m_terminal(cen_eq[n])
        roic = roics[n]
        evn = pl_justo(g_, roic, cap_, float(wacc), 0.0, 0.0, m_t)
        ev_mi = evn * float(nopat_fy)
        eq_mi = ev_mi + total_claims
        out_cen[n] = {
            "margem_nopat": float(cen_op[n]["margem_nopat"]),
            "giro_noa": float(cen_op[n]["giro_noa"]),
            "roic": round(roic, 6),
            "rir_implicito_terminal": round(g_ / roic, 6),
            "ev_nopat_justo": round(evn, 4),
            "ev_ebit_justo": round(evn * (1.0 - t), 4),
            "ev_mi": round(ev_mi, 2),
            "equity_mi": round(eq_mi, 2),
            "preco": round(eq_mi / float(acoes), 2),
        }
        if dsobre is not None:
            out_cen[n]["ev_ebitda_justo"] = round(evn * (1.0 - t) * (1.0 - float(dsobre)), 4)
    ponderado = round(_pond(cen_eq, {n: out_cen[n]["preco"] for n in nomes}), 2)

    # Paridade das âncoras — condição 3 da aprovação (2026-07-21): WARNING com nota de
    # resolução obrigatória no relatório; NUNCA bloqueio de publicação. Reavaliar a
    # decisão após 3 análises reais.
    preco_eq_central = econ["central_ponderado"]
    delta_pct = round(100.0 * (ponderado / preco_eq_central - 1.0), 1)
    diverge = abs(delta_pct) > EBIT_PARIDADE_LIMIAR_PCT
    nota_par = str(op.get("nota_paridade", "")).strip() or None
    paridade = {
        "preco_equity_central": preco_eq_central,
        "preco_op_ponderado": ponderado,
        "delta_pct": delta_pct,
        "limiar_pct": EBIT_PARIDADE_LIMIAR_PCT,
        "status": "DIVERGE" if diverge else "CONVERGE",
        "warning": "PARIDADE_DIVERGENTE" if diverge else None,
        "nota_resolucao": nota_par,
        "instrucao": ("Paridade é ROTA DE RECONCILIAÇÃO, nunca segundo preço-alvo: com ND≈0 e "
                      "premissas consistentes as âncoras convergem por identidade; divergência "
                      "isola wedges REAIS (ex.: add-backs na base de lucro — o teste "
                      "independente dos ajustes). Divergente => WARNING com nota de resolução "
                      "obrigatória no relatório; NÃO bloqueia publicação (decisão registrada; "
                      "reavaliar após 3 análises reais)."),
    }

    # Reverse operacional: o que o preço exige nos drivers operacionais (base do cenário base).
    base_eq = cen_eq["base"]
    m_base = _m_terminal(base_eq)
    g_b, cap_b = float(base_eq["g"]), float(base_eq["cap"])
    roic_b = roics["base"]
    preco_atual = meta["preco_atual"]
    alvo = (preco_atual * float(acoes) - total_claims) / float(nopat_fy)
    w = float(wacc)
    roic_impl = _bisseccao(lambda r: pl_justo(g_b, r, cap_b, w, 0.0, 0.0, m_base) - alvo,
                           g_b + 1e-6, 2.0)
    cap_impl = _bisseccao(lambda c: pl_justo(g_b, roic_b, c, w, 0.0, 0.0, m_base) - alvo,
                          0.5, 400.0)
    wacc_impl = _bisseccao(lambda x: pl_justo(g_b, roic_b, cap_b, x, 0.0, 0.0, m_base) - alvo,
                           1e-6, 0.60)
    reverse = {
        "alvo_ev_nopat_implicito": round(alvo, 4),
        "roic_implicito_no_preco": round(roic_impl, 4) if roic_impl is not None else None,
        "cap_implicito_op": round(cap_impl, 1) if cap_impl is not None else None,
        "wacc_implicito": round(wacc_impl, 4) if wacc_impl is not None else None,
        "nota": ("None = o driver isolado não alcança o EV/NOPAT implícito no preço dentro de "
                 "faixas plausíveis (degrade declarado, nunca número falso)"),
    }

    # Elasticidades operacionais (padrão R4: experimento declarado + alerta de sinal).
    mg_b, gr_b = float(cen_op["base"]["margem_nopat"]), float(cen_op["base"]["giro_noa"])

    def preco_op(margem, giro, cap_, w_):
        evn = pl_justo(g_b, margem * giro, cap_, w_, 0.0, 0.0, m_base)
        return (evn * float(nopat_fy) + total_claims) / float(acoes)

    p0 = preco_op(mg_b, gr_b, cap_b, w)
    elast = {
        "preco_base": round(p0, 2),
        "mais_1pp_margem": round(preco_op(mg_b + 0.01, gr_b, cap_b, w) - p0, 2),
        "mais_01x_giro": round(preco_op(mg_b, gr_b + 0.1, cap_b, w) - p0, 2),
        "mais_1a_cap": round(preco_op(mg_b, gr_b, cap_b + 1, w) - p0, 2),
        "menos_05pp_wacc": round(preco_op(mg_b, gr_b, cap_b, w - 0.005) - p0, 2),
    }
    spread_pos = roic_b > w
    esperados = {"mais_1pp_margem": "POSITIVO", "mais_01x_giro": "POSITIVO",
                 "mais_1a_cap": "POSITIVO" if spread_pos else "NEGATIVO",
                 "menos_05pp_wacc": "POSITIVO"}
    respostas = p.get("respostas_sinais") or {}
    alertas = []
    for parametro, esperado in esperados.items():
        v = elast[parametro]
        if abs(v) < 0.005:
            continue
        observado = "POSITIVO" if v > 0 else "NEGATIVO"
        if observado != esperado:
            resposta = str(respostas.get(parametro, "")).strip()
            alertas.append({"ancora": "operacional", "parametro": parametro, "valor": v,
                            "sinal_esperado": esperado, "sinal_observado": observado,
                            "exigencia": "Sinal contrário à relação econômica esperada: mesmo "
                                         "protocolo do R4 (mecanismo + plausibilidade em "
                                         "premissas.respostas_sinais).",
                            "respondido": bool(resposta), "resposta": resposta or None})
    elast["experimento"] = {
        "mais_1pp_margem": "Varia só a margem NOPAT (+1 p.p.; ROIC = margem×giro sobe junto); "
                           "mantém fixos NOPAT_fy da base, giro, g, CAP, WACC, m_terminal e claims.",
        "mais_01x_giro": "Varia só o giro de NOA (+0,1x; ROIC sobe junto); demais fixos como acima.",
        "mais_1a_cap": "Varia só a duração da vantagem (CAP +1 ano); demais fixos.",
        "menos_05pp_wacc": "Varia só o WACC (−0,5 p.p.); todo o resto fixo.",
    }
    elast["alertas_sinal"] = alertas

    # História→números (condição 6 da aprovação): tabela gerada POR CHAVE, um item por
    # cenário — a resposta estrutural ao "fundamentações meio arbitrárias" (Seção 5 do
    # prompt master). SEMPRE presente quando ebit_justo roda; drivers ausentes viram "—"
    # com aviso nomeado, nunca omissão silenciosa.
    avisos = []
    drivers = op.get("drivers_narrativos") or {}
    historia = {}
    sem_drivers = []
    for n in nomes:
        hist = str(drivers.get(n, "")).strip()
        if not hist:
            sem_drivers.append(n)
        historia[n] = {
            "historia": hist or "—",
            "premissa": f"margem_nopat {cen_op[n]['margem_nopat']} × giro_noa "
                        f"{cen_op[n]['giro_noa']} (g {cen_eq[n]['g']}, cap {cen_eq[n]['cap']})",
            "implicito": {"roic": out_cen[n]["roic"],
                          "rir_terminal": out_cen[n]["rir_implicito_terminal"],
                          "g": float(cen_eq[n]["g"])},
            "evidencia": f"wacc: {op['fonte_wacc']}; aliquotas: {op['fonte_aliquotas']}",
        }
    if sem_drivers:
        avisos.append(f"DRIVERS_NARRATIVOS_AUSENTES ({', '.join(sem_drivers)}): a coluna "
                      "'história' da tabela história→premissa→implícito→evidência ficou vazia — "
                      "o Modelador deve declarar premissas.operacional.drivers_narrativos por "
                      "cenário e defender cada implícito contra o dossiê (G2)")

    # Camadas de imposto (H5): operacional entra na cadeia; marginal/terminal são eco
    # rastreável de premissas.impostos. Terminal não declarada => aviso nomeado (evidência
    # TF no B0: 27%→34% no terminal move o EV em −12,6% — a escolha é material).
    imp = p.get("impostos") or {}
    aliquotas = {"operacional": t}
    for chave in ("marginal", "terminal"):
        if imp.get(chave) is not None:
            aliquotas[chave] = float(imp[chave])
    if imp.get("fontes"):
        aliquotas["fontes"] = str(imp["fontes"])
    if aliquotas.get("terminal") is None:
        avisos.append("ALIQUOTA_TERMINAL_NAO_DECLARADA: a cadeia usa a alíquota operacional; "
                      "declare premissas.impostos.terminal (statutory de longo prazo, salvo "
                      "evidência documentada) — no caso TF a diferença 27%→34% move o EV em "
                      "−12,6% (B0)")

    # Dupla penalização no bear (H6/Seção 5): margem E giro simultaneamente abaixo do base
    # exigem justificativa própria (a mesma força movendo os dois é história, não default).
    if (float(cen_op["bear"]["margem_nopat"]) < float(cen_op["base"]["margem_nopat"])
            and float(cen_op["bear"]["giro_noa"]) < float(cen_op["base"]["giro_noa"])
            and not str(op.get("justificativa_dupla_penalizacao", "")).strip()):
        avisos.append("DUPLA_PENALIZACAO_BEAR: margem E giro simultaneamente abaixo do base "
                      "sem justificativa própria (premissas.operacional."
                      "justificativa_dupla_penalizacao) — evidência TF: a mesma força move "
                      "margem para baixo e giro para CIMA (mix franquia); dupla penalização "
                      "exige história específica")

    return {
        "wacc": w,
        "fonte_wacc": str(op["fonte_wacc"]),
        "aliquotas": aliquotas,
        "historia_numeros": historia,
        "avisos": avisos,
        "cenarios": out_cen,
        "ponderado_preco": ponderado,
        "bridge": {"claims": claims, "total_mi": total_claims,
                   "convencao_sinal": "valor_mi = contribuição ao EQUITY (dívida negativa; "
                                      "caixa livre/NOL positivos)"},
        "paridade": paridade,
        "reverse": reverse,
        "elasticidades": elast,
        "convencao": "trailing (mesma convenção do motor equity); comparação com múltiplos "
                     "forward exige ×(1+g) e SÓ vale com m_terminal=1 (fator medido no B0)",
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
    fatos_ref = bloco_fatos_reformulado(inp)   # v3.1.0: valida na carga; None se ausente
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
    res = {
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
    if fatos_ref is not None:                  # gating por presença (nunca retroativo)
        res["fatos_reformulado"] = fatos_ref
    ebit = bloco_ebit_justo(inp, econ)
    if ebit is not None:
        res["ebit_justo"] = ebit
    return res


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
