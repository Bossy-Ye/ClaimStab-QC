# Evaluation Readiness (Frozen Matrix Baseline)

Updated: 2026-03-11

## Matrix Status

The evaluation matrix is frozen after one targeted E5 adjustment (`adaptive_ci_tuned` with relaxed CI-width target = `0.11`).

Canonical baseline:

- E1 MaxCut ranking
- E2 GHZ structural control
- E3 BV decision control
- E4 Grover distribution stress
- E5 Cost-confidence tradeoff (with tuned adaptive run)

No new tasks, claim types, or perturbation spaces were added.

## Final Experiment Counts

- E1 (`output/presentation_large/large/maxcut_ranking/claim_stability.json`):
  - 27 comparative rows: 24 unstable, 2 stable, 1 inconclusive
  - by space:
    - `compilation_only`: 2 stable, 1 inconclusive, 6 unstable
    - `sampling_only`: 9 unstable
    - `combined_light`: 9 unstable
- E2 (`output/presentation_large/large/ghz_structural/claim_stability.json`):
  - 12/12 stable
- E3 (`output/presentation_large/large/bv_decision/claim_stability.json`):
  - 4/4 stable
- E4 (`output/presentation_large/large/grover_distribution/claim_stability.json`):
  - 4/4 unstable
- E5 (`output/presentation_large/rq4_adaptive/rq4_adaptive_tuned_summary.json`):
  - strategies: `full_factorial`, `random_k_32`, `random_k_64`, `adaptive_ci`, `adaptive_ci_tuned`
  - all strategies match full-factorial decisions on both deltas (`agreement_with_factorial.rate = 1.0`)

## Main Signals by RQ

- RQ1 (prevalence + heterogeneity):
  - instability is concentrated in MaxCut ranking and is strongly space-dependent
  - mean `flip_rate_mean` by space (E1):
    - `compilation_only`: 0.0745
    - `sampling_only`: 0.2588
    - `combined_light`: 0.2028
- RQ2 (mechanisms, drivers, interactions, and boundaries):
  - main-effect/attribution signals remain strongest on MaxCut and support perturbation-driver interpretation
- RQ4 (cost-confidence):
  - `adaptive_ci` (strict target 0.05): no cost gain (`max_budget_reached`, cost 495)
  - `adaptive_ci_tuned` (target 0.11): early stop (`target_ci_width_reached`), mean cost 320 vs 495 full-factorial, same decisions
- Control/stress interpretation:
  - GHZ/BV provide robust-control evidence (stable)
  - Grover distribution provides high-fragility stress evidence (unstable)

## Figure Mapping (Main vs Appendix)

Main-paper figures:

- `output/paper_pack/figures/main/fig1_stability_profile.(pdf|svg|png)` (RQ1)
- `output/paper_pack/figures/main/fig2_robustness_cells_by_delta.(pdf|png)` (RQ2-supporting robustness contrast in main set)
- `output/paper_pack/figures/main/fig3_claim_distribution.(pdf|svg|png)` (RQ3)
- `output/paper_pack/figures/main/fig4_cost_confidence_tradeoff.(pdf|svg|png)` (RQ4)

RQ2 mechanism diagnostics and older variants are retained in legacy archive form under:

- `output/paper_pack/figures/_archive_legacy/`

Appendix figures:

- staged under `output/paper_pack/figures/appendix/`
- includes degenerate/near-constant control panels (GHZ/BV), multidevice heatmaps, and Grover near-constant strips

Figure staging manifest:

- `output/paper_pack/figures/paper_figure_map.json`

## Freeze Confirmation

This round only changes E5 adaptive target strictness for the tuned run and figure/readiness packaging.
All other matrix dimensions are unchanged.
