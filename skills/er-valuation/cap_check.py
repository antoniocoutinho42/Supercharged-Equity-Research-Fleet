#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cap_check.py — PARECER sobre o julgamento de CAP (substitui o tier_cap.py v1.x).

MUDANÇA DE NATUREZA (v2.0): isto NÃO é mais um gate determinístico. O tier_cap.py
antigo devolvia um tier_maximo_elegivel que o Modelador era proibido de exceder;
na prática, a persistência de UM produto virava teto duro do CAP da companhia
inteira (caso ABT: 7,5 anos do Libre -> Tier 0 -> teto 12 para a Abbott toda).
Este script devolve um PARECER: evidência resumida, banda de REFERÊNCIA sugerida
e ALERTAS que o Modelador responde um a um na tabela de premissas. Sobrescrever
o parecer é permitido, com justificativa registrada. O CAP é decisão do Modelador.

Princípios codificados (régua v5):
- CAP = duração econômica provável dos retornos excedentes da COMPANHIA CONSOLIDADA,
  não o número de anos de histórico disponível de um produto.
- Persistência realizada calibra a CONFIANÇA, não é teto automático.
- Em grupos diversificados, a evidência é ponderada por peso econômico dos segmentos;
  um produto/segmento isolado nunca determina sozinho o CAP do grupo.
- Vetor de erosão ABERTO não rebaixa nada automaticamente: exige análise de
  materialidade, probabilidade e horizonte, alocada no parâmetro certo.
- Confiança BAIXA -> ampliar o spread bear-bull e rebaixar convicção,
  nunca impor CAP curto mecanicamente.
- Capacidade comprovada de RENOVAR o moat (inovação, reinvestimento, M&A
  disciplinado, extensão de produtos) justifica CAP acima da persistência realizada.

Bandas de REFERÊNCIA (checklist de julgamento, não gate):
  8-12 default | 12-18 moat claro | 18-25 excepcional | 25-35 geracional
  CAP base >= 25: recomendar auditoria ao Coordenador (não é proibição).

Schema lido (inputs.yaml):
  fatos.duracao:
    consolidada: {persistencia_spread_anos, fonte}        # série de spread da COMPANHIA
    segmentos: [{nome, peso_lucro, persistencia_anos}]    # opcional, grupos diversificados
    fontes_estruturais: [{nome, evidencia}]
    renovacao_moat: {evidencia}                           # renovação comprovada do moat
    vetores_erosao: [{nome, status, materialidade, probabilidade, horizonte_anos}]
    precedentes: [{nome, anos}]
  (retrocompatível com persistencia_realizada_anos do schema v4)
  premissas: cenarios{...cap}, cap_teto_defensavel, cap_confianca,
             justificativa_cap, justificativa_cenarios

Uso:
  python cap_check.py inputs_<TICKER>.yaml [--json]
  python cap_check.py --selftest
