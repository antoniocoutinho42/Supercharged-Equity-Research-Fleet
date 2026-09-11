// Espelho verificado por paridade do nucleo de valor de vendor/multiplos-justos/scripts/justos.py
// (v9.31) — reproduz ev_nopat/ev_ebitda (linhas 32-72) e pe (linhas 214-271); nenhuma alteracao
// pode ser feita neste arquivo sem que o harness de paridade (tests/test_paridade_js.py) a aprove.
//
// [item 4, fatia B, task 2] Ganhou o SOLVER do mesmo motor congelado — linhas 272-347
// (_dedupe_roots 272-279, solve 281-297, solve_full 298-322, identificacao 323-347) — com
// paridade propria em tests/test_paridade_solver_js.py (harness separado do acima: o solver e
// ITERATIVO e amplifica, o nucleo e forma fechada; ver o comentario da secao SOLVER abaixo).
//
// [item 4, fatia B, task 3] Ganhou o WRAPPER: alvo de mercado (espelha
// skills/er-valuation/scripts/reversa.py:alvo_de_mercado) e as grades 1D/2D de sensibilidade
// (espelha skills/er-valuation/scripts/sensibilidades.py:grade_1d/grade_2d). Natureza de risco
// DIFERENTE das duas secoes acima: ali o lado Python de comparacao E' o motor congelado (direto
// ou via solver); aqui o lado Python E' O WRAPPER — que atravessa a CLI do motor por subprocesso
// (skills/er-valuation/scripts/motor.py:rodar), e essa CLI faz duas coisas que o nucleo em si
// nao faz: converte premissa de ponto percentual para fracao (`g: 5.0` = 5%, dividido por 100 —
// ver premissasParaNucleo abaixo) e ARREDONDA cada multiplo/preco antes de devolver o JSON
// (round(mn,4), round(preco_acao,2) — vendor justos.py, blocos dos cmds 'ev'/'pe'). Um espelho
// fiel ao nucleo e cego a essas duas conversoes produziria numero certo no lugar errado — por
// isso a paridade desta secao vive num harness PROPRIO, tests/test_paridade_wrapper_js.py,
// separado de tests/test_paridade_solver_js.py (que so' testa contra o motor).
//
// [item 4, fatia C, task 1] Ganhou a rota RAMPA: composicao bifasica (espelha
// vendor/multiplos-justos/scripts/justos.py:rampa_bifasica, linhas 74-171) mais a ponte do
// handler `elif a.cmd == 'rampa':` (mesmo arquivo, linhas 1946-1960), atras de
// skills/er-valuation/scripts/avaliar.py:precificar_rampa — o lado Python da paridade, MESMO
// harness (tests/test_paridade_wrapper_js.py) e MESMA fixture (tests/fixtures/vetores_solver.json)
// da secao WRAPPER acima: paridade e' contra o WRAPPER, nao contra o motor direto (a rota rampa
// nao tem consumidor 4A/solver — nasce direto nesta secao).
//
// Regra de risco: `rampa_bifasica` NAO devolve NaN para recusa de dominio (ao contrario de
// ev_nopat/pe) — ela LANCA ValueError (t_rampa/n, w/g2, wk/kappa, util sem g1, margem da fase 2).
// `rampaBifasica` abaixo espelha isso literalmente: lanca um Error da MESMA forma, no MESMO ponto
// do algoritmo, e quem chama (precificarRampa) captura — o analogo local de como MotorFalhou
// (avaliar.py) captura o subprocesso saindo com codigo != 0. Ha' ainda um SEGUNDO canal de recusa
// que rampa_bifasica nao lanca: a fase 2 chama ev_nopat (que RETORNA NaN, nao lanca) para o TV —
// um `gordon` com `gp >= w`, por exemplo, produz EV nao-finito sem nenhum ValueError. O motor de
// verdade ainda assim recusa nesse caso: o serializador do JSON converte o EV nao-finito em `null`,
// e `_exigir_valor` (motor.py/avaliar.py) recusa esse null como MotorFalhou. precificarRampa
// espelha essa segunda camada com uma checagem de Number.isFinite explicita — ver o comentario
// ali.
//
// Regras de espelho: a ordem das operacoes segue o Python termo a termo — inclusive o laco
// explicito t = 1..n somado na mesma ordem — porque divergencia de ordem em ponto flutuante e a
// causa mais provavel de erro na casa que importa. Cada guarda do Python (retorno NaN) vira uma
// guarda aqui; nenhuma e inventada, nenhuma e omitida.
//
// Ausencia (chave nao existe) x null (chave existe com valor null) — revisao final: os dois SO
// colapsam no mesmo comportamento para roic_tv/roe_tv/roic_book/roe_book, porque o default do
// Python para essas quatro TAMBEM e None. Para tv/gp/politica_tv o default do Python NAO e None
// ('book', 0.0, 'continua'), e Python so aplica esse default na AUSENCIA da chave — um None
// explicito atravessa **args direto para dentro da funcao e muda o caminho executado. Por isso
// estas tres usam checagem de PRESENCA ('k' in args ? args.k : default), nao '??' ('??' trata
// ausencia e null presente do mesmo jeito, que e exatamente o que o Python NAO faz aqui).
//
// Dois casos em que o Python nem chega a devolver NaN: ESTOURA (TypeError) — n nao-inteiro
// (range() do Python exige int) e gp null sob 'gordon' (gp <= -1 compara None com numero). Uma
// funcao pura deste lado nao pode propagar uma excecao Python para quem chama do outro lado do
// processo; a convencao explicita desta revisao e que os dois recusam por NaN aqui — a mesma
// linguagem de recusa de todo outro guarda deste arquivo.

// ---------------- convencoes de valor terminal (justos.py linhas 26-29) ----------------
const TV_CANON = {
  ic: 'book',
  spread: 'gordon',
  book: 'book',
  gordon: 'gordon',
  convergencia: 'convergencia',
};

function tvCanon(tv) {
  return Object.prototype.hasOwnProperty.call(TV_CANON, tv) ? TV_CANON[tv] : tv;
}

// ---------------- nucleo: ev_nopat / ev_ebitda (justos.py linhas 32-72) ----------------
function evNopat(args) {
  const g = args.g;
  const roic = args.roic;
  const w = args.w;
  const n = args.n;
  const tv = tvCanon('tv' in args ? args.tv : 'book');
  const roicTv = args.roic_tv ?? null;
  const gp = 'gp' in args ? args.gp : 0.0;
  const roicBook = args.roic_book ?? null;
  const midYear = args.mid_year ?? false;

  // n nao-inteiro: Python usa range(1, n+1), que estoura TypeError para n
  // fracionario — nao ha guarda de topo do Python que cubra isso (n<1 nao
  // pega n=7.5). Ver cabecalho: convencao explicita desta revisao, NaN.
  if (g <= -1 || roic <= 0 || w <= -1 || n < 1 || !Number.isInteger(n)) return NaN;

  const ret = 1 - g / roic;
  let s = 0;
  for (let t = 1; t <= n; t++) {
    s += ret * (1 + g) ** t / (1 + w) ** t;
  }

  if (tv === 'gordon') {
    // gp null: Python estoura TypeError em `gp <= -1`. Ver cabecalho:
    // convencao explicita desta revisao, NaN.
    if (roicTv === null || roicTv <= 0 || gp === null || gp <= -1 || gp >= w) return NaN;
    s += (1 + g) ** (n + 1) * (1 - gp / roicTv) / (w - gp) / (1 + w) ** n;
  } else if (tv === 'convergencia') {
    if (w <= 0) return NaN;
    s += (1 + g) ** (n + 1) / (w * (1 + w) ** n);
  } else {
    // book — [v9.28] IC_n por acumulacao coerente com o fluxo descontado: IC_0 = NOPAT_1/ROIC_medio;
    // capital novo entra ao MARGINAL (RiR = g/ROIC). Colapsa no comportamento antigo quando
    // medio = marginal ou g = 0. NAO usar NOPAT_{n+1}/medio — essa forma antiga esta errada
    // quando medio != marginal (o bug que o v9.26 do vendor corrigiu).
    const rb = roicBook !== null ? roicBook : roic;
    if (rb <= 0) return NaN;
    const icN = (1 + g) * (1.0 / rb - 1.0 / roic) + (1 + g) ** (n + 1) / roic;
    if (icN <= 0) return NaN;
    s += icN / (1 + w) ** n;
  }

  return s * (midYear ? (1 + w) ** 0.5 : 1.0);
}

