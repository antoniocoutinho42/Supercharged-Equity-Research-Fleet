/* graficos.js -- adaptador fino sobre o uPlot vendorizado (fatia 5B, item 5,
 * Task 2). Ver docs/superpowers/plans/2026-09-11-v4-item5b-graficos.md,
 * secao "Task 2", e docs/desenho-arquitetura-v4.md secoes 9-10/15 (E3).
 *
 * PAPEL (E3): este arquivo NUNCA le `analise.exhibits`/`entrega.dados`, nunca
 * resolve `fonte`/`formula`/`chave`, nunca decide o que e rastreavel -- tudo
 * isso e trabalho de `skills/er-relatorio/scripts/exhibits.py`
 * (`exhibits.resolver`), que roda em Python ANTES deste script existir no
 * navegador. O que chega aqui (via `renderizar`) e uma spec JA RESOLVIDA:
 * numeros e rotulos prontos, nenhuma fonte/formula/caminho de contrato. O
 * relatorio desenha; nao calcula (E3, desenho-arquitetura-v4.md secao 15).
 *
 * Spec resolvida (contrato deste modulo com render.py -- ver
 * `_exhibit_para_json` la): {
 *   id: "margem",                          // so para depuracao -- nunca lido de volta
 *   tipo: "linha"|"barras"|"area"|"empilhado"|"dispersao"|"tabela",
 *   eixoX: [...] | null,                   // rotulos do eixo x (numero OU texto); null == sem dataset (so series 'engine')
 *   series: [{rotulo: "...", valores: [numero|null, ...]}],
 *   overlays: [{rotulo: "...", valor: numero}],
 * }
 *
 * Formatacao pt-BR (milhar '.', decimal ',') e SEMPRE por `formatar` deste
 * modulo -- nunca `toLocaleString("en-US")` (o que o adaptador de graficos
 * da v3 fazia, removido no item 10). `dicionarioFmt`
 * (parametro de `renderizar`) carrega so PROSA de interface ja traduzida
 * (hoje, a mensagem de "grafico indisponivel") -- os separadores numericos
 * NAO vem dele: `formatar(valor, unidade, idioma)` tem sua PROPRIA tabela
 * (`SEPARADORES_POR_IDIOMA`, abaixo), duplicada de proposito de
 * `placeholders._SEPARADORES` (Python) -- mesmo espirito da duplicacao
 * deliberada de utilitarios entre `exhibits.py`/`entrega.py`: o adaptador do
 * browser nunca importa Python, entao o pequeno pedaco estavel (dois
 * separadores) atravessa como TABELA PROPRIA, nao como dado injetado.
 */
