# RQ2 Note: Semantic Discrimination

`RQ2` exists to show that ClaimStab-QC is not a trivial instability detector and
not merely a thin wrapper around generic sensitivity analysis.

Primary generated sources:
- [fig_a_cross_family_verdicts.png](/Users/mac/Documents/GitHub/ClaimStab-QC/output/paper/evaluation_v4/pack/figures/main/fig_a_cross_family_verdicts.png)
- [tab_a_cross_family_false_reassurance.csv](/Users/mac/Documents/GitHub/ClaimStab-QC/output/paper/evaluation_v4/pack/tables/tab_a_cross_family_false_reassurance.csv)

## Main reading

The verdict distribution is heterogeneous across families:
- `MaxCut QAOA` is dominated by unstable comparative claims
- `Max-2-SAT QAOA` is mixed, with many validated and some unstable claims
- `VQE/H2` is mostly stable on the ClaimStab decision layer, but often stably refuted on the baseline claim truth layer

This heterogeneity matters because it shows that:
- the framework does not simply classify everything as unstable
- claim-level validation behaves differently across populations
- the main `RQ1` mismatch phenomenon is structural but population-dependent

## Safe paper-facing takeaway

The method is semantically discriminative across claim populations rather than
uniformly pessimistic.
