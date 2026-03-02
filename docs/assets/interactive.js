(function () {
  function fmt(x, digits) {
    return Number(x).toFixed(digits);
  }

  function clamp(x, lo, hi) {
    return Math.min(hi, Math.max(lo, x));
  }

  function wilson(successes, total, z) {
    if (total <= 0) return { rate: 0, lo: 0, hi: 1 };
    const phat = successes / total;
    const z2 = z * z;
    const denom = 1 + z2 / total;
    const center = (phat + z2 / (2 * total)) / denom;
    const margin = (z / denom) * Math.sqrt((phat * (1 - phat) + z2 / (4 * total)) / total);
    return {
      rate: phat,
      lo: clamp(center - margin, 0, 1),
      hi: clamp(center + margin, 0, 1),
    };
  }

  function decision(lo, hi, threshold) {
    if (lo >= threshold) return "stable";
    if (hi < threshold) return "unstable";
    return "inconclusive";
  }

  function setDecisionClass(el, label) {
    el.classList.remove("stable", "unstable", "inconclusive");
    el.classList.add(label);
  }

  function confidenceToZ(c) {
    if (Math.abs(c - 0.90) < 1e-9) return 1.6448536269514722;
    if (Math.abs(c - 0.99) < 1e-9) return 2.5758293035489004;
    return 1.959963984540054; // default 95%
  }

  function updateClaimWidget() {
    const sEl = document.getElementById("cs-successes");
    const tEl = document.getElementById("cs-total");
    const cEl = document.getElementById("cs-confidence");
    const pEl = document.getElementById("cs-threshold");
    if (!sEl || !tEl || !cEl || !pEl) return;

    let s = parseInt(sEl.value || "0", 10);
    let t = parseInt(tEl.value || "1", 10);
    const c = parseFloat(cEl.value || "0.95");
    const p = parseFloat(pEl.value || "0.95");

    t = Math.max(1, t);
    s = Math.max(0, Math.min(s, t));

    const z = confidenceToZ(c);
    const est = wilson(s, t, z);
    const d = decision(est.lo, est.hi, p);

    document.getElementById("cs-rate").textContent = fmt(est.rate, 4);
    document.getElementById("cs-ci").textContent = `[${fmt(est.lo, 4)}, ${fmt(est.hi, 4)}]`;
    const dEl = document.getElementById("cs-decision");
    dEl.textContent = d;
    setDecisionClass(dEl, d);
  }

  function humanTime(seconds) {
    if (!Number.isFinite(seconds) || seconds < 0) return "-";
    if (seconds < 60) return `${fmt(seconds, 1)}s`;
    const mins = seconds / 60;
    if (mins < 60) return `${fmt(mins, 1)}m`;
    const hrs = mins / 60;
    return `${fmt(hrs, 2)}h`;
  }

  function updateSpaceWidget() {
    const ids = ["ps-seed-t", "ps-opt", "ps-layout", "ps-shots", "ps-seed-s", "ps-instances", "ps-k", "ps-sec"];
    if (!ids.every((id) => document.getElementById(id))) return;

    const seedT = Math.max(1, parseInt(document.getElementById("ps-seed-t").value || "1", 10));
    const opt = Math.max(1, parseInt(document.getElementById("ps-opt").value || "1", 10));
    const layout = Math.max(1, parseInt(document.getElementById("ps-layout").value || "1", 10));
    const shots = Math.max(1, parseInt(document.getElementById("ps-shots").value || "1", 10));
    const seedS = Math.max(1, parseInt(document.getElementById("ps-seed-s").value || "1", 10));
    const instances = Math.max(1, parseInt(document.getElementById("ps-instances").value || "1", 10));
    const k = Math.max(1, parseInt(document.getElementById("ps-k").value || "1", 10));
    const sec = Math.max(0.01, parseFloat(document.getElementById("ps-sec").value || "0.5"));

    const space = seedT * opt * layout * shots * seedS;
    const fullRuns = space * instances;
    const randRuns = k * instances;
    const reduction = 100 * (1 - randRuns / fullRuns);

    document.getElementById("ps-space").textContent = `${space.toLocaleString()} configs`;
    document.getElementById("ps-full-runs").textContent = fullRuns.toLocaleString();
    document.getElementById("ps-rand-runs").textContent = randRuns.toLocaleString();
    document.getElementById("ps-full-time").textContent = humanTime(fullRuns * sec);
    document.getElementById("ps-rand-time").textContent = humanTime(randRuns * sec);
    document.getElementById("ps-reduction").textContent = `${fmt(reduction, 2)}% fewer runs`;
  }

  function bind(ids, fn) {
    ids.forEach((id) => {
      const el = document.getElementById(id);
      if (el) {
        el.addEventListener("input", fn);
        el.addEventListener("change", fn);
      }
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    bind(["cs-successes", "cs-total", "cs-confidence", "cs-threshold"], updateClaimWidget);
    bind(["ps-seed-t", "ps-opt", "ps-layout", "ps-shots", "ps-seed-s", "ps-instances", "ps-k", "ps-sec"], updateSpaceWidget);
    updateClaimWidget();
    updateSpaceWidget();
  });
})();
