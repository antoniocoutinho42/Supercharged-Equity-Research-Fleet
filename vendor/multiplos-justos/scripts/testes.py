#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Múltiplos Justos — suíte de validação INDEPENDENTE (além dos anchors do selftest).
Reprodução de anchor ≠ validação: aqui vão property-based tests (identidades que devem
valer em qualquer combinação válida), reconciliação por fluxos construídos explicitamente
(DCF ↔ renda residual; FCFE@Ke_t ↔ APV), e boundary tests (limites e regiões degeneradas).
Uso de release: rode em DUAS invocações frescas:
  python scripts/testes.py --phase model
  python scripts/testes.py --phase cli
Cada comando sai com código 0 se sua fase passar. A separação evita que ambientes com quota de
subprocessos produzam falso negativo depois de dezenas de execuções reais do CLI.
"""
import sys, itertools, os, re

# [v9.9] A suíte imprime ≡ ↑ ↓ e acentos. Em locale não-UTF-8 (cp1252, Windows PT-BR) isso
# estoura em UnicodeEncodeError assim que a saída é redirecionada — falha de codec, não de
# teste. Fixar aqui mantém a regra 10: nada depende de o analista lembrar de exportar PYTHONUTF8.
for _fluxo in (sys.stdout, sys.stderr):
    if hasattr(_fluxo, 'reconfigure'):
        _fluxo.reconfigure(encoding='utf-8')
from justos import (ev_nopat, ev_ebitda, pe, apv_recursao, solve, solve_full, identificacao,
                    tv_canon, normaliza_ebitda, fator_h, rentab_pos_degrau,
                    elasticidade_exposicao, elasticidade_operacional, registro_drivers)

FALHAS = []
def check(nome, cond, detalhe=''):
    if not cond:
        FALHAS.append(f'{nome} {detalhe}')
        print(f'  FALHOU: {nome} {detalhe}')

# ---------- 1. PROPERTY TESTS ----------
def prop_neutralidade():
    """[identidade] ROIC = WACC ⟹ EV/NOPAT forward = 1/W, para 'book' e 'convergencia',
    em qualquer g, n, W válidos. As duas convenções coincidem EXATAMENTE nesse ponto."""
    tot = 0
    for W in (0.05, 0.07, 0.09, 0.12, 0.18, 0.25):
        for n in (1, 3, 5, 10, 20, 40):
            for g in (-0.05, 0.0, 0.02, 0.04, 0.049):
                for tv in ('book', 'convergencia'):
                    tot += 1
                    m = ev_nopat(g, W, W, n, tv=tv) / (1 + g)
                    check('neutralidade', abs(m - 1 / W) < 1e-9, f'({tv} W={W} n={n} g={g}: {m})')
    print(f'  neutralidade ROIC=WACC: {tot} combinações')

def prop_neutralidade_marginal_book():
    """[condição completa — auditoria matemática Fase 1] Sob 'book', a neutralidade exige
    ROIC marginal = WACC E ROIC book = WACC simultaneamente. Casos cruzados:
    (a) marginal=W, book≠W ⟹ forward ≠ 1/W sob 'book' (mas = 1/W sob 'convergencia',
        cujo TV não referencia o book);
    (b) marginal≠W, book=W ⟹ forward ≠ 1/W sob 'book';
    (c) marginal=book=W ⟹ forward = 1/W (identidade preservada)."""
    tot = 0
    for W in (0.05, 0.07, 0.12):
        for n in (5, 10, 20):
            for g in (0.0, 0.03, 0.049):
                for rb in (0.03, 0.20, 0.40):
                    if abs(rb - W) < 1e-9:
                        continue
                    tot += 3
                    # (a) marginal=W, book≠W: book quebra; convergencia preserva
                    ma = ev_nopat(g, W, W, n, tv='book', roic_book=rb) / (1 + g)
                    check('marg=W book≠W quebra (book)', abs(ma - 1 / W) > 1e-6,
                          f'(W={W} n={n} g={g} rb={rb}: {ma})')
                    mc = ev_nopat(g, W, W, n, tv='convergencia') / (1 + g)
                    check('marg=W neutro (convergencia)', abs(mc - 1 / W) < 1e-9,
                          f'(W={W} n={n} g={g}: {mc})')
                    # (b) marginal≠W, book=W: também quebra sob book — EXCETO em g=0, onde
                    # FCFF = NOPAT (o marginal só entra via g/ROIC) e a neutralidade vale
                    mb = ev_nopat(g, rb, W, n, tv='book', roic_book=W) / (1 + g)
                    if abs(g) < 1e-12:
                        check('marg≠W book=W g=0 neutro (book)', abs(mb - 1 / W) < 1e-9,
                              f'(W={W} n={n} marg={rb}: {mb})')
                    else:
                        check('marg≠W book=W quebra (book)', abs(mb - 1 / W) > 1e-6,
                              f'(W={W} n={n} g={g} marg={rb}: {mb})')
                # (c) conjunta: marginal=book=W, book explícito
                tot += 1
                mj = ev_nopat(g, W, W, n, tv='book', roic_book=W) / (1 + g)
                check('marg=book=W neutro (book)', abs(mj - 1 / W) < 1e-9,
                      f'(W={W} n={n} g={g}: {mj})')
    print(f'  neutralidade marginal×book (casos cruzados): {tot} checagens')

def prop_convergencia_gp():
    """[identidade] 'convergencia' ≡ 'gordon' com ROIC_TV = W, invariante a gp."""
    tot = 0
    for W in (0.06, 0.10, 0.15):
        for roic in (0.04, 0.08, 0.20, 0.50):
            for g in (0.0, 0.03, 0.06):
                cv = ev_nopat(g, roic, W, 10, tv='convergencia')
                for gp in (0.0, 0.02, W * 0.5, W * 0.9):
                    tot += 1
                    gv = ev_nopat(g, roic, W, 10, tv='gordon', roic_tv=W, gp=gp)
                    check('convergencia≡gordon(W)', abs(cv - gv) < 1e-9,
                          f'(W={W} roic={roic} g={g} gp={gp})')
    print(f'  convergencia ≡ gordon(ROIC_TV=W), invariante a gp: {tot} combinações')

def prop_monotonia_roic():
    """[propriedade condicionada à convenção] múltiplo em ROIC: DECRESCENTE sob 'book',
    CRESCENTE sob 'convergencia' e sob 'gordon'. É o coração da correção da v8: o sinal
    depende da convenção, não é lei econômica."""
    roics = [0.04, 0.06, 0.08, 0.10, 0.15, 0.25, 0.50]
    for W in (0.07, 0.12):
        for g in (0.0, 0.03):
            mb = [ev_nopat(g, r, W, 10, tv='book') for r in roics]
            mc = [ev_nopat(g, r, W, 10, tv='convergencia') for r in roics]
            mg = [ev_nopat(g, r, W, 10, tv='gordon', roic_tv=0.20, gp=0.03) for r in roics]
            check('book decresce em ROIC', all(a >= b - 1e-12 for a, b in zip(mb, mb[1:])), f'(W={W} g={g})')
            check('convergencia cresce em ROIC', all(a <= b + 1e-12 for a, b in zip(mc, mc[1:])), f'(W={W} g={g})')
            check('gordon cresce em ROIC', all(a <= b + 1e-12 for a, b in zip(mg, mg[1:])), f'(W={W} g={g})')
    print('  monotonicidade em ROIC por convenção: book ↓, convergencia ↑, gordon ↑')

def prop_gradiente_g():
    """[propriedade, base forward] sinal de ∂(múltiplo fwd)/∂g = sinal do spread,
    sob 'convergencia' (onde o terminal não contamina com o book)."""
    for W in (0.07, 0.12):
        for roic, sinal in ((W - 0.02, -1), (W + 0.03, +1)):
            m0 = ev_nopat(0.0, roic, W, 10, tv='convergencia')
            m1 = ev_nopat(0.04, roic, W, 10, tv='convergencia') / 1.04
            check('gradiente em g (fwd) = sinal do spread', (m1 - m0) * sinal > 0,
                  f'(W={W} roic={roic})')
    print('  sinal do gradiente em g (forward) = sinal do spread, sob convergencia')

def prop_pe_caixa():
    """[v9.30] Na `book`, clean surplus implica Div + E_n: caixa/E é neutro e ROE=Ke,
    com book=Ke, devolve P/L forward = 1/Ke para qualquer caixa. Nas convenções sem book
    terminal, o módulo FCFE proporcional continua podendo carregar efeito-caixa."""
    for ke in (0.10, 0.15, 0.22):
        for g in (0.0, 0.03, 0.06):
            for cx in (0.0, 0.10, 0.20, 0.50):
                m = pe(g, ke, ke, 10, cx, 0.0, tv='book') / (1 + g)
                check('neutralidade equity book independe de caixa', abs(m - 1 / ke) < 1e-9,
                      f'(ke={ke} g={g} caixa={cx})')
        # `convergencia` preserva o módulo FCFE legado e, com caixa, não precisa ser neutra.
        c0 = pe(0.06, ke, ke, 10, 0.0, 0.0, tv='convergencia') / 1.06
        c2 = pe(0.06, ke, ke, 10, 0.20, 0.0, tv='convergencia') / 1.06
        check('módulo não-book ainda distingue caixa', c2 > c0 + 1e-9, f'(ke={ke})')
    print('  neutralidade equity: book = Div + E_n e é invariante a caixa; não-book mantém módulo FCFE')

# ---------- 2. RECONCILIATION TESTS ----------
def rec_dcf_eva():
    """[identidade Preinreich–Lücke] sob 'book': EV = IC0 + Σ_{t≤n} IC_{t-1}(ROIC−W)/(1+W)^t,
    com fluxos construídos explicitamente (não a fórmula do motor)."""
    for (g, roic, W, n) in [(0.05, 0.10, 0.07, 10), (0.03, 0.20, 0.09, 15),
                            (0.08, 0.30, 0.12, 5), (0.02, 0.05, 0.07, 20)]:
        IC = (1 + g) / roic  # IC0 tal que NOPAT1 = IC0·ROIC, normalizado a NOPAT0 = 1
        v, ic_t = IC, IC
        for t in range(1, n + 1):
            v += (ic_t * roic - W * ic_t) / (1 + W) ** t
            ic_t *= (1 + g)
        dcf = ev_nopat(g, roic, W, n, tv='book')
        check('DCF ↔ EVA (book)', abs(dcf - v) < 1e-9, f'(g={g} roic={roic} W={W} n={n}: {dcf} vs {v})')
    print('  DCF ↔ renda residual (book): fecha por fluxos construídos')

def rec_fluxos_explicitos():
    """[reconciliação] motor vs. soma explícita independente de FCFF (construída aqui)."""
    for tv, kw in (('book', {}), ('convergencia', {}), ('gordon', dict(roic_tv=0.18, gp=0.025))):
        g, roic, W, n = 0.04, 0.12, 0.08, 12
        s = sum((1 - g / roic) * (1 + g) ** t / (1 + W) ** t for t in range(1, n + 1))
        if tv == 'book':
            s += (1 + g) ** (n + 1) / (roic * (1 + W) ** n)
        elif tv == 'convergencia':
            s += (1 + g) ** (n + 1) / (W * (1 + W) ** n)
        else:
            s += (1 + g) ** (n + 1) * (1 - kw['gp'] / kw['roic_tv']) / (W - kw['gp']) / (1 + W) ** n
        m = ev_nopat(g, roic, W, n, tv=tv, **kw)
        check('motor ↔ soma independente', abs(m - s) < 1e-12, f'({tv})')
    print('  motor ↔ soma explícita independente: fecha nas três convenções')

def rec_apv():
    """[reconciliação vF8] FCFE@Ke_t = E0, FCFF@WACC_t = V0, Ke dinâmico = fórmula Fernández,
    nos anchors da planilha E em parâmetros perturbados."""
    casos = [dict(fcff1=22.184, g=0.11, n=10, ku=0.20, kd=0.142714285714286, tax=0.30,
                  d0=35.0, fcff_tv=50.5317555785773),
             dict(fcff1=40.0, g=0.06, n=8, ku=0.14, kd=0.09, tax=0.34, d0=120.0),
             dict(fcff1=10.0, g=0.00, n=15, ku=0.11, kd=0.07, tax=0.25, d0=20.0, gtv=0.02)]
    for c in casos:
        r = apv_recursao(**c)
        check('APV check4 (FCFE@Ke_t=E0)', abs(r['check_FCFE_at_Ke_t_igual_E0']) < 1e-6, str(c['fcff1']))
        check('APV check6 (FCFF@WACC_t=V0)', abs(r['check_FCFF_at_WACC_t_igual_V0']) < 1e-6, str(c['fcff1']))
        check('APV check5 (Ke=Fernández)', abs(r['check_Ke_dinamico_igual_formula_Fernandez']) < 1e-9, str(c['fcff1']))
    a = apv_recursao(**casos[0])
    check('APV anchor V0', abs(a['V0'] - 193.659212) < 1e-4)
    check('APV anchor E0', abs(a['E0'] - 158.659212) < 1e-4)
    print('  APV: checks 4/5/6 fecham nos anchors vF8 e em parâmetros perturbados')

# ---------- 2b. C1 — POLÍTICA DE CAIXA NO TERMINAL (correção da auditoria v8) ----------
def rec_fcfe_tv():
    """[força bruta] pe(gordon, politica_tv='continua') vs simulação ano a ano do balanço
    terminal (rota Div + Δcaixa da planilha, clean surplus), 4000 anos, 300 sorteios."""
    import random
    random.seed(7); pior = 0.0
    for _ in range(300):
        ke = random.uniform(0.07, 0.30); roe = random.uniform(0.06, 0.9)
        g = random.uniform(0.0, min(0.35, roe * 0.9)); n = random.randint(2, 25)
        gde = random.uniform(0.0, 1.2); nde = random.uniform(0.0, gde)
        roetv = random.uniform(0.05, 0.6); gp = random.uniform(0.0, ke * 0.85)
        caixa = gde - nde
        m = pe(g, roe, ke, n, gde, nde, tv='gordon', roe_tv=roetv, gp=gp, politica_tv='continua')
        ret = (1 - g / roe) + caixa * (g / roe)
        s = sum(ret * (1 + g) ** t / (1 + ke) ** t for t in range(1, n + 1))
        E = (1 + g) ** (n + 1) / roetv        # equity re-baseado no ROE terminal (LL0 = 1)
        pv = 0.0; df = (1 + ke) ** (-n)
        for _t in range(4000):
            df /= (1 + ke)
            LL = roetv * E                    # LL_{t+1} = ROE_TV · E_t
            div = LL - gp * E                 # clean surplus: Div = LL − ΔE
            dcash = gp * caixa * E            # Δcaixa com proporção constante
            termo = (div + dcash) * df
            pv += termo
            if abs(termo) < 1e-16 * max(abs(pv), 1.0):   # cauda geométrica esgotada
                break                                     # (evita overflow E×underflow df)
            E *= (1 + gp)
        rel = abs((s + pv) - m) / abs(m)
        pior = max(pior, rel)
        check('C1 força bruta 4000 anos', rel < 1e-9, f'(rel={rel:.2e})')
    print(f'  C1 força bruta: 300 sorteios, pior erro relativo {pior:.1e}')

def rec_fcfe_canonico_tv():
    """[identidade contábil no terminal] FCFE canônico (FCFF − juros(1−t) + ΔD) == Div + Δcaixa
    no balanço terminal crescendo a gp — a prova de 3 rotas da planilha (linhas 226–235)
    estendida ao terminal. 200 sorteios."""
    import random
    random.seed(11)
    for _ in range(200):
        roetv = random.uniform(0.05, 0.5); gp = random.uniform(0.0, 0.10)
        gde = random.uniform(0.0, 1.2); nde = random.uniform(0.0, gde)
        kd = random.uniform(0.02, 0.20); tax = random.uniform(0.0, 0.45)
        E0 = random.uniform(10, 500)
        caixa = gde - nde
        E1 = E0 * (1 + gp)
        D0, D1 = gde * E0, gde * E1
        c0, c1 = caixa * E0, caixa * E1
        LL = roetv * E0
        r1 = (LL - (E1 - E0)) + (c1 - c0)                       # Div + Δcaixa
        nopat = LL + kd * D0 * (1 - tax)                         # NOPAT = LL + juros(1−t)
        ic0, ic1 = E0 + D0 - c0, E1 + D1 - c1                    # IC = ativos − caixa
        fcff = nopat - (ic1 - ic0)
        r2 = fcff - kd * D0 * (1 - tax) + (D1 - D0)              # FCFF − juros(1−t) + ΔD
        r3 = LL * ((1 - gp / roetv) + caixa * (gp / roetv))      # fator do motor
        check('C1 identidade canônica', abs(r1 - r2) < 1e-9 and abs(r1 - r3) < 1e-9,
              f'({r1:.6f} {r2:.6f} {r3:.6f})')
    print('  C1 identidade canônica: Div+Δcaixa == FCFF−juros(1−t)+ΔD == fator do motor, 200 sorteios')

def prop_politica_tv():
    """[propriedades da correção] encerra ≡ fórmula antiga; delta fechado; flags inertes fora
    do caso; formas fechadas em ROE_TV = Ke; invariância equity sob 'encerra' preservada."""
    import random
    random.seed(13)
    for _ in range(500):
        ke = random.uniform(0.07, 0.30); roe = random.uniform(0.06, 0.9)
        g = random.uniform(0.0, min(0.35, roe * 0.9)); n = random.randint(2, 25)
        gde = random.uniform(0.0, 1.2); nde = random.uniform(0.0, 1.2)
        roetv = random.uniform(0.05, 0.6); gp = random.uniform(0.0, ke * 0.85)
        caixa = gde - nde
        enc = pe(g, roe, ke, n, gde, nde, tv='gordon', roe_tv=roetv, gp=gp, politica_tv='encerra')
        ret = (1 - g / roe) + caixa * (g / roe)
        antiga = sum(ret * (1 + g) ** t / (1 + ke) ** t for t in range(1, n + 1)) \
                 + (1 + g) ** (n + 1) * (1 - gp / roetv) / (ke - gp) / (1 + ke) ** n
        check('encerra ≡ fórmula antiga', abs(enc - antiga) < 1e-12)
        cont = pe(g, roe, ke, n, gde, nde, tv='gordon', roe_tv=roetv, gp=gp, politica_tv='continua')
        delta = (1 + g) ** (n + 1) * caixa * (gp / roetv) / (ke - gp) / (1 + ke) ** n
        check('delta continua−encerra fechado', abs((cont - enc) - delta) < 1e-9 * max(1.0, abs(delta)))
        z1 = pe(g, roe, ke, n, 0.4, 0.4, tv='gordon', roe_tv=roetv, gp=gp, politica_tv='continua')
        z2 = pe(g, roe, ke, n, 0.4, 0.4, tv='gordon', roe_tv=roetv, gp=gp, politica_tv='encerra')
        check('gde=nde ⟹ flag indiferente', z1 == z2)
        for tvx in ('book', 'convergencia'):
            b1 = pe(g, roe, ke, n, gde, nde, tv=tvx, politica_tv='continua')
            b2 = pe(g, roe, ke, n, gde, nde, tv=tvx, politica_tv='encerra')
            check('book/convergencia insensíveis ao flag', b1 == b2 or (b1 != b1 and b2 != b2))
    ke, g, roe, n, caixa = 0.12, 0.05, 0.20, 10, 0.30
    for gp in (0.0, 0.02, 0.05, 0.09):
        m = pe(g, roe, ke, n, caixa, 0.0, tv='gordon', roe_tv=ke, gp=gp, politica_tv='continua')
        ret = (1 - g / roe) + caixa * (g / roe)
        alvo = sum(ret * (1 + g) ** t / (1 + ke) ** t for t in range(1, n + 1)) \
               + (1 + g) ** (n + 1) * ((ke - gp) + caixa * gp) / (ke * (ke - gp)) / (1 + ke) ** n
        check('forma fechada ROE_TV=Ke (continua)', abs(m - alvo) < 1e-12, f'(gp={gp})')
    for gp in (0.0, 0.03, 0.08):
        e1 = pe(0.05, 0.20, 0.12, 10, 0.30, 0.0, tv='convergencia')
        e2 = pe(0.05, 0.20, 0.12, 10, 0.30, 0.0, tv='gordon', roe_tv=0.12, gp=gp, politica_tv='encerra')
        check('convergencia ≡ gordon(Ke) sob encerra', abs(e1 - e2) < 1e-9, f'(gp={gp})')
    print('  C1 propriedades: encerra≡antiga, delta fechado, flags inertes fora do caso, formas fechadas')

# ---------- 2c. C3 / D2 / D4 — convenção temporal, base do alvo, elasticidade com sinal ----------
def prop_mid_year():
    """[C3] mid-year multiplica por (1+custo)^0.5 exatamente, é neutro por default, e não
    contamina a neutralidade (a razão mid/fim é constante = (1+W)^0.5 em qualquer ponto)."""
    import random
    random.seed(17)
    for _ in range(400):
        w = random.uniform(0.03, 0.30); roic = random.uniform(0.02, 1.0)
        g = random.uniform(-0.2, min(0.4, roic * 0.95)); n = random.randint(1, 30)
        tv = random.choice(['book', 'convergencia'])
        a = ev_nopat(g, roic, w, n, tv=tv)
        b = ev_nopat(g, roic, w, n, tv=tv, mid_year=True)
        check('mid_year = fator exato', abs(b - a * (1 + w) ** 0.5) < 1e-12 * max(1, abs(a)))
        check('default = fim de ano', ev_nopat(g, roic, w, n, tv=tv, mid_year=False) == a)
        ke = w; roe = roic
        p = pe(g, roe, ke, n, 0.1, 0.0, tv=tv)
        q = pe(g, roe, ke, n, 0.1, 0.0, tv=tv, mid_year=True)
        check('mid_year equity = fator exato', abs(q - p * (1 + ke) ** 0.5) < 1e-12 * max(1, abs(p)))
    # neutralidade sob mid-year: forward = (1+W)^0.5 / W
    for w in (0.06, 0.11, 0.19):
        for g in (0.0, 0.03, 0.05):
            m = ev_nopat(g, w, w, 12, tv='book', mid_year=True) / (1 + g)
            check('neutralidade mid-year', abs(m - (1 + w) ** 0.5 / w) < 1e-9)
    print('  C3 mid-year: fator exato (1+custo)^0.5, inerte por default, neutralidade preservada')

def prop_alvo_base():
    """[D2] resolver com alvo forward ≡ resolver com alvo corrente convertido a (1+g) na raiz.
    Verifica o caso circular (resolver='g'), onde a conversão ingênua erraria."""
    import random
    random.seed(19); casos = 0
    for _ in range(300):
        w = random.uniform(0.06, 0.20); roic = random.uniform(w * 1.05, 0.6)
        g0 = random.uniform(0.0, min(0.25, roic * 0.85)); n = random.randint(3, 20)
        M_fwd = ev_nopat(g0, roic, w, n, tv='convergencia') / (1 + g0)   # alvo NTM verdadeiro
        f = lambda x: ev_nopat(x, roic, w, n, tv='convergencia') / (1 + x) - M_fwd
        roots, _ = solve_full(f, -0.6, min(0.6, roic * 0.999), ref=M_fwd)
        ok = any(abs(r - g0) < 1e-4 for r in roots)
        check('D2 alvo forward recupera o g verdadeiro', ok, f'(g0={g0:.4f} roots={roots})')
        # e o erro de usar a base errada é material e do tamanho previsto
        f_err = lambda x: ev_nopat(x, roic, w, n, tv='convergencia') - M_fwd
        r_err, _ = solve_full(f_err, -0.6, min(0.6, roic * 0.999), ref=M_fwd)
        if r_err and g0 > 0.02:
            casos += 1
            check('D2 base errada desloca a raiz', abs(r_err[0] - g0) > 1e-6)
    print(f'  D2 base do alvo: forward recupera g verdadeiro; base errada desloca ({casos} casos)')

def prop_elasticidade_sinal():
    """[D4] elasticidade de driver de custo é negativa, de receita positiva; compat com a
    versão antiga; compensação líquida vs brutos no registro."""
    check('receita positiva', elasticidade_exposicao(730.95, 446.43, 'receita') > 0)
    check('custo negativo', elasticidade_exposicao(80.0, 446.43, 'custo') < 0)
    check('simetria', abs(elasticidade_exposicao(80.0, 446.43, 'custo')
                          + elasticidade_exposicao(80.0, 446.43, 'receita')) < 1e-15)
    check('compat anchor v7', abs(elasticidade_operacional(730.95, 446.43) - 1.6373227605671663) < 1e-12)
    r = registro_drivers([{'nome': 'preco', 'base': 100.0, 'spot': 120.0, 'elast': None,
                           'receita_driver': 500.0, 'metrica_base': 250.0, 'sentido': 'receita'},
                          {'nome': 'insumo', 'base': 100.0, 'spot': 140.0, 'elast': None,
                           'receita_driver': 250.0, 'metrica_base': 250.0, 'sentido': 'custo'}])
    liq = r['compensacao']['efeito_liquido_total_%']; bru = r['compensacao']['soma_dos_brutos_%']
    check('líquido = soma com sinal', abs(liq - (2.0 * 20 - 1.0 * 40)) < 1e-6, f'({liq})')
    check('brutos = soma dos módulos', abs(bru - (40 + 40)) < 1e-6, f'({bru})')
    check('compensação detectada', 'nota_compensacao' in r['compensacao'])
    check('driver de custo entra no gate', r['GATE'] is True)
    # elasticidade declarada negativa é classificada como custo
    r2 = registro_drivers([{'nome': 'frete', 'base': 10.0, 'spot': 13.0, 'elast': -0.5,
                            'sentido': 'custo'}])
    check('declarada negativa', r2['drivers'][0]['efeito_liquido_%'] < 0)
    print('  D4 elasticidade com sinal: custo negativo, compensação líquida vs brutos, compat v7')

# ---------- 3. BOUNDARY TESTS ----------
def bnd_limites():
    """[limites] g→ROIC (RiR→100%), gp→W, ROIC→0, n grande, spread negativo, caixa extremo."""
    # g → ROIC: contínuo, finito (o 'teto' da book é supremum na borda, não singularidade)
    m = ev_nopat(0.0849999, 0.085, 0.07, 10, tv='book')
    check('g→ROIC finito', m == m and abs(m) < 1e3, f'({m})')
    # gp → W: gordon deve devolver nan (não explosão silenciosa)
    check('gp≥W ⟹ nan', ev_nopat(0.03, 0.10, 0.07, 10, tv='gordon', roic_tv=0.2, gp=0.07) != \
                        ev_nopat(0.03, 0.10, 0.07, 10, tv='gordon', roic_tv=0.2, gp=0.07))
    # ROIC → 0+: book explode (patologia do caso CONFLACIONADO — sem roic_book o TV segue o
    # marginal; com book informado o TV fica preso e não explode, ver rec_b01), convergencia não
    mb = ev_nopat(0.0, 0.001, 0.07, 10, tv='book')
    mc = ev_nopat(0.0, 0.001, 0.07, 10, tv='convergencia')
    check('book explode com ROIC→0 (patologia da conflação)', mb > 100)
    check('convergencia estável com ROIC→0', abs(mc - 1 / 0.07) < 1e-6, f'({mc})')
    # n → ∞: book converge à value driver perpétua (§6.5 do paper)
    g, roic, W = 0.05, 0.085, 0.07
    perp = (1 - g / roic) / (W - g)
    m800 = ev_nopat(g, roic, W, 800, tv='book') / (1 + g)
    check('book n→∞ → value driver perpétua', abs(m800 - perp) < 1e-3, f'({m800} vs {perp})')
    # spread negativo persistente via gordon com roic_tv < W: definido e menor que 1/W
    mneg = ev_nopat(0.0, 0.05, 0.07, 10, tv='gordon', roic_tv=0.05, gp=0.01) 
    check('gordon roic_tv<W definido', mneg == mneg and mneg < 1 / 0.07)
    # caixa extremo no equity
    mx = pe(0.06, 0.12, 0.12, 10, 1.0, 0.0, tv='book')
    check('caixa/E=100% definido', mx == mx and mx > 0)
    print('  boundaries: g→ROIC, gp→W, ROIC→0, n→∞, spread negativo, caixa extremo')

def bnd_solver():
    """[solver] múltiplas raízes reportadas; tangência capturada; identificação coerente."""
    # tangência sintética: f(x) = (x-0.1)^2 - 0  → toque em 0.1 sem cruzamento
    roots, tang = solve_full(lambda x: (x - 0.10) ** 2, 0.0, 0.30, ref=1.0)
    check('tangência capturada', len(tang) == 1 and abs(tang[0]['x'] - 0.10) < 1e-4,
          f'(roots={roots}, tang={tang})')
    # múltiplas raízes: parábola deslocada
    roots2, _ = solve_full(lambda x: (x - 0.05) * (x - 0.20), 0.0, 0.30, ref=1.0)
    check('múltiplas raízes', len(roots2) == 2)
    # identificação: função plana ⟹ fraca; função íngreme ⟹ forte
    idw = identificacao(lambda x: 10.0 + 0.01 * x, 0.10, 10.0)
    ids = identificacao(lambda x: 10.0 + 500.0 * x, 0.10, 10.0)
    check('plana ⟹ fraca', idw['identificacao'] == 'fraca')
    check('íngreme ⟹ forte', ids['identificacao'] == 'forte')
    print('  solver: tangências, múltiplas raízes, classificação de identificação')

def bnd_aliases():
    """[compat] aliases legados produzem exatamente os mesmos números."""
    check('ic≡book', ev_nopat(0.05, 0.10, 0.07, 10, tv='ic') == ev_nopat(0.05, 0.10, 0.07, 10, tv='book'))
    check('spread≡gordon', ev_nopat(0.05, 0.10, 0.07, 10, tv='spread', roic_tv=0.2, gp=0.03) ==
                           ev_nopat(0.05, 0.10, 0.07, 10, tv='gordon', roic_tv=0.2, gp=0.03))
    check('canon', tv_canon('ic') == 'book' and tv_canon('spread') == 'gordon')
    print('  aliases legados: ic≡book, spread≡gordon, número a número')

def bnd_conflacao():
    """[v8, atualizado v9.26] --roic-book altera SÓ o terminal; sem ele, book == legado.
    Sob o IC acumulado (v9.26) o médio só entra pela âncora inicial: a diferença de TV entre
    com_book e legado é exatamente (1+g)·(1/rb − 1/roic)/(1+w)^n."""
    legado = ev_nopat(0.05, 0.25, 0.07, 10, tv='book')
    com_book = ev_nopat(0.05, 0.25, 0.07, 10, tv='book', roic_book=0.10)
    dif_tv = 1.05 * (1 / 0.10 - 1 / 0.25) / 1.07 ** 10
    check('roic_book move só o TV', abs((com_book - legado) - dif_tv) < 1e-12)
    check('sem roic_book = legado', ev_nopat(0.05, 0.25, 0.07, 10, tv='book', roic_book=None) == legado)
    print('  conflação marginal×médio: --roic-book move exatamente o TV, nada mais')

def rec_v926_book_acumulado():
    """[v9.26] Caso da auditoria ago/26: g 5%, marginal 20%, médio inicial 10%, W 8%, n 10.
    O TV congelado dava EV/NOPAT_1 = 13,68 (+11,9%); o IC acumulado dá 12,2261. Contraprova
    por acumulação explícita ano a ano + os três colapsos (médio=marginal; g=0; sem roic_book)."""
    g, r, rb, w, n = 0.05, 0.20, 0.10, 0.08, 10
    m = ev_nopat(g, r, w, n, tv='book', roic_book=rb)
    check('v9.26: caso da auditoria — EV/NOPAT_0 = 12,8374', abs(m - 12.8374) < 5e-4, f'({m})')
    check('v9.26: caso da auditoria — EV/NOPAT_1 = 12,2261', abs(m / (1 + g) - 12.2261) < 5e-4)
    # contraprova: fluxos + IC acumulado, sem a forma fechada
    nop = [(1 + g) ** t for t in range(0, n + 2)]
    ic = nop[1] / rb
    for t in range(1, n + 1):
        ic += (g / r) * nop[t]
    m_exp = sum(nop[t] * (1 - g / r) / (1 + w) ** t for t in range(1, n + 1)) + ic / (1 + w) ** n
    check('v9.26: forma fechada = acumulação explícita (1e-12)', abs(m - m_exp) < 1e-12)
    check('v9.26: ROIC médio deriva 10% → 12,39% no ano n', abs(nop[n + 1] / ic - 0.1239) < 5e-4)
    # colapsos
    check('v9.26: colapso médio=marginal (fórmula antiga exata)',
          abs(ev_nopat(g, r, w, n, tv='book', roic_book=r)
              - (sum(nop[t] * (1 - g / r) / (1 + w) ** t for t in range(1, n + 1))
                 + nop[n + 1] / (r * (1 + w) ** n))) < 1e-12)
    check('v9.26: colapso g=0 (IC_n = 1/book — média não deriva sem capital novo)',
          abs(ev_nopat(0.0, r, w, n, tv='book', roic_book=rb)
              - (sum(1 / (1 + w) ** t for t in range(1, n + 1)) + 1 / (rb * (1 + w) ** n))) < 1e-12)
    check('v9.26: ev_ebitda propaga a correção',
          abs(ev_ebitda(g, r, w, n, 0.15, 0.15, tv='book', roic_book=rb) - m * 0.85 * 0.85) < 1e-12)
    print('  v9.26: TV da book por IC acumulado — caso da auditoria, contraprova e colapsos')


# ---------- 5. CLI INTEGRATION (v8.4) ----------
# A matemática validada acima não garante o PIPELINE: o bug da v8.3 (NameError em diag_eq no
# caminho gordon+caixa≠0+roe_tv — exatamente o caso-vitrine da correção C1) passou por toda a
# suíte porque ela importa as funções e nunca executa a CLI. Esta bateria roda cada subcomando
# via subprocess, exige returncode 0, JSON parseável (NaN/Inf viram null — jprint) e a presença
# dos diagnósticos esperados no output.
def rec_v98():
    """[v9.28] Mantém os checks de condicionamento da reversa e trava o APV canônico.
    Desde v9.28 hp/me NÃO são aliases: pedir uma convenção não implementada deve falhar
    explicitamente em vez de devolver silenciosamente o regime ku."""
    import subprocess, json, os
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'justos.py')
    def run_json(args):
        r = subprocess.run([sys.executable, script] + args, capture_output=True, text=True,
                           encoding='utf-8')
        check('v9.28 CLI rc=0', r.returncode == 0, f'({args[0]}: {r.stderr[-160:]})')
        return json.loads(r.stdout)
    def run_fail(args):
        return subprocess.run([sys.executable, script] + args, capture_output=True, text=True,
                              encoding='utf-8')
    cab = ('premissa_regime', 'premissas_fixadas', 'faixa_de_busca')
    d1 = run_json(['rev', '--alvo', '10', '--resolver', 'cap', '--base', 'nopat',
                   '--g', '5', '--roic', '15', '--wacc', '7', '--tv', 'convergencia',
                   '--moeda', 'brl-nominal'])
    check('cap crescente: cabeçalho completo', all(k in d1 for k in cab),
          f'(faltam: {[k for k in cab if k not in d1]})')
    check('cap crescente: moeda ecoada', d1.get('convencao_moeda') == 'brl-nominal')
    check('cap crescente: variável cap não ecoada como fixada',
          'CAP_n_anos' not in d1.get('premissas_fixadas', {}).get('informadas', {}))
    d2 = run_json(['rev', '--alvo', '10', '--resolver', 'cap', '--base', 'nopat',
                   '--g', '3', '--roic', '4', '--wacc', '7', '--tv', 'gordon',
                   '--roic-tv', '4', '--gp', '2'])
    check('cap decrescente: cabeçalho completo', all(k in d2 for k in cab))
    base = ['apv', '--fcff1', '10', '--g', '3', '--n', '5', '--ku', '12', '--kd', '8',
            '--tax', '30', '--d0', '40']
    dku = run_json(base + ['--conv', 'ku'])
    dmm = run_json(base + ['--conv', 'mm'])
    check('APV: ku nomeia mecanismo sem alegar HP completo',
          'Ku' in dku.get('convencao', '') and 'EXÓGENA' in dku.get('convencao', '')
          and 'não é mantido constante' in dku.get('convencao', '').lower())
    check('APV: mm intacto', 'MM' in dmm.get('convencao', ''))
    for al in ('hp', 'me'):
        rr = run_fail(base + ['--conv', al])
        check(f'APV: {al} rejeitado pelo parser', rr.returncode != 0 and 'invalid choice' in rr.stderr)
    print('  v9.28: reversa condicionada + APV mm/ku canônicos; hp/me rejeitados')


def rec_lint_portabilidade(alvo=None):
    """[v9.9] Regressão de PORTABILIDADE do ritual de validação. Os property tests não pegam
    isto: a suíte exercita o motor por subprocess, e duas escolhas silenciosas quebram a
    validação em máquina de locale/instalação diferentes — sem produzir um único FALHOU, o que
    é pior que falhar (parece defeito de cálculo). (1) invocar o motor por NOME de interpretador
    ('python3') em vez do interpretador que roda a suíte: onde o nome não existe, stdout volta
    vazio; (2) abrir pipe de texto sem fixar encoding: o parent decodifica com o locale (cp1252
    em Windows PT-BR) e estoura no primeiro acento. O lint lê a própria suíte por AST — regra
    estrutural, não textual, então reformatar a chamada não a burla."""
    import ast, os
    alvo = alvo or os.path.abspath(__file__)
    tree = ast.parse(open(alvo, encoding='utf-8').read())
    _fonte = getattr(ast, 'unparse', lambda n: '?')
    total = 0
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == 'run' and isinstance(node.func.value, ast.Name)
                and node.func.value.id == 'subprocess'):
            continue
        total += 1
        argv = node.args[0] if node.args else None
        if isinstance(argv, ast.BinOp):        # forma [interp, script] + args
            argv = argv.left
        prim = argv.elts[0] if isinstance(argv, ast.List) and argv.elts else None
        check(f'portabilidade: subprocess.run (linha {node.lineno}) usa sys.executable',
              (isinstance(prim, ast.Attribute) and prim.attr == 'executable'
               and isinstance(prim.value, ast.Name) and prim.value.id == 'sys'),
              f'(invoca {_fonte(prim) if prim is not None else "argv não literal"})')
        enc = {k.arg: k.value for k in node.keywords}.get('encoding')
        check(f'portabilidade: subprocess.run (linha {node.lineno}) fixa encoding utf-8',
              isinstance(enc, ast.Constant)
              and str(enc.value).lower().replace('-', '') == 'utf8',
              '(pipe decodificado pelo locale)')
    check('portabilidade: a suíte de fato exercita o motor por subprocess', total >= 10,
          f'({total} chamadas encontradas)')
    print(f'  v9.9: lint de portabilidade — {total} chamadas de subprocess verificadas '
          f'(interpretador corrente + encoding fixado)')


def rec_lint_semantico():
    """[v9.8/C-01, P0.4] Regressão SEMÂNTICA/documental: os property tests numéricos não pegam
    rótulo econômico errado (o motor aceita qualquer número válido). Este lint varre docs e
    strings do motor contra expressões proscritas pelas auditorias — reintroduzi-las quebra a
    suíte. Escopo desenhado para preservar os usos LEGÍTIMOS de 'blended' (o médio da book via
    --roic-book/--roe-book; o alerta multi-segmento)."""
    import os, re
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    arquivos = ['SKILL.md', 'references/aplicacao.md', 'references/derivacao.md',
                'references/paper-multiplos-justos-v3.md', 'scripts/justos.py']
    proscritos = [
        # C-01: blended como DEFINIÇÃO da rentabilidade terminal do gordon
        (r'blended\s+do\s+portf[óo]lio\s*\n?\s*existente[^.]{0,120}?(nunca|n[ãa]o)\s+a\s+\**marginal',
         'C-01: gordon com rentabilidade terminal definida como blended ("nunca/não a marginal")'),
        # D-01: rótulos econômicos mais fortes que a mecânica
        (r'morre\s+por\s+completo',
         'D-01: "vantagem morre por completo" (leia: ancoragem no IC mensurado, condicionada)'),
        (r'significado\s+padr[ãa]o\s+de\s+["\'“]a\s+vantagem',
         'D-01: convergencia como "significado padrão" da exaustão total'),
        # B-01 (rodada 5, atualizado v9.26): a trava da 'book' é do caso CONFLACIONADO. Com o
        # book informado separadamente a perversidade não existe (o TV acompanha o marginal pelo
        # IC acumulado — v9.26) e a raiz é CONDICIONADA (tese de saída pelo capital investido),
        # nunca proibida ou vazia.
        (r'book[^.\n]{0,60}?\b(proibida|descartada)\b',
         'B-01: trava da book declarada sem condicionar ao caso conflacionado'),
        (r'regi[ãa]o\s+proibida',
         'B-01: "região proibida" — a região é condicionada a tese declarada, não proibida'),
        (r'ra[íi]z(es)?\s+economicamente\s+vazias?',
         'B-01: raiz classificada como economicamente vazia (é condicionada, não vazia)'),
        (r'economicamente\s+vazia\s+como\s+leitura',
         'B-01: reversa classificando raiz sub-custo como economicamente vazia'),
        # P-02 (rodada 5): a Hessiana de M(g, rent) é INDEFINIDA (autovalores −398,55 e +733,40
        # em g=4%/ROIC=15%/W=8%/CAP=10). Não há convexidade conjunta — logo não há Jensen, e o
        # viés do blended não tem sinal universal.
        (r'agrega[çc][ãa]o\s+de\s+segmentos\s+é\s+convexa',
         'P-02: agregação de segmentos declarada convexa (Hessiana é indefinida)'),
        (r'valor\s+é\s+convexo\s+nos\s+inputs',
         'P-02: "o valor é convexo nos inputs — Jensen" (não há convexidade conjunta)'),
    ]
    ocorrencias = []
    for arq in arquivos:
        txt = open(os.path.join(base, arq), encoding='utf-8').read()
        for pat, desc in proscritos:
            for m in re.finditer(pat, txt, re.IGNORECASE):
                linha = txt[:m.start()].count('\n') + 1
                ocorrencias.append(f'{arq}:{linha} — {desc}')
    for o in ocorrencias:
        check('lint semântico', False, f'({o})')
    if not ocorrencias:
        check('lint semântico: nenhuma expressão proscrita', True)
    print(f'  lint semântico: {len(arquivos)} arquivos varridos, '
          f'{len(ocorrencias)} ocorrência(s) proscrita(s)')


def rec_v97():
    """[v9.7] Auditoria Fase 2: (1) rev ecoa premissas_fixadas com a distinção tripla
    informadas/defaults/não-aplicáveis, condicionamento completo declarado; (2) apv ecoa
    SEMPRE o regime de dívida, com aviso quando entrou por default (padrão retrofit v9.4)."""
    import subprocess, json, os
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'justos.py')
    def run_json(args):
        r = subprocess.run([sys.executable, script] + args, capture_output=True, text=True,
                           encoding='utf-8')
        check('v9.7 CLI rc=0', r.returncode == 0, f'({args[0]}: {r.stderr[-160:]})')
        return json.loads(r.stdout)
    # (1) rev firm, gordon sem --gp: gp e alvo-base devem cair em defaults; g/wacc informados
    d = run_json(['rev', '--alvo', '12', '--resolver', 'roic', '--base', 'nopat',
                  '--g', '4', '--wacc', '9', '--n', '10', '--tv', 'gordon', '--roic-tv', '15'])
    pf = d.get('premissas_fixadas', {})
    check('rev: premissas_fixadas presente', bool(pf))
    check('rev: três chaves da distinção', all(k in pf for k in
          ('informadas', 'assumidas_por_default', 'nao_aplicaveis')))
    check('rev: g informado ecoado', pf.get('informadas', {}).get('g_%') == 4.0)
    check('rev: gp em default declarado', 'gp_%' in pf.get('assumidas_por_default', {}))
    check('rev: alvo-base em default', 'base_do_alvo' in pf.get('assumidas_por_default', {}))
    # (1b) equity book sem --roe-book: conflação declarada nos defaults; resolvido não ecoa
    d2 = run_json(['rev', '--alvo', '8', '--resolver', 'roe', '--base', 'pl',
                   '--g', '3', '--ke', '12', '--n', '10', '--tv', 'book'])
    pf2 = d2.get('premissas_fixadas', {})
    check('rev book: conflação nos defaults', 'roe_book_%' in pf2.get('assumidas_por_default', {}))
    check('rev: variável resolvida NÃO ecoada como fixada',
          'roe_marginal_%' not in pf2.get('informadas', {}))
    # (2) apv sem --conv: regime ecoado + aviso; com --conv me: regime me, sem aviso
    base = ['apv', '--fcff1', '10', '--g', '3', '--n', '5', '--ku', '12', '--kd', '8',
            '--tax', '30', '--d0', '40']
    d3 = run_json(base)
    check('apv: regime_divida sempre ecoado', 'mm' in d3.get('regime_divida', ''))
    check('apv: aviso quando default', 'aviso_regime_divida' in d3)
    d4 = run_json(base + ['--conv', 'ku'])
    check('apv: regime ku declarado ecoado', 'ku' in d4.get('regime_divida', ''))
    check('apv: sem aviso quando declarado', 'aviso_regime_divida' not in d4)
    print('  v9.7: premissas_fixadas no rev (tripla distinção) + regime de dívida no apv')


def rec_coerencia():
    """[v9.11] Ancoragem ESTRUTURAL do vetor. Até aqui o anchor dizia "este ponto reproduz este
    número"; passa a dizer "este ponto reproduz este número E respeita as identidades que o
    geraram". O vetor da âncora é o vetor de OUTPUTS da planilha vF8 — ele satisfaz as quatro
    identidades simultaneamente, e é isso que se trava.

    O complemento é o que importa na prática: perturbar UM driver que era output — o uso normal
    da skill ao montar cenários a partir da reversa — tem de ser SINALIZADO. Sem isso, o motor
    aceita em silêncio um vetor que nenhuma DRE/BP gera."""
    from justos import coerencia_vetor
    # vetor da planilha vF8 — proveniência célula a célula:
    #   g   D3    (input)      roic E105 (fórmula)   w    C164 (fórmula)   roe E117 (fórmula)
    #   ke  C162  (input)      gde  E70  (fórmula)   nde  E71  (fórmula)   d   E100 (fórmula)
    #   tax D38   (input)      kd   = juros/dívida bruta   rir_obs E96 (fórmula)
    V = dict(g=0.11, roic=0.3435157894736844, w=0.18733157894736852,
             roe=0.4482692307692308, ke=0.22, kd=0.142714285714286, tax=0.30,
             d=0.0666666666666665, gde=0.5384615384615384, nde=0.4615384615384615)
    dg, res = coerencia_vetor(**V, rir_observado=0.422258993687565)
    inc = [x for x in dg if 'INCOERÊNCIA' in x]
    check('coerência: as 4 identidades foram checadas no vetor da âncora',
          len(res['identidades_checadas']) >= 4, f"({res['identidades_checadas']})")
    check('coerência: nada ficou por falta de input no vetor completo',
          res['nao_checadas_por_falta_de_input'] == ['nenhuma'],
          f"({res['nao_checadas_por_falta_de_input']})")
    check('coerência: o vetor da planilha NÃO tem incoerência', not inc, f'({inc[:1]})')
    # a divergência de RiR da planilha é DECLARADA, não incoerência (nota Q157 do autor)
    check('coerência: RiR 42,2% vs 32,0% sai como divergência declarada, não erro',
          any('DIVERGÊNCIA DECLARADA' in x for x in dg))
    # eco da intensidade de capital reproduz o balanço: EBITDA 49,95 / capital investido 95
    eb_ic = V['roic'] / ((1 - V['d']) * (1 - V['tax']))
    check('coerência: EBITDA/capital investido implicado = 49,95/95 da planilha',
          abs(eb_ic - 49.95 / 95) < 1e-9, f'({eb_ic} vs {49.95/95})')
    # simetria estrutural: a transformação Ke→WACC é a MESMA que leva ROE→ROIC
    w_id = (V['ke'] + V['kd'] * (1 - V['tax']) * V['gde']) / (1 + V['nde'])
    roic_id = (V['roe'] + V['kd'] * (1 - V['tax']) * V['gde']) / (1 + V['nde'])
    check('coerência: identidade C164 reproduz o WACC da âncora', abs(w_id - V['w']) < 1e-12,
          f'({w_id})')
    check('coerência: a mesma transformação reproduz o ROIC da âncora',
          abs(roic_id - V['roic']) < 1e-12, f'({roic_id})')
    # PERTURBAÇÕES: mexer num driver que era output tem de ser sinalizado
    for nome, mut in (('roic 34,35%→45%', dict(roic=0.45)),
                      ('roe 44,83%→52%', dict(roe=0.52)),
                      ('wacc 18,73%→15%', dict(w=0.15)),
                      ('nde 0,462→0,20 (mudou a estrutura sem mudar o resto)', dict(nde=0.20))):
        vd = dict(V); vd.update(mut)
        dgp, _ = coerencia_vetor(**vd)
        check(f'coerência: perturbação [{nome}] é SINALIZADA',
              any('INCOERÊNCIA' in x for x in dgp), '(passou em silêncio)')
    # o gate é DECLARATÓRIO: nunca levanta, nunca bloqueia, mesmo com vetor absurdo
    for absurdo in (dict(roic=-0.5), dict(d=1.0), dict(nde=0.0, gde=0.0), dict(tax=1.0)):
        vd = dict(V); vd.update(absurdo)
        try:
            coerencia_vetor(**vd)
            ok = True
        except Exception:                                          # noqa: BLE001
            ok = False
        check(f'coerência: gate não levanta com vetor absurdo {list(absurdo)}', ok)
    # padrão retrofit: sem os opcionais, roda e DECLARA o que não pôde checar
    dg0, res0 = coerencia_vetor(g=0.11, roic=0.3435157894736844, w=0.187331578947, tax=0.30,
                                d=0.0666666666666665)
    check('coerência/retrofit: roda sem os flags novos', isinstance(dg0, list))
    check('coerência/retrofit: declara o que NÃO pôde checar',
          len(res0['nao_checadas_por_falta_de_input']) >= 2 and
          res0['nao_checadas_por_falta_de_input'] != ['nenhuma'],
          f"({res0['nao_checadas_por_falta_de_input']})")
    check('coerência/retrofit: sem os opcionais não inventa incoerência',
          not [x for x in dg0 if 'INCOERÊNCIA' in x])
    print('  v9.11: coerência do vetor — 4 identidades da planilha travadas na âncora, '
          '4 perturbações sinalizadas, gate declaratório e retrofit verificados')


def rec_roundtrip():
    """[v9.11] Realimentar como INPUT um driver que saiu como OUTPUT é o uso NORMAL da skill:
    a reversa devolve o ROIC implícito e o analista roda cenários a partir dele. A pergunta que
    isto responde é se essa realimentação é segura — se resolver a variável X para um alvo M e
    reinjetar a raiz devolve M.

    Duas exigências, não uma: (i) toda raiz devolvida reconcilia o alvo; (ii) a raiz VERDADEIRA
    está no conjunto — um solver que devolvesse só uma das raízes de um caso bi-radicular passaria
    em (i) e falharia o problema de identificação do §6.7. Cobre as duas bases (corrente e
    forward), que é onde o deslocamento (1+g) do achado D2 se esconde."""
    import random
    from justos import iso_curva
    rnd = random.Random(9110)
    TOL = 1e-6
    casos = raizes_multiplas = 0
    for _ in range(14):
        g = round(rnd.uniform(0.0, 0.05), 4)
        roic = round(rnd.uniform(0.10, 0.45), 4)
        w = round(rnd.uniform(max(g + 0.02, 0.07), 0.15), 4)
        n = rnd.choice([5, 10, 15])
        gp = round(rnd.uniform(0.0, w - 0.02), 4)
        for tv, kw in (('book', {}), ('convergencia', {}),
                       ('gordon', dict(roic_tv=round(rnd.uniform(0.08, 0.30), 4), gp=gp))):
            M = lambda gg, rr, ww, nn: ev_nopat(gg, rr, ww, nn, tv=tv, **kw)
            alvo = M(g, roic, w, n)
            if alvo != alvo or alvo <= 0:
                continue
            for var, verdadeiro, faixa, subst in (
                    ('roic', roic, (max(g + 1e-4, 0.005), 1.50),
                     lambda x: M(g, x, w, n)),
                    ('g', g, (-0.30, min(0.60, roic * 0.999)),
                     lambda x: M(x, roic, w, n)),
                    ('wacc', w, (max(kw.get('gp', 0.0) + 1e-3, 0.005), 0.40),
                     lambda x: M(g, roic, x, n))):
                raizes = solve(lambda x: subst(x) - alvo, faixa[0], faixa[1])
                casos += 1
                if len(raizes) > 1:
                    raizes_multiplas += 1
                # (i) toda raiz devolvida reconcilia o alvo
                for r in raizes:
                    check(f'roundtrip {tv}/{var}: raiz reinjetada reconcilia o alvo',
                          abs(subst(r) - alvo) < max(TOL, abs(alvo) * 1e-9),
                          f'(alvo={alvo:.9f} raiz={r:.9f} M={subst(r):.9f})')
                # (ii) a raiz VERDADEIRA está no conjunto
                check(f'roundtrip {tv}/{var}: valor verdadeiro recuperado',
                      any(abs(r - verdadeiro) < 1e-5 for r in raizes),
                      f'(verdadeiro={verdadeiro} raizes={[round(r, 6) for r in raizes]})')
            # base FORWARD: o alvo deslocado por (1+g) tem de devolver o MESMO roic (achado D2)
            alvo_fwd = alvo / (1 + g)
            rf = solve(lambda x: M(g, x, w, n) / (1 + g) - alvo_fwd, max(g + 1e-4, 0.005), 1.50)
            check(f'roundtrip {tv}/roic: base forward recupera o mesmo roic',
                  any(abs(r - roic) < 1e-5 for r in rf),
                  f'(verdadeiro={roic} raizes={[round(r, 6) for r in rf]})')
    # lado EQUITY: mesma propriedade com caixa/equity não nulo
    for _ in range(6):
        g = round(rnd.uniform(0.0, 0.05), 4)
        roe = round(rnd.uniform(0.12, 0.40), 4)
        ke = round(rnd.uniform(max(g + 0.02, 0.08), 0.20), 4)
        gde, nde = 0.40, 0.25
        alvo = pe(g, roe, ke, 10, gde, nde, tv='book')
        raizes = solve(lambda x: pe(g, x, ke, 10, gde, nde, tv='book') - alvo,
                       max(g + 1e-4, 0.005), 1.50)
        casos += 1
        check('roundtrip equity/roe: valor verdadeiro recuperado',
              any(abs(r - roe) < 1e-5 for r in raizes),
              f'(verdadeiro={roe} raizes={[round(r, 6) for r in raizes]})')
    # iso: cada rent* da grade, realimentada, reconcilia o alvo (o motor já verifica ponto a
    # ponto; aqui a propriedade é afirmada sobre a grade inteira, em três convenções)
    for tv, kw in (('book', {}), ('convergencia', {}), ('gordon', dict(rent_tv=0.18, gp=0.02))):
        alvo = ev_nopat(0.03, 0.20, 0.09, 10, tv=tv,
                        **({'roic_tv': 0.18, 'gp': 0.02} if tv == 'gordon' else {}))
        cur = iso_curva('ev', alvo, 0.09, 10, [0.01, 0.02, 0.03, 0.04], tv=tv, **kw)['curva']
        # pontos sem raiz (não identificáveis, ou alvo fora do supremo) não trazem a chave —
        # o que se exige é que TODA raiz devolvida reconcilie, não que toda grade tenha raiz
        com_raiz = [p for p in cur if p.get('check_multiplo') is not None]
        ok = [p for p in com_raiz if p['check_multiplo'] == 0.0]
        check(f'roundtrip iso/{tv}: a grade produziu raízes', len(com_raiz) > 0,
              f'({len(com_raiz)}/{len(cur)} pontos identificáveis)')
        check(f'roundtrip iso/{tv}: toda raiz da grade reconcilia o alvo',
              len(ok) == len(com_raiz), f'({len(ok)}/{len(com_raiz)} com check zero)')
        casos += len(com_raiz)
    # [v9.27] Topologia em g sob 'book' separado: o gradiente do múltiplo FORWARD segue o
    # spread marginal − W; isso NÃO implica monotonicidade da base CORRENTE, pois M0=(1+g)·M1.
    # Portanto a reversa em g pode continuar bi-radicular na base corrente mesmo com IC acumulado.
    w_b, n_b, rb_b = 0.07, 15, 0.10
    for roic_b, sobe in ((0.08, True), (0.05, False)):
        ff = lambda gg: ev_nopat(gg, roic_b, w_b, n_b, tv='book', roic_book=rb_b) / (1 + gg)
        grade = [i / 2000 for i in range(0, int(roic_b * 0.999 * 2000))]
        vals = [ff(g) for g in grade]
        mono = all((b > a) == sobe for a, b in zip(vals, vals[1:]))
        check(f'roundtrip §6.7/v9.27: book separado FORWARD, dM/dg segue o spread '
              f'(marginal {roic_b:.0%} {">" if sobe else "<"} W)', mono)

    # Contraprova corrente: marginal 10% < W 12%, book inicial 10%, n=15, alvo 8,65x.
    # A curva corrente tem máximo interior e DUAS raízes — a patologia não desaparece com IC acumulado.
    r_b, w_c, rb_c, n_c, alvo_c = 0.10, 0.12, 0.10, 15, 8.65
    fc = lambda gg: ev_nopat(gg, r_b, w_c, n_c, tv='book', roic_book=rb_c)
    roots_c = solve(lambda gg: fc(gg) - alvo_c, -0.30, r_b * 0.999)
    check('roundtrip §6.7/v9.27: base corrente preserva caso bi-radicular',
          len(roots_c) == 2, f'({[round(x, 9) for x in roots_c]})')
    anchors = (0.007552381209283143, 0.04410925822752708)
    check('roundtrip §6.7/v9.27: duas raízes corrente nos anchors',
          len(roots_c) == 2 and all(abs(a-b) < 2e-8 for a,b in zip(roots_c, anchors)),
          f'({roots_c})')
    for rr in roots_c:
        check('roundtrip §6.7/v9.27: cada raiz corrente reconcilia 8,65x',
              abs(fc(rr) - alvo_c) < 1e-9, f'(g={rr:.9f}, M={fc(rr):.9f})')
    casos += len(roots_c); raizes_multiplas += 1
    print(f'  v9.27: ida-e-volta output→input — {casos} reversões reinjetadas; gradiente forward '
          f'preservado e contraprova bi-radicular corrente com duas raízes verificada')



def rec_rev_sugestao():
    """[v9.13 / rodada 2 FNV] Quando a reversa não acha raiz no eixo primário (roic/roe/g), os dois
    passos que fecham (ou refutam) a conta — teto do crescimento gratuito RiR→0 e curva iso-valor —
    dependiam de o analista lembrar. Na rodada 2, o teto foi a única hipótese que reconciliou o
    preço da FNV, e o iso ficou na gaveta até a auditoria. O rev passa a sugerir os dois no output
    (regra 10: nada depende de o analista lembrar). Caso de reprodução: o alvo 31,944x EV/NOPAT da
    rodada 2, sem solução em roic."""
    import subprocess, json, os
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'justos.py')
    def run_json(args):
        r = subprocess.run([sys.executable, script] + args, capture_output=True, text=True,
                           encoding='utf-8')
        check('v9.13 rev CLI rc=0', r.returncode == 0, f'({r.stderr[-120:]})')
        return json.loads(r.stdout)
    base = ['rev', '--alvo', '31.944', '--base', 'nopat', '--resolver', 'roic',
            '--g', '4', '--roic', '23', '--wacc', '8.59', '--n', '10',
            '--tv', 'convergencia', '--rf', '4.74', '--moeda', 'USD-nominal']
    d = run_json(base)
    check('rev sem raiz: sem_solucao presente (premissa do caso)', 'sem_solucao' in d,
          f"(raizes={d.get('raizes_roic_%')})")
    check('rev sem raiz: sugestao aponta o teto RiR→0', 'GRATUITO' in d.get('sugestao', ''))
    check('rev sem raiz: sugestao aponta o iso', 'ISO' in d.get('sugestao', '').upper())
    # com raiz, a sugestão NÃO aparece
    ok = run_json(['rev', '--alvo', '12', '--base', 'nopat', '--resolver', 'roic',
                   '--g', '4', '--roic', '23', '--wacc', '8.59', '--n', '10',
                   '--tv', 'convergencia', '--rf', '4.74', '--moeda', 'USD-nominal'])
    check('rev com raiz: sem sugestao', 'sugestao' not in ok,
          f"(raizes={ok.get('raizes_roic_%')})")
    print('  v9.13: rev sem raiz no eixo primário sugere teto RiR→0 + iso no próprio output')


def rec_regime_driver():
    """[v9.14 / rodada 3, §13.2 + hipótese do usuário validada] O g da fórmula é crescimento de
    VOLUME (a regra 'nível não é taxa' expulsa o preço do g); com a métrica normalizada ao spot
    NOMINAL e convenção terminal sem crescimento de preço (`convergencia`, ou `gordon` com gp≈0),
    o modelo assume o driver CONGELADO em termos nominais = caindo ~inflação a.a. em termos reais,
    para sempre — descontado a Ke NOMINAL. É o erro de Modigliani-Cohn (fluxo real a taxa nominal);
    valeu ~28% do valor na FNV e não produzia sintoma. O normaliza passa a avisar quando a
    convenção declarada congela o preço do driver."""
    import subprocess, json, os
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'justos.py')
    def run_json(args):
        r = subprocess.run([sys.executable, script] + args, capture_output=True, text=True,
                           encoding='utf-8')
        check('v9.14 normaliza CLI rc=0', r.returncode == 0, f'({r.stderr[-120:]})')
        return json.loads(r.stdout)
    base = ['normaliza', '--ebitda-base', '1656.1', '--da', '310', '--preco-base', '3511',
            '--preco-novo', '4200', '--rev-driver', '1562.9', '--tax', '22.5',
            '--g', '3.0', '--roic', '4.1', '--wacc', '8.43', '--n', '10']
    conv = run_json(base + ['--tv', 'convergencia'])
    check('regime driver: convergencia sobre base normalizada AVISA o congelamento nominal',
          'aviso_regime_driver' in conv, f'(chaves: {sorted(conv)[:9]})')
    check('regime driver: aviso distingue rota real exata de terminal-only aproximada',
          'real' in conv.get('aviso_regime_driver', '').lower()
          and 'gordon' in conv.get('aviso_regime_driver', '').lower()
          and 'aproxima' in conv.get('aviso_regime_driver', '').lower())
    gz = run_json(base + ['--tv', 'gordon', '--roic-tv', '20', '--gp', '0'])
    check('regime driver: gordon com gp=0 também congela — avisa',
          'aviso_regime_driver' in gz)
    gpos = run_json(base + ['--tv', 'gordon', '--roic-tv', '20', '--gp', '2.3'])
    check('regime driver: gordon com gp>0 NÃO avisa (o terminal cresce)',
          'aviso_regime_driver' not in gpos)
    print('  v9.14: normaliza avisa quando a convenção congela o preço do driver (Fisher)')


def rec_iso_sugestao():
    """[v9.14 / rodada 3 FNV] O executor varreu `iso` em g 0–7%, recebeu null em TODOS os pontos e
    entregou ao usuário "não existe combinação que reconcilie o preço" — FALSO: a fronteira existe
    a partir de g≈8% (ele se corrigiu na rodada seguinte). O motor foi literalmente correto e
    materialmente enganoso: 'sem raiz NESTE intervalo' não é 'sem raiz'. O `rev` já tem o antídoto
    (campo sugestao, v9.13); o `iso` ganha o equivalente, com varredura grosseira reportando onde a
    fronteira começa. Caso de reprodução: os números exatos da rodada 3."""
    from justos import iso_curva
    # caso da rodada 3, número a número: alvo 21,385 (o relatório o passou DIRETO ao iso, como
    # EV/NOPAT — a fronteira dele reconcilia exatamente assim: g=8% ⟹ rent 109,97%; g=10% ⟹ 24,00%)
    ALVO, W = 21.385, 0.0843
    r = iso_curva('ev', ALVO, W, 10, [i / 100 for i in range(0, 8)], tv='convergencia')
    todos_null = all(p.get('rent_implicita_pct') is None or p['check_multiplo'] is None
                     or 'sem raiz' in p.get('diagnostico', '') for p in r['curva'])
    check('iso sugestao: premissa do caso — nenhum ponto com raiz em g 0–7%', todos_null,
          f"({[p.get('diagnostico', '')[:20] for p in r['curva'][:3]]})")
    check('iso sugestao: campo sugestao presente quando TODOS os pontos são null',
          'sugestao' in r, f'(chaves: {sorted(r)[:8]})')
    check('iso sugestao: sugestao avisa que a fronteira pode existir FORA do intervalo',
          'intervalo' in r.get('sugestao', '').lower())
    check('iso sugestao: varredura grosseira acha o início da fronteira (~8%)',
          'g' in r.get('sugestao', '') and '8' in r.get('sugestao', ''),
          f"({r.get('sugestao', '')[-90:]})")
    # com raiz em pelo menos um ponto, a sugestão NÃO aparece (g=10% ⟹ rent 24,00% do relatório)
    ok = iso_curva('ev', ALVO, W, 10, [0.09, 0.10], tv='convergencia')
    tem_raiz = any(p.get('rent_implicita_pct') for p in ok['curva'])
    check('iso sugestao: com raiz no intervalo, sem campo sugestao',
          tem_raiz and 'sugestao' not in ok,
          f"(raizes={[p.get('rent_implicita_pct') for p in ok['curva']]})")
    print('  v9.14: iso com grade toda null sugere ampliar o intervalo e aponta onde a fronteira começa')


def rec_gate_agregado():
    """[v9.13 / rodada 2 da execução fria FNV] O booleano GATE do `drivers` só olhava os
    individuais: gate = len(relevantes) > 0. O líquido agregado era calculado, exibido na
    compensação e IGNORADO pela luz — no caso FNV, 6 drivers todos abaixo de 10% somando −12,63%,
    e o painel devolvia GATE: false. A própria nota do motor dizia "o líquido decide o gate
    agregado": o motor contradizia a doutrina. Um analista que confie na luz pula o cenário
    normalizado obrigatório. Terceira ocorrência da família 'resultado com cara de certo'
    (v9.9 portabilidade; v9.12 escala do nivel).

    Caso de reprodução: os SEIS drivers da FNV rodada 2, números do relatório de auditoria
    (auditorias/08), elasticidades derivadas como lá."""
    fnv = [
        {'nome': 'ouro', 'base': 4792.9, 'spot': 4250.0, 'elast': None,
         'receita_driver': 436.9, 'metrica_base': 591.9, 'sentido': 'receita'},
        {'nome': 'prata', 'base': 80.10, 'spot': 61.00, 'elast': None,
         'receita_driver': 113.5, 'metrica_base': 591.9, 'sentido': 'receita'},
        {'nome': 'petroleo_NGL_WTI', 'base': 68.0, 'spot': 80.0, 'elast': None,
         'receita_driver': 32.6, 'metrica_base': 591.9, 'sentido': 'receita'},
        {'nome': 'gas_HH', 'base': 3.60, 'spot': 3.30, 'elast': None,
         'receita_driver': 20.6, 'metrica_base': 591.9, 'sentido': 'receita'},
        {'nome': 'minerio_ferro', 'base': 100.0, 'spot': 98.0, 'elast': None,
         'receita_driver': 17.1, 'metrica_base': 591.9, 'sentido': 'receita'},
        {'nome': 'PGM_platina', 'base': 2350.0, 'spot': 2100.0, 'elast': None,
         'receita_driver': 17.7, 'metrica_base': 591.9, 'sentido': 'receita'},
    ]
    r = registro_drivers(fnv)
    imps = [d['impacto_%'] for d in r['drivers']]
    liq = r['compensacao']['efeito_liquido_total_%']
    check('gate agregado: todos os individuais abaixo do limiar (premissa do caso)',
          all(i < 10 for i in imps), f'({imps})')
    check('gate agregado: líquido reproduz a rodada 2 (−12,63%)',
          abs(liq - (-12.63)) < 0.05, f'({liq})')
    check('gate agregado: GATE dispara pelo LÍQUIDO mesmo sem individual acima do limiar',
          r['GATE'] is True, f"(GATE={r['GATE']}, líquido={liq}%)")
    check('gate agregado: campo GATE_agregado presente e verdadeiro',
          r.get('GATE_agregado') is True)
    check('gate agregado: nota explica o disparo agregado',
          'líquido' in r.get('nota', '').lower() or 'agregado' in r.get('nota', '').lower(),
          f"({r.get('nota', '')[:90]})")
    # o caminho individual segue intacto: um driver dominante dispara como sempre
    dom = registro_drivers([{'nome': 'dominante', 'base': 100.0, 'spot': 130.0, 'elast': 0.8,
                             'sentido': 'receita'}])
    check('gate agregado: disparo individual preservado', dom['GATE'] is True)
    check('gate agregado: individual sem agregado ⟹ GATE_agregado presente',
          'GATE_agregado' in dom)
    # e sem NADA acima do limiar (individual ou líquido), a luz continua verde
    calmo = registro_drivers([{'nome': 'calmo', 'base': 100.0, 'spot': 103.0, 'elast': 0.5,
                               'sentido': 'receita'}])
    check('gate agregado: caso calmo segue GATE=false (sem falso positivo)',
          calmo['GATE'] is False and calmo.get('GATE_agregado') is False,
          f"(GATE={calmo['GATE']})")
    print('  v9.13: GATE do drivers decide por individual OU líquido agregado — caso FNV rodada 2')


def rec_nivel_escala():
    """[v9.12 / S-1 do dossiê FNV] `nivel` aceitava `--vol` em escala diferente da métrica-base e
    devolvia `preco_driver_implicito ≈ preco_base` EM SILÊNCIO: o auditor recebeu US$ 3.944,0023
    contra base de US$ 3.944 e quase leu como achado ("o preço implícito é o preço de hoje"). O
    valor correto era US$ 6.251/oz. Mesma CLASSE do defeito de portabilidade da v9.9 — não produz
    FALHOU, produz algo com cara de resultado.

    A assinatura do erro é específica e NÃO se confunde com "o mercado não embute degrau": ali o
    ajuste é pequeno porque o NUMERADOR é pequeno. Aqui o degrau da métrica é material (+44,5%) e
    ainda assim o ajuste de preço é desprezível. Só as duas condições JUNTAS caracterizam escala
    incoerente — é isso que o teste trava, para não criar falso positivo."""
    from justos import nivel_implicito
    ALVO, MULT, BASE, PB = 40491.9, 14.5438, 1926.1, 3944.0
    # (1) caso do auditor: volume em ONÇAS contra métrica em US$ milhões
    err = nivel_implicito(ALVO, MULT, BASE, vol=371900, preco_base=PB)
    check('S-1: degrau material reportado mesmo na escala errada',
          abs(err['degrau_implicito_%'] - 44.5) < 0.1, f"({err['degrau_implicito_%']})")
    check('S-1: escala incoerente é SINALIZADA (não devolve preço≈base calado)',
          'aviso_escala' in err, f'(chaves: {sorted(err)})')
    # (2) escala correta (Moz, mesma escala da métrica): reproduz o número do dossiê
    ok = nivel_implicito(ALVO, MULT, BASE, vol=0.3719, preco_base=PB)
    check('S-1: escala correta devolve US$ 6.251/oz (dossiê)',
          abs(ok['preco_driver_implicito'] - 6251) < 1.0, f"({ok.get('preco_driver_implicito')})")
    check('S-1: escala correta NÃO dispara o aviso', 'aviso_escala' not in ok,
          f"({ok.get('aviso_escala')})")
    # (3) sem falso positivo: sem degrau, o ajuste é pequeno por causa do NUMERADOR
    sem = nivel_implicito(BASE * MULT, MULT, BASE, vol=0.3719, preco_base=PB)
    check('S-1: sem degrau ⟹ sem falso positivo de escala', 'aviso_escala' not in sem,
          f"({sem.get('aviso_escala')})")
    # [v9.14 / rodada 3, §13.4] o nivel mantém o MÚLTIPLO fixo; a doutrina (§7, dupla alavanca)
    # ensina que nível maior ⟹ d menor ⟹ múltiplo justo MAIOR ⟹ preço implícito MENOR. Na rodada
    # 3: comando 15.240 vs conta completa 13.495 (11%). O output passa a declarar o viés.
    check('S-1/v9.14: preço implícito vem com nota de limite superior (dupla alavanca)',
          'LIMITE SUPERIOR' in ok.get('nota_dupla_alavanca', ''),
          f"({sorted(ok)})")
    check('S-1/v9.14: sem vol/preco_base, sem nota',
          'nota_dupla_alavanca' not in nivel_implicito(40491.9, 14.5438, 1926.1))
    print('  v9.12/S-1 + v9.14: nivel sinaliza escala incoerente E declara o limite superior da dupla alavanca')


def rec_guarda_raiz_gp():
    """[v9.12 / D-2 do dossiê FNV] Quando a variável RESOLVIDA é o gp, a guarda macro tem de
    incidir sobre a RAIZ, não sobre o chute inicial.

    O dossiê registrou o sintoma como "rev rodado sem --rf". Verificando o pacote, o `rev` já
    aceitava `--rf`/`--moeda` desde a v9.4 — o defeito é outro e pior: COM as flags, a reversa
    devolvia raiz gp = 6,215% enquanto a guarda reportava "ÂNCORA MACRO OK: gp = 2,50%", que é o
    valor de ENTRADA. Guarda verde sobre uma resposta fora do teto é falso negativo — pior que
    silêncio, porque tem cara de verificação feita. O auditor teve de descartar a raiz à mão."""
    import subprocess, json, os
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'justos.py')
    def argv_rev(alvo, rf):
        # lista montada ANTES da chamada: o lint de portabilidade desembrulha um nível de BinOp,
        # e concatenação aninhada esconde o literal [sys.executable, ...] dele. Ele está certo.
        return ['rev', '--alvo', alvo, '--base', 'ebitda', '--resolver', 'gp',
                '--g', '11.62', '--roic', '15', '--wacc', '8.43', '--n', '10',
                '--da', '16.42', '--tax', '21.27', '--tv', 'gordon', '--roic-tv', '11',
                '--gp', '2.5', '--rf', rf, '--moeda', 'USD-nominal']
    args = argv_rev('21.02', '4.62')
    r = subprocess.run([sys.executable, script] + args,
                       capture_output=True, text=True, encoding='utf-8')
    check('D-2: rev com --rf/--moeda roda', r.returncode == 0, f'({r.stderr[-160:]})')
    o = json.loads(r.stdout)
    raizes = o.get('raizes_gp_%', [])
    check('D-2: reversa em gp devolve a raiz do dossiê (6,215%)',
          raizes and abs(raizes[0] - 6.215) < 0.01, f'({raizes})')
    g = ' | '.join(o.get('guardas_v9_4', []))
    check('D-2: a guarda incide sobre a RAIZ, não sobre o chute de entrada',
          '2.50%' not in g, f'({g[:150]})')
    check('D-2: raiz acima do teto dispara ALERTA, não "OK"',
          'ALERTA' in g and 'EXCEDE' in g, f'({g[:150]})')
    check('D-2: o alerta cita a raiz que violou', '6.215' in g, f'({g[:150]})')
    # contraprova: raiz ABAIXO do teto não pode gerar alerta
    args2 = argv_rev('12.0', '9.0')
    r2 = subprocess.run([sys.executable, script] + args2,
                        capture_output=True, text=True, encoding='utf-8')
    if r2.returncode == 0:
        g2 = ' | '.join(json.loads(r2.stdout).get('guardas_v9_4', []))
        check('D-2: sem falso positivo quando a raiz respeita o teto',
              'EXCEDE' not in g2, f'({g2[:140]})')
    print('  v9.12/D-2: guarda macro do rev avaliada na RAIZ resolvida, não no valor de entrada')


def rec_doc_anchors():
    """[v9.11] Os docs afirmam ~38 números fechados que sustentam ARGUMENTOS de doutrina — "mesmas
    palavras, o dobro do valor" só funciona porque 9,86 e 20,55 estão ali. Nada os recomputava: se
    uma fórmula mudasse, o selftest gritaria e a prosa continuaria afirmando o número velho, calada.
    Este teste ancora cada afirmação ao motor.

    Cada entrada declara OBRIGATORIAMENTE a base. Não é burocracia: durante a auditoria da v9.11 um
    número do Apêndice C foi lido como EV/NOPAT corrente quando era EV/EBITDA FORWARD, e o
    'divergência' resultante era erro de leitura, não deriva. O número sem a base grudada é
    ambíguo mesmo para quem conhece o pacote."""
    def eb_fwd(m, g, d=0.15, t=0.15):
        """Ponte EBITDA + base forward: EV/EBITDA fwd = EV/NOPAT × (1−d)(1−t) / (1+g)."""
        return m * (1 - d) * (1 - t) / (1 + g)

    def sup_g(tv, n, roic=0.085, w=0.07, **kw):
        """Supremo sobre g com RiR <= 100% (g <= ROIC) — a fronteira do autofinanciável.
        NÃO é o supremo com g→W: essa faixa dá outro número (paper §6.4, Apêndice C)."""
        grade = [i * roic / 400 for i in range(401)]          # inclui o extremo g = ROIC
        vals = [eb_fwd(ev_nopat(g, roic, w, n, tv=tv, **kw), g) for g in grade]
        return max(v for v in vals if v == v)

    def segmentos(nA, rA, gA, nB, rB, gB, w=0.08, n=10):
        """(segmentado, blended) — g ponderado por NOPAT, rentabilidade por capital."""
        seg = (nA * ev_nopat(gA, rA, w, n, tv='convergencia')
               + nB * ev_nopat(gB, rB, w, n, tv='convergencia'))
        nop, cap = nA + nB, nA / rA + nB / rB
        return seg, nop * ev_nopat((nA * gA + nB * gB) / nop, nop / cap, w, n, tv='convergencia')

    # (onde, arquivo, literal que DEVE estar no doc, base declarada, chamada, valor, tolerância)
    # literal=None só quando a afirmação é qualitativa (identidade sem número impresso).
    DOC_ANCHORS = [
        ('SKILL: g=0 não neutraliza ROIC na book', 'SKILL.md', '23,97x', 'EV/NOPAT corrente',
         lambda: ev_nopat(0.0, 0.03, 0.07, 10, tv='book'), 23.97, 0.005),
        ('SKILL: idem, ROIC 50%', 'SKILL.md', '8,04x', 'EV/NOPAT corrente',
         lambda: ev_nopat(0.0, 0.50, 0.07, 10, tv='book'), 8.04, 0.005),
        ('SKILL: book ROE=Ke neutro com caixa (g=0)', 'SKILL.md', 'Caixa/E é neutro', 'P/L forward',
         lambda: pe(0.0, 0.12, 0.12, 10, 0.20, 0.0, tv='book'), 8.33, 0.005),
        ('SKILL: idem, g=6%', 'SKILL.md', 'independentemente de caixa/E', 'P/L forward',
         lambda: pe(0.06, 0.12, 0.12, 10, 0.20, 0.0, tv='book') / 1.06, 8.3333333333, 0.005),
        ('SKILL: gap entre convenções (book)', 'SKILL.md', '9,86x', 'EV/NOPAT corrente',
         lambda: ev_nopat(0.05, 0.50, 0.07, 10, tv='book'), 9.86, 0.005),
        ('SKILL: gap entre convenções (convergencia)', 'SKILL.md', '20,55x', 'EV/NOPAT corrente',
         lambda: ev_nopat(0.05, 0.50, 0.07, 10, tv='convergencia'), 20.55, 0.005),
        ('SKILL: convenções cruzam em ROIC=WACC', 'SKILL.md', None, 'EV/NOPAT — diferença',
         lambda: ev_nopat(0.05, 0.07, 0.07, 10, tv='book')
                 - ev_nopat(0.05, 0.07, 0.07, 10, tv='convergencia'), 0.0, 1e-9),
        ('paper §6.3: perversidade conflacionada (ROIC 2%)', 'references/paper-multiplos-justos-v3.md',
         '30,20x', 'EV/NOPAT forward',
         lambda: ev_nopat(0.03, 0.02, 0.07, 10, tv='book') / 1.03, 30.20, 0.005),
        ('paper §6.3: idem, ROIC 15%', 'references/paper-multiplos-justos-v3.md',
         '10,89x', 'EV/NOPAT forward',
         lambda: ev_nopat(0.03, 0.15, 0.07, 10, tv='book') / 1.03, 10.89, 0.005),
        ('SKILL: book separado, marginal 2% (v9.26)', 'SKILL.md', '10,16x', 'EV/NOPAT corrente',
         lambda: ev_nopat(0.03, 0.02, 0.07, 10, tv='book', roic_book=0.10), 10.16, 0.005),
        ('SKILL: book separado, marginal 8% (v9.26)', 'SKILL.md', '12,59x', 'EV/NOPAT corrente',
         lambda: ev_nopat(0.03, 0.08, 0.07, 10, tv='book', roic_book=0.10), 12.59, 0.005),
        ('paper §6.12: caso A segmentado', 'references/paper-multiplos-justos-v3.md',
         '1.393,4', 'valor absoluto',
         lambda: segmentos(20, 0.40, 0.06, 80, 0.08, 0.02)[0], 1393.4, 0.1),
        ('paper §6.12: caso A blended', 'references/paper-multiplos-justos-v3.md',
         '1.328,1', 'valor absoluto',
         lambda: segmentos(20, 0.40, 0.06, 80, 0.08, 0.02)[1], 1328.1, 0.1),
        ('paper §6.12: caso B segmentado', 'references/paper-multiplos-justos-v3.md',
         '1.365,4', 'valor absoluto',
         lambda: segmentos(50, 0.35, 0.01, 50, 0.09, 0.06)[0], 1365.4, 0.1),
        ('paper §6.12: caso B blended', 'references/paper-multiplos-justos-v3.md',
         '1.447,7', 'valor absoluto',
         lambda: segmentos(50, 0.35, 0.01, 50, 0.09, 0.06)[1], 1447.7, 0.1),
        ('paper §3.2: mortalidade λ=0', 'references/paper-multiplos-justos-v3.md',
         '23,41', 'EV/NOPAT corrente',
         lambda: ev_nopat(0.05, 0.15, 0.07, 10, tv='gordon', roic_tv=0.15, gp=0.03), 23.41, 0.005),
        ('paper §3.2: mortalidade λ=2%', 'references/paper-multiplos-justos-v3.md',
         '19,54', 'EV/NOPAT corrente',
         lambda: ev_nopat(0.05, 0.15, 0.07, 10, tv='gordon', roic_tv=0.15, gp=0.01), 19.54, 0.005),
        ('paper §3.2: mortalidade λ=3%', 'references/paper-multiplos-justos-v3.md',
         '18,44', 'EV/NOPAT corrente',
         lambda: ev_nopat(0.05, 0.15, 0.07, 10, tv='gordon', roic_tv=0.15, gp=0.00), 18.44, 0.005),
        ('paper §3.2: mortalidade λ=5%', 'references/paper-multiplos-justos-v3.md',
         '16,97', 'EV/NOPAT corrente',
         lambda: ev_nopat(0.05, 0.15, 0.07, 10, tv='gordon', roic_tv=0.15, gp=-0.02), 16.97, 0.005),
        ('paper Apêndice C: book g=5%', 'references/paper-multiplos-justos-v3.md',
         '9,60', 'EV/EBITDA FORWARD (d 15%, t 15%)',
         lambda: eb_fwd(ev_nopat(0.05, 0.085, 0.07, 10, tv='book'), 0.05), 9.60, 0.005),
        ('paper Apêndice C: convergencia g=5%', 'references/paper-multiplos-justos-v3.md',
         '11,10', 'EV/EBITDA FORWARD',
         lambda: eb_fwd(ev_nopat(0.05, 0.085, 0.07, 10, tv='convergencia'), 0.05), 11.10, 0.005),
        ('paper Apêndice C: gordon gp 3%', 'references/paper-multiplos-justos-v3.md',
         '15,27', 'EV/EBITDA FORWARD',
         lambda: eb_fwd(ev_nopat(0.05, 0.085, 0.07, 10, tv='gordon', roic_tv=0.20, gp=0.03), 0.05),
         15.27, 0.005),
        ('paper Apêndice C: gordon gp 4%', 'references/paper-multiplos-justos-v3.md',
         '18,51', 'EV/EBITDA FORWARD',
         lambda: eb_fwd(ev_nopat(0.05, 0.085, 0.07, 10, tv='gordon', roic_tv=0.20, gp=0.04), 0.05),
         18.51, 0.005),
        ('paper Apêndice C: supremo book n=10', 'references/paper-multiplos-justos-v3.md',
         '9,77', 'EV/EBITDA FORWARD, sup sobre g com RiR<=100% (g<=ROIC)',
         lambda: sup_g('book', 10), 9.77, 0.01),
        ('paper Apêndice C: supremo convergencia n=10', 'references/paper-multiplos-justos-v3.md',
         '11,86', 'EV/EBITDA FORWARD, sup com RiR<=100%',
         lambda: sup_g('convergencia', 10), 11.86, 0.01),
        ('paper §6.4: supremo convergencia n=100', 'references/paper-multiplos-justos-v3.md',
         '41,52', 'EV/EBITDA FORWARD, sup com RiR<=100%',
         lambda: sup_g('convergencia', 100), 41.52, 0.02),
        ('aplicacao §2: teto da book sobe com o CAP (n=100)', 'references/aplicacao.md',
         '34x', 'EV/EBITDA FORWARD, sup com RiR<=100%',
         lambda: sup_g('book', 100), 34.2, 0.1),
    ]
    import os
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cache = {}
    for onde, arq, literal, base, fn, alvo, tol in DOC_ANCHORS:
        # (1) o motor ainda produz o número afirmado?  -> pega deriva de FÓRMULA
        try:
            v = fn()
        except Exception as e:                                     # noqa: BLE001
            check(f'doc anchor {onde}', False, f'(erro ao recomputar: {e})')
            continue
        check(f'doc anchor {onde} [{base}]', v == v and abs(v - alvo) <= tol,
              f'(doc={alvo} motor={v!r})')
        # (2) o número afirmado ainda está NO DOC?  -> pega deriva de TEXTO (edição do paper
        # sem passar pelo motor); sem isto o teste só compararia motor contra esta tabela.
        if literal is None:
            continue
        if arq not in cache:
            cache[arq] = open(os.path.join(base_dir, arq), encoding='utf-8').read()
        check(f'doc anchor {onde}: literal "{literal}" presente em {arq}',
              literal in cache[arq])
    print(f'  v9.11: {len(DOC_ANCHORS)} afirmações dos docs — recomputadas no motor E conferidas '
          f'como literal no arquivo, cada uma com a BASE declarada')


def rec_b01():
    """[v9.10 / rodada 5, B-01 — atualizado v9.26] A trava da 'book' com marginal < custo é do
    caso CONFLACIONADO, não da convenção. Com o retorno médio informado à parte, o múltiplo é
    monotonicamente CRESCENTE no marginal (a perversidade não existe) e a raiz é CONDICIONADA a
    tese de saída pelo capital investido — nunca proibida nem economicamente vazia. [v9.26] O TV
    ACOMPANHA o marginal pelo termo de acumulação (o capital novo entra ao marginal e o médio
    deriva) — a contraprova por acumulação explícita ano a ano fecha com a forma fechada do motor.
    Sub-diagnóstico próprio quando o próprio book fica abaixo do custo: a âncora inicial
    (IC_0 = NOPAT/book) excede NOPAT/W pelo fator W/book (cruzamento exato em book = W)."""
    from justos import iso_curva, diag_firm, diag_eq
    g, w, n, rb = 0.03, 0.07, 10, 0.10
    rents = (0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08)
    # (1) com book separado: monotonicidade CRESCENTE no marginal
    ms = [ev_nopat(g, r, w, n, tv='book', roic_book=rb) for r in rents]
    check('B-01: múltiplo CRESCE com o marginal quando o book é separado',
          all(b > a for a, b in zip(ms, ms[1:])), f'({[round(m, 4) for m in ms]})')
    check('B-01: anchor da contraprova (marginal 5%, book 10%, W 7%, n 10 ⟹ 12,10x — v9.26)',
          abs(ms[3] - 12.1007) < 5e-4, f'({ms[3]})')
    # (2) [v9.26] o TV ACOMPANHA o marginal pelo IC acumulado — contraprova por acumulação
    # explícita ano a ano (IC_0 = NOPAT_1/book; IC_t = IC_{t-1} + (g/marginal)·NOPAT_t):
    def tv_implicito(r):
        expl = sum((1 - g / r) * (1 + g) ** t / (1 + w) ** t for t in range(1, n + 1))
        return ev_nopat(g, r, w, n, tv='book', roic_book=rb) - expl
    def ic_acumulado(r):
        nop = [(1 + g) ** t for t in range(0, n + 1)]
        ic = (1 + g) / rb
        for t in range(1, n + 1):
            ic += (g / r) * nop[t]
        return ic
    check('B-01/v9.26: TV = IC acumulado (capital novo ao marginal), fluxo a fluxo',
          all(abs(tv_implicito(r) - ic_acumulado(r) / (1 + w) ** n) < 1e-10 for r in rents))
    check('B-01/v9.26: o TV MOVE com o marginal — capital-light sai com menos patrimônio',
          tv_implicito(0.08) < tv_implicito(0.02),
          f'({tv_implicito(0.08):.4f} vs {tv_implicito(0.02):.4f})')
    # (3) no caso CONFLACIONADO a perversidade É real — a trava continua valendo lá
    mc = [ev_nopat(g, r, w, n, tv='book') for r in rents]
    check('B-01: no caso conflacionado o múltiplo CAI com o marginal (perversidade real)',
          all(b < a for a, b in zip(mc, mc[1:])), f'({[round(m, 4) for m in mc]})')
    # (4) a raiz exata deixa de ser descartada
    alvo = ev_nopat(g, 0.05, w, n, tv='book', roic_book=rb)
    p = iso_curva('ev', alvo, w, n, [g], tv='book', rent_book=rb)['curva'][0]
    check('B-01: iso encontra a raiz exata (check = 0)', p['check_multiplo'] == 0.0)
    check('B-01: raiz classificada CONDICIONADA, não descartada',
          'CONDICIONADA' in p['diagnostico'] and 'proibida' not in p['diagnostico'],
          f"({p['diagnostico'][:80]})")
    check('B-01: sem sub-alerta quando o book está ACIMA do custo',
          'SUB-ALERTA' not in p['diagnostico'])
    # (5) sub-diagnóstico: book abaixo do custo ⟹ perversidade migra para o papel médio
    alvo2 = ev_nopat(g, 0.05, w, n, tv='book', roic_book=0.05)
    p2 = iso_curva('ev', alvo2, w, n, [g], tv='book', rent_book=0.05)['curva'][0]
    check('B-01: sub-alerta dispara com book < custo', 'SUB-ALERTA' in p2['diagnostico'],
          f"({p2['diagnostico'][:100]})")
    check('B-01: fator do sub-alerta = W/book (1,40x a 7% contra 5%)',
          '1.40x' in p2['diagnostico'], f"({p2['diagnostico'][-90:]})")
    tv_b, tv_c = (1 + g) ** (n + 1) / (0.05 * (1 + w) ** n), (1 + g) ** (n + 1) / (w * (1 + w) ** n)
    check('B-01: com book < W o TV da book EXCEDE o da convergencia', tv_b > tv_c)
    tv_eq = (1 + g) ** (n + 1) / (w * (1 + w) ** n)
    check('B-01: cruzamento exato em book = W', abs(tv_eq - tv_c) < 1e-12)
    # (6) diagnósticos por lado: os três estados existem e são distintos
    for lado, fn, kw_conf, kw_sep, kw_sub in (
            ('firm', diag_firm, dict(tv='book'), dict(tv='book', roic_book=0.10),
             dict(tv='book', roic_book=0.05)),
            ('eq', diag_eq, dict(tv='book'), dict(tv='book', roe_book=0.10),
             dict(tv='book', roe_book=0.05))):
        args = (g, 0.05, w) if lado == 'firm' else (g, 0.05, w, 0.0, 0.0)
        conf = ' '.join(fn(*args, **kw_conf))
        sep = ' '.join(fn(*args, **kw_sep))
        subd = ' '.join(fn(*args, **kw_sub))
        check(f'B-01/{lado}: conflacionado ⟹ ALERTA DE CONFLAÇÃO', 'CONFLAÇÃO' in conf)
        check(f'B-01/{lado}: separado ⟹ CONVENÇÃO CONDICIONADA', 'CONDICIONADA' in sep)
        check(f'B-01/{lado}: separado NÃO afirma que o TV cresce quando o retorno cai',
              'CONFLAÇÃO' not in sep)
        check(f'B-01/{lado}: book < custo ⟹ SUB-ALERTA do papel médio', 'SUB-ALERTA' in subd)
        check(f'B-01/{lado}: book > custo ⟹ sem SUB-ALERTA', 'SUB-ALERTA' not in sep)
    print('  v9.10/B-01: trava bifurcada (conflacionado × separado), TV imóvel, sub-alerta do médio')


def rec_apv01():
    """[v9.10 / rodada 5, APV-01] O regime canônico 'ku' descreve o MECANISMO implementado —
    shields a Ku sobre dívida EXÓGENA D_t = D0(1+g)^t. Ele não é Harris-Pringle completo, que
    exigiria D_t = L×V_t com D/V constante. Este teste TRAVA a não-constância: se um dia o motor
    passar a impor alavancagem-alvo, ele falha e força a revisão do rótulo e da doutrina."""
    a = apv_recursao(22.184, 0.11, 10, 0.20, 0.142714285714286, 0.30, 35.0,
                     fcff_tv=50.5317555785773, gtv=0.0, conv='ku')
    dv = a['DV_t_%']
    check('APV-01: DV_t_% ecoado no output', isinstance(dv, list) and len(dv) == 11, f'({dv})')
    check('APV-01: D/V NÃO é constante (dívida exógena, não L×V)',
          max(dv) - min(dv) > 1.0, f'(amplitude {max(dv) - min(dv):.2f} p.p.)')
    check('APV-01: trajetória reproduz a contraprova da rodada 5 (18,75% → 36,28%)',
          abs(dv[0] - 18.7457) < 1e-3 and abs(dv[-1] - 36.2788) < 1e-3, f'({dv[0]}, {dv[-1]})')
    check('APV-01: D/V monotonicamente crescente na âncora',
          all(b > x for x, b in zip(dv, dv[1:])))
    check('APV-01: nota de não-constância acompanha a série',
          'constante' in a.get('nota_DV', ''), f"({a.get('nota_DV', '')[:60]})")
    check('APV-01: convenção declara dívida exógena E nega a constância de D/V',
          'EXÓGENA' in a['convencao'] and 'não é mantido constante' in a['convencao'].lower()
          and 'rebalanceamento contínuo' not in a['convencao'], f"({a['convencao']})")
    # hp/me deixam de ser aliases: função direta também deve rejeitar semântica falsa.
    for al in ('hp', 'me'):
        b = apv_recursao(22.184, 0.11, 10, 0.20, 0.142714285714286, 0.30, 35.0,
                         fcff_tv=50.5317555785773, gtv=0.0, conv=al)
        check(f'APV-01: {al} rejeitado explicitamente', 'erro' in b and 'não implementada' in b['erro'])
    # o check de Fernández não pode mais anunciar 'ME'
    check('APV-01: check de Fernández rotulado pelo regime real',
          'ME' not in str(a['check_Ke_dinamico_igual_formula_Fernandez']),
          f"({a['check_Ke_dinamico_igual_formula_Fernandez']})")
    print('  v9.28/APV-01: canônico ku, D/V não constante e aliases semânticos removidos')


def rec_p02():
    """[v9.10 / rodada 5, P-02] O viés do blended na agregação por segmentos NÃO tem sinal
    universal: a Hessiana de M(g, rentabilidade) é INDEFINIDA na região relevante, logo não há
    convexidade conjunta e não há Jensen a invocar. O teste exibe os DOIS sinais em casos
    admissíveis — se um dia sobrar só um, a proposição do §6.12 voltou a ser mais forte do que a
    álgebra sustenta."""
    W, N = 0.08, 10
    def erro_blended(nA, rA, gA, nB, rB, gB):
        seg = (nA * ev_nopat(gA, rA, W, N, tv='convergencia')
               + nB * ev_nopat(gB, rB, W, N, tv='convergencia'))
        nop, cap = nA + nB, nA / rA + nB / rB
        bl = nop * ev_nopat((nA * gA + nB * gB) / nop, nop / cap, W, N, tv='convergencia')
        return (bl / seg - 1) * 100
    eA = erro_blended(20, 0.40, 0.06, 80, 0.08, 0.02)   # caso A do paper §6.12
    eB = erro_blended(50, 0.35, 0.01, 50, 0.09, 0.06)   # caso B do paper §6.12
    check('P-02: caso A — blended SUBESTIMA', eA < 0, f'({eA:.2f}%)')
    check('P-02: caso B — blended SUPERESTIMA', eB > 0, f'({eB:.2f}%)')
    check('P-02: anchors do §6.12 (−4,7% e +6,0%)',
          abs(eA + 4.69) < 0.05 and abs(eB - 6.03) < 0.05, f'({eA:.2f}%, {eB:.2f}%)')
    h, g0, r0 = 1e-5, 0.04, 0.15
    M = lambda gg, rr: ev_nopat(gg, rr, W, N, tv='convergencia')
    fgg = (M(g0 + h, r0) - 2 * M(g0, r0) + M(g0 - h, r0)) / h ** 2
    frr = (M(g0, r0 + h) - 2 * M(g0, r0) + M(g0, r0 - h)) / h ** 2
    fgr = (M(g0 + h, r0 + h) - M(g0 + h, r0 - h)
           - M(g0 - h, r0 + h) + M(g0 - h, r0 - h)) / (4 * h ** 2)
    det = fgg * frr - fgr ** 2
    check('P-02: Hessiana INDEFINIDA (det < 0 ⟹ autovalores de sinais opostos)',
          det < 0, f'(det = {det:.1f})')
    check('P-02: as duas curvaturas puras têm sinais opostos', fgg * frr < 0,
          f'(∂²/∂g² = {fgg:.1f}, ∂²/∂rent² = {frr:.1f})')
    print('  v9.10/P-02: os dois sinais do viés do blended + Hessiana indefinida (sem Jensen)')


def cli_integration():
    import subprocess, json, os
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'justos.py')
    def run(args):
        r = subprocess.run([sys.executable, script] + args, capture_output=True, text=True,
                           encoding='utf-8')
        return r.returncode, r.stdout, r.stderr
    def run_json(nome, args, esperados=()):
        rc, out, err = run(args)
        check(f'CLI {nome}: returncode 0', rc == 0, f'(rc={rc}, stderr={err[-160:]})')
        try:
            d = json.loads(out)
        except Exception as e:
            check(f'CLI {nome}: JSON parseável', False, f'({e})'); return {}
        blob = json.dumps(d, ensure_ascii=False)
        for esp in esperados:
            check(f'CLI {nome}: contém "{esp[:44]}"', esp in blob)
        return d

    # [v9.26] --tv ausente: JSON de parada do Gate 1 (nunca usage cru do argparse) e rc=2 —
    # a mensagem instrui o agente a PERGUNTAR a convenção, não a adivinhar.
    rc, out, err = run(['ev', '--g', '5', '--roic', '15', '--wacc', '9', '--da', '30',
                        '--tax', '34'])
    check('CLI --tv ausente: returncode 2', rc == 2, f'(rc={rc})')
    try:
        d_tv = json.loads(out)
        check('CLI --tv ausente: JSON com erro do Gate 1',
              'Gate 1' in d_tv.get('erro', '') and 'instrucao' in d_tv and 'opcoes' in d_tv,
              f'({out[:120]})')
        check('CLI --tv ausente: instrução manda PARAR e perguntar',
              'PARE' in d_tv.get('instrucao', ''))
    except Exception as e:
        check('CLI --tv ausente: JSON parseável em stdout', False, f'({e}; out={out[:120]})')

    # [v9.27] --tv PRESENTE porém inválido não é ausência de Gate 1: argparse deve dizer invalid choice.
    rc, out, err = run(['ev', '--g', '5', '--roic', '15', '--wacc', '9', '--da', '30',
                        '--tax', '34', '--tv', 'xyz'])
    check('CLI --tv inválido: returncode 2', rc == 2, f'(rc={rc})')
    check('CLI --tv inválido: mantém diagnóstico invalid choice do argparse',
          'invalid choice' in err and 'Gate 1' not in out, f'(stdout={out[:80]} stderr={err[-120:]})')

    # ev × três convenções (gordon com C7 ecoado)
    run_json('ev book', ['ev', '--g', '5', '--roic', '25', '--roic-book', '10', '--wacc', '7',
                         '--n', '10', '--da', '15', '--tax', '15', '--tv', 'book'])
    run_json('ev convergencia', ['ev', '--g', '5', '--roic', '8.5', '--wacc', '7', '--n', '10',
                                 '--da', '15', '--tax', '15', '--tv', 'convergencia'])
    run_json('ev gordon', ['ev', '--g', '5', '--roic', '8.5', '--wacc', '7', '--n', '10',
                           '--da', '15', '--tax', '15', '--tv', 'gordon', '--roic-tv', '20',
                           '--gp', '3'], esperados=('convencao_fluxo_transicao_C7',))
    # pe × três convenções, SEMPRE com caixa ≠ 0 (gde ≠ nde) — inclui o caso que crashava na v8.3
    run_json('pe book caixa', ['pe', '--g', '11', '--roe', '44.83', '--ke', '22', '--n', '10',
                               '--gde', '53.85', '--nde', '46.15', '--tv', 'book'])
    run_json('pe convergencia caixa', ['pe', '--g', '6', '--roe', '18', '--ke', '12', '--n', '10',
                                       '--gde', '20', '--nde', '0', '--tv', 'convergencia'])
    d = run_json('pe gordon caixa (crash v8.3)', ['pe', '--g', '6', '--roe', '18', '--ke', '12',
                 '--n', '10', '--gde', '20', '--nde', '0', '--tv', 'gordon', '--roe-tv', '15',
                 '--gp', '3'], esperados=('POLÍTICA DE CAIXA NO TERMINAL', 'LIMITAÇÃO DECLARADA (C2)',
                                          'convencao_fluxo_transicao_C7', 'decomposicao'))
    check('CLI pe gordon: PL_curr numérico', isinstance(d.get('PL_curr'), (int, float)))
    run_json('pe gordon encerra', ['pe', '--g', '6', '--roe', '18', '--ke', '12', '--n', '10',
                                   '--gde', '20', '--nde', '0', '--tv', 'gordon', '--roe-tv', '15',
                                   '--gp', '3', '--politica-tv', 'encerra'],
             esperados=("'encerra'",))
    # rev: raiz em g (gordon), CAP (book), roe no lado pl com caixa
    run_json('rev g gordon', ['rev', '--alvo', '12', '--resolver', 'g', '--base', 'nopat',
                              '--roic', '15', '--wacc', '9', '--n', '10', '--tv', 'gordon',
                              '--roic-tv', '15', '--gp', '3'], esperados=('raizes_g_%',))
    run_json('rev cap book', ['rev', '--alvo', '8', '--resolver', 'cap', '--g', '5', '--roic', '15',
                              '--wacc', '9', '--base', 'nopat', '--tv', 'book'],
             esperados=('CAP_implicito_anos',))
    run_json('rev roe pl caixa', ['rev', '--alvo', '10', '--resolver', 'roe', '--base', 'pl',
                                  '--g', '6', '--ke', '12', '--gde', '20', '--nde', '0', '--n', '10',
                                  '--tv', 'gordon', '--roe-tv', '15', '--gp', '3'],
             esperados=('identificacao_por_raiz',))
    # v9.30: iso bifásico trabalha em múltiplos por NI0; equity monetário sem NI0 é escala incompatível.
    rc, out, err = run(['iso', 'pe', '--alvo', '12', '--ke', '12', '--n', '10', '--tv', 'book',
                        '--transicao', 'ponte', '--pt-n1', '3', '--pt-ke1', '12', '--pt-gde1', '0',
                        '--pt-nde1', '0', '--pt-kd', '8', '--pt-tax', '30', '--pt-g1', '5',
                        '--pt-roe1', '20', '--pt-equity', '100'])
    check('CLI iso ponte: --pt-equity monetário é bloqueado',
          rc != 0 and 'misturar as escalas é inconsistente' in err,
          f'(rc={rc}, stderr={err[-180:]})')
    # NaN -> null: gp >= wacc gera NaN no motor; o JSON tem que continuar válido
    d = run_json('ev NaN vira null', ['ev', '--g', '5', '--roic', '8', '--wacc', '7', '--n', '10',
                                      '--da', '15', '--tax', '15', '--tv', 'gordon',
                                      '--roic-tv', '20', '--gp', '8'])
    check('CLI NaN: EV/NOPAT_curr é null', d.get('EV/NOPAT_curr', 'ausente') is None)
    # degrau: book sem média ALERTA; com --roe-book aceita e some o alerta; gordon segue limpo
    d = run_json('degrau book sem media', ['degrau', '--indice-atual', '19.3', '--indice-alvo', '13',
                 '--roe', '20', '--ke', '15', '--g', '8', '--n', '10', '--tv', 'book'],
                 esperados=('ALERTA_CONVENCAO_BOOK', 'diagnosticos'))
    d = run_json('degrau book com media', ['degrau', '--indice-atual', '19.3', '--indice-alvo', '13',
                 '--roe', '20', '--ke', '15', '--g', '8', '--n', '10', '--tv', 'book',
                 '--roe-book', '12'])
    check('degrau book com media: sem alerta', 'ALERTA_CONVENCAO_BOOK' not in d)
    d = run_json('degrau gordon', ['degrau', '--indice-atual', '19.3', '--indice-alvo', '16,13',
                 '--m', '100', '--anos', '4', '--perfil-transicao', 'rampa', '--roe', '20',
                 '--ke', '20', '--g', '12', '--n', '10', '--tv', 'gordon', '--roe-tv', '20',
                 '--gp', '6.5'], esperados=('classificacao', 'travas_obrigatorias'))
    check('degrau gordon: sem alerta book', 'ALERTA_CONVENCAO_BOOK' not in d)
    # degrau firm com book + --roic-book (simetria do lado firm)
    run_json('degrau firm book com media', ['degrau', '--indice-atual', '19.3', '--indice-alvo', '13',
             '--roic', '20', '--wacc', '9', '--g', '5', '--n', '10', '--tv', 'book',
             '--roic-book', '12'], esperados=('diagnosticos',))
    # demais subcomandos: JSON válido e chaves nucleares
    run_json('normaliza', ['normaliza', '--ebitda-base', '446', '--da', '130', '--preco-base', '5.00',
                           '--preco-novo', '6.26', '--rev-driver', '731', '--tax', '18.5',
                           '--tv', 'book'], esperados=('EBITDA_normalizado',))
    run_json('drivers', ['drivers', '--driver', 'ouro:4050:4550:auto:730.95:446.43',
                         '--driver', 'frete:100:130:auto:80:446.43:custo'],
             esperados=('efeito_liquido_total_%',))
    run_json('nivel', ['nivel', '--alvo-valor', '5824', '--multiplo', '5.60',
                       '--metrica-base', '931'], esperados=('degrau_implicito_%',))
    run_json('kewacc', ['kewacc', '--ku', '20', '--kd', '14.27', '--tax', '30', '--de', '46.15'],
             esperados=('WACC_%',))
    run_json('apv', ['apv', '--fcff1', '22.184', '--g', '11', '--n', '10', '--ku', '20',
                     '--kd', '14.2714285714286', '--tax', '30', '--d0', '35',
                     '--fcff-tv', '50.5317555785773', '--gtv', '0'],
             esperados=('check_FCFE_at_Ke_t_igual_E0',))
    # tabela: não é JSON — só exige returncode 0 e a grade impressa
    rc, out, _ = run(['tabela', 'ev', '--wacc', '7', '--da', '15', '--tax', '15', '--n', '10',
                      '--centro-roic', '8.5', '--centro-g', '5', '--tv', 'gordon',
                      '--roic-tv', '20', '--gp', '3'])
    check('CLI tabela: returncode 0 e grade', rc == 0 and 'EV/EBITDA justo' in out)
    # aliases legados via CLI
    run_json('alias ic->book', ['ev', '--g', '5', '--roic', '25', '--roic-book', '10', '--wacc', '7',
                                '--n', '10', '--da', '15', '--tax', '15', '--tv', 'ic'],
             esperados=('aviso_tv',))
    # ---- v8.5: C7 quantificado — campo do output vs recomputação INDEPENDENTE ----
    # M sob a convenção alternativa reconstruído do zero: explícito idêntico, TV com (1+g)^n(1+gp).
    def m_alt_ev(g, roic, w, n, roic_tv, gp):
        ret = 1 - g / roic
        s = sum(ret * (1 + g) ** t / (1 + w) ** t for t in range(1, n + 1))
        return s + (1 + g) ** n * (1 + gp) * (1 - gp / roic_tv) / (w - gp) / (1 + w) ** n
    from justos import ev_nopat as _ev, pe as _pe
    for gg, gpgp in ((5, 3), (8, 3), (12, 6.5), (5, 4.5)):
        d = run_json(f'C7 ev g{gg}/gp{gpgp}',
                     ['ev', '--g', str(gg), '--roic', '20', '--wacc', '10', '--n', '10',
                      '--da', '15', '--tax', '15', '--tv', 'gordon', '--roic-tv', '15',
                      '--gp', str(gpgp)], esperados=('efeito_c7_alternativa_gp_%',))
        m = _ev(gg / 100, 0.20, 0.10, 10, tv='gordon', roic_tv=0.15, gp=gpgp / 100)
        esp = (m_alt_ev(gg / 100, 0.20, 0.10, 10, 0.15, gpgp / 100) / m - 1) * 100
        obs = d.get('efeito_c7_alternativa_gp_%')
        check(f'C7 ev g{gg}/gp{gpgp}: campo = recomputação independente',
              obs is not None and abs(obs - esp) <= 0.006, f'(campo {obs} vs indep {esp:.4f})')
        check(f'C7 ev g{gg}/gp{gpgp}: sinal = sinal de (gp−g)',
              obs is not None and (obs < 0) == (gpgp < gg))
    # lado equity, com caixa e politica continua: recomputação via pe() com TV escalado
    d = run_json('C7 pe caixa continua', ['pe', '--g', '6', '--roe', '18', '--ke', '12', '--n', '10',
                 '--gde', '20', '--nde', '0', '--tv', 'gordon', '--roe-tv', '15', '--gp', '3'],
                 esperados=('efeito_c7_alternativa_gp_%',))
    m = _pe(0.06, 0.18, 0.12, 10, 0.20, 0.0, tv='gordon', roe_tv=0.15, gp=0.03)
    caixa = 0.20
    ret_tv = (1 - 0.03 / 0.15) + caixa * (0.03 / 0.15)
    tvt = 1.06 ** 11 * ret_tv / (0.12 - 0.03) / 1.12 ** 10
    esp = (tvt / m) * (1.03 / 1.06 - 1) * 100
    obs = d.get('efeito_c7_alternativa_gp_%')
    check('C7 pe: campo = recomputação independente',
          obs is not None and abs(obs - esp) <= 0.006, f'(campo {obs} vs indep {esp:.4f})')
    # ---- v8.5: faixa de busca declarada + região RiR > 100% sob flag ----
    d = run_json('rev sem flag: faixa declarada', ['rev', '--alvo', '30', '--resolver', 'g',
                 '--base', 'nopat', '--roic', '8', '--wacc', '7', '--tv', 'convergencia'],
                 esperados=('faixa_de_busca', 'RiR ≤ 100%', '--rir-externo'))
    check('rev sem flag: sem raiz no alvo 30', d.get('raizes_g_%') == [])
    d = run_json('rev com --rir-externo: raiz além do autofinanciável',
                 ['rev', '--alvo', '30', '--resolver', 'g', '--base', 'nopat', '--roic', '8',
                  '--wacc', '7', '--tv', 'convergencia', '--rir-externo'],
                 esperados=('ALERTA_RIR_EXTERNO', 'funding'))
    raizes = d.get('raizes_g_%', [])
    check('rev com flag: encontra raiz com g > ROIC (RiR > 100%)',
          any(x > 8.0 for x in raizes), f'(raízes {raizes})')
    check('rev com flag: faixa marcada como RiR LIVRE',
          'RiR LIVRE' in json.dumps(d, ensure_ascii=False))
    d = run_json('rev cap: faixa declarada', ['rev', '--alvo', '8', '--resolver', 'cap', '--g', '5',
                 '--roic', '15', '--wacc', '9', '--base', 'nopat', '--tv', 'book'],
                 esperados=('faixa_de_busca',))
    print('  v8.5: C7 quantificado (4 pares firm + equity/caixa, vs recomputação independente); '
          'faixa_de_busca declarada; --rir-externo abre RiR > 100% com alerta de funding')
    print('  CLI: 20+ execuções reais por subprocess — JSON válido, diagnósticos presentes, '
          'caso-crash da v8.3 coberto, degrau com trava de conflação')


def rec_ponte():
    """v9.30 — ponte de releveraging: (1) colapso com estrutura igual; (2) antissimetria;
    (3) CONTRAPROVA num bifásico `book` por dividendos + E terminal + evento de estrutura;
    (4) corte artificial de uma empresa idêntica não altera o valor."""
    from justos import ponte_releveraging
    import random
    # (1) colapso
    p0 = ponte_releveraging(n1=4, ke1=0.18, ke2=0.18, gde1=0.5, nde1=0.3, gde2=0.5, nde2=0.3,
                            kd=0.10, tax=0.30, g1=0.08, roe1=0.20)
    check('ponte: colapso identicamente zero com estrutura igual',
          p0['PV_ponte'] == 0.0 and p0['delta_estrutura'] == 0.0)
    # (2) antissimetria do fluxo (mesma E_pre; troca 1->2 vs 2->1 com razões recíprocas)
    pa = ponte_releveraging(n1=3, ke1=0.15, ke2=0.15, gde1=0.2, nde1=0.1, gde2=0.8, nde2=0.6,
                            kd=0.10, tax=0.30, g1=0.05, equity=100.0)
    pb = ponte_releveraging(n1=3, ke1=0.15, ke2=0.15, gde1=0.8, nde1=0.6, gde2=0.2, nde2=0.1,
                            kd=0.10, tax=0.30, g1=0.05, equity=100.0)
    check('ponte: sinais opostos ao inverter a direção da troca',
          pa['fluxo_ano_n1_mais_1'] > 0 > pb['fluxo_ano_n1_mais_1'])
    # (3) contraprova por soma explícita de FCFE (5 sorteios)
    random.seed(86)
    for i in range(5):
        ke = random.uniform(0.12, 0.24); g1 = random.uniform(0.02, 0.15); g2 = random.uniform(0.03, 0.14)
        r1 = random.uniform(0.12, 0.35); r2 = random.uniform(0.12, 0.45)
        gde1, nde1 = random.uniform(0.2, 1.2), random.uniform(0.0, 0.9)
        gde2, nde2 = random.uniform(0.1, 0.8), random.uniform(0.0, 0.6)
        nde1, nde2 = min(nde1, gde1), min(nde2, gde2)
        n1, n2 = random.randint(2, 6), random.randint(4, 10)
        kd, tax = random.uniform(0.06, 0.14), 0.30
        razao = (1 + nde1) / (1 + nde2)
        # soma explícita `book`: dividendos + evento de estrutura + dividendos + E terminal.
        pv = sum((1 + g1) ** t * (1 - g1 / r1) / (1 + ke) ** t for t in range(1, n1 + 1))
        e_pre = (1 + g1) ** (n1 + 1) / r1
        pv += e_pre * (gde2 * razao - gde1) * (1 + kd * (1 - tax)) / (1 + ke) ** (n1 + 1)
        base2 = (1 + g1) ** (n1 + 1) * (r2 / r1) * razao
        pv += sum(base2 * (1 + g2) ** (s - 1) * (1 - g2 / r2) / (1 + ke) ** (n1 + s)
                  for s in range(1, n2 + 1))
        e_fim = e_pre * razao * (1 + g2) ** n2
        pv += e_fim / (1 + ke) ** (n1 + n2)
        # composição: anuidade f1 + ponte (motor) + bloco f2 + TV — sem o evento explícito
        pv_f1 = sum((1 + g1) ** t * (1 - g1 / r1) / (1 + ke) ** t for t in range(1, n1 + 1))
        pt = ponte_releveraging(n1=n1, ke1=ke, ke2=ke, gde1=gde1, nde1=nde1, gde2=gde2, nde2=nde2,
                                kd=kd, tax=tax, g1=g1, roe1=r1)['PV_ponte']
        pv_f2 = sum(base2 * (1 + g2) ** (s - 1) * (1 - g2 / r2) / (1 + ke) ** (n1 + s)
                    for s in range(1, n2 + 1)) + e_fim / (1 + ke) ** (n1 + n2)
        check(f'ponte: contraprova por soma explícita (sorteio {i + 1})',
              abs((pv_f1 + pt + pv_f2) - pv) < 1e-10,
              f'explicito={pv:.10f} composto={pv_f1 + pt + pv_f2:.10f}')
    # (4) degenerado: bifásico com estrutura igual == pe() monofásico da skill
    from justos import pe as pe_skill
    g, roe, ke, gde, nde, n = 0.11, 0.4483, 0.22, 0.5385, 0.4615, 10
    for n1 in (2, 5, 8):
        pv = sum((1 + g) ** t * (1 - g / roe) / (1 + ke) ** t for t in range(1, n + 1))
        pv += (1 + g) ** (n + 1) / roe / (1 + ke) ** n
        check(f'ponte: bifásico degenerado (corte em n1={n1}) == pe --tv book',
              abs(pv - pe_skill(g, roe, ke, n, gde, nde, tv='book')) < 1e-9)
    print('  v9: ponte de releveraging — colapso, antissimetria, contraprova explícita '
          '(5 sorteios), degenerado == pe')


def rec_iso():
    """v9.1 — curva iso-valor: todo par devolvido re-avalia ao alvo no motor (a curva se
    autovalida contra o pe/ev já validados), nas três convenções; anchors da vF8.1."""
    from justos import iso_curva, pe as pe_m, ev_nopat as ev_m
    import random
    random.seed(91)
    # (1) autovalidação: pares 'ok' re-avaliam ao alvo (book fechado + convergencia/gordon solver)
    casos = 0
    for _ in range(12):
        lado = random.choice(['pe', 'ev'])
        tv = random.choice(['book', 'convergencia', 'gordon'])
        K = random.uniform(0.08, 0.24); n = random.randint(5, 15)
        gde, nde = (random.uniform(0.1, 0.9), random.uniform(0.0, 0.6)) if lado == 'pe' else (0.0, 0.0)
        nde = min(nde, gde)
        rtv = random.uniform(K, K + 0.10) if tv == 'gordon' else None
        gp = random.uniform(0.0, min(0.04, K - 0.01)) if tv == 'gordon' else 0.0
        alvo = random.uniform(4.0, 14.0)
        grade = [random.uniform(0.0, K * 0.9) for _ in range(4)]
        out = iso_curva(lado, alvo, K, n, grade, tv=tv, gde=gde, nde=nde, rent_tv=rtv, gp=gp)
        for p in out['curva']:
            if p.get('rent_implicita_pct') is None: continue
            r = p['rent_implicita_pct'] / 100
            if r <= 0 or p.get('check_multiplo') is None: continue  # fora do domínio: sem re-avaliação
            m = pe_m(p['g_%'] / 100, r, K, n, gde, nde, tv=tv, roe_tv=rtv, gp=gp) if lado == 'pe' \
                else ev_m(p['g_%'] / 100, r, K, n, tv=tv, roic_tv=rtv, gp=gp)
            check(f'iso: par ({lado},{tv}) re-avalia ao alvo', abs(m - alvo) < 1e-5,
                  f'g={p["g_%"]}% rent={r:.4%} M={m:.6f} alvo={alvo:.6f}')
            casos += 1
    check('iso: amostra de autovalidação não-trivial', casos >= 20, f'{casos} pares')
    # (2) anchors: enterprise vF8.1 + equity book corrigido por clean surplus na v9.30
    a1 = iso_curva('pe', 5.617294815452462, 0.22, 10, [0.11], tv='book',
                   gde=0.538461538461538, nde=0.461538461538462)['curva'][0]
    a2 = iso_curva('ev', 6.429566333754988, 0.187331578947369, 10, [0.11], tv='book')['curva'][0]
    check('iso: anchor P/L book v9.30 (ROE* preservado)',
          abs(a1['rent_implicita_pct'] - 44.8269230769231) < 1e-7)
    check('iso: anchor EV vF8.1 (ROIC* = ROIC da Logic)',
          abs(a2['rent_implicita_pct'] - 34.3515789473684) < 1e-7)
    # (3) diagnósticos: book abaixo do custo e neutralidade sinalizados
    d = iso_curva('pe', 5.6173, 0.22, 10, [0.0], tv='book',
                  gde=0.538461538461538, nde=0.461538461538462)['curva'][0]
    check('iso: trava book (marginal < custo, SEM book informado) dispara no ramo baixo',
          'conflação' in d['diagnostico'])
    print('  v9.1: iso-valor — autovalidação em 3 convenções (%d pares), anchors vF8.1, travas' % casos)


def rec_correcoes():
    """v9.2 — correções da auditoria: B1 (inversão com papéis separados), R1 (validação do rev),
    R2 (ponte roe1-book), R3/R4 (diagnósticos), composição iso↔ponte."""
    from justos import iso_curva, pe as pe_m, ponte_releveraging
    import random, subprocess, json, os
    _J = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'justos.py')
    random.seed(92)
    # (B1) recuperação do marginal com rent_book, marginal != book, 8 sorteios
    for i in range(8):
        K = random.uniform(0.10, 0.24); n = random.randint(5, 15); g = random.uniform(0.02, K * 0.85)
        gde, nde = random.uniform(0.1, 0.9), random.uniform(0.0, 0.6); nde = min(nde, gde)
        rm = random.uniform(0.12, 0.50); rb = rm * random.uniform(0.5, 1.6)
        alvo = pe_m(g, rm, K, n, gde, nde, tv='book', roe_book=rb)
        out = iso_curva('pe', alvo, K, n, [g], tv='book', gde=gde, nde=nde, rent_book=rb)
        p = out['curva'][0]
        check(f'B1: iso recupera o marginal com rent-book (sorteio {i+1})',
              p.get('rent_implicita_pct') is not None and abs(p['rent_implicita_pct']/100 - rm) < 1e-7
              and p['check_multiplo'] == 0.0,
              f'g={g:.2%} rm={rm:.2%} rb={rb:.2%} -> {p.get("rent_implicita_pct")}')
    # (B1) sem rent_book: aviso de conflação presente
    out = iso_curva('pe', 6.0, 0.18, 10, [0.08], tv='book', gde=0.3, nde=0.2)
    check('B1: aviso de conflação sem rent-book', any('conflação' in a for a in out.get('avisos', [])))
    # (R2 v9.30) ponte: as duas rotas coincidem quando ancoram o MESMO E_pre. Com book separado,
    # E0 não cresce simplesmente a g: E_pre incorpora a retenção ao ROE marginal.
    g1, rb1 = 0.07, 0.19
    pa = ponte_releveraging(n1=4, ke1=0.18, ke2=0.15, gde1=1.0, nde1=0.7, gde2=0.4, nde2=0.3,
                            kd=0.12, tax=0.34, g1=g1, roe1=0.31, roe1_book=rb1)
    e0_equiv = pa['E_pre_transicao'] / (1 + g1) ** 4
    pb = ponte_releveraging(n1=4, ke1=0.18, ke2=0.15, gde1=1.0, nde1=0.7, gde2=0.4, nde2=0.3,
                            kd=0.12, tax=0.34, g1=g1, equity=e0_equiv)
    check('R2: ponte roe1-book ≡ base-equity quando E_pre é o mesmo',
          abs(pa['PV_ponte'] - pb['PV_ponte']) < 1e-12)
    pc_ = ponte_releveraging(n1=4, ke1=0.18, ke2=0.15, gde1=1.0, nde1=0.7, gde2=0.4, nde2=0.3,
                             kd=0.12, tax=0.34, g1=g1, roe1=0.31)
    check('R2: aviso de conflação sem roe1-book', any('conflação' in d for d in pc_['diagnosticos']))
    # (R1) rev: combinações inconsistentes falham com mensagem, nunca rota silenciosa
    r = subprocess.run([sys.executable, _J, 'rev', '--alvo', '8', '--resolver', 'roe',
                        '--g', '8', '--wacc', '15', '--roic', '20', '--n', '10',
                        '--tv', 'convergencia'], capture_output=True, text=True,
                       encoding='utf-8')
    check('R1: resolver roe no lado firm é bloqueado com explicação',
          r.returncode != 0 and 'EQUITY' in (r.stderr + r.stdout))
    r = subprocess.run([sys.executable, _J, 'rev', '--alvo', '8', '--resolver', 'roic',
                        '--g', '8', '--ke', '15', '--roe', '20', '--n', '10',
                        '--tv', 'convergencia', '--base', 'pl'], capture_output=True, text=True,
                       encoding='utf-8')
    check('R1: resolver roic no lado equity é bloqueado', r.returncode != 0)
    r = subprocess.run([sys.executable, _J, 'rev', '--alvo', '8', '--resolver', 'roe',
                        '--g', '8', '--ke', '15', '--n', '10', '--gde', '40', '--nde', '30',
                        '--tv', 'convergencia', '--base', 'pl'], capture_output=True, text=True,
                       encoding='utf-8')
    d = json.loads(r.stdout)
    check('R1: uso correto segue funcionando e carrega a nota de regime único',
          r.returncode == 0 and 'premissa_regime' in d)
    # (v9.2) iso: --transicao obrigatória no CLI; composição fecha a identidade
    r = subprocess.run([sys.executable, _J, 'iso', 'pe', '--alvo', '6', '--ke', '18',
                        '--n', '10', '--tv', 'book'], capture_output=True, text=True,
                       encoding='utf-8')
    check('v9.2: iso sem --transicao falha (argparse required)', r.returncode != 0)
    r = subprocess.run([sys.executable, _J, 'iso', 'pe', '--alvo', '10', '--ke', '16',
                        '--n', '12', '--tv', 'book', '--transicao', 'ponte', '--rent-book', '10',
                        '--pt-n1', '5', '--pt-ke1', '22', '--pt-gde1', '80', '--pt-nde1', '60',
                        '--pt-kd', '11', '--pt-tax', '30', '--pt-g1', '12', '--pt-roe1', '10.85'],
                       capture_output=True, text=True, encoding='utf-8')
    check('v9.31: --rent-book é rejeitado na ponte em vez de ser ignorado',
          r.returncode != 0 and '--rent-book' in (r.stderr + r.stdout) and 'rejeitado' in (r.stderr + r.stdout))
    out = iso_curva('pe', 10.0, 0.16, 12, [0.15], tv='book', gde=0.3, nde=0.2,
                    transicao='ponte',
                    ponte_params=dict(n1=5, ke1=0.22, gde1=0.8, nde1=0.6, kd=0.11,
                                      tax=0.30, g1=0.12, roe1=0.10846315789473689))
    ct = out['composicao_transicao']
    check('v9.31: composição explicita inversão fechada condicional', 'FECHADA E CONDICIONAL' in ct['composicao'] and 'não é identificação estrutural pura' in ct['composicao'])
    # (R3/R4) diagnósticos novos no pe
    r = subprocess.run([sys.executable, _J, 'pe', '--g', '5', '--roe', '20', '--ke', '15',
                        '--n', '10', '--gde', '30', '--nde', '20', '--tv', 'gordon',
                        '--roe-tv', '20', '--gp', '14.9'], capture_output=True, text=True,
                       encoding='utf-8')
    check('R3: alerta de sensibilidade Ke−gp', 'SENSIBILIDADE' in r.stdout)
    r = subprocess.run([sys.executable, _J, 'pe', '--g', '8', '--roe', '25', '--ke', '15',
                        '--n', '10', '--gde', '20', '--nde', '50', '--tv', 'book'],
                       capture_output=True, text=True, encoding='utf-8')
    check('R4: trava de domínio caixa/E negativo', 'DOMÍNIO' in r.stdout)
    print('  v9.2: correções da auditoria — B1 (8 sorteios), R1, R2, R3, R4, composição')


def rec_inversao_bifasica():
    """[v9.30] Inversão bifásica contra reconstrução DDM/clean-surplus independente.

    O teste carrega DOIS estados entre fases: patrimônio acumulado e nível de lucro. Inclui
    ROE_book separado na fase 1 para impedir regressão ao book congelado.
    """
    from justos import iso_curva
    import random
    random.seed(93)

    def verdade_explicita(g1, r1, rb1, ke1, n1, gde1, nde1,
                          g2, r2, ke2, n2, gde2, nde2, kd, tax):
        razao = (1 + nde1) / (1 + nde2)
        E = (1 + g1) / rb1
        pv = 0.0
        # fase 1: dividendos + clean surplus
        for t in range(1, n1 + 1):
            ni_t = (1 + g1) ** t
            dE = (g1 / r1) * ni_t
            div = ni_t - dE
            pv += div / (1 + ke1) ** t
            E += dE
        e_pre = E
        # evento de estrutura no ano n1+1
        pv += (e_pre * (gde2 * razao - gde1) * (1 + kd * (1 - tax))
               / ((1 + ke1) ** n1 * (1 + ke2)))
        # semântica histórica do rebase: NI2_1 = NI1_{n1+1}·(ROE2/ROE1)·razao
        ni2_1 = (1 + g1) ** (n1 + 1) * (r2 / r1) * razao
        E2 = e_pre * razao
        for t in range(1, n2 + 1):
            ni_t = ni2_1 * (1 + g2) ** (t - 1)
            dE = (g2 / r2) * ni_t
            div = ni_t - dE
            pv += div / ((1 + ke1) ** n1 * (1 + ke2) ** t)
            E2 += dE
        pv += E2 / ((1 + ke1) ** n1 * (1 + ke2) ** n2)
        return pv

    # anchor histórico com book=marginal: continua recuperando ROE2.
    alvo = verdade_explicita(0.12, 0.1085, 0.1085, 0.22, 5, 0.8, 0.6,
                             0.15, 0.4345, 0.16, 12, 0.3, 0.2, 0.11, 0.30)
    out = iso_curva('pe', alvo, 0.16, 12, [0.15], tv='book', gde=0.3, nde=0.2,
                    transicao='ponte',
                    ponte_params=dict(n1=5, ke1=0.22, gde1=0.8, nde1=0.6, kd=0.11,
                                      tax=0.30, g1=0.12, roe1=0.1085))
    p0 = out['curva'][0]
    check('B2/v9.30: anchor recupera ROE2 = 43.45% exato',
          abs(p0['rent_implicita_pct'] / 100 - 0.4345) < 1e-9 and p0['check_multiplo'] == 0.0,
          f"devolvido: {p0.get('rent_implicita_pct')}")

    # empresas sorteadas, metade com book inicial separado.
    for i in range(16):
        ke1 = random.uniform(0.12, 0.26); ke2 = random.uniform(0.10, 0.22)
        g1 = random.uniform(0.0, 0.15); g2 = random.uniform(0.02, min(0.16, ke2 * 0.9))
        r1 = random.uniform(0.08, 0.40); r2 = random.uniform(max(ke2, 0.12), 0.55)
        rb1 = r1 if i < 8 else random.uniform(0.07, 0.35)
        gde1, nde1 = random.uniform(0.2, 1.2), random.uniform(0.0, 0.9); nde1 = min(nde1, gde1)
        gde2, nde2 = random.uniform(0.1, 0.8), random.uniform(0.0, 0.6); nde2 = min(nde2, gde2)
        n1, n2 = random.randint(2, 7), random.randint(4, 14)
        kd, tax = random.uniform(0.06, 0.14), 0.30
        alvo = verdade_explicita(g1, r1, rb1, ke1, n1, gde1, nde1,
                                 g2, r2, ke2, n2, gde2, nde2, kd, tax)
        out = iso_curva('pe', alvo, ke2, n2, [g2], tv='book', gde=gde2, nde=nde2,
                        transicao='ponte',
                        ponte_params=dict(n1=n1, ke1=ke1, gde1=gde1, nde1=nde1, kd=kd,
                                          tax=tax, g1=g1, roe1=r1, roe1_book=rb1))
        p = out['curva'][0]
        check(f'B2/v9.30: inversão recupera ROE2 sorteado ({i + 1})',
              p.get('rent_implicita_pct') is not None
              and abs(p['rent_implicita_pct'] / 100 - r2) < 1e-7
              and p['check_multiplo'] == 0.0,
              f'r2={r2:.4%} rb1={rb1:.4%} devolvido={p.get("rent_implicita_pct")}')
    print('  v9.30: inversão bifásica — DDM/clean-surplus explícito, inclusive book inicial separado')


def rec_guardas_damodaran():
    """v9.4 — as duas guardas (opcionais, aviso na ausência): âncora macro do gp e moeda/regime."""
    import subprocess, os, json
    _J = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'justos.py')
    def run(args):
        r = subprocess.run([sys.executable, _J] + args, capture_output=True, text=True,
                           encoding='utf-8')
        return r.stdout
    base = ['pe', '--g', '6', '--roe', '20', '--ke', '12', '--n', '10',
            '--tv', 'gordon', '--roe-tv', '18']
    check('G1: gp > rf dispara alerta quantificado',
          'EXCEDE o teto' in run(base + ['--gp', '8.5', '--rf', '6', '--moeda', 'BRL-nominal']))
    check('G1: gp <= rf registra âncora OK',
          'ÂNCORA MACRO OK' in run(base + ['--gp', '4', '--rf', '6', '--moeda', 'BRL-nominal']))
    check('G1: sem --rf, premissa não ancorada',
          'NÃO ANCORADA' in run(base + ['--gp', '4']))
    check('G1: regime real usa teto de 3% mesmo com rf alto',
          'teto de 3.00%' in run(base + ['--gp', '4', '--rf', '10', '--moeda', 'BRL-real']))
    check('G2: sem --moeda, aviso de não declaração',
          'NÃO DECLARADOS' in run(base + ['--gp', '4', '--rf', '6']))
    out = json.loads(run(base + ['--gp', '4', '--rf', '6', '--moeda', 'USD-nominal']))
    check('G2: moeda declarada ecoa como convenção e silencia o aviso',
          out.get('convencao_moeda') == 'USD-nominal'
          and not any('NÃO DECLARADOS' in x for x in out['diagnosticos']))
    check('regressão: book sem gordon não ganha ruído de gp',
          'gp' not in ' '.join(x for x in json.loads(run(['pe', '--g', '6', '--roe', '20',
          '--ke', '12', '--n', '10', '--tv', 'book', '--moeda', 'BRL-nominal']))['diagnosticos']
          if 'ncora' in x or 'ANCORADA' in x) if True else False)
    # v9.5: guarda ligada na tabela (era flag morta) — travar contra regressão, nos dois rótulos
    out_t = run(['tabela', 'pe', '--ke', '16', '--gde', '30', '--nde', '20', '--n', '10',
                 '--centro-roe', '25', '--centro-g', '8', '--tv', 'gordon', '--roe-tv', '20',
                 '--gp', '5'])
    check('G1-tabela: gordon com gp e sem --rf emite PREMISSA NÃO ANCORADA',
          'NÃO ANCORADA' in out_t)
    out_t = run(['tabela', 'ev', '--wacc', '12', '--da', '15', '--tax', '30', '--n', '10',
                 '--centro-roic', '20', '--centro-g', '5', '--tv', 'gordon', '--roic-tv', '18',
                 '--gp', '4', '--rf', '6'])
    check('G2-tabela: lado firm rotula o custo como WACC na guarda de moeda',
          'WACC' in out_t and 'g, gp e Ke' not in out_t)
    print('  v9.4/9.5: guardas Damodaran — 4 comportamentos G1, eco/aviso G2, tabela travada, '
          'regressão book')




def rec_rampa_v924():
    """[v9.24] Suíte da composição bifásica (§8f) — as cinco provas da planilha ELMT ago/26,
    reconstruídas de forma INDEPENDENTE (o teste não usa a forma fechada do motor: monta as
    linhas do 3DF ano a ano e desconta), mais colheita, conservação e unit economics."""
    from justos import rampa_bifasica, ev_nopat, conservacao_capital, validacao_unit_economics
    R0, E0, DA, WK, W, TAX, N, T = 265.0, 26.8, 6.8, 0.191, 0.119, 0.35, 10, 5
    G2, KAP, UTIL = 0.08, 0.179364, 0.65
    rp = rampa_bifasica(R0, E0, DA, WK, W, TAX, N, T, G2, KAP, util=UTIL, tv='convergencia')
    m = E0 / R0
    g1 = (1 / UTIL) ** (1 / T) - 1
    # ---- reconstrução independente, linha a linha (o "3DF" do teste) ----
    rev = [R0]
    for t in range(1, N + 1):
        rev.append(rev[-1] * (1 + (g1 if t <= T else G2)))
    ebT = m * rev[T]; d2 = DA / ebT
    fcff = []
    for t in range(1, N + 1):
        eb = m * rev[t]
        if t <= T:
            nop = (eb - DA) * (1 - TAX)
            fcff.append(nop - WK * (rev[t] - rev[t - 1]))          # capex manut = D&A cancela
        else:
            nop = eb * (1 - d2) * (1 - TAX)
            fcff.append(nop - (WK + KAP) * (rev[t] - rev[t - 1]))  # giro + capex de expansão
    nopat11 = m * (1 - d2) * (1 - TAX) * rev[N] * (1 + G2)
    ev_indep = sum(f / (1 + W) ** t for t, f in enumerate(fcff, 1)) + (nopat11 / W) / (1 + W) ** N
    check('P2 rampa: EV do motor = reconstrução 3DF independente',
          abs(rp['EV'] - ev_indep) < 1e-4, f"{rp['EV']} vs {ev_indep:.4f}")
    # ---- P1: fluxo a fluxo da fase 1 contra alfa/beta (recalculados no teste) ----
    alfa = (1 - TAX) * E0 - WK * g1 * R0 / (1 + g1)
    beta = -(1 - TAX) * DA
    p1 = max(abs(fcff[t - 1] - (alfa * (1 + g1) ** t + beta)) for t in range(1, T + 1))
    check('P1 rampa: FCFF da fase 1 = alfa(1+g1)^t + beta', p1 < 1e-9, f'max dif {p1:.2e}')
    # ---- P3: fase 2 isolada = ev_nopat sobre a base do ano T ----
    m2n = m * (1 - d2) * (1 - TAX)
    rir2 = (WK + KAP) * G2 / ((1 + G2) * m2n)
    ev_T = ev_nopat(G2, G2 / rir2, W, N - T, tv='convergencia') * ebT * (1 - d2) * (1 - TAX)
    check('P3 rampa: valor da fase 2 no ano T = ev do motor sobre a base T',
          abs(rp['valor_fase2_no_ano_T'] - ev_T) < 1e-4, f"{rp['valor_fase2_no_ano_T']} vs {ev_T:.4f}")
    # ---- P4: a rampa aterrissa exatamente na capacidade ----
    check('P4 rampa: Receita_T = capacidade (por construção da anualização)',
          abs(rev[T] - R0 / UTIL) < 1e-8, f'{rev[T]:.6f} vs {R0 / UTIL:.6f}')
    # ---- P5: anchor da planilha (proveniência ELMT ago/26) ----
    check('P5 rampa: EV = planilha bifásica (170.93 ± 0.02)', abs(rp['EV'] - 170.93) < 0.02)
    check('P5 rampa: US$/ação com a ponte da planilha (9.0447 ± 0.005)',
          abs((rp['EV'] + 104.567) / 30.4595 - 9.0447) < 0.005)
    check('P5 rampa: d re-basa 25.4% → 16.5% (o que a rodada única congela)',
          abs(rp['d2_fase2_%'] - 16.493) < 0.01)
    # ---- colheita: g1 < 0 libera giro ⟹ FCFF > NOPAT na fase 1 ----
    rc = rampa_bifasica(R0, E0, DA, WK, W, TAX, N, T, G2, KAP, g1=-0.05, tv='convergencia')
    nop1 = (m * R0 * 0.95 - DA) * (1 - TAX)
    fcff1_c = nop1 - WK * (R0 * 0.95 - R0)
    check('colheita: g1<0 ⟹ FCFF > NOPAT (liberação de giro)', fcff1_c > nop1)
    check('colheita: bloco rotulado', 'colheita' in rc['bloco'])
    # ---- delator por componente: RiR2 >= 100% avisa ----
    rd = rampa_bifasica(R0, E0, DA, 0.60, W, TAX, N, T, 0.20, 0.40, util=UTIL, tv='convergencia')
    check('delator fase 2: RiR2 >= 100% ⟹ aviso de funding', 'aviso_delator' in rd)
    # ---- conservação de capital (§11.1b executável) ----
    cc = conservacao_capital(10.0, 4.05, 26.8, 0.254, 0.35, 0.08, 0.143)
    check('conservação: par coerente fecha (<10%)', 'leitura' in cc and abs(cc['gap_%']) < 10)
    cq = conservacao_capital(20.0, 4.05, 26.8, 0.254, 0.35, 0.08, 0.143)
    check('conservação: par quebrado dispara o alerta (>10%)', 'ALERTA' in cq)
    # ---- unit economics: identidade no ramo capacidade (só giro) ----
    # convenção fim-de-período do motor: RiR_wk = wk·g/((1+g)·m_nop) ⟹ g/RiR_wk = (1+g)·margem×giro;
    # na convenção início-de-período (deployment_t / NOPAT_{t-1}), colapsa em margem×giro puro.
    m_nop = m * (1 - 0.254) * (1 - TAX)                    # margem NOPAT do caso-base
    rir_wk = WK * 0.08 / ((1 + 0.08) * m_nop)
    check('unit economics: g/RiR_wk = (1+g)·margem×giro (identidade §11.2, convenção declarada)',
          abs(0.08 / rir_wk - (1 + 0.08) * m_nop / WK) < 1e-12)
    vu = validacao_unit_economics(0.257, 0.143)
    check('unit economics: divergência > limiar declarada', 'DIVERGENCIA_DECLARADA' in vu)
    vc = validacao_unit_economics(0.144, 0.143)
    check('unit economics: dentro do limiar não dispara', 'leitura' in vc)

def rec_v915():
    """[v9.15] D-1 retenção não-informativa; D-2 confronto temporal do nivel."""
    from justos import diag_eq, nivel_implicito
    # D-1: payout ~0 dispara o aviso; payout relevante não dispara
    d100 = diag_eq(0.20, 0.20, 0.13, 0.0, 0.0, tv='gordon', roe_tv=0.20, gp=0.04)
    check('v9.15 D-1: retenção 100% ⟹ aviso de RiR observado não-informativo',
          any('NÃO-INFORMATIVA' in x for x in d100))
    d50 = diag_eq(0.10, 0.20, 0.13, 0.0, 0.0, tv='gordon', roe_tv=0.20, gp=0.04)
    check('v9.15 D-1: retenção 50% ⟹ sem aviso (payout informativo)',
          not any('NÃO-INFORMATIVA' in x for x in d50))
    # D-2: leitura antecipação temporal vs acima do consenso
    r1 = nivel_implicito(92270, 19.456, 1863, consenso_t2=4084)
    check('v9.15 D-2: implícita ≈ consenso t+2 ⟹ antecipacao_temporal',
          r1.get('leitura', '').startswith('antecipacao_temporal'),
          f"(implícita {r1['metrica_base_implicita']}, razão {r1.get('razao_vs_consenso_t2')})")
    r2 = nivel_implicito(92270, 19.456, 1863, consenso_t2=2500)
    check('v9.15 D-2: implícita ≫ consenso ⟹ acima_do_consenso',
          r2.get('leitura', '').startswith('acima_do_consenso'))
    r3 = nivel_implicito(92270, 19.456, 1863)
    check('v9.15 D-2: sem consenso ⟹ output idêntico ao legado (sem leitura)',
          'leitura' not in r3 and r3['fator_k_implicito'] == 2.5456)
    print('  v9.15: retenção não-informativa (D-1) e confronto temporal do nivel (D-2)')

def rec_v928_hardening():
    """[v9.28] Regressões adversariais derivadas da diligência da v9.27."""
    import subprocess, json, os
    from justos import (coerencia_vetor, rampa_bifasica, desconto_transicao,
                        avaliar_dominios_cli, registro_drivers)

    # 1) Fisher: rota real e nominal integrais devem ser idênticas; terminal-only não é a identidade.
    kn, pi, n = 0.10, 0.03, 10
    kr = (1 + kn) / (1 + pi) - 1
    vp_real = sum(1 / (1 + kr) ** t for t in range(1, n + 1))
    vp_nom = sum((1 + pi) ** t / (1 + kn) ** t for t in range(1, n + 1))
    check('v9.28 Fisher: real exato = nominal exato', abs(vp_real - vp_nom) < 1e-12,
          f'({vp_real} vs {vp_nom})')
    # Contraprova da antiga rota terminal-only: fluxo real perpétuo unitário, 10 anos explícitos.
    v_exato = 1 / kr
    v_terminal_only = (sum(1 / (1 + kn) ** t for t in range(1, n + 1))
                       + ((1 + pi) / (kn - pi)) / ((1 + kn) ** n))
    check('v9.28 Fisher: terminal-only NÃO é Fisher equivalente',
          abs(v_terminal_only / v_exato - 1) > 0.15,
          f'({v_terminal_only:.6f} vs {v_exato:.6f})')

    # 2) Caixa remunerado: o exemplo da diligência fecha a 16,95% somente com Kcash.
    args = dict(roic=0.15, roe=0.1695, gde=0.50, nde=0.30, kd=0.10, tax=0.25)
    dc, _ = coerencia_vetor(**args, cash_yield=0.08)
    check('v9.28 caixa: identidade fecha com cash-yield',
          not any('INCOERÊNCIA' in x for x in dc), f'({dc})')
    d0, _ = coerencia_vetor(**args)
    check('v9.28 caixa: sem cash-yield há aviso específico',
          any('CAIXA REMUNERADO' in x for x in d0))
    check('v9.28 caixa: sem cash-yield o gap de 1,20 p.p. é detectado',
          any('INCOERÊNCIA' in x for x in d0))

    # 3) CAP longo: g>=W não fecha; com book separado e g<W o caminho pode não ser monotônico.
    def gap(N, g, r, w, rb=None):
        return abs(ev_nopat(g, r, w, N, tv='convergencia') -
                   ev_nopat(g, r, w, N, tv='book', roic_book=rb))
    check('v9.28 CAP: g>=W pode ampliar gap com n',
          gap(100, 0.15, 0.25, 0.10) > gap(10, 0.15, 0.25, 0.10))
    seq = [gap(N, 0.0631, 0.2846, 0.0721, 0.1714) for N in (1,5,10,20,50,100)]
    check('v9.28 CAP: book separado pode abrir antes de fechar',
          seq[2] > seq[0] and seq[-1] < seq[2], f'({seq})')

    # 4) Domínio: hard vs abnormal.
    er, av = avaliar_dominios_cli({'g': -150, 'wacc': 10, 'n': 10, 'tax': 150, 'da': 120})
    check('v9.28 domínio: g<=-100 hard error', any('--g' in x for x in er))
    check('v9.28 domínio: tax/d anômalos são warnings', len(av) == 2)
    check('v9.28 núcleo: g<-100 retorna NaN', ev_nopat(-1.5, 0.2, 0.1, 10, tv='book') != ev_nopat(-1.5, 0.2, 0.1, 10, tv='book'))

    # 5) Solver: raiz sobre grid não duplica.
    rr = solve(lambda x: x*x - 0.25, -1.0, 1.0, steps=4)
    check('v9.28 solver: grid roots deduplicadas', len(rr) == 2 and abs(rr[0]+0.5)<1e-8 and abs(rr[1]-0.5)<1e-8, f'({rr})')

    # 6) Rampa: g2=0 é válido; WACC=0 não divide por zero.
    rz = rampa_bifasica(265, 26.8, 6.8, 0.191, 0.119, 0.35, 10, 5, 0.0, 0.179364,
                        util=0.65, tv='convergencia')
    check('v9.28 rampa: g2=0 definido', rz['EV'] == rz['EV'] and rz['roic2_%'] is not None, f'({rz})')
    rw0 = rampa_bifasica(265, 26.8, 6.8, 0.191, 0.0, 0.35, 10, 5, 0.08, 0.179364,
                         util=0.65, tv='book')
    check('v9.28 rampa: WACC=0 sem divisão por zero', rw0['EV'] == rw0['EV'])

    # 7) Deployment fracionário: continuidade em torno de 1,5 ano e fórmula da tranche parcial.
    f149 = desconto_transicao(0.10, 1.499, 'rampa')
    f151 = desconto_transicao(0.10, 1.501, 'rampa')
    f15 = desconto_transicao(0.10, 1.5, 'rampa')
    esperado = ((1/1.1) + 0.5/(1.1**1.5)) / 1.5
    check('v9.28 deployment: T=1.5 usa tranche proporcional', abs(f15-esperado)<1e-12)
    check('v9.28 deployment: sem salto artificial em 1.5', abs(f149-f151) < 0.002, f'({f149},{f151})')

    # 8) APV C7 explícita e quantificada.
    ap = apv_recursao(22.184, 0.11, 10, 0.20, 0.142714285714286, 0.30, 35.0, gtv=0.0, conv='mm')
    for campo in ('FCFF_n','FCFF_n1_usado_no_TV','g_transicao_%','gtv_%','efeito_C7_alternativa_gtv_em_n1_%'):
        check(f'v9.28 APV C7: {campo} ecoado', campo in ap)
    check('v9.28 APV C7: alternativa é não-neutra quando g!=gtv', abs(ap['efeito_C7_alternativa_gtv_em_n1_%']) > 0.1)

    # 9) Gate de drivers decide com valor bruto, não display arredondado.
    gt = registro_drivers([{'nome':'x','base':100.0,'spot':110.004,'elast':1.0}], limiar=0.10)
    gf = registro_drivers([{'nome':'x','base':100.0,'spot':109.996,'elast':1.0}], limiar=0.10)
    check('v9.28 drivers: 10.004% dispara mesmo exibindo 10.00%', gt['GATE'])
    check('v9.28 drivers: 9.996% não dispara mesmo exibindo 10.00%', not gf['GATE'])

    # 10) CLI: hard error não pode sair como sucesso; warnings anômalos devem atravessar o JSON.
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'justos.py')
    bad = subprocess.run([sys.executable, script, 'ev', '--g','-150','--roic','20','--wacc','10','--da','10','--tax','30','--tv','book'],
                         capture_output=True, text=True, encoding='utf-8')
    check('v9.28 CLI: hard domain sai !=0', bad.returncode != 0 and 'domínio matemático inválido' in bad.stdout)
    warn = subprocess.run([sys.executable, script, 'ev', '--g','5','--roic','20','--wacc','10','--da','120','--tax','150','--tv','book'],
                          capture_output=True, text=True, encoding='utf-8')
    jd = json.loads(warn.stdout)
    check('v9.28 CLI: abnormal regime permanece executável', warn.returncode == 0)
    check('v9.28 CLI: abnormal warnings ecoados', len(jd.get('avisos_dominio',[])) == 2)
    cash = subprocess.run([sys.executable, script, 'pe', '--g','5','--roe','16.95','--ke','12',
                           '--gde','50','--nde','30','--roic','15','--kd','10','--tax','25',
                           '--cash-yield','8','--tv','convergencia'],
                          capture_output=True, text=True, encoding='utf-8')
    jc = json.loads(cash.stdout)
    check('v9.28 CLI: --cash-yield atravessa o parser', cash.returncode == 0)
    check('v9.28 CLI: cash-yield fecha o Gate ROE sem falsa incoerência',
          not any('INCOERÊNCIA ROE' in x for x in jc.get('diagnosticos', [])),
          f"({jc.get('diagnosticos',[])})")

    print('  v9.28: Fisher, caixa, CAP, domínio, solver, rampa, deployment, APV-C7 e arredondamento travados')


def rec_v929_equity_book():
    """[v9.30] Fecha o equity `book` por identidades INDEPENDENTES: DDM = residual income = motor,
    cash-invariance, neutralidade ROE=Ke e colapso bifásico→monofásico. Mantém o nome histórico da
    função para não quebrar o runner, mas os invariantes são os corretivos da v9.30.
    """
    from justos import pe, iso_curva, _pe2_book, _equity_book_end, ponte_releveraging
    import random

    # Anchor da auditoria: caixa não altera book; o valor correto é o mesmo do espelho firm.
    g, r, rb, ke, n = 0.05, 0.20, 0.10, 0.08, 10
    anchor = pe(g, r, ke, n, 0.20, 0.0, tv='book', roe_book=rb)
    check('v9.30: anchor equity book sem dupla contagem = 12,8374',
          abs(anchor - 12.837404750556278) < 1e-12, f'({anchor})')
    for cx in (0.0, 0.10, 0.20, 0.50):
        check(f'v9.30: book invariante a Caixa/E {cx:.0%}',
              abs(pe(g, r, ke, n, cx, 0.0, tv='book', roe_book=rb) - anchor) < 1e-12)

    # DDM = residual income = motor em 1.000 vetores, inclusive com book separado.
    random.seed(930)
    pior = 0.0
    for i in range(1000):
        ke_i = random.uniform(0.05, 0.30)
        r_i = random.uniform(0.06, 0.70)
        rb_i = random.uniform(0.05, 0.50)
        g_i = random.uniform(0.0, min(0.20, r_i * 0.90))
        n_i = random.randint(1, 25)
        cx = random.uniform(0.0, 0.60)
        E = (1 + g_i) / rb_i
        E0 = E
        ddm = 0.0; ri = E0
        for t in range(1, n_i + 1):
            ni_t = (1 + g_i) ** t
            dE = (g_i / r_i) * ni_t
            div = ni_t - dE
            ddm += div / (1 + ke_i) ** t
            ri += (ni_t - ke_i * E) / (1 + ke_i) ** t
            E += dE
        ddm += E / (1 + ke_i) ** n_i
        m = pe(g_i, r_i, ke_i, n_i, cx, 0.0, tv='book', roe_book=rb_i)
        err = max(abs(m - ddm), abs(m - ri), abs(E - _equity_book_end(1.0, g_i, r_i, rb_i, n_i)))
        pior = max(pior, err)
        check(f'v9.30 DDM=RI=motor #{i}', err < 1e-10,
              f'err={err:.3e} g={g_i:.2%} r={r_i:.2%} rb={rb_i:.2%} cx={cx:.2%}')
    print(f'  v9.30 equity book: DDM = residual income = motor em 1.000 vetores (pior {pior:.2e})')

    # Neutralidade: ROE marginal = book = Ke => fwd 1/Ke, qualquer caixa e g admissível.
    for ke_i in (0.08, 0.12, 0.20):
        for g_i in (0.0, 0.03, 0.06):
            for cx in (0.0, 0.20, 0.50):
                m = pe(g_i, ke_i, ke_i, 10, cx, 0.0, tv='book', roe_book=ke_i) / (1 + g_i)
                check('v9.30 neutralidade book ROE=Ke independente de caixa', abs(m - 1 / ke_i) < 1e-10)

    # Iso book deve ser invariante a caixa.
    alvo = pe(0.04, 0.18, 0.11, 12, 0.0, 0.0, tv='book', roe_book=0.10)
    a0 = iso_curva('pe', alvo, 0.11, 12, [0.04], tv='book', gde=0.0, nde=0.0, rent_book=0.10)
    a5 = iso_curva('pe', alvo, 0.11, 12, [0.04], tv='book', gde=0.50, nde=0.0, rent_book=0.10)
    check('v9.30 iso book invariante a caixa',
          abs(a0['curva'][0]['rent_implicita_pct'] - a5['curva'][0]['rent_implicita_pct']) < 1e-10)

    # Bifásico deve colapsar no monofásico quando os dois regimes são idênticos, mesmo rb != marginal.
    for cut in (1, 3, 5, 9):
        m1 = pe(0.05, 0.20, 0.08, 10, 0.20, 0.0, tv='book', roe_book=0.10)
        m2 = _pe2_book(0.05, 0.20, 0.08, cut, 0.20, 0.0,
                       0.05, 0.20, 0.08, 10-cut, 0.20, 0.0,
                       0.10, 0.25, rb1=0.10)['total']
        check(f'v9.30 bifásico degenera no monofásico cut={cut}', abs(m1 - m2) < 1e-12,
              f'{m1} vs {m2}')

    # Ponte standalone com roe_book deve usar exatamente o E_pre acumulado.
    pt = ponte_releveraging(n1=5, ke1=0.14, ke2=0.12, gde1=0.4, nde1=0.2,
                            gde2=0.3, nde2=0.1, kd=0.08, tax=0.30, g1=0.05,
                            roe1=0.20, roe1_book=0.10)
    ep = _equity_book_end(1.0, 0.05, 0.20, 0.10, 5)
    check('v9.30 ponte usa E_pre acumulado', abs(pt['E_pre_transicao'] - ep) < 1e-12)
    print('  v9.30: caixa sem dupla contagem; bifásico carrega E; ponte usa o mesmo state variable')


def rec_v927_consistencia_cross_layer():
    """[v9.27] Contrato cross-layer: a matemática firm/book deve existir com a mesma semântica
    em motor, derivação, paper e aplicação; fórmulas/textos congelados da v9.24 não podem reaparecer.
    Também trava a memória técnica expandida e a classificação da base monetária como invariante.
    """
    import os
    from justos import iso_curva
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    def txt(rel):
        with open(os.path.join(root, rel), encoding='utf-8') as f:
            return f.read()
    deriv = txt('references/derivacao.md')
    paper = txt('references/paper-multiplos-justos-v3.md')
    aplic = txt('references/aplicacao.md')
    skill = txt('SKILL.md')
    _n = lambda t: re.sub(r'\s+', ' ', t)          # [v9.32] tolerante a quebra de linha
    skill_n, aplic_n = _n(skill), _n(aplic)
    motor = txt('scripts/justos.py')
    assinaturas = {
        'derivacao': ('IC_n = IC_0 +' in deriv and 'ROIC_marginal' in deriv and 'TV_desc = IC_n/' in deriv),
        'paper': ('IC_n = (1+g)' in paper and 'ROIC_marginal' in paper and 'TV_desc = IC_n/' in paper),
        'motor': ('ic_n = (1 + g)' in motor and 'roic_book' in motor),
        'motor_equity [v9.30]': ('e_n = (1 + g)' in motor and 'roe_book' in motor),
        'derivacao_equity [v9.30]': ('E_n  = (1+g)' in deriv and 'DDM = E_0' in deriv and 'clean surplus' in deriv.lower()),
        'paper_equity [v9.30]': ('E_n = (1+g)' in paper and 'DDM = residual income = motor' in paper),
    }
    for nome, ok in assinaturas.items():
        check(f'v9.27 cross-layer: {nome} contém IC acumulado', ok)
    proibidos = [
        'TV_desc = (1+g)ⁿ⁺¹ / [ROIC_book × (1+W)ⁿ]',
        'TV = NOPAT/ROIC_médio **não acompanha o marginal**',
        'a topologia bi-radicular em g do antigo §6.7 era ARTEFATO',
        'duas rotas equivalentes (Ke real; preço gratuito no terminal)',
        'hp` e `me` seguem aceitos como aliases legados',
        'equity_book_congelado_pendente',
        'explicitamente pendente e o motor avisa',
        'book continua congelado nesta versão',
        'permanece, nesta versão, com book congelado',
        'enquanto o book congelado permanecer',
    ]
    for lit in proibidos:
        check(f'v9.27 cross-layer: literal obsoleto ausente — {lit[:36]}',
              lit not in deriv and lit not in paper and lit not in skill and lit not in aplic)
    for campo in ('crescimento:', 'depreciacao:', 'clean_surplus:', 'book:'):
        check(f'v9.27 memória técnica: campo {campo}', campo in aplic)
    check('v9.32 base monetária = invariante, renumerada para 12ª',
          'invariante obrigatório' in skill.lower()
          and 'não uma 12ª escolha metodológica' in skill
          and 'não uma 11ª escolha metodológica' not in skill)
    # --- v9.32: marca de estoque (J16) ---
    check('v9.32 gatilho da marca de estoque no corpo (Gate 0)',
          '**Marca de estoque.**' in skill_n and 'VP(aluguel 1..T)' in skill_n
          and '`aplicacao.md` §13' in skill_n)
    check('v9.32 §13 deixa de ser órfão: citado pelo corpo e na enumeração',
          '§13' in skill_n and 'fronteira de escopo e marca de estoque §13' in skill_n.lower())
    check('v9.32 §10 de volta à enumeração de referências',
          'status das premissas §10' in skill_n)
    check('v9.32 regra da identidade no playbook',
          'Marca = VP(aluguel que o estoque comanda' in aplic_n
          and 'Fator de tempo' in aplic_n and 'Apreciação implícita' in aplic_n)
    check('v9.32 parede estoque↔fluxo com as duas rotas e o gap',
          'Parede estoque↔fluxo' in aplic_n and 'marca à vista + aluguel imputado' in aplic_n
          and 'o gap entre as rotas MEDE a violação' in aplic_n
          and 'Lado do ativo:' in aplic_n)
    check('v9.32 razão R generalizada (restaura a fórmula perdida do §3)',
          'Razão R' in aplic_n and 'capitalização perpétua do fluxo corrente' in aplic_n
          and 'cruzamento é exato em R = 1' in aplic_n)
    check('v9.32 deságio é operação sobre ativo',
          'Deságio é operação sobre ATIVO, nunca sobre líquido de passivos' in aplic)
    check('v9.32 corolário: realização de estoque não valida base de fluxo',
          'NUNCA ancora nem VALIDA uma base de FLUXO' in aplic_n
          and 'derivação por subtração é proibida' in aplic_n)
    check('v9.32 11ª escolha nomeada = nível da marca; rota é invariante',
          '11ª escolha metodológica nomeada' in aplic_n
          and 'ROTA (a)/(b) fica FORA da lista' in aplic_n
          and 'ONZE escolhas metodológicas' in skill_n)
    check('v9.32 composição multiplicativa no registro de drivers',
          'linearização quebra na MESMA linha exposta' in aplic_n
          and 'soma dos impactos percentuais' in aplic_n)
    check('v9.32 critério de aceitação (vi) nos dois espelhos',
          'não conta como rodada' in skill and 'não conta como rodada' in aplic)
    check('v9.32 campo marca_de_estoque na memória técnica', 'marca_de_estoque:' in aplic)
    check('v9.32 jurisprudência J16 registrada', 'J16 (AGRO3' in aplic)
    check('v9.32 manual de manutenção existe e é citado',
          os.path.exists(os.path.join(root, 'references/manutencao.md'))
          and '`references/manutencao.md`' in skill)
    check('v9.27 paper distingue múltiplo forward e corrente nas raízes',
          'base corrente' in paper and 'duas raízes' in paper and 'base forward' in paper)
    check('v9.28 Fisher: terminal-only não é chamado de equivalente',
          'terminal-only' in paper and 'não deve ser chamada de Fisher equivalente' in paper)
    check('v9.28 CAP: paper condiciona convergência a g < W',
          'Se **g < W**' in paper and 'não precisa ser' in paper and 'monotônico' in paper)
    check('v9.28 cash yield documentado', '--cash-yield' in skill and '--cash-yield' in aplic)
    check('v9.28 Miles-Ezzell corrigido', 'primeiro** escudo' in paper and 'posteriores' in paper and 'Ku' in paper)
    check('v9.30 equity book documenta Div + E_n sem dupla contagem',
          'Div + E_n' in skill and 'DDM = residual income = motor' in paper and 'dupla contagem' in deriv)
    check('v9.30 bifásico documenta patrimônio como state variable',
          'state variable' in deriv and 'E2_end' in deriv and 'ROE2*' in deriv)
    # v9.31 — fechamento semântico/cross-layer
    check('v9.31 E_pre antigo ausente da derivação corrente',
          'E_pré = (1+g₁)^{n₁+1}/ROE₁` — o equity lido como lucro forward' not in deriv)
    check('v9.31 rebase qualificado como hipótese de nível',
          'hipótese de rebase' in skill.lower() and 'hipótese de nível' in deriv.lower() and
          'hipótese adicional de **rebase do primeiro lucro**' in paper and
          'não é identificação estrutural pura' in motor.lower())
    check('v9.31 anchor P/L canônico sincronizado',
          'P/L 5,617295x' in deriv and 'P/L 5,617295x' in paper and 'P/L 5,7337x' not in deriv and 'P/L 5,7337x' not in paper)
    check('v9.31 Penman/horizonte finito qualificado',
          'terminais transformados de forma consistente' in paper and 'equivalência DCF↔renda residual só é rigorosa em horizonte infinito' not in paper)
    check('v9.31 comentário não promete planilha no ZIP',
          'planilha-equity-book, entregue com o release' not in motor)
    alvo_alpha = pe(0.05, 0.20, 0.12, 10, 0.30, 0.10, tv='book', roe_book=0.10)
    alpha_out = iso_curva('pe', alvo_alpha, 0.12, 10, [0.05], tv='book', gde=0.30, nde=0.10,
                          rent_book=0.10, transicao='nenhuma')
    check('v9.31 alpha metadata = coeficiente efetivo da book', alpha_out['alpha'] == 1.0)
    try:
        iso_curva('pe', 10.0, 0.16, 12, [0.10], tv='book', rent_book=0.10,
                  transicao='ponte', ponte_params={})
        rejeitou = False
    except SystemExit as e:
        rejeitou = '--rent-book' in str(e) and 'ignorado' in str(e)
    check('v9.31 função rejeita rent-book silencioso na ponte', rejeitou)
    print('  v9.31: cross-layer fecha rebase condicional, E_pre, anchors, alpha e horizonte finito')


def _executa_fase(nome):
    """[v9.27] Executa uma fase autocontida da suíte.

    A suíte completa é deliberadamente particionada em processos Python frescos. Isso evita que
    dezenas de subprocessos CLI + testes numéricos/documentais compartilhem estado de longo prazo
    (locale, pipes e buffers) e transforma `python scripts/testes.py` num ritual reprodutível também
    em ambientes restritos. Cada fase continua usando o mesmo interpretador (`sys.executable`).
    """
    if nome == 'model':
        # Fase única de modelo/documentação: roda primeiro o bloco mais pesado de inversões e,
        # no mesmo processo fresco, segue para propriedades/reconciliações. Evita multiplicar
        # processos-parent em ambientes com quotas agressivas de subprocessos.
        rc = _executa_fase('advanced')
        if rc != 0:
            return rc
        return _executa_fase('core')
    if nome == 'cli':
        print('CLI INTEGRATION')
        cli_integration()
    elif nome == 'core':
        print('PROPERTY TESTS')
        prop_neutralidade(); prop_neutralidade_marginal_book(); prop_convergencia_gp(); prop_monotonia_roic()
        rec_v97(); rec_v98()
        rec_lint_semantico(); rec_lint_portabilidade()
        prop_gradiente_g(); prop_pe_caixa()
        print('RECONCILIATION TESTS')
        rec_dcf_eva(); rec_fluxos_explicitos(); rec_apv()
        print('C1 — POLÍTICA DE CAIXA NO TERMINAL')
        rec_fcfe_tv(); rec_fcfe_canonico_tv(); prop_politica_tv()
        print('C3 / D2 / D4 — CONVENÇÃO TEMPORAL, BASE DO ALVO, ELASTICIDADE COM SINAL')
        prop_mid_year(); prop_alvo_base(); prop_elasticidade_sinal()
        print('BOUNDARY TESTS')
        bnd_limites(); bnd_solver(); bnd_aliases(); bnd_conflacao()
    elif nome == 'advanced':
        print('GUARDAS DAMODARAN')
        rec_guardas_damodaran()
        print('INVERSÃO BIFÁSICA')
        rec_inversao_bifasica()
        print('CORREÇÕES DE AUDITORIA / ISO / PONTE')
        rec_correcoes(); rec_iso(); rec_ponte()
        print('B-01 / APV-01 / P-02')
        rec_b01(); rec_apv01(); rec_p02()
        print('BOOK ACUMULADO / TOPOLOGIA / HARDENING / CONSISTÊNCIA CROSS-LAYER')
        rec_v926_book_acumulado(); rec_v928_hardening(); rec_v929_equity_book(); rec_v927_consistencia_cross_layer()
        print('DOC ANCHORS / IDA-E-VOLTA / COERÊNCIA DO VETOR')
        rec_doc_anchors(); rec_roundtrip(); rec_coerencia()
        rec_nivel_escala(); rec_guarda_raiz_gp(); rec_gate_agregado(); rec_rev_sugestao()
        rec_iso_sugestao(); rec_regime_driver()
        print('BASE COERENTE / CONFRONTO TEMPORAL')
        rec_v915()
        print('RAMPA BIFÁSICA / CONSERVAÇÃO / UNIT ECONOMICS')
        rec_rampa_v924()
    else:
        print(f'Fase desconhecida: {nome}', file=sys.stderr)
        return 2

    if FALHAS:
        print(f'\n{len(FALHAS)} FALHA(S) — NÃO USE O MOTOR:')
        for f in FALHAS:
            print(' -', f)
        return 1
    print(f'\nFASE {nome.upper()} PASSOU.')
    return 0


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--phase':
        sys.exit(_executa_fase(sys.argv[2]))
    if len(sys.argv) == 1:
        print('VALIDAÇÃO DE RELEASE REQUER DUAS INVOCAÇÕES FRESCAS:', file=sys.stderr)
        print('  python scripts/testes.py --phase model', file=sys.stderr)
        print('  python scripts/testes.py --phase cli', file=sys.stderr)
        print('Motivo: a fase CLI abre 20+ subprocessos reais; separar evita falso negativo por quota do ambiente.', file=sys.stderr)
        sys.exit(2)
    print('Uso: python scripts/testes.py --phase model|cli|core|advanced', file=sys.stderr)
    sys.exit(2)
