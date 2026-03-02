# Perturbations

ClaimStab focuses on software-visible, controllable perturbations:
- `seed_transpiler`
- `optimization_level`
- `layout_method`
- `shots`
- `seed_simulator`

## Presets

| Preset | Varying Knobs | Fixed Knobs | Typical Use |
|---|---|---|---|
| `compilation_only` | `seed_transpiler`, `optimization_level`, `layout_method` | `shots`, `seed_simulator` | Isolate compiler/toolchain effects |
| `sampling_only` | `shots`, `seed_simulator` | transpilation knobs | Stress stochastic sampling effects |
| `combined_light` | compilation knobs + small execution variation | reduced mixed grid | Practical mixed perturbation regime |

## Rationale
- `compilation_only` tests algorithmic claims against transpiler stochasticity/heuristics.
- `sampling_only` captures instability from finite-shot and simulator randomness.
- `combined_light` approximates realistic combined variance while managing cost.

Low-shot settings (e.g., 16/32/64) are intentionally included in `sampling_only` to reveal failure modes and uncertainty-sensitive behavior.
