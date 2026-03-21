# Perturbations

ClaimStab focuses on software-visible, controllable perturbations:
- `seed_transpiler`
- `optimization_level`
- `layout_method`
- `shots`
- `seed_simulator`

Optional task-specific axis:
- `init_strategy` and `init_seed` for MaxCut/QAOA hybrid-initialization sensitivity
  - enabled only when `task.params.hybrid_optimization.enabled: true`
  - values are configured via `task.params.hybrid_optimization.init_strategies` and `init_seeds`

Deprecated compatibility note: legacy specs may use `repeats`; ClaimStab maps it to `seed_simulator` when needed and records `meta.deprecated_field_used`.

## Presets

| Preset | Varying Knobs | Fixed Knobs | Typical Use |
|---|---|---|---|
| `compilation_only` | `seed_transpiler`, `optimization_level`, `layout_method` | `shots`, `seed_simulator` | Isolate compiler/toolchain effects |
| `compilation_only_exact` | exact 27-cell compilation grid | execution knobs fixed | Small exact-scope paper reruns |
| `sampling_only` | `shots`, `seed_simulator` | transpilation knobs | Stress stochastic sampling effects |
| `sampling_only_exact` | exact 20-cell execution grid | transpilation knobs fixed | Small exact-scope paper reruns |
| `combined_light` | compilation knobs + small execution variation | reduced mixed grid | Practical mixed perturbation regime |
| `combined_light_exact` | exact 30-cell mixed grid | reduced mixed grid | Small exact-scope paper reruns |
| `compilation_stress` | same knobs as `compilation_only` with wider seed range | execution knobs fixed | Heavy transpiler stress tests |
| `sampling_stress` | same knobs as `sampling_only` with wider shots/seed range | transpilation knobs fixed | Low-shot fragility stress tests |
| `combined_stress` | compilation + execution knobs (expanded) | none | High-variance mixed stress regime |

## Rationale
- `compilation_only` tests algorithmic claims against transpiler stochasticity/heuristics.
- `sampling_only` captures instability from finite-shot and simulator randomness.
- `combined_light` approximates realistic combined variance while managing cost.
- `*_exact` presets are additive aliases for small, fully enumerable reruns and do not change the larger canonical presets.
- `*_stress` presets are optional and additive; they expand search breadth without changing existing preset semantics.

Low-shot settings (e.g., 16/32/64) are intentionally included in `sampling_only` to reveal failure modes and uncertainty-sensitive behavior.
