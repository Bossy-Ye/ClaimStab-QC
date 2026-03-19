# Live Claim Explorer

<div class="csx-hero">
  <div>
    <p class="csx-eyebrow">Cloud-First Interaction</p>
    <h2>Inspect ClaimStab outputs in seconds</h2>
    <p>Upload a <code>claim_stability.json</code> file and get immediate stability insights: decisions, spaces, claim types, adaptive coverage, and high-flip hotspots.</p>
    <div class="csx-hero-links">
      <a class="csx-link-chip" href="https://bossy-ye.github.io/ClaimStab-QC/quickstart/">Run CLI Locally</a>
      <a class="csx-link-chip" href="https://bossy-ye.github.io/ClaimStab-QC/reproduce/">Reproduction Guide</a>
      <a class="csx-link-chip" href="https://bossy-ye.github.io/ClaimStab-QC/dataset_registry/">Browse Public Datasets</a>
    </div>
  </div>
</div>

??? info "Input Format and Example (click to expand)"
    Use a ClaimStab output file named `claim_stability.json`.

    Recommended examples:
    - `output/paper/evaluation_v2/runs/E1_maxcut_main/claim_stability.json`
    - `output/paper/evaluation_v2/runs/E4_grover_distribution/claim_stability.json`
    - `output/tmp_smoke/adaptive_bv_smoke/claim_stability.json`

    Minimum structure:
    - `meta`
    - `experiments`
    - `comparative.space_claim_delta`

    Standard labels:
    - `decision`: `stable` | `unstable` | `inconclusive`
    - `claim_type`: `ranking` | `decision` | `distribution`
    - `adaptive_stopping.stop_reason`: `target_ci_width_reached` | `max_budget_reached` | `no_candidate_configs`

    Variation-rich demo example (recommended for this page):

    ```json
    {
      "meta": {
        "suite": "demo_mixed",
        "task": "mixed_claims",
        "deltas": [0.0, 0.01, 0.05],
        "generated_by": "explorer_demo_v2"
      },
      "experiments": [
        {
          "experiment_id": "compilation_only:QAOA_p2>RandomBaseline",
          "claim": { "type": "ranking" },
          "sampling": { "mode": "random_k", "sample_size": 64 }
        },
        {
          "experiment_id": "sampling_only:QAOA_p2>QAOA_p1",
          "claim": { "type": "ranking" },
          "sampling": {
            "mode": "adaptive_ci",
            "adaptive_stopping": {
              "enabled": true,
              "target_ci_width": 0.1,
              "achieved_ci_width": 0.12,
              "stop_reason": "max_budget_reached"
            }
          }
        },
        {
          "experiment_id": "sampling_only:BVOracle:decision_top1",
          "claim": { "type": "decision" },
          "sampling": {
            "mode": "adaptive_ci",
            "adaptive_stopping": {
              "enabled": true,
              "target_ci_width": 0.08,
              "achieved_ci_width": 0.07,
              "stop_reason": "target_ci_width_reached"
            }
          }
        },
        {
          "experiment_id": "combined_light:GroverOracle:distribution",
          "claim": { "type": "distribution" },
          "sampling": {
            "mode": "adaptive_ci",
            "adaptive_stopping": {
              "enabled": true,
              "target_ci_width": 0.05,
              "achieved_ci_width": null,
              "stop_reason": "no_candidate_configs"
            }
          }
        }
      ],
      "comparative": {
        "space_claim_delta": [
          {
            "space_preset": "compilation_only",
            "claim_pair": "QAOA_p2>RandomBaseline",
            "claim_type": "ranking",
            "delta": 0.0,
            "decision": "stable",
            "flip_rate_mean": 0.03
          },
          {
            "space_preset": "compilation_only",
            "claim_pair": "QAOA_p2>RandomBaseline",
            "claim_type": "ranking",
            "delta": 0.05,
            "decision": "inconclusive",
            "flip_rate_mean": 0.11
          },
          {
            "space_preset": "sampling_only",
            "claim_pair": "QAOA_p2>QAOA_p1",
            "claim_type": "ranking",
            "delta": 0.0,
            "decision": "unstable",
            "flip_rate_mean": 0.29
          },
          {
            "space_preset": "sampling_only",
            "claim_pair": "QAOA_p2>QAOA_p1",
            "claim_type": "ranking",
            "delta": 0.05,
            "decision": "unstable",
            "flip_rate_mean": 0.38
          },
          {
            "space_preset": "combined_light",
            "claim_pair": "QAOA_p1>RandomBaseline",
            "claim_type": "ranking",
            "delta": 0.01,
            "decision": "stable",
            "flip_rate_mean": 0.09
          },
          {
            "space_preset": "sampling_only",
            "claim_pair": "BVOracle:top_k=1",
            "claim_type": "decision",
            "delta": null,
            "decision": "stable",
            "flip_rate_mean": 0.04
          },
          {
            "space_preset": "combined_light",
            "claim_pair": "BVOracle:top_k=3",
            "claim_type": "decision",
            "delta": null,
            "decision": "inconclusive",
            "flip_rate_mean": 0.13
          },
          {
            "space_preset": "sampling_only",
            "claim_pair": "GroverOracle:dist<=0.06",
            "claim_type": "distribution",
            "delta": null,
            "decision": "unstable",
            "flip_rate_mean": 0.42
          },
          {
            "space_preset": "combined_light",
            "claim_pair": "GroverOracle:dist<=0.06",
            "claim_type": "distribution",
            "delta": null,
            "decision": "inconclusive",
            "flip_rate_mean": 0.18
          }
        ]
      }
    }
    ```

