# Formal Definitions

This page is the exported scaffold for the core ClaimStab terms used in paper and artifact text.

## Claim

A claim is a formal statement about one or more methods under a declared metric and task context.

- ranking claim: method `A` outperforms method `B` by at least margin `delta`
- decision claim: the target label appears in the top-`k` outputs
- distribution claim: two output distributions differ by at least `epsilon`

## Admissible Perturbation Space

An admissible perturbation space is the set of execution-visible configuration changes that preserve:

- the scientific task identity
- the target metric and decision criterion
- the semantic interpretation of claim satisfaction

These three checks correspond to the paper's `Q1/Q2/Q3` admissibility protocol.

## Claim-Preservation Event

For one claim-space-configuration tuple, let `Y = 1` if the claim is satisfied under that configuration and `Y = 0` otherwise.

ClaimStab reduces each configuration evaluation to this Bernoulli preservation event.

## Stability Estimate

For a declared perturbation scope with `n` evaluated configurations, the empirical stability estimate is:

- `s_hat = (1 / n) * sum_i Y_i`

This is the fraction of admissible configurations under which the claim remains true.

## Conservative Verdict Rule

Let `tau` be the stability threshold and let `CI(s_hat)` be a confidence interval on the preservation rate.

- `stable` if the lower CI bound is at least `tau`
- `unstable` if the upper CI bound is below `tau`
- `inconclusive` otherwise

This rule prevents overclaiming near the decision boundary.

## Diagnostic Witness

A diagnostic witness is a compact sufficient subset of varying perturbation factors whose restriction materially explains a stability flip pattern.

For small main-paper spaces, ClaimStab can enumerate exact minimal sufficient subsets.
For larger optional spaces, heuristic compression remains available as a fallback.
