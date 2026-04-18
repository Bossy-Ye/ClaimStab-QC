# 02 E1 Metric vs Claim

## Goal

Produce the central paper-facing dataset and figures showing where metric-level evaluation and claim-level validation disagree.
This task supports the main RQ1 claim:

> Current empirical evaluation pipelines can statistically support outcomes without explicitly validating conclusions.

## Inputs

- `../../../output/paper/evaluation_v3/derived_paper_evaluation/RQ1_necessity/e1_metric_matched_scope_table.csv`
- `../../../output/paper/evaluation_v4/derived_paper_evaluation/RQ1_necessity/cross_family_metric_baselines.csv`
- Optional appendix/supporting source:
  - `../../../output/paper/evaluation_v3/derived_paper_evaluation/RQ1_necessity/e5_metric_fullgrid_table.csv`

## Scope Freeze

- Main-paper dataset covers comparative / ranking claim variants only.
- Main-paper core sources are:
  - MaxCut QAOA (`E1`)
  - Max-2-SAT QAOA (`W1`)
  - VQE/H2 (`W1`)
- `decision` and `distribution` claim families are not forced into this metric-baseline surface.
- `E5` 495-configuration sensitivity remains supporting material, not the main E1 dataset.

## Required Dataset Schema

Each row should represent one claim variant and include at least:

- `claim_id`
- `source_table_bundle`
- `source_experiment_bundle`
- `task_family`
- `algorithm_family`
- `claim_family`
- `run_id`
- `claim_pair`
- `scope`
- `delta`
- `higher_is_better`
- `metric_value`
- `metric_verdict`
- `baseline_claim_holds`
- `claim_stability_verdict`
- `claim_validation_outcome`
- `metric_ci_lower`
- `metric_ci_upper`
- `s_hat`
- `claim_ci_lower`
- `claim_ci_upper`
- `false_reassurance_type`

## Row Semantics

- `claim_id` format:
  - `{algorithm_family}|{claim_pair}|{scope}|delta={delta}`
- `metric_verdict`:
  - `positive`
  - `negative`
- `claim_stability_verdict`:
  - `stable`
  - `unstable`
  - `inconclusive`
- `claim_validation_outcome`:
  - `validated`
  - `refuted`
  - `unstable`
  - `inconclusive`
- `false_reassurance_type`:
  - `metric_positive_claim_refuted`
  - `metric_positive_claim_unstable`
  - `metric_positive_claim_inconclusive`
  - `none`

## Outputs

- Unified dataset:
  - `output/paper/icse_pack/derived/RQ1/metric_claim_comparison_dataset.csv`
  - `output/paper/icse_pack/derived/RQ1/metric_claim_comparison_dataset.json`
- Summary tables:
  - `output/paper/icse_pack/tables/tab_mismatch_summary.csv`
  - `output/paper/icse_pack/tables/tab_false_reassurance_breakdown.csv`
- Main-paper figure:
  - `output/paper/icse_pack/figures/main/fig1_metric_claim_discrepancy_matrix.png`
  - `output/paper/icse_pack/figures/main/fig1_metric_claim_discrepancy_matrix.pdf`
- Short interpretation note for RQ1:
  - `output/paper/icse_pack/derived/RQ1/metric_claim_interpretation.md`

## Canonical Figure Timing

The canonical main-paper figure for this task is generated only after:

- the row-level claim-variant dataset is frozen
- the overall mismatch counts are verified against source summaries
- the structural breakdown table is available for family / scope / delta checks

The canonical figure role is:

- `Fig 1` headline result for the full paper

Appendix figures may be generated earlier, but they do not satisfy the main-paper acceptance condition.

## Execution Steps

- [x] Freeze row schema and source scope.
- [x] Export unified metric-vs-claim dataset.
- [x] Generate mismatch and false-reassurance summary tables.
- [x] Generate Fig 1 discrepancy matrix.
- [x] Write short RQ1 interpretation note.

## Figure Definition

Fig 1 should be a paper-facing discrepancy matrix, not a case-study figure.

- Rows:
  - `metric_verdict` (`positive`, `negative`)
- Columns:
  - `claim_validation_outcome` (`validated`, `refuted`, `unstable`, `inconclusive`)
- Each cell should show:
  - count
  - share among all rows
- Visual emphasis must be placed on:
  - `metric = positive` and `claim != validated`

## Summary Table Definition

`tab_mismatch_summary.csv` must support at least these groupings:

- overall
- by `algorithm_family`
- by `scope`

Each row should include:

- `group`
- `n_total`
- `metric_positive`
- `claim_validated`
- `claim_refuted`
- `claim_unstable`
- `claim_inconclusive`
- `metric_positive_claim_refuted`
- `metric_positive_claim_unstable`
- `metric_positive_claim_inconclusive`
- `conditional_false_reassurance_rate`
- `support_alignment_rate`

## Acceptance Criteria

- [x] Every included paper-facing comparative claim variant is represented exactly once.
- [x] Every row is traceable to one of the frozen input sources.
- [x] The dataset can be grouped by family, scope, and delta without manual repair.
- [x] False-reassurance counts and rates are computed directly from the exported dataset.
- [x] The overall counts match the existing source summaries.
- [x] Fig 1 can be generated from the dataset without ad-hoc patching.
- [x] Fig 1 visually highlights `metric = positive` and `claim = unstable/inconclusive`.
- [x] The canonical headline figure is generated only after the dataset and summary tables are frozen.
- [x] The resulting figure and tables support direct citation in the RQ1 main-text subsection.

## Dependencies

- [00_OVERVIEW.md](./00_OVERVIEW.md)
- [01_REPO_CONVERGENCE.md](./01_REPO_CONVERGENCE.md)

## Status

- [ ] Not started
- [ ] In progress
- [x] Done

## Notes

This is the main experimental strike. If this task is weak, the paper is weak.

Implementation completed via:

- `../scripts/export_rq1_metric_vs_claim.py`
- `output/paper/icse_pack/derived/RQ1/metric_claim_comparison_dataset.csv`
- `output/paper/icse_pack/tables/tab_mismatch_summary.csv`
- `output/paper/icse_pack/tables/tab_false_reassurance_breakdown.csv`
- `output/paper/icse_pack/tables/tab_rq1_family_breakdown.csv`
- `output/paper/icse_pack/tables/tab_rq1_scope_breakdown.csv`
- `output/paper/icse_pack/tables/tab_rq1_delta_breakdown.csv`
- `output/paper/icse_pack/tables/tab_rq1_primary_family_sensitivity.csv`
- `output/paper/icse_pack/tables/tab_rq1_leave_one_family_out_sensitivity.csv`
- `output/paper/icse_pack/figures/main/fig1_metric_claim_discrepancy_matrix.png`
