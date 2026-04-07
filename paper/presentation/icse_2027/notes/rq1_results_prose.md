# RQ1 Results Prose

This file contains manuscript-ready wording for the `RQ1` main result.

## Short version

We evaluate `RQ1` on a unified mismatch surface over comparative claims under
one frozen metric baseline. Across `63` comparative claim variants, the metric
baseline is positive for `27`. Among these metric-positive variants, only `13`
are claim-validated, while `13` are claim-unstable and `1` is claim-inconclusive,
yielding a conditional false-reassurance rate of `51.9%`. This shows that
empirical evaluation can statistically support outcomes without explicitly
validating the reported conclusion.

## Main-paper paragraph

To test whether outcome-level support aligns with conclusion-level validation,
we construct a unified comparative mismatch surface under one frozen metric
baseline. The surface contains `63` comparative claim variants spanning
algorithm family, admissible perturbation scope, and practical margin
configuration. Across these variants, the metric baseline reports positive
support in `27` cases. However, only `13` of those metric-positive variants are
claim-validated under ClaimStab-QC. The remaining `14` metric-positive variants
fail to validate at the claim level: `13` are unstable and `1` is
inconclusive. This yields a conditional false-reassurance rate of `14/27 =
51.9%`, directly demonstrating that a metric summary can support an empirical
outcome while failing to validate the reported claim.

## Family-aware paragraph

The mismatch is not uniform across all populations. It is strongest in the
primary MaxCut battleground, where all `9` metric-positive variants are
non-validated at the claim level. The effect remains visible but weaker in
Max-2-SAT, where `5` of `18` metric-positive variants are non-validated. In the
VQE/H2 diagonal proxy pilot, the frozen metric baseline does not produce any
metric-positive variants. This heterogeneity is important: it shows that the
problem is structural but population-dependent, rather than a universal
artifact of every family in the same form.

## Scope-aware paragraph

The mismatch is also visible across multiple admissible perturbation scopes.
Compilation-only variants yield a conditional false-reassurance rate of
`41.7%`, combined-light variants yield `50.0%`, and the current sampling-only
slice yields `100.0%`. We therefore do not observe a single-scope artifact.
Instead, the discrepancy persists across several operational slices, with the
execution-heavy slice exhibiting the most severe fragility in the present
comparison surface.

## Limitation paragraph

This result should be read with two explicit boundaries. First, the mismatch
surface is restricted to comparative / ranking claims; decision and
distribution claims are analyzed separately in `RQ2`. Second, the comparison is
performed against one frozen metric baseline rather than the full space of
possible baseline families. Accordingly, `RQ1` establishes that metric support
can diverge from claim validation under this baseline surface, not that every
possible conventional baseline fails in the same way.

## Figure caption template

**Fig. 1. Metric-claim discrepancy matrix.** A unified comparative mismatch
surface over `63` claim variants under one frozen metric baseline. Highlighted
cells mark false-reassurance cases, where the metric baseline is positive but
claim-level validation does not return `validated`. Across `27` metric-positive
variants, `14` are non-validated (`13` unstable, `1` inconclusive), yielding a
conditional false-reassurance rate of `51.9%`.

## Table caption template

**Tab. 1. Metric-claim mismatch summary.** Summary counts for the unified
comparative mismatch surface. The table reports the number of variants, the
number of metric-positive cases, the distribution of claim-level outcomes, and
the conditional false-reassurance rate overall and across key structural
breakdowns.

## Intro/abstract sentence

Current empirical evaluation pipelines can statistically support outcomes
without explicitly validating conclusions.