function evEbitda(args) {
  return evNopat(args) * (1 - args.d) * (1 - args.t);
}

// ---------------- nucleo: pe (justos.py linhas 214-271) ----------------
function pe(args) {
  const g = args.g;
  const roe = args.roe;
  const ke = args.ke;
  const n = args.n;
  const gde = args.gde;
  const nde = args.nde;
  const tv = tvCanon('tv' in args ? args.tv : 'book');
  const roeTv = args.roe_tv ?? null;
  const gp = 'gp' in args ? args.gp : 0.0;
  const roeBook = args.roe_book ?? null;
  const politicaTv = 'politica_tv' in args ? args.politica_tv : 'continua';
  const midYear = args.mid_year ?? false;

  // n nao-inteiro: mesma razao de evNopat (ver cabecalho e comentario la).
  if (g <= -1 || roe <= 0 || ke <= -1 || n < 1 || !Number.isInteger(n)) return NaN;

  const caixa = gde - nde;
  // [v9.30] Na convencao book, clean surplus exige DDM + book: Div = LL - DeltaE = LL*(1-g/ROE_marg).
  // O termo +Deltacaixa pertence ao FCFE de uma politica de sweep, mas esse mesmo caixa permanece
  // dentro de E_n; usar FCFE + E_n duplicaria caixa. Por isso caixa/E NAO entra no termo do
  // explicito nem no terminal quando tv == 'book' — so em gordon/convergencia (aqui, so gordon
  // usa caixa; convergencia nao declara gp e o termo cai fora).
  const ret = tv === 'book' ? (1 - g / roe) : ((1 - g / roe) + caixa * (g / roe));
  let s = 0;
  for (let t = 1; t <= n; t++) {
    s += ret * (1 + g) ** t / (1 + ke) ** t;
  }

  if (tv === 'gordon') {
    // gp null: mesma razao de evNopat (ver cabecalho).
    if (roeTv === null || roeTv <= 0 || gp === null || gp <= -1 || gp >= ke) return NaN;
    const retTv = (1 - gp / roeTv) + (politicaTv === 'continua' ? caixa * (gp / roeTv) : 0.0);
    s += (1 + g) ** (n + 1) * retTv / (ke - gp) / (1 + ke) ** n;
  } else if (tv === 'convergencia') {
    if (ke <= 0) return NaN;
    s += (1 + g) ** (n + 1) / (ke * (1 + ke) ** n);
  } else {
    // book — [v9.30] E_n por clean surplus, INVARIANTE a caixa/E pelo cancelamento descrito acima.
    // Colapsos do estoque: medio = marginal => E_n = LL_{n+1}/ROE; g = 0 => E_n = 1/medio.
    const rb = roeBook !== null ? roeBook : roe;
    if (rb <= 0) return NaN;
    const eN = (1 + g) * (1.0 / rb - 1.0 / roe) + (1 + g) ** (n + 1) / roe;
    if (eN <= 0) return NaN;
    s += eN / (1 + ke) ** n;
  }

  return s * (midYear ? (1 + ke) ** 0.5 : 1.0);
}

// ---------------- ponte para preco (EV -> equity -> preco/acao, fora do motor) ----------------
// ATENCAO — esta ponte espelha SOMENTE a rota firm/NOPAT de avaliar.py
// (precificar_firm, ramo NOPAT, linhas 233-234: `equity = ev - nd_efetivo`;
// `preco_acao = equity / acoes`). As outras duas rotas do relatorio NAO
// passam por aqui: a rota firm/EBITDA cruza a ponte DENTRO do motor
// (Preco_acao ja sai pronto de `saida` — avaliar.py chama isso de "ponte
// feita pelo motor"); a rota equity chega em Equity DIRETO de PL_curr x LL,
// sem divida liquida nenhuma (avaliar.py: "rota equity nao usa ponte").
// Chamar esta funcao sobre um caso equity SUBTRAIRIA nd_efetivo de um
// numero que ja e equity — divida contada duas vezes. Quem oferecer esta
// ponte no laboratorio do item 5 tem de saber, por rota, se deve chama-la.
//
// Chaves em snake_case, como o nucleo (roic_tv, mid_year, ...) — nao
// camelCase: fidelidade-por-leitura e o ponto do arquivo inteiro, e
// nd_efetivo/preco_acao sao os mesmos nomes que avaliar.py usa.
function ponteParaPreco(args) {
  const ev = args.ev;
  const ndEfetivo = args.nd_efetivo;
  const acoes = args.acoes;
  const equity = ev - ndEfetivo;
  const precoAcao = equity / acoes;
  return { equity, preco_acao: precoAcao };
}

// ---------------- avaliacao em lote (harness de paridade e laboratorio do relatorio) ----------------
const DESPACHO = { ev_nopat: evNopat, ev_ebitda: evEbitda, pe };

function avaliarVetores(vetores) {
  return vetores.map((vetor) => {
    const f = DESPACHO[vetor.fn];
    if (!f) throw new Error(`fn desconhecida no vetor de paridade: ${vetor.fn}`);
    const bruto = f(vetor.args);
    return { id: vetor.id, valor: Number.isFinite(bruto) ? bruto : null };
  });
}

// ============================================================================
// SOLVER (item 4, fatia B, task 2) — espelha vendor/multiplos-justos/scripts/
// justos.py linhas 272-347: _dedupe_roots (272-279), solve (281-297),
// solve_full (298-322), identificacao (323-347). Risco DIFERENTE do nucleo
// acima: aquele e forma fechada (uma diferenca de 1e-15 permanece 1e-15);
// este e ITERATIVO e AMPLIFICA — uma diferenca minuscula em f pode inverter
// a comparacao de sinal `y0*y1<=0` num ponto da varredura e produzir uma
// raiz A MAIS OU A MENOS, divergencia DISCRETA que uma comparacao de valor
// nao pega. Por isso a ORDEM das operacoes segue o Python passo a passo —
// inclusive reaproveitar y0 entre iteracoes em vez de recalcular f(x0), e o
// numero fixo de iteracoes das duas buscas — com a mesma disciplina de
// fidelidade-de-forma da secao do nucleo acima.
// ============================================================================

// _dedupe_roots (justos.py 272-279): uma raiz sobre um ponto da grade
// pertence aos dois intervalos adjacentes e nao pode virar dois regimes
// economicos no output.
function dedupeRaizes(raizes, atol = 1e-10, rtol = 1e-8) {
  const ordenadas = [...raizes].sort((a, b) => a - b);
  const out = [];
  for (const x of ordenadas) {
    const ultimo = out.length ? out[out.length - 1] : undefined;
    if (out.length === 0 ||
        Math.abs(x - ultimo) > Math.max(atol, rtol * Math.max(Math.abs(x), Math.abs(ultimo), 1.0))) {
      out.push(x);
    }
  }
  return out;
}

