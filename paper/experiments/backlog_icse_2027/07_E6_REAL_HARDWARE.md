# 07 E6 Real Hardware

## Goal

Add one minimal IQM/VTT real-hardware validation slice to show the methodology is not confined to simulator-only settings.

## Strategy

- IQM-first, not IBM-first
- BV only in the first wave
- fake-profile transport first
- local IQM fake rehearsal before facade or real backend
- facade/mock path first, real backend second
- appendix by default

## Priority Order

1. BV local rehearsal (`IQMFakeAphrodite` noisy simulation)
2. fake-profile transport on IQM / IBM fake backends
3. BV facade/mock run
4. BV real backend
5. Grover (only if BV is already stable)
6. VQE (only if BV and Grover are already stable)

## Inputs

- IQM runner and hardware-slice script
- local IQM fake-backend rehearsal spec
- fake-profile transport subtask:
  - [07A_PROFILE_TRANSPORT.md](./07A_PROFILE_TRANSPORT.md)
- hardware slice specs
- IQM server URL, quantum-computer name, and token
- optional facade backend for dry runs (e.g. `facade_aphrodite`)

## Outputs

- one real-hardware result package
- one local fake-backend rehearsal package
- one small hardware-facing figure or table
- one short interpretation note stating what the slice does and does not prove
- optional supporting non-target hardware note when a minimal real run lands on
  a different provider family before the target IQM/VTT path

## Canonical Figure Timing

The canonical hardware visual is generated only after:

- the local IQM fake rehearsal succeeds on the same BV slice
- the fake-profile transport summary is frozen if profile-conditioned evidence is cited
- the IQM facade or mock path runs end-to-end
- at least one real-backend run completes successfully
- the exact command path for reproduction is documented
- the note explicitly constrains the claim to a minimal reality check

Default paper role:

- appendix by default

Main-paper promotion is allowed only if the hardware slice materially sharpens `RQ4` rather than merely adding realism flavor.

## Acceptance Criteria

- [ ] An IQM facade or mock run completes successfully through the same ClaimStab pipeline used for hardware.
- [x] A local IQM fake-backend rehearsal completes successfully on the BV slice with `backend.noise_model=from_device_profile`.
- [x] If fake-profile evidence is cited, it is routed through `07A_PROFILE_TRANSPORT` rather than folded into the main perturbation space.
- [ ] At least one real IQM/VTT backend run completes successfully on the BV slice.
- [ ] The output package is reproducible with documented commands and environment variables.
- [ ] The paper-facing note states that this is a minimal slice, not a broad hardware benchmark.
- [ ] The task remains BV-first; Grover and VQE are not added until the BV slice is stable.
- [ ] The hardware evidence can be cited in main text or appendix without overclaiming.
- [ ] Any canonical hardware figure or table is generated only after the run package and reproduction command are frozen.

## Dependencies

- [01_REPO_CONVERGENCE.md](./01_REPO_CONVERGENCE.md)
- [02_E1_METRIC_VS_CLAIM.md](./02_E1_METRIC_VS_CLAIM.md)
- [07A_PROFILE_TRANSPORT.md](./07A_PROFILE_TRANSPORT.md)

## Status

- [ ] Not started
- [x] In progress
- [ ] Done

## Notes

Keep this small. Success means “credible reality check”, not “complete hardware study”.
Do not try to use all 54 qubits. The value of this task is a direct hardware path, not maximal circuit scale.

Current pre-hardware evidence:

- local IQM fake rehearsal on the BV slice succeeded
- `07A_PROFILE_TRANSPORT` completed on three IQM fake profiles and two IBM fake profiles
- within the frozen IQM fake family, both BV decision claims were `profile_robust`
- therefore a minimal real-IQM BV slice is worth attempting

Additional supporting evidence already available:

- one minimal `BVOracle`-only real run completed on `IBM Open Plan`
- this run is recorded as a supporting reality check in:
  - `paper/presentation/icse_2027/notes/hardware_reality_check_note.md`
- it does not satisfy the target IQM/VTT acceptance criterion for this task
- it does show that the frozen minimal slice survives a real-backend path on a
  non-target provider family

Current recommendation:

- proceed to IQM facade/mock first
- if the facade path succeeds end-to-end, run one appendix-scoped real IQM/VTT BV slice
- do not widen to Grover or VQE before the BV hardware slice is frozen

Suggested command path:

```bash
./venv/bin/python -m claimstab.cli run \
  --spec paper/experiments/specs/evaluation_v4/d0_bv_iqm_fake_rehearsal.yml \
  --out-dir output/paper/evaluation_v4/runs/D0_bv_iqm_fake_rehearsal \
  --report

./venv/bin/python paper/experiments/scripts/run_hardware_slice_iqm.py \
  --list-backends \
  --server-url "$CLAIMSTAB_IQM_SERVER_URL" \
  --quantum-computer "$CLAIMSTAB_IQM_QUANTUM_COMPUTER_MOCK" \
  --include-facades

./venv/bin/python paper/experiments/scripts/run_hardware_slice_iqm.py \
  --spec paper/experiments/specs/evaluation_v4/d1_bv_hardware_slice.yml \
  --out-dir output/paper/evaluation_v4/runs/D1_bv_hardware_slice_iqm_facade \
  --server-url "$CLAIMSTAB_IQM_SERVER_URL" \
  --quantum-computer "$CLAIMSTAB_IQM_QUANTUM_COMPUTER_MOCK" \
  --backend-name facade_aphrodite
```
