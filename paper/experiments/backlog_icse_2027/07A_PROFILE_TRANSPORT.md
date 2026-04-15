# 07A Profile Transport on Fake Backends

## Goal

Add a small, profile-conditioned supporting study that tests whether ClaimStab verdicts transport across fake backend profiles without turning backend profiles into ordinary perturbation knobs.

## Positioning

This task exists to strengthen `07_E6_REAL_HARDWARE`, not to replace it.

It should be treated as:

- a pre-hardware supporting study
- an outer execution-context layer
- appendix / artifact evidence by default

It must **not** be treated as:

- an expansion of the main admissible perturbation space
- a provider ranking study
- a benchmark-coverage exercise

## Scope

Fixed task:

- `BV`

Fixed claim units:

- `BVOracle`, `top_k = 1`
- `BVOracle`, `top_k = 3`

Fixed perturbation scope:

- `compilation_only_exact`

Fixed backend execution mode:

- `engine: aer`
- `noise_model: from_device_profile`

Profile families:

- IQM fake profiles:
  - `IQMFakeAdonis`
  - `IQMFakeAphrodite`
  - `IQMFakeApollo`
- IBM fake profiles:
  - `FakeBrisbane`
  - `FakePrague`

The study should first establish **within-family profile transport**, and only then summarize a limited **cross-family profile substitution** view.

## Non-goals

- Do not add Grover or VQE to this task.
- Do not fold `backend_profile` into the main perturbation grid alongside `shots`, `layout_method`, or `seed_transpiler`.
- Do not make claims about provider quality, realism, or superiority.
- Do not present fake-backend results as substitutes for real-hardware evidence.

## Inputs

- `BV` decision-claim task surface from:
  - `/Users/mac/Documents/GitHub/ClaimStab-QC/paper/experiments/specs/evaluation_v2/e3_bv_decision.yml`
- local IQM fake rehearsal surface from:
  - `/Users/mac/Documents/GitHub/ClaimStab-QC/paper/experiments/specs/evaluation_v4/d0_bv_iqm_fake_rehearsal.yml`
- device-profile support in:
  - `/Users/mac/Documents/GitHub/ClaimStab-QC/claimstab/devices/registry.py`
  - `/Users/mac/Documents/GitHub/ClaimStab-QC/claimstab/devices/iqm_fake.py`
- existing IBM fake support in:
  - `/Users/mac/Documents/GitHub/ClaimStab-QC/claimstab/devices/ibm_fake.py`

## Outputs

- one canonical profile-transport dataset
- one summary table with profile-conditioned verdicts
- optional one appendix-facing transport heatmap
- one short interpretation note explicitly constraining what fake profiles do and do not prove

Suggested canonical paths:

- `output/paper/icse_pack/derived/HW/profile_transport_dataset.csv`
- `output/paper/icse_pack/tables/tab_profile_transport_summary.csv`
- `output/paper/icse_pack/figures/appendix/fig_profile_transport_map.png`
- `output/paper/icse_pack/derived/HW/profile_transport_interpretation.md`

## Required Semantics

The study must explicitly distinguish:

- **main perturbation space**
  - software-visible protocol choices such as `shots`, `layout_method`, and `seed_transpiler`
- **profile layer**
  - backend-conditioned execution-context substitutions such as `IQMFakeAphrodite` or `FakeBrisbane`

The paper-facing note must state that backend profiles are treated as **outer execution contexts**, not as ordinary admissible perturbation knobs.

## Recommended Execution Strategy

1. Freeze the exact `BV` claim units and perturbation scope.
2. Run the same `BV` spec once per frozen profile.
3. Build a unified table keyed by:
   - `provider_family`
   - `profile_name`
   - `claim_id`
   - `decision`
   - `stability_hat`
   - `n_claim_evals`
   - `transport_class`
4. First summarize within-family transport.
5. Then summarize the small cross-family substitution view.

## Transport Taxonomy

Use one of:

- `profile_robust`
- `profile_sensitive`
- `profile_inconclusive`

If all frozen profiles agree on the same verdict for a claim, label it `profile_robust`.
If at least one frozen profile changes the verdict, label it `profile_sensitive`.
Use `profile_inconclusive` only when the summary cannot defend either conclusion cleanly.

## Canonical Figure Timing

The canonical figure or appendix visual is generated only after:

- the profile set is frozen
- the claim set is frozen
- the summary table is frozen
- the transport taxonomy is frozen
- the note explicitly states that the study is supporting profile evidence, not main perturbation-space evidence

## Acceptance Criteria

- [x] The task explicitly states that fake backend profiles are execution-context substitutions, not ordinary perturbation axes in the main admissible scope.
- [x] The same `BV` decision claims are executed successfully on at least three IQM fake profiles.
- [x] The same `BV` decision claims are executed successfully on at least two IBM fake profiles.
- [x] A single canonical dataset records profile-conditioned verdicts using the same claim units across all frozen profiles.
- [x] A canonical summary table reports, at minimum, `provider_family`, `profile_name`, `claim_id`, `decision`, `stability_hat`, `n_claim_evals`, and `transport_class`.
- [x] The accompanying note explicitly states that the study does not rank providers and does not substitute for real-hardware validation.
- [x] If verdicts are identical across profiles, the note explicitly states that the result is profile-robust rather than overstating generality.
- [x] If any verdict flips across profiles, the note explicitly names the result profile-sensitive rather than hiding the disagreement.
- [x] Any canonical figure is generated only after the summary table and taxonomy are frozen.

## Dependencies

- [04_E3_SCOPE_ROBUSTNESS.md](./04_E3_SCOPE_ROBUSTNESS.md)
- [07_E6_REAL_HARDWARE.md](./07_E6_REAL_HARDWARE.md)
- [08_FIGURES_AND_TABLES.md](./08_FIGURES_AND_TABLES.md)

## Status

- [ ] Not started
- [ ] In progress
- [x] Done

## Notes

This task is valuable because it raises the technical bar before real-hardware execution:

- it filters brittle cases before credits are spent
- it gives a structured profile-transport story
- it does so without polluting the main perturbation space

Observed result on the frozen five-profile set:

- within the IQM fake family, both `BVOracle top-1` and `BVOracle top-3` were `profile_robust`
- across the combined IQM + IBM fake set, both claims were `profile_sensitive`
- the resulting hardware recommendation is still `worth_real_iqm = yes`, because the instability was cross-family and not internal to the frozen IQM fake family

Canonical outputs:

- `/Users/mac/Documents/GitHub/ClaimStab-QC/output/paper/icse_pack/derived/HW/profile_transport_dataset.csv`
- `/Users/mac/Documents/GitHub/ClaimStab-QC/output/paper/icse_pack/tables/tab_profile_transport_summary.csv`
- `/Users/mac/Documents/GitHub/ClaimStab-QC/output/paper/icse_pack/figures/appendix/fig_profile_transport_map.png`
- `/Users/mac/Documents/GitHub/ClaimStab-QC/output/paper/icse_pack/derived/HW/profile_transport_interpretation.md`
