(function () {
  function normalize(value) {
    return String(value || "").toLowerCase().trim();
  }

  function bindDatasetRegistry() {
    var table = document.querySelector(".csr-table");
    if (!table) return;
    if (table.dataset.csrBound === "1") return;
    table.dataset.csrBound = "1";

    var rows = Array.prototype.slice.call(table.querySelectorAll("tbody tr.csr-row"));
    var filterInput = document.getElementById("csr-filter");
    var taskSelect = document.getElementById("csr-filter-task");
    var claimSelect = document.getElementById("csr-filter-claim");
    var visibleCount = document.getElementById("csr-visible-count");

    function rowMatches(row) {
      var searchNeedle = normalize(filterInput ? filterInput.value : "");
      var selectedTask = normalize(taskSelect ? taskSelect.value : "");
      var selectedClaim = normalize(claimSelect ? claimSelect.value : "");
      var task = normalize(row.getAttribute("data-task"));
      var claims = normalize(row.getAttribute("data-claims"));
      var search = normalize(row.getAttribute("data-search"));

      var searchOk = !searchNeedle || search.indexOf(searchNeedle) >= 0;
      var taskOk = !selectedTask || task === selectedTask;
      var claimOk = !selectedClaim || claims.split(",").map(normalize).indexOf(selectedClaim) >= 0;
      return searchOk && taskOk && claimOk;
    }

    function applyFilters() {
      var shown = 0;
      rows.forEach(function (row) {
        var show = rowMatches(row);
        row.style.display = show ? "" : "none";
        if (show) shown += 1;
      });
      if (visibleCount) visibleCount.textContent = String(shown);
    }

    function goToRowTarget(row) {
      var href = String(row.getAttribute("data-href") || "");
      if (!href) return;
      if (href.charAt(0) === "#") {
        window.location.hash = href.slice(1);
      } else {
        window.location.href = href;
      }
    }

    rows.forEach(function (row) {
      row.addEventListener("click", function (evt) {
        if (evt.target && evt.target.closest("a,button,input,select,textarea,label,summary")) return;
        goToRowTarget(row);
      });
      row.addEventListener("keydown", function (evt) {
        if (evt.key !== "Enter" && evt.key !== " ") return;
        evt.preventDefault();
        goToRowTarget(row);
      });
    });

    [filterInput, taskSelect, claimSelect].forEach(function (el) {
      if (!el) return;
      var eventName = el.tagName === "SELECT" ? "change" : "input";
      el.addEventListener(eventName, applyFilters);
    });

    applyFilters();
  }

  document.addEventListener("DOMContentLoaded", bindDatasetRegistry);
  if (typeof window.document$ !== "undefined" && typeof window.document$.subscribe === "function") {
    window.document$.subscribe(bindDatasetRegistry);
  }
})();
