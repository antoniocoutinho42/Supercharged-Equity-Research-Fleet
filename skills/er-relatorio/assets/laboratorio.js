/*
 * LABORATORIO DA ABA VALUATION -- item 5, fatia 5C, Task 2.
 *
 * SO INTERFACE. Este arquivo le campos do painel que `render.py` ja montou,
 * entrega o caso editado para `FachadaEspelho` e escreve na tela o que ela
 * devolver. Nao ha uma linha de metodologia aqui: nenhuma formula de valor,
 * nenhum limiar, nenhum nome de premissa escrito no codigo. Quem sabe que
 * campo existe, com que rotulo, unidade e widget, e o catalogo de
 * apresentacao -- lido no build, do lado do Python; quem sabe fazer a conta
 * e a camada de integracao, que esta pagina embute e chama. E a emenda E3
 * aplicada ao caso mais dificil do item 5, e ela e MECANIZADA:
 * `tests/test_relatorio_fronteira.py` varre este arquivo atras de qualquer
 * identificador do nucleo ou vocabulario de premissa, e a lista contra a
 * qual ele varre e DERIVADA do espelho e do catalogo -- nao uma lista
 * estatica que alguem precisa lembrar de atualizar. Um upgrade da
 * metodologia mexe no motor, no espelho e na fachada; nunca aqui.
 *
 * IIFE, e o arquivo inteiro nao declara UM identificador de topo. Nao e
 * estilo: varios <script> classicos compartilham o MESMO escopo lexico
 * global, e o espelho do nucleo sozinho ja declara ~55 nomes de topo. Um
 * `const`/`function` de topo aqui que colidisse com um deles mataria o
 * segundo <script> inteiro (`SyntaxError: Identifier ... has already been
 * declared`) -- e o sintoma nao seria um numero errado, seria a aba em
 * branco. O mesmo erro derrubou a primeira versao da fachada (Task 1), e
 * `tests/test_relatorio_laboratorio.py` carrega TODOS os modulos da pagina
 * no MESMO contexto para provar que nenhum deles se atropela.
 *
 * FORMATACAO: tabela propria (`SEPARADORES_POR_IDIOMA`), duplicada de
 * proposito de `placeholders._SEPARADORES` (Python) -- mesmo motivo ja
 * registrado em `graficos.js` e `svg.js`: um modulo de browser nunca importa
 * Python, e os tres modulos entram na pagina de forma INDEPENDENTE, entao um
 * nao pode depender do outro estar carregado. As CASAS, a escala, o prefixo
 * e o sufixo de cada numero NAO moram aqui -- chegam prontos no payload,
 * montados por `render.py` a partir das unidades que o contrato declara.
 *
 * SEM PROSA: toda string de interface chega em `dados.textos`, do dicionario
 * (secao 16.1). O unico literal de texto deste arquivo e o travessao de
 * "sem valor", que so vale como padrao quando quem chama nao passa o do
 * dicionario.
 *
 * SEM REDE, SEM RELOGIO, SEM ARMAZENAMENTO (L8): o painel roda inteiro no
 * arquivo aberto. O estado editado vive so na pagina -- fechar o relatorio
 * apaga tudo, e reabrir devolve a calibracao original.
 */
