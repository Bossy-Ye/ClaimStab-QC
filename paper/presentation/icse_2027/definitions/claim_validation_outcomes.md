# Claim Validation Outcomes

These are the canonical paper-facing claim outcomes for comparative claims.

## Validated

`validated` means:
- the baseline claim holds, and
- the claim is stable under the declared admissible perturbation scope

This is the strongest positive outcome.

## Refuted

`refuted` means:
- the baseline claim does not hold, and
- that non-holding relation is stable under the declared admissible perturbation scope

This is a stable negative result, not a noisy failure.

## Unstable

`unstable` means:
- the relation of interest is not preserved across the admissible perturbation scope

This is the core notion of claim fragility used in the paper.

## Inconclusive

`inconclusive` means:
- the current evidence is insufficient to conclude either stable or unstable

This is not treated as validation.

## Important distinction

`stable` in the raw ClaimStab decision layer is not identical to `validated`.

A claim can be:
- `stable and validated`, or
- `stable and refuted`

This distinction is essential for `RQ1`.
