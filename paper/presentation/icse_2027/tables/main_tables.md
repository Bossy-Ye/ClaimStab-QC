# Main Paper Tables

This file is the canonical table shortlist for the ICSE 2027 main paper.

## Table inventory

### Tab 1. Metric-Claim Mismatch Summary

Purpose:
- primary `RQ1` summary table
- reports the main mismatch counts behind the `metric vs claim` result

Generated source:
- [tab1_rq1_structural_breakdown.csv](../../../../output/paper/icse_pack/tables/tab1_rq1_structural_breakdown.csv)

Expected paper role:
- summarize the headline mismatch and its key structural breakdowns in one compact table
- report overall, family, scope, and delta structure without pushing detailed tables into the main text

Current status:
- `ready as source`
- `needs final paper formatting`

Structured supporting sources:
- [tab_mismatch_summary.csv](../../../../output/paper/icse_pack/tables/tab_mismatch_summary.csv)
- [tab_rq1_family_breakdown.csv](../../../../output/paper/icse_pack/tables/tab_rq1_family_breakdown.csv)
- [tab_rq1_scope_breakdown.csv](../../../../output/paper/icse_pack/tables/tab_rq1_scope_breakdown.csv)
- [tab_rq1_delta_breakdown.csv](../../../../output/paper/icse_pack/tables/tab_rq1_delta_breakdown.csv)

Recommended columns:
- `dimension`
- `slice`
- `metric_positive`
- `false_reassurance`
- `conditional_false_reassurance_rate`

### Tab 2. Baseline Capability Matrix

Purpose:
- `RQ1` / `RQ2` bridge table
- shows why conventional baselines do not substitute claim-level validation

Generated source:
- [tab2_baseline_capability_matrix.csv](../../../../output/paper/icse_pack/tables/tab2_baseline_capability_matrix.csv)

Structured supporting source:
- [tab_baseline_disagreement_summary.csv](../../../../output/paper/icse_pack/tables/tab_baseline_disagreement_summary.csv)

Expected paper role:
- compare:
  - mean + CI
  - repeated runs
  - local sensitivity analysis
  - support-ratio style baseline
  - ClaimStab-QC

Current status:
- `ready as source`
- `main-paper use recommended together with Fig 2`

### Tab 3. Exact Witness Examples

Purpose:
- `RQ3` explanatory adequacy table
- shows exact minimal overturn sets for representative claims

Generated source:
- [tab3_exact_witness_examples.csv](../../../../output/paper/icse_pack/tables/tab3_exact_witness_examples.csv)

Expected paper role:
- give 3-5 representative exact witness examples
- show that failure can be explained by compact sufficient subsets

Current status:
- `ready as source`

### Tab A-RQ3. Scope Transport Summary

Purpose:
- compact appendix-facing table for `RQ3`
- summarizes which representative cases are robustly stable, robustly unstable, or boundary-sensitive

Generated source:
- [tab_rq3_scope_transport_summary.csv](../../../../output/paper/icse_pack/tables/tab_rq3_scope_transport_summary.csv)

Expected paper role:
- support the scope-transport figure with a compact textual summary
- keep the main text focused while preserving explicit case taxonomy

Current status:
- `ready as source`

### Tab A-RQ3b. Exact vs Approximate Status

Purpose:
- appendix-facing support table for `RQ3`
- states which paper-facing runs use exact subset search and how often exact witnesses are found

Generated source:
- [tab_rq3_exact_approx_status.csv](../../../../output/paper/icse_pack/tables/tab_rq3_exact_approx_status.csv)

Expected paper role:
- make exact-default status explicit for tractable paper-facing spaces
- keep approximate legacy diagnostics clearly out of the canonical main-paper evidence

Current status:
- `ready as source`

### Tab 4. Cost / Policy Summary

Purpose:
- `RQ4` practicality table
- summarizes the cost-efficiency tradeoff across policy choices

Generated source:
- [tab4_rq4_practicality_summary.csv](../../../../output/paper/icse_pack/tables/tab4_rq4_practicality_summary.csv)

Expected paper role:
- support the main cost/configuration tradeoff figure
- state the clear-case vs near-boundary cost gap

Current status:
- `ready as source`
- `appendix placement recommended if main-paper space becomes tight`

## Current recommendation

If the paper needs to stay lean, keep only:
- `Tab 1` in the main paper
- keep `Tab 2` only if the baseline-comparison argument needs explicit capability dimensions
- move `Tab 4` to appendix if space becomes tight

`Tab 1` is the least negotiable main-paper table.