(function (root) {
  "use strict";

  var SEPARADORES_POR_IDIOMA = { "pt-BR": { milhar: ".", decimal: "," } };
  var SEM_VALOR_PADRAO = "—";

  // ----------------------------------------------------------------------
  // Utilitarios puros (sem DOM): formatacao e substituicao de marcadores.
  // ----------------------------------------------------------------------

  function numeroLocalizado(valor, casas, idioma) {
    var separadores = SEPARADORES_POR_IDIOMA[idioma] || SEPARADORES_POR_IDIOMA["pt-BR"];
    var negativo = valor < 0;
    var texto = Math.abs(valor).toFixed(casas);
    var partes = texto.split(".");
    var parteInteira = partes[0];
    var parteDecimal = partes.length > 1 ? partes[1] : "";

    var grupos = [];
    while (parteInteira.length > 3) {
      grupos.unshift(parteInteira.slice(-3));
      parteInteira = parteInteira.slice(0, -3);
    }
    grupos.unshift(parteInteira);
    var inteiroFormatado = grupos.join(separadores.milhar);

    var formatado = casas === 0
      ? inteiroFormatado
      : inteiroFormatado + separadores.decimal + parteDecimal;
    if (negativo && parseFloat(texto) !== 0) {
      formatado = "-" + formatado;
    }
    return formatado;
  }

  // `espec` e a RECEITA que `render.py` montou a partir da unidade declarada
  // ({casas, escala, prefixo, sufixo}) -- exatamente o mesmo formato que
  // `svg.js` ja consome. Valor nao numerico ou nao finito (inclusive `null`,
  // o jeito que a fachada recusa um cenario) devolve o texto de "sem valor":
  // este painel nunca desenha um numero que a integracao nao produziu.
  function formatar(valor, espec, idioma, textoVazio) {
    var vazio = typeof textoVazio === "string" ? textoVazio : SEM_VALOR_PADRAO;
    if (typeof valor !== "number" || !isFinite(valor)) {
      return vazio;
    }
    espec = espec || {};
    var casas = typeof espec.casas === "number" ? espec.casas : 2;
    var escala = typeof espec.escala === "number" ? espec.escala : 1;
    var prefixo = typeof espec.prefixo === "string" ? espec.prefixo : "";
    var sufixo = typeof espec.sufixo === "string" ? espec.sufixo : "";
    return prefixo + numeroLocalizado(valor * escala, casas, idioma || "pt-BR") + sufixo;
  }

  // Substitui `{marcador}` num modelo do dicionario. `split`/`join` em vez de
  // expressao regular: o valor substituido pode conter qualquer caractere, e
  // nenhuma escapada precisa ser inventada aqui.
  function textoDe(modelo, valores) {
    var saida = String(modelo === undefined || modelo === null ? "" : modelo);
    var nomeMarcador;
    for (nomeMarcador in valores) {
      if (Object.prototype.hasOwnProperty.call(valores, nomeMarcador)) {
        saida = saida.split("{" + nomeMarcador + "}").join(String(valores[nomeMarcador]));
      }
    }
    return saida;
  }

  function copiaProfunda(objeto) {
    return JSON.parse(JSON.stringify(objeto));
  }

  // ----------------------------------------------------------------------
  // Badge de paridade (L4): um FATO medido na maquina de quem abriu o
  // arquivo, nao um enfeite. Verde: o motor do navegador reproduz todos os
  // numeros publicados. Vermelho: nomeia cenario, campo e os DOIS numeros, e
  // a edicao fica bloqueada -- um editor cujo motor discorda do relatorio
  // mostraria ao analista um numero que o relatorio nao sustenta.
  // ----------------------------------------------------------------------

  // Os dois lados da divergencia saem CRUS, de proposito. Aplicar a receita
  // de apresentacao arredondaria justamente a diferenca que o badge existe
  // para denunciar (6,69 e 6,69 imprimem igual), e o campo divergente pode
  // ser preco, multiplo ou razao -- tres unidades distintas, que este arquivo
  // nao tem como distinguir sem passar a conhecer o vocabulario da fachada.
  // Uma LISTA de chaves de diagnostico (Task 3) sai crua pelo mesmo motivo:
  // pintada pelo catalogo, duas chaves sem rotulo imprimiriam o mesmo texto e
  // a divergencia sumiria justamente da mensagem que existe para mostra-la.
  function valorCru(valor, vazio) {
    if (typeof valor === "number" && isFinite(valor)) { return String(valor); }
    if (Array.isArray(valor)) { return JSON.stringify(valor); }
    return vazio;
  }

  function pintarBadge(alvo, estado, texto, itens) {
    if (!alvo) { return; }
    alvo.setAttribute("data-estado", estado);
    while (alvo.firstChild) { alvo.removeChild(alvo.firstChild); }

    var paragrafo = alvo.ownerDocument.createElement("p");
    paragrafo.textContent = texto;
    alvo.appendChild(paragrafo);

    if (!itens || !itens.length) { return; }
    var lista = alvo.ownerDocument.createElement("ul");
    var indice;
    for (indice = 0; indice < itens.length; indice++) {
      var item = alvo.ownerDocument.createElement("li");
      item.textContent = itens[indice];
      lista.appendChild(item);
    }
    alvo.appendChild(lista);
  }

  function travarEdicao(raiz) {
    var bloqueaveis = raiz.querySelectorAll(
      "[data-laboratorio-entrada], [data-laboratorio-restaurar]");
    var indice;
    for (indice = 0; indice < bloqueaveis.length; indice++) {
      bloqueaveis[indice].disabled = true;
    }
    // As linhas da ponte (fatia 5I, Task 4) sao editaveis e moram FORA da raiz: sem
    // isto, o badge vermelho travaria o painel e deixaria o degrau editavel.
    var daPonte = linhasDaPonte(raiz.ownerDocument);
    for (indice = 0; indice < daPonte.length; indice++) {
      if (daPonte[indice].campo) { daPonte[indice].campo.disabled = true; }
    }
  }

  // As linhas do degrau, com a chave do catalogo e o campo de entrada de cada uma. O
  // seletor sai em DOIS passos (o portador, depois o campo) de proposito: nao ha'
  // combinador de descendencia aqui, e o portador e' quem carrega a chave.
  function linhasDaPonte(documento) {
    var portadores = documento.querySelectorAll("[data-ponte-linha]");
    var linhas = [];
    var indice;
    for (indice = 0; indice < portadores.length; indice++) {
      linhas.push({
        chave: portadores[indice].getAttribute("data-ponte-linha"),
        campo: portadores[indice].querySelector("[data-laboratorio-entrada]")
      });
    }
    return linhas;
  }

  // ----------------------------------------------------------------------
  // Leitura dos campos e escrita das saidas.
  // ----------------------------------------------------------------------

  function nomeDaPremissa(campo) {
    var portador = campo.closest("[data-laboratorio-premissa]");
    return portador ? portador.getAttribute("data-laboratorio-premissa") : null;
  }

  // Monta o caso EDITADO sem tocar no original (secao 8.3 do desenho: o
  // usuario simula "sem sobrescrever a calibracao original"). A base e sempre
  // uma copia do caso embutido, e so os campos editaveis a sobrescrevem --
  // por isso um campo desabilitado (premissa que o catalogo nao conhece)
  // segue valendo no calculo com o valor que o caso declarou.
  //
  // Campo numerico vazio ou ilegivel nao vira zero nem volta em silencio ao
  // valor original: marca o campo e cega as saidas DAQUELE cenario.
  // A configuracao do triangulo daquele cenario (fatia 5I, Task 4, D7): o valor da
  // opcao e' a VARIAVEL DE SAIDA, e o payload traz a configuracao inteira ({inputs,
  // output}) de cada uma das tres. Este arquivo nao monta configuracao nenhuma nem
  // conhece o vocabulario da identidade -- ele escolhe uma entre as que chegaram.
  function configuracaoDoTriangulo(bloco, nomeCenario, dados) {
    var seletor = bloco.querySelector("[data-laboratorio-triangulo]");
    if (!seletor) { return null; }
    var porSaida = (dados.triangulos || {})[nomeCenario] || {};
    return Object.prototype.hasOwnProperty.call(porSaida, seletor.value) ? porSaida[seletor.value] : null;
  }

  function colher(raiz, base, dados) {
    var editado = copiaProfunda(base);
    var cegos = {};
    var blocos = raiz.querySelectorAll("[data-laboratorio-cenario]");
    var indice;
    for (indice = 0; indice < blocos.length; indice++) {
      var nomeCenario = blocos[indice].getAttribute("data-laboratorio-cenario");
      var registro = editado.cenarios ? editado.cenarios[nomeCenario] : null;
      var destino = registro ? registro.premissas : null;
      var configuracao = configuracaoDoTriangulo(blocos[indice], nomeCenario, dados);
      if (registro && configuracao) { registro.triangulo = configuracao; }
      var campos = blocos[indice].querySelectorAll("[data-laboratorio-entrada]");
      var posicao;
      for (posicao = 0; posicao < campos.length; posicao++) {
        var campo = campos[posicao];
        var nome = nomeDaPremissa(campo);
        var tipo = campo.getAttribute("data-laboratorio-entrada");
        // A variavel de SAIDA do triangulo e' derivada, nao entrada: quem a resolve e'
        // a integracao, pela identidade. Ela nao entra no vetor editado e nunca cega o
        // cenario por estar vazia -- o campo dela e' visor, nao campo.
        if (configuracao && nome !== null && nome === configuracao.output) { continue; }
        if (tipo === "booleano") {
          if (destino && nome) { destino[nome] = campo.checked; }
          continue;
        }
        if (tipo === "escolha") {
          if (destino && nome) { destino[nome] = campo.value; }
          continue;
        }
        var lido = Number(campo.value);
        var semTexto = String(campo.value).trim() === "";
        // Campo que o CASO nao declara (`data-laboratorio-opcional`: a variavel do
        // triangulo que nao e premissa da rota): vazio nele quer dizer NAO DECLARADO, nao
        // "nao sei". O vetor segue sem a chave, exatamente como o caso a declara, e o
        // cenario NAO cega. Cegar aqui apagava a pagina inteira na carga de um caso cuja
        // configuracao declara essa variavel como ENTRADA — sem numero no cenario, sem
        // leitura do que esta no preco, sem tabela 1D e sem matriz, e sem erro nenhum.
        // Valor ILEGIVEL (texto que nao vira numero) continua cegando: ai o analista
        // declarou algo, e o algo nao fecha.
        if (semTexto && campo.getAttribute("data-laboratorio-opcional") !== null) {
          campo.removeAttribute("aria-invalid");
          continue;
        }
        if (semTexto || !isFinite(lido)) {
          campo.setAttribute("aria-invalid", "true");
          cegos[nomeCenario] = true;
          continue;
        }
        campo.removeAttribute("aria-invalid");
        if (destino && nome) { destino[nome] = lido; }
      }
    }

    // O degrau da ponte (D8): cada linha escreve a SUA chave no bloco `ponte` do caso
    // editado. Quem soma as linhas em `nd_efetivo` e' a integracao -- este arquivo nao
    // conhece sinal nem ordem. Linha ilegivel vira `null`: a fachada a recusa pelo nome
    // (`ponte_incompleta`) e a pagina inteira fica sem numero, que e' a verdade -- sem
    // uma linha do balanco nao existe divida liquida, e nenhum cenario se sustenta.
    var linhas = linhasDaPonte(raiz.ownerDocument);
    for (indice = 0; indice < linhas.length; indice++) {
      var entrada = linhas[indice].campo;
      if (!entrada || !editado.ponte) { continue; }
      var lidoDaLinha = Number(entrada.value);
      if (String(entrada.value).trim() === "" || !isFinite(lidoDaLinha)) {
        entrada.setAttribute("aria-invalid", "true");
        editado.ponte[linhas[indice].chave] = null;
        continue;
      }
      entrada.removeAttribute("aria-invalid");
      editado.ponte[linhas[indice].chave] = lidoDaLinha;
    }
    return { caso: editado, cegos: cegos };
  }

  function escreverSaida(bloco, papel, texto) {
    var alvo = bloco.querySelector('[data-laboratorio-saida="' + papel + '"]');
    if (alvo) { alvo.textContent = texto; }
  }

  // ----------------------------------------------------------------------
  // O QUE ESTA NO PRECO e as SENSIBILIDADES, vivas (fatia 5I, Task 3; secao
  // 8.4). Ate aqui estes tres blocos eram numero CONGELADO ao lado do painel
  // editavel -- e a secao 8.4 proibe exatamente isso. Desde o lote 1 a fachada
  // recalcula a leitura de cada eixo, as duas grades e o teto a cada chamada,
  // e este arquivo passa a reescrever a tela com o que ela devolve.
  //
  // Nenhum nome de campo da leitura mora aqui. O payload traz DESCRITORES
  // (`dados.reversa.campos`) montados por `render.py` a partir de UMA
  // declaracao: onde ler (`de`, `lista`), como exibir (`unidade` -- o caminho
  // da unidade que a propria leitura declara --, `formato` ou `vocabulario`) e
  // o modelo do dicionario que compoe o texto. Este modulo so' percorre
  // caminho, formata pela receita e escreve. Uma leitura com um campo novo
  // chega a tela sem uma linha aqui, e a trava de `tests/test_relatorio_
  // fronteira.py` continua valendo palavra por palavra.
  //
  // Os elementos sao RECRIADOS a cada edicao, nunca so' atualizados: uma raiz
  // a mais, um CAP que fecha, um teto que aparece -- a lista muda de tamanho,
  // e um slot fixo esconderia o que passou a existir.
  // ----------------------------------------------------------------------

  function percorrer(no, caminho) {
    var atual = no;
    var indice;
    for (indice = 0; indice < caminho.length; indice++) {
      if (atual === null || atual === undefined) { return null; }
      atual = atual[caminho[indice]];
    }
    return atual === undefined ? null : atual;
  }

  function receitaDe(espec, leitura, dados) {
    if (espec.formato) { return espec.formato; }
    return (dados.formatosPorUnidade || {})[percorrer(leitura, espec.unidade)];
  }

  function rotuloDoCodigo(dados, vocabulario, codigo) {
    var mapa = (dados.vocabularios || {})[vocabulario] || {};
    var textos = dados.textos || {};
    return (Object.prototype.hasOwnProperty.call(mapa, codigo) && mapa[codigo])
      ? mapa[codigo] : (textos.rotuloDesconhecido || "");
  }

  // O texto de um marcador do modelo, ou `null` quando o valor nao existe -- e
  // ai o campo INTEIRO nao sai. `vazio` e a excecao declarada pelo payload: o
  // texto do dicionario para o valor que pode faltar sem derrubar a linha.
  function textoDoValor(no, leitura, espec, dados) {
    var vazio = (dados.textos && dados.textos.semValor) || SEM_VALOR_PADRAO;
    var bruto = percorrer(no, espec.de);
    if (espec.juntar !== undefined) {
      if (!Array.isArray(bruto) || !bruto.length) { return null; }
      var partes = [];
      var indice;
      for (indice = 0; indice < bruto.length; indice++) {
        partes.push(formatar(bruto[indice], receitaDe(espec, leitura, dados), dados.idioma, vazio));
      }
      return partes.join(espec.juntar);
    }
    if (bruto === null) { return espec.vazio !== undefined ? espec.vazio : null; }
    if (espec.vocabulario) { return rotuloDoCodigo(dados, espec.vocabulario, bruto); }
    return formatar(bruto, receitaDe(espec, leitura, dados), dados.idioma, vazio);
  }

  function textoDoCampo(no, leitura, campo, dados) {
    var valores = {};
    var marcador;
    for (marcador in campo.valores) {
      if (Object.prototype.hasOwnProperty.call(campo.valores, marcador)) {
        var texto = textoDoValor(no, leitura, campo.valores[marcador], dados);
        if (texto === null) { return null; }
        valores[marcador] = texto;
      }
    }
    return campo.modelo === undefined ? valores.valor : textoDe(campo.modelo, valores);
  }

  function elementoDe(documento, tag, classe, papel, texto) {
    var elemento = documento.createElement(tag);
    elemento.setAttribute("class", classe);
    if (papel !== null) { elemento.setAttribute("data-laboratorio-saida", papel); }
    if (texto !== null) { elemento.textContent = texto; }
    return elemento;
  }

  function esvaziar(elemento) {
    while (elemento.firstChild) { elemento.removeChild(elemento.firstChild); }
  }

  function itemDaLista(documento, valor, leitura, campo, dados) {
    var item = elementoDe(documento, campo.item.tag, campo.item.classe, null, null);
    var escritos = 0;
    var indice;
    for (indice = 0; indice < campo.item.campos.length; indice++) {
      var sub = campo.item.campos[indice];
      var texto = textoDoCampo(valor, leitura, sub, dados);
      if (texto === null) { continue; }
      // O separador que o HTML do build tem entre os pedacos da mesma linha:
      // sem ele, dois campos vizinhos sairiam colados na tela.
      if (escritos) { item.appendChild(documento.createTextNode(" ")); }
      item.appendChild(elementoDe(documento, sub.tag, sub.classe, sub.papel, texto));
      escritos += 1;
    }
    return item;
  }

  function pintarLeitura(corpo, leitura, dados) {
    var documento = corpo.ownerDocument;
    esvaziar(corpo);
    if (!leitura) { return; }
    var campos = (dados.reversa && dados.reversa.campos) || [];
    var indice;
    for (indice = 0; indice < campos.length; indice++) {
      var campo = campos[indice];
      if (campo.lista) {
        var itens = percorrer(leitura, campo.lista);
        if (!Array.isArray(itens) || !itens.length) { continue; }
        var container = elementoDe(documento, campo.tag, campo.classe, campo.papel, null);
        var posicao;
        for (posicao = 0; posicao < itens.length; posicao++) {
          container.appendChild(itemDaLista(documento, itens[posicao], leitura, campo, dados));
        }
        corpo.appendChild(container);
        continue;
      }
      var texto = textoDoCampo(leitura, leitura, campo, dados);
      if (texto === null) { continue; }
      corpo.appendChild(elementoDe(documento, campo.tag, campo.classe, campo.papel, texto));
    }
  }

  // O teto do crescimento gratuito existe SO' enquanto um eixo primario nao
  // fecha: ele aparece e some com a edicao, e por isso o bloco inteiro nasce e
  // morre aqui, em vez de ter um slot permanente que ficaria vazio.
  function pintarTeto(host, teto, dados) {
    var documento = host.ownerDocument;
    esvaziar(host);
    if (!teto || !dados.reversa) { return; }
    var espec = dados.reversa.teto;
    var vazio = (dados.textos && dados.textos.semValor) || SEM_VALOR_PADRAO;
    var bloco = elementoDe(documento, "div", "reversa-teto", null, null);
    var titulo = documento.createElement("h3");
    titulo.textContent = espec.rotulo;
    bloco.appendChild(titulo);
    bloco.appendChild(elementoDe(documento, "p", "reversa-teto-multiplo", null, textoDe(espec.modelo, {
      valor: formatar(teto.multiplo, espec.formato, dados.idioma, vazio),
      multiplo: (dados.rotulosMultiplos || {})[teto.chave] || ""
    })));
    bloco.appendChild(elementoDe(documento, "p", "reversa-teto-texto", null, espec.texto));
    host.appendChild(bloco);
  }

  function pintarLimitacoes(host, lista, dados) {
    var documento = host.ownerDocument;
    esvaziar(host);
    if (!Array.isArray(lista) || !lista.length) { return; }
    var container = elementoDe(documento, "ul", "reversa-limitacoes", null, null);
    var indice;
    for (indice = 0; indice < lista.length; indice++) {
      var item = documento.createElement("li");
      item.textContent = rotuloDoCodigo(dados, "limitacoes", lista[indice]);
      container.appendChild(item);
    }
    host.appendChild(container);
  }

  function pintarReversa(documento, reversa, dados) {
    var artigos = documento.querySelectorAll("[data-laboratorio-eixo]");
    var indice;
    for (indice = 0; indice < artigos.length; indice++) {
      var corpo = artigos[indice].querySelector("[data-laboratorio-corpo]");
      if (!corpo) { continue; }
      var nome = artigos[indice].getAttribute("data-laboratorio-eixo");
      var eixo = (reversa && reversa.eixos) ? reversa.eixos[nome] : null;
      // Eixo que a fachada recusou publica `leitura` nula -- o motor de verdade
      // nao procurou raiz nenhuma, e o corpo fica vazio em vez de repetir a
      // leitura anterior, que seria a leitura de OUTRO vetor.
      pintarLeitura(corpo, eixo ? eixo.leitura : null, dados);
    }
    var hostDoTeto = documento.querySelector("[data-laboratorio-teto]");
    if (hostDoTeto) { pintarTeto(hostDoTeto, reversa ? reversa.teto_do_crescimento_gratuito : null, dados); }
    var hostDasLimitacoes = documento.querySelector("[data-laboratorio-limitacoes]");
    if (hostDasLimitacoes) { pintarLimitacoes(hostDasLimitacoes, reversa ? reversa.limitacoes : null, dados); }
  }

  // As premissas do cenario que as grades perturbam, no caso EDITADO: a marca
  // do ponto e a celula-base saem da comparacao exata contra elas (a regra que
  // `render.py` aplica no build e o `svg.js`, no desenho). Sem isto a marca
  // vermelha continuaria no ponto do vetor ORIGINAL depois da edicao.
  function premissasDasGrades(caso, espec) {
    var cenario = (caso.cenarios || {})[espec.cenario];
    return cenario ? (cenario.premissas || {}) : {};
  }

  function baseDaMatriz(premissas, grade) {
    var x = premissas[grade.premissa_x];
    var y = premissas[grade.premissa_y];
    if (typeof x !== "number" || !isFinite(x) || typeof y !== "number" || !isFinite(y)) { return null; }
    return { x: x, y: y };
  }

  function pintarGrades1D(documento, vivas, dados, premissas) {
    var espec = dados.sensibilidades;
    var vazio = (dados.textos && dados.textos.semValor) || SEM_VALOR_PADRAO;
    var secoes = documento.querySelectorAll("[data-laboratorio-grade]");
    var indice;
    for (indice = 0; indice < secoes.length; indice++) {
      var posicao = Number(secoes[indice].getAttribute("data-laboratorio-grade"));
      var receita = espec.grades1d[posicao];
      var grade = vivas ? vivas.grades_1d[posicao] : null;
      if (!receita) { continue; }
      var linhas = secoes[indice].querySelectorAll("[data-laboratorio-linha]");
      var linha;
      for (linha = 0; linha < linhas.length; linha++) {
        var celula = grade ? grade.pontos[Number(linhas[linha].getAttribute("data-laboratorio-linha"))] : null;
        var ponto = celula ? formatar(celula.x, receita.formatoPonto, dados.idioma, vazio) : vazio;
        if (celula && premissas[grade.premissa] === celula.x) {
          ponto = textoDe(receita.modeloPonto, { valor: ponto, cenario: espec.cenario });
        }
        escreverSaida(linhas[linha], "ponto", ponto);
        escreverSaida(linhas[linha], "preco",
          celula ? formatar(celula.valor, receita.formatoValor, dados.idioma, vazio) : vazio);
        escreverSaida(linhas[linha], "multiplo",
          celula ? formatar(celula.multiplo, receita.formatoMultiplo, dados.idioma, vazio) : vazio);
      }
    }
  }

  function pintarMatrizes(documento, vivas, dados, premissas) {
    var espec = dados.sensibilidades;
    var hosts = documento.querySelectorAll("[data-laboratorio-matriz]");
    var indice;
    for (indice = 0; indice < hosts.length; indice++) {
      var posicao = Number(hosts[indice].getAttribute("data-laboratorio-matriz"));
      var opcoes = espec.matrizes[posicao];
      var grade = vivas ? vivas.grades_2d[posicao] : null;
      if (!opcoes) { continue; }
      if (!grade || typeof root.FleetSVG === "undefined") {
        hosts[indice].innerHTML = "";
        continue;
      }
      hosts[indice].innerHTML = root.FleetSVG.matriz(grade, {
        base: baseDaMatriz(premissas, grade),
        rotuloX: opcoes.rotuloX,
        rotuloY: opcoes.rotuloY,
        formato: opcoes.formato,
        formatoX: opcoes.formatoX,
        formatoY: opcoes.formatoY,
        idioma: dados.idioma
      });
    }
  }

  // O waterfall redesenhado a cada mudanca de degrau (D8). As parcelas sao as do
  // payload -- chave, rotulo e sinal, do catalogo -- com o valor que o caso EDITADO
  // declara; o total e' o `nd_efetivo` que a integracao recompos, nunca a soma feita
  // aqui. E' a mesma disciplina do bootstrap estatico: este modulo desenha, nao soma.
  function pintarPonte(documento, vivo, dados, caso) {
    var espec = dados.ponte;
    var host = documento.querySelector("[data-laboratorio-ponte]");
    if (!espec || !host) { return; }
    if (!vivo || !vivo.ponte || typeof root.FleetSVG === "undefined") {
      host.innerHTML = "";
      return;
    }
    var daPonte = caso.ponte || {};
    var parcelas = [];
    var indice;
    for (indice = 0; indice < espec.parcelas.length; indice++) {
      var parcela = espec.parcelas[indice];
      parcelas.push({
        chave: parcela.chave,
        rotulo: parcela.rotulo,
        sinal: parcela.sinal,
        valor: daPonte[parcela.chave]
      });
    }
    host.innerHTML = root.FleetSVG.waterfall(parcelas, {
      total: { rotulo: espec.total.rotulo, valor: vivo.ponte.nd_efetivo },
      formato: espec.formato
    });
  }

  // A variavel que a configuracao declara como SAIDA e' derivada: o campo dela vira
  // visor -- desabilitado, com o numero que a integracao resolveu. Trocar a
  // configuracao troca QUAL campo e' o visor, e nada mais: o valor original ao lado de
  // cada campo nao se move, e o botao de restaurar devolve a calibracao inteira,
  // configuracao inclusive (secao 8.3).
  function escreverTriangulo(bloco, triangulo) {
    var campos = bloco.querySelectorAll("[data-laboratorio-entrada]");
    var indice;
    for (indice = 0; indice < campos.length; indice++) {
      var nome = nomeDaPremissa(campos[indice]);
      if (nome === null) { continue; }
      var derivado = !!triangulo && nome === triangulo.variavel;
      campos[indice].disabled = derivado;
      if (derivado) {
        // Identidade que NAO fecha (falta a terceira variavel, que o caso nao declara)
        // deixa o campo como esta: o vetor EM VIGOR e' o declarado, e apagar o numero
        // deixaria a tela em branco ao lado de um preco calculado com ele.
        if (typeof triangulo.valor === "number" && isFinite(triangulo.valor)) {
          campos[indice].value = String(triangulo.valor);
        }
        campos[indice].removeAttribute("aria-invalid");
      }
    }
  }

  function pintarSensibilidades(documento, vivo, dados, caso, cegos) {
    var espec = dados.sensibilidades;
    if (!espec) { return; }
    // Cenario cego (campo numerico ilegivel) cega TAMBEM as grades: elas
    // perturbam o vetor daquele cenario, e mostrar celula calculada com o
    // valor que o campo deixou de declarar seria numero sem premissa.
    var vivas = (vivo && vivo.sensibilidades && !cegos[espec.cenario]) ? vivo.sensibilidades : null;
    var premissas = premissasDasGrades(caso, espec);
    pintarGrades1D(documento, vivas, dados, premissas);
    pintarMatrizes(documento, vivas, dados, premissas);
  }

  // ----------------------------------------------------------------------
  // Diagnosticos do cenario (Task 3; secao 8.4 do desenho: o diagnostico se
  // move junto com o numero). As chaves chegam da FACHADA numa lista so,
  // `diagnosticos_exibidos`, que a integracao monta a partir das formas do
  // contrato -- este painel nao conhece forma nenhuma nem caminho de contrato
  // (onda de correcao da revisao final da 5C, F4: uma forma aditiva de uma v10
  // chega a tela sem uma linha aqui). Ele so as PINTA, na ordem em que chegam:
  // rotulo e severidade vem do catalogo, pelo payload (`dados.diagnosticos`).
  // Nenhuma chave e interpretada aqui e nenhum predicado e avaliado aqui; a
  // severidade so vira classe CSS. Chave que o payload nao rotula vira o texto
  // do dicionario, nunca a chave crua (licao do B2).
  // ----------------------------------------------------------------------

  function escreverDiagnosticos(bloco, registro, dados) {
    var lista = bloco.querySelector("[data-laboratorio-diagnosticos]");
    if (!lista) { return; }
    while (lista.firstChild) { lista.removeChild(lista.firstChild); }
    var textos = dados.textos || {};
    var rotulados = dados.diagnosticos || {};

    function acrescentar(classe, texto) {
      var item = lista.ownerDocument.createElement("li");
      item.setAttribute("class", classe);
      item.textContent = texto;
      lista.appendChild(item);
    }

    // Sem numero, sem diagnostico: o mesmo "sem valor" das tres saidas.
    if (!registro) {
      acrescentar("lab-diagnostico lab-diagnostico-vazio", textos.semValor || SEM_VALOR_PADRAO);
      return;
    }
    // Cenario RECUSADO pela fachada (onda de correcao da revisao final da 5C,
    // F2 e F3): as tres saidas ja estao em "sem valor", e a lista diz por que.
    // O motivo chega como CODIGO e o rotulo vem do catalogo, pelo payload
    // (`dados.recusas`). Nunca o texto de "nenhum diagnostico" -- que seria
    // falso -- e nunca o codigo cru: motivo sem rotulo vira texto do dicionario.
    if (registro.recusa) {
      var rotulosDeRecusa = dados.recusas || {};
      var codigo = registro.recusa.codigo;
      var motivo = (typeof codigo === "string"
        && Object.prototype.hasOwnProperty.call(rotulosDeRecusa, codigo) && rotulosDeRecusa[codigo])
        ? rotulosDeRecusa[codigo] : (textos.recusaDesconhecida || "");
      acrescentar("lab-diagnostico lab-diagnostico-recusado",
        textoDe(textos.diagnosticosRecusado, { motivo: motivo }));
      return;
    }
    // Um registro sem lista exibivel cai no "sem valor" -- este painel nunca
    // afirma "nenhum diagnostico" sem uma lista que o diga.
    if (!Array.isArray(registro.diagnosticos_exibidos)) {
      acrescentar("lab-diagnostico lab-diagnostico-vazio", textos.semValor || SEM_VALOR_PADRAO);
      return;
    }
    var chaves = registro.diagnosticos_exibidos;
    if (!chaves.length) {
      acrescentar("lab-diagnostico lab-diagnostico-vazio", textos.diagnosticosNenhum || "");
      return;
    }
    var indice;
    for (indice = 0; indice < chaves.length; indice++) {
      var info = Object.prototype.hasOwnProperty.call(rotulados, chaves[indice])
        ? rotulados[chaves[indice]] : null;
      if (info && typeof info.rotulo === "string" && info.rotulo) {
        acrescentar(typeof info.severidade === "string" && info.severidade
          ? "lab-diagnostico lab-diagnostico-" + info.severidade : "lab-diagnostico",
          info.rotulo);
      } else {
        acrescentar("lab-diagnostico lab-diagnostico-desconhecido",
          textos.diagnosticoDesconhecido || "");
      }
    }
  }

  function escrever(raiz, vivo, cegos, dados, caso) {
    var idioma = dados.idioma;
    var vazio = (dados.textos && dados.textos.semValor) || SEM_VALOR_PADRAO;
    var rotulos = dados.rotulosMultiplos || {};
    var formatos = dados.formatos || {};
    var blocos = raiz.querySelectorAll("[data-laboratorio-cenario]");
    var indice;
    for (indice = 0; indice < blocos.length; indice++) {
      var bloco = blocos[indice];
      var nomeCenario = bloco.getAttribute("data-laboratorio-cenario");
      var registro = (vivo && vivo.cenarios && !cegos[nomeCenario])
        ? vivo.cenarios[nomeCenario] : null;
      if (!registro) {
        escreverSaida(bloco, "preco", vazio);
        escreverSaida(bloco, "multiplo", vazio);
        escreverSaida(bloco, "multiplo-rotulo", "");
        escreverSaida(bloco, "upside", vazio);
        escreverSaida(bloco, "teto-alavanca", "");
        escreverDiagnosticos(bloco, null, dados);
        continue;
      }
      escreverSaida(bloco, "preco",
        formatar(registro.valor.preco_acao, formatos.preco, idioma, vazio));
      escreverSaida(bloco, "multiplo",
        formatar(registro.multiplo.valor, formatos.multiplo, idioma, vazio));
      escreverSaida(bloco, "multiplo-rotulo", rotulos[registro.multiplo.chave] || "");
      escreverSaida(bloco, "upside",
        formatar(registro.vs_preco.upside, formatos.upside, idioma, vazio));
      // D10: o cenario cujo degrau acende a chave viva sai rotulado como NAO-CENARIO. O
      // predicado e' da integracao (um booleano no registro); o rotulo e o texto sao do
      // catalogo, pelo payload. O rotulo acende e apaga com o numero, na mesma chamada.
      escreverSaida(bloco, "teto-alavanca", registro.teto_da_alavanca
        ? textoDe((dados.textos || {}).tetoDaAlavanca, dados.tetoDaAlavanca || {}) : "");
      escreverTriangulo(bloco, registro.triangulo);
      escreverDiagnosticos(bloco, registro, dados);
    }

    // Fatia 5I, Task 3: os blocos vivos que moram FORA do painel -- a leitura
    // do que esta no preco e as sensibilidades sao secoes da aba, nao filhas de
    // `[data-laboratorio]`. O badge chega como parametro porque e' um elemento
    // so' e o painel inteiro depende dele; estes sao varios e mudam de numero
    // com a entrega, e saem do documento da propria raiz -- que no browser e' o
    // `document` que o bootstrap consultou.
    var documento = raiz.ownerDocument;
    if (dados.reversa) {
      pintarReversa(documento, (vivo && !cegos[dados.reversa.cenario]) ? vivo.reversa : null, dados);
    }
    pintarSensibilidades(documento, vivo, dados, caso, cegos);
    pintarPonte(documento, vivo, dados, caso);
  }

  // ----------------------------------------------------------------------
  // Ciclo: colher -> pedir a fachada -> escrever. Uma unica chamada por
  // mudanca: a fachada avalia o caso inteiro, todos os cenarios de uma vez.
  // ----------------------------------------------------------------------

  // D13: desde o lote 1 um redesenho custa a reversa inteira (milhares de
  // avaliacoes de forma fechada por eixo) mais as duas grades, e o ouvinte de
  // `input` dispara a cada TECLA -- digitar "12.5" pedia quatro. O agrupador
  // deixa passar so' a ultima da rajada. E' interface, nao metodologia: o
  // numero final e' o mesmo.
  //
  // Ambiente sem temporizador (um contexto de teste sem `setTimeout`)
  // redesenha na hora: atrasar nao pode virar NAO redesenhar.
  var ESPERA_DO_REDESENHO = 120;

  function agrupador(funcao) {
    if (typeof root.setTimeout !== "function") { return funcao; }
    var pendente = null;
    return function () {
      if (pendente !== null && typeof root.clearTimeout === "function") { root.clearTimeout(pendente); }
      pendente = root.setTimeout(function () { pendente = null; funcao(); }, ESPERA_DO_REDESENHO);
    };
  }

  function ligar(raiz, dados) {
    function redesenhar() {
      var colheita = colher(raiz, dados.caso, dados);
      var vivo = null;
      try {
        vivo = root.FachadaEspelho.avaliarCaso(colheita.caso);
      } catch (erro) {
        vivo = null;
      }
      escrever(raiz, vivo, colheita.cegos, dados, colheita.caso);
    }

    var comEspera = agrupador(redesenhar);
    var campos = [];
    var doPainel = raiz.querySelectorAll("[data-laboratorio-entrada]");
    var posicao;
    // `querySelectorAll` devolve NodeList no browser, nao Array: a lista de ouvintes e'
    // montada numa lista propria, nunca por `push` no que o DOM devolveu.
    for (posicao = 0; posicao < doPainel.length; posicao++) { campos.push(doPainel[posicao]); }
    // As linhas do degrau moram fora da raiz (D8) e sao numericas: entram na mesma
    // lista de ouvintes, com o mesmo agrupamento por rajada.
    var linhas = linhasDaPonte(raiz.ownerDocument);
    for (posicao = 0; posicao < linhas.length; posicao++) {
      if (linhas[posicao].campo) { campos.push(linhas[posicao].campo); }
    }
    var indice;
    for (indice = 0; indice < campos.length; indice++) {
      var tipo = campos[indice].getAttribute("data-laboratorio-entrada");
      // So' o campo numerico agrupa: ele dispara a cada TECLA (D13). Escolha e
      // booleano disparam uma vez por mudanca, e redesenham na hora.
      campos[indice].addEventListener(tipo === "numero" ? "input" : "change",
        tipo === "numero" ? comEspera : redesenhar);
    }

    var botoes = raiz.querySelectorAll("[data-laboratorio-restaurar]");
    for (indice = 0; indice < botoes.length; indice++) {
      botoes[indice].addEventListener("click", function (evento) {
        var bloco = evento.currentTarget.closest("[data-laboratorio-cenario]") || raiz;
        var doBloco = bloco.querySelectorAll("[data-laboratorio-entrada]");
        var posicao;
        for (posicao = 0; posicao < doBloco.length; posicao++) {
          var campo = doBloco[posicao];
          var original = campo.getAttribute("data-laboratorio-original");
          if (campo.getAttribute("data-laboratorio-entrada") === "booleano") {
            campo.checked = original === "true";
          } else {
            campo.value = original;
          }
          campo.removeAttribute("aria-invalid");
        }
        redesenhar();
      });
    }

    redesenhar();
  }

  /**
   * Liga o painel. `raiz`: o elemento `[data-laboratorio]` que `render.py`
   * emitiu. `dados`: o payload embutido ({idioma, caso, resultados, formatos,
   * rotulosMultiplos, formatosPorUnidade, vocabularios, reversa,
   * sensibilidades, diagnosticos, recusas, textos}). `badge`: o elemento
   * `[data-laboratorio-badge]`, que desde a fatia 5I mora no CABECALHO da aba
   * -- fora da raiz, porque o veredicto e' sobre a pagina inteira (a manchete,
   * os eixos, as grades), nao so' sobre os cenarios do painel. Quem o localiza
   * e' o bootstrap, por `document`; uma busca descendente a partir da raiz
   * devolveria `null`, e `pintarBadge` sairia no guarda -- sem badge, sem erro
   * e com o painel destravado.
   *
   * A ordem importa: o badge de paridade e decidido ANTES de qualquer campo
   * ficar editavel. Se a fachada recusar o contrato, ou se algum numero
   * recalculado nao bater com o publicado, o painel inteiro trava e diz por
   * que -- nunca abre para edicao "mesmo assim". E, travado, a tela FICA com o
   * que o Python publicou: a reversa e as grades so' sao reescritas depois do
   * badge verde.
   */
  function iniciar(raiz, dados, badge) {
    var textos = dados.textos || {};
    var vazio = textos.semValor || SEM_VALOR_PADRAO;
    var alvo = badge || null;
    var comparacao = null;

    try {
      comparacao = root.FachadaEspelho.compararComResultados(dados.caso, dados.resultados);
    } catch (erro) {
      pintarBadge(alvo, "indisponivel", textoDe(textos.paridadeIndisponivel, {
        erro: String((erro && erro.message) || erro)
      }), []);
      travarEdicao(raiz);
      return;
    }

    if (!comparacao.ok) {
      var itens = [];
      var indice;
      for (indice = 0; indice < comparacao.divergencias.length; indice++) {
        var divergencia = comparacao.divergencias[indice];
        itens.push(textoDe(textos.paridadeItem, {
          cenario: divergencia.cenario,
          chave: divergencia.chave,
          python: valorCru(divergencia.python, vazio),
          js: valorCru(divergencia.js, vazio)
        }));
      }
      pintarBadge(alvo, "divergente", textos.paridadeDivergente, itens);
      travarEdicao(raiz);
      return;
    }

    pintarBadge(alvo, "ok", textos.paridadeOk, []);
    ligar(raiz, dados);
  }

  root.FleetLaboratorio = { iniciar: iniciar, formatar: formatar, textoDe: textoDe };
})(typeof self !== "undefined" ? self : this);
