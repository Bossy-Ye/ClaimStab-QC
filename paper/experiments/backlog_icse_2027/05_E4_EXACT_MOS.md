# 05 E4 Exact MOS

## Goal

Turn claim-failure diagnostics into explicit explanatory evidence via exact minimal overturn sets where tractable.

## Inputs

- exact MOS implementation
- re-run packs with exact MOS materialized
- exact-vs-greedy comparison outputs

## Outputs

- exact witness examples table
- exact/approx status table by experiment
- MOS size distribution figure

## Canonical Figure Timing

The canonical figure for this task is generated only after:

- exact vs approximate status is frozen per experiment
- representative witness examples are curated
- witness-size statistics are derived from the final exact-aware outputs

Default paper role:

- `Fig 3` main-paper explanatory figure

## Acceptance Criteria

- [x] All tractable main-paper spaces use exact MOS by default.
- [x] Larger spaces are explicitly marked approximate.
- [x] At least one table shows concrete exact witness examples.
- [x] At least one figure summarizes witness-size behavior.
- [x] The canonical explanatory figure is generated only after the witness table and exact/approx status table are frozen.
- [x] Paper-facing wording uses “witness” / “compact sufficient subset”, not causal root-cause language.

## Dependencies

- [00_OVERVIEW.md](./00_OVERVIEW.md)

## Status

- [ ] Not started
- [ ] In progress
- [x] Done

## Notes

This task upgrades diagnostics from heuristic importance to formal explanatory evidence.
