# 03 E2 Baseline Comparison

## Goal

Show that common evaluation strategies cannot substitute claim-level validation.

## Baselines

At minimum compare:

- mean + confidence interval
- repeated runs
- local sensitivity analysis
- simple support-ratio / robustness heuristic
- ClaimStab verdict

## Inputs

- unified metric-vs-claim dataset
- existing `W3` analyses and sensitivity outputs

## Outputs

- baseline capability matrix
- disagreement comparison table
- one comparison figure or compact visual summary

## Acceptance Criteria

- [ ] At least four non-ClaimStab baselines are represented.
- [ ] Baseline outputs are comparable on the same claim instances.
- [ ] The resulting table/figure makes clear that the baselines do not replace claim validation.
- [ ] Capability dimensions are explicit, not narrative only.

## Dependencies

- [02_E1_METRIC_VS_CLAIM.md](./02_E1_METRIC_VS_CLAIM.md)

## Status

- [ ] Not started
- [ ] In progress
- [ ] Done

## Notes

This task is primarily to block the “your baseline is too weak” reviewer attack.
