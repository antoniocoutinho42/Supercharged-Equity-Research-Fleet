// ============================================================================
// FACHADA DO ESPELHO — item 5, fatia 5C, Task 1
//
// O que e': o equivalente em JS do caminho de `skills/er-valuation/scripts/
// avaliar.py` que produz o PRECO de cada cenario. Recebe um `caso` (o mesmo
// dict que `caso.json` carrega) e devolve o subconjunto VIVO do
// `resultados.json`, nas MESMAS chaves — para o laboratorio da aba Valuation
// recalcular preco e multiplo a cada premissa editada, e para o badge de
// paridade comparar chave a chave com o `resultados` que o Python publicou,
// sem traducao nenhuma no meio.
//
// Onde mora, e por que: `skills/er-valuation/assets/` — camada de
// INTEGRACAO, nunca o relatorio (decisao L1 do plano da fatia, emenda E3 do
// desenho v4 §15). Traduzir `caso` -> shape de `resultados` e' exatamente o
// que `avaliar.py` faz do lado Python: conhecimento de integracao e paridade.
// Por em `skills/er-relatorio/assets/` seria reimplementar o wrapper em JS —
// o acoplamento que E3 proibe, e que `tests/test_relatorio_fronteira.py`
// reprova por sha256. O relatorio LE este arquivo e o embute; nunca o copia.
//
// O que esta fachada NAO faz: aritmetica de valuation. Toda conta de valor
// vem de `motor_espelho.js` (`precificarCelula`, `precificarRampa`,
// `precificarDegrau`), que por sua vez espelha o motor congelado. A unica
// soma deste arquivo e' a PONTE (`ponte.py:compor`, linhas 36-69), que o
// proprio modulo Python declara nao ser calculo de valor: linhas de balanco
// com sinal explicito somadas em `nd_efetivo`. Ela entra aqui porque o
// escopo vivo da fatia inclui a ponte (decisao L3) e o espelho do nucleo nao
// a tem — `ponteParaPreco` cruza a ponte, nao a COMPOE.
//
// Escopo vivo desta fatia (L3): o que produz o preco de cada cenario. Fora
// dele, de proposito, e rotulado "congelado nas premissas originais" na tela:
// SOTP, reversa e sensibilidades. O espelho ja' tem `resolverCompleto`,
// `grade1D` e `grade2D`; eles entram quando houver consumidor, nao antes.
//
// DIAGNOSTICO (Task 3; secao 8.4 do desenho, regra inegociavel: o diagnostico
// se move junto com o numero). Cada cenario vivo publica as CHAVES de
// diagnostico no mesmo lugar e na mesma ordem em que `avaliar.py` as publica —
// tres formas, porque a fachada precifica quatro pernas:
// - firm/equity: `diagnosticos_chaves` = `diagnosticosFirm`/
//   `diagnosticosEquity` do espelho (do lado Python, as mensagens da mesma
//   chamada do motor, classificadas por `diagnosticos.classificar`);
// - rampa: `diagnosticos_chaves` = os avisos presentes, na ordem de
//   `AVISOS_RAMPA` (`_AVISOS_RAMPA_ORDEM`, do lado Python);
// - degrau: as chaves do PROPRIO cenario vem da perna P/L (o wrapper preserva
//   as de `_monta_cenario`), e as dos alertas do degrau vao em
//   `degrau.diagnosticos_chaves`, como `precificarDegrau` as devolve
//   (`_ALERTAS_DEGRAU_ORDEM`, do lado Python) — mais, desde a onda de correcao
//   da revisao final (F1), a da divergencia de base acima do limiar, que o
//   espelho decide com a copia travada do limiar do wrapper.
// Nenhuma chave e' decidida AQUI — nenhum predicado, nenhum limiar: esta
// fachada so' poe no lugar do contrato o que o espelho respondeu.
//
// CENARIO RECUSADO (onda de correcao da revisao final da 5C, F2 e F3). Um
// cenario recusado publica `null` — nunca `[]` — em toda lista de chaves e na
// lista exibivel, e `recusa: {codigo}` com o motivo nomeado:
// - `dominio_da_cli`: a CLI do motor recusa o vetor antes de calcular (codigo
//   2: argparse ou avaliar_dominios_cli) — `MotorEspelho.cliRecusa`;
// - `nucleo_nao_finito`: a CLI aceita, mas o nucleo nao fecha um numero finito
//   (o motor devolve `null`, ou o proprio nucleo levanta erro);
// - `degrau_book_sem_roe_book`: a D6 do gate (`caso.py:_validar_degrau`),
//   aplicada AQUI ao caso editado — a unica regra de cenario do gate que os
//   campos do painel alcancam. O laboratorio edita sem passar pelo gate, e o
//   relatorio nao reimplementa gate nenhum.
// `null`, e nao lista vazia, porque "nenhum diagnostico" seria falso: o motor
// que recusa por nucleo nao finito EMITE diagnosticos (com gp = wacc sob
// gordon sao quatro); o que ele nao produz e' numero. Cenario precificado
// publica `recusa: null`. Os tres codigos sao `MOTIVOS_DE_RECUSA`, expostos na
// superficie publica e travados contra os rotulos do catalogo.
//
// LISTA EXIBIVEL (onda de correcao da revisao final da 5C, F4; E3). Alem das
// formas do contrato, cada cenario vivo publica `diagnosticos_exibidos`: a
// UNICA lista que o laboratorio pinta, montada AQUI a partir das formas acima
// (as do cenario e, num cenario com degrau, as do degrau depois delas). O
// laboratorio deixou de conhecer caminho de contrato: uma forma aditiva de uma
// v10 (`transicao.diagnosticos_chaves`, digamos) chega a tela quando entra
// nesta lista, sem uma linha no relatorio — e, se ficar de fora,
// `tests/test_espelho_fachada_js.py` reprova na INTEGRACAO, porque deriva as
// listas de cada cenario do `resultados` descendo por ele, sem nomear caminho.
//
// Carregamento: no browser os dois arquivos chegam como <script> e a fachada
// acha o espelho por `globalThis.MotorEspelho`; em node, por `require` do
// irmao. A busca e' PREGUICOSA (na hora da chamada, nao no topo) para que a
// ordem das duas tags no HTML nunca importe.
//
// TUDO abaixo vive dentro de uma IIFE, e o arquivo inteiro nao declara UM
// identificador de topo — nem `const`, nem `function`. Nao e' estilo: dois
// <script> classicos compartilham o MESMO escopo lexico global, e
// `motor_espelho.js` ja' declara `const superficiePublica` (alem de `pe`,
// `resolver`, `identificacao`, `CHAVE`...). Uma versao anterior deste arquivo
// repetia esse nome no topo e o segundo <script> morria inteiro com
// `SyntaxError: Identifier 'superficiePublica' has already been declared` —
// pego por `test_a_fachada_roda_em_contexto_de_browser_sem_module_nem_require`,
// que carrega os dois FONTES no mesmo contexto, como o HTML faz. A IIFE fecha
// a classe inteira do problema (guarda estrutural, nao renomeacao pontual):
// nenhum nome daqui pode colidir com o espelho hoje nem com o que a fatia
// acrescentar amanha.
// ============================================================================

