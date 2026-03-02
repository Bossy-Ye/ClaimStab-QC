# Device-aware Results

ClaimStab supports device-targeted evaluation without requiring access to real QPU hardware.

## Modes
- **Tier-1: `transpile_only`**
  - Evaluate compiler/device compatibility and structure quality.
  - Metrics: `circuit_depth`, `two_qubit_count`, `swap_count`.
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

## Practical Notes
- Small devices may be incompatible with larger benchmark instances; ClaimStab now skips incompatible instances instead of crashing.
- On Python 3.13 in some environments, Aer noisy simulation may be unstable; ClaimStab reports explicit skip reasons.