// solve (justos.py 281-297): varredura + bissecao; devolve raizes DISTINTAS
// com mudanca de sinal no intervalo. Detalhe 1 do brief desta task: f(lo) e
// avaliado UMA VEZ antes do laco e y0 e REAPROVEITADO entre iteracoes — nao
// e f(x0) recalculado a cada passo. Detalhe 2: a bissecao roda 90 iteracoes
// FIXAS, sem criterio de parada por tolerancia — copia o numero, nao um
// "ate convergir".
function resolver(f, lo, hi, steps) {
  const raizes = [];
  let x0 = lo;
  let y0 = f(lo);
  for (let i = 1; i <= steps; i++) {
    const x1 = lo + (hi - lo) * i / steps;
    const y1 = f(x1);
    const ok = [y0, y1].every((v) => v === v && Math.abs(v) !== Infinity);
    if (ok && y0 * y1 <= 0 && y0 !== y1) {
      let a = x0;
      let b = x1;
      let fa = y0;
      for (let k = 0; k < 90; k++) {
        const m = (a + b) / 2;
        const fm = f(m);
        if (fa * fm <= 0) { b = m; } else { a = m; fa = fm; }
      }
      raizes.push((a + b) / 2);
    }
    x0 = x1;
    y0 = y1;
  }
  return dedupeRaizes(raizes);
}

// solve_full (justos.py 298-321): raizes por mudanca de sinal (resolver,
// acima) + candidatos TANGENCIAIS (minimos locais de |f| SEM cruzamento — a
// bissecao pura os perde exatamente na regiao do teto). Detalhe 3 do brief:
// busca ternaria de 80 iteracoes sobre |f|; aceita o candidato so' se
// |f(x)| <= tangRel*max(|ref|,1e-12); dedup contra as raizes JA achadas E
// contra as tangenciais JA aceitas, nos dois casos com tolerancia relativa
// 1e-3. Devolve {raizes, tangenciais} (objeto, nao a tupla do Python — sem
// consumidor externo que dependa de posicao).
function resolverCompleto(f, lo, hi, steps, ref = 1.0, tangRel = 1e-4) {
  const raizes = resolver(f, lo, hi, steps);
  const xs = [];
  const ys = [];
  for (let i = 0; i <= steps; i++) {
    const x = lo + (hi - lo) * i / steps;
    xs.push(x);
    ys.push(f(x));
  }
  const tangenciais = [];
  for (let i = 1; i < steps; i++) {
    const y0 = ys[i - 1];
    const y1 = ys[i];
    const y2 = ys[i + 1];
    if ([y0, y1, y2].some((v) => v !== v)) continue;
    if (Math.abs(y1) <= Math.abs(y0) && Math.abs(y1) <= Math.abs(y2) && y0 * y2 > 0) {
      let a = xs[i - 1];
      let b = xs[i + 1];
      for (let k = 0; k < 80; k++) {
        const m1 = a + (b - a) / 3;
        const m2 = b - (b - a) / 3;
        if (Math.abs(f(m1)) < Math.abs(f(m2))) { b = m2; } else { a = m1; }
      }
      const x = (a + b) / 2;
      const fx = f(x);
      if (Math.abs(fx) <= tangRel * Math.max(Math.abs(ref), 1e-12)) {
        const jaERaiz = raizes.some((r) => Math.abs(x - r) <= 1e-3 * Math.max(Math.abs(r), 1e-6));
        const jaETangencial = tangenciais.some(
          (t) => Math.abs(x - t.x) <= 1e-3 * Math.max(Math.abs(t.x), 1e-6),
        );
        if (!jaERaiz && !jaETangencial) {
          tangenciais.push({ x, residuo: fx });
        }
      }
    }
  }
  return { raizes, tangenciais };
}

// ---------------- arredondamento bancario (contrato de identificacao) ----------------
// Detalhe 4 do brief desta task: `round` do Python arredonda pelo valor
// EXATO do double, metade para o PAR mais proximo ("bancario"); `Math.round`
// do JS so' arredonda a INTEIRO, metade para CIMA e, em negativos, para
// +Infinito (nao "para longe de zero"). `identificacao` abaixo compara por
// IGUALDADE EXATA os campos arredondados — um helper que so' aproximasse o
// Math.round nativo divergiria sistematicamente bem antes de qualquer ruido
// de ponto flutuante genuino.
//
// `toFixed(100)` e' definido pela especificacao sobre o VALOR EXATO do
// double (nao sobre a string mais curta que arredonda de volta a ele — essa
// e' a razao de round(2.675, 2) dar 2.67 no Python: o double mais proximo de
// 2.675 e' na verdade 2.674999...82, e um algoritmo baseado na string curta
// "2.675" erraria para 2.68). 100 casas cobrem com folga a expansao decimal
// exata de qualquer double na faixa deste motor.
function arredondarPy(x, ndigits) {
  if (!Number.isFinite(x)) return x;
  if (x === 0) return x;
  if (ndigits < 0) throw new Error('arredondarPy: ndigits negativo nao suportado (nenhum campo desta task usa)');

  const negativo = x < 0;
  const ax = Math.abs(x);
  const str = ax.toFixed(100);
  const ponto = str.indexOf('.');
  const inteiro = str.slice(0, ponto);
  const fracionaria = str.slice(ponto + 1);

  const casas = ndigits;
  const digitoCorte = fracionaria[casas]; // digito IMEDIATAMENTE apos o corte
  const digitos = (inteiro + fracionaria.slice(0, casas)).split('').map(Number);

  let arredondaParaCima;
  if (digitoCorte === undefined || digitoCorte < '5') {
    arredondaParaCima = false;
  } else if (digitoCorte > '5') {
    arredondaParaCima = true;
  } else {
    // digito de corte == '5': EXATAMENTE no meio (dentro da precisao de 100
    // casas, que cobre a expansao exata do double) so' se todo digito
    // seguinte for zero -- caso contrario esta estritamente acima do meio.
    const restoAposCorte = fracionaria.slice(casas + 1);
    if (/[1-9]/.test(restoAposCorte)) {
      arredondaParaCima = true;
    } else {
      const ultimoDigito = digitos.length ? digitos[digitos.length - 1] : 0;
      arredondaParaCima = (ultimoDigito % 2) === 1; // par mais proximo
    }
  }

  if (arredondaParaCima) {
    let i = digitos.length - 1;
    while (i >= 0) {
      digitos[i] += 1;
      if (digitos[i] === 10) { digitos[i] = 0; i -= 1; } else { break; }
    }
    if (i < 0) digitos.unshift(1);
  }

  const semPonto = digitos.join('');
  const parteInteira = casas === 0 ? semPonto : (semPonto.slice(0, semPonto.length - casas) || '0');
  const parteFracionaria = casas === 0 ? '' : semPonto.slice(semPonto.length - casas);
  const resultadoStr = casas === 0 ? parteInteira : `${parteInteira}.${parteFracionaria}`;
  const resultado = parseFloat(resultadoStr);
  return negativo ? -resultado : resultado;
}

// f'{tol:.0%}' do Python: multiplica por 100 e arredonda a 0 casas (mesmo
// arredondamento bancario de round()) antes de anexar '%'. Só é chamada com
// tol=0.01 nesta task (-> "1%"), mas a implementação não hardcoda esse
// valor — generalidade sem custo, não invenção de superfície nova.
function formatarPercentualPy(tol) {
  return `${arredondarPy(tol * 100, 0)}%`;
}

