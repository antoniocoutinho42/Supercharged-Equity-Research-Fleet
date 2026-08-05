/* charts.js — adaptador fino do fleet v3 sobre uPlot (vendorizado, MIT).
 *
 * Papel: renderizar os gráficos da aba 2 (Análise) a partir das specs em
 * REPORT_DATA.analise.charts, SEM nenhuma matemática de valuation — toda
 * série e todo overlay chegam prontos do builder (build_report.py), que é
 * quem responde pela consistência com dados/ e results.json (checar_relatorio.py).
 *
 * Spec de um gráfico (contrato com build_report.py):
 * {
 *   id: "roe",                       // único na página
 *   titulo: "ROE — janela disponível",
 *   tipo: "line" | "bars",
 *   unidade: "%" | "x" | "BRL" | ...,      // formatação do eixo y e tooltip
 *   x: [2016, 2017, ...],                  // eixo x comum (anos ou epoch s)
 *   x_tempo: false,                        // true -> x em epoch segundos
 *   series: [{label, y: [..], cor?}],      // null em y = ponto ausente
 *   overlays: [{label, valor, cor?}],      // linhas horizontais (premissas)
 *   nota_janela: "Janela efetiva 2021–2025 (OpenBB yfinance); ...",
 *   caption: "texto curto sob o gráfico"   // opcional
 * }
 */
(function (root) {
  "use strict";

  var PALETA = ["#002060", "#C00000", "#7F7F7F", "#FFC000", "#4472C4", "#548235"];
  var PALETA_OVERLAY = ["#C00000", "#548235", "#7030A0", "#BF8F00"];

  function fmtVal(v, unidade) {
    if (v === null || v === undefined || !isFinite(v)) return "—";
    if (unidade === "%") return (100 * v).toFixed(1) + "%";
    if (unidade === "x") return v.toFixed(2) + "x";
    return v.toLocaleString("en-US", { maximumFractionDigits: 2 });
  }

  function renderChart(hostEl, spec) {
    var card = document.createElement("div");
    card.className = "chart-card";
    card.id = "chart-" + spec.id;

    var h = document.createElement("h4");
    h.textContent = spec.titulo;
    card.appendChild(h);

    if (spec.nota_janela) {
      var nota = document.createElement("div");
      nota.className = "chart-window-note";
      nota.textContent = spec.nota_janela;
      card.appendChild(nota);
    }

    var plotHost = document.createElement("div");
    card.appendChild(plotHost);

    var haveData = spec.series && spec.series.length &&
      spec.series.some(function (s) { return (s.y || []).some(function (v) { return v !== null && isFinite(v); }); });

    if (!haveData) {
      var deg = document.createElement("div");
      deg.className = "chart-degraded";
      deg.textContent = "Gráfico não renderizado — série indisponível. " + (spec.nota_janela || "Ver Limitações de dados.");
      card.appendChild(deg);
      hostEl.appendChild(card);
      return null;
    }

    var data = [spec.x];
    var seriesCfg = [{}];

    spec.series.forEach(function (s, i) {
      data.push(s.y);
      var cfg = {
        label: s.label,
        stroke: s.cor || PALETA[i % PALETA.length],
        width: 2,
        points: { show: spec.x.length <= 30, size: 5 },
        value: function (u, v) { return fmtVal(v, spec.unidade); },
      };
      if (spec.tipo === "bars" && uPlot.paths && typeof uPlot.paths.bars === "function") {
        cfg.paths = uPlot.paths.bars({ size: [0.6, 100] });
        cfg.fill = (s.cor || PALETA[i % PALETA.length]) + "55";
        cfg.points = { show: false };
      }
      seriesCfg.push(cfg);
    });

    (spec.overlays || []).forEach(function (o, i) {
      data.push(spec.x.map(function () { return o.valor; }));
      seriesCfg.push({
        label: o.label,
        stroke: o.cor || PALETA_OVERLAY[i % PALETA_OVERLAY.length],
        width: 1.5,
        dash: [8, 5],
        points: { show: false },
        value: function (u, v) { return fmtVal(v, spec.unidade); },
      });
    });

    var w = Math.min(920, Math.max(420, plotHost.clientWidth || card.clientWidth || 860));
    var opts = {
      width: w,
      height: 300,
      title: "",
      scales: { x: { time: !!spec.x_tempo } },
      legend: { live: true },
      cursor: { drag: { x: true, y: false } },
      series: seriesCfg,
      axes: [
        {
          values: spec.x_tempo ? undefined : function (u, ticks) {
            return ticks.map(function (t) { return String(Math.round(t)); });
          },
        },
        {
          size: 70,
          values: function (u, ticks) { return ticks.map(function (t) { return fmtVal(t, spec.unidade); }); },
        },
      ],
    };

    var plot = new uPlot(opts, data, plotHost);

    if (spec.caption) {
      var cap = document.createElement("div");
      cap.className = "chart-caption";
      cap.textContent = spec.caption;
      card.appendChild(cap);
    }
    hostEl.appendChild(card);
    return plot;
  }

  function renderAllCharts(hostId, specs) {
    var host = document.getElementById(hostId);
    if (!host) return;
    (specs || []).forEach(function (spec) {
      try {
        renderChart(host, spec);
      } catch (e) {
        var err = document.createElement("div");
        err.className = "chart-degraded";
        err.textContent = "Falha ao renderizar o gráfico \"" + spec.titulo + "\": " + e.message;
        host.appendChild(err);
      }
    });
  }

  root.FleetCharts = { renderChart: renderChart, renderAllCharts: renderAllCharts, fmtVal: fmtVal };
})(typeof self !== "undefined" ? self : this);
