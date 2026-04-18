# Analysis Units

This note fixes the counting language used throughout the paper.

## Claim variant

A `claim variant` is the primary analysis unit in `RQ1`.

For comparative claims, one variant is defined by:
- one claim pair,
- one perturbation scope,
- one practical margin `delta`

Example:
- `QAOA_p2 > QAOA_p1`
- under `combined_light_exact`
- with `delta = 0.05`

This is one claim variant.

## Configuration cell

A `configuration cell` is one perturbation configuration inside a declared
admissible scope.

Examples of varying dimensions include:
- transpiler seed
- optimization level
- layout method
- shot budget
- simulator seed

Configuration cells are not the same as claim variants.

## Why both counts appear

In `RQ1`, we report both:
- the number of claim variants
- the number of underlying configuration cells aggregated behind them

This distinction matters because the paper makes claim-level statements, while
those claims are evaluated over a full admissible perturbation space.

## Current `RQ1` counts

For the current comparative mismatch surface:
- `63` = number of comparative claim variants
- `1719` = total variant-scope-configuration cells aggregated behind those variants

Breakdown:
- `MaxCut QAOA`: `27` variants
- `Max-2-SAT QAOA`: `18` variants
- `VQE/H2`: `18` variants

Scope sizes:
- `compilation_only_exact = 27`
- `sampling_only_exact = 20`
- `combined_light_exact = 30`

These counts should not be conflated.

The paper's empirical unit for `RQ1` is the claim variant, not the raw
configuration cell.