## Load Run Output

<div class="csx-shell">
  <div class="csx-panel">
    <h3>Input</h3>
    <div class="csx-upload-grid">
      <label class="csx-field">
        <span>Upload claim_stability.json</span>
        <input id="csx-file" type="file" accept=".json,application/json" />
      </label>
      <button id="csx-parse-text" class="csx-btn" type="button">Parse Text</button>
      <button id="csx-clear" class="csx-btn csx-btn-muted" type="button">Clear</button>
    </div>
    <label class="csx-field">
      <span>Or paste JSON directly</span>
      <textarea id="csx-json-text" rows="8" placeholder='{"meta": {...}, "experiments": [...], "comparative": {...}}'></textarea>
    </label>
    <p id="csx-status" class="csx-status">No data loaded.</p>
  </div>

  <div class="csx-panel">
    <h3>Run Metadata</h3>
    <div class="csx-kv-grid">
      <div><b>Suite:</b> <span id="csx-meta-suite">-</span></div>
      <div><b>Task:</b> <span id="csx-meta-task">-</span></div>
      <div><b>Experiments:</b> <span id="csx-meta-experiments">-</span></div>
      <div><b>Comparative rows:</b> <span id="csx-meta-comparative">-</span></div>
      <div><b>Deltas:</b> <span id="csx-meta-deltas">-</span></div>
      <div><b>Generated by:</b> <span id="csx-meta-generated">-</span></div>
    </div>
  </div>
</div>

## Executive Signals

<div class="csx-card-grid">
  <div class="csx-card">
    <p class="csx-card-label">Dominant decision</p>
    <p id="csx-card-dominant-decision" class="csx-card-value">-</p>
  </div>
  <div class="csx-card">
    <p class="csx-card-label">Riskiest space</p>
    <p id="csx-card-riskiest-space" class="csx-card-value">-</p>
  </div>
  <div class="csx-card">
    <p class="csx-card-label">Max observed flip</p>
    <p id="csx-card-max-flip" class="csx-card-value">-</p>
  </div>
  <div class="csx-card">
    <p class="csx-card-label">Adaptive metadata quality</p>
    <p id="csx-card-adaptive-quality" class="csx-card-value">-</p>
  </div>
</div>

## Decision Distribution

<div class="csx-panel">
  <div id="csx-decision-bars" class="csx-bars"></div>
</div>

## Claim Types and Spaces

<div class="csx-shell">
  <div class="csx-panel">
    <h3>Claim Type Mix</h3>
    <div id="csx-claimtype-bars" class="csx-bars"></div>
  </div>
  <div class="csx-panel">
    <h3>Space Coverage</h3>
    <div id="csx-space-bars" class="csx-bars"></div>
  </div>
</div>

## Adaptive Sampling Coverage

<div class="csx-panel">
  <div class="csx-kv-grid">
    <div><b>Adaptive experiments:</b> <span id="csx-adaptive-total">-</span></div>
    <div><b>With adaptive_stopping:</b> <span id="csx-adaptive-with-block">-</span></div>
    <div><b>Coverage:</b> <span id="csx-adaptive-rate">-</span></div>
  </div>
  <div id="csx-adaptive-stop-bars" class="csx-bars"></div>
</div>

## High-Flip Triage

<div class="csx-panel">
  <div class="csx-filter-grid">
    <label class="csx-field">
      <span>Filter by claim type</span>
      <select id="csx-filter-claim-type">
        <option value="all">all</option>
      </select>
    </label>
    <label class="csx-field">
      <span>Filter by space</span>
      <select id="csx-filter-space">
        <option value="all">all</option>
      </select>
    </label>
  </div>
  <div class="csx-table-wrap">
    <table class="csx-table">
      <thead>
        <tr>
          <th>space</th>
          <th>claim</th>
          <th>type</th>
          <th>delta</th>
          <th>decision</th>
          <th>flip_rate_mean</th>
        </tr>
      </thead>
      <tbody id="csx-topflip-body">
        <tr><td colspan="6">Load a JSON file to populate this table.</td></tr>
      </tbody>
    </table>
  </div>
</div>
