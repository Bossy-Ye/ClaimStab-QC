# 04 E3 Scope Robustness

## Goal

Demonstrate that verdicts are evaluated relative to explicit admissibility choices, and characterize when verdicts are robust versus protocol-sensitive.

## Inputs

- existing scope-robustness source:
  - `output/paper/evaluation_v4/derived_paper_evaluation/RQ2_semantics/scope_robustness.csv`
- selected representative archetypes:
  - one clear-stable case
  - one clear-unstable case
  - one near-boundary case
- paper-facing presentation surface under:
  - `paper/presentation/icse_2027/`

## Outputs

- `output/paper/icse_pack/derived/RQ3/scope_transport_dataset.csv`
- `output/paper/icse_pack/tables/tab_rq3_scope_transport_summary.csv`
- `output/paper/icse_pack/figures/main/fig4_scope_transport_map.png`
- short interpretation note
- explicit transport taxonomy:
  - `robustly stable`
  - `robustly unstable`
  - `boundary-sensitive`

## Canonical Figure Timing

The canonical figure for this task is generated only after:

- the representative archetype cases are frozen
- the transport taxonomy is frozen
- the summary table records all tested scope variants and verdicts

Default paper role:

- appendix rigor figure

Main-paper promotion is allowed only if `RQ3` needs a dedicated visual and the full paper still remains visually lean.

## Acceptance Criteria

- [x] Includes at least one robustly stable case.
- [x] Includes at least one robustly unstable case.
- [x] Includes at least one boundary-sensitive case.
- [x] Uses explicit protocol variations, not ad-hoc prose only.
- [x] The scope-transport figure is generated only after the archetype set and summary table are frozen.
- [x] Interpretation note states what the results mean for methodological rigor.

## Dependencies

- [00_OVERVIEW.md](./00_OVERVIEW.md)
- [02_E1_METRIC_VS_CLAIM.md](./02_E1_METRIC_VS_CLAIM.md)

## Status

- [ ] Not started
- [ ] In progress
- [x] Done

## Notes

This task strengthens rigor. It should read as method validation, not as scope apology.
The paper-facing framing should emphasize scope transport, not arbitrary scope tweaking.
