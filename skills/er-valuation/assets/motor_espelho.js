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
// [item 4, fatia C, task 2] Ganhou os PREDICADOS de diagnostico das rotas firm/equity — espelha
// diag_firm (justos.py:513-602), diag_eq (604-731) e _guardas_damodaran (348-379), mais a
// composicao dos handlers `ev`/`pe` (`diagnosticos = diag_* + coerencia_vetor(...)[0]`). So' as
// CHAVES ESTAVEIS entram aqui — a prosa do motor (numeros interpolados, frases inteiras) fica de
// fora de proposito (ver diagnosticos_chaves.json, o vocabulario que classifica cada mensagem do
// motor pelo PREFIXO): o relatorio (item 5) chaveia um dicionario estatico de prosa por essas
// mesmas chaves, nunca reproduz o texto do motor. Ver a secao DIAGNOSTICOS abaixo para o
// contrato completo, inclusive a razao pela qual `coerencia_vetor` so' contribui UMA chave
// (identidade 4) e NENHUMA na rota equity — achado empirico, nao suposicao: PREMISSAS_FIRM/
// PREMISSAS_EQUITY (caso.py) nunca expoe as chaves cruzadas (roe/gde/nde/kd na rota firm;
// roic/wacc/kd/tax/da na equity) que as outras tres identidades exigem, entao elas nunca
// executam pelo caminho do wrapper — confirmado rodando o motor.rodar real (nao suposto por
// leitura), ver o relatorio desta task para a evidencia.
//
// [Fatia D, Task 2] Ganhou o DEGRAU (Gate 3 — capacidade ociosa de balanco) — espelha fator_h/
// rentab_pos_degrau/desconto_transicao/valor_transicionado (justos.py:792-830) e o calculo por
// nivel do handler `elif a.cmd == 'degrau':` (justos.py ~2531-2587), atras de
// skills/er-valuation/scripts/avaliar.py:precificar_degrau + _aplicar_degrau_ao_cenario — AINDA o
// WRAPPER (mesmo harness/fixture da secao WRAPPER acima): a forma que este espelho reproduz e' a
// de `resultados.json` (cenarios.<nome>.{valor,sem_degrau,vs_preco,degrau}), nao a saida crua do
// subcomando `degrau`. So' a rota equity tem degrau (D2, plano da fatia); o ramo firm do MESMO
// handler (roic/wacc) nunca e' alcancado pelo caminho do wrapper e fica de fora, por decisao de
// desenho, nao por descuido. Ver a secao DEGRAU abaixo para as duas correcoes ao plano
// (ALERTA_CONVENCAO_BOOK inalcancavel pelo Gate 3 da Task 1; dominioCliRecusa aplicado na entrada)
// e para a razao de ALERTA/ALERTA_RiR virarem `true`, nao a prosa do motor.
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

// ---------------- avaliar_dominios_cli (justos.py:1608-1630) — F2, revisao final, fatia 4C ------
// O motor roda avaliar_dominios_cli ANTES de QUALQUER handler (main(), justos.py:1881): para
// g/g1/g2/gp/gtv <= -100%, wacc/ke/ku/kd <= -100% ou n < 1, ele imprime o erro e sai com codigo 2
// (SystemExit) — nenhum handler roda, nenhum diagnostico e' computado. Ate' esta correcao, o
// espelho so' recusava quando o NUCLEO (evNopat/pe/rampaBifasica) por acaso tambem lancava/
// devolvia NaN para o MESMO valor — nao e' sempre o caso: 'gp' sob 'book'/'convergencia' e' inerte
// (nenhuma formula do nucleo o le), e 'g1' na rampa nao tem guarda de dominio nenhuma (vira
// receita negativa em vez de recusa). Verificado por execucao contra o wrapper real (ver
// fixes-4c-report.md): rampa com g1=-150% mostrava EV -359,30 em vez de recusar; rampa com
// gp=-150% sob 'book' mostrava o MESMO preco do caso valido (gp nunca e' lido).
//
// `premissas` chega em PONTOS PERCENTUAIS BRUTOS, com os MESMOS nomes que a CLI usa (g, g1, g2,
// gp, wacc, ke, n...) — a checagem roda ANTES de premissasParaNucleo/RENOMEIA_* (que so' fariam
// sentido depois de decidir que a entrada e' valida), exatamente como avaliar_dominios_cli roda
// sobre o namespace CRU do argparse, antes de qualquer renomeacao de handler. Uma chave de fora
// desta lista (roic, roe, da, tax, receita0...) e' ignorada, do mesmo jeito que a funcao Python
// ignora tudo que nao esta' na lista dela — 'ku'/'kd'/'gtv'/'roe'(firm)/'roic'(equity) nunca
// aparecem no vocabulario que o wrapper expoe (PREMISSAS_FIRM/PREMISSAS_EQUITY/PREMISSAS_RAMPA,
// caso.py), entao checa-las aqui e' inofensivo (sempre `undefined`, nunca dispara) — mantido pela
// MESMA razao que o resto deste arquivo prefere uma guarda estrutural unica a varias guardas
// pontuais: fiel a` funcao real, nao só aos sintomas ja' observados.
const CHAVES_DOMINIO_MAIOR_QUE_MENOS100 = ['g', 'g1', 'g2', 'gp', 'gtv', 'wacc', 'ke', 'ku', 'kd'];

function dominioCliRecusa(premissas) {
  for (const nome of CHAVES_DOMINIO_MAIOR_QUE_MENOS100) {
    const v = premissas[nome];
    if (v !== undefined && v !== null && v <= -100) return true;
  }
  const n = premissas.n;
  if (n !== undefined && n !== null && n < 1) return true;
  return false;
}

// [onda de correcao da revisao final da 5C, F2] cliRecusa: a CLI do motor recusa o vetor ANTES de
// qualquer handler, com codigo 2 e sem calcular nada, em duas camadas — o ARGPARSE (`--tv`
// obrigatorio, required=True, e `--n`/`--t-rampa` inteiros, type=int, nos quatro subcomandos que o
// wrapper chama: justos.py:1729 ev, 1748-1752 rampa, 1762 pe, 1825-1826 degrau) e
// avaliar_dominios_cli (dominioCliRecusa, acima). Nenhuma porta de precificacao deste arquivo
// precisa dela: todas ja recusam esses vetores por conta propria (tv null explicito, NaN do nucleo
// para n nao inteiro, dominioCliRecusa). Quem precisa e' a FACHADA, para dizer ao analista POR QUE
// um cenario foi recusado — premissa fora do dominio que o motor aceita x combinacao sem valor
// finito — com o motivo que o motor de verdade confirmaria: tests/test_espelho_fachada_js.py confere
// cada motivo contra avaliar() (codigo 2 x `null` ou erro do nucleo).
const CHAVES_INTEIRAS_DA_CLI = ['n', 't_rampa'];

