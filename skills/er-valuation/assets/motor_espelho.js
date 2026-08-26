// Espelho verificado por paridade do nucleo de valor de vendor/multiplos-justos/scripts/justos.py
// (v9.31) — reproduz ev_nopat/ev_ebitda (linhas 32-72) e pe (linhas 214-271); nenhuma alteracao
// pode ser feita neste arquivo sem que o harness de paridade (tests/test_paridade_js.py) a aprove.
//
// [item 4, fatia B, task 2] Ganhou o SOLVER do mesmo motor congelado — linhas 272-347
// (_dedupe_roots 272-279, solve 281-297, solve_full 298-322, identificacao 323-347) — com
// paridade propria em tests/test_paridade_solver_js.py (harness separado do acima: o solver e
// ITERATIVO e amplifica, o nucleo e forma fechada; ver o comentario da secao SOLVER abaixo).
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

// ---------------- despacho por item (CLI, item 4 fatia B) ----------------
// Sem `tipo`: item da fixture de VALOR da 4A (fn/args -> valor) — despachado
// por `avaliarVetores`, o MESMO caminho de sempre, sem nenhuma linha
// alterada nele: o harness da 4A continua verde sem mudanca. `tipo:
// 'solver'`: problema de solver (esta task), despachado por
// `resolverProblema`. Qualquer outro `tipo` LANCA — falha fechada, a mesma
// disciplina do resto deste arquivo.
function avaliarItem(item) {
  if (!('tipo' in item)) {
    return avaliarVetores([item])[0];
  }
  if (item.tipo === 'solver') {
    return resolverProblema(item);
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
