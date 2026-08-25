// Espelho verificado por paridade do nucleo de valor de vendor/multiplos-justos/scripts/justos.py
// (v9.31) — reproduz ev_nopat/ev_ebitda (linhas 32-72) e pe (linhas 214-271); nenhuma alteracao
// pode ser feita neste arquivo sem que o harness de paridade (tests/test_paridade_js.py) a aprove.
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

// ---------------- exportacao: CommonJS (node) OU globalThis (browser) ----------------
// FIX 1 (revisao final, item Critico) — `module.exports = {...}` incondicional
// estourava `ReferenceError: module is not defined` num contexto sem `module`
// — exatamente o de um <script> de browser (o banner de paridade e o
// laboratorio do item 5, os DOIS chamadores que a Decisao D2 do plano promete
// — "um caminho de codigo, dois chamadores"). A execucao morria antes de
// `avaliarVetores` ficar alcancavel: o segundo chamador nunca existiu de
// fato. `typeof` e a unica forma segura de checar um identificador que pode
// nem existir, sem estourar sozinho.
const superficiePublica = { evNopat, evEbitda, pe, ponteParaPreco, avaliarVetores };

if (typeof module !== 'undefined' && typeof module.exports !== 'undefined') {
  module.exports = superficiePublica;
} else {
  globalThis.MotorEspelho = superficiePublica;
}

// CLI
if (typeof module !== 'undefined' && typeof require !== 'undefined' && require.main === module) {
  const fs = require('fs');
  const caminho = process.argv[2];
  const vetores = JSON.parse(fs.readFileSync(caminho, 'utf-8'));
  const resultados = avaliarVetores(vetores);
  console.log(JSON.stringify(resultados));
}
