# 06 E5 Cross-Family Evidence

## Goal

Promote cross-family evidence into the main story so the method does not read as a single-case MaxCut phenomenon.

## Inputs

- ranking / decision / distribution claim-family outputs
- MaxCut QAOA / Max-2-SAT QAOA / VQE algorithm-family outputs
- simulator / fake backend / minimal hardware execution family outputs

## Outputs

- family-level distribution figure
- family-level summary table
- short narrative distinguishing:
  - claim family
  - algorithm family
  - execution family

## Canonical Figure Timing

The canonical cross-family figure is generated only after:

- the role of each family in the paper is frozen
- claim family and algorithm family are explicitly separated
- the summary table confirms the figure is not driven by a mislabeled family axis

Default paper role:

- appendix or supporting main-paper figure

It should move into the main paper only if it materially strengthens the “not a toy single-case artifact” argument beyond what `Tab 1` already shows.

## Acceptance Criteria

- [ ] The paper-facing results explicitly separate claim-family and algorithm-family evidence.
- [ ] VQE and Max-2-SAT appear in the main evidence surface, not only appendix/supporting text.
- [ ] At least one figure supports the “not a toy single-case artifact” argument.
- [ ] The canonical family-distribution figure is generated only after the family taxonomy and summary table are frozen.

## Dependencies

- [02_E1_METRIC_VS_CLAIM.md](./02_E1_METRIC_VS_CLAIM.md)
- [05_E4_EXACT_MOS.md](./05_E4_EXACT_MOS.md)

## Status

- [ ] Not started
- [ ] In progress
- [ ] Done

## Notes

Do not broaden for breadth alone. Only include families that sharpen the paper’s main claim.