// identificacao (justos.py 323-346): metricas de identificacao economica em
// torno de uma raiz — slope, curvatura, elasticidade e o intervalo da
// variavel compativel com alvo +/- tol. Quando qualquer uma das tres
// avaliacoes vizinhas e' NaN, devolve o dict DEGENERADO {nota: ...} sem os
// campos numericos — essa forma e' contrato (detalhe 5 do brief), nao um
// dict cheio de nulos.
//
// ATENCAO a truthiness: Python usa `if M`/`if d1`/`if x` (== "!= 0.0",
// valido ATE para NaN, porque `nan != 0` e' True em Python). "!== 0" do JS
// reproduz essa checagem EXATAMENTE, inclusive para NaN, porque
// `NaN !== 0` tambem e' `true` em JS — a armadilha seria usar coercao
// implicita (`v ? a : b`), onde NaN e' FALSY em JS ao contrario do Python.
function identificacao(multFn, x, M, tol = 0.01) {
  const h = Math.max(Math.abs(x), 1e-4) * 1e-4;
  const m0 = multFn(x);
  const mp = multFn(x + h);
  const mm = multFn(x - h);
  if ([m0, mp, mm].some((v) => v !== v)) {
    return { nota: 'derivadas indisponíveis na vizinhança da raiz' };
  }
  const d1 = (mp - mm) / (2 * h);
  const d2 = (mp - 2 * m0 + mm) / h ** 2;
  const elast = M !== 0 ? (d1 * x) / M : NaN;
  const dx = d1 !== 0 ? Math.abs((tol * M) / d1) : Infinity;
  const rel = x !== 0 ? dx / Math.abs(x) : Infinity;
  const cls = rel < 0.05 ? 'forte' : (rel < 0.20 ? 'moderada' : 'fraca');
  const notaPorClasse = {
    fraca: 'identificação FRACA: a função é quase plana — a raiz é ruído com cara '
      + 'de precisão; não apresente sem a curvatura',
    moderada: 'identificação moderada: reporte o intervalo junto com a raiz',
    forte: 'bem identificada no local',
  };
  const chaveIntervalo = `intervalo_para_alvo_±${formatarPercentualPy(tol)}`;
  return {
    slope_dM_dx: arredondarPy(d1, 4),
    curvatura_d2M_dx2: arredondarPy(d2, 2),
    elasticidade: arredondarPy(elast, 3),
    [chaveIntervalo]: [arredondarPy((x - dx) * 100, 3), arredondarPy((x + dx) * 100, 3)],
    'largura_relativa_%': rel === rel ? arredondarPy(rel * 100, 1) : null,
    identificacao: cls,
    nota: notaPorClasse[cls],
  };
}

// ---------------- problema de solver (contrato do brief task-4b-2) ----------------
// `args` traz o vetor SEM a premissa resolvida; injeta-se `x` sob a chave
// `resolver` para montar `f`, o mesmo jeito que o subcomando `rev` do
// vendor monta a funcao a resolver (justos.py, bloco do cmd 'rev':
// `def f(x): ... return base_f(...) - M`). `mult` NAO chama a funcao do
// nucleo de novo — e' `f(x) + alvo`, o MESMO caminho de ponto flutuante que
// o vendor usa (`mult = lambda x: f(x) + M`): (fn(x)-alvo)+alvo nao e'
// sempre bit-a-bit igual a fn(x), e esta task exige paridade em TAU=1e-12.
function resolverProblema(problema) {
  const f = DESPACHO[problema.fn];
  if (!f) throw new Error(`fn desconhecida no problema de solver: ${problema.fn}`);
  const resolverVar = problema.resolver;
  const alvo = problema.alvo;
  const calcular = (x) => f({ ...problema.args, [resolverVar]: x }) - alvo;
  const mult = (x) => calcular(x) + alvo;

  let raizes;
  let tangenciais;
  if (problema.completo) {
    ({ raizes, tangenciais } = resolverCompleto(calcular, problema.lo, problema.hi, problema.steps, alvo));
  } else {
    raizes = resolver(calcular, problema.lo, problema.hi, problema.steps);
    tangenciais = [];
  }

  const ident = raizes.length ? identificacao(mult, raizes[0], alvo, 0.01) : null;

  return { id: problema.id, raizes, tangenciais, identificacao: ident };
}

function avaliarProblemas(problemas) {
  return problemas.map(resolverProblema);
}

// ============================================================================
// WRAPPER (item 4, fatia B, task 3) — espelha skills/er-valuation/scripts/reversa.py
// (alvo_de_mercado) e skills/er-valuation/scripts/sensibilidades.py (grade_1d/grade_2d). Ver o
// comentario no topo do arquivo para o porque desta secao ter harness de paridade proprio.
// ============================================================================

// premissasParaNucleo (justos.py, blocos dos cmds 'ev'/'pe', ~linhas 1896-1901 e 1963-1968):
// a CLI do motor recebe premissa em PONTO PERCENTUAL (g: 5.0 = 5%, convencao de caso.json — ver
// tests/fixtures/caso_reversa_firm.json) e divide por 100 (`pc = lambda x: x/100.0`) ANTES de
// chamar ev_nopat/ev_ebitda/pe — que trabalham em fracao, como o resto deste arquivo (4A e o
// solver chamam essas funcoes DIRETO, pulando a CLI, entao nunca precisaram desta conversao). So'
// o WRAPPER (esta secao) atravessa a CLI, entao so' aqui essa conversao importa.
//
// [item 4, fatia C, task 1] 'receita0'/'ebitda0'/'da_parque'/'t_rampa' entraram aqui quando a rota
// rampa ganhou espelho: sao premissas EXCLUSIVAS do subparser 'rampa' (justos.py:1741-1743, 1748)
// e NENHUMA delas passa por `pc()` no handler (`elif a.cmd == 'rampa':`, justos.py:1946) — sao
// monetario/contagem/ano, nao taxa (detalhe 1 do brief da task: reaproveitar premissasParaNucleo
// sem esta extensao divide EBITDA por 100). Nao colidem com o vocabulario de ev/pe
// (PREMISSAS_FIRM/PREMISSAS_EQUITY, caso.py) — nomes exclusivos da rota rampa — entao estender o
// conjunto COMPARTILHADO e' seguro: nao muda em nada o caminho firm/equity ja' coberto pela 4B.
const CHAVES_NAO_PERCENTUAIS = new Set([
  'n', 'tv', 'mid_year', 'politica_tv', 'receita0', 'ebitda0', 'da_parque', 't_rampa',
]);

// Renomeacao de chave que a CLI da rota firm faz (justos.py, cmd 'ev'): 'wacc' -> 'w' (parametro
// de ev_nopat/ev_ebitda); 'da'/'tax' -> 'd'/'t' (escala EBITDA, `me = mn*(1-d)*(1-t)`). A rota
// equity nao renomeia nada — pe() usa os MESMOS nomes que caso.json declara.
const RENOMEIA_FIRM = { wacc: 'w', da: 'd', tax: 't' };

// [item 4, fatia C, task 1] Renomeacao da rota rampa: SO' 'wacc' -> 'w' — rampa_bifasica
// (justos.py linha 74) recebe o WACC pelo parametro posicional `w`, chamado como `pc(a.wacc)` no
// handler (mesma razao de RENOMEIA_FIRM). 'tax'/'da_parque'/'t_rampa' NAO renomeiam aqui: ao
// contrario da rota firm (onde 'tax' vira 't'), a assinatura de rampa_bifasica usa os MESMOS
// nomes 'tax'/'da_parque'/'t_rampa' que o caso.json/CLI declaram —
// `rampa_bifasica(receita0, ebitda0, da_parque, wk, w, tax, n, t_rampa, g2, kappa, ...)`.
// Reusar RENOMEIA_FIRM aqui renomearia 'tax'->'t' por engano (rampaBifasica nao tem parametro
// `t`), silenciosamente lendo `args.tax` como undefined.
const RENOMEIA_RAMPA = { wacc: 'w' };

function pct(valor) {
  return (valor === null || valor === undefined) ? null : valor / 100.0;
}

