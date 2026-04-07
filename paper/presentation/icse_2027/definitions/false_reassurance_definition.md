# False Reassurance Definition

This definition is the canonical paper-facing version for `RQ1`.

## Metric-positive

A comparative claim variant is `metric-positive` when the frozen metric baseline
reports positive support for method `A` over method `B`.

Operationally, for a matched-scope comparative baseline:
- compute a per-configuration margin between the two methods
- average the margin across configurations
- form a standard 95% confidence interval on that mean margin
- label the variant `metric-positive` only when:
  - the mean margin is positive, and
  - the lower confidence bound is strictly positive

For higher-is-better metrics:
- margin = `score(A) - score(B)`

For lower-is-better metrics:
- margin = `score(B) - score(A)`

## Claim validation outcomes

For each comparative claim variant, ClaimStab-QC assigns one of four paper-facing
outcomes:

- `validated`
  - the baseline claim holds, and
  - the claim is stable under the admissible perturbation scope
- `refuted`
  - the baseline claim does not hold, and
  - that non-holding relation is stable under the admissible perturbation scope
- `unstable`
  - the claim relation is not preserved under the admissible perturbation scope
- `inconclusive`
  - the evidence is insufficient to conclude either stable or unstable

## False reassurance

A variant is counted as `false reassurance` when:
- the metric baseline is positive, but
- claim-level validation does not return `validated`

Equivalently:
- `false reassurance = metric-positive AND claim_validation_outcome != validated`

This includes three cases:
- `metric-positive + refuted`
- `metric-positive + unstable`
- `metric-positive + inconclusive`

## Why this matters

The purpose of this definition is to distinguish:
- outcome-level support from
- conclusion-level validation

The paper claim is not that metric baselines are useless.
The paper claim is that they can support outcomes without explicitly validating
the reported conclusion.
