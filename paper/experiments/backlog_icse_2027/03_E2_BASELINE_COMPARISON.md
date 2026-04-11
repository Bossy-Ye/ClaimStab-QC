# 03 E2 Baseline Comparison

## Goal

Show that common evaluation strategies cannot substitute claim-level validation.
This task exists to block the reviewer objection that `RQ1` only defeats one
weak frozen baseline.

## Scope Freeze

- This task reuses the same comparative / ranking claim variants as `02`.
- No new large experiment family should be introduced here.
- The comparison unit remains the claim variant, not raw run count.
- `ClaimStab` remains the reference validation method, not a baseline.

## Frozen Baselines

The comparison set should remain small and explicit.

Required non-ClaimStab baselines:

- `single_baseline_realistic`
  - uses the existing realistic naive baseline signal already stored in
    `claim_stability.json`
  - supportive iff the baseline configuration satisfies the claim

- `metric_mean_ci`
  - uses the frozen metric baseline already used by `02`
  - supportive iff the metric margin is positive and its confidence interval is
    strictly above zero

- `support_ratio_heuristic`
  - uses the observed fraction of admissible configurations under which the
    claim holds
  - supportive iff `claim_holds_rate_mean > 0.50`

- `local_sensitivity_check`
  - uses one-factor-local perturbation checks around a scope-aware baseline
    anchor
  - supportive iff no single-factor local variation overturns the
    instance-averaged baseline relation

Optional only if implementation is cheap and semantics remain clean:

- `fixed_budget_metric_rerun`
  - fixed-budget resampled metric baseline over configuration cells
  - do not include this baseline if it delays the main four above

Reference method:

- mean + confidence interval
- repeated runs
- local sensitivity analysis
- simple support-ratio / robustness heuristic
- ClaimStab verdict

## Inputs

- `/Users/mac/Documents/GitHub/ClaimStab-QC/output/paper/icse_pack/derived/RQ1/metric_claim_comparison_dataset.csv`
- existing `W3` analyses and sensitivity outputs under:
  - `/Users/mac/Documents/GitHub/ClaimStab-QC/output/paper/evaluation_v3/derived_paper_evaluation/RQ1_necessity/`
- existing comparative runs:
  - `E1 MaxCut`
  - `W1 Max-2-SAT`
  - `W1 VQE/H2`
- current script base:
  - `/Users/mac/Documents/GitHub/ClaimStab-QC/paper/experiments/scripts/derive_rq1_metric_baselines_v3.py`
  - `/Users/mac/Documents/GitHub/ClaimStab-QC/paper/experiments/scripts/derive_e1_metric_vs_claim_icse.py`
  - `/Users/mac/Documents/GitHub/ClaimStab-QC/claimstab/figures/baseline_compare.py`

## Required Dataset Schema

Each row should represent one claim variant and include at least:

- `claim_id`
- `algorithm_family`
- `scope`
- `delta`
- `claim_validation_outcome`
- `claimstab_decision`
- `single_baseline_realistic_verdict`
- `metric_mean_ci_verdict`
- `support_ratio_verdict`
  - implemented as `majority_support_ratio_verdict`
- `local_sensitivity_verdict`
- optional: `fixed_budget_metric_rerun_verdict`

## Baseline Semantics

These verdicts must be defined explicitly in code and in the paper note.

- `supportive`
- `non_supportive`
- optional: `uninformative`

The output note must state which baselines can abstain and which cannot.

## Outputs

- Unified dataset:
  - `output/paper/icse_pack/derived/RQ1/baseline_comparison_dataset.csv`
  - `output/paper/icse_pack/derived/RQ1/baseline_comparison_dataset.json`
- Main-paper table:
  - `output/paper/icse_pack/tables/tab2_baseline_capability_matrix.csv`
- Main-paper comparison table:
  - `output/paper/icse_pack/tables/tab_baseline_disagreement_summary.csv`
- Main-paper figure:
  - `output/paper/icse_pack/figures/main/fig2_validated_vs_false_reassurance.png`
  - `output/paper/icse_pack/figures/main/fig2_validated_vs_false_reassurance.pdf`
- Supporting note:
  - `output/paper/icse_pack/derived/RQ1/baseline_comparison_interpretation.md`

## Canonical Figure Timing

The canonical paper figure for this task is generated only after:

- all baseline semantics are frozen in code
- the comparison dataset is complete on the same claim variants as `02`
- the disagreement summary table is stable

The canonical figure role is:

- `Fig 2` main-paper baseline comparison

## Execution Steps

- [x] Freeze the baseline universe and verdict semantics.
- [x] Build a unified baseline-comparison dataset over the same claim variants as `02`.
- [x] Generate the capability matrix.
- [x] Generate the disagreement summary table.
- [x] Generate the main-paper comparison figure.
- [x] Write a short interpretation note for `RQ1`.

## Acceptance Criteria

- [x] At least four non-ClaimStab baselines are represented.
- [x] Baseline outputs are comparable on the same claim instances.
- [x] Every baseline supportive verdict is operationally defined, not narrative only.
- [x] The resulting table/figure makes clear that the baselines do not replace claim validation.
- [x] Capability dimensions are explicit, not narrative only.
- [x] At least one baseline fails clearly on the current `RQ1` mismatch population.
- [x] The canonical comparison figure is generated only after the baseline dataset and disagreement summary are frozen.
- [x] The final figure and table can be cited directly in the paper without ad-hoc explanation.

## Dependencies

- [02_E1_METRIC_VS_CLAIM.md](./02_E1_METRIC_VS_CLAIM.md)

## Status

- [ ] Not started
- [ ] In progress
- [x] Done

## Notes

This task is primarily to block the “your baseline is too weak” reviewer attack.
Keep the baseline family small, explicit, and reviewer-legible. Do not let this
task expand into a new benchmark suite.
