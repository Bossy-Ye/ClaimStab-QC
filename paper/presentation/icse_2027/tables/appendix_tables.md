# Appendix Tables

This file tracks the table inventory that is likely better placed in the
appendix or supplementary material.

## Table inventory

### Tab A1. Family-Scope-Delta False-Reassurance Breakdown

Purpose:
- full structured `RQ1` breakdown
- supports the claim that mismatch is not a single-number artifact

Generated source:
- [tab_false_reassurance_breakdown.csv](/Users/mac/Documents/GitHub/ClaimStab-QC/output/paper/icse_pack/tables/tab_false_reassurance_breakdown.csv)
- Curated companion sources:
  - [tab_rq1_family_breakdown.csv](/Users/mac/Documents/GitHub/ClaimStab-QC/output/paper/icse_pack/tables/tab_rq1_family_breakdown.csv)
  - [tab_rq1_scope_breakdown.csv](/Users/mac/Documents/GitHub/ClaimStab-QC/output/paper/icse_pack/tables/tab_rq1_scope_breakdown.csv)
  - [tab_rq1_delta_breakdown.csv](/Users/mac/Documents/GitHub/ClaimStab-QC/output/paper/icse_pack/tables/tab_rq1_delta_breakdown.csv)

Current status:
- `ready as source`
- `family/scope/delta curated tables now available`

### Tab A2. Analysis Unit Clarification

Purpose:
- clarify the difference between:
  - claim variants
  - configuration cells

Canonical note:
- [analysis_units.md](/Users/mac/Documents/GitHub/ClaimStab-QC/paper/presentation/icse_2027/definitions/analysis_units.md)

Expected content:
- `63` comparative claim variants
- `1719` aggregated variant-scope-configuration cells

Current status:
- `ready conceptually`
- `not yet rendered as a formal appendix table`

### Tab A3. Exact vs Approximate MOS Status

Purpose:
- document which experiments use exact MOS and which retain approximate fallback

Generated source:
- [tab_rq3_exact_approx_status.csv](/Users/mac/Documents/GitHub/ClaimStab-QC/output/paper/icse_pack/tables/tab_rq3_exact_approx_status.csv)
- supporting legacy comparison source:
  - [tab_c_exact_vs_greedy_mos.csv](/Users/mac/Documents/GitHub/ClaimStab-QC/output/paper/evaluation_v4/pack/tables/tab_c_exact_vs_greedy_mos.csv)

Current status:
- `ready as source`
- `appendix placement recommended`

### Tab A4. Hamiltonian Correctness Audit Summary

Purpose:
- summarize family-level correctness classification
- make evidence grading explicit

Canonical source:
- [audit_report.md](/Users/mac/Documents/GitHub/ClaimStab-QC/paper/experiments/audits/hamiltonian_correctness/audit_report.md)

Expected rows:
- MaxCut
- Max-2-SAT
- VQE/H2

Expected columns:
- family
- classification
- evidence type
- local code reference
- sanity result

Current status:
- `ready conceptually`
- `table rendering pending`

### Tab A5. Primary-Family-Only and Leave-One-Family-Out Sensitivity

Purpose:
- show that the main `RQ1` conclusion does not depend on the weakest family

Generated source:
- [tab_rq1_primary_family_sensitivity.csv](/Users/mac/Documents/GitHub/ClaimStab-QC/output/paper/icse_pack/tables/tab_rq1_primary_family_sensitivity.csv)
- [tab_rq1_leave_one_family_out_sensitivity.csv](/Users/mac/Documents/GitHub/ClaimStab-QC/output/paper/icse_pack/tables/tab_rq1_leave_one_family_out_sensitivity.csv)

Current status:
- `ready as source`
- `appendix placement recommended`

### Tab A6. Baseline Disagreement Summary

Purpose:
- detailed appendix support for the `RQ1` baseline-comparison figure
- provides exact counts behind the main-paper comparison plot

Generated source:
- [tab_baseline_disagreement_summary.csv](/Users/mac/Documents/GitHub/ClaimStab-QC/output/paper/icse_pack/tables/tab_baseline_disagreement_summary.csv)

Current status:
- `ready as source`
- `appendix placement recommended if main paper keeps only the capability matrix`

### Tab A7. Scope Transport Summary

Purpose:
- appendix support for `RQ3`
- records the explicit case taxonomy behind the scope-transport figure

Generated source:
- [tab_rq3_scope_transport_summary.csv](/Users/mac/Documents/GitHub/ClaimStab-QC/output/paper/icse_pack/tables/tab_rq3_scope_transport_summary.csv)

Current status:
- `ready as source`
- `appendix placement recommended`

### Tab A8. Cross-Family Outcome Summary

Purpose:
- appendix support for `RQ2`
- records the comparative-claim outcome mix across algorithm families

Generated source:
- [tab_rq2_cross_family_summary.csv](/Users/mac/Documents/GitHub/ClaimStab-QC/output/paper/icse_pack/tables/tab_rq2_cross_family_summary.csv)

Current status:
- `ready as source`
- `appendix placement recommended`

## Recommendation

Appendix should definitely include:
- `Tab A1`
- `Tab A3`
- `Tab A4`

`Tab A5`, `Tab A6`, and `Tab A7` are valuable but optional if time becomes tight.
