# ICSE 2027 Presentation Surface

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
- [tables/README.md](/Users/mac/Documents/GitHub/ClaimStab-QC/paper/presentation/icse_2027/tables/README.md)

Figure inventory:
- [figures/README.md](/Users/mac/Documents/GitHub/ClaimStab-QC/paper/presentation/icse_2027/figures/README.md)

Definitions inventory:
- [definitions/README.md](/Users/mac/Documents/GitHub/ClaimStab-QC/paper/presentation/icse_2027/definitions/README.md)

Notes inventory:
- [notes/README.md](/Users/mac/Documents/GitHub/ClaimStab-QC/paper/presentation/icse_2027/notes/README.md)

## Current paper-facing assets

### RQ1: Metric vs Claim mismatch

Primary generated assets currently live in:
- [metric_claim_comparison_dataset.csv](/Users/mac/Documents/GitHub/ClaimStab-QC/output/paper/icse_pack/derived/RQ1/metric_claim_comparison_dataset.csv)
- [tab_mismatch_summary.csv](/Users/mac/Documents/GitHub/ClaimStab-QC/output/paper/icse_pack/tables/tab_mismatch_summary.csv)
- [tab1_rq1_structural_breakdown.csv](/Users/mac/Documents/GitHub/ClaimStab-QC/output/paper/icse_pack/tables/tab1_rq1_structural_breakdown.csv)
- [tab_false_reassurance_breakdown.csv](/Users/mac/Documents/GitHub/ClaimStab-QC/output/paper/icse_pack/tables/tab_false_reassurance_breakdown.csv)
- [tab_rq1_family_breakdown.csv](/Users/mac/Documents/GitHub/ClaimStab-QC/output/paper/icse_pack/tables/tab_rq1_family_breakdown.csv)
- [tab_rq1_scope_breakdown.csv](/Users/mac/Documents/GitHub/ClaimStab-QC/output/paper/icse_pack/tables/tab_rq1_scope_breakdown.csv)
- [tab_rq1_delta_breakdown.csv](/Users/mac/Documents/GitHub/ClaimStab-QC/output/paper/icse_pack/tables/tab_rq1_delta_breakdown.csv)
- [tab_rq1_primary_family_sensitivity.csv](/Users/mac/Documents/GitHub/ClaimStab-QC/output/paper/icse_pack/tables/tab_rq1_primary_family_sensitivity.csv)
- [tab_rq1_leave_one_family_out_sensitivity.csv](/Users/mac/Documents/GitHub/ClaimStab-QC/output/paper/icse_pack/tables/tab_rq1_leave_one_family_out_sensitivity.csv)
- [fig1_metric_positive_validation_bar.png](/Users/mac/Documents/GitHub/ClaimStab-QC/output/paper/icse_pack/figures/main/fig1_metric_positive_validation_bar.png)
- [fig1_metric_claim_discrepancy_matrix.png](/Users/mac/Documents/GitHub/ClaimStab-QC/output/paper/icse_pack/figures/main/fig1_metric_claim_discrepancy_matrix.png)
- [metric_claim_interpretation.md](/Users/mac/Documents/GitHub/ClaimStab-QC/output/paper/icse_pack/derived/RQ1/metric_claim_interpretation.md)

Curated paper-facing notes:
- [rq1_metric_claim_note.md](/Users/mac/Documents/GitHub/ClaimStab-QC/paper/presentation/icse_2027/notes/rq1_metric_claim_note.md)
- [rq1_breakdowns_note.md](/Users/mac/Documents/GitHub/ClaimStab-QC/paper/presentation/icse_2027/notes/rq1_breakdowns_note.md)
- [rq1_results_prose.md](/Users/mac/Documents/GitHub/ClaimStab-QC/paper/presentation/icse_2027/notes/rq1_results_prose.md)

### RQ1: Baseline comparison

Primary generated assets currently live in:
- [baseline_comparison_dataset.csv](/Users/mac/Documents/GitHub/ClaimStab-QC/output/paper/icse_pack/derived/RQ1/baseline_comparison_dataset.csv)
- [tab2_baseline_capability_matrix.csv](/Users/mac/Documents/GitHub/ClaimStab-QC/output/paper/icse_pack/tables/tab2_baseline_capability_matrix.csv)
- [tab_baseline_disagreement_summary.csv](/Users/mac/Documents/GitHub/ClaimStab-QC/output/paper/icse_pack/tables/tab_baseline_disagreement_summary.csv)
- [fig2_validated_vs_false_reassurance.png](/Users/mac/Documents/GitHub/ClaimStab-QC/output/paper/icse_pack/figures/main/fig2_validated_vs_false_reassurance.png)
- [baseline_comparison_interpretation.md](/Users/mac/Documents/GitHub/ClaimStab-QC/output/paper/icse_pack/derived/RQ1/baseline_comparison_interpretation.md)

Curated paper-facing note:
- [rq1_baseline_comparison_note.md](/Users/mac/Documents/GitHub/ClaimStab-QC/paper/presentation/icse_2027/notes/rq1_baseline_comparison_note.md)

### Hamiltonian correctness audit

Current audit material lives in:
- [audit_report.md](/Users/mac/Documents/GitHub/ClaimStab-QC/paper/experiments/audits/hamiltonian_correctness/audit_report.md)

Curated paper-facing note:
- [hamiltonian_correctness_note.md](/Users/mac/Documents/GitHub/ClaimStab-QC/paper/presentation/icse_2027/notes/hamiltonian_correctness_note.md)

## Status

- `RQ1` curated surface: active
- `RQ1 baseline comparison`: active
- `RQ2` curated surface: pending
- `RQ3` curated surface: pending
- `RQ4` curated surface: pending

## Curation rule

An asset belongs here only if:
1. it is intended to appear in the paper or appendix,
2. it has stable semantics,
3. it is backed by a reproducible source path,
4. it has a short note explaining how it should be read.