// ATENCAO — semantica de default OPOSTA a do nucleo (ver cabecalho do arquivo, linhas 28-40) —
// revisao final da fatia 4B, achados F1/F2/F3: e' a armadilha central deste arquivo e ja' pegou
// uma vez (esta funcao so' tratava 'gp' antes desta correcao).
//
// No NUCLEO (evNopat/pe acima, chamados DIRETO com **kwargs pela rota 4A/solver), um `null`
// explicito TEM DE atravessar intacto — muda o caminho executado, e os ids 86/87 de
// vetores_paridade.json cobram exatamente essa diferenca. NAO mexa naquele caminho.
//
// Aqui, no WRAPPER, e' o INVERSO: `null` e AUSENCIA colapsam no MESMO resultado — a chave
// simplesmente nao entra em `out`. E' a semantica de `motor.py:argv_para` (linha ~217:
// `if valor is None: continue` — a flag da CLI nem e' emitida) seguida do argparse do motor
// congelado, que aplica o SEU proprio default de subcomando (justos.py:1758/1763: gde=0.0,
// nde=0.0, gp=0.0 em 'pe'; gp=0.0 em 'ev'; politica_tv='continua'). Um `null` explicito
// PRESERVADO (o bug corrigido aqui) faria o nucleo ler `'chave' in args === true` com valor
// `null` e tomar um ramo ERRADO — ex.: `politica_tv: null` virava "nao e 'continua'",
// derrubando o termo de caixa do terminal onde o motor de verdade, nunca tendo visto a flag,
// aplica 'continua' (F2). Por isso o loop abaixo pula QUALQUER chave com valor `null`, nao so'
// 'gp': colapsar para ausencia e' sempre seguro aqui porque e' exatamente o que a CLI real faz
// antes do nucleo.
//
// Duas premissas que o colapso por si so' NAO resolve, porque o nucleo so' aplica
// presenca-ou-ausencia (nunca um default proprio para preencher o buraco):
// - gde/nde (rota equity): opcionais no caso (`caso.py:161`, PREMISSAS_OBRIGATORIAS_EQUITY nao
//   as exige), mas `pe()` (acima) LE `args.gde`/`args.nde` DIRETO, sem fallback de presenca —
//   ausentes, `caixa = undefined - undefined = NaN` e o multiplo inteiro vira `null` mesmo
//   quando o motor de verdade, com o default 0.0 do argparse, devolve um preco (F1).
//   `precificarCelula` (abaixo) repoe esse default depois do colapso, so' na rota equity.
// - tv: NAO tem default nenhum (`--tv required=True`, justos.py:1729) — e' a UNICA premissa
//   obrigatoria que pode chegar aqui como `null` (as outras obrigatorias recusariam antes, na
//   validacao do caso). Colapsar para ausencia faria o NUCLEO aplicar o SEU default ('book'),
//   inventando um preco onde o motor de verdade sai com Gate 1 (exit 2, `MotorFalhou`) sem
//   calcular nada (F3). `precificarCelula` recusa esse caso explicitamente, ANTES de chegar
//   aqui, em vez de deixar o colapso inventar um numero.
function premissasParaNucleo(premissas, renomeia) {
  const out = {};
  for (const chave of Object.keys(premissas)) {
    const valor = premissas[chave];
    // Colapsa com ausencia — motor.py:argv_para:217. SEMPRE, para TODA chave, nao so' 'gp'.
    if (valor === null) continue;
    const chaveNova = renomeia[chave] || chave;
    if (CHAVES_NAO_PERCENTUAIS.has(chave)) {
      out[chaveNova] = valor;
      continue;
    }
    out[chaveNova] = pct(valor);
  }
  return out;
}

function paraSaidaOuNulo(x) {
  return Number.isFinite(x) ? x : null;
}

// precificarCelula espelha avaliar.py:precificar_firm/precificar_equity (chamadas por
// sensibilidades.py:_precificar_celula, celula a celula) — a MESMA ponte de preco que o
// cenario principal usa, nunca um numero fora do nucleo. Os arredondamentos abaixo nao sao
// deste espelho: sao os do MOTOR (justos.py, blocos dos cmds 'ev'/'pe' — round(mn,4)/
// round(me,4) para o multiplo, round(_,2) para EV/Equity/Preco_acao) — o wrapper Python le o
// JSON do subprocesso DEPOIS desse arredondamento, entao um espelho que so' arredondasse no
// final (e nao nos MESMOS pontos que o motor arredonda) divergiria da paridade em TAU=1e-12.
//
// Ramo NOPAT (rota firm): o motor NUNCA recebe --ebitda/--nd/--acoes nesta chamada
// (precificar_firm, ramo NOPAT) — EV/Equity/preco_acao sao algebra do WRAPPER (avaliar.py,
// linhas ~222-239) sobre o multiplo JA' ARREDONDADO que atravessou o JSON do subprocesso (nao
// sobre `mn` cru): arredonda PRIMEIRO, so' DEPOIS multiplica.
//
// Ramo EBITDA (rota firm) e rota equity: o motor recebe a escala (--ebitda/--nd/--acoes ou
// --ni/--acoes) e computa EV/Equity/Preco_acao ele mesmo, a partir do `me`/`m` CRU (nao do
// multiplo arredondado) — o arredondamento do multiplo (EV/EBITDA_curr ou PL_curr) e' um
// calculo SEPARADO, que nao alimenta a cadeia EV->Equity->Preco_acao.
function precificarCelula(rota, premissas, metrica, ndEfetivo, acoes) {
  // F3 (revisao final 4B): 'tv' e' a UNICA premissa obrigatoria sem default nenhum (--tv
  // required=True, justos.py:1729) — o motor de verdade sai no Gate 1 (exit 2, MotorFalhou)
  // sem calcular nada quando ela chega null. Diferente de gde/nde/politica_tv (que TEM default
  // de argparse para repor depois do colapso null->ausencia em premissasParaNucleo), 'tv' nao
  // tem o que repor: deixar colapsar faria o NUCLEO aplicar o SEU default ('book'), inventando
  // um preco onde o motor recusa. Recusamos aqui, ANTES de premissasParaNucleo sequer rodar, no
  // mesmo vocabulario null que todo outro guarda deste arquivo usa.
  if (premissas.tv === null) {
    return { valor: null, multiplo: null };
  }
  if (rota === 'firm') {
    const args = premissasParaNucleo(premissas, RENOMEIA_FIRM);
    if (metrica.tipo === 'EBITDA') {
      const me = evEbitda(args);
      const multiplo = arredondarPy(me, 4);
      const evBruto = me * metrica.valor;
      const valor = arredondarPy((evBruto - ndEfetivo) / acoes, 2);
      return { valor: paraSaidaOuNulo(valor), multiplo: paraSaidaOuNulo(multiplo) };
    }
    const mn = evNopat(args);
    const multiplo = arredondarPy(mn, 4);
    const ev = multiplo * metrica.valor;
    const valor = (ev - ndEfetivo) / acoes;
    return { valor: paraSaidaOuNulo(valor), multiplo: paraSaidaOuNulo(multiplo) };
  }
  // equity
  const args = premissasParaNucleo(premissas, {});
  // gde/nde sao OPCIONAIS na rota equity (caso.py:161) mas pe() (acima) le args.gde/args.nde
  // DIRETO, sem fallback de presenca — ausentes depois do colapso null->ausencia, caixa =
  // undefined - undefined = NaN e o multiplo inteiro desaparece (achado F1). O argparse do
  // motor da' a elas default 0.0 (justos.py:1758); repomos o mesmo aqui, so' nesta rota.
  if (!('gde' in args)) args.gde = 0;
  if (!('nde' in args)) args.nde = 0;
  const m = pe(args);
  const multiplo = arredondarPy(m, 4);
  const eqBruto = m * metrica.valor;
  const valor = arredondarPy(eqBruto / acoes, 2);
  return { valor: paraSaidaOuNulo(valor), multiplo: paraSaidaOuNulo(multiplo) };
}

