# Main Paper Figures

This file is the canonical shortlist of main-paper figures for the ICSE 2027 submission.

## Figure inventory

### Fig 1. Metric-Claim Discrepancy Matrix

Purpose:
- primary `RQ1` figure
- operationalizes the central mismatch claim:
  - metric support does not imply claim validation

Generated source:
- [fig1_metric_claim_discrepancy_matrix.png](/Users/mac/Documents/GitHub/ClaimStab-QC/output/paper/icse_pack/figures/main/fig1_metric_claim_discrepancy_matrix.png)
- [fig1_metric_claim_discrepancy_matrix.pdf](/Users/mac/Documents/GitHub/ClaimStab-QC/output/paper/icse_pack/figures/main/fig1_metric_claim_discrepancy_matrix.pdf)

Expected paper role:
- main `RQ1` anchor figure
- highlighted cells:
  - `metric positive + unstable`
  - `metric positive + inconclusive`
  - `metric positive + refuted` if any appear in future revisions

Current status:
- `ready as source`
- `main-paper priority = highest`

### Fig 2. Cross-Family Verdict Distribution

Purpose:
- primary `RQ2` figure
- shows that claim behavior differs across algorithm/task families

Generated source:
- [fig_a_cross_family_verdicts.png](/Users/mac/Documents/GitHub/ClaimStab-QC/output/paper/evaluation_v4/pack/figures/main/fig_a_cross_family_verdicts.png)
- [fig_a_cross_family_verdicts.pdf](/Users/mac/Documents/GitHub/ClaimStab-QC/output/paper/evaluation_v4/pack/figures/main/fig_a_cross_family_verdicts.pdf)

Expected paper role:
- support semantic discrimination
- keep the story population-dependent rather than universal

Current status:
- `ready as source`
- `needs final caption and paper numbering`

### Fig 3. Scope Robustness / Protocol Sensitivity

Purpose:
- primary `RQ3` figure
- shows whether verdicts transport under nearby admissibility/protocol choices

Generated source:
- [fig_b_scope_robustness.png](/Users/mac/Documents/GitHub/ClaimStab-QC/output/paper/evaluation_v4/pack/figures/main/fig_b_scope_robustness.png)

Expected paper role:
- support the claim that admissible scope must be explicit
- distinguish robustly stable / robustly unstable / boundary-sensitive behavior

Current status:
- `ready as source`
- `paper-facing wording needs final tightening`

### Fig 4. Cost / Configuration Tradeoff

Purpose:
- primary `RQ4` figure
- summarizes cost-efficiency under clear cases and near-boundary cases

Generated source candidate:
- [fig_w5_near_boundary_tradeoff.png](/Users/mac/Documents/GitHub/ClaimStab-QC/output/paper/evaluation_v3/pack/figures/main/fig_w5_near_boundary_tradeoff.png)

Expected paper role:
- show that adaptive strategies help in clear cases
- show that boundary cases remain more expensive

Current status:
- `source data and candidate figure ready`
- `final ICSE-style unified version pending`

## Recommendation

If the paper must stay compact, keep these four figures as the main-paper core:
- `Fig 1`
- `Fig 2`
- `Fig 3`
- `Fig 4`

`Fig 1` is the least negotiable figure in the manuscript.
