# RQ2 Note: Semantic Discrimination

`RQ2` exists to show that ClaimStab-QC is not a trivial instability detector and
not merely a thin wrapper around generic sensitivity analysis.

Primary generated sources:
- [cross_family_dataset.csv](/Users/mac/Documents/GitHub/ClaimStab-QC/output/paper/icse_pack/derived/RQ2/cross_family_dataset.csv)
- [tab_rq2_cross_family_summary.csv](/Users/mac/Documents/GitHub/ClaimStab-QC/output/paper/icse_pack/tables/tab_rq2_cross_family_summary.csv)
- [fig5_cross_family_outcomes.png](/Users/mac/Documents/GitHub/ClaimStab-QC/output/paper/icse_pack/figures/main/fig5_cross_family_outcomes.png)

## Main reading

This note covers comparative / ranking claims only.

The outcome distribution is heterogeneous across algorithm families:
- `MaxCut QAOA` is dominated by unstable comparative claims
- `Max-2-SAT QAOA` is mixed, with many validated and some unstable / inconclusive claims
- `VQE/H2` is mostly refuted rather than unstable

This heterogeneity matters because it shows that:
- the framework does not simply classify everything as unstable
- claim-level validation behaves differently across populations
- the main `RQ1` mismatch phenomenon is structural but population-dependent

## Safe paper-facing takeaway

The method is semantically discriminative across comparative claim populations
rather than uniformly pessimistic. Hardware / execution-family expansion remains
outside the current `06` scope.