// alvoDeMercado espelha reversa.py:alvo_de_mercado — a definicao de multiplo aplicada aos
// dados JA' DECLARADOS do caso (preco, acoes, metrica-base e, na rota firm, a ponte via
// ndEfetivo). Pura aritmetica, NENHUMA chamada ao nucleo — por isso nao ha conversao percentual
// -> fracao aqui: preco/acoes/metrica.valor/ndEfetivo sao valor em moeda ou contagem, nunca
// taxa. Devolve so' o NUMERO (`["valor"]` de alvo_de_mercado) — `algebra`/`base` sao prosa de
// auditoria, fora do que a calibragem desta task pede para testar (numero e' material, string
// nao — ver task-4b-3-brief.md).
function alvoDeMercado({ rota, preco, acoes, ndEfetivo, metrica }) {
  const marketCap = preco * acoes;
  if (rota === 'firm') {
    const evMercado = marketCap + ndEfetivo;
    return evMercado / metrica.valor;
  }
  return marketCap / metrica.valor; // equity
}

// grade1D/grade2D espelham sensibilidades.py:grade_1d/grade_2d — cada celula e' uma chamada a
// precificarCelula acima, nunca um numero fora do nucleo. D5 do plano da fatia B: a dedup de
// diagnostico do wrapper (`diagnosticos_unicos`/"diag" por celula) NAO entra aqui — este espelho
// existe para o LABORATORIO numerico (valor, multiplo, orientacao da grade), nao para reproduzir
// a trilha de diagnostico do motor. `moeda` esta' na assinatura por paridade de forma com o
// wrapper (sensibilidades.grade_1d/grade_2d recebem `caso["moeda"]`), mas nao entra em nenhuma
// conta aqui: moeda so' troca o AVISO de diagnostico que o motor emite, nunca um numero.
//
// grade2D: `celulas[i][j]` = `(pontosY[i], pontosX[j])` — uma linha por valor de pontosY, uma
// coluna por valor de pontosX. MESMA orientacao de sensibilidades.grade_2d (linhas 184-190):
// `for y in pontos_y: for x in pontos_x: ...`. A fatia 3C descobriu que uma grade QUADRADA
// esconde uma transposicao de eixos (o teste passava com os eixos trocados) — por isso o
// harness de paridade desta task (test_grades_tem_a_orientacao_do_wrapper) exige uma grade
// NAO quadrada.
function grade1D({ rota, premissas, metrica, ndEfetivo, acoes, premissa, pontos }) {
  return pontos.map((x) => {
    const vetor = { ...premissas, [premissa]: x };
    const { valor, multiplo } = precificarCelula(rota, vetor, metrica, ndEfetivo, acoes);
    return { x, valor, multiplo };
  });
}

function grade2D({ rota, premissas, metrica, ndEfetivo, acoes, premissaX, pontosX, premissaY, pontosY }) {
  return pontosY.map((y) => pontosX.map((x) => {
    const vetor = { ...premissas, [premissaX]: x, [premissaY]: y };
    const { valor, multiplo } = precificarCelula(rota, vetor, metrica, ndEfetivo, acoes);
    return { x, y, valor, multiplo };
  }));
}

// ============================================================================
// RAMPA (item 4, fatia C, task 1) — espelha vendor/multiplos-justos/scripts/justos.py:
// rampa_bifasica (linhas 74-171) mais a ponte do handler `elif a.cmd == 'rampa':` (linhas
// 1946-1960). Ver o comentario no topo do arquivo para a natureza dos dois canais de recusa.
// ============================================================================

// Subconjunto da saida do motor que entra em `saida` (contrato do brief) — mesma lista, mesma
// ordem, em skills/er-valuation/scripts/vetores_solver.py (_avaliar_rampa) e em
// tests/test_paridade_wrapper_js.py: os tres lados tem de concordar, porque os harnesses comparam
// os dois primeiros contra o terceiro. `rir_fase1_%` sai SEM a chave 'nota' (texto estatico, nunca
// varia) — rampaBifasica abaixo simplesmente nunca a escreve, entao o filtro por CAMPOS_RAMPA nao
// precisa de um caso especial para tirá-la.
const CAMPOS_RAMPA = [
  'g1_%', 'd_trajetoria_fase1_%', 'd2_fase2_%', 'rir_fase1_%', 'alfa', 'beta',
  'rir2_%', 'roic2_%', 'vp_fase1', 'valor_fase2_no_ano_T', 'capacidade_receita',
];

// Chaves que o motor ACRESCENTA condicionalmente ao dict de saida (`out['aviso_colheita'] = ...`,
// `out['aviso_delator'] = ...`) — 'avisos' e' a lista, EM ORDEM, das que estao presentes. O TEXTO
// de cada aviso e' prosa fora do escopo desta fatia (ver cabecalho do arquivo e a nota da secao
// WRAPPER sobre alvoDeMercado); so' a PRESENCA importa, por isso rampaBifasica abaixo escreve
// `true` em vez de reproduzir a frase do motor.
const AVISOS_RAMPA = ['aviso_colheita', 'aviso_delator'];

