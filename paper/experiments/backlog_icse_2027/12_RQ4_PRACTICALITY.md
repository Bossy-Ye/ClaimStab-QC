# 12 RQ4 Practicality

## Goal

Turn the existing `E5` and `W5` policy-comparison results into a main-paper
`RQ4` evidence surface showing when claim-level validation is operationally
cheap and when conservative validation still requires larger budgets.

## Inputs

- `../../../output/paper/evaluation_v2/derived_paper_evaluation/RQ4_practicality/e5_policy_summary.csv`
- `../../../output/paper/evaluation_v3/derived_paper_evaluation/RQ4_practicality/w5_policy_by_strategy.csv`
- `../../../output/paper/evaluation_v3/derived_paper_evaluation/RQ4_practicality/w5_policy_by_variant.csv`

## Outputs

- unified dataset:
  - `output/paper/icse_pack/derived/RQ4/practicality_tradeoff_dataset.csv`
  - `output/paper/icse_pack/derived/RQ4/practicality_tradeoff_dataset.json`
- main-paper table:
  - `output/paper/icse_pack/tables/tab4_rq4_practicality_summary.csv`
- main-paper figure:
  - `output/paper/icse_pack/figures/main/fig4_cost_configuration_tradeoff.png`
  - `output/paper/icse_pack/figures/main/fig4_cost_configuration_tradeoff.pdf`
- short interpretation note:
  - `output/paper/icse_pack/derived/RQ4/practicality_interpretation.md`

## Canonical Figure Timing

The canonical `RQ4` figure is generated only after:

- the clear-case and boundary-case policy summaries are frozen
- cost is expressed on a common scale across both packs
- the supporting summary table is available
- the figure communicates one sentence-level claim:
  - boundary cases require larger evaluation budgets even when policy agreement remains intact

Default paper role:

- `Fig 4` main-paper practicality figure

## Acceptance Criteria

- [x] A unified `RQ4` dataset exists for both clear-case and boundary-case policy packs.
- [x] Cost is normalized to a comparable scale across packs.
- [x] The canonical `RQ4` table reports clear-case vs boundary-case cost by strategy.
- [x] The canonical `RQ4` figure is generated directly from the frozen dataset.
- [x] The figure uses paper-facing typography and natural-language labels.
- [x] The interpretation note explicitly states that the current evidence is about operational cost, not hardware realism.

## Dependencies

- [00_OVERVIEW.md](./00_OVERVIEW.md)
- [08_FIGURES_AND_TABLES.md](./08_FIGURES_AND_TABLES.md)

## Status

- [ ] Not started
- [ ] In progress
- [x] Done

## Notes

The current `RQ4` evidence is strongest when framed as:

- clear cases can often be decided cheaply
- difficult boundary cases consume more of the admissible configuration budget
- this is expected behavior for a conservative validation method
