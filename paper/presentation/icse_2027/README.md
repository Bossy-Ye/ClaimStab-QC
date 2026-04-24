# ICSE 2027 Submission Surface

This directory is the curated, paper-facing surface for the ICSE 2027 submission.

It is intentionally separate from:
- raw run outputs under `output/paper/...`
- derived experiment packs under `output/paper/evaluation_v2`, `evaluation_v3`, `evaluation_v4`
- exploratory scripts and intermediate artifacts

The purpose of this directory is to collect only the assets that are intended to
appear in the paper narrative:
- final figures
- final tables
- result notes
- definition boxes
- appendix-ready explanatory material

When wording conflicts exist, this directory wins over:

- backlog task files under `paper/experiments/backlog_icse_2027/`
- public-facing summary pages under `docs/results/`
- archived planning material under `paper/experiments/_archive_legacy/`

Venue-specific naming should remain confined to this subtree. Framework code,
historical specs, and generic script names should stay venue-neutral.

## Thesis

ClaimStab-QC is a claim-centric validation methodology for quantum software
experiments, showing that empirical evaluation often validates outcomes but not
conclusions.

## Scope

This surface should only contain curated evidence for the paper.

Do not place here:
- full run directories
- exploratory plots
- temporary tables
- duplicated historical bundles

## Directory layout

- `definitions/`
  - short paper-ready definitions for terms that must remain stable across the manuscript
- `notes/`
  - result notes and paragraph-ready interpretation fragments
- `figures/`
  - final figure assets selected for the submission
- `tables/`
  - final paper tables and appendix tables selected for the submission

Table inventory:
- [tables/README.md](tables/README.md)

Figure inventory:
- [figures/README.md](figures/README.md)

Definitions inventory:
- [definitions/README.md](definitions/README.md)

Notes inventory:
- [notes/README.md](notes/README.md)

## Current paper-facing assets

### RQ1: Metric vs Claim mismatch

Primary generated assets currently live in:
- [metric_claim_comparison_dataset.csv](../../../output/paper/icse_pack/derived/RQ1/metric_claim_comparison_dataset.csv)
- [tab_mismatch_summary.csv](../../../output/paper/icse_pack/tables/tab_mismatch_summary.csv)
- [tab1_rq1_structural_breakdown.csv](../../../output/paper/icse_pack/tables/tab1_rq1_structural_breakdown.csv)
- [tab_false_reassurance_breakdown.csv](../../../output/paper/icse_pack/tables/tab_false_reassurance_breakdown.csv)
- [tab_rq1_family_breakdown.csv](../../../output/paper/icse_pack/tables/tab_rq1_family_breakdown.csv)
- [tab_rq1_scope_breakdown.csv](../../../output/paper/icse_pack/tables/tab_rq1_scope_breakdown.csv)
- [tab_rq1_delta_breakdown.csv](../../../output/paper/icse_pack/tables/tab_rq1_delta_breakdown.csv)
- [tab_rq1_primary_family_sensitivity.csv](../../../output/paper/icse_pack/tables/tab_rq1_primary_family_sensitivity.csv)
- [tab_rq1_leave_one_family_out_sensitivity.csv](../../../output/paper/icse_pack/tables/tab_rq1_leave_one_family_out_sensitivity.csv)
- [fig1_metric_claim_discrepancy_matrix.png](../../../output/paper/icse_pack/figures/main/fig1_metric_claim_discrepancy_matrix.png)
- [metric_claim_interpretation.md](../../../output/paper/icse_pack/derived/RQ1/metric_claim_interpretation.md)

Curated paper-facing notes:
- [rq1_metric_claim_note.md](notes/rq1_metric_claim_note.md)
- [rq1_breakdowns_note.md](notes/rq1_breakdowns_note.md)
- [rq1_results_prose.md](notes/rq1_results_prose.md)

### RQ1: Baseline comparison

