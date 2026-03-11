# ClaimStab-QC Paper Scope

This document locks the paper-facing scope so the method narrative stays focused and reproducible.
The repository intentionally contains a broader infrastructure surface than the paper narrative; items outside this scope remain available for reproducibility and future community workflows.

## In Scope (Primary Contributions)

1. Claim-centric stability checking under perturbation spaces.
2. Conservative CI-based decision rule (`stable` / `unstable` / `inconclusive`).
3. Conditional robustness diagnostics:
   - robustness map cells
   - robust core
   - failure frontier
   - minimal lockdown set
4. Driver analysis:
   - main effects
   - pairwise interaction effects
5. Cost-vs-confidence analysis:
   - full-factorial, random-k, adaptive-ci
   - agreement vs cost and CI-width behavior

## Headline Experiment Packs

1. `output/presentations/large/maxcut_ranking`
   - Main fragility/robustness evidence for ranking claims.
2. `output/presentations/large/rq4_adaptive`
   - Adaptive stopping and cost/decision tradeoff.
3. `output/presentations/large/grover_dist`
   - Non-MaxCut distribution-claim fragility control.
4. `output/paper/multidevice` (when available)
   - Device-aware variation evidence via transpile/noisy-sim modes.

## Supporting Artifact Layer (Not Main Novelty Claim)

1. CEP (Claim Evidence Protocol) schema + validator.
2. Trace/cache/replay pipeline.
3. Atlas publish/validate/compare workflow.
4. Paper-pack exporter + manifest hashes.

These components support reproducibility and ecosystem usability; they should be described as enabling infrastructure, not the central algorithmic novelty.

## Out of Scope for Main Claims

1. New quantum algorithm design.
2. Hardware control/calibration contributions.
3. C++/native performance engineering as a core contribution.
4. Exhaustive all-device real-hardware benchmarking.

## Reporting Rules

1. Primary claims must be phrased as conditional robustness statements:
   - "Claim X is stable under condition set C at threshold tau."
2. Every stability decision in main figures must map to:
   - source run directory
   - `claim_stability.json`
   - paper-pack manifest entry
3. Keep CEP/Atlas discussion short and clearly labeled as artifact/reproducibility support.
