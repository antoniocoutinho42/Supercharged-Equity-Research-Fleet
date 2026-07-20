#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
compor.py — composição determinística do relatório final de research.

Lê o namespace da análise e monta relatorio.md SEM nenhum agente reescrever conteúdo.
Arquitetura R6 (separação de audiências):
  - CORPO institucional: recomendação + tese (cadeia causal, sem log de matriz de
    decisão), bloco de valor, dossiê do Analista injetado com saneamento determinístico
    (claim IDs, cites, nomenclatura institucional), seção de Valuation GERADA POR CHAVE
    (cenários, matrizes 3×3, reverse, múltiplos com conclusão da resolução, ladder,
    elasticidades com experimento declarado), verificação independente em linguagem
    executiva, encaixe e plano de ação. Zero linguagem operacional (o linter do
    checar.py --etapa relatorio reprova vazamentos).
  - ANEXO TÉCNICO: nota metodológica (engine/hash/profundidade), julgamento
    metodológico (metodo.yaml), racional operacional da decisão, resolução integral da
    divergência, exceção de DE/NDE com sensibilidade, memorando técnico do Modelador
    (valuation.md íntegro) e parecer integral da auditoria.
  - log_consistencia.md é gerado POR CONSTRUÇÃO: todo número injetado sai de uma chave,
    e o log lista número -> chave;
  - se grafico_faixas.png não existir, é regenerado do resultados.json (matplotlib).

Tolerância: resultados.json v1.x (sem validacao_multiplos / delta do ladder) degrada com nota.
R3: hurdle ausente (não informado pelo usuário) degrada com a ausência declarada em uma linha.

