(function () {
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

  function renderBars(containerId, counts, order) {
    var container = document.getElementById(containerId);
    if (!container) return;
    clearElement(container);
    var keys = order && order.length ? order.filter(function (k) { return Object.prototype.hasOwnProperty.call(counts, k); }) : Object.keys(counts);
    if (!keys.length) {
      container.textContent = "No data.";
      return;
    }
    var total = keys.reduce(function (acc, key) { return acc + asNumber(counts[key], 0); }, 0);
    if (total <= 0) {
      container.textContent = "No data.";
      return;
    }
    keys.forEach(function (key) {
      var count = asNumber(counts[key], 0);
      var rate = count / total;
      var row = document.createElement("div");
      row.className = "csx-bar-row";

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

  function aggregateComparativeRows(rows) {
    var decisionCounts = { stable: 0, unstable: 0, inconclusive: 0 };
    var spaceCounts = {};
    rows.forEach(function (row) {
      var d = String((row && row.decision) || "unknown");
      if (!Object.prototype.hasOwnProperty.call(decisionCounts, d)) {
        decisionCounts[d] = 0;
      }
      decisionCounts[d] += 1;
      var space = String((row && row.space_preset) || "unknown");
      spaceCounts[space] = (spaceCounts[space] || 0) + 1;
    });
    return { decisionCounts: decisionCounts, spaceCounts: spaceCounts };
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

  function renderTopFlipTable(rows) {
    var body = document.getElementById("csx-topflip-body");
    if (!body) return;
    clearElement(body);
    if (!rows.length) {
      var trEmpty = document.createElement("tr");
      var tdEmpty = document.createElement("td");
      tdEmpty.colSpan = 6;
      tdEmpty.textContent = "No comparative rows.";
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

  function renderPayload(payload) {
    var meta = payload && payload.meta ? payload.meta : {};
    var experiments = toArray(payload && payload.experiments);
    var comparativeRows = toArray((((payload || {}).comparative || {}).space_claim_delta));

    setText("csx-meta-suite", String(meta.suite || "-"));
    setText("csx-meta-task", String(meta.task || "-"));
    setText("csx-meta-experiments", String(experiments.length));
    setText("csx-meta-comparative", String(comparativeRows.length));
    setText("csx-meta-deltas", toArray(meta.deltas).join(", ") || "-");
    setText("csx-meta-generated", String(meta.generated_by || "-"));

    var comparativeAgg = aggregateComparativeRows(comparativeRows);
    var experimentAgg = aggregateExperiments(experiments);

    renderBars("csx-decision-bars", comparativeAgg.decisionCounts, ["stable", "unstable", "inconclusive", "unknown"]);
    renderBars("csx-claimtype-bars", experimentAgg.claimTypeCounts);
    renderBars("csx-space-bars", comparativeAgg.spaceCounts);
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

    renderTopFlipTable(comparativeRows);
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
      renderPayload({ meta: {}, experiments: [], comparative: { space_claim_delta: [] } });
    });
  }

  document.addEventListener("DOMContentLoaded", initClaimExplorer);
  if (typeof window.document$ !== "undefined" && typeof window.document$.subscribe === "function") {
    window.document$.subscribe(initClaimExplorer);
  }
})();
