# 06 E5 Cross-Family Evidence

## Goal

Promote cross-family evidence into the main story so the method does not read
as a single-case MaxCut phenomenon.

This task is intentionally narrower than a full claim-family or execution-family
study. The current paper-facing scope is:

- comparative / ranking claims only
- algorithm-family evidence across:
  - MaxCut QAOA
  - Max-2-SAT QAOA
  - VQE/H2

## Inputs

- frozen `RQ1` comparative-claim dataset
- MaxCut QAOA / Max-2-SAT QAOA / VQE algorithm-family outputs already materialized in the `RQ1` surface

## Outputs

- family-level distribution figure
- family-level summary table
- short narrative explicitly stating:
  - the current surface is comparative / ranking only
  - the current heterogeneity is across algorithm families
  - hardware / execution-family extension is deferred to `07`

## Canonical Figure Timing

The canonical cross-family figure is generated only after:

- the role of each family in the paper is frozen
- the note explicitly states that claim-family coverage is not broader than comparative / ranking
- the summary table confirms the figure is not driven by a mislabeled family axis

Default paper role:

- appendix or supporting main-paper figure

It should move into the main paper only if it materially strengthens the “not a toy single-case artifact” argument beyond what `Tab 1` already shows.

## Acceptance Criteria

- [x] The canonical `06` evidence explicitly states that the current cross-family surface covers comparative / ranking claims only.
- [x] A paper-facing table reports verdict and validation-outcome counts for `MaxCut QAOA`, `Max-2-SAT QAOA`, and `VQE/H2`.
- [x] A canonical `icse_pack` figure shows heterogeneous behavior across algorithm families without conflating claim-family and algorithm-family axes.
- [x] The accompanying note explicitly states that hardware / execution-family expansion remains outside the current `06` scope.
- [x] The canonical figure is generated only after the family taxonomy and summary table are frozen.

## Dependencies

- [02_E1_METRIC_VS_CLAIM.md](./02_E1_METRIC_VS_CLAIM.md)
- [05_E4_EXACT_MOS.md](./05_E4_EXACT_MOS.md)

## Status

- [ ] Not started
- [ ] In progress
- [x] Done

## Notes

Do not broaden for breadth alone. Only include families that sharpen the paper’s main claim.

Implementation completed via:

- `/Users/mac/Documents/GitHub/ClaimStab-QC/paper/experiments/scripts/derive_rq2_cross_family_icse.py`
- `output/paper/icse_pack/derived/RQ2/cross_family_dataset.csv`
- `output/paper/icse_pack/tables/tab_rq2_cross_family_summary.csv`
- `output/paper/icse_pack/figures/main/fig5_cross_family_outcomes.png`