Primary generated assets currently live in:
- [baseline_comparison_dataset.csv](../../../output/paper/icse_pack/derived/RQ1/baseline_comparison_dataset.csv)
- [tab2_baseline_capability_matrix.csv](../../../output/paper/icse_pack/tables/tab2_baseline_capability_matrix.csv)
- [tab_baseline_disagreement_summary.csv](../../../output/paper/icse_pack/tables/tab_baseline_disagreement_summary.csv)
- [fig2_validated_vs_false_reassurance.png](../../../output/paper/icse_pack/figures/main/fig2_validated_vs_false_reassurance.png)
- [baseline_comparison_interpretation.md](../../../output/paper/icse_pack/derived/RQ1/baseline_comparison_interpretation.md)

Curated paper-facing note:
- [rq1_baseline_comparison_note.md](notes/rq1_baseline_comparison_note.md)

### RQ3: Scope robustness

Primary generated assets currently live in:
- [scope_transport_dataset.csv](../../../output/paper/icse_pack/derived/RQ3/scope_transport_dataset.csv)
- [tab_rq3_scope_transport_summary.csv](../../../output/paper/icse_pack/tables/tab_rq3_scope_transport_summary.csv)
- [fig4_scope_transport_map.png](../../../output/paper/icse_pack/figures/main/fig4_scope_transport_map.png)
- [scope_transport_interpretation.md](../../../output/paper/icse_pack/derived/RQ3/scope_transport_interpretation.md)

Curated paper-facing note:
- [rq3_scope_robustness_note.md](notes/rq3_scope_robustness_note.md)

### RQ3: Exact witnesses

Primary generated assets currently live in:
- [exact_witness_dataset.csv](../../../output/paper/icse_pack/derived/RQ3/exact_witness_dataset.csv)
- [tab_rq3_exact_approx_status.csv](../../../output/paper/icse_pack/tables/tab_rq3_exact_approx_status.csv)
- [tab3_exact_witness_examples.csv](../../../output/paper/icse_pack/tables/tab3_exact_witness_examples.csv)
- [fig3_exact_witness_sizes.png](../../../output/paper/icse_pack/figures/main/fig3_exact_witness_sizes.png)
- [exact_witness_interpretation.md](../../../output/paper/icse_pack/derived/RQ3/exact_witness_interpretation.md)

Curated paper-facing note:
- [rq3_exact_witness_note.md](notes/rq3_exact_witness_note.md)

### RQ4: Practicality and cost

Primary generated assets currently live in:
- [practicality_tradeoff_dataset.csv](../../../output/paper/icse_pack/derived/RQ4/practicality_tradeoff_dataset.csv)
- [tab4_rq4_practicality_summary.csv](../../../output/paper/icse_pack/tables/tab4_rq4_practicality_summary.csv)
- [fig4_cost_configuration_tradeoff.png](../../../output/paper/icse_pack/figures/main/fig4_cost_configuration_tradeoff.png)
- [practicality_interpretation.md](../../../output/paper/icse_pack/derived/RQ4/practicality_interpretation.md)

Curated paper-facing note:
- [rq4_practicality_note.md](notes/rq4_practicality_note.md)

### RQ2: Cross-family heterogeneity

Primary generated assets currently live in:
- [cross_family_dataset.csv](../../../output/paper/icse_pack/derived/RQ2/cross_family_dataset.csv)
- [tab_rq2_cross_family_summary.csv](../../../output/paper/icse_pack/tables/tab_rq2_cross_family_summary.csv)
- [fig5_cross_family_outcomes.png](../../../output/paper/icse_pack/figures/main/fig5_cross_family_outcomes.png)
- [cross_family_interpretation.md](../../../output/paper/icse_pack/derived/RQ2/cross_family_interpretation.md)

Curated paper-facing note:
- [rq2_semantic_discrimination_note.md](notes/rq2_semantic_discrimination_note.md)

### Hamiltonian correctness audit

Current audit material lives in:
- [audit_report.md](../../experiments/audits/hamiltonian_correctness/audit_report.md)

Curated paper-facing note:
- [hamiltonian_correctness_note.md](notes/hamiltonian_correctness_note.md)

## Status

- `RQ1` curated surface: active
- `RQ1 baseline comparison`: active
- `RQ2` curated surface: active
- `RQ3` curated surface: active
- `RQ4` curated surface: active

## Curation rule

An asset belongs here only if:
1. it is intended to appear in the paper or appendix,
2. it has stable semantics,
3. it is backed by a reproducible source path,
4. it has a short note explaining how it should be read.
