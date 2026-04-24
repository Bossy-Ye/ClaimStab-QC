# Main Paper Figures

This file is the canonical shortlist of main-paper figures for the ICSE 2027 submission.

## Figure inventory

### Fig 1. Validated vs False Reassurance Among Baseline-Supportive Variants

Purpose:
- `RQ1` strengthening figure
- partitions the same `63` claim variants for each method into normalized claim-level outcomes
- keeps the `RQ1` baseline comparison count-based, but shows the full denominator rather than only supportive subsets

Generated source:
- [fig2_validated_vs_false_reassurance.png](../../../../output/paper/icse_pack/figures/main/fig2_validated_vs_false_reassurance.png)
- [fig2_validated_vs_false_reassurance.pdf](../../../../output/paper/icse_pack/figures/main/fig2_validated_vs_false_reassurance.pdf)

Expected paper role:
- block the reviewer objection that `RQ1` only defeats one frozen metric baseline
- compare baseline-supportive verdicts against claim-level validation outcomes on identical claim units in a direct count-based view
- show supportive error mass without hiding the non-supportive remainder

Current status:
- `ready as source`
- `main-paper use recommended`

### Fig 2. Comparative-Claim Outcomes Across Families and Mismatch Kinds

Purpose:
- primary `RQ2` figure
- shows that the outcome mix is family-dependent rather than uniformly pessimistic
- makes the MaxCut / Max-2-SAT / VQE split visually obvious in one view
- pairs the workload-family panel with the frozen mismatch-kind counts used in the paper text

Generated source:
- [fig5_cross_family_outcomes.png](../../../../output/paper/icse_pack/figures/main/fig5_cross_family_outcomes.png)
- [fig5_cross_family_outcomes.pdf](../../../../output/paper/icse_pack/figures/main/fig5_cross_family_outcomes.pdf)

Expected paper role:
- anchor `RQ2` visually
- show that instability, validation, and refutation cluster differently across workload families
- keep the false-confidence / refutation / near-threshold pattern counts visible without promoting a second figure

Current status:
- `ready as source`
- `main-paper use recommended`

### Fig 3. Scope Transport Across Representative Claims

Purpose:
- primary `RQ3` figure
- shows how representative claims behave as admissible scope broadens
- distinguishes robust stable, robust unstable, and boundary-sensitive behavior with observed Wilson intervals

Generated source:
- [fig4_scope_transport_map.png](../../../../output/paper/icse_pack/figures/main/fig4_scope_transport_map.png)
- [fig4_scope_transport_map.pdf](../../../../output/paper/icse_pack/figures/main/fig4_scope_transport_map.pdf)

Expected paper role:
- make `RQ3` explanatory rather than purely categorical
- show directly that scope changes matter most at the boundary, not uniformly

Current status:
- `ready as source`
- `main-paper use recommended`

### Fig 4. Cost / Configuration Tradeoff

Purpose:
- primary `RQ4` figure
- summarizes cost asymmetry under clear cases and near-boundary cases

Generated source:
- [fig4_cost_configuration_tradeoff.png](../../../../output/paper/icse_pack/figures/main/fig4_cost_configuration_tradeoff.png)
- [fig4_cost_configuration_tradeoff.pdf](../../../../output/paper/icse_pack/figures/main/fig4_cost_configuration_tradeoff.pdf)

Expected paper role:
- show that adaptive strategies help in clear cases
- show that boundary cases remain more expensive

Current status:
- `ready as source`
- `main-paper use recommended`

## Recommendation

If the paper must stay compact, keep these four figures as the main-paper core:
- `Fig 1`
- `Fig 2`
- `Fig 3`
- `Fig 4`

`Fig 1` and `Fig 2` are the least negotiable figures in the manuscript.
