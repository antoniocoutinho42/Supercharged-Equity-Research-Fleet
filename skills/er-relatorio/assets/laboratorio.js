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

  // Os dois numeros da divergencia saem CRUS, de proposito. Aplicar a receita
  // de apresentacao arredondaria justamente a diferenca que o badge existe
  // para denunciar (6,69 e 6,69 imprimem igual), e o campo divergente pode
  // ser preco, multiplo ou razao -- tres unidades distintas, que este arquivo
  // nao tem como distinguir sem passar a conhecer o vocabulario da fachada.
  function numeroCru(valor, vazio) {
    return (typeof valor === "number" && isFinite(valor)) ? String(valor) : vazio;
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
  function colher(raiz, base) {
    var editado = copiaProfunda(base);
    var cegos = {};
    var blocos = raiz.querySelectorAll("[data-laboratorio-cenario]");
    var indice;
    for (indice = 0; indice < blocos.length; indice++) {
      var nomeCenario = blocos[indice].getAttribute("data-laboratorio-cenario");
      var registro = editado.cenarios ? editado.cenarios[nomeCenario] : null;
      var destino = registro ? registro.premissas : null;
      var campos = blocos[indice].querySelectorAll("[data-laboratorio-entrada]");
      var posicao;
      for (posicao = 0; posicao < campos.length; posicao++) {
        var campo = campos[posicao];
        var nome = nomeDaPremissa(campo);
        var tipo = campo.getAttribute("data-laboratorio-entrada");
        if (tipo === "booleano") {
          if (destino && nome) { destino[nome] = campo.checked; }
          continue;
        }
        if (tipo === "escolha") {
          if (destino && nome) { destino[nome] = campo.value; }
          continue;
        }
        var lido = Number(campo.value);
        if (String(campo.value).trim() === "" || !isFinite(lido)) {
          campo.setAttribute("aria-invalid", "true");
          cegos[nomeCenario] = true;
          continue;
        }
        campo.removeAttribute("aria-invalid");
        if (destino && nome) { destino[nome] = lido; }
      }
    }
    return { caso: editado, cegos: cegos };
  }

  function escreverSaida(bloco, papel, texto) {
    var alvo = bloco.querySelector('[data-laboratorio-saida="' + papel + '"]');
    if (alvo) { alvo.textContent = texto; }
  }

  function escrever(raiz, vivo, cegos, dados) {
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
        continue;
      }
      escreverSaida(bloco, "preco",
        formatar(registro.valor.preco_acao, formatos.preco, idioma, vazio));
      escreverSaida(bloco, "multiplo",
        formatar(registro.multiplo.valor, formatos.multiplo, idioma, vazio));
      escreverSaida(bloco, "multiplo-rotulo", rotulos[registro.multiplo.chave] || "");
      escreverSaida(bloco, "upside",
        formatar(registro.vs_preco.upside, formatos.upside, idioma, vazio));
    }
  }

  // ----------------------------------------------------------------------
  // Ciclo: colher -> pedir a fachada -> escrever. Uma unica chamada por
  // mudanca: a fachada avalia o caso inteiro, todos os cenarios de uma vez.
  // ----------------------------------------------------------------------

  function ligar(raiz, dados) {
    function redesenhar() {
      var colheita = colher(raiz, dados.caso);
      var vivo = null;
      try {
        vivo = root.FachadaEspelho.avaliarCaso(colheita.caso);
      } catch (erro) {
        vivo = null;
      }
      escrever(raiz, vivo, colheita.cegos, dados);
    }

    var campos = raiz.querySelectorAll("[data-laboratorio-entrada]");
    var indice;
    for (indice = 0; indice < campos.length; indice++) {
      var tipo = campos[indice].getAttribute("data-laboratorio-entrada");
      campos[indice].addEventListener(tipo === "numero" ? "input" : "change", redesenhar);
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
   * rotulosMultiplos, textos}).
   *
   * A ordem importa: o badge de paridade e decidido ANTES de qualquer campo
   * ficar editavel. Se a fachada recusar o contrato, ou se algum numero
   * recalculado nao bater com o publicado, o painel inteiro trava e diz por
   * que -- nunca abre para edicao "mesmo assim".
   */
  function iniciar(raiz, dados) {
    var textos = dados.textos || {};
    var vazio = textos.semValor || SEM_VALOR_PADRAO;
    var alvo = raiz.querySelector("[data-laboratorio-badge]");
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
          python: numeroCru(divergencia.python, vazio),
          js: numeroCru(divergencia.js, vazio)
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