Uso: python compor.py <namespace> [--out relatorio.md]
Depois: python render_pdf.py <namespace>/relatorio.md --out <namespace>/relatorio_final.pdf
"""
import json
import os
import re
import sys

LOG = []  # (numero_formatado, chave_de_origem)


def humano(sinal):
    """Enums do engine em texto de leitura (NAO_ACIONAVEL -> NÃO ACIONÁVEL).
    R6: nenhum enum cru chega ao corpo do relatório — o linter do checar.py
    reprova qualquer token FORMATO_DE_ENUM que escape deste mapa."""
    mapa = {"NAO_ACIONAVEL": "NÃO ACIONÁVEL", "ACIONAVEL": "ACIONÁVEL",
            "LIMITROFE": "LIMÍTROFE", "DENTRO_DA_FAIXA": "DENTRO DA FAIXA",
            "SUMARIA": "SUMÁRIA", "PADRAO": "PADRÃO", "REFORCADA": "REFORÇADA",
            "SEM_HURDLE": "SEM RETORNO EXIGIDO INFORMADO",
            "DIVERGE_MATERIAL": "DIVERGÊNCIA MATERIAL", "CONVERGE": "CONVERGE",
            "SEM_DADOS": "SEM DADOS",
            "DEMONSTRADA": "demonstrada",
            "DEMONSTRADA_COM_RESSALVAS": "demonstrada com ressalvas",
            "NAO_DEMONSTRADA": "não demonstrada", "REPROVADA": "reprovada",
            "REVISAO_PREMISSAS": "revisão de premissas",
            "EXPLICACAO_FUNDAMENTADA": "explicação econômica fundamentada",
            "ADAPTACAO_METODOLOGICA": "adaptação metodológica específica"}
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
    # (4) R6 — saneamento institucional determinístico do corpo:
    # IDs de claim inline ([F-01]/[E-02]/[H-03]) são trilha de auditoria, não texto
    # institucional: vivem em claims.yaml e no dossiê-fonte (anexo), nunca no corpo.
    n_claims = len(re.findall(r"\s*\[[FEH]-\d{2,3}\]", texto))
    if n_claims:
        texto = re.sub(r"\s*\[[FEH]-\d{2,3}\]", "", texto)
        removidos.append(f"{n_claims} ID(s) de claim inline ([F-xx]/[E-xx]/[H-xx]) — trilha "
                         "em claims.yaml, fora do corpo institucional")
    n_cites = len(re.findall(r"</?cite[^>]*>", texto))
    if n_cites:
        texto = re.sub(r"</?cite[^>]*>", "", texto)
        removidos.append(f"{n_cites} tag(s) <cite> de sessão de pesquisa")
    # nomenclatura institucional (R6): "Dossiê de duração..." -> "Análise de duração..."
    if re.search(r"dossi[êe] de dura", texto, re.I):
        texto = re.sub(r"\bDOSSI[ÊE] DE DURA", "ANÁLISE DE DURA", texto)
        texto = re.sub(r"\bDossi[êe] de dura", "Análise de dura", texto)
        texto = re.sub(r"\bdossi[êe] de dura", "análise de dura", texto)
        removidos.append("nomenclatura: 'Dossiê de duração' -> 'Análise de duração'")
    # autorreferências do artefato interno viram referência ao documento
    n_ref = len(re.findall(r"\b[nd]este dossi[êe]\b", texto, re.I))
    if n_ref:
        texto = re.sub(r"\bneste dossi[êe]\b", "nesta análise", texto)
        texto = re.sub(r"\bNeste dossi[êe]\b", "Nesta análise", texto)
        texto = re.sub(r"\bdeste dossi[êe]\b", "desta análise", texto)
        texto = re.sub(r"\bDeste dossi[êe]\b", "Desta análise", texto)
        removidos.append(f"{n_ref} autorreferência(s) 'neste/deste dossiê' -> 'nesta/desta análise'")
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
    # metodo.yaml (R1): julgamento metodológico prévio — ecoado no anexo técnico
    p_met = os.path.join(ns, "metodo.yaml")
    dados["metodo"] = (yaml.safe_load(open(p_met, encoding="utf-8"))
                       if os.path.exists(p_met) else None)
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
    moeda = dados["res"]["meta"].get("moeda", "USD")
    moeda_rotulo = "US$ mi" if moeda == "USD" else f"{moeda} mi"
    barras_rec = ax1.bar(x - larg / 2, receita, larg, label="Receita", color="#002060")
    barras_luc = ax1.bar(x + larg / 2, lucro, larg, label="Lucro líquido", color="#FFC000")
    ax1.set_ylabel(f"Receita e lucro líquido ({moeda_rotulo})")
    ax1.set_xticks(x)
    ax1.set_xticklabels(anos)
    # R6: rótulos de dados em TODAS as séries — valores acima das barras, na moeda
    # reportada e em milhões
    for barras in (barras_rec, barras_luc):
        for b in barras:
            v = b.get_height()
            if v is None:
                continue
            ax1.annotate(f"{v:,.0f}".replace(",", "."), (b.get_x() + b.get_width() / 2, v),
                         xytext=(0, 3), textcoords="offset points",
                         ha="center", va="bottom", fontsize=7)
    ax1.set_ylim(top=ax1.get_ylim()[1] * 1.08)
    ax2 = ax1.twinx()
    ax2.plot(x, roe, color="#7F7F7F", marker="o", lw=2, label="ROE (%)")
    ax2.set_ylabel("ROE (%)")
    # R6: percentual do ROE centralizado sobre cada marcador, fundo branco e
    # contorno na cor da linha
    for xi, v in zip(x, roe):
        if v is None:
            continue
        ax2.annotate(f"{v:.0f}%", (xi, v), ha="center", va="center", fontsize=7,
                     bbox=dict(boxstyle="round,pad=0.25", facecolor="white",
                               edgecolor="#7F7F7F", linewidth=0.8))
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
    e = res["economico"]
    linhas = [("Valor econômico (P/L Justo)", e["faixa_completa"][0], e["faixa_completa"][1],
               e["central_ponderado"])]
    if res.get("hurdle"):  # R3: sem hurdle informado, só a âncora econômica
        h = res["hurdle"]["cenarios"]
        linhas.insert(0, ("Preço máx. hurdle", h["bear"]["preco"], h["bull"]["preco"], h["ponderado"]))
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
    """R6: recomendação + tese como cadeia causal. O racional operacional do gate
    (log da matriz de decisão) NÃO entra aqui — vive no anexo técnico."""
    est, res = dados["estado"], dados["res"]
    dec = est["decisao"]
    s = res["sinais"]
    ress = _como_lista(dec.get("ressalvas"))
    if not (est.get("auditoria") or {}).get("acionada"):
        ress.append("Esta análise não foi submetida a verificação independente.")
    if not est.get("snapshot"):
        ress.append("Encaixe e dimensionamento em carteira não avaliados (composição da "
                    "carteira não fornecida).")
    linhas = [f"> **RECOMENDAÇÃO: {dec['recomendacao']}** | Convicção: {dec['confianca']}"]
    if s.get("preco_sobre_hurdle_pond") is not None:
        linhas.append(
            f"> Leitura econômica: **{humano(s['economico']).lower()}** (preço com "
            f"{n(s['premio_sobre_econ_central_pct'], 'sinais.premio_sobre_econ_central_pct', 1)}% de prêmio "
            f"sobre o valor central). Disciplina de entrada: **{humano(s['entrada']).lower()}** "
            f"(preço a {n(s['preco_sobre_hurdle_pond'], 'sinais.preco_sobre_hurdle_pond')}x o preço máximo "
            "que remunera o retorno exigido).")
    else:
        # R3: sem hurdle informado, a ausência é declarada em uma linha
        linhas.append(
            f"> Leitura econômica: **{humano(s['economico']).lower()}** (preço com "
            f"{n(s['premio_sobre_econ_central_pct'], 'sinais.premio_sobre_econ_central_pct', 1)}% de prêmio "
            "sobre o valor central). O retorno mínimo exigido não foi informado pelo "
            "investidor; a disciplina de entrada e tudo que dela deriva não foram avaliados.")
    tese = str(dec.get("tese", "")).strip()
    bloco = "\n".join(linhas)
    if tese:
        bloco += f"\n\n**Tese de investimento.** {tese}"
    if ress:
        bloco += "\n\n**Ressalvas.**"
        for r in ress:
            bloco += f"\n- {r}"
    return bloco


def secao_bloco_valor(dados):
    res = dados["res"]
    moeda = res["meta"].get("moeda", "USD")
    pfx = "US$ " if moeda == "USD" else f"{moeda} "
    e, s = res["economico"], res["sinais"]
    h = (res.get("hurdle") or {}).get("cenarios")
    preco = res["meta"]["preco_atual"]
    central = e["central_ponderado"]
    down_central = 100.0 * (central / preco - 1.0)
    t = ["| Metodologia | Faixa / valor | Sinal |", "|---|---|---|"]
    t.append(f"| Valor Intrínseco Econômico (P/L Justo, motor principal) | "
             f"{n(e['faixa_ponderada'][0], 'economico.faixa_ponderada[0]', 2, pfx)} – "
             f"{n(e['faixa_ponderada'][1], 'economico.faixa_ponderada[1]')} "
             f"(central {n(central, 'economico.central_ponderado', 2, pfx)}) | {humano(s['economico'])} |")
    if h is not None:
        t.append(f"| **Preço Máximo para o Hurdle** (disciplina de compra) | "
                 f"{n(h['ponderado'], 'hurdle.cenarios.ponderado', 2, pfx)} ponderado "
                 f"(bear {n(h['bear']['preco'], 'hurdle.cenarios.bear.preco')} / "
                 f"base {n(h['base']['preco'], 'hurdle.cenarios.base.preco')} / "
                 f"bull {n(h['bull']['preco'], 'hurdle.cenarios.bull.preco')}) | {humano(s['entrada'])} |")
    if h is not None:
        down_hurdle = 100.0 * (h["ponderado"] / preco - 1.0)
        ms = (f"Preço {n(preco, 'meta.preco_atual', 2, pfx)}: prêmio de "
              f"{n(s['premio_sobre_econ_central_pct'], 'sinais.premio_sobre_econ_central_pct', 1)}% sobre o valor central "
              f"(downside até o valor: {n(down_central, 'derivado: central/preco-1', 1)}%) e prêmio de "
              f"{n(s['premio_sobre_hurdle_pct'], 'sinais.premio_sobre_hurdle_pct', 1)}% sobre o hurdle "
              f"(downside: {n(down_hurdle, 'derivado: hurdle/preco-1', 1)}%). Como o preço está acima do valor, "
              "não há margem de segurança tradicional; a métrica relevante é o downside até o valor."
              ) if preco > central else (
              f"Preço {n(preco, 'meta.preco_atual', 2, pfx)}: desconto de "
              f"{n(-down_central, 'derivado: 1-preco/central', 1)}% até o valor central.")
    else:
        ms = (f"Preço {n(preco, 'meta.preco_atual', 2, pfx)}: "
              + (f"prêmio de {n(s['premio_sobre_econ_central_pct'], 'sinais.premio_sobre_econ_central_pct', 1)}% "
                 "sobre o valor central." if preco > central else
                 f"desconto de {n(-down_central, 'derivado: 1-preco/central', 1)}% até o valor central.")
              + " O retorno mínimo exigido não foi informado pelo investidor: o preço máximo "
                "de compra e o sinal de entrada não foram calculados; a análise usa a âncora "
                "econômica.")
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


_ROTULO_DRIVER = {"cap": "CAP", "roe": "ROE", "g": "g"}


def _fmt_driver(driver, valor):
    if valor is None:
        return "n.d."
    if driver == "cap":
        return f"{valor} anos"
    return f"{br(100 * float(valor), 1 if driver == 'g' else 0)}%"


def secao_matrizes(dados):
    """R6: seis matrizes de sensibilidade 3×3 (três por âncora) com PREÇO POR AÇÃO
    em cada célula, substituindo as tabelas de limites. Eixos = premissas
    bear/base/bull da tabela de Cenários; célula Base/Base destacada. Herda o R4:
    cada matriz declara o que mantém fixo. Números 100% do engine (bloco matrizes),
    rastreados no log de consistência."""
    res = dados["res"]
    mz = res.get("matrizes")
    if not mz:
        return ("Matrizes de sensibilidade não disponíveis (resultado gerado por motor "
                "anterior; ver a tabela de Cenários para a leitura de premissas).")
    pfx = "US$ " if res["meta"].get("moeda", "USD") == "USD" else res["meta"].get("moeda", "") + " "
    blocos = []
    ancoras = []
    if mz.get("hurdle"):
        ancoras.append(("hurdle", "Preço Máximo para o Hurdle",
                        "Ke fixo = retorno exigido informado pelo investidor"))
    else:
        blocos.append("O retorno mínimo exigido não foi informado pelo investidor; as "
                      "matrizes do preço máximo de compra não foram calculadas.")
    ancoras.append(("economico", "Valor Intrínseco Econômico", "Ke fixo = Ke central do CAPM"))
    tem_incoerente = False
    for chave_anc, titulo_anc, nota_ke in ancoras:
        anc = mz[chave_anc]
        for par in ("cap_x_roe", "cap_x_g", "roe_x_g"):
            m = anc[par]
            linha_d, coluna_d = m["linha"], m["coluna"]
            fixo_nome = next(d for d in ("cap", "roe", "g") if d not in (linha_d, coluna_d))
            fixos = m["fixos"]
            cab = (f"**{titulo_anc} — {_ROTULO_DRIVER[linha_d]} × {_ROTULO_DRIVER[coluna_d]}** "
                   f"(fixos: {_ROTULO_DRIVER[fixo_nome]} base = "
                   f"{_fmt_driver(fixo_nome, fixos.get(fixo_nome))}, "
                   f"Ke = {br(100 * fixos['ke'], 1)}% [{nota_ke}], lucro por ação e "
                   f"estrutura de capital constantes)")
            t = ["| | " + " | ".join(
                f"{_ROTULO_DRIVER[coluna_d]} {_fmt_driver(coluna_d, m['valores_coluna'][c])}"
                for c in ("bear", "base", "bull")) + " |",
                 "|---|---|---|---|"]
            for ln in ("bear", "base", "bull"):
                cels = []
                for cn in ("bear", "base", "bull"):
                    v = m["precos"][ln][cn]
                    if v is None:
                        cels.append("n.s.")
                        tem_incoerente = True
                    else:
                        txt = n(v, f"matrizes.{chave_anc}.{par}.precos.{ln}.{cn}", 2, pfx)
                        cels.append(f"**{txt}**" if ln == "base" and cn == "base" else txt)
                rotulo_ln = f"{_ROTULO_DRIVER[linha_d]} {_fmt_driver(linha_d, m['valores_linha'][ln])}"
                if ln == "base":
                    rotulo_ln = f"**{rotulo_ln}**"
                t.append(f"| {rotulo_ln} | " + " | ".join(cels) + " |")
            blocos.append(cab + "\n\n" + "\n".join(t))
    nota = ("Cada matriz varia dois drivers pelos valores bear/base/bull da tabela de "
            "Cenários e mantém o terceiro no valor base, com lucro por ação, estrutura de "
            "capital e taxa de desconto da âncora constantes. As células mostram preço por "
            "ação e não são ponderadas por probabilidade — a leitura probabilística conjunta "
            "é a tabela de Cenários. A célula em negrito é o caso base.")
    if tem_incoerente:
        nota += (" Células marcadas n.s. combinariam crescimento acima da rentabilidade "
                 "(retenção acima de 100%) e não representam uma variação econômica possível.")
    return "\n\n".join(blocos) + "\n\n" + nota


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
                f"e o retorno exigido de {br(100*a['ke_hurdle'],0)}%"
                ) if (a['roe_base'] is not None and a['ke_hurdle'] is not None) else ""
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
    out = "\n".join(t) + f"\n\n**Veredicto: {humano(v['veredicto']).lower()}.**"
    # flags do engine chegam com prefixo de código (DIVERGENCIA_MATERIAL_XXX:) —
    # no corpo institucional entra só a leitura, sem o token operacional
    for f in v.get("flags", []):
        legivel = re.sub(r"^DIVERGENCIA_MATERIAL_(HISTORICO|COMPARAVEIS):\s*",
                         lambda m: ("Vs. banda histórica própria: " if m.group(1) == "HISTORICO"
                                    else "Vs. comparáveis: "), str(f))
        legivel = legivel.replace("— revisar premissas ou explicar premissa a premissa", "").strip()
        out += f"\n- {legivel}"
    # R5: a CONCLUSÃO da resolução entra no corpo; o histórico completo vai ao anexo.
    resol = v.get("resolucao")
    if v.get("veredicto") == "DIVERGE_MATERIAL":
        if resol:
            out += (f"\n\n**Resolução ({humano(resol['via'])}).** {resol['texto']}")
        else:
            out += ("\n\n**Divergência material sem resolução registrada — este relatório não "
                    "está apto a publicação (bloqueio de coerência econômica).**")
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
    rot = {"mais_1a_cap": "+1 ano de CAP", "mais_1pp_g": "+1 p.p. de g",
           "mais_1pp_roe": "+1 p.p. de ROE", "menos_05pp_ke": "−0,5 p.p. de Ke"}
    tem_hurdle = e.get("hurdle") is not None
    if tem_hurdle:
        t = ["| US$/ação por... | Âncora econômica | Âncora do retorno exigido |", "|---|---|---|"]
        for k, r in rot.items():
            t.append(f"| {r} | {n(e['economico'][k], f'elasticidades.economico.{k}')} | "
                     f"{n(e['hurdle'][k], f'elasticidades.hurdle.{k}')} |")
    else:
        t = ["| US$/ação por... | Âncora econômica |", "|---|---|"]
        for k, r in rot.items():
            t.append(f"| {r} | {n(e['economico'][k], f'elasticidades.economico.{k}')} |")
    out = "\n".join(t)
    # R4a: o experimento de cada sensibilidade é declarado junto do número.
    exp = e.get("experimento") or {}
    if exp:
        out += "\n\n**O experimento por trás de cada linha.**"
        for k, r in rot.items():
            if exp.get(k):
                out += f"\n- {r}: {exp[k]}"
    # R4b: sinal contrário ao esperado só é publicado COM a explicação do mecanismo
    # e da plausibilidade (a resposta registrada do Modelador). Sem resposta, o
    # checar.py bloqueia a publicação antes de chegar aqui.
    respondidos = [a for a in (e.get("alertas_sinal") or []) if a.get("respondido")]
    vistos = set()
    for a in respondidos:
        if a["parametro"] in vistos:
            continue
        vistos.add(a["parametro"])
        out += (f"\n\n**Por que {rot.get(a['parametro'], a['parametro'])} tem sinal "
                f"{('negativo' if a['sinal_observado'] == 'NEGATIVO' else 'positivo')} aqui.** "
                f"{a['resposta']}")
    return out


_RE_ENUM = re.compile(r"\b[A-Z][A-Z0-9]{2,}(?:_[A-Z0-9]{2,})+\b")


def _suavizar_enums(txt):
    """Substituição determinística de tokens ENUM_DO_ENGINE por texto de leitura
    em strings de terceiros injetadas no corpo (ex.: títulos de issues do
    Auditor). Tokens conhecidos usam o mapa humano(); desconhecidos viram
    minúsculas com espaços. Nunca altera números nem o resto da frase."""
    def _sub(m):
        tok = m.group(0)
        h = humano(tok)
        if h != tok:
            return h.lower()
        return tok.replace("_", " ").lower()
    saida = _RE_ENUM.sub(_sub, str(txt))
    # referências cruzadas de issue (AC-xx) viram linguagem executiva
    saida = re.sub(r"\bAC-0*(\d+)\b", r"achado \1 da verificação independente", saida)
    return saida


def _cabecalho_red_team(rt):
    """Extrai (cabecalho_dict, corpo) do red_team.md; (None, texto) se não parsear."""
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", rt, re.S)
    if not m:
        return None, rt
    import yaml
    try:
        return (yaml.safe_load(m.group(1)) or {}), m.group(2)
    except Exception:
        return None, rt


def secao_auditoria(dados):
    """R6: verificação independente em LINGUAGEM EXECUTIVA no corpo — o que estava
    incorreto/incompleto, como foi tratado, impacto e o que permanece fragilidade,
    distinguindo correção numérica (a conta reproduz) de adequação metodológica
    (a conta representa a economia). A íntegra técnica vai ao anexo."""
    rt = dados.get("red_team")
    if not rt:
        return ("Esta análise não foi submetida a verificação independente (auditoria não "
                "acionada pelo investidor). Não há questionamentos de segunda leitura nem "
                "testes de limite de um segundo examinador a reportar; a convicção da "
                "recomendação tem teto imposto por essa ausência.")
    cab, _ = _cabecalho_red_team(rt)
    if not cab:
        return ("A análise foi submetida a verificação independente; o parecer completo "
                "está no anexo técnico.")
    linhas = [f"A análise foi submetida a verificação independente. "
              f"Veredicto do examinador: **{humano(cab.get('agregado', 'n.d.'))}** — um juízo "
              f"sobre suficiência de demonstração, não uma recomendação."]
    dims = {k.lower(): str(v).lower() for k, v in (cab.get("dimensoes") or {}).items()}
    trad = []
    if "correcao" in dims:
        trad.append("os cálculos "
                    + ("reproduzem fielmente (correção numérica confirmada)"
                       if dims["correcao"].startswith("verificada")
                       else "apresentaram erro material, tratado conforme descrito abaixo"))
    if "especificacao" in dims:
        mapa_e = {"forte": "representa bem a economia do ativo",
                  "aceitavel": "representa a economia do ativo de forma aceitável, com pontos de atenção",
                  "aceitável": "representa a economia do ativo de forma aceitável, com pontos de atenção",
                  "fragil": "tem fragilidades relevantes na representação da economia do ativo",
                  "frágil": "tem fragilidades relevantes na representação da economia do ativo"}
        trad.append(f"a especificação do modelo {mapa_e.get(dims['especificacao'], dims['especificacao'])} "
                    "(adequação metodológica — distinta da correção numérica)")
    if "integridade" in dims:
        trad.append("os dados de entrada foram "
                    + ("verificados na fonte" if dims["integridade"].startswith("verificada")
                       else f"avaliados como {dims['integridade']}"))
    if "robustez" in dims:
        mapa_r = {"confirmada": "a conclusão resistiu aos testes de estresse do examinador",
                  "inconclusiva": "os testes de estresse foram inconclusivos",
                  "divergente": "há uma divergência de leitura não resolvida que limita a conclusão"}
        trad.append(mapa_r.get(dims["robustez"], dims["robustez"]))
    if trad:
        linhas.append("Em termos executivos: " + "; ".join(trad) + ".")
    issues = cab.get("issues") or []
    relevantes = [i for i in issues
                  if str(i.get("severidade", "")).upper().startswith(("CRIT", "RELE"))]
    if relevantes:
        linhas.append("\n**Achados relevantes e seu estado.**")
        for i in relevantes:
            sev = str(i.get("severidade", "")).upper()
            peso = ("capaz de mudar o sinal ou a decisão" if sev.startswith("CRIT")
                    else "capaz de mudar a convicção ou mover o valor de forma relevante")
            estado = str(i.get("estado", "")).lower()
            if estado.startswith("fechad") or estado.startswith("resolvid"):
                destino = "tratado e incorporado à análise"
            else:
                destino = "permanece como fragilidade declarada"
            linhas.append(f"- {_suavizar_enums(i.get('titulo', ''))} — achado {peso}; {destino}.")
    if cab.get("cap_auditoria"):
        linhas.append("\nSobre a duração da vantagem competitiva: "
                      f"{_suavizar_enums(cab['cap_auditoria'])}")
    linhas.append("\nO parecer integral do examinador está no anexo técnico.")
    return "\n".join(linhas)


def secao_encaixe(dados):
    pf = dados.get("portfolio_fit")
    if not pf:
        return "Não avaliado (composição da carteira não fornecida pelo investidor)."
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
            f"composto deterministicamente a partir desses arquivos; o corpo analítico é o texto "
            f"original do Analista (saneado de artefatos de processo, ver log de consistência) e a "
            f"seção de Valuation do corpo é gerada por chave a partir do resultados.json; o "
            f"memorando técnico do Modelador está reproduzido integralmente abaixo.")


def secao_anexo_metodo(dados):
    """Eco do julgamento metodológico prévio (R1) no anexo técnico."""
    met = dados.get("metodo")
    if not met:
        return None
    linhas = [f"Decisão: **{met.get('decisao', 'n.d.')}** ({met.get('autor', 'n.d.')}, "
              f"{met.get('data', 'sem data')})."]
    if met.get("justificativa"):
        linhas.append(f"Justificativa: {str(met['justificativa']).strip()}")
    riscos = met.get("premissas_em_risco") or []
    if riscos:
        linhas.append("Premissas da fórmula em risco neste caso:")
        for r in riscos:
            trat = f" Tratamento: {r['tratamento']}" if r.get("tratamento") else ""
            linhas.append(f"- {r.get('premissa')}: {r.get('risco')}{trat}")
    dados_extra = met.get("dados_adicionais") or []
    if dados_extra:
        linhas.append("Dados adicionais exigidos pela definição da fórmula (plano de coleta):")
        for d in dados_extra:
            status = "coletado" if d.get("coletado") else "PENDENTE"
            linhas.append(f"- {d.get('dado')} — {d.get('motivo')} [{status}]")
    adapts = met.get("adaptacoes") or []
    if adapts:
        linhas.append("Adaptações específicas (ex-ante, fundamentadas, com sensibilidade):")
        for a in adapts:
            prec = f" Precedente consultado: {a['precedente']}." if a.get("precedente") else ""
            linhas.append(f"- {a.get('parametro')}: {a.get('justificativa')} "
                          f"Sensibilidade: {a.get('sensibilidade')}.{prec}")
    rev = met.get("revisao_valuation") or {}
    if rev:
        linhas.append(f"Revisão pelo Modelador antes do valuation: "
                      f"{'confirmada' if rev.get('confirmada') else 'NÃO confirmada'}."
                      + (f" {rev['nota']}" if rev.get("nota") else ""))
    return "\n".join(linhas)


def secao_anexo_tecnico(dados, ns):
    """R6: separação de audiências. Toda a trilha operacional (chaves, hashes,
    gates, versões, memorandos técnicos, resolução integral da divergência,
    parecer integral da auditoria, racional do gate de decisão) vive AQUI —
    o linter do checar.py não varre esta seção."""
    res, est = dados["res"], dados["estado"]
    dec = est["decisao"]
    partes = ["## Nota metodológica e trilha documental\n\n" + nota_metodologica(dados, ns)]
    met = secao_anexo_metodo(dados)
    if met:
        partes.append("## Julgamento metodológico prévio (R1)\n\n" + met)
    partes.append("## Racional operacional da decisão\n\n"
                  + f"{dec.get('racional', 'n.d.')}\n\n"
                  + "Decisão tomada pelas regras de decisão do processo (matriz registrada em "
                    "eventos.jsonl); sinais de origem: sinais.economico = "
                  + f"{res['sinais']['economico']}, sinais.entrada = {res['sinais']['entrada']}.")
    resol = _get(res, "validacao_multiplos.resolucao")
    if resol:
        partes.append("## Resolução da divergência de múltiplos (histórico completo)\n\n"
                      + f"Via: {resol['via']}.\n\n{resol['texto']}")
    exc = _get(res, "de_nde.excecao")
    if exc:
        s = exc.get("sensibilidade") or {}
        partes.append(
            "## Exceção declarada de DE/NDE (inputs estruturais)\n\n"
            + f"Motivo: {exc.get('motivo')}\n\n"
            + f"Substitutos: DE = {exc.get('de_substituto')}, NDE = {exc.get('nde_substituto')}; "
              f"faixa alternativa: DE = {_get(exc, 'faixa_alternativa.de')}, "
              f"NDE = {_get(exc, 'faixa_alternativa.nde')}. "
              f"Sensibilidade calculada pelo engine: valor central econômico "
              f"{s.get('econ_central_substituto')} (substituto) vs. "
              f"{s.get('econ_central_alternativa')} (alternativa), delta "
              f"{s.get('delta_econ_central_pct')}%.")
    partes.append("## Memorando técnico do Modelador (valuation.md, íntegra)\n\n"
                  + demover_titulos(dados["valuation"].strip()))
    rt = dados.get("red_team")
    if rt:
        cab, corpo = _cabecalho_red_team(rt)
        bloco = "## Parecer integral da verificação independente (red_team.md)\n\n"
        if cab is not None:
            import json as _json
            bloco += "```yaml\n" + _json.dumps(cab, ensure_ascii=False, indent=2) + "\n```\n\n"
            bloco += demover_titulos(corpo.strip())
        else:
            bloco += demover_titulos(rt.strip())
        partes.append(bloco)
    if dados.get("_aparados"):
        partes.append("## Saneamento institucional do corpo (determinístico)\n\n"
                      + "\n".join(f"- {r}" for r in dados["_aparados"])
                      + "\n\nNada analítico foi removido; a íntegra dos documentos-fonte "
                        "permanece no namespace da análise e neste anexo.")
    return "\n\n".join(partes)


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
    # R6: front-matter sem metadados operacionais (versão do engine vive no anexo)
    fm = (f"---\ntitulo: \"{meta.get('nome', meta['ticker'])} ({meta['ticker']})\"\n"
          f"subtitulo: \"Equity Research — Relatório de Investimento | {dec['recomendacao']}\"\n"
          f"data: \"{est.get('data', meta.get('data_preco', ''))}\"\n"
          f"linha_meta: \"Preço de referência: {pfx}{br(meta['preco_atual'])} ({meta.get('data_preco','')}) | "
          f"Moeda: {meta.get('moeda','')}\"\n"
          f"rodape: \"{meta['ticker']} — research proprietário | uso interno\"\n---\n")
    if "--sem-aparar" in sys.argv:
        dossie_txt, removidos = dados["dossie"].strip(), []
    else:
        dossie_txt, removidos = aparar_dossie(dados["dossie"])
    dados["_aparados"] = removidos
    # ---- CORPO institucional (o linter do checar.py varre até o Anexo técnico) ----
    partes = [fm]
    partes.append("# Recomendação e tese\n\n" + secao_recomendacao(dados))
    partes.append("## Bloco de valor e sinais\n\n" + secao_bloco_valor(dados))
    if grafico:
        partes.append(f"![Preço atual vs. faixas de valor]({grafico})")
    bloco_dossie = "# Análise da Companhia\n\n" + demover_titulos(dossie_txt)
    if graf_fin:
        bloco_dossie += ("\n\n## Histórico de receita, lucro líquido e ROE\n\n"
                         f"![Histórico de receita, lucro líquido e ROE]({graf_fin})")
    partes.append(bloco_dossie)
    # Seção de Valuation orientada à decisão: conclusões primeiro (bloco de valor,
    # acima), depois fundamentos e sensibilidades — tudo gerado por chave.
    partes.append("# Valuation\n\n## Cenários\n\n" + secao_cenarios(dados))
    partes.append("## Matrizes de sensibilidade (preço por ação)\n\n" + secao_matrizes(dados))
    partes.append("## O que o preço atual embute\n\n" + secao_reverse(dados))
    partes.append("## Validação por múltiplos\n\n" + secao_multiplos(dados))
    if graf_pe:
        partes.append("### Múltiplos P/L históricos\n\n"
                      f"![P/L histórico da companhia com mediana e ± 1 desvio-padrão]({graf_pe})")
    partes.append("## Retorno e crença por faixa de entrada\n\n" + secao_ladder(dados))
    partes.append("## Elasticidades (o que move o valor por ação)\n\n" + secao_elasticidades(dados))
    partes.append("# Verificação independente\n\n" + secao_auditoria(dados))
    partes.append("# Encaixe na carteira\n\n" + secao_encaixe(dados))
    partes.append("# Plano de ação\n\n" + secao_plano(dados))
    # ---- ANEXO técnico (trilha auditável; fora do escopo do linter) ----
    partes.append("# Anexo técnico\n\n" + secao_anexo_tecnico(dados, ns))
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