// rampaBifasica espelha SOMENTE a funcao nucleo `rampa_bifasica` — mesma assinatura (em FRACAO,
// como o resto deste arquivo), mesmos defaults (g1/util/roic_tv/roic_book = null, gp = 0.0,
// tv = 'convergencia'; 'n' NAO tem default aqui, porque rampa_bifasica tambem nao tem — o default
// 10 e' do ARGPARSE do subcomando, aplicado por precificarRampa antes de chamar esta funcao, do
// jeito exato que o handler ja' teria `a.n == 10` antes de chamar rampa_bifasica). Calcula so' o
// que CAMPOS_RAMPA + a ponte (EV, EV/EBITDA0) precisam — bloco/checks_internos/travas/T_rampa/
// n_total/g2_% ficam de fora (Fora do escopo do plano: "Asserts internos de rampa_bifasica — nao
// espelhar"; nenhum consumidor le esses campos). fcff1/pv1_exp/p1 (so' existem no motor para o
// assert P1/P1b) tambem ficam de fora pela mesma razao — pv1 usa direto a forma fechada
// alfa*soma_r1 + beta*ann_beta, que e' o MESMO valor que o motor usa a jusante.
function rampaBifasica(args) {
  const receita0 = args.receita0;
  const ebitda0 = args.ebitda0;
  const daParque = args.da_parque;
  const wk = args.wk;
  const w = args.w;
  const tax = args.tax;
  const n = args.n;
  const tRampa = args.t_rampa;
  const g2 = args.g2;
  const kappa = args.kappa;
  let g1 = args.g1 ?? null;
  const util = args.util ?? null;
  const tv = 'tv' in args ? args.tv : 'convergencia';
  const roicTv = args.roic_tv ?? null;
  const gp = 'gp' in args ? args.gp : 0.0;
  const roicBook = args.roic_book ?? null;

  if (tRampa < 1 || n <= tRampa) {
    throw new Error('composição exige 1 <= t_rampa < n (a fase 2 precisa de >= 1 ano explícito)');
  }
  if (w <= -1 || g2 <= -1) {
    throw new Error('domínio inválido: requer WACC > -100% e g2 > -100%');
  }
  if (wk < 0 || kappa < 0) {
    throw new Error('domínio inválido: wk e kappa devem ser >= 0');
  }
  let capacidade = null;
  if (g1 === null) {
    if (util === null || !(util > 0.0 && util < 1.0)) {
      throw new Error('informe --g1 diretamente OU --util em (0,100) com --t-rampa');
    }
    g1 = (1.0 / util) ** (1.0 / tRampa) - 1.0;
    capacidade = receita0 / util;
  }
  const m = ebitda0 / receita0;
  const T = tRampa;

  const rev = [];
  for (let t = 0; t <= T; t++) rev.push(receita0 * (1 + g1) ** t);

  // rir1/dpath: fcff1 (a terceira serie que o motor acumula aqui) fica de fora — so' alimenta o
  // assert P1, fora do escopo (ver comentario acima da funcao).
  const rir1 = [];
  const dpath = [];
  for (let t = 1; t <= T; t++) {
    const eb = m * rev[t];
    const nop = (eb - daParque) * (1 - tax);
    const dwk = wk * (rev[t] - rev[t - 1]);
    // Python: `dwk/nop if nop else float('nan')` — truthiness sobre FLOAT, falsy so' em 0.0/-0.0.
    // `nop !== 0` reproduz isso (== trata -0 e 0 como iguais, tanto em Python quanto em JS) — ver
    // o aviso de truthiness NaN-vs-JS no cabecalho do arquivo (secao SOLVER, identificacao).
    rir1.push(nop !== 0 ? dwk / nop : NaN);
    dpath.push(daParque / eb);
  }

  const alfa = (1 - tax) * ebitda0 - (wk * g1 * receita0) / (1 + g1);
  const beta = -(1 - tax) * daParque;
  const r1 = (1 + g1) / (1 + w);
  const somaR1 = Math.abs(r1 - 1.0) < 1e-12 ? T : (r1 * (1 - r1 ** T)) / (1 - r1);
  const annBeta = Math.abs(w) < 1e-14 ? T : (1 - (1 + w) ** -T) / w;
  const pv1 = alfa * somaR1 + beta * annBeta;

  const ebT = m * rev[T];
  const d2 = daParque / ebT;
  const m2n = m * (1 - d2) * (1 - tax);
  if (m2n <= 0) {
    throw new Error('fase 2 inválida: margem NOPAT deve ser positiva para mapear capital incremental');
  }
  const denCap = wk + kappa;
  let rir2;
  let roic2;
  let roic2Limite;
  if (denCap <= 1e-15) {
    rir2 = 0.0;
    roic2 = 1e12;
    roic2Limite = true;
  } else {
    rir2 = (denCap * g2) / ((1 + g2) * m2n);
    roic2 = ((1 + g2) * m2n) / denCap;
    roic2Limite = false;
  }
  const nopT = ebT * (1 - d2) * (1 - tax);
  // Detalhe 8 do brief: a fase 2 chama ev_nopat do PROPRIO motor — reusa a funcao ja' espelhada
  // (4A) em vez de reescrever a logica de TV. Sem mid_year (rampa_bifasica nao tem esse
  // parametro) — evNopat aplica o default False dela mesma quando a chave esta' ausente.
  const mn2 = evNopat({
    g: g2, roic: roic2, w, n: n - T, tv, roic_tv: roicTv, gp, roic_book: roicBook,
  });
  const evT = mn2 * nopT;
  const ev = pv1 + evT / (1 + w) ** T;

  // Detalhe 4 do brief, primeira metade: EV e EV/EBITDA0 arredondam INDEPENDENTEMENTE sobre o
  // MESMO `ev` cru — EV/EBITDA0 nao deriva do EV ja' arredondado (a segunda metade do detalhe,
  // sobre a ponte Equity/Preco_acao, vive em precificarRampa abaixo).
  const rirFase1 = {};
  rirFase1.ano_1 = arredondarPy(rir1[0] * 100, 3);
  rirFase1[`ano_${T}`] = arredondarPy(rir1[rir1.length - 1] * 100, 3);
  const dTrajetoria = {};
  dTrajetoria.ano_1 = arredondarPy(dpath[0] * 100, 3);
  dTrajetoria[`ano_${T}`] = arredondarPy(dpath[dpath.length - 1] * 100, 3);

  const out = {
    'g1_%': arredondarPy(g1 * 100, 4),
    'd_trajetoria_fase1_%': dTrajetoria,
    'd2_fase2_%': arredondarPy(d2 * 100, 3),
    'rir_fase1_%': rirFase1,
    alfa: arredondarPy(alfa, 6),
    beta: arredondarPy(beta, 6),
    'rir2_%': arredondarPy(rir2 * 100, 3),
    // Detalhe 5 do brief: capital incremental zero (wk=kappa=0, ate' 1e-15) vira a STRING do
    // motor, nao um numero — comparada por igualdade exata do mesmo jeito que os campos numericos.
    'roic2_%': roic2Limite ? 'infinito — capital incremental zero' : arredondarPy(roic2 * 100, 3),
    vp_fase1: arredondarPy(pv1, 4),
    valor_fase2_no_ano_T: arredondarPy(evT, 4),
    EV: arredondarPy(ev, 4),
    'EV/EBITDA0': arredondarPy(ev / ebitda0, 4),
  };
  if (capacidade !== null) {
    out.capacidade_receita = arredondarPy(capacidade, 4);
  }
  if (g1 < 0) {
    out.aviso_colheita = true;
  }
  if (rir2 >= 1.0) {
    out.aviso_delator = true;
  }
  return out;
}

// precificarRampa espelha avaliar.py:precificar_rampa — irma' de precificarCelula (rotas
// firm/equity), mas para rampa: o motor recebe --nd/--acoes e faz a composicao bifasica inteira
// internamente, EV/Equity/Preco_acao saem prontos, do mesmo jeito que o ramo EBITDA da rota firm
// ja' usa o motor para fazer a ponte inteira (ver precificarCelula acima). Tres guardas de recusa:
//  1) Gate 1 (tv: null) — precificarCelula ja' faz o mesmo para ev/pe; 'tv' tambem nao tem default
//     no subparser 'rampa' (--tv required=True, justos.py:1752).
//  2) rampaBifasica pode LANCAR (ValueError no motor — dominio de t_rampa/n/w/g2/wk/kappa/util/
//     margem da fase 2) — capturado aqui, o analogo local de MotorFalhou quando o subprocesso do
//     motor de verdade sai com codigo != 0.
//  3) Mesmo com rampaBifasica retornando normalmente, a fase 2 (ev_nopat) pode devolver NaN — ex.:
//     'gordon' com gp >= w. rampa_bifasica NAO tem guarda para isso (nao e' um ValueError do
//     motor); mas o SERIALIZADOR do motor converte o EV/EV-EBITDA0 nao-finitos resultantes em
//     `null` no JSON, e _exigir_valor (motor.py/avaliar.py) recusa esse null como MotorFalhou —
//     _exigir_valor(saida, "EV/EBITDA0") e' a PRIMEIRA leitura que precificar_rampa faz, entao e'
//     ela quem dispara primeiro. Espelhado pela checagem de Number.isFinite abaixo, sobre o MESMO
//     campo.
function precificarRampa({
  premissas, ndEfetivo, acoes, moeda,
}) {
  if (premissas.tv === null) {
    return { recusado: true };
  }
  const nucleo = premissasParaNucleo(premissas, RENOMEIA_RAMPA);
  // 'n' tem default 10 no argparse do subparser 'rampa' (justos.py:1749) — AO CONTRARIO de ev/pe,
  // onde 'n' e' premissa OBRIGATORIA do caso (PREMISSAS_OBRIGATORIAS_EQUITY/FIRM, caso.py) e por
  // isso o espelho de ev/pe nunca precisou deste default. PREMISSAS_OBRIGATORIAS_RAMPA (caso.py)
  // NAO inclui 'n' (detalhe 2 do brief) — reposto aqui, depois do colapso null->ausencia de
  // premissasParaNucleo.
  if (!('n' in nucleo)) nucleo.n = 10;

  let saidaMotor;
  try {
    saidaMotor = rampaBifasica(nucleo);
  } catch (erro) {
    return { recusado: true };
  }
  if (!Number.isFinite(saidaMotor['EV/EBITDA0'])) {
    return { recusado: true };
  }
  const multiplo = saidaMotor['EV/EBITDA0'];

  let valor;
  if (ndEfetivo === null) {
    valor = { EV: saidaMotor.EV };
  } else {
    // Detalhe 4 do brief, segunda metade: Equity usa o EV JA' ARREDONDADO (saidaMotor.EV, nao um
    // `ev` cru — este espelho nem expõe um `ev` cru fora de rampaBifasica) — mesma ordem do
    // handler (`eq = res['EV'] - a.nd`, justos.py:1958).
    const eq = saidaMotor.EV - ndEfetivo;
    if (!acoes) {
      // O handler so' escreve 'Preco_acao' quando `a.acoes` e' truthy (`if a.acoes:`,
      // justos.py:1959); se nao, o wrapper (_exigir_valor sobre "Preco_acao") recusa por campo
      // ausente — mesmo vocabulario de recusa que os outros dois canais acima. Nenhum problema
      // desta fixture exercita `acoes` falsy com ponte (nao faz parte do plano), mas a guarda
      // fecha o caso mesmo assim: silenciar 'preco_acao' com recusado:false divergiria do
      // wrapper de verdade.
      return { recusado: true };
    }
    valor = {
      EV: saidaMotor.EV,
      Equity: arredondarPy(eq, 2),
      preco_acao: arredondarPy(eq / acoes, 2),
    };
  }

  const saida = {};
  for (const campo of CAMPOS_RAMPA) {
    if (campo in saidaMotor) saida[campo] = saidaMotor[campo];
  }
  const avisos = AVISOS_RAMPA.filter((chave) => chave in saidaMotor);

  return {
    recusado: false, multiplo, valor, saida, avisos,
  };
}