(function (root) {
  "use strict";

  // G2 (exhibits.py) -- os cinco tipos cartesianos que este adaptador
  // desenha com uPlot. 'tabela' e tratado a parte (sem uPlot); 'waterfall'/
  // 'matriz' sao do modulo svg.js (Task 3, nao deste arquivo).
  var TIPOS_CARTESIANOS = ["linha", "barras", "area", "empilhado", "dispersao"];

  var PALETA = ["#002060", "#C00000", "#7F7F7F", "#FFC000", "#4472C4", "#548235"];
  var PALETA_OVERLAY = ["#C00000", "#548235", "#7030A0", "#BF8F00"];

  // --------------------------------------------------------------------
  // Formatacao numerica pt-BR -- porte deliberado, termo a termo, de
  // `placeholders._num_localizado` (Python): mesma logica de agrupamento
  // de milhar e o mesmo cuidado de nao mostrar '-0,00' para um valor
  // negativo que arredonda a zero.
  // --------------------------------------------------------------------

  var SEPARADORES_POR_IDIOMA = { "pt-BR": { milhar: ".", decimal: "," } };

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

  // `unidade`: G1-G8 (a gramatica de exhibits) NAO declara unidade nenhuma
  // por serie/exhibit -- so "inteiro" (0 casas) e o padrao "numero" (2
  // casas) existem nesta fatia. Valor nao numerico/nao finito (inclusive
  // `null`, o jeito natural de um dataset marcar ponto ausente) devolve o
  // travessao -- mesma convencao do adaptador legado (charts.js).
  function formatar(valor, unidade, idioma) {
    if (typeof valor !== "number" || !isFinite(valor)) {
      return "—";
    }
    var casas = unidade === "inteiro" ? 0 : 2;
    return numeroLocalizado(valor, casas, idioma || "pt-BR");
  }

  function rotuloEixo(valorBruto, idioma) {
    if (valorBruto === undefined) { return ""; }
    return typeof valorBruto === "number" ? formatar(valorBruto, "numero", idioma) : String(valorBruto);
  }

  function maiorTamanho(spec) {
    var tamanho = Array.isArray(spec.eixoX) ? spec.eixoX.length : 0;
    (spec.series || []).forEach(function (serie) {
      tamanho = Math.max(tamanho, (serie.valores || []).length);
    });
    return tamanho;
  }

  // --------------------------------------------------------------------
  // uPlot sempre plota um eixo x NUMERICO -- um dataset com rotulos texto
  // ('2023', '2024', ...; ver `tests/test_relatorio_exhibits.py`) nao pode
  // ir direto. A solucao padrao (documentada nos exemplos do proprio uPlot
  // para eixo categorico): plotar indice posicional [0..N-1] e reescrever
  // os ticks visiveis com o rotulo ORIGINAL via `axes[0].values`. Cobre os
  // tres casos (x numerico, x texto, x ausente -- so series 'engine') com
  // o mesmo caminho, sem ramificacao por tipo.
  // --------------------------------------------------------------------

  function montarSeriesCartesianas(spec, indices, idioma) {
    var data = [indices];
    var seriesCfg = [{}];

    if (spec.tipo === "empilhado") {
      // Soma cumulativa (a "pilha"); desenhada em ordem REVERSA (maior
      // acumulado primeiro/ao fundo, menor por ultimo/na frente) -- cada
      // serie e um preenchimento OPACO de 0 ate seu proprio acumulado, e
      // desenhar da maior para a menor deixa visivel, de cada uma, so a
      // faixa [acumulado anterior, acumulado proprio] -- o efeito visual
      // de pilha, sem depender de uma API de "bandas" do uPlot. O tooltip
      // usa o valor ORIGINAL (nao cumulativo, capturado no fechamento),
      // nunca o acumulado.
      var acumulado = [];
      (spec.series || []).forEach(function (serie, i) {
        var anterior = i === 0 ? null : acumulado[i - 1];
        acumulado.push((serie.valores || []).map(function (v, k) {
          var base = anterior ? anterior[k] : 0;
          var atual = (typeof v === "number" && isFinite(v)) ? v : 0;
          return base + atual;
        }));
      });
      for (var i = spec.series.length - 1; i >= 0; i--) {
        (function (indice) {
          var original = spec.series[indice].valores || [];
          data.push(acumulado[indice]);
          seriesCfg.push({
            label: spec.series[indice].rotulo,
            stroke: PALETA[indice % PALETA.length],
            fill: PALETA[indice % PALETA.length] + "55",
            width: 1.5,
            points: { show: false },
            value: function (u, _v, _si, di) { return formatar(original[di], "numero", idioma); },
          });
        })(i);
      }
      return { data: data, seriesCfg: seriesCfg };
    }

    (spec.series || []).forEach(function (serie, i) {
      var valores = serie.valores || [];
      data.push(valores);
      var cfg = {
        label: serie.rotulo,
        stroke: PALETA[i % PALETA.length],
        width: 2,
        points: { show: indices.length <= 30, size: 5 },
        value: function (u, v) { return formatar(v, "numero", idioma); },
      };
      if (spec.tipo === "barras") {
        if (root.uPlot && root.uPlot.paths && typeof root.uPlot.paths.bars === "function") {
          cfg.paths = root.uPlot.paths.bars({ size: [0.6, 100] });
        }
        cfg.fill = PALETA[i % PALETA.length] + "55";
        cfg.points = { show: false };
      } else if (spec.tipo === "area") {
        cfg.fill = PALETA[i % PALETA.length] + "33";
      } else if (spec.tipo === "dispersao") {
        cfg.paths = function () { return null; };
        cfg.width = 0;
        cfg.points = { show: true, size: 6 };
      }
      seriesCfg.push(cfg);
    });
    return { data: data, seriesCfg: seriesCfg };
  }

  function criarGraficoCartesiano(hostEl, spec, idioma) {
    var tamanho = maiorTamanho(spec);
    var indices = [];
    for (var i = 0; i < tamanho; i++) { indices.push(i); }

    var montado = montarSeriesCartesianas(spec, indices, idioma);
    var data = montado.data;
    var seriesCfg = montado.seriesCfg;

    (spec.overlays || []).forEach(function (overlay, i) {
      data.push(indices.map(function () { return overlay.valor; }));
      seriesCfg.push({
        label: overlay.rotulo,
        stroke: PALETA_OVERLAY[i % PALETA_OVERLAY.length],
        width: 1.5,
        dash: [8, 5],
        points: { show: false },
        value: function (u, v) { return formatar(v, "numero", idioma); },
      });
    });

    var eixoX = Array.isArray(spec.eixoX) ? spec.eixoX : null;
    var largura = Math.min(920, Math.max(320, hostEl.clientWidth || 860));
    var opts = {
      width: largura,
      height: 300,
      scales: { x: { time: false } },
      legend: { live: true },
      cursor: { drag: { x: true, y: false } },
      series: seriesCfg,
      axes: [
        {
          values: function (u, ticks) {
            return ticks.map(function (t) {
              var indice = Math.round(t);
              return eixoX ? rotuloEixo(eixoX[indice], idioma) : String(indice);
            });
          },
        },
        {
          size: 70,
          values: function (u, ticks) { return ticks.map(function (t) { return formatar(t, "numero", idioma); }); },
        },
      ],
    };

    return new root.uPlot(opts, data, hostEl);
  }

  // --------------------------------------------------------------------
  // `tabela`: "cada serie e uma coluna, o x do dataset e a primeira" (plano
  // da 5B, Task 2). Construida com `createElement`/`textContent` -- nunca
  // `innerHTML` -- entao nenhum texto (rotulo de serie, rotulo de eixo)
  // precisa de escape manual: `textContent` nunca interpreta marcacao.
  // --------------------------------------------------------------------

  function criarTabela(hostEl, spec, idioma) {
    var eixoX = Array.isArray(spec.eixoX) ? spec.eixoX : null;
    var tabela = document.createElement("table");
    tabela.className = "exhibit-tabela";

    var thead = document.createElement("thead");
    var linhaCabecalho = document.createElement("tr");
    if (eixoX) { linhaCabecalho.appendChild(document.createElement("th")); }
    (spec.series || []).forEach(function (serie) {
      var th = document.createElement("th");
      th.textContent = serie.rotulo;
      linhaCabecalho.appendChild(th);
    });
    thead.appendChild(linhaCabecalho);
    tabela.appendChild(thead);

    var tbody = document.createElement("tbody");
    var linhas = maiorTamanho(spec);
    for (var i = 0; i < linhas; i++) {
      var tr = document.createElement("tr");
      if (eixoX) {
        var thLinha = document.createElement("th");
        thLinha.textContent = rotuloEixo(eixoX[i], idioma);
        tr.appendChild(thLinha);
      }
      (spec.series || []).forEach(function (serie) {
        var td = document.createElement("td");
        var valor = (serie.valores || [])[i];
        td.textContent = typeof valor === "number" ? formatar(valor, "numero", idioma) : formatar(null, "numero", idioma);
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    }
    tabela.appendChild(tbody);
    hostEl.appendChild(tabela);
  }

  // --------------------------------------------------------------------
  // Ponto de entrada unico (contrato com render.py/template.html): recebe
  // UM host (elemento DOM vazio) e a spec JA RESOLVIDA de UM exhibit.
  // `tipo` fora do enum cartesiano+tabela (nunca deveria acontecer -- o
  // builder ja recusou contrato antes de gerar este HTML) e QUALQUER
  // excecao de renderizacao caem no mesmo fallback textual, para que um
  // exhibit quebrado nunca derrube os outros na mesma pagina.
  // --------------------------------------------------------------------

  function renderizar(hostEl, specResolvida, dicionarioFmt) {
    dicionarioFmt = dicionarioFmt || {};
    var idioma = "pt-BR";
    try {
      while (hostEl.firstChild) { hostEl.removeChild(hostEl.firstChild); }
      if (specResolvida.tipo === "tabela") {
        criarTabela(hostEl, specResolvida, idioma);
        return null;
      }
      if (TIPOS_CARTESIANOS.indexOf(specResolvida.tipo) === -1) {
        throw new Error("tipo de exhibit nao suportado pelo adaptador cartesiano: " + specResolvida.tipo);
      }
      return criarGraficoCartesiano(hostEl, specResolvida, idioma);
    } catch (erro) {
      while (hostEl.firstChild) { hostEl.removeChild(hostEl.firstChild); }
      var aviso = document.createElement("p");
      aviso.className = "exhibit-indisponivel";
      aviso.textContent = dicionarioFmt.graficoIndisponivel || String(erro);
      hostEl.appendChild(aviso);
      return null;
    }
  }

  root.FleetGraficos = { renderizar: renderizar, formatar: formatar, TIPOS_CARTESIANOS: TIPOS_CARTESIANOS };
})(typeof self !== "undefined" ? self : this);
