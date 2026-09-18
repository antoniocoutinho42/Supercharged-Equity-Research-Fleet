#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Múltiplos Justos — motor de cálculo.
Soma explícita dos fluxos (sem singularidades de fórmula fechada).
Auto-validado contra os anchors da planilha "Justified Multiples Model" do usuário.
Taxas de entrada em % (ex.: --g 5 = 5%). Uso: ver SKILL.md.
"""
import argparse, sys, json

# ---------------- convenções de valor terminal ----------------
# 'book'         (ex-'ic'):     renda residual truncada em n. O NOPAT INTEIRO colapsa de
#                               ROIC×IC para W×IC no ano n+1; TV = capital investido IC_n.
#                               [v9.28] Com book separado, IC_0 = NOPAT_1/ROIC_book e TODO
#                               capital novo do explícito acumula ao ROIC marginal; portanto
#                               IC_n NÃO é NOPAT_{n+1}/ROIC_book salvo nos casos de colapso.
#                               Equivale a renda residual truncada com estoque de capital
#                               reconciliado à trajetória de reinvestimento.
# 'convergencia' (nova):        RONIC = W no capital NOVO, NOPAT existente preservado —
#                               TV = NOPAT_{n+1}/W. Exaustão da vantagem NO CAPITAL INCREMENTAL
#                               (McKinsey/Mauboussin); rendas do estoque preservadas. Invariante a gp.
# 'gordon'       (ex-'spread'): Gordon com ROIC_TV e gp livres; ROIC_TV = RONIC/ROIIC TERMINAL
#                               (marginal do capital novo que sustenta gp). Três regimes legítimos:
#                               ROIC_TV > W (excess returns persistentes), = W (equivale à
#                               'convergencia'), < W (destruição persistente declarada).
TV_CANON = {'ic': 'book', 'spread': 'gordon', 'book': 'book',
            'gordon': 'gordon', 'convergencia': 'convergencia'}
def tv_canon(tv):
    return TV_CANON.get(tv, tv)

# ---------------- núcleo ----------------
def ev_nopat_partes(g, roic, w, n, tv='book', roic_tv=None, gp=0.0, roic_book=None, mid_year=False):
    """[v10.1] Mesmo núcleo de `ev_nopat`, devolvendo as PARTES em vez da soma:
    {'explicito', 'terminal', 'total'} em unidades de NOPAT corrente. `ev_nopat` chama esta
    função e soma — assim as duas NÃO podem divergir. Existe porque a entrega passou a exigir
    o peso do valor terminal e o valor dos ativos instalados, e a regra do pacote é não
    calcular nada à mão."""
    tv = tv_canon(tv)
    if g <= -1 or roic <= 0 or w <= -1 or n < 1:
        return {'explicito': float('nan'), 'terminal': float('nan'), 'total': float('nan')}
    ret = 1 - g / roic
    expl = sum(ret * (1 + g) ** t / (1 + w) ** t for t in range(1, n + 1))
    if tv == 'gordon':
        if roic_tv is None or roic_tv <= 0 or gp <= -1 or gp >= w:
            term = float('nan')
        else:
            term = (1 + g) ** (n + 1) * (1 - gp / roic_tv) / (w - gp) / (1 + w) ** n
    elif tv == 'convergencia':
        term = float('nan') if w <= 0 else (1 + g) ** (n + 1) / (w * (1 + w) ** n)
    else:
        rb = roic_book if roic_book is not None else roic
        if rb <= 0:
            term = float('nan')
        else:
            ic_n = (1 + g) * (1.0 / rb - 1.0 / roic) + (1 + g) ** (n + 1) / roic
            term = float('nan') if ic_n <= 0 else ic_n / (1 + w) ** n
    f = (1 + w) ** 0.5 if mid_year else 1.0
    expl *= f
    term = term * f if term == term else term
    return {'explicito': expl, 'terminal': term,
            'total': (expl + term) if term == term else float('nan')}


def decomposicao_mm(g, roic, w, n, tv='book', roic_tv=None, gp=0.0, roic_book=None, mid_year=False):
    """[v10.1] Decomposição de Miller-Modigliani (1961) em unidades de NOPAT corrente.

    ativos_instalados = valor SEM crescimento nenhum: g = 0 E sem crescimento terminal (gp = 0).
    Em `convergencia` e em `gordon` isso colapsa exatamente em 1/W (identidade, `derivacao.md` §2);
    na `book` com CAP finito NÃO colapsa — depende da âncora média, e é por isso que o número sai
    do motor em vez de sair de uma divisão à mão.
    Trava de leitura: só é 'ativos instalados' se `d` for encargo de reposição verdadeiro."""
    partes = ev_nopat_partes(g, roic, w, n, tv=tv, roic_tv=roic_tv, gp=gp,
                             roic_book=roic_book, mid_year=mid_year)
    ai = ev_nopat(0.0, roic, w, n, tv=tv, roic_tv=roic_tv, gp=0.0,
                  roic_book=roic_book, mid_year=mid_year)
    tot = partes['total']
    out = {'ativos_instalados_x_NOPAT': ai, 'valor_do_crescimento_x_NOPAT': tot - ai,
           'participacao_do_crescimento_%': (tot - ai) / tot * 100 if tot else float('nan'),
           'peso_do_terminal_%': partes['terminal'] / tot * 100 if tot else float('nan'),
           'identidade_ativos_instalados': ('exata: 1/W (convergencia/gordon com gp=0)'
                                            if tv_canon(tv) in ('convergencia', 'gordon')
                                            else 'NÃO é 1/W: a book com CAP finito depende da âncora média'),
           'trava_de_leitura': ('só é "ativos instalados" se o d for encargo de reposição VERDADEIRO — '
                                'com d subdimensionado o NOPAT está superestimado e o termo herda o erro')}
    return out


def ev_nopat(g, roic, w, n, tv='book', roic_tv=None, gp=0.0, roic_book=None, mid_year=False):
    """EV/NOPAT current. tv em {'book','convergencia','gordon'} (aliases 'ic'/'spread' aceitos).
    roic_book: ROIC MÉDIO INICIAL/FORWARD do estoque que ancora IC_0 na 'book'. [v9.28] O TV é o IC
    ACUMULADO: IC_0 = NOPAT_1/ROIC_médio e o capital novo entra ao MARGINAL (RiR = g/ROIC),
    de modo que o médio DERIVA na direção do marginal ao longo do explícito — coerente com os
    fluxos descontados (forma fechada no ramo book; contraprova por acumulação em testes.py).
    Sem roic_book, a 'book' usa o ROIC do explícito (marginal) como se fosse médio — conflação
    sinalizada no diagnóstico; o erro pode ser material quando marginal ≠ médio.
    mid_year (C3): convenção midpoint — desloca cada fluxo anual do fim para o meio do período;
    é aproximação de midpoint, não integração contínua de um fluxo uniforme. Multiplica por (1+W)^0.5. DEFAULT False (fim de ano), que é a
    convenção da planilha de referência; a maior parte do sell-side usa mid-year, então
    comparações de NÍVEL com múltiplos de terceiros exigem declarar qual das duas está em uso."""
    return ev_nopat_partes(g, roic, w, n, tv=tv, roic_tv=roic_tv, gp=gp,
                           roic_book=roic_book, mid_year=mid_year)['total']

def ev_ebitda(g, roic, w, n, d, t, **kw):
    return ev_nopat(g, roic, w, n, **kw) * (1 - d) * (1 - t)

def rampa_bifasica(receita0, ebitda0, da_parque, wk, w, tax, n, t_rampa, g2, kappa,
                   g1=None, util=None, tv='convergencia', roic_tv=None, gp=0.0, roic_book=None):
    """[v9.24] Composição bifásica do §8f: fase 1 = rampa de capacidade PRÉ-CONSTRUÍDA
    (crescimento consome SÓ giro; D&A do parque FIXA em moeda; capex de manutenção = D&A),
    fase 2 = expansão de capacidade nova (bloco padrão, custo pleno giro + capex fixo),
    costurada como valor terminal da fase 1 e avaliada DE TRÁS PARA FRENTE.
    Forma fechada da rampa (provada em planilha — proveniência ELMT ago/26):
        FCFF_t = alfa·(1+g1)^t + beta,
        alfa = (1−t)·EBITDA0 − wk·g1·Receita0/(1+g1);  beta = −(1−t)·D&A_parque
    (a anuidade PLANA da depreciação fixa é o termo que a rodada única não representa; o RiR
    da rampa VARIA ano a ano — não há vetor único). g1 < 0 é o bloco de COLHEITA (liberação
    de giro: FCFF > NOPAT). A fase 2 roda no PRÓPRIO ev_nopat (a costura é verificável por
    partes). Autovalidação interna com asserts exatos: fluxo a fluxo vs alfa/beta; VP
    explícito vs fechado; Receita_T = capacidade quando g1 vem da utilização.
    Unidades: monetários na unidade do usuário; taxas em FRAÇÃO (o CLI converte de %)."""
    if t_rampa < 1 or n <= t_rampa:
        raise ValueError('composição exige 1 <= t_rampa < n (a fase 2 precisa de >= 1 ano explícito)')
    if w <= -1 or g2 <= -1:
        raise ValueError('domínio inválido: requer WACC > -100% e g2 > -100%')
    if kappa < 0:
        raise ValueError('domínio inválido: kappa (intensidade de capital fixo) deve ser >= 0')
    if wk < 0 and (wk + kappa) <= 1e-15:
        raise ValueError('giro negativo com |wk| >= kappa: o capital incremental total é <= 0 e a '
                         'intensidade de capital deixa de ser definida — rode as fases pelo bloco padrão '
                         '(`ev` por fase) em vez da rampa fechada')
    capacidade = None
    if g1 is None:
        if util is None or not (0.0 < util < 1.0):
            raise ValueError('informe --g1 diretamente OU --util em (0,100) com --t-rampa')
        g1 = (1.0 / util) ** (1.0 / t_rampa) - 1.0
        capacidade = receita0 / util
    m = ebitda0 / receita0
    T = t_rampa
    rev = [receita0 * (1 + g1) ** t for t in range(0, T + 1)]
    fcff1, rir1, dpath = [], [], []
    for t in range(1, T + 1):
        eb = m * rev[t]
        nop = (eb - da_parque) * (1 - tax)
        dwk = wk * (rev[t] - rev[t - 1])
        fcff1.append(nop - dwk)
        rir1.append(dwk / nop if nop else float('nan'))
        dpath.append(da_parque / eb)
    alfa = (1 - tax) * ebitda0 - wk * g1 * receita0 / (1 + g1)
    beta = -(1 - tax) * da_parque
    p1 = max(abs(fcff1[t - 1] - (alfa * (1 + g1) ** t + beta)) for t in range(1, T + 1))
    assert p1 < 1e-7 * max(1.0, abs(ebitda0)), f'P1 fluxo a fluxo quebrou: {p1}'
    pv1_exp = sum(f / (1 + w) ** t for t, f in enumerate(fcff1, 1))
    r1 = (1 + g1) / (1 + w)
    soma_r1 = float(T) if abs(r1 - 1.0) < 1e-12 else r1 * (1 - r1 ** T) / (1 - r1)
    # Limite analítico em W=0: a anuidade plana vale exatamente T·beta.
    ann_beta = float(T) if abs(w) < 1e-14 else (1 - (1 + w) ** -T) / w
    pv1 = alfa * soma_r1 + beta * ann_beta
    assert abs(pv1 - pv1_exp) < 1e-7 * max(1.0, abs(pv1_exp)), 'VP fechado != explícito'
    ebT = m * rev[T]
    d2 = da_parque / ebT
    m2n = m * (1 - d2) * (1 - tax)
    if m2n <= 0:
        raise ValueError('fase 2 inválida: margem NOPAT deve ser positiva para mapear capital incremental')
    den_cap = wk + kappa
    if den_cap <= 1e-15:
        rir2 = 0.0
        roic2 = 1e12
        roic2_limite = True
    else:
        # Forma simplificada exata, definida também em g2=0. A forma antiga g2/RiR gerava 0/0.
        rir2 = den_cap * g2 / ((1 + g2) * m2n)
        roic2 = (1 + g2) * m2n / den_cap
        roic2_limite = False
    nopT = ebT * (1 - d2) * (1 - tax)
    mn2 = ev_nopat(g2, roic2, w, n - T, tv=tv, roic_tv=roic_tv, gp=gp, roic_book=roic_book)
    ev_T = mn2 * nopT
    ev = pv1 + ev_T / (1 + w) ** T
    out = {'bloco': ('colheita → expansão' if g1 < 0 else 'rampa → expansão') + ' (composição §8f, de trás para frente)',
           'g1_%': round(g1 * 100, 4), 'g2_%': round(g2 * 100, 4), 'T_rampa': T, 'n_total': n,
           'd_trajetoria_fase1_%': {'ano_1': round(dpath[0] * 100, 3), f'ano_{T}': round(dpath[-1] * 100, 3)},
           'd2_fase2_%': round(d2 * 100, 3),
           'rir_fase1_%': {'ano_1': round(rir1[0] * 100, 3), f'ano_{T}': round(rir1[-1] * 100, 3),
                           'nota': 'VARIA — a rampa não tem vetor único; a compressão exata é alfa/beta'},
           'alfa': round(alfa, 6), 'beta': round(beta, 6),
           'rir2_%': round(rir2 * 100, 3),
           'roic2_%': ('infinito — capital incremental zero' if roic2_limite else round(roic2 * 100, 3)),
           'vp_fase1': round(pv1, 4), 'valor_fase2_no_ano_T': round(ev_T, 4),
           'EV': round(ev, 4), 'EV/EBITDA0': round(ev / ebitda0, 4),
           'checks_internos': {'P1_fluxo_a_fluxo_max_abs': p1,
                               'P1b_vp_fechado_vs_explicito': round(pv1 - pv1_exp, 12),
                               'P3': 'fase 2 = ev_nopat do próprio motor (costura verificável por partes)'},
           'travas': ['terminal NÃO herda a rampa: fase 2 e TV usam o vetor do capital que constrói',
                      'DELIMITADOR da fronteira (fim do ano T): declare o evento observável — '
                      'comissionamento datado, plena capacidade, termo, marco de guidance',
                      'volume != preço: g1 é VOLUME; repasse de preço entra separado (§7)']}
    if capacidade is not None:
        out['capacidade_receita'] = round(capacidade, 4)
        chk = rev[T] - capacidade
        assert abs(chk) < 1e-6 * capacidade, 'Receita_T != capacidade (erro de montagem)'
        out['checks_internos']['P4_receita_T_menos_capacidade'] = round(chk, 10)
    if g1 < 0:
        out['aviso_colheita'] = ('g1 < 0 com wk > 0: LIBERAÇÃO de giro — FCFF > NOPAT na fase 1 '
                                 '(processadora pós-pico, run-off, footprint encolhendo)')
    if rir2 >= 1.0:
        out['aviso_delator'] = ('RiR da fase 2 >= 100%: crescimento acima do autofinanciável — '
                                'exige funding declarado ou a classificação está errada (§8f, trava 6)')
    return out

def conservacao_capital(capex_total, dwc, ebitda, d, t, g, roic):
    """[v9.24] Verificação executável da identidade §11.1b (v9.19):
    capex_total + ΔWC = d×EBITDA + RiR×NOPAT, com RiR = g/ROIC e NOPAT = EBITDA(1−d)(1−t).
    Gap > 10% ⟹ o par (d, RiR) está na base errada. Frações; monetários na unidade do usuário."""
    consumido = capex_total + dwc
    nopat = ebitda * (1 - d) * (1 - t)
    rir = g / roic if roic else float('nan')
    encargos = d * ebitda + rir * nopat
    gap = consumido - encargos
    gap_pct = gap / consumido if consumido else float('nan')
    out = {'capital_consumido': round(consumido, 4),
           'encargo_reposicao_d_x_EBITDA': round(d * ebitda, 4),
           'encargo_crescimento_RiR_x_NOPAT': round(rir * nopat, 4),
           'gap': round(gap, 4), 'gap_%': round(gap_pct * 100, 2)}
    if abs(gap_pct) > 0.10:
        out['ALERTA'] = ('PAR (d, RiR) NA BASE ERRADA — gap > 10%: reclassifique antes de '
                         'qualquer cenário (§11.1b); d de caixa com RiR contábil não cobra '
                         'reposição; d contábil com RiR de capex bruto cobra duas vezes')
    else:
        out['leitura'] = 'identidade fecha dentro do limiar — par (d, RiR) na mesma base'
    return out

def validacao_unit_economics(roic_ue, roic, limiar=0.01):
    """[v9.24] Terceiro canal do triângulo (§11.2): confronta o ROIC do vetor com o ROIC de
    unit economics medido de baixo para cima (margem incremental × giro incremental do ciclo).
    Espelho do --rir-observado: divergir é legítimo, ficar calado não. Frações."""
    gap = roic_ue - roic
    out = {'roic_ue_%': round(roic_ue * 100, 3), 'roic_vetor_%': round(roic * 100, 3),
           'gap_pp': round(gap * 100, 3),
           'estatuto': ('OBSERVADO pode mover o vetor central, com a mudança declarada; '
                        'CONSTRUÍDO é linha de sensibilidade — nunca sobrescreve em silêncio. '
                        'Anti-identidade: só vale medido em fonte INDEPENDENTE dos agregados da cadeia.')}
    if abs(gap) > limiar:
        direc = ('margem incremental >> média sugere g subestimado ou RiR medido em ano de '
                 'deployment atípico' if gap > 0 else
                 'giro do ciclo << implícito sugere capital de giro estrutural subdimensionado na cadeia')
        out['DIVERGENCIA_DECLARADA'] = f'{gap * 100:+.1f} p.p. — {direc}'
    else:
        out['leitura'] = 'coincide dentro do limiar — o resíduo do triângulo é consistente com a economia do ciclo'
    return out

def pe(g, roe, ke, n, gde, nde, tv='book', roe_tv=None, gp=0.0, roe_book=None,
       politica_tv='continua', mid_year=False):
    """P/L current. Termo (gde-nde) = caixa/equity devolvido ao FCFE — MÓDULO DE POLÍTICA
    FINANCEIRA (proporção de caixa constante, payout endógeno via sweep), não identidade
    geral. A decomposição operacional × efeito-caixa sai no output do comando `pe`.
    politica_tv (só afeta 'gordon' com caixa != 0):
      'continua' (default, correção C1 da auditoria v8): a política segue na perpetuidade —
        FCFE_TV = LL_{n+1}·[(1−gp/ROE_TV) + (gde−nde)·(gp/ROE_TV)]. É o FCFE CANÔNICO
        (= FCFF − juros(1−t) + emissão) com o balanço crescendo a gp, provado equivalente
        a dividendos + Δcaixa na planilha vF8 (linhas 226–235).
      'encerra': a política morre no ano n (comportamento anterior à correção) — hipótese
        legítima, mas tem que ser declarada.
    'book': [v9.30] valuation canônico por CLEAN SURPLUS: os fluxos explícitos são DIVIDENDOS
    (Div_t = LL_t − ΔE_t), e o TV é E_n acumulado. Como E_n já contém o caixa retido, somar
    Δcaixa ao fluxo explícito e depois E_n no terminal contaria o mesmo caixa duas vezes. Por isso
    Caixa/E NÃO altera o valor da convenção book por si só; excess cash/rendimento de caixa deve ser
    tratado separadamente. 'convergencia': TV = LL/Ke sem gp declarado ⟹ termo nulo;
    para política contínua com crescimento terminal, use 'gordon'.
    mid_year (C3): convenção de meio de ano, multiplica por (1+Ke)^0.5. Default False."""
    tv = tv_canon(tv)
    if g <= -1 or roe <= 0 or ke <= -1 or n < 1:
        return float('nan')
    caixa = gde - nde
    # [v9.30] Na convenção book, clean surplus exige DDM + book: Div = LL − ΔE =
    # LL·(1−g/ROE_marg). O termo +Δcaixa pertence ao FCFE de uma política de sweep, mas esse
    # mesmo caixa permanece dentro de E_n; usar FCFE + E_n duplica caixa. Gordon/convergência
    # continuam no módulo financeiro legado, onde não há book terminal contendo o caixa.
    ret = (1 - g / roe) if tv == 'book' else ((1 - g / roe) + caixa * (g / roe))
    s = sum(ret * (1 + g) ** t / (1 + ke) ** t for t in range(1, n + 1))
    if tv == 'gordon':
        if roe_tv is None or roe_tv <= 0 or gp <= -1 or gp >= ke:
            return float('nan')
        ret_tv = (1 - gp / roe_tv) + (caixa * (gp / roe_tv) if politica_tv == 'continua' else 0.0)
        s += (1 + g) ** (n + 1) * ret_tv / (ke - gp) / (1 + ke) ** n
    elif tv == 'convergencia':
        if ke <= 0:
            return float('nan')
        s += (1 + g) ** (n + 1) / (ke * (1 + ke) ** n)
    else:  # book
        rb = roe_book if roe_book is not None else roe
        if rb <= 0:
            return float('nan')
        # [v9.30] E_n por clean surplus; valuation book por dividendos + E_n
        # (derivação reproduzida na suíte; a planilha de desenvolvimento não integra o ZIP canônico), NÃO por analogia: sob a política de
        # caixa constante (C = caixa·E) e a identidade vF8 (FCFE = Div + Δcaixa), a retenção
        # líquida sofre o gross-up da política e o caixa CANCELA — ΔE_t = (g/ROE_marg)·LL_t,
        # INVARIANTE a caixa/E. A forma fechada coincide com a do firm por esse cancelamento:
        # E_n = (1+g)·(1/ROE_médio_inicial − 1/ROE_marg) + (1+g)^{n+1}/ROE_marg.
        # Colapsos do ESTOQUE: médio = marginal ⟹ E_n = LL_{n+1}/ROE; g = 0 ⟹ E_n = 1/médio.
        # [v9.30] O VALUATION book não preserva o antigo anchor vF8 com caixa porque aquele anchor
        # somava Δcaixa aos fluxos e o mesmo caixa novamente dentro de E_n.
        e_n = (1 + g) * (1.0 / rb - 1.0 / roe) + (1 + g) ** (n + 1) / roe
        if e_n <= 0:
            return float('nan')
        s += e_n / (1 + ke) ** n
    return s * ((1 + ke) ** 0.5 if mid_year else 1.0)

# ---------------- solver ----------------
def _dedupe_roots(roots, atol=1e-10, rtol=1e-8):
    """Deduplica raízes numéricas: uma raiz sobre um ponto da grade pertence aos dois
    intervalos adjacentes e não pode virar dois regimes econômicos no output."""
    out = []
    for x in sorted(roots):
        if not out or abs(x - out[-1]) > max(atol, rtol * max(abs(x), abs(out[-1]), 1.0)):
            out.append(x)
    return out

def solve(f, lo, hi, steps=800):
    """Varredura + bissecção; retorna raízes DISTINTAS com mudança de sinal no intervalo."""
    roots, x0, y0 = [], lo, f(lo)
    for i in range(1, steps + 1):
        x1 = lo + (hi - lo) * i / steps
        y1 = f(x1)
        ok = all(map(lambda v: v == v and abs(v) != float('inf'), (y0, y1)))
        if ok and y0 * y1 <= 0 and y0 != y1:
            a, b, fa = x0, x1, y0
            for _ in range(90):
                m = (a + b) / 2; fm = f(m)
                if fa * fm <= 0: b = m
                else: a, fa = m, fm
            roots.append((a + b) / 2)
        x0, y0 = x1, y1
    return _dedupe_roots(roots)

def solve_full(f, lo, hi, steps=800, ref=1.0, tang_rel=1e-4):
    """Raízes por mudança de sinal + candidatos TANGENCIAIS (mínimos locais de |f| sem
    cruzamento — a bissecção pura os perde exatamente na região do teto, que é onde a
    leitura 'o mercado exige o máximo desta convenção' nasce)."""
    roots = solve(f, lo, hi, steps)
    xs = [lo + (hi - lo) * i / steps for i in range(steps + 1)]
    ys = [f(x) for x in xs]
    tang = []
    for i in range(1, steps):
        y0, y1, y2 = ys[i - 1], ys[i], ys[i + 1]
        if any(v != v for v in (y0, y1, y2)):
            continue
        if abs(y1) <= abs(y0) and abs(y1) <= abs(y2) and y0 * y2 > 0:
            a, b = xs[i - 1], xs[i + 1]
            for _ in range(80):
                m1, m2 = a + (b - a) / 3, b - (b - a) / 3
                if abs(f(m1)) < abs(f(m2)): b = m2
                else: a = m1
            x = (a + b) / 2; fx = f(x)
            if abs(fx) <= tang_rel * max(abs(ref), 1e-12):
                if not any(abs(x - r) <= 1e-3 * max(abs(r), 1e-6) for r in roots) and \
                   not any(abs(x - t['x']) <= 1e-3 * max(abs(t['x']), 1e-6) for t in tang):
                    tang.append({'x': x, 'residuo': fx})
    return roots, tang

def identificacao(mult_fn, x, M, tol=0.01):
    """Métricas de identificação econômica em torno de uma raiz: slope, curvatura,
    elasticidade e o intervalo da variável compatível com alvo ± tol. Precisão numérica
    da raiz NÃO é identificação — perto da neutralidade a variável implícita é ruído."""
    h = max(abs(x), 1e-4) * 1e-4
    m0, mp, mm = mult_fn(x), mult_fn(x + h), mult_fn(x - h)
    if any(v != v for v in (m0, mp, mm)):
        return {'nota': 'derivadas indisponíveis na vizinhança da raiz'}
    d1 = (mp - mm) / (2 * h)
    d2 = (mp - 2 * m0 + mm) / h ** 2
    elast = d1 * x / M if M else float('nan')
    dx = abs(tol * M / d1) if d1 else float('inf')
    rel = dx / abs(x) if x else float('inf')
    cls = 'forte' if rel < 0.05 else ('moderada' if rel < 0.20 else 'fraca')
    return {'slope_dM_dx': round(d1, 4), 'curvatura_d2M_dx2': round(d2, 2),
            'elasticidade': round(elast, 3),
            'intervalo_para_alvo_±' + f'{tol:.0%}': [round((x - dx) * 100, 3), round((x + dx) * 100, 3)],
            'largura_relativa_%': round(rel * 100, 1) if rel == rel else None,
            'identificacao': cls,
            'nota': ('identificação FRACA: a função é quase plana — a raiz é ruído com cara '
                     'de precisão; não apresente sem a curvatura' if cls == 'fraca' else
                     'identificação moderada: reporte o intervalo junto com a raiz'
                     if cls == 'moderada' else 'bem identificada no local')}

# ---------------- diagnósticos ----------------
def _guardas_damodaran(d, tv, gp, custo, rf=None, moeda=None, rotulo_custo='Ke'):
    """v9.4 — guardas opcionais (aviso na ausência, nunca bloqueio):
    Guarda 1 (âncora macro do gp, Damodaran): gp perpétuo ≤ rf NOMINAL da moeda do modelo
    (proxy do crescimento nominal da economia); em regime REAL, o teto é o PIB real (~3%).
    Guarda 2 (moeda/regime): g, gp e custo de capital na MESMA moeda e MESMO regime — o motor
    não tem como verificar moeda a partir de números; a guarda é declarativa."""
    regime_real = bool(moeda) and moeda.lower().endswith('-real')
    if tv_canon(tv) == 'gordon' and gp and gp > 0:
        if rf is not None:
            teto = min(rf, 0.03) if regime_real else rf
        elif regime_real:
            teto = 0.03
        else:
            teto = None
        if teto is not None:
            base_txt = ('PIB real (~3%, regime real declarado)' if regime_real and (rf is None or teto < rf)
                        else f'rf nominal declarado ({rf*100:.2f}%)')
            if gp > teto + 1e-9:
                d.append(f"ALERTA (âncora macro, Damodaran): gp = {gp*100:.2f}% EXCEDE o teto de "
                         f"{teto*100:.2f}% [{base_txt}] em {(gp-teto)*100:.2f} p.p. — a empresa cresce "
                         f"mais que a economia em perpetuidade. Ou reduza gp, ou declare por escrito "
                         f"na entrega a tese que sustenta a exceção.")
            else:
                d.append(f"ÂNCORA MACRO OK: gp = {gp*100:.2f}% ≤ teto de {teto*100:.2f}% [{base_txt}].")
        else:
            d.append(f"PREMISSA NÃO ANCORADA: gp = {gp*100:.2f}% perpétuo sem --rf declarado. "
                     f"Regra (Damodaran): gp ≤ rf nominal da moeda do modelo (ou ~3% em regime real). "
                     f"Declare --rf para ativar a verificação.")
    if not moeda:
        d.append(f"MOEDA/REGIME NÃO DECLARADOS: g, gp e {rotulo_custo} devem estar na MESMA moeda e "
                 f"MESMO regime (nominal/real). Declare --moeda (ex.: BRL-nominal, USD-nominal, BRL-real).")
    return d


def coerencia_vetor(g=None, roic=None, roe=None, w=None, ke=None, kd=None, tax=None,
                    d=None, gde=None, nde=None, cash_yield=None, rir_observado=None, ebitda_ic=None, tol=5e-3):
    """[v9.11] Gate de COERÊNCIA do vetor de inputs (declaratório: registra e avisa, nunca
    bloqueia nem converte — mesmo contrato do Gate 0).

    Motivo de existir. O motor recebe (g, ROIC, W, d, t, D/E) como parâmetros LIVRES, mas na
    planilha de referência eles são OUTPUTS acoplados por identidades: o vetor da âncora é o
    vetor de saída de uma DRE/BP/FC específica. O uso normal da skill — pegar o ROIC que a
    reversa devolveu e perturbá-lo num cenário — pode portanto produzir um vetor que nenhuma
    demonstração financeira gera, e até a v9.10 nada avisava. Este gate não deriva nada: ele só
    confronta o que o analista JÁ informou contra as identidades da planilha.

    NÃO fecha a lacuna maior: a cadeia DRE/BP/FC → drivers continua fora do motor por decisão de
    projeto (a skill aplica o framework, não substitui o modelo do analista).

    Identidades (referência de célula da planilha vF8, aba 'Justified Multiples Logic (2)'):
      (1) linha 122, ajustada na v9.28 para caixa remunerado:
          ROE = ROIC·(1 + ND/E) − Kd·(1−t)·(D/E) + Kcash·(1−t)·(Cash/E)    [alavancagem]
          O ROIC remunera o capital investido (= dívida LÍQUIDA + PL) e os juros incidem sobre a
          dívida BRUTA. Se o LL inclui rendimento de caixa e o ROIC exclui esse caixa do capital
          investido, Cash/E = D/E − ND/E e o termo Kcash líquido é obrigatório. Sem --cash-yield,
          o gate assume que esse rendimento foi retirado do LL (ou é imaterial) e avisa.
      (2) célula C164, mesma simetria:
          WACC = [Ke + Kd·(1−t)·(D/E) − Kcash·(1−t)·(Cash/E)] / (1 + ND/E)
          Simetria estrutural: a MESMA transformação leva ROE→ROIC e Ke→WACC, e é ela que faz
          "ROIC = WACC ⟺ ROE = Ke" ser identidade EXATA no motor. Note que este WACC não é o
          weighted-average de manual com pesos a mercado sobre dívida bruta: o capital investido
          é ND + PL e os juros incidem sobre a bruta. Com caixa = 0 as duas formas coincidem;
          com caixa > 0 divergem (na âncora, 18,73% contra 18,21%), e é a forma acima que
          reproduz a planilha. O comando `kewacc` responde a outra pergunta — sanity check
          ESTÁTICO de perpetuidade ancorado em Ku — e não deve ser confrontado com esta.
      (3) linha 96 vs 144  RiR observado (deployment/NOPAT) vs RiR da fórmula (g/ROIC)
      (4) linha 100 vs 105 d e ROIC implicam EBITDA/capital investido = ROIC/((1−d)(1−t))

    Devolve (diagnosticos, resumo) — resumo declara o que foi checado E o que NÃO pôde ser
    checado por falta de input (regra 10: nada depende de o analista lembrar)."""
    dg, checados, faltando = [], [], []

    def falta(nome, *pares):
        ausentes = [n for n, v in pares if v is None]
        if ausentes:
            faltando.append(f'{nome} (falta: {", ".join(ausentes)})')
            return True
        return False

    # (1) ROE × ROIC × alavancagem, com caixa remunerado separado quando aplicável.
    if not falta('ROE×ROIC×alavancagem', ('roic', roic), ('roe', roe), ('gde', gde), ('nde', nde),
                 ('kd', kd), ('tax', tax)):
        kd_liq = kd * (1 - tax)
        caixa = gde - nde
        ky_liq = (cash_yield or 0.0) * (1 - tax)
        roe_id = roic * (1 + nde) - kd_liq * gde + ky_liq * caixa
        checados.append('ROE×ROIC×alavancagem')
        if caixa > 1e-9 and cash_yield is None:
            dg.append('CAIXA REMUNERADO [vetor]: Cash/E = D/E − ND/E > 0 e --cash-yield não foi '
                      'informado. A identidade assume rendimento de caixa excluído do LL (ou imaterial). '
                      'Se o ROE informado inclui juros sobre caixa, informe --cash-yield bruto; rota '
                      'preferida: retire o resultado de excess cash do LL e valore o caixa separadamente.')
        if abs(roe_id - roe) > tol:
            termo_caixa = f" + Kcash_líq·Cash/E ({ky_liq:.2%}×{caixa:.3f})" if cash_yield is not None else ''
            dg.append(f"INCOERÊNCIA [vetor]: ROE informado ({roe:.2%}) ≠ ROE implicado pela "
                      f"alavancagem ({roe_id:.2%}); identidade operacional ROE = ROIC·(1 + ND/E) − "
                      f"Kd(1−t)·(D/E){termo_caixa}. ROIC {roic:.2%}, ND/E {nde:.3f}, D/E {gde:.3f}, "
                      f"Kd líq {kd_liq:.2%}. Desvio de {(roe - roe_id) * 100:+.2f} p.p. Um componente "
                      f"foi movido sem os demais ou o resultado do caixa não foi separado.")

    # (2) WACC × Ke × Kd × t × D/E × ND/E — mesma transformação, líquida do retorno do caixa.
    if not falta('WACC×Ke×Kd×alavancagem', ('w', w), ('ke', ke), ('kd', kd), ('tax', tax),
                 ('gde', gde), ('nde', nde)):
        caixa = gde - nde
        ky_liq = (cash_yield or 0.0) * (1 - tax)
        w_id = (ke + kd * (1 - tax) * gde - ky_liq * caixa) / (1 + nde)
        checados.append('WACC×Ke×Kd×alavancagem')
        if abs(w_id - w) > tol:
            dg.append(f"INCOERÊNCIA [vetor]: WACC informado ({w:.2%}) ≠ WACC implicado ({w_id:.2%}) "
                      f"por Ke {ke:.2%}, Kd {kd:.2%}, t {tax:.0%}, D/E {gde:.3f}, ND/E {nde:.3f}"
                      + (f" e Kcash {cash_yield:.2%}" if cash_yield is not None else '') + "; "
                      f"a transformação usa capital investido líquido e deduz retorno de caixa quando "
                      f"ele está no Ke/ROE. Desvio de {(w - w_id) * 100:+.2f} p.p.")
        # simetria: a mesma transformação em ROE tem de devolver o ROIC informado
        if roe is not None and roic is not None:
            roic_id = (roe + kd * (1 - tax) * gde - ky_liq * caixa) / (1 + nde)
            checados.append('simetria ROE→ROIC ≡ Ke→WACC')
            if abs(roic_id - roic) > tol:
                dg.append(f"INCOERÊNCIA [vetor]: a transformação que leva Ke→WACC não leva o ROE "
                          f"informado ({roe:.2%}) ao ROIC informado ({roic:.2%}) — devolve "
                          f"{roic_id:.2%}. As duas pernas do vetor descrevem estruturas de capital "
                          f"diferentes.")

    # (3) RiR observado × RiR da fórmula — planilha linha 96 vs 144
    if not falta('RiR observado×g/ROIC', ('g', g), ('roic', roic), ('rir_observado', rir_observado)):
        rir_f = g / roic if roic else float('inf')
        checados.append('RiR observado×g/ROIC')
        if abs(rir_f - rir_observado) > 2 * tol:
            direc = 'MAIS' if rir_observado > rir_f else 'MENOS'
            dg.append(f"DIVERGÊNCIA DECLARADA [vetor]: RiR observado ({rir_observado:.1%}, "
                      f"deployment/NOPAT) ≠ RiR da fórmula ({rir_f:.1%} = g/ROIC). A companhia "
                      f"reinvestiu {direc} do que o g efetivo exige. NÃO é erro — a própria "
                      f"planilha de referência exibe 42,2% contra 32,0% — mas condiciona a leitura: "
                      f"ou o g efetivo está defasado do capital já comprometido (upside de RiR=0, "
                      f"§6.9), ou a rentabilidade marginal do capital novo difere da que está no "
                      f"vetor. Declare qual das duas na entrega.")

    # (4) d e ROIC implicam a intensidade de capital — planilha linha 100 vs 105
    if not falta('d×intensidade de capital', ('roic', roic), ('d', d), ('tax', tax)):
        den = (1 - d) * (1 - tax)
        checados.append('d×intensidade de capital')
        if den > 0:
            eb_ic = roic / den
            nota = (f"ECO [vetor]: (ROIC {roic:.2%}, d {d:.1%}, t {tax:.0%}) implicam "
                    f"EBITDA/capital investido = {eb_ic:.4f}. Confronte com o balanço: mexer no "
                    f"ROIC sem mexer em d muda esta razão, e é por aí que o cenário perde a "
                    f"pré-imagem contábil.")
            if ebitda_ic is not None:
                if abs(eb_ic - ebitda_ic) > max(tol, abs(ebitda_ic) * 0.05):
                    dg.append(f"INCOERÊNCIA [vetor]: EBITDA/capital investido implicado "
                              f"({eb_ic:.4f}) ≠ observado ({ebitda_ic:.4f}). O vetor descreve uma "
                              f"intensidade de capital que o balanço informado não tem.")
                else:
                    dg.append(nota + ' Confere com o observado.')
            else:
                dg.append(nota)

    resumo = {'identidades_checadas': checados or ['nenhuma'],
              'nao_checadas_por_falta_de_input': faltando or ['nenhuma'],
              'nota': ('gate DECLARATÓRIO: avisa, nunca bloqueia. A cadeia DRE/BP/FC → drivers '
                       'permanece FORA do motor (decisão de projeto) — este gate confronta o vetor '
                       'informado contra as identidades da planilha, não o deriva.')}
    return dg, resumo


def diag_firm(g, roic, w, tv='book', n=10, roic_book=None, roic_tv=None, rf=None, moeda=None, gp=0.0,
              da=None, tax=None):
    tv = tv_canon(tv); d = []
    # --- guarda de domínio do encargo de reposição (v10) ---
    # A doutrina exigia esta verificação desde a v9.28 ('erro de unidade nunca pode virar
    # múltiplo aparentemente plausível') e o motor não a emitia: d >= 100% devolvia
    # EV/EBITDA NEGATIVO em silêncio.
    if da is not None:
        if da >= 1.0:
            d.append("DOMÍNIO [d]: encargo de reposição >= 100% do EBITDA ⟹ lucro operacional após "
                     "imposto NEGATIVO e múltiplo de EBITDA sem conteúdo econômico (sai com sinal "
                     "invertido). O múltiplo justo NÃO está definido nesta base: normalize a "
                     "métrica-base, migre o par (d, RiR) para base caixa, ou troque de arquitetura "
                     "(fronteira de escopo — valor de ativos, opção real, liquidação).")
        elif da >= 0.60:
            d.append(f"DOMÍNIO [d]: encargo de reposição em {da:.1%} do EBITDA — regime de D&A-overhang. "
                     "O lucro operacional após imposto é fino e o múltiplo fica hipersensível ao d: "
                     "a conservação de capital (capex + Δgiro = d×EBITDA + RiR×NOPAT) deixa de ser "
                     "opcional, e a base de lucro precisa ser confrontada com o nível normalizado.")
        if tax is not None and 0.0 <= da < 1.0 and (1 - da) * (1 - tax) <= 0:
            d.append("DOMÍNIO [NOPAT]: (1−d)(1−t) <= 0 ⟹ lucro operacional após imposto não positivo. "
                     "Cenário não representável no framework.")
    if tax is not None and not (0.0 <= tax <= 1.0):
        d.append(f"DOMÍNIO [t]: alíquota fora de 0–100% ({tax:.1%}). Regime anômalo — exige "
                 "justificativa explícita e reconciliação econômica.")
    if tv == 'book':
        d.append("CONVENÇÃO 'book' (ex-'ic') [hipótese, não lei]: renda residual truncada em n — o NOPAT "
                 "INTEIRO colapsa de ROIC×IC para WACC×IC no ano n+1 e o TV é o capital investido. É mais "
                 "agressiva que 'a vantagem se exaure' no sentido padrão (RONIC=WACC só no capital NOVO, "
                 "NOPAT preservado): para essa hipótese use tv='convergencia'. No caso CONFLACIONADO "
                 "(book=marginal), propriedades como o múltiplo poder cair quando a variável única de ROIC "
                 "sobe e existir teto sob certas inversões pertencem a esta convenção — não à convergência "
                 "competitiva em geral. Com --roic-book separado, interprete médio inicial e marginal como "
                 "variáveis distintas; sob 'convergencia' o múltiplo sobe com o ROIC marginal.")
        if roic_book is None:
            d.append("ATENÇÃO (conflação marginal×médio): sem --roic-book, a 'book' usa o MESMO ROIC do explícito para "
                     "ancorar IC_0 = NOPAT_1/ROIC e para remunerar o capital novo. Isso força retorno médio "
                     "inicial = marginal por hipótese. Se a rentabilidade marginal difere da contábil/blended — "
                     "exatamente o caso que aplicacao.md §11.1 manda derivar — informe --roic-book com a MÉDIA "
                     "forward do estoque; o erro pode ser material.")
    if tv == 'gordon' and roic_tv is not None:
        if roic_tv < w - 5e-4:
            d.append(f"REGIME DECLARADO: ROIC_TV ({roic_tv:.1%}) < WACC — destruição persistente na "
                     "perpetuidade. Legítimo, desde que declarado como hipótese na entrega.")
        elif abs(roic_tv - w) < 5e-4:
            d.append("NOTA: ROIC_TV = WACC ⟹ 'gordon' colapsa em 'convergencia' (TV = NOPAT/W, "
                     "invariante a gp). Crescimento terminal é value-neutral.")
    try:
        _p = ev_nopat_partes(g, roic, w, n, tv=tv, roic_tv=roic_tv, gp=gp, roic_book=roic_book)
        _peso_tv = _p['terminal'] / _p['total'] if _p['total'] else float('nan')
    except Exception:
        _peso_tv = float('nan')
    if _peso_tv == _peso_tv and _peso_tv > 0.50:
        d.append(f"TERMINAL DOMINANTE: {_peso_tv:.0%} do valor está no valor terminal. Duas "
                 "consequências obrigatórias na entrega: (i) a sensibilidade ao horizonte de "
                 "vantagem deixa de ser opcional; (ii) NENHUMA convenção terminal embute hazard "
                 "de extinção — o viés é unidirecional (terminal SUPERESTIMADO) e da ordem de "
                 "−16% a −27% para hazards de 2% a 5% a.a. Declare o viés e a direção.")
    rir = g / roic
    d.append(f"RiR = g/ROIC = {rir:.1%} | spread ROIC−WACC = {(roic-w)*100:+.1f} p.p.")
    if rir > 1:
        d.append("ALERTA: RiR > 100% — crescimento não autofinanciável (FCFF < 0 no explícito). "
                 "EXIGE fonte de funding declarada (captação, dívida, capital novo). Sem funding "
                 "plausível, é hipótese diagnóstica FORTE de erro de classificação nível→taxa "
                 "(degrau lançado como g) — mas é hipótese a investigar, não veredicto.")
    if roic < w and g > 0:
        d.append("ALERTA: ROIC < WACC com g > 0 — crescer destrói valor; múltiplo FORWARD cai com g "
                 "(na base corrente ele SOBE por reajuste (1+g) — não é criação de valor).")
    if roic < w and tv == 'book':
        if roic_book is None:
            d.append("ALERTA DE CONFLAÇÃO [B-01]: ROIC < WACC na 'book' com o MESMO ROIC nos dois papéis. "
                     "AQUI o mesmo ROIC baixo ancora um IC_0 artificialmente alto E remunera o capital novo, de modo que "
                     "o TV cresce quando o ROIC cai e o múltiplo pode subir conforme o negócio piora. A perversidade "
                     "é da CONFLAÇÃO, não da convenção: informe --roic-book com a MÉDIA forward do estoque. "
                     "Para spread negativo persistente use tv='gordon' com --roic-tv abaixo do WACC.")
        else:
            d.append(f"CONVENÇÃO CONDICIONADA [B-01]: ROIC marginal ({roic:.1%}) < WACC ({w:.1%}) com ROIC "
                     f"book informado ({roic_book:.1%}). [v9.27] O TV parte do book e ACUMULA o capital "
                     "novo ao marginal (a média deriva na direção dele; o eco abaixo mostra o médio no ano "
                     "n) — não há perversidade: o múltiplo acompanha o marginal, como deve. O "
                     "explícito destrói valor, mas a 'book' permanece ADMISSÍVEL sob tese DECLARADA de saída "
                     "pelo capital investido (turnaround, capex regulatório, reconstrução operacional, "
                     "liquidação ou venda pelo patrimônio). Sem essa tese na entrega, use tv='gordon' com "
                     "--roic-tv abaixo do WACC.")
            if roic_book < w:
                d.append(f"SUB-ALERTA [B-01, papel MÉDIO]: ROIC book ({roic_book:.1%}) < WACC ({w:.1%}) ⟹ "
                         f"a âncora inicial do TV (IC_0 = NOPAT/ROIC_book) excede NOPAT/WACC em {w/roic_book:.2f}x. A saída pelo capital "
                         "investido embute RECUPERAÇÃO acima do valor capitalizado de lucros sub-custo — "
                         "hipótese de recuperação, não de continuidade, e exige tese própria. O cruzamento "
                         "é exato em ROIC_book = WACC.")
    if tv == 'book' and roic_book is not None and abs(roic_book - roic) >= 5e-4 and abs(g) > 1e-9:
        ic_n = (1 + g) * (1.0 / roic_book - 1.0 / roic) + (1 + g) ** (n + 1) / roic
        if ic_n > 0:
            medio_n = (1 + g) ** (n + 1) / ic_n
            d.append(f"ECO [v9.27, deriva do médio]: ROIC médio do estoque parte de {roic_book:.1%} e chega a "
                     f"{medio_n:.1%} no ano {n} (capital novo ao marginal de {roic:.1%}); "
                     f"TV = IC acumulado = {ic_n/(1+g):.2f}x NOPAT_1.")
    if abs(roic - w) < 5e-4:
        if tv == 'book' and roic_book is not None and abs(roic_book - w) >= 5e-4:
            d.append(f"ATENÇÃO: ROIC marginal ≈ WACC mas ROIC book = {roic_book:.1%} ≠ WACC — sob 'book' "
                     f"a neutralidade é INCOMPLETA: o TV depende do book inicial (e, com g > 0, da "
                     f"acumulação ao marginal) e o múltiplo forward NÃO é 1/WACC. Neutralidade completa sob 'book' exige marginal E "
                     f"book iguais ao WACC; sob 'convergencia'/'gordon' o book não entra no TV e "
                     f"marginal = WACC basta.")
        else:
            d.append("NEUTRALIDADE [identidade]: ROIC ≈ WACC — múltiplo FORWARD invariante a g (= 1/WACC). "
                     "As convenções 'book' e 'convergencia' coincidem EXATAMENTE neste ponto. "
                     "Sob 'book' a identidade pressupõe ROIC book = WACC também (aqui satisfeito ou "
                     "conflacionado). O corrente varia com g por reajuste de base.")
    if abs(g) < 1e-6:
        if tv == 'gordon':
            d.append("NEUTRALIDADE: g = 0 na convenção 'gordon' — múltiplo invariante a ROIC "
                     "(o TV referencia ROIC_TV, não o ROIC do explícito).")
        elif tv == 'convergencia':
            d.append("NEUTRALIDADE: g = 0 na convenção 'convergencia' — múltiplo invariante a ROIC "
                     "(explícito = anuidade; TV = 1/(W(1+W)^n) não referencia o ROIC).")
        else:
            rb = roic_book if roic_book is not None else roic
            tv_share = (1 / (rb * (1 + w) ** n)) / (sum(1 / (1 + w) ** t for t in range(1, n + 1)) + 1 / (rb * (1 + w) ** n))
            d.append(f"ATENÇÃO: g = 0 NÃO torna o múltiplo invariante a ROIC na convenção 'book' com CAP "
                     f"finito. O explícito vale a anuidade, mas o TV = 1/(ROIC_book(1+W)^n) depende do book. "
                     f"A invariância (= 1/WACC) vale em 'convergencia', na forma perpétua ou com n → ∞ "
                     f"(aqui n = {n}; o TV responde por {tv_share:.1%} do múltiplo neste ROIC).")
    return _guardas_damodaran(d, tv, gp, w, rf=rf, moeda=moeda, rotulo_custo='WACC')

def diag_eq(g, roe, ke, gde, nde, tv='book', n=10, roe_book=None, roe_tv=None, politica_tv='continua',
            gp=0.0, rf=None, moeda=None):
    tv = tv_canon(tv); d = []
    caixa = gde - nde
    if tv == 'book':
        d.append("CONVENÇÃO 'book' (ex-'ic') [hipótese, não lei]: renda residual truncada — o LL inteiro "
                 "colapsa de ROE×E para Ke×E no ano n+1; TV = equity contábil. Para 'a vantagem se exaure' "
                 "no sentido padrão (retorno = Ke só no lucro RETIDO novo, LL preservado) use "
                 "tv='convergencia'. Sob 'convergencia' o P/L justo SOBE com o ROE; sob 'book', cai.")
        if roe_book is None:
            d.append("ATENÇÃO (conflação marginal×médio): o TV da 'book' usa o ROE do explícito (marginal) "
                     "como se fosse o ROE MÉDIO contábil INICIAL. Se diferem, informe --roe-book "
                     "com a média; o erro pode ser material.")
        elif abs(roe_book - roe) >= 5e-4 and abs(g) > 1e-9:
            e_n = (1 + g) * (1.0 / roe_book - 1.0 / roe) + (1 + g) ** (n + 1) / roe
            if e_n > 0:
                medio_n = (1 + g) ** (n + 1) / e_n
                d.append(f"ECO [v9.30, deriva do médio]: ROE médio parte de {roe_book:.1%} e chega a "
                         f"{medio_n:.1%} no ano {n} (lucro retido ao marginal de {roe:.1%}; a política de "
                         f"caixa não altera E_n; na book o valuation usa dividendos + E_n para não duplicar caixa); "
                         f"TV = equity acumulado = {e_n/(1+g):.2f}x LL_1.")
    if tv == 'gordon' and roe_tv is not None:
        if abs(caixa) > 1e-9 and gp > 0:
            if politica_tv == 'continua':
                d.append(f"POLÍTICA DE CAIXA NO TERMINAL: 'continua' (default, correção C1) — o FCFE_TV "
                         f"inclui +caixa·(gp/ROE_TV) = +{caixa*(gp/roe_tv)*100:.2f} p.p. no fator de "
                         f"payout terminal. É o FCFE canônico com o balanço crescendo a gp e proporção de "
                         f"caixa constante (premissa 4). Para encerrar a política no ano n, declare "
                         f"--politica-tv encerra.")
            else:
                d.append("POLÍTICA DE CAIXA NO TERMINAL: 'encerra' — a política de caixa proporcional "
                         "morre no ano n e o FCFE_TV usa só (1−gp/ROE_TV). Hipótese declarada; contradiz "
                         "a premissa de proporção de caixa constante se estendida à perpetuidade.")
        if roe_tv < ke - 5e-4:
            d.append(f"REGIME DECLARADO: ROE_TV ({roe_tv:.1%}) < Ke — destruição persistente na "
                     "perpetuidade. Legítimo, desde que declarado como hipótese na entrega.")
        elif abs(roe_tv - ke) < 5e-4:
            d.append("NOTA: ROE_TV = Ke ⟹ 'gordon' colapsa em 'convergencia' (TV = LL/Ke, invariante a gp).")
    ret = g / roe
    d.append(f"Retenção g/ROE = {ret:.1%} | payout implícito = {1-ret:.1%} | caixa/E = {caixa*100:.1f}%")
    if 0.95 <= ret <= 1.0 + 1e-9:
        d.append("[v9.15] payout ≈ 0 ⟹ a RETENÇÃO OBSERVADA é NÃO-INFORMATIVA sobre o RiR "
                 "requerido (camadas do RiR, aplicacao.md §2); confirme o regime da base "
                 "(teorema da base coerente, Gate 0) — base reportada deprimida + RiR 100% é o "
                 "quadrante proibido (dupla contagem do investimento).")
    if abs(caixa) > 1e-9:
        d.append("LIMITAÇÃO DECLARADA (C2): o Ke é INPUT FIXO neste comando — não responde à "
                 "estrutura de capital implícita em GD/E e ND/E, nem à sua deriva ao longo do "
                 "CAP. Comparar cenários com alavancagem/caixa diferentes sob o MESMO Ke atribui "
                 "ao caixa um efeito que em parte é de custo de capital. Para a trilha consistente "
                 "(Ke_t e WACC_t período a período, ancorados em Ku), rode `apv` e realimente o Ke.")
    if tv == 'gordon' and roe_tv is not None and 0 < (ke - gp) < 0.02:
        d.append(f"ALERTA DE SENSIBILIDADE (Ke − gp = {(ke-gp)*100:.2f} p.p.): o TV divide por (Ke − gp); "
                 f"nesta região, ±5 bps em gp movem o valor em dezenas de %. Reporte o valor como "
                 f"intervalo sobre gp, nunca como ponto.")
    if caixa < -1e-9:
        d.append(f"DOMÍNIO: ND/E > GD/E ⟹ caixa/E = {caixa*100:.1f}% NEGATIVO — fora do modelo de "
                 f"balanço declarado (caixa = GD/E − ND/E ≥ 0). Verifique a ordem dos inputs; se a "
                 f"posição líquida é credora de fato, os papéis de GD/E e ND/E estão trocados.")
    if ret > 1:
        d.append("ALERTA: g/ROE > 100% — payout negativo (emissão implícita). EXIGE fonte de funding "
                 "declarada; sem funding plausível, é hipótese diagnóstica FORTE de erro de classificação "
                 "nível→taxa (degrau lançado como g) — a investigar, não veredicto.")
    if roe < ke and g > 0:
        d.append("ALERTA: ROE < Ke com g > 0 — reter lucro destrói valor; P/L FORWARD cai com g "
                 "(na base corrente ele SOBE por reajuste (1+g) — não é criação de valor).")
    if roe < ke and tv == 'book':
        if roe_book is None:
            d.append("ALERTA DE CONFLAÇÃO [B-01]: ROE < Ke na 'book' com o MESMO ROE nos dois papéis. AQUI o "
                     "TV = equity contábil = LL/ROE cresce quando o ROE cai, e a convergência do ROE PARA "
                     "CIMA até o Ke é hipótese criadora de valor não declarada — o P/L justo sobe conforme o "
                     "negócio piora. A perversidade é da CONFLAÇÃO, não da convenção: informe --roe-book com "
                     "a MÉDIA contábil e o TV deixa de acompanhar o marginal. Para spread negativo "
                     "persistente use tv='gordon' com --roe-tv abaixo do Ke.")
        else:
            d.append(f"CONVENÇÃO CONDICIONADA [B-01]: ROE marginal ({roe:.1%}) < Ke ({ke:.1%}) com ROE book "
                     f"informado ({roe_book:.1%}). [v9.30] O TV parte do book e ACUMULA o lucro retido ao "
                     "marginal (a média deriva na direção dele; o eco mostra o médio no ano n) — "
                     "não há perversidade: o P/L acompanha o marginal, como deve. A retenção destrói "
                     "valor no explícito, mas a 'book' permanece ADMISSÍVEL sob tese DECLARADA de saída pelo "
                     "patrimônio (turnaround, capex regulatório, reconstrução operacional, liquidação ou "
                     "venda pelo book). Sem essa tese na entrega, use tv='gordon' com --roe-tv abaixo do Ke.")
            if roe_book < ke:
                d.append(f"SUB-ALERTA [B-01, papel MÉDIO]: ROE book ({roe_book:.1%}) < Ke ({ke:.1%}) ⟹ "
                         f"a âncora inicial do TV (E_0 = LL/ROE_book) excede LL/Ke em {ke/roe_book:.2f}x. A saída pelo patrimônio embute "
                         "RECUPERAÇÃO acima do valor capitalizado de lucros sub-custo — hipótese de "
                         "recuperação, não de continuidade, e exige tese própria. O cruzamento é exato em "
                         "ROE_book = Ke.")
    if abs(roe - ke) < 5e-4:
        if tv == 'book' and roe_book is not None and abs(roe_book - ke) >= 5e-4:
            d.append(f"ATENÇÃO: ROE marginal ≈ Ke mas ROE book = {roe_book:.1%} ≠ Ke — sob 'book' a "
                     f"neutralidade é INCOMPLETA: o TV depende do book inicial (e, com g > 0, da "
                     f"acumulação ao marginal) e o P/L "
                     f"forward NÃO é 1/Ke. Neutralidade completa sob 'book' exige "
                     f"marginal E book iguais ao Ke; Caixa/E é neutro nessa convenção porque o valuation "
                     f"é Div + E_n por clean surplus. Sob 'convergencia'/'gordon' "
                     f"o book não entra no TV e marginal = Ke basta.")
        elif tv == 'book':
            d.append("NEUTRALIDADE [book/clean surplus]: ROE marginal ≈ Ke e ROE book ≈ Ke — P/L "
                     "FORWARD invariante a g (= 1/Ke), independentemente de Caixa/E. O book usa "
                     "dividendos + E_n; caixa retido já está em E_n e não é contado novamente. O "
                     "corrente varia com g apenas por reajuste de base.")
        elif abs(caixa) < 1e-9:
            d.append("NEUTRALIDADE [identidade, condicionada a caixa/E=0]: ROE ≈ Ke — P/L FORWARD "
                     "invariante a g (= 1/Ke) nesta convenção sem book terminal. O corrente varia "
                     "com g por reajuste de base.")
        else:
            d.append(f"ATENÇÃO [módulo FCFE, não-book]: ROE ≈ Ke NÃO é linha de neutralidade com "
                     f"caixa/E = {caixa:.1%}. O termo "
                     f"(GD/E − ND/E)·(g/ROE) do FCFE libera caixa a cada ponto de g, então o P/L forward "
                     f"continua subindo com g mesmo sem spread — este é o MÓDULO DE POLÍTICA de caixa "
                     f"proporcional de gordon/convergencia, não identidade geral. Na `book`, essa "
                     f"liberação não é somada a E_n porque duplicaria caixa.")
    if abs(g) < 1e-6:
        if tv == 'gordon':
            d.append("NEUTRALIDADE: g = 0 na convenção 'gordon' — P/L invariante a ROE "
                     "(o TV referencia ROE_TV, não o ROE do explícito).")
        elif tv == 'convergencia':
            d.append("NEUTRALIDADE: g = 0 na convenção 'convergencia' — P/L invariante a ROE "
                     "(TV = 1/(Ke(1+Ke)^n) não referencia o ROE).")
        else:
            rb = roe_book if roe_book is not None else roe
            tv_share = (1 / (rb * (1 + ke) ** n)) / (sum(1 / (1 + ke) ** t for t in range(1, n + 1)) + 1 / (rb * (1 + ke) ** n))
            d.append(f"ATENÇÃO: g = 0 NÃO torna o P/L invariante a ROE na convenção 'book' com CAP finito. "
                     f"O explícito vale a anuidade, mas o TV = 1/(ROE_book(1+Ke)^n) depende do book. "
                     f"A invariância (= 1/Ke) vale em 'convergencia', na forma perpétua ou com n → ∞ "
                     f"(aqui n = {n}; o TV responde por {tv_share:.1%} do múltiplo neste ROE).")
    return _guardas_damodaran(d, tv, gp, ke, rf=rf, moeda=moeda, rotulo_custo='Ke')

# ---------------- grade de múltiplos (crescimento x rentabilidade) ----------------
def _linha_col(centro, passo, n_lados=5):
    return [centro + (i - n_lados) * passo for i in range(2 * n_lados + 1)]

def grade_ev(w, d, t, n, centro_roic, centro_g, passo_roic=0.01, passo_g=0.02,
             base='forward', tv='book', roic_tv=None, gp=0.0, roic_book=None, mid_year=False):
    cols = [c for c in _linha_col(centro_roic, passo_roic) if c > 0]
    linhas = []
    for g in _linha_col(centro_g, passo_g):
        row = []
        for roic in cols:
            m = ev_ebitda(g, roic, w, n, d, t, tv=tv, roic_tv=roic_tv, gp=gp, roic_book=roic_book,
                          mid_year=mid_year)
            row.append(m / (1 + g) if base == 'forward' else m)
        linhas.append((g, row))
    return cols, linhas

def grade_pe(ke, gde, nde, n, centro_roe, centro_g, passo_roe=0.02, passo_g=0.02,
             base='forward', tv='book', roe_tv=None, gp=0.0, roe_book=None, politica_tv='continua',
             mid_year=False):
    cols = [c for c in _linha_col(centro_roe, passo_roe) if c > 0]
    linhas = []
    for g in _linha_col(centro_g, passo_g):
        row = []
        for roe in cols:
            m = pe(g, roe, ke, n, gde, nde, tv=tv, roe_tv=roe_tv, gp=gp, roe_book=roe_book,
                   politica_tv=politica_tv, mid_year=mid_year)
            row.append(m / (1 + g) if base == 'forward' else m)
        linhas.append((g, row))
    return cols, linhas

def imprime_grade(titulo, col_label, cols, linhas, centro_col, centro_g, custo_capital=None, tv='book'):
    tv = tv_canon(tv)
    print(titulo)
    head = "  g \\ " + col_label + " |" + "".join(f"{c*100:7.1f}%" for c in cols)
    print(head); print("  " + "-" * (len(head) - 2))
    for g, row in linhas:
        mark = " *" if abs(g - centro_g) < 1e-9 else "  "
        cells = "".join((f"[{v:5.2f}]" if abs(cc - centro_col) < 1e-9 and abs(g - centro_g) < 1e-9
                         else f"{v:7.2f}") for cc, v in zip(cols, row))
        print(f"{g*100:5.1f}%{mark}|" + cells)
    if custo_capital is not None:
        abaixo = [c for c in cols if c < custo_capital - 5e-4]
        if abaixo and tv == 'book':
            print(f"  ! Colunas {', '.join(f'{c*100:.1f}%' for c in abaixo)} estão ABAIXO do custo de capital "
                  f"({custo_capital*100:.1f}%): na convenção 'book' os múltiplos altos dessa região refletem "
                  f"book grande + convergência para cima até o custo de capital — NÃO leia como 'rentabilidade "
                  f"baixa justifica múltiplo alto'.")
        if any(abs(c - custo_capital) < 5e-4 for c in cols):
            print(f"  * Coluna ≈ custo de capital: neutralidade exata só na base forward (= {1/custo_capital:.2f} "
                  f"em EV/NOPAT; multiplicar por (1−d)(1−t) ou fator FCFE para o múltiplo exibido).")

# ---------------- normalizacao a dado atual (ponte de alavancagem operacional) ----------------
def normaliza_ebitda(ebitda_base, da, preco_base, preco_novo, vol):
    """Re-base do EBITDA por alavancagem operacional (custo e volume fixos):
    EBITDA(P) = EBITDA_base + Volume * (P_novo - P_base). D&A absoluta fixa => d muda."""
    eb_novo = ebitda_base + vol * (preco_novo - preco_base)
    return eb_novo, da / ebitda_base, da / eb_novo

# ---------------- degrau de nível (capacidade ociosa / re-precificação) ----------------
def fator_h(indice_atual, indice_alvo):
    """Fator de expansão da base geradora com capital/PR constante.
    Índices do tipo 'quanto capital por unidade de exposição' (Basileia, solvência):
    h = índice_atual / índice_alvo."""
    if indice_alvo <= 0:
        return float('nan')
    return indice_atual / indice_alvo

def rentab_pos_degrau(rentab, h, m=1.0):
    """Degrau ENTRA COMO RENTABILIDADE, nunca como g (ver derivacao.md §8).
    m = eficiência marginal do capital liberado (ROA marginal / ROA médio)."""
    return rentab * (1 + (h - 1) * m)

def desconto_transicao(custo_capital, anos, perfil='rampa'):
    """O motor entrega o degrau instantâneo; a realidade leva `anos`.
    O desconto incide SOMENTE sobre o incremento, nunca sobre a base.
    perfil='rampa'   -> deployment linear em tranches anuais ao longo de T anos; T fracionário
                        recebe uma tranche proporcional no último período, sem saltos de arredondamento.
    perfil='pontual' -> o degrau inteiro cai no ano T; só com evento datado
                        (licença, decisão regulatória, fechamento de aquisição)."""
    T = max(anos, 0)
    if T <= 0:
        return 1.0
    if custo_capital <= -1:
        return float('nan')
    if perfil == 'pontual':
        return 1.0 / (1.0 + custo_capital) ** T
    n_full = int(T)
    frac = T - n_full
    numer = sum(1.0 / (1.0 + custo_capital) ** t for t in range(1, n_full + 1))
    if frac > 1e-12:
        numer += frac / (1.0 + custo_capital) ** T
    return numer / T

def valor_transicionado(valor_base, valor_degrau, custo_capital, anos, perfil='rampa'):
    f = desconto_transicao(custo_capital, anos, perfil)
    return valor_base + (valor_degrau - valor_base) * f, f

def classificacao_degrau(g, rentab, custo, n, h, anos, lado='equity',
                         gde=0.0, nde=0.0, **kw):
    """Prova numérica do teorema da classificação (derivacao.md §8).
    Compara os três caminhos e devolve o erro de cada rota errada.
    Múltiplo x rentabilidade = P/VP (equity) ou EV/Capital (firm)."""
    f = (lambda gg, rr: pe(gg, rr, custo, n, gde, nde, **kw)) if lado == 'equity' \
        else (lambda gg, rr: ev_nopat(gg, rr, custo, n, **kw))
    dg = h ** (1.0 / max(anos, 1)) - 1 if anos and anos > 0 else h - 1
    r2 = rentab * h
    correto = f(g, r2) * r2                      # degrau na rentabilidade, g intacto
    so_no_g = f(g + dg, rentab) * rentab         # erro de classificação
    dupla = f(g + dg, r2) * r2                   # erro de dupla contagem
    rir = (g + dg) / rentab if rentab else float('nan')
    return {
        'delta_g_que_o_erro_usaria': round(dg * 100, 2),
        'CORRETO_degrau_na_rentabilidade': round(correto, 4),
        'ERRO_so_no_g': round(so_no_g, 4),
        'ERRO_so_no_g_desvio_%': round((so_no_g / correto - 1) * 100, 1) if correto else None,
        'ERRO_dupla_contagem': round(dupla, 4),
        'ERRO_dupla_contagem_desvio_%': round((dupla / correto - 1) * 100, 1) if correto else None,
        'RiR_implicito_na_rota_errada_%': round(rir * 100, 1),
        'regime': ('rentabilidade < custo de capital — a rota errada INVERTE o sinal do evento'
                   if rentab < custo - 5e-4 else
                   'rentabilidade ≈ custo de capital — a rota errada FAZ O EVENTO DESAPARECER no forward'
                   if abs(rentab - custo) < 5e-4 else
                   'rentabilidade > custo de capital — a rota errada infla o múltiplo sobre base subestimada'),
    }

# ---------------- registro de drivers exógenos ----------------
def elasticidade_exposicao(linha_exposta, metrica_base, sentido='receita'):
    """[D4] Elasticidade DERIVADA e COM SINAL, válida para driver de receita E de custo.
    Com volume e demais linhas fixos no curto prazo, EBITDA = R − C:
      driver de RECEITA (commodity vendida, take-rate, tarifa): +linha_exposta/métrica
      driver de CUSTO   (frete, energia, insumo, câmbio no COGS): −linha_exposta/métrica
    'linha exposta' = a linha da DRE que se move 1-para-1 com o driver (receita do produto,
    ou o custo do insumo), NÃO a receita total. O sinal importa: driver de custo subindo
    DERRUBA a métrica-base, e um gate cego ao sinal soma o que deveria compensar.
    Drivers em direções opostas se compensam — o registro reporta líquido e brutos."""
    if not metrica_base:
        return float('nan')
    el = linha_exposta / metrica_base
    return -el if sentido == 'custo' else el

def elasticidade_operacional(receita_driver, metrica_base):
    """Compat: caso de driver de RECEITA de elasticidade_exposicao (sinal positivo)."""
    return elasticidade_exposicao(receita_driver, metrica_base, 'receita')

def registro_drivers(drivers, limiar=0.10):
    """drivers: dicts {nome, base, spot, elast} ou {nome, base, spot, receita_driver,
    metrica_base} para DERIVAR a elasticidade.
    O GATE dispara pelo IMPACTO = |elast x gap|, não pelo gap: driver com gap grande e
    elasticidade minúscula é irrelevante; gap moderado com elasticidade alta é o que move
    o valor. Só vira CENÁRIO quem passa do limiar E está entre os dois maiores."""
    out = []
    _raw = {}
    for d in drivers:
        gap = (d['spot'] / d['base'] - 1) if d['base'] else float('nan')
        sentido = d.get('sentido', 'receita')
        if d.get('elast') is None and d.get('receita_driver') is not None:
            el = elasticidade_exposicao(d['receita_driver'], d.get('metrica_base'), sentido)
            fonte = (f"DERIVADA = linha exposta ({sentido}) {d['receita_driver']} ÷ "
                     f"métrica-base {d.get('metrica_base')}"
                     + (" x (-1): driver de CUSTO — alta do driver DERRUBA a métrica"
                        if sentido == 'custo' else ""))
        else:
            el = d.get('elast', 1.0)
            fonte = ('declarada — derive sempre que houver linha exposta e métrica-base; '
                     'para driver de custo a elasticidade declarada deve vir NEGATIVA')
        efeito_raw = el * gap
        impacto_raw = abs(efeito_raw)
        _raw[d['nome']] = (efeito_raw, impacto_raw)
        out.append({'nome': d['nome'], 'base': d['base'], 'spot': d['spot'],
                    'sentido': sentido,
                    'gap_%': round(gap * 100, 2), 'elast': round(el, 4),
                    'elast_fonte': fonte,
                    'efeito_liquido_%': round(efeito_raw * 100, 2),
                    'impacto_%': round(impacto_raw * 100, 2)})
    out.sort(key=lambda x: -_raw[x['nome']][1])
    relevantes = [d for d in out if _raw[d['nome']][1] > limiar]
    # [v9.13] o líquido decide o gate AGREGADO — antes ele era calculado, exibido na compensação
    # e IGNORADO pela luz: 6 drivers todos < 10% somando −12,6% devolviam GATE: false (caso FNV,
    # rodada 2 da execução fria). A doutrina já dizia "o líquido decide"; o booleano contradizia.
    liq_raw = sum(_raw[d['nome']][0] for d in out if _raw[d['nome']][0] == _raw[d['nome']][0])
    bruto_raw = sum(_raw[d['nome']][1] for d in out if _raw[d['nome']][1] == _raw[d['nome']][1])
    liq, bruto = liq_raw * 100, bruto_raw * 100
    gate_individual = len(relevantes) > 0
    gate_agregado = abs(liq_raw) > limiar
    gate = gate_individual or gate_agregado
    # seleção de cenário: individuais acima do limiar; se SÓ o agregado disparou, promovem-se os
    # dois maiores contribuintes — o cenário normalizado é obrigatório e precisa de protagonistas
    base_cenario = relevantes if gate_individual else \
        (sorted(out, key=lambda d: -abs(d['impacto_%']))[:2] if gate_agregado else [])
    cenario = {d['nome'] for d in base_cenario[:2]}
    for d in out:
        d['tratamento'] = 'CENÁRIO' if d['nome'] in cenario else 'linha de sensibilidade'
    if gate_individual:
        nota = (f"GATE DISPARADO pelo IMPACTO (|elast x gap| > {limiar*100:.0f}%): "
                + ', '.join(d['nome'] for d in relevantes)
                + ". Obrigatório rodar cenário normalizado ao spot ALÉM do período-base e reverter "
                  "o nível implícito no preço."
                + (f" O líquido AGREGADO ({liq:+.1f}%) também excede o limiar." if gate_agregado else ""))
    elif gate_agregado:
        nota = (f"GATE DISPARADO pelo LÍQUIDO AGREGADO: nenhum driver isolado passou de "
                f"{limiar*100:.0f}%, mas a soma com sinal dos efeitos é {liq:+.1f}% — o período-base "
                f"NÃO é representativo em conjunto. Obrigatório rodar cenário normalizado ao spot "
                f"ALÉM do período-base e reverter o nível implícito no preço; os dois maiores "
                f"contribuintes entram como CENÁRIO.")
    else:
        nota = (f"Nenhum driver com impacto > {limiar*100:.0f}% e líquido agregado ({liq:+.1f}%) "
                "dentro do limiar: o período-base é representativo. Reporte assim mesmo — gaps, "
                "elasticidades e impactos, inclusive os que não passaram.")
    if gate_individual and len(relevantes) > 2:
        nota += (f" ATENÇÃO: {len(relevantes)-2} driver(s) acima do limiar ficaram FORA dos "
                 "cenários pela trava anticombinatória — declare como linha de sensibilidade, "
                 "não omita.")
    comp = {'efeito_liquido_total_%': round(liq, 2), 'soma_dos_brutos_%': round(bruto, 2)}
    if bruto > 1e-9 and abs(liq) < 0.5 * bruto:
        comp['nota_compensacao'] = ('drivers em direções OPOSTAS se compensam: o líquido '
                                    f'({liq:+.1f}%) é bem menor que a soma dos brutos ({bruto:.1f}%). '
                                    'Reporte os DOIS — o líquido decide o gate agregado, os brutos '
                                    'mostram o risco de a compensação não se sustentar (as duas pontas '
                                    'podem descolar).')
    return {'drivers': out, 'GATE': gate, 'GATE_agregado': gate_agregado,
            'criterio': 'impacto = |elasticidade x gap|; a luz dispara por driver OU pelo líquido agregado',
            'compensacao': comp, 'nota': nota}

def nivel_recalculado(alvo_valor, metrica_base, da_absoluta, tax, g, roic, w, n,
                      tv='convergencia', roic_tv=None, gp=0.0, roic_book=None, mid_year=False):
    """[v10.1] Nível implícito com o MÚLTIPLO RECALCULADO a cada iteração — a leitura CENTRAL.

    A leitura congelada (alvo ÷ múltiplo fixo) é LIMITE SUPERIOR quando a D&A absoluta não escala
    com o nível: se a métrica sobe, d = D&A/métrica CAI, o múltiplo justo SOBE e o nível exigido
    pelo preço é MENOR. Aqui a bissecção resolve `múltiplo(d(M)) × M = alvo`.
    Condição de validade declarada: vale para nível vindo de MARGEM ou PREÇO. Se o nível vier de
    VOLUME, a D&A escala com as unidades produzidas, d não cai, e as duas leituras convergem.
    Este número é, por identidade, o BREAK-EVEN da base de lucro contra o alvo informado."""
    if da_absoluta is None or tax is None or metrica_base <= 0:
        return None
    def valor(m):
        if m <= da_absoluta:
            return float('-inf')
        mult = ev_ebitda(g, roic, w, n, da_absoluta / m, tax, tv=tv, roic_tv=roic_tv,
                         gp=gp, roic_book=roic_book, mid_year=mid_year)
        return mult * m if mult == mult else float('nan')
    lo, hi = da_absoluta * 1.0000001, max(metrica_base, alvo_valor) * 50.0
    if valor(hi) < alvo_valor:
        return {'sem_solucao': ('alvo acima do valor atingível mesmo com nível 50x a métrica-base '
                                'ou o alvo — o preço não é explicável por NÍVEL sob este vetor')}
    for _ in range(200):
        mid = (lo + hi) / 2.0
        if valor(mid) < alvo_valor:
            lo = mid
        else:
            hi = mid
    m = (lo + hi) / 2.0
    d_impl = da_absoluta / m
    return {'configuracao_do_triangulo': ('VETOR TRAVADO: g e rentabilidade marginal fixos; apenas o '
                                         'encargo de reposição d = D&A/métrica responde ao nível. Se a '
                                         'rentabilidade TAMBÉM for derivada do nível (intensidade de '
                                         'capital constante), o múltiplo justo sobe mais e o nível '
                                         'exigido cai ainda mais — as três leituras formam uma escada: '
                                         'congelada > vetor travado > rentabilidade derivada.'),
            'metrica_base_implicita_recalculada': round(m, 2),
            'fator_k_recalculado': round(m / metrica_base, 4),
            'degrau_implicito_recalculado_%': round((m / metrica_base - 1) * 100, 1),
            'd_no_nivel_implicito_%': round(d_impl * 100, 2),
            'multiplo_justo_no_nivel_implicito': round(
                ev_ebitda(g, roic, w, n, d_impl, tax, tv=tv, roic_tv=roic_tv, gp=gp,
                          roic_book=roic_book, mid_year=mid_year), 4)}


def nivel_implicito(alvo_valor, multiplo_justo, metrica_base, vol=None, preco_base=None,
                    consenso_t1=None, consenso_t2=None, recalculado=None):
    """Reversa em degrau: que NÍVEL da métrica-base o preço embute, dadas as taxas.
    valor = múltiplo x métrica  =>  métrica_implícita = alvo / múltiplo (leitura CONGELADA).
    [v10.1] Com os parâmetros do vetor, devolve TAMBÉM a leitura RECALCULADA, que é a central."""
    if multiplo_justo <= 0:
        return {'erro': 'múltiplo justo não positivo'}
    mi = alvo_valor / multiplo_justo
    out = {'metrica_base_atual': round(metrica_base, 2),
           'metrica_base_implicita': round(mi, 2),
           'leitura_congelada': ('LIMITE SUPERIOR — o múltiplo foi mantido fixo; com D&A absoluta '
                                 'fixa, o múltiplo justo sobe quando a métrica sobe e o nível '
                                 'realmente exigido é MENOR. Rode a leitura recalculada.'),
           'fator_k_implicito': round(mi / metrica_base, 4) if metrica_base else None,
           'degrau_implicito_%': round((mi / metrica_base - 1) * 100, 1) if metrica_base else None}
    if recalculado:
        out['recalculado'] = recalculado
        out['recalculado_nota'] = ('leitura CENTRAL e, por identidade, o BREAK-EVEN da base de '
                                   'lucro contra o alvo. Vale para nível de margem/preço; se o '
                                   'nível vem de VOLUME, a D&A escala e as duas leituras convergem.')
    # [v9.15] confronto temporal (aplicacao.md §4): antecipação temporal vs hipótese terminal
    if consenso_t1 or consenso_t2:
        if consenso_t1:
            out['razao_vs_consenso_t1'] = round(mi / consenso_t1, 4)
        if consenso_t2:
            out['razao_vs_consenso_t2'] = round(mi / consenso_t2, 4)
        ref = max(x for x in (consenso_t1, consenso_t2) if x)
        if mi <= ref * 1.25:
            out['leitura'] = ('antecipacao_temporal: métrica implícita ≤ 125% do consenso '
                              't+1/t+2 — o mercado desconta uma base futura; a reversa correta '
                              'é sobre o vetor consenso (rev --resolver cap contra a base '
                              'futura = horizonte implícito de mercado), NÃO conclusão de '
                              'fantasia terminal.')
        else:
            out['leitura'] = ('acima_do_consenso: métrica implícita excede o consenso t+1/t+2 '
                              'em mais de 25% — a hipótese terminal está no preço; siga para o '
                              'teto do crescimento gratuito e o gp implícito (protocolo v9.13).')
    if vol and preco_base is not None:
        ajuste = (mi - metrica_base) / vol
        out['preco_driver_implicito'] = round(preco_base + ajuste, 4)
        out['nota'] = ('Compare o preço implícito com o SPOT: é a única variável implícita '
                       'do framework com observável de mercado direto.')
        # [v9.14 / rodada 3, §13.4] este comando mantém o MÚLTIPLO fixo. A dupla alavanca (§7 da
        # aplicacao) diz que nível maior ⟹ d = D&A/EBITDA CAI ⟹ o próprio múltiplo justo SOBE —
        # logo o preço de driver necessário é MENOR que o daqui. Na rodada 3 da execução fria a
        # diferença foi 11% (15.240 vs 13.495). Nota declaratória; a versão iterativa é roadmap.
        out['nota_dupla_alavanca'] = (
            'o múltiplo justo foi mantido FIXO nesta reversa. Com a dupla alavanca (nível maior '
            '⟹ d cai ⟹ múltiplo justo sobe), o preço de driver que reconcilia o alvo é MENOR — '
            'este número é o LIMITE SUPERIOR. Para o valor exato, re-derive d no nível implícito '
            'e itere (bisseção sobre o motor), ou trate a diferença como margem conservadora.')
        # [v9.12/S-1] `vol` TEM que estar na mesma escala da métrica-base. Fora de escala, o ajuste
        # sai desprezível e o preço implícito volta ≈ ao base — resultado com cara de achado ("o
        # preço implícito é o preço de hoje"), não erro. Mesma classe do defeito de portabilidade
        # da v9.9. A assinatura é degrau MATERIAL com ajuste DESPREZÍVEL (ou absurdo, na direção
        # oposta); as duas condições juntas, para não confundir com "o mercado não embute degrau",
        # onde o ajuste é pequeno porque o NUMERADOR é pequeno.
        degrau_rel = abs(mi / metrica_base - 1) if metrica_base else 0.0
        ajuste_rel = abs(ajuste) / abs(preco_base) if preco_base else float('inf')
        if degrau_rel > 0.01 and (ajuste_rel < 1e-3 or ajuste_rel > 100):
            comportamento = ('DESPREZÍVEL (o preço implícito volta ≈ ao preço base)'
                             if ajuste_rel < 1e-3 else 'ABSURDO (ordens de grandeza acima da base)')
            out['aviso_escala'] = (
                f"ESCALA INCOERENTE de --vol: o degrau da métrica é MATERIAL ({degrau_rel*100:.1f}%), "
                f"mas o ajuste de preço é {comportamento} — {ajuste:.6g} contra base {preco_base:g}. "
                f"O volume precisa estar na MESMA escala da métrica-base: métrica em milhões exige "
                f"volume em MILHÕES de unidades (métrica em US$ MM com volume em onças devolve "
                f"preço implícito ≈ preço base, que parece resultado e não é). Reveja a unidade "
                f"antes de ler o preço implícito.")
    return out

# ---------------- APV dinâmico (recursão backward, portado da planilha vF8) ----------------
def apv_recursao(fcff1, g, n, ku, kd, tax, d0, fcff_tv=None, gtv=0.0, conv='mm'):
    """Recursão backward da planilha vF8 (bloco 'Consistência Ke↔WACC — APV').
    Âncora única em Ku; Ke_t e WACC_t são OUTPUTS período a período.
    conv='mm': dívida determinística, shields descontados a Kd (MM/Myers/Fernández).
    conv='ku': shields descontados a Ku sobre a trajetória EXÓGENA de dívida do motor
    (D_t = D0(1+g)^t). O nome descreve o MECANISMO implementado, não uma teoria: é a
    convenção de RISCO dos shields de Harris-Pringle aplicada a uma política de dívida
    exógena. NÃO é Harris-Pringle completo — HP exige D_t = L×V_t com D/V constante, e aqui
    D/V DERIVA (a série vai no output em DV_t_%: na âncora do selftest vai de 18,75% a
    36,28%). HP verdadeiro (com a circularidade D=L×V resolvida) é roadmap planilha-primeiro,
    assim como Miles-Ezzell verdadeiro (primeiro shield a Kd, posteriores a Ku, Fernández).
    'hp' e 'me' NÃO são aliases numéricos: desde v9.28 retornam erro explícito porque
    Harris-Pringle e Miles-Ezzell exigem políticas de dívida próprias.
    Terminal: Vu_n = FCFF_TV/(Ku−gtv); dívida cresce a gtv no terminal.
    Devolve a trilha completa + checks de reconciliação FCFE@Ke_t = E0 e FCFF@WACC_t = V0."""
    if conv not in ('mm', 'ku'):
        return {'erro': f"convenção APV '{conv}' não implementada. Use 'mm' ou 'ku'. "
                        "Miles-Ezzell e Harris-Pringle exigem políticas de dívida próprias; "
                        "não são aliases numéricos."}
    if g <= -1 or gtv <= -1:
        return {'erro': 'requer g > -100% e gtv > -100%'}
    if ku - gtv <= 0 or n < 1:
        return {'erro': 'requer Ku > gtv e n >= 1'}
    fcff = [fcff1 * (1 + g) ** (t - 1) for t in range(1, n + 1)]
    ftv = fcff_tv if fcff_tv is not None else fcff[-1] * (1 + g)
    D = [d0 * (1 + g) ** t for t in range(0, n + 1)]
    shields = [tax * kd * D[t - 1] for t in range(1, n + 1)]
    sh_tv = tax * kd * D[n]
    r_vts = kd if conv == 'mm' else ku
    if r_vts - gtv <= 0:
        return {'erro': 'requer taxa de desconto dos shields > gtv'}
    Vu = [0.0] * (n + 1); VTS = [0.0] * (n + 1)
    Vu[n] = ftv / (ku - gtv)
    VTS[n] = sh_tv / (r_vts - gtv)
    for t in range(n - 1, -1, -1):
        Vu[t] = (Vu[t + 1] + fcff[t]) / (1 + ku)          # fcff[t] é o fluxo do período t+1
        VTS[t] = (VTS[t + 1] + shields[t]) / (1 + r_vts)
    V = [Vu[t] + VTS[t] for t in range(n + 1)]
    E = [V[t] - D[t] for t in range(n + 1)]
    if any(e <= 0 for e in E):
        return {'erro': 'equity a mercado <= 0 em algum período — recursão inválida com esta dívida'}
    fcfe = [fcff[t - 1] - kd * D[t - 1] * (1 - tax) + (D[t] - D[t - 1]) for t in range(1, n + 1)]
    # Ke_t pela DINÂMICA DE VALOR (sempre consistente): Ke_t = (E_t + FCFE_t)/E_{t-1} − 1
    ke_t = [(E[t] + fcfe[t - 1]) / E[t - 1] - 1 for t in range(1, n + 1)]
    # Ke_t pela fórmula de Fernández (só MM): Ku + (D−VTS)(Ku−Kd)/E — Check 5
    ke_f = [ku + (D[t - 1] - VTS[t - 1]) * (ku - kd) / E[t - 1] for t in range(1, n + 1)]
    wacc_t = [(E[t - 1] * ke_t[t - 1] + D[t - 1] * kd * (1 - tax)) / V[t - 1] for t in range(1, n + 1)]
    # Reconciliações (Checks 4 e 6 da planilha)
    dfe = dff = 1.0; e_pv = v_pv = 0.0
    for t in range(1, n + 1):
        dfe /= (1 + ke_t[t - 1]); dff /= (1 + wacc_t[t - 1])
        e_pv += fcfe[t - 1] * dfe; v_pv += fcff[t - 1] * dff
    e_pv += E[n] * dfe; v_pv += V[n] * dff
    chk4 = e_pv - E[0]; chk5 = max(abs(a - b) for a, b in zip(ke_t, ke_f)) if conv == 'mm' else None
    chk6 = v_pv - V[0]
    dv = [D[t] / V[t] for t in range(n + 1)]
    return {'convencao': ('MM — dívida determinística, shields a Kd' if conv == 'mm'
                          else 'Ku — shields a Ku sobre dívida EXÓGENA D_t = D0(1+g)^t '
                               '(convenção de risco de Harris-Pringle; D/V NÃO é mantido constante)'),
            'Vu0': round(Vu[0], 6), 'VTS0': round(VTS[0], 6),
            'V0': round(V[0], 6), 'E0': round(E[0], 6), 'D0': d0,
            'Ke_t_%': [round(k * 100, 4) for k in ke_t],
            'WACC_t_%': [round(w * 100, 4) for w in wacc_t],
            'DV_t_%': [round(x * 100, 4) for x in dv],
            'nota_DV': ('a alavancagem a MERCADO é OUTPUT, não alvo: a dívida segue a trajetória '
                        f'exógena D_t = D0(1+g)^t e o D/V vai de {dv[0]*100:.2f}% a {dv[-1]*100:.2f}% '
                        f'({(max(dv)-min(dv))*100:.2f} p.p. de amplitude). Nenhum regime deste motor '
                        'mantém D/V constante — se a tese exige alavancagem-alvo, ela NÃO está sendo '
                        'imposta aqui.'),
            'check_FCFE_at_Ke_t_igual_E0': round(chk4, 9),
            'check_Ke_dinamico_igual_formula_Fernandez': (round(chk5, 12) if chk5 is not None
                                                          else 'n/a (regime ku — a fórmula de '
                                                               'Fernández só vale sob MM)'),
            'check_FCFF_at_WACC_t_igual_V0': round(chk6, 9),
            'convencao_fluxo_transicao_C7': ('FCFF_{n+1} usa a taxa explícita g por default; gtv rege a perpetuidade. '
                                             'Se a estabilidade começar já em n+1, informe --fcff-tv explicitamente.'),
            'FCFF_n': round(fcff[-1], 6), 'FCFF_n1_usado_no_TV': round(ftv, 6),
            'g_transicao_%': round(g * 100, 4), 'gtv_%': round(gtv * 100, 4),
            'efeito_C7_alternativa_gtv_em_n1_%': round((((fcff[-1] * (1 + gtv) - ftv) / (ku - gtv))
                                                       / (1 + ku) ** n) / V[0] * 100, 4) if V[0] else None,
            'nota': ('Ke e WACC variam no tempo porque a alavancagem a MERCADO deriva. Um WACC único '
                     'aplicado a todos os períodos é inconsistente com a própria trilha — use a série. '
                     'O comando kewacc continua disponível como sanity check ESTÁTICO de perpetuidade.')}

# ---------------- selftest ----------------
ANCHORS = dict(g=0.11, roic=0.3435157894736844, w=0.18733157894736852, n=10,
               d=0.06666666666666651, t=0.30,
               roe=0.4482692307692308, ke=0.22, gde=0.5384615384615384, nde=0.4615384615384615)
def _equity_book_end(ni0, g, roe_marg, roe_book, n):
    """[v9.30] Patrimônio contábil ao fim de n períodos sob clean surplus.

    E0 = NI1/ROE_book e ΔE_t = (g/ROE_marg)·NI_t. É o state variable que deve
    atravessar fases; reestimar E como NI/ROE_book no corte congela indevidamente o retorno médio.
    """
    if roe_marg <= 0 or roe_book <= 0 or g <= -1 or n < 0:
        return float('nan')
    return ni0 * ((1 + g) * (1.0 / roe_book - 1.0 / roe_marg)
                  + (1 + g) ** (n + 1) / roe_marg)


def _pe2_book(g1, roe1, ke1, n1, gde1, nde1, g2, roe2, ke2, n2, gde2, nde2,
              kd, tax, rb1=None):
    """[v9.30] Bifásico `book` por unidade de NI0, com E como variável de estado.

    Fase 1 e fase 2 são valorizadas por dividendos + patrimônio terminal (clean surplus).
    O patrimônio ao corte é ACUMULADO a partir do ROE book inicial e do ROE marginal da fase 1;
    não é reestimado como NI/ROE_book. Caixa/E não entra nos dividendos do `book` — o caixa retido
    já está dentro de E. A única transferência financeira separada é a ponte discreta de releveraging.
    rb1 ausente mantém a hipótese conflacionada book=marginal, mas sem congelar o state variable.
    """
    rbb = rb1 if (rb1 is not None and abs(rb1) > 1e-12) else roe1
    razao = (1 + nde1) / (1 + nde2)

    def anu(g, ke, n):
        return n * 1.0 if abs(ke - g) < 1e-9 else \
            (1 + g) * (1 - ((1 + g) / (1 + ke)) ** n) / (ke - g)

    # Fase 1: DDM sob clean surplus.
    f1 = (1 - g1 / roe1) * anu(g1, ke1, n1)
    e_pre = _equity_book_end(1.0, g1, roe1, rbb, n1)

    # Fase 2 preserva DOIS estados: patrimônio acumulado e nível de lucro. A semântica histórica
    # da ponte rebaseia o primeiro lucro da fase 2 por (ROE2/ROE1)·razao; o book separado NÃO
    # pode substituir ROE1 por ROE_book nessa relação. Assim, quando as fases são idênticas, o
    # corte artificial não muda a trajetória de NI.
    ni1_next = (1 + g1) ** (n1 + 1)  # NI_{n1+1} na base NI0=1
    K = ni1_next * razao / (roe1 * (1 + g2) * (1 + ke1) ** n1)
    A2 = anu(g2, ke2, n2)
    f2 = K * A2 * (roe2 - g2)

    ponte = (e_pre / (1 + ke1) ** n1 / (1 + ke2)
             * (gde2 * razao - gde1) * (1 + kd * (1 - tax)))
    # E terminal é STATE VARIABLE: parte de E_pre·razao e soma retenção da fase 2. Não é
    # reestimado como NI/ROE2. Como NI2_1 = NI1_next·razao·ROE2/ROE1, o ROE2 cancela da
    # acumulação do book, mas continua determinando os dividendos da fase 2.
    e2_start = e_pre * razao
    e2_end = e2_start + (ni1_next * razao / roe1) * ((1 + g2) ** n2 - 1)
    tv = e2_end / (1 + ke1) ** n1 / (1 + ke2) ** n2
    return {'f1': f1, 'K': K, 'A2': A2, 'f2': f2, 'ponte': ponte, 'tv_desc': tv,
            'total': f1 + f2 + ponte + tv, 'alpha2': 1.0, 'razao': razao,
            'E_pre': e_pre, 'E2_start': e2_start, 'E2_end': e2_end,
            'NI2_1': ni1_next * razao * roe2 / roe1}


def iso_curva(lado, alvo, custo, n, grade_g, tv='book', gde=0.0, nde=0.0,
              rent_tv=None, gp=0.0, politica_tv='continua', tol=1e-6,
              rent_book=None, transicao='nenhuma', ponte_params=None):
    """Curva iso-valor (v9.1): grade de pares (g, rentabilidade) que reconciliam o MESMO
    múltiplo-alvo. Mecânica validada na planilha vF8.1 (aba Iso-Valor, prova por fluxos
    explícitos, checks = 0; reconciliação com a aba Logic a ~2e-15).

    Sob 'book' o múltiplo é LINEAR em 1/rentabilidade e a inversão é FECHADA. [v9.30]
    O book equity é DDM + patrimônio terminal, portanto α_book = 1 também no lado pe: caixa/E
    não cria valor por si só e não entra na inversão. Conflacionado:
    M = S + (B − g·S)/rent. Com book separado, nos dois lados:
    M = S + B1/rb + (B − B1 − g·S)/rent, B1 = (1+g)/(1+custo)^n.
    Sob 'convergencia'/'gordon' a inversão usa a bissecção do motor (solve) sobre pe/ev.
    Fora de `book`, o lado pe continua usando o módulo FCFE com α = 1−(gde−nde); no `book`,
    α_book = 1 nos dois lados. Cada ponto é VERIFICADO re-avaliando o múltiplo no motor —
    |M(g, rent*) − alvo| < tol ou o ponto sai marcado."""
    tv = tv_canon(tv)
    # [v9.31] O metadado reporta o coeficiente efetivamente usado: na `book`, clean surplus
    # implica alpha_book = 1 também no equity; fora dela, o FCFE mantém 1-(GD/E-ND/E).
    alpha = 1.0 if tv == 'book' else ((1 - (gde - nde)) if lado == 'pe' else 1.0)
    avisos = []
    comp = {'transicao': transicao}
    if transicao == 'ponte':
        if rent_book is not None:
            raise SystemExit("iso --transicao ponte: --rent-book pertence ao regime único e não entra no bifásico. "
                             "Use --pt-roe1-book para o book médio da fase 1. ROE2_book separado não é "
                             "implementado nesta versão; aceitar --rent-book aqui seria um input silenciosamente ignorado.")
        if lado != 'pe':
            raise SystemExit("iso: --transicao ponte só está definida no lado pe (a ponte é objeto de equity).")
        if not ponte_params:
            raise SystemExit("iso: --transicao ponte exige os parâmetros do regime 1 "
                             "(--pt-n1 --pt-ke1 --pt-gde1 --pt-nde1 --pt-kd --pt-tax --pt-g1 e "
                             "--pt-roe1 [--pt-roe1-book] ou --pt-equity). O motor calcula o PV — "
                             "nunca transcreva a ponte à mão.")
        if tv_canon(tv) != 'book':
            raise SystemExit("iso --transicao ponte: a inversão bifásica fechada está derivada "
                             "para a convenção book (TV = equity contábil, independente de ROE₂), "
                             "condicionada à convenção de rebase do primeiro lucro. "
                             "Bifásico com gordon/convergencia entra com o pe2 (roadmap).")
        pk = dict(ponte_params)
        if pk.get('equity') is not None:
            raise SystemExit("iso --transicao ponte: --pt-equity é monetário, enquanto --alvo é múltiplo por NI0. "
                             "Sem uma base NI0 explícita, misturar as escalas é inconsistente. Use "
                             "--pt-roe1 e --pt-roe1-book para a inversão em múltiplos; --equity permanece "
                             "suportado no comando `ponte` standalone.")
        if pk.get('roe1') is None:
            raise SystemExit("iso --transicao ponte (v9.3): --pt-roe1 é obrigatório — a anuidade da "
                             "fase 1 exige o ROE marginal do regime 1 (--pt-equity sozinho não basta).")
        pt = ponte_releveraging(n1=pk['n1'], ke1=pk['ke1'], ke2=custo,
                                gde1=pk['gde1'], nde1=pk['nde1'], gde2=gde, nde2=nde,
                                kd=pk['kd'], tax=pk['tax'], g1=pk['g1'],
                                roe1=pk.get('roe1'), equity=pk.get('equity'),
                                roe1_book=pk.get('roe1_book'))
        comp.update(alvo_cheio=alvo, PV_ponte=pt['PV_ponte'],
                    composicao=('ponte nula: estrutura igual nos dois regimes'
                                if abs(pt['delta_estrutura']) < 1e-12 else
                                'FECHADA E CONDICIONAL — inversão bifásica (book, sem fade; E é state variable): '
                                'o valor total é linear em ROE₂; f1, ponte e TV acumulado são removidos com os '
                                'parâmetros declarados e ROE₂* sai por divisão, verificado re-avaliando '
                                'o bifásico completo em cada ponto. ROE₂* é condicionado ao rebase NI2_1=NI1_next·(ROE2/ROE1)·razão; '
                                'não é identificação estrutural pura do marginal'),
                    diagnosticos_ponte=pt['diagnosticos'])
        if pk.get('roe1_book') is None and pk.get('equity') is None:
            avisos.append("ATENÇÃO (conflação marginal×médio no regime 1): sem --pt-roe1-book, a âncora "
                          "de equity da fase 1 (E = NI/ROE) usa o marginal como proxy do médio — "
                          "propaga para f1 não, mas para ponte, K e TV sim.")
    elif transicao != 'nenhuma':
        raise SystemExit("iso: --transicao deve ser 'nenhuma' (regime único declarado) ou 'ponte'.")
    if transicao == 'nenhuma' and tv == 'book' and rent_book is None:
        avisos.append("ATENÇÃO (conflação marginal×médio, P6.11): sem --rent-book, a inversão usa a "
                      "MESMA rentabilidade nos dois papéis — marginal (retenção) e média contábil (TV). "
                      "Se diferem, a rentabilidade implícita pode sair materialmente distorcida e gerar "
                      "raízes sem sentido. Informe --rent-book com a média do estoque.")
    curva = []
    for g in grade_g:
        pt = {'g_%': g * 100}
        if transicao == 'ponte':
            pk = ponte_params
            base = _pe2_book(pk['g1'], pk['roe1'], pk['ke1'], pk['n1'], pk['gde1'], pk['nde1'],
                             g, 1.0, custo, n, gde, nde, pk['kd'], pk['tax'],
                             rb1=pk.get('roe1_book'))
            den = base['K'] * base['A2']
            residuo = alvo - base['f1'] - base['ponte'] - base['tv_desc']
            if abs(den) < 1e-12:
                pt.update(rent_implicita=None,
                          diagnostico='K·A₂ ≈ 0: a rentabilidade do regime 2 não entra no valor neste '
                                      'ponto — não identificável')
                curva.append(pt); continue
            rent = residuo / den + g
            p = dict(pt)
            m = _pe2_book(pk['g1'], pk['roe1'], pk['ke1'], pk['n1'], pk['gde1'], pk['nde1'],
                          g, rent, custo, n, gde, nde, pk['kd'], pk['tax'],
                          rb1=pk.get('roe1_book'))['total']
            check = m - alvo
            rir = g / rent if rent else float('inf')
            if rent <= 0:
                diag = ('incompatível neste g — ou o alvo é irreconciliável com os regimes declarados, '
                        'ou a COMPOSIÇÃO está mal-posta (parâmetros da fase 1 errados distorcem o resíduo)')
            elif rent < custo:
                diag = ('marginal < custo no regime 2: retenção destrói valor. O TV book carrega o '
                        'patrimônio acumulado como state variable; a convenção continua admissível '
                        'somente sob tese declarada de saída pelo book. Para spread negativo persistente '
                        'sem essa tese, use gordon quando o pe2 correspondente existir.')
            elif rir > 1:
                diag = 'RiR > 100% no regime 2: exige fonte de funding declarada'
            else:
                diag = 'ok'
            p.update(rent_implicita_pct=rent * 100, RiR_pct=round(rir * 100, 2),
                     diagnostico=diag,
                     residuo_fase2=residuo,
                     check_multiplo=(check if abs(check) >= tol else 0.0))
            if abs(check) >= tol:
                p['diagnostico'] += ' | ATENÇÃO: re-avaliação do bifásico divergiu da inversão'
            curva.append(p)
            continue
        if tv == 'book':
            S = n if abs(custo - g) < 1e-9 else (1 + g) * (1 - ((1 + g) / (1 + custo)) ** n) / (custo - g)
            B = (1 + g) ** (n + 1) / (1 + custo) ** n
            if rent_book is not None:
                # [v9.30] papéis separados com capital/patrimônio ACUMULADO. No `book` equity,
                # clean surplus implica dividendos + E_n; logo caixa/E não entra e α_book = 1.
                B1 = (1 + g) / (1 + custo) ** n
                num = B - B1 - g * S
                den = alvo - S - B1 / rent_book
                if abs(num) < 1e-12:
                    pt.update(rent_implicita=None,
                              diagnostico='coeficiente de 1/rent ≈ 0 (g ≈ 0): a rentabilidade MARGINAL não '
                                          'entra no múltiplo e não é identificável neste g (só a média, via TV)')
                    curva.append(pt); continue
                if abs(den) < 1e-9:
                    pt.update(rent_implicita=None,
                              diagnostico='alvo ≈ S + B1/rent_book: variável não identificada — ruído com cara de precisão')
                    curva.append(pt); continue
                rent = num / den
            else:
                if abs(alvo - S) < 1e-6:
                    pt.update(rent_implicita=None,
                              diagnostico='alvo ≈ piso S(g): variável não identificada — ruído com cara de precisão')
                    curva.append(pt); continue
                rent = (B - g * S) / (alvo - S)
            rents = [rent]
        else:
            fmult = (lambda x: pe(g, x, custo, n, gde, nde, tv=tv, roe_tv=rent_tv, gp=gp,
                                  politica_tv=politica_tv)) if lado == 'pe' else \
                    (lambda x: ev_nopat(g, x, custo, n, tv=tv, roic_tv=rent_tv, gp=gp))
            rents = solve(lambda x: fmult(x) - alvo, 1e-4, 3.0)
            if not rents:
                pt.update(rent_implicita=None,
                          diagnostico='sem raiz em (0, 300%] neste g — taxonomia P6.4/P6.7: alvo acima do '
                                      'supremo da convenção, ou tangente ao extremo (bisseção não vê), ou '
                                      'g incompatível com o alvo nesta convenção')
                curva.append(pt); continue
        for rent in rents:
            p = dict(pt)
            if rent > 0:
                m = pe(g, rent, custo, n, gde, nde, tv=tv, roe_tv=rent_tv, gp=gp,
                       politica_tv=politica_tv, roe_book=rent_book) if lado == 'pe' else \
                    ev_nopat(g, rent, custo, n, tv=tv, roic_tv=rent_tv, gp=gp, roic_book=rent_book)
                check = m - alvo
            else:
                check = None  # fora do domínio econômico: verificação não se aplica
            rir = g / rent if rent else float('inf')
            if rent <= 0:
                diag = 'incompatível neste g (rentabilidade não positiva)'
            elif tv == 'book' and rent < custo:
                if rent_book is None:
                    diag = ('conflação marginal×médio no TV: com o MESMO retorno nos dois papéis o TV '
                            'cresce quando o retorno cai — informe o book (--roic-book/--roe-book) ou '
                            'declare gordon com spread negativo')
                else:
                    if lado == 'ev':
                        diag = ('CONDICIONADA: marginal < custo com book informado — o TV parte do book inicial, '
                                'mas acompanha o marginal pelo capital novo acumulado; não há convergência implícita '
                                'para cima. Admissível sob tese DECLARADA de saída pelo capital investido')
                    else:
                        diag = ('CONDICIONADA: marginal < custo com book informado — o TV parte do book '
                                'inicial e acumula o lucro retido ao marginal; na book o fluxo é dividendo '
                                'e Caixa/E é neutro. Admissível sob tese DECLARADA de saída pelo patrimônio')
                    if rent_book < custo:
                        diag += (f' | SUB-ALERTA: book ({rent_book:.1%}) < custo ({custo:.1%}) — o TV '
                                 f'embute recuperação {custo/rent_book:.2f}x acima do valor capitalizado '
                                 f'a custo de capital')
                    if rir > 1:
                        diag += ' | RiR > 100%: exige fonte de funding declarada'
            elif rir > 1:
                diag = 'RiR > 100%: exige fonte de funding declarada'
            else:
                diag = 'ok'
            p.update(rent_implicita_pct=rent * 100, RiR_pct=round(rir * 100, 2),
                     diagnostico=diag,
                     check_multiplo=(None if check is None else
                                     (check if abs(check) >= tol else 0.0)))
            if check is not None and abs(check) >= tol:
                p['diagnostico'] += ' | ATENÇÃO: verificação do motor divergiu do fechado'
            curva.append(p)
    out_extra = {}
    if avisos: out_extra['avisos'] = avisos
    if transicao != 'nenhuma' or comp.get('PV_ponte') is not None:
        out_extra['composicao_transicao'] = comp
    else:
        out_extra['premissa_regime'] = ('REGIME ÚNICO DECLARADO (--transicao nenhuma): sem evento de '
                                        'estrutura de capital datado no horizonte. Se houver, rode com '
                                        '--transicao ponte — o motor compõe o alvo líquido.')
    # [v9.14 / rodada 3 FNV] grade INTEIRA sem raiz é o silêncio mais perigoso do iso: "sem raiz
    # NESTE intervalo" não é "sem raiz", e a rodada 3 entregou "não existe combinação" com a
    # fronteira começando logo fora do intervalo varrido (g≈8% contra g-max de 7%). Mesmo padrão
    # do `sugestao` do rev (v9.13): varredura grosseira aponta onde a fronteira começa.
    if curva and all(p.get('rent_implicita_pct') is None for p in curva):
        g_lo = max(min(grade_g), -0.5)
        fmult_g = (lambda g, x: pe(g, x, custo, n, gde, nde, tv=tv, roe_tv=rent_tv, gp=gp,
                                   politica_tv=politica_tv)) if lado == 'pe' else \
                  (lambda g, x: ev_nopat(g, x, custo, n, tv=tv, roic_tv=rent_tv, gp=gp))
        g_inicio = None
        if transicao == 'nenhuma':
            g_scan = max(grade_g) + 0.005
            while g_scan <= 0.40:
                if solve(lambda x: fmult_g(g_scan, x) - alvo, 1e-4, 3.0):
                    g_inicio = g_scan
                    break
                g_scan += 0.005
        base = (f"NENHUMA raiz no intervalo varrido [g {g_lo*100:.1f}%–{max(grade_g)*100:.1f}%] — "
                f"isso NÃO significa que não exista combinação: a fronteira pode existir FORA do "
                f"intervalo. Amplie antes de concluir.")
        out_extra['sugestao'] = (base + (f" Varredura grosseira: a fronteira COMEÇA em g ≈ "
                                         f"{g_inicio*100:.1f}% — re-rode a grade a partir daí (e "
                                         f"leia o RiR de cada ponto: g alto cobra funding)."
                                         if g_inicio is not None else
                                         " Varredura grosseira até g = 40%: nenhuma raiz — o alvo "
                                         "parece de fato inalcançável nesta convenção; investigue "
                                         "nível/degrau ausente da métrica-base e a convenção antes "
                                         "do preço."))
    return {**out_extra, 'lado': lado, 'tv': tv, 'alvo': alvo,
            ('ke_%' if lado == 'pe' else 'wacc_%'): custo * 100, 'n': n,
            'alpha': alpha, 'curva': curva,
            'LEITURA': 'a curva converte "está barato?" em "qual dos dois vetores o mercado '
                       'não está pagando?" — o mercado paga por um, raramente pelos dois. '
                       'Pontos fora do ramo "ok" são raízes CONDICIONADAS — a condição (funding '
                       'declarado, tese de saída pelo capital investido, conflação a resolver) vai '
                       'junto do número na entrega, nunca implícita.'}


def ponte_releveraging(n1, ke1, ke2, gde1, nde1, gde2, nde2, kd, tax, g1,
                       roe1=None, ni=None, equity=None, kd1=None, pl_base=None, roe1_book=None):
    """Ponte de releveraging (v9): precifica a MUDANÇA DISCRETA de estrutura de capital
    entre dois regimes (fase 1 -> fase 2) como fluxo único ao acionista no ano n1+1.
    Derivada e validada contra a planilha vF19 do usuário (checks ~1e-13); no caso
    degenerado (estrutura igual) a ponte é identicamente zero e o bifásico colapsa no `pe`.

    fluxo = E_pre · (GD/E₂·razão − GD/E₁) · (1 + Kd_at)
      razão = (1+ND/E₁)/(1+ND/E₂)  — rebase do equity quando o caixa líquido relativo muda
      E_pre = equity ao fim da fase 1, na base da fase 1
      (1+Kd_at): ajuste de timing de um ano de juros após impostos sobre a Δdívida
    Base de E_pre: --equity (E0 hoje: E_pre = E0·(1+g1)^n1, convenção standalone existente)
    OU base-lucro. [v9.30] Na base-lucro, se --roe1-book é informado, E_pre é ACUMULADO por
    clean surplus com ROE marginal; não é reestimado como NI/ROE_book no corte.
    """
    kd_at = kd * (1 - tax)
    kd1 = kd if kd1 is None else kd1
    razao = (1 + nde1) / (1 + nde2)
    aviso_conflacao = None
    if equity is not None:
        e_pre = equity * (1 + g1) ** n1
        base = 'equity'
    elif roe1 is not None and abs(roe1) > 1e-12:
        ni0 = 1.0 if ni is None else ni
        rb1 = roe1_book if (roe1_book is not None and abs(roe1_book) > 1e-12) else roe1
        e_pre = _equity_book_end(ni0, g1, roe1, rb1, n1)
        base = 'lucro (NI0=%s, ROE %s)' % ('1 — PV lê-se como Δ P/L' if ni is None else ni,
                                           'book' if roe1_book is not None else 'marginal como proxy de book')
        if roe1_book is None:
            aviso_conflacao = ("ATENÇÃO (conflação marginal×médio, P6.11): sem --roe1-book, E_pré parte "
                               "de E0 = NI1/ROE1 e acumula ao mesmo ROE marginal — hipótese book=marginal. "
                               "Se a média inicial difere, informe --roe1-book.")
    else:
        raise SystemExit("ponte: informe --equity OU --roe1 (com --ni opcional) para ancorar E_pre.")
    delta_estrutura = gde2 * razao - gde1
    fluxo = e_pre * delta_estrutura * (1 + kd_at)
    pv = fluxo / ((1 + ke1) ** n1 * (1 + ke2))

    # Ku implícito por fase (MM estático, pesos D/E dados) — vigia do C2
    def ku_mm(ke, kdx, de):
        return (ke + kdx * (1 - tax) * de) / (1 + (1 - tax) * de)
    ku1, ku2 = ku_mm(ke1, kd1, gde1), ku_mm(ke2, kd, gde2)

    diag = []
    if abs(delta_estrutura) < 1e-12:
        diag.append("COLAPSO: estrutura igual nas duas fases (GD/E₂·razão = GD/E₁) — ponte "
                    "identicamente zero; o caso é monofásico, use `pe` direto.")
    else:
        diag.append(("RELEVERAGING: dívida levantada vai ao acionista (fluxo positivo)."
                     if fluxo > 0 else
                     "DELEVERAGING: o acionista financia a amortização (fluxo negativo) antes "
                     "de ver o primeiro dividendo do regime novo."))
    diag.append(f"[C2 — OBRIGATÓRIO] Ke1/Ke2 são INPUTS FIXOS. Ku implícito (MM estático): "
                f"fase 1 {ku1*100:.2f}% vs fase 2 {ku2*100:.2f}%"
                + (f" — GAP de {abs(ku1-ku2)*100:.2f} p.p.: o risco do negócio desalavancado "
                   f"muda entre fases sem declaração. Ou justifique o de-risking, ou derive os "
                   f"Ke de um Ku único via `apv`. Ponte com Ke inconsistente atribui à dívida "
                   f"valor que é de custo de capital (MM): o efeito líquido real é só o tax shield."
                   if abs(ku1 - ku2) > 0.005 else
                   " — consistentes com um Ku único (gap < 0,5 p.p.)."))
    if abs(razao - 1) > 1e-9:
        diag.append(f"REBASE (razão = {razao:.4f} ≠ 1): o equity E o lucro rebasam juntos na "
                    f"transição — pela convenção bifásica, o NI da fase 2 entra multiplicado por "
                    f"(ROE2/ROE1)·razão. Esse fator é HIPÓTESE DE REBASE DE NÍVEL, não identidade "
                    f"derivada do ROE marginal. NÃO some esta ponte a um valuation que não rebasou "
                    f"a base de lucro; qualquer ROE2 implícito é condicionado a essa convenção.")
    if pl_base is not None and abs(pl_base) > 1e-12:
        pct = pv / pl_base * 100
        diag.append(f"Ponte = {pct:+.1f}% do valor-base informado."
                    + (" ACIMA DE 10%: a transição domina — modele as fases explicitamente, "
                       "não como ajuste." if abs(pct) > 10 else ""))
    if aviso_conflacao:
        diag.append(aviso_conflacao)
    diag.append("ESCOPO: a ponte precifica o MOVIMENTO DE CAIXA da troca de estrutura, não o "
                "deslocamento de risco. Hipóteses declaradas: transição datada no ano n1+1, "
                "dívida a face, Kd = cupom.")
    diag.append("COMPOSIÇÃO (v9.3): NÃO subtraia esta ponte de um alvo para rodar curva ou "
                "reversa monofásica — a subtração deixa a fase 1 e o rebase de nível dentro do "
                "alvo e produz rentabilidades sem sentido (auditoria nº 2, achado B2). A rota "
                "correta é `iso --transicao ponte` com os parâmetros do regime 1: o motor "
                "inverte o bifásico em forma fechada, condicionada à convenção de rebase declarada.")
    return {'fluxo_ano_n1_mais_1': fluxo, 'PV_ponte': pv,
            'delta_estrutura': delta_estrutura, 'razao_rebase': razao,
            'E_pre_transicao': e_pre, 'base_de_ancoragem': base,
            'Ku_implicito_fase1_%': ku1 * 100, 'Ku_implicito_fase2_%': ku2 * 100,
            'diagnosticos': diag}


def selftest():
    a = ANCHORS
    mn = ev_nopat(a['g'], a['roic'], a['w'], a['n'])
    me = mn * (1 - a['d']) * (1 - a['t'])
    mp = pe(a['g'], a['roe'], a['ke'], a['n'], a['gde'], a['nde'])
    eb_novo, _, _ = normaliza_ebitda(446.43, 130.05, 5.00, 6.26, 730.95 / 5.00)  # anchor da ponte
    # anchors dos motores de nível (v2)
    h = fator_h(19.3, 13.0)
    rdep = rentab_pos_degrau(0.20, h, 1.0)
    ftr = desconto_transicao(0.20, 4, 'pontual')
    ftr_r = desconto_transicao(0.20, 4, 'rampa')
    el = elasticidade_operacional(730.95, 446.43)
    ni = nivel_implicito(5824.0, 5.60, 931.0)['metrica_base_implicita']
    dr = registro_drivers([{'nome': 'irrelevante', 'base': 100.0, 'spot': 112.0, 'elast': 0.1},
                           {'nome': 'dominante', 'base': 100.0, 'spot': 108.0, 'elast': 3.0}])
    # anchors novos (v8): convergencia == gordon(roic_tv=W), invariante a gp; APV vF8
    cv = ev_nopat(0.05, 0.085, 0.07, 10, tv='convergencia')
    gv1 = ev_nopat(0.05, 0.085, 0.07, 10, tv='gordon', roic_tv=0.07, gp=0.0)
    gv2 = ev_nopat(0.05, 0.085, 0.07, 10, tv='gordon', roic_tv=0.07, gp=0.05)
    apv = apv_recursao(22.184, 0.11, 10, 0.20, 0.142714285714286, 0.30, 35.0,
                       fcff_tv=50.5317555785773, gtv=0.0, conv='mm')
    # anchors C1 (v8.1): política de caixa no terminal do gordon
    c1c = pe(0.06, 0.18, 0.12, 10, 0.20, 0.0, tv='gordon', roe_tv=0.15, gp=0.03, politica_tv='continua')
    c1e = pe(0.06, 0.18, 0.12, 10, 0.20, 0.0, tv='gordon', roe_tv=0.15, gp=0.03, politica_tv='encerra')
    # anchors v9: ponte de releveraging (planilha vF19, aba 'JM 2 phases + Fade ROE')
    pt = ponte_releveraging(n1=5, ke1=0.22, ke2=0.16, gde1=0.8, nde1=0.6, gde2=0.3, nde2=0.2,
                            kd=0.11, tax=0.30, g1=0.12, roe1=0.10846315789473689)
    pt0 = ponte_releveraging(n1=5, ke1=0.22, ke2=0.16, gde1=0.8, nde1=0.6, gde2=0.8, nde2=0.6,
                             kd=0.11, tax=0.30, g1=0.12, roe1=0.10846315789473689)
    # anchor equity `book` v9.30: a antiga planilha vF8 somava Δcaixa aos fluxos e também E_n;
    # clean surplus corrige o P/L para DDM + book. O ROE implícito continua o mesmo.
    iso_pe = iso_curva('pe', 5.617294815452462, 0.22, 10, [0.11],
                       tv='book', gde=0.538461538461538, nde=0.461538461538462)
    iso_ev = iso_curva('ev', 6.429566333754988, 0.187331578947369, 10, [0.11], tv='book')
    r_pe = iso_pe['curva'][0]['rent_implicita_pct'] / 100
    r_ev = iso_ev['curva'][0]['rent_implicita_pct'] / 100
    # anchors v9.2: (a) inversão B1 recupera o marginal quando marginal != book
    alvo_b1 = pe(0.11, 0.4483, 0.22, 10, 0.538461538461538, 0.461538461538462,
                 tv='book', roe_book=0.28)
    iso_b1 = iso_curva('pe', alvo_b1, 0.22, 10, [0.11], tv='book',
                       gde=0.538461538461538, nde=0.461538461538462, rent_book=0.28)
    r_b1 = iso_b1['curva'][0]['rent_implicita_pct'] / 100
    # (b) inversão bifásica FECHADA CONDICIONAL à convenção de rebase — caso histórico vF19 (ROE2 = 43.45%)
    _alvo2 = _pe2_book(0.12, 0.1085, 0.22, 5, 0.8, 0.6, 0.15, 0.4345, 0.16, 12, 0.3, 0.2,
                       0.11, 0.30)['total']
    iso_tr = iso_curva('pe', _alvo2, 0.16, 12, [0.15], tv='book', gde=0.3, nde=0.2,
                       transicao='ponte',
                       ponte_params=dict(n1=5, ke1=0.22, gde1=0.8, nde1=0.6, kd=0.11,
                                         tax=0.30, g1=0.12, roe1=0.1085))
    ct = iso_tr['composicao_transicao']
    r_tr = iso_tr['curva'][0]['rent_implicita_pct'] / 100
    # anchor v9.24: composição bifásica rampa+expansão (planilha ELMT ago/26)
    rp = rampa_bifasica(265.0, 26.8, 6.8, 0.191, 0.119, 0.35, 10, 5, 0.08, 0.179364,
                        util=0.65, tv='convergencia')
    ok = (abs(mn - 6.429566333754988) < 1e-9 and abs(me - 4.200650004719926) < 1e-9
          and abs(mp - 5.617294815452462) < 1e-9 and abs(eb_novo - 630.6294) < 1e-3
          and abs(h - 1.4846153846153847) < 1e-12 and abs(rdep - 0.2969230769230769) < 1e-12
          and abs(ftr - 0.48225308641975306) < 1e-12 and abs(ftr_r - 0.6471836419753086) < 1e-12
          and abs(el - 1.6373227605671663) < 1e-12 and abs(ni - 1040.0) < 1e-6
          and dr['GATE'] is True and dr['drivers'][0]['nome'] == 'dominante'
          and dr['drivers'][0]['tratamento'] == 'CENÁRIO'
          and dr['drivers'][1]['tratamento'] == 'linha de sensibilidade'
          and abs(cv - 16.137921415912334) < 1e-9 and abs(cv - gv1) < 1e-12 and abs(cv - gv2) < 1e-9
          and abs(apv['V0'] - 193.659212) < 1e-4 and abs(apv['E0'] - 158.659212) < 1e-4
          and abs(apv['Vu0'] - 174.259240) < 1e-4 and abs(apv['VTS0'] - 19.399972) < 1e-4
          and abs(apv['Ke_t_%'][0] - 20.5633) < 1e-3 and abs(apv['WACC_t_%'][0] - 18.6524) < 1e-3
          and abs(apv['check_FCFE_at_Ke_t_igual_E0']) < 1e-6
          and abs(apv['check_FCFF_at_WACC_t_igual_V0']) < 1e-6
          and abs(apv['check_Ke_dinamico_igual_formula_Fernandez']) < 1e-9
          and abs(c1c - 11.18986282200995) < 1e-12 and abs(c1e - 10.918217786079857) < 1e-12
          and abs(pt['fluxo_ano_n1_mais_1'] - (-7.839738665939479)) < 1e-9
          and abs(pt['PV_ponte'] - (-2.5006012464438787)) < 1e-9
          and abs(pt0['PV_ponte']) < 1e-15 and abs(pt0['delta_estrutura']) < 1e-15
          and abs(r_pe - 0.448269230769231) < 1e-9 and abs(r_ev - 0.343515789473684) < 1e-9
          and iso_pe['curva'][0]['check_multiplo'] == 0.0 and iso_ev['curva'][0]['check_multiplo'] == 0.0
          and abs(r_b1 - 0.4483) < 1e-9 and iso_b1['curva'][0]['check_multiplo'] == 0.0
          and abs(r_tr - 0.4345) < 1e-9 and iso_tr['curva'][0]['check_multiplo'] == 0.0
          and 'FECHADA E CONDICIONAL' in ct['composicao']
          and abs(rp['EV'] - 170.9304) < 1e-3 and abs(rp['vp_fase1'] - 45.2592) < 1e-3
          and abs(rp['valor_fase2_no_ano_T'] - 220.4887) < 1e-3
          and abs(rp['g1_%'] - 8.9977) < 1e-3 and abs(rp['roic2_%'] - 16.007) < 1e-2
          and rp['checks_internos']['P1_fluxo_a_fluxo_max_abs'] < 1e-9
          and abs(rp['checks_internos']['P4_receita_T_menos_capacidade']) < 1e-6)
    print(f"EV/NOPAT {mn:.6f} (ref 6.429566) | EV/EBITDA {me:.6f} (ref 4.200650) | "
          f"P/L book-clean-surplus {mp:.6f} (ref v9.30 5.617295)")
    print(f"normaliza: EBITDA_norm {eb_novo:.4f} (ref 630.6294)")
    print(f"degrau: h {h:.6f} (ref 1.484615) | rentab_pos {rdep*100:.4f}% (ref 29.6923%) | "
          f"transicao 4a@20% pontual {ftr:.6f} (ref 0.482253) | rampa {ftr_r:.6f} (ref 0.647184)")
    print(f"elast operacional 730.95/446.43 {el:.6f} (ref 1.637323) | gate por impacto: "
          f"dominante={dr['drivers'][0]['tratamento']}, irrelevante={dr['drivers'][1]['tratamento']}")
    print(f"nivel: metrica implicita {ni:.2f} (ref 1040.00) | drivers gate={dr['GATE']} (ref True)")
    print(f"convergencia: {cv:.6f} (ref 16.137921) == gordon(roic_tv=W) gp=0/5%: {gv1:.6f}/{gv2:.6f}")
    print(f"APV vF8: V0 {apv['V0']:.4f} (ref 193.6592) | E0 {apv['E0']:.4f} (ref 158.6592) | "
          f"Ke_1 {apv['Ke_t_%'][0]:.4f}% (ref 20.5633%) | WACC_1 {apv['WACC_t_%'][0]:.4f}% (ref 18.6524%) | "
          f"checks 4/5/6 = {apv['check_FCFE_at_Ke_t_igual_E0']:.1e}/"
          f"{apv['check_Ke_dinamico_igual_formula_Fernandez']:.1e}/{apv['check_FCFF_at_WACC_t_igual_V0']:.1e}")
    print(f"C1 politica caixa TV: continua {c1c:.6f} (ref 11.189863) | encerra {c1e:.6f} (ref 10.918218)")
    print(f"ponte vF19: fluxo {pt['fluxo_ano_n1_mais_1']:.6f} (ref -7.839739) | PV {pt['PV_ponte']:.6f} "
          f"(ref -2.500601) | colapso estrutura igual = {pt0['PV_ponte']:.1e} (ref 0)")
    print(f"iso: ROE* {r_pe*100:.6f}% (ref 44.826923%, alvo book v9.30) | ROIC* {r_ev*100:.6f}% (ref 34.351579%) | "
          f"verificação no motor = 0/0")
    print(f"iso v9.2/9.3: B1 recupera marginal {r_b1*100:.4f}% (ref 44.8300%) | inversão bifásica "
          f"FECHADA CONDICIONAL recupera ROE2 {r_tr*100:.4f}% (ref 43.4500%, caso verdadeiro vF19)")
    print(f"rampa v9.24 (planilha ELMT ago/26): EV {rp['EV']:.4f} (ref 170.9304) | fase1 {rp['vp_fase1']:.4f} "
          f"(ref 45.2592) | fase2@T {rp['valor_fase2_no_ano_T']:.4f} (ref 220.4887) | "
          f"g1 {rp['g1_%']:.4f}% | ROIC2 {rp['roic2_%']:.3f}% | P1/P4 = "
          f"{rp['checks_internos']['P1_fluxo_a_fluxo_max_abs']:.1e}/"
          f"{rp['checks_internos']['P4_receita_T_menos_capacidade']:.1e}")
    print("SELFTEST OK — anchors preservados. v10.1: ev_nopat passou a somar PARTES (decomposição de Miller-Modigliani e peso do terminal saem do motor); guardas de domínio e giro negativo da v10 mantidos; núcleo numérico inalterado."
          if ok else "SELFTEST FALHOU — NÃO USE OS RESULTADOS.")
    sys.exit(0 if ok else 1)

# ---------------- saída JSON (NaN/Inf -> null: JSON válido sempre) ----------------
_DOMAIN_WARNINGS = []

def avaliar_dominios_cli(ns):
    """Hardening v9.28: separa impossibilidade matemática de regime econômico anômalo.
    Valores recebidos são os pontos percentuais BRUTOS da CLI."""
    d = vars(ns) if hasattr(ns, '__dict__') else dict(ns)
    erros, avisos = [], []
    for nome in ('g', 'g1', 'g2', 'gp', 'gtv'):
        v = d.get(nome)
        if v is not None and v <= -100:
            erros.append(f'--{nome.replace("_", "-")} deve ser > -100%; recebido {v}%')
    for nome in ('wacc', 'ke', 'ku', 'kd'):
        v = d.get(nome)
        if v is not None and v <= -100:
            erros.append(f'--{nome.replace("_", "-")} deve ser > -100%; recebido {v}%')
    n = d.get('n')
    if n is not None and n < 1:
        erros.append(f'--n deve ser >= 1; recebido {n}')
    tax = d.get('tax')
    if tax is not None and (tax < 0 or tax > 100):
        avisos.append(f'REGIME ANÔMALO: tax={tax}% fora de [0%,100%]. Exige justificativa explícita (NOL, crédito fiscal, benefício ou one-off).')
    da = d.get('da')
    if da is not None and (da < 0 or da > 100):
        avisos.append(f'REGIME ANÔMALO: d=D&A/EBITDA={da}% fora de [0%,100%]. Pode ocorrer, mas exige reconciliação econômica de D&A, capex e EBITDA.')
    return erros, avisos

def _json_sane(o):
    if isinstance(o, float) and (o != o or o == float('inf') or o == float('-inf')):
        return None
    if isinstance(o, dict):
        return {k: _json_sane(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_json_sane(v) for v in o]
    return o

def jprint(out):
    if isinstance(out, dict) and _DOMAIN_WARNINGS:
        out = dict(out)
        out.setdefault('avisos_dominio', list(_DOMAIN_WARNINGS))
    print(json.dumps(_json_sane(out), indent=2, ensure_ascii=False))

# [C7] Convenção do fluxo de transição no gordon — declarável, ecoada e QUANTIFICADA no output.
C7_NOTA = ('[C7] fluxo de transição: NOPAT/LL_{n+1} = base_n × (1+g) — o ano n+1 cresce à taxa do '
           'explícito e retém gp/rentabilidade_TV (timing: investimento em t financia o crescimento '
           'de t+1; internamente consistente e fiel à planilha de referência, que só arbitra a '
           "'book'). A alternativa base_n × (1+gp), usada por parte do sell-side, muda SÓ o termo "
           'de TV por um fator (1+gp)/(1+g): efeito relativo = TV_share × [(1+gp)/(1+g) − 1], '
           'dirigido pelo gap g−gp — o efeito exato deste caso sai no campo '
           'efeito_c7_alternativa_gp_%. Declare a convenção ao comparar com múltiplo justo de '
           'terceiros.')

def _efeito_c7_ev(g, roic, w, n, roic_tv, gp, mid_year=False, roic_book=None):
    """Efeito relativo de trocar a convenção do fluxo de transição para (1+gp), lado firm.
    = TV_share × [(1+gp)/(1+g) − 1]; TV_share do próprio caso (invariante a mid-year)."""
    m = ev_nopat(g, roic, w, n, tv='gordon', roic_tv=roic_tv, gp=gp,
                 roic_book=roic_book, mid_year=mid_year)
    if m != m or roic_tv is None:
        return None
    tv = (1 + g) ** (n + 1) * (1 - gp / roic_tv) / (w - gp) / (1 + w) ** n
    tv *= ((1 + w) ** 0.5 if mid_year else 1.0)
    return (tv / m) * ((1 + gp) / (1 + g) - 1)

def _efeito_c7_pe(g, roe, ke, n, gde, nde, roe_tv, gp, politica_tv='continua',
                  mid_year=False, roe_book=None):
    """Efeito C7 no lado equity, respeitando a política de caixa no terminal (C1)."""
    m = pe(g, roe, ke, n, gde, nde, tv='gordon', roe_tv=roe_tv, gp=gp,
           roe_book=roe_book, politica_tv=politica_tv, mid_year=mid_year)
    if m != m or roe_tv is None:
        return None
    caixa = gde - nde
    ret_tv = (1 - gp / roe_tv) + (caixa * (gp / roe_tv) if politica_tv == 'continua' else 0.0)
    tv = (1 + g) ** (n + 1) * ret_tv / (ke - gp) / (1 + ke) ** n
    tv *= ((1 + ke) ** 0.5 if mid_year else 1.0)
    return (tv / m) * ((1 + gp) / (1 + g) - 1)

# ---------------- CLI ----------------
def main():
    # [v9.9] Diagnósticos e selftest saem com acentos, ≡ e setas. Em locale não-UTF-8 (cp1252,
    # Windows PT-BR) a impressão estoura em UnicodeEncodeError assim que a saída é redirecionada
    # ou lida por outro processo. Fixado no ponto de ENTRADA do CLI: quem importa o motor como
    # biblioteca não tem seu sys.stdout mexido.
    for _fluxo in (sys.stdout, sys.stderr):
        if hasattr(_fluxo, 'reconfigure'):
            _fluxo.reconfigure(encoding='utf-8')
    class ParserGate1(argparse.ArgumentParser):
        """[v9.27] Só a AUSÊNCIA de --tv vira parada do Gate 1; valor inválido segue argparse."""
        def error(self, message):
            if message.startswith('the following arguments are required:') and '--tv' in message:
                print(json.dumps({
                    'erro': 'convenção terminal não declarada — Gate 1',
                    'instrucao': 'PARE. Não escolha uma convenção por conta própria: pergunte ao '
                                 'usuário qual hipótese sobre a morte do spread e rode o Gate 1.',
                    'opcoes': {'book': 'renda residual truncada — TV = capital investido',
                               'convergencia': 'RONIC=WACC no capital novo — TV = NOPAT/W',
                               'gordon': 'ROIC_TV e gp livres (exige --roic-tv; --gp)'}},
                    ensure_ascii=False, indent=2))
                raise SystemExit(2)
            super().error(message)
    p = ParserGate1(description=__doc__)
    sub = p.add_subparsers(dest='cmd', required=True, parser_class=ParserGate1)

    def rates(sp, names):
        for nm, df in names: sp.add_argument('--' + nm, type=float, default=df)

    def flags_coerencia(sp, cruzada):
        """[v9.11] Inputs OPCIONAIS do gate de coerência do vetor (padrão retrofit v9.4: nenhum
        script existente quebra; o que faltar sai declarado em nao_checadas_por_falta_de_input).
        `cruzada` é a variável do OUTRO lado — o gate precisa de ROIC e ROE juntos para testar a
        identidade de alavancagem da planilha (linha 122)."""
        for nm in cruzada + ['kd', 'cash-yield', 'rir-observado']:
            sp.add_argument('--' + nm, type=float, default=None,
                            help='[v9.11] opcional — gate de coerência do vetor (%%)')
        sp.add_argument('--ebitda-ic', type=float, default=None,
                        help='[v9.11] opcional — EBITDA/capital investido OBSERVADO (razão, não %%)')

    TVS = ['book', 'convergencia', 'gordon', 'ic', 'spread']  # ic/spread = aliases legados
    TVHELP = ("OBRIGATORIO, sem default. book (ex-ic): renda residual truncada, TV=capital investido; "
              "convergencia: RONIC=WACC no capital novo, TV=NOPAT/W; gordon (ex-spread): "
              "ROIC_TV e gp livres. Rode o Gate de convencao antes.")
    s = sub.add_parser('ev');  rates(s, [('g', None), ('roic', None), ('wacc', None), ('da', None), ('tax', None), ('roic-tv', None), ('roic-book', None), ('gp', 0.0), ('ebitda', None), ('nd', None), ('acoes', None)])
    s.add_argument('--rf', type=float, default=None, help='[v9.4] taxa livre de risco NOMINAL da moeda do modelo (%%) — ativa a âncora macro do gp (Damodaran)')
    s.add_argument('--moeda', type=str, default=None, help='[v9.4] moeda e regime do modelo (ex.: BRL-nominal, USD-nominal, BRL-real)')
    flags_coerencia(s, ['roe', 'ke', 'gde', 'nde'])
    s.add_argument('--n', type=int, default=10); s.add_argument('--tv', required=True, choices=TVS, help=TVHELP)
    s.add_argument('--mid-year', action='store_true',
                   help='[C3] convenção midpoint: desloca os fluxos anuais do fim para o meio do período e multiplica por (1+custo)^0.5. Default: fim de ano, como a planilha de referencia.')
    s.add_argument('--roic-ue', type=float, default=None,
                   help='[v9.24] ROIC de unit economics (%%) — terceiro canal do triangulo (§11.2), espelho do --rir-observado')
    s.add_argument('--capex-total', type=float, default=None,
                   help='[v9.24] capex total do ano-base (moeda) — ativa a conservacao de capital §11.1b (exige --dwc e --ebitda)')
    s.add_argument('--dwc', type=float, default=None,
                   help='[v9.24] variacao de capital de giro do ano-base (moeda) — par do --capex-total')
    s = sub.add_parser('rampa', help='[v9.24] composicao bifasica §8f: rampa de capacidade PRE-CONSTRUIDA '
                                     '(so giro; forma fechada alfa/beta) + expansao de capacidade nova '
                                     '(custo pleno), costurada como TV da fase 1. g1<0 = bloco de colheita.')
    s.add_argument('--receita0', type=float, required=True, help='receita do ano 0 (moeda)')
    s.add_argument('--ebitda0', type=float, required=True, help='EBITDA economico do ano 0 (moeda)')
    s.add_argument('--da-parque', type=float, required=True, help='D&A do parque instalado (moeda) — FIXA na fase 1; capex de manutencao = D&A')
    s.add_argument('--wk', type=float, required=True, help='intensidade de capital de giro liquido (%% da receita) — cobrada nas DUAS fases')
    s.add_argument('--kappa', type=float, required=True, help='capex fixo de EXPANSAO (%% da delta-receita) — so fase 2')
    s.add_argument('--g2', type=float, required=True, help='crescimento da fase 2 (%%)')
    s.add_argument('--wacc', type=float, required=True); s.add_argument('--tax', type=float, required=True)
    s.add_argument('--t-rampa', type=int, required=True, help='T — prazo da rampa (anos); delimitador OBSERVAVEL obrigatorio')
    s.add_argument('--n', type=int, default=10, help='horizonte total (rampa + expansao); a rampa NAO estica o CAP')
    s.add_argument('--util', type=float, default=None, help='utilizacao atual do parque (%%): g1=(1/u)^(1/T)-1 e Receita_T=capacidade por construcao')
    s.add_argument('--g1', type=float, default=None, help='alternativa ao --util: g1 direto (%%); negativo = colheita')
    s.add_argument('--tv', required=True, choices=TVS, help=TVHELP + ' (aplicada ao terminal da FASE 2)')
    s.add_argument('--roic-tv', type=float, default=None); s.add_argument('--gp', type=float, default=0.0)
    s.add_argument('--roic-book', type=float, default=None)
    s.add_argument('--nd', type=float, default=None); s.add_argument('--acoes', type=float, default=None)
    s.add_argument('--rf', type=float, default=None, help='[v9.4] taxa livre de risco NOMINAL da moeda (%%)')
    s.add_argument('--moeda', type=str, default=None, help='[v9.4] moeda e regime do modelo')
    s = sub.add_parser('pe');  rates(s, [('g', None), ('roe', None), ('ke', None), ('gde', 0.0), ('nde', 0.0), ('roe-tv', None), ('roe-book', None), ('gp', 0.0), ('ni', None), ('acoes', None)])
    flags_coerencia(s, ['roic', 'wacc', 'da', 'tax'])
    s.add_argument('--rf', type=float, default=None, help='[v9.4] taxa livre de risco NOMINAL da moeda do modelo (%%) — ativa a âncora macro do gp (Damodaran)')
    s.add_argument('--moeda', type=str, default=None, help='[v9.4] moeda e regime do modelo (ex.: BRL-nominal, USD-nominal, BRL-real)')
    s.add_argument('--n', type=int, default=10); s.add_argument('--tv', required=True, choices=TVS, help=TVHELP)
    s.add_argument('--politica-tv', default='continua', choices=['continua', 'encerra'], help='politica de caixa no terminal do gordon (correcao C1): continua (canonica, default) ou encerra no ano n')
    s.add_argument('--mid-year', action='store_true',
                   help='[C3] convenção midpoint: desloca os fluxos anuais do fim para o meio do período e multiplica por (1+custo)^0.5. Default: fim de ano, como a planilha de referencia.')
    s = sub.add_parser('rev'); rates(s, [('alvo', None), ('g', None), ('roic', None), ('roe', None), ('wacc', None), ('ke', None), ('da', 0.0), ('tax', 0.0), ('gde', 0.0), ('nde', 0.0), ('roic-tv', None), ('roe-tv', None), ('roic-book', None), ('roe-book', None), ('gp', 0.0)])
    s.add_argument('--rf', type=float, default=None, help='[v9.4] taxa livre de risco NOMINAL da moeda do modelo (%%) — ativa a âncora macro do gp (Damodaran)')
    s.add_argument('--moeda', type=str, default=None, help='[v9.4] moeda e regime do modelo (ex.: BRL-nominal, USD-nominal, BRL-real)')
    s.add_argument('--n', type=int, default=10); s.add_argument('--tv', required=True, choices=TVS, help=TVHELP)
    s.add_argument('--resolver', required=True, choices=['g', 'roic', 'roe', 'ke', 'wacc', 'gp', 'cap'])
    s.add_argument('--mid-year', action='store_true',
                   help='[C3] convenção midpoint: desloca os fluxos anuais do fim para o meio do período e multiplica por (1+custo)^0.5. Default: fim de ano, como a planilha de referencia.')
    s.add_argument('--politica-tv', default='continua', choices=['continua', 'encerra'])
    s.add_argument('--base', default='ebitda', choices=['ebitda', 'nopat', 'pl'], help='métrica do múltiplo-alvo')
    s.add_argument('--tol', type=float, default=1.0, help='tolerância do alvo em %% para o intervalo de identificação (default 1)')
    s.add_argument('--alvo-base', default='corrente', choices=['corrente', 'forward'],
                   help='[D2] base do multiplo-ALVO: corrente/TTM (default) ou forward/NTM. '
                        'Tela em NTM resolvida contra multiplo corrente desloca o alvo em (1+g).')
    s.add_argument('--rir-externo', action='store_true',
                   help='estende a busca a região RiR > 100%% (g > rentabilidade): crescimento acima '
                        'do autofinanciável, admissível SOMENTE com fonte de funding declarada '
                        '(paper §6.10, corolário 1). Default: busca restrita a RiR <= 100%%.')
    s = sub.add_parser('kewacc', help='sanity check ESTATICO de perpetuidade — para a trilha dinamica use apv'); rates(s, [('ku', None), ('ke', None), ('kd', None), ('tax', None), ('de', None)])
    s.add_argument('--conv', default='mm', choices=['mm', 'ku'])
    s = sub.add_parser('apv', help='recursao backward APV (vF8): Ke_t e WACC_t consistentes periodo a periodo')
    rates(s, [('ku', None), ('kd', None), ('tax', None), ('g', None), ('gtv', 0.0)])
    s.add_argument('--fcff1', type=float, required=True, help='FCFF do ano 1 (unidade monetaria)')
    s.add_argument('--fcff-tv', type=float, default=None, help='FCFF de n+1 usado no TV. Default C7: FCFF_n x (1+g); informe para iniciar gtv já em n+1.')
    s.add_argument('--d0', type=float, required=True, help='divida bruta inicial a mercado')
    s.add_argument('--n', type=int, default=10)
    s.add_argument('--conv', default='mm', choices=['mm', 'ku'])
    s = sub.add_parser('tabela')
    s.add_argument('--rf', type=float, default=None, help='[v9.4] taxa livre de risco NOMINAL da moeda do modelo (%%) — ativa a âncora macro do gp (Damodaran)')
    s.add_argument('--moeda', type=str, default=None, help='[v9.4] moeda e regime do modelo (ex.: BRL-nominal, USD-nominal, BRL-real)')
    s.add_argument('metrica', choices=['ev', 'pe'])
    rates(s, [('wacc', None), ('ke', None), ('da', 0.0), ('tax', 0.0), ('gde', 0.0), ('nde', 0.0),
              ('centro-roic', None), ('centro-roe', None), ('centro-g', None),
              ('passo-roic', 1.0), ('passo-roe', 2.0), ('passo-g', 2.0),
              ('roic-tv', None), ('roe-tv', None), ('roic-book', None), ('roe-book', None), ('gp', 0.0)])
    s.add_argument('--n', type=int, default=10)
    s.add_argument('--tv', required=True, choices=TVS, help=TVHELP)
    s.add_argument('--base', default='forward', choices=['forward', 'corrente'])
    s.add_argument('--mid-year', action='store_true',
                   help='[C3] convenção midpoint: desloca os fluxos anuais do fim para o meio do período e multiplica por (1+custo)^0.5. Default: fim de ano, como a planilha de referencia.')
    s.add_argument('--politica-tv', default='continua', choices=['continua', 'encerra'])
    s = sub.add_parser('normaliza'); rates(s, [('ebitda-base', None), ('da', None), ('preco-base', None), ('preco-novo', None),
              ('vol', None), ('rev-driver', None), ('tax', 0.0),
              ('g', None), ('roic', None), ('wacc', None), ('roic-tv', None), ('roic-book', None), ('gp', 0.0),
              ('nd', None), ('acoes', None)])
    s.add_argument('--limiar', type=float, default=10.0, help='gate por IMPACTO = |elast x gap| em %% (default 10)')
    s.add_argument('--n', type=int, default=10)
    s.add_argument('--tv', required=True, choices=TVS, help=TVHELP)
    s = sub.add_parser('degrau', help='degrau de nível: capacidade ociosa de balanço / re-precificação')
    s.add_argument('--rf', type=float, default=None, help='[v9.4] taxa livre de risco NOMINAL da moeda do modelo (%%)')
    s.add_argument('--moeda', type=str, default=None, help='[v9.4] moeda e regime do modelo (ex.: BRL-nominal)')
    rates(s, [('indice-atual', None), ('m', 100.0), ('g', None),
              ('roe', None), ('ke', None), ('roic', None), ('wacc', None),
              ('roe-tv', None), ('roic-tv', None), ('roe-book', None), ('roic-book', None),
              ('gp', 0.0), ('gde', 0.0), ('nde', 0.0),
              ('alvo-pvp', None)])
    s.add_argument('--indice-alvo', help='lista separada por vírgula, ex.: 16,14,13,11')
    s.add_argument('--anos', type=float, default=0.0, help='anos até completar o deployment')
    s.add_argument('--perfil-transicao', default='rampa', choices=['rampa', 'pontual'],
                   help='rampa (padrao, deployment linear) ou pontual (degrau datado no ano T)')
    s.add_argument('--n', type=int, default=10)
    s.add_argument('--tv', required=True, choices=TVS, help=TVHELP)
    s.add_argument('--politica-tv', default='continua', choices=['continua', 'encerra'])
    s.add_argument('--vpa', type=float, default=None, help='valor patrimonial por ação (ponte de preço)')
    s.add_argument('--fx', type=float, default=1.0)
    s = sub.add_parser('drivers', help='registro de drivers exógenos, gate e ranking')
    s.add_argument('--driver', action='append', required=True,
                   metavar='NOME:BASE:SPOT[:ELAST|:auto:LINHA:METRICA[:custo]]',
                   help='repetir por driver. ELAST = variação %% da métrica-base por 1%% do driver '
                        '(NEGATIVA para driver de custo). Use "auto:LINHA:METRICA" para DERIVAR '
                        '(= linha exposta / métrica-base) em vez de arbitrar; acrescente ":custo" '
                        'quando o driver for de CUSTO (frete, energia, insumo) — o sinal inverte.')
    s.add_argument('--limiar', type=float, default=10.0, help='gate em %% (default 10)')
    s = sub.add_parser('nivel', help='reversa em degrau: nível implícito no preço '
                       '(congelado = limite superior; recalculado = leitura central, v10.1)')
    rates(s, [('alvo-valor', None), ('multiplo', None), ('metrica-base', None),
              ('vol', None), ('preco-base', None),
              ('consenso-t1', None), ('consenso-t2', None),
              ('da-absoluta', None), ('tax', None), ('g', None), ('roic', None),
              ('wacc', None), ('roic-tv', None), ('gp', 0.0), ('roic-book', None)])
    s.add_argument('--n', type=int, default=10)
    s.add_argument('--tv', choices=TVS, default=None, help=TVHELP)
    s.add_argument('--mid-year', action='store_true')
    s = sub.add_parser('iso', help='curva iso-valor (v9.1): grade de pares (g, rentabilidade) '
                       'que reconciliam o mesmo múltiplo-alvo; book em forma fechada (vF8.1), '
                       'convergencia/gordon via bissecção do motor')
    s.add_argument('lado', choices=['pe', 'ev'])
    rates(s, [('alvo', None), ('ke', None), ('wacc', None), ('gde', 0.0), ('nde', 0.0),
              ('rent-tv', None), ('gp', 0.0), ('g-min', 0.0), ('g-max', 18.0)])
    s.add_argument('--n', type=int, default=10)
    s.add_argument('--tv', required=True, choices=TVS, help=TVHELP)
    s.add_argument('--pontos', type=int, default=10)
    s.add_argument('--rf', type=float, default=None, help='[v9.4] taxa livre de risco NOMINAL da moeda do modelo (%%) — ativa a âncora macro do gp (Damodaran)')
    s.add_argument('--moeda', type=str, default=None, help='[v9.4] moeda e regime do modelo (ex.: BRL-nominal, USD-nominal, BRL-real)')
    s.add_argument('--politica-tv', default='continua', choices=['continua', 'encerra'])
    s.add_argument('--rent-book', type=float, default=None,
                   help='[B1] rentabilidade MÉDIA contábil (%%) para o TV da book em --transicao nenhuma — separa '
                        'marginal×médio; com --transicao ponte é rejeitada porque a fase 1 usa --pt-roe1-book')
    s.add_argument('--transicao', required=True, choices=['nenhuma', 'ponte'],
                   help='[v9.2, obrigatório] nenhuma = regime único declarado; ponte = evento de estrutura '
                        'datado — inversão bifásica fechada, condicionada à convenção de rebase do primeiro lucro; resolve ROE2 em forma fechada')
    for pf, ph in [('pt-n1', 'anos do regime 1'), ('pt-ke1', 'Ke do regime 1 (%%)'),
                   ('pt-gde1', 'GD/E do regime 1 (%%)'), ('pt-nde1', 'ND/E do regime 1 (%%)'),
                   ('pt-kd', 'Kd (%%)'), ('pt-tax', 'alíquota (%%)'), ('pt-g1', 'g do regime 1 (%%)'),
                   ('pt-roe1', 'ROE marginal do regime 1 (%%)'), ('pt-roe1-book', 'ROE médio do regime 1 (%%)'),
                   ('pt-equity', 'LEGADO no iso: equity monetário sem NI0 não é compatível com alvo em múltiplo; use --pt-roe1 [--pt-roe1-book]. --equity segue suportado no comando ponte standalone')]:
        s.add_argument('--' + pf, type=(int if pf == 'pt-n1' else float), default=None, help=ph)
    s = sub.add_parser('ponte', help='ponte de releveraging (v9): precifica a mudança discreta '
                       'de estrutura de capital entre dois regimes como fluxo único ao acionista')
    rates(s, [('ke1', None), ('ke2', None), ('gde1', None), ('nde1', None),
              ('gde2', None), ('nde2', None), ('kd', None), ('kd1', None),
              ('tax', None), ('g1', None), ('roe1', None), ('roe1-book', None)])
    s.add_argument('--n1', type=int, required=True, help='duração da fase 1 (transição no ano n1+1)')
    s.add_argument('--ni', type=float, default=None, help='NI do ano 0 (monetário); sem ele, PV = Δ P/L')
    s.add_argument('--equity', type=float, default=None, help='equity de hoje (monetário) — alternativa a --roe1')
    s.add_argument('--pl-base', type=float, default=None, help='valor-base para reportar a ponte em %% (gate de 10%%)')
    sub.add_parser('selftest')
    a = p.parse_args()

    if a.cmd == 'selftest': selftest()

    global _DOMAIN_WARNINGS
    _erros_dom, _DOMAIN_WARNINGS = avaliar_dominios_cli(a)
    if _erros_dom:
        jprint({'erro': 'domínio matemático inválido', 'detalhes': _erros_dom})
        raise SystemExit(2)

    pc = lambda x: None if x is None else x / 100.0

    aviso_tv = None
    if getattr(a, 'tv', None) in ('ic', 'spread'):
        aviso_tv = (f"alias legado '{a.tv}' -> '{tv_canon(a.tv)}': 'ic' foi renomeada para 'book' "
                    "(renda residual truncada — o NOPAT inteiro colapsa no ano n+1; NAO e a "
                    "convergencia competitiva padrao, que agora se chama 'convergencia') e "
                    "'spread' para 'gordon' (tres regimes de ROIC_TV admitidos).")
        a.tv = tv_canon(a.tv)

    if a.cmd == 'ev':
        g, roic, w = pc(a.g), pc(a.roic), pc(a.wacc)
        d, t = pc(a.da), pc(a.tax)
        rb = pc(getattr(a, 'roic_book'))
        kw = dict(tv=a.tv, roic_tv=pc(getattr(a, 'roic_tv')), gp=pc(a.gp) or 0.0, roic_book=rb,
                  mid_year=getattr(a, 'mid_year', False))
        mn = ev_nopat(g, roic, w, a.n, **kw); me = mn * (1 - d) * (1 - t)
        _mm = decomposicao_mm(g, roic, w, a.n, **kw)
        out = {'EV/NOPAT_curr': round(mn, 4), 'EV/NOPAT_fwd': round(mn / (1 + g), 4),
               'EV/EBITDA_curr': round(me, 4), 'EV/EBITDA_fwd': round(me / (1 + g), 4),
               'decomposicao_mm': {k: (round(v, 4) if isinstance(v, float) else v)
                                   for k, v in _mm.items()},
               'convencao_temporal': ('midpoint / meio do período' if getattr(a, 'mid_year', False)
                                     else 'fim de ano (default, = planilha de referência)'),
               'diagnosticos': diag_firm(g, roic, w, tv=a.tv, n=a.n, roic_book=rb, da=d, tax=t, rf=None if getattr(a, 'rf', None) is None else a.rf / 100, moeda=getattr(a, 'moeda', None), gp=pc(a.gp) or 0.0,
                                         roic_tv=pc(getattr(a, 'roic_tv'))), 'tv': a.tv}
        if getattr(a, 'ebitda', None) is not None:
            nopat0 = a.ebitda * (1 - d) * (1 - t)
            out['decomposicao_mm']['NOPAT_base'] = round(nopat0, 4)
            out['decomposicao_mm']['ativos_instalados'] = round(_mm['ativos_instalados_x_NOPAT'] * nopat0, 2)
            out['decomposicao_mm']['valor_do_crescimento'] = round(_mm['valor_do_crescimento_x_NOPAT'] * nopat0, 2)
        # [v9.11] gate de coerência do vetor — inputs opcionais (padrão retrofit)
        dg_c, res_c = coerencia_vetor(g=g, roic=roic, roe=pc(getattr(a, 'roe', None)), w=w,
                                      ke=pc(getattr(a, 'ke', None)), kd=pc(getattr(a, 'kd', None)),
                                      tax=pc(a.tax), d=pc(a.da),
                                      gde=pc(getattr(a, 'gde', None)),
                                      nde=pc(getattr(a, 'nde', None)),
                                      cash_yield=pc(getattr(a, 'cash_yield', None)),
                                      rir_observado=pc(getattr(a, 'rir_observado', None)),
                                      ebitda_ic=getattr(a, 'ebitda_ic', None))
        out['diagnosticos'] = out['diagnosticos'] + dg_c
        out['coerencia_vetor'] = res_c
        # [v9.24] terceiro canal do triângulo (§11.2) — espelho do --rir-observado
        ue = pc(getattr(a, 'roic_ue', None))
        if ue is not None:
            out['validacao_unit_economics'] = validacao_unit_economics(ue, roic)
        # [v9.24] conservação de capital §11.1b — confronto executável
        cx, dw = getattr(a, 'capex_total', None), getattr(a, 'dwc', None)
        if cx is not None or dw is not None:
            if cx is None or dw is None or a.ebitda is None:
                out['conservacao_capital'] = ('NAO CHECAVEL — a identidade exige --capex-total, '
                                              '--dwc e --ebitda juntos')
            else:
                out['conservacao_capital'] = conservacao_capital(cx, dw, a.ebitda, d, t, g, roic)
        if a.tv == 'gordon':
            out['convencao_fluxo_transicao_C7'] = C7_NOTA
            ef = _efeito_c7_ev(g, roic, w, a.n, kw['roic_tv'], kw['gp'],
                               mid_year=kw['mid_year'], roic_book=kw['roic_book'])
            if ef is not None:
                out['efeito_c7_alternativa_gp_%'] = round(ef * 100, 2)
        if aviso_tv: out['aviso_tv'] = aviso_tv
        if a.ebitda is not None:
            ev = me * a.ebitda; out['EV'] = round(ev, 2)
            if a.nd is not None:
                eq = ev - a.nd; out['Equity'] = round(eq, 2)
                if a.acoes: out['Preco_acao'] = round(eq / a.acoes, 2)
        jprint(out)

    elif a.cmd == 'rampa':
        res = rampa_bifasica(a.receita0, a.ebitda0, a.da_parque, pc(a.wk), pc(a.wacc), pc(a.tax),
                             a.n, a.t_rampa, pc(a.g2), pc(a.kappa),
                             g1=pc(a.g1), util=pc(a.util), tv=a.tv,
                             roic_tv=pc(getattr(a, 'roic_tv', None)), gp=pc(a.gp) or 0.0,
                             roic_book=pc(getattr(a, 'roic_book', None)))
        res['convencao_moeda'] = a.moeda if getattr(a, 'moeda', None) else (
            'MOEDA/REGIME NAO DECLARADOS: g1, g2, gp e WACC na MESMA moeda e regime — declare --moeda')
        if getattr(a, 'rf', None) is not None and a.tv == 'gordon' and pc(a.gp) and pc(a.gp) > pc(a.rf):
            res['aviso_gp'] = (f'gp {a.gp}% acima do teto macro rf {a.rf}% (Damodaran) — hipotese '
                               'legitima SO se declarada por escrito na entrega')
        if a.nd is not None:
            eq = res['EV'] - a.nd; res['Equity'] = round(eq, 2)
            if a.acoes: res['Preco_acao'] = round(eq / a.acoes, 2)
        jprint(res)

    elif a.cmd == 'pe':
        g, roe, ke = pc(a.g), pc(a.roe), pc(a.ke)
        gde, nde = pc(a.gde) or 0, pc(a.nde) or 0
        rb = pc(getattr(a, 'roe_book'))
        kw = dict(tv=a.tv, roe_tv=pc(getattr(a, 'roe_tv')), gp=pc(a.gp) or 0.0, roe_book=rb,
                  politica_tv=getattr(a, 'politica_tv', 'continua'),
                  mid_year=getattr(a, 'mid_year', False))
        m = pe(g, roe, ke, a.n, gde, nde, **kw)
        out = {'PL_curr': round(m, 4), 'PL_fwd': round(m / (1 + g), 4),
               'politica_caixa_tv': getattr(a, 'politica_tv', 'continua'),
               'convencao_temporal': ('midpoint / meio do período' if getattr(a, 'mid_year', False)
                                     else 'fim de ano (default, = planilha de referência)'),
               'diagnosticos': diag_eq(g, roe, ke, gde, nde, tv=a.tv, n=a.n, roe_book=rb,
                                       roe_tv=pc(getattr(a, 'roe_tv')),
                                       politica_tv=getattr(a, 'politica_tv', 'continua'),
                                       gp=pc(a.gp) or 0.0,
                                       rf=None if getattr(a, 'rf', None) is None else a.rf / 100, moeda=a.moeda), 'tv': a.tv}
        if getattr(a, 'ebitda', None) is not None:
            nopat0 = a.ebitda * (1 - d) * (1 - t)
            out['decomposicao_mm']['NOPAT_base'] = round(nopat0, 4)
            out['decomposicao_mm']['ativos_instalados'] = round(_mm['ativos_instalados_x_NOPAT'] * nopat0, 2)
            out['decomposicao_mm']['valor_do_crescimento'] = round(_mm['valor_do_crescimento_x_NOPAT'] * nopat0, 2)
        # [v9.11] gate de coerência do vetor — inputs opcionais (padrão retrofit)
        dg_c, res_c = coerencia_vetor(g=g, roic=pc(getattr(a, 'roic', None)), roe=roe,
                                      w=pc(getattr(a, 'wacc', None)), ke=ke,
                                      kd=pc(getattr(a, 'kd', None)),
                                      tax=pc(getattr(a, 'tax', None)),
                                      d=pc(getattr(a, 'da', None)), gde=gde, nde=nde,
                                      cash_yield=pc(getattr(a, 'cash_yield', None)),
                                      rir_observado=pc(getattr(a, 'rir_observado', None)),
                                      ebitda_ic=getattr(a, 'ebitda_ic', None))
        out['diagnosticos'] = out['diagnosticos'] + dg_c
        out['coerencia_vetor'] = res_c
        if getattr(a, 'moeda', None): out['convencao_moeda'] = a.moeda
        if a.tv == 'gordon':
            out['convencao_fluxo_transicao_C7'] = C7_NOTA
            ef = _efeito_c7_pe(g, roe, ke, a.n, gde, nde, kw['roe_tv'], kw['gp'],
                               politica_tv=kw['politica_tv'], mid_year=kw['mid_year'],
                               roe_book=kw['roe_book'])
            if ef is not None:
                out['efeito_c7_alternativa_gp_%'] = round(ef * 100, 2)
        if abs(gde - nde) > 1e-9:
            m_op = pe(g, roe, ke, a.n, 0.0, 0.0, **kw)
            nota_caixa = (
                'Na convenção book, clean surplus exige Div + E_n: o caixa retido já está no '
                'patrimônio terminal e Caixa/E é neutro no valuation. Excess cash/rendimento de '
                'caixa deve ser tratado separadamente; efeito_politica_caixa deve ser zero.'
                if a.tv == 'book' else
                'PL_operacional = mesmo motor com caixa/E = 0. O efeito-caixa vem do MÓDULO DE '
                'POLÍTICA "proporção de caixa constante, payout endógeno via sweep" — não é '
                'identidade geral. Se o caixa for excedente distribuível (não operacional), a rota '
                'alternativa é Equity = PL_operacional × LL + excess cash, e as duas rotas devem ser '
                'reconciliadas sob a política declarada.'
            )
            out['decomposicao'] = {
                'PL_operacional_curr': round(m_op, 4),
                'efeito_politica_caixa': round(m - m_op, 4),
                'nota': nota_caixa}
        if aviso_tv: out['aviso_tv'] = aviso_tv
        if a.ni is not None:
            eq = m * a.ni; out['Equity'] = round(eq, 2)
            if a.acoes: out['Preco_acao'] = round(eq / a.acoes, 2)
        jprint(out)

    elif a.cmd == 'rev':
        eqside = a.base == 'pl'
        # [R1] consistência resolver × base × custo — falha explicada, nunca rota silenciosa
        if a.resolver in ('roe', 'ke') and not eqside:
            raise SystemExit(f"rev: --resolver {a.resolver} é do lado EQUITY e exige --base pl "
                             f"(base atual: {a.base}, lado firm). Sem isso o motor resolveria a "
                             f"variável do lado errado com o rótulo errado.")
        if a.resolver in ('roic', 'wacc') and eqside:
            raise SystemExit(f"rev: --resolver {a.resolver} é do lado FIRM e exige --base ebitda|nopat "
                             f"(base atual: pl, lado equity).")
        if eqside and pc(a.ke) is None and a.resolver != 'ke':
            raise SystemExit("rev: lado equity (--base pl) exige --ke.")
        if not eqside and pc(a.wacc) is None and a.resolver != 'wacc':
            raise SystemExit("rev: lado firm (--base ebitda|nopat) exige --wacc.")
        conv = 1.0 if a.base != 'ebitda' else (1 - pc(a.da)) * (1 - pc(a.tax))
        M = a.alvo / conv  # alvo em EV/NOPAT ou P/L
        kwf = dict(tv=a.tv, roic_tv=pc(getattr(a, 'roic_tv')), gp=pc(a.gp) or 0.0,
                   roic_book=pc(getattr(a, 'roic_book')), mid_year=getattr(a, 'mid_year', False))
        kwe = dict(tv=a.tv, roe_tv=pc(getattr(a, 'roe_tv')), gp=pc(a.gp) or 0.0,
                   roe_book=pc(getattr(a, 'roe_book')), politica_tv=getattr(a, 'politica_tv', 'continua'),
                   mid_year=getattr(a, 'mid_year', False))
        g, r, k = pc(a.g), pc(a.roe) if eqside else pc(a.roic), pc(a.ke) if eqside else pc(a.wacc)
        gde, nde = pc(a.gde) or 0, pc(a.nde) or 0
        _raw = (lambda gg, rr, kk, nn, kw: pe(gg, rr, kk, nn, gde, nde, **kw)) if eqside \
               else (lambda gg, rr, kk, nn, kw: ev_nopat(gg, rr, kk, nn, **kw))
        # D2 — a base do múltiplo-ALVO tem que casar com a base do múltiplo de tela.
        # Tela em NTM/forward comparada contra múltiplo corrente entra deslocada de (1+g):
        # a 12% de g são 12% de erro no alvo, que a reversa devolve como premissa implícita.
        alvo_base = getattr(a, 'alvo_base', 'corrente')
        nota_regime = ('PREMISSA (regime único): esta reversa assume UMA estrutura de capital ao longo '
                       'do CAP. Evento de estrutura DATADO no horizonte ⟹ use `iso --transicao ponte` '
                       '(inversão bifásica fechada condicionada ao rebase declarado); NÃO reverta sobre alvo subtraído da ponte — '
                       'a subtração deixa a fase 1 e o rebase dentro do alvo (achado B2).')
        base_f = (lambda gg, rr, kk, nn, kw: _raw(gg, rr, kk, nn, kw) / (1 + gg)) \
                 if alvo_base == 'forward' else _raw
        kw = kwe if eqside else kwf
        tvc = tv_canon(kw.get('tv', 'book'))
        rngs = {'g': (-0.60, min(0.60, (r or 0.6) * 0.999)), 'roic': (max(0.005, (g or 0) + 1e-4), 1.50),
                'roe': (max(0.005, (g or 0) + 1e-4), 1.50), 'ke': (max((kw['gp'] or 0) + 1e-3, 0.005), 0.40),
                'wacc': (max((kw['gp'] or 0) + 1e-3, 0.005), 0.40), 'gp': (0.0, (k or 0.4) - 1e-3)}
        rir_ext = getattr(a, 'rir_externo', False)
        if rir_ext:
            rngs['g'] = (-0.60, 0.60)
            rngs['roic'] = (0.005, 1.50)
            rngs['roe'] = (0.005, 1.50)
        def faixa_de_busca(var, lo, hi):
            if var in ('g', 'roic', 'roe'):
                restricao = ('RiR LIVRE (--rir-externo): região g > rentabilidade admitida — '
                             'crescimento acima do autofinanciável, EXIGE fonte de funding declarada '
                             'na entrega (paper §6.10, corolário 1)' if rir_ext else
                             'restrita a RiR ≤ 100% (g ≤ rentabilidade): crescimento '
                             'autofinanciável; para admitir RiR > 100% com funding declarado, '
                             're-rode com --rir-externo')
            else:
                restricao = 'faixa padrão do motor para a variável'
            return {'variavel': var, 'de_%': round(lo * 100, 3), 'ate_%': round(hi * 100, 3),
                    'restricao': restricao}
        var = a.resolver
        def _premissas_fixadas():
            """[v9.7/F-09] Eco integral do condicionamento da reversa: toda raiz devolvida é
            condicional a TUDO isto. Distingue o INFORMADO, o que entrou por DEFAULT e o que
            NÃO SE APLICA ao lado — nada depende de o analista lembrar (aplicacao §8d)."""
            import sys as _sys
            argv = _sys.argv[1:]
            pfmt = lambda v: None if v is None else round(v * 100, 4)
            rot_r, rot_k = ('roe', 'ke') if eqside else ('roic', 'wacc')
            inf = {'lado': 'equity' if eqside else 'firm', 'metrica_base': a.base,
                   'convencao_terminal': tvc}
            if a.base == 'ebitda':
                inf['d_%'], inf['t_%'] = pfmt(pc(a.da)), pfmt(pc(a.tax))
            if var != 'cap':
                inf['CAP_n_anos'] = a.n
            if var != 'g' and g is not None:
                inf['g_%'] = pfmt(g)
            if var not in ('roic', 'roe') and r is not None:
                inf[rot_r + '_marginal_%'] = pfmt(r)
            if var not in ('ke', 'wacc') and k is not None:
                inf[rot_k + '_%'] = pfmt(k)
            rb = kw.get('roe_book' if eqside else 'roic_book')
            if rb is not None:
                inf[rot_r + '_book_%'] = pfmt(rb)
            rtv = kw.get('roe_tv' if eqside else 'roic_tv')
            if rtv is not None:
                inf[rot_r + '_tv_%'] = pfmt(rtv)
            if eqside:
                inf['gde_%'], inf['nde_%'] = pfmt(gde), pfmt(nde)
            dflt = {}
            if var != 'gp' and tvc == 'gordon':
                if '--gp' in argv:
                    inf['gp_%'] = pfmt(kw.get('gp') or 0.0)
                else:
                    dflt['gp_%'] = '0,0 (default — declare se o terminal cresce; guarda macro v9.4 aplica)'
            if tvc == 'book' and rb is None:
                dflt[rot_r + '_book_%'] = ('= ' + rot_r + ' marginal (CONFLACIONADO por ausência de --'
                                           + rot_r + '-book — trava da book, erro potencialmente material'
                                           + ('; a raiz resolvida assume o papel DUPLO marginal=book'
                                              if var in ('roic', 'roe') else '') + ')')
            if eqside and tvc == 'gordon':
                (inf if '--politica-tv' in argv else dflt)['politica_tv'] = (
                    getattr(a, 'politica_tv', 'continua')
                    + ('' if '--politica-tv' in argv else ' (default C1)'))
            if getattr(a, 'mid_year', False):
                inf['convencao_temporal'] = 'midpoint / mid-year (C3)'
            else:
                dflt['convencao_temporal'] = 'fim de ano (default C3 — planilha)'
            if '--alvo-base' in argv:
                inf['base_do_alvo'] = alvo_base
            else:
                dflt['base_do_alvo'] = alvo_base + ' (default D2 — confirme que a tela é TTM)'
            na = (['da/tax (conversão só na base ebitda)'] if a.base != 'ebitda' else []) + \
                 (['gde/nde, politica_tv (lado firm)'] if not eqside else [])
            return {'informadas': inf, 'assumidas_por_default': dflt,
                    'nao_aplicaveis': na,
                    'nota': ('toda raiz é CONDICIONAL a este vetor completo — não é "a" premissa '
                             'implícita do mercado (paper P6.9); mude qualquer premissa fixada e '
                             'a raiz muda')}
        if var == 'cap':
            spread = (r - k) if r is not None and k is not None else None
            if spread is not None and spread <= 0 and tvc == 'book':
                print(json.dumps({'erro': f"CAP implícito indefinido: spread = {spread*100:+.1f} p.p. ≤ 0. "
                                  "Sem retorno acima do custo de capital não existe período de vantagem "
                                  "competitiva a medir — e na convenção 'book' o valor CAI com n (a convergência "
                                  "para cima do ROIC gera valor, e mais anos de spread negativo o destroem), "
                                  "então a varredura crescente devolveria um n espúrio. Reveja ROIC/convenção.",
                                  'alvo_normalizado': round(M, 3)}, ensure_ascii=False, indent=2)); return
            vals = [(n, base_f(g, r, k, n, kw)) for n in range(1, 61)]
            difs = [vals[i + 1][1] - vals[i][1] for i in range(len(vals) - 1)]
            monotona = all(d >= -1e-12 for d in difs) or all(d <= 1e-12 for d in difs)
            crescente = vals[-1][1] >= vals[0][1]
            def interp(subindo):
                """n contínuo por interpolação linear entre os anos inteiros que bracketam M."""
                for i in range(len(vals) - 1):
                    (n0, v0), (n1, v1) = vals[i], vals[i + 1]
                    if (subindo and v0 < M <= v1) or (not subindo and v0 > M >= v1):
                        return n0 + (M - v0) / (v1 - v0) if v1 != v0 else float(n0)
                if (subindo and vals[0][1] >= M) or (not subindo and vals[0][1] <= M):
                    return float(vals[0][0])
                return None
            if crescente:
                hit = interp(True)
                gd94 = _guardas_damodaran([], a.tv, pc(a.gp) or 0.0, k,
                                          rf=None if getattr(a, 'rf', None) is None else a.rf / 100,
                                          moeda=getattr(a, 'moeda', None),
                                          rotulo_custo='Ke' if eqside else 'WACC')
                out = {'premissa_regime': nota_regime,
                       'premissas_fixadas': _premissas_fixadas(),
                       **({'convencao_moeda': a.moeda} if getattr(a, 'moeda', None) else {}),
                       **({'guardas_v9_4': gd94} if gd94 else {}),
                       'base_do_alvo': alvo_base,
                   'CAP_implicito_anos': (round(hit, 1) if hit is not None else
                       f">60 — alvo incompatível com estas premissas sob esta convenção "
                       f"(máx em n=60: {vals[-1][1]:.2f})"),
                       'alvo_normalizado': round(M, 3), 'direcao': 'valor cresce com n (spread positivo)',
                       'nota': ('CAP interpolado entre anos inteiros; SEMPRE condicional às demais premissas '
                                '(g, rentabilidade, custo de capital, convenção) — mudou premissa, mudou o CAP. '
                                'Se inalcançável, investigue na ordem: (1) degrau/nível ausente da métrica-base; '
                                '(2) convenção terminal; (3) demais premissas; (4) só então o preço.')}
            else:
                if M > vals[0][1]:
                    hit_txt = (f"alvo {M:.2f} acima do máximo da série ({vals[0][1]:.2f} em n=1) — "
                               f"incompatível com estas premissas sob esta convenção")
                elif M < vals[-1][1]:
                    hit_txt = f"não cruza em n≤60 (faixa {vals[-1][1]:.2f}–{vals[0][1]:.2f})"
                else:
                    hit_txt = round(interp(False), 1)
                gd94 = _guardas_damodaran([], a.tv, pc(a.gp) or 0.0, k,
                                          rf=None if getattr(a, 'rf', None) is None else a.rf / 100,
                                          moeda=getattr(a, 'moeda', None),
                                          rotulo_custo='Ke' if eqside else 'WACC')
                out = {'premissa_regime': nota_regime,
                       'premissas_fixadas': _premissas_fixadas(),
                       **({'convencao_moeda': a.moeda} if getattr(a, 'moeda', None) else {}),
                       **({'guardas_v9_4': gd94} if gd94 else {}), 'CAP_implicito_anos': hit_txt,
                       'alvo_normalizado': round(M, 3),
                       'direcao': 'valor DECRESCE com n — interpretação invertida: n maior destrói valor',
                       'aviso': 'monotonicidade decrescente detectada; o "CAP" aqui mede anos de destruição '
                                'de valor tolerados pelo preço, não vantagem competitiva. Confirme convenção.'}
            out['faixa_de_busca'] = {'variavel': 'cap(n)', 'de_anos': 1, 'ate_anos': 60,
                                     'restricao': 'anos inteiros 1–60, raiz interpolada entre inteiros'}
            if not monotona:
                out['aviso_monotonia'] = ('série valor(n) NÃO monotônica — pode haver mais de um n compatível '
                                          'com o alvo; a interpolação devolve o primeiro cruzamento.')
            jprint(out); return
        def f(x):
            gg, rr, kk = g, r, k; kk2 = dict(kw)
            if var == 'g': gg = x
            elif var in ('roic', 'roe'): rr = x
            elif var in ('ke', 'wacc'): kk = x
            elif var == 'gp': kk2['gp'] = x
            return base_f(gg, rr, kk, a.n, kk2) - M
        mult = lambda x: f(x) + M
        lo, hi = rngs[var]
        roots, tang = solve_full(f, lo, hi, ref=M)
        tol = (a.tol or 1.0) / 100.0
        _rf_dec = None if getattr(a, 'rf', None) is None else a.rf / 100
        _moeda_dec = getattr(a, 'moeda', None)
        _rot = 'Ke' if eqside else 'WACC'
        # [v9.12/D-2] Quando a variável RESOLVIDA é o gp, a guarda macro tem de incidir sobre a
        # RAIZ, não sobre o chute de entrada. Antes, a reversa devolvia gp = 6,215% enquanto a
        # guarda reportava "ÂNCORA MACRO OK: gp = 2,50%" (o valor de ENTRADA) — guarda verde sobre
        # resposta fora do teto, que é falso negativo: pior que silêncio, porque tem cara de
        # verificação feita. Sem raiz, não há resposta a guardar e a guarda volta ao valor fixado.
        if var == 'gp' and roots:
            gd94 = _guardas_damodaran([], a.tv, 0.0, k, rf=_rf_dec, moeda=_moeda_dec,
                                      rotulo_custo=_rot)          # só a guarda de moeda/regime
            for _x in roots:
                gd94 += [f'[raiz gp = {_x*100:.3f}%] {s}' for s in
                         _guardas_damodaran([], a.tv, _x, k, rf=_rf_dec, moeda=_moeda_dec,
                                            rotulo_custo=_rot)
                         if not s.startswith('MOEDA/REGIME')]
        else:
            gd94 = _guardas_damodaran([], a.tv, pc(a.gp) or 0.0, k, rf=_rf_dec, moeda=_moeda_dec,
                                      rotulo_custo=_rot)
        out = {'premissa_regime': nota_regime,
                       'premissas_fixadas': _premissas_fixadas(),
               **({'convencao_moeda': a.moeda} if getattr(a, 'moeda', None) else {}),
               **({'guardas_v9_4': gd94} if gd94 else {}),
               'alvo_normalizado_' + ('PL' if eqside else 'EV/NOPAT'): round(M, 3),
               'base_do_alvo': alvo_base + (' (NTM/forward — resolvido na mesma base)'
                                            if alvo_base == 'forward' else
                                            ' (múltiplo corrente/TTM — confirme que a tela é TTM)'),
               'faixa_de_busca': faixa_de_busca(var, lo, hi),
               'raizes_' + var + '_%': [round(x * 100, 3) for x in roots]}
        if rir_ext and roots:
            ext = ([x for x in roots if r is not None and x > r] if var == 'g'
                   else [x for x in roots if g is not None and x < g] if var in ('roic', 'roe')
                   else [])
            if ext:
                out['ALERTA_RIR_EXTERNO'] = (
                    f"raiz(es) {[round(x * 100, 2) for x in ext]}% na região RiR > 100% "
                    "(crescimento acima do autofinanciável — FCFF/FCFE negativos no explícito): "
                    "válida SOMENTE com fonte de funding declarada na entrega (captação, dívida, "
                    "capital novo). Sem funding plausível, é hipótese diagnóstica FORTE de erro de "
                    "classificação nível→taxa (paper §6.10, corolário 1) — a investigar, não "
                    "veredicto.")
        if roots:
            out['identificacao_por_raiz'] = {f'{x*100:.3f}%': identificacao(mult, x, M, tol) for x in roots}
        if tang:
            out['raizes_tangenciais_' + var + '_%'] = [
                {'x_%': round(t['x'] * 100, 3), 'residuo': round(t['residuo'], 6),
                 'nota': 'toque sem cruzamento (alvo ≈ extremo da função) — a bissecção pura perde este caso; '
                         'identificação estruturalmente FRACA: qualquer perturbação do alvo remove ou '
                         'desdobra a raiz'} for t in tang]
        if not roots and not tang:
            grid = [base_f(g if var != 'g' else x, r if var not in ('roic', 'roe') else x,
                            k if var not in ('ke', 'wacc') else x, a.n,
                            kw if var != 'gp' else {**kw, 'gp': x})
                    for x in [lo + (hi - lo) * i / 200 for i in range(201)]]
            grid = [v for v in grid if v == v]
            out['sem_solucao'] = (f"máximo atingível {max(grid):.2f} | mínimo {min(grid):.2f} — alvo "
                                  f"incompatível com este conjunto de premissas sob esta convenção. Antes de "
                                  f"concluir sobre o preço, investigue na ordem: (1) degrau/nível ausente da "
                                  f"métrica-base; (2) convenção terminal; (3) demais premissas (base, "
                                  f"rentabilidade, capital, custo de capital); (4) só então o preço.")
            if not rir_ext and var in ('g', 'roic', 'roe'):
                out['sem_solucao'] += (' NOTA: a busca ficou restrita a RiR ≤ 100% '
                                       '(g ≤ rentabilidade) — alvos alcançáveis com funding externo '
                                       'podem existir fora dela; re-rode com --rir-externo para '
                                       'testá-los (raiz nessa região exige funding declarado).')
            # [v9.13 / rodada 2 FNV] quando os eixos primários não fecham, os dois passos que
            # reconciliam (ou refutam) o preço são conhecidos — e ficavam na gaveta por depender
            # de o analista lembrar (regra 10). No caso FNV, o teto RiR→0 foi a ÚNICA hipótese
            # que fechou a conta, e o iso produziu o achado "sem solução para g ≤ 6%".
            if var in ('g', 'roic', 'roe'):
                out['sugestao'] = (
                    'Eixo primário sem raiz — dois passos OBRIGATÓRIOS antes de concluir: '
                    '(1) TETO DO CRESCIMENTO GRATUITO: rode o caso-limite RiR→0 (gordon com '
                    'rentabilidade terminal → ∞, i.e. --roic-tv/--roe-tv altíssimo, e gp = g). A '
                    'distância entre esse teto e o caso-base é o preço que o mercado paga pela '
                    'hipótese de crescimento que não consome capital. (2) CURVA ISO-VALOR: rode '
                    '`iso` no mesmo alvo — ela varre TODOS os pares (g, rentabilidade) e mostra a '
                    'partir de que g o alvo passa a ter solução, com o RiR e os diagnósticos de '
                    'cada ponto.')
        if len(roots) > 1:
            out['aviso'] = 'múltiplas raízes — variável não identificada de forma única; escolher a economicamente plausível'
        if var in ('roic', 'roe') and k is not None and tvc == 'book':
            sub = [x for x in roots if x < k]
            if sub:
                lbl = 'WACC' if var == 'roic' else 'Ke'
                rb_rev = kw.get(var + '_book')
                if rb_rev is None:
                    out['aviso_convencao'] = (f"raiz(es) {[round(x*100,2) for x in sub]}% ABAIXO do {lbl} "
                        f"({k*100:.1f}%) na convenção 'book' SEM book informado: o alvo é reconciliado por um "
                        f"mesmo retorno nos papéis médio e marginal; o terminal então força o lucro inteiro "
                        f"a Ke/WACC sobre esse estoque, embutindo recuperação não declarada. Informe "
                        f"--{var}-book com a MÉDIA do estoque, reverta em outra variável ou use tv='gordon' "
                        f"com {var}_tv abaixo do custo de capital.")
                else:
                    if var == 'roic':
                        leitura_book = ("o TV parte do book inicial e acompanha o marginal pelo capital novo "
                                        "acumulado; não há convergência implícita para cima")
                    else:
                        leitura_book = ("o TV parte do book inicial e acompanha o marginal pelo lucro "
                                        "retido acumulado (clean surplus, v9.30); não há convergência "
                                        "implícita para cima")
                    out['aviso_convencao'] = (f"raiz(es) {[round(x*100,2) for x in sub]}% ABAIXO do {lbl} "
                        f"({k*100:.1f}%) na convenção 'book' COM book informado ({rb_rev*100:.1f}%): raiz(es) "
                        f"CONDICIONADAS, não vazias — {leitura_book}. Leitura admissível sob tese DECLARADA "
                        f"de saída pelo capital investido/patrimônio (turnaround, capex regulatório, liquidação)."
                        + (f" SUB-ALERTA: book < {lbl} — a âncora inicial embute recuperação {k/rb_rev:.2f}x acima do "
                           f"valor capitalizado a custo de capital." if rb_rev < k else ""))
        if aviso_tv: out['aviso_tv'] = aviso_tv
        jprint(out)

    elif a.cmd == 'apv':
        out = apv_recursao(a.fcff1, pc(a.g), a.n, pc(a.ku), pc(a.kd), pc(a.tax), a.d0,
                           fcff_tv=a.fcff_tv, gtv=pc(a.gtv) or 0.0, conv=a.conv)
        # [v9.7] regime de dívida SEMPRE ecoado — resultado APV sem a política de dívida
        # correspondente não é interpretável (auditoria Fase 2, §13). Padrão retrofit v9.4:
        # default preservado (nenhum script quebra), aviso quando entrou por default.
        import sys as _sys
        out['regime_divida'] = ('mm: dívida DETERMINÍSTICA, tax shields descontados a Kd '
                                '(MM/Myers sob a política declarada)' if a.conv == 'mm' else
                                'ku: dívida EXÓGENA D_t = D0(1+g)^t, tax shields descontados a Ku '
                                '(convenção de risco tipo Harris-Pringle; NÃO é HP completo porque D/V não é constante)')
        if '--conv' not in _sys.argv[1:]:
            out['aviso_regime_divida'] = ('regime de dívida NÃO declarado — assumido mm (default). '
                                          'A equivalência Ke↔WACC↔APV depende da política de dívida '
                                          'e do risco do tax shield; declare --conv mm|ku conforme '
                                          'a política real (nominal fixa vs proporção do valor).')
        jprint(out)

    elif a.cmd == 'iso':
        custo = pc(a.ke) if a.lado == 'pe' else pc(a.wacc)
        if custo is None:
            raise SystemExit("iso: informe --ke (lado pe) ou --wacc (lado ev).")
        gmin, gmax = pc(a.g_min), pc(a.g_max)
        k = max(a.pontos, 2)
        grade = [gmin + (gmax - gmin) * i / (k - 1) for i in range(k)]
        pp = None
        if a.transicao == 'ponte':
            if a.rent_book is not None:
                raise SystemExit("iso --transicao ponte: --rent-book não é usado no bifásico e por isso é rejeitado. "
                                 "Use --pt-roe1-book para a média contábil da fase 1; ROE2_book separado "
                                 "não é implementado nesta versão.")
            faltam = [f for f in ('pt_n1', 'pt_ke1', 'pt_gde1', 'pt_nde1', 'pt_kd', 'pt_tax', 'pt_g1')
                      if getattr(a, f) is None]
            if a.pt_equity is not None:
                raise SystemExit("iso --transicao ponte: --pt-equity é monetário, enquanto --alvo é múltiplo por NI0. "
                                 "Sem uma base NI0 explícita, misturar as escalas é inconsistente. Use "
                                 "--pt-roe1 e, se aplicável, --pt-roe1-book. O comando `ponte` standalone "
                                 "continua aceitando --equity monetário.")
            if a.pt_roe1 is None:
                faltam.append('pt_roe1')
            if faltam:
                raise SystemExit("iso --transicao ponte: faltam parâmetros do regime 1: "
                                 + ', '.join('--' + f.replace('_', '-') for f in faltam))
            pp = dict(n1=a.pt_n1, ke1=a.pt_ke1 / 100, gde1=a.pt_gde1 / 100, nde1=a.pt_nde1 / 100,
                      kd=a.pt_kd / 100, tax=a.pt_tax / 100, g1=a.pt_g1 / 100,
                      roe1=None if a.pt_roe1 is None else a.pt_roe1 / 100,
                      roe1_book=None if a.pt_roe1_book is None else a.pt_roe1_book / 100,
                      equity=a.pt_equity)
        out = iso_curva(a.lado, a.alvo, custo, a.n, grade, tv=a.tv,
                        gde=pc(a.gde) or 0.0, nde=pc(a.nde) or 0.0,
                        rent_tv=pc(a.rent_tv), gp=pc(a.gp) or 0.0,
                        politica_tv=a.politica_tv,
                        rent_book=None if a.rent_book is None else a.rent_book / 100,
                        transicao=a.transicao, ponte_params=pp)
        if getattr(a, 'moeda', None): out['convencao_moeda'] = a.moeda
        gd = _guardas_damodaran([], a.tv, pc(a.gp) or 0.0, custo,
                                rf=None if getattr(a, 'rf', None) is None else a.rf / 100, moeda=getattr(a, 'moeda', None),
                                rotulo_custo='Ke' if a.lado == 'pe' else 'WACC')
        if gd: out['guardas_v9_4'] = gd
        jprint(out)

    elif a.cmd == 'ponte':
        out = ponte_releveraging(n1=a.n1, ke1=pc(a.ke1), ke2=pc(a.ke2),
                                 gde1=pc(a.gde1), nde1=pc(a.nde1),
                                 gde2=pc(a.gde2), nde2=pc(a.nde2),
                                 kd=pc(a.kd), tax=pc(a.tax), g1=pc(a.g1),
                                 roe1=pc(a.roe1), ni=a.ni, equity=a.equity,
                                 kd1=pc(a.kd1), pl_base=a.pl_base,
                                 roe1_book=pc(getattr(a, 'roe1_book')))
        jprint(out)

    elif a.cmd == 'kewacc':
        kd, t, de = pc(a.kd), pc(a.tax), pc(a.de)
        conv_kw = a.conv
        fac = (1 - t) if conv_kw == 'mm' else 1.0
        if a.ku is not None:
            ku = pc(a.ku); ke = ku + (ku - kd) * fac * de
        else:
            ke_in = pc(a.ke); ku = (ke_in + kd * fac * de) / (1 + fac * de); ke = ke_in
        wE, wD = 1 / (1 + de), de / (1 + de)
        wacc = ke * wE + kd * (1 - t) * wD
        jprint({'convencao': ('MM (shields a Kd)' if conv_kw == 'mm'
                              else 'Ku (shields a Ku sobre dívida exógena; convenção de risco, não HP completo)'),
                'Ku_%': round(ku * 100, 3), 'Ke_%': round(ke * 100, 3),
                'WACC_%': round(wacc * 100, 3), 'Kd_pos_impostos_%': round(kd * (1 - t) * 100, 3),
                'ESCOPO': 'sanity check ESTÁTICO sob perpetuidade com alavancagem constante — NÃO é a recursão dinâmica. Para Ke_t e WACC_t use apv.',
                'aviso': 'D/E a valor de MERCADO; Ke consistente varia no tempo se alavancagem a mercado deriva'})

    elif a.cmd == 'tabela':
        _gd = _guardas_damodaran([], a.tv, pc(getattr(a, 'gp', None)) or 0.0,
                                 pc(getattr(a, 'wacc', None)) or pc(getattr(a, 'ke', None)) or 0.0,
                                 rf=None if getattr(a, 'rf', None) is None else a.rf / 100,
                                 moeda=getattr(a, 'moeda', None),
                                 rotulo_custo=('WACC' if a.metrica == 'ev' else 'Ke'))
        for _lin in _gd: print('! ' + _lin)
        if getattr(a, 'moeda', None): print('convenção de moeda: ' + a.moeda)
        base, tv, gp = a.base, a.tv, pc(a.gp) or 0.0
        if a.metrica == 'ev':
            w, d, t = pc(a.wacc), pc(a.da), pc(a.tax)
            cr, cg = pc(getattr(a, 'centro_roic')), pc(a.centro_g)
            cols, linhas = grade_ev(w, d, t, a.n, cr, cg, pc(a.passo_roic), pc(a.passo_g),
                                    base=base, tv=tv, roic_tv=pc(getattr(a, 'roic_tv')), gp=gp,
                                    roic_book=pc(getattr(a, 'roic_book')),
                                    mid_year=getattr(a, 'mid_year', False))
            titulo = (f"EV/EBITDA justo ({base}) | linhas=g | colunas=ROIC | "
                      f"WACC={w*100:.1f}% d={d*100:.1f}% t={t*100:.1f}% CAP={a.n} TV={tv}")
            imprime_grade(titulo, "ROIC", cols, linhas, cr, cg, custo_capital=w, tv=tv)
        else:
            ke = pc(a.ke); gde, nde = pc(a.gde) or 0, pc(a.nde) or 0
            cr, cg = pc(getattr(a, 'centro_roe')), pc(a.centro_g)
            cols, linhas = grade_pe(ke, gde, nde, a.n, cr, cg, pc(a.passo_roe), pc(a.passo_g),
                                    base=base, tv=tv, roe_tv=pc(getattr(a, 'roe_tv')), gp=gp,
                                    roe_book=pc(getattr(a, 'roe_book')),
                                    politica_tv=getattr(a, 'politica_tv', 'continua'),
                                    mid_year=getattr(a, 'mid_year', False))
            titulo = (f"P/L justo ({base}) | linhas=g | colunas=ROE | "
                      f"Ke={ke*100:.1f}% CAP={a.n} TV={tv}")
            imprime_grade(titulo, "ROE ", cols, linhas, cr, cg, custo_capital=ke, tv=tv)

    elif a.cmd == 'normaliza':
        eb, da = a.ebitda_base, a.da
        pb, pn = a.preco_base, a.preco_novo
        vol = a.vol if a.vol is not None else (a.rev_driver / pb if (a.rev_driver is not None and pb) else None)
        if vol is None or eb is None or da is None or pb is None or pn is None:
            print(json.dumps({'erro': 'requer --ebitda-base --da --preco-base --preco-novo e (--vol ou --rev-driver)'}, ensure_ascii=False)); return
        eb_novo, d_base, d_novo = normaliza_ebitda(eb, da, pb, pn, vol)
        gap = pn / pb - 1
        elast = elasticidade_operacional(vol * pb, eb)  # receita do driver / métrica-base
        impacto = abs(elast * gap)
        limiar = (a.limiar or 10.0) / 100.0
        out = {'preco_base': pb, 'preco_novo': pn, 'gap_preco_%': round(gap * 100, 1),
               'volume_driver': round(vol, 3), 'delta_EBITDA_por_unidade_preco': round(vol, 3),
               'elasticidade_operacional': round(elast, 4),
               'impacto_%': round(impacto * 100, 1),
               'criterio_gate': f'impacto = |elasticidade × gap| > {limiar*100:.0f}% — NUNCA o gap bruto',
               'EBITDA_base': round(eb, 2), 'EBITDA_normalizado': round(eb_novo, 2),
               'd_base_%': round(d_base * 100, 1), 'd_normalizado_%': round(d_novo * 100, 1),
               'nota': 'volume e custo fixos; D&A absoluta fixa (por unidade produzida, nao por preco) => d cai quando preco sobe; ROIC contabil sobe ciclicamente — NAO usar ROIC de pico no motor de g'}
        if impacto > limiar:
            out['GATE'] = (f'IMPACTO {impacto*100:+.1f}% = |elast {elast:.2f} × gap {gap*100:+.1f}%| '
                           f'> {limiar*100:.0f}% — rode cenario normalizado a spot ALEM do periodo-base '
                           f'e declare os dois, e reverta o nivel implicito (`nivel`)')
        else:
            out['gate_nao_disparou'] = (f'impacto {impacto*100:.1f}% <= {limiar*100:.0f}%: o periodo-base é '
                                        f'representativo por MATERIALIDADE (gap {gap*100:+.1f}% × elast '
                                        f'{elast:.2f}). Reporte os números assim mesmo.')
        # [v9.14 / rodada 3, §13.2 — regime monetário do modelo] a normalização deixa a métrica em
        # PREÇOS DE HOJE e a regra "nível não é taxa" expulsa o preço do g: os fluxos ficam reais
        # na moeda do driver. Sob convenção terminal sem crescimento de preço (convergencia, ou
        # gordon com gp≈0), o modelo então assume o driver CONGELADO nominal — caindo ~inflação
        # a.a. em termos REAIS, em perpetuidade — enquanto o Ke da regra travada é NOMINAL. Fluxo
        # real a taxa nominal é o erro de Modigliani-Cohn; valeu ~28% na FNV, sem sintoma numérico.
        tvc_norm = tv_canon(a.tv) if a.tv else None
        if tvc_norm == 'convergencia' or (tvc_norm == 'gordon' and (pc(a.gp) or 0.0) < 1e-9):
            out['aviso_regime_driver'] = (
                'REGIME DO DRIVER NO TERMINAL: a métrica foi normalizada ao preço de HOJE e a '
                f"convenção '{tvc_norm}' não dá crescimento de preço ao terminal — o modelo está "
                'assumindo o driver CONGELADO em termos nominais (= caindo ~inflação a.a. em '
                'termos REAIS, em perpetuidade) descontado a custo de capital NOMINAL. Isso é uma '
                'HIPÓTESE substantiva, não um default neutro. Fisher admite duas rotas EXATAS: '
                '(A) fluxos reais a custo REAL, com (1+K_real)=(1+K_nom)/(1+π); (B) fluxos NOMINAIS, '
                'inflacionando TODO o horizonte explícito e o terminal, a K nominal. Conceder inflação '
                'APENAS no terminal (gordon, rentabilidade terminal muito alta, gp=inflação) é uma '
                'APROXIMAÇÃO terminal-only, não equivalência de Fisher. Entregue as âncoras congelado × '
                'acompanha inflação e não misture fluxo real com taxa nominal.')
        if a.g is not None and a.roic is not None and a.wacc is not None:
            g, roic, w = pc(a.g), pc(a.roic), pc(a.wacc)
            kw = dict(tv=a.tv, roic_tv=pc(getattr(a, 'roic_tv')), gp=pc(a.gp) or 0.0,
                      roic_book=pc(getattr(a, 'roic_book')))
            mn = ev_nopat(g, roic, w, a.n, **kw); me = mn * (1 - d_novo) * (1 - pc(a.tax))
            ev = me * eb_novo
            out['EV/EBITDA_justo_norm'] = round(me, 4); out['EV_norm'] = round(ev, 2)
            if a.nd is not None:
                eq = ev - a.nd; out['Equity_norm'] = round(eq, 2)
                if a.acoes: out['Preco_acao_norm'] = round(eq / a.acoes, 2)
        jprint(out)

    elif a.cmd == 'drivers':
        ds = []
        for spec in a.driver:
            partes = spec.split(':')
            if len(partes) < 3:
                print(json.dumps({'erro': f'driver mal formado: {spec} (use NOME:BASE:SPOT[:ELAST])'},
                                 ensure_ascii=False)); return
            if len(partes) > 3 and partes[3].strip().lower() == 'auto':
                if len(partes) < 6:
                    print(json.dumps({'erro': f'{spec}: "auto" exige NOME:BASE:SPOT:auto:LINHA:METRICA[:custo]'},
                                     ensure_ascii=False)); return
                sentido = partes[6].strip().lower() if len(partes) > 6 else 'receita'
                if sentido not in ('receita', 'custo'):
                    print(json.dumps({'erro': f'{spec}: sentido deve ser "receita" ou "custo"'},
                                     ensure_ascii=False)); return
                ds.append({'nome': partes[0], 'base': float(partes[1]), 'spot': float(partes[2]),
                           'elast': None, 'receita_driver': float(partes[4]),
                           'metrica_base': float(partes[5]), 'sentido': sentido})
            else:
                el = float(partes[3]) if len(partes) > 3 else 1.0
                ds.append({'nome': partes[0], 'base': float(partes[1]), 'spot': float(partes[2]),
                           'elast': el, 'sentido': 'custo' if el < 0 else 'receita'})
        jprint(registro_drivers(ds, limiar=a.limiar / 100.0))

    elif a.cmd == 'nivel':
        _rec = None
        if a.da_absoluta is not None and a.tv is not None and a.g is not None \
                and a.roic is not None and a.wacc is not None and a.tax is not None:
            _rec = nivel_recalculado(a.alvo_valor, a.metrica_base, a.da_absoluta, pc(a.tax),
                                     pc(a.g), pc(a.roic), pc(a.wacc), a.n, tv=a.tv,
                                     roic_tv=pc(getattr(a, 'roic_tv', None)), gp=pc(a.gp) or 0.0,
                                     roic_book=pc(getattr(a, 'roic_book', None)),
                                     mid_year=getattr(a, 'mid_year', False))
        jprint(nivel_implicito(a.alvo_valor, a.multiplo, a.metrica_base,
                               vol=a.vol, preco_base=a.preco_base,
                               consenso_t1=a.consenso_t1, consenso_t2=a.consenso_t2,
                               recalculado=_rec))

    elif a.cmd == 'degrau':
        eqside = a.roe is not None
        rent, custo = (pc(a.roe), pc(a.ke)) if eqside else (pc(a.roic), pc(a.wacc))
        g = pc(a.g); mm = pc(a.m) if a.m is not None else 1.0
        gde, nde = pc(a.gde) or 0, pc(a.nde) or 0
        rb = pc(getattr(a, 'roe_book')) if eqside else pc(getattr(a, 'roic_book'))
        kw = (dict(tv=a.tv, roe_tv=pc(getattr(a, 'roe_tv')) or rent, gp=pc(a.gp) or 0.0,
                   roe_book=rb,
                   politica_tv=getattr(a, 'politica_tv', 'continua')) if eqside
              else dict(tv=a.tv, roic_tv=pc(getattr(a, 'roic_tv')) or rent, gp=pc(a.gp) or 0.0,
                        roic_book=rb))
        mult = (lambda gg, rr: pe(gg, rr, custo, a.n, gde, nde, **kw)) if eqside \
               else (lambda gg, rr: ev_nopat(gg, rr, custo, a.n, **kw))
        base_m = mult(g, rent); base_v = base_m * rent
        out = {'lado': 'equity (P/L, P/VP)' if eqside else 'firm (EV/NOPAT, EV/Capital)',
               'indice_atual_%': a.indice_atual, 'm_eficiencia_marginal': round(mm, 3),
               'anos_transicao': a.anos,
               'REGRA': 'o degrau entra como RENTABILIDADE; g permanece INALTERADO; '
                        'a rentabilidade terminal (roe-tv/roic-tv) NÃO acompanha o degrau '
                        '— a competição não deixa o spread marginal sobreviver ao CAP',
               'base': {'rentabilidade_%': round(rent * 100, 2), 'multiplo': round(base_m, 4),
                        'multiplo_x_rentab': round(base_v, 4)},
               'niveis': []}
        if g is not None:
            out['diagnosticos'] = (diag_eq(g, rent, custo, gde, nde, tv=a.tv, n=a.n, roe_book=rb, rf=None if getattr(a, 'rf', None) is None else a.rf / 100, moeda=getattr(a, 'moeda', None),
                                           roe_tv=kw.get('roe_tv'),
                                           politica_tv=kw.get('politica_tv', 'continua'),
                                           gp=kw.get('gp', 0.0)) if eqside
                                   else diag_firm(g, rent, custo, tv=a.tv, n=a.n, roic_book=rb, rf=None if getattr(a, 'rf', None) is None else a.rf / 100, moeda=getattr(a, 'moeda', None),
                                                  roic_tv=kw.get('roic_tv')))
        if tv_canon(a.tv) == 'book' and rb is None:
            out['ALERTA_CONVENCAO_BOOK'] = (
                "'book' no degrau sem --roe-book/--roic-book: o TV usaria a rentabilidade PÓS-degrau "
                "(marginal × h) no papel de MÉDIO do estoque — conflação marginal×médio AGRAVADA pelo "
                "degrau (o TV encolhe conforme o degrau cresce, contradizendo a regra de que a "
                "rentabilidade terminal não acompanha). Informe a média contábil via --roe-book/"
                "--roic-book ou use tv=gordon/convergencia.")
        alvos = [float(x) for x in (a.indice_alvo or '').split(',') if x.strip()]
        for alvo in alvos:
            h = fator_h(a.indice_atual, alvo)
            r2 = rentab_pos_degrau(rent, h, mm)
            m2 = mult(g, r2); v2 = m2 * r2
            v_tr, f_tr = valor_transicionado(base_v, v2, custo, a.anos, a.perfil_transicao)
            linha = {'indice_alvo_%': alvo, 'h': round(h, 4),
                     'rentabilidade_pos_%': round(r2 * 100, 2), 'multiplo': round(m2, 4),
                     'multiplo_x_rentab': round(v2, 4),
                     'com_transicao': round(v_tr, 4), 'fator_transicao': round(f_tr, 4),
                     'perfil_transicao': a.perfil_transicao}
            if a.vpa:
                linha['preco_acao'] = round(v_tr * a.vpa / (a.fx or 1.0), 2)
            if r2 > max(2.0 * custo, 0.30):
                linha['ALERTA'] = ('rentabilidade pós-degrau implausível como estado estacionário '
                                   '— aritmética, não economia: nenhum equilíbrio competitivo a sustenta. '
                                   'Reporte como teto da alavanca, não como cenário.')
            if g is not None and g / r2 > 1:
                linha['ALERTA_RiR'] = f'RiR = g/rentab = {g/r2*100:.0f}% > 100% — payout negativo'
            out['niveis'].append(linha)
        if a.alvo_pvp is not None and rent and mm:
            f = lambda B: mult(g, rentab_pos_degrau(rent, fator_h(a.indice_atual, B), mm)) \
                          * rentab_pos_degrau(rent, fator_h(a.indice_atual, B), mm) - a.alvo_pvp
            raizes = solve(f, 1.0, 60.0)
            out['reversa_indice_implicito_%'] = [round(r, 2) for r in raizes] or \
                'sem raiz na faixa 1–60% — o alvo não é reconciliável só por alavancagem'
            out['reversa_nota'] = ('índice-alvo que reconcilia o múltiplo-alvo dado. Combine com a '
                                  'reversa em rentabilidade: os dois vetores são SUBSTITUTOS e formam '
                                  'uma curva iso-valor — o preço paga por um, raramente pelos dois.')
        if alvos:
            out['classificacao'] = classificacao_degrau(
                g, rent, custo, a.n, fator_h(a.indice_atual, alvos[-1]),
                a.anos or 1, lado=('equity' if eqside else 'firm'), gde=gde, nde=nde, **kw)
        out['travas_obrigatorias'] = [
            'o degrau NÃO é grátis: consome o colchão — é uma opção vendida sobre a solvência',
            'verificar a restrição EFETIVA (funding, originação, share): frequentemente satura antes do capital, o que força m < 1 por construção e não por pessimismo',
            'o piso regulatório teórico não é o piso administrável — declarar os dois',
            'COERÊNCIA: o deployment VIOLA a premissa de D/E (ou alavancagem regulatória) constante '
            'durante a trajetória. O resultado vale para o ESTADO ESTACIONÁRIO PÓS-deployment, com '
            'a nova alavancagem estabilizada — nunca para o caminho. É exatamente por isso que (i) '
            'existe fator de transição sobre o incremento e (ii) a rentabilidade terminal não '
            'acompanha o degrau.',
        ]
        jprint(out)

if __name__ == '__main__':
    main()
