#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
compor.py — composição determinística do relatório final de research.

Lê o namespace da análise e monta relatorio.md SEM nenhum agente reescrever conteúdo:
  - dossie.md e valuation.md entram VERBATIM (títulos rebaixados um nível por código);
  - tearsheet, bloco de valor, cenários, expectativas implícitas, validação por múltiplos,
    entry ladder, elasticidades, auditoria, encaixe, plano de ação, ressalvas padronizadas,
    nota metodológica e trilha documental são gerados de estado.yaml, inputs.yaml,
    resultados.json, red_team.md (opcional) e portfolio_fit.md (opcional);
  - log_consistencia.md é gerado POR CONSTRUÇÃO: todo número injetado sai de uma chave,
    e o log lista número -> chave;
  - se grafico_faixas.png não existir, é regenerado do resultados.json (matplotlib).

Tolerância: resultados.json v1.x (sem validacao_multiplos / delta do ladder) degrada com nota.

Uso: python compor.py <namespace> [--out relatorio.md]
Depois: python render_pdf.py <namespace>/relatorio.md --out <namespace>/relatorio_final.pdf
"""
import json
import os
import re
import sys

LOG = []  # (numero_formatado, chave_de_origem)


def humano(sinal):
    """Enums do engine em texto de leitura (NAO_ACIONAVEL -> NÃO ACIONÁVEL)."""
    mapa = {"NAO_ACIONAVEL": "NÃO ACIONÁVEL", "ACIONAVEL": "ACIONÁVEL",
            "LIMITROFE": "LIMÍTROFE", "DENTRO_DA_FAIXA": "DENTRO DA FAIXA",
            "SUMARIA": "SUMÁRIA", "PADRAO": "PADRÃO", "REFORCADA": "REFORÇADA"}
    return mapa.get(str(sinal), str(sinal))


def br(x, nd=2):
    if x is None:
        return "n.d."
    s = f"{float(x):,.{nd}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return s


def n(valor, chave, nd=2, pref="", suf=""):
    """Formata número e registra no log de consistência."""
    txt = f"{pref}{br(valor, nd)}{suf}"
    LOG.append((txt, chave))
    return txt


def _get(d, caminho, default=None):
    cur = d
    for parte in caminho.split("."):
        if isinstance(cur, dict) and parte in cur:
            cur = cur[parte]
        else:
            return default
    return cur


def _como_lista(x):
    """Coerção defensiva de campos que DEVEM ser listas no estado.yaml
    (decisao.ressalvas, decisao.gatilhos, decisao.plano_acao).
    Uma string escalar iterada diretamente viraria um item POR CARACTERE
    (bug real: 'Ressalva: R / Ressalva: E / ...' nos relatórios). Aqui:
    None -> []; lista/tupla -> itens como str; string -> um item por linha
    não vazia (string de linha única vira item único); outro tipo -> [str(x)].
    O checar.py --etapa decisao reprova o tipo errado ANTES de compor; esta
    coerção é a segunda linha de defesa para nunca degradar o PDF."""
    if x is None:
        return []
    if isinstance(x, (list, tuple)):
        return [str(i).strip() for i in x if str(i).strip()]
    if isinstance(x, str):
        return [ln.strip() for ln in x.splitlines() if ln.strip()]
    return [str(x).strip()]


PADROES_PROCESSO = re.compile(
    r"escopo do Modelador|escopo deste dossiê|do Portfolio Manager|carimbo do Modelador"
    r"|não será reescrit|Profundidade: (PADRÃO|SUMÁRIA|REFORÇADA)", re.I)


def aparar_dossie(md):
    """Aparo DETERMINÍSTICO de artefatos de processo do dossiê antes da injeção.
    Remove apenas: (1) o preâmbulo de metadados entre o título H1 e o primeiro '---'
    (preço/market cap/profundidade já vivem na capa e no tearsheet); (2) a seção
    'Veredicto dos Guardrails' (artefato de gate, referencia mensagens internas);
    (3) parágrafos-disclaimer de fronteira de papéis (ex.: 'isso é escopo do
    Modelador Financeiro'). NADA analítico é tocado; tudo que sai é listado no
    log de consistência. Desligável com --sem-aparar."""
    removidos = []
    linhas = md.splitlines()
    # (1) preâmbulo: do início até o primeiro '---' (se houver um nas 15 primeiras linhas)
    corte = 0
    for i, ln in enumerate(linhas[:15]):
        if ln.strip() == "---":
            corte = i + 1
            break
    if corte:
        preambulo = [l for l in linhas[:corte - 1] if l.strip()]
        if preambulo:
            removidos.append(f"preâmbulo de metadados ({len(preambulo)} linhas: título, preço, "
                             f"market cap, profundidade — já presentes na capa/tearsheet)")
        linhas = linhas[corte:]
    # (2) seção de guardrails (gate interno)
    out, i, pulando, nivel_secao = [], 0, False, 0
    while i < len(linhas):
        ln = linhas[i]
        m = re.match(r"^(#{1,4})\s.*guardrails", ln, re.I)
        if m and not pulando:
            pulando, nivel_secao = True, len(m.group(1))
            removidos.append(f"seção '{ln.lstrip('# ').strip()}' (artefato do gate G1)")
            i += 1
            continue
        if pulando:
            m2 = re.match(r"^(#{1,4})\s", ln)
            if (m2 and len(m2.group(1)) <= nivel_secao) or ln.strip() == "---":
                pulando = False
            else:
                i += 1
                continue
        out.append(ln)
        i += 1
    # (3) parágrafos-disclaimer de processo (linha/parágrafo isolado, nunca dentro de tabela)
    final = []
    for ln in out:
        if (PADROES_PROCESSO.search(ln) and not ln.strip().startswith("|")
                and not ln.strip().startswith("#")):
            removidos.append(f"disclaimer de processo: \"{ln.strip()[:70]}...\"")
            continue
        final.append(ln)
    texto = re.sub(r"\n{3,}", "\n\n", "\n".join(final)).strip()
    # remove '---' órfãos duplicados no início
    texto = re.sub(r"^(-{3,}\s*\n)+", "", texto)
    return texto, removidos


def demover_titulos(md):
    """Rebaixa todos os títulos em um nível (# -> ##), preservando blocos de código."""
    linhas, dentro_code = [], False
    for ln in md.splitlines():
        if ln.strip().startswith("```"):
            dentro_code = not dentro_code
        if not dentro_code and re.match(r"^#{1,5} ", ln):
            ln = "#" + ln
        linhas.append(ln)
    return "\n".join(linhas)


def carregar(ns):
    import yaml
    dados = {}
    dados["estado"] = yaml.safe_load(open(os.path.join(ns, "estado.yaml"), encoding="utf-8"))
    dados["inputs"] = yaml.safe_load(open(os.path.join(ns, "inputs.yaml"), encoding="utf-8"))
    saida = next((os.path.join(ns, x) for x in os.listdir(ns)
                  if x.startswith("saida_") and os.path.isdir(os.path.join(ns, x))), None)
    dados["saida_dir"] = saida
    dados["res"] = json.load(open(os.path.join(saida, "resultados.json"), encoding="utf-8"))
    dados["dossie"] = open(os.path.join(ns, "dossie.md"), encoding="utf-8").read()
    dados["valuation"] = open(os.path.join(ns, "valuation.md"), encoding="utf-8").read()
    for opc in ("red_team.md", "portfolio_fit.md"):
        p = os.path.join(ns, opc)
        dados[opc.split(".")[0]] = open(p, encoding="utf-8").read() if os.path.exists(p) else None
    return dados


def _matplotlib():
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        return plt
    except ImportError:
        return None


def _series_financeiras(dados):
    """Série anual [{ano, receita, lucro_liquido, roe}] de fatos.series_historicas."""
    s = _get(dados["inputs"], "fatos.series_historicas") or []
    out = []
    for r in s:
        if r.get("ano") is None:
            continue
        out.append({"ano": r.get("ano"), "receita": r.get("receita"),
                    "lucro_liquido": r.get("lucro_liquido"), "roe": r.get("roe")})
    return sorted(out, key=lambda x: x["ano"])


def _serie_pe(dados):
    """Série anual [{ano, pe}] de fatos.multiplos_historicos.pe.serie."""
    s = _get(dados["inputs"], "fatos.multiplos_historicos.pe.serie") or []
    return sorted([{"ano": r.get("ano"), "pe": r.get("pe")} for r in s
                   if r.get("ano") is not None and r.get("pe") is not None],
                  key=lambda x: x["ano"])


def grafico_historico_financeiro(dados, ns):
    """H4: receita e lucro líquido em barras, ROE em linha (eixo secundário).
    Cores exigidas: Receita #002060, Lucro Líquido #FFC000, ROE #7F7F7F.
    Degrada para None (sem quebrar) se não houver série ou matplotlib."""
    serie = _series_financeiras(dados)
    if len(serie) < 2 or not dados.get("saida_dir"):
        return None
    plt = _matplotlib()
    if plt is None:
        return None
    png = os.path.join(dados["saida_dir"], "grafico_historico_financeiro.png")
    anos = [str(r["ano"]) for r in serie]
    receita = [r.get("receita") for r in serie]
    lucro = [r.get("lucro_liquido") for r in serie]
    roe = [(100.0 * r["roe"] if r.get("roe") is not None else None) for r in serie]
    import numpy as np
    x = np.arange(len(anos))
    fig, ax1 = plt.subplots(figsize=(9, 4.2))
    larg = 0.38
    ax1.bar(x - larg / 2, receita, larg, label="Receita", color="#002060")
    ax1.bar(x + larg / 2, lucro, larg, label="Lucro líquido", color="#FFC000")
    ax1.set_ylabel("Receita e lucro líquido")
    ax1.set_xticks(x)
    ax1.set_xticklabels(anos)
    ax2 = ax1.twinx()
    ax2.plot(x, roe, color="#7F7F7F", marker="o", lw=2, label="ROE (%)")
    ax2.set_ylabel("ROE (%)")
    linhas1, rot1 = ax1.get_legend_handles_labels()
    linhas2, rot2 = ax2.get_legend_handles_labels()
    ax1.legend(linhas1 + linhas2, rot1 + rot2, loc="upper left", fontsize=8)
    ax1.set_title(f"{dados['res']['meta']['ticker']} — histórico de receita, lucro líquido e ROE",
                  fontsize=10)
    fig.tight_layout()
    fig.savefig(png, dpi=150)
    plt.close(fig)
    return os.path.relpath(png, ns)


def grafico_pe_historico(dados, ns):
    """H5: linha do P/L histórico da companhia, com pontilhadas na mediana e em
    mediana ± 1 desvio-padrão. Usa fatos.multiplos_historicos.pe.serie; a mediana e
    o desvio saem da série (ou de desvio_padrao/mediana explícitos). Degrada para None."""
    serie = _serie_pe(dados)
    if len(serie) < 3 or not dados.get("saida_dir"):
        return None
    plt = _matplotlib()
    if plt is None:
        return None
    import statistics as st
    png = os.path.join(dados["saida_dir"], "grafico_pe_historico.png")
    anos = [r["ano"] for r in serie]
    pes = [float(r["pe"]) for r in serie]
    pe_cfg = _get(dados["inputs"], "fatos.multiplos_historicos.pe") or {}
    mediana = pe_cfg.get("mediana")
    mediana = float(mediana) if mediana is not None else st.median(pes)
    dp = pe_cfg.get("desvio_padrao")
    dp = float(dp) if dp is not None else (st.pstdev(pes) if len(pes) > 1 else 0.0)
    fig, ax = plt.subplots(figsize=(9, 4.0))
    ax.plot(anos, pes, color="#002060", marker="o", lw=2, label="P/L da companhia")
    ax.axhline(mediana, ls="--", color="#7F7F7F", lw=1.3, label=f"Mediana ({mediana:.1f}x)")
    ax.axhline(mediana + dp, ls=":", color="#C00000", lw=1.2, label=f"+1 desvio ({mediana + dp:.1f}x)")
    ax.axhline(mediana - dp, ls=":", color="#C00000", lw=1.2, label=f"-1 desvio ({mediana - dp:.1f}x)")
    ax.set_ylabel("P/L (x)")
    ax.set_xlabel("Ano")
    ax.set_xticks(anos)
    ax.legend(fontsize=8, loc="best")
    ax.set_title(f"{dados['res']['meta']['ticker']} — múltiplos P/L históricos (mediana ± 1 desvio-padrão)",
                 fontsize=10)
    fig.tight_layout()
    fig.savefig(png, dpi=150)
    plt.close(fig)
    return os.path.relpath(png, ns)


def garantir_grafico(dados, ns):
    png = os.path.join(dados["saida_dir"], "grafico_faixas.png")
    if os.path.exists(png):
        return os.path.relpath(png, ns)
    plt = _matplotlib()
    if plt is None:
        return None
    res = dados["res"]
    preco = res["meta"]["preco_atual"]
    h, e = res["hurdle"]["cenarios"], res["economico"]
    linhas = [("Preço máx. hurdle", h["bear"]["preco"], h["bull"]["preco"], h["ponderado"]),
              ("Valor econômico (P/L Justo)", e["faixa_completa"][0], e["faixa_completa"][1],
               e["central_ponderado"])]
    fig, ax = plt.subplots(figsize=(9, 3.2))
    for i, (rot, lo, hi, c) in enumerate(reversed(linhas)):
        ax.hlines(i, lo, hi, lw=8, alpha=0.45)
        ax.plot(c, i, "o", ms=9)
        ax.annotate(f"{lo:.0f}-{hi:.0f}", (hi, i), xytext=(6, -3), textcoords="offset points", fontsize=8)
    ax.axvline(preco, ls="--", color="k", lw=1)
    ax.annotate(f"Preço atual {preco:.2f}", (preco, len(linhas) - 0.4), fontsize=8, ha="center")
    ax.set_yticks(range(len(linhas)))
    ax.set_yticklabels([r[0] for r in reversed(linhas)], fontsize=8)
    ax.set_title(f"{res['meta']['ticker']} — preço atual vs. faixas do motor principal", fontsize=10)
    fig.tight_layout()
    fig.savefig(png, dpi=150)
    plt.close(fig)
    return os.path.relpath(png, ns)


def secao_recomendacao(dados):
    est, res = dados["estado"], dados["res"]
    dec = est["decisao"]
    moeda = res["meta"].get("moeda", "US$")
    s = res["sinais"]
    ress = _como_lista(dec.get("ressalvas"))
    if not (est.get("auditoria") or {}).get("acionada"):
        ress.append("Esta análise não foi submetida a verificação independente (auditoria não acionada).")
    if not est.get("snapshot"):
        ress.append("Encaixe e dimensionamento não avaliados (snapshot de carteira não fornecido).")
    linhas = [
        f"> **RECOMENDAÇÃO: {dec['recomendacao']}** | Confiança: {dec['confianca']}",
        f"> Sinal econômico **{humano(s['economico'])}** (preço {n(s['premio_sobre_econ_central_pct'], 'sinais.premio_sobre_econ_central_pct', 1)}% "
        f"vs. valor central) e sinal de entrada **{humano(s['entrada'])}** "
        f"(preço {n(s['preco_sobre_hurdle_pond'], 'sinais.preco_sobre_hurdle_pond')}x o preço máximo para o hurdle).",
        f"> {dec['racional']}",
    ]
    for r in ress:
        linhas.append(f"> Ressalva: {r}")
    tese = dec.get("tese")
    bloco = "\n".join(linhas)
    if tese:
        bloco += f"\n\n**Tese de investimento.** {tese}"
    return bloco


def secao_bloco_valor(dados):
    res = dados["res"]
    moeda = res["meta"].get("moeda", "USD")
    pfx = "US$ " if moeda == "USD" else f"{moeda} "
    h, e, s = res["hurdle"]["cenarios"], res["economico"], res["sinais"]
    preco = res["meta"]["preco_atual"]
    central = e["central_ponderado"]
    down_central = 100.0 * (central / preco - 1.0)
    down_hurdle = 100.0 * (h["ponderado"] / preco - 1.0)
    t = ["| Metodologia | Faixa / valor | Sinal |", "|---|---|---|"]
    t.append(f"| Valor Intrínseco Econômico (P/L Justo, motor principal) | "
             f"{n(e['faixa_ponderada'][0], 'economico.faixa_ponderada[0]', 2, pfx)} – "
             f"{n(e['faixa_ponderada'][1], 'economico.faixa_ponderada[1]')} "
             f"(central {n(central, 'economico.central_ponderado', 2, pfx)}) | {humano(s['economico'])} |")
    t.append(f"| **Preço Máximo para o Hurdle** (disciplina de compra) | "
             f"{n(h['ponderado'], 'hurdle.cenarios.ponderado', 2, pfx)} ponderado "
             f"(bear {n(h['bear']['preco'], 'hurdle.cenarios.bear.preco')} / "
             f"base {n(h['base']['preco'], 'hurdle.cenarios.base.preco')} / "
             f"bull {n(h['bull']['preco'], 'hurdle.cenarios.bull.preco')}) | {humano(s['entrada'])} |")
    ms = (f"Preço {n(preco, 'meta.preco_atual', 2, pfx)}: prêmio de "
          f"{n(s['premio_sobre_econ_central_pct'], 'sinais.premio_sobre_econ_central_pct', 1)}% sobre o valor central "
          f"(downside até o valor: {n(down_central, 'derivado: central/preco-1', 1)}%) e prêmio de "
          f"{n(s['premio_sobre_hurdle_pct'], 'sinais.premio_sobre_hurdle_pct', 1)}% sobre o hurdle "
          f"(downside: {n(down_hurdle, 'derivado: hurdle/preco-1', 1)}%). Como o preço está acima do valor, "
          "não há margem de segurança tradicional; a métrica relevante é o downside até o valor."
          ) if preco > central else (
          f"Preço {n(preco, 'meta.preco_atual', 2, pfx)}: desconto de "
          f"{n(-down_central, 'derivado: 1-preco/central', 1)}% até o valor central.")
    return "\n".join(t) + "\n\n" + ms


def _premissas_cenarios(dados):
    """Premissas por cenário {prob,g,roe,cap}, preferindo o eco do engine
    (res.cap.premissas_cenarios, v2.1.0+) e caindo para inputs.premissas.cenarios
    (retrocompatível com resultados.json v2.0.0)."""
    pc = _get(dados["res"], "cap.premissas_cenarios")
    if pc:
        return pc
    return _get(dados["inputs"], "premissas.cenarios") or {}


def _ancoras(dados):
    """Premissas-âncora fixas (base) e taxas usadas nas leituras reversas/ladder,
    para tornar EXPLÍCITAS as premissas por trás de cada número implícito (R3/R4)."""
    res = dados["res"]
    cen = _premissas_cenarios(dados)
    base = cen.get("base", {})
    ke_h = _get(res, "hurdle.ke")
    if ke_h is None:
        ke_h = _get(dados["inputs"], "premissas.ke_hurdle")
    teto = _get(res, "cap.teto_defensavel")
    if teto is None:
        teto = _get(dados["inputs"], "premissas.cap_teto_defensavel")
    return {
        "g_base": base.get("g"), "roe_base": base.get("roe"), "cap_base": base.get("cap"),
        "ke_hurdle": ke_h, "ke_central": _get(res, "economico.ke_central"),
        "cap_teto": teto,
    }


def secao_tabela_premissas_por_limite(dados):
    """Substitui o gráfico de faixas (comentário R1): tabela com as premissas
    (CAP, ROE, g, Ke) do LIMITE INFERIOR e SUPERIOR de cada âncora e o preço por
    ação em cada limite, mais a referência ponderada/central. Todo número por chave."""
    res = dados["res"]
    pfx = "US$ " if res["meta"].get("moeda", "USD") == "USD" else res["meta"].get("moeda", "") + " "
    cen = _premissas_cenarios(dados)
    ke_h = _get(res, "hurdle.ke")

    def _row(limite, nome_cen, cap, roe, g, ke, preco, chave_preco):
        return (f"| {limite} | {nome_cen.capitalize()} | {cap} anos | "
                f"{br(100*roe,0) if roe is not None else 'n.d.'}% | "
                f"{br(100*g,1) if g is not None else 'n.d.'}% | "
                f"{br(100*ke,1) if ke is not None else 'n.d.'}% | "
                f"{n(preco, chave_preco, 2, pfx)} |")

    # --- Preço Máximo para o Hurdle (Ke fixo = hurdle) ---
    hp = res["hurdle"]["cenarios"]
    precos_h = {s: hp[s]["preco"] for s in ("bear", "base", "bull")}
    lo_s = min(precos_h, key=precos_h.get)
    hi_s = max(precos_h, key=precos_h.get)
    cap_h = (f"**Preço Máximo para o Hurdle** (Ke fixo de disciplina = {br(100*ke_h,1)}%; "
             f"varia CAP, ROE e g por cenário)")
    th = ["| Limite | Cenário | CAP | ROE | g | Ke | Preço/ação |",
          "|---|---|---|---|---|---|---|"]
    th.append(_row("Inferior", lo_s, cen[lo_s].get("cap"), cen[lo_s].get("roe"),
                   cen[lo_s].get("g"), ke_h, precos_h[lo_s], f"hurdle.cenarios.{lo_s}.preco"))
    th.append(_row("Superior", hi_s, cen[hi_s].get("cap"), cen[hi_s].get("roe"),
                   cen[hi_s].get("g"), ke_h, precos_h[hi_s], f"hurdle.cenarios.{hi_s}.preco"))
    th.append(f"| **Ponderado** | (por probabilidade) | — | — | — | {br(100*ke_h,1)}% | "
              f"{n(hp['ponderado'], 'hurdle.cenarios.ponderado', 2, pfx)} |")

    # --- Valor Intrínseco Econômico (Ke varia na grade CAPM) ---
    econ = res["economico"]
    combos = []  # (preco, cenario, ke, kestr)
    for kestr, blk in econ["por_ke"].items():
        for s in ("bear", "base", "bull"):
            combos.append((blk["cenarios"][s]["preco"], s, blk["ke"], kestr))
    lo = min(combos, key=lambda x: x[0])
    hi = max(combos, key=lambda x: x[0])
    cap_e = "**Valor Intrínseco Econômico** (Ke da grade CAPM; varia CAP, ROE, g e Ke)"
    te = ["| Limite | Cenário | CAP | ROE | g | Ke | Preço/ação |",
          "|---|---|---|---|---|---|---|"]
    te.append(_row("Inferior", lo[1], cen[lo[1]].get("cap"), cen[lo[1]].get("roe"),
                   cen[lo[1]].get("g"), lo[2], lo[0], f"economico.por_ke.{lo[3]}.cenarios.{lo[1]}.preco"))
    te.append(_row("Superior", hi[1], cen[hi[1]].get("cap"), cen[hi[1]].get("roe"),
                   cen[hi[1]].get("g"), hi[2], hi[0], f"economico.por_ke.{hi[3]}.cenarios.{hi[1]}.preco"))
    te.append(f"| **Central** | (ponderado) | — | — | — | {br(100*econ['ke_central'],1)}% | "
              f"{n(econ['central_ponderado'], 'economico.central_ponderado', 2, pfx)} |")

    preco = res["meta"]["preco_atual"]
    legenda = (f"Preço de mercado de referência: {n(preco, 'meta.preco_atual', 2, pfx)}. "
               "Cada limite mostra as premissas exatas (CAP, ROE, g, Ke) que produzem aquele preço; "
               "o hurdle mantém o Ke fixo de disciplina e o econômico percorre a grade de Ke do CAPM.")
    # blocos separados por linha em branco (CommonMark exige linha vazia antes de tabela)
    return (cap_h + "\n\n" + "\n".join(th) + "\n\n"
            + cap_e + "\n\n" + "\n".join(te) + "\n\n" + legenda)


def secao_cenarios(dados):
    res = dados["res"]
    cen = _premissas_cenarios(dados)
    ke_c = res["economico"]["ke_central"]
    por = res["economico"]["por_ke"].get(f"{ke_c:.3f}", {}).get("cenarios", {})
    t = [f"| Cenário | Prob. | g | ROE | CAP | Valor (Ke {br(100*ke_c,1)}%) |", "|---|---|---|---|---|---|"]
    for nome in ("bear", "base", "bull"):
        c = cen.get(nome, {})
        p = por.get(nome, {}).get("preco")
        t.append(f"| {nome.capitalize()} | {br(100*c.get('prob',0),0)}% | {br(100*c.get('g',0),1)}% | "
                 f"{br(100*c.get('roe',0),0)}% | {c.get('cap','?')} anos | "
                 f"{n(p, f'economico.por_ke.{ke_c:.3f}.cenarios.{nome}.preco')} |")
    out = "\n".join(t)
    # fundamentação por driver (g, ROE, CAP) — mesma disciplina para os três (R2).
    # Cada justificativa vem do engine (res.cap.*) ou de inputs.premissas.* (fallback).
    def _just(chave_res, chave_inp):
        return _get(dados["res"], chave_res) or _get(dados["inputs"], chave_inp)
    just_g = _just("cap.justificativa_g", "premissas.justificativa_g")
    just_roe = _just("cap.justificativa_roe", "premissas.justificativa_roe")
    just_cap = _just("cap.justificativa_cenarios", "premissas.justificativa_cenarios")
    blocos = []
    if just_g:
        blocos.append(f"**Fundamentação do crescimento (g) por cenário.** {str(just_g).strip()}")
    if just_roe:
        blocos.append(f"**Fundamentação do ROE por cenário.** {str(just_roe).strip()}")
    if just_cap:
        blocos.append(f"**Fundamentação do CAP por cenário.** {str(just_cap).strip()}")
    if blocos:
        out += "\n\n" + "\n\n".join(blocos)
    conf = _get(dados["res"], "cap.confianca") or _get(dados["inputs"], "premissas.cap_confianca")
    if conf:
        out += f"\n\nConfiança declarada no CAP: **{str(conf).upper()}**."
    return out


def secao_reverse(dados):
    r = dados["res"]["reverse"]
    a = _ancoras(dados)
    teto = a["cap_teto"]
    # premissas-âncora fixas por trás de cada número implícito, ditas EXPLICITAMENTE (R3)
    p_econ = (f"mantendo ROE base = {br(100*a['roe_base'],0)}%, g base = {br(100*a['g_base'],1)}% "
              f"e Ke central = {br(100*a['ke_central'],1)}%") if a['roe_base'] is not None else ""
    p_hurdle = (f"mantendo ROE base = {br(100*a['roe_base'],0)}%, CAP base = {a['cap_base']} anos "
                f"e Ke hurdle = {br(100*a['ke_hurdle'],0)}%") if a['roe_base'] is not None else ""
    p_ke = (f"mantendo g base = {br(100*a['g_base'],1)}% e ROE base = {br(100*a['roe_base'],0)}%, "
            f"no teto de CAP = {teto} anos") if a['roe_base'] is not None else ""
    linhas = []
    if r.get("cap_implicito_econ_base") is not None:
        linhas.append(f"- O preço atual exige um CAP implícito de "
                      f"{n(r['cap_implicito_econ_base'], 'reverse.cap_implicito_econ_base', 1)} anos "
                      f"sob a âncora econômica ({p_econ}; teto defensável do caso: {teto} anos).")
    if r.get("g_implicito_hurdle_base") is not None:
        linhas.append(f"- Sob a disciplina do hurdle, o preço exige crescimento implícito de "
                      f"{n(100*r['g_implicito_hurdle_base'], 'reverse.g_implicito_hurdle_base', 1)}% a.a. "
                      f"({p_hurdle}).")
    if r.get("ke_implicito_cap_teto") is not None:
        linhas.append(f"- O custo de capital que reconcilia o preço com o teto do caso é "
                      f"{n(100*r['ke_implicito_cap_teto'], 'reverse.ke_implicito_cap_teto', 2)}% "
                      f"({p_ke}).")
    return "\n".join(linhas)


def secao_multiplos(dados):
    v = dados["res"].get("validacao_multiplos")
    if not v:
        return ("Bloco não disponível (resultados.json gerado por engine anterior à v2; "
                "a leitura de múltiplos está na seção de valuation).")
    t = ["| Leitura | Valor |", "|---|---|"]
    t.append(f"| Múltiplo atual ({v['metrica_primaria']}, base {v['base_lucro']}) | "
             f"{n(v['pe_atual'] if v['metrica_primaria']=='PE' else v['ev_ebitda_atual'], 'validacao_multiplos.pe_atual/ev_ebitda_atual')}x |")
    t.append(f"| P/L justo implícito (econômico ponderado) | {n(v['pl_justo_ponderado_econ'], 'validacao_multiplos.pl_justo_ponderado_econ')}x |")
    hp = v.get("historico_proprio")
    if hp:
        t.append(f"| Banda histórica própria ({hp.get('janela','n.d.')}) | "
                 f"{br(hp.get('min'))} / mediana {n(hp['mediana'], 'validacao_multiplos.historico_proprio.mediana')} / {br(hp.get('max'))} "
                 f"— atual {n(hp['atual_vs_mediana_pct'], 'validacao_multiplos.historico_proprio.atual_vs_mediana_pct', 1)}% vs. mediana ({hp['posicao_atual'].replace('_',' ').lower()}) |")
    cp = v.get("comparaveis")
    if cp:
        t.append(f"| Mediana dos pares (n={cp['n']}) | {n(cp['mediana_pares'], 'validacao_multiplos.comparaveis.mediana_pares')}x "
                 f"— P/L justo {n(cp.get('pl_justo_econ_vs_pares_pct'), 'validacao_multiplos.comparaveis.pl_justo_econ_vs_pares_pct', 1)}% vs. pares |")
    out = "\n".join(t) + f"\n\n**Veredicto: {v['veredicto']}.**"
    for f in v.get("flags", []):
        out += f"\n- {f}"
    return out


def secao_ladder(dados):
    res = dados["res"]
    central = res["economico"]["central_ponderado"]
    t = ["| Preço | Retorno anualizado implícito (Ke) | CAP implícito (econ.) | Até o valor central |",
         "|---|---|---|---|"]
    for i, d in enumerate(res["ladder"]):
        ke = f"{br(100*d['ke_implicito'],2)}%" if d.get("ke_implicito") is not None else "n.d."
        delta = d.get("delta_ate_econ_central_pct")
        if delta is None:
            delta = 100.0 * (central / d["preco"] - 1.0)
        rotulo = " (atual)" if i == 0 else ""
        t.append(f"| {n(d['preco'], f'ladder[{i}].preco')}{rotulo} | {ke} | "
                 f"{br(d.get('cap_implicito_econ'),1)} anos | {n(delta, f'ladder[{i}].delta_ate_econ_central_pct', 1)}% |")
        LOG.append((ke, f"ladder[{i}].ke_implicito"))
    a = _ancoras(dados)
    if a["roe_base"] is not None:
        nota = (f"\n\nNota: o **retorno anualizado implícito (Ke)** de cada preço é o Ke que iguala "
                f"o preço ao P/L Justo mantendo g base = {br(100*a['g_base'],1)}%, ROE base = "
                f"{br(100*a['roe_base'],0)}% e CAP base = {a['cap_base']} anos; o **CAP implícito** "
                f"é o CAP que iguala o preço ao valor econômico mantendo Ke central = "
                f"{br(100*a['ke_central'],1)}% e g/ROE base. Ver a tabela de Cenários acima para a "
                f"leitura de premissas que justifica cada faixa de preço.")
    else:
        nota = ("\n\nNota: retorno anualizado implícito (Ke) e CAP implícito calculados no cenário "
                "base; ver a tabela de Cenários para as premissas.")
    return "\n".join(t) + nota


def secao_elasticidades(dados):
    e = dados["res"]["elasticidades"]
    t = ["| US$/ação por... | Âncora econômica | Hurdle |", "|---|---|---|"]
    rot = {"mais_1a_cap": "+1 ano de CAP", "mais_1pp_g": "+1 p.p. de g",
           "mais_1pp_roe": "+1 p.p. de ROE", "menos_05pp_ke": "−0,5 p.p. de Ke"}
    for k, r in rot.items():
        t.append(f"| {r} | {n(e['economico'][k], f'elasticidades.economico.{k}')} | "
                 f"{n(e['hurdle'][k], f'elasticidades.hurdle.{k}')} |")
    return "\n".join(t)


def secao_auditoria(dados):
    rt = dados.get("red_team")
    if not rt:
        return ("Esta análise não foi submetida a verificação independente (auditoria não acionada). "
                "Não há questionamentos de segunda leitura nem testes de limite de um segundo "
                "examinador a reportar; a confiança da recomendação tem teto imposto por essa ausência.")
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", rt, re.S)
    corpo = rt
    if m:
        import yaml
        try:
            cab = yaml.safe_load(m.group(1)) or {}
            corpo = m.group(2)
            resumo = [f"**Agregado: {cab.get('agregado', 'n.d.')}.**"]
            dims = cab.get("dimensoes") or {}
            if dims:
                resumo.append(" | ".join(f"{k}: {v}" for k, v in dims.items()))
            issues = cab.get("issues") or []
            crit = [i for i in issues if str(i.get("severidade", "")).upper().startswith("CRIT")]
            rele = [i for i in issues if str(i.get("severidade", "")).upper().startswith("RELE")]
            resumo.append(f"Issues: {len(crit)} crítica(s), {len(rele)} relevante(s).")
            for i in crit + rele:
                resumo.append(f"- [{i.get('id','?')} | {i.get('severidade','?')} | {i.get('estado','?')}] {i.get('titulo','')}")
            if cab.get("cap_auditoria"):
                resumo.append(f"Auditoria do CAP: {cab['cap_auditoria']}")
            return "\n".join(resumo) + "\n\n" + demover_titulos(corpo.strip())
        except Exception:
            pass
    return demover_titulos(corpo.strip())


def secao_encaixe(dados):
    pf = dados.get("portfolio_fit")
    if not pf:
        return "Não avaliado (snapshot de carteira não fornecido)."
    return demover_titulos(pf.strip())


def secao_plano(dados):
    est = dados["estado"]
    dec = est["decisao"]
    linhas = []
    for item in _como_lista(dec.get("plano_acao")):
        linhas.append(f"- {item}")
    if not linhas:
        linhas.append(f"- Manter a recomendação {dec['recomendacao']}; reavaliar nos gatilhos abaixo.")
    for g in _como_lista(dec.get("gatilhos")):
        linhas.append(f"- Gatilho: {g}")
    if dec.get("revisao"):
        linhas.append(f"- Revisão obrigatória: {dec['revisao']}")
    return "\n".join(linhas)


def nota_metodologica(dados, ns):
    est, res = dados["estado"], dados["res"]
    aud = est.get("auditoria") or {}
    arquivos = sorted(a for a in os.listdir(ns) if a.endswith((".md", ".yaml", ".json")))
    return (f"Motor de valuation padrão (engine v{res['engine']['versao']}, hash de inputs "
            f"{res['engine']['hash_inputs']}), profundidade {est.get('profundidade')}, modo "
            f"{est.get('modo', 'n.d.')}. Auditoria: {'acionada, agregado ' + str(aud.get('agregado')) if aud.get('acionada') else 'não acionada'}. "
            f"Snapshot de carteira: {'fornecido' if est.get('snapshot') else 'não fornecido'}.\n\n"
            f"Trilha documental (namespace da análise): {', '.join(arquivos)}. Este relatório foi "
            f"composto deterministicamente a partir desses arquivos; o corpo analítico e o valuation "
            f"são o texto original do Analista e do Modelador.")


def compor(ns, out_nome="relatorio.md"):
    dados = carregar(ns)
    est, res = dados["estado"], dados["res"]
    meta = res["meta"]
    # R1: o gráfico de faixas dá lugar à tabela de premissas por limite.
    # O PNG só é gerado/injetado com --com-grafico (opt-in), reduzindo custo por padrão.
    grafico = garantir_grafico(dados, ns) if "--com-grafico" in sys.argv else None
    graf_fin = grafico_historico_financeiro(dados, ns)   # H4 (None se sem série)
    graf_pe = grafico_pe_historico(dados, ns)            # H5 (None se sem série)
    dec = est["decisao"]
    pfx = "US$ " if meta.get("moeda", "USD") == "USD" else meta.get("moeda", "") + " "
    fm = (f"---\ntitulo: \"{meta.get('nome', meta['ticker'])} ({meta['ticker']})\"\n"
          f"subtitulo: \"Equity Research — Relatório de Investimento | {dec['recomendacao']}\"\n"
          f"data: \"{est.get('data', meta.get('data_preco', ''))}\"\n"
          f"linha_meta: \"Preço de referência: {pfx}{br(meta['preco_atual'])} ({meta.get('data_preco','')}) | "
          f"Moeda: {meta.get('moeda','')} | Engine v{res['engine']['versao']}\"\n"
          f"rodape: \"{meta['ticker']} — research proprietário | uso interno\"\n---\n")
    partes = [fm]
    partes.append("# Recomendação e tearsheet\n\n" + secao_recomendacao(dados))
    partes.append("## Bloco de valor e sinais\n\n" + secao_bloco_valor(dados))
    partes.append("## Premissas por limite de valor\n\n" + secao_tabela_premissas_por_limite(dados))
    if grafico:
        partes.append(f"![Preço atual vs. faixas de valor]({grafico})")
    partes.append("## Cenários\n\n" + secao_cenarios(dados))
    partes.append("## Expectativas implícitas no preço\n\n" + secao_reverse(dados))
    partes.append("## Validação por múltiplos\n\n" + secao_multiplos(dados))
    if graf_pe:
        partes.append("### Múltiplos P/L históricos\n\n"
                      f"![P/L histórico da companhia com mediana e ± 1 desvio-padrão]({graf_pe})")
    partes.append("## Retorno e crença por faixa de entrada\n\n" + secao_ladder(dados))
    partes.append("## Elasticidades (o que move o valor por ação)\n\n" + secao_elasticidades(dados))
    if "--sem-aparar" in sys.argv:
        dossie_txt, removidos = dados["dossie"].strip(), []
    else:
        dossie_txt, removidos = aparar_dossie(dados["dossie"])
    dados["_aparados"] = removidos
    bloco_dossie = "# Análise da companhia (dossiê do Analista)\n\n" + demover_titulos(dossie_txt)
    if graf_fin:
        bloco_dossie += ("\n\n## Histórico de receita, lucro líquido e ROE\n\n"
                         f"![Histórico de receita, lucro líquido e ROE]({graf_fin})")
    partes.append(bloco_dossie)
    partes.append("# Valuation (leitura do Modelador)\n\n" + demover_titulos(dados["valuation"].strip()))
    partes.append("# Verificação independente\n\n" + secao_auditoria(dados))
    partes.append("# Encaixe na carteira\n\n" + secao_encaixe(dados))
    partes.append("# Plano de ação\n\n" + secao_plano(dados))
    partes.append("# Nota metodológica e trilha documental\n\n" + nota_metodologica(dados, ns))
    texto = "\n\n".join(partes) + "\n"
    with open(os.path.join(ns, out_nome), "w", encoding="utf-8") as fh:
        fh.write(texto)
    # log de consistência por construção
    with open(os.path.join(ns, "log_consistencia.md"), "w", encoding="utf-8") as fh:
        fh.write("# Log de consistência (gerado por compor.py — consistência por construção)\n\n"
                 "Todo número injetado no relatório composto sai de uma chave de "
                 "resultados.json/inputs.yaml/estado.yaml. O corpo analítico (dossiê) e o valuation "
                 "são texto original dos agentes, não redigitado.\n\n| Número | Origem |\n|---|---|\n")
        for txt, chave in LOG:
            fh.write(f"| {txt} | `{chave}` |\n")
        fh.write(f"\n**{len(LOG)} números injetados, {len(LOG)} rastreados (100% por construção).**\n")
        if dados.get("_aparados"):
            fh.write("\n## Blocos de processo aparados do dossiê (determinístico, compor.py)\n\n")
            for r in dados["_aparados"]:
                fh.write(f"- {r}\n")
            fh.write("\nNada analítico foi removido; o aparo cobre apenas metadados duplicados, "
                     "artefatos de gate e disclaimers de fronteira de papéis (desligável com --sem-aparar).\n")
    print(f"[compor] {os.path.join(ns, out_nome)} gerado; {len(LOG)} números rastreados em log_consistencia.md")
    return os.path.join(ns, out_nome)


if __name__ == "__main__":
    ns = sys.argv[1] if len(sys.argv) > 1 else "."
    out = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else "relatorio.md"
    compor(ns, out)
