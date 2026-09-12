/* svg.js -- os dois graficos NAO-CARTESIANOS da aba Valuation (fatia 5B,
 * item 5, Task 3), desenhados como STRING SVG por funcoes puras. Ver
 * docs/superpowers/plans/2026-09-11-v4-item5b-graficos.md, secao "Task 3"
 * (G6), e docs/desenho-arquitetura-v4.md secoes 9-10/15 (E3).
 *
 * PAPEL (E3): este arquivo NUNCA le contrato (`analise.exhibits`/
 * `entrega.dados`), NUNCA resolve `fonte`/`formula`/`chave`, NUNCA decide o
 * que e rastreavel e -- sobretudo -- NUNCA faz conta de valuation. O
 * relatorio desenha; nao calcula. As duas funcoes recebem numeros JA
 * PRONTOS de `resultados` (a ponte que o wrapper compos, a grade de
 * sensibilidade que o motor rodou), passados por `render.py`. A unica
 * aritmetica daqui e GEOMETRIA: empilhar barras, mapear valor -> pixel,
 * interpolar cor. Em particular, o total do waterfall (`opcoes.total.valor`)
 * e o `nd_efetivo` que o wrapper ja somou -- este modulo desenha a barra de
 * fechamento nesse valor, nunca o recalcula a partir das parcelas.
 *
 * PADRAO DE MODULO (igual ao de `graficos.js`): IIFE sobre `self`/`this`,
 * sem `module`/`require`/`process` -- o teste (`tests/test_relatorio_svg_js.
 * py`) carrega o FONTE com `vm.createContext`/`vm.runInContext` num contexto
 * VAZIO, e o browser o carrega como `<script>` inline. Nenhuma dependencia:
 * nem DOM, nem uPlot, nem `FleetGraficos` -- as duas funcoes so devolvem
 * string.
 *
 * PUREZA E DETERMINISMO (S5 do briefing): mesma entrada => mesma string,
 * byte a byte. Sem `Date`, sem `Math.random`, sem id gerada em tempo de
 * execucao, sem leitura de DOM. Toda coordenada sai com casas decimais
 * FIXAS (`coordenada`, abaixo) para que o float nunca imprima uma cauda
 * diferente. Todo texto que entra na string passa por `escapar` (`&`, `<`,
 * `>`, `"`) -- a string e inserida com `innerHTML` pelo bootstrap de
 * `template.html`.
 *
 * SEM PROSA (S3 do briefing): nenhuma string de interface mora aqui. Rotulo
 * de parcela, rotulo do total e rotulos dos eixos entram por ARGUMENTO --
 * quem os le e `render.py`, do dicionario (interface, secao 16.1) e do
 * catalogo de apresentacao (rotulo de linha da ponte e de premissa, A6).
 *
 * FORMATACAO: tabela PROPRIA (`SEPARADORES_POR_IDIOMA`, abaixo), pt-BR
 * (milhar '.', decimal ','), duplicada de proposito de `placeholders.
 * _SEPARADORES` (Python) -- exatamente o mesmo motivo ja registrado no
 * cabecalho de `graficos.js`: um modulo de browser nunca importa Python,
 * entao o pedaco pequeno e estavel (dois separadores) atravessa como tabela
 * propria, nao como dado injetado. Nao e uma copia de `graficos.js`: os dois
 * modulos sao embutidos INDEPENDENTEMENTE (o uPlot/adaptador so entra
 * quando a entrega declara exhibit; este so entra quando ha painel), entao
 * um nao pode depender do outro estar na pagina. `opcoes.formatar`, quando
 * dado, substitui a tabela -- e o gancho para o laboratorio da 5C.
 */