(function () {
  'use strict';

  // A versao de `resultados.versao_contrato` que esta fachada sabe ler —
  // `avaliar.py:140` (`VERSAO_CONTRATO = "resultados/1"`). Literal, nao
  // derivado: e' uma DECLARACAO de qual contrato este arquivo entende, e um
  // `resultados` de outra versao tem de reprovar aqui, em voz alta (L2).
  const VERSAO_CONTRATO = 'resultados/1';

  // Tolerancia do comparador: erro RELATIVO com piso absoluto,
  // |py - js| <= max(TAU*|py|, TAU) — a MESMA dos tres harnesses de paridade
  // da suite (ver `tests/test_paridade_js.py`, que a documenta e mede a folga
  // contra o erro real). Nao e' numero novo: e' o mesmo limiar, aplicado na
  // maquina de quem abriu o relatorio em vez de no CI.
  const TAU = 1e-12;

  // Os motivos de recusa de um CENARIO (F2 e F3; ver o cabecalho, "CENARIO
  // RECUSADO"). O rotulo de cada um mora em `catalogo_apresentacao.json:
  // recusas`, com o conjunto travado contra este em
  // `tests/test_espelho_fachada_js.py`.
  const RECUSA_DOMINIO_DA_CLI = 'dominio_da_cli';
  const RECUSA_NUCLEO_NAO_FINITO = 'nucleo_nao_finito';
  const RECUSA_DEGRAU_BOOK_SEM_ROE_BOOK = 'degrau_book_sem_roe_book';
  const MOTIVOS_DE_RECUSA = Object.freeze([
    RECUSA_DOMINIO_DA_CLI, RECUSA_NUCLEO_NAO_FINITO, RECUSA_DEGRAU_BOOK_SEM_ROE_BOOK,
  ]);

  // Ordem e sinal das linhas de balanco — `ponte.py:SINAIS` (linhas 18-24),
  // verbatim. Ordem importa para o waterfall; sinal, para a soma.
  const SINAIS_DA_PONTE = [
    ['divida_bruta', 1],
    ['caixa_e_equivalentes', -1],
    ['outros_ativos', -1],
    ['outros_passivos', 1],
    ['minoritarios', 1],
  ];

  // Rotas que cruzam ponte de divida — `avaliar.py:881-908`: firm e rampa
  // compoem `caso["ponte"]` e publicam o bloco em `resultados["ponte"]`; a
  // rota equity chega em Equity direto (P/L x LL), usa `nd_efetivo = 0.0`
  // internamente (linha 915) e NAO publica bloco nenhum.
  const ROTAS_COM_PONTE = new Set(['firm', 'rampa']);

  // Recusa NOMEADA, nunca um KeyError/TypeError nascido fundo (licao da
  // revisao final da 5B, achado F6): quem chama recebe um `codigo` estavel
  // para decidir o que mostrar, e uma mensagem que cita os dois lados.
  function recusa(codigo, mensagem) {
    const erro = new Error(`espelho_fachada: ${mensagem}`);
    erro.codigo = codigo;
    return erro;
  }

  function espelho() {
    if (typeof globalThis !== 'undefined' && globalThis.MotorEspelho) {
      return globalThis.MotorEspelho;
    }
    if (typeof module !== 'undefined' && typeof require === 'function') {
      return require('./motor_espelho.js');
    }
    throw recusa('espelho_ausente',
      'motor_espelho.js nao foi carregado — a fachada nao faz conta nenhuma por '
      + 'conta propria; carregue o espelho antes (globalThis.MotorEspelho).');
  }

  // `ponte.compor` (ponte.py:36-69), sem as `parcelas`: o laboratorio vive do
  // escalar. Linha ausente ou nao finita vira recusa nomeada — do lado Python
  // e' um KeyError de `ponte[rotulo]`, que aqui viraria `undefined` somado em
  // silencio (NaN, ou pior, um numero plausivel).
  function ndEfetivoDe(ponte) {
    if (ponte === null || typeof ponte !== 'object') {
      throw recusa('ponte_ausente',
        'o caso declara uma rota com ponte mas nao traz o bloco "ponte".');
    }
    let ndEfetivo = 0.0;
    for (const [rotulo, sinal] of SINAIS_DA_PONTE) {
      const valor = ponte[rotulo];
      if (!Number.isFinite(valor)) {
        throw recusa('ponte_incompleta',
          `linha de ponte "${rotulo}" ausente ou nao finita: ${JSON.stringify(valor)}.`);
      }
      ndEfetivo += valor * sinal;
    }
    return ndEfetivo;
  }

  // Chave do multiplo de REFERENCIA de cada rota — `avaliar.py:_chave_e_base_
  // do_multiplo` (linhas 182-212), sem a `base` (rotulo curto, que so' o
  // relatorio usa para parear tela x justo).
  //
  // Este objeto e' o PONTO UNICO que decide quais rotas esta fachada sabe
  // tratar: `avaliarCaso` o consulta (por `chaveDoMultiplo`) ANTES de
  // percorrer cenario nenhum, entao uma rota ausente daqui recusa a analise
  // inteira, nomeada. `ROTAS_ATENDIDAS` (exposta na superficie publica) e'
  // derivada dele — nao uma segunda lista que alguem precisa lembrar de
  // atualizar —, e `tests/test_espelho_fachada_js.py` a compara com o que o
  // gate aceita (`caso._PREMISSAS_POR_ROTA`). E' a mesma trava de upgrade do
  // catalogo de apresentacao: uma rota nova em `avaliar.py` sem perna aqui
  // reprova na INTEGRACAO, nunca em runtime no browser do analista.
  //
  // CONFIRMADO POR EXECUCAO, nao presumido (o plano mandava verificar): o
  // multiplo que `precificarCelula` devolve e' o da METRICA DECLARADA, e
  // corresponde a chave `_curr` dela em `resultados.cenarios.<n>.multiplos` —
  // 6.6906 = `EV/EBITDA_curr` na fixture `caso_reversa_firm` (rota firm,
  // metrica EBITDA), 9.003 = `PL_curr` em `caso_minimo_equity`. As chaves
  // `_fwd` (e a outra base da rota firm) sao numeros DIFERENTES, e
  // `tests/test_espelho_fachada_js.py` prende a correspondencia exigindo que
  // nenhuma outra chave de `multiplos` case com o valor publicado.
  const MULTIPLO_DE_REFERENCIA = {
    firm: (tipoMetrica) => (tipoMetrica === 'EBITDA' ? 'EV/EBITDA_curr' : 'EV/NOPAT_curr'),
    rampa: () => 'EV/EBITDA0',
    equity: () => 'PL_curr',
  };

  // `Object.keys`, nao `for...in`: so' as chaves PROPRIAS do objeto acima
  // entram — nada herdado do prototipo.
  const ROTAS_ATENDIDAS = Object.keys(MULTIPLO_DE_REFERENCIA);

  function chaveDoMultiplo(rota, tipoMetrica) {
    if (!Object.prototype.hasOwnProperty.call(MULTIPLO_DE_REFERENCIA, rota)) {
      throw recusa('rota_desconhecida',
        `rota sem multiplo de referencia: ${JSON.stringify(rota)}. Esta fachada `
        + `atende ${JSON.stringify(ROTAS_ATENDIDAS)}.`);
    }
    return MULTIPLO_DE_REFERENCIA[rota](tipoMetrica);
  }

  // `upside` — `avaliar._monta_cenario` (linha 704) e `_aplicar_degrau_ao_
  // cenario` (linha 669): `preco_acao / caso.preco.valor - 1`. E' a unica
  // conta que o wrapper Python faz FORA do motor, e por isso mesmo pertence
  // a esta fachada e nao ao laboratorio: comparar o preco justo com o preco
  // de tela e' orquestracao de integracao, exatamente como traduzir `caso`
  // em `resultados`. Preco recusado (`null`) propaga `null` — nunca o `-1`
  // que `null / preco - 1` produziria em JS, um numero plausivel e falso.
  function upsideDe(precoAcao, precoDeTela) {
    if (!Number.isFinite(precoAcao)) return null;
    return precoAcao / precoDeTela - 1;
  }

  function precoDeTelaDe(caso) {
    const preco = caso.preco;
    const valor = (preco === null || typeof preco !== 'object') ? undefined : preco.valor;
    if (!Number.isFinite(valor) || valor === 0) {
      throw recusa('preco_de_tela_ausente',
        `o caso nao declara um preco de tela utilizavel em "preco.valor": `
        + `${JSON.stringify(valor)}. Sem ele nao existe upside.`);
    }
    return valor;
  }

  // Um cenario recusado (premissa fora de dominio, `tv` null, nucleo nao
  // finito, ou a D6 no degrau) publica `null` nos dois numeros — o mesmo
  // vocabulario de recusa do espelho, nunca um numero inventado — e `null` na
  // lista de chaves: "nenhum diagnostico" seria falso (F2, cabecalho). O
  // comparador trata `null` contra o que o Python publicou como divergencia
  // (falha fechada). `codigo` e' um de MOTIVOS_DE_RECUSA.
  function cenarioRecusado(premissas, chave, codigo) {
    return {
      premissas,
      valor: { preco_acao: null },
      multiplo: { chave, valor: null },
      vs_preco: { upside: null },
      diagnosticos_chaves: null,
      recusa: { codigo },
    };
  }

  function cenarioPrecificado(premissas, precoAcao, chave, multiplo, precoDeTela,
    chavesDeDiagnostico) {
    return {
      premissas,
      valor: { preco_acao: precoAcao },
      multiplo: { chave, valor: multiplo },
      vs_preco: { upside: upsideDe(precoAcao, precoDeTela) },
      diagnosticos_chaves: chavesDeDiagnostico,
      recusa: null,
    };
  }

  // F2: POR QUE o espelho recusou este cenario — a pergunta que o motor de
  // verdade responderia pelo codigo de saida: a CLI recusa antes de calcular
  // (argparse ou avaliar_dominios_cli, `MotorEspelho.cliRecusa`) ou o nucleo
  // nao fecha um numero finito. So' e' chamada DEPOIS de o espelho recusar:
  // para essas recusas, esta fachada so' da o nome.
  function motivoDaRecusa(M, premissas) {
    return M.cliRecusa(premissas) ? RECUSA_DOMINIO_DA_CLI : RECUSA_NUCLEO_NAO_FINITO;
  }

  // F3: a D6 do gate (`caso.py:_validar_degrau`) — degrau com `tv` CANONICO
  // 'book' e sem `roe_book` (ausente ou `null`, como o `is None` do gate). O
  // alias legado 'ic' e' 'book' para o motor, por isso a comparacao passa por
  // `MotorEspelho.tvCanon`, o mesmo TV_CANON do espelho.
  // `tests/test_espelho_fachada_js.py` prende que esta fachada recusa pela D6
  // se e so' se `caso.validar` recusa o caso editado.
  function violaD6(M, premissas) {
    return M.tvCanon(premissas.tv) === 'book'
      && (premissas.roe_book === null || premissas.roe_book === undefined);
  }

  // `cenarios.<n>.degrau.diagnosticos_chaves` (Task 3): o unico campo do bloco
  // `degrau` do `resultados` que esta fachada publica — o preco e o multiplo
  // COM degrau ja' estao em `valor`/`multiplo`. So' existe nos cenarios com
  // degrau, do mesmo jeito que o bloco so' existe la' no `resultados`.
  function comDegrau(cenario, chavesDoDegrau) {
    cenario.degrau = { diagnosticos_chaves: chavesDoDegrau };
    return cenario;
  }

  // F4 (cabecalho, "LISTA EXIBIVEL"): toda forma de diagnostico que o cenario
  // publica, na ordem de cada uma — as do proprio cenario e, depois, as do
  // degrau. E' o UNICO ponto que junta as formas: uma forma nova entra aqui ou
  // reprova na trava da integracao.
  function listaExibida(cenario) {
    const formas = [cenario.diagnosticos_chaves];
    if (cenario.degrau) formas.push(cenario.degrau.diagnosticos_chaves);
    // F2: cenario recusado publica `null` em toda forma, e a lista exibivel
    // tambem sai `null` — nunca uma lista vazia que se leria como "nenhum
    // diagnostico".
    if (!formas.every((lista) => Array.isArray(lista))) return null;
    return [].concat(...formas);
  }

  // As chaves de um cenario firm/equity PRECIFICADO (Task 3). Do lado Python,
  // `_monta_cenario` classifica as mensagens da MESMA chamada do motor que
  // produziu o preco, com `moeda` e `rf`; o espelho ja' devolve as chaves
  // prontas, com a paridade presa em `tests/test_paridade_wrapper_js.py`. So'
  // e' chamada com preco finito: cenario recusado publica `null` (F2).
  function diagnosticosDaCelula(M, rota, premissas, moeda, rf) {
    return rota === 'firm'
      ? M.diagnosticosFirm(premissas, moeda, rf)
      : M.diagnosticosEquity(premissas, moeda, rf);
  }

  // `caso["degrau"]` chega com proveniencia por campo ({valor, fonte, data});
  // `precificarDegrau` (motor_espelho.js) quer os numeros CRUS, do jeito que
  // `avaliar.py:precificar_degrau` (linhas 590-600) os extrai antes de montar
  // o vetor do subcomando. `perfil_transicao` e `fx` seguem ausentes quando o
  // caso nao os declara: o espelho aplica os mesmos defaults do motor
  // ('rampa' e 1.0) — repo-los aqui seria decidir por ele.
  function blocoDegrauCru(blocoDegrau) {
    return {
      indice_atual: blocoDegrau.indice_atual.valor,
      indice_alvo: blocoDegrau.indice_alvo.valor,
      anos: blocoDegrau.anos,
      perfil_transicao: blocoDegrau.perfil_transicao,
      vpa: blocoDegrau.vpa.valor,
      fx: blocoDegrau.fx,
    };
  }

  /**
   * O subconjunto VIVO do `resultados.json`, recalculado do `caso`.
   *
   * Devolve `{cenarios: {<nome>: {premissas, valor: {preco_acao},
   * multiplo: {chave, valor}, vs_preco: {upside}, diagnosticos_chaves,
   * [degrau: {diagnosticos_chaves}], diagnosticos_exibidos, recusa}}}`, mais
   * `ponte: {nd_efetivo}` nas rotas que cruzam ponte (firm/rampa) — a rota
   * equity nao publica o bloco, do mesmo jeito que `resultados.json` nao
   * publica (L2: mesmas chaves). As chaves de diagnostico seguem as tres
   * formas descritas no cabecalho deste arquivo; `diagnosticos_exibidos` (F4)
   * e' a lista que o laboratorio pinta, e nao existe no `resultados`.
   *
   * Um cenario por vez, pela MESMA rota que `avaliar()` percorre
   * (`avaliar.py:881-934`):
   * - firm  : `precificarCelula('firm', ...)` — ramo EBITDA (ponte feita pelo
   *           motor) ou NOPAT (algebra do wrapper sobre o multiplo
   *           arredondado); os dois vivem dentro do espelho, nao aqui.
   * - equity: `precificarCelula('equity', ...)`, ou `precificarDegrau` quando
   *           o caso declara o bloco `degrau` — que so' existe nesta rota
   *           (`caso.py:_validar_degrau`, D2). Com degrau, o preco publicado
   *           e' o COM degrau e o multiplo de referencia vira
   *           `PVP_com_degrau` (o `com_transicao` do proprio degrau),
   *           exatamente a troca que `_aplicar_degrau_ao_cenario` (linha 668)
   *           e `_montar_manchete` (linhas 266-271) fazem do lado Python.
   * - rampa : `precificarRampa` — composicao bifasica inteira dentro do motor.
   */
  function avaliarCaso(caso) {
    const M = espelho();
    const rota = caso.rota;
    const metrica = { tipo: caso.metrica_base.tipo, valor: caso.metrica_base.valor };
    const acoes = caso.acoes_diluidas;
    const moeda = caso.moeda;
    // `mercado` e' bloco opcional (`caso.py:_validar_mercado`) — sem ele, `rf`
    // e' null, o mesmo que `avaliar.py:842` faz. `rf` chega em PONTO
    // PERCENTUAL (12.0 = 12%), como todo o resto do caso; quem converte e' o
    // espelho, nao esta fachada.
    const rf = caso.mercado ? caso.mercado.rf : null;
    const temPonte = ROTAS_COM_PONTE.has(rota);
    const ndEfetivo = temPonte ? ndEfetivoDe(caso.ponte) : 0.0;
    const chave = chaveDoMultiplo(rota, metrica.tipo);
    const blocoDegrau = rota === 'equity' ? (caso.degrau || null) : null;
    const precoDeTela = precoDeTelaDe(caso);

    const cenarios = {};
    for (const nome of Object.keys(caso.cenarios)) {
      const premissas = caso.cenarios[nome].premissas;

      if (rota === 'rampa') {
        const r = M.precificarRampa({ premissas, ndEfetivo, acoes, moeda, rf });
        // Diagnostico da rampa: os avisos presentes, na ordem de AVISOS_RAMPA.
        cenarios[nome] = r.recusado
          ? cenarioRecusado(premissas, chave, motivoDaRecusa(M, premissas))
          : cenarioPrecificado(premissas, r.valor.preco_acao, chave, r.multiplo, precoDeTela,
            r.avisos);
        continue;
      }

      if (blocoDegrau !== null) {
        // F3: a D6, sobre o caso EDITADO e antes de qualquer conta — a
        // combinacao que a metodologia proibe, alcancavel por um `select`.
        if (violaD6(M, premissas)) {
          cenarios[nome] = comDegrau(
            cenarioRecusado(premissas, 'PVP_com_degrau', RECUSA_DEGRAU_BOOK_SEM_ROE_BOOK), null);
          continue;
        }
        const r = M.precificarDegrau({
          premissas,
          metricaValor: metrica.valor,
          acoes,
          precoValor: precoDeTela,
          blocoDegrau: blocoDegrauCru(blocoDegrau),
          mValor: blocoDegrau.m[nome].valor,
        });
        // Diagnostico do degrau em duas listas, como o wrapper: as do cenario
        // (perna P/L) e as dos alertas do proprio degrau.
        cenarios[nome] = r.recusado
          ? comDegrau(
            cenarioRecusado(premissas, 'PVP_com_degrau', motivoDaRecusa(M, premissas)), null)
          : comDegrau(
            cenarioPrecificado(premissas, r.valor.preco_acao, 'PVP_com_degrau',
              r.degrau.com_transicao, precoDeTela,
              diagnosticosDaCelula(M, rota, premissas, moeda, rf)),
            r.degrau.diagnosticos_chaves);
        continue;
      }

      // `precificarCelula` recusa com `null` nos dois numeros; preco finito e
      // multiplo finito andam juntos (os dois saem do mesmo nucleo).
      const r = M.precificarCelula(rota, premissas, metrica, ndEfetivo, acoes);
      cenarios[nome] = Number.isFinite(r.valor)
        ? cenarioPrecificado(premissas, r.valor, chave, r.multiplo, precoDeTela,
          diagnosticosDaCelula(M, rota, premissas, moeda, rf))
        : cenarioRecusado(premissas, chave, motivoDaRecusa(M, premissas));
    }

    // F4: a lista exibivel, montada sobre o registro inteiro de cada cenario —
    // depois das tres pernas acima, para que nenhuma delas precise lembrar.
    for (const nome of Object.keys(cenarios)) {
      cenarios[nome].diagnosticos_exibidos = listaExibida(cenarios[nome]);
    }

    const vivo = { cenarios };
    if (temPonte) vivo.ponte = { nd_efetivo: ndEfetivo };
    return vivo;
  }

  function erroRelativo(python, js) {
    if (!Number.isFinite(python) || !Number.isFinite(js)) return null;
    return Math.abs(python - js) / Math.max(Math.abs(python), 1.0);
  }

  // Onde o `resultados` publica o multiplo que a fachada acabou de recalcular.
  // Fora do degrau e' `cenario.multiplos[<chave>]` direto; com degrau,
  // `PVP_com_degrau` nao mora em `multiplos` (que continua sendo o PL_curr/
  // PL_fwd integros da perna P/L, `_aplicar_degrau_ao_cenario` linhas 663-667)
  // — mora em `cenario.degrau.com_transicao`, que e' de onde
  // `_montar_manchete` (linhas 266-271) tira o multiplo daquele preco.
  function multiploPublicado(cenarioPython, chave) {
    if (chave === 'PVP_com_degrau') {
      return cenarioPython.degrau ? cenarioPython.degrau.com_transicao : undefined;
    }
    return cenarioPython.multiplos ? cenarioPython.multiplos[chave] : undefined;
  }

  function registrar(divergencias, cenario, chave, python, js) {
    const erro = erroRelativo(python, js);
    if (erro !== null && erro <= TAU) return;
    divergencias.push({
      cenario,
      chave,
      python: python === undefined ? null : python,
      js: js === undefined ? null : js,
      erro_relativo: erro,
    });
  }

  // Listas de chaves de diagnostico (Task 3, T4): IGUALDADE EXATA E ORDENADA —
  // a mesma chave na mesma posicao. A ordem nao e' enfeite: e' a ordem em que
  // o motor emite e o wrapper publica, e e' a ordem em que o laboratorio as
  // mostra. A divergencia leva as DUAS listas inteiras (`erro_relativo: null`,
  // o caso incomparavel): quem le o badge precisa ver o que sobrou e o que
  // faltou, nao um resumo.
  function mesmasChaves(python, js) {
    if (!Array.isArray(python) || !Array.isArray(js) || python.length !== js.length) return false;
    return python.every((chave, posicao) => chave === js[posicao]);
  }

  function registrarLista(divergencias, cenario, chave, python, js) {
    if (mesmasChaves(python, js)) return;
    divergencias.push({
      cenario,
      chave,
      python: python === undefined ? null : python,
      js: js === undefined ? null : js,
      erro_relativo: null,
    });
  }

  /**
   * O badge de paridade, como FATO: recomputa cada cenario do `caso` e compara
   * com o `resultados` publicado, numero a numero, na tolerancia dos harnesses
   * (TAU acima). Devolve `{ok, divergencias: [{cenario, chave, python, js,
   * erro_relativo}]}`.
   *
   * Verde significa que o motor do browser reproduz o que o Python publicou NA
   * MAQUINA DE QUEM ABRIU O ARQUIVO — a paridade de build ja' e' provada pelos
   * harnesses da suite; este e' outro fato. Vermelho nomeia o cenario, a chave
   * e os DOIS numeros: quem chama (o laboratorio) tem o suficiente para dizer
   * onde divergiu e travar a edicao, em vez de mostrar ao analista um numero
   * que o relatorio nao sustenta (L4).
   *
   * `erro_relativo: null` e' o caso incomparavel — a fachada recusou o cenario
   * (premissa fora de dominio) ou o `resultados` nao traz numero ali. Falha
   * FECHADA: entra como divergencia, nunca como "ok por ausencia".
   *
   * Contrato: um `resultados` cuja `versao_contrato` nao seja a que esta
   * fachada le REPROVA com excecao nomeada antes de qualquer comparacao (L2) —
   * uma v10 que troque a semantica de um campo tem de parar aqui, em voz alta,
   * nao desenhar numero errado em silencio.
   */
  function compararComResultados(caso, resultados) {
    const versao = (resultados === null || typeof resultados !== 'object')
      ? undefined : resultados.versao_contrato;
    if (versao !== VERSAO_CONTRATO) {
      throw recusa('contrato_desconhecido',
        `esta fachada le "${VERSAO_CONTRATO}"; o resultados declara `
        + `${JSON.stringify(versao)}. Comparar contratos diferentes e' desenhar `
        + 'numero errado em silencio.');
    }

    const vivo = avaliarCaso(caso);
    const cenariosPython = resultados.cenarios || {};
    const divergencias = [];

    for (const nome of Object.keys(vivo.cenarios)) {
      const js = vivo.cenarios[nome];
      const py = cenariosPython[nome];
      if (py === undefined || py === null) {
        // Cenario que o caso declara e o `resultados` nao publica: nao ha' o
        // que comparar, e seguir em silencio seria contar um cenario como
        // "batendo" por ausencia de contraparte.
        divergencias.push({
          cenario: nome,
          chave: 'cenario_ausente_no_resultados',
          python: null,
          js: js.valor.preco_acao,
          erro_relativo: null,
        });
        continue;
      }
      registrar(divergencias, nome, 'valor.preco_acao',
        py.valor ? py.valor.preco_acao : undefined, js.valor.preco_acao);
      registrar(divergencias, nome, js.multiplo.chave,
        multiploPublicado(py, js.multiplo.chave), js.multiplo.valor);
      // O terceiro numero publicado (Task 2). Nao e' redundante com o preco:
      // o preco pode bater e o upside divergir se a DEFINICAO divergir — e a
      // definicao e' justamente o que esta fachada passou a carregar em nome
      // do laboratorio.
      registrar(divergencias, nome, 'vs_preco.upside',
        py.vs_preco ? py.vs_preco.upside : undefined, js.vs_preco.upside);
      // Task 3 (T4): as chaves de diagnostico, nos dois lugares do contrato —
      // o que o laboratorio pinta ao lado dos tres numeros. Um motor de browser
      // que reproduzisse o preco mas acendesse outro alerta mostraria ao
      // analista um diagnostico que o relatorio nao sustenta.
      registrarLista(divergencias, nome, 'diagnosticos_chaves',
        py.diagnosticos_chaves, js.diagnosticos_chaves);
      if (js.degrau) {
        registrarLista(divergencias, nome, 'degrau.diagnosticos_chaves',
          py.degrau ? py.degrau.diagnosticos_chaves : undefined, js.degrau.diagnosticos_chaves);
      }
    }

    return { ok: divergencias.length === 0, divergencias };
  }

  // ---------------- exportacao: CommonJS (node) OU globalThis (browser) -----
  // Mesma disciplina do espelho (FIX 1 da revisao final da 4A):
  // `module.exports` incondicional estoura `ReferenceError: module is not
  // defined` num <script> de browser — que e' o consumidor REAL desta fachada.
  const publico = {
    VERSAO_CONTRATO, ROTAS_ATENDIDAS, MOTIVOS_DE_RECUSA, avaliarCaso, compararComResultados,
  };

  if (typeof module !== 'undefined' && typeof module.exports !== 'undefined') {
    module.exports = publico;
  } else {
    globalThis.FachadaEspelho = publico;
  }
}());
