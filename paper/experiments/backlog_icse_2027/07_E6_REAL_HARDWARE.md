# 07 E6 Real Hardware

## Goal

Add one minimal real-hardware validation slice to show the methodology is not confined to simulator-only settings.

## Priority Order

1. BV
2. Grover
3. VQE (only if budget and runtime allow)

## Inputs

- IBM runtime scaffold
- hardware slice specs
- backend credentials / access path

## Outputs

- one real-hardware result package
- one small hardware-facing figure or table
- one short interpretation note stating what the slice does and does not prove

## Acceptance Criteria

- [ ] At least one real-backend run completes successfully.
- [ ] The output package is reproducible with documented commands.
- [ ] The paper-facing note states that this is a minimal slice, not a broad hardware benchmark.
- [ ] The hardware evidence can be cited in main text or appendix without overclaiming.

## Dependencies

- [01_REPO_CONVERGENCE.md](./01_REPO_CONVERGENCE.md)
- [02_E1_METRIC_VS_CLAIM.md](./02_E1_METRIC_VS_CLAIM.md)

## Status

- [ ] Not started
- [ ] In progress
- [ ] Done

## Notes

Keep this small. Success means “credible reality check”, not “complete hardware study”.
