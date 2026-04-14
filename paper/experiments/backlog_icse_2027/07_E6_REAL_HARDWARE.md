# 07 E6 Real Hardware

## Goal

Add one minimal IQM/VTT real-hardware validation slice to show the methodology is not confined to simulator-only settings.

## Strategy

- IQM-first, not IBM-first
- BV only in the first wave
- facade/mock path first, real backend second
- appendix by default

## Priority Order

1. BV
2. Grover (only if BV is already stable)
3. VQE (only if BV and Grover are already stable)

## Inputs

- IQM runner and hardware-slice script
- hardware slice specs
- IQM server URL, quantum-computer name, and token
- optional facade backend for dry runs (e.g. `facade_aphrodite`)

## Outputs

- one real-hardware result package
- one small hardware-facing figure or table
- one short interpretation note stating what the slice does and does not prove

## Canonical Figure Timing

The canonical hardware visual is generated only after:

- the IQM facade or mock path runs end-to-end
- at least one real-backend run completes successfully
- the exact command path for reproduction is documented
- the note explicitly constrains the claim to a minimal reality check

Default paper role:

- appendix by default

Main-paper promotion is allowed only if the hardware slice materially sharpens `RQ4` rather than merely adding realism flavor.

## Acceptance Criteria

- [ ] An IQM facade or mock run completes successfully through the same ClaimStab pipeline used for hardware.
- [ ] At least one real IQM/VTT backend run completes successfully on the BV slice.
- [ ] The output package is reproducible with documented commands and environment variables.
- [ ] The paper-facing note states that this is a minimal slice, not a broad hardware benchmark.
- [ ] The task remains BV-first; Grover and VQE are not added until the BV slice is stable.
- [ ] The hardware evidence can be cited in main text or appendix without overclaiming.
- [ ] Any canonical hardware figure or table is generated only after the run package and reproduction command are frozen.

## Dependencies

- [01_REPO_CONVERGENCE.md](./01_REPO_CONVERGENCE.md)
- [02_E1_METRIC_VS_CLAIM.md](./02_E1_METRIC_VS_CLAIM.md)

## Status

- [ ] Not started
- [x] In progress
- [ ] Done

## Notes

Keep this small. Success means “credible reality check”, not “complete hardware study”.
Do not try to use all 54 qubits. The value of this task is a direct hardware path, not maximal circuit scale.

Suggested command path:

```bash
./venv/bin/python paper/experiments/scripts/run_real_hardware_slice_iqm.py \
  --list-backends \
  --server-url "$CLAIMSTAB_IQM_SERVER_URL" \
  --quantum-computer "$CLAIMSTAB_IQM_QUANTUM_COMPUTER" \
  --include-facades

./venv/bin/python paper/experiments/scripts/run_real_hardware_slice_iqm.py \
  --spec paper/experiments/specs/evaluation_v4/d1_bv_hardware_slice.yml \
  --out-dir output/paper/evaluation_v4/runs/D1_bv_hardware_slice_iqm_facade \
  --server-url "$CLAIMSTAB_IQM_SERVER_URL" \
  --quantum-computer "$CLAIMSTAB_IQM_QUANTUM_COMPUTER_MOCK" \
  --backend-name facade_aphrodite
```