function cliRecusa(premissas) {
  if (premissas.tv === null || premissas.tv === undefined) return true;
  for (const nome of CHAVES_INTEIRAS_DA_CLI) {
    const v = premissas[nome];
    if (v !== undefined && v !== null && !Number.isInteger(v)) return true;
  }
  return dominioCliRecusa(premissas);
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
  // F2 (revisao final, fatia 4C) — ver o comentario de dominioCliRecusa, secao WRAPPER acima.
  if (dominioCliRecusa(premissas)) {
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
//
// [item 4, fatia C, task 2] 'aviso_gp' acrescentado ao final da lista — DIFERENTE dos dois
// irmaos: aviso_colheita/aviso_delator sao decididos DENTRO de rampa_bifasica (o nucleo, sobre
// g1/rir2), mas aviso_gp e' decidido no HANDLER `elif a.cmd == 'rampa':` (justos.py ~1954), sobre
// `a.rf`/`a.tv`/`a.gp' — dados que rampa_bifasica nunca recebe (ela nao tem parametro `rf`). Por
// isso aviso_gp e' calculado em precificarRampa abaixo, nao em rampaBifasica — ver o comentario
// ali. A ORDEM dentro deste array so' precisa concordar entre os dois lados (o filtro
// `AVISOS_RAMPA.filter(chave => chave in saidaMotor)` usa a ordem do ARRAY, nao a de insercao no
// dict) — nao ha' semantica de "quem roda primeiro" sendo espelhada aqui.
const AVISOS_RAMPA = ['aviso_colheita', 'aviso_delator', 'aviso_gp'];

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
//
// [item 4, fatia C, task 2] `rf` (novo parametro, default null) ativa 'aviso_gp' — espelha a
// condicao INLINE do handler `elif a.cmd == 'rampa':` (justos.py ~1954):
//     if getattr(a, 'rf', None) is not None and a.tv == 'gordon' and pc(a.gp) and pc(a.gp) > pc(a.rf):
//         res['aviso_gp'] = ...
// ACHADO (nao suposicao — verificado por chamada direta ao motor real, duas vezes, com e sem
// avaliar.py no meio): o plano desta fatia dizia que a comparacao e' `a.tv == 'gordon'` SEM
// tv_canon, e que por isso o alias 'spread' nao dispararia o aviso. Isso NAO reproduz o motor
// congelado: a substituicao de alias (`a.tv = tv_canon(a.tv)`, justos.py ~1888-1894) roda uma
// UNICA vez, ANTES de QUALQUER `if a.cmd == ...`, para TODO subcomando — entao, no momento em que
// o handler rampa le `a.tv`, 'ic'/'spread' JA' viraram 'book'/'gordon'. `--tv spread --gp 8 --rf
// 5` no motor real dispara aviso_gp identico a `--tv gordon` com os mesmos numeros (mesma
// mensagem, byte a byte) — `--tv ic` (que canonicaliza para 'book', nao 'gordon') e' quem
// genuinamente NUNCA dispara. Por isso tvCanon(...) entra aqui: a paridade desta fatia inteira e'
// contra o COMPORTAMENTO do motor, nao contra uma leitura textual isolada do handler — reportado
// como discrepancia do plano no relatorio desta task, com os dois comandos que provam o achado.
function precificarRampa({
  premissas, ndEfetivo, acoes, moeda, rf = null,
}) {
  if (premissas.tv === null) {
    return { recusado: true };
  }
  // F2 (revisao final, fatia 4C) — ver o comentario de dominioCliRecusa, secao WRAPPER acima.
  // Cobre, entre outras, 'g1' (sem guarda de dominio nenhuma dentro de rampaBifasica — viraria
  // receita negativa em vez de recusa) e 'gp' sob 'book'/'convergencia' (nunca lido pelo nucleo
  // sob essas convencoes, entao nunca produziria NaN por conta propria).
  if (dominioCliRecusa(premissas)) {
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

  // aviso_gp: ver o comentario grande acima da funcao. `nucleo.gp` reproduz o mesmo default 0.0
  // que rampaBifasica aplica internamente (`'gp' in args ? args.gp : 0.0`) — precisa do MESMO
  // valor aqui porque o handler real le `pc(a.gp)`, que tambem ja' passou pelo default 0.0 do
  // argparse do subparser 'rampa' (justos.py:1753: `add_argument('--gp', ..., default=0.0)`).
  const rfFracao = pct(rf);
  const gpNucleo = 'gp' in nucleo ? nucleo.gp : 0.0;
  if (rfFracao !== null && tvCanon(nucleo.tv) === 'gordon' && gpNucleo && gpNucleo > rfFracao) {
    saidaMotor.aviso_gp = true;
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
// [item 4, fatia C, task 2] `rf` entra no adaptador com o mesmo `?? null` que os problemas de
// rampa anteriores a esta task (sem `rf` declarado) ja' esperam — `a.rf` ausente do JSON vira
// `undefined` em JS, nao `null`; `?? null` normaliza os dois para o mesmo "sem taxa livre de
// risco" que precificarRampa's default (`rf = null`) tambem entende.
function resolverRampa(item) {
  const a = item.args;
  const resultado = precificarRampa({
    premissas: a.premissas, ndEfetivo: a.nd_efetivo, acoes: a.acoes, moeda: a.moeda, rf: a.rf ?? null,
  });
  return { id: item.id, ...resultado, ...CAMPOS_SOLVER_VAZIOS };
}

// ============================================================================
// DIAGNOSTICOS (item 4, fatia C, task 2) — espelha diag_firm (justos.py:513-602), diag_eq
// (604-731) e _guardas_damodaran (348-379), mais a composicao dos handlers `ev`/`pe` no main()
// (`diagnosticos = diag_* + coerencia_vetor(...)[0]`). Ver o comentario no topo do arquivo para o
// porque de so' as CHAVES entrarem aqui, nunca a prosa.
//
// Paridade e' contra o WRAPPER (mesmo harness/fixture da secao WRAPPER acima), NUNCA contra
// diag_firm/diag_eq direto: e' o vocabulario de premissas do CASO (PREMISSAS_FIRM/
// PREMISSAS_EQUITY, caso.py) que decide quais ramos de coerencia_vetor sao alcancaveis — nao a
// assinatura de diag_firm/diag_eq, que aceita mais parametros do que o caso jamais declara (a
// rota 'ev' tambem tem --roe/--ke/--gde/--nde/--kd/--cash-yield/--rir-observado/--ebitda-ic na
// CLI, para uso direto fora do wrapper — `flags_coerencia`, justos.py:1710-1719/1728 — mas
// PREMISSAS_FIRM nunca inclui essas chaves, entao o wrapper nunca as emite). Por isso
// `diagnosticosFirm`/`diagnosticosEquity` abaixo leem SOMENTE premissas que
// `premissasParaNucleo` ja' resolve a partir do vetor do caso — nunca um vetor cruzado que so'
// existiria chamando o motor fora do wrapper.
// ============================================================================

// Limiares (contrato — copiados do vendor, nao escolhidos aqui):
// - 5e-4: "quase igual" para roic/wacc, roic_tv/wacc, roic_book/roic, roic_book/wacc (e os
//   quatro espelhos do lado equity) — diag_firm/diag_eq usam o MESMO literal em todo teste de
//   neutralidade/regime.
// - 1e-6: "g praticamente zero" no bloco NEUTRALIDADE (g=0) — LIMIAR DIFERENTE do 1e-9 abaixo,
//   nao e' o mesmo numero reusado com nomes diferentes (conferido linha a linha no vendor).
// - 1e-9: aparece em TRES lugares com o MESMO valor literal (nao o mesmo lugar): a margem do
//   teto de Damodaran (`gp > teto + 1e-9`), a guarda "g genuinamente != 0" antes do ECO de
//   deriva do medio (`abs(g) > 1e-9`, diag_firm/diag_eq — DIFERENTE do 1e-6 do paragrafo
//   anterior), e o teste de caixa~0 em diag_eq (`abs(caixa) > 1e-9` / `caixa < -1e-9`).
const TOL_NEUTRALIDADE = 5e-4;
const TOL_G_ZERO = 1e-6;
const TOL_EPS = 1e-9;
const FAIXA_SENSIBILIDADE_KE_GP = 0.02; // diag_eq: 0 < (ke - gp) < 0.02 (2 p.p., hardcoded no vendor)

// Chaves de diagnosticosFirm/diagnosticosEquity/_guardasDamodaranChaves — os valores tem de
// concordar, byte a byte, com o campo "chave" de diagnosticos_chaves.json (o harness classifica
// cada mensagem do motor por PREFIXO e compara a lista de chaves resultante contra esta lista).
const CHAVE = {
  FIRM_CONVENCAO_BOOK: 'firm_convencao_book',
  FIRM_CONFLACAO_SEM_ROIC_BOOK: 'firm_conflacao_sem_roic_book',
  FIRM_REGIME_DECLARADO_ROIC_TV: 'firm_regime_declarado_roic_tv',
  FIRM_NOTA_COLAPSO_GORDON: 'firm_nota_colapso_gordon',
  FIRM_RIR: 'firm_rir',
  FIRM_ALERTA_RIR_EXCEDE_100: 'firm_alerta_rir_excede_100',
  FIRM_ALERTA_ROIC_ABAIXO_WACC: 'firm_alerta_roic_abaixo_wacc',
  FIRM_ALERTA_CONFLACAO_B01: 'firm_alerta_conflacao_b01',
  FIRM_CONVENCAO_CONDICIONADA_B01: 'firm_convencao_condicionada_b01',
  FIRM_SUB_ALERTA_B01_MEDIO: 'firm_sub_alerta_b01_medio',
  FIRM_ECO_DERIVA_MEDIO: 'firm_eco_deriva_medio',
  FIRM_ATENCAO_ROIC_WACC_BOOK_DIVERGE: 'firm_atencao_roic_wacc_book_diverge',
  FIRM_NEUTRALIDADE_IDENTIDADE: 'firm_neutralidade_identidade',
  FIRM_NEUTRALIDADE_G0_GORDON: 'firm_neutralidade_g0_gordon',
  FIRM_NEUTRALIDADE_G0_CONVERGENCIA: 'firm_neutralidade_g0_convergencia',
  FIRM_ATENCAO_G0_BOOK: 'firm_atencao_g0_book',
  EQ_CONVENCAO_BOOK: 'eq_convencao_book',
  EQ_CONFLACAO_SEM_ROE_BOOK: 'eq_conflacao_sem_roe_book',
  EQ_ECO_DERIVA_MEDIO: 'eq_eco_deriva_medio',
  EQ_POLITICA_CAIXA_CONTINUA: 'eq_politica_caixa_continua',
  EQ_POLITICA_CAIXA_ENCERRA: 'eq_politica_caixa_encerra',
  EQ_REGIME_DECLARADO_ROE_TV: 'eq_regime_declarado_roe_tv',
  EQ_NOTA_COLAPSO_GORDON: 'eq_nota_colapso_gordon',
  EQ_RETENCAO: 'eq_retencao',
  EQ_PAYOUT_ZERO_NAO_INFORMATIVO: 'eq_payout_zero_nao_informativo',
  EQ_LIMITACAO_C2_KE_FIXO: 'eq_limitacao_c2_ke_fixo',
  EQ_ALERTA_SENSIBILIDADE_KE_GP: 'eq_alerta_sensibilidade_ke_gp',
  EQ_DOMINIO_NDE_MAIOR_GDE: 'eq_dominio_nde_maior_gde',
  EQ_ALERTA_GROE_EXCEDE_100: 'eq_alerta_groe_excede_100',
  EQ_ALERTA_ROE_ABAIXO_KE: 'eq_alerta_roe_abaixo_ke',
  EQ_ALERTA_CONFLACAO_B01: 'eq_alerta_conflacao_b01',
  EQ_CONVENCAO_CONDICIONADA_B01: 'eq_convencao_condicionada_b01',
  EQ_SUB_ALERTA_B01_MEDIO: 'eq_sub_alerta_b01_medio',
  EQ_ATENCAO_ROE_KE_BOOK_DIVERGE: 'eq_atencao_roe_ke_book_diverge',
  EQ_NEUTRALIDADE_BOOK_CLEAN_SURPLUS: 'eq_neutralidade_book_clean_surplus',
  EQ_NEUTRALIDADE_IDENTIDADE_CAIXA0: 'eq_neutralidade_identidade_caixa0',
  EQ_ATENCAO_FCFE_NAO_BOOK: 'eq_atencao_fcfe_nao_book',
  EQ_NEUTRALIDADE_G0_GORDON: 'eq_neutralidade_g0_gordon',
  EQ_NEUTRALIDADE_G0_CONVERGENCIA: 'eq_neutralidade_g0_convergencia',
  EQ_ATENCAO_G0_BOOK: 'eq_atencao_g0_book',
  DAMODARAN_ALERTA_ANCORA_MACRO: 'damodaran_alerta_ancora_macro',
  DAMODARAN_ANCORA_OK: 'damodaran_ancora_ok',
  DAMODARAN_PREMISSA_NAO_ANCORADA: 'damodaran_premissa_nao_ancorada',
  COERENCIA_ECO_INTENSIDADE_CAPITAL: 'coerencia_eco_intensidade_capital',
};

// _guardasDamodaranChaves espelha _guardas_damodaran (justos.py:348-379) — SO' a Guarda 1
// (ancora macro do gp). A Guarda 2 ("MOEDA/REGIME NAO DECLARADOS", `if not moeda:`) e'
// inalcancavel pelo wrapper — mas NAO porque `moeda` seja campo "obrigatorio" (obrigatorio, antes
// do F1, so' queria dizer presente e nao-nulo: `moeda: ""` passava por `_validar_campos_de_topo`
// normalmente e chegava vazia ao motor mesmo assim, porque `motor.py:argv_para` descarta o campo
// por truthiness — `if moeda:` — e a Guarda 2 disparava de verdade; achado F1 da revisao final,
// fatia 4C, verificado por execucao). Inalcancavel de fato porque `caso._validar_moeda` (F1) agora
// GARANTE `moeda` como texto nao-vazio no gate, antes de qualquer chamada ao motor — e' esse
// contrato, nao a mera presenca da chave, que torna `moeda` sempre truthy em `argv_para` e a
// Guarda 2 sempre inalcancavel por este caminho. "nao espelhe".
// `gp`/`rf` ja' chegam em FRACAO (rf convertido por `pct()` no chamador, como o handler faz:
// `rf=None if getattr(a,'rf',None) is None else a.rf/100`).
function _guardasDamodaranChaves(tv, gp, rfFracao, moeda) {
  const chaves = [];
  const tvC = tvCanon(tv);
  const regimeReal = !!moeda && moeda.toLowerCase().endsWith('-real');
  if (tvC === 'gordon' && gp && gp > 0) {
    let teto;
    if (rfFracao !== null) {
      teto = regimeReal ? Math.min(rfFracao, 0.03) : rfFracao;
    } else if (regimeReal) {
      teto = 0.03;
    } else {
      teto = null;
    }
    if (teto !== null) {
      if (gp > teto + TOL_EPS) {
        chaves.push(CHAVE.DAMODARAN_ALERTA_ANCORA_MACRO);
      } else {
        chaves.push(CHAVE.DAMODARAN_ANCORA_OK);
      }
    } else {
      chaves.push(CHAVE.DAMODARAN_PREMISSA_NAO_ANCORADA);
    }
  }
  return chaves;
}

// diagnosticosFirm espelha diag_firm (justos.py:513-602) + a identidade 4 de coerencia_vetor
// (382-510, "d×intensidade de capital" — a UNICA alcancavel pelo wrapper nesta rota; ver o
// comentario da secao acima) + _guardasDamodaranChaves — na MESMA ordem de concatenacao que o
// handler `ev` usa (`diagnosticos = diag_firm(...) + coerencia_vetor(...)[0]`, e diag_firm
// termina retornando _guardas_damodaran): diag_firm, DEPOIS guardas, DEPOIS coerencia.
//
// `premissas` chega em PONTOS PERCENTUAIS (convencao do caso, como precificarCelula) — reusa
// premissasParaNucleo/RENOMEIA_FIRM (secao WRAPPER acima) para o MESMO colapso null->ausencia e
// a MESMA conversao percentual->fracao que o resto do wrapper ja' usa. `rf` chega em PONTOS
// PERCENTUAIS tambem (convencao de `mercado.rf`), convertido aqui com `pct()`.
function diagnosticosFirm(premissas, moeda, rf) {
  // F2 (revisao final, fatia 4C): um motor que recusa (avaliar_dominios_cli, ANTES de qualquer
  // handler) nao emite diagnostico NENHUM — ver o comentario de dominioCliRecusa, secao WRAPPER
  // acima. Sem esta guarda, um wacc/ke/n/g/gp/g1/g2 fora do dominio produzia uma lista CHEIA de
  // chaves ao lado de um numero que precificarCelula/precificarRampa (acima) ja recusam — o
  // laboratorio mostraria diagnostico junto de preco ausente.
  if (dominioCliRecusa(premissas)) {
    return [];
  }
  const nucleo = premissasParaNucleo(premissas, RENOMEIA_FIRM);
  const g = nucleo.g;
  const roic = nucleo.roic;
  const w = nucleo.w;
  const n = nucleo.n;
  const tv = tvCanon('tv' in nucleo ? nucleo.tv : 'book');
  const roicBook = 'roic_book' in nucleo ? nucleo.roic_book : null;
  const roicTv = 'roic_tv' in nucleo ? nucleo.roic_tv : null;
  const gp = 'gp' in nucleo ? nucleo.gp : 0.0;
  const rfFracao = pct(rf);

  const chaves = [];
  if (tv === 'book') {
    chaves.push(CHAVE.FIRM_CONVENCAO_BOOK);
    if (roicBook === null) {
      chaves.push(CHAVE.FIRM_CONFLACAO_SEM_ROIC_BOOK);
    }
  }
  if (tv === 'gordon' && roicTv !== null) {
    if (roicTv < w - TOL_NEUTRALIDADE) {
      chaves.push(CHAVE.FIRM_REGIME_DECLARADO_ROIC_TV);
    } else if (Math.abs(roicTv - w) < TOL_NEUTRALIDADE) {
      chaves.push(CHAVE.FIRM_NOTA_COLAPSO_GORDON);
    }
  }
  const rir = g / roic;
  chaves.push(CHAVE.FIRM_RIR);
  if (rir > 1) {
    chaves.push(CHAVE.FIRM_ALERTA_RIR_EXCEDE_100);
  }
  if (roic < w && g > 0) {
    chaves.push(CHAVE.FIRM_ALERTA_ROIC_ABAIXO_WACC);
  }
  if (roic < w && tv === 'book') {
    if (roicBook === null) {
      chaves.push(CHAVE.FIRM_ALERTA_CONFLACAO_B01);
    } else {
      chaves.push(CHAVE.FIRM_CONVENCAO_CONDICIONADA_B01);
      if (roicBook < w) {
        chaves.push(CHAVE.FIRM_SUB_ALERTA_B01_MEDIO);
      }
    }
  }
  if (tv === 'book' && roicBook !== null && Math.abs(roicBook - roic) >= TOL_NEUTRALIDADE
      && Math.abs(g) > TOL_EPS) {
    const icN = (1 + g) * (1.0 / roicBook - 1.0 / roic) + (1 + g) ** (n + 1) / roic;
    if (icN > 0) {
      chaves.push(CHAVE.FIRM_ECO_DERIVA_MEDIO);
    }
  }
  if (Math.abs(roic - w) < TOL_NEUTRALIDADE) {
    if (tv === 'book' && roicBook !== null && Math.abs(roicBook - w) >= TOL_NEUTRALIDADE) {
      chaves.push(CHAVE.FIRM_ATENCAO_ROIC_WACC_BOOK_DIVERGE);
    } else {
      chaves.push(CHAVE.FIRM_NEUTRALIDADE_IDENTIDADE);
    }
  }
  if (Math.abs(g) < TOL_G_ZERO) {
    if (tv === 'gordon') {
      chaves.push(CHAVE.FIRM_NEUTRALIDADE_G0_GORDON);
    } else if (tv === 'convergencia') {
      chaves.push(CHAVE.FIRM_NEUTRALIDADE_G0_CONVERGENCIA);
    } else {
      chaves.push(CHAVE.FIRM_ATENCAO_G0_BOOK);
    }
  }
  chaves.push(..._guardasDamodaranChaves(tv, gp, rfFracao, moeda));

  // coerencia_vetor, identidade 4 ("d×intensidade de capital", justos.py:486-503): precisa de
  // roic/d/tax, os TRES sempre presentes na rota firm (PREMISSAS_OBRIGATORIAS_FIRM inclui roic/
  // da/tax). `ebitda_ic` (o unico input que ramificaria para a mensagem INCOERENCIA em vez do
  // ECO) nunca e' exposto pelo wrapper (decisao da 3A) — por isso so' o ramo ECO existe aqui; o
  // ramo INCOERENCIA nao tem chave em diagnosticos_chaves.json de proposito (inalcancavel).
  const d = nucleo.d;
  const tax = nucleo.t;
  if ((1 - d) * (1 - tax) > 0) {
    chaves.push(CHAVE.COERENCIA_ECO_INTENSIDADE_CAPITAL);
  }

  return chaves;
}

// diagnosticosEquity espelha diag_eq (justos.py:604-731) + _guardasDamodaranChaves, na mesma
// ordem de concatenacao do handler `pe`. coerencia_vetor NAO contribui nenhuma chave nesta rota:
// as quatro identidades exigem, cada uma, pelo menos um de {roic, w, kd, tax} ou
// `rir_observado` — nenhum desses nomes esta em PREMISSAS_EQUITY (caso.py), e nenhum vira flag
// pelo caminho do wrapper; confirmado rodando o motor.rodar real com o vetor equity completo
// (nenhuma mensagem "[vetor]" jamais aparece — ver o relatorio desta task).
//
// `gde`/`nde`: resolvidos com o MESMO default 0.0 que o handler `pe` aplica ANTES de chamar
// diag_eq (`gde, nde = pc(a.gde) or 0, pc(a.nde) or 0` — nao o default proprio de diag_eq, que
// nunca roda porque o handler ja' preencheu as duas variaveis antes da chamada).
function diagnosticosEquity(premissas, moeda, rf) {
  // F2 (revisao final, fatia 4C) — mesma razao de diagnosticosFirm acima.
  if (dominioCliRecusa(premissas)) {
    return [];
  }
  const nucleo = premissasParaNucleo(premissas, {});
  const g = nucleo.g;
  const roe = nucleo.roe;
  const ke = nucleo.ke;
  const gde = 'gde' in nucleo ? nucleo.gde : 0;
  const nde = 'nde' in nucleo ? nucleo.nde : 0;
  const n = nucleo.n;
  const tv = tvCanon('tv' in nucleo ? nucleo.tv : 'book');
  const roeBook = 'roe_book' in nucleo ? nucleo.roe_book : null;
  const roeTv = 'roe_tv' in nucleo ? nucleo.roe_tv : null;
  const politicaTv = 'politica_tv' in nucleo ? nucleo.politica_tv : 'continua';
  const gp = 'gp' in nucleo ? nucleo.gp : 0.0;
  const rfFracao = pct(rf);
  const caixa = gde - nde;

  const chaves = [];
  if (tv === 'book') {
    chaves.push(CHAVE.EQ_CONVENCAO_BOOK);
    if (roeBook === null) {
      chaves.push(CHAVE.EQ_CONFLACAO_SEM_ROE_BOOK);
    } else if (Math.abs(roeBook - roe) >= TOL_NEUTRALIDADE && Math.abs(g) > TOL_EPS) {
      const eN = (1 + g) * (1.0 / roeBook - 1.0 / roe) + (1 + g) ** (n + 1) / roe;
      if (eN > 0) {
        chaves.push(CHAVE.EQ_ECO_DERIVA_MEDIO);
      }
    }
  }
  if (tv === 'gordon' && roeTv !== null) {
    if (Math.abs(caixa) > TOL_EPS && gp > 0) {
      chaves.push(politicaTv === 'continua' ? CHAVE.EQ_POLITICA_CAIXA_CONTINUA : CHAVE.EQ_POLITICA_CAIXA_ENCERRA);
    }
    if (roeTv < ke - TOL_NEUTRALIDADE) {
      chaves.push(CHAVE.EQ_REGIME_DECLARADO_ROE_TV);
    } else if (Math.abs(roeTv - ke) < TOL_NEUTRALIDADE) {
      chaves.push(CHAVE.EQ_NOTA_COLAPSO_GORDON);
    }
  }
  const ret = g / roe;
  chaves.push(CHAVE.EQ_RETENCAO);
  if (ret >= 0.95 && ret <= 1.0 + TOL_EPS) {
    chaves.push(CHAVE.EQ_PAYOUT_ZERO_NAO_INFORMATIVO);
  }
  if (Math.abs(caixa) > TOL_EPS) {
    chaves.push(CHAVE.EQ_LIMITACAO_C2_KE_FIXO);
  }
  if (tv === 'gordon' && roeTv !== null && (ke - gp) > 0 && (ke - gp) < FAIXA_SENSIBILIDADE_KE_GP) {
    chaves.push(CHAVE.EQ_ALERTA_SENSIBILIDADE_KE_GP);
  }
  if (caixa < -TOL_EPS) {
    chaves.push(CHAVE.EQ_DOMINIO_NDE_MAIOR_GDE);
  }
  if (ret > 1) {
    chaves.push(CHAVE.EQ_ALERTA_GROE_EXCEDE_100);
  }
  if (roe < ke && g > 0) {
    chaves.push(CHAVE.EQ_ALERTA_ROE_ABAIXO_KE);
  }
  if (roe < ke && tv === 'book') {
    if (roeBook === null) {
      chaves.push(CHAVE.EQ_ALERTA_CONFLACAO_B01);
    } else {
      chaves.push(CHAVE.EQ_CONVENCAO_CONDICIONADA_B01);
      if (roeBook < ke) {
        chaves.push(CHAVE.EQ_SUB_ALERTA_B01_MEDIO);
      }
    }
  }
  if (Math.abs(roe - ke) < TOL_NEUTRALIDADE) {
    if (tv === 'book' && roeBook !== null && Math.abs(roeBook - ke) >= TOL_NEUTRALIDADE) {
      chaves.push(CHAVE.EQ_ATENCAO_ROE_KE_BOOK_DIVERGE);
    } else if (tv === 'book') {
      chaves.push(CHAVE.EQ_NEUTRALIDADE_BOOK_CLEAN_SURPLUS);
    } else if (Math.abs(caixa) < TOL_EPS) {
      chaves.push(CHAVE.EQ_NEUTRALIDADE_IDENTIDADE_CAIXA0);
    } else {
      chaves.push(CHAVE.EQ_ATENCAO_FCFE_NAO_BOOK);
    }
  }
  if (Math.abs(g) < TOL_G_ZERO) {
    if (tv === 'gordon') {
      chaves.push(CHAVE.EQ_NEUTRALIDADE_G0_GORDON);
    } else if (tv === 'convergencia') {
      chaves.push(CHAVE.EQ_NEUTRALIDADE_G0_CONVERGENCIA);
    } else {
      chaves.push(CHAVE.EQ_ATENCAO_G0_BOOK);
    }
  }
  chaves.push(..._guardasDamodaranChaves(tv, gp, rfFracao, moeda));

  return chaves;
}

// `args` de um problema `tipo: "diag"` esta' em snake_case (contrato do brief task-4c-2):
// `{"rota": "firm"|"equity", "premissas": {...}, "moeda": str, "rf": float|null}`. Sem os campos
// de compatibilidade do SOLVER, `resolverDiag` nao teria como conviver na mesma fixture que
// test_paridade_solver_js.py le sem filtrar por tipo — mesma razao de resolverAlvo/resolverRampa
// acima.
function resolverDiag(item) {
  const a = item.args;
  const chaves = a.rota === 'firm'
    ? diagnosticosFirm(a.premissas, a.moeda, a.rf ?? null)
    : diagnosticosEquity(a.premissas, a.moeda, a.rf ?? null);
  return { id: item.id, chaves, ...CAMPOS_SOLVER_VAZIOS };
}

// ============================================================================
// DEGRAU (Fatia D, Task 2) — espelha fator_h/rentab_pos_degrau/desconto_transicao/
// valor_transicionado (justos.py:792-830) e o calculo por nivel do handler `elif a.cmd ==
// 'degrau':` (justos.py ~2531-2587), atras de avaliar.py:precificar_degrau +
// _aplicar_degrau_ao_cenario. Paridade contra o WRAPPER (mesmo harness/fixture da secao WRAPPER
// acima) — a forma que este espelho reproduz e' a de `resultados.json`
// (cenarios.<nome>.{valor,sem_degrau,vs_preco,degrau}), NUNCA a saida crua do subcomando
// `degrau`: `precificarDegrau` abaixo roda as DUAS pernas que o wrapper roda por cenario (a rota
// P/L via `pe()` direto — precificarCelula nao serve aqui porque nao expoe Equity/PL_fwd, so'
// preco_acao/PL_curr — e o handler `degrau`, via `nivelDegrau`) sobre o MESMO `premissas` de
// cenario, D2 (so' a rota equity tem degrau: o motor fecha o preco sozinho via --vpa/--fx).
//
// Duas correcoes ao plano desta task (ver o relatorio para o texto completo):
// 1) ALERTA_CONVENCAO_BOOK NAO e' espelhado. O Gate 3 da Task 1 (D6, caso.py:_validar_degrau)
//    recusa 'tv'='book' sem 'roe_book' sempre que 'degrau' esta' no caso — o mesmo alerta que o
//    handler emitiria fica inalcancavel pelo caminho do wrapper (mesma logica de
//    `coerencia_vetor` so' contribuir uma chave na rota firm, secao DIAGNOSTICOS acima: o
//    vocabulario do CASO decide o que e' alcancavel, nao a assinatura mais ampla do motor).
//    [onda de correcao da revisao final da 5C, F3] O laboratorio edita premissas SEM passar pelo
//    gate, e o `select` da convencao terminal alcanca exatamente essa combinacao. A
//    inalcancabilidade continua valendo porque a FACHADA (espelho_fachada.js) aplica a D6 ao caso
//    editado e recusa o cenario, com o motivo nomeado, antes de chamar precificarDegrau.
// 2) `dominioCliRecusa` roda no TOPO de `precificarDegrau` — mesma disciplina das outras quatro
//    entradas de wrapper deste arquivo (precificarCelula, precificarRampa, diagnosticosFirm,
//    diagnosticosEquity): o motor recusa por dominio ANTES de qualquer handler
//    (avaliar_dominios_cli), e as DUAS pernas do degrau leem os MESMOS g/ke/gp/n de `premissas`
//    — uma checagem no topo cobre as duas.
//
// ALERTA/ALERTA_RiR: o wrapper real copia a PROSA do motor verbatim para resultados.json
// (avaliar.py: `degrau_cenario["ALERTA"] = nivel_alvo["ALERTA"]`) — mas, pela MESMA convencao que
// aviso_colheita/aviso_delator/aviso_gp ja' usam na secao RAMPA acima (so' a PRESENCA importa, a
// prosa fica fora do escopo — ver o comentario la'), `nivelDegrau` abaixo escreve `true`, nao a
// frase do motor; o harness de paridade compara so' a presenca das duas chaves.
// ============================================================================

// [fatia 5C, item 5, task 3] A CHAVE publica de cada alerta do degrau — espelha
// `avaliar.py:_ALERTAS_DEGRAU_ORDEM`. O motor publica ALERTA/ALERTA_RiR como prosa sem chave; o
// wrapper (a camada que conhece o motor) da a chave e publica `degrau.diagnosticos_chaves`: as
// chaves cujo campo esta' presente no nivel-alvo, na ORDEM deste array — mesma convencao de
// presenca de AVISOS_RAMPA. tests/test_paridade_wrapper_js.py compara a lista exata dos dois lados,
// e tests/test_espelho_fachada_js.py prende a ordem com os dois alertas acesos juntos.
const ALERTAS_DEGRAU = [['ALERTA', 'degrau_alerta'], ['ALERTA_RiR', 'degrau_alerta_rir']];

// [onda de correcao da revisao final da 5C, F1] A DIVERGENCIA DE BASE do degrau como chave —
// espelha `avaliar.py:_LIMIAR_DIVERGENCIA_DE_BASE_PCT`/`_CHAVE_DIVERGENCIA_DE_BASE`, a fonte
// numerica UNICA do limiar (o catalogo de apresentacao deixou de carregar o numero). Copia
// travada contra a fonte por igualdade em tests/test_paridade_wrapper_js.py (limiar e chave), e
// pelo comportamento na paridade do degrau: `degrau.diagnosticos_chaves` compara por igualdade
// exata, e a fixture tem divergencias dentro e acima do limiar, nos dois sinais. A chave sai
// DEPOIS das dos alertas, quando o MODULO da divergencia passa do limiar — a regra do wrapper.
const LIMIAR_DIVERGENCIA_DE_BASE_PCT = 5.0;
const CHAVE_DIVERGENCIA_DE_BASE = 'degrau_divergencia_de_base';

// fator_h (justos.py 793-799): h = indice_atual / indice_alvo — indice_alvo <= 0 devolve NaN
// (guarda do nucleo; nunca alcancada pelo caminho do wrapper, que exige indice_alvo > 0 no gate).
function fatorH(indiceAtual, indiceAlvo) {
  if (indiceAlvo <= 0) return NaN;
  return indiceAtual / indiceAlvo;
}

// rentab_pos_degrau (justos.py 801-804): degrau ENTRA COMO RENTABILIDADE — g nunca aparece aqui.
function rentabPosDegrau(rentab, h, m = 1.0) {
  return rentab * (1 + (h - 1) * m);
}

// desconto_transicao (justos.py 806-825). Detalhe 1 do brief desta task: T fracionario recebe
// uma tranche PROPORCIONAL no ULTIMO periodo (nem uma soma inteira a mais, nem uma tranche
// cheia) — `n_full = int(T)` trunca (T = max(anos,0) >= 0 aqui, entao `Math.trunc` == `int()` do
// Python sobre um float nao-negativo: os dois cortam a parte fracionaria, sem arredondar). anos
// <= 0 devolve 1.0 (degrau instantaneo, sem desconto de transicao nenhum).
function descontoTransicao(custoCapital, anos, perfil = 'rampa') {
  const T = Math.max(anos, 0);
  if (T <= 0) return 1.0;
  if (custoCapital <= -1) return NaN;
  if (perfil === 'pontual') {
    return 1.0 / (1.0 + custoCapital) ** T;
  }
  const nFull = Math.trunc(T);
  const frac = T - nFull;
  let numer = 0;
  for (let t = 1; t <= nFull; t++) {
    numer += 1.0 / (1.0 + custoCapital) ** t;
  }
  if (frac > 1e-12) {
    numer += frac / (1.0 + custoCapital) ** T;
  }
  return numer / T;
}

// valor_transicionado (justos.py 827-829): o desconto incide SO' sobre o incremento
// (valorDegrau - valorBase) — a base nunca e' descontada. E' esta a linha que a prova de
// falseabilidade desta task muta (fator de captura sobre o valor INTEIRO, nao so' o incremento).
function valorTransicionado(valorBase, valorDegrau, custoCapital, anos, perfil = 'rampa') {
  const f = descontoTransicao(custoCapital, anos, perfil);
  return { valor: valorBase + (valorDegrau - valorBase) * f, f };
}

// nivelDegrau: UMA linha do laco `for alvo in alvos` do handler (justos.py ~2569-2587) — os
// argumentos ja' resolvidos (rent/custo/g/gde/nde/tv/roeTvKw/gp/roeBook/politicaTv/mm/baseV/
// anos/perfilTransicao/vpa/fx) vem de `precificarDegrau`, que os calcula UMA vez por chamada — o
// handler real tambem os calcula uma vez, fora do laco `for alvo`, nunca dentro dele.
function nivelDegrau({
  indiceAtual, alvo, rent, custo, g, n, gde, nde, tv, roeTvKw, gp, roeBook, politicaTv, mm,
  baseV, anos, perfilTransicao, vpa, fx,
}) {
  const h = fatorH(indiceAtual, alvo);
  const r2 = rentabPosDegrau(rent, h, mm);
  const m2 = pe({
    g, roe: r2, ke: custo, n, gde, nde, tv, roe_tv: roeTvKw, gp, roe_book: roeBook,
    politica_tv: politicaTv,
  });
  const v2 = m2 * r2;
  const { valor: vTr, f: fTr } = valorTransicionado(baseV, v2, custo, anos, perfilTransicao);

  const linha = {
    h: arredondarPy(h, 4),
    'rentabilidade_pos_%': arredondarPy(r2 * 100, 2),
    multiplo: arredondarPy(m2, 4),
    multiplo_x_rentab: arredondarPy(v2, 4),
    com_transicao: arredondarPy(vTr, 4),
    fator_transicao: arredondarPy(fTr, 4),
    perfil_transicao: perfilTransicao,
  };
  // `if a.vpa:` do Python e' um teste de VERDADE, nao "is not None" — 0/None ficam SEM
  // 'preco_acao' na linha, do mesmo jeito que o handler real nunca escreve a chave nesse caso.
  if (vpa) {
    linha.preco_acao = arredondarPy((vTr * vpa) / (fx || 1.0), 2);
  }
  if (r2 > Math.max(2.0 * custo, 0.30)) {
    linha.ALERTA = true;
  }
  if (g !== null && g / r2 > 1) {
    linha.ALERTA_RiR = true;
  }
  return linha;
}

// precificarDegrau espelha avaliar.py:precificar_degrau + _aplicar_degrau_ao_cenario — as DUAS
// pernas (P/L via `pe()` direto; e o handler `degrau`, via nivelDegrau acima) sobre o MESMO
// `premissas` de cenario. `blocoDegrau` chega em valores CRUS (indice_atual/indice_alvo/anos/
// vpa/fx sao razao/moeda/ano, NUNCA passam por pc() — detalhe 3 do brief); `mValor` chega em %,
// como o resto de `caso.json`.
function precificarDegrau({
  premissas, metricaValor, acoes, precoValor, blocoDegrau, mValor,
}) {
  // Correcao 2 ao plano (ver cabecalho da secao): mesma guarda das outras quatro entradas de
  // wrapper deste arquivo, aplicada aqui porque as duas pernas abaixo leem os MESMOS g/ke/gp/n.
  if (dominioCliRecusa(premissas)) {
    return { recusado: true };
  }
  // F3 (mesma razao de precificarCelula, secao WRAPPER acima): 'tv' null colapsaria para
  // ausencia em premissasParaNucleo e pe() aplicaria o SEU default ('book'), inventando um preco
  // onde o motor recusa — '--tv' e' obrigatorio no subparser 'degrau' tambem.
  if (premissas.tv === null) {
    return { recusado: true };
  }

  const nucleo = premissasParaNucleo(premissas, {});
  // gde/nde: mesmo reparo de default (F1) que precificarCelula ja' aplica na rota equity — ver o
  // comentario la'. 'degrau' e' rota equity sempre (D2), entao o mesmo reparo vale aqui.
  if (!('gde' in nucleo)) nucleo.gde = 0;
  if (!('nde' in nucleo)) nucleo.nde = 0;

  // ---- perna SEM degrau (rota P/L: precificar_equity + _monta_cenario — "sem_degrau" intacto)
  // Nao reusa precificarCelula: aquela funcao so' devolve {valor: preco_acao, multiplo: PL_curr}
  // — nao expoe nem o `m` cru (necessario para PL_fwd) nem `Equity` (necessario aqui porque
  // `cenario_montado["valor"]` da rota equity e' {"Equity":..., "preco_acao":...}, nao so' o
  // preco — ao contrario da celula de sensibilidade, que so' precisa do preco).
  const mSemDegrau = pe(nucleo);
  if (!Number.isFinite(mSemDegrau)) {
    return { recusado: true };
  }
  const plCurr = arredondarPy(mSemDegrau, 4);
  // PL_fwd = round(m/(1+g), 4) sobre o `m` CRU (justos.py:1970) — nao sobre PL_curr arredondado.
  const plFwd = arredondarPy(mSemDegrau / (1 + nucleo.g), 4);
  const eqBrutoSemDegrau = mSemDegrau * metricaValor;
  const equitySemDegrau = arredondarPy(eqBrutoSemDegrau, 2);
  const precoSemDegrau = arredondarPy(eqBrutoSemDegrau / acoes, 2);

  // ---- perna DEGRAU (handler `elif a.cmd == 'degrau':`, justos.py ~2531-2587) ----
  const rent = nucleo.roe;
  const custo = nucleo.ke;
  const g = nucleo.g;
  const n = nucleo.n;
  const gde = nucleo.gde;
  const nde = nucleo.nde;
  const tv = 'tv' in nucleo ? nucleo.tv : 'book';
  const roeBook = 'roe_book' in nucleo ? nucleo.roe_book : null;
  const roeTvDeclarado = 'roe_tv' in nucleo ? nucleo.roe_tv : null;
  // Detalhe 2 do brief desta task: roe_tv AUSENTE — ou declarado como 0 — vira a rentabilidade
  // BASE (`pc(roe_tv) or rent`, justos.py:2537). `||` do JS reproduz esse `or` do Python
  // EXATAMENTE aqui: as duas linguagens tratam 0/None(null) como falsy e qualquer outro numero
  // (inclusive negativo) como truthy — NAO e' o mesmo risco de `??` que o cabecalho do arquivo
  // descreve para tv/gp/politica_tv (aqueles distinguem ausencia de null explicito; aqui o
  // PROPRIO Python usa `or`, entao colapsar os dois em falsy e' o comportamento CORRETO a
  // espelhar, nao um desvio).
  const roeTvKw = roeTvDeclarado || rent;
  const gp = 'gp' in nucleo ? nucleo.gp : 0.0;
  const politicaTv = 'politica_tv' in nucleo ? nucleo.politica_tv : 'continua';

  const baseM = pe({
    g, roe: rent, ke: custo, n, gde, nde, tv, roe_tv: roeTvKw, gp, roe_book: roeBook,
    politica_tv: politicaTv,
  });
  const baseV = baseM * rent;

  const indiceAtual = blocoDegrau.indice_atual;
  const anos = blocoDegrau.anos;
  const perfilTransicao = blocoDegrau.perfil_transicao || 'rampa';
  const vpa = blocoDegrau.vpa;
  const fx = blocoDegrau.fx;
  // 'm' chega em % (detalhe 3 do brief) — SEMPRE presente pelo caminho do wrapper
  // ('degrau.m' e' obrigatorio por cenario, caso.py), mas o handler real tem um `else 1.0` para
  // uso direto da CLI sem '--m' (a.m tambem defaulta 100.0 no argparse — na pratica morto pelo
  // caminho do wrapper, mas espelhado aqui por completude, sem custo nenhum).
  const mm = (mValor === null || mValor === undefined) ? 1.0 : pct(mValor);

  const argsNivel = {
    indiceAtual, rent, custo, g, n, gde, nde, tv, roeTvKw, gp, roeBook, politicaTv, mm,
    baseV, anos, perfilTransicao, vpa, fx,
  };
  const nivelAlvo = nivelDegrau({ ...argsNivel, alvo: blocoDegrau.indice_alvo });
  const nivelBase = nivelDegrau({ ...argsNivel, alvo: indiceAtual }); // h=1 por construcao (D8)

  // _exigir_valor (avaliar.py) recusa quando o motor devolve 'preco_acao' ausente/null para
  // QUALQUER um dos dois niveis — 'preco_acao' e' o campo mais a jusante de cada nivel (depende
  // de h/r2/m2/v2/v_tr), entao checar so' os dois 'preco_acao' cobre, por construcao, qualquer
  // NaN nascido mais cedo na cadeia DESSE MESMO nivel (r2<=0, m2 NaN, etc.) — Number.isFinite
  // sobre `undefined` (chave ausente, vpa falsy) tambem e' `false`, mesma recusa.
  if (!Number.isFinite(nivelAlvo.preco_acao) || !Number.isFinite(nivelBase.preco_acao)) {
    return { recusado: true };
  }

  const precoComDegrau = nivelAlvo.preco_acao;
  const precoBaseH1 = nivelBase.preco_acao;

  const degrauCenario = {
    h: nivelAlvo.h,
    'rentabilidade_pos_%': nivelAlvo['rentabilidade_pos_%'],
    multiplo: nivelAlvo.multiplo,
    multiplo_x_rentab: nivelAlvo.multiplo_x_rentab,
    com_transicao: nivelAlvo.com_transicao,
    fator_transicao: nivelAlvo.fator_transicao,
    perfil_transicao: nivelAlvo.perfil_transicao,
    m: mValor,
    // D8: comparacao entre DOIS outputs do motor (aqui, dois outputs deste MESMO espelho) — NAO
    // arredondada (detalhe do plano), sobre os dois precos JA' arredondados por nivel/pela perna
    // sem-degrau (arredondarPy acima), nunca sobre um v_tr cru.
    'divergencia_de_base_%': (precoBaseH1 / precoSemDegrau - 1) * 100,
  };
  if ('ALERTA' in nivelAlvo) degrauCenario.ALERTA = true;
  if ('ALERTA_RiR' in nivelAlvo) degrauCenario.ALERTA_RiR = true;
  // [fatia 5C, task 3] as chaves dos alertas presentes, na ordem de ALERTAS_DEGRAU (acima) — o
  // campo que `_aplicar_degrau_ao_cenario` publica ao lado da prosa.
  degrauCenario.diagnosticos_chaves = ALERTAS_DEGRAU
    .filter(([campo]) => campo in nivelAlvo)
    .map(([, chave]) => chave);
  // [onda de correcao da 5C, F1] e a da divergencia de base acima do limiar (ver
  // LIMIAR_DIVERGENCIA_DE_BASE_PCT acima) — `_chaves_do_degrau`, do lado Python.
  if (Math.abs(degrauCenario['divergencia_de_base_%']) > LIMIAR_DIVERGENCIA_DE_BASE_PCT) {
    degrauCenario.diagnosticos_chaves.push(CHAVE_DIVERGENCIA_DE_BASE);
  }

  return {
    recusado: false,
    valor: { preco_acao: precoComDegrau },
    sem_degrau: {
      valor: { Equity: equitySemDegrau, preco_acao: precoSemDegrau },
      multiplos: { PL_curr: plCurr, PL_fwd: plFwd },
    },
    vs_preco: { upside: precoComDegrau / precoValor - 1 },
    degrau: degrauCenario,
  };
}

// `args` de um problema `tipo: "degrau"` esta' em snake_case (contrato do brief desta task):
// {"premissas":{...}, "metrica_valor":float, "acoes":float, "preco_valor":float,
//  "bloco_degrau":{"indice_atual":float,"indice_alvo":float,"anos":float,
//                  "perfil_transicao":str,"vpa":float,"fx":float|null}, "m_valor":float}.
// Carrega CAMPOS_SOLVER_VAZIOS pela MESMA razao de resolverAlvo/resolverRampa/resolverDiag acima
// (test_paridade_solver_js.py le a fixture inteira sem filtrar por tipo).
function resolverDegrau(item) {
  const a = item.args;
  const resultado = precificarDegrau({
    premissas: a.premissas, metricaValor: a.metrica_valor, acoes: a.acoes,
    precoValor: a.preco_valor, blocoDegrau: a.bloco_degrau, mValor: a.m_valor,
  });
  return { id: item.id, ...resultado, ...CAMPOS_SOLVER_VAZIOS };
}

// ============================================================================
// CONSERVACAO DE CAPITAL (fatia 5F, Task 3) — espelha `conservacao_capital` (justos.py:173-193),
// a verificacao executavel da §11.1b que o handler `ev` roda com --capex-total/--dwc/--ebitda
// (justos.py:1925-1931), e a chave que `avaliar.py:_conservacao_publicada` da ao alerta.
// Paridade contra o WRAPPER (mesmo harness/fixture da secao WRAPPER acima): o lado Python roda
// `avaliar.precificar_firm` com as flags, e o numero publicado e' o do motor atravessando a CLI.
//
// `d`, `t`, `g` e `roic` chegam em PONTOS PERCENTUAIS, como o caso e a CLI os recebem — a conversao
// e' a da CLI (`pc`, justos.py:1886), feita aqui; `capexTotal`, `dwc` e `ebitda` em moeda, sem
// conversao. Os cinco numeros saem com o arredondamento do motor (4 casas; 2 no `gap_%`), e o limiar
// e' o do motor (10% do capital consumido) — nenhum limiar do Fleet aqui. `ALERTA` vira `true`
// (so' a presenca importa, a convencao de ALERTAS_DEGRAU), e `diagnosticos_chaves` e' a lista que o
// wrapper publica.
//
// Truthiness do Python: `g / roic if roic else nan` e `gap / consumido if consumido else nan`
// testam "!= 0.0" — `!== 0` reproduz, inclusive para NaN (ver `identificacao`, acima).
// ============================================================================

const LIMIAR_CONSERVACAO_CAPITAL = 0.10;
const ALERTAS_CONSERVACAO = [['ALERTA', 'conservacao_capital_nao_fecha']];

function conservacaoCapital(capexTotal, dwc, ebitda, d, t, g, roic) {
  const dF = pct(d);
  const tF = pct(t);
  const gF = pct(g);
  const roicF = pct(roic);
  const consumido = capexTotal + dwc;
  const nopat = ebitda * (1 - dF) * (1 - tF);
  const rir = roicF !== 0 ? gF / roicF : NaN;
  const encargos = dF * ebitda + rir * nopat;
  const gap = consumido - encargos;
  const gapPct = consumido !== 0 ? gap / consumido : NaN;
  const saida = {
    capital_consumido: arredondarPy(consumido, 4),
    encargo_reposicao_d_x_EBITDA: arredondarPy(dF * ebitda, 4),
    encargo_crescimento_RiR_x_NOPAT: arredondarPy(rir * nopat, 4),
    gap: arredondarPy(gap, 4),
    'gap_%': arredondarPy(gapPct * 100, 2),
  };
  if (Math.abs(gapPct) > LIMIAR_CONSERVACAO_CAPITAL) saida.ALERTA = true;
  saida.diagnosticos_chaves = ALERTAS_CONSERVACAO
    .filter(([campo]) => campo in saida)
    .map(([, chave]) => chave);
  return saida;
}

// `args` de um problema `tipo: "conservacao"`: {"premissas": {...vetor firm, em ponto percentual...},
// "ebitda": float, "capex_total": float, "dwc": float}. Carrega CAMPOS_SOLVER_VAZIOS pela MESMA razao
// de resolverDiag/resolverDegrau acima.
function resolverConservacao(item) {
  const a = item.args;
  const p = a.premissas;
  return {
    id: item.id,
    conservacao: conservacaoCapital(a.capex_total, a.dwc, a.ebitda, p.da, p.tax, p.g, p.roic),
    ...CAMPOS_SOLVER_VAZIOS,
  };
}

// ============================================================================
// REVERSA (item 5, fatia I, task 1) — espelha o ramo `rev` de
// vendor/multiplos-justos/scripts/justos.py (linhas 2021-2300) MAIS o wrapper
// skills/er-valuation/scripts/reversa.py (_motivo_do_eixo, _identificacao_da_raiz,
// _resolucao, _beta_implicito, leitura_do_eixo, teto_do_crescimento_gratuito,
// limitacoes_da_leitura). Duas naturezas de risco, um so' caminho:
//
// 1) o RAMO `rev` do vendor e' ITERATIVO (solve_full, ver a secao SOLVER acima) e
//    decide por PREDICADO (crescente/monotona/bracket); a ordem das operacoes segue o
//    Python passo a passo, pela mesma razao daquela secao.
// 2) o WRAPPER e' classificacao: `leitura`/`resolucao` sao o que a aba le desde a 5F
//    (D2 daquela fatia) — e o que o comparador da fachada confronta.
//
// O que NAO entra aqui, por decisao D1/A3 do plano desta fatia: `sem_solucao`,
// `sugestao` (o TEXTO), `guardas_v9_4`, `premissas_fixadas`, `premissa_regime`,
// `nota_regime`, `nivel_implicito` (D11) e `iso` (D12) — prosa e subcomandos do motor
// que a tela nunca mostra. Onde o motor escreve uma FRASE que o wrapper traduz para
// codigo (`direcao` do cap -> `_MOTIVO_DO_CAP_POR_DIRECAO`; `posicao_na_banda` do beta
// -> `_POSICAO_POR_PALAVRAS`), este espelho decide o CODIGO pelo MESMO predicado e
// nunca monta a frase (D3) — a mesma disciplina de `AVISOS_RAMPA`, que publica `true`
// em vez do texto do aviso.
// ============================================================================

// reversa.py:RESOLVER_POR_EIXO — eixo declarado no caso -> variavel de `--resolver`,
// por rota. Copia da tabela do wrapper, nao uma reinterpretacao dela.
const RESOLVER_POR_EIXO = {
  custo_capital: { firm: 'wacc', equity: 'ke' },
  rentabilidade: { firm: 'roic', equity: 'roe' },
  crescimento: { firm: 'g', equity: 'g' },
  cap: { firm: 'cap', equity: 'cap' },
};

const EIXO_DO_CUSTO_DE_CAPITAL = 'custo_capital';
// reversa.py:EIXOS_PRIMARIOS — os unicos cujo `raizes_*` vazio aciona o teto.
const EIXOS_PRIMARIOS = ['rentabilidade', 'crescimento'];
// reversa.py:RENTABILIDADE_TERMINAL_INFINITA (em PONTO PERCENTUAL, como todo o vetor
// do caso — a CLI divide por 100 depois).
const RENTABILIDADE_TERMINAL_INFINITA = 1e6;
// reversa.py: as unidades da leitura, chaves de `catalogo.unidades`.
const UNIDADE_DA_RAIZ = 'pp';
const UNIDADE_DO_CAP = 'anos_fracionarios';
const UNIDADE_DA_CURVATURA = 'curvatura';
const UNIDADE_DO_BETA = 'beta';
// reversa.py:_PREFIXO_DO_INTERVALO — `identificacao()` chaveia o intervalo pela
// tolerancia (`intervalo_para_alvo_±1%`), e a leitura o acha por PREFIXO.
const PREFIXO_DO_INTERVALO = 'intervalo_para_alvo_±';
// justos.py:1775 (`--tol` default 1.0, convertido por `tol = (a.tol or 1.0)/100.0`) e
// justos.py:281/298 (`steps=800`). `reverter` nunca passa `--tol`.
const TOL_DA_REVERSA = 0.01;
const STEPS_DA_REVERSA = 800;
// justos.py, ramo `cap`: a serie e' valor(n) para n INTEIRO de 1 a 60.
const CAP_ANO_MINIMO = 1;
const CAP_ANO_MAXIMO = 60;

// Truthiness do Python, que `or` do vendor usa em `(r or 0.6)`, `(g or 0)`,
// `(k or 0.4)`, `(kw['gp'] or 0)` e `pc(a.gp) or 0.0`: ZERO tambem cai no
// alternativo, e NaN NAO cai (`nan or 0.6` e' `nan` em Python, porque NaN e'
// truthy la'). `||` do JS erraria no segundo caso — NaN e' falsy aqui. A
// diferenca nao e' teorica: `roic = 0` num vetor editado muda a faixa de busca
// de `g` de `(-0.60, 0.0)` para `(-0.60, 0.5994)`.
function ouPy(valor, alternativa) {
  return (valor === null || valor === undefined || valor === 0) ? alternativa : valor;
}

// `f'{x:.3f}'` do Python sobre um numero JA' arredondado a 3 casas por
// `arredondarPy` — a chave de `identificacao_por_raiz` (justos.py:2263). A chave
// em si nunca e' lida pela leitura (que consome `.values()`), mas o COLAPSO
// importa: duas raizes que formatam igual viram UMA entrada no dict do motor, e
// `leitura_do_eixo` recusa o par por comprimento (MotorFalhou). Reproduzir a
// chave e' reproduzir esse colapso.
function chaveDaIdentificacao(xFracao) {
  return arredondarPy(xFracao * 100, 3).toFixed(3) + '%';
}

// justos.py:2058-2065 — as faixas de busca `rngs`, DERIVADAS das outras premissas
// (decisao D2 do plano: funcao, nunca constante; congelar o objeto daria a raiz
// certa para o vetor original e a errada para o editado, que e' o caso de uso).
// `premissas` chega em PONTOS PERCENTUAIS (convencao de caso.json) e SEM a variavel
// resolvida, exatamente como `reverter` monta o vetor; a saida e' em FRACAO, que e'
// a unidade em que o solver trabalha. `--rir-externo` fica de fora (D2): nenhum
// caso o declara e o caso nao tem campo para ele.
function faixaDeBusca({ variavel, rota, premissas }) {
  const eq = rota === 'equity';
  const g = pct(premissas.g ?? null);
  const r = pct((eq ? premissas.roe : premissas.roic) ?? null);
  const k = pct((eq ? premissas.ke : premissas.wacc) ?? null);
  // `kw['gp']` do vendor ja' e' `pc(a.gp) or 0.0`; `rngs` le `(kw['gp'] or 0)`.
  const gp = ouPy(pct(premissas.gp ?? null), 0.0);
  const faixas = {
    g: [-0.60, Math.min(0.60, ouPy(r, 0.6) * 0.999)],
    roic: [Math.max(0.005, ouPy(g, 0) + 1e-4), 1.50],
    roe: [Math.max(0.005, ouPy(g, 0) + 1e-4), 1.50],
    ke: [Math.max(ouPy(gp, 0) + 1e-3, 0.005), 0.40],
    wacc: [Math.max(ouPy(gp, 0) + 1e-3, 0.005), 0.40],
    gp: [0.0, ouPy(k, 0.4) - 1e-3],
  };
  if (!(variavel in faixas)) {
    throw new Error(`faixaDeBusca: variavel sem faixa no motor: ${variavel}`);
  }
  const [lo, hi] = faixas[variavel];
  return { lo, hi };
}

// justos.py:2035-2036 — `conv = 1.0 if base != 'ebitda' else (1-d)(1-t)` e
// `M = alvo / conv`. So' a base EBITDA converte: o `rev` resolve SEMPRE sobre
// EV/NOPAT (firm) ou P/L (equity), e a conversao mora no ALVO, nunca na funcao.
// `da`/`tax` ausentes ou nulas caem no default 0.0 do argparse (justos.py:1766),
// o mesmo colapso null->ausencia->default que `premissasParaNucleo` documenta.
function alvoNormalizado({ alvo, base, premissas }) {
  if (base !== 'ebitda') return alvo;
  const d = pct(premissas.da ?? null);
  const t = pct(premissas.tax ?? null);
  return alvo / ((1 - (d === null ? 0.0 : d)) * (1 - (t === null ? 0.0 : t)));
}

// reversa.py:alvo_de_mercado — a `base` que o alvo carrega, por rota e tipo de
// metrica. Mora aqui (e nao na fachada) porque e' o que decide `conv` acima: a
// mesma decisao em dois lugares divergiria (a licao do FIX 2 da 3B).
function baseDoAlvo(rota, tipoMetrica) {
  if (rota === 'firm') return tipoMetrica === 'EBITDA' ? 'ebitda' : 'nopat';
  if (rota === 'rampa') return 'ebitda0';
  if (rota === 'equity') return 'pl';
  throw new Error(`baseDoAlvo: rota desconhecida ${rota}`);
}

// O contexto numerico de uma reversa: `g`/`r`/`k` em fracao, `kw` do lado certo e a
// funcao BRUTA do vendor (`_raw`, justos.py:2044-2045). `base_f` do vendor so'
// difere de `_raw` sob `--alvo-base forward`, que `reverter` nunca usa (_ALVO_BASE =
// 'corrente', reversa.py:115) — por isso `base_f` nao aparece aqui.
function contextoDaReversa(rota, premissas) {
  const eq = rota === 'equity';
  const g = pct(premissas.g ?? null);
  const r = pct((eq ? premissas.roe : premissas.roic) ?? null);
  const k = pct((eq ? premissas.ke : premissas.wacc) ?? null);
  const n = premissas.n;
  // justos.py:2037-2041 (kwf/kwe). `politica_tv`/`mid_year` chegam pelo default do
  // argparse quando ausentes ou nulas — mesmo colapso de `premissasParaNucleo`.
  const politicaTv = (premissas.politica_tv === null || premissas.politica_tv === undefined)
    ? 'continua' : premissas.politica_tv;
  const midYear = (premissas.mid_year === null || premissas.mid_year === undefined)
    ? false : premissas.mid_year;
  const kw = eq
    ? {
      tv: premissas.tv,
      roe_tv: pct(premissas.roe_tv ?? null),
      gp: ouPy(pct(premissas.gp ?? null), 0.0),
      roe_book: pct(premissas.roe_book ?? null),
      politica_tv: politicaTv,
      mid_year: midYear,
    }
    : {
      tv: premissas.tv,
      roic_tv: pct(premissas.roic_tv ?? null),
      gp: ouPy(pct(premissas.gp ?? null), 0.0),
      roic_book: pct(premissas.roic_book ?? null),
      mid_year: midYear,
    };
  // justos.py:2042 — `gde, nde = pc(a.gde) or 0, pc(a.nde) or 0` (so' lado equity).
  const gde = ouPy(pct(premissas.gde ?? null), 0);
  const nde = ouPy(pct(premissas.nde ?? null), 0);
  const bruto = (gg, rr, kk, nn, kw2) => (eq
    ? pe({ g: gg, roe: rr, ke: kk, n: nn, gde, nde, ...kw2 })
    : evNopat({
      g: gg, roic: rr, w: kk, n: nn, ...kw2,
    }));
  return { eq, g, r, k, n, kw, bruto };
}

// justos.py:2137-2200 — o ramo `cap`. Publica o CODIGO de `MOTIVOS_DA_LEITURA`
// (D3), decidido pelo MESMO predicado (`crescente`) que escolhe as duas frases
// verbatim do vendor, e o numero so' quando ele existe. As QUATRO saidas:
// `cap_indefinido` (spread <= 0 sob book, sem numero), `cap_fora_da_faixa`
// (as duas pontas das duas direcoes, sem numero), `cap_na_faixa` e
// `cap_na_faixa_decrescente` (com numero).
function capImplicito({ rota, premissas, M }) {
  const ctx = contextoDaReversa(rota, premissas);
  const { g, r, k, kw, bruto } = ctx;
  const tvc = tvCanon('tv' in kw ? kw.tv : 'book');
  const alvoNorm = arredondarPy(M, 3);

  const spread = (r !== null && k !== null) ? r - k : null;
  if (spread !== null && spread <= 0 && tvc === 'book') {
    return { motivo_do_cap: 'cap_indefinido', CAP_implicito_anos: null,
      alvo_normalizado: alvoNorm, aviso_monotonia: false };
  }

  const vals = [];
  for (let n = CAP_ANO_MINIMO; n <= CAP_ANO_MAXIMO; n++) vals.push([n, bruto(g, r, k, n, kw)]);
  const difs = [];
  for (let i = 0; i < vals.length - 1; i++) difs.push(vals[i + 1][1] - vals[i][1]);
  const monotona = difs.every((d) => d >= -1e-12) || difs.every((d) => d <= 1e-12);
  const crescente = vals[vals.length - 1][1] >= vals[0][1];

  // n continuo por interpolacao linear entre os anos inteiros que bracketam M.
  const interp = (subindo) => {
    for (let i = 0; i < vals.length - 1; i++) {
      const [n0, v0] = vals[i];
      const [, v1] = vals[i + 1];
      if ((subindo && v0 < M && M <= v1) || (!subindo && v0 > M && M >= v1)) {
        return v1 !== v0 ? n0 + (M - v0) / (v1 - v0) : n0;
      }
    }
    if ((subindo && vals[0][1] >= M) || (!subindo && vals[0][1] <= M)) return vals[0][0];
    return null;
  };

  let motivo;
  let anos;
  if (crescente) {
    const hit = interp(true);
    motivo = hit !== null ? 'cap_na_faixa' : 'cap_fora_da_faixa';
    anos = hit !== null ? arredondarPy(hit, 1) : null;
  } else if (M > vals[0][1] || M < vals[vals.length - 1][1]) {
    // As duas pontas da serie decrescente: o motor escreve texto no lugar do
    // numero, e `_motivo_do_eixo` le exatamente isso como fora da faixa.
    motivo = 'cap_fora_da_faixa';
    anos = null;
  } else {
    motivo = 'cap_na_faixa_decrescente';
    anos = arredondarPy(interp(false), 1);
  }
  return { motivo_do_cap: motivo, CAP_implicito_anos: anos,
    alvo_normalizado: alvoNorm, aviso_monotonia: !monotona };
}

// justos.py:2203-2300 — o ramo dos tres eixos PERCENTUAIS. Devolve o subconjunto
// da saida do motor que a leitura e a resolucao leem, com a mesma forma: raizes e
// tangenciais em PONTO PERCENTUAL arredondados, `identificacao_por_raiz` chaveada
// como o motor a chaveia, e `sugestao` como PRESENCA (o texto fica no Python).
function revDoEixoPercentual({ rota, variavel, premissas, M }) {
  const ctx = contextoDaReversa(rota, premissas);
  const { g, r, k, n, kw, bruto } = ctx;
  const { lo, hi } = faixaDeBusca({ variavel, rota, premissas });

  // justos.py:2203-2210 — `f` injeta x na variavel resolvida; `mult = f(x) + M`
  // e' literal (nao uma chamada fresca ao nucleo): (fn(x)-M)+M nao e' sempre
  // bit-a-bit igual a fn(x), e a paridade desta fatia e' exata no arredondado.
  const f = (x) => {
    let gg = g;
    let rr = r;
    let kk = k;
    let kk2 = kw;
    if (variavel === 'g') gg = x;
    else if (variavel === 'roic' || variavel === 'roe') rr = x;
    else if (variavel === 'ke' || variavel === 'wacc') kk = x;
    else if (variavel === 'gp') kk2 = { ...kw, gp: x };
    return bruto(gg, rr, kk, n, kk2) - M;
  };
  const mult = (x) => f(x) + M;

  const { raizes, tangenciais } = resolverCompleto(f, lo, hi, STEPS_DA_REVERSA, M);

  const saida = {};
  saida[`raizes_${variavel}_%`] = raizes.map((x) => arredondarPy(x * 100, 3));
  if (raizes.length) {
    // Objeto chaveado como o motor o chaveia — o colapso por chave repetida e'
    // parte do contrato (ver `chaveDaIdentificacao`).
    const porRaiz = {};
    for (const x of raizes) porRaiz[chaveDaIdentificacao(x)] = identificacao(mult, x, M, TOL_DA_REVERSA);
    saida.identificacao_por_raiz = porRaiz;
  }
  if (tangenciais.length) {
    saida[`raizes_tangenciais_${variavel}_%`] = tangenciais.map((t) => ({
      'x_%': arredondarPy(t.x * 100, 3),
      residuo: arredondarPy(t.residuo, 6),
    }));
  }
  // justos.py:2278-2295 — `sugestao` so' existe quando NAO ha raiz NEM tangencial e
  // a variavel e' primaria. E' o gatilho de `limitacoes_da_leitura` e do teto; o
  // TEXTO fica no Python (A3).
  if (!raizes.length && !tangenciais.length && ['g', 'roic', 'roe'].includes(variavel)) {
    saida.sugestao = true;
  }
  return saida;
}

// reversa.py:_motivo_do_eixo — o classificador UNICO das saidas do `rev`, lido
// pela leitura E pela resolucao (nunca duas copias da mesma decisao). No eixo
// 'cap' o codigo ja' vem decidido por `capImplicito` (D3): o espelho nunca monta
// a frase `direcao` do vendor para traduzi-la de volta.
function motivoDoEixo(nomeEixo, variavel, saida) {
  if (nomeEixo === 'cap') return saida.motivo_do_cap;
  const raizes = saida[`raizes_${variavel}_%`];
  return (raizes && raizes.length) ? 'raiz_na_faixa' : 'sem_raiz_na_faixa';
}

// reversa.py:_identificacao_da_raiz — sem derivadas na vizinhanca, `identificacao()`
// devolve so' `{nota}` e os tres campos saem null, nunca inventados.
function identificacaoDaRaiz(ident) {
  if (!('identificacao' in ident)) {
    return { identificacao: null, intervalo: null, curvatura: null };
  }
  const chaveIntervalo = Object.keys(ident).find((c) => c.startsWith(PREFIXO_DO_INTERVALO));
  return {
    identificacao: ident.identificacao,
    intervalo: chaveIntervalo !== undefined ? [...ident[chaveIntervalo]] : null,
    curvatura: ident.curvatura_d2M_dx2 ?? null,
  };
}

// reversa.py:_posicao_e_distancia + _beta_implicito — a inversao declarada do CAPM
// sobre a PRIMEIRA raiz do eixo de custo de capital. Publica o CODIGO da posicao
// (`POSICOES_NA_BANDA`), nunca as palavras que o wrapper Python traduz de volta.
// `algebra` e `nota_multiplas_raizes` ficam no Python: prosa de auditoria (A3).
function betaImplicito(saidaEixo, variavel, mercado) {
  const raizes = saidaEixo[`raizes_${variavel}_%`] || [];
  if (!raizes.length) {
    return { valor: null, posicao: 'sem_raiz', distancia: null };
  }
  const raizUsada = raizes[0];
  const beta = (raizUsada - mercado.rf) / mercado.erp;
  const banda = mercado.beta_observado ?? null;
  if (banda === null) return { valor: beta, posicao: 'sem_banda', distancia: null, raiz_usada: raizUsada };
  const [minimo, maximo] = banda;
  if (beta < minimo) return { valor: beta, posicao: 'abaixo', distancia: minimo - beta, raiz_usada: raizUsada };
  if (beta > maximo) return { valor: beta, posicao: 'acima', distancia: beta - maximo, raiz_usada: raizUsada };
  return { valor: beta, posicao: 'dentro', distancia: 0.0, raiz_usada: raizUsada };
}

// reversa.py:_resolucao — o marcador uniforme `{resolveu, motivo}`, acrescentado AO
// LADO do que o motor devolveu. As frases sao deste wrapper (nunca copia do texto
// do motor) e entram no comparador por igualdade exata: sao o que a aba mostra
// quando o eixo nao fecha.
function resolucaoDoEixo(nomeEixo, variavel, saida) {
  const motivo = motivoDoEixo(nomeEixo, variavel, saida);
  if (motivo === 'cap_indefinido') {
    return { resolveu: false, motivo: 'CAP implícito indefinido: spread do eixo não é positivo.' };
  }
  if (motivo === 'cap_fora_da_faixa') {
    return { resolveu: false, motivo: 'CAP implícito fora da faixa de anos (1-60).' };
  }
  if (motivo === 'cap_na_faixa' || motivo === 'cap_na_faixa_decrescente') {
    return { resolveu: true, motivo: 'CAP implícito dentro da faixa de anos (1-60).' };
  }
  if (motivo === 'raiz_na_faixa') {
    return { resolveu: true, motivo: `raiz encontrada na faixa de busca de '${variavel}'.` };
  }
  return { resolveu: false, motivo: `sem raiz na faixa de busca de '${variavel}'.` };
}

// reversa.py:leitura_do_eixo — a forma normalizada que a aba le desde a 5F (D2), na
// MESMA forma e nas MESMAS chaves. Raiz e identificacao pareiam pela POSICAO, e
// comprimentos diferentes sao erro nomeado (nunca um par inventado).
function leituraDoEixo(nomeEixo, rota, saida, banda) {
  const variavel = RESOLVER_POR_EIXO[nomeEixo][rota];
  const motivo = motivoDoEixo(nomeEixo, variavel, saida);
  if (nomeEixo === 'cap') {
    return {
      premissa: null,
      unidade: UNIDADE_DO_CAP,
      unidade_da_curvatura: UNIDADE_DA_CURVATURA,
      motivo,
      raizes: [],
      tangenciais: [],
      cap_anos: (motivo === 'cap_na_faixa' || motivo === 'cap_na_faixa_decrescente')
        ? saida.CAP_implicito_anos : null,
    };
  }
  const valores = saida[`raizes_${variavel}_%`] || [];
  const identificacoes = Object.values(saida.identificacao_por_raiz || {});
  if (identificacoes.length !== valores.length) {
    throw new Error(
      `eixo '${nomeEixo}' da reversa com ${valores.length} raiz(es) em 'raizes_${variavel}_%' e `
      + `${identificacoes.length} em 'identificacao_por_raiz': a leitura pareia raiz e identificacao `
      + 'pela posicao, e sem o mesmo comprimento o par seria inventado.');
  }
  const leitura = {
    premissa: variavel,
    unidade: UNIDADE_DA_RAIZ,
    unidade_da_curvatura: UNIDADE_DA_CURVATURA,
    motivo,
    raizes: valores.map((valor, i) => ({ valor, ...identificacaoDaRaiz(identificacoes[i]) })),
    tangenciais: (saida[`raizes_tangenciais_${variavel}_%`] || []).map((t) => t['x_%']),
    cap_anos: null,
  };
  if (nomeEixo === EIXO_DO_CUSTO_DE_CAPITAL) {
    const beta = saida.beta_implicito;
    leitura.beta = {
      valor: beta.valor,
      posicao: beta.posicao,
      distancia: beta.distancia,
      banda: banda ? [...banda] : null,
      unidade: UNIDADE_DO_BETA,
    };
  }
  return leitura;
}

// reversa.py:_algum_eixo_primario_sem_raiz + LIMITACOES_DA_LEITURA. Uma funcao so',
// lida pelo teto E pela limitacao — uma segunda copia da condicao poderia divergir.
function algumEixoPrimarioSemRaiz(eixos) {
  return EIXOS_PRIMARIOS.some((nome) => nome in eixos && eixos[nome].sugestao === true);
}

// reversa.py:LIMITACOES_DA_LEITURA — o vocabulario publico das limitacoes da
// LEITURA da reversa. Exportado porque o comparador da fachada precisa saber
// QUAIS chaves de `resultados.limitacoes` sao desta camada: a lista publicada la'
// mistura a limitacao que SUPRIME a reversa (avaliar.py:1446) com estas, e filtrar
// por um literal escrito na fachada seria uma segunda copia do vocabulario.
const LIMITACOES_DA_LEITURA = ['iso_nao_calculada'];

function limitacoesDaLeitura(eixos) {
  return algumEixoPrimarioSemRaiz(eixos) ? [...LIMITACOES_DA_LEITURA] : [];
}

// reversa.py:teto_do_crescimento_gratuito — o caso-limite RiR_TV -> 0: `tv` forcado
// para 'gordon', a rentabilidade terminal levada a `RENTABILIDADE_TERMINAL_INFINITA`
// e `gp` igualado ao `g` do cenario. Devolve o MULTIPLO (nao um preco) pelo mesmo
// caminho de `precificarCelula` — o mesmo arredondamento do motor, nos mesmos
// pontos. `leitura` e `diagnosticos` (as MENSAGENS) ficam no Python; as CHAVES de
// diagnostico vem do espelho que a 4C ja' tem, para que o numero nao ande sozinho.
function tetoDoCrescimentoGratuito({ rota, premissas, metrica, ndEfetivo, acoes, moeda, rf }) {
  const variavelTv = `${RESOLVER_POR_EIXO.rentabilidade[rota]}_tv`;
  const premissasAlteradas = {
    tv: 'gordon',
    [variavelTv]: RENTABILIDADE_TERMINAL_INFINITA,
    gp: premissas.g,
  };
  const vetor = { ...premissas, ...premissasAlteradas };
  const { multiplo } = precificarCelula(rota, vetor, metrica, ndEfetivo, acoes);
  return {
    multiplo,
    premissas_alteradas: premissasAlteradas,
    diagnosticos_chaves: rota === 'firm'
      ? diagnosticosFirm(vetor, moeda, rf)
      : diagnosticosEquity(vetor, moeda, rf),
  };
}

// A orquestracao por eixo — o que faltava para a reversa rodar no browser (A1: "o
// que falta nao e' matematica de raiz, e' a orquestracao por eixo"). Espelha
// `reversa.reverter` no que a aba le: o vetor central do cenario MENOS a variavel
// resolvida, a faixa derivada desse vetor, o alvo normalizado, e `{leitura,
// resolucao}` por eixo. `alvo` chega pronto (a fachada o calcula com
// `alvoDeMercado`, a mesma conta que a 4B ja' espelha).
//
// D5 — a recusa da CLI entra ANTES de montar `f`: `cliRecusa` e' a mesma checagem
// que a 4C mediu (a CLI recusa o vetor com codigo 2 sem rodar handler nenhum), e o
// subcomando `rev` tem as DUAS camadas que ela cobre — `--tv required=True` e
// `--n type=int` (justos.py:1769) mais `avaliar_dominios_cli`. Um eixo recusado
// publica `resolucao: {resolveu: false}` com motivo proprio e `leitura: null` —
// nunca uma raiz, e nunca uma leitura com cara de "procurei e nao achei", porque o
// motor de verdade nao procurou nada.
const RECUSA_DA_CLI_NA_REVERSA = 'premissa fora do domínio que a CLI do motor aceita: '
  + 'o eixo não foi resolvido.';

function reverterEixos({ rota, eixos, premissas, alvo, base, metrica, ndEfetivo, acoes,
  mercado, moeda, rf }) {
  const saidas = {};
  const publicados = {};
  for (const nomeEixo of eixos) {
    const variavel = RESOLVER_POR_EIXO[nomeEixo][rota];
    // `reverter` remove a variavel resolvida do vetor: fixada, nao haveria o que
    // resolver — e `rngs` a le como ausente (`(r or 0.6)`).
    const vetor = { ...premissas };
    delete vetor[variavel];

    if (cliRecusa(vetor)) {
      saidas[nomeEixo] = {};
      publicados[nomeEixo] = {
        leitura: null,
        resolucao: { resolveu: false, motivo: RECUSA_DA_CLI_NA_REVERSA },
      };
      continue;
    }

    const M = alvoNormalizado({ alvo, base, premissas: vetor });
    const saida = nomeEixo === 'cap'
      ? capImplicito({ rota, premissas: vetor, M })
      : revDoEixoPercentual({ rota, variavel, premissas: vetor, M });
    if (nomeEixo === EIXO_DO_CUSTO_DE_CAPITAL) {
      saida.beta_implicito = betaImplicito(saida, variavel, mercado);
    }
    saidas[nomeEixo] = saida;
    publicados[nomeEixo] = {
      leitura: leituraDoEixo(nomeEixo, rota, saida, mercado.beta_observado ?? null),
      resolucao: resolucaoDoEixo(nomeEixo, variavel, saida),
    };
  }

  const resultado = { eixos: publicados, limitacoes: limitacoesDaLeitura(saidas) };
  if (algumEixoPrimarioSemRaiz(saidas)) {
    resultado.teto_do_crescimento_gratuito = tetoDoCrescimentoGratuito({
      rota, premissas, metrica, ndEfetivo, acoes, moeda, rf,
    });
  }
  return resultado;
}

// Problema `tipo: 'reversa'` da fixture de paridade: o caso minimo inteiro de uma
// vez (alvo + eixos + limitacoes + teto), contra `reversa.reverter` do lado Python.
function resolverReversa(item) {
  const a = item.args;
  const metrica = a.metrica;
  const alvo = alvoDeMercado({
    rota: a.rota, preco: a.preco, acoes: a.acoes, ndEfetivo: a.nd_efetivo, metrica,
  });
  const r = reverterEixos({
    rota: a.rota,
    eixos: a.eixos,
    premissas: a.premissas,
    alvo,
    base: baseDoAlvo(a.rota, metrica.tipo),
    metrica,
    ndEfetivo: a.nd_efetivo,
    acoes: a.acoes,
    mercado: a.mercado,
    moeda: a.moeda,
    rf: a.mercado ? a.mercado.rf : null,
  });
  // `reverter` do Python LEVANTA no primeiro eixo que a CLI recusa (o motor sai com
  // codigo 2 e `rodar` estoura): do lado Python nao sobra resultado nenhum. Aqui o
  // espelho segue e recusa eixo a eixo — o que o laboratorio precisa —, e o harness
  // compara o FATO que os dois lados compartilham: houve recusa da CLI ou nao.
  const recusaDaCli = Object.values(r.eixos).some((e) => e.leitura === null);
  if (recusaDaCli) return { id: item.id, recusa_da_cli: true, ...CAMPOS_SOLVER_VAZIOS };
  return { id: item.id, recusa_da_cli: false, alvo, ...r, ...CAMPOS_SOLVER_VAZIOS };
}

// ---------------- despacho por item (CLI, item 4 fatia B) ----------------
// Sem `tipo`: item da fixture de VALOR da 4A (fn/args -> valor) — despachado
// por `avaliarVetores`, o MESMO caminho de sempre, sem nenhuma linha
// alterada nele: o harness da 4A continua verde sem mudanca. `tipo:
// 'solver'`: problema de solver (task 2), despachado por `resolverProblema`.
// `tipo: 'alvo'|'grade1d'|'grade2d'`: problema de wrapper (task 3),
// despachado por `resolverAlvo`/`resolverGrade1D`/`resolverGrade2D`. `tipo:
// 'rampa'` (fatia C, task 1): despachado por `resolverRampa`. `tipo: 'diag'`
// (fatia C, task 2): despachado por `resolverDiag`. `tipo: 'degrau'`
// (fatia D, task 2): despachado por `resolverDegrau`. `tipo: 'conservacao'` (fatia 5F,
// task 3): despachado por `resolverConservacao`.
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
  if (item.tipo === 'diag') {
    return resolverDiag(item);
  }
  if (item.tipo === 'degrau') {
    return resolverDegrau(item);
  }
  if (item.tipo === 'conservacao') {
    return resolverConservacao(item);
  }
  if (item.tipo === 'reversa') {
    return resolverReversa(item);
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
  diagnosticosFirm, diagnosticosEquity, resolverDiag,
  fatorH, rentabPosDegrau, descontoTransicao, valorTransicionado, precificarDegrau, resolverDegrau,
  LIMIAR_DIVERGENCIA_DE_BASE_PCT, CHAVE_DIVERGENCIA_DE_BASE,
  LIMIAR_CONSERVACAO_CAPITAL, conservacaoCapital, resolverConservacao,
  RESOLVER_POR_EIXO, EIXO_DO_CUSTO_DE_CAPITAL, EIXOS_PRIMARIOS,
  faixaDeBusca, alvoNormalizado, baseDoAlvo, capImplicito, betaImplicito,
  motivoDoEixo, leituraDoEixo, resolucaoDoEixo, limitacoesDaLeitura, LIMITACOES_DA_LEITURA,
  tetoDoCrescimentoGratuito, reverterEixos, resolverReversa,
  tvCanon, cliRecusa,
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
