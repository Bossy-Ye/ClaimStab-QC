(function () {
  var state = {
    payload: null,
    comparativeRows: [],
    experiments: [],
  };

  function setText(id, value) {
    var el = document.getElementById(id);
    if (!el) return;
    el.textContent = value;
  }

  function toArray(value) {
    return Array.isArray(value) ? value : [];
  }

  function asNumber(value, fallback) {
    var n = Number(value);
    return Number.isFinite(n) ? n : fallback;
  }

  function formatPct(value) {
    return (value * 100).toFixed(1) + "%";
  }

  function clearElement(el) {
    while (el.firstChild) el.removeChild(el.firstChild);
  }

  function countBy(rows, keyFn) {
    var out = {};
    rows.forEach(function (row) {
      var key = String(keyFn(row) || "unknown");
      out[key] = (out[key] || 0) + 1;
    });
    return out;
  }

  function renderBars(containerId, counts, order) {
    var container = document.getElementById(containerId);
    if (!container) return;
    clearElement(container);

    var keys = order && order.length
      ? order.filter(function (k) { return Object.prototype.hasOwnProperty.call(counts, k); })
      : Object.keys(counts).sort(function (a, b) { return counts[b] - counts[a]; });

    if (!keys.length) {
      container.textContent = "No data.";
      return;
    }

    var total = keys.reduce(function (acc, key) { return acc + asNumber(counts[key], 0); }, 0);
    if (total <= 0) {
      container.textContent = "No data.";
      return;
    }

    keys.forEach(function (key, idx) {
      var count = asNumber(counts[key], 0);
      var rate = count / total;
      var row = document.createElement("div");
      row.className = "csx-bar-row";
      row.style.setProperty("--csx-stagger", String(idx));

      var head = document.createElement("div");
      head.className = "csx-bar-head";
      head.textContent = key + " (" + count + ", " + formatPct(rate) + ")";

      var track = document.createElement("div");
      track.className = "csx-bar-track";
      var fill = document.createElement("div");
      fill.className = "csx-bar-fill csx-key-" + String(key).toLowerCase().replace(/[^a-z0-9_]+/g, "-");
      fill.style.width = Math.max(1, Math.round(rate * 100)) + "%";
      track.appendChild(fill);

      row.appendChild(head);
      row.appendChild(track);
      container.appendChild(row);
    });
  }

  function dominantKey(counts) {
    var keys = Object.keys(counts);
    if (!keys.length) return "-";
    keys.sort(function (a, b) { return asNumber(counts[b], 0) - asNumber(counts[a], 0); });
    return keys[0];
  }

  function maxFlipRow(rows) {
    if (!rows.length) return null;
    return rows.slice().sort(function (a, b) {
      return asNumber((b || {}).flip_rate_mean, -1) - asNumber((a || {}).flip_rate_mean, -1);
    })[0];
  }

  function filterRows(rows) {
    var claimTypeSel = document.getElementById("csx-filter-claim-type");
    var spaceSel = document.getElementById("csx-filter-space");
    var claimType = claimTypeSel ? claimTypeSel.value : "all";
    var space = spaceSel ? spaceSel.value : "all";

    return rows.filter(function (row) {
      var okType = claimType === "all" || String(row.claim_type || "unknown") === claimType;
      var okSpace = space === "all" || String(row.space_preset || "unknown") === space;
      return okType && okSpace;
    });
  }

  function renderTopFlipTable(rows) {
    var body = document.getElementById("csx-topflip-body");
    if (!body) return;
    clearElement(body);
    if (!rows.length) {
      var trEmpty = document.createElement("tr");
      var tdEmpty = document.createElement("td");
      tdEmpty.colSpan = 6;
      tdEmpty.textContent = "No rows for current filters.";
      trEmpty.appendChild(tdEmpty);
      body.appendChild(trEmpty);
      return;
    }

    rows
      .slice()
      .sort(function (a, b) {
        return asNumber((b || {}).flip_rate_mean, -1) - asNumber((a || {}).flip_rate_mean, -1);
      })
      .slice(0, 12)
      .forEach(function (row) {
        var tr = document.createElement("tr");
        [
          String(row.space_preset || "-"),
          String(row.claim_pair || "-"),
          String(row.claim_type || "-"),
          row.delta == null ? "-" : String(row.delta),
          String(row.decision || "-"),
          asNumber(row.flip_rate_mean, 0).toFixed(4),
        ].forEach(function (v) {
          var td = document.createElement("td");
          td.textContent = v;
          tr.appendChild(td);
        });
        body.appendChild(tr);
      });
  }

  function populateFilter(selectId, values) {
    var el = document.getElementById(selectId);
    if (!el) return;
    var current = el.value;
    clearElement(el);

    var optAll = document.createElement("option");
    optAll.value = "all";
    optAll.textContent = "all";
    el.appendChild(optAll);

    values.sort().forEach(function (v) {
      var opt = document.createElement("option");
      opt.value = v;
      opt.textContent = v;
      el.appendChild(opt);
    });

    el.value = values.indexOf(current) >= 0 ? current : "all";
  }

  function aggregateExperiments(experiments) {
    var claimTypeCounts = {};
    var adaptiveTotal = 0;
    var adaptiveWithBlock = 0;
    var adaptiveStops = {};

    experiments.forEach(function (exp) {
      var claimType = String((((exp || {}).claim || {}).type) || "unknown");
      claimTypeCounts[claimType] = (claimTypeCounts[claimType] || 0) + 1;

      var sampling = (exp || {}).sampling || {};
      if (sampling.mode === "adaptive_ci") {
        adaptiveTotal += 1;
        var adaptive = sampling.adaptive_stopping;
        if (adaptive && typeof adaptive === "object") {
          adaptiveWithBlock += 1;
          var stopReason = String(adaptive.stop_reason || "unknown");
          adaptiveStops[stopReason] = (adaptiveStops[stopReason] || 0) + 1;
        }
      }
    });

    return {
      claimTypeCounts: claimTypeCounts,
      adaptiveTotal: adaptiveTotal,
      adaptiveWithBlock: adaptiveWithBlock,
      adaptiveStops: adaptiveStops,
    };
  }

  function renderCards(filteredRows, decisionCounts, adaptiveTotal, adaptiveWithBlock) {
    var dominantDecision = dominantKey(decisionCounts);
    var spaceCounts = countBy(filteredRows, function (row) { return row.space_preset || "unknown"; });
    var riskSpace = dominantKey(spaceCounts);
    var topFlip = maxFlipRow(filteredRows);

    setText("csx-card-dominant-decision", dominantDecision);
    setText("csx-card-riskiest-space", riskSpace);
    setText(
      "csx-card-max-flip",
      topFlip ? asNumber(topFlip.flip_rate_mean, 0).toFixed(4) + " (" + String(topFlip.claim_pair || "claim") + ")" : "-"
    );
    setText(
      "csx-card-adaptive-quality",
      adaptiveTotal > 0 ? adaptiveWithBlock + "/" + adaptiveTotal + " (" + formatPct(adaptiveWithBlock / adaptiveTotal) + ")" : "-"
    );
  }

  function renderFromState() {
    var filteredRows = filterRows(state.comparativeRows);
    var decisionCounts = countBy(filteredRows, function (row) { return row.decision || "unknown"; });
    var spaceCounts = countBy(filteredRows, function (row) { return row.space_preset || "unknown"; });
    var experimentAgg = aggregateExperiments(state.experiments);

    renderBars("csx-decision-bars", decisionCounts, ["stable", "unstable", "inconclusive", "unknown"]);
    renderBars("csx-claimtype-bars", experimentAgg.claimTypeCounts, ["ranking", "decision", "distribution", "unknown"]);
    renderBars("csx-space-bars", spaceCounts);
    renderBars("csx-adaptive-stop-bars", experimentAgg.adaptiveStops, [
      "target_ci_width_reached",
      "max_budget_reached",
      "no_candidate_configs",
      "unknown",
    ]);

    setText("csx-adaptive-total", String(experimentAgg.adaptiveTotal));
    setText("csx-adaptive-with-block", String(experimentAgg.adaptiveWithBlock));
    setText(
      "csx-adaptive-rate",
      experimentAgg.adaptiveTotal > 0 ? formatPct(experimentAgg.adaptiveWithBlock / experimentAgg.adaptiveTotal) : "-"
    );

    renderTopFlipTable(filteredRows);
    renderCards(filteredRows, decisionCounts, experimentAgg.adaptiveTotal, experimentAgg.adaptiveWithBlock);
  }

  function renderPayload(payload) {
    var meta = payload && payload.meta ? payload.meta : {};
    var experiments = toArray(payload && payload.experiments);
    var comparativeRows = toArray((((payload || {}).comparative || {}).space_claim_delta));

    state.payload = payload;
    state.experiments = experiments;
    state.comparativeRows = comparativeRows;

    setText("csx-meta-suite", String(meta.suite || "-"));
    setText("csx-meta-task", String(meta.task || "-"));
    setText("csx-meta-experiments", String(experiments.length));
    setText("csx-meta-comparative", String(comparativeRows.length));
    setText("csx-meta-deltas", toArray(meta.deltas).join(", ") || "-");
    setText("csx-meta-generated", String(meta.generated_by || "-"));

    var claimTypes = Object.keys(countBy(comparativeRows, function (row) { return row.claim_type || "unknown"; }));
    var spaces = Object.keys(countBy(comparativeRows, function (row) { return row.space_preset || "unknown"; }));
    populateFilter("csx-filter-claim-type", claimTypes);
    populateFilter("csx-filter-space", spaces);

    renderFromState();
  }

  function parseAndRender(raw, statusEl) {
    try {
      var payload = JSON.parse(raw);
      renderPayload(payload);
      statusEl.textContent = "Loaded successfully.";
      statusEl.classList.remove("error");
    } catch (err) {
      statusEl.textContent = "Invalid JSON: " + (err && err.message ? err.message : "parse failed");
      statusEl.classList.add("error");
    }
  }

  function bindSelectReRender(id) {
    var el = document.getElementById(id);
    if (!el) return;
    if (el.dataset.csxBound === "1") return;
    el.dataset.csxBound = "1";
    el.addEventListener("change", function () {
      if (!state.payload) return;
      renderFromState();
    });
  }

  function initClaimExplorer() {
    var fileInput = document.getElementById("csx-file");
    var parseButton = document.getElementById("csx-parse-text");
    var clearButton = document.getElementById("csx-clear");
    var textInput = document.getElementById("csx-json-text");
    var statusEl = document.getElementById("csx-status");

    if (!fileInput || !parseButton || !clearButton || !textInput || !statusEl) return;
    if (fileInput.dataset.csxBound === "1") return;
    fileInput.dataset.csxBound = "1";

    fileInput.addEventListener("change", function (evt) {
      var file = evt.target && evt.target.files ? evt.target.files[0] : null;
      if (!file) return;
      var reader = new FileReader();
      reader.onload = function () {
        var raw = String(reader.result || "");
        textInput.value = raw;
        parseAndRender(raw, statusEl);
      };
      reader.onerror = function () {
        statusEl.textContent = "Failed to read file.";
        statusEl.classList.add("error");
      };
      reader.readAsText(file, "utf-8");
    });

    parseButton.addEventListener("click", function () {
      parseAndRender(String(textInput.value || ""), statusEl);
    });

    clearButton.addEventListener("click", function () {
      textInput.value = "";
      statusEl.textContent = "Cleared.";
      statusEl.classList.remove("error");
      state.payload = null;
      renderPayload({ meta: {}, experiments: [], comparative: { space_claim_delta: [] } });
    });

    bindSelectReRender("csx-filter-claim-type");
    bindSelectReRender("csx-filter-space");
  }

  document.addEventListener("DOMContentLoaded", initClaimExplorer);
  if (typeof window.document$ !== "undefined" && typeof window.document$.subscribe === "function") {
    window.document$.subscribe(initClaimExplorer);
  }
})();
