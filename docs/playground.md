# Interactive Playground

Use these interactive widgets to understand how ClaimStab decisions respond to sampling statistics and perturbation-space size.

## 1) Stability Decision Simulator

<div class="cs-widget">
  <div class="cs-grid">
    <label>Stable outcomes
      <input id="cs-successes" type="number" min="0" value="190" />
    </label>
    <label>Total outcomes
      <input id="cs-total" type="number" min="1" value="200" />
    </label>
    <label>Confidence level
      <select id="cs-confidence">
        <option value="0.90">0.90</option>
        <option value="0.95" selected>0.95</option>
        <option value="0.99">0.99</option>
      </select>
    </label>
    <label>Stability threshold p
      <input id="cs-threshold" type="number" min="0" max="1" step="0.01" value="0.95" />
    </label>
  </div>
  <div class="cs-output">
    <p><b>Estimated stability:</b> <span id="cs-rate">-</span></p>
    <p><b>Wilson CI:</b> <span id="cs-ci">-</span></p>
    <p><b>Conservative decision:</b> <span id="cs-decision" class="cs-pill">-</span></p>
  </div>
</div>

Decision rule implemented:
- `stable` if `CI_low >= p`
- `unstable` if `CI_high < p`
- `inconclusive` otherwise

## 2) Perturbation Space + Cost Simulator

<div class="cs-widget">
  <div class="cs-grid">
    <label>Seeds (transpiler)
      <input id="ps-seed-t" type="number" min="1" value="10" />
    </label>
    <label>Optimization levels
      <input id="ps-opt" type="number" min="1" value="4" />
    </label>
    <label>Layouts
      <input id="ps-layout" type="number" min="1" value="2" />
    </label>
    <label>Shots options
      <input id="ps-shots" type="number" min="1" value="5" />
    </label>
    <label>Simulator seeds
      <input id="ps-seed-s" type="number" min="1" value="20" />
    </label>
    <label>Instances
      <input id="ps-instances" type="number" min="1" value="30" />
    </label>
    <label>Random-k sample size
      <input id="ps-k" type="number" min="1" value="64" />
    </label>
    <label>Estimated seconds / run
      <input id="ps-sec" type="number" min="0.01" step="0.01" value="0.5" />
    </label>
  </div>
  <div class="cs-output">
    <p><b>Full space size:</b> <span id="ps-space">-</span></p>
    <p><b>Full-factorial runs:</b> <span id="ps-full-runs">-</span> (<span id="ps-full-time">-</span>)</p>
    <p><b>Random-k runs:</b> <span id="ps-rand-runs">-</span> (<span id="ps-rand-time">-</span>)</p>
    <p><b>Run reduction:</b> <span id="ps-reduction">-</span></p>
  </div>
</div>

This mirrors ClaimStab’s practical strategy: exhaustive calibration for smaller settings, random-k for broad-scale evaluation.

## 3) Ranking Flip Simulator

Try a single baseline vs perturbed comparison and see whether a rank flip occurs.

<div class="cs-widget">
  <div class="cs-grid">
    <label>Direction
      <select id="rk-direction">
        <option value="higher_is_better" selected>higher_is_better</option>
        <option value="lower_is_better">lower_is_better</option>
      </select>
    </label>
    <label>Delta (δ)
      <input id="rk-delta" type="number" min="0" step="0.001" value="0.01" />
    </label>
    <label>Baseline score A
      <input id="rk-base-a" type="number" step="0.0001" value="0.62" />
    </label>
    <label>Baseline score B
      <input id="rk-base-b" type="number" step="0.0001" value="0.60" />
    </label>
    <label>Perturbed score A
      <input id="rk-pert-a" type="number" step="0.0001" value="0.58" />
    </label>
    <label>Perturbed score B
      <input id="rk-pert-b" type="number" step="0.0001" value="0.59" />
    </label>
  </div>
  <div class="cs-output">
    <p><b>Baseline claim state:</b> <span id="rk-base-state">-</span></p>
    <p><b>Perturbed claim state:</b> <span id="rk-pert-state">-</span></p>
    <p><b>Flip status:</b> <span id="rk-flip" class="cs-pill">-</span></p>
  </div>
</div>
