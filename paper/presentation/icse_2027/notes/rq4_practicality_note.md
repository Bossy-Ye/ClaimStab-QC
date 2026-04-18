# RQ4 Note: Practicality and Cost

`RQ4` asks whether the method is operationally usable, not whether it is always cheap.

Primary generated sources:
- [practicality_tradeoff_dataset.csv](../../../../output/paper/icse_pack/derived/RQ4/practicality_tradeoff_dataset.csv)
- [tab4_rq4_practicality_summary.csv](../../../../output/paper/icse_pack/tables/tab4_rq4_practicality_summary.csv)
- [fig4_cost_configuration_tradeoff.png](../../../../output/paper/icse_pack/figures/main/fig4_cost_configuration_tradeoff.png)

## Main reading

The current pattern is:
- all current strategies preserve full-factorial decisions in the current clear-case and boundary-case packs
- adaptive strategies save substantial effort on clear cases
- near-boundary claims remain more expensive even when decision agreement is preserved

Important scope limit:
- this is a same-agreement, different-cost comparison
- it should not be described as a general cost-accuracy frontier
- the current `RQ4` evidence is limited to the clear-case `E5` pack and the near-boundary `W5` pack

This should be framed as:
- a conservative decision-theoretic tradeoff
- not a failure of the method

## Safe paper-facing takeaway

Claim-level validation is practical for many clear cases, but difficult
boundary cases still require more evidence. This is expected behavior for a
conservative validation method. The current evidence shows an operational
budget gap under matched agreement, not a universal cost-accuracy law.
