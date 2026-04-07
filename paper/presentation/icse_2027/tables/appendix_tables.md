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

Current status:
- `ready as source`
- `needs curated appendix formatting`

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
- pending

Current status:
- `not started`

## Recommendation

Appendix should definitely include:
- `Tab A1`
- `Tab A3`
- `Tab A4`

`Tab A5` is valuable but optional if time becomes tight.
