# Main Paper Tables

This file is the canonical table shortlist for the ICSE 2027 main paper.

## Table inventory

### Tab 1. Metric-Claim Mismatch Summary

Purpose:
- primary `RQ1` summary table
- reports the main mismatch counts behind the `metric vs claim` result

Generated source:
- [tab_mismatch_summary.csv](/Users/mac/Documents/GitHub/ClaimStab-QC/output/paper/icse_pack/tables/tab_mismatch_summary.csv)

Expected paper role:
- summarize overall mismatch
- report family-level mismatch
- report scope-level mismatch

Current status:
- `ready as source`
- `needs final paper formatting`

Recommended columns:
- `group_kind`
- `group`
- `n_total`
- `metric_positive`
- `claim_validated`
- `claim_refuted`
- `claim_unstable`
- `claim_inconclusive`
- `conditional_false_reassurance_rate`

### Tab 2. Baseline Capability Matrix

Purpose:
- `RQ1` / `RQ2` bridge table
- shows why conventional baselines do not substitute claim-level validation

Generated source:
- pending from `03_E2_BASELINE_COMPARISON`

Expected paper role:
- compare:
  - mean + CI
  - repeated runs
  - local sensitivity analysis
  - support-ratio style baseline
  - ClaimStab-QC

Current status:
- `pending`

### Tab 3. Exact Witness Examples

Purpose:
- `RQ3` explanatory adequacy table
- shows exact minimal overturn sets for representative claims

Generated source:
- pending final curation from `E4 exact MOS`
- current supporting source:
  - [tab_c_exact_vs_greedy_mos.csv](/Users/mac/Documents/GitHub/ClaimStab-QC/output/paper/evaluation_v4/pack/tables/tab_c_exact_vs_greedy_mos.csv)

Expected paper role:
- give 3-5 representative exact witness examples
- show that failure can be explained by compact sufficient subsets

Current status:
- `partially ready`

### Tab 4. Cost / Policy Summary

Purpose:
- `RQ4` practicality table
- summarizes the cost-efficiency tradeoff across policy choices

Generated source candidates:
- [e5_policy_summary.csv](/Users/mac/Documents/GitHub/ClaimStab-QC/output/paper/evaluation_v2/derived_paper_evaluation/RQ4_practicality/e5_policy_summary.csv)
- [w5_policy_by_strategy.csv](/Users/mac/Documents/GitHub/ClaimStab-QC/output/paper/evaluation_v3/derived_paper_evaluation/RQ4_practicality/w5_policy_by_strategy.csv)

Expected paper role:
- support the main cost/configuration tradeoff figure
- state the clear-case vs near-boundary cost gap

Current status:
- `source data ready`
- `final table design pending`

## Current recommendation

If the paper needs to stay lean, keep only:
- `Tab 1` in the main paper
- move `Tab 2` or `Tab 4` to appendix if space becomes tight

`Tab 1` is the least negotiable main-paper table.
