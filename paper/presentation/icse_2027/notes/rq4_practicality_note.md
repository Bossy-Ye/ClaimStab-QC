# RQ4 Note: Practicality and Cost

`RQ4` asks whether the method is operationally usable, not whether it is always cheap.

Primary generated sources:
- [practicality_tradeoff_dataset.csv](/Users/mac/Documents/GitHub/ClaimStab-QC/output/paper/icse_pack/derived/RQ4/practicality_tradeoff_dataset.csv)
- [tab4_rq4_practicality_summary.csv](/Users/mac/Documents/GitHub/ClaimStab-QC/output/paper/icse_pack/tables/tab4_rq4_practicality_summary.csv)
- [fig4_cost_configuration_tradeoff.png](/Users/mac/Documents/GitHub/ClaimStab-QC/output/paper/icse_pack/figures/main/fig4_cost_configuration_tradeoff.png)

## Main reading

The current pattern is:
- all current strategies preserve full-factorial decisions in the current clear-case and boundary-case packs
- adaptive strategies save substantial effort on clear cases
- near-boundary claims remain more expensive even when decision agreement is preserved

This should be framed as:
- a conservative decision-theoretic tradeoff
- not a failure of the method

## Safe paper-facing takeaway

Claim-level validation is practical for many clear cases, but difficult
boundary cases still require more evidence. This is expected behavior for a
conservative validation method.