(function (root) {
  "use strict";

  var SEPARADORES_POR_IDIOMA = { "pt-BR": { milhar: ".", decimal: "," } };

  var LARGURA_PADRAO = 720;
  var ALTURA_PADRAO = 320;
  var ALTURA_DE_CELULA_PADRAO = 34;

  // Paleta alinhada com o CSS de `template.html` (--cor-acento,
  // --cor-acento-suave, --cor-texto, --cor-borda) -- literais, porque um
  // SVG montado como string nao enxerga variavel CSS do documento.
  var COR_ACENTO = "#1b3a5c";
  var COR_TEXTO = "#1f2328";
  var COR_TEXTO_SUAVE = "#57606a";
  var COR_BORDA = "#d8dbe0";
  var COR_SOBE = "#7f2b2b";
  var COR_DESCE = "#2f6b4f";
  var COR_TOTAL = "#1b3a5c";
  var COR_MARCA_BASE = "#c00000";
  var RAMPA_CLARA = [238, 242, 246];
  var RAMPA_ESCURA = [27, 58, 92];

  // --------------------------------------------------------------------
  // Utilitarios puros.
  // --------------------------------------------------------------------

  function escapar(texto) {
    return String(texto === undefined || texto === null ? "" : texto)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function numero(valor) {
    return (typeof valor === "number" && isFinite(valor)) ? valor : 0;
  }

  // Coordenada com casas FIXAS: sem isto, `0.1 + 0.2` imprimiria
  // '0.30000000000000004' numa maquina e o determinismo byte a byte
  // dependeria da ordem das somas. '-0.00' e normalizado para '0.00' --
  // mesmo cuidado que `numeroLocalizado` toma com o zero negativo.
  function coordenada(valor) {
    var texto = numero(valor).toFixed(2);
    return texto === "-0.00" ? "0.00" : texto;
  }

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

    var formatado = casas === 0 ? inteiroFormatado : inteiroFormatado + separadores.decimal + parteDecimal;
    if (negativo && parseFloat(texto) !== 0) {
      formatado = "-" + formatado;
    }
    return formatado;
  }

  // Valor nao numerico/nao finito (inclusive `null`, o jeito natural de uma
  // celula de grade marcar "sem resultado") devolve o travessao -- mesma
  // convencao de `FleetGraficos.formatar`.
  function formatarPadrao(valor) {
    if (typeof valor !== "number" || !isFinite(valor)) {
      return "—";
    }
    return numeroLocalizado(valor, 2, "pt-BR");
  }

  function formatadorDe(opcoes) {
    return typeof opcoes.formatar === "function" ? opcoes.formatar : formatarPadrao;
  }

  function texto(conteudo, x, y, classe, cor, ancora, tamanho) {
    return '<text class="' + classe + '" x="' + coordenada(x) + '" y="' + coordenada(y)
      + '" text-anchor="' + ancora + '" font-size="' + tamanho + '" fill="' + cor + '">'
      + escapar(conteudo) + '</text>';
  }

  function abrirSvg(largura, altura, classe) {
    return '<svg xmlns="http://www.w3.org/2000/svg" class="' + classe + '" role="img"'
      + ' width="' + coordenada(largura) + '" height="' + coordenada(altura) + '"'
      + ' viewBox="0 0 ' + coordenada(largura) + ' ' + coordenada(altura) + '"'
      + ' font-family="-apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif">';
  }

  // --------------------------------------------------------------------
  // waterfall(parcelas, opcoes) -> string
  //
  // `parcelas`: [{rotulo, valor, sinal}] -- a forma EXATA de
  // `resultados.ponte.parcelas`, com o rotulo JA TRADUZIDO pelo chamador
  // (S2/S3: quem le o catalogo e `render.py`).
  // `opcoes`: {largura, altura, total: {rotulo, valor}, formatar?}.
  //
  // Uma barra por parcela, empilhando `valor * sinal` (cada barra vai do
  // acumulado anterior ao proprio), MAIS uma barra de fechamento desenhada
  // de zero ao `total.valor` que o chamador passou. O empilhamento e
  // geometria; o total e dado. Quando os dois discordam a figura MOSTRA a
  // discordancia (a ultima barra nao encosta no acumulado) em vez de
  // esconde-la -- o relatorio nao conserta numero do motor.
  // --------------------------------------------------------------------

  var MARGEM_WATERFALL = { topo: 30, direita: 14, baixo: 54, esquerda: 14 };

  function waterfall(parcelas, opcoes) {
    parcelas = Array.isArray(parcelas) ? parcelas : [];
    opcoes = opcoes || {};
    var formatar = formatadorDe(opcoes);
    var largura = numero(opcoes.largura) > 0 ? opcoes.largura : LARGURA_PADRAO;
    var altura = numero(opcoes.altura) > 0 ? opcoes.altura : ALTURA_PADRAO;
    var total = opcoes.total || {};

    var passos = [];
    var acumulado = 0;
    var i;
    for (i = 0; i < parcelas.length; i++) {
      var contribuicao = numero(parcelas[i].valor) * numero(parcelas[i].sinal);
      var inicio = acumulado;
      acumulado = acumulado + contribuicao;
      passos.push({
        rotulo: parcelas[i].rotulo,
        inicio: inicio,
        fim: acumulado,
        valor: contribuicao,
        fechamento: false
      });
    }
    passos.push({
      rotulo: total.rotulo,
      inicio: 0,
      fim: numero(total.valor),
      valor: numero(total.valor),
      fechamento: true
    });

    var minimo = 0;
    var maximo = 0;
    for (i = 0; i < passos.length; i++) {
      minimo = Math.min(minimo, passos[i].inicio, passos[i].fim);
      maximo = Math.max(maximo, passos[i].inicio, passos[i].fim);
    }
    if (maximo - minimo < 1e-9) {
      maximo = minimo + 1;
    }

    var areaLargura = largura - MARGEM_WATERFALL.esquerda - MARGEM_WATERFALL.direita;
    var areaAltura = altura - MARGEM_WATERFALL.topo - MARGEM_WATERFALL.baixo;
    var faixa = areaLargura / passos.length;
    var larguraBarra = faixa * 0.62;

    function y(valor) {
      return MARGEM_WATERFALL.topo + areaAltura * (maximo - valor) / (maximo - minimo);
    }

    var pedacos = [abrirSvg(largura, altura, "fleet-svg fleet-svg-waterfall")];

    var yZero = y(0);
    pedacos.push('<line class="fleet-svg-zero" x1="' + coordenada(MARGEM_WATERFALL.esquerda)
      + '" y1="' + coordenada(yZero) + '" x2="' + coordenada(largura - MARGEM_WATERFALL.direita)
      + '" y2="' + coordenada(yZero) + '" stroke="' + COR_BORDA + '" stroke-width="1" />');

    for (i = 0; i < passos.length; i++) {
      var passo = passos[i];
      var centro = MARGEM_WATERFALL.esquerda + faixa * (i + 0.5);
      var x0 = centro - larguraBarra / 2;
      var topoBarra = Math.min(y(passo.inicio), y(passo.fim));
      var alturaBarra = Math.max(Math.abs(y(passo.fim) - y(passo.inicio)), 1);
      var cor = passo.fechamento ? COR_TOTAL : (passo.valor < 0 ? COR_DESCE : COR_SOBE);
      var classe = "fleet-svg-barra" + (passo.fechamento ? " fleet-svg-barra-fechamento" : "");

      pedacos.push('<rect class="' + classe + '" data-indice="' + i + '"'
        + (passo.fechamento ? ' data-fechamento="1"' : '')
        + ' data-valor="' + escapar(String(passo.valor)) + '"'
        + ' x="' + coordenada(x0) + '" y="' + coordenada(topoBarra) + '"'
        + ' width="' + coordenada(larguraBarra) + '" height="' + coordenada(alturaBarra) + '"'
        + ' fill="' + cor + '" />');

      pedacos.push(texto(formatar(passo.valor), centro, topoBarra - 7,
        "fleet-svg-valor", COR_TEXTO, "middle", 11));
      pedacos.push(texto(passo.rotulo, centro, altura - MARGEM_WATERFALL.baixo + 20,
        "fleet-svg-rotulo", COR_TEXTO_SUAVE, "middle", 11));
    }

    pedacos.push("</svg>");
    return pedacos.join("");
  }

  // --------------------------------------------------------------------
  // matriz(grade, opcoes) -> string
  //
  // `grade`: {pontos_x, pontos_y, celulas} -- a forma EXATA de uma grade 2D
  // de `resultados.sensibilidades.grades_2d`, com `celulas[i][j]` na
  // interseccao de `pontos_y[i]` (linha) com `pontos_x[j]` (coluna). So
  // `celula.valor` e lido; o resto da celula (multiplo, diag) e ignorado
  // aqui.
  // `opcoes`: {base: {x, y} | null, rotuloX, rotuloY, largura, altura,
  // formatar?}.
  //
  // A celula-base e marcada por IGUALDADE EXATA contra `opcoes.base` (S4):
  // quem decide qual e o par (x, y) central e `render.py`, lendo as
  // premissas do cenario QUE A GRADE PERTURBOU. Os dois numeros saem do
  // mesmo `caso.json`, entao '===' e o teste certo -- nada de tolerancia,
  // nada de "a do meio". `base` nulo, ou nenhum par casando, marca ZERO
  // celulas. A marca e visual (contorno) E identificavel (`data-base="1"`),
  // para quem verifica nao depender de cor.
  // --------------------------------------------------------------------

  var MARGEM_MATRIZ = { topo: 30, direita: 14, baixo: 40, esquerda: 34 };
  var LARGURA_DA_COLUNA_DE_LINHAS = 92;

  function componenteHex(valor) {
    var texto = Math.round(valor).toString(16);
    return texto.length < 2 ? "0" + texto : texto;
  }

  function corDaCelula(fracao) {
    var canais = "#";
    for (var k = 0; k < 3; k++) {
      canais += componenteHex(RAMPA_CLARA[k] + (RAMPA_ESCURA[k] - RAMPA_CLARA[k]) * fracao);
    }
    return canais;
  }

  function matriz(grade, opcoes) {
    grade = grade || {};
    opcoes = opcoes || {};
    var formatar = formatadorDe(opcoes);
    var pontosX = Array.isArray(grade.pontos_x) ? grade.pontos_x : [];
    var pontosY = Array.isArray(grade.pontos_y) ? grade.pontos_y : [];
    var linhas = Array.isArray(grade.celulas) ? grade.celulas : [];
    var base = opcoes.base || null;

    var largura = numero(opcoes.largura) > 0 ? opcoes.largura : LARGURA_PADRAO;
    var alturaPadrao = MARGEM_MATRIZ.topo + ALTURA_DE_CELULA_PADRAO * (pontosY.length + 1)
      + MARGEM_MATRIZ.baixo;
    var altura = numero(opcoes.altura) > 0 ? opcoes.altura : alturaPadrao;

    var areaLargura = largura - MARGEM_MATRIZ.esquerda - MARGEM_MATRIZ.direita
      - LARGURA_DA_COLUNA_DE_LINHAS;
    var larguraCelula = pontosX.length > 0 ? areaLargura / pontosX.length : areaLargura;
    var areaAltura = altura - MARGEM_MATRIZ.topo - MARGEM_MATRIZ.baixo;
    var alturaCelula = areaAltura / (pontosY.length + 1);
    var x0Grade = MARGEM_MATRIZ.esquerda + LARGURA_DA_COLUNA_DE_LINHAS;
    var y0Grade = MARGEM_MATRIZ.topo + alturaCelula;

    var i;
    var j;
    var minimo = null;
    var maximo = null;
    for (i = 0; i < linhas.length; i++) {
      var linha = Array.isArray(linhas[i]) ? linhas[i] : [];
      for (j = 0; j < linha.length; j++) {
        var bruto = (linha[j] || {}).valor;
        if (typeof bruto === "number" && isFinite(bruto)) {
          minimo = (minimo === null || bruto < minimo) ? bruto : minimo;
          maximo = (maximo === null || bruto > maximo) ? bruto : maximo;
        }
      }
    }

    function fracaoDe(valor) {
      if (typeof valor !== "number" || !isFinite(valor) || minimo === null) { return 0; }
      if (maximo - minimo < 1e-12) { return 0.5; }
      return (valor - minimo) / (maximo - minimo);
    }

    var pedacos = [abrirSvg(largura, altura, "fleet-svg fleet-svg-matriz")];

    // Cabecalho de colunas (pontos do eixo x) e rotulo do eixo x.
    for (j = 0; j < pontosX.length; j++) {
      pedacos.push(texto(formatar(pontosX[j]), x0Grade + larguraCelula * (j + 0.5),
        MARGEM_MATRIZ.topo + alturaCelula * 0.65, "fleet-svg-eixo-x", COR_TEXTO, "middle", 11));
    }
    pedacos.push(texto(opcoes.rotuloX, x0Grade + (larguraCelula * pontosX.length) / 2,
      MARGEM_MATRIZ.topo - 12, "fleet-svg-rotulo-x", COR_ACENTO, "middle", 12));

    // Rotulo do eixo y, girado na lateral esquerda.
    var meioVertical = y0Grade + (alturaCelula * pontosY.length) / 2;
    pedacos.push('<g transform="rotate(-90 ' + coordenada(MARGEM_MATRIZ.esquerda - 18) + ' '
      + coordenada(meioVertical) + ')">'
      + texto(opcoes.rotuloY, MARGEM_MATRIZ.esquerda - 18, meioVertical,
        "fleet-svg-rotulo-y", COR_ACENTO, "middle", 12)
      + '</g>');

    for (i = 0; i < pontosY.length; i++) {
      var yLinha = y0Grade + alturaCelula * i;
      pedacos.push(texto(formatar(pontosY[i]), x0Grade - 8, yLinha + alturaCelula * 0.62,
        "fleet-svg-eixo-y", COR_TEXTO, "end", 11));

      var celulasDaLinha = Array.isArray(linhas[i]) ? linhas[i] : [];
      for (j = 0; j < pontosX.length; j++) {
        var celula = celulasDaLinha[j] || {};
        var valor = celula.valor;
        var fracao = fracaoDe(valor);
        var ehBase = base !== null && pontosX[j] === base.x && pontosY[i] === base.y;
        var xCelula = x0Grade + larguraCelula * j;
        var classeCelula = "fleet-svg-celula" + (ehBase ? " fleet-svg-celula-base" : "");

        pedacos.push('<rect class="' + classeCelula + '" data-linha="' + i + '" data-coluna="' + j + '"'
          + (ehBase ? ' data-base="1"' : '')
          + ' x="' + coordenada(xCelula) + '" y="' + coordenada(yLinha) + '"'
          + ' width="' + coordenada(larguraCelula) + '" height="' + coordenada(alturaCelula) + '"'
          + ' fill="' + corDaCelula(fracao) + '"'
          + ' stroke="' + (ehBase ? COR_MARCA_BASE : COR_BORDA) + '"'
          + ' stroke-width="' + (ehBase ? "2.5" : "1") + '" />');

        pedacos.push(texto(formatar(valor), xCelula + larguraCelula / 2,
          yLinha + alturaCelula * 0.62, "fleet-svg-celula-valor",
          fracao > 0.6 ? "#ffffff" : COR_TEXTO, "middle", 11));
      }
    }

    pedacos.push("</svg>");
    return pedacos.join("");
  }

  root.FleetSVG = { waterfall: waterfall, matriz: matriz, formatar: formatarPadrao };
})(typeof self !== "undefined" ? self : this);