"""
import json
import sys

VERSAO = "2.0"
BANDAS = [
    (0, "default", (8, 12)),
    (1, "moat claro", (12, 18)),
    (2, "excepcional", (18, 25)),
    (3, "geracional", (25, 35)),
]


def _persistencias(d):
    """Devolve (consolidada, ponderada_por_segmento, origem)."""
    cons = None
    c = d.get("consolidada") or {}
    if c.get("persistencia_spread_anos") is not None:
        cons = float(c["persistencia_spread_anos"])
    elif d.get("persistencia_realizada_anos") is not None:  # legado v4
        cons = float(d["persistencia_realizada_anos"])
    segs = d.get("segmentos") or []
    pond = None
    if segs:
        pares = [(float(s.get("peso_lucro", 0)), float(s.get("persistencia_anos", 0)))
                 for s in segs if s.get("peso_lucro") is not None]
        peso_total = sum(p for p, _ in pares)
        if peso_total > 0:
            pond = sum(p * a for p, a in pares) / peso_total
    origem = ("consolidada informada" if (d.get("consolidada") or {}).get("persistencia_spread_anos") is not None
              else "legado: persistencia_realizada_anos (verificar se é da companhia ou de um produto)"
              if d.get("persistencia_realizada_anos") is not None else "ausente")
    return cons, (round(pond, 1) if pond is not None else None), origem


def _tem_evidencia(x):
    """Evidência conta apenas se houver texto no campo 'evidencia' (estrutura explícita).
    Corrige o defeito do tier_cap v1.x, em que qualquer string truthy (inclusive
    'não calculado nesta rodada') contava como critério satisfeito."""
    return isinstance(x, dict) and bool(str(x.get("evidencia", "")).strip())


def avaliar(inp):
    f = inp.get("fatos") or {}
    p = inp.get("premissas") or {}
    d = f.get("duracao") or {}
    alertas, notas = [], []

    if not d:
        return {"versao_cap_check": VERSAO,
                "parecer": "SEM_DOSSIE",
                "alertas": ["fatos.duracao ausente: sem o dossiê de duração do Analista, "
                            "qualquer CAP acima da banda default (8-12) exige justificativa "
                            "reforçada e confiança BAIXA declarada"],
                "banda_referencia": "default (8-12)"}

    cons, pond, origem = _persistencias(d)
    fontes = [x for x in (d.get("fontes_estruturais") or []) if _tem_evidencia(x)]
    renovacao = _tem_evidencia(d.get("renovacao_moat"))
    prec = max([float(x.get("anos", 0)) for x in (d.get("precedentes") or [])], default=0.0)
    vetores = d.get("vetores_erosao") or []

    # Evidência-âncora: a melhor leitura disponível da companhia consolidada
    ancora = pond if pond is not None else cons
    if ancora is None:
        alertas.append("nenhuma persistência informada (nem consolidada, nem por segmentos): "
                       "confiança do CAP não pode ser ALTA")

    # Banda de referência sugerida (julgamento auxiliar, não gate):
    # parte da evidência-âncora; renovação comprovada do moat e precedentes longos
    # sustentam banda acima da persistência (extrapolação disciplinada, não fé).
    sugerida = BANDAS[0]
    if ancora is not None:
        score = ancora
        if renovacao:
            score += 5.0            # moat que se auto-renova estende a duração provável
        if prec >= 20 and len(fontes) >= 2:
            score += 3.0            # taxa-base setorial + fontes estruturais múltiplas
        for banda in BANDAS:
            lo, hi = banda[2]
            if score >= lo:
                sugerida = banda
    nome_banda = f"{sugerida[1]} ({sugerida[2][0]}-{sugerida[2][1]})"
    notas.append(f"banda de referência sugerida: {nome_banda} — referência de julgamento; "
                 f"o CAP final é decisão do Modelador, defendida na tabela de premissas")

    # Vetores de erosão: exigem análise, não rebaixamento automático
    for v in vetores:
        status = str(v.get("status", "")).upper()
        if status.startswith(("ABERTO", "AGRAV")):
            faltam = [c for c in ("materialidade", "probabilidade", "horizonte_anos")
                      if not str(v.get(c, "")).strip()]
            if faltam:
                alertas.append(f"vetor de erosão '{v.get('nome', '?')}' está {status} sem "
                               f"{'/'.join(faltam)}: um vetor aberto não rebaixa o CAP "
                               f"automaticamente, mas exige análise de materialidade, "
                               f"probabilidade e horizonte, alocada no parâmetro certo "
                               f"(bear, probabilidade ou spread do CAP) e registrada")
            else:
                notas.append(f"vetor '{v.get('nome', '?')}' ({status}): materialidade "
                             f"{v.get('materialidade')}, probabilidade {v.get('probabilidade')}, "
                             f"horizonte {v.get('horizonte_anos')}a — verificar alocação no parecer")

    # Coerência dos CAPs dos cenários
    cen = p.get("cenarios") or {}
    caps = {n: float(cen[n]["cap"]) for n in ("bear", "base", "bull") if n in cen and "cap" in cen[n]}
    conf = str(p.get("cap_confianca", "")).upper().replace("É", "E")
    teto = p.get("cap_teto_defensavel")
    if caps:
        if ancora is not None and caps.get("base", 0) > 2.0 * ancora:
            alertas.append(f"CAP base ({caps['base']:.0f}) supera 2x a evidência-âncora "
                           f"({ancora:.1f} anos, {origem}): não é proibido, mas exige "
                           f"justificativa reforçada (renovação do moat, precedentes, runway)")
        if pond is None and cons is not None and (d.get("segmentos") is None) and \
           str(origem).startswith("legado"):
            alertas.append("persistência veio de UM número legado sem decomposição por "
                           "segmentos: confirme que mede a companhia consolidada, não um "
                           "produto isolado (um produto nunca determina sozinho o CAP do grupo)")
        if conf == "BAIXA":
            spread = caps.get("bull", 0) - caps.get("bear", 0)
            if caps.get("base") and spread < 0.8 * caps["base"]:
                alertas.append(f"confiança BAIXA com spread bear-bull estreito "
                               f"({spread:.0f} anos vs. base {caps['base']:.0f}): amplie a faixa "
                               f"(bear-bull) em vez de encurtar o CAP mecanicamente")
        if caps.get("base", 0) >= 25:
            notas.append("CAP base na banda geracional (25+): recomende auditoria ao "
                         "Coordenador em uma linha (não é proibição)")
        if teto is not None and caps.get("bull", 0) > float(teto):
            alertas.append(f"CAP bull ({caps['bull']:.0f}) excede o próprio "
                           f"cap_teto_defensavel ({teto}): incoerência interna, ajuste um dos dois")

    if not str(p.get("justificativa_cap", "")).strip():
        alertas.append("justificativa_cap ausente (o engine também recusará)")
    if conf not in ("ALTA", "MEDIA", "BAIXA"):
        alertas.append("cap_confianca ausente ou inválida (ALTA | MEDIA | BAIXA)")

    return {"versao_cap_check": VERSAO,
            "persistencia_consolidada_anos": cons,
            "persistencia_ponderada_segmentos_anos": pond,
            "origem_persistencia": origem,
            "n_fontes_estruturais_com_evidencia": len(fontes),
            "renovacao_moat_evidenciada": renovacao,
            "precedente_max_anos": prec,
            "banda_referencia": nome_banda,
            "confianca_declarada": conf or None,
            "alertas": alertas,
            "notas": notas,
            "natureza": "PARECER de julgamento, não gate: cada alerta exige resposta na "
                        "tabela de premissas; sobrescrever é permitido com justificativa registrada."}


def _selftest():
    casos = []
    # 1. Produto isolado (legado ABT): alerta de consolidação, banda default sugerida,
    #    mas SEM teto imposto.
    abt = {"fatos": {"duracao": {"persistencia_realizada_anos": 7.5,
                                 "fontes_estruturais": [{"nome": "rede", "evidencia": "x"},
                                                        {"nome": "escala", "evidencia": "y"}],
                                 "precedentes": [{"nome": "MDT", "anos": 25}],
                                 "vetores_erosao": [{"nome": "Stelo", "status": "ABERTO"}]}},
           "premissas": {"cenarios": {"bear": {"cap": 5}, "base": {"cap": 7}, "bull": {"cap": 10}},
                         "cap_teto_defensavel": 12, "cap_confianca": "MEDIA",
                         "justificativa_cap": "x", "justificativa_cenarios": "y"}}
    r = avaliar(abt)
    casos.append(("legado 1 produto -> alerta consolidação",
                  any("produto isolado" in a for a in r["alertas"])))
    casos.append(("vetor ABERTO sem materialidade -> alerta de análise, não rebaixamento",
                  any("materialidade" in a for a in r["alertas"])))
    casos.append(("parecer nunca emite teto duro", "tier_maximo_elegivel" not in r))
    # 2. Consolidada longa com renovação: banda alta sugerida
    forte = {"fatos": {"duracao": {"consolidada": {"persistencia_spread_anos": 22, "fonte": "s"},
                                   "fontes_estruturais": [{"nome": "a", "evidencia": "x"},
                                                          {"nome": "b", "evidencia": "y"}],
                                   "renovacao_moat": {"evidencia": "pipeline + M&A disciplinado"},
                                   "precedentes": [{"nome": "p", "anos": 25}],
                                   "vetores_erosao": []}},
             "premissas": {"cenarios": {"bear": {"cap": 12}, "base": {"cap": 18}, "bull": {"cap": 25}},
                           "cap_teto_defensavel": 25, "cap_confianca": "ALTA",
                           "justificativa_cap": "x", "justificativa_cenarios": "y"}}
    r2 = avaliar(forte)
    casos.append(("consolidada 22a + renovação -> banda geracional sugerida",
                  "geracional" in r2["banda_referencia"]))
    casos.append(("sem alertas espúrios no caso forte", r2["alertas"] == []))
    # 3. Ponderação por segmentos
    seg = {"fatos": {"duracao": {"segmentos": [{"nome": "A", "peso_lucro": 0.6, "persistencia_anos": 20},
                                               {"nome": "B", "peso_lucro": 0.4, "persistencia_anos": 5}],
                                 "fontes_estruturais": [{"nome": "a", "evidencia": "x"}],
                                 "precedentes": [{"nome": "p", "anos": 15}]}},
           "premissas": {"cenarios": {"bear": {"cap": 8}, "base": {"cap": 12}, "bull": {"cap": 16}},
                         "cap_teto_defensavel": 18, "cap_confianca": "MEDIA",
                         "justificativa_cap": "x", "justificativa_cenarios": "y"}}
    r3 = avaliar(seg)
    casos.append(("ponderada por segmentos = 14,0", r3["persistencia_ponderada_segmentos_anos"] == 14.0))
    # 4. Evidência negativa não conta (bug do tier_cap v1 corrigido)
    neg = {"fatos": {"duracao": {"consolidada": {"persistencia_spread_anos": 10},
                                 "fontes_estruturais": [{"nome": "a"}],
                                 "renovacao_moat": {},
                                 "precedentes": []}},
           "premissas": {"cenarios": {"bear": {"cap": 6}, "base": {"cap": 9}, "bull": {"cap": 12}},
                         "cap_teto_defensavel": 12, "cap_confianca": "BAIXA",
                         "justificativa_cap": "x", "justificativa_cenarios": "y"}}
    r4 = avaliar(neg)
    casos.append(("fonte sem campo evidencia não conta", r4["n_fontes_estruturais_com_evidencia"] == 0))
    casos.append(("renovacao_moat vazia não conta", r4["renovacao_moat_evidenciada"] is False))
    casos.append(("confiança BAIXA + spread estreito -> alerta de ampliar faixa",
                  any("amplie a faixa" in a for a in r4["alertas"])))
    ok = True
    for nome, passou in casos:
        ok &= passou
        print(f"{'PASS' if passou else 'FAIL'} | {nome}")
    print("SELFTEST:", "OK" if ok else "FALHOU")
    return 0 if ok else 1


def main():
    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    caminho = sys.argv[1]
    with open(caminho, encoding="utf-8") as fh:
        bruto = fh.read()
    if caminho.endswith((".yaml", ".yml")):
        import yaml
        inp = yaml.safe_load(bruto)
    else:
        inp = json.loads(bruto)
    r = avaliar(inp)
    if "--json" in sys.argv:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        print(f"[cap_check v{VERSAO}] persistência consolidada: "
              f"{r.get('persistencia_consolidada_anos')} | ponderada por segmentos: "
              f"{r.get('persistencia_ponderada_segmentos_anos')} ({r.get('origem_persistencia')})")
        print(f"  banda de referência: {r.get('banda_referencia')} | "
              f"confiança declarada: {r.get('confianca_declarada')}")
        for a in r.get("alertas", []):
            print("  ALERTA:", a)
        for n in r.get("notas", []):
            print("  nota:", n)
        print(" ", r.get("natureza", ""))


if __name__ == "__main__":
    main()