// ---------------- problemas de wrapper (contrato do brief task-4b-3) ----------------
// Campos do shape do SOLVER que todo resultado de "alvo"/"grade1d"/"grade2d" tambem carrega,
// vazios — nao e' o shape natural desses tres tipos (que so' tem "alvo" ou "celulas"), e'
// compatibilidade retroativa deliberada: tests/test_paridade_solver_js.py (task 2, imutavel por
// regra desta task) le a fixture INTEIRA sem filtrar por tipo e indexa `raizes`/`tangenciais`/
// `identificacao` direto (sem fallback) em todo item da lista — sem estes tres campos aqui,
// aquele harness levantaria erro assim que alcancasse um item de wrapper misturado na mesma
// fixture (tests/fixtures/vetores_solver.json carrega os dois tipos de problema, por decisao do
// plano da fatia B). O lado Python (vetores_solver.py, `_CAMPOS_SOLVER_VAZIOS`) carrega o MESMO
// preenchimento — os dois lados tem de concordar, porque aquele harness compara os dois.
const CAMPOS_SOLVER_VAZIOS = { raizes: [], tangenciais: [], identificacao: null };

// `args` de um problema de wrapper esta' em snake_case (JSON compartilhado com o Python); as
// tres funcoes acima usam camelCase (convencao do resto deste arquivo) — estes tres adaptadores
// fazem a ponte de nome, nada mais.
function resolverAlvo(item) {
  const a = item.args;
  const alvo = alvoDeMercado({
    rota: a.rota, preco: a.preco, acoes: a.acoes, ndEfetivo: a.nd_efetivo, metrica: a.metrica,
  });
  return { id: item.id, alvo, ...CAMPOS_SOLVER_VAZIOS };
}

function resolverGrade1D(item) {
  const a = item.args;
  const celulas = grade1D({
    rota: a.rota, premissas: a.premissas, metrica: a.metrica, ndEfetivo: a.nd_efetivo,
    acoes: a.acoes, premissa: a.premissa, pontos: a.pontos, moeda: a.moeda,
  });
  return { id: item.id, celulas, ...CAMPOS_SOLVER_VAZIOS };
}

function resolverGrade2D(item) {
  const a = item.args;
  const celulas = grade2D({
    rota: a.rota, premissas: a.premissas, metrica: a.metrica, ndEfetivo: a.nd_efetivo,
    acoes: a.acoes, premissaX: a.premissa_x, pontosX: a.pontos_x,
    premissaY: a.premissa_y, pontosY: a.pontos_y, moeda: a.moeda,
  });
  return { id: item.id, celulas, ...CAMPOS_SOLVER_VAZIOS };
}

// [item 4, fatia C, task 1] `args` de um problema de rampa esta' no MESMO shape do contrato
// (`premissas`/`nd_efetivo`/`acoes`/`moeda`) — precificarRampa ja' usa esses nomes, entao este
// adaptador so' espalha `item.args` nos parametros nomeados; ainda carrega CAMPOS_SOLVER_VAZIOS
// pela MESMA razao de resolverAlvo/resolverGrade1D/resolverGrade2D acima (test_paridade_solver_js.py
// le a fixture inteira sem filtrar por tipo).
function resolverRampa(item) {
  const a = item.args;
  const resultado = precificarRampa({
    premissas: a.premissas, ndEfetivo: a.nd_efetivo, acoes: a.acoes, moeda: a.moeda,
  });
  return { id: item.id, ...resultado, ...CAMPOS_SOLVER_VAZIOS };
}

// ---------------- despacho por item (CLI, item 4 fatia B) ----------------
// Sem `tipo`: item da fixture de VALOR da 4A (fn/args -> valor) — despachado
// por `avaliarVetores`, o MESMO caminho de sempre, sem nenhuma linha
// alterada nele: o harness da 4A continua verde sem mudanca. `tipo:
// 'solver'`: problema de solver (task 2), despachado por `resolverProblema`.
// `tipo: 'alvo'|'grade1d'|'grade2d'`: problema de wrapper (task 3),
// despachado por `resolverAlvo`/`resolverGrade1D`/`resolverGrade2D`. `tipo:
// 'rampa'` (fatia C, task 1): despachado por `resolverRampa`.
// Qualquer outro `tipo` LANCA — falha fechada, a mesma disciplina do resto
// deste arquivo.
function avaliarItem(item) {
  if (!('tipo' in item)) {
    return avaliarVetores([item])[0];
  }
  if (item.tipo === 'solver') {
    return resolverProblema(item);
  }
  if (item.tipo === 'alvo') {
    return resolverAlvo(item);
  }
  if (item.tipo === 'grade1d') {
    return resolverGrade1D(item);
  }
  if (item.tipo === 'grade2d') {
    return resolverGrade2D(item);
  }
  if (item.tipo === 'rampa') {
    return resolverRampa(item);
  }
  throw new Error(`tipo desconhecido no item de paridade: ${item.tipo}`);
}

function avaliarItens(itens) {
  return itens.map(avaliarItem);
}

// ---------------- exportacao: CommonJS (node) OU globalThis (browser) ----------------
// FIX 1 (revisao final, item Critico) — `module.exports = {...}` incondicional
// estourava `ReferenceError: module is not defined` num contexto sem `module`
// — exatamente o de um <script> de browser (o banner de paridade e o
// laboratorio do item 5, os DOIS chamadores que a Decisao D2 do plano promete
// — "um caminho de codigo, dois chamadores"). A execucao morria antes de
// `avaliarVetores` ficar alcancavel: o segundo chamador nunca existiu de
// fato. `typeof` e a unica forma segura de checar um identificador que pode
// nem existir, sem estourar sozinho.
const superficiePublica = {
  evNopat, evEbitda, pe, ponteParaPreco, avaliarVetores,
  dedupeRaizes, resolver, resolverCompleto, identificacao, resolverProblema, avaliarProblemas,
  alvoDeMercado, grade1D, grade2D, precificarCelula,
  resolverAlvo, resolverGrade1D, resolverGrade2D,
  rampaBifasica, precificarRampa, resolverRampa,
  avaliarItem, avaliarItens,
};

if (typeof module !== 'undefined' && typeof module.exports !== 'undefined') {
  module.exports = superficiePublica;
} else {
  globalThis.MotorEspelho = superficiePublica;
}

// CLI
if (typeof module !== 'undefined' && typeof require !== 'undefined' && require.main === module) {
  const fs = require('fs');
  const caminho = process.argv[2];
  const itens = JSON.parse(fs.readFileSync(caminho, 'utf-8'));
  const resultados = avaliarItens(itens);
  console.log(JSON.stringify(resultados));
}
