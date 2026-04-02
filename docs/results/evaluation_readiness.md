# Evaluation Readiness (`evaluation_v2`)

Updated: 2026-03-19

## Active Bundle Status

The active paper-facing bundle is:

- `output/paper/evaluation_v2/`

This bundle supersedes older output roots such as:

- `output/presentations/large/`
- `output/paper/artifact/`
- `output/paper/pack/`
- `output/paper/multidevice/`

## Completed Runs

The current bundle contains completed outputs for:

- `E1` main MaxCut ranking battleground
- `E2` GHZ structural calibration
- `E3` BV decision calibration
- `E4` Grover distribution fragility case
- `E5` policy comparison on the expanded 495-configuration grid
- `S1` backend-conditioned transpile-only structural portability
- `S2` boundary stress
- `QEC` repetition-code portability illustration

## Current Counts

- `E1`: `25 unstable`, `2 stable`, `0 inconclusive`
- `E2`: `4 stable`, `8 inconclusive`
- `E3`: `4 stable`
- `E4`: `4 unstable`
- `E5`: all evaluated policies match `full_factorial` (`agreement = 1.0`)
- `S1`: `90/90 stable`
- `S2`: `16 unstable`
- `QEC`: `3 stable`, `1 unstable`

## Readiness Assessment

The current bundle is strong enough to support the main ICSE-style narrative, provided the writing reflects the actual rerun rather than the earlier plan.

What is strong now:

- `E1` clearly supports the main fragility-prevalence claim.
- The metric-based baseline mismatch is strong (`9/9` false reassurance under the fixed 5-run metric summary).
- Claim-family discrimination is visible across ranking, decision, and distribution claims.
- `E5` now supports a real cost/agreement tradeoff claim.

What must still be written carefully:

- `E2` is mixed (`stable` + `inconclusive`), not a pure stable control.
- `S2` became direct fragility rather than abstention.
- `S1` is a controlled transpile-only structural portability result, not a full noisy-device portability study.
- exact MOS objects are now materialized on the main-paper exact spaces; supplementary comparisons are staged under `output/paper/evaluation_v4/pack/tables/tab_c_exact_vs_greedy_mos.csv`.

## Main Figure Mapping

The active publication-facing figure set is:

- `output/paper/evaluation_v2/pack/figures/main/fig1_stability_profile.*`
- `output/paper/evaluation_v2/pack/figures/main/fig2_robustness_cells_by_delta.*`
- `output/paper/evaluation_v2/pack/figures/main/fig3_claim_distribution.*`
- `output/paper/evaluation_v2/pack/figures/main/fig4_e1_prevalence_by_scope.*`
- `output/paper/evaluation_v2/pack/figures/main/fig5_claim_metric_mismatch.*`
- `output/paper/evaluation_v2/pack/figures/main/fig6_claim_family_verdicts.*`
- `output/paper/evaluation_v2/pack/figures/main/fig_rq4_ci_width_vs_cost.*`

Supporting figures are staged under:

- `output/paper/evaluation_v2/pack/figures/appendix/`

## Derived Tables and Narrative Support

Paper-facing derived outputs live under:

- `output/paper/evaluation_v2/derived_paper_evaluation/`

Most important subdirectories:

- `RQ1_necessity/`
- `RQ2_semantics/`
- `RQ3_diagnostics/`
- `RQ4_practicality/`

The latest prose-ready summary is:

- `output/paper/evaluation_v2/derived_paper_evaluation/results_draft.md`

## Bottom Line

The repository is no longer in a “frozen old matrix” state. It now has an active, coherent `evaluation_v2` bundle with updated figures, derived tables, and a consistent output structure.

The main remaining work is no longer experiment execution; it is accurate public narration and deployment of the updated docs/pages.
