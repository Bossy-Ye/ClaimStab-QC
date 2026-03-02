# Device-aware Results

ClaimStab supports device-targeted evaluation without requiring access to real QPU hardware.

## Modes
- **Tier-1: `transpile_only`**
  - Evaluate compiler/device compatibility and structure quality.
  - Metrics: `circuit_depth`, `two_qubit_count`, `swap_count`.
  - Default structural claim pairs: `QAOA_p1>QAOA_p2`, `QAOA_p1>RandomBaseline`, `QAOA_p2>RandomBaseline`.
- **Tier-2: `noisy_sim`**
  - Use IBM fake backend snapshots + Aer device-informed noise simulation.
  - Produces count-based objective metrics when runtime supports it.

## Device Profiles
Device profiles are resolved from:
- `qiskit_ibm_runtime.fake_provider` class names (e.g., `FakeBrisbane`, `FakePrague`)
- snapshot fingerprinting for reproducibility metadata.

## Scope Clarification
This is **device-aware estimation**, not real-hardware execution:
- no queue time or drift from physical devices,
- reproducible software-level comparison using fake backend snapshots,
- suitable for artifact and paper reproducibility studies.

## Interpretation for Submission
- Treat device-aware outputs as **supporting validity evidence**, not the primary instability claim.
- Primary instability evidence should remain the outcome-metric tracks (`sampling_only`, `combined_light`) in main experiments.
- Structural transpile-only runs can be stable on some pairs; this is expected and should be reported transparently.

## Practical Notes
- Small devices may be incompatible with larger benchmark instances; ClaimStab now skips incompatible instances instead of crashing.
- On Python 3.13 in some environments, Aer noisy simulation may be unstable; ClaimStab reports explicit skip reasons.
